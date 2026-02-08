"""
Enhanced Cognee Lite Mode - Interactive Setup Wizard

Guides users through Lite mode setup with interactive prompts.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.lite_mode.sqlite_manager import SQLiteManager


def print_header():
    """Print setup wizard header."""
    print("")
    print("=" * 60)
    print("Enhanced Cognee Lite Mode - Setup Wizard")
    print("=" * 60)
    print("Lightweight memory system with SQLite")
    print("No Docker required, <2 minute setup")
    print("=" * 60)
    print("")


def print_info(message: str):
    """Print info message (ASCII-only)."""
    print(f"[INFO] {message}")


def print_success(message: str):
    """Print success message (ASCII-only)."""
    print(f"[OK] {message}")


def print_warning(message: str):
    """Print warning message (ASCII-only)."""
    print(f"[WARN] {message}")


def print_error(message: str):
    """Print error message (ASCII-only)."""
    print(f"[ERR] {message}")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """
    Ask user yes/no question.

    Args:
        prompt: Question prompt
        default: Default answer

    Returns:
        True if yes, False if no
    """
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()

    if not response:
        return default

    return response in ['y', 'yes']


def ask_input(prompt: str, default: str = "") -> str:
    """
    Ask user for text input.

    Args:
        prompt: Input prompt
        default: Default value

    Returns:
        User input
    """
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        return input(f"{prompt}: ").strip()


def check_dependencies():
    """Check if required dependencies are installed."""
    print_info("Checking dependencies...")

    # Check Python version
    if sys.version_info < (3, 8):
        print_error(f"Python 3.8+ required (found {sys.version})")
        return False

    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor} found")

    # Check SQLite support
    try:
        sqlite_version = sqlite3.sqlite_version
        print_success(f"SQLite {sqlite_version} available")
    except Exception as e:
        print_error(f"SQLite not available: {e}")
        return False

    return True


def create_directories(base_path: str):
    """Create required directories."""
    print_info("Creating directories...")

    dirs = [
        os.path.join(base_path, "src", "lite_mode"),
        os.path.join(base_path, "migrations"),
        os.path.join(base_path, "backups"),
        os.path.join(base_path, "logs")
    ]

    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print_success(f"Created: {dir_path}")


def initialize_database(db_path: str, schema_path: str):
    """Initialize SQLite database with schema."""
    print_info("Initializing database...")

    # Check if schema file exists
    if not os.path.exists(schema_path):
        print_error(f"Schema file not found: {schema_path}")
        return False

    # Check if database already exists
    if os.path.exists(db_path):
        print_warning(f"Database already exists: {db_path}")
        if not ask_yes_no("Recreate database?", default=False):
            print_info("Using existing database")
            return True

        os.remove(db_path)
        print_info("Removed old database")

    # Create database and load schema
    try:
        conn = sqlite3.connect(db_path)

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Split and execute each statement
        for statement in schema_sql.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    conn.execute(statement)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        print_warning(f"Schema warning: {e}")

        conn.commit()
        conn.close()

        print_success(f"Database created: {db_path}")
        return True

    except Exception as e:
        print_error(f"Failed to initialize database: {e}")
        return False


def test_database(db_path: str):
    """Test database functionality."""
    print_info("Testing database...")

    try:
        db = SQLiteManager(db_path)

        # Health check
        health = db.health_check()
        if health['status'] != 'OK':
            print_error("Health check failed")
            return False

        print_success("Database health: OK")

        # Test adding a document
        doc_id = db.add_document(
            data_id="wizard_test",
            data_text="Enhanced Cognee Lite Mode setup wizard test",
            data_type="test",
            metadata={"setup": "wizard"},
            user_id="wizard",
            agent_id="setup_wizard"
        )

        print_success(f"Test document added: {doc_id}")

        # Test search
        results = db.search_documents("setup", user_id="wizard", limit=1)
        if results:
            print_success(f"Full-text search working: {len(results)} result(s)")
        else:
            print_warning("Full-text search returned no results")

        # Get stats
        stats = db.get_stats()
        print_success(f"Database stats: {stats['total_documents']} documents")

        db.close()

        return True

    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False


def create_config(config_path: str, db_path: str):
    """Create Lite mode configuration file."""
    print_info("Creating configuration...")

    config = {
        "lite_mode": {
            "enabled": True,
            "description": "Enhanced Cognee Lite Mode - SQLite-based memory system",
            "version": "1.0.0",
            "setup_date": None  # Will be set below
        },
        "database": {
            "type": "sqlite",
            "path": db_path,
            "fts5_enabled": True
        },
        "features": {
            "full_text_search": True,
            "metadata_support": True,
            "session_management": True,
            "agent_isolation": True,
            "knowledge_graph": False
        },
        "tools": [
            "add_memory",
            "search_memories",
            "get_memories",
            "get_memory",
            "update_memory",
            "delete_memory",
            "list_agents",
            "health",
            "get_stats",
            "cognify"
        ]
    }

    # Add setup date
    from datetime import datetime
    config["lite_mode"]["setup_date"] = datetime.now().isoformat()

    # Write config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print_success(f"Configuration created: {config_path}")


def print_completion_summary(base_path: str, db_path: str):
    """Print setup completion summary."""
    print("")
    print("=" * 60)
    print("[OK] Lite Mode Setup Complete!")
    print("=" * 60)
    print("")
    print("Summary:")
    print("--------")
    print(f"  Database: {db_path}")
    print(f"  Size: {os.path.getsize(db_path) if os.path.exists(db_path) else 0:,} bytes")
    print(f"  Base path: {base_path}")
    print("")
    print("Next Steps:")
    print("----------")
    print("1. Test Lite mode:")
    print(f"   cd {base_path}")
    print("   python src/lite_mode/lite_mcp_server.py")
    print("")
    print("2. Configure Claude Code:")
    print("   Add to ~/.claude.json (Linux/Mac) or %USERPROFILE%\\.claude.json (Windows):")
    print('   {')
    print('     "mcpServers": {')
    print(f'       "cognee-lite": {{')
    print(f'         "command": "python",')
    print(f'         "args": ["{base_path}/src/lite_mode/lite_mcp_server.py"]')
    print(f'       }}')
    print('     }')
    print('   }')
    print("")
    print("3. Read documentation:")
    print("   docs/LITE_MODE_GUIDE.md")
    print("")
    print("[INFO] Setup time: <2 minutes (no Docker required!)")
    print("=" * 60)
    print("")


def main():
    """Main setup wizard function."""
    print_header()

    # Check dependencies
    if not check_dependencies():
        print_error("Dependency check failed")
        return 1

    # Get base path
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    print_info(f"Base path: {base_path}")

    # Ask for configuration
    print("")
    print("Configuration:")
    print("--------------")

    db_path_default = os.path.join(base_path, "cognee_lite.db")
    db_path = ask_input("Database path", db_path_default)

    print("")
    print("Creating Lite mode setup...")
    print("")

    # Create directories
    create_directories(base_path)

    # Initialize database
    schema_path = os.path.join(base_path, "migrations", "create_lite_schema.sql")
    if not initialize_database(db_path, schema_path):
        print_error("Database initialization failed")
        return 1

    # Test database
    if not test_database(db_path):
        print_error("Database test failed")
        return 1

    # Create configuration
    config_path = os.path.join(base_path, "src", "lite_mode", "lite_config.json")
    create_config(config_path, db_path)

    # Print completion summary
    print_completion_summary(base_path, db_path)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("")
        print_warning("Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
