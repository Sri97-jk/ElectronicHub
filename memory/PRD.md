# ElectronicHub — Product Requirements Document

## Original Problem Statement
Build ElectronicHub, a public e-commerce platform for electronic & robotics components (sensors, microcontrollers, processors, robotic parts, actuators, cables, accessories). Targets students, hobbyists, makers, and small robotics teams. Full transactional store with live payments, inventory, and order fulfillment.

## User Choices (2026-07-26)
- Stack: FastAPI (Python) + MongoDB + React
- Payments: Stripe (Flow B / BYOK using `sk_test_emergent`)
- Auth: JWT email/password with bcrypt
- Storage: Emergent Object Storage (for admin product uploads)
- Scope: Full MVP (catalog + cart + checkout + payments + admin panel + orders)

## Architecture
- Backend: FastAPI at `:8001`, all routes prefixed `/api`
- Database: MongoDB (`test_database`), collections: users, products, cart_items, orders, reviews, coupons, wishlist, payment_transactions, files
- Frontend: React + React Router v7 + Tailwind + Phosphor Icons + Framer Motion + Sonner (toasts)
- Design: Dark theme (#050A0F) with #00FF66 primary accent, Cabinet Grotesk headings, JetBrains Mono for technical labels, blueprint-style grid borders

## Personas
- **Student Maker** — small quantities, correct-spec parts
- **Hobbyist** — wide catalog, technical detail
- **Robotics Team Lead** — small batches, saved lists, tracking
- **Educator** — bundles, kits

## Implemented (Phase 3 — 2026-07-26)
- **Project Kit Builder**: 4 seeded curated builds (Line Follower Robot, IoT Weather Station, Obstacle-Avoiding Robot, Motion-Alert Doorbell) each with parts list, difficulty tag, duration, and one-click "Add All To Cart". Endpoints: `GET /api/projects`, `GET /api/projects/{slug}`, `POST /api/projects/{slug}/add-to-cart`. Front-end pages `/projects` and `/projects/{slug}` + Home "Ready-to-build" section + header nav.
- **Datasheet & Image Uploads**: admin product form now has real file inputs. `POST /api/uploads/image` (image/*) and `POST /api/uploads/datasheet` (application/pdf) both push into Emergent Object Storage and return `/api/files/{path}` URLs.
- **Real Emails ON**: Resend live with `sk-emergent...` key; verified via server-side shipping status update → real inbox delivery (ID `98de374e-bb8b-45ae-85f5-929c6fb5e273`). `emails.py` now loads its own `.env` to avoid init-order bugs.
- **Product imagery refresh**: all 17 seeded products swapped to component-appropriate photos.

## Implemented (Phase 2 — 2026-07-26)
- **Transactional emails** (order confirmed, shipped, delivered) via Resend. Console-only mode active (RESEND_API_KEY empty in .env). Idempotent per-order flags: `email_sent`, `shipped_email_sent`, `delivered_email_sent`.
- **Compatibility Recommender** — new endpoint `GET /api/cart/recommendations` that scores candidates using `compatible_with` tag matches, shared tags, and shared category. Cart page shows "Works with your cart / Complete your build" when items are present, falls back to "Popular this week" for empty carts.

## Implemented (Phase 1 MVP — 2026-07-26)
### Backend endpoints
- Auth: `POST /api/auth/signup`, `POST /api/auth/login`, `GET /api/auth/me`
- Catalog: `GET /api/products` (filters: category, brand, voltage, interface, search, sort, featured, in_stock, min/max_price), `GET /api/products/{id}`, `GET /api/products/filters`, `GET /api/categories`
- Cart: `GET/POST /api/cart`, `/api/cart/add`, `/api/cart/update`, `DELETE /api/cart/item/{id}` (both auth & guest modes)
- Coupons: `POST /api/coupons/validate`
- Wishlist: `GET /api/wishlist`, `POST /api/wishlist/toggle/{id}`
- Reviews: `POST /api/reviews`
- Checkout: `POST /api/checkout/session` → Stripe checkout URL
- Payments: `GET /api/payments/status/{session_id}` (polling + Stripe fallback), `POST /api/webhook/stripe`
- Orders: `GET /api/orders`, `GET /api/orders/{id}`
- Admin: `/api/admin/dashboard`, product CRUD, order status update, coupon CRUD
- Uploads: `POST /api/uploads/image` (admin), `GET /api/files/{path}`

### Frontend pages
- Home (hero + categories grid + featured + CTA)
- Catalog (filters sidebar, sort, search)
- Product Detail (specs table, reviews, related, wishlist toggle)
- Cart, Checkout (address + coupon), Payment Success/Cancel
- Login, Signup, Orders, Wishlist
- Admin panel with Dashboard, Products (CRUD), Orders (status), Coupons (CRUD)

### Integrations
- Stripe via `emergentintegrations.payments.stripe.checkout` (Flow B, BYOK)
- Emergent Object Storage (initialized on backend startup)
- JWT (PyJWT) + bcrypt for auth

### Seed data
- Admin: `admin@electronichub.io` / `Admin@12345`
- Customer: `customer@electronichub.io` / `Customer@12345`
- 17 products across 8 categories, 2 coupons (WELCOME10 = 10% off ₹500+, MAKER100 = ₹100 off ₹999+)

## Testing (2026-07-26)
- Backend: 32 pytest cases — 100% pass
- Frontend: smoke tests through login, catalog, cart, admin — 100% pass
- No critical or high-priority bugs

## Backlog (P1/P2 — deferred)
- P1: Order status email notifications (SendGrid/SES)
- P1: Full-text search / Meilisearch integration
- P1: Guest checkout without user creation
- P1: Return/replacement request flow
- P2: Bulk CSV product import
- P2: Bundle/kit builder UI
- P2: Loyalty/rewards program
- P2: Multi-vendor support
- P2: Advanced analytics (top-selling, revenue by category)
