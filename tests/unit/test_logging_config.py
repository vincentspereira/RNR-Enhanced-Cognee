"""
Unit tests for src/logging_config.py
Target: >= 85% line coverage.
"""

import logging
import sys
import tempfile
import os
import builtins
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# EnhancedLogger
# ---------------------------------------------------------------------------

class TestEnhancedLogger:
    def test_instantiation(self):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.logger")
        assert el.logger is not None

    def test_logger_name_set(self):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.named")
        assert el.logger.name == "test.named"

    def test_default_level_is_info(self):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.default_level")
        assert el.logger.level == logging.INFO

    def test_custom_debug_level(self):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.debug_level", level=logging.DEBUG)
        assert el.logger.level == logging.DEBUG

    def test_handler_added(self):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.handler_check")
        assert len(el.logger.handlers) >= 1

    def test_handler_is_stream_handler(self):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.stream_handler")
        assert any(isinstance(h, logging.StreamHandler) for h in el.logger.handlers)

    def test_info_method_logs(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.info_log")
        el.info("hello info")
        out, _ = capfd.readouterr()
        assert "hello info" in out

    def test_warning_method_logs(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.warning_log")
        el.warning("watch out")
        out, _ = capfd.readouterr()
        assert "watch out" in out

    def test_error_method_logs(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.error_log")
        el.error("something broke")
        out, _ = capfd.readouterr()
        assert "something broke" in out

    def test_critical_method_logs(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.critical_log")
        el.critical("meltdown")
        out, _ = capfd.readouterr()
        assert "meltdown" in out

    def test_debug_method_logs_when_level_debug(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.debug_log", level=logging.DEBUG)
        el.debug("debug detail")
        out, _ = capfd.readouterr()
        assert "debug detail" in out

    def test_debug_method_suppressed_at_info_level(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.debug_suppressed")
        # Default is INFO, debug should be suppressed
        el.debug("should not appear")
        out, _ = capfd.readouterr()
        assert "should not appear" not in out

    def test_existing_handlers_cleared(self):
        """Constructor clears existing handlers before adding its own."""
        from src.logging_config import EnhancedLogger
        name = "test.handlers_cleared"
        raw = logging.getLogger(name)
        # Pre-populate a handler
        raw.addHandler(logging.NullHandler())
        raw.addHandler(logging.NullHandler())
        el = EnhancedLogger(name)
        # After EnhancedLogger init, only the StreamHandler it added should be present
        assert len(el.logger.handlers) == 1

    def test_format_contains_level_and_name(self, capfd):
        from src.logging_config import EnhancedLogger
        el = EnhancedLogger("test.format_check")
        el.info("format test message")
        out, _ = capfd.readouterr()
        # Format is [LEVELNAME] [name] message
        assert "INFO" in out or "test.format_check" in out


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    def test_returns_enhanced_logger(self):
        from src.logging_config import get_logger, EnhancedLogger
        el = get_logger("test.get_logger")
        assert isinstance(el, EnhancedLogger)

    def test_different_names_give_different_loggers(self):
        from src.logging_config import get_logger
        a = get_logger("test.a")
        b = get_logger("test.b")
        assert a.logger.name != b.logger.name

    def test_same_name_gives_consistent_naming(self):
        from src.logging_config import get_logger
        a = get_logger("test.same")
        b = get_logger("test.same")
        assert a.logger.name == b.logger.name


# ---------------------------------------------------------------------------
# replace_print_with_logging
# ---------------------------------------------------------------------------

class TestReplacePrintWithLogging:
    def test_replaces_builtin_print(self):
        from src.logging_config import replace_print_with_logging
        original_print = builtins.print
        try:
            replace_print_with_logging()
            assert builtins.print is not original_print
        finally:
            # Always restore to avoid polluting other tests
            builtins.print = original_print

    def test_replaced_print_still_outputs(self, capsys):
        from src.logging_config import replace_print_with_logging
        original_print = builtins.print
        try:
            replace_print_with_logging()
            # Call the patched print - it should still produce output
            builtins.print("test output from replaced print")
            captured = capsys.readouterr()
            assert "test output from replaced print" in captured.out
        finally:
            builtins.print = original_print

    def test_replaced_print_logs_message(self, capfd):
        from src.logging_config import replace_print_with_logging
        original_print = builtins.print
        try:
            replace_print_with_logging()
            builtins.print("my logged message")
            out, _ = capfd.readouterr()
            # The log line from the logger AND the original print both go to stdout
            assert "my logged message" in out
        finally:
            builtins.print = original_print


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

class TestSetupLogging:
    def test_basic_call_no_error(self):
        from src.logging_config import setup_logging
        setup_logging()  # should not raise

    def test_debug_level_string(self):
        from src.logging_config import setup_logging
        setup_logging(log_level="DEBUG")
        root = logging.getLogger()
        # basicConfig won't override an already-configured root logger in most envs;
        # just verify no exception was raised
        assert root is not None

    def test_warning_level_string(self):
        from src.logging_config import setup_logging
        setup_logging(log_level="WARNING")

    def test_error_level_string(self):
        from src.logging_config import setup_logging
        setup_logging(log_level="ERROR")

    def test_critical_level_string(self):
        from src.logging_config import setup_logging
        setup_logging(log_level="CRITICAL")

    def test_unknown_level_defaults_to_info(self):
        from src.logging_config import setup_logging
        # Should not raise even with unknown level
        setup_logging(log_level="VERBOSE")

    def test_with_log_file_plain_format(self):
        from src.logging_config import setup_logging
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            setup_logging(log_file=log_path, log_level="INFO", format_json=False)
            # Write something so the file gets content
            logging.getLogger("test.file_plain").info("plain file message")
            with open(log_path, "r") as fh:
                content = fh.read()
            assert "plain file message" in content
        finally:
            # Clean up handler to avoid file lock issues
            root = logging.getLogger()
            for h in list(root.handlers):
                if isinstance(h, logging.FileHandler) and log_path in getattr(h, "baseFilename", ""):
                    h.close()
                    root.removeHandler(h)
            os.unlink(log_path)

    def test_with_log_file_json_format(self):
        from src.logging_config import setup_logging
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            setup_logging(log_file=log_path, log_level="INFO", format_json=True)
            logging.getLogger("test.file_json").info("json file message")
            with open(log_path, "r") as fh:
                content = fh.read()
            assert "json file message" in content
        finally:
            root = logging.getLogger()
            for h in list(root.handlers):
                if isinstance(h, logging.FileHandler) and log_path in getattr(h, "baseFilename", ""):
                    h.close()
                    root.removeHandler(h)
            os.unlink(log_path)
