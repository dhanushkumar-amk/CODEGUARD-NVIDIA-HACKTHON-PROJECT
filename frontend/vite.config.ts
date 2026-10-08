import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'https://codeguard-backend-6pg4.onrender.com',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: process.env.VITE_WS_BASE_URL || 'wss://codeguard-backend-6pg4.onrender.com',
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
