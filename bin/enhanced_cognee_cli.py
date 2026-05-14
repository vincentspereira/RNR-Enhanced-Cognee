"""
Enhanced Cognee CLI
===================
Entry point: enhanced-cognee

Commands:
  setup     Run the interactive setup wizard
  start     Start the Enhanced Cognee MCP server
  docker    Manage Docker services (up / down / status)
  health    Check connectivity to all four Enhanced Cognee databases
  version   Print the package version

All output is ASCII-only (Windows cp1252 compatible).
"""

import argparse
import os
import subprocess
import sys
import socket
import time

# ---------------------------------------------------------------------------
# Locate project root (one level above this bin/ directory)
# ---------------------------------------------------------------------------
_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BIN_DIR)
_DOCKER_COMPOSE_FILE = os.path.join(
    _PROJECT_ROOT, "config", "docker", "docker-compose-enhanced-cognee.yml"
)
_MCP_SERVER = os.path.join(_BIN_DIR, "enhanced_cognee_mcp_server.py")
_SETUP_WIZARD = os.path.join(_BIN_DIR, "setup_wizard.py")


# ---------------------------------------------------------------------------
# Version helper
# ---------------------------------------------------------------------------

def _read_version() -> str:
    """Read version from pyproject.toml without importing the package."""
    pyproject = os.path.join(_PROJECT_ROOT, "pyproject.toml")
    try:
        with open(pyproject, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("version"):
                    # version = "1.0.9-enhanced"
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# Health check helpers
# ---------------------------------------------------------------------------

_SERVICES = {
    "PostgreSQL": ("POSTGRES_HOST", "POSTGRES_PORT", "localhost", "25432"),
    "Qdrant": ("QDRANT_HOST", "QDRANT_PORT", "localhost", "26333"),
    "Neo4j": ("NEO4J_HOST", "NEO4J_PORT", "localhost", "27687"),
    "Redis": ("REDIS_HOST", "REDIS_PORT", "localhost", "26379"),
}


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _load_dotenv_simple() -> None:
    """Minimal .env loader so health check works without python-dotenv installed."""
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------

def cmd_version(_args) -> int:
    ver = _read_version()
    print(f"Enhanced Cognee {ver}")
    return 0


def cmd_health(_args) -> int:
    _load_dotenv_simple()
    all_ok = True
    print("Enhanced Cognee Health Check")
    print("-" * 32)
    for name, (host_var, port_var, def_host, def_port) in _SERVICES.items():
        host = os.environ.get(host_var, def_host)
        port_str = os.environ.get(port_var, def_port)
        try:
            port = int(port_str)
        except ValueError:
            port = int(def_port)
        ok = _tcp_check(host, port)
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"  {status:<6} {name} ({host}:{port})")
    print("-" * 32)
    if all_ok:
        print("All services reachable.")
        return 0
    else:
        print("WARN: One or more services are unreachable.")
        print("      Run 'enhanced-cognee docker up' to start them.")
        return 1


def cmd_setup(_args) -> int:
    print("Starting Enhanced Cognee Setup Wizard...")
    print("=" * 40)
    # Import and run setup wizard directly if possible; otherwise subprocess
    try:
        sys.path.insert(0, _BIN_DIR)
        from setup_wizard import SetupWizard  # type: ignore
        wizard = SetupWizard()
        wizard.run()
        return 0
    except Exception as exc:
        # Fallback: run as subprocess
        print(f"Direct import failed ({exc}); running as subprocess.")
        result = subprocess.run(
            [sys.executable, _SETUP_WIZARD],
            cwd=_PROJECT_ROOT,
        )
        return result.returncode


def cmd_start(args) -> int:
    """Start the Enhanced Cognee MCP server (foreground unless --detach)."""
    detach = getattr(args, "detach", False)
    python = sys.executable
    cmd = [python, _MCP_SERVER]
    if not os.path.isfile(_MCP_SERVER):
        print(f"ERR MCP server not found: {_MCP_SERVER}")
        return 2

    if detach:
        # Background process; print PID for reference
        proc = subprocess.Popen(
            cmd,
            cwd=_PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"OK  MCP server started in background (PID {proc.pid})")
        print(f"    To stop: kill {proc.pid}")
    else:
        print("Starting Enhanced Cognee MCP Server (Ctrl+C to stop)...")
        try:
            subprocess.run(cmd, cwd=_PROJECT_ROOT, check=False)
        except KeyboardInterrupt:
            print("\nServer stopped by user.")
    return 0


