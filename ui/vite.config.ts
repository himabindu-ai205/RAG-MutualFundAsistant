import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const DEFAULT_DEV_API =
  "https://rag-mutualfundasistant-production.up.railway.app";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = (env.VITE_DEV_API_PROXY || DEFAULT_DEV_API).replace(/\/+$/, "");

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/chat": { target: proxyTarget, changeOrigin: true, secure: true },
        "/health": { target: proxyTarget, changeOrigin: true, secure: true },
      },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
  };
});
