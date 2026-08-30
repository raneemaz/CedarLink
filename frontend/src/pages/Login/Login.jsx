import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

function Login() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [twoFactorRequired, setTwoFactorRequired] = useState(false);
  const [challengeToken, setChallengeToken] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [useRecoveryCode, setUseRecoveryCode] = useState(false);

  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const [deactivated, setDeactivated] = useState(false);
  const [reactivating, setReactivating] = useState(false);

  const navigate = useNavigate();
  const { login } = useAuth();

  const redirectUser = (user) => {
    if (!user) {
      navigate("/");
      return;
    }

    if (user.role === "admin") {
      navigate("/admin");
    } else if (user.role === "vendor") {
      navigate("/vendor/store");
    } else {
      navigate("/");
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      toast.error(t("login.errEnterBoth"));
      return;
    }

    try {
      setLoading(true);
      setDeactivated(false);

      const response = await api.post("/auth/login", {
        email,
        password,
      });

      if (response.data.verification_required) {
        setChallengeToken(response.data.challenge_token);
        setTwoFactorRequired(true);

        toast.info(t("login.infoVerificationRequired"));
        return;
      }

      const userData = response.data.user || response.data;
      const accessToken = response.data.access_token || response.data.token;
      const refreshToken = response.data.refresh_token || null;

      if (!userData) {
        toast.error(t("login.errUserInfoMissing"));
        return;
      }

      login(userData, accessToken, refreshToken);

      toast.success(t("login.toastSuccess"));
      redirectUser(userData);
    } catch (error) {
      if (error.response?.data?.account_deactivated) {
        setDeactivated(true);
        toast.info(
          error.response.data.message || t("login.deactivatedTitle"),
        );
        return;
      }

      toast.error(
        error.response?.data?.message ||
          error.message ||
          t("login.fallbackFailed"),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReactivate = async () => {
    setReactivating(true);
    try {
      const response = await api.post("/auth/reactivate", {
        email,
        password,
      });
      toast.success(
        response.data?.message || t("login.reactivatedFallback"),
      );
      setDeactivated(false);
      await handleLogin();
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("login.reactivateError"),
      );
    } finally {
      setReactivating(false);
    }
  };

  const handleVerifyTwoFactor = async () => {
    if (!verificationCode) {
      toast.error(
        useRecoveryCode
          ? t("login.errEnterRecovery")
          : t("login.errEnterCode"),
      );
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/auth/2fa/verify", {
        challenge_token: challengeToken,
        code: verificationCode,
        use_recovery_code: useRecoveryCode,
      });

      const userData = response.data.user || response.data;
      const accessToken = response.data.access_token || response.data.token;
      const refreshToken = response.data.refresh_token || null;

      if (!userData) {
        toast.error(t("login.errVerifyUserInfoMissing"));
        return;
      }

      login(userData, accessToken, refreshToken);

      toast.success(t("login.toastVerifySuccess"));
      redirectUser(userData);
    } catch (error) {
      toast.error(
        error.response?.data?.message ||
          error.message ||
          t("login.fallbackVerifyFailed"),
      );
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (!challengeToken) {
      toast.error(t("login.errSessionMissing"));
      return;
    }

    try {
      setResending(true);

      const response = await api.post("/auth/2fa/resend", {
        challenge_token: challengeToken,
      });

      if (response.data.challenge_token) {
        setChallengeToken(response.data.challenge_token);
      }

      toast.success(response.data.message || t("login.fallbackResend"));
    } catch (error) {
      toast.error(
        error.response?.data?.message ||
          error.message ||
          t("login.fallbackResend"),
      );
    } finally {
      setResending(false);
    }
  };

  const handleBackToLogin = () => {
    setTwoFactorRequired(false);
    setChallengeToken("");
    setVerificationCode("");
    setUseRecoveryCode(false);
  };

  if (twoFactorRequired) {
    return (
      <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-8">
        <Card className="w-full max-w-md p-6 sm:p-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-center text-green-700">
            {t("auth.twoFactorTitle")}
          </h1>

          <p className="text-center text-sm text-gray-500 mt-2 mb-6">
            {useRecoveryCode
              ? t("login.promptRecovery")
              : t("login.promptCode")}
          </p>

          <Input
            label={
              useRecoveryCode
                ? t("auth.recoveryCode")
                : t("auth.verificationCode")
            }
            type="text"
            name="verificationCode"
            autoComplete="one-time-code"
            placeholder={
              useRecoveryCode
                ? t("auth.enterRecoveryCode")
                : t("auth.enterVerificationCode")
            }
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
          />

          <Button
            className="w-full cursor-pointer mt-2"
            onClick={handleVerifyTwoFactor}
            disabled={loading}
          >
            {loading ? t("auth.verifying") : t("auth.verify")}
          </Button>

          {!useRecoveryCode && (
            <button
              type="button"
              onClick={handleResendCode}
              disabled={resending}
              className="w-full mt-4 text-sm text-green-700 font-semibold hover:underline disabled:opacity-50"
            >
              {resending ? t("auth.sending") : t("auth.resendCode")}
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              setVerificationCode("");
              setUseRecoveryCode(!useRecoveryCode);
            }}
            className="w-full mt-3 text-sm text-gray-600 hover:underline"
          >
            {useRecoveryCode
              ? t("login.useCodeInstead")
              : t("login.useRecoveryInstead")}
          </button>

          <button
            type="button"
            onClick={handleBackToLogin}
            className="w-full mt-5 text-sm text-gray-500 hover:underline"
          >
            {t("auth.backToLogin")}
          </button>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-8">
      <Card className="w-full max-w-md p-6 sm:p-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-center text-green-700">
          CedarLink
        </h1>

        <p className="text-center text-sm text-gray-500 mt-1 mb-6">
          {t("auth.appTagline")}
        </p>

        <Input
          label={t("auth.email")}
          type="email"
          name="email"
          autoComplete="username"
          placeholder={t("auth.enterEmail")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <Input
          label={t("auth.password")}
          type="password"
          name="password"
          autoComplete="current-password"
          placeholder={t("auth.enterPassword")}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-2"
          onClick={handleLogin}
          disabled={loading || reactivating}
        >
          {loading ? t("login.loggingIn") : t("login.button")}
        </Button>

        <p className="text-center text-sm mt-3">
          <Link
            to="/forgot-password"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            {t("login.forgotPassword")}
          </Link>
        </p>

        {deactivated && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
            <p className="font-medium text-amber-800">
              {t("login.deactivatedTitle")}
            </p>
            <p className="mt-1 text-amber-700">
              {t("login.deactivatedBody")}
            </p>
            <button
              type="button"
              onClick={handleReactivate}
              disabled={reactivating}
              className="mt-3 cursor-pointer rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:opacity-60"
            >
              {reactivating
                ? t("login.reactivating")
                : t("login.reactivate")}
            </button>
          </div>
        )}

        <p className="text-center text-sm text-gray-600 mt-5">
          {t("login.noAccount")}{" "}
          <Link
            to="/register"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            {t("login.register")}
          </Link>
        </p>
      </Card>
    </main>
  );
}

export default Login;
