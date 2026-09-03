import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Plus, TicketPercent } from "lucide-react";

import api from "../../services/api";
import CouponForm from "../../components/coupon/CouponForm";
import CouponTable from "../../components/coupon/CouponTable";
import { couponToForm, formToPayload } from "../../utils/couponForm";

/**
 * Admin coupon console.
 *
 * Two sections, deliberately different in kind: the platform-wide coupons
 * an administrator owns and edits, and a read-only sweep of every
 * store-scoped coupon so they can see what is live across the marketplace
 * without reaching into a vendor's console to change it.
 */
function AdminCoupons() {
  const { t } = useTranslation();

  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);

  const [editing, setEditing] = useState(null);   // coupon | "new" | null
  const [form, setForm] = useState(couponToForm(null));
  const [saving, setSaving] = useState(false);

  // See VendorCoupons: the fetch lives in the effect so nothing sets
  // state synchronously in an effect body.
  const [reloadNonce, setReloadNonce] = useState(0);
  const load = () => setReloadNonce((n) => n + 1);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await api.get("/admin/coupons");
        if (!cancelled) setCoupons(response.data.coupons || []);
      } catch (error) {
        console.error("Failed to load coupons:", error);
        if (!cancelled) {
          toast.error(error.response?.data?.message || t("coupon.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [reloadNonce, t]);

  const [platformWide, storeScoped] = useMemo(
    () => [
      coupons.filter((coupon) => coupon.store_id == null),
      coupons.filter((coupon) => coupon.store_id != null),
    ],
    [coupons],
  );

  const startCreate = () => {
    setForm(couponToForm(null));
    setEditing("new");
  };

  const startEdit = (coupon) => {
    setForm(couponToForm(coupon));
    setEditing(coupon);
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = formToPayload(form);

      if (editing === "new") {
        await api.post("/admin/coupons", payload);
        toast.success(t("coupon.toastCreated"));
      } else {
        await api.put(`/admin/coupons/${editing.id}`, payload);
        toast.success(t("coupon.toastUpdated"));
      }

      setEditing(null);
      load();
    } catch (error) {
      toast.error(error.response?.data?.message || t("coupon.errSave"));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (coupon) => {
    try {
      const response = await api.delete(`/admin/coupons/${coupon.id}`);
      toast.success(response.data?.message || t("coupon.toastDeleted"));
      load();
    } catch (error) {
      toast.error(error.response?.data?.message || t("coupon.errDelete"));
    }
  };

  if (loading) {
    return (
      <p className="py-20 text-center text-slate-500">{t("common.loading")}</p>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t("coupon.adminTitle")}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {t("coupon.adminSubtitle")}
          </p>
        </div>

        {!editing && (
          <button
            type="button"
            onClick={startCreate}
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800"
          >
            <Plus size={16} />
            {t("coupon.newPlatformCoupon")}
          </button>
        )}
      </div>

      {editing && (
        <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="mb-1 text-lg font-semibold text-slate-900">
            {editing === "new"
              ? t("coupon.form.createPlatformTitle")
              : t("coupon.form.editTitle", { code: editing.code })}
          </h2>
          <p className="mb-5 text-sm text-slate-500">
            {t("coupon.form.platformScopeNote")}
          </p>

          <CouponForm
            form={form}
            setForm={setForm}
            onSubmit={save}
            onCancel={() => setEditing(null)}
            saving={saving}
            editing={editing !== "new"}
          />
        </div>
      )}

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t("coupon.platformSection")}
        </h2>

        {platformWide.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
            <TicketPercent size={28} className="mx-auto text-slate-400" />
            <p className="mt-3 font-medium text-slate-700">
              {t("coupon.emptyPlatformTitle")}
            </p>
            <p className="mt-1 text-sm text-slate-500">
              {t("coupon.emptyPlatformBody")}
            </p>
          </div>
        ) : (
          <CouponTable
            coupons={platformWide}
            onEdit={startEdit}
            onDelete={remove}
          />
        )}
      </section>

      <section>
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t("coupon.storeSection")}
        </h2>
        <p className="mb-3 text-sm text-slate-500">
          {t("coupon.storeSectionNote")}
        </p>

        {storeScoped.length === 0 ? (
          <p className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
            {t("coupon.emptyStoreScoped")}
          </p>
        ) : (
          // No onEdit / onDelete: an administrator can see what is live
          // without being handed the vendor's controls.
          <CouponTable coupons={storeScoped} showStore />
        )}
      </section>
    </div>
  );
}

export default AdminCoupons;
