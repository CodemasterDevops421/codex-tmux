import { ReactNode } from "react";
import clsx from "clsx";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx("rounded-2xl border border-base-700 bg-base-800/80 p-5 shadow-glow backdrop-blur", className)}>
      {children}
    </div>
  );
}

export function Badge({ text, tone = "slate" }: { text: string; tone?: "slate" | "cyan" | "lime" | "amber" | "pink" | "violet" }) {
  const toneMap: Record<string, string> = {
    slate: "bg-slate-700/40 text-slate-200",
    cyan: "bg-accent-cyan/20 text-accent-cyan",
    lime: "bg-accent-lime/20 text-accent-lime",
    amber: "bg-accent-amber/20 text-accent-amber",
    pink: "bg-accent-pink/20 text-accent-pink",
    violet: "bg-accent-violet/20 text-accent-violet"
  };
  return <span className={clsx("rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide", toneMap[tone])}>{text}</span>;
}

export function Button({ children, onClick, className }: { children: ReactNode; onClick?: () => void; className?: string }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "rounded-xl border border-base-700 bg-base-700/60 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-accent-cyan hover:text-accent-cyan",
        className
      )}
    >
      {children}
    </button>
  );
}

export function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase tracking-widest text-slate-400">{label}</div>
      <div className="text-2xl font-semibold text-white">{value}</div>
      {hint ? <div className="text-xs text-slate-400">{hint}</div> : null}
    </div>
  );
}
