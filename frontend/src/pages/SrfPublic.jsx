import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api, { fmtDate, formatApiError } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { FlaskConical, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export default function SrfPublic() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [name, setName] = useState("");
  const [comments, setComments] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get(`/srf/${token}`).then((r) => setData(r.data)).catch(() => setErr(true));
  useEffect(() => { load(); }, [token]);

  const submit = async (action) => {
    if (!name) return toast.error("Please enter your name");
    setBusy(true);
    try { await api.post(`/srf/${token}/action`, { action, customer_name: name, comments }); toast.success("Response submitted"); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const srf = data?.srf;
  const st = data?.srf_status;
  const done = data && !["sent", "correction_requested"].includes(st);

  return (
    <div className="min-h-screen bg-slate-100 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-md bg-blue-600 grid place-items-center"><FlaskConical className="h-5 w-5 text-white" /></div>
          <div><div className="font-head font-bold text-slate-900">YOG Electro Process Pvt. Ltd.</div>
            <div className="text-xs uppercase tracking-widest text-slate-500">Service Request Form — Customer Approval</div></div>
        </div>

        {err && <Card className="p-8 text-center"><XCircle className="h-10 w-10 text-red-500 mx-auto mb-2" /><p className="text-slate-600">This SRF link is invalid or has expired.</p></Card>}

        {data && srf && (
          <Card className="p-6" data-testid="srf-public-card">
            <div className="flex items-center justify-between mb-4">
              <h1 className="font-head text-xl font-bold text-slate-900">SRF {srf.srf_no}</h1>
              {st === "approved" && <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold text-sm"><CheckCircle2 className="h-4 w-4" /> Approved</span>}
              {st === "rejected" && <span className="inline-flex items-center gap-1 text-red-700 font-semibold text-sm"><XCircle className="h-4 w-4" /> Rejected</span>}
              {st === "correction_requested" && <span className="inline-flex items-center gap-1 text-amber-700 font-semibold text-sm"><AlertTriangle className="h-4 w-4" /> Correction Requested</span>}
            </div>
            <p className="text-sm text-slate-500 mb-4">Please review the calibration request and approve, request a correction, or reject.</p>

            <div className="grid sm:grid-cols-2 gap-3 text-sm mb-4 bg-slate-50 rounded-md p-4">
              <div><span className="text-xs text-slate-500">Customer</span><div className="font-medium">{srf.customer_name}</div></div>
              <div><span className="text-xs text-slate-500">Work Order Ref</span><div className="font-medium font-mono">{srf.work_order_ref || "—"}</div></div>
              <div className="sm:col-span-2"><span className="text-xs text-slate-500">Address</span><div className="font-medium">{srf.address}</div></div>
            </div>
            <div className="mb-5 rounded-md border border-slate-200 overflow-hidden">
              <div className="px-3 py-2 bg-slate-100 text-xs uppercase tracking-wide text-slate-500 font-medium">Products in this Work Order</div>
              <table className="w-full text-sm">
                <thead className="text-slate-500 text-xs"><tr>{["Product", "Serial", "Type", "Points (°C)"].map((h) => <th key={h} className="text-left px-3 py-1.5 font-medium">{h}</th>)}</tr></thead>
                <tbody>
                  {(srf.products || []).map((p, i) => (
                    <tr key={i} className="border-t" data-testid={`srf-product-${i}`}>
                      <td className="px-3 py-2 font-medium">{p.product_name}</td>
                      <td className="px-3 py-2 font-mono text-xs">{p.serial_number || "—"}</td>
                      <td className="px-3 py-2">{p.certificate_type}</td>
                      <td className="px-3 py-2 font-mono text-xs">{(p.calibration_points || []).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {srf.lab_notes && <p className="text-xs text-slate-500 mb-4">Lab notes: {srf.lab_notes}</p>}

            {done ? (
              <div className="mt-4 rounded-md bg-slate-50 p-4 text-sm text-slate-600" data-testid="srf-done">
                {data.srf_approval ? <>Your response (<b>{data.srf_approval.action.replace("_", " ")}</b>) was recorded on {fmtDate(data.srf_approval.date)}. Thank you.</> : "This SRF has already been processed."}
              </div>
            ) : (
              <div className="mt-5 border-t pt-5">
                <div className="grid sm:grid-cols-2 gap-3 mb-3">
                  <div><label className="text-xs text-slate-500">Your Name</label><Input value={name} onChange={(e) => setName(e.target.value)} data-testid="srf-customer-name" placeholder="Authorized person" /></div>
                  <div><label className="text-xs text-slate-500">Comments (optional)</label><Input value={comments} onChange={(e) => setComments(e.target.value)} data-testid="srf-comments" /></div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button className="bg-emerald-600 hover:bg-emerald-700" disabled={busy} onClick={() => submit("approve")} data-testid="srf-approve-btn"><CheckCircle2 className="h-4 w-4 mr-1.5" /> Approve SRF</Button>
                  <Button variant="outline" className="text-amber-700 border-amber-300" disabled={busy} onClick={() => submit("request_correction")} data-testid="srf-correction-btn"><AlertTriangle className="h-4 w-4 mr-1.5" /> Request Correction</Button>
                  <Button variant="outline" className="text-red-600 border-red-300" disabled={busy} onClick={() => submit("reject")} data-testid="srf-reject-btn"><XCircle className="h-4 w-4 mr-1.5" /> Reject</Button>
                </div>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
