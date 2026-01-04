#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""AI Interviewer Bot Implementation.

This module implements a configurable chatbot that can use either OpenAI's GPT-4 
or Google's Gemini Multimodal Live model based on the BOT_IMPLEMENTATION environment variable.

Features:
- Real-time audio/video interaction through Daily
- Four video options: Robot animation, Simli, HeyGen, Tavus avatars
- Configurable AI backend (OpenAI + separate STT/TTS or Gemini with built-in TTS)
- Interactive features: Voice activity detection, interruption handling
- Cost-optimized with separate STT/TTS services

The bot runs as part of a pipeline that processes audio/video frames and manages
the conversation flow.
"""

import os
import sys
import time
import aiohttp
import json
from urllib.parse import urlparse
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from loguru import logger

# Import scoring engine
from scoring_engine import ScoringEngine
from PIL import Image
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    EndFrame,
    Frame,
    LLMRunFrame,
    OutputImageRawFrame,
    SpriteFrame,
    StartFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.daily.transport import DailyParams, DailyTransport

# IMPORTANT:
# - In Docker Compose, environment variables are injected by the container runtime.
# - We must NOT override them from a local `.env` file inside the image (that would
#   reintroduce `localhost` URLs and break inter-container networking).
_IN_DOCKER = os.path.exists("/.dockerenv")
load_dotenv(override=not _IN_DOCKER)

# Web server integration configuration
# In Docker: the web service is reachable via the Compose service name `web-server`
WEB_SERVER_URL = os.getenv("WEB_SERVER_URL", "http://web-server:8009" if _IN_DOCKER else "http://localhost:8009")
INTERVIEW_ID = os.getenv("INTERVIEW_ID", "default_interview")
DAILY_API_URL = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
DAILY_API_KEY = os.getenv("DAILY_API_KEY")
# Safety timeouts to prevent runaway costs
MAX_SESSION_DURATION_SECONDS = int(os.getenv("MAX_SESSION_DURATION", "900"))  # 15 minutes default
ROOM_EXPIRY_CHECK_INTERVAL = 60  # Check room expiry every 60 seconds
ALONE_AFTER_PARTICIPANT_LEFT_TIMEOUT = int(os.getenv("ALONE_TIMEOUT", "100"))  # 100 seconds after participant leaves


async def fetch_interview_config(session: aiohttp.ClientSession, interview_id: str) -> Optional[Dict[str, Any]]:
    """Fetch interview configuration from web server"""
    try:
        url = f"{WEB_SERVER_URL}/api/v1/bot/interview-config/{interview_id}"
        logger.info(f"Fetching interview config from: {url}")
        
        async with session.get(url) as response:
            if response.status == 200:
                config = await response.json()
                logger.info(f"✅ Retrieved interview config for {interview_id}")
                return config
            else:
                logger.warning(f"Failed to fetch interview config: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching interview config: {e}")
        return None

async def send_interview_result(
    session: aiohttp.ClientSession, 
    interview_id: str, 
    transcript: str, 
    evaluation: Dict[str, Any],
    recording: Optional[Dict[str, Any]] = None
) -> bool:
    """Send interview results back to web server"""
    try:
        url = f"{WEB_SERVER_URL}/api/v1/bot/interview-result"
        payload = {
            "interview_id": interview_id,
            "transcript": transcript,
            "evaluation": evaluation
        }
        if recording:
            payload["recording"] = recording
        
        logger.info(f"Sending interview results to: {url}")
        
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                logger.info(f"✅ Successfully sent interview results for {interview_id}")
                return True
            else:
                logger.warning(f"Failed to send interview results: {response.status}")
                return False
    except Exception as e:
        logger.error(f"Error sending interview results: {e}")
        return False


def extract_room_name(room_url: Optional[str]) -> Optional[str]:
    """Extract the Daily room name from a full URL."""
    if not room_url:
        return None
    try:
        parsed = urlparse(room_url)
        return parsed.path.rstrip("/").split("/")[-1]
    except Exception as exc:
        logger.warning(f"Unable to parse room name from URL {room_url}: {exc}")
        return None


async def daily_api_request(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Generic helper for Daily REST API calls."""
    if not DAILY_API_KEY:
        logger.warning("DAILY_API_KEY not configured - skipping Daily API call")
        return None
    
    url = f"{DAILY_API_URL}{path}"
    headers = {
        "Authorization": f"Bearer {DAILY_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        async with session.request(method, url, headers=headers, json=payload) as response:
            if response.status in (200, 201, 202):
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"Daily API error ({response.status}) for {path}: {error_text}")
                return None
    except Exception as exc:
        logger.error(f"Daily API request failed for {path}: {exc}")
        return None


