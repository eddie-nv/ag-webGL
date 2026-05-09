import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.{test,spec}.{ts,tsx}', '**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
      '@shared': path.resolve(__dirname, '../shared'),
      // shared/ lives outside frontend/, so its `import { z } from 'zod'` can't
      // resolve via node walk-up. Pin zod to frontend/node_modules.
      zod: path.resolve(__dirname, 'node_modules/zod'),
    },
  },
  server: {
    fs: {
      // Allow Vite to read files in the parent dir (shared/).
      allow: ['..'],
    },
  },
})
