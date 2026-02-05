"""
Interviews API Router - REST API endpoints for interview management
"""

import os
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from dependencies import DbServiceDep, CurrentUserDep
from services.hire2inspire_service import hire2inspire_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for API
class InterviewCreate(BaseModel):
    candidate_name: str
    candidate_email: str
    position: str
    job_description_id: str
    resume_data_id: str
    scheduled_date: datetime
    config: Optional[Dict[str, Any]] = {}

class InterviewResponse(BaseModel):
    id: str
    candidate_name: str
    candidate_email: str
    position: str
    status: str
    score: Optional[float]
    scheduled_date: datetime
    created_at: datetime

class InterviewUpdate(BaseModel):
    status: Optional[str] = None
    transcript: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None

@router.get("/", response_model=List[InterviewResponse])
async def get_interviews(
    db: DbServiceDep,
    current_user: CurrentUserDep,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of interviews to return"),
    offset: int = Query(0, description="Number of interviews to skip")
):
    """Get list of interviews with optional filtering (filtered by current user)"""
    try:
        # Get user_id for data isolation
        user_id = current_user.get("userId")
        if not user_id:
            logger.warning("⚠️ No userId found - cannot filter interviews per user")
        
        # Use database service with dependency injection
        interviews = await db.get_interviews(status=status, limit=limit, offset=offset, user_id=user_id)
        
        # If no interviews found, return empty list (not mock data)
        if not interviews:
            return []
        
        # Format for API response
        formatted_interviews = []
        for interview in interviews:
            formatted_interviews.append({
                "id": interview.get("id", "unknown"),
                "candidate_name": interview.get("candidate_name", "Unknown"),
                "candidate_email": interview.get("candidate_email", "unknown@example.com"),
                "position": interview.get("position", "Unknown Position"),
                "status": interview.get("status", "unknown"),
                "score": interview.get("score"),
                "scheduled_date": interview.get("scheduled_date", datetime.now()),
                "created_at": interview.get("created_at", datetime.now())
            })
        
        return formatted_interviews
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve interviews: {str(e)}")

# Legacy mock endpoint (kept for backward compatibility during migration)
@router.get("/mock", response_model=List[InterviewResponse])
async def get_interviews_mock(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of interviews to return"),
    offset: int = Query(0, description="Number of interviews to skip")
):
    """Get mock interviews (deprecated - use / endpoint instead)"""
    mock_interviews = [
        {
            "id": "int_001",
            "candidate_name": "John Doe",
            "candidate_email": "john@example.com",
            "position": "Frontend Developer",
            "status": "completed",
            "score": 85.5,
            "scheduled_date": "2025-01-20T14:30:00",
            "created_at": "2025-01-19T10:00:00"
        },
        {
            "id": "int_002",
            "candidate_name": "Jane Smith",
            "candidate_email": "jane@example.com", 
            "position": "Backend Developer",
            "status": "scheduled",
            "score": None,
            "scheduled_date": "2025-01-21T10:00:00",
            "created_at": "2025-01-20T15:30:00"
        }
    ]
    
    # Apply status filter if provided
    if status:
        mock_interviews = [i for i in mock_interviews if i["status"] == status]
    
    # Apply pagination
    return mock_interviews[offset:offset + limit]

@router.post("/", response_model=InterviewResponse)
async def create_interview(
    interview: InterviewCreate, 
    db: DbServiceDep,
    current_user: CurrentUserDep
):
    """Create a new interview (filtered by current user)"""
    try:
        # Get user_id for data isolation
        user_id = current_user.get("userId")
        if not user_id:
            logger.warning("⚠️ No userId found - interview will not be isolated per user")
        
        # Create interview data dict
        interview_data = {
            "candidate_name": interview.candidate_name,
            "candidate_email": interview.candidate_email,
            "position": interview.position,
            "job_description_id": interview.job_description_id,
            "resume_data_id": interview.resume_data_id,
            "scheduled_date": interview.scheduled_date,
            "config": interview.config or {},
            "status": "scheduled",
            "created_at": datetime.now(),
            "user_id": user_id  # Store user_id for data isolation
        }
        
        # Create in database
        interview_id = await db.create_interview(interview_data)
        
        # TODO: Generate questions based on JD and resume
        # TODO: Send email notification to candidate
        
        response_data = {
            "id": interview_id,
            "candidate_name": interview.candidate_name,
            "candidate_email": interview.candidate_email,
            "position": interview.position,
            "status": "scheduled",
            "score": None,
            "scheduled_date": interview.scheduled_date,
            "created_at": datetime.now()
        }
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create interview: {str(e)}")

@router.get("/{interview_id}")
async def get_interview(interview_id: str, db: DbServiceDep):
    """Get detailed interview information"""
    try:
        # Get from database first
        interview = await db.get_interview(interview_id)
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        
        # Get result data if available
        result = await db.get_interview_result(interview_id)
        
        # Combine interview and result data
        response = {
            "id": interview_id,
            "status": interview.get("status", "unknown"),
            "job_description": interview.get("job_description", {}),
            "resume_data": interview.get("resume_data", {}),
            "config": interview.get("config", {})
        }
        
        if result:
            response.update({
                "transcript": result.get("transcript", ""),
                "evaluation": result.get("evaluation", {}),
                "completed_at": result.get("completed_at")
            })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve interview: {str(e)}")

