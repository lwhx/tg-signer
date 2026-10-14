import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: process.env.DASHBOARD_URL || "http://127.0.0.1:8999",
    viewport: { width: 1440, height: 1000 },
    trace: "off",
  },
  reporter: "list",
});
