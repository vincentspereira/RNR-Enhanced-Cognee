# RNR Enhanced Cognee Phase 1 Setup Guide

## 🎯 Overview

This guide walks you through the complete setup of Phase 1 of the RNR Enhanced Cognee testing framework. Phase 1 focuses on establishing the foundation infrastructure, testing tools, and basic configuration needed for comprehensive testing.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows with WSL2
- **RAM**: Minimum 8GB, recommended 16GB
- **Storage**: Minimum 50GB free disk space
- **CPU**: Multi-core processor recommended

### Software Requirements
- **Docker**: Version 20.10+ with Docker Compose
- **Python**: Version 3.9+ with pip
- **Git**: For version control
- **Node.js**: Version 18+ (for some testing tools)

### Network Requirements
- **Ports**: Ensure the following ports are available:
  - 25432 (PostgreSQL)
  - 26333 (Qdrant)
  - 27474 (Neo4j)
  - 26379 (Redis)
  - 28080 (RNR Enhanced Cognee API)
  - 29090 (Prometheus)
  - 29300 (Grafana)

## 🚀 Quick Start

### 1. Clone Repository and Navigate
```bash
cd "C:\Users\vince\Projects\AI Agents\RNR Enhanced Cognee"
```

### 2. Run Automated Setup
```bash
# Make setup script executable (Linux/macOS)
chmod +x testing/scripts/setup_phase1.sh

# Run the setup script
./testing/scripts/setup_phase1.sh
```

### 3. Verify Setup
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run basic tests
cd testing
pytest -m "unit and not slow" -v
```

## 📚 Manual Setup Instructions

If you prefer to set up manually or encounter issues with the automated script:

### Step 1: Environment Preparation

#### Install Dependencies
```bash
# Update package manager
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# or
brew update && brew upgrade              # macOS

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Python 3.9+
sudo apt install python3.9 python3.9-pip python3.9-venv  # Ubuntu/Debian
# or
brew install python@3.9                            # macOS
```

### Step 2: Python Environment Setup

#### Create Virtual Environment
```bash
# Create virtual environment
python3.9 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

#### Install Testing Dependencies
```bash
# Install testing framework
pip install -r testing/requirements.txt

# Install RNR Enhanced Cognee in development mode
pip install -e .
```

### Step 3: Docker Infrastructure Setup

#### Create Docker Networks
```bash
# Create testing network
docker network create testing-network

# Create monitoring network
docker network create monitoring-network
```

#### Create Necessary Directories
```bash
# Create directory structure
mkdir -p testing/reports/{coverage,performance,security,compliance,junit}
mkdir -p testing/data/{test_scenarios,test_data,performance_data}
mkdir -p testing/logs/{testing,monitoring,security}
```

### Step 4: Start Testing Infrastructure

#### Start Database Services
```bash
cd testing

# Start core databases
docker-compose -f docker-compose-testing.yml up -d \
    postgres-test \
    qdrant-test \
    neo4j-test \
    redis-test

# Wait for services to be ready
echo "Waiting for databases to start..."
sleep 30
```

#### Verify Database Connections
```bash
# Test PostgreSQL
docker exec enhanced-cognee-postgres-test pg_isready -U test_user -d test_cognee

# Test Qdrant
curl -f http://localhost:26333/health

# Test Redis
redis-cli -h localhost -p 26379 ping

# Test Neo4j
curl -f http://localhost:27474
```

### Step 5: Setup Monitoring Stack

#### Start Monitoring Services
```bash
# Start Prometheus and Grafana
docker-compose -f docker-compose-testing.yml up -d \
    prometheus-test \
    grafana-test

# Wait for monitoring services
echo "Waiting for monitoring services..."
sleep 20
```

#### Verify Monitoring
```bash
# Test Prometheus
curl -f http://localhost:29090/-/healthy

# Test Grafana
curl -f http://localhost:29300/api/health
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=25432
POSTGRES_DB=test_cognee
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password

QDRANT_HOST=localhost
QDRANT_PORT=26333

NEO4J_URI=bolt://localhost:27687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test_password

REDIS_HOST=localhost
REDIS_PORT=26379
REDIS_PASSWORD=test_password

# RNR Enhanced Cognee Configuration
ENHANCED_COGNEE_PORT=28080
LOG_LEVEL=INFO
TESTING_MODE=true

# Testing Configuration
TEST_CONCURRENT_AGENTS=100
TEST_MEMORY_OPS=1000
API_TIMEOUT=30
CLEANUP_AFTER_TEST=true

# Performance Testing
PERFORMANCE_TESTS_ENABLED=true
LOCUST_USERS=100
LOCUST_SPAWN_RATE=10
LOCUST_RUN_TIME=10m

# Security Testing
SECURITY_TESTS_ENABLED=true
ZAP_API_KEY=zap-test-api-key

# Chaos Testing
CHAOS_TESTS_ENABLED=false

# Monitoring
PROMETHEUS_HOST=localhost
PROMETHEUS_PORT=29090
GRAFANA_HOST=localhost
GRAFANA_PORT=29300
```

### Database Initialization

Run database initialization scripts:

```bash
# Activate virtual environment
source venv/bin/activate

# Initialize database schemas
python scripts/init_test_databases.py

# Or use Alembic if available
alembic upgrade head
```

