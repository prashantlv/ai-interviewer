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
from dependencies import DbServiceDep, AdminUserDep
from loguru import logger
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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
    admin: AdminUserDep
):
    """Admin dashboard page"""
    try:
        # Get replica requests
        pending_requests = await db_service.list_replica_requests(status="pending")
        approved_requests = await db_service.list_replica_requests(status="approved")
        rejected_requests = await db_service.list_replica_requests(status="rejected")
        training_requests = await db_service.list_replica_requests(status="training")
        completed_requests = await db_service.list_replica_requests(status="completed")
        
        # Get all requests for stats
        all_requests = await db_service.list_replica_requests(limit=1000)
        
        stats = {
            "total": len(all_requests),
            "pending": len(pending_requests),
            "approved": len(approved_requests),
            "rejected": len(rejected_requests),
            "training": len(training_requests),
            "completed": len(completed_requests)
        }
        
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "admin_username": admin.get("username"),
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "training_requests": training_requests,
            "completed_requests": completed_requests,
            "stats": stats
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
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List all replica requests"""
    try:
        requests = await db_service.list_replica_requests(
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


@router.get("/api/v1/admin/replica-requests/{request_id}")
async def get_replica_request(
    request_id: str,
    admin: AdminUserDep
):
    """Get a specific replica request"""
    try:
        request_data = await db_service.get_replica_request(request_id)
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
    admin: AdminUserDep
):
    """Approve a replica request"""
    try:
        # Get request first
        request_data = await db_service.get_replica_request(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Replica request not found")
        
        if request_data.get("status") != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve request with status: {request_data.get('status')}"
            )
        
        # Approve the request
        success = await db_service.approve_replica_request(
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
    admin: AdminUserDep
):
    """Reject a replica request"""
    try:
        # Get request first
        request_data = await db_service.get_replica_request(request_id)
        if not request_data:
            raise HTTPException(status_code=404, detail="Replica request not found")
        
        if request_data.get("status") != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject request with status: {request_data.get('status')}"
            )
        
        # Reject the request
        success = await db_service.reject_replica_request(
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
    admin: AdminUserDep
):
    """Start training for an approved replica request"""
    try:
        # Get request first
        request_data = await db_service.get_replica_request(request_id)
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
        success = await db_service.start_replica_training(
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
