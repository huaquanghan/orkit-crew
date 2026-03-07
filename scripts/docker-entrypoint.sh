#!/bin/bash
set -e

# Docker entrypoint script for orkit-crew

# Function to check if required environment variables are set
check_env() {
    local missing=()
    
    if [[ -z "${PLANNO_URL:-}" ]]; then
        missing+=("PLANNO_URL")
    fi
    
    if [[ -z "${PLANNO_API_KEY:-}" ]]; then
        missing+=("PLANNO_API_KEY")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "WARNING: Missing environment variables: ${missing[*]}"
        echo "Some features may not work correctly."
    fi
}

# Function to setup directories
setup_dirs() {
    # Create necessary directories
    mkdir -p /app/sessions /app/workspace
    
    # Ensure proper permissions (if running as root)
    if [[ "$(id -u)" == "0" ]]; then
        chown -R orkit:orkit /app/sessions /app/workspace 2>/dev/null || true
    fi
}

# Main entrypoint logic
main() {
    echo "Starting orkit-crew..."
    
    # Setup directories
    setup_dirs
    
    # Check environment
    check_env
    
    # Handle different commands
    case "${1:-}" in
        "shell"|"bash"|"sh")
            exec /bin/bash
            ;;
        "plan")
            shift
            exec orkit plan "$@"
            ;;
        "code")
            shift
            exec orkit code "$@"
            ;;
        "chat")
            exec orkit chat
            ;;
        "serve"|"api"|"server")
            echo "Starting API server on port 8000..."
            # If there's an API server command, use it
            # Otherwise show help
            exec orkit --help
            ;;
        ""|"help")
            exec orkit --help
            ;;
        *)
            exec orkit "$@"
            ;;
    esac
}

# Run main function
main "$@"
