# Tutorial 04: GDPR Compliance Workflow

**Audience:** Compliance officers and developers responsible for data subject rights
**Time required:** 30 minutes
**Prerequisites:** RNR Enhanced Cognee running; GDPRManager connected to PostgreSQL

---

## Overview

RNR Enhanced Cognee implements four GDPR/CCPA rights via the GDPRManager module:

- Right of access and data portability (Article 15 / Article 20)
- Right to erasure (Article 17)
- Consent management (Article 7)
- Multi-tenant data isolation (a technical safeguard)

This tutorial walks through each right using the MCP tools. For the operational
step-by-step erasure procedure, see RB-004.

---

## Concepts

**user_id:** The identifier under which a data subject's memories were stored.
This is the same user_id parameter used in add_memory calls.

**Consent record:** A structured entry stating that a specific user has (or has not)
consented to a specific data category being processed.

**Tenant isolation:** RNR Enhanced Cognee can serve multiple organisational tenants from
a single deployment. Tenant boundaries are enforced at the application layer so
that queries for tenant A never return data belonging to tenant B.

---

## Step 1: Record Consent

Before storing memories for a user, record their consent:

    Tool: gdpr_record_consent
    Parameters:
      user_id: "user-alice-001"
      category: "development"
      granted: true
      recorded_by: "onboarding-service"

Response:

    [OK] Consent recorded for user-alice-001 / category development
    Granted: true
    Recorded by: onboarding-service
    Timestamp: 2026-02-13T16:00:00Z

Repeat for each data category the user has consented to. If a user withdraws
consent, call the same tool with granted=false.

---

## Step 2: Check Consent Before Processing

Before ingesting or processing data for a user, verify their consent:

    Tool: gdpr_check_consent
    Parameters:
      user_id: "user-alice-001"
      category: "development"

Response when consent is granted:

    [OK] Consent granted for user-alice-001 / category development
    Recorded at: 2026-02-13T16:00:00Z

Response when consent is absent or withdrawn:

    [WARN] No active consent for user-alice-001 / category analysis
    Do not process data for this user in this category.

Your application code should check consent before calling add_memory or cognify
for user-generated content.

---

## Step 3: Export a User's Data (Right of Access)

A data subject may request a copy of all their stored data:

    Tool: gdpr_export_user_data
    Parameters:
      user_id: "user-alice-001"
      format: "zip"

Response:

    [OK] Export complete: gdpr_exports/user-alice-001_20260213.zip
    Includes:
      Documents:      23
      Vector entries: 23
      Graph nodes:    5
      Audit log rows: 87

Provide the zip file to the data subject. The export includes all memories,
version history, provenance metadata, and redacted audit entries.

---

## Step 4: Delete a User's Data (Right to Erasure)

For the full operational procedure, follow RB-004. The key MCP tool calls are:

Dry run first:

    Tool: gdpr_delete_user_data
    Parameters:
      user_id: "user-alice-001"
      dry_run: true

Confirm the counts match the export from Step 3, then execute:

    Tool: gdpr_delete_user_data
    Parameters:
      user_id: "user-alice-001"
      dry_run: false

Response:

    [OK] PostgreSQL: 23 documents deleted
    [OK] Qdrant: 23 vectors deleted
    [OK] Neo4j: 5 nodes deleted
    [OK] Audit log: 87 rows redacted
    [OK] Redis: cache flushed
    [DONE] Erasure complete for user-alice-001

---

## Step 5: Verify Tenant Isolation

For multi-tenant deployments, confirm that data for one tenant is not visible
to another:

    Tool: gdpr_verify_tenant_isolation
    Parameters:
      tenant_id_a: "tenant-acme"
      tenant_id_b: "tenant-globex"

Response when isolation is intact:

    [OK] Tenant isolation verified
    tenant-acme documents: 142
    tenant-globex documents: 89
    Cross-tenant leakage detected: 0 records

If any cross-tenant leakage is detected, the response lists the affected memory
IDs and the tool returns [ERR]. Investigate and correct before processing any
further requests.

---

## What to Read Next

- RB-004: GDPR Erasure Request -- operational runbook for compliance officers
- TUT-003: Versioning and Provenance -- how version history supports right of access
- ADR-003: Dynamic Categories -- how category design affects consent scoping
