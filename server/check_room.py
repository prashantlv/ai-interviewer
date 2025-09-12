#!/usr/bin/env python3
"""
Room Status Checker

Checks if there are participants in the Daily.co room and provides
information for rejoining ongoing interviews.
"""

import os
import sys
import asyncio
import aiohttp
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)

async def check_room_status():
    """Check the status of the Daily.co room."""
    
    daily_api_key = os.getenv("DAILY_API_KEY")
    room_url = os.getenv("DAILY_SAMPLE_ROOM_URL")
    
    if not daily_api_key:
        logger.error("DAILY_API_KEY not found in .env")
        return
        
    if not room_url:
        logger.error("DAILY_SAMPLE_ROOM_URL not found in .env")
        return
    
    # Extract room name from URL
    room_name = room_url.split("/")[-1]
    
    headers = {
        "Authorization": f"Bearer {daily_api_key}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Check room info
            async with session.get(
                f"https://api.daily.co/v1/rooms/{room_name}",
                headers=headers
            ) as response:
                if response.status == 200:
                    room_data = await response.json()
                    logger.info(f"✅ Room '{room_name}' exists")
                    logger.info(f"📍 Room URL: {room_url}")
                    
                    # Check for active sessions
                    async with session.get(
                        f"https://api.daily.co/v1/rooms/{room_name}/get-session-data",
                        headers=headers
                    ) as session_response:
                        if session_response.status == 200:
                            session_data = await session_response.json()
                            participants = session_data.get("participants", {})
                            
                            if participants:
                                logger.info(f"👥 Active participants: {len(participants)}")
                                for participant_id, participant_info in participants.items():
                                    user_name = participant_info.get("user_name", "Unknown")
                                    joined_at = participant_info.get("joined_at", "Unknown")
                                    logger.info(f"   • {user_name} (joined: {joined_at})")
                                
                                logger.warning("🔄 Candidates may be waiting - you can rejoin now!")
                                print("\n" + "="*50)
                                print("🚀 TO REJOIN THE INTERVIEW:")
                                print("python ai-interviewer.py --transport daily")
                                print("  OR")
                                print("python interview_manager.py")
                                print("="*50)
                            else:
                                logger.info("📭 No active participants in room")
                        else:
                            logger.warning("⚠️  Could not check session data")
                            
                elif response.status == 404:
                    logger.warning(f"⚠️  Room '{room_name}' not found")
                else:
                    logger.error(f"❌ Error checking room: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Error connecting to Daily API: {e}")

if __name__ == "__main__":
    print("🔍 Daily.co Room Status Checker")
    print("=" * 40)
    asyncio.run(check_room_status())
