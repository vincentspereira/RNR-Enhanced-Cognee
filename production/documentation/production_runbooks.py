"""
RNR Enhanced Cognee Production Documentation and Runbooks

This module provides comprehensive production documentation and runbooks for the RNR Enhanced Cognee
Multi-Agent System, including operational procedures, troubleshooting guides, and emergency
response procedures.

Phase 4: Production Readiness and Optimization (Weeks 11-12)
Category: Production Documentation and Runbooks
"""

import pytest
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import yaml
import asyncio

logger = logging.getLogger(__name__)

# Documentation Markers
pytest.mark.production = pytest.mark.production
pytest.mark.documentation = pytest.mark.documentation
pytest.mark.runbooks = pytest.mark.runbooks
pytest.mark.procedures = pytest.mark.procedures


class IncidentSeverity(Enum):
    """Incident severity levels"""
    CRITICAL = "critical"  # System down, major business impact
    HIGH = "high"        # Significant degradation, partial business impact
    MEDIUM = "medium"      # Minor issues, limited business impact
    LOW = "low"          # Cosmetic issues, no business impact
    INFO = "info"        # Informational, no impact


class IncidentStatus(Enum):
    """Incident status values"""
    NEW = "new"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class RunbookCategory(Enum):
    """Runbook categories"""
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    TROUBLESHOOTING = "troubleshooting"
    BACKUP_RECOVERY = "backup_recovery"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"


@dataclass
class Runbook:
    """Production operations runbook"""
    runbook_id: str
    title: str
    description: str
    category: RunbookCategory
    severity: IncidentSeverity
    estimated_duration_minutes: int
    prerequisites: List[str]
    steps: List[Dict[str, Any]]
    verification_steps: List[Dict[str, Any]]
    rollback_steps: List[Dict[str, Any]]
    escalation_contacts: List[Dict[str, str]]
    related_runbooks: List[str]
    tags: List[str]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"


@dataclass
class IncidentProcedure:
    """Standard incident response procedure"""
    procedure_id: str
    name: str
    description: str
    trigger_conditions: List[str]
    immediate_actions: List[str]
    investigation_steps: List[str]
    resolution_steps: List[str]
    communication_plan: Dict[str, Any]
    escalation_criteria: List[str]
    documentation_requirements: List[str]


@dataclass
class MonitoringGuide:
    """System monitoring guide"""
    guide_id: str
    title: str
    system: str
    metrics: List[Dict[str, Any]]
    dashboards: List[Dict[str, Any]]
    alert_thresholds: Dict[str, Any]
    normal_ranges: Dict[str, Any]
    troubleshooting_links: List[str]
    escalation_contacts: List[Dict[str, str]]


