"""
Daily.co API Service

Handles room creation and meeting token generation for interviews.
Based on: https://www.daily.co/blog/intro-to-room-access-control/
"""

import os
import httpx
from typing import Dict, Any, Optional
from loguru import logger


DEFAULT_ROOM_EXP_SECONDS = int(os.getenv("DAILY_ROOM_EXP_SECONDS", "1800"))


class DailyService:
    """Service for interacting with Daily.co API"""
    
    def __init__(self):
        self.api_key = os.getenv("DAILY_API_KEY")
        self.api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
        self.domain = os.getenv("DAILY_DOMAIN", "hi2inspire.daily.co")
        
        if not self.api_key:
            logger.warning("⚠️ DAILY_API_KEY not set - room creation will fail")
    
    async def create_interview_room(
        self, 
        interview_id: str,
        candidate_name: str = "Candidate",
        expires_in_minutes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a unique Daily.co room for an interview
        
        Args:
            interview_id: Unique interview identifier
            candidate_name: Name of the candidate (for room name)
            expires_in_minutes: Room expiration time (default: 60 minutes)
            
        Returns:
            Dict with room details including URL, or None if failed
        """
        if not self.api_key:
            logger.error("❌ Cannot create room: DAILY_API_KEY not configured")
            return None
        
        # Generate unique room name
        room_name = f"interview-{interview_id}"
        room_exp_minutes = expires_in_minutes or max(1, DEFAULT_ROOM_EXP_SECONDS // 60)
        
        # Room configuration
        # Reference: https://www.daily.co/blog/intro-to-room-access-control/
        room_config = {
            "name": room_name,
            "privacy": "private",  # Private room requires tokens to join
            "properties": {
                "enable_chat": False,
                "enable_screenshare": False,
                "enable_emoji_reactions": False,
                "enable_people_ui": False,
                "enable_pip_ui": False,
                "enable_noise_cancellation_ui": True,
                "enable_knocking": False,
                "start_video_off": False,
                "start_audio_off": False,
                "enable_recording": "cloud",  # Enable cloud recording
                "exp": self._calculate_expiry(room_exp_minutes),
                "eject_at_room_exp": True,  # Eject participants when room expires
                "owner_only_broadcast": False,  # Allow both bot and candidate to speak
                "enable_prejoin_ui": True,  # Show prejoin UI for candidates
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/rooms",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=room_config,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    room_data = response.json()
                    logger.info(f"✅ Created Daily.co room: {room_data['url']}")
                    return {
                        "room_url": room_data["url"],
                        "room_name": room_data["name"],
                        "room_id": room_data["id"],
                        "created_at": room_data.get("created_at"),
                        "expires": room_data["config"].get("exp")
                    }
                else:
                    error_msg = response.text
                    logger.error(f"❌ Failed to create room: {response.status_code} - {error_msg}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error creating Daily.co room: {e}")
            return None
    
    async def create_bot_token(
        self,
        room_name: str,
        expires_in_minutes: Optional[int] = None
    ) -> Optional[str]:
        """
        Create a meeting token for the AI bot (owner access)
        
        Reference: https://www.daily.co/blog/intro-to-room-access-control/
        
        Args:
            room_name: Name of the room
            expires_in_minutes: Token expiration time
            
        Returns:
            Meeting token string, or None if failed
        """
        if not self.api_key:
            logger.error("❌ Cannot create token: DAILY_API_KEY not configured")
            return None
        
        token_exp_minutes = expires_in_minutes or max(1, DEFAULT_ROOM_EXP_SECONDS // 60)
        
        token_config = {
            "properties": {
                "room_name": room_name,
                "is_owner": True,  # Bot needs owner privileges
                "user_name": "AI Interviewer Bot",
                "exp": self._calculate_expiry(token_exp_minutes),
                "enable_recording": "cloud"  # Bot can start recording
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/meeting-tokens",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=token_config,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    logger.info(f"✅ Created bot token for room: {room_name}")
                    return token_data["token"]
                else:
                    error_msg = response.text
                    logger.error(f"❌ Failed to create bot token: {response.status_code} - {error_msg}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error creating bot token: {e}")
            return None
    
    async def create_candidate_token(
        self,
        room_name: str,
        candidate_name: str,
        expires_in_minutes: Optional[int] = None
    ) -> Optional[str]:
        """
        Create a meeting token for the candidate (participant access)
        
        Reference: https://www.daily.co/blog/intro-to-room-access-control/
        
        Args:
            room_name: Name of the room
            candidate_name: Name of the candidate
            expires_in_minutes: Token expiration time
            
        Returns:
            Meeting token string, or None if failed
        """
        if not self.api_key:
            logger.error("❌ Cannot create token: DAILY_API_KEY not configured")
            return None
        
        token_exp_minutes = expires_in_minutes or max(1, DEFAULT_ROOM_EXP_SECONDS // 60)
        
        token_config = {
            "properties": {
                "room_name": room_name,
                "is_owner": False,  # Candidate is a participant
                "user_name": candidate_name,
                "exp": self._calculate_expiry(token_exp_minutes)
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/meeting-tokens",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=token_config,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    logger.info(f"✅ Created candidate token for: {candidate_name}")
                    return token_data["token"]
                else:
                    error_msg = response.text
                    logger.error(f"❌ Failed to create candidate token: {response.status_code} - {error_msg}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error creating candidate token: {e}")
            return None
    
    async def delete_room(self, room_name: str) -> bool:
        """
        Delete a Daily.co room after interview completion
        
        Args:
            room_name: Name of the room to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            logger.error("❌ Cannot delete room: DAILY_API_KEY not configured")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.api_url}/rooms/{room_name}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Deleted room: {room_name}")
                    return True
                else:
                    logger.error(f"❌ Failed to delete room: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error deleting room: {e}")
            return False
    
    def _calculate_expiry(self, minutes: int) -> int:
        """Calculate Unix timestamp for expiry (seconds since epoch)"""
        from datetime import datetime, timedelta
        future_time = datetime.now() + timedelta(minutes=minutes)
        return int(future_time.timestamp())
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return {
            "service": "Daily.co API",
            "configured": self.api_key is not None,
            "api_url": self.api_url,
            "domain": self.domain
        }


# Global instance
daily_service = DailyService()

