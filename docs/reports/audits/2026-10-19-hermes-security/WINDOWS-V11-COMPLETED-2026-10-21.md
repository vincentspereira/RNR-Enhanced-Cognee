# Windows v11 selected-data backup completed

Date: 21 October 2026. Evidence: owner-supplied Windows output, matching local
transcript, native qualification summary and completed archive/restore manifest.
This supersedes the earlier statement that the real v11 run was still building
its encrypted base. Remote upload and downloaded recovery remain unverified.

## Confirmed result

- Native qualification: 56 passed, zero failed; verification exit code 0.
- The qualification's script SHA256 matches the currently installed v11:
  `62214ce03631fd21861baec7c4262c059429690ad86fcfdf4516ce1fadeb3501`.
- Full selected-data backup: exit code 0, no recorded errors, duration 04:08:29.
- Staging tree: 91.01 GB as reported by the script.
- Four completed encrypted Cognee backup/manifest pairs collected with verified
  ciphertext hashes. Separate service-signature/decryption keys remain required.
- Native Hermes ZIP validated and hashed; native workspace archive verified.
- Completed encrypted base size: 47,503,603,481 bytes. It was promoted from the
  partial filename only after the v11 integrity check passed. A matched restore
  manifest exists and names this base; there is no differential in this first
  generation. Older generations/partials were preserved.
- Both OneDrive and Google sync-folder copies completed with file-size checks.
  Robocopy exit 1 means successful copying, not failure. Overall backup exit 0
  is separate from each native copy program's return code.
- Final cloud disposition is `copied_to_sync_folders`, not server-confirmed.

Selected generation:
`chain-20261021T140518Z-dc96519cf8914871abf4eed7be7ef35e`.
The local completed base and restore manifest remain together under its chains
directory. The recorded base digest is
`6fbbc9f4e5105d29e9ab7edd44260edb79a014c8a93202a0b03fb09c2b97f5e8`.
This digest was read from the successful run's manifest; a new independent
47.5-GB hash/decryption/recovery pass was not performed in Workspace.

## Separate manual Robocopy diagnostic

After the successful backup and exit code 0, the supplied attachment shows a
separate manual `/MIR` command against the raw Hermes agent-workspace path,
followed by a broad `Select-String 'ERROR'` query. Most matching lines are normal
filenames such as error.rs and error.tsx, not error records.

There are also 53 actual ERROR 995 records: two file-copy errors and 51 directory
timestamp errors. The two copy paths match the known security-test FIFO fixture
`test_public_symlink_duplicate_0/fifo/api.json`; the source test creates that path
with os.mkfifo. The diagnostic does not establish the exact cause of every
operation-aborted/timestamp error and is not a successful raw mirror.

This separate operation occurred after the completed encrypted generation and
did not target that immutable base. V11 already excludes the historical raw
agent-workspace staging tree from the encrypted source set and uses the verified
Linux-native workspace archive instead. Do not rerun the manual mirror as a
backup repair or infer the completed encrypted archive failed from its output.
No fixtures, source files, staging history or backup generations were deleted.

## Warnings and remaining evidence

Files On-Demand configuration could not be confirmed. Google DriveFS total
logical size was 84.03 GB, including metadata; it is not all disposable cache.
Neither observation is a recorded backup failure. Do not clear client data or
dehydrate/delete backup generations to meet a size target before upload/recovery
verification. This review changed no provider settings or files.

Remaining steps:

1. Confirm OneDrive upload finished with no sync error, then confirm Google.
2. Download the matched complete generation from a provider and recover into a
   new empty private directory using independently retained password material.
   Verify representative restored files and relevant native archive/database
   checks. Qualify each provider separately; local copies are not remote proof.
3. Verify actual scheduled execution. This was a manual run, even though the
   corrected task action was inspected by the native qualification.
4. Qualify v12 in native Windows before using it or switching the task. V12 is
   a separate format with broader coverage; this v11 pass does not qualify it.
5. Complete separate Cognee key custody/revocation and frontend release gates.

The initial owner step is to read OneDrive's status from its tray icon. No new
backup, upload, download, restore, account change or task switch was started by
this review.

Reference: [Microsoft Robocopy return codes](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy#exit-return-codes).
