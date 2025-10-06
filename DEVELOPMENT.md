# Development Guide

**AI Interviewer Project**  
**Last Updated:** October 6, 2025

---

## 🚀 Quick Start

### First Time Setup

```bash
# Clone repository
git clone <repo-url>
cd ai-interviewer

# Install dependencies
cd web_server
pip install -r requirements.txt

cd ../server
pip install -r requirements.txt

# Set up environment variables
cp web_server/.env.example web_server/.env
cp server/.env.example server/.env

# Edit .env files with your API keys
nano web_server/.env
nano server/.env

# Start MongoDB (if local)
mongod --dbpath /path/to/data

# Start web server
cd web_server
python main.py

# In another terminal, test the system
curl http://localhost:8009/health
```

---

## 📁 Project Structure

```
ai-interviewer/
├── docs/                       # 📚 Documentation
│   ├── ARCHITECTURE.md         # System architecture (READ FIRST!)
│   ├── ROADMAP.md              # Development roadmap
│   └── DEVELOPMENT.md          # This file
│
├── web_server/                 # 🌐 Web Server (FastAPI)
│   ├── main.py                 # Main application entry
│   ├── routers/                # HTTP route handlers
│   │   └── dashboard.py
│   ├── services/               # Business logic
│   │   └── database.py
│   ├── templates/              # HTML templates (Jinja2)
│   └── static/                 # CSS, JS, images
│
├── server/                     # 🤖 AI Bot (Pipecat)
│   ├── ai-interviewer.py       # Main bot script
│   ├── bot-openai.py           # OpenAI integration
│   └── bot-gemini.py           # Gemini integration
│
└── client/                     # 📱 Client apps
    ├── javascript/
    ├── react/
    └── react-native/
```

---

## 🛠️ Development Workflow

### Daily Workflow

1. **Start Your Day**
   ```bash
   # Update from develop
   git checkout develop
   git pull origin develop
   
   # Check current sprint
   cat ROADMAP.md | grep "Current Sprint" -A 10
   ```

2. **Pick a Task**
   - Look at current sprint in ROADMAP.md
   - Pick an unchecked task
   - Create a feature branch

3. **Create Feature Branch**
   ```bash
   # Naming: feature/sprint-X.X-short-description
   git checkout -b feature/sprint-1.1-scoring-engine
   ```

4. **Develop & Test**
   ```bash
   # Make changes
   # Test locally
   # Run tests (when available)
   python -m pytest tests/
   ```

5. **Commit**
   ```bash
   git add .
   git commit -m "[Sprint 1.1] Implement LLM-based scoring engine"
   ```

6. **Push & Create PR**
   ```bash
   git push origin feature/sprint-1.1-scoring-engine
   # Create PR to 'develop' branch
   ```

---

## 🔧 Common Tasks

### Start Web Server

```bash
cd web_server
python main.py

# Server runs on http://localhost:8009
# Dashboard: http://localhost:8009/dashboard
# API Docs: http://localhost:8009/docs
```

### Start AI Bot (Manual - Current Method)

```bash
cd server
source ~/miniconda3/etc/profile.d/conda.sh
conda activate pipecat-env

# Start bot with interview ID
DAILY_SAMPLE_ROOM_URL=https://hi2inspire.daily.co/hi2inspire \
WEB_SERVER_URL=http://localhost:8009 \
INTERVIEW_ID=interview_xxx \
python ai-interviewer.py --transport daily
```

### Test Interview Flow

```bash
# 1. Schedule interview via dashboard
# 2. Get interview ID from response
# 3. Start AI bot with that ID (see above)
# 4. Join Daily.co room as candidate
# 5. Talk to AI
# 6. Leave call
# 7. Check results in dashboard
```

### Database Operations

```bash
# Connect to MongoDB
mongosh mongodb://localhost:27017/hire2inspire_dev_db

# List collections
show collections

# View interviews
db.interview_results.find().pretty()

# Count interviews
db.interview_results.countDocuments()

# Delete test data
db.interview_results.deleteMany({ id: /test_/ })
```

