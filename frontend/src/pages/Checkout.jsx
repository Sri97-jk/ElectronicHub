import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useCart } from "../lib/cart";
import { useAuth } from "../lib/auth";
import api from "../lib/api";
import { toast } from "sonner";
import { ArrowRight } from "@phosphor-icons/react";

export default function Checkout() {
  const { items, subtotal } = useCart();
  const { user } = useAuth();
  const nav = useNavigate();
  const [addr, setAddr] = useState({
    full_name: user?.name || "", phone: "", line1: "", line2: "",
    city: "", state: "", pincode: "", country: "India"
  });
  const [couponCode, setCouponCode] = useState("");
  const [coupon, setCoupon] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (items.length === 0) nav("/cart");
  }, [items, nav]);

  const discount = coupon ? (coupon.discount_type === "percent" ? subtotal * (coupon.discount_value / 100) : coupon.discount_value) : 0;
  const shipping = subtotal >= 999 ? 0 : 79;
  const tax = (subtotal - discount) * 0.18;
  const total = subtotal - discount + shipping + tax;

  const applyCoupon = async () => {
    try {
      const r = await api.post("/coupons/validate", { code: couponCode, subtotal });
      setCoupon(r.data.coupon);
      toast.success(`Coupon applied: -₹${r.data.discount.toFixed(0)}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Invalid coupon");
    }
  };

  const submit = async () => {
    for (const [k, v] of Object.entries(addr)) {
      if (!v && k !== "line2") return toast.error(`Please fill ${k.replace("_", " ")}`);
    }
    setLoading(true);
    try {
      const r = await api.post("/checkout/session", {
        origin_url: window.location.origin,
        address: addr, coupon_code: coupon?.code,
      });
      window.location.href = r.data.checkout_url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Checkout failed");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-12 relative z-10">
      <div className="section-label mb-3">Checkout</div>
      <h1 className="font-display text-4xl md:text-5xl text-slate-900 mb-10">Shipping & Payment</h1>

      <div className="grid lg:grid-cols-[1fr_380px] gap-10">
        <div className="space-y-6">
          <div className="border border-slate-200 p-6">
            <div className="section-label mb-4">01 · Shipping Address</div>
            <div className="grid md:grid-cols-2 gap-4">
              <Field label="Full Name" testid="ck-name" value={addr.full_name} onChange={v => setAddr({...addr, full_name: v})} />
              <Field label="Phone" testid="ck-phone" value={addr.phone} onChange={v => setAddr({...addr, phone: v})} />
              <Field label="Address Line 1" testid="ck-line1" value={addr.line1} onChange={v => setAddr({...addr, line1: v})} className="md:col-span-2" />
              <Field label="Address Line 2 (optional)" testid="ck-line2" value={addr.line2} onChange={v => setAddr({...addr, line2: v})} className="md:col-span-2" />
              <Field label="City" testid="ck-city" value={addr.city} onChange={v => setAddr({...addr, city: v})} />
              <Field label="State" testid="ck-state" value={addr.state} onChange={v => setAddr({...addr, state: v})} />
              <Field label="Pincode" testid="ck-pincode" value={addr.pincode} onChange={v => setAddr({...addr, pincode: v})} />
              <Field label="Country" testid="ck-country" value={addr.country} onChange={v => setAddr({...addr, country: v})} />
            </div>
          </div>

          <div className="border border-slate-200 p-6">
            <div className="section-label mb-4">02 · Coupon</div>
            <div className="flex gap-3">
              <input data-testid="coupon-input" value={couponCode} onChange={e => setCouponCode(e.target.value)} placeholder="Try WELCOME10 or MAKER100" className="flex-1 px-3 py-2 text-sm" />
              <button data-testid="apply-coupon" onClick={applyCoupon} className="btn-ghost-neo">Apply</button>
            </div>
            {coupon && <div className="mt-3 text-blue-700 font-mono-tech text-xs uppercase">✓ {coupon.code} applied</div>}
          </div>
        </div>

        <aside className="border border-slate-200 p-6 self-start">
          <div className="section-label mb-4">Order Summary</div>
          <div className="max-h-64 overflow-y-auto space-y-3 mb-4">
            {items.map(it => (
              <div key={it.product_id} className="flex gap-3 text-sm">
                <img src={it.product.images?.[0]} alt="" className="w-12 h-12 object-cover border border-slate-200" />
                <div className="flex-1 min-w-0">
                  <div className="text-slate-900 truncate">{it.product.name}</div>
                  <div className="text-slate-500 font-mono-tech text-xs">× {it.quantity}</div>
                </div>
                <div className="text-slate-900 font-mono-tech">₹{((it.product.discount_price || it.product.price) * it.quantity).toFixed(0)}</div>
              </div>
            ))}
          </div>
          <div className="space-y-2 font-mono-tech text-sm border-t border-slate-200 pt-4">
            <Row label="Subtotal" value={`₹${subtotal.toFixed(0)}`} />
            {discount > 0 && <Row label="Discount" value={`-₹${discount.toFixed(0)}`} accent />}
            <Row label="Shipping" value={shipping === 0 ? "FREE" : `₹${shipping}`} />
            <Row label="Tax (18%)" value={`₹${tax.toFixed(0)}`} />
            <div className="flex justify-between text-slate-900 text-lg pt-3 border-t border-slate-200">
              <span>Total</span>
              <span data-testid="checkout-total" className="text-blue-700">₹{total.toFixed(0)}</span>
            </div>
          </div>
          <button data-testid="pay-btn" onClick={submit} disabled={loading} className="btn-primary-neo w-full mt-6 flex items-center justify-center gap-2">
            {loading ? "Redirecting…" : <>Pay Now <ArrowRight size={16} /></>}
          </button>
          <p className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest mt-4 text-center">
            Secured by Stripe · Test card 4242 4242 4242 4242
          </p>
        </aside>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, className = "", testid }) {
  return (
    <div className={className}>
      <label className="block text-[10px] font-mono-tech uppercase tracking-widest text-slate-500 mb-1">{label}</label>
      <input data-testid={testid} value={value} onChange={e => onChange(e.target.value)} className="w-full px-3 py-2 text-sm" />
    </div>
  );
}
function Row({ label, value, accent }) {
  return <div className="flex justify-between"><span className="text-slate-700">{label}</span><span className={accent ? "text-blue-700" : "text-slate-900"}>{value}</span></div>;
}
