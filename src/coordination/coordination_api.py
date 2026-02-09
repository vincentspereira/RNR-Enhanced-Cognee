#!/usr/bin/env python3
"""
Coordination API Layer
Unified API interface for all coordination functionalities
Provides RESTful endpoints for external systems to interact with coordination layer
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .sub_agent_coordinator import (
    SubAgentCoordinator, AgentTask, TaskPriority, AgentStatus,
    MessageType, AgentMessage, AgentCapability
)
from .task_orchestration import (
    TaskOrchestrationEngine, WorkflowDefinition, WorkflowStatus,
    TaskDependency
)
from .distributed_decision import (
    DistributedDecisionMaker, DecisionProposal, DecisionType,
    DecisionStatus, VoteType, DecisionOption
)

logger = logging.getLogger(__name__)

# Global coordination components
coordinator = None
orchestrator = None
decision_maker = None

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifespan events for coordination API"""
    global coordinator, orchestrator, decision_maker

    # Startup
    try:
        from ..agent_memory_integration import AgentMemoryIntegration
        integration = AgentMemoryIntegration()
        await integration.initialize()

        coordinator = SubAgentCoordinator(integration)
        orchestrator = TaskOrchestrationEngine(coordinator)
        decision_maker = DistributedDecisionMaker(coordinator)

        logger.info("Coordination API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize coordination API: {e}")
        raise

    yield

    # Shutdown
    if coordinator and hasattr(coordinator, 'integration'):
        await coordinator.integration.close()

    logger.info("Coordination API shutdown complete")

