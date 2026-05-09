import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import {
  Upload, Sparkles, FileText, ShieldCheck, Trash2, Brain,
  Loader2, History, Network,
} from "lucide-react";
import { Cases, Evidence, Reports, AI, IOCs, Timeline } from "../api/client";
import { Card, PageHeader, Severity, StatusPill, Empty } from "../components/ui.jsx";

const TABS = ["Overview", "Evidence", "IOCs", "Notes", "Timeline", "AI Insights", "Custody"];

export default function CaseDetail() {
  const { id } = useParams();
  const [cs, setCs] = useState(null);
  const [tab, setTab] = useState("Overview");
  const [evidence, setEvidence] = useState([]);
  const [iocs, setIocs] = useState([]);
  const [notes, setNotes] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [insights, setInsights] = useState([]);
  const [custody, setCustody] = useState([]);

  const reload = () => {
    Cases.get(id).then(setCs);
    Evidence.list({ case: id, page_size: 100 }).then(d => setEvidence(d.results || []));
    IOCs.list({ case: id, page_size: 200 }).then(d => setIocs(d.results || []));
    Cases.notes.list(id).then(d => setNotes(d.results || []));
    Timeline.list({ case: id, page_size: 200 }).then(d => setTimeline(d.results || []));
    AI.insights(id).then(d => setInsights(d.results || []));
    Cases.custody(id).then(setCustody);
  };
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [id]);

  if (!cs) return <div className="text-slate-400">Loading case…</div>;

  return (
    <>
      <PageHeader
        title={`${cs.code} — ${cs.title}`}
        subtitle={cs.description || "No description provided."}
        actions={
          <div className="flex gap-2 items-center">
            <Severity value={cs.severity} />
            <StatusPill value={cs.status} />
          </div>
        }
      />

      <div className="flex gap-1 border-b border-ink-700 mb-6 overflow-x-auto">
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={"px-4 py-2 text-sm whitespace-nowrap " +
              (tab === t ? "border-b-2 border-accent text-accent font-semibold"
                         : "text-slate-400 hover:text-slate-200")}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview"   && <OverviewTab cs={cs} reload={reload} />}
      {tab === "Evidence"   && <EvidenceTab caseObj={cs} items={evidence} reload={reload} />}
      {tab === "IOCs"       && <IocsTab items={iocs} />}
      {tab === "Notes"      && <NotesTab caseObj={cs} items={notes} reload={reload} />}
      {tab === "Timeline"   && <TimelineTab items={timeline} />}
      {tab === "AI Insights"&& <AITab caseId={id} items={insights} reload={reload} />}
      {tab === "Custody"    && <CustodyTab items={custody} />}
    </>
  );
}

