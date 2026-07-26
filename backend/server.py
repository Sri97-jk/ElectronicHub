from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query, Header, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os, logging, uuid, bcrypt, jwt, requests, stripe, hmac, hashlib, json
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from emails import send_order_confirmation, send_shipping_notification, send_delivered_notification
try:
    import razorpay
except ImportError:
    razorpay = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# --- Config
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGO = "HS256"
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = os.environ.get("APP_NAME", "electronichub")

# stripe (Flow B - BYOK using default sk_test_emergent)
try:
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest
    )
except ImportError:
    StripeCheckout = None
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")

# Razorpay
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
_rzp = None
if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    _rzp = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    logging.info(f"Razorpay client initialized (key_id={RAZORPAY_KEY_ID[:12]}…)")
else:
    logging.info("Razorpay NOT configured — set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env")

# --- DB
async_client = AsyncIOMotorClient(mongo_url)
db = async_client[db_name]
sync_client = MongoClient(mongo_url)
sync_db = sync_client[db_name]

# --- Storage helpers
storage_key = None
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# --- App
app = FastAPI(title="ElectronicHub API")
api_router = APIRouter(prefix="/api")

# --- Auth helpers
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False
def make_token(user_id: str, role: str) -> str:
    payload = {"sub": user_id, "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(days=30)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

security = HTTPBearer(auto_error=False)

async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")

async def get_optional_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        return await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    except jwt.PyJWTError:
        return None

async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return user

# --- Models
class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ProductIn(BaseModel):
    sku: str
    name: str
    category: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    price: float
    discount_price: Optional[float] = None
    stock_qty: int = 0
    low_stock_threshold: int = 5
    description: str = ""
    specs: Dict[str, Any] = {}
    compatible_with: List[str] = []
    voltage: Optional[str] = None
    interface: Optional[str] = None
    images: List[str] = []
    datasheet_url: Optional[str] = None
    is_active: bool = True
    is_featured: bool = False
    tags: List[str] = []

class ReviewIn(BaseModel):
    product_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""

class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)

