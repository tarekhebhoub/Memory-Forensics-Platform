import { useEffect, useState } from "react";
import { Download, RefreshCw, Plus } from "lucide-react";
import toast from "react-hot-toast";
import { Reports, Cases } from "../api/client";
import { Card, PageHeader, StatusPill, Empty } from "../components/ui.jsx";

export default function ReportsView() {
  const [items, setItems] = useState([]);
  const [cases, setCases] = useState([]);
  const [show, setShow] = useState(false);

  const reload = () => {
    Reports.list({ page_size: 100 }).then(d => setItems(d.results || []));
    Cases.list({ page_size: 200 }).then(d => setCases(d.results || []));
  };
  useEffect(() => {
    reload();
    const t = setInterval(reload, 5000);
    return () => clearInterval(t);
  }, []);

  const regen = async (id) => {
    try { await Reports.regenerate(id); toast.success("Regeneration queued"); reload(); }
    catch { toast.error("Failed"); }
  };

  return (
    <>
      <PageHeader title="Reports" subtitle="Investigation deliverables"
        actions={<button className="btn" onClick={() => setShow(true)}><Plus className="w-4 h-4" /> New report</button>} />

      {items.length === 0 ? <Empty>No reports yet.</Empty> : (
        <Card className="!p-0 overflow-hidden">
          <table className="table">
            <thead><tr>
              <th>Title</th><th>Case</th><th>Format</th><th>Status</th>
              <th>Created</th><th></th>
            </tr></thead>
            <tbody>
              {items.map(r => (
                <tr key={r.id}>
                  <td>{r.title}</td>
                  <td className="text-xs text-slate-400">#{r.case}</td>
                  <td className="uppercase text-xs">{r.format}</td>
                  <td><StatusPill value={r.status} /></td>
                  <td className="text-xs text-slate-400">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="text-right space-x-1 whitespace-nowrap">
                    <button className="btn-ghost" onClick={() => regen(r.id)}>
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                    {r.status === "ready" && (
                      <button className="btn" onClick={() => Reports.download(r.id, r.title || `report-${r.id}`)}>
                        <Download className="w-3.5 h-3.5" /> Download
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {show && <NewReportModal cases={cases} onClose={() => { setShow(false); reload(); }} />}
    </>
  );
}

function NewReportModal({ cases, onClose }) {
  const [form, setForm] = useState({ case: "", title: "", format: "pdf" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.case) return toast.error("Pick a case");
    setBusy(true);
    try { await Reports.create(form); toast.success("Report queued"); onClose(); }
    catch { toast.error("Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-30">
      <Card className="w-[440px] max-w-[95vw]">
        <form onSubmit={submit} className="space-y-3">
          <div className="font-semibold">New report</div>
          <select className="input" value={form.case} onChange={e => setForm({...form, case: e.target.value})}>
            <option value="">— select case —</option>
            {cases.map(c => <option key={c.id} value={c.id}>{c.code} — {c.title}</option>)}
          </select>
          <input className="input" placeholder="Title" value={form.title}
            onChange={e => setForm({...form, title: e.target.value})} required />
          <select className="input" value={form.format} onChange={e => setForm({...form, format: e.target.value})}>
            <option value="pdf">PDF</option>
            <option value="html">HTML</option>
          </select>
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn" disabled={busy}>{busy ? "Creating…" : "Create"}</button>
          </div>
        </form>
      </Card>
    </div>
  );
}
