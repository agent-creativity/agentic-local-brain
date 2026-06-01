import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'happy-dom',
      root: '.',
      include: ['tests/unit/**/*.{test,spec}.ts'],
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{ts,vue}'],
        exclude: ['src/main.ts', 'src/**/*.d.ts'],
        // thresholds enabled in Phase 2 when components stabilize
        // thresholds: {
        //   statements: 80,
        //   branches: 80,
        //   functions: 80,
        //   lines: 80,
        // },
      },
      setupFiles: ['tests/setup.ts'],
    },
  }),
)
