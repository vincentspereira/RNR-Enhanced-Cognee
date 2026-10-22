# Restricted account for the first live Hermes profile

Prepared: 22 October 2026. This is a reviewable proposal, not an installed
account or approval to activate private memory. The original temporary test
account was removed as requested; do not recreate it or repeat that deployment.

## Owner decision received - 22 October 2026

The owner selected: "Keep the current setup for invented-data testing only".
Do not create hermes-runtime, prepare its proposed new home, migrate everyday
profiles/bots, or enable private-data use on the basis of the proposal below.
The current administrator account and its memberships remain unchanged. The
existing protected backend, service keys, backups and recovery custody remain
in place. Continue authorized source remediation and separate invented-data
qualification using preserved synthetic profiles after read-only verification.
Do not rerun the removed temporary account's installation or interpret this
choice as approval to bypass OS isolation for private data. No further prompt
for the same account proposal is needed unless the owner revisits the decision.

The proposed permanent-account arrangement below is retained as reference only;
it is not an instruction to execute it under the current owner choice.

## Original proposal and current evidence

Retain vincentspereira as the human administrator. Prepare one dedicated,
non-administrator Hermes runtime identity for the selected first profile. Reuse
the existing protected Enhanced Cognee backend, source and configured model
route. No second database stack or model-weight copy is proposed.

Owner-run Windows-to-Hermes checks report:

- enhanced-cognee-api.service, enhanced-cognee-index.service and
  enhanced-cognee-backup.timer are active. This is current unit-state evidence,
  not a new authenticated recall/index/restore qualification.
- The current Linux account is vincentspereira, including sudo and docker group
  membership. Main ~/.hermes exists, but its enhanced_cognee plugin directory
  and enhanced_cognee.json are absent. Presence checks did not read keys or
  determine the currently selected provider from configuration contents.
- The filtered account listing returned only vincentspereira. It covered ordinary
  UIDs 1000-59999 and names beginning hermes; it was not an exhaustive review of
  every system identity, sudo rule, process or container socket.
- Current protected recovery-package custody passed the separately recorded
  owner/download/checksum/password workflow. Selected historical credential
  comparisons and outstanding coverage remain in RECOVERY-CUSTODY-2026-10-22.md.

A profile name or token cannot protect operator files if the same agent can
become root or administer Docker. Actual operating-system restrictions must be
qualified. Other bots retaining administrative authority can also compromise the
shared host. Creating one restricted identity alone does not prove protection
against those existing privileged agents.

## Concrete proposed scope

| Item | Proposal |
|---|---|
| Runtime account | hermes-runtime; check account/group/home collisions first and stop rather than repurpose unrelated data |
| Home/profile | /var/lib/hermes-runtime and /var/lib/hermes-runtime/.hermes; private directory permissions, bounded writable workspace |
| Privileges | Locked password; no sudo, Docker, LXD or other administrative groups/ACLs; verify actual socket/rule/capability denial |
| Human administration | Keep the original account, memberships, default WSL user and operator workflow unchanged |
| Initial data | Fresh profile and invented facts; preserve the original main profile, its histories and all existing bot profiles |
| Runtime | Inspect the installed Hermes version/entry point and reuse trusted dependencies where safely possible; code must not be writable by the agent; measure storage rather than promise a size |
| Models | Reuse the existing authorized local route and prepared embeddings; no downloads, new hosted calls or uncoordinated global model reload |
| Memory service | Existing loopback API at 127.0.0.1:28080; preserve its stores, namespace history, service identities and recovery keys |
| Provider | Install the reviewed eight-tool plugin into the new profile; no second maintained fork and no widening of the synthetic-only helper's path guards |
| Access | A fresh explicitly mapped ordinary profile identity/project scope and expiring token; no administrator/reviewer, database, signing or recovery keys in the profile |
| Launch | First inspect the supported Hermes CLI/Desktop/gateway paths; agent execution must actually occur as the restricted identity, not merely a helper subprocess while its tools retain administrator access |
| Existing bots | No automatic migration, restart, account/group changes or profile activation; review their real execution boundary before any shared-host private-use admission |

