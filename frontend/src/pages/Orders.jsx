import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Package } from "@phosphor-icons/react";

const STATUS_COLORS = {
  pending_payment: "text-yellow-400",
  confirmed: "text-blue-400",
  shipped: "text-purple-400",
  delivered: "text-blue-700",
  cancelled: "text-red-400",
};

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/orders").then(r => { setOrders(r.data); setLoading(false); });
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-6 py-12 relative z-10">
      <div className="section-label mb-3">My Orders</div>
      <h1 className="font-display text-4xl md:text-5xl text-slate-900 mb-10">Order History</h1>
      {loading ? <p className="text-slate-500">Loading…</p> : orders.length === 0 ? (
        <div className="border border-slate-200 p-16 text-center">
          <Package size={40} className="text-slate-500 mx-auto mb-4" />
          <p className="text-slate-500 mb-6">No orders yet.</p>
          <Link to="/catalog" className="btn-primary-neo inline-block">Start Shopping</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map(o => (
            <div key={o.id} data-testid={`order-${o.id}`} className="border border-slate-200 p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-[10px] font-mono-tech text-slate-500 uppercase tracking-widest">
                    Order #{o.id.slice(0, 8)} · {new Date(o.created_at).toLocaleString()}
                  </div>
                  <div className={`font-mono-tech text-sm uppercase tracking-widest mt-2 ${STATUS_COLORS[o.status] || "text-slate-700"}`}>
                    {o.status.replace("_", " ")}
                    {o.tracking_number && <span className="ml-2 text-slate-500">· Track: {o.tracking_number}</span>}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-display text-2xl text-blue-700">₹{o.total.toFixed(0)}</div>
                  <div className="text-xs font-mono-tech text-slate-500">{o.items.length} items</div>
                </div>
              </div>
              <div className="mt-4 flex gap-3 overflow-x-auto">
                {o.items.slice(0, 6).map((it, i) => (
                  <div key={i} className="flex-shrink-0 w-16 border border-slate-200 aspect-square">
                    {it.image && <img src={it.image} alt="" className="w-full h-full object-cover" />}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
