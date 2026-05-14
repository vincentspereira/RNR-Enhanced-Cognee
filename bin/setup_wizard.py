"""
Enhanced Cognee - Setup Wizard
================================
Interactive setup wizard for Enhanced Cognee configuration.
Generates secure passwords and creates .env file automatically.

Steps:
  1. LLM provider selection
  2. Database port configuration
  3. Installation mode (Full / Lite)
  4. Automation preferences
  5. Security (auto-generate passwords)
  6. Docker startup (offer to start containers)
  7. Health check (poll all 4 services)
  8. MCP config (print claude.json snippet)

Author: Enhanced Cognee Team
Version: 1.1.0 (Phase 7 enhancement - 2026-05-13)
"""

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BIN_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BIN_DIR.parent
_DOCKER_COMPOSE_FILE = (
    _PROJECT_ROOT / "config" / "docker" / "docker-compose-enhanced-cognee.yml"
)
_MCP_SERVER = _BIN_DIR / "enhanced_cognee_mcp_server.py"

_DEFAULT_PORTS = {
    "POSTGRES": "25432",
    "QDRANT": "26333",
    "NEO4J": "27687",
    "REDIS": "26379",
}

_SERVICE_LABELS = {
    "POSTGRES": "PostgreSQL",
    "QDRANT": "Qdrant",
    "NEO4J": "Neo4j",
    "REDIS": "Redis",
}


# ---------------------------------------------------------------------------
# SetupWizard
# ---------------------------------------------------------------------------

