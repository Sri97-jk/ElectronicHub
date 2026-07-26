import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-white/10 mt-24 bg-[#050A0F] relative z-10">
      <div className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <img src="/logo.png" alt="ElectronicHub" className="h-10 mb-4" />
          <p className="text-slate-400 text-sm max-w-sm leading-relaxed">
            The maker's marketplace. Sensors, boards, and robotics parts — with the specs and datasheets you actually need.
          </p>
          <div className="mt-6 flex items-center gap-3 text-xs font-mono-tech text-slate-500 uppercase tracking-widest">
            <span className="pulse-dot" /> Live inventory · Ships within 48h
          </div>
        </div>
        <div>
          <div className="section-label mb-4">Shop</div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><Link to="/catalog?category=sensors" className="hover:text-[#00FF66]">Sensors</Link></li>
            <li><Link to="/catalog?category=microcontrollers" className="hover:text-[#00FF66]">Microcontrollers</Link></li>
            <li><Link to="/catalog?category=robotics" className="hover:text-[#00FF66]">Robotic Parts</Link></li>
            <li><Link to="/catalog?category=kits" className="hover:text-[#00FF66]">Kits & Bundles</Link></li>
          </ul>
        </div>
        <div>
          <div className="section-label mb-4">Company</div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><Link to="/catalog" className="hover:text-[#00FF66]">All Products</Link></li>
            <li><Link to="/orders" className="hover:text-[#00FF66]">Order Tracking</Link></li>
            <li><span className="hover:text-[#00FF66] cursor-pointer">Return Policy</span></li>
            <li><span className="hover:text-[#00FF66] cursor-pointer">Contact</span></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/5 py-6 text-center text-xs font-mono-tech uppercase tracking-widest text-slate-500">
        © 2026 ElectronicHub · Built for makers
      </div>
    </footer>
  );
}
