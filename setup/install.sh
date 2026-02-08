#!/bin/bash
#
# Enhanced Cognee Installation Script for Linux/Mac
#
# This script installs Enhanced Cognee in one command.
# Supports both Full and Lite installation modes.
#
# Usage:
#   ./install.sh              # Interactive mode
#   ./install.sh --mode full   # Full mode (all databases)
#   ./install.sh --mode lite   # Lite mode (SQLite only)
#   ./install.sh --help        # Show help
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_MODE="full"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Enhanced Cognee Installation${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        print_info "Please install Python 3.10 or higher"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_info "Python version: $PYTHON_VERSION"

    # Check if Python version is >= 3.10
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
        print_error "Python 3.10 or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed"
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."

    cd "$PROJECT_ROOT"

    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
    else
        # Install core dependencies
        pip3 install \
            asyncpg \
            qdrant-client \
            neo4j \
            redis \
            tiktoken \
            anthropic \
            openai \
            python-dotenv \
            pydantic \
            fastapi \
            uvicorn \
            mcp
    fi

    print_success "Python dependencies installed"
}

# Install Docker dependencies (Full mode only)
install_docker() {
    if [ "$INSTALL_MODE" != "full" ]; then
        print_info "Skipping Docker installation (Lite mode)"
        return
    fi

    print_step "Checking Docker installation..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_warn "Docker is not installed"
        print_info "Installing Docker..."

        # Detect OS
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            print_info "Detected Linux"
            print_info "Please install Docker manually:"
            print_info "  https://docs.docker.com/engine/install/"
            exit 1
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            print_info "Detected macOS"
            print_info "Please install Docker Desktop:"
            print_info "  https://www.docker.com/products/docker-desktop/"
            exit 1
        else
            print_error "Unsupported OS: $OSTYPE"
            exit 1
        fi
    fi

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running"
        print_info "Please start Docker and try again"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi

    print_success "Docker installation verified"
}

# Run setup wizard
run_setup_wizard() {
    print_step "Running setup wizard..."

    cd "$PROJECT_ROOT"

    python3 setup_wizard.py

    print_success "Setup wizard completed"
}

# Start services
start_services() {
    print_step "Starting Enhanced Cognee services..."

    cd "$PROJECT_ROOT"

    if [ "$INSTALL_MODE" == "full" ]; then
        # Start Docker services
        print_info "Starting databases with Docker..."
        docker compose -f docker/docker-compose-enhanced-cognee.yml up -d
    fi

    print_success "Services started"
}

# Run pre-flight checks
run_preflight() {
    print_step "Running pre-flight checks..."

    cd "$PROJECT_ROOT"

    python3 preflight.py

    print_success "Pre-flight checks completed"
}

# Create CLI symlink
create_cli_symlink() {
    print_step "Creating CLI command..."

    CLI_SCRIPT="$PROJECT_ROOT/enhanced-cognee"

    if [ ! -f "$CLI_SCRIPT" ]; then
        print_error "CLI script not found: $CLI_SCRIPT"
        return
    fi

    # Make executable
    chmod +x "$CLI_SCRIPT"

    # Ask if user wants to create symlink
    read -p "Create symlink to /usr/local/bin? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo ln -sf "$CLI_SCRIPT" /usr/local/bin/enhanced-cognee
        print_success "Symlink created: /usr/local/bin/enhanced-cognee"
    else
        print_info "You can run Enhanced Cognee with: $CLI_SCRIPT"
    fi
}

# Print completion message
print_completion() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "Enhanced Cognee is ready to use!"
    echo ""
    echo "Quick Start:"
    echo "  1. Check status:"
    echo "     $ $PYTHON_CMD preflight.py"
    echo ""
    echo "  2. Start services:"
    echo "     $ ./enhanced-cognee start"
    echo ""
    echo "  3. View logs:"
    echo "     $ ./enhanced-cognee logs"
    echo ""
    echo "For more information, see README.md"
    echo ""
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                INSTALL_MODE="$2"
                shift 2
                ;;
            --help)
                echo "Enhanced Cognee Installation Script"
                echo ""
                echo "Usage:"
                echo "  ./install.sh [options]"
                echo ""
                echo "Options:"
                echo "  --mode <mode>  Installation mode (full or lite) [default: full]"
                echo "  --help         Show this help message"
                echo ""
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Validate INSTALL_MODE
    if [[ "$INSTALL_MODE" != "full" && "$INSTALL_MODE" != "lite" ]]; then
        print_error "Invalid installation mode: $INSTALL_MODE"
        exit 1
    fi
}

# Main installation flow
main() {
    print_header

    print_info "Installation mode: $INSTALL_MODE"
    echo ""

    # Parse arguments
    parse_args "$@"

    # Run installation steps
    check_prerequisites
    install_python_deps

    if [ "$INSTALL_MODE" == "full" ]; then
        install_docker
    fi

    run_setup_wizard
    start_services
    run_preflight
    create_cli_symlink

    print_completion
}

# Run main
main "$@"
