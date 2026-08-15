import { useEffect, useState, useRef } from "react";
import api, { fmtDate, formatApiError, API } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Plus, Send, CheckCircle2, Stamp, GitBranch, History, Paperclip, FileDown } from "lucide-react";

const CATEGORIES = ["Quality Manual", "SOP", "Calibration Procedure", "Work Instruction", "Form",
  "Calculation Method", "Uncertainty Procedure", "Equipment Procedure", "Environmental Procedure",
  "Certificate Template", "Policy"];

const EMPTY = { doc_number: "", title: "", category: "SOP", revision: "01", effective_date: "",
  review_date: "", prepared_by: "", reviewed_by: "", approved_by: "", file_url: "", change_note: "" };

export default function Documents() {
  const { user } = useAuth();
  const canManage = ["admin", "quality"].includes(user?.role);
  const [docs, setDocs] = useState([]);
  const [fCat, setFCat] = useState("all");
  const [fStatus, setFStatus] = useState("all");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [reviseFor, setReviseFor] = useState(null);
  const [reviseNote, setReviseNote] = useState("");
  const [history, setHistory] = useState(null);
  const fileRef = useRef(null);
  const [uploadFor, setUploadFor] = useState(null);

  const onFilePicked = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !uploadFor) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post(`/documents/${uploadFor}/attachment`, fd);
      toast.success("File attached");
      load();
    } catch (e2) { toast.error(formatApiError(e2.response?.data?.detail)); }
    setUploadFor(null);
  };
  const pickFile = (id) => { setUploadFor(id); setTimeout(() => fileRef.current?.click(), 0); };
  const viewFile = (id) => window.open(`${API}/documents/${id}/attachment`, "_blank");

  const load = () => {
    let url = "/documents";
    const qs = [];
    if (fCat !== "all") qs.push(`category=${encodeURIComponent(fCat)}`);
    if (fStatus !== "all") qs.push(`status=${fStatus}`);
    if (qs.length) url += "?" + qs.join("&");
    api.get(url).then((r) => setDocs(r.data));
  };
  useEffect(() => { load(); }, [fCat, fStatus]);

  const create = async () => {
    if (!form.doc_number.trim() || !form.title.trim()) return toast.error("Document Number and Title are required");
    try { await api.post("/documents", form); toast.success("Document created (draft)"); setOpen(false); setForm(EMPTY); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const transition = async (id, status) => {
    try { await api.post(`/documents/${id}/status`, { status }); toast.success(`Moved to ${status.replace("_", " ")}`); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const doRevise = async () => {
    try { await api.post(`/documents/${reviseFor.id}/revise`, { note: reviseNote }); toast.success("New revision created (draft)"); setReviseFor(null); setReviseNote(""); load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const showHistory = async (d) => {
    const { data } = await api.get(`/documents/${d.id}/history`);
    setHistory(data);
  };

  const F = (k, label, extra = {}) => (
    <div><Label className="text-xs">{label}</Label><Input className="mt-1" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} data-testid={`doc-${k}`} {...extra} /></div>
  );

  return (
    <div>
      <PageHeader title="Document Control" subtitle="Controlled documents — SOPs, procedures, forms & certificate templates with revision and obsolescence control"
        actions={canManage && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button className="bg-blue-600 hover:bg-blue-700" data-testid="add-doc-btn"><Plus className="h-4 w-4 mr-1.5" /> New Document</Button></DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader><DialogTitle>New Controlled Document</DialogTitle></DialogHeader>
              <div className="grid grid-cols-2 gap-3">
                {F("doc_number", "Document Number")}
                {F("title", "Title")}
                <div>
                  <Label className="text-xs">Category</Label>
                  <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                    <SelectTrigger className="mt-1" data-testid="doc-category"><SelectValue /></SelectTrigger>
                    <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                {F("revision", "Revision")}
                {F("review_date", "Review Date", { type: "date" })}
                {F("prepared_by", "Prepared By")}
                {F("reviewed_by", "Reviewed By")}
                {F("approved_by", "Approved By")}
                <div className="col-span-2">{F("file_url", "File / Attachment URL (optional)")}</div>
                <div className="col-span-2"><Label className="text-xs">Change Note</Label><Textarea className="mt-1" value={form.change_note} onChange={(e) => setForm({ ...form, change_note: e.target.value })} /></div>
              </div>
              <DialogFooter><Button onClick={create} className="bg-blue-600 hover:bg-blue-700" data-testid="save-doc-btn">Create</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        )} />

      <div className="flex gap-3 mb-4">
        <Select value={fCat} onValueChange={setFCat}><SelectTrigger className="w-56" data-testid="filter-category"><SelectValue placeholder="Category" /></SelectTrigger>
          <SelectContent><SelectItem value="all">All Categories</SelectItem>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent></Select>
        <Select value={fStatus} onValueChange={setFStatus}><SelectTrigger className="w-48" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>{["all", "draft", "under_review", "approved", "effective", "obsolete"].map((s) => <SelectItem key={s} value={s}>{s === "all" ? "All Statuses" : s.replace("_", " ")}</SelectItem>)}</SelectContent></Select>
      </div>

      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>{["Doc No.", "Title", "Category", "Rev", "Status", "Effective", "Actions"].map((h) => <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className={`border-t ${d.status === "obsolete" ? "opacity-60" : ""}`} data-testid={`doc-row-${d.id}`}>
                <td className="px-4 py-2.5 font-mono font-semibold text-slate-800">{d.doc_number}</td>
                <td className="px-4 py-2.5 text-slate-700">{d.title}</td>
                <td className="px-4 py-2.5 text-slate-600 text-xs">{d.category}</td>
                <td className="px-4 py-2.5 font-mono">{d.revision}{d.is_current && <span className="ml-1 text-[9px] text-emerald-600 font-bold">CURRENT</span>}</td>
                <td className="px-4 py-2.5"><StatusBadge status={d.status} /></td>
                <td className="px-4 py-2.5 text-slate-600">{fmtDate(d.effective_date)}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-1">
                    <Button size="icon" variant="ghost" title="History" onClick={() => showHistory(d)} data-testid={`doc-history-${d.id}`}><History className="h-4 w-4 text-slate-400" /></Button>
                    {d.attachment && <Button size="icon" variant="ghost" title={d.attachment.file_name} onClick={() => viewFile(d.id)} data-testid={`doc-viewfile-${d.id}`}><FileDown className="h-4 w-4 text-blue-500" /></Button>}
                    {canManage && <Button size="icon" variant="ghost" title="Attach file" onClick={() => pickFile(d.id)} data-testid={`doc-attach-${d.id}`}><Paperclip className={`h-4 w-4 ${d.attachment ? "text-emerald-500" : "text-slate-400"}`} /></Button>}
                    {canManage && d.status === "draft" && <Button size="sm" variant="outline" onClick={() => transition(d.id, "under_review")} data-testid={`doc-review-${d.id}`}><Send className="h-3.5 w-3.5 mr-1" /> Review</Button>}
                    {canManage && d.status === "under_review" && <Button size="sm" variant="outline" className="text-blue-700 border-blue-200" onClick={() => transition(d.id, "approved")} data-testid={`doc-approve-${d.id}`}><CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Approve</Button>}
                    {canManage && d.status === "approved" && <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => transition(d.id, "effective")} data-testid={`doc-effective-${d.id}`}><Stamp className="h-3.5 w-3.5 mr-1" /> Make Effective</Button>}
                    {canManage && d.status === "effective" && <Button size="sm" variant="outline" onClick={() => setReviseFor(d)} data-testid={`doc-revise-${d.id}`}><GitBranch className="h-3.5 w-3.5 mr-1" /> Revise</Button>}
                  </div>
                </td>
              </tr>
            ))}
            {docs.length === 0 && <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-400">No documents</td></tr>}
          </tbody>
        </table>
      </Card>

      {/* Revise dialog */}
      <Dialog open={!!reviseFor} onOpenChange={(v) => !v && setReviseFor(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>New Revision of {reviseFor?.doc_number} (rev {reviseFor?.revision})</DialogTitle></DialogHeader>
          <p className="text-sm text-slate-500">A new draft revision will be created. The current effective version stays effective until the new revision is made effective, at which point it is automatically marked <b>obsolete</b>.</p>
          <Textarea placeholder="Reason for revision / change note" value={reviseNote} onChange={(e) => setReviseNote(e.target.value)} data-testid="revise-note" />
          <DialogFooter><Button onClick={doRevise} className="bg-blue-600 hover:bg-blue-700" data-testid="confirm-revise-btn">Create Revision</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History dialog */}
      <Dialog open={!!history} onOpenChange={(v) => !v && setHistory(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Revision History — {history?.doc_number}</DialogTitle></DialogHeader>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {(history?.revisions || []).map((r) => (
              <div key={r.id} className="rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold">Rev {r.revision}</span>
                  <StatusBadge status={r.status} />
                </div>
                <div className="text-xs text-slate-500 mt-1">Prepared: {r.prepared_by || "—"} · Reviewed: {r.reviewed_by || "—"} · Approved: {r.approved_by || "—"} · Effective: {fmtDate(r.effective_date)}</div>
                {r.change_note && <div className="text-xs text-slate-600 mt-1">Note: {r.change_note}</div>}
                <div className="mt-2 space-y-0.5">
                  {(r.history || []).map((h, i) => <div key={i} className="text-[11px] text-slate-400 font-mono">{fmtDate(h.at)} · {h.action} · {h.by}{h.note ? ` — ${h.note}` : ""}</div>)}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
      {/* Hidden file input for attachments */}
      <input ref={fileRef} type="file" className="hidden" onChange={onFilePicked}
        accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.webp,.csv,.txt" data-testid="doc-file-input" />
    </div>
  );
}
