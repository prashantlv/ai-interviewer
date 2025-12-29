# 🚨 CRITICAL FIX: Duplicate Bot Spawning

## Problem Summary
- **Multiple bot processes** spawning for same interview
- **Two AI Interviewer Bots** appearing in call (one with avatar, one without)
- **AI not speaking** due to bot conflicts
- **Resource exhaustion** from duplicate Tavus conversations
- **RTVI validation errors** from conflicting bots

## Root Cause
The in-memory `_bot_start_locks` dictionary in `web_server/routers/proctoring.py` **doesn't work across multiple uvicorn worker processes**. Each worker has its own memory space, so locks aren't shared.

When multiple requests come in (page loads, refreshes, etc.), different workers can all schedule bots for the same interview.

## The Fix
**Commit:** `ded3f29` (and `23b12e0`)

### Changes Made:
1. **Redis Distributed Locking** - Replaced in-memory dict with Redis SET NX (atomic)
2. **Lock TTL** - 2-hour expiry prevents stuck locks if bot crashes
3. **Lock Cleanup** - Release lock when interview ends
4. **Cross-Process** - Works across all uvicorn workers

### Files Changed:
- `web_server/routers/proctoring.py` - Redis locking implementation
- `cleanup-duplicate-bots.sh` - Utility to kill duplicate bots

---

## 🚀 Deployment Steps (EC2)

### Step 1: Kill All Running Duplicate Bots

SSH into EC2 and run:

```bash
cd /home/ubuntu/ai-interviewer

# Download and run cleanup script
git pull origin main
chmod +x cleanup-duplicate-bots.sh
./cleanup-duplicate-bots.sh
```

**Expected Output:**
```
🧹 Cleaning up duplicate AI bot processes...

1️⃣ Killing all ai-interviewer.py processes...
[killed X processes]

2️⃣ Clearing all Redis bot locks...
[cleared Y locks]

3️⃣ Clearing RQ job queue...
[queue cleared]

4️⃣ Current status:
   Active bot processes: 0
   Redis bot locks: 0
   RQ jobs in queue: 0

✅ Cleanup complete!
```

### Step 2: Rebuild and Restart Docker

```bash
cd /home/ubuntu/ai-interviewer

# Stop all containers
docker compose down

# Rebuild with new code
docker compose build

# Start services
docker compose up -d

# Check logs
docker compose logs -f web
```

### Step 3: Verify Fix

```bash
# Check only ONE bot starts per interview
docker compose logs -f worker | grep "Starting bot for interview"

# Should see:
# ✅ Bot scheduled: ...
# ⏸️ Bot start already in progress for interview: ... (Redis lock held)
# ⏸️ Bot start already in progress for interview: ... (Redis lock held)
```

### Step 4: Test Interview

1. Open interview room: `https://api.human2intelligence.com/dashboard/`
2. Schedule test interview
3. Join interview room
4. **Verify:**
   - ✅ Only **1** "AI Interviewer Bot" in call
   - ✅ Bot has Tavus avatar
   - ✅ Bot greets candidate within 2-3 seconds
   - ✅ Bot responds to candidate speech
   - ✅ No RTVI validation errors in logs

---

## 🔍 Monitoring Commands

### Check Running Bot Processes
```bash
# On EC2 (direct)
ps aux | grep ai-interviewer.py | grep -v grep

# In Docker
docker exec ai-interviewer-worker ps aux | grep python
```

### Check Redis Locks
```bash
# List all bot locks
docker exec ai-interviewer-redis redis-cli --scan --pattern "bot_lock:*"

# Check specific interview lock
docker exec ai-interviewer-redis redis-cli GET "bot_lock:interview_20251229_070306_7dc9fc5c"
```

### Check RQ Job Queue
```bash
# Queue length
docker exec ai-interviewer-redis redis-cli LLEN rq:queue:ai_bots

# Running jobs
docker exec ai-interviewer-redis redis-cli SMEMBERS rq:queue:ai_bots:started
```

