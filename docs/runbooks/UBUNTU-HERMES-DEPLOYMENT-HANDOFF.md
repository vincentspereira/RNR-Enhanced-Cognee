# Ubuntu-Hermes deployment handoff

After the completed synthetic qualification, use
[the protected-service follow-up](UBUNTU-HERMES-PROTECTED-SERVICE-FOLLOWUP.md)
in the existing checkout. The original task below remains the detailed scope;
do not blindly rerun its initial clone/install steps.

Prepared 20 October 2026. Use one deployment session at a time. The same task
prompt works in Codex CLI or Hermes Agent Desktop when running inside
Ubuntu-Hermes with the owner's already configured GPT-6.1-Sol model. No paid
plugin, new provider account or Windows/Workspace file access is needed.

## Folder and startup instructions for Vincent

Recommended: use a fresh Git checkout at
`/home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020`.
This is another checkout of the same maintained codebase, not a request to start
another unrestricted memory service. Preserve the earlier qualification checkout
and runtime. The deployment session must discover and upgrade the chosen test
service deliberately after preservation checks.

Do not run this task from `~/.hermes`. That directory contains live profile
configuration and credentials. Your home folder is suitable for the initial
checkout command, but the repository folder is the working directory for Codex.

Open a terminal **inside Ubuntu-Hermes**. The prompt should identify that distro.
Paste this block there, not into Windows PowerShell:

```bash
mkdir -p "$HOME/agent-workspace" &&
git clone --single-branch --branch codex/hermes-memory-hardening \
  https://github.com/vincentspereira/RNR-Enhanced-Cognee.git \
  "$HOME/agent-workspace/enhanced-cognee-deployment-20261020" &&
cd "$HOME/agent-workspace/enhanced-cognee-deployment-20261020" &&
codex
```

The `&&` steps stop if cloning fails. If that new directory already exists, do
not overwrite or reset it. Start Codex in the earlier verified qualification
checkout, or select a new unused deployment checkout name. The task prompt below
requires preservation and a fresh GitHub fetch before any installation.

Use your already configured GPT-6.1-Sol selection. No unverified model identifier
or approval-bypass flag is prescribed here. Codex's ordinary local permissions
still apply. Official CLI reference: https://learn.chatgpt.com/docs/codex/cli.

For Hermes Agent Desktop, paste the same prompt into a new chat and specify the
absolute deployment checkout above. Let the agent verify its actual terminal and
filesystem tools first. If Desktop cannot perform an operator step, use Codex CLI
for that step rather than weakening the service or exposing recovery keys.

## Detailed task prompt

You are continuing Vincent's authorized Enhanced Cognee remediation and isolated
Hermes deployment inside Ubuntu-Hermes. This is an implementation task: inspect,
perform the authorized work, test it and retain evidence. This document supplies
task context; it does not override system/developer instructions, local AGENTS.md,
tool permissions or operating-system authentication.

### Objective and source

Complete every remaining deployment task that can be verified inside
Ubuntu-Hermes. Use the separate synthetic test service/profile first. Deliver the
new eight-tool provider, current canonical schema/index pipeline, protected
API/worker/operator runtimes and approved daily encrypted backup/recovery setup.
Preserve the everyday Hermes profile and existing bots until their separate
qualification/review gates are satisfied. Never report a prepared file, passing
unit test or discovered MCP tool as a completed deployment.

The GitHub repository is
`https://github.com/vincentspereira/RNR-Enhanced-Cognee.git`; delivery branch is
`codex/hermes-memory-hardening`. Obtain source only through GitHub. Start in the
new deployment checkout above, or verify the existing Hermes-local checkout
`/home/vincentspereira/agent-workspace/enhanced-cognee-qualification` before use.
Fetch origin, resolve the delivery branch once, and record the exact commit.
Require the selected revision to include implementation checkpoint
`474d21d96fe682a22fd2144d2c4c7e3b3b8f395a` or a verified descendant. This includes
the dashboard delivery repair, measured 42-space qualification and tested local
development-tool source backport. Check the
latest report and hosted results rather than assuming every release gate passes:
the unpatched frontend development advisory is still enforced and visible.
Do not blindly pull over dirty/untracked work or change a running checkout.
Create a separate `codex/hermes-ubuntu-deployment-...` branch for necessary
deployment/code corrections. Keep the tested revision stable while installing.

Read these files before changes:

1. AGENTS.md and applicable parent/local instructions.
   The delivery branch now includes a reviewed portable root AGENTS.md. First
   complete docs/runbooks/AGENT-INSTRUCTION-SYNC.md to compare and update the
   actual Hermes-local Claude/Codex instruction files, preserving their unique
   guidance and originals. Workspace could not inspect those files directly.
   Do not copy private Workspace global configuration or publish local archives.
