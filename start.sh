#!/bin/bash
# AI Interviewer - Start All Services with Live Logs
# Pure pip/venv approach - NO conda required

echo "🚀 Starting AI Interviewer with Live Logs..."
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up processes...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run setup first:"
    echo "  ./setup-venv.sh"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}🐍 Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "   ${GREEN}✅ Using Python: $(which python)${NC}"
echo -e "   ${GREEN}✅ Version: $(python --version)${NC}"

# 1. Start Redis
echo -e "\n${BLUE}1️⃣ Starting Redis...${NC}"
if docker ps | grep -q redis-ai-interviewer; then
    echo "   ✅ Redis container already running"
elif docker ps -a | grep -q redis-ai-interviewer; then
    docker start redis-ai-interviewer > /dev/null 2>&1
    echo "   ✅ Started existing Redis container"
else
    docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest > /dev/null 2>&1
    echo "   ✅ Created and started Redis container"
fi

# Verify Redis
sleep 2
if redis-cli ping > /dev/null 2>&1 || docker exec redis-ai-interviewer redis-cli ping > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Redis is ready${NC}"
else
    echo -e "   ${RED}❌ Redis failed to start${NC}"
    exit 1
fi

# 2. Start RQ Worker with live logs
echo -e "\n${BLUE}2️⃣ Starting RQ Worker (with live logs)...${NC}"
cd web_server

# Start RQ worker in background but pipe to tee for live viewing
rq worker ai_bots --with-scheduler 2>&1 | tee /tmp/rq_worker.log &
RQ_PID=$!
echo "   Worker PID: $RQ_PID"
sleep 2

# 3. Start Web Server with live logs
echo -e "\n${BLUE}3️⃣ Starting Web Server (with live logs)...${NC}"

# Start web server in background but pipe to tee for live viewing
python main.py 2>&1 | tee /tmp/web_server.log &
WEB_PID=$!
echo "   Server PID: $WEB_PID"
sleep 3

cd ..

# 4. Verify services
echo -e "\n${BLUE}4️⃣ Verifying services...${NC}"
redis-cli ping > /dev/null 2>&1 && echo -e "   ${GREEN}✅ Redis: Running${NC}" || echo -e "   ${RED}❌ Redis: Failed${NC}"

if ps -p $RQ_PID > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ RQ Worker: Running (PID: $RQ_PID)${NC}"
else
    echo -e "   ${RED}❌ RQ Worker: Failed${NC}"
fi

if curl -s http://localhost:8009/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Web Server: Running (PID: $WEB_PID)${NC}"
else
    echo -e "   ${RED}❌ Web Server: Failed${NC}"
fi

# 5. Show live logs
echo -e "\n${GREEN}🎉 AI Interviewer is ready!${NC}"
echo "============================================"
echo -e "${BLUE}📊 Dashboard:${NC} http://localhost:8009/dashboard"
echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8009/docs"
echo ""
echo -e "${YELLOW}📝 Live Logs (Ctrl+C to stop):${NC}"
echo "   Web Server: tail -f /tmp/web_server.log"
echo "   RQ Worker:  tail -f /tmp/rq_worker.log"
echo ""
echo -e "${YELLOW}💡 To view live logs in separate terminals:${NC}"
echo "   Terminal 1: tail -f /tmp/web_server.log"
echo "   Terminal 2: tail -f /tmp/rq_worker.log"
echo ""
echo -e "${YELLOW}🛑 To stop all services: Press Ctrl+C${NC}"
echo ""

# Show combined logs using tail -f with multiple files
echo -e "${BLUE}📋 Showing combined live logs (Ctrl+C to stop)...${NC}"
echo "============================================"
tail -f /tmp/web_server.log /tmp/rq_worker.log 2>/dev/null || {
    # If tail -f fails (files don't exist yet), wait a bit and try again
    sleep 2
    tail -f /tmp/web_server.log /tmp/rq_worker.log 2>/dev/null || {
        echo "Waiting for log files to be created..."
        sleep 3
        tail -f /tmp/web_server.log /tmp/rq_worker.log
    }
}
