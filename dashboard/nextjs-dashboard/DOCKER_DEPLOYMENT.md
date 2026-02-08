# Enhanced Cognee Dashboard - Docker Deployment Guide

**Status:** [OK] All dependencies are LOCAL (not global)

---

## Overview

This guide explains how to run the Enhanced Cognee Dashboard using Docker containers. All dependencies (Node.js, Python, databases) are installed locally within containers - **no global installations required**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Next.js     │  │   FastAPI    │  │   Nginx      │         │
│  │  Dashboard   │──│   Backend    │──│   (Proxy)    │         │
│  │  Port: 3000  │  │  Port: 8000  │  │  Port: 80    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                                  │
│         └──────────────────┴──────────────────┐                │
│                                                 ▼                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │   Qdrant     │  │    Neo4j     │         │
│  │  Port: 25432 │  │  Port: 26333 │  │  Port: 27687 │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐                                               │
│  │    Redis     │                                               │
│  │  Port: 26379 │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

**Docker Desktop** or **Docker Engine** installed:
- Windows: Install Docker Desktop from https://www.docker.com/products/docker-desktop/
- Linux: Install Docker Engine following official docs

**No Node.js, Python, or database installations required** - everything runs in containers!

---

## Quick Start

### 1. Start All Services

```bash
cd C:\Users\vince\Projects\AI Agents\enhanced-cognee\dashboard
docker compose -f docker-compose-dashboard.yml up -d
```

This starts:
- PostgreSQL (port 25432)
- Qdrant (port 26333)
- Neo4j (port 27474, 27687)
- Redis (port 26379)
- FastAPI Backend (port 8000)
- Next.js Dashboard (port 3000)

### 2. Verify Services are Running

```bash
# Check all containers
docker ps

# Check logs
docker compose -f docker-compose-dashboard.yml logs -f

# Check service health
curl http://localhost:8000/health  # Backend API
curl http://localhost:9050         # Frontend Dashboard
```

### 3. Access the Application

- **Dashboard:** http://localhost:9050
- **API Documentation:** http://localhost:8000/docs (Swagger UI)
- **Neo4j Browser:** http://localhost:27474
- **Qdrant Console:** http://localhost:26333/dashboard

---

## Environment Configuration

Create a `.env` file in the `dashboard/` directory:

```bash
# Database Passwords
POSTGRES_PASSWORD=your-secure-postgres-password
NEO4J_PASSWORD=your-secure-neo4j-password

# API Security
JWT_SECRET=your-jwt-secret-key-min-32-chars
API_KEY=your-api-key-for-authentication

# CORS (allowed origins)
CORS_ORIGINS=http://localhost:9050,http://localhost:8000

# Application URL
APP_URL=http://localhost:9050
```

**Security Note:** Change these passwords in production!

---

## Container Management

### View Logs

```bash
# All services
docker compose -f docker-compose-dashboard.yml logs -f

# Specific service
docker compose -f docker-compose-dashboard.yml logs -f dashboard
docker compose -f docker-compose-dashboard.yml logs -f backend-api
docker compose -f docker-compose-dashboard.yml logs -f postgres
```

### Stop Services

```bash
docker compose -f docker-compose-dashboard.yml down
```

### Stop and Remove Volumes (⚠️ Deletes Data)

```bash
docker compose -f docker-compose-dashboard.yml down -v
```

### Rebuild Services

```bash
# Rebuild dashboard
docker compose -f docker-compose-dashboard.yml build dashboard

# Rebuild backend API
docker compose -f docker-compose-dashboard.yml build backend-api

# Rebuild all
docker compose -f docker-compose-dashboard.yml build --no-cache
```

### Restart Services

```bash
docker compose -f docker-compose-dashboard.yml restart
```

---

## Development vs Production

### Development Mode

Run dashboard locally (not in Docker) for hot-reload:

```bash
# Start databases only
docker compose -f docker-compose-dashboard.yml up -d postgres qdrant neo4j redis backend-api

# Run dashboard locally
cd nextjs-dashboard
npm run dev
```