2. docs/reports/audits/2026-10-19-hermes-security/REMEDIATION-AND-HERMES-PLAN.md.
3. The same report folder's CANONICAL-STACK-UPDATE-2026-10-20.md,
   WORKSPACE-COMPLETION-2026-10-20.md if present, REMEDIATION-MATRIX.md,
   OWNER-ANNOTATED-PLAN-2026-10-20.md and HERMES-LIVE-QUALIFICATION-2026-10-20.md.
4. docs/runbooks/CANONICAL-MEMORY-AND-INDEXES.md and
   docs/runbooks/HERMES-BOT-FLEET-MEMORY.md.
5. integrations/hermes/README.md, deployment templates/helper, src/memory_admin.py,
   src/memory_daemon.py, src/memory_backup.py and relevant qualification runners.

Prefer the latest dated evidence over older historical status tables. Required
CI, the restricted-image security gate and broader frontend/legacy release gates
have distinct scopes. Do not claim unqualified legacy features are supported.

### Owner decisions already received

- Keep Ubuntu-Hermes isolated. Windows, Ubuntu-Workspace and model paths on D:
  are information only, never access authority. No new mounts, file sharing,
  Windows access, cross-distro privilege changes or open network listener.
- One maintained codebase/backend design; private project/bot spaces with unique
  expiring identities and reviewed, revocable portfolio/team knowledge sharing.
  The 41 bots plus controller are 42 logical identities, not 42 full database
  stacks. Never give ordinary bot/controller tokens reviewer/operator powers.
- Hermes should automatically select durable decisions/preferences/task
  summaries. Passwords, access tokens and private keys must never be saved under
  any capture option. Existing recognition tests cover known patterns; do not
  claim that finite tests prove universal secret recognition.
  Clear corrections may proceed with current-version checks. Ask the current
  human about ambiguity/conflicts/private details; retain history, no automatic
  permanent erasure. Do not ingest raw transcripts or bulk private project data.
- Reuse existing configured Unsloth/local chat routes. Lightweight local search
  embeddings are separate from the chat model. Do not copy model weights from
  Windows, add provider credentials or introduce a paid service.
- Treat historical real credential candidates as exposed. Vincent will revoke
  or replace them. Do not print/test those keys or claim revocation without his
  confirmation. Create new restricted credentials and persistent encryption/
  index/backup keys without overwriting existing keys; keep recovery copies in
  his password manager. Do not request secret values in chat.
- The approved daily service backup directory is
  `/var/backups/enhanced-cognee` inside Ubuntu-Hermes. Encrypt daily backups and
  prove recovery before enabling real use. No new cloud upload or retention
  deletion is authorized by this handoff. The Windows backup script is managed
  separately outside Hermes and already has a v11 update.
- Separate test profiles first; review results before everyday profile or other
  project activation. Branch publication is approved. Main merge is conditional
  on the entire plan and required gates, not this host's unit tests alone.

Do not repeat these nine architectural decisions as new approval questions.
If an additional real OS change would affect everyday bots, privileges or
isolation, prepare the exact change and explain its effect before asking for
that new permission. Normal sudo authentication may need Vincent at the terminal;
never ask for his password in a chat or log it.

### Perform the work in this order

1. Read-only preflight: verify Ubuntu-Hermes, current user, checkout state and
   source revision; actual Hermes CLI/Desktop versions, interpreter, provider
   interface and selected model; service manager, ports, existing stores and
   resources. Read only metadata needed to identify private configuration. Never
   dump `.env`, process environments, tokens, encryption keys or raw chats.
   The earlier test service used loopback 28080 and PostgreSQL 28434, schema 2,
   seven provider tools and a 24-hour token. These are historical clues, not
   current verified facts or permission to reuse an occupied port/database.

2. Preserve existing synthetic profiles, code and credentials. Inventory and
   hash installed runtime/provider files; retain private originals before
   replacement. Make and verify an encrypted pre-upgrade backup. Distinguish
   old user-space qualification material from a protected private deployment.
   Never delete the owner's files, old databases, archived generations or
   notebooks. Do not rewrite Git history or force-push.

