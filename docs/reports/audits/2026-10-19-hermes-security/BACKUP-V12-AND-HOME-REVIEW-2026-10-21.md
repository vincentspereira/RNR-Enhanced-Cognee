# Backup v12 and home-folder review

Date: 21 October 2026. Environment: Ubuntu-Workspace, source branch
`codex/hermes-memory-hardening`. Implementation is prepared; native Windows
qualification, actual v12 backup/cloud recovery and Hermes moves remain open.

## Owner decisions received

- No custom, trained, modified model weights/checkpoints need preservation.
  Downloadable weights may be excluded; original outputs/source/fixtures and
  recovery/licence/revision metadata are retained.
- Add the reviewed D: work products, excluding Entertainment.
- Leave personal OneDrive originals separate. This is an explicit coverage gap;
  do not hydrate/re-upload those originals to satisfy backup completeness.
- Reorganise the listed homes, preserving required work. The existing isolation,
  recovery-key custody, old generations and protected service remain intact.

## Implemented Windows source

`C:\Scripts\backup-all-wsl-v12.ps1` exists, with the backup-v12 support directory,
native synthetic qualification, guarded task update, recovery guide/tool,
read-only worker-profile review and inventory/apply Hermes-reorganisation wrapper.
Maintained, credential-free copies are in `scripts/windows` in this repository.
No real configuration, secrets, private instruction archives or backup payloads
were copied into Git. Restic is portable, free/open-source and pinned at 0.19.1;
official archive/binary hashes are recorded. No cloud subscription was added.

V12 stores encrypted, deduplicated recovery snapshots. The existing DPAPI-backed
archive password passes into restic through a private child pipe, never a
plaintext argument/environment/file. Finished scopes checkpoint; retries resume
unfinished scopes. Entirely unchanged Linux homes reuse a prior verified
snapshot following metadata comparison. Changed native home streams still need
reading; unchanged stored data blocks and cloud objects are reused.

Cloud repositories are separate `restic-v12` subfolders of the established
OneDrive and Google targets. Immutable encrypted objects copy first, snapshot
objects last. Verified partial prefixes resume. Existing mismatches fail closed
and remain untouched. No MIR, purge, forget or prune is used. Cloud upload status
is distinct from sync-folder verification. Existing generations remain.

Full Windows owner/worker profiles, C:\Scripts, D:\Vincent except Entertainment,
reviewed RNR folders and AI-work-product directories are covered by policy.
OneDrive personal originals, downloadable weights, rebuildable caches/runtimes,
live AppData WSL/Docker disks and full Windows system images are explicit limits.
Geometry binaries, original archives and useful logs are not globally excluded.
Windows VSS is required for file capture; real Windows behavior is unqualified.

All three reviewed Linux owner homes use native tar, retaining POSIX paths,
modes and links without following compatibility links. Hermes native ZIP data
is merged into that stream so it is not also stored as a duplicate ZIP/raw
mirror. Profiles/skills/plugins/custom source and per-profile history survive;
generated `.hermes/backups` is omitted. Committed SQLite WAL state gets consistent
database images; fixtures retain original bytes. A home is not globally atomic.
Local Linux software/cron and OS/isolation recovery metadata is also carried
inside encrypted home tar members. Its changes invalidate home reuse; collection
failures are not suppressed. Registered Windows software/OS-build metadata is
included separately in the encrypted Windows snapshot. The actual Workspace
inventory succeeded (empty crontab correctly recorded); other hosts remain
subject to native qualification. Raw inventory contents remain private.

Cognee completed encrypted backups are a required independent scope, with
freshness, age-envelope and ciphertext hash checks. Signature authenticity and
decryption still require separate recovery keys. Whole WSL images use explicit
offline export mode and already stopped distros. No distro is stopped/restarted
or mounted by this work, and offline export/import has not been qualified.

## Workspace moves completed and verified

All original bytes, modes, ownership and link targets matched after relocation.
Old home names are compatibility symlinks to one physical copy. No original file
was deleted. The private per-file journal remains under the owner's local
maintenance state and is not published.

