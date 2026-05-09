import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FolderKanban, Activity, Clock, ShieldAlert,
  FileBarChart2, Users, ScrollText, LogOut, Cpu,
} from "lucide-react";
import { useAuth, can } from "../auth/AuthContext.jsx";

const NAV = [
  { to: "/",         label: "Dashboard", icon: LayoutDashboard },
  { to: "/cases",    label: "Cases",     icon: FolderKanban },
  { to: "/timeline", label: "Timeline",  icon: Clock },
  { to: "/iocs",     label: "IOCs",      icon: ShieldAlert },
  { to: "/reports",  label: "Reports",   icon: FileBarChart2 },
];

const ADMIN_NAV = [
  { to: "/users", label: "Users", icon: Users },
  { to: "/audit", label: "Audit", icon: ScrollText },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-64 shrink-0 bg-ink-800 border-r border-ink-700 flex flex-col">
        <div className="px-5 py-5 flex items-center gap-3 border-b border-ink-700">
          <Cpu className="w-7 h-7 text-accent" />
          <div>
            <div className="text-lg font-bold leading-tight">MFP</div>
            <div className="text-[10px] uppercase tracking-widest text-slate-500">
              Memory Forensics
            </div>
          </div>
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) =>
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition " +
                (isActive
                  ? "bg-accent text-ink-900 font-semibold"
                  : "text-slate-300 hover:bg-ink-700")
              }>
              <Icon className="w-4 h-4" /> {label}
            </NavLink>
          ))}

          {can(user, "admin") && (
            <>
              <div className="mt-6 mb-2 px-3 text-[10px] uppercase tracking-widest text-slate-500">
                Administration
              </div>
              {ADMIN_NAV.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to}
                  className={({ isActive }) =>
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition " +
                    (isActive
                      ? "bg-accent text-ink-900 font-semibold"
                      : "text-slate-300 hover:bg-ink-700")
                  }>
                  <Icon className="w-4 h-4" /> {label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        <div className="px-3 py-3 border-t border-ink-700">
          <div className="text-xs text-slate-400 mb-2">
            <div className="text-slate-200 font-semibold truncate">{user?.username}</div>
            <div className="capitalize">{user?.role}</div>
          </div>
          <button
            onClick={() => { logout(); nav("/login"); }}
            className="btn-ghost w-full justify-start">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1600px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
