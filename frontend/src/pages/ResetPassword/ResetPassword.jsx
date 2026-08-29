import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import api from "../../services/api";

function ResetPassword() {
  const navigate = useNavigate();

  const resetData = JSON.parse(
    sessionStorage.getItem("password_reset") || "null"
  );

  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleReset = async () => {
    if (!resetData?.challenge_token) {
      toast.error("Password reset session not found.");
      navigate("/forgot-password");
      return;
    }

    if (!code.trim()) {
      toast.error("Please enter the reset code.");
      return;
    }

    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match.");
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

      toast.success("Your password has been reset. You can sign in now.");

      navigate("/login");
    } catch (error) {
      console.error("Password reset failed:", error);

      const message =
        error.response?.data?.message ||
        "Password reset failed.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-green-700">
          Reset Your Password
        </h1>

        <p className="text-center text-gray-500 mt-3 mb-8">
          Enter the code sent to{" "}
          {resetData?.email || "your email"} and choose a new password.
        </p>

        <Input
          label="Reset Code"
          name="reset_code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="Enter reset code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />

        <Input
          label="New Password"
          name="new_password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 8 characters"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />

        <Input
          label="Confirm New Password"
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          placeholder="Re-enter your new password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-2"
          onClick={handleReset}
          disabled={loading}
        >
          {loading ? "Resetting..." : "Reset password"}
        </Button>

        <p className="text-center text-gray-600 mt-6">
          Didn't get a code?{" "}
          <Link
            to="/forgot-password"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            Request a new one
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default ResetPassword;
