# Canonical memory and derived indexes

Use one maintained codebase and signed project identities. Start in the isolated
synthetic Hermes profile. This runbook prepares the service; it does not authorize
mounts, Windows access, private-data migration, backup uploads or production use.

For execution inside Ubuntu-Hermes, use the detailed
[deployment handoff](UBUNTU-HERMES-DEPLOYMENT-HANDOFF.md), including the source
checkout folder, already answered owner decisions and ordered verification tasks.

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

The restricted 1.2.0 runtime uses a text-only ONNX adapter, independently of
optional full-engine FastEmbed support. Its admitted model is
`BAAI/bge-small-en-v1.5` (384 dimensions). Other models fail closed pending
separate admission. Prepare a NEW operator-owned flat cache explicitly:

```bash
python scripts/qualification/prepare_text_model.py --cache /APPROVED/NEW/model-cache
```

Replace the example with the selected protected directory. This downloads only
five public MIT-licensed files at a pinned repository revision and verifies
exact sizes/SHA-256. `--source /APPROVED/EXISTING/flat-cache` uses verified local
files instead. Existing differing files are refused and retained. Runtime
startup never downloads or falls back to another model. Preserve the old cache
and runtime; do not repoint a running service until artifact, vector, actual
index/recovery and installed-host checks pass. A FastEmbed snapshot/link layout
is not silently migrated into the new flat cache.

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

### Noninteractive container runtime

`docker/Dockerfile.memory` assembles the same CPython 3.12 service on a pinned
official distroless Debian 13 C++ base. Both public input images use immutable
digests. The build retains the base package records and complete Debian control
and checksum inventories for the seven additional runtime library packages.
The build applies the signed Debian `liblzma5=5.8.1-1+deb13u2` update for
[DSA-6549-1](https://security-tracker.debian.org/tracker/DSA-6549-1);
the retained package record identifies the corrected version.
`/usr/share/enhanced-cognee/runtime-inventory.json` records input references,
versions, the interpreter checksum and the five omitted optional extensions.
The assembler checks native dependencies against both retained layers and
refuses unresolved or absent dependencies. It runs only in the build stage.

This artifact supports the API and indexing worker. It has no interactive shell,
package manager or runtime pip. `_tkinter`, `_curses`, `_curses_panel`, `readline` and the
optional `_uuid` native accelerator are omitted; UUID4 uses operating-system
randomness. It is not a general-purpose image for the larger legacy server or
operator backup commands. Use the separate protected native operator runtime
for backup and recovery; do not add recovery keys to the API/worker containers.

Use `docker logs` and the Python health check to diagnose a deployed container.
An interactive `docker exec ... sh` session is unavailable. The qualification
workflow checks TLS, compression, SQLite, dbm, encryption, UUID4 and native
imports inside the exact image, then exercises API/worker recovery with four
real stores and scans that same image. Source-level tests or an intermediate
root-filesystem scan do not qualify a final image. Findings are retained and the
HIGH/CRITICAL gate remains unsuppressed.

## Prepared private service-account deployment

The `integrations/hermes/deployment/enhanced-cognee-api.service` and
`enhanced-cognee-index.service` files are system service templates. They use
separate dynamic OS users, role-specific `LoadCredential` files, read-only system
and home protection, no additional capabilities, private temporary directories
and bounded CPU/memory/process counts. They are prepared assets, not installed
or OS-qualified services. An operator must review paths, resource limits and
the actual Ubuntu-Hermes service manager before installing/starting them.

Install the small native distribution in a root-owned runtime under
`/opt/enhanced-cognee-memory`, outside Hermes' writable checkout and home. Its
Python interpreter must also be accessible there or under the protected system
tree; a virtual environment pointing into a user's hidden home will not work
with home protection. Prepare the public offline model cache in a root-owned,
readable system location, and root-owned non-secret index settings under
`/etc/enhanced-cognee`. Do not change the existing Hermes profile's file access.

The operator creates separate root-only `api.json` and `worker.json` files in
`/etc/enhanced-cognee`. The API file contains its restricted PostgreSQL URL,
encryption configuration, JWT/OIDC verifier, local embedding settings and optional
read-only index credentials. The worker file contains its separately restricted
PostgreSQL URL, encryption/index keys, prepared model/config locations and index
write credentials. Omit backup signing, age recovery and database administrator
keys from both. `src.memory_daemon` reads only the service manager's private copy,
checks owner/file permissions, rejects duplicate/oversized/unexpected fields and
strips inherited operator/provider credentials and loader overrides. Runtime
security settings are forced rather than read from the agent's environment.

The systemd units and credential loader do not provision PostgreSQL/graph/vector
accounts, database ownership, root-only storage or network trust by themselves.
Those stores must also run outside the agent's writable files. Verify that the
Hermes OS user cannot read the service/operator credentials, rewrite installed
service code, access database files or obtain administrator/Docker privileges.
A different service username is insufficient if Hermes can become root. Keep
the loopback listener; a later central connection has a separate private-network
and certificate deployment decision. No system accounts, units, mounts, firewall
rules or everyday profile settings are changed by merely adding these templates.

## Owner-approved daily backup location

On 20 October 2026 the owner selected `/var/backups/enhanced-cognee` inside
Ubuntu-Hermes. This destination decision is complete. Do not create the directory
in Ubuntu-Workspace as a substitute, add a mount, or configure a new cloud upload.
Existing whole-WSL backups can include these encrypted files; they do not replace
the service recovery test or the separate recovery-key copies.

The backup unit is now a system service using the protected installed runtime
and a private `LoadCredential=backup.json` copy. The operator prepares the chosen
directory owned by root with mode `0700`, and a root-only
`/etc/enhanced-cognee/backup.json`. This JSON contains only the backup PostgreSQL
URL (`ENHANCED_MEMORY_DATABASE_URL`), persistent manifest signing key
(`ENHANCED_BACKUP_SIGNING_KEY`), optional signing key ID
(`ENHANCED_BACKUP_SIGNING_KEY_ID`) and public age recipient
(`ENHANCED_BACKUP_RECIPIENT`). Use a dedicated database read account capable of
dumping the selected canonical database. Do not put JWT signing, memory decryption
keys or an age private recovery identity in this scheduled service configuration.
The launcher rejects other credential fields and ignores inherited output paths.

Install the matching PostgreSQL client tools and the free age tools in protected
system locations available under `/usr/bin` or `/usr/local/bin`. The installed
Python runtime must contain the native memory distribution's backup modules.
The backup system unit restricts writes to the approved directory and private
temporary storage. Backup archives and signed completion manifests use mode
`0600`; incomplete outputs remain for review. The existing timer runs daily with
up to fifteen minutes of randomized delay and catches up a missed run.

Before enabling `enhanced-cognee-backup.timer`, run the backup service once as an
operator and restore into a fresh disposable database. Check decryption with the
separately held memory key, current records, retained history and project denial.
Keep the age private identity, manifest signing key and memory keys in the owner's
password manager, outside the backup directory. No automatic retention deletion
or new upload is configured. The service/timer must be installed and verified
inside Ubuntu-Hermes; adding these repository assets does not activate a backup.

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

For a human review console, the operator can issue a separate one-hour
`memory_admin issue-token --reviewer` credential with explicit tenant/project,
subject, agent and private output path. This role can review project records,
approve/revoke library membership and publish sanitized current versions. It
cannot add, correct or retract memories, rotate keys or create backups. Keep it
out of agent profiles. The service's signing key remains operator-only; the
reviewer receives only the expiring signed credential.

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
