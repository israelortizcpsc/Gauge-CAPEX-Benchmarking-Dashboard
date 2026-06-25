import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy /api and /healthz to the Django server so the browser sees a
// same-origin API (no CORS, no hardcoded host). In production the app is
// served behind the same origin as the API, or VITE_API_BASE is set at build.
export default defineConfig({
  // Project Pages serve under /<repo>/; the deploy workflow sets VITE_BASE.
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/healthz': 'http://127.0.0.1:8000',
    },
  },
})
