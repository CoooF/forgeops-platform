import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget =
  process.env.FORGEOPS_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/v1": apiProxyTarget,
      "/health": apiProxyTarget,
    },
  },
  preview: {
    proxy: {
      "/v1": apiProxyTarget,
      "/health": apiProxyTarget,
    },
  },
  test: {
    environment: "jsdom",
  },
});
