import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // 開發服務器配置
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_AUTH_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },

  // 生產構建優化
  build: {
    // 輸出目錄
    outDir: 'dist',

    // 代碼分割
    rollupOptions: {
      output: {
        manualChunks: {
          // React 核心
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // 圖表庫 (較大)
          'charts': ['recharts'],
        }
      }
    },

    // 壓縮選項
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,  // 移除 console.log
        drop_debugger: true  // 移除 debugger
      }
    },

    // 資源大小警告閾值 (KB)
    chunkSizeWarningLimit: 500,

    // 生成 sourcemap (生產環境可關閉)
    sourcemap: false
  },

  // 預覽服務器
  preview: {
    port: 4173,
    host: true
  }
})
