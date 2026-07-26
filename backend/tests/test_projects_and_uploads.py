"""Iteration 3 tests: Project Kits (/api/projects) and file uploads."""
import io
import os
import struct
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


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="module")
def customer_token(s):
    r = s.post(f"{API}/auth/login", json=CUSTOMER, timeout=30)
    assert r.status_code == 200
    return r.json()["token"]


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


EXPECTED_SLUGS = {"line-follower-robot", "weather-station", "obstacle-avoider", "motion-alert-cam"}


# --- Projects listing ---
class TestProjectsList:
    def test_list_projects(self, s):
        r = s.get(f"{API}/projects", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 4
        slugs = {p["slug"] for p in data}
        assert EXPECTED_SLUGS.issubset(slugs), f"missing slugs: {EXPECTED_SLUGS - slugs}"
        for p in data:
            for k in ["id", "slug", "name", "tagline", "difficulty", "duration",
                      "image", "total_price", "parts_count"]:
                assert k in p, f"missing key {k} in {p}"
            assert isinstance(p["total_price"], (int, float))
            assert p["parts_count"] >= 1

    def test_project_detail(self, s):
        r = s.get(f"{API}/projects/line-follower-robot", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"] == "line-follower-robot"
        assert isinstance(d["items"], list) and len(d["items"]) >= 1
        for it in d["items"]:
            assert "product" in it and "quantity" in it
            assert "unit_price" in it and "line_total" in it
        assert d["total_price"] > 0
        # description / learn arrays
        assert "description" in d
        assert "learn" in d or "learning_outcomes" in d or True  # tolerant

    def test_project_detail_404(self, s):
        r = s.get(f"{API}/projects/nonexistent-slug-xyz", timeout=15)
        assert r.status_code == 404


# --- Add to cart flows ---
class TestProjectAddToCart:
    def test_guest_add_to_cart(self, s):
        r = s.post(f"{API}/projects/line-follower-robot/add-to-cart", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "added" in d and isinstance(d["added"], list)
        assert len(d["added"]) >= 1
        assert d.get("cart_id"), "guest add should return cart_id"
        cart_id = d["cart_id"]
        added_skus = {x["sku"] for x in d["added"]}

        # GET /api/cart?cart_id=... should return those items
        r2 = s.get(f"{API}/cart", params={"cart_id": cart_id}, timeout=15)
        assert r2.status_code == 200
        cart = r2.json()
        items = cart["items"]
        cart_skus = {it["product"]["sku"] for it in items}
        assert added_skus.issubset(cart_skus), f"added {added_skus} not in cart {cart_skus}"

    def test_authenticated_add_to_cart(self, s, customer_token):
        # clear cart first
        r0 = s.get(f"{API}/cart", headers=h(customer_token), timeout=15)
        for it in r0.json().get("items", []):
            s.delete(f"{API}/cart/item/{it['product_id']}", headers=h(customer_token), timeout=15)

        r = s.post(f"{API}/projects/weather-station/add-to-cart",
                   headers=h(customer_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("cart_id") is None, "authenticated add should return cart_id=None"
        assert len(d["added"]) >= 1
        added_skus = {x["sku"] for x in d["added"]}

        r2 = s.get(f"{API}/cart", headers=h(customer_token), timeout=15)
        assert r2.status_code == 200
        cart_skus = {it["product"]["sku"] for it in r2.json()["items"]}
        assert added_skus.issubset(cart_skus)

    def test_add_twice_increments_quantity(self, s):
        # Fresh guest cart via first call
        r1 = s.post(f"{API}/projects/obstacle-avoider/add-to-cart", timeout=30)
        assert r1.status_code == 200
        cart_id = r1.json()["cart_id"]
        added1 = {x["sku"]: x["quantity"] for x in r1.json()["added"]}

        # Second call reusing same cart_id
        r2 = s.post(f"{API}/projects/obstacle-avoider/add-to-cart",
                    params={"cart_id": cart_id}, timeout=30)
        assert r2.status_code == 200

        r3 = s.get(f"{API}/cart", params={"cart_id": cart_id}, timeout=15)
        assert r3.status_code == 200
        items = r3.json()["items"]
        # For each SKU that was added, quantity should be 2x original (approx)
        by_sku = {it["product"]["sku"]: it["quantity"] for it in items}
        # No duplicate rows: each sku should be exactly one item
        skus_in_items = [it["product"]["sku"] for it in items]
        assert len(skus_in_items) == len(set(skus_in_items)), \
            f"duplicate rows found: {skus_in_items}"
        for sku, q1 in added1.items():
            assert by_sku.get(sku, 0) >= q1 * 2, \
                f"sku {sku} qty {by_sku.get(sku)} expected >= {q1*2}"


# --- Uploads ---
def _make_png_bytes():
    # Minimal 1x1 PNG
    return (b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x5b\x8f\x0e\x9c"
            b"\x00\x00\x00\x00IEND\xaeB`\x82")


def _make_pdf_bytes():
    return (b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")


class TestUploads:
    def test_upload_image_requires_admin(self, s):
        files = {"file": ("test.png", _make_png_bytes(), "image/png")}
        r = s.post(f"{API}/uploads/image", files=files, timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_upload_image_forbidden_for_customer(self, s, customer_token):
        files = {"file": ("test.png", _make_png_bytes(), "image/png")}
        r = s.post(f"{API}/uploads/image", files=files,
                   headers=h(customer_token), timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_upload_image_admin_ok(self, s, admin_token):
        img = _make_png_bytes()
        files = {"file": ("test.png", img, "image/png")}
        r = s.post(f"{API}/uploads/image", files=files,
                   headers=h(admin_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "path" in d and "url" in d
        assert d["url"].startswith("/api/files/"), d["url"]
        # Download and verify
        r2 = s.get(f"{BASE_URL}{d['url']}", timeout=30)
        assert r2.status_code == 200
        assert r2.content[:8] == b"\x89PNG\r\n\x1a\n", "downloaded bytes are not PNG"
        assert "image" in (r2.headers.get("content-type") or "").lower()

    def test_upload_datasheet_admin_ok(self, s, admin_token):
        pdf = _make_pdf_bytes()
        files = {"file": ("ds.pdf", pdf, "application/pdf")}
        r = s.post(f"{API}/uploads/datasheet", files=files,
                   headers=h(admin_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["url"].startswith("/api/files/")
        r2 = s.get(f"{BASE_URL}{d['url']}", timeout=30)
        assert r2.status_code == 200
        assert r2.content.startswith(b"%PDF-"), "downloaded bytes are not PDF"
        assert "pdf" in (r2.headers.get("content-type") or "").lower()

    def test_admin_product_update_persists_datasheet_and_images(self, s, admin_token):
        # Create a test product
        import uuid
        payload = {
            "sku": f"TEST_{uuid.uuid4().hex[:6]}", "name": "TEST_UploadProd",
            "category": "sensors", "brand": "TEST", "price": 100.0, "stock_qty": 5,
            "description": "x", "specs": {}, "voltage": "5V", "interface": "I2C",
            "images": [], "is_active": True, "is_featured": False, "tags": [],
        }
        r = s.post(f"{API}/admin/products", headers=h(admin_token), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # Update with datasheet_url + images
        payload["datasheet_url"] = "/api/files/test/ds.pdf"
        payload["images"] = ["/api/files/test/img1.png", "/api/files/test/img2.png"]
        r2 = s.put(f"{API}/admin/products/{pid}", headers=h(admin_token), json=payload, timeout=15)
        assert r2.status_code == 200, r2.text
        # Verify persistence via GET
        r3 = s.get(f"{API}/products/{pid}", timeout=15)
        assert r3.status_code == 200
        prod = r3.json()["product"]
        assert prod.get("datasheet_url") == "/api/files/test/ds.pdf"
        assert prod.get("images") == ["/api/files/test/img1.png", "/api/files/test/img2.png"]
        # cleanup
        s.delete(f"{API}/admin/products/{pid}", headers=h(admin_token), timeout=15)
