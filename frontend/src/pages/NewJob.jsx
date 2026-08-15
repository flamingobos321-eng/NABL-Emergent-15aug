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
import { Plus, Trash2, Package } from "lucide-react";

const newItem = () => ({
  product_id: "", serial_number: "", tag_number: "",
  sr_number: "", part_number: "", url_number: "",
  certificate_type: "NABL",
  cal_date: "", issue_date: "", item_received_date: "",
  template_code: "", reference_standard: "", method: "WI – TECH/11",
  master_ids: [], points: [],
});

export default function NewJob() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [masters, setMasters] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [job, setJob] = useState({ work_order_ref: "", work_order_date: "", work_order_notes: "", customer_id: "" });
  const [items, setItems] = useState([newItem()]);

  useEffect(() => {
    api.get("/masters").then((r) => setMasters(r.data));
    api.get("/templates").then((r) => setTemplates(r.data));
    api.get("/customers").then((r) => setCustomers(r.data));
  }, []);

  useEffect(() => {
    if (job.customer_id) api.get(`/products?customer_id=${job.customer_id}`).then((r) => setProducts(r.data));
    else setProducts([]);
  }, [job.customer_id]);

  const patchItem = (i, patch) => setItems((s) => s.map((it, k) => (k === i ? { ...it, ...patch } : it)));
  const templateComponents = (code) => templates.find((x) => x.code === code)?.components || [];

  const chooseTemplate = (i, code) => {
    const t = templates.find((x) => x.code === code);
    setItems((s) => s.map((it, k) => k === i ? {
      ...it, template_code: code,
      reference_standard: t?.reference_standard || it.reference_standard,
      method: t?.method || it.method,
      points: it.points.map((p) => ({ ...p, components: t?.components || p.components })),
    } : it));
  };

  const addPoint = (i) => setItems((s) => s.map((it, k) => k === i ? {
    ...it, points: [...it.points, {
      point_label: "", nominal: 0, master_readings: [0, 0, 0, 0, 0], uut_readings: [0, 0, 0, 0, 0],
      point_deviation: 0, cmc_floor: "", components: templateComponents(it.template_code),
    }],
  } : it));

  const patchPoint = (i, pi, patch) => setItems((s) => s.map((it, k) => k === i ? {
    ...it, points: it.points.map((p, j) => (j === pi ? { ...p, ...patch } : p)),
  } : it));

  const removePoint = (i, pi) => setItems((s) => s.map((it, k) => k === i ? { ...it, points: it.points.filter((_, j) => j !== pi) } : it));

  const toggleMaster = (i, mid) => setItems((s) => s.map((it, k) => k === i ? {
    ...it, master_ids: it.master_ids.includes(mid) ? it.master_ids.filter((x) => x !== mid) : [...it.master_ids, mid],
  } : it));

  const save = async () => {
    if (!job.work_order_ref.trim()) return toast.error("Work Order Reference is required");
    if (!job.customer_id) return toast.error("Select a customer");
    if (!items.length) return toast.error("Add at least one product");
    for (let i = 0; i < items.length; i++) {
      if (!items[i].product_id) return toast.error(`Product #${i + 1}: select a product`);
      if (!items[i].points.length) return toast.error(`Product #${i + 1}: add at least one calibration point`);
    }
    try {
      const payload = {
        ...job,
        items: items.map((it) => ({
          ...it,
          points: it.points.map((p) => ({
            ...p, nominal: Number(p.nominal) || 0,
            cmc_floor: p.cmc_floor === "" || p.cmc_floor === null ? null : Number(p.cmc_floor),
            components: p.components,
          })),
        })),
      };
      const { data } = await api.post("/jobs", payload);
      toast.success("Job created with " + items.length + " product(s)");
      navigate(`/jobs/${data.id}`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader title="New Calibration Job" subtitle="One Work Order → multiple products, each individually calibrated & certified" />

      <Card className="p-5 space-y-4 mb-6">
        <h3 className="font-head font-semibold">Work Order & Customer</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div><Label>Work Order Reference *</Label><Input data-testid="job-wo-ref" value={job.work_order_ref} onChange={(e) => setJob({ ...job, work_order_ref: e.target.value })} placeholder="WO-2026-00458 (Billing/ERP)" /></div>
          <div><Label>Work Order Date</Label><Input type="date" value={job.work_order_date} onChange={(e) => setJob({ ...job, work_order_date: e.target.value })} /></div>
          <div className="col-span-2">
            <Label>Customer</Label>
            <Select value={job.customer_id} onValueChange={(v) => { setJob({ ...job, customer_id: v }); setItems(items.map((it) => ({ ...it, product_id: "" }))); }}>
              <SelectTrigger data-testid="job-customer"><SelectValue placeholder="Select customer" /></SelectTrigger>
              <SelectContent>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {items.map((it, i) => (
        <Card className="p-5 mb-6 border-l-4 border-l-blue-500" key={i} data-testid={`product-item-${i}`}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-head font-semibold flex items-center gap-2"><Package className="h-4 w-4 text-blue-600" /> Product #{i + 1}</h3>
            {items.length > 1 && <Button variant="ghost" size="sm" className="text-red-600" onClick={() => setItems(items.filter((_, k) => k !== i))} data-testid={`remove-product-${i}`}><Trash2 className="h-4 w-4 mr-1" /> Remove</Button>}
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Label>Product</Label>
                <Select value={it.product_id} onValueChange={(v) => patchItem(i, { product_id: v })}>
                  <SelectTrigger data-testid={`item-product-${i}`}><SelectValue placeholder={job.customer_id ? "Select product" : "Select customer first"} /></SelectTrigger>
                  <SelectContent>{products.map((p) => <SelectItem key={p.id} value={p.id}>{p.name} ({p.type})</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>Serial Number</Label><Input data-testid={`item-serial-${i}`} value={it.serial_number} onChange={(e) => patchItem(i, { serial_number: e.target.value })} /></div>
              <div><Label>Tag Number</Label><Input value={it.tag_number} onChange={(e) => patchItem(i, { tag_number: e.target.value })} /></div>
              <div><Label>SR Number</Label><Input data-testid={`item-sr-${i}`} placeholder="manual entry" value={it.sr_number} onChange={(e) => patchItem(i, { sr_number: e.target.value })} /></div>
              <div><Label>Part Number</Label><Input data-testid={`item-part-${i}`} placeholder="manual entry" value={it.part_number} onChange={(e) => patchItem(i, { part_number: e.target.value })} /></div>
              <div><Label>URL Number</Label><Input data-testid={`item-url-${i}`} placeholder="manual entry" value={it.url_number} onChange={(e) => patchItem(i, { url_number: e.target.value })} /></div>
              <div>
                <Label>Certificate Type</Label>
                <Select value={it.certificate_type} onValueChange={(v) => patchItem(i, { certificate_type: v })}>
                  <SelectTrigger data-testid={`item-certtype-${i}`}><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="NABL">NABL</SelectItem><SelectItem value="Traceable">Traceable</SelectItem></SelectContent>
                </Select>
              </div>
              <div><Label>Calibration Date</Label><Input type="date" data-testid={`item-caldate-${i}`} value={it.cal_date} onChange={(e) => patchItem(i, { cal_date: e.target.value })} /></div>
              <div><Label>Issue Date</Label><Input type="date" value={it.issue_date} onChange={(e) => patchItem(i, { issue_date: e.target.value })} /></div>
              <div><Label>Item Received Date</Label><Input type="date" value={it.item_received_date} onChange={(e) => patchItem(i, { item_received_date: e.target.value })} /></div>
              <div>
                <Label>Calibration Template</Label>
                <Select value={it.template_code} onValueChange={(v) => chooseTemplate(i, v)}>
                  <SelectTrigger data-testid={`item-template-${i}`}><SelectValue placeholder="Select method template" /></SelectTrigger>
                  <SelectContent>{templates.map((t) => <SelectItem key={t.code} value={t.code}>{t.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="mb-1 block">Master Instruments</Label>
              <div className="space-y-2 max-h-64 overflow-y-auto rounded-md border border-slate-200 p-2.5">
                {masters.map((m) => (
                  <label key={m.id} className="flex items-center gap-2.5 text-sm cursor-pointer" data-testid={`item-${i}-master-${m.master_id}`}>
                    <Checkbox checked={it.master_ids.includes(m.master_id)} onCheckedChange={() => toggleMaster(i, m.master_id)} />
                    <span className="font-mono font-medium">{m.master_id}</span>
                    <span className="text-slate-500 truncate">{m.name}</span>
                    {m.validity_status === "expired" && <span className="text-red-600 text-xs">expired</span>}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-head font-semibold text-sm">Calibration Points</h4>
              <Button variant="outline" size="sm" onClick={() => addPoint(i)} data-testid={`add-point-${i}`} disabled={!it.template_code}>
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Point
              </Button>
            </div>
            {!it.template_code && <p className="text-xs text-amber-600 mb-2">Select a calibration template to load the uncertainty budget.</p>}
            <div className="space-y-3">
              {it.points.map((p, pi) => (
                <div key={pi} className="rounded-md border border-slate-200 p-3 bg-slate-50/50" data-testid={`item-${i}-point-${pi}`}>
                  <div className="grid grid-cols-4 gap-3 items-end">
                    <div><Label className="text-xs">Point Label</Label><Input value={p.point_label} onChange={(e) => patchPoint(i, pi, { point_label: e.target.value })} placeholder="100°C" /></div>
                    <div><Label className="text-xs">Nominal</Label><Input type="number" value={p.nominal} onChange={(e) => patchPoint(i, pi, { nominal: e.target.value })} /></div>
                    <div><Label className="text-xs">Master Deviation</Label><Input type="number" step="0.001" value={p.point_deviation} onChange={(e) => patchPoint(i, pi, { point_deviation: Number(e.target.value) })} /></div>
                    <div className="flex items-end gap-2">
                      <div className="flex-1"><Label className="text-xs">CMC Floor (opt)</Label><Input type="number" step="0.01" value={p.cmc_floor} onChange={(e) => patchPoint(i, pi, { cmc_floor: e.target.value })} /></div>
                      <Button variant="ghost" size="icon" onClick={() => removePoint(i, pi)}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-3">
                    {["master_readings", "uut_readings"].map((key) => (
                      <div key={key}>
                        <Label className="text-xs">{key === "master_readings" ? "Master (STD) readings" : "UUC readings"}</Label>
                        <div className="flex gap-1.5 mt-1">
                          {p[key].map((v, k) => (
                            <Input key={k} type="number" step="0.01" className="font-mono text-xs h-8 px-1 text-center"
                              value={v} onChange={(e) => { const arr = [...p[key]]; arr[k] = Number(e.target.value); patchPoint(i, pi, { [key]: arr }); }} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      ))}

      <div className="flex items-center justify-between mb-6">
        <Button variant="outline" onClick={() => setItems([...items, newItem()])} data-testid="add-product-btn">
          <Plus className="h-4 w-4 mr-1.5" /> Add Another Product
        </Button>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => navigate("/jobs")}>Cancel</Button>
          <Button className="bg-blue-600 hover:bg-blue-700" onClick={save} data-testid="save-job-btn">Create Job</Button>
        </div>
      </div>
    </div>
  );
}
