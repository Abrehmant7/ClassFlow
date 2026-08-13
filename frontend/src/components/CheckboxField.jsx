function CheckboxField({ checked, helpText, id, label, name, onChange }) {
  return (
    <div className="flex gap-3 rounded-md border border-[#d8e1ed] bg-[#f8fafc] p-3">
      <input
        checked={checked}
        className="mt-1 h-4 w-4 rounded border-[#cbd5e1] text-[#256f68] focus:ring-[#256f68]"
        id={id}
        name={name}
        onChange={onChange}
        type="checkbox"
      />
      <div>
        <label htmlFor={id} className="text-sm font-medium text-[#344056]">
          {label}
        </label>
        {helpText ? (
          <p className="mt-1 text-xs leading-5 text-[#667085]">{helpText}</p>
        ) : null}
      </div>
    </div>
  );
}

export default CheckboxField;
