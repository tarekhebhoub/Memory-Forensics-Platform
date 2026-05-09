import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ShieldCheck, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import { Evidence, Analysis } from "../api/client";
import { Card, PageHeader, StatusPill, Empty } from "../components/ui.jsx";

export default function EvidenceView() {
  const { id } = useParams();
  const [ev, setEv] = useState(null);
  const [jobs, setJobs] = useState([]);

  const load = () => {
    Evidence.get(id).then(setEv);
    Analysis.jobs({ evidence: id, page_size: 50 }).then(d => setJobs(d.results || []));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  if (!ev) return <div className="text-slate-400">Loading…</div>;

  const verify = async () => {
    try {
      const r = await Evidence.verify(id);
      r.ok ? toast.success("Integrity verified") : toast.error("HASH MISMATCH");
      load();
    } catch { toast.error("Failed"); }
  };
  const analyze = async () => {
    try { await Evidence.analyze(id); toast.success("Standard analysis queued"); load(); }
    catch { toast.error("Failed"); }
  };
  const deepAnalyze = async () => {
    if (!window.confirm("Deep analysis runs ~25 plugins (kernel + persistence + credentials). It can take 10–30 minutes. Continue?")) return;
    try { await Evidence.deepAnalyze(id); toast.success("Deep analysis queued"); load(); }
    catch { toast.error("Failed"); }
  };

  return (
    <>
      <PageHeader
        title={ev.name}
        subtitle={`Evidence in case `}
        actions={
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={verify}>
              <ShieldCheck className="w-4 h-4" /> Verify
            </button>
            <button className="btn" onClick={analyze}>
              <Sparkles className="w-4 h-4" /> Run analysis
            </button>
            <button className="btn bg-fuchsia-600 hover:bg-fuchsia-500" onClick={deepAnalyze}
                    title="~25 plugins: kernel callbacks, SSDT, drivers, registry, credentials">
              <Sparkles className="w-4 h-4" /> Deep analysis
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <div className="text-sm font-semibold mb-3">Metadata</div>
          <dl className="text-sm space-y-2">
            <Row k="Status"  v={<StatusPill value={ev.status} />} />
            <Row k="Kind"    v={ev.kind} />
            <Row k="Size"    v={`${(ev.size_bytes / (1024 * 1024)).toFixed(2)} MB`} />
            <Row k="OS hint" v={ev.os_hint || "—"} />
            <Row k="Uploaded" v={new Date(ev.uploaded_at).toLocaleString()} />
            <Row k="Uploader" v={ev.uploaded_by?.username || "—"} />
            <Row k="Case"    v={<Link className="text-accent" to={`/cases/${ev.case}`}>#{ev.case}</Link>} />
          </dl>
        </Card>
        <Card>
          <div className="text-sm font-semibold mb-3">Integrity</div>
          <dl className="text-sm space-y-2">
            <Row k="SHA-256" v={<code className="font-mono text-[11px] break-all">{ev.sha256}</code>} />
            <Row k="MD5"     v={<code className="font-mono text-[11px] break-all">{ev.md5 || "—"}</code>} />
            <Row k="Verified at" v={ev.verified_at ? new Date(ev.verified_at).toLocaleString() : "—"} />
          </dl>
        </Card>
      </div>

      <Card className="!p-0 overflow-hidden">
        <div className="px-4 py-3 text-sm font-semibold border-b border-ink-700">Analysis jobs</div>
        {jobs.length === 0 ? <Empty>No analyses yet.</Empty> : (
          <table className="table">
            <thead><tr>
              <th>Job</th><th>Status</th><th>Risk</th><th>OS</th><th>Started</th><th>Finished</th>
            </tr></thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id}>
                  <td><Link to={`/analysis/${j.id}`} className="text-accent hover:underline">#{j.id}</Link></td>
                  <td><StatusPill value={j.status} /></td>
                  <td>{j.risk_score ?? "—"}</td>
                  <td>{j.detected_os || "—"}</td>
                  <td className="text-slate-400 text-xs">{j.started_at ? new Date(j.started_at).toLocaleString() : "—"}</td>
                  <td className="text-slate-400 text-xs">{j.finished_at ? new Date(j.finished_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}

const Row = ({ k, v }) => (
  <div className="flex justify-between gap-4">
    <dt className="text-slate-400">{k}</dt>
    <dd className="text-slate-200 text-right">{v}</dd>
  </div>
);
