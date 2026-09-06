import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import BackLink from "../../components/common/BackLink";
import LocationPicker from "../../components/map/LocationPicker";
import api from "../../services/api";

function AddAddress() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    label: "",
    recipient_name: "",
    phone: "",
    address_line: "",
    city: "",
    delivery_instructions: "",
    is_default: false,
    latitude: null,
    longitude: null,
  });

  const [saving, setSaving] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setSaving(true);

    try {
      await api.post("/addresses", formData);

      toast.success(t("addresses.toastAdded"));

      navigate("/settings/addresses");
    } catch (error) {
      console.error("Error adding address:", error);

      const message =
        error.response?.data?.message ||
        t("addresses.errAdd");

      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper px-6 py-10">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink
            onClick={() => navigate("/settings/addresses")}
            className="mb-4"
          >
            {t("backLink.savedAddresses")}
          </BackLink>

          <h1 className="text-title font-bold text-ink">
            {t("addresses.formAddTitle")}
          </h1>

          <p className="mt-2 text-small text-ink-secondary">
            {t("addresses.formAddSubtitle")}
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="rounded-card bg-paper-raised p-6 shadow-card"
        >
          <div className="space-y-6">
            {/* Address Label */}
            <div>
              <label
                htmlFor="label"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("addresses.labelField")}
              </label>

              <select
                id="label"
                name="label"
                value={formData.label}
                onChange={handleChange}
                required
                className="w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              >
                <option value="">{t("addresses.selectLabel")}</option>
                <option value="Home">{t("addresses.labelHome")}</option>
                <option value="Work">{t("addresses.labelWork")}</option>
                <option value="Other">{t("addresses.labelOther")}</option>
              </select>
            </div>

            {/* Recipient Name */}
            <div>
              <label
                htmlFor="recipient_name"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("addresses.recipientName")}
              </label>

              <input
                id="recipient_name"
                name="recipient_name"
                type="text"
                value={formData.recipient_name}
                onChange={handleChange}
                placeholder={t("addresses.recipientNamePlaceholder")}
                required
                className="w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              />
            </div>

            {/* Phone */}
            <div>
              <label
                htmlFor="phone"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("addresses.phone")}
              </label>

              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                placeholder={t("addresses.phonePlaceholder")}
                required
                className="w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              />
            </div>

            {/* Address */}
            <div>
              <label
                htmlFor="address_line"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("addresses.addressField")}
              </label>

              <input
                id="address_line"
                name="address_line"
                type="text"
                value={formData.address_line}
                onChange={handleChange}
                placeholder={t("addresses.addressPlaceholder")}
                required
                className="w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              />
            </div>

            {/* City */}
            <div>
              <label
                htmlFor="city"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("addresses.city")}
              </label>

              <input
                id="city"
                name="city"
                type="text"
                value={formData.city}
                onChange={handleChange}
                placeholder={t("addresses.cityPlaceholder")}
                required
                className="w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              />
            </div>

            {/* Delivery Instructions */}
            <div>
              <label
                htmlFor="delivery_instructions"
                className="mb-2 block text-small font-medium text-ink-body"
              >
                {t("addresses.deliveryInstructions")}
              </label>

              <textarea
                id="delivery_instructions"
                name="delivery_instructions"
                value={formData.delivery_instructions}
                onChange={handleChange}
                placeholder={t("addresses.deliveryInstructionsPlaceholder")}
                rows="3"
                className="w-full resize-none rounded-control border border-line-strong px-4 py-3 text-small outline-none focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring"
              />
            </div>

            {/* Map pin — optional. An address with no pin saves and
                behaves exactly as it did before this existed; it just
                cannot be used as a search centre on /stores. */}
            <div>
              <span className="mb-2 block text-small font-medium text-ink-body">
                {t("addresses.pinField")}
              </span>

              <p className="mb-3 text-micro text-ink-muted">
                {t("addresses.pinHelp")}
              </p>

              <LocationPicker
                latitude={formData.latitude}
                longitude={formData.longitude}
                onChange={(lat, lng) =>
                  setFormData((prev) => ({
                    ...prev,
                    latitude: lat,
                    longitude: lng,
                  }))
                }
                onClear={() =>
                  setFormData((prev) => ({
                    ...prev,
                    latitude: null,
                    longitude: null,
                  }))
                }
                disabled={saving}
              />
            </div>

            {/* Default Address */}
            <div className="flex items-start gap-3 rounded-control bg-cedar-subtle p-4">
              <input
                id="is_default"
                name="is_default"
                type="checkbox"
                checked={formData.is_default}
                onChange={handleChange}
                className="mt-1 h-4 w-4 rounded border-line-strong text-cedar focus:ring-cedar-ring"
              />

              <div>
                <label
                  htmlFor="is_default"
                  className="cursor-pointer text-small font-medium text-ink-emphasis"
                >
                  {t("addresses.setDefaultAddress")}
                </label>

                <p className="mt-1 text-micro text-ink-secondary">
                  {t("addresses.setDefaultAddressDesc")}
                </p>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="mt-8 flex justify-end gap-3 border-t border-line-subtle pt-6">
            <button
              type="button"
              onClick={() => navigate("/settings/addresses")}
              disabled={saving}
              className="cursor-pointer rounded-control border border-line-strong px-5 py-3 text-small font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t("addresses.cancel")}
            </button>

            <button
              type="submit"
              disabled={saving}
              className="cursor-pointer rounded-control bg-cedar px-5 py-3 text-small font-semibold text-on-cedar hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? t("common.working") : t("addresses.saveAdd")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddAddress;