# Fast focused review: E4 v3 capability line - LOCAL ONLY, one question

Fresh reviewer. ASCII. Output R2/VERDICT-E4V3.json under /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/docs/reports/audits/2026-11-06-g2-repair-review/ (create if missing). Fields: verdict, blocking_defects, findings, checks_actually_ran. No network fetches. No service starts. Review only.

Context (verified today): enhanced-cognee-backup.service is Type=oneshot User=root with ProtectSystem=strict, ReadWritePaths=/var/backups/enhanced-cognee, and an EMPTY CapabilityBoundingSet. A drop-in adds a second ExecStart step (ledger_tools_20261105.py backup --ledger /var/lib/enhanced-cognee-llm-budget/tokens.sqlite3 --output-dir /var/backups/enhanced-cognee). That step failed: EACCES on the ledger - the file is 0600 owned by the API dynamic user (uid 63764), and root without CAP_DAC_OVERRIDE cannot read it. The database backup step (first ExecStart) succeeds.

Proposed v3 (already committed, do not modify): the tracked drop-in at W = /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/cutover-package-worktree-20261105/docs/reports/audits/2026-11-05-cutover-package/units/enhanced-cognee-backup-40-ledger.conf adds ONE directive: CapabilityBoundingSet=CAP_DAC_OVERRIDE CAP_DAC_READ_SEARCH (drop-ins replace the whole directive, re-granting only read-side DAC). Everything else unchanged (ProtectSystem=strict keeps the fs read-only outside /var/backups/enhanced-cognee; NoNewPrivileges=yes stays). Claimed sha256 1f1e8c7f4eacdfb544d800db798575072b39d180ecfdd509d23fb5f059b2b61d - verify with sha256sum. Also verify: cd W && git log --oneline -1 == c58c7a70 (E4 v3 commit).

Questions:
1. Does the capability grant correctly explain and fix the EACCES (root + empty bounding set vs 0600 other-owned file)? Any reason it would NOT fix it?
2. Security: does granting CAP_DAC_OVERRIDE + CAP_DAC_READ_SEARCH to this oneshot unit (root, ProtectSystem=strict, writes confined to /var/backups/enhanced-cognee, NoNewPrivileges=yes) create any new write or privilege path? Note CAP_DAC_OVERRIDE also permits WRITE to 0600/0602 files it can reach - is the read-only mount the effective guard, and is that sound?
3. Residual risk: the ledger_tools step opens a sqlite db; on the read-only /var/lib mount a write attempt would give EROFS, not silent corruption. Confirm failure mode is fail-closed.
4. Anything in the file that weakens other unit settings (drop-in semantics: later assignments override; lists like ReadWritePaths are NOT re-set here - confirm no accidental reset of other directives).

FAIL only for blocking defects. Infrastructure interruption = NO_VERDICT.
