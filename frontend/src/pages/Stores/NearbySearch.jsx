import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Home, LocateFixed, X } from "lucide-react";

import { LEBANON_PLACES } from "../../data/lebanonPlaces";
import { addressLabel } from "../../utils/addressLabel";
import { requestPosition } from "../../utils/geolocation";

const RADII = [1, 5, 10, 20];

/**
 * Set a search centre for the store listing — "near me" (browser
 * geolocation, only on press), a fixed place, or one of the customer's own
 * saved addresses that has a pin. The chosen centre lives in the parent's
 * ephemeral state and goes only into the search query.
 */
function NearbySearch({
  center,
  radiusKm,
  onCenterChange,
  onRadiusChange,
  savedAddresses = [],
}) {
  const { t } = useTranslation();
  const [geoBusy, setGeoBusy] = useState(false);
  const [geoErrorKey, setGeoErrorKey] = useState("");
  const [placeKey, setPlaceKey] = useState("");
  const [addressId, setAddressId] = useState(null);

  // Only a pinned address can be a centre. An address with no coordinates
  // is still a perfectly good delivery address; it just cannot centre a
  // distance search.
  const pinned = savedAddresses.filter(
    (a) => a.latitude != null && a.longitude != null,
  );

  const nearMe = () => {
    setGeoErrorKey("");
    setGeoBusy(true);
    requestPosition(
      (lat, lng) => {
        setGeoBusy(false);
        setPlaceKey("");
        setAddressId(null);
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
    setAddressId(null);
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

  const pickAddress = (address) => {
    setGeoErrorKey("");
    setPlaceKey("");

    // Tapping the active address again clears it, so the control can be
    // undone without hunting for "show all".
    if (addressId === address.id) {
      setAddressId(null);
      onCenterChange(null);
      return;
    }

    setAddressId(address.id);
    onCenterChange({
      lat: Number(address.latitude),
      lng: Number(address.longitude),
      label: addressLabel(t, address.label),
    });
  };

  const clear = () => {
    setPlaceKey("");
    setAddressId(null);
    setGeoErrorKey("");
    onCenterChange(null);
  };

  return (
    <div className="mb-4 rounded-xl bg-surface-raised p-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <button
          type="button"
          onClick={nearMe}
          disabled={geoBusy}
          className="inline-flex items-center gap-1.5 rounded-md border border-border-strong px-3 py-2 text-sm font-medium text-text-body hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
        >
          <LocateFixed className="h-4 w-4" />
          {geoBusy ? t("nearbySearch.locating") : t("nearbySearch.nearMe")}
        </button>

        <span className="text-sm text-text-faint">{t("nearbySearch.or")}</span>

        <select
          value={placeKey}
          onChange={(e) => pickPlace(e.target.value)}
          className="rounded-md border border-border-strong px-3 py-2 text-sm outline-none focus:border-brand-ring"
        >
          <option value="">{t("nearbySearch.pickPlace")}</option>
          {LEBANON_PLACES.map((place) => (
            <option key={place.key} value={place.key}>
              {t(`places.${place.key}`)}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-1.5">
          <span className="text-sm text-text-muted">
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
                  ? "bg-brand text-on-brand"
                  : "bg-surface-sunken text-text-secondary hover:bg-control"
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
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-sm font-medium text-brand hover:underline"
          >
            <X className="h-4 w-4" />
            {t("nearbySearch.showAll")}
          </button>
        )}
      </div>

      {pinned.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-2">
          <span className="text-sm text-text-muted">
            {t("nearbySearch.savedAddresses")}
          </span>
          {pinned.map((address) => (
            <button
              key={address.id}
              type="button"
              onClick={() => pickAddress(address)}
              aria-pressed={addressId === address.id}
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition ${
                addressId === address.id
                  ? "bg-brand text-on-brand"
                  : "bg-surface-sunken text-text-secondary hover:bg-control"
              }`}
            >
              <Home className="h-4 w-4" />
              {addressLabel(t, address.label)}
            </button>
          ))}
        </div>
      )}

      {center && (
        <p className="mt-2 text-sm text-text-secondary">
          {t("nearbySearch.centeredOn", { place: center.label })}
        </p>
      )}

      {geoErrorKey && (
        <p className="mt-2 text-sm text-danger">
          {t(geoErrorKey)} {t("nearbySearch.useThePicker")}
        </p>
      )}
    </div>
  );
}

export default NearbySearch;
