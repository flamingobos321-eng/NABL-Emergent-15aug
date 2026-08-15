import { useEffect, useState } from "react";
import api, { fmtDate, formatApiError } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

const EMPTY = {
  master_id: "", name: "", manufacturer: "", model: "", serial_number: "",
  range: "", accuracy: "", resolution: "", cert_no: "", cal_date: "",
  cal_due_date: "", traceability: "", uncertainty: 0, status: "active", location: "", remarks: "",
};

export default function Masters() {
  const { user } = useAuth();
  const canEdit = ["admin", "technician"].includes(user?.role);
  const [masters, setMasters] = useState([]);
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const load = () => api.get("/masters").then((r) => setMasters(r.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm(EMPTY); setEditingId(null); setOpen(true); };
  const openEdit = (m) => {
    setForm({ ...EMPTY, ...m });
    setEditingId(m.id); setOpen(true);
  };
  const cancel = () => { setOpen(false); setForm(EMPTY); setEditingId(null); };

  const save = async () => {
    if (!form.master_id.trim() || !form.name.trim()) return toast.error("Master ID and Instrument name are required");
    const payload = { ...form, uncertainty: Number(form.uncertainty) || 0 };
    delete payload.id; delete payload.validity_status; delete payload.created_at;
    try {
      if (editingId) { await api.put(`/masters/${editingId}`, payload); toast.success("Master updated"); }
      else { await api.post("/masters", payload); toast.success("Master added"); }
      cancel(); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const del = async (m) => {
    if (!window.confirm(`Delete master "${m.master_id}"? If it has been used in a calibration it will be marked Retired instead.`)) return;
    try {
      const { data } = await api.delete(`/masters/${m.id}`);
      toast.success(data.message);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const F = (k, label, extra = {}) => (
    <div><Label>{label}</Label><Input value={form[k] ?? ""} data-testid={`master-${k}`}
      onChange={(e) => setForm({ ...form, [k]: e.target.value })} {...extra} /></div>
  );

  return (
    <div>
      <PageHeader title="Master / Reference Instruments" subtitle="Traceable standards used in calibration"
        actions={canEdit && (
          <Button className="bg-blue-600 hover:bg-blue-700" data-testid="add-master-btn" onClick={openNew}>
            <Plus className="h-4 w-4 mr-1.5" /> New Master
          </Button>
        )} />

      <Dialog open={open} onOpenChange={(v) => !v && cancel()}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{editingId ? "Edit Master Instrument" : "New Master Instrument"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            {F("master_id", "Master ID")}
            {F("name", "Instrument Name")}
            {F("manufacturer", "Manufacturer")}
            {F("model", "Model")}
            {F("serial_number", "Serial No.")}
            {F("range", "Range")}
            {F("accuracy", "Accuracy")}
            {F("resolution", "Resolution")}
            {F("uncertainty", "Uncertainty (±°C)", { type: "number", step: "0.001" })}
            {F("cert_no", "Calibration Cert No.")}
            {F("cal_date", "Calibration Date", { type: "date" })}
            {F("cal_due_date", "Calibration Due Date", { type: "date" })}
            {F("location", "Location")}
            <div>
              <Label>Status</Label>
              <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                <SelectTrigger data-testid="master-status"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["active", "out_of_service", "under_calibration", "retired", "inactive"].map((s) => <SelectItem key={s} value={s}>{s.replace(/_/g, " ")}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2">{F("traceability", "Traceability")}</div>
            <div className="col-span-2">{F("remarks", "Remarks")}</div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={cancel} data-testid="cancel-master-btn">Cancel</Button>
            <Button onClick={save} data-testid="save-master-btn" className="bg-blue-600 hover:bg-blue-700">Save Master</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              {["ID", "Name", "Range", "Unc ±°C", "Cert No.", "Due Date", "Status", "Actions"].map((h) => (
                <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {masters.map((m) => (
              <tr key={m.id} className="border-t hover:bg-slate-50/60" data-testid={`master-row-${m.master_id}`}>
                <td className="px-4 py-2.5 font-mono font-semibold text-slate-800">{m.master_id}</td>
                <td className="px-4 py-2.5 text-slate-700">{m.name}</td>
                <td className="px-4 py-2.5 text-slate-600 font-mono text-xs">{m.range}</td>
                <td className="px-4 py-2.5 text-right font-mono">{m.uncertainty}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{m.cert_no}</td>
                <td className="px-4 py-2.5 text-slate-600">{fmtDate(m.cal_due_date)}</td>
                <td className="px-4 py-2.5"><StatusBadge status={m.validity_status} /></td>
                <td className="px-4 py-2.5">
                  {canEdit && (
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEdit(m)} data-testid={`edit-master-${m.master_id}`}><Pencil className="h-3.5 w-3.5 text-slate-500" /></Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => del(m)} data-testid={`delete-master-${m.master_id}`}><Trash2 className="h-3.5 w-3.5 text-red-500" /></Button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
