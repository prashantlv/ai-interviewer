"""
Cartesia Voice Cloning Service
Handles instant voice cloning using Cartesia's API
"""

import os
import httpx
from typing import Optional, Dict, Any
from loguru import logger


class VoiceCloningService:
    """Service for cloning voices using Cartesia Instant Voice Cloning API"""
    
    def __init__(self):
        # Default API key from environment (for backward compatibility)
        self.default_api_key = os.getenv("CARTESIA_API_KEY")
        self.api_url = "https://api.cartesia.ai/voices/clone"
        self.api_version = "2024-06-10"
        
        if not self.default_api_key:
            logger.warning("⚠️  CARTESIA_API_KEY not set - voice cloning will not work without per-user keys")
    
    async def clone_voice(
        self,
        audio_data: bytes,
        voice_name: str,
        language: str = "en",
        mode: str = "similarity",
        enhance: bool = False,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clone a voice from audio data using Cartesia Instant Voice Cloning
        
        Args:
            audio_data: Audio file bytes (3-5 seconds recommended)
            voice_name: Name for the cloned voice
            language: Language code (default: "en")
            mode: "similarity" or "stability" 
                  - similarity: Matches voice characteristics closely
                  - stability: More stable but less accurate
            enhance: Clean and denoise the audio (use if noisy)
            api_key: Optional Cartesia API key. If not provided, uses default from env.
        
        Returns:
            Dict with voice_id, name, and metadata
        
        Raises:
            Exception if cloning fails
        """
        key = api_key or self.default_api_key
        if not key:
            raise ValueError("Cartesia API key not provided and CARTESIA_API_KEY env var not set")
        
        try:
            logger.info(f"🎤 Cloning voice: {voice_name} (language: {language}, mode: {mode})")
            
            headers = {
                "X-API-Key": key,
                "Cartesia-Version": self.api_version,
            }
            
            # Create multipart form data
            files = {
                "clip": ("voice.wav", audio_data, "audio/wav")
            }
            
            data = {
                "name": voice_name,
                "language": language,
                "mode": mode,
                "enhance": str(enhance).lower()
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    error_msg = f"Cartesia voice cloning failed: {response.status_code} - {response.text}"
                    logger.error(f"❌ {error_msg}")
                    raise Exception(error_msg)
                
                result = response.json()
                voice_id = result.get("id")
                
                logger.info(f"✅ Voice cloned successfully: {voice_name} (ID: {voice_id})")
                
                return {
                    "voice_id": voice_id,
                    "name": voice_name,
                    "language": language,
                    "mode": mode,
                    "enhanced": enhance,
                    "metadata": result
                }
                
        except httpx.TimeoutException:
            error_msg = "Voice cloning timed out (>60s)"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"❌ Voice cloning error: {str(e)}")
            raise
    
    async def get_voice(self, voice_id: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get voice metadata from Cartesia
        
        Args:
            voice_id: The voice ID to retrieve
            api_key: Optional Cartesia API key. If not provided, uses default from env.
            
        Returns:
            Voice metadata dict or None if not found
        """
        key = api_key or self.default_api_key
        if not key:
            return None
        
        try:
            headers = {
                "X-API-Key": key,
                "Cartesia-Version": self.api_version,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.cartesia.ai/voices/{voice_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"⚠️  Voice not found: {voice_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error fetching voice: {str(e)}")
            return None
    
    async def list_voices(self, api_key: Optional[str] = None) -> list[Dict[str, Any]]:
        """
        List all available voices (including cloned ones)
        
        Args:
            api_key: Optional Cartesia API key. If not provided, uses default from env.
        
        Returns:
            List of voice metadata dicts
        """
        key = api_key or self.default_api_key
        if not key:
            return []
        
        try:
            headers = {
                "X-API-Key": key,
                "Cartesia-Version": self.api_version,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.cartesia.ai/voices",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"⚠️  Failed to list voices: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Error listing voices: {str(e)}")
            return []


# Singleton instance
voice_cloning_service = VoiceCloningService()

