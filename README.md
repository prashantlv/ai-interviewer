# AI Interviewer

AI-powered interview platform with real-time video/audio communication using Daily.co, intelligent conversation with OpenAI, and Cartesia TTS.

## 🚀 Quick Start (Pure Pip - No Conda!)

### **New Machine Setup:**

```bash
# 1. Clone the repository
git clone <repository-url>
cd ai-interviewer

# 2. Setup Python virtual environment
./setup-venv.sh

# 3. Configure environment variables
# Edit server/.env and web_server/.env with your API keys

# 4. Start the application
./start.sh
```

### **Daily Development:**

```bash
# Just run this:
./start.sh

# Access dashboard at:
# http://localhost:8009/dashboard
```

---

## 📦 Requirements

- **Python 3.10+** (3.12 recommended)
- **Docker** (for Redis)
- **API Keys:**
  - OpenAI API key
  - Daily.co API key
  - Cartesia API key
  - MongoDB Atlas connection string
  - Hire2Inspire credentials (optional)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Interviewer Stack                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    Redis     │◄─────┤  RQ Worker   │◄─────┤ Web Server   │
│  (Docker)    │      │  (Python)    │      │   (FastAPI)  │
│  Port: 6379  │      │              │      │  Port: 8009  │
└──────────────┘      └──────────────┘      └──────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  AI Bot      │
                      │  (Pipecat)   │
                      │  + Cartesia  │
                      └──────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  Daily.co    │
                      │  (Video)     │
                      └──────────────┘
```

### **Key Components:**

1. **Web Server (FastAPI)**
   - Interview scheduling and management
   - Dashboard UI
   - API endpoints
   - Job queue management

2. **RQ Worker**
   - Processes interview jobs
   - Spawns AI bot processes
   - Handles job lifecycle

3. **AI Bot (Pipecat)**
   - Real-time conversation
   - Speech-to-Text (OpenAI Whisper)
   - LLM (OpenAI GPT-4)
   - Text-to-Speech (Cartesia)
   - Video (Tavus/Simli)

4. **Redis**
   - Job queue
   - Task scheduling
   - State management

---

## 📁 Project Structure

```
ai-interviewer/
├── server/                     # AI Bot (Pipecat)
│   ├── ai-interviewer.py      # Main bot script
│   ├── services/              # TTS services
│   ├── requirements.txt       # Bot dependencies
│   └── .env                   # Bot configuration
│
├── web_server/                # FastAPI Web Server
│   ├── main.py               # FastAPI application
│   ├── routers/              # API endpoints
│   ├── services/             # Business logic
│   ├── templates/            # Jinja2 templates
│   ├── workers/              # RQ worker
│   ├── requirements.txt      # Web dependencies
│   └── .env                  # Web configuration
│
├── venv/                     # Python virtual environment
├── start.sh                  # Start all services
├── setup-venv.sh            # Setup virtual environment
├── test-docker.sh           # Test Docker locally
└── deploy.sh                # Deploy to EC2
```

---

## 🔧 Configuration

### **Environment Variables:**

#### **server/.env** (AI Bot):
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# TTS Service (cartesia, elevenlabs, openai)
TTS_SERVICE=cartesia
CARTESIA_API_KEY=...
CARTESIA_VOICE_ID=...

# Daily.co
DAILY_API_KEY=...

# Video Service (tavus, simli, none)
VIDEO_SERVICE=none  # or tavus, simli
TAVUS_API_KEY=...
TAVUS_REPLICA_ID=...

# Web Server URL
WEB_SERVER_URL=http://localhost:8009
```

#### **web_server/.env** (Web Server):
```bash
# MongoDB
MONGODB_URL=mongodb+srv://...
MONGODB_DB_NAME=ai_interviewer

# Redis
REDIS_URL=redis://localhost:6379
# or
REDIS_HOST=localhost
REDIS_PORT=6379

# Daily.co
DAILY_API_KEY=...

# Hire2Inspire (Optional)
H2I_BASE_URL=https://api.hire2inspire.com
H2I_EMAIL=...
H2I_PASSWORD=...
```

---

## 🎯 Features

### **Interview Management**
- ✅ Schedule interviews
- ✅ Real-time video/audio calls
- ✅ AI-powered conversation
- ✅ Automatic transcription
- ✅ Interview reports & analytics

### **AI Capabilities**
- ✅ Natural conversation flow
- ✅ Context-aware questions
- ✅ Multiple TTS providers (Cartesia, ElevenLabs, OpenAI)
- ✅ Video avatars (Tavus, Simli)
- ✅ Custom voice cloning

