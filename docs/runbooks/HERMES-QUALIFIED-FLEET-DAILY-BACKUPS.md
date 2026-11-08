# Daily encrypted backups for the 41 qualified inactive candidates

27 October owner-run V2 REPAIR AND DAILY BACKUP PASSED at
`operator-fleet-daily-backups-v2/run-54_yvptg`, helper `19956e7f...`.
The protected identity-switch repair probe qualified with zero owner-process
capabilities. All 41 candidates produced fresh signed encrypted generations.
The first real scheduled run and next daily schedule passed, with an enabled
daily timer, 86400-second interval and trusted PID-1 invocation proof (elapsed
52172 ms). The service stopped successfully; its timer remains scheduled.
No model/API call, credential/key change, private key sent to owner, recovery
key read, plaintext archive, restore replay or original-profile change occurred.
Previous disposable recovery evidence was reused. All admission policies stay
disabled. This closes candidate daily-backup installation, not fleet launch.
The failed V1 package/units/run remain preserved and its timer is disabled.

Do not repeat this completed backup qualification. The command below returns
the retained V2 result. Continue with
[the isolated gateway transport qualification](HERMES-ISOLATED-GATEWAY-TRANSPORT.md).
The historical failure and repair procedure below remain for provenance.

27 October first scheduled run FAILED with PermissionError and zero completed
profiles, retained at `operator-fleet-daily-backups-v1/run-9suhwfa3`, helper
`cfd9eb39...`. The timer stopped and the blocking marker remains. Repeating
install-fleet-backups returns the saved failure without repeating effects.
The main/40-profile recovery and lifecycle passes remain valid and untouched.

The journal confirms the first profile started; settings loading therefore
passed. The root permission error is inside the first capture's preflight or
child-launch path. The old receipt omitted errno/line details. It does not
prove which systemd restriction caused the failure, and this is not a reason
to remove filesystem, network or owner-isolation protections.

Run the following ONE guarded diagnosis/repair command instead:

```bash
sudo /opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime/bin/python -I /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment/launch_control.py repair-fleet-backups
```

It requires the exact preserved, stopped failure and no unit overrides. A
finite transient probe reproduces the public capture preflight and identity
switch under the same service restrictions. Its owner body reads only its
own process identity/capabilities, never profile contents, credentials or
archives. It returns fixed phase/errno/line metadata. Completed probes are
saved and never started again by a repeated command.

ONLY if the baseline proves a missing effective root identity-switch capability
and EPERM at child spawn will a second probe test root-only ambient SETUID and
SETGID, within the SAME two-capability bounding set. Before owner Python starts,
setpriv explicitly clears all inheritable and ambient capabilities. The child
must prove zero effective/ambient/inheritable capabilities, no supplementary
groups and no new privileges. All filesystem, network, device, root-key and
SUID/SGID restrictions stay. The distinction between ambient and bounding
capabilities follows the [systemd execution reference](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).

After that exact fix is proven, original unit files are preserved and the
failed timer's enablement is retired using systemctl disable. Its files,
blocked package and run remain. A NEW V2 package and daily unit/timer install
and qualify 41 fresh encrypted generations. If any other cause is observed,
the command returns backup_permission_diagnosed_no_automatic_repair and the
bounded diagnostic; no replacement schedule or backups are started. Do not
interpret a diagnostic as an installed repair or backup pass.

Validation: 61 targeted checks passed, including actual unprivileged native
setpriv execution/capability clearing. Prepared V2 units passed native systemd
analysis without diagnostics. No protected repair or installed pass is claimed
until the operator returns its real result.

## Original installation and retained behavior

The owner-run implementation and qualification batches passed for main plus
40 named candidates. Those exact artifacts, scopes, UIDs, configuration and
disposable recovery passes are reused. No completed model, renewal, restore or
invented-record probe is repeated by this operation.

Run one command in the owner's Ubuntu-Hermes terminal:

```bash
sudo /opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime/bin/python -I /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment/launch_control.py install-fleet-backups
```

The operator verifies both stopped protected batch receipts, all 41 exact
disabled identity bindings and the prepared backup draft. Every frozen source
and actual native/provider artifact must still match its recorded hash. It
refuses existing conflicting units/packages and preserves existing backup jobs.

The NEW root-owned service and timer are named
`enhanced-cognee-qualified-fleet-backup.service` and `.timer`. The first timer
fires after 15 seconds; later runs are scheduled daily. The service runs under
root with only identity-switching capabilities, no new privileges, a private
temporary directory, fixed writable homes/backups/state paths and strict
filesystem protection. Network connections are prohibited. The recovery key,
operator/API/worker credential files are inaccessible to this job.

Each private profile is captured by its own restricted owner, never traversed
by root. The exact recovered capture code handles SQLite/sidecars and the
fixed provider link. Main snapshots retain their known omission and per-database
transaction limits; this is not a globally atomic full-program snapshot.
Only the public AGE recipient is sent to children. Root signs ciphertext and
verifies written ciphertext hashes and HMAC readback. No plaintext archive file,
private recovery-key read, decryption, model/API call, credential issue,
deletion or upload occurs. Existing generations are retained. Capturing SQLite
can update ordinary read-bookkeeping files without logical database writes.

Per-profile start/completion checkpoints and immutable run summaries stay in
`operator-fleet-daily-backups-v1` under the backend candidate. A failed capture
preserves partial generations, records a blocking marker and stops this timer.
Later effects require explicit reconciliation. Repeating the install command
attaches to the first run or returns its saved installation result; it never
restarts completed probes. Ctrl+C only detaches the operator view.

The installer requires the first service to exit successfully, all 41 signed
generations, trusted PID-1 timer/invocation proof, an enabled active daily timer
and a next firing before reporting scheduled backup coverage. Future daily
runs get separate immutable receipts. A retained installation pass is not a
fresh current-health measurement. Backup failure leaves all admission gates
closed. This backup timer does not enable renewal or launch any agent.

Return only the final JSON summary. Production dispatch, main tools/context,
actual admitted-fleet lifecycle/coverage and final review remain separate gates.
