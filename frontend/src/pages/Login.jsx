import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FlaskConical } from "lucide-react";
import { toast } from "sonner";

const BG = "https://images.unsplash.com/photo-1606206873764-fd15e242df52?crop=entropy&cs=srgb&fm=jpg&q=85&w=1400";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      await login(email, password);
      toast.success("Signed in");
      navigate("/");
    } catch (e2) {
      const m = formatApiError(e2.response?.data?.detail) || e2.message;
      setErr(m); toast.error(m);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:block relative bg-slate-900">
        <img src={BG} alt="lab" className="absolute inset-0 h-full w-full object-cover opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent" />
        <div className="relative h-full flex flex-col justify-end p-12 text-white">
          <h2 className="font-head text-4xl font-bold leading-tight">Precision.<br />Traceability.<br />Trust.</h2>
          <p className="mt-4 text-slate-300 max-w-md text-sm">
            Digital calibration workflow for YOG Electro Process — reproducing your NABL Excel logic
            with full audit trail, uncertainty budgets and certificate control.
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center p-8 bg-slate-50">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <div className="flex items-center gap-3 mb-8">
            <div className="h-11 w-11 rounded-md bg-blue-600 grid place-items-center">
              <FlaskConical className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="font-head font-bold text-lg text-slate-900">YOG Electro Process</div>
              <div className="text-xs uppercase tracking-widest text-slate-500">Calibration Laboratory</div>
            </div>
          </div>
          <h1 className="font-head text-2xl font-bold text-slate-900 mb-1">Sign in</h1>
          <p className="text-sm text-slate-500 mb-6">Access the calibration management system</p>
          <div className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" data-testid="login-email" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} required className="mt-1" placeholder="you@yog.local" />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" data-testid="login-password" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} required className="mt-1" placeholder="••••••••" />
            </div>
            {err && <div className="text-sm text-red-600" data-testid="login-error">{err}</div>}
            <Button type="submit" disabled={busy} data-testid="login-submit" className="w-full bg-blue-600 hover:bg-blue-700">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </div>
          <div className="mt-6 text-xs text-slate-400 border-t pt-4">
            Demo: technician@yog.local · reviewer@yog.local · signatory@yog.local (see admin for passwords)
          </div>
        </form>
      </div>
    </div>
  );
}
