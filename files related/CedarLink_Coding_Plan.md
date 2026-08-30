# CedarLink — Coding Plan v2

**Supersedes:** the original A–N phase plan (still in git history at `622f0a6` and earlier).
**Companion document:** `CedarLink_Continuation_Plan.md` — the code review this plan acts on. Finding IDs below (`CL-01` … `CL-22`) refer to it.
**Context:** internship/academic delivery that must also be **publishable**. Two goals, one target: a narrower product built to real quality, plus a documented roadmap — not a wide product built to demo quality. Nothing in v1 is simulated or faked.

---

## How to read this

The original plan had one linear A→N sequence, which stopped being useful the moment the build overtook it. This version separates three different kinds of work:

| Part | What it is | Status |
|---|---|---|
| **A** | What is already built | Done — described here so the plan reflects reality |
| **B** | Stabilization and schema foundations | **Blocks everything in Part C** |
| **C** | Feature roadmap, v1.1 → v2.0 | Sequenced, with an explicit demo cut line |
| **D** | The cut line and what to defend in the report | Decision record |
| **E** | Declared future work | Deliberately out of scope |
| **F–H** | Data model delta, API additions, traceability | Reference |

**Working assumption:** ~14 working weeks, one developer. If your deadline is shorter, move the cut line in §D up — do not compress Part B.

---

# PART A — Shipped

## A.1 What exists today

### Authentication & accounts — complete
- Registration as customer or vendor; admin created out-of-band via `flask create-admin`
- Email/SMS/WhatsApp verification challenge on registration
- Login issues a verification challenge before tokens — **OTP login is already the default path**, not a future feature
- TOTP two-factor with QR provisioning, recovery codes, encrypted secret storage
- JWT access (15 min) + refresh (30 day) tokens, `role` claim, `@role_required` decorator
- Profile management, account deactivation, reactivation, soft delete
- Unique email enforced at the database. **Unique phone is not** — see B.3.

### Store management — mostly complete (backend)
- Create, edit, activate/deactivate; ownership checks on every mutation
- Inside-city and outside-city delivery fees; `delivery_available` toggle
- Contact info, description, location as free text

### Products & catalogue — complete (backend)
- Categories with admin-only CRUD; product CRUD with vendor ownership checks
- Image upload with UUID filenames, extension allow-list, 5 MB cap, max 5 per product
- Stock tracked per product

### Search & shopping — complete (backend), unwired (frontend)
- `GET /products` supports keyword, category, store, price range, `in_stock`, sort, pagination
- Multi-store cart with per-store grouping and stock guards
- Checkout preview and checkout, splitting the cart into one order per store, in a single transaction
- Order history, order detail, vendor incoming orders, status transitions, customer cancellation with stock restoration
- Payments with a state machine and a signed webhook; delivery assignments with status transitions

### Beyond the original plan
- Saved addresses; saved payment methods (cards, hashed)
- In-app notifications with category and channel preference gating
- Shopping preferences; privacy and data controls
- USD/LBP display currency with live exchange-rate fetch and caching
- i18n scaffolding: `en.json`, `ar.json`, `fr.json`, `i18n.js`, `users.language` column

## A.2 Architecture as built

```
React 19 + Vite 8 + Tailwind 4        →  Flask 3.1 + SQLAlchemy 2.0  →  SQLite
react-router 7, axios, i18next            16 blueprints, 5 services       24 migrations
```

Deviations from the original plan's structure, all documented in the review: the `services/` layer is 5 of 11 planned modules, `schemas/` was never created, and `tests/` does not exist.

## A.3 Debt this plan inherits

22 findings, five of them deploy blockers. Part B clears them. The short version: product images are never served, imports are case-broken for Linux, nothing is configurable, secret keys have committed fallbacks, and there are no tests.

---

# PART B — Stabilization & Schema Foundations

**Nothing in Part C starts until Part B is done.** Every feature in the roadmap adds tables that reference `products`, `stores` and `orders`. Fixing the foundation after six new features are built on it costs several times what it costs now.

For a capstone specifically: Part B is not invisible work. A test suite, a service layer and a migration history are the three things an examiner can actually read as evidence of engineering judgement. Budget them as deliverables, not as chores.

## B.1 — Clear the blockers
*≈ 1 week*

- Serve `uploads/products/` via `send_from_directory`; return usable URLs from product serializers — **CL-01**
- Normalize the case-mismatched imports in `App.jsx`; verify a Linux build — **CL-02**
- Split `Config` into Dev/Test/Prod; `DATABASE_URL` from env; `VITE_API_URL` on the frontend — **CL-03**
- `ProdConfig` raises on missing `SECRET_KEY`, `JWT_SECRET_KEY`, `TWO_FACTOR_ENCRYPTION_KEY` — **CL-04**
- Delete the dead view functions in `models/store.py`, the debug prints, the seven empty placeholder files — **CL-13, CL-22**
- Root README: install, migrate, seed, create admin, run both halves

> **Exit** — fresh clone on a clean Linux machine runs from the README alone; product images display.

## B.2 — Service layer, schemas, tests
*≈ 2.5 weeks*

