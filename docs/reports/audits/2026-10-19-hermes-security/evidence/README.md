# Evidence and reproduction notes

The summary files contain no credential values or full third-party transcript.
Dependency advisories are dated scanner observations, not a deployment SBOM or
proof that every reported issue is reachable. Python advisory IDs are deduplicated
within each package/version. npm results are matched to actual lock versions.

## Security reproductions

`security_probes.py` exercises synthetic requests against in-process FastAPI apps
and fake stores. It also extracts the registered search function's body for an
isolated SQL-capture check. That one check does not execute its decorator; the
HTTP permission checks separately exercise the actual middleware and permission
resolution, with the final registry dispatch replaced by a recording fake.

The script asserts the observed insecure behavior. Successful execution means
the defects were reproduced, not that the software passed security acceptance.
After a repair, replace these expectations with protective regression tests in
the supported test suite; preserve the audit as historical evidence.

Run from the repository root with its dependencies available:

```bash
PYTHONPATH="$PWD/docs/reports/audits/2026-10-19-hermes-security/evidence/guard" \
PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/python docs/reports/audits/2026-10-19-hermes-security/evidence/security_probes.py
```

The socket guard blocks live IPv4/IPv6 connections. The script removes credential
variables from its own process, supplies synthetic test configuration, disables
dotenv loading and telemetry, avoids TestClient lifespan startup, and uses fake
database/cache/vector calls. It writes results into a new temporary directory;
set AUDIT_OUTPUT_DIR to choose another evidence directory. No real row is deleted.

## Existing unit suite

The required-CI-equivalent suite was run with `tests/unit/ -q`, no pytest cache,
no inherited addopts, and a JUnit report. Real credentials were removed from the
test process and outbound sockets denied. Temporary overlay dependencies supplied
the three missing local packages. Result: 4,183 passed, 2 skipped in 32.78 seconds.
This is Python 3.12 local evidence, not a remote Python 3.11 CI result.

The earlier run failed predominantly because neo4j, psycopg2, and watchdog were
missing; one rate-limiter timing assertion failed once and passed on the second
full run. The passing rerun does not establish that a timing test can never flake.

Raw unit logs were retained in the temporary audit workspace rather than copied
into the report. The checked-in audit output includes counts and run metadata,
not a new coverage percentage or claim that integration tests ran.

## Scanners

- Gitleaks: entire available Git history, full redaction; separate tracked-tree
  snapshot scan. Three large/non-regular snapshot files were skipped and are
  listed in current-tree-scan-skipped.json. The history scan has its own scope.
- Bandit: broad Python scan across runtime, upstream, client, dashboard, and
  ancillary production trees. Nested tests were included by the tool's actual
  exclusions; high findings were triaged rather than equated to exploits.
- Ruff: syntax/undefined-name checks across src, tests, bin, dashboard,
  production, distributed. The independent AST pass checked all tracked Python.
- pip-audit: installed site-packages, explicit production-image override pins,
  and uv.lock package/version union. Multiple lock versions were split into
  three groups because pip-audit rejects duplicate requirements in one input.
- npm registry bulk advisories: all three lockfiles, exact semver matching using
  the maintained semver helper; no npm lifecycle scripts or application installs.
- Dependency resolution: requirements.txt plus pyproject.toml on Python 3.11;
  failed on conflicting structlog requirements, without changing declarations.

Scan tools and temporary dependencies ran outside the repository environment.
Public package-name/version queries were sent to package advisory services.
Source code, private memories, credentials, and family/client records were not
uploaded to those services. No paid tool or service was used.

## Evidence interpretation

`source_sha256` in audit-summary.json binds the primary reviewed files to their
contents. New changes should be retested against the implementation revision;
this report must not be silently relabeled as verification of later code.

Live image, schema, service, multi-worker, restore, and Hermes checks are listed
as outstanding in the audit and implementation plan. Their absence is not a pass.
