import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['Tests/js/**/*.test.js'],
    coverage: {
      reportOnFailure: true,
      provider: 'v8',
      include: ['casino/web/static/js/**/*.js'],
      reporter: ['text', 'html', 'json-summary'],
      reportsDirectory: 'coverage/js',
      thresholds: { 100: true },
    },
  },
});
