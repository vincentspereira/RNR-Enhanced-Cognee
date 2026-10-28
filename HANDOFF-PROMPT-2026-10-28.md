# Enhanced Cognee system-wide launch handoff

Copy the prompt below into the next model. It describes the current verified state and the immediate next action. Do not include passwords, tokens, private keys, profile contents, decrypted credential exports, or raw private conversations in the handoff.

---

You are continuing the authorized Enhanced Cognee system-wide launch work inside Ubuntu-Hermes. The owner is preparing a 40-bot fleet in parallel and explicitly reported that no bots have started. Preserve that concurrent preparation. Do not activate bots, change their launchers, enable production admission/renewal, switch the fleet, merge to main, or start services unless the documented gates and applicable owner approval are satisfied.

## Instructions and preservation

1. First read the applicable `AGENTS.md` instructions, the repository `AGENTS.md`, `docs/runbooks/HERMES-SYSTEM-WIDE-LAUNCH-CONTINUATION.md`, `docs/runbooks/UBUNTU-HERMES-DEPLOYMENT-HANDOFF.md`, `docs/runbooks/AGENT-INSTRUCTION-SYNC.md`, `docs/runbooks/HERMES-MANAGED-MCP-RUNTIME.md`, and the latest sanitized receipts listed below. Reconcile local Hermes instructions as documented; do not require a Workspace file.
2. Verify distro, user, working directory, branch, checkout status, source revision, and current host state before action. This is an Ubuntu-Hermes isolated environment. Do not access Windows/other-distro paths, add mounts, or copy secrets across environments.
3. Preserve all dirty/untracked work, archives, evidence, candidates, backups, and concurrent bot-fleet preparation. Never reset/clean/delete, overwrite prior evidence, or replay a completed qualification. The project authorizes delivery-branch publication; main merge remains conditional on its checks. Do not claim changes are committed/published unless verified.
4. Keep all output ASCII-only and sanitized. Never read, print, ask for, or place passwords, tokens, signing/recovery keys, decrypted custody data, or private profile contents in prompts, logs, reports, memory, or version control. Sudo authentication is terminal-specific; tell the owner to type credentials only at their Ubuntu-Hermes terminal prompt.
5. Do not ask the owner again about decisions already recorded. The KeePassXC custody step is complete: the owner verified the saved encrypted attachment hash against `6951FD09ED6DCCEA2A3FC53F1D8F90861E8776C4A3663397091FF3E7327D4322`. Never request decrypted contents.

## Verified checkout/source state at handoff

- Worktree: `/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024`
- Branch: `codex/hermes-ubuntu-deployment-launch-20261024`
- HEAD: `154fadfddc76653a6bea9754068cd245adf20a86`
- Required delivery source revision already fetched and verified: `21abf4857ca8dce8e0a3aafc725266c8d3754529`.
- Worktree is intentionally dirty with modifications and new files for the in-progress rollout. `git status --short --branch` listed modified launch reports/runbooks plus new sanitized receipts, a managed-MCP runbook, Fetch candidate source/lock, installer/build/probe/seal/qualification helpers, and a focused qualification test file. Preserve all.
- Earlier staging was blocked because the linked Git worktree metadata path `.git/worktrees/launch-worktree-20261024/index.lock` is on a read-only filesystem in that session. Nothing was staged by that attempt. Do not assume or report staged/committed changes. Continue reversible workspace work; if publication becomes necessary, inspect the exact error and use only an approved, safe route without disturbing the worktree.
- Four relevant delivery CI workflows had succeeded (run IDs `40055830507`, `40055830334`, `40055830340`, `40055830325`); broader CI runs `40055830266` and `40055830273` had failures. These are historical checks: inspect current results before claiming current CI is green. No claim that the new managed-MCP helpers have hosted CI coverage.

## Current verified implementation/qualification results

