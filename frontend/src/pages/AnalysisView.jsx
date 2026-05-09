import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Analysis } from "../api/client";
import { Card, PageHeader, StatusPill, Empty } from "../components/ui.jsx";

export default function AnalysisView() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [active, setActive] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let t;
    const tick = () => {
      Analysis.job(jobId).then(j => {
        setJob(j);
        if (j.results?.length && !active) setActive(j.results[0].plugin);
      });
    };
    tick();
    t = setInterval(tick, 4000);
    return () => clearInterval(t);
  }, [jobId, active]);

  useEffect(() => {
    if (active) Analysis.pluginResult(jobId, active).then(setResult);
  }, [jobId, active]);

  if (!job) return <div className="text-slate-400">Loading…</div>;

  const riskColor =
    job.risk_score == null     ? "bg-ink-700" :
    job.risk_score >= 75       ? "bg-sev-critical" :
    job.risk_score >= 50       ? "bg-sev-high" :
    job.risk_score >= 25       ? "bg-sev-medium" : "bg-sev-low";

  return (
    <>
      <PageHeader
        title={`Analysis #${job.id}`}
        subtitle={`Evidence: `}
        actions={
          <div className="flex gap-2 items-center">
            <StatusPill value={job.status} />
            <span className={`px-2 py-1 rounded-md text-xs font-semibold ${
              job.mode === "deep" ? "bg-fuchsia-600 text-white" : "bg-ink-700 text-slate-300"}`}>
              {(job.mode || "standard").toUpperCase()}
            </span>
            <span className={`px-3 py-1 rounded-md text-white text-xs font-semibold ${riskColor}`}>
              Risk {job.risk_score ?? "—"}/100
            </span>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card>
          <div className="text-sm font-semibold mb-3">Job overview</div>
          <dl className="text-sm space-y-2">
            <Row k="Mode"        v={(job.mode || "standard").toUpperCase()} />
            <Row k="Detected OS" v={job.detected_os || "—"} />
            <Row k="Plugins"     v={(job.plugins || []).length} />
            <Row k="Detections"  v={(job.detections || []).length} />
            <Row k="Started"     v={job.started_at  ? new Date(job.started_at).toLocaleString()  : "—"} />
            <Row k="Finished"    v={job.finished_at ? new Date(job.finished_at).toLocaleString() : "—"} />
            <Row k="Triggered by" v={job.triggered_by?.username || "—"} />
            <Row k="Evidence"    v={<Link className="text-accent" to={`/evidence/${job.evidence}`}>#{job.evidence}</Link>} />
          </dl>
          {(job.mitre_techniques || []).length > 0 && (
            <div className="mt-4">
              <div className="text-xs text-slate-400 uppercase mb-2">MITRE ATT&CK techniques</div>
              <div className="flex flex-wrap gap-1">
                {job.mitre_techniques.map(t => (
                  <a key={t} target="_blank" rel="noreferrer"
                     href={`https://attack.mitre.org/techniques/${t.replace(".", "/")}/`}
                     className="px-1.5 py-0.5 rounded bg-ink-700 hover:bg-accent/30 text-[11px] font-mono text-slate-200">
                    {t}
                  </a>
                ))}
              </div>
            </div>
          )}
        </Card>
        <Card className="lg:col-span-2">
          <div className="text-sm font-semibold mb-3">
            Detections
            <span className="ml-2 text-xs text-slate-400">
              ({(job.detections || []).length})
            </span>
          </div>
          {(job.detections || []).length === 0
            ? <div className="text-sm text-slate-400">No findings reported yet.</div>
            : <DetectionsList detections={job.detections} />}
          {job.error && <div className="mt-4 text-xs text-red-300 whitespace-pre-wrap">{job.error}</div>}
        </Card>
      </div>

      <Card className="!p-0 overflow-hidden">
        <div className="flex border-b border-ink-700 overflow-x-auto">
          {(job.results || []).map(r => (
            <button key={r.plugin}
              onClick={() => setActive(r.plugin)}
              className={"px-4 py-2 text-xs whitespace-nowrap font-mono " +
                (active === r.plugin ? "bg-ink-700 text-accent" : "text-slate-300 hover:bg-ink-700/40")}>
              {r.plugin}
            </button>
          ))}
        </div>

        {!result ? <Empty>Select a plugin tab.</Empty> : <PluginResultView result={result} />}
      </Card>
    </>
  );
}

function PluginResultView({ result }) {
  const rows = Array.isArray(result.parsed_rows) ? result.parsed_rows : [];
  const cols = rows.length ? Object.keys(rows[0]) : [];

  return (
    <div className="p-4 space-y-4">
      {result.summary && Object.keys(result.summary).length > 0 && (
        <div>
          <div className="text-xs text-slate-400 uppercase mb-2">Summary</div>
          <pre className="text-xs bg-ink-900/60 rounded p-3 overflow-auto">
            {JSON.stringify(result.summary, null, 2)}
          </pre>
        </div>
      )}

      {rows.length > 0 && (
        <div>
          <div className="text-xs text-slate-400 uppercase mb-2">Rows ({rows.length})</div>
          <div className="overflow-auto max-h-[500px] border border-ink-700 rounded">
            <table className="table text-xs">
              <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>
                {rows.slice(0, 500).map((r, i) => (
                  <tr key={i}>{cols.map(c => <td key={c} className="font-mono">{String(r[c] ?? "")}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result.raw_output && (
        <details>
          <summary className="cursor-pointer text-xs text-slate-400 uppercase">Raw output</summary>
          <pre className="text-xs bg-ink-900/60 rounded p-3 overflow-auto max-h-[400px] mt-2">
            {result.raw_output}
          </pre>
        </details>
      )}
    </div>
  );
}

const Row = ({ k, v }) => (
  <div className="flex justify-between gap-4">
    <dt className="text-slate-400">{k}</dt>
    <dd className="text-slate-200 text-right">{v}</dd>
  </div>
);

const SEV_BG = {
  critical: "bg-sev-critical text-white",
  high:     "bg-sev-high text-white",
  medium:   "bg-sev-medium text-black",
  low:      "bg-sev-low text-black",
  info:     "bg-ink-700 text-slate-200",
};
const SEV_RANK = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

function DetectionsList({ detections }) {
  const sorted = [...detections].sort(
    (a, b) => (SEV_RANK[a.severity] ?? 9) - (SEV_RANK[b.severity] ?? 9)
  );
  return (
    <ul className="space-y-3 text-sm max-h-[480px] overflow-auto pr-2">
      {sorted.map((d, i) => (
        <li key={i} className="border border-ink-700 rounded-md p-3 bg-ink-900/40">
          <div className="flex items-start justify-between gap-3 mb-1">
            <div className="font-semibold text-slate-100">{d.title}</div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${SEV_BG[d.severity] || "bg-ink-700"}`}>
              {d.severity}
            </span>
          </div>
          <div className="text-xs text-slate-300 mb-2">{d.message}</div>
          <div className="flex flex-wrap gap-1 items-center text-[11px]">
            <span className="font-mono text-slate-400">{d.plugin}</span>
            {d.pid && <span className="text-slate-500">· PID {d.pid}</span>}
            {(d.mitre || []).map(t => (
              <a key={t} target="_blank" rel="noreferrer"
                 href={`https://attack.mitre.org/techniques/${t.replace(".", "/")}/`}
                 className="ml-1 px-1.5 py-0.5 rounded bg-accent/20 hover:bg-accent/40 font-mono text-slate-100">
                {t}
              </a>
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
