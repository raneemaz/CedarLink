import { useEffect, useState } from "react";

// Leaflet (BSD-2-Clause) + OpenStreetMap raster tiles. No API key, no
// account. The OSM Tile Usage Policy requires the "© OpenStreetMap
// contributors" attribution to be visible on every map — TILE_ATTRIBUTION
// below is passed to every tileLayer, so Leaflet renders it in the
// attribution control.
export const TILE_URL =
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">' +
  "OpenStreetMap</a> contributors";
export const TILE_MAX_ZOOM = 19;

// Default map centre when there are no coordinates yet: central Beirut.
export const BEIRUT = { lat: 33.8938, lng: 35.5018 };

// One shared dynamic import. Vite splits Leaflet (~150 KB) and its CSS
// into their own chunk, so a page with no map never downloads it.
let leafletPromise = null;

function loadLeaflet() {
  if (!leafletPromise) {
    leafletPromise = Promise.all([
      import("leaflet"),
      import("leaflet/dist/leaflet.css"),
      import("leaflet/dist/images/marker-icon.png"),
      import("leaflet/dist/images/marker-icon-2x.png"),
      import("leaflet/dist/images/marker-shadow.png"),
    ]).then(([mod, , icon, iconRetina, shadow]) => {
      const L = mod.default ?? mod;
      // The bundler rewrites the icon URLs; hand them to Leaflet's default
      // marker so the pin actually shows.
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconUrl: icon.default,
        iconRetinaUrl: iconRetina.default,
        shadowUrl: shadow.default,
      });
      return L;
    });
  }
  return leafletPromise;
}

/** Returns the Leaflet namespace once it has loaded, or null meanwhile. */
export function useLeaflet() {
  const [L, setL] = useState(null);

  useEffect(() => {
    let active = true;
    loadLeaflet().then((lib) => {
      if (active) setL(lib);
    });
    return () => {
      active = false;
    };
  }, []);

  return L;
}
