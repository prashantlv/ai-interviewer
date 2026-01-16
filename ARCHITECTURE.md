# AI Interviewer - Technical Architecture

**Version:** 2.0  
**Last Updated:** January 16, 2026  
**Status:** Production

---

## System Overview

AI Interviewer is an automated interview platform that conducts voice-based interviews using AI avatars, evaluates candidates with LLM-based scoring, and provides detailed feedback through a web dashboard.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Web Browser (Recruiter)                         │
│  • Dashboard (Jinja2 SSR)                                   │
│  • Interview scheduling, results, analytics                 │
│  • Replica & voice management                               │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────────┐
│           Web Server (FastAPI) - Port 8009                   │
│  • web_server/main.py                                        │
│  • Routers: dashboard, interviews, tavus, voices, scoring   │
│  • Services: database, daily, tavus, voice_cloning          │
└────────────────────┬────────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┬─────────────┐
       ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌─────────┐  ┌──────────────┐
│  MongoDB  │  │   Redis   │  │  Daily  │  │  RQ Worker   │
│ Database  │  │  (Queue)  │  │  .co    │  │  (Bot Jobs)  │
└───────────┘  └───────────┘  └────┬────┘  └──────┬───────┘
                                   │              │
                                   │    ┌─────────▼─────────┐
                                   │    │  AI Bot Process   │
                                   │    │  (Pipecat)        │
                                   │    │  server/ai-inter- │
                                   │    │  viewer.py        │
                                   │    └─────────┬─────────┘
                                   │              │
                     ┌─────────────┴──────────────┴───────┐
                     ▼             ▼             ▼        ▼
              ┌───────────┐ ┌───────────┐ ┌─────────┐ ┌───────┐
              │  Tavus    │ │ Cartesia  │ │ OpenAI  │ │Deepgram│
              │ (Avatar)  │ │  (TTS)    │ │ (LLM)   │ │ (STT) │
              └───────────┘ └───────────┘ └─────────┘ └───────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend API | FastAPI | Web server & REST API |
| Database | MongoDB | Data persistence |
| Job Queue | Redis + RQ | Bot process management |
| AI Framework | Pipecat | Real-time voice AI pipeline |
| LLM | OpenAI GPT-4o-mini | Conversation & scoring |
| STT | Deepgram | Speech-to-text |
| TTS | Cartesia | Text-to-speech with voice cloning |
| Video Avatar | Tavus | AI replica with lip-sync |
| WebRTC | Daily.co | Video/audio rooms & recording |
| Templates | Jinja2 | Server-side HTML rendering |
| Containers | Docker | Deployment |

---

## Directory Structure

```
ai-interviewer/
├── web_server/                    # FastAPI Web Server
│   ├── main.py                    # Main app, API endpoints
│   ├── dependencies.py            # DI for services
│   ├── routers/
│   │   ├── dashboard.py           # Dashboard UI routes
│   │   ├── interviews.py          # Interview API
│   │   ├── tavus.py               # Replica management
│   │   ├── voices.py              # Voice management
│   │   ├── scoring_settings.py    # Scoring config
│   │   ├── proctoring.py          # Proctoring API
│   │   └── feedback.py            # Candidate feedback
│   ├── services/
│   │   ├── database.py            # MongoDB operations
│   │   ├── daily_service.py       # Daily.co API
│   │   ├── tavus_service.py       # Tavus API
│   │   ├── voice_cloning_service.py # Cartesia voice cloning
│   │   ├── question_engine.py     # LLM question generation
│   │   └── scoring_config_service.py
│   ├── workers/
│   │   └── ai_bot_worker.py       # RQ worker for bot jobs
│   ├── templates/                 # Jinja2 HTML templates
│   └── requirements.txt
│
├── server/                        # AI Bot (Pipecat)
│   ├── ai-interviewer.py          # Main bot script
│   ├── interview_manager.py       # Interview flow logic
│   ├── scoring_engine.py          # LLM-based scoring
│   ├── scoring_config.py          # Scoring criteria
│   └── services/
│       └── cartesia_tts.py        # Cartesia TTS service
│
├── docker-compose.yml             # Container orchestration
├── Dockerfile.web                 # Web server image
├── Dockerfile.worker              # RQ worker image
└── README.md
```

---

## Key Features

### Implemented ✅

1. **Interview Scheduling**
   - Create interviews with job description & resume
   - Auto-generate questions using GPT-4
   - Select AI avatar replica per interview

2. **AI Interview Bot**
   - Real-time voice conversation via Pipecat
   - Tavus avatar with lip-sync video
   - Cartesia TTS with voice cloning
   - Automatic transcript capture

3. **Replica & Voice Management**
   - Browse Tavus stock/personal replicas
   - Clone voice from replica video (via Cartesia)
   - Set default replica for all interviews
   - Select specific replica per interview

4. **LLM-Based Scoring**
   - Configurable scoring criteria (1-5 levels)
   - Real transcript analysis with GPT-4
   - Technical, communication, problem-solving scores
   - Detailed feedback generation

5. **Proctoring**
   - Fullscreen enforcement
   - Tab switch detection
   - Window blur monitoring
   - Violation timeline

6. **Recording & Playback**
   - Daily.co cloud recording
   - Auto-fetch recording links
   - Playback in dashboard

7. **Job Queue System**
   - Redis + RQ for bot management
   - Auto-start bot on interview schedule
   - Job monitoring

---

## Data Flow

### Interview Flow
```
1. Recruiter schedules interview (web dashboard)
2. Web server saves to MongoDB, creates Daily.co room
3. RQ worker starts AI bot process
4. Candidate joins Daily.co room
5. Bot conducts interview (Pipecat pipeline):
   - Deepgram STT → OpenAI LLM → Cartesia TTS → Tavus Video
6. Bot scores interview with LLM
7. Results saved to MongoDB
8. Recruiter views results in dashboard
```

### Replica-Voice Mapping
```
1. Admin sets default replica (dropdown)
2. If no voice mapped → auto-clone from replica video
3. Cloned voice saved to MongoDB + Cartesia
4. Bot uses mapped voice for TTS
```

---

## API Endpoints

### Bot API (`/api/v1/bot/`)
- `GET /interview-config/{id}` - Get interview config
- `GET /replica-config` - Get replica-voice mapping
- `POST /interview-result` - Save results

### Tavus API (`/api/v1/tavus/`)
- `GET /replicas` - List replicas
- `POST /replica-mappings` - Create voice mapping
- `PATCH /replica-mappings/{id}/set-default` - Set default
- `POST /replica-mappings/{id}/clone-voice` - Clone voice

### Dashboard (`/dashboard/`)
- `/` - Main dashboard
- `/interviews` - Interview list
- `/interview/{id}` - Results
- `/schedule` - Schedule new
- `/replicas` - Replica management

---

## Deployment

### Production (EC2)
```bash
docker-compose up -d
# Services: web-server, rq-worker, redis, mongodb
```

### Environment Variables
See `web_server/env.example` and `server/env.example`

Key variables:
- `MONGODB_URL`, `REDIS_URL`
- `DAILY_API_KEY`, `TAVUS_API_KEY`
- `CARTESIA_API_KEY`, `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`

---

## Future Enhancements

- [ ] React frontend (replace Jinja2)
- [ ] Multi-tenant support
- [ ] Authentication & authorization
- [ ] Analytics dashboard
- [ ] Email notifications
- [ ] Webhook integrations
