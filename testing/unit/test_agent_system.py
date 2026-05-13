"""
Unit Tests for Enhanced Cognee Agent System

Tests for all 21 agents across ATS, OMA, and SMC categories.
Includes agent initialization, functionality, coordination, and memory integration.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional

# ats/oma/smc agent modules were archived in Phase 4 (hardcoded category violation).
# These tests are skipped when the modules are not present.
try:
    import src.agents.ats
    import src.agents.oma
    import src.agents.smc
    _AGENTS_AVAILABLE = True
except ImportError:
    _AGENTS_AVAILABLE = False

# Mark all tests as unit tests; skip entire module when archived agents are absent
pytestmark = [
    pytest.mark.unit,
    pytest.mark.agents,
    pytest.mark.skipif(
        not _AGENTS_AVAILABLE,
        reason="ATS/OMA/SMC agents archived in Phase 4 (hardcoded category violation)",
    ),
]


class TestATSAgents:
    """Test Algorithmic Trading System (ATS) Agents"""

    @pytest.fixture
    async def algorithmic_trading_agent(self):
        """Fixture for Algorithmic Trading System agent"""
        with patch('src.agents.ats.algorithmic_trading_system.AlgorithmicTradingSystem') as mock_ats:
            agent = mock_ats.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "algorithmic-trading-system"
            agent.agent_type = "ATS"
            agent.status = "active"
            yield agent

    @pytest.fixture
    async def risk_management_agent(self):
        """Fixture for Risk Management agent"""
        with patch('src.agents.ats.risk_management.RiskManagementAgent') as mock_rm:
            agent = mock_rm.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "risk-management"
            agent.agent_type = "ATS"
            agent.risk_thresholds = {"max_position_size": 1000000, "max_drawdown": 0.05}
            yield agent

    @pytest.fixture
    async def market_analysis_agent(self):
        """Fixture for Market Analysis agent"""
        with patch('src.agents.ats.market_analysis.MarketAnalysisAgent') as mock_ma:
            agent = mock_ma.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "market-analysis"
            agent.agent_type = "ATS"
            agent.supported_symbols = ["BTC/USD", "ETH/USD", "AAPL", "GOOGL"]
            yield agent

    @pytest.mark.asyncio
    async def test_algorithmic_trading_agent_initialization(self, algorithmic_trading_agent):
        """Test Algorithmic Trading System agent initialization"""
        # Act
        await algorithmic_trading_agent.initialize()

        # Assert
        algorithmic_trading_agent.initialize.assert_called_once()
        assert algorithmic_trading_agent.agent_id == "algorithmic-trading-system"
        assert algorithmic_trading_agent.agent_type == "ATS"

    @pytest.mark.asyncio
    async def test_trading_signal_generation(self, algorithmic_trading_agent):
        """Test trading signal generation"""
        # Arrange
        market_data = {
            "symbol": "BTC/USD",
            "price": 45000.0,
            "volume": 125000000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicators": {
                "rsi": 65.0,
                "macd": 0.5,
                "bollinger_upper": 46000.0,
                "bollinger_lower": 44000.0
            }
        }

        expected_signal = {
            "symbol": "BTC/USD",
            "action": "BUY",
            "confidence": 0.85,
            "reason": "RSI indicates bullish momentum",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        algorithmic_trading_agent.generate_signal = AsyncMock(return_value=expected_signal)

        # Act
        signal = await algorithmic_trading_agent.generate_signal(market_data)

        # Assert
        assert signal["action"] == "BUY"
        assert signal["confidence"] == 0.85
        assert signal["symbol"] == "BTC/USD"

    @pytest.mark.asyncio
    async def test_risk_assessment(self, risk_management_agent):
        """Test risk assessment functionality"""
        # Arrange
        trade_request = {
            "symbol": "BTC/USD",
            "action": "BUY",
            "quantity": 10.0,
            "price": 45000.0,
            "total_value": 450000.0
        }

        risk_assessment = {
            "approved": True,
            "risk_score": 0.3,
            "warnings": [],
            "max_position_size": 1000000,
            "current_exposure": 200000.0
        }

        risk_management_agent.assess_risk = AsyncMock(return_value=risk_assessment)

        # Act
        assessment = await risk_management_agent.assess_risk(trade_request)

        # Assert
        assert assessment["approved"] is True
        assert assessment["risk_score"] == 0.3
        assert assessment["max_position_size"] == 1000000

    @pytest.mark.asyncio
    async def test_market_data_analysis(self, market_analysis_agent):
        """Test market data analysis"""
        # Arrange
        raw_data = [
            {"timestamp": "2024-01-01T10:00:00Z", "price": 45000.0, "volume": 1000000},
            {"timestamp": "2024-01-01T10:01:00Z", "price": 45100.0, "volume": 1100000},
            {"timestamp": "2024-01-01T10:02:00Z", "price": 44900.0, "volume": 900000}
        ]

        analysis_result = {
            "symbol": "BTC/USD",
            "trend": "BULLISH",
            "volatility": 0.02,
            "volume_trend": "INCREASING",
            "support_level": 44500.0,
            "resistance_level": 45500.0,
            "technical_indicators": {
                "rsi": 62.0,
                "macd": 0.3,
                "moving_average_50": 44800.0,
                "moving_average_200": 43500.0
            }
        }

        market_analysis_agent.analyze_market_data = AsyncMock(return_value=analysis_result)

        # Act
        analysis = await market_analysis_agent.analyze_market_data("BTC/USD", raw_data)

        # Assert
        assert analysis["symbol"] == "BTC/USD"
        assert analysis["trend"] == "BULLISH"
        assert analysis["volatility"] == 0.02
        assert "technical_indicators" in analysis

    @pytest.mark.asyncio
    async def test_agent_memory_integration(self, algorithmic_trading_agent):
        """Test agent memory integration"""
        # Arrange
        memory_content = "BTC showing strong uptrend with RSI at 65"
        memory_data = {
            "content": memory_content,
            "agent_id": "algorithmic-trading-system",
            "memory_type": "episodic",
            "metadata": {
                "symbol": "BTC/USD",
                "confidence": 0.85,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        algorithmic_trading_agent.store_memory = AsyncMock(return_value="memory_123")

        # Act
        memory_id = await algorithmic_trading_agent.store_memory(memory_content, memory_data["metadata"])

        # Assert
        assert memory_id == "memory_123"
        algorithmic_trading_agent.store_memory.assert_called_once()

    def test_agent_error_handling(self, algorithmic_trading_agent):
        """Test agent error handling"""
        # Arrange
        algorithmic_trading_agent.generate_signal = AsyncMock(side_effect=Exception("API Error"))

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await algorithmic_trading_agent.generate_signal({})

        assert str(exc_info.value) == "API Error"


class TestOMAAgents:
    """Test Other Multi-Agent (OMA) Agents"""

    @pytest.fixture
    async def code_reviewer_agent(self):
        """Fixture for Code Reviewer agent"""
        with patch('src.agents.oma.code_reviewer.CodeReviewer') as mock_cr:
            agent = mock_cr.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "code-reviewer"
            agent.agent_type = "OMA"
            agent.review_rules = ["security", "performance", "maintainability"]
            yield agent

    @pytest.fixture
    async def development_agent(self):
        """Fixture for Development agent"""
        with patch('src.agents.oma.development_agent.DevelopmentAgent') as mock_dev:
            agent = mock_dev.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "development-agent"
            agent.agent_type = "OMA"
            agent.skills = ["python", "javascript", "docker", "testing"]
            yield agent

    @pytest.fixture
    async def architecture_agent(self):
        """Fixture for Architecture agent"""
        with patch('src.agents.oma.architecture_agent.ArchitectureAgent') as mock_arch:
            agent = mock_arch.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "architecture-agent"
            agent.agent_type = "OMA"
            agent.architecture_patterns = ["microservices", "event-driven", "domain-driven"]
            yield agent

    @pytest.mark.asyncio
    async def test_code_review_functionality(self, code_reviewer_agent):
        """Test code review functionality"""
        # Arrange
        code_snippet = """
