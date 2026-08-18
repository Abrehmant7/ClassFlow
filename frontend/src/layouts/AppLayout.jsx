import { useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";
import { getDisplayName } from "../utils/user.js";

const navItems = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "My Classes", to: "/classes" },
  { label: "Course Catalogue", to: "/courses" },
  { label: "Profile", to: "/profile" },
];

function navClass({ isActive }) {
  return [
    "flex items-center rounded-lg px-3 py-2 text-sm font-semibold transition cf-focus",
    isActive
      ? "bg-blue-50 text-blue-700"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");
}

function currentTitle(pathname) {
  if (pathname.startsWith("/classes")) return "Classes";
  if (pathname.startsWith("/courses")) return "Catalogue";
  if (pathname.startsWith("/profile")) return "Profile";
  if (pathname.startsWith("/tasks")) return "Task";
  return "Dashboard";
}

function NavigationLinks({ onNavigate }) {
  return (
    <div className="space-y-1">
      {navItems.map((item) => (
        <NavLink
          className={navClass}
          key={item.to}
          onClick={onNavigate}
          to={item.to}
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

function AccountBlock({ logout, user }) {
  return (
    <div className="border-t border-slate-200 pt-4">
      <div className="rounded-lg bg-slate-50 p-3">
        <p className="truncate text-sm font-semibold text-slate-900">
          {getDisplayName(user)}
        </p>
        <p className="mt-0.5 truncate text-xs text-slate-500">{user?.email}</p>
      </div>
      <button
        className="mt-2 flex w-full items-center rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 cf-focus"
        onClick={logout}
        type="button"
      >
        Log out
      </button>
    </div>
  );
}

function AppLayout() {
  const { isAuthenticated, logout, user } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const title = useMemo(() => currentTitle(location.pathname), [location.pathname]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-50">
        <header className="border-b border-slate-200 bg-white">
          <nav
            aria-label="Public navigation"
            className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
          >
            <Link className="flex items-center gap-3 cf-focus" to="/login">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
                CF
              </span>
              <span className="text-lg font-semibold text-slate-900">
                ClassFlow
              </span>
            </Link>
            <div className="flex items-center gap-2">
              <NavLink to="/login" className={navClass}>
                Log in
              </NavLink>
              <NavLink to="/register" className={navClass}>
                Register
              </NavLink>
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[272px_1fr]">
      <aside className="sticky top-0 hidden h-screen border-r border-slate-200 bg-white px-4 py-5 lg:flex lg:flex-col">
        <Link className="flex items-center gap-3 rounded-lg px-2 cf-focus" to="/dashboard">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
            CF
          </span>
          <div>
            <p className="text-sm font-bold text-slate-900">ClassFlow</p>
            <p className="text-xs text-slate-500">Academic workspace</p>
          </div>
        </Link>

        <Link
          className="mt-6 flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 cf-focus"
          to="/dashboard?newTask=1"
        >
          New personal task
        </Link>

        <nav aria-label="Main navigation" className="mt-6 flex-1">
          <NavigationLinks />
        </nav>

        <AccountBlock logout={logout} user={user} />
      </aside>

      <div className="lg:min-w-0">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <Link className="flex items-center gap-2 cf-focus" to="/dashboard">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
                CF
              </span>
              <span className="text-sm font-semibold text-slate-900">{title}</span>
            </Link>
            <button
              aria-expanded={drawerOpen}
              aria-label="Open navigation menu"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 cf-focus"
              onClick={() => setDrawerOpen(true)}
              type="button"
            >
              Menu
            </button>
          </div>
        </header>

        {drawerOpen ? (
          <div className="fixed inset-0 z-50 bg-slate-950/40 lg:hidden">
            <button
              aria-label="Close navigation menu"
              className="absolute inset-0 cursor-default"
              onClick={() => setDrawerOpen(false)}
              type="button"
            />
            <div className="relative flex h-full w-80 max-w-[85vw] flex-col bg-white p-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
                    CF
                  </span>
                  <span className="text-sm font-semibold text-slate-900">
                    ClassFlow
                  </span>
                </div>
                <button
                  className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 cf-focus"
                  onClick={() => setDrawerOpen(false)}
                  type="button"
                >
                  Close
                </button>
              </div>
              <Link
                className="mt-6 flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 cf-focus"
                onClick={() => setDrawerOpen(false)}
                to="/dashboard?newTask=1"
              >
                New personal task
              </Link>
              <nav aria-label="Mobile navigation" className="mt-6 flex-1">
                <NavigationLinks onNavigate={() => setDrawerOpen(false)} />
              </nav>
              <AccountBlock logout={logout} user={user} />
            </div>
          </div>
        ) : null}

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppLayout;
