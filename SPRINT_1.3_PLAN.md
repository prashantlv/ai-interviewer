# Sprint 1.3: Database Dependency Injection Fix

**Start Date:** October 6, 2025  
**Estimated Duration:** 2-3 days (but we'll try to finish today!)  
**Status:** 🔄 IN PROGRESS

---

## 🎯 Goal

Fix database dependency injection patterns to use proper FastAPI DI instead of module-level globals and workarounds.

---

## 📋 Current Problems

### Problem #1: Module-Level Globals
**File:** `web_server/routers/dashboard.py`

```python
# Current (BAD):
db_service = None  # Module-level global

@router.get("/dashboard/")
async def dashboard_home(request: Request):
    global db_service  # Using global
    interviews = await db_service.get_interviews()
```

**Issues:**
- Hard to test
- Not thread-safe
- Violates FastAPI best practices
- Requires initialization from main.py

---

### Problem #2: Dashboard Self-HTTP Calls
**File:** `web_server/routers/dashboard.py`

```python
# Current (BAD):
async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8009/debug/interviews")
    interviews = response.json()
```

**Issues:**
- Dashboard calls itself via HTTP
- Unnecessary network overhead
- Potential circular dependencies
- Fragile (depends on server being up)

**Already Fixed:** We solved this in Sprint 1.2 by calling `db_service.get_interviews()` directly.

---

## ✅ Solution: Proper FastAPI Dependency Injection

### Pattern to Use:

```python
# In dependencies.py (NEW FILE)
from fastapi import Depends
from typing import Annotated

async def get_db_service() -> DatabaseService:
    """Dependency for database service"""
    return db_service

# Type alias for cleaner syntax
DbServiceDep = Annotated[DatabaseService, Depends(get_db_service)]

# In routes
@router.get("/dashboard/")
async def dashboard_home(
    request: Request,
    db: DbServiceDep  # Injected automatically!
):
    interviews = await db.get_interviews()
```

**Benefits:**
- ✅ No globals
- ✅ Easy to test (mock the dependency)
- ✅ Type-safe
- ✅ Standard FastAPI pattern
- ✅ Clean and maintainable

---

## 📝 Tasks

### Phase 1: Create Dependencies Module ✅

- [ ] Create `web_server/dependencies.py`
- [ ] Define `get_db_service()` dependency function
- [ ] Define `get_bot_manager()` dependency function
- [ ] Define `get_scoring_config()` dependency function
- [ ] Define `get_question_engine()` dependency function
- [ ] Create type aliases for clean syntax

**Files to Create:**
- `web_server/dependencies.py`

---

### Phase 2: Refactor Dashboard Router ✅

- [ ] Update `dashboard.py` to use DI
- [ ] Remove `global db_service` declarations
- [ ] Remove module-level `db_service = None`
- [ ] Add dependency parameters to all route functions
- [ ] Test all dashboard routes

**Files to Modify:**
- `web_server/routers/dashboard.py`

---

### Phase 3: Refactor Interviews Router ✅

- [ ] Update `interviews.py` to use DI
- [ ] Remove global dependencies
- [ ] Add dependency parameters
- [ ] Test all interview routes

**Files to Modify:**
- `web_server/routers/interviews.py`

---

### Phase 4: Refactor Feedback Router ✅

- [ ] Update `feedback.py` to use DI
- [ ] Add dependency parameters
- [ ] Test feedback routes

**Files to Modify:**
- `web_server/routers/feedback.py`

---

### Phase 5: Update Main Application ✅

- [ ] Remove service initialization from routers
- [ ] Keep initialization in lifespan context
- [ ] Update how services are shared (use app.state)
- [ ] Test startup/shutdown

**Files to Modify:**
- `web_server/main.py`

---

### Phase 6: Testing ✅

- [ ] Test all dashboard routes
- [ ] Test all interview routes
- [ ] Test all feedback routes
- [ ] Test health check
- [ ] Test bot management endpoints
- [ ] Verify no regression

---

## 🔧 Implementation Details

### Step 1: Create dependencies.py

```python
"""
FastAPI Dependencies
Provides dependency injection for services
"""
from typing import Annotated
from fastapi import Depends, Request

from services.database import DatabaseService
from services.bot_manager import BotManager
from services.scoring_config_service import ScoringConfigService
from services.question_engine import QuestionEngine


def get_db_service(request: Request) -> DatabaseService:
    """Get database service from app state"""
    return request.app.state.db_service


def get_bot_manager(request: Request) -> BotManager:
    """Get bot manager from app state"""
    return request.app.state.bot_manager


def get_scoring_config(request: Request) -> ScoringConfigService:
    """Get scoring config service from app state"""
    return request.app.state.scoring_config_service


def get_question_engine(request: Request) -> QuestionEngine:
    """Get question engine from app state"""
    return request.app.state.question_engine


# Type aliases for cleaner route signatures
DbServiceDep = Annotated[DatabaseService, Depends(get_db_service)]
BotManagerDep = Annotated[BotManager, Depends(get_bot_manager)]
ScoringConfigDep = Annotated[ScoringConfigService, Depends(get_scoring_config)]
QuestionEngineDep = Annotated[QuestionEngine, Depends(get_question_engine)]
```

---

### Step 2: Update main.py to use app.state

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await db_service.connect()
    
    # Store services in app state
    app.state.db_service = db_service
    app.state.bot_manager = get_bot_manager()
    app.state.scoring_config_service = scoring_config_service
    app.state.question_engine = question_engine
    
    # Initialize configs
    scoring_config_service.database = db_service.database
    await scoring_config_service.initialize_default_configs()
    
    # Initialize bot manager
    initialize_bot_manager()
    
    print("🚀 FastAPI Web Server started successfully!")
    yield
    
    # Shutdown
    await db_service.disconnect()
    print("🛑 FastAPI Web Server shut down")
```

---

### Step 3: Update Router Example

**Before (dashboard.py):**
```python
db_service = None

@router.get("/dashboard/")
async def dashboard_home(request: Request):
    global db_service
    interviews = await db_service.get_interviews()
```

**After (dashboard.py):**
```python
from dependencies import DbServiceDep

@router.get("/dashboard/")
async def dashboard_home(
    request: Request,
    db: DbServiceDep
):
    interviews = await db.get_interviews()
```

**Much cleaner! ✨**

---

## 🧪 Testing Checklist

After implementation, test:

- [ ] Dashboard loads correctly
- [ ] Recent interviews display
- [ ] Interview list page works
- [ ] Schedule interview works
- [ ] Interview details page works
- [ ] Analytics page works
- [ ] System health page works
- [ ] Bot management endpoints work
- [ ] Health check endpoint works
- [ ] No errors in logs
- [ ] No performance degradation

---

## 📊 Success Metrics

- ✅ Zero module-level globals
- ✅ All routes use FastAPI DI
- ✅ No self-HTTP calls
- ✅ All tests pass
- ✅ Code is cleaner and more maintainable
- ✅ Easy to write unit tests

---

## 🎯 Expected Outcome

**Before:**
```python
# Messy globals
db_service = None
bot_manager = None

def init_routers(db, bm):
    global db_service, bot_manager
    db_service = db
    bot_manager = bm

@router.get("/")
async def route(request: Request):
    global db_service
    # ...
```

**After:**
```python
# Clean DI
from dependencies import DbServiceDep, BotManagerDep

@router.get("/")
async def route(
    request: Request,
    db: DbServiceDep,
    bot_manager: BotManagerDep
):
    # ...
```

**Beautiful! ✨**

---

## 🚀 Let's Do This!

Ready to clean up the code and implement proper DI patterns!

**Estimated Time:** 2-3 hours (if we're focused)

**Let's start with Phase 1: Create dependencies.py**
