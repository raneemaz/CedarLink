import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Plus, Trash2 } from "lucide-react";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import { Section } from "./VendorStore";

// A compact field — the shared fieldClass is w-full, which would stack the
// two time inputs on top of each other.
const timeFieldClass =
  "rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none " +
  "focus:border-green-600 focus:ring-1 focus:ring-green-600";

// day_of_week is 0-6 with Monday = 0 (Python datetime.weekday()), so the
// display order below is also the wire value — index === day_of_week.
const DAY_KEYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

const WEEKDAY_INDICES = [0, 1, 2, 3, 4];

const DEFAULT_RANGE = { opens_at: "09:00", closes_at: "17:00" };

function emptyWeek() {
  return Array.from({ length: 7 }, () => []);
}

function groupWeek(hours) {
  const week = emptyWeek();
  for (const row of hours || []) {
    if (Number.isInteger(row.day_of_week) && row.day_of_week >= 0 &&
        row.day_of_week <= 6) {
      week[row.day_of_week].push({
        opens_at: row.opens_at,
        closes_at: row.closes_at,
      });
    }
  }
  week.forEach((ranges) =>
    ranges.sort((a, b) => a.opens_at.localeCompare(b.opens_at)),
  );
  return week;
}

function toMinutes(value) {
  const [h, m] = value.split(":").map(Number);
  return h * 60 + m;
}

// Mirrors store_service._assert_no_overlap / _parse_time on the client so the
// vendor sees the problem on the day it belongs to, not as a 400 toast.
function dayError(ranges, t) {
  for (const range of ranges) {
    if (!range.opens_at || !range.closes_at) {
      return t("storeHours.errIncomplete");
    }
    if (range.opens_at === range.closes_at) {
      return t("storeHours.errSameTime");
    }
  }

  const spans = ranges
    .map((range) => {
      const start = toMinutes(range.opens_at);
      const rawEnd = toMinutes(range.closes_at);
      // closes <= opens means the range crosses midnight; project it onto
      // its own day as [opens, 24:00) for the overlap check.
      return [start, rawEnd > start ? rawEnd : 24 * 60];
    })
    .sort((a, b) => a[0] - b[0]);

  for (let i = 1; i < spans.length; i += 1) {
    if (spans[i][0] < spans[i - 1][1]) {
      return t("storeHours.errOverlap");
    }
  }
  return null;
}

