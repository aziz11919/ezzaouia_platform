import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
  const proxiedPrefixes = [
    '/api',
    '/accounts',
    '/chatbot',
    '/ingestion',
    '/dashboard',
    '/bibliotheque',
    '/reports',
    '/audit',
    '/static',
    '/media',
  ]

  const proxy = Object.fromEntries(
    proxiedPrefixes.map(prefix => ([
      prefix,
      { target: backendTarget, changeOrigin: true, secure: false },
    ]))
  )

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy,
    },
    build: {
      outDir: '../static/react',
      emptyOutDir: true,
      assetsDir: 'assets',
    },
    base: '/static/react/',
  }
})
