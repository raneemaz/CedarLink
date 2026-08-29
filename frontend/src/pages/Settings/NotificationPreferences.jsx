import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import api from "../../services/api";
import Toggle from "../../components/common/Toggle/Toggle";

const DEFAULT_PREFERENCES = {
  order_updates: true,
  promotions: false,
  email: true,
  in_app: true,
};

const CATEGORY_KEYS = ["order_updates", "promotions"];
const CHANNEL_KEYS = ["email", "in_app"];

function getStoredUser() {
  const savedUser = localStorage.getItem("user");

  if (!savedUser || savedUser === "undefined") {
    return null;
  }

  try {
    return JSON.parse(savedUser);
  } catch {
    localStorage.removeItem("user");
    return null;
  }
}

function Notifications() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      toast.error(t("notifications.loadError"));
      setLoading(false);
      return;
    }

    const fetchPreferences = async () => {
      try {
        const response = await api.get(`/users/${storedUser.id}`);
        const serverPreferences =
          response.data?.user?.notification_preferences;

        if (serverPreferences) {
          setPreferences({ ...DEFAULT_PREFERENCES, ...serverPreferences });
        }
      } catch (error) {
        console.error("Failed to load notification preferences:", error);
        toast.error(t("notifications.loadError"));
      } finally {
        setLoading(false);
      }
    };

    fetchPreferences();
  }, [t]);

  const handleToggle = (key) => (nextValue) => {
    setPreferences((previous) => ({ ...previous, [key]: nextValue }));
  };

  const handleSave = async () => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      toast.error(t("notifications.loadError"));
      return;
    }

    setSaving(true);

    try {
      const response = await api.put(
        `/users/${storedUser.id}/notification-preferences`,
        preferences,
      );

      const savedPreferences =
        response.data?.user?.notification_preferences || preferences;

      setPreferences({ ...DEFAULT_PREFERENCES, ...savedPreferences });

      // Keep the stored user blob in sync.
      localStorage.setItem(
        "user",
        JSON.stringify({
          ...storedUser,
          notification_preferences: savedPreferences,
        }),
      );

      toast.success(t("notifications.saved"));
    } catch (error) {
      console.error("Failed to update notification preferences:", error);
      toast.error(
        error.response?.data?.message || t("notifications.saveError"),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate("/settings")}
            className="mb-4 cursor-pointer text-sm text-green-700 hover:underline"
          >
            {t("common.backToSettings")}
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <Bell size={24} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {t("notifications.title")}
              </h1>

              <p className="mt-1 text-sm text-gray-600">
                {t("notifications.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">
            {t("notifications.loading")}
          </p>
        ) : (
          <div className="space-y-6">
            {/* What to notify me about */}
            <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
              <div className="border-b border-gray-100 px-6 py-5">
                <h2 className="text-xl font-semibold text-gray-900">
                  {t("notifications.whatSection")}
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  {t("notifications.whatSectionDesc")}
                </p>
              </div>

              <div className="divide-y divide-gray-100 px-6">
                {CATEGORY_KEYS.map((key) => (
                  <Toggle
                    key={key}
                    checked={preferences[key]}
                    onChange={handleToggle(key)}
                    label={t(`notifications.${key}Label`)}
                    description={t(`notifications.${key}Desc`)}
                  />
                ))}
              </div>
            </section>

            {/* How to reach me */}
            <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
              <div className="border-b border-gray-100 px-6 py-5">
                <h2 className="text-xl font-semibold text-gray-900">
                  {t("notifications.howSection")}
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  {t("notifications.howSectionDesc")}
                </p>
              </div>

              <div className="divide-y divide-gray-100 px-6">
                {CHANNEL_KEYS.map((key) => (
                  <Toggle
                    key={key}
                    checked={preferences[key]}
                    onChange={handleToggle(key)}
                    label={t(`notifications.${key}Label`)}
                    description={t(`notifications.${key}Desc`)}
                  />
                ))}
              </div>
            </section>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving
                  ? t("notifications.saving")
                  : t("notifications.save")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Notifications;
