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

## Native model completion passed; selected capture and fresh recall prepared

Owner receipt at 6546a972a4a47d0d249c2d3b34e0b33a0056ffbc confirms the actual
restricted gpt-6.1-sol completion: native contract, server model and reply
validation passed, with 38 prompt and 12 completion tokens (50 total). Pilot
settings/auth remained unchanged; no memory was written. This supersedes the
pending completion checkpoint, not the remaining full-turn/capture/fleet gates.

check_pilot_codex.py now also provides main_memory(stage="capture"|"recall",
approved_test=True). Use the exact pinned/hash-verified operator command for
each stage in a separate process. Ordinary main() remains the single-completion
check. The memory stages use the actual protected run_agent.AIAgent interface,
native MemoryManager, provider loader, secret scope and installed provider;
there is no replacement tool loop, gateway launch or guard bypass. The pinned
[AIAgent interface](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/run_agent.py)
and [native initializer](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/agent_init.py)
define the runtime arguments. The gateway CLI was deliberately avoided because
its authority can outlive a timed-out client; its older --run-budget argument
is refused on that path. No gateway/default-profile change is needed here.

Both stages require the same restricted identity, protected Python, current
private settings/auth, hash-verified protected provider and exact local memory
endpoint. The helper binds only ENHANCED_COGNEE_ACCESS_TOKEN from the private
pilot .env to the native secret scope; it reads no human configuration or keys.
Authenticated status must match qualification/hermes_pilot/hermes_pilot_runtime,
selected capture, schema 3 and AES-256-GCM before any agent turn. Missing/expired
memory access fails before testing; do not reissue signing keys or expose them.

The capture stage requires an empty pilot namespace and no prior test receipt.
It creates a private mode-0600 /var/lib/hermes-runtime/cognee-pilot-model-test.json
receipt with an invented fixture identifier and capture session, never keys.
It is no-replace: preserve it and any saved evidence after a failure instead of
blindly repeating capture or deleting/overwriting records. The user's fixed
invented Larch planning decision asks only for an explanation, not a remember
action. Native selected-capture policy must lead the model to enhanced_recall
then enhanced_remember. Authoritative own-scope recall plus GET must confirm
exactly one current version-1 record containing the fixture and thirteen-day
decision. No existing memory is corrected, retracted or permanently deleted.

Only the qualification agent's in-memory tool surface is narrowed to native
recall/get/status/remember handlers (recall stage omits remember). Other tools,
including terminal/browser/session-search and correction/retraction, are absent
from this test. The provider/plugin/settings are unchanged. Explicit per-instance
gpt-6.1-sol/openai-codex/Responses/low-reasoning arguments use the pilot's own
OAuth without a credential pool or fallback. SDK retries/redirects are disabled.
A wire guard permits at most six exact subscription Responses requests, checks
model/store/tools/tier, and rejects other routes/tools/models. There is a
100-second native turn budget and five iterations, with a 180-second outer
process bound. This can use several existing-plan requests, unlike the earlier
single-completion test. Native startup may perform standard metadata lookup and
create local config/cache/session scaffolding; only invented task data is used.
This is not a claim that all native initialization egress was independently
audited or that Desktop/gateway delivery was tested.

The recall stage must run in a new process with a different session and empty
conversation history. Its prompt includes only the fixture identity and the
question, never the decision interval. It must answer thirteen days and cite
the saved record ID, with identical current record content/version and count.
All original config/settings/auth/.env bytes must remain unchanged. The synthetic
record and test receipt are retained as evidence. Raw replies, reasoning, tool
arguments/results, credentials and full configs are captured privately in memory
and never printed by the helper; only fixed booleans/counts/allowlisted tool
names leave it. Canonical encrypted memory contains the selected invented
summary, not raw chat output. Native Hermes runtime scaffolding is separate.

Success reports native_agent_turn_passed and the appropriate stage's capture or
fresh-session recall flag; runtime_qualified remains false pending the remaining
qualification/recovery/rollout gates. On failure, a fixed stage/category and
test-evidence/may-have-written flags prevent false success or unsafe retries.
The focused fixtures pass 437 tests, zero failures/skips and no reported
warnings, including 22 new fixture/agent/wire/preservation cases. Native agent,
model, memory and filesystem calls use fixtures in those tests. Installed-host
capture and fresh-session recall remain pending the two owner commands.

## Capture refused existing receipt: inspect before retrying

The owner returned a fixture_preparation failure from the prepared capture
command: existing_test_evidence_preserved_review_before_retry and receipt
presence true. The current attempt stopped before native agent construction
or a new chat-model request. Its memory_writes_may_have_occurred=false field
describes this attempt, not every earlier attempt. The receipt is published
before native_memory_turn, so its existence alone proves neither a saved record
nor a completed capture turn. Its creation time/origin was not established by
the relayed output; do not invent an explanation or delete/reset it.

The new main_memory(stage="inspect", approved_test=True) delegates to a
read-only native-provider inspection. It uses the same restricted preflight
without reading auth.json, selecting OAuth, importing AIAgent or calling a chat
model. The existing private receipt is read/validated, never rewritten. Only
the pilot settings, ordinary memory-token .env and authenticated qualification
scope are used. Existing provider hashes and directory/credential protections
still apply; no root/human store or operator key is read.

