# Restricted pilot memory access renewal

Scope: Ubuntu-Hermes, permanent hermes-runtime account and its existing
enhanced-cognee-pilot only. Reviewed 23 October 2026. Source implementation and
Workspace tests and the owner-run manual renewal passed. Installed interruption
recovery and an unattended/fleet credential lifecycle remain unqualified.

## What the owner does

Use the published pinned/hash-verified two-file command in the normal
Ubuntu-Hermes terminal as vincentspereira. Start from your home directory or the
existing protected deployment checkout. Keep this pilot idle during renewal;
everyday Hermes/bots can continue. Do not paste the command into Hermes chat.
Enter only your Linux sudo password at its private terminal prompt. No vault
password, API key or browser login is needed, and no chat model is called.

The reviewed bundle contains provision_pilot_access.py (unchanged issuer core)
and renew_pilot_access.py. Its bootstrap verifies the extension before executing
definitions, then verifies exact membership, hashes, regular types and size
limits for both sources entirely in memory. No adjacent checkout module is
imported and no package is installed. Root uses isolated system Python and only
standard-library code. The restricted child uses the existing protected tools1
Python and its existing dotenv parser.

Root checks the authorised human operator and protected runtime, reads only the
matching protected JWT signing configurations and creates a 24-hour credential
for the fixed pilot identity. Root does not walk the agent-owned profile. The
signing key never enters the child pipe, arguments, environment, report or file.
Only ordinary access tokens and their fixed claims go to the restricted child
over standard input. The existing account's denial of protected key access
remains a separate earlier installed check; this receipt is not a new audit of
every host path.

The child replaces only ENHANCED_COGNEE_ACCESS_TOKEN in the existing .env. It
preserves other bytes, OAuth and memory settings; does not change project/role,
Hermes defaults or existing memories. It checks the new credential against the
ready two-record pilot scope and verifies missing/expired/altered controls fail.
An expired existing pilot credential can be replaced after fixed-scope shape
checks; decoding its claims alone does not verify its signature. New access is
established by the authenticated API, not by local decoding.

## Successful result

Expect complete=true, stage=credential_renewal, credential_renewed=true,
authenticated_api_status_passed=true, unauthenticated_expired_altered_denied=true,
previous_environment_preserved=true and settings_and_oauth_preserved=true.
expires_utc is the new memory-token expiry. No raw token is printed. Existing
signing/encryption recovery copies remain applicable; renewal does not rotate
those keys. Keep the sanitized receipt with the qualification evidence.

runtime_qualified=false remains correct. This is manual pilot renewal only.
It neither installs a scheduled issuer nor qualifies fleet renewal, profile
backups, later human-answer durability, sharing/isolation or all release gates.

## Interruption and preservation

Every attempt retains a private .env-before-cognee-renew-<id> copy. A staged new
generation and private .cognee-renewal-<id>.json transaction journal are flushed
before atomic replacement. Readback, API acceptance and settings/OAuth comparison
precede the private .done.json completion receipt. The nonblocking private lock
prevents overlapping cooperating renewals. Existing files, generations and
journals are never deleted by the helper.

On a reviewed fresh retry, a recognized interrupted journal is reconciled only
when retained hashes match either the original or already-published generation.
It records not_published or published without reverting the current .env; the
fresh renewal then retains its own old generation. Incomplete copies created
before a journal remain private and retained. A journal/receipt torn during a
write, unsafe link/mode, unknown concurrent edit or conflicting evidence stops
for operator review. More than 128 journals also requires archival review.

If the command stops, send its sanitized message before retrying. Do not print
.env/auth.json, journal contents, recovery files or keys. Do not delete evidence,
restore the old .env automatically, loosen checks, renew from inside Hermes or
restart services. A failure after publication may mean the new credential is
already installed; inspection/reconciliation must determine that first.

Workspace checks use real temporary files and locks for transaction/recovery
cases, with API replies and account/process boundaries simulated. Installed
renewal and actual host interruption recovery require their own evidence.

## Installed result received on 23 October

At helper 8fb6fca95cf5480830d748134da93b785645820a the owner returned
complete=true/credential_renewal for the restricted pilot. The new expiry is
2026-10-24T09:15:06+00:00 (10:15:06 London time on 24 October). API acceptance,
missing/expired/altered refusal, retained old environment and unchanged
settings/OAuth all passed. No model was called or memory written. The receipt
reported interrupted_attempts_reconciled=0: this successful run is not installed
crash-recovery evidence. Keep the new expiry distinct from the initial token's
older expiry. No repeat of this successful renewal is requested.
