#!/bin/bash
# Test Cartesia TTS integration with Docker locally

set -e

echo "🐋 Testing Cartesia TTS with Docker Locally"
echo "============================================"

cd "$(dirname "$0")"

# Step 1: Build images
echo ""
echo "1️⃣ Building Docker images..."
echo "   (This may take a few minutes on first run)"

docker build -f Dockerfile.web -t ai-interviewer-web:test . > /tmp/docker-build-web.log 2>&1 &
WEB_PID=$!

docker build -f Dockerfile.worker -t ai-interviewer-worker:test . > /tmp/docker-build-worker.log 2>&1 &
WORKER_PID=$!

echo "   ⏳ Building in parallel..."
wait $WEB_PID && echo "   ✅ Web image built" || (echo "❌ Web build failed" && cat /tmp/docker-build-web.log && exit 1)
wait $WORKER_PID && echo "   ✅ Worker image built" || (echo "❌ Worker build failed" && cat /tmp/docker-build-worker.log && exit 1)

# Step 2: Stop any existing test containers
echo ""
echo "2️⃣ Cleaning up old test containers..."
docker stop test-ai-web test-ai-worker 2>/dev/null || true
docker rm test-ai-web test-ai-worker 2>/dev/null || true
echo "   ✅ Cleanup complete"

# Step 3: Verify .env has Cartesia config
echo ""
echo "3️⃣ Verifying Cartesia configuration..."
if grep -q "CARTESIA_API_KEY" server/.env && grep -q "TTS_SERVICE=cartesia" server/.env; then
    echo "   ✅ Cartesia config found in server/.env"
    grep "TTS_SERVICE\|CARTESIA_API_KEY\|CARTESIA_VOICE_ID" server/.env | sed 's/^/      /'
else
    echo "   ❌ Cartesia config missing in server/.env"
    echo "   Adding it now..."
    cat >> server/.env << 'EOF'

# Cartesia TTS Configuration
TTS_SERVICE=cartesia
CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
CARTESIA_MODEL=sonic-english
CARTESIA_LANGUAGE=en
EOF
    echo "   ✅ Cartesia config added"
fi

# Step 4: Start containers
echo ""
echo "4️⃣ Starting Docker containers..."

docker run -d \
  --name test-ai-web \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  ai-interviewer-web:test

docker run -d \
  --name test-ai-worker \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  ai-interviewer-worker:test

sleep 3
echo "   ✅ Containers started"

# Step 5: Verify containers are running
echo ""
echo "5️⃣ Container status:"
docker ps --filter name=test-ai --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Step 6: Check TTS configuration
echo ""
echo "6️⃣ Verifying TTS configuration in container..."
TTS_CHECK=$(docker exec test-ai-worker env | grep "TTS_SERVICE" || echo "NOT_FOUND")
if [[ "$TTS_CHECK" == *"cartesia"* ]]; then
    echo "   ✅ TTS_SERVICE=cartesia"
    docker exec test-ai-worker env | grep CARTESIA | sed 's/^/      /'
else
    echo "   ❌ TTS_SERVICE not set to cartesia"
    echo "   Current: $TTS_CHECK"
fi

# Step 7: Check logs
echo ""
echo "7️⃣ Checking worker logs for Cartesia initialization..."
sleep 2
docker logs test-ai-worker --tail 30 | grep -i "cartesia\|tts\|initialized" | sed 's/^/   /' || echo "   ⏳ No Cartesia logs yet (bot not started)"

# Step 8: Instructions
echo ""
echo "============================================"
echo "✅ Docker containers are running!"
echo ""
echo "📊 Dashboard: http://localhost:8009/dashboard"
echo "📚 API Docs: http://localhost:8009/docs"
echo ""
echo "🧪 To test Cartesia TTS:"
echo "   1. Open browser: http://localhost:8009/dashboard/schedule"
echo "   2. Schedule a test interview"
echo "   3. Join the interview call"
echo "   4. Listen for Cartesia voice (lower latency, clear audio)"
echo ""
echo "📜 Monitor logs:"
echo "   docker logs -f test-ai-worker | grep --line-buffered -i cartesia"
echo ""
echo "🛑 To stop containers:"
echo "   docker stop test-ai-web test-ai-worker"
echo "   docker rm test-ai-web test-ai-worker"
echo ""
echo "Press Ctrl+C to stop monitoring, or wait for manual stop..."
echo "============================================"

# Keep script running and show live logs
echo ""
echo "📜 Live worker logs (Ctrl+C to exit):"
docker logs -f test-ai-worker

