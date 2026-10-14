import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { publicArchiveMetadata } from './buildPlugins/publicArchiveMetadata.ts'

export default defineConfig({
  plugins: [react(), publicArchiveMetadata()],
  base: '/Macro/',
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
