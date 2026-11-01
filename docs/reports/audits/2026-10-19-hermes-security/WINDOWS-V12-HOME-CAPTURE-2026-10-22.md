# V12 home capture correction and owner recovery follow-up

Date: 22 October 2026. The owner resumed the existing normal run after its
48-check native pass. Cognee was reused and Workspace inventory succeeded;
Workspace capture then failed with backup-engine exit 1. No home success was
recorded. This is still an incomplete backup.

## Cause and repair

Protected producer stderr reports argparse rejected an unrecognized empty
argument. The conditional assigning no non-Hermes options emitted no pipeline
output, yielding null. Appending that null to the Python command appended one
argv element; process quoting converted it to an empty argument. The capture
helper correctly rejected it. The inventory command always supplies an option,
so its successful native launch did not exercise this case.

Reproduction using the original production expression returned five Python
command elements instead of four; the last element was null and serialized as
an empty quoted argument. The command builder now treats null options as an
empty array. The main home loop also explicitly collects its conditional output
as an array. Unknown arguments still fail; no helper validation was relaxed.

Portable qualification passed 55 checks, zero failures/skips. Added regressions
cover null and omitted options and the actual capture_home producer feeding an
encrypted restic repository, followed by verified restoration and inspection of
a synthetic original file inside the recovered tar. All source data are test
fixtures; no real backup/upload was started.

The native suite adds four checks exercising restic-to-WSL producer execution
and restored synthetic argv for both the no-option and Hermes-option cases.
These use the existing Workspace distro, identity/cwd and synthetic output,
without backing up real homes or creating a profile. A fresh native pass is
required: the prior 48-check receipt does not qualify changed runtime hashes.
Native execution remains pending and is not represented by portable results.

The installed engine, main script and native test match maintained source.
Their originals and prior manuals are retained in a dated
C:\Scripts\archive\2026-10-22-home-options-fix-* directory. The existing run
20261022T011910Z-65be90bc is byte-for-byte unchanged, with only cognee completed.
No backup generation, private log or checkpoint was removed.

## Owner sequencing

Vincent requested no v12 run before progressing Hermes incorporation, then asked
for one-step guidance through separate Cognee recovery custody and credential
review. V12 remains paused; v11 remains scheduled. The native rerun and normal
v12 resume are later steps, not the next owner action.

The latest protected Hermes report remains the 20 October installed synthetic
qualification. It does not establish current service health or activation of
an everyday profile. Reuse that protected backend; do not repeat its runtime
installation or create another database stack. First complete independent owner
custody and disposition of real exposed credentials, then review current host
health, one profile's privileges/token renewal, and the remaining release gates.
Existing frontend advisory/final-candidate checks remain implementation work.

The owner has KeePassXC and a recovered vault copy, but the two previously
confirmed entries (Windows archive and Microsoft account) do not establish
custody of Cognee memory/index/signing/age/operator recovery material. Preserve
existing keys and retained history. Use
[the credential and custody procedure](../../../runbooks/CREDENTIAL-REVIEW-AND-RECOVERY-CUSTODY.md)
without printing secrets into agent transcripts. The first guided step is to
prepare an Enhanced Cognee recovery group in the original vault. Read-only
operator inventory and private transfer follow; generating new encryption keys
or rerunning create-config is not a custody transfer.
