"""ExpireMate API — community urgent-giving platform."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Form
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

from auth_utils import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, serialize_user, get_current_user,
)
from storage_utils import init_storage, put_object, get_object, APP_NAME
from llm_utils import moderate_item

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="ExpireMate API")
api = APIRouter(prefix="/api")

CATEGORIES = ["Food", "Sealed Medicine", "Pet", "Cleaning", "Other"]
DONATION_PRESETS = {"three": 3.00, "five": 5.00, "ten": 10.00}
DONATION_GOAL = 20000.00
VERIFICATION_FEE = 2.00


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    zip_code: str = Field(default="")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class DonationCheckoutIn(BaseModel):
    preset: Optional[str] = None
    custom_amount: Optional[float] = None
    origin_url: str
    anonymous: bool = False


class ClaimCodeIn(BaseModel):
    code: str


class VerifyCheckoutIn(BaseModel):
    origin_url: str


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_stripe(host_url: str) -> StripeCheckout:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(500, "Stripe not configured")
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


def item_to_public(doc, viewer_id=None):
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title"),
        "description": doc.get("description", ""),
        "category": doc.get("category"),
        "expiration_date": doc.get("expiration_date", ""),
        "quantity": doc.get("quantity", "1"),
        "zip_code": doc.get("zip_code"),
        "meetup_suggestion": doc.get("meetup_suggestion", ""),
        "image_path": doc.get("image_path"),
        "status": doc.get("status", "active"),
        "owner_id": str(doc["owner_id"]),
        "owner_name": doc.get("owner_name", ""),
        "claimed_by": str(doc["claimed_by"]) if doc.get("claimed_by") else None,
        "claimed_at": doc.get("claimed_at"),
        "completed_at": doc.get("completed_at"),
        "created_at": doc.get("created_at"),
        "is_owner": viewer_id is not None and str(doc["owner_id"]) == viewer_id,
        "is_claimer": bool(viewer_id and doc.get("claimed_by") and str(doc["claimed_by"]) == viewer_id),
    }


async def auth_user(request: Request):
    return await get_current_user(request, db)


# ---------- Auth ----------
@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "zip_code": body.zip_code,
        "verified": False,
        "role": "user",
        "created_at": now_iso(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    access = create_access_token(str(result.inserted_id), email)
    refresh = create_refresh_token(str(result.inserted_id))
    set_auth_cookies(response, access, refresh)
    return {"user": serialize_user(doc), "token": access}


@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    access = create_access_token(str(user["_id"]), email)
    refresh = create_refresh_token(str(user["_id"]))
    set_auth_cookies(response, access, refresh)
    return {"user": serialize_user(user), "token": access}


@api.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/auth/me")
async def me(request: Request):
    user = await auth_user(request)
    return {"user": serialize_user(user)}


# ---------- Items ----------
@api.get("/items")
async def list_items(category: Optional[str] = None, zip_code: Optional[str] = None, status: Optional[str] = "active"):
    query = {}
    if status:
        query["status"] = status
    if category and category != "All":
        query["category"] = category
    if zip_code:
        query["zip_code"] = zip_code
    items = await db.items.find(query).sort("created_at", -1).to_list(200)
    return {"items": [item_to_public(i) for i in items]}


@api.get("/items/{item_id}")
async def get_item(item_id: str, request: Request):
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.items.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    viewer_id = None
    try:
        u = await auth_user(request)
        viewer_id = str(u["_id"])
    except Exception:
        pass
    return {"item": item_to_public(doc, viewer_id)}


@api.post("/items")
async def create_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    expiration_date: str = Form(...),
    quantity: str = Form("1"),
    zip_code: str = Form(...),
    meetup_suggestion: str = Form(""),
    photo: UploadFile = File(...),
):
    user = await auth_user(request)
    if not user.get("verified"):
        raise HTTPException(403, "ID verification required to post items")
    if category not in CATEGORIES:
        raise HTTPException(400, "Invalid category")

    mod = await moderate_item(title, description, category)
    if not mod["allowed"]:
        raise HTTPException(400, f"Item blocked by safety check: {mod['reason']}")

    photo_bytes = await photo.read()
    if len(photo_bytes) > 5 * 1024 * 1024:
        raise HTTPException(400, "Photo too large (max 5MB)")
    ext = (photo.filename.split(".")[-1] if photo.filename and "." in photo.filename else "jpg").lower()
    path = f"{APP_NAME}/items/{str(user['_id'])}/{uuid.uuid4()}.{ext}"
    try:
        result = put_object(path, photo_bytes, photo.content_type or "image/jpeg")
        image_path = result["path"]
    except Exception as e:
        logger.error(f"Photo upload failed: {e}")
        raise HTTPException(500, "Photo upload failed")

    doc = {
        "title": title, "description": description, "category": category,
        "expiration_date": expiration_date, "quantity": quantity,
        "zip_code": zip_code,
        "meetup_suggestion": meetup_suggestion or "Suggested: public grocery store parking lot",
        "image_path": image_path, "status": "active",
        "owner_id": user["_id"], "owner_name": user.get("name", ""),
        "claimed_by": None, "claim_code": None,
        "claimed_at": None, "completed_at": None,
        "created_at": now_iso(), "moderation_reason": mod.get("reason", ""),
    }
    res = await db.items.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {"item": item_to_public(doc, str(user["_id"]))}


@api.post("/items/{item_id}/claim")
async def claim_item(item_id: str, request: Request):
    user = await auth_user(request)
    if not user.get("verified"):
        raise HTTPException(403, "ID verification required to claim items")
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.items.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc.get("status") != "active":
        raise HTTPException(400, "Item already claimed")
    if str(doc["owner_id"]) == str(user["_id"]):
        raise HTTPException(400, "Cannot claim your own item")
    code = f"{random.randint(0, 9999):04d}"
    await db.items.update_one(
        {"_id": oid},
        {"$set": {"status": "claimed", "claimed_by": user["_id"],
                  "claim_code": code, "claimed_at": now_iso()}},
    )
    return {"claim_code": code, "message": "Show this code to the poster at pickup"}


@api.post("/items/{item_id}/confirm")
async def confirm_pickup(item_id: str, body: ClaimCodeIn, request: Request):
    user = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.items.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if str(doc["owner_id"]) != str(user["_id"]):
        raise HTTPException(403, "Only the poster can confirm pickup")
    if doc.get("claim_code") != body.code.strip():
        raise HTTPException(400, "Incorrect claim code")
    await db.items.update_one(
        {"_id": oid},
        {"$set": {"status": "completed", "completed_at": now_iso()}},
    )
    return {"ok": True, "message": "Pickup confirmed!"}


@api.post("/items/{item_id}/report")
async def report_item(item_id: str, request: Request, reason: str = Form(...)):
    user = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    await db.reports.insert_one({
        "item_id": oid, "reporter_id": user["_id"],
        "reason": reason, "created_at": now_iso(),
    })
    return {"ok": True}


@api.get("/me/items")
async def my_items(request: Request):
    user = await auth_user(request)
    posts = await db.items.find({"owner_id": user["_id"]}).sort("created_at", -1).to_list(100)
    claims = await db.items.find({"claimed_by": user["_id"]}).sort("claimed_at", -1).to_list(100)
    uid = str(user["_id"])
    return {
        "posts": [item_to_public(i, uid) for i in posts],
        "claims": [item_to_public(i, uid) for i in claims],
    }


# ---------- File serving (public for posted item photos) ----------
@api.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        logger.error(f"File fetch failed for {path}: {e}")
        raise HTTPException(404, "File not found")


# ---------- Payments ----------
@api.post("/payments/verify-checkout")
async def create_verify_checkout(body: VerifyCheckoutIn, request: Request):
    user = await auth_user(request)
    if user.get("verified"):
        raise HTTPException(400, "Already verified")
    origin = body.origin_url.rstrip("/")
    host_url = str(request.base_url)
    stripe = get_stripe(host_url)
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=verify"
    cancel_url = f"{origin}/verify"
    req = CheckoutSessionRequest(
        amount=VERIFICATION_FEE, currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": str(user["_id"]), "purpose": "id_verification"},
    )
    session = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["_id"],
        "purpose": "id_verification", "amount": VERIFICATION_FEE, "currency": "usd",
        "payment_status": "initiated",
        "metadata": {"user_id": str(user["_id"]), "purpose": "id_verification"},
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api.post("/payments/donate-checkout")
async def create_donate_checkout(body: DonationCheckoutIn, request: Request):
    user = None
    try:
        user = await auth_user(request)
    except Exception:
        pass

    amount = None
    if body.preset and body.preset in DONATION_PRESETS:
        amount = DONATION_PRESETS[body.preset]
    elif body.preset == "custom" and body.custom_amount:
        amt = float(body.custom_amount)
        if amt < 1 or amt > 1000:
            raise HTTPException(400, "Custom donation must be $1–$1000")
        amount = round(amt, 2)
    else:
        raise HTTPException(400, "Invalid donation amount")

    origin = body.origin_url.rstrip("/")
    host_url = str(request.base_url)
    stripe = get_stripe(host_url)
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=donate"
    cancel_url = f"{origin}/donate"
    meta = {"purpose": "donation", "anonymous": "true" if body.anonymous else "false"}
    if user:
        meta["user_id"] = str(user["_id"])
        meta["donor_name"] = user.get("name", "")
    req = CheckoutSessionRequest(
        amount=float(amount), currency="usd",
        success_url=success_url, cancel_url=cancel_url, metadata=meta,
    )
    session = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["_id"] if user else None,
        "purpose": "donation", "amount": amount, "currency": "usd",
        "payment_status": "initiated", "metadata": meta,
        "anonymous": body.anonymous, "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request):
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    if tx.get("payment_status") == "paid":
        return {"payment_status": "paid", "status": "complete",
                "purpose": tx["purpose"], "amount": tx["amount"]}

    host_url = str(request.base_url)
    stripe = get_stripe(host_url)
    status = await stripe.get_checkout_status(session_id)

    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status, "status": status.status,
                  "updated_at": now_iso()}},
    )

    if status.payment_status == "paid" and tx.get("payment_status") != "paid":
        if tx["purpose"] == "id_verification" and tx.get("user_id"):
            await db.users.update_one(
                {"_id": tx["user_id"]},
                {"$set": {"verified": True, "verified_at": now_iso()}},
            )

    return {"payment_status": status.payment_status, "status": status.status,
            "purpose": tx["purpose"], "amount": tx["amount"]}


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    stripe = get_stripe(str(request.base_url))
    try:
        ev = await stripe.handle_webhook(body, request.headers.get("Stripe-Signature"))
    except Exception as e:
        logger.error(f"Webhook err: {e}")
        return {"ok": False}
    if ev.payment_status == "paid":
        await db.payment_transactions.update_one(
            {"session_id": ev.session_id},
            {"$set": {"payment_status": "paid", "updated_at": now_iso()}},
        )
        tx = await db.payment_transactions.find_one({"session_id": ev.session_id})
        if tx and tx["purpose"] == "id_verification" and tx.get("user_id"):
            await db.users.update_one(
                {"_id": tx["user_id"]},
                {"$set": {"verified": True, "verified_at": now_iso()}},
            )
    return {"ok": True}


# ---------- Donations stats ----------
@api.get("/donations/stats")
async def donation_stats():
    pipeline = [
        {"$match": {"purpose": "donation", "payment_status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    raised, count = 0.0, 0
    async for row in db.payment_transactions.aggregate(pipeline):
        raised = float(row.get("total", 0))
        count = int(row.get("count", 0))
    return {
        "raised": round(raised, 2), "goal": DONATION_GOAL, "donor_count": count,
        "percent": round((raised / DONATION_GOAL) * 100, 2) if DONATION_GOAL else 0,
    }


@api.get("/donations/leaderboard")
async def leaderboard():
    pipeline = [
        {"$match": {"purpose": "donation", "payment_status": "paid"}},
        {"$group": {
            "_id": {"name": "$metadata.donor_name", "anon": "$anonymous"},
            "total": {"$sum": "$amount"}, "count": {"$sum": 1},
        }},
        {"$sort": {"total": -1}}, {"$limit": 25},
    ]
    rows = []
    async for r in db.payment_transactions.aggregate(pipeline):
        name = r["_id"].get("name") or "Anonymous"
        anon = r["_id"].get("anon", False)
        rows.append({
            "name": "Anonymous" if anon or not name else name,
            "total": round(float(r["total"]), 2), "count": int(r["count"]),
        })
    return {"leaderboard": rows}


@api.get("/config")
async def config():
    return {
        "categories": CATEGORIES, "donation_presets": DONATION_PRESETS,
        "donation_goal": DONATION_GOAL, "verification_fee": VERIFICATION_FEE,
    }


@api.get("/")
async def root():
    return {"message": "ExpireMate API", "status": "live"}


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.items.create_index("status")
    await db.items.create_index("category")
    await db.items.create_index("zip_code")
    await db.payment_transactions.create_index("session_id", unique=True)
    init_storage()
    try:
        Path("/app/memory").mkdir(exist_ok=True)
        creds = """# ExpireMate Test Credentials

## Test Users (created during testing)
- Test user: testuser@expiremate.com / Test1234

## Auth Endpoints
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET  /api/auth/me

Cookies: access_token (httpOnly, samesite=none, secure=true)
For testing without cross-site cookies, the API also returns `token` in the JSON
response and accepts `Authorization: Bearer <token>` headers.
"""
        Path("/app/memory/test_credentials.md").write_text(creds)
    except Exception as e:
        logger.warning(f"creds write failed: {e}")


app.include_router(api)

frontend_url = os.environ.get("FRONTEND_URL")
origins = [frontend_url] if frontend_url else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