- **Tests first.** `pytest` + fixtures + `TestConfig`; one integration test per user story in `CedarLink.md`; failing regression tests for CL-06, CL-11, CL-12 before fixing them — **CL-05**
- Extract `order_service`, `cart_service`, `product_service`, `store_service`, `payment_service`, `delivery_service`. One `price_cart()` shared by preview and checkout — **CL-15**
- Marshmallow schemas for request validation and response serialization; one error shape across all blueprints
- Global error handlers; stop returning `str(e)` — **CL-20**
- Logging configuration; `db.session.get()` everywhere; timezone-aware datetimes
- CI: flake8, eslint, pytest, Linux frontend build

> **Exit** — no route handler over ~40 lines; the fee calculation exists once; services unit-tested without a Flask app.

## B.3 — Schema foundations
*≈ 1.5 weeks*

These are the changes that get dramatically more expensive after Part C starts. Do them while the schema is small.

**Correctness fixes that are also schema changes**
- `Product.price` → `Numeric(10, 2)`; `Decimal` through the pricing path — **CL-07**
- `Order.payment_status` separate from fulfilment `status`; create the `Payment` row inside the checkout transaction — **CL-08**
- Conditional stock decrement + `CHECK (stock >= 0)` — **CL-06**
- Unique constraint on `users.phone` *(your Phase 2 list; currently unenforced)*
- The six missing indexes — **CL-17**

**Foundations laid now, used later**

| Change | Used by | Why now |
|---|---|---|
| `ProductVariant` table; stock and price move off `Product` | C.4, cart, checkout, orders | Every later feature that touches stock or price would need rewriting otherwise. This is the single most expensive thing to defer. |
| `name_en/ar/fr`, `description_en/ar/fr` on `Product` and `Category` | C.5 | Retrofitting translation after reviews, collections and recommendations all join to products is a wide migration. |
| `latitude`, `longitude` on `Store` | C.2 | One column pair; free to add now. |
| `rating_avg`, `rating_count` on `Store` and `Product`; `sales_count` on `Product` | C.3, C.2 filters | Denormalized counters. "Highest rated" and "best selling" as live aggregates over `order_items` are the two most expensive queries in the roadmap. |
| `Order.platform_fee`, `Order.commission_rate` (nullable, default 0) | Future monetization | You chose *free for now, monetize later*. With these columns present, turning on commission is a config change. Without them it's a migration against live order data — and historical orders would have no fee record at all. |
| `approval_status` on `Store` (`pending`/`approved`/`rejected`) | C.1 | Your requirements say admin approves stores. Today anyone can create one and sell instantly. |

**On product variants — the shape that matters**

```
Product          name, description, category, store, rating_avg, sales_count
  └─ ProductVariant   sku, price, stock, is_default
       └─ VariantOption   name ("Size"), value ("M")
```

Every product gets one default variant at migration time, so nothing existing breaks. `CartItem` and `OrderItem` re-point from `product_id` to `variant_id` (keep `product_id` denormalized for display). Stock lives on the variant, never on the product. This is the migration; the vendor UI comes in C.4.

> **Exit** — every Security and Reliability NFR in `CedarLink.md` maps to a passing test; the variant migration is applied and the existing suite is still green.

---

# PART C — Feature Roadmap

## C.1 — Store Operations
*≈ 2 weeks · your Phase 3, minus location*

**Working hours**
- `StoreHours(store_id, day_of_week, opens_at, closes_at, is_closed)` — seven rows per store
- Computed `is_open_now` derived server-side in `store_service`, never in the client — timezone handling belongs in one place (Asia/Beirut, UTC+3)
- Vendor UI: a weekly schedule editor with copy-to-all-days

**Manual override**
- `Store.override_status` (`open`/`closed`/`null`), `override_reason`, `override_until`
- Reason from a fixed list plus free text: Holiday, Maintenance, Power outage, Emergency
- Override beats schedule while `override_until` is in the future, then expires automatically — an override with no expiry is how a vendor accidentally stays closed for a month
- Surfaced on the store card, store page, and blocked at cart-add

> *Power outage is a first-class reason here and not a joke — that's a genuinely good piece of local product thinking. Auto-expiry keeps it honest.*

**Announcements**
- `StoreAnnouncement(store_id, title, body, starts_at, ends_at, is_active)`
- Shown on the store page and, optionally, as a customer notification through the existing `notification_service` with a new `promotions` category — the gate already exists

**Social links**
- `StoreSocialLink(store_id, platform, url)` — a table, not columns, because the set will grow
- Platforms: Instagram, Facebook, TikTok, WhatsApp, Website, Email, Phone
- Validate and normalize per platform; WhatsApp becomes a `wa.me` deep link

**Rich store profile**
- Cover image and logo (reuse `file_utils`, separate size caps)
- Assemble: cover, logo, description, rating, review count, hours, open-now, location, delivery availability, average delivery time, categories carried, contacts, products
- `Store.avg_delivery_minutes` computed from delivered orders once there are ≥5; vendor-declared estimate before that

**Store approval**
- `PATCH /api/admin/stores/{id}/approve` and `/reject` with a reason
- New stores start `pending`; unapproved stores are invisible to customers
- Admin queue in the admin console

> **Exit** — a store page shows every element in your Phase 3 list; a vendor can set hours, override with a reason, and post an announcement; an admin approves a new store before it appears.

## C.2 — Location & Discovery
*≈ 2 weeks · merges your Phase 3 location with all of Phase 5*

These were two phases in your list. They're one feature: the moment stores have coordinates and a map, the distance filter is a `WHERE` clause away. Splitting them means building the map UI twice.

**Google Maps architecture — decided**

