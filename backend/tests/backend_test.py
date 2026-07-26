"""ElectronicHub backend API test suite - covers auth, catalog, cart, coupons,
wishlist, reviews, checkout, orders, and admin endpoints."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to reading frontend .env at test-time
    from pathlib import Path
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@electronichub.io", "password": "Admin@12345"}
CUSTOMER = {"email": "customer@electronichub.io", "password": "Customer@12345"}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def customer_token(s):
    r = s.post(f"{API}/auth/login", json=CUSTOMER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def product_ids(s):
    r = s.get(f"{API}/products", params={"limit": 5}, timeout=30)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["items"]]
    assert len(ids) >= 2
    return ids


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Health / basic ----------
class TestHealth:
    def test_root(self, s):
        r = s.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_categories(self, s):
        r = s.get(f"{API}/categories", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) == 8
        assert {c["id"] for c in data} >= {"sensors", "microcontrollers", "kits"}


# ---------- Products ----------
class TestProducts:
    def test_list_products(self, s):
        r = s.get(f"{API}/products", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d
        assert d["total"] >= 10

    def test_filter_by_category(self, s):
        r = s.get(f"{API}/products", params={"category": "sensors"}, timeout=15)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["category"] == "sensors"

    def test_filter_featured(self, s):
        r = s.get(f"{API}/products", params={"featured": "true"}, timeout=15)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["is_featured"] is True

    def test_search(self, s):
        r = s.get(f"{API}/products", params={"search": "arduino"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_sort_price_asc(self, s):
        r = s.get(f"{API}/products", params={"sort": "price_asc", "limit": 5}, timeout=15)
        prices = [p["price"] for p in r.json()["items"]]
        assert prices == sorted(prices)

    def test_filters_endpoint(self, s):
        r = s.get(f"{API}/products/filters", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "brands" in d and "voltages" in d and "interfaces" in d
        assert len(d["brands"]) >= 1

    def test_product_detail(self, s, product_ids):
        r = s.get(f"{API}/products/{product_ids[0]}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "product" in d and "related" in d and "reviews" in d
        assert isinstance(d["related"], list)

    def test_product_detail_404(self, s):
        r = s.get(f"{API}/products/nonexistent-id-xyz", timeout=15)
        assert r.status_code == 404


# ---------- Auth ----------
class TestAuth:
    def test_login_customer(self, s):
        r = s.post(f"{API}/auth/login", json=CUSTOMER, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and d["user"]["role"] == "customer"

    def test_login_admin(self, s):
        r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_login_invalid(self, s):
        r = s.post(f"{API}/auth/login", json={"email": "x@y.com", "password": "bad"}, timeout=15)
        assert r.status_code == 401

    def test_signup_and_me(self, s):
        email = f"TEST_signup_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/signup", json={"name": "Test", "email": email, "password": "Pass@1234"}, timeout=15)
        assert r.status_code == 200, r.text
        tok = r.json()["token"]
        r2 = s.get(f"{API}/auth/me", headers=h(tok), timeout=15)
        assert r2.status_code == 200
        assert r2.json()["email"] == email.lower()

    def test_signup_duplicate(self, s):
        r = s.post(f"{API}/auth/signup", json={"name": "x", "email": CUSTOMER["email"], "password": "abc12345"}, timeout=15)
        assert r.status_code == 400

    def test_me_no_token(self, s):
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---------- Cart ----------
class TestCart:
    def test_cart_add_get_update_remove(self, s, customer_token, product_ids):
        pid = product_ids[0]
        # Clean first
        s.delete(f"{API}/cart/item/{pid}", headers=h(customer_token), timeout=15)
        r = s.post(f"{API}/cart/add", headers=h(customer_token),
                   json={"product_id": pid, "quantity": 2}, timeout=15)
        assert r.status_code == 200
        r = s.get(f"{API}/cart", headers=h(customer_token), timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        found = [x for x in items if x["product_id"] == pid]
        assert found and found[0]["quantity"] >= 2
        assert "product" in found[0]
        # update
        r = s.post(f"{API}/cart/update", headers=h(customer_token),
                   json={"product_id": pid, "quantity": 5}, timeout=15)
        assert r.status_code == 200
        r = s.get(f"{API}/cart", headers=h(customer_token), timeout=15)
        items = [x for x in r.json()["items"] if x["product_id"] == pid]
        assert items[0]["quantity"] == 5
        # remove
        r = s.delete(f"{API}/cart/item/{pid}", headers=h(customer_token), timeout=15)
        assert r.status_code == 200


# ---------- Coupons ----------
class TestCoupons:
    def test_welcome10(self, s):
        r = s.post(f"{API}/coupons/validate", json={"code": "WELCOME10", "subtotal": 600}, timeout=15)
        assert r.status_code == 200
        assert r.json()["discount"] == 60

    def test_maker100(self, s):
        r = s.post(f"{API}/coupons/validate", json={"code": "MAKER100", "subtotal": 1500}, timeout=15)
        assert r.status_code == 200
        assert r.json()["discount"] == 100

    def test_invalid_coupon(self, s):
        r = s.post(f"{API}/coupons/validate", json={"code": "FAKE", "subtotal": 1000}, timeout=15)
        assert r.status_code == 404

    def test_min_order(self, s):
        r = s.post(f"{API}/coupons/validate", json={"code": "WELCOME10", "subtotal": 100}, timeout=15)
        assert r.status_code == 400


# ---------- Wishlist ----------
class TestWishlist:
    def test_toggle(self, s, customer_token, product_ids):
        pid = product_ids[1]
        r1 = s.post(f"{API}/wishlist/toggle/{pid}", headers=h(customer_token), timeout=15)
        assert r1.status_code == 200
        state1 = r1.json()["in_wishlist"]
        r2 = s.post(f"{API}/wishlist/toggle/{pid}", headers=h(customer_token), timeout=15)
        assert r2.json()["in_wishlist"] == (not state1)
        r3 = s.get(f"{API}/wishlist", headers=h(customer_token), timeout=15)
        assert r3.status_code == 200
        assert isinstance(r3.json(), list)


# ---------- Reviews ----------
class TestReviews:
    def test_create_review(self, s, customer_token, product_ids):
        pid = product_ids[0]
        r = s.post(f"{API}/reviews", headers=h(customer_token),
                   json={"product_id": pid, "rating": 5, "comment": "TEST_review great"},
                   timeout=15)
        assert r.status_code == 200
        assert r.json()["rating"] == 5
        # verify on product
        r2 = s.get(f"{API}/products/{pid}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["product"]["rating_count"] >= 1


# ---------- Checkout ----------
class TestCheckout:
    def test_create_session(self, s, customer_token, product_ids):
        pid = product_ids[0]
        # ensure cart has item
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
        d = r.json()
        assert "checkout_url" in d and "session_id" in d and "order_id" in d
        assert d["checkout_url"].startswith("http")
        # Verify order is created with pending_payment
        r2 = s.get(f"{API}/orders", headers=h(customer_token), timeout=15)
        assert r2.status_code == 200
        orders = r2.json()
        assert any(o["id"] == d["order_id"] and o["status"] == "pending_payment" for o in orders)
        # Test payment status (unauthenticated) - polling
        r3 = s.get(f"{API}/payments/status/{d['session_id']}", timeout=30)
        assert r3.status_code == 200
        s_body = r3.json()
        assert s_body["session_id"] == d["session_id"]
        assert "payment_status" in s_body


# ---------- Orders ----------
class TestOrders:
    def test_list_orders_authenticated(self, s, customer_token):
        r = s.get(f"{API}/orders", headers=h(customer_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_orders_requires_auth(self, s):
        r = s.get(f"{API}/orders", timeout=15)
        assert r.status_code == 401


# ---------- Admin ----------
class TestAdmin:
    def test_dashboard(self, s, admin_token):
        r = s.get(f"{API}/admin/dashboard", headers=h(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_products", "total_orders", "total_users", "revenue", "low_stock", "recent_orders"]:
            assert k in d

    def test_dashboard_forbidden_for_customer(self, s, customer_token):
        r = s.get(f"{API}/admin/dashboard", headers=h(customer_token), timeout=15)
        assert r.status_code == 403

    def test_admin_product_crud(self, s, admin_token):
        payload = {
            "sku": f"TEST_{uuid.uuid4().hex[:6]}", "name": "TEST_Product",
            "category": "sensors", "brand": "TEST", "price": 100.0, "stock_qty": 10,
            "description": "test", "specs": {"a": "b"}, "voltage": "5V", "interface": "I2C",
            "images": [], "is_active": True, "is_featured": False, "tags": ["test"],
        }
        r = s.post(f"{API}/admin/products", headers=h(admin_token), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # update
        payload["name"] = "TEST_Product_Updated"
        payload["price"] = 150.0
        r = s.put(f"{API}/admin/products/{pid}", headers=h(admin_token), json=payload, timeout=15)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Product_Updated"
        # verify via get
        r2 = s.get(f"{API}/products/{pid}", timeout=15)
        assert r2.json()["product"]["price"] == 150.0
        # delete
        r = s.delete(f"{API}/admin/products/{pid}", headers=h(admin_token), timeout=15)
        assert r.status_code == 200
        r2 = s.get(f"{API}/products/{pid}", timeout=15)
        assert r2.status_code == 404

    def test_admin_orders_list(self, s, admin_token):
        r = s.get(f"{API}/admin/orders", headers=h(admin_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_order_status_update(self, s, admin_token):
        r = s.get(f"{API}/admin/orders", headers=h(admin_token), timeout=15)
        orders = r.json()
        if not orders:
            pytest.skip("no orders to update")
        oid = orders[0]["id"]
        r2 = s.post(f"{API}/admin/orders/{oid}/status", headers=h(admin_token),
                    json={"status": "shipped", "tracking_number": "TRACK123"}, timeout=15)
        assert r2.status_code == 200
        r3 = s.get(f"{API}/orders/{oid}", headers=h(admin_token), timeout=15)
        assert r3.json()["status"] == "shipped"
        assert r3.json()["tracking_number"] == "TRACK123"

    def test_admin_coupons(self, s, admin_token):
        code = f"TEST{uuid.uuid4().hex[:6].upper()}"
        r = s.post(f"{API}/admin/coupons", headers=h(admin_token),
                   json={"code": code, "discount_type": "flat", "discount_value": 50,
                         "min_order": 100, "max_uses": 10, "active": True}, timeout=15)
        assert r.status_code == 200
        r2 = s.get(f"{API}/admin/coupons", headers=h(admin_token), timeout=15)
        assert any(c["code"] == code for c in r2.json())
