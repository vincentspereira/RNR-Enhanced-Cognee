/**
 * Tests for the RNR Enhanced Cognee Node.js client.
 *
 * Uses Node's built-in `node:test` runner so no extra dependency
 * is required. The HTTP server is mocked at the `fetchImpl` level
 * so the tests don't require a running MCP server.
 */

import { test } from "node:test";
import assert from "node:assert/strict";

// Import the compiled JS (after tsc) -- for development we can also
// import from dist/.
import { EnhancedCogneeClient, EnhancedCogneeError } from "../dist/index.js";

function mockFetch(responses) {
  // responses is an array of {status, body, capture}
  const calls = [];
  let idx = 0;
  const fn = async (url, opts) => {
    calls.push({ url, opts });
    const r = responses[idx++] || { status: 200, body: {} };
    return new Response(JSON.stringify(r.body), { status: r.status });
  };
  fn.calls = calls;
  return fn;
}

test("canonical requests refuse an implicit destination before credential I/O", async () => {
  const previous = process.env.ENHANCED_COGNEE_URL;
  delete process.env.ENHANCED_COGNEE_URL;
  try {
    const network = mockFetch([]);
    const client = new EnhancedCogneeClient({ accessToken: "synthetic", fetchImpl: network });
    await assert.rejects(() => client.memoryStatus(), /explicit scoped bearer token and service origin/);
    assert.equal(network.calls.length, 0);
  } finally {
    if (previous === undefined) delete process.env.ENHANCED_COGNEE_URL;
    else process.env.ENHANCED_COGNEE_URL = previous;
  }
});

test("addMemory POSTs to /memory/add with snake_case payload", async () => {
  const m = mockFetch([{ status: 200, body: { id: "abc-123" } }]);
  const cli = new EnhancedCogneeClient({
    baseUrl: "http://example:8000",
    fetchImpl: m,
  });

  const result = await cli.addMemory({
    content: "hello",
    agentId: "agent-1",
    memoryCategory: "engineering",
  });

  assert.equal(result.id, "abc-123");
  assert.equal(m.calls.length, 1);
  assert.equal(m.calls[0].url, "http://example:8000/memory/add");
  assert.equal(m.calls[0].opts.method, "POST");
  const body = JSON.parse(m.calls[0].opts.body);
  assert.equal(body.content, "hello");
  assert.equal(body.agent_id, "agent-1");        // snake_case conversion
  assert.equal(body.memory_category, "engineering");
});

test("searchMemory returns the parsed array", async () => {
  const m = mockFetch([{
    status: 200,
    body: {
      results: [
        {
          id: "1",
          content: "hi",
          agent_id: "a",
          category: "eng",
          similarity_score: 0.9,
          metadata: {},
          created_at: "2026-05-21T00:00:00Z",
        },
      ],
      count: 1,
    },
  }]);
  const cli = new EnhancedCogneeClient({ baseUrl: "http://x", fetchImpl: m });
  const r = await cli.searchMemory({ query: "hi", limit: 5 });
  assert.equal(r.count, 1);
  assert.equal(r.results[0].id, "1");
});

test("API-key header attached when option present", async () => {
  const m = mockFetch([{ status: 200, body: { results: [], count: 0 } }]);
  const cli = new EnhancedCogneeClient({
    baseUrl: "https://approved",
    apiKey: "sk-test",
    fetchImpl: m,
  });
  await cli.searchMemory({ query: "x" });
  assert.equal(m.calls[0].opts.headers["X-API-Key"], "sk-test");
});

test("scoped token and redirect policy reach the actual fetch transport", async () => {
  const m = mockFetch([{ status: 200, body: { status: "fixture" } }]);
  const cli = new EnhancedCogneeClient({ baseUrl: "https://approved", accessToken: "synthetic", fetchImpl: m });
  await cli.getHealth();
  assert.equal(m.calls[0].opts.headers.Authorization, "Bearer synthetic");
  assert.equal(m.calls[0].opts.headers["X-API-Key"], undefined);
  assert.equal(m.calls[0].opts.redirect, "error");
  for (const options of [
    { baseUrl: "http://remote", accessToken: "synthetic" },
    { baseUrl: "https://approved", accessToken: "one", apiKey: "two" },
    { baseUrl: "https://user:pass@approved" },
    { baseUrl: "file:///private" },
  ]) assert.throws(() => new EnhancedCogneeClient(options));
});

test("response budget is enforced before JSON parsing", async () => {
  const cli = new EnhancedCogneeClient({ baseUrl: "https://approved", fetchImpl: async () => new Response("x".repeat(1024 * 1024 + 1)) });
  await assert.rejects(() => cli.getHealth(), /1 MiB/);
});

test("Tenant header attached when option present", async () => {
  const m = mockFetch([{ status: 200, body: { results: [], count: 0 } }]);
  const cli = new EnhancedCogneeClient({
    baseUrl: "http://x",
    tenantId: "acme",
    fetchImpl: m,
  });
  await cli.searchMemory({ query: "x" });
  assert.equal(m.calls[0].opts.headers["X-Tenant-ID"], "acme");
});

test("HTTP error surfaces as EnhancedCogneeError with status + body", async () => {
  const m = mockFetch([{
    status: 422,
    body: { detail: "validation failed" },
  }]);
  const cli = new EnhancedCogneeClient({ baseUrl: "http://x", fetchImpl: m });

  await assert.rejects(
    () => cli.addMemory({ content: "", agentId: "a", memoryCategory: "x" }),
    (err) => {
      assert.ok(err instanceof EnhancedCogneeError);
      assert.equal(err.status, 422);
      assert.ok(err.body.includes("validation failed"));
      return true;
    },
  );
});

test("addKnowledgeRelation snake-cases nested keys", async () => {
  const m = mockFetch([{ status: 200, body: { id: "rel-1" } }]);
  const cli = new EnhancedCogneeClient({ baseUrl: "http://x", fetchImpl: m });
  await cli.addKnowledgeRelation({
    sourceEntity: "a",
    targetEntity: "b",
    relationshipType: "KNOWS",
    confidence: 0.9,
  });
  const body = JSON.parse(m.calls[0].opts.body);
  assert.equal(body.source_entity, "a");
  assert.equal(body.target_entity, "b");
  assert.equal(body.relationship_type, "KNOWS");
  assert.equal(body.confidence, 0.9);
});

test("getHealth GETs /health", async () => {
  const m = mockFetch([{
    status: 200,
    body: { status: "healthy", enhanced_mode: true },
  }]);
  const cli = new EnhancedCogneeClient({ baseUrl: "http://x", fetchImpl: m });
  const h = await cli.getHealth();
  assert.equal(h.status, "healthy");
  assert.equal(m.calls[0].opts.method, "GET");
});
