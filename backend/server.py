"""ExpireMate API — community urgent-giving platform."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import random
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from dataclasses import dataclass
from types import SimpleNamespace
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
from helpers import (
    admin_email, admin_password, is_admin, make_token, now_utc,
    send_dev_email, build_receipt_pdf, EMAIL_LOG,
)
from email_sender import send_email, render_zip_alert, render_action_email
from push_utils import vapid_public_hex, send_push
import asyncio
import hashlib
import stripe as stripe_sdk

@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: dict | None = None

class StripeCheckout:
    def __init__(self, api_key: str, webhook_url: str | None = None):
        stripe_sdk.api_key = api_key
        self.webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    async def create_checkout_session(self, req: CheckoutSessionRequest):
        amount_cents = int(round(req.amount * 100))
        session = stripe_sdk.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": req.currency,
                    "product_data": {"name": "ExpireMate Payment"},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            metadata=req.metadata or {},
        )
        return SimpleNamespace(session_id=session.id, url=session.url)

    async def get_checkout_status(self, session_id: str):
        session = stripe_sdk.checkout.Session.retrieve(session_id)
        payment_status = getattr(session, "payment_status", "")
        status = "complete" if payment_status == "paid" else "pending"
        return SimpleNamespace(payment_status=payment_status, status=status)

    async def handle_webhook(self, body: bytes, signature: str | None):
        if self.webhook_secret and signature:
            event = stripe_sdk.Webhook.construct_event(body, signature, self.webhook_secret)
        else:
            event = stripe_sdk.Event.construct_from(json.loads(body), stripe_sdk.api_key)
        obj = getattr(event.data, "object", None)
        session_id = getattr(obj, "id", "") if obj else ""
        payment_status = getattr(obj, "payment_status", "unknown") if obj else "unknown"
        return SimpleNamespace(payment_status=payment_status, session_id=session_id)

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
CURRENCY = "cad"


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


def serialize_user(user_doc: dict) -> dict:  # override (also include role/banned/profile)
    from auth_utils import serialize_user as _orig
    base = _orig(user_doc)
    base.update({
        "role": user_doc.get("role", "user"),
        "banned": bool(user_doc.get("banned", False)),
        "email_verified": bool(user_doc.get("email_verified", False)),
        "bio": user_doc.get("bio", ""),
        "avatar_path": user_doc.get("avatar_path"),
    })
    return base


async def auth_user(request: Request):
    user = await get_current_user(request, db)
    if user.get("banned"):
        raise HTTPException(403, "Account suspended. Contact safety@expiremate.com.")
    return user


async def require_admin(request: Request):
    user = await auth_user(request)
    if not is_admin(user):
        raise HTTPException(403, "Admin only")
    return user


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

    # Dedup by content hash — prevent stock-photo / repost scams
    photo_hash = hashlib.sha256(photo_bytes).hexdigest()
    if await db.items.find_one({"photo_hash": photo_hash}):
        raise HTTPException(400, "This exact photo has already been posted. Please upload a fresh photo of the actual item.")

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
        "photo_hash": photo_hash,
        "owner_id": user["_id"], "owner_name": user.get("name", ""),
        "claimed_by": None, "claim_code": None,
        "claimed_at": None, "completed_at": None,
        "created_at": now_iso(), "moderation_reason": mod.get("reason", ""),
    }
    res = await db.items.insert_one(doc)
    doc["_id"] = res.inserted_id
    # Fire-and-forget: notify subscribers
    asyncio.create_task(_notify_zip_subscribers(doc))
    return {"item": item_to_public(doc, str(user["_id"]))}


@api.post("/items/{item_id}/claim")
async def claim_item(item_id: str, request: Request):
    user = await auth_user(request)
    # NOTE: verification NOT required to claim — only to post.
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
        amount=VERIFICATION_FEE, currency=CURRENCY,
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": str(user["_id"]), "purpose": "id_verification"},
    )
    session = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["_id"],
        "purpose": "id_verification", "amount": VERIFICATION_FEE, "currency": CURRENCY,
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
        amount=float(amount), currency=CURRENCY,
        success_url=success_url, cancel_url=cancel_url, metadata=meta,
    )
    session = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["_id"] if user else None,
        "purpose": "donation", "amount": amount, "currency": CURRENCY,
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


# ---------- Auth extras: email verification + password reset (MOCK email) ----------
class EmailIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


class TokenIn(BaseModel):
    token: str


@api.post("/auth/send-verification")
async def send_verification(request: Request):
    user = await auth_user(request)
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    token = make_token("ev")
    await db.email_tokens.insert_one({
        "user_id": user["_id"], "token": token, "purpose": "verify_email",
        "expires_at": (now_utc() + timedelta(hours=24)).isoformat(),
        "used": False, "created_at": now_iso(),
    })
    link = f"{os.environ.get('FRONTEND_URL', '')}/verify-email?token={token}"
    send_dev_email(user["email"], "Verify your ExpireMate email",
                   "Click the link to verify your account.", link=link)
    return {"ok": True, "dev_link": link}


@api.post("/auth/verify-email")
async def verify_email(body: TokenIn):
    tk = await db.email_tokens.find_one({"token": body.token, "purpose": "verify_email", "used": False})
    if not tk:
        raise HTTPException(400, "Invalid or already-used token")
    if tk["expires_at"] < now_utc().isoformat():
        raise HTTPException(400, "Token expired")
    await db.email_tokens.update_one({"_id": tk["_id"]}, {"$set": {"used": True}})
    await db.users.update_one({"_id": tk["user_id"]}, {"$set": {"email_verified": True}})
    return {"ok": True}


@api.post("/auth/forgot-password")
async def forgot_password(body: EmailIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if user:
        token = make_token("pr")
        await db.email_tokens.insert_one({
            "user_id": user["_id"], "token": token, "purpose": "password_reset",
            "expires_at": (now_utc() + timedelta(hours=1)).isoformat(),
            "used": False, "created_at": now_iso(),
        })
        link = f"{os.environ.get('FRONTEND_URL', '')}/reset-password?token={token}"
        send_dev_email(user["email"], "Reset your ExpireMate password",
                       "Click the link to choose a new password (expires in 1 hour).", link=link)
        return {"ok": True, "dev_link": link}
    return {"ok": True}  # don't leak existence


@api.post("/auth/reset-password")
async def reset_password(body: ResetIn):
    tk = await db.email_tokens.find_one({"token": body.token, "purpose": "password_reset", "used": False})
    if not tk:
        raise HTTPException(400, "Invalid or already-used token")
    if tk["expires_at"] < now_utc().isoformat():
        raise HTTPException(400, "Token expired")
    await db.email_tokens.update_one({"_id": tk["_id"]}, {"$set": {"used": True}})
    await db.users.update_one(
        {"_id": tk["user_id"]},
        {"$set": {"password_hash": hash_password(body.new_password)}},
    )
    return {"ok": True}


# ---------- Chat (poster <-> claimer per item) ----------
class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _can_chat(item: dict, user_id: str) -> bool:
    return (str(item["owner_id"]) == user_id or
            (item.get("claimed_by") and str(item["claimed_by"]) == user_id))


@api.get("/items/{item_id}/messages")
async def list_messages(item_id: str, request: Request):
    user = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    item = await db.items.find_one({"_id": oid})
    if not item:
        raise HTTPException(404, "Not found")
    if not _can_chat(item, str(user["_id"])):
        raise HTTPException(403, "Not authorized to view this thread")
    msgs = await db.messages.find({"item_id": oid}).sort("created_at", 1).to_list(500)
    return {
        "messages": [{
            "id": str(m["_id"]),
            "from_user_id": str(m["from_user_id"]),
            "from_name": m.get("from_name", ""),
            "text": m["text"],
            "created_at": m["created_at"],
        } for m in msgs]
    }


@api.post("/items/{item_id}/messages")
async def post_message(item_id: str, body: ChatIn, request: Request):
    user = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    item = await db.items.find_one({"_id": oid})
    if not item:
        raise HTTPException(404, "Not found")
    if item.get("status") not in ("claimed", "active"):
        raise HTTPException(400, "Thread closed")
    if not _can_chat(item, str(user["_id"])):
        raise HTTPException(403, "Only poster or claimer can chat here")
    # Basic PII scrub — strip US phone numbers
    import re
    safe = re.sub(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", "[redacted phone]", body.text)
    doc = {
        "item_id": oid, "from_user_id": user["_id"],
        "from_name": user.get("name", ""), "text": safe.strip(),
        "created_at": now_iso(),
    }
    r = await db.messages.insert_one(doc)
    doc["_id"] = r.inserted_id
    return {"message": {
        "id": str(r.inserted_id), "from_user_id": str(user["_id"]),
        "from_name": user.get("name", ""), "text": safe.strip(),
        "created_at": doc["created_at"],
    }}


# ---------- Tax-receipt PDFs ----------
@api.get("/me/donations")
async def my_donations(request: Request):
    user = await auth_user(request)
    rows = await db.payment_transactions.find({
        "user_id": user["_id"], "purpose": "donation", "payment_status": "paid",
    }).sort("created_at", -1).to_list(200)
    return {
        "donations": [{
            "session_id": r["session_id"],
            "amount": r["amount"],
            "currency": r.get("currency", "usd"),
            "created_at": r.get("created_at"),
            "paid_at": r.get("updated_at") or r.get("created_at"),
        } for r in rows]
    }


@api.get("/donations/{session_id}/receipt")
async def receipt_pdf(session_id: str, request: Request):
    user = await auth_user(request)
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx or tx.get("purpose") != "donation" or tx.get("payment_status") != "paid":
        raise HTTPException(404, "Donation not found")
    if not tx.get("user_id"):
        raise HTTPException(404, "Donation not found")
    if str(tx["user_id"]) != str(user["_id"]) and not is_admin(user):
        raise HTTPException(403, "Not your donation")
    pdf = build_receipt_pdf(
        donor_name=user.get("name", ""),
        donor_email=user.get("email", ""),
        amount=float(tx["amount"]),
        currency=tx.get("currency", "usd"),
        session_id=session_id,
        paid_at=tx.get("updated_at") or tx.get("created_at") or "",
    )
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="expiremate-receipt-{session_id[:10]}.pdf"'})


# ---------- Admin ----------
@api.get("/admin/overview")
async def admin_overview(request: Request):
    await require_admin(request)
    users = await db.users.count_documents({})
    items = await db.items.count_documents({})
    active = await db.items.count_documents({"status": "active"})
    reports = await db.reports.count_documents({})
    banned = await db.users.count_documents({"banned": True})
    don = await db.payment_transactions.count_documents({"purpose": "donation", "payment_status": "paid"})
    return {"users": users, "items": items, "active_items": active,
            "reports": reports, "banned": banned, "donations": don}


@api.get("/admin/reports")
async def admin_reports(request: Request):
    await require_admin(request)
    rows = await db.reports.find({}).sort("created_at", -1).to_list(200)
    out = []
    for r in rows:
        item = await db.items.find_one({"_id": r["item_id"]}) if r.get("item_id") else None
        reporter = await db.users.find_one({"_id": r["reporter_id"]})
        out.append({
            "id": str(r["_id"]),
            "reason": r.get("reason", ""),
            "created_at": r.get("created_at"),
            "item": item_to_public(item) if item else None,
            "reporter_email": reporter.get("email") if reporter else None,
        })
    return {"reports": out}


@api.get("/admin/users")
async def admin_users(request: Request):
    await require_admin(request)
    rows = await db.users.find({}).sort("created_at", -1).to_list(500)
    return {"users": [serialize_user(u) for u in rows]}


@api.post("/admin/users/{user_id}/ban")
async def admin_ban(user_id: str, request: Request):
    await require_admin(request)
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Not found")
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("email") == admin_email():
        raise HTTPException(400, "Cannot ban the admin")
    await db.users.update_one({"_id": oid}, {"$set": {"banned": True}})
    return {"ok": True}


@api.post("/admin/users/{user_id}/unban")
async def admin_unban(user_id: str, request: Request):
    await require_admin(request)
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Not found")
    await db.users.update_one({"_id": oid}, {"$set": {"banned": False}})
    return {"ok": True}


@api.delete("/admin/items/{item_id}")
async def admin_delete_item(item_id: str, request: Request):
    await require_admin(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    await db.items.update_one({"_id": oid}, {"$set": {"status": "removed"}})
    return {"ok": True}


@api.get("/admin/emails")
async def admin_emails(request: Request):
    await require_admin(request)
    return {"emails": EMAIL_LOG[:50]}


# ---------- Profiles, reviews, blocks, watchlist ----------
class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=600)


class ProfileUpdateIn(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=500)


def user_card(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "name": u.get("name", ""),
        "verified": bool(u.get("verified")),
        "avatar_path": u.get("avatar_path"),
        "bio": u.get("bio", ""),
        "joined": u.get("created_at"),
    }


async def _block_filter(user_id) -> dict:
    """Return a Mongo filter clause excluding items where viewer is blocked or has blocked the owner."""
    blocks = await db.user_blocks.find(
        {"$or": [{"blocker_id": user_id}, {"blocked_id": user_id}]}
    ).to_list(500)
    blocked_user_ids = set()
    for b in blocks:
        blocked_user_ids.add(b["blocker_id"])
        blocked_user_ids.add(b["blocked_id"])
    blocked_user_ids.discard(user_id)
    return {"owner_id": {"$nin": list(blocked_user_ids)}} if blocked_user_ids else {}


@api.get("/users/{user_id}/profile")
async def user_profile(user_id: str):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Not found")
    u = await db.users.find_one({"_id": oid})
    if not u:
        raise HTTPException(404, "Not found")
    # Aggregate rating
    pipeline = [
        {"$match": {"reviewee_id": oid}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    avg, count = None, 0
    async for r in db.reviews.aggregate(pipeline):
        avg = float(r.get("avg") or 0)
        count = int(r.get("count") or 0)
    rescued_posted = await db.items.count_documents({"owner_id": oid, "status": "completed"})
    rescued_claimed = await db.items.count_documents({"claimed_by": oid, "status": "completed"})
    return {
        "user": user_card(u),
        "rating_avg": round(avg, 2) if avg else None,
        "rating_count": count,
        "items_rescued": rescued_posted + rescued_claimed,
    }


@api.get("/users/{user_id}/reviews")
async def user_reviews(user_id: str):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Not found")
    rows = await db.reviews.find({"reviewee_id": oid}).sort("created_at", -1).to_list(100)
    out = []
    for r in rows:
        reviewer = await db.users.find_one({"_id": r["reviewer_id"]})
        out.append({
            "id": str(r["_id"]),
            "rating": r["rating"],
            "text": r.get("text", ""),
            "created_at": r.get("created_at"),
            "reviewer": user_card(reviewer) if reviewer else None,
        })
    return {"reviews": out}


@api.post("/items/{item_id}/review")
async def leave_review(item_id: str, body: ReviewIn, request: Request):
    user = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    item = await db.items.find_one({"_id": oid})
    if not item:
        raise HTTPException(404, "Not found")
    if item.get("status") != "completed":
        raise HTTPException(400, "Reviews allowed only after pickup is confirmed")
    is_owner = str(item["owner_id"]) == str(user["_id"])
    is_claimer = item.get("claimed_by") and str(item["claimed_by"]) == str(user["_id"])
    if not (is_owner or is_claimer):
        raise HTTPException(403, "Only the poster or claimer can leave a review")
    reviewee_id = item["claimed_by"] if is_owner else item["owner_id"]
    if not reviewee_id:
        raise HTTPException(400, "No counterparty to review")
    existing = await db.reviews.find_one({
        "item_id": oid, "reviewer_id": user["_id"],
    })
    if existing:
        raise HTTPException(400, "Already reviewed this pickup")
    await db.reviews.insert_one({
        "item_id": oid,
        "reviewer_id": user["_id"],
        "reviewee_id": reviewee_id,
        "rating": body.rating,
        "text": body.text.strip(),
        "created_at": now_iso(),
    })
    return {"ok": True}


@api.patch("/me/profile")
async def update_profile(body: ProfileUpdateIn, request: Request):
    user = await auth_user(request)
    update = {}
    if body.bio is not None:
        update["bio"] = body.bio.strip()
    if update:
        await db.users.update_one({"_id": user["_id"]}, {"$set": update})
    fresh = await db.users.find_one({"_id": user["_id"]})
    return {"user": serialize_user(fresh)}


@api.post("/me/avatar")
async def upload_avatar(request: Request, photo: UploadFile = File(...)):
    user = await auth_user(request)
    data = await photo.read()
    if len(data) > 3 * 1024 * 1024:
        raise HTTPException(400, "Avatar too large (max 3MB)")
    ext = (photo.filename.split(".")[-1] if photo.filename and "." in photo.filename else "jpg").lower()
    path = f"{APP_NAME}/avatars/{str(user['_id'])}/{uuid.uuid4()}.{ext}"
    try:
        result = put_object(path, data, photo.content_type or "image/jpeg")
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"avatar_path": result["path"]}})
    except Exception as e:
        logger.error(f"avatar upload failed: {e}")
        raise HTTPException(500, "Upload failed")
    fresh = await db.users.find_one({"_id": user["_id"]})
    return {"user": serialize_user(fresh)}


# ---------- Block / unblock ----------
@api.post("/users/{user_id}/block")
async def block_user(user_id: str, request: Request):
    me = await auth_user(request)
    try:
        target = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Not found")
    if str(target) == str(me["_id"]):
        raise HTTPException(400, "Can't block yourself")
    await db.user_blocks.update_one(
        {"blocker_id": me["_id"], "blocked_id": target},
        {"$setOnInsert": {"blocker_id": me["_id"], "blocked_id": target,
                          "created_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True}


@api.delete("/users/{user_id}/block")
async def unblock_user(user_id: str, request: Request):
    me = await auth_user(request)
    try:
        target = ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "Not found")
    await db.user_blocks.delete_one({"blocker_id": me["_id"], "blocked_id": target})
    return {"ok": True}


@api.get("/me/blocks")
async def my_blocks(request: Request):
    me = await auth_user(request)
    rows = await db.user_blocks.find({"blocker_id": me["_id"]}).to_list(200)
    out = []
    for r in rows:
        u = await db.users.find_one({"_id": r["blocked_id"]})
        if u:
            out.append(user_card(u))
    return {"blocks": out}


# ---------- Watchlist ----------
@api.post("/items/{item_id}/watch")
async def watch_item(item_id: str, request: Request):
    me = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    await db.watches.update_one(
        {"user_id": me["_id"], "item_id": oid},
        {"$setOnInsert": {"user_id": me["_id"], "item_id": oid,
                          "created_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True}


@api.delete("/items/{item_id}/watch")
async def unwatch_item(item_id: str, request: Request):
    me = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    await db.watches.delete_one({"user_id": me["_id"], "item_id": oid})
    return {"ok": True}


@api.get("/me/watchlist")
async def my_watchlist(request: Request):
    me = await auth_user(request)
    rows = await db.watches.find({"user_id": me["_id"]}).sort("created_at", -1).to_list(200)
    items = []
    for w in rows:
        it = await db.items.find_one({"_id": w["item_id"]})
        if it:
            items.append(item_to_public(it, str(me["_id"])))
    return {"items": items}


# ---------- Pickup reminder background loop ----------
_reminder_task = None


async def _pickup_reminder_loop():
    """Email both parties if an item has been claimed >24h with no confirm."""
    while True:
        try:
            cutoff = (now_utc() - timedelta(hours=24)).isoformat()
            cursor = db.items.find({
                "status": "claimed",
                "claimed_at": {"$lt": cutoff},
                "reminder_sent_at": {"$exists": False},
            })
            frontend = os.environ.get("FRONTEND_URL", "").rstrip("/") or "https://expiremate.com"
            async for it in cursor:
                owner = await db.users.find_one({"_id": it["owner_id"]})
                claimer = await db.users.find_one({"_id": it["claimed_by"]}) if it.get("claimed_by") else None
                link = f"{frontend}/items/{it['_id']}"
                for u in [owner, claimer]:
                    if not u or u.get("banned"):
                        continue
                    try:
                        await asyncio.to_thread(send_email,
                            to=u["email"],
                            subject=f"Reminder: pickup pending for '{it.get('title','item')}'",
                            html=render_action_email(
                                heading="Did the pickup happen?",
                                body=f"It's been a day since this item was claimed. If you've met up, confirm the pickup with the 4-digit code. Otherwise, message the other party in the in-app chat.",
                                cta_text="Open pickup page",
                                cta_url=link,
                            ),
                            link=link,
                        )
                    except Exception as e:
                        logger.warning(f"reminder email failed: {e}")
                await db.items.update_one(
                    {"_id": it["_id"]},
                    {"$set": {"reminder_sent_at": now_iso()}},
                )
        except Exception as e:
            logger.error(f"[pickup-reminder] {e}")
        await asyncio.sleep(60 * 60)  # 1 hour




_auto_expire_task = None
stripe_sdk.api_key = os.environ.get("STRIPE_API_KEY", "")


async def _notify_zip_subscribers(item: dict):
    """Email + web-push everyone subscribed to this item's ZIP code."""
    zip_code = item.get("zip_code")
    if not zip_code:
        return
    frontend = os.environ.get("FRONTEND_URL", "").rstrip("/") or "https://expiremate.com"
    item_url = f"{frontend}/items/{item['_id']}"
    days = 0
    try:
        from datetime import date
        days = (date.fromisoformat(item.get("expiration_date", "")) - date.today()).days
    except Exception:
        days = 0
    title = item.get("title", "New item")
    category = item.get("category", "")

    async for sub in db.zip_subscriptions.find({"zip_code": zip_code}):
        # Skip the poster themselves
        if sub.get("user_id") and item.get("owner_id") and str(sub["user_id"]) == str(item["owner_id"]):
            continue
        user = await db.users.find_one({"_id": sub["user_id"]})
        if not user or user.get("banned"):
            continue
        try:
            html = render_zip_alert(item_title=title, item_url=item_url,
                                    category=category, days_left=days, zip_code=zip_code)
            await asyncio.to_thread(send_email, to=user["email"],
                                    subject=f"New {category} in {zip_code} — expires soon",
                                    html=html, link=item_url)
        except Exception as e:
            logger.warning(f"zip email failed: {e}")

    # Web push
    async for push_sub in db.push_subscriptions.find({"zip_codes": zip_code}):
        try:
            await asyncio.to_thread(send_push, push_sub["subscription"], {
                "title": f"New item in {zip_code}",
                "body": f"{title} ({category}) — expires {'in ' + str(days) + 'd' if days > 0 else 'today'}",
                "url": f"/items/{item['_id']}",
            })
        except Exception as e:
            logger.warning(f"push send failed: {e}")


