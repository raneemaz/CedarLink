import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { AlertCircle, ArrowRight } from "lucide-react";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import { SOCIAL_PLATFORMS } from "../../components/store/socialPlatforms";
import { Section, fieldClass } from "./VendorStore";

const EMPTY = Object.fromEntries(
  SOCIAL_PLATFORMS.map((platform) => [platform.id, ""]),
);

function apiMessage(error, fallback) {
  return error.response?.data?.message || fallback;
}

/**
 * "Where to find us" for the vendor store page.
 *
 * One row per platform. Whatever the vendor types is normalised by the
 * server and echoed back under the field, so `@hamragrocery` visibly
 * becomes `https://www.instagram.com/hamragrocery` before anything is
 * saved. The preview is a server call rather than a copy of the rules in
 * JavaScript: the value ends up in an href on a public page, and a second
 * implementation of "what is safe to put there" is a second implementation
 * that can disagree with the first.
 */
function StoreSocialLinksSection({ storeId }) {
  const { t } = useTranslation();

  const [values, setValues] = useState(EMPTY);
  const [preview, setPreview] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Guards against a slow preview response landing after a newer one.
  const previewToken = useRef(0);

  useEffect(() => {
    let cancelled = false;

    api
      .get(`/stores/${storeId}/social-links`)
      .then(({ data }) => {
        if (cancelled) return;

        const next = { ...EMPTY };
        for (const link of data.social_links || []) {
          next[link.platform] = link.value;
        }
        setValues(next);
      })
      .catch((error) => {
        console.error("Failed to load store links:", error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [storeId]);

  const runPreview = useCallback(
    async (next) => {
      const token = ++previewToken.current;

      const entries = SOCIAL_PLATFORMS.filter(
        (platform) => next[platform.id]?.trim(),
      ).map((platform) => ({
        platform: platform.id,
        value: next[platform.id],
      }));

      if (entries.length === 0) {
        setPreview({});
        return;
      }

      try {
        const { data } = await api.post(
          `/stores/${storeId}/social-links/preview`,
          { social_links: entries },
        );

        if (token !== previewToken.current) return;

        setPreview(
          Object.fromEntries(
            (data.social_links || []).map((row) => [row.platform, row]),
          ),
        );
      } catch (error) {
        console.error("Failed to preview store links:", error);
      }
    },
    [storeId],
  );

  // Debounced: a preview per keystroke would be a request per keystroke.
  useEffect(() => {
    if (loading) return undefined;

    const timer = setTimeout(() => runPreview(values), 400);
    return () => clearTimeout(timer);
  }, [values, loading, runPreview]);

  const handleChange = (platformId) => (event) => {
    const { value } = event.target;
    setValues((prev) => ({ ...prev, [platformId]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);

    const entries = SOCIAL_PLATFORMS.filter(
      (platform) => values[platform.id]?.trim(),
    ).map((platform) => ({
      platform: platform.id,
      value: values[platform.id],
    }));

    try {
      const { data } = await api.put(`/stores/${storeId}/social-links`, {
        social_links: entries,
      });

      const next = { ...EMPTY };
      for (const link of data.social_links || []) {
        next[link.platform] = link.value;
      }
      setValues(next);
      setPreview({});

      toast.success(t("vendorStore.social.saved"));
    } catch (error) {
      console.error("Failed to save store links:", error);
      toast.error(apiMessage(error, t("vendorStore.social.errSave")));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section
      title={t("vendorStore.social.title")}
      description={t("vendorStore.social.description")}
      onSubmit={handleSubmit}
      footer={
        <Button type="submit" disabled={saving || loading}>
          {saving ? t("vendorStore.saving") : t("vendorStore.social.save")}
        </Button>
      }
    >
      {loading ? (
        <p className="text-sm text-ink-muted">
          {t("vendorStore.social.loading")}
        </p>
      ) : (
        <div className="space-y-5">
          {SOCIAL_PLATFORMS.map(({ id, Icon, hint }) => {
            const row = preview[id];
            const typed = values[id]?.trim();
            const inputId = `social-${id}`;

            return (
              <div key={id}>
                <label
                  htmlFor={inputId}
                  className="mb-2 flex items-center gap-2 text-sm font-medium text-ink-body"
                >
                  <Icon size={16} className="shrink-0 text-ink-faint" />
                  {t(`social.platform.${id}`)}
                </label>

                <input
                  id={inputId}
                  name={inputId}
                  value={values[id]}
                  onChange={handleChange(id)}
                  placeholder={hint}
                  dir="ltr"
                  className={fieldClass}
                />

                {typed && row?.error && (
                  <p className="mt-1 flex items-start gap-1.5 text-xs text-danger">
                    <AlertCircle size={13} className="mt-0.5 shrink-0" />
                    {row.error}
                  </p>
                )}

                {typed && !row?.error && row?.value && (
                  <p className="mt-1 flex items-start gap-1.5 text-xs text-ink-muted">
                    <ArrowRight size={13} className="mt-0.5 shrink-0" />
                    <span>
                      {t("vendorStore.social.willSaveAs")}{" "}
                      <span dir="ltr" className="font-mono break-all">
                        {row.value}
                      </span>
                    </span>
                  </p>
                )}
              </div>
            );
          })}

          <p className="text-xs text-ink-muted">
            {t("vendorStore.social.clearHint")}
          </p>
        </div>
      )}
    </Section>
  );
}

export default StoreSocialLinksSection;
