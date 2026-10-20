# Hermes protected installation checkpoint - 20 October 2026

Protected installation remains incomplete. No private/everyday admission or main
merge is justified by this checkpoint. Local operator authentication is pending;
no distro restart was performed.

## Source and preservation

Verified Ubuntu-Hermes, Ubuntu 24.04.4 LTS, human operator vincentspereira UID
1000. Fetched the requested delivery ref through GitHub; its immutable revision
is 674d4de34b4bf8874e917a38b8a2988ba9939eac. Verified ancestry includes the
published eca54b0c274b8c00f9a69ea3d5c68713cf766853 qualification.
The clean original checkout and branch remain unchanged. Created a separate
checkout enhanced-cognee-protected-20261020 on
codex/hermes-ubuntu-deployment-protected-20261020. No delivery branch switch,
reset, main merge or profile update occurred.

Read actual local Codex/Claude instructions and the fetched protected follow-up,
original handoff, Hermes reports and Workspace reconciliation. Global/root
instructions remain 15639/8857 bytes; no global override was present. Existing
instruction reconciliation remains applicable; no instruction files were changed.

Host process inspection outside the sandbox confirmed WSL init as PID 1, with
active Hermes/PM2 processes. The historical synthetic API/worker and four store
ports were not listening. Their retained files, databases, credentials, previous
model settings, recovery material and failed fixtures were preserved. Historical
PID files are not evidence that those processes are currently running.

## Exact prepared changes, not executed

Systemd and systemd-sysv 255.4-1ubuntu8.16 are installed. Sudo noninteractive
execution refused with a password-required result. No password was requested in
conversation. Existing /etc/wsl.conf SHA256:
570516068f90f26bbeba9f103d31535df16c457cde69f701733801b6b0da73c7.
Prepared a guarded operator helper adding only [boot] systemd=true, preserving
all original section values, archiving the exact original and hash under /root
before atomic replacement. Existing automount disabled, Windows PATH injection
disabled, user and hostname settings remain unchanged. Helper does not restart.

Prepared a separate offline installer for /opt/enhanced-cognee-memory, plus empty
root-owned mode-0700 /etc/enhanced-cognee and /var/backups/enhanced-cognee.
It refuses existing destinations and validates a SHA256 input manifest. It keeps
root-only installation inputs, uses a full copied Python 3.12.13 outside homes,
hash-locked index/MCP dependencies, the restricted 1.1.0 wheel and a public offline
BGE cache (about 65 MiB). No chat-model weights were copied. No units or timers
are enabled by this helper. Operator helpers and private artifacts currently
reside under /tmp/cognee-protected-stage-20261020 and
/tmp/cognee-protected-checks-20261020; retain these before any cleanup.

Wheel SHA256:
97c88cd6fc73c775c410aa7317fda79c2f3d26c7d4332bb430ff09b6e7092067.
Fetched provider __init__.py SHA256:
b221c38baab2c2915f42683e0b8e764be0a42bc3d160f9ab786fd8ea64da6a0a.
The installed synthetic providers were not replaced, so this is a source hash,
not a claim of installed-provider qualification.

## New verification and limits

- Provider/operator/credential-launcher lane: 19 passed, zero failures/errors/skips.
- Hardened complete-runner regressions: 14 passed, zero failures/errors/skips.
- One initial invocation named a nonexistent runner-test path and ran no tests;
  the corrected runner lane above is separate evidence.
- Restricted wheel-content boundary passed. Offline fresh temporary runtime
  dependency installation, pip check and installed service/worker/backup imports
  outside source passed using Python 3.12.13 and package 1.1.0.
- Pip warned that its home cache was unavailable in the sandbox; installation
  used explicit offline wheels. ONNX Runtime warned it could not persist a
  telemetry device identifier. These warnings were not suppressed.
- Offline embedding returned 384 finite dimensions in a bounded host-level check.
  The initial sandbox embedding inference stalled for about a minute; stopped
  only that newly launched test process and retained its fixture. This is not
  a protected-service embedding test.
- Complete real SDK/browser suite, actual protected service restart, non-admin
  denial, protected backup/restore/index rebuild and daily timer were not run.
  The earlier 78-test/model evidence retains its original revision and scope.

## Required continuation

Apply the already-authorized changes through local sudo, preserving the root
archives. Save ongoing work and let the owner choose the targeted Ubuntu-Hermes
restart time. Never terminate the distro from the agent. Reverify PID 1 after
restart before installing or activating system units.

Finish protected store identities/storage, separate API/worker credentials and
operator custody. Retain cognee_hermes_selected_20261020 schema-3 database,
persistent keys and Qwen 27B synthetic route. Do not replay unrelated rows.
Record a newly created temporary non-admin account's exact UID/home/dedicated
paths before use; none was created or removed during this checkpoint. Run real
privilege/file/store denial tests from it. Preserve evidence/recovery under
protected operator storage, then perform only the authorized account cleanup
once its tests are complete. No real-bot OS isolation follows from its removal.

Run protected encrypted backup and fresh disposable restore, verify history,
decryption, index rebuild and project denial, then enable and verify the daily
persistent timer. Repeat complete hardened SDK/browser suite and installed
provider/model checks with artifacts outside source. Preserve failures. Password
manager custody, historical credential revocation, enforced frontend audits and
native Windows recovery remain open. Everyday profiles and all 41 bots are
unchanged; no private data ingestion or new network exposure occurred.
