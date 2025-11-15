#!/bin/bash
# Setup Python Virtual Environment for AI Interviewer
# Pure pip approach - NO conda required

set -e  # Exit on error

echo "🚀 AI Interviewer - Virtual Environment Setup (Pure Pip)"
echo "========================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if Python 3.12 is available
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    print_success "Found Python 3.12: $(python3.12 --version)"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    # Check if Python 3.10 or higher
    if [[ "$MAJOR" -eq 3 ]] && [[ "$MINOR" -ge 10 ]]; then
        PYTHON_CMD="python3"
        print_success "Found Python: $(python3 --version)"
    else
        print_error "Python 3.10+ required. Found: Python $PYTHON_VERSION"
        echo "Please install Python 3.10 or higher from: https://www.python.org/downloads/"
        exit 1
    fi
else
    print_error "Python 3 not found!"
    echo "Please install Python 3.10 or higher from: https://www.python.org/downloads/"
    exit 1
fi

echo ""

# Set virtual environment directory
VENV_DIR="venv"

# Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    print_warning "Virtual environment already exists at: $VENV_DIR"
    read -p "Do you want to recreate it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        print_info "Using existing virtual environment"
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
        exit 0
    fi
fi

# Create virtual environment
print_info "Creating virtual environment with $PYTHON_CMD..."
$PYTHON_CMD -m venv "$VENV_DIR"
print_success "Virtual environment created at: $VENV_DIR"

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

echo ""

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "Pip upgraded to: $(pip --version)"

echo ""

# Ask user which installation method
echo "Choose installation method:"
echo "  1) Install from requirements.txt (recommended - latest compatible versions)"
echo "  2) Install from lock file (exact versions - if available)"
echo ""
read -p "Enter choice (1/2, default=1): " INSTALL_CHOICE
INSTALL_CHOICE=${INSTALL_CHOICE:-1}

case $INSTALL_CHOICE in
    1)
        print_info "Installing server dependencies..."
        pip install -r server/requirements.txt
        
        print_info "Installing web server dependencies..."
        pip install -r web_server/requirements.txt
        
        print_success "Packages installed!"
        ;;
    2)
        if [ -f "requirements-all.lock" ]; then
            print_info "Installing packages from lock file..."
            if pip install -r requirements-all.lock; then
                print_success "Packages installed from lock file!"
            else
                print_warning "Lock file installation failed (dependency conflicts)"
                print_info "Falling back to requirements.txt..."
                pip install -r server/requirements.txt
                pip install -r web_server/requirements.txt
                print_success "Packages installed from requirements.txt!"
            fi
        else
            print_warning "Lock file not found. Installing from requirements.txt instead..."
            print_info "Installing server dependencies..."
            pip install -r server/requirements.txt
            print_info "Installing web server dependencies..."
            pip install -r web_server/requirements.txt
            print_success "Packages installed!"
        fi
        ;;
    *)
        print_error "Invalid choice!"
        exit 1
        ;;
esac

echo ""
print_success "Installation complete!"

# Generate new lock file
print_info "Generating lock file for future use..."
pip freeze > requirements-all.lock
print_success "Lock file updated: requirements-all.lock"

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
print_success "Setup complete! 🎉"
echo ""

print_info "To activate the environment in future sessions:"
echo "  source venv/bin/activate"
echo ""

print_info "To start the application:"
echo "  ./start.sh"
echo ""

print_info "To verify the installation:"
echo "  source venv/bin/activate"
echo "  python -c 'import pipecat, cartesia, fastapi; print(\"✅ All packages imported successfully!\")'"
echo ""

print_warning "Don't forget to edit .env files with your API keys!"
echo "  • server/.env"
echo "  • web_server/.env"
echo ""