Only GET status/current-record and own-scope POST recall are used; recall may
use the service's existing local embedding/index machinery. No canonical memory
write, model turn, cloud request, receipt mutation or cleanup belongs to this
step. It reports scope_active_records, matching_fixture_records, bounded current
version and booleans for the fixture's invented decision, capture-session
provenance and selected-tool metadata. No fixture/session/record IDs, content,
sources, raw exceptions or secrets are printed. Metadata is actor-submitted
evidence, not proof of completed model-selected capture; the report explicitly
keeps capture_agent_turn_qualified=false and runtime_qualified=false.

The checked profile files' bytes and receipt's parsed state/inode/size/change
timestamps are compared after inspection. Auth.json is not opened or claimed
freshly verified. Empty/duplicate/nonmatching/corrected evidence is reported
without repairing it. Malformed or unsafe evidence is refused and retained.
Use the next pinned/hash-verified inspect command once and return its summary;
choose recall/resume only after reconciling it. No login/key replacement,
record deletion or repeated capture is needed just to perform this inspection.

Focused fixture suites pass 450 tests, zero failures/skips and no reported
warnings, including 13 new read-only inspection and output/privacy cases.
Native receipt/record reconciliation remains pending; test fixtures do not
establish whether an earlier native capture succeeded or wrote a record.

## Existing native record reconciled; proceed to fresh-session recall

The owner's inspect result at 2585bf30847b17417c36dce80435637dfe3918e4
passed as hermes-runtime for enhanced-cognee-pilot: scope_active_records=1,
matching_fixture_records=1, current_version=1, fixture_content_validated=true,
capture_session_provenance_matches=true and selected_tool_origin_matches=true.
Checked profile files and the receipt were unchanged. OAuth was not read and
neither a chat-model call nor a canonical memory write occurred in inspection.
The matching record does not establish a completed original capture agent turn;
capture_agent_turn_qualified and runtime_qualified remain false.

Preserve both the existing record and receipt. Run main_memory(stage="recall",
approved_test=True) in a new process using the same pinned helper blob at
2585bf30847b17417c36dce80435637dfe3918e4, SHA256
5d5dc28a38f80d520519444dfaa6ac0110c15d071822a2a4c754f743b1e3c66f.
Use the existing protected tools1 Python, hermes-runtime identity, pilot HOME,
clean environment, no-new-privileges and 180-second outer timeout. Do not rerun
capture, sign in again or change model defaults for this step.

The recall stage supplies only the fictional project identifier and a question
in a fresh session with empty history. Native Hermes must select recall/get
tools, answer with the saved interval and cite the record. Canonical content,
record count/version and profile settings/credentials must remain unchanged.
The authorized GPT-6.1-Sol subscription route is temporary for this check;
bounded requests can consume existing-plan usage. Return only the helper's
sanitized summary, including failures. Successful recall is a separate result
from original capture-turn completion or full runtime/fleet qualification.

## 23 October: diagnose an incomplete recall turn without raw logs

The owner-run recall at helper revision 2585bf30 stopped at native_agent_turn
with native_agent_turn_incomplete. The old summary did not identify which
native completion check failed. It did not establish an authentication, quota,
DNS or retrieval failure. Preserve the existing fixture receipt and record.

The updated helper retains the same native agent, model route, request/time
bounds and recall-only tool surface. It adds bounded HTTP response observations
and fixed diagnostics for incomplete results or propagated exceptions. No raw
error, final answer, transcript, arbitrary result keys, session/record identifier
or credential is printed. Unknown native reason/exit labels become null; this
means unclassified, not a successful turn. A request_guard_failure names a
locally rejected request, not a provider's verdict. HTTP statuses establish
observed responses, not successful completion. native_response_present reports
only whether text was present, never what it said.

The failure summary now checks profile/settings/credential byte preservation.
Recall failures report memory_writes_may_have_occurred=false because the narrowed
native tool surface has no canonical memory write tool. This corrects the old
overbroad flag; canonical record preservation is only verified when the later
authoritative comparison completes. Existing incomplete-turn refusal remains;
no completion check or Hermes safety guard was relaxed.

Run one new pinned/hash-verified main_memory(stage="recall", approved_test=True)
from the ordinary Ubuntu-Hermes operator terminal. Use the existing restricted
tools1 interpreter/profile and 180-second timeout. Return the sanitized result,
including native_diagnostics on failure; do not supply private logs or auth
files. This can make the already authorized synthetic subscription-model
requests. It does not retry capture, renew credentials, change model defaults,
install a runtime or activate everyday bots. The focused Workspace fixture
suites pass 464 tests with zero failures/skips and no reported warnings; the
diagnostic retry and runtime qualification remain pending installed execution.

## 23 October: guard request-scoped clients and accept native callback arguments

The c3fde7cb operator result shows native_completed=true, a nonempty native
response and no native failure/error/interruption/partial flag, but zero observed
requests/statuses/tool calls. Checked profile/settings/credential bytes were
unchanged. The helper refused qualification; the saved-answer/citation and
canonical-record comparison were not reached. Do not treat zero observations
as proof of no model calls or classify this as an authentication failure.

