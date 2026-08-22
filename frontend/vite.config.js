import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 8000,
    strictPort: true,
    proxy: {
      '/api/chat': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
    },
  },
})
