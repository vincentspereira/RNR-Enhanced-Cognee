"""
Enhanced Cognee - Setup Wizard

Interactive setup wizard for Enhanced Cognee configuration.
Generates secure passwords and creates .env file automatically.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import os
import secrets
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json


class SetupWizard:
    """
    Interactive setup wizard for Enhanced Cognee.

    Guides users through initial configuration with sensible defaults
    and secure password generation.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize setup wizard.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path.cwd()
        self.env_path = self.project_root / ".env"
        self.config_path = self.project_root / ".enhanced-cognee-config.json"

    def run(self) -> bool:
        """
        Run the interactive setup wizard.

        Returns:
            True if setup completed successfully, False otherwise
        """
        self._print_header()

        # Check if .env already exists
        if self.env_path.exists():
            print("WARN Existing .env file found")
            response = input("Do you want to overwrite it? (y/N): ").strip().lower()
            if response != 'y':
                print("Setup cancelled. Existing configuration preserved.")
                return False

        # Collect configuration
        config = self._collect_configuration()

        # Save configuration
        self._save_configuration(config)

        # Verify setup
        if self._verify_setup():
            self._print_success()
            return True
        else:
            print("ERR Setup verification failed")
            return False

    def _print_header(self):
        """Print wizard header."""
        print("=" * 60)
        print("  Enhanced Cognee Setup Wizard")
        print("=" * 60)
        print()
        print("This wizard will guide you through the initial setup.")
        print("You can accept the defaults or customize your configuration.")
        print()

    def _collect_configuration(self) -> Dict[str, Any]:
        """
        Collect configuration from user.

        Returns:
            Configuration dictionary
        """
        config = {}

        # LLM Provider Selection
        print("Step 1: LLM Provider Configuration")
        print("-" * 60)
        print("Select your preferred LLM provider:")
        print("  1. Anthropic Claude (recommended)")
        print("  2. OpenAI GPT")
        print("  3. LiteLLM (multi-provider)")
        print("  4. Skip (configure later)")

        choice = input("Enter choice (1-4) [1]: ").strip() or "1"

        if choice == "1":
            config["LLM_PROVIDER"] = "anthropic"
            api_key = input("Enter your Anthropic API key (or press Enter to skip): ").strip()
            if api_key:
                config["ANTHROPIC_API_KEY"] = api_key

        elif choice == "2":
            config["LLM_PROVIDER"] = "openai"
            api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
            if api_key:
                config["OPENAI_API_KEY"] = api_key

        elif choice == "3":
            config["LLM_PROVIDER"] = "litellm"
            api_key = input("Enter your LiteLLM API key (or press Enter to skip): ").strip()
            if api_key:
                config["LITELLM_API_KEY"] = api_key
        else:
            config["LLM_PROVIDER"] = ""

        print()

        # Database Ports
        print("Step 2: Database Port Configuration")
        print("-" * 60)
        print("Enhanced Cognee uses non-standard ports to avoid conflicts.")
        print("You can accept defaults or customize ports.")

        postgres_port = input(f"PostgreSQL port [25432]: ").strip() or "25432"
        qdrant_port = input(f"Qdrant port [26333]: ").strip() or "26333"
        neo4j_port = input(f"Neo4j port [27687]: ").strip() or "27687"
        redis_port = input(f"Redis port [26379]: ").strip() or "26379"

        config["POSTGRES_PORT"] = postgres_port
        config["QDRANT_PORT"] = qdrant_port
        config["NEO4J_PORT"] = neo4j_port
        config["REDIS_PORT"] = redis_port

        print()

        # Installation Mode
        print("Step 3: Installation Mode")
        print("-" * 60)
        print("Select installation mode:")
        print("  1. Full Mode - All 4 databases (PostgreSQL, Qdrant, Neo4j, Redis)")
        print("  2. Lite Mode - SQLite only (simpler, fewer features)")

        mode_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
        config["INSTALLATION_MODE"] = "full" if mode_choice == "1" else "lite"

        print()

        # Auto-configuration preferences
        print("Step 4: Automation Preferences")
        print("-" * 60)
        print("Enhanced Cognee can automate various tasks.")
        print("All automation is DISABLED by default for security.")

        auto_capture = input("Enable auto memory capture? (y/N): ").strip().lower()
        config["AUTO_MEMORY_CAPTURE"] = "true" if auto_capture == 'y' else "false"

        auto_dedup = input("Enable auto deduplication (weekly)? (y/N): ").strip().lower()
        config["AUTO_DEDUPLICATION"] = "true" if auto_dedup == 'y' else "false"

        auto_summarize = input("Enable auto summarization (monthly)? (y/N): ").strip().lower()
        config["AUTO_SUMMARIZATION"] = "true" if auto_summarize == 'y' else "false"

        print()

        # Generate secure passwords
        print("Step 5: Security Configuration")
        print("-" * 60)
        print("Generating secure passwords...")

        config["POSTGRES_PASSWORD"] = secrets.token_urlsafe(16)
        config["NEO4J_PASSWORD"] = secrets.token_urlsafe(16)
        config["REDIS_PASSWORD"] = secrets.token_urlsafe(16)

        print("OK Secure passwords generated")
        print()

        return config

    def _save_configuration(self, config: Dict[str, Any]):
        """
        Save configuration to .env file.

        Args:
            config: Configuration dictionary
        """
        # Generate .env content
        env_content = self._generate_env_content(config)

        # Write .env file
        self.env_path.write_text(env_content)

        # Also save JSON config for dynamic categories
        json_config = {
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
                }
            }
        }

        self.config_path.write_text(json.dumps(json_config, indent=2))

        print(f"OK Configuration saved to {self.env_path}")
        print(f"OK Category config saved to {self.config_path}")

    def _generate_env_content(self, config: Dict[str, Any]) -> str:
        """
        Generate .env file content from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            .env file content as string
        """
        lines = [
            "# Enhanced Cognee Configuration",
            f"# Generated: {self._get_timestamp()}",
            "",
            "# Enhanced Mode",
            "ENHANCED_COGNEE_MODE=true",
            "",
            "# Installation Mode",
            f'INSTALLATION_MODE={config.get("INSTALLATION_MODE", "full")}',
            "",
            "# LLM Provider",
            f'LLM_PROVIDER={config.get("LLM_PROVIDER", "")}',
        ]

        # Add API keys based on provider
        if config.get("LLM_PROVIDER") == "anthropic":
            lines.append(f'ANTHROPIC_API_KEY={config.get("ANTHROPIC_API_KEY", "")}')
        elif config.get("LLM_PROVIDER") == "openai":
            lines.append(f'OPENAI_API_KEY={config.get("OPENAI_API_KEY", "")}')
        elif config.get("LLM_PROVIDER") == "litellm":
            lines.append(f'LITELLM_API_KEY={config.get("LITELLM_API_KEY", "")}')

        lines.extend([
            "",
            "# PostgreSQL Configuration",
            f"POSTGRES_HOST=localhost",
            f'POSTGRES_PORT={config.get("POSTGRES_PORT", "25432")}',
            "POSTGRES_DB=cognee_db",
            "POSTGRES_USER=cognee_user",
            f'POSTGRES_PASSWORD={config.get("POSTGRES_PASSWORD", "")}',
            "",
            "# Qdrant Configuration",
            f"QDRANT_HOST=localhost",
            f'QDRANT_PORT={config.get("QDRANT_PORT", "26333")}',
            "",
            "# Neo4j Configuration",
            f'NEO4J_URI=bolt://localhost:{config.get("NEO4J_PORT", "27687")}',
            "NEO4J_USER=neo4j",
            f'NEO4J_PASSWORD={config.get("NEO4J_PASSWORD", "")}',
            "",
            "# Redis Configuration",
            f"REDIS_HOST=localhost",
            f'REDIS_PORT={config.get("REDIS_PORT", "26379")}',
            f'REDIS_PASSWORD={config.get("REDIS_PASSWORD", "")}',
            "",
            "# Automation Preferences",
            f'AUTO_MEMORY_CAPTURE={config.get("AUTO_MEMORY_CAPTURE", "false")}',
            f'AUTO_DEDUPLICATION={config.get("AUTO_DEDUPLICATION", "false")}',
            f'AUTO_SUMMARIZATION={config.get("AUTO_SUMMARIZATION", "false")}',
            "",
            "# Dynamic Categories",
            "MEMORY_CATEGORIZATION=true",
            'ENHANCED_COGNEE_CONFIG_PATH=.enhanced-cognee-config.json',
            "",
            "# End of configuration"
        ])

        return "\n".join(lines)

    def _verify_setup(self) -> bool:
        """
        Verify that setup was successful.

        Returns:
            True if verification passed, False otherwise
        """
        print()
        print("Verifying setup...")

        # Check .env file exists
        if not self.env_path.exists():
            print("ERR .env file not created")
            return False

        # Check config file exists
        if not self.config_path.exists():
            print("ERR Config file not created")
            return False

        # Verify .env is not empty
        if self.env_path.stat().st_size == 0:
            print("ERR .env file is empty")
            return False

        print("OK All configuration files created")
        return True

    def _print_success(self):
        """Print success message."""
        print()
        print("=" * 60)
        print("  Setup Complete!")
        print("=" * 60)
        print()
        print("Enhanced Cognee is ready to use!")
        print()
        print("Next steps:")
        print("  1. Start databases (Full mode):")
        print("     docker compose -f docker/docker-compose-enhanced-cognee.yml up -d")
        print()
        print("  2. Start the MCP server:")
        print("     python enhanced_cognee_mcp_server.py")
        print()
        print("  3. Verify installation:")
        print("     python preflight.py")
        print()
        print("For more information, see README.md")
        print()

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def main():
    """Main entry point for setup wizard."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Cognee Setup Wizard"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode with all defaults"
    )

    args = parser.parse_args()

    if args.non_interactive:
        print("Non-interactive mode not yet implemented")
        print("Please run setup wizard interactively:")
        print("  python setup_wizard.py")
        sys.exit(1)

    wizard = SetupWizard()
    success = wizard.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
