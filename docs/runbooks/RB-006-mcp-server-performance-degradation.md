# Runbook RB-006: MCP Server Performance Degradation

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Operators, developers on-call

---

## Overview

This runbook covers the investigation and remediation of MCP server performance
problems: slow tool response times, high CPU usage, and unbounded memory growth.
Follow the diagnosis steps in order. Each step narrows the root cause before
applying a fix.

---

## Symptoms

- Tool calls that normally complete in under 500 ms are taking more than 2 seconds.
- The MCP server process shows high CPU in docker stats or Task Manager.
- The MCP server process memory usage grows over hours without plateauing.
- Callers receive timeout errors from the MCP client.
- The get_slow_queries tool returns a non-empty list.

---

## Diagnosis Steps

### Step 1: Confirm the server is responding

    Tool: health

Expected output when healthy:

    Enhanced Cognee Health Check
    [OK] PostgreSQL  localhost:25432
    [OK] Qdrant      localhost:26333
    [OK] Neo4j       localhost:27687
    [OK] Redis       localhost:26379

If any database shows [FAIL], performance degradation may be caused by a missing
database connection. Follow RB-002 (Database Health Check) for that database before
continuing with this runbook.

---

### Step 2: Check Prometheus metrics for the slow tool

    Tool: get_prometheus_metrics

Look for these metrics in the output:

    mcp_tool_duration_seconds_p99
    mcp_tool_call_total
    mcp_tool_error_total

Identify which tool name has an elevated p99 latency. Record the tool name for
Step 3.

If get_prometheus_metrics itself times out, the server is severely degraded. Skip
to Fix Step 4 (restart).

---

### Step 3: Identify slow database queries

    Tool: get_slow_queries

This returns queries from pg_stat_activity and pg_stat_statements that have a
mean execution time above the configured slow query threshold (default 500 ms).

Example output:

    [INFO] Slow query report (queries above 500ms mean)
    1. mean=2340ms  calls=41  query=SELECT * FROM shared_memory.documents
       WHERE content LIKE '%keyword%'
    2. mean=890ms   calls=12  query=SELECT * FROM shared_memory.observations
       WHERE agent_id = $1

A full-table scan on the content column (LIKE query) indicates that a search
operation is bypassing the vector index and falling back to PostgreSQL text search.
This is common when the Qdrant connection is down and the server is degrading
gracefully (ADR-005).

An observations query without an index hit indicates the entity+attribute index
may be missing (check that the Alembic migration 0012 was applied; see RB-010).

---

### Step 4: Check connection pool exhaustion

Run from the host where the MCP server process is running:

    docker exec -it postgres-enhanced psql -U cognee_user -d cognee_db \
      -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

If the count of "idle" connections equals the configured pool size (default 20)
and the count of "active" connections is also near 20, the pool is exhausted.
Callers are queuing waiting for a free connection, which explains latency spikes.

Also check the MCP server startup logs for the line:

    [INFO] PostgreSQL pool: min=2 max=20 timeout=30

Confirm the pool size matches expectations. If a recent config change reduced the
pool size incorrectly, Fix Step 2 applies.

---

### Step 5: Check circuit breaker states

    Tool: health

Look for any component reported as [DEGRADED] rather than [OK] or [FAIL].
[DEGRADED] means the circuit breaker is open: the server is not sending requests
to that database but is retrying periodically. Requests that depend on that
database are failing fast (which is good) but may be generating unexpected load
on other components.

If Neo4j shows [DEGRADED], graph-intensive tools (extract_graph_v2, get_graph)
are failing fast. If those tools are being called in a loop by an agent, the loop
may generate high CPU on the MCP server even though each call is fast.

---

## Fix Steps

### Fix 1: Missing vector index - force Qdrant reconnect

If Step 3 identified that searches are hitting PostgreSQL with LIKE queries instead
of Qdrant:

1. Confirm Qdrant is running:

       docker ps --filter name=qdrant-enhanced

   If the container is stopped, start it:

       docker start qdrant-enhanced

2. Wait 10 seconds for the health check cycle, then verify:

       Tool: health
       Expected: [OK] Qdrant localhost:26333

