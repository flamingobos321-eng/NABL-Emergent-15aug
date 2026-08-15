import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { fmtDate } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { Plus, Package } from "lucide-react";

export default function Jobs() {
  const { user } = useAuth();
  const canCreate = ["admin", "technician"].includes(user?.role);
  const [jobs, setJobs] = useState([]);
  const navigate = useNavigate();
  useEffect(() => { api.get("/jobs").then((r) => setJobs(r.data)); }, []);

  return (
    <div>
      <PageHeader title="Calibration Jobs" subtitle="Each job (Work Order) can hold multiple products, each independently certified"
        actions={canCreate && (
          <Button className="bg-blue-600 hover:bg-blue-700" data-testid="new-job-btn" onClick={() => navigate("/jobs/new")}>
            <Plus className="h-4 w-4 mr-1.5" /> New Job
          </Button>
        )} />
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              {["Job No.", "Work Order", "Customer", "Products", "Cal Date", "Status"].map((h) => (
                <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} onClick={() => navigate(`/jobs/${j.id}`)}
                className="border-t hover:bg-blue-50/40 cursor-pointer" data-testid={`job-row-${j.id}`}>
                <td className="px-4 py-3 font-mono font-semibold text-slate-800">{j.job_no}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{j.work_order_ref || "—"}</td>
                <td className="px-4 py-3 text-slate-700">{j.customer_name}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700" data-testid={`job-product-count-${j.id}`}>
                    <Package className="h-3 w-3" /> {j.product_count} · {j.certified_count} certified
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{fmtDate(j.cal_date)}</td>
                <td className="px-4 py-3"><StatusBadge status={j.status} /></td>
              </tr>
            ))}
            {jobs.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">No jobs yet</td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
