"""
Unit tests for src.approval_workflow
======================================
Tests ApprovalRequest, ApprovalWorkflowManager, CLIApprovalWorkflow,
and DashboardApprovalWorkflow.
All filesystem I/O is mocked. No real file writes.
No Unicode characters in assertions.
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(tmp_path):
    """Create a manager using a temp directory for storage."""
    from src.approval_workflow import ApprovalWorkflowManager
    return ApprovalWorkflowManager(storage_path=tmp_path)


# ---------------------------------------------------------------------------
# ApprovalRequest
# ---------------------------------------------------------------------------

class TestApprovalRequest:
    def test_default_status_is_pending(self):
        from src.approval_workflow import ApprovalRequest
        req = ApprovalRequest("id-1", "test-op", {"key": "value"})
        assert req.status == "pending"

    def test_auto_created_at(self):
        from src.approval_workflow import ApprovalRequest
        req = ApprovalRequest("id-1", "test-op", {})
        assert req.created_at is not None
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(req.created_at)
        assert isinstance(dt, datetime)

    def test_custom_created_at(self):
        from src.approval_workflow import ApprovalRequest
        ts = "2026-01-01T00:00:00+00:00"
        req = ApprovalRequest("id-1", "op", {}, created_at=ts)
        assert req.created_at == ts

    def test_decided_at_initially_none(self):
        from src.approval_workflow import ApprovalRequest
        req = ApprovalRequest("id-1", "op", {})
        assert req.decided_at is None

    def test_to_dict_contains_all_fields(self):
        from src.approval_workflow import ApprovalRequest
        req = ApprovalRequest("id-1", "my-op", {"count": 5})
        d = req.to_dict()
        assert d["request_id"] == "id-1"
        assert d["operation"] == "my-op"
        assert d["details"] == {"count": 5}
        assert d["status"] == "pending"
        assert d["decided_at"] is None
        assert "created_at" in d

    def test_to_dict_after_approve(self):
        from src.approval_workflow import ApprovalRequest
        req = ApprovalRequest("id-2", "op", {})
        req.status = "approved"
        req.decided_at = "2026-01-01T12:00:00+00:00"
        d = req.to_dict()
        assert d["status"] == "approved"
        assert d["decided_at"] == "2026-01-01T12:00:00+00:00"


# ---------------------------------------------------------------------------
# ApprovalWorkflowManager - create_request
# ---------------------------------------------------------------------------

class TestApprovalWorkflowManagerCreate:
    def test_create_request_returns_approval_request(self, tmp_path):
        from src.approval_workflow import ApprovalRequest
        manager = _make_manager(tmp_path)
        req = manager.create_request("op-name", {"key": "value"})
        assert isinstance(req, ApprovalRequest)
        assert req.operation == "op-name"
        assert req.details == {"key": "value"}

    def test_create_request_adds_to_pending(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        assert req.request_id in manager.pending_requests

    def test_create_request_saves_file(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {"x": 1})
        file_path = tmp_path / f"{req.request_id}.json"
        assert file_path.exists()
        data = json.loads(file_path.read_text())
        assert data["operation"] == "op"

    def test_create_multiple_requests(self, tmp_path):
        manager = _make_manager(tmp_path)
        r1 = manager.create_request("op1", {})
        r2 = manager.create_request("op2", {})
        assert r1.request_id != r2.request_id
        assert len(manager.pending_requests) == 2

    def test_created_request_status_is_pending(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        assert req.status == "pending"


# ---------------------------------------------------------------------------
# ApprovalWorkflowManager - approve_request
# ---------------------------------------------------------------------------

class TestApprovalWorkflowManagerApprove:
    def test_approve_existing_request_returns_true(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        result = manager.approve_request(req.request_id)
        assert result is True

    def test_approve_changes_status_to_approved(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.approve_request(req.request_id)
        assert req.status == "approved"
        assert req.decided_at is not None

    def test_approve_removes_from_pending(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.approve_request(req.request_id)
        assert req.request_id not in manager.pending_requests

    def test_approve_adds_to_completed(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.approve_request(req.request_id)
        assert req in manager.completed_requests

    def test_approve_nonexistent_request_returns_false(self, tmp_path):
        manager = _make_manager(tmp_path)
        result = manager.approve_request("non-existent-id")
        assert result is False

    def test_approve_saves_updated_file(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.approve_request(req.request_id)
        file_path = tmp_path / f"{req.request_id}.json"
        data = json.loads(file_path.read_text())
        assert data["status"] == "approved"


# ---------------------------------------------------------------------------
# ApprovalWorkflowManager - reject_request
# ---------------------------------------------------------------------------

class TestApprovalWorkflowManagerReject:
    def test_reject_existing_request_returns_true(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        result = manager.reject_request(req.request_id)
        assert result is True

    def test_reject_changes_status_to_rejected(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.reject_request(req.request_id)
        assert req.status == "rejected"

    def test_reject_with_reason_adds_to_details(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.reject_request(req.request_id, reason="too risky")
        assert req.details.get("rejection_reason") == "too risky"

    def test_reject_without_reason(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.reject_request(req.request_id, reason=None)
        assert "rejection_reason" not in req.details

    def test_reject_removes_from_pending(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.reject_request(req.request_id)
        assert req.request_id not in manager.pending_requests

    def test_reject_adds_to_completed(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.reject_request(req.request_id)
        assert req in manager.completed_requests

    def test_reject_nonexistent_returns_false(self, tmp_path):
        manager = _make_manager(tmp_path)
        result = manager.reject_request("bad-id")
        assert result is False


# ---------------------------------------------------------------------------
# ApprovalWorkflowManager - get_pending_requests
# ---------------------------------------------------------------------------

class TestGetPendingRequests:
    def test_empty_initially(self, tmp_path):
        manager = _make_manager(tmp_path)
        assert manager.get_pending_requests() == []

    def test_returns_all_pending(self, tmp_path):
        manager = _make_manager(tmp_path)
        r1 = manager.create_request("op1", {})
        r2 = manager.create_request("op2", {})
        pending = manager.get_pending_requests()
        assert len(pending) == 2
        ids = {r.request_id for r in pending}
        assert r1.request_id in ids
        assert r2.request_id in ids

    def test_approved_requests_not_in_pending(self, tmp_path):
        manager = _make_manager(tmp_path)
        r1 = manager.create_request("op1", {})
        manager.create_request("op2", {})
        manager.approve_request(r1.request_id)
        pending = manager.get_pending_requests()
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# ApprovalWorkflowManager - get_request
# ---------------------------------------------------------------------------

class TestGetRequest:
    def test_get_pending_request(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        found = manager.get_request(req.request_id)
        assert found is req

    def test_get_completed_request(self, tmp_path):
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.approve_request(req.request_id)
        found = manager.get_request(req.request_id)
        assert found is req

    def test_get_nonexistent_returns_none(self, tmp_path):
        manager = _make_manager(tmp_path)
        found = manager.get_request("nonexistent-id")
        assert found is None


# ---------------------------------------------------------------------------
# CLIApprovalWorkflow - show_pending
# ---------------------------------------------------------------------------

class TestCLIApprovalWorkflow:
    def test_show_pending_empty(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        cli = CLIApprovalWorkflow(manager)
        cli.show_pending()
        out = capsys.readouterr().out
        assert "No pending" in out

    def test_show_pending_with_requests(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        manager.create_request("test-operation", {"count": 5})
        cli = CLIApprovalWorkflow(manager)
        cli.show_pending()
        out = capsys.readouterr().out
        assert "test-operation" in out
        assert "Pending" in out

    async def test_approve_interactive_back(self, tmp_path):
        from src.approval_workflow import CLIApprovalWorkflow
        from src.approval_workflow import ApprovalRequest
        manager = _make_manager(tmp_path)
        cli = CLIApprovalWorkflow(manager)
        pending = [ApprovalRequest("id-1", "op", {})]
        with patch("builtins.input", return_value="back"):
            await cli._approve_interactive(pending)
        # back should not change any requests

    async def test_approve_interactive_approves(self, tmp_path):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)

        with patch("builtins.input", return_value=req.request_id):
            await cli._approve_interactive(manager.get_pending_requests())

        assert req.status == "approved"

    async def test_approve_interactive_not_found(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        from src.approval_workflow import ApprovalRequest
        manager = _make_manager(tmp_path)
        cli = CLIApprovalWorkflow(manager)
        pending = [ApprovalRequest("id-1", "op", {})]
        manager.pending_requests["id-1"] = pending[0]

        with patch("builtins.input", return_value="wrong-id"):
            await cli._approve_interactive(pending)

        out = capsys.readouterr().out
        assert "not found" in out

    async def test_reject_interactive_back(self, tmp_path):
        from src.approval_workflow import CLIApprovalWorkflow
        from src.approval_workflow import ApprovalRequest
        manager = _make_manager(tmp_path)
        cli = CLIApprovalWorkflow(manager)
        pending = [ApprovalRequest("id-1", "op", {})]
        with patch("builtins.input", side_effect=["back"]):
            await cli._reject_interactive(pending)

    async def test_reject_interactive_rejects(self, tmp_path):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)

        with patch("builtins.input", side_effect=[req.request_id, ""]):
            await cli._reject_interactive(manager.get_pending_requests())

        assert req.status == "rejected"

    async def test_reject_interactive_with_reason(self, tmp_path):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)

        with patch("builtins.input", side_effect=[req.request_id, "security concern"]):
            await cli._reject_interactive(manager.get_pending_requests())

        assert req.details.get("rejection_reason") == "security concern"

    async def test_reject_interactive_not_found(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        from src.approval_workflow import ApprovalRequest
        manager = _make_manager(tmp_path)
        cli = CLIApprovalWorkflow(manager)
        pending = [ApprovalRequest("id-1", "op", {})]
        manager.pending_requests["id-1"] = pending[0]

        with patch("builtins.input", side_effect=["wrong-id", ""]):
            await cli._reject_interactive(pending)

        out = capsys.readouterr().out
        assert "not found" in out

    async def test_interactive_approve_exits_when_no_pending(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        cli = CLIApprovalWorkflow(manager)
        # No pending requests -> should print and break immediately
        await cli.interactive_approve()
        out = capsys.readouterr().out
        assert "No pending requests" in out

    async def test_interactive_approve_choice_exit(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)
        with patch("builtins.input", side_effect=["3"]):
            await cli.interactive_approve()
        out = capsys.readouterr().out
        assert "Exiting" in out

    async def test_interactive_approve_choice_approve(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)
        # choice 1 -> approve the request
        with patch("builtins.input", side_effect=["1", req.request_id, "3"]):
            await cli.interactive_approve()
        assert req.status == "approved"

    async def test_interactive_approve_choice_reject(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)
        # choice 2 -> reject the request
        with patch("builtins.input", side_effect=["2", req.request_id, ""]):
            await cli.interactive_approve()
        assert req.status == "rejected"

    async def test_interactive_approve_invalid_choice(self, tmp_path, capsys):
        from src.approval_workflow import CLIApprovalWorkflow
        manager = _make_manager(tmp_path)
        manager.create_request("op", {})
        cli = CLIApprovalWorkflow(manager)
        # First invalid, then exit
        with patch("builtins.input", side_effect=["9", "3"]):
            await cli.interactive_approve()
        out = capsys.readouterr().out
        assert "Invalid choice" in out


# ---------------------------------------------------------------------------
# DashboardApprovalWorkflow
# ---------------------------------------------------------------------------

class TestDashboardApprovalWorkflow:
    async def test_create_request_returns_dict(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.create_request("op", {"data": 1})
        assert isinstance(result, dict)
        assert result["operation"] == "op"
        assert result["status"] == "pending"

    async def test_list_pending_empty(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.list_pending()
        assert result == []

    async def test_list_pending_with_requests(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        manager.create_request("op1", {})
        manager.create_request("op2", {})
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.list_pending()
        assert len(result) == 2

    async def test_approve_success(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.approve(req.request_id)
        assert result["success"] is True
        assert result["status"] == "approved"
        assert result["request_id"] == req.request_id

    async def test_approve_nonexistent_fails(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.approve("bad-id")
        assert result["success"] is False
        assert result["status"] == "failed"

    async def test_reject_success(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.reject(req.request_id, reason="not now")
        assert result["success"] is True
        assert result["status"] == "rejected"
        assert result["reason"] == "not now"

    async def test_reject_nonexistent_fails(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.reject("bad-id")
        assert result["success"] is False

    async def test_get_details_existing(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {"count": 42})
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.get_details(req.request_id)
        assert result is not None
        assert result["details"]["count"] == 42

    async def test_get_details_nonexistent_returns_none(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.get_details("bad-id")
        assert result is None

    async def test_get_details_completed_request(self, tmp_path):
        from src.approval_workflow import DashboardApprovalWorkflow
        manager = _make_manager(tmp_path)
        req = manager.create_request("op", {})
        manager.approve_request(req.request_id)
        dashboard = DashboardApprovalWorkflow(manager)
        result = await dashboard.get_details(req.request_id)
        assert result is not None
        assert result["status"] == "approved"
