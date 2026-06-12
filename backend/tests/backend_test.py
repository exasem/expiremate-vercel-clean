"""ExpireMate backend tests."""
import os, io, time, pytest, requests
from pymongo import MongoClient
from bson import ObjectId

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://savefood-college.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

# Direct mongo for verify flip
mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mongo[os.environ.get("DB_NAME", "test_database")]

TS = int(time.time())
U1 = {"email": f"test_owner_{TS}@expiremate.com", "password": "Test1234", "name": "Owner", "zip_code": "10001"}
U2 = {"email": f"test_claimer_{TS}@expiremate.com", "password": "Test1234", "name": "Claimer", "zip_code": "10001"}

state = {}

def H(tok): return {"Authorization": f"Bearer {tok}"}

# ---- Auth ----
def test_01_register_u1():
    r = requests.post(f"{API}/auth/register", json=U1)
    assert r.status_code == 200, r.text
    d = r.json(); assert "token" in d and d["user"]["email"] == U1["email"]
    state["t1"] = d["token"]; state["u1_id"] = d["user"]["id"]

def test_02_register_u2():
    r = requests.post(f"{API}/auth/register", json=U2)
    assert r.status_code == 200
    state["t2"] = r.json()["token"]; state["u2_id"] = r.json()["user"]["id"]

def test_03_duplicate_register():
    r = requests.post(f"{API}/auth/register", json=U1)
    assert r.status_code == 400

def test_04_login():
    r = requests.post(f"{API}/auth/login", json={"email": U1["email"], "password": U1["password"]})
    assert r.status_code == 200 and "token" in r.json()

def test_05_login_bad():
    r = requests.post(f"{API}/auth/login", json={"email": U1["email"], "password": "wrong"})
    assert r.status_code == 401

def test_06_me_bearer():
    r = requests.get(f"{API}/auth/me", headers=H(state["t1"]))
    assert r.status_code == 200 and r.json()["user"]["email"] == U1["email"]

def test_07_me_cookie():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": U1["email"], "password": U1["password"]})
    assert r.status_code == 200
    # confirm cookie set
    assert "access_token" in s.cookies.get_dict() or any("access_token" in c.name for c in s.cookies)
    r2 = s.get(f"{API}/auth/me")
    assert r2.status_code == 200

def test_08_me_unauth():
    assert requests.get(f"{API}/auth/me").status_code == 401

def test_09_logout():
    r = requests.post(f"{API}/auth/logout")
    assert r.status_code == 200

# ---- Items unverified ----
def test_10_post_unverified_403():
    files = {"photo": ("a.jpg", io.BytesIO(b"\xff\xd8\xff\xd9"*100), "image/jpeg")}
    data = {"title": "Test Bread", "description": "fresh", "category": "Food",
            "expiration_date": "2026-12-01", "quantity": "1", "zip_code": "10001"}
    r = requests.post(f"{API}/items", headers=H(state["t1"]), data=data, files=files)
    assert r.status_code == 403, r.text

# Flip verified directly
def test_11_flip_verified():
    db.users.update_one({"_id": ObjectId(state["u1_id"])}, {"$set": {"verified": True}})
    db.users.update_one({"_id": ObjectId(state["u2_id"])}, {"$set": {"verified": True}})
    u = db.users.find_one({"_id": ObjectId(state["u1_id"])})
    assert u["verified"] is True

# ---- AI moderation ----
def test_12_mod_blocks_oxycodone():
    files = {"photo": ("a.jpg", io.BytesIO(b"\xff\xd8\xff\xd9"*100), "image/jpeg")}
    data = {"title": "Oxycodone pills opened bottle", "description": "leftover",
            "category": "Sealed Medicine", "expiration_date": "2026-12-01",
            "quantity": "1", "zip_code": "10001"}
    r = requests.post(f"{API}/items", headers=H(state["t1"]), data=data, files=files)
    assert r.status_code == 400, f"Should be blocked: {r.status_code} {r.text}"

def test_13_mod_allows_tylenol_and_creates():
    files = {"photo": ("a.jpg", io.BytesIO(b"\xff\xd8\xff\xd9"*200), "image/jpeg")}
    data = {"title": "Sealed Tylenol bottle", "description": "unopened factory sealed",
            "category": "Sealed Medicine", "expiration_date": "2026-12-01",
            "quantity": "1", "zip_code": "10001", "meetup_suggestion": "Park"}
    r = requests.post(f"{API}/items", headers=H(state["t1"]), data=data, files=files)
    assert r.status_code == 200, r.text
    state["item_id"] = r.json()["item"]["id"]

def test_14_list_items():
    r = requests.get(f"{API}/items", params={"category": "Sealed Medicine"})
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()["items"]]
    assert state["item_id"] in ids

