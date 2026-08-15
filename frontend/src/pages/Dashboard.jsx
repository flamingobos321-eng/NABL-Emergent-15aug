import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { fmtDate } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import {
  ClipboardList, ClipboardCheck, FileCheck2, AlertTriangle, ThermometerSnowflake, FilePlus2,
} from "lucide-react";

function Stat({ icon: Icon, label, value, tone = "blue", testid }) {
  const tones = {
    blue: "text-blue-600 bg-blue-50",
    amber: "text-amber-600 bg-amber-50",
    violet: "text-violet-600 bg-violet-50",
    emerald: "text-emerald-600 bg-emerald-50",
    red: "text-red-600 bg-red-50",
  };
  return (
    <Card className="p-4 flex items-center gap-4" data-testid={testid}>
      <div className={`h-11 w-11 rounded-md grid place-items-center ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="text-2xl font-bold font-mono text-slate-900">{value}</div>
        <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [d, setD] = useState(null);
  const navigate = useNavigate();
  useEffect(() => { api.get("/dashboard").then((r) => setD(r.data)); }, []);
  if (!d) return <div className="text-slate-500">Loading…</div>;
  const c = d.counts;

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Calibration operations overview" />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <Stat icon={ClipboardList} label="Today's Jobs" value={c.today_jobs} tone="blue" testid="stat-today" />
        <Stat icon={FilePlus2} label="Pending Readings" value={c.pending_readings} tone="blue" testid="stat-readings" />
        <Stat icon={ClipboardCheck} label="Pending Review" value={c.pending_review} tone="amber" testid="stat-review" />
        <Stat icon={FileCheck2} label="Pending Approval" value={c.pending_approval} tone="violet" testid="stat-approval" />
        <Stat icon={FileCheck2} label="Certificates Issued" value={c.certificates_issued} tone="emerald" testid="stat-issued" />
        <Stat icon={AlertTriangle} label="Masters Expired" value={c.masters_expired} tone="red" testid="stat-expired" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 p-0 overflow-hidden">
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <h3 className="font-head font-semibold text-slate-900">Recent Calibration Jobs</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="text-left px-5 py-2 font-medium">Job No.</th>
                <th className="text-left px-5 py-2 font-medium">Customer</th>
                <th className="text-left px-5 py-2 font-medium">Cal Date</th>
                <th className="text-left px-5 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {d.recent_jobs.map((j) => (
                <tr key={j.id} onClick={() => navigate(`/jobs/${j.id}`)}
                  className="border-t hover:bg-blue-50/40 cursor-pointer" data-testid={`recent-job-${j.id}`}>
                  <td className="px-5 py-2.5 font-mono text-slate-800">{j.job_no}</td>
                  <td className="px-5 py-2.5 text-slate-700">{j.customer_name}</td>
                  <td className="px-5 py-2.5 text-slate-600">{fmtDate(j.cal_date)}</td>
                  <td className="px-5 py-2.5"><StatusBadge status={j.status} /></td>
                </tr>
              ))}
              {d.recent_jobs.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-8 text-center text-slate-400">No jobs yet</td></tr>
              )}
            </tbody>
          </table>
        </Card>

        <Card className="p-5">
          <h3 className="font-head font-semibold text-slate-900 flex items-center gap-2 mb-3">
            <ThermometerSnowflake className="h-4 w-4 text-amber-500" /> Master Validity
          </h3>
          {d.expired_masters.length === 0 && d.expiring_masters.length === 0 && (
            <p className="text-sm text-slate-400">All masters valid ✓</p>
          )}
          {[...d.expired_masters.map((m) => ({ ...m, s: "expired" })),
            ...d.expiring_masters.map((m) => ({ ...m, s: "expiring" }))].map((m) => (
            <div key={m.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <div className="text-sm font-medium text-slate-800">{m.master_id}</div>
                <div className="text-xs text-slate-500">{m.name}</div>
              </div>
              <div className="text-right">
                <StatusBadge status={m.s} />
                <div className="text-[11px] text-slate-400 mt-0.5">{fmtDate(m.cal_due_date)}</div>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
