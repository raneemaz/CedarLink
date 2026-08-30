# CedarLink

CedarLink is a multi-vendor marketplace for Lebanese local stores — a Flask +
SQLAlchemy JSON API and a React single-page app, with trilingual UI (English,
Arabic, French) and USD / LBP price display. It runs cash-on-delivery, the
dominant payment method in Lebanon.

Three actors:

| Actor | Can |
|---|---|
| **Customer** | Browse stores and products, filter and search, cart across multiple stores, checkout (COD), track and cancel orders, manage addresses and preferences |
| **Vendor** | Run one store, manage products and images, set delivery fees and availability, advance orders through their fulfilment states |
| **Admin** | Approve and suspend stores and users, manage categories, view platform reports. Created only via CLI — never through public registration |

A fourth actor, **driver**, is planned (see the roadmap).

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

`flask seed` is idempotent — safe to run again — and refuses to run when
`FLASK_CONFIG=production`.

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

An automated test suite is not in the repository yet — it is the next item
on the delivery queue (`pytest` + `TestConfig`, one integration test per
user story). When present it will run with:

```bash
pytest
```

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

After `flask seed`, these accounts exist. **Password for all of them:
`Cedar!2026`**

| Email | Role | Notes |
|---|---|---|
| `admin@cedarlink.demo` | admin | Admin console (`/admin`). Created by `flask seed` — safe because the seed refuses to run in production. |
| `vendor.beirut@cedarlink.demo` | vendor | Hamra Grocery (Beirut) |
| `vendor.tripoli@cedarlink.demo` | vendor | Tripoli Threads (Tripoli) |
| `vendor.saida@cedarlink.demo` | vendor | Saida Electronics (Saida) |
| `vendor.jounieh@cedarlink.demo` | vendor | Jounieh Beauty Bar (Jounieh) — **store deactivated** |
| `customer.rania@cedarlink.demo` | customer | Beirut addresses, has delivered + pending orders |
| `customer.karim@cedarlink.demo` | customer | Jounieh address, has processing + canceled orders |
| `customer.lina@cedarlink.demo` | customer | Tripoli address, has delivered + processing orders |

The seed also creates 5 categories, 4 stores, 20 products (2 out of stock,
with generated placeholder images), saved addresses, and orders in every
status.

### Logging in

Every login sends a 6-digit verification code. With `MAIL_SUPPRESS_SEND=true`
(the `.env.example` default) the code is **printed to the Flask server
console** — read it there and enter it on the verification screen.

---

## Deployment

Not documented yet — deployment is a later item on the delivery queue.
