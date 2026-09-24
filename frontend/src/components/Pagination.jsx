import Button from "./Button.jsx";

function Pagination({ page, totalPages, onChange, disabled = false }) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3">
      <Button disabled={disabled || page <= 1} onClick={() => onChange(page - 1)}>Previous</Button>
      <span className="text-sm text-slate-600">Page {page} of {totalPages}</span>
      <Button disabled={disabled || page >= totalPages} onClick={() => onChange(page + 1)}>Next</Button>
    </nav>
  );
}

export default Pagination;
