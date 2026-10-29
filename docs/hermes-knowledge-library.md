# Enhanced Cognee human knowledge library: first-step candidate

## Decision and source-backed dashboard assessment

The checked Enhanced Cognee dashboard is not a simple independent replacement
for the Brain's source-first human library. It has database memory-management
routes and UI source, but not an offline original-note store with deliberate
revision preservation. This assessment is source inspection, not dashboard UI
acceptance or a claim that the dashboard was built or run.

Inspected baseline: `e25bd6356e38970c525e0258bdac983cd4079d29`, branch
`hermes/enhanced-cognee-native-memory-20261012`.

| Role | Source finding | Relevant lines |
| --- | --- | --- |
| List/read | `GET /api/memories` and `GET /api/memories/{memory_id}` select PostgreSQL `shared_memory.documents`; both call `require_pg()`. | `dashboard/dashboard_api.py:754-810` [1] |
| Create | `POST /api/memories` writes database content, with metadata source `dashboard`; title is derived from content rather than an original file identity. AddMemoryModal calls `createMemory`. | `dashboard/dashboard_api.py:813-850`; `AddMemoryModal.tsx:82-98` [1][4] |
| Edit | PATCH replaces content/metadata in the existing row. EditMemoryModal calls `updateMemory`; this is not append-only original-source versioning. | `dashboard/dashboard_api.py:859-911`; `EditMemoryModal.tsx:118-139` [1][5] |
| Source/provenance | Response includes content, timestamps, optional `files`, `facts`, before/after strings and agent fields. This is not an independently readable original Markdown source/history contract. | `dashboard/dashboard_api.py:326-343,426-449` [1] |
| Version/correction history | PATCH overwrites the row, and `/api/timeline/{memory_id}` returns chronological neighboring memories by the same agent, not earlier revisions of the same note. No revision/export endpoint was found in the inspected API route inventory. | `dashboard/dashboard_api.py:898-911,1081-1125` [1] |
| Export | Detail-page source calls `exportSingleMemoryAsMarkdown` imported from `@/lib/utils/export`. That target is absent in this checkout; an exact-source/provenance-preserving export could not be verified. | `[id]/page.tsx:22,98-103,185-192`; `tsconfig.json:21-23` [3][8] |
| Frontend completeness | List source fetches the API and imports `@/lib/stores` and API helpers. Referenced `src/lib` files are absent; the detail Edit button targets an `/edit` page absent in the checked tree. This is a source-level gap, not a runtime error reproduced in a browser. | `page.tsx:9-13,79-98`; `[id]/page.tsx:190`; evidence inventory [2][3][8] |
| Dependencies | Next.js/React and other packages are specified; the API imports FastAPI/Pydantic and initializes PostgreSQL, graph and Redis connections. CRUD requires PostgreSQL; graph/cache are not necessary for the new library. The compose deployment provisions services and published ports. | `package.json:20-71`; `dashboard_api.py:35-39,179-198,278-289,297-309`; compose [1][6][7] |

Therefore this change adds an owned, stdlib-only source library instead of
forcing the service-backed dashboard to serve a different authority model.
It is part of this Enhanced Cognee checkout, not upstream Cognee, and deliberately
has no runtime, embedding, MCP, graph-generation or AI-editing dependency.

## What is implemented

Executable entry point: `bin/enhanced_cognee_library.py`.
Standalone implementation: `src/hermes_memory/library.py`.

- Explicitly selected root; `init` only creates a **new** root and will not adopt
  an existing directory/vault. Root and directories are mode 0700, files 0600.
- Plain UTF-8 `source.md` originals with stable lowercase UUID note IDs.
- Working notes/documents: create, list, read, update, history, literal search.
- Human author, title, UTC timestamp, reason, origin, source SHA-256 and chained
  earlier-source/metadata hashes in readable JSON provenance sidecars.
- Every update writes a new revision. No delete, overwrite, automatic editor,
  auto-AI edit, generated summary or graph-generation command exists.
- Explicit single-Markdown import creates immutable raw evidence. Annotate it
  through a new working note linked to the evidence ID/revision/source hash.
- Offline all-revision export preserves exact original source and JSON bytes,
  identities and provenance. The export can be reopened in a fresh process.
