"""
Tavus Replica Management Router

Provides REST API endpoints for managing Tavus replicas (create, read, list, update, delete).
"""

from fastapi import APIRouter, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from services.tavus_service import tavus_service
from services.voice_cloning_service import voice_cloning_service
from dependencies import DbServiceDep, CurrentUserDep, UserApiKeysDep
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
async def replicas_page(
    request: Request,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    page: int = 1,
    limit: int = 20,
    replica_type: str = "stock"
):
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
        tavus_api_key = api_keys.get("tavus")
        user_id = current_user.get("userId", "unknown")
        
        # Log which API key is being used (for debugging data isolation)
        logger.info("=" * 60)
        logger.info(f"🔍 DEBUG: Listing replicas for user: {user_id}")
        if tavus_api_key:
            key_preview = tavus_api_key[:6] + "..." + tavus_api_key[-4:] if len(tavus_api_key) > 10 else tavus_api_key
            logger.info(f"✅ User {user_id} using their OWN Tavus API key from DB: {key_preview}")
            logger.info(f"   Key length: {len(tavus_api_key)}")
        else:
            logger.error(f"❌ User {user_id} has NO Tavus API key configured in DB")
            logger.error(f"   User must configure their Tavus API key via /api/v1/user/integrations/tavus")
        logger.info("=" * 60)
        
        # Return error if no API key configured
        if not tavus_api_key:
            logger.error(f"❌ User {user_id} attempted to access replicas without Tavus API key")
            return templates.TemplateResponse(
                "tavus_replicas.html",
                {
                    "request": request,
                    "error": "Tavus API key not configured. Please configure your Tavus API key via Settings > Integrations.",
                    "replicas": [],
                    "total_count": 0,
                    "page": page,
                    "limit": limit,
                    "replica_type": replica_type
                }
            )
        
        result = await tavus_service.list_replicas(
            verbose=True, 
            limit=limit, 
            page=page,
            replica_type=api_replica_type,
            api_key=tavus_api_key
        )
        
        # Log how many replicas were returned
        if result:
            replicas_count = len(result.get('data', []))
            logger.info(f"📊 User {user_id} sees {replicas_count} replicas (total_count: {result.get('total_count', 0)})")
            # Log replica IDs to see if they match between users
            replica_ids = [r.get('replica_id') for r in result.get('data', [])[:5]]
            logger.info(f"   First 5 replica IDs: {replica_ids}")
        
        replicas = []
        total_count = 0
        
        if result:
            replicas = result.get('data', [])
            total_count = result.get('total_count', 0)
        
        # Fetch voice mappings from database and merge with replicas
        from dependencies import get_db_service
        try:
            db = get_db_service(request)
            voice_mappings = await db.list_replica_configs()
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch voice mappings: {e}")
            voice_mappings = []
        
        # Create a lookup dict: replica_id -> voice mapping
        mapping_lookup = {m.get("replica_id"): m for m in voice_mappings}
        default_replica_id = None
        for m in voice_mappings:
            if m.get("is_default"):
                default_replica_id = m.get("replica_id")
                break
        
        # Merge voice mapping data into replicas
        for replica in replicas:
            replica_id = replica.get("replica_id")
            mapping = mapping_lookup.get(replica_id)
            if mapping:
                replica["voice_id"] = mapping.get("voice_id")
                replica["voice_name"] = mapping.get("name", "Unknown Voice")
                replica["is_default"] = mapping.get("is_default", False)
            else:
                replica["voice_id"] = None
                replica["voice_name"] = "Not configured"
                replica["is_default"] = False
        
        # Sort replicas: default first, then by name
        replicas = sorted(replicas, key=lambda r: (not r.get("is_default", False), r.get("replica_name", "").lower()))
        
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
                "replica_type": replica_type or "all",
                "default_replica_id": default_replica_id
            }
        )
    except Exception as e:
        logger.error(f"❌ Error loading Tavus replicas page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Endpoints - Replica Management
# ============================================================================

@router.post("/api/v1/tavus/replicas")
async def create_replica(
    request: CreateReplicaRequest,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    db: DbServiceDep
):
    """
    Create a new replica request (pending admin approval)
    
    Request Body:
        - train_video_url: Public URL to training video (required)
        - replica_name: Name for the replica (required)
        - consent_video_url: Public URL to consent video (optional, required for personal replicas)
        - callback_url: Webhook URL for training completion (optional, ignored - stored for future use)
        - model_name: Phoenix model version (default: phoenix-3)
    
    Returns:
        - request_id: Unique identifier for the replica request
        - status: "pending" (awaiting admin approval)
        - message: Success message
    """
    try:
        # Get user ID and email from JWT token
        user_id = current_user.get("userId", "unknown")
        payload = current_user.get("payload", {})
        user_email = payload.get("email") or payload.get("userEmail") or None
        
        # Format submitted_by: use email if available, otherwise user_id
        submitted_by = user_email if user_email else user_id
        
        # Store replica request in database (pending approval)
        request_id = await db.create_replica_request(
            replica_name=request.replica_name,
            train_video_url=request.train_video_url,
            submitted_by=submitted_by,
            consent_video_url=request.consent_video_url,
            model_name=request.model_name
        )
        
        if not request_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create replica request. Please try again."
            )
        
        logger.info(f"✅ Replica request created: {request_id} by user {user_id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Replica request submitted successfully. Awaiting admin approval.",
                "data": {
                    "request_id": request_id,
                    "status": "pending",
                    "replica_name": request.replica_name
                }
            }
        )
    except HTTPException:
        raise
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
        result = await tavus_service.get_replica(replica_id, verbose=verbose, api_key=api_keys.get("tavus"))
        
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
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
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
        tavus_api_key = api_keys.get("tavus")
        user_id = current_user.get("userId", "unknown")
        
        # Log which API key is being used (for debugging data isolation)
        logger.info("=" * 60)
        logger.info(f"🔍 DEBUG: API list_replicas for user: {user_id}")
        if tavus_api_key:
            key_preview = tavus_api_key[:6] + "..." + tavus_api_key[-4:] if len(tavus_api_key) > 10 else tavus_api_key
            logger.info(f"✅ User {user_id} using their OWN Tavus API key from DB: {key_preview}")
        else:
            logger.error(f"❌ User {user_id} has NO Tavus API key configured in DB")
            logger.error(f"   User must configure their Tavus API key via /api/v1/user/integrations/tavus")
        logger.info("=" * 60)
        
        # Return error if no API key configured
        if not tavus_api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tavus API key not configured. Please configure your Tavus API key via /api/v1/user/integrations/tavus"
            )
        
        result = await tavus_service.list_replicas(
            limit=limit,
            page=page,
            verbose=verbose,
            replica_type=replica_type,
            replica_ids=replica_ids,
            api_key=tavus_api_key
        )
        
        # Log results
        if result:
            replicas_count = len(result.get('data', []))
            logger.info(f"📊 User {user_id} API call returned {replicas_count} replicas")
        
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
async def rename_replica(
    replica_id: str, 
    request: RenameReplicaRequest,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep
):
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
            new_name=request.replica_name,
            api_key=api_keys.get("tavus")
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
async def delete_replica(
    replica_id: str,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    hard: bool = False
):
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
            hard_delete=hard,
            api_key=api_keys.get("tavus")
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
async def tavus_health_check(
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep
):
    """
    Check Tavus API health
    
    Returns:
        - status: healthy/unhealthy
        - api_key_valid: True if API key is valid
        - total_replicas: Number of replicas (if healthy)
        - error: Error message (if unhealthy)
    """
    try:
        result = await tavus_service.health_check(api_key=api_keys.get("tavus"))
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


