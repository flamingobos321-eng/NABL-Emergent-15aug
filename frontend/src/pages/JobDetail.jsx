import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import api, { fmtDate, num, formatApiError, PDF_URL } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  Calculator, FileText, Save, CheckCircle2, ClipboardCheck, Stamp, Download, ShieldCheck, XCircle, Send,
} from "lucide-react";

const DIST_LABEL = { normal_k2: "Normal (÷2)", rect_root3: "Rectangular (÷√3)", typeA: "Type A (s/√n)" };

export default function JobDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [job, setJob] = useState(null);
  const [computed, setComputed] = useState(null);
  const [validation, setValidation] = useState(null);
  const [audit, setAudit] = useState([]);
  const [preCheck, setPreCheck] = useState(null);
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get(`/jobs/${id}`);
    setJob(data);
    const a = await api.get(`/audit?entity_id=${id}`);
    setAudit(a.data);
    try { const pc = await api.get(`/jobs/${id}/pre-release-check`); setPreCheck(pc.data); } catch {}
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const calculate = useCallback(async () => {
    const { data } = await api.post(`/jobs/${id}/calculate`);
    setComputed(data.results);
    const v = await api.get(`/jobs/${id}/validation`);
    setValidation(v.data);
  }, [id]);

  useEffect(() => { if (job) calculate(); }, [job, calculate]);

  if (!job) return <div className="text-slate-500">Loading…</div>;

  const isTech = ["admin", "technician"].includes(user?.role);
  const locked = ["approved", "certified"].includes(job.status);

  const updateReading = (pi, key, ri, val) => {
    const pts = [...job.points];
    pts[pi][key][ri] = Number(val);
    setJob({ ...job, points: pts });
  };

  const saveReadings = async () => {
    setSaving(true);
    try {
      await api.put(`/jobs/${id}/readings`, { points: job.points });
      toast.success("Readings saved");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const act = async (path, body, msg) => {
    try {
      await api.post(`/jobs/${id}/${path}`, body || {});
      toast.success(msg);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const openPdf = () => window.open(PDF_URL(id), "_blank");
  const prepareSrf = async () => { try { await api.post(`/jobs/${id}/prepare-srf`); toast.success("SRF prepared"); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };
  const sendSrf = async () => { try { await api.post(`/jobs/${id}/send-srf`); toast.success("SRF sent to customer"); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); } };

  return (
    <div>
      <PageHeader
        title={<span className="font-mono">{job.job_no}</span>}
        subtitle={`${job.customer?.name || ""} · ${job.product?.name || ""} · S/N ${job.serial_number}`}
        actions={<div className="flex items-center gap-3"><StatusBadge status={job.status} /></div>}
      />

      {/* Workflow bar */}
      <Card className="p-3 mb-6 flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={calculate} data-testid="recalc-btn">
          <Calculator className="h-4 w-4 mr-1.5" /> Recalculate
        </Button>
        {isTech && !locked && (
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={() => act("submit-review", {}, "Submitted for review")} data-testid="submit-review-btn">
            <ClipboardCheck className="h-4 w-4 mr-1.5" /> Submit for Review
          </Button>
        )}
        {["admin", "reviewer"].includes(user?.role) && (
          <Button size="sm" className="bg-violet-600 hover:bg-violet-700" onClick={() => act("review", { comments: "Reviewed" }, "Marked reviewed")} data-testid="review-btn">
            <CheckCircle2 className="h-4 w-4 mr-1.5" /> Mark Reviewed
          </Button>
        )}
        {["admin", "signatory"].includes(user?.role) && job.status !== "certified" && (
          <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => act("approve", {}, "Approved & certificate issued")} data-testid="approve-btn">
            <Stamp className="h-4 w-4 mr-1.5" /> Approve & Issue Certificate
          </Button>
        )}
        {["admin", "reviewer", "signatory"].includes(user?.role) && !locked && (
          <Dialog>
            <DialogTrigger asChild><Button size="sm" variant="outline" className="text-red-600 border-red-200" data-testid="reject-btn"><XCircle className="h-4 w-4 mr-1.5" /> Reject</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Reject Job</DialogTitle></DialogHeader>
              <Textarea placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
              <DialogFooter><Button className="bg-red-600" onClick={() => act("reject", { reason }, "Job rejected")}>Reject</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        )}
        {job.certificate && (
          <Button size="sm" variant="outline" onClick={openPdf} data-testid="download-cert-btn">
            <Download className="h-4 w-4 mr-1.5" /> Certificate PDF
          </Button>
        )}
      </Card>

      <Tabs defaultValue="overview">
        <TabsList className="mb-4">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="srf" data-testid="tab-srf">SRF</TabsTrigger>
          <TabsTrigger value="readings" data-testid="tab-readings">Readings</TabsTrigger>
          <TabsTrigger value="calc" data-testid="tab-calc">Calculation</TabsTrigger>
          <TabsTrigger value="validation" data-testid="tab-validation">Excel vs App</TabsTrigger>
          <TabsTrigger value="certificate" data-testid="tab-certificate">Certificate</TabsTrigger>
          <TabsTrigger value="audit" data-testid="tab-audit">Audit</TabsTrigger>
        </TabsList>

        {/* OVERVIEW */}
        <TabsContent value="overview">
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="p-5">
              <h3 className="font-head font-semibold mb-3">Job Information</h3>
              <dl className="text-sm divide-y divide-slate-100">
                {[
                  ["Work Order Ref (Billing/ERP)", job.work_order_ref],
                  ["SRF No.", job.srf_no],
                  ["Certificate No.", job.cert_no], ["ULR No.", job.ulr_no],
                  ["Certificate Type", job.certificate_type || "NABL"],
                  ["Method", job.method], ["Reference Standard", job.reference_standard],
                  ["Calibration Date", fmtDate(job.cal_date)], ["Issue Date", fmtDate(job.issue_date)],
                  ["Item Received", fmtDate(job.item_received_date)], ["Next Cal Due", fmtDate(job.recommended_next_date)],
                  ["Technician", job.technician_name],
                  ["Environment", `${job.environmental?.humidity || ""} · ${job.environmental?.ambient_temp || ""}`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between py-2"><dt className="text-slate-500">{k}</dt><dd className="font-medium text-slate-800">{v || "—"}</dd></div>
                ))}
              </dl>
            </Card>
            <Card className="p-5">
              <h3 className="font-head font-semibold mb-3">Calibration Standards Used</h3>
              <table className="w-full text-sm">
                <thead className="text-xs text-slate-500 uppercase"><tr><th className="text-left py-1">ID</th><th className="text-left">Name</th><th className="text-right">Unc ±°C</th><th className="text-right">Validity</th></tr></thead>
                <tbody>
                  {(job.standards_used || []).map((s, i) => (
                    <tr key={i} className="border-t"><td className="py-1.5 font-mono">{s.id_no}</td><td>{s.name}</td><td className="text-right font-mono">{s.uncertainty}</td><td className="text-right text-slate-500">{fmtDate(s.validity)}</td></tr>
                  ))}
                </tbody>
              </table>
              {job.review && <div className="mt-4 text-sm bg-violet-50 rounded p-3"><b>Reviewed</b> by {job.review.reviewer_name} · {fmtDate(job.review.date)}</div>}
              {job.approval && <div className="mt-2 text-sm bg-emerald-50 rounded p-3"><b>Approved</b> by {job.approval.signatory_name} · {fmtDate(job.approval.date)}</div>}
            </Card>
          </div>
        </TabsContent>

        {/* SRF */}
        <TabsContent value="srf">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-head font-semibold">Service Request Form (SRF)</h3>
              <div className="flex gap-2">
                {isTech && !job.srf && <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={prepareSrf} data-testid="prepare-srf-btn"><FileText className="h-4 w-4 mr-1.5" /> Prepare SRF from Job</Button>}
                {isTech && job.srf && ["prepared", "correction_requested"].includes(job.srf_status) && <Button size="sm" className="bg-amber-600 hover:bg-amber-700" onClick={sendSrf} data-testid="send-srf-btn"><Send className="h-4 w-4 mr-1.5" /> Send SRF to Customer</Button>}
              </div>
            </div>
            {!job.srf && <p className="text-sm text-slate-400">No SRF yet. Prepare it from this job's Work Order reference & customer data.</p>}
            {job.srf && (
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-4">
                  <span><span className="text-slate-500">SRF No:</span> <b className="font-mono">{job.srf.srf_no}</b></span>
                  <span><span className="text-slate-500">WO Ref:</span> <b className="font-mono">{job.work_order_ref}</b></span>
                  <span><span className="text-slate-500">Status:</span> <StatusBadge status={job.srf_status === "sent" ? "srf_sent" : job.srf_status === "approved" ? "srf_approved" : job.srf_status === "correction_requested" ? "srf_correction_requested" : job.srf_status === "rejected" ? "srf_rejected" : "srf_prepared"} /></span>
                </div>
                <div className="grid sm:grid-cols-2 gap-2 bg-slate-50 rounded p-3">
                  <div><span className="text-xs text-slate-500">Customer</span><div className="font-medium">{job.srf.customer_name}</div></div>
                  <div><span className="text-xs text-slate-500">Product / Serial</span><div className="font-medium">{job.srf.product_name} · {job.srf.serial_number}</div></div>
                  <div><span className="text-xs text-slate-500">Certificate</span><div className="font-medium">{job.srf.certificate_type}</div></div>
                  <div><span className="text-xs text-slate-500">Points (°C)</span><div className="font-mono">{(job.srf.calibration_points || []).join(", ")}</div></div>
                </div>
                {job.srf_token && (
                  <div className="rounded bg-blue-50 border border-blue-200 p-3">
                    <div className="text-xs uppercase tracking-wide text-blue-700 mb-1">Secure customer SRF link</div>
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono truncate flex-1">{window.location.origin}/srf/{job.srf_token}</code>
                      <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(`${window.location.origin}/srf/${job.srf_token}`); toast.success("Copied"); }}>Copy</Button>
                      <Button size="sm" variant="outline" onClick={() => window.open(`/srf/${job.srf_token}`, "_blank")}>Open</Button>
                    </div>
                  </div>
                )}
                {job.srf_approval && (
                  <div className={`rounded p-3 ${job.srf_status === "approved" ? "bg-emerald-50" : "bg-amber-50"}`} data-testid="srf-approval-evidence">
                    <b>Customer {job.srf_approval.action.replace("_", " ")}</b> — {job.srf_approval.customer_name} · {fmtDate(job.srf_approval.date)} {job.srf_approval.comments && `· "${job.srf_approval.comments}"`}
                  </div>
                )}
              </div>
            )}
          </Card>
        </TabsContent>

        {/* READINGS */}
        <TabsContent value="readings">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-head font-semibold">Enter Readings</h3>
              {isTech && !locked && <Button size="sm" onClick={saveReadings} disabled={saving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-readings-btn"><Save className="h-4 w-4 mr-1.5" /> {saving ? "Saving…" : "Save & Recalculate"}</Button>}
            </div>
            <div className="space-y-5">
              {job.points.map((p, pi) => (
                <div key={pi} className="rounded-md border border-slate-200 overflow-hidden" data-testid={`readings-point-${pi}`}>
                  <div className="bg-slate-50 px-4 py-2 flex items-center justify-between border-b">
                    <span className="font-head font-semibold text-slate-800">Point: {p.point_label} <span className="text-slate-400 font-normal">(nominal {p.nominal})</span></span>
                    <span className="text-xs text-slate-500 font-mono">master dev {p.point_deviation}</span>
                  </div>
                  <div className="p-4 grid md:grid-cols-2 gap-4">
                    {["master_readings", "uut_readings"].map((key) => (
                      <div key={key}>
                        <div className="text-xs uppercase tracking-wide text-slate-500 mb-1.5">{key === "master_readings" ? "Master (STD) °C" : "UUC °C"}</div>
                        <div className="flex gap-1.5">
                          {p[key].map((v, ri) => (
                            <Input key={ri} type="number" step="0.01" disabled={!isTech || locked}
                              className="font-mono text-center text-sm h-9 px-1"
                              value={v} onChange={(e) => updateReading(pi, key, ri, e.target.value)}
                              data-testid={`reading-${pi}-${key}-${ri}`} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* CALCULATION */}
        <TabsContent value="calc">
          {!computed && <Card className="p-8 text-center text-slate-400">Click Recalculate</Card>}
          {computed && computed.map((p, pi) => (
            <Card key={pi} className="p-5 mb-5" data-testid={`calc-point-${pi}`}>
              <h3 className="font-head font-semibold mb-1">Point {p.point_label}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-4 text-sm">
                {[
                  ["Corrected STD", num(p.results.corrected_std)],
                  ["Measured (Xbar)", num(p.results.uut_mean)],
                  ["Deviation", num(p.results.deviation)],
                  ["s(x)", num(p.results.s_x, 5)],
                  ["Combined Uc", num(p.results.combined_unc, 5)],
                  ["Veff", num(p.results.veff, 0)],
                  ["k", num(p.results.k, 2)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-md bg-slate-50 border border-slate-200 px-3 py-2">
                    <div className="text-[10px] uppercase tracking-wide text-slate-500">{k}</div>
                    <div className="font-mono font-semibold text-slate-900">{v}</div>
                  </div>
                ))}
              </div>
              <div className="grid md:grid-cols-2 gap-3 mb-4">
                <div className="rounded-md bg-blue-50 border border-blue-200 px-4 py-3">
                  <div className="text-xs uppercase tracking-wide text-blue-700">Expanded Uncertainty (calc, k·Uc)</div>
                  <div className="font-mono font-bold text-lg text-blue-800">± {num(p.results.expanded_unc, 4)} °C</div>
                </div>
                <div className="rounded-md bg-emerald-50 border border-emerald-200 px-4 py-3">
                  <div className="text-xs uppercase tracking-wide text-emerald-700">Reported on Certificate {p.results.cmc_floor != null && `(CMC floor ${p.results.cmc_floor})`}</div>
                  <div className="font-mono font-bold text-lg text-emerald-800">± {num(p.results.reported_uncertainty)} °C</div>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-900 text-white">
                    <tr>{["Source", "Distribution", "Estimate Xi", "Std Unc u(xi)", "Ci", "Ui(y)", "Ui²", "dof"].map((h) => <th key={h} className="text-left px-2 py-1.5 font-medium">{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {p.results.budget.map((b, bi) => (
                      <tr key={bi} className={bi % 2 ? "bg-slate-50" : ""}>
                        <td className="px-2 py-1.5 text-slate-700">{b.label}<div className="text-[10px] text-slate-400">{b.source}</div></td>
                        <td className="px-2 py-1.5 text-slate-600">{DIST_LABEL[b.distribution]}</td>
                        <td className="px-2 py-1.5 font-mono text-right">{num(b.estimate, 4)}</td>
                        <td className="px-2 py-1.5 font-mono text-right">{num(b.std_unc, 5)}</td>
                        <td className="px-2 py-1.5 font-mono text-right">{num(b.ci, 1)}</td>
                        <td className="px-2 py-1.5 font-mono text-right">{num(b.ui, 5)}</td>
                        <td className="px-2 py-1.5 font-mono text-right">{num(b.ui_sq, 7)}</td>
                        <td className="px-2 py-1.5 font-mono text-right">{b.dof === null ? "∞" : b.dof}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))}
        </TabsContent>

        {/* VALIDATION */}
        <TabsContent value="validation">
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              <h3 className="font-head font-semibold">Excel vs Application Calculation Comparison</h3>
            </div>
            {!validation?.has_reference && <p className="text-sm text-amber-600 mb-3">No Excel reference values stored for this job. (Seeded example jobs carry the original Excel ground-truth for verification.)</p>}
            {validation && (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                  <tr>{["Point", "Parameter", "Excel", "Application", "Difference", "Status"].map((h) => <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {validation.rows.map((r, i) => (
                    <tr key={i} className="border-t" data-testid={`validation-row-${i}`}>
                      <td className="px-3 py-2 font-mono text-slate-500">{r.point}</td>
                      <td className="px-3 py-2 text-slate-700">{r.parameter}</td>
                      <td className="px-3 py-2 font-mono text-right">{r.excel === null ? "—" : (Math.abs(r.excel) < 0.001 ? r.excel : Number(r.excel).toPrecision(8))}</td>
                      <td className="px-3 py-2 font-mono text-right">{Math.abs(r.application) < 0.001 ? r.application : Number(r.application).toPrecision(8)}</td>
                      <td className="px-3 py-2 font-mono text-right">{r.difference === null ? "—" : Number(r.difference).toExponential(1)}</td>
                      <td className="px-3 py-2">
                        {r.status === "PASS" && <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-xs"><CheckCircle2 className="h-3.5 w-3.5" /> PASS</span>}
                        {r.status === "FAIL" && <span className="inline-flex items-center gap-1 text-red-600 font-semibold text-xs"><XCircle className="h-3.5 w-3.5" /> FAIL</span>}
                        {r.status === "N/A" && <span className="text-slate-400 text-xs">N/A</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </TabsContent>

        {/* CERTIFICATE */}
        <TabsContent value="certificate">
          {preCheck && (
            <Card className="p-5 mb-4" data-testid="pre-release-card">
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheck className={`h-5 w-5 ${preCheck.ready ? "text-emerald-600" : "text-amber-600"}`} />
                <h3 className="font-head font-semibold">Pre-Release Verification</h3>
                <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded ${preCheck.ready ? "bg-emerald-600 text-white" : "bg-amber-100 text-amber-700"}`}>
                  {preCheck.ready ? "READY TO RELEASE" : "INCOMPLETE"}
                </span>
              </div>
              <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
                {preCheck.checks.map((c, i) => (
                  <div key={i} className="flex items-center gap-2" data-testid={`precheck-${i}`}>
                    {c.ok ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-red-400" />}
                    <span className={c.ok ? "text-slate-700" : "text-slate-500"}>{c.item}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
          <Card className="p-8 text-center">
            {job.certificate ? (
              <div>
                <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto mb-3" />
                <h3 className="font-head font-semibold text-lg">Certificate Issued</h3>
                <p className="text-sm text-slate-500 mt-1">{job.certificate.cert_no} · Verification ID <span className="font-mono">{job.certificate.verification_id}</span></p>
                <div className="flex justify-center gap-3 mt-5">
                  <Button className="bg-blue-600 hover:bg-blue-700" onClick={openPdf} data-testid="view-cert-pdf-btn"><FileText className="h-4 w-4 mr-1.5" /> Open Certificate PDF</Button>
                  <Button variant="outline" onClick={() => window.open(`/verify/${job.certificate.verification_id}`, "_blank")}>View Public Verification</Button>
                </div>
              </div>
            ) : (
              <div>
                <Stamp className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                <h3 className="font-head font-semibold text-lg text-slate-600">Not yet certified</h3>
                <p className="text-sm text-slate-400 mt-1">An Authorized Signatory must approve this job to issue the certificate.</p>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* AUDIT */}
        <TabsContent value="audit">
          <Card className="p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase"><tr>{["Time", "User", "Action", "Field", "Change"].map((h) => <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>)}</tr></thead>
              <tbody>
                {audit.map((l) => (
                  <tr key={l.id} className="border-t align-top">
                    <td className="px-3 py-2 text-slate-500 whitespace-nowrap">{fmtDate(l.timestamp)} {(l.timestamp || "").slice(11, 19)}</td>
                    <td className="px-3 py-2">{l.user_name}</td>
                    <td className="px-3 py-2"><span className="inline-flex rounded bg-slate-100 px-2 py-0.5 text-xs">{l.action}</span></td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">{l.field || "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{l.old_value != null ? <span><span className="text-red-500">{JSON.stringify(l.old_value)}</span> → <span className="text-emerald-600">{JSON.stringify(l.new_value)}</span></span> : (l.reason || (l.new_value != null ? JSON.stringify(l.new_value) : "—"))}</td>
                  </tr>
                ))}
                {audit.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-400">No records</td></tr>}
              </tbody>
            </table>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
