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
      <label htmlFor={id} className="block text-sm font-medium text-[#344056]">
        {label}
      </label>
      <textarea
        aria-describedby={helpId}
        className="mt-1 block w-full rounded-md border border-[#cbd5e1] bg-white px-3 py-2 text-[#172033] shadow-sm outline-none transition placeholder:text-[#8a95a6] focus:border-[#256f68] focus:ring-2 focus:ring-[#256f68]/20"
        id={id}
        name={name}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
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

export default TextAreaField;
