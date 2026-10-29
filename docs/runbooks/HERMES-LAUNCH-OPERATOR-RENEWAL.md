# Allowlisted credential renewal candidate

Prepared inside Ubuntu-Hermes on 24 October 2026. These new operator helpers
are an implementation candidate on the deployment branch. They are not part
of the unchanged 21abf485 restricted wheel and are not installed or enabled.

`fleet_credential_policy.py` admits a bounded root-owned mode-0600 policy,
through root-owned non-writable ancestors without links. Each entry explicitly
binds account/UID/home/profile, tenant/project/subject/agent, ordinary api_client
role, 24-hour lifetime, fixed loopback origin and pinned protected interpreter.
It rejects duplicate private spaces, caller signing choices, and enablement
without reload, launch, backup and OS-boundary admission. The example is wholly
invented and disabled. Do not replace any existing credential with its values.

`renew_fleet_credentials.py` verifies the reviewed issuer, journal code, policy
and new lifecycle source hashes. It reads the signing key only in the root
parent; no key crosses the child environment, stdin, arguments or receipt.
Root never enters the profile tree. Restricted children have no supplementary
groups, no new privileges and zero effective/ambient capabilities. Accounts
with sudo, Docker, root, LXD or Incus administration are refused. Merely having
different profile names does not qualify an OS boundary.

`fleet_credential_lifecycle.py` reuses the reviewed private-file, dotenv and
interrupted-journal primitives. It preserves arbitrary existing configuration,
OAuth and unrelated environment values. Missing/expired/altered API refusal
controls and exact new scope must pass before publication. An already expired
profile requires explicit operator recovery. One prepared/published transaction
retains its original environment, candidate, journal and completion receipt.
Concurrent settings changes stop publication. Reusing an already published
credential is refused without another transaction.

The root ledger records each attempt before issuance. An incomplete attempt
blocks subsequent automatic issuance for that profile. Review the root ledger
and profile-owner journal together; preserve all evidence. Do not fabricate a
done receipt, discard the failure, or run a repeated issuer loop. The reviewed
child reconcile primitive can distinguish prepared and published outcomes,
but a new automated root-ledger reconciliation action is not yet qualified.
Until that gate passes, interruption recovery requires operator review.

Source continuation, 25 October 2026: the new issuer candidate binds an issued
token fingerprint to the exact policy identity/path/executable and driver/helper
hashes in a separate private `.issued.json` record before entering the owner
child. A finite manual `--reconcile ATTEMPT_ID` action takes the issuer lock,
loads that binding, and asks the restricted owner child to find exactly one
matching prepared/published profile journal. It verifies the journal, backup,
candidate/current environment and current API authentication. It never issues a
new credential or changes the environment. It writes a separate root
`.resolved.json`, preserving started/issued/profile evidence. Subsequent issuance
requires a valid bound completion or resolution. Missing legacy metadata,
ambiguous journals, changed policy identity, conflicting current state, expired
authentication and duplicate resolution remain refused for operator review.

`stage_launch_issuer.py --upgrade-disabled` creates a separate
`operator-issuer-candidate-v2`, retaining the original protected candidate and
the exact existing disabled policy. No timer or service is enabled. The prepared
`qualify_launch_issuer_reconciliation.py` combines that staging with two NEW
synthetic profile interruption cases and bound root-ledger recovery using real
API authentication and restricted owner children. Its separate fixture paths
are not fleet enrollment policy entries. Even a passing component receipt does
not qualify active issuer publication, scheduled firing, a running gateway or
per-profile OS isolation. Protected execution remains pending.

The `.service.disabled` and `.timer.disabled` files are review templates only.
They are not systemd units under installed names. Their exact execution identity,
capability transitions, protected code/policy and writable paths still need
installed acceptance. No timer enable command is authorized by these files.
Do not give an ordinary agent a package manager with privileged authority,
signing key, operator database credential or administrator socket.

## Evidence and remaining admission

25 October retained-journal completion PASSED for the original manual and
scheduled publication components, with a matching invocation and 16181 ms from
timer activation to successful service completion. The separate finish receipt
preserves the original failed summary and replays nothing. Reuse that evidence.
The unloaded transient units are not the recurring fleet renewal service.

