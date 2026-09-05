# CedarLink

[![CI](https://github.com/raneemaz/CedarLink/actions/workflows/ci.yml/badge.svg)](https://github.com/raneemaz/CedarLink/actions/workflows/ci.yml)

CedarLink is a multi-vendor marketplace for Lebanese local stores — a Flask +
SQLAlchemy JSON API and a React single-page app, with trilingual UI (English,
Arabic, French) and USD / LBP price display. It runs cash-on-delivery, the
dominant payment method in Lebanon.

Three actors:

| Actor | Can |
|---|---|
| **Customer** | Browse stores and products, search and filter, find stores near a point, cart across multiple stores, apply a coupon, checkout (COD), track and cancel orders, review what they received, manage addresses, interests and preferences |
| **Vendor** | Run one store, manage products and images, set opening hours and temporary overrides, post announcements, issue store coupons, set delivery fees and availability, advance orders through their fulfilment states |
| **Admin** | Approve and suspend stores and users, manage categories, issue platform-wide coupons, moderate reported reviews, view platform reports. Created only via CLI — never through public registration |

A fourth actor, **driver**, is planned (see the roadmap).

---

## What it does

Each of these has a decision record in `docs/decisions/` explaining the
design and its trade-offs.

**Storefront**
- Multi-store cart, priced in one place so a quote and a charge cannot
  drift (`/orders/preview` and `/orders` call the same function).
- Stock is decremented with a conditional `UPDATE`, so concurrent
  checkouts cannot oversell — proven by a barrier test, not by hope.
- Opening hours per weekday plus temporary overrides ("closed until 3pm"),
  answered by one function and DST-aware for Asia/Beirut.
- Store announcements, surfaced on the storefront.
- Distance search: pin a store on a map, then find stores near your
  location, a Lebanese place, or one of your saved addresses. Haversine
  straight-line distance — not driving distance.

**Money**
- Coupons: percentage or fixed, platform-wide or scoped to one store, with
  date windows, minimum order, usage and per-customer limits. Discounts
  come off the goods and never the delivery fee; the total clamps at zero;
  redemption is claimed with a conditional `UPDATE` and released when a
  pending order is cancelled.
- All money is `Decimal` end to end, converted to float only at the JSON
  boundary. USD is authoritative; LBP is shown as an approximate
  conversion and never as the charged amount.

**Trust**
- Reviews of a product or a store, gated on a delivered order the reviewer
  actually owns. Ratings are stored as aggregates, not recomputed per page.
- Reporting and moderation: a reported review moves published → flagged →
  removed, with an admin queue. Removed reviews are invisible to everyone
  but admins.
- Serializers are allowlists: moderation notes, approval notes and user ids
  are added back by admin routes, never leaked by a base `to_dict()`.

**Accounts**
- Two-factor authentication by authenticator app (TOTP, secret encrypted at
  rest) or emailed code, with single-use recovery codes. A TOTP code is
  accepted at most once (RFC 6238 §5.2).
- Password reset that cannot be used to discover which addresses are
  registered, and that revokes sessions issued before it.
- Interests: a customer picks up to five categories and the home page leads
  with them. **Stated, never inferred** — there is no browsing history, no
  view counter and no affinity model anywhere in the codebase.

**Localisation**
- English, Arabic and French across the whole interface, with correct RTL
  layout (logical properties, mirrored icons, unmirrored maps) and real
  Arabic plural categories including the dual.
- The API returns every translation and the client picks — locale is never
  negotiated server-side, so switching language needs no refetch.

---

## Stack

| | |
|---|---|
| Backend | Flask 3.1, SQLAlchemy 2.0, Flask-Migrate (Alembic), Flask-JWT-Extended, SQLite |
| Frontend | React 19, Vite 8, Tailwind 4, react-router 7, axios, i18next |

## Repository layout

```
app/
  __init__.py        application factory (create_app)
  config.py          Dev / Test / Prod config classes
  models/            SQLAlchemy models — data only
  routes/            HTTP blueprints — parse, call a service, return
  services/          business logic
  utils/             helpers (file handling, decorators, ...)
  cli.py             flask create-admin, flask seed
migrations/          Alembic migration history
frontend/            React SPA (its own package.json)
docs/decisions/      architecture decision records
files related/       specs (see below)
instance/            SQLite database (git-ignored, created on first migrate)
uploads/products/    uploaded product images (git-ignored)
```

## Where the specs live

- `files related/CedarLink.md` — original functional / non-functional
  requirements and user stories.
- `files related/CedarLink_Continuation_Plan.md` — code review; findings are
  numbered `CL-01` … `CL-22` and referenced from commits.
- `files related/CedarLink_Coding_Plan.md` — the roadmap. The **Delivery
  queue** section is the current work order.
- `docs/decisions/` — one page per significant design decision.

---

## Prerequisites

- **Python 3.11**
- **Node.js 20.19+** (22 LTS recommended) and npm
- Git

No database server is needed — CedarLink uses SQLite.

---

## Backend setup

From the repository root:

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env          # then edit .env (see the table below)

flask db upgrade              # create / migrate the SQLite database
flask create-admin            # create the first admin (prompts for details)
flask seed                    # load demo data (skip for a bare database)

flask run                     # http://localhost:5000
```

`flask seed` is re-runnable — it fills in whatever is missing, and
`flask seed --reset` rebuilds the demo data from scratch. Both refuse to
run when `FLASK_CONFIG=production`. See **Demo accounts** for what it
creates.

### Environment variables

Set in `.env` (copied from `.env.example`). "Required" means
`ProdConfig.validate()` raises at startup if it is missing when
`FLASK_CONFIG=production`; in development every variable has a working
default or is optional.

| Variable | Required (prod) | Purpose |
|---|:---:|---|
| `FLASK_APP` | — | Points the `flask` CLI at the app. Set to `run.py`. |
| `FLASK_CONFIG` | — | `development` \| `testing` \| `production`. Default `development`. |
| `SECRET_KEY` | **yes** | Flask session / signing key. |
| `JWT_SECRET_KEY` | **yes** | Signs JWT access and refresh tokens. |
| `TWO_FACTOR_ENCRYPTION_KEY` | **yes** | Fernet key encrypting stored TOTP secrets. |
| `DATABASE_URL` | no | SQLAlchemy URL. Default `sqlite:///cedarlink.db` (in `instance/`). |
| `CORS_ORIGINS` | no | Comma-separated browser origins allowed to call `/api/*`. Default: local Vite dev ports. Set explicitly in production. |
| `MAIL_SUPPRESS_SEND` | no | `true` prints verification codes to the console instead of emailing. Default `false`; `.env.example` ships `true`. |
| `MAIL_SERVER` `MAIL_PORT` `MAIL_USE_TLS` `MAIL_USE_SSL` `MAIL_USERNAME` `MAIL_PASSWORD` `MAIL_FROM` | no | SMTP settings, used when `MAIL_SUPPRESS_SEND=false`. |
| `PAYMENT_WEBHOOK_SECRET` | no | Shared secret for verifying payment-provider webhooks. |

### Database migrations

```bash
flask db upgrade                 # apply all migrations
flask db migrate -m "message"    # generate a migration after a model change
```

Always review a generated migration before committing it — Alembic
autogenerate gets enum and constraint changes wrong.

### Creating an admin

```bash
flask create-admin --email you@example.com --first-name Ada --last-name Lovelace --phone "+961 3 000 000"
```

Admins are verified immediately. Logging in still sends a verification code
(see "Logging in" under Demo accounts).

### Running tests

The suite runs on `TestConfig` (file-based SQLite, mail suppressed) with a
fresh schema per run and every table cleared between tests. From the repo
root, with the backend venv active:

```bash
pip install -r requirements.txt   # first run only — brings in pytest
pytest
```

Coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

Layout under `tests/`:

| Folder | What lives there |
|---|---|
| `conftest.py` | app / client / `db` fixtures, an `auth` helper that mints a JWT so tests skip the 2FA challenge, and factories: `customer`, `vendor`, `admin`, `make_store`, `make_product`, `make_order`, `add_to_cart` |
| `unit/` | service-level tests that need no HTTP layer |
| `integration/` | one test per user story in `files related/CedarLink.md` — customer, vendor and admin flows through the real HTTP layer |
| `regression/` | one test per fixed finding (CL-06, CL-12, CL-20, CL-23, CL-24), so it stays fixed |

**Foreign keys are enforced in the test suite.** SQLite ignores foreign-key
constraints unless `PRAGMA foreign_keys=ON` is issued per connection;
`conftest.py` issues it, so a green suite is evidence the schema holds under
real enforcement. Development and production do not yet enable it — see
`docs/decisions/0023-foreign-key-enforcement.md`.

Exactly one test walks the real register → verify → login → verify flow
(`test_register_verify_login_full_flow`); every other test uses the `auth`
helper.

Three tests exercise concurrency, all with the same shape: threads are
held at a lock-free barrier at the read/write seam, then released
together, so the result is deterministic and there are no sleeps.
`test_concurrent_checkout.py` proves the stock decrement cannot oversell
(CL-06); `test_coupons.py` proves two checkouts cannot both take the last
use of a coupon; `test_two_factor.py` proves one TOTP code cannot be
accepted twice. Each was run against the naive read-then-write version
first and fails there — a concurrency test that has never been seen to
fail is not evidence of anything. A clean run is fully green, no xfail.

---

## Frontend setup

From `frontend/`:

```bash
cp .env.example .env          # sets VITE_API_URL
npm install
npm run dev                   # http://localhost:5173
```

`frontend/.env` must contain the API base URL, including the `/api` prefix:

```
VITE_API_URL=http://localhost:5000/api
```

### Building for production

```bash
npm run build                 # output in frontend/dist/
npm run lint
```

**`VITE_API_URL` is read at build time and inlined into the bundle — it is
not runtime-configurable.** If the API URL changes, rebuild. Serve the
contents of `frontend/dist/` as static files, with a fallback to
`index.html` for client-side routing.

---

## Demo accounts

`flask seed` builds a demo marketplace where every screen has something
real on it. **Password for every account below: `Cedar!2026`**

### Start here

| Role | Email | What it shows |
|---|---|---|
| **Admin** | `admin@cedarlink.demo` | Store approval queue (one store waiting), review moderation queue (one flagged, one removed), platform coupons |
| **Vendor** | `vendor.hamra@cedarlink.demo` | Hamra Grocery — 8 products, opening hours, three announcements, store coupon, incoming orders |
| **Customer** | `customer.rania@cedarlink.demo` | Two pinned addresses, three chosen interests, order history with reviews and a discounted order, notifications |

### Every account

| Email | Role | Notes |
|---|---|---|
| `admin@cedarlink.demo` | admin | Admin console (`/admin`) |
| `vendor.hamra@cedarlink.demo` | vendor | Hamra Grocery, Beirut |
| `vendor.achrafieh@cedarlink.demo` | vendor | Achrafieh Pantry — **split opening hours** (09:00–14:00, 16:00–20:00) |
| `vendor.marmikhael@cedarlink.demo` | vendor | Mar Mikhael Books — **hours cross midnight** (20:00–02:00) |
| `vendor.tripoli@cedarlink.demo` | vendor | Tripoli Threads — **closed on Sundays** |
| `vendor.saida@cedarlink.demo` | vendor | Saida Electronics — **under an active override, "Power outage"** |
| `vendor.jounieh@cedarlink.demo` | vendor | Jounieh Beauty Bar — **store deactivated** by its owner |
| `vendor.cedarloom@cedarlink.demo` | vendor | Cedar Loom — **online only**, no shopfront, never in a distance result |
| `vendor.badaro@cedarlink.demo` | vendor | Badaro Home — **pending approval**, so the admin queue is not empty |
| `customer.rania@cedarlink.demo` | customer | Beirut. Home + Work addresses both pinned; interests set; wrote most of the reviews |
| `customer.karim@cedarlink.demo` | customer | Jounieh. **No interests chosen** — sees the default home order. Hides sold-out products |
| `customer.lina@cedarlink.demo` | customer | Tripoli. Left the two- and four-star reviews |
| `customer.omar@cedarlink.demo` | customer | Beirut. Has the **multi-store order** |

### What the seed creates

6 categories · 8 stores · 64 products · 60 opening-hours rows ·
10 announcements · 13 orders · 4 delivery assignments · 11 reviews ·
6 coupons · 2 coupon redemptions · 6 addresses · 6 stated interests ·
notifications for three customers.

Deliberately included so that every state renders somewhere:

- **Products** — 5 out of stock, 8 on low stock, prices $3.50–$140.00, all
  trilingual, all with an image.
- **Announcements** — live, scheduled and expired, so all badge states appear.
- **Orders** — pending, processing, delivered and cancelled; one spanning
  two stores; one with a coupon applied so the discount line is visible.
- **Deliveries** — one assigned, one picked up, two delivered. Two of
  them are on Rania's account on purpose: her Cedar Loom delivery is still
  out, so she is shown the driver's name *and* his phone number, while her
  Hamra Grocery delivery is finished, so the number is gone and only the
  name remains. That pair is ADR 0019 on screen.
- **Reviews** — ratings from 2 to 5 so nothing is uniformly 5.0; one
  reported and flagged, one removed by an admin.
- **Coupons** — active percentage, active fixed, expired, scheduled,
  store-scoped, and one that has reached its usage limit.

Aggregates are computed, not typed in: reviews go through `review_service`
so `rating_avg` is real, the coupon that shows "Limit reached" got there by
actually being redeemed at checkout, and each delivery walks
`assigned → picked_up → delivered` one step at a time through
`delivery_service`.

### Re-running it

```bash
flask seed            # fills in whatever is missing
flask seed --reset    # empties the demo tables and rebuilds from scratch
```

`--reset` is there for a screenshot session that goes wrong halfway: it
returns the database to a known state without touching the schema. Both
refuse to run when `FLASK_CONFIG=production`.

### Logging in

Every login sends a 6-digit verification code. With `MAIL_SUPPRESS_SEND=true`
(the `.env.example` default) the code is **printed to the Flask server
console** — read it there and enter it on the verification screen.

---

## Deployment

Not documented yet — deployment is a later item on the delivery queue.
