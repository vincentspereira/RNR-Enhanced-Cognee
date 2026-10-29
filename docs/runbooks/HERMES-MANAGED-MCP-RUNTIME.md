# Restore native managed MCP launcher support without fleet activation

29 October 2026 addendum: the retained Fetch HTML-extraction failure was
root-caused to a stale probe expectation, not the server. The served
example.com copy was reworded, and with Node present Mozilla Readability moves
the page heading into article metadata, so the earlier default-mode phrase
check could not pass even though conversion was correct in both extractor
paths. The probe now verifies conversion structurally (fixed URL prefix, HTML
actually converted away, simplification-failure marker absent, non-empty
body). The retained frozen build passed the full probe again, including the
new default-mode check: initialize, one-tool catalogue, two private-address
refusals, raw retrieval and converted-Markdown extraction. Thirty-eight
focused tests pass; native 3.14.7 compilation passes. Sanitized receipt:
`2026-10-29-fetch-html-extraction-qualified.json`. This qualifies the
ordinary-owner candidate build only; native Hermes Fetch binding remains
unqualified until the protected runtime has its managed PM components and the
binding group runs. The earlier failure record is preserved, not replayed.

28 October 2026, Ubuntu-Hermes. Delivery remains exact
21abf4857ca8dce8e0a3aafc725266c8d3754529. The protected Filesystem/REA component
passes are complete; do not replay them. Native Hermes launcher binding is a
separate gate. The owner confirms the concurrent 40-bot work is preparation
only, with no bots started. Read-only inspection found no processes under the
43 restricted accounts and no bot/fleet user services; the six backend services
were running. Older fleet roster/checklist status is dated 8-9 October and must
not be presented as current acceptance. Private preparation contents stay local.

## Confirmed packaging defect and independent preparation

The protected release is
/opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1. Its public manifest
selects python/ as the managed store, but its Python fact is only entry='.';
uv is absent and pm-runtime/pm-runtime.json does not exist. Native bare npx/uvx
resolution goes through PM, so finding a shell executable does not qualify it.
The original restricted-runtime preparer omitted these native PM components.
Existing source/interpreter/program-recovery evidence remains valid in its
recorded scope; full native managed launch was never established by that proof.

An ordinary-owner build uses unchanged public PM sources, the original pinned
tool lock and a NEW empty HOME/store. Supported PM operations prepare genuine
Python 3.14.7+20260901 and uv 0.12.3, build PM's independent locked environment,
and install Fetch 2026.10.24 in a separate frozen environment. No raw pip/uv
mutation of Hermes or source-profile discovery is used. The reviewed Fetch
project/lock is retained at integrations/hermes/deployment/fetch-candidate/;
future builds validate and use it frozen rather than resolving new dependencies.
Its lock SHA256 is
78647ee83c9b32ba3cd170b75367a7d171818b67e1dc4d929962d7463f095fdc.
The Fetch wheel SHA256 matches primary PyPI metadata:
3dbcb37801a037b29d486f791328a38354f6b2a8ab54ada8064ecf7268a826bf.

The native unchanged seal_pm_runtime helper seals a NEW PM payload. Its retained
464,097,280-byte archive SHA256 is
68a0325fec51b2922b379cec51b8d80a202f2e7783e3c8561154d8a9eb52f521.
All 5,005 members passed bounded admission and disposable restoration. The
relocated resident manager/imports and native uvx resolver PASSED in a fresh
ordinary-owner user/network namespace with zero capabilities and no profiles.
This is not execution under the actual main restricted UID.

Initial local validation refusals are retained: an unused native empty build
lock and the pinned 248,404,536-byte libpython required precise format/size
admission. The build lock is never published into the live store. A local
setpriv bounding-set request failed before Python ran; its existing restore
was reused, all 823 copied public source hashes rechecked, and the corrected
proof explicitly verified actual zero effective/inheritable/ambient capabilities.
No passing component, package acquisition or complete restore was replayed by
that finish. No original artifact or failure was overwritten.

