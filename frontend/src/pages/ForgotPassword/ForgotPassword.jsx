import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import api from "../../services/api";

function ForgotPassword() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) {
      toast.error(t("forgotPassword.errEnterEmail"));
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/auth/password-reset/request", {
        email: email.trim(),
      });

      sessionStorage.setItem(
        "password_reset",
        JSON.stringify({
          challenge_token: response.data.challenge_token,
          method: response.data.method,
          email: email.trim(),
        })
      );

      toast.success(t("forgotPassword.confirmation"));

      navigate("/reset-password");
    } catch (error) {
      console.error("Password reset request failed:", error);

      const message =
        error.response?.data?.message ||
        t("forgotPassword.errCantStart");

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper-sunken flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-cedar">
          {t("forgotPassword.title")}
        </h1>

        <p className="text-center text-ink-muted mt-3 mb-8">
          {t("forgotPassword.subtitle")}
        </p>

        <Input
          label={t("auth.email")}
          name="email"
          type="email"
          autoComplete="email"
          placeholder={t("auth.enterEmail")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-2"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? t("forgotPassword.sending") : t("forgotPassword.sendButton")}
        </Button>

        <p className="text-center text-ink-secondary mt-6">
          {t("forgotPassword.rememberedIt")}{" "}
          <Link
            to="/login"
            className="text-cedar cursor-pointer font-semibold hover:underline"
          >
            {t("forgotPassword.backToLogin")}
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default ForgotPassword;