### Check Logs

```bash
# Web server logs (in terminal where it's running)
# Look for:
✅ Connected to MongoDB
🚀 FastAPI Web Server started
📊 Dashboard: http://localhost:8009/dashboard

# AI bot logs (in terminal where it's running)
# Look for:
🤖 AI Interviewer Bot starting...
✅ Connected to Daily.co room
🎤 Candidate joined!
```

---

## 🧪 Testing

### Manual Testing Checklist

**Web Dashboard:**
- [ ] Homepage loads
- [ ] Interviews list shows data
- [ ] Interview details show correctly
- [ ] Schedule interview form works
- [ ] Stats are accurate

**AI Bot:**
- [ ] Bot starts successfully
- [ ] Bot joins Daily.co room
- [ ] Bot greets candidate by name
- [ ] Bot asks questions
- [ ] Bot understands responses
- [ ] Bot sends results to server

**End-to-End:**
- [ ] Schedule interview
- [ ] Start bot
- [ ] Conduct interview
- [ ] Results appear in dashboard
- [ ] Scores are correct
- [ ] Transcript is saved

### Automated Testing (Coming in Phase 3)

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Coverage report
pytest --cov=web_server tests/
```

---

## 🐛 Debugging

### Web Server Issues

```bash
# Check if server is running
curl http://localhost:8009/health

# Check database connection
curl http://localhost:8009/debug/interviews

# View detailed logs
# Add print statements in code
print(f"🔍 DEBUG: {variable_name}")
```

### AI Bot Issues

```bash
# Check environment variables
echo $WEB_SERVER_URL
echo $INTERVIEW_ID
echo $OPENAI_API_KEY

# Test web server API from bot's perspective
curl http://localhost:8009/api/bot/interview-config/test_interview_001

# Check Daily.co connection
# Look for WebRTC connection errors in logs
```

### Database Issues

```bash
# Check MongoDB is running
mongosh --eval "db.adminCommand('ping')"

# Check connection string
cat web_server/.env | grep MONGODB_URI

# View recent interviews
mongosh mongodb://localhost:27017/hire2inspire_dev_db \
  --eval "db.interview_results.find().sort({created_at: -1}).limit(5)"
```

---

## 📝 Code Style Guide

### Python Style

```python
# Use type hints
async def get_interview(interview_id: str) -> Optional[Dict[str, Any]]:
    pass

# Use descriptive names
candidate_name = "John Doe"  # Good
cn = "John Doe"              # Bad

# Add docstrings
async def score_interview(transcript: List[Dict]) -> float:
    """
    Score an interview based on transcript.
    
    Args:
        transcript: List of conversation exchanges
        
    Returns:
        Score between 0.0 and 100.0
    """
    pass

# Use async/await for I/O
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### File Organization

```python
# Order: imports, constants, classes, functions, main

# Imports
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends

# Constants
MAX_QUESTIONS = 10
DEFAULT_TIMEOUT = 30

# Classes
class InterviewService:
    pass

# Functions
async def create_interview():
    pass

# Main (if script)
if __name__ == "__main__":
    asyncio.run(main())
```

### Commit Messages

```bash
# Format: [Sprint X.X] Brief description
[Sprint 1.1] Implement LLM-based scoring engine
[Sprint 1.2] Add Redis job queue for bot management
[Hotfix] Fix dashboard date sorting bug
[Docs] Update ARCHITECTURE.md with new structure
```

---

## 🔐 Environment Variables

### Required Variables

**web_server/.env:**
```bash
# Database
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=hire2inspire_dev_db

# OpenAI
OPENAI_API_KEY=sk-...

# Server
PORT=8009
ENV=development
```

**server/.env:**
```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Daily.co
DAILY_API_KEY=...
DAILY_SAMPLE_ROOM_URL=https://hi2inspire.daily.co/hi2inspire

# Deepgram (STT)
DEEPGRAM_API_KEY=...

# Cartesia (TTS)
CARTESIA_API_KEY=...

# Web Server
WEB_SERVER_URL=http://localhost:8009

# Interview ID (set at runtime)
INTERVIEW_ID=interview_xxx
```

