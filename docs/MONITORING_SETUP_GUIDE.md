# Enhanced Cognee - Production Monitoring Setup Guide

## Overview

This guide covers setting up comprehensive monitoring for Enhanced Cognee in production, including metrics collection, visualization, alerting, and log aggregation.

## Architecture

```
Enhanced Cognee → Prometheus (Metrics) → Grafana (Dashboards)
                        ↓
                    Loki (Logs)
                        ↓
                  AlertManager (Alerts)
```

## 1. Prometheus Configuration

### Create Prometheus Configuration

File: `monitoring/prometheus.yml`

```yaml
# Prometheus configuration for Enhanced Cognee monitoring
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'enhanced-cognee-prod'
    env: 'production'

# AlertManager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

# Rule files
rule_files:
  - 'alerts/*.yml'

# Scrape configurations
scrape_configs:
  # Enhanced Cognee MCP Server Metrics
  - job_name: 'enhanced-cognee-server'
    static_configs:
      - targets: ['enhanced-cognee-server:9090']
        labels:
          service: 'mcp-server'
          env: 'production'
    scrape_interval: 10s
    metrics_path: /metrics

  # PostgreSQL Exporter
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
        labels:
          service: 'postgresql'
    scrape_interval: 30s

  # Redis Exporter
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
        labels:
          service: 'redis'
    scrape_interval: 30s

  # Qdrant Metrics (if available)
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant-enhanced:6333']
        labels:
          service: 'qdrant'
    scrape_interval: 30s
    metrics_path: /metrics

  # Node Exporter (System Metrics)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
        labels:
          service: 'system'
    scrape_interval: 15s

  # cAdvisor (Container Metrics)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
        labels:
          service: 'containers'
    scrape_interval: 30s

# Alert configuration
alertmanager:
  static_configs:
    - targets:
      - alertmanager:9093
```

### Add Alert Rules

File: `monitoring/alerts/cognee-alerts.yml`

```yaml
groups:
  - name: cognee_health
    interval: 30s
    rules:
      # Service Availability
      - alert: ServiceDown
        expr: up{job=~"enhanced-cognee.*"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.job }} has been down for more than 1 minute"

      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for {{ $labels.job }}"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Container {{ $labels.name }} is using {{ $value | humanizePercentage }} of memory"

      # High CPU Usage
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "Container {{ $labels.name }} is using {{ $value | humanizePercentage }} of CPU"

      # Slow Response Time
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time"
          description: "95th percentile response time is {{ $value }}s"

      # Disk Space Low
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space low"
          description: "Only {{ $value | humanizePercentage }} disk space available"

      # Database Connection Pool Exhausted
      - alert: DatabasePoolExhausted
        expr: pg_stat_activity_count{datname="cognee_db"} > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"
          description: "{{ $value }} active connections"

  - name: cognee_performance
    interval: 1m
    rules:
      # Query Performance Degraded
      - alert: QueryPerformanceDegraded
        expr: histogram_quantile(0.95, rate(query_duration_seconds_bucket[10m])) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Query performance degraded"
          description: "95th percentile query time is {{ $value }}s"

      # Cache Hit Rate Low
      - alert: CacheHitRateLow
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.7
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Cache hit rate is low"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

## 2. Grafana Dashboard Configuration

### Dashboard Provisioning

File: `monitoring/grafana/provisioning/dashboards/cognee-dashboard.yml`

```yaml
apiVersion: 1

providers:
  - name: 'CogneeDashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

### Main Dashboard JSON

File: `monitoring/grafana/provisioning/dashboards/cognee-main-dashboard.json`

