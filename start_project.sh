#!/bin/bash

# AI Interviewer Project Startup Script
# This script starts the complete AI interviewer system

set -e  # Exit on any error

echo "🚀 Starting AI Interviewer Project"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port is already in use${NC}"
        echo "   Killing existing processes on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $service_name failed to start within $max_attempts seconds${NC}"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up processes...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Check and kill processes on required ports
echo -e "${BLUE}🔍 Checking ports...${NC}"
check_port 8009
check_port 7860

# Start Web Server
echo -e "${BLUE}🌐 Starting Web Server...${NC}"
cd /home/prashant/Playground/personal/consult/ai-interviewer/web_server

# Activate conda environment and start web server in background
(
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate base
    python main.py
) &

WEB_SERVER_PID=$!
echo "Web Server PID: $WEB_SERVER_PID"

# Wait for web server to be ready
if wait_for_service "http://localhost:8009/health" "Web Server"; then
    echo -e "${GREEN}✅ Web Server started successfully${NC}"
    echo -e "${BLUE}📊 Dashboard: http://localhost:8009/dashboard/${NC}"
    echo -e "${BLUE}📚 API Docs: http://localhost:8009/docs${NC}"
else
    echo -e "${RED}❌ Failed to start Web Server${NC}"
    exit 1
fi

# Start AI Interviewer Bot
echo -e "\n${BLUE}🤖 Starting AI Interviewer Bot...${NC}"
cd /home/prashant/Playground/personal/consult/ai-interviewer/server

# Generate unique interview ID
INTERVIEW_ID="interview_$(date +%Y%m%d_%H%M%S)"
echo -e "${YELLOW}🆔 Interview ID: $INTERVIEW_ID${NC}"

# Activate pipecat environment and start bot in background
(
    source ~/miniconda3/etc/profile.d/conda.sh
    conda activate pipecat-env
    WEB_SERVER_URL=http://localhost:8009 INTERVIEW_ID=$INTERVIEW_ID python ai-interviewer.py --transport daily
) &

BOT_PID=$!
echo "AI Bot PID: $BOT_PID"

# Wait a bit for bot to initialize
sleep 5

echo -e "\n${GREEN}🎉 AI Interviewer Project Started Successfully!${NC}"
echo "=============================================="
echo -e "${GREEN}🌐 Web Dashboard:${NC} http://localhost:8009/dashboard/"
echo -e "${GREEN}📋 All Interviews:${NC} http://localhost:8009/dashboard/interviews"
echo -e "${GREEN}🎙️ Join Interview:${NC} https://hi2inspire.daily.co/hi2inspire"
echo -e "${GREEN}🆔 Interview ID:${NC} $INTERVIEW_ID"
echo ""
echo -e "${YELLOW}💡 How to test:${NC}"
echo "1. Visit the dashboard: http://localhost:8009/dashboard/"
echo "2. Click 'Schedule Interview' to create a new interview"
echo "3. Join the call: https://hi2inspire.daily.co/hi2inspire"
echo "4. Have a conversation with the AI"
echo "5. Leave the call and check results in dashboard"
echo ""
echo -e "${YELLOW}🛑 To stop: Press Ctrl+C${NC}"

# Keep script running and monitor processes
while true; do
    # Check if web server is still running
    if ! kill -0 $WEB_SERVER_PID 2>/dev/null; then
        echo -e "${RED}❌ Web Server stopped unexpectedly${NC}"
        break
    fi
    
    # Check if bot is still running
    if ! kill -0 $BOT_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️ AI Bot stopped. Restarting...${NC}"
        cd /home/prashant/Playground/personal/consult/ai-interviewer/server
        (
            source ~/miniconda3/etc/profile.d/conda.sh
            conda activate pipecat-env
            WEB_SERVER_URL=http://localhost:8009 INTERVIEW_ID=$INTERVIEW_ID python ai-interviewer.py --transport daily
        ) &
        BOT_PID=$!
        echo "New AI Bot PID: $BOT_PID"
    fi
    
    sleep 10
done

cleanup