Fetch's independent ordinary-owner stdio probe PASSED initialize, its one-tool
catalogue, unchanged localhost/metadata-address refusal and raw example.com
retrieval. A preceding default HTML extraction did not return the expected
content; preserve that failure. HTML-to-Markdown extraction and actual native
Hermes Fetch binding remain UNQUALIFIED. No private data or profile credential
was supplied to any Fetch request. No --allow-private-ips/ignore-robots guard
change was used. Hermes' vendor launcher and malware checks remain unchanged.

The primary OSV querybatch API reported zero findings for the 50 exact installed
public distributions in these NEW environments (46 Fetch, four PM) at
2026-10-28T20:01:18.580122+00:00. This is a point-in-time package advisory check,
not a full audit of the original Hermes runtime or its npm packages. Existing
full legacy filelock/LiteLLM and broader CI failures remain visible.

## One protected installation and identity-check group

The agent's sudo check still requires a password in the owner's terminal. Run
this one prepared command there; enter the password only at sudo's local prompt:

```bash
sudo /usr/bin/python3 -I /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment/install_managed_mcp_runtime.py
```

The exact live public preflight PASSED without root: four protected hashes,
five retained public package records, expected missing components and inactive
restricted accounts. The installer checks those facts again, and again before
publication. Any active restricted bot or differing existing component refuses
installation. It never stops a bot to make the guard pass.

The operator freezes its own public source, receives the exact archive from an
unprivileged owner child and verifies its full hash/length. Root never walks a
profile, imports a package dependency or executes downloaded code. Full bounded
archive validation precedes manual extraction into NEW protected staging.
Traversal, duplicate entries, hardlinks, special files, escaping/cyclic links,
writable/privileged modes and unreviewed tool roots are refused. Only the exact
pinned large libpython member gets its exact larger size bound. Original public
facts are retained before publication. Only two NEW tool directories and the
NEW pm-runtime directory are added; genuine tool facts replace the incomplete
Python fact and add uv while retaining all four other package facts. The old
Python, venv, code, manifest, source profiles and unit definitions are preserved.

A fresh empty-home child under actual UID 992/GID 984, zero capabilities,
no-new-privileges and a private network namespace then verifies resident PM
imports, full pinned tool digests and the actual native uvx/npx selection path.
Lazy installation is disabled. No MCP server, model, memory API, platform adapter
or bot is started. No credentials, signing/recovery keys or policies are read.
The result remains separate from native MCP-server binding and fleet acceptance.
No backend runtime or service restart occurs.

Return the final JSON only. Repetition returns the retained summary; it does
not reinstall or automatically retry a failed attempt. A partial publication is
reported explicitly with its checkpoint and retained evidence; it requires
reconciliation. Existing files and failures are never cleaned up automatically.
The public archive is also retained as recovery input. The main service/program
recovery checks are not replayed and this does not supersede their scope.

Thirty-seven invented-fixture regression tests PASS with no failures/errors/
skips/warnings. The five helpers compile with native Python 3.14.7. Protected
installation/UID-992 execution remains PENDING until an operator result exists.

## Remaining launch gates

- Actual native MCP binding: all six preserved definitions, Fetch extraction and
  remote acceptance, full main tools/context and current served capability.
- Production bot routing and launcher binding, with the two deferred existing
  bindings resolved and preserved scopes reviewed.
- Admitted production credential renewal/reload and dispatch qualification.
- Final fresh main-state reconciliation, backup/rollback membership and one
  concrete fleet-switch review after all applicable gates pass.

Forty candidate renewal/reload/recovery and 41 daily backup proofs remain
preserved. The implementation/qualification batches previously completed in
their recorded scope; they do not establish these later production gates. All
admission policies remain disabled. No fleet activation or main merge is claimed.
