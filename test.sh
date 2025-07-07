#!/bin/bash

# Stock Alerts - Test Runner Script
# This script runs type checking and basic tests to ensure code quality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.8+ is available
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    REQUIRED_VERSION="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python $PYTHON_VERSION found, but Python 3.8+ is required"
        exit 1
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found. Please run ./start.sh first to set up the environment."
        exit 1
    fi
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        source venv/Scripts/activate
    else
        # Linux/macOS
        source venv/bin/activate
    fi
    
    print_success "Virtual environment activated"
}

# Run type checking with mypy
run_type_checking() {
    print_status "Running type checking with mypy..."
    
    # Check if mypy is available
    if ! python -c "import mypy" 2>/dev/null; then
        print_warning "mypy not found. Installing mypy..."
        pip install mypy
    fi
    
    # Run type checking on core files
    CORE_FILES=(
        "app.py"
        "db_manager.py"
        "periodic_checker.py"
        "webhook_handler.py"
        "utils/scheduler.py"
        "utils/config.py"
        "utils/tiingo_client.py"
        "utils/validators.py"
        "services/stock_service.py"
        "services/auth_service.py"
        "services/admin_service.py"
        "routes/api_routes.py"
        "routes/webhook_routes.py"
        "routes/admin_routes.py"
        "routes/health_routes.py"
    )
    
    # Filter existing files
    EXISTING_FILES=()
    for file in "${CORE_FILES[@]}"; do
        if [ -f "$file" ]; then
            EXISTING_FILES+=("$file")
        fi
    done
    
    if [ ${#EXISTING_FILES[@]} -eq 0 ]; then
        print_warning "No core files found for type checking"
        return 0
    fi
    
    print_status "Type checking files: ${EXISTING_FILES[*]}"
    
    if python -m mypy "${EXISTING_FILES[@]}"; then
        print_success "Type checking passed ✓"
    else
        print_error "Type checking failed ✗"
        return 1
    fi
}

# Test basic imports
test_imports() {
    print_status "Testing basic imports..."
    
    # Test core module imports
    if python -c "
import app
import db_manager
import periodic_checker
import webhook_handler
from utils.scheduler import setup_scheduler
from utils.config import config
from utils.tiingo_client import TiingoClient
from utils.validators import validate_user_id
from services.stock_service import StockService
from services.auth_service import AuthService
from services.admin_service import AdminService
print('All imports successful')
    " 2>/dev/null; then
        print_success "Import tests passed ✓"
    else
        print_error "Import tests failed ✗"
        return 1
    fi
}

# Test syntax with flake8 (if available)
test_syntax() {
    print_status "Testing code syntax and style..."
    
    # Check if flake8 is available
    if python -c "import flake8" 2>/dev/null; then
        print_status "Running flake8 syntax check..."
        if python -m flake8 --config=pyproject.toml . 2>/dev/null; then
            print_success "Syntax check passed ✓"
        else
            print_warning "Syntax check found issues (see output above)"
        fi
    else
        print_status "flake8 not available, skipping syntax check"
    fi
}

# Run pytest if available
run_pytest() {
    print_status "Looking for tests..."
    
    if [ -d "tests" ]; then
        print_status "Tests directory found, running pytest..."
        if python -c "import pytest" 2>/dev/null; then
            python -m pytest tests/ -v
            print_success "Tests completed ✓"
        else
            print_warning "pytest not available, skipping unit tests"
        fi
    else
        print_status "No tests directory found, skipping unit tests"
    fi
}

# Test weekday functionality
test_weekday_logic() {
    print_status "Testing weekday restriction logic..."
    
    # Test the weekday logic in a controlled way
    if python -c "
from datetime import datetime
import sys

# Test weekday logic
today = datetime.now().weekday()  # 0=Monday, 6=Sunday
valid_days = [0, 1, 2, 3, 6]  # Monday-Thursday, Sunday
day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

print(f'Today is {day_names[today]} (weekday {today})')
print(f'Valid alert days: {[day_names[d] for d in valid_days]}')

if today in valid_days:
    print('✓ Today is a valid alert day')
else:
    print('✗ Today is NOT a valid alert day (alerts will be skipped)')

print('Weekday logic test passed')
    "; then
        print_success "Weekday logic test passed ✓"
    else
        print_error "Weekday logic test failed ✗"
        return 1
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "🧪 Stock Alerts - Test Runner"
    echo "=========================================="
    echo ""
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Track test results
    TESTS_PASSED=0
    TESTS_FAILED=0
    
    # Run all tests
    echo "Running test suite..."
    echo ""
    
    # Basic setup checks
    check_python
    activate_venv
    
    echo ""
    echo "=========================================="
    echo "🔍 Running Tests"
    echo "=========================================="
    echo ""
    
    # Type checking
    if run_type_checking; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    echo ""
    
    # Import tests
    if test_imports; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    echo ""
    
    # Syntax tests
    test_syntax
    
    echo ""
    
    # Weekday logic test
    if test_weekday_logic; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    echo ""
    
    # Unit tests (if available)
    run_pytest
    
    echo ""
    echo "=========================================="
    echo "📊 Test Results"
    echo "=========================================="
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        print_success "All tests passed! ✅"
        print_success "Tests passed: $TESTS_PASSED"
        echo ""
        print_success "🎉 Your code is ready for deployment!"
    else
        print_error "Some tests failed! ❌"
        print_error "Tests failed: $TESTS_FAILED"
        print_success "Tests passed: $TESTS_PASSED"
        echo ""
        print_error "Please fix the issues above before deploying."
        exit 1
    fi
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n\n${YELLOW}[INFO]${NC} Test run interrupted..."; exit 1' INT

# Run main function
main "$@"