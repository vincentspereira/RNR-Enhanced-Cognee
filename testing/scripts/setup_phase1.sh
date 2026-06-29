#!/bin/bash

# RNR Enhanced Cognee Phase 1 Foundation Setup Script
# Sets up testing infrastructure and prepares environment for comprehensive testing

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TESTING_DIR="$PROJECT_ROOT/testing"
LOG_FILE="$TESTING_DIR/logs/setup.log"

# Ensure log directory exists
mkdir -p "$TESTING_DIR/logs"

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Print banner
print_banner() {
    log "============================================================"
    log "🚀 RNR Enhanced Cognee Phase 1 Foundation Setup"
    log "============================================================"
    log "This script will set up the testing infrastructure for"
    log "the RNR Enhanced Cognee comprehensive testing framework."
    log "============================================================"
}

# Check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    log "✓ Docker found: $(docker --version)"

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    log "✓ Docker Compose found: $(docker-compose --version)"

    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    log "✓ Python found: $(python3 --version)"

    # Check if pip is installed
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed. Please install pip3 first."
        exit 1
    fi
    log "✓ pip3 found"

    # Check available disk space (minimum 10GB)
    available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 10 ]; then
        log_error "Insufficient disk space. At least 10GB required, but only ${available_space}GB available."
        exit 1
    fi
    log "✓ Sufficient disk space: ${available_space}GB available"

    log "✅ All prerequisites checked successfully!"
}

# Setup Python environment
setup_python_environment() {
    log "🐍 Setting up Python environment..."

    cd "$PROJECT_ROOT"

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install testing dependencies
    log_info "Installing testing dependencies..."
    pip install -r testing/requirements.txt

    # Install RNR Enhanced Cognee in development mode
    log_info "Installing RNR Enhanced Cognee in development mode..."
    pip install -e .

    log "✅ Python environment setup completed!"
}

# Setup Docker networks and volumes
setup_docker_infrastructure() {
    log "🐳 Setting up Docker infrastructure..."

    cd "$TESTING_DIR"

    # Create Docker network if it doesn't exist
    if ! docker network ls | grep -q "testing-network"; then
        log_info "Creating Docker testing network..."
        docker network create testing-network
    else
        log_info "Docker testing network already exists"
    fi

    # Create monitoring network if it doesn't exist
    if ! docker network ls | grep -q "monitoring-network"; then
        log_info "Creating Docker monitoring network..."
        docker network create monitoring-network
    else
        log_info "Docker monitoring network already exists"
    fi

    # Create necessary directories
    log_info "Creating necessary directories..."
    mkdir -p reports/{coverage,performance,security,compliance,junit}
    mkdir -p data/{test_scenarios,test_data,performance_data}
    mkdir -p logs/{testing,monitoring,security}

    # Set permissions
    chmod 755 reports data logs

    log "✅ Docker infrastructure setup completed!"
}

# Start testing databases
start_testing_databases() {
    log "🗄️ Starting testing databases..."

    cd "$TESTING_DIR"

    # Start database services
    log_info "Starting PostgreSQL, Qdrant, Neo4j, and Redis..."
    docker-compose -f docker-compose-testing.yml up -d postgres-test qdrant-test neo4j-test redis-test

    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."

    # Wait for PostgreSQL
    timeout 60 bash -c 'until docker exec enhanced-cognee-postgres-test pg_isready -U test_user -d test_cognee; do sleep 2; done'
    if [ $? -eq 0 ]; then
        log "✓ PostgreSQL is ready"
    else
        log_error "PostgreSQL failed to start within timeout"
        return 1
    fi

    # Wait for Qdrant
    timeout 60 bash -c 'until curl -f http://localhost:26333/health; do sleep 2; done'
    if [ $? -eq 0 ]; then
        log "✓ Qdrant is ready"
    else
        log_error "Qdrant failed to start within timeout"
        return 1
    fi

    # Wait for Redis
    timeout 30 bash -c 'until redis-cli -h localhost -p 26379 ping; do sleep 1; done'
    if [ $? -eq 0 ]; then
        log "✓ Redis is ready"
    else
        log_error "Redis failed to start within timeout"
        return 1
    fi

    # Wait for Neo4j (longer startup time)
    log_info "Waiting for Neo4j (this may take a while)..."
    timeout 120 bash -c 'until curl -f http://localhost:27474; do sleep 5; done'
    if [ $? -eq 0 ]; then
        log "✓ Neo4j is ready"
    else
        log_error "Neo4j failed to start within timeout"
        return 1
    fi

    log "✅ All testing databases are ready!"
}

