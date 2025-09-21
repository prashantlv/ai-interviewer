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

@app.get("/api/bot/interview-config/{interview_id}")
async def get_interview_config(interview_id: str):
    """Provide interview configuration to Pipecat bot"""
    try:
        # Get interview data including JD and resume
        interview_data = await db_service.get_interview(interview_id)
        if not interview_data:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Generate questions based on JD and resume
        questions = await question_engine.generate_questions(
            job_description=interview_data.get("job_description"),
            resume_data=interview_data.get("resume_data"),
            interview_config=interview_data.get("config", {})
        )
        
        return {
            "interview_id": interview_id,
            "questions": questions,
            "scoring_config": interview_data.get("scoring_config", {}),
            "candidate_info": interview_data.get("candidate_info", {})
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
