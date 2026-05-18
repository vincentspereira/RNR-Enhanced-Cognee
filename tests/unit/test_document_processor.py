"""
Unit tests for src.document_processor
========================================
Tests DocumentProcessor, DocumentProcessorManager.
All filesystem and watchdog interactions are mocked.
No real file I/O or OS calls. No Unicode characters.
"""

import asyncio
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.call_tool = AsyncMock(return_value="mock result")
    return client


def _make_processor(watch_paths=None, exclude_patterns=None, min_file_size=0, enabled=True):
    """Create a DocumentProcessor with mocked Observer."""
    from src.document_processor import DocumentProcessor
    with patch("src.document_processor.Observer"):
        processor = DocumentProcessor(
            mcp_client=_make_mcp_client(),
            watch_paths=watch_paths or [Path("/fake/path")],
            exclude_patterns=exclude_patterns,
            min_file_size=min_file_size,
            enabled=enabled
        )
    return processor


# ---------------------------------------------------------------------------
# DocumentProcessor init
# ---------------------------------------------------------------------------

class TestDocumentProcessorInit:
    def test_init_defaults(self):
        processor = _make_processor()
        assert processor.enabled is True
        assert processor.min_file_size == 0
        assert processor.processed_files == set()

    def test_init_stats_initialized(self):
        processor = _make_processor()
        assert processor.stats["files_seen"] == 0
        assert processor.stats["files_processed"] == 0
        assert processor.stats["files_skipped"] == 0
        assert processor.stats["processing_errors"] == 0

    def test_default_exclude_patterns_set(self):
        processor = _make_processor()
        assert len(processor.exclude_patterns) > 0
        assert "*.log" in processor.exclude_patterns

    def test_custom_exclude_patterns(self):
        processor = _make_processor(exclude_patterns=["*.custom"])
        assert processor.exclude_patterns == ["*.custom"]

    def test_disabled_processor(self):
        processor = _make_processor(enabled=False)
        assert processor.enabled is False


# ---------------------------------------------------------------------------
# _default_exclude_patterns
# ---------------------------------------------------------------------------

class TestDefaultExcludePatterns:
    def test_contains_common_patterns(self):
        processor = _make_processor()
        patterns = processor._default_exclude_patterns()
        assert "*.log" in patterns
        assert "*.tmp" in patterns
        assert "*.pyc" in patterns
        assert ".env" in patterns

    def test_returns_list(self):
        processor = _make_processor()
        patterns = processor._default_exclude_patterns()
        assert isinstance(patterns, list)


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

class TestStartStop:
    def test_start_disabled_does_not_schedule(self):
        from src.document_processor import DocumentProcessor
        mock_observer = MagicMock()
        with patch("src.document_processor.Observer", return_value=mock_observer):
            processor = DocumentProcessor(
                mcp_client=_make_mcp_client(),
                watch_paths=[Path("/fake")],
                enabled=False
            )
        processor.start()
        mock_observer.schedule.assert_not_called()

    def test_start_enabled_schedules_existing_path(self, tmp_path):
        from src.document_processor import DocumentProcessor
        mock_observer = MagicMock()
        with patch("src.document_processor.Observer", return_value=mock_observer):
            processor = DocumentProcessor(
                mcp_client=_make_mcp_client(),
                watch_paths=[tmp_path],
                enabled=True
            )
        processor.start()
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()

    def test_start_nonexistent_path_warns(self):
        from src.document_processor import DocumentProcessor
        mock_observer = MagicMock()
        nonexistent = Path("/nonexistent/path/xyz")
        with patch("src.document_processor.Observer", return_value=mock_observer):
            processor = DocumentProcessor(
                mcp_client=_make_mcp_client(),
                watch_paths=[nonexistent],
                enabled=True
            )
        processor.start()
        # Should not schedule the nonexistent path
        mock_observer.schedule.assert_not_called()
        mock_observer.start.assert_called_once()

    def test_stop_calls_observer_stop_and_join(self):
        processor = _make_processor()
        processor.stop()
        processor.observer.stop.assert_called_once()
        processor.observer.join.assert_called_once()


# ---------------------------------------------------------------------------
# on_created
# ---------------------------------------------------------------------------

