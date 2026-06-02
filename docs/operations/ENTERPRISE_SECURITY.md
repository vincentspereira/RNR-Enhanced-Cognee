# Enterprise Security: Authentication, RBAC, Audit, Multi-Tenancy

This document describes the enterprise security controls available in Enhanced
Cognee and how to configure them. All controls are **fail-open in development
and fail-closed in production** (`ENHANCED_ENV=production`), consistent with the
rest of the hardening work.

Two server surfaces are covered:

- **HTTP API** (`src/enhanced_cognee_mcp.py`) -- the network-facing FastAPI
  server. Full per-route RBAC, bearer (OIDC/JWT) + API-key authentication,
  audit logging, and multi-tenant enforcement, all applied via middleware.
- **stdio MCP server** (`bin/enhanced_cognee_mcp_server.py`) -- the local server
  Claude Code launches. Per-tool RBAC + audit logging applied via a single
  `mcp.tool()` wrapper (covers all tools). SSO/OIDC does not apply here (there
  is no HTTP request to carry a bearer token); a local role is assumed instead.

The implementation lives in `src/security/enterprise_auth.py` and builds on the
role/permission primitives in `src/security/auth.py`.

---

## 1. Authentication

The HTTP server resolves a **Principal** (subject + role + permissions +
tenant) for every non-public request, in this order:

1. **Bearer token** (`Authorization: Bearer <jwt>`) -- OIDC (asymmetric, via
   JWKS) or symmetric HS256.
2. **API key** (`X-API-Key: <key>`) -- maps to a full-access admin principal.
3. **Dev-open fallback** -- if *no* authentication is configured and the
   environment is not production, the caller is treated as a local admin so
   single-user / local development stays frictionless.

If authentication *is* configured, every non-public request must present valid
credentials or it is rejected with `401`. In production the server refuses to
start at all without authentication configured (`enforce_production_auth`).

### 1a. SSO / OIDC (recommended for production)

Point the server at your identity provider's issuer. Tokens are verified
against the provider's JWKS (signature, expiry, optionally audience + issuer).

| Variable | Purpose | Example |
|---|---|---|
| `ENHANCED_OIDC_ISSUER` | OIDC issuer URL (enables discovery + `iss` check) | `https://login.example.com/realms/acme` |
| `ENHANCED_OIDC_JWKS_URI` | Explicit JWKS URL (skips discovery) | `https://login.example.com/realms/acme/protocol/openid-connect/certs` |
| `ENHANCED_OIDC_AUDIENCE` | Expected `aud` claim (verified when set) | `enhanced-cognee` |
| `ENHANCED_OIDC_ALGORITHMS` | Allowed algorithms (default `RS256`) | `RS256,ES256` |

If `ENHANCED_OIDC_JWKS_URI` is not set but `ENHANCED_OIDC_ISSUER` is, the JWKS
URI is discovered once from `<issuer>/.well-known/openid-configuration`.

Works with any standards-compliant IdP: Keycloak, Auth0, Okta, Microsoft Entra
ID, Google, etc.

### 1b. Symmetric JWT (HS256)

For internal service-to-service tokens without an IdP:

| Variable | Purpose |
|---|---|
| `ENHANCED_JWT_SECRET` | HS256 shared secret. Also signs tokens minted by `JWTAuthenticator`. Set a strong, persistent value. |
| `ENHANCED_JWT_ALGORITHMS` | Allowed algorithms for this path (default `HS256`). |

### 1c. Static API key

A single operator key, mapped to an admin principal. Good for a trusted
reverse-proxy or a small deployment.

| Variable | Purpose |
|---|---|
| `ENHANCED_API_KEY` | The accepted key. Sent by clients as the `X-API-Key` header (HTTP) or `api_key` argument (stdio mutating tools). Compared in constant time. |

### 1d. Claim mapping

How role and tenant are read out of a verified token's claims:

| Variable | Purpose | Default |
|---|---|---|
| `ENHANCED_OIDC_ROLE_CLAIM` | Claim holding the role(s) | `roles` |
| `ENHANCED_OIDC_TENANT_CLAIM` | Claim holding the tenant id | `tenant` |
| `ENHANCED_OIDC_DEFAULT_ROLE` | Role for an authenticated caller whose roles we don't recognise (least privilege) | `readonly` |

Role claims may be a space/comma string or a list. Keycloak's
`realm_access.roles` is read automatically. A singular `role` claim is also
honoured. When multiple recognised roles are present, the highest-privilege one
wins. Recognised role synonyms (case-insensitive):

- **admin**: admin, administrator, superuser, owner, root
- **user**: user, member, editor, write, writer, contributor
- **api_client**: api, api_client, service, service_account, client
- **readonly**: readonly, read-only, read, viewer, reader, guest

Tenant is read from `ENHANCED_OIDC_TENANT_CLAIM`, then `tenant_id`, `tid`, or
`org_id`.

---

## 2. Role-Based Access Control (RBAC)

Roles and their permissions are defined in `src/security/auth.py`:

| Permission | admin | user | api_client | readonly |
|---|:--:|:--:|:--:|:--:|
| `memory:read` | yes | yes | yes | yes |
| `memory:write` | yes | yes | yes | - |
| `memory:delete` | yes | - | - | - |
| `memory:admin` | yes | - | - | - |
| `session:read` | yes | yes | yes | yes |
| `session:write` | yes | yes | yes | - |
| `session:delete` | yes | - | - | - |
| `system:admin` | yes | - | - | - |
| `system:monitor` | yes | yes | - | yes |
| `system:config` | yes | - | - | - |

### HTTP route -> required permission