# ============================================================================
# Replica-Voice Mapping API Endpoints
# ============================================================================

class CreateReplicaMappingRequest(BaseModel):
    """Request model for creating a replica-voice mapping"""
    replica_id: str
    voice_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: bool = False


@router.get("/api/v1/tavus/replica-mappings")
async def list_replica_mappings(db: DbServiceDep):
    """List all replica-voice mappings"""
    try:
        mappings = await db.list_replica_configs()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": mappings,
                "count": len(mappings)
            }
        )
    except Exception as e:
        logger.error(f"❌ Error listing replica mappings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tavus/replica-mappings/default")
async def get_default_replica_mapping(db: DbServiceDep):
    """Get the default replica-voice mapping"""
    try:
        config = await db.get_default_replica_config()
        if config:
            # Convert datetime objects to ISO format strings for JSON serialization
            def serialize_datetime(obj):
                """Recursively convert datetime objects to ISO format strings"""
                if isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                else:
                    return obj
            
            serialized_config = serialize_datetime(config)
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": serialized_config
                }
            )
        else:
            raise HTTPException(status_code=404, detail="No default replica mapping found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting default replica mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/tavus/replica-mappings/{replica_id}")
async def get_replica_mapping(replica_id: str, db: DbServiceDep):
    """Get replica-voice mapping for a specific replica"""
    try:
        config = await db.get_replica_config(replica_id)
        if config:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": config
                }
            )
        else:
            raise HTTPException(status_code=404, detail=f"Replica mapping not found: {replica_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting replica mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/tavus/replica-mappings")
