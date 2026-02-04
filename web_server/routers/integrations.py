"""
User Integrations Router
Handles user API key management (store, retrieve, delete)
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from dependencies import CurrentUserDep, DbServiceDep
from loguru import logger

router = APIRouter()


class SetApiKeyRequest(BaseModel):
    """Request model for setting API key"""
    api_key: str = Field(..., description="API key to store (will be encrypted)")
    is_active: bool = Field(True, description="Whether the key is active")
    config: Optional[Dict[str, Any]] = Field(None, description="Provider-specific configuration (e.g., default_replica_id, default_voice_id)")


class IntegrationStatus(BaseModel):
    """Response model for integration status"""
    provider: str
    is_configured: bool
    is_active: bool


class IntegrationListResponse(BaseModel):
    """Response model for list of integrations"""
    integrations: List[IntegrationStatus]
    total: int


# ============================================================================
# API Endpoints - User Integrations Management
# ============================================================================

@router.get("/api/v1/user/integrations")
async def list_user_integrations(
    current_user: CurrentUserDep,
    db: DbServiceDep
) -> IntegrationListResponse:
    """
    Get list of all integrations for the current user
    
    Returns:
        List of integration statuses (without exposing actual keys)
    """
    try:
        user_id = current_user.get("userId")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Get all integrations for user
        integrations_data = await db.get_user_integrations(user_id)
        
        # Build status list
        providers = ["openai", "tavus", "cartesia", "daily"]
        statuses = []
        
        for provider in providers:
            # Check if user has this integration
            integration = next(
                (i for i in integrations_data if i.get("provider") == provider),
                None
            )
            
            statuses.append(IntegrationStatus(
                provider=provider,
                is_configured=integration is not None,
                is_active=integration.get("is_active", False) if integration else False
            ))
        
        # Include config in response if available
        integrations_with_config = []
        for status in statuses:
            integration = next(
                (i for i in integrations_data if i.get("provider") == status.provider),
                None
            )
            status_dict = status.dict()
            if integration and integration.get("config"):
                status_dict["config"] = integration.get("config")
            integrations_with_config.append(status_dict)
        
        return IntegrationListResponse(
            integrations=integrations_with_config if integrations_with_config else statuses,
            total=len([s for s in statuses if s.is_configured])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing integrations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/user/integrations/{provider}")
async def set_user_api_key(
    provider: str,
    request: SetApiKeyRequest,
    current_user: CurrentUserDep,
    db: DbServiceDep
) -> JSONResponse:
    """
    Store or update API key for a provider
    
    Path Parameters:
        - provider: Provider name (openai, tavus, cartesia, daily)
    
    Request Body:
        - api_key: The API key to store (will be encrypted)
        - is_active: Whether the key is active (default: true)
    
    Returns:
        Success message
    """
    try:
        user_id = current_user.get("userId")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Validate provider
        valid_providers = ["openai", "tavus", "cartesia", "daily"]
        if provider.lower() not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Validate API key is not empty
        if not request.api_key or not request.api_key.strip():
            raise HTTPException(status_code=400, detail="API key cannot be empty")
        
        # Store the API key with optional config
        success = await db.set_user_api_key(
            user_id=user_id,
            provider=provider.lower(),
            api_key=request.api_key.strip(),
            is_active=request.is_active,
            config=request.config
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to store API key. Please try again."
            )
        
        logger.info(f"✅ User {user_id} stored API key for provider {provider}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"API key for {provider} stored successfully",
                "provider": provider.lower()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error storing API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/user/integrations/{provider}")
async def delete_user_api_key(
    provider: str,
    current_user: CurrentUserDep,
    db: DbServiceDep
) -> JSONResponse:
    """
    Delete (deactivate) API key for a provider
    
    Path Parameters:
        - provider: Provider name (openai, tavus, cartesia, daily)
    
    Returns:
        Success message
    """
    try:
        user_id = current_user.get("userId")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Validate provider
        valid_providers = ["openai", "tavus", "cartesia", "daily"]
        if provider.lower() not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Delete the API key
        success = await db.delete_user_api_key(
            user_id=user_id,
            provider=provider.lower()
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"API key for {provider} not found"
            )
        
        logger.info(f"✅ User {user_id} deleted API key for provider {provider}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"API key for {provider} deleted successfully",
                "provider": provider.lower()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting API key: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/user/integrations/status")
async def get_integrations_status(
    current_user: CurrentUserDep,
    db: DbServiceDep
) -> Dict[str, Any]:
    """
    Get status of all integrations (which are configured, which use env vars)
    
    Returns:
        Dict with provider statuses and fallback info
    """
    try:
        user_id = current_user.get("userId")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        import os
        
        # Get user's integrations
        integrations_data = await db.get_user_integrations(user_id)
        
        # Build status for each provider
        providers = ["openai", "tavus", "cartesia", "daily"]
        status = {}
        
        for provider in providers:
            integration = next(
                (i for i in integrations_data if i.get("provider") == provider),
                None
            )
            
            env_key = os.getenv(f"{provider.upper()}_API_KEY")
            
            status[provider] = {
                "has_user_key": integration is not None,
                "is_active": integration.get("is_active", False) if integration else False,
                "has_env_fallback": bool(env_key),
                "using": "user_key" if integration and integration.get("is_active") else ("env_var" if env_key else "none"),
                "config": integration.get("config", {}) if integration else {}
            }
        
        return {
            "success": True,
            "user_id": user_id,
            "providers": status,
            "note": "If has_user_key is false, system will use environment variable as fallback"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting integration status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateConfigRequest(BaseModel):
    """Request model for updating integration configuration"""
    config: Dict[str, Any] = Field(..., description="Configuration to update (e.g., default_replica_id, default_voice_id)")


@router.put("/api/v1/user/integrations/{provider}/config")
async def update_integration_config(
    provider: str,
    request: UpdateConfigRequest,
    current_user: CurrentUserDep,
    db: DbServiceDep
) -> Dict[str, Any]:
    """
    Update configuration for a user's integration (without changing API key)
    
    Example for Tavus:
        {
            "config": {
                "default_replica_id": "r0518ad3a314"
            }
        }
    
    Example for Cartesia:
        {
            "config": {
                "default_voice_id": "c252b73c-8627-4b1d-b9e1-9e03e8550d47",
                "model": "sonic-english",
                "language": "en"
            }
        }
    """
    try:
        user_id = current_user.get("userId")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Validate provider
        valid_providers = ["openai", "tavus", "cartesia", "daily"]
        if provider.lower() not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Check if integration exists
        integration = await db.database.user_integrations.find_one(
            {
                "user_id": user_id,
                "provider": provider.lower()
            }
        )
        
        if not integration:
            raise HTTPException(
                status_code=404,
                detail=f"Integration not found for provider {provider}. Please set API key first."
            )
        
        # Update config
        success = await db.update_user_integration_config(
            user_id=user_id,
            provider=provider.lower(),
            config=request.config
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update configuration"
            )
        
        logger.info(f"✅ Updated config for user {user_id}, provider {provider}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Configuration for {provider} updated successfully",
                "provider": provider.lower(),
                "config": request.config
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/user/integrations/{provider}/config")
async def get_integration_config(
    provider: str,
    current_user: CurrentUserDep,
    db: DbServiceDep
) -> Dict[str, Any]:
    """
    Get configuration for a user's integration
    """
    try:
        user_id = current_user.get("userId")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        # Validate provider
        valid_providers = ["openai", "tavus", "cartesia", "daily"]
        if provider.lower() not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Get config
        config = await db.get_user_integration_config(
            user_id=user_id,
            provider=provider.lower()
        )
        
        if config is None:
            # Check if integration exists
            integration = await db.database.user_integrations.find_one(
                {
                    "user_id": user_id,
                    "provider": provider.lower()
                }
            )
            
            if not integration:
                raise HTTPException(
                    status_code=404,
                    detail=f"Integration not found for provider {provider}"
                )
            
            # Integration exists but no config
            return JSONResponse(
                status_code=200,
                content={
                    "provider": provider.lower(),
                    "config": {}
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "provider": provider.lower(),
                "config": config
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
