#!/bin/bash
#
# Enhanced Cognee Uninstallation Script for Linux/Mac
#
# This script stops all services and optionally removes Docker volumes.
#
# Usage:
#   ./uninstall.sh              # Stop services only
#   ./uninstall.sh --cleanup    # Stop and remove all data
#   ./uninstall.sh --help       # Show help
#
# Author: Enhanced Cognee Team
# Version: 1.0.0
# Date: 2026-02-06

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
CLEANUP_VOLUMES=false
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose-enhanced-cognee.yml"

# Functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  Enhanced Cognee Uninstallation${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

confirm_action() {
    read -p "This action cannot be undone. Continue? (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

stop_services() {
    print_info "Stopping Enhanced Cognee services..."

    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_warn "Docker compose file not found: $DOCKER_COMPOSE_FILE"
        return
    fi

    cd "$PROJECT_ROOT"
    docker compose -f "$DOCKER_COMPOSE_FILE" down

    print_success "Services stopped"
}

cleanup_volumes() {
    if [ "$CLEANUP_VOLUMES" = false ]; then
        return
    fi

    print_warn "This will permanently delete all Enhanced Cognee data!"

    if ! confirm_action; then
        print_info "Volume cleanup cancelled"
        return
    fi

    print_info "Removing Docker volumes..."

    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "Docker compose file not found: $DOCKER_COMPOSE_FILE"
        return
    fi

    cd "$PROJECT_ROOT"
    docker compose -f "$DOCKER_COMPOSE_FILE" down -v

    print_success "Volumes removed"
}

remove_cli_symlink() {
    print_info "Removing CLI symlink..."

    if [ -L "/usr/local/bin/enhanced-cognee" ]; then
        sudo rm /usr/local/bin/enhanced-cognee
        print_success "Symlink removed"
    else
        print_info "No symlink found"
    fi
}

print_completion() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Uninstallation Complete${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "Enhanced Cognee services have been stopped."
    echo ""

    if [ "$CLEANUP_VOLUMES" = true ]; then
        echo "All data has been permanently deleted."
    else
        echo "Docker volumes have been preserved."
        echo "To remove data later, run:"
        echo "  $ ./uninstall.sh --cleanup"
    fi

    echo ""
    echo "To reinstall Enhanced Cognee, run:"
    echo "  $ ./install.sh"
    echo ""
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                CLEANUP_VOLUMES=true
                shift
                ;;
            --help)
                echo "Enhanced Cognee Uninstallation Script"
                echo ""
                echo "Usage:"
                echo "  ./uninstall.sh [options]"
                echo ""
                echo "Options:"
                echo "  --cleanup    Remove Docker volumes (deletes all data)"
                echo "  --help       Show this help message"
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
}

# Main flow
main() {
    print_header

    if [ "$CLEANUP_VOLUMES" = true ]; then
        print_warn "CLEANUP MODE: All data will be deleted!"
        echo ""
    fi

    if ! confirm_action; then
        print_info "Uninstall cancelled"
        exit 0
    fi

    parse_args "$@"

    stop_services
    cleanup_volumes
    remove_cli_symlink

    print_completion
}

main "$@"
