"""Tests for iteration-2 features: admin, password reset, email verify, chat, auto-expire, receipts."""
import os, time, asyncio, pytest, requests
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://savefood-college.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mongo[os.environ.get("DB_NAME", "test_database")]

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@expiremate.com")
ADMIN_PW = os.environ.get("ADMIN_PASSWORD", "ExpireMate2026!")

TS = int(time.time())
POSTER = {"email": f"poster_{TS}@expiremate.com", "password": "Test1234", "name": "Poster", "zip_code": "10001"}
CLAIMER = {"email": f"claimer_{TS}@expiremate.com", "password": "Test1234", "name": "Claimer", "zip_code": "10001"}
OTHER = {"email": f"other_{TS}@expiremate.com", "password": "Test1234", "name": "Other", "zip_code": "10001"}

S = {}

def H(t): return {"Authorization": f"Bearer {t}"}


def test_00_setup_admin_and_users():
    # admin login
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, f"admin login failed: {r.text}"
    d = r.json()
    S["admin_t"] = d["token"]
    S["admin_id"] = d["user"]["id"]
    assert d["user"]["role"] == "admin"
    assert d["user"]["email_verified"] is True

    # users
    for u, k in [(POSTER, "poster"), (CLAIMER, "claimer"), (OTHER, "other")]:
        r = requests.post(f"{API}/auth/register", json=u)
        assert r.status_code == 200, r.text
        S[f"{k}_t"] = r.json()["token"]
        S[f"{k}_id"] = r.json()["user"]["id"]
        db.users.update_one({"_id": ObjectId(S[f"{k}_id"])}, {"$set": {"verified": True}})


# ---------- Admin ----------
def test_01_admin_overview():
    r = requests.get(f"{API}/admin/overview", headers=H(S["admin_t"]))
    assert r.status_code == 200
    d = r.json()
    for k in ["users", "items", "active_items", "reports", "banned", "donations"]:
        assert k in d


def test_02_admin_endpoints_forbid_non_admin():
    r = requests.get(f"{API}/admin/overview", headers=H(S["poster_t"]))
    assert r.status_code == 403
    r2 = requests.get(f"{API}/admin/users", headers=H(S["poster_t"]))
    assert r2.status_code == 403


def test_03_admin_users_list():
    r = requests.get(f"{API}/admin/users", headers=H(S["admin_t"]))
    assert r.status_code == 200
    emails = [u["email"] for u in r.json()["users"]]
    assert POSTER["email"] in emails


def test_04_admin_cannot_ban_admin():
    r = requests.post(f"{API}/admin/users/{S['admin_id']}/ban", headers=H(S["admin_t"]))
    assert r.status_code == 400


def test_05_admin_ban_unban_other_user():
    # ban OTHER user
    r = requests.post(f"{API}/admin/users/{S['other_id']}/ban", headers=H(S["admin_t"]))
    assert r.status_code == 200

    # banned user gets 403 on authenticated endpoints
    r2 = requests.get(f"{API}/auth/me", headers=H(S["other_t"]))
    assert r2.status_code == 403, f"banned should be 403, got {r2.status_code}"
    assert "suspended" in r2.text.lower() or "banned" in r2.text.lower()

    # unban
    r3 = requests.post(f"{API}/admin/users/{S['other_id']}/unban", headers=H(S["admin_t"]))
    assert r3.status_code == 200
    r4 = requests.get(f"{API}/auth/me", headers=H(S["other_t"]))
    assert r4.status_code == 200


def test_06_admin_emails_outbox():
    r = requests.get(f"{API}/admin/emails", headers=H(S["admin_t"]))
    assert r.status_code == 200
    assert "emails" in r.json()


# ---------- Password reset ----------
def test_07_forgot_password_unknown_returns_ok_no_link():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": f"nonexistent_{TS}@nowhere.com"})
    assert r.status_code == 200
    d = r.json()
    assert d.get("ok") is True
    assert "dev_link" not in d  # no enumeration leak


