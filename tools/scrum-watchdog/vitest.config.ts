import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      // The CLI entrypoint (arg wiring + process/watch loop) is exercised via
      // integration-style tests but excluded from the unit coverage gate; the
      // pure logic modules carry the ratchet.
      exclude: ['src/cli.ts', 'src/index.ts'],
      thresholds: {
        lines: 95,
        functions: 95,
        branches: 90,
        statements: 95,
      },
    },
  },
});
