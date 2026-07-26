import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Heart, ShoppingCart } from "@phosphor-icons/react";
import { useCart } from "../lib/cart";
import { toast } from "sonner";

export default function ProductCard({ product, index = 0 }) {
  const { addToCart } = useCart();
  const price = product.discount_price || product.price;
  const hasDiscount = !!product.discount_price;
  const outOfStock = product.stock_qty <= 0;

  const handleAdd = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await addToCart(product.id, 1);
      toast.success(`${product.name} added to cart`);
    } catch { toast.error("Failed to add to cart"); }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04 }}
      className="tech-card group relative flex flex-col"
      data-testid={`product-card-${product.sku}`}
    >
      <Link to={`/product/${product.id}`} className="block">
        <div className="aspect-square bg-[#0A1017] border-b border-white/10 overflow-hidden relative">
          {product.images?.[0] && (
            <img src={product.images[0]} alt={product.name}
              className="w-full h-full object-cover opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-transform duration-500" />
          )}
          {hasDiscount && (
            <div className="absolute top-3 left-3 bg-[#00FF66] text-black px-2 py-1 font-mono-tech text-[10px] uppercase tracking-widest font-bold">
              -{Math.round((1 - product.discount_price / product.price) * 100)}%
            </div>
          )}
          {outOfStock && (
            <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
              <span className="tag-pill">Out of Stock</span>
            </div>
          )}
        </div>
        <div className="p-5">
          <div className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest mb-2">
            {product.sku} · {product.brand || "Generic"}
          </div>
          <h3 className="font-display text-lg leading-tight text-white mb-3 line-clamp-2 group-hover:text-[#00FF66] transition-colors">
            {product.name}
          </h3>
          <div className="flex items-center gap-2 mb-3">
            {product.voltage && <span className="tag-pill">{product.voltage}</span>}
            {product.interface && <span className="tag-pill">{product.interface}</span>}
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-2xl text-[#00FF66]">₹{price.toLocaleString()}</span>
            {hasDiscount && <span className="text-xs text-slate-500 line-through font-mono-tech">₹{product.price}</span>}
          </div>
        </div>
      </Link>
      <button
        onClick={handleAdd}
        disabled={outOfStock}
        data-testid={`add-to-cart-${product.sku}`}
        className="btn-primary-neo w-full mt-auto flex items-center justify-center gap-2"
      >
        <ShoppingCart size={16} /> Add to Cart
      </button>
    </motion.div>
  );
}
