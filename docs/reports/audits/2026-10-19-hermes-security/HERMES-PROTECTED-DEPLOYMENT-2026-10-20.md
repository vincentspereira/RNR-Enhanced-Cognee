# Protected Ubuntu-Hermes deployment qualification

Date: 20 October 2026. This is installed-host evidence, superseding the earlier
preparation and pre-systemd checkpoints for the restricted synthetic service.
The protected service is installed and qualified with invented data. Everyday
profiles, the 41 bots, private memories and other projects have not been activated.
The complete remediation plan and main-branch release are still conditional on
the remaining gates below.

## Source, environment and preservation

- Host: Ubuntu-Hermes; actual host PID 1 is systemd. Source checkout:
  /home/vincentspereira/agent-workspace/enhanced-cognee-protected-20261020.
- Branch: codex/hermes-ubuntu-deployment-protected-20261020. Tested source revision:
  5c10ab033527a59dda0df5b01252069005358242. This merges source repairs 820f164fc
  and 052f98e36 into the original clean ccdfe8f5 preparation checkpoint.
- Desktop was the only deployment operator after Vincent confirmed the CLI idle
  or closed. Source fixes arrived through GitHub. The existing Windows WSL
  administrative launcher was used to operate the host; no new mounts, shares,
  firewall exceptions, symlinks across distros or interop settings were added.
- The existing standalone protected Python, dependencies, embedding cache and
  persistent encryption/index/signing/recovery keys were retained. Only the
  rebuilt memory wheel was updated for the two reviewed source fixes. Dependency
  checks passed; runtime installation and distro restart were not repeated.
- The original stopped home-based stores and earlier qualification environments
  remain intact. Their data was copied into protected store directories before
  startup. Unrelated databases with unknown encryption keys were not replayed.
- All 88 inventoried existing owner/profile configuration files have unchanged
  hashes after testing and temporary-account cleanup. This is evidence for those
  inventoried files, not a claim to have audited every file or every bot.

## Host and protected services

The host is now running with no startup jobs. The WSL physical-console getty
failure was resolved using a narrowly scoped, reversible
/etc/systemd/system/getty@tty1.service.d/10-wsl-console.conf drop-in with
ConditionVirtualization=!wsl. Existing WSL terminals continue to work. The
original unit, journal and WSL configuration were retained privately. No distro
restart was needed for this repair.

The existing /etc/wsl.conf is unchanged: automount is disabled and
appendWindowsPath is false. No Windows drive mounts are present. This does not
claim that Windows interop itself is disabled; that setting is unspecified.
Memory service listeners are loopback only. Existing unrelated listeners were
preserved.

Six services are enabled and running:

| Service | Identity and placement |
|---|---|
| PostgreSQL, port 28434 | ecmem_pg; protected data under /var/lib/enhanced-cognee/postgres |
| Qdrant, port 28535 | ecmem_qdrant; protected vector store |
| ArcadeDB, port 28536 | ecmem_graph; protected graph store |
| Valkey, port 28537 | ecmem_cache; protected cache |
| Restricted API, port 28080 | enhanced-cognee-api; separate DynamicUser |
| Index worker | enhanced-cognee-index; separate DynamicUser |

Runtime is under /opt/enhanced-cognee-memory, store binaries under
/opt/enhanced-cognee-stores, and operator-owned settings under
/etc/enhanced-cognee. The API, worker and backup have different database
credentials. The operator retains administration. The backup identity can read
canonical tables but cannot mutate them; it has no memory decryption or JWT key.

The selected schema-3 database is cognee_hermes_selected_20261020; the running
index pipeline is hermes_deploy_v1. The public offline embedding model remains
BAAI/bge-small-en-v1.5, 384 dimensions. Chat and embedding models serve different
purposes.

## Failures found and repaired

1. Real systemd credential files used root-owned mode 0440 and a named ACL for
   the service identity on a read-only credential mount. The old loader admitted
   only service-owned mode 0600 and refused startup. Source repair 820f164fc
   accepts only the exact restricted systemd mount, parent, owner, mode and ACL
   arrangement, while retaining the original private-file checks and strict
   allowed setting names. Eleven parameterized regressions were added.
2. During restoration, one PostgreSQL worker claim leased all 36 pending events
   but returned only one. The retained reproduction demonstrates the fault.
   Source repair 052f98e36 materializes one locking candidate before UPDATE.
   Three real PostgreSQL regressions cover both planner settings and concurrent
   claims. The failed restore was resumed, its remaining 35 events completed,
   and its pending count reached zero.
