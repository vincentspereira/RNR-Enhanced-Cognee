"""
Enhanced Cognee - Document Auto-Processor

Automatically processes documents when added to the project.
Supports .md, .txt, .pdf, .rst files.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import fnmatch
import json
import logging
import os
from pathlib import Path
from typing import Set, Optional, Dict, Any, List
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)


class DocumentProcessor(FileSystemEventHandler):
    """
    File system event handler for automatic document processing.

    Watches for new documents and automatically cognifies them.
    """

    def __init__(
        self,
        mcp_client,
        watch_paths: List[Path],
        exclude_patterns: Optional[List[str]] = None,
        min_file_size: int = 1024,
        enabled: bool = True
    ):
        """
        Initialize document processor.

        Args:
            mcp_client: MCP client for calling tools
            watch_paths: List of paths to watch for new documents
            exclude_patterns: List of glob patterns to exclude
            min_file_size: Minimum file size in bytes (default 1KB)
            enabled: Whether auto-processing is enabled
        """
        self.mcp_client = mcp_client
        self.watch_paths = watch_paths
        self.exclude_patterns = exclude_patterns or self._default_exclude_patterns()
        self.min_file_size = min_file_size
        self.enabled = enabled

        self.processed_files: Set[str] = set()
        self.observer = Observer()
        self.stats = {
            "files_seen": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "processing_errors": 0
        }

    def _default_exclude_patterns(self) -> List[str]:
        """Default exclude patterns for auto-processing."""
        return [
            "*.log",
            "temp*",
            "*.tmp",
            "node_modules/*",
            ".git/*",
            "__pycache__/*",
            "*.pyc",
            ".env",
            "*.bak",
            "*.swp",
            "venv/*",
            ".venv/*"
        ]

    def start(self):
        """Start watching for file changes."""
        if not self.enabled:
            logger.info("Document auto-processor disabled")
            return

        for watch_path in self.watch_paths:
            if watch_path.exists():
                self.observer.schedule(self, path=str(watch_path), recursive=True)
                logger.info(f"Watching path: {watch_path}")
            else:
                logger.warning(f"Path does not exist: {watch_path}")

        self.observer.start()
        logger.info("Document auto-processor started")

    def stop(self):
        """Stop watching for file changes."""
        self.observer.stop()
        self.observer.join()
        logger.info("Document auto-processor stopped")

    def on_created(self, event):
        """
        Handle file creation events.

        Args:
            event: FileCreatedEvent
        """
        if event.is_directory:
            return

        self.stats["files_seen"] += 1
        file_path = event.src_path

        # Check if we should process this file
        if not self.should_process(file_path):
            logger.debug(f"Skipping file: {file_path}")
            self.stats["files_skipped"] += 1
            return

        # Process the file
        asyncio.create_task(self.process_file(file_path))

    def should_process(self, file_path: str) -> bool:
        """
        Determine if file should be auto-processed.

        Args:
            file_path: Path to the file

        Returns:
            True if should process, False otherwise
        """
        # Check if already processed
        if file_path in self.processed_files:
            return False

        # Check file extension
        if not self._is_document_file(file_path):
            return False

        # Check file size
        try:
            file_size = os.path.getsize(file_path)
            if file_size < self.min_file_size:
                logger.debug(f"File too small: {file_path} ({file_size} bytes)")
                return False
        except OSError:
            return False

        # Check exclude patterns
        if self._matches_exclude_patterns(file_path):
            logger.debug(f"File matches exclude pattern: {file_path}")
            return False

        return True

    def _is_document_file(self, file_path: str) -> bool:
        """Check if file is a document type we process."""
        document_extensions = [
            '.md',      # Markdown
            '.txt',     # Plain text
            '.pdf',     # PDF (requires additional dependency)
            '.rst',     # reStructuredText
            '.py',      # Python source code
            '.js',      # JavaScript
            '.ts',      # TypeScript
            '.json',    # JSON
            '.yaml',    # YAML
            '.yml',     # YAML
            '.html',    # HTML
            '.css',     # CSS
            '.sh',      # Shell script
            '.ps1',     # PowerShell
        ]

        return any(file_path.endswith(ext) for ext in document_extensions)

    def _matches_exclude_patterns(self, file_path: str) -> bool:
        """Check if file matches any exclude patterns."""
        file_path_lower = file_path.lower()

        for pattern in self.exclude_patterns:
            try:
                if fnmatch.fnmatch(file_path_lower, pattern.lower()):
                    return True
            except (re.error, AttributeError):
                # Invalid pattern
                pass

        return False

    async def process_file(self, file_path: str) -> bool:
        """
        Process a document file.

        Args:
            file_path: Path to the file

        Returns:
            True if processing succeeded
        """
        try:
            logger.info(f"Processing document: {file_path}")

            # Read file content
            content = await self._read_file(file_path)

            if not content:
                logger.warning(f"Empty content: {file_path}")
                self.stats["files_skipped"] += 1
                return False

            # Extract metadata
            metadata = self._extract_metadata(file_path)

            # Call cognify MCP tool
            result = await self.mcp_client.call_tool(
                "cognify",
                {
                    "data": content,
                    "metadata": json.dumps(metadata)
                }
            )

            # Mark as processed
            self.processed_files.add(file_path)
            self.stats["files_processed"] += 1

            logger.info(f"Successfully processed: {file_path}")
            logger.debug(f"Cognify result: {result}")

            return True

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats["processing_errors"] += 1
            return False

    async def _read_file(self, file_path: str) -> Optional[str]:
        """
        Read file content.

        Args:
            file_path: Path to the file

        Returns:
            File content as string, or None if error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None

    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from file path.

        Args:
            file_path: Path to the file

        Returns:
            Metadata dictionary
        """
        path = Path(file_path)

        return {
            "source": "auto_cognify",
            "file_path": file_path,
            "file_name": path.name,
            "file_extension": path.suffix,
            "file_size": path.stat().st_size,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "auto_processed": True
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Statistics dictionary
        """
        return {
            **self.stats,
            "currently_watching": len(self.watch_paths),
            "enabled": self.enabled,
            "exclude_patterns": len(self.exclude_patterns)
        }

    def reset_statistics(self):
        """Reset processing statistics."""
        self.stats = {
            "files_seen": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "processing_errors": 0
        }
        logger.info("Statistics reset")