You chose Google Maps. That comes with a key-management requirement that has to be built correctly the first time:

- **Two keys, never one.** A *browser key* restricted by HTTP referrer, used only by the Maps JavaScript API. A *server key* restricted by IP, used only by the backend. The server key never reaches the frontend bundle.
- **Geocoding is proxied.** Vendor sets a pin → the frontend sends coordinates → the backend calls the Geocoding API with the server key and stores the result. No geocoding call originates in the browser.
- **Nearby search does NOT call Google.** Distance filtering is a Haversine calculation in SQL against stored `latitude`/`longitude`. Calling the Distance Matrix API once per store to render a list is how a free tier evaporates in an afternoon. Google draws the map; the database answers "which stores are within 5 km".
- **Directions is a link, not an integration.** A *Get Directions* button opens `https://www.google.com/maps/dir/?api=1&destination=lat,lng`. Zero quota, zero cost, works on every device, and hands off to the app the user already has.
- **Travel time is deferred.** Real ETA needs the Distance Matrix API — metered, and traffic data quality for Lebanon is weak. Show straight-line distance ("2.3 km away") instead. See §E.

**Build**
- Vendor sets store location on a draggable map pin; coordinates stored, address reverse-geocoded for display
- Customer store page: embedded map, distance from the customer, Get Directions button
- Browser geolocation with explicit permission and a graceful denial path — falls back to the customer's saved address city
- Nearby: 2 / 5 / 10 km presets plus custom radius, Haversine-ordered
- Category-scoped nearby: nearest restaurants, pharmacies, bookstores — this is just nearby + a category filter, not a separate feature

**Advanced filters — and wiring the ones that already exist**

The product filter UI is currently decorative while the API behind it is complete (**CL-19**). Wire the existing parameters first, then add:

| Products | Source |
|---|---|
| Lowest / highest price | Exists |
| Newest | Exists |
| Highest rated | `Product.rating_avg` (C.3) |
| Best selling | `Product.sales_count` counter |
| Closest | Haversine on the product's store |
| Available now | `stock > 0` **and** store open now **and** store approved and active |

| Stores | Source |
|---|---|
| Highest rated | `Store.rating_avg` |
| Closest | Haversine |
| Open now | Hours + override |
| Free delivery | `inside_city_delivery_fee = 0` |
| Most popular | Order count, 30-day window |
| Fastest delivery | `avg_delivery_minutes` |

Also in this phase: make `GET /api/stores` public and filtered (**CL-11**), enforce `is_active` and `approval_status` on every customer-facing query (**CL-12**), add the missing public stores and categories pages, and add pagination controls.

> **Exit** — a customer with location permission sees the nearest open stores; every filter in your Phase 5 list returns correct results; no Google API call happens on a list render.

## C.3 — Reviews & Ratings
*≈ 1.5 weeks · your Phase 4, first half*

- `Review(user_id, order_id, product_id?, store_id?, rating, title, body, status, created_at)`
- Exactly one of `product_id` / `store_id` set — enforced by a `CHECK` constraint
- **Verified purchase only.** `order_id` is required and must be a delivered order belonging to the reviewer. This is the single most valuable design decision in the whole review feature — it eliminates most spam before moderation ever runs.
- One review per user per product per order; edit and delete allowed, with `updated_at` shown
- `rating_avg` / `rating_count` recalculated on write, in the service, inside the transaction
- **Moderation** — `status` of `published` / `flagged` / `removed`; an admin queue; a customer report button. Reviews without moderation become a spam surface, and an examiner will ask.
- Vendor reply to a review (one per review) — cheap, and it's what makes reviews feel fair to vendors

Driver ratings are deferred to C.7, since drivers don't exist until then.

> **Exit** — a customer who received an order can rate the product and the store; averages appear on cards and profiles and drive the "highest rated" filters; an admin can remove an abusive review.

## C.4 — Product Variants (UI)
*≈ 1 week · the schema landed in B.3*

- Vendor UI: define option types (Size, Colour), generate the variant matrix, set price and stock per variant, bulk-edit
- Product page: variant selector; price and stock update on selection; out-of-stock combinations disabled rather than hidden
- Cart and checkout display the chosen variant; order items record it
- **Image per variant** — nullable `variant_id` on the existing `ProductImage`; the gallery swaps on selection. Required whenever Colour is an option type: a customer selecting "red" and seeing a blue shirt is a broken experience, not a missing polish item. Clothing is a named target category, so this is in scope.

> **Exit** — a clothing vendor lists one shirt in three sizes and four colours, with independent stock, and a customer orders a specific combination.

## C.5 — Localization completion
*≈ 1.5 weeks · your Phase 8, re-scoped*

The scaffolding exists. What's missing:

- **RTL.** `dir="rtl"` on the document root when Arabic is active; Tailwind logical properties (`ps-`/`pe-`/`ms-`/`me-` instead of `pl-`/`pr-`) throughout; mirror directional icons; verify the navbar, cart, checkout and every settings screen. This is the largest piece of work in the phase and it is mostly a careful sweep, not new logic.
- **Product and category translation UI.** The columns exist from B.3. Vendor form gets three tabs; falls back to the store's default language when a translation is blank. Never show an empty product name.
- **Automatic language detection** on first visit from `navigator.language`, then the saved profile preference wins on every subsequent visit.
- **Localized notifications.** `notification_service` renders titles and bodies from message keys, not hardcoded English strings — this is a refactor of the existing `notify_*` helpers, worth doing carefully since they're already well-structured.
- **Localized dates and numbers** via `Intl.DateTimeFormat` and `Intl.NumberFormat` with the active locale. Arabic-Indic numerals are a per-locale choice, not an automatic one — decide and be consistent.