Two mismatches were found against public Hermes source at the installed pinned
revision 4d04303818b61bf3aa09278af48356315515965b:

- agent/client_lifecycle.py creates separate request clients through the native
  instance's _create_openai_client factory. agent/agent_runtime_helpers.py copies
  client kwargs and creates a fresh HTTP wrapper. Hooks on agent.client alone
  do not cover these calls.
- agent/tool_executor.py passes event, tool name, preview and display arguments
  positionally. The old two-positional-argument callback raised TypeError,
  which the native safe callback swallowed. The new callback discards the extra
  arguments and records only known event/tool names.

The correction decorates the ephemeral qualification agent's native factory;
it returns the native client after installing request/response hooks, SDK retry
and redirect restrictions. It also handles initial/cached clients. One lock
protects the shared six-request budget across request/recovery clients. Reused
transports receive each hook once. Provider handlers, native turn execution and
cleanup remain; installed program files, defaults and profile configuration are
not rewritten. This is a qualification-instance adaptation, not a Hermes release
upgrade or a change to everyday profiles/bots.

Earlier shared-client-only instrumentation did not establish request-scoped wire
coverage or reliable request counts. Earlier zero counts do not establish zero
subscription usage, and the physical-request guard must not be described as
enforced on those unobserved clients. The separate basic completion helper
guarded its actual transport and is unaffected by this lifecycle correction.

Run the next pinned/hash-verified recall command once in the normal Ubuntu-Hermes
operator terminal. Its SHA256 is
f5473ff5f02791b8801d8c44ec39911418b918e20f5e2f72bf8f7200c7932363.
Use main_memory(stage="recall", approved_test=True), the same tools1 interpreter,
restricted pilot, clean environment and 180-second outer timeout. Do not repeat
capture, clear the fixture, copy credentials or change defaults. Return only the
sanitized result. Successful native completion plus request observation must
still pass the answer/citation and canonical version/content/count checks.

The focused suites pass 468 tests, zero failures/skips and no reported warnings.
Transport regression uses real HTTPX hooks with a simulated transport; other
native agent/network/process operations use fixtures. No Workspace test calls
the model or proves installed recall. Native qualification remains pending.

## 23 October: original fixture recall passed; follow-up capture next

The owner-run d67ce6ca3e27ddb90623dd94c622e57907cfbd1f recall completed as
hermes-runtime/enhanced-cognee-pilot with gpt-6.1-sol. Both native_agent_turn_passed
and fresh_session_recall_passed were true: enhanced_get was observed, two model
requests were guarded, and the native answer/citation matched the saved
thirteen-day decision. Canonical comparison found one version-1 active fixture
unchanged. Profile/settings/credential bytes were unchanged; no model defaults
or canonical memory were written by this recall stage.

selected_capture_passed=false describes the current recall stage, not a failed
capture. The original capture completion is still unproven. Do not clear the
existing fixture/receipt to rerun the empty-scope capture. Runtime, private-data,
everyday-profile and fleet admission are still separate gates.

The next prepared mode is main_memory(stage="capture_followup", approved_test=True).
Run it once through the next pinned/hash-verified operator command. It requires
exactly one matching original fixture and no follow-up receipt. It writes one
new private receipt at /var/lib/hermes-runtime/cognee-pilot-capture-followup.json,
using O_EXCL/O_NOFOLLOW and 0600 permissions. The original receipt remains at
/var/lib/hermes-runtime/cognee-pilot-model-test.json. No evidence is replaced,
deleted or auto-retried, including after a failed/interrupted attempt.

The new prompt describes a different fictional project and a nineteen-day
decision, asking only for a one-sentence explanation. Native selected-capture
policy must lead the model to recall and then remember without an explicit
save request. The agent gets the same temporary subscription model, narrowed
native tools, guarded request clients and time/request bounds. It can add one
invented memory to the qualification scope; existing plan usage may be consumed.

Success requires a completed native turn, recall-before-remember tool evidence,
exactly two active records, a distinct new canonical version-1 record with the
new interval, session provenance and selected-tool origin, plus an unchanged
original canonical record and receipt file stamps/content. Profile/settings/
credential bytes must remain unchanged. The result should report stage
capture_followup, selected_capture_passed=true, synthetic_active_records=2 and
original_fixture_and_receipt_preserved=true. fresh_session_recall_passed=false
is expected for this capture stage. runtime_qualified remains false.

Focused fixtures pass 487 tests, zero failures/skips and no reported warnings.
They cover separate no-replace receipts, duplicate/replay and scope refusals,
old-record/receipt drift, wrong new provenance/origin/ID/count/interval, UUID
collision, canonical GET version/path validation, native call order and failures.
The new capture is prepared; the owner-run original-fixture recall above is the
current installed-model evidence. No everyday configuration or bot is activated.

## 23 October: automatic Cedar capture passed; fresh Cedar recall next

The owner-run 005bcf10b7a570624fdcb4a61dd1acdf4325bafc capture_followup
passed as hermes-runtime/enhanced-cognee-pilot with gpt-6.1-sol. Both native
agent completion and selected_capture_passed were true. The helper observed
enhanced_get, enhanced_recall and enhanced_remember, and four guarded model
requests. It verified recall-before-remember order internally, a new version-1
Cedar memory with the expected decision/provenance/origin, exactly two active
records and preservation of the original Larch fixture and receipt. Checked
settings/credentials were unchanged and model defaults were not edited.

