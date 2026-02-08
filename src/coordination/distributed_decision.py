#!/usr/bin/env python3
"""
Distributed Decision Making System
Enables collaborative decision-making across multiple agents
Uses consensus mechanisms and voting algorithms for complex decisions
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from .sub_agent_coordinator import (
    SubAgentCoordinator, AgentTask, TaskPriority, AgentStatus,
    MessageType, AgentMessage
)

logger = logging.getLogger(__name__)

class DecisionType(Enum):
    """Types of decisions that can be made"""
    BINARY = "binary"  # Yes/No, True/False decisions
    MULTIPLE_CHOICE = "multiple_choice"  # Select from multiple options
    NUMERIC = "numeric"  # Numerical value decision
    RANKING = "ranking"  # Rank multiple options
    CONSENSUS = "consensus"  # Full agreement required
    WEIGHTED = "weighted"  # Weighted voting based on expertise

class DecisionStatus(Enum):
    """Decision making status"""
    PROPOSED = "proposed"
    DEBATING = "debating"
    VOTING = "voting"
    CONSENSUS_REACHED = "consensus_reached"
    CONSENSUS_FAILED = "consensus_failed"
    IMPLEMENTED = "implemented"
    CANCELLED = "cancelled"

class VoteType(Enum):
    """Vote types"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    PROPOSED_AMENDMENT = "proposed_amendment"

@dataclass
class DecisionOption:
    """Decision option for multiple choice decisions"""
    option_id: str
    title: str
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    proposed_by: str = ""
    confidence_score: float = 0.0
    supporting_evidence: List[str] = field(default_factory=list)

@dataclass
class DecisionVote:
    """Agent vote on a decision"""
    vote_id: str
    decision_id: str
    agent_id: str
    vote_type: VoteType
    option_id: Optional[str] = None  # For multiple choice
    confidence: float = 1.0
    reasoning: str = ""
    expertise_weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DecisionProposal:
    """Decision proposal with all relevant information"""
    proposal_id: str
    title: str
    description: str
    decision_type: DecisionType
    proposed_by: str
    priority: TaskPriority
    context: Dict[str, Any] = field(default_factory=dict)
    options: List[DecisionOption] = field(default_factory=list)
    required_participants: List[str] = field(default_factory=list)
    voting_deadline: Optional[datetime] = None
    consensus_threshold: float = 0.7  # 70% agreement for consensus
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Decision:
    """Complete decision with proposal and votes"""
    decision_id: str
    proposal: DecisionProposal
    votes: List[DecisionVote] = field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PROPOSED
    result: Optional[Any] = None
    implementation_plan: Optional[Dict[str, Any]] = None
    debate_messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    confidence_score: float = 0.0

