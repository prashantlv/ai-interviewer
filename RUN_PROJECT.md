# 🚀 How to Run AI Interviewer - Complete Guide

**Last Updated:** October 9, 2025

---

## ⚡ Quick Start (3 Steps)

### Step 1: Start Redis (Job Queue)
```bash
# Option A: Using Docker (Recommended)
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest

# Option B: Using local Redis
redis-server --daemonize yes
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

---

### Step 2: Start RQ Worker (Bot Manager)
```bash
# Navigate to web_server directory
cd /home/prashant/Playground/personal/consult/ai-interviewer/web_server

# Activate conda environment and start worker
conda run -n pipecat-env rq worker --with-scheduler

# Or run in background:
conda run -n pipecat-env rq worker --with-scheduler > /tmp/rq_worker.log 2>&1 &
```

**Verify worker is running:**
```bash
rq info
# Should show: 1 worker running
```

---

### Step 3: Start Web Server
```bash
# Navigate to web_server directory
cd /home/prashant/Playground/personal/consult/ai-interviewer/web_server

# Start the server
conda run -n pipecat-env python main.py

# Or run in background:
conda run -n pipecat-env python main.py > /tmp/web_server.log 2>&1 &
```

**Verify web server is running:**
```bash
curl http://localhost:8009/health
# Should return: {"status":"healthy",...}
```

---

## 🎯 Access Your Application

1. **Dashboard:** http://localhost:8009/dashboard
2. **API Docs:** http://localhost:8009/docs
3. **Health Check:** http://localhost:8009/health

---

## 🤖 How Bot Auto-Join Works

When you schedule an interview with "Auto-start bot" enabled:

1. ✅ Interview is created in MongoDB
2. ✅ Daily.co room is created
3. ✅ Job is enqueued in Redis
4. ✅ RQ Worker picks up the job
5. ✅ Bot process starts automatically
6. ✅ Bot joins the Daily.co room
7. ✅ AI starts interviewing!

**Requirements:**
- ✅ Web Server running
- ✅ Redis running
- ✅ RQ Worker running
- ✅ MongoDB running (or mock mode)

---

## 📋 Full Startup Script

Create a script to start everything:

```bash
#!/bin/bash
# File: /home/prashant/Playground/personal/consult/ai-interviewer/start_all.sh

echo "🚀 Starting AI Interviewer..."

# 1. Start Redis
echo "1️⃣ Starting Redis..."
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest 2>/dev/null || \
docker start redis-ai-interviewer
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
rq info > /dev/null 2>&1 && echo "  ✅ RQ Worker: Running" || echo "  ❌ RQ Worker: Failed"
curl -s http://localhost:8009/health > /dev/null 2>&1 && echo "  ✅ Web Server: Running" || echo "  ❌ Web Server: Failed"

echo ""
echo "🎉 AI Interviewer is ready!"
echo "📊 Dashboard: http://localhost:8009/dashboard"
echo "📚 API Docs: http://localhost:8009/docs"
echo ""
echo "📝 Logs:"
echo "  Web Server: tail -f /tmp/web_server.log"
echo "  RQ Worker:  tail -f /tmp/rq_worker.log"
```

**Make it executable:**
```bash
chmod +x /home/prashant/Playground/personal/consult/ai-interviewer/start_all.sh
```

**Run it:**
```bash
/home/prashant/Playground/personal/consult/ai-interviewer/start_all.sh
```

---

## 🛑 Stop All Services

```bash
#!/bin/bash
# File: /home/prashant/Playground/personal/consult/ai-interviewer/stop_all.sh

echo "🛑 Stopping AI Interviewer..."

# Stop web server
pkill -f "python main.py"
echo "✅ Web server stopped"

# Stop RQ worker
pkill -f "rq worker"
echo "✅ RQ worker stopped"

# Stop Redis (Docker)
docker stop redis-ai-interviewer
echo "✅ Redis stopped"

echo "🎉 All services stopped!"
```

---

## 🔍 Troubleshooting

### Bot Not Joining Interview?

**Check all services are running:**
```bash
# 1. Check Redis
redis-cli ping
# Should return: PONG

# 2. Check RQ Worker
rq info
# Should show: 1 worker

# 3. Check Web Server
curl http://localhost:8009/health
# Should return healthy status

# 4. Check Queue
curl http://localhost:8009/api/v1/bots/queue
# Should show queue info
```

**Check logs:**
```bash
# Web server logs
tail -f /tmp/web_server.log

# Worker logs
tail -f /tmp/rq_worker.log
```

### Common Issues:

1. **"Connection refused" error**
   - ❌ Redis is not running
   - ✅ Start Redis: `docker run -d -p 6379:6379 redis:latest`

2. **Bot doesn't start**
   - ❌ RQ Worker is not running
   - ✅ Start worker: `rq worker --with-scheduler`

3. **"Auto-start bot" toggle not visible**
   - ❌ Old cached page
   - ✅ Hard refresh: Ctrl+Shift+R

---

## 🎯 Environment Variables

**Required for full functionality:**

```bash
# web_server/.env
OPENAI_API_KEY=your_openai_key
DAILY_API_KEY=your_daily_key
TAVUS_API_KEY=your_tavus_key
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ai_interviewer
```

---

## 📊 Monitoring

**Check system health:**
```bash
# Overall health
curl http://localhost:8009/health

# Detailed health
curl http://localhost:8009/api/v1/health

# Bot queue status
curl http://localhost:8009/api/v1/bots/queue

# Active bots
curl http://localhost:8009/api/v1/bots/active
```

---

**Questions? Check:**
- WORKER_GUIDE.md - RQ Worker details
- DAILY_CO_INTEGRATION.md - Daily.co setup
- DEVELOPMENT.md - Development guide