async def start_daily_recording(
    session: aiohttp.ClientSession,
    room_name: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Start Daily cloud recording for a room."""
    if not room_name:
        return None
    
    logger.info(f"🎥 Starting Daily recording for room: {room_name}")
    return await daily_api_request(
        session,
        "POST",
        f"/rooms/{room_name}/recordings/start",
        payload=None,
    )


async def stop_daily_recording(
    session: aiohttp.ClientSession,
    room_name: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Stop Daily cloud recording for a room."""
    if not room_name:
        return None
    
    logger.info(f"🛑 Stopping Daily recording for room: {room_name}")
    return await daily_api_request(
        session,
        "POST",
        f"/rooms/{room_name}/recordings/stop",
    )


def serialize_recording_context(recording_context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare recording context for sending to web server."""
    return {
        "room_name": recording_context.get("room_name"),
        "recording_id": recording_context.get("recording_id"),
        "status": recording_context.get("status"),
        "started_at": recording_context.get("started_at"),
        "stopped_at": recording_context.get("stopped_at"),
        "start_response": recording_context.get("start_response"),
        "stop_response": recording_context.get("stop_response"),
    }

def create_dynamic_system_prompt(interview_config: Optional[Dict[str, Any]]) -> str:
    """Create dynamic system prompt based on interview configuration"""
    base_prompt = """You are an AI Interviewer, a professional and friendly assistant conducting job interviews. 
Your goal is to ask thoughtful questions, evaluate candidates, and create a comfortable interview environment. 
Keep your responses concise and professional. Always maintain a conversational tone while being thorough in your assessment.
You are hiring on behalf of Hire2Inspire."""
    
    if not interview_config:
        return base_prompt + " Start by introducing yourself and explaining the interview process."
    
    # Extract interview-specific information
    questions = interview_config.get("questions", [])
    candidate_info = interview_config.get("candidate_info", {})
    
    if questions:
        question_text = "\\n".join([f"{i+1}. {q.get('question', '')}" for i, q in enumerate(questions[:3])])
        candidate_name = candidate_info.get('name', 'the candidate')
        
        # Extract job description details
        job_description = interview_config.get("job_description", {})
        job_title = job_description.get("title", "the position")
        company = job_description.get("company") or "our company"
        location = job_description.get("location", "")
        
        # Extract resume details
        resume_data = interview_config.get("resume_data", {})
        current_role = resume_data.get("experience", {}).get("current_role", "your current role")
        experience_years = resume_data.get("experience", {}).get("total_years", "your")
        
        base_prompt += f"""

IMPORTANT: You are interviewing {candidate_name} for the {job_title} position at {company}.

CANDIDATE CONTEXT:
- Name: {candidate_name}
- Current Role: {current_role}
- Experience: {experience_years} years
- Position Applied For: {job_title}
- Company: {company}
- Location: {location}

REQUIRED QUESTIONS TO ASK (in this exact order):
{question_text}

INSTRUCTIONS:
1. Start by greeting {candidate_name} by name and mention the {job_title} position at {company}
2. Ask each numbered question above in order
3. Wait for complete answers before moving to the next question
4. Ask relevant follow-up questions based on their {current_role} experience
5. Keep the interview focused on the {job_title} requirements"""
    else:
        base_prompt += " Start by introducing yourself and asking about their background and experience."
    
    return base_prompt

# Load configuration from environment
BOT_IMPLEMENTATION = os.getenv("BOT_IMPLEMENTATION", "openai").lower()
VIDEO_SERVICE = os.getenv("VIDEO_SERVICE", "none").lower()  # none, tavus, simli, heygen
TTS_SERVICE = os.getenv("TTS_SERVICE", "openai").lower()  # openai, cartesia

# Import AI services based on configuration
if BOT_IMPLEMENTATION == "openai":
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.services.openai.stt import OpenAISTTService
    from pipecat.services.openai.tts import OpenAITTSService
elif BOT_IMPLEMENTATION == "gemini":
    from pipecat.services.gemini_multimodal_live.gemini import GeminiMultimodalLiveLLMService
else:
    logger.error(f"Invalid BOT_IMPLEMENTATION: {BOT_IMPLEMENTATION}. Must be 'openai' or 'gemini'")
    sys.exit(1)

# Import TTS services based on configuration
if TTS_SERVICE == "cartesia":
    from pipecat.services.cartesia.tts import CartesiaTTSService
    logger.info("🎤 Using Cartesia TTS (WebSocket Streaming)")

# Import video services based on configuration
if VIDEO_SERVICE == "tavus":
    try:
        from pipecat.services.tavus.video import TavusVideoService

        # Tavus transport can be started twice by the framework lifecycle, which can
        # attempt to add the same Daily custom audio track name ("stream") twice.
        # Make Tavus start idempotent to prevent TrackNameAlreadyInUse → mute/no-audio.
        try:
            from pipecat.transports.tavus.transport import TavusTransportClient

            _orig_tavus_start = TavusTransportClient.start

            async def _tavus_start_once(self, *args, **kwargs):
                if getattr(self, "_start_called", False):
                    logger.info("✅ TavusTransportClient.start already called - skipping duplicate start()")
                    return
                self._start_called = True
                try:
                    return await _orig_tavus_start(self, *args, **kwargs)
                except Exception:
                    # allow retry if first start failed
                    self._start_called = False
                    raise

            TavusTransportClient.start = _tavus_start_once
            logger.info("🩹 Applied Tavus start() idempotency guard to prevent duplicate audio track creation")
        except Exception as _exc:
            logger.warning(f"Could not apply Tavus start() guard (continuing): {_exc}")
        
        logger.info("🎥 Using Tavus for video (Cartesia handles audio)")
    except ImportError:
        logger.error("Tavus integration not available. Install with: pip install pipecat-ai[tavus]")
        sys.exit(1)
elif VIDEO_SERVICE == "simli":
    try:
        from pipecat.services.simli.video import SimliVideoService
        from simli import SimliConfig
    except ImportError:
        logger.error("Simli integration not available. Install with: pip install pipecat-ai[simli]")
        sys.exit(1)
elif VIDEO_SERVICE == "heygen":
    try:
        from pipecat.services.heygen.video import HeyGenVideoService
        from pipecat.services.heygen.api import NewSessionRequest
    except ImportError:
        logger.error("HeyGen integration not available. Install with: pip install pipecat-ai[heygen]")
        sys.exit(1)

# Load animation sprites
sprites = []
script_dir = os.path.dirname(__file__)

# Load sequential animation frames
for i in range(1, 26):
    full_path = os.path.join(script_dir, f"assets/robot0{i}.png")
    try:
        with Image.open(full_path) as img:
            sprites.append(OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))
    except FileNotFoundError:
        logger.warning(f"Animation frame not found: {full_path}")
        break

# Create a smooth animation by adding reversed frames
if sprites:
    flipped = sprites[::-1]
    sprites.extend(flipped)
    # Define static and animated states
    quiet_frame = sprites[0]  # Static frame for when bot is listening
    talking_frame = SpriteFrame(images=sprites)  # Animation sequence for when bot is talking
else:
    logger.warning("No animation frames found, running without avatar")
    quiet_frame = None
    talking_frame = None


class TalkingAnimation(FrameProcessor):
    """Manages the bot's visual animation states.

    Switches between static (listening) and animated (talking) states based on
    the bot's current speaking status.
    """

    def __init__(self):
        super().__init__()
        self._is_talking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and update animation state.

        Args:
            frame: The incoming frame to process
            direction: The direction of frame flow in the pipeline
        """
        await super().process_frame(frame, direction)

        # Only handle animation if frames are available
        if talking_frame and quiet_frame:
            # Switch to talking animation when bot starts speaking
            if isinstance(frame, BotStartedSpeakingFrame):
                if not self._is_talking:
                    await self.push_frame(talking_frame)
                    self._is_talking = True
            # Return to static frame when bot stops speaking
            elif isinstance(frame, BotStoppedSpeakingFrame):
                await self.push_frame(quiet_frame)
                self._is_talking = False

        await self.push_frame(frame, direction)



class UserTranscriptCollector(FrameProcessor):
    """Collects candidate speech - must be placed BEFORE context_aggregator."""
    
    def __init__(self, transcript_list: list):
        super().__init__()
        self.transcript_list = transcript_list
        self.last_text = ""
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            logger.info(f"🎤 USER SPEECH: '{text}'")
            if text and len(text) > 1 and text.lower() != self.last_text.lower():
                self.transcript_list.append({"role": "candidate", "content": text})
                self.last_text = text
                logger.info(f"📝 CANDIDATE: {text}")
        
        await self.push_frame(frame, direction)


class AITranscriptCollector(FrameProcessor):
    """Collects AI responses - placed AFTER llm."""
    
    def __init__(self, transcript_list: list):
        super().__init__()
        self.transcript_list = transcript_list
        self.recent = []
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            text = frame.text.strip()
            if text and len(text) > 2:
                if text.lower() not in [t.lower() for t in self.recent[-15:]]:
                    self.transcript_list.append({"role": "ai_interviewer", "content": text})
                    self.recent.append(text)
                    if len(self.recent) > 30:
                        self.recent.pop(0)
                    logger.info(f"🤖 AI: {text}")
        
        await self.push_frame(frame, direction)


class TranscriptCollector(FrameProcessor):
    """Collects conversation transcript for later analysis with advanced filtering."""
    
    def __init__(self, transcript_list: list):
        super().__init__()
        self.transcript_list = transcript_list
        self.recent_ai_texts = []  # Track recent AI utterances for echo detection
        self.recent_candidate_texts = []  # Track recent candidate texts
        self.last_candidate_text = ""  # Track last candidate text to avoid duplicates
        self.pending_ai_text = ""  # Aggregate streaming AI text
        self.last_ai_timestamp = 0  # Track timing for aggregation
        self.time = time
    
    def _is_echo_of_ai(self, text: str) -> bool:
        """Check if candidate transcription is an echo of AI speech."""
        text_lower = text.lower().strip()
        
        for ai_text in self.recent_ai_texts:
            ai_lower = ai_text.lower().strip()
            if text_lower == ai_lower:
                return True
            if len(text_lower) > 5 and text_lower in ai_lower:
                return True
            if len(ai_lower) > 5 and ai_lower in text_lower:
                return True
            if len(text_lower) > 10 and len(ai_lower) > 10:
                if text_lower[:20] == ai_lower[:20]:
                    return True
        return False
    
    def _is_ai_echoing_candidate(self, text: str) -> bool:
        """Check if AI text is echoing what candidate just said."""
        text_lower = text.lower().strip()
        
        # Check against recent candidate transcriptions
        for candidate_text in self.recent_candidate_texts:
            candidate_lower = candidate_text.lower().strip()
            
            # Exact match
            if text_lower == candidate_lower:
                return True
            
            # AI text is contained in candidate speech
            if len(text_lower) > 5 and text_lower in candidate_lower:
                return True
            
            # Candidate speech is contained in AI text
            if len(candidate_lower) > 5 and candidate_lower in text_lower:
                return True
            
            # AI text starts with candidate speech (or vice versa)
            if len(text_lower) > 8 and len(candidate_lower) > 8:
                # Check first 10 chars
                if text_lower[:10] == candidate_lower[:10]:
                    return True
                # Check if one starts with the other
                if text_lower.startswith(candidate_lower[:8]) or candidate_lower.startswith(text_lower[:8]):
                    return True
        
        return False
    
    def _is_duplicate_candidate(self, text: str) -> bool:
        """Check if this is a duplicate/partial of recent candidate text."""
        text_lower = text.lower().strip()
        
        # Check against last candidate text
        if self.last_candidate_text:
            last_lower = self.last_candidate_text.lower().strip()
            if text_lower == last_lower:
                return True
            if len(text_lower) > 5 and text_lower in last_lower:
                return True
        
        # Check against recent texts
        for prev_text in self.recent_candidate_texts[-3:]:
            prev_lower = prev_text.lower().strip()
            if text_lower == prev_lower:
                return True
            # Current text is a shorter version of previous
            if len(text_lower) > 5 and text_lower in prev_lower:
                return True
        
        return False
    
    def _is_streaming_continuation(self, text: str) -> bool:
        """Check if this AI text is a streaming continuation (builds on previous text)."""
        text_lower = text.lower().strip()
        
        # Check against recent AI texts
        for ai_text in self.recent_ai_texts[-5:]:
            ai_lower = ai_text.lower().strip()
            
            # Exact duplicate
            if text_lower == ai_lower:
                return True
            
            # New text STARTS WITH old text (new is longer version)
            # e.g., old="Yeah. I have", new="Yeah. I have a little bit"
            if len(text_lower) > len(ai_lower) and text_lower.startswith(ai_lower):
                return True
            
            # Old text STARTS WITH new text (new is shorter/prefix)
            if len(ai_lower) > len(text_lower) and ai_lower.startswith(text_lower):
                return True
                
            # High similarity - first N characters match
            min_len = min(len(text_lower), len(ai_lower))
            if min_len > 10:
                # If first 80% of the shorter text matches
                check_len = int(min_len * 0.8)
                if text_lower[:check_len] == ai_lower[:check_len]:
                    return True
        
        return False
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # Capture user speech (transcription)
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            logger.info(f"📥 TranscriptionFrame received: '{text[:50]}...' (len={len(text)})")
            if text and len(text) > 1:  # Skip very short transcriptions
                # Always capture candidate speech - filtering caused issues
                self.transcript_list.append({
                    "role": "candidate",
                    "content": text
                })
                self.last_candidate_text = text
                self.recent_candidate_texts.append(text)
                if len(self.recent_candidate_texts) > 5:
                    self.recent_candidate_texts.pop(0)
                logger.info(f"📝 Candidate said: {text}")
        
        # Capture bot responses
        elif isinstance(frame, TextFrame):
            text = frame.text.strip()
            logger.info(f"📥 TextFrame received: '{text[:50]}...' (len={len(text)})")
            if text and len(text) > 1:
                # Skip very short fragments only
                if len(text) < 3:
                    logger.debug(f"🔇 Skipped short fragment: {text}")
                else:
                    # Capture AI response
                    self.transcript_list.append({
                        "role": "ai_interviewer",
                        "content": text
                    })
                    self.recent_ai_texts.append(text)
                    if len(self.recent_ai_texts) > 5:
                        self.recent_ai_texts.pop(0)
                    logger.info(f"📝 AI said: {text}")
        
        await self.push_frame(frame, direction)


async def run_bot(
    transport: BaseTransport,
    session: aiohttp.ClientSession,
    room_meta: Dict[str, Any],
):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Web server integration for dynamic questions
    - Configurable AI backend (OpenAI or Gemini)
    - Separate STT/TTS services for cost optimization
    - Video avatar integration (optional)
    - Language model integration
    - Animation processing (fallback)
    - RTVI event handling
    """

    room_name = room_meta.get("room_name")
    logger.info(f"Starting AI Interviewer with {BOT_IMPLEMENTATION.upper()} backend")
    if VIDEO_SERVICE != "none":
        logger.info(f"{VIDEO_SERVICE.capitalize()} video avatar enabled")
    
    # Fetch interview configuration from web server
    interview_config = await fetch_interview_config(session, INTERVIEW_ID)
    if interview_config:
        logger.info(f"🎯 Using dynamic interview config with {len(interview_config.get('questions', []))} questions")
    else:
        logger.warning("⚠️ Using fallback interview configuration")

    # Initialize AI services based on configuration
    if BOT_IMPLEMENTATION == "openai":
        # OpenAI with separate STT/TTS for cost control
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is required for OpenAI implementation")
            sys.exit(1)

        # Use OpenAI for STT and LLM
        stt = OpenAISTTService(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize TTS based on TTS_SERVICE configuration
        if TTS_SERVICE == "cartesia":
            if not os.getenv("CARTESIA_API_KEY"):
                logger.error("CARTESIA_API_KEY is required when TTS_SERVICE=cartesia")
                sys.exit(1)
            
            # Use Pipecat's built-in Cartesia with WebSocket streaming for low latency
            tts = CartesiaTTSService(
                api_key=os.getenv("CARTESIA_API_KEY"),
                voice_id=os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091"),
                model=os.getenv("CARTESIA_MODEL", "sonic-english"),
                sample_rate=16000,  # Match audio pipeline
            )
            logger.info(f"✅ Initialized Cartesia TTS (WebSocket) with voice: {os.getenv('CARTESIA_VOICE_ID', 'default')}")
        else:
            # Default to OpenAI TTS
            tts = OpenAITTSService(
                api_key=os.getenv("OPENAI_API_KEY"),
                voice="onyx",  # Options: alloy, echo, fable, onyx, nova, shimmer (onyx is deep male)
            )
            logger.info("✅ Initialized OpenAI TTS")
        
        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",  # Cost-optimized model
        )

        # Conversation context for OpenAI with dynamic prompt
        dynamic_prompt = create_dynamic_system_prompt(interview_config)
        messages = [
            {
                "role": "system",
                "content": dynamic_prompt,
            },
        ]

    else:  # BOT_IMPLEMENTATION == "gemini"
        # Gemini setup (built-in STT/TTS)
        if not os.getenv("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY is required for Gemini implementation")
            sys.exit(1)

        llm = GeminiMultimodalLiveLLMService(
            api_key=os.getenv("GOOGLE_API_KEY"),
            voice_id="Puck",  # Available: Aoede, Charon, Fenrir, Kore, Puck
        )

        # Conversation context for Gemini with dynamic prompt
        dynamic_prompt = create_dynamic_system_prompt(interview_config)
        messages = [
            {
                "role": "user",
                "content": dynamic_prompt,
            },
        ]

    # Set up conversation context and management
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)
    
    # Transcript collection temporarily disabled due to pipeline issues
    # Initialize transcript collection
    interview_transcript = []
    # Two collectors: one for user speech (before context), one for AI (after LLM)
    user_collector = UserTranscriptCollector(interview_transcript)
    ai_collector = AITranscriptCollector(interview_transcript)
    
    # Initialize RTVI processor
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
    
    # Initialize video service based on configuration
    video_service = None
    if VIDEO_SERVICE == "tavus":
        if not os.getenv("TAVUS_API_KEY"):
            logger.error("TAVUS_API_KEY is required when VIDEO_SERVICE=tavus")
            sys.exit(1)
        if not os.getenv("TAVUS_REPLICA_ID"):
            logger.error("TAVUS_REPLICA_ID is required when VIDEO_SERVICE=tavus")
            sys.exit(1)
            
        video_service = TavusVideoService(
            api_key=os.getenv("TAVUS_API_KEY"),
            replica_id=os.getenv("TAVUS_REPLICA_ID"),
            session=session,
        )
        logger.info(f"Initialized Tavus with replica: {os.getenv('TAVUS_REPLICA_ID')}")
        
    elif VIDEO_SERVICE == "simli":
        if not os.getenv("SIMLI_API_KEY"):
            logger.error("SIMLI_API_KEY is required when VIDEO_SERVICE=simli")
            sys.exit(1)
        if not os.getenv("SIMLI_FACE_ID"):
            logger.error("SIMLI_FACE_ID is required when VIDEO_SERVICE=simli")
            sys.exit(1)
            
        simli_config = SimliConfig(
            apiKey=os.getenv("SIMLI_API_KEY"),
            faceId=os.getenv("SIMLI_FACE_ID"),
            handleSilence=True,      # Keep video active during silence
            maxSessionLength=1200,   # 20 minute session limit
            maxIdleTime=60,          # 60 second idle timeout
            syncAudio=True,          # Synchronize audio streams
        )
        
        video_service = SimliVideoService(
            simli_config,
            use_turn_server=False,   # Set to True if needed for restrictive networks
            latency_interval=0,      # Latency monitoring interval
        )
        logger.info(f"Initialized Simli with face: {os.getenv('SIMLI_FACE_ID')}")
        
    elif VIDEO_SERVICE == "heygen":
        if not os.getenv("HEYGEN_API_KEY"):
            logger.error("HEYGEN_API_KEY is required when VIDEO_SERVICE=heygen")
            sys.exit(1)
            
        # Configure HeyGen with default or custom avatar
        avatar_id = os.getenv("HEYGEN_AVATAR_ID", "Shawn_Therapist_public")  # Default public avatar
        
        session_request = NewSessionRequest(
            avatar_id=avatar_id
        )
        
        video_service = HeyGenVideoService(
            api_key=os.getenv("HEYGEN_API_KEY"),
            session=session,
            session_request=session_request,
        )
        logger.info(f"Initialized HeyGen with avatar: {avatar_id}")
    
    # Initialize animation fallback (only if no video service is used)
    ta = None
    if VIDEO_SERVICE == "none":
        ta = TalkingAnimation()

    # Build pipeline based on configuration
    if BOT_IMPLEMENTATION == "openai":
        # Pipeline for OpenAI with separate STT/TTS
        # user_collector BEFORE context_aggregator (to capture TranscriptionFrame)
        # ai_collector AFTER llm (to capture TextFrame)
        pipeline_processors = [
            transport.input(),
            stt,
            user_collector,  # Capture user speech BEFORE context consumes it
            rtvi,
            context_aggregator.user(),
            llm,
            ai_collector,  # Capture AI responses AFTER llm generates them
            tts,
        ]
        
        # Add video processing
        if video_service:
            pipeline_processors.append(video_service)
        elif ta:
            pipeline_processors.append(ta)
        
        pipeline_processors.extend([
            transport.output(),
            context_aggregator.assistant(),
        ])
        
    else:  # BOT_IMPLEMENTATION == "gemini"
        # Pipeline for Gemini (built-in STT/TTS)
        pipeline_processors = [
            transport.input(),
            user_collector,  # Capture user speech
            rtvi,
            context_aggregator.user(),
            llm,
            ai_collector,  # Capture AI responses
        ]
        
        # Add video processing (Video services work with Gemini audio)
        if video_service:
            pipeline_processors.append(video_service)
        elif ta:
            pipeline_processors.append(ta)
            
        pipeline_processors.extend([
            transport.output(),
            context_aggregator.assistant(),
        ])

    # Create pipeline
    pipeline = Pipeline(pipeline_processors)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    # Queue StartFrame first to initialize the pipeline (required before processing audio frames)
    await task.queue_frame(StartFrame())    

    # Queue initial frame if available
    if quiet_frame:
        await task.queue_frame(quiet_frame)

    # Track if greeting has been sent (to prevent duplicates)
    greeting_sent = False
    
    async def send_initial_greeting():
        """Send initial greeting to start the conversation"""
        nonlocal greeting_sent
        if greeting_sent:
            return
        greeting_sent = True
        
        # Get candidate info for personalized greeting
        candidate_name = "there"
        position = "this position"
        if interview_config:
            candidate_info = interview_config.get("candidate_info", {})
            candidate_name = candidate_info.get("name", "there")
            job_desc = interview_config.get("job_description", {})
            position = job_desc.get("title", "this position")
        
        # Add initial user message to LLM context to trigger greeting
        # This simulates the candidate "joining" and prompts the AI to speak first
        context.add_message({
            "role": "user",
            "content": f"[Candidate {candidate_name} has joined the interview call for {position}. Begin the interview by greeting them.]"
        })
        
        logger.info(f"🎙️ Bot ready - starting interview for {candidate_name}")
        
        # Kick off the conversation - LLM will respond to above message
        await task.queue_frames([LLMRunFrame()])
    
    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        await send_initial_greeting()

    recording_context = {
        "room_name": room_name,
        "recording_id": None,
        "status": "not_started",
        "started_at": None,
        "stopped_at": None,
        "start_response": None,
        "stop_response": None,
    }

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, participant):
        logger.info(f"Client connected - AI Interviewer ({BOT_IMPLEMENTATION.upper()}) ready")
        # Note: Using OpenAI STT for transcription, not Daily's built-in transcription
        # This prevents the bot from transcribing its own TTS output
        
        if recording_context["status"] == "not_started":
            start_resp = await start_daily_recording(session, room_name)
            if start_resp:
                recording_context["recording_id"] = (
                    start_resp.get("recordingId")
                    or start_resp.get("recording_id")
                    or start_resp.get("id")
                    or recording_context["recording_id"]
                )
                recording_context["status"] = start_resp.get("state", "recording")
                recording_context["started_at"] = start_resp.get("created_at")
                recording_context["start_response"] = start_resp
            else:
                recording_context["status"] = "failed_to_start"

    @transport.event_handler("on_recording_started")
    async def on_recording_started(_transport, data):
        rid = data.get("recordingId") or data.get("recording_id")
        if rid:
            recording_context["recording_id"] = rid
        recording_context["status"] = data.get("state", "recording")
        recording_context["started_at"] = data.get("created_at") or recording_context["started_at"]
        recording_context["start_response"] = data

    @transport.event_handler("on_recording_stopped")
    async def on_recording_stopped(_transport, data):
        # Handle both dict and string (recording ID) formats
        if isinstance(data, str):
            # If data is just a string (recording ID), use it directly
            recording_context["recording_id"] = data
            recording_context["status"] = "stopped"
            from datetime import datetime
            recording_context["stopped_at"] = datetime.now().isoformat()
            recording_context["stop_response"] = {"recording_id": data}
        else:
            # If data is a dict, extract fields normally
            rid = data.get("recordingId") or data.get("recording_id")
            if rid:
                recording_context["recording_id"] = rid
            recording_context["status"] = data.get("state", "stopped")
            recording_context["stopped_at"] = data.get("created_at") or data.get("updated_at")
            recording_context["stop_response"] = data

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.info("Client disconnected")
        
        if recording_context["status"] not in ["not_started", "stopped", "failed_to_start"]:
            stop_resp = await stop_daily_recording(session, room_name)
            if stop_resp:
                recording_context["status"] = stop_resp.get("state", "stopped")
                recording_context["recording_id"] = stop_resp.get("id") or recording_context["recording_id"]
                recording_context["stopped_at"] = stop_resp.get("created_at") or stop_resp.get("updated_at")
                recording_context["stop_response"] = stop_resp
            else:
                recording_context["status"] = "stop_failed"
        
        # Clean up transcript - remove duplicates and streaming artifacts
        def clean_transcript(transcript):
            """Clean transcript: fix mislabeling, remove duplicates, merge fragments."""
            if not transcript:
                return []
            
            # Step 1: Fix mislabeled AI entries that are actually candidate speech
            # AI responses that match nearby candidate speech are likely echoes
            fixed = []
            for i, entry in enumerate(transcript):
                role = entry.get('role', '')
                content = entry.get('content', '').strip()
                
                if not content or len(content) < 2:
                    continue
                
                # Check if this AI entry matches a nearby CANDIDATE entry
                if role == 'ai_interviewer':
                    content_lower = content.lower()
                    is_echo = False
                    
                    # Look at surrounding candidate entries (within 5 positions)
                    for j in range(max(0, i-5), min(len(transcript), i+5)):
                        if j == i:
                            continue
                        other = transcript[j]
                        if other.get('role') == 'candidate':
                            other_content = other.get('content', '').lower().strip()
                            # Check if AI text is contained in or contains candidate text
                            if len(content_lower) > 5 and len(other_content) > 5:
                                if content_lower in other_content or other_content in content_lower:
                                    is_echo = True
                                    break
                                # Check prefix match
                                min_len = min(len(content_lower), len(other_content))
                                if min_len > 8 and content_lower[:min_len-3] == other_content[:min_len-3]:
                                    is_echo = True
                                    break
                    
                    if is_echo:
                        # Skip this - it's an echo of candidate speech
                        continue
                
                fixed.append(entry)
            
            # Step 2: Merge consecutive same-role entries that are fragments
            merged = []
            for entry in fixed:
                role = entry.get('role', '')
                content = entry.get('content', '').strip()
                
                if not content:
                    continue
                
                # If same role as last entry and looks like a fragment, try to merge
                if merged and merged[-1].get('role') == role:
                    last_content = merged[-1].get('content', '').strip()
                    combined_lower = last_content.lower() + ' ' + content.lower()
                    
                    # If this looks like a continuation (short fragment), merge
                    if len(content) < 30 and not content.endswith(('.', '?', '!')):
                        merged[-1]['content'] = last_content + ' ' + content
                        continue
                
                merged.append(entry.copy())
            
            # Step 3: Remove remaining duplicates
            final = []
            for entry in merged:
                role = entry.get('role', '')
                content = entry.get('content', '').strip()
                content_lower = content.lower()
                
                is_duplicate = False
                for prev in final[-5:]:
                    prev_lower = prev.get('content', '').lower().strip()
                    
                    # Exact or near-exact match
                    if content_lower == prev_lower:
                        is_duplicate = True
                        break
                    
                    # One contains the other
                    if len(content_lower) > 10 and len(prev_lower) > 10:
                        if content_lower in prev_lower or prev_lower in content_lower:
                            # Keep the longer one
                            if len(content) > len(prev.get('content', '')):
                                final.remove(prev)
                            else:
                                is_duplicate = True
                            break
                
                if not is_duplicate:
                    final.append(entry)
            
            return final
        
        # Clean the transcript before building text
        cleaned_transcript = clean_transcript(interview_transcript)
        logger.info(f"📝 Cleaned transcript: {len(interview_transcript)} -> {len(cleaned_transcript)} entries")
        
        # Collect transcript
        transcript_text = "\n\n".join([
            f"{entry['role'].upper()}: {entry['content']}" 
            for entry in cleaned_transcript
        ]) if cleaned_transcript else "No transcript available"
        
        logger.info(f"📝 Interview completed - collected {len(interview_transcript)} transcript entries")
        
        # Get candidate info from interview config
        candidate_info = interview_config.get("candidate_info", {}) if interview_config else {}
        job_description = interview_config.get("job_description", {}) if interview_config else {}
        questions = interview_config.get("questions", []) if interview_config else []
        questions_asked = [q.get("question", "") for q in questions]
        
        # Initialize scoring engine with DB-based config
        logger.info("🤖 Starting AI-based scoring analysis...")
        scoring_config = interview_config.get("scoring_config") if interview_config else None
        scoring_engine = ScoringEngine(
            api_key=os.getenv("OPENAI_API_KEY"),
            scoring_config=scoring_config
        )
        
        # Score the interview using LLM
        scoring_result = await scoring_engine.score_interview(
            transcript=cleaned_transcript,
            job_description=job_description,
            questions_asked=questions_asked
        )
        
        # Build complete evaluation with candidate info and config snapshot
        evaluation = {
            "overall_score": scoring_result.get("overall_score", 0),
            "individual_scores": scoring_result.get("individual_scores", {
                "correctness": 0,
                "terminology": 0,
                "confidence": 0,
                "experience_relevance": 0,
                "problem_solving": 0
            }),
            "score_category": scoring_result.get("score_category", "pending"),
            "recommendation": scoring_result.get("recommendation", "pending"),
            "feedback": scoring_result.get("feedback", f"Interview completed with {len(interview_transcript)} exchanges."),
            "strengths": scoring_result.get("strengths", []),
            "weaknesses": scoring_result.get("weaknesses", []),
            "improvement_suggestions": scoring_result.get("improvement_suggestions", []),
            # Include candidate information
            "candidate_name": candidate_info.get("name", "Unknown Candidate"),
            "candidate_email": candidate_info.get("email", "N/A"),
            "position": job_description.get("title", "Unknown Position"),
            "company": job_description.get("company", "Unknown Company"),
            "interview_id": INTERVIEW_ID,
            "questions_asked": questions_asked,
            # Store scoring config snapshot for audit trail
            "scoring_config_used": scoring_result.get("config_used", {
                "config_id": "unknown",
                "config_level": "unknown",
                "config_source": "fallback"
            })
        }
        
        logger.info(f"✅ Scoring complete - Overall: {evaluation['overall_score']}/100 ({evaluation['score_category']})")
        
        # Send results to web server with real transcript and scores
        recording_payload = serialize_recording_context(recording_context)
        await send_interview_result(session, INTERVIEW_ID, transcript_text, evaluation, recording_payload)
        
        await task.cancel()

    @transport.event_handler("on_participant_left")
    async def on_participant_left(_transport, participant, *args):
        nonlocal participant_joined, participant_left, participant_left_time
        # Handle participant leaving event
        participant_info = participant.get("info", {}) if isinstance(participant, dict) else {}
        participant_id = participant.get("id", "unknown") if isinstance(participant, dict) else str(participant)
        user_name = participant_info.get("userName", "") or ""
        
        logger.info(f"👋 Participant left: {participant_id} ({user_name})")
        
        # Log additional info for debugging
        if participant_info:
            logger.debug(f"Participant info: {participant_info}")
        
        # If a real participant had joined and now left, start the alone countdown
        if participant_joined and user_name and "Bot" not in user_name and "AI" not in user_name:
            participant_left = True
            participant_left_time = time.time()
            logger.info(f"📤 Candidate left - starting {ALONE_AFTER_PARTICIPANT_LEFT_TIMEOUT}s alone countdown")

    # Track session start time for safety timeout
    session_start_time = time.time()
    participant_joined = False  # Track if a real participant (not bot) joined
    participant_left = False     # Track if participant left after joining
    participant_left_time = None # When participant left
    
    @transport.event_handler("on_participant_joined")
    async def on_participant_joined_safety(_transport, participant):
        nonlocal participant_joined, participant_left, participant_left_time, greeting_sent
        # Check if this is a real participant (not the bot itself)
        participant_info = participant if isinstance(participant, dict) else {}
        user_name = participant_info.get("info", {}).get("userName", "") or participant_info.get("userName", "")
        if user_name and "Bot" not in user_name and "AI" not in user_name:
            participant_joined = True
            participant_left = False  # Reset if they rejoin
            participant_left_time = None
            logger.info(f"👤 Real participant joined: {user_name}")
            
            # Fallback: If greeting hasn't been sent yet (on_client_ready didn't fire),
            # trigger it now when the candidate joins
            if not greeting_sent:
                logger.info("🎯 Triggering greeting fallback (on_client_ready didn't fire)")
                await asyncio.sleep(0.5)  # Small delay to let Tavus stabilize
                await send_initial_greeting()
    
    async def safety_monitor():
        """Background task to monitor session duration, room expiry, and alone timeout"""
        nonlocal participant_joined, participant_left, participant_left_time
        
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds (more responsive for alone timeout)
            
            elapsed = time.time() - session_start_time
            remaining = MAX_SESSION_DURATION_SECONDS - elapsed
            
            # Check if participant left and we've been alone long enough
            if participant_left and participant_left_time:
                alone_time = time.time() - participant_left_time
                logger.debug(f"⏱️ Alone for {alone_time:.0f}s (timeout: {ALONE_AFTER_PARTICIPANT_LEFT_TIMEOUT}s)")
                
                if alone_time >= ALONE_AFTER_PARTICIPANT_LEFT_TIMEOUT:
                    logger.warning(f"🏁 Participant left {ALONE_AFTER_PARTICIPANT_LEFT_TIMEOUT}s ago - ending interview for scoring")
                    await task.queue_frame(EndFrame())
                    break
            
            # Check max session duration
            if elapsed >= MAX_SESSION_DURATION_SECONDS:
                logger.warning(f"⏰ MAX SESSION DURATION ({MAX_SESSION_DURATION_SECONDS/60:.0f} min) reached - shutting down")
                await task.queue_frame(EndFrame())
                break
            
            # Log warning at 5 minutes remaining
            if 270 < remaining <= 300:  # Between 4.5 and 5 minutes
                logger.warning(f"⚠️ Session ending in ~5 minutes")
            
            # Log status periodically
            if int(elapsed) % 60 == 0:  # Every minute
                logger.debug(f"⏱️ Session elapsed: {elapsed/60:.1f} min, remaining: {remaining/60:.1f} min")
    
    # Start safety monitor as background task
    safety_task = asyncio.create_task(safety_monitor())
    logger.info(f"🛡️ Safety monitor started - Max session: {MAX_SESSION_DURATION_SECONDS/60:.0f} minutes")
    
    runner = PipelineRunner(handle_sigint=False)
    
    try:
        await runner.run(task)
    finally:
        # Clean up safety monitor
        safety_task.cancel()
        try:
            await safety_task
        except asyncio.CancelledError:
            pass
        logger.info("🛡️ Safety monitor stopped")


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""

    # Use aiohttp session for video service integration
    async with aiohttp.ClientSession() as session:
        # Configure video output based on service
        video_service = os.getenv("VIDEO_SERVICE", "none").lower()
        if video_service == "simli":
            # Simli optimized resolution (512x512)
            video_width, video_height = 512, 512
            video_framerate = 30
        elif video_service == "heygen":
            # HeyGen optimal resolution (1280x720)
            video_width, video_height = 1280, 720
            video_framerate = 30
        else:
            # Default/Tavus resolution (1024x576)
            video_width, video_height = 1024, 576
            video_framerate = 30
        
        room_url = runner_args.room_url
        room_meta = {
            "room_url": room_url,
            "room_name": extract_room_name(room_url),
        }
        
        # Audio output:
        # Keep enabled so the candidate hears Cartesia audio in the main Daily room.
        # Tavus still receives audio frames from the pipeline for lip-sync; the Tavus
        # start() guard above prevents the duplicate "stream" track creation error.
        video_service_type = os.getenv("VIDEO_SERVICE", "none").lower()
        audio_out = True
        
        logger.info(f"🔧 DailyTransport config: audio_out_enabled={audio_out} (VIDEO_SERVICE={video_service_type})")
        
        transport = DailyTransport(
            runner_args.room_url,
            runner_args.token,
            "AI Interviewer Bot",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=audio_out,  # Enabled for Cartesia audio delivery
                video_out_enabled=True,
                video_out_is_live=True,           # Real-time video streaming
                video_out_width=video_width,
                video_out_height=video_height,
                video_out_framerate=video_framerate,
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        confidence=0.8,    # Higher confidence threshold
                        start_secs=0.2,    # Quick to detect speech start
                        stop_secs=1.5,     # Wait 1.5 seconds of silence before responding
                        min_volume=0.5     # Minimum volume threshold
                    )
                ),
                transcription_enabled=False,  # Disabled - using OpenAI STT instead
            ),
        )

        await run_bot(transport, session, room_meta)


if __name__ == "__main__":
    import argparse
    import asyncio
    
    # Check if --room-url is provided (direct join mode)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--room-url", type=str, help="Direct join to Daily.co room URL with token")
    args, remaining = parser.parse_known_args()
    
    if args.room_url:
        # Direct join mode - bypass Pipecat's web server
        logger.info(f"🎯 Direct join mode: {args.room_url}")
        
        async def direct_join():
            async with aiohttp.ClientSession() as session:
                # Extract room URL and token
                room_url = args.room_url
                token = None
                
                # Parse token from URL if present
                if "?t=" in room_url:
                    room_url, token = room_url.split("?t=")
                
                logger.info(f"📍 Joining room: {room_url}")
                if token:
                    logger.info(f"🔑 Using token: {token[:20]}...")
                
                # Configure video based on service
                video_service = os.getenv("VIDEO_SERVICE", "none").lower()
                if video_service == "simli":
                    video_width, video_height = 512, 512
                    video_framerate = 30
                elif video_service == "heygen":
                    video_width, video_height = 1280, 720
                    video_framerate = 30
                else:
                    video_width, video_height = 1024, 576
                    video_framerate = 30
                
                room_meta = {
                    "room_url": room_url,
                    "room_name": extract_room_name(room_url),
                }
                
                # Audio output:
                # Keep enabled so the candidate hears Cartesia audio in the main Daily room.
                # Tavus still receives audio frames from the pipeline for lip-sync; the Tavus
                # start() guard above prevents the duplicate "stream" track creation error.
                video_service_type = os.getenv("VIDEO_SERVICE", "none").lower()
                audio_out = True
                
                logger.info(f"🔧 DailyTransport config: audio_out_enabled={audio_out} (VIDEO_SERVICE={video_service_type})")
                
                # Create Daily transport
                transport = DailyTransport(
                    room_url,
                    token,
                    "AI Interviewer Bot",
                    params=DailyParams(
                        audio_in_enabled=True,
                        audio_out_enabled=audio_out,  # Enabled for Cartesia audio delivery
                        video_out_enabled=True,
                        video_out_is_live=True,
                        video_out_width=video_width,
                        video_out_height=video_height,
                        video_out_framerate=video_framerate,
                        vad_analyzer=SileroVADAnalyzer(
                            params=VADParams(
                                confidence=0.8,    # Higher confidence threshold
                                start_secs=0.2,    # Quick to detect speech start
                                stop_secs=1.5,     # Wait 1.5 seconds of silence before responding
                                min_volume=0.5     # Minimum volume threshold
                            )
                        ),
                        transcription_enabled=False,  # Disabled - using OpenAI STT instead
                    ),
                )
                
                logger.info("🚀 Starting bot in direct join mode...")
                
                # Keep VIDEO_SERVICE enabled (e.g., tavus) for proper audio/video pipeline
                await run_bot(transport, session, room_meta)
        
        # Run the async function
        asyncio.run(direct_join())
    else:
        # Standard Pipecat Cloud mode - web server
        from pipecat.runner.run import main
        main()
