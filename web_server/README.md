# AI Interviewer Web Platform

FastAPI-based web dashboard and API for managing AI-powered interviews.

## 🏗️ Architecture

```
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── routers/               # API route handlers
│   ├── dashboard.py       # Dashboard web pages
│   ├── interviews.py      # Interview management API
│   └── feedback.py        # Feedback collection API
├── services/              # Business logic
│   ├── database.py        # MongoDB operations (placeholder)
│   ├── question_engine.py # Dynamic question generation
│   └── scoring_engine.py  # Multi-attribute evaluation
└── templates/             # HTML templates
    ├── base.html          # Base template
    └── dashboard.html     # Main dashboard
```

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Start the Server**
   ```bash
   python main.py
   ```

4. **Access Dashboard**
   - Dashboard: http://localhost:8001/dashboard
   - API Docs: http://localhost:8001/docs

## 🔧 Configuration

### Environment Variables
- `MONGODB_URL`: MongoDB connection string
- `DATABASE_NAME`: Database name for AI interviewer
- `OPENAI_API_KEY`: OpenAI API key for question generation
- `PIPECAT_BOT_URL`: URL of the Pipecat bot server

## 📊 Features

### ✅ Implemented
- **FastAPI Web Server**: RESTful API with auto-documentation
- **Dashboard UI**: Bootstrap-based recruiter dashboard
- **Question Engine**: AI-powered dynamic question generation
- **Scoring Engine**: Multi-attribute candidate evaluation
- **Interview Management**: CRUD operations for interviews
- **Feedback System**: Recruiter feedback collection for AI tuning

### 🔄 Placeholder (Awaiting MongoDB Schema)
- **Database Integration**: MongoDB operations are mocked
- **ATS Integration**: Job description and resume data endpoints

## 🎯 API Endpoints

### Dashboard Routes
- `GET /dashboard` - Main dashboard
- `GET /dashboard/interviews` - Interview list
- `GET /dashboard/schedule` - Schedule new interview

### API Routes
- `GET /api/interviews` - List interviews
- `POST /api/interviews` - Create interview
- `GET /api/interviews/{id}` - Get interview details
- `POST /api/feedback/submit` - Submit feedback

### Bot Integration
- `GET /api/bot/interview-config/{id}` - Provide config to Pipecat bot
- `POST /api/bot/interview-result` - Receive results from bot

## 🤖 Integration with Pipecat Bot

The web server communicates with the Pipecat bot through HTTP APIs:

1. **Interview Config**: Bot requests questions and scoring config
2. **Real-time Updates**: Bot sends evaluation results
3. **Session Management**: Web server tracks interview status

## 🎨 UI Components

- **Responsive Dashboard**: Bootstrap 5 with custom styling
- **Real-time Stats**: Interview counts and status tracking
- **Interactive Tables**: Interview management with filtering
- **Score Visualization**: Color-coded evaluation display

## 🔄 Next Steps

1. **MongoDB Integration**: Replace placeholder database operations
2. **Additional Templates**: Complete remaining dashboard pages
3. **Bot Integration**: Connect with Pipecat bot for live sessions
4. **Testing**: Add comprehensive test suite

## 🛠️ Development

```bash
# Run in development mode
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# View logs
tail -f logs/web_server.log
```

## 📁 File Status

- ✅ **Complete**: Core FastAPI structure, routing, services
- 🔄 **Placeholder**: Database operations (awaiting MongoDB schema)
- ⏳ **Pending**: Additional templates, static assets, testing
