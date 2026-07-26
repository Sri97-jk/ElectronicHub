import { Link } from "react-router-dom";
import { XCircle } from "@phosphor-icons/react";

export default function PaymentCancel() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-24 text-center relative z-10">
      <XCircle size={80} weight="duotone" className="text-red-400 mx-auto mb-6" />
      <h1 className="font-display text-4xl text-white mb-4">Payment Cancelled</h1>
      <p className="text-slate-400 mb-8">No worries — your cart is still saved.</p>
      <div className="flex justify-center gap-3">
        <Link to="/cart" className="btn-primary-neo">Back to Cart</Link>
        <Link to="/catalog" className="btn-ghost-neo">Continue Shopping</Link>
      </div>
    </div>
  );
}
