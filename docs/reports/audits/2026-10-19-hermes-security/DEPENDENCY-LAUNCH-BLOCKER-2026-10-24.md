# Dependency launch blocker - 24 October 2026

Latest source checkpoint: [text-only embedding repair](TEXT-EMBEDDING-SECURITY-2026-10-24.md) closes the
restricted Pillow gate (zero known lock findings) and admits the reviewed
limits/packaging/virtualenv update. Full-lock findings are now three in filelock.
Installed host/fleet gates remain open. Historical results below are retained.

Recommendation: continue only the approved invented-data qualification while
resolving the restricted embedding runtime's dependency conflict. Do not admit
private/everyday fleet use or merge a release with the enforced security gate
failing. Do not ignore advisories or force incompatible dependency metadata.

Latest compatible-source checkpoint: the full lock now has 11 findings instead
of the initial 17, after patched Black, pypdf, setuptools and an aligned tracing
cohort were resolved without any other distribution changes. The restricted
index lock still reports 37 Pillow findings. Stable LiteLLM's filelock cap and
the limits/packaging/virtualenv constraint prevent admitting all remaining
patches together. No downgrade, incompatible metadata override or installed
upgrade is admitted. See [canonical effects and current security evidence](CANONICAL-EFFECTS-AND-SECURITY-2026-10-24.md).

The hosted required check passed on source
06037eb7b6d60eecc3be3921c3012d86d8e56a75. Both frontend qualification lanes
and canonical-browser also passed at the observed checkpoint. Separate memory,
default-stack and broader CI/security lanes did not all pass. These results are
separate from the green local source and disposable PostgreSQL checks.

## Confirmed security findings and bounded source repair

[Memory qualification run 40043837772](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/40043837772)
stopped in its enforced dependency audit before qualification tests. It reported
37 Pillow 12.3.0 advisories and identified Pillow 13.0.0 as the fixed version.
The original build-lock audit passed. A fresh local index-lock audit independently
reports the same 37 advisories in one package. The finding is not an observed
Hermes conversation failure, and no exploit or private-data loss was established.

Pillow's [official 13.0.0 release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
describe the security fixes and incompatible API changes. The selected full
runtime uses Python 3.12, which satisfies Pillow 13's Python >=3.11 requirement.
The full requirements input and hash lock now use Pillow >=13,<14 / 13.0.0.
Only the Pillow distribution block changed in the full lock; all unrelated
package pins remain preserved. Existing runtime packages/deployments were not
upgraded. Broader optional/core Python 3.10 support is not qualified by this fix.

In the separate test overlay, Pillow 13 PNG encode/decode/resize smoke passes,
the installed-package compatibility check passes, and all 4344 unit tests pass
with zero failures/errors/skips and no reported pytest warnings. The original
runtime and the failed-attempt evidence are retained.

At the initial Pillow-only checkpoint, an unsuppressed full-lock audit retained 17
advisories in six other packages: black, filelock, opentelemetry-api, pypdf,
setuptools and virtualenv. This is not a clean full-release audit. The audit tool
also reported cache-deserialization warnings before completing with findings;
those warnings are not hidden or converted into a clean result. The subsequent
compatible-source checkpoint above supersedes that count for the current full
lock; filelock and virtualenv retain 11 findings between them.

## Why the restricted memory runtime remains blocked

The restricted memory/index dependency set uses FastEmbed 0.9.0. Its
[current official metadata](https://github.com/qdrant/fastembed/blob/main/pyproject.toml)
requires Pillow <13 for Python 3.10-3.12, 3.13 and 3.14. Resolver checks against
all three candidate runtime versions reject a Pillow >=13 floor. A Python
version change alone therefore does not resolve this incompatibility. No newer
compatible release was admitted by the resolver at this checkpoint.

The unsuccessful restricted-service input was preserved privately and the
original valid service input restored. The memory/index lockfiles retain their
actual installed dependency versions and their security gate remains red.
No dependency overrides, fake package versions, audit ignores, removed checks,
global settings changes or installed service upgrades were introduced.

Resolve this through an upstream compatible release or a deliberately reviewed
compatibility patch/replacement with reproducible source/package provenance,
dependency checks, real configured BGE embedding comparisons, index/recall and
restart/recovery evidence. A metadata-only forced installation is not that
qualification. Replacing the encoder must preserve or explicitly rebuild derived
indexes; the canonical database and history must remain protected and intact.

## Safe next work

The consolidated native candidate command remains useful for the next invented-
data conversation/access checks. It changes neither the running backend runtime
nor the existing pilot/default provider. Keep the other batch-2 tasks explicit:
installed interrupted/unattended credential renewal, current database recovery,
real Windows/remote collection, actual fleet identity/secret boundaries and
remaining release/private credential-review requirements. Do not ask the owner
to repeat the already passed source, custody, manual profile restore or timer
steps merely because the security gate is inherited by later stages.