**Arabic search.** `ILIKE '%keyword%'` does not normalize Arabic diacritics, does not stem, and cannot rank. If Arabic is a primary market this is a real defect, not a polish item. The fix is Postgres full-text search with an Arabic configuration — which is the second strong argument for the database decision in the review. On SQLite the fallback is normalizing diacritics on write into a search column and matching against that. Pick one and document it.

> **Exit** — the interface flips to RTL in Arabic with no broken layout; a product created with three names displays correctly in each; an order-placed notification arrives in the recipient's language.

## C.6 — Customer Personalization
*≈ 1.5 weeks · your Phase 4 second half + Phase 10, consolidated and renamed*

**This is not an AI phase, and calling it one would be the wrong claim to make in a report.** At launch there is no interaction history to learn from — the cold-start problem is total. Everything below is a deterministic query, delivers most of the felt value, and can be *explained* under questioning, which a black-box recommender cannot.

- **Interests** — `UserInterest(user_id, category_id)`; picked at onboarding, editable in settings; drives homepage section order
- **Recently viewed** — `ProductView(user_id, product_id, viewed_at)`, deduplicated, capped at 20
- **Trending** — order count per product and per store over a rolling 7-day window, cached
- **Frequently bought together** — co-occurrence count over `order_items` grouped by order, top 3 per product, recomputed nightly. Two SQL statements.
- **Homepage ranking** — a transparent weighted score: manual interests, then category affinity from the customer's own order history, then trending, then newest. Weights in config, not buried in code, so they can be shown and justified.
- **Search suggestions** — prefix match on product and store names plus recent searches. Not semantic search.
- **Seasonal** — an admin-curated collection with a date range. Editorial, not inferred.

**Collections** — `Collection(user_id, name)` + `CollectionItem`. Ship a default "Saved" collection so the feature works with zero setup, and let customers create more. Unlimited named collections is fine here; it's two tables.

> **Exit** — two customers with different interests and order histories see measurably different homepages, and you can explain in one sentence why each section is ordered the way it is.

## C.7 — Delivery Platform
*≈ 2 weeks · your Phase 6*

This is the phase that changes the actor model, so it needs a decision recorded rather than assumed. Today the vendor does everything a driver was specified to do (**CL-21**).

- Add `driver` to the `users.role` enum; `DriverProfile(user_id, vehicle_type, plate, is_available, rating_avg)`
- `DeliveryAssignment` gains `driver_id`, `accepted_at`, `rejected_at`, `rejection_reason`
- **Broadcast** — `DeliveryOffer(assignment_id, driver_id, status, expires_at)`; a vendor broadcasts to available drivers, first acceptance wins, the rest expire. First-acceptance-wins needs the same conditional-update discipline as the stock fix in B.3, for exactly the same reason.
- **Driver dashboard** — incoming offers, accept, reject with reason, active deliveries, customer and store details, a Get Directions link per stop
- **Vendor dashboard** — assign a specific driver, or broadcast; view driver availability; track active deliveries
- Delivery status transitions move to the driver, with the vendor retaining an override
- Driver ratings, collected on delivery confirmation

> **Exit** — a driver logs in, accepts a broadcast order, navigates, and confirms delivery; the customer sees each transition as a notification.

## C.8 — Marketplace Expansion
*≈ 0.5 weeks · your Phase 7*

Small, and higher-leverage than its size suggests — this is what lets Instagram and Facebook sellers join without a physical shop.

- `Store.business_type`: `physical` / `online` / `both`
- Location becomes optional for `online`; nearby search excludes online-only stores rather than treating them as distance-infinite
- Business profile: About us, description, contacts, social links, website — largely already built in C.1; this phase makes location optional and adds the type selector and filter

> **Exit** — an online-only seller completes onboarding without a map pin and is discoverable by category and rating.

## C.9 — Commerce Extras
*Deferred to v1.1 — see §D and §E*

Of your Phase 9 list: **multi-currency display and exchange-rate conversion are already built.** Whish Money and OMT Pay are cut permanently (no obtainable merchant account). Card payments are deferred behind a cash-on-delivery launch — see §D. Loyalty, cashback and gift cards are declared future work.

**Coupons and discount codes** are the one item worth building once v1 is live, because they're self-contained and they exercise order-total logic under constraints:
- `Coupon(code, type, value, min_order, starts_at, ends_at, usage_limit, per_user_limit, store_id?)`
- Platform-wide or store-scoped; percentage or fixed
- Validated and applied **server-side inside `price_cart()`** — never trust a client-submitted discount
- `CouponRedemption` for usage limits

---

# PART D — Publishable v1

Two goals — a top grade, and software that can actually go live — and they agree almost everywhere. Both reward real working software, a test suite, and honest documentation. They disagree in exactly one place: **a grader rewards breadth, a launch rewards a smaller thing that genuinely works.**

This plan resolves that in favour of the launch, because the grade follows. A submission that says *"here are nine features that work, deployed, tested, with a specified roadmap for six more"* scores better than fourteen half-features — and only the first one can be published.

