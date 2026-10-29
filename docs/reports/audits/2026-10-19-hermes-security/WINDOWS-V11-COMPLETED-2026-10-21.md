# Windows v11 selected-data backup completed

Date: 21 October 2026. Evidence: owner-supplied Windows output, matching local
transcript, native qualification summary and completed archive/restore manifest.
This supersedes the earlier statement that the real v11 run was still building
its encrypted base. Subsequent owner-reported sync completion and the recovery
copy check are distinguished below from independently verified remote recovery.

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
This digest was initially read from the successful run's manifest. The subsequent
full recovery-copy hash pass and owner-run password/integrity test are recorded
below; representative file/application restoration remains a separate check.

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

### Recovery follow-up, 21-22 October 2026

The owner reports that both OneDrive and Google Drive show all files synced.
The owner also reports seeing the matched archive and manifest on the OneDrive
website. These are owner-reported upload observations, not a separate server
integrity check.

The owner subsequently confirmed completion of the transfer into
`D:\Recovery-Test\WSL-v11-OneDrive-2026-10-21`. The screenshot and local file
metadata show the expected archive length, 47,503,603,481 bytes: 47.5 decimal GB
or 44.24 GiB (displayed as about 44.2 GB by Windows). The earlier Explorer
transfer estimate of about 83 GB has no established explanation and is not the
archive's measured length. Preallocated size alone was not treated as proof
that the transfer had finished.

A full SHA256 check of the completed recovery copy passed after the owner
confirmed transfer completion: 47,503,603,481 bytes read in 471.2 seconds; actual
digest `6fbbc9f4e5105d29e9ab7edd44260edb79a014c8a93202a0b03fb09c2b97f5e8`
matches the manifest. Size, modification time and inode were unchanged across
the read; the check exited 0. No password was used and no files were extracted.
This proves agreement with the recorded manifest, not independent authenticity
of that manifest or successful decryption/restoration.

The owner then supplied native PowerShell output from 7-Zip 26.03 testing this
same recovery path. After its hidden password prompt, the tool reported
`Everything is Ok`: 70,388 folders, 744,108 files, 89,251,757,979 uncompressed
bytes and 47,503,603,481 compressed bytes. Method includes `7zAES`. This proves
that the supplied password unlocked the archive and its contents passed the
integrity test. No extraction command was run by that test; representative
restored-file/application recovery remains pending. The output does not include
an explicit process exit-code printout; do not invent one.

Subsequently, the owner ran `Test-V11RecoveredFiles.ps1 -OpenFiles` (exit 0).
Its saved report and independent folder/hash inspection confirm three selected
files, totaling 154,324 bytes, with matching reference hashes. The owner confirms
both opened text files were readable. Only those three files and the small JSON
report were written. A console-summary formatting bug displayed null values
despite the valid saved pass report; it is corrected and regression-tested.
Selected-file restoration is now demonstrated; application/database recovery,
independent provider provenance and service-key custody remain separate.

The simple operating/recovery manual is maintained in
`scripts/windows/BACKUP-AND-RESTORE-SIMPLE-MANUAL.md` and installed at
`C:\Scripts\BACKUP-AND-RESTORE-SIMPLE-MANUAL.md`. Its full extraction command is
prepared guidance, not evidence that the owner has performed the extraction.

The transfer screenshot showed
Explorer copying from a chain folder; it does not establish whether this was a
fresh website download or a copy through the local sync folder. Qualify that
provenance separately before calling this independent off-machine recovery.

Files On-Demand configuration could not be confirmed. Google DriveFS total
logical size was 84.03 GB, including metadata; it is not all disposable cache.
Neither observation is a recorded backup failure. Do not clear client data or
dehydrate/delete backup generations to meet a size target before upload/recovery
verification. This review changed no provider settings or files.

Remaining steps:

1. Owner-reported OneDrive and Google client sync completion has been received;
   independent provider recovery verification remains pending.
2. Download the matched complete generation from a provider and recover into a
   new empty private directory using independently retained password material.
   Verify representative restored files and relevant native archive/database
   checks. Qualify each provider separately; local copies are not remote proof.
3. Verify actual scheduled execution. This was a manual run, even though the
   corrected task action was inspected by the native qualification.
4. Qualify v12 in native Windows before using it or switching the task. V12 is
   a separate format with broader coverage; this v11 pass does not qualify it.
5. Complete separate Cognee key custody/revocation and frontend release gates.

The recovery-copy checksum, owner password/integrity and selected-file
restoration/readability checks have passed. Small evidence copies are retained
outside the owner-approved temporary-copy cleanup. A fresh full hash of the
retained original matched before all six temporary files and the empty
`D:\Recovery-Test` tree were removed. No original/cloud backup, task/account
setting or new real backup was changed or started by this review.

Reference: [Microsoft Robocopy return codes](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy#exit-return-codes).