### Watch Bot Logs
```bash
# Real-time bot scheduling
docker compose logs -f worker | grep -E "Starting bot|already in progress|Bot scheduled"

# Greeting/speaking
docker compose logs -f worker | grep -E "Bot ready|greeting|Real participant joined"

# Errors
docker compose logs -f worker | grep ERROR
```

---

## 🧪 Test Scenarios

### Scenario 1: Single Page Load
**Expected:** ONE bot starts, lock prevents duplicates

```bash
# Watch logs
docker compose logs -f worker | grep "interview_TEST123"

# Load page once
# Should see:
# 🤖 Starting bot for interview: TEST123
# ✅ Bot scheduled: ...
```

### Scenario 2: Page Refresh
**Expected:** No new bot, lock held

```bash
# Refresh page 5 times quickly
# Should see:
# ⏸️ Bot start already in progress for interview: TEST123 (Redis lock held)
# ⏸️ Bot start already in progress for interview: TEST123 (Redis lock held)
# ⏸️ Bot start already in progress for interview: TEST123 (Redis lock held)
# ⏸️ Bot start already in progress for interview: TEST123 (Redis lock held)
```

### Scenario 3: AI Greeting
**Expected:** Bot greets candidate within 2-3 seconds

```bash
# Join call as candidate
# Should see in logs:
# 👤 Real participant joined: [Name]
# 🎯 Triggering greeting fallback (if needed)
# 🤖 AI: Hello...
```

### Scenario 4: Multiple Workers
**Expected:** Lock works across all workers

```bash
# If you have multiple web server workers, all should respect the same Redis lock
# Only ONE bot starts regardless of which worker handles the request
```

---

## 🐛 Troubleshooting

### Issue: Bot Still Not Speaking
**Check:**
```bash
# Look for greeting trigger
docker compose logs worker | grep -E "greeting|Bot ready|LLMRunFrame"

# Check Tavus connection
docker compose logs worker | grep Tavus

# Check for errors
docker compose logs worker | grep -E "ERROR|Failed"
```

### Issue: Multiple Bots Still Appearing
**Check:**
```bash
# Verify Redis is running
docker compose ps redis

# Test Redis connection
docker exec ai-interviewer-redis redis-cli PING
# Should return: PONG

# Check if locks are being set
docker exec ai-interviewer-redis redis-cli MONITOR
# Then load interview page - should see SET bot_lock:...
```

### Issue: Bot Never Starts
**Check:**
```bash
# RQ worker running?
docker compose ps worker

# Redis queue?
docker exec ai-interviewer-redis redis-cli LLEN rq:queue:ai_bots

# Worker logs?
docker compose logs worker --tail 100
```

---

## 📊 Success Metrics

After deploying this fix, you should see:

| Metric | Before | After |
|--------|--------|-------|
| Bots per interview | 2-20+ | 1 |
| Tavus conversations | Multiple | 1 |
| AI greeting time | Never | 2-3 sec |
| RTVI errors | Many | None |
| CPU usage | High | Normal |
| Memory usage | High | Normal |

---

## 🔄 Rollback Plan

If issues occur:

```bash
cd /home/ubuntu/ai-interviewer
git revert ded3f29 23b12e0
docker compose down
docker compose build
docker compose up -d
```

---

## 📝 Notes

- Redis locks auto-expire after 2 hours (prevents stuck locks)
- Lock is released when interview ends (via `/api/interview/{id}/end`)
- Cleanup script can be run anytime to kill stuck bots
- Works with any number of uvicorn workers

---

## ✅ Deployment Checklist

- [ ] SSH into EC2
- [ ] Run `git pull origin main`
- [ ] Run `./cleanup-duplicate-bots.sh`
- [ ] Run `docker compose down`
- [ ] Run `docker compose build`
- [ ] Run `docker compose up -d`
- [ ] Watch logs: `docker compose logs -f worker`
- [ ] Test interview
- [ ] Verify only 1 bot joins
- [ ] Verify bot speaks
- [ ] Monitor for 10 minutes

---

**Deploy Time:** ~5 minutes  
**Downtime:** ~2 minutes (during rebuild)  
**Risk Level:** Low (can rollback in 3 minutes)

