import { NavLink } from "react-router-dom";

function Tabs({ items }) {
  return (
    <div className="border-b border-slate-200">
      <nav aria-label="Section navigation" className="-mb-px flex gap-1 overflow-x-auto">
        {items.map((item) => (
          <NavLink
            className={({ isActive }) =>
              [
                "whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold transition cf-focus",
                isActive
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-900",
              ].join(" ")
            }
            end={item.end}
            key={item.to}
            to={item.to}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default Tabs;
