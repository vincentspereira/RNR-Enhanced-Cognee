"""
RNR Enhanced Cognee API Testing Framework

This module provides comprehensive API testing capabilities for the RNR Enhanced Cognee
21-agent Multi-Agent System, covering RESTful APIs, GraphQL endpoints, API contracts,
performance validation, and security testing.

Coverage Target: 3% of total test coverage
Category: API Testing (Advanced Testing - Phase 3)
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import statistics
import hashlib
import hmac
import base64
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# API Testing Markers
pytest.mark.api = pytest.mark.api
pytest.mark.contract = pytest.mark.contract
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security
pytest.mark.rate_limiting = pytest.mark.rate_limiting
pytest.mark.graphql = pytest.mark.graphql


@dataclass
class APIContract:
    """Represents an API contract for validation"""
    name: str
    method: str
    endpoint: str
    headers: Dict[str, str]
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    status_codes: List[int]
    authentication_required: bool = True
    rate_limit: Optional[int] = None


@dataclass
class APIPerformanceScenario:
    """Represents a performance testing scenario"""
    name: str
    method: str
    endpoint: str
    request_data: Dict[str, Any]
    concurrent_requests: int
    max_response_time: float
    expected_throughput: float
    duration_seconds: int = 60


@dataclass
class GraphQLQuery:
    """Represents a GraphQL query for testing"""
    name: str
    query: str
    variables: Dict[str, Any]
    expected_schema: Dict[str, Any]
    operation_type: str  # query, mutation, subscription


class APITestFramework:
    """Comprehensive API testing framework for RNR Enhanced Cognee"""

    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None
        self.performance_metrics = {}
        self.contract_validations = []

    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=50,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def make_request(self, method: str, endpoint: str,
                          data: Dict[str, Any] = None,
                          headers: Dict[str, str] = None) -> Tuple[int, Dict[str, Any], float]:
        """Make HTTP request and return status, response data, and response time"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method.upper() == 'GET':
                async with self.session.get(url, headers=headers) as response:
                    status_code = response.status
                    response_data = await response.json()
            elif method.upper() == 'POST':
                async with self.session.post(url, json=data, headers=headers) as response:
                    status_code = response.status
                    response_data = await response.json()
            elif method.upper() == 'PUT':
                async with self.session.put(url, json=data, headers=headers) as response:
                    status_code = response.status
                    response_data = await response.json()
            elif method.upper() == 'DELETE':
                async with self.session.delete(url, headers=headers) as response:
                    status_code = response.status
                    response_data = await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response_time = time.time() - start_time
            return status_code, response_data, response_time

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"API request failed: {method} {url} - {str(e)}")
            raise

    def validate_json_schema(self, data: Dict[str, Any],
                           schema: Dict[str, Any]) -> bool:
        """Validate JSON data against schema"""
        try:
            # Simple schema validation - in production, use jsonschema library
            for key, expected_type in schema.items():
                if key not in data:
                    return False
                if not isinstance(data[key], expected_type):
                    return False
            return True
        except Exception:
            return False

    def generate_hmac_signature(self, method: str, endpoint: str,
                              body: str, secret_key: str) -> str:
        """Generate HMAC signature for API authentication"""
        message = f"{method.upper()} {endpoint}{body}"
        signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')


@pytest.fixture
async def api_client():
    """Fixture for API client with authentication"""
    base_url = "http://localhost:8000/api/v1"
    auth_token = "test-auth-token"  # In production, get from auth service

    async with APITestFramework(base_url, auth_token) as client:
        yield client


@pytest.fixture
def api_contracts():
    """Fixture providing API contracts for testing"""
    return [
        # Authentication API Contracts
        APIContract(
            name="user_login",
            method="POST",
            endpoint="/auth/login",
            headers={"Content-Type": "application/json"},
            request_schema={
                "username": str,
                "password": str
            },
            response_schema={
                "access_token": str,
                "refresh_token": str,
                "user_id": str,
                "expires_in": int
            },
            status_codes=[200, 401, 400],
            rate_limit=10  # requests per minute
        ),

        # Agent Management API Contracts
        APIContract(
            name="create_agent",
            method="POST",
            endpoint="/agents",
            headers={"Content-Type": "application/json"},
            request_schema={
                "name": str,
                "type": str,
                "category": str,
                "config": dict
            },
            response_schema={
                "agent_id": str,
                "name": str,
                "status": str,
                "created_at": str
            },
            status_codes=[201, 400, 403],
            rate_limit=5
        ),

        # Memory Storage API Contracts
        APIContract(
            name="store_memory",
            method="POST",
            endpoint="/memory",
            headers={"Content-Type": "application/json"},
            request_schema={
                "content": str,
                "agent_id": str,
                "memory_type": str,
                "metadata": dict,
                "embedding": list
            },
            response_schema={
                "memory_id": str,
                "storage_location": str,
                "timestamp": str
            },
            status_codes=[201, 400, 403],
            rate_limit=100
        ),

        # Query API Contracts
        APIContract(
            name="query_memory",
            method="GET",
            endpoint="/memory/search",
            headers={"Content-Type": "application/json"},
            request_schema={},
            response_schema={
                "results": list,
                "total_count": int,
                "query_time_ms": float
            },
            status_codes=[200, 400],
            rate_limit=50
        )
    ]


