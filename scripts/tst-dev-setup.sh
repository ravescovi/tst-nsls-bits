#!/bin/bash

# TST NSLS-II BITS Development Environment Setup
# Enhanced version of the original setup-dev-env.sh with better management

set -e  # Exit on any command failure

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
VENV_DIR="${PROJECT_ROOT}/venv"
OVERLAYS_DIR="${PROJECT_ROOT}/overlays"

# Development repositories to clone and install
declare -a CORE_REPOS=(
    "ophyd-async"
    "bluesky"
    "event-model"
    "tiled"
    "nslsii"
    "bluesky-queueserver"
    "bluesky-widgets"
    "bluesky-queueserver-api"
)

# Additional TST-specific repositories
declare -a TST_REPOS=(
    # Add any TST-specific repositories here
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if Python version is available
check_python() {
    if ! command -v "python${PYTHON_VERSION}" &> /dev/null; then
        error "Python ${PYTHON_VERSION} is not installed or not in PATH"
    fi
    log "Using Python $(python${PYTHON_VERSION} --version)"
}

# Clean existing environment
clean_environment() {
    log "Cleaning existing development environment"

    if [ -d "${VENV_DIR}" ]; then
        warn "Removing existing virtual environment: ${VENV_DIR}"
        rm -rf "${VENV_DIR}"
    fi

    if [ -d "${OVERLAYS_DIR}" ]; then
        warn "Removing existing overlays directory: ${OVERLAYS_DIR}"
        rm -rf "${OVERLAYS_DIR}"
    fi
}

# Create virtual environment
create_venv() {
    log "Creating virtual environment in ${VENV_DIR}"
    mkdir -p "${VENV_DIR}"
    "python${PYTHON_VERSION}" -m venv "${VENV_DIR}"

    # Activate virtual environment
    source "${VENV_DIR}/bin/activate"

    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    log "Virtual environment created and activated"
}

# Install base requirements
install_base_requirements() {
    log "Installing base requirements"

    # Install TST BITS package in development mode
    pip install -e "${PROJECT_ROOT}[dev]"

    log "Base requirements installed"
}

# Clone and install development repositories
install_dev_repos() {
    log "Setting up development overlays in ${OVERLAYS_DIR}"
    mkdir -p "${OVERLAYS_DIR}"
    cd "${OVERLAYS_DIR}"

    local repos=("${CORE_REPOS[@]}" "${TST_REPOS[@]}")
    local total=${#repos[@]}
    local current=0

    for repo in "${repos[@]}"; do
        current=$((current + 1))
        info "[$current/$total] Processing repository: $repo"

        if [ -d "$repo" ]; then
            warn "Repository $repo already exists, skipping clone"
            cd "$repo"
        else
            log "Cloning https://github.com/bluesky/$repo"
            if ! git clone "https://github.com/bluesky/$repo"; then
                warn "Failed to clone $repo, skipping"
                continue
            fi
            cd "$repo"
        fi

        # Install in development mode
        log "Installing $repo in development mode"
        if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
            if pip install -e ".[dev]" 2>/dev/null || pip install -e . 2>/dev/null; then
                log "Successfully installed $repo"
            else
                warn "Failed to install $repo, continuing"
            fi
        else
            warn "No setup.py or pyproject.toml found in $repo"
        fi

        cd "${OVERLAYS_DIR}"
    done

    cd "${PROJECT_ROOT}"
    log "Development repositories setup complete"
}

# Create activation script
create_activation_script() {
    local activate_script="${PROJECT_ROOT}/activate-dev.sh"

    cat > "$activate_script" << 'EOF'
#!/bin/bash
# TST NSLS-II BITS Development Environment Activation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

if [ ! -d "${VENV_DIR}" ]; then
    echo "Error: Virtual environment not found at ${VENV_DIR}"
    echo "Run ./scripts/tst-dev-setup.sh to create the development environment"
    return 1
fi

source "${VENV_DIR}/bin/activate"

# Set environment variables for development
export TST_DEV_MODE="YES"
export TST_MOCK_MODE="YES"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

echo "TST NSLS-II BITS Development Environment Activated"
echo "Virtual environment: ${VENV_DIR}"
echo "Project root: ${SCRIPT_DIR}"
echo ""
echo "Available commands:"
echo "  tst-bits          - Launch IPython with TST instrument"
echo "  ./scripts/tiled-serve.sh - Start Tiled server"
echo "  pre-commit run --all-files - Run code quality checks"
echo ""
echo "To deactivate: deactivate"
EOF

    chmod +x "$activate_script"
    log "Created activation script: $activate_script"
}

# Setup pre-commit hooks
setup_pre_commit() {
    log "Setting up pre-commit hooks"

    if command -v pre-commit &> /dev/null; then
        pre-commit install
        log "Pre-commit hooks installed"
    else
        warn "pre-commit not found, install with: pip install pre-commit"
    fi
}

# Display completion message
show_completion() {
    log "Development environment setup complete!"
    echo ""
    echo "To activate the development environment:"
    echo "  source activate-dev.sh"
    echo ""
    echo "To test the installation:"
    echo "  source activate-dev.sh"
    echo "  tst-bits"
    echo ""
    echo "To start the Tiled server:"
    echo "  ./scripts/tiled-serve.sh"
    echo ""
    echo "To run quality checks:"
    echo "  pre-commit run --all-files"
}

# Usage information
usage() {
    cat << EOF
TST NSLS-II BITS Development Environment Setup

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -p, --python VERSION    Python version to use (default: 3.11)
    -c, --clean             Clean existing environment before setup
    --no-overlays          Skip cloning development repositories
    --no-pre-commit        Skip pre-commit setup
    --dry-run              Show what would be done without executing

Examples:
    $0                      # Standard setup
    $0 -c                   # Clean setup
    $0 -p 3.10              # Use Python 3.10
    $0 --no-overlays        # Skip development repositories

EOF
}

# Parse command line arguments
CLEAN=false
NO_OVERLAYS=false
NO_PRECOMMIT=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -p|--python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        --no-overlays)
            NO_OVERLAYS=true
            shift
            ;;
        --no-pre-commit)
            NO_PRECOMMIT=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            error "Unknown option: $1. Use -h for help."
            ;;
    esac
done

# Main execution
main() {
    log "Setting up TST NSLS-II BITS development environment"
    log "Project root: ${PROJECT_ROOT}"
    log "Python version: ${PYTHON_VERSION}"

    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN - Would perform the following actions:"
        log "  - Check Python ${PYTHON_VERSION}"
        [ "$CLEAN" = true ] && log "  - Clean existing environment"
        log "  - Create virtual environment in ${VENV_DIR}"
        log "  - Install base requirements"
        [ "$NO_OVERLAYS" = false ] && log "  - Clone and install development repositories"
        log "  - Create activation script"
        [ "$NO_PRECOMMIT" = false ] && log "  - Setup pre-commit hooks"
        exit 0
    fi

    check_python

    if [ "$CLEAN" = true ]; then
        clean_environment
    fi

    create_venv
    install_base_requirements

    if [ "$NO_OVERLAYS" = false ]; then
        install_dev_repos
    fi

    create_activation_script

    if [ "$NO_PRECOMMIT" = false ]; then
        setup_pre_commit
    fi

    show_completion
}

# Handle interrupts gracefully
cleanup() {
    warn "Setup interrupted, cleaning up..."
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate
    fi
    exit 1
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@"
