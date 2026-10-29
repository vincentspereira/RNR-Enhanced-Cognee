# Branch consolidation and release review - 22 October 2026

Recommendation: prepare one delivery-to-main pull request now, retain the five
strict required checks, and merge only after the unresolved release and owner/
installed-host prerequisites pass. The owner has authorised consolidation and
conflict resolution, with earlier merge approval conditional on working code
and completed checks. No bypass, force push or branch deletion is required.

## Remote branches and ancestry

GitHub branch tips and comparison API were checked on 22 October; explicit local
commit ancestry agrees. The initial reviewed delivery anchor is
bbfa0eea94664d46afa381107b244df59c632465. This review's certificate correction and
native receipt are subsequent changes on the same delivery branch, not a new
deployment or a change of the protected Hermes application revision.

| Remote branch | Reviewed tip | Unique commits absent from the delivery anchor |
|---|---|---|
| main | e25bd6356e38970c525e0258bdac983cd4079d29 | 0; delivery is 82 commits ahead and zero behind |
| codex/hermes-ubuntu-deployment-20261020 | eca54b0c274b8c00f9a69ea3d5c68713cf766853 | 0; already an ancestor, delivery is 53 ahead |
| codex/hermes-ubuntu-deployment-protected-20261020 | 101ccfe62ae8970a970fde0508f6e05b1e4acd4e | 0; already an ancestor, delivery is 37 ahead |
| codex/hermes-memory-hardening | bbfa0eea94664d46afa381107b244df59c632465 | Maintained combined delivery branch |

Do not independently merge the two old deployment branches again. They carry
history/qualification evidence already included in delivery. Preserve all branch
names and recovery points. A source merge does not automatically deploy code,
copy private configuration between environments or connect forty bots.

A local all-ref fetch encountered an internal app capture ref referring to a
missing object. No ref/file was deleted or repaired by guessing. Remote tips and
GitHub comparison were checked directly, and explicit commit ancestry remains
readable. GitHub pull-request checks use fresh checkouts. This local capture-ref
issue is separate from code conflicts and remains a local maintenance concern.
The existing untracked token-renewal helper was preserved and excluded.

## Current enforced release blockers

Main requires five trusted GitHub Actions checks, strict/up-to-date matching,
and administrator enforcement: Required CI (unit tests), default-stack,
canonical-browser, frontend (cognee-frontend), and frontend
(dashboard/nextjs-dashboard). Review requirements and conversation resolution
remain intact. No administrator override or merge has been attempted.

Both frontend lock-only audits were refreshed with native Linux Node 24.18.0:
each reports five HIGH matches in the braces/micromatch/fast-glob/Next lint
dependency chain. The official
[braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) still lists
no patched version. The existing source backport is not advisory clearance.
Do not remove lint coverage, disguise a package version, suppress the audit or
accept the audit's unsupported Next configuration downgrade to clear this gate.

The [latest delivery container run](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/39812458815)
at bbfa0eea failed its unsuppressed image scan after the functional steps. Its
reported language-package totals are 20 blocking matches: 16 HIGH and four
CRITICAL, in certifi 2026.10.18 and Pillow 12.3.0. Those results supersede the
older zero-HIGH/CRITICAL image receipt. The JSON artifact could not be downloaded
from its storage host in this session (network unreachable); these counts and
versions are from the actual hosted scan log, not a newly downloaded JSON scan.

## Certificate correction and actual local verification

The [certifi advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) requires
2026.10.19 or later. Added that floor to the restricted service/MCP inputs and
full pip requirements, then recompiled the memory, index, MCP, full and optional
unit locks with hashes. Each lock's only package-version change is certifi
2026.10.18 to 2026.10.19; no unrelated upgrades or downgrades were retained.

Created a separate disposable Workspace runtime from the hashed index/MCP/test
locks. The 59 installed packages pass dependency consistency. Actual certifi
2026.10.19, FastEmbed 0.9.0 and Pillow 12.3.0 import with the memory API/index
modules; a public PyPI HTTPS request using the new bundle returns HTTP 200.
No model was loaded, no private configuration read and no provider called.
The six focused helper suites in that new runtime pass 114 tests, zero failures,
zero skips and no reported warnings. Coverage/full-suite success is not claimed.

The fresh hashed index audit confirms certifi 2026.10.19 has zero reported
advisories, but reports 34 Pillow advisories and exits unsuccessfully. An initial
audit emitted cache-deserialization warnings; the affected entries were ignored.
Repeating with a separate fresh cache confirmed the same 34 Pillow findings,
all listing 13.0.0 as the fix, and zero certifi findings, without those warnings.
These package-audit counts are not the severity-filtered Trivy count above and
must not be added together. The security gate remains red.

The universal uv lock is preserved. Its attempted targeted refresh also changed
the existing tenacity resolution and downgraded optional google-genai; that
candidate was retained privately for diagnosis and not accepted. The current
universal optional-provider lock still needs its own constraint/security review;
the five corrected pip locks do not claim to clear every optional installation.
No existing developer, protected backend or Hermes runtime was upgraded here.

## Remaining dependency and native work

[Pillow 13.0.0](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
contains the published corrections, but the latest published
[FastEmbed 0.9.0 metadata](https://pypi.org/pypi/fastembed/0.9.0/json) requires
Pillow <13 across its supported Python ranges. A compatible dependency release
or an explicitly maintained and genuinely tested dependency change is needed.
Do not use --no-deps, edit package metadata to invent compatibility, remove
image inventory from the scan, or strip required packages to hide the finding.
No current-model incompatibility is assumed; forcing an unsatisfied dependency
is not qualification. Broader legacy image/optional-extra evidence remains
separate and current findings must stay visible.

After dependency remediation, run all required hosted checks on the final exact
candidate and review their evidence. The new protected Hermes tools1 generation
still needs restricted startup/tool execution/access checks, followed by scoped
provider credentials, the authorised model route, actual selected-memory and
cross-scope tests, backup coverage and staged fleet admission. Current owner
credential review/revocation and any remaining recovery acceptance also stay
explicit. The successful 43574-file preparation does not complete these gates.

No automatic private-data activation, default-profile switch, bot deployment,
Windows backup/task change or main merge is part of this review.