Now you can:
- Edit code and see changes immediately (hot module reload)
- Use browser DevTools
- Debug with VS Code

### Production Mode

Run everything in Docker:

```bash
# Start all services including Nginx
docker compose -f docker-compose-dashboard.yml --profile production up -d
```

This enables:
- Nginx reverse proxy (port 80, 443)
- Optimized builds
- Production-ready configuration

---

## Troubleshooting

### Issue: Port Already in Use

**Problem:** Port 9050, 8000, or 25432 already in use

**Solution:** Change ports in `docker-compose-dashboard.yml`:

```yaml
services:
  dashboard:
    ports:
      - "9060:9050"  # Use different external port
```

### Issue: Container Won't Start

**Problem:** Service fails to start

**Solution:** Check logs:

```bash
docker compose -f docker-compose-dashboard.yml logs [service-name]
```

### Issue: Database Connection Failed

**Problem:** Dashboard can't connect to backend

**Solution:** Verify environment variables:

```bash
# Check backend API logs
docker compose -f docker-compose-dashboard.yml logs backend-api

# Verify services are healthy
docker compose -f docker-compose-dashboard.yml ps
```

### Issue: Out of Memory

**Problem:** Containers crash due to memory limits

**Solution:** Increase Docker memory limit:
- Docker Desktop → Settings → Resources → Memory (4GB+ recommended)

---

## Data Persistence

All database data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep enhanced-cognee

# Backup PostgreSQL data
docker run --rm \
  -v postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz -C /data .

# Restore PostgreSQL data
docker run --rm \
  -v postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup.tar.gz -C /data
```

---

## Performance Optimization

### Build Optimization

```bash
# Use build cache for faster rebuilds
docker compose -f docker-compose-dashboard.yml build

# Parallel builds
DOCKER_BUILDKIT=1 docker compose -f docker-compose-dashboard.yml build
```

### Resource Limits

Add to `docker-compose-dashboard.yml`:

```yaml
services:
  dashboard:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## Security Best Practices

1. **Change Default Passwords**
   ```bash
   # Generate secure passwords
   openssl rand -base64 32
   ```

2. **Use Secrets in Production**
   ```bash
   echo "your-secret" | docker secret create jwt_secret -
   ```

3. **Enable HTTPS** (production)
   - Configure Nginx with SSL certificates
   - Use Let's Encrypt for free SSL

4. **Network Isolation**
   - Services run on private Docker network
   - Only necessary ports exposed

5. **Regular Updates**
   ```bash
   docker compose -f docker-compose-dashboard.yml pull
   docker compose -f docker-compose-dashboard.yml up -d
   ```

---

## Monitoring

### Health Checks

```bash
# Check service health
docker compose -f docker-compose-dashboard.yml ps

# All services should show "healthy" status
```

### Metrics

```bash
# Container resource usage
docker stats

# Database connections
docker exec postgres-enhanced-cognee psql -U cognee_user -d cognee_db -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Cleanup

### Remove All Containers and Volumes

```bash
docker compose -f docker-compose-dashboard.yml down -v
docker system prune -a
```

**⚠️ WARNING:** This deletes all data!

---

## Summary

**[OK] All Dependencies are Local**

- ✅ Node.js packages: `node_modules/` (within container)
- ✅ Python packages: Installed in container virtual environment
- ✅ Databases: Run as Docker containers
- ✅ No global installations required
- ✅ Isolated development environment
- ✅ Reproducible builds

**Quick Commands:**

```bash
# Start everything
docker compose -f docker-compose-dashboard.yml up -d

# View logs
docker compose -f docker-compose-dashboard.yml logs -f

# Stop everything
docker compose -f docker-compose-dashboard.yml down

# Rebuild
docker compose -f docker-compose-dashboard.yml build --no-cache
```

---

**Generated:** 2026-02-06
**Enhanced Cognee Dashboard Team**
**Status:** Docker deployment ready
