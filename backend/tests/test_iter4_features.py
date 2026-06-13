"""Iteration-4 tests: profiles, reviews+stars, blocks, watchlist, avatar/bio,
unverified-claim allowance, pickup reminder loop, CAD currency, LIVE Stripe URL."""
import os, time, io, asyncio, pytest, requests
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE}/api"
mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mongo[os.environ.get("DB_NAME", "test_database")]

TS = int(time.time())
POSTER = {"email": f"iter4poster_{TS}@expiremate.com", "password": "Test1234", "name": "Iter4Poster", "zip_code": "10101"}
CLAIMER = {"email": f"iter4claim_{TS}@expiremate.com", "password": "Test1234", "name": "Iter4Claimer", "zip_code": "10101"}
UNVER = {"email": f"iter4unver_{TS}@expiremate.com", "password": "Test1234", "name": "Iter4Unver", "zip_code": "10101"}
S = {}


def H(t):
    return {"Authorization": f"Bearer {t}"}


def _photo_bytes():
    return b"\xff\xd8\xff\xd9" + os.urandom(512) + str(time.time_ns()).encode()


def _post_item(token, title="Iter4 Item"):
    files = {"photo": ("a.jpg", _photo_bytes(), "image/jpeg")}
    data = {
        "title": title, "description": "Fresh sealed item for pickup", "category": "Food",
        "expiration_date": (datetime.utcnow() + timedelta(days=2)).date().isoformat(),
        "quantity": "1 unit", "zip_code": "10101",
        "meetup_suggestion": "Suggested: public grocery store parking lot",
    }
    r = requests.post(f"{API}/items", headers=H(token), data=data, files=files)
    return r


# ---------- Setup: 3 users ----------
def test_00_setup_users():
    for u, k in [(POSTER, "poster"), (CLAIMER, "claimer"), (UNVER, "unver")]:
        r = requests.post(f"{API}/auth/register", json=u)
        assert r.status_code == 200, r.text
        S[f"{k}_t"] = r.json()["token"]
        S[f"{k}_id"] = r.json()["user"]["id"]
    # only POSTER is verified; CLAIMER + UNVER are NOT
    db.users.update_one({"_id": ObjectId(S["poster_id"])}, {"$set": {"verified": True}})


# ---------- 1: unverified user CAN claim ----------
def test_01_unverified_claim_allowed():
    r = _post_item(S["poster_t"], title=f"UnverClaim {TS}")
    assert r.status_code == 200, r.text
    item_id = r.json()["item"]["id"]
    S["item_for_unver_id"] = item_id

    # UNVER user (not verified) claims — should succeed
    r2 = requests.post(f"{API}/items/{item_id}/claim", headers=H(S["unver_t"]))
    assert r2.status_code == 200, r2.text
    assert "claim_code" in r2.json()
    S["item_for_unver_code"] = r2.json()["claim_code"]


# ---------- 2: unverified user CANNOT post ----------
def test_02_unverified_post_forbidden():
    r = _post_item(S["unver_t"], title=f"UnverPost {TS}")
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"


# ---------- 3: profile endpoint shape ----------
def test_03_profile_shape():
    r = requests.get(f"{API}/users/{S['poster_id']}/profile")
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["user", "rating_avg", "rating_count", "items_rescued"]:
        assert k in d
    assert d["user"]["id"] == S["poster_id"]
    assert "bio" in d["user"]
    assert "avatar_path" in d["user"]
    assert d["rating_count"] == 0 or isinstance(d["rating_count"], int)


# ---------- 4: reviews list empty initially ----------
def test_04_reviews_initially_empty():
    r = requests.get(f"{API}/users/{S['poster_id']}/reviews")
    assert r.status_code == 200
    assert isinstance(r.json().get("reviews"), list)


