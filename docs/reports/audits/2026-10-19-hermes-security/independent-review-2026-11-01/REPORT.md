# Independent audit: Enhanced Cognee fleet memory delivery

Date: 2026-11-01, UTC. Host observed: Ubuntu-Hermes, Ubuntu 24.04.4 LTS,
Linux 6.18.54.1-microsoft-standard-WSL2, ordinary user UID 1000.

Repository: /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024
Branch: codex/hermes-ubuntu-deployment-launch-20261024
Revision audited: 89d1be78bbe9571b9152396c5483eabbb8360b95

## Verdict and recommendation

**The deployment is substantially functional, but the blanket claim "delivered
and verified, everything passes" is not supported. Do not sign off unrestricted
production readiness until the high-severity findings are addressed.**

All 44 roles advertise their expected MCP tools. The five backend services plus
the index worker are active. Every current role token and the main token passed
an authenticated, correctly scoped status request. Invented-data memory CRUD,
ingestion refusal, translation and reviewer-only library protection worked.
Separate seeded probes proved real GLM-5.3-Flash summarisation and consolidation.

However, the supplied consolidated verifier crashes at root-only receipts, the
functional suite reports two failures while exiting zero, and several security
and recovery claims are stronger than their evidence. There are four high-
severity findings: a root job executing a user-writable interpreter, an ingestion
DNS-check bypass, summaries that detach shared content from its access lifecycle,
and a token cap that is not a reliable spending limit.

Recommendation: commission a separate, bounded remediation task for F01-F04,
then repair the acceptance checks and reconcile backup/renewal evidence. This
audit made no deployment fixes, no commits or pushes, and no main merge.

## Evidence labels and boundaries

- LIVE: fresh installed-host command or bounded API/MCP probe.
- OFFLINE: actual source functions exercised using invented data and fake
  sockets/stores/model responses. This is not installed-host exploitation.
- SOURCE: code inspection at the revision above.
- INHERITED: a dated delivery document or receipt, not a fresh execution.
- NOT VERIFIED: evidence unavailable, owner-only, or deliberately not rerun.

The installed MCP server equals its repository source byte-for-byte. All 45
provider-plugin Python file sets, including main, match one another. The installed
renewal job does NOT equal the repository source. The protected backend candidate
source/inventory was not accessible through the attempted paths; source-level
findings below must not be read as proof of exact deployed backend bytes. Live
behaviour is separately identified.

No fleet bot or fleet admission was activated. No credential family was rotated
or tested again, no service was restarted, and no completed native/memory
qualification suite was rerun. The explicitly requested functional suite and
bounded investigative probes are separate from those qualification suites.

Only invented test records were created by the functional/investigative probes.
A separate selected audit-summary memory was saved to the main provider and read
back, without raw outputs or credentials. The original suite's web-researcher scope
was checked empty, including shared-visible rows, before its unfiltered analysis
calls. Its final count was zero. Two later audit fixtures plus their generated
summary were retracted with version checks; each read back as HTTP 404 and active
scope returned to zero. Encrypted history remains by design; nothing was
permanently deleted.

Only this new audit directory was added to the checkout. Existing tracked files
remained unchanged. The second reviewer reported one incidental ignored Python
bytecode-cache refresh during import; subsequent parent/reviewer probes used -B.
No profile config, .env, credential file or protected deployment file was edited.

## 1. Verification matrix: headline results

Full per-check rows, exact command aliases, all 44 role rows and all 20 functional
rows are in [VERIFICATION-MATRIX.md](VERIFICATION-MATRIX.md). Raw stdout is retained
in consolidated.txt, fleet-tools.txt and functional-original.txt.

