import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import { formatDateTime } from "../../utils/helpers";
import { Section, fieldClass } from "./VendorStore";

const REASON_KEYS = ["holiday", "maintenance", "powerOutage", "emergency"];

// Wire values for PATCH /stores/{id}/override. Named durations are resolved
// server-side against Beirut time (ADR 0013) — the browser only sends the
// name. "custom" is the one case that carries an explicit instant.
const DURATIONS = ["1h", "3h", "end_of_day", "tomorrow_morning", "custom"];

function StoreOverridePanel({ store, onStoreChange }) {
  const { t, i18n } = useTranslation();

  // Time-derived, so it is computed in an effect rather than during render.
  const [overrideActive, setOverrideActive] = useState(false);
  useEffect(() => {
    const active =
      (store.override_status === "open" ||
        store.override_status === "closed") &&
      store.override_until &&
      new Date(store.override_until).getTime() > Date.now();
    setOverrideActive(Boolean(active));
  }, [store.override_status, store.override_until]);

  const [status, setStatus] = useState("closed");
  const [reason, setReason] = useState("");
  const [duration, setDuration] = useState("3h");
  const [customUntil, setCustomUntil] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [clearing, setClearing] = useState(false);

  const currentState = () => {
    if (!overrideActive) return t("storeOverride.stateSchedule");
    const until = formatDateTime(store.override_until, i18n.language);
    return store.override_status === "open"
      ? t("storeOverride.stateOpen", { until })
      : t("storeOverride.stateClosed", { until });
  };

  const applyOverride = async (event) => {
    event.preventDefault();
    setError(null);

    const payload = { status, reason: reason.trim(), duration };

    if (duration === "custom") {
      if (!customUntil) {
        setError(t("storeOverride.errUntilRequired"));
        return;
      }
      const parsed = new Date(customUntil);
      if (Number.isNaN(parsed.getTime()) || parsed.getTime() <= Date.now()) {
        setError(t("storeOverride.errUntilFuture"));
        return;
      }
      payload.until = parsed.toISOString();
    }

    setSubmitting(true);
    try {
      const response = await api.patch(
        `/stores/${store.id}/override`,
        payload,
      );
      onStoreChange(response.data.store);
      toast.success(t("storeOverride.toastApplied"));
      setReason("");
      setCustomUntil("");
    } catch (err) {
      console.error("Failed to set store override:", err);
      setError(err.response?.data?.message || t("storeOverride.errApply"));
    } finally {
      setSubmitting(false);
    }
  };

  const resumeSchedule = async () => {
    setClearing(true);
    setError(null);
    try {
      const response = await api.delete(`/stores/${store.id}/override`);
      onStoreChange(response.data.store);
      toast.success(t("storeOverride.toastResumed"));
    } catch (err) {
      console.error("Failed to clear store override:", err);
      setError(err.response?.data?.message || t("storeOverride.errResume"));
    } finally {
      setClearing(false);
    }
  };

  return (
    <Section
      title={t("storeOverride.title")}
      description={t("storeOverride.description")}
    >
      <div className="space-y-6">
        <div className="rounded-xl bg-paper px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            {t("storeOverride.currentLabel")}
          </p>
          <p className="mt-1 text-sm font-semibold text-ink">
            {currentState()}
          </p>
          {overrideActive && store.override_reason && (
            <p className="mt-1 text-sm text-ink-secondary">
              {store.override_reason}
            </p>
          )}
          {overrideActive && (
            <div className="mt-3">
              <Button
                variant="secondary"
                onClick={resumeSchedule}
                disabled={clearing}
              >
                {clearing
                  ? t("vendorStore.saving")
                  : t("storeOverride.resume")}
              </Button>
            </div>
          )}
        </div>

        <form onSubmit={applyOverride} className="space-y-5">
          <p className="text-sm font-semibold text-ink">
            {overrideActive
              ? t("storeOverride.replaceHeading")
              : t("storeOverride.setHeading")}
          </p>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink-body">
              {t("storeOverride.statusLabel")}
            </legend>
            <div className="flex flex-wrap gap-2">
              {["closed", "open"].map((option) => (
                <label
                  key={option}
                  className={`cursor-pointer rounded-lg border px-4 py-2 text-sm font-medium ${
                    status === option
                      ? "border-cedar-ring bg-cedar-subtle text-cedar-strong"
                      : "border-line-strong text-ink-secondary"
                  }`}
                >
                  <input
                    type="radio"
                    name="override-status"
                    value={option}
                    checked={status === option}
                    onChange={() => setStatus(option)}
                    className="sr-only"
                  />
                  {t(`storeOverride.status.${option}`)}
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor="override-reason"
              className="mb-2 block text-sm font-medium text-ink-body"
            >
              {t("storeOverride.reasonLabel")}
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {REASON_KEYS.map((key) => {
                const label = t(`storeOverride.reasons.${key}`);
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setReason(label)}
                    className="rounded-full border border-line-strong px-3 py-1 text-xs font-medium text-ink-secondary hover:border-cedar-ring hover:text-cedar-strong"
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            <input
              id="override-reason"
              type="text"
              value={reason}
              maxLength={255}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t("storeOverride.reasonPlaceholder")}
              className={fieldClass}
            />
          </div>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink-body">
              {t("storeOverride.durationLabel")}
            </legend>
            <div className="flex flex-wrap gap-2">
              {DURATIONS.map((option) => (
                <label
                  key={option}
                  className={`cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium ${
                    duration === option
                      ? "border-cedar-ring bg-cedar-subtle text-cedar-strong"
                      : "border-line-strong text-ink-secondary"
                  }`}
                >
                  <input
                    type="radio"
                    name="override-duration"
                    value={option}
                    checked={duration === option}
                    onChange={() => setDuration(option)}
                    className="sr-only"
                  />
                  {t(`storeOverride.durations.${option}`)}
                </label>
              ))}
            </div>

            {duration === "custom" && (
              <input
                type="datetime-local"
                dir="ltr"
                aria-label={t("storeOverride.durations.custom")}
                value={customUntil}
                onChange={(e) => setCustomUntil(e.target.value)}
                className="mt-2 rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              />
            )}
          </fieldset>

          {error && <p className="text-xs text-danger">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting
              ? t("vendorStore.saving")
              : t("storeOverride.apply")}
          </Button>
        </form>
      </div>
    </Section>
  );
}

export default StoreOverridePanel;
