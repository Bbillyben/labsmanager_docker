import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const djangoTarget = env.VITE_DJANGO_PROXY_TARGET || 'http://192.168.1.145:7000'

  return {
    base: '/app/',
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: djangoTarget,
          changeOrigin: true,
          headers: { Origin: djangoTarget },
        },
      },
    },
  }
})
