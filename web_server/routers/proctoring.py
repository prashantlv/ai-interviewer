"""
Proctoring Router

Handles interview proctoring functionality including:
- Interview room wrapper page
- Violation logging API
- Proctoring summary endpoint
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from loguru import logger
from redis import Redis

from services.database import db_service  # Use the global connected instance
from services.daily_service import daily_service  # For creating bot tokens


router = APIRouter(tags=["proctoring"])

# Templates
templates = Jinja2Templates(directory="templates")

# Redis connection for distributed locking (shared across all web server workers)
# Use 'redis' hostname in Docker, 'localhost' for local dev
redis_client = Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, decode_responses=True)
BOT_LOCK_TTL = 7200  # 2 hours - lock expires if bot crashes


# ============= Pydantic Models =============

class ViolationData(BaseModel):
    interview_id: str
    violation: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None


class ProctoringSummary(BaseModel):
    interview_id: str
    start_time: str
    end_time: str
    summary: Dict[str, Any]
    violations: List[Dict[str, Any]]


# ============= Interview Room Routes =============

# ============= TEST ROUTE (Development Only) =============

@router.get("/interview/test/room", response_class=HTMLResponse)
async def test_interview_room(request: Request):
    """
    Test route for proctoring - uses a mock Daily.co room
    Access: http://localhost:8009/interview/test/room
    """
    api_base = str(request.base_url).rstrip('/')
    

    daily_domain = os.getenv("DAILY_DOMAIN", "human2intelligence.daily.co")
    test_room_url = f"https://{daily_domain}/test-proctoring"
    
    interview_config = {
        "interview_id": "test-123",
        "room_url": test_room_url,
        "candidate_name": "Test Candidate",
        "api_base": api_base
    }
    interview_config_json = json.dumps(interview_config)
    return templates.TemplateResponse(
        "interview_room.html",
        {
            "request": request,
            "interview_id": "test-123",
            "room_url": test_room_url,  # This won't connect but shows the UI
            "candidate_name": "Test Candidate",
            "position": "Software Developer",
            "api_base": api_base,
            "interview_config_json": interview_config_json
        }
    )


@router.get("/interview/{interview_id}/room", response_class=HTMLResponse)
async def interview_room(request: Request, interview_id: str):
    """
    Serve the proctored interview room wrapper page.
    This embeds Daily.co and adds proctoring JavaScript.
    """
    logger.info(f"📹 Loading interview room for: {interview_id}")
    
    # Get db_service from app state (connected instance)
    db = request.app.state.db_service
    
    # Get bot_manager from app state
    bot_manager = request.app.state.bot_manager
    
    # Get interview details from database
    interview = await db.get_interview_result(interview_id)
    
    if not interview:
        logger.error(f"❌ Interview not found: {interview_id}")
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Interview data is nested in "evaluation" sub-document
    evaluation = interview.get("evaluation", {})
    
    # Get room name and base URL (WITHOUT candidate token)
    room_name = evaluation.get("room_name") or interview.get("room_name", f"interview-{interview_id}")
    daily_domain = os.getenv("DAILY_DOMAIN", "human2intelligence.daily.co")
    base_room_url = f"https://{daily_domain}/{room_name}"
    
    # Get candidate room URL (with candidate token for iframe)
    candidate_room_url = (
        evaluation.get("daily_room_url_with_token") or 
        evaluation.get("room_url") or
        interview.get("daily_room_url_with_token") or 
        interview.get("room_url") or
        base_room_url
    )
    
    # Trigger bot to join when candidate opens the room (if not already running)
    try:
        # Create BOT token (separate from candidate token)
        bot_token = await daily_service.create_bot_token(room_name=room_name)
        
        # Bot joins with its own token (has "AI Interviewer Bot" as user_name)
        bot_room_url = f"{base_room_url}?t={bot_token}" if bot_token else base_room_url
        
        logger.info(f"🤖 Bot URL: {bot_room_url[:50]}... (with bot token)")
        logger.info(f"👤 Candidate URL: {candidate_room_url[:50]}... (with candidate token)")
        
        # Build bot config from interview data (for display only - bot already started from dashboard)
        bot_config = {
            "room_url": bot_room_url,  # ← Now using BOT token!
            "interview_id": interview_id,
            "candidate_name": evaluation.get("candidate_name", "Candidate"),
            "position": evaluation.get("position", "Position"),
            "scoring_level": evaluation.get("scoring_level", "intermediate"),
        }
        
        # NOTE: Bot scheduling removed from here! Bot is scheduled ONCE from dashboard.py
        # when the interview is created. This page just displays the room.
        logger.info(f"📍 Interview room ready. Bot should already be running (started from dashboard).")
        
    except Exception as e:
        logger.error(f"⚠️ Failed to prepare interview room (continuing anyway): {e}")
    
    # Extract interview details from evaluation
    candidate_name = evaluation.get("candidate_name") or interview.get("candidate_name", "Candidate")
    position = evaluation.get("position") or interview.get("job_title") or interview.get("position", "Interview")
    
    # Get API base URL
    api_base = str(request.base_url).rstrip('/')
    
    logger.info(f"✅ Serving interview room: candidate={candidate_name}, room={candidate_room_url}")

    interview_config = {
        "interview_id": interview_id,
        "room_url": candidate_room_url,  # Candidate uses their own token
        "candidate_name": candidate_name,
        "api_base": api_base
    }
    interview_config_json = json.dumps(interview_config)
    
    return templates.TemplateResponse(
        "interview_room.html",
        {
            "request": request,
            "interview_id": interview_id,
            "room_url": candidate_room_url,  # Candidate iframe URL
            "candidate_name": candidate_name,
            "position": position,
            "api_base": api_base,
            "interview_config_json": interview_config_json
        }
    )


@router.get("/interview/{interview_id}/complete", response_class=HTMLResponse)
async def interview_complete(request: Request, interview_id: str):
    """
    Show interview completion page after candidate leaves.
    """
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Interview Complete</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #FFF5F6;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 60px 40px;
                text-align: center;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                max-width: 500px;
            }}
            .checkmark {{
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
            }}
            .checkmark svg {{
                width: 40px;
                height: 40px;
                fill: white;
            }}
            h1 {{
                color: #1f2937;
                margin-bottom: 12px;
            }}
            p {{
                color: #6b7280;
                margin-bottom: 30px;
                line-height: 1.6;
            }}
            .btn {{
                background: linear-gradient(135deg, #FF6183 0%, #E5557A 100%);
                color: white;
                border: none;
                padding: 14px 30px;
                font-size: 1rem;
                border-radius: 8px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="checkmark">
                <svg viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                </svg>
            </div>
            <h1>Interview Complete!</h1>
            <p>Thank you for completing your interview. Our team will review your responses and get back to you soon.</p>
            <p style="font-size: 0.9rem;">You can safely close this window now.</p>
        </div>
    </body>
    </html>
    """)


