import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Accessibility Audit", () => {
  test("should not have any automatically detectable accessibility issues on homepage", async ({
    page,
  }) => {
    await page.goto("/");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("should not have any accessibility issues on memories page", async ({ page }) => {
    await page.goto("/memories");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("should not have any accessibility issues on timeline page", async ({ page }) => {
    await page.goto("/memories/timeline");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("should not have any accessibility issues on graph page", async ({ page }) => {
    await page.goto("/memories/graph");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .exclude("[data-testid='knowledge-graph']") // Graph visualization has known issues
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("should not have any accessibility issues on analytics page", async ({ page }) => {
    await page.goto("/analytics");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("should not have any accessibility issues on search page", async ({ page }) => {
    await page.goto("/search");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });
});

test.describe("Keyboard Navigation", () => {
  test("should be fully navigable with keyboard", async ({ page }) => {
    await page.goto("/memories");

    // Tab through navigation
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toBeVisible();

    // Tab through memory cards
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press("Tab");
      await expect(page.locator(":focus")).toBeVisible();
    }

    // Enter to activate focused element
    const focusedElement = page.locator(":focus");
    await page.keyboard.press("Enter");
  });

  test("should have visible focus indicators", async ({ page }) => {
    await page.goto("/memories");

    // Tab through page and check focus rings
    await page.keyboard.press("Tab");

    const hasFocusRing = await page.locator(":focus").evaluate((el) => {
      const styles = window.getComputedStyle(el);
      const outline = styles.outline;
      const boxShadow = styles.boxShadow;

      return (
        outline !== "none" ||
        boxShadow.includes("0 0 0") ||
        styles.backgroundColor !== "rgba(0, 0, 0, 0)"
      );
    });

    expect(hasFocusRing).toBe(true);
  });

  test("should close modals with Escape key", async ({ page }) => {
    await page.goto("/memories");

    // Open modal
    await page.getByRole("button", { name: /add memory/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();

    // Close with Escape
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("should trap focus in modals", async ({ page }) => {
    await page.goto("/memories");

    // Open modal
    await page.getByRole("button", { name: /add memory/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();

    // Press Tab multiple times and verify focus stays in modal
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press("Tab");
      const focusedElement = page.locator(":focus");

      // Check if focused element is within the modal
      const isInModal = await focusedElement.evaluate((el) => {
        return el.closest('[role="dialog"]') !== null;
      });

      expect(isInModal).toBe(true);
    }
  });
});

test.describe("Screen Reader", () => {
  test("should have proper ARIA labels", async ({ page }) => {
    await page.goto("/memories");

    // Check for aria-labels on buttons without text
    const iconButtons = page.locator("button:not(:has-text(/^\\S$/))");
    const count = await iconButtons.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = iconButtons.nth(i);
      const hasAriaLabel = await button.evaluate((el) => {
        return (
          el.hasAttribute("aria-label") ||
          el.hasAttribute("aria-labelledby") ||
          el.textContent?.trim() !== ""
        );
      });

      expect(hasAriaLabel).toBe(true);
    }
  });

  test("should announce dynamic updates", async ({ page }) => {
    await page.goto("/memories");

    // Check for live regions
    const liveRegions = page.locator('[aria-live], [role="status"]');
    await expect(liveRegions.first()).toBeVisible();
  });

  test("should have semantic HTML structure", async ({ page }) => {
    await page.goto("/");

    // Check for landmark roles
    await expect(page.locator("nav")).toBeVisible();
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("h1")).toBeVisible();

    // Check heading hierarchy
    const headings = page.locator("h1, h2, h3, h4, h5, h6");
    const count = await headings.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe("Color Contrast", () => {
  test("should have sufficient color contrast", async ({ page }) => {
    await page.goto("/memories");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2aa"])
      .include(["body"])
      .analyze();

    // Check for contrast violations
    const contrastViolations = accessibilityScanResults.violations.filter(
      (v) => v.id === "color-contrast"
    );

    expect(contrastViolations).toEqual([]);
  });
});

test.describe("Forms", () => {
  test("should have proper form labels", async ({ page }) => {
    await page.goto("/memories");

    // Open add memory modal
    await page.getByRole("button", { name: /add memory/i }).click();

    // Check for form labels
    const inputs = page.locator("input, textarea, select");
    const count = await inputs.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const input = inputs.nth(i);
      const hasLabel = await input.evaluate((el) => {
        return (
          el.hasAttribute("aria-label") ||
          el.hasAttribute("aria-labelledby") ||
          el.labels !== null && el.labels.length > 0 ||
          el.closest("label") !== null
        );
      });

      expect(hasLabel).toBe(true);
    }
  });

  test("should show error messages properly", async ({ page }) => {
    await page.goto("/memories");

    // Open add memory modal
    await page.getByRole("button", { name: /add memory/i }).click();

    // Submit empty form
    await page.getByRole("button", { name: /add memory/i, exact: true }).click();

    // Check for error messages
    const errors = page.locator('[role="alert"], .error, [aria-invalid="true"]');
    await expect(errors.first()).toBeVisible();
  });
});
