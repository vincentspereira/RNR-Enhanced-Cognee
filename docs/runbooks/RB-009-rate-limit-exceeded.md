# Runbook RB-009: Per-Agent Rate Limit Exceeded

**Applies to:** Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Operators, developers

---

## Overview

Enhanced Cognee enforces per-agent rate limits on MCP tool calls to prevent a
single agent from monopolizing server resources or triggering runaway loops. When
an agent exceeds its configured rate limit, all subsequent calls within the rate
window return an error response. This runbook guides the operator through
diagnosing the cause and restoring normal operation.

---

## Symptoms

- An agent's tasks are failing with the error:

      [ERR] Rate limit exceeded for agent_id=<agent_id>. Retry after N seconds.

- The agent's calling application reports repeated failures on a specific tool.
- MCP server logs contain many lines of the form:

      [WARN] rate_limit agent_id=<agent_id> tool=<tool_name> window=60s limit=100

- The get_search_analytics or get_performance_metrics tools show an abnormally
  high call count for a specific agent in a recent time window.

---

## Diagnosis Steps

### Step 1: Confirm the rate limit error

Call the health tool to ensure the server is responsive and the error is rate-limit
specific rather than a broader outage:

    Tool: health
    Expected: all components [OK]

If health shows database failures, follow RB-002 before this runbook. Rate limit
errors during a partial outage may be a symptom of retry loops triggered by
connection failures.

---

### Step 2: Identify the agent and call pattern

Check MCP server logs for the affected agent:

    enhanced-cognee logs --tail 500 | grep "rate_limit"

Note:
- Which agent_id is hitting the limit.
- Which tool is being called most frequently.
- The rate (calls per minute) in the log lines.

Also query the analytics tool:

    Tool: get_search_analytics
    Parameters:
      agent_id: <agent_id>
      time_window_minutes: 60

Review the call_count_by_tool field. A call count of several hundred per minute
on a single tool suggests a retry loop. A call count spread across many tools
suggests legitimate high-volume work.

---

### Step 3: Check the configured rate limit

View the current rate limit configuration:

    Tool: get_stats

Look for the section:

    rate_limits:
      default_calls_per_minute: 100
      per_agent_overrides:
        <agent_id>: 200

Also check .enhanced-cognee-config.json:

    {
      "rate_limits": {
        "default_calls_per_minute": 100,
        "per_agent_overrides": {}
      }
    }

Compare the configured limit against the actual call rate from Step 2. If the
call rate is legitimately high (e.g., a batch processing agent ingesting many
documents), Fix Step 1 applies. If the call rate is unexpectedly high (e.g., a
100 calls-per-minute agent hammering a single tool), Fix Step 2 applies.

---

### Step 4: Check Redis rate limiter state

The rate limiter uses Redis to store the sliding window counter. Confirm Redis is
running and the counter key exists:

    docker exec -it redis-enhanced redis-cli TTL "rate:<agent_id>"

