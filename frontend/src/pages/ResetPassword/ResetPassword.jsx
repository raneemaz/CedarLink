import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import api from "../../services/api";

function ResetPassword() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const resetData = JSON.parse(
    sessionStorage.getItem("password_reset") || "null"
  );

  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleReset = async () => {
    if (!resetData?.challenge_token) {
      toast.error(t("resetPassword.errSessionNotFound"));
      navigate("/forgot-password");
      return;
    }

    if (!code.trim()) {
      toast.error(t("resetPassword.errEnterCode"));
      return;
    }

    if (newPassword.length < 8) {
      toast.error(t("resetPassword.errMin8"));
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error(t("resetPassword.errPasswordsMatch"));
      return;
    }

    try {
      setLoading(true);

      await api.post("/auth/password-reset/confirm", {
        challenge_token: resetData.challenge_token,
        code: code.trim(),
        new_password: newPassword,
      });

      sessionStorage.removeItem("password_reset");

      toast.success(t("resetPassword.toastSuccess"));

      navigate("/login");
    } catch (error) {
      console.error("Password reset failed:", error);

      const message =
        error.response?.data?.message ||
        t("resetPassword.errSessionNotFound");

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-green-700">
          {t("resetPassword.title")}
        </h1>

        <p className="text-center text-gray-500 mt-3 mb-8">
          {t("resetPassword.subtitle", {
            email: resetData?.email || t("auth.genericEmail"),
          })}
        </p>

        <Input
          label={t("resetPassword.resetCode")}
          name="reset_code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder={t("resetPassword.enterResetCode")}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />

        <Input
          label={t("resetPassword.newPassword")}
          name="new_password"
          type="password"
          autoComplete="new-password"
          placeholder={t("resetPassword.atLeast8")}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />

        <Input
          label={t("resetPassword.confirmNewPassword")}
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          placeholder={t("resetPassword.reenterPassword")}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-2"
          onClick={handleReset}
          disabled={loading}
        >
          {loading ? t("resetPassword.resetting") : t("resetPassword.submit")}
        </Button>

        <p className="text-center text-gray-600 mt-6">
          {t("resetPassword.didntGetCode")}{" "}
          <Link
            to="/forgot-password"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            {t("resetPassword.requestNew")}
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default ResetPassword;
