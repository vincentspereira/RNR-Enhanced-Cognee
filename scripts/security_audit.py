#!/usr/bin/env python3
"""
Comprehensive Security Audit Script for Enhanced Cognee
Performs security checks, vulnerability scanning, and best practices validation
"""

import os
import re
import sys
import json
import subprocess
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass, field


@dataclass
class SecurityFinding:
    """Security finding result"""
    severity: str  # "critical", "high", "medium", "low", "info"
    category: str  # "secrets", "injection", "config", "dependencies"
    file_path: str
    line_number: Optional[int]
    description: str
    recommendation: str
    found_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat)


class SecurityAuditor:
    """
    Comprehensive Security Auditor for Enhanced Cognee

    Checks:
    - Hardcoded secrets (API keys, passwords, tokens)
    - SQL injection vulnerabilities
    - Command injection vulnerabilities
    - Insecure dependencies
    - Configuration issues
    - File permission problems
    - API security issues
    """

    def __init__(self, project_root: str):
        """
        Initialize security auditor

        Args:
            project_root: Root directory of project
        """
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []

        # Security patterns
        self.secret_patterns = {
            r'API[_-]?KEY\s*=\s*["\'][\w-]+["\']': "API Key",
            r'SECRET[_-]?KEY\s*=\s*["\'][\w-]+["\']': "Secret Key",
            r'PASSWORD\s*=\s*["\'][\w-]+["\']': "Hardcoded Password",
            r'TOKEN\s*=\s*["\'][\w-]+["\']': "Hardcoded Token",
            r'aws[_-]?(access[_-]?key[_-]?id|secret[_-]?access[_-]?key)\s*=\s*["\'][\w-]+["\']': "AWS Credentials",
            r'mongo[_-]?db[_-]?uri\s*=\s*["\'][^"\']+["\']': "MongoDB URI",
            r'redis[_-]?url\s*=\s*["\'][^"\']+["\']': "Redis URL",
            r'postgresql?[_-]?url\s*=\s*["\'][^"\']+["\']': "PostgreSQL URL",
            r'connection[_-]?string\s*=\s*["\'][^"\']+["\']': "Connection String",
            r'bearer\s+["\']?[a-zA-Z0-9._-]+["\']?': "Bearer Token",
        }

        # SQL injection patterns
        self.sql_injection_patterns = [
            r'execute\(["\'].*?\+.*?["\']',  # String concatenation in SQL
            r'format\s*\(["\'].*?%s.*?["\']',  # Format strings with user input
            r'%\s*\+.*?execute',  # String formatting with execute
            r'f["\'].*?SELECT.*?\{.*?\}.*?["\']',  # f-strings with SQL
        ]

        # Command injection patterns
        self.command_injection_patterns = [
            r'subprocess\.(call|run|Popen)\(["\'].*?\+.*?["\']',  # String concatenation
            r'os\.system\(["\'].*?\+.*?["\']',  # os.system with concatenation
            r'os\.popen\(["\'].*?\+.*?["\']',  # popen with concatenation
        ]

        # Insecure functions
        self.insecure_functions = {
            'eval': "Code execution vulnerability",
            'exec': "Code execution vulnerability",
            'os.system': "Command injection risk",
            'subprocess.call': "Command injection risk if input not sanitized",
            'pickle.loads': "Deserialization vulnerability",
            'yaml.load': "YAML deserialization vulnerability",
        }

    async def run_full_audit(self) -> Dict[str, Any]:
        """
        Run complete security audit

        Returns:
            Audit summary with findings
        """
        print("[SECURITY] Starting comprehensive security audit...")

        # 1. Check for hardcoded secrets
        print("[1/8] Scanning for hardcoded secrets...")
        await self._scan_secrets()

        # 2. Check SQL injection vulnerabilities
        print("[2/8] Checking for SQL injection vulnerabilities...")
        await self._check_sql_injection()

        # 3. Check command injection vulnerabilities
        print("[3/8] Checking for command injection vulnerabilities...")
        await self._check_command_injection()

        # 4. Check insecure dependencies
        print("[4/8] Checking for vulnerable dependencies...")
        await self._check_dependencies()

        # 5. Check file permissions
        print("[5/8] Checking file permissions...")
        await self._check_file_permissions()

        # 6. Check API security
        print("[6/8] Checking API security...")
        await self._check_api_security()

        # 7. Check configuration security
        print("[7/8] Checking configuration security...")
        await self._check_configuration()

        # 8. Check authentication & authorization
        print("[8/8] Checking authentication & authorization...")
        await self._check_auth_security()

        # Generate report
        return self._generate_report()

    async def _scan_secrets(self):
        """Scan for hardcoded secrets in code"""
        secret_files = [
            '.env',
            '.env.local',
            '.env.production',
            'secrets.yaml',
            'secrets.json',
            'credentials.json',
            'config.py',
            'settings.py'
        ]

        # Scan Python files
        python_files = list(self.project_root.rglob("*.py"))
        for file_path in python_files:
            # Skip test files
            if 'test' in str(file_path):
                continue

            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    # Check each secret pattern
                    for pattern, secret_type in self.secret_patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            # Skip if it's a default/example value
                            if any(keyword in line.lower() for keyword in ['change', 'example', 'test', 'dummy', 'xxx']):
                                continue

                            self.findings.append(SecurityFinding(
                                severity="critical",
                                category="secrets",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                description=f"Hardcoded {secret_type} detected",
                                recommendation="Use environment variables or secret management system"
                            ))
            except Exception as e:
                print(f"  Error scanning {file_path}: {e}")

        # Check if .env is in .gitignore
        gitignore = self.project_root / '.gitignore'
        if gitignore.exists():
            gitignore_content = gitignore.read_text()
            if '.env' not in gitignore_content:
                self.findings.append(SecurityFinding(
                    severity="high",
                    category="configuration",
                    file_path=".gitignore",
                    description=".env file not in .gitignore",
                    recommendation="Add .env to .gitignore to prevent committing secrets"
                ))

    async def _check_sql_injection(self):
        """Check for SQL injection vulnerabilities"""
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    for pattern in self.sql_injection_patterns:
                        if re.search(pattern, line):
                            self.findings.append(SecurityFinding(
                                severity="critical",
                                category="injection",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                description="Potential SQL injection vulnerability",
                                recommendation="Use parameterized queries or prepared statements"
                            ))
            except Exception as e:
                print(f"  Error checking {file_path}: {e}")

    async def _check_command_injection(self):
        """Check for command injection vulnerabilities"""
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    # Check for insecure functions with user input
                    for func, risk in self.insecure_functions.items():
                        if func in line:
                            if '+' in line or '%' in line or 'format' in line:
                                self.findings.append(SecurityFinding(
                                    severity="high",
                                    category="injection",
                                    file_path=str(file_path.relative_to(self.project_root)),
                                    line_number=line_num,
                                    description=f"Potential {risk}",
                                    recommendation="Avoid using user input in system commands"
                                ))

                    # Check command injection patterns
                    for pattern in self.command_injection_patterns:
                        if re.search(pattern, line):
                            self.findings.append(SecurityFinding(
                                severity="critical",
                                category="injection",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                description="Potential command injection vulnerability",
                                recommendation="Use subprocess.run with list arguments and sanitize input"
                            ))
            except Exception as e:
                print(f"  Error checking {file_path}: {e}")

    async def _check_dependencies(self):
        """Check for vulnerable dependencies"""
        requirements_files = [
            'requirements.txt',
            'requirements-dev.txt',
            'pyproject.toml',
            'setup.py'
        ]

        for req_file in requirements_files:
            file_path = self.project_root / req_file
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text()
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Check for pinned versions
                    if '==' in line:
                        # Good - version is pinned
                        continue
                    elif '>=' in line or '~=' in line:
                        # Minimum version specified - acceptable
                        continue
                    elif line.startswith('-e') or line.startswith('--'):
                        # Install options - skip
                        continue
                    else:
                        # Unpinned dependency
                        package = line.split('>=')[0].split('==')[0].split('[')[0].strip()

                        self.findings.append(SecurityFinding(
                            severity="medium",
                            category="dependencies",
                            file_path=req_file,
                            line_number=line_num,
                            description=f"Unpinned dependency: {package}",
                            recommendation="Pin dependency versions for reproducible builds"
                        ))
            except Exception as e:
                print(f"  Error checking {req_file}: {e}")

        # Try to run safety check
        try:
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # No vulnerabilities
                print("  OK No known vulnerabilities found")
            else:
                # Parse safety output
                try:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns:
                        self.findings.append(SecurityFinding(
                            severity="high",
                            category="dependencies",
                            file_path="requirements.txt",
                            description=f"Vulnerable dependency: {vuln.get('package', 'unknown')}",
                            recommendation=f"Upgrade to safe version: {vuln.get('affected_versions', [])}"
                        ))
                except json.JSONDecodeError:
                    pass
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("  INFO Safety check not available (pip install safety)")

    async def _check_file_permissions(self):
        """Check file permissions"""
        # Check for overly permissive files
        sensitive_files = [
            '.env',
            '*.pem',
            '*.key',
            'id_rsa',
            'credentials.json',
            'secrets/'
        ]

        try:
            result = subprocess.run(
                ['find', '.', '-type', 'f', '-perm', '-o+rwx', '-ls'],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10
            )

            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if not line:
                        continue

                    parts = line.split()
                    if len(parts) >= 9:
                        permissions = parts[0]
                        file_path = parts[8]

                        # Check if world-writable
                        if 'o+w' in permissions or permissions.endswith('w'):
                            self.findings.append(SecurityFinding(
                                severity="medium",
                                category="permissions",
                                file_path=file_path,
                                description=f"Overly permissive file: {permissions}",
                                recommendation="Remove write permissions for others/group"
                            ))
        except (subprocess.TimeoutExpired, Exception):
            print("  INFO File permission check skipped")

    async def _check_api_security(self):
        """Check API security issues"""
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Check for CORS misconfigurations
                if re.search(r'Access-Control-Allow-Origin:\s*\*\s*["\']', content):
                    self.findings.append(SecurityFinding(
                        severity="medium",
                        category="api",
                        file_path=str(file_path.relative_to(self.project_root)),
                        description="CORS wildcard origin detected",
                        recommendation="Specify exact allowed origins instead of wildcard"
                    ))

                # Check for missing authentication
                if '@app.route' in content:
                    # Look for routes without auth decorators
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if '@app.route' in line:
                            # Check next few lines for auth decorator
                            has_auth = False
                            for j in range(i+1, min(i+5, len(lines))):
                                if any(auth in lines[j] for auth in ['@login_required', '@require_auth', 'auth']):
                                    has_auth = True
                                    break

                            if not has_auth:
                                # Extract route
                                route_match = re.search(r'route\(["\']([^"\']+)["\']', line)
                                if route_match:
                                    self.findings.append(SecurityFinding(
                                        severity="high",
                                        category="api",
                                        file_path=str(file_path.relative_to(self.project_root)),
                                        line_number=i+1,
                                        description=f"Unauthenticated route: {route_match.group(1)}",
                                        recommendation="Add authentication decorator to protected routes"
                                    ))

            except Exception as e:
                print(f"  Error checking API security in {file_path}: {e}")

    async def _check_configuration(self):
        """Check configuration security"""
        config_files = [
            '.env',
            '.env.example',
            'config.py',
            'settings.py',
            'docker-compose.yml'
        ]

        for config_file in config_files:
            file_path = self.project_root / config_file
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Check for default passwords
                if any(keyword in content.lower() for keyword in ['password', 'secret', 'key']):
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if 'password' in line.lower() and any(default in line for default in ['change', 'xxx', 'test', 'demo', 'example']):
                            self.findings.append(SecurityFinding(
                                severity="high",
                                category="configuration",
                                file_path=config_file,
                                line_number=line_num,
                                description="Default password detected",
                                recommendation="Change default passwords before deployment"
                            ))

                # Check for debug mode
                if 'DEBUG=True' in content or 'debug=True' in content:
                    self.findings.append(SecurityFinding(
                        severity="medium",
                        category="configuration",
                        file_path=config_file,
                        description="Debug mode enabled",
                        recommendation="Disable debug mode in production"
                    ))

            except Exception as e:
                print(f"  Error checking {config_file}: {e}")

    async def _check_auth_security(self):
        """Check authentication and authorization security"""
        python_files = list(self.project_root.rglob("*.py"))

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Check for hardcoded credentials in auth
                if re.search(r'(auth|login|password).*=\s*["\'][\w-]+["\']', content, re.IGNORECASE):
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if re.search(r'(auth|login|password).*=\s*["\'][\w-]+["\']', line, re.IGNORECASE):
                            if 'admin' in line.lower() or 'root' in line.lower() or 'test' in line.lower():
                                if not any(skip in line for skip in ['os.getenv', 'environ', 'config']):
                                    self.findings.append(SecurityFinding(
                                        severity="high",
                                        category="secrets",
                                        file_path=str(file_path.relative_to(self.project_root)),
                                        line_number=line_num,
                                        description="Potential hardcoded credentials in auth logic",
                                        recommendation="Use environment variables for credentials"
                                    ))

                # Check for missing rate limiting
                if 'api' in content.lower() or 'route' in content.lower():
                    # File has API/route definitions
                    if 'rate_limit' not in content and 'ratelimit' not in content:
                        self.findings.append(SecurityFinding(
                            severity="medium",
                            category="api",
                            file_path=str(file_path.relative_to(self.project_root)),
                            description="No rate limiting detected",
                            recommendation="Implement rate limiting on API endpoints"
                        ))

            except Exception as e:
                print(f"  Error checking auth security in {file_path}: {e}")

    def _generate_report(self) -> Dict[str, Any]:
        """Generate security audit report"""
        # Count findings by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }

        category_counts = {}

        for finding in self.findings:
            severity_counts[finding.severity] += 1
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1

        return {
            "scan_date": datetime.now(UTC).isoformat(),
            "total_findings": len(self.findings),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "file": f.file_path,
                    "line": f.line_number,
                    "description": f.description,
                    "recommendation": f.recommendation
                }
                for f in self.findings
            ]
        }

    def save_report(self, output_file: str = "security_audit_report.json"):
        """Save audit report to file"""
        report = self._generate_report()

        output_path = self.project_root / output_file
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n[SECURITY] Report saved to: {output_path}")
        print(f"[SECURITY] Total Findings: {report['total_findings']}")
        print(f"[SECURITY] Critical: {report['severity_breakdown']['critical']}")
        print(f"[SECURITY] High: {report['severity_breakdown']['high']}")
        print(f"[SECURITY] Medium: {report['severity_breakdown']['medium']}")

        return report


# CLI interface
async def main():
    """Main entry point for security audit"""
    import sys

    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()

    print(f"[SECURITY] Enhanced Cognee Security Audit")
    print(f"[SECURITY] Project root: {project_root}\n")

    auditor = SecurityAuditor(project_root)

    try:
        # Run full audit
        report = await auditor.run_full_audit()

        # Save report
        auditor.save_report()

        # Exit with error code if critical/high findings
        critical_count = report['severity_breakdown']['critical']
        high_count = report['severity_breakdown']['high']

        if critical_count > 0 or high_count > 0:
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Security audit failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
