// Browser geolocation, wrapped so every caller reports the same four
// failure modes with the same messages. Used by the vendor LocationPicker
// and the storefront "near me" search.
//
// The coordinates this returns are the customer's live position. Callers
// pass them straight into a request and hold them in ephemeral component
// state only — never localStorage, a URL, a store, or a log.

export const GEO_TIMEOUT_MS = 10000;

/** i18n key (under the `geolocation` namespace) for a getCurrentPosition error. */
export function geoErrorKey(err) {
  switch (err && err.code) {
    case 1:
      return "geolocation.denied";
    case 3:
      return "geolocation.timeout";
    default:
      return "geolocation.unavailable";
  }
}

/**
 * requestPosition(onOk, onError)
 *   onOk(latitude, longitude)
 *   onError(i18nKey)   — "geolocation.denied" | ".unavailable" | ".timeout"
 *                        | ".unsupported"
 */
export function requestPosition(onOk, onError) {
  if (!navigator.geolocation) {
    onError("geolocation.unsupported");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => onOk(pos.coords.latitude, pos.coords.longitude),
    (err) => onError(geoErrorKey(err)),
    { timeout: GEO_TIMEOUT_MS, maximumAge: 0 },
  );
}
