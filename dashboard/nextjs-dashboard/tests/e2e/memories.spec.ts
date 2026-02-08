import { test, expect } from "@playwright/test";

test.describe("Memory Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/memories");
  });

  test("should display memory list", async ({ page }) => {
    // Wait for memories to load
    await expect(page.getByTestId("memory-list")).toBeVisible();

    // Check if at least one memory is displayed
    const memories = page.locator('[data-testid="memory-card"]');
    await expect(memories.first()).toBeVisible();
  });

  test("should search memories", async ({ page }) => {
    // Click on search
    await page.getByRole("link", { name: /search/i }).click();

    // Enter search query
    await page.getByRole("searchbox").fill("test");

    // Wait for search results
    await expect(page.getByTestId("search-results")).toBeVisible();
  });

  test("should filter by type", async ({ page }) => {
    // Click on filter dropdown
    await page.getByRole("button", { name: /filter/i }).click();

    // Select memory type
    await page.getByRole("option", { name: /observation/i }).click();

    // Wait for filtered results
    await expect(page.getByTestId("memory-list")).toBeVisible();
  });

  test("should add new memory", async ({ page }) => {
    // Click add memory button
    await page.getByRole("button", { name: /add memory/i }).click();

    // Fill in memory form
    await page.getByRole("textbox", { name: /content/i }).fill(
      "Test memory content created by E2E test"
    );

    // Select memory type
    await page.getByRole("combobox", { name: /type/i }).selectOption(
      "observation"
    );

    // Submit form
    await page.getByRole("button", { name: /add memory/i }).click();

    // Wait for success toast
    await expect(
      page.getByText(/memory added successfully/i)
    ).toBeVisible();

    // Verify new memory appears in list
    await expect(
      page.getByText("Test memory content created by E2E test")
    ).toBeVisible();
  });

  test("should edit memory", async ({ page }) => {
    // Click on first memory's edit button
    await page.locator('[data-testid="memory-card"]').first().getByRole("button", { name: /edit/i }).click();

    // Update content
    const textarea = page.getByRole("textbox", { name: /content/i });
    await textarea.clear();
    await textarea.fill("Updated memory content by E2E test");

    // Save changes
    await page.getByRole("button", { name: /save/i }).click();

    // Wait for success toast
    await expect(
      page.getByText(/memory updated successfully/i)
    ).toBeVisible();
  });

  test("should delete memory", async ({ page }) => {
    // Get initial memory count
    const initialCount = await page.locator('[data-testid="memory-card"]').count();

    // Click delete button on first memory
    await page.locator('[data-testid="memory-card"]').first().getByRole("button", { name: /delete/i }).click();

    // Confirm deletion
    await page.getByRole("button", { name: /confirm/i }).click();

    // Wait for success toast
    await expect(
      page.getByText(/memory deleted/i)
    ).toBeVisible();

    // Verify memory count decreased
    const newCount = await page.locator('[data-testid="memory-card"]').count();
    expect(newCount).toBeLessThan(initialCount);
  });

  test("should export memories", async ({ page }) => {
    // Click export button
    await page.getByRole("button", { name: /export/i }).click();

    // Select export format
    await page.getByRole("menuitem", { name: /json/i }).click();

    // Wait for download
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /download/i }).click();
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toMatch(/\.json$/);
  });

  test("should handle batch operations", async ({ page }) => {
    // Select multiple memories
    await page.locator('[data-testid="memory-card"]').first().getByRole("checkbox").check();
    await page.locator('[data-testid="memory-card"]').nth(1).getByRole("checkbox").check();

    // Verify batch actions appear
    await expect(page.getByRole("button", { name: /delete selected/i })).toBeVisible();

    // Delete selected
    await page.getByRole("button", { name: /delete selected/i }).click();
    await page.getByRole("button", { name: /confirm/i }).click();

    // Wait for success message
    await expect(page.getByText(/memories deleted/i)).toBeVisible();
  });

  test("should paginate memories", async ({ page }) => {
    // Scroll to bottom of list
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Wait for more memories to load
    await expect(page.locator('[data-testid="memory-card"]').nth(20)).toBeVisible();
  });

  test("should view memory details", async ({ page }) => {
    // Click on first memory
    await page.locator('[data-testid="memory-card"]').first().click();

    // Verify detail page loads
    await expect(page.getByTestId("memory-detail")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });
});
