import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import Toggle from "../../components/common/Toggle/Toggle";
import { lebanonLocations } from "../../data/lebanonLocations";

// Flattened, de-duplicated list of Lebanese cities. The store location must
// come from the same vocabulary as customer addresses — delivery-fee logic
// matches a customer's delivery_city against store.location by string.
const CITY_OPTIONS = Array.from(
  new Set(
    lebanonLocations.flatMap((governorate) =>
      governorate.districts.flatMap((district) => district.cities),
    ),
  ),
).sort((a, b) => a.localeCompare(b));

const fieldClass =
  "w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none " +
  "focus:border-green-600 focus:ring-1 focus:ring-green-600";

const EMPTY_DETAILS = {
  name: "",
  description: "",
  location: "",
  contact_info: "",
};

const EMPTY_DELIVERY = {
  inside_city_delivery_fee: "",
  outside_city_delivery_fee: "",
  delivery_available: true,
};

function detailsFromStore(store) {
  return {
    name: store.name ?? "",
    description: store.description ?? "",
    location: store.location ?? "",
    contact_info: store.contact_info ?? "",
  };
}

function deliveryFromStore(store) {
  return {
    inside_city_delivery_fee: String(store.inside_city_delivery_fee ?? ""),
    outside_city_delivery_fee: String(store.outside_city_delivery_fee ?? ""),
    delivery_available: Boolean(store.delivery_available),
  };
}

function apiMessage(error, fallback) {
  return error.response?.data?.message || fallback;
}

function Section({ title, description, children, onSubmit, footer }) {
  const Wrapper = onSubmit ? "form" : "section";

  return (
    <Wrapper
      onSubmit={onSubmit}
      className="overflow-hidden rounded-2xl bg-white shadow-sm"
    >
      <div className="border-b border-gray-100 px-6 py-5">
        <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
        {description && (
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        )}
      </div>

      <div className="px-6 py-6">{children}</div>

      {footer && (
        <div className="flex justify-end border-t border-gray-100 px-6 py-4">
          {footer}
        </div>
      )}
    </Wrapper>
  );
}

