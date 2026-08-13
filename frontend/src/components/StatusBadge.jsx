const styles = {
  approved: "bg-[#ecfdf7] text-[#14534a] ring-[#9ed8cb]",
  pending: "bg-[#fff8e8] text-[#7a4b00] ring-[#f2cf82]",
  rejected: "bg-[#fff1f1] text-[#7f1d1d] ring-[#f5b5b5]",
  removed: "bg-[#f1f5f9] text-[#475569] ring-[#cbd5e1]",
  representative: "bg-[#eaf4ff] text-[#17466e] ring-[#a9ccef]",
  student: "bg-[#f1f5f9] text-[#344056] ring-[#cbd5e1]",
  default: "bg-[#ecfdf7] text-[#14534a] ring-[#9ed8cb]",
  optional: "bg-[#f8fafc] text-[#344056] ring-[#cbd5e1]",
  active: "bg-[#ecfdf7] text-[#14534a] ring-[#9ed8cb]",
  inactive: "bg-[#fff1f1] text-[#7f1d1d] ring-[#f5b5b5]",
};

function StatusBadge({ value }) {
  const label = String(value || "unknown").replaceAll("_", " ");

  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${
        styles[value] || "bg-white text-[#344056] ring-[#cbd5e1]"
      }`}
    >
      {label}
    </span>
  );
}

export default StatusBadge;
