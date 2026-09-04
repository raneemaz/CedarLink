// Shared client-side reading of a store's manual override.
//
// The server is the source of truth for `is_open_now` (store_service, ADR
// 0013). These helpers only interpret the override_* fields already on the
// payload — e.g. to show "Closed — power outage, until 18:00". Pass `nowMs`
// from component state (set in an effect) so callers stay render-pure.

export function overrideIsActive(store, nowMs) {
  if (!store) return false;
  const status = store.override_status;
  if (status !== "open" && status !== "closed") return false;
  if (!store.override_until) return false;
  const until = new Date(store.override_until).getTime();
  return Number.isFinite(until) && until > nowMs;
}

// The Monday=0 weekday (matching StoreHours.day_of_week) for "now" in
// Beirut — the store's wall clock, not the viewer's.
export function beirutWeekday(date = new Date()) {
  const name = date.toLocaleDateString("en-US", {
    timeZone: "Asia/Beirut",
    weekday: "long",
  });
  return [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ].indexOf(name);
}

/**
 * "Tuesday at 09:00" for a next-opening ISO instant, in the viewer's
 * language but the *store's* clock.
 *
 * Asia/Beirut, not the browser's zone: a customer in Paris reading
 * "opens Tuesday at 09:00" means the shop's nine, and shifting it to
 * their own would be a lie about when the shop unlocks its door.
 * Returns "" for a missing or unparseable value so callers can fall back.
 */
export function formatNextOpening(iso, language) {
  if (!iso) return "";

  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return "";

  return new Intl.DateTimeFormat(language || "en", {
    timeZone: "Asia/Beirut",
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(when);
}
