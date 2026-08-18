import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import FormField from "../components/FormField.jsx";
import PageHeader from "../components/PageHeader.jsx";
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
      <PageHeader
        description="Continue with the account you registered in the ClassFlow backend."
        eyebrow="Welcome back"
        title="Sign in to ClassFlow"
      />

      <form
        className="cf-card p-5 sm:p-6"
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

          <Button className="w-full" disabled={isSubmitting} type="submit" variant="primary">
            {isSubmitting ? "Signing in..." : "Log in"}
          </Button>

          <p className="text-center text-sm text-slate-500">
            Need an account?{" "}
            <Link
              to="/register"
              className="font-semibold text-blue-700 hover:text-blue-900 cf-focus"
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
