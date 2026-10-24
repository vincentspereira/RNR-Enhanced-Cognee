// Opt-in real browser checks. The Python fixture supplies synthetic tokens only.
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";
const origin = process.env.RNR_DASHBOARD_QUALIFICATION_URL;
const service = process.env.RNR_DASHBOARD_API_URL;
const token = process.env.RNR_DASHBOARD_QUALIFICATION_TOKEN;
assert(origin && service && token);
const browser = await chromium.launch({ headless: true, executablePath: process.env.RNR_BROWSER_EXECUTABLE });
try {
  const context = await browser.newContext();
  await context.route("**/*", route => {
    const target = new URL(route.request().url());
    return [origin, service].includes(target.origin) ? route.continue() : route.abort();
  });
  const page = await context.newPage();
  await page.goto(origin + "/memories");
  await page.waitForURL("**/login");
  await page.locator("#token").fill(token);
  await page.getByRole("button", {name: "Save Token and Continue"}).click();
  await page.goto(origin + "/memories");
  await page.getByRole("button", {name: "Add Memory", exact: true}).first().click();
  await page.locator("#content").fill("Synthetic Browser Cedar retains eleven daily copies.");
  const created = page.waitForResponse(response => response.url() === service + "/api/memories" && response.request().method() === "POST");
  await page.locator("button[type=submit]").click();
  const write = await created;
  assert.equal(write.status(), 201, await write.text());
  await page.getByText("Synthetic Browser Cedar retains eleven daily copies.", {exact: true}).first().waitFor();
  assert.equal(await page.evaluate(() => sessionStorage.getItem("auth_token")), token);
  // Use the browser's own authenticated API connection for a current-version
  // check, then load the corresponding rendered detail page.
  const headers = {Authorization: "Bearer " + token};
  const records = await (await context.request.get(service + "/api/memories", {headers})).json();
  assert.equal(records.length, 1);
  const record = records[0];
  assert.equal(record.version, 1);
  await page.goto(origin + "/memories/" + record.memory_id);
  await page.getByText(record.content, {exact: true}).first().waitFor();
  await page.getByRole("button", {name: "Edit", exact: true}).click();
  await page.waitForFunction(content => document.querySelector("#content")?.value === content, record.content);
  await page.locator("#content").fill("Synthetic Browser Cedar retains nine daily copies.");
  await page.locator("#memory_type").fill("custom_browser_project");
  const corrected = page.waitForResponse(response => response.url() === service + "/api/memories/" + record.memory_id && response.request().method() === "PATCH");
  await page.getByRole("button", {name: "Save Changes", exact: true}).click();
  assert.equal((await corrected).status(), 200);
  await page.getByText("Synthetic Browser Cedar retains nine daily copies.", {exact: true}).first().waitFor();
  const current = await (await context.request.get(service + "/api/memories/" + record.memory_id, {headers})).json();
  assert.equal(current.version, 2);
  assert.equal(current.memory_type, "custom_browser_project");
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", {name: "Retract", exact: true}).click();
  await page.waitForURL("**/memories");
  const history = await (await context.request.get(service + "/v1/memories/" + record.memory_id + "/history", {headers})).json();
  assert.equal(history.versions.length, 3);
  const unauthorized = await context.request.get(service + "/api/memories");
  assert.equal(unauthorized.status(), 401);
  // Withdrawing the browser's credential must fail on the next data request.
  await page.evaluate(() => sessionStorage.removeItem("auth_token"));
  await page.reload();
  await page.waitForURL("**/login");
  console.log("Real browser login, create/list/detail, versioned edit, custom category, retraction/history and credential withdrawal passed");
  await context.close();
} finally { await browser.close(); }
