#!/bin/bash
# Setup Environment Script for AI Interviewer
# This script sets up the complete development environment on a new machine

set -e  # Exit on error

echo "🚀 AI Interviewer - Environment Setup"
echo "======================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    print_error "Conda is not installed!"
    echo "Please install Miniconda or Anaconda first:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

print_success "Conda found: $(conda --version)"
echo ""

# Ask user which setup method they want
echo "Choose setup method:"
echo "  1) Full environment (exact replication with all 161 packages)"
echo "  2) Minimal environment (only essential packages)"
echo "  3) Quick setup (latest versions from requirements.txt)"
echo ""
read -p "Enter choice (1/2/3): " SETUP_CHOICE

ENV_NAME="pipecat-env"

case $SETUP_CHOICE in
    1)
        print_info "Setting up FULL environment from environment.yml..."
        if [ -f "environment.yml" ]; then
            conda env create -f environment.yml -n $ENV_NAME
            print_success "Full environment created!"
        else
            print_error "environment.yml not found!"
            exit 1
        fi
        ;;
    2)
        print_info "Setting up MINIMAL environment..."
        conda create -n $ENV_NAME python=3.12 -y
        conda activate $ENV_NAME
        
        # Install only essential packages
        print_info "Installing server dependencies..."
        pip install -r server/requirements.txt
        
        print_info "Installing web server dependencies..."
        pip install -r web_server/requirements.txt
        
        print_success "Minimal environment created!"
        ;;
    3)
        print_info "Setting up QUICK environment (latest versions)..."
        if [ -f "requirements-all.lock" ]; then
            conda create -n $ENV_NAME python=3.12 -y
            conda activate $ENV_NAME
            pip install -r requirements-all.lock
            print_success "Environment created from lock file!"
        else
            print_warning "Lock file not found, using requirements.txt instead..."
            conda create -n $ENV_NAME python=3.12 -y
            conda activate $ENV_NAME
            pip install -r server/requirements.txt
            pip install -r web_server/requirements.txt
            print_success "Environment created from requirements.txt!"
        fi
        ;;
    *)
        print_error "Invalid choice!"
        exit 1
        ;;
esac

echo ""
print_success "Environment setup complete!"
echo ""

# Check if .env files exist
print_info "Checking environment configuration files..."
if [ ! -f "server/.env" ]; then
    print_warning "server/.env not found. Copying from env.example..."
    cp server/env.example server/.env
    print_warning "Please edit server/.env with your API keys!"
fi

if [ ! -f "web_server/.env" ]; then
    print_warning "web_server/.env not found. Copying from env.example..."
    cp web_server/env.example web_server/.env
    print_warning "Please edit web_server/.env with your API keys!"
fi

echo ""
print_info "To activate the environment, run:"
echo "  conda activate $ENV_NAME"
echo ""

print_info "To start the web server, run:"
echo "  conda activate $ENV_NAME"
echo "  cd web_server"
echo "  uvicorn main:app --reload --port 8009"
echo ""

print_info "To verify the installation, run:"
echo "  conda activate $ENV_NAME"
echo "  python -c 'import pipecat, cartesia, fastapi; print(\"✅ All packages imported successfully!\")'"
echo ""

print_success "Setup complete! Happy coding! 🎉"

