import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://auth_server:8000', // Docker 內部 DNS
        changeOrigin: true,
        secure: false,
      }
    }
  }
})