#!/bin/bash

# Stock Alerts - One-Click Startup Script
# This script sets up the environment and launches the web dashboard

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

# Create and activate virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
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

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Check environment configuration
check_env() {
    print_status "Checking environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warning ".env file not found. Creating from .env.example..."
            cp .env.example .env
            print_warning "Please edit .env file with your Telegram bot token and other settings"
            print_warning "You can continue running for web dashboard only, but Telegram bot won't work"
        else
            print_warning "No .env file found. Some features may not work properly."
        fi
    else
        print_success "Environment configuration found"
    fi
}

# Create necessary directories
setup_directories() {
    print_status "Setting up directories..."
    
    mkdir -p logs
    mkdir -p db
    mkdir -p static/js
    
    print_success "Directories created"
}

# Start the application
start_app() {
    print_status "Starting Stock Alerts Dashboard..."
    print_status "Setting up database and initializing application..."
    
    # Get port from environment or use default
    PORT=${PORT:-5001}
    
    print_success "🚀 Starting Stock Alerts Dashboard on port $PORT"
    print_success "📊 Web Dashboard: http://localhost:$PORT"
    print_success "📱 Bot commands: /start, /add, /list, /remove, /help"
    print_success ""
    print_status "Press Ctrl+C to stop the application"
    print_status "Logs are being written to logs/stock_alerts.log"
    
    # Start the Flask application
    python app.py
}

# Main execution
main() {
    echo "=========================================="
    echo "🚀 Stock Alerts - One-Click Startup"
    echo "=========================================="
    echo ""
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    check_python
    setup_venv
    install_dependencies
    check_env
    setup_directories
    
    echo ""
    echo "=========================================="
    echo "✅ Setup Complete - Starting Application"
    echo "=========================================="
    echo ""
    
    start_app
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n\n${YELLOW}[INFO]${NC} Shutting down Stock Alerts Dashboard..."; exit 0' INT

# Run main function
main "$@"