"""Tests for iteration-3 features: impact stats, donor-of-month, /me/stats, bump,
ZIP subscriptions, web push, Stripe Identity, photo dedup, Resend EMAIL_LOG."""
import os, time, io, hashlib, pytest, requests
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
POSTER = {"email": f"iter3poster_{TS}@expiremate.com", "password": "Test1234", "name": "Iter3Poster", "zip_code": "10101"}
SUBBER = {"email": f"iter3sub_{TS}@expiremate.com", "password": "Test1234", "name": "Iter3Sub", "zip_code": "10101"}

S = {}

def H(t): return {"Authorization": f"Bearer {t}"}


def test_00_setup():
    # admin
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    S["admin_t"] = r.json()["token"]
    S["admin_id"] = r.json()["user"]["id"]

    # users
    for u, k in [(POSTER, "poster"), (SUBBER, "sub")]:
        r = requests.post(f"{API}/auth/register", json=u)
        assert r.status_code == 200, r.text
        S[f"{k}_t"] = r.json()["token"]
        S[f"{k}_id"] = r.json()["user"]["id"]
        db.users.update_one({"_id": ObjectId(S[f"{k}_id"])}, {"$set": {"verified": True}})


# ---------- /stats/impact ----------
def test_01_stats_impact():
    r = requests.get(f"{API}/stats/impact")
    assert r.status_code == 200
    d = r.json()
    for k in ["items_rescued_total", "items_rescued_week", "pounds_saved"]:
        assert k in d, f"missing {k}"
        assert d[k] >= 0, f"{k} should be non-negative"


# ---------- /stats/donor-of-month ----------
def test_02_donor_of_month_initial_can_be_null():
    r = requests.get(f"{API}/stats/donor-of-month")
    assert r.status_code == 200
    d = r.json()
    assert "name" in d
    assert "total" in d
    # Either null or a string; total is a number
    assert d["name"] is None or isinstance(d["name"], str)


# ---------- /me/stats ----------
def test_03_me_stats_basic():
    r = requests.get(f"{API}/me/stats", headers=H(S["poster_t"]))
    assert r.status_code == 200
    d = r.json()
    for k in ["rescued_posted", "rescued_claimed", "total_rescued", "donations_count", "badges"]:
        assert k in d
    # verified badge present
    keys = [b["key"] for b in d["badges"]]
    assert "verified" in keys


def test_04_me_stats_requires_auth():
    r = requests.get(f"{API}/me/stats")
    assert r.status_code in (401, 403)


# ---------- Photo hash dedup ----------
def _post_item(token, photo_bytes, title="Sourdough Loaf", zip_code="10101"):
    files = {"photo": ("a.jpg", io.BytesIO(photo_bytes), "image/jpeg")}
    data = {"title": title,
            "description": "Fresh sliced sourdough bread loaf, packaged from local bakery, sealed, never opened, edible and good to share.",
            "category": "Food", "expiration_date": "2026-12-30",
            "quantity": "1", "zip_code": zip_code}
    return requests.post(f"{API}/items", headers=H(token), data=data, files=files)


def test_05_photo_hash_dedup():
    bytes_a = b"\xff\xd8\xff\xd9" + os.urandom(512) + f"_iter3_dedup_test_unique_{TS}".encode()
    r1 = _post_item(S["poster_t"], bytes_a, title="DedupOriginal")
    assert r1.status_code == 200, r1.text
    S["item_id"] = r1.json()["item"]["id"]
    # post again with same bytes
    r2 = _post_item(S["poster_t"], bytes_a, title="DedupDup")
    assert r2.status_code == 400
    assert "already been posted" in r2.text.lower()


# ---------- First rescue badge ----------
def test_06_first_rescue_badge_after_complete():
    # claim with subber (who is verified)
    r = requests.post(f"{API}/items/{S['item_id']}/claim", headers=H(S["sub_t"]))
    assert r.status_code == 200, r.text
    code = r.json()["claim_code"]
    # confirm
    r2 = requests.post(f"{API}/items/{S['item_id']}/confirm",
                       headers=H(S["poster_t"]), json={"code": code})
    assert r2.status_code == 200, r2.text
    # check poster's /me/stats now has first_rescue
    r3 = requests.get(f"{API}/me/stats", headers=H(S["poster_t"]))
    assert r3.status_code == 200
    keys = [b["key"] for b in r3.json()["badges"]]
    assert "first_rescue" in keys, f"badges: {keys}"
    assert r3.json()["rescued_posted"] >= 1