### **Integrations**
- ✅ Daily.co for video calls
- ✅ OpenAI for LLM & STT
- ✅ Cartesia for TTS
- ✅ MongoDB for data storage
- ✅ Hire2Inspire for candidate data

---

## 🛠️ Development

### **Local Development:**

```bash
# Start all services
./start.sh

# View logs
tail -f /tmp/web_server.log
tail -f /tmp/rq_worker.log

# Stop services
Ctrl+C
```

### **Manual Startup (for debugging):**

**Terminal 1 - Redis:**
```bash
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest
```

**Terminal 2 - RQ Worker:**
```bash
source venv/bin/activate
cd web_server
rq worker ai_bots --with-scheduler
```

**Terminal 3 - Web Server:**
```bash
source venv/bin/activate
cd web_server
python main.py
```

### **Testing:**

```bash
# Test Docker images
./test-docker.sh

# Access dashboard
open http://localhost:8009/dashboard

# Check health
curl http://localhost:8009/health
```

---

## 🐳 Docker Deployment

### **Build Images:**

```bash
# Build web server
docker build -f Dockerfile.web -t ai-interviewer-web:latest .

# Build worker
docker build -f Dockerfile.worker -t ai-interviewer-worker:latest .
```

### **Run Containers:**

```bash
# Redis
docker run -d --name redis-ai-interviewer -p 6379:6379 redis:latest

# Web server
docker run -d --name ai-interviewer-web \
  --network host \
  --env-file web_server/.env \
  ai-interviewer-web:latest

# Worker
docker run -d --name ai-interviewer-worker \
  --network host \
  --env-file server/.env \
  --env-file web_server/.env \
  ai-interviewer-worker:latest
```

---

## 🚀 EC2 Deployment

### **On EC2 Instance:**

```bash
# 1. Clone repository
git clone <repository-url>
cd ai-interviewer

# 2. Configure environment
cp server/env.example server/.env
cp web_server/env.example web_server/.env
# Edit .env files with production credentials

# 3. Deploy
./deploy.sh
```

### **HTTPS Setup:**

The application uses Nginx as a reverse proxy with Let's Encrypt SSL certificates.

**Access:**
- Dashboard: https://api.human2intelligence.com/dashboard
- API Docs: https://api.human2intelligence.com/docs

---

## 📚 Documentation

- **`LOCAL_DEVELOPMENT.md`** - Local development guide
- **`ENVIRONMENT_MANAGEMENT_GUIDE.md`** - Package management
- **`PACKAGE_COMPARISON.md`** - Local vs Docker comparison
- **`DEPLOYMENT_GUIDE.md`** - EC2 deployment details
- **`CARTESIA_DEPLOYMENT.md`** - Cartesia TTS setup

---

## 🐛 Troubleshooting

### **Issue: Virtual environment not found**
```bash
./setup-venv.sh
```

### **Issue: Port 8009 already in use**
```bash
lsof -ti:8009 | xargs kill -9
./start.sh
```

### **Issue: Redis connection failed**
```bash
docker restart redis-ai-interviewer
```

### **Issue: AI bot not joining**
Check logs:
```bash
tail -f /tmp/rq_worker.log
```

Common causes:
- Missing API keys in `.env`
- Tavus payment required (set `VIDEO_SERVICE=none`)
- Invalid Daily.co room URL

### **Issue: Import errors**
```bash
source venv/bin/activate
pip install --upgrade -r server/requirements.txt -r web_server/requirements.txt
```

---

## 🔄 Updating Dependencies

```bash
# Activate venv
source venv/bin/activate

# Upgrade packages
pip install --upgrade pipecat-ai openai cartesia fastapi

# Update lock file
pip freeze > requirements-all.lock

# Commit changes
git add requirements-all.lock
git commit -m "Update dependencies"
```

---

## 📊 Monitoring

### **Health Checks:**
- Web Server: http://localhost:8009/health
- System Health: http://localhost:8009/dashboard/system-health

### **Logs:**
- Web Server: `/tmp/web_server.log`
- RQ Worker: `/tmp/rq_worker.log`

### **Redis:**
```bash
redis-cli ping
redis-cli INFO
```

### **RQ Worker:**
```bash
source venv/bin/activate
cd web_server
rq info
```

---

## 🎓 Best Practices

1. ✅ Always use virtual environment (`source venv/bin/activate`)
2. ✅ Never commit `.env` files
3. ✅ Use `requirements-all.lock` for exact versions
4. ✅ Test in Docker before deploying
5. ✅ Monitor logs regularly
6. ✅ Keep dependencies updated
7. ✅ Use environment variables for configuration

---



