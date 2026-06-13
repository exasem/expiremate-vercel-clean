from __future__ import annotations
import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient
from bson import ObjectId
import stripe
import openai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "expiremate")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 60 * 24
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
VERIFICATION_FEE = 2.00
CURRENCY = "cad"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
stripe.api_key = STRIPE_API_KEY
openai.api_key = OPENAI_API_KEY

client = MongoClient(MONGO_URL)
db = client[DB_NAME]
app = FastAPI(title="ExpireMate Backend")


async def db_find_one(collection, query):
    return await asyncio.to_thread(collection.find_one, query)


async def db_insert_one(collection, document):
    return await asyncio.to_thread(collection.insert_one, document)


async def db_update_one(collection, query, update, upsert=False):
    return await asyncio.to_thread(collection.update_one, query, update, upsert=upsert)


async def db_find(collection, query, sort=None, limit=None):
    def _find():
        cursor = collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    return await asyncio.to_thread(_find)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenData(BaseModel):
    user_id: str
    email: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class DonationCheckoutIn(BaseModel):
    preset: Optional[str] = None
    custom_amount: Optional[float] = None
    origin_url: str
    anonymous: bool = False


class VerifyCheckoutIn(BaseModel):
    origin_url: str


class IdentityCheckoutIn(BaseModel):
    origin_url: str


