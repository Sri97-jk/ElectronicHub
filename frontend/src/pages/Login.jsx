import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

export default function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await login(email, password);
      toast.success(`Welcome back, ${user.name}`);
      nav(user.role === "admin" ? "/admin" : "/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    }
    setLoading(false);
  };

  return (
    <div className="max-w-md mx-auto px-6 py-20 relative z-10">
      <div className="section-label mb-3">Access Terminal</div>
      <h1 className="font-display text-4xl text-slate-900 mb-10">Log in</h1>
      <form onSubmit={submit} className="space-y-4 border border-slate-200 p-8">
        <div>
          <label className="block text-[10px] font-mono-tech uppercase tracking-widest text-slate-500 mb-1">Email</label>
          <input data-testid="login-email" type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full px-3 py-2" />
        </div>
        <div>
          <label className="block text-[10px] font-mono-tech uppercase tracking-widest text-slate-500 mb-1">Password</label>
          <input data-testid="login-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full px-3 py-2" />
        </div>
        <button data-testid="login-submit" type="submit" disabled={loading} className="btn-primary-neo w-full">
          {loading ? "Signing in…" : "Sign In"}
        </button>
        <p className="text-center text-sm text-slate-500 pt-4">
          No account? <Link to="/signup" className="text-blue-700">Create one</Link>
        </p>
      </form>
    </div>
  );
}
