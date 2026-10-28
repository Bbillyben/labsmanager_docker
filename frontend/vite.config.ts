import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const djangoTarget = env.VITE_DJANGO_PROXY_TARGET || 'http://192.168.1.145:7000'
  let resolvedBase = '/'
  const hostModule = (name: string) => `${resolvedBase}${command === 'build' ? `${name}.js` : `src/${name}.ts`}`

  return {
    base: command === 'build' ? '/static/frontend/' : '/app/',
    plugins: [react(), tailwindcss(), {
      name: 'plugin-ui-import-map',
      configResolved: (config) => { resolvedBase = config.base },
      transformIndexHtml: (html: string) => html
        .replace('__PLUGIN_REACT_URL__', hostModule('plugin-react'))
        .replace('__PLUGIN_JSX_URL__', hostModule('plugin-jsx-runtime'))
        .replace('__PLUGIN_API_URL__', hostModule('plugin-api'))
        .replace('__PLUGIN_CALENDAR_URL__', hostModule('plugin-calendar')),
    }],
    build: {
      rollupOptions: {
        preserveEntrySignatures: 'exports-only',
        input: {
          app: fileURLToPath(new URL('./index.html', import.meta.url)),
          'plugin-api': fileURLToPath(new URL('./src/plugin-api.ts', import.meta.url)),
          'plugin-react': fileURLToPath(new URL('./src/plugin-react.ts', import.meta.url)),
          'plugin-jsx-runtime': fileURLToPath(new URL('./src/plugin-jsx-runtime.ts', import.meta.url)),
          'plugin-calendar': fileURLToPath(new URL('./src/plugin-calendar.ts', import.meta.url)),
        },
        output: {
          entryFileNames: (chunk) => chunk.name.startsWith('plugin-') ? `${chunk.name}.js` : 'assets/[name]-[hash].js',
        },
      },
    },
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      host: '0.0.0.0',
      proxy: {
        '/static/img/labsmanager/labsmanager-logo.png': { target: djangoTarget, changeOrigin: true },
        '/static/django_prose_editor': { target: djangoTarget, changeOrigin: true },
        '/static/plugins/': { target: djangoTarget, changeOrigin: true },
        '/plugin/': { target: djangoTarget, changeOrigin: true, headers: { Origin: djangoTarget } },
        '/api': {
          target: djangoTarget,
          changeOrigin: true,
          headers: { Origin: djangoTarget },
        },
      },
    },
  }
})
