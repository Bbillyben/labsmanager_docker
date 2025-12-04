import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",  // pour que ton serveur soit accessible sur le réseau
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://192.168.1.145:8000',  // ton backend Django
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
