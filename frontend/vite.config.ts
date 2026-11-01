import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

/**
 * TORNE frontend — a compiled static application.
 *
 * In development Vite serves the application and proxies `/api` to FastAPI.
 * In production the build lands in the Python package (`torne.explorer.static`)
 * and FastAPI serves it, so the wheel ships the whole application.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: '../src/torne/explorer/static',
    emptyOutDir: true,
    sourcemap: false,
    target: 'es2022',
    /**
     * The chart library is deliberately one chunk, and it is deliberately
     * lazy: a page that shows no chart never downloads it. The warning about
     * large chunks is therefore expected, and the budget that matters is the
     * one `npm run bundle:report` checks.
     */
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        /**
         * Keep the chart library out of the entry chunk: a page that shows no
         * chart must not pay for the chart library.
         *
         * Vite 8 bundles with Rolldown, where `manualChunks` is a function.
         */
        manualChunks(id: string) {
          if (/node_modules[\\/](echarts|zrender)[\\/]/.test(id)) {
            return 'echarts';
          }
          if (/node_modules[\\/]leaflet[\\/]/.test(id)) {
            return 'leaflet';
          }
          if (/node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/.test(id)) {
            return 'react';
          }
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/unit/**/*.test.{ts,tsx}'],
    css: false,
    restoreMocks: true,
  },
});
