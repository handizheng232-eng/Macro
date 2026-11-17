import { configDefaults, defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { publicArchiveMetadata } from './buildPlugins/publicArchiveMetadata.ts'

export default defineConfig({
  plugins: [react(), publicArchiveMetadata()],
  base: '/Macro/',
  test: {
    globals: true,
    exclude: [...configDefaults.exclude, 'comments-worker/**'], // Independent Node runner.
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    // Large archived-research DOMs contend for CPU/GC when each file gets a
    // worker. Serialize files, keeping isolation and the 5s per-test budget.
    maxWorkers: 1,
    testTimeout: 5000,
  },
})
