import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Wrench, Clock, Package } from "@phosphor-icons/react";
import api from "../lib/api";

const DIFF_COLORS = {
  Beginner: "text-green-700 border-green-500 bg-green-50",
  Intermediate: "text-blue-700 border-blue-500 bg-blue-50",
  Advanced: "text-orange-700 border-orange-500 bg-orange-50",
};

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/projects").then(r => { setProjects(r.data); setLoading(false); });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-16 relative z-10">
      <div className="section-label mb-3">Curated builds</div>
      <h1 className="font-display text-4xl md:text-6xl text-slate-900 mb-4">Project Kits</h1>
      <p className="text-slate-500 max-w-2xl mb-14 leading-relaxed">
        Skip the parts-list hunt. Pick a project, review the components, and one-click add everything to your cart.
        Curated by makers, priced honestly.
      </p>
      {loading ? (
        <div className="grid md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => <div key={i} className="aspect-[4/3] bg-slate-100 animate-pulse" />)}
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {projects.map((p, i) => (
            <motion.div key={p.id} initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{duration:0.4, delay:i*0.06}}>
              <Link to={`/projects/${p.slug}`} data-testid={`project-card-${p.slug}`} className="tech-card block group">
                <div className="aspect-[16/9] bg-slate-50 overflow-hidden">
                  {p.image && <img src={p.image} alt={p.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />}
                </div>
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <span className={`tag-pill ${DIFF_COLORS[p.difficulty]?.replace('text-','text-').split(' ').join(' ')}`}
                      style={{
                        color: p.difficulty === "Beginner" ? "#15803D" : p.difficulty === "Intermediate" ? "#1D4ED8" : "#C2410C",
                        borderColor: p.difficulty === "Beginner" ? "#16A34A" : p.difficulty === "Intermediate" ? "#1E40AF" : "#EA580C",
                        background: p.difficulty === "Beginner" ? "#F0FDF4" : p.difficulty === "Intermediate" ? "#EFF6FF" : "#FFF7ED",
                      }}>
                      {p.difficulty}
                    </span>
                    <span className="tag-pill flex items-center gap-1"><Clock size={10} /> {p.duration}</span>
                    <span className="tag-pill flex items-center gap-1"><Package size={10} /> {p.parts_count} parts</span>
                  </div>
                  <h3 className="font-display text-2xl text-slate-900 group-hover:text-blue-700 transition-colors mb-2">{p.name}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed mb-4 line-clamp-2">{p.tagline}</p>
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest">Total parts cost</div>
                      <div className="font-display text-3xl text-blue-700 mt-1">₹{p.total_price.toLocaleString()}</div>
                    </div>
                    <div className="flex items-center gap-2 font-mono-tech text-xs uppercase tracking-widest text-slate-900 group-hover:text-blue-700">
                      Build it <ArrowRight size={14} />
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
