# Runbook RB-010: Database Migration Failure

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Operators, developers

---

## Overview

Enhanced Cognee uses Alembic to manage the PostgreSQL schema. Each new release
may include Alembic migrations that add tables, columns, or indexes. If a migration
fails (partially applied, never applied, or schema mismatch), the MCP server cannot
start. This runbook guides the operator through identifying the migration state and
restoring a healthy database schema.

---

## Symptoms

- The MCP server exits immediately after startup with a log message such as:

      [ERR] alembic: relation "shared_memory.documents" does not exist
      [ERR] alembic: column "confidence" of relation "observations" does not exist
      [ERR] alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
      [ERR] psycopg2.errors.UndefinedTable: relation does not exist

- Running enhanced-cognee health fails before reaching the database connection step.
- A call to any MCP tool returns:

      [ERR] Database schema is not up to date. Run: enhanced-cognee migrate upgrade head

---

## Diagnosis Steps

### Step 1: Confirm PostgreSQL is reachable

Before investigating migrations, confirm the database container is running:

    docker ps --filter name=postgres-enhanced

If the container is not listed, start it:

    docker start postgres-enhanced

Wait 5 seconds, then confirm:

    docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db -c "SELECT 1;"

Expected output:

    ?column?
    ----------
            1
    (1 row)

If this fails, the PostgreSQL container itself is the problem. Follow RB-002
(Database Health Check) before continuing.

---

### Step 2: Check the current Alembic revision

    enhanced-cognee migrate current

This command queries the alembic_version table in PostgreSQL and prints the current
revision hash and description.

Possible outputs:

    INFO  [alembic.runtime.migration] Current revision: 0011_add_audit_log_indexes (head)

This means migrations are up to date. The MCP server startup error is not a
migration problem; check the MCP server logs for a different error.

    INFO  [alembic.runtime.migration] Current revision: 0009_add_confidence_column

This means the database is at revision 0009 but the code expects a later revision.
Fix Step 1 applies.

    [ERR] alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'

The alembic_version table contains a revision hash that does not exist in the
migration scripts directory. Fix Step 3 applies.

    [ERR] psycopg2.errors.UndefinedTable: relation "alembic_version" does not exist

The alembic_version table has never been created. The database schema was never
initialized. Fix Step 2 applies.

---

### Step 3: View the full migration history

    enhanced-cognee migrate history

This prints all known revisions in order:

    0001_initial_schema  -> 0002_add_vector_column  (...)
    0002_add_vector_column -> 0003_add_audit_log  (...)
    ...
    0011_add_audit_log_indexes -> <head>

Compare the list against the current revision from Step 2 to identify which
migrations have not been applied.

---

### Step 4: Check for a partially applied migration

A partially applied migration is the most dangerous state: some SQL statements in
the migration script ran successfully, others failed. The alembic_version table
may or may not have been updated.

Check PostgreSQL directly for the tables and columns that the failing revision was
supposed to create. For example, if revision 0012 adds the observations table:

    docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
      -c "\d shared_memory.observations"

If the table does not exist, the migration did not run (or ran and failed before
creating the table). If the table exists but is missing a column, the migration
ran partially.

---

## Fix Steps

### Fix 1: Migration never ran or is behind - run upgrade head

This is the standard fix for a database that is behind by one or more revisions.

    enhanced-cognee migrate upgrade head

Alembic applies all pending migrations in order. Each migration is wrapped in a
transaction; if any individual migration script fails, that migration is rolled
back and Alembic stops.

After the command completes:

    enhanced-cognee migrate current

Confirm the output shows "(head)".

Then start the MCP server:

    enhanced-cognee start

---

### Fix 2: Alembic version table missing - initialize from scratch

If Step 2 showed that the alembic_version table does not exist, the database
schema was never initialized.

[WARN] This step creates all tables from scratch. Only use it on an empty database
or after confirming that all existing data has been backed up.

1. Create a backup first (even for an empty database, as a precaution):

       enhanced-cognee backup create

