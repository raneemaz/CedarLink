import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import api from "../../services/api";
import BackLink from "../../components/common/BackLink";
import { addressLabel } from "../../utils/addressLabel";

function SavedAddresses() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [addresses, setAddresses] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAddresses = async () => {
    try {
      const response = await api.get("/addresses");

      setAddresses(response.data.addresses || []);
    } catch (error) {
      console.error("Error fetching addresses:", error);

      const message =
        error.response?.data?.message ||
        t("addresses.errLoad");

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAddresses();
  }, [t]);

  const handleSetDefault = async (addressId) => {
    try {
      await api.patch(`/addresses/${addressId}/default`);

      toast.success(t("addresses.toastDefault"));

      // Reload addresses so the new default is reflected immediately.
      fetchAddresses();
    } catch (error) {
      console.error("Error setting default address:", error);

      const message =
        error.response?.data?.message ||
        t("addresses.errDefault");

      toast.error(message);
    }
  };

  const handleDelete = async (addressId) => {
    const confirmed = window.confirm(t("addresses.deleteConfirm"));

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(`/addresses/${addressId}`);

      toast.success(t("addresses.toastDeleted"));

      fetchAddresses();
    } catch (error) {
      console.error("Error deleting address:", error);

      const message =
        error.response?.data?.message ||
        t("addresses.errDelete");

      toast.error(message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface px-6 py-10">
        <div className="mx-auto max-w-4xl">
          <p className="text-text-muted">{t("addresses.loading")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("backLink.settings")}
          </BackLink>

          <h1 className="text-3xl font-bold text-text-primary">
            {t("addresses.title")}
          </h1>

          <p className="mt-2 text-sm text-text-secondary">
            {t("addresses.subtitle")}
          </p>
        </div>

        {/* Add Address */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={() => navigate("/settings/addresses/new")}
            style={{ cursor: "pointer" }}
            className="rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-on-brand transition hover:bg-brand-strong"
          >
            + {t("addresses.addNew")}
          </button>
        </div>

        {/* Empty State */}
        {addresses.length === 0 ? (
          <div className="rounded-xl bg-surface-raised p-10 text-center shadow-sm">
            <div className="mb-4 text-4xl">📍</div>

            <h2 className="text-lg font-semibold text-text-primary">
              {t("addresses.emptyTitle")}
            </h2>

            <p className="mt-2 text-sm text-text-muted">
              {t("addresses.emptyBody")}
            </p>

            <button
              onClick={() => navigate("/settings/addresses/new")}
              className="mt-6 rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-on-brand hover:bg-brand-strong"
            >
              {t("addresses.addFirst")}
            </button>
          </div>
        ) : (
          /* Address List */
          <div className="space-y-5">
            {addresses.map((address) => (
              <div
                key={address.id}
                className="rounded-xl bg-surface-raised p-6 shadow-sm"
              >
                {/* Top Row */}
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg font-semibold text-text-primary">
                        {addressLabel(t, address.label)}
                      </h2>

                      {address.is_default && (
                        <span className="rounded-full bg-brand-tint px-3 py-1 text-xs font-semibold text-brand">
                          {t("common.default")}
                        </span>
                      )}
                    </div>

                    <p className="mt-3 font-medium text-text-emphasis">
                      {address.recipient_name}
                    </p>

                    <p className="mt-1 text-sm text-text-secondary">
                      {address.phone}
                    </p>
                  </div>
                </div>

                {/* Address */}
                <div className="mt-4 border-t border-border-subtle pt-4">
                  <p className="text-sm text-text-body">
                    {address.address_line}
                  </p>

                  <p className="mt-1 text-sm text-text-body">
                    {address.city}
                  </p>

                  {address.delivery_instructions && (
                    <p className="mt-3 text-sm text-text-muted">
                      <span className="font-medium text-text-body">
                        {t("addresses.deliveryInstructionsLabel")}
                      </span>{" "}
                      {address.delivery_instructions}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  {!address.is_default && (
                    <button
                      onClick={() => handleSetDefault(address.id)}
                      className="rounded-lg border border-brand px-4 py-2 text-sm font-medium text-brand hover:bg-brand-subtle"
                    >
                      {t("addresses.setAsDefault")}
                    </button>
                  )}

                  <button
                    onClick={() =>
                      navigate(`/settings/addresses/${address.id}/edit`)
                    }
                    className="cursor-pointer rounded-lg border border-border-strong px-4 py-2 text-sm font-medium text-text-body hover:bg-surface"
                  >
                    {t("addresses.edit")}
                  </button>

                  <button
                    onClick={() => handleDelete(address.id)}
                    className="cursor-pointer rounded-lg border border-danger-border px-4 py-2 text-sm font-medium text-danger hover:bg-danger-subtle"
                  >
                    {t("addresses.delete")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SavedAddresses;