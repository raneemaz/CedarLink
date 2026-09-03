# 0018 — Location data and distance search

**Date:** 2026-09-02
**Status:** accepted
**Queue item:** 8 (C.2 — location & discovery, first slice: coordinates +
distance search)

Stores and saved addresses can now carry a `latitude` / `longitude` map
pin (`Numeric(9, 6)`, nullable), and `GET /api/stores` gains a
`near=lat,lng&radius=km` mode that returns stores nearest-first with a
`distance_km` on each. This record covers the decisions that could have
gone another way.

## 1. No geocoding service — the vendor drops a pin

The obvious design is "vendor types their address, we geocode it to
coordinates". We are not doing that.

- **Nominatim** (the free OpenStreetMap geocoder) forbids heavy or
  bulk use, asks for ≤ 1 request/second, requires a genuine
  `User-Agent`/contact, and offers no uptime guarantee. A store-onboarding
  flow that geocodes on every save is exactly the pattern its usage policy
  is written to stop, and the moment it rate-limits us the onboarding form
  breaks.
- **Google / Mapbox / HERE geocoding** all need a billing account with a
  card on file before the first request. This is a student/internship
  project; there is no card, and "add a paid dependency to onboarding" is
  not a reasonable ask.
- **Address resolution in Lebanon is poor anyway.** Lebanese addresses are
  frequently informal — "the building behind the Spinneys in Hamra, third
  floor" — with no postcodes and inconsistent street naming. A geocoder
  returns a confident wrong point often enough that a human dragging a pin
  on a map is *more* accurate, not less.

So the vendor places a pin on a map and we store the two numbers. The
address text stays free-form and is not parsed. Same for a saved delivery
address: an optional pin the customer can drop, independent of the typed
address line.

## 2. Leaflet + OpenStreetMap for the map itself

The pin-drop UI (a later frontend slice) uses **Leaflet** with
**OpenStreetMap** raster tiles:

- No API key, no billing account, no per-load quota to blow through.
- OSM tile coverage for Beirut and Lebanon's cities is good.
- Leaflet is ~40 KB, framework-agnostic, and if OSM's tile-usage policy
  ever becomes a problem the tile URL is a one-line swap to a paid
  provider or a self-hosted set.

Google Maps was the original plan (it is named in the roadmap). It is
rejected here for the same billing-account reason as its geocoder, and
because its JS SDK is heavy and its terms restrict storing or reusing the
data it returns.

## 3. Bounding box, then Haversine — and the longitude scaling

`store_service.nearby(lat, lng, radius_km, query)` is two stages:

### Stage 1 — a SQL bounding box (uses the index)

```sql
WHERE latitude  BETWEEN :lat - :dlat AND :lat + :dlat
  AND longitude BETWEEN :lng - :dlng AND :lng + :dlng
```

with a composite index on `(latitude, longitude)`, so this is a range
scan, not a table scan. The half-widths:

```
dlat = radius_km / 111.045
dlng = radius_km / (111.045 · cos(latitude))
```

**The `cos(latitude)` is the point.** One degree of latitude is ~111 km
anywhere. One degree of *longitude* is `111.045 km × cos(latitude)` — the
meridians converge toward the poles. At Beirut's latitude (~33.9°),
`cos ≈ 0.83`, so a degree of longitude is only ~92 km. Using 111 for both
makes the box **17 % too narrow east–west**, and a store that is due east
or west near the edge of the radius falls outside the box and is silently
dropped — the results just quietly miss real stores, with no error. The
regression test
(`test_bounding_box_keeps_a_store_due_east_or_west_at_the_radius_edge`)
places a store at 0.92 × radius due east, which is inside the true circle
but outside a flat-111 box, and fails if the scaling is wrong.

Near the poles `cos(latitude) → 0` and `dlng → ∞`; the code clamps `cos`
to `1e-6`. Lebanon never gets close, but a global input shouldn't divide
by zero.

The box is padded by 200 m so float error at the very edge can never clip
a genuine in-radius store — Stage 2 does the real cut anyway.

### Stage 2 — Haversine in Python on the survivors

