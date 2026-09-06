import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Pencil, Trash2 } from "lucide-react";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import { Section, fieldClass } from "./VendorStore";

const EMPTY_FORM = {
  title: "",
  body: "",
  starts_at: "",
  ends_at: "",
  is_active: true,
};

// ISO instant -> value for <input type="datetime-local"> (viewer-local).
function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function statusKey(item, nowMs) {
  if (!item.is_active) return "inactive";
  if (item.is_live) return "live";
  if (item.starts_at && new Date(item.starts_at).getTime() > nowMs) {
    return "scheduled";
  }
  return "ended";
}

const STATUS_STYLE = {
  live: "bg-success-subtle text-success-strong",
  scheduled: "bg-warning-tint text-warning",
  ended: "bg-paper-sunken text-ink-muted",
  inactive: "bg-paper-sunken text-ink-muted",
};

function StoreAnnouncementsManager({ storeId }) {
  const { t } = useTranslation();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null | "new" | id
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);

  // Mount-time "now" — accurate enough to label scheduled vs. ended, and a
  // reload after every write refreshes the server-computed is_live flag.
  const [nowMs] = useState(() => Date.now());

  const refresh = () => setReloadTick((n) => n + 1);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const response = await api.get(`/stores/${storeId}/announcements`);
        if (!cancelled) setItems(response.data.announcements || []);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load announcements:", error);
        toast.error(
          error.response?.data?.message || t("storeAnnouncements.errLoad"),
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [storeId, reloadTick, t]);

  const startCreate = () => {
    setForm(EMPTY_FORM);
    setFormError(null);
    setEditing("new");
  };

  const startEdit = (item) => {
    setForm({
      title: item.title,
      body: item.body,
      starts_at: toLocalInput(item.starts_at),
      ends_at: toLocalInput(item.ends_at),
      is_active: item.is_active,
    });
    setFormError(null);
    setEditing(item.id);
  };

  const cancelEdit = () => {
    setEditing(null);
    setFormError(null);
  };

  const submit = async (event) => {
    event.preventDefault();
    setFormError(null);

    if (!form.title.trim() || !form.body.trim()) {
      setFormError(t("storeAnnouncements.errTitleBody"));
      return;
    }

    const payload = {
      title: form.title.trim(),
      body: form.body.trim(),
      is_active: form.is_active,
      ends_at: form.ends_at ? new Date(form.ends_at).toISOString() : null,
    };
    if (form.starts_at) {
      payload.starts_at = new Date(form.starts_at).toISOString();
    }

    setSaving(true);
    try {
      if (editing === "new") {
        await api.post(`/stores/${storeId}/announcements`, payload);
        toast.success(t("storeAnnouncements.toastCreated"));
      } else {
        await api.put(
          `/stores/${storeId}/announcements/${editing}`,
          payload,
        );
        toast.success(t("storeAnnouncements.toastUpdated"));
      }
      setEditing(null);
      refresh();
    } catch (error) {
      console.error("Failed to save announcement:", error);
      setFormError(
        error.response?.data?.message || t("storeAnnouncements.errSave"),
      );
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (item) => {
    try {
      await api.put(`/stores/${storeId}/announcements/${item.id}`, {
        is_active: !item.is_active,
      });
      refresh();
    } catch (error) {
      console.error("Failed to update announcement:", error);
      toast.error(
        error.response?.data?.message || t("storeAnnouncements.errSave"),
      );
    }
  };

  const remove = async (item) => {
    if (!window.confirm(t("storeAnnouncements.confirmDelete"))) return;
    try {
      await api.delete(`/stores/${storeId}/announcements/${item.id}`);
      toast.success(t("storeAnnouncements.toastDeleted"));
      refresh();
    } catch (error) {
      console.error("Failed to delete announcement:", error);
      toast.error(
        error.response?.data?.message || t("storeAnnouncements.errSave"),
      );
    }
  };

  const activeCount = items.filter((i) => i.is_active).length;

  return (
    <Section
      title={t("storeAnnouncements.title")}
      description={t("storeAnnouncements.description")}
      footer={
        editing === null ? (
          <Button onClick={startCreate} disabled={loading}>
            {t("storeAnnouncements.new")}
          </Button>
        ) : null
      }
    >
      {loading ? (
        <p className="text-sm text-ink-muted">
          {t("storeAnnouncements.loading")}
        </p>
      ) : (
        <div className="space-y-4">
          <p className="text-xs text-ink-muted">
            {t("storeAnnouncements.activeCount", { count: activeCount })}
          </p>

          {items.length === 0 && editing === null && (
            <p className="text-sm text-ink-faint">
              {t("storeAnnouncements.empty")}
            </p>
          )}

          <ul className="divide-y divide-line-subtle">
            {items.map((item) => {
              const key = statusKey(item, nowMs);
              return (
                <li key={item.id} className="py-4 first:pt-0">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 font-semibold text-ink">
                        {item.title}
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[key]}`}
                        >
                          {t(`storeAnnouncements.status.${key}`)}
                        </span>
                      </p>
                      <p className="mt-1 text-sm text-ink-secondary">
                        {item.body}
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-1">
                      <button
                        type="button"
                        onClick={() => startEdit(item)}
                        aria-label={t("storeAnnouncements.edit")}
                        className="rounded-lg p-2 text-ink-faint hover:bg-paper-sunken hover:text-ink-body"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(item)}
                        aria-label={t("storeAnnouncements.delete")}
                        className="rounded-lg p-2 text-ink-faint hover:bg-paper-sunken hover:text-danger"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => toggleActive(item)}
                    className="mt-2 text-xs font-medium text-cedar hover:underline"
                  >
                    {item.is_active
                      ? t("storeAnnouncements.deactivate")
                      : t("storeAnnouncements.activate")}
                  </button>
                </li>
              );
            })}
          </ul>

          {editing !== null && (
            <form
              onSubmit={submit}
              className="space-y-4 rounded-xl border border-line p-4"
            >
              <p className="text-sm font-semibold text-ink">
                {editing === "new"
                  ? t("storeAnnouncements.newHeading")
                  : t("storeAnnouncements.editHeading")}
              </p>

              <div>
                <label
                  htmlFor="ann-title"
                  className="mb-1 block text-sm font-medium text-ink-body"
                >
                  {t("storeAnnouncements.fieldTitle")}
                </label>
                <input
                  id="ann-title"
                  type="text"
                  maxLength={255}
                  value={form.title}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, title: e.target.value }))
                  }
                  className={fieldClass}
                />
              </div>

              <div>
                <label
                  htmlFor="ann-body"
                  className="mb-1 block text-sm font-medium text-ink-body"
                >
                  {t("storeAnnouncements.fieldBody")}
                </label>
                <textarea
                  id="ann-body"
                  rows="3"
                  maxLength={2000}
                  value={form.body}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, body: e.target.value }))
                  }
                  className={`resize-none ${fieldClass}`}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="ann-start"
                    className="mb-1 block text-sm font-medium text-ink-body"
                  >
                    {t("storeAnnouncements.fieldStart")}
                  </label>
                  <input
                    id="ann-start"
                    type="datetime-local"
                    dir="ltr"
                    value={form.starts_at}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, starts_at: e.target.value }))
                    }
                    className="w-full rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
                  />
                </div>
                <div>
                  <label
                    htmlFor="ann-end"
                    className="mb-1 block text-sm font-medium text-ink-body"
                  >
                    {t("storeAnnouncements.fieldEnd")}
                  </label>
                  <input
                    id="ann-end"
                    type="datetime-local"
                    dir="ltr"
                    value={form.ends_at}
                    onChange={(e) =>
                      setForm((p) => ({ ...p, ends_at: e.target.value }))
                    }
                    className="w-full rounded-lg border border-line-strong px-3 py-2 text-sm outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-ink-body">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, is_active: e.target.checked }))
                  }
                />
                {t("storeAnnouncements.fieldActive")}
              </label>

              {formError && (
                <p className="text-xs text-danger">{formError}</p>
              )}

              <div className="flex gap-3">
                <Button type="submit" disabled={saving}>
                  {saving
                    ? t("vendorStore.saving")
                    : t("storeAnnouncements.save")}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={cancelEdit}
                  disabled={saving}
                >
                  {t("storeAnnouncements.cancel")}
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </Section>
  );
}

export default StoreAnnouncementsManager;
