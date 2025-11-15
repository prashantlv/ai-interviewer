# Local Development Guide

## 🚀 Quick Start

### **For New Machine Setup:**
```bash
# 1. Clone and setup environment
./setup-environment.sh

# 2. Configure .env files
# Edit server/.env and web_server/.env with your API keys

# 3. Start the application
./start.sh
```

### **For Daily Development:**
```bash
# Just run this one command:
./start.sh
```

---

## 📁 Startup Scripts Overview

### **For Local Development:**
```
./start.sh                    ← Use this to start everything locally
./setup-environment.sh        ← Use this to setup on new machine
```

### **For Docker/Production:**
```
./test-docker.sh              ← Test Docker images locally
./deploy.sh                   ← Deploy to EC2 (run on server)
```

---

## 🎯 Main Startup Script: `start.sh`

### **What it does:**
1. ✅ Starts Redis (Docker container)
2. ✅ Starts RQ Worker (job queue processor)
3. ✅ Starts Web Server (FastAPI application)
4. ✅ Verifies all services are running
5. ✅ Shows **live logs** from both services
6. ✅ Cleans up properly on Ctrl+C

### **Usage:**
```bash
# Start everything
./start.sh

# You'll see live logs from:
# - Web Server (port 8009)
# - RQ Worker (processes interview jobs)

# To stop: Press Ctrl+C (cleans up everything)
```

### **Access Points:**
- 🌐 **Dashboard:** http://localhost:8009/dashboard
- 📚 **API Docs:** http://localhost:8009/docs
- 🔧 **Health Check:** http://localhost:8009/health
- 📊 **System Status:** http://localhost:8009/dashboard/system-health

### **Log Files:**
```bash
# Logs are saved to /tmp/ for viewing in separate terminals

# View web server logs
tail -f /tmp/web_server.log

# View RQ worker logs
tail -f /tmp/rq_worker.log
```

---

## 🏗️ Architecture (Local Development)

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Development Stack                   │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    Redis     │◄─────┤  RQ Worker   │◄─────┤ Web Server   │
│ (Docker)     │      │ (pipecat-env)│      │(pipecat-env) │
│ Port: 6379   │      │              │      │ Port: 8009   │
└──────────────┘      └──────────────┘      └──────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  AI Bot      │
                      │  Process     │
                      │ (spawned)    │
                      └──────────────┘
```

### **How it works:**
1. **Web Server** receives interview scheduling requests
2. Adds job to **Redis** queue
3. **RQ Worker** picks up the job
4. Worker spawns **AI Bot** subprocess
5. Bot joins Daily.co room and conducts interview
6. Results saved to MongoDB

---

## 🔧 Manual Startup (Step by Step)

If you prefer to start services manually:

### **Terminal 1 - Redis:**
```bash
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest
```

### **Terminal 2 - RQ Worker:**
```bash
cd web_server
conda activate pipecat-env
rq worker ai_bots --with-scheduler
```

### **Terminal 3 - Web Server:**
```bash
cd web_server
conda activate pipecat-env
python main.py
```

---

## 🐛 Troubleshooting

### **Issue: Port 8009 already in use**
```bash
# Find and kill the process
lsof -ti:8009 | xargs kill -9

# Or use the script (it handles this automatically)
./start.sh
```

### **Issue: Redis connection failed**
```bash
# Check if Redis is running
docker ps | grep redis

# Start Redis
docker start redis-ai-interviewer

# Or create new Redis container
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest
```

### **Issue: Conda environment not found**
```bash
# Create environment
./setup-environment.sh

# Or manually:
conda create -n pipecat-env python=3.12
conda activate pipecat-env
pip install -r server/requirements.txt
pip install -r web_server/requirements.txt
```

### **Issue: Import errors / Missing packages**
```bash
# Update packages
conda activate pipecat-env
pip install --upgrade -r server/requirements.txt
pip install --upgrade -r web_server/requirements.txt
```

### **Issue: AI bot not joining interview**
```bash
# Check RQ worker logs
tail -f /tmp/rq_worker.log

