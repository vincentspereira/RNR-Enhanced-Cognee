/**
 * RNR Enhanced Cognee Node.js client.
 *
 * Talks to the FastAPI HTTP variant of the RNR Enhanced Cognee MCP server
 * (src/enhanced_cognee_mcp.py) over HTTP/JSON. Endpoints covered:
 *
 *   POST  /memory/add          -> addMemory()
 *   POST  /memory/search       -> searchMemory()
 *   POST  /knowledge/add_relation -> addKnowledgeRelation()
 *   GET   /stats               -> getStats()
 *   GET   /health              -> getHealth()
 *
 * Usage:
 *
 *   import { EnhancedCogneeClient } from "@enhanced-cognee/client";
 *
 *   const cli = new EnhancedCogneeClient({
 *     baseUrl: "http://localhost:8080",
 *     apiKey: process.env.ENHANCED_API_KEY,    // optional
 *     tenantId: "acme",                         // optional
 *   });
 *
 *   const { id } = await cli.addMemory({
 *     content: "We use OAuth 2.0 for external services",
 *     agentId: "code-reviewer",
 *     memoryCategory: "engineering",
 *   });
 */

export interface ClientOptions {
  baseUrl?: string;
  apiKey?: string;
  accessToken?: string;
  tenantId?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export interface MemoryEntry {
  id?: string;
  content: string;
  agentId: string;
  memoryCategory: string;
  embedding?: number[];
  metadata?: Record<string, unknown>;
  tags?: string[];
  createdAt?: string;
}

export interface SearchQuery {
  query: string;
  embedding?: number[];
  limit?: number;
  similarityThreshold?: number;
  memoryCategory?: string;
  agentId?: string;
  filters?: Record<string, unknown>;
}

export interface KnowledgeRelation {
  sourceEntity: string;
  targetEntity: string;
  relationshipType: string;
  properties?: Record<string, unknown>;
  confidence?: number;
}

export interface SearchResult {
  id: string;
  content: string;
  agent_id: string;
  category: string;
  similarity_score: number;
  metadata: Record<string, unknown>;
  created_at: string;
}

export class EnhancedCogneeError extends Error {
  status: number;
  body: string;
  constructor(message: string, status: number, body: string) {
    super(message);
    this.name = "EnhancedCogneeError";
    this.status = status;
    this.body = body;
  }
}

export class EnhancedCogneeClient {
  private baseUrl: string;
  private apiKey?: string;
  private accessToken?: string;
  private tenantId?: string;
  private fetchImpl: typeof fetch;
  private timeoutMs: number;
  private explicitBaseUrl: boolean;

  constructor(opts: ClientOptions = {}) {
    this.explicitBaseUrl = Boolean(opts.baseUrl ?? process.env.ENHANCED_COGNEE_URL);
    this.baseUrl = (
      opts.baseUrl
      ?? process.env.ENHANCED_COGNEE_URL
      ?? "http://localhost:8080"
    ).replace(/\/$/, "");
    this.accessToken = opts.accessToken ?? process.env.ENHANCED_COGNEE_ACCESS_TOKEN;
    this.apiKey = opts.apiKey ?? (this.accessToken ? undefined : process.env.ENHANCED_API_KEY);
    const origin = new URL(this.baseUrl);
    if (!["http:", "https:"].includes(origin.protocol) || origin.username || origin.password || origin.search || origin.hash) {
      throw new Error("baseUrl must use HTTP or HTTPS without embedded credentials, query or fragment");
    }
    if (this.apiKey && this.accessToken) throw new Error("Use either apiKey or accessToken");
    if ((this.apiKey || this.accessToken) && origin.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname)) {
      throw new Error("Authenticated remote services require HTTPS");
    }
    this.tenantId = opts.tenantId ?? process.env.ENHANCED_TENANT_ID;
    this.fetchImpl = opts.fetchImpl ?? fetch;
    this.timeoutMs = opts.timeoutMs ?? 30_000;
    if (!Number.isFinite(this.timeoutMs) || this.timeoutMs <= 0) throw new Error("timeoutMs must be positive");
  }