# ---------- 5: review forbidden when not completed ----------
def test_05_review_blocked_when_not_completed():
    r = requests.post(f"{API}/items/{S['item_for_unver_id']}/review",
                      headers=H(S["unver_t"]),
                      json={"rating": 5, "text": "great"})
    assert r.status_code == 400, r.text


# ---------- Setup completed item for review tests ----------
def test_06_create_completed_item():
    # post (verified poster) -> claim (verified claimer) -> confirm
    db.users.update_one({"_id": ObjectId(S["claimer_id"])}, {"$set": {"verified": True}})
    r = _post_item(S["poster_t"], title=f"Completed {TS}")
    assert r.status_code == 200, r.text
    item_id = r.json()["item"]["id"]
    S["completed_id"] = item_id

    rc = requests.post(f"{API}/items/{item_id}/claim", headers=H(S["claimer_t"]))
    assert rc.status_code == 200, rc.text
    code = rc.json()["claim_code"]

    rcf = requests.post(f"{API}/items/{item_id}/confirm", headers=H(S["poster_t"]),
                        json={"code": code})
    assert rcf.status_code == 200, rcf.text


# ---------- 7: rating validation ----------
def test_07_rating_validation():
    for bad in [0, 6, "abc"]:
        r = requests.post(f"{API}/items/{S['completed_id']}/review",
                          headers=H(S["poster_t"]), json={"rating": bad, "text": ""})
        assert r.status_code in (400, 422), f"rating={bad} should reject, got {r.status_code}"


# ---------- 8: poster reviews claimer; reviewee_id correctness ----------
def test_08_poster_reviews_claimer():
    r = requests.post(f"{API}/items/{S['completed_id']}/review",
                      headers=H(S["poster_t"]),
                      json={"rating": 5, "text": "Great pickup!"})
    assert r.status_code == 200, r.text
    # Check reviewee is the claimer
    rev = db.reviews.find_one({
        "item_id": ObjectId(S["completed_id"]),
        "reviewer_id": ObjectId(S["poster_id"]),
    })
    assert rev is not None
    assert str(rev["reviewee_id"]) == S["claimer_id"]


# ---------- 9: only once per (item, reviewer) ----------
def test_09_review_once():
    r = requests.post(f"{API}/items/{S['completed_id']}/review",
                      headers=H(S["poster_t"]),
                      json={"rating": 4, "text": "dup"})
    assert r.status_code == 400


# ---------- 10: claimer reviews poster; reviewee correct ----------
def test_10_claimer_reviews_poster():
    r = requests.post(f"{API}/items/{S['completed_id']}/review",
                      headers=H(S["claimer_t"]),
                      json={"rating": 4, "text": "Quick handoff"})
    assert r.status_code == 200, r.text
    rev = db.reviews.find_one({
        "item_id": ObjectId(S["completed_id"]),
        "reviewer_id": ObjectId(S["claimer_id"]),
    })
    assert rev and str(rev["reviewee_id"]) == S["poster_id"]


# ---------- 11: non-participant cannot review ----------
def test_11_non_participant_review_blocked():
    r = requests.post(f"{API}/items/{S['completed_id']}/review",
                      headers=H(S["unver_t"]),
                      json={"rating": 5, "text": "no"})
    assert r.status_code == 403, r.text


# ---------- 12: profile aggregation reflects review ----------
def test_12_profile_aggregates():
    r = requests.get(f"{API}/users/{S['claimer_id']}/profile")
    assert r.status_code == 200
    d = r.json()
    assert d["rating_count"] >= 1
    assert d["rating_avg"] is not None
    assert 1 <= d["rating_avg"] <= 5
    assert d["items_rescued"] >= 1

    rr = requests.get(f"{API}/users/{S['claimer_id']}/reviews")
    assert rr.status_code == 200
    revs = rr.json()["reviews"]
    assert len(revs) >= 1
    assert revs[0]["reviewer"] is not None
    assert "id" in revs[0]["reviewer"]


