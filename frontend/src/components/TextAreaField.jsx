function TextAreaField({
  helpText,
  id,
  label,
  name,
  onChange,
  placeholder,
  rows = 4,
  value,
}) {
  const helpId = helpText ? `${id}-help` : undefined;

  return (
    <div>
      <label htmlFor={id} className="cf-label">
        {label}
      </label>
      <textarea
        aria-describedby={helpId}
        className="cf-input"
        id={id}
        name={name}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
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

export default TextAreaField;
