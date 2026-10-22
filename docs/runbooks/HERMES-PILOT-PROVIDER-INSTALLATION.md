# Protected pilot provider installation

Prepared 22 October 2026. Scope: Ubuntu-Hermes, existing hermes-runtime account,
existing enhanced-cognee-pilot profile. The owner subsequently returned a
successful native installation/loader receipt at
ab0626632a5f4c271ec6c9c3cac33f099a7d5dee: artifact/link created, version 0.1.0,
eight tools registered as hermes-runtime. Credentials, active provider selection,
memory/model connection and full runtime qualification remain false. This is
not private-data admission. The sections below describe that staged procedure.

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
