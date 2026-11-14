import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../python/botmartz_engine/api/static",
    emptyOutDir: true
  },
  server: {
    proxy: {
      "/health": "http://127.0.0.1:8420",
      "/v1": "http://127.0.0.1:8420",
      "/a2a": "http://127.0.0.1:8420",
      "/mcp": "http://127.0.0.1:8420",
      "/.well-known": "http://127.0.0.1:8420"
    }
  }
});
