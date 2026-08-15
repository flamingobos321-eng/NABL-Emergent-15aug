import { NavLink, useNavigate } from "react-router-dom";
import { useAuth, ROLE_LABELS } from "@/context/AuthContext";
import {
  LayoutDashboard, Users2, Thermometer, ClipboardList, ShieldCheck,
  ScrollText, LogOut, FlaskConical, FileStack,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/jobs", label: "Calibration Jobs", icon: ClipboardList, testid: "nav-jobs" },
  { to: "/customers", label: "Customers & Products", icon: Users2, testid: "nav-customers" },
  { to: "/masters", label: "Master Instruments", icon: Thermometer, testid: "nav-masters" },
  { to: "/audit", label: "Audit Trail", icon: ScrollText, testid: "nav-audit" },
  { to: "/users", label: "Users & Roles", icon: ShieldCheck, testid: "nav-users", adminOnly: true },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-slate-50">
      <aside className="w-64 shrink-0 bg-slate-900 text-slate-300 flex flex-col fixed inset-y-0 left-0">
        <div className="px-5 py-5 border-b border-slate-800 flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-md bg-blue-600 grid place-items-center">
            <FlaskConical className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="font-head font-bold text-white text-[15px] leading-tight">YOG Electro</div>
            <div className="text-[10px] uppercase tracking-widest text-slate-400">Calibration Lab</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.filter((n) => !n.adminOnly || user?.role === "admin").map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ${
                  isActive ? "bg-blue-600 text-white" : "hover:bg-slate-800 hover:text-white"
                }`}>
              <n.icon className="h-4 w-4" /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-slate-800">
          <div className="px-2 pb-2">
            <div className="text-sm font-medium text-white truncate">{user?.name}</div>
            <div className="text-[11px] text-blue-400">{ROLE_LABELS[user?.role] || user?.role}</div>
          </div>
          <Button variant="ghost" size="sm" data-testid="logout-btn"
            className="w-full justify-start text-slate-300 hover:text-white hover:bg-slate-800"
            onClick={async () => { await logout(); navigate("/login"); }}>
            <LogOut className="h-4 w-4 mr-2" /> Sign out
          </Button>
        </div>
      </aside>
      <main className="flex-1 ml-64 min-h-screen">
        <div className="max-w-[1400px] mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="font-head text-2xl font-bold text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

const STATUS_STYLES = {
  draft: "bg-slate-100 text-slate-700",
  readings_entered: "bg-blue-50 text-blue-700",
  calculated: "bg-indigo-50 text-indigo-700",
  in_review: "bg-amber-50 text-amber-700",
  reviewed: "bg-violet-50 text-violet-700",
  approved: "bg-emerald-50 text-emerald-700",
  certified: "bg-emerald-600 text-white",
  rejected: "bg-red-50 text-red-700",
  valid: "bg-emerald-50 text-emerald-700",
  expiring: "bg-amber-50 text-amber-700",
  expired: "bg-red-50 text-red-700",
  work_order_received: "bg-slate-100 text-slate-700",
  lab_review: "bg-blue-50 text-blue-700",
  srf_prepared: "bg-indigo-50 text-indigo-700",
  srf_sent: "bg-amber-50 text-amber-700",
  srf_correction_requested: "bg-orange-50 text-orange-700",
  srf_rejected: "bg-red-50 text-red-700",
  srf_approved: "bg-emerald-50 text-emerald-700",
  calibration_in_progress: "bg-violet-50 text-violet-700",
  completed: "bg-emerald-600 text-white",
};

const STATUS_LABELS = {
  work_order_received: "New Work Order",
  lab_review: "Lab Review",
  srf_prepared: "SRF Prepared",
  srf_sent: "Awaiting Customer",
  srf_correction_requested: "Correction Requested",
  srf_rejected: "SRF Rejected",
  srf_approved: "Ready for Calibration",
  calibration_in_progress: "Calibration In Progress",
  completed: "Completed",
};

export function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] || (status || "").replace(/_/g, " ");
  return (
    <span data-testid={`status-${status}`}
      className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
        STATUS_STYLES[status] || "bg-slate-100 text-slate-700"}`}>
      {label}
    </span>
  );
}
