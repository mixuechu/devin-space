import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: [
      'mcp-server-app-tunnel-5og2qm94.devinapps.com',
      'mcp-server-app-tunnel-z3sdrgjg.devinapps.com',
      'mcp-server-app-tunnel-zjeyr0eb.devinapps.com',
      'mcp-server-app-tunnel-z4cyqqgr.devinapps.com',
      'mcp-server-app-tunnel-fbdgpvrm.devinapps.com',
      'mcp-server-app-tunnel-xgvxo1fc.devinapps.com',
      'mcp-server-app-tunnel-abtsy492.devinapps.com',
      'mcp-server-app-42rhe1o4.devinapps.com',
      'mcp-server-app-tunnel-7hqw8gzl.devinapps.com',
      'localhost',
      '.devinapps.com'
    ],
    cors: true
  },
})

