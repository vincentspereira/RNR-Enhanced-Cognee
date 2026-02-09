# Quick Test Reference Guide

## Test Suite Location

**File:** `tests/unit/test_llm_session_state.py`

## Running the Tests

### Run All Tests in Suite
```bash
# Basic run
pytest tests/unit/test_llm_session_state.py -v

# With detailed output
pytest tests/unit/test_llm_session_state.py -vv

# With coverage report
pytest tests/unit/test_llm_session_state.py --cov=src/llm --cov=src/session_manager --cov=src/document_processor --cov=src/auto_configuration --cov=src/progressive_disclosure --cov=src/structured_memory --cov=src/approval_workflow --cov-report=term-missing
```

### Run Specific Test Classes

```bash
# LLM Provider Tests
pytest tests/unit/test_llm_session_state.py::TestAnthropicClient -v

# Rate Limiter Tests
pytest tests/unit/test_llm_session_state.py::TestRateLimiter -v
pytest tests/unit/test_llm_session_state.py::TestTokenBucket -v

# Token Counter Tests
pytest tests/unit/test_llm_session_state.py::TestTokenCounter -v

# Session Manager Tests
pytest tests/unit/test_llm_session_state.py::TestSessionManager -v
pytest tests/unit/test_llm_session_state.py::TestContextInjector -v

# Document Processor Tests
pytest tests/unit/test_llm_session_state.py::TestDocumentProcessor -v
pytest tests/unit/test_llm_session_state.py::TestDocumentProcessorManager -v

# Auto Configuration Tests
pytest tests/unit/test_llm_session_state.py::TestAutoConfiguration -v

# Progressive Disclosure Tests
pytest tests/unit/test_llm_session_state.py::TestProgressiveDisclosureSearch -v

# Structured Memory Tests
pytest tests/unit/test_llm_session_state.py::TestAutoCategorizer -v
pytest tests/unit/test_llm_session_state.py::TestStructuredMemoryModel -v

# Approval Workflow Tests
pytest tests/unit/test_llm_session_state.py::TestApprovalRequest -v
pytest tests/unit/test_llm_session_state.py::TestApprovalWorkflowManager -v
pytest tests/unit/test_llm_session_state.py::TestCLIApprovalWorkflow -v
pytest tests/unit/test_llm_session_state.py::TestDashboardApprovalWorkflow -v

# Integration Tests
pytest tests/unit/test_llm_session_state.py::TestLLMIntegrationFlow -v
pytest tests/unit/test_llm_session_state.py::TestSessionMemoryIntegration -v
```

### Run Specific Test Methods

```bash
# Test Anthropic client initialization
pytest tests/unit/test_llm_session_state.py::TestAnthropicClient::test_initialization_with_api_key -v

# Test rate lock acquisition
pytest tests/unit/test_llm_session_state.py::TestRateLimiter::test_acquire_rate_lock_success -v

# Test token counting
pytest tests/unit/test_llm_session_state.py::TestTokenCounter::test_count_tokens_anthropic -v

# Test session start/end
pytest tests/unit/test_llm_session_state.py::TestSessionManager::test_start_session -v
pytest tests/unit/test_llm_session_state.py::TestSessionManager::test_end_session -v

# Test document processing
pytest tests/unit/test_llm_session_state.py::TestDocumentProcessor::test_process_file -v

# Test auto-categorization
pytest tests/unit/test_llm_session_state.py::TestAutoCategorizer::test_categorize_bugfix -v

# Test approval workflow
pytest tests/unit/test_llm_session_state.py::TestApprovalWorkflowManager::test_create_request -v
pytest tests/unit/test_llm_session_state.py::TestApprovalWorkflowManager::test_approve_request -v
```

### Run Tests by Pattern

```bash
# All rate limiter tests
pytest tests/unit/test_llm_session_state.py -k "rate" -v

# All session tests
pytest tests/unit/test_llm_session_state.py -k "session" -v

# All token tests
pytest tests/unit/test_llm_session_state.py -k "token" -v

# All approval tests
pytest tests/unit/test_llm_session_state.py -k "approval" -v

# All categorization tests
pytest tests/unit/test_llm_session_state.py -k "categorize" -v
```

## Test Output Formats

### Standard Output
```bash
pytest tests/unit/test_llm_session_state.py -v
```

### Detailed Output
```bash
pytest tests/unit/test_llm_session_state.py -vv -s
```

### Coverage Report (HTML)
```bash
pytest tests/unit/test_llm_session_state.py --cov=src/llm --cov=src/session_manager --cov=src/document_processor --cov=src/auto_configuration --cov=src/progressive_disclosure --cov=src/structured_memory --cov=src/approval_workflow --cov-report=html

# Open report
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux
```

### Coverage Report (Terminal)
```bash
pytest tests/unit/test_llm_session_state.py --cov=src/llm --cov=src/session_manager --cov-report=term-missing
```

