import { useEffect, useState } from "react";
import api, { fmtDate } from "@/lib/api";
import { PageHeader } from "@/components/Layout";
import { Card } from "@/components/ui/card";

export default function Audit() {
  const [logs, setLogs] = useState([]);
  useEffect(() => { api.get("/audit").then((r) => setLogs(r.data)); }, []);
  return (
    <div>
      <PageHeader title="Audit Trail" subtitle="Immutable record of all important changes" />
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>{["Time", "User", "Action", "Entity", "Field", "Old → New"].map((h) => <th key={h} className="text-left px-4 py-2.5 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-t align-top" data-testid={`audit-${l.id}`}>
                <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">{fmtDate(l.timestamp)} <span className="text-xs">{(l.timestamp || "").slice(11, 19)}</span></td>
                <td className="px-4 py-2.5 text-slate-700">{l.user_name}<div className="text-[11px] text-slate-400">{l.user_role}</div></td>
                <td className="px-4 py-2.5"><span className="inline-flex rounded bg-slate-100 px-2 py-0.5 text-xs font-medium">{l.action}</span></td>
                <td className="px-4 py-2.5 text-slate-600">{l.entity_type}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{l.field || "—"}</td>
                <td className="px-4 py-2.5 font-mono text-xs">
                  {l.old_value !== null && l.old_value !== undefined ? (
                    <span><span className="text-red-500">{JSON.stringify(l.old_value)}</span> → <span className="text-emerald-600">{JSON.stringify(l.new_value)}</span></span>
                  ) : l.new_value !== null && l.new_value !== undefined ? (
                    <span className="text-emerald-600">{JSON.stringify(l.new_value)}</span>
                  ) : (l.reason ? <span className="text-slate-500">{l.reason}</span> : "—")}
                </td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-400">No audit records</td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