| Check | Command/evidence | Actual result | Verdict |
|---|---|---|---|
| Checkout and revision | git status --short; git branch --show-current; git rev-parse HEAD | Correct delivery branch; HEAD 89d1be78; clean before audit | PASS |
| Backend services plus worker | systemctl is-active enhanced-cognee-{api,postgres,qdrant,graph,cache,index} | Six active responses | PASS |
| Loopback bindings | ss -lnt | API 127.0.0.1:28080; PostgreSQL 28434, Qdrant 28535 and graph 28536 loopback-bound | PASS for observed listeners |
| Supplied consolidated verifier | verify_everything.py, deployment Python | 55 OK rows, then PermissionError on /var/lib/enhanced-cognee-rotation; exit 1; no normal final failed list | FAIL, receipt access expected but crash is a verifier defect |
| Expected total | Source enumeration | 60 planned checks after four-role expansion: 55 non-receipt checks plus five rotation families | VERIFIED count; full 60 not executed |
| Per-role verifier | verify_fleet_memory_tools.py | complete=true, failures=[], roles=44; exit 0 | PASS for catalogue/config groups only |
| Original functional suite | .archive/fetch-html-diagnosis/comprehensive-functional-test.py | 18/20; summary and consolidation failed; complete=false; process exit 0 | FAIL |
| Functional-failure cause | independent_probes.py | Empty scope: summary 422 Nothing to summarize; consolidation 422 Too few records to compare | Cause established |
| Seeded real summary | Same independent probe, two invented records only | HTTP 200, sources=2, tokens_used=568, 13.573 seconds; stored text read back exactly | PASS, distinct investigation, not a retroactive suite pass |
| Seeded consolidation | Same probe, invented records only | HTTP 200, compared=3, report_only=true, tokens_used=580 | PASS |
| Paced normal writes | Two writes, three-second spacing, authenticated GET readback | Both HTTP 200; both read back correctly | PASS |
| Library publish gate | Original functional suite, one chief-of-staff attempt | HTTP 403 requiring memory:admin | PASS; expected refusal |
| Loopback ingestion refusal | Original suite | Refused with public-address reason | PASS for direct loopback; F02 remains |
| MCP manual independent client | Legal-specialist config, own JSON-RPC client | Exact literal 15-name set; authenticated get_stats correct scope; unoffered ingest tool refused | PASS |
| All ten MCP read tools | probe_read_tools.py, actual web-researcher definition | Seven non-error payloads; get_related 422, library reads 403; all three failures omit isError | FAIL, F18 |
| Malformed MCP request | Disposable child only | params=[1] terminates child, exit 1 | FAIL, F16 |
| Provider selection | inspect_host.py, selected fields only | 45/45 memory.provider=enhanced_cognee; memory CLI toolset enabled; 44 fleet plugins explicitly enabled | PASS for configuration |
| Main provider | Installed plugin plus current chat's enhanced tools and successful enhanced_recall | Eight tool schemas present; real recall works; main has no explicit plugins.enabled entry | PASS for present tool/recall path; no new main capture cycle |
| Fresh automatic capture for all 44 | Prohibited completed qualification not rerun | Config/API/catalogue proof is not a fresh per-role native remember/recall/capture test | NOT VERIFIED independently end-to-end |
| Profile token files | stat and in-memory presence/expiry parsing | All 45 current .env files mode 0600; 30-day issued lifetimes; remaining roughly 28-30 days; all authenticated status scopes correct | PASS |
| Token copies | Presence-only scan of .env* backups | Five additional token-bearing backup files, all 0600 | Protected backups found; literal "only .env" claim is too strong |
| LLM route/status | GET /v1/memories/summarization/status | configured=true, model=GLM-5.3-Flash, daily_token_cap=50000 | PASS configuration, not hard spending enforcement |
| LLM key filesystem | stat of /etc/enhanced-cognee; attempted llm.json stat | Parent directory root:root 0700; llm.json access denied | PARTIAL; exact key file mode/exclusivity owner-only |
| Renewal schedule | systemctl show/cat timer | Mon 04:00, 5-minute jitter, Persistent=yes; next 2026-11-02 04:00:17 GMT | PASS |
| Renewal current inventory | Installed profiles() function only, no renewal | 45 identities including main and four specialists | PASS inventory; no credential action |
| Renewal last saved run | Selected state.json fields | 2026-10-30T23:30:32Z; default renewed, 40 skipped, no failures; state lacks new four | INHERITED past execution; not 44-role renewal execution |
| Renewal deployed-source equality | Byte comparison | False; installed receipt-only discovery versus source union/import | FAIL claim of deployed source change, F09 |
| Daily backup scheduling | systemctl show/list-timers/cat | Qualified-fleet timer active; prior service success; next 2026-11-01 13:16:59 GMT | PASS schedule, not current fleet recovery coverage |
| Backup membership | Live unit plus source | Qualified inactive 41-candidate homes, ProtectHome=yes; current ~/.hermes not included in that job | GAP, F13 |
| Canonical/profile backup job state | systemctl show | Prior executions success; protected backup content inaccessible | PASS job metadata; restore/ciphertext not freshly verified |
| Five rotation families | Root directory mode 0700; non-root verifier failure | Receipt bodies not accessible; no privileged commands run | NOT VERIFIED; owner summaries required |
| Fresh branch-history secret scan | scan_branch.py; git rev-list/cat-file | 17,359 blobs, 846,762,262 bytes; no exact current fleet token or literal JWT match; structural candidates in test/detection artifacts | PASS bounded scan; not universal secret-free certification |
| Fresh dependency check | audit_dependencies.py; OSV querybatch | 47 unique public lockfile package/version pairs; no advisories returned | PASS selected current locks; not deployed binary/OS inventory |
| Disk/inodes | df -h; df -i | 823G available, 14% used; inodes 3% used | PASS current headroom |
| Journal storage | journalctl --disk-usage; systemd-analyze cat-config | 388.2M; default journal retention, no explicit local size/age override | Defaults present; no bespoke retention proof |
| Alert routing | systemctl show ... -p OnFailure -p WatchdogUSec | Relevant OnFailure entries empty; no alert delivery was tested | NOT VERIFIED operational alerting |

