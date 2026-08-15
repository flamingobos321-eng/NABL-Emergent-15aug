import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { Plus, ChevronRight, Package } from "lucide-react";
import { toast } from "sonner";

export default function Customers() {
  const { user } = useAuth();
  const canEdit = ["admin", "technician"].includes(user?.role);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState({});
  const [open, setOpen] = useState(false);
  const [prodOpen, setProdOpen] = useState(null);
  const [form, setForm] = useState({ name: "", address: "", contact: "", email: "", phone: "" });
  const [pform, setPform] = useState({ name: "", type: "", make: "", range: "", description: "" });

  const load = async () => {
    const { data } = await api.get("/customers");
    setCustomers(data);
    const map = {};
    for (const c of data) {
      const r = await api.get(`/products?customer_id=${c.id}`);
      map[c.id] = r.data;
    }
    setProducts(map);
  };
  useEffect(() => { load(); }, []);

  const addCustomer = async () => {
    try {
      await api.post("/customers", form);
      toast.success("Customer added");
      setOpen(false); setForm({ name: "", address: "", contact: "", email: "", phone: "" });
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const addProduct = async (cid) => {
    try {
      await api.post("/products", { ...pform, customer_id: cid });
      toast.success("Product added");
      setProdOpen(null); setPform({ name: "", type: "", make: "", range: "", description: "" });
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader title="Customers & Products" subtitle="Manage customer records and their calibrated items"
        actions={canEdit && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700" data-testid="add-customer-btn">
                <Plus className="h-4 w-4 mr-1.5" /> New Customer
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>New Customer</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label>Name</Label><Input data-testid="customer-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                <div><Label>Address</Label><Textarea data-testid="customer-address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Contact</Label><Input value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} /></div>
                  <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
                </div>
                <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
              </div>
              <DialogFooter><Button onClick={addCustomer} data-testid="save-customer-btn" className="bg-blue-600 hover:bg-blue-700">Save</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        )} />

      <div className="space-y-4">
        {customers.map((c) => (
          <Card key={c.id} className="p-5" data-testid={`customer-${c.id}`}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-head font-semibold text-slate-900">{c.name}</h3>
                <p className="text-sm text-slate-500 mt-0.5">{c.address}</p>
                <p className="text-xs text-slate-400 mt-1">{c.email} {c.phone && `· ${c.phone}`}</p>
              </div>
              {canEdit && (
                <Dialog open={prodOpen === c.id} onOpenChange={(v) => setProdOpen(v ? c.id : null)}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm" data-testid={`add-product-${c.id}`}>
                      <Plus className="h-3.5 w-3.5 mr-1" /> Product
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader><DialogTitle>New Product for {c.name}</DialogTitle></DialogHeader>
                    <div className="space-y-3">
                      <div><Label>Name</Label><Input data-testid="product-name" value={pform.name} onChange={(e) => setPform({ ...pform, name: e.target.value })} /></div>
                      <div className="grid grid-cols-2 gap-3">
                        <div><Label>Type</Label><Input placeholder="K / PT-100" value={pform.type} onChange={(e) => setPform({ ...pform, type: e.target.value })} /></div>
                        <div><Label>Make</Label><Input value={pform.make} onChange={(e) => setPform({ ...pform, make: e.target.value })} /></div>
                      </div>
                      <div><Label>Range</Label><Input placeholder="0 to 800 °C" value={pform.range} onChange={(e) => setPform({ ...pform, range: e.target.value })} /></div>
                    </div>
                    <DialogFooter><Button onClick={() => addProduct(c.id)} data-testid="save-product-btn" className="bg-blue-600 hover:bg-blue-700">Save</Button></DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </div>
            <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {(products[c.id] || []).map((p) => (
                <div key={p.id} className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 bg-slate-50/50">
                  <Package className="h-4 w-4 text-slate-400" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-800 truncate">{p.name}</div>
                    <div className="text-xs text-slate-500 font-mono">{p.type} · {p.range}</div>
                  </div>
                </div>
              ))}
              {(products[c.id] || []).length === 0 && <div className="text-xs text-slate-400 py-2">No products</div>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