# ---------- Impact + streaks + donor-of-month ----------
@api.get("/stats/impact")
async def stats_impact():
    total_rescued = await db.items.count_documents({"status": "completed"})
    today_iso = now_utc().date().isoformat()
    week_ago = (now_utc() - timedelta(days=7)).date().isoformat()
    weekly = await db.items.count_documents({"status": "completed", "completed_at": {"$gte": week_ago}})
    # Rough estimate: 1.2 lbs per rescued item
    pounds = round(total_rescued * 1.2, 1)
    return {"items_rescued_total": total_rescued, "items_rescued_week": weekly,
            "pounds_saved": pounds, "today": today_iso}


@api.get("/stats/donor-of-month")
async def stats_donor_of_month():
    month_start = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    pipeline = [
        {"$match": {"purpose": "donation", "payment_status": "paid",
                    "created_at": {"$gte": month_start},
                    "anonymous": {"$ne": True}}},
        {"$group": {"_id": "$metadata.donor_name", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}}, {"$limit": 1},
    ]
    async for r in db.payment_transactions.aggregate(pipeline):
        return {"name": r["_id"] or "Anonymous", "total": round(float(r["total"]), 2)}
    return {"name": None, "total": 0}


@api.get("/me/stats")
async def my_stats(request: Request):
    user = await auth_user(request)
    rescued_posted = await db.items.count_documents({"owner_id": user["_id"], "status": "completed"})
    rescued_claimed = await db.items.count_documents({"claimed_by": user["_id"], "status": "completed"})
    donations_count = await db.payment_transactions.count_documents({
        "user_id": user["_id"], "purpose": "donation", "payment_status": "paid"})

    badges = []
    total_rescued = rescued_posted + rescued_claimed
    if total_rescued >= 1: badges.append({"key": "first_rescue", "label": "First Rescue", "emoji": "🌱"})
    if total_rescued >= 5: badges.append({"key": "five", "label": "5 Items Saved", "emoji": "🌟"})
    if total_rescued >= 25: badges.append({"key": "twentyfive", "label": "25 Saved", "emoji": "🏆"})
    if donations_count >= 1: badges.append({"key": "donor", "label": "Donor", "emoji": "💛"})
    if user.get("verified"): badges.append({"key": "verified", "label": "Verified", "emoji": "✓"})
    return {
        "rescued_posted": rescued_posted, "rescued_claimed": rescued_claimed,
        "total_rescued": total_rescued, "donations_count": donations_count,
        "badges": badges,
    }


