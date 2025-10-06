# 🚀 Getting Started - AI Interviewer

**Quick start guide for solo development**

---

## 📋 Prerequisites

Before you begin, make sure you have:

- ✅ Python 3.11 or higher
- ✅ MongoDB 6.0+ installed and running
- ✅ OpenAI API key
- ✅ Daily.co account (for WebRTC)
- ✅ Deepgram API key (for STT)
- ✅ Cartesia API key (for TTS)

---

## ⚡ Quick Setup (5 Minutes)

### 1. Clone and Navigate

```bash
cd /home/prashant/Playground/personal/consult/ai-interviewer
```

### 2. Install Dependencies

```bash
# Web server
cd web_server
pip install -r requirements.txt

# AI bot
cd ../server
pip install -r requirements.txt
cd ..
```

### 3. Set Up Environment Variables

```bash
# Web server
cd web_server
cp .env.example .env
nano .env  # Add your API keys

# AI bot
cd ../server
cp .env.example .env
nano .env  # Add your API keys
```

**Required values:**
- `OPENAI_API_KEY` (both files)
- `MONGODB_URI` (web_server/.env)
- `DAILY_API_KEY` (server/.env)
- `DEEPGRAM_API_KEY` (server/.env)
- `CARTESIA_API_KEY` (server/.env)

### 4. Start MongoDB

```bash
# Check if running
mongosh --eval "db.adminCommand('ping')"

# If not running, start it
sudo systemctl start mongod
```

### 5. Start the System

**Option A: Using the helper script (Recommended)**
```bash
./start.sh
# Choose option 1 to start web server
```

**Option B: Manual start**
```bash
# Terminal 1: Web Server
cd web_server
python main.py

# Terminal 2: AI Bot (when needed)
cd server
INTERVIEW_ID=xxx python ai-interviewer.py --transport daily
```

### 6. Access Dashboard

Open your browser: http://localhost:8009/dashboard

---

## 📖 What to Read First

**If you're new:**
1. ✅ This file (GETTING_STARTED.md) - You're here!
2. ✅ [README.md](./README.md) - Project overview
3. ✅ [ARCHITECTURE.md](./ARCHITECTURE.md) - Deep dive into architecture
4. ✅ [DEVELOPMENT.md](./DEVELOPMENT.md) - Day-to-day development

**If you're ready to code:**
1. ✅ [ROADMAP.md](./ROADMAP.md) - See what's next
2. ✅ [TODO.md](./TODO.md) - Track your daily tasks
3. ✅ [DEVELOPMENT.md](./DEVELOPMENT.md) - Development guide

---

## 🎯 Your First Task

### Verify Everything Works

1. **Check Dashboard**
   - Go to: http://localhost:8009/dashboard
   - Should see: Interview statistics and list

2. **Schedule a Test Interview**
   - Click "Schedule Interview"
   - Fill in test candidate details
   - Submit

3. **Start AI Bot**
   ```bash
   cd server
   INTERVIEW_ID=interview_xxx python ai-interviewer.py --transport daily
   ```
   (Use the ID from step 2)

4. **Join as Candidate**
   - Open: https://hi2inspire.daily.co/hi2inspire
   - Talk to the AI
   - Say "goodbye" to end

5. **Check Results**
   - Go to: http://localhost:8009/dashboard/interviews
   - See your test interview results

**If everything works:** ✅ You're ready to start development!

---

## 🛠️ Daily Workflow

### Start of Day
```bash
# 1. Update code
git checkout develop
git pull origin develop

# 2. Check what to work on
cat ROADMAP.md | grep "Current Sprint" -A 10

# 3. Start services
./start.sh  # Option 1 or 3
```

### During Development
```bash
# Make changes to code
# Test locally
# Commit frequently

git add .
git commit -m "[Sprint X.X] Brief description"
```

### End of Day
```bash
# 1. Update TODO.md with progress
nano TODO.md

# 2. Push your work
git push origin your-branch

# 3. Stop services
# Press Ctrl+C in terminal
# Or: ./start.sh (option 7)
```

---

## 📂 Project Structure Overview

```
ai-interviewer/
├── 📚 Documentation
│   ├── README.md           ← Start here
│   ├── GETTING_STARTED.md  ← You are here
│   ├── ARCHITECTURE.md     ← Deep dive
│   ├── ROADMAP.md          ← What's next
│   ├── DEVELOPMENT.md      ← Dev guide
│   ├── TODO.md             ← Daily tasks
│   └── CHANGELOG.md        ← Version history
│
├── 🌐 web_server/          ← Dashboard & API
│   ├── main.py             ← Start here
│   ├── routers/            ← HTTP routes
│   ├── services/           ← Business logic
│   ├── templates/          ← HTML templates
│   └── .env                ← Config (don't commit!)
│
├── 🤖 server/              ← AI Bot
│   ├── ai-interviewer.py   ← Main bot
│   └── .env                ← Config (don't commit!)
│
└── 🚀 start.sh             ← Helper script
```