def test_08_forgot_password_existing_returns_link():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": POSTER["email"]})
    assert r.status_code == 200
    d = r.json()
    assert d.get("ok") is True
    assert "dev_link" in d and "token=" in d["dev_link"]
    S["reset_token"] = d["dev_link"].split("token=")[-1]

    # token row written
    tk = db.email_tokens.find_one({"token": S["reset_token"], "purpose": "password_reset"})
    assert tk is not None
    assert tk["used"] is False


def test_09_reset_password_works():
    new_pw = "NewPass5678"
    r = requests.post(f"{API}/auth/reset-password", json={"token": S["reset_token"], "new_password": new_pw})
    assert r.status_code == 200

    # old fails
    r2 = requests.post(f"{API}/auth/login", json={"email": POSTER["email"], "password": POSTER["password"]})
    assert r2.status_code == 401

    # new works
    r3 = requests.post(f"{API}/auth/login", json={"email": POSTER["email"], "password": new_pw})
    assert r3.status_code == 200
    POSTER["password"] = new_pw
    S["poster_t"] = r3.json()["token"]


def test_10_expired_reset_token_rejected():
    # generate a token, expire it, then attempt
    r = requests.post(f"{API}/auth/forgot-password", json={"email": POSTER["email"]})
    token = r.json()["dev_link"].split("token=")[-1]
    db.email_tokens.update_one(
        {"token": token},
        {"$set": {"expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}},
    )
    r2 = requests.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "AnyPass1234"})
    assert r2.status_code == 400


# ---------- Email verification ----------
def test_11_send_and_verify_email():
    r = requests.post(f"{API}/auth/send-verification", headers=H(S["poster_t"]))
    assert r.status_code == 200
    d = r.json()
    assert d.get("ok") is True
    assert "dev_link" in d, f"expected dev_link, got {d}"
    token = d["dev_link"].split("token=")[-1]

    r2 = requests.post(f"{API}/auth/verify-email", json={"token": token})
    assert r2.status_code == 200

    r3 = requests.get(f"{API}/auth/me", headers=H(S["poster_t"]))
    assert r3.status_code == 200
    assert r3.json()["user"]["email_verified"] is True


# ---------- Chat ----------
def test_12_create_item_for_chat():
    import io
    files = {"photo": ("a.jpg", io.BytesIO(b"\xff\xd8\xff\xd9"*200), "image/jpeg")}
    data = {"title": "Chat Bread", "description": "fresh sliced loaf",
            "category": "Food", "expiration_date": "2026-12-01",
            "quantity": "1", "zip_code": "10001"}
    r = requests.post(f"{API}/items", headers=H(S["poster_t"]), data=data, files=files)
    assert r.status_code == 200, r.text
    S["item_id"] = r.json()["item"]["id"]
    # claim
    r2 = requests.post(f"{API}/items/{S['item_id']}/claim", headers=H(S["claimer_t"]))
    assert r2.status_code == 200
    S["claim_code"] = r2.json()["claim_code"]


def test_13_chat_third_party_forbidden():
    r = requests.get(f"{API}/items/{S['item_id']}/messages", headers=H(S["other_t"]))
    assert r.status_code == 403
    r2 = requests.post(f"{API}/items/{S['item_id']}/messages",
                       headers=H(S["other_t"]), json={"text": "Hi"})
    assert r2.status_code == 403


def test_14_chat_pii_scrub():
    r = requests.post(f"{API}/items/{S['item_id']}/messages",
                      headers=H(S["poster_t"]),
                      json={"text": "Call me at 555-123-4567 anytime"})
    assert r.status_code == 200
    text = r.json()["message"]["text"]
    assert "555" not in text
    assert "[redacted phone]" in text


def test_15_chat_visible_to_both_parties():
    for tok in [S["poster_t"], S["claimer_t"]]:
        r = requests.get(f"{API}/items/{S['item_id']}/messages", headers=H(tok))
        assert r.status_code == 200
        assert len(r.json()["messages"]) >= 1


