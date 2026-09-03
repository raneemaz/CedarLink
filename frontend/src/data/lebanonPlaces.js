// Hardcoded search centres for nearby store discovery. Deliberately NOT a
// geocoding service — a short list of well-known Lebanese cities and Beirut
// neighbourhoods with fixed coordinates. See
// docs/decisions/0018-location-and-distance-search.md.
//
// Display names come from i18n (`places.<key>`) so ar / fr get real names.
// Order: Beirut and its neighbourhoods first, then the other cities.

export const LEBANON_PLACES = [
  { key: "beirut", lat: 33.8938, lng: 35.5018 },
  { key: "hamra", lat: 33.897, lng: 35.4793 },
  { key: "achrafieh", lat: 33.8869, lng: 35.5201 },
  { key: "verdun", lat: 33.8792, lng: 35.4838 },
  { key: "gemmayzeh", lat: 33.8961, lng: 35.5142 },
  { key: "jounieh", lat: 33.9808, lng: 35.6178 },
  { key: "tripoli", lat: 34.4363, lng: 35.8497 },
  { key: "saida", lat: 33.5606, lng: 35.3758 },
  { key: "tyre", lat: 33.2705, lng: 35.2038 },
  { key: "zahle", lat: 33.8463, lng: 35.9019 },
  { key: "byblos", lat: 34.1232, lng: 35.6512 },
];
