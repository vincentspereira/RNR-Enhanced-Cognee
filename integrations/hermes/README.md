# Enhanced Cognee for isolated Hermes

Status: installed and under live qualification in the separate invented-data
Hermes test profile. The everyday profile is unchanged. See the audit
implementation tracker for current evidence and outstanding release checks.

The [Ubuntu-Hermes deployment handoff](../../docs/runbooks/UBUNTU-HERMES-DEPLOYMENT-HANDOFF.md)
provides the exact isolated checkout folder and a full Codex CLI/Hermes Desktop
task prompt. Use that handoff for the current schema/index/provider deployment;
older user-space test installation evidence does not establish private isolation.

For multiple bot profiles, use the [fleet memory runbook](../../docs/runbooks/HERMES-BOT-FLEET-MEMORY.md).
It describes one protected backend with per-profile private spaces/credentials,
reviewed shared libraries, credential renewal requirements and deployment limits.

This is a native Hermes memory-provider plugin, not the upstream Cognee engine.
It uses the restricted Enhanced Cognee project-memory API and Python's standard
library. It does not install a second Cognee package into Hermes.

## Isolation and installation location

Hermes runs in Ubuntu-Hermes. Windows and Ubuntu-Workspace paths are informational
only. Obtain this repository through GitHub into a checkout inside Ubuntu-Hermes.
Use the reviewed release/commit once it has been published. Never mount the
Workspace checkout or copy its private configuration into Hermes.

Install the `enhanced_cognee` directory from that Hermes-local checkout into the
chosen profile's `plugins/enhanced_cognee` directory, using the supported Hermes
plugin workflow. Its `__init__.py` exposes `register(ctx)` and a MemoryProvider.
The initial contract was checked against the API in Vincent's installed Hermes
0.22.2, commit d923a5eb487a. Host-shim tests alone do not establish live compatibility.

Use a dedicated test profile and invented facts first. The recommended first
service placement is inside Ubuntu-Hermes; a later central service requires an
explicitly permitted private network connection. Service credentials and storage
must be protected from ordinary agent filesystem/administrator access before
using private information.

## Profile configuration

For the reviewed Ubuntu-Hermes synthetic setup, the operator helper
`deployment/test_service.py` provides `provision`, `install`, `local-model` and
`serve` actions. It accepts only the dedicated test-runtime/profile paths. Obtain
it through GitHub before execution. The service uses its generated restricted
database role. The helper never starts Docker, changes mounts/firewall/default
profile, or installs system services. This user-space test setup shares the OS
user with Hermes; it is not sufficient filesystem separation for private service
keys. Install copies the Hermes-local plugin once and refuses to replace
differing existing plugin files or a token.

Run the selected profile's `hermes memory setup` after installing the plugin and
choose `enhanced_cognee`. Its setup schema asks for the service origin and a
restricted access token. Hermes stores the token in its profile secret store as
`ENHANCED_COGNEE_ACCESS_TOKEN`.

The non-secret file `<selected Hermes home>/enhanced_cognee.json` has this shape:

```json
{
  "base_url": "http://127.0.0.1:28080",
  "timeout": 3,
  "include_shared": true,
  "capture_policy": "selected"
}
```

The address above is an example, not a claim that a service is already installed.
Plain HTTP is accepted only for a loopback host. A remote service requires HTTPS
with a valid trusted certificate. Redirects and ambient HTTP proxies are disabled
so a credential cannot be forwarded to another destination.

The token's verified `tenant`, `project_id`, `sub`, `agent_id` and role determine
scope. The plugin has no user-selectable tenant/project field. Ordinary Hermes
credentials must not hold reviewer or administrator powers. Production tokens
must include an expiration; arrange renewal before everyday use. A service
operator's static API key is not a substitute for the scoped token.

