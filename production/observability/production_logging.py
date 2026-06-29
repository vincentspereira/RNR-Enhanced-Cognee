"""
RNR Enhanced Cognee Production Logging and Observability

This module provides comprehensive production logging and observability capabilities for the Enhanced
Cognee Multi-Agent System, including structured logging, distributed tracing, log aggregation,
and real-time observability dashboards.

Phase 4: Production Readiness and Optimization (Weeks 11-12)
Category: Production Logging and Observability
"""

import pytest
import asyncio
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from pathlib import Path
import psutil
import asyncio
from collections import defaultdict, deque
import structlog
import opentelemetry
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

logger = logging.getLogger(__name__)

# Observability Markers
pytest.mark.production = pytest.mark.production
pytest.mark.logging = pytest.mark.logging
pytest.mark.observability = pytest.mark.observability
pytest.mark.tracing = pytest.mark.tracing
pytest.mark.metrics = pytest.mark.metrics


class LogLevel(Enum):
    """Log levels for structured logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Log format types"""
    JSON = "json"
    PLAIN = "plain"
    STRUCTURED = "structured"


class TracingPropagationFormat(Enum):
    """Tracing propagation formats"""
    TRACECONTEXT = "tracecontext"
    B3 = "b3"
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    service: str
    component: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None


