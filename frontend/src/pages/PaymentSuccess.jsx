import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { CheckCircle, Warning } from "@phosphor-icons/react";
import api from "../lib/api";
import { useCart } from "../lib/cart";

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const orderId = params.get("order_id");
  const sessionId = params.get("session_id");  // legacy stripe
  const [status, setStatus] = useState("checking");
  const [order, setOrder] = useState(null);
  const { refresh } = useCart();

  useEffect(() => {
    let stopped = false;
    let attempts = 0;

    const check = async () => {
      attempts++;
      try {
        // Razorpay flow: order_id is the internal order id, hit /orders/{id} directly
        if (orderId) {
          const r = await api.get(`/orders/${orderId}`);
          if (r.data.payment_status === "paid") {
            if (!stopped) { setOrder(r.data); setStatus("paid"); refresh(); }
            return;
          }
        }
        // Stripe legacy fallback
        if (sessionId) {
          const r = await api.get(`/payments/status/${sessionId}`);
          if (r.data.payment_status === "paid") {
            if (!stopped) { setStatus("paid"); refresh(); }
            return;
          }
        }
        if (attempts >= 6) { if (!stopped) setStatus("timeout"); return; }
        setTimeout(check, 1500);
      } catch { if (!stopped) setStatus("error"); }
    };

    if (!orderId && !sessionId) { setStatus("error"); return; }
    check();
    return () => { stopped = true; };
  }, [orderId, sessionId, refresh]);

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
          <p className="text-slate-500 mb-4">Your order has been placed successfully.</p>
          {order && (
            <div className="inline-block border border-slate-200 px-6 py-3 mb-6 text-sm font-mono-tech text-slate-700">
              Order <span className="text-slate-900 font-semibold">#{order.id.slice(0, 8).toUpperCase()}</span> · Total <span className="text-blue-700 font-semibold">₹{order.total.toFixed(0)}</span>
            </div>
          )}
          <p className="text-slate-500 mb-8 text-sm">A confirmation email is on its way to your inbox.</p>
          <div className="flex justify-center gap-3">
            <Link to="/orders" data-testid="view-order" className="btn-primary-neo">View Orders</Link>
            <Link to="/catalog" className="btn-ghost-neo">Continue Shopping</Link>
          </div>
        </>
      )}
      {(status === "timeout" || status === "error") && (
        <>
          <Warning size={80} weight="duotone" className="text-yellow-500 mx-auto mb-6" />
          <h1 className="font-display text-3xl text-slate-900 mb-4">Payment Status Unclear</h1>
          <p className="text-slate-500 mb-8">Check your orders page to verify.</p>
          <Link to="/orders" className="btn-primary-neo">Go to Orders</Link>
        </>
      )}
    </div>
  );
}
