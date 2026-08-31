# CedarLink

Multi-vendor marketplace for Lebanese local stores. Flask + SQLAlchemy API, React SPA, three languages (en / ar / fr), USD + LBP display.

## Specs — read before non-trivial work

Both live in `files related/`:

- **`CedarLink_Continuation_Plan.md`** — code review. Findings are numbered `CL-01`…`CL-22`; commit messages and prompts reference them.
- **`CedarLink_Coding_Plan.md`** — roadmap. The **Delivery queue** section in Part D is the current work order.
- `CedarLink.md` — original functional/non-functional requirements and user stories.

## Stack

| | |
|---|---|
| Backend | Flask 3.1, SQLAlchemy 2.0, Flask-Migrate, Flask-JWT-Extended, SQLite |
| Frontend | React 19, Vite 8, Tailwind 4, react-router 7, axios, i18next |
| Layout | `app/` (models, routes, services, utils) · `frontend/src/` · `migrations/` |

## Commands

```bash
# Backend (venv active, from repo root)
flask db upgrade            # apply migrations
flask db migrate -m "..."   # generate a migration — always review it before applying
flask create-admin          # admins are never created via a public endpoint
flask run

# Frontend (from frontend/)
npm run dev
npm run build               # must pass; catches case-sensitivity bugs
npm run lint
```

## Conventions

### Backend

- Business logic lives in `app/services/`. Route handlers only parse the request, call a service, and return a response. Target: no handler over ~40 lines.
- **No Flask imports or view functions in `app/models/`.** Models are data only — columns, relationships, `to_dict`.
- Money is `Decimal` with `Numeric(10, 2)`. Never `float`. Convert to float only at the JSON boundary.
- `db.session.get(Model, id)` — never `Model.query.get()` or `get_or_404()` (legacy SQLAlchemy 1.x).
- `datetime.now(timezone.utc)` — never `datetime.utcnow()`.
- One error shape across every blueprint. **Never return `str(exception)` to a client** — log it with a correlation id and return the id.
- Never store card numbers or anything derived from them, hashes included. Provider token + last four only.
- Pricing logic exists in exactly one place. `/orders/preview` and `/orders` must call the same function — if they diverge, a customer gets quoted one price and charged another.

### Database

- Stock is decremented with a conditional UPDATE (`WHERE stock >= :qty`) and a zero rowcount means out-of-stock. Never read-then-write.
- `Product` has `name_en` / `name_ar` / `name_fr` and `description_en` / `description_ar` / `description_fr`; `Category` has `name_en` / `name_ar` / `name_fr` (its `description` is single-language). English is required (`nullable=False`); Arabic and French are nullable and fall back to English when blank. `.name` / `.description` are SQLAlchemy synonyms for the English column — use them for queries and internal callers; use `localized_name(lang)` / `localized_description(lang)` for anything user-facing. The API returns every translation and the client picks — locale is never negotiated server-side. See docs/decisions/0012-product-category-translation.md.
- Review every generated migration before applying it. Autogenerate gets enum and constraint changes wrong.

### Frontend

- **`pages/Settings/` has a capital S.** Match real folder casing exactly — Windows hides mismatches and the Linux build fails on them.
- Tailwind logical properties (`ps-` `pe-` `ms-` `me-`), not `pl-`/`pr-`, so the Arabic RTL layout works.
- API base URL comes from `VITE_API_URL`. Never hardcode `localhost`.
- No `localStorage` for anything that must survive or be shared — tokens and light preferences only.

## Roles

`customer` · `vendor` · `admin` (and `driver`, planned). Public registration may only create `customer` or `vendor` — admin is CLI-only. Every mutating endpoint checks ownership as well as role.

## Working rules

- **One delivery-queue item per session.** Don't start item N+1 before N is finished.
- **Done means deployed** — merged, tested, live, with a decision record in `docs/decisions/`. Anything else is 0%, not 80%.
- `main` stays deployable every day.
- Show diffs incrementally, not as one large change. The human is the reviewer and that is the bottleneck.
- Don't refactor code outside the task at hand. Note it instead.

## Deadline

**30 September 2026**, code freeze 28 September. Work depth-first: whatever is finished must be live and tested, and whatever is unreached stays documented as roadmap.
