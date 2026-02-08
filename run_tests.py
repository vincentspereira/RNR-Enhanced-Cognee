#!/usr/bin/env python3
"""
Enhanced Cognee Test Runner
Runs comprehensive test suite with coverage reporting
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and display output"""
    print(f"\n{'=' * 70}")
    print(f"{description}")
    print(f"{'=' * 70}")
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    """Main test runner"""
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Determine Python executable (use virtual environment if available)
    if os.name == 'nt':  # Windows
        venv_python = project_root / '.venv' / 'Scripts' / 'python.exe'
    else:  # Linux/Mac
        venv_python = project_root / '.venv' / 'bin' / 'python'

    python_cmd = str(venv_python) if venv_python.exists() else 'python'

    print("""
======================================================================

           Enhanced Cognee Comprehensive Test Suite

   Coverage Target: >98%   Success Rate: 100%
   Warnings: 0              Skipped: 0

======================================================================
    """)

    # Test results tracking
    results = {}

    # 1. Unit Tests
    print("\n[1/4] Running Unit Tests...")
    returncode = run_command(
        f'"{python_cmd}" -m pytest tests/test_language_detector.py tests/test_multi_language_search.py tests/test_performance_optimizer.py tests/test_advanced_search.py -v --tb=short -m unit',
        "UNIT TESTS"
    )
    results["unit"] = returncode == 0

    # 2. Integration Tests
    print("\n[2/4] Running Integration Tests...")
    returncode = run_command(
        f'"{python_cmd}" -m pytest tests/test_multi_language_integration.py -v --tb=short -m integration',
        "INTEGRATION TESTS"
    )
    results["integration"] = returncode == 0

    # 3. System Tests
    print("\n[3/4] Running System Tests...")
    returncode = run_command(
        f'"{python_cmd}" -m pytest tests/test_system_workflows.py -v --tb=short -m system',
        "SYSTEM TESTS"
    )
    results["system"] = returncode == 0

    # 4. End-to-End Tests
    print("\n[4/4] Running End-to-End Tests...")
    returncode = run_command(
        f'"{python_cmd}" -m pytest tests/test_e2e_scenarios.py -v --tb=short -m e2e',
        "END-TO-END TESTS"
    )
    results["e2e"] = returncode == 0

    # 5. All Tests with Coverage
    print("\n[5/5] Running All Tests with Coverage...")
    returncode = run_command(
        f'"{python_cmd}" -m pytest tests/ -v --tb=short --cov=src --cov-report=term --cov-report=html --cov-fail-under=98',
        "ALL TESTS WITH COVERAGE"
    )
    results["coverage"] = returncode == 0

    # Print Summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    for test_type, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"  {test_type.upper():20} {status}")

    print("-" * 70)
    print(f"  {'TOTAL':20} {passed_tests}/{total_tests} passed")

    if passed_tests == total_tests:
        print("\n[OK] ALL TESTS PASSED!")
        print("\nCoverage Reports:")
        print("  - HTML: htmlcov/index.html")
        print("  - Terminal: See above")
        return 0
    else:
        print(f"\n[FAIL] {total_tests - passed_tests} TEST SUITE(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
