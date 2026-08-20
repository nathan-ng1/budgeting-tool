import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The Dashboard is served by the Python backend (src/dashboard/server.py), so
// the build lands in a `static/` directory alongside it rather than a top-level
// `dist/`. In development, `npm run dev` proxies /api through to that same
// backend so the frontend always talks to the real local database.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/dashboard/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.js",
  },
});
