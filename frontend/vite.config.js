import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const httpsEnabled = process.env.VITE_HTTPS === '1'
const certificateDir = path.resolve(frontendDir, '..', '.cert')
const https = httpsEnabled ? {
  cert: readFileSync(process.env.VITE_HTTPS_CERT || path.join(certificateDir, 'lan-cert.pem')),
  key: readFileSync(process.env.VITE_HTTPS_KEY || path.join(certificateDir, 'lan-key.pem')),
} : undefined
const apiProxy = { '/api': { target: 'http://127.0.0.1:8002', changeOrigin: true } }

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['qwen-voice.svg', 'pwa-192x192.png', 'pwa-512x512.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Qwen Voice Workspace',
        short_name: 'Qwen Voice',
        description: 'Local bilingual AI chat and real-time voice workspace.',
        lang: 'zh-CN', start_url: '/', scope: '/', display: 'standalone',
        background_color: '#111114', theme_color: '#111114',
        categories: ['productivity', 'utilities'],
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
        navigateFallback: '/index.html', cleanupOutdatedCaches: true, clientsClaim: true,
      },
      devOptions: { enabled: process.env.VITE_PWA_DEV === '1' },
    }),
  ],
  server: {
    host: '0.0.0.0',
    port: Number(process.env.VITE_PORT || (httpsEnabled ? 8443 : 8000)),
    strictPort: true,
    https,
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    port: Number(process.env.VITE_PORT || (httpsEnabled ? 8443 : 8000)),
    strictPort: true,
    https,
    proxy: apiProxy,
  },
})
