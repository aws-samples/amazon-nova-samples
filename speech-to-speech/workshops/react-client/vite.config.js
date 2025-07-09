import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: process.env.REACT_APP_BASE || '/',
  server: {
    port: 3000,
    allowedHosts: true,
    open: true,
    proxy: {
      // Proxy WebSocket connections if needed
      '/ws': {
        target: 'ws://localhost:8081/ws',
        ws: true,
        changeOrigin: true,
      }
    }
  },
  envPrefix: 'REACT_APP_'
})