def cmd_docker(args) -> int:
    """Manage Docker services."""
    action = getattr(args, "action", "status")
    if not os.path.isfile(_DOCKER_COMPOSE_FILE):
        print(f"ERR docker-compose file not found: {_DOCKER_COMPOSE_FILE}")
        return 2

    base_cmd = [
        "docker", "compose",
        "-f", _DOCKER_COMPOSE_FILE,
        "--project-name", "enhanced-cognee",
    ]

    if action == "up":
        print("Starting Enhanced Cognee Docker services...")
        cmd = base_cmd + ["up", "-d"]
        result = subprocess.run(cmd, cwd=_PROJECT_ROOT)
        if result.returncode == 0:
            print("OK  Docker services started.")
            print("    Run 'enhanced-cognee health' to verify connectivity.")
        else:
            print("ERR docker compose up failed.")
        return result.returncode

    elif action == "down":
        print("Stopping Enhanced Cognee Docker services...")
        result = subprocess.run(base_cmd + ["down"], cwd=_PROJECT_ROOT)
        if result.returncode == 0:
            print("OK  Docker services stopped.")
        else:
            print("ERR docker compose down failed.")
        return result.returncode

    elif action == "status":
        result = subprocess.run(base_cmd + ["ps"], cwd=_PROJECT_ROOT)
        return result.returncode

    elif action == "logs":
        tail = getattr(args, "tail", "100")
        service = getattr(args, "service", None)
        log_cmd = base_cmd + ["logs", "--tail", str(tail)]
        if service:
            log_cmd.append(service)
        result = subprocess.run(log_cmd, cwd=_PROJECT_ROOT)
        return result.returncode

    else:
        print(f"ERR Unknown docker action: {action}")
        return 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enhanced-cognee",
        description="Enhanced Cognee - enterprise memory MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  enhanced-cognee setup                # interactive first-time setup
  enhanced-cognee docker up            # start all four database containers
  enhanced-cognee health               # check DB connectivity
  enhanced-cognee start                # run MCP server (foreground)
  enhanced-cognee start --detach       # run MCP server (background)
  enhanced-cognee docker logs          # tail Docker logs
  enhanced-cognee version              # print version string
""",
    )

    subs = parser.add_subparsers(dest="command", metavar="<command>")
    subs.required = True

    # -- version --
    subs.add_parser(
        "version",
        help="Print the Enhanced Cognee version",
    )

    # -- health --
    subs.add_parser(
        "health",
        help="Check connectivity to all four Enhanced Cognee databases",
    )

    # -- setup --
    subs.add_parser(
        "setup",
        help="Run the interactive setup wizard",
    )

    # -- start --
    start_p = subs.add_parser(
        "start",
        help="Start the Enhanced Cognee MCP server",
    )
    start_p.add_argument(
        "--detach", "-d",
        action="store_true",
        help="Run server in the background",
    )

    # -- docker --
    docker_p = subs.add_parser(
        "docker",
        help="Manage Docker services (up / down / status / logs)",
    )
    docker_subs = docker_p.add_subparsers(dest="action", metavar="<action>")
    docker_subs.required = True

    docker_subs.add_parser("up", help="Start all Docker services (detached)")
    docker_subs.add_parser("down", help="Stop all Docker services")
    docker_subs.add_parser("status", help="Show Docker service status")

    logs_p = docker_subs.add_parser("logs", help="Tail Docker service logs")
    logs_p.add_argument(
        "--tail", default="100", metavar="N",
        help="Number of log lines to show (default: 100)",
    )
    logs_p.add_argument(
        "service", nargs="?", default=None,
        help="Optional service name (postgres-enhanced, qdrant-enhanced, etc.)",
    )

    # -- migrate --
    migrate_p = subs.add_parser(
        "migrate",
        help="Run Enhanced Cognee database schema migrations",
    )
    migrate_subs = migrate_p.add_subparsers(dest="action", metavar="<action>")
    migrate_subs.required = True
    _up = migrate_subs.add_parser("upgrade", help="Apply migrations (default: head)")
    _up.add_argument("revision", nargs="?", default="head",
                     help="Target revision (default: head)")
    _dn = migrate_subs.add_parser("downgrade", help="Revert migrations")
    _dn.add_argument("revision", nargs="?", default="-1",
                     help="Target revision (default: -1 = one step back)")
    migrate_subs.add_parser("current", help="Show current migration revision")
    migrate_subs.add_parser("history", help="Show migration history")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def cmd_migrate(args) -> int:
    """Run Enhanced Cognee database schema migrations via Alembic."""
    action = getattr(args, "action", "upgrade")
    revision = getattr(args, "revision", "head")
    _ALEMBIC_INI = os.path.join(_PROJECT_ROOT, "alembic-enhanced.ini")
    if not os.path.isfile(_ALEMBIC_INI):
        print(f"ERR alembic-enhanced.ini not found: {_ALEMBIC_INI}")
        return 2

    # Load .env so DB credentials are available
    _load_dotenv_simple()

    if action == "upgrade":
        print(f"Running migration: upgrade to {revision}")
        cmd = [sys.executable, "-m", "alembic", "-c", _ALEMBIC_INI, "upgrade", revision]
    elif action == "downgrade":
        print(f"Running migration: downgrade to {revision}")
        cmd = [sys.executable, "-m", "alembic", "-c", _ALEMBIC_INI, "downgrade", revision]
    elif action == "current":
        cmd = [sys.executable, "-m", "alembic", "-c", _ALEMBIC_INI, "current"]
    elif action == "history":
        cmd = [sys.executable, "-m", "alembic", "-c", _ALEMBIC_INI, "history"]
    else:
        print(f"ERR Unknown migrate action: {action}")
        return 1

    result = subprocess.run(cmd, cwd=_PROJECT_ROOT)
    if result.returncode == 0 and action in ("upgrade", "downgrade"):
        print("OK  Migration complete.")
    return result.returncode


_COMMAND_MAP = {
    "version": cmd_version,
    "health": cmd_health,
    "setup": cmd_setup,
    "start": cmd_start,
    "docker": cmd_docker,
    "migrate": cmd_migrate,
}


def cli() -> None:
    """Entry point for the 'enhanced-cognee' console script."""
    parser = build_parser()
    args = parser.parse_args()
    handler = _COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(handler(args))


if __name__ == "__main__":
    cli()