function TextField({ label, name, value, onChange, hint, ...rest }) {
  return (
    <div>
      <label
        htmlFor={name}
        className="mb-2 block text-sm font-medium text-gray-700"
      >
        {label}
      </label>

      <input
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        className={fieldClass}
        {...rest}
      />

      {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

function StoreDetailFields({ values, onChange }) {
  return (
    <div className="space-y-6">
      <TextField
        label="Store name"
        name="name"
        type="text"
        placeholder="e.g. Hamra Grocery"
        value={values.name}
        onChange={onChange}
        required
      />

      <div>
        <label
          htmlFor="description"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          Description
        </label>

        <textarea
          id="description"
          name="description"
          rows="3"
          placeholder="What does your store sell?"
          value={values.description}
          onChange={onChange}
          required
          className={`resize-none ${fieldClass}`}
        />
      </div>

      <div>
        <label
          htmlFor="location"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          Location (city)
        </label>

        <select
          id="location"
          name="location"
          value={values.location}
          onChange={onChange}
          required
          className={fieldClass}
        >
          <option value="">Select a city</option>
          {CITY_OPTIONS.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </select>

        <p className="mt-1 text-xs text-gray-500">
          Delivery fees are applied by matching a customer&apos;s city to
          this value.
        </p>
      </div>

      <TextField
        label="Contact info"
        name="contact_info"
        type="text"
        placeholder="Phone or email customers can reach you at"
        value={values.contact_info}
        onChange={onChange}
        required
      />
    </div>
  );
}

function VendorStore() {
  const [loading, setLoading] = useState(true);
  const [store, setStore] = useState(null);

  const [details, setDetails] = useState(EMPTY_DETAILS);
  const [delivery, setDelivery] = useState(EMPTY_DELIVERY);

  const [creating, setCreating] = useState(false);
  const [savingDetails, setSavingDetails] = useState(false);
  const [savingDelivery, setSavingDelivery] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);

  const applyStore = (nextStore) => {
    setStore(nextStore);
    setDetails(detailsFromStore(nextStore));
    setDelivery(deliveryFromStore(nextStore));
    // Let the console shell refresh its approval / removed banner.
    window.dispatchEvent(new Event("vendorStoreChanged"));
  };

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const response = await api.get("/vendor/store");
        if (!cancelled) applyStore(response.data.store);
      } catch (error) {
        if (cancelled) return;

        if (error.response?.status === 404) {
          setStore(null);
        } else {
          console.error("Failed to load store:", error);
          toast.error(apiMessage(error, "Unable to load your store."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleDetailChange = (event) => {
    const { name, value } = event.target;
    setDetails((prev) => ({ ...prev, [name]: value }));
  };

  const handleDeliveryChange = (event) => {
    const { name, value } = event.target;
    setDelivery((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    setCreating(true);

    try {
      const response = await api.post("/stores", {
        ...details,
        inside_city_delivery_fee: delivery.inside_city_delivery_fee,
        outside_city_delivery_fee: delivery.outside_city_delivery_fee,
      });

      applyStore(response.data.store);
      toast.success("Store created.");
    } catch (error) {
      console.error("Failed to create store:", error);
      toast.error(apiMessage(error, "Unable to create your store."));
    } finally {
      setCreating(false);
    }
  };

  const handleSaveDetails = async (event) => {
    event.preventDefault();
    setSavingDetails(true);

    try {
      const response = await api.put(`/stores/${store.id}`, details);
      applyStore(response.data.store);
      toast.success("Store details saved.");
    } catch (error) {
      console.error("Failed to save store details:", error);
      toast.error(apiMessage(error, "Unable to save store details."));
    } finally {
      setSavingDetails(false);
    }
  };

  const handleSaveDelivery = async (event) => {
    event.preventDefault();
    setSavingDelivery(true);

    try {
      const response = await api.put(`/stores/${store.id}`, {
        inside_city_delivery_fee: delivery.inside_city_delivery_fee,
        outside_city_delivery_fee: delivery.outside_city_delivery_fee,
        delivery_available: delivery.delivery_available,
      });

      applyStore(response.data.store);
      toast.success("Delivery settings saved.");
    } catch (error) {
      console.error("Failed to save delivery settings:", error);
      toast.error(apiMessage(error, "Unable to save delivery settings."));
    } finally {
      setSavingDelivery(false);
    }
  };

  const handleToggleStatus = async () => {
    setSavingStatus(true);

    try {
      const response = await api.patch(`/stores/${store.id}/status`, {
        is_active: !store.is_active,
      });

      applyStore(response.data.store);
      toast.success(
        response.data.store.is_active
          ? "Store activated."
          : "Store deactivated.",
      );
    } catch (error) {
      console.error("Failed to update store status:", error);
      toast.error(apiMessage(error, "Unable to update store status."));
    } finally {
      setSavingStatus(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading your store...</p>;
  }

  // ---- No store yet: creation form ----------------------------------------
  if (!store) {
    return (
      <div>
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Store</h1>
          <p className="mt-2 text-gray-600">
            Set up your store to start selling on CedarLink.
          </p>
        </div>

        <Section
          title="Create your store"
          description="All fields are required."
          onSubmit={handleCreate}
          footer={
            <Button type="submit" disabled={creating}>
              {creating ? "Creating..." : "Create store"}
            </Button>
          }
        >
          <div className="space-y-6">
            <StoreDetailFields
              values={details}
              onChange={handleDetailChange}
            />

            <div className="grid gap-6 sm:grid-cols-2">
              <TextField
                label="Inside-city delivery fee (USD)"
                name="inside_city_delivery_fee"
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={delivery.inside_city_delivery_fee}
                onChange={handleDeliveryChange}
                required
              />

              <TextField
                label="Outside-city delivery fee (USD)"
                name="outside_city_delivery_fee"
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={delivery.outside_city_delivery_fee}
                onChange={handleDeliveryChange}
                required
              />
            </div>
          </div>
        </Section>
      </div>
    );
  }

  // ---- Existing store: edit + delivery + status ---------------------------
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Store</h1>
        <p className="mt-2 text-gray-600">
          {store.name}
          {!store.is_active && (
            <span className="ms-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
              Deactivated
            </span>
          )}
        </p>
      </div>

      <div className="space-y-6">
        <Section
          title="Store details"
          onSubmit={handleSaveDetails}
          footer={
            <Button type="submit" disabled={savingDetails}>
              {savingDetails ? "Saving..." : "Save changes"}
            </Button>
          }
        >
          <StoreDetailFields values={details} onChange={handleDetailChange} />
        </Section>

        <Section
          title="Delivery"
          description="Fees are charged per order, based on the customer's city."
          onSubmit={handleSaveDelivery}
          footer={
            <Button type="submit" disabled={savingDelivery}>
              {savingDelivery ? "Saving..." : "Save delivery settings"}
            </Button>
          }
        >
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <TextField
                label="Inside-city delivery fee (USD)"
                name="inside_city_delivery_fee"
                type="number"
                min="0"
                step="0.01"
                value={delivery.inside_city_delivery_fee}
                onChange={handleDeliveryChange}
                required
              />

              <TextField
                label="Outside-city delivery fee (USD)"
                name="outside_city_delivery_fee"
                type="number"
                min="0"
                step="0.01"
                value={delivery.outside_city_delivery_fee}
                onChange={handleDeliveryChange}
                required
              />
            </div>

            <div className="border-t border-gray-100">
              <Toggle
                checked={delivery.delivery_available}
                onChange={(next) =>
                  setDelivery((prev) => ({
                    ...prev,
                    delivery_available: next,
                  }))
                }
                label="Accepting delivery orders"
                description="Turn off to stop taking new orders without deactivating the store."
              />
            </div>
          </div>
        </Section>

        <Section
          title="Store status"
          description="A deactivated store is hidden from customers and cannot take orders."
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium text-gray-900">
                {store.is_active ? "Active" : "Deactivated"}
              </p>
              <p className="mt-1 text-sm text-gray-500">
                {store.is_active
                  ? "Your store is visible to customers."
                  : "Your store is currently hidden from customers."}
              </p>
            </div>

            <Button
              variant={store.is_active ? "danger" : "primary"}
              onClick={handleToggleStatus}
              disabled={savingStatus}
            >
              {savingStatus
                ? "Saving..."
                : store.is_active
                ? "Deactivate store"
                : "Activate store"}
            </Button>
          </div>
        </Section>
      </div>
    </div>
  );
}

export default VendorStore;
