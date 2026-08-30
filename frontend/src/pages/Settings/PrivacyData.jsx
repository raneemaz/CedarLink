import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, PauseCircle, Trash2 } from "lucide-react";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import BackLink from "../../components/common/BackLink";

function getStoredUser() {
  const savedUser = localStorage.getItem("user");
  if (!savedUser || savedUser === "undefined") return null;
  try {
    return JSON.parse(savedUser);
  } catch {
    localStorage.removeItem("user");
    return null;
  }
}

/**
 * Shared re-auth panel: current password, plus a 2FA security challenge when
 * two-factor is enabled. Calls `onSubmit({ current_password, challenge_token,
 * code, use_recovery_code })` once the user has provided everything.
 */
function ReauthPanel({ userId, twoFactorEnabled, submitting, submitLabel, onSubmit, danger }) {
  const { t } = useTranslation();

  const [password, setPassword] = useState("");
  const [challengeToken, setChallengeToken] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);

  const btnClass = danger
    ? "bg-red-600 hover:bg-red-700"
    : "bg-emerald-700 hover:bg-emerald-800";
  const focusClass = danger
    ? "focus:border-red-500 focus:ring-red-100"
    : "focus:border-emerald-600 focus:ring-emerald-100";

  const startChallenge = async () => {
    if (!password) {
      toast.error(t("privacyData.enterPassword"));
      return;
    }
    setSending(true);
    try {
      const res = await api.post(`/users/${userId}/2fa/security-challenge`, {
        current_password: password,
      });
      const token = res.data?.challenge_token || "";
      if (!token) {
        toast.error(t("privacyData.challengeError"));
        return;
      }
      setChallengeToken(token);
      toast.success(res.data?.message || t("privacyData.codeSent"));
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("privacyData.challengeError"),
      );
    } finally {
      setSending(false);
    }
  };

  const submit = () => {
    if (!password) {
      toast.error(t("privacyData.enterPassword"));
      return;
    }
    if (twoFactorEnabled && (!challengeToken || !code.trim())) {
      toast.error(t("privacyData.enterCode"));
      return;
    }
    onSubmit({
      current_password: password,
      challenge_token: challengeToken || undefined,
      code: code.trim() || undefined,
      use_recovery_code: false,
    });
  };

  return (
    <div className="mt-4 space-y-3">
      <input
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder={t("privacyData.passwordPlaceholder")}
        className={`w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none focus:ring-2 ${focusClass}`}
      />

      {twoFactorEnabled && !challengeToken && (
        <button
          type="button"
          onClick={startChallenge}
          disabled={sending}
          className={`cursor-pointer rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition disabled:opacity-60 ${btnClass}`}
        >
          {sending
            ? t("privacyData.sending")
            : t("privacyData.sendCode")}
        </button>
      )}

      {twoFactorEnabled && challengeToken && (
        <input
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder={t("privacyData.codePlaceholder")}
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-gray-500 focus:ring-2 focus:ring-gray-100"
        />
      )}

      {(!twoFactorEnabled || challengeToken) && (
        <button
          type="button"
          onClick={submit}
          disabled={submitting}
          className={`cursor-pointer rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${btnClass}`}
        >
          {submitting ? t("privacyData.working") : submitLabel}
        </button>
      )}
    </div>
  );
}