**The governing rule: nothing in v1 is simulated.** No mock driver, no fake tracking, no pretend payment confirmation. Anything that cannot be built for real is *deferred and documented*, never faked. A feature honestly marked "v1.1" costs nothing. A feature that looks real and isn't will be found — by an examiner, or worse, by a user.

## The cash-on-delivery unlock

Card payments looked like the hard blocker. They aren't, because **cash on delivery is already built and is the dominant payment method in Lebanon.**

v1 launches COD-only. The card path stays in the codebase, fully designed, disabled by configuration, and documented as pending a merchant account — which is a business prerequisite, not an engineering gap. This is not a workaround; it is how most Lebanese marketplaces actually launch. It removes the last thing forcing you to simulate anything.

Consequence: `payment_methods.number_hash` should be **dropped in B.3**. Storing anything derived from a card number puts you in PCI DSS scope the moment real cards appear, hashes included. When card payments arrive, you store a provider token and a last-four; the number never reaches your database. Removing the column now is a one-line migration; removing it later is a compliance incident.

## In v1 — built for real

| | Why it's in |
|---|---|
| **Part B in full** | Non-negotiable for both goals. The test suite, service layer and migration history are the strongest evidence of engineering judgement an examiner can read, and the only thing that makes a live system safe to change. |
| **C.1** Store operations | Highest value per week in the plan. Hours, override with reason, announcements, approval gate. The approval gate stops being a grading feature and becomes load-bearing the moment real vendors sign up. |
| **C.2** Location & discovery | The most compelling part of the product, and the reason a customer opens it twice. |
| **C.3** Reviews & ratings | Expected in any marketplace; its absence is noticed. Moderation is mandatory once the site is public. |
| **C.4** Variants (+ variant images) | Proves the data model is real. Required for the clothing category. |
| **C.5** RTL + trilingual | Your strongest differentiator, and the clearest evidence of market awareness. Nothing else in the plan is as distinctive. |
| **C.8** Marketplace expansion | Half a week, and it's what lets Instagram sellers join — the most realistic source of early vendors. |
| **Refunds & returns** | *Promoted from future work.* You cannot take real orders without a return path. COD makes this simpler, not optional: request → vendor approval → restock decision → recorded resolution. |
| **Vendor-side order cancellation** | Cheap, and a vendor who is out of stock currently has no exit. |
| **Manual interests + collections** *(part of C.6)* | The half of personalization that works at zero traffic. Customer picks interests, homepage reorders. |
| **Real email verification** | SMTP is free and `MAIL_*` config already exists. Users receiving actual codes is a launch requirement. |
| **Deployment** | *Promoted from future work.* A capstone can live on localhost. A publishable product cannot. |
| **ToS, privacy policy, data export** | Small, and legally the minimum for taking real users' data. Account deletion already works. |

## Deferred to v1.1 — documented, not hidden

| | Why it waits |
|---|---|
| **Card payments** | Needs a merchant account. Launch COD-only; the code path is written and disabled. |
| **C.7** Delivery platform | Vendors handling their own delivery is how most Lebanese small shops already operate. The driver network is a phase-two business decision, not a missing feature. |
| **Behavioural personalization** | Trending, bought-together, recently-viewed all need order volume that does not exist on day one. The queries are specified in C.6 and cost a week once there's data. |
| **C.9** Coupons | Self-contained; build it when there's a promotion to run. |
| **Commission and payouts** | Hooks land in B.3. Turn on when the business model is decided. |

## Cut permanently

| | Why |
|---|---|
| **Whish Money, OMT Pay** | Require a merchant account tied to a registered Lebanese business. Not obtainable, at any budget, by this project. |
| **SMS / WhatsApp verification** | WhatsApp Business API requires Meta business verification — weeks, needs a legal entity, may not complete. SMS to Lebanese carriers via international aggregators is costly and unreliable. Email verification is real and free. Phone is collected but not verified in v1; say so in the UI. |
| **Live GPS tracking and real ETA** | Needs a persistent location channel and a routing provider. Google's traffic data for Lebanon is thin, so ETAs would be confidently wrong — worse than absent. And a mock would violate the no-simulation rule. |
| **Loyalty, cashback, gift cards** | Stored-value ledgers. All the difficulty of accounting, none of the marketplace learning, and no retention to improve at zero users. |

## Working practice

Construction speed is not the constraint when an AI assistant is writing most of the code — **review and integration capacity is.** Two artifacts protect against that, and both double as things an examiner can read.

**`CLAUDE.md` at the repository root.** Read automatically at the start of every session; encodes the conventions this plan establishes so generated code stops reintroducing the debt Part B removes. Write it in B.1, before any generated code lands.

```markdown
# CedarLink — conventions

## Backend
- Business logic lives in app/services/. Routes only parse, call, return.
- No Flask imports or view functions in app/models/.
- Money is Decimal + Numeric(10,2). Never float.
- db.session.get(Model, id) — never Model.query.get().
- datetime.now(timezone.utc) — never datetime.utcnow().
- One error shape everywhere. Never return str(exception).

## Database
- Stock lives on ProductVariant, never on Product.
- Product/Category names use name_en / name_ar / name_fr.
- Never store card numbers or hashes of them.

## Frontend
- pages/Settings/ with a capital S. Match the real casing exactly.
- Tailwind logical properties (ps-, pe-, ms-, me-) so RTL works.
- API base URL from VITE_API_URL. Never hardcode localhost.
```

