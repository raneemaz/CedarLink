import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import Button from "../../components/common/Button/Button";
import Input from "../../components/common/Input/Input";
import Card from "../../components/common/Card/Card";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const METHOD_KEYS = {
  email: "auth.method_email",
  sms: "auth.method_sms",
  whatsapp: "auth.method_whatsapp",
};

function RegisterVerify() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { login } = useAuth();

  const verificationData = JSON.parse(
    sessionStorage.getItem("registration_verification") || "null"
  );

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const handleVerify = async () => {
    if (!verificationData?.challenge_token) {
      toast.error(t("registerVerify.errSessionNotFound"));
      navigate("/register");
      return;
    }

    if (!code.trim()) {
      toast.error(t("registerVerify.errEnterCode"));
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/auth/register/verify", {
        challenge_token: verificationData.challenge_token,
        code: code.trim(),
      });

      const { access_token, refresh_token, user } = response.data;

      login(user, access_token, refresh_token);

      sessionStorage.removeItem("registration_verification");

      toast.success(t("registerVerify.toastVerified"));

      // A new vendor goes straight to the store-creation form.
      navigate(user?.role === "vendor" ? "/vendor/store" : "/");
    } catch (error) {
      console.error("Registration verification failed:", error);

      const message =
        error.response?.data?.message ||
        t("login.fallbackVerifyFailed");

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!verificationData?.challenge_token) {
      toast.error(t("registerVerify.errSessionNotFound"));
      navigate("/register");
      return;
    }

    try {
      setResending(true);

      const response = await api.post("/auth/register/resend", {
        challenge_token: verificationData.challenge_token,
      });

      const updatedVerificationData = {
        ...verificationData,
        expires_at: response.data.expires_at,
      };

      sessionStorage.setItem(
        "registration_verification",
        JSON.stringify(updatedVerificationData)
      );

      toast.success(
        response.data?.message ||
          t("registerVerify.fallbackResend")
      );
    } catch (error) {
      console.error("Resending verification code failed:", error);

      const message =
        error.response?.data?.message ||
        t("registerVerify.errResend");

      toast.error(message);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-sunken flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-brand">
          {t("registerVerify.title")}
        </h1>

        <p className="text-center text-text-muted mt-3 mb-8">
          {t("registerVerify.subtitle", {
            method: t(
              METHOD_KEYS[verificationData?.method] || "auth.method_selected",
            ),
          })}
        </p>

        <Input
          label={t("auth.verificationCode")}
          name="verification_code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder={t("auth.enterVerificationCode")}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-4"
          onClick={handleVerify}
          disabled={loading}
        >
          {loading ? t("auth.verifying") : t("registerVerify.submit")}
        </Button>

        <button
          type="button"
          onClick={handleResend}
          disabled={resending}
          className="w-full mt-4 text-brand font-semibold hover:underline disabled:opacity-50"
        >
          {resending
            ? t("auth.sending")
            : t("auth.resendCode")}
        </button>
      </Card>
    </div>
  );
}

export default RegisterVerify;