#!/bin/bash
# Cross-platform script to run all code quality checks
# Usage: ./scripts/check_code.sh [type-check|lint|format|check-docs|check-all|fix]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Python is available
if ! command_exists python3 && ! command_exists python; then
    print_error "Python is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if ! command_exists pip3 && ! command_exists pip; then
    print_error "pip is not installed or not in PATH"
    exit 1
fi

# Get the command (default to check-all)
CMD=${1:-check-all}

case "$CMD" in
    type-check)
        print_info "Running type checking with mypy..."
        if command_exists mypy; then
            mypy src/ || print_warn "Type checking found some issues"
        else
            print_error "mypy is not installed. Run: pip install -r requirements-dev.txt"
            exit 1
        fi
        ;;
    
    lint)
        print_info "Running linting checks..."
        if command_exists ruff; then
            ruff check src/ || print_warn "Ruff found some issues"
        else
            print_error "ruff is not installed. Run: pip install -r requirements-dev.txt"
            exit 1
        fi
        if command_exists pylint; then
            pylint src/ || print_warn "Pylint found some issues"
        else
            print_warn "pylint is not installed. Skipping pylint check."
        fi
        ;;
    
    format)
        print_info "Formatting code with ruff..."
        if command_exists ruff; then
            ruff format src/
            print_info "Code formatting complete"
        else
            print_error "ruff is not installed. Run: pip install -r requirements-dev.txt"
            exit 1
        fi
        ;;
    
    check-docs)
        print_info "Checking docstring style with pydocstyle..."
        if command_exists pydocstyle; then
            pydocstyle src/ || print_warn "Docstring check found some issues"
        else
            print_error "pydocstyle is not installed. Run: pip install -r requirements-dev.txt"
            exit 1
        fi
        ;;
    
    check-all)
        print_info "Running all code quality checks..."
        "$0" type-check || true
        echo ""
        "$0" lint || true
        echo ""
        "$0" check-docs || true
        echo ""
        print_info "All checks complete!"
        ;;
    
    fix)
        print_info "Auto-fixing issues with ruff..."
        if command_exists ruff; then
            ruff check src/ --fix
            ruff format src/
            print_info "Auto-fix complete"
        else
            print_error "ruff is not installed. Run: pip install -r requirements-dev.txt"
            exit 1
        fi
        ;;
    
    *)
        print_error "Unknown command: $CMD"
        echo "Usage: $0 [type-check|lint|format|check-docs|check-all|fix]"
        exit 1
        ;;
esac