**Decision records — written by you, not generated.** One page each, in `docs/decisions/`. They exist so that when you are asked "why did you build it this way," the answer already exists in writing. Ten cover the project:

1. Why nearby search uses Haversine in SQL, not the Distance Matrix API (one billed call per store per render vs. free)
2. Why v1 launches cash-on-delivery only
3. Why reviews require a delivered order (spam prevention through data modelling, not moderation effort)
4. Why recommendations are deterministic queries, not a trained model (cold start, explainability)
5. Why stock lives on the variant, not the product
6. Why payment state is separate from fulfilment state
7. Why the store override auto-expires
8. Why translation uses columns rather than a translations table
9. Why the checkout stock decrement is a conditional UPDATE
10. Why one store per vendor is enforced

That list is also, almost exactly, the outline of your report's design chapter.

---

# PART E — Declared future work

Listing these deliberately is stronger than omitting them. It shows the boundary was chosen rather than hit — and every item here has a written reason above.

- **Card payments** — pending a merchant account. Path designed, disabled by config, PCI-safe by construction (provider token + last four, never a PAN).
- **Commission and vendor payouts.** `Order.platform_fee` and `commission_rate` land in B.3, so enabling this is configuration rather than a migration against live order data. Full scope: rate configuration, per-order fee breakdown, payout ledger, vendor earnings dashboard, scheduling.
- **Driver network** (C.7 in full) — driver accounts, dashboards, broadcast assignment, driver ratings.
- **Behavioural personalization** — trending, frequently-bought-together, recently-viewed, seasonal curation.
- **Coupons and discount codes** — specified in C.9, ready to build.
- **Live delivery tracking, driver GPS, real ETA.**
- **Whish Money, OMT Pay, additional gateways.**
- **Loyalty points, cashback, gift cards.**
- **SMS and WhatsApp verification** — pending a registered business entity for Meta verification.
- **Stock reservation at cart-add** rather than at checkout. Today two customers can hold the last item in their carts.
- **Multi-store vendors.** The model allows many, the API assumes one (**CL-16**). One store per vendor is enforced for now.

---

# PART F — Data model delta

Existing: 18 models. After Part C: ~33.

**Modified**
- `User` — `role` enum gains `driver`; unique constraint on `phone`
- `Store` — `latitude`, `longitude`, `cover_image`, `logo`, `avg_delivery_minutes`, `business_type`, `approval_status`, `rating_avg`, `rating_count`, `override_status`, `override_reason`, `override_until`
- `Product` — `price`/`stock` move to variants; `name_en/ar/fr`, `description_en/ar/fr`, `rating_avg`, `rating_count`, `sales_count`
- `Category` — `name_en/ar/fr`
- `Order` — `payment_status`, `platform_fee`, `commission_rate`
- `CartItem`, `OrderItem` — `variant_id` (keeping `product_id` denormalized for display)
- `DeliveryAssignment` — `driver_id`, `accepted_at`, `rejected_at`, `rejection_reason`

**New — Part B**
`ProductVariant`, `VariantOption`

**New — Part C**
`StoreHours`, `StoreSocialLink`, `StoreAnnouncement`, `Review`, `ReviewReport`, `Collection`, `CollectionItem`, `UserInterest`, `ProductView`, `DriverProfile`, `DeliveryOffer`, `Coupon`, `CouponRedemption`, `TokenDenylist`

---

# PART G — API surface additions

Existing endpoints are unchanged except where noted. Base path `/api`.

### Store operations
| Method | Endpoint | Auth |
|---|---|---|
| GET / PUT | `/stores/{id}/hours` | Public / Owner |
| PATCH | `/stores/{id}/override` | Owner |
| GET / POST | `/stores/{id}/announcements` | Public / Owner |
| PUT / DELETE | `/stores/{id}/announcements/{aid}` | Owner |
| GET / PUT | `/stores/{id}/social-links` | Public / Owner |
| POST | `/stores/{id}/cover` · `/stores/{id}/logo` | Owner |
| PATCH | `/admin/stores/{id}/approve` · `/reject` | Admin |

### Location & discovery
| Method | Endpoint | Auth |
|---|---|---|
| GET | `/stores?lat=&lng=&radius_km=&category_id=&open_now=&free_delivery=&sort=` | Public |
| PUT | `/stores/{id}/location` | Owner |
| GET | `/products?...&sort=rating\|best_selling\|closest&available_now=` | Public |

### Reviews
| Method | Endpoint | Auth |
|---|---|---|
| GET / POST | `/products/{id}/reviews` · `/stores/{id}/reviews` | Public / Customer |
| PUT / DELETE | `/reviews/{id}` | Author |
| POST | `/reviews/{id}/report` · `/reviews/{id}/reply` | Auth / Vendor |
| GET / PATCH | `/admin/reviews` · `/admin/reviews/{id}/status` | Admin |

### Variants
| Method | Endpoint | Auth |
|---|---|---|
| GET / POST | `/products/{id}/variants` | Public / Owner |
| PUT / DELETE | `/variants/{id}` | Owner |

### Personalization
| Method | Endpoint | Auth |
|---|---|---|
| GET / PUT | `/users/me/interests` | Customer |
| GET / POST | `/collections` · `/collections/{id}/items` | Customer |
| GET | `/me/recently-viewed` · `/products/trending` · `/stores/trending` | Customer / Public |
| GET | `/products/{id}/bought-together` · `/search/suggestions` | Public |

