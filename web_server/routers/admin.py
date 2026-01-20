"""
Admin Router - Admin panel for replica approval and management
"""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pydantic import BaseModel
from services.admin_auth_service import admin_auth_service
from services.database import db_service
from services.tavus_service import tavus_service
from services.hire2inspire_service import hire2inspire_service
from dependencies import DbServiceDep, AdminUserDep
from loguru import logger
from datetime import datetime
import pytz

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Register IST datetime filters (same as in main.py)
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
        if not isinstance(dt, datetime):
            return str(dt)
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


# ============================================================================
# Pydantic Models
# ============================================================================

class RejectRequestModel(BaseModel):
    reason: Optional[str] = None


# ============================================================================
# Authentication Routes
# ============================================================================

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    # Check if already logged in
    admin_username = request.cookies.get("admin_session")
    if admin_username:
        admin = await db_service.get_admin_user(admin_username)
        if admin:
            return RedirectResponse(url="/admin/dashboard", status_code=302)
    
    return templates.TemplateResponse("admin_login.html", {
        "request": request
    })


@router.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Admin login endpoint"""
    try:
        logger.info(f"🔐 Admin login attempt for username: {username}")
        # Use db_service from app state (connected instance)
        db = request.app.state.db_service
        
        # Pass the connected db_service to authenticate_admin
        admin = await admin_auth_service.authenticate_admin(username, password, db_service_instance=db)
        
        if not admin:
            logger.warning(f"❌ Admin login failed for username: {username}")
            return templates.TemplateResponse("admin_login.html", {
                "request": request,
                "error": "Invalid username or password"
            })
        
        logger.info(f"✅ Admin login successful for username: {username}")
        
        # Create response with redirect
        response = RedirectResponse(url="/admin/dashboard", status_code=302)
        # Set admin session cookie
        response.set_cookie(
            key="admin_session",
            value=username,
            max_age=86400,  # 24 hours
            httponly=True,
            samesite="lax"
        )
        return response
    except Exception as e:
        logger.error(f"❌ Error in admin login: {str(e)}")
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": f"Login failed: {str(e)}"
        })


@router.get("/admin/logout")
async def admin_logout():
    """Admin logout endpoint"""
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(key="admin_session")
    return response


# ============================================================================
# Dashboard Routes
# ============================================================================

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin: AdminUserDep,
    db: DbServiceDep
):
    """Admin dashboard page"""
    try:
        # Get replica requests
        pending_requests = await db.list_replica_requests(status="pending")
        approved_requests = await db.list_replica_requests(status="approved")
        rejected_requests = await db.list_replica_requests(status="rejected")
        training_requests = await db.list_replica_requests(status="training")
        completed_requests = await db.list_replica_requests(status="completed")
        
        # Get all requests for stats
        all_requests = await db.list_replica_requests(limit=1000)
        
        stats = {
            "total": len(all_requests),
            "pending": len(pending_requests),
            "approved": len(approved_requests),
            "rejected": len(rejected_requests),
            "training": len(training_requests),
            "completed": len(completed_requests)
        }
        
        # Get agencies list
        agencies = []
        try:
            agencies = await hire2inspire_service.get_agency_list(user_type="agencies")
            logger.info(f"📊 Loaded {len(agencies)} agencies for admin dashboard")
            if len(agencies) == 0:
                logger.warning("⚠️ No agencies returned from API - check logs for details")
        except Exception as e:
            logger.error(f"❌ Failed to fetch agencies: {e}", exc_info=True)
            agencies = []
        
        # Get employers list
        employers = []
        try:
            employers = await hire2inspire_service.get_agency_list(user_type="employers")
            logger.info(f"📊 Loaded {len(employers)} employers for admin dashboard")
            if len(employers) == 0:
                logger.warning("⚠️ No employers returned from API - check logs for details")
        except Exception as e:
            logger.error(f"❌ Failed to fetch employers: {e}", exc_info=True)
            employers = []
        
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "admin_username": admin.get("username"),
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "training_requests": training_requests,
            "completed_requests": completed_requests,
            "stats": stats,
            "agencies": agencies,
            "employers": employers
        })
    except Exception as e:
        logger.error(f"❌ Error loading admin dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Routes - Replica Requests
# ============================================================================

@router.get("/api/v1/admin/replica-requests")
async def list_replica_requests(
    admin: AdminUserDep,
    db: DbServiceDep,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all replica requests"""
    try:
        requests = await db.list_replica_requests(
            status=status,
            limit=limit,
            offset=offset
        )
        return JSONResponse({
            "success": True,
            "data": requests,
            "count": len(requests)
        })
    except Exception as e:
        logger.error(f"❌ Error listing replica requests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/admin/agencies/{agency_id}")
async def get_agency_details(
    agency_id: str,
    admin: AdminUserDep
):
    """Get details of a specific agency"""
    try:
        agency = await hire2inspire_service.get_agency_details(agency_id)
        if agency:
            # Explicitly verify subscription is in the response before returning
            if isinstance(agency, dict):
                logger.info(f"📤 Admin route: Agency has {len(agency)} keys")
                if 'subscription' in agency:
                    logger.info(f"✅ Admin route: Subscription confirmed in agency dict")
                    logger.info(f"✅ Admin route: Subscription type: {type(agency['subscription'])}, is array: {isinstance(agency['subscription'], list)}")
                else:
                    logger.error(f"❌ Admin route: Subscription MISSING from agency dict!")
                    logger.error(f"❌ Admin route: Available keys: {list(agency.keys())[:20]}")
            
            response_data = {
                "success": True,
                "data": agency
            }
            
            # Double-check subscription in response
            if isinstance(agency, dict) and 'subscription' not in agency:
                logger.error(f"❌ Admin route: Subscription will NOT be in JSON response!")
            else:
                logger.info(f"✅ Admin route: Subscription WILL be in JSON response")
            
            return JSONResponse(response_data)
        else:
            raise HTTPException(status_code=404, detail="Agency not found")
    except Exception as e:
        logger.error(f"❌ Error getting agency details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/admin/agencies/{agency_id}/interview-insights")
