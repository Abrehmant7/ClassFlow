function Alert({ type = "error", title, message, items = [] }) {
  const classes = {
    error: "border-red-200 bg-red-50 text-red-700",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    info: "border-slate-200 bg-white text-slate-700",
  }[type] || "border-slate-200 bg-white text-slate-700";

  return (
    <div className={`rounded-lg border px-4 py-3 ${classes}`} role="alert">
      {title ? <p className="text-sm font-semibold">{title}</p> : null}
      {message ? <p className="mt-1 text-sm">{message}</p> : null}
      {items.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default Alert;
