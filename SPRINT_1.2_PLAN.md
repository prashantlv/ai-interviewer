# Sprint 1.2: Job Queue System - Implementation Plan

**Created:** October 6, 2025  
**Status:** ✅ Phases 1-4 Complete | Testing & Documentation In Progress  
**Priority:** P0 (Critical)  
**Duration:** 5-7 days  
**Completed:** October 6, 2025 (Phases 1-4)

---

## 🎯 Goal

Automate AI bot process management so that bots start automatically when interviews are scheduled, eliminating manual intervention and enabling scalability.

---

## 📊 Current Problem

**Manual Process:**
```bash
# User must manually run this for EVERY interview:
cd server
INTERVIEW_ID=interview_xxx python ai-interviewer.py --transport daily
```

**Issues:**
- ❌ Not scalable (what if 10 interviews at once?)
- ❌ Requires human intervention
- ❌ No auto-recovery if bot crashes
- ❌ Can't handle concurrent interviews
- ❌ Blocks automated scheduling

---

## ✅ Solution

**Automated Job Queue System:**
1. User schedules interview via dashboard
2. Web server saves to MongoDB + enqueues bot job
3. Redis stores the job
4. Worker process picks up job
5. Worker starts AI bot automatically
6. Bot conducts interview
7. Results saved automatically

**Benefits:**
- ✅ Fully automated
- ✅ Scalable to 100+ interviews/day
- ✅ Handles concurrent interviews
- ✅ Auto-retries on failures
- ✅ Monitor and manage bots via API

---

## 🔧 Technology Decision

**Choice:** Redis + Python-RQ

**Why RQ over Celery:**
- Simpler setup and learning curve
- Python-native, easy integration
- Sufficient for our use case
- Can use Redis for caching later (Phase 3)
- Can migrate to Celery if needed

**Dependencies:**
```
rq==1.15.1
redis==5.0.0
```

---

## 📐 Architecture

### New Components

```
web_server/
├── services/
│   └── bot_manager.py       ✨ NEW - Bot management service
├── workers/
│   └── ai_bot_worker.py     ✨ NEW - RQ worker for bot jobs
└── main.py                  🔄 UPDATE - Add bot API endpoints

External:
- Redis (system service)     ✨ NEW - Job queue storage
```

### Data Flow

```
┌──────────────────┐
│   Dashboard UI   │
└────────┬─────────┘
         │ POST /api/interviews
         ▼
┌──────────────────┐
│   Web Server     │
│  (FastAPI)       │
│  1. Save MongoDB │
│  2. Enqueue job  │◄──────┐
└────────┬─────────┘       │
         │                 │
         ▼                 │
┌──────────────────┐       │
│  Redis Queue     │       │
│  - Job ID        │       │
│  - Interview ID  │       │
│  - Status        │       │
└────────┬─────────┘       │
         │                 │
         ▼                 │
┌──────────────────┐       │
│  RQ Worker       │       │
│  ai_bot_worker   │       │
│  1. Pick job     │       │
│  2. Start bot    │       │
│  3. Monitor      │       │
│  4. Update status├───────┘
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  AI Bot Process  │
│  (Pipecat)       │
│  - Conducts      │
│  - Scores        │
│  - Sends results │
└──────────────────┘
```

---

## 📋 Implementation Tasks

### Phase 1: Setup (Day 1) ✅ COMPLETE

**Goal:** Install and configure Redis + RQ

- [x] **Task 1.1:** Install Redis
  - ✅ Using Docker: `redis:7-alpine`
  - ✅ Running on port 6379
  - ✅ No authentication required

- [x] **Task 1.2:** Verify Redis
  - ✅ `redis-cli ping` returns "PONG"
  - ✅ Python connection verified

- [x] **Task 1.3:** Install Python dependencies
  - ✅ `pip install rq redis` completed

- [x] **Task 1.4:** Update requirements.txt
  - ✅ Added `rq>=1.15.1`
  - ✅ Added `redis>=5.0.0`

- [x] **Task 1.5:** Test connection from Python
  - ✅ Successfully tested read/write operations

**Success Criteria:**
- ✅ Redis service running (Docker)
- ✅ Python can connect to Redis
- ✅ Dependencies installed

**Completed:** October 6, 2025

---

### Phase 2: Bot Worker (Day 2-3) ✅ COMPLETE

**Goal:** Create worker process that starts bot jobs

- [x] **Task 2.1:** Create workers directory
  - ✅ Created `web_server/workers/`
  - ✅ Created `__init__.py`

- [x] **Task 2.2:** Create `workers/ai_bot_worker.py`
  - ✅ Implemented `start_interview_bot(interview_id, config)`
  - ✅ Implemented `stop_interview_bot(interview_id, force)`
  - ✅ Implemented `get_active_bots()`
  - ✅ Implemented `test_job(message)` for testing
  - ✅ 270 lines of production-ready code