| Original home folder | Physical destination under the same home |
|---|---|
| AI-Models | Projects/_LocalData/RNR-Spatial-Engine/legacy-home-AI-Models |
| ai-setup | tools/ai-setup |
| LSWA-e2e-data | Projects/_LocalData/RNR-Legal-and-Social-Work-Assistant/LSWA-e2e-data |
| pr18_3_smoke.IQOR | Projects/_LocalData/RNR-Spatial-Engine/pr18_3_smoke.IQOR |
| rnr-eval | Projects/_LocalData/RNR-Spatial-Engine/rnr-eval |
| rnr-worktrees | Projects/_LocalData/RNR-Spatial-Engine/rnr-worktrees |

The legacy AI-Models evidence differs from canonical D: evidence; it was not
overwritten or merged blindly. rnr-eval is referenced by current Spatial source
and historical evidence. rnr-worktrees contains scripts/evidence, not actual Git
worktrees. LSWA contains database/index state, so deletion was inappropriate.
No concurrent Spatial source changes were modified by this cleanup.

## Hermes fleet, pending moves and worker-profile decision

Metadata-only review of the owner's current native Hermes ZIP found 42 profiles
(40 bot profiles and two test profiles), all with configs and skills; 126
profile database files were included. Plugin files were present where configured,
and root skills/plugins/fleet/sessions/config data were included. Earlier
excluded-directory lists did not exclude those whole bot profiles.

Hermes native startup and live file moves could not run in this session:
Workspace currently cannot launch Windows executables, and no access boundary
was changed to bypass that. The prepared native wrapper can inventory/apply the
two research moves into Projects/StanKorp, archive private instruction rollback
folders outside Git, retain/move the MAS clone, and consolidate the lower-case
projects checkout. It checks activity, collisions and linked/multiple Git
worktrees, preserves dirty/untracked content, journals results and verifies
contents/metadata. Protected running deployment checkouts are not targets.
No Hermes move is claimed completed. Collisions/active work are retained for
individual resolution; no repository is declared redundant merely by its name.

`C:\Users\rnr-worker` is a Windows-managed worker identity/profile, not a stray
project directory. Existing Spatial PR-02 and PR-16.6 evidence records its
isolation role. Keep it in place. Fresh Windows enabled/admin/profile-loaded
checks are prepared but have not run; no account, ACL or firewall was changed.

## Qualification and remaining gates

- Python/Linux qualification: 14 tests passed, zero failures/skips. Real pinned
  restic encryption, block reuse, version/deletion recovery, failed-producer
  rejection, native tar/SQLite/profile coverage, fingerprint reuse and atomic
  reorganisation/collision preservation and private-archive Git exclusion are
  exercised with synthetic data. Recovery-inventory failure and system-change
  invalidation are also covered.
- Portable PowerShell qualification: 24 checks passed, zero failures/skips,
  including all new script parsing, actual scope checkpoint/resume behavior,
  ciphertext reuse/check, verified-prefix resume, corruption/lock refusal and
  process-argument round trip. This is PowerShell 7.6.7 on Linux, not Windows.
- Native Windows 5.1/VSS/DPAPI/ACL and real policy-filter tests are prepared in
  Test-WindowsBackup-v12.ps1. They must pass against exact installed hashes
  before v12 can start a real backup or its helper can switch the task.
- Existing v11 file/task are unchanged by v12 preparation. The latest log still
  reports encrypted-base creation; its current partial file was growing, not
  yet a completed/cloud-qualified recovery generation. Do not interrupt it.
- Real v12 capture of all three homes and Cognee, provider upload confirmation,
  downloaded recovery from EACH provider, actual weekly task execution and
  offline WSL export/import remain native/owner steps.
- No automatic retention deletion. Additional local/cloud capacity is needed
  for the first v12 seed alongside retained v11 archives; encrypted v11 blocks
  cannot seed the new restic format.

Owner service-key custody/revocation, frontend release gates and everyday-bot
admission remain separate. This backup improvement is not a main-merge or
production-readiness claim.

## Next owner step

After the current v11 backup finishes, run the native synthetic v12 test from
elevated Windows PowerShell under the usual Windows owner account. It starts
no full real backup, uploads no real data and changes no scheduled task:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Scripts\Test-WindowsBackup-v12.ps1"
Write-Host ("Exit code: " + $LASTEXITCODE)
```

Review the result before running a real v12 backup, applying Hermes moves or
switching the existing weekly task. The installed recovery guide provides
subsequent instructions without requesting any secret in chat.
