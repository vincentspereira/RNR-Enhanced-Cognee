"""
Unit tests for src/coordination/distributed_decision.py

Targets >= 85% line coverage.
All coordinator, memory wrapper, and message routing calls are mocked.
ASCII-only assertions and output.
"""

import asyncio
import sys
import types
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Stub out the heavy coordination imports before the module loads
# ---------------------------------------------------------------------------

def _make_coordination_stubs():
    """Build minimal stub modules for coordination package."""
    # Enums and dataclasses needed by sub_agent_coordinator
    import enum
    from dataclasses import dataclass, field

    class TaskPriority(enum.Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    class AgentStatus(enum.Enum):
        IDLE = "idle"
        BUSY = "busy"

    class MessageType(enum.Enum):
        NOTIFICATION = "notification"
        REQUEST = "request"

    @dataclass
    class AgentTask:
        task_id: str = ""
        agent_id: str = ""
        priority: TaskPriority = TaskPriority.MEDIUM

    @dataclass
    class AgentMessage:
        message_id: str = ""
        from_agent: str = ""
        to_agent: str = ""
        message_type: MessageType = MessageType.NOTIFICATION
        subject: str = ""
        content: dict = field(default_factory=dict)
        priority: TaskPriority = TaskPriority.MEDIUM

    class SubAgentCoordinator:
        def __init__(self, integration=None):
            self.integration = integration

        async def route_message(self, message):
            return True

    sub_coord_mod = types.ModuleType("src.coordination.sub_agent_coordinator")
    sub_coord_mod.SubAgentCoordinator = SubAgentCoordinator
    sub_coord_mod.AgentTask = AgentTask
    sub_coord_mod.TaskPriority = TaskPriority
    sub_coord_mod.AgentStatus = AgentStatus
    sub_coord_mod.MessageType = MessageType
    sub_coord_mod.AgentMessage = AgentMessage

    # Pre-register the sub_agent_coordinator stub BEFORE anything tries to import it.
    # Do NOT stub src.coordination itself -- let Python find the real package so that
    # the relative import `from .sub_agent_coordinator import ...` in distributed_decision.py
    # resolves to our stub.
    sys.modules.setdefault("src.coordination.sub_agent_coordinator", sub_coord_mod)

    # Also need to stub the heavy coordination_api import so src.coordination.__init__
    # doesn't blow up when we later import the package.
    coord_api_mod = types.ModuleType("src.coordination.coordination_api")
    coord_api_mod.app = MagicMock()
    sys.modules.setdefault("src.coordination.coordination_api", coord_api_mod)

    # Stub task_orchestration
    task_orch_mod = types.ModuleType("src.coordination.task_orchestration")
    class TaskOrchestrationEngine:
        def __init__(self, coordinator=None):
            pass
    task_orch_mod.TaskOrchestrationEngine = TaskOrchestrationEngine
    sys.modules.setdefault("src.coordination.task_orchestration", task_orch_mod)

    # Stub agent_memory_integration (needed by sub_agent_coordinator real module path)
    ami_mod = types.ModuleType("src.agent_memory_integration")
    class AgentMemoryIntegration:
        pass
    class MemoryType(enum.Enum):
        CORE = "core"
    ami_mod.AgentMemoryIntegration = AgentMemoryIntegration
    ami_mod.MemoryType = MemoryType
    sys.modules.setdefault("src.agent_memory_integration", ami_mod)

    # Stub agents package and smc_memory_wrapper (needed by _store_decision)
    agents_pkg = types.ModuleType("src.agents")
    agents_pkg.__path__ = [str(Path(__file__).parent.parent.parent / "src" / "agents")]
    sys.modules.setdefault("src.agents", agents_pkg)

    class SMCMemoryWrapper:
        def __init__(self, integration=None):
            pass

        async def store_context(self, agent_id=None, context_data=None):
            return True

        async def store_message(self, agent_id=None, message_data=None):
            return True

        async def store_task(self, agent_id=None, task_data=None):
            return True

    smc_mod = types.ModuleType("src.agents.smc_memory_wrapper")
    smc_mod.SMCMemoryWrapper = SMCMemoryWrapper
    sys.modules.setdefault("src.agents.smc_memory_wrapper", smc_mod)

    return sub_coord_mod


_sub_coord_mod = _make_coordination_stubs()

# If another test file (e.g. test_coordination_api.py) already pre-loaded
# a minimal stub for distributed_decision, evict it AND restore the real
# src.coordination package so that Python can find the real source file via
# its __path__.  We want the real implementation, not a stub.
_real_coord_path = str(Path(__file__).parent.parent.parent / "src" / "coordination")
_existing_coord = sys.modules.get("src.coordination")
if _existing_coord is not None and not hasattr(_existing_coord, "_is_real_pkg"):
    # It's a stub; replace with a proper package object pointing at the real dir
    import importlib.util as _ilu
    import importlib.machinery as _ilm
    _real_pkg = types.ModuleType("src.coordination")
    _real_pkg.__path__ = [_real_coord_path]
    _real_pkg.__package__ = "src.coordination"
    _real_pkg._is_real_pkg = True
    sys.modules["src.coordination"] = _real_pkg
sys.modules.pop("src.coordination.distributed_decision", None)


from src.coordination.distributed_decision import (  # noqa: E402
    DistributedDecisionMaker,
    DecisionProposal,
    DecisionType,
    DecisionStatus,
    VoteType,
    DecisionOption,
    DecisionVote,
    Decision,
)


# ---------------------------------------------------------------------------
# Convenience factory helpers
# ---------------------------------------------------------------------------

def _make_coordinator():
    SubAgentCoordinator = _sub_coord_mod.SubAgentCoordinator
    TaskPriority = _sub_coord_mod.TaskPriority
    coord = SubAgentCoordinator(integration=None)
    coord.route_message = AsyncMock(return_value=True)
    coord.integration = MagicMock()
    return coord, TaskPriority


def _make_proposal(
    decision_type=DecisionType.BINARY,
    participants=None,
    options=None,
    voting_deadline=None,
    consensus_threshold=0.7,
):
    _, TaskPriority = _make_coordinator()
    if participants is None:
        participants = ["agent-a", "agent-b", "agent-c"]
    proposal = DecisionProposal(
        proposal_id="prop-1",
        title="Test Decision",
        description="Test decision description",
        decision_type=decision_type,
        proposed_by="agent-a",
        priority=TaskPriority.HIGH,
        required_participants=participants,
        options=options or [],
        voting_deadline=voting_deadline,
        consensus_threshold=consensus_threshold,
    )
    return proposal


def _make_ddm():
    coord, _ = _make_coordinator()
    ddm = DistributedDecisionMaker(coordinator=coord)
    return ddm


# ---------------------------------------------------------------------------
# Tests: propose_decision
# ---------------------------------------------------------------------------

class TestProposeDecision:
    @pytest.mark.asyncio
    async def test_propose_valid_binary(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.BINARY)
        decision_id = await ddm.propose_decision(proposal)
        assert isinstance(decision_id, str)
        assert len(decision_id) > 0
        assert decision_id in ddm.active_decisions

    @pytest.mark.asyncio
    async def test_propose_stores_and_notifies(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        decision_id = await ddm.propose_decision(proposal)
        # route_message should have been called for each participant
        assert ddm.coordinator.route_message.called

    @pytest.mark.asyncio
    async def test_propose_invalid_too_few_participants(self):
        ddm = _make_ddm()
        proposal = _make_proposal(participants=["only-one", "two"])
        with pytest.raises(ValueError):
            await ddm.propose_decision(proposal)

    @pytest.mark.asyncio
    async def test_propose_multiple_choice_requires_two_options(self):
        ddm = _make_ddm()
        proposal = _make_proposal(
            decision_type=DecisionType.MULTIPLE_CHOICE,
            options=[DecisionOption(option_id="o1", title="Option 1", description="desc")],
        )
        with pytest.raises(ValueError):
            await ddm.propose_decision(proposal)

    @pytest.mark.asyncio
    async def test_propose_expired_deadline_fails(self):
        ddm = _make_ddm()
        past_deadline = datetime.now(UTC) - timedelta(hours=1)
        proposal = _make_proposal(voting_deadline=past_deadline)
        with pytest.raises(ValueError):
            await ddm.propose_decision(proposal)


# ---------------------------------------------------------------------------
# Tests: cast_vote
# ---------------------------------------------------------------------------

class TestCastVote:
    @pytest.mark.asyncio
    async def test_cast_vote_approve(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        result = await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        assert result is True

    @pytest.mark.asyncio
    async def test_cast_vote_reject(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        result = await ddm.cast_vote(did, "agent-b", VoteType.REJECT)
        assert result is True

    @pytest.mark.asyncio
    async def test_cast_vote_abstain(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        result = await ddm.cast_vote(did, "agent-c", VoteType.ABSTAIN)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_vote_twice(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        result = await ddm.cast_vote(did, "agent-a", VoteType.REJECT)
        assert result is False

    @pytest.mark.asyncio
    async def test_non_participant_cannot_vote(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        result = await ddm.cast_vote(did, "outsider", VoteType.APPROVE)
        assert result is False

    @pytest.mark.asyncio
    async def test_vote_on_unknown_decision_returns_false(self):
        ddm = _make_ddm()
        result = await ddm.cast_vote("no-such-id", "agent-a", VoteType.APPROVE)
        assert result is False

    @pytest.mark.asyncio
    async def test_all_votes_triggers_resolve_consensus(self):
        """All participants voting approve with threshold <= ratio triggers resolution."""
        ddm = _make_ddm()
        proposal = _make_proposal(consensus_threshold=0.5)
        did = await ddm.propose_decision(proposal)
        await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        await ddm.cast_vote(did, "agent-b", VoteType.APPROVE)
        # Third vote should trigger resolution
        await ddm.cast_vote(did, "agent-c", VoteType.APPROVE)
        # Decision should now be in history (moved from active)
        found = any(d.decision_id == did for d in ddm.decision_history)
        assert found


# ---------------------------------------------------------------------------
# Tests: add_debate_message
# ---------------------------------------------------------------------------

class TestAddDebateMessage:
    @pytest.mark.asyncio
    async def test_add_message_to_existing_decision(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        result = await ddm.add_debate_message(did, "agent-a", "I support this.", "argument")
        assert result is True
        decision = ddm.active_decisions[did]
        assert len(decision.debate_messages) == 1

    @pytest.mark.asyncio
    async def test_add_message_notifies_other_participants(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        call_count_before = ddm.coordinator.route_message.call_count
        await ddm.add_debate_message(did, "agent-a", "Point.", "argument")
        # Should notify remaining participants (agent-b, agent-c)
        assert ddm.coordinator.route_message.call_count > call_count_before

    @pytest.mark.asyncio
    async def test_add_message_to_unknown_decision_returns_false(self):
        ddm = _make_ddm()
        result = await ddm.add_debate_message("bad-id", "agent-a", "Hello")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: get_decision_status
# ---------------------------------------------------------------------------

class TestGetDecisionStatus:
    @pytest.mark.asyncio
    async def test_active_decision_status(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        status = await ddm.get_decision_status(did)
        assert status["decision_id"] == did
        assert "status" in status
        assert "voting_statistics" in status

    @pytest.mark.asyncio
    async def test_historic_decision_status(self):
        ddm = _make_ddm()
        proposal = _make_proposal(consensus_threshold=0.0)
        did = await ddm.propose_decision(proposal)
        # Trigger resolution by voting all participants
        await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        await ddm.cast_vote(did, "agent-b", VoteType.APPROVE)
        await ddm.cast_vote(did, "agent-c", VoteType.APPROVE)
        # Now check history
        status = await ddm.get_decision_status(did)
        assert status["decision_id"] == did

    @pytest.mark.asyncio
    async def test_unknown_decision_returns_error(self):
        ddm = _make_ddm()
        status = await ddm.get_decision_status("does-not-exist")
        assert "error" in status

    @pytest.mark.asyncio
    async def test_status_includes_deadline_passed_false(self):
        ddm = _make_ddm()
        future = datetime.now(UTC) + timedelta(hours=2)
        proposal = _make_proposal(voting_deadline=future)
        did = await ddm.propose_decision(proposal)
        status = await ddm.get_decision_status(did)
        assert status["deadline_passed"] is False


# ---------------------------------------------------------------------------
# Tests: cancel_decision
# ---------------------------------------------------------------------------

class TestCancelDecision:
    @pytest.mark.asyncio
    async def test_cancel_active_decision(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        result = await ddm.cancel_decision(did, "testing cancel")
        assert result is True
        assert did not in ddm.active_decisions
        assert any(d.decision_id == did for d in ddm.decision_history)

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_false(self):
        ddm = _make_ddm()
        result = await ddm.cancel_decision("no-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_returns_false(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        await ddm.cancel_decision(did)
        # Cancelled decision moved to history, not active -> returns False
        result = await ddm.cancel_decision(did)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: get_decision_recommendations
# ---------------------------------------------------------------------------

class TestGetDecisionRecommendations:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        ddm = _make_ddm()
        recs = await ddm.get_decision_recommendations({"domain": "trading strategy"})
        assert isinstance(recs, list)

    @pytest.mark.asyncio
    async def test_limits_results(self):
        ddm = _make_ddm()
        recs = await ddm.get_decision_recommendations(
            {"domain": "trading risk market analysis"},
            max_participants=2
        )
        assert len(recs) <= 2

    @pytest.mark.asyncio
    async def test_empty_context_returns_empty(self):
        ddm = _make_ddm()
        recs = await ddm.get_decision_recommendations({})
        assert isinstance(recs, list)


# ---------------------------------------------------------------------------
# Tests: _resolve_* internal methods
# ---------------------------------------------------------------------------

class TestResolveDecisions:
    @pytest.mark.asyncio
    async def test_resolve_binary_approved(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.BINARY)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # DecisionVote is already imported at module level
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE, expertise_weight=1.0),
        ]
        result = await ddm._resolve_binary_decision(decision)
        assert result["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_resolve_binary_rejected(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.BINARY)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.REJECT, expertise_weight=2.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE, expertise_weight=1.0),
        ]
        result = await ddm._resolve_binary_decision(decision)
        assert result["decision"] == "rejected"

    @pytest.mark.asyncio
    async def test_resolve_multiple_choice(self):
        ddm = _make_ddm()
        opts = [
            DecisionOption("opt-a", "Option A", "desc"),
            DecisionOption("opt-b", "Option B", "desc"),
        ]
        proposal = _make_proposal(
            decision_type=DecisionType.MULTIPLE_CHOICE,
            options=opts,
        )
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE,
                         option_id="opt-a", expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE,
                         option_id="opt-b", expertise_weight=0.5),
        ]
        result = await ddm._resolve_multiple_choice_decision(decision)
        assert result["winning_option"] == "opt-a"

    @pytest.mark.asyncio
    async def test_resolve_numeric(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.NUMERIC)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE,
                         option_id="100", expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE,
                         option_id="200", expertise_weight=1.0),
        ]
        result = await ddm._resolve_numeric_decision(decision)
        assert result["result"] == pytest.approx(150.0)

    @pytest.mark.asyncio
    async def test_resolve_consensus(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.CONSENSUS)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE, expertise_weight=1.0),
        ]
        result = await ddm._resolve_consensus_decision(decision)
        assert result["consensus_reached"] is True

    @pytest.mark.asyncio
    async def test_resolve_consensus_fails_with_reject(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.CONSENSUS)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.REJECT, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE, expertise_weight=1.0),
        ]
        result = await ddm._resolve_consensus_decision(decision)
        assert result["consensus_reached"] is False


# ---------------------------------------------------------------------------
# Tests: _calculate_vote_statistics
# ---------------------------------------------------------------------------

class TestCalculateVoteStatistics:
    @pytest.mark.asyncio
    async def test_statistics_with_votes(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        await ddm.cast_vote(did, "agent-b", VoteType.REJECT)
        decision = ddm.active_decisions.get(did)
        if decision is None:
            # may have been resolved
            decision = next(d for d in ddm.decision_history if d.decision_id == did)
        stats = ddm._calculate_vote_statistics(decision)
        assert stats["total_votes"] == 2
        assert stats["vote_breakdown"]["approve"] == 1
        assert stats["vote_breakdown"]["reject"] == 1

    def test_statistics_no_votes(self):
        ddm = _make_ddm()
        # Decision is already imported at module level
        _, TaskPriority = _make_coordinator()
        proposal = _make_proposal()
        decision = Decision(
            decision_id="fake-id",
            proposal=proposal,
        )
        stats = ddm._calculate_vote_statistics(decision)
        assert stats["total_votes"] == 0
        assert stats["consensus_percentage"] == 0.0


# ---------------------------------------------------------------------------
# Tests: _get_expertise_weight
# ---------------------------------------------------------------------------

class TestGetExpertiseWeight:
    @pytest.mark.asyncio
    async def test_known_agent_with_matching_context(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        proposal.context = {"domain": "trading_strategy market_analysis"}
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        weight = await ddm._get_expertise_weight("algorithmic-trading-system", decision)
        # Agent has trading_strategy: 0.9 and market_analysis: 0.8 -> avg > 1.0? no < 1.0
        assert weight > 0.0

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_default(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        weight = await ddm._get_expertise_weight("unknown-agent", decision)
        assert weight == 1.0

    @pytest.mark.asyncio
    async def test_expertise_weighting_disabled(self):
        ddm = _make_ddm()
        ddm.decision_settings["enable_expertise_weighting"] = False
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        weight = await ddm._get_expertise_weight("algorithmic-trading-system", decision)
        assert weight == 1.0


# ---------------------------------------------------------------------------
# Tests: _calculate_decision_confidence
# ---------------------------------------------------------------------------

class TestCalculateDecisionConfidence:
    @pytest.mark.asyncio
    async def test_no_votes_returns_zero(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        confidence = await ddm._calculate_decision_confidence(decision)
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_full_participation_returns_positive(self):
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # DecisionVote is already imported at module level
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE, expertise_weight=1.0),
        ]
        confidence = await ddm._calculate_decision_confidence(decision)
        assert 0.0 < confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests: _generate_implementation_steps
# ---------------------------------------------------------------------------

class TestGenerateImplementationSteps:
    @pytest.mark.asyncio
    async def test_binary_approved_generates_steps(self):
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.BINARY)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.result = {"decision": "approved"}
        steps = await ddm._generate_implementation_steps(decision)
        assert isinstance(steps, list)
        assert len(steps) > 0

    @pytest.mark.asyncio
    async def test_non_binary_returns_empty(self):
        ddm = _make_ddm()
        opts = [
            DecisionOption("o1", "Op1", "d"),
            DecisionOption("o2", "Op2", "d"),
        ]
        proposal = _make_proposal(
            decision_type=DecisionType.MULTIPLE_CHOICE,
            options=opts
        )
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.result = {"winning_option": "o1"}
        steps = await ddm._generate_implementation_steps(decision)
        assert isinstance(steps, list)
        assert len(steps) == 0


# ---------------------------------------------------------------------------
# Tests: _can_vote edge cases (lines 377, 381)
# ---------------------------------------------------------------------------

class TestCanVoteEdgeCases:
    @pytest.mark.asyncio
    async def test_cannot_vote_on_cancelled_decision(self):
        """Line 377: decision not in PROPOSED/DEBATING/VOTING."""
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        await ddm.cancel_decision(did, "cancelled")
        # Decision is in history now, not active -- cast_vote returns False
        result = await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_vote_past_deadline(self):
        """Line 381: voting deadline passed."""
        ddm = _make_ddm()
        future = datetime.now(UTC) + timedelta(hours=2)
        proposal = _make_proposal(voting_deadline=future)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # Backdating deadline to simulate it has passed
        decision.proposal.voting_deadline = datetime.now(UTC) - timedelta(seconds=1)
        result = await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: _should_resolve_decision edge cases (lines 425, 431, 436)
# ---------------------------------------------------------------------------

class TestShouldResolveDecision:
    @pytest.mark.asyncio
    async def test_resolves_when_deadline_passes(self):
        """Line 425: all voted + deadline passed -> should resolve (True)."""
        ddm = _make_ddm()
        future = datetime.now(UTC) + timedelta(hours=2)
        proposal = _make_proposal(voting_deadline=future)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # ALL three required participants vote with low weight so consensus not met
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.REJECT, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.REJECT, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.REJECT, expertise_weight=1.0),
        ]
        # Simulate deadline passed AFTER all have voted
        decision.proposal.voting_deadline = datetime.now(UTC) - timedelta(seconds=1)
        should = await ddm._should_resolve_decision(decision)
        assert should is True

    @pytest.mark.asyncio
    async def test_resolves_when_consensus_already_reached(self):
        """Line 431: consensus already reached -> should resolve."""
        ddm = _make_ddm()
        proposal = _make_proposal(consensus_threshold=0.0)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # All three participants voted
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE, expertise_weight=1.0),
        ]
        should = await ddm._should_resolve_decision(decision)
        assert should is True

    @pytest.mark.asyncio
    async def test_does_not_resolve_when_not_all_voted(self):
        """Line 436: not all required participants voted -> do not resolve."""
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # Only one of three voted, no deadline, no consensus reached
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
        ]
        should = await ddm._should_resolve_decision(decision)
        assert should is False