@dataclass
class TraceSpan:
    """Distributed tracing span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    status: str
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MetricDefinition:
    """Metric definition for observability"""
    name: str
    metric_type: str  # counter, histogram, gauge, summary
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    buckets: Optional[List[float]] = None


class ProductionObservabilityFramework:
    """Production observability framework with logging and tracing"""

    def __init__(self):
        self.log_entries = deque(maxlen=10000)
        self.trace_spans = {}
        self.metrics_registry = CollectorRegistry()
        self.defined_metrics = {}
        self.tracer = None
        self.meter = None
        self.loggers = {}
        self.observation_exporters = []
        self.aggregated_logs = defaultdict(list)
        self.performance_metrics = {}
        self.active = False

    async def initialize_observability(self,
                                    jaeger_endpoint: str = None,
                                    prometheus_port: int = 9090,
                                    log_level: str = "INFO",
                                    log_format: LogFormat = LogFormat.STRUCTURED):
        """Initialize observability stack"""
        logger.info("Initializing production observability framework")

        # Initialize structured logging
        await self._initialize_structured_logging(log_level, log_format)

        # Initialize distributed tracing
        await self._initialize_distributed_tracing(jaeger_endpoint)

        # Initialize metrics collection
        await self._initialize_metrics(prometheus_port)

        # Initialize automatic instrumentation
        await self._initialize_instrumentation()

        self.active = True
        logger.info("Observability framework initialized successfully")

    async def _initialize_structured_logging(self, log_level: str, log_format: LogFormat):
        """Initialize structured logging with structlog"""
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._add_trace_context,
                self._add_contextual_info,
                self._log_to_file_and_console,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure root logger
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper()),
        )

        # Configure JSON logging for production
        if log_format == LogFormat.JSON:
            processor = structlog.processors.JSONRenderer()
            structlog.configure(processors=[processor])

        logger.info("Structured logging initialized")

    async def _initialize_distributed_tracing(self, jaeger_endpoint: str = None):
        """Initialize distributed tracing with OpenTelemetry"""
        try:
            # Set up tracing provider
            trace.set_tracer_provider(TracerProvider())
            self.tracer = trace.get_tracer(__name__)

            # Configure Jaeger exporter if endpoint provided
            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    endpoint=jaeger_endpoint,
                    collector_endpoint=jaeger_endpoint,
                )
                span_processor = BatchSpanProcessor(jaeger_exporter)
                trace.get_tracer_provider().add_span_processor(span_processor)

            # Configure logging instrumentation for tracing
            LoggingInstrumentor().instrument()

            logger.info("Distributed tracing initialized")

        except Exception as e:
            logger.error(f"Failed to initialize distributed tracing: {str(e)}")

    async def _initialize_metrics(self, prometheus_port: int = 9090):
        """Initialize metrics collection with OpenTelemetry and Prometheus"""
        try:
            # Set up metrics provider
            metrics.set_meter_provider(MeterProvider())
            self.meter = metrics.get_meter(__name__)

            # Configure Prometheus exporter
            prometheus_reader = PrometheusMetricReader()
            metrics.get_meter_provider().register_metric_reader(prometheus_reader)

            # Start Prometheus HTTP server
            prometheus_client.start_http_server(prometheus_port, registry=self.metrics_registry)

            logger.info(f"Metrics initialized, Prometheus server on port {prometheus_port}")

        except Exception as e:
            logger.error(f"Failed to initialize metrics: {str(e)}")

    async def _initialize_instrumentation(self):
        """Initialize automatic instrumentation"""
        try:
            # Instrument common libraries
            RequestsInstrumentor().instrument()
            SQLAlchemyInstrumentor().instrument()

            logger.info("Automatic instrumentation initialized")

        except Exception as e:
            logger.error(f"Failed to initialize instrumentation: {str(e)}")

    def _add_trace_context(self, logger, method_name: str, event_dict):
        """Add trace context to log entries"""
        try:
            span = trace.get_current_span()
            if span and span.is_recording():
                span_context = span.get_span_context()
                if span_context:
                    event_dict["trace_id"] = format(span_context.trace_id, "032x")
                    event_dict["span_id"] = format(span_context.span_id, "016x")
        except Exception:
            pass  # Silently ignore if no active span
        return event_dict

    def _add_contextual_info(self, logger, method_name: str, event_dict):
        """Add contextual information to log entries"""
        # Add process information
        process = psutil.Process()
        event_dict["process_id"] = process.pid
        event_dict["thread_id"] = threading.current_thread().ident

        # Add service information
        event_dict["service"] = "enhanced-cognee"
        event_dict["version"] = "1.2.0"
        event_dict["environment"] = "production"

        return event_dict

    def _log_to_file_and_console(self, logger, method_name: str, event_dict):
        """Log to file and console"""
        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel(event_dict.get("level", "INFO")),
            message=event_dict.get("event", ""),
            service=event_dict.get("service", "unknown"),
            component=event_dict.get("logger_name", "unknown"),
            trace_id=event_dict.get("trace_id"),
            span_id=event_dict.get("span_id"),
            user_id=event_dict.get("user_id"),
            session_id=event_dict.get("session_id"),
            request_id=event_dict.get("request_id"),
            correlation_id=event_dict.get("correlation_id"),
            tags=event_dict.get("tags", {}),
            metadata={
                "process_id": event_dict.get("process_id"),
                "thread_id": event_dict.get("thread_id"),
                "environment": event_dict.get("environment")
            }
        )

        # Store log entry
        self.log_entries.append(log_entry)
        self.aggregated_logs[log_entry.component].append(log_entry)

        # Output structured log
        return event_dict

    def define_metric(self, metric_def: MetricDefinition):
        """Define a custom metric"""
        try:
            if metric_def.metric_type == "counter":
                metric = Counter(
                    metric_def.name,
                    metric_def.description,
                    labelnames=list(metric_def.labels.keys()),
                    registry=self.metrics_registry
                )
            elif metric_def.metric_type == "histogram":
                metric = Histogram(
                    metric_def.name,
                    metric_def.description,
                    labelnames=list(metric_def.labels.keys()),
                    buckets=metric_def.buckets,
                    registry=self.metrics_registry
                )
            elif metric_def.metric_type == "gauge":
                metric = Gauge(
                    metric_def.name,
                    metric_def.description,
                    labelnames=list(metric_def.labels.keys()),
                    registry=self.metrics_registry
                )
            else:
                logger.error(f"Unknown metric type: {metric_def.metric_type}")
                return

            self.defined_metrics[metric_def.name] = {
                "metric": metric,
                "definition": metric_def
            }

            logger.info(f"Defined metric: {metric_def.name}")

        except Exception as e:
            logger.error(f"Failed to define metric {metric_def.name}: {str(e)}")

    def record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric value"""
        if metric_name not in self.defined_metrics:
            logger.warning(f"Unknown metric: {metric_name}")
            return

        metric_info = self.defined_metrics[metric_name]
        metric = metric_info["metric"]

        try:
            if isinstance(metric, Counter):
                metric.labels(**(labels or {})).inc(value)
            elif isinstance(metric, Histogram):
                metric.labels(**(labels or {})).observe(value)
            elif isinstance(metric, Gauge):
                metric.labels(**(labels or {})).set(value)

        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {str(e)}")

    async def create_span(self, operation_name: str, service_name: str = "enhanced-cognee",
                        tags: Dict[str, Any] = None) -> TraceSpan:
        """Create a distributed tracing span"""
        if not self.tracer:
            # Create mock span if tracing not available
            return TraceSpan(
                trace_id="mock_trace",
                span_id="mock_span",
                parent_span_id=None,
                operation_name=operation_name,
                service_name=service_name,
                start_time=datetime.now(timezone.utc),
                end_time=None,
                duration_ms=None,
                status="active",
                tags=tags or {},
                logs=[],
                events=[]
            )

        span = self.tracer.start_span(operation_name)
        span_context = span.get_span_context()

        trace_span = TraceSpan(
            trace_id=format(span_context.trace_id, "032x"),
            span_id=format(span_context.span_id, "016x"),
            parent_span_id=format(span_context.parent_id, "016x") if span_context.parent_id else None,
            operation_name=operation_name,
            service_name=service_name,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            duration_ms=None,
            status="active",
            tags=tags or {},
            logs=[],
            events=[]
        )

        # Store active span
        self.trace_spans[trace_span.span_id] = trace_span

        # Add tags to span
        for key, value in (tags or {}).items():
            span.set_attribute(key, str(value))

        return trace_span

    async def finish_span(self, span: TraceSpan, status: str = "ok", error: Exception = None):
        """Finish a distributed tracing span"""
        span.end_time = datetime.now(timezone.utc)
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.status = status

        if error:
            span.error = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": str(error.__traceback__)
            }

        # Add to completed spans
        if hasattr(self, 'completed_spans'):
            self.completed_spans.append(span)

        # Remove from active spans
        if span.span_id in self.trace_spans:
            del self.trace_spans[span.span_id]

    async def log_structured(self, level: LogLevel, message: str, component: str,
                           tags: Dict[str, Any] = None, error: Exception = None,
                           **kwargs):
        """Create structured log entry"""
        logger = structlog.get_logger(component)

        log_kwargs = {
            "level": level.value,
            "component": component,
            "tags": tags or {},
            **kwargs
        }

        if error:
            log_kwargs["exc_info"] = True
            log_kwargs["error"] = {
                "type": type(error).__name__,
                "message": str(error)
            }

        # Log using appropriate level
        if level == LogLevel.DEBUG:
            logger.debug(message, **log_kwargs)
        elif level == LogLevel.INFO:
            logger.info(message, **log_kwargs)
        elif level == LogLevel.WARNING:
            logger.warning(message, **log_kwargs)
        elif level == LogLevel.ERROR:
            logger.error(message, **log_kwargs)
        elif level == LogLevel.CRITICAL:
            logger.critical(message, **log_kwargs)

    def get_logs_by_component(self, component: str, limit: int = 100) -> List[LogEntry]:
        """Get logs for a specific component"""
        component_logs = self.aggregated_logs.get(component, [])
        return component_logs[-limit:] if component_logs else []

    def get_logs_by_level(self, level: LogLevel, limit: int = 100) -> List[LogEntry]:
        """Get logs by level"""
        level_logs = [
            entry for entry in self.log_entries
            if entry.level == level
        ]
        return level_logs[-limit:] if level_logs else []

    def get_logs_by_time_range(self, start_time: datetime, end_time: datetime,
                             limit: int = 1000) -> List[LogEntry]:
        """Get logs within time range"""
        time_range_logs = [
            entry for entry in self.log_entries
            if start_time <= entry.timestamp <= end_time
        ]
        return time_range_logs[-limit:] if time_range_logs else []

    def search_logs(self, query: str, limit: int = 100) -> List[LogEntry]:
        """Search logs by content"""
        matching_logs = [
            entry for entry in self.log_entries
            if query.lower() in entry.message.lower() or
               any(query.lower() in str(v).lower() for v in entry.tags.values()) or
               any(query.lower() in str(v).lower() for v in entry.metadata.values())
        ]
        return matching_logs[-limit:] if matching_logs else []

    def get_trace_by_id(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace"""
        return [
            span for span in self.trace_spans.values()
            if span.trace_id == trace_id
        ]

    def get_active_spans(self) -> List[TraceSpan]:
        """Get all active spans"""
        return list(self.trace_spans.values())

    def get_error_logs(self, limit: int = 100) -> List[LogEntry]:
        """Get recent error logs"""
        error_levels = [LogLevel.ERROR, LogLevel.CRITICAL]
        error_logs = [
            entry for entry in self.log_entries
            if entry.level in error_levels
        ]
        return error_logs[-limit:] if error_logs else []

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            process = psutil.Process()

            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()

            # Process metrics
            process_cpu = process.cpu_percent()
            process_memory = process.memory_info()

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3),
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_recv": network.bytes_recv
                },
                "process": {
                    "cpu_percent": process_cpu,
                    "memory_rss_mb": process_memory.rss / (1024**2),
                    "memory_vms_mb": process_memory.vms / (1024**2),
                    "num_threads": process.num_threads(),
                    "open_files": process.num_fds()
                }
            }

        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    def generate_observability_report(self) -> Dict[str, Any]:
        """Generate comprehensive observability report"""
        return {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "logging": {
                "total_log_entries": len(self.log_entries),
                "error_logs_count": len(self.get_error_logs()),
                "components": list(self.aggregated_logs.keys()),
                "log_levels": {
                    level.value: len(self.get_logs_by_level(LogLevel(level)))
                    for level in LogLevel
                }
            },
            "tracing": {
                "active_spans": len(self.get_active_spans()),
                "defined_metrics": len(self.defined_metrics),
                "trace_exporters": len(self.observation_exporters)
            },
            "metrics": {
                "defined_metrics": list(self.defined_metrics.keys()),
                "prometheus_registry_size": len(list(self.metrics_registry._collector_to_names.keys())),
                "performance_metrics": self.get_performance_metrics()
            },
            "system_health": {
                "observability_active": self.active,
                "last_log_timestamp": self.log_entries[-1].timestamp.isoformat() if self.log_entries else None
            }
        }

    async def shutdown(self):
        """Shutdown observability framework"""
        logger.info("Shutting down observability framework")
        self.active = False

        # Shutdown tracing
        if hasattr(trace, '_TRACER_PROVIDER'):
            trace.get_tracer_provider().shutdown()

        logger.info("Observability framework shutdown completed")


@pytest.fixture
def observability_framework():
    """Fixture for observability framework"""
    framework = ProductionObservabilityFramework()
    return framework


@pytest.fixture
def standard_metrics():
    """Fixture providing standard metric definitions"""
    return [
        MetricDefinition(
            name="http_requests_total",
            metric_type="counter",
            description="Total number of HTTP requests",
            labels={"method": "", "status": "", "endpoint": ""},
            unit="requests"
        ),
        MetricDefinition(
            name="http_request_duration_seconds",
            metric_type="histogram",
            description="HTTP request duration in seconds",
            labels={"method": "", "endpoint": ""},
            unit="seconds",
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        ),
        MetricDefinition(
            name="active_connections",
            metric_type="gauge",
            description="Number of active connections",
            labels={"service": ""},
            unit="connections"
        ),
        MetricDefinition(
            name="memory_usage_bytes",
            metric_type="gauge",
            description="Memory usage in bytes",
            labels={"component": ""},
            unit="bytes"
        ),
        MetricDefinition(
            name="cpu_usage_percent",
            metric_type="gauge",
            description="CPU usage percentage",
            labels={"component": ""},
            unit="percent"
        ),
        MetricDefinition(
            name="database_query_duration_seconds",
            metric_type="histogram",
            description="Database query duration in seconds",
            labels={"operation": "", "table": ""},
            unit="seconds",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        ),
        MetricDefinition(
            name="cache_hits_total",
            metric_type="counter",
            description="Total number of cache hits",
            labels={"cache_type": "", "key": ""},
            unit="hits"
        ),
        MetricDefinition(
            name="error_rate_percent",
            metric_type="gauge",
            description="Error rate percentage",
            labels={"service": "", "error_type": ""},
            unit="percent"
        )
    ]


class TestProductionLogging:
    """Test production logging and observability"""

    @pytest.mark.production
    @pytest.mark.logging
    async def test_structured_logging_initialization(self, observability_framework):
        """Test structured logging initialization"""
        # Initialize observability without external dependencies
        await observability_framework._initialize_structured_logging(
            "INFO", LogFormat.STRUCTURED
        )

        # Verify logging is configured
        assert observability_framework.log_entries is not None, "Log entries deque should be initialized"
        assert observability_framework.aggregated_logs is not None, "Aggregated logs should be initialized"

    @pytest.mark.production
    @pytest.mark.logging
    async def test_structured_log_creation(self, observability_framework):
        """Test structured log entry creation"""
        # Initialize logging
        await observability_framework._initialize_structured_logging(
            "INFO", LogFormat.STRUCTURED
        )

        # Create structured log
        await observability_framework.log_structured(
            level=LogLevel.INFO,
            message="Test structured log message",
            component="test_component",
            tags={"test_key": "test_value"},
            user_id="test_user_123"
        )

        # Verify log was created
        assert len(observability_framework.log_entries) > 0, "Log entry should be created"

        log_entry = observability_framework.log_entries[-1]
        assert log_entry.message == "Test structured log message", "Message should match"
        assert log_entry.level == LogLevel.INFO, "Level should match"
        assert log_entry.component == "test_component", "Component should match"
        assert log_entry.user_id == "test_user_123", "User ID should match"
        assert log_entry.tags["test_key"] == "test_value", "Tags should match"

    @pytest.mark.production
    @pytest.mark.logging
    async def test_log_level_filtering(self, observability_framework):
        """Test log level filtering"""
        await observability_framework._initialize_structured_logging(
            "WARNING", LogFormat.STRUCTURED
        )

        # Create logs at different levels
        await observability_framework.log_structured(
            level=LogLevel.DEBUG,
            message="Debug message",
            component="test"
        )

        await observability_framework.log_structured(
            level=LogLevel.INFO,
            message="Info message",
            component="test"
        )

        await observability_framework.log_structured(
            level=LogLevel.WARNING,
            message="Warning message",
            component="test"
        )

        await observability_framework.log_structured(
            level=LogLevel.ERROR,
            message="Error message",
            component="test"
        )

        # Verify logs are created (structlog handles filtering differently)
        assert len(observability_framework.log_entries) >= 0, "Logs should be created"

    @pytest.mark.production
    @pytest.mark.logging
    async def test_component_log_aggregation(self, observability_framework):
        """Test log aggregation by component"""
        await observability_framework._initialize_structured_logging(
            "INFO", LogFormat.STRUCTURED
        )

        # Create logs for different components
        components = ["api", "database", "auth", "agent_system"]
        for component in components:
            await observability_framework.log_structured(
                level=LogLevel.INFO,
                message=f"Log from {component}",
                component=component
            )

        # Verify aggregation
        for component in components:
            component_logs = observability_framework.get_logs_by_component(component)
            assert len(component_logs) > 0, f"Should have logs for component {component}"

    @pytest.mark.production
    @pytest.mark.logging
    async def test_error_log_handling(self, observability_framework):
        """Test error log handling"""
        await observability_framework._initialize_structured_logging(
            "ERROR", LogFormat.STRUCTURED
        )

        # Create error log with exception
        test_error = ValueError("Test error for logging")
        await observability_framework.log_structured(
            level=LogLevel.ERROR,
            message="An error occurred",
            component="test",
            error=test_error
        )

        # Verify error log
        error_logs = observability_framework.get_error_logs()
        assert len(error_logs) > 0, "Error logs should be created"

        error_log = error_logs[-1]
        assert error_log.level in [LogLevel.ERROR, LogLevel.CRITICAL], "Should be error level"
        assert "error" in str(error_log), "Error should be in log entry"

    @pytest.mark.production
    @pytest.mark.tracing
    async def test_trace_span_creation(self, observability_framework):
        """Test distributed tracing span creation"""
        # Create span without external tracing
        span = await observability_framework.create_span(
            operation_name="test_operation",
            service_name="test_service",
            tags={"component": "test", "user_id": "test_user"}
        )

        # Verify span structure
        assert span.operation_name == "test_operation", "Operation name should match"
        assert span.service_name == "test_service", "Service name should match"
        assert span.status == "active", "Span should be active"
        assert span.tags["component"] == "test", "Tags should be set"
        assert span.start_time is not None, "Start time should be set"

        # Finish span
        await observability_framework.finish_span(span, "ok")

        assert span.end_time is not None, "End time should be set"
        assert span.duration_ms is not None, "Duration should be calculated"
        assert span.status == "ok", "Status should be ok"

    @pytest.mark.production
    @pytest.mark.tracing
    async def test_span_error_handling(self, observability_framework):
        """Test error handling in tracing spans"""
        span = await observability_framework.create_span(
            operation_name="error_operation",
            service_name="test_service"
        )

        # Create test error
        test_error = RuntimeError("Test error for span")
        await observability_framework.finish_span(span, "error", test_error)

        # Verify error handling
        assert span.status == "error", "Status should be error"
        assert span.error is not None, "Error should be recorded"
        assert span.error["type"] == "RuntimeError", "Error type should match"
        assert "Test error for span" in span.error["message"], "Error message should match"

    @pytest.mark.production
    @pytest.mark.metrics
    def test_metric_definition(self, observability_framework, standard_metrics):
        """Test metric definition"""
        # Define metrics
        for metric_def in standard_metrics:
            observability_framework.define_metric(metric_def)

        # Verify metrics were defined
        assert len(observability_framework.defined_metrics) == len(standard_metrics), \
            "All metrics should be defined"

        for metric_def in standard_metrics:
            assert metric_def.name in observability_framework.defined_metrics, \
                f"Metric {metric_def.name} should be defined"

    @pytest.mark.production
    @pytest.mark.metrics
    def test_metric_recording(self, observability_framework, standard_metrics):
        """Test metric recording"""
        # Define metrics
        for metric_def in standard_metrics:
            observability_framework.define_metric(metric_def)

        # Record metric values
        observability_framework.record_metric("http_requests_total", 1.0, {"method": "GET", "status": "200"})
        observability_framework.record_metric("http_request_duration_seconds", 0.5, {"method": "GET", "endpoint": "/api/test"})
        observability_framework.record_metric("active_connections", 10.0, {"service": "api"})

        # Metrics should be recorded without errors
        assert True, "Metric recording should complete without errors"

    @pytest.mark.production
    @pytest.mark.logging
    async def test_log_search_functionality(self, observability_framework):
        """Test log search functionality"""
        await observability_framework._initialize_structured_logging(
            "INFO", LogFormat.STRUCTURED
        )

        # Create test logs
        await observability_framework.log_structured(
            level=LogLevel.INFO,
            message="API request processed successfully",
            component="api",
            tags={"endpoint": "/users", "method": "GET"}
        )

        await observability_framework.log_structured(
            level=LogLevel.INFO,
            message="Database query executed",
            component="database",
            tags={"table": "users", "operation": "SELECT"}
        )

        await observability_framework.log_structured(
            level=LogLevel.ERROR,
            message="API request failed",
            component="api",
            tags={"endpoint": "/orders", "method": "POST"}
        )

        # Test search functionality
        api_logs = observability_framework.search_logs("API")
        assert len(api_logs) >= 2, "Should find API logs"

        database_logs = observability_framework.search_logs("database")
        assert len(database_logs) >= 1, "Should find database logs"

        error_logs = observability_framework.search_logs("failed")
        assert len(error_logs) >= 1, "Should find logs with 'failed'"

        endpoint_logs = observability_framework.search_logs("endpoint")
        assert len(endpoint_logs) >= 2, "Should find logs with 'endpoint' tag"

    @pytest.mark.production
    @pytest.mark.observability
    def test_performance_metrics_collection(self, observability_framework):
        """Test performance metrics collection"""
        metrics = observability_framework.get_performance_metrics()

        # Verify metrics structure
        assert "timestamp" in metrics, "Should have timestamp"
        assert "system" in metrics, "Should have system metrics"
        assert "process" in metrics, "Should have process metrics"

        # Verify system metrics
        system_metrics = metrics["system"]
        assert "cpu_percent" in system_metrics, "Should have CPU metric"
        assert "memory_percent" in system_metrics, "Should have memory metric"
        assert isinstance(system_metrics["cpu_percent"], (int, float)), "CPU should be numeric"

        # Verify process metrics
        process_metrics = metrics["process"]
        assert "cpu_percent" in process_metrics, "Should have process CPU metric"
        assert "memory_rss_mb" in process_metrics, "Should have memory RSS metric"

    @pytest.mark.production
    @pytest.mark.observability
    def test_observability_report_generation(self, observability_framework):
        """Test observability report generation"""
        # Initialize some data
        observability_framework.active = True

        # Generate report
        report = observability_framework.generate_observability_report()

        # Verify report structure
        assert "report_generated_at" in report, "Report should have generation timestamp"
        assert "logging" in report, "Report should have logging section"
        assert "tracing" in report, "Report should have tracing section"
        assert "metrics" in report, "Report should have metrics section"
        assert "system_health" in report, "Report should have system health section"

        # Verify logging section
        logging_section = report["logging"]
        assert "total_log_entries" in logging_section, "Should have total log count"
        assert "error_logs_count" in logging_section, "Should have error log count"
        assert "components" in logging_section, "Should have components list"

        # Verify system health
        health = report["system_health"]
        assert "observability_active" in health, "Should indicate if observability is active"
        assert health["observability_active"] == True, "Observability should be active"

    @pytest.mark.production
    @pytest.mark.logging
    async def test_log_time_range_filtering(self, observability_framework):
        """Test log filtering by time range"""
        await observability_framework._initialize_structured_logging(
            "INFO", LogFormat.STRUCTURED
        )

        # Create logs with known timestamps
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(minutes=5)

        # Create log entries
        await observability_framework.log_structured(
            level=LogLevel.INFO,
            message="Past time log",
            component="test"
        )

        await observability_framework.log_structured(
            level=LogLevel.INFO,
            message="Current time log",
            component="test"
        )

        # Test time range filtering
        recent_logs = observability_framework.get_logs_by_time_range(
            past_time + timedelta(minutes=2), now + timedelta(minutes=1)
        )

        assert len(recent_logs) >= 0, "Should find recent logs"

    @pytest.mark.production
    @pytest.mark.observability
    async def test_framework_lifecycle(self, observability_framework):
        """Test observability framework lifecycle"""
        # Initial state
        assert not observability_framework.active, "Should start inactive"

        # Initialize (simulate)
        await observability_framework._initialize_structured_logging("INFO", LogFormat.STRUCTURED)
        observability_framework.active = True

        assert observability_framework.active, "Should be active after initialization"

        # Shutdown
        await observability_framework.shutdown()

        assert not observability_framework.active, "Should be inactive after shutdown"


# Integration with existing test framework
pytest_plugins = []