import { useEffect, useState } from "react";
import { NavLink, Routes, Route, Navigate } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import { Gauge, Cube, ShoppingBag, Tag, Warning, ArrowUp, TrendUp } from "@phosphor-icons/react";

export default function Admin() {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-slate-400">Loading…</div>;
  if (!user || user.role !== "admin") return <Navigate to="/login" replace />;

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 relative z-10">
      <div className="section-label mb-3">Admin Panel</div>
      <h1 className="font-display text-4xl md:text-5xl text-white mb-8">Command Center</h1>
      <div className="flex gap-6 border-b border-white/10 mb-8 overflow-x-auto">
        {[
          ["", "Dashboard", Gauge],
          ["products", "Products", Cube],
          ["orders", "Orders", ShoppingBag],
          ["coupons", "Coupons", Tag],
        ].map(([path, label, Icon]) => (
          <NavLink key={path} to={`/admin/${path}`} end
            className={({isActive}) => `flex items-center gap-2 py-3 font-mono-tech text-xs uppercase tracking-widest transition-colors ${isActive ? "text-[#00FF66] border-b-2 border-[#00FF66]" : "text-slate-400 hover:text-white"}`}
            data-testid={`admin-nav-${path || "dashboard"}`}>
            <Icon size={16} /> {label}
          </NavLink>
        ))}
      </div>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="products" element={<AdminProducts />} />
        <Route path="orders" element={<AdminOrders />} />
        <Route path="coupons" element={<AdminCoupons />} />
      </Routes>
    </div>
  );
}

