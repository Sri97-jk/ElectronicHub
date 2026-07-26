import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { CheckCircle, Warning } from "@phosphor-icons/react";
import api from "../lib/api";
import { useCart } from "../lib/cart";

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const [status, setStatus] = useState("checking");
  const [orderId, setOrderId] = useState(null);
  const pollCount = useRef(0);
  const { refresh } = useCart();

  useEffect(() => {
    if (!sessionId) { setStatus("error"); return; }
    let stopped = false;
    const poll = async () => {
      pollCount.current++;
      try {
        const r = await api.get(`/payments/status/${sessionId}`);
        setOrderId(r.data.order_id);
        if (r.data.payment_status === "paid") {
          if (!stopped) { setStatus("paid"); refresh(); }
          return;
        }
        if (pollCount.current >= 10) { if (!stopped) setStatus("timeout"); return; }
        setTimeout(poll, 2000);
      } catch { if (!stopped) setStatus("error"); }
    };
    poll();
    return () => { stopped = true; };
  }, [sessionId, refresh]);

  return (
    <div className="max-w-2xl mx-auto px-6 py-24 relative z-10 text-center">
      {status === "checking" && (
        <>
          <div className="w-16 h-16 border-2 border-slate-900 border-t-transparent rounded-full animate-spin mx-auto mb-8" />
          <h1 className="font-display text-3xl text-slate-900 mb-4">Confirming Payment…</h1>
          <p className="text-slate-500">Please don't close this window.</p>
        </>
      )}
      {status === "paid" && (
        <>
          <CheckCircle size={80} weight="duotone" className="text-blue-700 mx-auto mb-6" />
          <div className="section-label mb-3 justify-center">Order Confirmed</div>
          <h1 className="font-display text-4xl md:text-5xl text-slate-900 mb-4">Thank you!</h1>
          <p className="text-slate-500 mb-8">Your order has been placed successfully. You'll receive tracking updates via email.</p>
          <div className="flex justify-center gap-3">
            {orderId && <Link to={`/orders`} data-testid="view-order" className="btn-primary-neo">View Orders</Link>}
            <Link to="/catalog" className="btn-ghost-neo">Continue Shopping</Link>
          </div>
        </>
      )}
      {(status === "timeout" || status === "error") && (
        <>
          <Warning size={80} weight="duotone" className="text-yellow-400 mx-auto mb-6" />
          <h1 className="font-display text-3xl text-slate-900 mb-4">Payment Status Unclear</h1>
          <p className="text-slate-500 mb-8">Check your orders page to verify.</p>
          <Link to="/orders" className="btn-primary-neo">Go to Orders</Link>
        </>
      )}
    </div>
  );
}
