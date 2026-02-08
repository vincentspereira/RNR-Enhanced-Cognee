#!/usr/bin/env python3
"""
Task Orchestration Engine
Handles complex workflows, dependencies, and task scheduling
Integrates with Sub-Agent Coordinator for distributed execution
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from .sub_agent_coordinator import (
    SubAgentCoordinator, AgentTask, TaskPriority, AgentStatus,
    MessageType, AgentMessage
)

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Detailed task status for orchestration"""
    PENDING = "pending"
    WAITING_DEPENDENCIES = "waiting_dependencies"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRY = "retry"

class WorkflowStatus(Enum):
    """Workflow execution status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskDependency:
    """Task dependency definition"""
    task_id: str
    depends_on: str
    dependency_type: str  # "completion", "success", "data"
    condition: Optional[str] = None  # Additional condition for dependency

@dataclass
class WorkflowDefinition:
    """Workflow definition with tasks and dependencies"""
    workflow_id: str
    name: str
    description: str
    created_by: str
    tasks: List[AgentTask] = field(default_factory=list)
    dependencies: List[TaskDependency] = field(default_factory=list)
    global_parameters: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

@dataclass
class TaskExecution:
    """Task execution instance with runtime data"""
    execution_id: str
    task_id: str
    workflow_id: str
    assigned_agents: List[str]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    timeout_minutes: int = 60
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowExecution:
    """Workflow execution instance"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    task_executions: Dict[str, TaskExecution] = field(default_factory=dict)
    global_context: Dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    total_steps: int = 0

