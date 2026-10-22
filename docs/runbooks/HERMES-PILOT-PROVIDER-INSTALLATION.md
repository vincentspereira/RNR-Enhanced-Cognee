# Protected pilot provider installation

Prepared 22 October 2026. Scope: Ubuntu-Hermes, existing hermes-runtime account,
existing enhanced-cognee-pilot profile. The owner subsequently returned a
successful native installation/loader receipt at
ab0626632a5f4c271ec6c9c3cac33f099a7d5dee: artifact/link created, version 0.1.0,
eight tools registered as hermes-runtime. Later native receipts confirm ordinary
credential issuance and, at 81f20cf6d81f8b127d7c5c4c1c0fd7b269b317c7, provider
selection, initialization, authenticated status and empty recall with .env
unchanged. Chat-model calls, memory-record writes and full runtime qualification
remain false. This is not private-data admission. The sections below preserve
the staged procedure and its dated checkpoints.

## Purpose and selected integration

Install the version 0.1.0 Enhanced Cognee native MemoryProvider with eight callable
tools using the actual Hermes contract at source
4d04303818b61bf3aa09278af48356315515965b. This uses Hermes' supported user-profile
plugin directory and memory loader, rather than installing the entire Cognee
repository as a plugin. The pinned upstream [memory loader](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/plugins/memory/__init__.py)
and [MemoryProvider contract](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/memory_provider.py)
are the source references. No MCP transport is introduced by this step.

Reuse the qualified version-command/access-tested release:

    /opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1

The add-on contains only __init__.py, client.py and plugin.yaml, copied from
integrations/hermes/enhanced_cognee with hashes embedded in the installer.
Combined filename/NUL/content bundle SHA256 is
29cb9fa3400a816aabd656587eede8024151a76906132230616d8e33afde9e55.
Provider code is not installed into the large runtime snapshot or human .hermes.

Artifact:

    /opt/hermes-runtime/providers/enhanced-cognee-0.1.0-29cb9fa3400a

Pilot link:

    /var/lib/hermes-runtime/.hermes/profiles/enhanced-cognee-pilot/plugins/enhanced_cognee

## Reviewed operator execution

Use the normal vincentspereira terminal inside Ubuntu-Hermes. Desktop can remain
open. Use the exact published revision and helper SHA256 supplied in the guided
command. Fetch through the independent protected-deployment checkout without
changing its checked-out branch. A bounded four-file Git tar stream supplies the
helper and three provider files. The isolated/no-site system Python verifier
checks names, types, sizes, duplicates, completeness and the helper hash without
extracting paths. The helper checks all provider hashes before publication.
No checkout imports or third-party application code execute as root.

The root phase checks the operator/distro/account and protected executables,
opens the protected destination through directory descriptors without following
links, writes a new detached generation and publishes it without replacing an
existing name. A matching generation is reused. Differing bytes, permissions,
extra files or links are refused and retained. New failed stages are retained
for review; do not remove them without owner permission.

The application phase runs as hermes-runtime with only its own group, zero
effective/ambient capabilities, no-new-privileges, a clean environment and the
protected Python interpreter. Only this child visits the agent-owned profile.
It creates/reuses the exact plugin symlink without replacing an existing name,
checks the actual Hermes profile/contract source, invokes the actual memory
loader with skill registration disabled, checks the MemoryProvider instance
and its eight tool schemas, and shuts it down. Existing plugin isolation policy
remains enforced. There is no compatibility stub, forced loader bypass or
provider/model initialization. An already selected external provider is refused.

## Receipt and limits

Expected success includes complete=true, native_loader_passed=true,
effective_user=hermes-runtime and exactly these registered tools:

- enhanced_clarify
- enhanced_connections
- enhanced_correct
- enhanced_get
- enhanced_recall
- enhanced_remember
- enhanced_retract
- enhanced_status

artifact_created and profile_plugin_link_created can be false on a matching
retry. The following must remain false for this step: provider_selected,
credentials_provisioned, memory_connected, model_called, runtime_qualified.
A failed child reports only an approved stage label; do not paste raw private
configuration or credentials into chat to diagnose it.

The received successful host receipt proves installed native loading. No token,
model route, service request or saved memory was created by this step. The human
Desktop/default profile, other profiles/bots, backend services, existing keys,
backup generations and separate fleet review bundle are outside this change.
The profile owner can change its own plugin link/configuration. Root-owned
provider bytes alone do not create a full sandbox or separate all bot accounts.

## Validation and recovery