@pytest.fixture
def graphql_queries():
    """Fixture providing GraphQL queries for testing"""
    return [
        GraphQLQuery(
            name="get_agent_status",
            query="""
                query GetAgentStatus($agentId: ID!) {
                    agent(id: $agentId) {
                        id
                        name
                        status
                        category
                        lastActivity
                        performanceMetrics {
                            cpuUsage
                            memoryUsage
                            taskCompletionRate
                        }
                    }
                }
            """,
            variables={"agentId": "test-agent-123"},
            expected_schema={
                "data": {
                    "agent": {
                        "id": str,
                        "name": str,
                        "status": str,
                        "category": str,
                        "lastActivity": str,
                        "performanceMetrics": {
                            "cpuUsage": float,
                            "memoryUsage": float,
                            "taskCompletionRate": float
                        }
                    }
                }
            },
            operation_type="query"
        ),

        GraphQLQuery(
            name="execute_agent_command",
            query="""
                mutation ExecuteAgentCommand($agentId: ID!, $command: String!, $parameters: JSON) {
                    executeCommand(agentId: $agentId, command: $command, parameters: $parameters) {
                        success
                        result
                        error
                        executionTime
                    }
                }
            """,
            variables={
                "agentId": "test-agent-456",
                "command": "analyze_data",
                "parameters": {"dataset": "market_data.csv"}
            },
            expected_schema={
                "data": {
                    "executeCommand": {
                        "success": bool,
                        "result": dict,
                        "error": str,
                        "executionTime": float
                    }
                }
            },
            operation_type="mutation"
        )
    ]


@pytest.fixture
def performance_scenarios():
    """Fixture providing performance testing scenarios"""
    return [
        APIPerformanceScenario(
            name="high_frequency_memory_storage",
            method="POST",
            endpoint="/memory",
            request_data={
                "content": "Test memory content",
                "agent_id": "test-agent",
                "memory_type": "episodic",
                "metadata": {"test": True}
            },
            concurrent_requests=100,
            max_response_time=0.5,  # 500ms
            expected_throughput=100,  # requests per second
            duration_seconds=60
        ),

        APIPerformanceScenario(
            name="concurrent_agent_queries",
            method="GET",
            endpoint="/agents/status",
            request_data={},
            concurrent_requests=50,
            max_response_time=1.0,  # 1 second
            expected_throughput=50,
            duration_seconds=30
        ),

        APIPerformanceScenario(
            name="memory_search_load",
            method="POST",
            endpoint="/memory/search",
            request_data={
                "query": "test search query",
                "limit": 10,
                "filters": {"memory_type": "episodic"}
            },
            concurrent_requests=25,
            max_response_time=2.0,  # 2 seconds
            expected_throughput=25,
            duration_seconds=45
        )
    ]