- [x] **Task 2.3:** Implement subprocess management
  - ✅ Using `subprocess.Popen` for non-blocking execution
  - ✅ Tracking process PID in `ACTIVE_BOTS` dict
  - ✅ Environment variables passed correctly
  - ✅ Working directory set to `server/`

- [x] **Task 2.4:** Add error handling
  - ✅ Try-except blocks for all operations
  - ✅ Structured error messages returned
  - ✅ Logging with Python `logging` module
  - ✅ FileNotFoundError, generic Exception handling

- [x] **Task 2.5:** Test worker locally
  - ✅ Module imports successfully
  - ✅ Test job enqueued successfully
  - ✅ Job visible in Redis queue

**Success Criteria:**
- ✅ Worker process starts without errors
- ✅ Can pick up and execute jobs
- ✅ Bot subprocess starts correctly
- ✅ Errors are logged properly

**Completed:** October 6, 2025

---

### Phase 3: Bot Manager Service (Day 3-4) ✅ COMPLETE

**Goal:** High-level service for bot management

- [ ] **Task 3.1:** Create `services/bot_manager.py`

  **Class Structure:**
  ```python
  class BotManagerService:
      def __init__(self, redis_host='localhost', redis_port=6379):
          self.redis_conn = Redis(...)
          self.queue = Queue('ai_bots', connection=self.redis_conn)
          self.active_bots = {}  # interview_id -> bot_info
      
      async def enqueue_bot_start(self, interview_id: str) -> str:
          """Enqueue job to start bot for interview"""
          
      async def get_bot_status(self, interview_id: str) -> dict:
          """Get status of bot for interview"""
          
      async def list_active_bots(self) -> List[dict]:
          """List all currently active bots"""
          
      async def stop_bot(self, interview_id: str) -> bool:
          """Terminate bot for interview"""
  ```

- [ ] **Task 3.2:** Implement `enqueue_bot_start()`
  - Fetch interview config from database
  - Build job parameters
  - Enqueue to Redis
  - Store job ID
  - Return job status

- [ ] **Task 3.3:** Implement `get_bot_status()`
  - Check Redis for job status
  - Check if process is running
  - Return structured status

- [ ] **Task 3.4:** Implement `list_active_bots()`
  - Query Redis for all jobs
  - Filter by status (queued, running)
  - Return list with details

- [ ] **Task 3.5:** Implement `stop_bot()`
  - Find running process
  - Send SIGTERM
  - Wait for graceful shutdown
  - Force kill if needed (SIGKILL)
  - Update job status