If the command returns -2, the key does not exist (the window has already expired
and the agent's counter has reset). The rate limit will not recur unless the agent
hits the limit again in the next window.

If the command returns a positive number, the key exists and the window is still
active. The agent is still blocked for that many more seconds.

---

## Fix Steps

### Fix 1: Temporarily increase the rate limit for a legitimate high-volume agent

If the agent has a legitimate need for more than the default calls per minute:

1. Open .enhanced-cognee-config.json and add or update the per-agent override:

       {
         "rate_limits": {
           "default_calls_per_minute": 100,
           "per_agent_overrides": {
             "<agent_id>": 500
           }
         }
       }

2. Restart the MCP server to apply the change:

       enhanced-cognee stop
       enhanced-cognee start

3. Verify the new limit is active:

       Tool: get_stats
       Confirm: rate_limits.per_agent_overrides.<agent_id>: 500

4. Monitor the agent's call rate for 15 minutes after re-enabling:

       Tool: get_search_analytics
       Parameters:
         agent_id: <agent_id>
         time_window_minutes: 15

If the call rate remains within the new limit and the agent's tasks complete
successfully, the fix is complete.

---

### Fix 2: Investigate and stop a runaway retry loop

If Step 2 identified that the agent is calling a single tool at an abnormal rate
(e.g., 300 calls per minute on add_memory):

1. Check whether the tool is returning errors that trigger retries:

       enhanced-cognee logs --tail 200 | grep "<agent_id>"

   Look for repeated [ERR] responses from the same tool. If the tool is
   consistently failing and the agent is retrying without backoff, the agent is
   in a retry loop.

2. Identify the calling application or script that runs the agent. Stop it:

       # If the agent is a script running in a terminal, press Ctrl+C to stop it.
       # If the agent is running as a background process:
       ps aux | grep <agent_script_name>
       kill <pid>

3. Diagnose why the tool is failing. Common causes:

       - Database connection lost (check health tool)
       - Invalid parameters passed by the agent (check tool input in logs)
       - Missing required configuration (check get_stats)

4. Fix the root cause, then restart the agent with retry backoff implemented.
   Exponential backoff pattern:

       import time

       def call_with_backoff(tool_fn, max_retries=5):
           for attempt in range(max_retries):
               try:
                   return tool_fn()
               except RateLimitError as e:
                   if attempt == max_retries - 1:
                       raise
                   wait = 2 ** attempt
                   time.sleep(wait)

---

### Fix 3: Clear the Redis rate limit key for an agent (emergency unblock)

If a legitimate agent must be unblocked immediately (e.g., a critical pipeline
is blocked by a rate limit that was triggered by a now-fixed bug):

1. Confirm the scenario is legitimate. Clearing the rate limit key bypasses
   the protection for the remainder of the window.

2. Delete the Redis key:

       docker exec -it redis-enhanced redis-cli DEL "rate:<agent_id>"

3. Verify the key is gone:

       docker exec -it redis-enhanced redis-cli TTL "rate:<agent_id>"
       Expected: -2 (key does not exist)

4. The agent can now make calls again. Monitor for recurrence of the high call
   rate to confirm the loop is resolved.

---

### Fix 4: Add Redis-based rate limit override for a specific tool

If a specific tool (not the agent globally) needs a higher limit:

1. Open .enhanced-cognee-config.json and add a per-tool override:

       {
         "rate_limits": {
           "default_calls_per_minute": 100,
           "per_tool_overrides": {
             "add_memory": 300,
             "search_memories": 200
           }
         }
       }

2. Restart the MCP server.

3. Verify with get_stats that the per-tool override appears in the rate_limits
   section.

---

## Verification

After applying any fix:

1. Confirm the affected agent can call tools successfully:

       Tool: health
       Expected: all components [OK]

2. Call the tool that was rate-limited on behalf of the affected agent and
   confirm it returns a valid result (not a rate limit error).

3. Monitor get_search_analytics for the agent over the next 15 minutes. Confirm
   the call rate is within the configured limit.

4. If Fix 2 was applied, confirm the agent is not re-entering the retry loop
   by checking logs for recurrence of the high call rate.

---

## Postmortem Template

    Incident: Per-Agent Rate Limit Exceeded
    Date: YYYY-MM-DD
    Agent affected: <agent_id>
    Duration: HH:MM (time from first [ERR] to restored operation)

    Metrics at incident time:
    - Configured limit: N calls/minute
    - Actual call rate: N calls/minute
    - Tool most called: <tool_name>
    - Error count: N

    Timeline:
    - HH:MM  First rate limit [ERR] observed
    - HH:MM  Operator alerted
    - HH:MM  Root cause identified (Step N)
    - HH:MM  Fix applied (Fix N)
    - HH:MM  Agent resumed normal operation

    Root Cause:
    <Was the limit too low for legitimate workload, or was the agent in a retry
    loop? Describe the specific condition that led to the high call rate.>

    Fix Applied:
    <Which fix step was used. What configuration was changed or what process
    was stopped.>

    Prevention:
    <Increase default limit? Add alerting when call rate exceeds X% of limit?
    Require retry backoff in agent SDK? Document as a known high-volume agent?>

    Follow-up Actions:
    - [ ] Action 1 (owner, due date)
    - [ ] Action 2 (owner, due date)