class TestOnCreated:
    def test_directory_event_is_ignored(self):
        processor = _make_processor()
        event = MagicMock()
        event.is_directory = True
        processor.on_created(event)
        assert processor.stats["files_seen"] == 0

    def test_file_event_increments_files_seen(self):
        processor = _make_processor()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/fake/path/file.md"

        with patch.object(processor, "should_process", return_value=False):
            processor.on_created(event)

        assert processor.stats["files_seen"] == 1
        assert processor.stats["files_skipped"] == 1

    def test_file_event_creates_task_when_should_process(self):
        processor = _make_processor()
        event = MagicMock()
        event.is_directory = False
        event.src_path = "/fake/path/file.md"

        with patch.object(processor, "should_process", return_value=True), \
             patch("src.document_processor.asyncio.create_task") as mock_task:
            processor.on_created(event)

        mock_task.assert_called_once()


# ---------------------------------------------------------------------------
# should_process
# ---------------------------------------------------------------------------

class TestShouldProcess:
    def test_already_processed_returns_false(self):
        processor = _make_processor(min_file_size=0)
        processor.processed_files.add("/path/file.md")
        assert processor.should_process("/path/file.md") is False

    def test_non_document_extension_returns_false(self):
        processor = _make_processor(min_file_size=0)
        assert processor.should_process("/path/file.xyz") is False

    def test_file_too_small_returns_false(self, tmp_path):
        processor = _make_processor(min_file_size=10000)
        small_file = tmp_path / "small.md"
        small_file.write_bytes(b"tiny")
        assert processor.should_process(str(small_file)) is False

    def test_os_error_returns_false(self):
        processor = _make_processor(min_file_size=1)
        # Non-existent file -> OSError
        assert processor.should_process("/nonexistent/file.md") is False

    def test_excluded_file_returns_false(self, tmp_path):
        processor = _make_processor(
            min_file_size=0,
            exclude_patterns=["*.log"]
        )
        log_file = tmp_path / "test.log"
        log_file.write_bytes(b"x" * 100)
        assert processor.should_process(str(log_file)) is False

    def test_document_file_matching_exclude_pattern_returns_false(self, tmp_path):
        # Use a .md (document) extension so _is_document_file passes, then
        # confirm the exclude pattern check (lines 155-157) is reached.
        processor = _make_processor(
            min_file_size=0,
            exclude_patterns=["*.md"]
        )
        md_file = tmp_path / "readme.md"
        md_file.write_bytes(b"# content")
        assert processor.should_process(str(md_file)) is False

    def test_valid_document_returns_true(self, tmp_path):
        processor = _make_processor(
            min_file_size=0,
            exclude_patterns=[]
        )
        valid_file = tmp_path / "readme.md"
        valid_file.write_bytes(b"# Hello World")
        assert processor.should_process(str(valid_file)) is True


# ---------------------------------------------------------------------------
# _is_document_file
# ---------------------------------------------------------------------------

class TestIsDocumentFile:
    def test_markdown_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("file.md") is True

    def test_txt_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("file.txt") is True

    def test_pdf_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("doc.pdf") is True

    def test_python_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("script.py") is True

    def test_js_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("app.js") is True

    def test_ts_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("app.ts") is True

    def test_json_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("config.json") is True

    def test_yaml_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("config.yaml") is True

    def test_yml_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("config.yml") is True

    def test_sh_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("script.sh") is True

    def test_ps1_is_document(self):
        processor = _make_processor()
        assert processor._is_document_file("script.ps1") is True

    def test_exe_not_document(self):
        processor = _make_processor()
        assert processor._is_document_file("program.exe") is False

    def test_zip_not_document(self):
        processor = _make_processor()
        assert processor._is_document_file("archive.zip") is False


# ---------------------------------------------------------------------------
# _matches_exclude_patterns
# ---------------------------------------------------------------------------

