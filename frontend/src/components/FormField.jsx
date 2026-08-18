function FormField({
  autoComplete,
  helpText,
  id,
  inputMode,
  label,
  min,
  name,
  onChange,
  placeholder,
  required = false,
  type = "text",
  value,
}) {
  const helpId = helpText ? `${id}-help` : undefined;

  return (
    <div>
      <label htmlFor={id} className="cf-label">
        {label}
        {required ? <span className="text-red-600"> *</span> : null}
      </label>
      <input
        autoComplete={autoComplete}
        aria-describedby={helpId}
        className="cf-input"
        id={id}
        inputMode={inputMode}
        min={min}
        name={name}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        type={type}
        value={value}
      />
      {helpText ? (
        <p id={helpId} className="mt-1 text-xs text-slate-500">
          {helpText}
        </p>
      ) : null}
    </div>
  );
}

export default FormField;