3. Re-run the slow search that was identified in Step 3. Confirm it now completes
   in under 500 ms.

---

### Fix 2: Connection pool too small

If Step 4 identified pool exhaustion:

1. Open .env and increase the pool size:

       POSTGRES_POOL_MAX=40

2. Restart the MCP server:

       enhanced-cognee stop
       enhanced-cognee start

3. Re-run the pg_stat_activity query from Step 4 and confirm idle connections
   are now available.

[WARN] Do not set POSTGRES_POOL_MAX above 100 without also adjusting PostgreSQL's
max_connections (default 100). If Enhanced Cognee's pool size exceeds
max_connections, new connections will be rejected.

---

### Fix 3: Enable or warm up Redis caching

If Step 2 showed high call counts on a single tool with moderate latency:

1. Confirm Redis is running:

       docker ps --filter name=redis-enhanced

2. Check if result caching is enabled in .enhanced-cognee-config.json:

       {
         "cache": {
           "enabled": true,
           "default_ttl_seconds": 300
         }
       }

   If "enabled" is false or the key is missing, set it to true and restart:

       enhanced-cognee stop
       enhanced-cognee start

3. After the server restarts, re-run the slow tool twice. The second call should
   return from cache and complete in under 50 ms.

---

### Fix 4: Restart the MCP server if memory leak is suspected

If the server process memory has grown continuously for several hours without
plateauing and no other fix resolves the latency:

1. Check current process memory:

       docker stats enhanced-cognee-mcp --no-stream

   Note the MEM USAGE value.

2. Stop the server:

       enhanced-cognee stop

3. Start the server:

       enhanced-cognee start

4. Monitor memory over the next 30 minutes:

       watch -n 30 "docker stats enhanced-cognee-mcp --no-stream"

   If memory grows linearly again, a memory leak exists in the server process.
   Open a GitHub issue with the metric values and the tool identified in Step 2.

---

### Fix 5: Disable a runaway tool call loop

If Step 5 identified a circuit-breaker [DEGRADED] state AND tool error counts in
Step 2 are very high (thousands per minute):

1. Identify which agent is making the calls. Check MCP server logs:

       enhanced-cognee logs --tail 200

   Look for lines with the pattern:

       [ERR] tool=<tool_name> agent_id=<agent_id> reason=circuit_open

2. If a specific agent_id is making calls at an abnormal rate, temporarily revoke
   its rate limit override:

       Tool: update_memory
       Locate the agent's rate limit config and remove any override.

   Or block the agent temporarily by setting its rate limit to 0 in
   .enhanced-cognee-config.json and restarting the server.

3. Investigate why the agent entered a retry loop before re-enabling it.

---

## Verification

After applying any fix:

1. Confirm the health tool shows all components [OK].
2. Run the tool that was identified as slow in Step 2 and confirm p99 latency
   is below 500 ms.
3. Confirm get_slow_queries returns no results above the threshold.
4. Monitor get_prometheus_metrics for 5 minutes to ensure no regression.

---

## Postmortem Template

Use this template to document the incident after it is resolved.

    Incident: MCP Server Performance Degradation
    Date: YYYY-MM-DD
    Duration: HH:MM (time from first alert to resolution)
    Severity: [Low / Medium / High / Critical]

    Timeline:
    - HH:MM  First symptom observed (tool timeouts, user report, alert)
    - HH:MM  Diagnosis started (this runbook opened)
    - HH:MM  Root cause identified (Step N: <description>)
    - HH:MM  Fix applied (Fix N: <description>)
    - HH:MM  Verification passed
    - HH:MM  Incident closed

    Root Cause:
    <One paragraph describing the technical root cause.>

    Contributing Factors:
    <List any configuration, workload, or environmental factors that contributed.>

    Fix Applied:
    <What was changed or restarted.>

    Prevention:
    <What change to code, configuration, monitoring, or process would prevent
    a recurrence? Include a GitHub issue or PR number if one was created.>

    Follow-up Actions:
    - [ ] Action 1 (owner, due date)
    - [ ] Action 2 (owner, due date)