### Delivery
| Method | Endpoint | Auth |
|---|---|---|
| GET / PUT | `/drivers/me` · `/drivers/me/availability` | Driver |
| GET | `/drivers/me/offers` · `/drivers/me/deliveries` | Driver |
| POST | `/delivery/offers/{id}/accept` · `/reject` | Driver |
| POST | `/delivery/assignments/broadcast` | Vendor |
| GET | `/vendor/drivers/available` | Vendor |

### Admin (currently missing — **CL-14**)
| Method | Endpoint | Auth |
|---|---|---|
| PATCH | `/admin/users/{id}/suspend` | Admin |
| GET | `/admin/reports` | Admin |

### Auth (currently missing — **CL-09**)
| Method | Endpoint | Auth |
|---|---|---|
| POST | `/auth/logout` | Auth |
| POST | `/auth/password-reset/request` · `/confirm` | Public |

> Password reset is on your Phase 2 list and is genuinely not built. It belongs in B.1 — the 2FA challenge machinery it needs already exists, so it is a small addition, and a login system without password reset is the first thing anyone will try to break.

---

# PART H — Requirement traceability

| Requirement group | Where | Status after this plan |
|---|---|---|
| User Management | A.1, B.1 | Complete + password reset |
| Store Management | A.1, C.1 | Complete + hours, override, announcements, approval |
| Product Management | A.1, B.3, C.4 | Complete + variants + translation |
| Search & Filter | C.2 | Complete + geo, ratings, availability |
| Cart System | A.1, B.3 | Complete, variant-aware |
| Order Management | A.1, B.3 | Complete + separated payment state |
| Delivery Handling | C.7 | Complete + real driver actor |
| Admin Panel | C.1, C.3, Part G | Complete + approval, suspend, moderation, reports |
| **Security NFR** | B.1, B.2, B.3 | Secrets, token revocation, rate limiting, error handling |
| **Performance NFR** | B.3, C.2 | Indexes, eager loading, denormalized counters, no per-render API calls |
| **Reliability NFR** | B.3 | Atomic checkout with a conditional stock decrement |
| **Maintainability NFR** | B.2 | Service layer, schemas, tests, CI |
| **Scalability NFR** | B.3, C.2 | Variant model, counters, geo indexing |
| **Usability NFR** | C.5 | RTL, trilingual, localized dates and notifications |
| **Availability NFR** | B.1, §D | Deployable configuration in B.1; live deployment is in v1 scope |

---

## Delivery queue — deadline 30 September 2026

**No scope is removed from this plan.** The full roadmap stands. What follows is the *order* it is built in, and one rule that makes running out of time harmless.

### The always-shippable rule

> **One item in progress at a time. Nothing is "done" until it is deployed, has a test, and has a decision record. `main` is deployable every single day.**

The deadline is ~4.5 weeks from the start of this queue and the queue is longer than that. That is expected and it is fine — *provided* the work is depth-first. Two ways to run out of time, from identical effort:

| | On 30 September | Outcome |
|---|---|---|
| **Breadth-first** | 12 features at 60%, nothing deployed | Not demonstrable, not publishable |
| **Depth-first** | Items 1–N complete, live, tested; N+1 onward documented as roadmap | Grades well, and ships |

Whatever is unreached on the deadline becomes the Future Work chapter — already specified in Parts C and E, which is a stronger chapter than most reports contain.

### The queue

Ordered by value to *both* goals divided by cost. Do not reorder without a reason written down.

| # | Item | Why here | Est. |
|---|---|---|---|
| 1 | `CLAUDE.md`, CL-01–04 blockers, password reset, **root README**, **seed command** | Nothing below this works or is visible until it is done. README and seed data serve the graded deliverables directly — see below. | 1.0 wk |
| 2 | **Vendor console** (CL-14) — store setup, product CRUD, images, delivery settings, order status, assignment | Without it a vendor cannot use CedarLink at all. This is the week it becomes a marketplace. All endpoints already exist; pure UI. | 1.0 wk |
| 3 | **Admin console** + public store browsing (CL-11) + wire product filters and pagination (CL-19) + enforce `is_active` (CL-12) | Closes every remaining "endpoint with no screen." Completes the three-actor story end to end. | 1.0 wk |
| 4 | Integration tests (15–20, one per user story) + extract `order_service` (CL-15) + `Decimal` money (CL-07) + conditional stock decrement (CL-06) + error handling (CL-20) | The evidence of engineering judgement, plus the fixes that can charge a customer wrongly. Partial Part B, deliberately. | 0.75 wk |
| 5 | **RTL sweep** (C.5, first half) | Cheapest differentiator in the plan — 70% already built, mechanical, and trilingual-with-RTL is the most distinctive claim available. | 0.5 wk |
| 6 | Store hours + manual override + announcements (C.1) | First genuinely new feature. Demos in 30 seconds; the power-outage override is memorable. | 1.0 wk |
| 7 | Reviews, ratings, moderation (C.3) | Expected in a marketplace; verified-purchase gating is a defensible design decision. | 1.0 wk |
| 8 | Maps, location, nearby search (C.2) | The most compelling feature in the product, and the most expensive so far. | 1.5 wk |
| 9 | Product variants UI + variant images (C.4) | Needs the B.3 schema migration first. | 1.5 wk |
| 10 | Refunds, returns, vendor cancellation | Required before real money or real vendors, not before a grade. | 1.0 wk |
| 11 | Product translation UI (C.5, second half) | Columns from B.3; three-tab vendor form. | 0.75 wk |
| 12 | Interests, collections, homepage ordering (C.6 manual half) | Works at zero traffic. | 0.75 wk |
| 13 | Business types, online-only stores (C.8) | | 0.5 wk |
| 14 | Driver accounts and dashboards (C.7) | | 2.0 wk |
| 15 | Coupons, behavioural personalization (C.9, C.6 second half) | | 2.0 wk |
| 16 | **Deployment** — Dockerfile, compose, health endpoint, Postgres, hosting | Last. Not a graded deliverable; see below. | 1.0 wk |

