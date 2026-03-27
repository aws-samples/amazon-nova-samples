import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:8000',
    headless: false,  // Show browser during demo
    screenshot: 'on',  // Take screenshots for all tests
    video: 'retain-on-failure',  // Record video on failure
  },
});
