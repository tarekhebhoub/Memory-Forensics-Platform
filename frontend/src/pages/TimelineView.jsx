import { useEffect, useState } from "react";
import { Timeline } from "../api/client";
import { Card, PageHeader, Empty, Severity } from "../components/ui.jsx";

export default function TimelineView() {
  const [items, setItems] = useState([]);
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    Timeline.list({ search: q, kind: kind || undefined, page_size: 500 })
      .then(d => setItems(d.results || []));
  }, [q, kind]);

  const groups = items.reduce((acc, e) => {
    const key = e.occurred_at ? new Date(e.occurred_at).toISOString().slice(0, 10) : "Unknown";
    (acc[key] ||= []).push(e);
    return acc;
  }, {});
  const dateKeys = Object.keys(groups).sort().reverse();

  return (
    <>
      <PageHeader title="Investigation timeline" subtitle="Cross-case event stream" />

      <Card className="mb-6">
        <div className="flex flex-wrap gap-3">
          <input className="input flex-1 min-w-[220px]" placeholder="Search title/description…"
            value={q} onChange={e => setQ(e.target.value)} />
          <select className="input w-56" value={kind} onChange={e => setKind(e.target.value)}>
            <option value="">All kinds</option>
            <option value="process_create">process_create</option>
            <option value="network_conn">network_conn</option>
            <option value="file_event">file_event</option>
            <option value="registry">registry</option>
            <option value="service">service</option>
            <option value="alert">alert</option>
            <option value="custom">custom</option>
          </select>
        </div>
      </Card>

      {dateKeys.length === 0 ? <Empty>No timeline events.</Empty> : (
        <div className="space-y-6">
          {dateKeys.map(d => (
            <div key={d}>
              <div className="text-xs uppercase text-slate-400 mb-2">{d}</div>
              <Card className="!p-0">
                {groups[d].map(e => (
                  <div key={e.id} className="px-4 py-2 border-b border-ink-700/60 flex gap-3">
                    <div className="text-xs text-slate-400 w-24 font-mono shrink-0">
                      {e.occurred_at ? new Date(e.occurred_at).toLocaleTimeString() : "—"}
                    </div>
                    <div className="text-xs uppercase text-accent w-28 shrink-0">{e.kind}</div>
                    <div className="flex-1">
                      <div className="text-sm">{e.title}</div>
                      {e.description && <div className="text-xs text-slate-400">{e.description}</div>}
                    </div>
                    <Severity value={e.severity} />
                  </div>
                ))}
              </Card>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
