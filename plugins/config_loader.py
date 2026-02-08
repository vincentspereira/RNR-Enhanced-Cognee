"""
Enhanced Cognee - Configuration Loader for Plugins

This module loads and manages configuration for the Claude Code plugin.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads and validates configuration for the Claude Code plugin.
    """

    DEFAULT_CONFIG_PATH = "automation_config.json"
    DEFAULT_CONFIG = {
        "auto_memory_capture": {
            "enabled": False,
            "capture_on": [
                "code_edit",
                "file_write",
                "terminal_command"
            ],
            "exclude_patterns": [
                "*.log",
                "temp*",
                "*.tmp",
                "node_modules/*",
                ".git/*",
                "__pycache__/*",
                "*.pyc",
                ".env"
            ],
            "importance_threshold": 0.3,
            "max_memory_length": 5000
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to automation config file
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = None
        self.last_modified = None

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dict
        """
        # Check if file exists
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}")
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

            # Validate config
            self._validate_config()

            self.last_modified = os.path.getmtime(self.config_path)
            logger.info(f"Loaded configuration from {self.config_path}")

            return self.config

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return self.DEFAULT_CONFIG.copy()

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _validate_config(self):
        """
        Validate configuration structure and values.
        """
        if not self.config:
            raise ValueError("Configuration is empty")

        # Validate auto_memory_capture section
        if "auto_memory_capture" not in self.config:
            logger.warning("Missing auto_memory_capture section, using defaults")
            self.config["auto_memory_capture"] = self.DEFAULT_CONFIG["auto_memory_capture"].copy()
            return

        auto_capture = self.config["auto_memory_capture"]

        # Validate required fields
        if "enabled" not in auto_capture:
            auto_capture["enabled"] = False

        if "capture_on" not in auto_capture or not isinstance(auto_capture["capture_on"], list):
            auto_capture["capture_on"] = self.DEFAULT_CONFIG["auto_memory_capture"]["capture_on"].copy()

        if "exclude_patterns" not in auto_capture or not isinstance(auto_capture["exclude_patterns"], list):
            auto_capture["exclude_patterns"] = self.DEFAULT_CONFIG["auto_memory_capture"]["exclude_patterns"].copy()

        if "importance_threshold" not in auto_capture:
            auto_capture["importance_threshold"] = self.DEFAULT_CONFIG["auto_memory_capture"]["importance_threshold"]

        if "max_memory_length" not in auto_capture:
            auto_capture["max_memory_length"] = self.DEFAULT_CONFIG["auto_memory_capture"]["max_memory_length"]

        # Validate types
        if not isinstance(auto_capture["importance_threshold"], (int, float)):
            auto_capture["importance_threshold"] = float(auto_capture["importance_threshold"])

        if not isinstance(auto_capture["max_memory_length"], int):
            auto_capture["max_memory_length"] = int(auto_capture["max_memory_length"])

        # Clamp values to valid ranges
        auto_capture["importance_threshold"] = max(0.0, min(1.0, auto_capture["importance_threshold"]))
        auto_capture["max_memory_length"] = max(100, min(50000, auto_capture["max_memory_length"]))

    def get_auto_capture_config(self) -> Dict[str, Any]:
        """
        Get auto memory capture configuration.

        Returns:
            Auto capture configuration dict
        """
        if self.config is None:
            self.load_config()

        return self.config.get("auto_memory_capture", self.DEFAULT_CONFIG["auto_memory_capture"])

    def reload_if_modified(self) -> bool:
        """
        Reload configuration if file has been modified.

        Returns:
            True if reloaded, False otherwise
        """
        if not os.path.exists(self.config_path):
            return False

        current_modified = os.path.getmtime(self.config_path)
        if self.last_modified != current_modified:
            logger.info("Configuration file modified, reloading...")
            self.load_config()
            return True

        return False
