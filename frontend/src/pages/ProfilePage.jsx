import { useEffect, useMemo, useState } from "react";

import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import FormField from "../components/FormField.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { useAuth } from "../auth/useAuth.js";
import { parseApiError } from "../utils/errors.js";
import { getDisplayName } from "../utils/user.js";

function DetailRow({ label, value }) {
  return (
    <div className="min-w-0 border-b border-slate-200 py-3 last:border-b-0 sm:grid sm:grid-cols-[120px_minmax(0,1fr)] sm:gap-4 xl:grid-cols-[160px_minmax(0,1fr)]">
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 min-w-0 overflow-wrap-anywhere break-words text-sm text-slate-900 sm:mt-0">
        {value || "Not set"}
      </dd>
    </div>
  );
}

function getInitialForm(user) {
  return {
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    roll_number: user?.roll_number || "",
    semester: user?.semester ? String(user.semester) : "",
    section: user?.section || "",
  };
}

function cleanOptionalText(value) {
  const trimmed = value.trim();
  return trimmed || null;
}

function ProfilePage() {
  const { updateProfile, user } = useAuth();
  const [form, setForm] = useState(() => getInitialForm(user));
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setForm(getInitialForm(user));
  }, [user]);

  const isDirty = useMemo(() => {
    const initial = getInitialForm(user);
    return Object.keys(initial).some((key) => initial[key] !== form[key]);
  }, [form, user]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleReset() {
    setForm(getInitialForm(user));
    setError(null);
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess("");

    try {
      await updateProfile({
        first_name: cleanOptionalText(form.first_name),
        last_name: cleanOptionalText(form.last_name),
        roll_number: cleanOptionalText(form.roll_number),
        semester: form.semester ? Number(form.semester) : null,
        section: cleanOptionalText(form.section),
      });
      setSuccess("Your profile was updated.");
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="space-y-6">
      <PageHeader
        description="Keep your ClassFlow identity accurate for classmates and representatives."
        eyebrow="Profile"
        title={getDisplayName(user)}
      />

      {error ? (
        <Alert
          title="Could not update profile"
          message={error.message}
          items={error.items}
        />
      ) : null}
      {success ? <Alert type="success" title="Saved" message={success} /> : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <form className="cf-card p-5 sm:p-6" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1">
            <h2 className="text-lg font-semibold text-slate-900">
              Edit Profile
            </h2>
            <p className="text-sm leading-6 text-slate-500">
              Username and email are fixed by the current backend contract.
            </p>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <FormField
              autoComplete="given-name"
              id="profile-first-name"
              label="First name"
              name="first_name"
              onChange={handleChange}
              value={form.first_name}
            />
            <FormField
              autoComplete="family-name"
              id="profile-last-name"
              label="Last name"
              name="last_name"
              onChange={handleChange}
              value={form.last_name}
            />
            <FormField
              autoComplete="off"
              id="profile-roll-number"
              label="Roll number"
              name="roll_number"
              onChange={handleChange}
              value={form.roll_number}
            />
            <FormField
              id="profile-section"
              label="Section"
              name="section"
              onChange={handleChange}
              value={form.section}
            />
            <FormField
              id="profile-semester"
              inputMode="numeric"
              label="Semester"
              min="1"
              name="semester"
              onChange={handleChange}
              type="number"
              value={form.semester}
            />
          </div>

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              disabled={!isDirty || isSubmitting}
              onClick={handleReset}
              type="button"
            >
              Reset
            </Button>
            <Button
              disabled={!isDirty || isSubmitting}
              type="submit"
              variant="primary"
            >
              {isSubmitting ? "Saving..." : "Save changes"}
            </Button>
          </div>
        </form>

        <div className="space-y-6">
          <section className="cf-card p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-900">Account</h2>
            <dl className="mt-4">
              <DetailRow label="Username" value={user?.username} />
              <DetailRow label="Email" value={user?.email} />
              <DetailRow label="Full name" value={getDisplayName(user)} />
              <DetailRow label="Roll number" value={user?.roll_number} />
              <DetailRow label="Semester" value={user?.semester} />
              <DetailRow label="Section" value={user?.section} />
            </dl>
          </section>

          <section className="cf-card p-5 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-900">
              Password Reset
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              This frontend checkout does not expose a password reset endpoint
              yet, so no reset request is sent from this screen.
            </p>
            <Button className="mt-4 w-full" disabled>
              Reset password unavailable
            </Button>
          </section>
        </div>
      </div>
    </section>
  );
}

export default ProfilePage;
