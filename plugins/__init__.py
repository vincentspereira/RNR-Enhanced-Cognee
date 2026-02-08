"""
Enhanced Cognee - Claude Code Plugins

This package contains plugins for Enhanced Cognee integration with Claude Code.

Plugins:
- claude_code_plugin: Automatic memory capture from Claude Code actions
- context_hooks: Context injection hooks for Claude Code sessions
- memory_extractor: Observation extraction from tool results
- config_loader: Configuration management

Usage:
    from plugins.claude_code_plugin import EnhancedCogneePlugin
    from plugins.context_hooks import AutoSessionManager

    plugin = EnhancedCogneePlugin()
    auto_manager = AutoSessionManager(plugin)
    await auto_manager.start()

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

from .claude_code_plugin import EnhancedCogneePlugin, get_plugin, init_plugin
from .memory_extractor import MemoryExtractor
from .config_loader import ConfigLoader
from .context_hooks import ContextInjectionHooks, SessionSummaryGenerator, AutoSessionManager

__all__ = [
    "EnhancedCogneePlugin",
    "get_plugin",
    "init_plugin",
    "MemoryExtractor",
    "ConfigLoader",
    "ContextInjectionHooks",
    "SessionSummaryGenerator",
    "AutoSessionManager"
]