class AddressIn(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = ""
    city: str
    state: str
    pincode: str
    country: str = "India"

class CheckoutIn(BaseModel):
    origin_url: str
    address: AddressIn
    coupon_code: Optional[str] = None

class CouponIn(BaseModel):
    code: str
    discount_type: str  # "percent" or "flat"
    discount_value: float
    min_order: float = 0
    max_uses: int = 100
    active: bool = True

# --- Auth routes
@api_router.post("/auth/signup")
async def signup(data: SignupIn):
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id, "name": data.name, "email": data.email.lower(),
        "password_hash": hash_pw(data.password), "role": "customer",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = make_token(user_id, "customer")
    return {"token": token, "user": {"id": user_id, "name": data.name, "email": data.email.lower(), "role": "customer"}}

@api_router.post("/auth/login")
async def login(data: LoginIn):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not verify_pw(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(user["id"], user["role"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}}

@api_router.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user

# --- Categories
CATEGORIES = [
    {"id": "sensors", "name": "Sensors", "icon": "SensorCog"},
    {"id": "microcontrollers", "name": "Microcontrollers", "icon": "Cpu"},
    {"id": "processors", "name": "Processors / SBCs", "icon": "CircuitBoard"},
    {"id": "robotics", "name": "Robotic Parts", "icon": "Robot"},
    {"id": "power", "name": "Power", "icon": "BatteryCharging"},
    {"id": "connectivity", "name": "Connectivity", "icon": "Wifi"},
    {"id": "tools", "name": "Tools & Accessories", "icon": "Wrench"},
    {"id": "kits", "name": "Kits & Bundles", "icon": "Package"},
]

@api_router.get("/categories")
async def get_categories():
    return CATEGORIES

# --- Products
@api_router.get("/products")
async def list_products(
    category: Optional[str] = None, search: Optional[str] = None,
    brand: Optional[str] = None, min_price: Optional[float] = None,
    max_price: Optional[float] = None, voltage: Optional[str] = None,
    interface: Optional[str] = None, in_stock: Optional[bool] = None,
    featured: Optional[bool] = None, sort: str = "newest",
    limit: int = 50, skip: int = 0,
):
    q: Dict[str, Any] = {"is_active": True}
    if category: q["category"] = category
    if brand: q["brand"] = brand
    if voltage: q["voltage"] = voltage
    if interface: q["interface"] = interface
    if in_stock: q["stock_qty"] = {"$gt": 0}
    if featured is not None: q["is_featured"] = featured
    if min_price is not None or max_price is not None:
        pr = {}
        if min_price is not None: pr["$gte"] = min_price
        if max_price is not None: pr["$lte"] = max_price
        q["price"] = pr
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"sku": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]
    sort_map = {"newest": [("created_at", -1)], "price_asc": [("price", 1)],
                "price_desc": [("price", -1)], "rating": [("rating_avg", -1)]}
    cursor = db.products.find(q, {"_id": 0}).sort(sort_map.get(sort, sort_map["newest"])).skip(skip).limit(limit)
    items = await cursor.to_list(limit)
    total = await db.products.count_documents(q)
    return {"items": items, "total": total}

@api_router.get("/products/filters")
async def product_filters(category: Optional[str] = None):
    q: Dict[str, Any] = {"is_active": True}
    if category: q["category"] = category
    brands = await db.products.distinct("brand", q)
    voltages = await db.products.distinct("voltage", q)
    interfaces = await db.products.distinct("interface", q)
    return {
        "brands": [b for b in brands if b],
        "voltages": [v for v in voltages if v],
        "interfaces": [i for i in interfaces if i],
    }

@api_router.get("/products/{product_id}")
async def product_detail(product_id: str):
    prod = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not prod:
        raise HTTPException(404, "Product not found")
    # related products (same category)
    related = await db.products.find(
        {"category": prod["category"], "id": {"$ne": product_id}, "is_active": True},
        {"_id": 0}
    ).limit(6).to_list(6)
    reviews = await db.reviews.find({"product_id": product_id}, {"_id": 0}).sort([("created_at", -1)]).to_list(50)
    return {"product": prod, "related": related, "reviews": reviews}

# --- Reviews
@api_router.post("/reviews")
async def create_review(data: ReviewIn, user=Depends(get_current_user)):
    doc = {
        "id": str(uuid.uuid4()), "product_id": data.product_id,
        "user_id": user["id"], "user_name": user["name"],
        "rating": data.rating, "comment": data.comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.reviews.insert_one(doc)
    # update product rating
    all_rev = await db.reviews.find({"product_id": data.product_id}).to_list(1000)
    avg = sum(r["rating"] for r in all_rev) / len(all_rev)
    await db.products.update_one({"id": data.product_id},
        {"$set": {"rating_avg": round(avg, 2), "rating_count": len(all_rev)}})
    doc.pop("_id", None)
    return doc

# --- Cart (user or guest via cart_id)
@api_router.get("/cart")
async def get_cart(user=Depends(get_optional_user), cart_id: Optional[str] = None):
    key = {"user_id": user["id"]} if user else {"cart_id": cart_id or ""}
    items = await db.cart_items.find(key, {"_id": 0}).to_list(200)
    enriched = []
    for it in items:
        prod = await db.products.find_one({"id": it["product_id"]}, {"_id": 0})
        if prod:
            enriched.append({**it, "product": prod})
    return {"items": enriched}

@api_router.post("/cart/add")
async def cart_add(data: CartItemIn, user=Depends(get_optional_user), cart_id: Optional[str] = None):
    if user:
        key = {"user_id": user["id"], "product_id": data.product_id}
    else:
        if not cart_id:
            cart_id = str(uuid.uuid4())
        key = {"cart_id": cart_id, "product_id": data.product_id}
    existing = await db.cart_items.find_one(key)
    if existing:
        await db.cart_items.update_one(key, {"$inc": {"quantity": data.quantity}})
    else:
        doc = {**key, "id": str(uuid.uuid4()), "quantity": data.quantity,
               "created_at": datetime.now(timezone.utc).isoformat()}
        await db.cart_items.insert_one(doc)
    return {"ok": True, "cart_id": cart_id if not user else None}

@api_router.post("/cart/update")
async def cart_update(data: CartItemIn, user=Depends(get_optional_user), cart_id: Optional[str] = None):
    key = {"user_id": user["id"], "product_id": data.product_id} if user else {"cart_id": cart_id, "product_id": data.product_id}
    if data.quantity <= 0:
        await db.cart_items.delete_one(key)
    else:
        await db.cart_items.update_one(key, {"$set": {"quantity": data.quantity}})
    return {"ok": True}

@api_router.delete("/cart/item/{product_id}")
async def cart_remove(product_id: str, user=Depends(get_optional_user), cart_id: Optional[str] = None):
    key = {"user_id": user["id"], "product_id": product_id} if user else {"cart_id": cart_id, "product_id": product_id}
    await db.cart_items.delete_one(key)
    return {"ok": True}

@api_router.get("/cart/recommendations")
async def cart_recommendations(user=Depends(get_optional_user), cart_id: Optional[str] = None, limit: int = 6):
    """Returns products that pair well with items currently in the cart.
    Priority: (1) products in `compatible_with` tags of cart items,
    (2) products sharing tags/category with cart items."""
    key = {"user_id": user["id"]} if user else {"cart_id": cart_id or ""}
    cart_items = await db.cart_items.find(key).to_list(200)
    if not cart_items:
        # If cart is empty, return featured products
        featured = await db.products.find(
            {"is_active": True, "is_featured": True}, {"_id": 0}
        ).limit(limit).to_list(limit)
        return {"items": featured, "reason": "featured"}
    cart_product_ids = [it["product_id"] for it in cart_items]
    cart_products = await db.products.find(
        {"id": {"$in": cart_product_ids}}, {"_id": 0}
    ).to_list(len(cart_product_ids))
    # Collect compatibility hints from cart products
    compat_names = set()
    cats = set()
    tags = set()
    for p in cart_products:
        for c in (p.get("compatible_with") or []):
            compat_names.add(c)
        if p.get("category"): cats.add(p["category"])
        for t in (p.get("tags") or []):
            tags.add(t)
    # Score products: name-match on compatible_with, then shared tags, then shared category
    query = {
        "id": {"$nin": cart_product_ids},
        "is_active": True,
        "stock_qty": {"$gt": 0},
    }
    candidates = await db.products.find(query, {"_id": 0}).to_list(200)
    scored = []
    for c in candidates:
        score = 0
        # If the candidate's name/sku matches one of the compatibility strings from cart items
        for cn in compat_names:
            if cn.lower() in (c.get("name", "") + " " + c.get("brand", "")).lower():
                score += 5
        # Or if the candidate's own compatible_with references any cart product name
        for cp in cart_products:
            for cn in (c.get("compatible_with") or []):
                if cn.lower() in cp.get("name", "").lower():
                    score += 5
        # Shared tags
        shared_tags = tags.intersection(set(c.get("tags") or []))
        score += len(shared_tags) * 2
        # Same category, different item
        if c.get("category") in cats:
            score += 1
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    picks = [c for _, c in scored[:limit]]
    if len(picks) < limit:
        # Backfill with featured products from same categories
        fill = await db.products.find(
            {"category": {"$in": list(cats)}, "id": {"$nin": cart_product_ids + [p["id"] for p in picks]},
             "is_active": True}, {"_id": 0}
        ).limit(limit - len(picks)).to_list(limit - len(picks))
        picks.extend(fill)
    return {"items": picks[:limit], "reason": "compatible"}

# --- Coupons
@api_router.post("/coupons/validate")
async def validate_coupon(payload: dict):
    code = payload.get("code", "").upper()
    subtotal = float(payload.get("subtotal", 0))
    c = await db.coupons.find_one({"code": code, "active": True}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Invalid coupon")
    if subtotal < c.get("min_order", 0):
        raise HTTPException(400, f"Min order ₹{c['min_order']} required")
    if c["discount_type"] == "percent":
        discount = subtotal * (c["discount_value"] / 100)
    else:
        discount = c["discount_value"]
    return {"coupon": c, "discount": round(discount, 2)}

# --- Checkout & payments
async def compute_cart_totals(items: list, coupon_code: Optional[str] = None):
    subtotal = 0
    line_items = []
    for it in items:
        prod = await db.products.find_one({"id": it["product_id"]}, {"_id": 0})
        if not prod: continue
        price = prod.get("discount_price") or prod["price"]
        line_total = price * it["quantity"]
        subtotal += line_total
        line_items.append({"product_id": prod["id"], "name": prod["name"], "sku": prod["sku"],
                           "quantity": it["quantity"], "unit_price": price, "line_total": line_total,
                           "image": prod.get("images", [""])[0] if prod.get("images") else ""})
    discount = 0
    coupon = None
    if coupon_code:
        c = await db.coupons.find_one({"code": coupon_code.upper(), "active": True}, {"_id": 0})
        if c and subtotal >= c.get("min_order", 0):
            coupon = c
            discount = subtotal * (c["discount_value"] / 100) if c["discount_type"] == "percent" else c["discount_value"]
    shipping = 0 if subtotal >= 999 else 79
    tax = round((subtotal - discount) * 0.18, 2)  # 18% GST
    total = round(subtotal - discount + shipping + tax, 2)
    return {"subtotal": round(subtotal, 2), "discount": round(discount, 2),
            "shipping": shipping, "tax": tax, "total": total,
            "line_items": line_items, "coupon": coupon}

@api_router.post("/checkout/session")
async def create_checkout(data: CheckoutIn, user=Depends(get_optional_user), cart_id: Optional[str] = None):
    if not StripeCheckout:
        raise HTTPException(500, "Stripe not available")
    key = {"user_id": user["id"]} if user else {"cart_id": cart_id or ""}
    items = await db.cart_items.find(key).to_list(200)
    if not items:
        raise HTTPException(400, "Cart is empty")
    totals = await compute_cart_totals(items, data.coupon_code)
    # Create order (pending)
    order_id = str(uuid.uuid4())
    order_doc = {
        "id": order_id, "user_id": user["id"] if user else None,
        "guest_email": None,
        "status": "pending_payment",
        "payment_status": "pending",
        "items": totals["line_items"],
        "subtotal": totals["subtotal"], "discount": totals["discount"],
        "shipping": totals["shipping"], "tax": totals["tax"],
        "total": totals["total"], "currency": "INR",
        "coupon": totals["coupon"]["code"] if totals["coupon"] else None,
        "address": data.address.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tracking_number": None,
    }
    await db.orders.insert_one(order_doc)
    # Stripe checkout
    host_url = data.origin_url.rstrip("/")
    success_url = f"{host_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/payment/cancel"
    stripe_ck = StripeCheckout(api_key=STRIPE_API_KEY,
        webhook_url=f"{host_url}/api/webhook/stripe")
    # Charge in USD equivalent for sandbox (INR->USD approx /85) OR use INR
    amount_usd = round(totals["total"] / 85, 2)
    req = CheckoutSessionRequest(
        amount=amount_usd, currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"order_id": order_id, "user_id": user["id"] if user else "guest"},
    )
    session = await stripe_ck.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "order_id": order_id,
        "amount": amount_usd, "currency": "usd",
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.orders.update_one({"id": order_id},
        {"$set": {"stripe_session_id": session.session_id}})
    return {"checkout_url": session.url, "session_id": session.session_id, "order_id": order_id}

@api_router.get("/payments/status/{session_id}")
async def payment_status(session_id: str):
    if not StripeCheckout:
        raise HTTPException(500, "Stripe not available")
    rec = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Not found")
    if rec.get("payment_status") != "paid":
        try:
            stripe_ck = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
            status = await stripe_ck.get_checkout_status(session_id)
            if status.payment_status == "paid" or status.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid",
                              "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                await db.orders.update_one(
                    {"stripe_session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"payment_status": "paid", "status": "confirmed",
                              "confirmed_at": datetime.now(timezone.utc).isoformat()}}
                )
                # Decrement stock and clear cart
                order = await db.orders.find_one({"stripe_session_id": session_id})
                if order:
                    for it in order["items"]:
                        await db.products.update_one({"id": it["product_id"]},
                            {"$inc": {"stock_qty": -it["quantity"]}})
                    if order.get("user_id"):
                        await db.cart_items.delete_many({"user_id": order["user_id"]})
                    # Send order confirmation email
                    if not order.get("email_sent"):
                        recipient = None
                        if order.get("user_id"):
                            u = await db.users.find_one({"id": order["user_id"]}, {"_id": 0, "email": 1})
                            if u: recipient = u.get("email")
                        recipient = recipient or order.get("guest_email")
                        if recipient:
                            try:
                                await send_order_confirmation(order, recipient)
                                await db.orders.update_one({"id": order["id"]},
                                    {"$set": {"email_sent": True}})
                            except Exception as e:
                                logging.error(f"Order confirmation email failed: {e}")
                    rec = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        except Exception as e:
            logging.error(f"Status check error: {e}")
    return {"session_id": rec["session_id"], "status": rec["status"],
            "payment_status": rec["payment_status"], "order_id": rec.get("order_id")}

