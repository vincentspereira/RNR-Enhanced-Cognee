# Runbook RB-004: Processing a GDPR Erasure Request

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Compliance officers and developers handling data subject requests

---

## Overview

GDPR Article 17 (right to erasure) requires that all personal data for a data
subject be permanently deleted on request. Enhanced Cognee's GDPRManager covers
all four databases: PostgreSQL (documents, audit logs), Qdrant (vectors), Neo4j
(graph nodes), and Redis (cached entries).

Audit log rows are redacted (personal identifiers replaced with [REDACTED]) rather
than deleted. This preserves the log count and timeline for compliance reporting
while removing the personal data.

Allow 15-30 minutes to complete this runbook end-to-end.

---

## Step 1: Identify the user_id

Confirm the exact user_id associated with the erasure request. This is the
identifier used when memories were stored (the user_id parameter passed to
add_memory). Confirm with the data subject or your user management system before
proceeding.

---

## Step 2: Export the User's Data (Archive Copy)

Before erasing, produce a data export for your records. Retain it for at least 30
days to handle any dispute about what was deleted.

    Tool: gdpr_export_user_data
    Parameters:
      user_id: "user-abc-123"
      format: "zip"

The tool returns a download path and a summary:

    [OK] Export complete: gdpr_exports/user-abc-123_20260213.zip
    Documents: 47
    Vector entries: 47
    Graph nodes: 12
    Audit log rows: 203

Store the zip file in a secure location outside the Enhanced Cognee data directories.

---

## Step 3: Dry-Run Erasure

Run delete with dry_run=True to see exactly what will be removed before committing:

    Tool: gdpr_delete_user_data
    Parameters:
      user_id: "user-abc-123"
      dry_run: true

Review the output:

    [INFO] DRY RUN - no data will be deleted
    Would delete: 47 documents from PostgreSQL
    Would delete: 47 vectors from Qdrant
    Would delete: 12 nodes from Neo4j graph
    Would redact: 203 audit log rows
    Would flush: Redis keys matching user-abc-123:*

If any count looks unexpectedly high or low, verify the user_id is correct before
proceeding to the live run.

---

## Step 4: Execute the Erasure

    Tool: gdpr_delete_user_data
    Parameters:
      user_id: "user-abc-123"
      dry_run: false

Confirm the output shows [OK] for each database:

    [OK] PostgreSQL: 47 documents deleted
    [OK] Qdrant: 47 vectors deleted
    [OK] Neo4j: 12 nodes deleted
    [OK] Audit log: 203 rows redacted
    [OK] Redis: cache flushed
    [DONE] Erasure complete for user-abc-123

---

## Step 5: Verify Consent Records

Check that the consent record for this user is also cleared:

    Tool: gdpr_check_consent
    Parameters:
      user_id: "user-abc-123"

Expected response after erasure:

    [INFO] No consent records found for user-abc-123

If consent records remain, call gdpr_delete_user_data again to ensure all data
stores have been covered, or contact the maintainers.

---

## Step 6: Record Completion

Document the completed erasure in your compliance tracker with:
- Date and time of erasure
- user_id processed
- The backup ID from the export (Step 2)
- The operator who performed the erasure

The erasure event is written to the audit log automatically by GDPRManager with
the requester field set to the agent_id or operator name passed to the tool.

---

## Notes

- Erasure is permanent. Data cannot be recovered after Step 4 unless a backup
  exists from before the erasure (see RB-003).
- Audit log redaction preserves row timestamps and event types but replaces
  all fields containing the user_id or personal identifiers with [REDACTED].
- If you need to stop partway through, call gdpr_delete_user_data with dry_run=true
  again after the partial run to see what remains.