### Selected real output

Consolidated verifier:

```text
OK   token renewal timer                                  active
OK   daily fleet backup timer                             Sun 2026-11-01 13:16:59 GMT 8h Sat 2026-
{"complete": false, "error_kind": "PermissionError", "detail": "[Errno 13] Permission denied: '/var/lib/enhanced-cognee-rotation'"}
```

Per-role verifier:

```json
{"complete": true, "failures": [], "roles": 44}
```

Original functional suite:

```text
ERR  analysis: summarize (real model)
ERR  analysis: consolidation report-only
{"checks": 20, "complete": false, "failed": ["analysis: summarize (real model)", "analysis: consolidation report-only"]}
```

Its operating-system exit code was nevertheless 0. See functional-command.json.

## 2. Findings, evidence and minimal fixes

Severity is reviewer judgement about impact, not proof that a vulnerability was
exploited. Source/offline findings require deployment-byte reconciliation before
claiming the identical installed defect. F01 is installed-host evidence.

### F01 - HIGH - Root renewal depends on an ordinary-user-writable runtime

Evidence: LIVE /etc/systemd/system/ec-hermes-memory-token-renew.service uses
User=root and ExecStart pointing to the deployment virtual environment under
/home/vincentspereira. Its resolved Python target is UID 1000-owned, mode 0775,
and writable by the audit user. Its parent environment is also replaceable.
SOURCE integrations/hermes/deployment/install_fleet_token_renewal.py:22-23,88-94.
Metadata and no-launch confirmation: offline-secondary-probes.json and
renewal-units.txt.

Impact: an ordinary-user compromise can replace code executed by the scheduled
root job. Root-owned renewal scripts and NoNewPrivileges do not remove root's
existing ability to read protected credentials. The sandbox still exposes the
service credentials needed for renewal; no exploit or credential read was tried.

Minimal fix: use a root-owned interpreter, dependencies and ancestor directories;
retain a narrowly hardened renewal unit. Do not deploy the source-only role-table
change unchanged: renew_fleet_memory_tokens.py:75-83 also executes a writable
checkout module as root. That extra import is NOT in the installed job today.
Use a validated, root-owned data-only inventory instead.