2. Run the full upgrade:

       enhanced-cognee migrate upgrade head

3. Verify:

       enhanced-cognee migrate current
       Expected: "<latest_revision> (head)"

---

### Fix 3: Unknown revision in alembic_version - manual rollback

This occurs when the alembic_version table contains a revision hash that does not
match any migration script. This can happen after:
- A git branch switch that removed a migration script that was already applied.
- A manual edit of the alembic_version table.

[WARN] This fix modifies the alembic_version table directly. Proceed carefully.

1. Back up the current alembic_version value:

       docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
         -c "SELECT version_num FROM alembic_version;"

   Record the value.

2. Identify the last known good revision from the history (Step 3). Typically
   this is the revision just before the unknown hash.

3. Manually reset alembic_version to the last known good revision:

       docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
         -c "UPDATE alembic_version SET version_num = '0011_add_audit_log_indexes';"

   Replace the value with the correct revision identifier from Step 3.

4. Run upgrade head:

       enhanced-cognee migrate upgrade head

5. Verify:

       enhanced-cognee migrate current
       Expected: "<latest_revision> (head)"

---

### Fix 4: Partially applied migration - downgrade then upgrade

If Step 4 confirmed a partial application (some objects were created, others were
not):

[WARN] Downgrading removes schema objects. If those objects contain data, the data
will be lost. Take a backup first.

1. Back up the database:

       enhanced-cognee backup create

   Record the backup ID from the output.

2. Downgrade to the revision before the failing one. For example, if revision 0012
   failed, downgrade to 0011:

       enhanced-cognee migrate downgrade 0011_add_audit_log_indexes

3. Confirm the downgrade:

       enhanced-cognee migrate current
       Expected: "0011_add_audit_log_indexes"

4. Investigate and fix the migration script if it contained a bug. The migration
   scripts are in alembic_enhanced/versions/. Read the failing script:

       cat alembic_enhanced/versions/0012_add_observations_table.py

5. Re-run the upgrade:

       enhanced-cognee migrate upgrade head

6. Verify:

       enhanced-cognee migrate current
       Expected: "<latest_revision> (head)"

---

## Verification

After any fix, confirm the MCP server starts and the schema is complete:

1. Start the server:

       enhanced-cognee start

2. Run a health check:

       Tool: health
       Expected: all components [OK]

3. Run a basic smoke test:

       Tool: add_memory
       Parameters:
         content: "Migration test memory"
         agent_id: "migration-test"

       Tool: search_memories
       Parameters:
         query: "migration test"
         agent_id: "migration-test"

   Confirm the memory is returned by the search.

4. Clean up the test memory:

       Tool: delete_memory
       Parameters:
         memory_id: <id_returned_by_add_memory>

---

## Postmortem Template

    Incident: Database Migration Failure
    Date: YYYY-MM-DD
    Duration: HH:MM (time from first error to healthy state)
    Release version that triggered the migration: X.Y.Z

    State at incident start:
    - Current revision at time of failure: <revision_hash>
    - Expected revision (head): <revision_hash>
    - Migration state: [never_ran / partially_applied / unknown_revision / behind]

    Timeline:
    - HH:MM  MCP server startup failure first observed
    - HH:MM  alembic migrate current run (Step 2)
    - HH:MM  Root cause identified (Fix N)
    - HH:MM  Backup taken (if applicable)
    - HH:MM  Fix applied
    - HH:MM  Verification passed, MCP server healthy

    Root Cause:
    <Why did the migration fail? Bad SQL in the migration script? Network
    interruption during the upgrade? Branch switch that removed a script?
    Manual edit of alembic_version?>

    Data Loss:
    [None / Partial - describe what was lost / Full - describe recovery from backup]

    Prevention:
    <Add a migration smoke test to CI? Pin migration script checksums? Add a
    pre-startup migration check to the MCP server that prints a clear [ERR] with
    the fix command?>

    Follow-up Actions:
    - [ ] Action 1 (owner, due date)
    - [ ] Action 2 (owner, due date)
