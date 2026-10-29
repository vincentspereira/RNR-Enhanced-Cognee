# Enhanced Cognee for a Hermes bot fleet

## Approved rollout scope - 22 October 2026

The owner approved the permanent restricted account and initial profile in
[the account plan](HERMES-LIVE-PROFILE-ACCOUNT-PLAN.md), with the explicit final
objective of connecting the main Hermes assistant, all 40-plus bots and all
other Hermes profiles after qualification. The pilot does not limit that scope.
Inventory the actual current fleet; 41 bots plus a controller below is the
previously tested example, not a fixed maximum or proof of installed coverage.

Start with the new restricted profile and invented facts. Once it passes,
connect existing profiles in bounded batches with individual mappings, access
checks, renewable credentials, explicit profile-backup coverage and a preserved
way to reopen each previous configuration. Record every actual profile as
pending, qualified or connected; do not report the fleet complete while any
profile is unaccounted for. Future profiles use the same onboarding process.
Approved common knowledge remains reviewed and permission controlled.

One runtime account separates agents from the human administrator; it does not
separate all bots from each other. Inspect filesystem/process access for each
trust boundary before choosing whether profiles can share an account or need
separate restricted identities/sandboxes. Preserve the existing bots during the
initial setup. Source tests and the owner's approval are not installed-fleet
evidence or automatic private-data admission.

## Recommended arrangement

Use one maintained Enhanced Cognee codebase and one protected memory service for
the initial trusted bot fleet. Give the controller and each separately configured
bot profile its own scoped credential and private memory space. Forty-one bots
plus the controller means 42 logical identities, not 42 PostgreSQL/Qdrant/graph/
cache stacks or 42 copies of the maintained application.

A profile's memory-provider object is a client of that service. It does not mean
a separate database server is required. Hermes' official provider contract binds
each provider instance to an active profile and secret scope:
<https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin>.

| Component | Recommended scope |
|---|---|
| Controller/main profile | Its own private working memory and ordinary credential |
| Each standalone bot profile | Its own private memory space, distinct agent identity and credential |
| General portfolio guidance | Reviewed library available to admitted profiles |
| A project team | A narrower reviewed library for its participating bots/projects |
| Human sharing reviewer | Separate expiring reviewer credential, never given to an agent |
| Canonical database backup | One consistent backup containing the included spaces, sharing metadata and history |

The controller should not receive an administrator credential or automatic access
to every bot's private records. Useful knowledge reaches other profiles through
reviewed, sanitized current summaries. A correction withdraws the old published
version until the replacement is reviewed; revocation is checked on every read.

## What must be configured per profile

1. Map the profile to an explicit canonical tenant, memory-space/project ID,
   subject and agent ID. Keep the mapping in an operator registry. Use canonical
   project identifiers up to 32 characters; a display name is not an authority.
2. Provision a distinct project-scoped credential. Do not copy the controller's
   token or place a service signing, database or recovery key in a profile.
3. Install the reviewed provider in that profile's plugin directory from the
   GitHub checkout inside Ubuntu-Hermes. Keep one maintained source version;
   per-profile plugin copies are deployment artifacts, not separate forks.
4. Use the profile's normal Hermes memory setup and profile secret store. Its
   non-secret settings identify the same service URL, selected capture and
   whether reviewed shared recall is enabled. Signed credentials determine scope;
   the model cannot select another project's namespace in a tool argument.
5. Plan credential renewal before unattended activation. Operator-issued tokens
   expire; copying a one-hour test token to every bot is not a durable rollout.
   The approved operator/identity mechanism must renew or replace credentials
   without putting service signing authority in a bot. No fleet-wide renewal
   daemon or everyday-profile activation is claimed here.
6. Test each profile's own recall, another profile's denial, approved shared
   guidance and correction/retraction behavior before admitting private data.

A temporary delegated child or cron invocation is different from a standalone
profile bot. The provider intentionally avoids automatic writes from non-primary
agent contexts. A child can return a proposed summary to its owning profile;
do not create a new database instance for every temporary child.

## Isolation and capacity limits

Profiles separate Hermes configuration and ordinary memory routing. They are not
a strong OS security boundary if all bots run under one Linux user and can read
one another's secret files or become root. Sensitive or untrusted bots need
restricted filesystem/process authority, separate OS users or suitable sandboxes
and no access to other profiles' credentials. A separate service instance is an
option for a different trust boundary, retention policy or independent recovery
requirement, rather than a default consequence of having more profiles.

One service has shared resource limits and a shared outage domain. Keep bounded
admission and per-identity budgets. Bursts beyond current admission receive a
clear busy response; retry with the SAME idempotency key after backoff. Do not
solve bursts by creating new write identities or disabling limits. Capacity
qualification must use the actual intended mix of active bots, query rates,
embedding workload and inference endpoints. Forty-two configured profiles do not
mean 42 models should remain loaded or run concurrently.

The present first deployment remains the isolated test service inside
Ubuntu-Hermes. Other systems can later use a controlled authenticated API route;
they do not need shared project folders or Windows mounts in Hermes. Installation,
network routing and the ordinary-profile rollout remain subject to the existing
qualification/review sequence.

## Evidence and current deployment status

- A synthetic real-PostgreSQL/API test creates 41 bot spaces plus a controller,
  checks concurrent scoped writes with bounded-admission retry, private recall,
  cross-profile denial and reviewed library membership/publication/revocation.
  Corrected shared guidance requires a fresh review.
- A separate host-contract test initializes 42 provider instances in independent
  profile contexts and checks distinct credential revisions and caller mismatch
  refusal. This is not an installed Hermes gateway or model-driven fleet test.
- These tests do not qualify 42 simultaneous inference sessions, long-term load,
  installed OS/credential separation, automatic credential renewal or a private
  fleet rollout. No everyday/bot profiles were activated by adding this runbook.

## Backups

The native Hermes backup covers profile state; the native workspace archive
preserves selected Linux source names, links and modes. Neither is a substitute
for the separate canonical database backup at
`/var/backups/enhanced-cognee` inside Ubuntu-Hermes.

The updated Windows backup script pulls only completed encrypted database
archive/manifest pairs from that approved directory, verifies source/copy hashes
and includes them in encrypted cloud generations. It neither mounts Windows in
Hermes nor exports private recovery identities. Directory ownership, private
service credentials, first backup/restore and the timer must still be verified
inside Ubuntu-Hermes. Missing pre-activation coverage is reported explicitly;
enable `-RequireCogneeBackup` on the Windows job after service activation.

One canonical restore recovers all included bot spaces and their sharing/history
metadata. The operator must then recheck access, encryption and derived-index
rebuild. Keep recovery keys in the owner's independent password manager, not in
any bot's ordinary or extended memory.
