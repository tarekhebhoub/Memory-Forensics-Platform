import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Cpu, Shield } from "lucide-react";
import { useAuth } from "../auth/AuthContext.jsx";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState("admin");
  const [p, setP] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(u, p);
      toast.success("Welcome back.");
      nav("/", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-ink-900 p-6">
      <div className="w-full max-w-md card p-8">
        <div className="flex items-center gap-3 mb-6">
          <Cpu className="w-9 h-9 text-accent" />
          <div>
            <div className="text-xl font-bold">Memory Forensics Platform</div>
            <div className="text-xs text-slate-400">Sign in to your DFIR workspace</div>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Username</label>
            <input className="input" value={u} onChange={(e) => setU(e.target.value)} autoFocus />
          </div>
          <div>
            <label className="label">Password</label>
            <input type="password" className="input" value={p} onChange={(e) => setP(e.target.value)} />
          </div>
          <button className="btn w-full justify-center" disabled={busy}>
            <Shield className="w-4 h-4" /> {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="mt-6 text-[11px] text-slate-500 text-center">
          Authorised SOC personnel only. All access is audited.
        </div>
      </div>
    </div>
  );
}