Account creation and profile preparation are separate from private-data
activation. The proposed account is intended to host the eventual active
profile; it is not another disposable test account or 42 backend instances.
Initially it must use invented data until qualification and review are complete.

## Operator implementation and qualification sequence

1. Use one Ubuntu-Hermes operator session in the existing protected checkout,
   /home/vincentspereira/agent-workspace/enhanced-cognee-protected-20261020.
   Verify host identity, revision, dirty/concurrent work and current processes.
   Obtain changes through GitHub; do not blindly pull/reset a running checkout.
2. After the owner's decision on this proposal, check collisions, existing
   access paths, default sudo rules and administrative sockets. Prepare exactly
   the selected account/home, without changing existing user memberships,
   mounts, interop, firewall, memory services or the default WSL user. No distro
   restart or reinstallation of the existing memory runtime is proposed.
3. Inspect the real installed Hermes runtime and supported launch/profile
   mechanism. Resolve code/dependency/model access without broad home-directory
   ACL grants, copying private global settings, changing shared inode ownership,
   or making agent-writable source authoritative for protected services.
4. Prepare only the selected profile and its narrow required model settings.
   Do not copy whole .hermes trees, private notebooks, histories or all bot keys.
   Preserve originals; report any specific selected migration separately.
5. Provision the scoped client token through the trusted operator. The supplied
   issuer permits 1-24 hour lifetimes; qualify expiry and operator renewal before
   unattended use. A short-lived test token is not a durable rollout. Never put
   signing authority or privileged renewal callbacks in agent-controlled files.
6. Verify that the restricted process cannot read operator/API/worker/recovery
   secrets, elevate privileges or use administrative sockets. Check peer profile
   credentials and the actual agent tool runtime, not just group names. Review
   other privileged agent processes before claiming private host isolation.
7. Run actual provider registration and normal guarded model calls. Check
   automatic selected capture, fresh-session recall, correction, ambiguity,
   secret rejection, cross-scope denial and approved sharing. Preserve version
   checks/idempotency. Reuse finite prior evidence only where behavior is
   unchanged; do not infer a fleet or Desktop launch qualification from a CLI.
8. Include the new /var/lib/hermes-runtime profile/workspace in explicit
   recoverable backup coverage before private use. Existing backups of
   /home/vincentspereira do not automatically include this new home. Canonical
   Cognee backups cover memory records, not the whole Hermes profile. V12 remains
   paused at the owner's request; do not start it or assert its pending runtime
   qualification passed in order to close this separate backup requirement.
9. Reconcile current service backup freshness, relevant release/advisory and
   exact-candidate checks, remaining credential coverage, model/resource behavior
   and the owner's activation review before private data/everyday rollout.

## Recovery and alternatives

Before any later profile switch, retain the current profile/settings and a
verified way to reopen the previous setup. On failure, stop only the new pilot
process, withdraw its launch/renewal path, and retain its files/evidence. Account
locking does not itself invalidate an already issued token: respect bounded
expiry and the actual supported revocation mechanism. Do not rotate global
signing keys to stop one pilot or delete accounts/data without permission.

Alternative: retain the present administrator-owned setup and invented-data
qualification while planning a broader runtime isolation change. Removing
sudo/docker from the owner's account is not proposed: it can disrupt existing
work and would need a separate deliberate administrator-recovery plan. Per-bot
accounts or suitable sandboxes may later be needed for distinct trust boundaries;
one shared runtime account is not private OS isolation between all bots.

## Effective scope

The owner chose the current synthetic-only arrangement, not preparation of the
persistent account. No account or private profile was activated by this plan.
Any future change to that decision must be explicit. Existing approval for
reversible repository fixes, publication of the delivery branch and finite
invented-data tests remains separate; no full-release or private-use completion
is inferred. The v12 backup pause also remains in effect until revisited.
