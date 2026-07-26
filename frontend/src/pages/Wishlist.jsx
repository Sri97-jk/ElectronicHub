import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import ProductCard from "../components/ProductCard";

export default function Wishlist() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/wishlist").then(r => setItems(r.data)); }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 relative z-10">
      <div className="section-label mb-3">Saved</div>
      <h1 className="font-display text-4xl md:text-5xl text-slate-900 mb-10">Wishlist</h1>
      {items.length === 0 ? (
        <div className="border border-slate-200 p-16 text-center">
          <p className="text-slate-500 mb-6">No items saved yet.</p>
          <Link to="/catalog" className="btn-primary-neo inline-block">Browse Catalog</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {items.map((p, i) => <ProductCard key={p.id} product={p} index={i} />)}
        </div>
      )}
    </div>
  );
}