# ---------------------------------------------------------------------------
# Tests: _resolve_decision - RANKING/WEIGHTED path (lines 455-460, 473)
# ---------------------------------------------------------------------------

class TestResolveDecisionPaths:
    @pytest.mark.asyncio
    async def test_resolve_ranking_uses_consensus_path(self):
        """DecisionType.RANKING falls through to _resolve_consensus_decision."""
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.RANKING)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.REJECT, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE, expertise_weight=1.0),
        ]
        # Should not raise; consensus_failed because only 2/3 approve < 0.7 threshold
        await ddm._resolve_decision(decision)

    @pytest.mark.asyncio
    async def test_resolve_decision_consensus_failed_moves_to_history(self):
        """Lines 473: consensus_failed path when threshold not met."""
        ddm = _make_ddm()
        proposal = _make_proposal(
            decision_type=DecisionType.BINARY,
            consensus_threshold=0.9,  # High threshold
        )
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.REJECT, expertise_weight=2.0),
            DecisionVote("v3", did, "agent-c", VoteType.REJECT, expertise_weight=1.0),
        ]
        await ddm._resolve_decision(decision)
        assert any(d.status == DecisionStatus.CONSENSUS_FAILED
                   for d in ddm.decision_history)


# ---------------------------------------------------------------------------
# Tests: _resolve_numeric_decision ValueError path (lines 556-557)
# ---------------------------------------------------------------------------

