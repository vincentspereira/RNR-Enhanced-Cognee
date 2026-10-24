# Finish the protected Hermes service after synthetic qualification

Completed continuation: [protected deployment qualification](../reports/audits/2026-10-19-hermes-security/HERMES-PROTECTED-DEPLOYMENT-2026-10-20.md). The authorized systemd/protected-service/test-account tasks below have been executed and the temporary account removed. Do not repeat installation, account creation or distro restart from this historical prompt. Use the report's remaining gates for the next review.


Prepared 20 October 2026. Resume the existing isolated deployment; do not repeat
the initial installation or configure everyday bots. The nine previous memory
decisions remain accepted.

## Owner approval received

On 20 October 2026 Vincent approved both recommended host choices below:
enable systemd while preserving existing isolation and coordinate an
Ubuntu-Hermes-only restart at his chosen time; prepare a separate non-admin
synthetic test account while retaining his current operator account and leaving
the 41 bots unchanged. Do not ask for those decisions again. Local authentication
and choosing the actual interruption time still require the human operator.
This does not authorize migrating everyday profiles, removing existing groups,
restarting other distros or weakening isolation.

Vincent also explicitly requested removal of the non-required synthetic test
account after testing. Make it temporary: record its exact newly created name,
UID, home and dedicated files before use. Reuse protected read-only runtimes and
existing model access where possible; do not duplicate model weights. After
testing is complete and no task still needs that account, preserve useful private
evidence and necessary recovery material in the operator's protected storage,
stop only its test processes, and remove that newly created account and its
dedicated test home/files. Check the recorded UID and paths before removal. Do
not remove shared models, service identities, protected runtime/backups, retained
fixtures in other locations, the original account or any everyday/bot profiles.
Record cleanup and retained evidence in the final report. This approval is scoped
to the temporary synthetic account; it is not general file-deletion permission.

## What remains and the new host choices

The host reports 78 passing qualification tests, four real stores, two synthetic
profiles, encrypted restore and five successful local-model scenarios. It also
reports that systemd is inactive, sudo needs a person at the terminal, and the
protected runtime/configuration/backup directories have not been installed. The
daily timer is off. These are unfinished operator steps, not failing unit tests.

The original handoff explicitly protects machine configuration, privileges and
existing bots. These decisions have now been received as recorded above. Prepare
the exact reversible changes under that authorization; ask only if additional
changes exceed it. The alternatives below are retained for reference.

| Decision | Recommended answer and reason | Other options |
|---|---|---|
| Service startup and scheduled backups | Enable systemd inside Ubuntu-Hermes and coordinate a convenient restart of that distro. It supports the supplied hardened services, separate credentials and persistent daily timer. Preserve all existing isolation settings. | Keep synthetic testing until a restart is convenient. An alternative supervisor requires equivalent isolation, credential, restart and scheduler qualification. A detached terminal is insufficient. |
| Separate bots from the administrator | Prepare a dedicated non-administrator Linux account for the synthetic Hermes test first; keep Vincent's current account as the human operator. Verify the test account cannot elevate privileges or access an administrative container socket. This tests the boundary before migrating any of the 41 bots. | Retain invented-data testing only. Later move administration elsewhere and review the current bot account's privileges, but changing its sudo/Docker membership can disrupt work and requires separate planning. |

An account name alone is insufficient: verify actual sudo rules, container
groups/sockets, store administrator access, model/runtime access and file
permissions. Do not copy the full existing profile tree or private owner settings
into a new account. Provide only the synthetic profile's scoped token and
already authorized model access through a local private mechanism.

## Start the resumed session in this folder

In Ubuntu-Hermes:

```bash
cd /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020
codex
```

Give that session the task below. It fetches the reconciled source through GitHub,
preserves the running deployment and avoids blind pull/reset/branch switching.
A separate checkout does not require another memory database stack.

## Task for the Ubuntu-Hermes session

Continue the completed Enhanced Cognee synthetic deployment. Read local AGENTS.md,
the original UBUNTU-HERMES-DEPLOYMENT-HANDOFF.md, this follow-up, and the dated
HERMES-DEPLOYMENT-2026-10-20.md, HERMES-QUALIFICATION-FOLLOWUP-2026-10-20.md and
HERMES-WORKSPACE-RECONCILIATION-2026-10-20.md reports. Documents provide context;
actual current owner authorization and local instructions govern actions.