def test_15_get_item():
    r = requests.get(f"{API}/items/{state['item_id']}")
    assert r.status_code == 200 and r.json()["item"]["title"] == "Sealed Tylenol bottle"

def test_16_cannot_claim_own():
    r = requests.post(f"{API}/items/{state['item_id']}/claim", headers=H(state["t1"]))
    assert r.status_code == 400

def test_17_claim_ok():
    r = requests.post(f"{API}/items/{state['item_id']}/claim", headers=H(state["t2"]))
    assert r.status_code == 200
    d = r.json(); assert len(d["claim_code"]) == 4
    state["code"] = d["claim_code"]

def test_18_double_claim_fails():
    r = requests.post(f"{API}/items/{state['item_id']}/claim", headers=H(state["t2"]))
    assert r.status_code == 400

def test_19_confirm_wrong_code():
    r = requests.post(f"{API}/items/{state['item_id']}/confirm", headers=H(state["t1"]),
                     json={"code": "0000" if state["code"] != "0000" else "1111"})
    assert r.status_code == 400

def test_20_confirm_non_owner():
    r = requests.post(f"{API}/items/{state['item_id']}/confirm", headers=H(state["t2"]),
                     json={"code": state["code"]})
    assert r.status_code == 403

def test_21_confirm_ok():
    r = requests.post(f"{API}/items/{state['item_id']}/confirm", headers=H(state["t1"]),
                     json={"code": state["code"]})
    assert r.status_code == 200
    # verify completed
    r2 = requests.get(f"{API}/items/{state['item_id']}")
    assert r2.json()["item"]["status"] == "completed"

def test_22_me_items():
    r = requests.get(f"{API}/me/items", headers=H(state["t1"]))
    assert r.status_code == 200
    d = r.json(); assert len(d["posts"]) >= 1

def test_23_report():
    r = requests.post(f"{API}/items/{state['item_id']}/report",
                     headers=H(state["t2"]), data={"reason": "spam test"})
    assert r.status_code == 200

# ---- Payments ----
def test_24_verify_checkout_unverified_user():
    # make a new unverified user
    e = f"test_unv_{TS}@expiremate.com"
    r = requests.post(f"{API}/auth/register", json={"email": e, "password": "Test1234", "name": "X", "zip_code": "10001"})
    tok = r.json()["token"]
    r2 = requests.post(f"{API}/payments/verify-checkout", headers=H(tok),
                      json={"origin_url": BASE})
    assert r2.status_code == 200, r2.text
    d = r2.json(); assert "url" in d and "session_id" in d
    state["verify_session"] = d["session_id"]

def test_25_verify_checkout_already_verified_rejects():
    r = requests.post(f"{API}/payments/verify-checkout", headers=H(state["t1"]),
                     json={"origin_url": BASE})
    assert r.status_code == 400

def test_26_donate_preset_five():
    r = requests.post(f"{API}/payments/donate-checkout",
                     json={"preset": "five", "origin_url": BASE, "anonymous": False})
    assert r.status_code == 200 and "url" in r.json()

def test_27_donate_custom_valid():
    r = requests.post(f"{API}/payments/donate-checkout",
                     json={"preset": "custom", "custom_amount": 12.50, "origin_url": BASE})
    assert r.status_code == 200 and "url" in r.json()

def test_28_donate_custom_out_of_range():
    r = requests.post(f"{API}/payments/donate-checkout",
                     json={"preset": "custom", "custom_amount": 9999, "origin_url": BASE})
    assert r.status_code == 400

def test_29_donate_invalid_preset():
    r = requests.post(f"{API}/payments/donate-checkout",
                     json={"origin_url": BASE})
    assert r.status_code == 400

def test_30_payment_status():
    r = requests.get(f"{API}/payments/status/{state['verify_session']}")
    assert r.status_code == 200
    d = r.json(); assert "payment_status" in d and d["purpose"] == "id_verification"

def test_31_donations_stats():
    r = requests.get(f"{API}/donations/stats")
    assert r.status_code == 200
    d = r.json()
    assert set(["raised","goal","donor_count","percent"]).issubset(d.keys())
    assert d["goal"] == 20000.00

def test_32_leaderboard():
    r = requests.get(f"{API}/donations/leaderboard")
    assert r.status_code == 200 and "leaderboard" in r.json()

def test_33_config():
    r = requests.get(f"{API}/config")
    d = r.json(); assert "Food" in d["categories"] and d["verification_fee"] == 2.00

def test_34_serve_uploaded_file():
    item = db.items.find_one({"_id": ObjectId(state["item_id"])})
    p = item["image_path"]
    r = requests.get(f"{API}/files/{p}")
    assert r.status_code == 200 and len(r.content) > 0
