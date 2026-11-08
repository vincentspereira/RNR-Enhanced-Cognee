# Findings discovered during implementation

Date: 19 October 2026. These add to the original F01-F27 audit, rather than
rewriting its baseline. Repairs remain local; no private Hermes activation.

## F28 - Critical when the upstream API is exposed: global settings mutation

The full-image scanner identified CVE-2026-58473 against the fork's upstream
Cognee version. Source review confirmed that settings GET/POST required an
ordinary authenticated user, but did not require an administrator. The general
authentication helper can also supply a default administrator in optional-auth
mode. Global LLM/vector settings therefore require a distinct strict dependency.

Implemented: settings reads and writes now require a real active authenticated
administrator, even if ordinary optional authentication is configured. Public
registration defaults off. Settings return a constant mask for configured keys,
without revealing their prefix or length. Existing fork version metadata is
unchanged; it is not relabelled to make the advisory disappear.

Evidence: real FastAPI settings-router tests cover anonymous rejection, ordinary
user rejection, administrator reads/writes, no backend mutation on denial,
secret masking and default-off registration. An additional request retains the
actual authentication dependency and confirms anonymous callers cannot acquire
the default administrator. Database access is replaced for that request, and
provider writes are mocked. No real provider was configured.

The upstream history includes both a security change and its revert; do not
blindly copy a commit referenced by an advisory. The reviewed source and local
regressions are the authority for this backport. References:
[upstream issue](https://github.com/topoteretes/cognee/issues/3084),
[referenced revert](https://github.com/topoteretes/cognee/commit/10971db1b0bd97e88f96bd2a9ffb3edb7b22bcd0).
The full scanner can continue flagging the older version after a source backport.
Packaged backport evidence and any VEX decision remain separate release work;
there is no broad advisory suppression. The restricted service does not ship the
upstream `cognee` package or expose these routes.

## F29 - High: configuration lookup lacked an owner condition

`get_user_configuration/{config_id}` passed an ID to a query that checked only
that ID. An authenticated user knowing another configuration's ID could obtain
its configuration, potentially including private credentials or endpoints.

Implemented: the route passes its authenticated owner's ID. The shared query
requires an explicit owner and applies both ID and owner conditions. Missing
owner context fails; another owner receives no record. An actual in-memory
SQLite fixture proves owner reads and cross-owner denial without using real data.

## F30 - Preservation and configuration side effects during import

Importing Cognee previously loaded a nearby `.env` with override enabled and
automatically pruned older files in the ordinary user log directory. During the
upstream test work, one deletion of an older log was observed. See
[the implementation incident record](IMPLEMENTATION-INCIDENT.md).

Implemented: automatic log deletion is disabled; the compatibility cleanup hook
preserves all files. Import-time dotenv loading requires explicit enablement and
cannot override existing environment settings. Qualification runs disable file
logging and dotenv loading; image/CI defaults do the same. A regression fixture
confirms all existing log files survive the cleanup hook. Operational retention
and erasure remain explicit owner decisions.

## F31 - Container findings beyond release-lock dependency scans

The Debian 12 images contained additional OS matches, an old global/venv pip,
and the upstream Cognee advisory. Moving to the official Python 3.12.15 Debian 13
base removed the two critical OS matches in the first restricted-image scan,
but left high OS findings and exposed advisories in components vendored by pip
26.2.1 itself. Installing newer standalone urllib3/setuptools would not replace
those vendored copies.

Implemented: hashed bootstrap tools during builds; dependency compatibility
checks before finalization; the final runtime removes the unused installer and
its vendored components. This removes the actual tool and its component metadata,
not just a scanner record. Package installation requires an image rebuild.
The restricted API is then rebuilt, exercised and rescanned. Unfixed OS findings
remain visible and require applicability/mitigation review before private use.
Scanner counts are package/advisory matches, not individually demonstrated
remote exploits. No `ignore-unfixed` or general ignore list is used.

## F32 - High before publication: local stores could enter full build artifacts

The checkout contains an extensionless local database at
`cognee/.cognee_system/databases/cognee_db`. Earlier build exclusions covered
common database extensions but did not exclude that entire local store. The
initial explicitly supplied tar contexts also lacked the root `.dockerignore`.
A path-only check confirms the file exists in the earlier local full test image.
Its content was not inspected or used for qualification requests.

Implemented: nested local-store/cache/data directories and secret-file patterns
are excluded from Docker contexts; the application wheel has matching explicit
exclusions. Upstream tests are excluded from the wheel. A release check inspects
the actual wheel for forbidden paths. Current builds use the real checkout
context with `.dockerignore`; a clean replacement image must also pass path
checks before release. Do not publish or reuse the earlier full test images:
`rnr-cognee-full:qualification-20261019` and
`rnr-cognee-full:qualification-latest-20261019`. A superseded intermediate
Debian 13 build was stopped. Earlier local image/build-cache copies are retained
pending a separately reviewed cleanup; no broad Docker prune is authorized.

No image was pushed to a registry. Original database files stay in place. All
actual database qualification requests use explicitly disposable PostgreSQL
fixtures; packaging a local file is nevertheless a separate preservation/privacy
issue and is not described as proof that only synthetic bytes entered old images.

## F33 - Medium: repeated security loggers duplicate handlers and cross-write

Each `SecurityLogger` previously attached new file and console handlers to the
same global logger. Repeated construction accumulated handlers, sent events to
other instances' file destinations and substantially multiplied logging work.
A security performance test exposed the repeated output during this run.

Implemented: each canonical file destination has its own logger; handler setup
is synchronized and idempotent. Events no longer propagate into other destinations.
A real temporary-file test constructs twenty repeated instances, confirms the
handler count remains stable, and confirms an event does not enter the second
destination. The existing performance threshold was retained; its elapsed-time
measurement now uses a monotonic performance clock.

## F34 - Startup failure when production tenant enforcement is enabled

Two legacy class descriptions were formatted strings that executed a table-scope
lookup during import, before any request had selected a tenant. The production
guard correctly refused this, preventing the full registry from loading.

Implemented: descriptions are ordinary documentation strings; tenant lookup still
occurs at storage execution. A subprocess regression confirms imports work and
unscoped storage still fails. The rebuilt full image also passed API imports,
122-tool discovery and an actual MCP handshake/readonly-denial check with tenant
enforcement enabled, no external network, a read-only filesystem and dropped
container capabilities. A dedicated full-runtime CI workflow now exercises this.

## F35 - Legacy integrity verification could change state under read permission

`verify_memory` was assigned read permission despite writing a verification flag.
It also claimed inspection verification when no checksum existed and could
acknowledge a failed verification write. Extra provenance attributes could replace
the recorded origin/checksum/verification fields.

Implemented: this tool requires administrator permission. Missing checksums cannot
acquire verification; the shared method checks the baseline and uses an atomic
content/checksum condition to prevent verification racing with a content edit.
Only an actual affected row is acknowledged. Custom attributes cannot override
recorded provenance. The result explicitly concerns checksum integrity, not truth.
Real PostgreSQL tests and readonly public-boundary denial cover the repair.

## F36 - Remaining unscoped branches inside legacy scoped operations

The provenance transformation update still used the global documents table. Two
consolidation joins and an agent-copy source query did the same. The copy statement
also had mismatched destination columns, values and argument positions.

Implemented: those branches use the selected tenant table on both sides. The copy
statement retains the actual content/category/target writer and supplies its
creation timestamp. A real PostgreSQL fixture with identical IDs in two separate
tenant tables proves that transformation and copying affect only the selected
tenant. Other legacy session/undo/compliance paths still require consolidation;
these repairs do not establish complete legacy isolation or encryption.

## F37 - An inherited ignore rule omitted new recovery code from delivery

The broad `*_backup.*` ignore rule excluded `src/memory_backup.py` and its real
backup qualification test. Local tests could pass while a GitHub checkout lacked
both files. An actual Hermes-local import exposed the delivery failure.

Implemented: explicit exceptions admit those two maintained source/test files
without admitting unrelated backup files or private data. Both were published,
pulled through GitHub and exercised in Ubuntu-Hermes. The native 69-check lane
includes the delivered backup test. Local-only test success is not delivery proof.

## F38 - Native restore did not explicitly select its fresh database

The default `pg_restore` command lacked `--dbname`. The connection environment
alone does not put pg_restore into database restoration mode. Earlier tests used
an explicit Docker command that already supplied the database and masked this
native-path omission. The native test failed; it did not acknowledge recovery.

Implemented: the default command explicitly names the newly created database.
The actual default-command test passed in Ubuntu-Hermes with native PostgreSQL
clients and age, covering wrong-key and tampered-manifest rejection, refusal to
overwrite an existing database, retained encrypted history and project denial.
The incomplete synthetic restore was retained. Existing databases were not
overwritten. The CI fixture also exercises the default command.

## F39 - Local serving window below the installed Hermes minimum

This is a compatibility prerequisite, not an Enhanced Cognee vulnerability. The
configured local Granite service reported an 8,192-token window. Installed Hermes
requires at least 64,000. A first model request exceeded the actual window;
subsequent initialization refused the detected limit. A reachable local endpoint
and a model's native maximum do not prove usable Hermes configuration.

Documented: verify the actual served context and resource budget before local
chat activation. No guard was bypassed and no Unsloth setting was changed. The
small local embedding model works independently. Full chat automatic capture,
fresh-session recall, clear correction and uncertain-change clarification were
exercised with the owner's existing authorized cloud model and invented facts.
Local chat qualification remains open; the live report records the exact limit.
