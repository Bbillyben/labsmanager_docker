import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react-swc'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: [
    { find: '@labsmanager/plugin-ui', replacement: fileURLToPath(new URL('./src/plugin-api.ts', import.meta.url)) },
    { find: '@labsmanager/plugin-calendar', replacement: fileURLToPath(new URL('./src/plugin-calendar.ts', import.meta.url)) },
    { find: '@fullcalendar/react/skeleton.css', replacement: fileURLToPath(new URL('./node_modules/@fullcalendar/react/skeleton.css', import.meta.url)) },
    { find: '@fullcalendar/react/themes/classic/theme.css', replacement: fileURLToPath(new URL('./node_modules/@fullcalendar/react/themes/classic/theme.css', import.meta.url)) },
    { find: '@fullcalendar/react/themes/classic/palette.css', replacement: fileURLToPath(new URL('./node_modules/@fullcalendar/react/themes/classic/palette.css', import.meta.url)) },
    { find: /^react$/, replacement: fileURLToPath(new URL('./node_modules/react/index.js', import.meta.url)) },
    { find: /^react\/jsx-dev-runtime$/, replacement: fileURLToPath(new URL('./node_modules/react/jsx-dev-runtime.js', import.meta.url)) },
    { find: '@', replacement: fileURLToPath(new URL('./src', import.meta.url)) },
  ] },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    restoreMocks: true,
  },
})
