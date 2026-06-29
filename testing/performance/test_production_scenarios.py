"""
RNR Enhanced Cognee Advanced Performance Testing Scenarios

This module provides comprehensive production-like performance testing scenarios for the Enhanced
Cognee Multi-Agent System, including real-world user behavior modeling, long-running stability
testing, resource utilization optimization, and performance regression detection.

Coverage Target: Part of overall performance testing infrastructure
Category: Advanced Performance Testing (Advanced Testing - Phase 3)
"""

import pytest
import asyncio
import json
import time
import random
import statistics
import threading
import psutil
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Performance Testing Markers
pytest.mark.performance = pytest.mark.performance
pytest.mark.production = pytest.mark.production
pytest.mark.load = pytest.mark.load
pytest.mark.stress = pytest.mark.stress
pytest.mark.stability = pytest.mark.stability
pytest.mark.regression = pytest.mark.regression


class PerformanceMetricType(Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    ERROR_RATE = "error_rate"
    CONCURRENCY = "concurrency"


@dataclass
class PerformanceBenchmark:
    """Performance benchmark baseline"""
    scenario_name: str
    metrics: Dict[str, float]
    created_at: datetime
    environment: str
    test_conditions: Dict[str, Any]


@dataclass
class PerformanceScenario:
    """Performance testing scenario definition"""
    scenario_id: str
    name: str
    description: str
    duration_minutes: int
    concurrent_users: int
    requests_per_second: int
    user_behavior_patterns: List[Dict[str, Any]]
    resource_limits: Dict[str, Any]
    success_criteria: Dict[str, Any]
    warmup_duration_minutes: int = 2


@dataclass
class PerformanceMetrics:
    """Performance metrics collection"""
    scenario_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    response_times: List[float]
    throughput_rps: float
    cpu_usage_avg: float
    cpu_usage_max: float
    memory_usage_avg: float
    memory_usage_max: float
    error_rate: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    resource_saturation_points: List[Dict[str, Any]]


class UserBehaviorSimulator:
    """Simulates realistic user behavior patterns"""

    def __init__(self):
        self.session_duration_range = (60, 1800)  # 1 minute to 30 minutes
        self.think_time_range = (0.5, 5.0)  # 0.5 to 5 seconds
        self.request_patterns = {
            "light_user": {"requests_per_minute": 2, "data_size_kb": 10},
            "medium_user": {"requests_per_minute": 10, "data_size_kb": 50},
            "heavy_user": {"requests_per_minute": 30, "data_size_kb": 200},
            "power_user": {"requests_per_minute": 60, "data_size_kb": 500}
        }

    def simulate_user_session(self, user_type: str,
                            scenario_duration: int) -> List[Dict[str, Any]]:
        """Simulate a user session with realistic behavior"""
        session_start = time.time()
        session_end = session_start + scenario_duration
        requests = []

        # Get user pattern
        pattern = self.request_patterns.get(user_type, self.request_patterns["medium_user"])
        requests_per_minute = pattern["requests_per_minute"]
        avg_request_interval = 60 / requests_per_minute

        current_time = session_start
        request_count = 0

        while current_time < session_end:
            # Add variability to request timing
            interval = avg_request_interval * random.uniform(0.5, 2.0)
            current_time += interval

            if current_time >= session_end:
                break

            # Simulate think time before request
            think_time = random.uniform(*self.think_time_range)
            current_time += think_time

            if current_time >= session_end:
                break

            # Generate request
            request = {
                "timestamp": current_time,
                "session_id": f"session_{int(session_start)}",
                "user_type": user_type,
                "request_id": f"req_{request_count}",
                "data_size_kb": pattern["data_size_kb"] * random.uniform(0.5, 2.0),
                "request_type": self._select_request_type(user_type),
                "expected_response_time": self._get_expected_response_time(user_type)
            }
            requests.append(request)
            request_count += 1

        return requests

    def _select_request_type(self, user_type: str) -> str:
        """Select request type based on user behavior"""
        request_weights = {
            "light_user": {"read": 0.8, "write": 0.2, "search": 0.0},
            "medium_user": {"read": 0.6, "write": 0.3, "search": 0.1},
            "heavy_user": {"read": 0.4, "write": 0.4, "search": 0.2},
            "power_user": {"read": 0.3, "write": 0.4, "search": 0.3}
        }

        weights = request_weights.get(user_type, request_weights["medium_user"])
        return random.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]

    def _get_expected_response_time(self, user_type: str) -> float:
        """Get expected response time based on request complexity"""
        base_times = {
            "light_user": 0.1,
            "medium_user": 0.2,
            "heavy_user": 0.3,
            "power_user": 0.5
        }
        return base_times.get(user_type, 0.2) * random.uniform(0.5, 2.0)


