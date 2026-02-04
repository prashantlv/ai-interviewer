"""
Voice Cloning API Router
Handles voice cloning and management endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from dependencies import DbServiceDep, CurrentUserDep, UserApiKeysDep
from services.voice_cloning_service import voice_cloning_service
from loguru import logger

router = APIRouter()


class VoiceResponse(BaseModel):
    """Response model for cloned voice"""
    voice_id: str
    name: str
    language: str
    mode: str
    created_at: datetime
    owner_id: Optional[str] = None


class VoiceListResponse(BaseModel):
    """Response model for list of voices"""
    voices: List[VoiceResponse]
    total: int


@router.post("/clone", response_model=VoiceResponse)
async def clone_voice(
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep,
    db: DbServiceDep,
    audio_file: UploadFile = File(..., description="Audio file (WAV/MP3, 3-5 seconds recommended)"),
    voice_name: str = Form(..., description="Name for the cloned voice"),
    language: str = Form("en", description="Language code (en, es, fr, etc.)"),
    mode: str = Form("similarity", description="similarity or stability"),
    enhance: bool = Form(False, description="Clean and denoise audio"),
    owner_id: Optional[str] = Form(None, description="Owner/user ID")
):
    """
    Clone a voice from an audio file
    
    **Requirements:**
    - Audio file: 3-5 seconds (optimal)
    - Clear recording without background noise
    - Supported formats: WAV, MP3, FLAC, OGG
    
    **Tips for best results:**
    - Record in a quiet environment
    - Use a good quality microphone
    - Speak naturally and clearly
    - 5 seconds is ideal for accuracy
    - Set enhance=true if audio is noisy
    """
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Validate file size (max 10MB)
        if len(audio_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")
        
        # Validate audio duration is reasonable (approx check via size)
        if len(audio_data) < 10 * 1024:  # Less than ~10KB
            raise HTTPException(
                status_code=400,
                detail="Audio file too small. Please provide at least 3 seconds of audio."
            )
        
        logger.info(f"🎤 Cloning voice from file: {audio_file.filename} ({len(audio_data)} bytes)")
        
        # Clone voice using Cartesia
        cartesia_key = api_keys.get("cartesia")
        result = await voice_cloning_service.clone_voice(
            audio_data=audio_data,
            voice_name=voice_name,
            language=language,
            mode=mode,
            enhance=enhance,
            api_key=cartesia_key
        )
        
        # Store in database
        voice_data = {
            "voice_id": result["voice_id"],
            "name": voice_name,
            "language": language,
            "mode": mode,
            "enhanced": enhance,
            "owner_id": owner_id,
            "created_at": datetime.now(),
            "metadata": result.get("metadata", {})
        }
        
        if db and db.database:
            await db.database.cloned_voices.insert_one(voice_data)
            logger.info(f"✅ Stored cloned voice in database: {voice_name}")
        
        return VoiceResponse(
            voice_id=result["voice_id"],
            name=voice_name,
            language=language,
            mode=mode,
            created_at=datetime.now(),
            owner_id=owner_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Voice cloning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")


@router.get("/", response_model=VoiceListResponse)
async def list_voices(
    owner_id: Optional[str] = None,
    db: DbServiceDep = None
):
    """
    List all cloned voices
    
    Optionally filter by owner_id to get user-specific voices
    """
    try:
        voices = []
        
        if db and db.database:
            # Query database for cloned voices
            query = {}
            if owner_id:
                query["owner_id"] = owner_id
            
            cursor = db.database.cloned_voices.find(query).sort("created_at", -1)
            async for voice in cursor:
                voices.append(VoiceResponse(
                    voice_id=voice["voice_id"],
                    name=voice["name"],
                    language=voice.get("language", "en"),
                    mode=voice.get("mode", "similarity"),
                    created_at=voice["created_at"],
                    owner_id=voice.get("owner_id")
                ))
        
        return VoiceListResponse(
            voices=voices,
            total=len(voices)
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to list voices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {str(e)}")


@router.get("/{voice_id}", response_model=VoiceResponse)
async def get_voice(voice_id: str, db: DbServiceDep = None):
    """Get details of a specific cloned voice"""
    try:
        if db and db.database:
            voice = await db.database.cloned_voices.find_one({"voice_id": voice_id})
            if voice:
                return VoiceResponse(
                    voice_id=voice["voice_id"],
                    name=voice["name"],
                    language=voice.get("language", "en"),
                    mode=voice.get("mode", "similarity"),
                    created_at=voice["created_at"],
                    owner_id=voice.get("owner_id")
                )
        
        raise HTTPException(status_code=404, detail="Voice not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get voice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get voice: {str(e)}")


@router.delete("/{voice_id}")
async def delete_voice(voice_id: str, db: DbServiceDep = None):
    """
    Delete a cloned voice
    
    Note: This only removes it from our database.
    The voice remains in Cartesia's system.
    """
    try:
        if db and db.database:
            result = await db.database.cloned_voices.delete_one({"voice_id": voice_id})
            if result.deleted_count > 0:
                logger.info(f"✅ Deleted voice: {voice_id}")
                return {"message": "Voice deleted successfully", "voice_id": voice_id}
        
        raise HTTPException(status_code=404, detail="Voice not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete voice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete voice: {str(e)}")


@router.get("/cartesia/voices", response_model=Dict[str, Any])
async def get_cartesia_voices(
    current_user: CurrentUserDep,
    api_keys: UserApiKeysDep
):
    """
    Get all voices from Cartesia (including pre-built voices)
    
    This includes both:
    - Cartesia's pre-built voices
    - Your cloned voices
    """
    try:
        cartesia_key = api_keys.get("cartesia")
        voices = await voice_cloning_service.list_voices(api_key=cartesia_key)
        return {
            "voices": voices,
            "total": len(voices)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get Cartesia voices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Cartesia voices: {str(e)}")