- A self-contained HTML reading/search snapshot displays source as escaped plain
  text, provenance and all revisions. It does not execute note HTML/Markdown.
  The bundled filter script is fixed; CSP allows only its hash and the fixed
  style hash, denies network connections, forms and other asset sources.

The CLI plus reading view is **not full Obsidian GUI parity**. The HTML has no
write backend or editing controls and says: **No browser changes are saved**.
CLI search uses Unicode casefolding over latest title/source (optionally history).
HTML filtering uses JavaScript lowercase substring matching over displayed source,
metadata and history; its Unicode matching semantics are not identical to CLI.

## Authority and data layout

```text
<explicit-new-root>/
  library.json
  notes/
    <stable-uuid>/
      000001/
        source.md
        metadata.json
      000002/
        source.md
        metadata.json
```

There is no hidden database or separate mutable latest-note copy. Revision source
files are the human-readable content authority; sidecars define identity and
provenance. Highest contiguous revision is current. History remains directly
readable without running this code. Do not edit these originals/sidecars in place:
silent edits fail checksum, schema or chain validation. Edit a separate working
Markdown file and apply it with `update` instead.

Raw imported evidence is never rewritten by this API. An annotation's `corrects`
link records the target ID/revision/hash; changing an annotation does not change
the evidence. User-supplied origin/author labels are declarations, not externally
verified identity or provenance. Hashes are not digital signatures: a process
with write access to the owned root could intentionally rewrite the complete
history or last metadata, or remove final revisions. This is not tamper-proof
storage or a substitute for backups.

Choose **one** live authority after a separately authorized adoption decision.
Exports and HTML views are offline snapshots/backups, not simultaneously edited
competing libraries. The canonical Brain vault remains
`/home/vincentspereira/Projects/RNR-Personal-Brain/vault`; this work did not read
its note contents, ingest it, migrate it or modify it. The new library is only a
candidate for future deliberately owned notes, not an authorized replacement
for existing Brain authority.

## Local CLI examples (synthetic paths only)

From the repository, with a pre-existing scratch parent and a root that does not
exist yet:

```sh
CLI="$PWD/bin/enhanced_cognee_library.py"
ROOT="$TMPDIR/my-owned-library"
"$CLI" --root "$ROOT" init
"$CLI" --root "$ROOT" create --file "$TMPDIR/draft.md" \
  --title "Working document" --author "Human reviewer"
"$CLI" --root "$ROOT" list
"$CLI" --root "$ROOT" read <id>
"$CLI" --root "$ROOT" read <id> --revision 1
"$CLI" --root "$ROOT" update <id> --file "$TMPDIR/reviewed.md" \
  --expect-revision 1 --author "Human reviewer" --reason "Corrected attribution"
"$CLI" --root "$ROOT" history <id>
"$CLI" --root "$ROOT" search "attribution"
"$CLI" --root "$ROOT" search "original wording" --history
"$CLI" --root "$ROOT" import --file "$TMPDIR/evidence.md" \
  --title "Evidence" --author "Human reviewer" --origin "synthetic:document-v1"
"$CLI" --root "$ROOT" create --file "$TMPDIR/annotation.md" \
  --title "Evidence correction" --author "Human reviewer" \
  --corrects <evidence-id> --reason "Clarify attribution without rewriting evidence"
"$CLI" --root "$ROOT" export --destination "$TMPDIR/my-offline-export"
"$CLI" --root "$ROOT" view --output "$TMPDIR/reading.html"
```

Create the draft/reviewed/evidence/annotation Markdown files yourself first.
Replace `<id>` tokens with exact lowercase IDs returned by the CLI; no identifier
normalization is performed. `--expect-revision` rejects stale writers. JSON
commands emit ASCII-escaped JSON; `read` emits exact UTF-8 source bytes, preserving
CRLF/LF, whitespace and Unicode. `python3 bin/enhanced_cognee_library.py` also
works and avoids importing the separate memory runtime package.

Open `reading.html` directly as a local file; no local webserver is needed.
Regenerate to a new output name after changes. Existing HTML outputs and export
roots are never overwritten. Browser Find remains available if scripting is off.

## Path, privacy and failure boundaries

