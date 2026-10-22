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

Current test-model direction: use glm-5.3-flash through the existing Z.ai GLM
Pro Coding Plan with temporary test overrides only. Preserve all existing
Hermes default/fallback model settings. See the latest owner correction below;
older local-model next-step wording is historical.

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

## Owner model correction: Z.ai for tests; preserve existing defaults

The owner returned the local inventory at
de771c38d7838c699c865ca0611a7cb78b237505. The main config was readable and has
two declarations for http://localhost:8888/v1 and the seven expected local model
IDs, without declared context sizes. That is not network/model evidence or a
statement that either declaration is the active default. The two earlier test
configurations returned unreadable_unsafe_or_invalid; the bounded reader did
not distinguish ownership, permissions, links or parse errors. Do not infer
data loss or change permissions just to make that inventory green. The current
restricted pilot already passed its independent native connector checks.

The owner then directed GLM-5.3-Flash from the existing Z.ai GLM Pro Coding Plan
for testing, reserving local chat models for offline work/cloud unavailability.
Their latest clarification supersedes the intervening conditional permission
to change defaults: "Do not change the default models setup done in Hermes
Agent. Just use GLM-5.3-Flash for your tests and checks." Preserve main/default,
bot and profile model settings. Use temporary test-run overrides rather than
changing configured defaults or fallback/router behavior. No model settings have been changed by these
inspection steps. A local fallback cannot be reported as a passed GLM test.
This chat-model choice does not replace the existing local embedding/index
component or authorize hosted extraction/private-data admission.

