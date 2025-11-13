"""
Cartesia TTS Service for Pipecat
Implements Text-to-Speech using Cartesia's Sonic API
"""

import asyncio
import aiohttp
import os
from typing import AsyncGenerator
from loguru import logger

from pipecat.frames.frames import Frame, AudioRawFrame, ErrorFrame
from pipecat.services.tts_service import TTSService


class CartesiaTTSService(TTSService):
    """Cartesia TTS service implementation for Pipecat"""
    
    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091",  # Default Sonic voice
        model: str = "sonic-english",
        language: str = "en",
        sample_rate: int = 16000,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self._api_key = api_key
        self._voice_id = voice_id
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._api_url = "https://api.cartesia.ai/tts/bytes"
        self._api_version = "2024-06-10"
        
        logger.info(f"🎤 CartesiaTTSService initialized with voice: {voice_id}, model: {model}")
    
    def can_generate_metrics(self) -> bool:
        """Cartesia supports metrics"""
        return True
    
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """
        Generate speech from text using Cartesia API
        
        Args:
            text: Text to convert to speech
            
        Yields:
            AudioRawFrame: Audio frames containing PCM data
        """
        logger.debug(f"🎵 Generating speech for text: {text[:50]}...")
        
        try:
            await self.start_ttfb_metrics()
            
            headers = {
                "X-API-Key": self._api_key,
                "Cartesia-Version": self._api_version,
                "Content-Type": "application/json"
            }
            
            payload = {
                "model_id": self._model,
                "transcript": text,
                "voice": {
                    "mode": "id",
                    "id": self._voice_id
                },
                "language": self._language,
                "output_format": {
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": self._sample_rate
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Cartesia API error {response.status}: {error_text}")
                        yield ErrorFrame(f"Cartesia TTS failed: {response.status}")
                        return
                    
                    await self.start_tts_usage_metrics(text)
                    
                    # Read audio data in chunks
                    audio_data = await response.read()
                    
                    if audio_data:
                        # Create audio frame with PCM data
                        frame = AudioRawFrame(
                            audio=audio_data,
                            sample_rate=self._sample_rate,
                            num_channels=1
                        )
                        yield frame
                        await self.stop_ttfb_metrics()
                        logger.debug(f"✅ Generated {len(audio_data)} bytes of audio")
                    else:
                        logger.warning("⚠️ No audio data received from Cartesia")
                    
        except asyncio.TimeoutError:
            logger.error("❌ Cartesia API timeout")
            yield ErrorFrame("Cartesia TTS timeout")
        except Exception as e:
            logger.error(f"❌ Cartesia TTS error: {str(e)}")
            yield ErrorFrame(f"Cartesia TTS error: {str(e)}")