---

## 🔧 Useful Commands

### Web Server
```bash
# Start
cd web_server && python main.py

# Check health
curl http://localhost:8009/health

# View API docs
# Open: http://localhost:8009/docs
```

### AI Bot
```bash
# Start with interview ID
cd server
INTERVIEW_ID=xxx python ai-interviewer.py --transport daily
```

### Database
```bash
# Connect
mongosh mongodb://localhost:27017/hire2inspire_dev_db

# View interviews
db.interview_results.find().pretty()

# Count interviews
db.interview_results.countDocuments()
```

### Git
```bash
# Create feature branch
git checkout -b feature/sprint-1.1-scoring-engine

# Commit with sprint reference
git commit -m "[Sprint 1.1] Implement scoring engine"

# Push
git push origin feature/sprint-1.1-scoring-engine
```

---

## 🐛 Common Issues

### "MongoDB connection failed"
```bash
# Check MongoDB status
sudo systemctl status mongod

# Start MongoDB
sudo systemctl start mongod
```

### "OpenAI API key invalid"
```bash
# Check your .env file
cat web_server/.env | grep OPENAI_API_KEY
cat server/.env | grep OPENAI_API_KEY

# Test the key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_KEY_HERE"
```

### "Port 8009 already in use"
```bash
# Find and kill the process
lsof -ti:8009 | xargs kill -9

# Or use different port
PORT=8010 python main.py
```

### "Dashboard shows no data"
```bash
# Check database
mongosh mongodb://localhost:27017/hire2inspire_dev_db \
  --eval "db.interview_results.countDocuments()"

# Check API
curl http://localhost:8009/debug/interviews

# Restart web server
# (Some changes require restart)
```

**More solutions:** See [DEVELOPMENT.md](./DEVELOPMENT.md#common-issues--solutions)

---

## 📚 Next Steps

### For Solo Development

1. **Read Documentation**
   - Spend 30 minutes reading ARCHITECTURE.md
   - Understand the current issues and roadmap

2. **Set Up Your Workflow**
   - Update TODO.md daily
   - Use ROADMAP.md to track sprints
   - Commit with sprint references

3. **Start First Sprint**
   - Open ROADMAP.md
   - Start Sprint 1.1: Real Scoring Engine
   - Follow tasks in order

4. **Build Incrementally**
   - Complete one sprint at a time
   - Test thoroughly after each change
   - Update documentation as you go

---

## 🎯 Recommended Learning Path

### Week 1: Foundation
- ✅ Set up development environment
- ✅ Read all documentation
- ✅ Run and test the system
- ✅ Complete Sprint 1.1 (Scoring Engine)

### Week 2-3: Core Features
- ✅ Complete Sprint 1.2 (Job Queue)
- ✅ Complete Sprint 1.3 (Database DI)
- ✅ Complete Sprint 1.4 (API Versioning)

### Week 4-8: Architecture
- ✅ Complete Phase 2 sprints
- ✅ Separate frontend
- ✅ Create engine layer

### Week 9-12: Production
- ✅ Complete Phase 3 sprints
- ✅ Add monitoring
- ✅ Deploy to production

---

## 📞 Getting Help

### Self-Help Resources
1. Check [DEVELOPMENT.md](./DEVELOPMENT.md) for common issues
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for context
3. Search the documentation for keywords
4. Check git history for similar changes

### When Stuck
1. Take a break (seriously!)
2. Re-read the relevant section
3. Try a different approach
4. Google the specific error
5. Check Stack Overflow

---

## ✅ Checklist

Before you start coding, make sure:

- [ ] MongoDB is running
- [ ] All .env files are configured
- [ ] Dependencies are installed
- [ ] You can access the dashboard
- [ ] You've read README.md
- [ ] You've read ARCHITECTURE.md
- [ ] You understand the roadmap
- [ ] You know which sprint you're starting

---

## 🎉 You're Ready!

Everything is set up. Here's your action plan:

1. ✅ Start web server: `./start.sh`
2. ✅ Open dashboard: http://localhost:8009/dashboard
3. ✅ Test the system (schedule & conduct an interview)
4. ✅ Read ROADMAP.md to see Sprint 1.1
5. ✅ Start coding!

**Remember:**
- Update TODO.md daily
- Commit frequently with clear messages
- Test everything locally
- Update documentation as you go
- Small, consistent progress is key!

---

**Good luck! You got this! 🚀**

**Questions?** Check [DEVELOPMENT.md](./DEVELOPMENT.md) or review [ARCHITECTURE.md](./ARCHITECTURE.md)
