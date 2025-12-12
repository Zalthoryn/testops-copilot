import axios from "axios";

// Backend publishes routes under "/api", keep default aligned
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err?.response?.data?.detail || err.message;
    console.error("API error:", message);
    return Promise.reject(err);
  },
);