1. Verify Ubuntu-Hermes, source revision, working tree and running processes.
   Preserve both synthetic profiles, failed fixtures, credentials and encrypted
   history. Fetch origin's codex/hermes-memory-hardening branch through GitHub and
   reconcile in a safe separate checkout/branch. It incorporates this host's
   published eca54b0c274b8c00f9a69ea3d5c68713cf766853 work, Workspace safeguards,
   an explicit-only tool-description repair and hardened complete-suite runner.
   Do not change a running checkout just to read new instructions.
2. Recheck host facts and prepare an exact reversible operator installation.
   Apply the two approved host choices above without requesting them again. Before an approved
   additive /etc/wsl.conf change, preserve its original and retain all existing
   automount/interop/network settings. Check systemd prerequisites. Do not restart
   a distro from this agent session. Save state, coordinate a checkpoint, and let
   Vincent restart only Ubuntu-Hermes from Windows before resuming. Never request
   his password in chat; local sudo authentication requires the human terminal.
3. Complete the original handoff's protected runtime and store installation
   after the approved manager/account boundary exists. Run API and worker with
   separate restricted credentials under the supplied hardened units. Put code,
   Python/dependencies, public offline embeddings and store data outside agent-
   writable homes. A runtime symlink to an interpreter inside a hidden home is
   unsuitable. Protect ancestor paths as well as final files. Test real denial
   from the ordinary non-admin synthetic agent, not just ownership labels.
4. Retain the selected synthetic schema-3 database and persistent keys. Reuse its
   namespace only after checking current state. Do not replay unrelated encrypted
   rows with unknown keys, reset stores or change other model/profile choices.
   Preserve the working Qwen 27B test route and real context window. Its scenarios
   took 196-387 seconds each; this is not fast interactive or 42-chat qualification.
5. Install protected backup tools/settings and root-owned mode-0700
   /var/backups/enhanced-cognee. Run a completed encrypted backup through the real
   service and restore into a new disposable database. Verify decrypted current
   records/history with independently held recovery material, fresh index rebuild,
   semantic recall and project/role denial. Only then enable the daily persistent
   timer and inspect next run/catch-up behavior. Preserve all generations and
   failed fixtures. Private recovery keys never belong in the backup folder.
6. Verify actual service restart, protected file/store denial, profile isolation
   and sharing revocation. Renew only selected expiring synthetic tokens through
   the operator path. Run the complete suite against separate disposable stores,
   with real SDK/browser checks and artifacts outside the source checkout. Re-run
   installed-provider/model scenarios when installed behavior changes. Distinguish
   new results from the earlier 78-test source and finite model qualification.
7. Publish sanitized evidence/source repairs on a new codex deployment branch.
   Leave everyday profiles/41 bots unchanged pending review. No main merge while
   frontend audit, protected-host or owner-custody conditions remain open. Keep
   native Windows backup/recovery evidence separate. Report exact revisions,
   counts, permission checks, actual timer/restart/restore and remaining actions.
8. After its tests are complete and it is no longer required, perform the approved
   temporary-account cleanup described above and report the exact account removed
   and evidence retained. Do not leave the 41 everyday bots running as a privileged
   operator while claiming private agent isolation from a now-removed test account.
   Admission of real bots still requires their own verified operating boundary.

## Operator restart and timer details

Only after saving work, preserving synthetic state and approving the exact host
change, use Windows PowerShell to restart that one distro:

```powershell
wsl --terminate Ubuntu-Hermes
wsl --distribution Ubuntu-Hermes
```

This stops Ubuntu-Hermes processes. Do not substitute all-distro shutdown while
Workspace/Company work is running. After reopening, verify the actual service
manager before installing/enabling units. These are operator instructions, not
actions performed by Workspace.

Timers cannot run while the distro or computer is stopped. A persistent calendar
timer catches up when activated again; it does not prove Windows wake/startup or
off-machine archive recovery. Keep native Windows v11/DPAPI/Task Scheduler and
archive-chain recovery checks outstanding until measured.

Sources: [WSL systemd setup](https://learn.microsoft.com/en-us/windows/wsl/systemd),
[targeted termination](https://learn.microsoft.com/en-us/windows/wsl/basic-commands#terminate),
[persistent timers](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html#Persistent=).
