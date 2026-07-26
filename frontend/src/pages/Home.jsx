import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Cpu, Robot, WifiHigh, Package, Wrench, BatteryCharging, Waveform, HardDrives } from "@phosphor-icons/react";
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

  useEffect(() => {
    api.get("/products", { params: { featured: true, limit: 8 }}).then(r => setFeatured(r.data.items));
    api.get("/categories").then(r => setCats(r.data));
  }, []);

  return (
    <div className="relative z-10">
      {/* HERO */}
      <section className="relative border-b border-white/10 overflow-hidden">
        <div className="absolute inset-0 grid-lines opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0066FF]/10 via-transparent to-[#00FF66]/5 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 py-24 md:py-32 relative">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div className="section-label mb-6">Sys.ready · Inventory Live</div>
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl leading-[0.9] text-white max-w-4xl">
              Where makers<br />
              <span className="text-[#00FF66]">get their parts.</span>
            </h1>
            <p className="mt-8 text-lg text-slate-300 max-w-2xl leading-relaxed">
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
                <div key={k} className="border-l border-[#00FF66]/40 pl-4">
                  <div className="font-display text-3xl text-white">{k}</div>
                  <div className="font-mono-tech text-[10px] uppercase tracking-widest text-slate-400 mt-1">{v}</div>
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
            <h2 className="font-display text-4xl md:text-5xl text-white">Shop by domain</h2>
          </div>
          <Link to="/catalog" className="hidden md:flex items-center gap-2 font-mono-tech text-xs uppercase tracking-widest text-slate-400 hover:text-[#00FF66]">
            All <ArrowRight size={14} />
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 border-t border-l border-white/10">
          {cats.map((c, i) => {
            const Icon = ICONS[c.id] || Package;
            return (
              <Link key={c.id} to={`/catalog?category=${c.id}`} data-testid={`cat-${c.id}`}
                className="p-8 border-r border-b border-white/10 hover:bg-[#00FF66]/5 hover:border-[#00FF66]/40 transition-colors group">
                <Icon size={32} weight="duotone" className="text-[#00FF66] mb-6" />
                <div className="font-display text-xl text-white group-hover:text-[#00FF66] transition-colors">{c.name}</div>
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
            <h2 className="font-display text-4xl md:text-5xl text-white">Popular this week</h2>
          </div>
          <Link to="/catalog?featured=true" className="hidden md:flex items-center gap-2 font-mono-tech text-xs uppercase tracking-widest text-slate-400 hover:text-[#00FF66]">
            All featured <ArrowRight size={14} />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {featured.map((p, i) => <ProductCard key={p.id} product={p} index={i} />)}
        </div>
      </section>

      {/* CTA STRIP */}
      <section className="max-w-7xl mx-auto px-6 my-20">
        <div className="border border-[#00FF66]/30 p-12 md:p-16 bg-gradient-to-br from-[#00FF66]/5 to-transparent relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#00FF66]/10 blur-3xl" />
          <div className="section-label mb-4 relative">03 · Bundle & Save</div>
          <h3 className="font-display text-3xl md:text-5xl text-white max-w-2xl relative">
            Save 15% with code <span className="text-[#00FF66] font-mono-tech">WELCOME10</span> on your first order over ₹500.
          </h3>
          <Link to="/catalog" data-testid="cta-catalog-btn" className="btn-primary-neo mt-8 inline-flex items-center gap-2 relative">
            Start Shopping <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  );
}
