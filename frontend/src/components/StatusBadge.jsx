const variants = {
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  registered: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  urgent: "bg-amber-50 text-amber-700 ring-amber-200",
  high: "bg-amber-50 text-amber-700 ring-amber-200",
  overdue: "bg-red-50 text-red-700 ring-red-200",
  rejected: "bg-red-50 text-red-700 ring-red-200",
  removed: "bg-slate-100 text-slate-600 ring-slate-200",
  archived: "bg-slate-100 text-slate-600 ring-slate-200",
  inactive: "bg-slate-100 text-slate-600 ring-slate-200",
  cancelled: "bg-red-50 text-red-700 ring-red-200",
  representative: "bg-blue-50 text-blue-700 ring-blue-200",
  shared: "bg-blue-50 text-blue-700 ring-blue-200",
  course: "bg-blue-50 text-blue-700 ring-blue-200",
  student: "bg-slate-100 text-slate-600 ring-slate-200",
  personal: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  independent: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  default: "bg-cyan-50 text-cyan-700 ring-cyan-200",
  optional: "bg-slate-100 text-slate-600 ring-slate-200",
};

function StatusBadge({ value, subtle = false }) {
  const key = String(value || "unknown");
  const label = key.replaceAll("_", " ");
  const subtleClass = subtle
    ? "bg-transparent text-slate-500 ring-slate-200"
    : variants[key] || "bg-slate-100 text-slate-600 ring-slate-200";

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${subtleClass}`}
    >
      {label}
    </span>
  );
}

export default StatusBadge;