class TaskOrchestrationEngine:
    """
    Orchestrates complex workflows across multiple agents
    Manages dependencies, scheduling, and execution monitoring
    """

    def __init__(self, coordinator: SubAgentCoordinator):
        self.coordinator = coordinator

        # Workflow and task storage
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.workflow_executions: Dict[str, WorkflowExecution] = {}
        self.task_executions: Dict[str, TaskExecution] = {}

        # Execution queues
        self.pending_tasks: List[TaskExecution] = []
        self.running_tasks: List[TaskExecution] = []
        self.completed_tasks: List[TaskExecution] = []

        # Orchestration settings
        self.orchestration_settings = {
            "max_concurrent_workflows": 10,
            "max_concurrent_tasks_per_workflow": 5,
            "task_timeout_default": 60,  # minutes
            "workflow_timeout_default": 360,  # minutes
            "retry_delay_base": 5,  # minutes
            "retry_backoff_factor": 2,
            "auto_retry_on_failure": True,
            "checkpoint_interval": 10,  # tasks
            "cleanup_completed_after": 24,  # hours
        }

    async def create_workflow(self, workflow_def: WorkflowDefinition) -> str:
        """Create a new workflow definition"""
        try:
            # Validate workflow
            if not await self._validate_workflow(workflow_def):
                raise ValueError("Invalid workflow definition")

            # Store workflow
            self.workflows[workflow_def.workflow_id] = workflow_def

            # Store in memory for persistence
            await self._store_workflow_definition(workflow_def)

            logger.info(f"Created workflow: {workflow_def.workflow_id}")
            return workflow_def.workflow_id

        except Exception as e:
            logger.error(f"Failed to create workflow {workflow_def.workflow_id}: {e}")
            raise

    async def execute_workflow(self, workflow_id: str,
                             execution_context: Dict[str, Any] = None) -> str:
        """Execute a workflow"""
        try:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {workflow_id}")

            # Create execution instance
            execution_id = str(uuid.uuid4())
            execution = WorkflowExecution(
                execution_id=execution_id,
                workflow_id=workflow_id,
                global_context=execution_context or {},
                total_steps=len(workflow.tasks)
            )

            self.workflow_executions[execution_id] = execution

            # Initialize task executions
            for task in workflow.tasks:
                task_execution = TaskExecution(
                    execution_id=str(uuid.uuid4()),
                    task_id=task.task_id,
                    workflow_id=execution_id,
                    assigned_agents=[],
                    timeout_minutes=self.orchestration_settings["task_timeout_default"],
                    max_retries=self.orchestration_settings["max_retries_on_failure"]
                )
                self.task_executions[task_execution.execution_id] = task_execution
                execution.task_executions[task.task_id] = task_execution

            # Start execution
            workflow.status = WorkflowStatus.ACTIVE
            execution.status = WorkflowStatus.ACTIVE
            execution.started_at = datetime.now(UTC)

            # Begin task scheduling
            await self._schedule_ready_tasks(execution_id)

            # Store execution
            await self._store_workflow_execution(execution)

            logger.info(f"Started workflow execution: {execution_id}")
            return execution_id

        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            raise

    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed status of workflow execution"""
        try:
            execution = self.workflow_executions.get(execution_id)
            if not execution:
                raise ValueError(f"Workflow execution not found: {execution_id}")

            workflow = self.workflows.get(execution.workflow_id)
            if not workflow:
                raise ValueError(f"Workflow definition not found: {execution.workflow_id}")

            # Calculate task statistics
            task_stats = {
                "total": len(execution.task_executions),
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }

            for task_exec in execution.task_executions.values():
                task_stats[task_exec.status.value] += 1

            # Calculate progress
            progress = (task_stats["completed"] / task_stats["total"] * 100) if task_stats["total"] > 0 else 0

            # Estimate completion time
            if execution.started_at and progress > 0:
                elapsed = datetime.now(UTC) - execution.started_at
                estimated_total = elapsed / (progress / 100)
                eta = execution.started_at + estimated_total
                eta_str = eta.isoformat() if eta > datetime.now(UTC) else "Overdue"
            else:
                eta_str = "Unknown"

            return {
                "execution_id": execution_id,
                "workflow_id": execution.workflow_id,
                "workflow_name": workflow.name,
                "status": execution.status.value,
                "progress_percentage": round(progress, 2),
                "task_statistics": task_stats,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "estimated_completion": eta_str,
                "current_step": execution.current_step,
                "total_steps": execution.total_steps,
                "global_context": execution.global_context
            }

        except Exception as e:
            logger.error(f"Failed to get workflow status {execution_id}: {e}")
            return {"error": str(e), "execution_id": execution_id}

    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause a running workflow"""
        try:
            execution = self.workflow_executions.get(execution_id)
            if not execution:
                raise ValueError(f"Workflow execution not found: {execution_id}")

            if execution.status != WorkflowStatus.ACTIVE:
                return False

            # Pause running tasks
            for task_exec in execution.task_executions.values():
                if task_exec.status == TaskStatus.RUNNING:
                    await self._pause_task_execution(task_exec)

            execution.status = WorkflowStatus.PAUSED
            await self._store_workflow_execution(execution)

            logger.info(f"Paused workflow execution: {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to pause workflow {execution_id}: {e}")
            return False

    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume a paused workflow"""
        try:
            execution = self.workflow_executions.get(execution_id)
            if not execution:
                raise ValueError(f"Workflow execution not found: {execution_id}")

            if execution.status != WorkflowStatus.PAUSED:
                return False

            execution.status = WorkflowStatus.ACTIVE

            # Resume paused tasks and schedule new ones
            await self._schedule_ready_tasks(execution_id)
            await self._store_workflow_execution(execution)

            logger.info(f"Resumed workflow execution: {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resume workflow {execution_id}: {e}")
            return False

    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a workflow execution"""
        try:
            execution = self.workflow_executions.get(execution_id)
            if not execution:
                raise ValueError(f"Workflow execution not found: {execution_id}")

            if execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                return False

            # Cancel all running tasks
            for task_exec in execution.task_executions.values():
                if task_exec.status in [TaskStatus.RUNNING, TaskStatus.SCHEDULED]:
                    await self._cancel_task_execution(task_exec)
                    task_exec.status = TaskStatus.CANCELLED

            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.now(UTC)
            await self._store_workflow_execution(execution)

            logger.info(f"Cancelled workflow execution: {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel workflow {execution_id}: {e}")
            return False

    async def _validate_workflow(self, workflow: WorkflowDefinition) -> bool:
        """Validate workflow definition"""
        # Check for unique task IDs
        task_ids = [task.task_id for task in workflow.tasks]
        if len(task_ids) != len(set(task_ids)):
            logger.error("Duplicate task IDs in workflow")
            return False

        # Check dependencies reference valid tasks
        task_id_set = set(task_ids)
        for dep in workflow.dependencies:
            if dep.task_id not in task_id_set or dep.depends_on not in task_id_set:
                logger.error(f"Invalid dependency: {dep.task_id} -> {dep.depends_on}")
                return False

        # Check for circular dependencies
        if await self._has_circular_dependencies(workflow):
            logger.error("Circular dependencies detected in workflow")
            return False

        return True

    async def _has_circular_dependencies(self, workflow: WorkflowDefinition) -> bool:
        """Check for circular dependencies using DFS"""
        # Build dependency graph
        graph = {}
        for task in workflow.tasks:
            graph[task.task_id] = []

        for dep in workflow.dependencies:
            graph[dep.task_id].append(dep.depends_on)

        # DFS to detect cycles
        visited = set()
        recursion_stack = set()

        def has_cycle(node):
            visited.add(node)
            recursion_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True

            recursion_stack.remove(node)
            return False

        for task_id in graph:
            if task_id not in visited:
                if has_cycle(task_id):
                    return True

        return False

    async def _schedule_ready_tasks(self, execution_id: str):
        """Schedule tasks whose dependencies are satisfied"""
        try:
            execution = self.workflow_executions.get(execution_id)
            if not execution:
                return

            workflow = self.workflows.get(execution.workflow_id)
            if not workflow:
                return

            # Find tasks ready for execution
            ready_tasks = []
            for task in workflow.tasks:
                task_exec = execution.task_executions.get(task.task_id)
                if not task_exec or task_exec.status != TaskStatus.PENDING:
                    continue

                # Check if dependencies are satisfied
                if await self._are_dependencies_satisfied(task, execution):
                    ready_tasks.append((task, task_exec))

            # Schedule ready tasks (respect concurrency limits)
            scheduled_count = 0
            max_concurrent = self.orchestration_settings["max_concurrent_tasks_per_workflow"]
            running_count = sum(1 for te in execution.task_executions.values()
                              if te.status == TaskStatus.RUNNING)

            available_slots = max_concurrent - running_count

            for task, task_exec in ready_tasks[:available_slots]:
                # Assign to agents using coordinator
                task_assigned = await self.coordinator.assign_task(task)
                if task_assigned:
                    task_exec.status = TaskStatus.SCHEDULED
                    task_exec.assigned_agents = task.assigned_to
                    await self._execute_task(task, task_exec)
                    scheduled_count += 1

            if scheduled_count > 0:
                logger.info(f"Scheduled {scheduled_count} tasks for workflow {execution_id}")

        except Exception as e:
            logger.error(f"Failed to schedule tasks for workflow {execution_id}: {e}")

    async def _are_dependencies_satisfied(self, task: AgentTask,
                                        execution: WorkflowExecution) -> bool:
        """Check if all dependencies for a task are satisfied"""
        workflow = self.workflows.get(execution.workflow_id)
        if not workflow:
            return False

        # Find dependencies for this task
        task_deps = [dep for dep in workflow.dependencies if dep.task_id == task.task_id]

        for dep in task_deps:
            dep_task_exec = execution.task_executions.get(dep.depends_on)
            if not dep_task_exec:
                return False

            if dep.dependency_type == "completion":
                if dep_task_exec.status != TaskStatus.COMPLETED:
                    return False
            elif dep.dependency_type == "success":
                if dep_task_exec.status != TaskStatus.COMPLETED or dep_task_exec.error_message:
                    return False
            elif dep.dependency_type == "data":
                if not dep_task_exec.result_data:
                    return False

        return True

    async def _execute_task(self, task: AgentTask, task_exec: TaskExecution):
        """Execute a task and monitor its progress"""
        try:
            task_exec.status = TaskStatus.RUNNING
            task_exec.started_at = datetime.now(UTC)

            # Send task assignment message
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent=task.assigned_to[0] if task.assigned_to else "unknown",
                message_type=MessageType.TASK_ASSIGNMENT,
                subject=f"Execute Task: {task.title}",
                content={
                    "task": task.__dict__,
                    "execution_id": task_exec.execution_id,
                    "workflow_id": task_exec.workflow_id
                },
                priority=task.priority,
                requires_response=True
            )

            await self.coordinator.route_message(message)

            # Schedule timeout monitoring
            asyncio.create_task(self._monitor_task_timeout(task_exec))

            logger.info(f"Started task execution: {task_exec.execution_id}")

        except Exception as e:
            logger.error(f"Failed to execute task {task_exec.execution_id}: {e}")
            await self._handle_task_failure(task_exec, str(e))

    async def _monitor_task_timeout(self, task_exec: TaskExecution):
        """Monitor task execution for timeout"""
        try:
            timeout_seconds = task_exec.timeout_minutes * 60

            # Wait for either task completion or timeout
            for _ in range(timeout_seconds):
                if task_exec.status not in [TaskStatus.RUNNING, TaskStatus.SCHEDULED]:
                    return
                await asyncio.sleep(1)

            # Handle timeout
            if task_exec.status in [TaskStatus.RUNNING, TaskStatus.SCHEDULED]:
                await self._handle_task_timeout(task_exec)

        except Exception as e:
            logger.error(f"Error monitoring task timeout for {task_exec.execution_id}: {e}")

    async def _handle_task_timeout(self, task_exec: TaskExecution):
        """Handle task execution timeout"""
        logger.warning(f"Task {task_exec.execution_id} timed out")
        task_exec.status = TaskStatus.TIMEOUT
        task_exec.error_message = f"Task timed out after {task_exec.timeout_minutes} minutes"

        # Check if retry is possible
        if task_exec.retry_count < task_exec.max_retries:
            await self._retry_task(task_exec)
        else:
            await self._handle_task_failure(task_exec, "Maximum retries exceeded")

    async def _retry_task(self, task_exec: TaskExecution):
        """Retry a failed task"""
        try:
            task_exec.retry_count += 1
            task_exec.status = TaskStatus.RETRY

            # Calculate delay with exponential backoff
            base_delay = self.orchestration_settings["retry_delay_base"]
            backoff_factor = self.orchestration_settings["retry_backoff_factor"]
            delay_minutes = base_delay * (backoff_factor ** (task_exec.retry_count - 1))

            # Schedule retry
            await asyncio.sleep(delay_minutes * 60)  # Convert to seconds

            # Reset and retry
            task_exec.status = TaskStatus.PENDING
            task_exec.error_message = None
            task_exec.started_at = None

            await self._schedule_ready_tasks(task_exec.workflow_id)

            logger.info(f"Retrying task {task_exec.execution_id} (attempt {task_exec.retry_count})")

        except Exception as e:
            logger.error(f"Failed to retry task {task_exec.execution_id}: {e}")
            await self._handle_task_failure(task_exec, str(e))

    async def _handle_task_failure(self, task_exec: TaskExecution, error_message: str):
        """Handle task execution failure"""
        task_exec.status = TaskStatus.FAILED
        task_exec.error_message = error_message
        task_exec.completed_at = datetime.now(UTC)

        # Update workflow execution
        execution = self.workflow_executions.get(task_exec.workflow_id)
        if execution:
            execution.current_step += 1

            # Check if workflow should fail
            workflow = self.workflows.get(execution.workflow_id)
            if workflow and await self._should_fail_workflow(execution):
                execution.status = WorkflowStatus.FAILED
                execution.completed_at = datetime.now(UTC)

        logger.error(f"Task failed: {task_exec.execution_id} - {error_message}")

    async def _should_fail_workflow(self, execution: WorkflowExecution) -> bool:
        """Determine if workflow should fail based on task failures"""
        workflow = self.workflows.get(execution.workflow_id)
        if not workflow:
            return True

        # Check if any critical tasks failed
        failed_tasks = [
            task_exec for task_exec in execution.task_executions.values()
            if task_exec.status == TaskStatus.FAILED
        ]

        # If any task in critical path failed, fail workflow
        for task_exec in failed_tasks:
            task = next((t for t in workflow.tasks if t.task_id == task_exec.task_id), None)
            if task and task.priority == TaskPriority.CRITICAL:
                return True

        # If more than 50% of tasks failed, fail workflow
        if len(failed_tasks) > len(execution.task_executions) * 0.5:
            return True

        return False

    async def _pause_task_execution(self, task_exec: TaskExecution):
        """Pause a running task"""
        task_exec.status = TaskStatus.SCHEDULED
        # Send pause message to assigned agents
        await self._send_task_control_message(task_exec, "pause")

    async def _cancel_task_execution(self, task_exec: TaskExecution):
        """Cancel a task execution"""
        task_exec.status = TaskStatus.CANCELLED
        task_exec.completed_at = datetime.now(UTC)
        # Send cancel message to assigned agents
        await self._send_task_control_message(task_exec, "cancel")

    async def _send_task_control_message(self, task_exec: TaskExecution, action: str):
        """Send control message to assigned agents"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            from_agent="orchestrator",
            to_agent="multiple",  # Will be expanded to actual agents
            message_type=MessageType.NOTIFICATION,
            subject=f"Task {action.title()}",
            content={
                "action": action,
                "task_id": task_exec.task_id,
                "execution_id": task_exec.execution_id
            },
            priority=TaskPriority.HIGH
        )

        await self.coordinator.route_message(message)

    async def _store_workflow_definition(self, workflow: WorkflowDefinition):
        """Store workflow definition in memory"""
        # Store using SMC wrapper as this is coordination data
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_task(
            agent_id="orchestrator",
            task_data={
                "task_id": f"workflow_def_{workflow.workflow_id}",
                "type": "workflow_definition",
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "task_count": len(workflow.tasks),
                "dependency_count": len(workflow.dependencies),
                "created_by": workflow.created_by
            }
        )

    async def _store_workflow_execution(self, execution: WorkflowExecution):
        """Store workflow execution in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_task(
            agent_id="orchestrator",
            task_data={
                "task_id": f"workflow_exec_{execution.execution_id}",
                "type": "workflow_execution",
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "progress": f"{execution.current_step}/{execution.total_steps}",
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
            }
        )

