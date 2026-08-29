import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, LockKeyhole, ShieldCheck, ShieldOff } from "lucide-react";
import { toast } from "react-toastify";
import api from "../../services/api";

// Module scope: a component declared inside Security()'s body gets a new
// identity every render, so React unmounts and remounts it on each
// keystroke and the field loses focus. Confirmed before moving it.
function PasswordInput({ label, value, onChange, show, setShow, placeholder }) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-gray-700">
        {label}
      </label>

      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={
            label === "Current Password"
              ? "current-password"
              : "new-password"
          }
          className="w-full rounded-lg border border-gray-300 px-4 py-3 pr-12 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
        />

        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-gray-500 hover:text-gray-700"
          aria-label={show ? "Hide password" : "Show password"}
        >
          {show ? <EyeOff size={19} /> : <Eye size={19} />}
        </button>
      </div>
    </div>
  );
}

function Security() {
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
        toast.error("Unable to identify your account.");
        return;
      }

      const response = await api.get(`/users/${user.id}/2fa`);

      setTwoFactorEnabled(Boolean(response.data?.two_factor_enabled));

      setTwoFactorMethod(response.data?.two_factor_method || null);
    } catch (error) {
      console.error("Error loading 2FA status:", error);

      const message =
        error.response?.data?.message ||
        "Failed to load two-factor authentication status.";

      toast.error(message);
    } finally {
      setTwoFactorLoading(false);
    }
  };

  useEffect(() => {
    loadTwoFactorStatus();
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();

    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error("Please fill in all password fields.");
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error("New passwords do not match.");
      return;
    }

    try {
      setLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error("Unable to identify your account.");
        return;
      }

      const response = await api.put(`/users/${user.id}/password`, {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      toast.success(response.data?.message || "Password changed successfully.");

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      console.error("Error changing password:", error);

      const message =
        error.response?.data?.message || "Failed to change your password.";

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
        toast.error("Unable to identify your account.");
        return;
      }

      const response = await api.post(`/users/${user.id}/2fa/setup`, {
        method: "email",
      });

      console.log("2FA setup response:", response.data);

      if (!response.data?.challenge_token) {
        toast.error("The verification challenge could not be created.");
        return;
      }

      setSetupData(response.data);

      setSetupChallengeToken(response.data.challenge_token);

      setVerificationCode("");
      setRecoveryCodes([]);
      setShowRecoveryCodes(false);
      setShowSetup(true);

      toast.success(
        response.data?.message || "Two-factor authentication setup started.",
      );
    } catch (error) {
      console.error("Error starting 2FA setup:", error);

      const message =
        error.response?.data?.message ||
        "Failed to start two-factor authentication setup.";

      toast.error(message);
    } finally {
      setSetupLoading(false);
    }
  };

  const handleConfirmTwoFactorSetup = async () => {
    if (!verificationCode.trim()) {
      toast.error("Please enter the verification code.");
      return;
    }

    if (!setupChallengeToken) {
      toast.error(
        "Verification challenge is missing. Please start the setup again.",
      );
      return;
    }

    try {
      setConfirmLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error("Unable to identify your account.");
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
          "Two-factor authentication enabled successfully.",
      );

      await loadTwoFactorStatus();
    } catch (error) {
      console.error("Error confirming 2FA setup:", error);

      const message =
        error.response?.data?.message ||
        "Failed to confirm two-factor authentication.";

      toast.error(message);
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleCreateSecurityChallenge = async () => {
    if (!securityPassword) {
      toast.error("Please enter your current password first.");
      return null;
    }

    try {
      setChallengeLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error("Unable to identify your account.");
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
        toast.error("Unable to create a security challenge.");
        return null;
      }

      setSecurityChallengeToken(token);
      setSecurityChallengeStarted(true);
      setDisableCode("");

      toast.success(response.data?.message || "Security verification started.");

      return response.data;
    } catch (error) {
      console.error("Error creating security challenge:", error);

      const message =
        error.response?.data?.message || "Failed to create security challenge.";

      toast.error(message);

      return null;
    } finally {
      setChallengeLoading(false);
    }
  };

  const handleStartRecoveryCodeRegeneration = async () => {
    if (!regeneratePassword) {
      toast.error("Please enter your current password first.");
      return;
    }

    try {
      setRegenerateLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error("Unable to identify your account.");
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
        toast.error("Unable to create a security challenge.");
        return;
      }

      setRegenerateChallengeToken(token);
      setRegenerateChallengeStarted(true);
      setRegenerateCode("");

      toast.success(response.data?.message || "Verification code sent.");
    } catch (error) {
      console.error("Error starting recovery code regeneration:", error);

      const message =
        error.response?.data?.message ||
        "Failed to start security verification.";

      toast.error(message);
    } finally {
      setRegenerateLoading(false);
    }
  };

  const handleRegenerateRecoveryCodes = async () => {
    if (!regenerateCode.trim()) {
      toast.error("Please enter your verification code.");
      return;
    }

    if (!regenerateChallengeToken) {
      toast.error("Security verification is missing. Please start again.");
      return;
    }

    try {
      setRegenerateVerifyLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error("Unable to identify your account.");
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
        toast.error("Recovery codes were not returned.");
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
        response.data?.message || "Recovery codes regenerated successfully.",
      );
    } catch (error) {
      console.error("Error regenerating recovery codes:", error);

      const message =
        error.response?.data?.message || "Failed to regenerate recovery codes.";

      toast.error(message);
    } finally {
      setRegenerateVerifyLoading(false);
    }
  };

  const handleDisableTwoFactor = async () => {
    if (!disableCode.trim()) {
      toast.error("Please enter your verification code.");
      return;
    }

    if (!securityChallengeToken) {
      toast.error("Please start security verification first.");
      return;
    }

    try {
      setDisableLoading(true);

      const user = getUser();

      if (!user?.id) {
        toast.error("Unable to identify your account.");
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
          "Two-factor authentication has been disabled.",
      );

      await loadTwoFactorStatus();
    } catch (error) {
      console.error("Error disabling 2FA:", error);

      const message =
        error.response?.data?.message ||
        "Failed to disable two-factor authentication.";

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
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        {}
        <div className="mb-8">
          <button
            onClick={() => navigate("/settings")}
            className="mb-4 cursor-pointer text-sm text-green-700 hover:underline"
          >
            ← Back to Settings
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <LockKeyhole size={23} />
            </div>

            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Login & Security
              </h1>

              <p className="mt-1 text-sm text-gray-600">
                Manage your password and account security.
              </p>
            </div>
          </div>
        </div>

        {}
        <section className="rounded-2xl bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-5">
            <h2 className="text-xl font-semibold text-gray-900">
              Change Password
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              Update your CedarLink account password.
            </p>
          </div>

          <form onSubmit={handleChangePassword} className="space-y-5 px-6 py-6">
            <PasswordInput
              label="Current Password"
              value={currentPassword}
              onChange={setCurrentPassword}
              show={showCurrent}
              setShow={setShowCurrent}
              placeholder="Enter your current password"
            />

            <PasswordInput
              label="New Password"
              value={newPassword}
              onChange={setNewPassword}
              show={showNew}
              setShow={setShowNew}
              placeholder="Enter your new password"
            />

            <PasswordInput
              label="Confirm New Password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              show={showConfirm}
              setShow={setShowConfirm}
              placeholder="Confirm your new password"
            />

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={loading}
                className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Changing Password..." : "Change Password"}
              </button>
            </div>
          </form>
        </section>

        {}
        <section className="mt-6 rounded-2xl bg-white shadow-sm">
          <div className="border-b border-gray-100 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                <ShieldCheck size={22} />
              </div>

              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Two-Factor Authentication
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  Add an extra layer of security to your CedarLink account.
                </p>
              </div>
            </div>
          </div>

          <div className="px-6 py-6">
            {}
            {twoFactorLoading ? (
              <div className="py-4 text-sm text-gray-500">
                Loading security status...
              </div>
            ) : (
              <>
                {}
                {!twoFactorEnabled && !showSetup && (
                  <div>
                    <div className="mb-5 rounded-xl border border-gray-200 bg-gray-50 p-4">
                      <div className="flex items-center gap-3">
                        <ShieldOff size={21} className="text-gray-500" />

                        <div>
                          <p className="font-medium text-gray-900">
                            Two-factor authentication is not enabled.
                          </p>

                          <p className="mt-1 text-sm text-gray-500">
                            Protect your account by requiring an additional
                            verification step when signing in.
                          </p>
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleStartTwoFactorSetup}
                      disabled={setupLoading}
                      className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {setupLoading
                        ? "Starting Setup..."
                        : "Set Up Two-Factor Authentication"}
                    </button>
                  </div>
                )}

                {}
                {!twoFactorEnabled && showSetup && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        Set Up Two-Factor Authentication
                      </h3>

                      <p className="mt-1 text-sm text-gray-500">
                        Enter the verification code sent to your CedarLink email
                        address.
                      </p>
                    </div>

                    {}
                    {setupData && (
                      <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
                        {}
                        {setupData.qr_code_data_url && (
                          <div className="mb-5 flex justify-center">
                            <img
                              src={setupData.qr_code_data_url}
                              alt="Two-factor authentication QR code"
                              className="h-52 w-52 rounded-lg border bg-white p-2"
                            />
                          </div>
                        )}

                        {}
                        {setupData.manual_key && (
                          <div className="mb-5">
                            <p className="text-sm font-medium text-gray-700">
                              Setup Key
                            </p>

                            <p className="mt-1 break-all rounded-lg bg-white p-3 font-mono text-sm text-gray-800">
                              {setupData.manual_key}
                            </p>
                          </div>
                        )}

                        {}
                        {setupData.method === "email" && (
                          <div>
                            <p className="font-medium text-gray-900">
                              Verification code sent
                            </p>

                            <p className="mt-1 text-sm text-gray-600">
                              A verification code was sent to:
                            </p>

                            {setupData.email && (
                              <p className="mt-2 font-medium text-gray-800">
                                {setupData.email}
                              </p>
                            )}

                            <p className="mt-3 text-sm text-gray-500">
                              In development mode, check your Flask terminal for
                              the verification code.
                            </p>
                          </div>
                        )}

                        {setupData.message && (
                          <p className="mt-3 text-sm text-gray-600">
                            {setupData.message}
                          </p>
                        )}
                      </div>
                    )}

                    <div>
                      <label className="mb-2 block text-sm font-medium text-gray-700">
                        Verification Code
                      </label>

                      <input
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        value={verificationCode}
                        onChange={(e) => setVerificationCode(e.target.value)}
                        placeholder="Enter verification code"
                        className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                      />
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={handleConfirmTwoFactorSetup}
                        disabled={confirmLoading}
                        className="cursor-pointer rounded-lg bg-green-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {confirmLoading ? "Confirming..." : "Confirm & Enable"}
                      </button>

                      <button
                        type="button"
                        onClick={handleCancelSetup}
                        disabled={confirmLoading}
                        className="cursor-pointer rounded-lg border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {}
                {twoFactorEnabled && (
                  <div className="space-y-5">
                    <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                      <div className="flex items-center gap-3">
                        <ShieldCheck size={22} className="text-green-700" />

                        <div>
                          <p className="font-semibold text-green-900">
                            Two-factor authentication is enabled.
                          </p>

                          <p className="mt-1 text-sm text-green-800">
                            Your account has an additional layer of login
                            protection.
                          </p>
                        </div>
                      </div>
                    </div>

                    {twoFactorMethod && (
                      <div className="rounded-lg border border-gray-200 p-4">
                        <p className="text-sm text-gray-500">
                          Authentication method
                        </p>

                        <p className="mt-1 font-medium capitalize text-gray-900">
                          {twoFactorMethod}
                        </p>
                      </div>
                    )}

                    {}
                    {showRecoveryCodes && recoveryCodes.length > 0 && (
                      <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-5">
                        <h3 className="font-semibold text-gray-900">
                          Save Your Recovery Codes
                        </h3>

                        <p className="mt-1 text-sm text-gray-600">
                          Store these codes somewhere safe. They can be used if
                          you cannot access your normal two-factor
                          authentication method.
                        </p>

                        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                          {recoveryCodes.map((code, index) => (
                            <div
                              key={`${code}-${index}`}
                              className="rounded-lg bg-white px-4 py-3 font-mono text-sm text-gray-800 shadow-sm"
                            >
                              {code}
                            </div>
                          ))}
                        </div>

                        <button
                          type="button"
                          onClick={() => setShowRecoveryCodes(false)}
                          className="mt-4 text-sm font-medium text-gray-600 hover:underline"
                        >
                          Hide recovery codes
                        </button>
                      </div>
                    )}

                    {}
                    {!showRegenerateCodes && (
                      <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
                        <h3 className="font-semibold text-gray-900">
                          Recovery Codes
                        </h3>

                        <p className="mt-1 text-sm text-gray-600">
                          Generate a new set of recovery codes if you no longer
                          have access to your previous codes.
                        </p>

                        <p className="mt-2 text-sm font-medium text-red-600">
                          Generating new codes will invalidate all previous
                          recovery codes.
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
                          className="mt-4 cursor-pointer rounded-lg border border-green-700 px-5 py-3 text-sm font-semibold text-green-700 transition hover:bg-green-50"
                        >
                          Generate New Recovery Codes
                        </button>
                      </div>
                    )}

                    {showRegenerateCodes && (
                      <div className="rounded-xl border border-yellow-300 bg-yellow-50 p-5">
                        <h3 className="font-semibold text-gray-900">
                          Generate New Recovery Codes
                        </h3>

                        {!regenerateChallengeStarted ? (
                          <>
                            <p className="mt-1 text-sm text-gray-600">
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
                                placeholder="Enter your current password"
                                autoComplete="current-password"
                                className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 pr-12 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                              />

                              <button
                                type="button"
                                onClick={() =>
                                  setShowRegeneratePassword(
                                    !showRegeneratePassword,
                                  )
                                }
                                className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-gray-500 hover:text-gray-700"
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
                                className="cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {regenerateLoading
                                  ? "Sending..."
                                  : "Send Verification Code"}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelRecoveryCodeRegeneration}
                                disabled={regenerateLoading}
                                className="cursor-pointer rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                              >
                                Cancel
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <p className="mt-1 text-sm text-gray-600">
                              Enter the verification code to generate your new
                              recovery codes.
                            </p>

                            <p className="mt-2 text-sm font-medium text-red-600">
                              Your previous recovery codes will stop working.
                            </p>

                            <input
                              type="text"
                              inputMode="numeric"
                              autoComplete="one-time-code"
                              value={regenerateCode}
                              onChange={(e) =>
                                setRegenerateCode(e.target.value)
                              }
                              placeholder="Enter verification code"
                              className="mt-4 w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                            />

                            <div className="mt-4 flex flex-wrap gap-3">
                              <button
                                type="button"
                                onClick={handleRegenerateRecoveryCodes}
                                disabled={regenerateVerifyLoading}
                                className="cursor-pointer rounded-lg bg-green-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {regenerateVerifyLoading
                                  ? "Generating..."
                                  : "Generate New Codes"}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelRecoveryCodeRegeneration}
                                disabled={regenerateVerifyLoading}
                                className="cursor-pointer rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                              >
                                Cancel
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
                        className="cursor-pointer rounded-lg border border-red-300 px-5 py-3 text-sm font-semibold text-red-600 transition hover:bg-red-50"
                      >
                        Disable Two-Factor Authentication
                      </button>
                    )}

                    {}
                    {showDisable && (
                      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
                        <h3 className="font-semibold text-gray-900">
                          Disable Two-Factor Authentication
                        </h3>

                        {!securityChallengeStarted ? (
                          <>
                            <p className="mt-1 text-sm text-gray-600">
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
                                placeholder="Enter your current password"
                                autoComplete="current-password"
                                className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 pr-12 text-sm outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100"
                              />

                              <button
                                type="button"
                                onClick={() =>
                                  setShowSecurityPassword(!showSecurityPassword)
                                }
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
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
                                className="cursor-pointer rounded-lg bg-red-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {challengeLoading
                                  ? "Starting Verification..."
                                  : "Send Verification Code"}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelDisable}
                                disabled={challengeLoading}
                                className="cursor-pointer rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                              >
                                Cancel
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <p className="mt-1 text-sm text-gray-600">
                              Enter the verification code to confirm that you
                              want to disable two-factor authentication.
                            </p>

                            <input
                              type="text"
                              inputMode="numeric"
                              autoComplete="one-time-code"
                              value={disableCode}
                              onChange={(e) => setDisableCode(e.target.value)}
                              placeholder="Enter verification code"
                              className="mt-4 w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100"
                            />

                            <div className="mt-4 flex flex-wrap gap-3">
                              <button
                                type="button"
                                onClick={handleDisableTwoFactor}
                                disabled={disableLoading}
                                className="cursor-pointer rounded-lg bg-red-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {disableLoading
                                  ? "Disabling..."
                                  : "Confirm Disable"}
                              </button>

                              <button
                                type="button"
                                onClick={handleCancelDisable}
                                disabled={disableLoading}
                                className="cursor-pointer rounded-lg border border-gray-300 bg-white px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                              >
                                Cancel
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