Official Z.ai [supported-tool and endpoint documentation](https://docs.z.ai/devpack/tool/others)
lists Hermes as a supported general-purpose agent and gives the Coding Plan
OpenAI Chat Completions endpoint https://api.z.ai/api/coding/paas/v4. The
[model-switch guide](https://docs.z.ai/devpack/latest-model) documents the model
ID glm-5.3-flash. Do not substitute the general pay-as-you-go endpoint
https://api.z.ai/api/paas/v4. Documentation is not proof of account entitlement,
quota, credential availability or actual successful model calls. Preserve
existing context/safety guards and verify the chosen runtime capabilities.

The inspector now has an explicit main-only mode, main(zai_only=True), still
read-only as the ordinary operator. It reports the allowlisted current model
identifier, builtin Z.ai selection flag, exact public Z.ai endpoint kind,
declared GLM models and presence booleans for credential fields/references and
extra headers. No key values, reference names, source provider names, .env file,
secret store, model/network request or configuration write belongs to this step.
It distinguishes dedicated Coding Plan endpoints from the general API, without
assuming that a builtin provider name proves which endpoint will be used.
Current defaults may be reported for reconciliation but are never modified.

The focused suites pass 282 cases, zero failures/skips and no reported warnings,
including 20 new Z.ai endpoint/privacy/main-only regressions. The original local
inspection mode is preserved. Execute the exact published hash-verified blob in
the main-only Z.ai mode before arranging narrow credential use and temporary
GLM test overrides; do not request keys in chat or copy the whole owner .env.
Native Z.ai inventory, authenticated account access and cloud model/memory
capture remain pending. No additional cloud subscription or paid app is needed
for this read-only configuration inspection.

## Native Z.ai declarations received; one synthetic Coding Plan request next

The owner returned the main-only receipt at
681247e71554e80c91df5de1de7c168ceff69908. The current default identifier was
GLM-5.3-Flash and the selected provider was builtin Z.ai. No explicit endpoint
or additional Z.ai route was declared. The false requested-model comparison was
a case-sensitive diagnostic bug: the inspector now compares case-insensitively.
No model configuration was changed. The implicit endpoint remains unresolved
by that receipt; no credential, quota or model access was tested.

Use deployment/check_zai_pilot_connectivity.py only through the pinned,
hash-verified operator command supplied with its delivery. Run as the normal
Ubuntu-Hermes owner with the existing protected tools1 Python. The parent must
retain the ability to use sudo for the UID switch; do not apply no-new-privileges
to the parent. An outer sudo -v authenticates the operator; application code is
never executed as root. The child is hermes-runtime with no-new-privileges,
zero effective/ambient capabilities and only its primary group.

Unlike the previous metadata inspection, this explicitly authorized model test
reads the owner's fixed main config.yaml and private .env; if no selected Z.ai
key is found, it reads auth.json for one unambiguous Z.ai pool credential.
Sources must satisfy the helper's ownership, permissions, no-link and size
checks. It uses the pinned pure environment parser, not the native provider
resolver, auth-store loader or endpoint detection. Those higher-level paths can
probe endpoints or migrate/cache settings. Other provider credentials are never
passed to the child. Only the selected ordinary model key crosses a private
stdin pipe, not command arguments, environment variables, files or reports.
No signing/recovery key or root service configuration is read. Source bytes
are compared after the test; a concurrent change is reported, never restored.

The child makes at most one SDK Chat Completions request to exactly
https://api.z.ai/api/coding/paas/v4/chat/completions using glm-5.3-flash, a fixed
invented acknowledgement prompt, max_tokens=512 and reasoning_effort=low.
Thinking is enabled: the current official
[GLM-5.3-Flash guide](https://docs.z.ai/guides/vlm/glm-5.3-flash) documents that
it cannot be disabled. The
[Chat Completions contract](https://docs.z.ai/api-reference/llm/chat-completion)
documents the request fields. No automatic retries, endpoint/model fallback,
proxy discovery or redirects are allowed. TLS verification remains enabled.
The request uses the existing plan allowance; account availability is determined
by the actual response, not inferred from documentation. No new subscription,
general API route, local fallback or model-default edit is introduced.

Only a validated acknowledgement/model-match flag and bounded token counts are
reported; response content, reasoning, key and exception bodies are suppressed.
This does not start Hermes chat, call memory tools, write a memory or qualify
automatic capture/context limits. Expected success includes complete,
model_reply_validated, model_called and owner_source_files_unchanged true;
model_defaults_changed, credential_written_to_files, memory_records_written,
hermes_capture_qualified and runtime_qualified remain false. On failure, retain
the fixed public stage/status only and reconcile before another request.

The focused Workspace suites pass 325 tests with zero failures/skips and no
reported warnings. These add 42 connectivity/privacy/identity regressions and
one case-comparison regression to the previous 282. SDK and subprocess calls
in those tests are fixtures; no native cloud request was made from Workspace.
Actual restricted SDK access is pending the owner command. Actual Hermes
model-driven tool/capture and fresh-session recall tests follow separately.

## First restricted SDK attempt failed; sanitized diagnostics added

The owner ran revision 01617e5e182090d23a0eb1b54bd531a07db54528. The helper
reached coding_plan_request, then failed without an HTTP status. No defaults
were written. That stage includes SDK import/client setup, network access and
response validation: it does not prove that a request reached Z.ai, that a key
was rejected, or that the model returned a completion. The first helper hid
too much diagnostic information to distinguish those cases. Do not infer a
network failure or raise the token allowance without further evidence.

The revised helper keeps the exact same endpoint, model, 512-token limit,
synthetic prompt, credential-selection rules and one-request/no-retry behavior.
On failure it now prints a reconstructed JSON summary with a fixed category,
HTTP status if available, completion_received, allowlisted finish_reason,
content_present, reasoning_present and bounded numeric usage. A category such
as completion_limit_reached is distinguished from SDK arguments, missing
dependencies, DNS, TLS/certificate, connection, timeout or HTTP errors. Unknown
errors remain unclassified; raw exception text, arbitrary class names, response
content, reasoning text and keys never appear. completion_received describes
an SDK completion object; HTTP errors can have a status without such an object.
Diagnostics do not bypass validation or count an incomplete answer as success.

Run the new pinned/hash-verified operator command once and return only its
public summary. This can make one additional existing-plan request; no automatic
retry or token-budget increase is introduced. Model-driven memory qualification
remains pending. The focused fixture suites pass 343 tests, zero failures/skips
and no reported warnings, including 18 new failure-classification and privacy
cases. Actual failure cause and native GLM success await the new host receipt.

## OpenAI fallback: independent restricted pilot sign-in

The owner returned the direct DNS comparison: both normal and restricted
accounts resolve GitHub and the OpenAI API/ChatGPT hosts, while api.z.ai gives
EAI_AGAIN under both. No account-specific DNS denial is established. See
HERMES-ZAI-DNS-CHECK.md. Authentication/model access is a separate gate.

The reviewed deployment/login_pilot_codex.py starts the native pinned Hermes
auth_add_command for openai-codex with type oauth, no browser launch and a fixed
pilot label. It deliberately avoids the older model/login handler that calls
_update_config_for_provider. The native
[credential-add handler](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/auth_commands.py)
and [device-flow selector](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/auth_codex_browser.py)
perform a fresh login, not a human CLI-token import. Source review is not native
login evidence. Official [OpenAI authentication guidance](https://learn.chatgpt.com/docs/auth)
describes device sign-in and the possible account/workspace enablement
requirement; it does not establish eligibility for this host/account/model.

Execute only the pinned/hash-verified operator command as hermes-runtime using
the protected tools1 Python, no-new-privileges, zero capabilities, only its own
group and a clean environment. HOME is /var/lib/hermes-runtime; HERMES_HOME is
the existing enhanced-cognee-pilot. Never run application code as root. The
operator authenticates sudo outside the restricted process. Existing auth stores
are refused/preserved. The helper also refuses changed/unsafe pilot settings
or a readable human auth store. It compares config.yaml, enhanced_cognee.json
and .env bytes before/after, without printing them or modifying their contents.

Before login, a bounded 12-second subprocess checks auth.openai.com resolution.
No credentials are read from the human account, passed through stdin/environment
or copied from its .hermes/.codex. The terminal displays only the fixed OpenAI
device URL and a validated one-time code; the code belongs only in the owner's
browser, never chat/screenshots/reports. Native stderr/other stdout and raw
exceptions are suppressed. Complete sign-in using the existing eligible account.
This creates a NEW private pilot auth.json credential pool entry and native
auth lock/config-backup scaffolding as needed. The first credential may set
active_provider inside this new pilot auth store. It does not change persistent
model configuration or the normal account's authentication/defaults. Existing
runtime/global/CLI auth state is not imported or overwritten. Do not delete a
partial auth store or repeat sign-in blindly after a failure.

The helper verifies private file ownership/mode and exactly one expected native
OAuth pool entry without printing tokens/account identity. Success reports
fresh_pilot_oauth_saved and pilot_settings_unchanged true; model_called,
model_defaults_changed, human_credentials_copied, memory_records_written and
runtime_qualified false. This is sign-in only, not a model/context/capture test.
Subsequent gpt-6.1-sol tests must use explicit temporary runtime selection and
prove actual account/model access. Profile backup/recovery and renewal remain
separate gates. Stop on existing auth state and reconcile; no rollback/deletion
is automatic. To leave the fallback unused, do not start pilot model calls;
credential revocation/removal requires its own deliberate operator step.

Focused Workspace suites pass 376 tests, zero failures/skips and no reported
warnings, including 33 new login/output/privacy/preservation checks. All OAuth
and process calls in those tests use fixtures; no live sign-in or model call
was performed in Workspace. Native pilot sign-in remains pending the owner.

## Native pilot sign-in passed; one Responses completion next

The owner returned complete=true at 42f61235b1ef2228fad08484be94e14b3592b69a:
hermes-runtime saved fresh pilot OAuth, pilot settings were unchanged and human
credentials were not copied. Model/default/memory/runtime-qualification flags
remained false. This supersedes the pending sign-in checkpoint above. Do not
retain the interactive one-time code in reports, fixtures or Git. Sign-in is
not model entitlement or completion evidence.

The next reviewed helper, deployment/check_pilot_codex.py, selects only the
single expected pilot OAuth pool entry at the fixed subscription endpoint.
It never uses the auth resolver, refresh/import, main account or general API.
Only the pilot auth.json and two non-secret settings files are read and checked
for private ownership/mode; their original bytes are compared after the request.
The memory-token .env and human stores are not opened. No file is written.

The helper uses the native protected Hermes request converter/preflight,
required identity/account headers, stream assembler and completion normalizer
from the pinned source: [request/response adapter](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/codex_responses_adapter.py),
[headers](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/codex_headers.py),
[stream assembly](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/codex_runtime.py)
and [normalization](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/auxiliary_codex_response.py).
No compatibility substitute, chat session, tool registry or memory tool is used.

Exactly one SDK Responses request is permitted at
https://chatgpt.com/backend-api/codex/responses, for gpt-6.1-sol, low reasoning,
store=false and a fixed invented acknowledgement prompt. The request guard
rejects retries, other routes/models, tools, elevated service tiers and altered
store/stream/reasoning fields. SDK retries, proxies and redirects are disabled;
TLS verification stays enabled. Native subscription code omits max_output_tokens
because this endpoint rejects it; there is no promised server token cap. The
short prompt, 60-second transport timeout, 75-second stream/event guard and
120-second outer command bound limit the test. It uses the existing plan quota.
Official [model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
describes supported low reasoning, while [Codex model guidance](https://learn.chatgpt.com/docs/models)
conditions availability on account/client rollout. Documentation is not the
pilot's account/model-access evidence.

The check requires an actual response.completed event, matching server-reported
model metadata, a final stop and the exact acknowledgement without tool calls.
The assembler's request-model echo alone is not server-model evidence. Only
booleans and bounded token counts leave the process; raw replies, reasoning,
headers, OAuth tokens, IDs and exception bodies are suppressed. Failures report
fixed categories/status/allowlisted provider codes, never a local fallback.

Execute the pinned/hash-verified blob under the same restricted identity and
clean environment as the sign-in helper, selecting main(approved_test=True).
Expected success includes native_responses_contract_passed,
model_reply_validated, server_model_matches_requested and
profile_settings_and_auth_unchanged true. full_hermes_turn_tested,
hermes_capture_qualified, memory_records_written and runtime_qualified remain
false: actual model-selected capture and fresh-session recall follow separately.
On authentication failure, reconcile only the pilot login rather than importing
the human store or automatically signing in again.

Focused fixture suites pass 415 tests, zero failures/skips and no reported
warnings, including 39 new completion/selection/privacy/wire-guard checks. Native
module/SDK substitutes are fixtures in these tests; the host command supplies
actual protected native-component/model evidence. No Workspace cloud call,
installed model completion, context qualification or full release claim is made.
