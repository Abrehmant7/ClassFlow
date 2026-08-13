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
      <label htmlFor={id} className="block text-sm font-medium text-[#344056]">
        {label}
        {required ? <span className="text-[#b42318]"> *</span> : null}
      </label>
      <input
        autoComplete={autoComplete}
        aria-describedby={helpId}
        className="mt-1 block w-full rounded-md border border-[#cbd5e1] bg-white px-3 py-2 text-[#172033] shadow-sm outline-none transition placeholder:text-[#8a95a6] focus:border-[#256f68] focus:ring-2 focus:ring-[#256f68]/20"
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
        <p id={helpId} className="mt-1 text-xs text-[#667085]">
          {helpText}
        </p>
      ) : null}
    </div>
  );
}

export default FormField;
