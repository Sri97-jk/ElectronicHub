import { createContext, useContext, useState, useEffect, useCallback } from "react";
import api from "./api";
import { useAuth } from "./auth";

const CartCtx = createContext(null);

export function CartProvider({ children }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      let cartId = localStorage.getItem("eh_cart_id");
      const r = await api.get("/cart");
      setItems(r.data.items || []);
    } catch { setItems([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh, user]);

  const addToCart = async (product_id, quantity = 1) => {
    let cartId = localStorage.getItem("eh_cart_id");
    const r = await api.post("/cart/add", { product_id, quantity });
    if (r.data.cart_id && !user) {
      localStorage.setItem("eh_cart_id", r.data.cart_id);
    }
    await refresh();
  };

  const updateQty = async (product_id, quantity) => {
    await api.post("/cart/update", { product_id, quantity });
    await refresh();
  };
  const removeItem = async (product_id) => {
    await api.delete(`/cart/item/${product_id}`);
    await refresh();
  };

  const count = items.reduce((s, it) => s + it.quantity, 0);
  const subtotal = items.reduce((s, it) => {
    const price = it.product?.discount_price || it.product?.price || 0;
    return s + price * it.quantity;
  }, 0);

  return (
    <CartCtx.Provider value={{ items, count, subtotal, addToCart, updateQty, removeItem, refresh, loading }}>
      {children}
    </CartCtx.Provider>
  );
}
export const useCart = () => useContext(CartCtx);
