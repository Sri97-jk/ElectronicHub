import { Link, useNavigate } from "react-router-dom";
import { ShoppingCart, User, Package, Heart, MagnifyingGlass, List, X, SignOut, Gauge } from "@phosphor-icons/react";
import { useState } from "react";
import { useAuth } from "../lib/auth";
import { useCart } from "../lib/cart";

export default function Header() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const nav = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [q, setQ] = useState("");

  const submitSearch = (e) => {
    e.preventDefault();
    if (q.trim()) nav(`/catalog?search=${encodeURIComponent(q.trim())}`);
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/75 border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-6">
        <Link to="/" data-testid="header-logo" className="flex items-center gap-3">
          <img src="/logo.png" alt="ElectronicHub" className="h-9 w-auto" />
        </Link>

        <nav className="hidden lg:flex items-center gap-6 font-mono-tech text-xs uppercase tracking-widest text-slate-700">
          <Link to="/catalog" data-testid="nav-catalog" className="hover:text-blue-700 transition-colors">Catalog</Link>
          <Link to="/projects" data-testid="nav-projects" className="hover:text-blue-700 transition-colors">Projects</Link>
          <Link to="/catalog?category=kits" data-testid="nav-kits" className="hover:text-blue-700 transition-colors">Kits</Link>
          <Link to="/catalog?category=microcontrollers" data-testid="nav-mcu" className="hover:text-blue-700 transition-colors">Boards</Link>
          <Link to="/catalog?featured=true" data-testid="nav-featured" className="hover:text-blue-700 transition-colors">Featured</Link>
        </nav>

        <form onSubmit={submitSearch} className="flex-1 max-w-md hidden md:block">
          <div className="relative">
            <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input
              data-testid="search-input"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search sensors, boards, kits…"
              className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 focus:outline-none focus:border-slate-900"
            />
          </div>
        </form>

        <div className="flex items-center gap-4 ml-auto">
          {user ? (
            <div className="hidden md:flex items-center gap-3">
              <Link to="/wishlist" data-testid="nav-wishlist" title="Wishlist" className="text-slate-700 hover:text-blue-700">
                <Heart size={20} />
              </Link>
              <Link to="/orders" data-testid="nav-orders" title="Orders" className="text-slate-700 hover:text-blue-700">
                <Package size={20} />
              </Link>
              {user.role === "admin" && (
                <Link to="/admin" data-testid="nav-admin" title="Admin" className="text-slate-700 hover:text-blue-700">
                  <Gauge size={20} />
                </Link>
              )}
              <div className="relative group">
                <button data-testid="user-menu-btn" className="text-slate-700 hover:text-blue-700 flex items-center gap-2">
                  <User size={20} />
                  <span className="text-xs font-mono-tech uppercase">{user.name.split(" ")[0]}</span>
                </button>
                <div className="absolute right-0 top-full mt-2 w-40 bg-slate-50 border border-slate-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity">
                  <button data-testid="logout-btn" onClick={logout} className="w-full text-left px-4 py-2 text-xs font-mono-tech uppercase text-slate-700 hover:bg-slate-50 hover:text-blue-700 flex items-center gap-2">
                    <SignOut size={14} /> Logout
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="hidden md:flex items-center gap-3">
              <Link to="/login" data-testid="nav-login" className="text-xs font-mono-tech uppercase tracking-widest text-slate-700 hover:text-blue-700">
                Login
              </Link>
              <Link to="/signup" data-testid="nav-signup" className="btn-primary-neo text-xs" style={{padding: "8px 16px"}}>
                Sign Up
              </Link>
            </div>
          )}

          <Link to="/cart" data-testid="nav-cart" className="relative text-slate-900 hover:text-blue-700">
            <ShoppingCart size={22} weight="duotone" />
            {count > 0 && (
              <span data-testid="cart-count" className="absolute -top-2 -right-2 bg-slate-900 text-white text-[10px] font-bold w-5 h-5 flex items-center justify-center font-mono-tech">
                {count}
              </span>
            )}
          </Link>

          <button data-testid="mobile-menu-btn" onClick={() => setMobileOpen(!mobileOpen)} className="lg:hidden text-slate-700">
            {mobileOpen ? <X size={22} /> : <List size={22} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-6 py-4 space-y-3 font-mono-tech text-xs uppercase tracking-widest text-slate-700">
          <Link to="/catalog" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Catalog</Link>
          <Link to="/projects" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Projects</Link>
          <Link to="/catalog?category=kits" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Kits</Link>
          {user ? (
            <>
              <Link to="/orders" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Orders</Link>
              <Link to="/wishlist" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Wishlist</Link>
              {user.role === "admin" && <Link to="/admin" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Admin</Link>}
              <button onClick={() => { logout(); setMobileOpen(false); }} className="block hover:text-blue-700">Logout</button>
            </>
          ) : (
            <>
              <Link to="/login" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Login</Link>
              <Link to="/signup" onClick={() => setMobileOpen(false)} className="block hover:text-blue-700">Sign Up</Link>
            </>
          )}
        </div>
      )}
    </header>
  );
}
