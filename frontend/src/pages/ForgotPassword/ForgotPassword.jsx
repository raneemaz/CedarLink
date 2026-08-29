import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import api from "../../services/api";

// Shown after every submission, whether or not the email is registered —
// the backend response is identical either way (no account enumeration).
const CONFIRMATION =
  "If an account exists for that email, we've sent a password reset code.";

function ForgotPassword() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) {
      toast.error("Please enter your email.");
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

      toast.success(CONFIRMATION);

      navigate("/reset-password");
    } catch (error) {
      console.error("Password reset request failed:", error);

      const message =
        error.response?.data?.message ||
        "Unable to start a password reset.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-green-700">
          Forgot Your Password?
        </h1>

        <p className="text-center text-gray-500 mt-3 mb-8">
          Enter your account email and we'll send you a reset code.
        </p>

        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-2"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? "Sending..." : "Send reset code"}
        </Button>

        <p className="text-center text-gray-600 mt-6">
          Remembered it?{" "}
          <Link
            to="/login"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            Back to login
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default ForgotPassword;
