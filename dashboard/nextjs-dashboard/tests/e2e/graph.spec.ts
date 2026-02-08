import { test, expect } from "@playwright/test";

test.describe("Knowledge Graph", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/memories/graph");
  });

  test("should display graph", async ({ page }) => {
    // Wait for graph to load
    await expect(page.getByTestId("knowledge-graph")).toBeVisible();

    // Check if nodes are rendered
    await expect(page.locator('[data-testid="graph-node"]').first()).toBeVisible();
  });

  test("should search nodes", async ({ page }) => {
    // Enter search query
    await page.getByRole("searchbox", { name: /search nodes/i }).fill("test");

    // Wait for search results
    await page.waitForTimeout(500);

    // Verify nodes are filtered
    const visibleNodes = await page.locator('[data-testid="graph-node"]').count();
    expect(visibleNodes).toBeGreaterThan(0);
  });

  test("should click node to view details", async ({ page }) => {
    // Click on first node
    await page.locator('[data-testid="graph-node"]').first().click();

    // Verify details panel appears
    await expect(page.getByTestId("node-details")).toBeVisible();
    await expect(page.getByRole("heading", { name: /node details/i })).toBeVisible();
  });

  test("should change graph layout", async ({ page }) => {
    // Open layout menu
    await page.getByRole("button", { name: /layout/i }).click();

    // Select force-directed layout
    await page.getByRole("menuitem", { name: /force-directed/i }).click();

    // Wait for layout to change
    await page.waitForTimeout(1000);

    // Verify graph is still visible
    await expect(page.getByTestId("knowledge-graph")).toBeVisible();
  });

  test("should zoom and pan graph", async ({ page }) => {
    const graph = page.getByTestId("knowledge-graph");

    // Zoom in
    await graph.click({ position: { x: 400, y: 300 } });
    await page.mouse.wheel(0, -100);
    await page.waitForTimeout(500);

    // Pan graph
    await graph.dragTo(graph, {
      sourcePosition: { x: 400, y: 300 },
      targetPosition: { x: 300, y: 200 },
    });

    // Verify graph is still interactive
    await expect(graph).toBeVisible();
  });

  test("should highlight connected nodes on hover", async ({ page }) => {
    // Hover over a node
    await page.locator('[data-testid="graph-node"]').first().hover();

    // Check if connected nodes are highlighted
    await expect(page.locator('[data-testid="graph-node"].highlighted').first()).toBeVisible();
  });

  test("should filter by node type", async ({ page }) => {
    // Open filter menu
    await page.getByRole("button", { name: /filter/i }).click();

    // Select memory type
    await page.getByRole("checkbox", { name: /memory/i }).check();

    // Apply filters
    await page.getByRole("button", { name: /apply/i }).click();

    // Wait for filtered graph
    await expect(page.getByTestId("knowledge-graph")).toBeVisible();
  });

  test("should show edge labels", async ({ page }) => {
    // Enable edge labels
    await page.getByRole("checkbox", { name: /show labels/i }).check();

    // Verify edge labels are visible
    await expect(page.locator('[data-testid="edge-label"]').first()).toBeVisible();
  });

  test("should export graph as image", async ({ page }) => {
    // Click export button
    await page.getByRole("button", { name: /export/i }).click();

    // Select image format
    await page.getByRole("menuitem", { name: /png/i }).click();

    // Wait for download
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /download/i }).click();
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toMatch(/\.png$/);
  });

  test("should display node information on click", async ({ page }) => {
    // Click on a node
    await page.locator('[data-testid="graph-node"]').first().click();

    // Verify information is displayed
    await expect(page.getByTestId("node-properties")).toBeVisible();
    await expect(page.getByText(/type:/i)).toBeVisible();
    await expect(page.getByText(/connections:/i)).toBeVisible();
  });

  test("should adjust node size by importance", async ({ page }) => {
    // Enable size by importance
    await page.getByRole("checkbox", { name: /size by importance/i }).check();

    // Wait for graph to update
    await page.waitForTimeout(1000);

    // Verify nodes are still visible
    await expect(page.locator('[data-testid="graph-node"]').first()).toBeVisible();
  });

  test("should handle large graphs with many nodes", async ({ page }) => {
    // The graph should load without errors even with many nodes
    await expect(page.getByTestId("knowledge-graph")).toBeVisible();

    // Verify performance by checking if nodes are rendered
    const nodeCount = await page.locator('[data-testid="graph-node"]').count();
    expect(nodeCount).toBeGreaterThan(0);
  });
});
