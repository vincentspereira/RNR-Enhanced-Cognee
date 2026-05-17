# Enhanced Cognee Operations Runbook

A copy-pasteable playbook for the 10 most common incidents.

**Severity legend:** P0 = production down; P1 = degraded; P2 = warning; P3 = informational.

---

## 1. Postgres container is down (P0)

**Symptoms:** All `add_memory` / `search_memories` return errors. `health()` shows postgres = FAIL.

**Diagnose:**
```bash
docker ps -a --filter name=cognee-mcp-postgres
docker logs cognee-mcp-postgres --tail 50
```

**Fix:**
```bash
# Restart the container
docker restart cognee-mcp-postgres

# If that fails, recreate (DATA IS PRESERVED on the named volume)
cd /opt/enhanced-cognee   # (or your repo path)
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d postgres

# Verify
docker exec cognee-mcp-postgres pg_isready -U cognee_user
```

**Root-cause checks:** disk full (`df -h`), OOM kill (`dmesg | grep -i kill`), corrupted WAL (`docker logs cognee-mcp-postgres | grep -i recovery`).

---

## 2. Qdrant queries slow (P1)

**Symptoms:** Search latency > 1s, `get_slow_queries()` shows Qdrant hot.

**Diagnose:**
```bash
curl http://localhost:26333/collections | jq '.result.collections[] | {name: .name, points_count: .points_count}'
curl http://localhost:26333/collections/<collection>/cluster
```

**Fix (in priority order):**
1. **Restart Qdrant** (often a transient memory issue):
   ```bash
   docker restart cognee-mcp-qdrant
   ```
2. **Optimize collection** (rebuilds HNSW indices):
   ```bash
   curl -X POST http://localhost:26333/collections/<collection>/optimize
   ```
3. **Reduce `ef` search parameter** in `src/agent_memory_integration.py` to trade recall for speed.
4. **Scale up:** if you're on Hetzner CX22, upgrade to CX32 (4 vCPU / 8 GB).

---

## 3. Undo log table full (P2)

**Symptoms:** `undo_last()` errors with disk-related messages. Postgres disk usage growing fast.

**Diagnose:**
```sql
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  SELECT pg_size_pretty(pg_total_relation_size('shared_memory.undo_log')) AS size,
         count(*) AS rows
  FROM shared_memory.undo_log;
"
```

**Fix:**
```sql
-- Run cleanup_expired_entries (deletes >24h old by default)
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  DELETE FROM shared_memory.undo_log
  WHERE expiration_date < NOW() - INTERVAL '24 hours';
"

-- Reclaim space
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  VACUUM FULL ANALYZE shared_memory.undo_log;
"
```

**Prevent recurrence:** schedule `cleanup_expired_entries()` daily (or use `auto_scheduler.cleanup_expired_undo`).

---

## 4. Backup script failure (P1)

**Symptoms:** No new files in `/var/backups/enhanced-cognee/` overnight. `/var/log/cognee-backup.log` shows ERR lines.

**Diagnose:**
```bash
tail -100 /var/log/cognee-backup.log
ls -lh /var/backups/enhanced-cognee/
df -h /var/backups
```

**Fix:**
1. **Disk full:** prune old backups manually:
   ```bash
   find /var/backups/enhanced-cognee -mtime +14 -type d -exec rm -rf {} +
   ```
2. **pg_dump auth failure:** confirm `POSTGRES_PASSWORD` in `/etc/enhanced-cognee/secrets.env` matches what's in Postgres.
3. **Neo4j export failure:** install APOC plugin (`apoc.export.cypher.all`) or accept the fallback `neo4j-admin database dump`.

Re-run manually:
```bash
sudo /usr/local/bin/cognee-backup
```

---

## 5. Disk full on VPS (P0)

**Symptoms:** Everything fails. `df -h` shows 100% on `/`.

**Diagnose:**
```bash
# Top 20 biggest dirs
sudo du -h --max-depth=2 / 2>/dev/null | sort -rh | head -20

# Docker disk usage
docker system df
```

**Fix (immediate):**
```bash
# Prune dead Docker resources
docker system prune -af --volumes  # WARNING: removes unused volumes too

# Truncate biggest logs
sudo truncate -s 100M /var/log/syslog
sudo journalctl --vacuum-size=200M

# Old backups
find /var/backups/enhanced-cognee -mtime +14 -type d -exec rm -rf {} +
```

**Prevent:** add log rotation for `/var/log/caddy/`, `/var/log/cognee-backup.log`.

---

## 6. Network partition / Docker bridge issue (P0)

**Symptoms:** MCP server logs show "connection refused" to one or more DBs even though `docker ps` shows them healthy.