Workspace focused suites pass 156 tests with no failures/skips or reported
warnings, including 26 new installer regressions. Filesystem fixtures and
subprocess mocks exercise preservation and privilege selection. They do not
substitute for native Hermes execution, service recall, model capture, provider
security audits, peer-profile isolation or fleet qualification.

No active provider selection is made, so staging alone needs no configuration
rollback. Preserve the staged artifact/link if a later step fails. Any future
activation must archive the previous pilot configuration first and document
returning memory.provider to its prior setting. Do not delete the pilot or
artifact as an automatic rollback. Existing encrypted canonical backups remain
unchanged; before private use, prove backup/restore coverage for the restricted
profile and its future scoped credential, as well as service data/key custody.

After the native loader receipt: provision an expiring ordinary pilot credential
with signed project scope, configure the approved local model route, test actual
authenticated invented-memory operations and capture, review account/profile
isolation and recovery, then consider wider scoped bot onboarding. Existing
release security gates and owner credential review remain separate requirements.

## Initial pilot access after native loader success

The owner subsequently reported the initial read-only preflight as passed:
pilot .env is a regular runtime-owned mode-0600 file; enhanced_cognee.json and
config.yaml are absent; unauthenticated local status returns HTTP 401. Preserve
the existing environment even though it has no Cognee configuration yet.

Use the exact published blob/hash of deployment/provision_pilot_access.py through
the guided Ubuntu-Hermes operator command. This one-shot helper is deliberately
not a general issuer/renewer: it accepts no arbitrary account, path, role,
namespace, key or lifetime. The fixed token lives for 24 hours, using the same
HS256 claim format as src/memory_admin.py: tenant qualification, project
hermes_pilot, subject hermes_pilot_runtime, agent hermes_pilot, role api_client,
capture_policy selected. It grants no administrator/reviewer role or sharing
membership. The current signed identity/server policy define its scope.

The hash-verified root stdlib phase only reads the protected operator/API
signing configurations, checks protection/key agreement and signs ordinary
tokens. It does not open the agent-owned profile. A clean restricted child
receives only the ordinary valid/expired/altered test tokens and public claims
through stdin. The child uses the already protected Hermes interpreter and
dotenv parser; it does not load unrelated environment settings into its process.

Before writing, it requires the unconfigured pilot, validates private .env
metadata and syntax, refuses an existing token assignment, checks HTTP 401 for
missing/expired/altered tokens and HTTP 200 for the exact fresh pilot scope with
schema 3 and AES-256-GCM. These status probes may update operational request
counters but write no memory record. No proxy or redirect receives the token.

It saves an exact mode-0600 .env-before-cognee-pilot-* copy, writes/fsyncs a
private new stage, checks the locked original/name/content for intervening
changes, atomically publishes and verifies readback. Existing settings remain
byte-for-byte at the beginning of the new .env. No other profile, service key,
model configuration or backup generation changes. Failures retain originals
and prepared files; never delete or retry by overwriting an existing token.
The account can edit its own files; advisory locking does not make same-account
processes mutually secure. Use one operator and do not launch the pilot during
initial provisioning. The human Desktop profile can continue independently.

The public receipt contains scope/expiry, backup basename and status booleans,
never the credential or key. credential_installed and both API-check flags must
be true. provider_selected, model_called, memory_records_written and
runtime_qualified must remain false for this step. Authentication status does
not establish recall/capture, index freshness, complete isolation or fleet
admission. The 208 focused passing cases include 52 new access regressions;
network/process fixtures are mocked and native issuance is still pending.

The ordinary credential expires after 24 hours, without changing any persistent
service/recovery key. Qualify a protected operator renewal/revocation procedure
before unattended use. An account lock or disabling the provider does not revoke
a bearer token already copied elsewhere. On a later failure, retain the private
backup and stop only the new pilot path; restore the exact saved .env through
the restricted operator workflow only after checking concurrent changes. Do
not rotate global keys, erase the pilot or mark owner acceptance automatically.

## Received initial credential and next native provider reads

The owner has now returned complete=true from initial issuance at
44a093fc5eb712670bf7464777d840831d47d564. The ordinary pilot credential expires
2026-10-23T18:23:15+00:00. Authenticated status and all three denial controls
passed under hermes-runtime. The exact environment backup was retained. Provider
selection, chat/model calls, memory-record writes and full qualification were
still false in that receipt; do not repeat initial issuance or overwrite the
installed credential to progress to configuration.

