import type { InternalAxiosRequestConfig } from "axios";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

beforeEach(() => { vi.resetModules(); sessionStorage.clear(); vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000"); });
afterEach(() => vi.unstubAllEnvs());

describe("distributed dashboard credential boundary", () => {
  it("sends the tab token only to its configured service", async () => {
    const { apiClient } = await import("./client");
    sessionStorage.setItem("auth_token", "synthetic-scoped-tab-token");
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => ({ data: {}, status: 200, statusText: "OK", headers: {}, config }));
    await apiClient.get("/api/memories", { adapter });
    expect(adapter.mock.calls[0][0].headers.Authorization).toBe("Bearer synthetic-scoped-tab-token");
    adapter.mockClear();
    await expect(apiClient.get("https://other.invalid/api/memories", { adapter })).rejects.toThrow("configured protected service");
    expect(adapter).not.toHaveBeenCalled();
  });

  it("rejects embedded URL credentials and a changed origin before any request", async () => {
    const { apiClient } = await import("./client");
    const adapter = vi.fn();
    for (const url of ["http://name:synthetic@localhost:8000/api/memories", "//other.invalid/api/memories"])
      await expect(apiClient.get(url, { adapter })).rejects.toThrow();
    expect(adapter).not.toHaveBeenCalled();
  });
});
