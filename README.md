# 🤖 AI Interviewer System

**Automated AI-powered technical interview platform**

[![Status](https://img.shields.io/badge/status-active%20development-green)]()
[![Version](https://img.shields.io/badge/version-0.1.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## 📖 Overview

AI Interviewer is an intelligent system that conducts voice-based technical interviews, evaluates candidates in real-time, and provides detailed feedback through a comprehensive web dashboard.

### Key Features

- 🎤 **Voice-Based Interviews** - Natural conversation using AI
- 📊 **Real-Time Evaluation** - LLM-powered scoring (coming soon)
- 📈 **Dashboard Analytics** - Track interview metrics
- 🤖 **Automated Process** - From scheduling to results
- 🎯 **Custom Questions** - Tailored to job requirements
- 📝 **Detailed Feedback** - Comprehensive candidate assessment

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB 6.0+
- OpenAI API Key
- Daily.co Account (for video/audio)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd ai-interviewer

# Install dependencies
cd web_server
pip install -r requirements.txt

cd ../server
pip install -r requirements.txt

# Set up environment
cp web_server/.env.example web_server/.env
cp server/.env.example server/.env

# Edit .env files with your API keys
nano web_server/.env
nano server/.env

# Start MongoDB
mongod --dbpath /path/to/data

# Start web server
cd web_server
python main.py
```

### Access

- **Dashboard:** http://localhost:8009/dashboard
- **API Docs:** http://localhost:8009/docs
- **Health Check:** http://localhost:8009/health

---

## 📚 Documentation

> **👉 Start here if you're new to the project!**

| Document | Description | Audience |
|----------|-------------|----------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Complete system architecture, issues, and solutions | Developers, Architects |
| **[ROADMAP.md](./ROADMAP.md)** | Development roadmap and sprint plans | Team, Managers |
| **[DEVELOPMENT.md](./DEVELOPMENT.md)** | Day-to-day development guide | Developers |
| **[API.md](./API.md)** | API documentation (coming soon) | Frontend, Integrations |

### Quick Links

- 🏗️ **Understanding the System?** → Read [ARCHITECTURE.md](./ARCHITECTURE.md)
- 📅 **What's Next?** → Check [ROADMAP.md](./ROADMAP.md)
- 💻 **Starting Development?** → Follow [DEVELOPMENT.md](./DEVELOPMENT.md)
- 🐛 **Found a Bug?** → See [DEVELOPMENT.md#reporting-bugs](./DEVELOPMENT.md#reporting-bugs)

---

## 🎯 Current Status

**Version:** 0.1.0 (MVP)  
**Status:** Active Development  
**Architecture Grade:** 6.5/10

### ✅ What's Working
- Web dashboard with interview management
- AI-powered voice interviews via Daily.co
- MongoDB data persistence
- Interview result visualization

### ⚠️ Known Issues
- Manual bot process management (requires manual start)
- Mock scoring system (not real LLM-based yet)
- Monolithic architecture (needs refactoring)

**See [ARCHITECTURE.md](./ARCHITECTURE.md#identified-issues) for full list**

---

## 🏗️ Architecture

### High-Level Overview

```
┌─────────────┐
│  Dashboard  │ ← User schedules interview
└──────┬──────┘
       │
┌──────▼──────┐
│ Web Server  │ ← FastAPI (Port 8009)
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌────────┐ ┌─────────┐
│MongoDB │ │ AI Bot  │ ← Pipecat
└────────┘ └────┬────┘
                │
           ┌────▼────┐
           │Daily.co │ ← WebRTC
           └─────────┘
```

**See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture**

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI (async Python web framework)
- **Database:** MongoDB (NoSQL for flexible schemas)
- **AI Framework:** Pipecat (voice AI pipelines)

### AI & ML
- **LLM:** OpenAI GPT-4 (conversation & scoring)
- **STT:** Deepgram (speech-to-text)
- **TTS:** Cartesia (text-to-speech)

### Infrastructure
- **Video/Audio:** Daily.co (WebRTC)
- **Deployment:** Docker (coming soon)

---

## 📦 Project Structure

```
ai-interviewer/
├── docs/                       # 📚 Documentation
│   ├── ARCHITECTURE.md         # System design & issues
│   ├── ROADMAP.md              # Development plan
│   └── DEVELOPMENT.md          # Dev guide
│
├── web_server/                 # 🌐 Web Server (FastAPI)
│   ├── main.py                 # Entry point
│   ├── routers/                # HTTP routes
│   ├── services/               # Business logic
│   ├── templates/              # HTML (Jinja2)
│   └── static/                 # CSS, JS
│
├── server/                     # 🤖 AI Bot (Pipecat)
│   ├── ai-interviewer.py       # Main bot
│   └── requirements.txt
│
└── client/                     # 📱 Client apps
    ├── javascript/
    ├── react/
    └── react-native/
```

---

## 🎬 Usage

### 1. Schedule Interview

```bash
# Via dashboard
http://localhost:8009/dashboard/schedule

# Or via API
curl -X POST http://localhost:8009/api/interviews \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "John Doe",
    "position": "Senior Developer",
    "scheduled_date": "2025-10-10"
  }'
```

### 2. Start AI Bot

```bash
cd server
INTERVIEW_ID=interview_xxx \
WEB_SERVER_URL=http://localhost:8009 \
python ai-interviewer.py --transport daily
```

### 3. Candidate Joins

- Candidate opens: `https://hi2inspire.daily.co/hi2inspire`
- AI greets and starts interview
- Conversation happens naturally

### 4. View Results

- Dashboard: `http://localhost:8009/dashboard/interviews`
- Results appear automatically after interview ends

---

## 🧪 Testing

### Manual Testing

```bash
# Test web server
curl http://localhost:8009/health

# Test database connection
curl http://localhost:8009/debug/interviews

# Test complete flow
1. Schedule interview via dashboard
2. Start bot with interview ID
3. Join as candidate
4. Complete interview
5. Check results
```

### Automated Testing (Coming Soon)

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/
```

---

## 📅 Development Roadmap

### Phase 1: Foundation (Weeks 1-3) ⏳
- [ ] Real LLM-based scoring engine
- [ ] Automated bot job queue
- [ ] Database dependency injection
- [ ] API versioning

### Phase 2: Architecture (Weeks 4-8) ⏳
- [ ] Separate React frontend
- [ ] Proper engine layer
- [ ] Service layer refactoring
- [ ] Authentication system

### Phase 3: Production (Weeks 9-12) ⏳
- [ ] Caching with Redis
- [ ] Monitoring & logging
- [ ] Infrastructure & deployment
- [ ] Comprehensive testing

**See [ROADMAP.md](./ROADMAP.md) for detailed timeline**

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Read Documentation**
   - Start with [ARCHITECTURE.md](./ARCHITECTURE.md)
   - Check current sprint in [ROADMAP.md](./ROADMAP.md)

2. **Set Up Development**
   - Follow [DEVELOPMENT.md](./DEVELOPMENT.md)

3. **Create Feature Branch**
   ```bash
   git checkout -b feature/sprint-X.X-description
   ```

4. **Make Changes**
   - Follow code style guide in [DEVELOPMENT.md](./DEVELOPMENT.md#code-style-guide)
   - Add tests
   - Update documentation

5. **Submit PR**
   - Create PR to `develop` branch
   - Add clear description
   - Request review

**See [DEVELOPMENT.md#contributing](./DEVELOPMENT.md#contributing) for details**

---

## 🐛 Known Issues

1. **Manual Bot Start** - Bots must be started manually for each interview
2. **Mock Scoring** - Scoring uses hardcoded values, not real LLM
3. **Monolithic Server** - API and UI are tightly coupled

**See [ARCHITECTURE.md#identified-issues](./ARCHITECTURE.md#identified-issues) for full list and solutions**

---

## 📊 Metrics

- **Interviews Conducted:** 6+ (as of Oct 6, 2025)
- **Average Score:** 54.6/100
- **System Uptime:** 99%+
- **Test Coverage:** 0% (coming in Phase 3)

---

## 🔒 Security

- API keys stored in `.env` files (never commit!)
- MongoDB access controlled
- Interview data encrypted in transit
- No PII stored without consent

**See [ARCHITECTURE.md#security](./ARCHITECTURE.md) for details**

---

## 📝 License

MIT License - See [LICENSE](./LICENSE) file

---

## 📞 Support

### Questions?
1. Check [DEVELOPMENT.md](./DEVELOPMENT.md#getting-help)
2. Read [ARCHITECTURE.md](./ARCHITECTURE.md)
3. Search existing issues
4. Create new issue with details

### Bug Reports
See [DEVELOPMENT.md#reporting-bugs](./DEVELOPMENT.md#reporting-bugs)

---

## 🙏 Acknowledgments

- **Pipecat** - Voice AI framework
- **FastAPI** - Web framework
- **OpenAI** - LLM capabilities
- **Daily.co** - WebRTC infrastructure
- **MongoDB** - Database

---

## 🎯 Quick Commands

```bash
# Start development
git checkout develop
git pull
git checkout -b feature/my-feature

# Run locally
cd web_server && python main.py

# Test
curl http://localhost:8009/health

# Deploy changes
git add .
git commit -m "[Sprint X.X] Description"
git push origin feature/my-feature
```

---

**Built with ❤️ for better hiring**

**Status:** 🟢 Active Development  
**Last Updated:** October 6, 2025  
**Version:** 0.1.0

