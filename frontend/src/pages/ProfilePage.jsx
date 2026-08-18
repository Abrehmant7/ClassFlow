import { useAuth } from "../auth/useAuth.js";
import PageHeader from "../components/PageHeader.jsx";
import { getDisplayName } from "../utils/user.js";

function DetailRow({ label, value }) {
  return (
    <div className="border-b border-slate-200 py-3 last:border-b-0 sm:grid sm:grid-cols-[160px_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-slate-900 sm:mt-0">
        {value || "Not set"}
      </dd>
    </div>
  );
}

function ProfilePage() {
  const { user } = useAuth();

  return (
    <section className="space-y-6">
      <PageHeader
        description="Your authenticated account details from ClassFlow."
        eyebrow="Profile"
        title={getDisplayName(user)}
      />

      <div className="cf-card p-5 sm:p-6">
        <h2 className="text-lg font-semibold text-slate-900">Account</h2>
        <dl className="mt-4">
          <DetailRow label="Username" value={user?.username} />
          <DetailRow label="Email" value={user?.email} />
          <DetailRow label="First name" value={user?.first_name} />
          <DetailRow label="Last name" value={user?.last_name} />
          <DetailRow label="Roll number" value={user?.roll_number} />
          <DetailRow label="Semester" value={user?.semester} />
          <DetailRow label="Section" value={user?.section} />
        </dl>
      </div>
    </section>
  );
}

export default ProfilePage;
