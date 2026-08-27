import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

import Card from "../../components/common/Card/Card";
import Input from "../../components/common/Input/Input";
import Button from "../../components/common/Button/Button";
import api from "../../services/api";

function Register() {
  const navigate = useNavigate();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verificationMethod, setVerificationMethod] =
    useState("email");

  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (
      !firstName ||
      !lastName ||
      !email ||
      !phone ||
      !password ||
      !confirmPassword ||
      !verificationMethod
    ) {
      toast.error("Please fill in all fields.");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/auth/register", {
        first_name: firstName,
        last_name: lastName,
        email,
        phone,
        password,
        role: "customer",
        verification_method: verificationMethod,
      });

      if (!response.data?.challenge_token) {
        toast.error(
          "Unable to start account verification."
        );
        return;
      }

      sessionStorage.setItem(
        "registration_verification",
        JSON.stringify({
          challenge_token:
            response.data.challenge_token,
          method: response.data.method,
          email,
          phone,
          expires_at: response.data.expires_at,
        })
      );

      toast.success(
        response.data?.message ||
          "Verification code sent."
      );

      navigate("/register/verify");
    } catch (error) {
      console.error("Registration failed:", error);

      const message =
        error.response?.data?.message ||
        error.response?.data?.error ||
        "Registration failed.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <h1 className="text-4xl font-bold text-center text-green-700">
          CedarLink
        </h1>

        <p className="text-center text-gray-500 mt-2 mb-8">
          Create your account
        </p>

        <Input
          label="First Name"
          name="first_name"
          autoComplete="given-name"
          type="text"
          placeholder="Enter your first name"
          value={firstName}
          onChange={(e) =>
            setFirstName(e.target.value)
          }
        />

        <Input
          label="Last Name"
          name="last_name"
          autoComplete="family-name"
          type="text"
          placeholder="Enter your last name"
          value={lastName}
          onChange={(e) =>
            setLastName(e.target.value)
          }
        />

        <Input
          label="Email"
          name="email"
          autoComplete="email"
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) =>
            setEmail(e.target.value)
          }
        />

        <Input
          label="Phone"
          name="phone"
          autoComplete="tel"
          type="tel"
          placeholder="Enter your phone number"
          value={phone}
          onChange={(e) =>
            setPhone(e.target.value)
          }
        />

        <div className="mb-5">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Verification Method
          </label>

          <select
            value={verificationMethod}
            onChange={(e) =>
              setVerificationMethod(e.target.value)
            }
            className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
          >
            <option value="email">
              Email
            </option>

            <option value="sms">
              SMS
            </option>

            <option value="whatsapp">
              WhatsApp
            </option>
          </select>
        </div>

        <Input
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          placeholder="Create a password"
          value={password}
          onChange={(e) =>
            setPassword(e.target.value)
          }
        />

        <Input
          label="Confirm Password"
          name="confirm_password"
          autoComplete="new-password"
          type="password"
          placeholder="Confirm your password"
          value={confirmPassword}
          onChange={(e) =>
            setConfirmPassword(e.target.value)
          }
        />

        <Button
          className="w-full cursor-pointer"
          onClick={handleRegister}
          disabled={loading}
        >
          {loading
            ? "Creating Account..."
            : "Create Account"}
        </Button>

        <p className="text-center text-gray-600 mt-6">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-green-700 cursor-pointer font-semibold hover:underline"
          >
            Login
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default Register;