# FastAPI app initialization with lifespan
app = FastAPI(
    title="Enhanced Cognee Coordination API",
    description="Unified coordination interface for multi-agent system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class TaskRequest(BaseModel):
    title: str
    description: str
    assigned_to: List[str] = []
    priority: str = "normal"
    deadline: Optional[str] = None
    dependencies: List[str] = []
    metadata: Dict[str, Any] = {}

class WorkflowRequest(BaseModel):
    workflow_id: str
    name: str
    description: str
    tasks: List[TaskRequest]
    dependencies: List[Dict[str, Any]] = []
    global_parameters: Dict[str, Any] = {}
    deadline: Optional[str] = None

class DecisionRequest(BaseModel):
    title: str
    description: str
    decision_type: str
    priority: str = "normal"
    context: Dict[str, Any] = {}
    options: List[Dict[str, Any]] = []
    required_participants: List[str]
    voting_deadline: Optional[str] = None
    consensus_threshold: float = 0.7

class VoteRequest(BaseModel):
    agent_id: str
    vote_type: str
    option_id: Optional[str] = None
    reasoning: str = ""
    confidence: float = 1.0

class MessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str
    subject: str
    content: Dict[str, Any]
    priority: str = "normal"
    requires_response: bool = False

class CapabilityRequest(BaseModel):
    agent_id: str
    capability_name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    max_concurrent_tasks: int = 1

# Dependency injection function
async def get_coordination_components():
    """Dependency injection for coordination components"""
    global coordinator, orchestrator, decision_maker
    return coordinator, orchestrator, decision_maker

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check health of coordination system"""
    components = {}
    overall_status = "healthy"

    try:
        coord_status = await get_coordination_components()
        if all(coord_status):
            components["coordinator"] = "healthy"
            components["orchestrator"] = "healthy"
            components["decision_maker"] = "healthy"
        else:
            overall_status = "unhealthy"

    except Exception as e:
        overall_status = "unhealthy"
        components["error"] = str(e)

    return {
        "status": overall_status,
        "components": components,
        "timestamp": datetime.now(UTC).isoformat()
    }

# Task management endpoints
@app.post("/tasks")
async def create_task(task_request: TaskRequest, components = Depends(get_coordination_components)):
    """Create and assign a new task"""
    try:
        coordinator, _, _ = components

        task = AgentTask(
            task_id=str(uuid.uuid4()),
            title=task_request.title,
            description=task_request.description,
            assigned_to=task_request.assigned_to,
            created_by="api_user",
            priority=TaskPriority(task_request.priority),
            deadline=datetime.fromisoformat(task_request.deadline) if task_request.deadline else None,
            dependencies=task_request.dependencies,
            metadata=task_request.metadata
        )

        success = await coordinator.assign_task(task)

        if success:
            return {
                "task_id": task.task_id,
                "status": "created",
                "message": "Task created and assigned successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to assign task")

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str, components = Depends(get_coordination_components)):
    """Get status of a specific task"""
    try:
        coordinator, _, _ = components

        if task_id in coordinator.active_tasks:
            task = coordinator.active_tasks[task_id]
            return {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status,
                "assigned_to": task.assigned_to,
                "created_at": task.created_at.isoformat(),
                "priority": task.priority.value,
                "deadline": task.deadline.isoformat() if task.deadline else None
            }
        else:
            raise HTTPException(status_code=404, detail="Task not found")

    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/agent/{agent_id}")
async def get_agent_tasks(agent_id: str, components = Depends(get_coordination_components)):
    """Get tasks assigned to a specific agent"""
    try:
        coordinator, _, _ = components

        agent_tasks = []
        for task in coordinator.active_tasks.values():
            if agent_id in task.assigned_to:
                agent_tasks.append({
                    "task_id": task.task_id,
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority.value,
                    "created_at": task.created_at.isoformat()
                })

        return {"agent_id": agent_id, "tasks": agent_tasks}

    except Exception as e:
        logger.error(f"Error getting agent tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Workflow management endpoints
@app.post("/workflows")
async def create_workflow(workflow_request: WorkflowRequest, components = Depends(get_coordination_components)):
    """Create a new workflow"""
    try:
        _, orchestrator, _ = components

        # Convert task requests to AgentTask objects
        tasks = []
        for task_req in workflow_request.tasks:
            task = AgentTask(
                task_id=str(uuid.uuid4()),
                title=task_req.title,
                description=task_req.description,
                assigned_to=task_req.assigned_to,
                created_by="api_user",
                priority=TaskPriority(task_req.priority),
                deadline=datetime.fromisoformat(task_req.deadline) if task_req.deadline else None,
                dependencies=task_req.dependencies,
                metadata=task_req.metadata
            )
            tasks.append(task)

        # Convert dependencies
        dependencies = []
        for dep in workflow_request.dependencies:
            dependencies.append(TaskDependency(
                task_id=dep["task_id"],
                depends_on=dep["depends_on"],
                dependency_type=dep.get("dependency_type", "completion"),
                condition=dep.get("condition")
            ))

        workflow = WorkflowDefinition(
            workflow_id=workflow_request.workflow_id,
            name=workflow_request.name,
            description=workflow_request.description,
            created_by="api_user",
            tasks=tasks,
            dependencies=dependencies,
            global_parameters=workflow_request.global_parameters,
            deadline=datetime.fromisoformat(workflow_request.deadline) if workflow_request.deadline else None
        )

        workflow_id = await orchestrator.create_workflow(workflow)

        return {
            "workflow_id": workflow_id,
            "status": "created",
            "message": "Workflow created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, execution_context: Dict[str, Any] = None, components = Depends(get_coordination_components)):
    """Execute a workflow"""
    try:
        _, orchestrator, _ = components

        execution_id = await orchestrator.execute_workflow(workflow_id, execution_context)

        return {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "started",
            "message": "Workflow execution started"
        }

    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows/executions/{execution_id}/status")
async def get_workflow_execution_status(execution_id: str, components = Depends(get_coordination_components)):
    """Get status of workflow execution"""
    try:
        _, orchestrator, _ = components

        status = await orchestrator.get_workflow_status(execution_id)
        return status

    except Exception as e:
        logger.error(f"Error getting workflow execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/executions/{execution_id}/pause")
async def pause_workflow(execution_id: str, components = Depends(get_coordination_components)):
    """Pause a running workflow"""
    try:
        _, orchestrator, _ = components

        success = await orchestrator.pause_workflow(execution_id)

        if success:
            return {"message": "Workflow paused successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to pause workflow")

    except Exception as e:
        logger.error(f"Error pausing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/executions/{execution_id}/resume")
async def resume_workflow(execution_id: str, components = Depends(get_coordination_components)):
    """Resume a paused workflow"""
    try:
        _, orchestrator, _ = components

        success = await orchestrator.resume_workflow(execution_id)

        if success:
            return {"message": "Workflow resumed successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to resume workflow")

    except Exception as e:
        logger.error(f"Error resuming workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Decision making endpoints
@app.post("/decisions")
async def propose_decision(decision_request: DecisionRequest, components = Depends(get_coordination_components)):
    """Propose a new decision"""
    try:
        _, _, decision_maker = components

        # Convert options
        options = []
        for opt in decision_request.options:
            options.append(DecisionOption(
                option_id=opt.get("option_id", str(uuid.uuid4())),
                title=opt["title"],
                description=opt["description"],
                data=opt.get("data", {}),
                proposed_by=opt.get("proposed_by", ""),
                confidence_score=opt.get("confidence_score", 0.0),
                supporting_evidence=opt.get("supporting_evidence", [])
            ))

        proposal = DecisionProposal(
            proposal_id=str(uuid.uuid4()),
            title=decision_request.title,
            description=decision_request.description,
            decision_type=DecisionType(decision_request.decision_type),
            proposed_by="api_user",
            priority=TaskPriority(decision_request.priority),
            context=decision_request.context,
            options=options,
            required_participants=decision_request.required_participants,
            voting_deadline=datetime.fromisoformat(decision_request.voting_deadline) if decision_request.voting_deadline else None,
            consensus_threshold=decision_request.consensus_threshold
        )

        decision_id = await decision_maker.propose_decision(proposal)

        return {
            "decision_id": decision_id,
            "status": "proposed",
            "message": "Decision proposed successfully"
        }

    except Exception as e:
        logger.error(f"Error proposing decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/decisions/{decision_id}/vote")
async def cast_vote(decision_id: str, vote_request: VoteRequest, components = Depends(get_coordination_components)):
    """Cast a vote on a decision"""
    try:
        _, _, decision_maker = components

        success = await decision_maker.cast_vote(
            decision_id=decision_id,
            agent_id=vote_request.agent_id,
            vote_type=VoteType(vote_request.vote_type),
            option_id=vote_request.option_id,
            reasoning=vote_request.reasoning,
            confidence=vote_request.confidence
        )

        if success:
            return {"message": "Vote cast successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cast vote")

    except Exception as e:
        logger.error(f"Error casting vote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/decisions/{decision_id}")
async def get_decision_status(decision_id: str, components = Depends(get_coordination_components)):
    """Get status of a decision"""
    try:
        _, _, decision_maker = components

        status = await decision_maker.get_decision_status(decision_id)
        return status

    except Exception as e:
        logger.error(f"Error getting decision status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/decisions/{decision_id}/debate")
async def add_debate_message(decision_id: str, agent_id: str, message: str, message_type: str = "argument", components = Depends(get_coordination_components)):
    """Add message to decision debate"""
    try:
        _, _, decision_maker = components

        success = await decision_maker.add_debate_message(
            decision_id=decision_id,
            agent_id=agent_id,
            message=message,
            message_type=message_type
        )

        if success:
            return {"message": "Debate message added successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add debate message")

    except Exception as e:
        logger.error(f"Error adding debate message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Agent communication endpoints
@app.post("/messages")
async def send_message(message_request: MessageRequest, components = Depends(get_coordination_components)):
    """Send a message between agents"""
    try:
        coordinator, _, _ = components

        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            from_agent=message_request.from_agent,
            to_agent=message_request.to_agent,
            message_type=MessageType(message_request.message_type),
            subject=message_request.subject,
            content=message_request.content,
            priority=TaskPriority(message_request.priority),
            requires_response=message_request.requires_response
        )

        success = await coordinator.route_message(message)

        if success:
            return {
                "message_id": message.message_id,
                "status": "sent",
                "message": "Message sent successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to send message")

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Agent capability endpoints
@app.post("/agents/capabilities")
async def register_capability(capability_request: CapabilityRequest, components = Depends(get_coordination_components)):
    """Register agent capability"""
    try:
        coordinator, _, _ = components

        capability = AgentCapability(
            agent_id=capability_request.agent_id,
            capability_name=capability_request.capability_name,
            description=capability_request.description,
            input_types=capability_request.input_types,
            output_types=capability_request.output_types,
            max_concurrent_tasks=capability_request.max_concurrent_tasks
        )

        success = await coordinator.register_agent_capability(capability)

        if success:
            return {"message": "Capability registered successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to register capability")

    except Exception as e:
        logger.error(f"Error registering capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}/load")
async def get_agent_load(agent_id: str, components = Depends(get_coordination_components)):
    """Get current load of an agent"""
    try:
        coordinator, _, _ = components

        load = await coordinator.get_agent_load(agent_id)
        return load

    except Exception as e:
        logger.error(f"Error getting agent load: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System overview endpoints
@app.get("/overview")
async def get_system_overview(components = Depends(get_coordination_components)):
    """Get comprehensive system overview"""
    try:
        coordinator, orchestrator, decision_maker = components

        # Get coordination overview
        coordination_overview = await coordinator.get_coordination_overview()

        # Get decision recommendations (example context)
        recommendations = await decision_maker.get_decision_recommendations(
            context={"trading": "strategy", "risk": "assessment"},
            max_participants=5
        )

        return {
            "coordination_overview": coordination_overview,
            "decision_recommendations": recommendations,
            "system_health": await health_check()
        }

    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents")
async def list_agents(components = Depends(get_coordination_components)):
    """List all registered agents"""
    try:
        coordinator, _, _ = components

        agents = []
        for agent_id, info in coordinator.agent_registry.items():
            load = await coordinator.get_agent_load(agent_id)
            agents.append({
                "agent_id": agent_id,
                "category": info["category"].value,
                "type": info["type"],
                "capabilities": info["capabilities"],
                "max_concurrent_tasks": info["max_concurrent_tasks"],
                "critical": info["critical"],
                "current_load": load.get("load_percentage", 0),
                "status": load.get("status", "unknown")
            })

        return {"agents": agents}

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics and monitoring endpoints
@app.get("/analytics/tasks")
async def get_task_analytics(hours: int = 24, components = Depends(get_coordination_components)):
    """Get task analytics"""
    try:
        coordinator, _, _ = components

        # Calculate task statistics
        total_tasks = len(coordinator.active_tasks)
        task_status_counts = {}

        for task in coordinator.active_tasks.values():
            task_status_counts[task.status] = task_status_counts.get(task.status, 0) + 1

        return {
            "period_hours": hours,
            "total_tasks": total_tasks,
            "status_breakdown": task_status_counts,
            "completion_rate": (task_status_counts.get("completed", 0) / total_tasks * 100) if total_tasks > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error getting task analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/decisions")
async def get_decision_analytics(hours: int = 24, components = Depends(get_coordination_components)):
    """Get decision analytics"""
    try:
        _, _, decision_maker = components

        active_decisions = len(decision_maker.active_decisions)
        completed_decisions = len([
            d for d in decision_maker.decision_history
            if d.completed_at and d.completed_at > datetime.now(UTC) - timedelta(hours=hours)
        ])

        return {
            "period_hours": hours,
            "active_decisions": active_decisions,
            "completed_decisions": completed_decisions,
            "average_confidence": sum(d.confidence_score for d in decision_maker.decision_history[-10:]) / min(len(decision_maker.decision_history), 10)
        }

    except Exception as e:
        logger.error(f"Error getting decision analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoints for external integrations
@app.post("/webhooks/task-completed")
async def handle_task_completed_webhook(payload: Dict[str, Any], components = Depends(get_coordination_components)):
    """Handle task completion webhook from external systems"""
    try:
        _, orchestrator, _ = components

        task_id = payload.get("task_id")
        result = payload.get("result", {})
        status = payload.get("status", "completed")

        # Update task execution in orchestrator
        for execution in orchestrator.task_executions.values():
            if execution.task_id == task_id:
                execution.status = TaskStatus(status) if status in [s.value for s in TaskStatus] else TaskStatus.COMPLETED
                execution.result_data = result
                execution.completed_at = datetime.now(UTC)

                # Schedule dependent tasks
                await orchestrator._schedule_ready_tasks(execution.workflow_id)
                break

        return {"status": "processed", "task_id": task_id}

    except Exception as e:
        logger.error(f"Error handling task completed webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now(UTC).isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "status_code": 500,
        "timestamp": datetime.now(UTC).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)