- Enhanced Cognee revision `21abf4857ca8dce8e0a3aafc725266c8d3754529` was staged as an isolated candidate, its exact wheel/hashed dependencies and model verified, and the controlled service runtime switch passed. Canonical encrypted recovery and actual derived-store recovery passed. Installed worker projection passed after credential rotation and retirement. All fleet admission policies have remained disabled.
- Native current-model capture and fresh-process recall passed (`model-recall-finish-fdu97vca`), but maximum context was not verified. Do not claim it was.
- Actual Java/Ghidra program qualification passed, including Java version and Ghidra headless import (`rea-owner-receipt-finish-zy8t6r38`). Actual main-account filesystem MCP qualification passed, and REA's 207-tool catalogue passed under the actual restricted main UID. The completed component receipt is `docs/reports/audits/2026-10-19-hermes-security/2026-10-28-main-local-mcp-components-pass.json`.
- The exact prior native qualification test ID `5d0e9a49bdf544359ae6deff` was already completed and retracted with history preserved. Never replay it. Also reuse, do not replay, other passed capture/share/withdrawal and installed-worker evidence recorded in current runbooks/reports.
- All 40 named candidate profiles passed the latest qualification batch (40/40) and renewal/recovery probes. Daily encrypted fleet backups for 41 profiles were installed and scheduled after a root-identity boundary repair; the scheduled backup qualification passed. Isolated transport and durable delivery recovery also passed. These candidate/backup results do not mean live bot profiles were activated.
- Current main candidate configuration and MCP definitions were reconciled and recovered into an inactive candidate; six MCP definitions were preserved. The latest main local MCP component pass covers filesystem and REA catalogue only. It does not establish all actual MCP servers, full Hermes tool/program coverage, provider connectivity, maximum-context capture, or fleet production dispatch.
- Public Fetch MCP candidate work is prepared in a separate, owner-safe candidate. A frozen lock for Fetch `2026.10.24` was verified; the prepared Fetch candidate had isolated stdio initialize/catalogue/network-boundary proof and sanitized package findings. Its HTML content extraction did not pass its expected-content check. Do not represent HTML extraction or the actual main-profile Fetch integration as qualified.
- The new sealed managed package-manager runtime payload is 464,097,280 bytes with SHA256 `68a0325fec51b2922b379cec51b8d80a202f2e7783e3c8561154d8a9eb52f521`. It contains 5,005 admitted archive members. The disposable restore and ordinary-user proof passed after preserving an initial failure and reusing the restore. The protected live installer has not yet been run. It is designed to stage only the isolated PM runtime and update protected runtime facts; it must not change bots, profiles, services, source configuration, credentials, policy, or backend services.
- Latest sanitized managed runtime receipt: `docs/reports/audits/2026-10-19-hermes-security/2026-10-28-managed-mcp-runtime-preparation.json`.
- Installer runbook: `docs/runbooks/HERMES-MANAGED-MCP-RUNTIME.md`.

## Immediate next action: protected owner-terminal install

The local agent's noninteractive `sudo -n` cannot use the owner's terminal-specific sudo timestamp. In the Ubuntu-Hermes terminal, the owner should run exactly this prepared command, enter the password only at the local sudo prompt, and return only its final JSON summary (not the password):

```bash
sudo /usr/bin/python3 -I /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment/install_managed_mcp_runtime.py
```

Before asking the owner to run it, read the installer and its runbook and verify current source/helper/artifact hashes against the sanitized preparation receipt and live protected preflight. The public/local prep previously verified the current Hermes release, runtime facts, source hashes and payload hash; rerun only the read-only current preflight if freshness is uncertain. The installer is explicitly idempotent on a completed verified receipt and must refuse partial/changed state instead of automatic retry. Do not make it run as the ordinary user if it requires root. Do not run services or MCP servers as part of this step. Summarize the JSON without secrets and continue only from verified checkpoints.

## Remaining gates after this step

Work in the order documented by the continuation runbook and launch control. Reuse completed evidence; preserve failed attempts and inspect before any effectful continuation.

1. Verify the protected PM-runtime installation receipt and protected post-install runtime facts. If any hash, identity, or state check fails, stop and inspect; do not retry or edit protected files blindly.
2. Finish actual main-profile MCP integration qualifications. Maintain the six retained MCP definitions. Complete Fetch in a controlled isolated candidate and fix/qualify the HTML extraction behavior before claiming it works. Qualify required local/external MCPs only when the documented network/data boundary permits. No platform adapters or external sends unless an explicit qualified test requires them.
3. Complete full actual Hermes main-profile tool/program coverage, route/context/capture verification, and any still-open REA, recovery, credential-issuer, and installed native gateway admission predicates. Clearly distinguish candidate and synthetic results from actual installed main-profile results. Maximum model context remains unverified unless a new valid evidence receipt proves it.
4. Establish pinned profile-to-launcher identity bindings for live Hermes launch processes. Earlier inspection found two candidates without profile binding and no pinned executable matches; later isolated/candidate qualifications do not establish live production bindings. Re-inspect the current actual process state because the owner is preparing fleet setup concurrently. Do not activate/start any bots; the owner reported none are started.
5. Confirm current main-profile backup/recovery membership and rollback plan, and recheck the installed daily fleet backup schedule. Retain all existing encrypted generations and custody evidence.
6. Keep all fleet admission/renewal policies disabled until each applicable gate is verified. Prepare the final fleet switch for review only after a fresh gate audit; do not switch/activate the 40-bot fleet without the documented final review/approval. Do not merge main until agreed checks pass.
7. Check current CI statuses and run only necessary checks for changed files when authorized/appropriate. Past CI results are not current. Do not repeat passing expensive qualification or test `5d0e9a49bdf544359ae6deff`.

## Reporting requirements

For each step report: exact source revision and environment, command/action, evidence path or sanitized receipt, verified pass/fail, effects on services/profiles/credentials/data, and the next blocker. Do not expose secrets. Keep "implementation complete," "candidate qualified," "installed main-profile qualified," "fleet switch prepared," "fleet activated," and "production accepted" as separate states. At this handoff, the fleet is NOT launch-approved and no bots are confirmed started.

---

End of prompt.