# ============= Proctoring API Routes =============

@router.post("/api/proctoring/violations")
async def log_violation(data: ViolationData):
    """
    Log a proctoring violation in real-time.
    Called by the frontend when a violation is detected.
    """
    logger.warning(f"🚨 Proctoring violation for interview {data.interview_id}: {data.violation.get('type')}")
    
    try:
        # Get db_service from app state - but we need request, using global for API routes
        # For API routes without request context, we'll use the module-level db_service
        from services.database import db_service as db_svc
        interview = await db_svc.get_interview_result(data.interview_id)
        
        if not interview:
            return {"status": "error", "message": "Interview not found"}
        
        # Get or initialize proctoring data
        proctoring_data = interview.get("proctoring", {
            "violations": [],
            "summary": {
                "tab_switches": 0,
                "fullscreen_exits": 0,
                "window_blurs": 0,
                "blocked_shortcuts": []
            }
        })
        
        # Add violation
        proctoring_data["violations"].append(data.violation)
        
        # Update summary if provided
        if data.summary:
            proctoring_data["summary"] = data.summary
        
        # Update interview record
        await db_svc.update_interview(
            data.interview_id,
            {"proctoring": proctoring_data}
        )
        
        return {"status": "logged", "violation_count": len(proctoring_data["violations"])}
        
    except Exception as e:
        logger.error(f"❌ Failed to log violation: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/api/proctoring/summary")
