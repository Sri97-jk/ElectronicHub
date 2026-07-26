import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ShoppingCart, Heart, FilePdf, Star, ArrowLeft, CheckCircle } from "@phosphor-icons/react";
import api from "../lib/api";
import { useCart } from "../lib/cart";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import ProductCard from "../components/ProductCard";

export default function ProductDetail() {
  const { id } = useParams();
  const { addToCart } = useCart();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [qty, setQty] = useState(1);
  const [tab, setTab] = useState("specs");
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewText, setReviewText] = useState("");
  const [inWishlist, setInWishlist] = useState(false);

  useEffect(() => {
    api.get(`/products/${id}`).then(r => setData(r.data));
    if (user) api.get("/wishlist").then(r => setInWishlist(r.data.some(p => p.id === id)));
  }, [id, user]);

  if (!data) return <div className="max-w-7xl mx-auto px-6 py-20 text-slate-400">Loading…</div>;
  const { product, related, reviews } = data;
  const price = product.discount_price || product.price;

  const handleAdd = async () => {
    await addToCart(product.id, qty);
    toast.success(`Added ${qty} × ${product.name}`);
  };
  const toggleWish = async () => {
    if (!user) return toast.error("Please login to save to wishlist");
    const r = await api.post(`/wishlist/toggle/${product.id}`);
    setInWishlist(r.data.in_wishlist);
    toast.success(r.data.in_wishlist ? "Added to wishlist" : "Removed from wishlist");
  };
  const submitReview = async () => {
    if (!user) return toast.error("Login required to review");
    try {
      await api.post("/reviews", { product_id: product.id, rating: reviewRating, comment: reviewText });
      setReviewText(""); setReviewRating(5);
      const r = await api.get(`/products/${id}`);
      setData(r.data);
      toast.success("Review posted");
    } catch { toast.error("Failed to post review"); }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 relative z-10">
      <Link to="/catalog" className="inline-flex items-center gap-2 text-xs font-mono-tech uppercase tracking-widest text-slate-400 hover:text-[#00FF66] mb-8">
        <ArrowLeft size={14} /> Back to Catalog
      </Link>

      <div className="grid lg:grid-cols-2 gap-12">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border border-white/10 bg-[#0A1017] aspect-square overflow-hidden">
          {product.images?.[0] && <img src={product.images[0]} alt={product.name} className="w-full h-full object-cover" />}
        </motion.div>

        <div>
          <div className="text-xs font-mono-tech text-slate-500 uppercase tracking-widest mb-3">
            {product.sku} · {product.brand || "Generic"} · {product.category}
          </div>
          <h1 className="font-display text-3xl md:text-5xl text-white leading-tight mb-4">{product.name}</h1>
          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center gap-1">
              {[1,2,3,4,5].map(i => <Star key={i} size={16} weight={i <= (product.rating_avg || 0) ? "fill" : "regular"} className="text-[#00FF66]" />)}
            </div>
            <span className="text-xs font-mono-tech text-slate-400">{product.rating_count || 0} reviews</span>
          </div>

          <div className="flex items-baseline gap-3 mb-6">
            <span className="font-display text-5xl text-[#00FF66]">₹{price.toLocaleString()}</span>
            {product.discount_price && <span className="text-lg text-slate-500 line-through font-mono-tech">₹{product.price}</span>}
          </div>

          <div className="flex flex-wrap gap-2 mb-6">
            {product.voltage && <span className="tag-pill tag-pill-accent">VDD {product.voltage}</span>}
            {product.interface && <span className="tag-pill tag-pill-accent">{product.interface}</span>}
            {product.stock_qty > 0 ? (
              <span className="tag-pill" style={{color: "#00FF66", borderColor: "rgba(0,255,102,0.4)"}}>
                <CheckCircle size={12} className="inline mr-1" /> {product.stock_qty} in stock
              </span>
            ) : <span className="tag-pill">Out of stock</span>}
          </div>

          <p className="text-slate-300 leading-relaxed mb-8">{product.description}</p>

          <div className="flex items-center gap-3 mb-6">
            <div className="flex border border-white/15">
              <button data-testid="qty-decr" onClick={() => setQty(Math.max(1, qty - 1))} className="w-10 h-12 font-mono-tech text-white hover:bg-white/5">−</button>
              <div data-testid="qty-display" className="w-12 h-12 flex items-center justify-center font-mono-tech text-white border-x border-white/15">{qty}</div>
              <button data-testid="qty-incr" onClick={() => setQty(qty + 1)} className="w-10 h-12 font-mono-tech text-white hover:bg-white/5">+</button>
            </div>
            <button data-testid="detail-add-cart" onClick={handleAdd} disabled={product.stock_qty <= 0} className="btn-primary-neo flex-1 flex items-center justify-center gap-2">
              <ShoppingCart size={16} /> Add to Cart
            </button>
            <button data-testid="wishlist-btn" onClick={toggleWish} className="btn-ghost-neo" style={{padding: "12px 14px"}}>
              <Heart size={18} weight={inWishlist ? "fill" : "regular"} className={inWishlist ? "text-[#00FF66]" : ""} />
            </button>
          </div>

          {product.datasheet_url && (
            <a href={product.datasheet_url} target="_blank" rel="noreferrer" className="btn-ghost-neo inline-flex items-center gap-2 mb-6">
              <FilePdf size={16} /> Download Datasheet
            </a>
          )}

          {product.compatible_with?.length > 0 && (
            <div>
              <div className="section-label mb-3">Compatible With</div>
              <div className="flex flex-wrap gap-2">
                {product.compatible_with.map(c => <span key={c} className="tag-pill">{c}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* TABS */}
      <div className="mt-16 border-t border-white/10">
        <div className="flex gap-8 border-b border-white/10">
          {["specs", "reviews"].map(t => (
            <button key={t} data-testid={`tab-${t}`} onClick={() => setTab(t)}
              className={`py-4 font-mono-tech text-xs uppercase tracking-widest transition-colors ${tab === t ? "text-[#00FF66] border-b border-[#00FF66]" : "text-slate-400"}`}>
              {t === "specs" ? "Specifications" : `Reviews (${reviews.length})`}
            </button>
          ))}
        </div>

        {tab === "specs" && (
          <table className="spec-table w-full mt-8 max-w-2xl">
            <tbody>
              {Object.entries(product.specs || {}).map(([k, v]) => (
                <tr key={k}><th className="text-left w-40">{k}</th><td className="text-white">{v}</td></tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === "reviews" && (
          <div className="mt-8 space-y-8 max-w-3xl">
            {user && (
              <div className="border border-white/10 p-6">
                <div className="section-label mb-4">Post a Review</div>
                <div className="flex gap-1 mb-3">
                  {[1,2,3,4,5].map(n => (
                    <button key={n} data-testid={`star-${n}`} onClick={() => setReviewRating(n)}>
                      <Star size={22} weight={n <= reviewRating ? "fill" : "regular"} className="text-[#00FF66]" />
                    </button>
                  ))}
                </div>
                <textarea data-testid="review-text" value={reviewText} onChange={(e) => setReviewText(e.target.value)} rows={3}
                  placeholder="What did you think?" className="w-full px-3 py-2 text-sm" />
                <button data-testid="submit-review" onClick={submitReview} className="btn-primary-neo mt-3">Submit Review</button>
              </div>
            )}
            {reviews.length === 0 && <p className="text-slate-400">No reviews yet. Be the first!</p>}
            {reviews.map(r => (
              <div key={r.id} className="border-b border-white/5 pb-6">
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-display text-white">{r.user_name}</span>
                  <div className="flex">
                    {[1,2,3,4,5].map(i => <Star key={i} size={12} weight={i <= r.rating ? "fill" : "regular"} className="text-[#00FF66]" />)}
                  </div>
                </div>
                <p className="text-slate-300 text-sm">{r.comment}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* RELATED */}
      {related?.length > 0 && (
        <div className="mt-20">
          <div className="section-label mb-3">Related</div>
          <h2 className="font-display text-3xl text-white mb-8">You might also need</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
            {related.slice(0, 4).map((p, i) => <ProductCard key={p.id} product={p} index={i} />)}
          </div>
        </div>
      )}
    </div>
  );
}