# ---------- Item bump ----------
@api.post("/items/{item_id}/bump")
async def bump_item(item_id: str, request: Request):
    user = await auth_user(request)
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(404, "Not found")
    item = await db.items.find_one({"_id": oid})
    if not item:
        raise HTTPException(404, "Not found")
    if str(item["owner_id"]) != str(user["_id"]):
        raise HTTPException(403, "Only the owner can bump")
    if item.get("status") != "active":
        raise HTTPException(400, "Only active items can be bumped")
    last_bump = item.get("bumped_at") or item.get("created_at")
    if last_bump and (now_utc() - datetime.fromisoformat(last_bump.replace("Z", "+00:00"))).total_seconds() < 24 * 3600:
        raise HTTPException(429, "Already bumped in the last 24h")
    await db.items.update_one(
        {"_id": oid},
        {"$set": {"created_at": now_iso(), "bumped_at": now_iso()}},
    )
    return {"ok": True}


# ---------- ZIP subscriptions (email + push opt-in) ----------
class ZipSubIn(BaseModel):
    zip_code: str = Field(min_length=3, max_length=10)


@api.post("/subscriptions/zip")
async def subscribe_zip(body: ZipSubIn, request: Request):
    user = await auth_user(request)
    await db.zip_subscriptions.update_one(
        {"user_id": user["_id"], "zip_code": body.zip_code},
        {"$setOnInsert": {"user_id": user["_id"], "zip_code": body.zip_code,
                          "created_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True}


@api.delete("/subscriptions/zip/{zip_code}")
async def unsubscribe_zip(zip_code: str, request: Request):
    user = await auth_user(request)
    await db.zip_subscriptions.delete_one({"user_id": user["_id"], "zip_code": zip_code})
    return {"ok": True}


@api.get("/me/subscriptions")
async def my_subscriptions(request: Request):
    user = await auth_user(request)
    rows = await db.zip_subscriptions.find({"user_id": user["_id"]}).to_list(50)
    return {"zips": [r["zip_code"] for r in rows]}


# ---------- Web push ----------
@api.get("/push/vapid-public-key")
async def push_vapid_key():
    return {"public_key_hex": vapid_public_hex()}


class PushSubIn(BaseModel):
    subscription: dict
    zip_codes: list[str] = []


@api.post("/push/subscribe")
async def push_subscribe(body: PushSubIn, request: Request):
    user = await auth_user(request)
    await db.push_subscriptions.update_one(
        {"user_id": user["_id"], "subscription.endpoint": body.subscription.get("endpoint")},
        {"$set": {
            "user_id": user["_id"],
            "subscription": body.subscription,
            "zip_codes": body.zip_codes or ([user.get("zip_code")] if user.get("zip_code") else []),
            "updated_at": now_iso(),
        }},
        upsert=True,
    )
    return {"ok": True}


# ---------- Stripe Identity ----------
class IdentityCheckoutIn(BaseModel):
    origin_url: str


@api.post("/payments/identity-checkout")
async def create_identity_checkout(body: IdentityCheckoutIn, request: Request):
    user = await auth_user(request)
    if user.get("verified"):
        raise HTTPException(400, "Already verified")
    if not stripe_sdk.api_key:
        raise HTTPException(500, "Stripe not configured")
    origin = body.origin_url.rstrip("/")
    return_url = f"{origin}/identity-return?session_id={{SESSION_ID}}"
    try:
        session = stripe_sdk.identity.VerificationSession.create(
            type="document",
            metadata={"user_id": str(user["_id"])},
            return_url=return_url,
            options={"document": {"require_id_number": False,
                                  "require_live_capture": True,
                                  "require_matching_selfie": True}},
        )
    except Exception as e:
        logger.error(f"identity create failed: {e}")
        raise HTTPException(502, f"Stripe Identity error: {e}")
    await db.identity_sessions.insert_one({
        "session_id": session["id"], "user_id": user["_id"],
        "status": session["status"], "created_at": now_iso(),
    })
    return {"url": session["url"], "session_id": session["id"], "status": session["status"]}


@api.get("/payments/identity-status/{session_id}")
async def identity_status(session_id: str, request: Request):
    user = await auth_user(request)
    try:
        session = stripe_sdk.identity.VerificationSession.retrieve(session_id)
    except Exception as e:
        raise HTTPException(404, f"Session not found: {e}")
    meta = session.get("metadata") or {}
    if meta.get("user_id") != str(user["_id"]) and not is_admin(user):
        raise HTTPException(403, "Not your session")
    status_value = session.get("status", "unknown")
    await db.identity_sessions.update_one(
        {"session_id": session_id}, {"$set": {"status": status_value, "updated_at": now_iso()}}
    )
    if status_value == "verified" and not user.get("verified"):
        await db.users.update_one({"_id": user["_id"]},
                                   {"$set": {"verified": True, "verified_at": now_iso()}})
    return {"status": status_value, "last_error": session.get("last_error")}





async def _auto_expire_loop():
    while True:
        try:
            today = now_utc().date().isoformat()
            # Mark items whose expiration_date < today as expired (active or claimed)
            res = await db.items.update_many(
                {"status": {"$in": ["active", "claimed"]},
                 "expiration_date": {"$lt": today}},
                {"$set": {"status": "expired", "expired_at": now_iso()}},
            )
            if res.modified_count:
                logger.info(f"[auto-expire] marked {res.modified_count} items expired")
        except Exception as e:
            logger.error(f"[auto-expire] {e}")
        await asyncio.sleep(30 * 60)  # 30 minutes



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
    await db.items.create_index("expiration_date")
    await db.items.create_index("photo_hash", sparse=True)
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.messages.create_index([("item_id", 1), ("created_at", 1)])
    await db.email_tokens.create_index("token", unique=True)
    await db.reviews.create_index([("reviewee_id", 1), ("created_at", -1)])
    await db.reviews.create_index([("item_id", 1), ("reviewer_id", 1)], unique=True)
    await db.user_blocks.create_index([("blocker_id", 1), ("blocked_id", 1)], unique=True)
    await db.watches.create_index([("user_id", 1), ("item_id", 1)], unique=True)
    init_storage()

    admin_em = admin_email()
    if not await db.users.find_one({"email": admin_em}):
        await db.users.insert_one({
            "email": admin_em,
            "password_hash": hash_password(admin_password()),
            "name": "ExpireMate Admin",
            "zip_code": "",
            "verified": True,
            "email_verified": True,
            "role": "admin",
            "created_at": now_iso(),
        })
        logger.info(f"[seed] admin created: {admin_em}")
    else:
        await db.users.update_one(
            {"email": admin_em},
            {"$set": {"role": "admin", "verified": True, "email_verified": True}},
        )

    global _auto_expire_task, _reminder_task
    _auto_expire_task = asyncio.create_task(_auto_expire_loop())
    _reminder_task = asyncio.create_task(_pickup_reminder_loop())

    try:
        Path("/app/memory").mkdir(exist_ok=True)
        creds = f"""# ExpireMate Test Credentials

## Admin
- {admin_em} / {admin_password()}  (login at /login, then visit /admin)

## Test Users (created during testing)
- testuser@expiremate.com / Test1234

## Auth Endpoints
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET  /api/auth/me
- POST /api/auth/forgot-password / /api/auth/reset-password
- POST /api/auth/send-verification / /api/auth/verify-email

Cookies: access_token (httpOnly, samesite=none, secure=true)
Also accepts `Authorization: Bearer <token>` headers.
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
    global _auto_expire_task, _reminder_task
    if _auto_expire_task:
        _auto_expire_task.cancel()
    if _reminder_task:
        _reminder_task.cancel()
    client.close()
