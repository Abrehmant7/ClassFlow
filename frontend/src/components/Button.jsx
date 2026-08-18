const variants = {
  primary:
    "border-transparent bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300",
  secondary:
    "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 disabled:opacity-60",
  subtle:
    "border-transparent bg-transparent text-slate-600 hover:bg-slate-100 disabled:opacity-60",
  danger:
    "border-transparent bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
  ghost:
    "border-transparent bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-60",
};

function Button({
  children,
  className = "",
  type = "button",
  variant = "secondary",
  ...props
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold shadow-sm transition cf-focus disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
