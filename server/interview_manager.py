#!/usr/bin/env python3
"""
Interview Manager Script

Manages AI interviewer sessions with automatic reconnection capabilities.
Handles cases where the AI interviewer drops from the call but candidates remain.
"""

import asyncio
import os
import sys
import signal
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Add current directory to path to import ai_interviewer
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv(override=True)

class InterviewManager:
    def __init__(self):
        self.room_url = os.getenv("DAILY_SAMPLE_ROOM_URL")
        self.is_running = False
        self.restart_count = 0
        self.max_restarts = 5
        
    async def start_interview_session(self):
        """Start a new interview session with reconnection capability."""
        
        if not self.room_url:
            logger.error("DAILY_SAMPLE_ROOM_URL not set in .env file")
            return
            
        logger.info(f"🎬 Starting AI Interview Session")
        logger.info(f"📍 Room URL: {self.room_url}")
        logger.info(f"🤖 Backend: {os.getenv('BOT_IMPLEMENTATION', 'openai').upper()}")
        video_service = os.getenv('VIDEO_SERVICE', 'none').lower()
        logger.info(f"🎬 Video Service: {video_service.upper()}")
        
        self.is_running = True
        
        while self.is_running and self.restart_count < self.max_restarts:
            try:
                logger.info(f"🚀 Starting AI Interviewer (attempt {self.restart_count + 1})")
                
                # Run the ai-interviewer as a subprocess to avoid event loop conflicts
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "ai-interviewer.py", "--transport", "daily",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=os.path.dirname(__file__)
                )
                
                # Reset restart count on successful start
                bot_started = False
                
                # Monitor the process output in real-time
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    
                    line_text = line.decode().strip()
                    if line_text:
                        # Check for successful bot startup
                        if "🚀 Bot ready!" in line_text or "Uvicorn running on" in line_text:
                            if not bot_started:
                                logger.info("✅ AI Interviewer started successfully!")
                                bot_started = True
                                self.restart_count = 0  # Reset counter on successful start
                        
                        # Log important messages
                        if any(keyword in line_text.lower() for keyword in ["error", "exception", "traceback", "bot ready", "uvicorn running"]):
                            if "warning" not in line_text.lower():  # Skip RTVI warnings
                                logger.info(f"📋 {line_text}")
                
                # Wait for process to complete
                await process.wait()
                
                # Check if we should continue running
                if not self.is_running:
                    logger.info("🛑 Session stopped by user")
                    break
                
                # If bot never started successfully, it's an error
                if not bot_started:
                    self.restart_count += 1
                    error_msg = f"Bot failed to start (exit code: {process.returncode})"
                    raise Exception(error_msg)
                
                # If bot started but exited, check if it was normal or error
                if process.returncode != 0:
                    self.restart_count += 1
                    error_msg = f"Bot crashed with exit code {process.returncode}"
                    raise Exception(error_msg)
                else:
                    # Normal completion (user left call) - restart immediately
                    logger.info("🔄 Session completed normally, restarting bot...")
                    continue
                
            except KeyboardInterrupt:
                logger.info("🛑 Interview session stopped by user")
                self.is_running = False
                break
                
            except Exception as e:
                logger.error(f"❌ AI Interviewer error: {e}")
                
                if self.restart_count < self.max_restarts:
                    wait_time = min(5 * self.restart_count, 30)  # Exponential backoff
                    logger.info(f"🔄 Restarting in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"💥 Maximum restart attempts ({self.max_restarts}) reached")
                    break
        
        logger.info("📋 Interview session ended")
    
    def stop_session(self):
        """Stop the current interview session."""
        logger.info("🛑 Stopping interview session...")
        self.is_running = False

async def main():
    """Main entry point for the interview manager."""
    
    manager = InterviewManager()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"📢 Received signal {signum}")
        manager.stop_session()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await manager.start_interview_session()
    except Exception as e:
        logger.error(f"Fatal error in interview manager: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🎯 AI Interview Manager")
    print("=" * 50)
    print("Features:")
    print("• Automatic reconnection if AI interviewer drops")
    print("• Persistent room URL for candidates")
    print("• Graceful error handling")
    print("• Session monitoring")
    print("=" * 50)
    
    asyncio.run(main())
