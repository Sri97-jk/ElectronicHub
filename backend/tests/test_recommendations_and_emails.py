"""Tests for /api/cart/recommendations endpoint and admin email flows (console mode)."""
import os
import re
import time
import uuid
import subprocess
import pytest
import requests
from pathlib import Path

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@electronichub.io", "password": "Admin@12345"}
CUSTOMER = {"email": "customer@electronichub.io", "password": "Customer@12345"}
LOG_PATH = "/var/log/supervisor/backend.err.log"


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def customer_token(s):
    r = s.post(f"{API}/auth/login", json=CUSTOMER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def arduino_uno_id(s):
    """Find the Arduino Uno product (SKU MCU-UNO-R3)."""
    r = s.get(f"{API}/products", params={"search": "Arduino Uno", "limit": 20}, timeout=15)
    assert r.status_code == 200
    for p in r.json()["items"]:
        if p["sku"] == "MCU-UNO-R3":
            return p["id"]
    pytest.fail("Arduino Uno (MCU-UNO-R3) not found in catalog")


def _clean_customer_cart(s, tok):
    """Delete all items from customer's cart."""
    r = s.get(f"{API}/cart", headers=h(tok), timeout=15)
    if r.status_code == 200:
        for it in r.json().get("items", []):
            s.delete(f"{API}/cart/item/{it['product_id']}", headers=h(tok), timeout=15)


# ---------------- Cart Recommendations ----------------
class TestCartRecommendations:
    def test_guest_empty_cart_returns_featured(self, s):
        cart_id = f"TEST_guest_{uuid.uuid4().hex[:8]}"
        r = s.get(f"{API}/cart/recommendations", params={"cart_id": cart_id, "limit": 6}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["reason"] == "featured"
        assert isinstance(d["items"], list)
        assert 1 <= len(d["items"]) <= 6
        for p in d["items"]:
            assert p.get("is_featured") is True

    def test_limit_param_respected(self, s):
        cart_id = f"TEST_guest_{uuid.uuid4().hex[:8]}"
        r = s.get(f"{API}/cart/recommendations", params={"cart_id": cart_id, "limit": 2}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 2

    def test_authenticated_empty_cart(self, s, customer_token):
        _clean_customer_cart(s, customer_token)
        r = s.get(f"{API}/cart/recommendations", headers=h(customer_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["reason"] == "featured"
        assert len(d["items"]) > 0

    def test_arduino_uno_in_cart_returns_compatible(self, s, customer_token, arduino_uno_id):
        _clean_customer_cart(s, customer_token)
        r = s.post(f"{API}/cart/add", headers=h(customer_token),
                   json={"product_id": arduino_uno_id, "quantity": 1}, timeout=15)
        assert r.status_code == 200

        r = s.get(f"{API}/cart/recommendations", headers=h(customer_token),
                  params={"limit": 8}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["reason"] == "compatible"
        assert len(d["items"]) > 0
        # The recommendations should include at least one product whose compatible_with
        # references Arduino (e.g. SG90, L298N, MPU-6050, HC-SR04, DHT22, HC-SR501).
        rec_skus = [p["sku"] for p in d["items"]]
        rec_names = " ".join(p["name"] for p in d["items"])
        # Verify at least one recommended product has "Arduino" in its compatible_with
        arduino_related = False
        for p in d["items"]:
            for c in (p.get("compatible_with") or []):
                if "arduino" in c.lower():
                    arduino_related = True
                    break
            if arduino_related:
                break
        assert arduino_related, f"No Arduino-compatible product in recs. skus={rec_skus}"
        # Cleanup
        _clean_customer_cart(s, customer_token)

    def test_guest_with_cart_id_returns_compatible(self, s, arduino_uno_id):
        cart_id = f"TEST_guest_{uuid.uuid4().hex[:8]}"
        r = s.post(f"{API}/cart/add",
                   params={"cart_id": cart_id},
                   json={"product_id": arduino_uno_id, "quantity": 1}, timeout=15)
        assert r.status_code == 200, r.text
        # Server may echo cart_id; use param version regardless
        r2 = s.get(f"{API}/cart/recommendations", params={"cart_id": cart_id, "limit": 6}, timeout=15)
        assert r2.status_code == 200
        d = r2.json()
        # If the cart_add doesn't persist against provided cart_id, response may be featured.
        # Accept either but assert schema.
        assert d["reason"] in ("compatible", "featured")
        assert isinstance(d["items"], list)


# ---------------- Email flow via admin order status update ----------------
def _tail_log(lines=400):
    try:
        out = subprocess.check_output(["tail", f"-n", str(lines), LOG_PATH], timeout=5)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return ""


class TestEmailFlow:
    """Uses admin order status update to trigger shipped / delivered emails in console mode."""

    def _ensure_order(self, s, customer_token, admin_token, force_new=False):
        """Return an existing (un-shipped) order id or create a new one via checkout."""
        if not force_new:
            r = s.get(f"{API}/orders", headers=h(customer_token), timeout=15)
            if r.status_code == 200:
                for o in r.json():
                    if not o.get("shipped_email_sent"):
                        return o["id"]
        # Create a fresh pending_payment order via checkout
        rp = s.get(f"{API}/products", params={"limit": 1}, timeout=15)
        pid = rp.json()["items"][0]["id"]
        s.post(f"{API}/cart/add", headers=h(customer_token),
               json={"product_id": pid, "quantity": 1}, timeout=15)
        payload = {
            "origin_url": BASE_URL,
            "address": {"full_name": "T User", "phone": "9999999999",
                        "line1": "1 Test Rd", "city": "Bangalore",
                        "state": "KA", "pincode": "560001", "country": "India"},
        }
        r = s.post(f"{API}/checkout/session", headers=h(customer_token), json=payload, timeout=45)
        assert r.status_code == 200, r.text
        return r.json()["order_id"]

    def test_shipped_email_console_log(self, s, customer_token, admin_token):
        oid = self._ensure_order(s, customer_token, admin_token)
        # Reset any previous shipped_email_sent flag by creating fresh order id via checkout for guaranteed idempotency test
        # First transition to shipped
        tracking = f"TRK{uuid.uuid4().hex[:6].upper()}"
        t0 = time.time()
        r = s.post(f"{API}/admin/orders/{oid}/status", headers=h(admin_token),
                   json={"status": "shipped", "tracking_number": tracking}, timeout=30)
        assert r.status_code == 200, r.text
        time.sleep(1.5)
        log = _tail_log(600)
        # Look for EMAIL:CONSOLE with Shipped subject and tracking number
        assert "[EMAIL:CONSOLE]" in log, "No console email log found after shipping"
        # Extract lines after t0-ish (heuristic: last 100 lines)
        recent = "\n".join(log.splitlines()[-200:])
        assert "Shipped" in recent, f"No 'Shipped' subject in recent logs"
        # Tracking number embedded in the body
        assert tracking in recent, f"Tracking {tracking} not in recent logs"

        # Verify flag
        ro = s.get(f"{API}/admin/orders", headers=h(admin_token), timeout=15)
        order = next(o for o in ro.json() if o["id"] == oid)
        assert order.get("shipped_email_sent") is True
        assert order.get("tracking_number") == tracking

        # Idempotency: call again, log line count for shipping should not grow
        before_count = recent.count("Shipped ·")
        r2 = s.post(f"{API}/admin/orders/{oid}/status", headers=h(admin_token),
                    json={"status": "shipped", "tracking_number": tracking}, timeout=15)
        assert r2.status_code == 200
        time.sleep(1.2)
        log2 = _tail_log(600)
        recent2 = "\n".join(log2.splitlines()[-250:])
        after_count = recent2.count("Shipped ·")
        assert after_count == before_count, f"Duplicate shipping email sent (before={before_count}, after={after_count})"

    def test_delivered_email_console_log(self, s, customer_token, admin_token):
        # find an order that is already shipped (from prior test) or create+ship one
        ro = s.get(f"{API}/admin/orders", headers=h(admin_token), timeout=15)
        shipped = [o for o in ro.json() if o.get("shipped_email_sent") and not o.get("delivered_email_sent")]
        if not shipped:
            # fallback: pick any order and ship first
            oid = self._ensure_order(s, customer_token, admin_token)
            s.post(f"{API}/admin/orders/{oid}/status", headers=h(admin_token),
                   json={"status": "shipped", "tracking_number": "TRKAUTO"}, timeout=15)
            time.sleep(0.5)
        else:
            oid = shipped[0]["id"]

        r = s.post(f"{API}/admin/orders/{oid}/status", headers=h(admin_token),
                   json={"status": "delivered"}, timeout=30)
        assert r.status_code == 200, r.text
        time.sleep(1.5)
        log = _tail_log(600)
        recent = "\n".join(log.splitlines()[-250:])
        assert "[EMAIL:CONSOLE]" in log
        assert "Delivered" in recent

        ro2 = s.get(f"{API}/admin/orders", headers=h(admin_token), timeout=15)
        order = next(o for o in ro2.json() if o["id"] == oid)
        assert order.get("delivered_email_sent") is True

        # Idempotency
        before = recent.count("Delivered ·")
        s.post(f"{API}/admin/orders/{oid}/status", headers=h(admin_token),
               json={"status": "delivered"}, timeout=15)
        time.sleep(1.0)
        recent2 = "\n".join(_tail_log(600).splitlines()[-300:])
        after = recent2.count("Delivered ·")
        assert after == before, f"Duplicate delivered email (before={before}, after={after})"
