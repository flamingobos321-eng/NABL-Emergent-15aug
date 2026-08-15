import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { fmtDate } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { Plus } from "lucide-react";

export default function Jobs() {
  const { user } = useAuth();
  const canCreate = ["admin", "technician"].includes(user?.role);
  const [jobs, setJobs] = useState([]);
  const navigate = useNavigate();
  useEffect(() => { api.get("/jobs").then((r) => setJobs(r.data)); }, []);

  return (
    <div>
      <PageHeader title="Calibration Jobs" subtitle="All calibration activities and certificates"
        actions={canCreate && (
          <Button className="bg-blue-600 hover:bg-blue-700" data-testid="new-job-btn" onClick={() => navigate("/jobs/new")}>
            <Plus className="h-4 w-4 mr-1.5" /> New Job
          </Button>
        )} />
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              {["Job No.", "Customer", "Item S/N", "Cal Date", "Points", "Status"].map((h) => (
                <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} onClick={() => navigate(`/jobs/${j.id}`)}
                className="border-t hover:bg-blue-50/40 cursor-pointer" data-testid={`job-row-${j.id}`}>
                <td className="px-4 py-3 font-mono font-semibold text-slate-800">{j.job_no}</td>
                <td className="px-4 py-3 text-slate-700">{j.customer_name}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{j.serial_number}</td>
                <td className="px-4 py-3 text-slate-600">{fmtDate(j.cal_date)}</td>
                <td className="px-4 py-3 font-mono">{(j.points || []).length}</td>
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
