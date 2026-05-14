# Runbook RB-008: Memory Consolidation Runaway

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Operators, developers

---

## Overview

The auto_consolidate_memories tool merges similar memories to reduce redundancy.
When the similarity threshold is set too low, or when an agent adds many slightly
rephrased versions of the same information in a short period, the consolidation
process may merge memories that should remain distinct. This runbook diagnoses an
unexpectedly high consolidation rate and guides the operator through reverting
incorrect merges and tuning the threshold.

---

## Symptoms

- An agent reports that it can no longer recall a specific memory it previously
  stored, but that memory was not explicitly deleted.
- The deduplication_report tool shows a merge ratio above 20% for a recent
  consolidation run.
- The consolidation_report field in a recent run shows a large number of merged
  pairs where the "kept" and "discarded" memories appear semantically distinct.
- An operator who manually reviewed recent memories found that distinct facts
  (e.g., two different configuration values for two different services) were merged
  into a single memory.

---

## Diagnosis Steps

### Step 1: Review the most recent consolidation report

    Tool: deduplication_report

The report includes:

    run_id           UUID identifying this consolidation run
    agent_id         Which agent's memories were processed
    candidates_found Total pairs above the similarity threshold
    pairs_merged     How many pairs were actually merged
    merge_ratio      pairs_merged / candidates_found
    duration_ms      Wall-clock time of the run

A merge_ratio above 0.20 (20%) warrants investigation.

---

### Step 2: Inspect the consolidation candidates

    Tool: find_consolidation_candidates
    Parameters:
      agent_id: <agent_id_from_report>
      limit: 50

This returns pairs of memories with their similarity scores. Review the top 10
pairs (highest similarity score). For each pair, read both memories:

    Tool: get_memory
    Parameters:
      memory_id: <id_of_first_memory>

    Tool: get_memory
    Parameters:
      memory_id: <id_of_second_memory>

For each pair, decide: should these two memories have been merged? If yes, the
consolidation was correct. If no, record the pair's similarity score and memory
IDs for the fix steps.

---

### Step 3: Check the configured similarity threshold

    Tool: get_stats

Look for the line:

    consolidation_similarity_threshold: 0.75

Compare this value against the lowest similarity score among incorrectly merged
pairs identified in Step 2. If incorrect merges have similarity scores around
0.75-0.80, the threshold is too permissive.

Also check .enhanced-cognee-config.json directly:

    {
      "consolidation": {
        "similarity_threshold": 0.75,
        "auto_consolidate_enabled": true,
        "min_memories_before_consolidation": 10
      }
    }

---

### Step 4: Determine the scope of incorrect merges

    Tool: get_memory_age_stats
    Parameters:
      agent_id: <agent_id>

This shows memory count before and after the last consolidation run. If the count
dropped by more than 20% in the consolidation window, many memories were merged.

Check the audit log for the consolidation run:

    docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
      -c "SELECT * FROM shared_memory.audit_log
          WHERE operation = 'consolidate' AND created_at > NOW() - INTERVAL '24 hours'
          ORDER BY created_at DESC LIMIT 50;"

Each row records the memory_id of the discarded memory and the memory_id of the
kept memory. This list is the input for Fix Step 1.

---

## Fix Steps

### Fix 1: Revert specific incorrect consolidations

For each incorrectly merged pair identified in Step 2:

1. Find the discarded memory's last content in the audit log:

       docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
         -c "SELECT content, metadata FROM shared_memory.audit_log
             WHERE memory_id = '<discarded_memory_id>'
             ORDER BY created_at DESC LIMIT 1;"

2. Re-create the discarded memory using its original content:

       Tool: add_memory
       Parameters:
         content: <content_from_audit_log>
         agent_id: <agent_id>
         metadata: <metadata_from_audit_log>

3. Note the new memory_id returned. The merge has been reversed at the cost of
   the original memory_id (the new memory has a different ID). If any downstream
   process references the old memory_id, it must be updated.

Repeat for each incorrectly merged pair.

---

### Fix 2: Raise the similarity threshold

To prevent future over-aggressive consolidation:

1. Open .enhanced-cognee-config.json.
2. Increase the similarity_threshold. A value of 0.90 is conservative; memories
   must be 90% similar (by cosine similarity of their embeddings) before being
   considered candidates.

       {
         "consolidation": {
           "similarity_threshold": 0.90,
           "auto_consolidate_enabled": true
         }
       }

3. Restart the MCP server to apply the change:

       enhanced-cognee stop
       enhanced-cognee start

4. Verify the new threshold is active:

       Tool: get_stats
       Expected: consolidation_similarity_threshold: 0.90

---

### Fix 3: Disable auto-consolidation temporarily

If the scope of incorrect merges is large and you need time to investigate:

1. In .enhanced-cognee-config.json, set:

       {
         "consolidation": {
           "auto_consolidate_enabled": false
         }
       }

2. Restart the MCP server.

3. Verify no consolidation runs are scheduled:

       Tool: list_tasks
       Confirm no task named "auto_consolidate_memories" appears with status "scheduled".

4. Restore any incorrectly merged memories using Fix 1.
5. Re-enable auto-consolidation after setting a higher threshold (Fix 2) and
   verifying on a small test run (see Verification below).

---

### Fix 4: Protect specific memories from consolidation

If certain memories must never be merged regardless of similarity (e.g., two
different service configurations that happen to sound similar):

1. Update each protected memory to add a "no_consolidate" metadata flag:

       Tool: update_memory
       Parameters:
         memory_id: <memory_id>
         content: <existing_content>
         metadata: '{"no_consolidate": true, ...existing_metadata...}'

The consolidation engine skips any memory with no_consolidate set to true in its
metadata.

---

## Verification

After applying fixes, run a manual consolidation on a small test set:

    Tool: auto_deduplicate
    Parameters:
      agent_id: <agent_id>
      dry_run: true

The dry_run parameter returns the list of pairs that would be merged without
actually merging them. Review the list and confirm all pairs are genuinely
redundant before running without dry_run.

If the dry_run list looks correct, run the real consolidation:

    Tool: auto_deduplicate
    Parameters:
      agent_id: <agent_id>
      dry_run: false

Then verify:

    Tool: deduplication_report

Confirm the merge_ratio is below 0.10 (10%) for the test run.

---

## Postmortem Template

    Incident: Memory Consolidation Runaway
    Date: YYYY-MM-DD
    Agent affected: <agent_id>
    Duration: HH:MM (time from first report to restored state)

    Metrics:
    - Memories before consolidation: N
    - Memories incorrectly merged: N
    - Memories restored (Fix 1): N
    - Similarity threshold at time of incident: 0.XX
    - Threshold after fix: 0.XX

    Timeline:
    - HH:MM  Symptom observed (missing memory, high merge ratio alert)
    - HH:MM  Diagnosis started
    - HH:MM  Scope of incorrect merges determined (Step 4)
    - HH:MM  Restoration complete (Fix 1)
    - HH:MM  New threshold applied (Fix 2)
    - HH:MM  Verification passed

    Root Cause:
    <Describe why the threshold was too low. Was it the default? Was it lowered
    recently? Did the agent add many near-duplicate memories in a short window?>

    Prevention:
    <What change prevents recurrence? New threshold? Alerting on merge ratio?
    A merge-ratio alert threshold added to get_prometheus_metrics?>

    Follow-up Actions:
    - [ ] Action 1 (owner, due date)
    - [ ] Action 2 (owner, due date)