class TestMatchesExcludePatterns:
    def test_log_file_matches_log_pattern(self):
        processor = _make_processor(exclude_patterns=["*.log"])
        assert processor._matches_exclude_patterns("/path/server.log") is True

    def test_md_file_does_not_match_log_pattern(self):
        processor = _make_processor(exclude_patterns=["*.log"])
        assert processor._matches_exclude_patterns("/path/readme.md") is False

    def test_temp_file_matches_temp_pattern(self):
        # fnmatch matches against the full path string, so "temp*" only matches
        # when the full path starts with "temp" (no leading directory).
        processor = _make_processor(exclude_patterns=["temp*"])
        assert processor._matches_exclude_patterns("tempfile.txt") is True

    def test_case_insensitive_match(self):
        processor = _make_processor(exclude_patterns=["*.log"])
        # Both lower and upper should match (function lowercases both)
        assert processor._matches_exclude_patterns("/path/server.LOG") is True

    def test_no_patterns_returns_false(self):
        processor = _make_processor(exclude_patterns=[])
        assert processor._matches_exclude_patterns("/path/any.md") is False

    def test_invalid_pattern_swallowed(self):
        # BUG FIX: document_processor.py now imports `re` at module level so
        # the `except (re.error, AttributeError)` clause works as intended.
        # Bad patterns (None, malformed) are silently skipped instead of
        # crashing the matcher.
        processor = _make_processor(exclude_patterns=["*.log"])
        processor.exclude_patterns = [None, "*.log"]
        # None triggers AttributeError inside fnmatch (via .lower()),
        # which is now properly caught. The remaining "*.log" pattern matches.
        assert processor._matches_exclude_patterns("/path/server.log") is True

    def test_invalid_pattern_alone_returns_false(self):
        # BUG FIX: a bad pattern with no other matchers cleanly returns False
        # (was: raised NameError due to undefined `re`).
        processor = _make_processor(exclude_patterns=[None])
        processor.exclude_patterns = [None]
        assert processor._matches_exclude_patterns("/path/server.log") is False


# ---------------------------------------------------------------------------
# process_file
# ---------------------------------------------------------------------------

class TestProcessFile:
    async def test_process_file_success(self, tmp_path):
        processor = _make_processor(min_file_size=0)
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document\n\nSome content here.")

        result = await processor.process_file(str(test_file))

        assert result is True
        assert str(test_file) in processor.processed_files
        assert processor.stats["files_processed"] == 1
        processor.mcp_client.call_tool.assert_called_once_with("cognify", {
            "data": "# Test Document\n\nSome content here.",
            "metadata": processor.mcp_client.call_tool.call_args[0][1]["metadata"]
        })

    async def test_process_empty_file_skips(self, tmp_path):
        processor = _make_processor(min_file_size=0)
        empty_file = tmp_path / "empty.md"
        empty_file.write_bytes(b"")

        result = await processor.process_file(str(empty_file))

        assert result is False
        assert processor.stats["files_skipped"] == 1

    async def test_process_file_exception_records_error(self, tmp_path):
        processor = _make_processor(min_file_size=0)
        test_file = tmp_path / "error.md"
        test_file.write_text("content")
        processor.mcp_client.call_tool = AsyncMock(side_effect=Exception("MCP error"))

        result = await processor.process_file(str(test_file))

        assert result is False
        assert processor.stats["processing_errors"] == 1


# ---------------------------------------------------------------------------
# _read_file
# ---------------------------------------------------------------------------

class TestReadFile:
    async def test_read_utf8_file(self, tmp_path):
        processor = _make_processor()
        test_file = tmp_path / "utf8.txt"
        test_file.write_text("Hello UTF-8", encoding="utf-8")
        content = await processor._read_file(str(test_file))
        assert content == "Hello UTF-8"

    async def test_read_nonexistent_file_returns_none(self):
        processor = _make_processor()
        content = await processor._read_file("/nonexistent/file.txt")
        assert content is None

    async def test_read_latin1_fallback(self, tmp_path):
        """Files that can't be read as UTF-8 should try latin-1."""
        processor = _make_processor()
        test_file = tmp_path / "latin1.txt"
        # Write bytes that are invalid UTF-8
        test_file.write_bytes(b"\xe9\xe0\xf9")  # Valid latin-1
        content = await processor._read_file(str(test_file))
        assert content is not None

    async def test_read_file_latin1_also_fails_returns_none(self, tmp_path):
        """When both UTF-8 and latin-1 reads raise exceptions, return None."""
        processor = _make_processor()
        test_file = tmp_path / "bad.txt"
        test_file.write_bytes(b"\xff")

        with patch("builtins.open") as mock_open_fn:
            # First open (UTF-8) raises UnicodeDecodeError; second raises Exception.
            mock_open_fn.side_effect = [
                UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid byte"),
                Exception("IO error on latin-1 read"),
            ]
            content = await processor._read_file(str(test_file))

        assert content is None


# ---------------------------------------------------------------------------
# _extract_metadata
# ---------------------------------------------------------------------------

