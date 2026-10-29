"""
Production Performance Baseline Establishment
Implements comprehensive performance baseline creation and SLA management
"""

import pytest

import os
import json
import time
import asyncio
import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import csv

import aiohttp
import psutil
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    DATABASE_PERFORMANCE = "database_performance"
    CACHE_PERFORMANCE = "cache_performance"


class SLATier(Enum):
    """SLA tiers"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    metric_id: str
    metric_type: MetricType
    component: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@dataclass
class SLARequirement:
    """SLA requirement definition"""
    requirement_id: str
    metric_type: MetricType
    tier: SLATier
    target_value: float
    unit: str
    measurement_period: str  # e.g., "24h", "7d", "30d"
    consequence_breach: str
    monitoring_window: str = "5m"


@dataclass
class PerformanceBaseline:
    """Performance baseline for a component"""
    baseline_id: str
    component_name: str
    component_type: str
    metric_type: MetricType
    baseline_value: float
    unit: str
    percentile_50: float
    percentile_90: float
    percentile_95: float
    percentile_99: float
    standard_deviation: float
    sample_count: int
    measurement_period_hours: int
    creation_date: datetime
    last_updated: datetime
    is_active: bool = True


@dataclass
class PerformanceReport:
    """Performance analysis report"""
    report_id: str
    baseline_id: str
    analysis_period_start: datetime
    analysis_period_end: datetime
    current_performance: Dict[str, float]
    baseline_comparison: Dict[str, float]
    sla_compliance: Dict[str, bool]
    performance_trend: str  # "improving", "stable", "degrading"
    recommendations: List[str]
    generated_at: datetime


class PerformanceMonitor:
    """Real-time performance monitoring"""

    def __init__(self):
        self.metrics_history: List[PerformanceMetric] = []
        self.monitoring_active = False
        self.monitoring_interval = 5.0  # seconds

    async def start_monitoring(self, duration_minutes: int = 60) -> List[PerformanceMetric]:
        """Start performance monitoring for specified duration"""
        logger.info(f"Starting performance monitoring for {duration_minutes} minutes")

        self.monitoring_active = True
        self.metrics_history.clear()

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        monitoring_tasks = [
            self._monitor_system_metrics(),
            self._monitor_application_metrics(),
            self._monitor_database_metrics(),
            self._monitor_cache_metrics()
        ]

        # Run monitoring tasks concurrently
        await asyncio.gather(*monitoring_tasks)

        # Wait for monitoring duration
        while time.time() < end_time and self.monitoring_active:
            await asyncio.sleep(1)

        self.monitoring_active = False

        logger.info(f"Collected {len(self.metrics_history)} performance metrics")
        return self.metrics_history

    async def _monitor_system_metrics(self):
        """Monitor system-level metrics"""
        while self.monitoring_active:
            timestamp = datetime.now(timezone.utc)

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_metric = PerformanceMetric(
                metric_id=f"cpu_{int(timestamp.timestamp())}",
                metric_type=MetricType.CPU_UTILIZATION,
                component="system",
                value=cpu_percent,
                unit="percent",
                timestamp=timestamp,
                tags={"metric": "cpu_utilization"},
                threshold_warning=75.0,
                threshold_critical=90.0
            )

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_metric = PerformanceMetric(
                metric_id=f"memory_{int(timestamp.timestamp())}",
                metric_type=MetricType.MEMORY_UTILIZATION,
                component="system",
                value=memory.percent,
                unit="percent",
                timestamp=timestamp,
                tags={"metric": "memory_utilization"},
                threshold_warning=80.0,
                threshold_critical=95.0
            )

            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                disk_read_metric = PerformanceMetric(
                    metric_id=f"disk_read_{int(timestamp.timestamp())}",
                    metric_type=MetricType.DISK_IO,
                    component="system",
                    value=disk_io.read_bytes / 1024 / 1024,  # MB/s
                    unit="MB/s",
                    timestamp=timestamp,
                    tags={"metric": "disk_read", "operation": "read"}
                )

                disk_write_metric = PerformanceMetric(
                    metric_id=f"disk_write_{int(timestamp.timestamp())}",
                    metric_type=MetricType.DISK_IO,
                    component="system",
                    value=disk_io.write_bytes / 1024 / 1024,  # MB/s
                    unit="MB/s",
                    timestamp=timestamp,
                    tags={"metric": "disk_write", "operation": "write"}
                )

                self.metrics_history.extend([disk_read_metric, disk_write_metric])

            # Network I/O metrics
            network_io = psutil.net_io_counters()
            if network_io:
                network_sent_metric = PerformanceMetric(
                    metric_id=f"net_sent_{int(timestamp.timestamp())}",
                    metric_type=MetricType.NETWORK_IO,
                    component="system",
                    value=network_io.bytes_sent / 1024 / 1024,  # MB/s
                    unit="MB/s",
                    timestamp=timestamp,
                    tags={"metric": "network_sent", "direction": "outbound"}
                )

                network_recv_metric = PerformanceMetric(
                    metric_id=f"net_recv_{int(timestamp.timestamp())}",
                    metric_type=MetricType.NETWORK_IO,
                    component="system",
                    value=network_io.bytes_recv / 1024 / 1024,  # MB/s
                    unit="MB/s",
                    timestamp=timestamp,
                    tags={"metric": "network_recv", "direction": "inbound"}
                )

                self.metrics_history.extend([network_sent_metric, network_recv_metric])

            self.metrics_history.extend([cpu_metric, memory_metric])
            await asyncio.sleep(self.monitoring_interval)

    async def _monitor_application_metrics(self):
        """Monitor application-level metrics"""
        async with aiohttp.ClientSession() as session:
            while self.monitoring_active:
                try:
                    timestamp = datetime.now(timezone.utc)

                    # Monitor API response time
                    start_time = time.time()
                    async with session.get("http://localhost:8000/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                        await response.text()
                        response_time = (time.time() - start_time) * 1000  # milliseconds

                        response_time_metric = PerformanceMetric(
                            metric_id=f"api_response_{int(timestamp.timestamp())}",
                            metric_type=MetricType.RESPONSE_TIME,
                            component="api",
                            value=response_time,
                            unit="ms",
                            timestamp=timestamp,
                            tags={"endpoint": "/health", "method": "GET"},
                            threshold_warning=500.0,
                            threshold_critical=2000.0
                        )

                        availability_metric = PerformanceMetric(
                            metric_id=f"api_availability_{int(timestamp.timestamp())}",
                            metric_type=MetricType.AVAILABILITY,
                            component="api",
                            value=100.0 if response.status == 200 else 0.0,
                            unit="percent",
                            timestamp=timestamp,
                            tags={"endpoint": "/health"},
                            threshold_warning=99.0,
                            threshold_critical=95.0
                        )

                        self.metrics_history.extend([response_time_metric, availability_metric])

                except Exception as e:
                    logger.warning(f"Failed to monitor application metrics: {e}")

                await asyncio.sleep(self.monitoring_interval)

    async def _monitor_database_metrics(self):
        """Monitor database performance metrics"""
        while self.monitoring_active:
            try:
                timestamp = datetime.now(timezone.utc)

                # Simulate database performance metrics
                # In production, connect to actual database and collect metrics
                db_metrics = {
                    "query_time_avg": 45.2,  # ms
                    "query_time_p95": 120.5,  # ms
                    "connections_active": 25,
                    "cache_hit_ratio": 0.85
                }

                # Query time metric
                query_time_metric = PerformanceMetric(
                    metric_id=f"db_query_time_{int(timestamp.timestamp())}",
                    metric_type=MetricType.DATABASE_PERFORMANCE,
                    component="database",
                    value=db_metrics["query_time_avg"],
                    unit="ms",
                    timestamp=timestamp,
                    tags={"metric": "query_time_avg"},
                    threshold_warning=100.0,
                    threshold_critical=500.0
                )

                # Connection metric
                connection_metric = PerformanceMetric(
                    metric_id=f"db_connections_{int(timestamp.timestamp())}",
                    metric_type=MetricType.DATABASE_PERFORMANCE,
                    component="database",
                    value=db_metrics["connections_active"],
                    unit="count",
                    timestamp=timestamp,
                    tags={"metric": "connections_active"},
                    threshold_warning=80.0,
                    threshold_critical=100.0
                )

                # Cache hit ratio metric
                cache_ratio_metric = PerformanceMetric(
                    metric_id=f"db_cache_hit_{int(timestamp.timestamp())}",
                    metric_type=MetricType.DATABASE_PERFORMANCE,
                    component="database",
                    value=db_metrics["cache_hit_ratio"] * 100,  # Convert to percentage
                    unit="percent",
                    timestamp=timestamp,
                    tags={"metric": "cache_hit_ratio"},
                    threshold_warning=80.0,
                    threshold_critical=70.0
                )

                self.metrics_history.extend([query_time_metric, connection_metric, cache_ratio_metric])

            except Exception as e:
                logger.warning(f"Failed to monitor database metrics: {e}")

            await asyncio.sleep(self.monitoring_interval)

    async def _monitor_cache_metrics(self):
        """Monitor cache performance metrics"""
        while self.monitoring_active:
            try:
                timestamp = datetime.now(timezone.utc)

                # Simulate cache performance metrics
                cache_metrics = {
                    "hit_ratio": 0.78,
                    "ops_per_second": 5000,
                    "memory_usage_mb": 512
                }

                # Hit ratio metric
                hit_ratio_metric = PerformanceMetric(
                    metric_id=f"cache_hit_ratio_{int(timestamp.timestamp())}",
                    metric_type=MetricType.CACHE_PERFORMANCE,
                    component="cache",
                    value=cache_metrics["hit_ratio"] * 100,  # Convert to percentage
                    unit="percent",
                    timestamp=timestamp,
                    tags={"metric": "hit_ratio"},
                    threshold_warning=75.0,
                    threshold_critical=60.0
                )

                # Operations per second metric
                ops_metric = PerformanceMetric(
                    metric_id=f"cache_ops_{int(timestamp.timestamp())}",
                    metric_type=MetricType.CACHE_PERFORMANCE,
                    component="cache",
                    value=cache_metrics["ops_per_second"],
                    unit="ops/s",
                    timestamp=timestamp,
                    tags={"metric": "operations_per_second"},
                    threshold_warning=1000.0,
                    threshold_critical=500.0
                )

                # Memory usage metric
                memory_metric = PerformanceMetric(
                    metric_id=f"cache_memory_{int(timestamp.timestamp())}",
                    metric_type=MetricType.CACHE_PERFORMANCE,
                    component="cache",
                    value=cache_metrics["memory_usage_mb"],
                    unit="MB",
                    timestamp=timestamp,
                    tags={"metric": "memory_usage"},
                    threshold_warning=1024.0,  # 1GB
                    threshold_critical=2048.0  # 2GB
                )

                self.metrics_history.extend([hit_ratio_metric, ops_metric, memory_metric])

            except Exception as e:
                logger.warning(f"Failed to monitor cache metrics: {e}")

            await asyncio.sleep(self.monitoring_interval)

    def get_metrics_summary(self, metric_type: MetricType, component: str = None) -> Dict[str, Any]:
        """Get summary statistics for specific metrics"""
        filtered_metrics = [
            m for m in self.metrics_history
            if m.metric_type == metric_type and (component is None or m.component == component)
        ]

        if not filtered_metrics:
            return {"error": "No metrics found for the specified criteria"}

        values = [m.value for m in filtered_metrics]

        summary = {
            "metric_type": metric_type.value,
            "component": component or "all",
            "sample_count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "percentile_50": np.percentile(values, 50),
            "percentile_90": np.percentile(values, 90),
            "percentile_95": np.percentile(values, 95),
            "percentile_99": np.percentile(values, 99),
            "time_range": {
                "start": min(m.timestamp for m in filtered_metrics).isoformat(),
                "end": max(m.timestamp for m in filtered_metrics).isoformat()
            }
        }

        return summary


class BaselineManager:
    """Manages performance baselines"""

    def __init__(self, database_path: str = "performance_baselines.db"):
        self.database_path = database_path
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self._initialize_database()

    def _initialize_database(self):
        """Initialize SQLite database for baselines"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baselines (
                baseline_id TEXT PRIMARY KEY,
                component_name TEXT NOT NULL,
                component_type TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                baseline_value REAL NOT NULL,
                unit TEXT NOT NULL,
                percentile_50 REAL NOT NULL,
                percentile_90 REAL NOT NULL,
                percentile_95 REAL NOT NULL,
                percentile_99 REAL NOT NULL,
                standard_deviation REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                measurement_period_hours INTEGER NOT NULL,
                creation_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        ''')

        conn.commit()
        conn.close()

    def create_baseline(
        self,
        component_name: str,
        component_type: str,
        metric_type: MetricType,
        metrics: List[PerformanceMetric],
        measurement_period_hours: int
    ) -> PerformanceBaseline:
        """Create performance baseline from metrics"""
        if not metrics:
            raise ValueError("No metrics provided for baseline creation")

        values = [m.value for m in metrics]
        baseline_id = f"{component_name}_{metric_type.value}_{int(time.time())}"

        baseline = PerformanceBaseline(
            baseline_id=baseline_id,
            component_name=component_name,
            component_type=component_type,
            metric_type=metric_type,
            baseline_value=statistics.mean(values),
            unit=metrics[0].unit,
            percentile_50=np.percentile(values, 50),
            percentile_90=np.percentile(values, 90),
            percentile_95=np.percentile(values, 95),
            percentile_99=np.percentile(values, 99),
            standard_deviation=statistics.stdev(values) if len(values) > 1 else 0,
            sample_count=len(values),
            measurement_period_hours=measurement_period_hours,
            creation_date=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )

        # Store in memory
        self.baselines[baseline_id] = baseline

        # Store in database
        self._save_baseline_to_db(baseline)

        logger.info(f"Created baseline {baseline_id} for {component_name} {metric_type.value}")
        return baseline

    def _save_baseline_to_db(self, baseline: PerformanceBaseline):
        """Save baseline to database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO baselines (
                baseline_id, component_name, component_type, metric_type,
                baseline_value, unit, percentile_50, percentile_90, percentile_95, percentile_99,
                standard_deviation, sample_count, measurement_period_hours,
                creation_date, last_updated, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            baseline.baseline_id,
            baseline.component_name,
            baseline.component_type,
            baseline.metric_type.value,
            baseline.baseline_value,
            baseline.unit,
            baseline.percentile_50,
            baseline.percentile_90,
            baseline.percentile_95,
            baseline.percentile_99,
            baseline.standard_deviation,
            baseline.sample_count,
            baseline.measurement_period_hours,
            baseline.creation_date.isoformat(),
            baseline.last_updated.isoformat(),
            baseline.is_active
        ))

        conn.commit()
        conn.close()

    def get_baseline(self, component_name: str, metric_type: MetricType) -> Optional[PerformanceBaseline]:
        """Get active baseline for component and metric type"""
        # Check in-memory first
        for baseline in self.baselines.values():
            if (baseline.component_name == component_name and
                baseline.metric_type == metric_type and
                baseline.is_active):
                return baseline

        # Check database
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM baselines
            WHERE component_name = ? AND metric_type = ? AND is_active = 1
            ORDER BY last_updated DESC
            LIMIT 1
        ''', (component_name, metric_type.value))

        row = cursor.fetchone()
        conn.close()

        if row:
            return PerformanceBaseline(
                baseline_id=row[0],
                component_name=row[1],
                component_type=row[2],
                metric_type=MetricType(row[3]),
                baseline_value=row[4],
                unit=row[5],
                percentile_50=row[6],
                percentile_90=row[7],
                percentile_95=row[8],
                percentile_99=row[9],
                standard_deviation=row[10],
                sample_count=row[11],
                measurement_period_hours=row[12],
                creation_date=datetime.fromisoformat(row[13]),
                last_updated=datetime.fromisoformat(row[14]),
                is_active=bool(row[15])
            )

        return None

    def compare_against_baseline(
        self,
        component_name: str,
        metric_type: MetricType,
        current_value: float
    ) -> Dict[str, Any]:
        """Compare current value against baseline"""
        baseline = self.get_baseline(component_name, metric_type)
        if not baseline:
            return {"error": "No baseline found for comparison"}

        deviation_from_baseline = ((current_value - baseline.baseline_value) / baseline.baseline_value) * 100

        # Determine performance level
        if metric_type in [MetricType.RESPONSE_TIME, MetricType.CPU_UTILIZATION, MetricType.MEMORY_UTILIZATION]:
            # Lower is better for these metrics
            if current_value <= baseline.percentile_50:
                performance_level = "excellent"
            elif current_value <= baseline.percentile_90:
                performance_level = "good"
            elif current_value <= baseline.percentile_95:
                performance_level = "acceptable"
            else:
                performance_level = "poor"
        else:
            # Higher is better for these metrics
            if current_value >= baseline.percentile_95:
                performance_level = "excellent"
            elif current_value >= baseline.percentile_90:
                performance_level = "good"
            elif current_value >= baseline.percentile_50:
                performance_level = "acceptable"
            else:
                performance_level = "poor"

        return {
            "component": component_name,
            "metric_type": metric_type.value,
            "current_value": current_value,
            "baseline_value": baseline.baseline_value,
            "deviation_percent": deviation_from_baseline,
            "performance_level": performance_level,
            "percentile_comparison": {
                "p50": baseline.percentile_50,
                "p90": baseline.percentile_90,
                "p95": baseline.percentile_95,
                "p99": baseline.percentile_99
            },
            "baseline_age_days": (datetime.now(timezone.utc) - baseline.last_updated).days
        }


