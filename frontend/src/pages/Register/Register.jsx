import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import api from "../../services/api";

function Register() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [role, setRole] = useState("customer");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verificationMethod, setVerificationMethod] =
    useState("email");

  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (
      !firstName ||
      !lastName ||
      !email ||
      !phone ||
      !password ||
      !confirmPassword ||
      !verificationMethod
    ) {
      toast.error(t("register.errFillAll"));
      return;
    }

    if (password !== confirmPassword) {
      toast.error(t("register.errPasswordsMatch"));
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/auth/register", {
        first_name: firstName,
        last_name: lastName,
        email,
        phone,
        password,
        // The API's own allow-list is the real guard (customer | vendor only).
        role: role === "vendor" ? "vendor" : "customer",
        verification_method: verificationMethod,
      });

      if (!response.data?.challenge_token) {
        toast.error(t("register.errCantStart"));
        return;
      }

      sessionStorage.setItem(
        "registration_verification",
        JSON.stringify({
          challenge_token:
            response.data.challenge_token,
          method: response.data.method,
          email,
          phone,
          expires_at: response.data.expires_at,
        })
      );

      toast.success(
        response.data?.message || t("register.fallbackCodeSent"),
      );

      navigate("/register/verify");
    } catch (error) {
      console.error("Registration failed:", error);

      toast.error(
        error.response?.data?.message ||
          error.response?.data?.error ||
          t("register.errCantStart"),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-4xl font-bold text-center text-green-700">
          CedarLink
        </h1>

        <p className="text-center text-gray-500 mt-2 mb-8">
          {t("register.createAccount")}
        </p>

        {/* Account type — the first decision a new user makes */}
        <div className="mb-6">
          <p className="mb-3 block text-sm font-medium text-gray-700">
            {t("register.whatBrings")}
          </p>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setRole("customer")}
              className={`rounded-xl border-2 p-4 text-start transition ${
                role === "customer"
                  ? "border-green-600 bg-green-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <span className="block font-semibold text-gray-900">
                {t("register.iWantToShop")}
              </span>
              <span className="mt-1 block text-xs text-gray-500">
                {t("register.iWantToShopDesc")}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setRole("vendor")}
              className={`rounded-xl border-2 p-4 text-start transition ${
                role === "vendor"
                  ? "border-green-600 bg-green-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <span className="block font-semibold text-gray-900">
                {t("register.iWantToSell")}
              </span>
              <span className="mt-1 block text-xs text-gray-500">
                {t("register.iWantToSellDesc")}
              </span>
            </button>
          </div>

          {role === "vendor" && (
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {t("register.vendorApprovalNote")}
            </p>
          )}
        </div>

        <Input
          label={t("register.firstName")}
          name="first_name"
          autoComplete="given-name"
          type="text"
          placeholder={t("register.enterFirstName")}
          value={firstName}
          onChange={(e) =>
            setFirstName(e.target.value)
          }
        />

        <Input
          label={t("register.lastName")}
          name="last_name"
          autoComplete="family-name"
          type="text"
          placeholder={t("register.enterLastName")}
          value={lastName}
          onChange={(e) =>
            setLastName(e.target.value)
          }
        />

        <Input
          label={t("auth.email")}
          name="email"
          autoComplete="email"
          type="email"
          placeholder={t("auth.enterEmail")}
          value={email}
          onChange={(e) =>
            setEmail(e.target.value)
          }
        />

        <Input
          label={t("register.phone")}
          name="phone"
          autoComplete="tel"
          type="tel"
          placeholder={t("register.enterPhone")}
          value={phone}
          onChange={(e) =>
            setPhone(e.target.value)
          }
        />

        <div className="mb-5">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            {t("register.verificationMethod")}
          </label>

          <select
            value={verificationMethod}
            onChange={(e) =>
              setVerificationMethod(e.target.value)
            }
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
          >
            <option value="email">{t("auth.method_email")}</option>
            <option value="sms">{t("auth.method_sms")}</option>
            <option value="whatsapp">{t("auth.method_whatsapp")}</option>
          </select>
        </div>

        <Input
          label={t("auth.password")}
          name="password"
          type="password"
          autoComplete="new-password"
          placeholder={t("register.createPassword")}
          value={password}
          onChange={(e) =>
            setPassword(e.target.value)
          }
        />

        <Input
          label={t("register.confirmPassword")}
          name="confirm_password"
          autoComplete="new-password"
          type="password"
          placeholder={t("register.confirmPasswordPlaceholder")}
          value={confirmPassword}
          onChange={(e) =>
            setConfirmPassword(e.target.value)
          }
        />

        <Button
          className="w-full cursor-pointer"
          onClick={handleRegister}
          disabled={loading}
        >
          {loading ? t("register.creating") : t("register.submit")}
        </Button>

        <p className="text-center text-gray-600 mt-6">
          {t("register.alreadyHaveAccount")}{" "}
          <Link
            to="/login"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            {t("register.login")}
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default Register;