import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Package, Clock, Lightning, Sparkle, Check, FilePdf } from "@phosphor-icons/react";
import api from "../lib/api";
import { useCart } from "../lib/cart";
import { toast } from "sonner";

export default function ProjectDetail() {
  const { slug } = useParams();
  const [project, setProject] = useState(null);
  const [adding, setAdding] = useState(false);
  const nav = useNavigate();
  const { refresh } = useCart();

  useEffect(() => { api.get(`/projects/${slug}`).then(r => setProject(r.data)); }, [slug]);

  if (!project) return <div className="max-w-7xl mx-auto px-6 py-20 text-slate-500">Loading…</div>;

  const addAll = async () => {
    setAdding(true);
    try {
      const r = await api.post(`/projects/${project.slug}/add-to-cart`);
      if (r.data.cart_id) localStorage.setItem("eh_cart_id", r.data.cart_id);
      await refresh();
      if (r.data.unavailable?.length) {
        toast.warning(`Added ${r.data.added.length} parts. ${r.data.unavailable.length} out of stock.`);
      } else {
        toast.success(`All ${r.data.added.length} parts added to cart`);
      }
      setTimeout(() => nav("/cart"), 900);
    } catch (e) {
      toast.error("Failed to add parts");
      setAdding(false);
    }
  };

  return (
    <div className="relative z-10">
      <div className="max-w-7xl mx-auto px-6 py-10">
        <Link to="/projects" className="inline-flex items-center gap-2 text-xs font-mono-tech uppercase tracking-widest text-slate-500 hover:text-slate-900 mb-8">
          <ArrowLeft size={14} /> All Projects
        </Link>

        <div className="grid lg:grid-cols-[1.2fr_1fr] gap-12 items-start">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="border border-slate-200 aspect-[16/10] overflow-hidden bg-slate-50">
              {project.image && <img src={project.image} alt={project.name} className="w-full h-full object-cover" />}
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              <span className="tag-pill" style={{
                color: project.difficulty === "Beginner" ? "#15803D" : project.difficulty === "Intermediate" ? "#1D4ED8" : "#C2410C",
                borderColor: project.difficulty === "Beginner" ? "#16A34A" : project.difficulty === "Intermediate" ? "#1E40AF" : "#EA580C",
                background: project.difficulty === "Beginner" ? "#F0FDF4" : project.difficulty === "Intermediate" ? "#EFF6FF" : "#FFF7ED",
              }}>{project.difficulty}</span>
              <span className="tag-pill flex items-center gap-1"><Clock size={10} /> {project.duration}</span>
              <span className="tag-pill flex items-center gap-1"><Package size={10} /> {project.items.length} parts</span>
            </div>

            <h1 className="font-display text-4xl md:text-5xl text-slate-900 mt-6 mb-4 leading-tight">{project.name}</h1>
            <p className="text-lg text-slate-500 leading-relaxed mb-8">{project.description}</p>

            {project.learn?.length > 0 && (
              <div>
                <div className="section-label mb-4">You'll learn</div>
                <ul className="space-y-3">
                  {project.learn.map((l, i) => (
                    <li key={i} className="flex items-start gap-3 text-slate-700">
                      <Sparkle size={16} weight="fill" className="text-blue-700 mt-1 flex-shrink-0" />
                      <span>{l}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {project.guide_url && (
              <a href={project.guide_url} target="_blank" rel="noreferrer"
                 data-testid="assembly-guide-btn"
                 className="btn-ghost-neo mt-8 inline-flex items-center gap-2">
                <FilePdf size={16} weight="fill" className="text-blue-700" /> Download Assembly Guide
              </a>
            )}
          </motion.div>

          {/* Right column: parts list */}
          <div className="lg:sticky lg:top-24">
            <div className="border border-slate-200 bg-white">
              <div className="p-6 border-b border-slate-200 flex items-center gap-3">
                <Lightning size={16} weight="fill" className="text-blue-700" />
                <div>
                  <div className="section-label">Bill of materials</div>
                  <div className="text-xs text-slate-500 mt-1 font-mono-tech">One-click adds everything below</div>
                </div>
              </div>
              <div className="divide-y divide-slate-100">
                {project.items.map((it) => (
                  <div key={it.product.id} className="flex items-center gap-3 p-4" data-testid={`bom-${it.product.sku}`}>
                    <Link to={`/product/${it.product.id}`} className="flex-shrink-0">
                      <img src={it.product.images?.[0]} alt={it.product.name}
                        className="w-14 h-14 object-cover border border-slate-200" />
                    </Link>
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest">{it.product.sku}</div>
                      <Link to={`/product/${it.product.id}`} className="text-sm text-slate-900 hover:text-blue-700 line-clamp-1">
                        {it.product.name}
                      </Link>
                      <div className="text-xs font-mono-tech text-slate-500 mt-0.5">
                        × {it.quantity} · ₹{it.unit_price.toFixed(0)} each
                      </div>
                    </div>
                    <div className="text-sm font-mono-tech text-slate-900 font-semibold">
                      ₹{it.line_total.toFixed(0)}
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-6 border-t border-slate-200 bg-slate-50">
                <div className="flex justify-between mb-4">
                  <span className="font-mono-tech text-xs uppercase tracking-widest text-slate-500">Total parts</span>
                  <span className="font-display text-3xl text-blue-700">₹{project.total_price.toLocaleString()}</span>
                </div>
                <button data-testid="add-all-btn" onClick={addAll} disabled={adding}
                  className="btn-primary-neo w-full flex items-center justify-center gap-2">
                  {adding ? <><Check size={16} /> Adding…</> : <><Sparkle size={16} weight="fill" /> Add All To Cart</>}
                </button>
                <p className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest text-center mt-3">
                  Free shipping on orders over ₹999
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
