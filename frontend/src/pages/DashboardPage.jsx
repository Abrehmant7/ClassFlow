import { useAuth } from "../auth/useAuth.js";
import { getDisplayName } from "../utils/user.js";

function DetailRow({ label, value }) {
  return (
    <div className="border-b border-[#e5eaf2] py-3 last:border-b-0 sm:grid sm:grid-cols-[160px_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-[#566176]">{label}</dt>
      <dd className="mt-1 text-sm text-[#172033] sm:mt-0">{value || "Not set"}</dd>
    </div>
  );
}

function DashboardPage() {
  const { user } = useAuth();

  return (
    <section className="space-y-6">
      <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-[#256f68]">
          Dashboard
        </p>
        <h1 className="mt-2 text-3xl font-bold text-[#172033]">
          Welcome, {getDisplayName(user)}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-[#566176]">
          Your authenticated profile is loaded from the FastAPI `/users/me`
          endpoint.
        </p>
      </div>

      <div className="rounded-md border border-[#dde4ef] bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-lg font-semibold text-[#172033]">Account</h2>
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

export default DashboardPage;
