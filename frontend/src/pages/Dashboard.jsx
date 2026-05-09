import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  Tooltip, CartesianGrid,
} from "recharts";
import { Cases, IOCs, Analysis } from "../api/client";
import { Card, PageHeader, Severity, StatusPill, Stat, Empty } from "../components/ui.jsx";

const SEV_COLORS = { critical: "#dc2626", high: "#ea580c", medium: "#f59e0b",
                     low: "#22c55e", info: "#64748b" };

export default function Dashboard() {
  const [cases, setCases] = useState({ count: 0, results: [] });
  const [iocs,  setIocs]  = useState({ count: 0, results: [] });
  const [jobs,  setJobs]  = useState({ count: 0, results: [] });

  useEffect(() => {
    Cases.list({ page_size: 5, ordering: "-opened_at" }).then(setCases).catch(() => {});
    IOCs.list({ page_size: 200 }).then(setIocs).catch(() => {});
    Analysis.jobs({ page_size: 5, ordering: "-created_at" }).then(setJobs).catch(() => {});
  }, []);

  const sevCounts = (iocs.results || []).reduce((acc, x) => {
    acc[x.severity] = (acc[x.severity] || 0) + 1; return acc;
  }, {});
  const sevData = Object.entries(sevCounts).map(([name, value]) => ({ name, value }));

  const kindCounts = (iocs.results || []).reduce((acc, x) => {
    acc[x.kind] = (acc[x.kind] || 0) + 1; return acc;
  }, {});
  const kindData = Object.entries(kindCounts).map(([name, value]) => ({ name, value }));

  const openCases = (cases.results || []).filter(c =>
    !["closed", "archived"].includes(c.status)).length;

  return (
    <>
      <PageHeader title="SOC Dashboard"
        subtitle="Real-time view of investigations, indicators and analyses." />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Stat label="Open Cases"   value={openCases} />
        <Stat label="Total Cases"  value={cases.count || 0} />
        <Stat label="Total IOCs"   value={iocs.count  || 0} accent="text-amber-400" />
        <Stat label="Analyses"     value={jobs.count  || 0} accent="text-emerald-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <div className="text-sm font-semibold mb-3">IOCs by Severity</div>
          {sevData.length === 0
            ? <Empty>No IOCs yet.</Empty>
            : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={sevData} dataKey="value" nameKey="name"
                       outerRadius={90} innerRadius={50} stroke="none">
                    {sevData.map((s, i) => (
                      <Cell key={i} fill={SEV_COLORS[s.name] || "#475569"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
        </Card>

        <Card>
          <div className="text-sm font-semibold mb-3">IOCs by Kind</div>
          {kindData.length === 0
            ? <Empty>No IOCs yet.</Empty>
            : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={kindData}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                  <Bar dataKey="value" fill="#38bdf8" />
                </BarChart>
              </ResponsiveContainer>
            )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="flex justify-between mb-3">
            <div className="text-sm font-semibold">Recent Cases</div>
            <Link to="/cases" className="text-xs text-accent hover:underline">View all →</Link>
          </div>
          {(cases.results || []).length === 0 ? <Empty>No cases yet.</Empty> : (
            <table className="table">
              <thead><tr><th>Code</th><th>Title</th><th>Status</th><th>Severity</th></tr></thead>
              <tbody>
              {(cases.results || []).slice(0, 5).map(c => (
                <tr key={c.id}>
                  <td><Link to={`/cases/${c.id}`} className="text-accent hover:underline">{c.code}</Link></td>
                  <td className="truncate max-w-xs">{c.title}</td>
                  <td><StatusPill value={c.status} /></td>
                  <td><Severity value={c.severity} /></td>
                </tr>
              ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <div className="text-sm font-semibold mb-3">Recent Analyses</div>
          {(jobs.results || []).length === 0 ? <Empty>No analyses yet.</Empty> : (
            <table className="table">
              <thead><tr><th>Evidence</th><th>OS</th><th>Status</th><th>Risk</th></tr></thead>
              <tbody>
              {(jobs.results || []).slice(0, 5).map(j => (
                <tr key={j.id}>
                  <td><Link to={`/analysis/${j.id}`} className="text-accent hover:underline">{j.evidence_name}</Link></td>
                  <td className="capitalize">{j.detected_os || "—"}</td>
                  <td><StatusPill value={j.status} /></td>
                  <td className="font-mono">{j.risk_score}</td>
                </tr>
              ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </>
  );
}
