import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // TEMPORARY: Cloudflare quick tunnel host for phone testing
    // (2026-09-06). Safe to remove once done — a new tunnel gets a new
    // random subdomain each time it's started anyway.
    allowedHosts: ["opponents-corner-michelle-wyoming.trycloudflare.com"],
  },
});
