import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

export default function NewJob() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [masters, setMasters] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [f, setF] = useState({
    work_order_ref: "", work_order_date: "", work_order_notes: "",
    customer_id: "", product_id: "", serial_number: "", tag_number: "",
    cal_date: "", issue_date: "", item_received_date: "", cert_no: "", ulr_no: "",
    method: "WI – TECH/11", reference_standard: "", template_code: "",
    master_ids: [],
  });
  const [points, setPoints] = useState([]);

  useEffect(() => {
    api.get("/customers").then((r) => setCustomers(r.data));
    api.get("/masters").then((r) => setMasters(r.data));
    api.get("/templates").then((r) => setTemplates(r.data));
  }, []);

  useEffect(() => {
    if (f.customer_id) api.get(`/products?customer_id=${f.customer_id}`).then((r) => setProducts(r.data));
  }, [f.customer_id]);

  const chooseTemplate = (code) => {
    const t = templates.find((x) => x.code === code);
    setF({ ...f, template_code: code, reference_standard: t?.reference_standard || "", method: t?.method || f.method });
    if (t && points.length) {
      setPoints(points.map((p) => ({ ...p, components: t.components })));
    }
  };

  const templateComponents = () => templates.find((x) => x.code === f.template_code)?.components || [];

  const chooseProduct = (pid) => {
    const p = products.find((x) => x.id === pid);
    setF((s) => ({
      ...s, product_id: pid,
      serial_number: p?.serial_number || s.serial_number,
      tag_number: p?.tag_number || s.tag_number,
      cert_no: p?.reference_no || s.cert_no,
      ulr_no: p?.ulr_no || s.ulr_no,
    }));
  };

  const addPoint = () => setPoints([...points, {
    point_label: "", nominal: 0, master_readings: [0, 0, 0, 0, 0], uut_readings: [0, 0, 0, 0, 0],
    point_deviation: 0, cmc_floor: "", components: templateComponents(),
  }]);

  const toggleMaster = (mid) => setF((s) => ({
    ...s, master_ids: s.master_ids.includes(mid) ? s.master_ids.filter((x) => x !== mid) : [...s.master_ids, mid],
  }));

  const save = async () => {
    if (!f.customer_id || !f.product_id) return toast.error("Select customer & product");
    if (!points.length) return toast.error("Add at least one calibration point");
    try {
      const payload = {
        ...f,
        points: points.map((p) => ({
          ...p, nominal: Number(p.nominal) || 0,
          cmc_floor: p.cmc_floor === "" || p.cmc_floor === null ? null : Number(p.cmc_floor),
          components: p.components,
        })),
      };
      const { data } = await api.post("/jobs", payload);
      toast.success("Job created");
      navigate(`/jobs/${data.id}`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader title="New Calibration Job" subtitle="Customer → Product → Masters → Calibration Points" />
      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 p-5 space-y-4">
          <h3 className="font-head font-semibold">Job Details</h3>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Work Order Reference *</Label><Input data-testid="job-wo-ref" value={f.work_order_ref} onChange={(e) => setF({ ...f, work_order_ref: e.target.value })} placeholder="WO-2026-00458 (from Billing/ERP)" /></div>
            <div><Label>Work Order Date</Label><Input type="date" value={f.work_order_date} onChange={(e) => setF({ ...f, work_order_date: e.target.value })} /></div>
            <div>
              <Label>Customer</Label>
              <Select value={f.customer_id} onValueChange={(v) => setF({ ...f, customer_id: v, product_id: "" })}>
                <SelectTrigger data-testid="job-customer"><SelectValue placeholder="Select customer" /></SelectTrigger>
                <SelectContent>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label>Product</Label>
              <Select value={f.product_id} onValueChange={chooseProduct}>
                <SelectTrigger data-testid="job-product"><SelectValue placeholder="Select product" /></SelectTrigger>
                <SelectContent>{products.map((p) => <SelectItem key={p.id} value={p.id}>{p.name} ({p.type})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Serial No.</Label><Input data-testid="job-serial" value={f.serial_number} onChange={(e) => setF({ ...f, serial_number: e.target.value })} /></div>
            <div><Label>Tag No.</Label><Input value={f.tag_number} onChange={(e) => setF({ ...f, tag_number: e.target.value })} /></div>
            <div><Label>Certificate No.</Label><Input data-testid="job-certno" value={f.cert_no} onChange={(e) => setF({ ...f, cert_no: e.target.value })} /></div>
            <div><Label>ULR No.</Label><Input value={f.ulr_no} onChange={(e) => setF({ ...f, ulr_no: e.target.value })} /></div>
            <div><Label>Calibration Date</Label><Input type="date" data-testid="job-caldate" value={f.cal_date} onChange={(e) => setF({ ...f, cal_date: e.target.value })} /></div>
            <div><Label>Issue Date</Label><Input type="date" value={f.issue_date} onChange={(e) => setF({ ...f, issue_date: e.target.value })} /></div>
            <div><Label>Item Received Date</Label><Input type="date" value={f.item_received_date} onChange={(e) => setF({ ...f, item_received_date: e.target.value })} /></div>
            <div>
              <Label>Calibration Template</Label>
              <Select value={f.template_code} onValueChange={chooseTemplate}>
                <SelectTrigger data-testid="job-template"><SelectValue placeholder="Select method template" /></SelectTrigger>
                <SelectContent>{templates.map((t) => <SelectItem key={t.code} value={t.code}>{t.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="font-head font-semibold mb-3">Master Instruments</h3>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {masters.map((m) => (
              <label key={m.id} className="flex items-center gap-2.5 text-sm cursor-pointer" data-testid={`master-check-${m.master_id}`}>
                <Checkbox checked={f.master_ids.includes(m.master_id)} onCheckedChange={() => toggleMaster(m.master_id)} />
                <span className="font-mono font-medium">{m.master_id}</span>
                <span className="text-slate-500 truncate">{m.name}</span>
                {m.validity_status === "expired" && <span className="text-red-600 text-xs">expired</span>}
              </label>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-5 mt-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-head font-semibold">Calibration Points</h3>
          <Button variant="outline" size="sm" onClick={addPoint} data-testid="add-point-btn"
            disabled={!f.template_code}>
            <Plus className="h-3.5 w-3.5 mr-1" /> Add Point
          </Button>
        </div>
        {!f.template_code && <p className="text-sm text-amber-600">Select a calibration template first to load the uncertainty budget.</p>}
        <div className="space-y-3">
          {points.map((p, i) => (
            <div key={i} className="rounded-md border border-slate-200 p-3 bg-slate-50/50" data-testid={`point-${i}`}>
              <div className="grid grid-cols-4 gap-3 items-end">
                <div><Label className="text-xs">Point Label</Label><Input value={p.point_label} onChange={(e) => { const n = [...points]; n[i].point_label = e.target.value; setPoints(n); }} placeholder="100°C" /></div>
                <div><Label className="text-xs">Nominal</Label><Input type="number" value={p.nominal} onChange={(e) => { const n = [...points]; n[i].nominal = e.target.value; setPoints(n); }} /></div>
                <div><Label className="text-xs">Master Deviation</Label><Input type="number" step="0.001" value={p.point_deviation} onChange={(e) => { const n = [...points]; n[i].point_deviation = Number(e.target.value); setPoints(n); }} /></div>
                <div className="flex items-end gap-2">
                  <div className="flex-1"><Label className="text-xs">CMC Floor (opt)</Label><Input type="number" step="0.01" value={p.cmc_floor} onChange={(e) => { const n = [...points]; n[i].cmc_floor = e.target.value; setPoints(n); }} /></div>
                  <Button variant="ghost" size="icon" onClick={() => setPoints(points.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-3">
                {["master_readings", "uut_readings"].map((key) => (
                  <div key={key}>
                    <Label className="text-xs">{key === "master_readings" ? "Master (STD) readings" : "UUC readings"}</Label>
                    <div className="flex gap-1.5 mt-1">
                      {p[key].map((v, k) => (
                        <Input key={k} type="number" step="0.01" className="font-mono text-xs h-8 px-1 text-center"
                          value={v} onChange={(e) => { const n = [...points]; n[i][key][k] = Number(e.target.value); setPoints(n); }} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="flex justify-end gap-3 mt-6">
        <Button variant="outline" onClick={() => navigate("/jobs")}>Cancel</Button>
        <Button className="bg-blue-600 hover:bg-blue-700" onClick={save} data-testid="save-job-btn">Create Job</Button>
      </div>
    </div>
  );
}