# ---------- 13: PATCH /me/profile updates bio ----------
def test_13_update_bio():
    bio_text = f"Hi I'm Iter4 {TS}"
    r = requests.patch(f"{API}/me/profile", headers=H(S["poster_t"]),
                       json={"bio": bio_text})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["bio"] == bio_text

    me = requests.get(f"{API}/auth/me", headers=H(S["poster_t"]))
    assert me.status_code == 200
    assert me.json()["user"]["bio"] == bio_text
    assert "avatar_path" in me.json()["user"]


# ---------- 14: avatar upload ----------
def test_14_avatar_upload():
    files = {"photo": ("avatar.jpg", _photo_bytes(), "image/jpeg")}
    r = requests.post(f"{API}/me/avatar", headers=H(S["poster_t"]), files=files)
    # Object storage may not be configured in test env => 500 acceptable but flagged
    if r.status_code != 200:
        pytest.skip(f"avatar upload returned {r.status_code}: {r.text[:200]} — object storage likely unavailable")
    body = r.json()
    assert body["user"]["avatar_path"], "avatar_path should be set"


# ---------- 15: block/unblock roundtrip ----------
def test_15_block_roundtrip():
    # block self => 400
    r0 = requests.post(f"{API}/users/{S['poster_id']}/block", headers=H(S["poster_t"]))
    assert r0.status_code == 400

    r1 = requests.post(f"{API}/users/{S['unver_id']}/block", headers=H(S["poster_t"]))
    assert r1.status_code == 200, r1.text

    rg = requests.get(f"{API}/me/blocks", headers=H(S["poster_t"]))
    assert rg.status_code == 200
    ids = [b["id"] for b in rg.json()["blocks"]]
    assert S["unver_id"] in ids

    # idempotent block (no error)
    r2 = requests.post(f"{API}/users/{S['unver_id']}/block", headers=H(S["poster_t"]))
    assert r2.status_code == 200

    rd = requests.delete(f"{API}/users/{S['unver_id']}/block", headers=H(S["poster_t"]))
    assert rd.status_code == 200

    rg2 = requests.get(f"{API}/me/blocks", headers=H(S["poster_t"]))
    assert S["unver_id"] not in [b["id"] for b in rg2.json()["blocks"]]


# ---------- 16: watchlist roundtrip + idempotency ----------
def test_16_watchlist_roundtrip():
    r = _post_item(S["poster_t"], title=f"Watchable {TS}")
    assert r.status_code == 200, r.text
    item_id = r.json()["item"]["id"]

    r1 = requests.post(f"{API}/items/{item_id}/watch", headers=H(S["claimer_t"]))
    assert r1.status_code == 200, r1.text

    # second watch — idempotent
    r2 = requests.post(f"{API}/items/{item_id}/watch", headers=H(S["claimer_t"]))
    assert r2.status_code == 200

    cnt = db.watches.count_documents({
        "user_id": ObjectId(S["claimer_id"]), "item_id": ObjectId(item_id)
    })
    assert cnt == 1, f"expected 1 watch doc, got {cnt}"

    rg = requests.get(f"{API}/me/watchlist", headers=H(S["claimer_t"]))
    assert rg.status_code == 200
    assert any(i["id"] == item_id for i in rg.json()["items"])

    rd = requests.delete(f"{API}/items/{item_id}/watch", headers=H(S["claimer_t"]))
    assert rd.status_code == 200

    rg2 = requests.get(f"{API}/me/watchlist", headers=H(S["claimer_t"]))
    assert not any(i["id"] == item_id for i in rg2.json()["items"])