| Route | Permission |
|---|---|
| `POST /memory/add`, `POST /mcp/add_memory`, `POST /knowledge/add_relation`, `POST /mcp/update_memory` | `memory:write` |
| `POST /memory/search`, `POST /mcp/search_memories`, `POST /mcp/get_memories`, `GET /mcp/list_agents` | `memory:read` |
| `POST /mcp/delete_memory` | `memory:delete` |
| `GET /stats` | `system:monitor` |
| `GET /health`, `/health/live`, `/health/ready`, `/metrics` | none (public) |

Unknown routes require only authentication (no specific permission), except
`DELETE` verbs which require `memory:delete`. Custom routes are therefore not
silently broken, while authentication still applies to them.

### stdio tool -> required permission

Write tools (`add_memory`, `update_memory`, `cognify`, ...) require
`memory:write`; destructive tools (`delete_memory`, `forget_memory`,
`archive_category`, ...) require `memory:delete`; backup/restore/key-rotation
require `system:admin`. The full map is `TOOL_PERMISSIONS` in
`enterprise_auth.py`. Read/introspection tools require only authentication.

stdio RBAC is **off by default** (the local caller is assumed to be admin so
Claude Code is unaffected). Lock a deployment down with:

| Variable | Effect |
|---|---|
| `ENHANCED_MCP_ROLE` | Role the local stdio caller assumes (default `admin`; set e.g. `readonly` to restrict). |
| `ENHANCED_MCP_ENFORCE_RBAC` | Force per-tool RBAC even for admin (`1`/`true`). |

---

## 3. Audit logging

Every security-relevant operation is recorded to the audit log
(`src/audit_logger.py`): file channel (rotating, bounded) + an in-memory buffer
queryable via the `query_audit_log` MCP tool, and optional PostgreSQL
persistence.

- **HTTP**: an outermost middleware records every mutation (`POST`/`PUT`/
  `PATCH`/`DELETE`) and every authorization failure (`401`/`403`), capturing the
  caller subject, role, auth method, tenant, path, status code, and latency.
- **stdio**: the `mcp.tool()` wrapper records every tool call (success +
  failure) with the tool name, agent id, status, and latency.

Sensitive fields (api_key, password, token, ...) are hashed before being
written. Retention and channels are configured in `automation_config.json`
(`audit_logging` block) and via:

| Variable | Purpose |
|---|---|
| `ENHANCED_LOG_DIR` | Directory for the audit + app logs. |
| `ENHANCED_LOG_MAX_BYTES` | Rotating-file size cap (default 50 MiB). |
| `ENHANCED_LOG_BACKUP_COUNT` | Rotated backups kept (default 5). |

To persist audit records to PostgreSQL, set `audit_logging.log_to_database` to
`true` in `automation_config.json` and apply
`migrations/create_audit_log_table.sql`.

---

## 4. Multi-tenancy

Tenant isolation is implemented in `src/multi_tenant.py`: storage identifiers
(Postgres tables, Qdrant collections, graph databases, Valkey keys) are scoped
per tenant via naming helpers, and a per-request `TenantContext` carries the
active tenant.

- **HTTP**: the `X-Tenant-ID` request header sets the tenant for the request.
- **Enforced by default in production**: when `ENHANCED_ENV=production`, a
  tenant is **required** -- requests without `X-Tenant-ID` are rejected with
  `400`, and any storage call without a tenant raises. Outside production it is
  optional (single-tenant friendly).

| Variable | Effect |
|---|---|
| `ENHANCED_REQUIRE_TENANT` | Explicit override (`1`/`true` -> required; `0` -> optional). Always wins over the production default. Set to `0` for a genuine single-tenant production install. |

---

## 5. Transport security (TLS)

The application can terminate TLS directly (or sit behind a TLS-terminating
reverse proxy / ingress):

| Variable | Purpose |
|---|---|
| `ENHANCED_HTTPS_CERT_FILE` / `ENHANCED_HTTPS_KEY_FILE` | PEM cert + key; when both set the server listens on HTTPS. |
| `ENHANCED_HTTPS_CA_CERTS` | Optional CA bundle for client-certificate verification. |
| `ENHANCED_HTTPS_HOST` / `ENHANCED_HTTPS_PORT` | Bind address (default `0.0.0.0:8080`). |

---

## 6. Other request controls

| Variable | Purpose |
|---|---|
| `ENHANCED_CORS_ORIGINS` | Comma-separated allowed origins (default: none). A literal `*` forces `allow_credentials=False`. |
| `ENHANCED_MAX_PAYLOAD_BYTES` | Request body size cap (413 when exceeded). |
| `ENHANCED_RATE_LIMIT_<TOOL>_PER_MIN` | Per-(tool, agent) token-bucket rate limit. |
| `ENHANCED_METRICS_PUBLIC` | `/metrics` is public by default; set `0` to require auth on it. |

---

## 7. Production checklist

- [ ] `ENHANCED_ENV=production`
- [ ] One authentication method configured (OIDC issuer, JWT secret, or API key)
- [ ] `ENHANCED_JWT_SECRET` set to a strong, persistent value (if using JWT/HS256)
- [ ] TLS terminated (app-level certs or a TLS reverse proxy)
- [ ] `ENHANCED_CORS_ORIGINS` set to the exact front-end origins (never `*` with credentials)
- [ ] Multi-tenant: leave the production default on, or set `ENHANCED_REQUIRE_TENANT=0` only for a deliberate single-tenant install
- [ ] Audit retention + (optionally) DB persistence configured
- [ ] `ENHANCED_MAX_PAYLOAD_BYTES` + per-tool rate limits set to sane caps
