import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout.jsx";
import { useAuth } from "./auth/AuthContext.jsx";

import Login         from "./pages/Login.jsx";
import Dashboard     from "./pages/Dashboard.jsx";
import CasesList     from "./pages/CasesList.jsx";
import CaseDetail    from "./pages/CaseDetail.jsx";
import EvidenceView  from "./pages/EvidenceView.jsx";
import AnalysisView  from "./pages/AnalysisView.jsx";
import TimelineView  from "./pages/TimelineView.jsx";
import IOCsView      from "./pages/IOCsView.jsx";
import ReportsView   from "./pages/ReportsView.jsx";
import UsersView     from "./pages/UsersView.jsx";
import AuditView     from "./pages/AuditView.jsx";

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="flex items-center justify-center h-screen text-slate-400">Loading…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="cases" element={<CasesList />} />
        <Route path="cases/:id" element={<CaseDetail />} />
        <Route path="evidence/:id" element={<EvidenceView />} />
        <Route path="analysis/:jobId" element={<AnalysisView />} />
        <Route path="timeline" element={<TimelineView />} />
        <Route path="iocs" element={<IOCsView />} />
        <Route path="reports" element={<ReportsView />} />
        <Route path="users" element={<UsersView />} />
        <Route path="audit" element={<AuditView />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
