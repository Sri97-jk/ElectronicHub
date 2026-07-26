import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../lib/api";
import ProductCard from "../components/ProductCard";
import { FunnelSimple, X } from "@phosphor-icons/react";

export default function Catalog() {
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const [filters, setFilters] = useState({ brands: [], voltages: [], interfaces: [] });
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  const category = params.get("category") || "";
  const search = params.get("search") || "";
  const brand = params.get("brand") || "";
  const voltage = params.get("voltage") || "";
  const iface = params.get("interface") || "";
  const sort = params.get("sort") || "newest";
  const featured = params.get("featured") === "true";

  useEffect(() => {
    setLoading(true);
    const q = { limit: 60, sort };
    if (category) q.category = category;
    if (search) q.search = search;
    if (brand) q.brand = brand;
    if (voltage) q.voltage = voltage;
    if (iface) q.interface = iface;
    if (featured) q.featured = true;
    api.get("/products", { params: q }).then(r => {
      setProducts(r.data.items);
      setTotal(r.data.total);
      setLoading(false);
    });
    api.get("/products/filters", { params: category ? { category } : {} }).then(r => setFilters(r.data));
  }, [category, search, brand, voltage, iface, sort, featured]);

  const setParam = (k, v) => {
    const p = new URLSearchParams(params);
    if (v) p.set(k, v); else p.delete(k);
    setParams(p);
  };

  const clearAll = () => setParams({});

  return (
    <div className="max-w-7xl mx-auto px-6 py-12 relative z-10">
      <div className="mb-10">
        <div className="section-label mb-3">Catalog</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <h1 className="font-display text-4xl md:text-5xl text-slate-900">
            {search ? `"${search}"` : category ? category.charAt(0).toUpperCase() + category.slice(1) : featured ? "Featured" : "All Products"}
          </h1>
          <div className="flex items-center gap-3">
            <span className="font-mono-tech text-xs uppercase tracking-widest text-slate-500">{total} results</span>
            <select data-testid="sort-select" value={sort} onChange={(e) => setParam("sort", e.target.value)}
              className="text-xs font-mono-tech uppercase px-3 py-2">
              <option value="newest">Newest</option>
              <option value="price_asc">Price ↑</option>
              <option value="price_desc">Price ↓</option>
              <option value="rating">Top Rated</option>
            </select>
            <button data-testid="toggle-filters" onClick={() => setShowFilters(!showFilters)} className="md:hidden btn-ghost-neo text-xs" style={{padding:"8px 12px"}}>
              <FunnelSimple size={16} />
            </button>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-[240px_1fr] gap-8">
        <aside className={`${showFilters ? "block" : "hidden"} lg:block space-y-6`}>
          {(brand || voltage || iface || category || featured) && (
            <button onClick={clearAll} className="text-xs font-mono-tech uppercase text-blue-700 flex items-center gap-1">
              <X size={12} /> Clear all filters
            </button>
          )}
          <FilterGroup title="Brand" options={filters.brands} active={brand} onSelect={(v) => setParam("brand", v)} testid="brand" />
          <FilterGroup title="Voltage" options={filters.voltages} active={voltage} onSelect={(v) => setParam("voltage", v)} testid="voltage" />
          <FilterGroup title="Interface" options={filters.interfaces} active={iface} onSelect={(v) => setParam("interface", v)} testid="interface" />
        </aside>

        <div>
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => <div key={i} className="aspect-[3/4] tech-card animate-pulse" />)}
            </div>
          ) : products.length === 0 ? (
            <div className="border border-slate-200 p-16 text-center">
              <p className="text-slate-500">No products match your filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {products.map((p, i) => <ProductCard key={p.id} product={p} index={i} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilterGroup({ title, options, active, onSelect, testid }) {
  if (!options?.length) return null;
  return (
    <div>
      <div className="section-label mb-3">{title}</div>
      <div className="space-y-2">
        {options.map(o => (
          <button key={o} data-testid={`filter-${testid}-${o}`} onClick={() => onSelect(active === o ? "" : o)}
            className={`block text-sm font-mono-tech text-left w-full py-1 transition-colors ${active === o ? "text-blue-700" : "text-slate-500 hover:text-slate-900"}`}>
            <span className="mr-2">{active === o ? "▪" : "□"}</span> {o}
          </button>
        ))}
      </div>
    </div>
  );
}