class ProductionPerformanceTestFramework:
    """Production-like performance testing framework"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.behavior_simulator = UserBehaviorSimulator()
        self.benchmarks = {}
        self.current_test = None
        self.monitoring_active = False

    async def execute_production_scenario(self, scenario: PerformanceScenario) -> PerformanceMetrics:
        """Execute a production-like performance scenario"""
        logger.info(f"Starting production scenario: {scenario.name}")

        self.current_test = scenario
        start_time = datetime.now(timezone.utc)

        # Initialize metrics collection
        self.metrics_collector.start_collection(scenario.scenario_id)

        try:
            # Warmup phase
            if scenario.warmup_duration_minutes > 0:
                await self._execute_warmup_phase(scenario)

            # Main test phase
            results = await self._execute_main_phase(scenario)

            # Cool-down phase
            await self._execute_cooldown_phase(scenario)

        finally:
            # Stop metrics collection
            raw_metrics = self.metrics_collector.stop_collection()

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # Process metrics
        processed_metrics = self._process_metrics(
            scenario.scenario_id, start_time, end_time, duration, results, raw_metrics
        )

        # Validate against success criteria
        self._validate_performance_criteria(processed_metrics, scenario.success_criteria)

        logger.info(f"Production scenario completed: {scenario.name}")
        return processed_metrics

    async def _execute_warmup_phase(self, scenario: PerformanceScenario):
        """Execute warmup phase to stabilize system"""
        logger.info("Starting warmup phase")

        warmup_duration = scenario.warmup_duration_minutes * 60
        warmup_users = min(10, scenario.concurrent_users // 4)

        # Generate light warmup traffic
        warmup_tasks = []
        for i in range(warmup_users):
            task = self._simulate_user_workload(
                f"warmup_user_{i}",
                "light_user",
                warmup_duration
            )
            warmup_tasks.append(task)

        # Wait for warmup to complete
        await asyncio.gather(*warmup_tasks, return_exceptions=True)

        # Additional stabilization time
        await asyncio.sleep(30)

    async def _execute_main_phase(self, scenario: PerformanceScenario) -> Dict[str, Any]:
        """Execute main performance testing phase"""
        logger.info("Starting main test phase")

        test_duration = scenario.duration_minutes * 60
        concurrent_users = scenario.concurrent_users

        # Calculate user distribution
        user_distribution = self._calculate_user_distribution(scenario.user_behavior_patterns)

        # Create user workload tasks
        tasks = []
        user_count = 0

        for user_type, percentage in user_distribution.items():
            users_of_type = int(concurrent_users * percentage / 100)

            for i in range(users_of_type):
                user_id = f"{user_type}_user_{user_count}"
                task = self._simulate_user_workload(
                    user_id,
                    user_type,
                    test_duration
                )
                tasks.append(task)
                user_count += 1

        # Start all user workloads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]

        return {
            "total_users": user_count,
            "successful_sessions": len(successful_results),
            "failed_sessions": len(failed_results),
            "results": successful_results,
            "errors": failed_results
        }

    async def _execute_cooldown_phase(self, scenario: PerformanceScenario):
        """Execute cooldown phase"""
        logger.info("Starting cooldown phase")
        await asyncio.sleep(60)  # 1 minute cooldown

    def _calculate_user_distribution(self, behavior_patterns: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate user type distribution"""
        if not behavior_patterns:
            # Default distribution
            return {
                "light_user": 30,
                "medium_user": 40,
                "heavy_user": 20,
                "power_user": 10
            }

        distribution = {}
        total_percentage = 0

        for pattern in behavior_patterns:
            user_type = pattern.get("user_type", "medium_user")
            percentage = pattern.get("percentage", 0)
            distribution[user_type] = percentage
            total_percentage += percentage

        # Normalize to 100%
        if total_percentage > 0:
            for user_type in distribution:
                distribution[user_type] = (distribution[user_type] / total_percentage) * 100

        return distribution

    async def _simulate_user_workload(self, user_id: str,
                                    user_type: str,
                                    duration_seconds: int) -> Dict[str, Any]:
        """Simulate individual user workload"""
        session_start = time.time()
        session_end = session_start + duration_seconds

        # Generate user session requests
        requests = self.behavior_simulator.simulate_user_session(
            user_type, duration_seconds
        )

        session_metrics = {
            "user_id": user_id,
            "user_type": user_type,
            "session_start": session_start,
            "session_end": session_end,
            "total_requests": len(requests),
            "completed_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": []
        }

        # Execute requests
        for request in requests:
            current_time = time.time()

            if current_time >= session_end:
                break

            # Execute request with simulated load
            try:
                response_time = await self._execute_request(request)
                session_metrics["response_times"].append(response_time)
                session_metrics["completed_requests"] += 1

                # Simulate processing time
                await asyncio.sleep(response_time / 1000)  # Convert ms to seconds

            except Exception as e:
                session_metrics["failed_requests"] += 1
                session_metrics["errors"].append(str(e))

        return session_metrics

    async def _execute_request(self, request: Dict[str, Any]) -> float:
        """Execute a single request with realistic latency"""
        request_type = request["request_type"]
        data_size = request["data_size_kb"]
        expected_time = request["expected_response_time"]

        # Simulate different response times based on request type
        base_response_times = {
            "read": 0.05,      # 50ms
            "write": 0.15,     # 150ms
            "search": 0.25,    # 250ms
            "complex": 0.5     # 500ms
        }

        base_time = base_response_times.get(request_type, 0.1)

        # Add data size factor
        size_factor = 1 + (data_size / 1000)  # 1ms per MB

        # Add variability and load factors
        load_factor = random.uniform(0.8, 1.5)  # System load variability
        variability = random.gauss(1.0, 0.2)    # Normal distribution variability

        # Calculate final response time
        response_time = base_time * size_factor * load_factor * variability * 1000  # Convert to ms

        # Simulate occasional errors
        if random.random() < 0.01:  # 1% error rate
            raise Exception(f"Simulated request error for {request['request_id']}")

        return max(10, response_time)  # Minimum 10ms response time

    def _process_metrics(self, scenario_id: str, start_time: datetime,
                        end_time: datetime, duration: float,
                        results: Dict[str, Any], raw_metrics: Dict[str, Any]) -> PerformanceMetrics:
        """Process and aggregate performance metrics"""

        # Collect response times from all user sessions
        all_response_times = []
        total_requests = 0
        successful_requests = 0
        failed_requests = 0

        for session_result in results.get("results", []):
            if isinstance(session_result, dict):
                all_response_times.extend(session_result.get("response_times", []))
                total_requests += session_result.get("total_requests", 0)
                successful_requests += session_result.get("completed_requests", 0)
                failed_requests += session_result.get("failed_requests", 0)

        # Calculate statistics
        if all_response_times:
            response_times_array = np.array(all_response_times)
            p50 = float(np.percentile(response_times_array, 50))
            p95 = float(np.percentile(response_times_array, 95))
            p99 = float(np.percentile(response_times_array, 99))
            avg_response_time = float(np.mean(response_times_array))
        else:
            p50 = p95 = p99 = avg_response_time = 0.0

        # Calculate throughput
        throughput = successful_requests / duration if duration > 0 else 0.0

        # Get resource metrics
        cpu_metrics = raw_metrics.get("cpu_usage", [])
        memory_metrics = raw_metrics.get("memory_usage", [])

        if cpu_metrics:
            avg_cpu = statistics.mean(cpu_metrics)
            max_cpu = max(cpu_metrics)
        else:
            avg_cpu = max_cpu = 0.0

        if memory_metrics:
            avg_memory = statistics.mean(memory_metrics)
            max_memory = max(memory_metrics)
        else:
            avg_memory = max_memory = 0.0

        # Calculate error rate
        error_rate = failed_requests / total_requests if total_requests > 0 else 0.0

        # Identify resource saturation points
        saturation_points = self._identify_saturation_points(raw_metrics)

        return PerformanceMetrics(
            scenario_id=scenario_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            response_times=all_response_times,
            throughput_rps=throughput,
            cpu_usage_avg=avg_cpu,
            cpu_usage_max=max_cpu,
            memory_usage_avg=avg_memory,
            memory_usage_max=max_memory,
            error_rate=error_rate,
            p50_response_time=p50,
            p95_response_time=p95,
            p99_response_time=p99,
            resource_saturation_points=saturation_points
        )

    def _identify_saturation_points(self, raw_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify resource saturation points"""
        saturation_points = []

        # Check CPU saturation
        cpu_metrics = raw_metrics.get("cpu_usage", [])
        for i, cpu_usage in enumerate(cpu_metrics):
            if cpu_usage > 90:  # CPU usage above 90%
                saturation_points.append({
                    "metric": "cpu_usage",
                    "value": cpu_usage,
                    "timestamp": i,
                    "threshold": 90,
                    "severity": "high" if cpu_usage > 95 else "medium"
                })

        # Check memory saturation
        memory_metrics = raw_metrics.get("memory_usage", [])
        for i, memory_usage in enumerate(memory_metrics):
            if memory_usage > 85:  # Memory usage above 85%
                saturation_points.append({
                    "metric": "memory_usage",
                    "value": memory_usage,
                    "timestamp": i,
                    "threshold": 85,
                    "severity": "high" if memory_usage > 95 else "medium"
                })

        return saturation_points

    def _validate_performance_criteria(self, metrics: PerformanceMetrics,
                                     success_criteria: Dict[str, Any]):
        """Validate metrics against success criteria"""
        violations = []

        # Check response time criteria
        if "max_p95_response_time" in success_criteria:
            max_p95 = success_criteria["max_p95_response_time"]
            if metrics.p95_response_time > max_p95:
                violations.append(f"P95 response time {metrics.p95_response_time:.2f}ms exceeds limit {max_p95}ms")

        if "max_p99_response_time" in success_criteria:
            max_p99 = success_criteria["max_p99_response_time"]
            if metrics.p99_response_time > max_p99:
                violations.append(f"P99 response time {metrics.p99_response_time:.2f}ms exceeds limit {max_p99}ms")

        # Check throughput criteria
        if "min_throughput" in success_criteria:
            min_throughput = success_criteria["min_throughput"]
            if metrics.throughput_rps < min_throughput:
                violations.append(f"Throughput {metrics.throughput_rps:.2f} RPS below minimum {min_throughput} RPS")

        # Check error rate criteria
        if "max_error_rate" in success_criteria:
            max_error_rate = success_criteria["max_error_rate"]
            if metrics.error_rate > max_error_rate:
                violations.append(f"Error rate {metrics.error_rate:.2%} exceeds maximum {max_error_rate:.2%}")

        # Check resource usage criteria
        if "max_cpu_usage" in success_criteria:
            max_cpu = success_criteria["max_cpu_usage"]
            if metrics.cpu_usage_avg > max_cpu:
                violations.append(f"Average CPU usage {metrics.cpu_usage_avg:.1f}% exceeds limit {max_cpu}%")

        if "max_memory_usage" in success_criteria:
            max_memory = success_criteria["max_memory_usage"]
            if metrics.memory_usage_avg > max_memory:
                violations.append(f"Average memory usage {metrics.memory_usage_avg:.1f}% exceeds limit {max_memory}%")

        if violations:
            error_message = f"Performance criteria violations: {'; '.join(violations)}"
            logger.error(error_message)
            raise AssertionError(error_message)

    def compare_with_benchmark(self, current_metrics: PerformanceMetrics,
                             benchmark: PerformanceBenchmark) -> Dict[str, Any]:
        """Compare current metrics with benchmark"""
        comparison = {
            "scenario": current_metrics.scenario_id,
            "benchmark_created": benchmark.created_at.isoformat(),
            "improvements": [],
            "regressions": [],
            "within_tolerance": []
        }

        tolerance = 0.1  # 10% tolerance

        # Compare key metrics
        metrics_to_compare = [
            ("p95_response_time", "P95 Response Time"),
            ("throughput_rps", "Throughput"),
            ("error_rate", "Error Rate"),
            ("cpu_usage_avg", "Average CPU Usage")
        ]

        for metric_key, metric_name in metrics_to_compare:
            current_value = getattr(current_metrics, metric_key)
            benchmark_value = benchmark.metrics.get(metric_key)

            if benchmark_value is None:
                continue

            # Calculate percentage change
            if benchmark_value > 0:
                change_percent = ((current_value - benchmark_value) / benchmark_value) * 100
            else:
                change_percent = 0

            comparison_item = {
                "metric": metric_name,
                "current": current_value,
                "benchmark": benchmark_value,
                "change_percent": change_percent
            }

            # Determine if improvement, regression, or within tolerance
            if abs(change_percent) <= tolerance * 100:
                comparison["within_tolerance"].append(comparison_item)
            elif self._is_improvement(metric_key, change_percent):
                comparison["improvements"].append(comparison_item)
            else:
                comparison["regressions"].append(comparison_item)

        return comparison

    def _is_improvement(self, metric_key: str, change_percent: float) -> bool:
        """Determine if metric change is an improvement"""
        # Lower is better for response times, error rates, resource usage
        lower_is_better = [
            "p95_response_time", "p99_response_time", "error_rate",
            "cpu_usage_avg", "memory_usage_avg"
        ]

        # Higher is better for throughput
        higher_is_better = ["throughput_rps"]

        if metric_key in lower_is_better:
            return change_percent < 0  # Decrease is improvement
        elif metric_key in higher_is_better:
            return change_percent > 0  # Increase is improvement
        else:
            return False


class MetricsCollector:
    """Collects system metrics during performance tests"""

    def __init__(self):
        self.collection_active = False
        self.metrics = {}
        self.collection_task = None

    def start_collection(self, scenario_id: str):
        """Start metrics collection"""
        self.collection_active = True
        self.metrics[scenario_id] = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_io": [],
            "network_io": [],
            "timestamps": []
        }

        # Start background collection task
        self.collection_task = asyncio.create_task(self._collect_metrics(scenario_id))

    def stop_collection(self) -> Dict[str, Any]:
        """Stop metrics collection and return collected data"""
        self.collection_active = False

        if self.collection_task:
            self.collection_task.cancel()
            try:
                self.collection_task.result()
            except asyncio.CancelledError:
                pass

        return self.metrics

    async def _collect_metrics(self, scenario_id: str):
        """Background task to collect system metrics"""
        while self.collection_active:
            try:
                # Collect CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics[scenario_id]["cpu_usage"].append(cpu_percent)

                # Collect memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.metrics[scenario_id]["memory_usage"].append(memory_percent)

                # Collect disk I/O
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.metrics[scenario_id]["disk_io"].append({
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes
                    })

                # Collect network I/O
                network_io = psutil.net_io_counters()
                if network_io:
                    self.metrics[scenario_id]["network_io"].append({
                        "bytes_sent": network_io.bytes_sent,
                        "bytes_recv": network_io.bytes_recv
                    })

                # Record timestamp
                self.metrics[scenario_id]["timestamps"].append(time.time())

            except Exception as e:
                logger.error(f"Error collecting metrics: {str(e)}")
                break


@pytest.fixture
def performance_framework():
    """Fixture for performance testing framework"""
    return ProductionPerformanceTestFramework()


@pytest.fixture
def production_scenarios():
    """Fixture providing production performance test scenarios"""
    return [
        # Normal Business Hours Load
        PerformanceScenario(
            scenario_id="PROD_NORMAL_LOAD",
            name="Normal Business Hours Load",
            description="Simulates normal daytime user traffic patterns",
            duration_minutes=30,
            concurrent_users=500,
            requests_per_second=100,
            user_behavior_patterns=[
                {"user_type": "light_user", "percentage": 40},
                {"user_type": "medium_user", "percentage": 35},
                {"user_type": "heavy_user", "percentage": 20},
                {"user_type": "power_user", "percentage": 5}
            ],
            resource_limits={
                "max_cpu_percent": 80,
                "max_memory_percent": 85,
                "max_disk_io_percent": 70
            },
            success_criteria={
                "max_p95_response_time": 500,  # ms
                "min_throughput": 80,  # RPS
                "max_error_rate": 0.01,  # 1%
                "max_cpu_usage": 75,  # %
                "max_memory_usage": 80  # %
            }
        ),

        # Peak Load Scenario
        PerformanceScenario(
            scenario_id="PROD_PEAK_LOAD",
            name="Peak Load Scenario",
            description="Simulates peak hour traffic with maximum concurrent users",
            duration_minutes=20,
            concurrent_users=1500,
            requests_per_second=300,
            user_behavior_patterns=[
                {"user_type": "light_user", "percentage": 25},
                {"user_type": "medium_user", "percentage": 30},
                {"user_type": "heavy_user", "percentage": 30},
                {"user_type": "power_user", "percentage": 15}
            ],
            resource_limits={
                "max_cpu_percent": 90,
                "max_memory_percent": 90,
                "max_disk_io_percent": 85
            },
            success_criteria={
                "max_p95_response_time": 1000,  # ms
                "min_throughput": 250,  # RPS
                "max_error_rate": 0.02,  # 2%
                "max_cpu_usage": 85,  # %
                "max_memory_usage": 85  # %
            }
        ),

        # Stress Test Scenario
        PerformanceScenario(
            scenario_id="PROD_STRESS_TEST",
            name="Stress Test Scenario",
            description="Tests system limits with extreme load",
            duration_minutes=15,
            concurrent_users=2500,
            requests_per_second=500,
            user_behavior_patterns=[
                {"user_type": "medium_user", "percentage": 20},
                {"user_type": "heavy_user", "percentage": 40},
                {"user_type": "power_user", "percentage": 40}
            ],
            resource_limits={
                "max_cpu_percent": 95,
                "max_memory_percent": 95,
                "max_disk_io_percent": 90
            },
            success_criteria={
                "max_p99_response_time": 2000,  # ms
                "min_throughput": 400,  # RPS
                "max_error_rate": 0.05,  # 5%
                "max_cpu_usage": 90,  # %
                "max_memory_usage": 90  # %
            }
        ),

        # Long-Running Stability Test
        PerformanceScenario(
            scenario_id="PROD_STABILITY_TEST",
            name="Long-Running Stability Test",
            description="Tests system stability over extended period",
            duration_minutes=120,  # 2 hours
            concurrent_users=200,
            requests_per_second=40,
            user_behavior_patterns=[
                {"user_type": "light_user", "percentage": 50},
                {"user_type": "medium_user", "percentage": 30},
                {"user_type": "heavy_user", "percentage": 20}
            ],
            resource_limits={
                "max_cpu_percent": 70,
                "max_memory_percent": 75,
                "max_disk_io_percent": 60
            },
            success_criteria={
                "max_p95_response_time": 300,  # ms
                "min_throughput": 35,  # RPS
                "max_error_rate": 0.005,  # 0.5%
                "max_cpu_usage": 65,  # %
                "max_memory_usage": 70  # %
            }
        )
    ]


class TestProductionPerformance:
    """Test production-like performance scenarios"""

    @pytest.mark.performance
    @pytest.mark.production
    async def test_normal_business_hours_load(self, performance_framework, production_scenarios):
        """Test normal business hours load scenario"""
        scenario = production_scenarios[0]  # Normal Load Scenario

        # Execute scenario
        metrics = await performance_framework.execute_production_scenario(scenario)

        # Validate basic metrics
        assert metrics.total_requests > 0, "No requests generated"
        assert metrics.successful_requests > 0, "No successful requests"

        # Validate success criteria
        assert metrics.p95_response_time <= scenario.success_criteria["max_p95_response_time"], \
            f"P95 response time {metrics.p95_response_time:.2f}ms exceeds limit"

        assert metrics.throughput_rps >= scenario.success_criteria["min_throughput"], \
            f"Throughput {metrics.throughput_rps:.2f} RPS below minimum"

        assert metrics.error_rate <= scenario.success_criteria["max_error_rate"], \
            f"Error rate {metrics.error_rate:.2%} exceeds maximum"

        # Validate resource usage
        assert metrics.cpu_usage_avg <= scenario.success_criteria["max_cpu_usage"], \
            f"Average CPU usage {metrics.cpu_usage_avg:.1f}% exceeds limit"

        assert metrics.memory_usage_avg <= scenario.success_criteria["max_memory_usage"], \
            f"Average memory usage {metrics.memory_usage_avg:.1f}% exceeds limit"

    @pytest.mark.performance
    @pytest.mark.production
    async def test_peak_load_performance(self, performance_framework, production_scenarios):
        """Test system performance under peak load"""
        scenario = production_scenarios[1]  # Peak Load Scenario

        # Execute scenario
        metrics = await performance_framework.execute_production_scenario(scenario)

        # Validate peak load handling
        assert metrics.concurrent_users >= scenario.concurrent_users * 0.9, \
            "Not enough concurrent users generated"

        # Validate performance under load
        assert metrics.p99_response_time <= scenario.success_criteria.get("max_p99_response_time", 2000), \
            f"P99 response time {metrics.p99_response_time:.2f}ms excessive under peak load"

        # Check for resource saturation
        high_saturation = [
            point for point in metrics.resource_saturation_points
            if point["severity"] == "high"
        ]

        # Allow some high saturation under peak load but not excessive
        assert len(high_saturation) <= len(metrics.resource_saturation_points) * 0.3, \
            "Excessive resource saturation under peak load"

    @pytest.mark.performance
    @pytest.mark.production
    async def test_stress_test_limits(self, performance_framework, production_scenarios):
        """Test system limits under stress conditions"""
        scenario = production_scenarios[2]  # Stress Test Scenario

        # Execute scenario
        metrics = await performance_framework.execute_production_scenario(scenario)

        # Stress tests should find system limits
        assert metrics.resource_saturation_points, \
            "No resource saturation detected in stress test"

        # Validate graceful degradation
        assert metrics.error_rate <= 0.1,  # Allow up to 10% errors under extreme stress
            f"Error rate {metrics.error_rate:.2%} too high even under stress"

        # System should maintain some level of service
        assert metrics.throughput_rps >= scenario.requests_per_second * 0.5, \
            "Throughput degraded too severely under stress"

    @pytest.mark.performance
    @pytest.mark.stability
    async def test_long_running_stability(self, performance_framework, production_scenarios):
        """Test system stability over extended period"""
        scenario = production_scenarios[3]  # Stability Test Scenario

        # Execute scenario
        metrics = await performance_framework.execute_production_scenario(scenario)

        # Validate extended duration
        assert metrics.duration_seconds >= scenario.duration_minutes * 60 * 0.95, \
            "Test duration shorter than expected"

        # Validate consistent performance over time
        response_time_variance = statistics.stdev(metrics.response_times) if len(metrics.response_times) > 1 else 0
        avg_response_time = statistics.mean(metrics.response_times) if metrics.response_times else 0

        # Response times should be relatively consistent (variance < mean)
        if avg_response_time > 0:
            variance_ratio = response_time_variance / avg_response_time
            assert variance_ratio < 2.0, \
                f"Response time variance too high: {variance_ratio:.2f}"

        # Validate no memory leaks (memory usage should not continuously increase)
        # This is a simplified check - in reality would analyze memory usage trend
        assert metrics.memory_usage_max < metrics.memory_usage_avg * 1.5, \
            "Potential memory leak detected"

    @pytest.mark.performance
    @pytest.mark.regression
    async def test_performance_regression_detection(self, performance_framework):
        """Test performance regression detection"""
        # Create baseline benchmark
        benchmark = PerformanceBenchmark(
            scenario_name="regression_test_baseline",
            metrics={
                "p95_response_time": 200.0,
                "throughput_rps": 150.0,
                "error_rate": 0.005,
                "cpu_usage_avg": 60.0,
                "memory_usage_avg": 65.0
            },
            created_at=datetime.now(timezone.utc) - timedelta(days=7),
            environment="staging",
            test_conditions={"concurrent_users": 100}
        )

        # Simulate current performance (with some regressions)
        current_metrics = PerformanceMetrics(
            scenario_id="regression_test_current",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(minutes=10),
            duration_seconds=600,
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            response_times=[random.uniform(100, 400) for _ in range(950)],
            throughput_rps=120.0,  # Regression: lower throughput
            cpu_usage_avg=75.0,    # Regression: higher CPU
            cpu_usage_max=90.0,
            memory_usage_avg=70.0,
            memory_usage_max=85.0,
            error_rate=0.05,        # Regression: higher error rate
            p50_response_time=180.0,
            p95_response_time=350.0,  # Regression: higher P95
            p99_response_time=400.0,
            resource_saturation_points=[]
        )

        # Compare with benchmark
        comparison = performance_framework.compare_with_benchmark(current_metrics, benchmark)

        # Validate regression detection
        assert len(comparison["regressions"]) > 0, \
            "Should detect performance regressions"

        # Check specific regressions
        regression_metrics = [r["metric"] for r in comparison["regressions"]]
        expected_regressions = ["Throughput", "Error Rate", "Average CPU Usage"]

        for expected in expected_regressions:
            assert expected in regression_metrics, \
                f"Should detect regression in {expected}"

    @pytest.mark.performance
    @pytest.mark.production
    async def test_user_behavior_simulation(self, performance_framework):
        """Test realistic user behavior simulation"""
        simulator = performance_framework.behavior_simulator

        # Test different user types
        user_types = ["light_user", "medium_user", "heavy_user", "power_user"]
        duration_minutes = 10

        for user_type in user_types:
            requests = simulator.simulate_user_session(user_type, duration_minutes * 60)

            # Validate request generation
            assert len(requests) > 0, f"No requests generated for {user_type}"

            # Validate request distribution
            request_types = [req["request_type"] for req in requests]
            unique_types = set(request_types)
            assert len(unique_types) > 0, f"No request types for {user_type}"

            # Validate timing patterns
            timestamps = [req["timestamp"] for req in requests]
            if len(timestamps) > 1:
                time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                assert all(diff > 0 for diff in time_diffs), "Invalid timestamps in requests"

            # Validate data sizes
            data_sizes = [req["data_size_kb"] for req in requests]
            assert all(size > 0 for size in data_sizes), "Invalid data sizes in requests"

    @pytest.mark.performance
    async def test_scalability_patterns(self, performance_framework):
        """Test system scalability patterns"""
        # Test with different load levels
        load_levels = [100, 500, 1000, 1500]
        scalability_results = []

        for concurrent_users in load_levels:
            # Create mini-scenario for scalability testing
            scenario = PerformanceScenario(
                scenario_id=f"scalability_test_{concurrent_users}",
                name=f"Scalability Test {concurrent_users} Users",
                description=f"Test scalability with {concurrent_users} concurrent users",
                duration_minutes=5,
                concurrent_users=concurrent_users,
                requests_per_second=concurrent_users // 5,
                user_behavior_patterns=[{"user_type": "medium_user", "percentage": 100}],
                resource_limits={},
                success_criteria={},
                warmup_duration_minutes=1
            )

            # Execute scenario
            metrics = await performance_framework.execute_production_scenario(scenario)

            scalability_results.append({
                "concurrent_users": concurrent_users,
                "throughput_rps": metrics.throughput_rps,
                "p95_response_time": metrics.p95_response_time,
                "cpu_usage_avg": metrics.cpu_usage_avg,
                "memory_usage_avg": metrics.memory_usage_avg
            })

        # Analyze scalability patterns
        # Throughput should scale linearly (approximately)
        throughputs = [r["throughput_rps"] for r in scalability_results]
        user_counts = [r["concurrent_users"] for r in scalability_results]

        # Calculate scaling efficiency
        scaling_efficiency = []
        for i in range(1, len(throughputs)):
            if i > 0:
                expected_increase = (throughputs[0] * user_counts[i]) / user_counts[0]
                actual_increase = throughputs[i]
                efficiency = actual_increase / expected_increase if expected_increase > 0 else 0
                scaling_efficiency.append(efficiency)

        # Validate scaling efficiency (should be reasonable)
        avg_efficiency = statistics.mean(scaling_efficiency) if scaling_efficiency else 0
        assert avg_efficiency >= 0.5, \
            f"Poor scaling efficiency: {avg_efficiency:.2f}"

        # Response times should not degrade excessively
        p95_times = [r["p95_response_time"] for r in scalability_results]
        max_acceptable_p95 = p95_times[0] * 3  # Allow 3x degradation

        for i, p95_time in enumerate(p95_times):
            assert p95_time <= max_acceptable_p95, \
                f"P95 response time degradation too high at {user_counts[i]} users: {p95_time:.2f}ms"

    @pytest.mark.performance
    @pytest.mark.production
    async def test_resource_utilization_optimization(self, performance_framework):
        """Test resource utilization under optimal conditions"""
        # Create optimized scenario
        optimized_scenario = PerformanceScenario(
            scenario_id="resource_optimization_test",
            name="Resource Utilization Test",
            description="Test optimal resource utilization patterns",
            duration_minutes=15,
            concurrent_users=300,
            requests_per_second=60,
            user_behavior_patterns=[
                {"user_type": "medium_user", "percentage": 60},
                {"user_type": "light_user", "percentage": 40}
            ],
            resource_limits={
                "max_cpu_percent": 70,
                "max_memory_percent": 75
            },
            success_criteria={
                "max_cpu_usage": 65,
                "max_memory_usage": 70,
                "max_p95_response_time": 400
            }
        )

        # Execute scenario
        metrics = await performance_framework.execute_production_scenario(optimized_scenario)

        # Validate efficient resource usage
        assert metrics.cpu_usage_avg <= 65, \
            f"CPU usage not optimized: {metrics.cpu_usage_avg:.1f}%"

        assert metrics.memory_usage_avg <= 70, \
            f"Memory usage not optimized: {metrics.memory_usage_avg:.1f}%"

        # Validate performance efficiency
        performance_per_cpu = metrics.throughput_rps / max(metrics.cpu_usage_avg, 1)
        assert performance_per_cpu >= 1.0, \
            f"Poor performance per CPU: {performance_per_cpu:.2f} RPS per CPU%"

        # Check for resource waste (usage too low for load)
        assert metrics.cpu_usage_avg >= 30, \
            f"CPU utilization too low: {metrics.cpu_usage_avg:.1f}%"

        assert metrics.memory_usage_avg >= 40, \
            f"Memory utilization too low: {metrics.memory_usage_avg:.1f}%"


# Integration with existing test framework
pytest_plugins = []