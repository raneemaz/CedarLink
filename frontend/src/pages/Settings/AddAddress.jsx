import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import BackLink from "../../components/common/BackLink";
import api from "../../services/api";

function AddAddress() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    label: "",
    recipient_name: "",
    phone: "",
    address_line: "",
    city: "",
    delivery_instructions: "",
    is_default: false,
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

      toast.success("Address added successfully.");

      navigate("/settings/addresses");
    } catch (error) {
      console.error("Error adding address:", error);

      const message =
        error.response?.data?.message ||
        "Failed to add address.";

      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink
            onClick={() => navigate("/settings/addresses")}
            className="mb-4"
          >
            Back to Saved Addresses
          </BackLink>

          <h1 className="text-3xl font-bold text-gray-900">
            Add New Address
          </h1>

          <p className="mt-2 text-sm text-gray-600">
            Add a delivery address to your CedarLink account.
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="rounded-xl bg-white p-6 shadow-sm"
        >
          <div className="space-y-6">
            {/* Address Label */}
            <div>
              <label
                htmlFor="label"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Address Label
              </label>

              <select
                id="label"
                name="label"
                value={formData.label}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              >
                <option value="">Select a label</option>
                <option value="Home">Home</option>
                <option value="Work">Work</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Recipient Name */}
            <div>
              <label
                htmlFor="recipient_name"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Recipient Name
              </label>

              <input
                id="recipient_name"
                name="recipient_name"
                type="text"
                value={formData.recipient_name}
                onChange={handleChange}
                placeholder="Enter recipient name"
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>

            {/* Phone */}
            <div>
              <label
                htmlFor="phone"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Phone
              </label>

              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                placeholder="Enter phone number"
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>

            {/* Address */}
            <div>
              <label
                htmlFor="address_line"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Address
              </label>

              <input
                id="address_line"
                name="address_line"
                type="text"
                value={formData.address_line}
                onChange={handleChange}
                placeholder="Street, building, apartment..."
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>

            {/* City */}
            <div>
              <label
                htmlFor="city"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                City
              </label>

              <input
                id="city"
                name="city"
                type="text"
                value={formData.city}
                onChange={handleChange}
                placeholder="Enter city"
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>

            {/* Delivery Instructions */}
            <div>
              <label
                htmlFor="delivery_instructions"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Delivery Instructions
              </label>

              <textarea
                id="delivery_instructions"
                name="delivery_instructions"
                value={formData.delivery_instructions}
                onChange={handleChange}
                placeholder="Example: Leave at the door"
                rows="3"
                className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600"
              />
            </div>

            {/* Default Address */}
            <div className="flex items-start gap-3 rounded-lg bg-green-50 p-4">
              <input
                id="is_default"
                name="is_default"
                type="checkbox"
                checked={formData.is_default}
                onChange={handleChange}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-green-700 focus:ring-green-600"
              />

              <div>
                <label
                  htmlFor="is_default"
                  className="cursor-pointer text-sm font-medium text-gray-800"
                >
                  Set as default address
                </label>

                <p className="mt-1 text-xs text-gray-600">
                  Your default address will be selected automatically during
                  checkout.
                </p>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="mt-8 flex justify-end gap-3 border-t border-gray-100 pt-6">
            <button
              type="button"
              onClick={() => navigate("/settings/addresses")}
              disabled={saving}
              className="cursor-pointer rounded-lg border border-gray-300 px-5 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={saving}
              className="cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Address"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddAddress;