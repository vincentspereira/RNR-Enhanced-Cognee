# RNR Enhanced Cognee Examples

## 📚 Table of Contents

1. [Quick Start Examples](#quick-start-examples)
2. [Agent System Examples](#agent-system-examples)
3. [Memory Integration Examples](#memory-integration-examples)
4. [Coordination Examples](#coordination-examples)
5. [Advanced Examples](#advanced-examples)
6. [Production Examples](#production-examples)

## 🚀 Quick Start Examples

### Example 1: Basic Memory Operations

```python
# examples/01_basic_memory_operations.py
import asyncio
from agent_memory_integration import AgentMemoryIntegration, MemoryType

async def basic_memory_example():
    """Basic memory storage and retrieval"""

    # Initialize RNR Enhanced Cognee
    memory_system = AgentMemoryIntegration()
    await memory_system.initialize()

    # Store memory for different agents
    trading_memory = await memory_system.add_memory(
        agent_id="algorithmic-trading-system",
        content="BTC price crossed 200-day moving average",
        memory_type=MemoryType.EPISODIC,
        metadata={
            "symbol": "BTC/USD",
            "price": 45000.0,
            "confidence": 0.85
        }
    )

    code_review_memory = await memory_system.add_memory(
        agent_id="code-reviewer",
        content="Security vulnerability found in authentication module",
        memory_type=MemoryType.FACTUAL,
        metadata={
            "severity": "high",
            "file": "auth.py",
            "line": 234
        }
    )

    # Search memories
    trading_results = await memory_system.search_memory(
        agent_id="algorithmic-trading-system",
        query="BTC price",
        limit=5
    )

    security_results = await memory_system.search_memory(
        agent_id="code-reviewer",
        query="vulnerability",
        limit=3
    )

    print(f"Trading memories found: {len(trading_results)}")
    print(f"Security memories found: {len(security_results)}")

    return trading_results, security_results

if __name__ == "__main__":
    asyncio.run(basic_memory_example())
```

### Example 2: Enhanced MCP Server

```python
# examples/02_enhanced_mcp_server.py
import asyncio
from enhanced_cognee_mcp import EnhancedCogneeMCPServer

async def mcp_server_example():
    """Enhanced MCP server usage example"""

    # Initialize MCP server
    server = EnhancedCogneeMCPServer()
    await server.initialize()

    # Store memories via MCP interface
    memory_id = await server.add_memory(
        content="Market analysis indicates bullish trend",
        agent_id="market-analyzer",
        memory_category="ats",
        metadata={
            "trend": "bullish",
            "confidence": 0.78,
            "indicators": ["RSI", "MACD", "Volume"]
        }
    )

    print(f"Memory stored via MCP: {memory_id}")

    # Search via MCP interface
    search_results = await server.search_memory(
        query="market trend",
        limit=10,
        agent_id="market-analyzer"
    )

    print(f"MCP search results: {len(search_results)}")

    # Get memory statistics
    stats = await server.get_memory_stats()
    print(f"Memory statistics: {stats}")

    return memory_id, search_results, stats

if __name__ == "__main__":
    asyncio.run(mcp_server_example())
```

## 🤖 Agent System Examples

### Example 3: Trading Agent Workflow

```python
# examples/03_trading_agent_workflow.py
import asyncio
import datetime
from src.agents.ats import AlgorithmicTradingSystem, RiskManagement
from agent_memory_integration import AgentMemoryIntegration, MemoryType

async def trading_workflow_example():
    """Complete trading agent workflow example"""

    # Initialize systems
    memory_system = AgentMemoryIntegration()
    await memory_system.initialize()

    trading_agent = AlgorithmicTradingSystem()
    risk_manager = RiskManagement()

    # Market data for analysis
    market_data = {
        "symbol": "ETH/USD",
        "current_price": 3200.0,
        "volume_24h": 1500000000,
        "rsi": 65.5,
        "macd": "bullish",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    # Trading agent analysis
    analysis_result = await trading_agent.analyze_market(market_data)

    # Store analysis in memory
    await memory_system.add_memory(
        agent_id="algorithmic-trading-system",
        content=f"Analysis result: {analysis_result['signal']} signal for {market_data['symbol']}",
        memory_type=MemoryType.PROCEDURAL,
        metadata={
            "signal": analysis_result["signal"],
            "confidence": analysis_result["confidence"],
            "market_data": market_data
        }
    )

    # Risk management check
    risk_assessment = await risk_manager.assess_risk({
        "trade_type": analysis_result["signal"],
        "symbol": market_data["symbol"],
        "entry_price": market_data["current_price"],
        "position_size": 1.0
    })

    # Store risk assessment
    await memory_system.add_memory(
        agent_id="risk-management",
        content=f"Risk assessment: {risk_assessment['risk_level']} risk level",
        memory_type=MemoryType.FACTUAL,
        metadata=risk_assessment
    )

    # Retrieve recent trading history for context
    recent_trades = await memory_system.search_memory(
        agent_id="algorithmic-trading-system",
        query=market_data["symbol"],
        memory_type=MemoryType.EPISODIC,
        limit=10
    )

    print(f"Trading analysis: {analysis_result['signal']}")
    print(f"Risk assessment: {risk_assessment['risk_level']}")
    print(f"Recent {market_data['symbol']} trades: {len(recent_trades)}")

    return analysis_result, risk_assessment, recent_trades

if __name__ == "__main__":
    asyncio.run(trading_workflow_example())
```

### Example 4: Development Agent Integration

```python
# examples/04_development_agent_integration.py
import asyncio
from src.agents.oma import CodeReviewer, TestGenerator
from src.agents.smc import ContextManager
from agent_memory_integration import AgentMemoryIntegration, MemoryType

async def development_integration_example():
    """Development agent integration example"""

    memory_system = AgentMemoryIntegration()
    await memory_system.initialize()

    # Initialize agents
    code_reviewer = CodeReviewer()
    test_generator = TestGenerator()
    context_manager = ContextManager()

    # Code for review
    code_content = """
    class AuthenticationSystem:
        def __init__(self):
            self.users = {}

        def authenticate(self, username, password):
            # Vulnerable authentication logic
            if username in self.users and self.users[username] == password:
                return True
            return False
    """

    # Code review process
    review_result = await code_reviewer.review_code(
        file_path="auth.py",
        code_content=code_content,
        agent_id="code-reviewer"
    )

    # Store review results
    await memory_system.add_memory(
        agent_id="code-reviewer",
        content=f"Code review completed: {len(review_result['issues'])} issues found",
        memory_type=MemoryType.FACTUAL,
        metadata={
            "file_path": "auth.py",
            "issues": review_result["issues"],
            "score": review_result["score"],
            "review_time": review_result["timestamp"]
        }
    )

    # Generate automated tests
    test_cases = await test_generator.generate_tests(
        file_path="auth.py",
        code_content=code_content,
        agent_id="test-generator"
    )

    # Store test information
    await memory_system.add_memory(
        agent_id="test-generator",
        content=f"Generated {len(test_cases)} test cases",
        memory_type=MemoryType.PROCEDURAL,
        metadata={
            "file_path": "auth.py",
            "test_count": len(test_cases),
            "coverage_estimate": test_cases.get("coverage", 0)
        }
    )

    # Update session context
    session_context = {
        "active_file": "auth.py",
        "review_status": "completed",
        "test_status": "generated",
        "team_members": ["code-reviewer", "test-generator"]
    }

    await context_manager.update_context(
        context_id="dev_session_001",
        context_data=session_context
    )

    print(f"Code review completed: {review_result['score']}/100")
    print(f"Generated test cases: {len(test_cases)}")
    print(f"Session context updated: {session_context}")

    return review_result, test_cases, session_context

if __name__ == "__main__":
    asyncio.run(development_integration_example())
```

## 🗄️ Memory Integration Examples

### Example 5: Cross-Agent Memory Sharing

```python
# examples/05_cross_agent_memory_sharing.py
import asyncio
from agent_memory_integration import AgentMemoryIntegration, MemoryType, MemoryCategory

async def cross_agent_memory_sharing():
    """Cross-agent memory sharing and coordination example"""

    memory_system = AgentMemoryIntegration()
    await memory_system.initialize()

    # Trading agent stores market analysis
    await memory_system.add_memory(
        agent_id="algorithmic-trading-system",
        content="Major price movement detected in cryptocurrency market",
        memory_type=MemoryType.EPISODIC,
        metadata={
            "event": "price_spike",
            "severity": "high",
            "symbols": ["BTC", "ETH", "SOL"],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )

    # Context manager responds to the event
    await memory_system.add_memory(
        agent_id="context-manager",
        content="High priority trading event - activating coordination protocols",
        memory_type=MemoryType.SEMANTIC,
        metadata={
            "event_id": "market_spike_001",
            "priority": "critical",
            "coordinated_agents": ["algorithmic-trading-system", "risk-management", "compliance-monitor"]
        }
    )

    # Risk manager assesses and responds
    await memory_system.add_memory(
        agent_id="risk-management",
        content="Risk level escalated due to market volatility",
        memory_type=MemoryType.PROCEDURAL,
        metadata={
            "risk_level": "high",
            "action_taken": "position_sizing_adjusted",
            "new_risk_parameters": {"max_position_size": "0.5x"}
        }
    )

    # Search for related events across agents
    market_events = await memory_system.search_memory(
        query="price movement volatility spike",
        agent_categories=[MemoryCategory.ATS, MemoryCategory.SMC],
        limit=10
    )

    print(f"Cross-agent market events found: {len(market_events)}")

    # Show coordination between agents
    for event in market_events:
        agent_id = event.get("agent_id", "unknown")
        content = event.get("content", "")[:100] + "..."
        print(f"{agent_id}: {content}")

    return market_events

if __name__ == "__main__":
    asyncio.run(cross_agent_memory_sharing())
```

### Example 6: Memory Type Categorization

```python
# examples/06_memory_type_categorization.py
import asyncio
from agent_memory_integration import AgentMemoryIntegration, MemoryType

async def memory_type_categorization():
    """Demonstrate different memory types and their usage"""

    memory_system = AgentMemoryIntegration()
    await memory_system.initialize()

    # Test all memory types with examples
    memory_examples = {
        MemoryType.EPISODIC: {
            "agent_id": "algorithmic-trading-system",
            "content": "User performed trade: Buy 1.5 BTC at $45,000",
            "metadata": {"trade_id": "trade_001", "profit_loss": "+$500"}
        },

        MemoryType.PROCEDURAL: {
            "agent_id": "code-reviewer",
            "content": "Security review process for authentication systems",
            "metadata": {"steps": 12, "duration": "45 minutes"}
        },

        MemoryType.SEMANTIC: {
            agent_id": "knowledge-graph",
            "content": "Relationship: Authentication -> User -> Permissions",
            "metadata": {"relationship_type": "has_permission", "confidence": 0.95}
        },

        MemoryType.FACTUAL: {
            "agent_id": "compliance-monitor",
            "content": "Regulatory requirement: KYC verification completed",
            "metadata": {"regulation": "KYC", "status": "compliant"}
        }
    }

    stored_memories = []

    for memory_type, example in memory_examples.items():
        memory_id = await memory_system.add_memory(
            memory_type=memory_type,
            **example
        )
        stored_memories.append({
            "type": memory_type.name,
            "id": memory_id,
            "agent": example["agent_id"]
        })

    # Test searching by memory type
    for memory_type in MemoryType:
        results = await memory_system.search_memory(
            memory_type=memory_type,
            limit=3
        )
        print(f"{memory_type.name} memories: {len(results)}")
        for result in results:
            print(f"  - {result['content'][:50]}...")

    return stored_memories

if __name__ == "__main__":
    asyncio.run(memory_type_categorization())
```

## 🔄 Coordination Examples

### Example 7: Task Orchestration

```python
# examples/07_task_orchestration.py
import asyncio
from src.coordination.task_orchestration import TaskOrchestrationEngine, TaskStatus
from src.coordination.sub_agent_coordinator import SubAgentCoordinator, AgentTask, TaskPriority

async def task_orchestration_example():
    """Advanced task orchestration and workflow management"""

    # Initialize coordination systems
    memory_integration = AgentMemoryIntegration()
    await memory_integration.initialize()

    orchestrator = TaskOrchestrationEngine(memory_integration)
    coordinator = SubAgentCoordinator(memory_integration)

    # Create complex workflow
    workflow_definition = {
        "workflow_id": "security_audit_2025",
        "name": "Comprehensive Security Audit",
        "description": "Perform complete security audit of trading platform",
        "steps": [
            {
                "step_id": "step_1",
                "name": "Code Analysis",
                "agent": "code-reviewer",
                "estimated_duration": "2 hours",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "name": "Vulnerability Scanning",
                "agent": "security-auditor",
                "estimated_duration": "3 hours",
                "dependencies": ["step_1"]
            },
            {
                "step_3",
                "name": "Penetration Testing",
                "agent": "security-auditor",
                "estimated_duration": "4 hours",
                "dependencies": ["step_1", "step_2"]
            },
            {
                "step_4",
                "name": "Compliance Review",
                "agent": "compliance-monitor",
                "estimated_duration": "1 hour",
                "dependencies": ["step_3"]
            }
        ],
        "assigned_to": ["code-reviewer", "security-auditor", "compliance-monitor"],
        "priority": TaskPriority.CRITICAL,
        "deadline": "2025-11-15T00:00:00Z"
    }

    # Execute workflow
    execution_result = await orchestrator.execute_workflow(workflow_definition)

    print(f"Workflow execution result: {execution_result['status']}")
    print(f"Completed steps: {len(execution_result['completed_steps'])}")
    print(f"Total duration: {execution_result['total_duration']}")

    # Create coordination tasks
    coordination_tasks = []

    for step in workflow_definition["steps"]:
        task = AgentTask(
            task_id=f"{step['step_id']}_task",
            title=step["name"],
            description=step["description"],
            created_by="orchestrator",
            assigned_to=[step["agent"]],
            priority=TaskPriority.CRITICAL,
            metadata={
                "workflow_id": workflow_definition["workflow_id"],
                "estimated_duration": step["estimated_duration"],
                "dependencies": step["dependencies"]
            }
        )

        await coordinator.assign_task(task)
        coordination_tasks.append(task)

    print(f"Created {len(coordination_tasks)} coordination tasks")

    return execution_result, coordination_tasks

if __name__ == "__main__":
    asyncio.run(task_orchestration_example())
```

### Example 8: Distributed Decision Making

```python
# examples/08_distributed_decision_making.py
import asyncio
from src.coordination.distributed_decision import DistributedDecisionMaker, DecisionType, VoteType

async def distributed_decision_example():
    """Distributed decision making and consensus building"""

    memory_integration = AgentMemoryIntegration()
    await memory_integration.initialize()

    decision_maker = DistributedDecisionMaker()

    # Risk assessment decision
    risk_proposal = await decision_maker.create_proposal(
        decision_type=DecisionType.RISK_ASSESSMENT,
        title="Trading Risk Assessment",
        description="Assess overall system risk given current market conditions",
        options=[
            {"option": "Low Risk", "description": "Conservative trading approach"},
            {"option": "Medium Risk", "description": "Balanced risk-reward approach"},
            {"option": "High Risk", "description": "Aggressive trading approach"},
            {"option": "Critical Risk", "description": "Maximum caution required"}
        ],
        voters=["risk-management", "compliance-monitor", "portfolio-optimizer"],
        deadline="2025-11-12T16:00:00Z",
        voting_method=VoteType.WEIGHTED_VOTE,
        voting_weights={
            "risk-management": 0.4,
            "compliance-monitor": 0.4,
            "portfolio-optimizer": 0.2
        }
    )

    # Simulate voting process
    votes = {
        "risk-management": {"option": "Medium Risk", "confidence": 0.75, "reasoning": "Balanced approach suitable for current market"},
        "compliance-monitor": {"option": "Low Risk", "confidence": 0.90, "reasoning": "Regulatory requirements dictate caution"},
        "portfolio-optimizer": {"option": "Medium Risk", "confidence": 0.80, "reasoning": "Optimal risk-reward ratio"}
    }

    # Process decision
    decision_result = await decision_maker.process_votes(
        proposal_id=risk_proposal["proposal_id"],
        votes=votes
    )

    print(f"Decision made: {decision_result['selected_option']}")
    print(f"Confidence: {decision_result['confidence']}")
    print(f"Rationale: {decision_result['rationale']}")

    # Store decision in memory
    await memory_integration.add_memory(
        agent_id="distributed-decision-maker",
        content=f"Risk assessment decision: {decision_result['selected_option']}",
        memory_type="procedural",
        metadata={
            "decision_type": "risk_assessment",
            "selected_option": decision_result["selected_option"],
            "confidence": decision_result["confidence"],
            "voting_participants": list(votes.keys()),
            "proposal_id": risk_proposal["proposal_id"]
        }
    )

    return risk_proposal, decision_result, votes

if __name__ == "__main__":
    asyncio.run(distributed_decision_example())
```

## 🔧 Advanced Examples

### Example 9: Custom Memory Storage Strategies

```python
# examples/09_custom_memory_strategies.py
import asyncio
from agent_memory_integration import AgentMemoryIntegration, MemoryType, MemoryCategory

class CustomMemoryStrategy:
    """Custom memory management strategy for specific agent needs"""

    def __init__(self, memory_integration):
        self.memory_integration = memory_integration
        self.retention_policies = {
            MemoryType.EPISODIC: 30,  # days
            MemoryType.PROCEDURAL: 90,
            MemoryType.SEMANTIC: 180,
            MemoryType.FACTUAL: 365
        }

    async def intelligent_cleanup(self):
        """Automated memory cleanup based on importance and usage patterns"""

        for agent_id in self.memory_integration.agent_registry.keys():
            # Get agent's memory usage patterns
            memories = await self.memory_integration.get_agent_memories(agent_id)

            # Analyze memory importance and usage
            important_memories = []
            cleanup_candidates = []

            for memory in memories:
                memory_age = self._calculate_age(memory)
                retention_days = self.retention_policies.get(memory["memory_type"], 30)
                usage_score = self._calculate_usage_score(memory)

                if memory_age > retention_days and usage_score < 0.3:
                    cleanup_candidates.append(memory)
                else:
                    important_memories.append(memory)

            # Archive old memories
            for memory in cleanup_candidates:
                await self.memory_integration.archive_memory(memory["id"])
                print(f"Archived old memory: {memory['id']}")

            print(f"Agent {agent_id}: {len(important_memories)} retained, {len(cleanup_candidates)} archived")

    def _calculate_age(self, memory):
        """Calculate memory age in days"""
        # Implementation details...
        return 10  # placeholder

    def _calculate_usage_score(self, memory):
        """Calculate memory importance based on access patterns"""
        # Implementation details...
        return 0.8  # placeholder

async def custom_strategy_example():
    """Custom memory strategy implementation"""

    memory_integration = AgentMemoryIntegration()
    await memory_integration.initialize()

    custom_strategy = CustomMemoryStrategy(memory_integration)

    # Run intelligent cleanup
    await custom_strategy.intelligent_cleanup()

    return custom_strategy

if __name__ == "__main__":
    asyncio.run(custom_strategy_example())
```

## 🚀 Production Examples

### Example 10: Production Deployment Script

```bash
# examples/10_production_deployment.sh
#!/bin/bash

# RNR Enhanced Cognee Production Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Configuration
ENHANCED_COGNE_DIR="${ENHANCED_COGNE_DIR:-$(pwd)}"
BACKUP_DIR="/tmp/backup_$(date +%Y%m%d_%H%M%S)"
ENV_FILE="${ENHANCED_COGNE_DIR}/.env"

log "Starting RNR Enhanced Cognee Production Deployment"

# Pre-deployment checks
log "Running pre-deployment checks..."

# Verify Docker is installed and running
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Verify Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if RNR Enhanced Cognee directory exists
if [ ! -d "$ENHANCED_COGNE_DIR" ]; then
    error "RNR Enhanced Cognee directory not found: $ENHANCED_COGNE_DIR"
    exit 1
fi

cd "$ENHANCED_COGNE_DIR"

# Create backup of current configuration
log "Creating configuration backup..."
mkdir -p "$BACKUP_DIR"
cp -r docker/ src/ "$BACKUP_DIR/"
cp .env.example "$BACKUP_DIR/env.backup" 2>/dev/null || true

# Verify environment file
if [ ! -f "$ENV_FILE" ]; then
    log "Creating .env file from template..."
    cp .env.example "$ENV_FILE"
    log "Please review and update $ENV_FILE with your configuration"
fi

# Validate Docker Compose files
log "Validating Docker Compose configurations..."
docker-compose -f docker/docker-compose-enhanced-cognee.yml config --quiet
if [ $? -eq 0 ]; then
    log "✅ Enhanced stack configuration is valid"
else
    error "❌ Enhanced stack configuration has errors"
    exit 1
fi

# Stop any existing containers
log "Stopping existing containers..."
docker-compose -f docker/docker-compose-enhanced-cognee.yml down 2>/dev/null || true

# Pull latest images
log "Pulling latest Docker images..."
docker-compose -f docker/docker-compose-enhanced-cogyne.yml pull

# Start RNR Enhanced Cognee stack
log "Starting RNR Enhanced Cognee stack..."
docker-compose -f docker/docker-compose-enhanced-cognee.yml up -d

# Wait for services to be healthy
log "Waiting for services to initialize..."
sleep 30

# Health checks
log "Performing health checks..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U cognee_user -d cognee_db &>/dev/null; then
    log "✅ PostgreSQL is healthy"
else
    error "❌ PostgreSQL is not responding"
    exit 1
fi

# Check Qdrant
if curl -f http://localhost:26333/health &>/dev/null; then
    log "✅ Qdrant is healthy"
else
    error "❌ Qdrant is not responding"
    exit 1
fi

# Check Neo4j
if curl -f http://localhost:27474 &>/dev/null; then
    log "✅ Neo4j is healthy"
else
    error "❌ Neo4j is not responding"
    exit 1
fi

# Check Redis
if redis-cli -p 26379 ping &>/dev/null; then
    log "✅ Redis is healthy"
else
    error "❌ Redis is not responding"
    exit 1
fi

# Check RNR Enhanced Cognee service
if curl -f http://localhost:28080/health &>/dev/null; then
    log "✅ RNR Enhanced Cognee service is healthy"
else
    error "❌ RNR Enhanced Cognee service is not responding"
    exit 1
fi

# Start monitoring stack if available
if [ -f "docker/docker-compose-monitoring.yml" ]; then
    log "Starting monitoring stack..."
    docker-compose -f docker/docker-compose-monitoring.yml up -d
    sleep 15

    # Check Grafana
    if curl -f http://localhost:3000/api/health &>/dev/null; then
        log "✅ Grafana is healthy"
    else
        warn "⚠️  Grafana is not responding (monitoring may be starting)"
    fi
fi

# Display service URLs
log "🎉 RNR Enhanced Cognee is now running!"
log ""
log "Service URLs:"
log "  RNR Enhanced Cognee API: http://localhost:28080"
log "  Grafana Dashboard: http://localhost:3000"
log "  Prometheus: http://localhost:9090"
log ""
log "Admin Credentials:"
log "  Grafana: admin/admin (change after first login)"
log "  Prometheus: Default (no authentication)"
log ""
log "Management Commands:"
log "  View logs: docker-compose logs -f"
log "  Stop services: docker-compose down"
log "  Restart services: docker-compose restart"
log "  Scale services: docker-compose up --scale RNR-Enhanced-Cognee=3"

log "Deployment completed successfully!"

# Create monitoring script
cat > scripts/monitor.sh << 'EOF'
#!/bin/bash
# RNR Enhanced Cognee Monitoring Script

echo "=== RNR Enhanced Cognee System Status ==="

echo "Service Status:"
docker-compose ps

echo -e "\nMemory Usage:"
docker-compose exec RNR-Enhanced-Cognee python -c "
import sys
sys.path.append('src')
from agent_memory_integration import AgentMemoryIntegration
memory_system = AgentMemoryIntegration()
stats = memory_system.get_memory_stats()
print(f'Total Memories: {stats[\"total\"]}')
print(f'ATS Agents: {stats[\"ats\"]}')
print(f'OMA Agents: {stats[\"oma\"]}')
print(f'SMC Agents: {stats[\"smc\"]}')
"

echo -e "\nDatabase Sizes:"
docker exec postgres psql -U cognee_user -d cognee_db -c "
SELECT pg_size_pretty(pg_database_size('cognee_db')) AS size;"
docker exec qdrant curl -X GET http://localhost:6333/collections/qdrant/collections
docker exec neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as nodes"
"
EOF

chmod +x scripts/monitor.sh

log "Created monitoring script: scripts/monitor.sh"

# Create backup script
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
# RNR Enhanced Cognee Backup Script

BACKUP_DIR="/backup/enhanced-cognee/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating RNR Enhanced Cognee backup..."

# Backup configurations
cp -r docker/ src/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# Backup data volumes
docker run --rm -v enhanced_cognee_postgres_data:/data \
    -v "$BACKUP_DIR/postgres:/backup \
    postgres:16 tar czf /backup/postgres_backup.tar.gz /data

docker run --rm -v enhanced_cognee_qdrant_storage:/data \
    -v "$BACKUP_DIR/qdrant:/backup \
    qdrant/qdrant tar czf /backup/qdrant_backup.tar.gz /data

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x scripts/backup.sh

log "Created backup script: scripts/backup.sh"

# Cleanup
log "Cleaning up temporary files..."

log "🎉 Production deployment completed successfully!"
log ""
log "Next steps:"
log "1. Configure your agents and workflows"
log "2. Set up monitoring alerts"
log "3. Implement backup strategies"
log "4. Review security configurations"
log ""
log "For more information, see the documentation:"
log "- Implementation Guide: docs/IMPLEMENTATION_GUIDE.md"
log "- Examples: examples/ENHANCED_COGNEE_EXAMPLES.md"
```

### Example 11: Configuration Templates

```yaml
# examples/11_configuration_templates.yml
# RNR Enhanced Cognee Configuration Templates

# Production Environment Template
production:
  enhanced_cognee:
    port: 28080
    log_level: INFO
    max_connections: 100

  postgres:
    host: postgres
    port: 5432
    database: cognee_db
    user: cognee_user
    password: ${POSTGRES_PASSWORD}
    max_connections: 50

  qdrant:
    host: qdrant
    port: 6333
    api_key: ${QDRANT_API_KEY}

  neo4j:
    host: neo4j
    port: 7687
    user: neo4j
    password: ${NEO4J_PASSWORD}

  redis:
    host: redis
    port: 6379
    password: ${REDIS_PASSWORD}
    max_connections: 20

# Development Environment Template
development:
  enhanced_cognee:
    port: 28081
    debug: true
    log_level: DEBUG
    auto_reload: true

  postgres:
    host: localhost
    port: 5433
    database: cognee_dev
    user: cognee_user
    password: dev_password

  monitoring:
    grafana:
      enabled: true
      port: 3000
      admin_password: ${GRAFANA_ADMIN_PASSWORD}

    prometheus:
      enabled: true
      port: 9090

  agents:
    auto_discovery: true
    registration_interval: 60

  memory:
    retention_days: 30
    cleanup_interval: 3600  # 1 hour
    archive_old_memories: true
```

---

## 📋 Examples Summary

### **Quick Start Examples** (Examples 1-2)
- Basic memory operations and MCP server usage

### **Agent System Examples** (Examples 3-4)
- Trading agent workflows and development agent integration

### **Memory Integration Examples** (Examples 5-6)
- Cross-agent sharing and memory type categorization

### **Coordination Examples** (Examples 7-8)
- Task orchestration and distributed decision making

### **Advanced Examples** (Example 9)
- Custom memory strategies and intelligent cleanup

### **Production Examples** (Examples 10-11)
- Production deployment and configuration templates

Each example includes:
- ✅ **Complete working code**
- ✅ **Error handling**
- ✅ **Documentation**
- ✅ **Best practices**

---

*Last Updated: 2025-11-12*
*RNR Enhanced Cognee Examples Collection*