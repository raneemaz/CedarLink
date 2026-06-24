# CedarLink — Coding Plan (A to Z)
### Full Implementation Roadmap, including Complete API Specification

This plan turns the established CedarLink documentation (Functional/Non-Functional Requirements, User Stories, System Actors, Three-Tier Architecture, and the 11-entity ERD) into an executable build order. It covers environment setup, database implementation, the full REST API, core business logic, frontend integration, testing, and deployment — then maps every piece back to the original requirements.

**Stack (per established architecture):** HTML/CSS/JS (frontend) → Python Flask (backend) → MySQL (data layer).

---

## 0. Build Philosophy

Build in dependency order, not feature-popularity order. Nothing above a table can be built before the tables below it exist; nothing in the API can be tested before auth exists. The order below respects the ERD's foreign-key chain:

```
User → Store → Category → Product → ProductImage
            → Cart → CartItem
            → Order → OrderItem → Payment
                    → DeliveryAssignment
```

Each phase below is a vertical slice (DB → service → API → minimal UI hook) rather than building all models, then all routes, then all UI — this keeps every phase demoable and testable on its own.

---

## 1. Project Structure

```
cedarlink/
├── app/
│   ├── __init__.py              # app factory, blueprint registration
│   ├── config.py                # Dev/Test/Prod config classes
│   ├── extensions.py            # db, jwt, cors, migrate instances
│   ├── models/
│   │   ├── user.py
│   │   ├── store.py
│   │   ├── category.py
│   │   ├── product.py
│   │   ├── product_image.py
│   │   ├── cart.py
│   │   ├── cart_item.py
│   │   ├── order.py
│   │   ├── order_item.py
│   │   ├── payment.py
│   │   └── delivery_assignment.py
│   ├── routes/                  # one blueprint per resource
│   │   ├── auth_routes.py
│   │   ├── user_routes.py
│   │   ├── store_routes.py
│   │   ├── category_routes.py
│   │   ├── product_routes.py
│   │   ├── cart_routes.py
│   │   ├── order_routes.py
│   │   ├── payment_routes.py
│   │   ├── delivery_routes.py
│   │   └── admin_routes.py
│   ├── services/                # business logic, kept out of routes
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   ├── cart_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   └── delivery_service.py
│   ├── schemas/                 # marshmallow/pydantic request+response validation
│   └── utils/
│       ├── decorators.py        # @role_required, @login_required
│       └── helpers.py
├── migrations/                  # Flask-Migrate / Alembic
├── tests/
│   ├── unit/
│   └── integration/
├── static/  templates/          # or a separate /frontend if decoupled SPA
├── run.py
├── requirements.txt
└── .env
```

**Why a service layer:** routes stay thin (parse request → call service → return response), which directly satisfies the Maintainability NFR ("modular structure, separation of concerns") and makes the logic in Section 6 unit-testable without spinning up Flask.

**Core dependencies:** `Flask`, `Flask-SQLAlchemy`, `Flask-Migrate`, `Flask-JWT-Extended`, `Flask-CORS`, `marshmallow`, `bcrypt` (or `werkzeug.security`), `pytest`, `python-dotenv`.

---

## 2. Database Layer

Models are created in FK order so every migration applies cleanly:

| Order | Model | Depends on |
|---|---|---|
| 1 | User | — |
| 2 | Store | User (owner_id) |
| 3 | Category | — |
| 4 | Product | Store, Category |
| 5 | ProductImage | Product |
| 6 | Cart | User |
| 7 | CartItem | Cart, Product |
| 8 | Order | User |
| 9 | OrderItem | Order, Product |
| 10 | Payment | Order |
| 11 | DeliveryAssignment | Order |

Each model gets a matching Alembic migration (`flask db migrate -m "create_<table>"`) so the schema history is reviewable — this is what makes the ERD "real" instead of just a diagram.

**Indexing for the Performance NFR (2–3s page loads):**
- `products(store_id)`, `products(category_id)`, `products(name)` (for keyword search)
- `cart_items(cart_id)`, `order_items(order_id)`
- `orders(user_id, status)` — supports order-history and vendor-incoming-orders queries directly

---

## 3. Authentication & Role-Based Access

- **Token strategy:** JWT access token (Flask-JWT-Extended), `role` claim embedded (`customer` / `vendor` / `admin`) per the User Management functional requirement.
- **Password storage:** hashed with bcrypt — satisfies the Security NFR directly.
- **Decorators (`utils/decorators.py`):**
  ```python
  def role_required(*roles):
      def wrapper(fn):
          @wraps(fn)
          @jwt_required()
          def decorated(*args, **kwargs):
              claims = get_jwt()
              if claims.get("role") not in roles:
                  abort(403)
              return fn(*args, **kwargs)
          return decorated
      return wrapper
  ```
- **Ownership checks:** every mutating endpoint on Store/Product/Order additionally checks `resource.owner_id == current_user.id` unless the caller is `admin` — this is what enforces "Users can only access their own data."

---

## 4. Full REST API Specification

