"""Iteration 4 feature tests:
1) Featured Project of the Week
2) Kit Assembly Guide (guide_url + PDF upload)
3) Customer Support (Ask-a-Question) tickets
4) Abandoned-cart scan trigger + eligibility + cooldown
"""
import io
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    from pathlib import Path
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@electronichub.io", "password": "Admin@12345"}
CUSTOMER = {"email": "suraganithanusri@gmail.com", "password": "Customer@12345"}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def customer_token(s):
    r = s.post(f"{API}/auth/login", json=CUSTOMER, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def customer_user(s, customer_token):
    r = s.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {customer_token}"}, timeout=15)
    return r.json()


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ============ Featured Project of the Week ============
class TestFeaturedProject:
    def test_get_default_featured(self, s, admin_token):
        # Reset first by setting to line-follower-robot (sort_order=1 default)
        s.post(f"{API}/admin/featured-project", headers=h(admin_token),
               json={"slug": "line-follower-robot"}, timeout=15)
        r = s.get(f"{API}/featured-project", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("project") is not None
        proj = d["project"]
        assert proj["slug"] == "line-follower-robot"
        assert "items" in proj and len(proj["items"]) > 0
        assert "total_price" in proj and isinstance(proj["total_price"], (int, float))

    def test_set_featured_admin(self, s, admin_token):
        r = s.post(f"{API}/admin/featured-project", headers=h(admin_token),
                   json={"slug": "weather-station"}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        # Verify
        r2 = s.get(f"{API}/featured-project", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["project"]["slug"] == "weather-station"
        # Reset
        s.post(f"{API}/admin/featured-project", headers=h(admin_token),
               json={"slug": "line-follower-robot"}, timeout=15)

    def test_set_featured_requires_admin_no_token(self, s):
        r = s.post(f"{API}/admin/featured-project", json={"slug": "weather-station"}, timeout=15)
        assert r.status_code in (401, 403)

    def test_set_featured_requires_admin_customer(self, s, customer_token):
        r = s.post(f"{API}/admin/featured-project", headers=h(customer_token),
                   json={"slug": "weather-station"}, timeout=15)
        assert r.status_code == 403


# ============ Admin Projects + Kit Assembly Guide ============
class TestAdminProjectsAndGuide:
    def test_admin_list_projects(self, s, admin_token):
        r = s.get(f"{API}/admin/projects", headers=h(admin_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        slugs = {p["slug"] for p in data}
        assert {"line-follower-robot", "weather-station",
                "obstacle-avoider", "motion-alert-cam"}.issubset(slugs)

    def test_admin_projects_forbidden_customer(self, s, customer_token):
        r = s.get(f"{API}/admin/projects", headers=h(customer_token), timeout=15)
        assert r.status_code == 403

    def test_upload_datasheet_pdf_and_set_guide(self, s, admin_token):
        # Upload small PDF
        pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        files = {"file": ("guide.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        r = s.post(f"{API}/uploads/datasheet", headers=h(admin_token),
                   files=files, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "path" in d and "url" in d
        assert d["url"].startswith("/api/files/")

        # Fetch project slug per request; note review says 'electronics-shop-97' but seeded is 'motion-alert-cam'?
        # Use both — try electronics-shop-97 first, fall back to motion-alert-cam if not found.
        target_slug = None
        r_list = s.get(f"{API}/admin/projects", headers=h(admin_token), timeout=15)
        slugs = [p["slug"] for p in r_list.json()]
        for cand in ("electronics-shop-97", "motion-alert-cam", "line-follower-robot"):
            if cand in slugs:
                target_slug = cand
                break
        assert target_slug, f"No suitable project found; available: {slugs}"

        guide_url = d["url"]
        r2 = s.put(f"{API}/admin/projects/{target_slug}", headers=h(admin_token),
                   json={"guide_url": guide_url}, timeout=15)
        assert r2.status_code == 200, r2.text
        assert r2.json().get("guide_url") == guide_url

        # Verify exposed on public GET
        r3 = s.get(f"{API}/projects/{target_slug}", timeout=15)
        assert r3.status_code == 200
        assert r3.json().get("guide_url") == guide_url


# ============ Customer Support ============
class TestSupport:
    def test_submit_question_success(self, s):
        # Get a product id
        pr = s.get(f"{API}/products", params={"limit": 1}, timeout=15)
        pid = pr.json()["items"][0]["id"]
        payload = {
            "name": "TEST_QA_User", "email": "TEST_qa@example.com",
            "question": "Is this compatible with 3.3V logic?", "product_id": pid,
        }
        r = s.post(f"{API}/support/question", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert "ticket_id" in d and len(d["ticket_id"]) > 0

    def test_submit_question_validation_empty_name(self, s):
        r = s.post(f"{API}/support/question",
                   json={"name": "", "email": "a@b.com", "question": "long enough question here"},
                   timeout=15)
        assert r.status_code == 422

    def test_submit_question_validation_short_question(self, s):
        r = s.post(f"{API}/support/question",
                   json={"name": "X", "email": "a@b.com", "question": "hi"}, timeout=15)
        assert r.status_code == 422

    def test_submit_question_bad_email(self, s):
        r = s.post(f"{API}/support/question",
                   json={"name": "X", "email": "not-an-email", "question": "long question here"},
                   timeout=15)
        assert r.status_code == 422

    def test_admin_list_and_update_status(self, s, admin_token):
        r = s.get(f"{API}/admin/support", headers=h(admin_token), timeout=15)
        assert r.status_code == 200
        tickets = r.json()
        assert isinstance(tickets, list)
        # Sorted newest first
        if len(tickets) >= 2:
            assert tickets[0]["created_at"] >= tickets[1]["created_at"]
        # Find the most recent TEST ticket
        target = next((t for t in tickets if t["email"] == "TEST_qa@example.com"), None)
        assert target is not None
        tid = target["id"]
        assert target["status"] == "open"
        r2 = s.post(f"{API}/admin/support/{tid}/status", headers=h(admin_token),
                    json={"status": "closed"}, timeout=15)
        assert r2.status_code == 200
        # Verify
        r3 = s.get(f"{API}/admin/support", headers=h(admin_token), timeout=15)
        upd = next(t for t in r3.json() if t["id"] == tid)
        assert upd["status"] == "closed"

    def test_admin_support_forbidden_customer(self, s, customer_token):
        r = s.get(f"{API}/admin/support", headers=h(customer_token), timeout=15)
        assert r.status_code == 403


# ============ Abandoned Cart Scan ============
class TestAbandonedCart:
    def test_trigger_scan_returns_ok(self, s, admin_token):
        r = s.post(f"{API}/admin/trigger-abandoned-cart-scan",
                   headers=h(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_trigger_scan_requires_admin(self, s, customer_token):
        r = s.post(f"{API}/admin/trigger-abandoned-cart-scan",
                   headers=h(customer_token), timeout=15)
        assert r.status_code == 403

    def test_eligibility_and_cooldown(self, s, admin_token, customer_token, customer_user):
        """Manually age a cart item >24h and verify email sent + cooldown flag."""
        import motor.motor_asyncio
        import asyncio
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
        db_name = os.environ.get("DB_NAME") or "test_database"
        # Fetch from backend env (subprocess of same k8s pod)
        for line in open("/app/backend/.env").read().splitlines():
            if line.startswith("MONGO_URL="):
                mongo_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("DB_NAME="):
                db_name = line.split("=", 1)[1].strip().strip('"').strip("'")

        client = MongoClient(mongo_url)
        db = client[db_name]
        user_id = customer_user["id"]

        # Ensure cart has an item (add via API)
        pr = s.get(f"{API}/products", params={"limit": 1}, timeout=15)
        pid = pr.json()["items"][0]["id"]
        s.post(f"{API}/cart/add", headers=h(customer_token),
               json={"product_id": pid, "quantity": 1}, timeout=15)

        # Age the cart item
        old_iso = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        res = db.cart_items.update_many({"user_id": user_id},
                                         {"$set": {"created_at": old_iso}})
        assert res.matched_count >= 1

        # Clear cooldown flag
        db.users.update_one({"id": user_id}, {"$unset": {"last_cart_reminder_at": ""}})

        # Trigger
        r = s.post(f"{API}/admin/trigger-abandoned-cart-scan",
                   headers=h(admin_token), timeout=60)
        assert r.status_code == 200

        # Verify DB flag was set (this is authoritative per test brief)
        u = db.users.find_one({"id": user_id})
        assert u.get("last_cart_reminder_at"), (
            "Expected last_cart_reminder_at to be set after abandoned-cart scan")
        first_stamp = u["last_cart_reminder_at"]

        # Cooldown: trigger again — should NOT resend (flag unchanged)
        time.sleep(1)
        r2 = s.post(f"{API}/admin/trigger-abandoned-cart-scan",
                    headers=h(admin_token), timeout=60)
        assert r2.status_code == 200
        u2 = db.users.find_one({"id": user_id})
        assert u2["last_cart_reminder_at"] == first_stamp, (
            "Cooldown violated: reminder timestamp changed on immediate re-trigger")

        # Cleanup: remove the cart item and cooldown so we don't pollute state
        db.cart_items.delete_many({"user_id": user_id})
        db.users.update_one({"id": user_id}, {"$unset": {"last_cart_reminder_at": ""}})
        client.close()

    def test_trigger_scan_no_eligible_carts(self, s, admin_token):
        """After cleanup above, no cart items are older than 24h — call succeeds and is idempotent."""
        r = s.post(f"{API}/admin/trigger-abandoned-cart-scan",
                   headers=h(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True
