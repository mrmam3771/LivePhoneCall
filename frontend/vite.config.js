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
      '/api/voice': { target: 'http://127.0.0.1:8003', changeOrigin: true },
      '/api/start': { target: 'http://127.0.0.1:8003', changeOrigin: true },
      '/api/chunk': { target: 'http://127.0.0.1:8003', changeOrigin: true },
      '/api/finish': { target: 'http://127.0.0.1:8003', changeOrigin: true },
      '/api/agent': { target: 'http://127.0.0.1:8003', changeOrigin: true },
      '/api/tts': { target: 'http://127.0.0.1:8003', changeOrigin: true },
    },
  },
})
