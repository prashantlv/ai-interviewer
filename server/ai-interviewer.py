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
- Realistic human avatar through Tavus (optional)
- Configurable AI backend (OpenAI + separate STT/TTS or Gemini with built-in TTS)
- Voice activity detection and transcription
- Cost-optimized with separate STT/TTS services

The bot runs as part of a pipeline that processes audio/video frames and manages
the conversation flow.
"""

import os
import sys
import aiohttp

from dotenv import load_dotenv
from loguru import logger
from PIL import Image
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    LLMRunFrame,
    OutputImageRawFrame,
    SpriteFrame,
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

load_dotenv(override=True)

# Load configuration from environment
BOT_IMPLEMENTATION = os.getenv("BOT_IMPLEMENTATION", "openai").lower()
USE_TAVUS = os.getenv("USE_TAVUS", "false").lower() == "true"

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

# Import Tavus services if enabled
if USE_TAVUS:
    try:
        from pipecat.services.tavus.video import TavusVideoService
    except ImportError:
        logger.error("Tavus integration not available. Install with: pip install pipecat-ai[tavus]")
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


async def run_bot(transport: BaseTransport, session: aiohttp.ClientSession):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Configurable AI backend (OpenAI or Gemini)
    - Separate STT/TTS services for cost optimization
    - Tavus video avatar (optional)
    - Language model integration
    - Animation processing (fallback)
    - RTVI event handling
    """

    logger.info(f"Starting AI Interviewer with {BOT_IMPLEMENTATION.upper()} backend")
    if USE_TAVUS:
        logger.info("Tavus video avatar enabled")

    # Initialize AI services based on configuration
    if BOT_IMPLEMENTATION == "openai":
        # OpenAI with separate STT/TTS for cost control
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY is required for OpenAI implementation")
            sys.exit(1)

        # Use OpenAI for STT, TTS, and LLM (can be configured separately)
        stt = OpenAISTTService(api_key=os.getenv("OPENAI_API_KEY"))
        tts = OpenAITTSService(
            api_key=os.getenv("OPENAI_API_KEY"),
            voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
        )
        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",  # Cost-optimized model
        )

        messages = [
            {
                "role": "system",
                "content": "You are an AI Interviewer, a professional and friendly assistant conducting job interviews. Your goal is to ask thoughtful questions, evaluate candidates, and create a comfortable interview environment. Keep your responses concise and professional. Always maintain a conversational tone while being thorough in your assessment. Start by introducing yourself and explaining the interview process.",
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

        messages = [
            {
                "role": "user",
                "content": "You are an AI Interviewer, a professional and friendly assistant conducting job interviews. Your goal is to ask thoughtful questions, evaluate candidates, and create a comfortable interview environment. Keep your responses concise and professional. Always maintain a conversational tone while being thorough in your assessment. Start by introducing yourself and explaining the interview process.",
            },
        ]

    # Set up conversation context and management
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)
    
    # Initialize RTVI processor
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
    
    # Initialize Tavus video service if enabled
    tavus = None
    if USE_TAVUS:
        if not os.getenv("TAVUS_API_KEY"):
            logger.error("TAVUS_API_KEY is required when USE_TAVUS=true")
            sys.exit(1)
        if not os.getenv("TAVUS_REPLICA_ID"):
            logger.error("TAVUS_REPLICA_ID is required when USE_TAVUS=true")
            sys.exit(1)
            
        tavus = TavusVideoService(
            api_key=os.getenv("TAVUS_API_KEY"),
            replica_id=os.getenv("TAVUS_REPLICA_ID"),
            session=session,
        )
        logger.info(f"Initialized Tavus with replica: {os.getenv('TAVUS_REPLICA_ID')}")
    
    # Initialize animation fallback (only if Tavus is not used)
    ta = None
    if not USE_TAVUS:
        ta = TalkingAnimation()

    # Build pipeline based on configuration
    if BOT_IMPLEMENTATION == "openai":
        # Pipeline for OpenAI with separate STT/TTS
        pipeline_processors = [
            transport.input(),
            stt,
            rtvi,
            context_aggregator.user(),
            llm,
            tts,
        ]
        
        # Add video processing
        if USE_TAVUS:
            pipeline_processors.append(tavus)
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
            rtvi,
            context_aggregator.user(),
            llm,
        ]
        
        # Add video processing (Tavus works with Gemini audio)
        if USE_TAVUS:
            pipeline_processors.append(tavus)
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

    # Queue initial frame if available
    if quiet_frame:
        await task.queue_frame(quiet_frame)

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        # Kick off the conversation
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, participant):
        logger.info(f"Client connected - AI Interviewer ({BOT_IMPLEMENTATION.upper()}) ready")
        await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""

    # Use aiohttp session for Tavus integration
    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            runner_args.room_url,
            runner_args.token,
            "AI Interviewer Bot",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                video_out_enabled=True,
                video_out_width=1024,
                video_out_height=576,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=True,
            ),
        )

        await run_bot(transport, session)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
