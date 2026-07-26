import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

export default function Signup() {
  const nav = useNavigate();
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 6) return toast.error("Password must be at least 6 characters");
    setLoading(true);
    try {
      await signup(name, email, password);
      toast.success("Welcome to ElectronicHub!");
      nav("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Signup failed");
    }
    setLoading(false);
  };

  return (
    <div className="max-w-md mx-auto px-6 py-20 relative z-10">
      <div className="section-label mb-3">Register</div>
      <h1 className="font-display text-4xl text-white mb-10">Create Account</h1>
      <form onSubmit={submit} className="space-y-4 border border-white/10 p-8">
        <div>
          <label className="block text-[10px] font-mono-tech uppercase tracking-widest text-slate-400 mb-1">Name</label>
          <input data-testid="signup-name" value={name} onChange={e => setName(e.target.value)} required className="w-full px-3 py-2" />
        </div>
        <div>
          <label className="block text-[10px] font-mono-tech uppercase tracking-widest text-slate-400 mb-1">Email</label>
          <input data-testid="signup-email" type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-3 py-2" />
        </div>
        <div>
          <label className="block text-[10px] font-mono-tech uppercase tracking-widest text-slate-400 mb-1">Password</label>
          <input data-testid="signup-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full px-3 py-2" />
        </div>
        <button data-testid="signup-submit" type="submit" disabled={loading} className="btn-primary-neo w-full">
          {loading ? "Creating…" : "Create Account"}
        </button>
        <p className="text-center text-sm text-slate-400 pt-4">
          Already registered? <Link to="/login" className="text-[#00FF66]">Log in</Link>
        </p>
      </form>
    </div>
  );
}