- Paths containing `..` are rejected before normalization. Directory-descriptor
  traversal uses `O_NOFOLLOW` on every component, including root/input/output
  ancestors. Symlink escapes are rejected; selected files must be regular and
  not hardlinked. Initialization cannot claim an existing directory.
- Inputs are explicitly selected `.md` files, with conservative ASCII filename
  allowlisting. Hidden basenames, non-Markdown extensions and secret/config-like
  names such as `.env`, `config.md`, `credentials.md` and `secrets.md` are refused.
  This is not a content-based secret classifier: do not select notes containing
  secrets just because their filename is allowed. No automatic scanning occurs.
- Notes are limited to 8 MiB each, valid UTF-8 without NUL. Roots must belong to
  the current user and have mode 0700. No chmod/repair of arbitrary roots occurs.
- Cooperating CLI writers use an advisory root-directory lock, exclusive file
  creation and fsync. Updates preserve prior versions; concurrent stale writers
  cannot overwrite one another. No external direct-write editor participates in
  that advisory lock.
- Interrupted writes can leave partial revision/export directories. Incomplete
  or disconnected history fails closed; no automatic deletion/repair is provided.
  Crash recovery, whole-export transactional publication and signed audit trails
  are missing. Retain verified backups before adoption.
- This implementation targets Ubuntu/WSL local Linux filesystems, not Windows,
  remote shares or multi-user hostile storage. It is a first-step candidate,
  not a production replacement or permission to retire Obsidian.

## Verification and remaining acceptance

Run without package installation or services:

```sh
python3 -m unittest discover -s tests/hermes_library -v
python3 tests/hermes_library/exercise_library.py --evidence <new-evidence-directory>
```

The library and tests use Python stdlib. An additional filter-script regression
test uses already installed Node's built-in `vm` with a synthetic DOM; it skips
if Node is absent and downloads nothing. This is not a browser/UI acceptance test.
The CLI exercise preserves synthetic scratch notes and writes an escaped reading
view plus structured evidence; use a fresh evidence directory or new output
name on subsequent runs because view output intentionally cannot be overwritten.

Actual result in this checkout: **15 tests passed**, including direct executable
CLI/fresh-process reopening, exact Unicode/CRLF source preservation, all-revision
byte-equal export, revision/provenance chains, immutable raw imports/corrections,
stale concurrent writers, path/symlink/hardlink guards, malformed input/schema,
HTML injection/CSP checks and executed synthetic-DOM filtering. Genuine RED/GREEN
logs for successive vertical slices are retained. The separate real CLI exercise
created **3 synthetic notes / 4 revisions**, reopened the export, compared every
source/metadata byte and verified raw-update rejection. No browser acceptance,
full repository suite, dashboard build or live backend integration is claimed.

Evidence directory:
`/home/vincentspereira/Projects/Hermes-Bot-Fleet/verification/enhanced-cognee-build-2026-10-12/library/`

Key artifacts: `19-final-green.txt`, `final-cli/cli-exercise.json`, `final-cli/exercise-summary.json`,
`final-cli/reading.html`, `dashboard-source-verification.json`, `source-ledger.json`, and
`owned-files-sha256.json`.

Before considering Obsidian retirement, separately verify Vincent's human
workflow and require: a write-capable GUI with honest save/error/conflict behavior;
Markdown rendering/links/backlinks/attachments/tags and navigation as needed;
Brain schema/owner-guide compatibility; deliberately authorized migration with
source/provenance equivalence and rollback; backup/recovery and larger-library
performance; actual browser/accessibility acceptance; and a single-authority
adoption decision. These are missing, not silently supplied by the CLI or HTML.

## Sources

[1] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/dashboard_api.py
[2] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/nextjs-dashboard/src/app/memories/page.tsx
[3] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/nextjs-dashboard/src/app/memories/%5Bid%5D/page.tsx
[4] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/nextjs-dashboard/src/components/organisms/AddMemoryModal.tsx
[5] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/nextjs-dashboard/src/components/organisms/EditMemoryModal.tsx
[6] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/nextjs-dashboard/package.json
[7] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/docker-compose-dashboard.yml
[8] file:///home/vincentspereira/Projects/RNR-Enhanced-Cognee-Hermes/dashboard/nextjs-dashboard/tsconfig.json