## 🧪 Verification Testing

### Run Basic Tests

```bash
cd testing
source ../venv/bin/activate

# Test database connectivity
pytest -m "unit and requires_database" -v

# Test API endpoints
pytest -m "integration and not slow" -v

# Test configuration
pytest -m "unit and test_config" -v
```

### Manual Verification

#### Test Database Connections
```python
# Test script: test_connections.py
import asyncio
import asyncpg
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
import redis

async def test_connections():
    # Test PostgreSQL
    conn = await asyncpg.connect(
        host="localhost",
        port=25432,
        database="test_cognee",
        user="test_user",
        password="test_password"
    )
    await conn.execute("SELECT 1")
    await conn.close()
    print("✅ PostgreSQL connection successful")

    # Test Qdrant
    client = QdrantClient(host="localhost", port=26333)
    collections = client.get_collections()
    print("✅ Qdrant connection successful")

    # Test Neo4j
    driver = GraphDatabase.driver(
        "bolt://localhost:27687",
        auth=("neo4j", "test_password")
    )
    driver.verify_connectivity()
    driver.close()
    print("✅ Neo4j connection successful")

    # Test Redis
    r = redis.Redis(host="localhost", port=26379, password="test_password")
    r.ping()
    print("✅ Redis connection successful")

# Run test
asyncio.run(test_connections())
```

## 📊 Access Points

### Web Interfaces

- **RNR Enhanced Cognee API**: http://localhost:28080
- **API Documentation**: http://localhost:28080/docs
- **Prometheus**: http://localhost:29090
- **Grafana**: http://localhost:29300
  - Username: admin
  - Password: test_admin
- **Neo4j Browser**: http://localhost:27474
  - Username: neo4j
  - Password: test_password

### Database Endpoints

- **PostgreSQL**: localhost:25432
- **Qdrant HTTP API**: http://localhost:26333
- **Qdrant gRPC**: localhost:26334
- **Neo4j Bolt**: localhost:27687
- **Redis**: localhost:26379

## 🔍 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using ports
netstat -tulpn | grep :25432
netstat -tulpn | grep :26333

# Kill processes if needed
sudo kill -9 <PID>
```

#### Docker Issues
```bash
# Check Docker logs
docker-compose -f docker-compose-testing.yml logs postgres-test
docker-compose -f docker-compose-testing.yml logs qdrant-test

# Restart services
docker-compose -f docker-compose-testing.yml restart

# Clean up and restart
docker-compose -f docker-compose-testing.yml down -v
docker-compose -f docker-compose-testing.yml up -d
```

#### Python Environment Issues
```bash
# Rebuild virtual environment
rm -rf venv
python3.9 -m venv venv
source venv/bin/activate
pip install -r testing/requirements.txt
pip install -e .
```

#### Permission Issues
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER

# Fix file permissions
chmod -R 755 testing/
chmod +x testing/scripts/*.sh
```

### Health Checks

#### Service Status Script
```bash
#!/bin/bash
# health_check.sh

echo "🔍 RNR Enhanced Cognee Infrastructure Health Check"

# Check Docker services
echo "Docker Services:"
docker-compose -f testing/docker-compose-testing.yml ps

# Check port availability
echo -e "\nPort Availability:"
for port in 25432 26333 27474 26379 28080 29090 29300; do
    if nc -z localhost $port; then
        echo "✅ Port $port is open"
    else
        echo "❌ Port $port is closed"
    fi
done

# Check resource usage
echo -e "\nResource Usage:"
docker stats --no-stream
```

## 📈 Next Steps

### After Phase 1 Setup

1. **Run Initial Tests**
   ```bash
   cd testing
   pytest -m "unit or integration" -v --cov-report=html
   ```

2. **Start RNR Enhanced Cognee API**
   ```bash
   cd ..
   python -m cognee.api
   ```

3. **Run Performance Tests**
   ```bash
   cd testing
   locust --headless --host=http://localhost:28080 --users=10 --spawn-rate=1
   ```

4. **Explore Monitoring**
   - Open Grafana: http://localhost:29300
   - View Prometheus metrics: http://localhost:29090
   - Check alerting rules

### Phase 2 Preparation

Phase 2 will focus on implementing core testing components:

1. **Unit Tests**: Comprehensive unit testing for all components
2. **Integration Tests**: Component interaction testing
3. **System Tests**: End-to-end workflow testing
4. **Performance Tests**: Load and stress testing
5. **Security Tests**: Vulnerability assessment

## 📚 Additional Resources

- **Full Testing Strategy**: `docs/testing/COMPREHENSIVE_TESTING_STRATEGY.md`
- **Implementation Roadmap**: `docs/testing/IMPLEMENTATION_ROADMAP.md`
- **Test Scenarios**: `docs/testing/TEST_SCENARIOS.md`
- **API Documentation**: http://localhost:28080/docs
- **Grafana Dashboards**: http://localhost:29300

---

## 💬 Support

If you encounter issues during setup:

1. Check the setup logs: `testing/logs/setup.log`
2. Review Docker logs: `docker-compose logs`
3. Check the troubleshooting section above
4. Create an issue in the project repository

*Last Updated: 2025-11-13*
*RNR Enhanced Cognee Testing Framework*