# Enhanced Cognee - Convenience targets for development and operations.
# Cross-platform: works on Linux/macOS (GNU make) and Windows (via PowerShell or bash).
# All targets are idempotent and safe to re-run.

.PHONY: help install test test-fast test-cov test-int test-load test-bench \
        lint format stack-up stack-down stack-logs stack-status \
        smoke clean docs

# ============================================================================
# Defaults
# ============================================================================

# Env vars for live integration tests (override on command line if needed)
export POSTGRES_HOST   ?= localhost
export POSTGRES_PORT   ?= 25432
export POSTGRES_DB     ?= cognee_test_db
export POSTGRES_USER   ?= cognee_test_user
export POSTGRES_PASSWORD ?= cognee_test_password
export QDRANT_HOST     ?= localhost
export QDRANT_PORT     ?= 26333
export REDIS_HOST      ?= localhost
export REDIS_PORT      ?= 26379
export NEO4J_URI       ?= bolt://localhost:27687
export NEO4J_USER      ?= neo4j
export NEO4J_PASSWORD  ?= cognee_password

PY ?= python
PIP ?= pip
PYTEST ?= $(PY) -m pytest
DOCKER_COMPOSE ?= docker compose
COMPOSE_FILE ?= docker/docker-compose-enhanced-cognee.yml

# ============================================================================
# Help
# ============================================================================

help:	## Show this help
	@echo "Enhanced Cognee - available commands:"
	@echo ""
	@echo "  Development:"
	@echo "    make install      Install Python deps + editable package"
	@echo "    make test         Run full test suite (unit + system + live integration)"
	@echo "    make test-fast    Run only unit tests (no DB required)"
	@echo "    make test-cov     Run tests with coverage report"
	@echo "    make test-int     Run integration + e2e against live Docker stack"
	@echo "    make test-bench   Run performance benchmarks"
	@echo "    make test-load    Run load tests (Locust)"
	@echo "    make lint         Run ruff + black --check"
	@echo "    make format       Auto-fix formatting with black + ruff"
	@echo ""
	@echo "  Docker stack:"
	@echo "    make stack-up     Start postgres + qdrant + neo4j + redis"
	@echo "    make stack-down   Stop the stack (keeps volumes)"
	@echo "    make stack-logs   Tail container logs"
	@echo "    make stack-status Show container health"
	@echo ""
	@echo "  Smoke / cleanup:"
	@echo "    make smoke        Quick health check of stack + MCP server"
	@echo "    make clean        Remove __pycache__, .pytest_cache, htmlcov"
	@echo "    make docs         Open the production-readiness plan"

# ============================================================================
# Install
# ============================================================================

install:	## Install Python dependencies in editable mode
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	$(PIP) install -r requirements-dev.txt 2>/dev/null || $(PIP) install pytest pytest-cov pytest-asyncio pytest-mock pytest-benchmark hypothesis ruff black

# ============================================================================
# Tests
# ============================================================================

test-fast:	## Unit tests only (no live DB)
	$(PYTEST) tests/unit/ tests/system/ -q --tb=short

test:	## Full suite (unit + system + live integration + e2e)
	$(PYTEST) tests/ -q --tb=short

test-cov:	## Tests with terminal coverage report
	$(PYTEST) tests/ --cov=src --cov-report=term-missing --cov-report=html -q

test-int:	## Live integration + e2e against running Docker stack
	$(PYTEST) tests/integration/ tests/e2e/ -q --tb=short

test-bench:	## Pytest-benchmark performance tests
	$(PYTEST) tests/performance/ --benchmark-only --tb=short

test-load:	## Locust load test (headless, 30s smoke)
	locust -f tests/load/locustfile.py --headless --users 50 --spawn-rate 5 --run-time 30s --host http://localhost:8000

# ============================================================================
# Code quality
# ============================================================================

lint:	## Static analysis with ruff + black check
	ruff check src/ tests/
	black --check src/ tests/ --line-length 100

format:	## Auto-format with black + ruff fix
	black src/ tests/ --line-length 100
	ruff check --fix src/ tests/

# ============================================================================
# Docker stack
# ============================================================================

stack-up:	## Bring up postgres + qdrant + neo4j + redis (detached)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d
	@echo "Waiting for services to become healthy..."
	@sleep 10
	@$(MAKE) stack-status

stack-down:	## Stop the stack but keep data volumes
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down

stack-logs:	## Tail logs for all stack containers
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs --tail=50 -f

stack-status:	## Show container health
	@docker ps --filter "name=cognee-mcp-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ============================================================================
# Smoke + cleanup
# ============================================================================

smoke:	## Quick health probe of stack and MCP server
	@echo "[1] Container status:"
	@$(MAKE) stack-status
	@echo ""
	@echo "[2] Postgres ping:"
	@docker exec cognee-mcp-postgres pg_isready -U cognee_user || echo "FAIL"
	@echo "[3] Qdrant /healthz:"
	@curl -s -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:26333/healthz || echo "FAIL"
	@echo "[4] Redis PING:"
	@docker exec cognee-mcp-redis redis-cli PING || echo "FAIL"
	@echo "[5] Neo4j HTTP:"
	@curl -s -o /dev/null -w "  HTTP %{http_code}\n" http://localhost:27474 || echo "FAIL"

clean:	## Remove pyc, caches, coverage artefacts
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache htmlcov .coverage coverage.xml 2>/dev/null || true
	@echo "Cleaned."

docs:	## Open the production-readiness plan
	@echo "Read docs/PRODUCTION_READINESS_PLAN.md or open in your editor"
	@echo "Open in VSCode:  code docs/PRODUCTION_READINESS_PLAN.md"
