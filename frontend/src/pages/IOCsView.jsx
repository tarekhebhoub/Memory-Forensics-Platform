import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { IOCs } from "../api/client";
import { Card, PageHeader, Severity, Empty } from "../components/ui.jsx";

export default function IOCsView() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [sev, setSev] = useState("");

  useEffect(() => {
    IOCs.list({
      search: q, kind: kind || undefined, severity: sev || undefined, page_size: 500,
    }).then(d => setItems(d.results || []));
  }, [q, kind, sev]);

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(items, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `iocs-${Date.now()}.json`;
    a.click();
  };

  return (
    <>
      <PageHeader title="Indicators of Compromise" subtitle={`${items.length} indicators`}
        actions={<button className="btn-ghost" onClick={exportJson}><Download className="w-4 h-4" /> Export JSON</button>}
      />

      <Card className="mb-6">
        <div className="flex flex-wrap gap-3">
          <input className="input flex-1 min-w-[220px]" placeholder="Search IOC value…"
            value={q} onChange={e => setQ(e.target.value)} />
          <select className="input w-44" value={kind} onChange={e => setKind(e.target.value)}>
            <option value="">All kinds</option>
            {["ip","domain","url","md5","sha1","sha256","path","process","registry","email"].map(k =>
              <option key={k} value={k}>{k}</option>)}
          </select>
          <select className="input w-44" value={sev} onChange={e => setSev(e.target.value)}>
            <option value="">All severities</option>
            {["critical","high","medium","low","info"].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </Card>

      {items.length === 0 ? <Empty>No indicators.</Empty> : (
        <Card className="!p-0 overflow-hidden">
          <table className="table">
            <thead><tr>
              <th>Kind</th><th>Value</th><th>Severity</th><th>Confidence</th>
              <th>MITRE</th><th>Source</th><th>Case</th>
            </tr></thead>
            <tbody>
              {items.map(i => (
                <tr key={i.id}>
                  <td className="uppercase text-xs">{i.kind}</td>
                  <td className="font-mono text-xs break-all">{i.value}</td>
                  <td><Severity value={i.severity} /></td>
                  <td>{i.confidence}%</td>
                  <td className="text-xs">{(i.mitre_techniques || []).join(", ") || "—"}</td>
                  <td className="text-xs">{i.source_plugin || "—"}</td>
                  <td className="text-xs text-slate-400">#{i.case}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
