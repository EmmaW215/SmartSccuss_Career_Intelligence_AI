import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
      },
      plugins: [react()],
      publicDir: 'Public', // Ensure Public directory is served correctly
      define: {
        // SECURITY: never define LLM API keys here — they get baked into the
        // public bundle. All LLM calls go through the backend (/api/lab/*).
        'process.env.NEXT_PUBLIC_BACKEND_URL': JSON.stringify(env.NEXT_PUBLIC_BACKEND_URL || 'https://smartsccuss-career-intelligence-ai.onrender.com'),
        'process.env.NEXT_PUBLIC_RENDER_BACKEND_URL': JSON.stringify(env.NEXT_PUBLIC_RENDER_BACKEND_URL || 'https://smartsccuss-career-intelligence-ai.onrender.com')
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
