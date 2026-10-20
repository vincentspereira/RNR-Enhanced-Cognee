# Canonical stack implementation update - 20 October 2026

The remediation plan is being implemented. It is not fully complete, and the
everyday Hermes profile and other projects are not activated. This update
supersedes earlier statements that graph workers and canonical transport
consolidation were entirely unimplemented. Earlier evidence remains historical;
an old image or installed plugin does not qualify a newer source revision.

## Implemented and tested in this continuation

- Additive canonical schema 3 and separately restricted worker/API database
  permissions. Existing runtime accounts can receive the new read grants without
  credential replacement. Runtime startup validates schema rather than creating it.
- Durable leased delivery to actual Qdrant, ArcadeDB and Valkey stores. Delivery
  is repeatable, acknowledges every store before completion, retries partial
  failures, recovers crashed leases and serializes against current corrections.
  Current semantic recall remains available while an index is delayed.
- Source-linked graph claims, bounded multi-hop traversal and authorization at
  every hop. Current source/version checks reject stale edges, revoked sharing,
  expired sources and retractions immediately. Graph failures are reported.
  Hashes replace entity labels in graph storage; cache snapshots stay encrypted.
  These controls do not make derived vectors opaque to infrastructure operators.
- Real graph transaction rollback and fresh-namespace rebuild from retained
  canonical events, including events processed by an earlier pipeline.
- Canonical list/history/agent reads, bounded responses and admission capacity.
  History preserves versions and withholds recognized secret/private content.
  Compatibility HTTP/tool/dashboard adapters delegate to the same service.
  Canonical mode admits sixteen reviewed aliases; unsupported legacy operations
  are denied. The full 122-tool permission/effect manifest distinguishes canonical
  behavior from conservatively unqualified legacy effects.
- A nine-tool actual stdio MCP bridge and canonical Python, Node, Go and Rust
  client methods. Real-service tests check retries, project denial, stale versions,
  correction, retraction, retained history and credential refusal. Scoped errors
  avoid returning private server error content. The Python client refuses routes
  that could forward its bearer credential to another origin.
- Dashboard authentication, explicit permitted origins, tab-session credentials,
  protected-origin checks, JSON writes, stable write identities, version-checked
  edits, dynamic category input and retraction with retained history. Fixed
  unauthenticated direct requests, stale query refreshes and edit links leading
  to a missing route. Built-browser qualification is recorded separately below.
- An eight-tool Hermes provider update adds graph connections and optional
  source-span relationship declarations. Main-model selection still governs
  summaries; no raw transcript capture or extra extraction provider was added.
  Operator upgrades archive existing test-provider files and preserve extra files.
  Token renewal preserves private originals and never copies signing keys into
  the profile. This newer provider has not yet been delivered to Ubuntu-Hermes.
- A small native distribution built from the same maintained source tree, plus
  hashed index/MCP locks. It includes no upstream Cognee engine. Its clean
  installation and dependency compatibility checks pass outside the checkout.
  The larger root Cognee wheel still requires its full dependency set; minimal
  dependency import checks alone are not full-distribution qualification.
- Required core CI coverage and a separate default-stack/image-security workflow.
  The workflow retains unsuppressed findings and fails on high/critical matches.
  Adding a workflow is not proof that its hosted run has passed.

## Evidence from the current local checks

- Full unit lane: 4,245 passed, 2 skipped, with credential environment removed and
  outbound network denied. This is the developer lane with documented compatible
  overlays, not an exact newly built full-image environment.
- Full opt-in qualification suite: 68 passed, no skipped tests, against an
  explicitly provisioned native PostgreSQL 16.15 fixture, prepared offline BGE
  search model, real Qdrant 1.18.3, ArcadeDB 26.9.1 and Valkey 7.2.13. Includes
  the three actual language clients, actual stdio bridge, encrypted age backup
  and fresh-database recovery, browser flow and operator-update checks.
