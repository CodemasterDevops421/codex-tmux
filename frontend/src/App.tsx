import { useEffect } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Jobs from "./pages/Jobs";
import JobDetail from "./pages/JobDetail";
import Agents from "./pages/Agents";

const navItems = [
  { path: "/", label: "Dashboard" },
  { path: "/jobs", label: "Jobs" },
  { path: "/agents", label: "Agents" }
];

export default function App() {
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "g") {
        const next = (e: KeyboardEvent) => {
          if (e.key.toLowerCase() === "d") navigate("/");
          if (e.key.toLowerCase() === "j") navigate("/jobs");
          if (e.key.toLowerCase() === "a") navigate("/agents");
          window.removeEventListener("keydown", next);
        };
        window.addEventListener("keydown", next);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);

  return (
    <div className="min-h-screen text-slate-100">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <div>
          <div className="text-xs uppercase tracking-[0.4em] text-accent-cyan">Codex Control Tower</div>
          <div className="text-2xl font-semibold">Real-time agent telemetry</div>
        </div>
        <nav className="flex items-center gap-3">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-accent-cyan/20 text-accent-cyan" : "text-slate-200 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl px-6 pb-12">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/agents" element={<Agents />} />
        </Routes>
      </main>
    </div>
  );
}
