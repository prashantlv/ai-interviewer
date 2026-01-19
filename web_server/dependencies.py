"""
FastAPI Dependencies

Provides dependency injection for services throughout the application.
This module defines all injectable dependencies following FastAPI best practices.
"""
from typing import Annotated, Optional, Dict, Any
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.database import DatabaseService
from services.bot_manager import BotManager
from services.scoring_config_service import ScoringConfigService
from services.question_engine import QuestionEngine
from services.scoring_engine import ScoringEngine
from services.auth_service import auth_service

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


# =============================================================================
# Dependency Functions
# =============================================================================

def get_db_service(request: Request) -> DatabaseService:
    """
    Get database service from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        DatabaseService instance
        
    Raises:
        AttributeError: If db_service not initialized in app state
    """
    return request.app.state.db_service


def get_bot_manager(request: Request) -> BotManager:
    """
    Get bot manager from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        BotManager instance
        
    Raises:
        AttributeError: If bot_manager not initialized in app state
    """
    return request.app.state.bot_manager


def get_scoring_config(request: Request) -> ScoringConfigService:
    """
    Get scoring config service from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        ScoringConfigService instance
        
    Raises:
        AttributeError: If scoring_config_service not initialized in app state
    """
    return request.app.state.scoring_config_service


def get_question_engine(request: Request) -> QuestionEngine:
    """
    Get question engine from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        QuestionEngine instance
        
    Raises:
        AttributeError: If question_engine not initialized in app state
    """
    return request.app.state.question_engine


def get_scoring_engine(request: Request) -> ScoringEngine:
    """
    Get scoring engine from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        ScoringEngine instance
        
    Raises:
        AttributeError: If scoring_engine not initialized in app state
    """
    return request.app.state.scoring_engine


# =============================================================================
# Type Aliases (Annotated Dependencies)
# =============================================================================
# These provide cleaner syntax in route signatures:
# Instead of: db: DatabaseService = Depends(get_db_service)
# Use:        db: DbServiceDep

DbServiceDep = Annotated[DatabaseService, Depends(get_db_service)]
"""Database service dependency - injects DatabaseService instance"""

BotManagerDep = Annotated[BotManager, Depends(get_bot_manager)]
"""Bot manager dependency - injects BotManager instance"""

ScoringConfigDep = Annotated[ScoringConfigService, Depends(get_scoring_config)]
"""Scoring config dependency - injects ScoringConfigService instance"""

QuestionEngineDep = Annotated[QuestionEngine, Depends(get_question_engine)]
"""Question engine dependency - injects QuestionEngine instance"""

ScoringEngineDep = Annotated[ScoringEngine, Depends(get_scoring_engine)]
"""Scoring engine dependency - injects ScoringEngine instance"""


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    
    Checks token in:
    1. Authorization header (Bearer token)
    2. Query parameter (token)
    3. Cookies (accessToken or access_token)
    
    Returns:
        Dict with userId and dataModel
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    # Try to get token from Authorization header
    token = None
    if credentials:
        token = credentials.credentials
    
    # If not in header, try other sources
    if not token:
        token = auth_service.extract_token_from_request(request)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login at https://human2intelligence.com/",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token
    user_data = auth_service.verify_access_token(token)
    return user_data

# Type alias for route dependencies
CurrentUserDep = Annotated[Dict[str, Any], Depends(get_current_user)]
"""Current user dependency - injects authenticated user data (userId, dataModel)"""


# =============================================================================
# Admin Authentication Dependencies
# =============================================================================

async def get_admin_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current authenticated admin from cookie
    
    Checks admin_session cookie for admin login status
    
    Returns:
        Dict with username
        
    Raises:
        HTTPException: If admin not logged in
    """
    from services.database import db_service
    
    admin_username = request.cookies.get("admin_session")
    if not admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Please login at /admin/login"
        )
    
    # Verify admin exists and is active
    admin = await db_service.get_admin_user(admin_username)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin session. Please login again."
        )
    
    return {
        "username": admin_username
    }

# Type alias for admin routes
AdminUserDep = Annotated[Dict[str, Any], Depends(get_admin_user)]
"""Admin user dependency - injects authenticated admin data (username)"""


# =============================================================================
# Usage Example
# =============================================================================
"""
In your router files:

from dependencies import DbServiceDep, BotManagerDep

@router.get("/interviews")
async def get_interviews(
    request: Request,
    db: DbServiceDep  # Automatically injected!
):
    interviews = await db.get_interviews()
    return interviews

@router.post("/bots/start")
async def start_bot(
    interview_id: str,
    bot_manager: BotManagerDep  # Automatically injected!
):
    result = bot_manager.schedule_interview(interview_id)
    return result
"""