- A subsequent expanded real-store test passed graph transaction rollback and
  rebuilding a fresh index namespace after previous delivery completion.
- The dashboard production build passes type checks. The browser qualification
  exercises a real built frontend and service using invented data. It does not
  qualify historical graph/analytics/session screens or every browser/device.
- The index and MCP locked-dependency advisory scans report no known findings.
  The refreshed dashboard production-dependency scan reports zero findings.
  Neither result closes the separate existing OS-image or development-tool gates.
- Root and small native wheels pass the local-data/secret/test-path packaging
  boundary check. Native wheel imports and dependency compatibility pass in a
  fresh Python 3.12 environment outside the checkout.

Sanitized logs, XML and the policy inventory are in `remediation-evidence` with
the `2026-10-20-canonical-` prefix. Fixture data and originals were retained. No
private owner replies, service keys or profile credentials are release artifacts.

## Phase status and remaining work

| Phase | Current status | Still required |
|---|---|---|
| 0 - Preserve and baseline | Preservation and synthetic baselines established | Owner confirmation of exposed-key revocation and recovery custody |
| 1 - Access control | Canonical boundaries, manifest, adapters and regression checks implemented | Private service/operator OS separation and deployment-specific index credentials; broader legacy capabilities remain outside canonical admission |
| 2 - Consistent memory and retrieval | Canonical memory, transport adapters and actual default-stack delivery/recovery implemented | Qualify the deployed configuration and any separately selected legacy/provider paths; no automatic bulk migration or permanent erasure |
| 3 - Packaging and release | Small native artifact, locks, builds and checks prepared/tested locally | Exact hosted image build/scan, known OS/development advisory gates, release automation results and supported deployment configuration |
| 4 - Hermes provider | Earlier native provider installed and model-tested; newer eight-tool update implemented | GitHub-only delivery of this update, schema/grant upgrade, installed-host and model-driven requalification inside Ubuntu-Hermes |
| 5 - Isolated qualification | Current 68-test suite, real graph recovery and service/client/browser checks pass | Broader retrieval/load/soak assessment, selected local chat-model qualification, isolated deployed service checks, owner-managed recovery test and review before everyday/other-project activation |

The installed Hermes version previously refused the local chat endpoint's
8,192-token serving window because it requires at least 64,000. Reusing an
existing Unsloth route does not change that served limit. Earlier model-driven
synthetic checks used the already configured authorized cloud route; they do not
qualify the chosen local serving configuration. No guard was bypassed.

Windows WSL-control executables currently fail to launch from this Workspace
session (`Exec format error`), and the local Docker control socket is unresponsive.
These are environment limitations, not a missing paid plugin or approval. Native
Workspace fixtures let independent implementation/tests proceed. WSL mounts,
firewall, interop configuration and existing services were not changed to bypass
the limits. Restoring operator access is needed to deliver/recheck the newer
provider in Ubuntu-Hermes. A hosted image workflow is prepared for the image checks.

## Owner actions before private activation

All nine architectural/policy decisions were already answered; no repeat approval
is needed to continue the authorized fixes or publish the implementation branch.
The remaining owner-controlled evidence is specific: confirm real exposed keys
were revoked/replaced, keep recovery copies of the generated keys in the password
manager, and name the private daily service-backup destination. Existing whole-WSL
and cloud backups do not identify that destination or establish service recovery.
An operator must apply and verify a service account/credential boundary before
Hermes handles private memories. Synthetic tests sharing its OS user do not
provide that boundary.

Publication is authorized. Merge remains conditional on complete implementation
and working required checks. This checkpoint does not satisfy every remaining
release/activation requirement, so it must not be described as fully complete or
merged solely because the local tests passed.

Use [the operator runbook](../../../runbooks/CANONICAL-MEMORY-AND-INDEXES.md)
for schema, index, project-client and isolated Hermes upgrade instructions.
