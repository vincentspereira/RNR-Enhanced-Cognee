# Canonical memory and derived indexes

Use one maintained codebase and signed project identities. Start in the isolated
synthetic Hermes profile. This runbook prepares the service; it does not authorize
mounts, Windows access, private-data migration, backup uploads or production use.

## What the stores contain

PostgreSQL holds encrypted current records, retained versions, audit entries and
transactional change events. Qdrant holds embeddings and scope/version references.
ArcadeDB holds keyed entity hashes and source/version references, not source
labels. Valkey holds bounded encrypted snapshots with an expiry. Vectors and
relationship patterns still reveal derived information to infrastructure
operators; protect these stores, credentials, backups and network connections.

The main Hermes model may supply relationships from selected summaries. Named
entities must occur within their cited summary spans. The service checks that
correspondence, not whether the relationship is true. Every returned graph hop
rechecks the current canonical source, version and sharing authorization.

## Install and provision

Use Python 3.12 and the hashed `requirements-index.lock` for service/worker
environments. Prepare the named local embedding model once as an operator; the
runtime loads its existing offline cache. No chat-model API key belongs in this
service. The Hermes plugin reuses its host's separately configured model.

The separate `packaging/memory/pyproject.toml` builds the small
`rnr-enhanced-cognee-memory` wheel directly from this same maintained source.
Install the hashed index and MCP locks, then this wheel with `--no-deps`, and run
the package compatibility check. This artifact includes the API, worker, operator
modules, project SDK and MCP bridge without installing the upstream Cognee
engine. The repository's root `cognee` wheel describes the larger full stack;
installing that full distribution with only minimal dependencies is not a
dependency-qualified installation. Neither artifact is published to PyPI here.

Before an upgrade, keep a verified encrypted backup and matching recovery keys.
Run `python -m src.memory_admin init-schema` with the explicit operator database
URL. Schema 3 is additive; API/worker startup performs validation, not schema
creation. Run `grant-runtime` for a new API database account, or
`upgrade-runtime --role <existing-runtime-role>` to add schema-3 read grants without
replacing its credentials. Run `grant-worker --role <new-worker-role> --output
<absolute-private-file>` for a separate account that can read canonical records
and maintain deliveries but cannot edit memories/history or create schemas.

New `create-config` output includes a persistent `ENHANCED_INDEX_KEY`. Existing
installations use `create-index-key --output <new-absolute-private-file>` and keep
the original service/recovery material. Never replace an existing encryption key
just to enable indexes. Keep recovery copies of the index key as well.

Create an explicit non-secret index configuration. These addresses are examples;
select verified disposable services for qualification, not an existing private
database just because it uses one of these ports.

```json
{
  "pipeline": "project_memory_v1",
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "qdrant_url": "http://127.0.0.1:26333",
  "arcade_url": "http://127.0.0.1:22480",
  "arcade_database": "project_memory",
  "allow_internal_http": false
}
```

`ENHANCED_INDEX_CONFIG` names that absolute configuration path. Put credentials
in separate private service environments: `INDEX_ARCADEDB_USER`,
`INDEX_ARCADEDB_PASSWORD`, `INDEX_VALKEY_URL`, and `INDEX_QDRANT_API_KEY` when
configured. Use separate index read credentials for the API and write credentials
for the worker. The worker also needs its generated `ENHANCED_INDEX_DATABASE_URL`,
the canonical encryption configuration, `ENHANCED_INDEX_KEY` and
`ENHANCED_MODEL_CACHE`. It does not need JWT signing, backup signing or age
private recovery keys. Service/operator key files must be inaccessible to Hermes'
ordinary OS user before private activation.

Run `python -m src.index_runtime provision --create-graph-database` only when
intentionally creating a new graph database. Omit that flag for a prepared
database. Provisioning validates the vector dimensions and prepares graph types
and indexes. The synthetic test used ArcadeDB 26.9.1, Qdrant 1.18.3 and Valkey
7.2.13. This does not qualify every older provider/version in the legacy matrix.

Run `python -m src.index_runtime run` under the worker's service identity.
Configure the API with the same index pipeline/model/key contract and its read
credentials. Keep API, worker and operator accounts separate. The prepared
restricted Docker image contains the worker modules and dependencies, but still
requires an exact image build/scan and hardened deployment configuration.

