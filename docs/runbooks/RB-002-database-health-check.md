# Runbook RB-002: Database Health Check and Recovery

**Applies to:** RNR Enhanced Cognee 1.0.9-enhanced and later
**Audience:** Developers and operators

---

## When to Use This Runbook

Use this runbook when:
- The RNR-Enhanced-Cognee health command reports [FAIL] for one or more databases
- MCP tools return [ERR] messages mentioning a specific database
- The MCP server starts but some tools return no results

---

## Step 1: Run the Health Check Command

    RNR-Enhanced-Cognee health

Review each line. Identify which databases show [FAIL]. A healthy output looks like:

    RNR Enhanced Cognee Health Check
    --------------------------------
    [OK] PostgreSQL  localhost:25432
    [OK] Qdrant      localhost:26333
    [OK] Neo4j       localhost:27687
    [OK] Redis       localhost:26379

Proceed to Step 2 only for services that show [FAIL].

---

## Step 2: Check Docker Container Status

    docker ps --filter name=enhanced

All four containers should appear with status "Up". If a container is absent or
shows "Exited", view its logs:

    docker logs postgres-enhanced   --tail 50
    docker logs qdrant-enhanced     --tail 50
    docker logs neo4j-enhanced      --tail 50
    docker logs redis-enhanced      --tail 50

Common log messages and causes:

- "data directory has wrong ownership" - volume permission issue (see below)
- "address already in use" - port conflict with another process
- "out of memory" - host machine has insufficient RAM; stop other containers

---

## Step 3: Restart Failed Containers

    RNR-Enhanced-Cognee docker up

This restarts any stopped containers without affecting running ones. Wait 15 seconds
for databases to initialise, then rerun:

    RNR-Enhanced-Cognee health

If a container fails to start after two attempts, proceed to manual verification.

---

## Step 4: Manual Connection Verification

Use these commands to verify connectivity independently of the RNR Enhanced Cognee CLI.

**PostgreSQL:**

    docker exec -it postgres-enhanced psql \
      -U cognee_user -d cognee_db \
      -c "SELECT COUNT(*) FROM shared_memory.documents;"

**Redis:**

    docker exec -it redis-enhanced redis-cli PING
    # Expected: PONG

**Qdrant:**

    curl -s http://localhost:26333/collections
    # Expected: {"result":{"collections":[...]},"status":"ok","time":...}

**Neo4j (requires cypher-shell inside the container):**

    docker exec -it neo4j-enhanced cypher-shell \
      -u neo4j -p your-db-password \
      "MATCH (n) RETURN count(n) AS node_count;"

---

## Step 5: Volume Permission Recovery (PostgreSQL)

If the PostgreSQL log shows "data directory has wrong ownership":

    docker compose -f config/docker/docker-compose-enhanced-cognee.yml down -v
    docker compose -f config/docker/docker-compose-enhanced-cognee.yml up -d

Warning: the -v flag removes named volumes. Data stored in PostgreSQL will be lost
unless a backup was taken (see RB-003).

---

## Step 6: Final Verification

After recovery, rerun the health check and confirm all lines show [OK]:

    RNR-Enhanced-Cognee health

If [FAIL] persists for a specific database after following the steps above, open
an issue and include the output of:

    docker logs <container-name> --tail 100
    docker inspect <container-name>
