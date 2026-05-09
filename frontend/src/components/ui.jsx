import clsx from "clsx";

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">{title}</h1>
        {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}

export function Severity({ value }) {
  const v = (value || "info").toLowerCase();
  const cls = {
    critical: "pill-critical", high: "pill-high", medium: "pill-medium",
    low: "pill-low", info: "pill-info",
  }[v] || "pill-info";
  return <span className={cls}>{v}</span>;
}

export function StatusPill({ value }) {
  const v = (value || "").toLowerCase();
  const map = {
    open: "bg-blue-500/20 text-blue-300",
    in_progress: "bg-amber-500/20 text-amber-300",
    on_hold: "bg-zinc-500/20 text-zinc-300",
    closed: "bg-emerald-500/20 text-emerald-300",
    archived: "bg-slate-700 text-slate-400",
    queued: "bg-blue-500/20 text-blue-300",
    running: "bg-amber-500/20 text-amber-300",
    completed: "bg-emerald-500/20 text-emerald-300",
    partial: "bg-yellow-500/20 text-yellow-300",
    failed: "bg-red-500/20 text-red-300",
    uploading: "bg-amber-500/20 text-amber-300",
    uploaded: "bg-blue-500/20 text-blue-300",
    verified: "bg-emerald-500/20 text-emerald-300",
    analyzing: "bg-amber-500/20 text-amber-300",
    analyzed: "bg-emerald-500/20 text-emerald-300",
    quarantined: "bg-red-500/20 text-red-300",
    ready: "bg-emerald-500/20 text-emerald-300",
    generating: "bg-amber-500/20 text-amber-300",
  };
  return (
    <span className={clsx("px-2 py-0.5 rounded text-xs font-semibold uppercase",
      map[v] || "bg-slate-700 text-slate-300")}>
      {v.replace(/_/g, " ")}
    </span>
  );
}

export function Card({ children, className }) {
  return <div className={clsx("card p-5", className)}>{children}</div>;
}

export function Empty({ children }) {
  return (
    <div className="text-center text-sm text-slate-400 py-12 border border-dashed border-ink-700 rounded">
      {children}
    </div>
  );
}

export function Stat({ label, value, accent }) {
  return (
    <Card className="!p-4">
      <div className="text-[10px] uppercase tracking-widest text-slate-400">{label}</div>
      <div className={clsx("text-2xl font-bold mt-1", accent || "text-accent")}>{value}</div>
    </Card>
  );
}