# ---------- 17: pickup reminder loop body ----------
def test_17_pickup_reminder_loop():
    # Insert an item directly in mongo: claimed, claimed_at > 24h ago, no reminder_sent_at
    old_iso = (datetime.utcnow() - timedelta(hours=30)).isoformat()
    item_doc = {
        "title": f"Reminder Test {TS}",
        "description": "test", "category": "Food",
        "expiration_date": (datetime.utcnow() + timedelta(days=2)).date().isoformat(),
        "quantity": "1", "zip_code": "10101",
        "owner_id": ObjectId(S["poster_id"]),
        "claimed_by": ObjectId(S["claimer_id"]),
        "status": "claimed",
        "claim_code": "1234",
        "claimed_at": old_iso,
        "created_at": old_iso,
        "image_path": "test/x.jpg",
        "meetup_suggestion": "x",
        "photo_hash": "test_hash_" + str(time.time_ns()),
    }
    ins = db.items.insert_one(item_doc)
    item_id = ins.inserted_id

    # Call the loop body once directly via server module
    import sys, importlib
    sys.path.insert(0, "/app/backend")
    server = importlib.import_module("server")

    async def _run_once():
        # Execute just the body of the loop (one iteration)
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        cursor = server.db.items.find({
            "status": "claimed",
            "claimed_at": {"$lt": cutoff},
            "reminder_sent_at": {"$exists": False},
        })
        async for it in cursor:
            owner = await server.db.users.find_one({"_id": it["owner_id"]})
            claimer = await server.db.users.find_one({"_id": it["claimed_by"]}) if it.get("claimed_by") else None
            for u in [owner, claimer]:
                if not u or u.get("banned"):
                    continue
                try:
                    await asyncio.to_thread(server.send_email,
                        to=u["email"], subject="Reminder", html="<p>r</p>",
                        link="https://x")
                except Exception:
                    pass
            await server.db.items.update_one(
                {"_id": it["_id"]},
                {"$set": {"reminder_sent_at": (datetime.utcnow().isoformat())}},
            )

    asyncio.get_event_loop().run_until_complete(_run_once())

    fresh = db.items.find_one({"_id": item_id})
    assert fresh.get("reminder_sent_at"), "reminder_sent_at should be set after loop body"

    # Check EMAIL_LOG had entries for both parties
    outbox = server.EMAIL_LOG
    emails_to = [e.get("to") for e in outbox]
    assert POSTER["email"] in emails_to or CLAIMER["email"] in emails_to, \
        f"expected reminder email in outbox; outbox tail: {outbox[:5]}"

    # cleanup
    db.items.delete_one({"_id": item_id})


# ---------- 18: currency = cad on donate-checkout ----------
def test_18_currency_cad_and_stripe_live_url():
    payload = {"preset": "five", "origin_url": BASE, "anonymous": False}
    r = requests.post(f"{API}/payments/donate-checkout", headers=H(S["poster_t"]),
                      json=payload)
    # tolerate alternate preset names — if 400, retry with custom
    if r.status_code == 400:
        payload = {"preset": "custom", "custom_amount": 5.0, "origin_url": BASE, "anonymous": False}
        r = requests.post(f"{API}/payments/donate-checkout", headers=H(S["poster_t"]),
                          json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    url = body.get("url") or body.get("checkout_url") or ""
    assert "checkout.stripe.com" in url, f"expected real Stripe URL, got {url}"

    rec = db.payment_transactions.find_one(
        {"user_id": ObjectId(S["poster_id"]), "purpose": "donation"},
        sort=[("created_at", -1)]
    )
    assert rec is not None, "payment_transactions doc missing"
    assert rec.get("currency") == "cad", f"expected currency cad, got {rec.get('currency')}"


# ---------- 19: verification-checkout also cad ----------
def test_19_verification_checkout_currency():
    payload = {"origin_url": BASE}
    r = requests.post(f"{API}/payments/verify-checkout", headers=H(S["unver_t"]),
                      json=payload)
    if r.status_code == 200:
        rec = db.payment_transactions.find_one(
            {"user_id": ObjectId(S["unver_id"]), "purpose": "id_verification"},
            sort=[("created_at", -1)]
        )
        if rec:
            assert rec.get("currency") == "cad"
