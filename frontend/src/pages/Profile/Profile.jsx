import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import api from "../../services/api";

function Profile() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const getStoredUser = () => {
    const savedUser = localStorage.getItem("user");

    if (!savedUser || savedUser === "undefined") {
      return null;
    }

    try {
      return JSON.parse(savedUser);
    } catch {
      localStorage.removeItem("user");
      return null;
    }
  };

  useEffect(() => {
    const storedUser = getStoredUser();

    if (!storedUser?.id) {
      setError(t("profile.errNoAccount"));
      setLoading(false);
      return;
    }

    const fetchProfile = async () => {
      try {
        const response = await api.get(`/users/${storedUser.id}`);

        const user = response.data?.user;

        setProfile({
          first_name: user?.first_name || "",
          last_name: user?.last_name || "",
          email: user?.email || "",
          phone: user?.phone || "",
        });
      } catch (err) {
        console.error("Failed to load profile:", err);

        setError(
          err.response?.data?.message ||
            t("profile.errLoad")
        );
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [t]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setProfile((previousProfile) => ({
      ...previousProfile,
      [name]: value,
    }));

    setError("");
    setSuccess("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const storedUser = getStoredUser();

      if (!storedUser?.id) {
        setError(t("profile.errNoAccount"));
        return;
      }

      const response = await api.put(`/users/${storedUser.id}`, {
        first_name: profile.first_name,
        last_name: profile.last_name,
        email: profile.email,
        phone: profile.phone,
      });

      const updatedUser = response.data?.user;

      if (!updatedUser) {
        throw new Error("Updated user information was not returned.");
      }

      setProfile({
        first_name: updatedUser.first_name || "",
        last_name: updatedUser.last_name || "",
        email: updatedUser.email || "",
        phone: updatedUser.phone || "",
      });

      localStorage.setItem(
        "user",
        JSON.stringify({
          ...storedUser,
          id: updatedUser.id,
          first_name: updatedUser.first_name,
          last_name: updatedUser.last_name,
          email: updatedUser.email,
          phone: updatedUser.phone,
          role: updatedUser.role,
        })
      );

      setSuccess(
        response.data?.message ||
          t("profile.toastUpdated")
      );
    } catch (err) {
      console.error("Failed to update profile:", err);

      setError(
        err.response?.data?.message ||
          err.message ||
          t("profile.errUpdate")
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-gray-600">{t("profile.loading")}</p>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-2xl bg-white p-8 shadow-md">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">
              {t("profile.title")}
            </h1>

            <p className="mt-2 text-gray-600">
              {t("profile.subtitle")}
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-6 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label
                  htmlFor="first_name"
                  className="mb-2 block text-sm font-medium text-gray-700"
                >
                  {t("profile.firstName")}
                </label>

                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={profile.first_name}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                />
              </div>

              <div>
                <label
                  htmlFor="last_name"
                  className="mb-2 block text-sm font-medium text-gray-700"
                >
                  {t("profile.lastName")}
                </label>

                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={profile.last_name}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                {t("profile.email")}
              </label>

              <input
                id="email"
                name="email"
                type="email"
                value={profile.email}
                onChange={handleChange}
                required
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
              />
            </div>

            <div>
              <label
                htmlFor="phone"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                {t("profile.phone")}
              </label>

              <input
                id="phone"
                name="phone"
                type="tel"
                value={profile.phone}
                onChange={handleChange}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
              />
            </div>

            <div className="flex justify-end pt-4">
              <button
                type="submit"
                disabled={saving}
                className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? t("profile.saving") : t("profile.save")}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Profile;