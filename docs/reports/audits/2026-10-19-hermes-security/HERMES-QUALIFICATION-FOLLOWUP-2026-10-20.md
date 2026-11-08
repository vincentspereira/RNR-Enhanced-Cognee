# Hermes qualification follow-up - 20 October 2026

The complete qualification suite now passes all 78 tests with zero failures,
errors or skips inside Ubuntu-Hermes. The earlier four skipped checks were
executed against real clients and Chromium, not removed or relabelled.

## Complete suite

Prepared isolated native toolchains and caches under `.qualification-tools`:
Go 1.27.3, Rust 1.99.1, Chromium 156.0.8078.4, with the existing native Node
24.18.0/npm 12.0.1. Go artifacts and the Rust installer were checked against
their published checksums. No global shell configuration was changed.

Compiled the locked Node and Rust clients and race-enabled Go client. Installed
the dashboard from its existing lock, applied its existing source backport via
the build hook, built the actual frontend, and verified native headless Chromium.
No package lock, dependency version or advisory suppression was changed.

Enabled both `RNR_QUALIFICATION_CROSS_LANGUAGE` and `RNR_QUALIFICATION_BROWSER`
with explicit disposable PostgreSQL, authenticated index stores and an offline
model cache. The three real language clients exercised the live canonical HTTP
contract, and Chromium exercised the built dashboard against real PostgreSQL.
The original tests and their assertions remain present.

Added `tests/qualification/run_complete.py`: a reproducible full-suite entrypoint
that enables those checks and rejects any skipped test, failure or error.
It also rejects missing build/runtime prerequisites and retains private logs,
XML and fixtures in a new directory. See
[COMPLETE-MEMORY-QUALIFICATION.md](../../../runbooks/COMPLETE-MEMORY-QUALIFICATION.md).

The original 77-test lane passed twice during this follow-up. The final lane
also includes a regression for actionable optional graph-span validation and
passes all 78 cases. Sanitized counts, test timings, runtime versions
and the XML hash are recorded in
[the complete qualification evidence](remediation-evidence/2026-10-20-hermes-complete-qualification.json).
Raw logs and fixtures remain in the existing private synthetic runtime.

The dashboard install still reported five HIGH development-dependency findings
and an ESLint deprecation warning. They remain unsuppressed. A 78/78 functional
qualification does not clear those separate release findings.

## Local capture investigation

The existing local server's actual API schema, hardware report, loaded-model
metadata and memory estimator were inspected. No model files or Windows or
Workspace filesystem were accessed. Credentials and full request prompts remain
private; a temporary loopback diagnostic recorded only tool names and whether
the provider policy was present, then restored the synthetic profile settings.

The diagnostic established that Granite received the capture policy and all
eight provider tools. It supported explicit native function calls but omitted
automatic saves. Hermes subsequently detected its actual 8,192-token window
and correctly refused initialization below the 64,000-token requirement.

The existing cached Granite was reloaded at a real, enforced 65,536-token
window using a measured CPU/GPU placement plan, one slot and q8 KV cache. Its
automatic-save check still failed, so it was not marked qualified.

The existing cached Qwen 9B alternative was also tested at an actual
65,536-token window. It omitted saves on explicitly fictional qualification
input and on a natural declaration of an ongoing project decision. An isolated
second-profile attempt made repeated reads but did not complete the required
save. These failed traces and restored settings are retained.

Strengthened the provider policy and tool description to require a completed
save before the final answer for a new durable item, distinguish an unrelated
project's decision from a duplicate, and state that recall alone is insufficient.
Credential exclusion, ambiguity clarification, current-version checks, scoped
identity and raw-transcript exclusion remain enforced. Both synthetic plugin
copies were preserved before update. The real 78-test lane passes this source.

A real 27B write attempt exposed a separate repair: the model supplied a graph
endpoint `eleven days` while the text said `eleven-day`, and the cited span did
not contain both endpoints. The server correctly rejected it; the original
generic error did not tell the model how to repair the optional field. Added
local character-span/endpoint validation and a static, non-sensitive
`validation_hint` explaining how to fix or omit optional links and retry the
same key. The server remains authoritative and its grounding rules were not
relaxed. Valid links are forwarded unchanged. A regression verifies rejection
before transport, no echoed content, same-key retry after an uncommitted invalid
request, correction rejection, and valid-link forwarding with a fresh identity.

The owner's configured, cached `unsloth/Qwen3.8-27B-GGUF` route now passes
all five actual Hermes model scenarios in `enhanced-cognee-test-two`, with no
cloud fallback and an actual enforced 65,536-token context. A natural statement
of a durable decision triggered `enhanced_remember` without an explicit save
request. A separate session recalled and fetched it; a clear correction created
version 2; uncertainty triggered `enhanced_clarify` without changing it; an
invented credential was refused without a write. Independent canonical inspection
confirmed encrypted versions 1 and 2, the original eleven-day interval and
current nine-day interval. Neither the fixture nor invented credential appeared
in builtin notebooks. Raw model traces and unsuccessful attempts stay private.
See [local capture evidence](remediation-evidence/2026-10-20-hermes-local-capture.json).

After qualification, preserved the second synthetic profile's original files
and selected this existing local route there persistently. Its scoped memory
token was retained, its existing local model credential was reused, and no
service signing/encryption/recovery key was copied. Verified the selected model
and served context through the actual endpoint. Everyday configuration and
credentials were hash-checked unchanged. The original Granite test profile and
all everyday/bot profiles retain their model settings. Both synthetic provider
plugins have the repaired source.

The server estimate is 21,582,035,667 bytes total, including 4,571,069,275 bytes
on the 6 GiB GPU, with 14 GPU layers, one slot and q8 KV cache. Speculative
decoding and vision are disabled. Eight context checkpoints add 1,255,145,472
bytes of host memory. Hermes guards remain enabled; no context override replaces
served capacity. Reasoning is disabled for this qualified text-only route.

This is a functional qualification with a substantial performance limitation:
the five scenarios took 294, 387, 299, 244 and 196 seconds respectively, with CPU
offload. It is not a claim of fast interactive use or fleet capacity. Granite
and Qwen 9B remain unqualified for automatic capture. Earlier failures on
explicitly fictional wording remain evidence of model variability. These five
selected cases do not prove universal capture or secret recognition.

## Final verification and delivery

Source baseline: `7fb2e2d721fa5d64a65c409f6305a5562f1316c9`, branch
`codex/hermes-ubuntu-deployment-20261020`, inside verified Ubuntu-Hermes.
The final complete run passed 78 tests in 50.231 seconds, with zero failures,
errors or skips. Targeted provider/operator checks passed 15 tests; installed
provider lifecycle checks passed 11. Both installed synthetic plugin hashes
match the repaired source. The live schema-3 service reports semantic retrieval,
source-linked graph availability, a running index worker and zero pending events.

`git diff --check` and ASCII checks pass. Gitleaks 8.30.1 scanned the nine
proposed public files with zero leaks. Private instructions, profile originals,
raw traces, credentials, toolchains and retained runtime fixtures are excluded
from publication. This follow-up is delivered on the separate deployment branch;
no main merge is authorized by these results alone.

## Unchanged admission limits

This follow-up does not establish protected OS service identities, scheduled
root-owned backups, owner recovery custody, exposed-key revocation or complete
release acceptance. Everyday and real-bot profiles remain unactivated. Main is
not merged. The prior deployment report remains historical evidence of its
specific revision, tests, failures and pending gates.
