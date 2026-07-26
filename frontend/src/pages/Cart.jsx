import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../lib/cart";
import { Trash, ArrowRight, Lightning } from "@phosphor-icons/react";
import { toast } from "sonner";
import api from "../lib/api";
import ProductCard from "../components/ProductCard";

export default function Cart() {
  const { items, subtotal, updateQty, removeItem } = useCart();
  const nav = useNavigate();
  const [recs, setRecs] = useState({ items: [], reason: "featured" });
  const shipping = subtotal >= 999 ? 0 : (subtotal > 0 ? 79 : 0);
  const tax = subtotal * 0.18;
  const total = subtotal + shipping + tax;

  useEffect(() => {
    api.get("/cart/recommendations", { params: { limit: 4 } })
      .then(r => setRecs(r.data))
      .catch(() => setRecs({ items: [], reason: "featured" }));
  }, [items.length]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 relative z-10">
      <div className="section-label mb-3">Cart</div>
      <h1 className="font-display text-4xl md:text-5xl text-white mb-10">Your Cart</h1>

      {items.length === 0 ? (
        <div className="border border-white/10 p-16 text-center">
          <p className="text-slate-400 mb-6">Your cart is empty.</p>
          <Link to="/catalog" className="btn-primary-neo inline-flex items-center gap-2">
            Browse Catalog <ArrowRight size={16} />
          </Link>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[1fr_360px] gap-10">
          <div className="border border-white/10">
            {items.map(it => {
              const p = it.product;
              const price = p.discount_price || p.price;
              return (
                <div key={it.product_id} data-testid={`cart-item-${p.sku}`} className="flex gap-4 p-4 border-b border-white/5 last:border-b-0">
                  <img src={p.images?.[0]} alt={p.name} className="w-24 h-24 object-cover border border-white/10" />
                  <div className="flex-1">
                    <div className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest">{p.sku}</div>
                    <Link to={`/product/${p.id}`} className="font-display text-lg text-white hover:text-[#00FF66]">{p.name}</Link>
                    <div className="text-[#00FF66] font-mono-tech mt-1">₹{price.toLocaleString()}</div>
                    <div className="flex items-center gap-3 mt-3">
                      <div className="flex border border-white/15">
                        <button data-testid={`cart-decr-${p.sku}`} onClick={() => updateQty(p.id, it.quantity - 1)} className="w-8 h-8 text-white hover:bg-white/5">−</button>
                        <div className="w-10 h-8 flex items-center justify-center font-mono-tech text-white border-x border-white/15">{it.quantity}</div>
                        <button data-testid={`cart-incr-${p.sku}`} onClick={() => updateQty(p.id, it.quantity + 1)} className="w-8 h-8 text-white hover:bg-white/5">+</button>
                      </div>
                      <button data-testid={`cart-remove-${p.sku}`} onClick={() => { removeItem(p.id); toast.success("Removed from cart"); }}
                        className="text-slate-400 hover:text-red-400"><Trash size={18} /></button>
                    </div>
                  </div>
                  <div className="font-display text-xl text-white">₹{(price * it.quantity).toLocaleString()}</div>
                </div>
              );
            })}
          </div>

          <aside className="border border-white/10 p-6 self-start">
            <div className="section-label mb-4">Summary</div>
            <div className="space-y-3 font-mono-tech text-sm">
              <Row label="Subtotal" value={`₹${subtotal.toLocaleString()}`} />
              <Row label="Shipping" value={shipping === 0 ? "FREE" : `₹${shipping}`} />
              <Row label="Tax (18%)" value={`₹${tax.toFixed(0)}`} />
              <div className="border-t border-white/10 pt-3 mt-3 flex justify-between text-white text-lg">
                <span>Total</span>
                <span data-testid="cart-total" className="text-[#00FF66]">₹{total.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
              </div>
            </div>
            <button data-testid="checkout-btn" onClick={() => nav("/checkout")} className="btn-primary-neo w-full mt-6 flex items-center justify-center gap-2">
              Checkout <ArrowRight size={16} />
            </button>
            <p className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest mt-4">
              Free shipping on orders over ₹999
            </p>
          </aside>
        </div>
      )}

      {/* COMPATIBILITY RECOMMENDER */}
      {recs.items.length > 0 && (
        <section className="mt-20" data-testid="cart-recommendations">
          <div className="flex items-center gap-3 mb-3">
            <Lightning size={16} weight="fill" className="text-[#00FF66]" />
            <div className="section-label">
              {recs.reason === "compatible" && items.length > 0 ? "Works with your cart" : "Popular this week"}
            </div>
          </div>
          <h2 className="font-display text-3xl md:text-4xl text-white mb-8">
            {recs.reason === "compatible" && items.length > 0
              ? <>Complete your build <span className="text-[#00FF66]">.</span></>
              : <>Add these to get started</>}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {recs.items.map((p, i) => <ProductCard key={p.id} product={p} index={i} />)}
          </div>
        </section>
      )}
    </div>
  );
}
function Row({ label, value }) {
  return <div className="flex justify-between text-slate-300"><span>{label}</span><span>{value}</span></div>;
}