**Diagnose:**
```bash
# Can MCP container reach Postgres?
docker exec cognee-mcp-postgres pg_isready -h localhost  # via container's own loopback
# Test from host:
nc -zv localhost 25432
```

**Fix:**
```bash
# Recreate the network
cd /opt/enhanced-cognee
docker compose -f docker/docker-compose-enhanced-cognee.yml down
docker network prune -f
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
```

---

## 7. Container OOM-killed (P1)

**Symptoms:** A container restarts repeatedly. `docker logs <container>` shows OOM messages or abrupt termination.

**Diagnose:**
```bash
docker inspect <container> --format='{{.State.OOMKilled}} -- {{.State.ExitCode}}'
dmesg | grep -i "killed process"
free -h
```

**Fix:**
1. **Raise the container memory limit** in `docker/docker-compose-enhanced-cognee.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G   # was 512M
   ```
   then `docker compose up -d --force-recreate <service>`.
2. **Reduce workload:** lower `--workers 2` to `--workers 1` in systemd unit.
3. **Scale up the VPS.**

---

## 8. TLS cert expiry (P1)

**Symptoms:** Browsers show cert warning. `curl` fails with `certificate has expired`.

**Diagnose:**
```bash
echo | openssl s_client -servername cognee.example.com -connect cognee.example.com:443 2>/dev/null | openssl x509 -noout -dates
sudo journalctl -u caddy | grep -i "tls\|cert"
```

**Fix:** Caddy auto-renews. If it's stuck:
```bash
sudo systemctl restart caddy
# Force a cert refresh:
sudo caddy reload --config /etc/caddy/Caddyfile
```

Common cause: DNS A record changed, port 80 blocked (Let's Encrypt HTTP-01
challenge needs port 80 reachable).

---

## 9. MCP server hangs (P0)

**Symptoms:** `claude mcp list` shows the server as `Failed to connect`. Tool calls time out.

**Diagnose:**
```bash
# Is the process even running?
sudo systemctl status enhanced-cognee
# Stuck on something?
sudo journalctl -u enhanced-cognee --since "5 minutes ago" | tail -50
# Check for deadlock symptoms:
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  SELECT pid, state, wait_event_type, wait_event, query
  FROM pg_stat_activity
  WHERE state != 'idle'
  ORDER BY query_start;
"
```

**Fix:**
```bash
# Hard restart
sudo systemctl restart enhanced-cognee

# If postgres has stuck locks:
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state != 'idle' AND query_start < NOW() - INTERVAL '5 minutes';
"
```

---

## 10. Schema migration failure (P1)

**Symptoms:** New code fails because expected tables/columns don't exist. `undo_log` or other schema not yet created.

**Diagnose:**
```bash
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  SELECT schemaname, tablename
  FROM pg_catalog.pg_tables
  WHERE schemaname = 'shared_memory'
  ORDER BY tablename;
"
```

**Fix (each manager creates its schema lazily on first use):**

```bash
# Force schema creation via Python
cd /opt/enhanced-cognee
source .venv/bin/activate
python -c "
import asyncio, asyncpg
from src.undo_manager import UndoManager

async def main():
    pool = await asyncpg.create_pool(
        host='localhost', port=25432,
        database='cognee_db', user='cognee_user', password='cognee_password'
    )
    mgr = UndoManager(db_pool=pool)
    await mgr._ensure_schema()
    print('OK schema created')

asyncio.run(main())
"
```

For a more permanent fix, install Alembic and convert lazy `_ensure_schema()`
calls into versioned migrations (see Phase F10 in the production plan).

---

## Escalation Path

1. **For all P0 incidents:** trigger the on-call rotation (configure in
   `notification_manager` Slack / email channels).
2. **For data-loss risk:** stop writes immediately via
   `docker compose -f docker/docker-compose-enhanced-cognee.yml stop postgres`.
3. **Post-incident:** open a GitHub issue labelled `incident` with a copy of
   the relevant log lines and the runbook step that fixed it.

## Useful one-liners

```bash
# All container health at a glance
docker ps --format "table {{.Names}}\t{{.Status}}"

# Tail combined logs
docker compose -f /opt/enhanced-cognee/docker/docker-compose-enhanced-cognee.yml logs -f --tail=50

# Postgres connection count
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"

# Top 10 slowest queries (from pg_stat_statements if enabled)
docker exec cognee-mcp-postgres psql -U cognee_user -d cognee_db -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC LIMIT 10;
"

# Qdrant total memory size
curl -s http://localhost:26333/collections | jq '.result.collections[].points_count' | awk '{s+=$1} END {print s, "points"}'

# Redis memory + key count
docker exec cognee-mcp-redis redis-cli INFO memory | grep used_memory_human
docker exec cognee-mcp-redis redis-cli DBSIZE
```
