# Text-only embedding security repair and launch continuation

24 October 2026, Ubuntu-Workspace source and disposable synthetic runtime.
Installed Ubuntu-Hermes is not changed or qualified by these checks.

## Result and implementation

The restricted memory/index locks now pass an unsuppressed pip-audit with zero
known vulnerabilities. Their previous 37 Pillow findings are removed by
replacing the service's multimodal FastEmbed dependency with a text-only
ONNX/Tokenizer adapter. No forced version metadata or advisory ignore is used.
The memory lock has 34 distributions instead of 42; index has 35 instead of 43.
All retained distribution pins are unchanged. FastEmbed, Pillow and six other
unneeded distributions leave these restricted locks. Optional full-engine
FastEmbed support is separate and is not newly qualified.

The restricted wheel is version 1.2.0. The admitted model remains
BAAI/bge-small-en-v1.5, 384 dimensions, from the MIT-licensed Qdrant quantized
ONNX artifact at repository revision aa8f8b060edb00e03bfdd08813a2949946c8ba55.
All five model/tokenizer files have source-controlled SHA-256 and exact-size
checks. Inference uses the verified bytes, CLS pooling, normalized vectors,
512-token right truncation, bounded CPU concurrency and disabled ONNX telemetry.
Unreviewed models, wrong bytes/types/symlinks/shapes and nonfinite results fail
closed. Runtime startup cannot download a model. Explicit operator preparation
is separate and never replaces an existing file. Existing FastEmbed cache layouts
are not silently rewritten or treated as the new flat cache.

An unchanged isolated FastEmbed 0.9.0 baseline produced vectors from the same
public pinned files. All 30 synthetic comparisons (including retrieval corpus,
queries, empty/case/whitespace/overlong/special-token input) match exactly:
maximum absolute error 0.0. Reference vectors from three cases are retained as
a regression fixture. Service inference in a separate subprocess denies TCP
and imports neither FastEmbed nor PIL. Existing canonical/history data is not
migrated or rewritten. Same vectors permit reuse of a matching existing model/
pipeline only after the installed hash/config checks; real derived-store and
container qualification remains enforced in CI and on the selected host.

