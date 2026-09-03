import { useState } from "react";
import { useTranslation } from "react-i18next";
import { LocateFixed, X } from "lucide-react";

import { LEBANON_PLACES } from "../../data/lebanonPlaces";
import { requestPosition } from "../../utils/geolocation";

const RADII = [1, 5, 10, 20];

/**
 * Set a search centre for the store listing — "near me" (browser
 * geolocation, only on press) or a fixed place. The chosen centre lives in
 * the parent's ephemeral state and goes only into the search query.
 */
function NearbySearch({ center, radiusKm, onCenterChange, onRadiusChange }) {
  const { t } = useTranslation();
  const [geoBusy, setGeoBusy] = useState(false);
  const [geoErrorKey, setGeoErrorKey] = useState("");
  const [placeKey, setPlaceKey] = useState("");

  const nearMe = () => {
    setGeoErrorKey("");
    setGeoBusy(true);
    requestPosition(
      (lat, lng) => {
        setGeoBusy(false);
        setPlaceKey("");
        onCenterChange({ lat, lng, label: t("nearbySearch.yourLocation") });
      },
      (key) => {
        setGeoBusy(false);
        setGeoErrorKey(key);
      },
    );
  };

  const pickPlace = (key) => {
    setPlaceKey(key);
    setGeoErrorKey("");
    if (!key) {
      onCenterChange(null);
      return;
    }
    const place = LEBANON_PLACES.find((p) => p.key === key);
    onCenterChange({
      lat: place.lat,
      lng: place.lng,
      label: t(`places.${key}`),
    });
  };

  const clear = () => {
    setPlaceKey("");
    setGeoErrorKey("");
    onCenterChange(null);
  };

  return (
    <div className="mb-4 rounded-xl bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <button
          type="button"
          onClick={nearMe}
          disabled={geoBusy}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <LocateFixed className="h-4 w-4" />
          {geoBusy ? t("nearbySearch.locating") : t("nearbySearch.nearMe")}
        </button>

        <span className="text-sm text-gray-400">{t("nearbySearch.or")}</span>

        <select
          value={placeKey}
          onChange={(e) => pickPlace(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-emerald-600"
        >
          <option value="">{t("nearbySearch.pickPlace")}</option>
          {LEBANON_PLACES.map((place) => (
            <option key={place.key} value={place.key}>
              {t(`places.${place.key}`)}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-1.5">
          <span className="text-sm text-gray-500">
            {t("nearbySearch.radius")}
          </span>
          {RADII.map((km) => (
            <button
              key={km}
              type="button"
              onClick={() => onRadiusChange(km)}
              aria-pressed={radiusKm === km}
              className={`rounded-md px-2.5 py-1.5 text-sm font-medium transition ${
                radiusKm === km
                  ? "bg-emerald-700 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {t("nearbySearch.km", { count: km })}
            </button>
          ))}
        </div>

        {center && (
          <button
            type="button"
            onClick={clear}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-sm font-medium text-emerald-700 hover:underline"
          >
            <X className="h-4 w-4" />
            {t("nearbySearch.showAll")}
          </button>
        )}
      </div>

      {center && (
        <p className="mt-2 text-sm text-gray-600">
          {t("nearbySearch.centeredOn", { place: center.label })}
        </p>
      )}

      {geoErrorKey && (
        <p className="mt-2 text-sm text-red-600">
          {t(geoErrorKey)} {t("nearbySearch.useThePicker")}
        </p>
      )}
    </div>
  );
}

export default NearbySearch;
