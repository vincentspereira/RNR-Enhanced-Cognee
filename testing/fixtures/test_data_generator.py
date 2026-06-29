"""
Test Data Generator for RNR Enhanced Cognee Testing

Provides comprehensive test data generation for various testing scenarios
including performance testing, load testing, security testing, and edge cases.
"""

import json
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
import secrets
import string
import hashlib
from dataclasses import dataclass
from enum import Enum

class DataCategory(Enum):
    """Test data categories"""
    AUTHENTICATION = "authentication"
    TRADING = "trading"
    MEMORY = "memory"
    AGENT = "agent"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    COORDINATION = "coordination"

class MemoryType(Enum):
    """Memory types for RNR Enhanced Cognee"""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    FACTUAL = "factual"
    WORKING = "working"

class AgentCategory(Enum):
    """Agent categories"""
    ATS = "ats"
    OMA = "oma"
    SMC = "smc"

@dataclass
class TestMemoryData:
    """Structure for test memory data"""
    content: str
    agent_id: str
    memory_type: MemoryType
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: Optional[datetime] = None

@dataclass
class TestAgentData:
    """Structure for test agent data"""
    agent_id: str
    agent_type: str
    category: AgentCategory
    capabilities: List[str]
    configuration: Dict[str, Any]
    status: str = "active"

@dataclass
class TestUserData:
    """Structure for test user data"""
    username: str
    email: str
    password: str
    role: str
    preferences: Dict[str, Any]
    profile: Dict[str, Any]

