import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

const emptyItem = () => ({
  product_name: "", description: "", quantity: 1, serial_number: "", tag_number: "",
  range: "", points_text: "", certificate_type: "NABL", template_code: "",
});

export default function NewWorkOrder() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [f, setF] = useState({ wo_number: "", customer_id: "", customer_po: "", required_completion_date: "", special_instructions: "", remarks: "" });
  const [items, setItems] = useState([emptyItem()]);

  useEffect(() => {
    api.get("/customers").then((r) => setCustomers(r.data));
    api.get("/templates").then((r) => setTemplates(r.data));
  }, []);

  const setItem = (i, k, v) => { const n = [...items]; n[i][k] = v; setItems(n); };

  const save = async () => {
    if (!f.wo_number || !f.customer_id) return toast.error("Enter WO number & customer");
    try {
      const payload = {
        ...f,
        items: items.map((it) => ({
          product_name: it.product_name, description: it.description,
          quantity: Number(it.quantity) || 1, serial_number: it.serial_number,
          tag_number: it.tag_number, range: it.range,
          calibration_points: (it.points_text || "").split(",").map((x) => parseFloat(x.trim())).filter((x) => !isNaN(x)),
          certificate_type: it.certificate_type, template_code: it.template_code,
        })),
      };
      const { data } = await api.post("/work-orders", payload);
      toast.success("Work Order created");
      navigate(`/work-orders/${data.id}`);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader title="New Work Order" subtitle="Enter the Work Order received from Sales/Admin" />
      <Card className="p-5 mb-6">
        <h3 className="font-head font-semibold mb-3">Work Order Details</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <div><Label>Work Order No.</Label><Input data-testid="wo-number" value={f.wo_number} onChange={(e) => setF({ ...f, wo_number: e.target.value })} placeholder="WO/2026/001" /></div>
          <div>
            <Label>Customer</Label>
            <Select value={f.customer_id} onValueChange={(v) => setF({ ...f, customer_id: v })}>
              <SelectTrigger data-testid="wo-customer"><SelectValue placeholder="Select customer" /></SelectTrigger>
              <SelectContent>{customers.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div><Label>Customer PO / Reference</Label><Input value={f.customer_po} onChange={(e) => setF({ ...f, customer_po: e.target.value })} /></div>
          <div><Label>Required Completion Date</Label><Input type="date" value={f.required_completion_date} onChange={(e) => setF({ ...f, required_completion_date: e.target.value })} /></div>
          <div className="col-span-2"><Label>Special Instructions</Label><Input value={f.special_instructions} onChange={(e) => setF({ ...f, special_instructions: e.target.value })} /></div>
          <div className="col-span-3"><Label>Remarks</Label><Textarea value={f.remarks} onChange={(e) => setF({ ...f, remarks: e.target.value })} /></div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-head font-semibold">Products / Items</h3>
          <Button variant="outline" size="sm" onClick={() => setItems([...items, emptyItem()])} data-testid="add-wo-item-btn"><Plus className="h-3.5 w-3.5 mr-1" /> Add Item</Button>
        </div>
        <div className="space-y-4">
          {items.map((it, i) => (
            <div key={i} className="rounded-md border border-slate-200 p-4 bg-slate-50/50" data-testid={`wo-item-${i}`}>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div><Label className="text-xs">Product</Label><Input value={it.product_name} onChange={(e) => setItem(i, "product_name", e.target.value)} placeholder="Thermocouple" /></div>
                <div><Label className="text-xs">Serial No.</Label><Input value={it.serial_number} onChange={(e) => setItem(i, "serial_number", e.target.value)} placeholder="TC001" /></div>
                <div><Label className="text-xs">Quantity</Label><Input type="number" value={it.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} /></div>
                <div><Label className="text-xs">Range</Label><Input value={it.range} onChange={(e) => setItem(i, "range", e.target.value)} placeholder="0 to 800 °C" /></div>
                <div className="lg:col-span-2"><Label className="text-xs">Calibration Points (°C, comma separated)</Label><Input value={it.points_text} onChange={(e) => setItem(i, "points_text", e.target.value)} placeholder="100, 400" data-testid={`wo-item-points-${i}`} /></div>
                <div>
                  <Label className="text-xs">Certificate Type</Label>
                  <Select value={it.certificate_type} onValueChange={(v) => setItem(i, "certificate_type", v)}>
                    <SelectTrigger data-testid={`wo-item-certtype-${i}`}><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="NABL">NABL</SelectItem><SelectItem value="Traceable">Traceable</SelectItem></SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Calc Template</Label>
                  <Select value={it.template_code} onValueChange={(v) => setItem(i, "template_code", v)}>
                    <SelectTrigger data-testid={`wo-item-template-${i}`}><SelectValue placeholder="Template" /></SelectTrigger>
                    <SelectContent>{templates.map((t) => <SelectItem key={t.code} value={t.code}>{t.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end mt-2">
                <Button variant="ghost" size="sm" onClick={() => setItems(items.filter((_, j) => j !== i))} className="text-red-500"><Trash2 className="h-4 w-4 mr-1" /> Remove</Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="flex justify-end gap-3 mt-6">
        <Button variant="outline" onClick={() => navigate("/work-orders")}>Cancel</Button>
        <Button className="bg-blue-600 hover:bg-blue-700" onClick={save} data-testid="save-wo-btn">Create Work Order</Button>
      </div>
    </div>
  );
}
