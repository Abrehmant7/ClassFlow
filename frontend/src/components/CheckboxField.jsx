function CheckboxField({ checked, helpText, id, label, name, onChange }) {
  return (
    <div className="flex gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <input
        checked={checked}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600"
        id={id}
        name={name}
        onChange={onChange}
        type="checkbox"
      />
      <div>
        <label htmlFor={id} className="text-sm font-medium text-slate-700">
          {label}
        </label>
        {helpText ? (
          <p className="mt-1 text-xs leading-5 text-slate-500">{helpText}</p>
        ) : null}
      </div>
    </div>
  );
}

export default CheckboxField;
