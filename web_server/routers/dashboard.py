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

# Global database service (will be set by main.py)
db_service = None

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    # Get real data from database via HTTP call to debug endpoint
    try:
        import httpx
        from datetime import datetime, timedelta
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8009/debug/interviews")
            if response.status_code == 200:
                data = response.json()
                interviews = data.get("interviews", [])
            else:
                interviews = []
        
        # Sort interviews by date (most recent first) - FIX #1
        interviews.sort(key=lambda x: x.get("scheduled_date", ""), reverse=True)
        
        # Calculate dashboard statistics
        total_interviews = len(interviews)
        
        # Get today's date for filtering
        today = datetime.now().date()
        
        # Count today's interviews - FIX #1
        interviews_today = 0
        completed_today = 0
        for interview in interviews:
            date_str = interview.get("scheduled_date", "")
            if date_str and date_str != "N/A":
                try:
                    interview_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    if interview_date == today:
                        interviews_today += 1
                        if interview.get("status") == "completed":
                            completed_today += 1
                except:
                    pass
        
        pending_interviews = len([i for i in interviews if i.get("status") in ["scheduled", "in_progress"]])
        
        # Get recent interviews (limit to 5 for dashboard) - already sorted
        recent_interviews = []
        for interview in interviews[:5]:
            recent_interviews.append({
                "id": interview.get("id", "unknown"),
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "position": interview.get("position", "Unknown Position"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score", 0),
                "date": interview.get("scheduled_date", "N/A")
            })
        
        dashboard_data = {
            "total_interviews": total_interviews,
            "interviews_today": interviews_today,
            "pending_interviews": pending_interviews,
            "completed_today": completed_today,
            "recent_interviews": recent_interviews
        }
        
    except Exception as e:
        print(f"❌ Error getting dashboard data: {e}")
        # Fallback to empty data
        dashboard_data = {
            "total_interviews": 0,
            "interviews_today": 0,
            "pending_interviews": 0,
            "completed_today": 0,
            "recent_interviews": []
        }
    
    # Get system status - FIX #3
    # For now, we check database status. Bot status would need heartbeat/health check
    global db_service
    db_status = "connected" if (db_service and db_service.database is not None) else "disconnected"
    
    system_status = {
        "database": db_status,
        "bot": "manual_check",  # Note: Bot status requires manual check - no heartbeat system yet
        "question_engine": "operational",
        "scoring_engine": "operational"
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "data": dashboard_data,
        "system_status": system_status
    })

@router.get("/test-db")
async def test_database_connection():
    """Test endpoint to check database connection"""
    global db_service
    
    return {
        "db_service_is_none": db_service is None,
        "db_service_type": str(type(db_service)),
        "has_database": hasattr(db_service, 'database') if db_service else False,
        "database_is_none": db_service.database is None if (db_service and hasattr(db_service, 'database')) else True
    }

