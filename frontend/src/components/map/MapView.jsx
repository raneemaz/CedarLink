import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { isRtl } from "../../i18n/i18n";
import {
  TILE_ATTRIBUTION,
  TILE_MAX_ZOOM,
  TILE_URL,
  useLeaflet,
} from "../../hooks/useLeaflet";

/**
 * A small non-interactive map with a single pin. No panning, no zoom
 * buttons — it just shows where a place is. The tiles are geography and
 * are never mirrored; the OSM attribution follows dir.
 */
function MapView({ latitude, longitude, className = "" }) {
  const { i18n } = useTranslation();
  const L = useLeaflet();
  const rtl = isRtl(i18n.language);

  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const coordsRef = useRef({ latitude, longitude });
  useEffect(() => {
    coordsRef.current = { latitude, longitude };
  });

  useEffect(() => {
    if (!L || !containerRef.current || mapRef.current) return;
    const { latitude: lat, longitude: lng } = coordsRef.current;
    if (lat == null || lng == null) return;

    const map = L.map(containerRef.current, {
      zoomControl: false,
      attributionControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      boxZoom: false,
      keyboard: false,
      touchZoom: false,
      tap: false,
    }).setView([lat, lng], 15);

    L.tileLayer(TILE_URL, {
      maxZoom: TILE_MAX_ZOOM,
      attribution: TILE_ATTRIBUTION,
    }).addTo(map);
    L.control
      .attribution({ position: rtl ? "bottomleft" : "bottomright" })
      .addTo(map);
    L.marker([lat, lng]).addTo(map);

    mapRef.current = map;

    // The container is often laid out (or resized by the RTL sidebar)
    // after the map is created; keep its size in sync so tiles fill it.
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, [L, rtl]);

  if (latitude == null || longitude == null) return null;

  return (
    <div
      ref={containerRef}
      dir="ltr"
      className={`h-48 w-full overflow-hidden rounded-xl border border-border bg-surface-sunken ${className}`}
    />
  );
}

export default MapView;
