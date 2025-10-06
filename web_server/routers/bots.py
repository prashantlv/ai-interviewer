"""
Bot Management Router - API v1

Handles bot lifecycle management, monitoring, and job queue operations.
All endpoints are under /api/v1/bots/

Sprint 1.4: API Versioning
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from dependencies import BotManagerDep

router = APIRouter()


@router.post("/start")
async def start_bot(
    bot_manager: BotManagerDep,
    interview_id: str,
    delay: int = 0
) -> Dict[str, Any]:
    """
    Start an AI bot for an interview
    
    This enqueues a job to start the bot process.
    
    Args:
        bot_manager: Injected bot manager service
        interview_id: The interview ID to conduct
        delay: Optional delay in seconds before starting (default: 0)
        
    Returns:
        Dict with job info including job_id, status, etc.
        
    Raises:
        HTTPException: If bot scheduling fails
    """
    try:
        result = bot_manager.schedule_interview(interview_id, delay=delay)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start bot: {str(e)}"
        )


@router.post("/stop/{interview_id}")
async def stop_bot(
    interview_id: str,
    bot_manager: BotManagerDep,
    force: bool = False
) -> Dict[str, Any]:
    """
    Stop a running interview bot
    
    Args:
        interview_id: The interview ID whose bot to stop
        bot_manager: Injected bot manager service
        force: If True, forcefully kill the process
        
    Returns:
        Dict with stop status
        
    Raises:
        HTTPException: If stopping fails
    """
    try:
        result = bot_manager.stop_bot(interview_id, force=force)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop bot: {str(e)}"
        )


@router.get("/status/{interview_id}")
async def get_bot_status(
    interview_id: str,
    bot_manager: BotManagerDep
) -> Dict[str, Any]:
    """
    Get status of an interview bot
    
    Args:
        interview_id: The interview ID to check
        bot_manager: Injected bot manager service
        
    Returns:
        Dict with bot status information
        
    Raises:
        HTTPException: If status retrieval fails
    """
    try:
        result = bot_manager.get_interview_status(interview_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get bot status: {str(e)}"
        )


@router.get("/active")
async def get_active_bots(
    bot_manager: BotManagerDep
) -> Dict[str, Any]:
    """
    Get list of currently active bots
    
    Args:
        bot_manager: Injected bot manager service
        
    Returns:
        Dict with list of active bots
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        result = bot_manager.get_active_bots()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active bots: {str(e)}"
        )


@router.get("/queue")
async def get_queue_info(
    bot_manager: BotManagerDep
) -> Dict[str, Any]:
    """
    Get job queue information
    
    Returns statistics about the RQ job queue including:
    - Number of queued jobs
    - Number of running jobs
    - Number of finished jobs
    - Active workers
    
    Args:
        bot_manager: Injected bot manager service
        
    Returns:
        Dict with queue statistics
        
    Raises:
        HTTPException: If queue info retrieval fails
    """
    try:
        result = bot_manager.get_queue_info()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue info: {str(e)}"
        )


@router.delete("/job/{job_id}")
async def cancel_job(
    job_id: str,
    bot_manager: BotManagerDep
) -> Dict[str, Any]:
    """
    Cancel a queued job
    
    Args:
        job_id: The job ID to cancel
        bot_manager: Injected bot manager service
        
    Returns:
        Dict with cancellation status
        
    Raises:
        HTTPException: If cancellation fails
    """
    try:
        result = bot_manager.cancel_job(job_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )
