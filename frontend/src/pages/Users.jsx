import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { ROLE_LABELS } from "@/context/AuthContext";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", email: "", password: "", role: "technician" });

  const load = () => api.get("/users").then((r) => setUsers(r.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      await api.post("/users", f);
      toast.success("User created");
      setOpen(false); setF({ name: "", email: "", password: "", role: "technician" }); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const del = async (id) => { await api.delete(`/users/${id}`); load(); toast.success("Removed"); };

  return (
    <div>
      <PageHeader title="Users & Roles" subtitle="Manage laboratory personnel access"
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700" data-testid="add-user-btn"><Plus className="h-4 w-4 mr-1.5" /> New User</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>New User</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label>Name</Label><Input data-testid="user-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
                <div><Label>Email</Label><Input data-testid="user-email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
                <div><Label>Password</Label><Input data-testid="user-password" type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div>
                <div>
                  <Label>Role</Label>
                  <Select value={f.role} onValueChange={(v) => setF({ ...f, role: v })}>
                    <SelectTrigger data-testid="user-role"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(ROLE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter><Button onClick={save} data-testid="save-user-btn" className="bg-blue-600 hover:bg-blue-700">Save</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        } />
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>{["Name", "Email", "Role", ""].map((h) => <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t" data-testid={`user-row-${u.email}`}>
                <td className="px-4 py-3 font-medium text-slate-800">{u.name}</td>
                <td className="px-4 py-3 text-slate-600 font-mono text-xs">{u.email}</td>
                <td className="px-4 py-3"><span className="inline-flex rounded bg-blue-50 text-blue-700 px-2 py-0.5 text-xs font-semibold">{ROLE_LABELS[u.role]}</span></td>
                <td className="px-4 py-3 text-right">
                  {u.role !== "admin" && <Button variant="ghost" size="icon" onClick={() => del(u.id)}><Trash2 className="h-4 w-4 text-red-500" /></Button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