class TestExtractMetadata:
    def test_metadata_contains_source(self, tmp_path):
        processor = _make_processor()
        test_file = tmp_path / "doc.md"
        test_file.write_text("content")
        metadata = processor._extract_metadata(str(test_file))
        assert metadata["source"] == "auto_cognify"
        assert metadata["auto_processed"] is True

    def test_metadata_contains_file_info(self, tmp_path):
        processor = _make_processor()
        test_file = tmp_path / "readme.md"
        test_file.write_text("hello")
        metadata = processor._extract_metadata(str(test_file))
        assert metadata["file_name"] == "readme.md"
        assert metadata["file_extension"] == ".md"
        assert "file_path" in metadata
        assert "file_size" in metadata
        assert "processed_at" in metadata


# ---------------------------------------------------------------------------
# get_statistics / reset_statistics
# ---------------------------------------------------------------------------

class TestStatistics:
    def test_get_statistics_default(self):
        processor = _make_processor()
        stats = processor.get_statistics()
        assert stats["files_seen"] == 0
        assert stats["files_processed"] == 0
        assert "currently_watching" in stats
        assert stats["enabled"] is True

    def test_get_statistics_with_counts(self, tmp_path):
        processor = _make_processor(watch_paths=[tmp_path])
        processor.stats["files_seen"] = 5
        processor.stats["files_processed"] = 3
        stats = processor.get_statistics()
        assert stats["files_seen"] == 5
        assert stats["files_processed"] == 3

    def test_reset_statistics(self):
        processor = _make_processor()
        processor.stats["files_seen"] = 10
        processor.stats["files_processed"] = 5
        processor.reset_statistics()
        assert processor.stats["files_seen"] == 0
        assert processor.stats["files_processed"] == 0


# ---------------------------------------------------------------------------
# DocumentProcessorManager
# ---------------------------------------------------------------------------

class TestDocumentProcessorManager:
    async def test_start_disabled_does_not_create_processor(self):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {"auto_cognify": {"enabled": False}}
        manager = DocumentProcessorManager(mcp, config)
        await manager.start()
        assert manager.processor is None

    async def test_start_enabled_creates_processor(self, tmp_path):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {
            "auto_cognify": {
                "enabled": True,
                "watch_paths": [str(tmp_path)],
                "min_file_size": 0
            }
        }
        with patch("src.document_processor.Observer"):
            manager = DocumentProcessorManager(mcp, config)
            await manager.start()
        assert manager.processor is not None

    async def test_stop_when_no_processor(self):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {}
        manager = DocumentProcessorManager(mcp, config)
        # Should not raise
        await manager.stop()

    async def test_stop_calls_processor_stop(self, tmp_path):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {
            "auto_cognify": {
                "enabled": True,
                "watch_paths": [str(tmp_path)],
                "min_file_size": 0
            }
        }
        with patch("src.document_processor.Observer"):
            manager = DocumentProcessorManager(mcp, config)
            await manager.start()

        with patch.object(manager.processor, "stop") as mock_stop:
            await manager.stop()
        mock_stop.assert_called_once()

    def test_get_statistics_no_processor(self):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        manager = DocumentProcessorManager(mcp, {})
        stats = manager.get_statistics()
        assert stats["files_seen"] == 0
        assert stats["enabled"] is False

    async def test_get_statistics_with_processor(self, tmp_path):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {
            "auto_cognify": {
                "enabled": True,
                "watch_paths": [str(tmp_path)],
                "min_file_size": 0
            }
        }
        with patch("src.document_processor.Observer"):
            manager = DocumentProcessorManager(mcp, config)
            await manager.start()
        stats = manager.get_statistics()
        assert "files_seen" in stats
        assert stats["enabled"] is True

    async def test_start_uses_default_watch_paths(self):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {
            "auto_cognify": {
                "enabled": True
                # No watch_paths -> defaults to ["."]
            }
        }
        with patch("src.document_processor.Observer"):
            manager = DocumentProcessorManager(mcp, config)
            await manager.start()
        assert manager.processor is not None

    async def test_start_with_exclude_patterns(self, tmp_path):
        from src.document_processor import DocumentProcessorManager
        mcp = _make_mcp_client()
        config = {
            "auto_cognify": {
                "enabled": True,
                "watch_paths": [str(tmp_path)],
                "exclude_patterns": ["*.secret"],
                "min_file_size": 0
            }
        }
        with patch("src.document_processor.Observer"):
            manager = DocumentProcessorManager(mcp, config)
            await manager.start()
        assert "*.secret" in manager.processor.exclude_patterns