function Dashboard() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/admin/dashboard").then(r => setD(r.data)); }, []);
  if (!d) return <p className="text-slate-400">Loading…</p>;
  const stats = [
    ["Revenue", `₹${d.revenue.toLocaleString()}`, TrendUp],
    ["Orders", d.total_orders, ShoppingBag],
    ["Products", d.total_products, Cube],
    ["Customers", d.total_users, ArrowUp],
  ];
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(([l, v, Icon]) => (
          <div key={l} className="border border-white/10 p-6">
            <Icon size={20} className="text-[#00FF66] mb-3" />
            <div className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest">{l}</div>
            <div className="font-display text-3xl text-white mt-1">{v}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="border border-white/10 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Warning size={16} className="text-yellow-400" />
            <div className="section-label">Low Stock</div>
          </div>
          {d.low_stock.length === 0 ? <p className="text-slate-400 text-sm">All stocked.</p> : (
            <div className="space-y-2">
              {d.low_stock.map(p => (
                <div key={p.id} className="flex justify-between text-sm border-b border-white/5 pb-2">
                  <span className="text-white">{p.name}</span>
                  <span className="font-mono-tech text-yellow-400">{p.stock_qty} left</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="border border-white/10 p-6">
          <div className="section-label mb-4">Recent Orders</div>
          {d.recent_orders.length === 0 ? <p className="text-slate-400 text-sm">No orders yet.</p> : (
            <div className="space-y-2">
              {d.recent_orders.slice(0, 5).map(o => (
                <div key={o.id} className="flex justify-between text-sm border-b border-white/5 pb-2">
                  <span className="text-white font-mono-tech text-xs">#{o.id.slice(0, 8)}</span>
                  <span className="text-slate-400 text-xs">{o.status}</span>
                  <span className="text-[#00FF66] font-mono-tech">₹{o.total.toFixed(0)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AdminProducts() {
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const empty = { sku: "", name: "", category: "sensors", brand: "", price: 0, discount_price: null, stock_qty: 0,
    description: "", voltage: "", interface: "", images: [], is_active: true, is_featured: false, specs: {} };
  const [form, setForm] = useState(empty);

  const load = () => api.get("/products", { params: { limit: 200 }}).then(r => setProducts(r.data.items));
  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      const payload = { ...form,
        images: typeof form.images === "string" ? form.images.split(",").map(s => s.trim()).filter(Boolean) : form.images,
        price: parseFloat(form.price) || 0,
        discount_price: form.discount_price ? parseFloat(form.discount_price) : null,
        stock_qty: parseInt(form.stock_qty) || 0,
      };
      if (editing) await api.put(`/admin/products/${editing}`, payload);
      else await api.post("/admin/products", payload);
      toast.success("Saved");
      setShowForm(false); setEditing(null); setForm(empty); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
  };
  const remove = async (id) => {
    if (!window.confirm("Delete this product?")) return;
    await api.delete(`/admin/products/${id}`);
    toast.success("Deleted"); load();
  };
  const edit = (p) => {
    setEditing(p.id);
    setForm({ ...p, images: (p.images || []).join(", "), discount_price: p.discount_price || "" });
    setShowForm(true);
  };

  return (
    <div>
      <div className="flex justify-between mb-6">
        <div className="section-label">Products ({products.length})</div>
        <button data-testid="new-product" onClick={() => { setForm(empty); setEditing(null); setShowForm(true); }} className="btn-primary-neo">+ New Product</button>
      </div>

      {showForm && (
        <div className="border border-[#00FF66]/40 p-6 mb-6 bg-[#00FF66]/5">
          <div className="section-label mb-4">{editing ? "Edit" : "New"} Product</div>
          <div className="grid md:grid-cols-2 gap-4">
            <Inp l="SKU" v={form.sku} on={v=>setForm({...form,sku:v})} tid="p-sku" />
            <Inp l="Name" v={form.name} on={v=>setForm({...form,name:v})} tid="p-name" />
            <div>
              <label className="block text-[10px] font-mono-tech uppercase text-slate-400 mb-1">Category</label>
              <select data-testid="p-category" value={form.category} onChange={e=>setForm({...form,category:e.target.value})} className="w-full px-3 py-2">
                {["sensors","microcontrollers","processors","robotics","power","connectivity","tools","kits"].map(c=><option key={c}>{c}</option>)}
              </select>
            </div>
            <Inp l="Brand" v={form.brand} on={v=>setForm({...form,brand:v})} tid="p-brand" />
            <Inp l="Price (₹)" v={form.price} on={v=>setForm({...form,price:v})} type="number" tid="p-price" />
            <Inp l="Discount Price (₹)" v={form.discount_price || ""} on={v=>setForm({...form,discount_price:v})} type="number" tid="p-discount" />
            <Inp l="Stock" v={form.stock_qty} on={v=>setForm({...form,stock_qty:v})} type="number" tid="p-stock" />
            <Inp l="Voltage" v={form.voltage || ""} on={v=>setForm({...form,voltage:v})} tid="p-voltage" />
            <Inp l="Interface" v={form.interface || ""} on={v=>setForm({...form,interface:v})} tid="p-interface" />
            <Inp l="Image URLs (comma separated)" v={form.images} on={v=>setForm({...form,images:v})} tid="p-images" cls="md:col-span-2" />
            <div className="md:col-span-2">
              <label className="block text-[10px] font-mono-tech uppercase text-slate-400 mb-1">Description</label>
              <textarea data-testid="p-desc" value={form.description} onChange={e=>setForm({...form,description:e.target.value})} rows={3} className="w-full px-3 py-2" />
            </div>
            <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={form.is_featured} onChange={e=>setForm({...form,is_featured:e.target.checked})} /> Featured</label>
            <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={form.is_active} onChange={e=>setForm({...form,is_active:e.target.checked})} /> Active</label>
          </div>
          <div className="flex gap-3 mt-6">
            <button data-testid="save-product" onClick={save} className="btn-primary-neo">Save</button>
            <button onClick={() => setShowForm(false)} className="btn-ghost-neo">Cancel</button>
          </div>
        </div>
      )}

      <div className="border border-white/10">
        {products.map(p => (
          <div key={p.id} className="flex items-center gap-4 p-4 border-b border-white/5 last:border-b-0">
            <img src={p.images?.[0]} className="w-12 h-12 object-cover border border-white/10" alt="" />
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-mono-tech text-slate-500 uppercase">{p.sku}</div>
              <div className="text-white truncate">{p.name}</div>
            </div>
            <div className="text-[#00FF66] font-mono-tech">₹{(p.discount_price || p.price).toFixed(0)}</div>
            <div className="text-xs font-mono-tech text-slate-400 w-16 text-right">{p.stock_qty} in stock</div>
            <button onClick={() => edit(p)} className="text-xs font-mono-tech text-slate-300 hover:text-[#00FF66]">EDIT</button>
            <button onClick={() => remove(p.id)} className="text-xs font-mono-tech text-red-400 hover:text-red-300">DEL</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const load = () => api.get("/admin/orders").then(r => setOrders(r.data));
  useEffect(() => { load(); }, []);

  const updateStatus = async (id, status, tracking = null) => {
    await api.post(`/admin/orders/${id}/status`, { status, tracking_number: tracking });
    toast.success("Updated"); load();
  };

  return (
    <div>
      <div className="section-label mb-6">Orders ({orders.length})</div>
      <div className="space-y-3">
        {orders.map(o => (
          <div key={o.id} className="border border-white/10 p-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="text-[10px] font-mono-tech text-slate-500 uppercase">#{o.id.slice(0, 8)} · {new Date(o.created_at).toLocaleString()}</div>
                <div className="text-white">{o.address?.full_name} · {o.items.length} items · ₹{o.total.toFixed(0)}</div>
              </div>
              <select value={o.status} onChange={e => updateStatus(o.id, e.target.value)} className="text-xs font-mono-tech uppercase px-2 py-1">
                {["pending_payment","confirmed","shipped","delivered","cancelled"].map(s => <option key={s}>{s}</option>)}
              </select>
              <input placeholder="tracking #" defaultValue={o.tracking_number || ""} onBlur={e => e.target.value !== (o.tracking_number || "") && updateStatus(o.id, o.status, e.target.value)} className="text-xs px-2 py-1 w-40" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AdminCoupons() {
  const [coupons, setCoupons] = useState([]);
  const [form, setForm] = useState({ code: "", discount_type: "percent", discount_value: 10, min_order: 0, max_uses: 100, active: true });
  const load = () => api.get("/admin/coupons").then(r => setCoupons(r.data));
  useEffect(() => { load(); }, []);
  const save = async () => {
    try {
      await api.post("/admin/coupons", {...form, discount_value: parseFloat(form.discount_value), min_order: parseFloat(form.min_order), max_uses: parseInt(form.max_uses)});
      toast.success("Coupon created"); load();
      setForm({ code: "", discount_type: "percent", discount_value: 10, min_order: 0, max_uses: 100, active: true });
    } catch (e) { toast.error("Failed"); }
  };
  return (
    <div className="space-y-6">
      <div className="border border-white/10 p-6">
        <div className="section-label mb-4">New Coupon</div>
        <div className="grid md:grid-cols-3 gap-4">
          <Inp l="Code" v={form.code} on={v=>setForm({...form,code:v})} tid="c-code" />
          <div>
            <label className="block text-[10px] font-mono-tech uppercase text-slate-400 mb-1">Type</label>
            <select value={form.discount_type} onChange={e=>setForm({...form,discount_type:e.target.value})} className="w-full px-3 py-2">
              <option value="percent">Percent (%)</option>
              <option value="flat">Flat (₹)</option>
            </select>
          </div>
          <Inp l="Value" v={form.discount_value} on={v=>setForm({...form,discount_value:v})} type="number" />
          <Inp l="Min Order (₹)" v={form.min_order} on={v=>setForm({...form,min_order:v})} type="number" />
          <Inp l="Max Uses" v={form.max_uses} on={v=>setForm({...form,max_uses:v})} type="number" />
        </div>
        <button data-testid="save-coupon" onClick={save} className="btn-primary-neo mt-4">Create Coupon</button>
      </div>
      <div className="border border-white/10">
        {coupons.map(c => (
          <div key={c.id} className="flex items-center gap-4 p-4 border-b border-white/5 last:border-b-0">
            <span className="font-mono-tech text-[#00FF66] uppercase">{c.code}</span>
            <span className="text-white">{c.discount_type === "percent" ? `${c.discount_value}%` : `₹${c.discount_value}`} off</span>
            <span className="text-slate-400 text-xs font-mono-tech ml-auto">Min ₹{c.min_order} · Used {c.uses || 0}/{c.max_uses}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Inp({ l, v, on, type = "text", tid, cls = "" }) {
  return (
    <div className={cls}>
      <label className="block text-[10px] font-mono-tech uppercase text-slate-400 mb-1">{l}</label>
      <input data-testid={tid} type={type} value={v} onChange={e => on(e.target.value)} className="w-full px-3 py-2" />
    </div>
  );
}
