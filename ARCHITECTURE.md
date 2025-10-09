# AI Interviewer - Technical Architecture Document

**Version:** 1.0  
**Last Updated:** October 6, 2025  
**Status:** Active Development  

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture](#current-architecture)
3. [Identified Issues](#identified-issues)
4. [Target Architecture](#target-architecture)
5. [Migration Roadmap](#migration-roadmap)
6. [Technical Decisions Log](#technical-decisions-log)
7. [Development Guidelines](#development-guidelines)

---

## 1. Executive Summary

### Project Overview
AI Interviewer is an automated interview system that conducts voice-based technical interviews using AI, evaluates candidates, and provides detailed feedback through a web dashboard.

### Current Status
- ✅ **Working MVP** - Core functionality operational
- ⚠️ **Production-Ready** - No (requires refactoring)
- 📊 **Architecture Grade** - 6.5/10
- 🎯 **Next Phase** - Systematic improvements following this roadmap

### Key Components
- **Web Server** (FastAPI) - Dashboard + API
- **AI Bot** (Pipecat) - Voice interview conductor
- **Database** (MongoDB) - Data persistence
- **Video Platform** (Daily.co) - WebRTC infrastructure

---

## 2. Current Architecture

### 2.1 System Diagram (As-Is)

```
┌─────────────────────────────────────────────────┐
│           Web Browser (Client)                   │
│  • Dashboard (Jinja2 templates)                 │
│  • Interview scheduling UI                      │
└─────────────────┬───────────────────────────────┘
                  │ HTTP
┌─────────────────▼───────────────────────────────┐
│         Web Server (FastAPI)                     │
│  • main.py (API + Dashboard routes)             │
│  • routers/dashboard.py                         │
│  • services/database.py                         │
│  Port: 8009                                     │
└─────────────────┬───────────────────────────────┘
                  │
          ┌───────┴────────┐
          │                │
          ▼                ▼
┌─────────────┐    ┌──────────────────────┐
│   MongoDB   │    │   AI Bot Process     │
│  Database   │    │   (Pipecat)          │
│             │    │   • Manually started │
│             │    │   • One per interview│
└─────────────┘    └──────────┬───────────┘
                              │
                      ┌───────▼────────┐
                      │   Daily.co     │
                      │   (WebRTC)     │
                      └────────────────┘
```

### 2.2 Directory Structure

```
ai-interviewer/
├── web_server/
│   ├── main.py                    # Main FastAPI app (API + Dashboard)
│   ├── routers/
│   │   └── dashboard.py           # Dashboard routes
│   ├── services/
│   │   └── database.py            # MongoDB service
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── interviews.html
│   │   └── interview_result.html
│   └── static/                    # CSS, JS, images
│
├── server/                        # AI Bot
│   ├── ai-interviewer.py          # Main bot script
│   ├── bot-openai.py              # OpenAI integration
│   ├── bot-gemini.py              # Gemini integration
│   └── requirements.txt
│
├── client/                        # Client applications
│   ├── javascript/
│   ├── react/
│   └── react-native/
│
└── README.md
```

### 2.3 Data Flow

**Interview Scheduling Flow:**
```
1. User schedules interview → Web Dashboard
2. Web Server saves to MongoDB
3. Interview ID generated
4. User manually starts AI Bot with Interview ID
5. Bot fetches config from Web Server API
6. Candidate joins Daily.co room
7. AI conducts interview
8. Bot sends results to Web Server API
9. Web Server saves to MongoDB
10. Results visible on Dashboard
```

### 2.4 Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Backend API | FastAPI | 0.104+ | Web server & API |
| Database | MongoDB | 6.0+ | Data storage |
| AI Framework | Pipecat | Latest | Voice AI pipelines |
| LLM | OpenAI GPT-4 | Latest | Conversation & scoring |
| STT | Deepgram | Latest | Speech-to-text |
| TTS | Cartesia | Latest | Text-to-speech |
| WebRTC | Daily.co | Latest | Video/audio calls |
| Templates | Jinja2 | 3.1+ | Server-side rendering |
| Python | 3.11+ | 3.11+ | Runtime |

---
### 2.5 Real-time Interview Pipeline (As Implemented)

This section documents the exact, production-tested pipeline currently used during a live interview. It clarifies the roles of Daily.co, Tavus, OpenAI services, and the current (non)role of ElevenLabs.

```
Candidate Browser (Daily.co) ── WebRTC ─▶ Daily Room (hi2inspire.daily.co)
                                                │
                                                ▼
                                     Bot (Pipecat Pipeline)
                                     ─────────────────────────────────────────
                                     1) Audio In: DailyTransport.input()
                                     2) STT: OpenAI Whisper → Text
                                     3) LLM: OpenAI GPT-4o-mini → Response Text
                                     4) TTS: OpenAI TTS (voice="onyx") → Audio
                                     5) Video: TavusVideoService (lip‑sync) → Frames
                                     6) Output: DailyTransport.output() → Candidate sees/hears bot
```

- Meeting room service: Daily.co (room creation and tokens managed by `web_server/services/daily_service.py`).
- Video avatar: Tavus replica via `TavusVideoService` for video frames only (lip‑sync from our audio).
- Audio stack:
  - STT: OpenAI Whisper
  - LLM: OpenAI GPT‑4o‑mini
  - TTS: OpenAI TTS with `voice="onyx"` (male; chosen to match Tavus male avatar)
- Transport: DailyTransport streams audio/video into the Daily.co room in real‑time.

Important clarifications:
- We are NOT using Tavus Conversational API. Tavus is used strictly for video rendering (replica lip‑sync) from our own audio.
- Tavus billing impact is for video rendering/streaming minutes, not “conversational minutes.”
- ElevenLabs is NOT currently used in the pipeline. It’s optional for future TTS; today we use OpenAI TTS.

Implications:
- Maximum control and modularity (we own STT/LLM/TTS choices).
- Predictable costs: OpenAI (STT/LLM/TTS) + Tavus (video frames) + Daily (room/recording).
- Easy to swap voice (OpenAI TTS voice) without touching Tavus replicas.

---

## 3. Identified Issues

### 3.1 Critical Issues 🔴

#### Issue #1: Tight Coupling Between Components
**Problem:**
- AI Bot directly calls Web Server HTTP endpoints
- If Web Server is down, Bot can't start
- Hard to test components in isolation

**Impact:** High  
**Priority:** P0  
**Status:** ⏳ Pending

---

#### Issue #2: Manual Bot Process Management
**Problem:**
```bash
# Current: Must manually run for each interview
INTERVIEW_ID=xxx python ai-interviewer.py --transport daily
```
- Not scalable
- Requires human intervention
- No automatic recovery
- Can't handle concurrent interviews

**Impact:** Critical (blocks scalability)  
**Priority:** P0  
**Status:** ⏳ Pending

---

#### Issue #3: Mock Scoring System
**Problem:**
- Current scoring uses hardcoded values
- No real LLM-based evaluation
- Not useful for actual candidate assessment

**Impact:** High (core feature not working)  
**Priority:** P0  
**Status:** ⏳ Pending

---

### 3.2 Medium Priority Issues 🟡

#### Issue #4: Monolithic Web Server
**Problem:**
- API and UI tightly coupled
- Can't scale independently
- Hard to maintain

**Impact:** Medium  
**Priority:** P1  
**Status:** ⏳ Pending

---

#### Issue #5: No Proper Engine Layer
**Problem:**
- No Question Generation Engine
- No Resume Parsing Engine
- No Job Matching Engine
- Business logic scattered across files

**Impact:** Medium  
**Priority:** P1  
**Status:** ⏳ Pending

---

#### Issue #6: Database Access Pattern Issues
**Problem:**
- Dashboard makes HTTP calls to itself
- Module-level globals for DB service
- Workarounds due to improper dependency injection

**Impact:** Medium  
**Priority:** P1  
**Status:** ⏳ Pending

---

### 3.3 Minor Issues 🟢

#### Issue #7: No API Versioning
**Impact:** Low  
**Priority:** P2  
**Status:** ⏳ Pending

#### Issue #8: Missing Production Services
- No authentication/authorization
- No rate limiting
- No caching layer
- No monitoring/logging
- No email notifications

**Impact:** Low (for MVP)  
**Priority:** P2  
**Status:** ⏳ Pending

---

## 4. Target Architecture

### 4.1 Target System Diagram (To-Be)

```
┌─────────────────────────────────────────────────────────────┐
│                  FRONTEND (Separate App)                     │
│  React/Next.js - Modern SPA                                 │
│  • Dashboard UI                                             │
│  • Interview Management                                     │
│  • Real-time updates (WebSocket)                           │
└─────────────────┬───────────────────────────────────────────┘
                  │ REST API / GraphQL
┌─────────────────▼───────────────────────────────────────────┐
│                     API GATEWAY (Optional)                   │
│  Nginx / Kong / AWS API Gateway                             │
│  • Authentication                                           │
│  • Rate limiting                                            │
│  • Load balancing                                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┬──────────────┬─────────────┐
        ▼                   ▼              ▼             ▼
┌───────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐
│  Interview    │  │  Candidate  │  │ Scoring  │  │   Bot    │
│   Service     │  │   Service   │  │ Service  │  │ Manager  │
│   (FastAPI)   │  │  (FastAPI)  │  │(FastAPI) │  │(FastAPI) │
└───────┬───────┘  └──────┬──────┘  └────┬─────┘  └────┬─────┘
        │                 │               │             │
        └─────────────────┴───────────────┴─────────────┘
                          │
                ┌─────────▼────────┐
                │  Message Queue   │
                │  Redis / RabbitMQ│
                │  • Job scheduling│
                │  • Event bus     │
                └─────────┬────────┘
                          │
        ┌─────────────────┴───────────────┬─────────────┐
        ▼                                 ▼             ▼
┌───────────────┐               ┌─────────────┐  ┌──────────┐
│   MongoDB     │               │  AI Workers │  │  Redis   │
│  (Primary DB) │               │  Pool       │  │ (Cache)  │
│               │               │  • Auto-scale│  │          │
└───────────────┘               └─────────────┘  └──────────┘
                                      │
                              ┌───────▼────────┐
                              │  Daily.co      │
                              │  (WebRTC)      │
                              └────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ENGINE LAYER (Reusable)                   │
│  engines/                                                    │
│  ├── question_generator.py  # LLM-based question gen       │
│  ├── scoring_engine.py      # Real interview scoring       │
│  ├── resume_parser.py       # Extract structured data      │
│  └── job_matcher.py         # Skills matching              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Target Directory Structure

```
ai-interviewer/
├── docs/
│   ├── ARCHITECTURE.md           # This document
│   ├── API.md                    # API documentation
│   ├── DEPLOYMENT.md             # Deployment guide
│   └── DEVELOPMENT.md            # Development guide
│
├── backend/                      # Backend services
│   ├── api/                      # API layer
│   │   ├── v1/                   # Version 1 API
│   │   │   ├── interviews.py
│   │   │   ├── candidates.py
│   │   │   ├── scoring.py
│   │   │   └── bot.py
│   │   └── main.py
│   │
│   ├── services/                 # Business logic
│   │   ├── interview_service.py
│   │   ├── candidate_service.py
│   │   ├── bot_manager.py
│   │   └── notification_service.py
│   │
│   ├── engines/                  # AI/ML engines
│   │   ├── question_generator.py
│   │   ├── scoring_engine.py
│   │   ├── resume_parser.py
│   │   └── job_matcher.py
│   │
│   ├── models/                   # Data models
│   │   ├── interview.py
│   │   ├── candidate.py
│   │   └── score.py
│   │
│   ├── database/                 # Database layer
│   │   ├── mongodb.py
│   │   └── redis.py
│   │
│   ├── workers/                  # Background workers
│   │   ├── ai_bot_worker.py
│   │   └── notification_worker.py
│   │
│   └── requirements.txt
│
├── frontend/                     # Frontend app
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── README.md
│
├── ai-bot/                       # AI Bot (Pipecat)
│   ├── bot.py
│   ├── processors/
│   └── requirements.txt
│
├── scripts/                      # Utility scripts
│   ├── deploy.sh
│   ├── seed_db.py
│   └── test_integration.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 5. Migration Roadmap

### Phase 1: Foundation & Critical Fixes (Weeks 1-3)
**Goal:** Fix critical issues, establish patterns

#### Sprint 1.1: Real Scoring Engine ✅
- **Objective:** Replace mock scores with real LLM-based evaluation
- **Tasks:**
  - [ ] Create `engines/scoring_engine.py`
  - [ ] Implement LLM prompt for scoring
  - [ ] Add scoring criteria configuration
  - [ ] Test with real interview transcripts
  - [ ] Update AI bot to use real scoring
- **Success Criteria:** 
  - Real scores appear in dashboard
  - Scores match evaluation criteria
- **Estimated Effort:** 3-5 days
- **Status:** ⏳ Pending

---

#### Sprint 1.2: Job Queue System ✅
- **Objective:** Automate bot process management
- **Tasks:**
  - [ ] Choose queue system (Redis + RQ or Celery)
  - [ ] Set up Redis instance
  - [ ] Create `workers/ai_bot_worker.py`
  - [ ] Create `services/bot_manager.py`
  - [ ] Update interview scheduling to enqueue jobs
  - [ ] Add job monitoring dashboard
- **Success Criteria:**
  - Bots start automatically when interview scheduled
  - Multiple concurrent interviews work
  - Failed jobs auto-retry
- **Estimated Effort:** 5-7 days
- **Status:** ⏳ Pending

---

#### Sprint 1.3: Database Dependency Injection ✅
- **Objective:** Fix database access patterns
- **Tasks:**
  - [ ] Refactor to use FastAPI Depends()
  - [ ] Remove HTTP workarounds in dashboard
  - [ ] Add proper connection pooling
  - [ ] Add database health checks
- **Success Criteria:**
  - Direct database access in all routes
  - No internal HTTP calls
- **Estimated Effort:** 2-3 days
- **Status:** ⏳ Pending

---

#### Sprint 1.4: API Versioning ✅
- **Objective:** Add version prefix to all APIs
- **Tasks:**
  - [ ] Move routes to `/api/v1/...`
  - [ ] Update AI bot to use versioned endpoints
  - [ ] Add API version middleware
  - [ ] Update documentation
- **Success Criteria:**
  - All APIs under `/api/v1/`
  - Old endpoints redirect to v1
- **Estimated Effort:** 1-2 days
- **Status:** ⏳ Pending

---

### Phase 2: Architecture Improvements (Weeks 4-8)
**Goal:** Separate concerns, improve maintainability

#### Sprint 2.1: Frontend Separation ✅
- **Objective:** Create standalone React/Next.js frontend
- **Tasks:**
  - [ ] Set up Next.js project
  - [ ] Create API client
  - [ ] Port dashboard UI to React
  - [ ] Port interview list UI
  - [ ] Port interview detail UI
  - [ ] Port scheduling UI
  - [ ] Add real-time updates (WebSocket)
  - [ ] Deploy separately from backend
- **Success Criteria:**
  - Frontend runs independently
  - Backend becomes pure API
- **Estimated Effort:** 10-15 days
- **Status:** ⏳ Pending

---

#### Sprint 2.2: Engine Layer Implementation ✅
- **Objective:** Create reusable AI/ML engines
- **Tasks:**
  - [ ] Create `engines/question_generator.py`
  - [ ] Create `engines/resume_parser.py`
  - [ ] Create `engines/job_matcher.py`
  - [ ] Add tests for each engine
  - [ ] Integrate with services
- **Success Criteria:**
  - Engines work independently
  - Can be reused across services
- **Estimated Effort:** 7-10 days
- **Status:** ⏳ Pending

---

#### Sprint 2.3: Service Layer Refactoring ✅
- **Objective:** Create proper service layer
- **Tasks:**
  - [ ] Create `services/interview_service.py`
  - [ ] Create `services/candidate_service.py`
  - [ ] Create `services/notification_service.py`
  - [ ] Move business logic from routes to services
  - [ ] Add service tests
- **Success Criteria:**
  - Routes are thin (just HTTP handling)
  - Business logic in services
- **Estimated Effort:** 5-7 days
- **Status:** ⏳ Pending

---

#### Sprint 2.4: Authentication & Authorization ✅
- **Objective:** Add user management
- **Tasks:**
  - [ ] Choose auth system (JWT, OAuth2)
  - [ ] Add user model & database tables
  - [ ] Implement login/logout
  - [ ] Add role-based access control
  - [ ] Protect API endpoints
  - [ ] Add auth to frontend
- **Success Criteria:**
  - Users can login/logout
  - Protected routes require auth
- **Estimated Effort:** 7-10 days
- **Status:** ⏳ Pending

---

### Phase 3: Production Readiness (Weeks 9-12)
**Goal:** Scale, monitor, deploy

#### Sprint 3.1: Caching Layer ✅
- **Objective:** Add Redis for caching
- **Tasks:**
  - [ ] Set up Redis
  - [ ] Add caching to frequently accessed data
  - [ ] Add cache invalidation logic
  - [ ] Monitor cache hit rates
- **Estimated Effort:** 3-5 days
- **Status:** ⏳ Pending

---

#### Sprint 3.2: Monitoring & Logging ✅
- **Objective:** Add observability
- **Tasks:**
  - [ ] Set up structured logging
  - [ ] Add application metrics
  - [ ] Set up dashboards (Grafana/Datadog)
  - [ ] Add error tracking (Sentry)
  - [ ] Add uptime monitoring
- **Estimated Effort:** 5-7 days
- **Status:** ⏳ Pending

---

#### Sprint 3.3: Infrastructure & Deployment ✅
- **Objective:** Production deployment
- **Tasks:**
  - [ ] Dockerize all services
  - [ ] Create docker-compose for local dev
  - [ ] Set up CI/CD pipeline
  - [ ] Deploy to cloud (AWS/GCP/Azure)
  - [ ] Set up auto-scaling
  - [ ] Configure load balancer
  - [ ] Set up backups
- **Estimated Effort:** 7-10 days
- **Status:** ⏳ Pending

---

#### Sprint 3.4: Testing & Documentation ✅
- **Objective:** Quality assurance
- **Tasks:**
  - [ ] Write unit tests (80% coverage)
  - [ ] Write integration tests
  - [ ] Write E2E tests
  - [ ] Complete API documentation
  - [ ] Create deployment guide
  - [ ] Create developer onboarding guide
- **Estimated Effort:** 7-10 days
- **Status:** ⏳ Pending

---

## 6. Technical Decisions Log

### Decision #1: Use Redis for Job Queue
**Date:** TBD  
**Decision:** Use Redis + RQ (or Celery) for job queue  
**Rationale:**
- ✅ Simple to set up
- ✅ Can also use for caching
- ✅ Good Python support
- ✅ Lightweight

**Alternatives Considered:**
- RabbitMQ (too heavy for MVP)
- AWS SQS (vendor lock-in)
- Database-backed queue (not scalable)

**Status:** ✅ Approved

---

### Decision #2: Next.js for Frontend
**Date:** TBD  
**Decision:** Use Next.js for frontend  
**Rationale:**
- ✅ Server-side rendering
- ✅ Great developer experience
- ✅ Built-in routing
- ✅ Easy deployment (Vercel)

**Alternatives Considered:**
- Plain React (need to add routing, SSR)
- Vue.js (less ecosystem support)
- Keep Jinja2 (not scalable)

**Status:** ⏳ Pending Discussion

---

### Decision #3: OpenAI for LLM
**Date:** October 6, 2025  
**Decision:** Continue using OpenAI GPT-4 for scoring  
**Rationale:**
- ✅ Best quality
- ✅ Already integrated
- ✅ Good API

**Alternatives Considered:**
- Gemini (cheaper but less accurate)
- Claude (no streaming for long transcripts)
- Open-source LLMs (need hosting)

**Status:** ✅ Approved

---

### Decision #4: MongoDB vs PostgreSQL
**Date:** October 6, 2025  
**Decision:** Keep MongoDB  
**Rationale:**
- ✅ Flexible schema (interview data varies)
- ✅ Already implemented
- ✅ Good for document storage

**Future Consideration:**
- May add PostgreSQL for user/auth data (structured)
- Hybrid approach: MongoDB for interviews, PostgreSQL for users

**Status:** ✅ Approved (with future hybrid option)

---

## 7. Development Guidelines

### 7.1 Code Organization Principles

1. **Separation of Concerns**
   - Routes handle HTTP only
   - Services handle business logic
   - Engines handle AI/ML operations
   - Database layer handles data access

2. **Dependency Injection**
   - Use FastAPI's `Depends()` for all dependencies
   - No global variables
   - Make testing easier

3. **API Versioning**
   - All APIs under `/api/v1/`, `/api/v2/`, etc.
   - Never break backward compatibility within a version

4. **Error Handling**
   - Use proper HTTP status codes
   - Return structured error responses
   - Log all errors with context

### 7.2 Naming Conventions

**Files:**
```python
# Services
services/interview_service.py
services/candidate_service.py

# Engines
engines/scoring_engine.py
engines/question_generator.py

# API Routes
api/v1/interviews.py
api/v1/candidates.py
```

**Classes:**
```python
class InterviewService:
    pass

class ScoringEngine:
    pass

class CandidateRepository:
    pass
```

**Functions:**
```python
# Services - business operations
async def create_interview(...)
async def schedule_interview(...)

# Engines - AI/ML operations
async def generate_questions(...)
async def score_interview(...)

# Repositories - data operations
async def save_interview(...)
async def get_interview_by_id(...)
```

### 7.3 Testing Strategy

**Unit Tests:**
- Test individual functions/classes
- Mock all external dependencies
- Target: 80% coverage

**Integration Tests:**
- Test service interactions
- Use test database
- Test API endpoints

**E2E Tests:**
- Test complete user flows
- Use test environment
- Run before deployment

### 7.4 Git Workflow

**Branch Strategy:**
```
main (production)
├── develop (staging)
    ├── feature/sprint-1.1-scoring-engine
    ├── feature/sprint-1.2-job-queue
    └── hotfix/bug-123
```

**Commit Messages:**
```
[Sprint 1.1] Implement LLM-based scoring engine
[Sprint 1.2] Add Redis job queue for bot management
[Hotfix] Fix dashboard date sorting issue
```

### 7.5 Documentation Requirements

**Every Sprint Must Deliver:**
1. ✅ Updated code with comments
2. ✅ API documentation (if API changed)
3. ✅ Updated ARCHITECTURE.md (if structure changed)
4. ✅ Updated README.md
5. ✅ Migration notes (if breaking changes)

---

## 8. Appendices

### Appendix A: Current Issues Tracker

| ID | Issue | Priority | Phase | Status |
|----|-------|----------|-------|--------|
| #1 | Tight coupling | P0 | 1 | ⏳ Pending |
| #2 | Manual bot start | P0 | 1 | ⏳ Pending |
| #3 | Mock scoring | P0 | 1 | ⏳ Pending |
| #4 | Monolithic server | P1 | 2 | ⏳ Pending |
| #5 | No engine layer | P1 | 2 | ⏳ Pending |
| #6 | DB access pattern | P1 | 1 | ⏳ Pending |
| #7 | No API versioning | P2 | 1 | ⏳ Pending |
| #8 | Missing services | P2 | 3 | ⏳ Pending |

### Appendix B: Useful Resources

**FastAPI Best Practices:**
- https://fastapi.tiangolo.com/tutorial/bigger-applications/
- https://github.com/zhanymkanov/fastapi-best-practices

**System Design:**
- https://github.com/donnemartin/system-design-primer

**MongoDB Best Practices:**
- https://www.mongodb.com/docs/manual/administration/production-notes/

### Appendix C: Contact & Ownership

**Document Owner:** [Your Name]  
**Last Review Date:** October 6, 2025  
**Next Review Date:** End of Phase 1  

---

**END OF DOCUMENT**