**Items 1–5 (≈4.25 weeks) are the realistic reach by 30 September.** That lands a tested, trilingual marketplace where all three actors can do their jobs. Everything from item 6 down is roadmap — and every one of them is already specified above, which is exactly what the Future Work chapter needs.

### Graded deliverables — the repository and the report

No published website is required. What is assessed is **the GitHub repository and the written report**, and that changes what earns marks:

| Artifact | Why it matters | Status |
|---|---|---|
| **Root README** | The first thing anyone sees on GitHub. Currently the only README in the repo is Vite's default template text under `frontend/`. | Item 1 |
| **Seed command** | Every screenshot in the report, every manual QA pass, and any grader who runs the project needs realistic data. The database currently holds 2 users, 0 stores, 0 products — **an empty marketplace cannot be screenshotted.** | Item 1 |
| **Commit history** | Conventional commits referencing finding IDs (`fix(CL-01): …`) read as deliberate engineering. Already in good shape — keep it. | Ongoing |
| **`tests/`** | Visible in the repo without running anything. Clear test names are the evidence. | Item 4 |
| **`docs/decisions/`** | Feeds the report's design chapter directly. | Per feature |
| **Screenshots** | With no live site, these carry all the visual evidence. Capture each feature the day it lands. | Per feature |

### Deployment — last, item 16

Deployment is not assessed, so it moves to the end of the queue. Constraints recorded for whenever it happens:

- **SQLite and `uploads/` are files.** The host needs a persistent volume. Most free PaaS tiers have ephemeral filesystems and erase the database and every product image on each redeploy. **Vercel cannot host the Flask backend** — Python there runs as serverless functions with an ephemeral `/tmp` and no long-running process. Vercel is ideal for the frontend only.
- **The cheap path when the time comes:** move the database to a free managed Postgres (Neon ~3 GiB, Supabase ~500 MB) and let images reset, rather than adding object storage. That is roughly two hours — `psycopg2-binary`, drop the unused `PyMySQL`, repoint `DATABASE_URL` — and Postgres was already the right call for write concurrency and Arabic full-text search. Fold it into item 4 if convenient.
- **Gotcha:** `db.Enum(...)` columns become real Postgres ENUM types and Alembic handles them poorly. Run migrations against a fresh database and verify.
- **Gotcha:** `VITE_API_URL` is inlined by Vite **at build time**. Rebuild the frontend whenever the API host changes.

### Report, written incrementally

The report is due the same day as the code. Building until the 30th means no report. So:

- Write the decision record **when the feature is finished**, not at the end. Ten of them are listed in §D.
- Screenshot each feature the day it lands.
- Code freeze **28 September**. The last two days are the report and a final smoke test.

### Note on the estimates below

Estimates assume AI-assisted construction. **Part B barely compresses and Part C compresses a lot**, because B is decisions — what belongs in a service, what the variant table should look like — and those take the same thinking time whoever types them. C is volume, and volume is where the speedup lives. Part B is therefore a *larger* share of this timeline than of the previous one, not a smaller one.

| Work | Weeks | Cumulative |
|---|---|---|
| B.1 Blockers + `CLAUDE.md` + password reset | 1.0 | 1.0 |
| B.2 Services, schemas, tests, CI | 2.0 | 3.0 |
| B.3 Schema foundations (variants, translations, geo, counters, PCI cleanup) | 1.5 | 4.5 |
| C.1 Store operations | 1.5 | 6.0 |
| C.2 Location & discovery | 1.5 | 7.5 |
| C.3 Reviews, ratings, moderation | 1.0 | 8.5 |
| C.4 Variants UI + variant images | 1.0 | 9.5 |
| C.5 Localization: RTL, translations, localized notifications | 1.5 | 11.0 |
| Refunds, returns, vendor cancellation | 1.0 | 12.0 |
| C.8 Business types + interests/collections | 1.0 | 13.0 |
| Launch: real email, ToS, privacy, data export, seed data | 0.5 | 13.5 |
| Deployment, monitoring, backups, smoke test | 1.0 | 14.5 |

**≈ 14–15 weeks to a live, tested, trilingual marketplace** with nothing simulated.

**If the deadline is shorter, cut in this order** — each step removes a whole feature rather than degrading everything:

1. **−1.5 wk** C.5 down to RTL only; defer product translation UI (columns stay, vendor enters one language)
2. **−1.0 wk** C.4 UI; keep the variant schema, one default variant per product
3. **−1.0 wk** C.8 and collections; keep interests
4. **−1.0 wk** Refunds down to admin-recorded resolution with no customer-facing request form

Never cut from Part B. A narrower product on a tested foundation both grades and ships better than a wider one on an untested foundation — and only the first can be handed to a real vendor.
