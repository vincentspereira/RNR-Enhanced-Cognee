# Enhanced Cognee: authorised request-validation repair phase

Recorded on 2026-10-12 following the owner's explicit reply:

> Approve the scoped request-validation repair phase

This authorises the proposed bounded repair in `docs/hermes-chat-switch-safety-phase-final-result-2026-10-12.md`, section `Next owner decision`. It does not unfreeze, promote or activate either rejected bridge.

## Allowed work

- Preserve `integrations/hermes/` and `integrations/hermes-chat-switch-safety-v1/`, all historical evidence and the exact independent failure tests unchanged.
- Create a separately versioned candidate at `integrations/hermes-request-validation-v1/` in `/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes`, on existing task branch `hermes/enhanced-cognee-native-memory-20261012`.
- Copy the last candidate byte-identically before editing. Limit changes to the candidate bridge's request admission, necessary tests and documentation.
- Validate a lookup's active known session before changing current request ownership, clearing indicators or altering recall diagnostics. Reject old/unknown calls without affecting a valid published or pending current result. Retain atomic snapshot/publication and short state locks; do not hold state locks during model/database work.
- Reproduce the four preserved failures before production changes. Replay unchanged failure and positive controls after the minimal fix; keep session-switch, superseding-request, shutdown, delayed-write, scope and source attribution checks.
- Explicitly document and reconcile only copied legacy assertions that contradict the new rejection contract. Preserve their original bytes; do not skip tests or weaken safety/identity assertions.
- Require a fresh independent review and parent verification against exact source/test hashes.

## Stop condition

One scoped implementation followed by fresh independent review is authorised. Freeze and escalate a remaining blocking finding or work outside this boundary; do not start another automatic repair loop or rename a new candidate to bypass the stop condition.

## Excluded work

No edits to Hermes core, existing runtime/database adapters/library, dependencies, live profiles or configurations. No private conversation/Brain ingestion or migration, services, external model processing, package installation, source promotion, live activation, spending, commit or push.

## Evidence boundary

New phase evidence:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/request-validation-phase-v1/`

Use synthetic homes under the authorised Hermes scratch directory and existing model/runtime. Run actual model/storage tests with networking denied. Record actual provider import path/hash, literal test commands, separate setup failures and baseline limits, before/after preservation manifests and independent verdict.

## Preflight

The current task branch was verified. All 10 last-candidate files and 152 protected existing files matched their recorded hashes and sizes. The new candidate path did not exist. The rejected starting provider remains:
`3e3fe9282af38fabde5b86aab3d1af4a318bce77d99d78480433d514c4f6d6d7`

This approval does not establish full installation, host prompt-dispatch safety, operational recovery, overall benefit, fleet readiness or Brain replacement.
