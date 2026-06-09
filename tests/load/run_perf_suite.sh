#!/usr/bin/env bash
# ===========================================================================
# Enhanced Cognee -- production-host performance suite (one command)
# ===========================================================================
# Runs the SLA burst and/or the multi-hour soak on a provisioned host. This is
# the turnkey entry point the deploy/terraform/ outputs point at:
#
#   sudo -u cognee /opt/enhanced-cognee/tests/load/run_perf_suite.sh both
#
# Modes:
#   sla    100-user burst, hard PASS/FAIL vs the SLA (>=100 RPS, p95<200ms, 0% err)
#   soak   sustained load for $SOAK_DURATION seconds (default 4h), leak analysis
#   both   sla, then soak (default)
#
# Env overrides:
#   SOAK_DURATION   soak length in seconds (default 14400 = 4h)
#   SOAK_USERS      soak concurrent users (default 40)
#   SLA_USERS       sla burst users (default 100)
#   COMPOSE_FILE    docker compose file (default docker/docker-compose-enhanced-cognee.yml)
#   LOADGEN_LABEL   label recorded in the report (default "on-box")
#
# ASCII-only output.
# ===========================================================================
set -euo pipefail

MODE="${1:-both}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose-enhanced-cognee.yml}"
SOAK_DURATION="${SOAK_DURATION:-14400}"
SOAK_USERS="${SOAK_USERS:-40}"
SLA_USERS="${SLA_USERS:-100}"
LOADGEN_LABEL="${LOADGEN_LABEL:-on-box}"

# Pick a Python with locust + psutil. Prefer the cloud-init perf venv.
if   [ -x "$REPO_ROOT/.venv-perf/bin/python" ]; then PY="$REPO_ROOT/.venv-perf/bin/python"
elif [ -x "$REPO_ROOT/.venv/bin/python" ];      then PY="$REPO_ROOT/.venv/bin/python"
else PY="$(command -v python3)"; fi

log() { printf '[perf-suite] %s\n' "$1"; }

ensure_stack() {
  log "checking docker compose stack ($COMPOSE_FILE)"
  if ! docker compose -f "$COMPOSE_FILE" ps --status running 2>/dev/null | grep -q .; then
    log "stack not running; bringing it up"
    docker compose -f "$COMPOSE_FILE" up -d
  fi
  log "waiting for postgres health"
  for _ in $(seq 1 60); do
    if docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null \
         | grep -qi 'postgres' ; then
      # crude readiness: pg accepting connections
      if docker exec "$(docker compose -f "$COMPOSE_FILE" ps -q postgres 2>/dev/null | head -1)" \
           pg_isready >/dev/null 2>&1; then
        log "postgres ready"; return 0
      fi
    fi
    sleep 2
  done
  log "WARN postgres readiness not confirmed; continuing anyway"
}

run_sla() {
  log "=== SLA burst: $SLA_USERS users ==="
  "$PY" "$SCRIPT_DIR/sla_suite.py" --users "$SLA_USERS" --loadgen "$LOADGEN_LABEL"
}

run_soak() {
  log "=== Soak: $SOAK_USERS users for ${SOAK_DURATION}s ==="
  "$PY" "$SCRIPT_DIR/soak_test.py" --duration "$SOAK_DURATION" --users "$SOAK_USERS"
}

ensure_stack
case "$MODE" in
  sla)  run_sla ;;
  soak) run_soak ;;
  both) run_sla || log "SLA did not pass; continuing to soak"; run_soak ;;
  *) echo "usage: $0 [sla|soak|both]" >&2; exit 64 ;;
esac

log "done. Reports in tests/benchmarks/output/"