# Example workflow scenarios
async def example_workflow_scenarios():
    """Example usage of the Task Orchestration Engine"""
    # Initialize integration and coordinator
    from ..agent_memory_integration import AgentMemoryIntegration
    integration = AgentMemoryIntegration()
    await integration.initialize()

    coordinator = SubAgentCoordinator(integration)
    orchestrator = TaskOrchestrationEngine(coordinator)

    # Example 1: Create a trading analysis workflow
    analysis_task1 = AgentTask(
        task_id="market_analysis",
        title="Analyze market conditions",
        description="Perform comprehensive market analysis",
        assigned_to=[],
        created_by="trading_manager",
        priority=TaskPriority.HIGH
    )

    analysis_task2 = AgentTask(
        task_id="risk_assessment",
        title="Assess risk factors",
        description="Evaluate risk factors for trading",
        assigned_to=[],
        created_by="trading_manager",
        priority=TaskPriority.HIGH
    )

    execution_task = AgentTask(
        task_id="execute_trades",
        title="Execute trading strategy",
        description="Execute trades based on analysis",
        assigned_to=[],
        created_by="trading_manager",
        priority=TaskPriority.CRITICAL
    )

    # Create workflow with dependencies
    dependencies = [
        TaskDependency("risk_assessment", "market_analysis", "completion"),
        TaskDependency("execute_trades", "risk_assessment", "success")
    ]

    workflow = WorkflowDefinition(
        workflow_id="trading_analysis_001",
        name="Trading Analysis Workflow",
        description="Comprehensive trading analysis and execution",
        created_by="trading_manager",
        tasks=[analysis_task1, analysis_task2, execution_task],
        dependencies=dependencies
    )

    # Create and execute workflow
    workflow_id = await orchestrator.create_workflow(workflow)
    execution_id = await orchestrator.execute_workflow(workflow_id)

    # Monitor workflow progress
    status = await orchestrator.get_workflow_status(execution_id)
    print(f"Workflow status: {status}")

    await integration.close()

if __name__ == "__main__":
    asyncio.run(example_workflow_scenarios())