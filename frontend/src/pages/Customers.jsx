import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { Plus, Package, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

const EMPTY_PROD = { name: "", type: "", make: "", range: "", description: "", serial_number: "", tag_number: "", reference_no: "" };

export default function Customers() {
  const { user } = useAuth();
  const canEdit = ["admin", "technician"].includes(user?.role);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState({});
  const [custOpen, setCustOpen] = useState(false);
  const [form, setForm] = useState({ name: "", address: "", contact: "", email: "", phone: "" });
  const [prodDialog, setProdDialog] = useState(null); // {customerId, editingId}
  const [pform, setPform] = useState(EMPTY_PROD);

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
    if (!form.name.trim()) return toast.error("Customer name is required");
    try {
      await api.post("/customers", form);
      toast.success("Customer added");
      setCustOpen(false); setForm({ name: "", address: "", contact: "", email: "", phone: "" });
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const openNewProduct = (cid) => { setPform(EMPTY_PROD); setProdDialog({ customerId: cid, editingId: null }); };
  const openEditProduct = (cid, p) => {
    setPform({ name: p.name || "", type: p.type || "", make: p.make || "", range: p.range || "",
      description: p.description || "", serial_number: p.serial_number || "", tag_number: p.tag_number || "", reference_no: p.reference_no || "" });
    setProdDialog({ customerId: cid, editingId: p.id });
  };
  const cancelProduct = () => { setProdDialog(null); setPform(EMPTY_PROD); };

  const saveProduct = async () => {
    if (!pform.name.trim()) return toast.error("Product name is required");
    try {
      if (prodDialog.editingId) {
        await api.put(`/products/${prodDialog.editingId}`, { ...pform, customer_id: prodDialog.customerId });
        toast.success("Product updated");
      } else {
        await api.post("/products", { ...pform, customer_id: prodDialog.customerId });
        toast.success("Product added");
      }
      cancelProduct(); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const deleteProduct = async (p) => {
    if (!window.confirm(`Are you sure you want to delete "${p.name}"? If it has been used in a calibration job it will be archived instead of deleted.`)) return;
    try {
      const { data } = await api.delete(`/products/${p.id}`);
      toast.success(data.message);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader title="Customers & Products" subtitle="Manage customer records and their calibrated items"
        actions={canEdit && (
          <Button className="bg-blue-600 hover:bg-blue-700" data-testid="add-customer-btn" onClick={() => setCustOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" /> New Customer
          </Button>
        )} />

      {/* Customer dialog */}
      <Dialog open={custOpen} onOpenChange={setCustOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>New Customer</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Name *</Label><Input data-testid="customer-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div><Label>Address</Label><Textarea data-testid="customer-address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Contact</Label><Input value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} /></div>
              <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            </div>
            <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCustOpen(false)} data-testid="cancel-customer-btn">Cancel</Button>
            <Button onClick={addCustomer} data-testid="save-customer-btn" className="bg-blue-600 hover:bg-blue-700">Save Customer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Product dialog (create + edit) */}
      <Dialog open={!!prodDialog} onOpenChange={(v) => !v && cancelProduct()}>
        <DialogContent>
          <DialogHeader><DialogTitle>{prodDialog?.editingId ? "Edit Product" : "New Product"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Name *</Label><Input data-testid="product-name" value={pform.name} onChange={(e) => setPform({ ...pform, name: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Type</Label><Input data-testid="product-type" placeholder="K / PT-100" value={pform.type} onChange={(e) => setPform({ ...pform, type: e.target.value })} /></div>
              <div><Label>Make</Label><Input value={pform.make} onChange={(e) => setPform({ ...pform, make: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Serial Number</Label><Input data-testid="product-serial" value={pform.serial_number} onChange={(e) => setPform({ ...pform, serial_number: e.target.value })} /></div>
              <div><Label>Tag Number</Label><Input data-testid="product-tag" value={pform.tag_number} onChange={(e) => setPform({ ...pform, tag_number: e.target.value })} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Range</Label><Input placeholder="0 to 800 °C" value={pform.range} onChange={(e) => setPform({ ...pform, range: e.target.value })} /></div>
              <div><Label>Reference / Cert No.</Label><Input data-testid="product-refno" value={pform.reference_no} onChange={(e) => setPform({ ...pform, reference_no: e.target.value })} /></div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={cancelProduct} data-testid="cancel-product-btn">Cancel</Button>
            <Button onClick={saveProduct} data-testid="save-product-btn" className="bg-blue-600 hover:bg-blue-700">Save Product</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
                <Button variant="outline" size="sm" data-testid={`add-product-${c.id}`} onClick={() => openNewProduct(c.id)}>
                  <Plus className="h-3.5 w-3.5 mr-1" /> Product
                </Button>
              )}
            </div>
            <div className="mt-4 grid sm:grid-cols-2 gap-2">
              {(products[c.id] || []).map((p) => (
                <div key={p.id} className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 bg-slate-50/50" data-testid={`product-${p.id}`}>
                  <Package className="h-4 w-4 text-slate-400 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-slate-800 truncate">{p.name} {p.status === "archived" && <span className="text-[10px] text-red-500">(archived)</span>}</div>
                    <div className="text-xs text-slate-500 font-mono">{p.type} · S/N {p.serial_number || "—"} · Tag {p.tag_number || "—"}</div>
                  </div>
                  {canEdit && (
                    <div className="flex gap-1 shrink-0">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => openEditProduct(c.id, p)} data-testid={`edit-product-${p.id}`}><Pencil className="h-3.5 w-3.5 text-slate-500" /></Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => deleteProduct(p)} data-testid={`delete-product-${p.id}`}><Trash2 className="h-3.5 w-3.5 text-red-500" /></Button>
                    </div>
                  )}
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
