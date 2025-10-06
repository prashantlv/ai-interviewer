# Sprint 1.4: API Versioning

**Start Date:** October 6, 2025  
**Estimated Duration:** 1-2 hours  
**Status:** 🔄 IN PROGRESS

---

## 🎯 Goal

Implement API versioning to ensure backward compatibility and future-proof the API for changes.

---

## 📋 Current State

**Problem:**
- All API endpoints are unversioned (e.g., `/api/interviews`, `/api/bots/start`)
- No way to introduce breaking changes without affecting existing clients
- Not production-ready for external integrations

**Example Current URLs:**
```
/api/interviews
/api/feedback/analytics
/api/bots/start
/api/bot/interview-config/{interview_id}
```

---

## ✅ Target State

**After Versioning:**
```
/api/v1/interviews
/api/v1/feedback/analytics
/api/v1/bots/start
/api/v1/bot/interview-config/{interview_id}
```

**Benefits:**
- ✅ Can introduce `/api/v2/` without breaking v1 clients
- ✅ Clear API version in URLs
- ✅ Production-ready API structure
- ✅ Standard industry practice

---

## 📝 Implementation Plan

### Phase 1: Update Router Prefixes ✅

Update `main.py` to add `/v1` prefix to all API routers:

**Before:**
```python
app.include_router(interviews.router, prefix="/api/interviews", tags=["interviews"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
```

**After:**
```python
app.include_router(interviews.router, prefix="/api/v1/interviews", tags=["interviews-v1"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback-v1"])
```

---

### Phase 2: Update Bot Endpoints ✅

Move bot management endpoints under `/api/v1/bots/`:

**Before:**
```python
@app.post("/api/bots/start")
@app.get("/api/bots/status/{interview_id}")
```

**After:**
```python
# Create a new router for bot management
bot_router = APIRouter(prefix="/api/v1/bots", tags=["bots-v1"])

@bot_router.post("/start")
@bot_router.get("/status/{interview_id}")
```

---

### Phase 3: Update Bot Integration Endpoints ✅

Update endpoints that the bot calls:

**Before:**
```python
/api/bot/interview-config/{interview_id}
/api/bot/interview-result
```

**After:**
```python
/api/v1/bot/interview-config/{interview_id}
/api/v1/bot/interview-result
```

---

### Phase 4: Update Bot Script ✅

Update `server/ai-interviewer.py` to use versioned URLs:

**Before:**
```python
config_url = f"{web_server_url}/api/bot/interview-config/{interview_id}"
result_url = f"{web_server_url}/api/bot/interview-result"
```

**After:**
```python
config_url = f"{web_server_url}/api/v1/bot/interview-config/{interview_id}"
result_url = f"{web_server_url}/api/v1/bot/interview-result"
```

---

### Phase 5: Update Dashboard Templates ✅

Update any JavaScript/HTML that calls API endpoints:

**Files to check:**
- `templates/system_health.html` - Queue statistics API call
- Any other templates with API calls

---

### Phase 6: Documentation ✅

Update documentation to reflect new API versioning:

**Files to update:**
- `README.md` - Update API examples
- `ARCHITECTURE.md` - Document versioning strategy
- API documentation (if any)

---

## 🔧 Detailed Implementation

### Step 1: Create Bot Router (NEW)

Create `web_server/routers/bots.py`:

```python
"""
Bot Management Router - API v1
Handles bot lifecycle management and monitoring
"""
from fastapi import APIRouter, Request
from dependencies import BotManagerDep

router = APIRouter()

@router.post("/start")
async def start_bot(
    request: Request,
    bot_manager: BotManagerDep,
    interview_id: str,
    delay: int = 0
):
    """Start an AI bot for an interview"""
    result = bot_manager.schedule_interview(interview_id, delay=delay)
    return result

@router.post("/stop/{interview_id}")
async def stop_bot(
    request: Request,
    bot_manager: BotManagerDep,
    interview_id: str,
    force: bool = False
):
    """Stop a running interview bot"""
    result = bot_manager.stop_bot(interview_id, force=force)
    return result

# ... more endpoints
```