class DocumentProcessorManager:
    """
    Manager for document processor lifecycle.

    Provides high-level interface for starting/stopping auto-processing.
    """

    def __init__(self, mcp_client, config: Dict[str, Any]):
        """
        Initialize document processor manager.

        Args:
            mcp_client: MCP client for calling tools
            config: Configuration dictionary
        """
        self.mcp_client = mcp_client
        self.config = config
        self.processor: Optional[DocumentProcessor] = None

    async def start(self):
        """Start document processor based on configuration."""
        auto_cognify_config = self.config.get("auto_cognify", {})

        if not auto_cognify_config.get("enabled", False):
            logger.info("Auto-cognify disabled in configuration")
            return

        # Get watch paths
        watch_paths_str = auto_cognify_config.get("watch_paths", ["."])
        watch_paths = [Path(p) for p in watch_paths_str]

        # Get exclude patterns
        exclude_patterns = auto_cognify_config.get("exclude_patterns")

        # Get minimum file size
        min_file_size = auto_cognify_config.get("min_file_size", 1024)

        # Create processor
        self.processor = DocumentProcessor(
            mcp_client=self.mcp_client,
            watch_paths=watch_paths,
            exclude_patterns=exclude_patterns,
            min_file_size=min_file_size,
            enabled=True
        )

        # Start processor
        self.processor.start()

        logger.info("Document auto-processor started")

    async def stop(self):
        """Stop document processor."""
        if self.processor:
            self.processor.stop()
            logger.info("Document auto-processor stopped")

    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics."""
        if self.processor:
            return self.processor.get_statistics()
        return {
            "files_seen": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "processing_errors": 0,
            "currently_watching": 0,
            "enabled": False
        }


async def main():
    """Test document processor."""
    import json

    # Mock MCP client
    class MockMCPClient:
        async def call_tool(self, tool_name: str, params: dict):
            logger.info(f"Mock MCP call: {tool_name}")
            return f"Mock result: {tool_name}"

    # Test configuration
    config = {
        "auto_cognify": {
            "enabled": True,
            "watch_paths": ["."],
            "exclude_patterns": ["*.log", "temp*"],
            "min_file_size": 1024
        }
    }

    # Create manager
    manager = DocumentProcessorManager(MockMCPClient(), config)
    await manager.start()

    # Run for a few seconds
    logger.info("Running for 5 seconds...")
    await asyncio.sleep(5)

    # Print statistics
    stats = manager.get_statistics()
    print(json.dumps(stats, indent=2))

    # Stop
    await manager.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
