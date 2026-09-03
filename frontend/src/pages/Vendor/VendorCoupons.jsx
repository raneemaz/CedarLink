import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Plus, TicketPercent } from "lucide-react";

import api from "../../services/api";
import CouponForm from "../../components/coupon/CouponForm";
import CouponTable from "../../components/coupon/CouponTable";
import { couponToForm, formToPayload } from "../../utils/couponForm";

/**
 * Vendor coupon console — store-scoped only.
 *
 * Every request goes to /api/stores/{id}/coupons, which takes the scope
 * from the URL. There is deliberately no platform-wide option anywhere in
 * this interface: a vendor cannot create one, and offering the control
 * would be offering something the API refuses.
 */
function VendorCoupons() {
  const { t } = useTranslation();

  const [store, setStore] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);

  const [editing, setEditing] = useState(null);   // coupon | "new" | null
  const [form, setForm] = useState(couponToForm(null));
  const [saving, setSaving] = useState(false);

  // Bumped to re-read after a save or delete. The fetch lives inside the
  // effect and starts with an await, so nothing sets state synchronously
  // in an effect body.
  const [reloadNonce, setReloadNonce] = useState(0);
  const load = () => setReloadNonce((n) => n + 1);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const storeResponse = await api.get("/vendor/store");
        const own = storeResponse.data.store;
        if (cancelled) return;
        setStore(own);

        if (!own) return;

        const response = await api.get(`/stores/${own.id}/coupons`);
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
        await api.post(`/stores/${store.id}/coupons`, payload);
        toast.success(t("coupon.toastCreated"));
      } else {
        await api.put(`/stores/${store.id}/coupons/${editing.id}`, payload);
        toast.success(t("coupon.toastUpdated"));
      }

      setEditing(null);
      load();
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("coupon.errSave"),
      );
    } finally {
      setSaving(false);
    }
  };

  const remove = async (coupon) => {
    try {
      const response = await api.delete(
        `/stores/${store.id}/coupons/${coupon.id}`,
      );
      // A redeemed coupon deactivates instead of being destroyed, so the
      // order history keeps pointing at something (ADR 0021). Say which
      // happened rather than claiming a delete either way.
      toast.success(response.data?.message || t("coupon.toastDeleted"));
      load();
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("coupon.errDelete"),
      );
    }
  };

  if (loading) {
    return (
      <p className="py-20 text-center text-slate-500">{t("common.loading")}</p>
    );
  }

  if (!store) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
        <TicketPercent size={28} className="mx-auto text-slate-400" />
        <p className="mt-3 text-slate-600">{t("coupon.noStore")}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {t("coupon.vendorTitle")}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {t("coupon.vendorSubtitle", { store: store.name })}
          </p>
        </div>

        {!editing && (
          <button
            type="button"
            onClick={startCreate}
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800"
          >
            <Plus size={16} />
            {t("coupon.newCoupon")}
          </button>
        )}
      </div>

      {editing && (
        <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="mb-5 text-lg font-semibold text-slate-900">
            {editing === "new"
              ? t("coupon.form.createTitle")
              : t("coupon.form.editTitle", { code: editing.code })}
          </h2>

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

      {coupons.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
          <TicketPercent size={28} className="mx-auto text-slate-400" />
          <p className="mt-3 font-medium text-slate-700">
            {t("coupon.emptyTitle")}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {t("coupon.emptyBody")}
          </p>
        </div>
      ) : (
        <CouponTable
          coupons={coupons}
          onEdit={startEdit}
          onDelete={remove}
        />
      )}
    </div>
  );
}

export default VendorCoupons;