## Readiness, interruptions and rebuilding

`/health/live` reports process liveness. `/health/ready` checks the canonical
schema and reports whether graph support is configured. It does not promise
that every index is caught up. Authenticated `/v1/memories/status` reports the
worker heartbeat, pipeline, pending event count and oldest pending event age.
The `once` command's `work_attempted` flag is not an indexing acknowledgement.
Check delivery errors and lag before declaring indexing complete.

Canonical writes acknowledge only after their encrypted record/history/audit and
event commit. Index delivery is separate and repeatable. If one store fails, the
event remains pending for retry. A crashed worker's bounded lease expires so a
new worker can continue. A shared record lock prevents an older delivery from
overwriting a newer correction. Graph replacement is transactional. Retraction,
expiry and revoked sharing exclude sources immediately in canonical reads, even
while derived cleanup is delayed. Current local semantic scoring remains a
fallback when the vector index is late or unavailable; graph unavailability is
reported rather than described as successful graph reasoning.

For recovery or a changed embedding model/key, choose a new explicit pipeline
and fresh graph/vector namespaces, provision them, then run a worker until lag
is zero. All retained canonical events are replayed for the new pipeline even
when an earlier pipeline processed them. Keep the original namespace and keys
until recovery is checked. Retired indexes may retain hashed/derived artifacts;
they are not used by the new API pipeline. Permanent cleanup has a separate
owner-approved retention/deletion decision.

## Other projects and standard MCP

Give each project its own expiring signed token and private raw space. Use the
reviewed library/membership API for approved common guidance and sanitized
summaries. A library membership does not grant all raw project memories. Do not
give agents reviewer, operator, database or service-key access.

The Python `ProjectMemoryClient`, and the Node/Go/Rust canonical methods, use
`/v1/memories`. Writes require an idempotency key; corrections/retractions require
the last read version. A timeout is an uncertain result: retry the same identity,
not a newly invented key. A 409 requires reviewing the current record or asking
for clarification. Retraction retains encrypted history.

For coding agents, install `requirements-memory-mcp.lock` and configure the
stdio command `python -m bin.project_memory_mcp` from the installed wheel, or
the absolute `bin/project_memory_mcp.py` path in a reviewed checkout. Supply
only `ENHANCED_MEMORY_URL` and `ENHANCED_COGNEE_ACCESS_TOKEN` to that process.
This is an actual MCP protocol bridge with nine tools. The `/mcp/*` JSON aliases
are compatibility routes, not Streamable HTTP MCP endpoints.

Set `ENHANCED_MEMORY_MODE=canonical` on the historical HTTP/dashboard entrypoints
to serve the canonical application. Setting the canonical database URL also
selects that mode unless explicitly overridden. Existing historical stores need
the reviewed copy-only migration before they appear in canonical memory.
Unsupported legacy tools fail closed; the 122-tool historical registry is not
automatically admitted. `src.security.tool_policy.manifest()` records the complete
permission/effect inventory and explicitly marks legacy effects as unqualified.

The dashboard requires a project token and an explicitly allowed browser origin
in `ENHANCED_DASHBOARD_ORIGINS`. Tokens are kept in browser session storage and
sent only to the configured protected service origin. Core login, create, list
and detail flows have a real browser test. Historical graph/analytics/session
screens do not gain capability merely because they are visible in the frontend.

## Updating the isolated Hermes test profile

Obtain the published commit with GitHub inside Ubuntu-Hermes. Do not mount/copy
Workspace source or operator secrets into Hermes. With the operator's prepared
environment, run `test_service.py provision` to add schema-3 grants, then
`upgrade-plugin` to archive and update the dedicated test provider. Run
`renew-test-token` if its test credential has expired; original private settings
are archived. All commands require the explicit dedicated `--runtime-root` and
leave the everyday profile unchanged. Restart only the test service/profile.

The newer plugin offers eight tools, including `enhanced_connections` and
optional summary relationship declarations. Repeat the installed-host smoke
test and model-driven tests after updating it. An earlier successful seven-tool
installation is not evidence that this update has already reached Hermes.