@router.get("/interviews", response_class=HTMLResponse)
async def interviews_page(request: Request, status: Optional[str] = None, page: int = 1):
    """Interviews management page with filtering and pagination"""
    # Pagination settings
    per_page = 20
    offset = (page - 1) * per_page
    
    # Get interviews from database by calling the working debug endpoint
    all_interviews = []  # Initialize early to avoid NameError
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8009/debug/interviews")
            if response.status_code == 200:
                data = response.json()
                all_interviews = data.get("interviews", [])
                print(f"🔍 DEBUG: Retrieved {len(all_interviews)} interviews from debug endpoint")
            else:
                print(f"🔍 DEBUG: Failed to get interviews: {response.status_code}")
                all_interviews = []
        
        # Sort by date - most recent first - FIX #2
        all_interviews.sort(key=lambda x: x.get("scheduled_date", ""), reverse=True)
        
        # Apply pagination
        start_idx = offset
        end_idx = offset + per_page
        interviews = all_interviews[start_idx:end_idx]
        
        total_interviews = len(all_interviews)
        total_pages = (total_interviews + per_page - 1) // per_page if total_interviews > 0 else 0
        
        # Transform data for template
        interview_list = []
        for interview in interviews:
            interview_list.append({
                "id": interview.get("id", "unknown"),
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "candidate_email": "N/A",  # TODO: Add email to database
                "position": interview.get("position", "Unknown Position"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score", 0),
                "scheduled_date": interview.get("created_at", "N/A"),
                "duration": "N/A",  # TODO: Calculate from transcript
                "transcript_available": interview.get("transcript_available", False)
            })
            
    except Exception as e:
        print(f"❌ Error getting interviews: {e}")
        # Fallback to empty list
        all_interviews = []
        interview_list = []
        total_interviews = 0
        total_pages = 0
    
    print(f"🔍 DEBUG: Sending {len(interview_list)} interviews to template")
    for i, interview in enumerate(interview_list):
        print(f"🔍 DEBUG: Interview {i}: {interview}")
    
    # Calculate real statistics for the page footer - FIX #4
    from datetime import datetime
    completed_count = len([i for i in all_interviews if i.get("status") == "completed"])
    completion_rate = (completed_count / total_interviews * 100) if total_interviews > 0 else 0
    
    # Calculate average score (only for completed interviews with scores > 0)
    scored_interviews = [i for i in all_interviews if i.get("status") == "completed" and i.get("score", 0) > 0]
    average_score = sum(i.get("score", 0) for i in scored_interviews) / len(scored_interviews) if scored_interviews else 0
    
    # Calculate hire rate (recommendation = "yes" or "strong_yes")
    # For now, use score >= 65 as proxy for "recommended"
    recommended_count = len([i for i in all_interviews if i.get("status") == "completed" and i.get("score", 0) >= 65])
    hire_rate = (recommended_count / completed_count * 100) if completed_count > 0 else 0
    
    # Count this month's interviews
    from datetime import datetime
    today = datetime.now()
    this_month_count = 0
    for interview in all_interviews:
        # Try multiple date fields
        date_str = interview.get("scheduled_date") or interview.get("created_at") or ""
        if date_str and date_str != "N/A":
            try:
                # Handle both string and datetime objects
                if isinstance(date_str, str):
                    interview_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                elif isinstance(date_str, datetime):
                    interview_date = date_str
                else:
                    continue
                
                if interview_date.year == today.year and interview_date.month == today.month:
                    this_month_count += 1
            except Exception as e:
                print(f"⚠️ Date parsing error for {interview.get('id')}: {date_str} - {e}")
                pass
    
    return templates.TemplateResponse("interviews.html", {
        "request": request,
        "interviews": interview_list,
        "current_status": status,
        "current_page": page,
        "total_pages": total_pages,
        "total_interviews": total_interviews,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else 1,
        "next_page": page + 1 if page < total_pages else total_pages,
        # Real statistics - FIX #4
        "this_month_count": this_month_count,
        "completed_count": completed_count,
        "completion_rate": round(completion_rate, 1),
        "average_score": round(average_score, 1),
        "hire_rate": round(hire_rate)
    })

@router.get("/interview/{interview_id}", response_class=HTMLResponse)
async def interview_detail(request: Request, interview_id: str):
    """Individual interview detail page"""
    # Get interview data from MongoDB directly
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("DATABASE_NAME")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    interview_result = await db.interview_results.find_one({"interview_id": interview_id})
    if interview_result:
        interview_result.pop('_id', None)
    client.close()
    
    if interview_result:
        # Use real data from database
        evaluation = interview_result.get("evaluation", {})
        individual_scores = evaluation.get("individual_scores", {})
        
        interview_data = {
            "id": interview_id,
            "candidate_name": evaluation.get("candidate_name", "Unknown Candidate"),
            "candidate_email": evaluation.get("candidate_email", "N/A"),
            "position": evaluation.get("position", "Unknown Position"),
            "status": interview_result.get("status", "completed"),
            "score": evaluation.get("overall_score", 0),
            "scheduled_date": str(interview_result.get("completed_at", "N/A")),
            "duration": "N/A",
            "transcript": interview_result.get("transcript", "No transcript available"),
            "evaluation": {
                "correctness": individual_scores.get("correctness", 0),
                "terminology": individual_scores.get("terminology", 0),
                "confidence": individual_scores.get("confidence", 0),
                "experience_relevance": individual_scores.get("experience_relevance", 0),
                "problem_solving": individual_scores.get("problem_solving", 0)
            },
            "questions_asked": evaluation.get("questions_asked", []),
            "feedback": evaluation.get("feedback", None),
            "company": evaluation.get("company", "N/A"),
            "recommendation": evaluation.get("recommendation", "N/A")
        }
    else:
        # Fallback to demo data if interview not found
        interview_data = {
            "id": interview_id,
            "candidate_name": "Interview Not Found",
            "candidate_email": "N/A",
            "position": "N/A",
            "status": "not_found",
            "score": 0,
            "scheduled_date": "N/A",
            "duration": "N/A",
            "transcript": f"Interview {interview_id} not found in database",
            "evaluation": {
                "correctness": 0,
                "terminology": 0,
                "confidence": 0,
                "experience_relevance": 0,
                "problem_solving": 0
            },
            "questions_asked": [],
            "feedback": None
        }
    
    return templates.TemplateResponse("interview_result.html", {
        "request": request,
        "interview": interview_data,
        "current_date": datetime.now().strftime("%B %d, %Y")
    })

@router.get("/schedule", response_class=HTMLResponse)
async def schedule_interview_page(request: Request):
    """Schedule new interview page"""
    return templates.TemplateResponse("schedule_interview.html", {
        "request": request
    })

@router.post("/schedule", response_class=HTMLResponse)
async def create_interview(
    request: Request,
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    position: str = Form(...),
    interview_type: str = Form("technical"),
    scoring_level: str = Form("intermediate"),
    notes: str = Form("")
):
    """Create a new interview"""
    import uuid
    from datetime import datetime
    
    # Use the global db_service that was set by main.py
    global db_service
    if db_service is None:
        raise HTTPException(status_code=500, detail="Database service not available")
    
    # Generate unique interview ID
    interview_id = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    # Create interview record
    interview_data = {
        "interview_id": interview_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "position": position,
        "interview_type": interview_type,
        "scoring_level": scoring_level,
        "status": "scheduled",
        "notes": notes,
        "created_at": datetime.now(),
        "room_url": "https://hi2inspire.daily.co/hi2inspire"
    }
    
    try:
        print(f"🔍 DEBUG: Attempting to save interview {interview_id}")
        print(f"   Candidate: {candidate_name}, Position: {position}")
        print(f"   Scoring Level: {scoring_level}")
        print(f"   db_service status: {db_service is not None}")
        
        # Store in database - create proper interview result entry
        success = await db_service.update_interview_result(
            interview_id=interview_id,
            transcript="Interview scheduled - waiting for completion",
            evaluation={
                "candidate_name": candidate_name,
                "candidate_email": candidate_email,
                "position": position,
                "company": "Hire2Inspire Tech Solutions",
                "interview_type": interview_type,
                "scoring_level": scoring_level,
                "status": "scheduled",
                "overall_score": 0,
                "individual_scores": {
                    "correctness": 0,
                    "terminology": 0,
                    "confidence": 0,
                    "experience_relevance": 0,
                    "problem_solving": 0
                },
                "questions_asked": [],
                "notes": notes
            },
            status="scheduled"
        )
        
        print(f"🔍 DEBUG: Save result: {success}")
        
        if success:
            # Redirect to interview instructions
            return templates.TemplateResponse("interview_scheduled.html", {
                "request": request,
                "interview": interview_data
            })
        else:
            raise Exception("Failed to create interview")
            
    except Exception as e:
        return templates.TemplateResponse("schedule_interview.html", {
            "request": request,
            "error": f"Failed to schedule interview: {str(e)}"
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