# Check for errors in bot startup
# Common issues:
# - Missing API keys (check .env files)
# - Tavus payment required (use VIDEO_SERVICE=none or VIDEO_SERVICE=simli)
# - Daily.co room URL invalid
```

---

## 📋 Verification Checklist

After starting with `./start.sh`, verify:

### **1. Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### **2. Web Server is running:**
```bash
curl http://localhost:8009/health
# Should return: {"status":"healthy","timestamp":"..."}
```

### **3. RQ Worker is running:**
```bash
# Check if worker is processing jobs
conda activate pipecat-env
cd web_server
rq info
# Should show worker status
```

### **4. Test full flow:**
```bash
# 1. Visit dashboard
open http://localhost:8009/dashboard

# 2. Schedule an interview
# 3. Check system health
open http://localhost:8009/dashboard/system-health

# 4. Verify bot starts
tail -f /tmp/rq_worker.log
# Should see: "✅ Bot started successfully! PID: ..."
```

---

## 🔄 Development Workflow

### **Typical Development Session:**

```bash
# 1. Start everything
./start.sh

# 2. Open in browser
open http://localhost:8009/dashboard

# 3. Make code changes
# (web_server auto-reloads with uvicorn --reload)
# (worker needs manual restart if changed)

# 4. Test changes
# Schedule interview → Check logs → Verify results

# 5. Stop when done
# Press Ctrl+C in terminal running start.sh
```

### **If you modify Worker code:**
```bash
# 1. Find and kill worker process
ps aux | grep "rq worker"
kill <PID>

# 2. Restart worker
cd web_server
conda activate pipecat-env
rq worker ai_bots --with-scheduler
```

### **If you modify AI Bot code:**
```bash
# No restart needed!
# Worker spawns a new bot process for each interview
# Changes take effect on next interview
```

---

## 📦 Environment Management

### **Active Conda Environment:**
```
Name:     pipecat-env
Python:   3.12.11
Packages: 161 total
Location: ~/miniconda3/envs/pipecat-env
```

### **View installed packages:**
```bash
conda activate pipecat-env
pip list
```

### **Export current environment:**
```bash
conda activate pipecat-env
pip freeze > requirements.lock
```

### **Sync with Docker:**
```bash
# Compare versions
conda activate pipecat-env
pip show pipecat-ai openai fastapi

# vs Docker
docker exec test-ai-worker pip show pipecat-ai openai fastapi
```

---

## 🎯 Quick Commands Reference

```bash
# Setup on new machine
./setup-environment.sh

# Start development
./start.sh

# Stop everything
Ctrl+C (in start.sh terminal)

# View logs
tail -f /tmp/web_server.log
tail -f /tmp/rq_worker.log

# Check Redis
redis-cli ping

# Check Web Server
curl http://localhost:8009/health

# Check RQ Worker
conda activate pipecat-env && cd web_server && rq info

# Restart Redis
docker restart redis-ai-interviewer

# Clean up old containers
docker rm -f redis-ai-interviewer

# Test locally
open http://localhost:8009/dashboard
```

---

## 📚 Related Documentation

- **`ENVIRONMENT_MANAGEMENT_GUIDE.md`** - Package management details
- **`PACKAGE_COMPARISON.md`** - Local vs Docker comparison
- **`setup-environment.sh`** - New machine setup script
- **`start.sh`** - Main startup script (this guide)
- **`test-docker.sh`** - Local Docker testing
- **`deploy.sh`** - EC2 deployment

---

## 🎓 Best Practices

1. ✅ **Always use `start.sh`** for consistent startup
2. ✅ **Check logs** if something doesn't work
3. ✅ **Keep conda env updated** with requirements.txt
4. ✅ **Test in Docker** before deploying to production
5. ✅ **Use `.env` files** for API keys (never commit them)
6. ✅ **Monitor system health** dashboard regularly
7. ✅ **Clean up** properly with Ctrl+C (not kill -9)

---

## 🚀 Summary

**For Local Development:**
```bash
# One command to rule them all:
./start.sh
```

**What you get:**
- ✅ Redis running in Docker
- ✅ RQ Worker processing jobs
- ✅ Web Server on port 8009
- ✅ Live logs from all services
- ✅ Clean shutdown with Ctrl+C

**Access your app:**
- Dashboard: http://localhost:8009/dashboard
- API Docs: http://localhost:8009/docs

**Need help?** Check logs in `/tmp/` or read the troubleshooting section above.

---

**Happy coding! 🎉**