# Legacy mock endpoint for testing
@router.get("/mock/{interview_id}")
async def get_interview_mock(interview_id: str):
    """Get mock interview (deprecated)"""
    if interview_id == "int_001":
        return {
            "id": interview_id,
            "candidate_name": "John Doe",
            "candidate_email": "john@example.com",
            "position": "Frontend Developer",
            "status": "completed",
            "score": 85.5,
            "scheduled_date": "2025-01-20T14:30:00",
            "created_at": "2025-01-19T10:00:00",
            "transcript": "AI: Hello! Welcome to your interview...\nCandidate: Thank you, I'm excited to be here...",
            "evaluation": {
                "correctness": 80,
                "terminology": 85,
                "confidence": 90,
                "experience_relevance": 85,
                "problem_solving": 75,
                "overall_score": 85.5
            },
            "questions_asked": [
                "Tell me about your experience with React",
                "How do you handle state management in large applications?",
                "Describe a challenging project you worked on"
            ],
            "job_description": {
                "title": "Frontend Developer",
                "skills_required": ["React", "JavaScript", "CSS", "Redux"],
                "experience_level": "Mid-level"
            },
            "resume_data": {
                "skills": ["React", "JavaScript", "Node.js", "CSS"],
                "experience_years": 3,
                "previous_roles": ["Junior Developer", "Frontend Developer"]
            }
        }
    else:
        raise HTTPException(status_code=404, detail="Interview not found")

@router.put("/{interview_id}")
async def update_interview(interview_id: str, update: InterviewUpdate):
    """Update interview information"""
    # TODO: Implement database update
    # For now, return success response
    return {
        "success": True,
        "interview_id": interview_id,
        "updated_fields": update.dict(exclude_unset=True)
    }

@router.delete("/{interview_id}")
async def delete_interview(interview_id: str):
    """Delete an interview"""
    # TODO: Implement database deletion
    return {"success": True, "interview_id": interview_id}

@router.post("/{interview_id}/start")
async def start_interview(interview_id: str):
    """Start an interview session"""
    # TODO: Notify Pipecat bot to start interview
    # TODO: Update interview status to "in_progress"
    daily_domain = os.getenv("DAILY_DOMAIN", "human2intelligence.daily.co")
    return {
        "success": True,
        "interview_id": interview_id,
        "bot_room_url": f"https://{daily_domain}/interview-{interview_id}",
        "candidate_join_url": f"https://{daily_domain}/interview-{interview_id}?participant=candidate"
    }

@router.post("/{interview_id}/complete")
async def complete_interview(
    interview_id: str,
    transcript: str,
    evaluation: Dict[str, Any]
):
    """Mark interview as completed with results"""
    # TODO: Store final results in database
    # TODO: Generate interview report
    # TODO: Send notification to recruiter
    
    return {
        "success": True,
        "interview_id": interview_id,
        "final_score": evaluation.get("overall_score"),
        "report_url": f"/dashboard/interview/{interview_id}"
    }


# Hire2Inspire Integration Endpoints
@router.get("/h2i/jobs")
async def get_h2i_jobs(request: Request):
    """Get all job descriptions from Hire2Inspire"""
    try:
        # Get access token from sign-in (cookie) - prefer this over env var
        access_token = request.cookies.get("accessToken") or request.cookies.get("access_token")
        if access_token:
            logger.info("✅ Using access token from sign-in cookie for get_all_jobs")
        else:
            logger.warning("⚠️ No access token found in cookies - will use env var or login")
        
        # Get user_id from current user for Hire2Inspire credentials
        from dependencies import get_current_user
        try:
            current_user = await get_current_user(request, None)
            user_id = current_user.get("userId")
        except:
            user_id = None
        
        jobs = await hire2inspire_service.get_all_jobs(token=access_token, user_id=user_id)
        
        # Log the result for debugging
        logger.info(f"📊 Returning {len(jobs)} jobs to frontend")
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        logger.error(f"❌ Error fetching jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/h2i/candidates/{job_hash_id}")
async def get_h2i_candidates(job_hash_id: str, request: Request):
    """Get shortlisted candidates for a specific job"""
    try:
        # Get access token from sign-in (cookie)
        access_token = request.cookies.get("accessToken") or request.cookies.get("access_token")
        if access_token:
            logger.info("✅ Using access token from sign-in cookie for get_shortlisted_candidates")
        else:
            logger.warning("⚠️ No access token found in cookies - will use env var or login")
        
        # Get user_id from current user for Hire2Inspire credentials
        from dependencies import get_current_user
        try:
            current_user = await get_current_user(request, None)
            user_id = current_user.get("userId")
        except:
            user_id = None
        
        candidates = await hire2inspire_service.get_shortlisted_candidates(
            job_hash_id, 
            token=access_token,
            user_id=user_id
        )
        return {
            "success": True,
            "job_hash_id": job_hash_id,
            "count": len(candidates),
            "candidates": candidates
        }
    except Exception as e:
        logger.error(f"❌ Error fetching candidates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