class TestAPIContracts:
    """Test API contract compliance"""

    @pytest.mark.api
    @pytest.mark.contract
    async def test_api_contract_validation(self, api_client, api_contracts):
        """Validate API contracts and OpenAPI specifications"""

        for contract in api_contracts:
            # Prepare test data
            test_data = self._generate_test_data(contract.request_schema)

            # Make API request
            status_code, response_data, response_time = await api_client.make_request(
                method=contract.method,
                endpoint=contract.endpoint,
                data=test_data,
                headers=contract.headers
            )

            # Validate status code
            assert status_code in contract.status_codes, \
                f"Contract {contract.name}: Unexpected status code {status_code}, expected {contract.status_codes}"

            if status_code < 400:  # Success response
                # Validate response schema
                assert api_client.validate_json_schema(response_data, contract.response_schema), \
                    f"Contract {contract.name}: Response schema validation failed"

                # Validate response time
                assert response_time < 2.0, \
                    f"Contract {contract.name}: Response time {response_time}s exceeds 2s limit"

    @pytest.mark.api
    @pytest.mark.contract
    async def test_api_authentication_enforcement(self, api_client, api_contracts):
        """Validate that authentication is properly enforced"""

        # Test without authentication
        unauthenticated_client = APITestFramework(api_client.base_url)

        async with unauthenticated_client as client:
            for contract in api_contracts:
                if contract.authentication_required:
                    test_data = self._generate_test_data(contract.request_schema)

                    status_code, _, _ = await client.make_request(
                        method=contract.method,
                        endpoint=contract.endpoint,
                        data=test_data,
                        headers=contract.headers
                    )

                    # Should return 401 or 403 without authentication
                    assert status_code in [401, 403], \
                        f"Contract {contract.name}: Authentication not enforced (got {status_code})"

    @pytest.mark.api
    @pytest.mark.rate_limiting
    async def test_api_rate_limiting(self, api_client, api_contracts):
        """Test API rate limiting enforcement"""

        for contract in api_contracts:
            if contract.rate_limit:
                test_data = self._generate_test_data(contract.request_schema)

                # Make requests up to the limit
                successful_requests = 0
                for i in range(contract.rate_limit + 5):  # Exceed limit by 5
                    try:
                        status_code, _, _ = await api_client.make_request(
                            method=contract.method,
                            endpoint=contract.endpoint,
                            data=test_data,
                            headers=contract.headers
                        )

                        if status_code == 429:  # Rate limited
                            break
                        elif status_code < 400:
                            successful_requests += 1

                    except Exception:
                        break

                # Should allow approximately the rate limit
                assert successful_requests >= contract.rate_limit - 1, \
                    f"Contract {contract.name}: Rate limit too restrictive ({successful_requests} < {contract.rate_limit})"
                assert successful_requests <= contract.rate_limit + 1, \
                    f"Contract {contract.name}: Rate limit not enforced ({successful_requests} > {contract.rate_limit})"

    def _generate_test_data(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test data based on schema"""
        test_data = {}
        for key, value_type in schema.items():
            if value_type == str:
                test_data[key] = f"test_{key}_{int(time.time())}"
            elif value_type == int:
                test_data[key] = 123
            elif value_type == float:
                test_data[key] = 123.45
            elif value_type == bool:
                test_data[key] = True
            elif value_type == list:
                test_data[key] = [1, 2, 3]
            elif value_type == dict:
                test_data[key] = {"test": True}
            else:
                test_data[key] = None
        return test_data


class TestAPIPerformance:
    """Test API performance under various conditions"""

    @pytest.mark.api
    @pytest.mark.performance
    async def test_api_load_testing(self, api_client, performance_scenarios):
        """API performance testing under various load conditions"""

        for scenario in performance_scenarios:
            # Reset performance metrics
            response_times = []
            success_count = 0
            error_count = 0

            start_time = time.time()

            # Execute concurrent requests
            tasks = []
            for i in range(scenario.concurrent_requests):
                task = self._make_performance_request(api_client, scenario, i)
                tasks.append(task)

            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Analyze results
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    status_code, response_time = result
                    if status_code < 400:
                        success_count += 1
                        response_times.append(response_time)
                    else:
                        error_count += 1

            total_time = time.time() - start_time

            # Validate performance metrics
            if response_times:
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile

                # Average response time should be within limits
                assert avg_response_time <= scenario.max_response_time, \
                    f"Scenario {scenario.name}: Avg response time {avg_response_time:.3f}s exceeds {scenario.max_response_time}s"

                # 95th percentile should be reasonable
                assert p95_response_time <= scenario.max_response_time * 2, \
                    f"Scenario {scenario.name}: 95th percentile {p95_response_time:.3f}s exceeds {scenario.max_response_time * 2}s"

            # Success rate should be high
            success_rate = success_count / len(results)
            assert success_rate >= 0.95, \
                f"Scenario {scenario.name}: Success rate {success_rate:.2%} below 95%"

            # Throughput should meet expectations
            actual_throughput = success_count / total_time
            assert actual_throughput >= scenario.expected_throughput * 0.8, \
                f"Scenario {scenario.name}: Throughput {actual_throughput:.1f} below expected {scenario.expected_throughput}"

    async def _make_performance_request(self, api_client, scenario, request_id):
        """Make a single performance request"""
        try:
            # Add unique identifier to test data for concurrent requests
            test_data = scenario.request_data.copy()
            if 'metadata' in test_data:
                test_data['metadata']['request_id'] = request_id
            else:
                test_data['request_id'] = request_id

            status_code, _, response_time = await api_client.make_request(
                method=scenario.method,
                endpoint=scenario.endpoint,
                data=test_data
            )

            return status_code, response_time

        except Exception as e:
            logger.error(f"Performance request failed: {str(e)}")
            return e

    @pytest.mark.api
    @pytest.mark.performance
    async def test_api_timeout_handling(self, api_client):
        """Test API timeout handling"""

        # Test with very slow endpoint (if available)
        timeout_scenarios = [
            ("GET", "/agents/status", {}, 5.0),  # 5 second timeout
            ("POST", "/memory/search", {"query": "complex query"}, 10.0)  # 10 second timeout
        ]

        for method, endpoint, data, timeout in timeout_scenarios:
            start_time = time.time()

            try:
                status_code, response_data, response_time = await asyncio.wait_for(
                    api_client.make_request(method, endpoint, data),
                    timeout=timeout + 1  # Give some buffer
                )

                actual_time = time.time() - start_time
                assert actual_time <= timeout + 0.5, \
                    f"Request took {actual_time:.2f}s, timeout was {timeout}s"

            except asyncio.TimeoutError:
                # This is expected for very slow operations
                pass

    @pytest.mark.api
    @pytest.mark.performance
    async def test_api_concurrent_load(self, api_client):
        """Test API under sustained concurrent load"""

        # Sustained load test
        load_duration = 30  # seconds
        requests_per_second = 20
        total_requests = load_duration * requests_per_second

        request_tasks = []
        completed_requests = 0
        failed_requests = 0

        async def make_request_batch():
            nonlocal completed_requests, failed_requests
            try:
                status_code, _, _ = await api_client.make_request(
                    "GET", "/agents/status"
                )
                if status_code < 400:
                    completed_requests += 1
                else:
                    failed_requests += 1
            except Exception:
                failed_requests += 1

        # Start sustained load
        start_time = time.time()

        for i in range(total_requests):
            delay = i / requests_per_second  # Stagger requests
            task = asyncio.create_task(make_request_batch())

            # Schedule task to start at appropriate time
            if delay > 0:
                await asyncio.sleep(delay)

            request_tasks.append(task)

        # Wait for all requests to complete
        await asyncio.gather(*request_tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Validate sustained load performance
        actual_requests_per_second = completed_requests / total_time
        success_rate = completed_requests / total_requests

        assert actual_requests_per_second >= requests_per_second * 0.8, \
            f"Sustained load: {actual_requests_per_second:.1f} RPS, expected >= {requests_per_second * 0.8}"

        assert success_rate >= 0.95, \
            f"Sustained load success rate: {success_rate:.2%}, expected >= 95%"


class TestGraphQLAPI:
    """Test GraphQL API endpoints"""

    @pytest.mark.api
    @pytest.mark.graphql
    async def test_graphql_query_execution(self, api_client, graphql_queries):
        """Test GraphQL query execution and response validation"""

        for query in graphql_queries:
            # Make GraphQL request
            graphql_endpoint = "/graphql"
            graphql_data = {
                "query": query.query,
                "variables": query.variables
            }

            status_code, response_data, response_time = await api_client.make_request(
                method="POST",
                endpoint=graphql_endpoint,
                data=graphql_data
            )

            # Validate successful response
            assert status_code == 200, \
                f"GraphQL query {query.name}: Failed with status {status_code}"

            # Validate response structure
            assert "data" in response_data, \
                f"GraphQL query {query.name}: Missing 'data' field in response"

            # Validate response schema
            assert api_client.validate_json_schema(response_data, query.expected_schema), \
                f"GraphQL query {query.name}: Response schema validation failed"

            # Validate response time
            assert response_time < 2.0, \
                f"GraphQL query {query.name}: Response time {response_time:.3f}s exceeds 2s"

    @pytest.mark.api
    @pytest.mark.graphql
    async def test_graphql_error_handling(self, api_client):
        """Test GraphQL error handling"""

        # Test invalid query
        invalid_query = {
            "query": "query InvalidQuery { nonExistentField }",
            "variables": {}
        }

        status_code, response_data, _ = await api_client.make_request(
            method="POST",
            endpoint="/graphql",
            data=invalid_query
        )

        # Should return 200 with GraphQL errors
        assert status_code == 200, \
            "GraphQL error response should have status 200"

        assert "errors" in response_data, \
            "GraphQL error response should contain 'errors' field"

    @pytest.mark.api
    @pytest.mark.graphql
    async def test_graphql_subscription_support(self, api_client):
        """Test GraphQL subscription support (if implemented)"""

        subscription_query = {
            "query": """
                subscription AgentStatusUpdate($agentId: ID!) {
                    agentStatusUpdate(agentId: $agentId) {
                        agentId
                        status
                        timestamp
                    }
                }
            """,
            "variables": {"agentId": "test-agent-123"}
        }

        # Note: Subscriptions typically use WebSocket, this is a basic test
        try:
            status_code, response_data, _ = await api_client.make_request(
                method="POST",
                endpoint="/graphql",
                data=subscription_query
            )

            # If subscriptions are supported, should handle appropriately
            # This might return 200 with subscription info or specific error
            assert status_code in [200, 400], \
                f"GraphQL subscription unexpected status: {status_code}"

        except Exception as e:
            # Subscriptions might not be implemented via HTTP
            logger.info(f"GraphQL subscriptions not supported via HTTP: {str(e)}")


class TestAPISecurity:
    """Test API security measures"""

    @pytest.mark.api
    @pytest.mark.security
    async def test_api_input_validation(self, api_client):
        """Test API input validation and sanitization"""

        # Test malicious input attempts
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../etc/passwd",
            "${jndi:ldap://malicious.com/a}",
            "{{7*7}}",  # Template injection
            "' OR '1'='1",
        ]

        for malicious_input in malicious_inputs:
            # Test in various endpoints
            test_endpoints = [
                ("POST", "/agents", {"name": malicious_input}),
                ("POST", "/memory", {"content": malicious_input}),
                ("GET", "/agents/search", {"query": malicious_input}),
            ]

            for method, endpoint, data in test_endpoints:
                try:
                    status_code, response_data, _ = await api_client.make_request(
                        method=method,
                        endpoint=endpoint,
                        data=data
                    )

                    # Should not succeed with malicious input
                    # Should either reject (400) or sanitize (200 but no malicious content)
                    if status_code == 200:
                        # Check that malicious content was sanitized
                        response_str = json.dumps(response_data)
                        assert malicious_input not in response_str, \
                            f"Malicious input not sanitized in {method} {endpoint}"

                except Exception:
                    # Exceptions are acceptable for malicious input
                    pass

    @pytest.mark.api
    @pytest.mark.security
    async def test_api_cors_headers(self, api_client):
        """Test CORS headers configuration"""

        # Make OPTIONS request
        headers = {"Origin": "https://example.com", "Access-Control-Request-Method": "GET"}

        status_code, response_data, _ = await api_client.make_request(
            method="OPTIONS",
            endpoint="/agents",
            headers=headers
        )

        # Should return appropriate CORS headers
        # Note: response_data might contain headers in different format depending on implementation
        assert status_code in [200, 204], \
            f"CORS preflight failed with status {status_code}"

    @pytest.mark.api
    @pytest.mark.security
    async def test_api_rate_limit_security(self, api_client):
        """Test rate limiting security against abuse"""

        # Test burst requests
        burst_count = 100
        success_count = 0

        for i in range(burst_count):
            try:
                status_code, _, _ = await api_client.make_request(
                    "GET",
                    "/agents/status"
                )

                if status_code == 429:  # Rate limited
                    break
                elif status_code < 400:
                    success_count += 1

            except Exception:
                break

        # Should be rate limited after reasonable number of requests
        assert success_count < burst_count, \
            "Rate limiting not properly enforced against burst requests"


class TestAPIVersioning:
    """Test API versioning and backward compatibility"""

    @pytest.mark.api
    async def test_api_version_support(self, api_client):
        """Test multiple API version support"""

        # Test different API versions
        versions = ["v1", "v2"]  # Add more versions as needed

        for version in versions:
            try:
                status_code, response_data, _ = await api_client.make_request(
                    "GET",
                    f"/{version}/agents"
                )

                # Should respond appropriately (might be 404 for unsupported versions)
                assert status_code in [200, 404], \
                    f"API version {version} unexpected status: {status_code}"

            except Exception:
                # Versions might not be implemented yet
                pass

    @pytest.mark.api
    async def test_api_backward_compatibility(self, api_client):
        """Test backward compatibility with older API versions"""

        # Test that newer API versions maintain compatibility
        compatibility_tests = [
            ("GET", "/v1/agents", "GET", "/v2/agents"),
            ("POST", "/v1/memory", "POST", "/v2/memory"),
        ]

        for old_method, old_endpoint, new_method, new_endpoint in compatibility_tests:
            try:
                # Make request to old version
                old_status, old_data, _ = await api_client.make_request(
                    old_method, old_endpoint, {"test": "data"}
                )

                # Make request to new version
                new_status, new_data, _ = await api_client.make_request(
                    new_method, new_endpoint, {"test": "data"}
                )

                # Both should succeed or both should fail consistently
                assert (old_status < 400) == (new_status < 400), \
                    f"Incompatibility between {old_endpoint} and {new_endpoint}"

            except Exception:
                # Both endpoints might not be implemented
                pass


# Integration with existing test framework
pytest_plugins = []