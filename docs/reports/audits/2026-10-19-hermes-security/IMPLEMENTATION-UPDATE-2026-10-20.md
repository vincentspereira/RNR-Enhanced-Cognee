# Implementation update - 20 October 2026

The owner's decisions have been incorporated. The detailed owner response remains
local. This document contains the generic implementation policy and qualification
status suitable for the repository. Full remediation is still in progress.
See [live Hermes qualification](HERMES-LIVE-QUALIFICATION-2026-10-20.md) for the
later isolated installation, full-chat results, native recovery fixes and exact
remaining release requirements.

## Implemented in this continuation

- Selected capture through Hermes' normal model/tool loop: durable decisions,
  preferences and task summaries can be saved without an explicit remember
  request. This reuses Hermes' configured local-model connection. No Windows model
  directory is mounted and no separate hosted extraction pipeline is started.
- A clarification tool marks uncertain changes; pending corrections require a
  quote present in the current human reply. Bot-authored turns cannot authorize
  writes. Clear corrections retain owner/version checks and correction history.
- Always-on credential-pattern rejection for new canonical writes and old-record
  reads, independent of optional PII settings. Selected-capture credentials also
  reject recognized private details pending a sanitized summary/clarification.
  Pattern matching and agent judgment do not guarantee recognition of every
  disguised secret or personal detail.
- Optional stable fact keys prevent conflicting fresh records for one topic.
  Retraction/expiry can release a key without reactivating or deleting old records.
- Reviewed library groups let approved projects search common knowledge. Group
  membership alone does not expose raw project memories. Publications name the
  current reviewed version; correction/retraction/source removal revoke access.
  Shared results omit internal actor/session metadata. Sensitive summaries require
  sanitization before library publication.
- Canonical schema version 2 with additive provisioning. Runtime startup only
  checks the matching schema. A separate generated database role has no schema
  creation, memory/history deletion, or history/audit update permissions.
- Operator commands generate persistent encryption/signing material and restricted
  expiring profile tokens into new owner-only files. Values are never printed.
- Streaming pg_dump backups encrypted with the free age tools, with HMAC-signed
  completion manifests. Restore authenticates the whole file before creating a
  fresh database and uses a transactional pg_restore. It refuses existing targets.
  Daily systemd unit/timer templates are prepared. No schedule or cloud upload is
  activated before destination, recovery keys and actual restore are reviewed.

## Qualification and deployment state

The pre-continuation unit run had 4,245 passing tests and two skipped. The current
real PostgreSQL/model/provider/capture/library/operator/backup lane passes **69
checks**, including actual age-encrypted dump/restore, wrong-key denial, altered
manifest denial, retained history and project denial. This lane also passed in
Ubuntu-Hermes on the native cluster. See the dated XML/log evidence. Built-image
checks and actual model-driven Hermes qualification remain separately identified.

Ubuntu-Hermes has the Docker client but its daemon is not running. Starting it can
change networking, so it has not been started as an automatic workaround. Native
user-space PostgreSQL/runtime provisioning and the separate test profile now work
while preserving isolation. Actual automatic capture, new-session recall, clear
correction and uncertain-change clarification were exercised with the existing
authorized cloud model. The local Granite serving window is below this Hermes
version's minimum; its full-chat qualification is still open. No everyday profile
has been switched.

The branch has been published and the tested code pulled from GitHub into Hermes.
Merging remains conditional on completion
and working checks. Known image advisory gates, full legacy consolidation,
graph/index workers and wider retrieval/load qualification remain open. New tests
are evidence for their exact scope; they do not close those remaining phases.

## Recovery boundaries

Keep the memory encryption key, backup signing key and age private recovery key
in the owner's password manager, separately from encrypted backup files. All are
needed for the relevant recovery steps. Existing whole-system backups do not
replace a tested service restore. No old key was tested for validity, no private
backup destination was selected, and no retained history was permanently erased.