// ─── Tabs ───────────────────────────────────────────────────────────
function OverviewTab({ cs, reload }) {
  const [busy, setBusy] = useState(false);
  const setStatus = async (s) => {
    setBusy(true);
    try { await Cases.setStatus(cs.id, s); toast.success("Status updated"); reload(); }
    catch { toast.error("Failed"); }
    finally { setBusy(false); }
  };
  const newReport = async (format) => {
    try {
      await Reports.create({ case: cs.id, title: `${cs.code} report`, format });
      toast.success(`Report (${format.toUpperCase()}) queued`);
    } catch { toast.error("Failed to queue report"); }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card>
        <div className="text-sm font-semibold mb-3">Case info</div>
        <dl className="text-sm space-y-2">
          <Row k="Code"           v={cs.code} />
          <Row k="Status"         v={<StatusPill value={cs.status} />} />
          <Row k="Severity"       v={<Severity value={cs.severity} />} />
          <Row k="Classification" v={cs.classification || "—"} />
          <Row k="Lead analyst"   v={cs.lead_analyst?.username || "—"} />
          <Row k="Created by"     v={cs.created_by?.username || "—"} />
          <Row k="Opened"         v={new Date(cs.opened_at).toLocaleString()} />
          <Row k="Updated"        v={new Date(cs.updated_at).toLocaleString()} />
        </dl>
      </Card>

      <Card>
        <div className="text-sm font-semibold mb-3">Workflow</div>
        <div className="flex flex-wrap gap-2">
          {["open", "in_progress", "on_hold", "closed", "archived"].map(s => (
            <button key={s} disabled={busy || cs.status === s}
              onClick={() => setStatus(s)}
              className={cs.status === s ? "btn" : "btn-ghost"}>
              {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <div className="text-sm font-semibold mb-3">Reporting</div>
        <div className="flex gap-2">
          <button className="btn" onClick={() => newReport("pdf")}>
            <FileText className="w-4 h-4" /> Generate PDF
          </button>
          <button className="btn-ghost" onClick={() => newReport("html")}>
            <FileText className="w-4 h-4" /> Generate HTML
          </button>
        </div>
        <div className="text-xs text-slate-400 mt-3">
          Reports are produced asynchronously. View them under <Link className="text-accent" to="/reports">Reports</Link>.
        </div>
      </Card>
    </div>
  );
}

const Row = ({ k, v }) => (
  <div className="flex justify-between gap-4">
    <dt className="text-slate-400">{k}</dt>
    <dd className="text-slate-200 text-right">{v}</dd>
  </div>
);

function EvidenceTab({ caseObj, items, reload }) {
  const fileRef = useRef();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);

  const upload = async (file) => {
    setBusy(true); setProgress(0);
    try {
      await Evidence.upload(caseObj.id, file, {
        onProgress: (e) => setProgress(Math.round((e.loaded / e.total) * 100)),
      });
      toast.success("Evidence uploaded.");
      reload();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally { setBusy(false); setProgress(0); }
  };

  const analyze = async (id) => {
    try { await Evidence.analyze(id); toast.success("Standard analysis queued."); reload(); }
    catch { toast.error("Failed"); }
  };
  const deepAnalyze = async (id) => {
    if (!window.confirm("Deep analysis runs ~25 plugins (kernel + persistence + credentials). It can take 10–30 minutes. Continue?")) return;
    try { await Evidence.deepAnalyze(id); toast.success("Deep analysis queued."); reload(); }
    catch { toast.error("Failed"); }
  };
  const verify = async (id) => {
    try {
      const r = await Evidence.verify(id);
      r.ok ? toast.success("Integrity OK") : toast.error("INTEGRITY MISMATCH");
      reload();
    } catch { toast.error("Failed"); }
  };
  const remove = async (id) => {
    if (!window.confirm("Delete this evidence?")) return;
    try { await Evidence.remove(id); reload(); } catch { toast.error("Failed"); }
  };

  return (
    <>
      <Card className="mb-6">
        <div className="flex items-center gap-3">
          <input ref={fileRef} type="file" className="hidden"
            onChange={e => e.target.files[0] && upload(e.target.files[0])} />
          <button className="btn" disabled={busy} onClick={() => fileRef.current?.click()}>
            <Upload className="w-4 h-4" />
            {busy ? `Uploading… ${progress}%` : "Upload memory dump"}
          </button>
          <span className="text-xs text-slate-400">
            Supported: .raw, .mem, .dmp, .lime, .vmem, .bin (and .gz/.zip/.7z/.xz/.bz2 wrappers).
          </span>
        </div>
        {busy && (
          <div className="mt-3 h-2 bg-ink-700 rounded overflow-hidden">
            <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
      </Card>

      {items.length === 0 ? <Empty>No evidence attached.</Empty> : (
        <Card className="!p-0 overflow-hidden">
          <table className="table">
            <thead><tr>
              <th>Name</th><th>Size</th><th>SHA-256</th><th>Status</th>
              <th>Uploaded</th><th></th>
            </tr></thead>
            <tbody>
              {items.map(ev => (
                <tr key={ev.id}>
                  <td>
                    <Link to={`/evidence/${ev.id}`} className="text-accent hover:underline">
                      {ev.name}
                    </Link>
                  </td>
                  <td>{(ev.size_bytes / (1024 * 1024)).toFixed(1)} MB</td>
                  <td className="font-mono text-xs">{ev.sha256?.slice(0, 16)}…</td>
                  <td><StatusPill value={ev.status} /></td>
                  <td className="text-slate-400 whitespace-nowrap">
                    {new Date(ev.uploaded_at).toLocaleString()}
                  </td>
                  <td className="space-x-1 text-right whitespace-nowrap">
                    <button className="btn-ghost" onClick={() => analyze(ev.id)}>
                      <Sparkles className="w-3.5 h-3.5" /> Analyze
                    </button>
                    <button className="btn-ghost text-fuchsia-300" onClick={() => deepAnalyze(ev.id)} title="Deep analysis (~25 plugins, kernel+persistence+credentials)">
                      <Sparkles className="w-3.5 h-3.5" /> Deep
                    </button>
                    <button className="btn-ghost" onClick={() => verify(ev.id)}>
                      <ShieldCheck className="w-3.5 h-3.5" /> Verify
                    </button>
                    <button className="btn-ghost text-red-300" onClick={() => remove(ev.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}

function IocsTab({ items }) {
  if (!items.length) return <Empty>No indicators yet.</Empty>;
  return (
    <Card className="!p-0 overflow-hidden">
      <table className="table">
        <thead><tr>
          <th>Kind</th><th>Value</th><th>Severity</th><th>Confidence</th>
          <th>Source</th><th>Description</th>
        </tr></thead>
        <tbody>
          {items.map(i => (
            <tr key={i.id}>
              <td className="uppercase text-xs">{i.kind}</td>
              <td className="font-mono">{i.value}</td>
              <td><Severity value={i.severity} /></td>
              <td>{i.confidence}%</td>
              <td className="text-xs">{i.source_plugin || "—"}</td>
              <td className="text-slate-400">{i.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function NotesTab({ caseObj, items, reload }) {
  const [text, setText] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    await Cases.notes.create({ case: caseObj.id, body: text });
    setText(""); reload();
  };
  return (
    <>
      <Card className="mb-6">
        <form onSubmit={submit} className="space-y-2">
          <textarea className="input min-h-[100px]" value={text}
            placeholder="Add a case note…"
            onChange={(e) => setText(e.target.value)} />
          <div className="flex justify-end">
            <button className="btn">Add note</button>
          </div>
        </form>
      </Card>
      {items.length === 0 ? <Empty>No notes yet.</Empty> : (
        <div className="space-y-3">
          {items.map(n => (
            <Card key={n.id}>
              <div className="text-xs text-slate-400 mb-1">
                {n.author_username} · {new Date(n.created_at).toLocaleString()}
              </div>
              <div className="whitespace-pre-wrap text-sm">{n.body}</div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function TimelineTab({ items }) {
  if (!items.length) return <Empty>No timeline events.</Empty>;
  return (
    <Card className="!p-0">
      <div className="max-h-[70vh] overflow-y-auto">
        {items.map(t => (
          <div key={t.id} className="px-4 py-3 border-b border-ink-700/60 flex gap-3">
            <div className="text-xs text-slate-400 w-44 shrink-0 font-mono">
              {t.occurred_at_text || (t.occurred_at && new Date(t.occurred_at).toLocaleString()) || "—"}
            </div>
            <div className="text-xs uppercase text-accent w-24 shrink-0">{t.kind}</div>
            <div className="flex-1">
              <div className="text-sm font-medium">{t.title}</div>
              <div className="text-xs text-slate-400">{t.description}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function AITab({ caseId, items, reload }) {
  const [busy, setBusy] = useState(null);
  const run = async (kind, fn) => {
    setBusy(kind);
    try { await fn(caseId); toast.success("AI insight ready"); reload(); }
    catch { toast.error("Failed"); }
    finally { setBusy(null); }
  };
  return (
    <>
      <div className="flex flex-wrap gap-2 mb-6">
        <button className="btn" onClick={() => run("sum", AI.summarize)}>
          {busy === "sum" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
          Summarise behaviour
        </button>
        <button className="btn-ghost" onClick={() => run("cls", AI.classify)}>
          {busy === "cls" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Network className="w-4 h-4" />}
          Classify threat
        </button>
        <button className="btn-ghost" onClick={() => run("rec", AI.recommend)}>
          {busy === "rec" ? <Loader2 className="w-4 h-4 animate-spin" /> : <History className="w-4 h-4" />}
          Recommend next steps
        </button>
      </div>

      {items.length === 0 ? <Empty>No AI insights yet.</Empty> : (
        <div className="space-y-3">
          {items.map(i => (
            <Card key={i.id}>
              <div className="flex justify-between items-center mb-2">
                <div className="font-semibold">{i.title}</div>
                <div className="text-xs text-slate-400">
                  {i.model_used} · {new Date(i.created_at).toLocaleString()}
                </div>
              </div>
              <pre className="whitespace-pre-wrap text-sm text-slate-200">{i.content}</pre>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function CustodyTab({ items }) {
  if (!items.length) return <Empty>No custody entries.</Empty>;
  return (
    <Card className="!p-0">
      <table className="table">
        <thead><tr>
          <th>Time</th><th>Actor</th><th>Action</th><th>Description</th>
        </tr></thead>
        <tbody>
          {items.map(c => (
            <tr key={c.id}>
              <td className="text-xs whitespace-nowrap">
                {new Date(c.timestamp).toLocaleString()}
              </td>
              <td>{c.actor_username || "system"}</td>
              <td className="text-xs uppercase">{c.action}</td>
              <td className="text-slate-300">{c.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