class ProductionDocumentationFramework:
    """Production documentation and runbooks framework"""

    def __init__(self):
        self.runbooks = {}
        self.incident_procedures = {}
        self.monitoring_guides = {}
        self.documentation_index = {}
        self.runbook_history = []
        self.documentation_validated = {}

    def create_runbook(self, runbook: Runbook) -> str:
        """Create a new runbook"""
        self.runbooks[runbook.runbook_id] = runbook
        self._update_documentation_index(runbook)

        logger.info(f"Created runbook: {runbook.title} ({runbook.runbook_id})")
        return runbook.runbook_id

    def create_incident_procedure(self, procedure: IncidentProcedure) -> str:
        """Create a new incident procedure"""
        self.incident_procedures[procedure.procedure_id] = procedure
        logger.info(f"Created incident procedure: {procedure.name} ({procedure.procedure_id})")
        return procedure.procedure_id

    def create_monitoring_guide(self, guide: MonitoringGuide) -> str:
        """Create a new monitoring guide"""
        self.monitoring_guides[guide.guide_id] = guide
        logger.info(f"Created monitoring guide: {guide.title} ({guide.guide_id})")
        return guide.guide_id

    def _update_documentation_index(self, runbook: Runbook):
        """Update documentation index"""
        category = runbook.category.value
        if category not in self.documentation_index:
            self.documentation_index[category] = []

        index_entry = {
            "runbook_id": runbook.runbook_id,
            "title": runbook.title,
            "severity": runbook.severity.value,
            "description": runbook.description,
            "tags": runbook.tags,
            "last_updated": runbook.last_updated.isoformat(),
            "version": runbook.version
        }

        # Remove existing entry if present
        self.documentation_index[category] = [
            entry for entry in self.documentation_index[category]
            if entry["runbook_id"] != runbook.runbook_id
        ]

        # Add new entry
        self.documentation_index[category].append(index_entry)

    def get_runbook(self, runbook_id: str) -> Optional[Runbook]:
        """Get runbook by ID"""
        return self.runbooks.get(runbook_id)

    def search_runbooks(self, query: str, category: RunbookCategory = None,
                      severity: IncidentSeverity = None,
                      tags: List[str] = None) -> List[Runbook]:
        """Search runbooks by various criteria"""
        matching_runbooks = []

        for runbook in self.runbooks.values():
            # Category filter
            if category and runbook.category != category:
                continue

            # Severity filter
            if severity and runbook.severity != severity:
                continue

            # Tags filter
            if tags and not all(tag in runbook.tags for tag in tags):
                continue

            # Text search
            if query:
                search_text = f"{runbook.title} {runbook.description} {' '.join(runbook.tags)}".lower()
                if query.lower() not in search_text:
                    continue

            matching_runbooks.append(runbook)

        return matching_runbooks

    def get_runbooks_by_category(self, category: RunbookCategory) -> List[Runbook]:
        """Get all runbooks in a category"""
        return [rb for rb in self.runbooks.values() if rb.category == category]

    def get_runbooks_by_severity(self, severity: IncidentSeverity) -> List[Runbook]:
        """Get all runbooks by severity"""
        return [rb for rb in self.runbooks.values() if rb.severity == severity]

    def execute_runbook(self, runbook_id: str, dry_run: bool = True) -> Dict[str, Any]:
        """Execute a runbook (or simulate execution)"""
        runbook = self.get_runbook(runbook_id)
        if not runbook:
            raise ValueError(f"Runbook not found: {runbook_id}")

        execution_result = {
            "runbook_id": runbook_id,
            "title": runbook.title,
            "execution_id": f"exec_{int(time.time())}",
            "dry_run": dry_run,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "step_results": [],
            "verification_results": [],
            "issues": [],
            "success": False
        }

        try:
            # Check prerequisites
            for prerequisite in runbook.prerequisites:
                if not self._check_prerequisite(prerequisite, dry_run):
                    execution_result["issues"].append(f"Prerequisite not met: {prerequisite}")
                    execution_result["status"] = "failed"
                    execution_result["end_time"] = datetime.now(timezone.utc).isoformat()
                    return execution_result

            # Execute steps
            for i, step in enumerate(runbook.steps, 1):
                step_start = time.time()
                step_result = await self._execute_step(step, i, dry_run)
                step_duration = time.time() - step_start

                execution_result["step_results"].append({
                    "step_number": i,
                    "step_name": step.get("name", f"Step {i}"),
                    "description": step.get("description", ""),
                    "command": step.get("command", ""),
                    "duration_seconds": step_duration,
                    "success": step_result["success"],
                    "output": step_result.get("output", ""),
                    "issues": step_result.get("issues", [])
                })

                if not step_result["success"]:
                    execution_result["issues"].append(f"Step {i} failed: {step_result.get('issues', [])}")
                    execution_result["status"] = "failed"

                    # Stop execution on failure
                    break

            # If all steps succeeded, run verification steps
            if execution_result["status"] != "failed":
                for i, verification in enumerate(runbook.verification_steps, 1):
                    verification_result = await self._execute_verification_step(verification, i, dry_run)

                    execution_result["verification_results"].append({
                        "step_number": i,
                        "step_name": verification.get("name", f"Verification {i}"),
                        "description": verification.get("description", ""),
                        "success": verification_result["success"],
                        "output": verification_result.get("output", ""),
                        "issues": verification_result.get("issues", [])
                    })

                    if not verification_result["success"]:
                        execution_result["issues"].append(f"Verification {i} failed: {verification_result.get('issues', [])}")

            # Determine overall success
            execution_result["success"] = (
                execution_result["status"] != "failed" and
                all(vr["success"] for vr in execution_result["verification_results"])
                and all(sr["success"] for sr in execution_result["step_results"])
            )

            execution_result["status"] = "completed" if execution_result["success"] else "failed"

        except Exception as e:
            execution_result["issues"].append(f"Execution error: {str(e)}")
            execution_result["status"] = "error"

        finally:
            execution_result["end_time"] = datetime.now(timezone.utc).isoformat()
            execution_result["duration_seconds"] = (
                datetime.fromisoformat(execution_result["end_time"]) -
                datetime.fromisoformat(execution_result["start_time"])
            ).total_seconds()

        # Store execution history
        self.runbook_history.append(execution_result)

        return execution_result

    def _check_prerequisite(self, prerequisite: str, dry_run: bool) -> bool:
        """Check if prerequisite is met"""
        if dry_run:
            # In dry run, simulate prerequisite check
            return prerequisite not in ["root_access", "special_permissions", "physical_access"]
        else:
            # In real execution, check actual prerequisites
            # This would involve actual system checks
            return True

    async def _execute_step(self, step: Dict[str, Any], step_number: int, dry_run: bool) -> Dict[str, Any]:
        """Execute a single runbook step"""
        result = {"success": False, "output": "", "issues": []}

        if dry_run:
            # Simulate step execution
            await asyncio.sleep(0.1)  # Simulate execution time

            command = step.get("command", "")
            if command:
                result["output"] = f"[DRY RUN] Would execute: {command}"

            # Simulate potential failures
            if "fail" in step.get("name", "").lower():
                result["success"] = False
                result["issues"].append("Simulated step failure")
            else:
                result["success"] = True

        else:
            # Real execution would go here
            command = step.get("command", "")
            if command:
                try:
                    # Simulate command execution
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    result["output"] = stdout.decode() if stdout else stderr.decode()
                    result["success"] = process.returncode == 0

                    if not result["success"]:
                        result["issues"].append(f"Command failed with return code {process.returncode}")

                except Exception as e:
                    result["issues"].append(f"Command execution error: {str(e)}")
            else:
                result["success"] = True
                result["output"] = "Step completed (no command specified)"

        return result

    async def _execute_verification_step(self, verification: Dict[str, Any], step_number: int,
                                       dry_run: bool) -> Dict[str, Any]:
        """Execute a verification step"""
        result = {"success": False, "output": "", "issues": []}

        if dry_run:
            # Simulate verification
            await asyncio.sleep(0.1)

            check = verification.get("check", "")
            if check:
                result["output"] = f"[DRY RUN] Would verify: {check}"

            # Simulate verification success/failure
            if "fail" in verification.get("name", "").lower():
                result["success"] = False
                result["issues"].append("Simulated verification failure")
            else:
                result["success"] = True

        else:
            # Real verification would go here
            check = verification.get("check", "")
            if check:
                try:
                    process = await asyncio.create_subprocess_shell(
                        check,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    result["output"] = stdout.decode() if stdout else stderr.decode()
                    result["success"] = process.returncode == 0

                    if not result["success"]:
                        result["issues"].append(f"Verification check failed: {process.returncode}")

                except Exception as e:
                    result["issues"].append(f"Verification error: {str(e)}")
            else:
                result["success"] = True
                result["output"] = "Verification completed (no check specified)"

        return result

    def generate_runbook_documentation(self) -> Dict[str, Any]:
        """Generate comprehensive runbook documentation"""
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_runbooks": len(self.runbooks),
            "categories": {
                category.value: len(self.get_runbooks_by_category(RunbookCategory(category)))
                for category in RunbookCategory
            },
            "severities": {
                severity.value: len(self.get_runbooks_by_severity(IncidentSeverity(severity)))
                for severity in IncidentSeverity
            },
            "recent_executions": self.runbook_history[-10:] if self.runbook_history else [],
            "runbook_index": self.documentation_index,
            "incident_procedures": {
                proc_id: {
                    "name": proc.name,
                    "description": proc.description,
                    "trigger_conditions": proc.trigger_conditions
                }
                for proc_id, proc in self.incident_procedures.items()
            },
            "monitoring_guides": {
                guide_id: {
                    "title": guide.title,
                    "system": guide.system,
                    "metrics_count": len(guide.metrics)
                }
                for guide_id, guide in self.monitoring_guides.items()
            }
        }

    def create_standard_runbooks(self):
        """Create standard production runbooks"""
        standard_runbooks = [
            self._create_deployment_runbook(),
            self._create_service_restart_runbook(),
            self._create_backup_runbook(),
            self._create_database_maintenance_runbook(),
            self._create_performance_troubleshooting_runbook(),
            self._create_security_incident_runbook(),
            self._create_monitoring_alert_runbook(),
            self._create_disaster_recovery_runbook()
        ]

        for runbook in standard_runbooks:
            self.create_runbook(runbook)

        logger.info(f"Created {len(standard_runbooks)} standard runbooks")

    def _create_deployment_runbook(self) -> Runbook:
        """Create deployment runbook"""
        return Runbook(
            runbook_id="deployment_procedure",
            title="Application Deployment Procedure",
            description="Standard procedure for deploying RNR Enhanced Cognee to production",
            category=RunbookCategory.DEPLOYMENT,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=45,
            prerequisites=[
                "Valid deployment package",
                "Database access credentials",
                "Access to production cluster",
                "Backup of current version"
            ],
            steps=[
                {
                    "name": "Verify Prerequisites",
                    "description": "Check all prerequisites are met",
                    "command": "./scripts/check_prerequisites.sh",
                    "verification": "All checks pass"
                },
                {
                    "name": "Create Backup",
                    "description": "Create backup of current deployment",
                    "command": "./scripts/backup_current_deployment.sh",
                    "verification": "Backup completed successfully"
                },
                {
                    "name": "Deploy New Version",
                    "description": "Deploy new version to production",
                    "command": "kubectl apply -f deployment.yaml",
                    "verification": "Deployment created successfully"
                },
                {
                    "name": "Wait for Rollout",
                    "description": "Wait for deployment rollout to complete",
                    "command": "kubectl rollout status deployment/cognee",
                    "verification": "Rollout completed successfully"
                },
                {
                    "name": "Health Check",
                    "description": "Perform health check on deployed application",
                    "command": "./scripts/health_check.sh",
                    "verification": "Health check passed"
                },
                {
                    "name": "Smoke Test",
                    "description": "Run smoke tests on new deployment",
                    "command": "./scripts/smoke_tests.sh",
                    "verification": "All smoke tests passed"
                }
            ],
            verification_steps=[
                {
                    "name": "Verify Application Health",
                    "description": "Check application is healthy",
                    "check": "curl -f http://localhost:8000/health"
                },
                {
                    "name": "Verify Database Connectivity",
                    "description": "Check database connectivity",
                    "check": "./scripts/check_database.sh"
                },
                {
                    "name": "Verify Service Endpoints",
                    "description": "Check all service endpoints",
                    "check": "./scripts/check_endpoints.sh"
                }
            ],
            rollback_steps=[
                {
                    "name": "Rollback Deployment",
                    "description": "Rollback to previous version",
                    "command": "kubectl rollout undo deployment/cognee"
                },
                {
                    "name": "Restore from Backup",
                    "description": "Restore from pre-deployment backup if needed",
                    "command": "./scripts/restore_backup.sh"
                },
                {
                    "name": "Verify Rollback",
                    "description": "Verify rollback was successful",
                    "command": "./scripts/verify_rollback.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "DevOps Team",
                    "contact": "devops@cognee.com",
                    "priority": "high"
                },
                {
                    "role": "On-call Engineer",
                    "contact": "oncall@cognee.com",
                    "priority": "critical"
                }
            ],
            related_runbooks=["service_restart", "backup_recovery"],
            tags=["deployment", "production", "kubernetes", "rollout"]
        )

    def _create_service_restart_runbook(self) -> Runbook:
        """Create service restart runbook"""
        return Runbook(
            runbook_id="service_restart",
            title="Service Restart Procedure",
            description="Procedure for restarting RNR Enhanced Cognee services in production",
            category=RunbookCategory.MAINTENANCE,
            severity=IncidentSeverity.HIGH,
            estimated_duration_minutes=15,
            prerequisites=[
                "Access to production cluster",
                "Service identification information",
                "Current service status"
            ],
            steps=[
                {
                    "name": "Identify Affected Service",
                    "description": "Identify which service needs restarting",
                    "command": "kubectl get pods | grep cognee"
                },
                {
                    "name": "Check Service Dependencies",
                    "description": "Check service dependencies before restart",
                    "command": "./scripts/check_dependencies.sh"
                },
                {
                    "name": "Scale Down Service",
                    "description": "Scale down service gracefully",
                    "command": "kubectl scale deployment cognee-api --replicas=0"
                },
                {
                    "name": "Wait for Scale Down",
                    "description": "Wait for pods to terminate",
                    "command": "kubectl get pods -l app=cognee-api"
                },
                {
                    "name": "Scale Up Service",
                    "description": "Scale service back up",
                    "command": "kubectl scale deployment cognee-api --replicas=3"
                },
                {
                    "name": "Wait for Scale Up",
                    "description": "Wait for pods to become ready",
                    "command": "kubectl rollout status deployment/cognee-api"
                },
                {
                    "name": "Verify Service Health",
                    "description": "Verify service is healthy after restart",
                    "command": "./scripts/service_health_check.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Check Service Status",
                    "description": "Check service is running",
                    "check": "kubectl get deployment cognee-api"
                },
                {
                    "name": "Check Pod Health",
                    "description": "Check all pods are healthy",
                    "check": "kubectl get pods -l app=cognee-api --field-selector=status.phase=Running"
                },
                {
                    "name": "Check Service Endpoints",
                    "description": "Check service endpoints are responding",
                    "check": "curl -f http://cognee-api:8000/health"
                }
            ],
            rollback_steps=[
                {
                    "name": "Check Previous State",
                    "description": "Check service state before restart",
                    "command": "kubectl rollout history deployment/cognee-api"
                },
                {
                    "name": "Rollback if Needed",
                    "description": "Rollback to previous version if restart failed",
                    "command": "kubectl rollout undo deployment/cognee-api"
                }
            ],
            escalation_contacts=[
                {
                    "role": "On-call Engineer",
                    "contact": "oncall@cognee.com",
                    "priority": "critical"
                }
            ],
            related_runbooks=["monitoring", "troubleshooting"],
            tags=["restart", "service", "maintenance", "kubernetes"]
        )

    def _create_backup_runbook(self) -> Runbook:
        """Create backup runbook"""
        return Runbook(
            runbook_id="backup_procedure",
            title="System Backup Procedure",
            description="Comprehensive backup procedure for RNR Enhanced Cognee production system",
            category=RunbookCategory.BACKUP_RECOVERY,
            severity=IncidentSeverity.LOW,
            estimated_duration_minutes=30,
            prerequisites=[
                "Sufficient storage space",
                "Backup access credentials",
                "List of components to backup"
            ],
            steps=[
                {
                    "name": "Verify Storage Space",
                    "description": "Ensure sufficient storage for backup",
                    "command": "df -h /backup"
                },
                {
                    "name": "Create Application Backup",
                    "description": "Backup application configuration and data",
                    "command": "./scripts/backup_application.sh"
                },
                {
                    "name": "Create Database Backup",
                    "description": "Backup all databases",
                    "command": "./scripts/backup_databases.sh"
                },
                {
                    "name": "Create Configuration Backup",
                    "description": "Backup system configurations",
                    "command": "tar -czf /backup/configs.tar.gz /etc/cognee"
                },
                {
                    "name": "Verify Backup Integrity",
                    "description": "Verify backup files integrity",
                    "command": "./scripts/verify_backup.sh"
                },
                {
                    "name": "Cleanup Old Backups",
                    "description": "Clean up old backup files",
                    "command": "./scripts/cleanup_old_backups.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Check Backup Files",
                    "description": "Verify backup files were created",
                    "check": "ls -la /backup/"
                },
                {
                    "name": "Verify Backup Integrity",
                    "description": "Verify backup file integrity",
                    "check": "./scripts/backup_integrity_check.sh"
                },
                {
                    "name": "Check Backup Size",
                    "description": "Verify backup size is reasonable",
                    "check": "du -sh /backup/"
                }
            ],
            rollback_steps=[
                {
                    "name": "Restore from Previous Backup",
                    "description": "Restore from previous backup if needed",
                    "command": "./scripts/restore_backup.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "Backup Administrator",
                    "contact": "backup@cognee.com",
                    "priority": "medium"
                }
            ],
            related_runbooks=["disaster_recovery", "database_maintenance"],
            tags=["backup", "storage", "data_protection"]
        )

    def _create_database_maintenance_runbook(self) -> Runbook:
        """Create database maintenance runbook"""
        return Runbook(
            runbook_id="database_maintenance",
            title="Database Maintenance Procedure",
            description="Database maintenance procedures for RNR Enhanced Cognee",
            category=RunbookCategory.MAINTENANCE,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=60,
            prerequisites=[
                "Database access credentials",
                "Maintenance window approval",
                "Backup completion verification"
            ],
            steps=[
                {
                    "name": "Schedule Maintenance Window",
                    "description": "Schedule maintenance window",
                    "command": "./scripts/schedule_maintenance.sh"
                },
                {
                    "name": "Create Pre-Maintenance Backup",
                    "description": "Create backup before maintenance",
                    "command": "./scripts/pre_maintenance_backup.sh"
                },
                {
                    "name": "Stop Application Services",
                    "description": "Stop application services",
                    "command": "kubectl scale deployment cognee-api --replicas=0"
                },
                {
                    "name": "Run Database Maintenance",
                    "description": "Execute database maintenance tasks",
                    "command": "./scripts/database_maintenance.sh"
                },
                {
                    "name": "Update Database Statistics",
                    "description": "Update database statistics",
                    "command": "./scripts/update_statistics.sh"
                },
                {
                    "name": "Optimize Database",
                    "description": "Optimize database performance",
                    "command": "./scripts/optimize_database.sh"
                },
                {
                    "name": "Start Application Services",
                    "description": "Start application services",
                    "command": "kubectl scale deployment cognee-api --replicas=3"
                },
                {
                    "name": "Verify Application Health",
                    "description": "Verify application health after maintenance",
                    "command": "./scripts/post_maintenance_health_check.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Check Database Health",
                    "description": "Check database is healthy",
                    "check": "pg_isready -h localhost -U cognee"
                },
                {
                    "name": "Check Application Connectivity",
                    "description": "Check application can connect to database",
                    "check": "./scripts/test_db_connectivity.sh"
                },
                {
                    "name": "Verify Performance",
                    "description": "Verify database performance is acceptable",
                    "check": "./scripts/check_db_performance.sh"
                }
            ],
            rollback_steps=[
                {
                    "name": "Rollback Database Changes",
                    "description": "Rollback database changes if needed",
                    "command": "./scripts/rollback_database.sh"
                },
                {
                    "name": "Restore Pre-Maintenance Backup",
                    "description": "Restore from pre-maintenance backup",
                    "command": "./scripts/restore_pre_maintenance_backup.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "DBA Team",
                    "contact": "dba@cognee.com",
                    "priority": "high"
                },
                {
                    "role": "DevOps Team",
                    "contact": "devops@cognee.com",
                    "priority": "medium"
                }
            ],
            related_runbooks=["backup", "troubleshooting"],
            tags=["database", "maintenance", "postgresql", "optimization"]
        )

    def _create_performance_troubleshooting_runbook(self) -> Runbook:
        """Create performance troubleshooting runbook"""
        return Runbook(
            runbook_id="performance_troubleshooting",
            title="Performance Troubleshooting Procedure",
            description="Procedures for diagnosing and resolving performance issues",
            category=RunbookCategory.TROUBLESHOOTING,
            severity=IncidentSeverity.HIGH,
            estimated_duration_minutes=45,
            prerequisites=[
                "Monitoring access",
                "Performance metrics access",
                "System logs access"
            ],
            steps=[
                {
                    "name": "Identify Performance Issue",
                    "description": "Identify the nature of performance issue",
                    "command": "./scripts/identify_performance_issue.sh"
                },
                {
                    "name": "Collect System Metrics",
                    "description": "Collect detailed system performance metrics",
                    "command": "./scripts/collect_performance_metrics.sh"
                },
                {
                    "name": "Analyze Resource Usage",
                    "description": "Analyze CPU, memory, disk, and network usage",
                    "command": "./scripts/analyze_resource_usage.sh"
                },
                {
                    "name": "Check Database Performance",
                    "description": "Check database query performance",
                    "command": "./scripts/check_database_performance.sh"
                },
                {
                    "name": "Check Application Metrics",
                    "description": "Check application-specific metrics",
                    "command": "./scripts/check_application_metrics.sh"
                },
                {
                    "name": "Identify Bottlenecks",
                    "description": "Identify performance bottlenecks",
                    "command": "./scripts/identify_bottlenecks.sh"
                },
                {
                    "name": "Apply Performance Fixes",
                    "description": "Apply identified performance fixes",
                    "command": "./scripts/apply_performance_fixes.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Verify Performance Improvement",
                    "description": "Verify performance has improved",
                    "check": "./scripts/verify_performance_improvement.sh"
                },
                {
                    "name": "Monitor System Stability",
                    "description": "Monitor system stability after fixes",
                    "check": "./scripts/monitor_stability.sh"
                }
            ],
            rollback_steps=[
                {
                    "name": "Revert Changes",
                    "description": "Revert performance changes if needed",
                    "command": "./scripts/revert_performance_changes.sh"
                },
                {
                    "name": "Restart Services",
                    "description": "Restart affected services",
                    "command": "./scripts/restart_affected_services.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "Performance Team",
                    "contact": "performance@cognee.com",
                    "priority": "high"
                }
            ],
            related_runbooks=["monitoring", "service_restart"],
            tags=["performance", "troubleshooting", "optimization", "metrics"]
        )

    def _create_security_incident_runbook(self) -> Runbook:
        """Create security incident runbook"""
        return Runbook(
            runbook_id="security_incident_response",
            title="Security Incident Response Procedure",
            description="Procedure for responding to security incidents",
            category=RunbookCategory.SECURITY,
            severity=IncidentSeverity.CRITICAL,
            estimated_duration_minutes=90,
            prerequisites=[
                "Security team access",
                "Incident response plan",
                "Forensic tools access",
                "Communication channels"
            ],
            steps=[
                {
                    "name": "Assess Incident Severity",
                    "description": "Assess and classify security incident",
                    "command": "./scripts/assess_security_incident.sh"
                },
                {
                    "name": "Activate Incident Response Team",
                    "description": "Activate security incident response team",
                    "command": "./scripts/activate_security_team.sh"
                },
                {
                    "name": "Isolate Affected Systems",
                    "description": "Isolate affected systems to prevent further damage",
                    "command": "./scripts/isolate_affected_systems.sh"
                },
                {
                    "name": "Preserve Evidence",
                    "description": "Preserve forensic evidence",
                    "command": "./scripts/preserve_evidence.sh"
                },
                {
                    "name": "Investigate Incident",
                    "description": "Investigate security incident",
                    "command": "./scripts/investigate_security_incident.sh"
                },
                {
                    "name": "Contain Threat",
                    "description": "Contain and neutralize threat",
                    "command": "./scripts/contain_threat.sh"
                },
                {
                    "name": "Remediate Vulnerability",
                    "description": "Remediate security vulnerability",
                    "command": "./scripts/remediate_vulnerability.sh"
                },
                {
                    "name": "Restore Services",
                    "description": "Restore normal service operations",
                    "command": "./scripts/restore_services.sh"
                },
                {
                    "name": "Post-Incident Review",
                    "description": "Conduct post-incident review",
                    "command": "./scripts/post_incident_review.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Verify Security",
                    "description": "Verify system is secure",
                    "check": "./scripts/verify_system_security.sh"
                },
                {
                    "name": "Verify Services",
                    "description": "Verify all services are operational",
                    "check": "./scripts/verify_services.sh"
                }
            ],
            rollback_steps=[
                {
                    "name": "Rollback Changes",
                    "description": "Rollback security changes if needed",
                    "command": "./scripts/rollback_security_changes.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "Security Team",
                    "contact": "security@cognee.com",
                    "priority": "critical"
                },
                {
                    "role": "Management",
                    "contact": "management@cognee.com",
                    "priority": "high"
                }
            ],
            related_runbooks=["disaster_recovery", "monitoring"],
            tags=["security", "incident", "forensic", "compliance"]
        )

    def _create_monitoring_alert_runbook(self) -> Runbook:
        """Create monitoring alert runbook"""
        return Runbook(
            runbook_id="monitoring_alert_response",
            title="Monitoring Alert Response Procedure",
            description="Procedure for responding to monitoring alerts",
            category=RunbookCategory.MONITORING,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=20,
            prerequisites=[
                "Monitoring dashboard access",
                "Alert notification access",
                "System access credentials"
            ],
            steps=[
                {
                    "name": "Acknowledge Alert",
                    "description": "Acknowledge the monitoring alert",
                    "command": "./scripts/acknowledge_alert.sh"
                },
                {
                    "name": "Assess Alert Severity",
                    "description": "Assess alert severity and impact",
                    "command": "./scripts/assess_alert_severity.sh"
                },
                {
                    "name": "Investigate Root Cause",
                    "description": "Investigate alert root cause",
                    "command": "./scripts/investigate_root_cause.sh"
                },
                {
                    "name": "Gather System Metrics",
                    "description": "Collect relevant system metrics",
                    "command": "./scripts/collect_system_metrics.sh"
                },
                {
                    "name": "Review Logs",
                    "description": "Review system logs for related issues",
                    "command": "./scripts/review_logs.sh"
                },
                {
                    "name": "Implement Fix",
                    "description": "Implement fix for alert condition",
                    "command": "./scripts/implement_fix.sh"
                },
                {
                    "name": "Verify Resolution",
                    "description": "Verify alert condition is resolved",
                    "command": "./scripts/verify_resolution.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Check Alert Status",
                    "description": "Check if alert is resolved",
                    "check": "./scripts/check_alert_status.sh"
                },
                {
                    "name": "Monitor Stability",
                    "description": "Monitor system stability after fix",
                    "check": "./scripts/monitor_stability.sh"
                }
            ],
            rollback_steps=[
                {
                    "name": "Rollback Changes",
                    "description": "Rollback changes if fix failed",
                    "command": "./scripts/rollback_changes.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "On-Call Engineer",
                    "contact": "oncall@cognee.com",
                    "priority": "high"
                }
            ],
            related_runbooks=["troubleshooting", "performance"],
            tags=["monitoring", "alerts", "metrics", "operations"]
        )

    def _create_disaster_recovery_runbook(self) -> Runbook:
        """Create disaster recovery runbook"""
        return Runbook(
            runbook_id="disaster_recovery",
            title="Disaster Recovery Procedure",
            description="Comprehensive disaster recovery and business continuity procedure",
            category=RunbookCategory.EMERGENCY,
            severity=IncidentSeverity.CRITICAL,
            estimated_duration_minutes=180,
            prerequisites=[
                "Disaster recovery plan",
                "Backup access",
                "Alternate site access",
                "Communication channels"
            ],
            steps=[
                {
                    "name": "Declare Disaster",
                    "description": "Declare disaster and activate response team",
                    "command": "./scripts/declare_disaster.sh"
                },
                {
                    "name": "Activate DRP",
                    "description": "Activate disaster recovery plan",
                    "command": "./scripts/activate_drp.sh"
                },
                {
                    "name": "Communicate Stakeholders",
                    "description": "Communicate with all stakeholders",
                    "command": "./scripts/communicate_stakeholders.sh"
                },
                {
                    "name": "Failover to Alternate Site",
                    "description": "Failover to alternate site if needed",
                    "command": "./scripts/failover_to_alternate.sh"
                },
                {
                    "name": "Restore from Backups",
                    "description": "Restore systems from backups",
                    "command": "./scripts/restore_from_backups.sh"
                },
                {
                    "name": "Validate System Functionality",
                    "description": "Validate system functionality",
                    "command": "./scripts/validate_functionality.sh"
                },
                {
                    "name": "Monitor Stability",
                    "description": "Monitor system stability",
                    "command": "./scripts/monitor_stability.sh"
                },
                {
                    "name": "Document Lessons Learned",
                    "description": "Document lessons learned",
                    "command": "./scripts/document_lessons.sh"
                }
            ],
            verification_steps=[
                {
                    "name": "Verify Critical Services",
                    "description": "Verify critical services are operational",
                    "check": "./scripts/verify_critical_services.sh"
                },
                {
                    "name": "Verify Data Integrity",
                    "description": "Verify data integrity",
                    "check": "./scripts/verify_data_integrity.sh"
                }
            ],
            rollback_steps=[
                {
                    "name": "Rollback to Primary Site",
                    "description": "Rollback to primary site when ready",
                    "command": "./scripts/rollback_to_primary.sh"
                }
            ],
            escalation_contacts=[
                {
                    "role": "Crisis Management Team",
                    "contact": "crisis@cognee.com",
                    "priority": "critical"
                }
            ],
            related_runbooks=["backup_recovery", "security_incident", "communication"],
            tags=["disaster_recovery", "business_continuity", "emergency", "drp"]
        )


