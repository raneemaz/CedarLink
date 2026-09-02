import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import Toggle from "../../components/common/Toggle/Toggle";
import LocationPicker from "../../components/map/LocationPicker";
import { Section } from "./VendorStore";

function apiMessage(error, fallback) {
  return error.response?.data?.message || fallback;
}

/** Map pin + "online only" toggle for the vendor store page. */
function StoreLocationSection({ store, onStoreChange }) {
  const { t } = useTranslation();

  const [lat, setLat] = useState(store.latitude ?? null);
  const [lng, setLng] = useState(store.longitude ?? null);
  const [dirty, setDirty] = useState(false);
  const [savingPin, setSavingPin] = useState(false);
  const [savingFlag, setSavingFlag] = useState(false);

  const onlineOnly = Boolean(store.is_online_only);

  const setPin = (nextLat, nextLng) => {
    setLat(nextLat);
    setLng(nextLng);
    setDirty(true);
  };

  const clearPin = () => {
    setLat(null);
    setLng(null);
    setDirty(true);
  };

  const savePin = async () => {
    setSavingPin(true);
    try {
      const { data } = await api.put(`/stores/${store.id}/location`, {
        latitude: lat,
        longitude: lng,
      });
      onStoreChange(data.store);
      setDirty(false);
      toast.success(t("storeLocation.saved"));
    } catch (error) {
      console.error("Failed to save store location:", error);
      toast.error(apiMessage(error, t("storeLocation.errSave")));
    } finally {
      setSavingPin(false);
    }
  };

  const toggleOnlineOnly = async (next) => {
    setSavingFlag(true);
    try {
      const { data } = await api.put(`/stores/${store.id}`, {
        is_online_only: next,
      });
      onStoreChange(data.store);
      setLat(data.store.latitude ?? null);
      setLng(data.store.longitude ?? null);
      setDirty(false);
      toast.success(
        next
          ? t("storeLocation.toastOnline")
          : t("storeLocation.toastPhysical"),
      );
    } catch (error) {
      console.error("Failed to update online-only:", error);
      toast.error(apiMessage(error, t("storeLocation.errFlag")));
    } finally {
      setSavingFlag(false);
    }
  };

  return (
    <Section
      title={t("storeLocation.title")}
      description={t("storeLocation.description")}
      footer={
        !onlineOnly && (
          <Button
            type="button"
            onClick={savePin}
            disabled={!dirty || savingPin}
          >
            {savingPin ? t("vendorStore.saving") : t("storeLocation.save")}
          </Button>
        )
      }
    >
      <div className="space-y-5">
        <Toggle
          checked={onlineOnly}
          disabled={savingFlag}
          onChange={toggleOnlineOnly}
          label={t("storeLocation.onlineToggle")}
          description={t("storeLocation.onlineToggleDesc")}
        />

        {onlineOnly ? (
          <p className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-600">
            {t("storeLocation.onlineExplainer")}
          </p>
        ) : (
          <LocationPicker
            latitude={lat}
            longitude={lng}
            onChange={setPin}
            onClear={clearPin}
          />
        )}
      </div>
    </Section>
  );
}

export default StoreLocationSection;