async def get_agency_interview_insights(
    agency_id: str,
    admin: AdminUserDep,
    db: DbServiceDep
):
    """Get interview insights/metrics for a specific agency"""
    try:
        # Get agency details to extract corporate_email for filtering
        agency = await hire2inspire_service.get_agency_details(agency_id)
        if not agency:
            raise HTTPException(status_code=404, detail="Agency not found")
        
        # For now, get all interviews (since interviews don't have agency_id)
        # TODO: In future, filter by agency_email or add agency_id to interviews
        all_interviews = await db.get_interviews()
        
        # Calculate metrics similar to analytics page
        total_interviews = len(all_interviews)
        completed_interviews = [i for i in all_interviews if i.get("status") in ["completed", "ended_by_candidate"]]
        completed_count = len(completed_interviews)
        
        # Average score
        scored_interviews = [i for i in completed_interviews if i.get("score", 0) > 0]
        avg_score = round(sum(i.get("score", 0) for i in scored_interviews) / len(scored_interviews), 1) if scored_interviews else 0
        
        # Hire rate (score >= 65)
        recommended_count = len([i for i in completed_interviews if i.get("score", 0) >= 65])
        hire_rate = round((recommended_count / completed_count * 100), 1) if completed_count > 0 else 0
        
        # Completion rate
        completion_rate = round((completed_count / total_interviews * 100), 1) if total_interviews > 0 else 0
        
        # Growth rate (placeholder - could calculate from date range)
        growth_rate = 0.0  # TODO: Calculate actual growth rate
        
        insights = {
            "total_interviews": total_interviews,
            "avg_score": avg_score,
            "hire_rate": hire_rate,
            "completion_rate": completion_rate,
            "recommended_count": recommended_count,
            "completed_count": completed_count,
            "growth_rate": growth_rate
        }
        
        return JSONResponse({
            "success": True,
            "data": insights
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting agency interview insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/admin/replica-requests/{request_id}")
async def get_replica_request(
    request_id: str,
    admin: AdminUserDep,
    db: DbServiceDep
):
    """Get a specific replica request"""
    try:
        request_data = await db.get_replica_request(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Replica request not found")
        
        return JSONResponse({
            "success": True,
            "data": request_data
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting replica request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/v1/admin/replica-requests/{request_id}/approve")
async def approve_replica_request(
    request_id: str,
    admin: AdminUserDep,
    db: DbServiceDep
):
    """Approve a replica request"""
    try:
        # Get request first
        request_data = await db.get_replica_request(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Replica request not found")
        
        if request_data.get("status") != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve request with status: {request_data.get('status')}"
            )
        
        # Approve the request
        success = await db.approve_replica_request(
            request_id=request_id,
            admin_username=admin.get("username")
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to approve request")
        
        return JSONResponse({
            "success": True,
            "message": "Replica request approved"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error approving replica request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/v1/admin/replica-requests/{request_id}/reject")
async def reject_replica_request(
    request_id: str,
    request_body: RejectRequestModel,
    admin: AdminUserDep,
    db: DbServiceDep
):
    """Reject a replica request"""
    try:
        # Get request first
        request_data = await db.get_replica_request(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Replica request not found")
        
        if request_data.get("status") != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject request with status: {request_data.get('status')}"
            )
        
        # Reject the request
        success = await db.reject_replica_request(
            request_id=request_id,
            admin_username=admin.get("username"),
            reason=request_body.reason
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reject request")
        
        return JSONResponse({
            "success": True,
            "message": "Replica request rejected"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error rejecting replica request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/admin/replica-requests/{request_id}/train")
async def train_replica_request(
    request_id: str,
    admin: AdminUserDep,
    db: DbServiceDep
):
    """Start training for an approved replica request"""
    try:
        # Get request first
        request_data = await db.get_replica_request(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Replica request not found")
        
        if request_data.get("status") != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot train request with status: {request_data.get('status')}. Request must be approved first."
            )
        
        # Call Tavus API to create replica
        logger.info(f"🎬 Starting training for replica request: {request_id}")
        tavus_result = await tavus_service.create_replica(
            train_video_url=request_data.get("train_video_url"),
            replica_name=request_data.get("replica_name"),
            consent_video_url=request_data.get("consent_video_url"),
            callback_url=None,  # Optional: can add webhook URL later
            model_name=request_data.get("model_name", "phoenix-3")
        )
        
        if not tavus_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to start training with Tavus API"
            )
        
        tavus_replica_id = tavus_result.get("replica_id")
        
        # Update request status to training
        success = await db.start_replica_training(
            request_id=request_id,
            tavus_replica_id=tavus_replica_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update request status")
        
        return JSONResponse({
            "success": True,
            "message": "Training started successfully",
            "data": {
                "tavus_replica_id": tavus_replica_id,
                "status": tavus_result.get("status")
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error training replica request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
