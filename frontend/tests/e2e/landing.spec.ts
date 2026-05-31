import { expect, test } from "@playwright/test";

import { mockLangGraphAPI } from "./utils/mock-api";

test.describe("Landing page", () => {
  test("renders the header and hero section", async ({ page }) => {
    await page.goto("/");

    // Header brand name (Prism logo text)
    await expect(
      page.locator("header span", { hasText: "Prism" }),
    ).toBeVisible();

    // "启动 Agent" call-to-action button in hero
    await expect(page.getByRole("link", { name: /启动 Agent/i })).toBeVisible();
  });

  test("Get Started link navigates to workspace", async ({ page }) => {
    mockLangGraphAPI(page);

    await page.goto("/");

    const getStarted = page.getByRole("link", { name: /启动 Agent/i });
    await getStarted.click();

    // Should redirect to /login (for unauthenticated users)
    await page.waitForURL("**/login");
    await expect(page).toHaveURL(/\/login/);
  });
});