fresh_session_recall_passed=false is expected in this capture stage. The new
record is invented qualification data. This is completed native selected-capture
evidence; do not replay the historically unqualified original Larch capture or
infer fleet/private-data admission. runtime_qualified correctly remains false.

The next prepared mode is main_memory(stage="recall_followup", approved_test=True).
Use a new process with the same restricted pilot/tools1 interpreter, clean
environment, hash verification and 180-second outer timeout. It reads the
existing Cedar and Larch receipts and verifies two active version-1 canonical
records before calling the native agent. The new session has empty history;
the prompt contains only the fictional Cedar identifier and a question, not
its interval or saved record ID. Only native recall/get/status tools are enabled.

Success requires a completed native turn, guarded model requests, the correct
saved interval and citation, unchanged Cedar content/version, unchanged Larch
canonical row and both receipts' states/file stamps, plus unchanged checked
profile/settings/credentials. It writes no receipt or canonical memory. Return
the sanitized summary, including failures; do not rerun capture or clear files.
Expect fresh_session_recall_passed=true, original_fixture_and_receipt_preserved=true,
followup_receipt_preserved=true, synthetic_active_records=2, current_version=1 and
memory_records_written=false. selected_capture_passed=false describes this new
recall-only stage and does not undo the preceding capture result.

Focused Workspace fixtures pass 500 tests, zero failures/skips and no reported
warnings. Thirteen additional cases cover successful/failed Cedar recall,
missing receipt, scope/count drift, old-record/receipt drift, wrong provenance/
origin/record ID, wrong answer/citation and new-receipt modification. Native
agent/provider/network calls use fixtures; fresh installed Cedar recall remains
pending. Existing defaults, everyday profiles/bots and the installation remain
unchanged by this preparation.

## 23 October: new decision retrieved; clear-error correction next

Owner output at ca500986c99e1dec3f77e373c3d42fb722785cca passed
recall_followup: completed native gpt-6.1-sol turn as hermes-runtime in the
pilot, enhanced_get observed and two guarded model requests. Both active
version-1 canonical fixtures and both receipts were preserved, with unchanged
checked settings/credentials and no default edit or canonical write. Together
with the prior completed Cedar capture, the invented-data save/retrieve cycle
now has native evidence. The stage's selected_capture_passed=false is expected.
This narrow success does not qualify everyday profiles, gateways or the fleet.

The next prepared stage is main_memory(stage="correct_followup", approved_test=True).
It intentionally changes only the invented Cedar decision from nineteen to
twenty-three days. It requires the current version-1 Cedar/Larch fixtures,
exactly two active records and both existing private capture receipts. A new
private no-replace cognee-pilot-correction.json receipt under the runtime home
is written before the native turn. If it exists already, stop and reconcile;
do not remove it or repeat the correction automatically.

The new session receives a clear fictional user correction and asks for a
one-sentence explanation. It offers only native recall/get/status/correct tools,
requires recall-before-correct and preserves the usual model/request/time
bounds. The supplied MemoryManager stays initialized in the pinned constructor.
A test-instance memory transport guard permits one version-checked PATCH of
the known Cedar record with its identifier/new interval, refusing other records,
new records, retraction and duplicate PATCH attempts before HTTP. This adds a
qualification boundary; it neither replaces handlers nor bypasses native guards.

Success requires Cedar's same ID at version 2 with correction lineage and the
new interval, plus exact old/new content in the bounded retained history.
Larch and both capture receipts must remain unchanged, together with checked
profile/settings/credentials and the correction receipt. Expect
clear_correction_passed=true, previous_version_preserved=true, current_version=2,
synthetic_active_records=2 and memory_records_written=true. No additional record
or permanent deletion is expected. The capture/recall flags describe this
correction-only stage and remain false; runtime_qualified remains false.

Run the next pinned/hash-verified command once in the normal Ubuntu-Hermes
operator terminal using the same restricted pilot/tools1 interpreter and clean
environment. Existing subscription usage may be consumed. Send only the
sanitized result; on failure retain all receipts/records for review. Defaults,
everyday profiles, bots, program files and service keys remain unchanged.
Focused fixtures pass 534 tests, zero failures/skips and no reported warnings;
native correction is still pending. Ambiguous clarification/privacy behavior,
renewal/recovery/isolation and release/fleet checks remain separate.

## 23 October: clear correction passed; retrieve the current version next

Owner output from 2f297dd2c52938db860008bcc9958e825ebb6961 passed native
correct_followup as hermes-runtime/enhanced-cognee-pilot with gpt-6.1-sol.
The helper observed enhanced_correct/get/recall and five guarded model requests,
then validated the same Cedar record at version 2, its new interval/hash lineage
and exact prior/current content in retained history. Two active records remained,
with Larch, both capture receipts, the correction receipt and checked settings/
credentials preserved. No default edit occurred. This is a versioned correction,
not a new memory record or permanent deletion. The stage's capture/recall flags
are expected to be false. Full runtime/fleet admission remains open.