class TestResolveNumericDecisionEdgeCases:
    @pytest.mark.asyncio
    async def test_non_numeric_option_id_skipped(self):
        """Lines 556-557: ValueError for non-numeric option_id."""
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.NUMERIC)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE,
                         option_id="not-a-number", expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE,
                         option_id="100", expertise_weight=1.0),
        ]
        result = await ddm._resolve_numeric_decision(decision)
        # Only one numeric vote (100) contributed
        assert result["result"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Tests: cancel_decision exception path (lines 312-314)
# ---------------------------------------------------------------------------

class TestCancelDecisionException:
    @pytest.mark.asyncio
    async def test_cancel_exception_returns_false(self):
        """Lines 312-314: exception in cancel_decision returns False."""
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        # Corrupt the decision so del raises
        decision = ddm.active_decisions[did]
        decision.status = DecisionStatus.PROPOSED  # stays valid for cancellation
        # Remove from active_decisions before cancel so del raises KeyError
        del ddm.active_decisions[did]
        ddm.active_decisions[did] = decision
        # Patch _store_decision_cancellation to raise
        async def _raise(*args, **kwargs):
            raise RuntimeError("storage failure")
        ddm._store_decision_cancellation = _raise
        result = await ddm.cancel_decision(did)
        # Should return False due to exception handler
        assert result is False


# ---------------------------------------------------------------------------
# Tests: cancel_decision - already cancelled/implemented (line 294)
# ---------------------------------------------------------------------------

class TestCancelAlreadyTerminated:
    @pytest.mark.asyncio
    async def test_cancel_implemented_decision_returns_false(self):
        """Line 294: decision already in IMPLEMENTED or CANCELLED status."""
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.status = DecisionStatus.IMPLEMENTED
        result = await ddm.cancel_decision(did)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: get_decision_recommendations with matching keywords (lines 332, 335)
# ---------------------------------------------------------------------------

class TestGetDecisionRecommendationsKeywords:
    @pytest.mark.asyncio
    async def test_returns_agents_with_matching_expertise(self):
        """Lines 332, 335: agent expertise score > 0, appended to results."""
        ddm = _make_ddm()
        recs = await ddm.get_decision_recommendations(
            {"domain": "trading_strategy market_analysis risk_assessment"}
        )
        # Known agents: algorithmic-trading-system, risk-management, market-analyzer
        assert len(recs) > 0
        assert "algorithmic-trading-system" in recs or "risk-management" in recs

    @pytest.mark.asyncio
    async def test_recommendations_exception_returns_empty(self):
        """Lines 341-343: exception returns []."""
        ddm = _make_ddm()
        # Corrupt agent_expertise to force an exception
        ddm.agent_expertise = "not a dict"
        recs = await ddm.get_decision_recommendations({"domain": "test"})
        assert recs == []


# ---------------------------------------------------------------------------
# Tests: _can_vote - decision status not in allowed set (line 377)
# ---------------------------------------------------------------------------

class TestCanVoteStatusCheck:
    @pytest.mark.asyncio
    async def test_cannot_vote_on_implemented_decision(self):
        """Line 377: decision.status not in allowed voting states."""
        ddm = _make_ddm()
        proposal = _make_proposal()
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.status = DecisionStatus.IMPLEMENTED
        # cast_vote calls _can_vote which sees status != PROPOSED/DEBATING/VOTING
        result = await ddm.cast_vote(did, "agent-a", VoteType.APPROVE)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: _should_resolve_decision - all voted, no deadline, no consensus (line 431)
# ---------------------------------------------------------------------------

class TestShouldResolveAllVotedNoConsensus:
    @pytest.mark.asyncio
    async def test_returns_false_when_all_voted_but_no_consensus(self):
        """Line 431: all voted, no deadline, consensus not reached -> False."""
        ddm = _make_ddm()
        # High threshold so 1/3 approves doesn't meet it
        proposal = _make_proposal(consensus_threshold=0.99)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE, expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.REJECT, expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.REJECT, expertise_weight=1.0),
        ]
        should = await ddm._should_resolve_decision(decision)
        assert should is False