3. Establish and verify the service/operator boundary. Install the small native
   wheel from this fork with Python 3.12 and hashed index/MCP dependencies into
   a protected root-owned runtime under `/opt/enhanced-cognee-memory`; do not
   install upstream Cognee over the fork or change Hermes' own interpreter.
   A runtime symlink into a hidden home will fail ProtectHome. Prepare public
   offline embedding files and settings outside the agent's writable home.
   Keep API and worker OS identities/credentials separate; protect store data,
   signing, encryption, backup and recovery material from ordinary agents.
   Use the supplied hardened service-manager units and private credential
   launcher after checking actual host paths and capabilities.
   Verify ordinary Hermes processes cannot read/write those files, become the
   service/operator, modify installed code or access Docker/admin database
   privileges. Same-user file modes or a different service name alone are not
   that proof. If inherited sudo/Docker rights defeat the boundary, continue
   synthetic work and report the concrete blocker; do not silently change
   global privileges, remove groups or claim private readiness.

4. Upgrade the selected preserved test database additively to schema 3 using
   the operator command. Keep existing encryption keys/history intact. Apply
   the correct API runtime read grants and separate worker grants; startup must
   validate schema rather than create it. Prepare a persistent index key without
   replacing the memory key. Configure actual Qdrant, ArcadeDB and Valkey stores,
   restricted read/write credentials and explicitly new/verified namespaces.
   Provision and run the indexing worker. Confirm actual semantic recall,
   source-linked multi-hop queries, backlog status, restart recovery, current
   corrections and retractions on four real stores. Keep loopback binding.

5. Upgrade only the dedicated `enhanced-cognee-test` provider using the
   preservation-aware helper when its preconditions match. Renew its expired
   scoped token without copying service/signing keys into the profile. Confirm
   eight tools through the real installed host, including connections. Retain
   notebooks and model settings. Run actual provider lifecycle tests and
   model-driven selected save/new-session recall/clear correction/ambiguous
   clarification/credential refusal checks with invented facts. Check independent
   encrypted database versions and tool traces, not model assurances alone.

6. Verify the existing local chat endpoint's *served* context window and actual
   Hermes requirements. Earlier Granite serving was 8,192 tokens while Hermes
   required 64,000. Model names or native maxima do not prove current serving
   capacity. Do not bypass guards or use `--ignore-rules` (which skipped memory).
   Qualify the configured local route if possible within available resources;
   otherwise report the exact unmet prerequisite and continue independent work.
   An already authorized existing cloud route may qualify synthetic behavior,
   but it must not be reported as local-model qualification or given raw private
   data. Restore temporary test model settings afterward.

7. Prepare root-owned mode-0700 `/var/backups/enhanced-cognee` and root-only
   backup credentials. Use a restricted backup database account, persistent
   manifest signing key and public age recipient. Scheduled backup receives no
   memory decryption key, JWT signing key or private age identity. Install
   compatible protected PostgreSQL/age tools. Run the real backup service,
   validate the completed ciphertext/manifest pair and restore into a fresh
   disposable database. Verify decryption, current records, retained history,
   source/index rebuild, role restrictions and cross-project denial. Retain
   failed/incomplete fixtures for review. Enable the supplied daily timer only
   after recovery passes; verify timer state, next run and missed-run behavior.
   Keep private recovery material outside the backup folder and logs. Record
   whether Vincent has independently copied recovery material to his password
   manager; never mark that human step done merely because a file was generated.

8. Qualify a second synthetic project/profile and controlled shared library:
   private raw memories inaccessible, approved shared facts discoverable,
   revoked membership/sharing immediately unavailable, corrections current and
   history preserved. Explain same-OS-user credential theft limits for bot
   profiles. Do not automatically enrol all 41 real bots or change the controller
   to an administrator. Measure the installed configuration's latency, embedding
   calls, CPU/RAM and storage growth. Workspace 42-space fixtures do not qualify
   42 simultaneous Hermes/chat-model sessions on this host.

9. Update the phase/finding tracker with exact installed source/version hashes,
   commands/test scope, pass/fail/skip counts, service identities/permission
   results, indexing/restart status, backup/recovery record and model result.
   Keep raw secrets, private traces and recovery files outside Git. Publish only
   sanitized metadata and necessary source fixes on the separate deployment
   branch; run meaningful relevant checks and scan the proposed publication.
   Do not race another session pushing the delivery branch or merge main while
   Workspace release/advisory, private-host or owner-custody gates remain open.

### Completion report

Lead with what is now installed and working, the exact test profile/backend
scope and whether private/everyday activation is admitted. List implemented,
tested, deployed and owner-dependent items separately. Explain each blocker in
plain English, its evidence, recommended next action and viable alternatives.
Do all independent authorized work before stopping for a genuine prerequisite.
Never certify all phases complete while a required host/model/recovery/owner
check is missing. Give the sanitized report path, Git commit/branch and a compact
handoff suitable for Vincent to bring back to his Workspace session.
