"""
Bot Manager Service - High-level interface for managing AI interview bots

This service provides a clean API for:
- Scheduling bot jobs
- Monitoring bot status
- Managing bot lifecycle
- Integrating with Redis/RQ job queue

Sprint 1.2 - Job Queue System
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from rq import Queue, Worker
from rq.job import Job
from redis import Redis

from workers.ai_bot_worker import start_interview_bot, stop_interview_bot, get_active_bots

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotManager:
    """
    High-level service for managing AI interview bots
    
    Provides clean interface for:
    - Scheduling new interviews (enqueuing jobs)
    - Checking bot/job status
    - Stopping bots
    - Monitoring workers
    """
    
    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        queue_name: str = 'ai_bots'
    ):
        """
        Initialize Bot Manager
        
        Args:
            redis_host: Redis host (default: localhost)
            redis_port: Redis port (default: 6379)
            queue_name: RQ queue name (default: ai_bots)
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.queue_name = queue_name
        
        # Initialize Redis connection
        self.redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        
        # Initialize RQ queue
        self.queue = Queue(queue_name, connection=self.redis_conn)
        
        logger.info(f"✅ BotManager initialized (queue: {queue_name})")
    
    def schedule_interview(
        self,
        interview_id: str,
        config: Optional[Dict[str, Any]] = None,
        delay: int = 0
    ) -> Dict[str, Any]:
        """
        Schedule a new interview bot
        
        Enqueues a job to start an AI bot for the specified interview.
        
        Args:
            interview_id: The interview ID to conduct
            config: Optional configuration for the bot
            delay: Optional delay in seconds before starting (default: 0)
            
        Returns:
            Dict with job info including job_id, status, etc.
        """
        logger.info(f"📅 Scheduling interview bot: {interview_id}")
        
        try:
            # Enqueue the job
            if delay > 0:
                job = self.queue.enqueue_in(
                    timedelta(seconds=delay),
                    start_interview_bot,
                    interview_id,
                    config,
                    job_id=f"interview_{interview_id}"
                )
            else:
                job = self.queue.enqueue(
                    start_interview_bot,
                    interview_id,
                    config,
                    job_id=f"interview_{interview_id}",
                    job_timeout='30m',  # 30 minute timeout
                    result_ttl=3600  # Keep result for 1 hour
                )
            
            logger.info(f"✅ Job enqueued: {job.id}")
            
            return {
                "success": True,
                "interview_id": interview_id,
                "job_id": job.id,
                "status": job.get_status(),
                "enqueued_at": datetime.now().isoformat(),
                "position": job.get_position() if job.get_position() is not None else 0
            }
            
        except Exception as e:
            error_msg = f"Failed to schedule interview: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "interview_id": interview_id,
                "error": error_msg
            }
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a specific job
        
        Args:
            job_id: The RQ job ID
            
        Returns:
            Dict with job status and details
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            result = {
                "success": True,
                "job_id": job.id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
            
            # Add result if job is finished
            if job.is_finished:
                result["result"] = job.result
            
            # Add error if job failed
            if job.is_failed:
                result["error"] = str(job.exc_info) if job.exc_info else "Unknown error"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "job_id": job_id,
                "error": f"Job not found or error: {str(e)}"
            }
    
    def get_interview_status(self, interview_id: str) -> Dict[str, Any]:
        """
        Get status of an interview (by interview_id, not job_id)
        
        Args:
            interview_id: The interview ID
            
        Returns:
            Dict with interview bot status
        """
        job_id = f"interview_{interview_id}"
        return self.get_job_status(job_id)
    
    def stop_bot(self, interview_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Stop a running interview bot
        
        This enqueues a stop job to gracefully terminate the bot.
        
        Args:
            interview_id: The interview ID whose bot should be stopped
            force: If True, force kill the bot
            
        Returns:
            Dict with stop operation result
        """
        logger.info(f"🛑 Stopping bot for interview: {interview_id}")
        
        try:
            # Enqueue stop job with high priority
            job = self.queue.enqueue(
                stop_interview_bot,
                interview_id,
                force,
                job_id=f"stop_{interview_id}",
                at_front=True  # High priority
            )
            
            return {
                "success": True,
                "interview_id": interview_id,
                "stop_job_id": job.id,
                "message": "Stop job enqueued"
            }
            
        except Exception as e:
            error_msg = f"Failed to stop bot: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "interview_id": interview_id,
                "error": error_msg
            }
    
    def get_active_bots(self) -> Dict[str, Any]:
        """
        Get list of currently active bots
        
        Returns:
            Dict with active bots information
        """
        try:
            # This will be tracked in-memory by the worker
            # For now, return job queue stats
            active_jobs = []
            
            # Get started jobs (currently running)
            started_registry = self.queue.started_job_registry
            for job_id in started_registry.get_job_ids():
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    if job.func_name == 'workers.ai_bot_worker.start_interview_bot':
                        active_jobs.append({
                            "job_id": job.id,
                            "interview_id": job.args[0] if job.args else None,
                            "started_at": job.started_at.isoformat() if job.started_at else None,
                            "status": "running"
                        })
                except:
                    continue
            
            return {
                "success": True,
                "active_bots": active_jobs,
                "count": len(active_jobs)
            }
            
        except Exception as e:
            error_msg = f"Failed to get active bots: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "active_bots": [],
                "count": 0
            }
    
    def get_queue_info(self) -> Dict[str, Any]:
        """
        Get information about the job queue
        
        Returns:
            Dict with queue statistics
        """
        try:
            # Get queue stats
            queued_count = len(self.queue)
            
            # Get workers
            workers = Worker.all(connection=self.redis_conn)
            active_workers = [w for w in workers if w.state == 'busy']
            
            # Get job registries
            started_jobs = self.queue.started_job_registry.count
            finished_jobs = self.queue.finished_job_registry.count
            failed_jobs = self.queue.failed_job_registry.count
            
            return {
                "success": True,
                "queue_name": self.queue_name,
                "queued_jobs": queued_count,
                "workers": {
                    "total": len(workers),
                    "active": len(active_workers),
                    "idle": len(workers) - len(active_workers)
                },
                "jobs": {
                    "queued": queued_count,
                    "running": started_jobs,
                    "finished": finished_jobs,
                    "failed": failed_jobs
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to get queue info: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a queued job (before it starts)
        
        Args:
            job_id: The RQ job ID
            
        Returns:
            Dict with cancellation result
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            if job.get_status() not in ['queued', 'scheduled']:
                return {
                    "success": False,
                    "job_id": job_id,
                    "error": f"Cannot cancel job in status: {job.get_status()}"
                }
            
            job.cancel()
            logger.info(f"✅ Job cancelled: {job_id}")
            
            return {
                "success": True,
                "job_id": job_id,
                "message": "Job cancelled successfully"
            }
            
        except Exception as e:
            error_msg = f"Failed to cancel job: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "job_id": job_id,
                "error": error_msg
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of the job queue system
        
        Returns:
            Dict with health status
        """
        try:
            # Test Redis connection
            redis_ping = self.redis_conn.ping()
            
            # Get workers
            workers = Worker.all(connection=self.redis_conn)
            worker_count = len(list(workers))
            
            # Check if any workers are available
            workers_available = worker_count > 0
            
            status = "healthy" if redis_ping and workers_available else "degraded"
            if not redis_ping:
                status = "unhealthy"
            
            return {
                "status": status,
                "redis_connected": bool(redis_ping),
                "workers_available": workers_available,
                "worker_count": worker_count,
                "queue_name": self.queue_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance (initialized in main.py lifespan)
bot_manager: Optional[BotManager] = None


def get_bot_manager() -> BotManager:
    """
    Get the global BotManager instance
    
    Returns:
        BotManager instance
        
    Raises:
        RuntimeError if BotManager not initialized
    """
    if bot_manager is None:
        raise RuntimeError("BotManager not initialized. Call initialize_bot_manager() first.")
    return bot_manager


def initialize_bot_manager(redis_host: str = 'localhost', redis_port: int = 6379) -> BotManager:
    """
    Initialize the global BotManager instance
    
    Args:
        redis_host: Redis host
        redis_port: Redis port
        
    Returns:
        Initialized BotManager instance
    """
    global bot_manager
    bot_manager = BotManager(redis_host=redis_host, redis_port=redis_port)
    return bot_manager


if __name__ == "__main__":
    # For testing
    print("Bot Manager Service")
    print("=" * 60)
    
    # Initialize
    manager = BotManager()
    
    # Test health check
    health = manager.health_check()
    print(f"\nHealth Check: {health}")
    
    # Test queue info
    queue_info = manager.get_queue_info()
    print(f"\nQueue Info: {queue_info}")
    
    print("\nBot Manager is ready to use!")