  /** Add a memory entry. */
  private async projectRequest(method: string, path: string, body?: unknown): Promise<Record<string, any>> {
    if (!this.explicitBaseUrl || !this.accessToken || this.apiKey || new URL(this.baseUrl).pathname !== "/") {
      throw new Error("Canonical memory requires an explicit scoped bearer token and service origin");
    }
    try { return await this._request(method, "/v1/memories" + path, body); }
    catch (error) {
      const status = error instanceof EnhancedCogneeError ? error.status : 503;
      let clarification = false;
      if (error instanceof EnhancedCogneeError) {
        try { clarification = JSON.parse(error.body).clarification_required === true; } catch { /* no source echo */ }
      }
      throw new EnhancedCogneeError("Memory request refused or unavailable; no success acknowledged", status,
        JSON.stringify({ clarification_required: clarification, retry_same_identity: [408,429,500,502,503,504].includes(status) }));
    }
  }

  /** Canonical project writes require a stable retry identity; scope comes from the signed token. */
  async remember(content: string, idempotencyKey: string, declarations: Record<string, unknown> = {}) {
    return this.projectRequest("POST", "", { ...declarations, content, idempotency_key: idempotencyKey });
  }
  async recall(query: string, limit = 5, includeShared = true) {
    return this.projectRequest("POST", "/recall", { query, limit, include_shared: includeShared });
  }
  async getRecord(id: string) { return this.projectRequest("GET", "/" + encodeURIComponent(id)); }
  async listRecords(limit = 50, offset = 0) {
    return this.projectRequest("GET", `?limit=${limit}&offset=${offset}`);
  }
  async correctRecord(id: string, content: string, expectedVersion: number, declarations: Record<string, unknown> = {}) {
    return this.projectRequest("PATCH", "/" + encodeURIComponent(id), { ...declarations, content, expected_version: expectedVersion });
  }
  async retractRecord(id: string, expectedVersion: number) {
    return this.projectRequest("POST", "/" + encodeURIComponent(id) + "/retract", { expected_version: expectedVersion });
  }
  async recordHistory(id: string) { return this.projectRequest("GET", "/" + encodeURIComponent(id) + "/history"); }
  async connections(entity: string, depth = 2, limit = 10) {
    return this.projectRequest("POST", "/connections", { entity, depth, limit });
  }
  async memoryStatus() { return this.projectRequest("GET", "/status"); }

  /** Legacy endpoint; use remember() for canonical memory. */
  async addMemory(entry: MemoryEntry): Promise<{ id: string }> {
    return this._post("/memory/add", this._snakeCase(entry));
  }

  /** Search memory. */
  async searchMemory(
    query: SearchQuery,
  ): Promise<{ results: SearchResult[]; count: number }> {
    return this._post("/memory/search", this._snakeCase(query));
  }

  /** Add a knowledge-graph relation. */
  async addKnowledgeRelation(
    relation: KnowledgeRelation,
  ): Promise<{ id: string }> {
    return this._post(
      "/knowledge/add_relation",
      this._snakeCase(relation),
    );
  }

  /** Get memory statistics. */
  async getStats(): Promise<Record<string, unknown>> {
    return this._get("/stats");
  }

  /** Health check. */
  async getHealth(): Promise<Record<string, unknown>> {
    return this._get("/health");
  }

  // --------------------------------------------------------------
  // Internals
  // --------------------------------------------------------------

  private async _get(path: string): Promise<any> {
    return this._request("GET", path);
  }

  private async _post(path: string, body: unknown): Promise<any> {
    return this._request("POST", path, body);
  }

  private async _request(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<any> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };
    if (this.apiKey) headers["X-API-Key"] = this.apiKey;
    if (this.accessToken) headers["Authorization"] = `Bearer ${this.accessToken}`;
    if (this.tenantId) headers["X-Tenant-ID"] = this.tenantId;

    try {
      const resp = await this.fetchImpl(this.baseUrl + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
        redirect: "error",
      });

      const reader = resp.body?.getReader();
      const parts: Uint8Array[] = [];
      let size = 0;
      if (reader) {
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            size += value.length;
            if (size > 1024 * 1024) throw new Error("Response exceeds the 1 MiB client limit");
            parts.push(value);
          }
        } finally {
          await reader.cancel();
        }
      }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const part of parts) { bytes.set(part, offset); offset += part.length; }
      const text = new TextDecoder().decode(bytes);

      if (!resp.ok) {
        throw new EnhancedCogneeError(
          `RNR Enhanced Cognee ${method} ${path} -> ${resp.status}`,
          resp.status,
          text,
        );
      }

      return JSON.parse(text);
    } finally {
      clearTimeout(timer);
    }
  }

  private _snakeCase(obj: object): Record<string, unknown> {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(obj)) {
      if (v === undefined) continue;
      const sk = k.replace(/([A-Z])/g, "_$1").toLowerCase();
      out[sk] = v;
    }
    return out;
  }
}

export default EnhancedCogneeClient;