The next prepared mode is main_memory(stage="recall_corrected", approved_test=True).
Run the next pinned/hash-verified command once using the same restricted pilot,
tools1 interpreter, clean environment and 180-second outer timeout. It securely
reads the existing correction receipt and capture receipts, verifies current
version 2 against retained version-1 history and then starts a new native session
with empty history. The prompt supplies only the fictional Cedar identifier and
a question/citation request; neither review interval nor record ID is supplied.

Only recall/get/status tools are enabled. The answer must give the corrected
current interval and cite the record; returning the superseded interval fails
this current-only question. Canonical Cedar content/version must be unchanged,
and both history versions, Larch, all receipts and checked settings/credentials
must remain preserved. There is no canonical write or receipt creation; native
startup may still create its ordinary local cache/session scaffolding.

Expect fresh_session_recall_passed=true, corrected_recall_passed=true,
previous_version_preserved=true, correction_receipt_preserved=true,
current_version=2, synthetic_active_records=2 and memory_records_written=false.
Stage capture flags remain false; they do not undo the earlier capture/correction
passes. runtime_qualified remains false pending the other gates. Do not rerun
correct_followup or reset any receipt if this read-only check fails.

Focused fixtures pass 561 tests with zero failures/skips and no reported warnings.
The 27 added cases cover safe receipt parsing, prior-history selection, fresh
current-answer/citation, stale answers and canonical/receipt preservation. Native
agent/provider/network calls use fixtures; installed corrected recall is pending.
This step can consume existing subscription usage, with defaults and everyday
profiles/bots unchanged.

## 23 October: corrected recall hit the model rate limit; local operations next

The owner returned complete=false/stage native_agent_turn from helper revision
086e61e698e46b3bddec48befe35829ea46fe900. The three observed HTTP statuses were
429; native failure_reason was rate_limit. No tool call was observed, checked
profile/settings/credentials were unchanged and no canonical write was enabled.
The post-turn authoritative comparison did not complete. Do not infer the
exact reset time, a credential fault or a failed prior correction from this
result. Corrected recall remains unqualified; preserve all fixtures/receipts.

The test helper now latches the first observed 429 across its initial/request/
recovery clients and rejects further requests before sending. SDK retries were
already disabled; Hermes' own turn retries explain why three physical requests
were previously observed. This qualification guard leaves native guards intact
and cannot claim that an account limit has reset. Already in-flight concurrent
requests are not retroactively cancelled, and a later manual process has a fresh
latch. Any observed 429 refuses success even if a native result says completed.

The next safe operator step is main_operations(approved_test=True), using the
same restricted account and pinned/hash-verified helper. It reads only checked
profile settings and ordinary Cognee .env, decodes bounded token-expiry metadata
without claiming local signature verification, and requests authenticated local
API status. It reads no OAuth store, memory content or receipts and constructs
no chat agent. It writes/renews nothing and consumes no cloud-model request.
Claims are explicitly unverified locally; API acceptance is a separate current
server observation. Safe expiry metadata remains available on an API refusal.

[The operational-readiness review](HERMES-PILOT-OPERATIONAL-READINESS.md) explains
the scope, required renewal checks and restricted-profile recovery gap. Existing
home-selected backups and canonical database dumps do not automatically include
the new /var/lib/hermes-runtime profile. Its backup proof remains false/unverified
in this status check; no backup or Windows task is changed and V12 stays paused.

Focused Workspace fixtures pass 579 tests with zero failures/skips and no reported
warnings. Eighteen added cases cover expiry/privacy/identity validation, read-only
operations/status refusals and first-429 blocking across request/recovery clients.
The native status check remains pending; no cloud/model call ran in Workspace.
Defer another corrected-memory model recall until its limit permits a deliberate
retry; no provider change, credential copying or limit bypass is introduced.

## 23 October: owner-selected second pilot OpenAI account

The owner confirms the first account reached its five-hour usage limit and
authorizes a fresh sign-in to his second account for continued pilot tests.
This is pilot-only account enrollment; main Hermes defaults, first-account
credential fields and everyday bot/profile settings must remain preserved.
No automatic account rotation, status reset or retry across accounts is added.

The pinned/hash-verified login helper now supports
main_secondary(approved_login=True). Run it under the same hermes-runtime
identity, protected tools1 interpreter, clean environment and no-new-privileges
wrapper as the original sign-in. Allow a 360-second outer timeout. Existing
auth.json must contain exactly the original named native OAuth entry; the
normal auth.lock, when present, must be a private regular single-link file.
A separate private advisory lock excludes competing secondary-helper sign-ins.
It does not lock out unrelated Hermes processes; keep the pilot idle throughout
sign-in. The human/global auth stores remain forbidden, and pilot settings must
match the prepared memory-only configuration. No existing credential is removed.

Before starting native auth_add_command, the helper checks OpenAI sign-in DNS
and preserves the existing pilot auth.json in a new no-overwrite mode-0600
auth-before-secondary-<random>.json inside the private profile. This is a local
credential copy, not an encrypted off-machine recovery proof. Keep it private
and retain it for review. The profile-backup coverage gap remains open.

Open the terminal's fixed OpenAI device-login URL in a private browser window,
then deliberately sign in to the SECOND account. Do not paste device codes,
passwords, emails or tokens into chat. Only the terminal prints the short-lived
device code. This uses Hermes' native fresh OAuth add operation; it imports no
human credential file. The new entry is named cognee-pilot-codex-secondary.