class DistributedDecisionMaker:
    """
    Manages distributed decision-making across multiple agents
    Implements various consensus mechanisms and voting algorithms
    """

    def __init__(self, coordinator: SubAgentCoordinator):
        self.coordinator = coordinator

        # Decision storage
        self.active_decisions: Dict[str, Decision] = {}
        self.decision_history: List[Decision] = []

        # Decision settings
        self.decision_settings = {
            "default_consensus_threshold": 0.7,
            "default_voting_timeout_minutes": 60,
            "min_participants_for_decision": 3,
            "max_debate_duration_minutes": 30,
            "enable_expertise_weighting": True,
            "require_justification": True,
            "auto_implement_decisions": True,
            "decision_retention_days": 90
        }

        # Agent expertise mapping (can be learned over time)
        self.agent_expertise = {
            "algorithmic-trading-system": {"trading_strategy": 0.9, "market_analysis": 0.8},
            "risk-management": {"risk_assessment": 0.95, "compliance": 0.9},
            "portfolio-optimizer": {"portfolio_optimization": 0.9, "asset_allocation": 0.8},
            "market-analyzer": {"market_analysis": 0.95, "sentiment_analysis": 0.8},
            "code-reviewer": {"code_quality": 0.9, "security": 0.7},
            "security-specialist": {"security": 0.95, "compliance": 0.8},
            "technical-writer": {"documentation": 0.9, "communication": 0.8}
        }

    async def propose_decision(self, proposal: DecisionProposal) -> str:
        """Propose a new decision for agent consideration"""
        try:
            # Validate proposal
            if not await self._validate_proposal(proposal):
                raise ValueError("Invalid decision proposal")

            # Create decision
            decision = Decision(
                decision_id=str(uuid.uuid4()),
                proposal=proposal,
                created_at=datetime.now(UTC)
            )

            # Store decision
            self.active_decisions[decision.decision_id] = decision

            # Store in memory
            await self._store_decision(decision)

            # Notify required participants
            await self._notify_participants(decision)

            logger.info(f"Proposed decision: {decision.decision_id} - {proposal.title}")
            return decision.decision_id

        except Exception as e:
            logger.error(f"Failed to propose decision: {e}")
            raise

    async def cast_vote(self, decision_id: str, agent_id: str, vote_type: VoteType,
                       option_id: str = None, reasoning: str = "",
                       confidence: float = 1.0) -> bool:
        """Cast a vote on a decision"""
        try:
            decision = self.active_decisions.get(decision_id)
            if not decision:
                raise ValueError(f"Decision not found: {decision_id}")

            # Validate voting rights
            if not await self._can_vote(agent_id, decision):
                raise ValueError(f"Agent {agent_id} cannot vote on decision {decision_id}")

            # Create vote
            vote = DecisionVote(
                vote_id=str(uuid.uuid4()),
                decision_id=decision_id,
                agent_id=agent_id,
                vote_type=vote_type,
                option_id=option_id,
                reasoning=reasoning,
                confidence=confidence,
                expertise_weight=await self._get_expertise_weight(agent_id, decision)
            )

            # Add vote
            decision.votes.append(vote)

            # Store vote in memory
            await self._store_vote(vote)

            # Check if decision can be resolved
            if await self._should_resolve_decision(decision):
                await self._resolve_decision(decision)

            logger.info(f"Vote cast: {agent_id} -> {decision_id} ({vote_type.value})")
            return True

        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            return False

    async def add_debate_message(self, decision_id: str, agent_id: str,
                               message: str, message_type: str = "argument") -> bool:
        """Add a message to the decision debate"""
        try:
            decision = self.active_decisions.get(decision_id)
            if not decision:
                raise ValueError(f"Decision not found: {decision_id}")

            debate_message = {
                "message_id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "message": message,
                "message_type": message_type,
                "timestamp": datetime.now(UTC).isoformat()
            }

            decision.debate_messages.append(debate_message)

            # Store in memory
            await self._store_debate_message(decision_id, debate_message)

            # Notify other participants
            await self._notify_debate_message(decision, debate_message)

            logger.debug(f"Debate message added to decision {decision_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add debate message: {e}")
            return False

    async def get_decision_status(self, decision_id: str) -> Dict[str, Any]:
        """Get detailed status of a decision"""
        try:
            decision = self.active_decisions.get(decision_id)
            if not decision:
                # Check in history
                historic_decision = next((d for d in self.decision_history if d.decision_id == decision_id), None)
                if historic_decision:
                    decision = historic_decision
                else:
                    raise ValueError(f"Decision not found: {decision_id}")

            # Calculate voting statistics
            vote_stats = self._calculate_vote_statistics(decision)

            # Check if voting deadline has passed
            deadline_passed = False
            if decision.proposal.voting_deadline:
                deadline_passed = datetime.now(UTC) > decision.proposal.voting_deadline

            return {
                "decision_id": decision_id,
                "title": decision.proposal.title,
                "status": decision.status.value,
                "decision_type": decision.proposal.decision_type.value,
                "proposal": {
                    "description": decision.proposal.description,
                    "proposed_by": decision.proposal.proposed_by,
                    "priority": decision.proposal.priority.value,
                    "options": [opt.__dict__ for opt in decision.proposal.options]
                },
                "voting_statistics": vote_stats,
                "deadline_passed": deadline_passed,
                "created_at": decision.created_at.isoformat(),
                "completed_at": decision.completed_at.isoformat() if decision.completed_at else None,
                "debate_message_count": len(decision.debate_messages),
                "confidence_score": decision.confidence_score
            }

        except Exception as e:
            logger.error(f"Failed to get decision status: {e}")
            return {"error": str(e), "decision_id": decision_id}

    async def cancel_decision(self, decision_id: str, reason: str = "") -> bool:
        """Cancel an active decision"""
        try:
            decision = self.active_decisions.get(decision_id)
            if not decision:
                return False

            if decision.status in [DecisionStatus.IMPLEMENTED, DecisionStatus.CANCELLED]:
                return False

            decision.status = DecisionStatus.CANCELLED
            decision.completed_at = datetime.now(UTC)

            # Move to history
            self.decision_history.append(decision)
            del self.active_decisions[decision_id]

            # Store cancellation
            await self._store_decision_cancellation(decision_id, reason)

            # Notify participants
            await self._notify_decision_cancelled(decision, reason)

            logger.info(f"Decision cancelled: {decision_id} - {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel decision: {e}")
            return False

    async def get_decision_recommendations(self, context: Dict[str, Any],
                                         max_participants: int = 5) -> List[str]:
        """Get recommended participants for a decision based on context"""
        try:
            # Analyze context to determine relevant expertise areas
            context_keywords = set()
            for value in context.values():
                if isinstance(value, str):
                    context_keywords.update(value.lower().split())

            # Score agents based on expertise relevance
            agent_scores = []
            for agent_id, expertise in self.agent_expertise.items():
                score = 0.0
                for exp_area, exp_level in expertise.items():
                    if exp_area in context_keywords:
                        score += exp_level

                if score > 0:
                    agent_scores.append((agent_id, score))

            # Sort by score and return top agents
            agent_scores.sort(key=lambda x: x[1], reverse=True)
            return [agent for agent, _ in agent_scores[:max_participants]]

        except Exception as e:
            logger.error(f"Failed to get decision recommendations: {e}")
            return []

    async def _validate_proposal(self, proposal: DecisionProposal) -> bool:
        """Validate decision proposal"""
        # Check required participants
        if len(proposal.required_participants) < self.decision_settings["min_participants_for_decision"]:
            logger.error("Insufficient required participants")
            return False

        # Validate options for multiple choice decisions
        if proposal.decision_type == DecisionType.MULTIPLE_CHOICE and len(proposal.options) < 2:
            logger.error("Multiple choice decision requires at least 2 options")
            return False

        # Check voting deadline
        if proposal.voting_deadline and proposal.voting_deadline <= datetime.now(UTC):
            logger.error("Voting deadline must be in the future")
            return False

        return True

    async def _can_vote(self, agent_id: str, decision: Decision) -> bool:
        """Check if agent can vote on decision"""
        # Check if agent is in required participants
        if agent_id not in decision.proposal.required_participants:
            return False

        # Check if agent has already voted
        existing_vote = next((v for v in decision.votes if v.agent_id == agent_id), None)
        if existing_vote:
            return False

        # Check if decision is still in voting phase
        if decision.status not in [DecisionStatus.PROPOSED, DecisionStatus.DEBATING, DecisionStatus.VOTING]:
            return False

        # Check voting deadline
        if decision.proposal.voting_deadline and datetime.now(UTC) > decision.proposal.voting_deadline:
            return False

        return True

    async def _get_expertise_weight(self, agent_id: str, decision: Decision) -> float:
        """Calculate expertise weight for an agent on a decision"""
        if not self.decision_settings["enable_expertise_weighting"]:
            return 1.0

        # Get agent expertise in relevant areas
        agent_expertise = self.agent_expertise.get(agent_id, {})

        # Analyze decision context for expertise areas
        context_keywords = set()
        context = decision.proposal.context
        for value in context.values():
            if isinstance(value, str):
                context_keywords.update(value.lower().split())

        # Calculate expertise score
        expertise_score = 0.0
        relevant_expertise = 0

        for exp_area, exp_level in agent_expertise.items():
            if exp_area in context_keywords:
                expertise_score += exp_level
                relevant_expertise += 1

        if relevant_expertise > 0:
            return expertise_score / relevant_expertise
        else:
            return 1.0  # Default weight if no relevant expertise

    async def _should_resolve_decision(self, decision: Decision) -> bool:
        """Check if a decision can be resolved"""
        required_participants = decision.proposal.required_participants
        voting_participants = set(vote.agent_id for vote in decision.votes)

        # Check if all required participants have voted
        if not set(required_participants).issubset(voting_participants):
            return False

        # Check if voting deadline has passed
        if decision.proposal.voting_deadline and datetime.now(UTC) > decision.proposal.voting_deadline:
            return True

        # Check if consensus is already reached
        if await self._check_consensus(decision):
            return True

        return False

    async def _check_consensus(self, decision: Decision) -> bool:
        """Check if consensus has been reached"""
        if not decision.votes:
            return False

        total_weight = sum(vote.expertise_weight for vote in decision.votes)
        approve_weight = sum(
            vote.expertise_weight for vote in decision.votes
            if vote.vote_type == VoteType.APPROVE
        )

        consensus_ratio = approve_weight / total_weight if total_weight > 0 else 0
        threshold = decision.proposal.consensus_threshold

        return consensus_ratio >= threshold

    async def _resolve_decision(self, decision: Decision):
        """Resolve a decision and implement if necessary"""
        try:
            # Calculate result based on votes
            if decision.proposal.decision_type == DecisionType.BINARY:
                decision.result = await self._resolve_binary_decision(decision)
            elif decision.proposal.decision_type == DecisionType.MULTIPLE_CHOICE:
                decision.result = await self._resolve_multiple_choice_decision(decision)
            elif decision.proposal.decision_type == DecisionType.NUMERIC:
                decision.result = await self._resolve_numeric_decision(decision)
            else:
                decision.result = await self._resolve_consensus_decision(decision)

            # Calculate confidence score
            decision.confidence_score = await self._calculate_decision_confidence(decision)

            # Update status
            if await self._check_consensus(decision):
                decision.status = DecisionStatus.CONSENSUS_REACHED

                # Auto-implement if enabled
                if self.decision_settings["auto_implement_decisions"]:
                    await self._implement_decision(decision)
            else:
                decision.status = DecisionStatus.CONSENSUS_FAILED

            decision.completed_at = datetime.now(UTC)

            # Move to history
            self.decision_history.append(decision)
            if decision.decision_id in self.active_decisions:
                del self.active_decisions[decision.decision_id]

            # Store resolution
            await self._store_decision_resolution(decision)

            # Notify participants
            await self._notify_decision_resolved(decision)

            logger.info(f"Decision resolved: {decision.decision_id} - {decision.status.value}")

        except Exception as e:
            logger.error(f"Failed to resolve decision: {e}")

    async def _resolve_binary_decision(self, decision: Decision) -> Dict[str, Any]:
        """Resolve binary decision from votes"""
        approve_votes = [v for v in decision.votes if v.vote_type == VoteType.APPROVE]
        reject_votes = [v for v in decision.votes if v.vote_type == VoteType.REJECT]

        approve_weight = sum(v.expertise_weight for v in approve_votes)
        reject_weight = sum(v.expertise_weight for v in reject_votes)

        result = {
            "decision": "approved" if approve_weight > reject_weight else "rejected",
            "approve_weight": approve_weight,
            "reject_weight": reject_weight,
            "total_weight": approve_weight + reject_weight,
            "vote_breakdown": {
                "approve": len(approve_votes),
                "reject": len(reject_votes),
                "abstain": len([v for v in decision.votes if v.vote_type == VoteType.ABSTAIN])
            }
        }

        return result

    async def _resolve_multiple_choice_decision(self, decision: Decision) -> Dict[str, Any]:
        """Resolve multiple choice decision from votes"""
        option_weights = {}
        total_weight = 0

        for vote in decision.votes:
            if vote.vote_type == VoteType.APPROVE and vote.option_id:
                weight = vote.expertise_weight
                option_weights[vote.option_id] = option_weights.get(vote.option_id, 0) + weight
                total_weight += weight

        # Find winning option
        winning_option = None
        max_weight = 0
        for option_id, weight in option_weights.items():
            if weight > max_weight:
                max_weight = weight
                winning_option = option_id

        return {
            "winning_option": winning_option,
            "option_weights": option_weights,
            "total_weight": total_weight,
            "winning_percentage": (max_weight / total_weight * 100) if total_weight > 0 else 0
        }

    async def _resolve_numeric_decision(self, decision: Decision) -> Dict[str, Any]:
        """Resolve numeric decision using weighted average"""
        numeric_votes = [
            vote for vote in decision.votes
            if vote.vote_type == VoteType.APPROVE and vote.option_id
        ]

        weighted_sum = 0
        total_weight = 0

        for vote in numeric_votes:
            try:
                value = float(vote.option_id)  # Option ID contains numeric value
                weighted_sum += value * vote.expertise_weight
                total_weight += vote.expertise_weight
            except ValueError:
                continue

        result_value = weighted_sum / total_weight if total_weight > 0 else 0

        return {
            "result": result_value,
            "weighted_sum": weighted_sum,
            "total_weight": total_weight,
            "vote_count": len(numeric_votes)
        }

    async def _resolve_consensus_decision(self, decision: Decision) -> Dict[str, Any]:
        """Resolve consensus decision requiring full agreement"""
        approve_votes = [v for v in decision.votes if v.vote_type == VoteType.APPROVE]
        total_required = len(decision.proposal.required_participants)

        consensus_reached = len(approve_votes) == total_required

        return {
            "consensus_reached": consensus_reached,
            "approve_votes": len(approve_votes),
            "required_votes": total_required,
            "abstain_votes": len([v for v in decision.votes if v.vote_type == VoteType.ABSTAIN])
        }

    def _calculate_vote_statistics(self, decision: Decision) -> Dict[str, Any]:
        """Calculate voting statistics for a decision"""
        vote_counts = {
            "approve": 0,
            "reject": 0,
            "abstain": 0,
            "amendment": 0
        }

        total_weight = 0
        approve_weight = 0

        for vote in decision.votes:
            vote_counts[vote.vote_type.value] += 1
            total_weight += vote.expertise_weight
            if vote.vote_type == VoteType.APPROVE:
                approve_weight += vote.expertise_weight

        consensus_percentage = (approve_weight / total_weight * 100) if total_weight > 0 else 0

        return {
            "total_votes": len(decision.votes),
            "vote_breakdown": vote_counts,
            "total_weight": total_weight,
            "approve_weight": approve_weight,
            "consensus_percentage": round(consensus_percentage, 2),
            "required_participants": len(decision.proposal.required_participants),
            "participated_participants": len(set(vote.agent_id for vote in decision.votes))
        }

    async def _calculate_decision_confidence(self, decision: Decision) -> float:
        """Calculate confidence score for the decision"""
        if not decision.votes:
            return 0.0

        # Factors affecting confidence:
        # 1. Participation rate
        # 2. Expertise relevance
        # 3. Reasoning quality (if provided)
        # 4. Vote consistency

        participation_rate = len(decision.votes) / len(decision.proposal.required_participants)
        expertise_weight = sum(vote.expertise_weight for vote in decision.votes) / len(decision.votes)

        confidence = (participation_rate * 0.4 + expertise_weight * 0.6)
        return min(confidence, 1.0)

    async def _notify_participants(self, decision: Decision):
        """Notify required participants about the decision"""
        for agent_id in decision.proposal.required_participants:
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                from_agent="decision_maker",
                to_agent=agent_id,
                message_type=MessageType.NOTIFICATION,
                subject=f"Decision Proposal: {decision.proposal.title}",
                content={
                    "decision_id": decision.decision_id,
                    "proposal": decision.proposal.__dict__,
                    "action_required": "review_and_vote"
                },
                priority=decision.proposal.priority
            )

            await self.coordinator.route_message(message)

    async def _implement_decision(self, decision: Decision):
        """Implement a resolved decision"""
        # Create implementation plan
        decision.implementation_plan = {
            "decision_id": decision.decision_id,
            "implementation_status": "planned",
            "assigned_to": "task_scheduler",
            "estimated_completion": datetime.now(UTC) + timedelta(hours=1),
            "implementation_steps": await self._generate_implementation_steps(decision)
        }

        # Store implementation plan
        await self._store_implementation_plan(decision)

        # Update decision status
        decision.status = DecisionStatus.IMPLEMENTED

    async def _generate_implementation_steps(self, decision: Decision) -> List[Dict[str, Any]]:
        """Generate implementation steps for a decision"""
        steps = []

        # Example implementation steps based on decision type
        if decision.proposal.decision_type == DecisionType.BINARY:
            if decision.result.get("decision") == "approved":
                steps.append({
                    "step": "create_tasks",
                    "description": "Create tasks for decision implementation",
                    "assigned_to": "task-scheduler"
                })
                steps.append({
                    "step": "notify_stakeholders",
                    "description": "Notify relevant stakeholders about decision",
                    "assigned_to": "message-broker"
                })

        return steps

    # Memory storage methods (simplified)
    async def _store_decision(self, decision: Decision):
        """Store decision in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_context(
            agent_id="decision_maker",
            context_data={
                "type": "decision",
                "decision_id": decision.decision_id,
                "title": decision.proposal.title,
                "status": decision.status.value,
                "decision_type": decision.proposal.decision_type.value
            }
        )

    async def _store_vote(self, vote: DecisionVote):
        """Store vote in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_message(
            agent_id="decision_maker",
            message_data={
                "type": "vote",
                "vote_id": vote.vote_id,
                "decision_id": vote.decision_id,
                "agent_id": vote.agent_id,
                "vote_type": vote.vote_type.value,
                "confidence": vote.confidence
            }
        )

    async def _store_debate_message(self, decision_id: str, message: Dict[str, Any]):
        """Store debate message in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_message(
            agent_id="decision_maker",
            message_data={
                "type": "debate",
                "decision_id": decision_id,
                "message": message
            }
        )

    async def _store_decision_resolution(self, decision: Decision):
        """Store decision resolution in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_context(
            agent_id="decision_maker",
            context_data={
                "type": "decision_resolution",
                "decision_id": decision.decision_id,
                "result": decision.result,
                "confidence_score": decision.confidence_score,
                "status": decision.status.value
            }
        )

    async def _store_decision_cancellation(self, decision_id: str, reason: str):
        """Store decision cancellation in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_context(
            agent_id="decision_maker",
            context_data={
                "type": "decision_cancellation",
                "decision_id": decision_id,
                "reason": reason
            }
        )

    async def _store_implementation_plan(self, decision: Decision):
        """Store implementation plan in memory"""
        from ..agents.smc_memory_wrapper import SMCMemoryWrapper
        smc_wrapper = SMCMemoryWrapper(self.coordinator.integration)

        await smc_wrapper.store_task(
            agent_id="decision_maker",
            task_data={
                "task_id": f"implement_{decision.decision_id}",
                "type": "decision_implementation",
                "decision_id": decision.decision_id,
                "implementation_plan": decision.implementation_plan
            }
        )

    # Notification methods (simplified)
    async def _notify_debate_message(self, decision: Decision, message: Dict[str, Any]):
        """Notify participants about new debate message"""
        for agent_id in decision.proposal.required_participants:
            if agent_id != message["agent_id"]:  # Don't notify sender
                notification = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    from_agent="decision_maker",
                    to_agent=agent_id,
                    message_type=MessageType.NOTIFICATION,
                    subject=f"New Debate Message: {decision.proposal.title}",
                    content={
                        "decision_id": decision.decision_id,
                        "debate_message": message
                    },
                    priority=decision.proposal.priority
                )

                await self.coordinator.route_message(notification)

    async def _notify_decision_resolved(self, decision: Decision):
        """Notify participants about decision resolution"""
        for agent_id in decision.proposal.required_participants:
            notification = AgentMessage(
                message_id=str(uuid.uuid4()),
                from_agent="decision_maker",
                to_agent=agent_id,
                message_type=MessageType.NOTIFICATION,
                subject=f"Decision Resolved: {decision.proposal.title}",
                content={
                    "decision_id": decision.decision_id,
                    "result": decision.result,
                    "status": decision.status.value,
                    "confidence_score": decision.confidence_score
                },
                priority=decision.proposal.priority
            )

            await self.coordinator.route_message(notification)

    async def _notify_decision_cancelled(self, decision: Decision, reason: str):
        """Notify participants about decision cancellation"""
        for agent_id in decision.proposal.required_participants:
            notification = AgentMessage(
                message_id=str(uuid.uuid4()),
                from_agent="decision_maker",
                to_agent=agent_id,
                message_type=MessageType.NOTIFICATION,
                subject=f"Decision Cancelled: {decision.proposal.title}",
                content={
                    "decision_id": decision.decision_id,
                    "reason": reason
                },
                priority=decision.proposal.priority
            )

            await self.coordinator.route_message(notification)

# Example decision scenarios
async def example_decision_scenarios():
    """Example usage of the Distributed Decision Maker"""
    # Initialize integration and coordinator
    from ..agent_memory_integration import AgentMemoryIntegration
    integration = AgentMemoryIntegration()
    await integration.initialize()

    coordinator = SubAgentCoordinator(integration)
    decision_maker = DistributedDecisionMaker(coordinator)

    # Example 1: Binary decision on trading strategy
    proposal = DecisionProposal(
        proposal_id="prop_001",
        title="Adopt New Trading Strategy",
        description="Should we adopt the new momentum-based trading strategy?",
        decision_type=DecisionType.BINARY,
        proposed_by="algorithmic-trading-system",
        priority=TaskPriority.HIGH,
        context={
            "strategy_type": "momentum",
            "expected_return": "15%",
            "risk_level": "medium",
            "implementation_cost": "low"
        },
        required_participants=[
            "algorithmic-trading-system",
            "risk-management",
            "portfolio-optimizer"
        ],
        voting_deadline=datetime.now(UTC) + timedelta(hours=2),
        consensus_threshold=0.8
    )

    decision_id = await decision_maker.propose_decision(proposal)
    print(f"Proposed decision: {decision_id}")

    # Example votes
    await decision_maker.cast_vote(
        decision_id, "algorithmic-trading-system", VoteType.APPROVE,
        reasoning="Strategy shows strong backtest results with 15% expected return"
    )

    await decision_maker.cast_vote(
        decision_id, "risk-management", VoteType.APPROVE,
        reasoning="Risk levels are acceptable within our risk management framework"
    )

    await decision_maker.cast_vote(
        decision_id, "portfolio-optimizer", VoteType.REJECT,
        reasoning="Strategy may not align with current portfolio diversification goals"
    )

    # Check decision status
    status = await decision_maker.get_decision_status(decision_id)
    print(f"Decision status: {status}")

    await integration.close()

if __name__ == "__main__":
    asyncio.run(example_decision_scenarios())