The prepared `qualify_launch_gateway_renewal.py` uses one NEW synthetic profile
and real native GatewayRunner/TurnRunner/AIAgent objects in one process. It
requires actual old-token expiry denial and automatic multiplex scope/cache
rebuilding with the replacement token; chat/model connections and external
platform adapters are not used. Public native/provider source hashes are pinned
and keys remain in root. The constructor/cache prototype passed without network
calls, but protected real-credential expiry execution is pending. Its scope is
a headless multiplex gateway component, not every existing launch mode or bot.
Standalone, per-profile launch/OS/backup admission and owner custody stay open.

Retained publication inspection confirmed both synthetic cases completed, while
the original aggregate receipt failed after live transient properties were
lost/defaulted. Do not replay either case. The prepared publication helper's
`--finish-existing` mode verifies the original source/ticket and trusted PID-1
journal completion records, exact unit/invocation binding, successful timer and
service jobs, one boot and the configured delay. It writes a separate completion
only if all retained evidence passes; otherwise it returns diagnostics without
issuing credentials or starting a unit. Scheduled component acceptance remains
pending that verification. Live unloaded-unit defaults are not execution proof.

25 October continuation: the owner-run protected reconciliation probe passed
both prepared/not_published and published/published outcomes, preserving active
environments and refusing duplicate resolution. Its scope is root/owner recovery
components on two NEW disposable profiles, not active fleet admission. Reuse it.

The next prepared `qualify_launch_issuer_publication.py` tests the protected
publication child and bound root completion on NEW invented scopes, first
manually and then from a separate one-shot systemd timer. It preserves the
existing disabled policy byte-for-byte. Its fixed qualification cases are not
enrolled fleet entries. Successful component execution, trigger metadata and
unit exit would qualify only that synthetic scheduled component path. Full
policy admission, persistent gateway refresh and recurring fleet operation
remain separate gates. Protected execution is pending; no timer has yet been
created by these prepared files.

Source tests cover policy widening, administrative identity refusal, bounded
typed receipts, prepared/published interruption outcomes, preservation of
concurrent work and existing settings/OAuth, scope/refusal failure, expiry and
duplicate publication. HTTP responses in lifecycle source tests are doubles.
They do not establish installed API expiry, native reload or scheduled firing.

A separate finite installed-native code-path probe used invented strings to
verify exact-byte dotenv refresh, installed secret-scope refresh, changed
provider credential revision and gateway identity, and a freshly initialized
provider receiving the new value. It made no API/model call and does not prove
a real expiry cycle or that an already running gateway rebuilt its agent.

Before installation/enabling, qualify a NEW invented scope with the exact
root-owned allowlist and source. Exercise actual API acceptance/expiry and
native secret refresh, cache invalidation/rebuild, prepared/published crashes,
root-ledger recovery and actual scheduled firing. Preserve the completed
5d0e9a49bdf544359ae6deff record. No resume-answer or mutation replay of that
record is permitted. Each real profile then needs its own mapping, explicit
launch binding, scope checks, trust boundary, backup and disable/restore path.

25 October gateway probe continuation: the original v1 failed its connection
count because native hermes_bootstrap uses connect_ex after import. Preserve
v1 and its failure. Use the separately prepared
`qualify_launch_gateway_renewal_v2.py` for a NEW invented expiry/reload scope.
V2 guards connect, connect_ex and DNS, pins the bootstrap source, and uses NEW
protected artifact/evidence directories. Its source tests and invalid-token
native-import checks pass; protected execution remains required. It starts no
platform adapters, calls no model, edits no existing profiles and does not
approve the fleet. Do not repeat completed native conversations/publication.

Owner-run protected gateway v2 now PASSED at
`operator-evidence/gateway-renewal-v2`: real expiry denial, native cached-agent
replacement, scope authentication and settings preservation; nine memory
connections, no forbidden attempts. Reuse this synthetic multiplex result.
Actual profile launch mappings remain unqualified. The read-only
`inspect_launch_process_bindings.py` prepares bounded owner-only live launch
observations against the retained registry without activation or root keys.
It cannot qualify dormant launchers or establish private OS boundaries.
