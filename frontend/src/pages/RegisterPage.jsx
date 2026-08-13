import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";
import Alert from "../components/Alert.jsx";
import FormField from "../components/FormField.jsx";
import { parseApiError } from "../utils/errors.js";

const initialForm = {
  username: "",
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  roll_number: "",
  semester: "",
  section: "",
};

function buildPayload(form) {
  const payload = {
    username: form.username.trim(),
    email: form.email.trim(),
    password: form.password,
  };

  [
    "first_name",
    "last_name",
    "roll_number",
    "section",
  ].forEach((field) => {
    const value = form[field].trim();
    if (value) {
      payload[field] = value;
    }
  });

  if (form.semester !== "") {
    payload.semester = Number(form.semester);
  }

  return payload;
}

function RegisterPage() {
  const { register } = useAuth();
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
      const user = await register(buildPayload(form));
      setSuccess(`${user.username} was registered successfully. You can log in now.`);
      setForm(initialForm);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-5xl">
      <div className="mb-8 max-w-2xl space-y-4">
        <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
          Create account
        </p>
        <h1 className="text-3xl font-bold text-[#172033] sm:text-4xl">
          Register for ClassFlow
        </h1>
        <p className="text-base leading-7 text-[#566176]">
          Required account fields match the FastAPI registration schema. Academic
          profile fields are optional.
        </p>
      </div>

      <form
        className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6"
        onSubmit={handleSubmit}
      >
        <div className="space-y-6">
          {error ? (
            <Alert
              title="Could not register"
              message={error.message}
              items={error.items}
            />
          ) : null}
          {success ? (
            <Alert type="success" title="Account created" message={success} />
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              autoComplete="username"
              id="register-username"
              label="Username"
              name="username"
              onChange={handleChange}
              placeholder="your_username"
              required
              value={form.username}
            />
            <FormField
              autoComplete="email"
              id="register-email"
              label="Email"
              name="email"
              onChange={handleChange}
              placeholder="you@example.com"
              required
              type="email"
              value={form.email}
            />
            <FormField
              autoComplete="new-password"
              id="register-password"
              label="Password"
              name="password"
              onChange={handleChange}
              required
              type="password"
              value={form.password}
            />
            <FormField
              autoComplete="given-name"
              id="first-name"
              label="First name"
              name="first_name"
              onChange={handleChange}
              value={form.first_name}
            />
            <FormField
              autoComplete="family-name"
              id="last-name"
              label="Last name"
              name="last_name"
              onChange={handleChange}
              value={form.last_name}
            />
            <FormField
              id="roll-number"
              label="Roll number"
              name="roll_number"
              onChange={handleChange}
              value={form.roll_number}
            />
            <FormField
              id="semester"
              inputMode="numeric"
              label="Semester"
              min="1"
              name="semester"
              onChange={handleChange}
              type="number"
              value={form.semester}
            />
            <FormField
              id="section"
              label="Section"
              name="section"
              onChange={handleChange}
              value={form.section}
            />
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-[#566176]">
              Already registered?{" "}
              <Link
                to="/login"
                className="font-semibold text-[#256f68] hover:text-[#1f5d58]"
              >
                Log in
              </Link>
            </p>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded-md bg-[#256f68] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#1f5d58] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-[#8ebbb5]"
            >
              {isSubmitting ? "Creating account..." : "Create account"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}

export default RegisterPage;