function StoreHoursEditor({ storeId }) {
  const { t } = useTranslation();

  const [week, setWeek] = useState(emptyWeek);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const response = await api.get(`/stores/${storeId}/hours`);
        if (!cancelled) setWeek(groupWeek(response.data.hours));
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load store hours:", error);
          toast.error(
            error.response?.data?.message || t("storeHours.errLoad"),
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [storeId, t]);

  const mutateDay = (dayIndex, nextRanges) => {
    setWeek((prev) => {
      const next = prev.map((ranges, i) =>
        i === dayIndex ? nextRanges : ranges,
      );
      return next;
    });
    setErrors((prev) => {
      if (!(dayIndex in prev)) return prev;
      const next = { ...prev };
      delete next[dayIndex];
      return next;
    });
  };

  const addRange = (dayIndex) => {
    mutateDay(dayIndex, [...week[dayIndex], { ...DEFAULT_RANGE }]);
  };

  const removeRange = (dayIndex, rangeIndex) => {
    mutateDay(
      dayIndex,
      week[dayIndex].filter((_, i) => i !== rangeIndex),
    );
  };

  const updateRange = (dayIndex, rangeIndex, field, value) => {
    mutateDay(
      dayIndex,
      week[dayIndex].map((range, i) =>
        i === rangeIndex ? { ...range, [field]: value } : range,
      ),
    );
  };

  const copyTo = (sourceIndex, targetIndices) => {
    const clone = () =>
      week[sourceIndex].map((range) => ({ ...range }));
    setWeek((prev) =>
      prev.map((ranges, i) =>
        targetIndices.includes(i) ? clone() : ranges,
      ),
    );
    setErrors({});
  };

  const handleSave = async (event) => {
    event.preventDefault();

    const nextErrors = {};
    week.forEach((ranges, dayIndex) => {
      const error = dayError(ranges, t);
      if (error) nextErrors[dayIndex] = error;
    });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    const hours = [];
    week.forEach((ranges, dayIndex) => {
      ranges.forEach((range) => {
        hours.push({
          day_of_week: dayIndex,
          opens_at: range.opens_at,
          closes_at: range.closes_at,
        });
      });
    });

    setSaving(true);
    try {
      const response = await api.put(`/stores/${storeId}/hours`, { hours });
      setWeek(groupWeek(response.data.hours));
      toast.success(t("storeHours.toastSaved"));
    } catch (error) {
      console.error("Failed to save store hours:", error);
      toast.error(error.response?.data?.message || t("storeHours.errSave"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section
      title={t("storeHours.title")}
      description={t("storeHours.description")}
      onSubmit={handleSave}
      footer={
        <Button type="submit" disabled={loading || saving}>
          {saving ? t("vendorStore.saving") : t("storeHours.save")}
        </Button>
      }
    >
      {loading ? (
        <p className="text-sm text-gray-500">{t("storeHours.loading")}</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {DAY_KEYS.map((dayKey, dayIndex) => {
            const ranges = week[dayIndex];
            return (
              <li key={dayKey} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-gray-900">
                    {t(`storeHours.days.${dayKey}`)}
                  </span>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                    <button
                      type="button"
                      onClick={() => copyTo(dayIndex, [0, 1, 2, 3, 4, 5, 6])}
                      className="font-medium text-green-700 hover:underline"
                    >
                      {t("storeHours.copyToAll")}
                    </button>
                    <button
                      type="button"
                      onClick={() => copyTo(dayIndex, WEEKDAY_INDICES)}
                      className="font-medium text-green-700 hover:underline"
                    >
                      {t("storeHours.copyToWeekdays")}
                    </button>
                  </div>
                </div>

                <div className="mt-3 space-y-2">
                  {ranges.length === 0 && (
                    <p className="text-sm text-gray-400">
                      {t("storeHours.closed")}
                    </p>
                  )}

                  {ranges.map((range, rangeIndex) => (
                    <div
                      key={rangeIndex}
                      className="flex flex-wrap items-center gap-2"
                    >
                      {/* dir="ltr": a time is HH:MM in every locale — it must
                          not visually reverse inside the RTL layout. */}
                      <input
                        type="time"
                        dir="ltr"
                        aria-label={t("storeHours.opensAt")}
                        value={range.opens_at}
                        onChange={(e) =>
                          updateRange(
                            dayIndex,
                            rangeIndex,
                            "opens_at",
                            e.target.value,
                          )
                        }
                        className={timeFieldClass}
                      />
                      <span className="text-sm text-gray-500">
                        {t("storeHours.rangeSeparator")}
                      </span>
                      <input
                        type="time"
                        dir="ltr"
                        aria-label={t("storeHours.closesAt")}
                        value={range.closes_at}
                        onChange={(e) =>
                          updateRange(
                            dayIndex,
                            rangeIndex,
                            "closes_at",
                            e.target.value,
                          )
                        }
                        className={timeFieldClass}
                      />
                      <button
                        type="button"
                        onClick={() => removeRange(dayIndex, rangeIndex)}
                        aria-label={t("storeHours.removeRange")}
                        className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={() => addRange(dayIndex)}
                    className="inline-flex items-center gap-1 text-sm font-medium text-green-700 hover:underline"
                  >
                    <Plus className="h-4 w-4" />
                    {t("storeHours.addRange")}
                  </button>

                  {errors[dayIndex] && (
                    <p className="text-xs text-red-600">{errors[dayIndex]}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

export default StoreHoursEditor;