class TestDataGenerator:
    """Comprehensive test data generator for RNR Enhanced Cognee"""

    def __init__(self, seed: Optional[int] = None):
        """Initialize test data generator with optional seed"""
        if seed:
            random.seed(seed)
            np.random.seed(seed)

        # Agent configurations
        self.ats_agents = [
            "algorithmic-trading-system",
            "risk-management",
            "market-analysis",
            "portfolio-optimization",
            "trade-execution",
            "volatility-analysis",
            "sentiment-analysis"
        ]

        self.oma_agents = [
            "code-reviewer",
            "security-auditor",
            "development-agent",
            "documentation-agent",
            "testing-agent",
            "architecture-agent",
            "requirements-analyst",
            "project-manager",
            "quality-assurance",
            "compliance-officer"
        ]

        self.smc_agents = [
            "context-manager",
            "communication-coordinator",
            "performance-monitor",
            "resource-manager",
            "conflict-resolver",
            "synchronization-manager"
        ]

        # Test data pools
        self.trading_symbols = ["BTC/USD", "ETH/USD", "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        self.memory_keywords = [
            "analysis", "algorithm", "optimization", "security", "performance",
            "coordination", "trading", "market", "risk", "strategy"
        ]

        self.security_threats = [
            "sql_injection", "xss", "csrf", "authentication_bypass",
            "data_breach", "privilege_escalation", "session_hijacking"
        ]

    def generate_memory_data(self, category: DataCategory, count: int = 1) -> List[TestMemoryData]:
        """Generate memory data for specific category"""

        memories = []

        for i in range(count):
            if category == DataCategory.TRADING:
                memory = self._generate_trading_memory(i)
            elif category == DataCategory.AGENT:
                memory = self._generate_agent_memory(i)
            elif category == DataCategory.SECURITY:
                memory = self._generate_security_memory(i)
            elif category == DataCategory.PERFORMANCE:
                memory = self._generate_performance_memory(i)
            elif category == DataCategory.COMPLIANCE:
                memory = self._generate_compliance_memory(i)
            elif category == DataCategory.COORDINATION:
                memory = self._generate_coordination_memory(i)
            else:  # MEMORY or default
                memory = self._generate_general_memory(i)

            memories.append(memory)

        return memories

    def _generate_trading_memory(self, index: int) -> TestMemoryData:
        """Generate trading-related memory"""
        symbol = random.choice(self.trading_symbols)
        action = random.choice(["BUY", "SELL", "HOLD"])
        confidence = random.uniform(0.6, 1.0)
        price = random.uniform(100, 100000)

        content_templates = [
            f"Executed {action} order for {symbol} at ${price:.2f} with {confidence:.2%} confidence",
            f"Market analysis for {symbol} shows {action.lower()} signal, confidence: {confidence:.2%}",
            f"Risk assessment for {symbol} position approved, price target: ${price:.2f}",
            f"Portfolio rebalancing triggered for {symbol}, allocated ${random.uniform(10000, 100000):.2f}"
        ]

        content = random.choice(content_templates)

        metadata = {
            "symbol": symbol,
            "action": action,
            "price": price,
            "confidence": confidence,
            "volume": random.randint(1000, 10000000),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "trading",
            "risk_score": random.uniform(0.1, 0.9),
            "strategy": random.choice(["momentum", "mean_reversion", "arbitrage", "trend_following"])
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice(self.ats_agents),
            memory_type=MemoryType.EPISODIC,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_agent_memory(self, index: int) -> TestMemoryData:
        """Generate agent-related memory"""
        agent_types = ["code_review", "development", "architecture", "testing", "documentation"]
        agent_type = random.choice(agent_types)
        status = random.choice(["completed", "in_progress", "failed", "pending"])

        content_templates = [
            f"Code review completed for {agent_type} module with {random.randint(1, 50)} issues found",
            f"{agent_type.title()} task {status}: {random.choice(['security review', 'performance optimization', 'bug fixing', 'feature implementation'])}",
            f"Agent coordination session completed for {agent_type} workflow, {random.randint(2, 10)} agents participated",
            f"Documentation updated for {agent_type} system, version {random.randint(1, 10)}"
        ]

        content = random.choice(content_templates)

        metadata = {
            "agent_type": agent_type,
            "status": status,
            "priority": random.choice(["low", "medium", "high", "critical"]),
            "complexity": random.randint(1, 10),
            "duration_hours": random.uniform(0.5, 40),
            "participants": random.sample(self.oma_agents + self.smc_agents, random.randint(2, 5)),
            "quality_score": random.uniform(0.6, 1.0)
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice(self.oma_agents),
            memory_type=MemoryType.PROCEDURAL,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_security_memory(self, index: int) -> TestMemoryData:
        """Generate security-related memory"""
        threat_type = random.choice(self.security_threats)
        severity = random.choice(["low", "medium", "high", "critical"])
        resolved = random.choice([True, False])

        content_templates = [
            f"Security scan detected {threat_type} vulnerability, severity: {severity}",
            f"Penetration testing completed for {threat_type} scenario, {random.randint(1, 20)} vulnerabilities found",
            f"Security incident resolved: {threat_type}, status: {'fixed' if resolved else 'investigating'}",
            f"Compliance audit completed for {threat_type} controls, status: {'passed' if resolved else 'action_required'}"
        ]

        content = random.choice(content_templates)

        metadata = {
            "threat_type": threat_type,
            "severity": severity,
            "resolved": resolved,
            "cve_id": f"CVE-{random.randint(2020, 2024)}-{random.randint(1000, 9999)}",
            "scan_tool": random.choice(["OWASP ZAP", "Burp Suite", "Nessus", "Custom Scanner"]),
            "affected_systems": random.sample(["api", "database", "webapp", "mobile"], random.randint(1, 3)),
            "remediation_time": random.uniform(1, 168) if resolved else None
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice([agent for agent in self.oma_agents if "security" in agent or "audit" in agent] + ["security-auditor"]),
            memory_type=MemoryType.FACTUAL,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_performance_memory(self, index: int) -> TestMemoryData:
        """Generate performance-related memory"""
        metric_type = random.choice(["response_time", "throughput", "cpu_usage", "memory_usage", "error_rate"])
        status = random.choice(["optimal", "warning", "critical"])

        content_templates = [
            f"Performance alert: {metric_type.replace('_', ' ')} is {status}",
            f"System monitoring shows {metric_type} at {random.uniform(0.1, 1.0):.2%}, status: {status}",
            f"Performance optimization completed for {metric_type}, improvement: {random.randint(5, 50)}%",
            f"Benchmark test for {metric_type} completed, score: {random.randint(60, 100)}/100"
        ]

        content = random.choice(content_templates)

        metadata = {
            "metric_type": metric_type,
            "status": status,
            "value": random.uniform(0.1, 1.0),
            "threshold": random.uniform(0.5, 0.9),
            "component": random.choice(["api", "database", "cache", "queue", "agent"]),
            "timestamp_range": f"last_{random.randint(1, 60)}_minutes",
            "benchmark_id": f"benchmark_{uuid.uuid4().hex[:8]}"
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice(self.smc_agents),
            memory_type=MemoryType.FACTUAL,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_compliance_memory(self, index: int) -> TestMemoryData:
        """Generate compliance-related memory"""
        regulation = random.choice(["GDPR", "SOC 2", "PCI DSS", "HIPAA", "SOX"])
        audit_type = random.choice(["internal", "external", "continuous"])
        status = random.choice(["compliant", "non_compliant", "in_progress"])

        content_templates = [
            f"{regulation} compliance audit completed, status: {status}",
            f"{audit_type} audit for {regulation} controls: {random.randint(5, 50)} requirements checked",
            f"Compliance policy updated for {regulation}, version {random.randint(1, 5)}.0",
            f"Risk assessment for {regulation} compliance: {random.choice(['low', 'medium', 'high']} risk level"
        ]

        content = random.choice(content_templates)

        metadata = {
            "regulation": regulation,
            "audit_type": audit_type,
            "status": status,
            "auditor": random.choice(["internal_team", "external_auditor", "regulatory_body"]),
            "compliance_score": random.randint(60, 100),
            "findings_count": random.randint(0, 25),
            "remediation_deadline": (datetime.now(timezone.utc) + timedelta(days=random.randint(30, 365))).isoformat()
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice(self.oma_agents),
            memory_type=MemoryType.FACTUAL,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_coordination_memory(self, index: int) -> TestMemoryData:
        """Generate coordination-related memory"""
        coordination_type = random.choice(["task_delegation", "consensus_building", "resource_allocation", "conflict_resolution"])
        participants_count = random.randint(2, 10)
        outcome = random.choice(["success", "partial", "failed"])

        content_templates = [
            f"{coordination_type.replace('_', ' ')} completed with {participants_count} agents, outcome: {outcome}",
            f"Multi-agent coordination session: {participants_count} participants, decision: {random.choice(['approved', 'rejected', 'deferred'])}",
            f"Resource allocation for {coordination_type}: {random.randint(1000, 10000)} units distributed across {participants_count} agents",
            f"Consensus reached for {coordination_type} with {random.randint(60, 95)}% agreement"
        ]

        content = random.choice(content_templates)

        participants = random.sample(self.ats_agents + self.oma_agents + self.smc_agents, participants_count)

        metadata = {
            "coordination_type": coordination_type,
            "participants_count": participants_count,
            "participants": participants,
            "outcome": outcome,
            "decision_maker": random.choice(participants),
            "coordination_time": random.uniform(5, 300),
            "vote_distribution": {agent: random.randint(0, 5) for agent in participants}
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice(self.smc_agents),
            memory_type=MemoryType.PROCEDURAL,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_general_memory(self, index: int) -> TestMemoryData:
        """Generate general-purpose memory"""
        memory_types = list(MemoryType)
        memory_type = random.choice(memory_types)

        content_templates = [
            f"System operation completed successfully at {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
            f"Process optimization task {random.choice(['initiated', 'completed', 'failed'])}",
            f"Data backup completed, {random.randint(100, 10000)} records processed",
            f"Configuration update applied, version {random.randint(1, 100)}",
            f"Routine maintenance completed, {random.randint(1, 50)} checks performed"
        ]

        content = random.choice(content_templates)

        metadata = {
            "category": "general",
            "priority": random.choice(["low", "medium", "high"]),
            "tags": random.sample(self.memory_keywords, random.randint(1, 3)),
            "processing_time": random.uniform(0.1, 60),
            "resource_usage": {
                "cpu": random.uniform(0.1, 0.9),
                "memory": random.uniform(0.1, 0.9),
                "disk": random.uniform(0.1, 0.8)
            }
        }

        return TestMemoryData(
            content=content,
            agent_id=random.choice(self.ats_agents + self.oma_agents + self.smc_agents),
            memory_type=memory_type,
            metadata=metadata,
            embedding=self._generate_embedding(),
            timestamp=datetime.now(timezone.utc)
        )

    def _generate_embedding(self, dimension: int = 1536) -> List[float]:
        """Generate random embedding vector for testing"""
        return [random.uniform(-1, 1) for _ in range(dimension)]

    def generate_test_user(self, category: DataCategory = DataCategory.AUTHENTICATION) -> TestUserData:
        """Generate test user data"""
        usernames = {
            DataCategory.AUTHENTICATION: ["test_user", "admin_user", "analyst_user", "trader_user"],
            DataCategory.TRADING: ["trader_john", "market_analyst", "risk_manager"],
            DataCategory.SECURITY: ["security_admin", "auditor", "penetration_tester"]
        }

        usernames_list = usernames.get(category, ["test_user"])
        username = random.choice(usernames_list) + f"_{int(time.time())}_{random.randint(100, 999)}"

        # Generate secure password
        password = self._generate_secure_password()

        user_data = TestUserData(
            username=username,
            email=f"{username}@example.com",
            password=password,
            role=random.choice(["user", "admin", "analyst", "trader", "auditor"]),
            preferences={
                "theme": random.choice(["light", "dark"]),
                "language": random.choice(["en", "es", "fr", "de"]),
                "notifications": random.choice([True, False]),
                "auto_save": random.choice([True, False])
            },
            profile={
                "first_name": random.choice(["John", "Jane", "Michael", "Sarah", "David", "Emily"]),
                "last_name": random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller"]),
                "department": random.choice(["Engineering", "Security", "Trading", "Operations", "Compliance"]),
                "join_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))).isoformat()
            }
        )

        return user_data

    def _generate_secure_password(self, length: int = 12) -> str:
        """Generate secure password meeting complexity requirements"""
        # Ensure password contains uppercase, lowercase, digits, and special characters
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special)
        ]

        # Fill remaining length
        remaining_length = length - 4
        all_chars = lowercase + uppercase + digits + special
        password.extend(random.choices(all_chars, k=remaining_length))

        # Shuffle password characters
        random.shuffle(password)

        return ''.join(password)

    def generate_test_scenario_data(self, scenario: str, scale: str = "medium") -> Dict[str, Any]:
        """Generate data for specific test scenarios"""

        scenario_data = {}

        if scenario == "trading_workflow":
            scenario_data = self._generate_trading_scenario(scale)
        elif scenario == "security_breach":
            scenario_data = self._generate_security_breach_scenario(scale)
        elif scenario == "code_review_workflow":
            scenario_data = self._generate_code_review_scenario(scale)
        elif scenario == "performance_load":
            scenario_data = self._generate_performance_scenario(scale)
        elif scenario == "compliance_audit":
            scenario_data = self._generate_compliance_scenario(scale)
        else:
            scenario_data = self._generate_general_scenario(scale)

        return scenario_data

    def _generate_trading_scenario(self, scale: str) -> Dict[str, Any]:
        """Generate trading workflow scenario data"""
        scale_factors = {"small": 10, "medium": 100, "large": 1000}
        operation_count = scale_factors.get(scale, 100)

        return {
            "scenario_type": "trading_workflow",
            "scale": scale,
            "operations": operation_count,
            "symbols": random.sample(self.trading_symbols, random.randint(2, 5)),
            "duration_minutes": random.randint(30, 120),
            "algorithms": [
                {
                    "name": "mean_reversion",
                    "parameters": {"lookback": 20, "threshold": 0.02},
                    "success_rate": random.uniform(0.6, 0.9)
                },
                {
                    "name": "momentum",
                    "parameters": {"lookback": 50, "threshold": 0.7},
                    "success_rate": random.uniform(0.7, 0.95)
                }
            ],
            "risk_parameters": {
                "max_position_size": random.randint(100000, 1000000),
                "max_drawdown": random.uniform(0.02, 0.1),
                "stop_loss": random.uniform(0.01, 0.05)
            }
        }

    def _generate_security_breach_scenario(self, scale: str) -> Dict[str, Any]:
        """Generate security breach scenario data"""
        scale_factors = {"small": 5, "medium": 20, "large": 100}
        attack_vectors_count = scale_factors.get(scale, 20)

        return {
            "scenario_type": "security_breach",
            "scale": scale,
            "attack_vectors": [
                {
                    "type": random.choice(self.security_threats),
                    "severity": random.choice(["low", "medium", "high", "critical"]),
                    "success": random.choice([True, False]),
                    "detection_time": random.randint(1, 60),
                    "mitigation_time": random.randint(5, 120)
                }
                for _ in range(attack_vectors_count)
            ],
            "attacker_profile": {
                "type": random.choice(["external", "internal", "partner"]),
                "motivation": random.choice(["financial", "espionage", "vandalism", "activism"]),
                "skill_level": random.choice(["low", "medium", "high", "advanced"])
            },
            "impact_assessment": {
                "data_breach": random.choice([True, False]),
                "service_disruption": random.uniform(0.0, 1.0),
                "financial_loss": random.randint(0, 1000000),
                "reputation_damage": random.choice(["low", "medium", "high"])
            }
        }

    def _generate_code_review_scenario(self, scale: str) -> Dict[str, Any]:
        """Generate code review workflow scenario data"""
        scale_factors = {"small": 5, "medium": 25, "large": 100}
        files_count = scale_factors.get(scale, 25)

        return {
            "scenario_type": "code_review_workflow",
            "scale": scale,
            "files": [
                {
                    "name": f"module_{i}.py",
                    "lines_of_code": random.randint(50, 1000),
                    "complexity": random.choice(["low", "medium", "high"]),
                    "language": random.choice(["python", "javascript", "java", "c++"]),
                    "issues_found": random.randint(0, 20)
                }
                for i in range(files_count)
            ],
            "reviewers": random.sample(self.oma_agents, random.randint(1, 3)),
            "quality_metrics": {
                "code_quality_score": random.uniform(0.6, 0.95),
                "security_score": random.uniform(0.7, 1.0),
                "maintainability_score": random.uniform(0.5, 0.9),
                "test_coverage": random.uniform(0.3, 0.85)
            }
        }

    def _generate_performance_scenario(self, scale: str) -> Dict[str, Any]:
        """Generate performance testing scenario data"""
        scale_factors = {"small": 50, "medium": 500, "large": 5000}
        concurrent_users = scale_factors.get(scale, 500)

        return {
            "scenario_type": "performance_load",
            "scale": scale,
            "concurrent_users": concurrent_users,
            "test_duration_minutes": random.randint(5, 60),
            "ramp_up_time": random.randint(1, 10),
            "endpoints": [
                {
                    "path": "/api/v1/memory",
                    "method": "POST",
                    "payload_size": random.randint(100, 10000),
                    "expected_response_time": random.uniform(0.05, 0.5)
                },
                {
                    "path": "/api/v1/memory/search",
                    "method": "POST",
                    "payload_size": random.randint(50, 5000),
                    "expected_response_time": random.uniform(0.1, 1.0)
                }
            ],
            "thresholds": {
                "max_response_time": random.uniform(0.1, 1.0),
                "max_error_rate": random.uniform(0.01, 0.05),
                "min_throughput": random.randint(100, 1000)
            }
        }

    def _generate_compliance_scenario(self, scale: str) -> Dict[str, Any]:
        """Generate compliance audit scenario data"""
        scale_factors = {"small": 5, "medium": 25, "large": 100}
        controls_count = scale_factors.get(scale, 25)

        return {
            "scenario_type": "compliance_audit",
            "scale": scale,
            "framework": random.choice(["GDPR", "SOC 2", "PCI DSS", "HIPAA"]),
            "controls": [
                {
                    "control_id": f"CTL-{random.randint(1000, 9999)}",
                    "description": f"Control {i} for compliance",
                    "category": random.choice(["technical", "administrative", "physical"]),
                    "status": random.choice(["compliant", "non_compliant", "partial"]),
                    "evidence": random.choice(["available", "missing", "partial"])
                }
                for i in range(controls_count)
            ],
            "audit_trail": {
                "auditor": random.choice(["internal", "external", "regulatory"]),
                "audit_date": datetime.now(timezone.utc).isoformat(),
                "scope": random.choice(["full", "partial", "focused"])
            }
        }

    def _generate_general_scenario(self, scale: str) -> Dict[str, Any]:
        """Generate general test scenario data"""
        return {
            "scenario_type": "general_testing",
            "scale": scale,
            "test_types": random.sample(
                ["unit", "integration", "system", "performance", "security"],
                random.randint(1, 3)
            ),
            "duration_minutes": random.randint(5, 30),
            "priority": random.choice(["low", "medium", "high", "critical"]),
            "environment": random.choice(["development", "staging", "production"])
        }

    def export_test_data(self, data: List[TestMemoryData], output_file: str, format: str = "json"):
        """Export test data to file"""
        export_data = []

        for memory_data in data:
            export_item = {
                "content": memory_data.content,
                "agent_id": memory_data.agent_id,
                "memory_type": memory_data.memory_type.value,
                "metadata": memory_data.metadata,
                "embedding": memory_data.embedding,
                "timestamp": memory_data.timestamp.isoformat() if memory_data.timestamp else None
            }
            export_data.append(export_item)

        if format.lower() == "json":
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def load_test_data(self, input_file: str) -> List[TestMemoryData]:
        """Load test data from file"""
        with open(input_file, 'r') as f:
            export_data = json.load(f)

        memories = []
        for item in export_data:
            memory = TestMemoryData(
                content=item["content"],
                agent_id=item["agent_id"],
                memory_type=MemoryType(item["memory_type"]),
                metadata=item["metadata"],
                embedding=item.get("embedding"),
                timestamp=datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else None
            )
            memories.append(memory)

        return memories

    def generate_batch_data(self, categories: List[DataCategory], count_per_category: int = 100) -> Dict[DataCategory, List[TestMemoryData]]:
        """Generate batch test data for multiple categories"""
        batch_data = {}

        for category in categories:
            batch_data[category] = self.generate_memory_data(category, count_per_category)

        return batch_data


# Utility functions for test data management
def create_test_dataset(output_dir: str, categories: List[str], count_per_category: int = 100):
    """Create comprehensive test dataset"""
    generator = TestDataGenerator()

    # Convert string categories to enum
    data_categories = [DataCategory(cat.lower()) for cat in categories]

    batch_data = generator.generate_batch_data(data_categories, count_per_category)

    # Export each category to separate file
    for category, memories in batch_data.items():
        output_file = f"{output_dir}/{category.value}_test_data.json"
        generator.export_test_data(memories, output_file)
        print(f"Created {len(memories)} test records for {category.value} in {output_file}")

def load_test_dataset(input_dir: str) -> Dict[str, List[TestMemoryData]]:
    """Load test dataset from directory"""
    generator = TestDataGenerator()
    dataset = {}

    import os
    for filename in os.listdir(input_dir):
        if filename.endswith("_test_data.json"):
            category_name = filename.replace("_test_data.json", "")
            try:
                category = DataCategory(category_name)
                input_file = os.path.join(input_dir, filename)
                dataset[category.value] = generator.load_test_data(input_file)
                print(f"Loaded {len(dataset[category.value])} test records for {category.value}")
            except ValueError:
                print(f"Skipping {filename} - unknown category")

    return dataset


if __name__ == "__main__":
    # Example usage
    generator = TestDataGenerator(seed=42)

    # Generate test data
    trading_memories = generator.generate_memory_data(DataCategory.TRADING, 50)
    security_memories = generator.generate_memory_data(DataCategory.SECURITY, 25)

    # Export test data
    generator.export_test_data(trading_memories, "trading_test_data.json")
    generator.export_test_data(security_memories, "security_test_data.json")

    # Generate scenario data
    trading_scenario = generator.generate_test_scenario_data("trading_workflow", "medium")
    print("Generated trading scenario:", json.dumps(trading_scenario, indent=2))

    print("Test data generation completed!")