The next hash-verified restricted operator step executes
deployment/configure_pilot_provider.py directly as hermes-runtime under
no-new-privileges and the already protected tools1 Python, never root. Use a
clean environment with HERMES_HOME pointing to the existing pilot and a bounded
90-second operator timeout. The human Desktop can remain open; do not launch
the pilot concurrently. No runtime rebuild, service restart or default-profile
switch is requested.

The helper verifies account/process/profile/provider protection and native source
paths. It creates only missing mode-0600 enhanced_cognee.json and config.yaml,
with atomic non-overwrite publication. The JSON selects the local origin,
10-second transport timeout, selected capture and reviewed sharing; YAML selects
only memory.provider=enhanced_cognee. No chat model, credentials or gateway
configuration is stored in these two settings files. Existing matching settings
allow a retry after interruption; differing settings, links or loose permissions
stop before either file is overwritten. The credential .env is read/checked for
unchanged bytes, not edited. Native config loading can also create Hermes' normal
last-known-good settings backup inside the pilot.

Actual pinned Hermes APIs supply profile identity, profile .env parsing, scoped
secret binding and memory-provider loading. Bind only the ordinary Cognee token
to this profile through set_secret_scope; do not copy other model/admin keys or
load a full environment into the process. Keep the existing plugin isolation
policy enforced. The provider initializes and performs enhanced_status and an
empty-scope enhanced_recall. The latter can call the already prepared local
embedding model and derived indexes. It does not call a chat model or admit a
memory record. Server-authorized reviewed sharing remains enabled without
changing membership or grants. Native config/secret-scope APIs are described in
the pinned [secret-scope source](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/secret_scope.py)
and the memory-loader reference above; no compatibility shim is substituted.

Expected success includes provider_selected, native_provider_initialized,
authenticated_provider_status_passed, empty_scope_recall_passed and
credential_file_unchanged true. chat_model_called, memory_records_written and
runtime_qualified remain false. created_settings can be empty on a matching
retry. A failure prints only its stage; files may already be published at a
later failure, so preserve and reconcile rather than auto-rollback or delete.
The 234 focused passing cases include 26 new settings/read-contract regressions;
mocked provider calls are not native evidence. Await the host receipt before
marking this step passed. Empty recall does not qualify saved-memory recall,
model-selected capture, OS/fleet isolation or private-data admission. The next
stage must select the existing authorized local chat route and exercise an
invented decision through actual memory tools and fresh-session retrieval.

## Native provider connection received; local chat route inventory next

The owner returned complete=true at
81f20cf6d81f8b127d7c5c4c1c0fd7b269b317c7. Both settings files were created under
hermes-runtime. Actual provider selection, initialization, authenticated status,
empty recall, selected capture and reviewed-sharing settings passed; the
credential file was unchanged. chat_model_called, memory_records_written and
runtime_qualified remain false. This supersedes the pending native configuration
checkpoint above, while saved-record retrieval/model-selected capture remain
untested on the new restricted pilot.

Run the hash-verified deployment/inspect_local_model_routes.py as the ordinary
human operator, never sudo/root. It uses the existing protected tools1 Python
and no-new-privileges with a clean environment and a 30-second timeout. It reads
only the main and two earlier synthetic profile config.yaml files. It does not
open .env, external secret stores, conversation histories, the fleet bundle or
other environments, and makes no network request or model call. No file changes
or Hermes startup occur.

Only explicit credential-free loopback origins with an empty or /v1 path,
allowlisted model IDs, declared context integers, recognized API modes and
credential-reference/header presence booleans can reach the summary. Other
configuration and inline key/header values are not printed. YAML parsing can
encounter inline credential fields in memory; this is not a claim that every
source byte is non-secret. Origins containing userinfo, queries/fragments,
non-loopback hosts or unexpected paths are omitted without revealing them.
Environment-expanded URLs are not resolved. Missing/unsafe/invalid files get
only a fixed source label/reason; raw errors and private paths are not dumped.
The inventory is bounded to 32 entries per provider section and 16 model IDs
per route. No source provider name or credential-variable name is printed.

Treat output as configured declarations only. A context number is not proof of
the server's real context limit, and a model ID is not proof it is currently
loaded. A missing/empty local inventory is not proof that no local route exists.
Reconcile the actual route before connecting/testing the pilot; never start a
replacement server, reload models during current Desktop work, copy Windows
model weights or substitute a cloud fallback to fill a missing field. The
focused suites now pass 262 cases with zero failures/skips and no reported
warnings, including 28 new inventory/privacy cases. Native inventory remains
pending; fixture success is not host model-route evidence.