# ---------------------------------------------------------------------------
# Tests: _resolve_decision - MULTIPLE_CHOICE and NUMERIC paths (lines 456, 458)
# ---------------------------------------------------------------------------

class TestResolveDecisionBranches:
    @pytest.mark.asyncio
    async def test_resolve_decision_multiple_choice_path(self):
        """Line 456: DecisionType.MULTIPLE_CHOICE branch in _resolve_decision."""
        ddm = _make_ddm()
        opts = [
            DecisionOption("opt-x", "X", "desc x"),
            DecisionOption("opt-y", "Y", "desc y"),
        ]
        proposal = _make_proposal(
            decision_type=DecisionType.MULTIPLE_CHOICE,
            options=opts,
            consensus_threshold=0.0,
        )
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE,
                         option_id="opt-x", expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE,
                         option_id="opt-x", expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE,
                         option_id="opt-y", expertise_weight=1.0),
        ]
        await ddm._resolve_decision(decision)
        # Moved to history with some resolved status
        found = next((d for d in ddm.decision_history if d.decision_id == did), None)
        assert found is not None

    @pytest.mark.asyncio
    async def test_resolve_decision_numeric_path(self):
        """Line 458: DecisionType.NUMERIC branch in _resolve_decision."""
        ddm = _make_ddm()
        proposal = _make_proposal(
            decision_type=DecisionType.NUMERIC,
            consensus_threshold=0.0,
        )
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        decision.votes = [
            DecisionVote("v1", did, "agent-a", VoteType.APPROVE,
                         option_id="50", expertise_weight=1.0),
            DecisionVote("v2", did, "agent-b", VoteType.APPROVE,
                         option_id="100", expertise_weight=1.0),
            DecisionVote("v3", did, "agent-c", VoteType.APPROVE,
                         option_id="75", expertise_weight=1.0),
        ]
        await ddm._resolve_decision(decision)
        found = next((d for d in ddm.decision_history if d.decision_id == did), None)
        assert found is not None

    @pytest.mark.asyncio
    async def test_resolve_decision_exception_path(self):
        """Lines 490-491: exception in _resolve_decision is caught."""
        ddm = _make_ddm()
        proposal = _make_proposal(decision_type=DecisionType.BINARY)
        did = await ddm.propose_decision(proposal)
        decision = ddm.active_decisions[did]
        # Corrupt votes to cause exception during resolution
        decision.votes = "not a list"
        # Should not raise - exception is caught internally
        await ddm._resolve_decision(decision)
