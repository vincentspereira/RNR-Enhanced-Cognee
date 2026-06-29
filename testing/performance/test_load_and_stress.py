"""
Performance Tests for RNR Enhanced Cognee System

Load testing, stress testing, and performance benchmarking for all system components.
Tests memory operations, API endpoints, agent coordination, and system scalability.
"""

import pytest
import asyncio
import json
import time
import requests
import psutil
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
import numpy as np

# Mark all tests as performance tests
pytestmark = [pytest.mark.performance, pytest.mark.slow, pytest.mark.requires_docker]


class TestSystemLoadTesting:
    """Test system performance under various load conditions"""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for RNR Enhanced Cognee API"""
        return "http://localhost:28080"

    @pytest.fixture
    def performance_thresholds(self):
        """Performance thresholds for testing"""
        return {
            "api_response_time": 100,  # ms
            "memory_operation_time": 50,  # ms
            "search_response_time": 200,  # ms
            "concurrent_users": 100,
            "memory_throughput": 1000,  # ops/second
            "error_rate": 0.01  # 1%
        }

    def test_memory_storage_load(self, api_base_url, performance_thresholds):
        """Test memory storage performance under load"""

        # Prepare test data
        test_memories = []
        for i in range(1000):
            memory_data = {
                "content": f"Performance test memory {i} with sufficient content for realistic testing",
                "agent_id": f"perf_agent_{i % 10}",
                "memory_type": "episodic",
                "metadata": {
                    "performance_test": True,
                    "index": i,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "category": "load_testing"
                }
            }
            test_memories.append(memory_data)

        # Test sequential storage performance
        sequential_start = time.time()
        sequential_memory_ids = []

        for memory_data in test_memories[:100]:  # Test with 100 memories first
            response = requests.post(
                f"{api_base_url}/api/v1/memory",
                json=memory_data,
                timeout=30
            )
            assert response.status_code == 201
            sequential_memory_ids.append(response.json()["memory_id"])

        sequential_time = time.time() - sequential_start
        sequential_avg_time = (sequential_time / 100) * 1000  # Convert to ms

        assert sequential_avg_time < performance_thresholds["memory_operation_time"], \
            f"Sequential storage avg time {sequential_avg_time:.2f}ms exceeds threshold {performance_thresholds['memory_operation_time']}ms"

        # Test concurrent storage performance
        concurrent_start = time.time()
        concurrent_memory_ids = []

        def store_memory(memory_data):
            response = requests.post(
                f"{api_base_url}/api/v1/memory",
                json=memory_data,
                timeout=30
            )
            return response.json()["memory_id"] if response.status_code == 201 else None

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(store_memory, memory_data) for memory_data in test_memories[100:300]]

            for future in as_completed(futures):
                memory_id = future.result()
                if memory_id:
                    concurrent_memory_ids.append(memory_id)

        concurrent_time = time.time() - concurrent_start
        concurrent_avg_time = (concurrent_time / 200) * 1000  # Convert to ms

        assert concurrent_avg_time < performance_thresholds["memory_operation_time"], \
            f"Concurrent storage avg time {concurrent_avg_time:.2f}ms exceeds threshold {performance_thresholds['memory_operation_time']}ms"
        assert len(concurrent_memory_ids) == 200, "Not all concurrent memories were stored successfully"

        # Calculate throughput
        total_memories = len(sequential_memory_ids) + len(concurrent_memory_ids)
        total_time = sequential_time + concurrent_time
        throughput = total_memories / total_time

        assert throughput > performance_thresholds["memory_throughput"], \
            f"Throughput {throughput:.2f} ops/sec below threshold {performance_thresholds['memory_throughput']} ops/sec"

        # Cleanup
        all_memory_ids = sequential_memory_ids + concurrent_memory_ids
        for memory_id in all_memory_ids[:50]:  # Clean up subset for time
            requests.delete(f"{api_base_url}/api/v1/memory/{memory_id}", timeout=30)

    def test_api_load_testing(self, api_base_url, performance_thresholds):
        """Test API performance under concurrent load"""

        # Define API endpoints to test
        api_endpoints = [
            {"method": "GET", "path": "/health", "expected_status": 200},
            {"method": "GET", "path": "/api/v1/memory", "expected_status": 200},
            {"method": "POST", "path": "/api/v1/memory/search", "expected_status": 200},
        ]

        # Test data for POST requests
        search_data = {
            "query": "test query for load testing",
            "limit": 10
        }

        # Load test parameters
        concurrent_users = 50
        requests_per_user = 20

        def user_simulation(user_id):
            """Simulate a single user making requests"""
            user_metrics = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_response_time": 0,
                "errors": []
            }

            for request_num in range(requests_per_user):
                endpoint = api_endpoints[request_num % len(api_endpoints)]

                request_start = time.time()
                try:
                    if endpoint["method"] == "GET":
                        response = requests.get(
                            f"{api_base_url}{endpoint['path']}",
                            timeout=30
                        )
                    else:  # POST
                        response = requests.post(
                            f"{api_base_url}{endpoint['path']}",
                            json=search_data,
                            timeout=30
                        )

                    request_time = time.time() - request_start
                    user_metrics["total_requests"] += 1
                    user_metrics["total_response_time"] += request_time

                    if response.status_code == endpoint["expected_status"]:
                        user_metrics["successful_requests"] += 1
                    else:
                        user_metrics["errors"].append(f"HTTP {response.status_code}")

                except Exception as e:
                    user_metrics["total_requests"] += 1
                    user_metrics["errors"].append(str(e))

            return user_metrics

        # Execute load test
        load_test_start = time.time()

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(concurrent_users)]
            user_metrics_list = [future.result() for future in as_completed(futures)]

        load_test_time = time.time() - load_test_start

        # Aggregate metrics
        total_requests = sum(m["total_requests"] for m in user_metrics_list)
        total_successful = sum(m["successful_requests"] for m in user_metrics_list)
        total_response_time = sum(m["total_response_time"] for m in user_metrics_list)
        total_errors = sum(len(m["errors"]) for m in user_metrics_list)

        avg_response_time = (total_response_time / total_requests) * 1000 if total_requests > 0 else 0
        error_rate = total_errors / total_requests if total_requests > 0 else 0
        requests_per_second = total_requests / load_test_time

        # Assert performance requirements
        assert avg_response_time < performance_thresholds["api_response_time"], \
            f"Average response time {avg_response_time:.2f}ms exceeds threshold {performance_thresholds['api_response_time']}ms"

        assert error_rate < performance_thresholds["error_rate"], \
            f"Error rate {error_rate:.2%} exceeds threshold {performance_thresholds['error_rate']}%"

        assert total_successful > (total_requests * 0.95), \
            f"Success rate {total_successful/total_requests:.2%} below 95%"

        print(f"Load Test Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful Requests: {total_successful}")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
        print(f"  Error Rate: {error_rate:.2%}")
        print(f"  Requests per Second: {requests_per_second:.2f}")

    def test_search_performance_under_load(self, api_base_url, performance_thresholds):
        """Test search performance with large dataset"""

        # Step 1: Create test dataset
        dataset_size = 500
        memory_ids = []

        print(f"Creating {dataset_size} test memories...")
        create_start = time.time()

        for i in range(dataset_size):
            memory_data = {
                "content": f"Search performance test memory {i}. This memory contains specific keywords like search, performance, testing, and optimization to enable effective similarity search testing.",
                "agent_id": f"search_agent_{i % 5}",
                "memory_type": "semantic",
                "metadata": {
                    "search_test": True,
                    "index": i,
                    "keywords": ["search", "performance", "testing", "optimization"],
                    "category": f"category_{i % 10}"
                }
            }

            response = requests.post(
                f"{api_base_url}/api/v1/memory",
                json=memory_data,
                timeout=30
            )

            if response.status_code == 201:
                memory_ids.append(response.json()["memory_id"])

        create_time = time.time() - create_start
        print(f"Created {len(memory_ids)} memories in {create_time:.2f}s")

        # Step 2: Test search performance
        search_queries = [
            "search performance optimization",
            "testing with specific keywords",
            "memory search and retrieval",
            "categorical search testing",
            "performance benchmarking"
        ]

        search_metrics = {
            "total_searches": 0,
            "total_response_time": 0,
            "result_counts": [],
            "errors": []
        }

        print("Running search performance tests...")
        search_start = time.time()

        # Run multiple searches concurrently
        def perform_search(query, search_id):
            try:
                search_start = time.time()
                response = requests.post(
                    f"{api_base_url}/api/v1/memory/search",
                    json={
                        "query": query,
                        "limit": 20,
                        "threshold": 0.7
                    },
                    timeout=30
                )
                search_time = time.time() - search_start

                if response.status_code == 200:
                    results = response.json()
                    return {
                        "search_id": search_id,
                        "query": query,
                        "response_time": search_time,
                        "result_count": len(results),
                        "success": True
                    }
                else:
                    return {
                        "search_id": search_id,
                        "query": query,
                        "response_time": search_time,
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                return {
                    "search_id": search_id,
                    "query": query,
                    "success": False,
                    "error": str(e)
                }

        # Run searches with concurrency
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i, query in enumerate(search_queries):
                for j in range(10):  # 10 searches per query
                    future = executor.submit(perform_search, query, f"{i}_{j}")
                    futures.append(future)

            search_results = [future.result() for future in as_completed(futures)]

        search_time = time.time() - search_start

        # Analyze search results
        successful_searches = [r for r in search_results if r["success"]]
        failed_searches = [r for r in search_results if not r["success"]]

        if successful_searches:
            avg_response_time = sum(r["response_time"] for r in successful_searches) / len(successful_searches)
            avg_result_count = sum(r["result_count"] for r in successful_searches) / len(successful_searches)

            assert avg_response_time < (performance_thresholds["search_response_time"] / 1000), \
                f"Search avg response time {avg_response_time*1000:.2f}ms exceeds threshold {performance_thresholds['search_response_time']}ms"

            print(f"Search Performance Results:")
            print(f"  Total Searches: {len(search_results)}")
            print(f"  Successful Searches: {len(successful_searches)}")
            print(f"  Failed Searches: {len(failed_searches)}")
            print(f"  Average Response Time: {avg_response_time*1000:.2f}ms")
            print(f"  Average Result Count: {avg_result_count:.1f}")
            print(f"  Searches per Second: {len(successful_searches)/search_time:.2f}")

        # Cleanup
        print(f"Cleaning up {len(memory_ids)} memories...")
        cleanup_start = time.time()

        for memory_id in memory_ids[:100]:  # Clean up subset for time
            requests.delete(f"{api_base_url}/api/v1/memory/{memory_id}", timeout=30)

        cleanup_time = time.time() - cleanup_start
        print(f"Cleanup completed in {cleanup_time:.2f}s")


class TestSystemStressTesting:
    """Test system behavior under extreme conditions"""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for RNR Enhanced Cognee API"""
        return "http://localhost:28080"

    def test_memory_system_stress(self, api_base_url):
        """Stress test memory system with high volume operations"""

        # Stress test parameters
        stress_duration = 60  # seconds
        target_ops_per_second = 100
        batch_size = 50

        stress_metrics = {
            "start_time": time.time(),
            "operations_completed": 0,
            "operations_failed": 0,
            "response_times": [],
            "memory_ids": []
        }

        print(f"Starting memory stress test for {stress_duration} seconds...")
        print(f"Target: {target_ops_per_second} ops/second")

        def stress_operation(operation_id):
            """Perform stress operation"""
            op_start = time.time()

            try:
                # Mix of operations (70% create, 20% search, 10% update)
                rand = np.random.random()
                if rand < 0.7:  # Create memory
                    memory_data = {
                        "content": f"Stress test memory {operation_id} with content designed to test system performance under load",
                        "agent_id": f"stress_agent_{operation_id % 10}",
                        "memory_type": "episodic",
                        "metadata": {
                            "stress_test": True,
                            "operation_id": operation_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }

                    response = requests.post(
                        f"{api_base_url}/api/v1/memory",
                        json=memory_data,
                        timeout=10
                    )

                    if response.status_code == 201:
                        memory_id = response.json()["memory_id"]
                        return {"success": True, "operation": "create", "memory_id": memory_id}
                    else:
                        return {"success": False, "operation": "create", "error": f"HTTP {response.status_code}"}

                elif rand < 0.9:  # Search memory
                    response = requests.post(
                        f"{api_base_url}/api/v1/memory/search",
                        json={
                            "query": f"stress test query {operation_id}",
                            "limit": 10
                        },
                        timeout=10
                    )

                    if response.status_code == 200:
                        return {"success": True, "operation": "search", "result_count": len(response.json())}
                    else:
                        return {"success": False, "operation": "search", "error": f"HTTP {response.status_code}"}

                else:  # Update memory
                    if stress_metrics["memory_ids"]:
                        memory_id = np.random.choice(stress_metrics["memory_ids"])
                        update_data = {
                            "content": f"Updated stress test memory {operation_id}",
                            "metadata": {"updated_by_stress_test": True}
                        }

                        response = requests.put(
                            f"{api_base_url}/api/v1/memory/{memory_id}",
                            json=update_data,
                            timeout=10
                        )

                        if response.status_code == 200:
                            return {"success": True, "operation": "update"}
                        else:
                            return {"success": False, "operation": "update", "error": f"HTTP {response.status_code}"}
                    else:
                        return {"success": False, "operation": "update", "error": "No memories to update"}

            except Exception as e:
                return {"success": False, "operation": "unknown", "error": str(e)}

        # Execute stress test
        end_time = stress_metrics["start_time"] + stress_duration

        with ThreadPoolExecutor(max_workers=20) as executor:
            while time.time() < end_time:
                # Calculate how many operations to run in this batch
                remaining_time = end_time - time.time()
                if remaining_time <= 0:
                    break

                batch_operations = min(
                    batch_size,
                    int(target_ops_per_second * remaining_time) - stress_metrics["operations_completed"]
                )

                if batch_operations <= 0:
                    break

                # Submit batch operations
                futures = [
                    executor.submit(stress_operation, stress_metrics["operations_completed"] + i)
                    for i in range(batch_operations)
                ]

                # Wait for batch completion
                batch_start = time.time()
                for future in as_completed(futures):
                    op_end = time.time()
                    result = future.result()

                    stress_metrics["operations_completed"] += 1
                    if result["success"]:
                        if result["operation"] == "create" and "memory_id" in result:
                            stress_metrics["memory_ids"].append(result["memory_id"])
                    else:
                        stress_metrics["operations_failed"] += 1

                    stress_metrics["response_times"].append(op_end - batch_start)

                # Brief pause to prevent overwhelming the system
                time.sleep(0.1)

        # Calculate stress test results
        total_time = time.time() - stress_metrics["start_time"]
        ops_per_second = stress_metrics["operations_completed"] / total_time
        success_rate = stress_metrics["operations_completed"] / (stress_metrics["operations_completed"] + stress_metrics["operations_failed"])
        avg_response_time = np.mean(stress_metrics["response_times"]) * 1000 if stress_metrics["response_times"] else 0
        p95_response_time = np.percentile(stress_metrics["response_times"], 95) * 1000 if stress_metrics["response_times"] else 0

        print(f"Stress Test Results:")
        print(f"  Duration: {total_time:.2f}s")
        print(f"  Operations Completed: {stress_metrics['operations_completed']}")
        print(f"  Operations Failed: {stress_metrics['operations_failed']}")
        print(f"  Operations per Second: {ops_per_second:.2f}")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
        print(f"  95th Percentile Response Time: {p95_response_time:.2f}ms")

        # Assert stress test requirements
        assert ops_per_second >= (target_ops_per_second * 0.8), \
            f"Operations per second {ops_per_second:.2f} below 80% of target {target_ops_per_second}"

        assert success_rate >= 0.95, \
            f"Success rate {success_rate:.2%} below 95%"

        assert p95_response_time < 5000, \
            f"95th percentile response time {p95_response_time:.2f}ms exceeds 5000ms"

        # Cleanup some memories to free space
        cleanup_count = min(len(stress_metrics["memory_ids"]), 200)
        for memory_id in stress_metrics["memory_ids"][:cleanup_count]:
            try:
                requests.delete(f"{api_base_url}/api/v1/memory/{memory_id}", timeout=10)
            except:
                pass

    def test_concurrent_user_simulation(self, api_base_url):
        """Simulate multiple concurrent users with realistic behavior"""

        num_users = 20
        simulation_duration = 30  # seconds

        class UserSimulator:
            def __init__(self, user_id, api_url):
                self.user_id = user_id
                self.api_url = api_url
                self.session_id = None
                self.memory_ids = []
                self.metrics = {
                    "operations": 0,
                    "successful": 0,
                    "response_times": []
                }

            def simulate_user_behavior(self):
                """Simulate realistic user behavior"""
                behaviors = [
                    self.create_memory,
                    self.search_memories,
                    self.update_memory,
                    self.get_memory,
                    self.search_with_filters
                ]

                end_time = time.time() + simulation_duration

                while time.time() < end_time:
                    # Random behavior selection
                    behavior = np.random.choice(behaviors)

                    try:
                        behavior()
                    except Exception as e:
                        print(f"User {self.user_id} behavior failed: {e}")

                    # Random pause between actions
                    time.sleep(np.random.uniform(0.1, 2.0))

            def create_memory(self):
                op_start = time.time()
                memory_data = {
                    "content": f"User {self.user_id} memory about {np.random.choice(['trading', 'analysis', 'security', 'performance'])}",
                    "agent_id": f"user_agent_{self.user_id}",
                    "memory_type": np.random.choice(["episodic", "semantic", "procedural"]),
                    "metadata": {
                        "user_id": self.user_id,
                        "session_id": self.session_id
                    }
                }

                response = requests.post(f"{self.api_url}/api/v1/memory", json=memory_data, timeout=10)

                self.metrics["operations"] += 1
                self.metrics["response_times"].append(time.time() - op_start)

                if response.status_code == 201:
                    self.memory_ids.append(response.json()["memory_id"])
                    self.metrics["successful"] += 1

            def search_memories(self):
                op_start = time.time()
                response = requests.post(
                    f"{self.api_url}/api/v1/memory/search",
                    json={
                        "query": f"user {self.user_id} memories",
                        "limit": 10
                    },
                    timeout=10
                )

                self.metrics["operations"] += 1
                self.metrics["response_times"].append(time.time() - op_start)

                if response.status_code == 200:
                    self.metrics["successful"] += 1

            def update_memory(self):
                if not self.memory_ids:
                    return

                op_start = time.time()
                memory_id = np.random.choice(self.memory_ids)

                update_data = {
                    "content": f"Updated by user {self.user_id}",
                    "metadata": {"last_updated_by_user": self.user_id}
                }

                response = requests.put(
                    f"{self.api_url}/api/v1/memory/{memory_id}",
                    json=update_data,
                    timeout=10
                )

                self.metrics["operations"] += 1
                self.metrics["response_times"].append(time.time() - op_start)

                if response.status_code == 200:
                    self.metrics["successful"] += 1

            def get_memory(self):
                if not self.memory_ids:
                    return

                op_start = time.time()
                memory_id = np.random.choice(self.memory_ids)

                response = requests.get(f"{self.api_url}/api/v1/memory/{memory_id}", timeout=10)

                self.metrics["operations"] += 1
                self.metrics["response_times"].append(time.time() - op_start)

                if response.status_code == 200:
                    self.metrics["successful"] += 1

            def search_with_filters(self):
                op_start = time.time()
                response = requests.post(
                    f"{self.api_url}/api/v1/memory/search",
                    json={
                        "query": "user memories",
                        "filters": {"user_id": self.user_id},
                        "limit": 20
                    },
                    timeout=10
                )

                self.metrics["operations"] += 1
                self.metrics["response_times"].append(time.time() - op_start)

                if response.status_code == 200:
                    self.metrics["successful"] += 1

        # Initialize users
        users = [UserSimulator(i, api_base_url) for i in range(num_users)]

        print(f"Starting concurrent user simulation with {num_users} users for {simulation_duration}s...")

        # Run simulation
        simulation_start = time.time()

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user.simulate_user_behavior) for user in users]

            # Wait for all users to complete or timeout
            for future in as_completed(futures, timeout=simulation_duration + 10):
                pass

        simulation_time = time.time() - simulation_start

        # Aggregate results
        total_operations = sum(user.metrics["operations"] for user in users)
        total_successful = sum(user.metrics["successful"] for user in users)
        all_response_times = []
        for user in users:
            all_response_times.extend(user.metrics["response_times"])

        avg_response_time = np.mean(all_response_times) * 1000 if all_response_times else 0
        p95_response_time = np.percentile(all_response_times, 95) * 1000 if all_response_times else 0
        success_rate = total_successful / total_operations if total_operations > 0 else 0
        ops_per_second = total_operations / simulation_time

        print(f"Concurrent User Simulation Results:")
        print(f"  Users: {num_users}")
        print(f"  Duration: {simulation_time:.2f}s")
        print(f"  Total Operations: {total_operations}")
        print(f"  Successful Operations: {total_successful}")
        print(f"  Operations per Second: {ops_per_second:.2f}")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Average Response Time: {avg_response_time:.2f}ms")
        print(f"  95th Percentile Response Time: {p95_response_time:.2f}ms")

        # Assert requirements
        assert success_rate >= 0.90, f"Success rate {success_rate:.2%} below 90%"
        assert p95_response_time < 2000, f"P95 response time {p95_response_time:.2f}ms exceeds 2000ms"
        assert ops_per_second >= (num_users * 2), f"Ops per second {ops_per_second:.2f} below {num_users * 2}"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])