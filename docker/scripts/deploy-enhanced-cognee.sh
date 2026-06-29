#!/bin/bash

# RNR Enhanced Cognee Deployment Script
# Deploys enterprise-grade memory stack with Enhanced features
# Replaces: SQLite->PostgreSQL, LanceDB->Qdrant, Kuzu->Neo4j, adds Redis

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
COMPOSE_FILE="$PROJECT_DIR/docker-compose-enhanced-cognee.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Helper functions
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

check_docker_swarm() {
    if ! docker node ls &> /dev/null; then
        log_error "Docker Swarm is not initialized. Run 'docker swarm init' first"
        exit 1
    fi
    log_success "Docker Swarm is active"
}

create_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "Environment file not found. Creating from example..."
        if [[ -f "$PROJECT_DIR/.env.example" ]]; then
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
            log_warning "Please edit $ENV_FILE with your configuration before running again"
            exit 1
        else
            log_error ".env.example file not found"
            exit 1
        fi
    fi
}

validate_env_file() {
    log_info "Validating environment configuration..."

    # Required environment variables
    local required_vars=(
        "ENHANCED_COGNEE_MODE"
        "POSTGRES_PASSWORD"
        "NEO4J_PASSWORD"
        "LLM_API_KEY"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE" || grep -q "^${var}=.*your_.*_here" "$ENV_FILE"; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing or unset environment variables:"
        printf '  %s\n' "${missing_vars[@]}"
        log_error "Please set these in $ENV_FILE"
        exit 1
    fi

    log_success "Environment validation passed"
}

create_networks() {
    log_info "Creating Docker networks..."

    local networks=("cognee-network" "ats_network" "oma_network" "smc_network")

    for network in "${networks[@]}"; do
        if ! docker network ls --filter name=^"${network}"$ --format "{{.Name}}" | grep -q "^${network}$"; then
            log_info "Creating network: $network"
            docker network create --driver overlay --attachable "$network"
            log_success "Network $network created"
        else
            log_info "Network $network already exists"
        fi
    done
}

deploy_services() {
    log_info "Deploying RNR Enhanced Cognee services..."

    cd "$PROJECT_DIR"

    # Deploy base services first
    log_info "Deploying database services..."
    docker compose -f "$COMPOSE_FILE" up -d postgres qdrant neo4j redis

    # Wait for databases to be healthy
    log_info "Waiting for databases to be healthy..."
    sleep 30

    # Check database health
    local services=("postgres" "qdrant" "neo4j" "redis")
    for service in "${services[@]}"; do
        local health=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        if [[ "$health" != "healthy" ]]; then
            log_warning "$service health status: $health (continuing anyway)"
        else
            log_success "$service is healthy"
        fi
    done

    # Deploy RNR Enhanced Cognee services
    log_info "Deploying RNR Enhanced Cognee application..."
    docker compose -f "$COMPOSE_FILE" up -d enhanced-cognee enhanced-cognee-dashboard

    log_success "All services deployed"
}

verify_deployment() {
    log_info "Verifying deployment..."

    cd "$PROJECT_DIR"

    # Check if all services are running
    local services=("postgres" "qdrant" "neo4j" "redis" "enhanced-cognee" "enhanced-cognee-dashboard")
    local failed_services=()

    for service in "${services[@]}"; do
        if docker compose -f "$COMPOSE_FILE" ps -q "$service" | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null | grep -q "running"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
            failed_services+=("$service")
        fi
    done

    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "Failed services: ${failed_services[*]}"
        exit 1
    fi

    # Test connectivity
    log_info "Testing service connectivity..."

    # Test RNR Enhanced Cognee API
    if curl -f http://localhost:8080/health &>/dev/null; then
        log_success "RNR Enhanced Cognee API is accessible"
    else
        log_warning "RNR Enhanced Cognee API not yet ready (this is normal for first deployment)"
    fi

    # Test Dashboard
    if curl -f http://localhost:3000/health &>/dev/null; then
        log_success "RNR Enhanced Cognee Dashboard is accessible"
    else
        log_warning "RNR Enhanced Cognee Dashboard not yet ready (this is normal for first deployment)"
    fi

    log_success "Deployment verification completed"
}

show_status() {
    log_info "RNR Enhanced Cognee Deployment Status"
    echo "======================================="

    cd "$PROJECT_DIR"

    echo "Services Status:"
    docker compose -f "$COMPOSE_FILE" ps

    echo ""
    echo "Service URLs:"
    echo "- RNR Enhanced Cognee API:     http://localhost:8080"
    echo "- RNR Enhanced Cognee Dashboard: http://localhost:3000"
    echo "- PostgreSQL:               localhost:5432"
    echo "- Qdrant:                   http://localhost:6333"
    echo "- Neo4j Browser:            http://localhost:7474"
    echo "- Redis:                    localhost:6379"

    echo ""
    echo "Management Commands:"
    echo "- View logs:        docker compose -f $COMPOSE_FILE logs -f [service]"
    echo "- Stop services:    docker compose -f $COMPOSE_FILE down"
    echo "- Update services:  docker compose -f $COMPOSE_FILE pull && docker compose -f $COMPOSE_FILE up -d"
}

# Main deployment flow
main() {
    log_info "Starting RNR Enhanced Cognee deployment..."
    echo "Deploying enterprise-grade memory stack with Enhanced features"
    echo "Stack: PostgreSQL + pgVector, Qdrant, Neo4j, Redis + RNR Enhanced Cognee"
    echo ""

    # Pre-deployment checks
    check_docker
    check_docker_swarm

    # Environment setup
    create_env_file
    validate_env_file

    # Infrastructure setup
    create_networks

    # Deploy services
    deploy_services

    # Verify deployment
    verify_deployment

    # Show status
    show_status

    log_success "RNR Enhanced Cognee deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Access the dashboard at http://localhost:3000"
    echo "2. Configure your agents to use the Enhanced memory stack"
    echo "3. Monitor performance in the dashboard"
    echo ""
    echo "For troubleshooting, check logs with:"
    echo "docker compose -f $COMPOSE_FILE logs -f enhanced-cognee"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "status")
        show_status
        ;;
    "stop")
        log_info "Stopping RNR Enhanced Cognee services..."
        cd "$PROJECT_DIR"
        docker compose -f "$COMPOSE_FILE" down
        log_success "Services stopped"
        ;;
    "restart")
        log_info "Restarting RNR Enhanced Cognee services..."
        cd "$PROJECT_DIR"
        docker compose -f "$COMPOSE_FILE" restart
        log_success "Services restarted"
        ;;
    "logs")
        cd "$PROJECT_DIR"
        docker compose -f "$COMPOSE_FILE" logs -f "${2:-enhanced-cognee}"
        ;;
    "clean")
        log_warning "This will remove all RNR Enhanced Cognee services and data. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            cd "$PROJECT_DIR"
            docker compose -f "$COMPOSE_FILE" down -v
            docker system prune -f
            log_success "RNR Enhanced Cognee stack cleaned up"
        else
            log_info "Cleanup cancelled"
        fi
        ;;
    "help"|"-h"|"--help")
        echo "RNR Enhanced Cognee Deployment Script"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  deploy   Deploy RNR Enhanced Cognee stack (default)"
        echo "  status   Show deployment status"
        echo "  stop     Stop all services"
        echo "  restart  Restart all services"
        echo "  logs     Show logs for a service (default: enhanced-cognee)"
        echo "  clean    Remove all services and data (destructive)"
        echo "  help     Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 deploy                    # Deploy the stack"
        echo "  $0 logs enhanced-cognee      # Show RNR Enhanced Cognee logs"
        echo "  $0 status                    # Show deployment status"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac