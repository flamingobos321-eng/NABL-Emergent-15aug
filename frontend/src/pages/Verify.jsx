import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api, { fmtDate } from "@/lib/api";
import { FlaskConical, CheckCircle2, XCircle, ShieldAlert } from "lucide-react";

export default function Verify() {
  const { vid } = useParams();
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    api.get(`/verify/${vid}`).then((r) => setState({ loading: false, data: r.data }))
      .catch(() => setState({ loading: false, error: true }));
  }, [vid]);

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        <div className="flex items-center gap-3 justify-center mb-6 text-white">
          <div className="h-10 w-10 rounded-md bg-blue-600 grid place-items-center"><FlaskConical className="h-5 w-5" /></div>
          <div>
            <div className="font-head font-bold">YOG Electro Process Pvt. Ltd.</div>
            <div className="text-xs uppercase tracking-widest text-slate-400">Certificate Verification</div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-xl p-8" data-testid="verify-card">
          {state.loading && <p className="text-center text-slate-400">Verifying…</p>}
          {state.error && (
            <div className="text-center">
              <XCircle className="h-12 w-12 text-red-500 mx-auto mb-3" />
              <h2 className="font-head text-xl font-bold text-slate-900">Certificate Not Found</h2>
              <p className="text-sm text-slate-500 mt-1">No certificate matches this verification code.</p>
            </div>
          )}
          {state.data && (
            <div>
              <div className="text-center mb-6">
                {state.data.status === "issued" ? (
                  <>
                    <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-3" />
                    <h2 className="font-head text-xl font-bold text-slate-900">Certificate Verified</h2>
                    <p className="text-sm text-emerald-600 font-medium">Valid & Issued</p>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-12 w-12 text-amber-500 mx-auto mb-3" />
                    <h2 className="font-head text-xl font-bold text-slate-900">Certificate {state.data.status}</h2>
                    <p className="text-sm text-amber-600 font-medium">This certificate is no longer valid</p>
                  </>
                )}
              </div>
              <dl className="divide-y divide-slate-100 text-sm">
                {[
                  ["Certificate No.", state.data.certificate_no],
                  ["ULR No.", state.data.ulr_no],
                  ["Item", state.data.item],
                  ["Type", state.data.item_type],
                  ["Serial No.", state.data.serial_number],
                  ["Calibration Points", state.data.points],
                  ["Calibration Date", fmtDate(state.data.cal_date)],
                  ["Recommended Next Cal", fmtDate(state.data.recommended_next_date)],
                  ["Issued Date", fmtDate(state.data.issued_date)],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between py-2">
                    <dt className="text-slate-500">{k}</dt>
                    <dd className="font-medium text-slate-800 font-mono">{v || "—"}</dd>
                  </div>
                ))}
              </dl>
              <p className="text-xs text-slate-400 text-center mt-6">Confidential customer details are not displayed publicly.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
