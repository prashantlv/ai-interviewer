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
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime
from typing import Optional, Dict, Any
import pytz

# Import our modules
from routers import interviews, dashboard, feedback, bots, tavus, voices, scoring_settings, proctoring, admin, integrations
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

# Add CORS middleware for cross-origin requests from human2intelligence.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://human2intelligence.com",
        "https://www.human2intelligence.com",
        "http://localhost:3000",  # For local development
        "http://localhost:3001",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates (shared across all routers)
# Disable caching for development to ensure template changes are reflected immediately
templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True
templates.env.cache = None  # Completely disable cache

# Add custom Jinja2 filter for IST date formatting
def format_ist_datetime(dt, format_str='%Y-%m-%d %I:%M %p IST'):
    """Format datetime in IST timezone"""
    if not dt:
        return 'N/A'
    
    # If already formatted with IST, return as-is
    if isinstance(dt, str) and 'IST' in dt and ('PM' in dt or 'AM' in dt or ':' in dt):
        return dt
    
    try:
        IST = pytz.timezone('Asia/Kolkata')
        if isinstance(dt, str):
            # Check if it's already a formatted date (not ISO)
            if 'IST' in dt and ('PM' in dt or 'AM' in dt):
                return dt
            # Parse ISO format string
            dt_str = dt.replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_str)
        # Ensure dt is a datetime object
        if not isinstance(dt, datetime):
            return str(dt)
        if dt.tzinfo is None:
            # Assume UTC if timezone-naive
            dt = dt.replace(tzinfo=pytz.UTC)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime(format_str)
    except Exception as e:
        # Return original value if formatting fails
        return str(dt) if dt else 'N/A'

def format_ist_time_only(dt):
    """Format datetime to show only time in IST"""
    if not dt:
        return 'N/A'
    try:
        IST = pytz.timezone('Asia/Kolkata')
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        ist_dt = dt.astimezone(IST)
        return ist_dt.strftime('%I:%M %p IST')
    except Exception as e:
        # Fallback: try to extract time from string
        if isinstance(dt, str) and len(dt) >= 19:
            return dt[11:19] + ' IST'
        return str(dt)

templates.env.filters['ist_datetime'] = format_ist_datetime
templates.env.filters['ist_time'] = format_ist_time_only

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
app.include_router(integrations.router, tags=["integrations"])

# Admin routes
# Login: /admin/login
# Dashboard: /admin/dashboard
# API: /api/v1/admin/*
app.include_router(admin.router, tags=["admin"])

