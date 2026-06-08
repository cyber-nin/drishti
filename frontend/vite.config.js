import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://localhost:5000'

const proxyEntry = {
  target: BACKEND,
  changeOrigin: true,
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/investigate': proxyEntry,
      '/crawl':       proxyEntry,
      '/batch':       proxyEntry,
      '/enrich':      proxyEntry,
      '/graph':       proxyEntry,
      '/tor':         proxyEntry,
      '/download':    proxyEntry,
      '/export':      proxyEntry,
      '/health':      proxyEntry,
      '/status':      proxyEntry,
    }
  }
})
