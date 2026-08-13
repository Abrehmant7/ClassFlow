import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";
import Alert from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import { parseApiError } from "../utils/errors.js";

const initialForm = {
  username: "",
  password: "",
};

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname || "/dashboard";
  const [form, setForm] = useState(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess("");

    try {
      await login({
        username: form.username.trim(),
        password: form.password,
      });
      setSuccess("Login successful. Redirecting...");
      window.setTimeout(() => navigate(redirectTo, { replace: true }), 300);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
      <div className="space-y-4">
        <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
          Welcome back
        </p>
        <h1 className="text-3xl font-bold text-[#172033] sm:text-4xl">
          Sign in to ClassFlow
        </h1>
        <p className="max-w-xl text-base leading-7 text-[#566176]">
          Continue with the account you registered in the ClassFlow backend.
        </p>
      </div>

      <form
        className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6"
        onSubmit={handleSubmit}
      >
        <div className="space-y-5">
          {error ? (
            <Alert title="Could not log in" message={error.message} items={error.items} />
          ) : null}
          {success ? (
            <Alert type="success" title="Signed in" message={success} />
          ) : null}

          <FormField
            autoComplete="username"
            id="username"
            label="Username"
            name="username"
            onChange={handleChange}
            placeholder="your_username"
            required
            value={form.username}
          />

          <FormField
            autoComplete="current-password"
            id="password"
            label="Password"
            name="password"
            onChange={handleChange}
            required
            type="password"
            value={form.password}
          />

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center rounded-md bg-[#256f68] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
          >
            {isSubmitting ? "Signing in..." : "Log in"}
          </button>

          <p className="text-center text-sm text-[#566176]">
            Need an account?{" "}
            <Link
              to="/register"
              className="font-semibold text-[#256f68] hover:text-[#1f5d58]"
            >
              Register
            </Link>
          </p>
        </div>
      </form>
    </section>
  );
}

export default LoginPage;
