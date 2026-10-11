import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiBase = env.VITE_API_BASE_URL || 'http://localhost:8000';
  const wsBase = env.VITE_WS_BASE_URL || 'ws://localhost:8000';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiBase,
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: wsBase,
          ws: true,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
