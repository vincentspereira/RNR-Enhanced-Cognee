"""
Security Deployment and Monitoring System

Production-ready security deployment with automated monitoring, alerts, and incident response
"""

import asyncio
import logging
import json
import os
import smtplib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import certifi
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import schedule
import time
import threading

from .enhanced_security_framework import EnhancedSecurityFramework, SecurityEvent


class SecurityIncidentSeverity(Enum):
    """Security incident severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


@dataclass
class SecurityIncident:
    """Security incident data structure"""
    incident_id: str
    severity: SecurityIncidentSeverity
    incident_type: str
    source_ip: str
    affected_systems: List[str]
    description: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    actions_taken: List[str] = None
    impact_assessment: str = ""

    def __post_init__(self):
        if self.actions_taken is None:
            self.actions_taken = []


@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    condition: str
    severity_threshold: SecurityIncidentSeverity
    channels: List[AlertChannel]
    enabled: bool = True
    cooldown_minutes: int = 15
    last_triggered: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SecurityMetrics:
    """Prometheus metrics for security monitoring"""

    def __init__(self):
        self.security_events_total = Counter(
            'cognee_security_events_total',
            'Total number of security events',
            ['event_type', 'severity']
        )

        self.security_incidents_total = Counter(
            'cognee_security_incidents_total',
            'Total number of security incidents',
            ['severity', 'incident_type']
        )

        self.blocked_requests_total = Counter(
            'cognee_blocked_requests_total',
            'Total number of blocked requests',
            ['block_reason']
        )

        self.file_upload_attempts_total = Counter(
            'cognee_file_upload_attempts_total',
            'Total number of file upload attempts',
            ['result', 'file_type']
        )

        self.password_validation_failures_total = Counter(
            'cognee_password_validation_failures_total',
            'Total number of password validation failures',
            ['failure_reason']
        )

        self.rate_limit_violations_total = Counter(
            'cognee_rate_limit_violations_total',
            'Total number of rate limit violations',
            ['endpoint', 'source_ip']
        )

        self.security_scan_duration_seconds = Histogram(
            'cognee_security_scan_duration_seconds',
            'Time spent on security scans',
            ['scan_type']
        )

        self.active_security_incidents = Gauge(
            'cognee_active_security_incidents',
            'Number of active security incidents',
            ['severity']
        )

        self.dependency_vulnerabilities = Gauge(
            'cognee_dependency_vulnerabilities',
            'Number of dependency vulnerabilities',
            ['severity']
        )


class AlertManager:
    """Manages security alerts and notifications"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics = SecurityMetrics()
        self.logger = logging.getLogger(__name__)
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_incidents: Dict[str, SecurityIncident] = {}
        self.cooldown_periods: Dict[str, datetime] = {}

    def load_alert_rules(self, rules_file: str):
        """Load alert rules from configuration file"""
        try:
            with open(rules_file, 'r') as f:
                rules_data = yaml.safe_load(f)

            for rule_data in rules_data.get('alert_rules', []):
                rule = AlertRule(
                    rule_id=rule_data['rule_id'],
                    name=rule_data['name'],
                    description=rule_data['description'],
                    condition=rule_data['condition'],
                    severity_threshold=SecurityIncidentSeverity(rule_data['severity_threshold']),
                    channels=[AlertChannel(ch) for ch in rule_data['channels']],
                    enabled=rule_data.get('enabled', True),
                    cooldown_minutes=rule_data.get('cooldown_minutes', 15)
                )
                self.alert_rules[rule.rule_id] = rule

            self.logger.info(f"Loaded {len(self.alert_rules)} alert rules")

        except Exception as e:
            self.logger.error(f"Failed to load alert rules: {e}")

    async def process_security_event(self, event: SecurityEvent) -> Optional[SecurityIncident]:
        """Process security event and potentially create incident"""

        # Update metrics
        self.metrics.security_events_total.labels(
            event_type=event.event_type,
            severity=event.severity
        ).inc()

        # Check alert rules
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue

            # Check cooldown
            if rule.rule_id in self.cooldown_periods:
                if datetime.now() - self.cooldown_periods[rule.rule_id] < timedelta(minutes=rule.cooldown_minutes):
                    continue

            # Evaluate rule condition (simplified for demo)
            if self._evaluate_rule_condition(rule, event):
                # Create incident
                incident = SecurityIncident(
                    incident_id=self._generate_incident_id(),
                    severity=self._determine_incident_severity(event, rule),
                    incident_type=event.event_type,
                    source_ip=event.source_ip,
                    affected_systems=self._determine_affected_systems(event),
                    description=f"Security incident: {event.event_type} - {event.details}",
                    timestamp=event.timestamp
                )

                self.active_incidents[incident.incident_id] = incident
                self.cooldown_periods[rule.rule_id] = datetime.now()

                # Update metrics
                self.metrics.security_incidents_total.labels(
                    severity=incident.severity.value,
                    incident_type=incident.incident_type
                ).inc()

                self.metrics.active_security_incidents.labels(
                    severity=incident.severity.value
                ).inc()

                # Send alerts
                await self._send_alerts(incident, rule.channels)

                return incident

        return None

    def _evaluate_rule_condition(self, rule: AlertRule, event: SecurityEvent) -> bool:
        """Evaluate alert rule condition (simplified logic)"""
        # This is a simplified evaluation - in production, you'd use a proper rule engine
        condition = rule.condition.lower()
        event_str = f"{event.event_type} {event.severity} {json.dumps(event.details)}".lower()

        # Simple keyword matching
        if "event_type:" in condition:
            expected_type = condition.split("event_type:")[1].strip().strip('"\'')
            if expected_type not in event_str:
                return False

        if "severity:" in condition:
            expected_severity = condition.split("severity:")[1].strip().strip('"\'')
            severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            event_level = severity_levels.get(event.severity, 0)
            rule_level = severity_levels.get(rule.severity_threshold.value, 0)

            if event_level < rule_level:
                return False

        return True

    def _determine_incident_severity(self, event: SecurityEvent, rule: AlertRule) -> SecurityIncidentSeverity:
        """Determine incident severity based on event and rule"""
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        event_level = severity_levels.get(event.severity, 0)
        rule_level = severity_levels.get(rule.severity_threshold.value, 0)

        # Use higher severity between event and rule threshold
        final_level = max(event_level, rule_level)
        return SecurityIncidentSeverity([k for k, v in severity_levels.items() if v == final_level][0])

    def _determine_affected_systems(self, event: SecurityEvent) -> List[str]:
        """Determine which systems are affected by the event"""
        systems = []

        event_type = event.event_type.lower()
        details = event.details

        if "auth" in event_type or "password" in event_type:
            systems.append("authentication")
        if "file" in event_type or "upload" in event_type:
            systems.append("file_system")
        if "api" in event_type or "endpoint" in event_type:
            systems.append("api_gateway")
        if "database" in event_type or "sql" in event_type:
            systems.append("database")
        if "network" in event_type or "rate_limit" in event_type:
            systems.append("network")

        return systems if systems else ["general"]

    async def _send_alerts(self, incident: SecurityIncident, channels: List[AlertChannel]):
        """Send alerts through specified channels"""

        alert_message = self._format_alert_message(incident)

        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    await self._send_email_alert(alert_message, incident)
                elif channel == AlertChannel.SLACK:
                    await self._send_slack_alert(alert_message, incident)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert_message, incident)
                elif channel == AlertChannel.SMS:
                    await self._send_sms_alert(alert_message, incident)
                elif channel == AlertChannel.PAGERDUTY:
                    await self._send_pagerduty_alert(alert_message, incident)

            except Exception as e:
                self.logger.error(f"Failed to send {channel.value} alert: {e}")

    def _format_alert_message(self, incident: SecurityIncident) -> Dict[str, Any]:
        """Format alert message for different channels"""
        return {
            "title": f"Security Alert: {incident.severity.value.upper()} - {incident.incident_type}",
            "incident_id": incident.incident_id,
            "severity": incident.severity.value,
            "description": incident.description,
            "source_ip": incident.source_ip,
            "affected_systems": incident.affected_systems,
            "timestamp": incident.timestamp.isoformat(),
            "actions_required": self._get_required_actions(incident)
        }

    def _get_required_actions(self, incident: SecurityIncident) -> List[str]:
        """Get required actions based on incident type and severity"""
        actions = []

        if incident.severity == SecurityIncidentSeverity.CRITICAL:
            actions.extend([
                "IMMEDIATE: Block source IP address",
                "IMMEDIATE: Investigate potential breach",
                "WITHIN 30 MIN: Document incident details",
                "WITHIN 1 HOUR: Notify management"
            ])
        elif incident.severity == SecurityIncidentSeverity.HIGH:
            actions.extend([
                "WITHIN 15 MIN: Review and analyze logs",
                "WITHIN 30 MIN: Implement additional controls if needed",
                "WITHIN 2 HOUR: Document and report incident"
            ])
        elif incident.severity == SecurityIncidentSeverity.MEDIUM:
            actions.extend([
                "WITHIN 1 HOUR: Investigate source and impact",
                "WITHIN 4 HOUR: Update monitoring if needed",
                "WITHIN 24 HOUR: Document for trend analysis"
            ])
        else:
            actions.extend([
                "WITHIN 24 HOUR: Review for patterns",
                "WEEKLY: Include in security report"
            ])

        # Add incident-specific actions
        if "authentication" in incident.affected_systems:
            actions.append("Review user account security")
        if "file_system" in incident.affected_systems:
            actions.append("Scan uploaded files for malware")
        if "api_gateway" in incident.affected_systems:
            actions.append("Review API access logs")

        return actions

    async def _send_email_alert(self, alert_message: Dict[str, Any], incident: SecurityIncident):
        """Send email alert"""
        email_config = self.config.get('email', {})
        if not email_config.get('enabled'):
            return

        smtp_server = email_config.get('smtp_server')
        smtp_port = email_config.get('smtp_port', 587)
        username = email_config.get('username')
        password = email_config.get('password')
        recipients = email_config.get('recipients', [])

        if not all([smtp_server, username, password, recipients]):
            self.logger.warning("Email configuration incomplete")
            return

        try:
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = alert_message['title']

            body = f"""
Security Incident Alert

Incident ID: {incident.incident_id}
Severity: {incident.severity.value.upper()}
Type: {incident.incident_type}
Source IP: {incident.source_ip}
Affected Systems: {', '.join(incident.affected_systems)}
Timestamp: {incident.timestamp}

Description:
{incident.description}

Required Actions:
{chr(10).join(f"- {action}" for action in alert_message['actions_required'])}

---
Cognee Security System
            """

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email alert sent for incident {incident.incident_id}")

        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    async def _send_slack_alert(self, alert_message: Dict[str, Any], incident: SecurityIncident):
        """Send Slack alert"""
        slack_config = self.config.get('slack', {})
        if not slack_config.get('enabled'):
            return

        webhook_url = slack_config.get('webhook_url')
        channel = slack_config.get('channel', '#security-alerts')

        if not webhook_url:
            self.logger.warning("Slack webhook URL not configured")
            return

        try:
            # Color based on severity
            severity_colors = {
                'low': 'good',
                'medium': 'warning',
                'high': 'danger',
                'critical': '#ff0000'
            }

            payload = {
                "channel": channel,
                "username": "Cognee Security",
                "icon_emoji": ":shield:",
                "attachments": [{
                    "color": severity_colors.get(incident.severity.value, 'warning'),
                    "title": alert_message['title'],
                    "fields": [
                        {"title": "Incident ID", "value": incident.incident_id, "short": True},
                        {"title": "Severity", "value": incident.severity.value.upper(), "short": True},
                        {"title": "Source IP", "value": incident.source_ip, "short": True},
                        {"title": "Affected Systems", "value": ', '.join(incident.affected_systems), "short": True},
                        {"title": "Description", "value": incident.description, "short": False}
                    ],
                    "footer": "Cognee Security System",
                    "ts": int(incident.timestamp.timestamp())
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack alert sent for incident {incident.incident_id}")
                    else:
                        self.logger.error(f"Failed to send Slack alert: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    async def _send_webhook_alert(self, alert_message: Dict[str, Any], incident: SecurityIncident):
        """Send webhook alert"""
        webhook_config = self.config.get('webhook', {})
        if not webhook_config.get('enabled'):
            return

        webhook_url = webhook_config.get('url')
        headers = webhook_config.get('headers', {})

        if not webhook_url:
            self.logger.warning("Webhook URL not configured")
            return

        try:
            payload = {
                "incident": alert_message,
                "timestamp": datetime.now().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook alert sent for incident {incident.incident_id}")
                    else:
                        self.logger.error(f"Failed to send webhook alert: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    async def _send_sms_alert(self, alert_message: Dict[str, Any], incident: SecurityIncident):
        """Send SMS alert (placeholder)"""
        # SMS integration would go here
        # For now, just log that SMS would be sent
        self.logger.info(f"SMS alert would be sent for critical incident {incident.incident_id}")

    async def _send_pagerduty_alert(self, alert_message: Dict[str, Any], incident: SecurityIncident):
        """Send PagerDuty alert (placeholder)"""
        # PagerDuty integration would go here
        # For now, just log that PagerDuty would be triggered
        self.logger.info(f"PagerDuty alert would be triggered for critical incident {incident.incident_id}")

    def _generate_incident_id(self) -> str:
        """Generate unique incident ID"""
        return f"INC-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"

    def resolve_incident(self, incident_id: str, resolution_notes: str):
        """Resolve a security incident"""
        if incident_id in self.active_incidents:
            incident = self.active_incidents[incident_id]
            incident.resolved = True
            incident.resolution_time = datetime.now()
            incident.actions_taken.append(f"Resolved: {resolution_notes}")

            # Update metrics
            self.metrics.active_security_incidents.labels(
                severity=incident.severity.value
            ).dec()

            self.logger.info(f"Resolved incident {incident_id}")
            return True

        return False


class SecurityMonitoringService:
    """Main security monitoring service"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.security_framework = EnhancedSecurityFramework()
        self.alert_manager = AlertManager(config)
        self.metrics = SecurityMetrics()
        self.logger = logging.getLogger(__name__)
        self.monitoring_active = False

    async def start_monitoring(self):
        """Start the security monitoring service"""
        self.logger.info("Starting security monitoring service")

        # Load alert rules
        rules_file = self.config.get('alert_rules_file', 'config/alert_rules.yaml')
        self.alert_manager.load_alert_rules(rules_file)

        # Start Prometheus metrics server
        metrics_port = self.config.get('metrics_port', 8090)
        start_http_server(metrics_port)
        self.logger.info(f"Prometheus metrics server started on port {metrics_port}")

        # Start monitoring loop
        self.monitoring_active = True
        await self._monitoring_loop()

    async def stop_monitoring(self):
        """Stop the security monitoring service"""
        self.monitoring_active = False
        self.logger.info("Security monitoring service stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Process security events from framework
                await self._process_pending_security_events()

                # Run periodic security checks
                await self._run_periodic_checks()

                # Update metrics
                await self._update_metrics()

                # Sleep before next iteration
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retry

    async def _process_pending_security_events(self):
        """Process pending security events from the framework"""
        # This would integrate with the security framework's event queue
        # For demo purposes, we'll simulate processing events
        pass

    async def _run_periodic_checks(self):
        """Run periodic security checks"""
        try:
            # Check for dependency vulnerabilities
            dependency_check = self.security_framework.dependency_updater.check_dependencies()
            if 'vulnerable_packages' in dependency_check:
                vulnerable_count = len(dependency_check['vulnerable_packages'])
                self.metrics.dependency_vulnerabilities.set(vulnerable_count)

                if vulnerable_count > 0:
                    # Create security event for vulnerabilities
                    event = SecurityEvent(
                        event_type="dependency_vulnerabilities",
                        severity="medium" if vulnerable_count < 5 else "high",
                        source_ip="system",
                        user_agent="security-monitor",
                        timestamp=datetime.now(),
                        details=dependency_check
                    )

                    await self.alert_manager.process_security_event(event)

        except Exception as e:
            self.logger.error(f"Error in periodic checks: {e}")

    async def _update_metrics(self):
        """Update security metrics"""
        try:
            # Update active incidents count
            active_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            for incident in self.alert_manager.active_incidents.values():
                active_counts[incident.severity.value] += 1

            for severity, count in active_counts.items():
                self.metrics.active_security_incidents.labels(severity=severity).set(count)

        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        active_incidents = list(self.alert_manager.active_incidents.values())

        # Sort by severity and timestamp
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        active_incidents.sort(key=lambda x: (severity_order[x.severity.value], x.timestamp), reverse=True)

        return {
            "monitoring_active": self.monitoring_active,
            "active_incidents": len(active_incidents),
            "incidents_by_severity": {
                severity: sum(1 for inc in active_incidents if inc.severity.value == severity)
                for severity in ['critical', 'high', 'medium', 'low']
            },
            "recent_incidents": [
                {
                    "incident_id": inc.incident_id,
                    "severity": inc.severity.value,
                    "type": inc.incident_type,
                    "timestamp": inc.timestamp.isoformat(),
                    "description": inc.description,
                    "source_ip": inc.source_ip
                }
                for inc in active_incidents[:10]  # Last 10 incidents
            ],
            "metrics_port": self.config.get('metrics_port', 8090),
            "alert_rules_enabled": len([r for r in self.alert_manager.alert_rules.values() if r.enabled])
        }


# Configuration management
def load_security_config(config_file: str = "config/security_config.yaml") -> Dict[str, Any]:
    """Load security configuration from file"""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Set default values
        config.setdefault('metrics_port', 8090)
        config.setdefault('alert_rules_file', 'config/alert_rules.yaml')

        return config

    except Exception as e:
        logging.error(f"Failed to load security config: {e}")
        return {
            "metrics_port": 8090,
            "alert_rules_file": "config/alert_rules.yaml",
            "email": {"enabled": False},
            "slack": {"enabled": False},
            "webhook": {"enabled": False}
        }


def create_default_config():
    """Create default security configuration"""
    config = {
        "metrics_port": 8090,
        "alert_rules_file": "config/alert_rules.yaml",
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "recipients": ["security@example.com"]
        },
        "slack": {
            "enabled": False,
            "webhook_url": "",
            "channel": "#security-alerts"
        },
        "webhook": {
            "enabled": False,
            "url": "",
            "headers": {
                "Authorization": "Bearer YOUR_TOKEN",
                "Content-Type": "application/json"
            }
        }
    }

    # Ensure config directory exists
    os.makedirs("config", exist_ok=True)

    # Write config file
    with open("config/security_config.yaml", 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def create_default_alert_rules():
    """Create default alert rules"""
    rules = {
        "alert_rules": [
            {
                "rule_id": "critical_file_upload_block",
                "name": "Critical File Upload Blocked",
                "description": "Alert when malicious file upload is blocked",
                "condition": "event_type:file_upload_blocked AND severity:high",
                "severity_threshold": "high",
                "channels": ["email", "slack"],
                "enabled": True,
                "cooldown_minutes": 5
            },
            {
                "rule_id": "authentication_failure_spike",
                "name": "Authentication Failure Spike",
                "description": "Alert on spike in authentication failures",
                "condition": "event_type:authentication_failure AND severity:medium",
                "severity_threshold": "medium",
                "channels": ["email"],
                "enabled": True,
                "cooldown_minutes": 15
            },
            {
                "rule_id": "potential_injection_attempt",
                "name": "Potential Injection Attack",
                "description": "Alert on potential SQL injection attempts",
                "condition": "event_type:potential_injection AND severity:high",
                "severity_threshold": "high",
                "channels": ["email", "slack", "webhook"],
                "enabled": True,
                "cooldown_minutes": 10
            },
            {
                "rule_id": "rate_limit_exceeded",
                "name": "Rate Limit Exceeded",
                "description": "Alert when rate limits are exceeded",
                "condition": "event_type:rate_limit_exceeded AND severity:medium",
                "severity_threshold": "medium",
                "channels": ["slack"],
                "enabled": True,
                "cooldown_minutes": 5
            },
            {
                "rule_id": "dependency_vulnerabilities",
                "name": "Dependency Vulnerabilities Detected",
                "description": "Alert when dependency vulnerabilities are found",
                "condition": "event_type:dependency_vulnerabilities AND severity:medium",
                "severity_threshold": "medium",
                "channels": ["email"],
                "enabled": True,
                "cooldown_minutes": 60
            }
        ]
    }

    # Ensure config directory exists
    os.makedirs("config", exist_ok=True)

    # Write alert rules file
    with open("config/alert_rules.yaml", 'w') as f:
        yaml.dump(rules, f, default_flow_style=False)


# Main entry point
async def main():
    """Main entry point for security monitoring service"""
    import argparse
    import secrets

    parser = argparse.ArgumentParser(description="Cognee Security Monitoring Service")
    parser.add_argument("--config", default="config/security_config.yaml", help="Configuration file")
    parser.add_argument("--create-config", action="store_true", help="Create default configuration")
    parser.add_argument("--create-rules", action="store_true", help="Create default alert rules")

    args = parser.parse_args()

    if args.create_config:
        create_default_config()
        print("Default security configuration created at config/security_config.yaml")
        return

    if args.create_rules:
        create_default_alert_rules()
        print("Default alert rules created at config/alert_rules.yaml")
        return

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load configuration
    config = load_security_config(args.config)

    # Create and start monitoring service
    monitoring_service = SecurityMonitoringService(config)

    try:
        print("Starting Cognee Security Monitoring Service...")
        await monitoring_service.start_monitoring()

    except KeyboardInterrupt:
        print("\nShutting down security monitoring service...")
        await monitoring_service.stop_monitoring()

    except Exception as e:
        print(f"Error starting monitoring service: {e}")
        await monitoring_service.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())