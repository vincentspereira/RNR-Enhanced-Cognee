#!/bin/sh
# RNR Enhanced Cognee container entrypoint (POSIX sh).
#
# Responsibilities:
#   1. Optionally run Alembic migrations (set ENHANCED_RUN_MIGRATIONS=1).
#   2. Exec the FastAPI HTTP app under uvicorn on ${PORT:-8080}.
#
# ASCII-only output. This file MUST be executable: chmod +x entrypoint.sh
# (the Dockerfile also runs `chmod +x /app/entrypoint.sh` as a safety net).
set -e

PORT="${PORT:-8080}"

if [ "${ENHANCED_RUN_MIGRATIONS}" = "1" ]; then
    echo "[INFO] ENHANCED_RUN_MIGRATIONS=1 -- running alembic upgrade head"
    # Enhanced stack uses the dedicated alembic config.
    alembic -c alembic-enhanced.ini upgrade head
    echo "[INFO] Migrations complete"
else
    echo "[INFO] Skipping migrations (set ENHANCED_RUN_MIGRATIONS=1 to enable)"
fi

echo "[INFO] Starting uvicorn on 0.0.0.0:${PORT} (src.enhanced_cognee_mcp:app)"
exec uvicorn src.enhanced_cognee_mcp:app --host 0.0.0.0 --port "${PORT}"
