# ADR-009: Heuristic Memory Importance Scoring Over ML Models

**Status:** Accepted
**Date:** 2026-05-14
**Deciders:** Enhanced Cognee maintainers

---

## Context

Enhanced Cognee stores memories indefinitely unless explicitly deleted or expired.
As the number of stored memories grows, retrieval quality degrades: low-signal
memories (transient observations, intermediate computation results, redundant
notes) compete with high-signal memories (validated facts, frequently accessed
reference material, agent-critical context) in search rankings.

Two mechanisms need an importance score to function correctly:

1. Memory expiry (expire_memories tool): the system must know which memories
   to consider for expiry. Low-importance memories with no recent access are
   candidates; high-importance memories should be retained even if not recently
   accessed.
2. Memory consolidation (auto_consolidate_memories tool): when two memories
   are similar, the system must decide which one to keep as the canonical version.
   The one with the higher importance score survives.

A reliable importance score is therefore a prerequisite for both tools to behave
predictably. The score must be computed without human feedback labels, because
Enhanced Cognee is deployed as a single-user or small-team system with no
mechanism for users to rate memories explicitly.

---

## Decision

Use a weighted heuristic formula to compute an importance score in the range [0.0,
1.0] for each memory. The formula:

    score = (
        normalized_access_count  * 0.4 +
        recency_score            * 0.3 +
        confidence               * 0.2 +
        source_type_weight       * 0.1
    )

Component definitions:

    normalized_access_count
        access_count / (access_count + ACCESS_DECAY_CONSTANT)
        where ACCESS_DECAY_CONSTANT = 10 by default.
        A memory accessed 10 times scores 0.5 on this component; one accessed
        100 times scores ~0.91. The decay constant prevents high access counts
        from dominating.

    recency_score
        exp(-lambda * days_since_last_access)
        where lambda = 0.05 by default (half-life approximately 14 days).
        A memory accessed today scores 1.0 on this component; one not accessed
        in 30 days scores approximately 0.22.

    confidence
        A float in [0.0, 1.0] stored on the memory record. Set at write time
        by the caller (default 0.5 if not provided). Reflects the caller's
        certainty that the memory content is correct.

    source_type_weight
        A lookup table keyed on the memory's source_type field:
            "agent_observation"   : 0.6
            "user_input"          : 0.9
            "automated_ingestion" : 0.4
            "system_generated"    : 0.3
        Default for unknown source types: 0.5.

The formula is implemented in src/importance_scorer.py and called by the memory
repository at read time. Scores are not stored in the database; they are computed
on the fly from stored fields (access_count, last_accessed_at, confidence,
source_type) and cached in Redis for 5 minutes per memory_id.

All weights and constants (ACCESS_DECAY_CONSTANT, lambda, source_type_weight values,
the four component weights) are configurable via the .enhanced-cognee-config.json
file. Operators who find the defaults unsuitable can tune without code changes.

---

## Consequences

**Positive**
- The score is deterministic and reproducible: given the same inputs, the same
  score is always produced. Operators can explain why a memory was selected for
  expiry or consolidation.
- No training data is required. The heuristic works from day one with zero
  historical feedback.
- The formula is simple enough to audit in a code review. The four components
  and their weights can be understood without machine learning knowledge.
- All parameters are configurable: operators who disagree with the defaults can
  tune the weights without modifying source code.
- The formula is cheap to compute: three arithmetic operations and a table lookup
  per memory. A Redis cache makes repeated lookups negligible.

**Negative**
- The weights (0.4, 0.3, 0.2, 0.1) are chosen by intuition and are not validated
  against real usage data. Early users may find the defaults poorly calibrated for
  their workload.
- Access count conflates meaningful access (a deliberate lookup) with incidental
  access (a memory returned as a side effect of a broad search). The heuristic
  cannot distinguish these.
- The recency component penalizes memories that are important but rarely needed
  (e.g., emergency procedures, reference configurations). Operators must increase
  the confidence field on such memories to compensate.
- There is no feedback loop: if the system incorrectly expires an important memory,
  there is no signal that updates the scoring model. An ML model with explicit
  feedback would self-correct over time.

---

## Alternatives Considered

**Trained logistic regression classifier**
Train a binary classifier (important / not important) on memory records labelled
by users. Rejected because there are no labelled training examples at project
inception. A classifier trained on invented data would be worse than a simple
heuristic and would give operators false confidence in its predictions.

**Collaborative filtering**
Infer importance from patterns across multiple users (memories that many users
access tend to be important). Rejected because Enhanced Cognee is a single-user
or small-team system. There is insufficient cross-user data to build meaningful
collaborative signals.

**LLM-based scoring**
Send memory content to a language model and ask it to rate importance (1-10).
Rejected because each scoring call incurs an LLM API cost. With potentially
thousands of memories, scoring all candidates at expiry time would be
prohibitively expensive. LLM scoring may be appropriate for a small set of
finalists after heuristic pre-filtering, but that design is deferred.

**Fixed TTL without importance scoring**
Expire all memories older than N days regardless of importance. Rejected because
it would delete historically important but infrequently accessed memories
(reference facts, critical configurations) while retaining recent but low-value
transient observations.
