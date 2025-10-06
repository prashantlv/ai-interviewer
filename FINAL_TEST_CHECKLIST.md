# Final Test Checklist - Sprint 1.2

**Date:** October 6, 2025  
**Status:** Ready for Testing

---

## Pre-Test Setup

### ✅ Services Running

- [ ] **Redis:** Docker container on port 6379
  ```bash
  docker ps | grep redis
  ```

- [ ] **Web Server:** FastAPI on port 8009
  ```bash
  # Should be running in terminal
  curl http://localhost:8009/health
  ```

- [ ] **RQ Worker:** Running with scheduler
  ```bash
  # In web_server directory:
  rq worker ai_bots --with-scheduler
  ```

### ✅ Environment Variables

- [ ] **Web Server:** `.env` file in `web_server/`
  - `DAILY_API_KEY` set
  - `MONGODB_URI` set
  - `OPENAI_API_KEY` set

- [ ] **Bot Server:** `.env` file in `server/`
  - `DAILY_API_KEY` set
  - `OPENAI_API_KEY` set
  - `WEB_SERVER_URL=http://localhost:8009`
  - `VIDEO_SERVICE=tavus` or `none`

---

## Test 1: Auto-Start Bot (Primary Flow)

### Steps

1. **Schedule Interview**
   - [ ] Visit: http://localhost:8009/dashboard/schedule
   - [ ] Fill in:
     - Candidate Name: `TestUser01`
     - Email: `test@example.com`
     - Position: `Software Engineer`
     - Scoring Level: `Intermediate`
   - [ ] ✅ **Enable "Auto-start AI Bot"** (checked)
   - [ ] Click "Schedule Interview"

2. **Verify Success Page**
   - [ ] Page shows: "Interview Scheduled Successfully"
   - [ ] See interview ID (e.g., `interview_20251006_180000_abc123`)
   - [ ] See "AI Bot Status" green box with:
     - Job ID starting with `interview_...`
     - Status: "Queued"
   - [ ] See "Candidate Join Link" with token (`?t=...`)
   - [ ] **Copy the candidate URL** (will need it later)

3. **Check Worker Logs**
   - [ ] Switch to RQ worker terminal
   - [ ] See these log messages (within 1-2 seconds):
     ```
     ✅ ai_bots: workers.ai_bot_worker.start_interview_bot(...)
     ✅ INFO:workers.ai_bot_worker:🤖 Starting bot worker for interview: ...
     ✅ INFO:workers.ai_bot_worker:📍 Using room URL from config: ...
     ✅ INFO:workers.ai_bot_worker:📝 Command: /home/.../pipecat-env/bin/python ai-interviewer.py --room-url ...
     ✅ INFO:workers.ai_bot_worker:✅ Bot started successfully! PID: ...
     ```

4. **Check Bot Process Logs**
   - [ ] Still in worker terminal, look for bot output:
     ```
     ✅ [Bot interview_...] 🎯 Direct join mode: https://...
     ✅ [Bot interview_...] 📍 Joining room: https://hi2inspire.daily.co/...
     ✅ [Bot interview_...] 🔑 Using token: eyJ...
     ✅ [Bot interview_...] 🚀 Starting bot in direct join mode...
     ✅ [Bot interview_...] INFO: Joining https://hi2inspire.daily.co/...
     ✅ [Bot interview_...] Fetching interview config from: http://localhost:8009/...
     ✅ [Bot interview_...] ✅ Retrieved interview config
     ```

5. **Join as Candidate**
   - [ ] Open the **candidate URL** (from step 2) in a browser
   - [ ] Allow camera/microphone permissions
   - [ ] Should see:
     - [ ] Your video feed
     - [ ] Bot's video (if Tavus enabled) or audio indicator
     - [ ] Daily.co interface
   - [ ] Bot should:
     - [ ] Greet you (audio)
     - [ ] Start asking interview questions
     - [ ] Respond to your answers

6. **Conduct Mini Interview**
   - [ ] Answer 1-2 questions
   - [ ] Hang up when done

7. **Verify Results**
   - [ ] Visit: http://localhost:8009/dashboard/interviews
   - [ ] Find your interview (should be at the top)
   - [ ] Status should be: "completed"
   - [ ] Click "View Results"
   - [ ] Verify:
     - [ ] Transcript is present
     - [ ] Score is calculated (not 0.0 unless very short)
     - [ ] Feedback is shown
     - [ ] Questions asked are listed

---

## Test 2: Manual Start (Fallback)

### Steps

1. **Schedule Interview**
   - [ ] Visit: http://localhost:8009/dashboard/schedule
   - [ ] Fill in interview details
   - [ ] ❌ **Disable "Auto-start AI Bot"** (unchecked)
   - [ ] Click "Schedule Interview"

2. **Verify Success Page**
   - [ ] See "Manual Bot Start Required" yellow box
   - [ ] See command to start bot manually
   - [ ] No job ID shown

3. **Manually Start Bot (Optional Test)**
   - [ ] Copy the command from success page
   - [ ] Open new terminal
   - [ ] Activate conda: `conda activate pipecat-env`
   - [ ] Run the command
   - [ ] Verify bot starts

---

## Test 3: System Health Monitoring

### Steps

