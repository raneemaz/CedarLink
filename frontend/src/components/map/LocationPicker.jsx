import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { LocateFixed, X } from "lucide-react";

import { isRtl } from "../../i18n/i18n";
import {
  BEIRUT,
  TILE_ATTRIBUTION,
  TILE_MAX_ZOOM,
  TILE_URL,
  useLeaflet,
} from "../../hooks/useLeaflet";

const GEO_TIMEOUT_MS = 10000;

const round6 = (n) => Math.round(n * 1e6) / 1e6;

/**
 * Reusable map location picker: draggable pin, "use my location", the
 * chosen coordinates as text, and clear. Used by the vendor store page
 * and (later) the saved-address form. The map itself is geography and is
 * never mirrored; its controls and the surrounding text follow dir.
 */
function LocationPicker({
  latitude,
  longitude,
  onChange,
  onClear,
  disabled = false,
}) {
  const { t, i18n } = useTranslation();
  const L = useLeaflet();
  const rtl = isRtl(i18n.language);

  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);

  // Latest props / callbacks for the Leaflet event handlers, which are
  // registered once. Synced after every render (writing a ref in an
  // effect is fine; doing it during render is not).
  const live = useRef({ latitude, longitude, disabled, onChange });
  useEffect(() => {
    live.current = { latitude, longitude, disabled, onChange };
  });

  const [geoError, setGeoError] = useState("");
  const [locating, setLocating] = useState(false);

  const hasCoords = latitude != null && longitude != null;

  // Build the map once Leaflet has loaded; rebuild on a language switch so
  // the zoom control moves to the new inline-start side.
  useEffect(() => {
    if (!L || !containerRef.current || mapRef.current) return;

    const { latitude: lat0, longitude: lng0, disabled: d0 } = live.current;
    const start = lat0 != null ? [lat0, lng0] : [BEIRUT.lat, BEIRUT.lng];

    const map = L.map(containerRef.current, {
      zoomControl: false,
      attributionControl: false,
    }).setView(start, lat0 != null ? 16 : 13);

    L.tileLayer(TILE_URL, {
      maxZoom: TILE_MAX_ZOOM,
      attribution: TILE_ATTRIBUTION,
    }).addTo(map);
    L.control.zoom({ position: rtl ? "topright" : "topleft" }).addTo(map);
    L.control
      .attribution({ position: rtl ? "bottomleft" : "bottomright" })
      .addTo(map);

    const marker = L.marker(start, { draggable: !d0 }).addTo(map);
    const commit = (latlng) =>
      live.current.onChange(round6(latlng.lat), round6(latlng.lng));

    marker.on("dragend", () => commit(marker.getLatLng()));
    map.on("click", (e) => {
      if (live.current.disabled) return;
      marker.setLatLng(e.latlng);
      commit(e.latlng);
    });

    mapRef.current = map;
    markerRef.current = marker;

    // The container is often laid out (or resized by the RTL sidebar or a
    // toggled section) after the map is created; keep it in sync.
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [L, rtl]);

  const useMyLocation = () => {
    setGeoError("");
    if (!navigator.geolocation) {
      setGeoError(t("locationPicker.geoUnsupported"));
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const lat = round6(pos.coords.latitude);
        const lng = round6(pos.coords.longitude);
        if (mapRef.current && markerRef.current) {
          markerRef.current.setLatLng([lat, lng]);
          mapRef.current.setView([lat, lng], 16);
        }
        onChange(lat, lng);
      },
      (err) => {
        setLocating(false);
        const byCode = {
          1: "locationPicker.geoDenied",
          2: "locationPicker.geoUnavailable",
          3: "locationPicker.geoTimeout",
        };
        setGeoError(t(byCode[err.code] || "locationPicker.geoUnavailable"));
      },
      { timeout: GEO_TIMEOUT_MS, maximumAge: 0 },
    );
  };

  const clear = () => {
    setGeoError("");
    if (mapRef.current && markerRef.current) {
      markerRef.current.setLatLng([BEIRUT.lat, BEIRUT.lng]);
      mapRef.current.setView([BEIRUT.lat, BEIRUT.lng], 13);
    }
    onClear();
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={useMyLocation}
          disabled={disabled || locating}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <LocateFixed className="h-4 w-4" />
          {locating
            ? t("locationPicker.locating")
            : t("locationPicker.useMyLocation")}
        </button>

        {hasCoords && (
          <button
            type="button"
            onClick={clear}
            disabled={disabled}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <X className="h-4 w-4" />
            {t("locationPicker.clear")}
          </button>
        )}
      </div>

      {geoError && (
        <p className="mt-2 text-sm text-red-600">
          {geoError} {t("locationPicker.dragInstead")}
        </p>
      )}

      {/* dir="ltr": a map is geography, not layout. */}
      <div
        ref={containerRef}
        dir="ltr"
        className="mt-3 h-64 w-full overflow-hidden rounded-xl border border-gray-200 bg-gray-100"
      />

      <p className="mt-2 text-xs text-gray-500">
        {hasCoords ? (
          <span dir="ltr">
            {t("locationPicker.coords", {
              lat: Number(latitude).toFixed(6),
              lng: Number(longitude).toFixed(6),
            })}
          </span>
        ) : (
          t("locationPicker.noPin")
        )}
      </p>
    </div>
  );
}

export default LocationPicker;
