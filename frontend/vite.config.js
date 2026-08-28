import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    // Fail loudly if 5173 is taken instead of silently drifting to 5174
    // (which then breaks CORS against the backend).
    strictPort: true,
  },
});