async def save_proctoring_summary(data: ProctoringSummary, request: Request):
    """
    Save final proctoring summary when interview ends.
    """
    logger.info(f"📊 Saving proctoring summary for interview {data.interview_id}")
    
    try:
        # Get db_service from app state
        db = request.app.state.db_service
        
        # Calculate risk score based on violations
        total_violations = data.summary.get("total_violations", 0)
        tab_switches = data.summary.get("tab_switches", 0)
        fullscreen_exits = data.summary.get("fullscreen_exits", 0)
        
        if total_violations == 0:
            risk_level = "low"
        elif total_violations <= 3 and tab_switches <= 2:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # Prepare final proctoring data
        proctoring_data = {
            "start_time": data.start_time,
            "end_time": data.end_time,
            "summary": data.summary,
            "violations": data.violations,
            "risk_level": risk_level,
            "completed": True
        }
        
        # Update interview record
        logger.info(f"📝 Updating interview {data.interview_id} with proctoring data...")
        logger.debug(f"   Proctoring data: {proctoring_data}")
        
        result = await db.update_interview(
            data.interview_id,
            {"proctoring": proctoring_data}
        )
        
        if result:
            logger.info(f"✅ Proctoring summary saved. Risk level: {risk_level}, Violations: {total_violations}")
            
            # VERIFY: Read back the data to confirm it was saved
            verify_interview = await db.get_interview_result(data.interview_id)
            if verify_interview and verify_interview.get("proctoring"):
                logger.info(f"✅ VERIFIED: Proctoring data is in DB")
                logger.info(f"   DB Risk Level: {verify_interview.get('proctoring', {}).get('risk_level')}")
                logger.info(f"   DB Violations: {len(verify_interview.get('proctoring', {}).get('violations', []))}")
            else:
                logger.error(f"❌ FAILED: Proctoring data NOT found in DB after save!")
        else:
            logger.warning(f"⚠️ Proctoring update returned False for {data.interview_id}")
        
        return {
            "status": "saved",
            "risk_level": risk_level,
            "total_violations": total_violations
        }
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to save proctoring summary: {e}")
        logger.error(f"   Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}




@router.post("/api/interview/{interview_id}/end")
async def end_interview(interview_id: str, request: Request):
    """
    Mark interview as ended by candidate.
    Called when candidate clicks 'End Interview' button.
    """
    logger.info(f"🏁 Ending interview {interview_id}")
    
    try:
        db = request.app.state.db_service
        
        # Update the interview status
        from datetime import datetime
        
        result = await db.database.interview_results.update_one(
            {"interview_id": interview_id},
            {
                "$set": {
                    "status": "ended_by_candidate",
                    "ended_at": datetime.now(),
                    "ended_by": "candidate"
                }
            }
        )
        
        # Release Redis lock to allow cleanup/rerun if needed
        lock_key = f"bot_lock:{interview_id}"
        redis_client.delete(lock_key)
        logger.info(f"🔓 Released bot lock for {interview_id}")
        
        if result.modified_count > 0:
            logger.info(f"✅ Interview {interview_id} marked as ended by candidate")
            return {"status": "success", "message": "Interview ended"}
        else:
            logger.warning(f"⚠️ Interview {interview_id} not found or not modified")
            return {"status": "warning", "message": "Interview not found or already ended"}
            
    except Exception as e:
        logger.error(f"❌ Failed to end interview {interview_id}: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/api/proctoring/{interview_id}")
async def get_proctoring_data(interview_id: str, request: Request):
    """
    Get proctoring data for an interview.
    """
    db = request.app.state.db_service
    interview = await db.get_interview_result(interview_id)
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    proctoring_data = interview.get("proctoring", {})
    
    return {
        "interview_id": interview_id,
        "proctoring": proctoring_data
    }



