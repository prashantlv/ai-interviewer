"""
Interviews API Router - REST API endpoints for interview management
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

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
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of interviews to return"),
    offset: int = Query(0, description="Number of interviews to skip")
):
    """Get list of interviews with optional filtering"""
    # TODO: Implement database query
    # For now, return mock data
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
async def create_interview(interview: InterviewCreate):
    """Create a new interview"""
    # TODO: Implement database creation
    # TODO: Generate questions based on JD and resume
    # TODO: Send email notification to candidate
    
    # Mock creation
    interview_id = f"int_{hash(interview.candidate_email) % 100000:05d}"
    
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

@router.get("/{interview_id}")
async def get_interview(interview_id: str):
    """Get detailed interview information"""
    # TODO: Implement database query
    # Mock detailed interview data
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
    return {
        "success": True,
        "interview_id": interview_id,
        "bot_room_url": f"https://hi2inspire.daily.co/interview-{interview_id}",
        "candidate_join_url": f"https://hi2inspire.daily.co/interview-{interview_id}?participant=candidate"
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
