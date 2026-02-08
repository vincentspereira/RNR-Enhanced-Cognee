"""
Enhanced Cognee - Pre-flight Checks

Verification script to ensure all systems are operational before use.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class PreflightChecker:
    """
    Pre-flight checker for Enhanced Cognee.

    Verifies all dependencies and services are operational.
    """

    def __init__(self):
        """Initialize pre-flight checker."""
        self.project_root = Path.cwd()
        self.env_path = self.project_root / ".env"
        self.results = {}

    async def run_all_checks(self) -> bool:
        """
        Run all pre-flight checks.

        Returns:
            True if all checks passed, False otherwise
        """
        print("=" * 60)
        print("  Enhanced Cognee Pre-flight Checks")
        print("=" * 60)
        print()

        # Run checks
        checks = [
            ("Configuration Files", self._check_config_files),
            ("Python Dependencies", self._check_python_deps),
            ("Environment Variables", self._check_env_vars),
            ("PostgreSQL", self._check_postgres),
            ("Qdrant", self._check_qdrant),
            ("Neo4j", self._check_neo4j),
            ("Redis", self._check_redis),
        ]

        all_passed = True
        for check_name, check_func in checks:
            try:
                result = await check_func()
                self.results[check_name] = result
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f"ERR {check_name}: {e}")
                self.results[check_name] = False
                all_passed = False

        # Print summary
        self._print_summary()

        return all_passed

    async def _check_config_files(self) -> bool:
        """Check if configuration files exist."""
        print("Checking configuration files...")

        required_files = [
            self.env_path,
            self.project_root / ".enhanced-cognee-config.json",
            self.project_root / "automation_config.json",
        ]

        all_exist = True
        for file_path in required_files:
            if file_path.exists():
                print(f"  OK {file_path.name}")
            else:
                print(f"  WARN {file_path.name} not found (run setup_wizard.py)")
                all_exist = False

        return all_exist

    async def _check_python_deps(self) -> bool:
        """Check if Python dependencies are installed."""
        print("Checking Python dependencies...")

        required_packages = [
            ("asyncpg", "PostgreSQL adapter"),
            ("qdrant_client", "Qdrant client"),
            ("neo4j", "Neo4j driver"),
            ("redis", "Redis client"),
            ("tiktoken", "Token counting"),
            ("anthropic", "Anthropic API"),
            ("openai", "OpenAI API"),
        ]

        all_installed = True
        for package, description in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"  OK {package} ({description})")
            except ImportError:
                print(f"  WARN {package} not installed ({description})")
                all_installed = False

        return all_installed

    async def _check_env_vars(self) -> bool:
        """Check if environment variables are set."""
        print("Checking environment variables...")

        # Load .env file
        if not self.env_path.exists():
            print("  WARN .env file not found")
            return False

        # Read and parse .env
        env_vars = {}
        with open(self.env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

        # Check required variables
        required_vars = [
            ("ENHANCED_COGNEE_MODE", "Enhanced mode flag"),
            ("POSTGRES_HOST", "PostgreSQL host"),
            ("POSTGRES_PORT", "PostgreSQL port"),
            ("POSTGRES_DB", "PostgreSQL database"),
            ("POSTGRES_USER", "PostgreSQL user"),
            ("QDRANT_HOST", "Qdrant host"),
            ("QDRANT_PORT", "Qdrant port"),
        ]

        all_set = True
        for var, description in required_vars:
            if var in env_vars and env_vars[var]:
                # Mask passwords in output
                if "PASSWORD" in var and env_vars[var]:
                    print(f"  OK {var} ({description}): ******")
                else:
                    print(f"  OK {var} ({description}): {env_vars[var]}")
            else:
                print(f"  WARN {var} not set ({description})")
                all_set = False

        return all_set

    async def _check_postgres(self) -> bool:
        """Check PostgreSQL connection."""
        print("Checking PostgreSQL...")

        try:
            import asyncpg

            # Load connection details from .env
            env = self._load_env()
            host = env.get("POSTGRES_HOST", "localhost")
            port = int(env.get("POSTGRES_PORT", "25432"))
            database = env.get("POSTGRES_DB", "cognee_db")
            user = env.get("POSTGRES_USER", "cognee_user")
            password = env.get("POSTGRES_PASSWORD", "")

            # Test connection
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password
                ),
                timeout=5
            )

            # Check version
            version = await conn.fetchval("SELECT version()")
            await conn.close()

            print(f"  OK PostgreSQL connected")
            print(f"    Version: {version.split()[1]}")

            return True

        except asyncio.TimeoutError:
            print("  WARN PostgreSQL connection timeout")
            return False
        except Exception as e:
            print(f"  WARN PostgreSQL not available: {e}")
            return False

    async def _check_qdrant(self) -> bool:
        """Check Qdrant connection."""
        print("Checking Qdrant...")

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.exceptions import UnexpectedResponse

            # Load connection details from .env
            env = self._load_env()
            host = env.get("QDRANT_HOST", "localhost")
            port = int(env.get("QDRANT_PORT", "26333"))

            # Test connection
            client = QdrantClient(host=host, port=port, timeout=5)
            collections = client.get_collections()

            print(f"  OK Qdrant connected")
            print(f"    Collections: {len(collections.collections)}")

            return True

        except Exception as e:
            print(f"  WARN Qdrant not available: {e}")
            return False

    async def _check_neo4j(self) -> bool:
        """Check Neo4j connection."""
        print("Checking Neo4j...")

        try:
            from neo4j import AsyncGraphDatabase

            # Load connection details from .env
            env = self._load_env()
            uri = env.get("NEO4J_URI", "bolt://localhost:27687")
            user = env.get("NEO4J_USER", "neo4j")
            password = env.get("NEO4J_PASSWORD", "")

            # Test connection
            driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS test")
                value = await result.single()
                await driver.close()

            print(f"  OK Neo4j connected")

            return True

        except Exception as e:
            print(f"  WARN Neo4j not available: {e}")
            return False

    async def _check_redis(self) -> bool:
        """Check Redis connection."""
        print("Checking Redis...")

        try:
            import redis.asyncio as redis

            # Load connection details from .env
            env = self._load_env()
            host = env.get("REDIS_HOST", "localhost")
            port = int(env.get("REDIS_PORT", "26379"))
            password = env.get("REDIS_PASSWORD", "")

            # Test connection
            if password:
                client = redis.Redis(host=host, port=port, password=password, decode_responses=True)
            else:
                client = redis.Redis(host=host, port=port, decode_responses=True)

            await client.ping()
            await client.close()

            print(f"  OK Redis connected")

            return True

        except Exception as e:
            print(f"  WARN Redis not available: {e}")
            return False

    def _load_env(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env = {}
        if self.env_path.exists():
            with open(self.env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env[key.strip()] = value.strip()
        return env

    def _print_summary(self):
        """Print check summary."""
        print()
        print("=" * 60)
        print("  Summary")
        print("=" * 60)
        print()

        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)

        print(f"Checks Passed: {passed}/{total}")
        print()

        for check_name, result in self.results.items():
            status = "OK" if result else "WARN"
            print(f"  [{status}] {check_name}")

        print()

        if passed == total:
            print("All systems operational! Enhanced Cognee is ready to use.")
        else:
            print("Some issues detected. Please fix the warnings above.")
            print("Run 'python setup_wizard.py' if configuration is missing.")


async def main():
    """Main entry point for pre-flight checks."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Cognee Pre-flight Checks"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix common issues"
    )

    args = parser.parse_args()

    checker = PreflightChecker()
    success = await checker.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
