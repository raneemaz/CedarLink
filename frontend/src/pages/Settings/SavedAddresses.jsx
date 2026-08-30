import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import api from "../../services/api";
import BackLink from "../../components/common/BackLink";

function SavedAddresses() {
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
        "Failed to load your saved addresses.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAddresses();
  }, []);

  const handleSetDefault = async (addressId) => {
    try {
      await api.patch(`/addresses/${addressId}/default`);

      toast.success("Default address updated.");

      // Reload addresses so the new default is reflected immediately.
      fetchAddresses();
    } catch (error) {
      console.error("Error setting default address:", error);

      const message =
        error.response?.data?.message ||
        "Failed to update default address.";

      toast.error(message);
    }
  };

  const handleDelete = async (addressId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this address?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(`/addresses/${addressId}`);

      toast.success("Address deleted successfully.");

      fetchAddresses();
    } catch (error) {
      console.error("Error deleting address:", error);

      const message =
        error.response?.data?.message ||
        "Failed to delete address.";

      toast.error(message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-10">
        <div className="mx-auto max-w-4xl">
          <p className="text-gray-500">Loading your saved addresses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            Back to Settings
          </BackLink>

          <h1 className="text-3xl font-bold text-gray-900">
            Saved Addresses
          </h1>

          <p className="mt-2 text-sm text-gray-600">
            Manage your delivery and billing addresses.
          </p>
        </div>

        {/* Add Address */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={() => navigate("/settings/addresses/new")}
            style={{ cursor: "pointer" }}
            className="rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-green-800"
          >
            + Add New Address
          </button>
        </div>

        {/* Empty State */}
        {addresses.length === 0 ? (
          <div className="rounded-xl bg-white p-10 text-center shadow-sm">
            <div className="mb-4 text-4xl">📍</div>

            <h2 className="text-lg font-semibold text-gray-900">
              No saved addresses
            </h2>

            <p className="mt-2 text-sm text-gray-500">
              Add an address to make checkout faster and easier.
            </p>

            <button
              onClick={() => navigate("/settings/addresses/new")}
              className="mt-6 rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white hover:bg-green-800"
            >
              Add Your First Address
            </button>
          </div>
        ) : (
          /* Address List */
          <div className="space-y-5">
            {addresses.map((address) => (
              <div
                key={address.id}
                className="rounded-xl bg-white p-6 shadow-sm"
              >
                {/* Top Row */}
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg font-semibold text-gray-900">
                        {address.label}
                      </h2>

                      {address.is_default && (
                        <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                          Default
                        </span>
                      )}
                    </div>

                    <p className="mt-3 font-medium text-gray-800">
                      {address.recipient_name}
                    </p>

                    <p className="mt-1 text-sm text-gray-600">
                      {address.phone}
                    </p>
                  </div>
                </div>

                {/* Address */}
                <div className="mt-4 border-t border-gray-100 pt-4">
                  <p className="text-sm text-gray-700">
                    {address.address_line}
                  </p>

                  <p className="mt-1 text-sm text-gray-700">
                    {address.city}
                  </p>

                  {address.delivery_instructions && (
                    <p className="mt-3 text-sm text-gray-500">
                      <span className="font-medium text-gray-700">
                        Delivery instructions:
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
                      className="rounded-lg border border-green-700 px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-50"
                    >
                      Set as Default
                    </button>
                  )}

                  <button
                    onClick={() =>
                      navigate(`/settings/addresses/${address.id}/edit`)
                    }
                    className="cursor-pointer rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Edit
                  </button>

                  <button
                    onClick={() => handleDelete(address.id)}
                    className="cursor-pointer rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    Delete
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