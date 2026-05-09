import type { NextConfig } from 'next'
import path from 'node:path'

const nextConfig: NextConfig = {
  // shared/schema/sceneSchema.ts lives outside frontend/. Map the alias here so
  // Turbopack/Webpack can resolve it during build (tsconfig paths alone aren't
  // enough -- bundlers need explicit allowance for parent-of-project imports).
  turbopack: {
    resolveAlias: {
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
  outputFileTracingRoot: path.resolve(__dirname, '..'),
}

export default nextConfig
