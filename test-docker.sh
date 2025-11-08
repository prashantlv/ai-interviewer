#!/bin/bash
# Test Docker Images Locally

set -e

echo "🧪 Testing AI Interviewer Docker Images"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

echo -e "\n${BLUE}1️⃣ Building Docker images...${NC}"
docker build -f Dockerfile.web -t ai-interviewer-web:test .
echo -e "${GREEN}✅ Web server image built${NC}"

docker build -f Dockerfile.worker -t ai-interviewer-worker:test .
echo -e "${GREEN}✅ Worker image built${NC}"

echo -e "\n${BLUE}2️⃣ Checking Redis...${NC}"
# Check if Redis is already running
REDIS_RUNNING=false
if command -v redis-cli > /dev/null 2>&1; then
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is running on host (localhost:6379)${NC}"
        REDIS_RUNNING=true
        REDIS_URL="redis://localhost:6379/0"
    fi
fi

if [ "$REDIS_RUNNING" = false ]; then
    if docker ps | grep -q redis; then
        echo -e "${GREEN}✅ Redis container is running${NC}"
        REDIS_RUNNING=true
        REDIS_URL="redis://localhost:6379/0"
    else
        echo -e "${YELLOW}⚠️ Redis not found. Starting test Redis container...${NC}"
        docker run -d --name test-redis -p 6379:6379 redis:7-alpine 2>/dev/null || \
            docker start test-redis 2>/dev/null || true
        sleep 2
        if docker ps | grep -q test-redis; then
            echo -e "${GREEN}✅ Test Redis started on port 6379${NC}"
            REDIS_RUNNING=true
            REDIS_URL="redis://localhost:6379/0"
        else
            echo -e "${RED}❌ Could not start Redis${NC}"
            echo -e "${YELLOW}⚠️ Continuing anyway - make sure Redis is accessible${NC}"
            REDIS_URL="redis://localhost:6379/0"
        fi
    fi
fi

echo -e "\n${BLUE}3️⃣ Loading environment variables from .env files...${NC}"

# Load .env files if they exist
ENV_ARGS=""
if [ -f "server/.env" ]; then
    echo -e "${GREEN}✅ Found server/.env${NC}"
    # Export variables from .env file
    set -a
    source server/.env 2>/dev/null || true
    set +a
fi

if [ -f "web_server/.env" ]; then
    echo -e "${GREEN}✅ Found web_server/.env${NC}"
    set -a
    source web_server/.env 2>/dev/null || true
    set +a
fi

# Build environment variable arguments for docker run
if [ -n "$MONGODB_URL" ]; then
    ENV_ARGS="$ENV_ARGS -e MONGODB_URL=\"$MONGODB_URL\""
fi
if [ -n "$DATABASE_NAME" ]; then
    ENV_ARGS="$ENV_ARGS -e DATABASE_NAME=\"$DATABASE_NAME\""
else
    ENV_ARGS="$ENV_ARGS -e DATABASE_NAME=\"ai_interviewer\""
fi
# Use detected REDIS_URL if not in .env, otherwise use .env value
if [ -z "$REDIS_URL" ]; then
    # REDIS_URL not in .env, use detected one (set in step 2)
    ENV_ARGS="$ENV_ARGS -e REDIS_URL=\"redis://localhost:6379/0\""
else
    # REDIS_URL in .env, use it
    ENV_ARGS="$ENV_ARGS -e REDIS_URL=\"$REDIS_URL\""
fi
if [ -n "$OPENAI_API_KEY" ]; then
    ENV_ARGS="$ENV_ARGS -e OPENAI_API_KEY=\"$OPENAI_API_KEY\""
fi
if [ -n "$DAILY_API_KEY" ]; then
    ENV_ARGS="$ENV_ARGS -e DAILY_API_KEY=\"$DAILY_API_KEY\""
fi
if [ -n "$VIDEO_SERVICE" ]; then
    ENV_ARGS="$ENV_ARGS -e VIDEO_SERVICE=\"$VIDEO_SERVICE\""
fi
if [ -n "$TAVUS_API_KEY" ]; then
    ENV_ARGS="$ENV_ARGS -e TAVUS_API_KEY=\"$TAVUS_API_KEY\""
fi
if [ -n "$TAVUS_REPLICA_ID" ]; then
    ENV_ARGS="$ENV_ARGS -e TAVUS_REPLICA_ID=\"$TAVUS_REPLICA_ID\""
fi
if [ -n "$HEYGEN_API_KEY" ]; then
    ENV_ARGS="$ENV_ARGS -e HEYGEN_API_KEY=\"$HEYGEN_API_KEY\""
fi
if [ -n "$HEYGEN_AVATAR_ID" ]; then
    ENV_ARGS="$ENV_ARGS -e HEYGEN_AVATAR_ID=\"$HEYGEN_AVATAR_ID\""
