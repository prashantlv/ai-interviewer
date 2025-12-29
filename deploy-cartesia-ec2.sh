#!/bin/bash
#
# 🚀 AI Interviewer Deployment Script for EC2
# 
# This script handles complete deployment including:
# - Git pull latest code
# - Port conflict detection and cleanup
# - Cleanup of old bot processes
# - Docker rebuild (no cache)
# - Service startup with health checks
# - Verification of Redis locking
#
# Usage: ./deploy-cartesia-ec2.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 AI Interviewer Deployment Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if running on EC2
if [ ! -d "/home/ubuntu/ai-interviewer" ]; then
    echo -e "${RED}❌ Error: /home/ubuntu/ai-interviewer not found${NC}"
    echo "This script should be run on EC2 instance"
    exit 1
fi

cd /home/ubuntu/ai-interviewer

# ============================================
# Step 1: Pull Latest Code
# ============================================
echo -e "${YELLOW}📥 Step 1: Pulling latest code from GitHub...${NC}"
git fetch origin main
git reset --hard origin/main
echo -e "${GREEN}✅ Code updated to latest version${NC}"
echo ""

# ============================================
# Step 2: Verify Redis Lock Code
# ============================================
echo -e "${YELLOW}🔍 Step 2: Verifying Redis lock implementation...${NC}"
if grep -q "redis_client = Redis" web_server/routers/proctoring.py; then
    echo -e "${GREEN}✅ Redis distributed locking code found${NC}"
else
    echo -e "${RED}❌ ERROR: Redis lock code not found in proctoring.py${NC}"
    echo "   This means duplicate bots will still occur!"
    exit 1
fi
echo ""

# ============================================
# Step 3: Check and Free Port Conflicts
# ============================================
echo -e "${YELLOW}🔌 Step 3: Checking for port conflicts...${NC}"

# Check critical ports: 6379 (Redis), 27017 (MongoDB), 8009 (Web)
PORTS_TO_CHECK=(6379 27017 8009)
CONFLICTS_FOUND=0

for PORT in "${PORTS_TO_CHECK[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "   ${YELLOW}⚠️  Port $PORT is in use${NC}"
        CONFLICTS_FOUND=1
    fi
done

if [ $CONFLICTS_FOUND -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}   Stopping all Docker containers to free ports...${NC}"
    docker stop $(docker ps -aq) 2>/dev/null || true
    sleep 3
    
    # Check again
    STILL_IN_USE=0
    for PORT in "${PORTS_TO_CHECK[@]}"; do
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "   ${RED}❌ Port $PORT still in use after stopping containers${NC}"
            PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
            echo -e "   ${YELLOW}   PID: $PID${NC}"
            STILL_IN_USE=1
        fi
    done
    
    if [ $STILL_IN_USE -eq 1 ]; then
        echo ""
        echo -e "${RED}❌ ERROR: Ports still in use. Manual cleanup required:${NC}"
        echo "   Run: sudo lsof -i :6379 -i :27017 -i :8009"
        echo "   Then: sudo kill -9 <PID>"
        exit 1
    fi
fi

echo -e "${GREEN}✅ All ports available${NC}"
echo ""

# ============================================
# Step 4: Cleanup Old Bot Processes
# ============================================
echo -e "${YELLOW}🧹 Step 4: Cleaning up old bot processes...${NC}"

# Kill all running ai-interviewer.py processes
KILLED_PROCS=$(pkill -f "ai-interviewer.py" 2>/dev/null && echo "killed" || echo "none")
if [ "$KILLED_PROCS" = "killed" ]; then
    echo "   Killed running bot processes"
    sleep 2
else
    echo "   No running bot processes found"
fi

# Clear Redis bot locks (if Redis is accessible)
if command -v redis-cli &> /dev/null; then
    LOCKS_CLEARED=$(redis-cli --scan --pattern "bot_lock:*" 2>/dev/null | wc -l || echo "0")
    if [ "$LOCKS_CLEARED" -gt 0 ]; then
        redis-cli --scan --pattern "bot_lock:*" | xargs -r redis-cli DEL > /dev/null 2>&1 || true
        echo "   Cleared $LOCKS_CLEARED Redis bot locks"
    else
        echo "   No Redis locks to clear"
    fi
    
    # Clear RQ job queue
    redis-cli DEL rq:queue:ai_bots > /dev/null 2>&1 || true
    echo "   Cleared RQ job queue"
else
    echo "   ${YELLOW}⚠️  redis-cli not available, skipping Redis cleanup${NC}"
fi

echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# ============================================
# Step 5: Stop All Containers
# ============================================
echo -e "${YELLOW}🛑 Step 5: Stopping all containers...${NC}"
docker compose down -v 2>/dev/null || true
docker stop $(docker ps -aq) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true
docker network prune -f > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Containers stopped and removed${NC}"
echo ""

# ============================================
# Step 6: Remove Old Images
# ============================================
echo -e "${YELLOW}🗑️  Step 6: Removing old Docker images...${NC}"
docker rmi $(docker images -q 'ai-interviewer*' 2>/dev/null) 2>/dev/null || true
docker system prune -f > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Old images removed${NC}"
echo ""