The box is a rectangle; the radius is a circle. For each store that
survived the box, `haversine_km` computes the true great-circle distance
and the store is kept only if `distance ≤ radius_km`. Survivors are sorted
by true distance (ascending) and each gets `distance_km` rounded to one
decimal. Pagination is applied to this sorted list in the route.

Haversine, not a database `earthdistance`/PostGIS call: the box has
already cut the candidate set to the handful of stores in one
neighbourhood, so the trig runs on a few rows in Python and needs no
extension. If the store count per city ever makes that slow, the fix is
PostGIS, not a smarter box.

### Haversine is straight-line distance, not driving distance

`distance_km` is **as-the-crow-flies**. It is not routing distance and not
travel time. In Beirut the two diverge substantially — one-way streets,
the Corniche, and traffic mean a 2 km straight-line hop can be a 20-minute
drive. Real ETA needs a routing provider (metered, and traffic data
quality for Lebanon is weak), so it is deliberately out of scope; the
number is honest about being a distance, labelled as such, and useful for
"which of these stores is closest", which is the actual question.

## 4. A store with no pin is absent, not at (0, 0)

`nearby` filters `latitude IS NOT NULL AND longitude IS NOT NULL` in
Stage 1. A coordless store is **excluded from distance results entirely** —
never coerced to `(0, 0)`, which is a point in the Atlantic Ocean off
Ghana and would sort every unpinned store ~5000 km away (or, with a huge
radius, first). It still appears in the plain (no-`near`) directory
exactly as before. Existing stores keep working everywhere; distance
search is simply a view they are not in until their vendor drops a pin.

## 5. `is_online_only`

`Store.is_online_only` (Boolean, default false) marks a seller with no
shopfront — made-to-order, ships nationwide. Turning it on **clears the
store's coordinates** (`store_service.set_online_only`), and `nearby`
also filters `is_online_only IS FALSE` as a belt-and-braces guard, so an
online-only store never shows in a distance search even if a stale
coordinate somehow survives. `set_location` refuses to pin an
online-only store.

## 6. Addresses get the same treatment

`Address.latitude` / `Address.longitude`, same type, same validation
(`app/utils/geo.validate_coords` — range check, both-or-neither), nullable
so every address saved before this feature keeps working. Used later to
default the "stores near me" centre to the customer's saved pin instead of
asking for browser geolocation on every visit.

## 7. Privacy

The customer's search coordinates arrive as `?near=lat,lng` and are used
for that one request only. They are **not logged** — not in an access
log line, not in an analytics event, nowhere. The route has no logging on
that path and a comment says why.

### Two kinds of coordinate, and only one of them is stored

Since the saved-address slice landed, `/stores` can be centred on three
things, and they do **not** get the same treatment:

| centre | source | stored? |
|---|---|---|
| "Near me" | `navigator.geolocation`, on press only | **never** |
| A Lebanese place | hardcoded table, not personal data | n/a |
| A saved address | `Address.latitude` / `longitude` | **yes, already** |

The distinction is consent, not sensitivity. **Live geolocation is
where the customer is right now.** They did not ask us to keep it, only
to use it, so it lives in React state for the lifetime of the view and
goes into the query string and nowhere else — no `localStorage`, no URL,
no persisted state, no log.

**A saved address is different: the customer deliberately saved it.**
They opened the address form, dropped a pin, and pressed save. Persisting
it is the whole point of the feature — the pin is theirs, it is attached
to an address they chose to keep, and they can clear it from the same
form. Reusing it as a search centre discloses nothing they have not
already stored on purpose, and it spares them a geolocation prompt on
every visit.

So: **storing the pin is fine because the customer saved it; storing the
live fix would not be, because they did not.** Do not let the two merge —
in particular, do not "helpfully" write a live geolocation fix onto a
saved address, and do not use a saved pin as an implicit default centre
without the customer tapping it.

The pin stays optional. An address with no coordinates saves and behaves
exactly as it did before; it simply does not appear as a search centre.

## Migration

`da88ef8e28e3` — `stores` + `addresses` gain `latitude` / `longitude`;
`stores` gains `is_online_only` and the `ix_stores_lat_lng` composite
index. `flask db migrate`, reviewed, verified `upgrade` from empty /
`downgrade` to base / `upgrade` again, and `flask db check` clean.