function PrivacyData() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { logout } = useAuth();

  const storedUser = getStoredUser();
  const userId = storedUser?.id;

  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);

  const [showDeactivate, setShowDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  const [showDelete, setShowDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  useEffect(() => {
    if (!userId) {
      setStatusLoading(false);
      return;
    }
    api
      .get(`/users/${userId}/2fa`)
      .then((res) =>
        setTwoFactorEnabled(Boolean(res.data?.two_factor_enabled)),
      )
      .catch(() => {})
      .finally(() => setStatusLoading(false));
  }, [userId]);

  const handleDeactivate = async (payload) => {
    setDeactivating(true);
    try {
      await api.post(`/users/${userId}/deactivate`, payload);
      toast.success(t("privacyData.deactivatedToast"));
      logout();
      navigate("/login");
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("privacyData.actionError"),
      );
    } finally {
      setDeactivating(false);
    }
  };

  const handleDelete = async (payload) => {
    if (deleteConfirmText.trim().toUpperCase() !== "DELETE") {
      toast.error(t("privacyData.typeDelete"));
      return;
    }
    setDeleting(true);
    try {
      await api.delete(`/users/${userId}`, { data: payload });
      toast.success(t("privacyData.deletedToast"));
      logout();
      navigate("/");
    } catch (error) {
      toast.error(
        error.response?.data?.message || t("privacyData.actionError"),
      );
    } finally {
      setDeleting(false);
    }
  };

  if (!userId) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-red-700">{t("privacyData.loadError")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8">
          <BackLink onClick={() => navigate("/settings")} className="mb-4">
            {t("common.backToSettings")}
          </BackLink>

          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <ShieldCheck size={24} />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {t("privacyData.title")}
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                {t("privacyData.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {statusLoading ? (
          <p className="text-sm text-gray-500">{t("privacyData.loading")}</p>
        ) : (
          <div className="space-y-6">
            {/* Deactivate */}
            <section className="rounded-2xl border border-amber-200 bg-white p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <PauseCircle size={22} className="mt-0.5 text-amber-600" />
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {t("privacyData.deactivateTitle")}
                  </h2>
                  <p className="mt-1 text-sm text-gray-600">
                    {t("privacyData.deactivateDesc")}
                  </p>

                  {!showDeactivate ? (
                    <button
                      type="button"
                      onClick={() => setShowDeactivate(true)}
                      className="mt-4 cursor-pointer rounded-lg border border-amber-400 px-5 py-2.5 text-sm font-semibold text-amber-700 transition hover:bg-amber-50"
                    >
                      {t("privacyData.deactivateButton")}
                    </button>
                  ) : (
                    <ReauthPanel
                      userId={userId}
                      twoFactorEnabled={twoFactorEnabled}
                      submitting={deactivating}
                      submitLabel={t("privacyData.deactivateConfirm")}
                      onSubmit={handleDeactivate}
                    />
                  )}
                </div>
              </div>
            </section>

            {/* Delete */}
            <section className="rounded-2xl border border-red-200 bg-white p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <Trash2 size={22} className="mt-0.5 text-red-600" />
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {t("privacyData.deleteTitle")}
                  </h2>
                  <p className="mt-1 text-sm text-gray-600">
                    {t("privacyData.deleteDesc")}
                  </p>

                  <ul className="mt-3 list-disc space-y-1 ps-5 text-sm text-gray-500">
                    <li>{t("privacyData.deleteKept")}</li>
                    <li>{t("privacyData.deleteRemoved")}</li>
                    <li>{t("privacyData.deleteIrreversible")}</li>
                  </ul>

                  {!showDelete ? (
                    <button
                      type="button"
                      onClick={() => setShowDelete(true)}
                      className="mt-4 cursor-pointer rounded-lg border border-red-400 px-5 py-2.5 text-sm font-semibold text-red-600 transition hover:bg-red-50"
                    >
                      {t("privacyData.deleteButton")}
                    </button>
                  ) : (
                    <div className="mt-4">
                      <label className="block text-sm font-medium text-gray-700">
                        {t("privacyData.typeDeleteLabel")}
                      </label>
                      <input
                        type="text"
                        value={deleteConfirmText}
                        onChange={(e) =>
                          setDeleteConfirmText(e.target.value)
                        }
                        placeholder="DELETE"
                        className="mt-2 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-red-500 focus:ring-2 focus:ring-red-100"
                      />

                      <ReauthPanel
                        userId={userId}
                        twoFactorEnabled={twoFactorEnabled}
                        submitting={deleting}
                        submitLabel={t("privacyData.deleteConfirm")}
                        onSubmit={handleDelete}
                        danger
                      />
                    </div>
                  )}
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

export default PrivacyData;
