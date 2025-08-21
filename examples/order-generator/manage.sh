#!/bin/bash

# MockExchange Order Generator - Management Script
# Usage: ./manage.sh [COMMAND] [OPTIONS]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Container name
CONTAINER_NAME="order-generator"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== MockExchange Order Generator ===${NC}"
}

# Function to show help
show_help() {
    print_header
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start              Start the order generator without reset (builds Docker)"
    echo "  start --reset      Start the order generator with reset (builds Docker)"
    echo "  restart            Restart the order generator (no rebuild)"
    echo "  restart --reset    Restart with reset (no rebuild)"
    echo "  stop               Stop the order generator"
    echo "  logs               Show container logs"
    echo "  status             Show container status"
    echo "  help               Show this help message"
    echo ""
    echo "Options:"
    echo "  --reset            Reset backend state (clears all data)"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Fresh start without reset (builds Docker)"
    echo "  $0 start --reset   # Fresh start with reset (builds Docker)"
    echo "  $0 restart         # Continue without reset (no rebuild)"
    echo "  $0 restart --reset # Continue with reset (no rebuild)"
    echo "  $0 logs            # View logs"
    echo "  $0 stop            # Stop generator"
    echo "  $0 status          # Check status"
    echo ""
    echo "Prerequisites:"
    echo "  - MockX Engine running on http://localhost:8000"
    echo "  - MockX Oracle providing price feeds"
    echo "  - MockX Valkey (Redis) running"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "Created .env from .env.example"
            print_warning "Please edit .env with your API settings before starting"
        else
            print_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi
}

# Function to check if MockX Engine is running
check_engine() {
    if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_warning "MockX Engine doesn't seem to be running on http://localhost:8000"
        print_warning "Please start the MockExchange stack first: make start"
        print_warning "Or start individual services: make start-engine"
    fi
}

# Function to start (always builds Docker)
start_generator() {
    local reset_flag=$1

    print_status "Starting order generator (building Docker)..."
    check_docker
    check_env
    check_engine

    # Build and start
    docker compose build --no-cache

    if [ "$reset_flag" = "true" ]; then
        print_warning "Reset flag detected. This will clear backend state!"
        # Start with reset environment variable
        RESET_PORTFOLIO=true docker compose up -d
    else
        print_warning "Reset flag not detected. This will not clear backend state!"
        # Start without reset
        RESET_PORTFOLIO=false docker compose up -d
    fi

    print_status "Order generator started"
    print_status "Container name: $CONTAINER_NAME"
    print_status "View logs with: $0 logs"
    print_status "Check status with: $0 status"
}

# Function to stop
stop_generator() {
    print_status "Stopping order generator..."
    docker compose down
    print_status "Order generator stopped"
}

# Function to restart (no rebuild)
restart_generator() {
    local reset_flag=$1

    print_status "Restarting order generator (no rebuild)..."
    check_docker
    check_env
    check_engine

    # Stop first
    docker compose down

    if [ "$reset_flag" = "true" ]; then
        print_warning "Reset flag detected. This will clear backend state!"
        # Start with reset environment variable
        RESET_PORTFOLIO=true docker compose up -d
    else
        print_warning "Reset flag not detected. This will not clear backend state!"
        # Start without reset
        RESET_PORTFOLIO=false docker compose up -d
    fi

    print_status "Order generator restarted"
    print_status "View logs with: $0 logs"
    print_status "Check status with: $0 status"
}

# Function to show logs
show_logs() {
    print_status "Showing order generator logs..."
    docker logs -f $CONTAINER_NAME
}

# Function to show status
show_status() {
    print_status "Order generator status:"
    docker compose ps
    echo ""
    print_status "Container logs (last 10 lines):"
    docker logs --tail=10 $CONTAINER_NAME 2>/dev/null || print_warning "Container not running"
}

# Main script logic
main() {
    local command="${1:-help}"
    local option="${2:-}"

    case "$command" in
        start)
            local reset_flag="false"
            if [ "$option" = "--reset" ]; then
                reset_flag="true"
            fi
            start_generator "$reset_flag"
            ;;
        stop)
            stop_generator
            ;;
        restart)
            local reset_flag="false"
            if [ "$option" = "--reset" ]; then
                reset_flag="true"
            fi
            restart_generator "$reset_flag"
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
