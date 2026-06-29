# Tutorial 03: Memory Versioning and Provenance

**Audience:** Intermediate users
**Time required:** 25 minutes
**Prerequisites:** RNR Enhanced Cognee running; PostgreSQL connected

---

## Overview

Every time a memory's content changes, RNR Enhanced Cognee records the previous content
as a version row in the memory_versions table. This means you can:

- See the full history of edits to a memory
- Revert to any previous version
- Know where a memory originated and what transformations it has undergone
- Assign a confidence score that reflects how reliable the content is

The versioning and provenance systems work together to give you auditability over
your memory store.

---

## Concepts

**Version:** An immutable snapshot of a memory's content taken before each update.
Version numbers start at 1 and increase monotonically.

**Provenance:** Metadata about a memory's origin -- where the content came from,
who authored it, when it was ingested, and what transformations were applied.

**Confidence score:** A decimal between 0.0 and 1.0 reflecting how reliable the
content is believed to be. 1.0 means ground truth; below 0.3 means uncertain.

---

## Step 1: Update a Memory to Create a Version

First, store a memory and note its ID:

    Tool: add_memory
    Parameters:
      content: "Redis is configured on port 26379."
      agent_id: "infra-agent"

    Response: [OK] Memory stored: mem_e5f6a7b8-...

Now update it to trigger versioning:

    Tool: update_memory
    Parameters:
      memory_id: "mem_e5f6a7b8-..."
      content: "Redis is configured on port 26379 with TLS enabled."

    Response: [OK] Memory updated (version 2 created)

Each update creates a new version before applying the change.

---

## Step 2: View the Version History

    Tool: get_memory_history
    Parameters:
      memory_id: "mem_e5f6a7b8-..."
      limit: 10

Response:

    Memory mem_e5f6a7b8-... has 2 version(s):

    Version 2 (current)
      Content:    Redis is configured on port 26379 with TLS enabled.
      Changed at: 2026-02-13T15:01:44Z
      Agent:      infra-agent

    Version 1
      Content:    Redis is configured on port 26379.
      Changed at: 2026-02-13T14:55:22Z
      Agent:      infra-agent

---

## Step 3: Revert to a Previous Version

    Tool: revert_memory
    Parameters:
      memory_id: "mem_e5f6a7b8-..."
      version_number: 1

Response:

    [OK] Memory mem_e5f6a7b8-... reverted to version 1
    Current content: Redis is configured on port 26379.

A revert is itself versioned -- version 3 will now record the content at the time
of the revert, so no history is lost.

---

## Step 4: Inspect Provenance

Provenance tracks where a memory came from and what happened to it:

    Tool: get_memory_provenance
    Parameters:
      memory_id: "mem_e5f6a7b8-..."

Response:

    Provenance for mem_e5f6a7b8-...:
      Source:        user_input
      Author:        infra-agent
      Ingested at:   2026-02-13T14:55:22Z
      Checksum:      sha256:a3f9...
      Transformations: (none)
      Verified:      false

When a memory is produced by ingesting a URL or a database record, the source field
reflects that origin (ingest_url, ingest_db). When PII is redacted or the content
is translated, a transformation entry is added.

---

## Step 5: Verify a Memory

Verification marks a memory as checked and authoritative (confidence 1.0):

    Tool: verify_memory
    Parameters:
      memory_id: "mem_e5f6a7b8-..."
      verified_by: "senior-engineer"

Response:

    [OK] Memory mem_e5f6a7b8-... verified by senior-engineer
    Confidence set to 1.0 (high)

---

## Step 6: Set Confidence Manually

You can set a confidence score without full verification. Use this when a memory
comes from a less reliable source:

    Tool: set_memory_confidence
    Parameters:
      memory_id: "mem_e5f6a7b8-..."
      score: 0.6
      reason: "Inferred from log output; not directly confirmed"

Response:

    [OK] Confidence set to 0.6 (medium) for mem_e5f6a7b8-...

Confidence levels:
- 0.8 to 1.0: high -- use with confidence
- 0.5 to 0.8: medium -- treat as likely but verify before acting
- 0.3 to 0.5: low -- treat with caution
- below 0.3:  uncertain -- candidate for deletion or review

---

## What to Read Next

- TUT-004: GDPR Compliance Workflow -- how provenance supports right-of-access
- TUT-002: Memory Lifecycle Management -- expiring uncertain memories automatically
