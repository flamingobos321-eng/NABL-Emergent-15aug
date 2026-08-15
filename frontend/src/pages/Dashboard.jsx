import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { fmtDate } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  FileClock, UserCheck, FileCheck2, AlertTriangle, ThermometerSnowflake, Search as SearchIcon, FileText,
} from "lucide-react";

function Stat({ icon: Icon, label, value, tone = "blue", testid }) {
  const tones = {
    blue: "text-blue-600 bg-blue-50", amber: "text-amber-600 bg-amber-50",
    violet: "text-violet-600 bg-violet-50", emerald: "text-emerald-600 bg-emerald-50",
    red: "text-red-600 bg-red-50", slate: "text-slate-600 bg-slate-100",
  };
  return (
    <Card className="p-4 flex items-center gap-4" data-testid={testid}>
      <div className={`h-11 w-11 rounded-md grid place-items-center ${tones[tone]}`}><Icon className="h-5 w-5" /></div>
      <div><div className="text-2xl font-bold font-mono text-slate-900">{value}</div>
        <div className="text-[11px] text-slate-500 uppercase tracking-wide leading-tight">{label}</div></div>
    </Card>
  );
}

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const navigate = useNavigate();
  useEffect(() => { api.get("/dashboard").then((r) => setD(r.data)); }, []);

  const doSearch = async (e) => {
    e.preventDefault();
    if (!q.trim()) { setResults(null); return; }
    const { data } = await api.get(`/search?q=${encodeURIComponent(q)}`);
    setResults(data.jobs);
  };

  if (!d) return <div className="text-slate-500">Loading…</div>;
  const p = d.srf_pipeline || {};
  const c = d.counts;

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Laboratory operations — Calibration Jobs (Work Orders referenced from Billing/ERP)" />

      <form onSubmit={doSearch} className="mb-6 flex gap-2 max-w-xl" data-testid="global-search">
        <div className="relative flex-1">
          <SearchIcon className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input className="pl-9" placeholder="Search Work Order, Job, SRF, Certificate, Customer, Serial…"
            value={q} onChange={(e) => setQ(e.target.value)} data-testid="search-input" />
        </div>
      </form>

      {results && (
        <Card className="p-0 overflow-hidden mb-6">
          <div className="px-5 py-2.5 border-b text-sm font-semibold">Search results ({results.length})</div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase"><tr>{["Job", "WO Ref", "SRF", "Certificate", "Customer", "Status"].map((h) => <th key={h} className="text-left px-4 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {results.map((j) => (
                <tr key={j.id} onClick={() => navigate(`/jobs/${j.id}`)} className="border-t hover:bg-blue-50/40 cursor-pointer" data-testid={`search-result-${j.id}`}>
                  <td className="px-4 py-2 font-mono">{j.job_no}</td><td className="px-4 py-2 font-mono text-xs">{j.work_order_ref}</td>
                  <td className="px-4 py-2 font-mono text-xs">{j.srf_no || "—"}</td><td className="px-4 py-2 font-mono text-xs">{j.cert_no || "—"}</td>
                  <td className="px-4 py-2">{j.customer_name}</td><td className="px-4 py-2"><StatusBadge status={j.status} /></td>
                </tr>
              ))}
              {results.length === 0 && <tr><td colSpan={6} className="px-4 py-6 text-center text-slate-400">No matches</td></tr>}
            </tbody>
          </table>
        </Card>
      )}

      <h2 className="font-head font-semibold text-slate-700 text-sm uppercase tracking-wide mb-3">SRF Pipeline</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <Stat icon={FileText} label="No SRF Yet" value={p.no_srf || 0} tone="slate" testid="srf-none" />
        <Stat icon={FileClock} label="SRF Prepared" value={p.prepared || 0} tone="blue" testid="srf-prepared" />
        <Stat icon={UserCheck} label="Awaiting Customer" value={p.awaiting_customer || 0} tone="amber" testid="srf-awaiting" />
        <Stat icon={FileCheck2} label="SRF Approved" value={p.approved || 0} tone="emerald" testid="srf-approved" />
        <Stat icon={AlertTriangle} label="Correction / Rejected" value={p.correction || 0} tone="red" testid="srf-correction" />
      </div>

      <h2 className="font-head font-semibold text-slate-700 text-sm uppercase tracking-wide mb-3">Calibration & Certificates</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Stat icon={FileClock} label="Pending Readings" value={c.pending_readings} tone="blue" testid="stat-readings" />
        <Stat icon={UserCheck} label="Pending Review" value={c.pending_review} tone="amber" testid="stat-review" />
        <Stat icon={FileCheck2} label="Pending Approval" value={c.pending_approval} tone="violet" testid="stat-approval" />
        <Stat icon={FileCheck2} label="Certificates Issued" value={c.certificates_issued} tone="emerald" testid="stat-issued" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 p-0 overflow-hidden">
          <div className="px-5 py-3 border-b"><h3 className="font-head font-semibold text-slate-900">Recent Calibration Jobs</h3></div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase"><tr>{["Job No.", "WO Ref", "Customer", "Cert Type", "Status"].map((h) => <th key={h} className="text-left px-5 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {(d.recent_jobs || []).map((j) => (
                <tr key={j.id} onClick={() => navigate(`/jobs/${j.id}`)} className="border-t hover:bg-blue-50/40 cursor-pointer" data-testid={`recent-job-${j.id}`}>
                  <td className="px-5 py-2.5 font-mono text-slate-800">{j.job_no}</td>
                  <td className="px-5 py-2.5 font-mono text-xs text-slate-600">{j.work_order_ref}</td>
                  <td className="px-5 py-2.5 text-slate-700">{j.customer_name}</td>
                  <td className="px-5 py-2.5"><span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${j.certificate_type === "NABL" ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"}`}>{j.certificate_type || "NABL"}</span></td>
                  <td className="px-5 py-2.5"><StatusBadge status={j.status} /></td>
                </tr>
              ))}
              {(d.recent_jobs || []).length === 0 && <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-400">No jobs yet</td></tr>}
            </tbody>
          </table>
        </Card>
        <Card className="p-5">
          <h3 className="font-head font-semibold text-slate-900 flex items-center gap-2 mb-3"><ThermometerSnowflake className="h-4 w-4 text-amber-500" /> Master Validity</h3>
          {d.expired_masters.length === 0 && d.expiring_masters.length === 0 && <p className="text-sm text-slate-400">All masters valid ✓</p>}
          {[...d.expired_masters.map((m) => ({ ...m, s: "expired" })), ...d.expiring_masters.map((m) => ({ ...m, s: "expiring" }))].map((m) => (
            <div key={m.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div><div className="text-sm font-medium text-slate-800">{m.master_id}</div><div className="text-xs text-slate-500">{m.name}</div></div>
              <StatusBadge status={m.s} />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
