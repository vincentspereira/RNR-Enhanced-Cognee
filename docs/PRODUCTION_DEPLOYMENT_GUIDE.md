# Enhanced Cognee - Production Deployment Guide

## Quick Start - Deploy to Production

### Prerequisites

Before deploying to production, ensure you have:

- [ ] Docker 20.10+ and Docker Compose 2.0+
- [ ] 8GB+ RAM available
- [ ] 50GB+ disk space
- [ ] Linux server (Ubuntu 22.04 LTS recommended)
- [ ] SSL certificate for your domain
- [ ] Domain name configured with DNS

### Deployment Steps

#### Step 1: Prepare Environment

```bash
# Clone repository
git clone https://github.com/your-org/enhanced-cognee.git
cd enhanced-cognee

# Create production environment file
cp .env.production.template .env.production

# Generate strong passwords
openssl rand -base64 32  # For each password in .env.production
```

#### Step 2: Configure Environment

Edit `.env.production`:
```bash
nano .env.production
```

Update all `CHANGE_THIS` placeholders with actual values.

**Critical:** Generate unique, strong passwords for:
- POSTGRES_PASSWORD
- NEO4J_PASSWORD
- REDIS_PASSWORD
- COGNEE_API_KEY
- GRAFANA_PASSWORD

#### Step 3: Configure SSL Certificates

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Option A: Use Let's Encrypt (recommended)
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# Option B: Use self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

#### Step 4: Configure Nginx

Create `nginx/nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    # Performance settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    # Upstream servers
    upstream cognee_backend {
        server enhanced-cognee-server:8000;
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API proxy
        location / {
            limit_req zone=api_limit burst=20;

            proxy_pass http://cognee_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Metrics endpoint (protected)
        location /metrics {
            auth_basic "Prometheus Metrics";
            auth_basic_user_file /etc/nginx/.htpasswd;

            proxy_pass http://enhanced-cognee-server:9090/metrics;
        }

        # Health check (no auth required)
        location /health {
            proxy_pass http://cognee_backend/health;
            access_log off;
        }
    }
}
```

#### Step 5: Create Monitoring Password

```bash
# Create password for metrics endpoint
htpasswd -c monitoring/htpasswd admin
```

#### Step 6: Initialize Databases

```bash
# Start databases only
docker-compose -f docker/docker-compose-production.yml up -d postgres-enhanced qdrant-enhanced neo4j-enhanced redis-enhanced

# Wait for databases to be healthy (30 seconds)
sleep 30

# Run database initialization
docker exec cognee-postgres-prod psql -U cognee_user -d cognee_db -f /docker/init-db.sql

# Verify databases are running
docker-compose ps
```

#### Step 7: Deploy Application

```bash
# Deploy full stack
docker-compose -f docker/docker-compose-production.yml up -d

# Check logs
docker-compose -f docker/docker-compose-production.yml logs -f enhanced-cognee-server

# Verify health
curl http://localhost:8000/health
```

#### Step 8: Verify Deployment

```bash
# 1. Check all containers are running
docker-compose -f docker/docker-compose-production.yml ps

# 2. Check health endpoint
curl https://your-domain.com/health

# 3. Test metrics endpoint
curl -u admin:PASSWORD https://your-domain.com/metrics

# 4. Check Grafana
# Open: https://your-domain.com:3000
# Login: admin / (GRAFANA_PASSWORD)

# 5. Check Prometheus targets
# Open: http://your-server:9091/targets
```

## Rolling Updates

### Update Application Without Downtime

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild image
docker-compose -f docker/docker-compose-production.yml build enhanced-cognee-server

# 3. Rolling update (zero downtime)
docker-compose -f docker/docker-compose-production.yml up -d enhanced-cognee-server

# The application will update while existing connections complete
```

### Database Migrations

```bash
# Run migrations during update
docker exec cognee-postgres-prod psql -U cognee_user -d cognee_db -f /docker/migrations/001_add_new_table.sql
```

## Backup & Recovery

### Automated Backups

Create `scripts/backup.sh`:

```bash
#!/bin/bash
# Enhanced Cognee Production Backup Script

BACKUP_DIR="/backups/cognee"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting backup at $(date)"

# PostgreSQL backup
docker exec cognee-postgres-prod pg_dump -U cognee_user cognee_db | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Qdrant backup (snapshot)
docker exec cognee-qdrant-prod curl -X POST http://localhost:6333/collections/cognee_general_memory/snapshots