### F02 - HIGH - Public-address validation can be bypassed by DNS rebinding

SOURCE src/ingestion.py:124-129 validates resolve_public(host), discards the
addresses, then constructs HTTPConnection/HTTPSConnection using the hostname.
The connection resolves it again. OFFLINE parent-replayed probe: two lookups,
first a public IP, second 127.0.0.1:80; the invented document was accepted.
See offline-security-receipt.json, ssrf_dns_rebinding.

Impact: a hostile name may pass the first check then target an internal address
on the second lookup. The live direct-loopback refusal does not test this. No
real internal endpoint was contacted and installed exploitability is untested.

Minimal fix: connect to a validated IP, preserve original Host and TLS
SNI/certificate verification, check the actual peer, and never re-resolve between
admission and connection.

### F03 - HIGH - Stored summaries lose shared-source access and expiry controls

SOURCE src/memory_api.py:276-291 reads include_shared=True and writes an ordinary
new caller-owned summary. Only source count/model are retained, not source IDs,
versions, grant dependencies or expiry. src/memory_service.py:213-217 defaults
expiry to none. OFFLINE endpoint probe confirmed foreign shared content enters
the prompt and is copied independently; see summary_grant_lifecycle receipt.

Impact: revoking, retracting, correcting or expiring the source does not invalidate
that detached copy. This undermines the documented reviewed-sharing lifecycle.
This was not a live cross-role revocation experiment.

Minimal fix: owned-only default, explicit approval for shared-source derivatives,
source project/ID/version references, inherited expiry and enforced dependency
checks when serving derivatives. Merely adding provenance labels is insufficient.

### F04 - HIGH - The 50k/day cap is not a dependable spending limit

SOURCE src/llm_summarize.py:86-104 holds per-process counters; API checks allowance
before awaiting model work and charges afterward (memory_api.py:282-285,317-321,
331-335). No reservation protects concurrent calls. Missing usage is accepted as
zero (llm_summarize.py:130-134). A fixed 4,000 estimate is not a conservative bound
for every permitted input plus output.

OFFLINE parent-replayed probe: two requests both passed a 5,000 cap and charged
8,000 tokens. A successful fake model reply without usage charged zero. A new
TokenBudget after restart also loses previous daily accounting, explicitly
acknowledged in source but not in the engagement's hard-cap wording.

Minimal fix: atomically reserve a conservative prompt/output maximum before
sending, reconcile afterward, conservatively account for missing usage and
uncertain failures, and persist accounting shared across service workers/restarts.
Treat the current cap as best-effort accounting, not a cost guarantee.

### F05 - MEDIUM - Hosted model requests lack explicit source/privacy admission

SOURCE memory_api.py:46-50,276-284,311-320 selects recent own/shared records without
source-ID allowlists or an explicit hosted-processing approval check. Translation
passes supplied text directly to the model. OFFLINE invented credential-shaped
translation input reached the fake model without screening. No real credential
was used. Existing capture/read credential checks are useful but are not a
record-level permission to send content to an external model.

The supplied functional suite's summary/consolidation is not fixture-isolated.
This audit checked the scope empty first; it did not send private records out.
The live configured route/model and real invented-data calls were confirmed;
the root-only route file was not read.

Minimal fix: explicit selected source IDs, owned-only default, a project/record
hosted-processing policy, and credential screening before every model dispatch.
Make tests refuse pre-existing data or operate on a narrowly approved fixture set.

### F06 - MEDIUM - MCP transport errors do not set isError

SOURCE integrations/hermes/enhanced_cognee_mcp/server.py:118-126,329-330 converts
HTTP errors into dictionaries and wraps them as ordinary MCP text results.
OFFLINE parent reproduction returned HTTP 403 content with mcp_isError=false.
Later live calls confirmed that get_related returns HTTP 422
while get_shared_memories and library_membership return HTTP 403, all without
isError. Thus the original suite actually reports a passing graph-traversal
check for a refused request (see F18), not merely a hypothetical false positive.
Oversize/non-JSON responses have the same reporting weakness.

