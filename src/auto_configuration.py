"""
Enhanced Cognee - Auto-Configuration System

Automatically configures Enhanced Cognee based on environment detection.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class AutoConfiguration:
    """
    Automatic configuration system for Enhanced Cognee.

    Detects system capabilities and configures settings automatically.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize auto-configuration system.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.env_path = self.project_root / ".env"
        self.config_path = self.project_root / "automation_config.json"
        self.category_config_path = self.project_root / ".enhanced-cognee-config.json"

    async def auto_configure(self) -> Dict[str, Any]:
        """
        Run automatic configuration.

        Returns:
            Configuration dictionary with detected settings
        """
        logger.info("Starting auto-configuration...")

        config = {}

        # Detect system capabilities
        config["system"] = await self._detect_system_capabilities()

        # Detect Docker availability
        config["docker"] = await self._detect_docker()

        # Detect available ports
        config["ports"] = await self._detect_available_ports()

        # Detect LLM provider (if API keys present)
        config["llm"] = await self._detect_llm_provider()

        # Determine installation mode
        config["installation_mode"] = self._determine_installation_mode(config)

        # Generate secure passwords
        config["passwords"] = self._generate_passwords()

        logger.info("Auto-configuration complete")
        return config

    async def _detect_system_capabilities(self) -> Dict[str, Any]:
        """Detect system capabilities."""
        import platform
        import psutil

        system = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 1) if platform.system() != 'Windows' else round(psutil.disk_usage('C:\\').free / (1024**3), 1)
        }

        logger.info(f"Detected system: {system['os']} {system['os_version']}")
        logger.info(f"CPU cores: {system['cpu_count']}, RAM: {system['memory_gb']} GB")

        return system

    async def _detect_docker(self) -> Dict[str, Any]:
        """Detect Docker availability."""
        import subprocess

        docker_info = {
            "available": False,
            "version": None,
            "compose_available": False
        }

        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                docker_info["available"] = True
                docker_info["version"] = result.stdout.strip()

                # Check Docker Compose
                result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    docker_info["compose_available"] = True
                    logger.info(f"Docker available: {docker_info['version']}")
                else:
                    logger.warning("Docker Compose not available")
            else:
                logger.info("Docker not available")

        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.info("Docker not found")

        return docker_info

    async def _detect_available_ports(self) -> Dict[str, int]:
        """Detect available ports for Enhanced stack."""
        import socket

        ports = {
            "postgres": 25432,
            "qdrant": 26333,
            "neo4j": 27687,
            "redis": 26379
        }

        # Check if default ports are available
        for service, port in ports.items():
            if self._is_port_available(port):
                logger.info(f"Port {port} available for {service}")
            else:
                # Find alternative port
                for alt_port in range(port + 1, port + 100):
                    if self._is_port_available(alt_port):
                        ports[service] = alt_port
                        logger.info(f"Port {port} busy, using {alt_port} for {service}")
                        break

        return ports

    def _is_port_available(self, port: int) -> bool:
        """Check if port is available."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return True
            except OSError:
                return False

    async def _detect_llm_provider(self) -> Dict[str, Any]:
        """Detect LLM provider from environment variables."""
        llm_info = {
            "provider": None,
            "api_key_present": False,
            "recommended_provider": "anthropic"
        }

        # Check for API keys in environment
        if os.environ.get("ANTHROPIC_API_KEY"):
            llm_info["provider"] = "anthropic"
            llm_info["api_key_present"] = True
            logger.info("Detected Anthropic API key")
        elif os.environ.get("OPENAI_API_KEY"):
            llm_info["provider"] = "openai"
            llm_info["api_key_present"] = True
            logger.info("Detected OpenAI API key")
        else:
            logger.info("No LLM API key detected - Anthropic recommended")

        return llm_info

    def _determine_installation_mode(self, config: Dict[str, Any]) -> str:
        """Determine recommended installation mode."""
        # Use Lite mode if:
        # - Docker not available
        # - Less than 4 GB RAM
        # - Less than 10 GB disk space

        if not config["docker"]["available"]:
            logger.info("Docker not available - recommending Lite mode")
            return "lite"

        if config["system"]["memory_gb"] < 4:
            logger.info("Low memory - recommending Lite mode")
            return "lite"

        if config["system"]["disk_free_gb"] < 10:
            logger.info("Low disk space - recommending Lite mode")
            return "lite"

        logger.info("System capable - recommending Full mode")
        return "full"

    def _generate_passwords(self) -> Dict[str, str]:
        """Generate secure passwords."""
        import secrets

        return {
            "postgres": secrets.token_urlsafe(16),
            "neo4j": secrets.token_urlsafe(16),
            "redis": secrets.token_urlsafe(16)
        }

    async def apply_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Apply auto-generated configuration.

        Args:
            config: Configuration dictionary from auto_configure()

        Returns:
            True if configuration applied successfully
        """
        try:
            # Generate .env file
            env_content = self._generate_env_content(config)
            self.env_path.write_text(env_content)
            logger.info(f"Configuration saved to {self.env_path}")

            # Generate automation config
            await self._generate_automation_config()

            # Generate category config
            await self._generate_category_config()

            return True

        except Exception as e:
            logger.error(f"Failed to apply configuration: {e}")
            return False

    def _generate_env_content(self, config: Dict[str, Any]) -> str:
        """Generate .env file content."""
        lines = [
            "# Enhanced Cognee Auto-Generated Configuration",
            f"# Generated: {self._get_timestamp()}",
            "",
            "# Enhanced Mode",
            "ENHANCED_COGNEE_MODE=true",
            "",
            "# Installation Mode",
            f'INSTALLATION_MODE={config["installation_mode"]}',
            "",
            "# LLM Provider",
            f'LLM_PROVIDER={config["llm"]["provider"] or "anthropic"}',
        ]

        # Add LLM API key if present
        if config["llm"]["provider"] == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            lines.append(f'ANTHROPIC_API_KEY={os.environ["ANTHROPIC_API_KEY"]}')
        elif config["llm"]["provider"] == "openai" and os.environ.get("OPENAI_API_KEY"):
            lines.append(f'OPENAI_API_KEY={os.environ["OPENAI_API_KEY"]}')

        # Add database configuration
        ports = config["ports"]
        passwords = config["passwords"]

        lines.extend([
            "",
            "# PostgreSQL Configuration",
            "POSTGRES_HOST=localhost",
            f'POSTGRES_PORT={ports["postgres"]}',
            "POSTGRES_DB=cognee_db",
            "POSTGRES_USER=cognee_user",
            f'POSTGRES_PASSWORD={passwords["postgres"]}',
            "",
            "# Qdrant Configuration",
            f"QDRANT_HOST=localhost",
            f'QDRANT_PORT={ports["qdrant"]}',
            "",
            "# Neo4j Configuration",
            f'NEO4J_URI=bolt://localhost:{ports["neo4j"]}',
            "NEO4J_USER=neo4j",
            f'NEO4J_PASSWORD={passwords["neo4j"]}',
            "",
            "# Redis Configuration",
            f"REDIS_HOST=localhost",
            f'REDIS_PORT={ports["redis"]}',
            f'REDIS_PASSWORD={passwords["redis"]}',
            "",
            "# Automation Preferences (all disabled for security)",
            "AUTO_MEMORY_CAPTURE=false",
            "AUTO_DEDUPLICATION=false",
            "AUTO_SUMMARIZATION=false",
            "",
            "# Dynamic Categories",
            "MEMORY_CATEGORIZATION=true",
            'ENHANCED_COGNEE_CONFIG_PATH=.enhanced-cognee-config.json',
        ])

        return "\n".join(lines)

    async def _generate_automation_config(self):
        """Generate automation_config.json with safe defaults."""
        # This file already exists - just verify it
        if not self.config_path.exists():
            logger.warning(f"Automation config not found: {self.config_path}")

    async def _generate_category_config(self):
        """Generate .enhanced-cognee-config.json."""
        categories = {
            "categories": {
                "default": {
                    "prefix": "default_",
                    "description": "Default memories"
                },
                "trading": {
                    "prefix": "trading_",
                    "description": "Trading system memories"
                },
                "development": {
                    "prefix": "dev_",
                    "description": "Development memories"
                },
                "analysis": {
                    "prefix": "analysis_",
                    "description": "Analysis and reports"
                }
            }
        }

        self.category_config_path.write_text(json.dumps(categories, indent=2))
        logger.info(f"Category config saved to {self.category_config_path}")

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def main():
    """Test auto-configuration."""
    auto_config = AutoConfiguration()
    config = await auto_config.auto_configure()
    print(json.dumps(config, indent=2))
    success = await auto_config.apply_configuration(config)
    print(f"Configuration applied: {success}")


if __name__ == "__main__":
    asyncio.run(main())
