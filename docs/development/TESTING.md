# Enhanced Cognee Testing Guide

## Overview

This document describes the comprehensive testing strategy for Enhanced Cognee, including unit tests, integration tests, system tests, and end-to-end tests.

---

## Test Coverage Goals

- **Code Coverage**: >98%
- **Success Rate**: 100%
- **Warnings**: 0
- **Skipped Tests**: 0

---

## Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_memory_management.py
│   ├── test_memory_deduplication.py
│   ├── test_memory_summarization.py
│   ├── test_performance_analytics.py
│   ├── test_cross_agent_sharing.py
│   └── test_realtime_sync.py
├── integration/             # Integration tests (database required)
│   └── test_database_integration.py
├── system/                  # System tests (full stack)
│   └── test_mcp_server.py
├── e2e/                     # End-to-end tests (user workflows)
│   └── test_complete_workflows.py
├── fixtures/                # Test fixtures and mocks
│   └── __init__.py
└── conftest.py             # Pytest configuration
```

---

## Running Tests

### Run All Tests

```bash
python run_tests.py
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v -m unit

# Integration tests only
pytest tests/integration/ -v -m integration

# System tests only
pytest tests/system/ -v -m system

# End-to-end tests only
pytest tests/e2e/ -v -m e2e
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# Open HTML coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test File

```bash
pytest tests/unit/test_memory_management.py -v
```

### Run Specific Test

```bash
pytest tests/unit/test_memory_management.py::TestMemoryManagerInit::test_init_with_valid_dependencies -v
```

---

## Test Requirements

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

---

## Test Database Setup

### For Unit Tests

Unit tests use **mocked** databases - no setup required.

### For Integration Tests

Integration tests require real databases:

```bash
# Start Enhanced databases
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d

# Verify databases are running
docker ps | grep enhanced
```

### For System Tests

System tests require the MCP server to be configured:

```bash
# Set environment variables
export ENHANCED_COGNEE_MODE=true
export POSTGRES_HOST=localhost
export POSTGRES_PORT=25432
# ... (see .env.example)
```

---

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual functions and classes in isolation

**Characteristics**:
- Fast execution (< 1 second per test)
- No external dependencies
- Use mocks for databases

**Example**:
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_expire_memories(memory_manager):
    result = await memory_manager.expire_old_memories(days=90)
    assert result["status"] == "success"
```

**Markers**: `@pytest.mark.unit`

---

### 2. Integration Tests

**Purpose**: Test integration between modules and real databases

**Characteristics**:
- Require PostgreSQL, Qdrant, Redis
- Test real database operations
- Clean up test data after execution

**Example**:
```python
@pytest.mark.integration
@pytest.mark.postgresql
@pytest.mark.asyncio
async def test_create_and_query_memory(real_postgres_pool):
    async with real_postgres_pool.acquire() as conn:
        await conn.execute("INSERT INTO ...")
        result = await conn.fetchrow("SELECT ...")
        assert result is not None
```

**Markers**: `@pytest.mark.integration`, `@pytest.mark.postgresql`, `@pytest.mark.qdrant`, `@pytest.mark.redis`

---

### 3. System Tests

**Purpose**: Test the complete MCP server system

**Characteristics**:
- Test server initialization
- Verify tool registration
- Test configuration

**Example**:
```python
@pytest.mark.system
def test_all_tools_registered():
    import enhanced_cognee_mcp_server as server
    expected_tools = ["add_memory", "search_memories", ...]
    for tool in expected_tools:
        assert hasattr(server, tool)
```

**Markers**: `@pytest.mark.system`

---

### 4. End-to-End Tests

**Purpose**: Test complete user workflows

**Characteristics**:
- Test multi-step workflows
- Simulate real usage scenarios
- Test feature integration

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_memory_lifecycle():
    # 1. Add memory
    add_result = await add_memory(content="test")
    # 2. Search
    search_result = await search_memories(query="test")
    # 3. Update
    update_result = await update_memory(memory_id=...)
    # 4. Delete
    delete_result = await delete_memory(memory_id=...)
```