Minimal fix: carry failures through _error with isError=true; require valid,
endpoint-specific payloads in the tests. A readable error string alone is not a
successful operation.

### F07 - MEDIUM - MCP's timeout is shorter than real model operations

SOURCE server.py:79 fixes the API timeout at ten seconds; llm_summarize.chat allows
45 seconds. LIVE independent direct-API summary took 13.573 seconds. This proves a
configuration mismatch, not that this exact request failed through MCP.

Impact: valid model work can outlive its caller's timeout. A stored summary could
be created after the client reports failure; retries use a new random summary key
(memory_api.py:288), so duplicate digests are possible. No orphan/duplicate was
created deliberately in this audit.

Minimal fix: align bounded operation deadlines and add stable request identities
or job-status retrieval for longer operations. Test the real MCP analysis path,
including a timeout-after-dispatch case, under separately approved scope.

### F08 - MEDIUM - Renewal failures are not reliably isolated or acknowledged

SOURCE installed renewal job:80-91,100-123, and repository equivalent:100-111,
120-143. A subprocess timeout escapes the per-profile loop and prevents later
profiles/state publication. Completion uses bool(receipt.get("complete")) and
ignores process.returncode.

OFFLINE parent confirmations: TimeoutExpired escapes; exit 1 plus the string
"false" is accepted as complete. state.json is written non-atomically. The
installer at install_fleet_token_renewal.py:132-143 reports complete=true even if
the immediate service run fails; the consolidated check only tests timer activity.

Minimal fix: catch bounded exceptions per profile, require exit zero and literal
complete is True, validate profile/expiry, continue the sweep, and atomically
publish state. Installation acceptance and health checks must verify service
success and full inventory, not timer activity alone.

### F09 - MEDIUM - The documented renewal source update is not installed

LIVE byte comparison differs. Installed /opt/.../fleet-renewal/
renew_fleet_memory_tokens.py:67-73 uses receipts only; source :67-93 unions the
role table and receipts. Current installed discovery still returns all 45
identities because the receipts were updated. Therefore no current specialist
omission is claimed.

The last state is October 30 and covers 41 identities, not an execution of the
new 44-role sweep. The installer's upgrade path (:69-72) allows a predecessor only
for the provisioner, not the installed older renewal job, so it does not provide
a valid automatic upgrade for that changed file.

Minimal fix: reconcile the report with installed bytes; design a reviewed,
atomic upgrade from the exact predecessor. First remove F01 and the source-only
root import risk. Do not simply rerun the installer during this audit.

### F10 - MEDIUM - Running MCP credential refresh remains an acceptance gap

SOURCE server.py:345-362 captures the token at startup. The provisioner publishes
a new .env but does not itself reconnect existing children. A successful file
replacement is not proof a long-running MCP child uses the new credential.
Hermes has profile-scoped secret-refresh machinery, so a gateway restart must
not be asserted necessary without tracing it.

No credential renewal, expiry simulation or gateway restart was performed.
This is an unclosed reliability gate, not a demonstrated current outage. The
weekly seven-day renewal window also leaves little scheduling slack if the
host misses its trigger, making a missed-run alert important.

Minimal fix: establish a bounded token handoff/reconnect and post-renewal live
check, or prove the existing runtime refreshes every relevant child. Preserve
old valid access until the handoff is acknowledged; test interruption explicitly.

### F11 - MEDIUM - Acceptance scripts give misleading or incomplete verdicts

LIVE verify_everything.py recorded 55 OK lines then PermissionError at :143-147.
The documented non-root behaviour (five false receipt rows plus a normal summary)
does not occur. SOURCE :168-182 loses the normal per-check report on that error.

LIVE functional suite has complete=false and two failures but process exit 0;
:216-218 never sets a failure exit. Its correction status is overwritten by
history status (:70-75), a clarification conflict counts as retraction success
(:82-85), cleanup results are ignored, and missing active_records defaults to zero
(:213-214) without measuring a starting baseline.