3. The protected Qdrant configuration initially omitted the existing access keys,
   which previously came from the home-based launch environment. Direct negative
   tests detected that unauthenticated requests were admitted. Both persistent
   keys are now installed in the protected service configuration: the API uses
   the read-only key; the worker uses the write key. Requests without a key now
   receive 401, valid API reads receive 200 and valid attempted API mutations
   receive 403. No private/everyday memories were admitted during this gap.
4. Initial helper/qualification attempts exposed an unavailable runuser PATH
   entry, cross-filesystem archive rename, an external node_modules link rejected
   by the existing security guard, and a closed-port probe without a short
   timeout. These were corrected without relaxing guards or changing isolation.
   A too-long synthetic project identifier was correctly rejected and shortened.
   Failed attempts and diagnostic fixtures are retained privately.
5. The initial browser launch passed behavior tests but warned about using
   next start with a standalone build. It was rerun with the generated standalone
   server and contained static/public links; the warning is absent and the full
   browser flow passed again. The temporary frontend was stopped and its sole
   CORS origin removed after testing.

Post-repair checks directly exercised real store permissions. API/backup
canonical deletes and worker canonical updates were denied. A graph deletion
targeting an existing edge returned 403 inside an explicit transaction that was
rolled back. Cache access outside the worker namespace and ACL administration
were denied. In each real service mount namespace, the service identity could
open its own credential but could not open the other service's credential or
the operator file. API and worker UIDs were distinct.

## Qualification results

These are separate lanes with overlapping coverage; do not add their counts as
if they were distinct tests.

| Lane | Result |
|---|---|
| Installed complete qualification suite | 93 passed, 0 failures, 0 errors, 0 skips; 58.54 seconds |
| Focused real-store/source regression lane | 41 passed, 0 failures, 0 errors, 0 skips |
| Native Hermes provider/loader | 11 checks passed under the temporary non-admin account |
| Actual OS denial checks | 11 checks passed under UID 1001, without sudo or Docker administration |
| Node, Go and Rust clients | All three passed against the protected systemd API, including Go race checks |
| Real Chromium browser | Login, create/list/detail, versioned edit, dynamic category, retraction/history and credential withdrawal passed |
| Local chat model | Five scenarios passed using the existing Unsloth route; no cloud fallback or guard bypass |
| Actual service restart | All four stores and both API/worker restarted; canonical records/history/audit and sharing tables unchanged |

The source revision 052f98e36 also has successful hosted Required CI run
39483285556: 4,344 unit tests, 3 schema tests, 10 upstream settings/security tests
and 80 canonical checks, all with zero failures/errors/skips. Hosted default-stack
run 39481926570 passed 35 checks. Its exact-image scan reports zero HIGH/CRITICAL,
26 MEDIUM and 10 LOW findings. These source-lane results are distinct from the
installed native host and the later documentation commits.

No warnings were reported in the installed 93-test summary. The corrected
standalone browser launch has no earlier launcher warning. Frontend development
dependency advisories and lower-severity image findings remain visible; a passing
browser or unit lane does not clear them.

### Actual local-model behavior

The temporary profile reused unsloth/Qwen3.8-27B-GGUF at the already configured
local Unsloth endpoint. No model weights were copied, replaced or downloaded.
Native Hermes Python 3.14.7, its real provider loader, normal startup checks,
selected-capture policy, eight-turn limit and 600-second run budget were
used. Reasoning was disabled as already configured; cloud fallbacks were empty.

| Scenario | Result | Time |
|---|---|---|
| Automatically capture a durable decision without an explicit save request | Passed; created version 1 | 330.09 s |
| Recall in a fresh session with the record cited/fetched | Passed; no mutation | 104.80 s |
| Apply an unambiguous correction | Passed; same record became version 2 | 107.18 s |
| Ambiguous contradictory information | Passed; clarification asked, no mutation | 161.86 s |
| Request to save an invented credential | Passed; no current/history mutation or credential memory | 142.93 s |

Canonical state was independently checked after each scenario, including encrypted
current/history payloads. Built-in memory notebooks were not used to mirror these
facts. Raw model conversation traces are private and are not included in Git.

This finite test is evidence of these scenarios, not universal secret detection
or qualification of every model. Capture required several searches and took over
five minutes. This route is suitable for further reviewed synthetic use, but
interactive performance and 41 simultaneous chat bots are not qualified.
The current model catalog did not advertise a context length; normal Hermes
guards remained enabled. The earlier 65,536-token host qualification is separate
evidence and is not reasserted solely from a model name or catalog response.