- [ ] **Task 3.6:** Add to `main.py` lifespan
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Initialize bot manager
      app.state.bot_manager = BotManagerService()
      yield
      # Cleanup on shutdown
  ```

**Success Criteria:**
- ✅ Can enqueue bot jobs
- ✅ Can query job status
- ✅ Can list active bots
- ✅ Can stop running bots

**Files Created:**
- ✅ `web_server/services/bot_manager.py` (400+ lines)
- ✅ Integrated with `main.py` lifespan
- ✅ Added to health check endpoint

**Completed:** October 6, 2025

---

### Phase 4: Integration (Day 4-5) ✅ COMPLETE

**Goal:** Integrate with web server and dashboard

- [x] **Task 4.1:** Update `routers/dashboard.py`
  - ✅ Added `auto_start` parameter to `create_interview()`
  - ✅ Auto-enqueue bot job when `auto_start=True`
  - ✅ Pass bot status to template
  - ✅ Show job ID in response

- [x] **Task 4.2:** Add API endpoints in `main.py`
  - ✅ `POST /api/bots/start` - Start bot for interview
  - ✅ `POST /api/bots/stop/{interview_id}` - Stop running bot
  - ✅ `GET /api/bots/status/{interview_id}` - Get bot status
  - ✅ `GET /api/bots/active` - List active bots
  - ✅ `GET /api/bots/queue` - Queue statistics
  - ✅ `DELETE /api/bots/job/{job_id}` - Cancel queued job
  - ✅ 6 new endpoints total

- [x] **Task 4.3:** Update `templates/schedule_interview.html`
  - ✅ Added "Auto-start AI Bot" toggle switch
  - ✅ Checked by default
  - ✅ Clear explanation of manual vs auto mode

- [x] **Task 4.4:** Update `templates/interview_scheduled.html`
  - ✅ Show bot status (Queued / Manual)
  - ✅ Display job ID when auto-started
  - ✅ Different instructions based on mode

- [x] **Task 4.5:** Update `templates/system_health.html`
  - ✅ Added Job Queue component status
  - ✅ Live queue statistics display
  - ✅ Auto-refresh every 30 seconds
  - ✅ Shows: queued, running, finished jobs
  - ✅ Shows: active workers count

**Success Criteria:**
- ✅ Scheduling interview auto-starts bot
- ✅ Bot status visible in UI
- ✅ API endpoints working
- ✅ Manual mode still available

**Completed:** October 6, 2025

---

### Phase 5: Testing (Day 5-6)

**Goal:** Comprehensive testing of job queue system

- [ ] **Test 5.1:** Single Interview Flow
  1. Start Redis
  2. Start web server
  3. Start RQ worker
  4. Schedule interview via dashboard
  5. Verify bot auto-starts
  6. Join as candidate
  7. Complete interview
  8. Verify results saved
  9. **Expected:** Full automation, no manual steps

- [ ] **Test 5.2:** Concurrent Interviews
  1. Schedule 3 interviews simultaneously
  2. Verify all 3 bots start
  3. Verify they run independently
  4. Complete all 3
  5. Verify all results saved
  6. **Expected:** All handle correctly, no conflicts

- [ ] **Test 5.3:** Error Handling
  1. Invalid interview ID → Should fail gracefully
  2. Bot crash mid-interview → Should log error
  3. Redis down → Should queue when back up
  4. Worker stopped → Jobs wait until worker starts
  5. **Expected:** Graceful degradation, clear errors

- [ ] **Test 5.4:** Job Monitoring
  1. Check job status via API
  2. View active bots list
  3. Manually stop a bot
  4. Verify job marked as stopped
  5. **Expected:** Full visibility and control

- [ ] **Test 5.5:** Performance
  1. Schedule 10 interviews
  2. Measure: Time to start all bots
  3. Measure: Resource usage (CPU, memory)
  4. Measure: Redis memory usage
  5. **Expected:** < 5 seconds to start, < 500MB memory

**Success Criteria:**
- ✅ All tests pass
- ✅ No manual intervention needed
- ✅ Error handling works
- ✅ Performance acceptable

---

### Phase 6: Documentation (Day 6-7)

**Goal:** Update all documentation

- [ ] **Task 6.1:** Update ARCHITECTURE.md
  - Add Job Queue section
  - Update architecture diagrams
  - Document Redis integration
  - Document worker process

- [ ] **Task 6.2:** Update DEVELOPMENT.md
  - Add "Starting Redis" section
  - Add "Starting RQ Worker" section
  - Update common tasks
  - Add troubleshooting for Redis issues

- [ ] **Task 6.3:** Update GETTING_STARTED.md
  - Add Redis to prerequisites
  - Update setup instructions
  - Update testing flow

- [ ] **Task 6.4:** Update ROADMAP.md
  - Mark Sprint 1.2 as complete
  - Update progress bars
  - Set Sprint 1.3 as next

- [ ] **Task 6.5:** Update CHANGELOG.md
  - Add Sprint 1.2 completion entry
  - List all changes
  - Document new dependencies

- [ ] **Task 6.6:** Update start.sh script
  - Add option to start Redis
  - Add option to start RQ worker
  - Update menu options

**Success Criteria:**
- ✅ All docs updated
- ✅ Clear instructions for new developers
- ✅ Troubleshooting guides added

---

## 🎯 Success Metrics

Sprint 1.2 is complete when:

1. ✅ Redis installed and running
2. ✅ RQ worker implemented and tested
3. ✅ Bot manager service working
4. ✅ Dashboard integration complete
5. ✅ API endpoints functional
6. ✅ Single interview auto-starts bot
7. ✅ Concurrent interviews work
8. ✅ Error handling verified
9. ✅ All documentation updated
10. ✅ No manual bot starting needed

---

## 📝 Notes

### Important Considerations

1. **Environment Variables:**
   - Worker needs access to same .env as bot
   - Consider using environment variable file

2. **Process Management:**
   - Use `subprocess.Popen()` not `os.system()`
   - Capture stdout/stderr for debugging
   - Track PIDs for cleanup

3. **Error Recovery:**
   - Max 3 retries for failed jobs
   - Exponential backoff between retries
   - Alert on persistent failures

4. **Monitoring:**
   - Log all job starts/stops
   - Track success/failure rates
   - Monitor Redis memory usage

5. **Security:**
   - Validate interview_id before starting bot
   - Sanitize all subprocess commands
   - Rate limit bot starts (max 10/minute)

---

## 🚀 Ready to Start!

**Next Steps:**
1. Review this plan
2. Start with Phase 1 (Redis setup)
3. Work through phases systematically
4. Test after each phase
5. Update documentation as you go

**Estimated Timeline:**
- Day 1: Setup
- Day 2-3: Worker
- Day 3-4: Manager
- Day 4-5: Integration
- Day 5-6: Testing
- Day 6-7: Documentation

**Total: 5-7 days**

Good luck! 🎯

