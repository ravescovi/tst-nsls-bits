#!/bin/bash

# TST NSLS-II BITS Tiled Server Startup Script
# Enhanced version of the original tiled-serve.sh with better configuration management

set -e  # Exit on any command failure

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_API_KEY="e9fa22c35c4b7414e59d96c265ab46fabdfdea9046c78a88b5f390cea29f6b15"
STORAGE_DIR="${TILED_STORAGE_DIR:-/tmp/tiled_storage}"
DATA_ROOT="${TST_DATA_ROOT:-/nsls2/data/tst/}"
CATALOG_DB="${STORAGE_DIR}/catalog.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if tiled is available
check_tiled() {
    if ! command -v tiled &> /dev/null; then
        error "Tiled is not installed or not in PATH. Please install with: pip install tiled"
    fi
    log "Tiled found: $(tiled --version)"
}

# Setup storage directory
setup_storage() {
    log "Setting up storage directory: ${STORAGE_DIR}"
    
    # Clean and recreate storage directory
    if [ -d "${STORAGE_DIR}" ]; then
        warn "Removing existing storage directory"
        rm -rf "${STORAGE_DIR}"
    fi
    
    mkdir -p "${STORAGE_DIR}/data"
    log "Storage directory created: ${STORAGE_DIR}"
}

# Initialize catalog
init_catalog() {
    log "Initializing catalog database: ${CATALOG_DB}"
    tiled catalog init "sqlite+aiosqlite:///${CATALOG_DB}"
    log "Catalog initialized successfully"
}

# Set API key
setup_api_key() {
    if [ -n "${TILED_API_KEY}" ]; then
        log "Using TILED_API_KEY from environment"
    else
        export TILED_API_KEY="${DEFAULT_API_KEY}"
        warn "Using default API key. Set TILED_API_KEY environment variable for production"
    fi
}

# Check data root directory
check_data_root() {
    if [ ! -d "${DATA_ROOT}" ]; then
        warn "Data root directory does not exist: ${DATA_ROOT}"
        warn "Creating mock data directory for development"
        mkdir -p "${DATA_ROOT}"
    fi
    log "Data root directory: ${DATA_ROOT}"
}

# Start tiled server
start_server() {
    log "Starting Tiled server..."
    log "  Catalog: ${CATALOG_DB}"
    log "  Workspace: ${STORAGE_DIR}/data/"
    log "  Data root: ${DATA_ROOT}"
    log "  API Key: ${TILED_API_KEY:0:8}..."
    
    exec tiled serve catalog \
        "${CATALOG_DB}" \
        -w "${STORAGE_DIR}/data/" \
        --api-key="${TILED_API_KEY}" \
        -r "${DATA_ROOT}"
}

# Usage information
usage() {
    cat << EOF
TST NSLS-II BITS Tiled Server

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -s, --storage DIR       Set storage directory (default: /tmp/tiled_storage)
    -d, --data-root DIR     Set data root directory (default: /nsls2/data/tst/)
    -k, --api-key KEY       Set API key (default: use environment or built-in)
    -c, --clean             Clean existing storage before starting
    --dry-run              Show configuration without starting server

Environment Variables:
    TILED_STORAGE_DIR       Storage directory for catalog and workspace
    TST_DATA_ROOT          Root directory for TST data
    TILED_API_KEY          API key for authentication

Examples:
    $0                                 # Start with defaults
    $0 -s /data/tiled -d /nsls2/data/tst/  # Custom directories
    $0 --dry-run                       # Show configuration
    
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -s|--storage)
            STORAGE_DIR="$2"
            CATALOG_DB="${STORAGE_DIR}/catalog.db"
            shift 2
            ;;
        -d|--data-root)
            DATA_ROOT="$2"
            shift 2
            ;;
        -k|--api-key)
            export TILED_API_KEY="$2"
            shift 2
            ;;
        -c|--clean)
            # This is handled in setup_storage
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            error "Unknown option: $1. Use -h for help."
            ;;
    esac
done

# Main execution
main() {
    log "Starting TST NSLS-II BITS Tiled Server"
    
    check_tiled
    setup_api_key
    check_data_root
    setup_storage
    init_catalog
    
    if [ "${DRY_RUN:-0}" == "1" ]; then
        log "DRY RUN - Configuration:"
        log "  Storage: ${STORAGE_DIR}"
        log "  Catalog: ${CATALOG_DB}" 
        log "  Data root: ${DATA_ROOT}"
        log "  API key: ${TILED_API_KEY:0:8}..."
        exit 0
    fi
    
    start_server
}

# Handle interrupts gracefully
cleanup() {
    log "Shutting down Tiled server..."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@"