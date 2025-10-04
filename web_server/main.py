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

# Make database service available to routers BEFORE including them
import routers.dashboard as dashboard_module
dashboard_module.db_service = db_service
dashboard_module.shared_db_service = db_service

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
            "database": db_service.health_check(),
            "question_engine": question_engine.health_check(),
            "scoring_engine": scoring_engine.health_check()
        }
    }

@app.get("/debug/interviews")
async def debug_interviews():
    """Debug endpoint to check stored interviews"""
    try:
        interviews = await db_service.get_interviews()
        return {
            "count": len(interviews),
            "interviews": interviews
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/dashboard-test")
async def debug_dashboard_test():
    """Debug endpoint to test dashboard data flow"""
    try:
        # Test the same logic as dashboard route
        interviews = await db_service.get_interviews()
        print(f"🔍 DEBUG: Retrieved {len(interviews)} interviews from database")
        
        # Transform data for template (same as dashboard route)
        interview_list = []
        for interview in interviews:
            interview_list.append({
                "id": interview.get("id", "unknown"),
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "candidate_email": "N/A",
                "position": interview.get("position", "Unknown Position"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score", 0),
                "scheduled_date": interview.get("created_at", "N/A"),
                "duration": "N/A",
                "transcript_available": interview.get("transcript_available", False)
            })
        
        return {
            "raw_interviews": interviews,
            "transformed_interviews": interview_list,
            "count": len(interview_list)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/dashboard/interviews")
async def get_dashboard_interviews(status: Optional[str] = None, page: int = 1):
    """API endpoint for dashboard to get interview data"""
    try:
        per_page = 20
        offset = (page - 1) * per_page
        
        interviews = await db_service.get_interviews(status=status, limit=per_page, offset=offset)
        
        # Transform data for template
        interview_list = []
        for interview in interviews:
            interview_list.append({
                "id": interview.get("id", "unknown"),
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "candidate_email": "N/A",
                "position": interview.get("position", "Unknown Position"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score", 0),
                "scheduled_date": interview.get("created_at", "N/A"),
                "duration": "N/A",
                "transcript_available": interview.get("transcript_available", False)
            })
        
        return {
            "interviews": interview_list,
            "count": len(interview_list)
        }
    except Exception as e:
        return {"error": str(e)}

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
        # First, try to get interview from database
        interview = await db_service.get_interview_result(interview_id)
        
        if interview and interview.get("evaluation"):
            # Extract candidate info from database
            evaluation = interview.get("evaluation", {})
            candidate_name = evaluation.get("candidate_name", "Unknown Candidate")
            candidate_email = evaluation.get("candidate_email", "N/A")
            position = evaluation.get("position", "Unknown Position")
            company = evaluation.get("company", "Hire2Inspire Tech Solutions")
            
            print(f"🔍 Loaded from DB - Candidate: {candidate_name}, Position: {position}")
            
            # Build candidate info from database
            candidate_info = {
                "name": candidate_name,
                "email": candidate_email
            }
            
            # Build job description from database
            job_description_data = {
                "title": position,
                "company": company,
                "location": "Remote / Bangalore, India",
                "difficulty_level": "medium"
            }
        else:
            # Fallback to JSON files for testing/development
            print(f"⚠️ Interview {interview_id} not found in DB, using JSON files as fallback")
            job_description_data = _load_json_file("job_description_local.json")
            candidate_resume = _load_json_file("candidate_resume_local.json")
            
            candidate_info = candidate_resume.get("personal_info", {})
            candidate_name = candidate_info.get("name", "Unknown Candidate")
            
            print(f"🔍 Loaded from JSON - Candidate: {candidate_name}")
            
            # Use JSON file structure for backward compatibility
            job_description = job_description_data
            candidate_resume = candidate_resume
        
        # For DB-loaded interviews, create compatible structure
        if interview and interview.get("evaluation"):
            job_description = job_description_data
            candidate_resume = {
                "personal_info": candidate_info,
                "experience": {
                    "current_role": evaluation.get("interview_type", "Developer"),
                    "total_years": 6
                }
            }
        
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