### JSON Report
```bash
pytest tests/unit/test_llm_session_state.py --json-report
```

## Running Tests in Different Modes

### Verbose Mode
```bash
pytest tests/unit/test_llm_session_state.py -v
```

### Quiet Mode (summary only)
```bash
pytest tests/unit/test_llm_session_state.py -q
```

### Stop on First Failure
```bash
pytest tests/unit/test_llm_session_state.py -x
```

### Show Local Variables on Failure
```bash
pytest tests/unit/test_llm_session_state.py -l
```

### Run Failed Tests Only
```bash
# First run
pytest tests/unit/test_llm_session_state.py

# Re-run failed tests
pytest tests/unit/test_llm_session_state.py --lf
```

### Run Last Failed Tests First
```bash
pytest tests/unit/test_llm_session_state.py --ff
```

## Test Markers

### Run Only Unit Tests
```bash
pytest tests/unit/test_llm_session_state.py -m unit
```

### Run Only Integration Tests
```bash
pytest tests/unit/test_llm_session_state.py -m integration
```

### Skip Slow Tests
```bash
pytest tests/unit/test_llm_session_state.py -m "not slow"
```

## Parallel Testing

### Install pytest-xdist
```bash
pip install pytest-xdist
```

### Run Tests in Parallel
```bash
# Use all CPUs
pytest tests/unit/test_llm_session_state.py -n auto

# Use 4 processes
pytest tests/unit/test_llm_session_state.py -n 4
```

## Test Profiling

### Install pytest-profiling
```bash
pip install pytest-profiling
```

### Profile Tests
```bash
pytest tests/unit/test_llm_session_state.py --profile
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov pytest-asyncio
      - run: pytest tests/unit/test_llm_session_state.py --cov=src/llm --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Common Issues and Solutions

### Issue: "No module named 'src'"

**Solution:** Run from project root or add to PYTHONPATH
```bash
# From project root
pytest tests/unit/test_llm_session_state.py

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/unit/test_llm_session_state.py
```

### Issue: Async tests not running

**Solution:** Install pytest-asyncio
```bash
pip install pytest-asyncio
```

### Issue: Database connection errors

**Solution:** These tests use mocks, no database needed. If you see DB errors, check that mocks are properly set up.

### Issue: Port already in use

**Solution:** These tests don't use real ports. If you see port errors, check auto-configuration tests.

## Test Statistics

### Count Tests
```bash
pytest tests/unit/test_llm_session_state.py --collect-only
```

### List All Test Names
```bash
pytest tests/unit/test_llm_session_state.py --collect-only -q
```

### Estimate Test Runtime
```bash
# First run to establish baseline
pytest tests/unit/test_llm_session_state.py

# Subsequent runs will show timing
pytest tests/unit/test_llm_session_state.py -d --duration=N
```

## Debugging Tests

### Run with PDB on Failure
```bash
pytest tests/unit/test_llm_session_state.py --pdb
```

### Run with PDB on Error (not just failure)
```bash
pytest tests/unit/test_llm_session_state.py --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

### Drop into PDB at Start of Test
```bash
pytest tests/unit/test_llm_session_state.py --trace
```

### Print Statements
```bash
# Show print output
pytest tests/unit/test_llm_session_state.py -s

# Capture and show output
pytest tests/unit/test_llm_session_state.py -s --capture=no
```

## Best Practices

### 1. Run Tests Before Committing
```bash
pytest tests/unit/test_llm_session_state.py -v
```

### 2. Check Coverage Regularly
```bash
pytest tests/unit/test_llm_session_state.py --cov=src/llm --cov-report=term-missing
```

### 3. Fix Broken Tests Immediately
Don't commit with failing tests. Fix or skip them.

### 4. Add Tests for New Features
Every new feature should have corresponding tests.

### 5. Keep Tests Independent
Tests should not depend on each other. Each test should be runnable in isolation.

### 6. Use Descriptive Test Names
```python
# Good
def test_acquire_rate_lock_success(self):
    pass

# Bad
def test_1(self):
    pass
```

### 7. Follow AAA Pattern
- **Arrange:** Set up test data and mocks
- **Act:** Call the function being tested
- **Assert:** Verify expected results

## Test Organization

### File Structure
```
tests/
├── unit/
│   ├── test_llm_session_state.py       # This test suite
│   ├── test_claude_api_integration.py  # API integration tests
│   └── ...
├── integration/
│   └── ...
└── conftest.py                          # Shared fixtures
```

### Test Class Naming
- `Test<ClassName>` for class tests
- Async test methods use `@pytest.mark.asyncio`
- Test methods use `test_<method_or_feature>` naming

## Summary

This test suite provides comprehensive coverage of LLM Integration and Session/State modules. Run tests regularly to ensure code quality and catch regressions early.

For detailed coverage information, see `tests/TEST_COVERAGE_SUMMARY.md`