The two observed analysis failures are fixture-ordering defects: the suite
retracts its own input before analysing an otherwise empty profile. Seeded
independent calls passed, so the failures do not establish broken backend models.

Minimal fix: explicit PASS/FAIL/SKIP, predictable non-root summaries and nonzero
exit for failed assertions. Keep fixtures alive for their dependent checks,
isolate them from existing data, assert each status/version, and prove cleanup
against a measured baseline. Preserve these original failures as evidence.

### F12 - MEDIUM - Catalogue verification is not provider end-to-end proof

SOURCE verify_everything.py:106-121 and verify_fleet_memory_tools.py:60-84 inspect
only the final configured argument and then launch hardcoded commands. They do
not validate provider selection, plugin/toolset enablement, the configured command
or actual gateway credential interpolation. Expected names also come from the
same source GROUPS definition. Thus a matching catalogue is not independent
proof of the intended launch/provider path.

This audit separately verified selected config fields and all 45 authenticated
scopes, and implemented a separate legal-specialist client with a literal
expected name set. Those extra checks passed. They still are not a fresh
44-role native capture/recall lifecycle test; that completed qualification was
not rerun, as instructed.

Minimal fix: label catalogue checks accurately, validate the entire configured
contract, exercise the supported configured launch path, and keep existing native
qualification evidence linked separately from discovery.

### F13 - MEDIUM - The named fleet backup does not prove current fleet recovery

LIVE qualified-fleet-backup-v2 unit describes qualified INACTIVE candidates,
sets ProtectHome=yes, and its writable/readable scope names the 41 restricted
candidate homes under /var/lib/enhanced-cognee-profiles, not the current gateway
home or 44 ~/.hermes/profiles. SOURCE install_launch_fleet_backups.py:69-99,
204-218,231-245 explicitly fixes membership at 40 roles plus main and reuses prior
restore evidence instead of replaying a restore for each scheduled generation.

The canonical database backup may cover all memory rows and had successful job
metadata; that is distinct from recovery of current profile configs/plugins/
credentials. Another current gateway backup may exist but was not established.
No current backup content, signature or recent restore was read as ordinary user.

Minimal fix: explicitly inventory current gateway/profile coverage, including
four specialists and post-renewal credentials; retain separate canonical-store
and inactive-candidate coverage. Provide dated restore receipts and a periodic
bounded drill. No unapproved backup deletion or off-host upload is recommended.

### F14 - MEDIUM - URL-fetch timeout is not an absolute operation deadline

SOURCE ingestion.py:96-100,126-139 uses synchronous DNS and a socket inactivity
timeout; memory_api.py:243 runs it in a thread. Slow trickle responses can extend
the operation beyond ten seconds. Cancellation of the awaiting coroutine does
not by itself stop a running thread. This is source analysis, not a live
slow-response denial-of-service test.

Minimal fix: bound DNS, connection, headers and body by an absolute monotonic
deadline; terminate owned sockets/work when the deadline is reached.

### F15 - LOW - Failed multi-chunk ingestion can leave partial writes

SOURCE memory_api.py:251-252 commits each chunk through remember separately.
OFFLINE probe accepted one invented chunk then refused the next, retaining one
record although the request failed. No live partial-ingestion attack was run.

Minimal fix: transactionally preflight/store a batch, or return explicit partial
progress and stable resumable identities. Do not silently treat request failure
as proof that no records were written.

### F16 - LOW - Malformed MCP params terminates the child

SOURCE server.py:322-323 assumes params has .get before entering the handler's
try block. LIVE disposable legal-specialist MCP child terminated with exit 1 for
params=[1]; params=[] had not crashed because the empty value became {}.

Minimal fix: validate JSON-RPC object, params and arguments shapes before lookup;
return a protocol error and keep the server alive. No actual fleet bot or gateway
child was killed or restarted.

### F17 - LOW - Completion documentation contains stale and conflicting claims

