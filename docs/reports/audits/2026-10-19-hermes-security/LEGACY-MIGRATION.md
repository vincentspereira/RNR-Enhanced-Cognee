# Preserving older memories during migration

Status: implemented and tested on invented PostgreSQL fixtures. No existing
private memory tables have been migrated. The source tables stay in place.

Use `python -m src.legacy_memory_migration` in the service environment. This is
an operator command and is deliberately absent from the Hermes tool list.
It requires the database URL and persistent encryption key through the protected
environment, just like the restricted memory service.

## Review before copying

Decide which old table belongs to which project and who owns the copied records.
Do not infer ownership from a category, an old agent label, or document metadata.
An old global table can contain several projects; do not copy that whole table
into one project unless every selected record has been reviewed for that scope.
The current command copies a bounded ID-ordered batch, not a content-based filter.
Use a separately reviewed source table for mixed-project data.

Start with a disposable restored backup and this preview:

```bash
python -m src.legacy_memory_migration \
  --tenant approved_owner --project approved_project \
  --owner approved_subject --agent migration_operator --limit 100
```

The values above are examples. Supply reviewed canonical IDs. The command selects
`shared_memory.documents_t_<tenant>`. Only the explicit `--source-global` option
selects the old `shared_memory.documents` table. Ambiguous or noncanonical tenant
names are refused rather than normalized to a potentially different namespace.

Without `--apply`, the command only reads and validates the source; it does not
initialize a schema or copy records. Its summary contains counts and a continuation
ID, not document content or credentials. A preview is not an authorization decision
and does not guarantee that a source table will remain unchanged afterward.

## Copy a reviewed batch

After reviewing the backup, scope, and preview, repeat the command with `--apply`.
Use `--after-id` with the returned continuation ID to select the next batch.
The maximum is 500 records; reduce it if the batch exceeds the 16 MiB source budget.

Each acknowledged record commits with encrypted content, encrypted source lineage,
version history, an audit entry and a durable change event. The new record has its
own canonical ID; its original UUID or text ID remains in encrypted metadata.
Retries keep the same canonical record through a stable source-based retry key.
A changed source snapshot conflicts instead of overwriting an earlier import.
The complete bounded batch is validated before copying, but records commit one
at a time. A later database outage or retry conflict can therefore leave an
acknowledged prefix copied. Retry the same batch after investigating; do not
advance the continuation ID after a failed run.

Legacy metadata is preserved as unverified source material. It cannot select a
project, set an owner, grant sharing, or turn imported claims into verified facts.
Old vectors are not copied because their model and dimension contracts differ.
This command imports text without semantic vectors; those records use text recall
until a qualified reindexing process supplies the selected model's embeddings.
Legacy expiry is preserved from either the dedicated column or the older metadata
field. Conflicting expiry values stop the batch. Expired records remain excluded
from recall. Non-object metadata is refused rather than silently discarded.
Protected legacy content must decrypt with the supplied key; decryption failure
stops migration rather than importing ciphertext as a remembered fact.

Never point this command at real data before backup/key recovery and the ownership
mapping have been reviewed. It does not delete, rename, overwrite, or erase the
source table, and it does not solve legacy graph/vector cleanup or permanent erasure.

## Evidence

The additive legacy schema revision also supplies missing category, tags, expiry,
metadata and update-time columns on existing document/tenant tables. Versioning
now uses the document table's actual UUID or TEXT ID type for its foreign key.
The older Docker initializer no longer creates a full-precision ANN index on
2560-dimensional vectors: pgvector rejects that index above 2000 dimensions.
Stored vectors retain their full precision; the existing search uses exact
distance ordering. This trades indexing speed for a working, data-preserving
legacy initializer until a separate index/model profile is qualified. See the
[pgvector index limits](https://github.com/pgvector/pgvector#ivfflat).

`tests/integration/test_legacy_schema_qualification.py` passes against real
pgvector for a fresh Alembic install, a UUID Docker installation, and an existing
TEXT installation with a tenant table. It checks data preservation, compatible
version foreign keys and unchanged legacy vector dimensions. These fixtures live
in separate disposable databases and do not alter any existing private database.

`tests/qualification/test_legacy_memory_migration.py` covers UUID and TEXT source
IDs, optional-column differences, JSONB lineage, preview without writes, retry
deduplication, source preservation, encrypted destination payloads, cross-project
denial and conflicting source revisions. These are synthetic fixtures, not proof
that every historical installation layout can be imported without further review.
