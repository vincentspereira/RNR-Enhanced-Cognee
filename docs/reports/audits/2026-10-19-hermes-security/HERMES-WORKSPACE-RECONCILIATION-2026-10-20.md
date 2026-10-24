# Hermes results reconciled with Workspace

Prepared 20 October 2026. Read this checkpoint before older status tables.
The isolated CLI completed synthetic qualification. The entire plan and
private/everyday deployment remain incomplete for the specific reasons below.

## Source and evidence review

Workspace cannot read Ubuntu-Hermes directly and has not changed mounts, interop,
isolation, privileges or host configuration. It fetched the published deployment
branch through GitHub at eca54b0c274b8c00f9a69ea3d5c68713cf766853, reviewed its
two commits and incorporated them without conflicts into
codex/hermes-memory-hardening. Later Workspace safeguards and owner guidance were
preserved. Main was not merged. There is no need to attach the committed reports.

The committed [deployment](HERMES-DEPLOYMENT-2026-10-20.md) and
[follow-up](HERMES-QUALIFICATION-FOLLOWUP-2026-10-20.md) reports contain installed-
host results from that session, not new execution by Workspace. Raw traces and
private recovery/settings remain in Hermes. The follow-up provider SHA-256
13d314e27ce8a8f6195082f1484a40b5ab32416a005345a18fe25edd3af9640b matches the
published branch's bytes. It does not name the later Workspace repair, and old
results are not relabelled as qualification of a newer revision.

- Complete host suite: 78 passed, zero failed/errors/skipped, with real Node, Go,
  Rust and Chromium. The earlier skips and model failures remain historical.
- Four stores, schema 3, worker, two synthetic profiles, graph/source paths,
  sharing/revocation and encrypted restore were exercised. The restored snapshot
  retained 15 records, 30 versions, 42 audit rows, two memberships and a publication.
- The existing local Qwen 27B route passed five selected-save, later recall,
  correction, ambiguity/no-mutation and invented-secret refusal scenarios at a
  served 65,536-token context. It took 196-387 seconds per scenario. Granite and
  Qwen 9B did not qualify for automatic capture. There is no universal model/
  secret-detection guarantee or qualification for 42 concurrent chat sessions.
- Protected runtime/configuration/backup directories were absent. Processes ran
  from the owner's home; the system timer was off. PID 1 was WSL init and sudo
  required a person. Sudo/Docker group membership requires actual boundary review;
  it does not itself prove that unattended root/container access is available.

## Source repairs after review

The received remember-tool description encouraged automatic saving even in an
explicit-only profile. Returned schemas now follow the active capture policy,
without mutating shared/other-profile schemas or selected-capture instructions.
A regression covers policy agreement and cross-instance schema separation.
This corrects contradictory instructions, not a claim that models cannot disobey
or that a profile setting replaces server authorization.

The complete-suite runner now refuses raw artifacts inside the source checkout,
including symlink paths, requires the documented backup tools, disables dotenv/
telemetry in its child and rejects malformed/inconsistent reports. It preserves
earlier artifact directories. Fourteen focused runner regressions cover success,
failure/error/skip/missing/malformed evidence, private logs, preservation and
missing-tool refusal. Together with provider/operator checks, the focused lane
passes 30 tests with zero failures, errors or skips.

The received graph-span validator agrees with the server's endpoint normalization
and supplies only a static repair hint. Server grounding/authorization remains
authoritative, submitted content is not echoed and retry identity is preserved.

## Current phases and remaining work

| Phase | Implemented/qualified scope | Still required |
|---|---|---|
| 0 - Preservation | Source, fixtures and instruction originals preserved | Owner classification/revocation and independent recovery custody |
| 1 - Access | Restricted source, real-store and synthetic profile/role checks | Protected OS/service/operator/store installation and actual non-admin agent denial |
| 2 - Storage | Schema 3, encrypted history, reviewed sharing, workers, synthetic restore | Protected persistent keys/store identities and restore; optional legacy/private migrations only if selected |
| 3 - Release | Reviewed packaging, mitigation and exact-revision main safeguards | Fresh combined-revision checks; unsuppressed frontend audit findings; broader legacy surface has separate admission |
| 4 - Hermes | Eight-tool provider and actual local synthetic capture | Protected installation and reviewed provider update; resource review before wider rollout |
| 5 - Operations | Complete synthetic suite, index/restart fixtures, encrypted recovery | Actual protected restart, approved-path backup/restore/timer, owner custody, native Windows recovery and everyday-use review |

The [protected-service follow-up](../../../runbooks/UBUNTU-HERMES-PROTECTED-SERVICE-FOLLOWUP.md)
contains the existing folder, resumable task and two new host choices with reasons
and alternatives. Recommended: systemd with a coordinated Ubuntu-Hermes-only
restart, and a non-admin synthetic account while Vincent retains administration.
Documenting these choices does not authorize machine changes or bot migration.

Subsequent owner decision, 20 October 2026: Vincent explicitly approved enabling
systemd with a coordinated Ubuntu-Hermes-only restart and preparing a separate
non-admin synthetic test account, keeping his operator account and the 41 bots
unchanged. The follow-up now carries that authorization; do not ask again. Actual
host installation, local authentication and scheduling the interruption remain
execution work inside Hermes, not actions completed by Workspace.

Vincent subsequently authorized removing the non-required synthetic test account
after testing. The handoff now requires a recorded temporary UID/home, preservation
of useful evidence/recovery material and scoped cleanup once the account is no
longer needed. It forbids deleting shared models, protected services/backups,
retained outside fixtures or everyday accounts/profiles. No account was created
or removed by Workspace, and test-account cleanup does not qualify real bots'
operating-system boundaries.

Fresh hosted checks are requested after publication; record their exact revision
and results separately. Main's five trusted-app checks and strict protection were
rechecked. The official braces
[advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) still lists no patched
version. Keep the tested mitigation and complete audit failures visible. No
suppression, fake version, lint removal, new upload destination or protection
bypass was introduced. Old unit counts do not close the remaining phase gates.
