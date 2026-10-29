# Enhanced Cognee: simple deployment plan and current authority

Evidence date: 2026-10-12.

## Plain-English answer

The integration project has not been rejected. Earlier connector versions had faults and remain preserved as historical evidence. The latest connector's scoped code repair passed independent review. It has not yet been installed and selected as memory for the running main Hermes profile.

The task counter contains planning, implementation, review and historical failed-version steps. Its 15 completed items out of 23 are not a percentage measure of a finished live integration. Historical failures must not be relabelled successful just to make the counter green.

## Recommendation

Proceed with a small local integration and test its actual usefulness. Do not run the full Enhanced Cognee service catalogue just because it exists. Existing results justify continued evaluation, but do not yet prove that the complete workflow is better than Hermes's built-in memory plus its session search.

## Owner authority now recorded

The owner requested completion of the remaining integration work and deployment as external memory, unless it is not worth the effort or creates substantial duplication/complexity. This authorises deployment preparation and a conditional main-profile deployment after the selected path passes its necessary checks.

The owner separately selected this exact first-live data scope:

> Your future one-to-one messages in the main Hermes profile only; no old chats, Brain import or shared-room capture

Therefore:

- Use the main/default Hermes profile only for initial live memory.
- Remember approved future direct-user message evidence locally, not old archived chats.
- Do not import the Brain, bulk files, private briefing or existing sessions.
- Do not capture shared rooms, other people, bot replies, assistant guesses, tool outputs or subagent/scheduled-run transcripts.
- Do not activate dormant bots or override earlier bot-isolation freezes. Prepare profile-compatible code and prove separation with synthetic test profiles; later rollout must respect their actual operating permissions and data policy.
- No paid services, cloud memory account, remote publication or unrelated spend.
- Preserve existing files, credentials, active sessions, earlier candidates and evidence. No bulk deletion or forced restart of the active chat.

## One clear job for each part

| Part | Job it keeps |
| --- | --- |
| Hermes | Run conversations/tools, manage bots/tasks, retain conversation history, essential built-in memory and reusable skills |
| Enhanced Cognee | Provide optional local meaning-based recall of approved user evidence, with source attribution |
| Existing Brain | Remain the current owner-editable knowledge library; no automatic rewrite or migration |

Do not add a second bot controller, task scheduler, conversation answer model, skill store or competing owner knowledge library. An external memory creates a derived searchable record of some information that also exists in Hermes history; that limited overlap is intentional. It is not permission to create a second authoritative transcript or mirror every built-in memory entry.

Keep one native connector, one external-memory selection per profile and a clear disable path. Keep memory storage and runtime under the authorised `.hermes` area. The memory store/search should be local; ordinary Hermes answers still use the AI provider already chosen for conversations, so this is not a promise that Hermes as a whole is offline.

## Work now underway

1. **Real installation and loading:** prepare the smallest self-contained directory provider, declare dependencies and test actual Hermes discovery/loading in disposable homes. Use Hermes's managed plugin dependency process, not ad-hoc pip injection into its selected environment. Do not treat direct test imports as proof of installation.
2. **Reliable memory operations:** exercise corrections/withdrawals, missing-answer behaviour, outages, complete stopped-writer backup/restore and resource cost with artificial data. Preserve failures and use separate calibration and evaluation questions rather than tuning to an already seen test.
3. **Deployment review and main-profile activation:** review the exact resulting artifact and installation changes, verify actual main Desktop/session scope and shared-room capture rejection, then configure only the authorised main profile. A working CLI-only test does not establish Desktop cross-session recall.
4. **Useful-work decision:** measure benefit against Hermes's complete baseline, not first-result ranking alone. If the smallest practical option is still too costly or complicated, report that directly instead of forcing activation.
5. **Remaining-task reconciliation:** retain every requested workstream, but distinguish an assessed alternative from an enabled feature. Broader database adapters/full-server features must not inherit this connector's acceptance. The library replacement assessment is not permission to migrate the Brain or build an unnecessary second interface.

No task will be closed merely because a command returned successfully or a worker reported it done. Installation, selection, fresh-session recall, privacy boundaries, failure handling and recovery need their own read-back/test evidence.

## Current read-back

The main profile's `memory.provider` is unset and `plugins.enabled` is empty in the inspected configuration. `enhanced-cognee.json` is absent. The existing `~/.hermes/enhanced-cognee` directory is present and must be preserved, not adopted or overwritten without checking its purpose. No live external-memory deployment is claimed by this report.

## Locations

Authorised implementation checkout:
`/home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes`

Accepted source candidate:
`integrations/hermes-request-validation-v1/`

New deployment candidate boundary:
`integrations/hermes-deployment-v1/`

New deployment evidence:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-deployment-2026-10-12/`

New operational helper/test boundary, if needed:
`src/hermes_memory/operations_v1.py`, `tests/hermes_operations_v1/`

Current repair acceptance report:
`docs/hermes-request-validation-phase-accepted-2026-10-12.md`

This document records the expanded current deployment request and selected live data scope. It does not declare the pending deployment tests passed or grant private bulk ingestion, dormant-fleet activation, cloud memory, Brain migration or uncontrolled feature rollout.
