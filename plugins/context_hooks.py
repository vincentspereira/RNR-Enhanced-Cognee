"""
Enhanced Cognee - Context Injection Hooks

Provides hooks for automatic context injection in Claude Code.
Implements SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd hooks.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ContextInjectionHooks:
    """
    Context injection hooks for Claude Code integration.

    Provides lifecycle hooks for automatic session management and context injection.
    """

    def __init__(self, plugin):
        """
        Initialize context injection hooks.

        Args:
            plugin: EnhancedCogneePlugin instance
        """
        self.plugin = plugin
        self.session_config = {
            "auto_start_session": True,
            "auto_inject_context": True,
            "max_context_tokens": 2000,
            "end_session_on_stop": True
        }
        self.hooks_enabled = True

    async def on_session_start(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Hook called when a Claude Code session starts.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            metadata: Optional session metadata

        Returns:
            Session ID
        """
        if not self.hooks_enabled:
            return None

        logger.info(f"Session start hook: user={user_id}, agent={agent_id}")

        # Auto-start session if enabled
        if self.session_config["auto_start_session"]:
            session_id = await self.plugin.start_session(
                user_id=user_id,
                agent_id=agent_id,
                metadata=metadata
            )
            return session_id

        return None

    async def on_user_prompt_submit(
        self,
        prompt: str,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ) -> str:
        """
        Hook called before user prompt is submitted to Claude.

        Injects session context into the prompt.

        Args:
            prompt: Original user prompt
            user_id: User identifier
            agent_id: Agent identifier

        Returns:
            Prompt with context injected (if enabled)
        """
        if not self.hooks_enabled:
            return prompt

        logger.debug(f"User prompt submit hook: prompt length={len(prompt)}")

        # Auto-start session if none active
        await self.plugin.auto_start_session(user_id, agent_id)

        # Inject context if enabled
        if self.session_config["auto_inject_context"]:
            max_tokens = self.session_config["max_context_tokens"]
            enhanced_prompt = await self.plugin.inject_context_to_prompt(
                prompt,
                max_tokens=max_tokens
            )

            if enhanced_prompt != prompt:
                logger.info(f"Context injected: +{len(enhanced_prompt) - len(prompt)} chars")

            return enhanced_prompt

        return prompt

    async def on_post_tool_use(
        self,
        tool_name: str,
        tool_result: Any,
        context: Optional[Dict] = None
    ):
        """
        Hook called after tool execution.

        This is the main entry point for automatic memory capture.
        Delegates to the plugin's post_tool_use_hook.

        Args:
            tool_name: Name of the tool that was used
            tool_result: Result returned by the tool
            context: Additional context about the tool usage
        """
        if not self.hooks_enabled:
            return

        # Delegate to plugin
        await self.plugin.post_tool_use_hook(tool_name, tool_result, context)

    async def on_session_end(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code",
        generate_summary: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Hook called when a Claude Code session ends.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
            generate_summary: Whether to generate session summary

        Returns:
            Session info if ended successfully
        """
        if not self.hooks_enabled:
            return None

        logger.info(f"Session end hook: user={user_id}, agent={agent_id}")

        # End current session
        session_info = await self.plugin.end_session()

        if session_info:
            logger.info(f"Session ended: {session_info.get('session_id')}")

        return session_info

    async def on_stop(
        self,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ):
        """
        Hook called when Claude Code stops/exits.

        Args:
            user_id: User identifier
            agent_id: Agent identifier
        """
        if not self.hooks_enabled:
            return

        logger.info(f"Stop hook: user={user_id}, agent={agent_id}")

        # End session if enabled
        if self.session_config["end_session_on_stop"]:
            await self.on_session_end(user_id, agent_id)

    def configure(self, config: Dict[str, Any]):
        """
        Configure hook behavior.

        Args:
            config: Configuration dictionary
        """
        self.session_config.update(config)
        logger.info(f"Hook configuration updated: {self.session_config}")

    def enable(self):
        """Enable all hooks."""
        self.hooks_enabled = True
        logger.info("Context injection hooks enabled")

    def disable(self):
        """Disable all hooks."""
        self.hooks_enabled = False
        logger.info("Context injection hooks disabled")


class SessionSummaryGenerator:
    """
    Generates session summaries for context continuity.

    Provides automatic summarization of long sessions.
    """

    def __init__(self, plugin):
        """
        Initialize session summary generator.

        Args:
            plugin: EnhancedCogneePlugin instance
        """
        self.plugin = plugin
        self.summary_config = {
            "auto_summarize": True,
            "max_memories_before_summary": 20,
            "summary_interval_minutes": 30,
            "include_summary_in_context": True
        }

    async def should_generate_summary(self, session_id: str) -> bool:
        """
        Check if session should be summarized.

        Args:
            session_id: Session ID

        Returns:
            True if summary should be generated
        """
        if not self.summary_config["auto_summarize"]:
            return False

        if not self.plugin.session_manager:
            return False

        # Get session context
        session_context = await self.plugin.session_manager.get_session_context(
            session_id,
            include_memories=True
        )

        if not session_context or "error" in session_context:
            return False

        # Check memory count
        memory_count = len(session_context.get("memories", []))

        if memory_count >= self.summary_config["max_memories_before_summary"]:
            logger.info(f"Session {session_id} has {memory_count} memories - should summarize")
            return True

        return False

    async def generate_summary(
        self,
        session_id: str
    ) -> Optional[str]:
        """
        Generate session summary.

        Args:
            session_id: Session ID

        Returns:
            Generated summary or None
        """
        if not self.plugin.session_manager:
            return None

        logger.info(f"Generating summary for session: {session_id}")

        summary = await self.plugin.session_manager.generate_session_summary(session_id)

        if summary:
            logger.info(f"Summary generated: {len(summary)} chars")
        else:
            logger.warning(f"Summary generation failed for session: {session_id}")

        return summary

    def configure(self, config: Dict[str, Any]):
        """
        Configure summary generation behavior.

        Args:
            config: Configuration dictionary
        """
        self.summary_config.update(config)
        logger.info(f"Summary configuration updated: {self.summary_config}")


class AutoSessionManager:
    """
    Automatic session lifecycle manager.

    Manages session start, context injection, and end automatically.
    """

    def __init__(self, plugin):
        """
        Initialize auto session manager.

        Args:
            plugin: EnhancedCogneePlugin instance
        """
        self.plugin = plugin
        self.hooks = ContextInjectionHooks(plugin)
        self.summary_generator = SessionSummaryGenerator(plugin)
        self.active = False

    async def start(self):
        """Start automatic session management."""
        self.active = True
        self.hooks.enable()
        logger.info("Auto session manager started")

    async def stop(self):
        """Stop automatic session management."""
        self.active = False
        self.hooks.disable()
        logger.info("Auto session manager stopped")

    async def process_prompt(
        self,
        prompt: str,
        user_id: str = "default",
        agent_id: str = "claude-code"
    ) -> str:
        """
        Process user prompt with automatic context injection.

        Args:
            prompt: User prompt
            user_id: User identifier
            agent_id: Agent identifier

        Returns:
            Enhanced prompt with context
        """
        if not self.active:
            return prompt

        return await self.hooks.on_user_prompt_submit(
            prompt,
            user_id=user_id,
            agent_id=agent_id
        )

    async def process_tool_result(
        self,
        tool_name: str,
        tool_result: Any,
        context: Optional[Dict] = None
    ):
        """
        Process tool result with automatic memory capture.

        Args:
            tool_name: Tool name
            tool_result: Tool result
            context: Additional context
        """
        if not self.active:
            return

        await self.hooks.on_post_tool_use(tool_name, tool_result, context)

        # Check if session should be summarized
        session_id = await self.plugin.get_active_session()
        if session_id and await self.summary_generator.should_generate_summary(session_id):
            await self.summary_generator.generate_summary(session_id)

    async def end_session(self) -> Optional[Dict[str, Any]]:
        """End the current session."""
        if not self.active:
            return None

        return await self.hooks.on_session_end()

    def configure(self, config: Dict[str, Any]):
        """
        Configure auto session manager.

        Args:
            config: Configuration dictionary with 'hooks' and 'summary' sections
        """
        if "hooks" in config:
            self.hooks.configure(config["hooks"])

        if "summary" in config:
            self.summary_generator.configure(config["summary"])

        logger.info(f"Auto session manager configured")


# Example usage function
async def example_auto_session_workflow():
    """
    Example workflow demonstrating automatic session management.

    This shows how Claude Code would use the auto session manager.
    """
    # This would be initialized with actual plugin instance
    # plugin = EnhancedCogneePlugin()
    # auto_manager = AutoSessionManager(plugin)

    # Start auto session management
    # await auto_manager.start()

    # Claude Code submits user prompt
    # original_prompt = "How do I implement X?"
    # enhanced_prompt = await auto_manager.process_prompt(original_prompt)
    # Send enhanced_prompt to Claude...

    # Claude uses a tool
    # tool_result = await some_tool()
    # await auto_manager.process_tool_result("code_edit", tool_result, context)

    # Session ends
    # await auto_manager.end_session()
    pass


async def main():
    """Test context injection hooks."""
    print("Context injection hooks require plugin instance")
    print("Use with EnhancedCogneePlugin instance")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