```json
{
  "dashboard": {
    "title": "Enhanced Cognee - Production Dashboard",
    "tags": ["cognee", "production"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=~\"enhanced-cognee.*\"}",
            "legendFormat": "{{job}}"
          }
        ],
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
        "options": {
          "colorMode": "background",
          "graphMode": "area"
        }
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{job=\"enhanced-cognee-server\"}[5m])",
            "legendFormat": "{{method}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 6, "y": 0}
      },
      {
        "title": "Response Time (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 18, "y": 0}
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage_bytes{container=~\"cognee.*\"}",
            "legendFormat": "{{container}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total{container=~\"cognee.*\"}[5m])",
            "legendFormat": "{{container}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "title": "Database Connections",
        "type": "gauge",
        "targets": [
          {
            "expr": "pg_stat_activity_count{datname=\"cognee_db\"}",
            "legendFormat": "Active Connections"
          }
        ],
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 16}
      },
      {
        "title": "Cache Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m])",
            "legendFormat": "Hits"
          },
          {
            "expr": "rate(cache_misses_total[5m])",
            "legendFormat": "Misses"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 6, "y": 16}
      },
      {
        "title": "Qdrant Collection Sizes",
        "type": "table",
        "targets": [
          {
            "expr": "qdrant_collections_points_total",
            "legendFormat": "{{collection}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 18, "y": 16}
      },
      {
        "title": "Error Rate by Endpoint",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "{{status}}"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 24}
      }
    ]
  }
}
```

## 3. Log Aggregation with Loki

### Loki Configuration

File: `monitoring/loki-config.yml`

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    max_transfer_retries: 0
  chunk_idle_period: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 24h

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
      chunks:
        prefix: chunk_
        period: 24h
      row_shards: [16]

storage_config:
  boltdb-shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

compactor:
  working_directory: /loki/boltdb-shipper-active
  shared_store: filesystem
```

### Promtail Configuration (Log Agent)

File: `monitoring/promtail-config.yml`

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Docker Container Logs
  - job_name: docker-logs
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: [container_name]
        target_label: container
      - source_labels: [container_label_com_docker_compose_service]
        target_label: service
      - regex: container_name.+"(cognee.*)"
        action: keep

  # Application Logs
  - job_name: cognee-app-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: enhanced-cognee
          __path__: /var/log/cognee/**/*.log
```

## 4. Docker Compose Update for Monitoring

Add to `docker-compose-production.yml`:

```yaml
  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: cognee-prometheus-prod
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/alerts:/etc/prometheus/alerts:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    ports:
      - "9091:9090"
    networks:
      - cognee-network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: cognee-grafana-prod
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SERVER_ROOT_URL: http://grafana:3000
      GF_INSTALL_PLUGINS: redis-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    networks:
      - cognee-network
    depends_on:
      - prometheus

  # Loki Log Aggregation
  loki:
    image: grafana/loki:latest
    container_name: cognee-loki-prod
    restart: unless-stopped
    volumes:
      - ./monitoring/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    ports:
      - "3100:3100"
    networks:
      - cognee-network

  # Promtail Log Agent
  promtail:
    image: grafana/promtail:latest
    container_name: cognee-promtail-prod
    restart: unless-stopped
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./monitoring/promtail-config.yml:/etc/promtail/config.yml:ro
      - promtail_position:/tmp/positions
    command:
      - '-config.file=/etc/promtail/config.yml'
    networks:
      - cognee-network
    depends_on:
      - loki
```

## 5. Application Metrics Setup

### Add Metrics to MCP Server

In `enhanced_cognee_mcp_server.py`, add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'active_connections',
    'Active database connections'
)

memory_operations = Counter(
    'memory_operations_total',
    'Total memory operations',
    ['operation', 'status']  # operation: add/search/delete, status: success/error
)

cache_performance = Counter(
    'cache_operations_total',
    'Cache performance',
    ['operation']  # operation: hit/miss
)

