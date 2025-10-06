# 🤖 RQ Worker Guide - AI Interview Bot Queue

**Sprint 1.2: Job Queue System**  
**Last Updated:** October 6, 2025

---

## 📋 Overview

This guide explains how to run and manage RQ (Redis Queue) workers that automatically start AI interview bots when interviews are scheduled.

### What is an RQ Worker?

An RQ worker is a Python process that:
1. Connects to Redis
2. Listens for jobs in the queue
3. Executes jobs (starts AI bots)
4. Reports results back to Redis

---

## 🚀 Quick Start

### Prerequisites

1. **Redis running:**
   ```bash
   # Check if Redis is running
   redis-cli ping
   # Should return: PONG
   
   # If not running (Docker):
   docker run -d --name redis-job-queue -p 6379:6379 redis:7-alpine
   ```

2. **Dependencies installed:**
   ```bash
   cd web_server
   pip install rq redis
   ```

3. **Web server running:**
   ```bash
   cd web_server
   python main.py
   ```

### Start a Worker

```bash
cd web_server
rq worker ai_bots --with-scheduler
```

**Output:**
```
14:30:00 RQ worker 'rq:worker:hostname.12345' started
14:30:00 Cleaning registries for queue: ai_bots
14:30:00 Listening on ai_bots...
```

✅ **Worker is now ready to process jobs!**

---

## 📊 Worker Commands

### Start Worker

```bash
# Basic worker
rq worker ai_bots

# With scheduler support (recommended)
rq worker ai_bots --with-scheduler

# With custom name
rq worker ai_bots --name interview-bot-worker-1

# Verbose logging
rq worker ai_bots --verbose

# Run in background (using nohup)
nohup rq worker ai_bots --with-scheduler > worker.log 2>&1 &
```

### Monitor Workers

```bash
# List all workers
rq info --url redis://localhost:6379

# Watch in real-time
rq info --url redis://localhost:6379 --interval 1

# Check specific queue
rq info ai_bots --url redis://localhost:6379
```

### Manage Jobs

```bash
# View failed jobs
rq info --only-failed

# Requeue failed jobs
rq requeue --all --queue ai_bots

# Empty queue
rq empty ai_bots
```

---

## 🔧 Production Setup

### 1. Using systemd (Linux)

Create `/etc/systemd/system/ai-bot-worker.service`:

```ini
[Unit]
Description=AI Interview Bot RQ Worker
After=network.target redis.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/ai-interviewer/web_server
Environment="PATH=/path/to/conda/envs/pipecat-env/bin:$PATH"
ExecStart=/path/to/conda/envs/pipecat-env/bin/rq worker ai_bots --with-scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable ai-bot-worker
sudo systemctl start ai-bot-worker
sudo systemctl status ai-bot-worker
```

### 2. Using Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  web-server:
    build: ./web_server
    ports:
      - "8009:8009"
    depends_on:
      - redis
  
  rq-worker:
    build: ./web_server
    command: rq worker ai_bots --with-scheduler
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
```

### 3. Multiple Workers (Scaling)

Run multiple workers for concurrent processing:

```bash
# Terminal 1
rq worker ai_bots --name worker-1 --with-scheduler

# Terminal 2
rq worker ai_bots --name worker-2

# Terminal 3
rq worker ai_bots --name worker-3
```

Or with supervisor/systemd, create multiple service instances.

---

## 🧪 Testing the Worker

### Test 1: Simple Test Job

```python
cd web_server
python3 << 'EOF'
from rq import Queue
from redis import Redis
from workers.ai_bot_worker import test_job

# Connect
redis_conn = Redis(host='localhost', port=6379, decode_responses=True)
q = Queue('ai_bots', connection=redis_conn)

# Enqueue test
job = q.enqueue(test_job, 'Hello from test!')
print(f"Job {job.id} enqueued")
print(f"Status: {job.get_status()}")
EOF
```

**Expected:**
- Worker logs: `🧪 Test job executing: Hello from test!`
- Job completes successfully

### Test 2: Bot Start Job

```python
from rq import Queue
from redis import Redis
from workers.ai_bot_worker import start_interview_bot

