#!/bin/bash
# One-liner deployment script for Cartesia TTS on EC2
# Run this on EC2 to deploy Cartesia TTS integration

set -e

echo "🚀 Deploying Cartesia TTS Integration to EC2..."
echo "================================================"

# Step 1: Pull latest code
echo "📥 Step 1: Pulling latest code..."
cd ~/ai-interviewer
git pull origin main

# Step 2: Update environment variables
echo "⚙️  Step 2: Updating environment variables..."
grep -q "CARTESIA_API_KEY" server/.env || cat >> server/.env << 'EOF'

# Cartesia TTS Configuration
TTS_SERVICE=cartesia
CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
CARTESIA_MODEL=sonic-english
CARTESIA_LANGUAGE=en
EOF

grep -q "CARTESIA_API_KEY" web_server/.env || cat >> web_server/.env << 'EOF'

# Cartesia TTS Configuration
TTS_SERVICE=cartesia
CARTESIA_API_KEY=sk_car_ib5wETe49cRfZX6HMGpArL
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
CARTESIA_MODEL=sonic-english
CARTESIA_LANGUAGE=en
EOF

echo "✅ Environment variables updated"

# Step 3: Rebuild Docker images
echo "🔨 Step 3: Rebuilding Docker images (this may take 5-10 minutes)..."
sudo docker build -f Dockerfile.web -t ai-interviewer-web:test . > /dev/null 2>&1 &
WEB_PID=$!
sudo docker build -f Dockerfile.worker -t ai-interviewer-worker:test . > /dev/null 2>&1 &
WORKER_PID=$!

echo "⏳ Building images in parallel..."
wait $WEB_PID && echo "  ✅ Web image built"
wait $WORKER_PID && echo "  ✅ Worker image built"

# Step 4: Stop and remove old containers
echo "🛑 Step 4: Stopping old containers..."
sudo docker stop ai-interviewer-web ai-interviewer-worker 2>/dev/null || true
sudo docker rm ai-interviewer-web ai-interviewer-worker 2>/dev/null || true
echo "✅ Old containers removed"

# Step 5: Start new containers
echo "🚀 Step 5: Starting new containers..."
sudo docker run -d \
  --name ai-interviewer-web \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  --restart unless-stopped \
  ai-interviewer-web:test

sudo docker run -d \
  --name ai-interviewer-worker \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  --restart unless-stopped \
  ai-interviewer-worker:test

sleep 3
echo "✅ New containers started"

# Step 6: Verify deployment
echo "🔍 Step 6: Verifying deployment..."
echo ""
echo "=== Container Status ==="
sudo docker ps --filter name=ai-interviewer --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "=== TTS Configuration ==="
sudo docker exec ai-interviewer-worker env | grep -E "TTS_SERVICE|CARTESIA_VOICE_ID" || echo "⚠️  Configuration not found"

echo ""
echo "=== Worker Logs (last 20 lines) ==="
sudo docker logs ai-interviewer-worker --tail 20 | grep -i "cartesia\|tts\|initialized" || echo "No Cartesia logs yet (bot not started)"

echo ""
echo "================================================"
echo "✅ Deployment Complete!"
echo ""
echo "Next steps:"
echo "1. Schedule a test interview at https://api.human2intelligence.com/dashboard/schedule"
echo "2. Monitor logs: sudo docker logs -f ai-interviewer-worker | grep -i cartesia"
echo "3. Check for: '✅ Initialized Cartesia TTS' message when bot starts"
echo ""
echo "To rollback to OpenAI:"
echo "  sed -i 's/TTS_SERVICE=cartesia/TTS_SERVICE=openai/' ~/ai-interviewer/server/.env"
echo "  sudo docker restart ai-interviewer-worker"
echo "================================================"

