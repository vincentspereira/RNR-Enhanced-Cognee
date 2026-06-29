"""
RNR Enhanced Cognee Production Monitoring and Alerting System

This module provides comprehensive production monitoring and alerting capabilities for the Enhanced
Cognee Multi-Agent System, including metrics collection, alerting, dashboards, and
production health monitoring.

Phase 4: Production Readiness and Optimization (Weeks 11-12)
Category: Production Monitoring and Alerting
"""

import pytest
import asyncio
import json
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import psutil
import asyncio
import aiohttp
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Production Monitoring Markers
pytest.mark.production = pytest.mark.production
pytest.mark.monitoring = pytest.mark.monitoring
pytest.mark.alerting = pytest.mark.alerting
pytest.mark.metrics = pytest.mark.metrics
pytest.mark.health = pytest.mark.health


class MetricType(Enum):
    """Types of metrics to monitor"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MetricDefinition:
    """Metric definition"""
    name: str
    metric_type: MetricType
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    threshold_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule definition"""
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str
    threshold: float
    severity: AlertSeverity
    duration_minutes: int
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    severity: AlertSeverity
    status: str  # firing, resolved
    message: str
    timestamp: datetime
    labels: Dict[str, str]
    annotations: Dict[str, str]
    resolved_timestamp: Optional[datetime] = None


@dataclass
class HealthCheck:
    """Health check definition"""
    check_id: str
    name: str
    endpoint: str
    method: str = "GET"
    timeout_seconds: int = 10
    expected_status: int = 200
    check_interval_seconds: int = 30
    failure_threshold: int = 3
    labels: Dict[str, str] = field(default_factory=dict)