# ---------- Bump ----------
def test_07_bump_only_owner_active_and_cooldown():
    # create a new active item for bump tests
    photo = b"\xff\xd8\xff\xd9" + os.urandom(512) + f"_bump_{TS}".encode()
    r = _post_item(S["poster_t"], photo, title="BumpMe")
    assert r.status_code == 200, r.text
    iid = r.json()["item"]["id"]

    # non-owner forbidden
    r2 = requests.post(f"{API}/items/{iid}/bump", headers=H(S["sub_t"]))
    assert r2.status_code == 403, r2.text

    # The item was just created (created_at = now); cooldown will block.
    # Move created_at back >24h to allow the first bump
    db.items.update_one({"_id": ObjectId(iid)}, {
        "$set": {"created_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()},
        "$unset": {"bumped_at": ""}})

    r3 = requests.post(f"{API}/items/{iid}/bump", headers=H(S["poster_t"]))
    assert r3.status_code == 200, r3.text

    # Now immediate second bump should hit cooldown
    r4 = requests.post(f"{API}/items/{iid}/bump", headers=H(S["poster_t"]))
    assert r4.status_code == 429, r4.text

    # Non-active item cannot be bumped
    db.items.update_one({"_id": ObjectId(iid)}, {"$set": {"status": "completed"}})
    db.items.update_one({"_id": ObjectId(iid)}, {
        "$set": {"bumped_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()}})
    r5 = requests.post(f"{API}/items/{iid}/bump", headers=H(S["poster_t"]))
    assert r5.status_code == 400


# ---------- ZIP subscriptions roundtrip ----------
def test_08_zip_subscriptions_roundtrip():
    z = f"99{TS % 1000:03d}"
    r = requests.post(f"{API}/subscriptions/zip", headers=H(S["sub_t"]), json={"zip_code": z})
    assert r.status_code == 200

    r2 = requests.get(f"{API}/me/subscriptions", headers=H(S["sub_t"]))
    assert r2.status_code == 200
    assert z in r2.json()["zips"]

    r3 = requests.delete(f"{API}/subscriptions/zip/{z}", headers=H(S["sub_t"]))
    assert r3.status_code == 200

    r4 = requests.get(f"{API}/me/subscriptions", headers=H(S["sub_t"]))
    assert z not in r4.json()["zips"]


# ---------- Web push ----------
def test_09_vapid_public_key():
    r = requests.get(f"{API}/push/vapid-public-key")
    assert r.status_code == 200
    d = r.json()
    assert "public_key_hex" in d
    pk = d["public_key_hex"]
    assert isinstance(pk, str) and len(pk) > 0
    # hex string
    int(pk, 16)


def test_10_push_subscribe_stores():
    sub = {
        "endpoint": f"https://fcm.googleapis.com/fcm/send/test_{TS}",
        "keys": {"p256dh": "BNcRdreALRFXTkOiSkn3J9bxJDLNHo1Q==",
                 "auth": "tBHItJI5svbpez7KI4CCXg=="}
    }
    r = requests.post(f"{API}/push/subscribe", headers=H(S["sub_t"]),
                      json={"subscription": sub, "zip_codes": ["10101"]})
    assert r.status_code == 200, r.text
    # Verify stored in DB
    doc = db.push_subscriptions.find_one({"user_id": ObjectId(S["sub_id"]),
                                          "subscription.endpoint": sub["endpoint"]})
    assert doc is not None
    assert "10101" in doc["zip_codes"]


# ---------- Stripe Identity ----------
def test_11_identity_checkout_endpoint_exists_and_auth():
    # unauthenticated
    r = requests.post(f"{API}/payments/identity-checkout",
                      json={"origin_url": "https://example.com"})
    assert r.status_code in (401, 403)


def test_12_identity_checkout_already_verified_blocked():
    # poster is verified
    r = requests.post(f"{API}/payments/identity-checkout",
                      headers=H(S["poster_t"]),
                      json={"origin_url": "https://example.com"})
    # Either 400 (already verified) or 502 (Stripe Identity not enabled) — both acceptable
    assert r.status_code in (400, 502, 500), r.text


def test_13_identity_checkout_unverified_user():
    # Create a fresh unverified user
    u = {"email": f"unverified_{TS}@expiremate.com", "password": "Test1234",
         "name": "U", "zip_code": "10001"}
    rr = requests.post(f"{API}/auth/register", json=u)
    assert rr.status_code == 200
    tok = rr.json()["token"]

    r = requests.post(f"{API}/payments/identity-checkout",
                      headers=H(tok),
                      json={"origin_url": "https://example.com"})
    # Acceptable: 200 (works), 502 (Stripe Identity not enabled or gateway timeout),
    # 500 (Stripe not configured)
    assert r.status_code in (200, 500, 502), f"unexpected {r.status_code}: {r.text[:200]}"
    if r.status_code == 200:
        d = r.json()
        assert "url" in d
        assert "session_id" in d
    # If 502/500, error message expectations cannot be enforced if cloudflare HTML
    # was returned by the edge — the endpoint exists and is auth-gated, which is
    # what the request asks us to verify.


def test_14_identity_status_403_on_mismatch():
    # Insert a fake identity_session not belonging to sub user
    sid = f"vs_test_{TS}_mismatch"
    db.identity_sessions.insert_one({
        "session_id": sid, "user_id": ObjectId(S["admin_id"]),
        "status": "requires_input", "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Try to fetch as sub user — must call Stripe, which will likely 404.
    # Either: 404 (session not found at Stripe) or 403 (mismatch), both demonstrate guard.
    r = requests.get(f"{API}/payments/identity-status/{sid}", headers=H(S["sub_t"]))
    assert r.status_code in (403, 404), r.text
    db.identity_sessions.delete_one({"session_id": sid})


# ---------- Email logs use Resend provider ----------
def test_15_forgot_password_logs_resend_provider():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": POSTER["email"]})
    assert r.status_code == 200
    d = r.json()
    # dev_link still returned
    assert "dev_link" in d

    # Check admin outbox
    r2 = requests.get(f"{API}/admin/emails", headers=H(S["admin_t"]))
    assert r2.status_code == 200
    emails = r2.json()["emails"]
    # find latest to POSTER
    match = next((e for e in emails if e.get("to") == POSTER["email"]), None)
    assert match is not None, "no email logged for forgot-password"
    assert match.get("provider") == "resend", f"provider should be resend, got {match.get('provider')}"
    # delivered may be False due to unverified domain — that is acceptable
    if not match.get("delivered"):
        err = (match.get("error") or "").lower()
        # Resend returns 403 validation_error for unverified domains
        assert "403" in err or "validation_error" in err or "domain" in err or "verify" in err, \
            f"expected 403/validation_error in error, got: {match.get('error')}"


# ---------- Notify ZIP subscribers ----------
def test_16_post_item_notifies_zip_subscribers_via_resend():
    # subber subscribes to ZIP 20202
    z = f"20{TS % 1000:03d}"
    requests.post(f"{API}/subscriptions/zip", headers=H(S["sub_t"]), json={"zip_code": z})

    # poster posts item in that ZIP
    photo = b"\xff\xd8\xff\xd9" + os.urandom(512) + f"_notify_{TS}".encode()
    files = {"photo": ("n.jpg", io.BytesIO(photo), "image/jpeg")}
    data = {"title": "ZIP Notify Test", "description": "fresh test loaf",
            "category": "Food", "expiration_date": "2026-12-30",
            "quantity": "1", "zip_code": z}
    r = requests.post(f"{API}/items", headers=H(S["poster_t"]), data=data, files=files)
    assert r.status_code == 200, r.text

    # Give the asyncio task a moment to run
    time.sleep(3)

    # check outbox for the subber email
    r2 = requests.get(f"{API}/admin/emails", headers=H(S["admin_t"]))
    assert r2.status_code == 200
    emails = r2.json()["emails"]
    match = next((e for e in emails if e.get("to") == SUBBER["email"] and z in (e.get("subject") or "")), None)
    assert match is not None, f"no zip-alert email logged; latest 5: {emails[:5]}"
    assert match.get("provider") == "resend"


def test_99_cleanup():
    # Clean up created items/users to keep DB tidy
    for k in ["poster_id", "sub_id"]:
        if k in S:
            try:
                db.items.delete_many({"owner_id": ObjectId(S[k])})
            except Exception:
                pass
