import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { copyFileSync, mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

const spaRoutes = [
  'dashboard-first',
  'dashboard-test',
  'dashboard-test2',
  'dashboard-test3',
  'dashboard-test4',
  'qr-front',
  'confirm',
  'staff-access',
  'staff-close',
  'submit-close',
  'login',
  'self-confirm',
  'mobile/schedule',
  'mobile/empty-rooms',
  'mobile/booking',
  'mobile/home',
  'mobile/change-pin',
  'desktop/schedule',
  'desktop/home',
  'desktop/room-summary',
  'desktop/schedule-info',
  'desktop/overview',
  'admin/dashboard-new',
  'admin/home',
  'admin/semester',
  'admin/schedule',
  'admin/rooms',
  'admin/cancel-room',
  'dashboard',
]

function staticSpaEntrypoints() {
  return {
    name: 'static-spa-entrypoints',
    closeBundle() {
      const outputRoot = resolve(process.cwd(), 'dist')
      const appEntry = resolve(outputRoot, 'index.html')

      for (const route of spaRoutes) {
        const routeDirectory = resolve(outputRoot, route)
        mkdirSync(routeDirectory, { recursive: true })
        copyFileSync(appEntry, resolve(routeDirectory, 'index.html'))
      }

      // Used by static hosts that support a custom 404 document but do not
      // provide an SPA history fallback.
      copyFileSync(appEntry, resolve(outputRoot, '404.html'))
    },
  }
}

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'https://cosai.nrru.ac.th:8000',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  plugins: [
    vue(),
    staticSpaEntrypoints(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/icon-192.svg', 'icons/icon-512.svg'],
      manifest: {
        name: 'ระบบบริหารจัดการห้องคอมพิวเตอร์',
        short_name: 'ระบบห้องคอมพิวเตอร์',
        description: 'ระบบจองห้องและแสดงตารางการใช้ห้องคอมพิวเตอร์',
        theme_color: '#0f172a',
        background_color: '#0f172a',
        display: 'standalone',
        icons: [
          {
            src: '/icons/icon-192.svg',
            sizes: '192x192',
            type: 'image/svg+xml',
          },
          {
            src: '/icons/icon-512.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
          },
        ],
      },
    }),
  ],
})
