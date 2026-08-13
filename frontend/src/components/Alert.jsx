function Alert({ type = "error", title, message, items = [] }) {
  const isError = type === "error";
  const classes = isError
    ? "border-[#f5b5b5] bg-[#fff1f1] text-[#7f1d1d]"
    : "border-[#9ed8cb] bg-[#ecfdf7] text-[#14534a]";

  return (
    <div className={`rounded-md border px-4 py-3 ${classes}`} role="alert">
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