Verification requires exactly two expected labels, the original entry's fields
preserved, unchanged checked pilot settings and differing native account
identity hints. The native comparison decodes account/subject metadata without
signature verification: it detects an accidental repeat account but does not
prove token validity, entitlement, quota or a reset. IDs remain private. A same
account, unknown hint, unexpected pool or concurrent drift stops qualification
and retains all state/copies for review; do not delete, overwrite, retry login
blindly or restore a stale auth store over a newer grant.

After the owner's successful sign-in receipt, basic completion and memory test
entry points accept explicit credential_label="cognee-pilot-codex-secondary".
Without that explicit choice, the old single-account selector refuses a two-row
pool. It never falls back to the first credential or uses native pool rotation.
The native agent receives the selected token only, with credential_pool=None
and no fallback model. First-429 blocking remains enforced. Each account keeps
its own provider restrictions; signing in makes no quota-availability claim.
Check ordinary local Cognee credential expiry/status independently, then resume
the read-only recall_corrected stage rather than replaying capture/correction.

Workspace fixture suites pass 622 tests, zero failures/skips and no reported
warnings. The 43 added cases cover private no-overwrite backups, concurrent/
unsafe locks, original credential/status preservation, wrong-account refusal,
native protected identity hints, strict second-account selection and corrected
recall using that explicit token. Native auth/model/network calls use fixtures;
no second-account login, provider request or installed-host pass is claimed.

## 23 October: corrected recall passed; ambiguous-change check prepared

Owner-run secondary enrollment, local authenticated status and corrected recall
now pass at helper revision 2117ba01ae473dfd0ff4698c212eec01c8c013cf. The last
stage observed enhanced_get, two guarded GPT-6.1-Sol requests, two active records
and current version 2 with retained old history/receipts/settings/credentials.
No memory write or default change occurred. Keep the earlier first-account 429
as historical evidence; this pass does not assert that its limit has reset.

Do not rerun the old 086e61e6 recall or df64ad56 operations commands to reconstruct
these completed gates. The former lacks explicit second-account selection. The
existing original/capture/correction receipts are deliberately preserved and
write stages are not replayed. The next operator step is one pinned/hash-verified
main_memory(stage="clarify_followup", approved_test=True,
credential_label="cognee-pilot-codex-secondary") under the same protected tools1
runtime, clean restricted environment and 180-second outer timeout.

The new prompt describes an uncertain, undecided proposed twenty-nine-day Cedar
change. It does not supply the stored interval/record ID or demand a particular
tool by name. Keep normal memory-edit choices visible to the model. A successful
native turn must consult memory, then call enhanced_clarify for the existing
record, ask a basic English question and leave the current record unchanged.
No editing tool may be called. A separate qualification client guard refuses
every canonical write before transport and records attempts; even a refused
write fails qualification. The native provider's local pending set must contain
only the expected record before shutdown. No human confirmation is fabricated.

Post-turn authoritative reads validate current version 2, unchanged canonical
content/history and Larch, exactly two active records, all three receipts and
checked profile/settings/authentication files. This mode writes no new receipt
and uses the existing scoped memory identity, explicit second-account OAuth and
first-429 model guard. Expect ambiguous_clarification_passed=true,
standing_decision_unchanged=true, canonical_write_attempts=0,
previous_version_preserved=true and memory_records_written=false. Capture,
fresh-recall and corrected-recall per-stage flags are false here; earlier passes
stand. runtime_qualified remains false.

The pending marker is native in-process state; shutdown clears it. This stage
does not qualify persistence across restarts or the later human-answer turn.
It is a narrow invented-case observation, not proof of all conversational
ambiguities, sensitive-data exclusion or fleet isolation. On refusal preserve
all records/receipts, return only the sanitized report and reconcile the actual
failure instead of repeating write stages or downgrading safeguards.

Workspace fixtures pass 664 tests with zero failures/skips and no reported
warnings, including 28 new clarification/guard/preservation cases and 14 existing
provider-contract cases added to the focused run. No new cloud or installed-host
call ran in Workspace. The installed clarification check is pending.

## 23 October: failed clarification needs bounded diagnostics

The owner's ef39013eab7aba9df2c1413e39f53943ddaaa0f8 run returned
ambiguous_change_not_preserved_for_clarification, unchanged checked profile
settings/credentials and no possible canonical writes from the guarded test.
The terse result did not identify the failing condition or complete the
post-turn canonical/receipt comparison. Preserve that failure and do not infer
the model's tool sequence, a lost memory, a question or a successful gate.

Run the next pinned/hash-verified clarify_followup once, with the same explicit
secondary label and restricted 180-second operator wrapper. It now reports
bounded native turn/tool-name diagnostics and clarification booleans/counts.
If the completed turn misses a clarification condition, authoritative reads
still check unchanged canonical history, counts, receipts and profile files
before setting post_turn_canonical_and_receipt_preservation_verified=true.
Canonical drift cannot be converted into a behavior failure with a false
preservation pass. No identifiers, conversation text, arguments or credentials
are printed. The required behavior, visible editing choices and pre-transport
write guard are unchanged. Expect either the same success flags or an actionable
sanitized diagnostic; do not describe this reporting fix as an installed pass.

