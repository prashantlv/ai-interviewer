"""
Tavus Replica Management Router

Provides REST API endpoints for managing Tavus replicas (create, read, list, update, delete).
"""

from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pydantic import BaseModel
from services.tavus_service import tavus_service
from loguru import logger

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ============================================================================
# Pydantic Models for Request Validation
# ============================================================================

class CreateReplicaRequest(BaseModel):
    """Request model for creating a replica"""
    train_video_url: str
    replica_name: str
    consent_video_url: Optional[str] = None
    callback_url: Optional[str] = None
    model_name: str = "phoenix-3"


class RenameReplicaRequest(BaseModel):
    """Request model for renaming a replica"""
    replica_name: str


# ============================================================================
# Dashboard Page Endpoints
# ============================================================================

@router.get("/dashboard/replicas", response_class=HTMLResponse)
async def replicas_page(request: Request, page: int = 1, limit: int = 20, replica_type: str = "stock"):
    """
    Replica Management dashboard page
    
    Displays UI for managing avatar replicas (list, create, rename, delete)
    Supports pagination with page and limit query parameters.
    
    Args:
        replica_type: Filter by 'user' (personal), 'stock' (system), or None (all)
    """
    try:
        # Map 'stock' to 'system' for Tavus API
        api_replica_type = None
        if replica_type == 'stock':
            api_replica_type = 'system'
        elif replica_type == 'user':
            api_replica_type = 'user'
        
        # Fetch replicas with pagination and optional type filter
        result = await tavus_service.list_replicas(
            verbose=True, 
            limit=limit, 
            page=page,
            replica_type=api_replica_type
        )
        
        replicas = []
        total_count = 0
        
        if result:
            replicas = result.get('data', [])
            total_count = result.get('total_count', 0)
        
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        return templates.TemplateResponse(
            "tavus_replicas.html",
            {
                "request": request,
                "replicas": replicas,
                "total_count": total_count,
                "page_title": "Replicas",
                "current_page": page,
                "limit": limit,
                "total_pages": total_pages,
                "replica_type": replica_type or "all"
            }
        )
    except Exception as e:
        logger.error(f"❌ Error loading Tavus replicas page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints - Replica Management
# ============================================================================

@router.post("/api/v1/tavus/replicas")
async def create_replica(request: CreateReplicaRequest):
    """
    Create a new Tavus replica
    
    Request Body:
        - train_video_url: Public URL to training video (required)
        - replica_name: Name for the replica (required)
        - consent_video_url: Public URL to consent video (optional, required for personal replicas)
        - callback_url: Webhook URL for training completion (optional)
        - model_name: Phoenix model version (default: phoenix-3)
    
    Returns:
        - replica_id: Unique identifier for the created replica
        - status: Training status (started, completed, error)
    """
    try:
        result = await tavus_service.create_replica(
            train_video_url=request.train_video_url,
            replica_name=request.replica_name,
            consent_video_url=request.consent_video_url,
            callback_url=request.callback_url,
            model_name=request.model_name
        )
        
        if result:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": result
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create replica. Check logs for details."
            )
    except Exception as e:
        logger.error(f"❌ Error in create_replica endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tavus/replicas/{replica_id}")
async def get_replica(replica_id: str, verbose: bool = True):
    """
    Get a single Tavus replica by ID
    
    Path Parameters:
        - replica_id: Unique identifier for the replica
    
    Query Parameters:
        - verbose: Include additional data like replica_type (default: true)
    
    Returns:
        Replica details including:
        - replica_id, replica_name, status, training_progress
        - thumbnail_video_url, created_at, updated_at
        - error_message (if status is error)
        - replica_type (if verbose=true)
    """
    try:
        result = await tavus_service.get_replica(replica_id, verbose=verbose)
        
        if result:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": result
                }
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Replica not found: {replica_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in get_replica endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tavus/replicas")
async def list_replicas(
    limit: Optional[int] = None,
    page: Optional[int] = None,
    verbose: bool = True,
    replica_type: Optional[str] = None,
    replica_ids: Optional[str] = None
):
    """
    List all Tavus replicas
    
    Query Parameters:
        - limit: Number of replicas per page
        - page: Page number
        - verbose: Include additional data like replica_type (default: true)
        - replica_type: Filter by type ('user' or 'system')
        - replica_ids: Comma-separated list of replica IDs to filter
    
    Returns:
        - data: List of replica objects
        - total_count: Total number of replicas
    """
    try:
        result = await tavus_service.list_replicas(
            limit=limit,
            page=page,
            verbose=verbose,
            replica_type=replica_type,
            replica_ids=replica_ids
        )
        
        if result:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": result.get('data', []),
                    "total_count": result.get('total_count', 0)
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to list replicas. Check logs for details."
            )
    except Exception as e:
        logger.error(f"❌ Error in list_replicas endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/v1/tavus/replicas/{replica_id}")
async def rename_replica(replica_id: str, request: RenameReplicaRequest):
    """
    Rename a Tavus replica
    
    Path Parameters:
        - replica_id: Unique identifier for the replica
    
    Request Body:
        - replica_name: New name for the replica
    
    Returns:
        - success: True if renamed successfully
    """
    try:
        success = await tavus_service.rename_replica(
            replica_id=replica_id,
            new_name=request.replica_name
        )
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Replica {replica_id} renamed successfully"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to rename replica. Check logs for details."
            )
    except Exception as e:
        logger.error(f"❌ Error in rename_replica endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/tavus/replicas/{replica_id}")
async def delete_replica(replica_id: str, hard: bool = False):
    """
    Delete a Tavus replica
    
    Path Parameters:
        - replica_id: Unique identifier for the replica
    
    Query Parameters:
        - hard: If true, permanently delete replica and training footage (default: false)
                CAUTION: This action is irreversible!
    
    Returns:
        - success: True if deleted successfully
    """
    try:
        success = await tavus_service.delete_replica(
            replica_id=replica_id,
            hard_delete=hard
        )
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Replica {replica_id} deleted successfully"
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete replica. Check logs for details."
            )
    except Exception as e:
        logger.error(f"❌ Error in delete_replica endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tavus/health")
async def tavus_health_check():
    """
    Check Tavus API health
    
    Returns:
        - status: healthy/unhealthy
        - api_key_valid: True if API key is valid
        - total_replicas: Number of replicas (if healthy)
        - error: Error message (if unhealthy)
    """
    try:
        result = await tavus_service.health_check()
        return JSONResponse(
            status_code=200 if result.get('status') == 'healthy' else 500,
            content=result
        )
    except Exception as e:
        logger.error(f"❌ Error in tavus_health_check endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