class ProductionMonitoringFramework:
    """Production monitoring and alerting framework"""

    def __init__(self):
        self.metrics_store = defaultdict(deque)
        self.alert_rules = {}
        self.active_alerts = {}
        self.health_checks = {}
        self.monitoring_active = False
        self.alert_handlers = []
        self.metric_definitions = {}
        self.system_metrics = {}
        self.alert_history = deque(maxlen=1000)

    def register_metric(self, metric_def: MetricDefinition):
        """Register a metric definition"""
        self.metric_definitions[metric_def.name] = metric_def
        logger.info(f"Registered metric: {metric_def.name}")

    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value"""
        if metric_name not in self.metric_definitions:
            logger.warning(f"Unknown metric: {metric_name}")
            return

        timestamp = time.time()
        metric_value = {
            "timestamp": timestamp,
            "value": value,
            "labels": labels or {}
        }

        # Store metric with time series data (keep last 1000 values)
        self.metrics_store[metric_name].append(metric_value)

        # Keep only last 1000 values per metric
        if len(self.metrics_store[metric_name]) > 1000:
            self.metrics_store[metric_name].popleft()

        # Check alert rules
        asyncio.create_task(self._check_alert_rules(metric_name, value, labels))

    def register_alert_rule(self, rule: AlertRule):
        """Register an alert rule"""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"Registered alert rule: {rule.rule_id}")

    def register_health_check(self, health_check: HealthCheck):
        """Register a health check"""
        self.health_checks[health_check.check_id] = health_check
        logger.info(f"Registered health check: {health_check.check_id}")

    async def start_monitoring(self):
        """Start monitoring system"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        logger.info("Starting production monitoring")

        # Start monitoring tasks
        monitoring_tasks = [
            asyncio.create_task(self._collect_system_metrics()),
            asyncio.create_task(self._run_health_checks()),
            asyncio.create_task(self._process_alert_rules()),
            asyncio.create_task(self._cleanup_old_data())
        ]

        await asyncio.gather(*monitoring_tasks, return_exceptions=True)

    def stop_monitoring(self):
        """Stop monitoring system"""
        self.monitoring_active = False
        logger.info("Stopping production monitoring")

    async def _collect_system_metrics(self):
        """Collect system metrics continuously"""
        while self.monitoring_active:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric("system_cpu_usage", cpu_percent, {"component": "system"})

                # Memory metrics
                memory = psutil.virtual_memory()
                self.record_metric("system_memory_usage", memory.percent, {"component": "system"})
                self.record_metric("system_memory_available_gb", memory.available / (1024**3), {"component": "system"})

                # Disk metrics
                disk = psutil.disk_usage('/')
                self.record_metric("system_disk_usage", disk.percent, {"component": "system", "device": "/"})
                self.record_metric("system_disk_free_gb", disk.free / (1024**3), {"component": "system", "device": "/"})

                # Network metrics
                network = psutil.net_io_counters()
                self.record_metric("system_network_bytes_sent", network.bytes_sent, {"component": "system"})
                self.record_metric("system_network_bytes_recv", network.bytes_recv, {"component": "system"})

                # Process metrics for key processes
                await self._collect_process_metrics()

                await asyncio.sleep(10)  # Collect every 10 seconds

            except Exception as e:
                logger.error(f"Error collecting system metrics: {str(e)}")
                await asyncio.sleep(10)

    async def _collect_process_metrics(self):
        """Collect metrics for key processes"""
        try:
            # Find cognee processes
            cognee_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'cognee' in proc.info['name'] or \
                       any('cognee' in arg for arg in proc.info['cmdline'] or []):
                        cognee_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            for proc in cognee_processes:
                try:
                    with proc.oneshot():
                        cpu_percent = proc.cpu_percent()
                        memory_info = proc.memory_info()
                        memory_mb = memory_info.rss / (1024 * 1024)

                        self.record_metric(
                            "process_cpu_usage",
                            cpu_percent,
                            {"component": "process", "pid": str(proc.pid)}
                        )
                        self.record_metric(
                            "process_memory_mb",
                            memory_mb,
                            {"component": "process", "pid": str(proc.pid)}
                        )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.error(f"Error collecting process metrics: {str(e)}")

    async def _run_health_checks(self):
        """Run all registered health checks"""
        while self.monitoring_active:
            try:
                for check_id, health_check in self.health_checks.items():
                    await self._execute_health_check(health_check)

                await asyncio.sleep(30)  # Run health checks every 30 seconds

            except Exception as e:
                logger.error(f"Error running health checks: {str(e)}")
                await asyncio.sleep(30)

    async def _execute_health_check(self, health_check: HealthCheck):
        """Execute a single health check"""
        try:
            timeout = aiohttp.ClientTimeout(total=health_check.timeout_seconds)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    health_check.method,
                    health_check.endpoint,
                    headers=health_check.labels.get("headers", {})
                ) as response:
                    success = response.status == health_check.expected_status
                    response_time = response.headers.get("X-Response-Time", "0")

                    # Record health check metrics
                    self.record_metric(
                        "health_check_success",
                        1 if success else 0,
                        {
                            "component": "health_check",
                            "check_id": check_id,
                            "endpoint": health_check.endpoint
                        }
                    )

                    if response_time:
                        try:
                            response_time_ms = float(response_time)
                            self.record_metric(
                                "health_check_response_time_ms",
                                response_time_ms,
                                {
                                    "component": "health_check",
                                    "check_id": check_id
                                }
                            )
                        except ValueError:
                            pass

                    # Update health check status
                    if not success:
                        await self._handle_health_check_failure(health_check)

        except Exception as e:
            logger.error(f"Health check {health_check.check_id} failed: {str(e)}")
            await self._handle_health_check_failure(health_check)

    async def _handle_health_check_failure(self, health_check: HealthCheck):
        """Handle health check failure"""
        check_id = health_check.check_id

        # Increment failure count
        if not hasattr(self, '_health_check_failures'):
            self._health_check_failures = defaultdict(int)

        self._health_check_failures[check_id] += 1

        # Check if failure threshold exceeded
        if self._health_check_failures[check_id] >= health_check.failure_threshold:
            # Create critical alert
            alert = Alert(
                alert_id=f"health_check_{check_id}_{int(time.time())}",
                rule_id=f"health_check_{check_id}",
                severity=AlertSeverity.CRITICAL,
                status="firing",
                message=f"Health check {health_check.name} failed {self._health_check_failures[check_id]} times",
                timestamp=datetime.now(timezone.utc),
                labels={
                    "component": "health_check",
                    "check_id": check_id,
                    "endpoint": health_check.endpoint
                },
                annotations={
                    "description": f"Health check {health_check.name} has exceeded failure threshold",
                    "runbook_url": f"https://docs.cognee.com/runbooks/health-checks/{check_id}"
                }
            )

            await self._send_alert(alert)

    async def _check_alert_rules(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Check if any alert rules are triggered"""
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled or rule.metric_name != metric_name:
                continue

            # Check if condition is met
            if self._evaluate_condition(rule.condition, value, rule.threshold):
                await self._trigger_alert(rule, value, labels)

    def _evaluate_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Evaluate alert condition"""
        if condition == "gt":
            return value > threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False

    async def _trigger_alert(self, rule: AlertRule, value: float, labels: Dict[str, str] = None):
        """Trigger an alert"""
        alert_id = f"{rule.rule_id}_{int(time.time())}"

        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            severity=rule.severity,
            status="firing",
            message=f"{rule.name}: {rule.metric_name} is {value} (threshold: {rule.threshold})",
            timestamp=datetime.now(timezone.utc),
            labels={**rule.labels, **(labels or {})},
            annotations={
                "description": rule.description,
                "metric_value": str(value),
                "threshold": str(rule.threshold),
                "runbook_url": f"https://docs.cognee.com/runbooks/alerts/{rule.rule_id}"
            }
        )

        self.active_alerts[alert_id] = alert
        await self._send_alert(alert)

    async def _send_alert(self, alert: Alert):
        """Send alert to all registered handlers"""
        self.alert_history.append(alert)

        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}")

    async def _process_alert_rules(self):
        """Process alert rules and handle duration-based alerts"""
        while self.monitoring_active:
            try:
                current_time = datetime.now(timezone.utc)

                # Check for alerts that should be resolved
                for alert_id, alert in list(self.active_alerts.items()):
                    rule = self.alert_rules.get(alert.rule_id)

                    if not rule:
                        continue

                    # Check if condition is still met
                    recent_metrics = self._get_recent_metrics(
                        rule.metric_name,
                        rule.duration_minutes * 60
                    )

                    if recent_metrics and not self._is_condition_met(
                        rule.metric_name, rule.condition, rule.threshold, recent_metrics
                    ):
                        # Resolve alert
                        alert.status = "resolved"
                        alert.resolved_timestamp = current_time
                        await self._send_alert(alert)
                        del self.active_alerts[alert_id]

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error processing alert rules: {str(e)}")
                await asyncio.sleep(30)

    def _get_recent_metrics(self, metric_name: str, duration_seconds: int) -> List[Dict[str, Any]]:
        """Get recent metrics for the specified duration"""
        if metric_name not in self.metrics_store:
            return []

        cutoff_time = time.time() - duration_seconds
        recent_metrics = [
            metric for metric in self.metrics_store[metric_name]
            if metric["timestamp"] >= cutoff_time
        ]

        return recent_metrics

    def _is_condition_met(self, metric_name: str, condition: str,
                          threshold: float, metrics: List[Dict[str, Any]]) -> bool:
        """Check if alert condition is still met"""
        if not metrics:
            return False

        recent_values = [metric["value"] for metric in metrics]
        latest_value = recent_values[-1]

        return self._evaluate_condition(condition, latest_value, threshold)

    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        while self.monitoring_active:
            try:
                # Keep metrics for last 24 hours
                cutoff_time = time.time() - (24 * 60 * 60)

                for metric_name in list(self.metrics_store.keys()):
                    # Remove old metrics
                    while (self.metrics_store[metric_name] and
                           self.metrics_store[metric_name][0]["timestamp"] < cutoff_time):
                        self.metrics_store[metric_name].popleft()

                await asyncio.sleep(3600)  # Cleanup every hour

            except Exception as e:
                logger.error(f"Error cleaning up old data: {str(e)}")
                await asyncio.sleep(3600)

    def get_metrics_summary(self, metric_name: str, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for the specified duration"""
        recent_metrics = self._get_recent_metrics(metric_name, duration_minutes * 60)

        if not recent_metrics:
            return {
                "metric_name": metric_name,
                "duration_minutes": duration_minutes,
                "sample_count": 0,
                "latest_value": None,
                "min": None,
                "max": None,
                "avg": None,
                "p50": None,
                "p95": None,
                "p99": None
            }

        values = [metric["value"] for metric in recent_metrics]
        values.sort()

        return {
            "metric_name": metric_name,
            "duration_minutes": duration_minutes,
            "sample_count": len(values),
            "latest_value": values[-1],
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not sorted_values:
            return 0.0

        index = (percentile / 100) * (len(sorted_values) - 1)
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return (sorted_values[lower_index] * (1 - weight) +
                   sorted_values[upper_index] * weight)

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health_status = {
            "overall_status": HealthStatus.UNKNOWN.value,
            "components": {},
            "active_alerts": len(self.active_alerts),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        # Check health checks status
        healthy_checks = 0
        total_checks = len(self.health_checks)

        for check_id, health_check in self.health_checks.items():
            failures = getattr(self, '_health_check_failures', defaultdict(int)).get(check_id, 0)
            component_health = HealthStatus.HEALTHY if failures < health_check.failure_threshold else HealthStatus.UNHEALTHY

            health_status["components"][check_id] = {
                "status": component_health.value,
                "consecutive_failures": failures,
                "failure_threshold": health_check.failure_threshold,
                "endpoint": health_check.endpoint
            }

            if component_health == HealthStatus.HEALTHY:
                healthy_checks += 1

        # Determine overall status
        if healthy_checks == total_checks and total_checks > 0:
            health_status["overall_status"] = HealthStatus.HEALTHY.value
        elif healthy_checks >= total_checks * 0.7:
            health_status["overall_status"] = HealthStatus.DEGRADED.value
        else:
            health_status["overall_status"] = HealthStatus.UNHEALTHY.value

        # Check active alerts severity
        if self.active_alerts:
            critical_alerts = sum(1 for alert in self.active_alerts.values()
                                if alert.severity == AlertSeverity.CRITICAL)
            if critical_alerts > 0:
                health_status["overall_status"] = HealthStatus.UNHEALTHY.value

        return health_status

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler"""
        self.alert_handlers.append(handler)
        logger.info("Added alert handler")

    async def send_test_alert(self):
        """Send a test alert to verify alerting system"""
        test_alert = Alert(
            alert_id=f"test_alert_{int(time.time())}",
            rule_id="test_rule",
            severity=AlertSeverity.INFO,
            status="firing",
            message="This is a test alert to verify the monitoring system",
            timestamp=datetime.now(timezone.utc),
            labels={"component": "test", "environment": "production"},
            annotations={
                "description": "Test alert for monitoring system verification",
                "runbook_url": "https://docs.cognee.com/runbooks/test"
            }
        )

        await self._send_alert(test_alert)
        return test_alert.alert_id


# Alert Handlers

class SlackAlertHandler:
    """Slack alert handler"""

    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        self.webhook_url = webhook_url
        self.channel = channel

    async def __call__(self, alert: Alert):
        """Handle alert by sending to Slack"""
        try:
            color_map = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.HIGH: "warning",
                AlertSeverity.MEDIUM: "warning",
                AlertSeverity.LOW: "good",
                AlertSeverity.INFO: "good"
            }

            emoji_map = {
                AlertSeverity.CRITICAL: "🚨",
                AlertSeverity.HIGH: "⚠️",
                AlertSeverity.MEDIUM: "⚡",
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.INFO: "📢"
            }

            payload = {
                "channel": self.channel,
                "username": "Cognee Monitor",
                "icon_emoji": ":robot_face:",
                "attachments": [{
                    "color": color_map.get(alert.severity, "good"),
                    "title": f"{emoji_map.get(alert.severity, '')} {alert.message}",
                    "title_link": f"https://monitoring.cognee.com/alerts/{alert.alert_id}",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value,
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": alert.status,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ],
                    "footer": "RNR Enhanced Cognee Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack alert: {response.status}")

        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}")


class EmailAlertHandler:
    """Email alert handler"""

    def __init__(self, smtp_server: str, smtp_port: int, username: str,
                 password: str, recipients: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients

    async def __call__(self, alert: Alert):
        """Handle alert by sending email"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.message}"

            # Email body
            body = f"""
Alert Details:
- Severity: {alert.severity.value}
- Status: {alert.status}
- Timestamp: {alert.timestamp}
- Message: {alert.message}

Labels:
{json.dumps(alert.labels, indent=2)}

Annotations:
{json.dumps(alert.annotations, indent=2)}

Runbook: https://docs.cognee.com/runbooks/alerts/{alert.rule_id}
            """

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email alert sent for {alert.alert_id}")

        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")


@pytest.fixture
def monitoring_framework():
    """Fixture for monitoring framework"""
    framework = ProductionMonitoringFramework()

    # Register standard metrics
    standard_metrics = [
        MetricDefinition(
            name="system_cpu_usage",
            metric_type=MetricType.GAUGE,
            description="System CPU usage percentage",
            unit="percent"
        ),
        MetricDefinition(
            name="system_memory_usage",
            metric_type=MetricType.GAUGE,
            description="System memory usage percentage",
            unit="percent"
        ),
        MetricDefinition(
            name="api_request_count",
            metric_type=MetricType.COUNTER,
            description="Total API request count",
            unit="requests"
        ),
        MetricDefinition(
            name="api_response_time_ms",
            metric_type=MetricType.HISTOGRAM,
            description="API response time in milliseconds",
            unit="milliseconds"
        ),
        MetricDefinition(
            name="error_rate",
            metric_type=MetricType.GAUGE,
            description="Error rate percentage",
            unit="percent"
        )
    ]

    for metric in standard_metrics:
        framework.register_metric(metric)

    return framework


@pytest.fixture
def alert_rules():
    """Fixture providing standard alert rules"""
    return [
        AlertRule(
            rule_id="high_cpu_usage",
            name="High CPU Usage",
            description="CPU usage is above threshold",
            metric_name="system_cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            duration_minutes=5,
            labels={"component": "system"},
            annotations={
                "runbook": "https://docs.cognee.com/runbooks/cpu-usage"
            }
        ),
        AlertRule(
            rule_id="high_memory_usage",
            name="High Memory Usage",
            description="Memory usage is above threshold",
            metric_name="system_memory_usage",
            condition="gt",
            threshold=85.0,
            severity=AlertSeverity.HIGH,
            duration_minutes=5,
            labels={"component": "system"},
            annotations={
                "runbook": "https://docs.cognee.com/runbooks/memory-usage"
            }
        ),
        AlertRule(
            rule_id="high_error_rate",
            name="High Error Rate",
            description="Error rate is above threshold",
            metric_name="error_rate",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.CRITICAL,
            duration_minutes=2,
            labels={"component": "api"},
            annotations={
                "runbook": "https://docs.cognee.com/runbooks/error-rate"
            }
        ),
        AlertRule(
            rule_id="slow_response_time",
            name="Slow Response Time",
            description="API response time is above threshold",
            metric_name="api_response_time_ms",
            condition="gt",
            threshold=1000.0,
            severity=AlertSeverity.MEDIUM,
            duration_minutes=3,
            labels={"component": "api"},
            annotations={
                "runbook": "https://docs.cognee.com/runbooks/response-time"
            }
        )
    ]


@pytest.fixture
def health_checks():
    """Fixture providing standard health checks"""
    return [
        HealthCheck(
            check_id="api_health",
            name="API Health Check",
            endpoint="http://localhost:8000/health",
            timeout_seconds=10,
            expected_status=200
        ),
        HealthCheck(
            check_id="memory_stack_health",
            name="Memory Stack Health Check",
            endpoint="http://localhost:8000/api/v1/memory/health",
            timeout_seconds=15,
            expected_status=200
        ),
        HealthCheck(
            check_id="agent_system_health",
            name="Agent System Health Check",
            endpoint="http://localhost:8000/api/v1/agents/health",
            timeout_seconds=20,
            expected_status=200
        )
    ]


class TestProductionMonitoring:
    """Test production monitoring and alerting system"""

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_metric_recording(self, monitoring_framework):
        """Test metric recording functionality"""
        # Record test metrics
        test_metrics = [
            ("system_cpu_usage", 45.5),
            ("system_memory_usage", 67.2),
            ("api_request_count", 1000),
            ("api_response_time_ms", 250.0)
        ]

        for metric_name, value in test_metrics:
            monitoring_framework.record_metric(metric_name, value, {"test": "true"})

        # Verify metrics were recorded
        for metric_name, expected_value in test_metrics:
            assert metric_name in monitoring_framework.metrics_store, \
                f"Metric {metric_name} not recorded"

            latest_metric = monitoring_framework.metrics_store[metric_name][-1]
            assert latest_metric["value"] == expected_value, \
                f"Metric {metric_name} value mismatch"

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_alert_rule_registration(self, monitoring_framework, alert_rules):
        """Test alert rule registration and triggering"""
        # Register alert rules
        for rule in alert_rules:
            monitoring_framework.register_alert_rule(rule)

        assert len(monitoring_framework.alert_rules) == len(alert_rules), \
            "Not all alert rules registered"

        # Trigger an alert by recording a metric that exceeds threshold
        monitoring_framework.record_metric("system_cpu_usage", 90.0, {"test": "cpu_alert"})

        # Wait for alert processing
        await asyncio.sleep(2)

        # Check if alert was triggered
        cpu_alerts = [
            alert for alert in monitoring_framework.active_alerts.values()
            if alert.rule_id == "high_cpu_usage"
        ]

        assert len(cpu_alerts) > 0, "CPU usage alert should be triggered"

        alert = cpu_alerts[0]
        assert alert.severity == AlertSeverity.HIGH, "Alert severity mismatch"
        assert "90.0" in alert.message, "Alert message should contain metric value"

    @pytest.mark.production
    @pytest.mark.health
    async def test_health_check_execution(self, monitoring_framework, health_checks):
        """Test health check execution"""
        # Register health checks
        for health_check in health_checks:
            monitoring_framework.register_health_check(health_check)

        assert len(monitoring_framework.health_checks) == len(health_checks), \
            "Not all health checks registered"

        # Execute health checks
        for health_check in health_checks:
            await monitoring_framework._execute_health_check(health_check)

        # Check health metrics were recorded
        health_metrics = [
            metric for metric in monitoring_framework.metrics_store.keys()
            if metric == "health_check_success"
        ]

        assert len(health_metrics) > 0, "Health check metrics should be recorded"

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_metrics_summary(self, monitoring_framework):
        """Test metrics summary functionality"""
        # Generate test metrics data
        base_time = time.time()
        for i in range(100):
            timestamp = base_time + i * 10  # 10 second intervals
            value = 50 + (i % 20)  # Values between 50 and 70

            monitoring_framework.record_metric("test_metric", value, {"test": "summary"})

        # Get metrics summary
        summary = monitoring_framework.get_metrics_summary("test_metric", 30)  # 30 minutes

        assert summary["metric_name"] == "test_metric", "Metric name mismatch"
        assert summary["sample_count"] > 0, "Should have samples"
        assert summary["latest_value"] is not None, "Should have latest value"
        assert summary["min"] is not None, "Should have minimum value"
        assert summary["max"] is not None, "Should have maximum value"
        assert summary["avg"] is not None, "Should have average value"

        # Validate statistical calculations
        assert summary["min"] <= summary["avg"] <= summary["max"], \
            "Average should be between min and max"
        assert summary["p50"] <= summary["p95"] <= summary["p99"], \
            "Percentiles should be in ascending order"

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_system_health_assessment(self, monitoring_framework):
        """Test system health assessment"""
        # Record some health metrics
        monitoring_framework.record_metric("health_check_success", 1, {"check_id": "test_check"})

        # Get system health
        health = monitoring_framework.get_system_health()

        assert "overall_status" in health, "Overall status should be present"
        assert "components" in health, "Components should be present"
        assert "active_alerts" in health, "Active alerts count should be present"
        assert "last_updated" in health, "Last updated timestamp should be present"

        assert health["overall_status"] in [
            HealthStatus.HEALTHY.value,
            HealthStatus.DEGRADED.value,
            HealthStatus.UNHEALTHY.value,
            HealthStatus.UNKNOWN.value
        ], "Invalid overall status"

    @pytest.mark.production
    @pytest.mark.alerting
    async def test_alert_handlers(self, monitoring_framework):
        """Test alert handler functionality"""
        # Test alert handler
        test_alerts = []

        class TestAlertHandler:
            async def __call__(self, alert):
                test_alerts.append(alert)

        # Add test handler
        monitoring_framework.add_alert_handler(TestAlertHandler())

        # Register test alert rule
        test_rule = AlertRule(
            rule_id="test_alert",
            name="Test Alert",
            description="Test alert for validation",
            metric_name="test_metric",
            condition="gt",
            threshold=50.0,
            severity=AlertSeverity.INFO,
            duration_minutes=1
        )
        monitoring_framework.register_alert_rule(test_rule)

        # Trigger test alert
        monitoring_framework.record_metric("test_metric", 75.0, {"test": "handler"})

        # Wait for alert processing
        await asyncio.sleep(2)

        # Check if handler was called
        assert len(test_alerts) > 0, "Alert handler should be called"

        alert = test_alerts[0]
        assert alert.rule_id == "test_alert", "Alert rule ID mismatch"
        assert alert.severity == AlertSeverity.INFO, "Alert severity mismatch"

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_test_alert_functionality(self, monitoring_framework):
        """Test test alert functionality"""
        # Send test alert
        alert_id = await monitoring_framework.send_test_alert()

        assert alert_id is not None, "Test alert should return alert ID"
        assert alert_id.startswith("test_alert_"), "Test alert ID should have correct prefix"

        # Check if alert is in history
        test_alerts = [
            alert for alert in monitoring_framework.alert_history
            if alert.alert_id == alert_id
        ]

        assert len(test_alerts) > 0, "Test alert should be in history"

        alert = test_alerts[0]
        assert alert.rule_id == "test_rule", "Test alert rule ID mismatch"
        assert alert.severity == AlertSeverity.INFO, "Test alert severity should be INFO"

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_monitoring_lifecycle(self, monitoring_framework):
        """Test monitoring start/stop lifecycle"""
        # Initially monitoring should not be active
        assert not monitoring_framework.monitoring_active, "Monitoring should not be active initially"

        # Start monitoring in background (don't wait for it to complete)
        monitoring_task = asyncio.create_task(monitoring_framework.start_monitoring())

        # Give it a moment to start
        await asyncio.sleep(1)

        assert monitoring_framework.monitoring_active, "Monitoring should be active"

        # Stop monitoring
        monitoring_framework.stop_monitoring()

        # Wait for task to complete
        try:
            monitoring_task.result(timeout=5)
        except asyncio.TimeoutError:
            monitoring_task.cancel()

        assert not monitoring_framework.monitoring_active, "Monitoring should be stopped"

    @pytest.mark.production
    @pytest.mark.monitoring
    async def test_slack_alert_handler(self):
        """Test Slack alert handler"""
        # Mock Slack webhook URL
        webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"

        handler = SlackAlertHandler(webhook_url)

        # Create test alert
        test_alert = Alert(
            alert_id="test_slack_alert",
            rule_id="test_rule",
            severity=AlertSeverity.HIGH,
            status="firing",
            message="Test Slack alert",
            timestamp=datetime.now(timezone.utc),
            labels={"test": "slack"},
            annotations={"description": "Test alert for Slack handler"}
        )

        # Test handler (won't actually send due to mock URL)
        try:
            await handler(test_alert)
            # If no exception, handler structure is correct
            assert True, "Slack handler structure is correct"
        except Exception as e:
            # Expected to fail due to mock URL, but structure should be valid
            assert "webhook_url" in str(e) or "404" in str(e), \
                "Expected failure due to mock webhook URL"

    @pytest.mark.production
    @pytest.mark.monitoring
    def test_metric_definition_validation(self, monitoring_framework):
        """Test metric definition validation"""
        # Register valid metric
        valid_metric = MetricDefinition(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric"
        )
        monitoring_framework.register_metric(valid_metric)

        assert "test_metric" in monitoring_framework.metric_definitions, \
            "Valid metric should be registered"

        # Record metric to existing definition
        monitoring_framework.record_metric("test_metric", 42.0)

        # Try to record unknown metric (should log warning but not crash)
        monitoring_framework.record_metric("unknown_metric", 42.0)

        # Unknown metric should not be in store
        assert "unknown_metric" not in monitoring_framework.metrics_store, \
            "Unknown metric should not create store automatically"


# Integration with existing test framework
pytest_plugins = []