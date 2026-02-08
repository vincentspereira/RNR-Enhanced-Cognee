"""
Enhanced Cognee - Memory Extractor for Claude Code Plugin

This module extracts observations from Claude Code tool usage to automatically
create meaningful memories.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import re
import json
import fnmatch
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """
    Extracts observations from Claude Code tool results.

    Analyzes tool usage to identify meaningful information worth remembering.
    """

    # Tools that commonly produce memory-worthy results
    MEMORY_WORTHY_TOOLS = {
        # Code editing tools
        "code_writer",
        "code_edit",
        "file_writer",
        "file_edit",

        # Terminal/tools
        "run_terminal",
        "execute_command",

        # Reading/analysis tools
        "read_file",
        "grep",
        "search_files",

        # Build tools
        "build",
        "test",
        "compile",

        # Git operations
        "git_commit",
        "git_push",
        "git_pull",
    }

    # Patterns that indicate low importance (should not auto-capture)
    LOW_IMPORTANCE_PATTERNS = [
        r"^[\s\-]*$",  # Empty or whitespace only
        r"^OK$",  # Simple success messages
        r"^Done$",  # Simple completion messages
        r"^(test|example|demo)[\s\d]*$",  # Test/example code
        r"^\/\/.*$",  # Comment-only lines
        r"^#.*$",  # Comment-only lines
    ]

    # Patterns that indicate high importance
    HIGH_IMPORTANCE_PATTERNS = [
        r"error",  # Error messages
        r"fix",  # Fixes or solutions
        r"bug",  # Bug reports or fixes
        r"implement",  # Implementation notes
        r"configur",  # Configuration changes
        r"setup",  # Setup instructions
        r"deploy",  # Deployment notes
        r"architect",  # Architecture decisions
        r"design",  # Design decisions
    ]

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize memory extractor.

        Args:
            config: Configuration from automation_config.json
        """
        self.config = config
        self.auto_capture_config = config.get("auto_memory_capture", {})

        # Get settings
        self.enabled = self.auto_capture_config.get("enabled", False)
        self.capture_on = self.auto_capture_config.get("capture_on", [])
        self.exclude_patterns = self.auto_capture_config.get("exclude_patterns", [])
        self.importance_threshold = self.auto_capture_config.get("importance_threshold", 0.3)
        self.max_memory_length = self.auto_capture_config.get("max_memory_length", 5000)

    def should_capture_tool_use(
        self,
        tool_name: str,
        tool_result: Any,
        context: Optional[Dict] = None
    ) -> bool:
        """
        Determine if tool usage should be captured as a memory.

        Args:
            tool_name: Name of the tool that was used
            tool_result: Result from the tool
            context: Additional context

        Returns:
            True if should capture, False otherwise
        """
        if not self.enabled:
            return False

        # Check if tool is in capture list
        if tool_name not in self.capture_on:
            return False

        # Check if tool is memory-worthy
        if tool_name not in self.MEMORY_WORTHY_TOOLS:
            return False

        # Extract content from result
        content = self._extract_content_from_result(tool_result)
        if not content:
            return False

        # Check exclude patterns
        if self._matches_exclude_patterns(content):
            return False

        # Check length
        if len(content) < 50:  # Too short
            return False

        if len(content) > self.max_memory_length * 2:  # Way too long
            return False

        # Check importance
        importance = self._calculate_importance(content)
        if importance < self.importance_threshold:
            return False

        return True

    def extract_memory(
        self,
        tool_name: str,
        tool_result: Any,
        context: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract memory from tool usage.

        Args:
            tool_name: Name of the tool
            tool_result: Result from the tool
            context: Additional context

        Returns:
            Memory dict with content and metadata, or None
        """
        content = self._extract_content_from_result(tool_result)
        if not content:
            return None

        # Calculate importance
        importance = self._calculate_importance(content)

        # Truncate if too long
        if len(content) > self.max_memory_length:
            content = content[:self.max_memory_length] + "..."

        # Extract metadata
        metadata = self._extract_metadata(tool_name, tool_result, context, importance)

        return {
            "content": content,
            "metadata": json.dumps(metadata)
        }

    def _extract_content_from_result(self, result: Any) -> Optional[str]:
        """
        Extract text content from tool result.

        Args:
            result: Tool result (can be various types)

        Returns:
            Extracted text content or None
        """
        if result is None:
            return None

        # If it's already a string
        if isinstance(result, str):
            return result.strip()

        # If it's a dict with specific fields
        if isinstance(result, dict):
            # Look for common content fields
            for field in ["output", "result", "content", "text", "message"]:
                if field in result and result[field]:
                    return str(result[field]).strip()

            # If no standard field, serialize the whole dict
            if result:
                return json.dumps(result, indent=2)

        # If it's a list, join items
        if isinstance(result, list):
            items = [str(item) for item in result if item]
            if items:
                return "\n".join(items)

        # Fallback: string representation
        try:
            return str(result).strip()
        except Exception:
            return None

    def _calculate_importance(self, content: str) -> float:
        """
        Calculate importance score for content.

        Args:
            content: Text content

        Returns:
            Importance score (0.0 to 1.0)
        """
        if not content:
            return 0.0

        score = 0.3  # Base score

        # Check for high importance patterns
        content_lower = content.lower()
        for pattern in self.HIGH_IMPORTANCE_PATTERNS:
            if re.search(pattern, content_lower):
                score += 0.2
                break

        # Check for low importance patterns
        for pattern in self.LOW_IMPORTANCE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                score -= 0.1

        # Length factor (prefer medium length)
        length = len(content)
        if 100 <= length <= 1000:
            score += 0.1
        elif length < 50 or length > 3000:
            score -= 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def _matches_exclude_patterns(self, content: str) -> bool:
        """
        Check if content matches any exclude patterns.

        Args:
            content: Text content

        Returns:
            True if should exclude
        """
        content_lower = content.lower()

        for pattern in self.exclude_patterns:
            try:
                if fnmatch.fnmatch(content_lower, pattern.lower()):
                    return True
            except (re.error, AttributeError):
                # Invalid regex or glob pattern
                pass

        return False

    def _extract_metadata(
        self,
        tool_name: str,
        tool_result: Any,
        context: Optional[Dict],
        importance: float
    ) -> Dict[str, Any]:
        """
        Extract metadata from tool usage.

        Args:
            tool_name: Name of the tool
            tool_result: Result from tool
            context: Additional context
            importance: Calculated importance score

        Returns:
            Metadata dict
        """
        metadata = {
            "source": "claude_code_plugin",
            "tool_name": tool_name,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "importance_score": round(importance, 2),
            "auto_captured": True
        }

        # Add context if available
        if context:
            if "file_path" in context:
                metadata["file_path"] = context["file_path"]
            if "directory" in context:
                metadata["directory"] = context["directory"]
            if "agent_id" in context:
                metadata["agent_id"] = context["agent_id"]

        # Extract file paths from content
        if isinstance(tool_result, str):
            file_paths = self._extract_file_paths(tool_result)
            if file_paths:
                metadata["file_paths"] = file_paths

        return metadata

    def _extract_file_paths(self, content: str) -> List[str]:
        """
        Extract file paths from content.

        Args:
            content: Text content

        Returns:
            List of file paths found
        """
        # Common file path patterns
        patterns = [
            r'[\w\-./]+\.py',  # Python files
            r'[\w\-./]+\.js',  # JavaScript files
            r'[\w\-./]+\.ts',  # TypeScript files
            r'[\w\-./]+\.json',  # JSON files
            r'[\w\-./]+\.ya?ml',  # YAML files
            r'[\w\-./]+\.md',  # Markdown files
            r'[\w\-./]+\.txt',  # Text files
            r'[\w\-./]+/',  # Directories
        ]

        file_paths = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            file_paths.extend(matches)

        # Remove duplicates and return
        return list(set(file_paths))
