# Claude/Codex instruction reconciliation and remaining work

Date: 20 October 2026. This is an instruction-delivery update, not private-host
deployment or release acceptance. Main remains unmerged.

## Completed in this session

- Compared the Ubuntu-Workspace Linux-global Claude instructions, Projects-level
  Claude catalog and Enhanced Cognee Claude file with their Codex counterparts.
- Updated the Workspace Linux-global and Projects-level Codex instruction files,
  preserving their previous guidance. Updated the Desktop global Codex file with
  the same applicable reconciliation so both Workspace entry points carry it.
- Preserved seven original instruction sources and their SHA-256 manifest in a
  private ignored archive. All three compared Claude source files are unchanged.
  Existing non-ASCII glyphs in the three personal/workspace Codex files were
  escaped rather than silently removed. New guidance is ASCII-only.
- Replaced the long, outdated repository Codex instructions with reviewed portable
  guidance. Original content remains archived. The new root file distinguishes
  canonical restricted memory from the larger legacy surface, records the current
  owner decisions and keeps installed-host/private-activation checks explicit.
- Added a root-only Git ignore exception for AGENTS.md. It now travels with this
  branch's code. Personal/global files, nested local instruction files, Claude
  sources, archives and private owner annotations remain excluded.
- Updated the deployment handoff to reconcile actual Hermes-local instructions
  before service/profile changes. The detailed procedure is in
  [AGENT-INSTRUCTION-SYNC.md](../../../runbooks/AGENT-INSTRUCTION-SYNC.md).

## Guidance transferred or clarified

| Area | Result |
|---|---|
| Working agreements | Plain-language recommendations, reasons/alternatives, preservation, existing authorization and honest qualification boundaries |
| Machine setup | Actual environment/tool verification; native Linux npm; old shared-configuration claims treated as historical rather than current facts |
| Catalog | Current local Spatial/Studio compatibility links, current gateway/strategy/Blender locations and explicit reading of relevant local catalog guidance |
| Media/design | Existing Studio/Blender pipelines and Open Design/shadcn options, conditional on relevance, availability and authorization |
| Typed judgement | Existing TypeSafe/Jev intent retained; narrow typed questions, reviewable thresholds, deterministic work in code and hosted-route privacy |
| Graph navigation | Existing dated graph/wiki navigation and available local AST-only refresh, without installing a paid extraction tool |
| Memory/deployment | Selected capture, secret exclusion, clarification/version history, approved sharing, separate identities, persistent keys, encrypted recovery and test-profile-first deployment |
| Instruction delivery | Portable root AGENTS.md through GitHub; private global instructions stay local; override precedence and instruction-size limits checked |

The measured Linux-global plus repository instruction content is 32,030 bytes
including a separator, below Codex's documented default 32 KiB limit. An actual
Hermes session must measure its own configured chain; its global instructions
and overrides are not known here. No Codex configuration/size limit was changed.

## Verification scope

Verified original/archive hashes, preservation of all existing instructions in
the three appended personal/workspace files, unchanged Claude source bytes,
ASCII encoding, relative documentation links, Git exclusions and whitespace.
The six proposed publication files also passed a redacted Gitleaks scan with
zero detected secrets; private instruction sources/archives were not published.
These are documentation/ignore changes; runtime source and service configuration
were not changed, so the full unit/browser/store suites were not repeated.
The previous dated runtime evidence retains its original scope.

## Work that remains outside this session

- Ubuntu-Hermes: read and reconcile its real instruction files, preserving unique
  local rules and originals; qualify the installed provider/schema/index/OS/model
  and service backup/recovery/timer. The WSL Windows launcher still returns an
  executable-format error here; no interop/mount/firewall change was attempted.
- Windows: run v11 under native Windows PowerShell/DPAPI, verify scheduled-task
  paths and the real encrypted backup/recovery chain. Source-level checks cannot
  certify these installed Windows behaviors.
- Owner: confirm actual exposed credentials revoked/replaced and recovery copies
  retained privately; review qualification before everyday/other-project activation.
- Frontend security: GitHub's current GHSA-vfj7-8cjw-p6xm advisory still lists no
  patched version, and the official npm registry still reports braces 3.0.3 as
  latest. The tested depth backport remains a mitigation, not a cleared audit.
  Full audit gates stay enforced. No unsafe downgrade or suppression was added.
- Separately selected legacy/providers: choose and qualify the needed actual
  configuration before admitting it. No blanket support or production claim.

The general source documentation and instruction delivery work can be completed
here. The host/owner tasks above cannot honestly be marked complete from this
Workspace session. No file deletion, paid installation, private import, everyday
activation, cloud upload or main merge was performed.
