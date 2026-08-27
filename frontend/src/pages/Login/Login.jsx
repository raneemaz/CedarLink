import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "react-toastify";

import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [twoFactorRequired, setTwoFactorRequired] = useState(false);
  const [challengeToken, setChallengeToken] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [useRecoveryCode, setUseRecoveryCode] = useState(false);

  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const navigate = useNavigate();
  const { login } = useAuth();

  const redirectUser = (user) => {
    if (!user) {
      navigate("/");
      return;
    }

    if (user.role === "admin") {
      navigate("/admin/dashboard");
    } else if (user.role === "vendor") {
      navigate("/vendor/dashboard");
    } else {
      navigate("/");
    }
  };

  const handleLogin = async () => {
    if (!email || !password) {
      toast.error("Please enter both email and password.");
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/auth/login", {
        email,
        password,
      });

      console.log("Login response:", response.data);

      if (response.data.verification_required) {
        setChallengeToken(response.data.challenge_token);
        setTwoFactorRequired(true);

        toast.info("Verification is required.");
        return;
      }

      const userData =
        response.data.user ||
        response.data;

      const accessToken =
        response.data.access_token ||
        response.data.token;

      const refreshToken =
        response.data.refresh_token ||
        null;

      if (!userData) {
        toast.error("Login succeeded, but user information is missing.");
        return;
      }

      login(
        userData,
        accessToken,
        refreshToken
      );

      toast.success("Login successful!");
      redirectUser(userData);
    } catch (error) {
      console.log(error);

      const message =
        error.response?.data?.message ||
        error.message ||
        "Login failed.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyTwoFactor = async () => {
    if (!verificationCode) {
      toast.error(
        useRecoveryCode
          ? "Please enter a recovery code."
          : "Please enter the verification code."
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

      console.log("2FA verification response:", response.data);

      const userData =
        response.data.user ||
        response.data;

      const accessToken =
        response.data.access_token ||
        response.data.token;

      const refreshToken =
        response.data.refresh_token ||
        null;

      if (!userData) {
        toast.error("Verification succeeded, but user information is missing.");
        return;
      }

      login(
        userData,
        accessToken,
        refreshToken
      );

      toast.success("Verification successful!");
      redirectUser(userData);
    } catch (error) {
      console.log(error);

      const message =
        error.response?.data?.message ||
        error.message ||
        "Verification failed.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (!challengeToken) {
      toast.error("Your verification session is missing. Please log in again.");
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

      toast.success(
        response.data.message || "A new verification code was sent."
      );
    } catch (error) {
      console.log(error);

      const message =
        error.response?.data?.message ||
        error.message ||
        "Failed to resend the verification code.";

      toast.error(message);
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
            Two-Factor Authentication
          </h1>

          <p className="text-center text-sm text-gray-500 mt-2 mb-6">
            {useRecoveryCode
              ? "Enter one of your recovery codes to continue."
              : "Enter the verification code to complete your login."}
          </p>

          <Input
            label={
              useRecoveryCode
                ? "Recovery Code"
                : "Verification Code"
            }
            type="text"
            name="verificationCode"
            autoComplete="one-time-code"
            placeholder={
              useRecoveryCode
                ? "Enter your recovery code"
                : "Enter verification code"
            }
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
          />

          <Button
            className="w-full cursor-pointer mt-2"
            onClick={handleVerifyTwoFactor}
            disabled={loading}
          >
            {loading ? "Verifying..." : "Verify"}
          </Button>

          {!useRecoveryCode && (
            <button
              type="button"
              onClick={handleResendCode}
              disabled={resending}
              className="w-full mt-4 text-sm text-green-700 font-semibold hover:underline disabled:opacity-50"
            >
              {resending ? "Sending..." : "Resend verification code"}
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
              ? "Use a verification code instead"
              : "Use a recovery code instead"}
          </button>

          <button
            type="button"
            onClick={handleBackToLogin}
            className="w-full mt-5 text-sm text-gray-500 hover:underline"
          >
            Back to login
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
          Connect Customers & Local Vendors
        </p>

        <Input
          label="Email"
          type="email"
          name="email"
          autoComplete="username"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <Input
          label="Password"
          type="password"
          name="password"
          autoComplete="current-password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <Button
          className="w-full cursor-pointer mt-2"
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? "Logging in..." : "Login"}
        </Button>

        <p className="text-center text-sm text-gray-600 mt-5">
          Don't have an account?{" "}
          <Link
            to="/register"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            Register
          </Link>
        </p>
      </Card>
    </main>
  );
}

export default Login;