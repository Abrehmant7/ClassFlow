import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";

const linkClass = ({ isActive }) =>
  [
    "rounded-md px-3 py-2 text-sm font-medium transition",
    isActive
      ? "bg-[#172033] text-white"
      : "text-[#344056] hover:bg-[#e8edf5] hover:text-[#172033]",
  ].join(" ");

function AppLayout() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <div className="min-h-screen bg-[#f7f8fb]">
      <header className="border-b border-[#dde4ef] bg-white">
        <nav
          className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"
          aria-label="Main navigation"
        >
          <Link to="/dashboard" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#256f68] text-sm font-bold text-white">
              CF
            </span>
            <span className="text-lg font-semibold text-[#172033]">
              ClassFlow
            </span>
          </Link>

          <div className="flex flex-wrap items-center gap-2">
            {isAuthenticated ? (
              <>
                <NavLink to="/dashboard" className={linkClass}>
                  Dashboard
                </NavLink>
                <NavLink to="/classes" className={linkClass}>
                  My Classes
                </NavLink>
                <NavLink to="/courses" className={linkClass}>
                  Catalogue
                </NavLink>
                <span className="hidden text-sm text-[#667085] sm:inline">
                  {user?.username}
                </span>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-md border border-[#cbd5e1] px-3 py-2 text-sm font-medium text-[#344056] transition hover:border-[#8ea0b8] hover:bg-[#f1f5f9] focus:outline-none focus:ring-2 focus:ring-[#256f68] focus:ring-offset-2"
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={linkClass}>
                  Log in
                </NavLink>
                <NavLink to="/register" className={linkClass}>
                  Register
                </NavLink>
              </>
            )}
          </div>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