Base path: `/api`. Auth column: **Public**, **Auth** (any logged-in user), or a specific role. All bodies are JSON unless noted.

### 4.1 Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Create account as `customer` or `vendor` |
| POST | `/auth/login` | Public | Returns `{access_token, user}` |
| POST | `/auth/logout` | Auth | Revoke/blacklist token |
| GET | `/auth/me` | Auth | Current user's profile |

### 4.2 Users

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/users/{id}` | Owner / Admin | View profile |
| PUT | `/users/{id}` | Owner | Update profile info |
| GET | `/admin/users` | Admin | List/search all users |
| PATCH | `/admin/users/{id}/suspend` | Admin | Suspend or reactivate an account |

### 4.3 Stores

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/stores` | Vendor | Create store profile |
| GET | `/stores` | Public | Browse stores (filter by location) |
| GET | `/stores/{id}` | Public | Store detail |
| PUT | `/stores/{id}` | Owner | Update name/description/location/contact |
| PATCH | `/stores/{id}/status` | Owner | Activate / deactivate store |
| GET | `/stores/{id}/products` | Public | "View products by store" |
| DELETE | `/stores/{id}` | Admin | Remove store |

### 4.4 Categories

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/categories` | Public | List all categories |
| POST | `/categories` | Admin | Create category |
| PUT | `/categories/{id}` | Admin | Rename/update |
| DELETE | `/categories/{id}` | Admin | Remove |

### 4.5 Products

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/products` | Public | Search/filter: `?keyword=&category_id=&min_price=&max_price=&location=&store_id=&page=` |
| GET | `/products/{id}` | Public | Product detail incl. images |
| POST | `/products` | Vendor | Add product (name, description, price, category, stock) |
| PUT | `/products/{id}` | Owner | Edit product |
| DELETE | `/products/{id}` | Owner | Delete product |
| POST | `/products/{id}/images` | Owner | Upload image (multipart) |
| DELETE | `/products/{id}/images/{image_id}` | Owner | Remove image |

### 4.6 Cart

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/cart` | Customer | Current cart, items grouped by store |
| POST | `/cart/items` | Customer | Add `{product_id, quantity}` |
| PUT | `/cart/items/{id}` | Customer | Update quantity |
| DELETE | `/cart/items/{id}` | Customer | Remove item |
| DELETE | `/cart` | Customer | Clear cart |

### 4.7 Orders

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/orders` | Customer | Checkout: `{delivery_address, payment_method}` — see Section 5.1 |
| GET | `/orders` | Customer | Own order history |
| GET | `/orders/{id}` | Customer (owner) / Vendor (involved) / Admin | Order detail |
| GET | `/vendor/orders` | Vendor | Incoming orders for the vendor's store(s), `?status=` |
| PATCH | `/orders/{id}/status` | Vendor | Advance status (pending → processing → delivered) |
| PATCH | `/orders/{id}/cancel` | Customer | Cancel while still `pending` |

### 4.8 Payments

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/payments` | Customer | Initiate payment for an order (`order_id`, `method`) |
| GET | `/payments/{id}` | Customer / Vendor / Admin | Payment status |
| POST | `/payments/webhook/{provider}` | Public (gateway-signed) | Async confirmation from Wish Money / OMT Pay / card processor |

### 4.9 Delivery

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/delivery/assignments` | Vendor / Admin | Assign a delivery for an order |
| GET | `/delivery/assignments/{id}` | Driver / Customer / Vendor | View status |
| PATCH | `/delivery/assignments/{id}/status` | Driver | Update (picked up → delivered) |

### 4.10 Admin

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/admin/stores` | Admin | List/monitor all stores |
| PATCH | `/admin/stores/{id}/approve` | Admin | Approve a pending vendor store |
| DELETE | `/admin/stores/{id}` | Admin | Remove inappropriate store |
| GET | `/admin/reports` | Admin | Aggregate platform reports |

---

## 5. Business Logic Worth Designing Before Coding

### 5.1 Multi-Vendor Checkout (Cart → Order)

The Cart functional requirement explicitly allows products from multiple stores in one cart, but each `Order` is fulfilled by one vendor (vendors only see "their" incoming orders). So checkout must **split the cart by store**:

```python
def checkout(user, delivery_address, payment_method):
    cart_items = get_cart_items(user)
    items_by_store = group_by(cart_items, key=lambda i: i.product.store_id)

    created_orders = []
    with db.session.begin():               # one transaction: all-or-nothing
        for store_id, items in items_by_store.items():
            order = Order(user_id=user.id, status="pending",
                           delivery_address=delivery_address)
            db.session.add(order)
            for item in items:
                if item.product.stock < item.quantity:
                    raise InsufficientStockError(item.product)
                db.session.add(OrderItem(order=order, product_id=item.product_id,
                                          quantity=item.quantity, unit_price=item.product.price))
                item.product.stock -= item.quantity
            created_orders.append(order)
        clear_cart(user)
    return created_orders
