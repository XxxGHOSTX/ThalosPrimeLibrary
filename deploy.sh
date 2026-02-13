#!/bin/bash
# Quick deployment script for Thalos Prime Library
# This script automates the deployment process

set -e  # Exit on error

echo "=========================================="
echo "Thalos Prime Library - Quick Deploy"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
info "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    success "Python $PYTHON_VERSION found"
else
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Ask deployment type
echo ""
echo "Select deployment method:"
echo "1) Install as Python package (editable mode)"
echo "2) Install as Python package (production mode)"
echo "3) Run API server (development)"
echo "4) Run API server (production with Gunicorn)"
echo "5) Docker deployment"
echo "6) Run tests"
echo ""
read -p "Enter your choice [1-6]: " choice

case $choice in
    1)
        info "Installing in editable mode..."
        pip install -e ".[dev]"
        success "Installation complete!"
        echo ""
        info "Try: python example_usage.py"
        ;;
    2)
        info "Installing in production mode..."
        pip install .
        success "Installation complete!"
        ;;
    3)
        info "Starting development server..."
        if [ ! -f "run_thalos.py" ]; then
            warning "run_thalos.py not found, using uvicorn directly"
            pip install -e .
            uvicorn thalos_prime.api.server:app --host 127.0.0.1 --port 8000 --reload
        else
            python run_thalos.py
        fi
        ;;
    4)
        info "Starting production server with Gunicorn..."
        pip install gunicorn
        pip install .
        gunicorn thalos_prime.api.server:app \
            --workers 4 \
            --worker-class uvicorn.workers.UvicornWorker \
            --bind 0.0.0.0:8000 \
            --log-level info
        ;;
    5)
        info "Docker deployment..."
        if ! command -v docker &> /dev/null; then
            echo "Error: Docker is not installed"
            exit 1
        fi
        
        if [ -f "docker-compose.yml" ]; then
            info "Using Docker Compose..."
            docker-compose up --build
        else
            info "Building Docker image..."
            docker build -t thalos-prime:latest .
            success "Docker image built!"
            info "Starting container..."
            docker run -p 8000:8000 --name thalos-prime thalos-prime:latest
        fi
        ;;
    6)
        info "Running tests..."
        pip install -e ".[dev]"
        python -m pytest tests -v
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
success "Done!"