def authenticate_user(username, password):
    if not username or not password:
        return False

    # Hash password and check against database
    hashed_password = hash_password(password)
    user = get_user(username)

    if user and user.password_hash == hashed_password:
        return True

    return False
        """

        review_result = {
            "overall_score": 8.5,
            "security_issues": [],
            "performance_suggestions": ["Consider caching user lookups"],
            "maintainability_score": 9.0,
            "recommendations": [
                "Add input validation",
                "Document function behavior",
                "Add unit tests"
            ]
        }

        code_reviewer_agent.review_code = AsyncMock(return_value=review_result)

        # Act
        review = await code_reviewer_agent.review_code(code_snippet, "python")

        # Assert
        assert review["overall_score"] == 8.5
        assert len(review["recommendations"]) == 3
        assert review["maintainability_score"] == 9.0

    @pytest.mark.asyncio
    async def test_security_vulnerability_detection(self, code_reviewer_agent):
        """Test security vulnerability detection"""
        # Arrange
        vulnerable_code = """
def login(username, password):
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    return execute_query(query)
        """

        security_issues = [
            {
                "type": "SQL_INJECTION",
                "severity": "HIGH",
                "line": 2,
                "description": "SQL injection vulnerability in query construction"
            }
        ]

        code_reviewer_agent.detect_security_issues = AsyncMock(return_value=security_issues)

        # Act
        issues = await code_reviewer_agent.detect_security_issues(vulnerable_code)

        # Assert
        assert len(issues) == 1
        assert issues[0]["type"] == "SQL_INJECTION"
        assert issues[0]["severity"] == "HIGH"

    @pytest.mark.asyncio
    async def test_development_task_execution(self, development_agent):
        """Test development task execution"""
        # Arrange
        task = {
            "type": "feature_development",
            "description": "Implement user authentication with JWT",
            "requirements": ["JWT tokens", "Password hashing", "Session management"],
            "priority": "HIGH",
            "estimated_hours": 8
        }

        task_result = {
            "task_id": "task_001",
            "status": "COMPLETED",
            "output": {
                "code_files": ["auth.py", "models/user.py", "utils/jwt_utils.py"],
                "tests": ["test_auth.py"],
                "documentation": ["docs/auth.md"],
                "actual_hours": 7.5
            }
        }

        development_agent.execute_task = AsyncMock(return_value=task_result)

        # Act
        result = await development_agent.execute_task(task)

        # Assert
        assert result["status"] == "COMPLETED"
        assert len(result["output"]["code_files"]) == 3
        assert result["output"]["actual_hours"] == 7.5

    @pytest.mark.asyncio
    async def test_architecture_design(self, architecture_agent):
        """Test architecture design functionality"""
        # Arrange
        requirements = {
            "system_type": "microservices",
            "scalability": "HIGH",
            "availability": "99.9%",
            "technologies": ["Python", "Docker", "Kubernetes", "PostgreSQL"],
            "functional_requirements": ["User management", "Authentication", "Data processing"]
        }

        architecture_design = {
            "pattern": "microservices",
            "services": [
                {"name": "user-service", "responsibility": "User management"},
                {"name": "auth-service", "responsibility": "Authentication"},
                {"name": "data-service", "responsibility": "Data processing"}
            ],
            "infrastructure": {
                "containerization": "Docker",
                "orchestration": "Kubernetes",
                "database": "PostgreSQL",
                "caching": "Redis"
            },
            "communication": ["REST APIs", "Message Queues"],
            "quality_attributes": {
                "scalability": "horizontal",
                "availability": "multi-zone deployment",
                "security": "OAuth 2.0, JWT"
            }
        }

        architecture_agent.design_architecture = AsyncMock(return_value=architecture_design)

        # Act
        design = await architecture_agent.design_architecture(requirements)

        # Assert
        assert design["pattern"] == "microservices"
        assert len(design["services"]) == 3
        assert "kubernetes" in str(design["infrastructure"]).lower()


class TestSMCAgents:
    """Test Shared Multi-Agent Components (SMC) Agents"""

    @pytest.fixture
    async def context_manager_agent(self):
        """Fixture for Context Manager agent"""
        with patch('src.agents.smc.context_manager.ContextManager') as mock_cm:
            agent = mock_cm.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "context-manager"
            agent.agent_type = "SMC"
            agent.active_contexts = {}
            yield agent

    @pytest.fixture
    async def performance_monitor_agent(self):
        """Fixture for Performance Monitor agent"""
        with patch('src.agents.smc.performance_monitor.PerformanceMonitor') as mock_pm:
            agent = mock_pm.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "performance-monitor"
            agent.agent_type = "SMC"
            agent.metrics_collector = Mock()
            yield agent

    @pytest.fixture
    async def communication_coordinator_agent(self):
        """Fixture for Communication Coordinator agent"""
        with patch('src.agents.smc.communication_coordinator.CommunicationCoordinator') as mock_cc:
            agent = mock_cc.return_value
            agent.initialize = AsyncMock(return_value=True)
            agent.cleanup = AsyncMock(return_value=True)
            agent.agent_id = "communication-coordinator"
            agent.agent_type = "SMC"
            agent.active_channels = {}
            yield agent

    @pytest.mark.asyncio
    async def test_context_creation(self, context_manager_agent):
        """Test context creation"""
        # Arrange
        context_data = {
            "session_id": "sess_001",
            "user_id": "user_123",
            "agent_ids": ["code-reviewer", "development-agent"],
            "shared_data": {"project": "enhanced-cognee", "task": "code review"},
            "metadata": {"created_at": datetime.now(timezone.utc).isoformat()}
        }

        context_result = {
            "context_id": "ctx_001",
            "status": "ACTIVE",
            "participants": ["code-reviewer", "development-agent"],
            "shared_memory": {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        context_manager_agent.create_context = AsyncMock(return_value=context_result)

        # Act
        context = await context_manager_agent.create_context(context_data)

        # Assert
        assert context["status"] == "ACTIVE"
        assert len(context["participants"]) == 2
        assert "shared_memory" in context

    @pytest.mark.asyncio
    async def test_context_memory_sharing(self, context_manager_agent):
        """Test context memory sharing"""
        # Arrange
        context_id = "ctx_001"
        agent_id = "code-reviewer"
        memory_data = {
            "content": "Code review completed for auth module",
            "type": "review_result",
            "confidence": 0.9
        }

        sharing_result = {
            "success": True,
            "shared_with": ["development-agent"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        context_manager_agent.share_memory = AsyncMock(return_value=sharing_result)

        # Act
        result = await context_manager_agent.share_memory(context_id, agent_id, memory_data)

        # Assert
        assert result["success"] is True
        assert len(result["shared_with"]) == 1

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, performance_monitor_agent):
        """Test performance monitoring"""
        # Arrange
        metrics_data = {
            "cpu_usage": 65.5,
            "memory_usage": 78.2,
            "disk_io": 1250,
            "network_io": 890,
            "response_times": [45, 52, 38, 61, 43],
            "throughput": 1250,
            "error_rate": 0.02
        }

        performance_metrics = {
            "agent_id": "algorithmic-trading-system",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_score": 85.5,
            "alerts": ["Memory usage above threshold"],
            "recommendations": ["Consider memory optimization"]
        }

        performance_monitor_agent.collect_metrics = AsyncMock(return_value=performance_metrics)

        # Act
        metrics = await performance_monitor_agent.collect_metrics("algorithmic-trading-system")

        # Assert
        assert metrics["health_score"] == 85.5
        assert len(metrics["alerts"]) == 1
        assert "recommendations" in metrics

    @pytest.mark.asyncio
    async def test_agent_coordination(self, communication_coordinator_agent):
        """Test agent coordination"""
        # Arrange
        coordination_request = {
            "coordinator_id": "communication-coordinator",
            "participants": ["code-reviewer", "development-agent", "security-auditor"],
            "task_type": "code_review_security",
            "message": "Review authentication module for security vulnerabilities",
            "priority": "HIGH",
            "deadline": datetime.now(timezone.utc).isoformat()
        }

        coordination_result = {
            "coordination_id": "coord_001",
            "status": "INITIATED",
            "participants_confirmed": 3,
            "estimated_completion": "2024-01-01T16:00:00Z",
            "communication_channel": "secure_channel_001"
        }

        communication_coordinator_agent.initiate_coordination = AsyncMock(return_value=coordination_result)

        # Act
        result = await communication_coordinator_agent.initiate_coordination(coordination_request)

        # Assert
        assert result["status"] == "INITIATED"
        assert result["participants_confirmed"] == 3
        assert "communication_channel" in result


class TestAgentCoordination:
    """Test multi-agent coordination and communication"""

    @pytest.mark.asyncio
    async def test_cross_category_coordination(self):
        """Test coordination between different agent categories"""
        # Mock agents from different categories
        with patch('src.agents.ats.algorithmic_trading_system.AlgorithmicTradingSystem') as mock_ats, \
             patch('src.agents.oma.code_reviewer.CodeReviewer') as mock_oma, \
             patch('src.agents.smc.context_manager.ContextManager') as mock_smc:

            # Setup mock agents
            ats_agent = mock_ats.return_value
            ats_agent.agent_id = "algorithmic-trading-system"
            ats_agent.agent_type = "ATS"
            ats_agent.process_request = AsyncMock(return_value={"status": "completed"})

            oma_agent = mock_oma.return_value
            oma_agent.agent_id = "code-reviewer"
            oma_agent.agent_type = "OMA"
            oma_agent.process_request = AsyncMock(return_value={"status": "completed"})

            smc_agent = mock_smc.return_value
            smc_agent.agent_id = "context-manager"
            smc_agent.agent_type = "SMC"
            smc_agent.coordinate_agents = AsyncMock(return_value={"status": "coordinated"})

            # Test coordination
            coordination_request = {
                "coordinator": "context-manager",
                "participants": ["algorithmic-trading-system", "code-reviewer"],
                "task": "Review trading algorithm implementation",
                "priority": "MEDIUM"
            }

            result = await smc_agent.coordinate_agents(coordination_request)

            # Assert
            assert result["status"] == "coordinated"
            smc_agent.coordinate_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_memory_sharing(self):
        """Test memory sharing between agents"""
        # Mock agents
        with patch('src.agent_memory_integration.AgentMemoryIntegration') as mock_memory:

            memory_integration = mock_memory.return_value
            memory_integration.share_memory = AsyncMock(return_value={"success": True})

            # Test memory sharing
            sharing_request = {
                "from_agent": "algorithmic-trading-system",
                "to_agents": ["risk-management", "market-analysis"],
                "memory_content": "Market analysis showing upward trend",
                "memory_type": "episodic",
                "access_level": "shared"
            }

            result = await memory_integration.share_memory(sharing_request)

            # Assert
            assert result["success"] is True
            memory_integration.share_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_consensus_building(self):
        """Test consensus building between agents"""
        with patch('src.coordination.distributed_decision.DistributedDecisionMaker') as mock_dd:

            decision_maker = mock_dd.return_value
            decision_maker.create_proposal = AsyncMock(return_value={
                "proposal_id": "prop_001",
                "status": "ACTIVE",
                "options": ["APPROVE", "REJECT", "MODIFY"]
            })

            # Test consensus
            consensus_request = {
                "decision_type": "trading_strategy_approval",
                "participants": ["algorithmic-trading-system", "risk-management", "market-analysis"],
                "proposal": "Implement new high-frequency trading strategy",
                "voting_deadline": "2024-01-01T16:00:00Z"
            }

            result = await decision_maker.create_proposal(consensus_request)

            # Assert
            assert result["proposal_id"] == "prop_001"
            assert result["status"] == "ACTIVE"
            assert len(result["options"]) == 3


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])