1. **Visit System Health Page**
   - [ ] Go to: http://localhost:8009/dashboard/system-health

2. **Verify Job Queue Section**
   - [ ] See "Job Queue (Redis + RQ)" status: ✅ Operational
   - [ ] See "Job Queue Statistics" card with:
     - [ ] Queued Jobs: (number)
     - [ ] Running Jobs: (number)
     - [ ] Finished Jobs: (number)
     - [ ] Active Workers: 1 (if worker running)

3. **Test Auto-Refresh**
   - [ ] Schedule a new interview (auto-start enabled)
   - [ ] Return to system health page
   - [ ] Watch "Finished Jobs" count increase (auto-refreshes every 5 seconds)

---

## Test 4: API Endpoints

### Manual API Testing (Optional)

1. **Start Bot via API**
   ```bash
   curl -X POST http://localhost:8009/api/bots/start?interview_id=test_123
   ```
   - [ ] Response: `{"success": true, "job_id": "interview_test_123", ...}`

2. **Get Bot Status**
   ```bash
   curl http://localhost:8009/api/bots/status/test_123
   ```
   - [ ] Response shows job status

3. **Get Active Bots**
   ```bash
   curl http://localhost:8009/api/bots/active
   ```
   - [ ] Response lists active bots

4. **Get Queue Info**
   ```bash
   curl http://localhost:8009/api/bots/queue
   ```
   - [ ] Response shows queue statistics

---

## Test 5: Error Scenarios

### Test Invalid Room

1. **Manually Test Bot with Bad URL**
   ```bash
   cd server
   python ai-interviewer.py --room-url "https://invalid-room-url.daily.co/nonexistent"
   ```
   - [ ] Bot should error gracefully
   - [ ] See error message about room not existing

### Test Missing Token

1. **Visit Room Without Token**
   - [ ] Take a candidate URL from a scheduled interview
   - [ ] Remove the `?t=...` part
   - [ ] Open in browser
   - [ ] Should see: "You are not allowed to join this meeting"

---

## Success Criteria

### ✅ All Tests Pass If:

- [ ] Bot auto-starts when enabled
- [ ] Bot joins Daily.co room successfully
- [ ] Candidate can join with provided URL
- [ ] Interview proceeds normally (questions asked, answers recorded)
- [ ] Transcript saved to database
- [ ] Score calculated by LLM
- [ ] Results displayed correctly in dashboard
- [ ] System health page shows accurate statistics
- [ ] Manual mode works as fallback
- [ ] No errors in worker logs (except expected ones)
- [ ] No errors in web server logs
- [ ] No bot processes left hanging after interview ends

---

## Troubleshooting

### If Bot Doesn't Join:

1. **Check Worker Logs** for:
   - Python path: Should use conda env (`/home/.../pipecat-env/bin/python`)
   - Command includes: `--room-url`
   - Bot PID is shown
   - No immediate "exit" or error

2. **Check Bot Logs** (in worker output) for:
   - "Direct join mode" message
   - "Joining room" message
   - Token being used
   - Any error messages

3. **Verify Room URL**:
   - URL should be: `https://hi2inspire.daily.co/interview-...`
   - Token should be present: `?t=eyJ...`
   - Room should exist (check web server logs for room creation)

4. **Check Environment**:
   - Bot `.env` has `DAILY_API_KEY`
   - Bot `.env` has `WEB_SERVER_URL=http://localhost:8009`
   - Token hasn't expired (90 minutes)

### If Candidate Can't Join:

1. **Verify URL has token**: `?t=...` should be present
2. **Check if room was created**: Look in web server logs for room creation message
3. **Try regenerating**: Schedule a fresh interview

### If Worker Can't Connect to Redis:

1. **Verify Redis is running**:
   ```bash
   docker ps | grep redis
   ```

2. **Test Redis connection**:
   ```bash
   redis-cli ping  # Should return: PONG
   ```

3. **Restart Redis if needed**:
   ```bash
   docker restart <redis-container-id>
   ```

---

## Completion Report Template

```markdown
## Test Results - Sprint 1.2

**Date:** [DATE]
**Tester:** [NAME]

### Test 1: Auto-Start Bot
- Result: [ ] ✅ PASS / [ ] ❌ FAIL
- Notes:

### Test 2: Manual Start
- Result: [ ] ✅ PASS / [ ] ❌ FAIL
- Notes:

### Test 3: System Health
- Result: [ ] ✅ PASS / [ ] ❌ FAIL
- Notes:

### Test 4: API Endpoints
- Result: [ ] ✅ PASS / [ ] ❌ FAIL / [ ] ⏭️ SKIPPED
- Notes:

### Test 5: Error Scenarios
- Result: [ ] ✅ PASS / [ ] ❌ FAIL / [ ] ⏭️ SKIPPED
- Notes:

### Overall Assessment:
- [ ] ✅ Ready for production
- [ ] ⚠️ Minor issues, acceptable
- [ ] ❌ Major issues, needs fixes

### Issues Found:
1.
2.
3.

### Performance Notes:
- Bot startup time: ~X seconds
- Room join time: ~Y seconds
- Interview flow: (smooth / laggy / issues)
```

---

**Ready to test! Good luck! 🚀**

Report results back and we'll address any issues found.