ENGAGEMENT-COMPLETE-2026-11-01.md :5-20 still names old head 96153d35, 40 roles and
56/56. Section 3.5 :129-139 still advertises coordinator-grade 20 tools for main
and the removed coordination group. Section 5 corrects this; section 6 adds the
four roles. The review prompt :71-73,89 still uses 51/56 despite 60 current planned
checks. User's later correction of 60 checks is consistent with current source.

Section 6's claim that the renewal job now unions the table is only true of
repository source, not installed code. "Tokens only in .env" also omits five
0600 token-bearing preservation backups; these are not evidence of a leak.

Minimal fix: one current top-level revision/roster/matrix/check-count table,
separately labelled historical sections, and explicit source-versus-installed
status. Do not erase historical evidence or remove protected backups.

### F18 - MEDIUM - Three of ten advertised read tools fail on the live path

LIVE probe_read_tools.py exercised all ten memory_read tools using the actual
web-researcher MCP definition and one invented fixture. Seven returned non-error
payloads. get_related returned HTTP 422; get_shared_memories and
library_membership returned HTTP 403 requiring memory:admin. None marked the MCP
result isError. See read-tool-live.json. The fixture was version-retracted,
returned 404 afterward, and the active scope returned to zero.

SOURCE server.py:153-156 sends {"query":...} to /v1/memories/connections, whose
ConnectionRequest at memory_api.py:86-91 requires entity, not query. The two
library-read tools at server.py:159-163 target /v1/memories/library/ and
/v1/memories/library/membership, which hit the broad admin permission rule at
security/enterprise_auth.py:467-468. The reviewed memory_api/router source
provides no matching GET library-read handlers. Do not infer a working route
behind the 403: authentication is evaluated before routing.

These READ failures are distinct from deliberately reviewer-gated library
publication. No extra admin permission should be given to role credentials to
make them pass. The existing native enhanced_connections tool uses the correct
entity contract; this finding concerns the separate MCP get_related tool.

Minimal fix: map the MCP graph input to the actual entity contract, implement
scoped, authorised library-read endpoints or remove unsupported tools from the
advertised read family, and keep mutation/publication admin-only. Test each read
tool's payload, not only tools/list or the absence of isError.

## 3. Gap hunt and known-open-item assessment

### Monitoring and alerting

Relevant services have empty OnFailure hooks and no ordinary daemon watchdog.
Automatic restart-on-failure exists for API/index. No tested notification path
for backup failure, near-expiry credentials, stale renewal state, index lag or
low disk was established. This is a basic operational acceptance gap, distinct
from the already-deferred deeper ops metrics. Other monitoring outside the
inspected units may exist; absence of an OnFailure hook does not prove none does.
Recommend a narrowly scoped, tested owner notification route, not a new general
monitoring stack by default.

### Recovery, retention and capacity

Available disk/inode headroom is currently good. Encrypted backup generations and
current-store sizes are protected and were not measurable as ordinary user;
capacity growth/retention cannot be concluded from df alone. The recorded owner
policy preserves generations and forbids automatic deletion; any retention
change needs owner permission. Journald has ordinary built-in rotation/defaults
and uses 388.2M, so "no log rotation" would be an inaccurate finding. Explicit
service log retention and recovery-drill recency remain unproven.

### Dependencies

A fresh OSV query on the three current memory/index/MCP lockfiles returned no
advisories for 47 unique package/version pairs on 2026-11-01. No package was
installed or upgraded. This does not audit the exact protected runtime, store
binaries, OS packages, the entire monolith or optional clients. The older
2026-10-24 dependency-followup.json openly records unresolved full/index findings
at that date; it must not be converted into a current clean-runtime claim.

### Credential and source evidence

The fresh local branch-history scan covered all 17,359 unique blobs reachable
from HEAD. Provider-shaped candidates were test parameter/detection artifacts;
no complete private-key body was found among the private-key marker hits, and
no current fleet JWT exact match or literal JWT was detected. Pattern matching
cannot certify absence of arbitrary passwords or unknown formats. Gitleaks and
TruffleHog were not installed, and were not downloaded. No historical candidate
was tested against a provider. Exact LLM key mode, uniqueness and root rotation
receipt summaries remain owner-only evidence, not failed rotations.

