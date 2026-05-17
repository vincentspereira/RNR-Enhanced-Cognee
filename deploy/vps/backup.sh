#!/usr/bin/env bash
# Nightly backup for Enhanced Cognee VPS deployment.
# Run via cron: 30 2 * * * /usr/local/bin/cognee-backup
#
# Backs up:
#   - PostgreSQL (pg_dump custom format, compressed)
#   - Qdrant (snapshot via HTTP API)
#   - Neo4j (cypher-shell export of all data)
#   - Redis (BGSAVE + copy dump.rdb)
#
# Rotates backups older than 30 days.

set -euo pipefail

BACKUP_DIR="/var/backups/enhanced-cognee"
DATE=$(date +%Y%m%d-%H%M%S)
TARGET="$BACKUP_DIR/$DATE"
RETENTION_DAYS=30

mkdir -p "$TARGET"
echo "[$(date)] Starting backup -> $TARGET"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log()  { printf '[%s] [INFO] %s\n' "$(date +%H:%M:%S)" "$1"; }
warn() { printf '[%s] [WARN] %s\n' "$(date +%H:%M:%S)" "$1" >&2; }
err()  { printf '[%s] [ERR]  %s\n' "$(date +%H:%M:%S)" "$1" >&2; }

# ---------------------------------------------------------------------------
# 1. PostgreSQL
# ---------------------------------------------------------------------------

log "Backing up PostgreSQL"
if docker exec cognee-mcp-postgres pg_dump \
    -U cognee_user -d cognee_db \
    -Fc -Z9 \
    > "$TARGET/postgres-cognee_db.dump" 2>/dev/null; then
    size=$(du -h "$TARGET/postgres-cognee_db.dump" | cut -f1)
    log "  postgres dump OK ($size)"
else
    err "  postgres dump FAILED"
fi

# ---------------------------------------------------------------------------
# 2. Qdrant
# ---------------------------------------------------------------------------

log "Backing up Qdrant collections"
collections=$(curl -sf http://localhost:26333/collections | python3 -c 'import sys,json; [print(c["name"]) for c in json.load(sys.stdin)["result"]["collections"]]' 2>/dev/null || true)

if [ -n "$collections" ]; then
    for coll in $collections; do
        log "  snapshot collection: $coll"
        snap=$(curl -sf -X POST "http://localhost:26333/collections/$coll/snapshots" \
            | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["name"])' 2>/dev/null || echo "")
        if [ -n "$snap" ]; then
            curl -sf "http://localhost:26333/collections/$coll/snapshots/$snap" \
                -o "$TARGET/qdrant-$coll-$snap" && log "    saved $snap" || warn "    download failed"
        fi
    done
else
    log "  no collections to back up"
fi

# ---------------------------------------------------------------------------
# 3. Neo4j (cypher-shell export)
# ---------------------------------------------------------------------------

log "Backing up Neo4j"
if docker exec cognee-mcp-neo4j cypher-shell \
    -u neo4j -p cognee_password \
    "CALL apoc.export.cypher.all('/var/lib/neo4j/import/backup-${DATE}.cypher', {format:'cypher-shell'})" \
    > /dev/null 2>&1; then
    docker cp "cognee-mcp-neo4j:/var/lib/neo4j/import/backup-${DATE}.cypher" "$TARGET/neo4j-backup.cypher" 2>/dev/null \
        && gzip "$TARGET/neo4j-backup.cypher" \
        && log "  neo4j export OK ($(du -h "$TARGET/neo4j-backup.cypher.gz" | cut -f1))" \
        || warn "  neo4j cp failed (APOC plugin may not be installed)"
else
    # Fallback: plain dump-database (single-database only)
    log "  APOC not available, trying neo4j-admin dump"
    docker exec cognee-mcp-neo4j neo4j-admin database dump neo4j --to-path=/data 2>/dev/null || true
    docker cp cognee-mcp-neo4j:/data/neo4j.dump "$TARGET/neo4j-dump.bin" 2>/dev/null \
        && log "  neo4j dump OK" \
        || warn "  neo4j dump failed (database may be running)"
fi

# ---------------------------------------------------------------------------
# 4. Valkey (cache; Apache-2.0 Redis replacement)
# ---------------------------------------------------------------------------

log "Backing up Valkey"
docker exec cognee-mcp-valkey valkey-cli BGSAVE > /dev/null
sleep 3   # let BGSAVE finish for small dbs
docker cp cognee-mcp-valkey:/data/dump.rdb "$TARGET/valkey-dump.rdb" 2>/dev/null \
    && log "  valkey dump OK ($(du -h "$TARGET/valkey-dump.rdb" | cut -f1))" \
    || warn "  valkey dump failed"

# ---------------------------------------------------------------------------
# 5. Manifest
# ---------------------------------------------------------------------------

cat > "$TARGET/MANIFEST.txt" <<EOF
Enhanced Cognee Backup
======================
Date:       $(date -Iseconds)
Hostname:   $(hostname)
Files:
$(ls -lh "$TARGET" | tail -n +2)

Restore notes:
  - postgres-cognee_db.dump : pg_restore -U cognee_user -d cognee_db --clean
  - qdrant-*                 : POST to /collections/<name>/snapshots/upload
  - neo4j-backup.cypher.gz   : zcat | cypher-shell -u neo4j -p ...
  - redis-dump.rdb           : stop redis, copy to /data/dump.rdb, start
EOF

# ---------------------------------------------------------------------------
# 6. Rotation
# ---------------------------------------------------------------------------

log "Rotating backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -exec rm -rf {} \;

total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Backup complete. Total backup dir size: $total_size"
