#!/usr/bin/env python3
"""
FastAPI Web Server for AI Interviewer
Handles dashboard, interview management, and reporting
"""

# Load environment variables FIRST (before any other imports that might use them)
from dotenv import load_dotenv
from pathlib import Path

# Load from web_server/.env (if exists)
load_dotenv()
# Also load from server/.env (for MongoDB and other shared configs)
server_env = Path(__file__).parent.parent / "server" / ".env"
if server_env.exists():
    load_dotenv(server_env)

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Import our modules
from routers import interviews, dashboard, feedback, bots, tavus, voices, scoring_settings, proctoring
from services.database import DatabaseService
from services.question_engine import QuestionEngine
from services.scoring_engine import ScoringEngine
from services.scoring_config_service import ScoringConfigService
from services.bot_manager import initialize_bot_manager, get_bot_manager
from services.static_data import get_demo_interview_config
from services.daily_service import daily_service
import json

# Initialize services
db_service = DatabaseService()
question_engine = QuestionEngine()
scoring_engine = ScoringEngine()
scoring_config_service = ScoringConfigService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await db_service.connect()
    
    # Initialize scoring config service with database
    scoring_config_service.database = db_service.database
    await scoring_config_service.initialize_default_configs()
    
    # Initialize bot manager with Redis
    # Parse REDIS_URL if provided, otherwise use defaults
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        # Parse redis://host:port or redis://host:port/db
        import re
        match = re.match(r"redis://([^:/]+)(?::(\d+))?(?:/(\d+))?", redis_url)
        if match:
            redis_host = match.group(1)
            redis_port = int(match.group(2)) if match.group(2) else 6379
            initialize_bot_manager(redis_host=redis_host, redis_port=redis_port)
        else:
            initialize_bot_manager()
    else:
        # Try individual env vars
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        initialize_bot_manager(redis_host=redis_host, redis_port=redis_port)
    
    # Store services in app state for dependency injection
    app.state.db_service = db_service
    app.state.bot_manager = get_bot_manager()
    app.state.scoring_config_service = scoring_config_service
    app.state.question_engine = question_engine
    app.state.scoring_engine = scoring_engine
    
    print("🚀 FastAPI Web Server started successfully!")
    print(f"📊 Dashboard: http://localhost:8009/dashboard")
    print(f"📚 API Docs: http://localhost:8009/docs")
    print(f"🤖 Bot Queue System: Ready")
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

# Configure Jinja2 templates (shared across all routers)
# Disable caching for development to ensure template changes are reflected immediately
templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True
templates.env.cache = None  # Completely disable cache

# Make templates available to routers via app state
app.state.templates = templates

# Include routers
# Dashboard (no versioning - UI routes)
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(scoring_settings.router, prefix="/dashboard/scoring-settings", tags=["scoring-settings"])

