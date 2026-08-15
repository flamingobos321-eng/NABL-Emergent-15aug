import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { fmtDate } from "@/lib/api";
import { PageHeader, StatusBadge } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { Plus } from "lucide-react";

export default function WorkOrders() {
  const { user } = useAuth();
  const canCreate = ["admin", "technician"].includes(user?.role);
  const [wos, setWos] = useState([]);
  const navigate = useNavigate();
  useEffect(() => { api.get("/work-orders").then((r) => setWos(r.data)); }, []);

  return (
    <div>
      <PageHeader title="Work Orders" subtitle="Received from Sales/Admin — the starting point of every calibration"
        actions={canCreate && (
          <Button className="bg-blue-600 hover:bg-blue-700" data-testid="new-wo-btn" onClick={() => navigate("/work-orders/new")}>
            <Plus className="h-4 w-4 mr-1.5" /> New Work Order
          </Button>
        )} />
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>{["WO No.", "Customer", "PO Ref.", "Items", "Completion", "Status"].map((h) => <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {wos.map((w) => (
              <tr key={w.id} onClick={() => navigate(`/work-orders/${w.id}`)}
                className="border-t hover:bg-blue-50/40 cursor-pointer" data-testid={`wo-row-${w.id}`}>
                <td className="px-4 py-3 font-mono font-semibold text-slate-800">{w.wo_number}</td>
                <td className="px-4 py-3 text-slate-700">{w.customer_name}</td>
                <td className="px-4 py-3 text-slate-600 font-mono text-xs">{w.customer_po || "—"}</td>
                <td className="px-4 py-3 font-mono">{(w.items || []).length}</td>
                <td className="px-4 py-3 text-slate-600">{fmtDate(w.required_completion_date)}</td>
                <td className="px-4 py-3"><StatusBadge status={w.status} /></td>
              </tr>
            ))}
            {wos.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">No work orders yet</td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