def test_16_chat_closed_after_completed():
    # confirm pickup
    r = requests.post(f"{API}/items/{S['item_id']}/confirm", headers=H(S["poster_t"]),
                      json={"code": S["claim_code"]})
    assert r.status_code == 200
    # now posting should be blocked
    r2 = requests.post(f"{API}/items/{S['item_id']}/messages",
                       headers=H(S["poster_t"]), json={"text": "after close"})
    assert r2.status_code == 400


# ---------- Admin reports + delete ----------
def test_17_admin_reports_and_delete_item():
    # Create a report on item via claimer
    rep = requests.post(f"{API}/items/{S['item_id']}/report",
                        headers=H(S["claimer_t"]), data={"reason": "test report iter2"})
    assert rep.status_code == 200

    r = requests.get(f"{API}/admin/reports", headers=H(S["admin_t"]))
    assert r.status_code == 200
    reasons = [x["reason"] for x in r.json()["reports"]]
    assert any("test report iter2" in x for x in reasons)

    # delete item
    r2 = requests.delete(f"{API}/admin/items/{S['item_id']}", headers=H(S["admin_t"]))
    assert r2.status_code == 200
    doc = db.items.find_one({"_id": ObjectId(S["item_id"])})
    assert doc["status"] == "removed"


# ---------- Auto-expire ----------
def test_18_auto_expire_function():
    # Insert an item with past expiration_date directly
    past = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
    res = db.items.insert_one({
        "title": "Old bread", "description": "x", "category": "Food",
        "expiration_date": past, "quantity": "1", "zip_code": "10001",
        "meetup_suggestion": "x", "image_path": "x", "status": "active",
        "owner_id": ObjectId(S["poster_id"]), "owner_name": "Poster",
        "claimed_by": None, "claim_code": None, "claimed_at": None,
        "completed_at": None, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    iid = res.inserted_id

    # Call the loop body directly (one iteration) — easier than importing the loop
    today = datetime.now(timezone.utc).date().isoformat()
    upd = db.items.update_many(
        {"status": {"$in": ["active", "claimed"]}, "expiration_date": {"$lt": today}},
        {"$set": {"status": "expired"}},
    )
    assert upd.modified_count >= 1
    doc = db.items.find_one({"_id": iid})
    assert doc["status"] == "expired"
    db.items.delete_one({"_id": iid})


# ---------- Donations + receipts ----------
def test_19_my_donations_empty_ok():
    r = requests.get(f"{API}/me/donations", headers=H(S["claimer_t"]))
    assert r.status_code == 200
    assert isinstance(r.json()["donations"], list)


def test_20_receipt_pdf_owner_and_admin():
    # Insert a paid donation directly
    sid = f"cs_test_{TS}_receipt"
    db.payment_transactions.insert_one({
        "session_id": sid,
        "user_id": ObjectId(S["claimer_id"]),
        "purpose": "donation",
        "amount": 25.00,
        "currency": "usd",
        "payment_status": "paid",
        "metadata": {"purpose": "donation", "donor_name": "Claimer"},
        "anonymous": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    # Now /me/donations for claimer should include it
    r = requests.get(f"{API}/me/donations", headers=H(S["claimer_t"]))
    assert r.status_code == 200
    sids = [d["session_id"] for d in r.json()["donations"]]
    assert sid in sids

    # Owner can download
    r2 = requests.get(f"{API}/donations/{sid}/receipt", headers=H(S["claimer_t"]))
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("application/pdf")
    assert r2.content[:4] == b"%PDF"

    # Other user cannot
    r3 = requests.get(f"{API}/donations/{sid}/receipt", headers=H(S["other_t"]))
    assert r3.status_code == 403

    # Admin can
    r4 = requests.get(f"{API}/donations/{sid}/receipt", headers=H(S["admin_t"]))
    assert r4.status_code == 200
    assert r4.headers["content-type"].startswith("application/pdf")

    db.payment_transactions.delete_one({"session_id": sid})


def test_21_admin_seed_idempotent_role_set():
    u = db.users.find_one({"email": ADMIN_EMAIL})
    assert u is not None
    assert u.get("role") == "admin"
    assert u.get("verified") is True
    assert u.get("email_verified") is True