The protected backend's exact deployed source/dependency match was not proved.
A report about current repository source is not automatically a report about
the installed bytes. MCP equality was proved; renewal inequality was proved.

### Gateway restart and renewal interruptions

No restart/expiry simulation was authorised or performed. Provider identity
signatures and Hermes secret-scope refresh exist in source; MCP children are
long-lived and capture their token at startup. The exact renewal-to-child handoff
and restart-mid-renewal behaviour need a targeted acceptance protocol. Do not
resolve this gap by restarting production during an audit.

### Automatic memory semantics

The installed provider implements automatic recall via prefetch and instructs
the assistant to select durable writes through eight tools. It does not claim to
archive every raw turn. Its system prompt, tool schemas and actual current recall
were inspected. "Automatic capture" is model-mediated selected capture, not a
guarantee that every suitable decision will be stored; a catalogue/status check
cannot measure its reliability. The owner-run maximum-context live protocol
remains an honestly declared separate gate.

### Previously declared open items: not new findings

- No main merge: deliberate boundary maintained, not a newly found defect.
- Context7/deepwiki not enabled for fleet: documented deferred enablement;
  completed native qualification was not repeated.
- Structured/DB ingestion and deeper metrics: explicitly future work, not a
  claim that all optional Enhanced Cognee features are installed.
- Long-session maximum-context capture: owner-run protocol, not freshly proven.
- Library publication by ordinary roles: refusal is intentional and passed;
  reviewer/admin credentials must not be handed to bots to make tests green.
- Hosted CI: not independently rerun; local claims do not establish newest-head
  hosted green checks. The supplied documentation admits that limitation.

The engagement is honest about these explicit boundaries. Its headline
"complete" nevertheless overstates the independent evidence and overlooks the
findings above.

## 4. What the owner must do next

Recommended order, not an executed change plan:

1. Review/authorise F01-F04 remediation on a separate task branch, not the
   delivery branch. F01 is especially time-sensitive before scheduled root work.
2. Decide whether shared records may be copied into model-generated summaries
   and which records may be sent to the hosted model. Safest default: owned-only,
   explicitly selected inputs; this limits convenience but preserves controls.
3. Supply the read-only root summaries in [OWNER-CHECKS.md](OWNER-CHECKS.md).
   Do not run the user-writable full verifier as root merely to obtain 60/60.
4. Repair the acceptance scripts, reconcile installed renewal inventory and
   current-profile backups, then run targeted acceptance with explicit cleanup.
5. Keep completed native qualifications and their historical evidence intact.

Alternative: retain the current bounded deployment while accepting documented
risks and pausing new ingestion/analysis workloads. This avoids immediate code
changes but does not remove the root scheduled-job exposure or close readiness.
No pause, timer change or feature disablement was performed by this reviewer.

## 5. Deliverables and reproducibility

- REPORT.md: this independent assessment.
- VERIFICATION-MATRIX.md: full scripted and per-role rows with command aliases.
- OWNER-CHECKS.md: safe, narrow owner-only evidence requests.
- consolidated.txt, fleet-tools.txt, functional-original.txt: original outputs.
- profile-settings.json: selected settings/booleans, never raw profile contents.
- independent-probes.json: manual MCP, paced writes, seeded analysis and cleanup.
- offline-security-receipt.json / offline_security_probe.py: replayed isolated
  ingestion, summary-lifecycle, budget and partial-write reproductions.
- offline-secondary-probes.json / offline_secondary_probes.py: replayed error
  propagation and renewal-contract reproductions, plus installed metadata.
- secret-scan.json and candidate triage: value-free branch scan findings.
- dependency-osv.json: fresh, public-package-only advisory query result.
- Other .txt files: safe system metadata commands and actual outputs.
- audit-summary.json, MANIFEST.json: machine-readable counts and file integrity.

Audit scripts are not daemon installers and must not be run as root. The
invented-data probe is state-changing within its bounded test scope; inspect it
before any future run. Do not rerun tests merely because the scripts are bundled.
