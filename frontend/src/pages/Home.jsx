import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Cpu, Robot, WifiHigh, Package, Wrench, BatteryCharging, Waveform, HardDrives, Sparkle } from "@phosphor-icons/react";
import api from "../lib/api";
import ProductCard from "../components/ProductCard";

const ICONS = {
  sensors: Waveform, microcontrollers: Cpu, processors: HardDrives,
  robotics: Robot, power: BatteryCharging, connectivity: WifiHigh,
  tools: Wrench, kits: Package,
};

export default function Home() {
  const [featured, setFeatured] = useState([]);
  const [cats, setCats] = useState([]);
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    api.get("/products", { params: { featured: true, limit: 8 }}).then(r => setFeatured(r.data.items));
    api.get("/categories").then(r => setCats(r.data));
    api.get("/projects").then(r => setProjects(r.data.slice(0, 3))).catch(() => {});
  }, []);

  return (
    <div className="relative z-10">
      {/* HERO */}
      <section className="relative border-b border-slate-200 overflow-hidden">
        <div className="absolute inset-0 grid-lines opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-transparent to-blue-50 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 py-24 md:py-32 relative">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div className="section-label mb-6">Sys.ready · Inventory Live</div>
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl leading-[0.9] text-slate-900 max-w-4xl">
              Where makers<br />
              <span className="text-blue-700">get their parts.</span>
            </h1>
            <p className="mt-8 text-lg text-slate-700 max-w-2xl leading-relaxed">
              Sensors, microcontrollers, robotic parts — with datasheets, pinouts, and compatibility tags. Ships within 48 hours. No minimum order.
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link to="/catalog" data-testid="hero-shop-btn" className="btn-primary-neo inline-flex items-center gap-2">
                Browse Catalog <ArrowRight size={16} />
              </Link>
              <Link to="/catalog?category=kits" data-testid="hero-kits-btn" className="btn-ghost-neo">Explore Kits</Link>
            </div>
            <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl">
              {[
                ["500+", "SKUs in stock"], ["48h", "Dispatch"], ["100%", "Genuine parts"], ["Free", "Ship over ₹999"],
              ].map(([k, v]) => (
                <div key={k} className="border-l border-slate-300 pl-4">
                  <div className="font-display text-3xl text-slate-900">{k}</div>
                  <div className="font-mono-tech text-[10px] uppercase tracking-widest text-slate-500 mt-1">{v}</div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <div className="section-label mb-3">01 · Categories</div>
            <h2 className="font-display text-4xl md:text-5xl text-slate-900">Shop by domain</h2>
          </div>
          <Link to="/catalog" className="hidden md:flex items-center gap-2 font-mono-tech text-xs uppercase tracking-widest text-slate-500 hover:text-blue-700">
            All <ArrowRight size={14} />
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 border-t border-l border-slate-200">
          {cats.map((c, i) => {
            const Icon = ICONS[c.id] || Package;
            return (
              <Link key={c.id} to={`/catalog?category=${c.id}`} data-testid={`cat-${c.id}`}
                className="p-8 border-r border-b border-slate-200 hover:bg-blue-50 hover:border-slate-900 transition-colors group">
                <Icon size={32} weight="duotone" className="text-blue-700 mb-6" />
                <div className="font-display text-xl text-slate-900 group-hover:text-blue-700 transition-colors">{c.name}</div>
                <div className="font-mono-tech text-[10px] uppercase tracking-widest text-slate-500 mt-2">
                  0{i + 1} → explore
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* FEATURED */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <div className="section-label mb-3">02 · Featured</div>
            <h2 className="font-display text-4xl md:text-5xl text-slate-900">Popular this week</h2>
          </div>
          <Link to="/catalog?featured=true" className="hidden md:flex items-center gap-2 font-mono-tech text-xs uppercase tracking-widest text-slate-500 hover:text-blue-700">
            All featured <ArrowRight size={14} />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {featured.map((p, i) => <ProductCard key={p.id} product={p} index={i} />)}
        </div>
      </section>

      {/* PROJECT KITS */}
      {projects.length > 0 && (
        <section className="max-w-7xl mx-auto px-6 py-20">
          <div className="flex items-end justify-between mb-10">
            <div>
              <div className="section-label mb-3">03 · Ready-to-build</div>
              <h2 className="font-display text-4xl md:text-5xl text-slate-900 flex items-center gap-3">
                Project kits <Sparkle size={32} weight="fill" className="text-blue-700" />
              </h2>
              <p className="text-slate-500 mt-3 max-w-xl">Pick a project. Every required part added in one click.</p>
            </div>
            <Link to="/projects" className="hidden md:flex items-center gap-2 font-mono-tech text-xs uppercase tracking-widest text-slate-500 hover:text-slate-900">
              All projects <ArrowRight size={14} />
            </Link>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {projects.map((p) => (
              <Link key={p.id} to={`/projects/${p.slug}`} className="tech-card block group" data-testid={`home-project-${p.slug}`}>
                <div className="aspect-video bg-slate-50 overflow-hidden">
                  {p.image && <img src={p.image} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />}
                </div>
                <div className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="tag-pill">{p.difficulty}</span>
                    <span className="tag-pill">{p.duration}</span>
                  </div>
                  <h3 className="font-display text-xl text-slate-900 group-hover:text-blue-700 mb-2">{p.name}</h3>
                  <div className="flex items-center justify-between">
                    <span className="font-display text-2xl text-blue-700">₹{p.total_price.toLocaleString()}</span>
                    <ArrowRight size={16} className="text-slate-500 group-hover:text-blue-700" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* CTA STRIP */}
      <section className="max-w-7xl mx-auto px-6 my-20">
        <div className="border border-slate-200 p-12 md:p-16 bg-slate-50 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-100 blur-3xl opacity-60" />
          <div className="section-label mb-4 relative">04 · Bundle & Save</div>
          <h3 className="font-display text-3xl md:text-5xl text-slate-900 max-w-2xl relative">
            Save 10% with code <span className="text-blue-700 font-mono-tech">WELCOME10</span> on your first order over ₹500.
          </h3>
          <Link to="/catalog" data-testid="cta-catalog-btn" className="btn-primary-neo mt-8 inline-flex items-center gap-2 relative">
            Start Shopping <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  );
}