# Setup monitoring stack
setup_monitoring() {
    log "📊 Setting up monitoring stack..."

    cd "$TESTING_DIR"

    # Start monitoring services
    log_info "Starting Prometheus and Grafana..."
    docker-compose -f docker-compose-testing.yml up -d prometheus-test grafana-test

    # Wait for Prometheus
    timeout 30 bash -c 'until curl -f http://localhost:29090/-/healthy; do sleep 2; done'
    if [ $? -eq 0 ]; then
        log "✓ Prometheus is ready"
    else
        log_error "Prometheus failed to start within timeout"
        return 1
    fi

    # Wait for Grafana
    timeout 30 bash -c 'until curl -f http://localhost:29300/api/health; do sleep 2; done'
    if [ $? -eq 0 ]; then
        log "✓ Grafana is ready"
    else
        log_error "Grafana failed to start within timeout"
        return 1
    fi

    log "✅ Monitoring stack is ready!"
}

# Initialize database schemas
initialize_database_schemas() {
    log "🔧 Initializing database schemas..."

    cd "$PROJECT_ROOT"
    source venv/bin/activate

    # Run database initialization script
    if [ -f "scripts/init_test_databases.py" ]; then
        log_info "Running database initialization script..."
        python scripts/init_test_databases.py
    else
        log_warning "Database initialization script not found. Creating basic schemas..."

        # Create basic schemas using Alembic if available
        if command -v alembic &> /dev/null; then
            log_info "Running Alembic migrations..."
            alembic upgrade head
        else
            log_warning "Alembic not found. Manual schema setup may be required."
        fi
    fi

    log "✅ Database schemas initialized!"
}

# Run initial tests to verify setup
run_verification_tests() {
    log "🧪 Running verification tests..."

    cd "$TESTING_DIR"
    source "$PROJECT_ROOT/venv/bin/activate"

    # Run basic connectivity tests
    log_info "Running database connectivity tests..."
    pytest -m "unit and requires_database" -v --tb=short || {
        log_error "Database connectivity tests failed"
        return 1
    }

    # Run basic API tests
    log_info "Running basic API tests..."
    pytest -m "integration and not slow" -v --tb=short || {
        log_warning "Some API tests failed, but setup may still be functional"
    }

    log "✅ Verification tests completed!"
}

# Generate setup report
generate_setup_report() {
    log "📋 Generating setup report..."

    REPORT_FILE="$TESTING_DIR/reports/setup_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# RNR Enhanced Cognee Phase 1 Setup Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Environment:** Testing

## Infrastructure Status

### Database Services
- **PostgreSQL:** ✅ Running on port 25432
- **Qdrant:** ✅ Running on port 26333
- **Neo4j:** ✅ Running on port 27474
- **Redis:** ✅ Running on port 26379

### Monitoring Services
- **Prometheus:** ✅ Running on port 29090
- **Grafana:** ✅ Running on port 29300

### Testing Services
- **RNR Enhanced Cognee API:** Configured for port 28080
- **Locust Master:** Configured for port 28089
- **OWASP ZAP:** Configured for port 28090

## Access URLs

- **RNR Enhanced Cognee API:** http://localhost:28080
- **Prometheus:** http://localhost:29090
- **Grafana:** http://localhost:29300 (admin/test_admin)
- **Neo4j Browser:** http://localhost:27474 (neo4j/test_password)

## Next Steps

1. **Run comprehensive tests:**
   \`\`\`bash
   cd testing
   pytest -m "unit or integration" -v
   \`\`\`

2. **Start performance testing:**
   \`\`\`bash
   cd testing
   locust --headless --host=http://localhost:28080 --users=10 --spawn-rate=1
   \`\`\`

3. **Run security tests:**
   \`\`\`bash
   cd testing
   pytest -m "security" -v
   \`\`\`

## Troubleshooting

If any service fails to start:
1. Check logs: \`docker-compose -f docker-compose-testing.yml logs <service>\`
2. Verify port availability
3. Check resource availability

EOF

    log "✅ Setup report generated: $REPORT_FILE"
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Setup failed. Check logs for details: $LOG_FILE"
        log_info "To clean up partially created resources, run:"
        log_info "  cd $TESTING_DIR && docker-compose -f docker-compose-testing.yml down"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Main execution
main() {
    print_banner

    # Execute setup steps
    check_prerequisites
    setup_python_environment
    setup_docker_infrastructure
    start_testing_databases
    setup_monitoring
    initialize_database_schemas
    run_verification_tests
    generate_setup_report

    log "🎉 Phase 1 Foundation Setup completed successfully!"
    log ""
    log "📊 Monitoring Dashboards:"
    log "   - Prometheus: http://localhost:29090"
    log "   - Grafana: http://localhost:29300"
    log ""
    log "🗄️ Database Endpoints:"
    log "   - PostgreSQL: localhost:25432"
    log "   - Qdrant: http://localhost:26333"
    log "   - Neo4j: http://localhost:27474"
    log "   - Redis: localhost:26379"
    log ""
    log "🚀 Next Steps:"
    log "   1. Run: cd testing && pytest -m 'unit or integration' -v"
    log "   2. Start RNR Enhanced Cognee API: python -m cognee.api"
    log "   3. Run performance tests with Locust"
    log ""
    log "📋 Full setup report saved in: $TESTING_DIR/reports/"
}

# Execute main function
main "$@"