# Redis backup
docker exec cognee-redis-prod redis-cli --rdb /data/dump_$DATE.rdb SAVE

# Neo4j backup
docker exec cognee-neo4j-prod neo4j-admin backup --from=/data --to=$BACKUP_DIR/neo4j_$DATE

echo "Backup completed at $(date)"

# Upload to S3 (optional)
# aws s3 sync "$BACKUP_DIR" s3://your-backup-bucket/cognee/
```

### Restore from Backup

```bash
# Restore PostgreSQL
gunzip -c /backups/cognee/postgres_YYYYMMDD_HHMMSS.sql.gz | docker exec -i cognee-postgres-prod psql -U cognee_user cognee_db

# Restore Qdrant (manually create snapshot)
# Via Qdrant REST API

# Restore Redis
docker cp /backups/cognee/dump_YYYYMMDD_HHMMSS.rdb cognee-redis-prod:/data/dump.rdb
docker restart cognee-redis-prod

# Restore Neo4j
docker exec cognee-neo4j-prod neo4j-admin restore --from=$BACKUP_DIR/neo4j_YYYYMMDD_HHMMSS --to=/data
```

## Monitoring Verification

After deployment, verify monitoring is working:

```bash
# Check Prometheus targets
curl http://localhost:9091/api/v1/targets | jq

# Check Prometheus metrics
curl http://localhost:9091/metrics | grep cognee

# Verify alerts are loaded
curl http://localhost:9091/api/v1/rules | jq

# Check Grafana dashboards
curl -u admin:PASSWORD http://localhost:3000/api/search?query=cognee
```

## Scaling Guide

### Horizontal Scaling

To handle increased load, you can scale the MCP servers:

```bash
# Scale to 3 instances
docker-compose -f docker/docker-compose-production.yml up -d --scale enhanced-cognee-server=3

# Behind Nginx load balancer, traffic will distribute automatically
```

### Vertical Scaling

Update resource limits in `docker-compose-production.yml`:

```yaml
services:
  postgres-enhanced:
    deploy:
      resources:
        limits:
          cpus: '4.0'      # Increase from 2.0
          memory: 4G      # Increase from 2G
```

Then restart:
```bash
docker-compose -f docker/docker-compose-production.yml up -d postgres-enhanced
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker/docker-compose-production.yml logs enhanced-cognee-server

# Check container status
docker-compose -f docker/docker-compose-production.yml ps

# Check resource usage
docker stats
```

### Database Connection Issues

```bash
# Verify database is running
docker exec cognee-postgres-prod pg_isready -U cognee_user

# Check network connectivity
docker network inspect enhanced-cogne_cognee-network

# Test from application container
docker exec cognee-server-prod ping postgres-enhanced
```

### High Memory Usage

```bash
# Check container memory
docker stats --no-stream

# Restart container
docker-compose -f docker/docker-compose-production.yml restart enhanced-cognee-server

# Check for memory leaks (connect to Grafana dashboard)
```

## Security Checklist

Before going to production, verify:

- [ ] All passwords changed from defaults
- [ ] SSL certificate is valid
- [ ] Firewall configured (only ports 80, 443 exposed)
- [ ] Rate limiting enabled
- [ ] Authentication required
- [ ] Monitoring and alerting active
- [ ] Backup automation configured
- [ ] Log aggregation working
- [ ] Incident response plan documented

## Production Runbook

### Daily Operations

**Morning (9:00 AM)**
- Check Grafana dashboard for overnight issues
- Review alert notifications
- Verify backup completion

**Weekly**
- Review performance trends
- Check disk space usage
- Update security patches
- Review and rotate logs

**Monthly**
- Test backup restoration
- Security audit
- Capacity planning
- Performance optimization review

### Incident Response

1. **Detection**: Alert triggered from monitoring
2. **Assessment**: Log into Grafana, check dashboard
3. **Isolation**: Identify affected service
4. **Resolution**: Apply fix or rollback
5. **Recovery**: Verify service restored
6. **Post-Mortem**: Document incident

## Support

For issues or questions:
- Documentation: https://github.com/your-org/enhanced-cognee/docs
- Issues: https://github.com/your-org/enhanced-cognee/issues
- Email: support@your-domain.com

---

**Last Updated**: 2026-02-06
**Version**: 1.0.0
