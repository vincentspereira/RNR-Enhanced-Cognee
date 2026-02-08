"""
Enhanced Cognee - Approval Workflow System

Provides approval workflow for automated operations.
Supports CLI and dashboard-based approval.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ApprovalRequest:
    """Approval request for automated operation."""

    def __init__(
        self,
        request_id: str,
        operation: str,
        details: Dict[str, Any],
        created_at: Optional[str] = None
    ):
        """
        Initialize approval request.

        Args:
            request_id: Unique request ID
            operation: Operation name
            details: Operation details
            created_at: Creation timestamp (ISO format)
        """
        self.request_id = request_id
        self.operation = operation
        self.details = details
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.status = "pending"  # pending, approved, rejected
        self.decided_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "operation": self.operation,
            "details": self.details,
            "created_at": self.created_at,
            "status": self.status,
            "decided_at": self.decided_at
        }


class ApprovalWorkflowManager:
    """
    Manager for approval workflows.

    Handles creation, tracking, and execution of approval requests.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize approval workflow manager.

        Args:
            storage_path: Path to store approval requests
        """
        self.storage_path = storage_path or Path("data/approvals")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.completed_requests: List[ApprovalRequest] = []

    def create_request(
        self,
        operation: str,
        details: Dict[str, Any]
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            operation: Operation name
            details: Operation details

        Returns:
            ApprovalRequest object
        """
        import uuid

        request_id = str(uuid.uuid4())
        request = ApprovalRequest(request_id, operation, details)

        self.pending_requests[request_id] = request
        self._save_request(request)

        logger.info(f"Created approval request: {request_id} for {operation}")

        return request

    def approve_request(self, request_id: str) -> bool:
        """
        Approve an approval request.

        Args:
            request_id: Request ID to approve

        Returns:
            True if approved successfully
        """
        request = self.pending_requests.get(request_id)
        if not request:
            logger.error(f"Request not found: {request_id}")
            return False

        request.status = "approved"
        request.decided_at = datetime.now(timezone.utc).isoformat()

        # Move to completed
        self.completed_requests.append(request)
        del self.pending_requests[request_id]

        self._save_request(request)
        logger.info(f"Approved request: {request_id}")

        return True

    def reject_request(self, request_id: str, reason: Optional[str] = None) -> bool:
        """
        Reject an approval request.

        Args:
            request_id: Request ID to reject
            reason: Optional rejection reason

        Returns:
            True if rejected successfully
        """
        request = self.pending_requests.get(request_id)
        if not request:
            logger.error(f"Request not found: {request_id}")
            return False

        request.status = "rejected"
        request.decided_at = datetime.now(timezone.utc).isoformat()
        if reason:
            request.details["rejection_reason"] = reason

        # Move to completed
        self.completed_requests.append(request)
        del self.pending_requests[request_id]

        self._save_request(request)
        logger.info(f"Rejected request: {request_id}")

        return True

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self.pending_requests.values())

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get request by ID."""
        if request_id in self.pending_requests:
            return self.pending_requests[request_id]

        for request in self.completed_requests:
            if request.request_id == request_id:
                return request

        return None

    def _save_request(self, request: ApprovalRequest):
        """Save request to storage."""
        request_file = self.storage_path / f"{request.request_id}.json"
        request_file.write_text(json.dumps(request.to_dict(), indent=2))


class CLIApprovalWorkflow:
    """
    CLI-based approval workflow interface.

    Provides interactive command-line interface for approving operations.
    """

    def __init__(self, workflow_manager: ApprovalWorkflowManager):
        """
        Initialize CLI approval workflow.

        Args:
            workflow_manager: Approval workflow manager
        """
        self.manager = workflow_manager

    def show_pending(self):
        """Show pending approval requests."""
        pending = self.manager.get_pending_requests()

        if not pending:
            print("No pending approval requests")
            return

        print("=" * 60)
        print("Pending Approval Requests")
        print("=" * 60)
        print()

        for request in pending:
            print(f"Request ID: {request.request_id}")
            print(f"Operation: {request.operation}")
            print(f"Created: {request.created_at}")
            print()
            print("Details:")
            print(json.dumps(request.details, indent=2))
            print()
            print("-" * 60)
            print()

    async def interactive_approve(self):
        """Run interactive approval session."""
        while True:
            self.show_pending()

            pending = self.manager.get_pending_requests()
            if not pending:
                print("No pending requests. Exiting.")
                break

            print("Options:")
            print("  1. Approve a request")
            print("  2. Reject a request")
            print("  3. Exit")
            print()

            choice = input("Enter choice (1-3): ").strip()

            if choice == "1":
                await self._approve_interactive(pending)
            elif choice == "2":
                await self._reject_interactive(pending)
            elif choice == "3":
                print("Exiting...")
                break
            else:
                print("Invalid choice")

    async def _approve_interactive(self, pending: List[ApprovalRequest]):
        """Interactive approve flow."""
        print("\nEnter request ID to approve (or 'back' to return):")
        request_id = input("> ").strip()

        if request_id == "back":
            return

        if self.manager.approve_request(request_id):
            print(f"Approved: {request_id}")
        else:
            print(f"Request not found: {request_id}")

    async def _reject_interactive(self, pending: List[ApprovalRequest]):
        """Interactive reject flow."""
        print("\nEnter request ID to reject (or 'back' to return):")
        request_id = input("> ").strip()

        if request_id == "back":
            return

        reason = input("Reason (optional): ").strip() or None

        if self.manager.reject_request(request_id, reason):
            print(f"Rejected: {request_id}")
        else:
            print(f"Request not found: {request_id}")


class DashboardApprovalWorkflow:
    """
    Dashboard-based approval workflow interface.

    Provides REST API endpoints for dashboard integration.
    """

    def __init__(self, workflow_manager: ApprovalWorkflowManager):
        """
        Initialize dashboard approval workflow.

        Args:
            workflow_manager: Approval workflow manager
        """
        self.manager = workflow_manager

    async def create_request(
        self,
        operation: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create approval request via API.

        Args:
            operation: Operation name
            details: Operation details

        Returns:
            Created request as dictionary
        """
        request = self.manager.create_request(operation, details)
        return request.to_dict()

    async def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending requests via API."""
        pending = self.manager.get_pending_requests()
        return [r.to_dict() for r in pending]

    async def approve(self, request_id: str) -> Dict[str, Any]:
        """Approve request via API."""
        success = self.manager.approve_request(request_id)
        return {
            "request_id": request_id,
            "success": success,
            "status": "approved" if success else "failed"
        }

    async def reject(
        self,
        request_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject request via API."""
        success = self.manager.reject_request(request_id, reason)
        return {
            "request_id": request_id,
            "success": success,
            "status": "rejected" if success else "failed",
            "reason": reason
        }

    async def get_details(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get request details via API."""
        request = self.manager.get_request(request_id)
        return request.to_dict() if request else None


async def main():
    """Test approval workflow."""
    # Create workflow manager
    manager = ApprovalWorkflowManager()

    # Create test requests
    request1 = manager.create_request(
        "auto_deduplicate",
        {
            "duplicates_found": 5,
            "memories_affected": 12,
            "storage_saved_mb": 2.5
        }
    )

    request2 = manager.create_request(
        "summarize_old_memories",
        {
            "memories_to_summarize": 20,
            "estimated_time_minutes": 5
        }
    )

    # Show CLI interface
    cli = CLIApprovalWorkflow(manager)
    cli.show_pending()

    # Approve one request
    manager.approve_request(request1.request_id)

    print("\nAfter approval:")
    cli.show_pending()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
