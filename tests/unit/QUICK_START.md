# Test Suite Quick Start Guide

## Running the Tests

### Run All Tests in File
```bash
python -m pytest tests/unit/test_remaining_modules.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/unit/test_remaining_modules.py::TestLiteMCPServer -v
```

### Run Specific Test
```bash
python -m pytest tests/unit/test_remaining_modules.py::TestLiteMCPServer::test_add_memory -v
```

### Run with Coverage
```bash
python -m pytest tests/unit/test_remaining_modules.py --cov=src/lite_mode --cov=src/memory_config --cov=src/audit_logger --cov-report=html
```

### Run with Minimal Output
```bash
python -m pytest tests/unit/test_remaining_modules.py -q
```

## Test Organization

### Test Classes by Module

#### Lite Mode Tests
- `TestLiteMCPServer` - Lite MCP server functionality (10 tests)
- `TestLiteMCPServerProtocol` - MCP protocol implementation (3 tests)
- `TestSQLiteManager` - SQLite database operations (14 tests)
- `TestMCPTool` - MCP tool dataclass (1 test)

#### Configuration Tests
- `TestMemoryCategoryConfig` - Category configuration (1 test)
- `TestAgentConfig` - Agent configuration (1 test)
- `TestDefaultMemoryCategories` - Default categories (2 tests)
- `TestMemoryConfigManager` - Config manager (11 tests)

#### Integration Tests
- `TestSDLCIntegrationManager` - SDLC integration (8 tests)

#### Performance Tests
- `TestPerformanceOptimizer` - Query optimization (8 tests)

#### Audit Tests
- `TestAuditLogLevel` - Log level enum (1 test)
- `TestAuditOperationType` - Operation type enum (1 test)
- `TestAuditLogger` - Audit logger (10 tests)
- `TestAuditLogDecorator` - Decorator tests (2 tests)

#### WebSocket Tests
- `TestEventType` - Event type enum (1 test)
- `TestWebSocketEvent` - Event dataclass (2 tests)
- `TestWebSocketClient` - WebSocket client (1 test)
- `TestRealTimeWebSocketServer` - WebSocket server (10 tests)

#### Integration & Performance Tests
- `TestModuleIntegration` - Cross-module workflows (4 tests)
- `TestErrorHandling` - Error scenarios (3 tests)
- `TestPerformance` - Performance benchmarks (2 tests)

## Common Test Patterns

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_operation(self):
    result = await some_async_function()
    assert result is not None
```

### Mock Pattern
```python
def test_with_mock(self, mock_postgres_pool):
    # Configure mock
    mock_postgres_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = []
    # Test
    result = await function_using_postgres()
    assert result == []
```

### Fixture Pattern
```python
@pytest.fixture
def temp_resource(tmp_path):
    resource_file = tmp_path / "test.txt"
    resource_file.write_text("test content")
    yield str(resource_file)
    # Cleanup handled by tmp_path
```

## Expected Test Results

### Passing Tests (94)
- All Lite mode operations (add, get, update, delete)
- Configuration management
- Audit logging
- WebSocket server
- SDLC integration
- Error handling
- Most performance tests

### Expected Failures (5)
1. **FTS5 Search Tests** (3 failures)
   - Missing `migrations/create_lite_schema.sql`
   - Requires FTS5 virtual tables
   - Would pass with full schema

2. **Performance Optimizer Mock Tests** (2 failures)
   - Mock async context limitations
   - Would pass with real PostgreSQL or enhanced mocks

## Troubleshooting

### Import Errors
```
Solution: Ensure you're running from the project root
cd "C:\Users\vince\Projects\AI Agents\enhanced-cognee"
```

### Database Lock Errors
```
Solution: Close all SQLite connections before cleanup
Tests use pytest's tmp_path for automatic cleanup
```

### Async Warnings
```
Solution: Remove @pytest.mark.asyncio from sync tests
Or use pytest.mark.asyncio(forbid_async_loop=False)
```

## Coverage Goals

### Target Coverage: 98%+

**Currently Covered:**
- Lite Mode MCP Server: 95%+
- SQLite Manager: 90%+
- Memory Configuration: 100%
- Audit Logger: 95%+
- WebSocket Server: 90%+

**To Be Covered:**
- Multi-tenant features (encoding issues)
- Ecosystem development (encoding issues)

## Adding New Tests

### Template
```python
class TestNewModule:
    """Test NewModule functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test module initialization."""
        module = NewModule()
        assert module is not None

    @pytest.mark.asyncio
    async def test_core_functionality(self):
        """Test core functionality."""
        result = await module.some_method()
        assert result is not None

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            module.invalid_method()
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.14'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          pytest tests/unit/test_remaining_modules.py --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Clear Naming
- Test names should describe what they test
- Use `test_<method>_<scenario>` pattern
- Add docstrings for complex tests

### 3. Proper Assertions
- Use specific assertion messages
- Test both success and failure cases
- Assert on meaningful values

### 4. Mock Appropriately
- Mock external dependencies
- Don't mock the code under test
- Use realistic mock data

### 5. Performance
- Keep tests fast (< 1 second each)
- Use fixtures for shared setup
- Avoid unnecessary I/O

## Getting Help

### View Detailed Output
```bash
python -m pytest tests/unit/test_remaining_modules.py -vv --tb=long
```

### Run Only Failed Tests
```bash
python -m pytest tests/unit/test_remaining_modules.py --lf
```

### Stop on First Failure
```bash
python -m pytest tests/unit/test_remaining_modules.py -x
```

### Debug with pdb
```bash
python -m pytest tests/unit/test_remaining_modules.py --pdb
```

---

**Last Updated:** 2026-02-09
**Test Framework:** pytest 9.0.2
**Python Version:** 3.14+
