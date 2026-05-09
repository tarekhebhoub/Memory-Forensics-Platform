import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import { Auth } from "../api/client";
import { Card, PageHeader, Empty } from "../components/ui.jsx";

const ROLES = ["admin", "lead", "analyst", "viewer"];

export default function UsersView() {
  const [items, setItems] = useState([]);
  const [show, setShow] = useState(false);

  const reload = () => Auth.users.list().then(d => setItems(d.results || d || []));
  useEffect(() => { reload(); }, []);

  const updateRole = async (u, role) => {
    try { await Auth.users.update(u.id, { role }); toast.success("Role updated"); reload(); }
    catch { toast.error("Failed"); }
  };
  const toggleActive = async (u) => {
    try { await Auth.users.update(u.id, { is_active: !u.is_active }); reload(); }
    catch { toast.error("Failed"); }
  };
  const remove = async (u) => {
    if (!window.confirm(`Delete user ${u.username}?`)) return;
    try { await Auth.users.remove(u.id); reload(); } catch { toast.error("Failed"); }
  };

  return (
    <>
      <PageHeader title="Users & roles" subtitle="Manage analysts, leads and admins"
        actions={<button className="btn" onClick={() => setShow(true)}><Plus className="w-4 h-4" /> New user</button>} />

      {items.length === 0 ? <Empty>No users.</Empty> : (
        <Card className="!p-0 overflow-hidden">
          <table className="table">
            <thead><tr>
              <th>Username</th><th>Email</th><th>Role</th><th>Active</th>
              <th>Last login</th><th></th>
            </tr></thead>
            <tbody>
              {items.map(u => (
                <tr key={u.id}>
                  <td className="font-medium">{u.username}</td>
                  <td className="text-xs text-slate-400">{u.email || "—"}</td>
                  <td>
                    <select className="input !py-1 !text-xs w-32" value={u.role}
                      onChange={(e) => updateRole(u, e.target.value)}>
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td>
                    <button className="btn-ghost text-xs" onClick={() => toggleActive(u)}>
                      {u.is_active ? "yes" : "no"}
                    </button>
                  </td>
                  <td className="text-xs text-slate-400">
                    {u.last_login ? new Date(u.last_login).toLocaleString() : "—"}
                  </td>
                  <td className="text-right">
                    <button className="btn-ghost text-red-300" onClick={() => remove(u)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {show && <NewUserModal onClose={() => { setShow(false); reload(); }} />}
    </>
  );
}

function NewUserModal({ onClose }) {
  const [form, setForm] = useState({ username: "", email: "", password: "", role: "analyst" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await Auth.users.create(form); toast.success("User created"); onClose(); }
    catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-30">
      <Card className="w-[440px] max-w-[95vw]">
        <form onSubmit={submit} className="space-y-3">
          <div className="font-semibold">Create user</div>
          <input className="input" placeholder="Username" value={form.username}
            onChange={e => setForm({...form, username: e.target.value})} required />
          <input className="input" type="email" placeholder="Email" value={form.email}
            onChange={e => setForm({...form, email: e.target.value})} />
          <input className="input" type="password" placeholder="Initial password" value={form.password}
            onChange={e => setForm({...form, password: e.target.value})} required />
          <select className="input" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
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
