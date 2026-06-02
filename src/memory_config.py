#!/usr/bin/env python3
"""
Enhanced Cognee Memory Configuration System
Allows projects to define their own memory categories and prefixes
This is a CONFIGURABLE system - NOT hardcoded to any specific project
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MemoryCategoryConfig:
    """Configuration for a memory category"""
    name: str
    description: str
    prefix: str
    retention_days: int = 30
    priority: int = 1


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    agent_id: str
    category: str  # References MemoryCategoryConfig.name
    prefix: str
    description: str
    memory_types: List[str] = field(default_factory=list)
    priority: int = 1
    data_retention_days: int = 30


class DefaultMemoryCategories:
    """Default memory categories (can be overridden by projects)"""

    @staticmethod
    def get_example_categories() -> Dict[str, MemoryCategoryConfig]:
        """
        Example memory categories for a multi-agent system.
        Replace with your own categories via .enhanced-cognee-config.json.
        This is a REFERENCE EXAMPLE only - not used in production.
        """
        return {
            "trading": MemoryCategoryConfig(
                name="trading",
                description="Trading and market analysis agents",
                prefix="trading_",
                retention_days=30,
                priority=1
            ),
            "development": MemoryCategoryConfig(
                name="development",
                description="Development and operations agents",
                prefix="dev_",
                retention_days=60,
                priority=2
            ),
            "coordination": MemoryCategoryConfig(
                name="coordination",
                description="Coordination and infrastructure agents",
                prefix="coord_",
                retention_days=90,
                priority=3
            )
        }

    @staticmethod
    def get_default_categories() -> Dict[str, MemoryCategoryConfig]:
        """
        Generic default categories for simple projects
        Projects can override with their own categories
        """
        return {
            "DEFAULT": MemoryCategoryConfig(
                name="DEFAULT",
                description="Default memory category",
                prefix="",
                retention_days=30,
                priority=1
            )
        }


class MemoryConfigManager:
    """
    Manages memory configuration for projects
    Projects can provide their own config via:
    1. Environment variable: ENHANCED_COGNEE_CONFIG_PATH
    2. JSON file in project root: .enhanced-cognee-config.json
    3. Python config file passed programmatically
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("ENHANCED_COGNEE_CONFIG_PATH")
        self.categories: Dict[str, MemoryCategoryConfig] = {}
        self.agents: Dict[str, AgentConfig] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from file or use defaults"""
        # Try to load from JSON file
        json_path = self._find_config_file()
        if json_path and Path(json_path).exists():
            self._load_from_json(json_path)
        else:
            # Use MAS categories as default for backward compatibility
            logger.warning(
                "No custom config found. Using MAS default categories. "
                "For other projects, create a .enhanced-cognee-config.json file "
                "with your project-specific categories."
            )
            self.categories = DefaultMemoryCategories.get_example_categories()

    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations"""
        # Check explicit path
        if self.config_path:
            return self.config_path

        # Check environment variable
        env_path = os.getenv("ENHANCED_COGNEE_CONFIG_PATH")
        if env_path:
            return env_path

        # Check current directory and parent directories
        current_dir = Path.cwd()
        for parent in [current_dir] + list(current_dir.parents):
            config_file = parent / ".enhanced-cognee-config.json"
            if config_file.exists():
                return str(config_file)

        return None

    def _load_from_json(self, json_path: str):
        """Load configuration from JSON file"""
        try:
            with open(json_path, 'r') as f:
                config_data = json.load(f)

            # Load categories
            if "categories" in config_data:
                self.categories = {
                    name: MemoryCategoryConfig(**cat_config)
                    for name, cat_config in config_data["categories"].items()
                }

            # Load agents
            if "agents" in config_data:
                self.agents = {
                    agent_id: AgentConfig(**agent_config)
                    for agent_id, agent_config in config_data["agents"].items()
                }

            logger.info(f"Loaded configuration from {json_path}")

        except Exception as e:
            logger.error(f"Error loading config from {json_path}: {e}")
            logger.info("Falling back to default categories")
            self.categories = DefaultMemoryCategories.get_example_categories()

    def get_category(self, category_name: str) -> Optional[MemoryCategoryConfig]:
        """Get category configuration by name"""
        return self.categories.get(category_name)

    def get_all_categories(self) -> Dict[str, MemoryCategoryConfig]:
        """Get all categories"""
        return self.categories

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration"""
        return self.agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """Get all agents"""
        return self.agents

    def add_category(self, name: str, config: MemoryCategoryConfig):
        """Add or update a category"""
        self.categories[name] = config

    def add_agent(self, agent_id: str, config: AgentConfig):
        """Add or update an agent"""
        self.agents[agent_id] = config

    def validate_category(self, category_name: str) -> bool:
        """Check if category exists"""
        return category_name in self.categories

    def get_prefix_for_category(self, category_name: str) -> str:
        """Get prefix for a category"""
        category = self.get_category(category_name)
        return category.prefix if category else ""


def create_project_config_example(output_path: str = ".enhanced-cognee-config.json"):
    """
    Create an example configuration file for a project
    Projects can customize this for their needs
    """
    example_config = {
        "project_name": "My Project",
        "description": "Example Enhanced Cognee configuration",
        "categories": {
            "CATEGORY1": {
                "name": "CATEGORY1",
                "description": "First custom category",
                "prefix": "cat1_",
                "retention_days": 30,
                "priority": 1
            },
            "CATEGORY2": {
                "name": "CATEGORY2",
                "description": "Second custom category",
                "prefix": "cat2_",
                "retention_days": 60,
                "priority": 2
            }
        },
        "agents": {
            "my-agent": {
                "agent_id": "my-agent",
                "category": "CATEGORY1",
                "prefix": "cat1_",
                "description": "My custom agent",
                "memory_types": ["factual", "procedural"],
                "priority": 1,
                "data_retention_days": 30
            }
        }
    }

    with open(output_path, 'w') as f:
        json.dump(example_config, f, indent=2)

    logger.info(f"Created example config at {output_path}")
    return example_config


# Singleton instance (can be replaced with custom instance)
_config_manager: Optional[MemoryConfigManager] = None


def get_config_manager() -> MemoryConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = MemoryConfigManager()
    return _config_manager


def reset_config_manager():
    """Reset the global configuration manager (for testing)"""
    global _config_manager
    _config_manager = None


if __name__ == "__main__":
    # Example usage
    print("=== Enhanced Cognee Configuration System ===\n")

    # 1. Use default example configuration
    print("1. Default Example Configuration:")
    config = MemoryConfigManager()
    for cat_name, cat_config in config.get_all_categories().items():
        print(f"  {cat_name}: {cat_config.description} (prefix: {cat_config.prefix})")

    # 2. Create example config for a custom project
    print("\n2. Creating example configuration for custom project...")
    create_project_config_example("/tmp/example-cognee-config.json")

    # 3. Show how to load custom config
    print("\n3. Loading custom configuration...")
    custom_config = MemoryConfigManager(config_path="/tmp/example-cognee-config.json")
    for cat_name, cat_config in custom_config.get_all_categories().items():
        print(f"  {cat_name}: {cat_config.description} (prefix: {cat_config.prefix})")

    print("\n[OK] Configuration system is working!")