async def create_replica_mapping(
    request: CreateReplicaMappingRequest, 
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    db: DbServiceDep
):
    """
    Create or update a replica-voice mapping
    
    Validates that:
    - replica_id exists in Tavus
    - voice_id exists in Cartesia
    """
    try:
        # Validate replica exists in Tavus
        replica = await tavus_service.get_replica(request.replica_id, verbose=False, api_key=api_keys.get("tavus"))
        if not replica:
            raise HTTPException(
                status_code=400,
                detail=f"Replica not found in Tavus: {request.replica_id}"
            )
        
        # Validate voice exists in Cartesia
        voice = await voice_cloning_service.get_voice(request.voice_id, api_key=api_keys.get("cartesia"))
        if not voice:
            # Try to list all voices to see if it's a pre-built voice
            all_voices = await voice_cloning_service.list_voices(api_key=api_keys.get("cartesia"))
            voice_found = any(v.get("id") == request.voice_id for v in all_voices)
            if not voice_found:
                raise HTTPException(
                    status_code=400,
                    detail=f"Voice not found in Cartesia: {request.voice_id}"
                )
        
        # Create mapping
        success = await db.create_replica_mapping(
            replica_id=request.replica_id,
            voice_id=request.voice_id,
            name=request.name,
            description=request.description,
            is_default=request.is_default
        )
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Replica mapping created/updated: {request.replica_id}"
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create replica mapping")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating replica mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/v1/tavus/replica-mappings/{replica_id}/set-default")
async def set_default_replica_mapping(
    replica_id: str,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    db: DbServiceDep
):
    """Set a replica as the default (unset others)
    
    If no mapping exists for this replica, creates one with auto-cloned voice.
    """
    try:
        # Verify replica exists in Tavus
        replica = await tavus_service.get_replica(replica_id, verbose=False, api_key=api_keys.get("tavus"))
        if not replica:
            raise HTTPException(
                status_code=404,
                detail=f"Replica not found in Tavus: {replica_id}"
            )
        
        replica_name = replica.get("replica_name", replica_id)
        
        # Check if mapping exists
        config = await db.get_replica_config(replica_id)
        if not config:
            # No mapping exists - create one with auto-cloned voice
            # The bot will auto-clone the voice when needed, but we need a mapping entry
            logger.info(f"🔄 No mapping found for {replica_id}, creating default mapping...")
            
            # Create a basic mapping (voice will be auto-cloned by bot when used)
            # Use None/empty voice_id - bot will auto-clone from video when needed
            # We need to modify create_replica_mapping to accept optional voice_id
            # For now, create mapping with a placeholder that bot will replace
            success = await db.create_replica_mapping(
                replica_id=replica_id,
                voice_id="auto-clone",  # Special marker - bot will auto-clone when used
                name=f"{replica_name} Voice",
                description="Auto-created when set as default (voice will be auto-cloned)",
                is_default=True
            )
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create replica mapping"
                )
        else:
            # Mapping exists - just set as default
            success = await db.set_default_replica(replica_id)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to set default replica"
                )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Replica {replica_name} set as default"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error setting default replica: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/tavus/replica-mappings/{replica_id}/clone-voice")
async def clone_voice_for_replica(
    replica_id: str,
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    db: DbServiceDep
):
    """
    Manually clone voice from replica's thumbnail video.
    
    This extracts audio from the replica's video and creates a Cartesia voice clone.
    The cloned voice is then saved as a mapping for this replica.
    """
    try:
        import httpx
        import tempfile
        import subprocess
        from services.voice_cloning_service import VoiceCloningService
        
        # Verify replica exists
        replica = await tavus_service.get_replica(replica_id, verbose=True, api_key=api_keys.get("tavus"))
        if not replica:
            raise HTTPException(status_code=404, detail=f"Replica not found: {replica_id}")
        
        replica_name = replica.get("replica_name", "Unknown")
        video_url = replica.get("thumbnail_video_url")
        
        if not video_url:
            raise HTTPException(status_code=400, detail="No video URL found for this replica")
        
        logger.info(f"🎤 Cloning voice for replica: {replica_name} ({replica_id})")
        
        # Download video
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(video_url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to download video: {response.status_code}")
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
                error_msg = result.stderr.decode()[:200] if result.stderr else "Unknown error"
                raise HTTPException(status_code=500, detail=f"FFmpeg error: {error_msg}")
            
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            # Clone voice using Cartesia
            voice_service = VoiceCloningService()
            voice_name = f"{replica_name} Voice"
            cartesia_key = api_keys.get("cartesia")
            
            clone_result = await voice_service.clone_voice(
                api_key=cartesia_key,
                audio_data=audio_data,
                voice_name=voice_name,
                language="en",
                mode="similarity"
            )
            
            cloned_voice_id = clone_result.get("voice_id")
            
            if not cloned_voice_id:
                raise HTTPException(status_code=500, detail="Voice cloning failed - no voice_id returned")
            
            # Check if this replica is currently the default
            current_default = await db.get_default_replica_config()
            is_default = current_default and current_default.get("replica_id") == replica_id
            
            # Save the mapping
            success = await db.create_replica_mapping(
                replica_id=replica_id,
                voice_id=cloned_voice_id,
                name=voice_name,
                description=f"Cloned from {replica_name} video",
                is_default=is_default
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to save voice mapping")
            
            logger.info(f"✅ Voice cloned successfully: {voice_name} ({cloned_voice_id})")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Voice cloned successfully for {replica_name}",
                    "voice_id": cloned_voice_id,
                    "voice_name": voice_name
                }
            )
            
        finally:
            import os as _os
            try:
                _os.unlink(video_path)
                _os.unlink(audio_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cloning voice: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/tavus/replica-mappings/{replica_id}")
async def delete_replica_mapping(replica_id: str, db: DbServiceDep):
    """Delete a replica-voice mapping (soft delete)"""
    try:
        success = await db.delete_replica_mapping(replica_id)
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Replica mapping deleted: {replica_id}"
                }
            )
        else:
            raise HTTPException(status_code=404, detail=f"Replica mapping not found: {replica_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting replica mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