class SLAManager:
    """Manages SLA requirements and compliance"""

    def __init__(self):
        self.sla_requirements: List[SLARequirement] = []
        self.compliance_history: List[Dict[str, Any]] = []

    def create_default_sla_requirements(self) -> List[SLARequirement]:
        """Create default SLA requirements for all tiers"""
        requirements = []

        # Basic tier SLAs
        requirements.extend([
            SLARequirement(
                requirement_id="basic_availability",
                metric_type=MetricType.AVAILABILITY,
                tier=SLATier.BASIC,
                target_value=99.0,
                unit="percent",
                measurement_period="30d",
                consequence_breach="Service credit for downtime"
            ),
            SLARequirement(
                requirement_id="basic_response_time",
                metric_type=MetricType.RESPONSE_TIME,
                tier=SLATier.BASIC,
                target_value=1000.0,
                unit="ms",
                measurement_period="24h",
                consequence_breach="Performance investigation"
            )
        ])

        # Standard tier SLAs
        requirements.extend([
            SLARequirement(
                requirement_id="standard_availability",
                metric_type=MetricType.AVAILABILITY,
                tier=SLATier.STANDARD,
                target_value=99.5,
                unit="percent",
                measurement_period="30d",
                consequence_breach="Service credit for downtime"
            ),
            SLARequirement(
                requirement_id="standard_response_time",
                metric_type=MetricType.RESPONSE_TIME,
                tier=SLATier.STANDARD,
                target_value=500.0,
                unit="ms",
                measurement_period="24h",
                consequence_breach="Performance investigation"
            ),
            SLARequirement(
                requirement_id="standard_error_rate",
                metric_type=MetricType.ERROR_RATE,
                tier=SLATier.STANDARD,
                target_value=1.0,
                unit="percent",
                measurement_period="24h",
                consequence_breach="Error rate investigation"
            )
        ])

        # Premium tier SLAs
        requirements.extend([
            SLARequirement(
                requirement_id="premium_availability",
                metric_type=MetricType.AVAILABILITY,
                tier=SLATier.PREMIUM,
                target_value=99.9,
                unit="percent",
                measurement_period="30d",
                consequence_breach="Service credit for downtime"
            ),
            SLARequirement(
                requirement_id="premium_response_time",
                metric_type=MetricType.RESPONSE_TIME,
                tier=SLATier.PREMIUM,
                target_value=200.0,
                unit="ms",
                measurement_period="24h",
                consequence_breach="Performance investigation"
            ),
            SLARequirement(
                requirement_id="premium_error_rate",
                metric_type=MetricType.ERROR_RATE,
                tier=SLATier.PREMIUM,
                target_value=0.5,
                unit="percent",
                measurement_period="24h",
                consequence_breach="Error rate investigation"
            )
        ])

        # Enterprise tier SLAs
        requirements.extend([
            SLARequirement(
                requirement_id="enterprise_availability",
                metric_type=MetricType.AVAILABILITY,
                tier=SLATier.ENTERPRISE,
                target_value=99.95,
                unit="percent",
                measurement_period="30d",
                consequence_breach="Service credit for downtime"
            ),
            SLARequirement(
                requirement_id="enterprise_response_time",
                metric_type=MetricType.RESPONSE_TIME,
                tier=SLATier.ENTERPRISE,
                target_value=100.0,
                unit="ms",
                measurement_period="24h",
                consequence_breach="Performance investigation"
            ),
            SLARequirement(
                requirement_id="enterprise_error_rate",
                metric_type=MetricType.ERROR_RATE,
                tier=SLATier.ENTERPRISE,
                target_value=0.1,
                unit="percent",
                measurement_period="24h",
                consequence_breach="Error rate investigation"
            )
        ])

        self.sla_requirements = requirements
        return requirements

    def check_sla_compliance(
        self,
        tier: SLATier,
        metrics: Dict[MetricType, float]
    ) -> Dict[str, Any]:
        """Check SLA compliance for specified tier"""
        tier_requirements = [r for r in self.sla_requirements if r.tier == tier]

        compliance_results = {}
        overall_compliant = True

        for requirement in tier_requirements:
            metric_value = metrics.get(requirement.metric_type)
            if metric_value is None:
                compliance_results[requirement.requirement_id] = {
                    "compliant": False,
                    "reason": "Metric not available",
                    "target": requirement.target_value,
                    "actual": None
                }
                overall_compliant = False
                continue

            # Check compliance based on metric type
            if requirement.metric_type in [MetricType.AVAILABILITY, MetricType.CACHE_PERFORMANCE]:
                # Higher is better
                compliant = metric_value >= requirement.target_value
            else:
                # Lower is better
                compliant = metric_value <= requirement.target_value

            compliance_results[requirement.requirement_id] = {
                "compliant": compliant,
                "target": requirement.target_value,
                "actual": metric_value,
                "deviation": ((metric_value - requirement.target_value) / requirement.target_value) * 100,
                "consequence": requirement.consequence_breach if not compliant else None
            }

            if not compliant:
                overall_compliant = False

        compliance_percentage = (
            sum(1 for result in compliance_results.values() if result["compliant"]) /
            len(compliance_results) * 100
        ) if compliance_results else 0

        return {
            "tier": tier.value,
            "overall_compliant": overall_compliant,
            "compliance_percentage": compliance_percentage,
            "requirement_compliance": compliance_results,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    def get_sla_dashboard(self, tier: SLATier) -> Dict[str, Any]:
        """Get SLA dashboard data"""
        tier_requirements = [r for r in self.sla_requirements if r.tier == tier]

        dashboard = {
            "tier": tier.value,
            "total_requirements": len(tier_requirements),
            "requirements": []
        }

        for requirement in tier_requirements:
            # Get recent compliance history for this requirement
            recent_compliance = [
                entry for entry in self.compliance_history[-10:]  # Last 10 entries
                if entry.get("requirement_id") == requirement.requirement_id
            ]

            dashboard["requirements"].append({
                "requirement_id": requirement.requirement_id,
                "metric_type": requirement.metric_type.value,
                "target_value": requirement.target_value,
                "unit": requirement.unit,
                "measurement_period": requirement.measurement_period,
                "consequence_breach": requirement.consequence_breach,
                "recent_compliance_percentage": (
                    sum(1 for entry in recent_compliance if entry.get("compliant", False)) /
                    len(recent_compliance) * 100
                ) if recent_compliance else None
            })

        return dashboard


class PerformanceBaselineSystem:
    """Complete performance baseline establishment system"""

    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.baseline_manager = BaselineManager()
        self.sla_manager = SLAManager()
        self.performance_reports: List[PerformanceReport] = []

    async def establish_performance_baselines(self, duration_minutes: int = 120) -> Dict[str, Any]:
        """Establish comprehensive performance baselines"""
        logger.info("Starting performance baseline establishment")

        # Initialize SLA requirements
        sla_requirements = self.sla_manager.create_default_sla_requirements()

        # Start performance monitoring
        logger.info(f"Collecting performance metrics for {duration_minutes} minutes...")
        metrics = await self.monitor.start_monitoring(duration_minutes)

        # Create baselines for different components and metric types
        baselines_created = {}
        components = set(m.component for m in metrics)
        metric_types = set(m.metric_type for m in metrics)

        for component in components:
            component_baselines = {}
            for metric_type in metric_types:
                component_metrics = [
                    m for m in metrics
                    if m.component == component and m.metric_type == metric_type
                ]

                if len(component_metrics) >= 10:  # Minimum samples for baseline
                    try:
                        baseline = self.baseline_manager.create_baseline(
                            component_name=component,
                            component_type="service",
                            metric_type=metric_type,
                            metrics=component_metrics,
                            measurement_period_hours=duration_minutes / 60
                        )
                        component_baselines[metric_type.value] = baseline.baseline_id
                    except Exception as e:
                        logger.warning(f"Failed to create baseline for {component} {metric_type.value}: {e}")

            if component_baselines:
                baselines_created[component] = component_baselines

        # Generate baseline establishment report
        report = {
            "baseline_establishment_id": f"baseline_{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "monitoring_duration_minutes": duration_minutes,
            "total_metrics_collected": len(metrics),
            "components_monitored": len(components),
            "metric_types_monitored": len(metric_types),
            "baselines_created": baselines_created,
            "sla_requirements_defined": len(sla_requirements),
            "sla_tiers_configured": list(set(r.tier for r in sla_requirements)),
            "monitoring_summary": self._generate_monitoring_summary(metrics),
            "next_steps": [
                "Monitor performance against established baselines",
                "Review SLA compliance regularly",
                "Update baselines quarterly or after major changes",
                "Investigate any significant performance deviations"
            ]
        }

        return report

    def _generate_monitoring_summary(self, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """Generate monitoring summary statistics"""
        summary = {
            "metrics_by_type": {},
            "metrics_by_component": {},
            "monitoring_period": {
                "start": min(m.timestamp for m in metrics).isoformat(),
                "end": max(m.timestamp for m in metrics).isoformat(),
                "duration_hours": (
                    max(m.timestamp for m in metrics) - min(m.timestamp for m in metrics)
                ).total_seconds() / 3600
            }
        }

        # Group metrics by type
        for metric_type in set(m.metric_type for m in metrics):
            type_metrics = [m for m in metrics if m.metric_type == metric_type]
            values = [m.value for m in type_metrics]

            summary["metrics_by_type"][metric_type.value] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "min": min(values),
                "max": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0
            }

        # Group metrics by component
        for component in set(m.component for m in metrics):
            component_metrics = [m for m in metrics if m.component == component]
            summary["metrics_by_component"][component] = {
                "total_metrics": len(component_metrics),
                "metric_types": list(set(m.metric_type.value for m in component_metrics))
            }

        return summary

    async def generate_performance_report(
        self,
        component_name: str,
        metric_types: List[MetricType],
        analysis_period_hours: int = 24
    ) -> PerformanceReport:
        """Generate comprehensive performance analysis report"""
        report_id = f"perf_report_{component_name}_{int(time.time())}"

        # Get recent metrics
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=analysis_period_hours)
        recent_metrics = [
            m for m in self.monitor.metrics_history
            if (m.component == component_name and
                m.metric_type in metric_types and
                m.timestamp >= cutoff_time)
        ]

        if not recent_metrics:
            raise ValueError(f"No recent metrics found for {component_name}")

        # Calculate current performance
        current_performance = {}
        baseline_comparison = {}
        sla_compliance = {}

        for metric_type in metric_types:
            type_metrics = [m for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                values = [m.value for m in type_metrics]
                current_performance[metric_type.value] = statistics.mean(values)

                # Compare with baseline
                baseline = self.baseline_manager.get_baseline(component_name, metric_type)
                if baseline:
                    comparison = self.baseline_manager.compare_against_baseline(
                        component_name, metric_type, current_performance[metric_type.value]
                    )
                    baseline_comparison[metric_type.value] = comparison

        # Check SLA compliance (using Standard tier as default)
        if current_performance:
            metric_type_map = {
                key: MetricType(key) for key in current_performance.keys()
            }
            sla_results = self.sla_manager.check_sla_compliance(SLATier.STANDARD, metric_type_map)
            sla_compliance = sla_results["requirement_compliance"]

        # Determine performance trend
        performance_trend = self._analyze_performance_trend(recent_metrics)

        # Generate recommendations
        recommendations = self._generate_performance_recommendations(
            baseline_comparison, sla_compliance, performance_trend
        )

        report = PerformanceReport(
            report_id=report_id,
            baseline_id=f"baseline_{component_name}",
            analysis_period_start=cutoff_time,
            analysis_period_end=datetime.now(timezone.utc),
            current_performance=current_performance,
            baseline_comparison=baseline_comparison,
            sla_compliance=sla_compliance,
            performance_trend=performance_trend,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc)
        )

        self.performance_reports.append(report)
        return report

    def _analyze_performance_trend(self, metrics: List[PerformanceMetric]) -> str:
        """Analyze performance trend from metrics"""
        if len(metrics) < 10:
            return "insufficient_data"

        # Sort metrics by timestamp
        sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)

        # Split into two halves
        mid_point = len(sorted_metrics) // 2
        first_half = sorted_metrics[:mid_point]
        second_half = sorted_metrics[mid_point:]

        # Compare averages
        first_avg = statistics.mean(m.value for m in first_half)
        second_avg = statistics.mean(m.value for m in second_half)

        change_percent = ((second_avg - first_avg) / first_avg) * 100

        # Determine trend based on metric type
        metric_type = sorted_metrics[0].metric_type
        if metric_type in [MetricType.RESPONSE_TIME, MetricType.CPU_UTILIZATION, MetricType.MEMORY_UTILIZATION]:
            # Lower is better
            if change_percent < -5:
                return "improving"
            elif change_percent > 5:
                return "degrading"
            else:
                return "stable"
        else:
            # Higher is better
            if change_percent > 5:
                return "improving"
            elif change_percent < -5:
                return "degrading"
            else:
                return "stable"

    def _generate_performance_recommendations(
        self,
        baseline_comparison: Dict[str, Any],
        sla_compliance: Dict[str, Any],
        performance_trend: str
    ) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []

        # Baseline comparison recommendations
        for metric_name, comparison in baseline_comparison.items():
            if comparison.get("performance_level") == "poor":
                recommendations.append(
                    f"Immediate attention required for {metric_name}: "
                    f"Current performance is significantly worse than baseline"
                )
            elif comparison.get("performance_level") == "acceptable":
                recommendations.append(
                    f"Monitor {metric_name}: Performance is acceptable but could be optimized"
                )

        # SLA compliance recommendations
        for requirement_id, compliance in sla_compliance.items():
            if not compliance.get("compliant", True):
                recommendations.append(
                    f"SLA breach risk for {requirement_id}: "
                    f"Current performance may not meet SLA requirements"
                )

        # Trend-based recommendations
        if performance_trend == "degrading":
            recommendations.append(
                "Performance trend is degrading: Investigate root causes and implement optimizations"
            )
        elif performance_trend == "improving":
            recommendations.append(
                "Performance trend is improving: Continue current optimization efforts"
            )
        elif performance_trend == "stable":
            recommendations.append(
                "Performance is stable: Consider proactive optimizations for better efficiency"
            )

        # General recommendations
        recommendations.extend([
            "Review resource utilization and scaling policies",
            "Optimize database queries and caching strategies",
            "Monitor application errors and implement fixes",
            "Consider A/B testing for performance improvements"
        ])

        return recommendations[:10]  # Limit to top 10 recommendations

    def export_baselines_to_csv(self, output_path: str):
        """Export baselines to CSV file"""
        baselines_data = []
        for baseline in self.baseline_manager.baselines.values():
            baselines_data.append({
                "baseline_id": baseline.baseline_id,
                "component_name": baseline.component_name,
                "component_type": baseline.component_type,
                "metric_type": baseline.metric_type.value,
                "baseline_value": baseline.baseline_value,
                "unit": baseline.unit,
                "percentile_50": baseline.percentile_50,
                "percentile_90": baseline.percentile_90,
                "percentile_95": baseline.percentile_95,
                "percentile_99": baseline.percentile_99,
                "standard_deviation": baseline.standard_deviation,
                "sample_count": baseline.sample_count,
                "measurement_period_hours": baseline.measurement_period_hours,
                "creation_date": baseline.creation_date.isoformat(),
                "last_updated": baseline.last_updated.isoformat(),
                "is_active": baseline.is_active
            })

        df = pd.DataFrame(baselines_data)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(baselines_data)} baselines to {output_path}")

    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard"""
        dashboard = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_baselines": len(self.baseline_manager.baselines),
            "total_reports": len(self.performance_reports),
            "recent_reports": [],
            "baseline_summary": {},
            "sla_dashboard": {},
            "performance_alerts": []
        }

        # Recent reports
        dashboard["recent_reports"] = [
            {
                "report_id": report.report_id,
                "generated_at": report.generated_at.isoformat(),
                "performance_trend": report.performance_trend,
                "recommendations_count": len(report.recommendations)
            }
            for report in sorted(self.performance_reports, key=lambda r: r.generated_at, reverse=True)[:5]
        ]

        # Baseline summary by component
        component_summary = {}
        for baseline in self.baseline_manager.baselines.values():
            if baseline.component_name not in component_summary:
                component_summary[baseline.component_name] = {
                    "baselines_count": 0,
                    "metric_types": []
                }
            component_summary[baseline.component_name]["baselines_count"] += 1
            if baseline.metric_type.value not in component_summary[baseline.component_name]["metric_types"]:
                component_summary[baseline.component_name]["metric_types"].append(baseline.metric_type.value)

        dashboard["baseline_summary"] = component_summary

        # SLA dashboard for all tiers
        for tier in SLATier:
            dashboard["sla_dashboard"][tier.value] = self.sla_manager.get_sla_dashboard(tier)

        return dashboard


# Pytest test fixtures and tests
@pytest.fixture
async def performance_baseline_system():
    """Performance baseline system fixture"""
    return PerformanceBaselineSystem()


@pytest.fixture
async def sample_metrics():
    """Sample performance metrics fixture"""
    return [
        PerformanceMetric(
            metric_id="test_1",
            metric_type=MetricType.RESPONSE_TIME,
            component="api",
            value=150.5,
            unit="ms",
            timestamp=datetime.now(timezone.utc)
        ),
        PerformanceMetric(
            metric_id="test_2",
            metric_type=MetricType.CPU_UTILIZATION,
            component="system",
            value=45.2,
            unit="percent",
            timestamp=datetime.now(timezone.utc)
        ),
        PerformanceMetric(
            metric_id="test_3",
            metric_type=MetricType.AVAILABILITY,
            component="api",
            value=99.9,
            unit="percent",
            timestamp=datetime.now(timezone.utc)
        )
    ]


@pytest.mark.performance
@pytest.mark.baseline
async def test_baseline_creation(performance_baseline_system, sample_metrics):
    """Test performance baseline creation"""
    # Create baseline for API response time
    api_metrics = [m for m in sample_metrics if m.component == "api" and m.metric_type == MetricType.RESPONSE_TIME]

    if len(api_metrics) >= 1:  # For testing, we'll use single metric
        # Create additional test metrics
        for i in range(10):
            api_metrics.append(PerformanceMetric(
                metric_id=f"test_api_{i}",
                metric_type=MetricType.RESPONSE_TIME,
                component="api",
                value=150.5 + (i * 2),  # Vary the values slightly
                unit="ms",
                timestamp=datetime.now(timezone.utc)
            ))

        baseline = performance_baseline_system.baseline_manager.create_baseline(
            component_name="api",
            component_type="service",
            metric_type=MetricType.RESPONSE_TIME,
            metrics=api_metrics,
            measurement_period_hours=1
        )

        assert baseline.component_name == "api", "Component name should match"
        assert baseline.metric_type == MetricType.RESPONSE_TIME, "Metric type should match"
        assert baseline.sample_count >= 10, "Should have adequate sample count"
        assert baseline.baseline_value > 0, "Baseline value should be positive"


@pytest.mark.performance
@pytest.mark.baseline
async def test_sla_requirement_creation(performance_baseline_system):
    """Test SLA requirement creation"""
    sla_requirements = performance_baseline_system.sla_manager.create_default_sla_requirements()

    assert len(sla_requirements) > 0, "Should create SLA requirements"

    # Check that all tiers are represented
    tiers = set(r.tier for r in sla_requirements)
    assert SLATier.BASIC in tiers, "Should have Basic tier"
    assert SLATier.STANDARD in tiers, "Should have Standard tier"
    assert SLATier.PREMIUM in tiers, "Should have Premium tier"
    assert SLATier.ENTERPRISE in tiers, "Should have Enterprise tier"

    # Check availability SLA progression
    basic_availability = next(r for r in sla_requirements if r.requirement_id == "basic_availability")
    standard_availability = next(r for r in sla_requirements if r.requirement_id == "standard_availability")
    premium_availability = next(r for r in sla_requirements if r.requirement_id == "premium_availability")

    assert basic_availability.target_value < standard_availability.target_value, "Basic availability should be lower than Standard"
    assert standard_availability.target_value < premium_availability.target_value, "Standard availability should be lower than Premium"


@pytest.mark.performance
@pytest.mark.baseline
async def test_sla_compliance_checking(performance_baseline_system):
    """Test SLA compliance checking"""
    # Create SLA requirements
    performance_baseline_system.sla_manager.create_default_sla_requirements()

    # Test metrics for Standard tier
    test_metrics = {
        MetricType.AVAILABILITY: 99.7,  # Should pass (target: 99.5)
        MetricType.RESPONSE_TIME: 600.0,  # Should fail (target: 500ms)
        MetricType.ERROR_RATE: 0.8  # Should pass (target: 1.0)
    }

    compliance_results = performance_baseline_system.sla_manager.check_sla_compliance(
        SLATier.STANDARD, test_metrics
    )

    assert compliance_results["tier"] == "standard", "Tier should match"
    assert "overall_compliant" in compliance_results, "Should have overall compliance status"
    assert "compliance_percentage" in compliance_results, "Should have compliance percentage"
    assert len(compliance_results["requirement_compliance"]) > 0, "Should have requirement compliance details"

    # Should not be fully compliant due to response time
    assert compliance_results["overall_compliant"] is False, "Should not be compliant due to response time"


@pytest.mark.performance
@pytest.mark.baseline
async def test_baseline_comparison(performance_baseline_system):
    """Test baseline comparison functionality"""
    # Create a baseline first
    test_metrics = []
    for i in range(20):
        test_metrics.append(PerformanceMetric(
            metric_id=f"baseline_test_{i}",
            metric_type=MetricType.RESPONSE_TIME,
            component="test_api",
            value=100.0 + (i * 2),  # Values from 100 to 138
            unit="ms",
            timestamp=datetime.now(timezone.utc)
        ))

    baseline = performance_baseline_system.baseline_manager.create_baseline(
        component_name="test_api",
        component_type="service",
        metric_type=MetricType.RESPONSE_TIME,
        metrics=test_metrics,
        measurement_period_hours=1
    )

    # Test comparison with current value
    current_value = 150.0  # Higher than baseline
    comparison = performance_baseline_system.baseline_manager.compare_against_baseline(
        "test_api", MetricType.RESPONSE_TIME, current_value
    )

    assert comparison["component"] == "test_api", "Component should match"
    assert comparison["metric_type"] == "response_time", "Metric type should match"
    assert comparison["current_value"] == current_value, "Current value should match"
    assert comparison["performance_level"] in ["excellent", "good", "acceptable", "poor"], "Should have valid performance level"

    # Higher response time should be "poor" performance
    assert comparison["performance_level"] == "poor", "Higher response time should be poor performance"


@pytest.mark.performance
@pytest.mark.baseline
async def test_performance_report_generation(performance_baseline_system):
    """Test performance report generation"""
    # Add some test metrics to the monitor
    test_metrics = []
    current_time = datetime.now(timezone.utc)

    for i in range(50):
        test_metrics.append(PerformanceMetric(
            metric_id=f"report_test_{i}",
            metric_type=MetricType.RESPONSE_TIME,
            component="test_component",
            value=120.0 + (i % 20),  # Vary values
            unit="ms",
            timestamp=current_time - timedelta(minutes=i)
        ))

    performance_baseline_system.monitor.metrics_history.extend(test_metrics)

    # Generate performance report
    report = await performance_baseline_system.generate_performance_report(
        component_name="test_component",
        metric_types=[MetricType.RESPONSE_TIME],
        analysis_period_hours=1
    )

    assert report.report_id.startswith("perf_report_"), "Report ID should be correctly formatted"
    assert report.component_name == "test_component", "Component should match"
    assert len(report.current_performance) > 0, "Should have current performance data"
    assert len(report.recommendations) > 0, "Should generate recommendations"
    assert report.performance_trend in ["improving", "stable", "degrading", "insufficient_data"], "Should have valid trend"


@pytest.mark.performance
@pytest.mark.baseline
async def test_performance_dashboard(performance_baseline_system):
    """Test performance dashboard generation"""
    # Create some test data
    performance_baseline_system.sla_manager.create_default_sla_requirements()

    # Generate dashboard
    dashboard = performance_baseline_system.get_performance_dashboard()

    assert "timestamp" in dashboard, "Should have timestamp"
    assert "total_baselines" in dashboard, "Should have total baselines count"
    assert "sla_dashboard" in dashboard, "Should have SLA dashboard"
    assert "baseline_summary" in dashboard, "Should have baseline summary"

    # Check SLA dashboard structure
    for tier in ["basic", "standard", "premium", "enterprise"]:
        assert tier in dashboard["sla_dashboard"], f"Should have {tier} tier in SLA dashboard"
        tier_dashboard = dashboard["sla_dashboard"][tier]
        assert "total_requirements" in tier_dashboard, "Should have total requirements count"
        assert "requirements" in tier_dashboard, "Should have requirements list"


@pytest.mark.performance
@pytest.mark.baseline
async def test_monitoring_summary(performance_baseline_system):
    """Test monitoring summary generation"""
    # Create test metrics
    test_metrics = []
    current_time = datetime.now(timezone.utc)

    for i in range(100):
        test_metrics.append(PerformanceMetric(
            metric_id=f"summary_test_{i}",
            metric_type=MetricType.RESPONSE_TIME if i % 2 == 0 else MetricType.CPU_UTILIZATION,
            component=f"component_{i % 3}",  # 3 different components
            value=100.0 + (i % 50),  # Vary values
            unit="ms" if i % 2 == 0 else "percent",
            timestamp=current_time - timedelta(seconds=i)
        ))

    summary = performance_baseline_system._generate_monitoring_summary(test_metrics)

    assert "metrics_by_type" in summary, "Should have metrics by type"
    assert "metrics_by_component" in summary, "Should have metrics by component"
    assert "monitoring_period" in summary, "Should have monitoring period"

    # Check metrics by type
    assert len(summary["metrics_by_type"]) == 2, "Should have 2 metric types"
    assert "response_time" in summary["metrics_by_type"], "Should have response time metrics"
    assert "cpu_utilization" in summary["metrics_by_type"], "Should have CPU utilization metrics"

    # Check metrics by component
    assert len(summary["metrics_by_component"]) == 3, "Should have 3 components"

    # Check monitoring period
    assert summary["monitoring_period"]["duration_hours"] > 0, "Should have positive duration"


if __name__ == "__main__":
    # Run performance baseline establishment
    print("=" * 70)
    print("PERFORMANCE BASELINE ESTABLISHMENT")
    print("=" * 70)

    async def main():
        system = PerformanceBaselineSystem()

        print("\n--- Starting Performance Baseline Establishment ---")

        # For demo purposes, we'll run a shorter monitoring period
        print("⏱️  Monitoring system performance for baseline establishment...")
        print("   (Note: Using 30-second demo instead of full 2-hour monitoring)")

        # Start monitoring for a short period for demo
        system.monitor.monitoring_interval = 2.0  # 2 seconds for demo
        metrics = await system.monitor.start_monitoring(0.5)  # 30 seconds

        print(f"   ✅ Collected {len(metrics)} performance metrics")

        if len(metrics) > 0:
            print("\n--- Creating Performance Baselines ---")

            # Create baselines from collected metrics
            components = set(m.component for m in metrics)
            metric_types = set(m.metric_type for m in metrics)

            baselines_created = {}
            for component in components:
                component_baselines = {}
                for metric_type in metric_types:
                    component_metrics = [
                        m for m in metrics
                        if m.component == component and m.metric_type == metric_type
                    ]

                    if len(component_metrics) >= 3:  # Minimum samples for demo
                        try:
                            baseline = system.baseline_manager.create_baseline(
                                component_name=component,
                                component_type="service",
                                metric_type=metric_type,
                                metrics=component_metrics,
                                measurement_period_hours=0.5  # 30 minutes
                            )
                            component_baselines[metric_type.value] = baseline.baseline_id
                            print(f"   ✅ Created baseline for {component} {metric_type.value}")
                            print(f"      Baseline value: {baseline.baseline_value:.2f} {baseline.unit}")
                            print(f"      P95: {baseline.percentile_95:.2f} {baseline.unit}")
                        except Exception as e:
                            print(f"   ❌ Failed to create baseline for {component} {metric_type.value}: {e}")

                if component_baselines:
                    baselines_created[component] = component_baselines

            print(f"\n📊 Baseline Summary:")
            print(f"   Components monitored: {len(components)}")
            print(f"   Metric types: {len(metric_types)}")
            print(f"   Baselines created: {sum(len(v) for v in baselines_created.values())}")

        print("\n--- Setting Up SLA Requirements ---")

        # Create SLA requirements
        sla_requirements = system.sla_manager.create_default_sla_requirements()
        print(f"   ✅ Created {len(sla_requirements)} SLA requirements")

        # Group by tier
        tier_counts = {}
        for req in sla_requirements:
            tier = req.tier.value
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        print(f"   📋 SLA Requirements by Tier:")
        for tier, count in tier_counts.items():
            print(f"      {tier.title()}: {count} requirements")

        print("\n--- Testing SLA Compliance ---")

        # Test SLA compliance with sample metrics
        test_metrics = {
            MetricType.AVAILABILITY: 99.7,
            MetricType.RESPONSE_TIME: 450.0,
            MetricType.ERROR_RATE: 0.3
        }

        for tier in [SLATier.STANDARD, SLATier.PREMIUM]:
            compliance = system.sla_manager.check_sla_compliance(tier, test_metrics)
            print(f"   📊 {tier.title()} Tier Compliance:")
            print(f"      Overall Compliant: {compliance['overall_compliant']}")
            print(f"      Compliance Percentage: {compliance['compliance_percentage']:.1f}%")

            for req_id, result in compliance['requirement_compliance'].items():
                status = "✅" if result['compliant'] else "❌"
                print(f"      {status} {req_id}: {result['actual']:.2f} vs target {result['target']:.2f}")

        print("\n--- Performance Monitoring Summary ---")

        if len(metrics) > 0:
            # Generate monitoring summary
            summary = system._generate_monitoring_summary(metrics)

            print(f"   📈 Metrics Collected:")
            for metric_type, stats in summary["metrics_by_type"].items():
                print(f"      {metric_type}: {stats['count']} samples")
                print(f"         Mean: {stats['mean']:.2f} {metrics[0].unit if metrics else ''}")
                print(f"         Range: {stats['min']:.2f} - {stats['max']:.2f}")

            print(f"   🔧 Components Monitored:")
            for component, info in summary["metrics_by_component"].items():
                print(f"      {component}: {info['total_metrics']} metrics, types: {', '.join(info['metric_types'])}")

        print("\n--- Generating Performance Dashboard ---")

        dashboard = system.get_performance_dashboard()
        print(f"   📊 Dashboard Generated:")
        print(f"      Total Baselines: {dashboard['total_baselines']}")
        print(f"      Total Reports: {dashboard['total_reports']}")
        print(f"      SLA Tiers: {list(dashboard['sla_dashboard'].keys())}")

        print("\n--- Baseline Comparison Demo ---")

        # Test baseline comparison
        if len(baselines_created) > 0:
            # Get first baseline for demo
            first_baseline_id = list(system.baseline_manager.baselines.values())[0].baseline_id
            baseline = system.baseline_manager.baselines[first_baseline_id]

            # Compare with different values
            test_values = [baseline.baseline_value * 0.8, baseline.baseline_value * 1.2, baseline.baseline_value * 1.5]
            for test_value in test_values:
                comparison = system.baseline_manager.compare_against_baseline(
                    baseline.component_name, baseline.metric_type, test_value
                )
                print(f"   📊 {baseline.component_name} {baseline.metric_type.value}:")
                print(f"      Current: {test_value:.2f} vs Baseline: {baseline.baseline_value:.2f}")
                print(f"      Performance Level: {comparison['performance_level'].upper()}")
                print(f"      Deviation: {comparison['deviation_percent']:.1f}%")

        print("\n--- Exporting Baselines ---")

        # Export baselines to CSV
        if len(system.baseline_manager.baselines) > 0:
            csv_path = "performance_baselines_export.csv"
            system.export_baselines_to_csv(csv_path)
            print(f"   📁 Exported {len(system.baseline_manager.baselines)} baselines to {csv_path}")

        print(f"\n" + "=" * 70)
        print("PERFORMANCE BASELINE ESTABLISHMENT COMPLETED")
        print("=" * 70)
        print("\n📋 Next Steps:")
        print("   1. Review established baselines and adjust if needed")
        print("   2. Set up automated monitoring against baselines")
        print("   3. Configure SLA alerting and compliance monitoring")
        print("   4. Schedule regular baseline updates (quarterly)")
        print("   5. Integrate with CI/CD pipeline for performance regression testing")
        print("\n📚 Files Generated:")
        if len(system.baseline_manager.baselines) > 0:
            print("   • performance_baselines.db (SQLite database)")
            print("   • performance_baselines_export.csv (CSV export)")
        print("   • Performance monitoring dashboard configured")
        print("   • SLA requirements and compliance monitoring")

    asyncio.run(main())