The [remaining rollout checklist](HERMES-REMAINING-ROLLOUT-CHECKLIST.md) separates
five shared readiness groups from actual fleet admission, rather than promising
a fixed remaining command count. Existing 40-plus profiles need inventory and
batch scope/launch/backup checks. Private credential-review coverage remains a
separate owner checkpoint; completed custody/recovery steps are retained.

Workspace fixture suites pass 672 tests, zero failures/skips and no reported
warnings, including eight added diagnostic/deferred-preservation cases. Installed
diagnosis and the other rollout groups remain pending; no Workspace model call,
profile activation, Windows backup or unrelated fleet change occurred.

## 23 October: account for native automatic recall before clarification

The owner's latest diagnostic identifies the sole failure as absence of an
explicit read tool before enhanced_clarify. The completed turn had two HTTP 200
model requests, correct pending target, a reply question mark, no edit/write
attempt and verified post-turn canonical/history/receipt/profile preservation.
Hermes can legitimately obtain the record through automatic prefetch before
calling tools; the earlier qualification predicate omitted that read path.

The unchanged pinned native implementation is visible in
[turn context](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/turn_context.py),
[memory manager](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/memory_manager.py)
and [Codex adapter](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/agent/codex_responses_adapter.py).
Automatic recall is a source-supported explanation, not retrospective proof of
what the model received in the earlier run. Preserve the earlier refusal.

Run the next pinned/hash-verified clarify_followup once under the same restricted
wrapper, explicit secondary label and 180-second limit. The helper now verifies
the current canonical ID/version/content in the native provider's returned read
and in marked native user input_text inside a model request receiving HTTP 200.
It correlates that response with the actual request, and freezes whether this
delivery occurred before the first clarify callback. An explicit read also must
match the current record. A late, stale, malformed or undelivered prefetch does
not satisfy the requirement. No read/tool/context is fabricated or added to the
model prompt to make the test pass. No IDs/content are printed or persisted by
the qualification instrumentation.

Expect the previous success fields plus memory_evidence_verified=true and,
when automatic recall supplies the evidence, verified_prefetch_before_clarify=true.
The tool list may contain only enhanced_clarify; an extra get/recall tool is not
required when this delivery proof passes. Every edit/write/pending-target/history/
receipt/profile check remains enforced. runtime_qualified stays false for the
other rollout groups. No installed provider upgrade or settings change is needed.

Workspace suites pass 698 tests, zero failures/skips and no reported warnings,
including 26 new evidence/delivery/order/guard cases. This adds source regression
coverage, not 26 operator/model runs. Installed delivery qualification is pending.

## 23 October: uncertainty passed; batch local API privacy without a chat model

The owner-run 0768a43e0d3e429327b23e108ab5ad4eafe56e30 check passed with
verified native prefetch before enhanced_clarify, two model requests, current
version 2, no edit/write attempt and preserved prior history/receipts/profile.
This completes the narrow single-turn uncertainty gate. Keep runtime_qualified
false for the other work; do not replay completed capture/correction/recall.

The next operator check uses a two-file Git archive: the unchanged reviewed
check_pilot_codex.py core and the new check_pilot_privacy.py extension. Use the
new pinned revision, hashes and restricted tools1 Python in the supplied command.
The bootstrap caps the archive at 256 KiB and verifies the privacy source before
executing its definitions. Its tested validator then checks exactly both allowed
regular source files, their sizes/hashes and allowed parent directory entries,
refusing extras, duplicates and links before executing the core. No file is
extracted to the host filesystem and the adjacent checkout is never imported.
This reuses checked account/provider/receipt logic without extending a single
qualification source beyond the existing 64 KiB per-file budget.

Call main(core=reviewed_core_namespace, approved_test=True) on the extension.
It permits only the existing private memory-only pilot settings and root-protected
provider, and uses the ordinary memory token through native secret scope. It
reads no OAuth store or operator key and constructs no chat agent/model. Normal
authoritative fixture recall may use the existing local embedding/index path.
There is no OpenAI request/quota, installation, settings/default edit, token
renewal, backup, fleet activation or automatic permanent deletion.

The eleven cases expect credential-shaped content, metadata, evidence, category,
retry key and a credential-bearing correction to receive HTTP 422. Selected
personal details in content/metadata/evidence must receive HTTP 409 with the
clarification flag. Every example is synthetic and nonfunctional; never substitute
a real password/key or personal detail. The helper stops at the first unexpected
response. Preserve any unexpected synthetic state and the sanitized report;
do not delete/reset fixtures or relax expected refusals to make the check pass.

Before/after comparisons cover the two existing canonical records, returned
version histories, count, all three receipts/stamps and checked profile files.
Successful reporting includes cases_passed=11, credential_rejection_passed=true,
selected_private_detail_clarification_passed=true, preservation flags true,
model_called=false, oauth_store_read=false and memory_records_written=false.
native_model_privacy_qualified=false is intentional: model-selected privacy,
later human clarification, renewal/recovery and fleet boundaries remain open.
Refusal patterns are finite, not a complete personal-data classifier. Ordinary
request-budget accounting may occur even when memory admission is refused.