@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    if not StripeCheckout:
        return {"status": "no_stripe"}
    try:
        stripe_ck = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
        result = await stripe_ck.handle_webhook(body, sig)
        if result.payment_status == "paid":
            await db.payment_transactions.update_one(
                {"session_id": result.session_id, "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "completed", "payment_status": "paid"}}
            )
            await db.orders.update_one(
                {"stripe_session_id": result.session_id, "payment_status": {"$ne": "paid"}},
                {"$set": {"payment_status": "paid", "status": "confirmed"}}
            )
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return {"status": "ok"}

# --- Razorpay (primary payment gateway for India / INR) ---
@api_router.get("/config/razorpay")
async def razorpay_config():
    """Expose the public key id so the frontend can initialize the checkout modal."""
    return {"key_id": RAZORPAY_KEY_ID, "enabled": _rzp is not None}


@api_router.post("/razorpay/order")
async def razorpay_create_order(data: CheckoutIn, user=Depends(get_optional_user), cart_id: Optional[str] = None):
    """Create a Razorpay order from the current cart. Returns the order details
    so the frontend can open the Razorpay Checkout modal."""
    if not _rzp:
        raise HTTPException(503, "Razorpay is not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in the server .env")
    key = {"user_id": user["id"]} if user else {"cart_id": cart_id or ""}
    items = await db.cart_items.find(key).to_list(200)
    if not items:
        raise HTTPException(400, "Cart is empty")
    totals = await compute_cart_totals(items, data.coupon_code)
    order_id = str(uuid.uuid4())
    receipt = f"eh_{order_id[:8]}"
    try:
        rzp_order = _rzp.order.create({
            "amount": int(round(totals["total"] * 100)),  # in paise
            "currency": "INR",
            "receipt": receipt,
            "notes": {"internal_order_id": order_id, "user_id": user["id"] if user else "guest"},
        })
    except Exception as e:
        logging.error(f"Razorpay order create failed: {e}")
        raise HTTPException(502, f"Razorpay order failed: {e}")

    order_doc = {
        "id": order_id, "user_id": user["id"] if user else None,
        "guest_email": None,
        "status": "pending_payment", "payment_status": "pending",
        "items": totals["line_items"],
        "subtotal": totals["subtotal"], "discount": totals["discount"],
        "shipping": totals["shipping"], "tax": totals["tax"],
        "total": totals["total"], "currency": "INR",
        "coupon": totals["coupon"]["code"] if totals["coupon"] else None,
        "address": data.address.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tracking_number": None,
        "gateway": "razorpay",
        "razorpay_order_id": rzp_order["id"],
    }
    await db.orders.insert_one(order_doc)
    await db.payment_transactions.insert_one({
        "gateway": "razorpay",
        "razorpay_order_id": rzp_order["id"],
        "order_id": order_id,
        "amount": totals["total"], "currency": "INR",
        "status": "created", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "razorpay_order_id": rzp_order["id"],
        "amount": rzp_order["amount"],
        "currency": rzp_order["currency"],
        "key_id": RAZORPAY_KEY_ID,
        "order_id": order_id,
        "prefill": {
            "name": data.address.full_name,
            "email": (user or {}).get("email", ""),
            "contact": data.address.phone,
        },
    }


class RazorpayVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


async def _finalize_razorpay_order(rzp_order_id: str, rzp_payment_id: str):
    """Mark order as paid, decrement stock, clear cart, send email. Idempotent."""
    order = await db.orders.find_one({"razorpay_order_id": rzp_order_id})
    if not order:
        return None
    if order.get("payment_status") == "paid":
        return order
    await db.payment_transactions.update_one(
        {"razorpay_order_id": rzp_order_id},
        {"$set": {"status": "completed", "payment_status": "paid",
                  "razorpay_payment_id": rzp_payment_id,
                  "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.orders.update_one(
        {"razorpay_order_id": rzp_order_id, "payment_status": {"$ne": "paid"}},
        {"$set": {"payment_status": "paid", "status": "confirmed",
                  "razorpay_payment_id": rzp_payment_id,
                  "confirmed_at": datetime.now(timezone.utc).isoformat()}}
    )
    # Decrement stock, clear cart, send email
    for it in order["items"]:
        await db.products.update_one({"id": it["product_id"]},
            {"$inc": {"stock_qty": -it["quantity"]}})
    if order.get("user_id"):
        await db.cart_items.delete_many({"user_id": order["user_id"]})
    if not order.get("email_sent"):
        recipient = None
        if order.get("user_id"):
            u = await db.users.find_one({"id": order["user_id"]}, {"_id": 0, "email": 1})
            if u: recipient = u.get("email")
        recipient = recipient or order.get("guest_email")
        if recipient:
            try:
                await send_order_confirmation(order, recipient)
                await db.orders.update_one({"id": order["id"]},
                    {"$set": {"email_sent": True}})
            except Exception as e:
                logging.error(f"Order confirmation email failed: {e}")
    return await db.orders.find_one({"id": order["id"]}, {"_id": 0})


@api_router.post("/razorpay/verify")
async def razorpay_verify(data: RazorpayVerifyIn):
    """Verify Razorpay payment signature and finalize the order."""
    if not _rzp:
        raise HTTPException(503, "Razorpay is not configured")
    try:
        _rzp.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature,
        })
    except Exception as e:
        logging.warning(f"Razorpay signature verification failed: {e}")
        raise HTTPException(400, "Invalid payment signature")
    order = await _finalize_razorpay_order(data.razorpay_order_id, data.razorpay_payment_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": "success", "order_id": order["id"], "payment_status": order["payment_status"]}


@app.post("/api/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay server-to-server webhook events (payment.captured etc)."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logging.warning("Razorpay webhook signature mismatch")
            raise HTTPException(400, "Invalid webhook signature")
    try:
        payload = json.loads(body.decode())
        event = payload.get("event", "")
        payment_entity = (payload.get("payload", {}).get("payment", {}) or {}).get("entity", {})
        rzp_order_id = payment_entity.get("order_id")
        rzp_payment_id = payment_entity.get("id")
        if event == "payment.captured" and rzp_order_id and rzp_payment_id:
            await _finalize_razorpay_order(rzp_order_id, rzp_payment_id)
    except Exception as e:
        logging.error(f"Razorpay webhook processing error: {e}")
    return {"status": "ok"}

# --- Orders
@api_router.get("/orders")
async def list_orders(user=Depends(get_current_user)):
    orders = await db.orders.find({"user_id": user["id"]}, {"_id": 0}).sort([("created_at", -1)]).to_list(100)
    return orders

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Not found")
    if user["role"] != "admin" and order.get("user_id") != user["id"]:
        raise HTTPException(403, "Forbidden")
    return order

# --- Wishlist
@api_router.get("/wishlist")
async def get_wishlist(user=Depends(get_current_user)):
    items = await db.wishlist.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    enriched = []
    for it in items:
        p = await db.products.find_one({"id": it["product_id"]}, {"_id": 0})
        if p: enriched.append(p)
    return enriched

@api_router.post("/wishlist/toggle/{product_id}")
async def toggle_wishlist(product_id: str, user=Depends(get_current_user)):
    existing = await db.wishlist.find_one({"user_id": user["id"], "product_id": product_id})
    if existing:
        await db.wishlist.delete_one({"user_id": user["id"], "product_id": product_id})
        return {"in_wishlist": False}
    await db.wishlist.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"],
        "product_id": product_id, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"in_wishlist": True}

# --- Uploads
@api_router.post("/uploads/image")
async def upload_image(file: UploadFile = File(...), user=Depends(require_admin)):
    ext = (file.filename or "file").split(".")[-1].lower()
    path = f"{APP_NAME}/products/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    await db.files.insert_one({
        "id": str(uuid.uuid4()), "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type,
        "size": result.get("size", len(data)), "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"path": result["path"], "url": f"/api/files/{result['path']}"}

@api_router.post("/uploads/datasheet")
async def upload_datasheet(file: UploadFile = File(...), user=Depends(require_admin)):
    ext = (file.filename or "file").split(".")[-1].lower()
    path = f"{APP_NAME}/datasheets/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/pdf")
    await db.files.insert_one({
        "id": str(uuid.uuid4()), "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type or "application/pdf",
        "size": result.get("size", len(data)), "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"path": result["path"], "url": f"/api/files/{result['path']}"}

@api_router.get("/files/{path:path}")
async def download_file(path: str):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not rec:
        raise HTTPException(404, "File not found")
    data, ct = get_object(path)
    return Response(content=data, media_type=rec.get("content_type") or ct)

# --- Admin: Products
@api_router.get("/admin/dashboard")
async def admin_dashboard(user=Depends(require_admin)):
    total_products = await db.products.count_documents({})
    total_orders = await db.orders.count_documents({})
    total_users = await db.users.count_documents({"role": "customer"})
    paid_orders = await db.orders.find({"payment_status": "paid"}, {"_id": 0}).to_list(1000)
    revenue = sum(o.get("total", 0) for o in paid_orders)
    low_stock = await db.products.find(
        {"$expr": {"$lte": ["$stock_qty", "$low_stock_threshold"]}},
        {"_id": 0, "id": 1, "name": 1, "stock_qty": 1, "sku": 1}
    ).limit(20).to_list(20)
    recent_orders = await db.orders.find({}, {"_id": 0}).sort([("created_at", -1)]).limit(10).to_list(10)
    return {"total_products": total_products, "total_orders": total_orders,
            "total_users": total_users, "revenue": round(revenue, 2),
            "low_stock": low_stock, "recent_orders": recent_orders}

@api_router.post("/admin/products")
async def admin_create_product(data: ProductIn, user=Depends(require_admin)):
    doc = data.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["rating_avg"] = 0
    doc["rating_count"] = 0
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/admin/products/{product_id}")
async def admin_update_product(product_id: str, data: ProductIn, user=Depends(require_admin)):
    await db.products.update_one({"id": product_id}, {"$set": data.model_dump()})
    prod = await db.products.find_one({"id": product_id}, {"_id": 0})
    return prod

@api_router.delete("/admin/products/{product_id}")
async def admin_delete_product(product_id: str, user=Depends(require_admin)):
    await db.products.delete_one({"id": product_id})
    return {"ok": True}

@api_router.get("/admin/orders")
async def admin_orders(user=Depends(require_admin)):
    orders = await db.orders.find({}, {"_id": 0}).sort([("created_at", -1)]).to_list(500)
    return orders

@api_router.post("/admin/orders/{order_id}/status")
async def admin_update_order(order_id: str, payload: dict, user=Depends(require_admin)):
    status = payload.get("status")
    tracking = payload.get("tracking_number")
    upd = {"status": status}
    if tracking: upd["tracking_number"] = tracking
    await db.orders.update_one({"id": order_id}, {"$set": upd})
    # Send shipping/delivery notification email on status transition
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if order and order.get("user_id"):
        u = await db.users.find_one({"id": order["user_id"]}, {"_id": 0, "email": 1})
        recipient = u.get("email") if u else None
        if recipient:
            try:
                if status == "shipped" and not order.get("shipped_email_sent"):
                    await send_shipping_notification(order, recipient)
                    await db.orders.update_one({"id": order_id}, {"$set": {"shipped_email_sent": True}})
                elif status == "delivered" and not order.get("delivered_email_sent"):
                    await send_delivered_notification(order, recipient)
                    await db.orders.update_one({"id": order_id}, {"$set": {"delivered_email_sent": True}})
            except Exception as e:
                logging.error(f"Order status email failed: {e}")
    return {"ok": True}

@api_router.post("/admin/coupons")
async def admin_create_coupon(data: CouponIn, user=Depends(require_admin)):
    doc = data.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["code"] = doc["code"].upper()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["uses"] = 0
    await db.coupons.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/admin/coupons")
async def admin_list_coupons(user=Depends(require_admin)):
    return await db.coupons.find({}, {"_id": 0}).to_list(200)

# --- Project Kits (curated maker projects that add all required parts to cart)
async def _resolve_project(proj: dict):
    """Enrich a project with full product data + calculated total price."""
    items = []
    total = 0
    missing = []
    for entry in proj.get("parts", []):
        sku = entry["sku"]
        qty = entry.get("quantity", 1)
        p = await db.products.find_one({"sku": sku, "is_active": True}, {"_id": 0})
        if not p:
            missing.append(sku)
            continue
        price = p.get("discount_price") or p["price"]
        line_total = price * qty
        total += line_total
        items.append({"product": p, "quantity": qty, "unit_price": price, "line_total": line_total})
    proj_copy = {k: v for k, v in proj.items() if k != "_id"}
    proj_copy["items"] = items
    proj_copy["total_price"] = round(total, 2)
    proj_copy["parts_missing"] = missing
    return proj_copy


@api_router.get("/projects")
async def list_projects():
    projs = await db.projects.find({"is_active": True}, {"_id": 0}).sort([("sort_order", 1)]).to_list(100)
    result = []
    for p in projs:
        enriched = await _resolve_project(p)
        # only send summary in the list view
        result.append({
            "id": enriched["id"], "slug": enriched["slug"], "name": enriched["name"],
            "tagline": enriched["tagline"], "difficulty": enriched["difficulty"],
            "duration": enriched["duration"], "image": enriched.get("image"),
            "total_price": enriched["total_price"],
            "parts_count": sum(it["quantity"] for it in enriched["items"]),
        })
    return result


@api_router.get("/projects/{slug}")
async def get_project(slug: str):
    proj = await db.projects.find_one({"slug": slug, "is_active": True}, {"_id": 0})
    if not proj:
        raise HTTPException(404, "Project not found")
    return await _resolve_project(proj)


@api_router.post("/projects/{slug}/add-to-cart")
async def add_project_to_cart(slug: str, user=Depends(get_optional_user), cart_id: Optional[str] = None):
    proj = await db.projects.find_one({"slug": slug, "is_active": True}, {"_id": 0})
    if not proj:
        raise HTTPException(404, "Project not found")
    if not user and not cart_id:
        cart_id = str(uuid.uuid4())
    added = []
    unavailable = []
    for entry in proj.get("parts", []):
        p = await db.products.find_one({"sku": entry["sku"], "is_active": True}, {"_id": 0})
        if not p:
            unavailable.append(entry["sku"]); continue
        if p.get("stock_qty", 0) < entry["quantity"]:
            unavailable.append(entry["sku"]); continue
        key = {"user_id": user["id"], "product_id": p["id"]} if user else {"cart_id": cart_id, "product_id": p["id"]}
        existing = await db.cart_items.find_one(key)
        if existing:
            await db.cart_items.update_one(key, {"$inc": {"quantity": entry["quantity"]}})
        else:
            await db.cart_items.insert_one({**key, "id": str(uuid.uuid4()),
                "quantity": entry["quantity"],
                "created_at": datetime.now(timezone.utc).isoformat()})
        added.append({"sku": p["sku"], "name": p["name"], "quantity": entry["quantity"]})
    return {"added": added, "unavailable": unavailable, "cart_id": cart_id if not user else None}


async def seed_projects():
    if await db.projects.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    projects = [
        {
            "slug": "line-follower-robot",
            "name": "Line Follower Robot",
            "tagline": "Your first autonomous bot — follows a black line on white surface using IR sensors.",
            "difficulty": "Beginner",
            "duration": "3–4 hours",
            "image": "https://images.pexels.com/photos/3913012/pexels-photo-3913012.jpeg?w=1200",
            "description": "Build a classic line-following robot using an Arduino, two motors, IR sensors and an L298N motor driver. Great intro to closed-loop control, PWM, and digital sensor reading.",
            "learn": ["Digital I/O and interrupts", "PWM motor control", "Simple closed-loop control"],
            "parts": [
                {"sku": "MCU-UNO-R3", "quantity": 1},
                {"sku": "ROB-L298N", "quantity": 1},
                {"sku": "ROB-SG90", "quantity": 0},  # not needed but shows compatibility
                {"sku": "PWR-18650", "quantity": 2},
                {"sku": "TOO-BB830", "quantity": 1},
                {"sku": "TOO-JW40", "quantity": 1},
            ],
            "is_active": True, "sort_order": 1, "created_at": now,
        },
        {
            "slug": "weather-station",
            "name": "IoT Weather Station",
            "tagline": "WiFi-connected temperature, humidity and motion logger that pushes data to your phone.",
            "difficulty": "Intermediate",
            "duration": "5–6 hours",
            "image": "https://images.unsplash.com/photo-1580983230712-71cf10154a68?w=1200",
            "description": "Combine an ESP32 with DHT22 and PIR sensors to build a full-fledged environmental logger. Data can be sent to a dashboard via MQTT or REST.",
            "learn": ["ESP32 WiFi & HTTP client", "I²C / 1-Wire sensor protocols", "Deep sleep power management"],
            "parts": [
                {"sku": "MCU-ESP32", "quantity": 1},
                {"sku": "SEN-DHT22", "quantity": 1},
                {"sku": "SEN-PIR", "quantity": 1},
                {"sku": "PWR-LM2596", "quantity": 1},
                {"sku": "TOO-BB830", "quantity": 1},
                {"sku": "TOO-JW40", "quantity": 1},
            ],
            "is_active": True, "sort_order": 2, "created_at": now,
        },
        {
            "slug": "obstacle-avoider",
            "name": "Obstacle-Avoiding Robot",
            "tagline": "A rover that senses walls with ultrasonic and steers around them autonomously.",
            "difficulty": "Beginner",
            "duration": "4–5 hours",
            "image": "https://images.unsplash.com/photo-1517420704952-d9f39e95b43e?w=1200",
            "description": "Mount an HC-SR04 on a servo to sweep for obstacles, then use an L298N to control drive motors. A perfect follow-up after the Line Follower.",
            "learn": ["Servo sweep + ultrasonic sensing", "State-machine logic", "Motor kinematics"],
            "parts": [
                {"sku": "MCU-UNO-R3", "quantity": 1},
                {"sku": "SEN-HCSR04", "quantity": 1},
                {"sku": "ROB-SG90", "quantity": 1},
                {"sku": "ROB-L298N", "quantity": 1},
                {"sku": "PWR-18650", "quantity": 2},
                {"sku": "TOO-JW40", "quantity": 1},
            ],
            "is_active": True, "sort_order": 3, "created_at": now,
        },
        {
            "slug": "motion-alert-cam",
            "name": "Motion-Alert Doorbell",
            "tagline": "PIR-triggered alert that fires a wireless signal when someone approaches your door.",
            "difficulty": "Intermediate",
            "duration": "3–4 hours",
            "image": "https://images.unsplash.com/photo-1592659762303-90081d34b277?w=1200",
            "description": "Combine a PIR motion sensor with an ESP32 and an nRF24 module to build a battery-powered wireless doorbell / motion notifier.",
            "learn": ["Interrupt-driven sleep + wake", "SPI communication", "Wireless protocols"],
            "parts": [
                {"sku": "MCU-ESP32", "quantity": 1},
                {"sku": "SEN-PIR", "quantity": 1},
                {"sku": "CON-NRF24", "quantity": 2},
                {"sku": "PWR-18650", "quantity": 1},
                {"sku": "TOO-BB830", "quantity": 1},
                {"sku": "TOO-JW40", "quantity": 1},
            ],
            "is_active": True, "sort_order": 4, "created_at": now,
        },
    ]
    for p in projects:
        p["id"] = str(uuid.uuid4())
        # Remove zero-quantity parts (they're informational, not required)
        p["parts"] = [x for x in p["parts"] if x.get("quantity", 0) > 0]
    await db.projects.insert_many(projects)


# --- Seed
async def seed_data():
    # Admin user
    if not await db.users.find_one({"email": "admin@electronichub.io"}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "name": "Admin",
            "email": "admin@electronichub.io",
            "password_hash": hash_pw("Admin@12345"),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    if not await db.users.find_one({"email": "customer@electronichub.io"}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "name": "Test Customer",
            "email": "customer@electronichub.io",
            "password_hash": hash_pw("Customer@12345"),
            "role": "customer",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    # Products
    if await db.products.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    products = [
        # Sensors
        {"sku": "SEN-DHT22", "name": "DHT22 Temperature & Humidity Sensor", "category": "sensors",
         "brand": "Generic", "price": 249, "discount_price": 199, "stock_qty": 120,
         "description": "Digital temperature and humidity sensor. Range: -40 to 80°C, 0-100% RH. Single-wire digital output.",
         "specs": {"Voltage": "3.3-5V", "Interface": "1-Wire Digital", "Accuracy": "±0.5°C, ±2% RH", "Sampling Rate": "0.5Hz"},
         "voltage": "5V", "interface": "1-Wire", "compatible_with": ["Arduino Uno", "ESP32", "Raspberry Pi"],
         "images": ["https://images.unsplash.com/photo-1580983230712-71cf10154a68?w=800"],
         "is_featured": True, "tags": ["temperature", "humidity", "iot"]},
        {"sku": "SEN-HCSR04", "name": "HC-SR04 Ultrasonic Distance Sensor", "category": "sensors",
         "brand": "Generic", "price": 129, "stock_qty": 250,
         "description": "Non-contact ultrasonic ranging module. Range 2cm to 400cm with 3mm accuracy.",
         "specs": {"Voltage": "5V", "Range": "2-400cm", "Interface": "Digital I/O", "Frequency": "40kHz"},
         "voltage": "5V", "interface": "Digital", "compatible_with": ["Arduino Uno", "Arduino Mega"],
         "images": ["https://images.unsplash.com/photo-1517420704952-d9f39e95b43e?w=800"],
         "is_featured": True, "tags": ["ultrasonic", "distance"]},
        {"sku": "SEN-MPU6050", "name": "MPU-6050 6-Axis Gyro & Accelerometer", "category": "sensors",
         "brand": "InvenSense", "price": 179, "stock_qty": 80,
         "description": "3-axis gyroscope + 3-axis accelerometer with digital motion processor.",
         "specs": {"Voltage": "3.3-5V", "Interface": "I2C", "Gyro Range": "±250-2000°/s", "Accel Range": "±2-16g"},
         "voltage": "3.3V", "interface": "I2C", "compatible_with": ["Arduino", "ESP32", "STM32"],
         "images": ["https://images.unsplash.com/photo-1592659762303-90081d34b277?w=800"],
         "tags": ["gyro", "imu"]},
        {"sku": "SEN-PIR", "name": "HC-SR501 PIR Motion Sensor", "category": "sensors",
         "brand": "Generic", "price": 89, "stock_qty": 300,
         "description": "Passive infrared motion detector with adjustable delay and sensitivity.",
         "specs": {"Voltage": "5-20V", "Detection Range": "7m", "Interface": "Digital Out"},
         "voltage": "5V", "interface": "Digital", "compatible_with": ["Arduino", "ESP32"],
         "images": ["https://images.pexels.com/photos/39290/mother-board-electronics-computer-board-39290.jpeg?w=800"],
         "tags": ["motion", "pir"]},
        # Microcontrollers
        {"sku": "MCU-UNO-R3", "name": "Arduino Uno R3 Compatible Board", "category": "microcontrollers",
         "brand": "Arduino", "price": 599, "discount_price": 499, "stock_qty": 60,
         "description": "ATmega328P microcontroller board with 14 digital pins, 6 analog inputs, USB connection.",
         "specs": {"MCU": "ATmega328P", "Voltage": "5V", "Flash": "32KB", "SRAM": "2KB", "Clock": "16MHz"},
         "voltage": "5V", "interface": "USB/UART",
         "images": ["https://images.unsplash.com/photo-1553406830-ef2513450d76?w=800"],
         "is_featured": True, "tags": ["arduino", "atmega"]},
        {"sku": "MCU-ESP32", "name": "ESP32 DevKit V1 (WiFi + Bluetooth)", "category": "microcontrollers",
         "brand": "Espressif", "price": 449, "stock_qty": 90,
         "description": "Dual-core WiFi + BLE microcontroller. 30 GPIO pins, ideal for IoT projects.",
         "specs": {"MCU": "Xtensa LX6 Dual-Core", "Voltage": "3.3V", "Flash": "4MB", "WiFi": "802.11 b/g/n", "Bluetooth": "4.2 BLE"},
         "voltage": "3.3V", "interface": "USB", "compatible_with": ["Arduino IDE", "PlatformIO"],
         "images": ["https://images.unsplash.com/photo-1518770660439-4636190af475?w=800"],
         "is_featured": True, "tags": ["esp32", "wifi", "iot"]},
        {"sku": "MCU-PICO", "name": "Raspberry Pi Pico W", "category": "microcontrollers",
         "brand": "Raspberry Pi", "price": 549, "stock_qty": 45,
         "description": "RP2040-based board with onboard WiFi. Dual-core Arm Cortex-M0+ at 133MHz.",
         "specs": {"MCU": "RP2040", "Voltage": "3.3V", "Flash": "2MB", "WiFi": "802.11n", "GPIO": "26"},
         "voltage": "3.3V", "interface": "USB", "compatible_with": ["MicroPython", "C/C++ SDK"],
         "images": ["https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=800"],
         "tags": ["pico", "rp2040"]},
        # Processors/SBCs
        {"sku": "SBC-RPI4-4GB", "name": "Raspberry Pi 4 Model B - 4GB RAM", "category": "processors",
         "brand": "Raspberry Pi", "price": 5999, "stock_qty": 25,
         "description": "Quad-core Cortex-A72 @ 1.5GHz. Dual 4K HDMI, USB 3.0, Gigabit Ethernet.",
         "specs": {"SoC": "BCM2711", "RAM": "4GB LPDDR4", "Voltage": "5V/3A", "USB": "2×3.0, 2×2.0"},
         "voltage": "5V", "interface": "USB/HDMI/Ethernet",
         "images": ["https://images.pexels.com/photos/3913012/pexels-photo-3913012.jpeg?w=800"],
         "is_featured": True, "tags": ["raspberry-pi", "sbc"]},
        # Robotics
        {"sku": "ROB-SG90", "name": "SG90 Micro Servo Motor 9g", "category": "robotics",
         "brand": "TowerPro", "price": 149, "stock_qty": 400,
         "description": "Small servo for robotics, RC vehicles, and hobby projects. 180° rotation.",
         "specs": {"Voltage": "4.8-6V", "Torque": "1.8 kg-cm", "Speed": "0.1s/60°", "Weight": "9g"},
         "voltage": "5V", "interface": "PWM",
         "images": ["https://images.unsplash.com/photo-1518770660439-4636190af475?w=800"],
         "tags": ["servo", "motor"]},
        {"sku": "ROB-L298N", "name": "L298N Dual H-Bridge Motor Driver", "category": "robotics",
         "brand": "STMicro", "price": 199, "stock_qty": 150,
         "description": "Dual full-bridge motor driver. Controls 2 DC motors or 1 stepper motor.",
         "specs": {"Voltage": "5-35V", "Current": "2A/channel", "Interface": "Digital I/O"},
         "voltage": "12V", "interface": "PWM/Digital",
         "images": ["https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=800"],
         "tags": ["motor-driver", "h-bridge"]},
        # Power
        {"sku": "PWR-LM2596", "name": "LM2596 DC-DC Buck Converter Module", "category": "power",
         "brand": "TI", "price": 79, "stock_qty": 500,
         "description": "Step-down converter, adjustable 1.25-35V output, up to 3A.",
         "specs": {"Input": "4-40V", "Output": "1.25-37V", "Current": "3A max"},
         "voltage": "12V", "interface": "Screw Terminals",
         "images": ["https://images.pexels.com/photos/39290/mother-board-electronics-computer-board-39290.jpeg?w=800"],
         "tags": ["buck", "regulator"]},
        {"sku": "PWR-18650", "name": "Samsung 18650 Li-Ion Battery 3400mAh", "category": "power",
         "brand": "Samsung", "price": 349, "stock_qty": 200,
         "description": "Rechargeable Li-Ion cell with protection circuit.",
         "specs": {"Voltage": "3.7V", "Capacity": "3400mAh", "Chemistry": "Li-Ion", "Cycles": "500+"},
         "voltage": "3.7V", "interface": "Terminals",
         "images": ["https://images.unsplash.com/photo-1620714223084-8fcacc6dfd8d?w=800"],
         "tags": ["battery", "lithium"]},
        # Connectivity
        {"sku": "CON-NRF24", "name": "nRF24L01+ Wireless RF Module", "category": "connectivity",
         "brand": "Nordic", "price": 99, "stock_qty": 220,
         "description": "2.4GHz wireless transceiver module. Up to 100m range in open field.",
         "specs": {"Voltage": "3.3V", "Frequency": "2.4GHz", "Interface": "SPI", "Range": "100m"},
         "voltage": "3.3V", "interface": "SPI", "compatible_with": ["Arduino", "ESP32"],
         "images": ["https://images.unsplash.com/photo-1518770660439-4636190af475?w=800"],
         "tags": ["wireless", "rf"]},
        # Tools
        {"sku": "TOO-BB830", "name": "830-Point Solderless Breadboard", "category": "tools",
         "brand": "Generic", "price": 149, "stock_qty": 300,
         "description": "Standard full-size breadboard with 830 tie-points. Ideal for prototyping.",
         "specs": {"Points": "830", "Size": "165×55mm", "Rows": "63"},
         "images": ["https://images.pexels.com/photos/3913012/pexels-photo-3913012.jpeg?w=800"],
         "tags": ["breadboard", "prototyping"]},
        {"sku": "TOO-JW40", "name": "Jumper Wires - 40pcs Male-to-Male", "category": "tools",
         "brand": "Generic", "price": 69, "stock_qty": 800,
         "description": "20cm flexible jumper wires. 40 pieces, multicolor.",
         "specs": {"Length": "20cm", "Count": "40", "Type": "M-M"},
         "images": ["https://images.unsplash.com/photo-1517420704952-d9f39e95b43e?w=800"],
         "tags": ["wires", "jumper"]},
        # Kits
        {"sku": "KIT-LFR", "name": "Line Follower Robot Kit", "category": "kits",
         "brand": "ElectronicHub", "price": 1999, "discount_price": 1699, "stock_qty": 30,
         "description": "Complete kit to build a line-following robot. Includes chassis, motors, sensors, driver, and battery.",
         "specs": {"Includes": "Chassis, 2× Motors, IR Sensors, L298N, Battery Holder, Wheels"},
         "voltage": "9V", "compatible_with": ["Arduino Uno"],
         "images": ["https://images.pexels.com/photos/3913012/pexels-photo-3913012.jpeg?w=800"],
         "is_featured": True, "tags": ["robot", "kit", "beginner"]},
        {"sku": "KIT-STARTER", "name": "Arduino Uno Starter Kit (50+ components)", "category": "kits",
         "brand": "ElectronicHub", "price": 2499, "stock_qty": 40,
         "description": "Everything needed to start with Arduino. Includes Uno, breadboard, sensors, LEDs, resistors, and project book.",
         "specs": {"Board": "Arduino Uno", "Components": "50+", "Projects": "15 guided"},
         "voltage": "5V",
         "images": ["https://images.unsplash.com/photo-1553406830-ef2513450d76?w=800"],
         "is_featured": True, "tags": ["starter", "kit"]},
    ]
    for p in products:
        p["id"] = str(uuid.uuid4())
        p["is_active"] = True
        p["is_featured"] = p.get("is_featured", False)
        p["low_stock_threshold"] = 10
        p["rating_avg"] = 4.5
        p["rating_count"] = 12
        p["created_at"] = now
        p.setdefault("compatible_with", [])
        p.setdefault("tags", [])
    await db.products.insert_many(products)
    # Coupons
    await db.coupons.insert_many([
        {"id": str(uuid.uuid4()), "code": "WELCOME10", "discount_type": "percent",
         "discount_value": 10, "min_order": 500, "max_uses": 1000, "active": True,
         "uses": 0, "created_at": now},
        {"id": str(uuid.uuid4()), "code": "MAKER100", "discount_type": "flat",
         "discount_value": 100, "min_order": 999, "max_uses": 500, "active": True,
         "uses": 0, "created_at": now},
    ])

@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logging.info("Storage initialized")
    except Exception as e:
        logging.warning(f"Storage init failed (uploads disabled): {e}")
    await seed_data()
    await seed_projects()

@api_router.get("/")
async def root():
    return {"message": "ElectronicHub API", "status": "ok"}

app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"], allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.on_event("shutdown")
async def shutdown():
    async_client.close()