```

This single DB transaction is what satisfies the Reliability NFR ("prevent data loss during order creation… transactions ensure order consistency") — either every order/item/stock-decrement commits, or none does.

### 5.2 Delivery Fee & Total Calculation

Each store sets its own delivery fee/availability (per Delivery Handling FR). Total price = `Σ(item price × qty)` per store + that store's delivery fee, computed server-side at checkout (never trust a client-submitted total).

### 5.3 Order Status State Machine

```
pending → processing → delivered
   └────────────────→ canceled
```
Enforced in `order_service.update_status()`: only vendors can move `pending → processing → delivered`; only customers can cancel, and only while still `pending`.

### 5.4 Payment Flow

1. `POST /payments` creates a `Payment` row in `pending` state and (for redirect-based gateways) returns a redirect URL.
2. The gateway calls `/payments/webhook/{provider}` asynchronously; the handler verifies the signature, updates `Payment.status`, and on success flips the related `Order` out of "awaiting payment."
3. Never trust a client-side "payment succeeded" call alone — webhook is the source of truth.

---

## 6. Frontend Build Plan

Three dashboards, matching the System Actors:

| Area | Key Screens | Primary API calls |
|---|---|---|
| **Customer** | Browse/Search, Product detail, Cart, Checkout, Order history | `/products`, `/cart/*`, `/orders` |
| **Vendor** | Store setup, Product CRUD, Incoming orders, Delivery config | `/stores/*`, `/products` (own), `/vendor/orders` |
| **Admin** | User list, Store moderation, Reports | `/admin/*` |

Responsive layout (Bootstrap or hand-rolled CSS grid) covers the Usability NFR's mobile-friendly requirement. Keep API calls in a single `api.js` client module so auth-token handling and error formatting live in one place.

---

## 7. Testing Strategy

- **Unit tests** (`tests/unit`): service-layer functions in isolation — checkout splitting, stock-decrement, status transitions, fee math — no Flask app needed.
- **Integration tests** (`tests/integration`): `pytest` + Flask test client hitting real endpoints against a throwaway test DB; one test per user story acceptance path (e.g., "customer can add to cart from two stores and receive two orders at checkout").
- **Manual QA pass**: walk every User Story in CedarLink.md end-to-end before each milestone sign-off.

---

## 8. Deployment

| Layer | Choice |
|---|---|
| WSGI server | Gunicorn behind Nginx (reverse proxy + static file serving) |
| Database | Managed MySQL instance, daily backups |
| Secrets | `.env` (never committed); separate Dev/Staging/Prod config classes |
| Process | `flask db upgrade` on deploy, then restart Gunicorn workers |

This satisfies the Availability NFR ("accessible 24/7") with a conventional always-on process model — no serverless cold-starts to account for.

---

## 9. Milestone Order (A → N)

| Phase | Focus | Exit criteria |
|---|---|---|
| A | Env setup, repo, Flask app factory, DB connection | `flask run` boots, connects to MySQL |
| B | User model + migrations | Table exists, can insert via shell |
| C | Auth (register/login/JWT) + role decorators | Can register all 3 roles, get a working token |
| D | Store CRUD | Vendor can create/edit/deactivate a store |
| E | Category + Product CRUD + images | Vendor can fully manage a catalog |
| F | Search & filter | `/products?keyword=&category_id=&...` returns correct results |
| G | Cart system | Add/update/remove across multiple stores |
| H | Checkout / Order management | Multi-store cart → correct split orders, stock decremented |
| I | Payment integration | Webhook flips order/payment status correctly |
| J | Delivery handling | Fee shown at checkout, assignment status updates |
| K | Admin panel | User/store moderation endpoints functional |
| L | Frontend integration, all 3 dashboards | Every API above is wired to a UI screen |
| M | Testing pass | Unit + integration suite green; manual QA against user stories |
| N | Deployment | Live on Gunicorn/Nginx, smoke-tested in prod config |

---

## 10. Requirement Traceability

| Functional Requirement Group | Phase | Key Endpoints |
|---|---|---|
| User Management | C | `/auth/*`, `/users/{id}` |
| Store Management | D | `/stores/*` |
| Product Management | E | `/products/*` |
| Search & Filter | F | `/products?...` |
| Cart System | G | `/cart/*` |
| Order Management | H | `/orders/*`, `/vendor/orders` |
| Delivery Handling | I, J | `/payments/*`, `/delivery/*` |
| Admin Panel | K | `/admin/*` |

| Non-Functional Requirement | Where it's enforced |
|---|---|
| Security | bcrypt hashing, JWT roles, ownership checks (Section 3) |
| Performance | Indexes on FK/search columns (Section 2), pagination on `/products` |
| Scalability | Modular blueprints/services; no redesign needed to add stores |
| Maintainability | Routes/services/models separation (Section 1) |
| Reliability | Atomic checkout transaction (Section 5.1) |
| Availability | Gunicorn + Nginx always-on deployment (Section 8) |

---

This plan assumes the schema, attributes, and FKs as designed in the prior ERD phase; if any entity's attributes changed since then, only Section 2's column lists and Section 4's request/response bodies would need adjusting — the endpoint surface and phase order stay the same.