@pytest.fixture
def documentation_framework():
    """Fixture for documentation framework"""
    framework = ProductionDocumentationFramework()
    return framework


class TestProductionDocumentation:
    """Test production documentation and runbooks"""

    @pytest.mark.production
    @pytest.mark.documentation
    def test_runbook_creation(self, documentation_framework):
        """Test runbook creation"""
        runbook = Runbook(
            runbook_id="test_runbook",
            title="Test Runbook",
            description="Test runbook for validation",
            category=RunbookCategory.TROUBLESHOOTING,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=10,
            prerequisites=["Test prerequisite"],
            steps=[],
            verification_steps=[],
            rollback_steps=[],
            escalation_contacts=[],
            related_runbooks=[],
            tags=["test"]
        )

        runbook_id = documentation_framework.create_runbook(runbook)

        assert runbook_id == "test_runbook", "Runbook ID should match"
        assert runbook.runbook_id in documentation_framework.runbooks, "Runbook should be stored"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_runbook_search(self, documentation_framework):
        """Test runbook search functionality"""
        # Create test runbooks
        documentation_framework.create_standard_runbooks()

        # Search by category
        deployment_runbooks = documentation_framework.get_runbooks_by_category(RunbookCategory.DEPLOYMENT)
        assert len(deployment_runbooks) > 0, "Should find deployment runbooks"

        # Search by severity
        critical_runbooks = documentation_framework.get_runbooks_by_severity(IncidentSeverity.CRITICAL)
        assert len(critical_runbooks) > 0, "Should find critical severity runbooks"

        # Search by tags
        api_runbooks = documentation_framework.search_runbooks("api")
        assert len(api_runbooks) > 0, "Should find API-related runbooks"

    @pytest.mark.production
    @pytest.mark.runbooks
    async def test_runbook_execution_dry_run(self, documentation_framework):
        """Test runbook execution in dry run mode"""
        documentation_framework.create_standard_runbooks()

        # Execute deployment runbook in dry run mode
        result = documentation_framework.execute_runbook("deployment_procedure", dry_run=True)

        assert result["runbook_id"] == "deployment_procedure", "Runbook ID should match"
        assert result["dry_run"] is True, "Should be dry run mode"
        assert result["start_time"] is not None, "Should have start time"
        assert result["end_time"] is not None, "Should have end time"
        assert result["duration_seconds"] > 0, "Should have duration"

        # Should have step results
        assert len(result["step_results"]) > 0, "Should have step results"

        # All steps should succeed in dry run mode (unless explicitly marked to fail)
        assert result["status"] == "completed", "Should complete successfully"

    @pytest.mark.production
    @pytest.mark.procedures
    def test_incident_procedure_creation(self, documentation_framework):
        """Test incident procedure creation"""
        procedure = IncidentProcedure(
            procedure_id="test_procedure",
            name="Test Procedure",
            description="Test incident procedure",
            trigger_conditions=["test condition"],
            immediate_actions=["Test action"],
            investigation_steps=["Test investigation"],
            resolution_steps=["Test resolution"],
            communication_plan={},
            escalation_criteria=["test escalation"],
            documentation_requirements=["Test documentation"]
        )

        procedure_id = documentation_framework.create_incident_procedure(procedure)

        assert procedure_id == "test_procedure", "Procedure ID should match"
        assert procedure_id in documentation_framework.incident_procedures, "Procedure should be stored"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_monitoring_guide_creation(self, documentation_framework):
        """Test monitoring guide creation"""
        guide = MonitoringGuide(
            guide_id="test_guide",
            title="Test Monitoring Guide",
            system="Test System",
            metrics=[
                {"name": "test_metric", "type": "gauge", "description": "Test metric"}
            ],
            dashboards=[
                {"name": "test_dashboard", "url": "http://test.com"}
            ],
            alert_thresholds={"test_metric": 100},
            normal_ranges={"test_metric": {"min": 0, "max": 80}},
            troubleshooting_links=[],
            escalation_contacts=[]
        )

        guide_id = documentation_framework.create_monitoring_guide(guide)

        assert guide_id == "test_guide", "Guide ID should match"
        assert guide_id in documentation_framework.monitoring_guides, "Guide should be stored"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_documentation_generation(self, documentation_framework):
        """Test documentation report generation"""
        documentation_framework.create_standard_runbooks()

        report = documentation_framework.generate_runbook_documentation()

        assert "generated_at" in report, "Report should have generation timestamp"
        assert "total_runbooks" in report, "Report should have total runbooks count"
        assert "categories" in report, "Report should have categories section"
        assert "severities" in report, "Report should have severities section"

        assert report["total_runbooks"] > 0, "Should have runbooks documented"

    @pytest.mark.production
    @pytest.mark.runbooks
    def test_standard_runbooks_creation(self, documentation_framework):
        """Test standard runbooks creation"""
        initial_count = len(documentation_framework.runbooks)
        documentation_framework.create_standard_runbooks()

        final_count = len(documentation_framework.runbooks)
        assert final_count > initial_count, "Should create additional runbooks"

        # Verify specific standard runbooks
        standard_runbook_ids = [
            "deployment_procedure",
            "service_restart",
            "backup_procedure",
            "database_maintenance",
            "performance_troubleshooting",
            "security_incident_response",
            "monitoring_alert_response",
            "disaster_recovery"
        ]

        for runbook_id in standard_runbook_ids:
            assert runbook_id in documentation_framework.runbooks, \
                f"Standard runbook {runbook_id} should be created"

    @pytest.mark.production
    @pytest.mark.runbooks
    def test_runbook_structure_validation(self, documentation_framework):
        """Test runbook structure validation"""
        documentation_framework.create_standard_runbooks()

        for runbook in documentation_framework.runbooks.values():
            # Required fields
            assert runbook.runbook_id is not None, "Runbook ID is required"
            assert runbook.title is not None, "Title is required"
            assert runbook.description is not None, "Description is required"
            assert runbook.category in RunbookCategory, "Valid category is required"
            assert runbook.severity in IncidentSeverity, "Valid severity is required"
            assert runbook.estimated_duration_minutes > 0, "Duration must be positive"
            assert isinstance(runbook.prerequisites, list), "Prerequisites should be a list"
            assert isinstance(runbook.steps, list), "Steps should be a list"
            assert isinstance(runbook.verification_steps, list), "Verification steps should be a list"
            assert isinstance(runbook.rollback_steps, list), "Rollback steps should be a list"
            assert isinstance(runbook.escalation_contacts, list), "Escalation contacts should be a list"
            assert isinstance(runbook.related_runbooks, list), "Related runbooks should be a list"
            assert isinstance(runbook.tags, list), "Tags should be a list"

    @pytest.mark.production
    @pytest.mark.procedures
    def test_incident_procedure_structure(self, documentation_framework):
        """Test incident procedure structure validation"""
        # Create test procedure
        procedure = IncidentProcedure(
            procedure_id="test_procedure",
            name="Test Procedure",
            description="Test procedure",
            trigger_conditions=["test condition"],
            immediate_actions=["Test action"],
            investigation_steps=["Test investigation"],
            resolution_steps=["Test resolution"],
            communication_plan={"primary": "test@example.com"},
            escalation_criteria=["test escalation"],
            documentation_requirements=["Test documentation"]
        )

        procedure_id = documentation_framework.create_incident_procedure(procedure)

        # Validate structure
        assert procedure.procedure_id == "test_procedure", "Procedure ID should match"
        assert procedure.name is not None, "Name is required"
        assert procedure.description is not None, "Description is required"
        assert isinstance(procedure.trigger_conditions, list), "Trigger conditions should be a list"
        assert isinstance(procedure.immediate_actions, list), "Immediate actions should be a list"
        assert isinstance(procedure.investigation_steps, list), "Investigation steps should be a list"
        assert isinstance(procedure.resolution_steps, list), "Resolution steps should be a list"
        assert isinstance(procedure.communication_plan, dict), "Communication plan should be a dict"
        assert isinstance(procedure.escalation_criteria, list), "Escalation criteria should be a list"
        assert isinstance(procedure.documentation_requirements, list), "Documentation requirements should be a list"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_documentation_index_structure(self, documentation_framework):
        """Test documentation index structure"""
        documentation_framework.create_standard_runbooks()

        index = documentation_framework.documentation_index

        # Verify categories exist
        for category in RunbookCategory:
            category_key = category.value
            assert category_key in index, f"Category {category_key} should be in index"

        # Verify category structure
        for category_key, category_entries in index.items():
            assert isinstance(category_entries, list), f"Category {category_key} entries should be a list"
            for entry in category_entries:
                assert "runbook_id" in entry, "Entry should have runbook_id"
                assert "title" in entry, "Entry should have title"
                assert "severity" in entry, "Entry should have severity"
                assert "tags" in entry, "Entry should have tags"
                assert "last_updated" in entry, "Entry should have last_updated"

    @pytest.mark.production
    @pytest.mark.runbooks
    async def test_runbook_execution_rollback(self, documentation_framework):
        """Test runbook execution rollback functionality"""
        # Create runbook with failure step
        runbook = Runbook(
            runbook_id="test_rollback",
            title="Test Rollback Runbook",
            description="Test runbook with rollback",
            category=RunbookCategory.TROUBLESHOOTING,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=10,
            prerequisites=[],
            steps=[
                {
                    "name": "Success Step",
                    "description": "This step should succeed",
                    "command": "echo 'success'",
                    "verification": "Should pass"
                },
                {
                    "name": "Failure Step",
                    "description": "This step should fail",
                    "command": "false",
                    "verification": "Should fail"
                }
            ],
            verification_steps=[],
            rollback_steps=[
                {
                    "name": "Rollback Step",
                    "description": "Rollback step",
                    "command": "echo 'rollback'",
                    "verification": "Should pass"
                }
            ],
            escalation_contacts=[],
            related_runbooks=[],
            tags=["test"]
        )

        documentation_framework.create_runbook(runbook)

        # Execute runbook with failure
        result = documentation_framework.execute_runbook("test_rollback", dry_run=True)

        assert result["status"] == "failed", "Should fail due to failure step"
        assert len(result["step_results"]) == 2, "Should have step results for both steps"
        assert result["step_results"][0]["success"] is True, "First step should succeed"
        assert result["step_results"][1]["success"] is False, "Second step should fail"
        assert len(result["issues"]) > 0, "Should have issues recorded"

    @pytest.mark.production
    @pytest.mark.observability
    async def test_runbook_verification_steps(self, documentation_framework):
        """Test runbook verification steps execution"""
        # Create runbook with verification steps
        runbook = Runbook(
            runbook_id="test_verification",
            title="Test Verification Runbook",
            description="Test runbook with verification",
            category=RunbookCategory.MONITORING,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=10,
            prerequisites=[],
            steps=[
                {
                    "name": "Main Step",
                    "description": "Main step",
                    "command": "echo 'main step'",
                    "verification": "Should pass"
                }
            ],
            verification_steps=[
                {
                    "name": "Verification Step",
                    "description": "Verification step",
                    "check": "echo 'verification check'"
                },
                {
                    "name": "Failing Verification",
                    "description": "This verification should fail",
                    "check": "false"
                }
            ],
            rollback_steps=[],
            escalation_contacts=[],
            related_runbooks=[],
            tags=["test"]
        )

        documentation_framework.create_runbook(runbook)

        # Execute runbook
        result = documentation_framework.execute_runbook("test_verification", dry_run=True)

        # Main step should succeed
        assert result["status"] == "completed", "Should complete"
        assert result["step_results"][0]["success"] is True, "Main step should succeed"

        # Should have verification results
        assert len(result["verification_results"]) == 2, "Should have 2 verification results"

        # One verification should pass, one should fail
        passed_verifications = [vr for vr in result["verification_results"] if vr["success"]]
        assert len(passed_verifications) == 1, "One verification should pass"

        # Overall success should be False because one verification failed
        assert result["success"] is False, "Overall should fail due to failed verification"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_runbook_versioning(self, documentation_framework):
        """Test runbook versioning"""
        runbook = Runbook(
            runbook_id="test_versioning",
            title="Test Versioning",
            description="Test runbook versioning",
            category=RunbookCategory.MAINTENANCE,
            severity=IncidentSeverity.LOW,
            estimated_duration_minutes=5,
            prerequisites=[],
            steps=[],
            verification_steps=[],
            rollback_steps=[],
            escalation_contacts=[],
            related_runbooks=[],
            tags=["test"]
        )

        # Create initial version
        initial_id = documentation_framework.create_runbook(runbook)
        assert documentation_framework.get_runbook(initial_id).version == "1.0", "Initial version should be 1.0"

        # Update version
        runbook.version = "2.0"
        documentation_framework.create_runbook(runbook)
        updated_runbook = documentation_framework.get_runbook(initial_id)
        assert updated_runbook.version == "2.0", "Version should be updated"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_runbook_tags_functionality(self, documentation_framework):
        """Test runbook tags functionality"""
        tags_to_test = ["api", "database", "security", "performance"]

        for tag in tags_to_test:
            runbook = Runbook(
                runbook_id=f"test_{tag}",
                title=f"Test {tag}",
                description=f"Test runbook for {tag}",
                category=RunbookCategory.TROUBLESHOOTING,
                severity=IncidentSeverity.MEDIUM,
                estimated_duration_minutes=10,
                prerequisites=[],
                steps=[],
                verification_steps=[],
                rollback_steps=[],
                escalation_contacts=[],
                related_runbooks=[],
                tags=[tag]
            )

            documentation_framework.create_runbook(runbook)

        # Search by tags
        for tag in tags_to_test:
            tagged_runbooks = documentation_framework.search_runbooks("", tags=[tag])
            assert len(tagged_runbooks) > 0, f"Should find runbooks with tag '{tag}'"
            assert all(tag in rb.tags for rb in tagged_runbooks), f"All found runbooks should have tag '{tag}'"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_escalation_contacts_structure(self, documentation_framework):
        """Test escalation contacts structure"""
        runbook = Runbook(
            runbook_id="test_contacts",
            title="Test Contacts",
            description="Test escalation contacts",
            category=RunbookCategory.EMERGENCY,
            severity=IncidentSeverity.HIGH,
            estimated_duration_minutes=15,
            prerequisites=[],
            steps=[],
            verification_steps=[],
            rollback_steps=[],
            escalation_contacts=[
                {
                    "role": "Test Role",
                    "contact": "test@example.com",
                    "priority": "high"
                }
            ],
            related_runbooks=[],
            tags=["test"]
        )

        documentation_framework.create_runbook(runbook)

        created_runbook = documentation_framework.get_runbook("test_contacts")
        assert len(created_runbook.escalation_contacts) == 1, "Should have one contact"

        contact = created_runbook.escalation_contacts[0]
        assert "role" in contact, "Contact should have role"
        assert "contact" in contact, "Contact should have contact info"
        assert "priority" in contact, "Contact should have priority"

    @pytest.mark.production
    @pytest.mark.procedures
    def test_related_runbooks_structure(self, documentation_framework):
        """Test related runbooks functionality"""
        related_ids = ["runbook1", "runbook2"]

        runbook = Runbook(
            runbook_id="test_related",
            title="Test Related Runbooks",
            description="Test related runbooks functionality",
            category=RunbookCategory.TROUBLESHOOTING,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=10,
            prerequisites=[],
            steps=[],
            verification_steps=[],
            rollback_steps=[],
            escalation_contacts=[],
            related_runbooks=related_ids,
            tags=["test"]
        )

        documentation_framework.create_runbook(runbook)

        created_runbook = documentation_framework.get_runbook("test_related")
        assert len(created_runbook.related_runbooks) == 2, "Should have 2 related runbooks"
        assert all(rb in related_ids for rb in created_runbook.related_runbooks), "Should have specified related runbooks"

    @pytest.mark.production
    @pytest.mark.documentation
    def test_runbook_prerequisites(self, documentation_framework):
        """Test runbook prerequisites"""
        prerequisites = [
            "Admin access",
            "Backup available",
            "Maintenance window"
        ]

        runbook = Runbook(
            runbook_id="test_prerequisites",
            title="Test Prerequisites",
            description="Test runbook prerequisites",
            category=RunbookCategory.DEPLOYMENT,
            severity=IncidentSeverity.MEDIUM,
            estimated_duration_minutes=20,
            prerequisites=prerequisites,
            steps=[],
            verification_steps=[],
            rollback_steps=[],
            escalation_contacts=[],
            related_runbooks=[],
            tags=["test"]
        )

        documentation_framework.create_runbook(runbook)

        created_runbook = documentation_framework.get_runbook("test_prerequisites")
        assert len(created_runbook.prerequisites) == 3, "Should have 3 prerequisites"
        assert all(prereq in created_runbook.prerequisites for prereq in prerequisites), "Should have specified prerequisites"


# Integration with existing test framework
pytest_plugins = []