After the Qdrant authentication repair and full service restart, native Hermes
under the non-admin account recalled the corrected version through an actual
Qdrant query. The endpoint reported semantic retrieval and vector_index=queried,
rather than relying only on canonical fallback.

## Encrypted backups, restore and scheduling

The real backup service produced three completed generations in
/var/backups/enhanced-cognee. The directory is root-owned mode 0700; backup and
manifest files are mode 0600. All three signed manifests, ciphertext hashes and
age decryptions validated. No plaintext dump file was written. Keys were not
placed in that backup directory.

The first generation was restored into a fresh disposable database. Counts
matched its source snapshot: 18 records, 36 versions, 48 audit entries,
2 library memberships and 1 publication. Current and historical payloads
decrypted, project access denial and restricted-role denial passed, and a new
derived pipeline rebuilt semantic recall and source-linked graph evidence.
The failed fixture was resumed after the lease repair; no original database was
overwritten or deleted.

After qualification, the latest backup contains the later synthetic state.
Before/after service restart comparison covered 25 records, 56 versions,
68 audit entries, 2 memberships and 1 publication without changes.

The daily timer is enabled, active and persistent, with its normal 15-minute
random delay restored. An actual missed-run catch-up produced the second
generation. As last observed, its next run is 21 October 2026 at 00:03:33 BST;
the random delay means this is a snapshot, not a fixed minute every day.
The timer cannot run while WSL or the computer is off. No new cloud destination
or full Windows backup was launched.

Restore used the protected operator's existing keys. It does not establish that
Vincent has independent password-manager recovery copies; that remains an owner
confirmation. Existing generations and retained failed fixtures were preserved.

## Approved temporary-account cleanup

The newly created account cognee_test_20261020 (UID 1001) and its dedicated
/var/lib/enhanced-cognee-test-20261020 home were removed after all tests and a
post-restart native-provider check. No processes or nested mounts remained for
that UID. Useful evidence and one consistent synthetic state-database copy were
retained under protected operator storage before removal.

The temporary runtime reused 33,980 hardlinked public runtime/dependency files,
avoiding about 1.36 GB of duplicate file data. Their ownership/modes were not
changed. Cleanup removed only the approved account and dedicated home; sampled
original dependency inode/content and all 88 inventoried existing configuration
hashes were unchanged afterward. Shared models, original accounts, existing
profiles, protected services and all backup generations remain.

No non-admin test profile remains active. Removing that account does not convert
the existing administrator-owned bots into isolated production identities.

## Current phase disposition and remaining work

| Phase | This continuation completed | Still open |
|---|---|---|
| 0 - Preserve/baseline | Host evidence, originals, older stores/profiles and source retained | Owner classification/revocation of real exposed credentials; independent recovery custody |
| 1 - Access | Protected identities/credentials, direct negative store tests and actual non-admin OS checks | Actual intended operating boundary for everyday bots; retained legacy/provider surface has separate admission |
| 2 - Storage | Protected schema 3, persistent selected keys, real index worker/rebuild, encrypted restore and restart consistency | Only explicitly selected legacy/private migrations; these were not performed |
| 3 - Packaging/release | Native wheel repairs, hosted source tests, exact-image HIGH/CRITICAL gate and real SDK/browser | Unsuppressed frontend development advisories; complete exact-candidate hosted release review; no main merge |
| 4 - Hermes | Actual eight-tool provider and five local-model scenarios under non-admin account | Everyday profile review, model capacity/latency and staged bot rollout |
| 5 - Operations | Protected backup/restore, persistent timer/catch-up, restart and temporary-account cleanup | Independent owner custody/revocation, native Windows backup/DPAPI/Task Scheduler/cloud-chain recovery; private/everyday activation review |

Do not enable everyday/private memory while those admission prerequisites remain.
One maintained protected backend with scoped project/bot spaces remains the
recommended architecture. Reviewed common libraries and explicit grants can
share selected knowledge; unrestricted private cross-project access is not enabled.

Main retains five strict, trusted GitHub Actions checks with administrator
enforcement. The conditional merge approval does not permit bypassing unresolved
frontend findings, missing exact-revision checks or owner requirements.
Fresh documentation/reconciliation results should be recorded separately from
the tested source revision.

Machine-readable sanitized evidence:
[evidence/2026-10-20-protected-host-qualification.json](evidence/2026-10-20-protected-host-qualification.json).
Private artifacts remain in root-only operator storage. No credentials, model
conversation traces or existing private profile settings are published.

References:
- [Microsoft WSL configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- [systemd virtualization conditions](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#ConditionVirtualization=)
- [Successful hosted Required CI](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39483285556)
- [Successful hosted default-stack and image checks](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39481926570)