redis_conn = Redis(host='localhost', port=6379, decode_responses=True)
q = Queue('ai_bots', connection=redis_conn)

job = q.enqueue(start_interview_bot, 'test_interview_001')
print(f"Bot job {job.id} enqueued")
```

**Expected:**
- Worker logs: `🤖 Starting bot worker for interview: test_interview_001`
- Bot process starts (check with `ps aux | grep ai-interviewer`)

### Test 3: Via API

```bash
# Schedule interview with auto-start
curl -X POST http://localhost:8009/api/bots/start?interview_id=test_123

# Check status
curl http://localhost:8009/api/bots/status/test_123

# Check queue
curl http://localhost:8009/api/bots/queue
```

---

## 📈 Monitoring & Debugging

### Check Worker Status

```bash
# Using RQ CLI
rq info --url redis://localhost:6379

# Check queue stats
redis-cli LLEN rq:queue:ai_bots
```

### View Worker Logs

```bash
# If running in foreground: see terminal output

# If running with systemd:
sudo journalctl -u ai-bot-worker -f

# If running with nohup:
tail -f worker.log
```

### Common Issues

#### 1. Worker Can't Connect to Redis

```bash
# Error: redis.exceptions.ConnectionError

# Fix: Check Redis is running
redis-cli ping

# Fix: Check connection settings
redis-cli -h localhost -p 6379 ping
```

#### 2. Worker Not Picking Up Jobs

```bash
# Check if worker is running
rq info --url redis://localhost:6379

# Check queue name matches
# Worker: rq worker ai_bots
# Enqueue: Queue('ai_bots', ...)
```

#### 3. Bot Fails to Start

```bash
# Check worker logs for error messages
# Common issues:
# - INTERVIEW_ID not set
# - Bot script path incorrect
# - Python environment not activated
# - Daily.co room URL missing
```

---

## 🔍 Troubleshooting

### Debug Mode

Run worker with verbose logging:

```bash
rq worker ai_bots --verbose --logging_level DEBUG
```

### Manual Job Inspection

```python
from rq import Queue
from redis import Redis

redis_conn = Redis(host='localhost', port=6379, decode_responses=True)
q = Queue('ai_bots', connection=redis_conn)

# List all jobs
print(f"Queued: {len(q)}")

# Get job details
for job_id in q.job_ids:
    job = q.fetch_job(job_id)
    print(f"Job {job_id}: {job.func_name} - {job.get_status()}")
```

### Failed Jobs

```bash
# View failed jobs
rq info --only-failed

# Requeue failed jobs
rq requeue --all --queue ai_bots

# Or via Python:
from rq import Queue
from redis import Redis

redis_conn = Redis()
q = Queue('ai_bots', connection=redis_conn)

failed = q.failed_job_registry
for job_id in failed.get_job_ids():
    failed.requeue(job_id)
```

---

## 📚 Additional Resources

- **RQ Documentation:** https://python-rq.org/
- **Redis Documentation:** https://redis.io/documentation
- **Project Docs:**
  - `SPRINT_1.2_PLAN.md` - Implementation details
  - `DEVELOPMENT.md` - Development workflow
  - `ARCHITECTURE.md` - System architecture

---

## 🎯 Best Practices

1. **Always run with `--with-scheduler`** for delayed job support
2. **Use systemd or Docker** for production deployments
3. **Monitor worker health** regularly
4. **Run multiple workers** for high-concurrency scenarios
5. **Set up log rotation** for worker logs
6. **Use Redis persistence** (AOF or RDB) to prevent job loss
7. **Set job timeouts** to prevent stuck jobs

---

## 🆘 Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review worker logs
3. Check Redis connection
4. Verify environment setup
5. Consult `SPRINT_1.2_PLAN.md` for implementation details

**Quick Health Check:**
```bash
# 1. Redis running?
redis-cli ping

# 2. Worker running?
rq info --url redis://localhost:6379

# 3. Web server running?
curl http://localhost:8009/health

# 4. Queue working?
curl http://localhost:8009/api/bots/queue
```

---

**Last Updated:** October 6, 2025  
**Sprint:** 1.2 - Job Queue System  
**Status:** ✅ Complete

