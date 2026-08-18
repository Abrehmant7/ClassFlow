function EmptyState({ title, message, action }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white px-5 py-8 text-center">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      {message ? (
        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
          {message}
        </p>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export default EmptyState;