The full lock also admits limits 5.8.0, packaging 26.3 and virtualenv 21.14.13,
removing eight virtualenv findings. No other full-lock distribution changes.
The actual core LLM limiter is exercised with the real MemoryStorage and
MovingWindowRateLimiter for enabled/disabled/adjusted-rate cases. Configuration
and logging are isolated in that test; the limits implementation is real. The
[upstream changelog](https://limits.readthedocs.io/en/stable/changelog.html)
identifies the packaging-bound relaxation and removed strategies. This project
uses the retained moving-window APIs, not the removed elastic/etcd strategies.

## Remaining broader dependency gate

Full-lock pip-audit still fails with THREE filelock 3.32.7 findings:
GHSA-v4x8-3wr5-3wq8, GHSA-9vhv-jxww-xfm5 and GHSA-567q-5qvw-pf92.
Their reported fix floor is 4.2.1. Stable LiteLLM 1.106.2, its available
1.107.0rc2 prerelease and litellm-core 1.106.2 retain filelock <4. This was
rechecked against official PyPI metadata. The admitted full-lock LiteLLM 1.106.0
is preserved. The older 1.103.7 resolver alternative is not admitted simply to
clear an audit. No upstream/private-data model call, metadata override, audit
suppression or unsafe downgrade is used. Full legacy release/main merge remains
separate and blocked; the restricted locks use patched filelock 4.2.4.

## Validation and limits

- Consolidated source batch: 4349 unit and 1330 Hermes/operator/recovery checks,
  zero failures/errors/skips; no pytest warnings reported. A separate overlay
  tests limits 5 without changing the original repository environment.
- Clean restricted environment: exact hashed index, MCP and test locks, followed
  by the built wheel installed without resolving extras; pip check passes all
  52 installed distributions. Both root and restricted wheels build and pass
  the wheel-boundary check (no secret/local-store/test files).
- Real disposable PostgreSQL/model batch: 54 passed, zero failures/errors/skips
  and no pytest warnings. Includes actual semantic/paraphrase recall, normalized
  vectors, fresh model sessions, canonical/history/access, signed synthetic
  fleet spaces, index-worker interruption/replay with sink doubles, SDK/MCP,
  key rotation and actual age-encrypted dump/fresh-database restore. The model
  variant restores a separate cache/session and confirms semantic recall and
  other-project denial after database restoration. Sink doubles do not qualify
  actual Qdrant/ArcadeDB/Valkey transports; hosted tests retain that distinction.
- The first database run could not authenticate to the earlier disposable
  cluster: 7 failed/12 errors/3 passed. It did not establish application failures.
  Its private logs/cluster are preserved. A separate freshly initialized
  synthetic cluster was then used; the 22-check run and expanded 54-check run
  pass. No installed/private database or credential was changed.
- Docker cannot execute in this Workspace distro; no integration/mount settings
  were changed. Fresh hosted container/index scans must be read before claiming
  exact-candidate image qualification. Coverage, broad performance/accessibility
  and an installed backend upgrade are not established by this source batch.

Private evidence is retained under /tmp/ec-text-source-batch-20261024,
/tmp/ec-text-runtime-20261024, /tmp/ec-text-unit-overlay-20261024,
/tmp/ec-fastembed-baseline-20261024, /tmp/ec-bge-compatibility-20261024,
/tmp/ec-text-pg-20261024 and /tmp/ec-text-wheel-20261024. Model bytes, synthetic
database generations and failed-attempt logs remain private/local. Original
source and locks were preserved under .archive/2026-10-24_text_embedding_security.
Sanitized hashes/counts are in remediation-evidence/2026-10-24-text-embedding-security.json.

## Hosted continuation and portability repairs

The first hosted run on d2bb1ccfd61960428dce9905ed21986678310a69 passed the
restricted dependency audit, but the combined memory lane reported 51 failed,
1360 passed and 5 skipped. Forty-nine failures came from fixtures hardcoding
UID 1000 while GitHub's temporary files belong to its actual runner. These
fixtures now use their actual effective UID; production ownership guards stay
unchanged. A one-shot helper also left the pytest process umask at 0077,
silently making a later deliberately public negative fixture private. A scoped
fixture now restores the process mask between qualification cases. The actual
cache permission rejection is not weakened.

The cross-machine golden-vector assertion observed a maximum component
difference of 0.00021559 on the first case, while strict same-host restart
checks passed. The exact 30-vector baseline equality above applies to Workspace.
Quantized CPU kernels can vary; [ONNX Runtime documents architecture-dependent
integer saturation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html#when-and-why-do-i-need-to-try-u8u8).
The stored cross-machine reference now requires BOTH maximum component error
<=0.001 and cosine >=0.99999. Same-host restart still uses the original strict
tolerance, and model/tokenizer hashes, dimensions, semantic ordering and scope
checks remain enforced. This is a numeric portability bound, not an assertion
of bit-for-bit equality across CPUs. Fresh hosted results remain necessary.

After these fixture repairs the complete combined memory selection passes
locally: 1411 passed, zero failed/errors and 5 explicit skips (Node/Go/Rust real
clients, browser and external derived stores). Those require their separate
hosted jobs and are not called passes. The source operator/cache selection also
passes 286 checks. Earlier independent source/real-DB counts remain valid.

The first hosted default-stack job built the restricted image and passed its
reduced-runtime smoke, but the image's worker did not catch up. The new model
cache had operator-only 0700 traversal, which cannot serve the non-root container.
CI now explicitly grants read/traverse for that NEW public-only cache and exact
pinned public files; private settings/keys are untouched. A bounded container
state artifact records exit/OOM/status without configuration or raw logs on
future failure. Installed-host cache access and exact-image/store acceptance
are still required; no cause beyond the observed cache incompatibility or
successful image qualification is inferred.

## Hosted accepted memory candidate and final type repair

On cc6dc226f85c2d87fe8a2878494af1a2dc1d58db, both
[project memory qualification](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/40055060743)
and [canonical memory stack qualification](https://github.com/vincentspereira/RNR-Enhanced-Cognee/actions/runs/40055060862)
PASS. The combined memory XML records 1411 passed, zero failures/errors and five
explicit separate-client/browser/store skips. The actual-store XML records 35
passed, zero failures/errors/skips. Actual restricted API/worker images pass
semantic/source-linked recall, restart/backlog recovery, scope, reviewed sharing
and revocation, correction lineage and retraction. Reduced-runtime smoke passes.
Required CI and the canonical browser/both frontend jobs also pass at that head.
These are hosted synthetic results, not the installed Hermes fleet.

The exact built restricted image has zero HIGH/CRITICAL findings. Its complete
inventory retains 37 other findings: 26 MEDIUM, 10 LOW and one UNKNOWN. The
UNKNOWN ca-certificates DSA-6572-1 has a reported Debian fix at
20250419+deb13u1; the other 36 have no reported fixed version in that scan.
No inventory or advisory is hidden. Patched Python certifi is already in the
service lock; that does not erase the separate base-image trust-store finding.
Keep these image findings visible for release review and subsequent base-image
maintenance. Full legacy filelock and installed gates remain independent.

The broader Python-3.11 CI still fails. Its unit/system run records 34 failed
and 4408 passed with 80.90 percent measured coverage; passing coverage does not
close failed tests. Failures include missing optional pymemcache/locust test
dependencies and historical legacy MCP fixtures/contracts. It is not the
passing restricted eight-tool qualification. The broader type gate separately
found three no-any-return errors in provenance and encryption. Source now
requires a string database update acknowledgement and bytes from both crypto
backends, failing closed on unexpected types. No cast/ignore or type-check
suppression is used. The unchanged 29-module blocking type selection passes
with mypy 2.4.0 using the matched installed dependency environment. A first
isolated mypy invocation without that environment reported four unrelated
missing-import-derived Any errors; both logs are retained and not conflated.

After the type guards, the entire source batch again passes 4349 unit and 1330
Hermes/operator/recovery checks with zero failures/errors/skips. Targeted real
crypto/provenance tests pass 79 checks. Fresh encrypted database/model recovery
and wheel checks cover the final source separately. No broader all-green/main
merge claim is made; fresh hosted results must be checked on its published head.

## Exact remaining execution boundary

The owner-run completed version-4 record remains preserved; its earlier native
turn completion cause is unresolved. Installed current database/index recovery,
interrupted/unattended renewal and long-running credential reload, actual fleet
inventory/OS boundaries/admission, Windows real collection/remote recovery,
private exposed-credential disposition and exact release acceptance still need
their scoped evidence. There is no system-wide launch claim.

Use [the consolidated Ubuntu-Hermes continuation](../../../runbooks/HERMES-SYSTEM-WIDE-LAUNCH-CONTINUATION.md)
to implement and qualify the host work in one local agent session, grouped into
two batches. It explicitly reuses prior passes and forbids replaying the finished
invented record. No Workspace-to-Hermes filesystem access is requested.