# Metrics endpoint
from starlette.responses import Response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Middleware to track metrics
@app.middleware("http")
async def track_requests(request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    method = request.method
    endpoint = request.url.path
    status = response.status_code

    request_count.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()

    duration = time.time() - start_time
    request_duration.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

    return response
```

## 6. Health Check Endpoints

### Comprehensive Health Check

```python
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {}
    }

    overall_healthy = True

    # Check PostgreSQL
    try:
        async with postgres_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["checks"]["postgres"] = "healthy"
    except Exception as e:
        health_status["checks"]["postgres"] = f"unhealthy: {str(e)}"
        overall_healthy = False

    # Check Qdrant
    try:
        collections = qdrant_client.get_collections()
        health_status["checks"]["qdrant"] = "healthy"
    except Exception as e:
        health_status["checks"]["qdrant"] = f"unhealthy: {str(e)}"
        overall_healthy = False

    # Check Redis
    try:
        await redis_client.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        overall_healthy = False

    # Check Neo4j
    try:
        # Verify Neo4j connectivity
        health_status["checks"]["neo4j"] = "healthy"
    except Exception as e:
        health_status["checks"]["neo4j"] = f"unhealthy: {str(e)}"
        overall_healthy = False

    if not overall_healthy:
        health_status["status"] = "degraded"

    status_code = 200 if overall_healthy else 503
    return JSONResponse(content=health_status, status_code=status_code)
```

## 7. AlertManager Configuration

File: `monitoring/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: smtp.gmail.com:587
  smtp_from: noreply@your-domain.com
  smtp_auth_username: your-email@gmail.com
  smtp_auth_password: your-app-password

# Route alerts to notification channels
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    # Critical alerts go to pager
    - match:
        severity: critical
      receiver: 'pager-receiver'
      continue: false

    # Warning alerts go to email
    - match:
        severity: warning
      receiver: 'email-receiver'

    # Info alerts go to slack
    - match:
        severity: info
      receiver: 'slack-receiver'

receivers:
  - name: 'default-receiver'
    email_configs:
      - to: alerts@your-domain.com

  - name: 'pager-receiver'
    pagerduty_configs:
      - service_key: YOUR_PAGERDUTY_KEY
    slack_configs:
      - api_url: YOUR_SLACK_WEBHOOK
      channel: '#alerts-critical'

  - name: 'email-receiver'
    email_configs:
      - to: ops-team@your-domain.com
      headers:
        Subject: '[Cognee Alert] {{ .GroupLabels.alertname }}'

  - name: 'slack-receiver'
    slack_configs:
      - api_url: YOUR_SLACK_WEBHOOK
      channel: '#cognee-ops'
      title: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
      text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

## 8. Deployment Steps

```bash
# 1. Create monitoring directory structure
mkdir -p monitoring/alerts monitoring/grafana/provisioning/dashboards

# 2. Copy configuration files
cp monitoring/prometheus.yml monitoring/prometheus.yml
cp monitoring/alerts/cognee-alerts.yml monitoring/alerts/

# 3. Start monitoring stack
docker-compose -f docker-compose-production.yml up -d prometheus grafana loki promtail

# 4. Verify Prometheus is scraping
curl http://localhost:9091/api/v1/targets

# 5. Access Grafana
# URL: http://localhost:3000
# Username: admin
# Password: (from GRAFANA_PASSWORD env var)

# 6. Import dashboards or use provisioning
# Dashboards will be auto-loaded from provisioning directory

# 7. Verify metrics are being collected
# http://localhost:9091/metrics
```

## 9. Monitoring URLs

After deployment, access monitoring at:

- **Grafana Dashboard**: http://your-server:3000
- **Prometheus**: http://your-server:9091
- **AlertManager**: http://your-server:9093
- **Service Metrics**: http://your-server:8000/metrics
- **Health Check**: http://your-server:8000/health

## 10. Key Metrics to Monitor

### Application Metrics
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (percentage)
- Active connections
- Memory operations (add/search/delete)
- Cache hit/miss ratio

### Database Metrics
- Connection pool usage
- Query duration
- Transaction throughput
- Deadlocks/locks
- Table sizes

### Infrastructure Metrics
- CPU usage per container
- Memory usage per container
- Disk I/O
- Network I/O
- Container restarts

### Business Metrics
- Memories stored per day
- Active users/agents
- Search queries per day
- Cross-language searches
- Memory sharing events

## 11. Alert Thresholds

Recommended alert thresholds:

- **Critical**: Service down, error rate > 5%, memory > 90%, CPU > 90%, disk space < 10%
- **Warning**: Response time p95 > 1s, cache hit rate < 70%, query time > 500ms
- **Info**: New deployment, high traffic (normal), cache warming

This monitoring setup provides complete visibility into your Enhanced Cognee production deployment!
