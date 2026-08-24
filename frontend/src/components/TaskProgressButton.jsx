function TaskProgressButton({ checked, disabled, isBusy, onClick }) {
  return (
    <button
      aria-label={checked ? "Mark task pending" : "Mark task complete"}
      aria-pressed={checked}
      className={`flex h-5 w-5 items-center justify-center rounded border text-xs font-bold transition cf-focus ${
        checked
          ? "border-emerald-600 bg-emerald-600 text-white"
          : "border-slate-300 bg-white text-transparent hover:border-blue-600 hover:text-blue-600"
      } disabled:cursor-not-allowed disabled:opacity-60`}
      disabled={disabled || isBusy}
      onClick={onClick}
      type="button"
    >
      <span aria-hidden="true">{"\u2713"}</span>
    </button>
  );
}

export default TaskProgressButton;
