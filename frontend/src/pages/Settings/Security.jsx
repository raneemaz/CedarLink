import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff, LockKeyhole, ShieldCheck, ShieldOff } from "lucide-react";
import { toast } from "react-toastify";
import BackLink from "../../components/common/BackLink";
import api from "../../services/api";

// Module scope: a component declared inside Security()'s body gets a new
// identity every render, so React unmounts and remounts it on each
// keystroke and the field loses focus. Confirmed before moving it.
function PasswordInput({
  label,
  value,
  onChange,
  show,
  setShow,
  placeholder,
  autoComplete = "new-password",
}) {
  const { t } = useTranslation();

  return (
    <div>
      <label className="mb-2 block text-small font-medium text-ink-body">
        {label}
      </label>

      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className="w-full rounded-control border border-line-strong px-4 py-3 pe-12 text-small outline-none transition focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
        />

        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute end-3 top-1/2 -translate-y-1/2 cursor-pointer text-ink-muted hover:text-ink-body"
          aria-label={
            show ? t("common.hidePassword") : t("common.showPassword")
          }
        >
          {show ? <EyeOff size={19} /> : <Eye size={19} />}
        </button>
      </div>
    </div>
  );
}

function Security() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);

  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [twoFactorMethod, setTwoFactorMethod] = useState(null);

  const [twoFactorLoading, setTwoFactorLoading] = useState(true);
  const [setupLoading, setSetupLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);

  const [showSetup, setShowSetup] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");

  const [setupData, setSetupData] = useState(null);
  const [setupChallengeToken, setSetupChallengeToken] = useState("");

  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [showRecoveryCodes, setShowRecoveryCodes] = useState(false);

  const [showRegenerateCodes, setShowRegenerateCodes] = useState(false);

  const [regeneratePassword, setRegeneratePassword] = useState("");

  const [showRegeneratePassword, setShowRegeneratePassword] = useState(false);

  const [regenerateChallengeToken, setRegenerateChallengeToken] = useState("");

  const [regenerateChallengeStarted, setRegenerateChallengeStarted] =
    useState(false);

  const [regenerateCode, setRegenerateCode] = useState("");

  const [regenerateLoading, setRegenerateLoading] = useState(false);

  const [regenerateVerifyLoading, setRegenerateVerifyLoading] = useState(false);

  const [challengeLoading, setChallengeLoading] = useState(false);
  const [securityChallengeToken, setSecurityChallengeToken] = useState("");

  const [securityPassword, setSecurityPassword] = useState("");
  const [showSecurityPassword, setShowSecurityPassword] = useState(false);

  const [showDisable, setShowDisable] = useState(false);
  const [disableCode, setDisableCode] = useState("");
  const [disableLoading, setDisableLoading] = useState(false);
  const [securityChallengeStarted, setSecurityChallengeStarted] =
    useState(false);

  const getUser = () => {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  };

  const loadTwoFactorStatus = async () => {
    try {
      setTwoFactorLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.get(`/users/${user.id}/2fa`);

      setTwoFactorEnabled(Boolean(response.data?.two_factor_enabled));

      setTwoFactorMethod(response.data?.two_factor_method || null);
    } catch (error) {
      console.error("Error loading 2FA status:", error);

      const message =
        error.response?.data?.message ||
        t("security.errLoadStatus");

      toast.error(message);
    } finally {
      setTwoFactorLoading(false);
    }
  };

  useEffect(() => {
    loadTwoFactorStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();

    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error(t("security.errFillPasswords"));
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error(t("security.errPasswordsMatch"));
      return;
    }

    try {
      setLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.put(`/users/${user.id}/password`, {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      toast.success(response.data?.message || t("security.toastPasswordChanged"));

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      console.error("Error changing password:", error);

      const message =
        error.response?.data?.message || t("security.errChangePassword");

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleStartTwoFactorSetup = async () => {
    try {
      setSetupLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.post(`/users/${user.id}/2fa/setup`, {
        method: "email",
      });

      console.log("2FA setup response:", response.data);

      if (!response.data?.challenge_token) {
        toast.error(t("security.errChallengeNotCreated"));
        return;
      }

      setSetupData(response.data);

      setSetupChallengeToken(response.data.challenge_token);

      setVerificationCode("");
      setRecoveryCodes([]);
      setShowRecoveryCodes(false);
      setShowSetup(true);

      toast.success(
        response.data?.message || t("security.toastSetupStarted"),
      );
    } catch (error) {
      console.error("Error starting 2FA setup:", error);

      const message =
        error.response?.data?.message ||
        t("security.errStartSetup");

      toast.error(message);
    } finally {
      setSetupLoading(false);
    }
  };

  const handleConfirmTwoFactorSetup = async () => {
    if (!verificationCode.trim()) {
      toast.error(t("security.errEnterCode"));
      return;
    }

    if (!setupChallengeToken) {
      toast.error(
        t("security.errChallengeMissing"),
      );
      return;
    }

    try {
      setConfirmLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.post(`/users/${user.id}/2fa/confirm`, {
        challenge_token: setupChallengeToken,
        code: verificationCode.trim(),
      });

      console.log("2FA confirmation response:", response.data);

      setTwoFactorEnabled(true);

      setTwoFactorMethod(
        response.data?.two_factor_method || setupData?.method || null,
      );

      const codes = response.data?.recovery_codes || [];

      setRecoveryCodes(codes);
      setShowRecoveryCodes(codes.length > 0);

      setShowSetup(false);
      setSetupData(null);
      setSetupChallengeToken("");
      setVerificationCode("");

      toast.success(
        response.data?.message ||
          t("security.toastEnabled"),
      );

      await loadTwoFactorStatus();
    } catch (error) {
      console.error("Error confirming 2FA setup:", error);

      const message =
        error.response?.data?.message ||
        t("security.errConfirm");

      toast.error(message);
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleCreateSecurityChallenge = async () => {
    if (!securityPassword) {
      toast.error(t("security.errEnterPasswordFirst"));
      return null;
    }

    try {
      setChallengeLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return null;
      }

      const response = await api.post(
        `/users/${user.id}/2fa/security-challenge`,
        {
          current_password: securityPassword,
        },
      );

      const token = response.data?.challenge_token || "";

      if (!token) {
        toast.error(t("security.errCreateChallenge"));
        return null;
      }

      setSecurityChallengeToken(token);
      setSecurityChallengeStarted(true);
      setDisableCode("");

      toast.success(response.data?.message || t("security.toastVerificationStarted"));

      return response.data;
    } catch (error) {
      console.error("Error creating security challenge:", error);

      const message =
        error.response?.data?.message || t("security.errCreateChallenge2");

      toast.error(message);

      return null;
    } finally {
      setChallengeLoading(false);
    }
  };

  const handleStartRecoveryCodeRegeneration = async () => {
    if (!regeneratePassword) {
      toast.error(t("security.errEnterPasswordFirst"));
      return;
    }

    try {
      setRegenerateLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.post(
        `/users/${user.id}/2fa/security-challenge`,
        {
          current_password: regeneratePassword,
        },
      );

      const token = response.data?.challenge_token || "";

      if (!token) {
        toast.error(t("security.errCreateChallenge"));
        return;
      }

      setRegenerateChallengeToken(token);
      setRegenerateChallengeStarted(true);
      setRegenerateCode("");

      toast.success(response.data?.message || t("security.toastCodeSent"));
    } catch (error) {
      console.error("Error starting recovery code regeneration:", error);

      const message =
        error.response?.data?.message ||
        t("security.errStartVerification");

      toast.error(message);
    } finally {
      setRegenerateLoading(false);
    }
  };

  const handleRegenerateRecoveryCodes = async () => {
    if (!regenerateCode.trim()) {
      toast.error(t("security.errEnterYourCode"));
      return;
    }

    if (!regenerateChallengeToken) {
      toast.error(t("security.errVerificationMissing"));
      return;
    }

    try {
      setRegenerateVerifyLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.post(
        `/users/${user.id}/2fa/recovery-codes/regenerate`,
        {
          challenge_token: regenerateChallengeToken,
          code: regenerateCode.trim(),
          use_recovery_code: false,
        },
      );

      const codes = response.data?.recovery_codes || [];

      if (codes.length === 0) {
        toast.error(t("security.errNoRecoveryCodes"));
        return;
      }

      setRecoveryCodes(codes);
      setShowRecoveryCodes(true);

      setShowRegenerateCodes(false);
      setRegeneratePassword("");
      setShowRegeneratePassword(false);
      setRegenerateChallengeToken("");
      setRegenerateChallengeStarted(false);
      setRegenerateCode("");

      toast.success(
        response.data?.message || t("security.toastRegenerated"),
      );
    } catch (error) {
      console.error("Error regenerating recovery codes:", error);

      const message =
        error.response?.data?.message || t("security.errRegenerate");

      toast.error(message);
    } finally {
      setRegenerateVerifyLoading(false);
    }
  };

  const handleDisableTwoFactor = async () => {
    if (!disableCode.trim()) {
      toast.error(t("security.errEnterYourCode"));
      return;
    }

    if (!securityChallengeToken) {
      toast.error(t("security.errStartVerificationFirst"));
      return;
    }

    try {
      setDisableLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error(t("security.errNoAccount"));
        return;
      }

      const response = await api.post(`/users/${user.id}/2fa/disable`, {
        challenge_token: securityChallengeToken,
        code: disableCode.trim(),
      });

      setTwoFactorEnabled(false);
      setTwoFactorMethod(null);

      setSecurityChallengeToken("");
      setSecurityChallengeStarted(false);
      setSecurityPassword("");
      setDisableCode("");

      setShowDisable(false);

      setRecoveryCodes([]);
      setShowRecoveryCodes(false);

      toast.success(
        response.data?.message ||
          t("security.toastDisabled"),
      );

      await loadTwoFactorStatus();
    } catch (error) {
      console.error("Error disabling 2FA:", error);

      const message =
        error.response?.data?.message ||
        t("security.errDisable");

      toast.error(message);
    } finally {
      setDisableLoading(false);
    }
  };

  const handleCancelSetup = () => {
    setShowSetup(false);
    setSetupData(null);
    setSetupChallengeToken("");
    setVerificationCode("");
  };

  const handleCancelDisable = () => {
    setShowDisable(false);

    setSecurityPassword("");
    setShowSecurityPassword(false);

    setSecurityChallengeToken("");
    setSecurityChallengeStarted(false);

    setDisableCode("");
  };

  const handleCancelRecoveryCodeRegeneration = () => {
    setShowRegenerateCodes(false);

    setRegeneratePassword("");
    setShowRegeneratePassword(false);

    setRegenerateChallengeToken("");
    setRegenerateChallengeStarted(false);

    setRegenerateCode("");
  };

  return (
    <div className="min-h-screen bg-paper px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {}
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("backLink.settings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-card bg-paper-sunken text-cedar">
              <LockKeyhole size={23} />
            </div>

            <div>
              <h1 className="text-title font-bold text-ink">
                {t("security.title")}
              </h1>

              <p className="mt-1 text-small text-ink-secondary">
                {t("security.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {}
        <section className="rounded-card bg-paper-raised shadow-card">
          <div className="border-b border-line-subtle px-6 py-5">
            <h2 className="text-title font-semibold text-ink">
              {t("security.changePasswordSection")}
            </h2>

            <p className="mt-1 text-small text-ink-muted">
              {t("security.changePasswordDesc")}
            </p>
          </div>

          <form onSubmit={handleChangePassword} className="space-y-5 px-6 py-6">
            <PasswordInput
              label={t("security.currentPassword")}
              value={currentPassword}
              onChange={setCurrentPassword}
              show={showCurrent}
              setShow={setShowCurrent}
              placeholder={t("security.currentPasswordPlaceholder")}
              autoComplete="current-password"
            />

            <PasswordInput
              label={t("security.newPassword")}
              value={newPassword}
              onChange={setNewPassword}
              show={showNew}
              setShow={setShowNew}
              placeholder={t("security.newPasswordPlaceholder")}
            />

            <PasswordInput
              label={t("security.confirmPassword")}
              value={confirmPassword}
              onChange={setConfirmPassword}
              show={showConfirm}
              setShow={setShowConfirm}
              placeholder={t("security.confirmPasswordPlaceholder")}
            />

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={loading}
                className="cursor-pointer rounded-control bg-cedar px-6 py-3 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? t("security.changingPassword") : t("security.changePassword")}
              </button>
            </div>
          </form>
        </section>

        {}
        <section className="mt-6 rounded-card bg-paper-raised shadow-card">
          <div className="border-b border-line-subtle px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-card bg-paper-sunken text-cedar">
                <ShieldCheck size={22} />
              </div>

              <div>
                <h2 className="text-title font-semibold text-ink">
                  {t("security.twoFactorTitle")}
                </h2>

                <p className="mt-1 text-small text-ink-muted">
                  {t("security.twoFactorDesc")}
                </p>
              </div>
            </div>
          </div>

          <div className="px-6 py-6">
            {}
            {twoFactorLoading ? (
              <div className="py-4 text-small text-ink-muted">
                {t("security.loading")}
              </div>
            ) : (
              <>
                {}
                {!twoFactorEnabled && !showSetup && (
                  <div>
                    <div className="mb-5 rounded-card border border-line bg-paper p-4">
                      <div className="flex items-center gap-3">
                        <ShieldOff size={21} className="text-ink-muted" />

                        <div>
                          <p className="font-medium text-ink">
                            {t("security.notEnabled")}
                          </p>

                          <p className="mt-1 text-small text-ink-muted">
                            {t("security.notEnabledDesc")}
                          </p>
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleStartTwoFactorSetup}
                      disabled={setupLoading}
                      className="cursor-pointer rounded-control bg-cedar px-6 py-3 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {setupLoading
                        ? t("security.startingSetup")
                        : t("security.setUp")}
                    </button>
                  </div>
                )}

                {}
                {!twoFactorEnabled && showSetup && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-body font-semibold text-ink">
                        {t("security.setUp")}
                      </h3>

                      <p className="mt-1 text-small text-ink-muted">
                        {t("security.setupEmailNote")}
                      </p>
                    </div>

                    {}
                    {setupData && (
                      <div className="rounded-card border border-line bg-paper p-5">
                        {}
                        {setupData.qr_code_data_url && (
                          <div className="mb-5 flex justify-center">
                            <img
                              src={setupData.qr_code_data_url}
                              alt={t("security.qrAlt")}
                              className="h-52 w-52 rounded-control border bg-paper-raised p-2"
                            />
                          </div>
                        )}

                        {}
                        {setupData.manual_key && (
                          <div className="mb-5">
                            <p className="text-small font-medium text-ink-body">
                              {t("security.setupKey")}
                            </p>

                            <p className="mt-1 break-all rounded-control bg-paper-raised p-3 font-mono text-small text-ink-emphasis">
                              {setupData.manual_key}
                            </p>
                          </div>
                        )}

                        {}
                        {setupData.method === "email" && (
                          <div>
                            <p className="font-medium text-ink">
                              {t("security.codeSent")}
                            </p>

                            <p className="mt-1 text-small text-ink-secondary">
                              {t("security.codeSentTo")}
                            </p>

                            {setupData.email && (
                              <p className="mt-2 font-medium text-ink-emphasis">
                                {setupData.email}
                              </p>
                            )}

                            <p className="mt-3 text-small text-ink-muted">
                              {t("security.devNote")}
                            </p>
                          </div>
                        )}

                        {setupData.message && (
                          <p className="mt-3 text-small text-ink-secondary">
                            {setupData.message}
                          </p>
                        )}
                      </div>
                    )}

                    <div>
                      <label className="mb-2 block text-small font-medium text-ink-body">
                        {t("security.verificationCode")}
                      </label>

                      <input
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        value={verificationCode}
                        onChange={(e) => setVerificationCode(e.target.value)}
                        placeholder={t("security.enterVerificationCode")}
                        className="w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none transition focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
                      />
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={handleConfirmTwoFactorSetup}
                        disabled={confirmLoading}
                        className="cursor-pointer rounded-control bg-cedar px-6 py-3 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {confirmLoading ? t("security.confirming") : t("security.confirmEnable")}
                      </button>

                      <button
                        type="button"
                        onClick={handleCancelSetup}
                        disabled={confirmLoading}
                        className="cursor-pointer rounded-control border border-line-strong px-6 py-3 text-small font-semibold text-ink-body transition hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {t("security.cancel")}
                      </button>
                    </div>
                  </div>
                )}

                {}
                {twoFactorEnabled && (
                  <div className="space-y-5">
                    <div className="rounded-card border border-cedar-tint bg-paper-sunken p-4">
                      <div className="flex items-center gap-3">
                        <ShieldCheck size={22} className="text-cedar" />

                        <div>
                          <p className="font-semibold text-cedar-strong">
                            {t("security.enabled")}
                          </p>

                          <p className="mt-1 text-small text-cedar-strong">
                            {t("security.enabledDesc")}
                          </p>
                        </div>
                      </div>
                    </div>

                    {twoFactorMethod && (
                      <div className="rounded-control border border-line p-4">
                        <p className="text-small text-ink-muted">
                          {t("security.authMethod")}
                        </p>

                        <p className="mt-1 font-medium capitalize text-ink">
                          {twoFactorMethod}
                        </p>
                      </div>
                    )}

                    {}
                    {showRecoveryCodes && recoveryCodes.length > 0 && (
                      <div className="rounded-card border border-warning-border bg-warning-subtle p-5">
                        <h3 className="font-semibold text-ink">
                          {t("security.recoveryCodesTitle")}
                        </h3>

                        <p className="mt-1 text-small text-ink-secondary">
                          {t("security.recoveryCodesNote")}
                        </p>

                        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                          {recoveryCodes.map((code, index) => (
                            <div
                              key={`${code}-${index}`}
                              className="rounded-control bg-paper-raised px-4 py-3 font-mono text-small text-ink-emphasis shadow-card"
                            >
                              {code}
                            </div>
                          ))}
                        </div>

                        <button
                          type="button"
                          onClick={() => setShowRecoveryCodes(false)}
                          className="mt-4 text-small font-medium text-ink-secondary hover:underline"
                        >
                          {t("security.hideRecoveryCodes")}
                        </button>
                      </div>
                    )}

                    {}
                    {!showRegenerateCodes && (
                      <div className="rounded-card border border-line bg-paper p-5">
                        <h3 className="font-semibold text-ink">
                          {t("security.recoveryCodesHeading")}
                        </h3>

                        <p className="mt-1 text-small text-ink-secondary">
                          {t("security.regenerateDesc")}
                        </p>

                        <p className="mt-2 text-small font-medium text-danger">
                          {t("security.regenerateWarn")}
                        </p>

                        <button
                          type="button"
                          onClick={() => {
                            setShowRegenerateCodes(true);

                            setRegeneratePassword("");
                            setRegenerateCode("");

                            setRegenerateChallengeToken("");
                            setRegenerateChallengeStarted(false);
                          }}
                          className="mt-4 cursor-pointer rounded-control border border-cedar px-5 py-3 text-small font-semibold text-cedar transition hover:bg-paper-sunken"
                        >
                          {t("security.regenerateTitle")}
                        </button>
                      </div>
                    )}

                    {showRegenerateCodes && (
                      <div className="rounded-card border border-warning-border bg-warning-subtle p-5">
                        <h3 className="font-semibold text-ink">
                          {t("security.regenerateTitle")}
                        </h3>

                        {!regenerateChallengeStarted ? (
                          <>
                            <p className="mt-1 text-small text-ink-secondary">
                              For security, enter your current password. We will
                              then send you a verification code.
                            </p>

                            <div className="relative mt-4">
                              <input
                                type={
                                  showRegeneratePassword ? "text" : "password"
                                }
                                value={regeneratePassword}
                                onChange={(e) =>
                                  setRegeneratePassword(e.target.value)
                                }
                                placeholder={t("security.currentPasswordPlaceholder")}
                                autoComplete="current-password"
                                className="w-full rounded-control border border-line-strong bg-paper-raised px-4 py-3 pe-12 text-small outline-none transition focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
                              />

                              <button
                                type="button"
                                onClick={() =>
                                  setShowRegeneratePassword(
                                    !showRegeneratePassword,
                                  )
                                }
                                className="absolute end-3 top-1/2 -translate-y-1/2 cursor-pointer text-ink-muted hover:text-ink-body"
                              >
                                {showRegeneratePassword ? (
                                  <EyeOff size={19} />
                                ) : (
                                  <Eye size={19} />
                                )}
                              </button>
                            </div>

                            <div className="mt-4 flex flex-wrap gap-3">
                              <button
                                type="button"
                                onClick={handleStartRecoveryCodeRegeneration}
                                disabled={regenerateLoading}
                                className="cursor-pointer rounded-control bg-cedar px-5 py-3 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {regenerateLoading
                                  ? t("security.sending")
                                  : t("security.sendVerificationCode")}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelRecoveryCodeRegeneration}
                                disabled={regenerateLoading}
                                className="cursor-pointer rounded-control border border-line-strong bg-paper-raised px-5 py-3 text-small font-semibold text-ink-body transition hover:bg-paper"
                              >
                                {t("security.cancel")}
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <p className="mt-1 text-small text-ink-secondary">
                              Enter the verification code to generate your new
                              recovery codes.
                            </p>

                            <p className="mt-2 text-small font-medium text-danger">
                              {t("security.regeneratePrevWarn")}
                            </p>

                            <input
                              type="text"
                              inputMode="numeric"
                              autoComplete="one-time-code"
                              value={regenerateCode}
                              onChange={(e) =>
                                setRegenerateCode(e.target.value)
                              }
                              placeholder={t("security.enterVerificationCode")}
                              className="mt-4 w-full rounded-control border border-line-strong bg-paper-raised px-4 py-3 text-small outline-none transition focus:border-cedar-ring focus:ring-2 focus:ring-cedar-tint"
                            />

                            <div className="mt-4 flex flex-wrap gap-3">
                              <button
                                type="button"
                                onClick={handleRegenerateRecoveryCodes}
                                disabled={regenerateVerifyLoading}
                                className="cursor-pointer rounded-control bg-cedar px-5 py-3 text-small font-semibold text-on-cedar transition hover:bg-cedar-strong disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {regenerateVerifyLoading
                                  ? t("security.generating")
                                  : t("security.generateNewCodes")}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelRecoveryCodeRegeneration}
                                disabled={regenerateVerifyLoading}
                                className="cursor-pointer rounded-control border border-line-strong bg-paper-raised px-5 py-3 text-small font-semibold text-ink-body transition hover:bg-paper"
                              >
                                {t("security.cancel")}
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {}
                    {!showDisable && (
                      <button
                        type="button"
                        onClick={() => {
                          setShowDisable(true);

                          setSecurityPassword("");
                          setDisableCode("");

                          setSecurityChallengeToken("");
                          setSecurityChallengeStarted(false);
                        }}
                        className="cursor-pointer rounded-control border border-danger-border px-5 py-3 text-small font-semibold text-danger transition hover:bg-danger-subtle"
                      >
                        {t("security.disableTitle")}
                      </button>
                    )}

                    {}
                    {showDisable && (
                      <div className="rounded-card border border-danger-border bg-danger-subtle p-5">
                        <h3 className="font-semibold text-ink">
                          {t("security.disableTitle")}
                        </h3>

                        {!securityChallengeStarted ? (
                          <>
                            <p className="mt-1 text-small text-ink-secondary">
                              For security, enter your current password. We will
                              then send you a verification code.
                            </p>

                            <div className="relative mt-4">
                              <input
                                type={
                                  showSecurityPassword ? "text" : "password"
                                }
                                value={securityPassword}
                                onChange={(e) =>
                                  setSecurityPassword(e.target.value)
                                }
                                placeholder={t("security.currentPasswordPlaceholder")}
                                autoComplete="current-password"
                                className="w-full rounded-control border border-line-strong bg-paper-raised px-4 py-3 pe-12 text-small outline-none transition focus:border-danger-accent focus:ring-2 focus:ring-danger-tint"
                              />

                              <button
                                type="button"
                                onClick={() =>
                                  setShowSecurityPassword(!showSecurityPassword)
                                }
                                className="absolute end-3 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink-body"
                              >
                                {showSecurityPassword ? (
                                  <EyeOff size={19} />
                                ) : (
                                  <Eye size={19} />
                                )}
                              </button>
                            </div>

                            <div className="mt-4 flex flex-wrap gap-3">
                              <button
                                type="button"
                                onClick={handleCreateSecurityChallenge}
                                disabled={challengeLoading}
                                className="cursor-pointer rounded-control bg-danger px-5 py-3 text-small font-semibold text-on-danger transition hover:bg-danger-strong disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {challengeLoading
                                  ? t("security.startingVerification")
                                  : t("security.sendVerificationCode")}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelDisable}
                                disabled={challengeLoading}
                                className="cursor-pointer rounded-control border border-line-strong bg-paper-raised px-5 py-3 text-small font-semibold text-ink-body transition hover:bg-paper"
                              >
                                {t("security.cancel")}
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <p className="mt-1 text-small text-ink-secondary">
                              Enter the verification code to confirm that you
                              want to disable two-factor authentication.
                            </p>

                            <input
                              type="text"
                              inputMode="numeric"
                              autoComplete="one-time-code"
                              value={disableCode}
                              onChange={(e) => setDisableCode(e.target.value)}
                              placeholder={t("security.enterVerificationCode")}
                              className="mt-4 w-full rounded-control border border-line-strong bg-paper-raised px-4 py-3 text-small outline-none transition focus:border-danger-accent focus:ring-2 focus:ring-danger-tint"
                            />

                            <div className="mt-4 flex flex-wrap gap-3">
                              <button
                                type="button"
                                onClick={handleDisableTwoFactor}
                                disabled={disableLoading}
                                className="cursor-pointer rounded-control bg-danger px-5 py-3 text-small font-semibold text-on-danger transition hover:bg-danger-strong disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {disableLoading
                                  ? t("security.disabling")
                                  : t("security.confirmDisable")}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelDisable}
                                disabled={disableLoading}
                                className="cursor-pointer rounded-control border border-line-strong bg-paper-raised px-5 py-3 text-small font-semibold text-ink-body transition hover:bg-paper"
                              >
                                {t("security.cancel")}
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default Security;