# ============================================
# Step 7: Rebuild Docker Images (No Cache)
# ============================================
echo -e "${YELLOW}🔨 Step 7: Building Docker images (this may take 5-10 minutes)...${NC}"
echo "   Building without cache to ensure latest code is used"
docker compose build --no-cache
echo -e "${GREEN}✅ Docker images built successfully${NC}"
echo ""

# ============================================
# Step 8: Start Services
# ============================================
echo -e "${YELLOW}🚀 Step 8: Starting services...${NC}"
docker compose up -d
echo "   Waiting for services to initialize..."
sleep 10
echo -e "${GREEN}✅ Services started${NC}"
echo ""

# ============================================
# Step 9: Health Checks
# ============================================
echo -e "${YELLOW}🏥 Step 9: Running health checks...${NC}"
echo ""

# Check container status
echo "=== Container Status ==="
docker compose ps
echo ""

# Check Redis connection
echo "=== Redis Connection ==="
if docker exec ai-interviewer-redis redis-cli PING 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✅ Redis: Connected${NC}"
else
    echo -e "${RED}❌ Redis: Not responding${NC}"
fi
echo ""

# Check MongoDB connection
echo "=== MongoDB Connection ==="
if docker exec ai-interviewer-mongodb mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null | grep -q "ok"; then
    echo -e "${GREEN}✅ MongoDB: Connected${NC}"
else
    echo -e "${RED}❌ MongoDB: Not responding${NC}"
fi
echo ""

# Check web server
echo "=== Web Server ==="
if curl -s -f http://localhost:8009/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Web Server: Responding on port 8009${NC}"
else
    echo -e "${RED}❌ Web Server: Not responding${NC}"
fi
echo ""

# Check worker status
echo "=== RQ Workers ==="
WORKER_COUNT=$(docker compose ps rq-worker | grep -c "Up" || echo "0")
echo "   Active workers: $WORKER_COUNT"
if [ "$WORKER_COUNT" -ge 1 ]; then
    echo -e "${GREEN}✅ Workers: Running${NC}"
else
    echo -e "${RED}❌ Workers: Not running${NC}"
fi
echo ""

# ============================================
# Step 10: Verify Configuration
# ============================================
echo -e "${YELLOW}⚙️  Step 10: Verifying configuration...${NC}"
echo ""

echo "=== Environment Variables ==="
docker exec ai-interviewer-rq-worker-1 env 2>/dev/null | grep -E "VIDEO_SERVICE|BOT_IMPLEMENTATION|DAILY_DOMAIN" || echo "Configuration check skipped"
echo ""

echo "=== Recent Web Server Logs ==="
docker compose logs web --tail 10 2>/dev/null | grep -E "Started server|Uvicorn running" || echo "No startup logs yet"
echo ""

# ============================================
# Deployment Summary
# ============================================
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "🎯 Next Steps:"
echo ""
echo "1. Schedule a test interview:"
echo "   https://api.human2intelligence.com/dashboard/schedule"
echo ""
echo "2. Monitor bot scheduling (watch for Redis lock messages):"
echo "   docker compose logs -f web | grep -E 'Starting bot|already in progress|Redis lock'"
echo ""
echo "3. Monitor worker logs (watch for single bot start):"
echo "   docker compose logs -f rq-worker | grep -E 'Starting bot|Bot scheduled'"
echo ""
echo "4. Watch for greeting and speech:"
echo "   docker compose logs -f rq-worker | grep -E 'greeting|Bot ready|Real participant joined'"
echo ""
echo "5. Check for errors:"
echo "   docker compose logs -f | grep -i error"
echo ""
echo -e "${BLUE}================================================${NC}"
echo "📊 Expected Behavior:"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "✅ GOOD - Page Load:"
echo "   🤖 Starting bot for interview: interview_XXXXX"
echo "   ✅ Bot scheduled: ..."
echo ""
echo "✅ GOOD - Page Refresh:"
echo "   ⏸️ Bot start already in progress (Redis lock held)"
echo "   ⏸️ Bot start already in progress (Redis lock held)"
echo ""
echo "❌ BAD - Duplicate Bots:"
echo "   🤖 Starting bot for interview: interview_XXXXX"
echo "   🤖 Starting bot for interview: interview_XXXXX  ← Should NOT happen!"
echo ""
echo -e "${BLUE}================================================${NC}"
echo "🔧 Troubleshooting Commands:"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "# Check Redis locks:"
echo "docker exec ai-interviewer-redis redis-cli --scan --pattern 'bot_lock:*'"
echo ""
echo "# Check RQ job queue:"
echo "docker exec ai-interviewer-redis redis-cli LLEN rq:queue:ai_bots"
echo ""
echo "# Kill stuck bots:"
echo "./cleanup-duplicate-bots.sh"
echo ""
echo "# View all logs:"
echo "docker compose logs -f"
echo ""
echo "# Restart single service:"
echo "docker compose restart web"
echo "docker compose restart rq-worker"
echo ""
echo -e "${BLUE}================================================${NC}"
echo "🚨 Rollback (if needed):"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "git log --oneline -10  # Find previous commit"
echo "git reset --hard <commit-hash>"
echo "docker compose down && docker compose build --no-cache && docker compose up -d"
echo ""
echo -e "${GREEN}Deployment script completed successfully!${NC}"
echo ""

