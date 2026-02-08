import { test, expect } from "@playwright/test";

test.describe("Timeline View", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/memories/timeline");
  });

  test("should display timeline", async ({ page }) => {
    // Wait for timeline to load
    await expect(page.getByTestId("timeline")).toBeVisible();

    // Check if timeline items are displayed
    const timelineItems = page.locator('[data-testid="timeline-item"]');
    await expect(timelineItems.first()).toBeVisible();
  });

  test("should zoom in/out", async ({ page }) => {
    const initialZoom = await page.getByTestId("timeline-zoom").innerText();

    // Click zoom in
    await page.getByRole("button", { name: /zoom in/i }).click();

    // Wait for zoom to change
    await page.waitForTimeout(500);

    const zoomedIn = await page.getByTestId("timeline-zoom").innerText();
    expect(zoomedIn).not.toBe(initialZoom);

    // Click zoom out
    await page.getByRole("button", { name: /zoom out/i }).click();

    // Wait for zoom to change
    await page.waitForTimeout(500);

    const zoomedOut = await page.getByTestId("timeline-zoom").innerText();
    expect(zoomedOut).not.toBe(zoomedIn);
  });

  test("should filter by type", async ({ page }) => {
    // Open filter menu
    await page.getByRole("button", { name: /filter/i }).click();

    // Select memory type
    await page.getByRole("checkbox", { name: /observation/i }).check();

    // Apply filters
    await page.getByRole("button", { name: /apply/i }).click();

    // Wait for filtered timeline
    await expect(page.getByTestId("timeline")).toBeVisible();
  });

  test("should click timeline item to view memory", async ({ page }) => {
    // Click on first timeline item
    await page.locator('[data-testid="timeline-item"]').first().click();

    // Verify memory detail modal appears
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("heading", { name: /memory detail/i })).toBeVisible();
  });

  test("should navigate timeline with arrow keys", async ({ page }) => {
    const initialItem = await page.locator('[data-testid="timeline-item"]').first().textContent();

    // Press right arrow to navigate forward
    await page.keyboard.press("ArrowRight");

    // Wait for navigation
    await page.waitForTimeout(300);

    // Verify timeline moved
    const nextItem = await page.locator('[data-testid="timeline-item"]').first().textContent();
    expect(nextItem).not.toBe(initialItem);
  });

  test("should display date markers", async ({ page }) => {
    // Check if date markers are visible
    await expect(page.locator('[data-testid="date-marker"]').first()).toBeVisible();
  });

  test("should adjust timeline range", async ({ page }) => {
    // Click on date range selector
    await page.getByRole("button", { name: /date range/i }).click();

    // Select last 30 days
    await page.getByRole("menuitem", { name: /last 30 days/i }).click();

    // Wait for timeline to update
    await expect(page.getByTestId("timeline")).toBeVisible();
  });

  test("should show connection lines between related memories", async ({ page }) => {
    // Hover over a timeline item
    await page.locator('[data-testid="timeline-item"]').first().hover();

    // Check if connection lines appear
    await expect(page.locator('[data-testid="connection-line"]').first()).toBeVisible();
  });

  test("should collapse/expand timeline sections", async ({ page }) => {
    // Find a timeline section
    const section = page.locator('[data-testid="timeline-section"]').first();

    // Click collapse button
    await section.getByRole("button", { name: /collapse/i }).click();

    // Verify section is collapsed
    await expect(section.locator('[data-testid="timeline-item"]')).toHaveCount(0);

    // Click expand button
    await section.getByRole("button", { name: /expand/i }).click();

    // Verify items are visible
    await expect(section.locator('[data-testid="timeline-item"]').first()).toBeVisible();
  });
});
