"""
AI Bot Worker - RQ Job for Starting Interview Bots

This worker picks up jobs from Redis queue and starts AI bot processes
for conducting interviews automatically.

Sprint 1.2 - Job Queue System
"""

import os
import sys
import subprocess
import time
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Store active bot processes (in-memory for now)
ACTIVE_BOTS = {}


def start_interview_bot(interview_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    RQ Job: Start an AI bot process for a specific interview
    
    This is the main job function that RQ workers will execute.
    It starts the AI bot as a subprocess and monitors it.
    
    Args:
        interview_id: The interview ID to conduct
        config: Optional configuration dict (should contain 'room_url')
        
    Returns:
        Dict with job result including status, PID, etc.
    """
    logger.info(f"🤖 Starting bot worker for interview: {interview_id}")
    
    start_time = datetime.now()
    
    try:
        # Extract room URL from config or generate default
        room_url = None
        if config and "room_url" in config:
            room_url = config["room_url"]
            logger.info(f"📍 Using room URL from config: {room_url}")
        else:
            # Generate default room URL based on interview ID
            room_url = f"https://hi2inspire.daily.co/interview-{interview_id}"
            logger.info(f"📍 Generated room URL: {room_url}")
        
        # Build the command to start the AI bot
        command = _build_bot_command(interview_id, room_url)
        logger.info(f"📝 Command: {' '.join(command)}")
        
        # Start the bot process
        # Note: stdout/stderr are captured but we log them for debugging
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_get_bot_environment(interview_id),
            cwd=_get_bot_directory(),
            text=True,
            bufsize=1
        )
        
        # Log the first few lines of output for debugging
        import threading
        def log_output(pipe, prefix):
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        logger.info(f"{prefix} {line.rstrip()}")
            except Exception:
                pass  # Silently ignore output reading errors
        
        # Start threads to log output (non-blocking)
        threading.Thread(target=log_output, args=(process.stdout, f"[Bot {interview_id}]"), daemon=True).start()
        threading.Thread(target=log_output, args=(process.stderr, f"[Bot {interview_id} ERR]"), daemon=True).start()
        
        # Store process info
        ACTIVE_BOTS[interview_id] = {
            "pid": process.pid,
            "started_at": start_time.isoformat(),
            "status": "running",
            "process": process
        }
        
        logger.info(f"✅ Bot started successfully! PID: {process.pid}")
        
        # Note: We don't wait for the process to complete here
        # The bot will run independently and send results when done
        
        return {
            "success": True,
            "interview_id": interview_id,
            "pid": process.pid,
            "started_at": start_time.isoformat(),
            "message": f"Bot started successfully for interview {interview_id}"
        }
        
    except FileNotFoundError as e:
        error_msg = f"Bot script not found: {e}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "interview_id": interview_id,
            "error": error_msg,
            "error_type": "file_not_found"
        }
        
    except Exception as e:
        error_msg = f"Failed to start bot: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "interview_id": interview_id,
            "error": error_msg,
            "error_type": type(e).__name__
        }


def _build_bot_command(interview_id: str, room_url: str = None) -> list:
    """
    Build the command to start the AI bot
    
    Args:
        interview_id: The interview ID
        room_url: Daily.co room URL (if provided, bot joins directly)
    
    Returns list of command arguments for subprocess
    """
    # Path to the bot script
    bot_script = "ai-interviewer.py"
    
    # Determine Python executable to use
    # In Docker, use the current Python interpreter (sys.executable)
    # In local dev, try conda environment first, then fall back to sys.executable
    python_executable = None
    
    # Check if we're in Docker (common indicators)
    is_docker = False
    if os.path.exists("/.dockerenv"):
        is_docker = True
    elif os.path.exists("/proc/self/cgroup"):
        try:
            with open("/proc/self/cgroup", "r") as f:
                if "docker" in f.read():
                    is_docker = True
        except:
            pass
    
    if is_docker:
        # In Docker, use the current Python interpreter
        python_executable = sys.executable
        logger.info(f"🐳 Docker detected, using: {python_executable}")
    else:
        # Local development: try conda environment first
        conda_python = os.path.expanduser("~/miniconda3/envs/pipecat-env/bin/python")
        if os.path.exists(conda_python):
            python_executable = conda_python
            logger.info(f"💻 Using conda environment: {python_executable}")
        else:
            # Fall back to current Python
            python_executable = sys.executable
            logger.info(f"💻 Using system Python: {python_executable}")
    
    # Build command
    command = [
        python_executable,
        bot_script,
    ]
    
    # If room_url provided, join directly; otherwise start web server
    if room_url:
        command.extend(["--room-url", room_url])
    else:
        command.extend(["--transport", "daily"])
    
    return command


def _get_bot_environment(interview_id: str) -> Dict[str, str]:
    """
    Get environment variables for the bot process
    
    Includes all current env vars plus interview-specific ones
    """
    env = os.environ.copy()
    
    # Add interview-specific env vars
    env["INTERVIEW_ID"] = interview_id
    
    # Ensure these are set (from .env file in bot directory)
    # The bot will load its own .env file, but we can override here if needed
    # env["WEB_SERVER_URL"] = os.getenv("WEB_SERVER_URL", "http://localhost:8009")
    # env["DAILY_SAMPLE_ROOM_URL"] = os.getenv("DAILY_SAMPLE_ROOM_URL", "")
    
    return env


def _get_bot_directory() -> str:
    """
    Get the directory where the bot script is located
    
    Returns absolute path to server/ directory
    """
    # Assuming workers/ is in web_server/ and bot is in server/
    current_dir = os.path.dirname(os.path.abspath(__file__))  # workers/
    web_server_dir = os.path.dirname(current_dir)  # web_server/
    project_root = os.path.dirname(web_server_dir)  # ai-interviewer/
    bot_dir = os.path.join(project_root, "server")
    
    return bot_dir


def stop_interview_bot(interview_id: str, force: bool = False) -> Dict[str, Any]:
    """
    RQ Job: Stop a running interview bot
    
    Args:
        interview_id: The interview ID whose bot should be stopped
        force: If True, use SIGKILL instead of SIGTERM
        
    Returns:
        Dict with result status
    """
    logger.info(f"🛑 Stopping bot for interview: {interview_id}")
    
    if interview_id not in ACTIVE_BOTS:
        return {
            "success": False,
            "interview_id": interview_id,
            "error": "Bot not found in active bots"
        }
    
    bot_info = ACTIVE_BOTS[interview_id]
    process = bot_info.get("process")
    pid = bot_info.get("pid")
    
    if not process:
        return {
            "success": False,
            "interview_id": interview_id,
            "error": "Process object not available"
        }
    
    try:
        # Try graceful shutdown first
        if not force:
            logger.info(f"📤 Sending SIGTERM to PID {pid}...")
            process.terminate()
            
            # Wait up to 5 seconds for graceful shutdown
            try:
                process.wait(timeout=5)
                logger.info(f"✅ Bot terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️ Timeout waiting for graceful shutdown, forcing...")
                force = True
        
        # Force kill if needed
        if force:
            logger.info(f"💥 Sending SIGKILL to PID {pid}...")
            process.kill()
            process.wait(timeout=2)
            logger.info(f"✅ Bot killed forcefully")
        
        # Remove from active bots
        del ACTIVE_BOTS[interview_id]
        
        return {
            "success": True,
            "interview_id": interview_id,
            "pid": pid,
            "message": "Bot stopped successfully"
        }
        
    except Exception as e:
        error_msg = f"Failed to stop bot: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "interview_id": interview_id,
            "error": error_msg
        }


def get_active_bots() -> Dict[str, Dict[str, Any]]:
    """
    Get list of currently active bot processes
    
    Returns:
        Dict mapping interview_id to bot info
    """
    # Clean up any dead processes
    for interview_id, bot_info in list(ACTIVE_BOTS.items()):
        process = bot_info.get("process")
        if process and process.poll() is not None:
            # Process has finished
            bot_info["status"] = "completed"
            bot_info["exit_code"] = process.returncode
            logger.info(f"📊 Bot for {interview_id} completed with exit code {process.returncode}")
    
    return ACTIVE_BOTS


# For testing: Simple function to verify worker is working
def test_job(message: str = "Hello from RQ!") -> Dict[str, Any]:
    """
    Simple test job to verify RQ worker is functioning
    
    Args:
        message: Test message to echo back
        
    Returns:
        Dict with test result
    """
    logger.info(f"🧪 Test job executing: {message}")
    time.sleep(2)  # Simulate some work
    
    return {
        "success": True,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "worker": "ai_bot_worker"
    }


if __name__ == "__main__":
    # For manual testing
    print("AI Bot Worker Module")
    print("=" * 60)
    print(f"Bot directory: {_get_bot_directory()}")
    print(f"Test command: {' '.join(_build_bot_command('test_123'))}")
    print("\nThis module is meant to be used with RQ workers.")
    print("To start a worker: rq worker --with-scheduler")

