import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { fmtDate, formatApiError } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  ClipboardCheck, FileText, Send, PlayCircle, Copy, CheckCircle2, XCircle, ArrowRight,
} from "lucide-react";

function Step({ done, active, label }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`h-6 w-6 rounded-full grid place-items-center text-[11px] font-bold ${done ? "bg-emerald-500 text-white" : active ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-500"}`}>
        {done ? "✓" : ""}
      </div>
      <span className={`text-xs ${active ? "text-blue-700 font-semibold" : done ? "text-emerald-700" : "text-slate-400"}`}>{label}</span>
    </div>
  );
}

const ORDER = ["work_order_received", "lab_review", "srf_prepared", "srf_sent", "srf_approved", "calibration_in_progress", "completed"];

export default function WorkOrderDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [w, setW] = useState(null);
  const [srf, setSrf] = useState(null);
  const [link, setLink] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get(`/work-orders/${id}`);
    setW(data);
    setSrf(data.srf);
    if (data.srf_token) setLink(`${window.location.origin}/srf/${data.srf_token}`);
  }, [id]);
  useEffect(() => { load(); }, [load]);

  if (!w) return <div className="text-slate-500">Loading…</div>;
  const isTech = ["admin", "technician"].includes(user?.role);
  const stIdx = ORDER.indexOf(w.status);

  const act = async (path, msg) => {
    try { await api.post(`/work-orders/${id}/${path}`); toast.success(msg); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const prepareSrf = async () => { try { const { data } = await api.post(`/work-orders/${id}/prepare-srf`); setSrf(data.srf); toast.success("SRF prepared from Work Order"); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };
  const saveSrf = async () => { try { await api.put(`/work-orders/${id}/srf`, { srf }); toast.success("SRF saved"); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };
  const sendSrf = async () => { try { const { data } = await api.post(`/work-orders/${id}/send-srf`); setLink(data.srf_link); toast.success("SRF sent — share the secure link with the customer"); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };
  const startCal = async () => { try { const { data } = await api.post(`/work-orders/${id}/start-calibration`); toast.success(`Created ${data.job_ids.length} calibration jobs`); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };

  return (
    <div>
      <PageHeader title={<span className="font-mono">{w.wo_number}</span>}
        subtitle={`${w.customer_name} · PO ${w.customer_po || "—"}`}
        actions={<StatusBadge status={w.status} />} />

      {/* Stepper */}
      <Card className="p-4 mb-6 flex flex-wrap items-center gap-x-4 gap-y-2">
        {[["Received", 0], ["Lab Review", 1], ["SRF Prepared", 2], ["SRF Sent", 3], ["Approved", 4], ["Calibrating", 5], ["Completed", 6]].map(([lbl, i]) => (
          <div key={i} className="flex items-center gap-3">
            <Step done={stIdx > i} active={stIdx === i} label={lbl} />
            {i < 6 && <ArrowRight className="h-3 w-3 text-slate-300" />}
          </div>
        ))}
      </Card>

      {/* Action bar */}
      {isTech && (
        <Card className="p-3 mb-6 flex flex-wrap gap-2">
          {w.status === "work_order_received" && <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={() => act("review", "Marked reviewed")} data-testid="wo-review-btn"><ClipboardCheck className="h-4 w-4 mr-1.5" /> Review Work Order</Button>}
          {["lab_review", "work_order_received"].includes(w.status) && <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={prepareSrf} data-testid="prepare-srf-btn"><FileText className="h-4 w-4 mr-1.5" /> Prepare SRF</Button>}
          {["srf_prepared", "srf_correction_requested"].includes(w.status) && <Button size="sm" className="bg-amber-600 hover:bg-amber-700" onClick={sendSrf} data-testid="send-srf-btn"><Send className="h-4 w-4 mr-1.5" /> Send SRF to Customer</Button>}
          {w.status === "srf_approved" && <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={startCal} data-testid="start-calibration-btn"><PlayCircle className="h-4 w-4 mr-1.5" /> Start Calibration</Button>}
        </Card>
      )}

      {link && ["srf_sent", "srf_correction_requested", "srf_approved", "srf_rejected"].includes(w.status) && (
        <Card className="p-4 mb-6 bg-blue-50 border-blue-200">
          <div className="text-xs uppercase tracking-wide text-blue-700 mb-1">Secure SRF link for customer</div>
          <div className="flex items-center gap-2">
            <code className="text-sm text-blue-900 font-mono truncate flex-1">{link}</code>
            <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(link); toast.success("Link copied"); }}><Copy className="h-4 w-4 mr-1" /> Copy</Button>
            <Button size="sm" variant="outline" onClick={() => window.open(link, "_blank")}>Open</Button>
          </div>
        </Card>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Work Order */}
        <Card className="p-5">
          <h3 className="font-head font-semibold mb-3">Work Order (from Sales/Admin)</h3>
          <dl className="text-sm divide-y divide-slate-100 mb-3">
            {[["Customer PO", w.customer_po], ["Completion Date", fmtDate(w.required_completion_date)], ["Special Instructions", w.special_instructions], ["Remarks", w.remarks]].map(([k, v]) => (
              <div key={k} className="flex justify-between py-1.5 gap-4"><dt className="text-slate-500">{k}</dt><dd className="font-medium text-slate-800 text-right">{v || "—"}</dd></div>
            ))}
          </dl>
          <div className="space-y-2">
            {w.items.map((it, i) => (
              <div key={i} className="rounded border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-slate-800">{it.product_name} <span className="text-slate-400 font-mono text-xs">S/N {it.serial_number || "—"}</span></div>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${it.certificate_type === "NABL" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}>{it.certificate_type}</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">Qty {it.quantity} · {it.range}</div>
                <div className="text-xs font-mono text-slate-700 mt-1">Points: {(it.calibration_points || []).join(", ")} °C</div>
              </div>
            ))}
          </div>
        </Card>

        {/* SRF */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-head font-semibold">SRF (prepared by Lab)</h3>
            {srf && isTech && ["srf_prepared", "srf_correction_requested"].includes(w.status) && <Button size="sm" variant="outline" onClick={saveSrf}>Save SRF</Button>}
          </div>
          {!srf && <p className="text-sm text-slate-400">SRF not prepared yet. Click "Prepare SRF" to auto-fill it from the Work Order.</p>}
          {srf && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div><span className="text-xs text-slate-500">Customer</span><div className="font-medium">{srf.customer_name}</div></div>
                <div><span className="text-xs text-slate-500">Contact</span><div className="font-medium">{srf.contact || "—"}</div></div>
                <div className="col-span-2"><span className="text-xs text-slate-500">Address</span><div className="font-medium">{srf.address}</div></div>
              </div>
              <div>
                <span className="text-xs text-slate-500">Lab Notes</span>
                <Textarea className="mt-1" value={srf.lab_notes || ""} disabled={!isTech || !["srf_prepared", "srf_correction_requested"].includes(w.status)}
                  onChange={(e) => setSrf({ ...srf, lab_notes: e.target.value })} data-testid="srf-lab-notes" />
              </div>
              <div className="space-y-2">
                {srf.items.map((it, i) => (
                  <div key={i} className="rounded border border-slate-200 p-2 text-xs">
                    <b>{it.product_name}</b> · S/N {it.serial_number} · {it.certificate_type} · Points {(it.calibration_points || []).join(", ")} °C
                  </div>
                ))}
              </div>
              {w.srf_approval && (
                <div className={`rounded p-3 text-sm ${w.status === "srf_approved" ? "bg-emerald-50" : "bg-amber-50"}`}>
                  <div className="font-semibold flex items-center gap-1.5">
                    {w.status === "srf_approved" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <XCircle className="h-4 w-4 text-amber-600" />}
                    Customer {w.srf_approval.action.replace("_", " ")}
                  </div>
                  <div className="text-xs text-slate-600 mt-1">By {w.srf_approval.customer_name || "customer"} · {fmtDate(w.srf_approval.date)} {w.srf_approval.comments && `· "${w.srf_approval.comments}"`}</div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Linked jobs */}
      {w.jobs && w.jobs.length > 0 && (
        <Card className="p-0 overflow-hidden mt-6">
          <div className="px-5 py-3 border-b"><h3 className="font-head font-semibold">Calibration Jobs</h3></div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase"><tr>{["Job No.", "S/N", "Cert Type", "Points", "Status"].map((h) => <th key={h} className="text-left px-4 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {w.jobs.map((j) => (
                <tr key={j.id} className="border-t hover:bg-blue-50/40 cursor-pointer" onClick={() => navigate(`/jobs/${j.id}`)} data-testid={`wo-job-${j.id}`}>
                  <td className="px-4 py-2.5 font-mono font-medium">{j.job_no}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{j.serial_number}</td>
                  <td className="px-4 py-2.5"><span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${j.certificate_type === "NABL" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}>{j.certificate_type}</span></td>
                  <td className="px-4 py-2.5 font-mono">{(j.points || []).length}</td>
                  <td className="px-4 py-2.5"><StatusBadge status={j.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