class SetupWizard:
    """
    Interactive setup wizard for Enhanced Cognee.

    Guides users through initial configuration with sensible defaults
    and secure password generation.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        non_interactive: bool = False,
    ):
        self.project_root = project_root or _PROJECT_ROOT
        self.env_path = self.project_root / ".env"
        self.config_path = self.project_root / ".enhanced-cognee-config.json"
        self.non_interactive = non_interactive

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """
        Run the full setup wizard.

        Returns:
            True if setup completed successfully, False otherwise.
        """
        self._print_header()

        if self.env_path.exists() and not self.non_interactive:
            print("WARN Existing .env file found")
            response = self._ask("Do you want to overwrite it? (y/N): ", "n")
            if response.lower() != "y":
                print("Setup cancelled. Existing configuration preserved.")
                return False

        # Steps 1-5: collect and save configuration
        config = self._collect_configuration()
        self._save_configuration(config)

        if not self._verify_setup():
            print("ERR Setup verification failed")
            return False

        # Step 6: offer to start Docker services
        self._step_docker_startup(config)

        # Step 7: health check
        self._step_health_check(config)

        # Step 8: print MCP config snippet
        self._step_mcp_config(config)

        self._print_success()
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ask(self, prompt: str, default: str = "") -> str:
        """Print prompt and read input; return default when non-interactive."""
        if self.non_interactive:
            return default
        try:
            answer = input(prompt).strip()
            return answer if answer else default
        except (EOFError, KeyboardInterrupt):
            return default

    def _print_header(self):
        print("=" * 60)
        print("  Enhanced Cognee Setup Wizard v1.1")
        print("=" * 60)
        print()
        if self.non_interactive:
            print("Running in non-interactive mode (all defaults applied).")
        else:
            print("This wizard will guide you through the initial setup.")
            print("Press Enter to accept the default shown in [brackets].")
        print()

    # ------------------------------------------------------------------
    # Configuration collection (Steps 1-5)
    # ------------------------------------------------------------------

    def _collect_configuration(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {}

        # Step 1: LLM provider
        print("Step 1: LLM Provider Configuration")
        print("-" * 60)
        print("Select your preferred LLM provider:")
        print("  1. Anthropic Claude (recommended)")
        print("  2. OpenAI GPT")
        print("  3. LiteLLM (multi-provider)")
        print("  4. Skip (configure later)")
        choice = self._ask("Enter choice (1-4) [1]: ", "1")

        if choice == "1":
            config["LLM_PROVIDER"] = "anthropic"
            api_key = self._ask("Enter your Anthropic API key (or Enter to skip): ", "")
            if api_key:
                config["ANTHROPIC_API_KEY"] = api_key
        elif choice == "2":
            config["LLM_PROVIDER"] = "openai"
            api_key = self._ask("Enter your OpenAI API key (or Enter to skip): ", "")
            if api_key:
                config["OPENAI_API_KEY"] = api_key
        elif choice == "3":
            config["LLM_PROVIDER"] = "litellm"
            api_key = self._ask("Enter your LiteLLM API key (or Enter to skip): ", "")
            if api_key:
                config["LITELLM_API_KEY"] = api_key
        else:
            config["LLM_PROVIDER"] = ""
        print()

        # Step 2: Database ports
        print("Step 2: Database Port Configuration")
        print("-" * 60)
        print("Enhanced Cognee uses non-standard ports to avoid conflicts.")
        for key, label in _SERVICE_LABELS.items():
            default_port = _DEFAULT_PORTS[key]
            port_key = f"{key}_PORT"
            value = self._ask(
                f"  {label} port [{default_port}]: ",
                default_port,
            )
            config[port_key] = value
        print()

        # Step 3: Installation mode
        print("Step 3: Installation Mode")
        print("-" * 60)
        print("  1. Full Mode - All 4 databases (PostgreSQL, Qdrant, Neo4j, Redis)")
        print("  2. Lite Mode - SQLite only (simpler, fewer features)")
        mode_choice = self._ask("Enter choice (1-2) [1]: ", "1")
        config["INSTALLATION_MODE"] = "full" if mode_choice == "1" else "lite"
        print()

        # Step 4: Automation preferences
        print("Step 4: Automation Preferences")
        print("-" * 60)
        print("All automation is DISABLED by default for security.")
        auto_capture = self._ask("Enable auto memory capture? (y/N): ", "n")
        config["AUTO_MEMORY_CAPTURE"] = "true" if auto_capture.lower() == "y" else "false"
        auto_dedup = self._ask("Enable auto deduplication (weekly)? (y/N): ", "n")
        config["AUTO_DEDUPLICATION"] = "true" if auto_dedup.lower() == "y" else "false"
        auto_sum = self._ask("Enable auto summarization (monthly)? (y/N): ", "n")
        config["AUTO_SUMMARIZATION"] = "true" if auto_sum.lower() == "y" else "false"
        print()

        # Step 5: Security - auto-generate passwords
        print("Step 5: Security Configuration")
        print("-" * 60)
        print("Generating secure passwords...")
        config["POSTGRES_PASSWORD"] = secrets.token_urlsafe(16)
        config["NEO4J_PASSWORD"] = secrets.token_urlsafe(16)
        config["REDIS_PASSWORD"] = secrets.token_urlsafe(16)
        print("OK Secure passwords generated")
        print()

        return config

    # ------------------------------------------------------------------
    # Save & verify
    # ------------------------------------------------------------------

    def _save_configuration(self, config: Dict[str, Any]):
        env_content = self._generate_env_content(config)
        self.env_path.write_text(env_content, encoding="utf-8")

        json_config = {
            "categories": {
                "default": {"prefix": "default_", "description": "Default memories"},
                "trading": {"prefix": "trading_", "description": "Trading system memories"},
                "development": {"prefix": "dev_", "description": "Development memories"},
            }
        }
        self.config_path.write_text(json.dumps(json_config, indent=2), encoding="utf-8")

        print(f"OK Configuration saved to {self.env_path}")
        print(f"OK Category config saved to {self.config_path}")

    def _generate_env_content(self, config: Dict[str, Any]) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# Enhanced Cognee Configuration",
            f"# Generated: {ts}",
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

        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LITELLM_API_KEY"):
            if key in config:
                lines.append(f'{key}={config[key]}')

        pg_port = config.get("POSTGRES_PORT", _DEFAULT_PORTS["POSTGRES"])
        neo4j_port = config.get("NEO4J_PORT", _DEFAULT_PORTS["NEO4J"])

        lines.extend([
            "",
            "# PostgreSQL Configuration",
            "POSTGRES_HOST=localhost",
            f"POSTGRES_PORT={pg_port}",
            "POSTGRES_DB=cognee_db",
            "POSTGRES_USER=cognee_user",
            f'POSTGRES_PASSWORD={config.get("POSTGRES_PASSWORD", "")}',
            "",
            "# Qdrant Configuration",
            "QDRANT_HOST=localhost",
            f'QDRANT_PORT={config.get("QDRANT_PORT", _DEFAULT_PORTS["QDRANT"])}',
            "",
            "# Neo4j Configuration",
            f"NEO4J_URI=bolt://localhost:{neo4j_port}",
            "NEO4J_USER=neo4j",
            f'NEO4J_PASSWORD={config.get("NEO4J_PASSWORD", "")}',
            "",
            "# Redis Configuration",
            "REDIS_HOST=localhost",
            f'REDIS_PORT={config.get("REDIS_PORT", _DEFAULT_PORTS["REDIS"])}',
            f'REDIS_PASSWORD={config.get("REDIS_PASSWORD", "")}',
            "",
            "# Automation Preferences",
            f'AUTO_MEMORY_CAPTURE={config.get("AUTO_MEMORY_CAPTURE", "false")}',
            f'AUTO_DEDUPLICATION={config.get("AUTO_DEDUPLICATION", "false")}',
            f'AUTO_SUMMARIZATION={config.get("AUTO_SUMMARIZATION", "false")}',
            "",
            "# Dynamic Categories",
            "MEMORY_CATEGORIZATION=true",
            "ENHANCED_COGNEE_CONFIG_PATH=.enhanced-cognee-config.json",
            "",
            "# End of configuration",
        ])
        return "\n".join(lines)

    def _verify_setup(self) -> bool:
        print()
        print("Verifying setup...")
        ok = True

        if not self.env_path.exists():
            print("ERR .env file not created")
            ok = False
        elif self.env_path.stat().st_size == 0:
            print("ERR .env file is empty")
            ok = False
        else:
            print("OK .env file created")

        if not self.config_path.exists():
            print("ERR Category config file not created")
            ok = False
        else:
            print("OK Category config file created")

        return ok

    # ------------------------------------------------------------------
    # Step 6: Docker startup
    # ------------------------------------------------------------------

    def _step_docker_startup(self, config: Dict[str, Any]) -> None:
        """Offer to start Docker services and show progress."""
        print()
        print("Step 6: Docker Services")
        print("-" * 60)

        if config.get("INSTALLATION_MODE") == "lite":
            print("INFO Lite mode selected - Docker not required.")
            return

        if not _DOCKER_COMPOSE_FILE.is_file():
            print(f"WARN docker-compose file not found: {_DOCKER_COMPOSE_FILE}")
            print("     Skipping Docker startup.")
            return

        start = self._ask(
            "Start Docker services now? (Y/n): ", "y"
        )
        if start.lower() == "n":
            print("INFO Skipping Docker startup.")
            print(
                "     Run later: enhanced-cognee docker up"
            )
            return

        print("Starting Docker services (this may take a minute)...")
        cmd = [
            "docker", "compose",
            "-f", str(_DOCKER_COMPOSE_FILE),
            "--project-name", "enhanced-cognee",
            "up", "-d",
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=False,
            )
            if result.returncode == 0:
                print("OK  Docker services started.")
            else:
                print("ERR docker compose up failed (exit code %d)." % result.returncode)
                print("     Run manually: enhanced-cognee docker up")
        except FileNotFoundError:
            print("ERR 'docker' command not found.")
            print("     Install Docker Desktop and re-run 'enhanced-cognee setup'.")

    # ------------------------------------------------------------------
    # Step 7: Health check
    # ------------------------------------------------------------------

    def _step_health_check(self, config: Dict[str, Any]) -> None:
        """Poll all four services via TCP and report status."""
        print()
        print("Step 7: Health Check")
        print("-" * 60)

        if config.get("INSTALLATION_MODE") == "lite":
            print("INFO Lite mode - only PostgreSQL/SQLite required.")
            return

        services = [
            ("PostgreSQL", "localhost", int(config.get("POSTGRES_PORT", _DEFAULT_PORTS["POSTGRES"]))),
            ("Qdrant",     "localhost", int(config.get("QDRANT_PORT",   _DEFAULT_PORTS["QDRANT"]))),
            ("Neo4j",      "localhost", int(config.get("NEO4J_PORT",    _DEFAULT_PORTS["NEO4J"]))),
            ("Redis",      "localhost", int(config.get("REDIS_PORT",    _DEFAULT_PORTS["REDIS"]))),
        ]

        max_wait = 30  # seconds total
        poll_interval = 2
        deadline = time.monotonic() + max_wait
        remaining = list(services)
        ok_set: set = set()

        print(f"Waiting up to {max_wait}s for services to become reachable...")

        while remaining and time.monotonic() < deadline:
            still_waiting = []
            for name, host, port in remaining:
                if _tcp_check(host, port):
                    print(f"  OK   {name} ({host}:{port})")
                    ok_set.add(name)
                else:
                    still_waiting.append((name, host, port))
            remaining = still_waiting
            if remaining:
                time.sleep(poll_interval)

        for name, host, port in remaining:
            print(f"  WARN {name} ({host}:{port}) - not reachable yet")

        if not remaining:
            print("OK  All services reachable.")
        else:
            print(
                "WARN Some services did not start in time. "
                "Run 'enhanced-cognee health' to check again."
            )

    # ------------------------------------------------------------------
    # Step 8: MCP config snippet
    # ------------------------------------------------------------------

    def _step_mcp_config(self, config: Dict[str, Any]) -> None:
        """Print the MCP server config snippet for claude.json."""
        print()
        print("Step 8: MCP Server Configuration")
        print("-" * 60)
        print("Add the following to your ~/.claude.json (mcpServers section):")
        print()

        server_path = str(_MCP_SERVER).replace("\\", "/")
        pg_port = config.get("POSTGRES_PORT", _DEFAULT_PORTS["POSTGRES"])
        qd_port = config.get("QDRANT_PORT", _DEFAULT_PORTS["QDRANT"])
        neo_port = config.get("NEO4J_PORT", _DEFAULT_PORTS["NEO4J"])
        redis_port = config.get("REDIS_PORT", _DEFAULT_PORTS["REDIS"])
        pg_pass = config.get("POSTGRES_PASSWORD", "<your-postgres-password>")
        neo_pass = config.get("NEO4J_PASSWORD", "<your-neo4j-password>")

        snippet = {
            "cognee": {
                "command": "python",
                "args": [server_path],
                "env": {
                    "ENHANCED_COGNEE_MODE": "true",
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": pg_port,
                    "POSTGRES_DB": "cognee_db",
                    "POSTGRES_USER": "cognee_user",
                    "POSTGRES_PASSWORD": pg_pass,
                    "QDRANT_HOST": "localhost",
                    "QDRANT_PORT": qd_port,
                    "NEO4J_URI": f"bolt://localhost:{neo_port}",
                    "NEO4J_USER": "neo4j",
                    "NEO4J_PASSWORD": neo_pass,
                    "REDIS_HOST": "localhost",
                    "REDIS_PORT": redis_port,
                },
            }
        }

        # Print as JSON without Unicode (pure ASCII)
        print(json.dumps({"mcpServers": snippet}, indent=2))
        print()
        print("NOTE: Passwords shown above are already saved in .env")
        print("      Keep .env out of version control (.gitignore).")

    # ------------------------------------------------------------------
    # Success banner
    # ------------------------------------------------------------------

    def _print_success(self):
        print()
        print("=" * 60)
        print("  Setup Complete!")
        print("=" * 60)
        print()
        print("Enhanced Cognee is configured and ready.")
        print()
        print("Next steps:")
        print("  Start databases:        enhanced-cognee docker up")
        print("  Check service health:   enhanced-cognee health")
        print("  Start the MCP server:   enhanced-cognee start")
        print("  View this wizard again: enhanced-cognee setup")
        print()
        print("For more information, see README.md")
        print()


# ---------------------------------------------------------------------------
# TCP helper (duplicated here so setup_wizard is self-contained)
# ---------------------------------------------------------------------------

def _tcp_check(host: str, port: int, timeout: float = 1.5) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Main entry point for setup wizard."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Cognee Setup Wizard"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run with all defaults, no prompts (for CI/scripted installs)",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Override project root directory",
    )
    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else None
    wizard = SetupWizard(project_root=root, non_interactive=args.non_interactive)
    success = wizard.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