Select the provider in that profile's normal Hermes configuration:

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: enhanced_cognee
```

Restart that test profile and check `hermes memory status`. A successful status
must identify the actual connected capability; an installed plugin is not proof
of working storage, semantic recall or graph reasoning.

## Behavior - selected capture policy

The newer provider offers eight tools: `enhanced_recall`, `enhanced_remember`,
`enhanced_get`, `enhanced_correct`, `enhanced_retract`, `enhanced_status`, and
`enhanced_clarify`, plus `enhanced_connections` for source-linked graph claims.
The latter requires a configured, ready index worker. Remember/correct can include
optional `knowledge_links` grounded in character spans of their summary content;
these remain unverified claims. The newer eight-tool update requires GitHub-only
delivery and installed-host requalification; earlier live seven-tool evidence
does not establish that it is already installed. See
[the canonical memory/index runbook](../../docs/runbooks/CANONICAL-MEMORY-AND-INDEXES.md).
Only the primary agent writes. Remember requests require a retry key; use the
same key after a timeout, because a timed-out request may already have committed.
Corrections and retractions require the current version to prevent lost updates.

Remember and correct can include an optional `evidence` object: a classification
(`fact`, `preference`, `decision`, `inference`, `summary` or `unclassified`), source
ID, reference URL, source hash, character span and the submitter's confidence.
These are unverified declarations; a high confidence value does not prove truth.
Categories remain project-defined strings. Reference links never trigger fetching.
Source URLs exclude credentials, query strings and fragments. A span requires a
source ID and both endpoints. If a correction supplies no new source declaration,
the new version requires source review instead of inheriting an old citation as
though it supported changed text. Earlier versions retain their original evidence.
Retracted records cannot be reactivated through the correction tool.

The default `capture_policy` is `selected`. Hermes' already configured conversation
model is instructed to select durable decisions, stable preferences and completed
task summaries and submit them through the memory tools without waiting for an
explicit remember request. This reuses Hermes' local Unsloth connection when that
is the configured conversation model. It needs no access to Windows model files
and starts no additional hosted extraction job. Agent compliance still needs an
an actual model-driven test for each selected model/configuration; host-shim tests
alone establish only the tool contract.

The live test found an additional prerequisite in the installed Hermes version:
the served chat model must expose at least a 64,000-token context window. The
configured local Granite endpoint reported 8,192, so Hermes refused the full chat
after detecting that limit. Do not disguise the provider, lie about its window,
or disable Hermes' guard. Increase the chosen local model's serving window only
after checking resource use, or select an already approved compatible provider.
The model's native advertised maximum does not prove the served window.
The memory service's small local embedding model is independent of this chat-model
requirement. A full chat capture test passed with the owner's already configured
cloud model and invented facts; this does not qualify the local chat configuration.

Raw transcript capture, raw tool-output storage and notebook mirroring remain
disabled. The inherited sync/end hooks do not archive conversations. Selected
tool writes complete synchronously and are acknowledged only after a successful
service response. There is no detached capture queue. Set `capture_policy` to
`explicit` for a profile whose owner prefers explicit-only writes.

On uncertain conflicts, Hermes uses `enhanced_clarify` and asks the user before
editing. A pending correction requires a quote from the current human reply;
bot replies and invented quotes cannot clear it. A clear user correction can
proceed directly with its current record version. This guard verifies the quote's
presence, not its semantic meaning; the configured agent still judges ambiguity.
Optional stable `fact_key` identifiers prevent conflicting fresh records from
silently accumulating under the same topic. Categories remain dynamic strings.

Server-side credential patterns are always enforced, including for explicit
writes and old-record reads. Scoped tokens issued by `src.memory_admin` also
mark selected capture, which blocks recognized private details pending a sanitized
summary/clarification. Pattern screening is not a guarantee that every disguised
secret or personal fact can be recognized; the model policy and restricted test
profile remain necessary. No automatic permanent erasure is implemented.

Recall is bounded to five records and approximately 8,000 JSON characters for
automatic prefetch. Every request rechecks service-side access and sharing grants.
Recalled content is labelled untrusted evidence; embedded instructions never
grant authority. This label cannot guarantee how every chat model will behave.
Previously recalled information may also remain in a conversation's context.

Sharing requires a separate reviewer outside the plugin. A grant targets a named
project or an approved library group in the same tenant and one reviewed version.
Approved portfolio members can search the common library alongside their private
project space. Enrollment does not expose private source records. Library review
rejects recognized personal/credential details, and shared results omit private
session/actor metadata. Revocation, correction,
retraction and expiry remove access on subsequent authoritative recalls. Retraction
preserves encrypted history; it is not permanent erasure.

## Service and processing

Use `requirements-memory.lock` and `src.memory_api:app`, or build
`docker/Dockerfile.memory`. Required settings are `ENHANCED_MEMORY_DATABASE_URL`,
`ENHANCED_JWT_SECRET` or configured OIDC verification, `ENCRYPTION_MASTER_KEY`,
`ENHANCED_ENV=production`, and `ENHANCED_REQUIRE_TENANT=1`. Keep persistent keys
outside Git and outside ordinary agent access, with a separately protected
recovery copy. Never paste credentials into instructions or memory content.

Before starting, an operator runs `python -m src.memory_admin init-schema` against
the dedicated service database. Runtime startup only validates schema version 3.
Use `grant-runtime` to create a separate service account with no schema creation,
canonical/history deletion, or audit/history update permission. `create-config`
and `issue-token` write generated secrets to new owner-only files and never print
values. `issue-token` defaults to one hour, with a 24-hour maximum; arrange renewal
before everyday use. Operator recovery files must be transferred to the owner's
password manager before private activation. Do not reuse operator credentials in
the plugin. See `python -m src.memory_admin --help` for command options.

Optional named-key support and an operator-only rotation command are documented
in `docs/reports/audits/2026-10-19-hermes-security/KEY-ROTATION.md`. This setting
belongs to the service, not the Hermes plugin. Ordinary Hermes tools cannot rotate
keys or retire recovery keys.

For local semantic recall, prepare the selected free FastEmbed model separately,
then set `ENHANCED_EMBEDDING_MODEL` and `ENHANCED_MODEL_CACHE`. Startup uses only
the prepared cache. Without a configured model the service reports text retrieval.
Source-linked graph recall requires a configured Qdrant/ArcadeDB/Valkey pipeline
and a ready indexing worker. Without that configuration it reports unavailable.
Use the canonical memory/index runbook to provision and qualify those stores;
an outbox alone does not establish working index delivery.

Local memory processing does not make the chat model local: retrieved facts may
be sent to Hermes' configured chat model when they enter the conversation.

## Disable or recover

Switch the test profile back to its built-in provider and restart it to stop
external memory use. Keep its data and keys for recovery; do not delete them as
part of disabling the integration. Restore and compare a disposable backup before
attempting a real-data recovery. Existing legacy memory tables and diskcache files
are not automatically imported or erased by this service.