# API v1 routes
app.include_router(interviews.router, prefix="/api/v1/interviews", tags=["interviews-v1"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback-v1"])
app.include_router(bots.router, prefix="/api/v1/bots", tags=["bots-v1"])
app.include_router(voices.router, prefix="/api/v1/voices", tags=["voices-v1"])

# Replica management routes (includes both dashboard and API)
# Dashboard: /dashboard/replicas
# API: /api/v1/tavus/* (backend still uses tavus service)
app.include_router(tavus.router, tags=["replicas"])
app.include_router(proctoring.router, tags=["proctoring"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to dashboard"""
    return RedirectResponse(url="/dashboard")

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint - Basic status"""
    from dependencies import DbServiceDep, BotManagerDep
    db: DbServiceDep = request.app.state.db_service
    bot_manager: BotManagerDep = request.app.state.bot_manager
    
    db_health = await db.health_check()
    return {
        "status": "healthy" if db_health.get("status") == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_health.get("status", "unknown"),
        "bot_queue": bot_manager.health_check().get("status", "unknown")
    }

@app.get("/api/v1/health")
async def health_check_detailed(request: Request):
    """Detailed health check endpoint with full statistics"""
    from dependencies import DbServiceDep, BotManagerDep, QuestionEngineDep, ScoringEngineDep
    
    db: DbServiceDep = request.app.state.db_service
    bot_manager: BotManagerDep = request.app.state.bot_manager
    question_eng: QuestionEngineDep = request.app.state.question_engine
    scoring_eng: ScoringEngineDep = request.app.state.scoring_engine
    
    # Get detailed health for each service
    db_health = await db.health_check()
    bot_health = bot_manager.health_check()
    question_health = question_eng.health_check()
    scoring_health = scoring_eng.health_check()
    
    # Calculate overall status
    services_up = sum([
        db_health.get("status") == "connected",
        bot_health.get("status") == "operational",
        question_health.get("status") == "operational",
        scoring_health.get("status") == "operational"
    ])
    total_services = 4
    health_percentage = (services_up / total_services) * 100
    
    overall_status = "healthy" if health_percentage >= 75 else "degraded" if health_percentage >= 50 else "critical"
    
    return {
        "status": overall_status,
        "health_percentage": health_percentage,
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": db_health,
            "bot_queue": bot_health,
            "question_engine": question_health,
            "scoring_engine": scoring_health
        }
    }

@app.get("/debug/interviews")
async def debug_interviews(request: Request):
    """Debug endpoint to check stored interviews"""
    try:
        db = request.app.state.db_service
        interviews = await db.get_interviews()
        return {
            "count": len(interviews),
            "interviews": interviews
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/dashboard-test")
async def debug_dashboard_test(request: Request):
    """Debug endpoint to test dashboard data flow"""
    try:
        # Get db_service from app state
        db = request.app.state.db_service
        # Test the same logic as dashboard route
        interviews = await db.get_interviews()
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

@app.get("/api/v1/dashboard/interviews")
async def get_dashboard_interviews(
    request: Request,
    status: Optional[str] = None,
    page: int = 1
):
    """API endpoint for dashboard to get interview data"""
    try:
        # Get db_service from app state
        db = request.app.state.db_service
        per_page = 20
        offset = (page - 1) * per_page
        
        interviews = await db.get_interviews(status=status, limit=per_page, offset=offset)
        
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

@app.post("/api/v1/bot/interview-result")
async def receive_interview_result(
    request: Request,
    payload: Dict[str, Any]
):
    """Receive interview results from Pipecat bot (API v1)"""
    try:
        # Get db_service from app state
        db = request.app.state.db_service
        interview_id = payload.get("interview_id")
        transcript = payload.get("transcript", "")
        evaluation = payload.get("evaluation", {})
        recording_payload = payload.get("recording")
        
        # Enrich recording info with Daily metadata/access link if available
        if recording_payload and recording_payload.get("recording_id"):
            enriched = await daily_service.fetch_recording_asset(recording_payload["recording_id"])
            if enriched:
                recording_payload.update({k: v for k, v in enriched.items() if v is not None})
        
        # Store interview results in database
        result = await db.update_interview_result(
            interview_id=interview_id,
            transcript=transcript,
            evaluation=evaluation,
            status="completed",
            recording=recording_payload
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

@app.get("/api/v1/bot/interview-config/{interview_id}")
async def get_interview_config(interview_id: str, scoring_level: Optional[str] = None):
    """Provide interview configuration to Pipecat bot (API v1 - includes scoring config)"""
    try:
        # First, try to get interview from database
        interview = await db_service.get_interview_result(interview_id)
        
        # Get scoring level from interview record if not provided
        if interview and not scoring_level:
            evaluation = interview.get("evaluation", {})
            scoring_level = evaluation.get("scoring_level", "intermediate")
            print(f"📊 Using scoring level from interview: {scoring_level}")
        elif not scoring_level:
            scoring_level = "intermediate"  # Default fallback
        
        if interview and interview.get("evaluation"):
            # Extract candidate info from database
            evaluation = interview.get("evaluation", {})
            candidate_name = evaluation.get("candidate_name", "Unknown Candidate")
            candidate_email = evaluation.get("candidate_email", "N/A")
            position = evaluation.get("position", "Unknown Position")
            company = evaluation.get("company", "Hire2Inspire Tech Solutions")
            
            # NEW: Get parsed JD and Resume from database
            parsed_jd = evaluation.get("job_description_parsed", {})
            parsed_resume = evaluation.get("candidate_resume_parsed", {})
            
            print(f"🔍 Loaded from DB - Candidate: {candidate_name}, Position: {position}")
            print(f"📄 Parsed JD skills: {', '.join(parsed_jd.get('skills_required', [])[:5])}")
            print(f"👤 Parsed Resume skills: {', '.join(parsed_resume.get('skills', [])[:5])}")
            
            # Build candidate info from database (use parsed data if available)
            candidate_info = {
                "name": parsed_resume.get("name") or candidate_name,
                "email": parsed_resume.get("email") or candidate_email
            }
            
            # Build job description from database (use parsed data if available)
            job_description_data = parsed_jd if parsed_jd else {
                "title": position,
                "company": company,
                "location": "Remote / Bangalore, India",
                "difficulty_level": "medium",
                "skills_required": ["Python", "FastAPI", "MongoDB"]
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
            # Use parsed resume data if available
            if parsed_resume and parsed_resume.get("skills"):
                candidate_resume = {
                    "personal_info": candidate_info,
                    "experience": {
                        "current_role": parsed_resume.get("previous_roles", ["Developer"])[0] if parsed_resume.get("previous_roles") else "Developer",
                        "total_years": parsed_resume.get("experience_years", 0)
                    },
                    "skills": parsed_resume.get("skills", []),
                    "education": parsed_resume.get("education", []),
                    "previous_roles": parsed_resume.get("previous_roles", [])
                }
            else:
                # Fallback structure
                candidate_resume = {
                    "personal_info": candidate_info,
                    "experience": {
                        "current_role": evaluation.get("interview_type", "Developer"),
                        "total_years": 0
                    },
                    "skills": [],
                    "education": [],
                    "previous_roles": []
                }
        
        # Get interview type from evaluation (defaults to technical)
        interview_type = evaluation.get("interview_type", "technical") if interview and interview.get("evaluation") else "technical"
        print(f"🎯 Interview type: {interview_type}")
        
        # Define focus areas based on interview type
        interview_type_focus_areas = {
            "technical": {
                "technical_skills": 45,
                "experience": 25,
                "problem_solving": 20,
                "cultural_fit": 10,
                "behavioral": 0
            },
            "behavioral": {
                "technical_skills": 10,
                "experience": 25,
                "problem_solving": 15,
                "cultural_fit": 25,
                "behavioral": 25
            },
            "mixed": {
                "technical_skills": 30,
                "experience": 20,
                "problem_solving": 15,
                "cultural_fit": 15,
                "behavioral": 20
            },
            "leadership": {
                "technical_skills": 15,
                "experience": 30,
                "problem_solving": 15,
                "cultural_fit": 20,
                "behavioral": 20
            },
            "cultural_fit": {
                "technical_skills": 5,
                "experience": 20,
                "problem_solving": 10,
                "cultural_fit": 40,
                "behavioral": 25
            }
        }
        
        # Get focus areas for the selected interview type (default to technical)
        focus_areas = interview_type_focus_areas.get(interview_type.lower(), interview_type_focus_areas["technical"])
        
        # Create interview config with correct focus areas based on interview type
        interview_config = {
            "difficulty_level": job_description.get("difficulty_level", "medium"),
            "interview_type": interview_type,
            "focus_areas": focus_areas,
            "question_count": 8
        }
        
        # Generate questions based on JD and resume
        questions = await question_engine.generate_questions(
            job_description=job_description,
            resume_data=candidate_resume,
            interview_config=interview_config
        )
        
        # Get scoring configuration from database
        scoring_config = await scoring_config_service.get_config_by_level(scoring_level)
        if not scoring_config:
            print(f"⚠️ Scoring config not found for level '{scoring_level}', using default")
            scoring_config = await scoring_config_service.get_default_config()
        
        return {
            "interview_id": interview_id,
            "questions": questions,
            "scoring_config": scoring_config,  # Full DB-based scoring config
            "candidate_info": {
                "name": candidate_resume.get("personal_info", {}).get("name", "Unknown"),
                "email": candidate_resume.get("personal_info", {}).get("email", "N/A"),
                "experience_years": candidate_resume.get("experience", {}).get("total_years", 0),
                "current_role": candidate_resume.get("experience", {}).get("current_role", "Unknown"),
                "skills_match": 85  # Can be calculated from skills comparison
            },
            "job_description": job_description,
            "resume_data": candidate_resume
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get interview config: {str(e)}")

# ============================================================================
# SCORING CONFIGURATION API ENDPOINTS
# ============================================================================

@app.get("/api/v1/scoring-configs")
async def get_scoring_configs():
    """Get all active scoring configurations"""
    try:
        configs = await scoring_config_service.get_all_configs()
        return {
            "success": True,
            "count": len(configs),
            "configs": configs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scoring configs: {str(e)}")

@app.get("/api/v1/scoring-configs/default")
async def get_default_scoring_config():
    """Get the default scoring configuration"""
    try:
        config = await scoring_config_service.get_default_config()
        if config:
            return {
                "success": True,
                "config": config
            }
        else:
            raise HTTPException(status_code=404, detail="No default scoring config found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get default config: {str(e)}")

@app.get("/api/v1/scoring-configs/level/{level}")
async def get_scoring_config_by_level(level: str):
    """Get scoring configuration by level (easy/intermediate/strict)"""
    try:
        if level not in ["easy", "intermediate", "strict"]:
            raise HTTPException(status_code=400, detail="Level must be: easy, intermediate, or strict")
        
        config = await scoring_config_service.get_config_by_level(level)
        if config:
            return {
                "success": True,
                "config": config
            }
        else:
            raise HTTPException(status_code=404, detail=f"No config found for level: {level}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@app.get("/api/v1/scoring-configs/{config_id}")
async def get_scoring_config_by_id(config_id: str):
    """Get scoring configuration by ID"""
    try:
        config = await scoring_config_service.get_config_by_id(config_id)
        if config:
            return {
                "success": True,
                "config": config
            }
        else:
            raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@app.put("/api/v1/scoring-configs/{config_id}")
async def update_scoring_config(config_id: str, updates: Dict[str, Any]):
    """Update a scoring configuration"""
    try:
        success = await scoring_config_service.update_config(config_id, updates)
        if success:
            return {
                "success": True,
                "message": f"Config {config_id} updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Config not found or no changes made: {config_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")

@app.post("/api/v1/scoring-configs")
async def create_scoring_config(config_data: Dict[str, Any]):
    """Create a new custom scoring configuration"""
    try:
        config_id = await scoring_config_service.create_custom_config(config_data)
        if config_id:
            return {
                "success": True,
                "config_id": config_id,
                "message": "Config created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create config")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create config: {str(e)}")

# ============================================================================
# NOTE: Bot management API endpoints moved to routers/bots.py (Sprint 1.4)
# Now accessible under /api/v1/bots/*
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,  # Changed to 8009 to avoid conflict
        reload=False,  # Disable reload to prevent issues
        log_level="info"
    )
