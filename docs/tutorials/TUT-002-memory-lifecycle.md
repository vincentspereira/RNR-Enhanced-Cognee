# Tutorial 02: Memory Lifecycle Management

**Audience:** Intermediate users who have completed TUT-001
**Time required:** 25 minutes
**Prerequisites:** Enhanced Cognee running; at least a few memories stored

---

## Overview

Memories accumulate over time. Without lifecycle management, a memory store grows
indefinitely and search quality degrades as outdated or irrelevant memories compete
with current ones. Enhanced Cognee provides tools for:

- Setting automatic expiry via TTL (time-to-live)
- Expiring memories in bulk by age
- Archiving entire categories to cold storage
- Inspecting the age distribution of the memory store

---

## Concepts

**TTL (time-to-live):** A duration after which a memory is automatically deleted.
Set at the individual memory level. Useful for session data or temporary notes that
should not persist beyond a known deadline.

**Expiry by age:** A bulk operation that deletes (or archives) all memories older
than N days. Useful for scheduled maintenance.

**Archive:** Move memories from the active store to a compressed archive table. They
are no longer returned by search_memories but can be restored if needed.

---

## Step 1: Check the Current Age Distribution

Before making changes, understand what you have:

    Tool: get_memory_age_stats

Example response:

    Memory age distribution:
      0-7 days:    42 memories
      8-30 days:   117 memories
      31-90 days:  203 memories
      90+ days:    88 memories
    Total: 450 memories

The 90+ days bucket is a good target for expiry or archival review.

---

## Step 2: Set a TTL on a Specific Memory

Use set_memory_ttl to schedule automatic deletion of a single memory:

    Tool: set_memory_ttl
    Parameters:
      memory_id: "mem_a1b2c3d4-..."
      ttl_days: 30

Response:

    [OK] TTL set: mem_a1b2c3d4-... expires in 30 days (2026-03-15)

After the TTL elapses, the memory is deleted on the next expiry pass. TTL
does not delete the memory immediately.

To remove a TTL (make the memory permanent again), pass ttl_days=0:

    Tool: set_memory_ttl
    Parameters:
      memory_id: "mem_a1b2c3d4-..."
      ttl_days: 0

---

## Step 3: Preview a Bulk Expiry

Before deleting anything, preview what expire_memories would remove:

    Tool: expire_memories
    Parameters:
      days: 90
      dry_run: true

Response:

    [INFO] DRY RUN - no data deleted
    Would expire: 88 memories older than 90 days
    Policy: delete_old

Review the count. If it looks reasonable, proceed to the live run.

---

## Step 4: Run Bulk Expiry

    Tool: expire_memories
    Parameters:
      days: 90
      dry_run: false

Response:

    [OK] Expired 88 memories older than 90 days
    Action: deleted

Run get_memory_age_stats again to confirm the 90+ days bucket is now zero.

---

## Step 5: Archive a Category Instead of Deleting

If you want to preserve old memories in a recoverable form, use archive_category:

    Tool: archive_category
    Parameters:
      category: "development"
      older_than_days: 60

Response:

    [OK] Archived 37 memories from category 'development' (older than 60 days)
    Archived memories are excluded from search but can be restored.

Archived memories do not appear in search_memories results. They remain in
PostgreSQL in the archive table and can be restored by contacting the maintainers
or via direct SQL if needed.

---

## Step 6: Verify the Store Is Healthier

    Tool: get_memory_age_stats

Compare the distribution to Step 1. The 90+ days bucket should reflect your
expiry choices.

---

## Scheduling Regular Expiry

To automate expiry, use schedule_task:

    Tool: schedule_task
    Parameters:
      task: "expire_memories"
      cron: "0 3 * * 0"    # weekly at 03:00 on Sunday
      params: {"days": 90, "dry_run": false}

Scheduled tasks appear in the output of list_tasks.

---

## What to Read Next

- TUT-003: Memory Versioning and Provenance -- tracking the history of a memory
- RB-003: Backup and Restore -- create a backup before bulk expiry in production
