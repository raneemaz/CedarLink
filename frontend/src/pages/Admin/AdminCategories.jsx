import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import LanguageTabs from "../../components/common/LanguageTabs/LanguageTabs";
import { localizedName } from "../../utils/localize";

const fieldClass =
  "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none " +
  "focus:border-green-600 focus:ring-1 focus:ring-green-600";

const LANG_LABEL = {
  en: "language.english",
  ar: "language.arabic",
  fr: "language.french",
};

const EMPTY_NAMES = { en: "", ar: "", fr: "" };

function namesPayload(names) {
  return {
    name_en: names.en.trim(),
    name_ar: names.ar.trim(),
    name_fr: names.fr.trim(),
  };
}

function filledFlags(names) {
  return {
    en: Boolean(names.en.trim()),
    ar: Boolean(names.ar.trim()),
    fr: Boolean(names.fr.trim()),
  };
}

function AdminCategories() {
  const { t, i18n } = useTranslation();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  const [newNames, setNewNames] = useState(EMPTY_NAMES);
  const [newDescription, setNewDescription] = useState("");
  const [newLang, setNewLang] = useState("en");
  const [creating, setCreating] = useState(false);

  const [editId, setEditId] = useState(null);
  const [editNames, setEditNames] = useState(EMPTY_NAMES);
  const [editDescription, setEditDescription] = useState("");
  const [editLang, setEditLang] = useState("en");
  const [savingEdit, setSavingEdit] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    const response = await api.get("/categories");
    setCategories(response.data || []);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load categories:", error);
          toast.error(t("adminCategories.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!newNames.en.trim()) {
      setNewLang("en");
      toast.error(t("adminCategories.errNameEnRequired"));
      return;
    }
    setCreating(true);
    try {
      await api.post("/categories", {
        ...namesPayload(newNames),
        description: newDescription.trim() || null,
      });
      toast.success(t("adminCategories.toastCreated"));
      setNewNames(EMPTY_NAMES);
      setNewDescription("");
      setNewLang("en");
      await load();
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("adminCategories.errCreate"),
      );
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (category) => {
    setEditId(category.id);
    setEditNames({
      en: category.name_en || "",
      ar: category.name_ar || "",
      fr: category.name_fr || "",
    });
    setEditDescription(category.description || "");
    setEditLang("en");
  };

  const saveEdit = async () => {
    if (!editNames.en.trim()) {
      setEditLang("en");
      toast.error(t("adminCategories.errNameEnRequired"));
      return;
    }
    setSavingEdit(true);
    try {
      await api.put(`/categories/${editId}`, {
        ...namesPayload(editNames),
        description: editDescription.trim() || null,
      });
      toast.success(t("adminCategories.toastUpdated"));
      setEditId(null);
      await load();
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("adminCategories.errUpdate"),
      );
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/categories/${deleteTarget.id}`);
      toast.success(
        t("adminCategories.toastDeleted", {
          name: localizedName(deleteTarget, i18n.language),
        }),
      );
      await load();
      setDeleteTarget(null);
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("adminCategories.errDelete"),
      );
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">{t("adminCategories.loading")}</p>;
  }

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold text-gray-900">{t("adminCategories.title")}</h1>

      <form
        onSubmit={handleCreate}
        className="mb-6 rounded-2xl bg-white p-5 shadow-sm"
      >
        <p className="mb-3 text-sm font-semibold text-gray-700">
          {t("adminCategories.addHeading")}
        </p>

        <LanguageTabs
          active={newLang}
          onSelect={setNewLang}
          filled={filledFlags(newNames)}
        />

        <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-start">
          <input
            type="text"
            value={newNames[newLang]}
            onChange={(event) =>
              setNewNames((prev) => ({ ...prev, [newLang]: event.target.value }))
            }
            placeholder={t("adminCategories.nameLangLabel", {
              lang: t(LANG_LABEL[newLang]),
            })}
            className={fieldClass}
          />
          <input
            type="text"
            value={newDescription}
            onChange={(event) => setNewDescription(event.target.value)}
            placeholder={t("adminCategories.descriptionPlaceholder")}
            className={fieldClass}
          />
          <Button type="submit" disabled={creating}>
            {creating ? t("adminCategories.adding") : t("adminCategories.add")}
          </Button>
        </div>

        <p className="mt-2 text-xs text-gray-500">
          {t("translationTabs.fallbackHint")}
        </p>
      </form>

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-start text-xs uppercase tracking-wide text-gray-400">
              <th className="px-4 py-3 font-medium">{t("adminCategories.colName")}</th>
              <th className="px-4 py-3 font-medium">{t("adminCategories.colDescription")}</th>
              <th className="px-4 py-3 font-medium text-end">{t("adminCategories.colActions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {categories.map((category) =>
              editId === category.id ? (
                <tr key={category.id} className="bg-emerald-50/40">
                  <td className="px-4 py-3">
                    <LanguageTabs
                      active={editLang}
                      onSelect={setEditLang}
                      filled={filledFlags(editNames)}
                    />
                    <input
                      type="text"
                      value={editNames[editLang]}
                      onChange={(event) =>
                        setEditNames((prev) => ({
                          ...prev,
                          [editLang]: event.target.value,
                        }))
                      }
                      placeholder={t("adminCategories.nameLangLabel", {
                        lang: t(LANG_LABEL[editLang]),
                      })}
                      className={`mt-2 ${fieldClass}`}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={editDescription}
                      onChange={(event) =>
                        setEditDescription(event.target.value)
                      }
                      className={fieldClass}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        onClick={saveEdit}
                        disabled={savingEdit}
                        className="font-medium text-emerald-700 hover:underline disabled:opacity-50"
                      >
                        {savingEdit ? t("adminCategories.saving") : t("common.save")}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditId(null)}
                        className="font-medium text-gray-500 hover:underline"
                      >
                        {t("common.cancel")}
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={category.id}>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {localizedName(category, i18n.language)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {category.description || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-4">
                      <button
                        type="button"
                        onClick={() => startEdit(category)}
                        className="font-medium text-emerald-700 hover:underline"
                      >
                        {t("common.edit")}
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(category)}
                        className="font-medium text-red-600 hover:underline"
                      >
                        {t("common.delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t("adminCategories.deleteTitle")}
        message={
          deleteTarget
            ? t("adminCategories.deleteMessage", {
                name: localizedName(deleteTarget, i18n.language),
              })
            : ""
        }
        confirmLabel={t("common.delete")}
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => (deleting ? null : setDeleteTarget(null))}
      />
    </div>
  );
}

export default AdminCategories;
