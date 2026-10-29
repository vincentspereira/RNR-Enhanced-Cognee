# Enhanced Cognee: authorised chat-switch safety phase

Recorded on 2026-10-12 following the owner's explicit reply:

> Approve the scoped chat-switch safety phase.

This approves the bounded phase in `docs/hermes-bridge-freeze-and-owner-decision-2026-10-12.md`, section `Decision needed`. It does not erase the rejected candidate or grant live activation.

## Scope

- Preserve the rejected bridge at `integrations/hermes/` unchanged, including its provider SHA-256 `0b4778e7530dee07f531195917cfbc679e20178b424a50d6414c80dd95a6546f` and historical failure evidence.
- Prepare the separate versioned candidate at `integrations/hermes-chat-switch-safety-v1/` on the existing authorised task branch `hermes/enhanced-cognee-native-memory-20261012`.
- Change only the candidate bridge's chat-state handling and necessary tests/documentation. Use existing runtime, dependencies, local model and synthetic fixtures.
- Reproduce the exact previous failure first. Replay the same test bytes against the candidate with explicit import/output rebinding recorded; do not alter the failure or positive-control expectations.
- Make snapshotting chat identity/change state and validating/publishing recall internally consistent across concurrent switches. Keep model/database work outside any short-lived chat-state lock so a slow lookup does not block switching.
- Retain correct keyed-chat/profile boundaries, delayed-job source/author provenance, bounded untrusted recall, default-off capture, no built-in memory mirroring, and truthful timeout/busy/shutdown limitations.
- Require fresh independent review with additional timing/interleaving checks. Passing old tests does not establish acceptance over a new reproduced defect.

## Not authorised

No installation or dependency changes, Hermes core edits, live configuration/profile/bot activation, private data or Brain ingestion/migration, services, external processing, spending, commit/push, or promotion over the frozen bridge.

## Evidence and completion

New phase evidence:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/chat-switch-safety-phase-v1/`

Preserve original hashes, versioned RED/GREEN candidates, exact executed tests, source manifests, review verdict and parent replay. Record safety acceptance separately from remaining deployment, value and library-replacement gates.

This phase permits one scoped implementation and a fresh independent review. If review finds another blocker or a fix would exceed this scope, preserve and freeze the candidate, report the exact issue and ask for a new decision rather than automatically restarting repair cycles.

Preflight verified the existing task branch and all 150 entries in the frozen final bridge manifest. No repository instruction files were found in the checked parent/root/integration locations. The new candidate path did not exist before this phase.
