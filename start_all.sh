#!/bin/bash
# AI Interviewer - Start All Services

echo "🚀 Starting AI Interviewer..."

# 1. Start Redis
echo "1️⃣ Starting Redis..."
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest 2>/dev/null || docker start redis-ai-interviewer
sleep 2

# 2. Start RQ Worker  
echo "2️⃣ Starting RQ Worker..."
cd /home/prashant/Playground/personal/consult/ai-interviewer/web_server
conda run -n pipecat-env rq worker --with-scheduler > /tmp/rq_worker.log 2>&1 &
RQ_PID=$!
echo "   Worker PID: $RQ_PID"
sleep 2

# 3. Start Web Server
echo "3️⃣ Starting Web Server..."
conda run -n pipecat-env python main.py > /tmp/web_server.log 2>&1 &
WEB_PID=$!
echo "   Server PID: $WEB_PID"
sleep 3

# 4. Verify
echo ""
echo "✅ Verification:"
redis-cli ping > /dev/null 2>&1 && echo "  ✅ Redis: Running" || echo "  ❌ Redis: Failed"
conda run -n pipecat-env rq info > /dev/null 2>&1 && echo "  ✅ RQ Worker: Running" || echo "  ❌ RQ Worker: Failed"
curl -s http://localhost:8009/health > /dev/null 2>&1 && echo "  ✅ Web Server: Running" || echo "  ❌ Web Server: Failed"

echo ""
echo "🎉 AI Interviewer is ready!"
echo "📊 Dashboard: http://localhost:8009/dashboard"
echo "📚 API Docs: http://localhost:8009/docs"
echo ""
echo "📝 Logs:"
echo "  Web Server: tail -f /tmp/web_server.log"
echo "  RQ Worker:  tail -f /tmp/rq_worker.log"
