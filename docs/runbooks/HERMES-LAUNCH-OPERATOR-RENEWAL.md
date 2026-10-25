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
