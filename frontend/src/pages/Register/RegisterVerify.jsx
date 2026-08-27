import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import Button from "../../components/common/Button/Button";
import Input from "../../components/common/Input/Input";
import Card from "../../components/common/Card/Card";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

function RegisterVerify() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const verificationData = JSON.parse(
    sessionStorage.getItem("registration_verification") || "null"
  );

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const handleVerify = async () => {
    if (!verificationData?.challenge_token) {
      toast.error("Registration verification session not found.");
      navigate("/register");
      return;
    }

    if (!code.trim()) {
      toast.error("Please enter the verification code.");
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

      toast.success("Account verified successfully!");

      navigate("/");
    } catch (error) {
      console.error("Registration verification failed:", error);

      const message =
        error.response?.data?.message ||
        "Verification failed.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!verificationData?.challenge_token) {
      toast.error("Registration verification session not found.");
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
          "A new verification code was sent."
      );
    } catch (error) {
      console.error("Resending verification code failed:", error);

      const message =
        error.response?.data?.message ||
        "Unable to resend verification code.";

      toast.error(message);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-green-700">
          Verify Your Account
        </h1>

        <p className="text-center text-gray-500 mt-3 mb-8">
          Enter the verification code sent to your{" "}
          {verificationData?.method || "selected"} method.
        </p>

        <Input
          label="Verification Code"
          name="verification_code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="Enter verification code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-4"
          onClick={handleVerify}
          disabled={loading}
        >
          {loading ? "Verifying..." : "Verify & Continue"}
        </Button>

        <button
          type="button"
          onClick={handleResend}
          disabled={resending}
          className="w-full mt-4 text-green-700 font-semibold hover:underline disabled:opacity-50"
        >
          {resending
            ? "Sending..."
            : "Resend verification code"}
        </button>
      </Card>
    </div>
  );
}

export default RegisterVerify;