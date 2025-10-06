#!/bin/bash

# AI Interviewer - Quick Start Script
# Makes starting the system easier for solo development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════╗
║                                              ║
║       🤖 AI INTERVIEWER SYSTEM               ║
║                                              ║
╚══════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Function to print colored messages
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if MongoDB is running
check_mongodb() {
    info "Checking MongoDB..."
    if mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        success "MongoDB is running"
        return 0
    else
        error "MongoDB is not running!"
        echo ""
        echo "Start MongoDB with:"
        echo "  sudo systemctl start mongod"
        echo "Or:"
        echo "  mongod --dbpath /path/to/data"
        return 1
    fi
}

# Check environment files
check_env_files() {
    info "Checking environment files..."
    
    if [ ! -f "web_server/.env" ]; then
        error "web_server/.env not found!"
        echo "Copy from example: cp web_server/.env.example web_server/.env"
        return 1
    fi
    
    if [ ! -f "server/.env" ]; then
        error "server/.env not found!"
        echo "Copy from example: cp server/.env.example server/.env"
        return 1
    fi
    
    success "Environment files found"
    return 0
}

# Check Python dependencies
check_dependencies() {
    info "Checking Python dependencies..."
    
    if ! python3 -c "import fastapi" 2>/dev/null; then
        warning "FastAPI not installed"
        echo "Install: pip install -r web_server/requirements.txt"
        return 1
    fi
    
    success "Dependencies OK"
    return 0
}

# Main menu
show_menu() {
    echo ""
    echo "What would you like to do?"
    echo ""
    echo "  1) Start Web Server"
    echo "  2) Start AI Bot (with Interview ID)"
    echo "  3) Start Both (Web Server in background)"
    echo "  4) View Dashboard"
    echo "  5) Check System Status"
    echo "  6) View Database"
    echo "  7) Stop All Services"
    echo "  8) Exit"
    echo ""
    read -p "Enter choice [1-8]: " choice
    
    case $choice in
        1) start_web_server ;;
        2) start_ai_bot ;;
        3) start_both ;;
        4) open_dashboard ;;
        5) check_status ;;
        6) view_database ;;
        7) stop_services ;;
        8) exit 0 ;;
        *) 
            error "Invalid choice"
            show_menu
            ;;
    esac
}

# Start web server
start_web_server() {
    info "Starting Web Server..."
    cd web_server
    python main.py
}

# Start AI bot
start_ai_bot() {
    echo ""
    read -p "Enter Interview ID: " interview_id
    
    if [ -z "$interview_id" ]; then
        error "Interview ID required!"
        show_menu
        return
    fi
    
    info "Starting AI Bot for interview: $interview_id"
    cd server
    
    # Activate conda if available
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda activate pipecat-env
    fi
    
    WEB_SERVER_URL=http://localhost:8009 \
    INTERVIEW_ID=$interview_id \
    python ai-interviewer.py --transport daily
}

# Start both services
start_both() {
    info "Starting Web Server in background..."
    cd web_server
    nohup python main.py > ../logs/web_server.log 2>&1 &
    WEB_PID=$!
    success "Web Server started (PID: $WEB_PID)"
    
    sleep 3
    
    info "You can now start the AI Bot manually when needed"
    echo ""
    echo "To start AI Bot:"
    echo "  ./start.sh  (and choose option 2)"
    echo ""
    echo "To stop web server:"
    echo "  kill $WEB_PID"
    echo ""
    
    show_menu
}

# Open dashboard in browser
open_dashboard() {
    info "Opening dashboard..."
    
    # Check if web server is running
    if curl -s http://localhost:8009/health > /dev/null 2>&1; then
        success "Web server is running"
        
        # Try to open in browser
        if command -v xdg-open > /dev/null; then
            xdg-open http://localhost:8009/dashboard
        elif command -v open > /dev/null; then
            open http://localhost:8009/dashboard
        else
            echo "Open in browser: http://localhost:8009/dashboard"
        fi
    else
        error "Web server is not running!"
        echo "Start it first (option 1 or 3)"
    fi
    
    echo ""
    show_menu
}

# Check system status
check_status() {
    echo ""
    info "=== SYSTEM STATUS ==="
    echo ""
    
    # Check MongoDB
    if mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        success "MongoDB: Running"
    else
        error "MongoDB: Not Running"
    fi
    
    # Check Web Server
    if curl -s http://localhost:8009/health > /dev/null 2>&1; then
        success "Web Server: Running (http://localhost:8009)"
    else
        error "Web Server: Not Running"
    fi
    
    # Check interviews in database
    if mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        count=$(mongosh mongodb://localhost:27017/hire2inspire_dev_db \
            --quiet --eval "db.interview_results.countDocuments()" 2>/dev/null || echo "0")
        info "Interviews in Database: $count"
    fi
    
    echo ""
    show_menu
}

# View database
view_database() {
    info "Connecting to MongoDB..."
    mongosh mongodb://localhost:27017/hire2inspire_dev_db
    show_menu
}

# Stop all services
stop_services() {
    info "Stopping all services..."
    
    # Kill web server
    pkill -f "python.*main.py" && success "Web server stopped" || warning "No web server running"
    
    # Kill AI bot
    pkill -f "python.*ai-interviewer.py" && success "AI bot stopped" || warning "No AI bot running"
    
    echo ""
    show_menu
}

# Main script execution
main() {
    # Run checks
    check_mongodb || exit 1
    check_env_files || exit 1
    check_dependencies || warning "Some dependencies missing"
    
    success "All checks passed!"
    
    # Show menu
    show_menu
}

# Run main
main

