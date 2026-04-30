import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Vite proxies /api/* and /static/* to the Django dev server so the
 * frontend stays same-origin. apiFetch uses `credentials: "same-origin"`
 * + `X-CSRFToken` header, both of which require the proxy.
 *
 * In Docker Compose the backend service hostname is `backend` on the
 * private network; for host-machine dev (`npm run dev`) it's
 * localhost:8000. Override with VITE_BACKEND_TARGET if needed.
 */
const BACKEND_TARGET = process.env.VITE_BACKEND_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: BACKEND_TARGET, changeOrigin: true },
      "/static": { target: BACKEND_TARGET, changeOrigin: true },
    },
  },
});
