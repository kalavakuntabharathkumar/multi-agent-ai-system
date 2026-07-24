// Vite configuration for the React frontend.
// Reads PORT and BASE_PATH from the environment (both required at dev/build time).

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

const rawPort = process.env.PORT;

// Fail fast if PORT is missing — vite needs it to bind the dev server
if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const basePath = process.env.BASE_PATH;

// Fail fast if BASE_PATH is missing — needed for correct asset URL resolution
if (!basePath) {
  throw new Error(
    "BASE_PATH environment variable is required but was not provided.",
  );
}

export default defineConfig({
  base: basePath,  // prefix all asset URLs with the configured base path
  plugins: [
    react(),         // Babel-based React transform (JSX, Fast Refresh)
    tailwindcss(),   // Tailwind CSS v4 Vite plugin (no PostCSS config needed)
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),  // @ → src/ shortcut used throughout the app
    },
    dedupe: ["react", "react-dom"],  // prevent duplicate React instances in the bundle
  },
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist/public"),
    emptyOutDir: true,  // clean the output directory before each build
  },
  server: {
    port,
    strictPort: true,     // fail if the port is already in use instead of picking another
    host: "0.0.0.0",      // bind to all interfaces so the dev server is accessible in containerized environments
    allowedHosts: true,   // accept requests from any hostname (required when behind a proxy)
    fs: {
      strict: true,       // block requests to files outside the project root
    },
  },
  preview: {
    port,
    host: "0.0.0.0",
    allowedHosts: true,
  },
});
