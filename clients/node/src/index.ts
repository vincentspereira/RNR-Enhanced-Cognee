/**
 * Enhanced Cognee Node.js client.
 *
 * Talks to the FastAPI HTTP variant of the Enhanced Cognee MCP server
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
  private tenantId?: string;
  private fetchImpl: typeof fetch;
  private timeoutMs: number;

  constructor(opts: ClientOptions = {}) {
    this.baseUrl = (
      opts.baseUrl
      ?? process.env.ENHANCED_COGNEE_URL
      ?? "http://localhost:8080"
    ).replace(/\/$/, "");
    this.apiKey = opts.apiKey ?? process.env.ENHANCED_API_KEY;
    this.tenantId = opts.tenantId ?? process.env.ENHANCED_TENANT_ID;
    this.fetchImpl = opts.fetchImpl ?? fetch;
    this.timeoutMs = opts.timeoutMs ?? 30_000;
  }

  /** Add a memory entry. */
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
    if (this.tenantId) headers["X-Tenant-ID"] = this.tenantId;

    try {
      const resp = await this.fetchImpl(this.baseUrl + path, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new EnhancedCogneeError(
          `Enhanced Cognee ${method} ${path} -> ${resp.status}`,
          resp.status,
          text,
        );
      }

      return resp.json();
    } finally {
      clearTimeout(timer);
    }
  }

  private _snakeCase(obj: Record<string, unknown>): Record<string, unknown> {
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
