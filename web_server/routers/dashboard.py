"""
Dashboard Router - Recruiter dashboard endpoints
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    # TODO: Get real data from database
    dashboard_data = {
        "total_interviews": 42,
        "interviews_today": 8,
        "pending_interviews": 5,
        "completed_today": 3,
        "recent_interviews": [
            {
                "id": "int_001",
                "candidate_name": "John Doe",
                "position": "Frontend Developer",
                "status": "completed",
                "score": 85,
                "date": "2025-01-20 14:30"
            },
            {
                "id": "int_002", 
                "candidate_name": "Jane Smith",
                "position": "Backend Developer",
                "status": "in_progress",
                "score": None,
                "date": "2025-01-20 15:00"
            }
        ]
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "data": dashboard_data
    })

@router.get("/interviews", response_class=HTMLResponse)
async def interviews_page(request: Request):
    """Interviews management page"""
    # TODO: Get real interviews from database
    interviews = [
        {
            "id": "int_001",
            "candidate_name": "John Doe",
            "candidate_email": "john@example.com",
            "position": "Frontend Developer",
            "status": "completed",
            "score": 85,
            "scheduled_date": "2025-01-20 14:30",
            "duration": "45 minutes"
        },
        {
            "id": "int_002",
            "candidate_name": "Jane Smith", 
            "candidate_email": "jane@example.com",
            "position": "Backend Developer",
            "status": "scheduled",
            "score": None,
            "scheduled_date": "2025-01-21 10:00",
            "duration": "60 minutes"
        }
    ]
    
    return templates.TemplateResponse("interviews.html", {
        "request": request,
        "interviews": interviews
    })

@router.get("/interview/{interview_id}", response_class=HTMLResponse)
async def interview_detail(request: Request, interview_id: str):
    """Individual interview detail page"""
    # TODO: Get real interview data from database
    interview_data = {
        "id": interview_id,
        "candidate_name": "John Doe",
        "candidate_email": "john@example.com",
        "position": "Frontend Developer",
        "status": "completed",
        "score": 85,
        "scheduled_date": "2025-01-20 14:30",
        "duration": "45 minutes",
        "transcript": "AI: Hello! Welcome to your interview...\nCandidate: Thank you, I'm excited to be here...",
        "evaluation": {
            "correctness": 80,
            "terminology": 85,
            "confidence": 90,
            "experience_relevance": 85,
            "problem_solving": 75
        },
        "questions_asked": [
            "Tell me about your experience with React",
            "How do you handle state management?",
            "Describe a challenging project you worked on"
        ],
        "feedback": None
    }
    
    return templates.TemplateResponse("interview_detail.html", {
        "request": request,
        "interview": interview_data
    })

@router.get("/schedule", response_class=HTMLResponse)
async def schedule_interview_page(request: Request):
    """Schedule new interview page"""
    return templates.TemplateResponse("schedule_interview.html", {
        "request": request
    })

@router.post("/schedule")
async def schedule_interview(
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    position: str = Form(...),
    scheduled_date: str = Form(...),
    job_description_id: str = Form(...),
    resume_data_id: str = Form(...)
):
    """Handle interview scheduling form submission"""
    # TODO: Create interview in database
    # TODO: Generate interview questions
    # TODO: Send email to candidate
    
    interview_data = {
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "position": position,
        "scheduled_date": scheduled_date,
        "status": "scheduled",
        "created_at": datetime.now().isoformat()
    }
    
    # For now, just return success
    return {"success": True, "interview_id": "int_" + str(hash(candidate_email))[:6]}

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Interview settings and configuration page"""
    # TODO: Get current settings from database
    settings = {
        "default_duration": 45,
        "scoring_thresholds": {
            "excellent": 90,
            "good": 75,
            "average": 60,
            "poor": 40
        },
        "question_focus": {
            "technical_skills": 40,
            "experience": 30,
            "problem_solving": 20,
            "cultural_fit": 10
        },
        "difficulty_level": "medium"
    }
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": settings
    })