---

## 🚨 Common Issues & Solutions

### Issue: "MongoDB connection failed"
**Solution:**
```bash
# Check MongoDB is running
sudo systemctl status mongod

# Start MongoDB
sudo systemctl start mongod

# Check connection string
cat web_server/.env | grep MONGODB_URI
```

### Issue: "OpenAI API key invalid"
**Solution:**
```bash
# Check key is set
cat server/.env | grep OPENAI_API_KEY

# Test key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: "Bot doesn't start"
**Solution:**
```bash
# Check all environment variables
echo $WEB_SERVER_URL
echo $INTERVIEW_ID
echo $DAILY_SAMPLE_ROOM_URL

# Check web server is running
curl http://localhost:8009/health

# Check interview config exists
curl http://localhost:8009/api/bot/interview-config/$INTERVIEW_ID
```

### Issue: "Dashboard shows 0 interviews"
**Solution:**
```bash
# Check database directly
mongosh mongodb://localhost:27017/hire2inspire_dev_db \
  --eval "db.interview_results.countDocuments()"

# Check API endpoint
curl http://localhost:8009/debug/interviews

# Restart web server
# (Changes to database.py require restart)
```

### Issue: "Score shows as blank"
**Solution:**
```bash
# Check if score is 0 or None
mongosh mongodb://localhost:27017/hire2inspire_dev_db \
  --eval "db.interview_results.find({}, {evaluation: 1})"

# Template uses: {% if interview.score is not none %}
# Not: {% if interview.score %}  (treats 0 as False!)
```

---

## 📚 Additional Resources

### Project Documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Full system architecture
- [ROADMAP.md](./ROADMAP.md) - Development roadmap
- [API.md](./API.md) - API documentation (coming soon)

### External Resources
- FastAPI Docs: https://fastapi.tiangolo.com/
- Pipecat Docs: https://github.com/pipecat-ai/pipecat
- MongoDB Python: https://motor.readthedocs.io/
- Daily.co API: https://docs.daily.co/

### Learning Materials
- FastAPI Tutorial: https://fastapi.tiangolo.com/tutorial/
- Async Python: https://realpython.com/async-io-python/
- MongoDB Best Practices: https://www.mongodb.com/docs/manual/

---

## 🤝 Contributing

### Before You Start
1. Read ARCHITECTURE.md
2. Check ROADMAP.md for current sprint
3. Create feature branch from `develop`
4. Follow code style guide
5. Test thoroughly

### Creating a PR
1. Write clear commit messages
2. Update relevant documentation
3. Test all changes
4. Create PR to `develop` branch
5. Request review from team

### Code Review Checklist
- [ ] Code follows style guide
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling added
- [ ] Logging added where needed

---

## 📞 Getting Help

### Questions?
1. Check this guide first
2. Check ARCHITECTURE.md
3. Check existing issues
4. Ask team members
5. Create new issue with details

### Reporting Bugs
```markdown
## Bug Report

**Description:** Brief description

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:** What should happen

**Actual Behavior:** What actually happens

**Environment:**
- OS: 
- Python Version:
- Branch:

**Logs:**
```
paste relevant logs here
```
```

---

## 🎯 Quick Reference

### Start Development
```bash
git checkout develop
git pull origin develop
git checkout -b feature/sprint-X.X-name
```

### Run Locally
```bash
# Terminal 1: Web Server
cd web_server && python main.py

# Terminal 2: AI Bot (when needed)
cd server && INTERVIEW_ID=xxx python ai-interviewer.py --transport daily
```

### Deploy Changes
```bash
git add .
git commit -m "[Sprint X.X] Description"
git push origin feature/sprint-X.X-name
# Create PR
```

### Update Docs
```bash
nano ROADMAP.md  # Update sprint progress
git commit -m "[Docs] Update roadmap"
```

---

**Happy Coding! 🚀**

**Questions?** Check ARCHITECTURE.md or ask the team!

