import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, LifeBuoy, Moon, Sun, Upload } from "lucide-react";

function useTheme() {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark")
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      // Storage can be blocked in private mode; the theme still works for this session.
    }
  }, [dark]);

  return [dark, () => setDark((value) => !value)];
}

const NAV_ITEMS = [
  { to: "/", label: "New Ticket", icon: LifeBuoy, end: true },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/batch", label: "Batch Upload", icon: Upload },
];

export default function Layout() {
  const [dark, toggleTheme] = useTheme();

  const linkClass = ({ isActive }) =>
    `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive
        ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
        : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
    }`;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <LifeBuoy size={20} />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold">AI Support Desk</p>
              <p className="hidden text-xs text-slate-500 dark:text-slate-400 sm:block">
                Automated ticket triage and replies
              </p>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass}>
                <Icon size={16} />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="ml-2 rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>

      <footer className="pb-8 text-center text-xs text-slate-500 dark:text-slate-500">
        Built with FastAPI, LangChain and React
      </footer>
    </div>
  );
}