@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    """Handle authentication errors.

    - API/JSON clients: return JSON 401
    - Dashboard/HTML requests: return an on-page 401 debug view (no redirect) to help frontend debug headers/cookies
    """
    if exc.status_code == 401:
        accept = (request.headers.get("accept") or "").lower()
        is_api = request.url.path.startswith("/api/") or request.url.path.startswith("/api/v1/")

        # For API requests (or JSON clients), return JSON error
        if is_api or "application/json" in accept:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

        # For admin routes, redirect to admin login
        is_admin = request.url.path.startswith("/admin/")
        if is_admin:
            return RedirectResponse(
                url="/admin/login",
                status_code=302
            )

        # For dashboard/HTML requests, redirect to agency signin page
        return RedirectResponse(
            url="https://human2intelligence.com/signin/agency",
            status_code=302
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/sso/login")
async def sso_login(request: Request, token: Optional[str] = None):
    """SSO login endpoint - receives JWT from Hire2Inspire and sets cookie."""
    from services.auth_service import auth_service
    
    if not token:
        return HTMLResponse(
            status_code=400,
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>SSO Login - Missing Token</title></head>
            <body style="font-family: system-ui; padding: 40px; background: #f8f9fa;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc3545; margin: 0 0 16px;">❌ SSO Login Failed</h1>
                    <p style="color: #666; line-height: 1.6;">No authentication token provided in the URL.</p>
                    <p style="color: #666; line-height: 1.6;">
                        This endpoint expects: <code style="background: #f1f3f5; padding: 2px 6px; border-radius: 4px;">/sso/login?token=YOUR_JWT</code>
                    </p>
                    <a href="https://human2intelligence.com/login" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #FF6183; color: white; text-decoration: none; border-radius: 6px;">
                        ← Back to Login
                    </a>
                </div>
            </body>
            </html>
            """
        )
    
    try:
        # Verify token using auth_service
        user_data = auth_service.verify_access_token(token)
        user_id = user_data.get("userId")
        data_model = user_data.get("dataModel", "employers")
        
        # Create redirect response to dashboard
        response = RedirectResponse(url="/dashboard", status_code=302)
        
        # Set secure cookie on .human2intelligence.com domain
        # This cookie will be sent to api.human2intelligence.com automatically
        response.set_cookie(
            key="accessToken",
            value=token,
            httponly=True,
            secure=True,
            samesite="none",
            domain=".human2intelligence.com",
            max_age=7 * 24 * 60 * 60,
            path="/"
        )
        
        print(f"✅ SSO Login successful - User: {user_id} ({data_model})")
        return response
        
    except HTTPException as e:
        return HTMLResponse(
            status_code=401,
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>SSO Login - Invalid Token</title></head>
            <body style="font-family: system-ui; padding: 40px; background: #f8f9fa;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc3545; margin: 0 0 16px;">❌ SSO Login Failed</h1>
                    <p style="color: #666; line-height: 1.6;"><strong>Error:</strong> {e.detail}</p>
                    <p style="color: #666; line-height: 1.6;">
                        The authentication token provided is invalid or has expired. Please log in again.
                    </p>
                    <a href="https://human2intelligence.com/login" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #FF6183; color: white; text-decoration: none; border-radius: 6px;">
                        ← Back to Login
                    </a>
                </div>
            </body>
            </html>
            """
        )
    except Exception as e:
        return HTMLResponse(
            status_code=500,
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>SSO Login - Error</title></head>
            <body style="font-family: system-ui; padding: 40px; background: #f8f9fa;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc3545; margin: 0 0 16px;">⚠️ SSO Login Error</h1>
                    <p style="color: #666; line-height: 1.6;">An unexpected error occurred during authentication.</p>
                    <p style="color: #999; font-size: 14px; font-family: monospace; background: #f8f9fa; padding: 12px; border-radius: 4px; margin-top: 16px;">
                        {str(e)}
                    </p>
                    <a href="https://human2intelligence.com/login" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #FF6183; color: white; text-decoration: none; border-radius: 6px;">
                        ← Back to Login
                    </a>
                </div>
            </body>
            </html>
            """
        )

@app.get("/logout")
async def logout(request: Request):
    """
    Logout endpoint - clears authentication cookie and redirects to login page.
    Also attempts to invalidate token on hire2inspire backend.
    """
    from services.auth_service import auth_service
    import httpx
    
    # Extract token from request (cookie or header)
    token = auth_service.extract_token_from_request(request)
    
    # If token exists, try to call hire2inspire logout API
    if token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "https://pro.hire2inspire.com/api/agency/logout",
                    headers={"Authorization": f"Bearer {token}"}
                )
                print(f"✅ Logout API called - Status: {response.status_code}")
        except Exception as e:
            # Don't fail logout if API call fails
            print(f"⚠️ Logout API call failed (non-critical): {e}")
    
    # Create redirect response to signin page
    response = RedirectResponse(
        url="https://human2intelligence.com/signin/agency",
        status_code=302
    )
    
    # Clear the accessToken cookie
    response.delete_cookie(
        key="accessToken",
        domain=".human2intelligence.com",
        path="/"
    )
    
    print(f"✅ User logged out successfully")
    return response

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
        
        # Get OpenAI API key (use env fallback for bot endpoints)
        # Note: This endpoint is called by bots, not users, so we use env fallback
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Generate questions based on JD and resume
        questions = await question_engine.generate_questions(
            job_description=job_description,
            resume_data=candidate_resume,
            interview_config=interview_config,
            api_key=openai_api_key
        )
        
        # Get scoring configuration from database
        scoring_config = await scoring_config_service.get_config_by_level(scoring_level)
        if not scoring_config:
            print(f"⚠️ Scoring config not found for level '{scoring_level}', using default")
            scoring_config = await scoring_config_service.get_default_config()
        
        # Get replica_id from interview if specified (for per-interview replica selection)
        # Priority: 1) Interview-specific replica_id, 2) User's default_replica_id from config, 3) None
        replica_id = None
        user_id = None
        
        if interview:
            # Get user_id from interview if available
            user_id = interview.get("user_id") or interview.get("userId")
            
            # Check for interview-specific replica_id first
            if interview.get("evaluation"):
                replica_id = interview.get("evaluation", {}).get("replica_id")
            
            # If no interview-specific replica, check user's config
            if not replica_id and user_id:
                tavus_config = await db_service.get_user_integration_config(user_id, "tavus")
                if tavus_config and tavus_config.get("default_replica_id"):
                    replica_id = tavus_config.get("default_replica_id")
                    print(f"✅ Using user's default replica from config: {replica_id}")
        
        return {
            "interview_id": interview_id,
            "questions": questions,
            "scoring_config": scoring_config,  # Full DB-based scoring config
            "replica_id": replica_id,  # Optional: allows per-interview replica selection
            "user_id": user_id,  # Include user_id so bot can use it for replica-config
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

@app.get("/api/v1/bot/replica-config")
async def get_replica_config(
    replica_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """
    Get replica-voice configuration for bot.
    
    Priority order:
    1. User's config from user_integrations (if user_id provided)
    2. Specific replica mapping from replica_voice_mappings (if replica_id provided)
    3. Default replica mapping from replica_voice_mappings
    4. Environment variables
    
    If replica_id is provided, returns config for that replica (auto-cloning voice if needed).
    Otherwise, returns the default replica config.
    
    Falls back to environment variables only if no replica_id specified and no default exists.
    """
    try:
        config = None
        target_replica_id = replica_id
        
        # Priority 1: Check user's config from user_integrations if user_id provided
        if user_id:
            tavus_config = await db_service.get_user_integration_config(user_id, "tavus")
            cartesia_config = await db_service.get_user_integration_config(user_id, "cartesia")
            
            if tavus_config and tavus_config.get("default_replica_id"):
                user_replica_id = tavus_config.get("default_replica_id")
                # Use user's default replica if no specific replica requested
                if not replica_id:
                    target_replica_id = user_replica_id
                    replica_id = user_replica_id
                    print(f"✅ Using user's default replica from config: {user_replica_id}")
                
                # Get voice from user's cartesia config or fallback
                user_voice_id = None
                if cartesia_config:
                    user_voice_id = cartesia_config.get("default_voice_id")
                
                if user_voice_id:
                    config = {
                        "replica_id": target_replica_id or user_replica_id,
                        "voice_id": user_voice_id,
                        "is_default": True,
                        "source": "user_config"
                    }
                    print(f"✅ Using user's config: replica={config['replica_id']}, voice={user_voice_id}")
        
        # Priority 2: Specific replica requested - try to get its mapping
        if replica_id and not config:
            config = await db_service.get_replica_config(replica_id)
            
            # If no mapping exists for this replica, auto-clone its voice
            if not config:
                print(f"🔄 No mapping for replica {replica_id}, will auto-clone voice")
                cloned_voice_id = await _auto_clone_voice_for_replica(replica_id)
                
                if cloned_voice_id:
                    print(f"✅ Voice auto-cloned for {replica_id}: {cloned_voice_id}")
                    config = {
                        "replica_id": replica_id,
                        "voice_id": cloned_voice_id,
                        "is_default": False,
                        "source": "auto-cloned"
                    }
                else:
                    # Use fallback voice but still use the requested replica
                    # Check user's cartesia config first
                    fallback_voice = None
                    if user_id:
                        cartesia_config = await db_service.get_user_integration_config(user_id, "cartesia")
                        if cartesia_config:
                            fallback_voice = cartesia_config.get("default_voice_id")
                    
                    if not fallback_voice:
                        fallback_voice = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")
                    
                    print(f"⚠️ Auto-clone failed for {replica_id}, using fallback voice: {fallback_voice}")
                    config = {
                        "replica_id": replica_id,
                        "voice_id": fallback_voice,
                        "is_default": False,
                        "source": "fallback"
                    }
        
        # Priority 3: No specific replica - get default config from replica_voice_mappings
        if not config and not replica_id:
            config = await db_service.get_default_replica_config()
            if config:
                target_replica_id = config.get("replica_id")
        
        # Handle auto-clone marker for existing mappings
        if config and config.get("voice_id") == "auto-clone" and target_replica_id:
            print(f"🔄 Voice needs auto-cloning for replica: {target_replica_id}")
            cloned_voice_id = await _auto_clone_voice_for_replica(target_replica_id)
            if cloned_voice_id:
                config["voice_id"] = cloned_voice_id
                print(f"✅ Auto-cloned voice: {cloned_voice_id}")
            else:
                # Fallback to user's cartesia config or env var
                fallback = None
                if user_id:
                    cartesia_config = await db_service.get_user_integration_config(user_id, "cartesia")
                    if cartesia_config:
                        fallback = cartesia_config.get("default_voice_id")
                
                if not fallback:
                    fallback = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")
                
                config["voice_id"] = fallback
                print(f"⚠️ Auto-clone failed, using fallback: {fallback}")
        
        # Priority 4: Fallback to environment variables ONLY if no replica specified and no default
        if not config:
            replica_id_env = os.getenv("TAVUS_REPLICA_ID")
            voice_id_env = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")
            
            if replica_id_env:
                config = {
                    "replica_id": replica_id_env,
                    "voice_id": voice_id_env,
                    "is_default": True,
                    "source": "environment"
                }
        
        if config:
            return {
                "replica_id": config.get("replica_id"),
                "voice_id": config.get("voice_id"),
                "is_default": config.get("is_default", False),
                "source": config.get("source", "database")
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="No replica configuration found. Please configure a default replica."
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting replica config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get replica config: {str(e)}")


async def _auto_clone_voice_for_replica(replica_id: str) -> Optional[str]:
    """
    Auto-clone a voice from the replica's thumbnail video.
    Returns the cloned voice_id if successful, None otherwise.
    """
    try:
        from services.tavus_service import TavusService
        from services.voice_cloning_service import VoiceCloningService
        import httpx
        import tempfile
        import subprocess
        
        tavus = TavusService()
        voice_service = VoiceCloningService()
        
        # Get replica details
        replica = await tavus.get_replica(replica_id, verbose=True)
        if not replica:
            print(f"❌ Replica not found: {replica_id}")
            return None
        
        replica_name = replica.get("replica_name", "Unknown")
        video_url = replica.get("thumbnail_video_url")
        
        if not video_url:
            print(f"❌ No video URL for replica: {replica_id}")
            return None
        
        print(f"🎬 Downloading video for voice clone: {video_url[:50]}...")
        
        # Download video
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(video_url)
            if response.status_code != 200:
                print(f"❌ Failed to download video: {response.status_code}")
                return None
            video_data = response.content
        
        # Extract audio with ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vf:
            vf.write(video_data)
            video_path = vf.name
        
        audio_path = video_path.replace(".mp4", ".wav")
        
        try:
            result = subprocess.run([
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1",
                "-t", "10", "-y", audio_path
            ], capture_output=True, timeout=30)
            
            if result.returncode != 0:
                print(f"❌ FFmpeg error: {result.stderr.decode()[:200]}")
                return None
            
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            # Clone voice
            voice_name = f"{replica_name} Voice (Auto)"
            clone_result = await voice_service.clone_voice(
                audio_data=audio_data,
                voice_name=voice_name,
                language="en",
                mode="similarity"
            )
            
            cloned_voice_id = clone_result.get("voice_id")
            
            if cloned_voice_id:
                # Update mapping with real voice_id
                await db_service.create_replica_mapping(
                    replica_id=replica_id,
                    voice_id=cloned_voice_id,
                    name=voice_name,
                    description=f"Auto-cloned from {replica_name}",
                    is_default=True
                )
                print(f"✅ Voice cloned: {cloned_voice_id}")
                return cloned_voice_id
                
        finally:
            import os as _os
            try:
                _os.unlink(video_path)
                _os.unlink(audio_path)
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"❌ Auto-clone failed: {e}")
        import traceback
        traceback.print_exc()
        return None

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
