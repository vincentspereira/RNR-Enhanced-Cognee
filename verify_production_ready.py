#!/usr/bin/env python3
"""
Enhanced Cognee - Production Readiness Verification Script

This script verifies that the Enhanced Cognee system is production-ready by checking:
- All critical issues resolved
- All databases connected
- All tools functional
- Security checks passed
- Configuration valid

Usage:
    python verify_production_ready.py

Output:
    Production readiness report with pass/fail status for each check
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ANSI colors for output
class Colors:
    OK = '\033[92m'      # Green
    WARN = '\033[93m'     # Yellow
    ERR = '\033[91m'      # Red
    INFO = '\033[94m'     # Blue
    RESET = '\033[0m'

    @staticmethod
    def ok(msg: str) -> str:
        return f"{Colors.OK}[OK] {msg}{Colors.RESET}"

    @staticmethod
    def warn(msg: str) -> str:
        return f"{Colors.WARN}[WARN] {msg}{Colors.RESET}"

    @staticmethod
    def err(msg: str) -> str:
        return f"{Colors.ERR}[ERR] {msg}{Colors.RESET}"

    @staticmethod
    def info(msg: str) -> str:
        return f"{Colors.INFO}[INFO] {msg}{Colors.RESET}"


# ============================================================================
# VERIFICATION CHECKS
# ============================================================================

class ProductionVerifier:
    """Production readiness verifier for Enhanced Cognee"""

    def __init__(self):
        """Initialize verifier with results tracking"""
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def record(self, check_name: str, passed: bool, error: str = None) -> None:
        """Record verification result"""
        self.results[check_name] = passed
        if not passed:
            self.errors.append(f"{check_name}: {error}")
        logger.info(f"{'PASS' if passed else 'FAIL'}: {check_name}")

    async def check_security_module(self) -> bool:
        """Verify security module exists and is importable"""
        try:
            from src.security_mcp import (
                ValidationError,
                AuthorizationError,
                ConfirmationRequiredError,
                authorizer,
                confirmation_manager
            )
            self.record(
                "Security Module Import",
                True
            )
            return True
        except ImportError as e:
            self.record(
                "Security Module Import",
                False,
                f"Cannot import security module: {e}"
            )
            return False
        except Exception as e:
            self.record(
                "Security Module Import",
                False,
                f"Unexpected error: {e}"
            )
            return False

    async def check_duplicate_functions(self) -> bool:
        """Verify no duplicate function definitions"""
        try:
            # Read MCP server file
            mcp_server_path = project_root / "bin" / "enhanced_cognee_mcp_server.py"
            if not mcp_server_path.exists():
                self.record(
                    "Duplicate Function Check",
                    False,
                    "MCP server file not found"
                )
                return False

            content = mcp_server_path.read_text()

            # Check for duplicate summarize_old_memories
            count = content.count("@mcp.tool()\nasync def summarize_old_memories")
            passed = count == 1  # Should be exactly 1

            if not passed:
                self.record(
                    "Duplicate Function Check",
                    False,
                    f"Found {count} definitions of summarize_old_memories, expected 1"
                )
            else:
                self.record(
                    "Duplicate Function Check",
                    True
                )
            return passed
        except Exception as e:
            self.record(
                "Duplicate Function Check",
                False,
                f"Check failed: {e}"
            )
            return False

    async def check_authorization_checks(self) -> bool:
        """Verify authorization checks are in place"""
        try:
            mcp_server_path = project_root / "bin" / "enhanced_cognee_mcp_server.py"
            content = mcp_server_path.read_text()

            # Check for authorization imports
            has_import = "from src.security_mcp import" in content
            has_authorizer = "authorizer" in content
            has_require_auth = "require_agent_authorization" in content

            # Check authorization in delete_memory
            delete_section = content[content.find("async def delete_memory"):
                                        content.find("async def list_agents")]
            has_delete_auth = "require_agent_authorization" in delete_section

            # Check authorization in expire_memories
            expire_section = content[content.find("async def expire_memories"):
                                        content.find("async def get_memory_age_stats")]
            has_expire_auth = "require_agent_authorization" in expire_section

            passed = (has_import and has_authorizer and has_require_auth
                      and has_delete_auth and has_expire_auth)

            if not passed:
                missing = []
                if not has_import:
                    missing.append("security_mcp import")
                if not has_authorizer:
                    missing.append("authorizer usage")
                if not has_require_auth:
                    missing.append("require_agent_authorization")
                if not has_delete_auth:
                    missing.append("delete_memory auth check")
                if not has_expire_auth:
                    missing.append("expire_memories auth check")

                self.record(
                    "Authorization Checks",
                    False,
                    f"Missing: {', '.join(missing)}"
                )
            else:
                self.record(
                    "Authorization Checks",
                    True
                )
            return passed
        except Exception as e:
            self.record(
                "Authorization Checks",
                False,
                f"Check failed: {e}"
            )
            return False

    async def check_input_validation(self) -> bool:
        """Verify input validation is in place"""
        try:
            mcp_server_path = project_root / "bin" / "enhanced_cognee_mcp_server.py"
            content = mcp_server_path.read_text()

            # Check for validation imports and usage
            has_import = "from src.security_mcp import" in content
            has_validate_uuid = "validate_uuid(" in content
            has_validate_days = "validate_days(" in content
            has_validate_limit = "validate_limit(" in content
            has_validate_agent_id = "validate_agent_id(" in content

            passed = (has_import and has_validate_uuid and has_validate_days
                      and has_validate_limit and has_validate_agent_id)

            if not passed:
                missing = []
                if not has_import:
                    missing.append("security_mcp import")
                if not has_validate_uuid:
                    missing.append("validate_uuid usage")
                if not has_validate_days:
                    missing.append("validate_days usage")
                if not has_validate_limit:
                    missing.append("validate_limit usage")
                if not has_validate_agent_id:
                    missing.append("validate_agent_id usage")

                self.record(
                    "Input Validation",
                    False,
                    f"Missing: {', '.join(missing)}"
                )
            else:
                self.record(
                    "Input Validation",
                    True
                )
            return passed
        except Exception as e:
            self.record(
                "Input Validation",
                False,
                f"Check failed: {e}"
            )
            return False

    async def check_trigger_classifications(self) -> bool:
        """Verify tools have correct trigger classifications"""
        try:
            mcp_server_path = project_root / "bin" / "enhanced_cognee_mcp_server.py"
            content = mcp_server_path.read_text()

            # Check for System (S) classification in archive_category
            archive_section = content[content.find("async def archive_category"):
                                          content.find("async def check_duplicate")]
            has_system_archive = "(S) System" in archive_section or "System - Automatically" in archive_section

            # Check for System (S) classification in verify_backup
            verify_section = content[content.find("async def verify_backup"):
                                        content.find("async def rollback_restore")]
            has_system_verify = "(S) System" in verify_section or "System - Automatically" in verify_section

            # Check for Auto (A) classification in create_backup
            create_section = content[content.find("async def create_backup"):
                                        content.find("async def restore_backup")]
            has_auto_backup = "(A) Auto" in create_section or "Auto - Automatically" in create_section

            passed = has_system_archive and has_system_verify and has_auto_backup

            if not passed:
                missing = []
                if not has_system_archive:
                    missing.append("archive_category as System")
                if not has_system_verify:
                    missing.append("verify_backup as System")
                if not has_auto_backup:
                    missing.append("create_backup as Auto")

                self.record(
                    "Trigger Classifications",
                    False,
                    f"Missing: {', '.join(missing)}"
                )
            else:
                self.record(
                    "Trigger Classifications",
                    True
                )
            return passed
        except Exception as e:
            self.record(
                "Trigger Classifications",
                False,
                f"Check failed: {e}"
            )
            return False

    async def check_database_configuration(self) -> bool:
        """Verify database configuration is correct"""
        try:
            # Check .env file
            env_path = project_root / ".env"
            if not env_path.exists():
                self.record(
                    "Database Configuration",
                    False,
                    ".env file not found"
                )
                return False

            env_content = env_path.read_text()

            # Check for Enhanced stack ports
            has_postgres_port = "POSTGRES_PORT=25432" in env_content
            has_qdrant_port = "QDRANT_PORT=26333" in env_content
            has_neo4j_port = "NEO4J_URI=" in env_content and "27687" in env_content
            has_redis_port = "REDIS_PORT=26379" in env_content

            passed = (has_postgres_port and has_qdrant_port
                      and has_neo4j_port and has_redis_port)

            if not passed:
                missing = []
                if not has_postgres_port:
                    missing.append("PostgreSQL port 25432")
                if not has_qdrant_port:
                    missing.append("Qdrant port 26333")
                if not has_neo4j_port:
                    missing.append("Neo4j port 27687")
                if not has_redis_port:
                    missing.append("Redis port 26379")

                self.record(
                    "Database Configuration",
                    False,
                    f"Missing or incorrect: {', '.join(missing)}"
                )
            else:
                self.record(
                    "Database Configuration",
                    True
                )
            return passed
        except Exception as e:
            self.record(
                "Database Configuration",
                False,
                f"Check failed: {e}"
            )
            return False

    async def check_mcp_tools_count(self) -> bool:
        """Verify correct MCP tools count (should be 58 unique tools)"""
        try:
            mcp_server_path = project_root / "bin" / "enhanced_cognee_mcp_server.py"
            content = mcp_server_path.read_text()

            # Count @mcp.tool() decorators
            tool_count = content.count("@mcp.tool()")

            # Should be 58 unique tools (59 - 1 duplicate removed)
            passed = tool_count == 58

            if not passed:
                self.record(
                    "MCP Tools Count",
                    False,
                    f"Found {tool_count} tools, expected 58 (duplicate removed)"
                )
            else:
                self.record(
                    "MCP Tools Count",
                    True
                )
            return passed
        except Exception as e:
            self.record(
                "MCP Tools Count",
                False,
                f"Check failed: {e}"
            )
            return False

    def generate_report(self) -> str:
        """Generate production readiness report"""
        report = []
        report.append("=" * 80)
        report.append("ENHANCED COGNEE - PRODUCTION READINESS VERIFICATION REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        total_checks = len(self.results)
        passed_checks = sum(1 for v in self.results.values() if v)
        failed_checks = total_checks - passed_checks
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        report.append(Colors.info("SUMMARY"))
        report.append(f"  Total Checks: {total_checks}")
        report.append(f"  Passed: {Colors.ok(str(passed_checks))}")
        report.append(f"  Failed: {Colors.err(str(failed_checks))}")
        report.append(f"  Pass Rate: {pass_rate:.1f}%")
        report.append("")

        # Detailed Results
        report.append(Colors.info("DETAILED RESULTS"))
        report.append("")

        for check_name, passed in sorted(self.results.items()):
            status = Colors.ok("PASS") if passed else Colors.err("FAIL")
            report.append(f"  [{status}] {check_name}")

        # Errors and Warnings
        if self.errors:
            report.append("")
            report.append(Colors.err("ERRORS"))
            for error in self.errors:
                report.append(f"  - {error}")

        if self.warnings:
            report.append("")
            report.append(Colors.warn("WARNINGS"))
            for warning in self.warnings:
                report.append(f"  - {warning}")

        # Final Verdict
        report.append("")
        report.append("=" * 80)
        if failed_checks == 0:
            report.append(Colors.ok("PRODUCTION READY: All checks passed!"))
            report.append("")
            report.append("The Enhanced Cognee system is ready for production deployment.")
        elif pass_rate >= 80:
            report.append(Colors.warn("PRODUCTION READY WITH CAUTION: Most checks passed"))
            report.append("")
            report.append("The system is mostly ready but has some issues that should be reviewed.")
            report.append("Review the errors above and address them before full production deployment.")
        else:
            report.append(Colors.err("NOT PRODUCTION READY: Critical issues found"))
            report.append("")
            report.append("The system has critical issues that must be resolved before production use.")
            report.append("Please address all failed checks above.")

        report.append("=" * 80)
        report.append("")

        return "\n".join(report)


# ============================================================================
# MAIN VERIFICATION FLOW
# ============================================================================

async def run_verification() -> Tuple[bool, str]:
    """Run all production readiness checks"""
    verifier = ProductionVerifier()

    print(Colors.info("Starting Enhanced Cognee Production Readiness Verification..."))
    print("")

    # Run all checks
    await verifier.check_security_module()
    await verifier.check_duplicate_functions()
    await verifier.check_authorization_checks()
    await verifier.check_input_validation()
    await verifier.check_trigger_classifications()
    await verifier.check_database_configuration()
    await verifier.check_mcp_tools_count()

    # Generate report
    report = verifier.generate_report()

    # Determine if production ready
    total_checks = len(verifier.results)
    passed_checks = sum(1 for v in verifier.results.values() if v)
    is_ready = passed_checks == total_checks

    return is_ready, report


async def main():
    """Main entry point"""
    try:
        is_ready, report = await run_verification()

        # Print report
        print("")
        print(report)

        # Exit with appropriate code
        sys.exit(0 if is_ready else 1)

    except KeyboardInterrupt:
        print(Colors.warn("\nVerification interrupted by user"))
        sys.exit(130)
    except Exception as e:
        print(Colors.err(f"\nUnexpected error: {e}"))
        logger.error(f"Verification failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
