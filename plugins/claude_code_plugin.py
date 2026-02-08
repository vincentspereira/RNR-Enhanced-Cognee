"""
Enhanced Cognee - Claude Code Plugin for Auto Memory Capture

This plugin integrates with Claude Code to automatically capture observations
from user actions and add them as memories.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import logging

# Import Enhanced Cognee components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audit_logger import AuditLogger, AuditOperationType
from .memory_extractor import MemoryExtractor
from .config_loader import ConfigLoader

# Import session management
try:
    from session_manager import SessionManager, ContextInjector
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False
    logging.warning("Session manager not available - session features disabled")

logger = logging.getLogger(__name__)


class EnhancedCogneePlugin:
    """
    Claude Code plugin for automatic memory capture.

    Hooks into Claude Code's tool usage to automatically create memories
    from meaningful user actions.
    """

    def __init__(
        self,
        config_path: str = "automation_config.json",
        mcp_server_url: Optional[str] = None,
        db_pool: Optional[Any] = None,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize the plugin.

        Args:
            config_path: Path to automation config file
            mcp_server_url: URL of MCP server (for add_memory calls)
            db_pool: PostgreSQL connection pool for session management
            llm_client: LLM client for summaries
        """
        self.config_path = config_path
        self.mcp_server_url = mcp_server_url
        self.db_pool = db_pool
        self.llm_client = llm_client

        # Load configuration
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.load_config()

        # Initialize memory extractor
        self.extractor = MemoryExtractor(self.config)

        # Initialize audit logger
        self.audit_logger = None  # Will be initialized when needed

        # Initialize session manager
        self.session_manager: Optional[SessionManager] = None
        self.context_injector: Optional[ContextInjector] = None
        self.current_session_id: Optional[str] = None

        if SESSION_MANAGER_AVAILABLE and db_pool:
            self.session_manager = SessionManager(db_pool, llm_client)
            self.context_injector = ContextInjector(self.session_manager)
            logger.info("Session manager initialized")

        # Statistics
        self.stats = {
            "total_tool_uses": 0,
            "memories_created": 0,
            "memories_skipped": 0,
            "errors": 0,
            "sessions_started": 0,
            "sessions_ended": 0,
            "contexts_injected": 0
        }

        logger.info("Enhanced Cognee Plugin initialized")

    async def post_tool_use_hook(
        self,
        tool_name: str,
        tool_result: Any,
        context: Optional[Dict] = None
    ):
        """
        Hook called after tool execution.

        This is the main entry point for the plugin. Claude Code will call this
        after every tool usage.

        Args:
            tool_name: Name of the tool that was used
            tool_result: Result returned by the tool
            context: Additional context about the tool usage
        """
        self.stats["total_tool_uses"] += 1

        try:
            # Check if we should capture this
            if not self.extractor.should_capture_tool_use(tool_name, tool_result, context):
                logger.debug(f"Skipping tool: {tool_name}")
                self.stats["memories_skipped"] += 1
                return

            # Extract memory
            memory = self.extractor.extract_memory(tool_name, tool_result, context)
            if not memory:
                logger.debug(f"No memory extracted from: {tool_name}")
                self.stats["memories_skipped"] += 1
                return

            # Check for duplicates before adding
            duplicate_check = await self._check_duplicate(memory["content"])
            if duplicate_check.get("is_duplicate", False):
                logger.info(f"Skipping duplicate memory from: {tool_name}")
                self.stats["memories_skipped"] += 1
                return

            # Add memory and associate with session
            memory_id = await self._add_memory(memory)

            # Associate with current session if active
            if memory_id and self.session_manager and self.current_session_id:
                await self.session_manager.add_memory_to_session(
                    self.current_session_id,
                    memory_id
                )
                logger.debug(f"Associated memory {memory_id} with session {self.current_session_id}")

            # Log success
            self.stats["memories_created"] += 1
            logger.info(f"Auto-captured memory from {tool_name} (length: {len(memory['content'])} chars)")

            # Audit log the capture
            if self.audit_logger:
                await self.audit_logger.log(
                    operation_type=AuditOperationType.MEMORY_ADD,
                    agent_id=context.get("agent_id", "claude_code_plugin"),
                    status="success",
                    details={
                        "source": "auto_capture",
                        "tool_name": tool_name,
                        "memory_length": len(memory["content"])
                    },
                    metadata=json.dumps({
                        "importance_score": memory.get("metadata", {}).get("importance_score", 0.5)
                    })
                )

        except Exception as e:
            logger.error(f"Error in post_tool_use_hook for {tool_name}: {e}")
            self.stats["errors"] += 1

    async def _check_duplicate(self, content: str) -> Dict[str, Any]:
        """
        Check if content is a duplicate.

        Args:
            content: Memory content to check

        Returns:
            Dict with is_duplicate boolean and details
        """
        # This would call the MCP check_duplicate tool
        # For now, return False
        # TODO: Integrate with MCP server
        return {"is_duplicate": False, "confidence": 0.0}

    async def _add_memory(self, memory: Dict[str, Any]):
        """
        Add memory via MCP server.

        Args:
            memory: Memory dict with content and metadata
        """
        # This would call the MCP add_memory tool
        # TODO: Integrate with MCP server
        logger.debug(f"Would add memory: {memory['content'][:100]}...")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get plugin statistics.

        Returns:
            Statistics dict
        """
        return {
            **self.stats,
            "config": {
                "enabled": self.extractor.enabled,
                "capture_tools": self.extractor.capture_on,
                "exclude_patterns": len(self.extractor.exclude_patterns)
            },
            "session": {
                "current_session_id": self.current_session_id,
                "session_manager_available": self.session_manager is not None
            }
        }

    async def reload_config(self):
        """Reload configuration from file."""
        self.config = self.config_loader.load_config()
        self.extractor = MemoryExtractor(self.config)
        logger.info("Plugin configuration reloaded")

    # Session Management Methods

    async def start_session(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Start a new Claude Code session.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            metadata: Optional session metadata

        Returns:
            Session ID or None if session manager unavailable
        """
        if not self.session_manager:
            logger.warning("Session manager not available")
            return None

        session_id = await self.session_manager.start_session(
            user_id=user_id,
            agent_id=agent_id,
            metadata=metadata
        )

        self.current_session_id = session_id
        self.stats["sessions_started"] += 1

        logger.info(f"Started session: {session_id}")

        # Log session start
        if self.audit_logger:
            await self.audit_logger.log(
                operation_type=AuditOperationType.MEMORY_ADD,
                agent_id=agent_id,
                status="success",
                details={
                    "action": "session_start",
                    "session_id": session_id
                }
            )

        return session_id

    async def end_session(
        self,
        summary: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        End the current session.

        Args:
            summary: Optional session summary

        Returns:
            Session info or None if no active session
        """
        if not self.session_manager or not self.current_session_id:
            logger.warning("No active session to end")
            return None

        session_info = await self.session_manager.end_session(
            self.current_session_id,
            summary=summary
        )

        self.stats["sessions_ended"] += 1
        logger.info(f"Ended session: {self.current_session_id}")

        # Log session end
        if self.audit_logger:
            await self.audit_logger.log(
                operation_type=AuditOperationType.MEMORY_ADD,
                agent_id=session_info.get("agent_id", "claude-code"),
                status="success",
                details={
                    "action": "session_end",
                    "session_id": self.current_session_id
                }
            )

        self.current_session_id = None
        return session_info

    async def get_session_context(
        self,
        max_tokens: int = 2000
    ) -> str:
        """
        Get context for current session.

        Args:
            max_tokens: Maximum tokens for context

        Returns:
            Formatted context string
        """
        if not self.context_injector or not self.current_session_id:
            return ""

        context = await self.context_injector.inject_context(
            self.current_session_id,
            max_tokens=max_tokens
        )

        self.stats["contexts_injected"] += 1

        return context

    async def inject_context_to_prompt(
        self,
        prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """
        Inject session context into a prompt.

        Args:
            prompt: Original prompt
            max_tokens: Maximum tokens for context

        Returns:
            Prompt with context prepended
        """
        context = await self.get_session_context(max_tokens)

        if not context:
            return prompt

        return f"{context}\n\n{prompt}"

    async def add_memory_with_session(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Add memory and associate with current session.

        Args:
            content: Memory content
            metadata: Optional metadata

        Returns:
            Memory ID or None
        """
        # Add memory via MCP
        memory_id = await self._add_memory({
            "content": content,
            "metadata": json.dumps(metadata or {})
        })

        # Associate with session if active
        if memory_id and self.session_manager and self.current_session_id:
            await self.session_manager.add_memory_to_session(
                self.current_session_id,
                memory_id
            )

        return memory_id

    async def get_active_session(self) -> Optional[str]:
        """
        Get the current active session ID.

        Returns:
            Session ID or None
        """
        return self.current_session_id

    async def auto_start_session(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ):
        """
        Automatically start a session if none is active.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
        """
        if self.current_session_id:
            # Session already active
            return

        if self.session_manager:
            # Try to get existing active session
            active_session = await self.session_manager.get_active_session(
                user_id=user_id,
                agent_id=agent_id
            )

            if active_session:
                self.current_session_id = active_session
                logger.info(f"Resumed existing session: {active_session}")
            else:
                # Start new session
                await self.start_session(user_id, agent_id)


# Global plugin instance
_plugin_instance: Optional[EnhancedCogneePlugin] = None


def get_plugin() -> Optional[EnhancedCogneePlugin]:
    """Get the global plugin instance."""
    return _plugin_instance


def init_plugin(
    config_path: str = "automation_config.json",
    mcp_server_url: Optional[str] = None
) -> EnhancedCogneePlugin:
    """
    Initialize the global plugin instance.

    Args:
        config_path: Path to automation config
        mcp_server_url: MCP server URL

    Returns:
        Plugin instance
    """
    global _plugin_instance
    _plugin_instance = EnhancedCogneePlugin(config_path, mcp_server_url)
    return _plugin_instance


# Example hook function (would be called by Claude Code)
async def example_post_tool_use_hook(
    tool_name: str,
    tool_result: Any,
    context: Optional[Dict] = None
):
    """
    Example hook function that Claude Code would call.

    This demonstrates how the plugin integrates with Claude Code.
    """
    plugin = get_plugin()
    if plugin:
        await plugin.post_tool_use_hook(tool_name, tool_result, context)
