import { useState } from "react";
import { Check, Monitor, Moon, Sun } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import BackLink from "../../components/common/BackLink";
import { useTheme } from "../../context/ThemeContext";

const OPTIONS = [
  { id: "light", Icon: Sun },
  { id: "dark", Icon: Moon },
  { id: "system", Icon: Monitor },
];

function Theme() {
  const { t } = useTranslation();
  const { theme, setTheme, resolved, systemIsDark } = useTheme();

  const [saving, setSaving] = useState(false);

  const choose = async (next) => {
    setSaving(true);
    const { ok } = await setTheme(next);
    setSaving(false);

    if (ok) {
      toast.success(t("theme.saved"));
    } else {
      toast.error(t("theme.errSave"));
    }
  };

  return (
    <div className="min-h-screen bg-paper px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <BackLink to="/settings">{t("backLink.settings")}</BackLink>

        <div className="mt-6">
          <h1 className="text-title font-bold text-ink">{t("theme.title")}</h1>
          <p className="mt-1 text-ink-secondary">{t("theme.subtitle")}</p>
        </div>

        <section className="mt-8 rounded-card border border-line bg-paper-raised p-6 shadow-card">
          <div className="space-y-3">
            {OPTIONS.map(({ id, Icon }) => {
              const isSelected = theme === id;

              return (
                <button
                  key={id}
                  type="button"
                  disabled={saving}
                  onClick={() => choose(id)}
                  aria-pressed={isSelected}
                  className={`flex w-full cursor-pointer items-center justify-between rounded-card border p-4 text-start transition disabled:cursor-not-allowed ${
                    isSelected
                      ? "border-cedar-ring bg-cedar-subtle"
                      : "border-line hover:bg-paper"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={20} className="shrink-0 text-ink-muted" />

                    <div>
                      <p className="font-medium text-ink">
                        {t(`theme.option.${id}`)}
                      </p>

                      <p className="mt-1 text-small text-ink-muted">
                        {id === "system"
                          ? t("theme.systemNow", {
                              current: systemIsDark
                                ? t("theme.option.dark")
                                : t("theme.option.light"),
                            })
                          : t(`theme.describe.${id}`)}
                      </p>
                    </div>
                  </div>

                  {isSelected && (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-pill bg-cedar text-on-cedar">
                      <Check size={17} />
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          <p className="mt-6 border-t border-line-subtle pt-6 text-small text-ink-muted">
            {t("theme.showing", { current: t(`theme.option.${resolved}`) })}
          </p>
        </section>
      </div>
    </div>
  );
}

export default Theme;
