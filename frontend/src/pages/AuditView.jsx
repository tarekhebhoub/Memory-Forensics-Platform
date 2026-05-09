import { useEffect, useState } from "react";
import { Audit } from "../api/client";
import { Card, PageHeader, Empty } from "../components/ui.jsx";

export default function AuditView() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");

  useEffect(() => {
    Audit.list({ search: q, action: action || undefined, page_size: 200 })
      .then(d => setItems(d.results || []));
  }, [q, action]);

  return (
    <>
      <PageHeader title="Audit log" subtitle="Immutable record of platform activity" />

      <Card className="mb-6">
        <div className="flex flex-wrap gap-3">
          <input className="input flex-1 min-w-[220px]" placeholder="Search target/path/IP…"
            value={q} onChange={e => setQ(e.target.value)} />
          <select className="input w-48" value={action} onChange={e => setAction(e.target.value)}>
            <option value="">All actions</option>
            {["create","read","update","delete","login","logout","upload","download","analyze","report","permission"].map(a =>
              <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      </Card>

      {items.length === 0 ? <Empty>No audit events.</Empty> : (
        <Card className="!p-0 overflow-hidden">
          <table className="table">
            <thead><tr>
              <th>Time</th><th>Actor</th><th>Action</th><th>Target</th>
              <th>IP</th><th>Path</th><th>Status</th>
            </tr></thead>
            <tbody>
              {items.map(e => (
                <tr key={e.id}>
                  <td className="text-xs whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="text-xs">{e.actor_username || "anonymous"}</td>
                  <td className="text-xs uppercase text-accent">{e.action}</td>
                  <td className="text-xs">{e.target_type}{e.target_id ? `#${e.target_id}` : ""}</td>
                  <td className="text-xs font-mono text-slate-400">{e.ip_address || "—"}</td>
                  <td className="text-xs font-mono text-slate-400">{e.path}</td>
                  <td className="text-xs">{e.status_code || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
