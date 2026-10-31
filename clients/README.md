# RNR Enhanced Cognee Cross-Language Clients

Official SDKs for calling the [RNR Enhanced Cognee](https://github.com/vincentspereira/RNR-Enhanced-Cognee) MCP HTTP server from non-Python codebases. All four clients (Python + the three here) expose the same HTTP contract — see `src/enhanced_cognee_mcp.py::setup_routes`.

## Languages

| Client | Path | Status |
| --- | --- | --- |
| **Python** | (root) | ✅ Production — installed as `enhanced-cognee-client` on PyPI |
| **Node.js / TypeScript** | [`node/`](node/) | ✅ Shipped 2026-05-21 |
| **Go** | [`go/`](go/) | ✅ Shipped 2026-05-21 |
| **Rust** | [`rust/`](rust/) | ✅ Shipped 2026-05-21 |

## Shared HTTP contract

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/memory/add` | POST | Store a memory entry |
| `/memory/search` | POST | Vector + text search |
| `/knowledge/add_relation` | POST | Add a graph edge |
| `/stats` | GET | Memory store statistics |
| `/health` | GET | Stack health snapshot |

## Shared headers

| Header | Purpose | Set by |
| --- | --- | --- |
| `X-API-Key` | Auth (when server has `ENHANCED_API_KEY` set) | `apiKey` / `APIKey` / `api_key` constructor option |
| `X-Tenant-ID` | Multi-tenant routing (when server uses `TenantContext`) | `tenantId` / `TenantID` / `tenant_id` constructor option |

## Adding a new language

To add a new SDK (e.g. Java, C#), follow the pattern established by the three existing ones:

1. One client class with a builder/options pattern
2. One method per HTTP endpoint
3. Headers set centrally (auth + tenant)
4. Typed errors for HTTP non-2xx
5. Unit tests using the language's standard HTTP mocking pattern
6. README with quick-start + auth examples

The HTTP contract is stable; new languages should not break it.

## License

All clients are Apache-2.0. See repository root [LICENSE](../LICENSE).
# Security qualification update - 19 October 2026

The Python, Node, Go and Rust clients distinguish an operator API key from a
scoped Bearer token. Authenticated remote URLs require HTTPS, and redirects are
refused. Python, Go and Rust disable ambient proxies by default. Node uses its
configured fetch implementation, which is part of the caller's trusted transport.
Node/Go/Rust responses are limited to 1 MiB. These checks do not qualify every
backend or optional provider.

These clients currently address legacy HTTP endpoints. Credentials carrying a
`project_id` are confined to the restricted `/v1/memories` API, so they cannot be
used to reach these older endpoints. Use the isolated Hermes provider for that
API; do not substitute an administrator key to bypass the project boundary.

Use `access_token` in Python, `accessToken` in Node, `AccessToken` in Go, or
`.api_key(None).access_token(Some(...))` in Rust. Keep tokens in the calling
system's secret store, outside source, instructions and memory content.

Local checks: Python wheel/registry contracts, Node 9 tests, Rust 9 tests plus a
documentation compile, and the Go suite with its race detector pass. Current
Rust lock and Go vulnerability checks report no known findings. These are local
results, not a claim of published SDK releases or private-project activation.
