# Remediation evidence index

Latest 20 October continuation: `2026-10-20-canonical-final-required-ci.json`
records a fully passing hosted run with 4,285 unit, three schema, ten settings and
64 canonical checks, zero failures/errors/skips. `2026-10-20-canonical-fleet-qualification.xml`
records 77 local opt-in checks. Fleet, ten-minute load, native-package and exact
unsuppressed hosted-image scan evidence use the same dated prefix. The image
security gate remains failed; these results do not authorize private activation.
The earlier undated files below are preserved historical checkpoints.

These files describe local checks after implementation. The sibling `../evidence/`
folder is the original audit baseline and has not been regenerated.

- `unit-suite.xml` and `unit-suite-result.json`: earlier credential-scrubbed,
  network-denying unit run; 4,245 passed and two skipped.
- `qualification.xml` and `qualification.log`: 52 real database/model/provider,
  migration, source, key-rotation and capability checks.
- `legacy-schema-qualification.xml`: three actual installer/upgrade fixtures.
- `upstream-security.xml`: ten settings/ownership/import-preservation checks.
- `full-runtime-protocol.log`: actual built full-image imports, production tenant
  enforcement, registry and MCP protocol check. Earlier import-only and pip-check
  logs are retained snapshots and have narrower coverage.
- `full-runtime-source-check.log`: critical runtime source-hash comparison.
- `built-image-hardened-smoke.log`, `built-image-named-keys-smoke.log` and
  `restricted-privilege-mode-check.log`: actual restricted HTTP/key/privilege checks.
- `container-scan-summary.json`: exact scanned image identities and advisory
  matches. Unresolved findings are retained, including the version-matched Cognee
  advisory despite its tested source backport.
- `tool-policy-inventory.json`: all 122 legacy tools have declared permission
  policies. It does not establish complete legacy side-effect/storage coverage.
- Client test logs, lock-audit reports, syntax/lint reports and secret-diff scan
  retain their stated scope. A clean new-diff scan does not revoke historical keys.
- `remediation-manifest.json`: source and evidence hashes for this checkpoint.

All service/database requests used invented records and disposable test stores.
The earlier local-image packaging exception is recorded in F32; it remains a
separate privacy/preservation issue. No private Hermes profile was activated.
No unit or smoke result alone grants production or commercial readiness.