class ModerateIn(BaseModel):
    title: str
    description: str
    category: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenData(user_id=str(payload["user_id"]), email=payload["email"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif request.cookies.get("access_token"):
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token_data = decode_access_token(token)
    user = await db_find_one(db.users, {"_id": ObjectId(token_data.user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def sanitize_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "verified": bool(user.get("verified", False)),
    }


def item_to_public(item: dict, viewer_id: Optional[str] = None) -> dict:
    return {
        "id": str(item["_id"]),
        "title": item.get("title"),
        "description": item.get("description", ""),
        "category": item.get("category"),
        "expiration_date": item.get("expiration_date", ""),
        "quantity": item.get("quantity", "1"),
        "zip_code": item.get("zip_code"),
        "meetup_suggestion": item.get("meetup_suggestion", ""),
        "image_path": item.get("image_path"),
        "status": item.get("status", "active"),
        "owner_id": str(item["owner_id"]),
        "owner_name": item.get("owner_name", ""),
        "claimed_by": str(item["claimed_by"]) if item.get("claimed_by") else None,
        "claimed_at": item.get("claimed_at"),
        "completed_at": item.get("completed_at"),
        "created_at": item.get("created_at"),
        "is_owner": viewer_id is not None and str(item["owner_id"]) == viewer_id,
        "is_claimer": bool(viewer_id and item.get("claimed_by") and str(item["claimed_by"]) == viewer_id),
    }


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.post("/api/auth/register")
async def register(payload: RegisterIn):
    existing = await db_find_one(db.users, {"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_doc = {
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "name": payload.name,
        "verified": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = await db_insert_one(db.users, user_doc)
    user_doc["_id"] = result.inserted_id
    token = create_access_token({"user_id": str(result.inserted_id), "email": payload.email.lower()})
    response = JSONResponse({"user": sanitize_user(user_doc), "token": token})
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@app.post("/api/auth/login")
async def login(payload: LoginIn):
    user = await db_find_one(db.users, {"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"user_id": str(user["_id"]), "email": user["email"]})
    response = JSONResponse({"user": sanitize_user(user), "token": token})
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("access_token")
    return response


@app.get("/api/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return {"user": sanitize_user(user)}


@app.get("/api/items")
async def list_items(category: Optional[str] = None, zip_code: Optional[str] = None, status: Optional[str] = "active"):
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if zip_code:
        query["zip_code"] = zip_code
    items = await db_find(db.items, query, sort=[("created_at", -1)], limit=100)
    return {"items": [item_to_public(item) for item in items]}


@app.get("/api/items/{item_id}")
async def get_item(item_id: str, request: Request):
    try:
        item = await db_find_one(db.items, {"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Item not found")
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    viewer_id = None
    if token:
        try:
            decoded = decode_access_token(token)
            viewer_id = decoded.user_id
        except HTTPException:
            viewer_id = None
    return {"item": item_to_public(item, viewer_id)}


@app.post("/api/items/{item_id}/claim")
async def claim_item(item_id: str, user: dict = Depends(get_current_user)):
    try:
        item = await db_find_one(db.items, {"_id": ObjectId(item_id)})
    except Exception:
        item = None
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.get("status") != "active":
        raise HTTPException(status_code=400, detail="Item cannot be claimed")
    if str(item["owner_id"]) == str(user["_id"]):
        raise HTTPException(status_code=400, detail="Cannot claim your own item")
    claim_code = str(uuid.uuid4().int)[:4].zfill(4)
    await db_update_one(db.items, {"_id": item["_id"]}, {"$set": {
        "status": "claimed",
        "claimed_by": user["_id"],
        "claimed_at": datetime.utcnow().isoformat(),
        "claim_code": claim_code,
    }})
    return {"claim_code": claim_code}


@app.post("/api/items/{item_id}/unclaim")
async def unclaim_item(item_id: str, user: dict = Depends(get_current_user)):
    try:
        item = await db_find_one(db.items, {"_id": ObjectId(item_id)})
    except Exception:
        item = None
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.get("status") != "claimed":
        raise HTTPException(status_code=400, detail="Item is not claimed")
    if str(item.get("claimed_by")) != str(user["_id"]) and str(item["owner_id"]) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    await db_update_one(db.items, {"_id": item["_id"]}, {"$set": {
        "status": "active",
        "claimed_by": None,
        "claimed_at": None,
        "claim_code": None,
    }})
    return {"ok": True}


class ConfirmPickupIn(BaseModel):
    code: str


@app.post("/api/items/{item_id}/confirm")
async def confirm_pickup(item_id: str, payload: ConfirmPickupIn, user: dict = Depends(get_current_user)):
    try:
        item = await db_find_one(db.items, {"_id": ObjectId(item_id)})
    except Exception:
        item = None
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if str(item["owner_id"]) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Only owner can confirm pickup")
    if item.get("status") != "claimed":
        raise HTTPException(status_code=400, detail="Item is not claimed")
    if item.get("claim_code") != payload.code:
        raise HTTPException(status_code=400, detail="Invalid claim code")
    await db_update_one(db.items, {"_id": item["_id"]}, {"$set": {
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
    }})
    return {"ok": True}


@app.post("/api/payments/donate-checkout")
async def donate_checkout(payload: DonationCheckoutIn, user: Optional[dict] = Depends(get_current_user)):
    amount = None
    presets = {"three": 3.00, "five": 5.00, "ten": 10.00}
    if payload.preset in presets:
        amount = presets[payload.preset]
    elif payload.preset == "custom" and payload.custom_amount:
        amount = float(payload.custom_amount)
    if not amount or amount < 1 or amount > 1000:
        raise HTTPException(status_code=400, detail="Invalid donation amount")
    host = payload.origin_url.rstrip("/")
    success_url = f"{host}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=donate"
    cancel_url = f"{host}/donate"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": CURRENCY,
                "product_data": {"name": "ExpireMate Donation"},
                "unit_amount": int(amount * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"purpose": "donation", "anonymous": str(payload.anonymous).lower(), **({"user_id": str(user["_id"])} if user else {})},
    )
    await db_insert_one(db.payment_transactions, {
        "session_id": session.id,
        "purpose": "donation",
        "user_id": user["_id"] if user else None,
        "amount": amount,
        "currency": CURRENCY,
        "payment_status": "initiated",
        "metadata": {"anonymous": str(payload.anonymous).lower()},
        "created_at": datetime.utcnow().isoformat(),
    })
    return {"url": session.url, "session_id": session.id}


# Aliases without the /api prefix (some frontends may call these)
@app.post("/payments/donate-checkout")
async def donate_checkout_alias(payload: DonationCheckoutIn, user: Optional[dict] = Depends(get_current_user)):
    return await donate_checkout(payload, user)


@app.post("/api/payments/verify-checkout")
async def verify_checkout(payload: VerifyCheckoutIn, user: dict = Depends(get_current_user)):
    if user.get("verified"):
        raise HTTPException(status_code=400, detail="Already verified")
    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=verify"
    cancel_url = f"{origin}/verify"
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": CURRENCY,
                "product_data": {"name": "ExpireMate Verification Fee"},
                "unit_amount": int(VERIFICATION_FEE * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"purpose": "id_verification", "user_id": str(user["_id"])},
    )
    await db_insert_one(db.payment_transactions, {
        "session_id": session.id,
        "purpose": "id_verification",
        "user_id": user["_id"],
        "amount": VERIFICATION_FEE,
        "currency": CURRENCY,
        "payment_status": "initiated",
        "metadata": {},
        "created_at": datetime.utcnow().isoformat(),
    })
    return {"url": session.url, "session_id": session.id}


@app.post("/payments/verify-checkout")
async def verify_checkout_alias(payload: VerifyCheckoutIn, user: dict = Depends(get_current_user)):
    return await verify_checkout(payload, user)


@app.post("/api/payments/identity-checkout")
async def identity_checkout(payload: IdentityCheckoutIn, user: dict = Depends(get_current_user)):
    if user.get("verified"):
        raise HTTPException(status_code=400, detail="Already verified")
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    return_url = f"{payload.origin_url.rstrip('/')}/identity-return?session_id={{SESSION_ID}}"
    try:
        session = stripe.identity.VerificationSession.create(
            type="document",
            metadata={"user_id": str(user["_id"])},
            return_url=return_url,
            options={"document": {"require_id_number": False, "require_live_capture": True, "require_matching_selfie": True}},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await db_insert_one(db.identity_sessions, {
        "session_id": session.id,
        "user_id": user["_id"],
        "status": session.status,
        "created_at": datetime.utcnow().isoformat(),
    })
    return {"url": session.url, "session_id": session.id, "status": session.status}


@app.post("/payments/identity-checkout")
async def identity_checkout_alias(payload: IdentityCheckoutIn, user: dict = Depends(get_current_user)):
    return await identity_checkout(payload, user)


@app.get("/api/payments/identity-status/{session_id}")
async def identity_status(session_id: str, user: dict = Depends(get_current_user)):
    try:
        session = stripe.identity.VerificationSession.retrieve(session_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if str(session.metadata.get("user_id")) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    await db_update_one(db.identity_sessions, {"session_id": session_id}, {"$set": {"status": session.status, "updated_at": datetime.utcnow().isoformat()}})
    if session.status == "verified" and not user.get("verified"):
        await db_update_one(db.users, {"_id": user["_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow().isoformat()}})
    return {"status": session.status, "last_error": getattr(session, "last_error", None)}


@app.get("/api/payments/status/{session_id}")
async def payment_status(session_id: str):
    transaction = await db_find_one(db.payment_transactions, {"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    payment_status = getattr(session, "payment_status", "unknown")
    status_value = "complete" if payment_status == "paid" else "pending"
    await db_update_one(db.payment_transactions, {"session_id": session_id}, {"$set": {"payment_status": payment_status, "status": status_value, "updated_at": datetime.utcnow().isoformat()}})
    if transaction.get("purpose") == "id_verification" and payment_status == "paid" and transaction.get("user_id"):
        await db_update_one(db.users, {"_id": transaction["user_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow().isoformat()}})
    return {"payment_status": payment_status, "status": status_value, "purpose": transaction.get("purpose"), "amount": transaction.get("amount")}


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    event = None
    try:
        if STRIPE_WEBHOOK_SECRET and signature:
            event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        else:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}") from exc
    if event.type == "checkout.session.completed":
        session = event.data.object
        await db_update_one(db.payment_transactions, {"session_id": session.id}, {"$set": {"payment_status": session.payment_status, "updated_at": datetime.utcnow().isoformat()}})
        transaction = await db_find_one(db.payment_transactions, {"session_id": session.id})
        if transaction and transaction.get("purpose") == "id_verification" and session.payment_status == "paid" and transaction.get("user_id"):
            await db_update_one(db.users, {"_id": transaction["user_id"]}, {"$set": {"verified": True, "verified_at": datetime.utcnow().isoformat()}})
    elif event.type.startswith("identity.verification_session"):
        session = event.data.object
        await db_update_one(db.identity_sessions, {"session_id": session.id}, {"$set": {"status": session.status, "updated_at": datetime.utcnow().isoformat()}})
        if session.status == "verified" and session.metadata and session.metadata.get("user_id"):
            await db_update_one(db.users, {"_id": ObjectId(session.metadata["user_id"])}, {"$set": {"verified": True, "verified_at": datetime.utcnow().isoformat()}})
    return {"ok": True}


@app.post("/api/moderation")
async def moderation(payload: ModerateIn):
    if not OPENAI_API_KEY:
        return {"allowed": True, "reason": "Moderation skipped"}
    prompt = (
        "You are a strict content moderator. Reply only with valid JSON: {\"allowed\": true/false, \"reason\": \"...\"}.\n"
        f"Category: {payload.category}\nTitle: {payload.title}\nDescription: {payload.description}"
    )
    def call_openai():
        return openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a strict content moderator for item listings."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=150,
        )
    try:
        response = await asyncio.to_thread(call_openai)
        text = response.choices[0].message["content"].strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(text[start:end+1])
            return {"allowed": bool(data.get("allowed", True)), "reason": str(data.get("reason", ""))}
    except Exception:
        pass
    return {"allowed": True, "reason": "Moderation fallback"}