---

### Step 2: Update main.py

```python
# Import bot router
from routers import interviews, dashboard, feedback, bots

# Include routers with v1 prefix
app.include_router(
    interviews.router,
    prefix="/api/v1/interviews",
    tags=["interviews-v1"]
)
app.include_router(
    feedback.router,
    prefix="/api/v1/feedback",
    tags=["feedback-v1"]
)
app.include_router(
    bots.router,
    prefix="/api/v1/bots",
    tags=["bots-v1"]
)

# Bot integration endpoints (still in main.py but versioned)
@app.get("/api/v1/bot/interview-config/{interview_id}")
async def get_bot_interview_config(...):
    ...

@app.post("/api/v1/bot/interview-result")
async def receive_interview_result(...):
    ...
```

---

### Step 3: Update ai-interviewer.py

```python
# In fetch_interview_config function
config_url = f"{web_server_url}/api/v1/bot/interview-config/{interview_id}"

# In send_interview_results function
result_url = f"{web_server_url}/api/v1/bot/interview-result"
```

---

### Step 4: Update Templates

**system_health.html:**
```javascript
// Before
fetch('/api/bots/queue')

// After
fetch('/api/v1/bots/queue')
```

---

## 🧪 Testing Checklist

After implementation:

- [ ] `/api/v1/health` works (or keep `/health` unversioned)
- [ ] `/api/v1/interviews` endpoint works
- [ ] `/api/v1/feedback/analytics` works
- [ ] `/api/v1/bots/start` works
- [ ] `/api/v1/bots/queue` works
- [ ] Bot can fetch config from `/api/v1/bot/interview-config/`
- [ ] Bot can post results to `/api/v1/bot/interview-result`
- [ ] Dashboard queue stats work (system health page)
- [ ] API docs reflect v1 endpoints
- [ ] No broken links in templates

---

## 📊 Files to Modify

1. ✅ **`web_server/routers/bots.py`** (NEW)
   - Extract bot management endpoints from main.py
   
2. ✅ **`web_server/main.py`**
   - Update router prefixes
   - Version bot integration endpoints
   - Remove bot management endpoints (moved to bots.py)

3. ✅ **`server/ai-interviewer.py`**
   - Update API URLs to use /api/v1/

4. ✅ **`web_server/templates/system_health.html`**
   - Update queue API endpoint

5. ✅ **Documentation files**
   - Update examples and references

---

## 🎯 Success Criteria

- ✅ All API endpoints under `/api/v1/`
- ✅ Bot integration working with versioned URLs
- ✅ Dashboard functionality intact
- ✅ No breaking changes to existing functionality
- ✅ API documentation updated
- ✅ Tests pass

---

## 📝 Version Strategy Document

Create `API_VERSIONING.md`:

```markdown
# API Versioning Strategy

## Current Version: v1

### Versioning Scheme
- URL-based versioning: `/api/v{version}/`
- Current version: v1
- Future versions: v2, v3, etc.

### Version Lifecycle
1. **Active** - Current recommended version
2. **Deprecated** - Still supported, but migrate away
3. **Sunset** - No longer supported

### Current Status
- **v1**: Active (October 2025 - Present)

### Breaking Changes Policy
- Breaking changes require new API version
- Non-breaking changes can be added to existing version
- Deprecated versions supported for minimum 6 months

### Examples
- v1: `/api/v1/interviews`
- v2 (future): `/api/v2/interviews`
```

---

## 🚀 Let's Implement!

**Estimated time:** 1-2 hours

**Steps:**
1. Create bots router
2. Update main.py
3. Update bot script
4. Update templates
5. Test everything
6. Update documentation

**Ready to start!**
