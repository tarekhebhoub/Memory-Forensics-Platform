import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import toast from "react-hot-toast";
import { Cases } from "../api/client";
import { PageHeader, Card, Severity, StatusPill, Empty } from "../components/ui.jsx";
import { can, useAuth } from "../auth/AuthContext.jsx";

export default function CasesList() {
  const { user } = useAuth();
  const [data, setData] = useState({ results: [] });
  const [q, setQ] = useState("");
  const [showNew, setShowNew] = useState(false);

  const load = () => Cases.list({ search: q, page_size: 100 }).then(setData);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);

  return (
    <>
      <PageHeader
        title="Cases"
        subtitle="Active and historical investigations."
        actions={
          can(user, "write") && (
            <button className="btn" onClick={() => setShowNew(true)}>
              <Plus className="w-4 h-4" /> New case
            </button>
          )
        }
      />

      <Card className="!p-3 mb-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input className="input pl-9" placeholder="Search cases by code, title, description…"
                 value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </Card>

      <Card className="!p-0 overflow-hidden">
        {(data.results || []).length === 0 ? <div className="p-6"><Empty>No cases found.</Empty></div>
        : (
          <table className="table">
            <thead><tr>
              <th>Code</th><th>Title</th><th>Status</th><th>Severity</th>
              <th>Lead</th><th>Evidence</th><th>Opened</th>
            </tr></thead>
            <tbody>
              {data.results.map(c => (
                <tr key={c.id}>
                  <td className="font-mono">
                    <Link to={`/cases/${c.id}`} className="text-accent hover:underline">{c.code}</Link>
                  </td>
                  <td className="max-w-md truncate">{c.title}</td>
                  <td><StatusPill value={c.status} /></td>
                  <td><Severity value={c.severity} /></td>
                  <td>{c.lead_analyst?.username || "—"}</td>
                  <td>{c.evidence_count}</td>
                  <td className="text-slate-400 whitespace-nowrap">
                    {new Date(c.opened_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {showNew && <NewCaseModal onClose={() => setShowNew(false)} onCreated={load} />}
    </>
  );
}

function NewCaseModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    code: "", title: "", severity: "medium", classification: "TLP:AMBER", description: "",
  });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await Cases.create(form);
      toast.success("Case created.");
      onCreated();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail
        || JSON.stringify(err.response?.data || {})
        || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6">
      <div className="card w-full max-w-lg p-6">
        <h2 className="text-lg font-bold mb-4">New Case</h2>
        <form onSubmit={submit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Case code</label>
              <input className="input" required value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value })}
                placeholder="INC-2026-0001" />
            </div>
            <div>
              <label className="label">Severity</label>
              <select className="input" value={form.severity}
                onChange={e => setForm({ ...form, severity: e.target.value })}>
                {["low", "medium", "high", "critical"].map(s =>
                  <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Title</label>
            <input className="input" required value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })} />
          </div>
          <div>
            <label className="label">Classification</label>
            <input className="input" value={form.classification}
              onChange={e => setForm({ ...form, classification: e.target.value })} />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea className="input min-h-[80px]" value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn" disabled={busy}>{busy ? "Creating…" : "Create case"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
