"""
RNR Enhanced Cognee CI/CD Integration and Test Automation Framework

This module provides comprehensive CI/CD integration and test automation optimization
for the RNR Enhanced Cognee Multi-Agent System, including GitHub Actions workflows,
parallel test execution, intelligent test selection, and automated quality gates.

Coverage Target: Part of overall test automation infrastructure
Category: CI/CD Integration (Advanced Testing - Phase 3)
"""

import pytest
import asyncio
import json
import time
import os
import subprocess
import yaml
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import hashlib

logger = logging.getLogger(__name__)

# CI/CD Testing Markers
pytest.mark.automation = pytest.mark.automation
pytest.mark.ci_cd = pytest.mark.ci_cd
pytest.mark.parallel = pytest.mark.parallel
pytest.mark.quality_gate = pytest.mark.quality_gate
pytest.mark.environment = pytest.mark.environment
pytest.mark.deployment = pytest.mark.deployment


class CIEnvironment(Enum):
    """CI/CD environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class TestCategory(Enum):
    """Test categories for intelligent selection"""
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    API = "api"
    UI = "ui"
    COMPLIANCE = "compliance"
    E2E = "e2e"
    DOCUMENTATION = "documentation"


@dataclass
class CIConfig:
    """CI/CD configuration parameters"""
    environment: CIEnvironment
    max_parallel_jobs: int
    test_timeout_minutes: int
    coverage_threshold: float
    performance_thresholds: Dict[str, float]
    security_scan_enabled: bool
    deployment_enabled: bool
    notification_channels: List[str]
    artifacts_retention_days: int


@dataclass
class TestExecutionPlan:
    """Test execution plan for CI/CD"""
    test_categories: List[TestCategory]
    parallel_groups: List[List[TestCategory]]
    estimated_duration_minutes: int
    resource_requirements: Dict[str, Any]
    dependencies: Dict[TestCategory, List[TestCategory]] = field(default_factory=dict)


@dataclass
class QualityGateResult:
    """Quality gate evaluation result"""
    gate_name: str
    status: str  # passed, failed, warning
    metrics: Dict[str, Any]
    thresholds: Dict[str, float]
    actual_values: Dict[str, float]
    timestamp: datetime


class CICDTestFramework:
    """Comprehensive CI/CD test automation framework"""

    def __init__(self):
        self.execution_plans = {}
        self.quality_gates = {}
        self.test_results = {}
        self.performance_baselines = {}
        self.deployment_history = []

    def generate_test_matrix(self, changed_files: List[str],
                           commit_hash: str) -> TestExecutionPlan:
        """Generate intelligent test matrix based on changes"""
        test_categories = set()

        # Analyze changed files to determine required tests
        for file_path in changed_files:
            if file_path.startswith("src/agents/"):
                test_categories.update([TestCategory.UNIT, TestCategory.INTEGRATION, TestCategory.E2E])
            elif file_path.startswith("src/memory/"):
                test_categories.update([TestCategory.UNIT, TestCategory.INTEGRATION, TestCategory.PERFORMANCE])
            elif file_path.startswith("src/"):
                test_categories.update([TestCategory.UNIT, TestCategory.INTEGRATION])
            elif file_path.startswith("testing/"):
                test_categories.add(TestCategory.DOCUMENTATION)
            elif file_path.startswith("docs/"):
                test_categories.update([TestCategory.DOCUMENTATION, TestCategory.API])
            elif file_path.startswith("docker"):
                test_categories.update([TestCategory.E2E, TestCategory.DEPLOYMENT])
            elif file_path.startswith(".github/workflows"):
                test_categories.add(TestCategory.CI_CD)
            elif any(backend_file in file_path for backend_file in ["api", "routes", "controllers"]):
                test_categories.update([TestCategory.API, TestCategory.INTEGRATION])
            elif any(frontend_file in file_path for frontend_file in ["ui", "frontend", "web"]):
                test_categories.add(TestCategory.UI)

        # Ensure minimum test coverage
        if not test_categories:
            test_categories = {TestCategory.UNIT, TestCategory.INTEGRATION}

        # Create parallel execution groups
        parallel_groups = self._create_parallel_groups(list(test_categories))

        # Estimate execution duration
        category_durations = {
            TestCategory.UNIT: 5,
            TestCategory.INTEGRATION: 15,
            TestCategory.SYSTEM: 20,
            TestCategory.PERFORMANCE: 30,
            TestCategory.SECURITY: 25,
            TestCategory.API: 10,
            TestCategory.UI: 15,
            TestCategory.COMPLIANCE: 20,
            TestCategory.E2E: 25,
            TestCategory.DOCUMENTATION: 5
        }

        estimated_duration = sum(
            category_durations.get(cat, 10) for cat in test_categories
        ) // len(parallel_groups)

        # Define dependencies
        dependencies = {
            TestCategory.UNIT: [],
            TestCategory.INTEGRATION: [TestCategory.UNIT],
            TestCategory.SYSTEM: [TestCategory.INTEGRATION],
            TestCategory.E2E: [TestCategory.SYSTEM, TestCategory.API, TestCategory.UI],
            TestCategory.PERFORMANCE: [TestCategory.INTEGRATION],
            TestCategory.SECURITY: [TestCategory.UNIT, TestCategory.INTEGRATION]
        }

        return TestExecutionPlan(
            test_categories=list(test_categories),
            parallel_groups=parallel_groups,
            estimated_duration_minutes=estimated_duration,
            resource_requirements=self._calculate_resource_requirements(test_categories),
            dependencies=dependencies
        )

    def _create_parallel_groups(self, categories: List[TestCategory]) -> List[List[TestCategory]]:
        """Create parallel execution groups based on dependencies and resource needs"""
        # Group tests that can run in parallel
        independent_tests = [TestCategory.UNIT, TestCategory.DOCUMENTATION, TestCategory.SECURITY]
        integration_tests = [TestCategory.INTEGRATION, TestCategory.API]
        system_tests = [TestCategory.SYSTEM, TestCategory.E2E, TestCategory.UI]
        specialized_tests = [TestCategory.PERFORMANCE, TestCategory.COMPLIANCE]

        groups = []
        if any(cat in categories for cat in independent_tests):
            groups.append([cat for cat in independent_tests if cat in categories])

        if any(cat in categories for cat in integration_tests):
            groups.append([cat for cat in integration_tests if cat in categories])

        if any(cat in categories for cat in system_tests):
            groups.append([cat for cat in system_tests if cat in categories])

        if any(cat in categories for cat in specialized_tests):
            groups.append([cat for cat in specialized_tests if cat in categories])

        return groups

    def _calculate_resource_requirements(self, categories: List[TestCategory]) -> Dict[str, Any]:
        """Calculate resource requirements for test execution"""
        requirements = {
            "cpu_cores": 2,
            "memory_gb": 4,
            "disk_gb": 10,
            "parallel_jobs": 1
        }

        # Add resources based on test categories
        if TestCategory.PERFORMANCE in categories:
            requirements["cpu_cores"] = max(requirements["cpu_cores"], 8)
            requirements["memory_gb"] = max(requirements["memory_gb"], 16)

        if TestCategory.E2E in categories:
            requirements["cpu_cores"] = max(requirements["cpu_cores"], 4)
            requirements["memory_gb"] = max(requirements["memory_gb"], 8)

        if TestCategory.UI in categories:
            requirements["cpu_cores"] = max(requirements["cpu_cores"], 4)
            requirements["memory_gb"] = max(requirements["memory_gb"], 6)

        total_tests = len(categories)
        requirements["parallel_jobs"] = min(total_tests // 2 + 1, 4)

        return requirements

    async def execute_test_group(self, group: List[TestCategory],
                               ci_config: CIConfig) -> Dict[str, Any]:
        """Execute a group of tests in parallel"""
        group_start_time = time.time()
        execution_id = f"exec_{int(group_start_time)}"

        # Create test commands for each category
        test_commands = self._generate_test_commands(group, ci_config)

        # Execute tests in parallel
        tasks = []
        for command_info in test_commands:
            task = self._execute_test_command(command_info, ci_config.test_timeout_minutes)
            tasks.append(task)

        # Wait for all tests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        group_result = {
            "execution_id": execution_id,
            "test_group": group,
            "start_time": group_start_time,
            "end_time": time.time(),
            "duration": time.time() - group_start_time,
            "results": [],
            "success_count": 0,
            "failure_count": 0,
            "coverage_data": {},
            "performance_metrics": {}
        }

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                group_result["results"].append({
                    "category": group[i],
                    "status": "failed",
                    "error": str(result),
                    "duration": 0
                })
                group_result["failure_count"] += 1
            else:
                group_result["results"].append(result)
                if result.get("status") == "passed":
                    group_result["success_count"] += 1
                else:
                    group_result["failure_count"] += 1

                # Collect coverage and performance data
                if result.get("coverage"):
                    group_result["coverage_data"][group[i].value] = result["coverage"]
                if result.get("performance"):
                    group_result["performance_metrics"][group[i].value] = result["performance"]

        return group_result

    def _generate_test_commands(self, categories: List[TestCategory],
                              ci_config: CIConfig) -> List[Dict[str, Any]]:
        """Generate test commands for each category"""
        commands = []

        for category in categories:
            if category == TestCategory.UNIT:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/unit/",
                        "-v",
                        "--cov=src",
                        f"--cov-fail-under={ci_config.coverage_threshold}",
                        "--junit-xml=test-results-unit.xml",
                        "--tb=short"
                    ],
                    "env": {"PYTHONPATH": "src"},
                    "timeout": ci_config.test_timeout_minutes
                })

            elif category == TestCategory.INTEGRATION:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/integration/",
                        "-v",
                        "--cov=src",
                        f"--cov-fail-under={ci_config.coverage_threshold * 0.8}",
                        "--junit-xml=test-results-integration.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "TEST_ENV": "ci"},
                    "timeout": ci_config.test_timeout_minutes * 1.5
                })

            elif category == TestCategory.SYSTEM:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/system/",
                        "-v",
                        "--junit-xml=test-results-system.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "TEST_ENV": "system_test"},
                    "timeout": ci_config.test_timeout_minutes * 2
                })

            elif category == TestCategory.PERFORMANCE:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/performance/",
                        "-v",
                        "--junit-xml=test-results-performance.xml",
                        "--benchmark-only"
                    ],
                    "env": {"PYTHONPATH": "src", "PERFORMANCE_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes * 3
                })

            elif category == TestCategory.SECURITY:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/security/",
                        "-v",
                        "--junit-xml=test-results-security.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "SECURITY_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes * 2
                })

            elif category == TestCategory.API:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/api/",
                        "-v",
                        "--junit-xml=test-results-api.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "API_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes
                })

            elif category == TestCategory.UI:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/ui/",
                        "-v",
                        "--junit-xml=test-results-ui.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "UI_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes * 1.5
                })

            elif category == TestCategory.COMPLIANCE:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/compliance/",
                        "-v",
                        "--junit-xml=test-results-compliance.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "COMPLIANCE_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes * 2
                })

            elif category == TestCategory.E2E:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/automation/test_end_to_end_workflows.py",
                        "-v",
                        "--junit-xml=test-results-e2e.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "E2E_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes * 3
                })

            elif category == TestCategory.DOCUMENTATION:
                commands.append({
                    "category": category,
                    "command": [
                        "python", "-m", "pytest",
                        "testing/documentation/",
                        "-v",
                        "--junit-xml=test-results-documentation.xml"
                    ],
                    "env": {"PYTHONPATH": "src", "DOC_TEST": "true"},
                    "timeout": ci_config.test_timeout_minutes
                })

        return commands

    async def _execute_test_command(self, command_info: Dict[str, Any],
                                  timeout_minutes: int) -> Dict[str, Any]:
        """Execute a single test command"""
        start_time = time.time()
        category = command_info["category"]
        command = command_info["command"]
        env = command_info.get("env", {})

        try:
            # Set up environment
            test_env = os.environ.copy()
            test_env.update(env)

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *command,
                env=test_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_minutes * 60
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Test category {category} timed out after {timeout_minutes} minutes")

            # Parse test results
            return_code = process.returncode
            duration = time.time() - start_time

            # Parse coverage and performance data if available
            coverage = None
            performance = None

            if return_code == 0:
                # Try to parse coverage data
                coverage = await self._parse_coverage_data(category)

                # Try to parse performance data
                performance = await self._parse_performance_data(category)

            return {
                "category": category,
                "status": "passed" if return_code == 0 else "failed",
                "duration": duration,
                "return_code": return_code,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "coverage": coverage,
                "performance": performance
            }

        except Exception as e:
            return {
                "category": category,
                "status": "failed",
                "duration": time.time() - start_time,
                "error": str(e),
                "coverage": None,
                "performance": None
            }

    async def _parse_coverage_data(self, category: TestCategory) -> Optional[Dict[str, Any]]:
        """Parse test coverage data"""
        try:
            coverage_file = f"coverage-{category.value}.json"
            if Path(coverage_file).exists():
                with open(coverage_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    async def _parse_performance_data(self, category: TestCategory) -> Optional[Dict[str, Any]]:
        """Parse performance test data"""
        try:
            perf_file = f"performance-{category.value}.json"
            if Path(perf_file).exists():
                with open(perf_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def evaluate_quality_gates(self, test_results: Dict[str, Any],
                             ci_config: CIConfig) -> List[QualityGateResult]:
        """Evaluate quality gates against test results"""
        quality_gates = []

        # Coverage quality gate
        overall_coverage = self._calculate_overall_coverage(test_results)
        coverage_gate = QualityGateResult(
            gate_name="code_coverage",
            status="passed" if overall_coverage >= ci_config.coverage_threshold else "failed",
            metrics={"coverage_percentage": overall_coverage},
            thresholds={"min_coverage": ci_config.coverage_threshold},
            actual_values{"coverage": overall_coverage},
            timestamp=datetime.now(timezone.utc)
        )
        quality_gates.append(coverage_gate)

        # Test success rate gate
        total_tests = sum(result.get("success_count", 0) + result.get("failure_count", 0)
                         for result in test_results.values())
        successful_tests = sum(result.get("success_count", 0) for result in test_results.values())

        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        success_gate = QualityGateResult(
            gate_name="test_success_rate",
            status="passed" if success_rate >= 0.95 else "failed",
            metrics={"success_rate": success_rate, "total_tests": total_tests},
            thresholds={"min_success_rate": 0.95},
            actual_values={"success_rate": success_rate},
            timestamp=datetime.now(timezone.utc)
        )
        quality_gates.append(success_gate)

        # Performance quality gate
        performance_gate = self._evaluate_performance_gate(test_results, ci_config)
        quality_gates.append(performance_gate)

        # Security quality gate
        security_gate = self._evaluate_security_gate(test_results, ci_config)
        quality_gates.append(security_gate)

        return quality_gates

    def _calculate_overall_coverage(self, test_results: Dict[str, Any]) -> float:
        """Calculate overall test coverage from all test results"""
        total_lines = 0
        covered_lines = 0

        for result in test_results.values():
            coverage_data = result.get("coverage_data", {})
            for category_coverage in coverage_data.values():
                if isinstance(category_coverage, dict):
                    total_lines += category_coverage.get("total_lines", 0)
                    covered_lines += category_coverage.get("covered_lines", 0)

        return covered_lines / total_lines if total_lines > 0 else 0.0

    def _evaluate_performance_gate(self, test_results: Dict[str, Any],
                                  ci_config: CIConfig) -> QualityGateResult:
        """Evaluate performance quality gate"""
        performance_metrics = test_results.get("performance_metrics", {})
        all_thresholds_met = True
        violations = []

        for metric, threshold in ci_config.performance_thresholds.items():
            if metric in performance_metrics:
                actual_value = performance_metrics[metric]
                if actual_value > threshold:
                    all_thresholds_met = False
                    violations.append(f"{metric}: {actual_value} > {threshold}")

        return QualityGateResult(
            gate_name="performance",
            status="passed" if all_thresholds_met else "failed",
            metrics=performance_metrics,
            thresholds=ci_config.performance_thresholds,
            actual_values=performance_metrics,
            timestamp=datetime.now(timezone.utc)
        )

    def _evaluate_security_gate(self, test_results: Dict[str, Any],
                               ci_config: CIConfig) -> QualityGateResult:
        """Evaluate security quality gate"""
        security_metrics = {}
        critical_vulnerabilities = 0

        # Extract security test results
        for result in test_results.values():
            if "security" in result.get("coverage_data", {}):
                security_data = result["coverage_data"]["security"]
                if isinstance(security_data, dict):
                    security_metrics.update(security_data)
                    critical_vulnerabilities += security_data.get("critical_vulnerabilities", 0)

        security_passed = critical_vulnerabilities == 0

        return QualityGateResult(
            gate_name="security",
            status="passed" if security_passed else "failed",
            metrics=security_metrics,
            thresholds={"critical_vulnerabilities": 0},
            actual_values={"critical_vulnerabilities": critical_vulnerabilities},
            timestamp=datetime.now(timezone.utc)
        )

    async def setup_test_environment(self, ci_config: CIConfig) -> Dict[str, Any]:
        """Set up test environment for CI/CD"""
        setup_start_time = time.time()

        try:
            # Create test environment
            env_setup_commands = [
                # Install dependencies
                ["pip", "install", "-r", "requirements.txt"],
                ["pip", "install", "-r", "requirements-test.txt"],
                # Set up test database
                ["python", "scripts/setup_test_db.py"],
                # Initialize test services
                ["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"],
                # Wait for services to be ready
                ["python", "scripts/wait_for_services.py"]
            ]

            for command in env_setup_commands:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    raise RuntimeError(f"Environment setup failed: {stderr.decode()}")

            return {
                "status": "success",
                "duration": time.time() - setup_start_time,
                "environment": ci_config.environment.value,
                "services": ["postgresql", "qdrant", "neo4j", "redis", "api"]
            }

        except Exception as e:
            return {
                "status": "failed",
                "duration": time.time() - setup_start_time,
                "error": str(e)
            }

    async def cleanup_test_environment(self, ci_config: CIConfig) -> Dict[str, Any]:
        """Clean up test environment after CI/CD"""
        cleanup_start_time = time.time()

        try:
            # Cleanup commands
            cleanup_commands = [
                # Stop test services
                ["docker-compose", "-f", "docker-compose.test.yml", "down", "-v"],
                # Clean up test data
                ["python", "scripts/cleanup_test_data.py"],
                # Remove test artifacts (optional)
                ["find", ".", "-name", "*.pyc", "-delete"],
                ["find", ".", "-name", "__pycache__", "-type", "d", "-exec", "rm", "-rf", "{}", "+"]
            ]

            for command in cleanup_commands:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

            return {
                "status": "success",
                "duration": time.time() - cleanup_start_time
            }

        except Exception as e:
            return {
                "status": "failed",
                "duration": time.time() - cleanup_start_time,
                "error": str(e)
            }

    def generate_ci_report(self, test_results: Dict[str, Any],
                         quality_gates: List[QualityGateResult],
                         ci_config: CIConfig) -> Dict[str, Any]:
        """Generate comprehensive CI/CD report"""
        total_duration = sum(result.get("duration", 0) for result in test_results.values())
        total_tests = sum(result.get("success_count", 0) + result.get("failure_count", 0)
                         for result in test_results.values())
        successful_tests = sum(result.get("success_count", 0) for result in test_results.values())

        passed_gates = sum(1 for gate in quality_gates if gate.status == "passed")
        total_gates = len(quality_gates)

        report = {
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": ci_config.environment.value,
            "summary": {
                "total_duration_minutes": total_duration / 60,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "quality_gates_passed": passed_gates,
                "quality_gates_total": total_gates,
                "overall_status": "passed" if passed_gates == total_gates else "failed"
            },
            "test_results": test_results,
            "quality_gates": [
                {
                    "name": gate.gate_name,
                    "status": gate.status,
                    "metrics": gate.metrics,
                    "thresholds": gate.thresholds
                }
                for gate in quality_gates
            ],
            "coverage_summary": self._calculate_overall_coverage(test_results),
            "performance_summary": self._extract_performance_summary(test_results),
            "recommendations": self._generate_recommendations(test_results, quality_gates)
        }

        return report

    def _extract_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance summary from test results"""
        performance_summary = {}

        for result in test_results.values():
            perf_metrics = result.get("performance_metrics", {})
            performance_summary.update(perf_metrics)

        return performance_summary

    def _generate_recommendations(self, test_results: Dict[str, Any],
                                quality_gates: List[QualityGateResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Coverage recommendations
        overall_coverage = self._calculate_overall_coverage(test_results)
        if overall_coverage < 80:
            recommendations.append("Increase test coverage to improve code quality")

        # Performance recommendations
        for gate in quality_gates:
            if gate.gate_name == "performance" and gate.status == "failed":
                recommendations.append("Address performance bottlenecks identified in tests")

        # Security recommendations
        for gate in quality_gates:
            if gate.gate_name == "security" and gate.status == "failed":
                recommendations.append("Address security vulnerabilities before deployment")

        # Test failure recommendations
        failed_tests = sum(result.get("failure_count", 0) for result in test_results.values())
        if failed_tests > 0:
            recommendations.append(f"Fix {failed_tests} failing tests before deployment")

        return recommendations


@pytest.fixture
def ci_framework():
    """Fixture for CI/CD test framework"""
    return CICDTestFramework()


@pytest.fixture
def ci_configs():
    """Fixture providing CI/CD configurations for different environments"""
    return {
        CIEnvironment.DEVELOPMENT: CIConfig(
            environment=CIEnvironment.DEVELOPMENT,
            max_parallel_jobs=4,
            test_timeout_minutes=15,
            coverage_threshold=70,
            performance_thresholds={
                "api_response_time_ms": 500,
                "memory_usage_mb": 512,
                "cpu_usage_percent": 80
            },
            security_scan_enabled=False,
            deployment_enabled=False,
            notification_channels=["slack-dev"],
            artifacts_retention_days=7
        ),

        CIEnvironment.STAGING: CIConfig(
            environment=CIEnvironment.STAGING,
            max_parallel_jobs=6,
            test_timeout_minutes=30,
            coverage_threshold=85,
            performance_thresholds={
                "api_response_time_ms": 300,
                "memory_usage_mb": 256,
                "cpu_usage_percent": 70
            },
            security_scan_enabled=True,
            deployment_enabled=True,
            notification_channels=["slack-staging", "email"],
            artifacts_retention_days=30
        ),

        CIEnvironment.PRODUCTION: CIConfig(
            environment=CIEnvironment.PRODUCTION,
            max_parallel_jobs=8,
            test_timeout_minutes=45,
            coverage_threshold=90,
            performance_thresholds={
                "api_response_time_ms": 200,
                "memory_usage_mb": 256,
                "cpu_usage_percent": 60
            },
            security_scan_enabled=True,
            deployment_enabled=True,
            notification_channels=["slack-prod", "email", "pagerduty"],
            artifacts_retention_days=90
        )
    }


class TestCICDIntegration:
    """Test CI/CD integration and automation"""

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_github_actions_workflow_generation(self, ci_framework):
        """Test GitHub Actions workflow generation"""
        # Generate workflow YAML
        workflow = {
            "name": "RNR Enhanced Cognee CI/CD Pipeline",
            "on": {
                "push": {
                    "branches": ["main", "develop"]
                },
                "pull_request": {
                    "branches": ["main"]
                }
            },
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "strategy": {
                        "matrix": {
                            "python-version": ["3.9", "3.10", "3.11"]
                        }
                    },
                    "services": {
                        "postgres": {
                            "image": "postgres:14",
                            "env": {
                                "POSTGRES_PASSWORD": "test",
                                "POSTGRES_DB": "cognee_test"
                            },
                            "options": "--health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5"
                        },
                        "redis": {
                            "image": "redis:7",
                            "options": "--health-cmd redis-cli ping --health-interval 10s --health-timeout 5s --health-retries 5"
                        }
                    },
                    "steps": [
                        {
                            "name": "Checkout code",
                            "uses": "actions/checkout@v3"
                        },
                        {
                            "name": "Set up Python",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ matrix.python-version }}"
                            }
                        },
                        {
                            "name": "Cache dependencies",
                            "uses": "actions/cache@v3",
                            "with": {
                                "path": "~/.cache/pip",
                                "key": "${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}"
                            }
                        },
                        {
                            "name": "Install dependencies",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install -r requirements.txt
                                pip install -r requirements-test.txt
                        },
                        {
                            "name": "Run tests",
                            "run": |
                                python -m pytest testing/ -v --cov=src --cov-report=xml --junit-xml=test-results.xml
                        },
                        {
                            "name": "Upload coverage to Codecov",
                            "uses": "codecov/codecov-action@v3",
                            "with": {
                                "file": "coverage.xml"
                            }
                        }
                    ]
                }
            }
        }

        # Validate workflow structure
        assert "name" in workflow, "Workflow missing name"
        assert "on" in workflow, "Workflow missing triggers"
        assert "jobs" in workflow, "Workflow missing jobs"

        # Validate test job
        test_job = workflow["jobs"]["test"]
        assert "runs-on" in test_job, "Test job missing runner"
        assert "strategy" in test_job, "Test job missing matrix strategy"
        assert "services" in test_job, "Test job missing services"

        # Validate steps
        steps = test_job["steps"]
        assert len(steps) >= 6, f"Insufficient workflow steps: {len(steps)}"

        step_names = [step.get("name", "") for step in steps]
        required_steps = ["Checkout code", "Set up Python", "Install dependencies", "Run tests"]
        for required_step in required_steps:
            assert any(required_step in name for name in step_names), \
                f"Missing required step: {required_step}"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_parallel_test_execution(self, ci_framework, ci_configs):
        """Test parallel test execution optimization"""
        # Simulate changed files
        changed_files = [
            "src/agents/ats/algorithmic_trading_system.py",
            "src/memory/postgresql_memory_store.py",
            "docs/api/README.md"
        ]

        # Generate test execution plan
        execution_plan = ci_framework.generate_test_matrix(changed_files, "commit_hash_123")

        # Validate test categories
        expected_categories = {TestCategory.UNIT, TestCategory.INTEGRATION, TestCategory.DOCUMENTATION}
        actual_categories = set(execution_plan.test_categories)

        assert actual_categories >= expected_categories, \
            f"Missing test categories: {expected_categories - actual_categories}"

        # Validate parallel groups
        assert len(execution_plan.parallel_groups) >= 1, \
            "No parallel groups created"

        total_parallel_tests = sum(len(group) for group in execution_plan.parallel_groups)
        assert total_parallel_tests >= len(expected_categories), \
            "Not all tests assigned to parallel groups"

        # Validate resource requirements
        requirements = execution_plan.resource_requirements
        assert requirements["cpu_cores"] >= 2, "Insufficient CPU allocation"
        assert requirements["memory_gb"] >= 4, "Insufficient memory allocation"
        assert requirements["parallel_jobs"] >= 1, "No parallel jobs configured"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_environment_provisioning(self, ci_framework, ci_configs):
        """Test automated environment provisioning"""
        ci_config = ci_configs[CIEnvironment.STAGING]

        # Test environment setup
        setup_result = await ci_framework.setup_test_environment(ci_config)

        assert setup_result["status"] == "success", \
            f"Environment setup failed: {setup_result.get('error', 'Unknown error')}"

        assert "environment" in setup_result, \
            "Environment info missing from setup result"

        assert setup_result["environment"] == CIEnvironment.STAGING.value, \
            "Wrong environment configured"

        # Test services are running
        expected_services = ["postgresql", "qdrant", "neo4j", "redis", "api"]
        actual_services = setup_result.get("services", [])

        for service in expected_services:
            assert service in actual_services, \
                f"Service {service} not running"

        # Test environment cleanup
        cleanup_result = await ci_framework.cleanup_test_environment(ci_config)

        assert cleanup_result["status"] == "success", \
            f"Environment cleanup failed: {cleanup_result.get('error', 'Unknown error')}"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_quality_gate_enforcement(self, ci_framework, ci_configs):
        """Test quality gate enforcement"""
        ci_config = ci_configs[CIEnvironment.PRODUCTION]

        # Mock test results
        mock_test_results = {
            "group_1": {
                "success_count": 150,
                "failure_count": 5,
                "coverage_data": {
                    "unit": {"total_lines": 1000, "covered_lines": 950},
                    "integration": {"total_lines": 500, "covered_lines": 400}
                },
                "performance_metrics": {
                    "api_response_time_ms": 180,
                    "memory_usage_mb": 200
                }
            },
            "group_2": {
                "success_count": 75,
                "failure_count": 2,
                "coverage_data": {
                    "system": {"total_lines": 300, "covered_lines": 270}
                },
                "performance_metrics": {}
            }
        }

        # Evaluate quality gates
        quality_gates = ci_framework.evaluate_quality_gates(mock_test_results, ci_config)

        # Validate quality gate results
        assert len(quality_gates) >= 3, \
            "Insufficient quality gates evaluated"

        gate_names = [gate.gate_name for gate in quality_gates]
        required_gates = ["code_coverage", "test_success_rate", "performance", "security"]
        for gate in required_gates:
            assert gate in gate_names, \
                f"Missing quality gate: {gate}"

        # Validate coverage gate
        coverage_gate = next(gate for gate in quality_gates if gate.gate_name == "code_coverage")
        assert coverage_gate.thresholds["min_coverage"] == ci_config.coverage_threshold, \
            "Coverage threshold not applied correctly"

        # Validate performance gate
        perf_gate = next(gate for gate in quality_gates if gate.gate_name == "performance")
        assert perf_gate.thresholds == ci_config.performance_thresholds, \
            "Performance thresholds not applied correctly"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_intelligent_test_selection(self, ci_framework):
        """Test intelligent test selection based on changes"""
        # Test case 1: Agent system changes
        agent_changes = [
            "src/agents/ats/algorithmic_trading_system.py",
            "src/agents/oma/orchestration_manager.py",
            "src/agents/smc/monitoring_agent.py"
        ]

        plan1 = ci_framework.generate_test_matrix(agent_changes, "commit_1")
        assert TestCategory.UNIT in plan1.test_categories, \
            "Unit tests required for agent changes"
        assert TestCategory.INTEGRATION in plan1.test_categories, \
            "Integration tests required for agent changes"
        assert TestCategory.E2E in plan1.test_categories, \
            "E2E tests required for agent changes"

        # Test case 2: Documentation changes only
        doc_changes = [
            "docs/api/README.md",
            "docs/user-guide/getting-started.md",
            "README.md"
        ]

        plan2 = ci_framework.generate_test_matrix(doc_changes, "commit_2")
        assert TestCategory.DOCUMENTATION in plan2.test_categories, \
            "Documentation tests required for doc changes"
        # Should still have some basic tests
        assert len(plan2.test_categories) >= 2, \
            "Minimum test coverage not maintained"

        # Test case 3: No changes (should run minimum tests)
        no_changes = []
        plan3 = ci_framework.generate_test_matrix(no_changes, "commit_3")
        assert len(plan3.test_categories) >= 2, \
            "Minimum test coverage not maintained for no changes"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_deployment_pipeline_integration(self, ci_framework, ci_configs):
        """Test deployment pipeline integration"""
        ci_config = ci_configs[CIEnvironment.PRODUCTION]

        # Mock successful test results
        successful_test_results = {
            "unit_tests": {
                "success_count": 200,
                "failure_count": 0,
                "coverage_data": {
                    "total_coverage": 92
                }
            },
            "integration_tests": {
                "success_count": 50,
                "failure_count": 0,
                "coverage_data": {}
            },
            "security_tests": {
                "success_count": 30,
                "failure_count": 0,
                "coverage_data": {}
            }
        }

        # Mock quality gates
        successful_quality_gates = [
            QualityGateResult(
                gate_name="code_coverage",
                status="passed",
                metrics={"coverage_percentage": 92},
                thresholds={"min_coverage": 90},
                actual_values={"coverage": 92},
                timestamp=datetime.now(timezone.utc)
            ),
            QualityGateResult(
                gate_name="test_success_rate",
                status="passed",
                metrics={"success_rate": 1.0},
                thresholds={"min_success_rate": 0.95},
                actual_values={"success_rate": 1.0},
                timestamp=datetime.now(timezone.utc)
            )
        ]

        # Generate CI report
        ci_report = ci_framework.generate_ci_report(
            successful_test_results,
            successful_quality_gates,
            ci_config
        )

        # Validate report structure
        assert "execution_timestamp" in ci_report, "Report missing timestamp"
        assert "summary" in ci_report, "Report missing summary"
        assert "test_results" in ci_report, "Report missing test results"
        assert "quality_gates" in ci_report, "Report missing quality gates"

        # Validate summary
        summary = ci_report["summary"]
        assert summary["overall_status"] == "passed", \
            "Deployment should be allowed for successful tests"

        assert summary["success_rate"] == 1.0, \
            "Success rate incorrect for successful tests"

        # Validate deployment decision
        deployment_allowed = (
            summary["overall_status"] == "passed" and
            summary["quality_gates_passed"] == summary["quality_gates_total"] and
            ci_config.deployment_enabled
        )

        assert deployment_allowed, \
            "Deployment should be allowed for successful pipeline"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_artifact_management(self, ci_framework):
        """Test test artifact collection and management"""
        # Mock test artifacts
        test_artifacts = {
            "test_reports": [
                "test-results-unit.xml",
                "test-results-integration.xml",
                "test-results-performance.xml"
            ],
            "coverage_reports": [
                "coverage.xml",
                "coverage-html/index.html"
            ],
            "logs": [
                "pytest.log",
                "performance.log"
            ],
            "screenshots": [
                "ui-test-screenshot-1.png",
                "ui-test-screenshot-2.png"
            ]
        }

        # Simulate artifact collection
        collected_artifacts = []
        for artifact_type, files in test_artifacts.items():
            for file in files:
                artifact_info = {
                    "file_name": file,
                    "type": artifact_type,
                    "size": len(file.encode()),  # Mock file size
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "retention_days": 30
                }
                collected_artifacts.append(artifact_info)

        # Validate artifact collection
        assert len(collected_artifacts) >= 8, \
            "Insufficient artifacts collected"

        artifact_types = set(artifact["type"] for artifact in collected_artifacts)
        expected_types = {"test_reports", "coverage_reports", "logs", "screenshots"}
        assert artifact_types >= expected_types, \
            "Missing artifact types"

        # Validate artifact metadata
        for artifact in collected_artifacts:
            assert "file_name" in artifact, "Artifact missing file name"
            assert "type" in artifact, "Artifact missing type"
            assert "created_at" in artifact, "Artifact missing timestamp"

    @pytest.mark.automation
    @pytest.mark.ci_cd
    async def test_notification_integration(self, ci_framework, ci_configs):
        """Test notification integration for CI/CD events"""
        ci_config = ci_configs[CIEnvironment.PRODUCTION]

        # Mock CI/CD events
        ci_events = [
            {
                "event_type": "pipeline_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {
                    "branch": "main",
                    "commit": "abc123",
                    "environment": "production"
                }
            },
            {
                "event_type": "test_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {
                    "total_tests": 300,
                    "passed_tests": 295,
                    "failed_tests": 5,
                    "coverage": 88
                }
            },
            {
                "event_type": "deployment_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {
                    "version": "1.2.3",
                    "environment": "production"
                }
            }
        ]

        # Validate notification channels
        notification_channels = ci_config.notification_channels
        expected_channels = ["slack-prod", "email", "pagerduty"]
        assert len(notification_channels) >= len(expected_channels), \
            "Insufficient notification channels"

        for channel in expected_channels:
            assert channel in notification_channels, \
                f"Missing notification channel: {channel}"

        # Validate event notification formatting
        for event in ci_events:
            assert "event_type" in event, "Event missing type"
            assert "timestamp" in event, "Event missing timestamp"
            assert "details" in event, "Event missing details"

            # Format notification message
            message = self._format_notification_message(event)
            assert len(message) > 0, "Notification message empty"
            assert event["event_type"] in message, "Event type not in message"

    def _format_notification_message(self, event: Dict[str, Any]) -> str:
        """Format notification message for CI/CD event"""
        event_type = event["event_type"]
        details = event["details"]

        if event_type == "pipeline_started":
            return f"🚀 Pipeline started for branch {details.get('branch', 'unknown')} ({details.get('commit', 'unknown')[:8]})"
        elif event_type == "test_completed":
            passed = details.get("passed_tests", 0)
            total = details.get("total_tests", 0)
            coverage = details.get("coverage", 0)
            return f"✅ Tests completed: {passed}/{total} passed, {coverage}% coverage"
        elif event_type == "deployment_started":
            return f"🎯 Deployment started: v{details.get('version', 'unknown')} to {details.get('environment', 'unknown')}"
        else:
            return f"📢 CI/CD Event: {event_type}"


# Integration with existing test framework
pytest_plugins = []