**Markers**: `@pytest.mark.e2e`, `@pytest.mark.slow`

---

## Test Fixtures

### Available Fixtures (conftest.py)

**Mock Fixtures**:
- `mock_postgres_pool` - Mock PostgreSQL connection pool
- `mock_qdrant_client` - Mock Qdrant client
- `mock_redis_client` - Mock Redis client
- `mock_neo4j_driver` - Mock Neo4j driver
- `mock_llm_config` - Mock LLM configuration

**Real Database Fixtures** (Integration tests):
- `real_postgres_pool` - Real PostgreSQL connection
- `real_qdrant_client` - Real Qdrant client
- `real_redis_client` - Real Redis client

**Module Instances**:
- `memory_manager` - MemoryManager instance
- `memory_deduplicator` - MemoryDeduplicator instance
- `memory_summarizer` - MemorySummarizer instance
- `performance_analytics` - PerformanceAnalytics instance
- `cross_agent_sharing` - CrossAgentMemorySharing instance
- `realtime_sync` - RealTimeMemorySync instance

**Test Data**:
- `sample_memory` - Sample memory dictionary
- `sample_memories` - List of sample memories
- `sample_embedding` - Sample vector embedding

---

## Writing Tests

### Test Template

```python
"""
Tests for [Module Name]
"""

import pytest
from unittest.mock import AsyncMock, Mock
from src.module_name import ClassName


class TestClassName:
    """Test ClassName functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_method_name(self, fixture_name):
        """Test what this method does"""
        # Arrange
        expected = "expected_value"

        # Act
        result = await fixture_instance.method_name()

        # Assert
        assert result == expected
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Use descriptive test names**: `test_expire_memories_with_delete_policy`
3. **Follow Arrange-Act-Assert pattern**
4. **Clean up resources** in tests
5. **Use appropriate markers** (`@pytest.mark.unit`, etc.)
6. **Mock external dependencies** in unit tests
7. **Test error cases**, not just success cases

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: cognee_test_db
          POSTGRES_USER: cognee_test_user
          POSTGRES_PASSWORD: cognee_test_password
        ports:
          - 25432:5432
      redis:
        image: redis:7
        ports:
          - 26379:6379
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 26333:6333

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-test.txt
      - run: python run_tests.py
```

---

## Troubleshooting

### Tests Fail with "Database not available"

**Solution**: Start databases first:
```bash
docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
```

### Low Coverage

**Solution**:
1. Check coverage report: `htmlcov/index.html`
2. Identify untested code
3. Add tests for uncovered paths

### Import Errors

**Solution**: Ensure project root is in Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Tests Fail

**Solution**: Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

---

## Test Metrics Dashboard

After running tests, view metrics:

```bash
# Coverage report
open htmlcov/index.html

# Pytest stats (if using pytest-html)
open pytest-report.html
```

---

## Performance Benchmarks

Test execution times (approximate):

- **Unit Tests**: ~10 seconds
- **Integration Tests**: ~30 seconds
- **System Tests**: ~5 seconds
- **E2E Tests**: ~60 seconds

**Total**: ~105 seconds (~2 minutes)

---

## Contributing Tests

When adding new features:

1. **Write tests first** (TDD approach)
2. Ensure >98% coverage
3. Add unit tests for new functions
4. Add integration tests for database operations
5. Add E2E test for user workflows
6. Update documentation

---

## Summary

Enhanced Cognee has comprehensive testing across:

- ✅ 6 core modules tested
- ✅ Unit tests for all functions
- ✅ Integration tests with real databases
- ✅ System tests for MCP server
- ✅ E2E tests for workflows
- ✅ Performance analytics
- ✅ Error handling
- ✅ Edge cases

**Target**: >98% coverage, 100% success rate, 0 warnings, 0 skipped tests

---

**Repository**: https://github.com/vincentspereira/Enhanced-Cognee
**Issues**: Report test failures at GitHub Issues