Workspace suites pass 741 tests, zero failures/skips and no reported warnings,
including 43 new API/admission/source/scope/bundle/preservation cases. The actual
ASGI/auth/schema/admission code is exercised with request-budget persistence
substituted and canonical-database access forbidden; other host operations use
fixtures. Installed privacy behavior remains pending the next owner-run batch.

## 23 October: installed API privacy pass; one native synthetic privacy turn

The owner returned all eleven expected privacy refusals at 37cc5d9b, preserving
canonical history, receipts and checked files, without OAuth or chat-model use.
Do not repeat that API batch or earlier capture/correction/recall passes.

Next use the new pinned/hash-verified two-file Git archive command in a normal
Ubuntu-Hermes operator terminal as vincentspereira, not inside Hermes chat or a
root shell. It runs under hermes-runtime using the existing tools1 protected
Python and enhanced-cognee-pilot. Leave the pilot idle during this bounded check;
everyday Desktop/bot profiles remain unchanged.

The new invocation is:

```python
privacy["main_model"](core=core, approved_test=True,
    credential_label="cognee-pilot-codex-secondary")
```

It uses the explicit secondary pilot subscription OAuth for gpt-6.1-sol, without
refreshing/rotating accounts or changing defaults. Only invented, nonfunctional
sensitive canaries go to the model. One native turn can use up to six physical
requests within the existing 100-second native run budget; stop on first 429.
No privileged service/recovery key is read. Memory edit tools remain visible,
but every API mutation is guarded before transport. Any editing tool choice or
write attempt fails; the test does not hide these tools to force a safe result.

Expect stage=privacy_model, native_selected_privacy_passed=true, zero canonical
write attempts, no full sensitive canary in the short reply, unchanged canonical
history/receipts/profile/credentials and memory_records_written=false. This is
one finite behavior case, not universal privacy coverage. Compare preserved
state after failed turns too; retain evidence on failure and relay only the
sanitized JSON. Existing profile token expiry or provider rate limits can block
the run; neither should be bypassed. runtime_qualified remains false for later
human-answer, retraction/history, sharing/isolation, renewal/recovery and release
work. Focused Workspace suites pass 760 tests, zero failures/skips and no reported
warnings; model/native paths here are fixtures, not installed-host evidence.

## 23 October: native privacy passed; next qualify ordinary token renewal

Owner-run 79264eeb confirms the native sensitive-input case passed: one explicit
secondary-account GPT-6.1-Sol request, no tools or writes, absent full sensitive
canaries and all checked state preserved. Do not repeat it. This finite case
does not qualify later human-answer/pending durability or retraction/history.

Next follow HERMES-PILOT-CREDENTIAL-RENEWAL.md. The new reviewed two-file bundle
uses the existing stdlib issuer core and a separate renewal extension. It runs
only through the human operator, retaining root-only signing and restricted-child
profile writes. It handles the already populated scope and existing ordinary
credential without changing OAuth or model defaults. No chat-model quota is used.
This is prepared manual renewal, not an installed recurring issuer or all-bot
lifecycle. Focused Workspace suites pass 817 tests, zero failures/skips and no
reported warnings; installed renewal is pending the owner's sanitized receipt.

## 23 October: manual token renewal passed; inspect recovery coverage next

Owner-run 8fb6fca9 passed manual fixed-scope pilot renewal. The retained old
file, settings/OAuth preservation, new-token acceptance and negative controls
verified; expiry is 2026-10-24T09:15:06+00:00. No model or memory write occurred.
interrupted_attempts_reconciled=0 is not installed crash-recovery qualification.
Preserve this pass; do not rerun initial provisioning or successful model tests.

Next run the pinned/hash-verified inspect_pilot_recovery.py once as the existing
restricted account with the protected tools1 Python and no-new-privileges.
Its standard-library inventory has no SQLite connection, HTTP/model call or
file write. It reports counts, sizes and protection/binding flags without
private filenames, credentials or contents. See HERMES-PILOT-RECOVERY.md.
It creates no backup or restored files and changes no schedule/Windows script.
Focused Workspace suites pass 846 tests, zero failures/skips and no reported
warnings; installed profile backup and disposable restore remain unqualified.

## 23 October: inventory passed; encrypted profile snapshot/restore prepared

The owner-run 61c272a7 inventory passed: 60 files, 205571 bytes, no detected
SQLite/sidecars or problematic entries, expected protected provider link and
private credentials/receipts present. Preserve that pass; do not repeat it.

The next three-file operator bundle composes the unchanged issuer/inventory
helpers with backup_pilot_profile.py. It makes one bounded file-only in-memory
snapshot under the restricted identity, encrypts/signs with existing protected
keys and verifies a fresh private restore outside the live HOME. It refuses
new databases, unknown links, changing state or exceeded budgets. No plaintext
archive file, recovered program execution, model call, token renewal, schedule
change, cloud upload or fleet admission occurs. Existing generations and source
are retained. See HERMES-PILOT-RECOVERY.md for paths and qualification limits.

Workspace focused suites pass 914 tests, zero failures/skips and no reported
warnings. Sixty-eight new cases include actual age encryption/decryption with
synthetic keys and file/permission round trips; host identity/API boundaries are
simulated. Installed encrypted profile recovery remains pending the owner run.
