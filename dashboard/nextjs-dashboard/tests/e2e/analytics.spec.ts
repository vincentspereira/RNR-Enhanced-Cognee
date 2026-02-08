import { test, expect } from "@playwright/test";

test.describe("Analytics Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/analytics");
  });

  test("should display KPI cards", async ({ page }) => {
    // Check if all KPI cards are visible
    await expect(page.getByTestId("kpi-card-total-memories")).toBeVisible();
    await expect(page.getByTestId("kpi-card-total-sessions")).toBeVisible();
    await expect(page.getByTestId("kpi-card-token-efficiency")).toBeVisible();
    await expect(page.getByTestId("kpi-card-active-agents")).toBeVisible();

    // Verify KPI values are displayed
    await expect(page.getByTestId("kpi-value").first()).toBeVisible();
  });

  test("should display charts", async ({ page }) => {
    // Check if charts are rendered
    await expect(page.getByTestId("chart-memory-growth")).toBeVisible();
    await expect(page.getByTestId("chart-type-distribution")).toBeVisible();
    await expect(page.getByTestId("chart-token-usage")).toBeVisible();
  });

  test("should display activity heatmap", async ({ page }) => {
    // Wait for heatmap to load
    await expect(page.getByTestId("activity-heatmap")).toBeVisible();

    // Check if heatmap cells are rendered
    await expect(page.locator('[data-testid="heatmap-cell"]').first()).toBeVisible();
  });

  test("should filter by date range", async ({ page }) => {
    // Open date range picker
    await page.getByRole("button", { name: /date range/i }).click();

    // Select last 7 days
    await page.getByRole("menuitem", { name: /last 7 days/i }).click();

    // Wait for analytics to update
    await page.waitForTimeout(1000);

    // Verify analytics are still displayed
    await expect(page.getByTestId("kpi-card-total-memories")).toBeVisible();
  });

  test("should filter by agent", async ({ page }) => {
    // Open agent filter
    await page.getByRole("button", { name: /agent/i }).click();

    // Select an agent
    await page.getByRole("menuitem", { name: /claude-code/i }).click();

    // Wait for analytics to update
    await page.waitForTimeout(1000);

    // Verify analytics are still displayed
    await expect(page.getByTestId("analytics-dashboard")).toBeVisible();
  });

  test("should export analytics report", async ({ page }) => {
    // Click export button
    await page.getByRole("button", { name: /export/i }).click();

    // Select PDF format
    await page.getByRole("menuitem", { name: /pdf/i }).click();

    // Wait for download to start
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /download/i }).click();
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  });

  test("should refresh analytics data", async ({ page }) => {
    // Click refresh button
    await page.getByRole("button", { name: /refresh/i }).click();

    // Wait for data to reload
    await expect(page.getByTestId("analytics-dashboard")).toBeVisible();
  });

  test("should display structured stats", async ({ page }) => {
    // Navigate to structured stats section
    await page.getByRole("tab", { name: /structured/i }).click();

    // Verify structured stats are displayed
    await expect(page.getByTestId("structured-stats")).toBeVisible();
    await expect(page.getByText(/observations/i)).toBeVisible();
    await expect(page.getByText(/bugfixes/i)).toBeVisible();
  });

  test("should display session analytics", async ({ page }) => {
    // Navigate to session analytics
    await page.getByRole("tab", { name: /sessions/i }).click();

    // Verify session analytics are displayed
    await expect(page.getByTestId("session-analytics")).toBeVisible();
  });

  test("should interact with charts", async ({ page }) => {
    // Hover over a chart
    await page.locator('[data-testid="chart-memory-growth"]').hover();

    // Check if tooltip appears
    await expect(page.locator('[data-testid="chart-tooltip"]').first()).toBeVisible();
  });

  test("should switch between time periods", async ({ page }) => {
    // Click on time period selector
    await page.getByRole("button", { name: /time period/i }).click();

    // Select "This Month"
    await page.getByRole("menuitem", { name: /this month/i }).click();

    // Wait for charts to update
    await page.waitForTimeout(1000);

    // Verify charts are still visible
    await expect(page.getByTestId("chart-memory-growth")).toBeVisible();
  });

  test("should compare time periods", async ({ page }) => {
    // Enable comparison mode
    await page.getByRole("checkbox", { name: /compare periods/i }).check();

    // Select previous period
    await page.getByRole("button", { name: /compare with/i }).click();
    await page.getByRole("menuitem", { name: /previous period/i }).click();

    // Wait for comparison data
    await page.waitForTimeout(1000);

    // Verify comparison is displayed
    await expect(page.getByTestId("comparison-data")).toBeVisible();
  });

  test("should handle zero data gracefully", async ({ page }) => {
    // This test ensures analytics handles edge cases
    await expect(page.getByTestId("analytics-dashboard")).toBeVisible();

    // Even with zero data, UI should be functional
    await expect(page.getByRole("button", { name: /refresh/i })).toBeVisible();
  });
});
