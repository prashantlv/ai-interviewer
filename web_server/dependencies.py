"""
FastAPI Dependencies

Provides dependency injection for services throughout the application.
This module defines all injectable dependencies following FastAPI best practices.
"""
from typing import Annotated
from fastapi import Depends, Request

from services.database import DatabaseService
from services.bot_manager import BotManager
from services.scoring_config_service import ScoringConfigService
from services.question_engine import QuestionEngine
from services.scoring_engine import ScoringEngine


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
