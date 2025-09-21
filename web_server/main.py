#!/usr/bin/env python3
"""
FastAPI Web Server for AI Interviewer
Handles dashboard, interview management, and reporting
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Import our modules
from routers import interviews, dashboard, feedback
from services.database import DatabaseService
from services.question_engine import QuestionEngine
from services.scoring_engine import ScoringEngine
from services.static_data import get_demo_interview_config
import json
import os

# Load environment variables
load_dotenv()

# Initialize services
db_service = DatabaseService()
question_engine = QuestionEngine()
scoring_engine = ScoringEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await db_service.connect()
    print("🚀 FastAPI Web Server started successfully!")
    print(f"📊 Dashboard: http://localhost:8009/dashboard")
    print(f"📚 API Docs: http://localhost:8009/docs")
    yield
    # Shutdown
    await db_service.disconnect()
    print("🛑 FastAPI Web Server shut down")

# Initialize FastAPI app
app = FastAPI(
    title="AI Interviewer Web Platform",
    description="Web dashboard and API for AI-powered interviews",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(interviews.router, prefix="/api/interviews", tags=["interviews"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to dashboard"""
    return RedirectResponse(url="/dashboard")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "mock_mode",
            "question_engine": question_engine.health_check(),
            "scoring_engine": scoring_engine.health_check()
        }
    }

@app.post("/api/bot/interview-result")
async def receive_interview_result(payload: Dict[str, Any]):
    """Receive interview results from Pipecat bot"""
    try:
        interview_id = payload.get("interview_id")
        transcript = payload.get("transcript", "")
        evaluation = payload.get("evaluation", {})
        
        # Store interview results in database
        result = await db_service.update_interview_result(
            interview_id=interview_id,
            transcript=transcript,
            evaluation=evaluation,
            status="completed"
        )
        return {"success": True, "interview_id": interview_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store interview result: {str(e)}")

def _load_json_file(filename: str) -> Dict[str, Any]:
    """Load data from JSON file in current directory (easy to modify for testing)"""
    try:
        # Load from current directory for easy testing
        file_path = os.path.join(os.path.dirname(__file__), filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return {}

@app.get("/api/bot/interview-config/{interview_id}")
async def get_interview_config(interview_id: str):
    """Provide interview configuration to Pipecat bot"""
    try:
        # Load JD and resume from local JSON files (easy to modify for testing)
        job_description = _load_json_file("job_description_local.json")
        candidate_resume = _load_json_file("candidate_resume_local.json")
        
        # Debug: Print loaded candidate name
        print(f"🔍 Loaded candidate: {candidate_resume.get('personal_info', {}).get('name', 'UNKNOWN')}")
        
        if not job_description or not candidate_resume:
            raise HTTPException(status_code=500, detail="Failed to load JD or resume data")
        
        # Create interview config
        interview_config = {
            "difficulty_level": job_description.get("difficulty_level", "medium"),
            "focus_areas": job_description.get("interview_focus_areas", {
                "technical_skills": 40,
                "experience": 25,
                "problem_solving": 20,
                "cultural_fit": 10,
                "leadership": 5
            }),
            "question_count": 8
        }
        
        # Generate questions based on JD and resume
        questions = await question_engine.generate_questions(
            job_description=job_description,
            resume_data=candidate_resume,
            interview_config=interview_config
        )
        
        return {
            "interview_id": interview_id,
            "questions": questions,
            "scoring_config": {
                "correctness": 0.25,
                "terminology": 0.20,
                "confidence": 0.15,
                "experience_relevance": 0.20,
                "problem_solving": 0.20
            },
            "candidate_info": {
                "name": candidate_resume.get("personal_info", {}).get("name", "Unknown"),
                "experience_years": candidate_resume.get("experience", {}).get("total_years", 0),
                "current_role": candidate_resume.get("experience", {}).get("current_role", "Unknown"),
                "skills_match": 85  # Can be calculated from skills comparison
            },
            "job_description": job_description,
            "resume_data": candidate_resume
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get interview config: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,  # Changed to 8009 to avoid conflict
        reload=False,  # Disable reload to prevent issues
        log_level="info"
    )