fi
if [ -n "$BOT_IMPLEMENTATION" ]; then
    ENV_ARGS="$ENV_ARGS -e BOT_IMPLEMENTATION=\"$BOT_IMPLEMENTATION\""
fi


echo -e "\n${BLUE}4️⃣ Testing web server image...${NC}"
echo -e "${YELLOW}Starting web server container (will keep running for manual testing)...${NC}"

# Stop any existing test container
docker stop test-web 2>/dev/null || true
docker rm test-web 2>/dev/null || true

# Start web server container (keep it running)
echo -e "${BLUE}Starting container with your .env variables...${NC}"
eval "docker run -d \
    --name test-web \
    -p 8009:8009 \
    --network host \
    $ENV_ARGS \
    ai-interviewer-web:test"

sleep 5

# Check if container is running
if docker ps | grep -q test-web; then
    echo -e "${GREEN}✅ Web server container started successfully${NC}"
    
    # Wait a bit for server to fully start
    sleep 3
    
    # Test health check
    echo -e "\n${BLUE}Testing health endpoint...${NC}"
    HEALTH_RESPONSE=$(curl -s http://localhost:8009/health 2>/dev/null || echo "failed")
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo -e "${GREEN}✅ Health check passed!${NC}"
        echo "$HEALTH_RESPONSE" | python -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
    else
        echo -e "${YELLOW}⚠️ Health check response: $HEALTH_RESPONSE${NC}"
    fi
    
    echo -e "\n${GREEN}🌐 Web server is running!${NC}"
    echo -e "${BLUE}📊 Dashboard:${NC} http://localhost:8009/dashboard"
    echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8009/docs"
    echo -e "${BLUE}❤️ Health:${NC} http://localhost:8009/health"
    echo ""
    echo -e "${YELLOW}⏸️ Container is running in background. Test in your browser!${NC}"
    echo -e "${YELLOW}📝 To view logs: docker logs -f test-web${NC}"
    echo -e "${YELLOW}🛑 To stop: docker stop test-web${NC}"
    echo ""
    echo -e "${BLUE}ℹ️  Note: .env files are NOT automatically loaded into Docker containers.${NC}"
    echo -e "${BLUE}   This script loads them and passes as environment variables.${NC}"
    echo ""
    echo -e "\n${YELLOW}💡 Tip: Make sure Redis is running on your host (or in a container)${NC}"
    echo -e "${YELLOW}   The containers use --network host to connect to host Redis${NC}"
    echo ""
    read -p "Press Enter to stop all containers and continue..."
    
    # Stop containers
    echo -e "\n${BLUE}Stopping containers...${NC}"
    docker stop test-web test-worker 2>/dev/null || true
    docker rm test-web test-worker 2>/dev/null || true
    echo -e "${GREEN}✅ Containers stopped${NC}"
else
    echo -e "${RED}❌ Web server container failed to start${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker logs test-web 2>/dev/null || true
fi

echo -e "\n${BLUE}5️⃣ Starting worker container...${NC}"
echo -e "${YELLOW}Worker is needed to process bot jobs${NC}"

# Stop any existing worker container
docker stop test-worker 2>/dev/null || true
docker rm test-worker 2>/dev/null || true

# Start worker container
echo -e "${BLUE}Starting worker container with your .env variables...${NC}"
eval "docker run -d \
    --name test-worker \
    --network host \
    $ENV_ARGS \
    ai-interviewer-worker:test"

sleep 3

# Check if worker is running
if docker ps | grep -q test-worker; then
    echo -e "${GREEN}✅ Worker container started successfully${NC}"
    echo -e "${YELLOW}📝 To view worker logs: docker logs -f test-worker${NC}"
else
    echo -e "${RED}❌ Worker container failed to start${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    docker logs test-worker 2>/dev/null || true
fi

echo -e "\n${BLUE}6️⃣ Cleaning up test containers...${NC}"
# Only remove test-redis if we created it (not if it was already running)
if docker ps -a | grep -q test-redis; then
    docker stop test-redis 2>/dev/null || true
    docker rm test-redis 2>/dev/null || true
    echo -e "${GREEN}✅ Test containers cleaned up${NC}"
else
    echo -e "${YELLOW}⚠️ No test containers to clean up${NC}"
fi

echo -e "\n${GREEN}✅ Docker image tests completed!${NC}"
echo -e "\n${YELLOW}📝 Next steps:${NC}"
echo "1. Images are ready: ai-interviewer-web:test and ai-interviewer-worker:test"
echo "2. Tag them as :latest for deployment:"
echo "   docker tag ai-interviewer-web:test ai-interviewer-web:latest"
echo "   docker tag ai-interviewer-worker:test ai-interviewer-worker:latest"
echo "3. Test with docker-compose (requires MongoDB):"
echo "   docker-compose up -d"

