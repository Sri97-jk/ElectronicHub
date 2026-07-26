import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("eh_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  const cartId = localStorage.getItem("eh_cart_id");
  if (cartId && !token) {
    cfg.params = { ...(cfg.params || {}), cart_id: cartId };
  }
  return cfg;
});

export default api;
