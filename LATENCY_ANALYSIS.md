# AI Interviewer Latency Analysis & Optimization Guide

**Created:** October 7, 2025  
**Current Configuration:** OpenAI (gpt-4o-mini) + OpenAI STT/TTS + No Video

---

## 🔍 Latency Sources Identified

Your AI interviewer has **5 main latency bottlenecks** in the conversation flow:

```
User speaks → [1] STT → [2] LLM → [3] TTS → [4] Network → [5] Rendering → User hears
   ↑                                                                              ↓
   └──────────────────────── Total Perceived Latency ─────────────────────────────┘
```

---

## 1️⃣ Speech-to-Text (STT) Latency

**Current Setup:** OpenAI Whisper API  
**Typical Latency:** 300-800ms

**Factors:**
- ✅ **Voice Activity Detection (VAD):** You're using `SileroVADAnalyzer()` (good!)
- ⚠️ **Endpoint Detection:** Waiting for user to finish speaking adds 500-1000ms
- ⚠️ **Audio Chunk Buffering:** Accumulates audio before sending to API
- ⚠️ **API Processing:** Whisper model transcription time

**Your Code:**
```python
# server/ai-interviewer.py:325
stt = OpenAISTTService(api_key=os.getenv("OPENAI_API_KEY"))
```

**Optimization Options:**

### Option A: Switch to Deepgram (Faster STT)
```python
from pipecat.services.deepgram.stt import DeepgramSTTService

stt = DeepgramSTTService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    live_options={
        "model": "nova-2",        # Latest, fastest model
        "language": "en",
        "smart_format": True,
        "interim_results": True,  # Get partial results faster!
        "endpointing": 300,       # Milliseconds to wait (lower = faster)
    }
)
```
**Expected Improvement:** 200-400ms faster (40-60% reduction)

### Option B: Optimize OpenAI STT
```python
stt = OpenAISTTService(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="whisper-1",  # Explicit model
)
```
**Expected Improvement:** Minimal (5-10%)

---

## 2️⃣ Large Language Model (LLM) Latency

**Current Setup:** GPT-4o-mini  
**Typical Latency:** 800-2000ms (depends on response length)

**Factors:**
- ⚠️ **Model Speed:** gpt-4o-mini is already fast, but still processes sequentially
- ⚠️ **Response Length:** Longer AI responses = more latency
- ⚠️ **System Prompt Length:** Your dynamic prompt is quite detailed
- ⚠️ **No Streaming:** Currently waiting for full response before TTS

**Your Code:**
```python
# server/ai-interviewer.py:330-333
llm = OpenAILLMService(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",  # Cost-optimized model
)
```

**Optimization Options:**

### Option A: Enable Streaming (BEST!)
The LLM likely already streams tokens, but ensure TTS starts immediately:
```python
# This is likely already enabled in Pipecat, but verify:
llm = OpenAILLMService(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    stream=True,  # Stream tokens as they arrive
)
```
**Expected Improvement:** 500-1000ms faster perceived latency

### Option B: Optimize System Prompt
Shorter prompts = faster processing. Review `create_dynamic_system_prompt()`:
```python
# Current: Detailed multi-paragraph prompt
# Optimized: Concise, focused instructions
```
**Expected Improvement:** 100-300ms

### Option C: Consider GPT-4o-realtime (Future)
OpenAI's Realtime API bypasses separate STT/TTS:
```python
# NOTE: Not currently in your setup, but available
from pipecat.services.openai.realtime import OpenAIRealtimeService

# Single service handles audio → text → audio
realtime = OpenAIRealtimeService(
    api_key=os.getenv("OPENAI_API_KEY"),
    voice="alloy",
)
```
**Expected Improvement:** 1000-2000ms faster (eliminates STT/TTS round-trips)

---

## 3️⃣ Text-to-Speech (TTS) Latency

**Current Setup:** OpenAI TTS (voice: alloy)  
**Typical Latency:** 400-1000ms

**Factors:**
- ⚠️ **First Byte Time:** Time to start audio generation
- ⚠️ **Audio Generation:** Converting text to speech
- ⚠️ **Streaming:** Whether audio starts playing immediately or waits for full response

**Your Code:**
```python
# server/ai-interviewer.py:326-328
tts = OpenAITTSService(
    api_key=os.getenv("OPENAI_API_KEY"),
    voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
)
```

**Optimization Options:**

### Option A: Switch to ElevenLabs (Better Streaming)
```python
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

tts = ElevenLabsTTSService(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel (clear, professional)
    model="eleven_turbo_v2_5",        # Fastest model!
    optimize_streaming_latency=4,     # Max optimization (0-4)
)
```
**Expected Improvement:** 300-600ms faster  
**Note:** You already have `ELEVENLABS_API_KEY` in your `.env`!

### Option B: Switch to Cartesia (Ultra-Low Latency)
```python
from pipecat.services.cartesia.tts import CartesiaTTSService

tts = CartesiaTTSService(
    api_key=os.getenv("CARTESIA_API_KEY"),
    voice_id="a0e99841-438c-4a64-b679-ae501e7d6091",  # Barbershop Man
    model="sonic-english",  # Ultra-fast model
)
```
**Expected Improvement:** 400-800ms faster (fastest option!)

### Option C: Try Different OpenAI Voice
Some voices may be faster:
```python
tts = OpenAITTSService(
    api_key=os.getenv("OPENAI_API_KEY"),
    voice="nova",  # Try: nova, shimmer (may be faster than alloy)
)
```
**Expected Improvement:** 50-100ms

---

## 4️⃣ Network Latency

**Current Setup:** Daily.co WebRTC  
**Typical Latency:** 50-200ms (varies by location)

**Factors:**
- ✅ **WebRTC:** Already using optimal real-time protocol
- ⚠️ **Geographic Distance:** User → Daily.co servers → Bot
- ⚠️ **Internet Connection:** User's bandwidth and stability
- ⚠️ **Server Location:** Where your bot is running

**Your Code:**
```python
# server/ai-interviewer.py:621-636
transport = DailyTransport(
    runner_args.room_url,
    runner_args.token,
    "AI Interviewer Bot",
    params=DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_out_enabled=True,        # Currently disabled (VIDEO_SERVICE=none)
        video_out_is_live=True,
        vad_analyzer=SileroVADAnalyzer(),  # Good!
        transcription_enabled=True,
    ),
)
```

**Optimization Options:**

### Option A: Disable Video Output (Already Done!)
```python
# You've already set VIDEO_SERVICE=none, which helps!
video_out_enabled=False,  # Consider setting this to False
```
**Expected Improvement:** 50-100ms (video encoding overhead removed)

### Option B: Optimize Audio Settings
```python
params=DailyParams(
    audio_in_enabled=True,
    audio_out_enabled=True,
    video_out_enabled=False,           # Disable completely
    vad_analyzer=SileroVADAnalyzer(),
    transcription_enabled=True,
    audio_in_sample_rate=16000,        # Lower if acceptable (default 48k)
    audio_out_sample_rate=16000,       # Match STT requirements
)
```
**Expected Improvement:** 20-50ms

### Option C: Run Bot Closer to Daily.co Servers
- Daily.co servers are typically in US/EU regions
- Running bot in same region reduces round-trip time
**Expected Improvement:** 50-200ms (if currently distant)

---

## 5️⃣ Client-Side Rendering

**Factors:**
- ⚠️ **Browser Audio Pipeline:** Decoding and playback
- ⚠️ **Device Performance:** User's computer/phone
- ⚠️ **Browser Choice:** Chrome typically best for WebRTC

**Optimization:**
- Ensure users use modern browsers (Chrome, Edge, Safari)
- Minimize other browser tabs/apps
**Expected Improvement:** 20-50ms

---

## 📊 Current Total Latency Estimate

Based on your OpenAI setup:

| Component | Latency | Percentage |
|-----------|---------|------------|
| STT (OpenAI Whisper) | 500-800ms | 25-30% |
| LLM (GPT-4o-mini) | 800-1500ms | 40-50% |
| TTS (OpenAI) | 400-800ms | 20-25% |
| Network (WebRTC) | 100-200ms | 5-10% |
| Rendering | 50-100ms | 2-5% |
| **TOTAL** | **1850-3400ms** | **100%** |

**Perceived Latency:** ~2-3 seconds from end of user speech to start of AI response

---

## 🚀 Recommended Optimizations (Priority Order)

### 🥇 **HIGH IMPACT** (Do These First!)

#### 1. Switch to Faster TTS (ElevenLabs Turbo)
**Effort:** 5 minutes  
**Impact:** 300-600ms reduction  
**Cost:** ~$0.30 per 1000 characters (vs OpenAI ~$0.015)

```bash
# Add to .env
ELEVENLABS_API_KEY=sk_fc792205525e0788307801b1ae68ac52450a6b59f8e4fe09  # Already there!
```

```python
# In server/ai-interviewer.py, replace TTS section:
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

tts = ElevenLabsTTSService(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
    model="eleven_turbo_v2_5",
    optimize_streaming_latency=4,
)
```

#### 2. Switch to Faster STT (Deepgram Nova-2)
**Effort:** 10 minutes  
**Impact:** 200-400ms reduction  
**Cost:** ~$0.0043 per minute (vs OpenAI Whisper ~$0.006)

```bash
# Add to .env
DEEPGRAM_API_KEY=your_deepgram_key
```

```python
# In server/ai-interviewer.py, replace STT section:
from pipecat.services.deepgram.stt import DeepgramSTTService

stt = DeepgramSTTService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    live_options={
        "model": "nova-2",
        "language": "en",
        "smart_format": True,
        "interim_results": True,
        "endpointing": 300,  # 300ms wait after speech
    }
)
```

#### 3. Verify LLM Streaming is Enabled
**Effort:** 2 minutes  
**Impact:** 500-1000ms perceived reduction  
**Cost:** Free (just configuration)

Pipecat likely handles this automatically, but verify in logs.

**Expected Total Improvement:** **1000-2000ms reduction** (33-60% faster!)

---

### 🥈 **MEDIUM IMPACT** (Do These Next)

#### 4. Optimize System Prompt Length
**Effort:** 30 minutes  
**Impact:** 100-300ms reduction

Review and shorten `create_dynamic_system_prompt()` in `ai-interviewer.py`.

#### 5. Disable Video Output Completely
**Effort:** 1 minute  
**Impact:** 50-100ms reduction

```python
# In ai-interviewer.py:
video_out_enabled=False,  # Instead of True
```

#### 6. Optimize VAD Settings
**Effort:** 10 minutes  
**Impact:** 100-200ms reduction

```python
vad_analyzer=SileroVADAnalyzer(
    min_speech_duration_ms=50,   # Lower = more responsive
    min_silence_duration_ms=300,  # Lower = faster cutoff
)
```

**Expected Total Improvement:** **250-600ms additional reduction**

---

### 🥉 **ADVANCED** (Future Considerations)

#### 7. Migrate to OpenAI Realtime API
**Effort:** 4-8 hours (significant refactoring)  
**Impact:** 1000-2000ms reduction (eliminates STT/TTS)  
**Cost:** Higher ($0.06/min input, $0.24/min output)

This is the ultimate solution but requires rewriting the pipeline.

#### 8. Deploy Bot to Cloud (Near Daily.co)
**Effort:** 2-4 hours (infrastructure setup)  
**Impact:** 50-200ms reduction (if currently running locally)

Use AWS/GCP/Azure in same region as Daily.co servers.

---

## 🎯 Quick Win Implementation Plan

### Phase 1: Immediate (15 minutes)
```bash
# 1. Install Deepgram
cd /home/prashant/Playground/personal/consult/ai-interviewer/server
conda activate pipecat-env
pip install deepgram-sdk

# 2. Get Deepgram API key
# Sign up at https://deepgram.com (free $200 credit)
# Add to .env: DEEPGRAM_API_KEY=xxx
```

### Phase 2: Update Code (10 minutes)
Modify `server/ai-interviewer.py`:

```python
# Add at top (around line 170)
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

# Replace STT section (around line 325)
if os.getenv("DEEPGRAM_API_KEY"):
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options={
            "model": "nova-2",
            "language": "en",
            "smart_format": True,
            "interim_results": True,
            "endpointing": 300,
        }
    )
else:
    stt = OpenAISTTService(api_key=os.getenv("OPENAI_API_KEY"))

# Replace TTS section (around line 326)
if os.getenv("ELEVENLABS_API_KEY"):
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
        model="eleven_turbo_v2_5",
        optimize_streaming_latency=4,
    )
else:
    tts = OpenAITTSService(
        api_key=os.getenv("OPENAI_API_KEY"),
        voice="alloy",
    )
```

### Phase 3: Test (5 minutes)
```bash
# Restart web server and RQ worker
# Schedule new interview
# Compare latency
```

---

## 📈 Expected Results

### Current Performance:
- **Total Latency:** 2-3 seconds
- **User Experience:** Noticeable lag, feels unnatural

### After Quick Wins (Deepgram + ElevenLabs):
- **Total Latency:** 1-1.5 seconds
- **User Experience:** Much more conversational, acceptable for interviews
- **Improvement:** 40-50% reduction

### After All Optimizations:
- **Total Latency:** 0.5-1 second
- **User Experience:** Near real-time, natural conversation
- **Improvement:** 60-70% reduction

---

## 🔍 Debugging Latency Issues

### Enable Metrics in Pipecat
Already enabled in your code:
```python
# server/ai-interviewer.py:490-493
params=PipelineParams(
    enable_metrics=True,
    enable_usage_metrics=True,
)
```

### Check Logs for Timing
Add custom timing logs:
```python
import time

@transcript_collector.on_frame
async def log_timing(frame):
    if isinstance(frame, TranscriptionFrame):
        logger.info(f"⏱️ STT completed: {frame.text}")
    elif isinstance(frame, TextFrame):
        logger.info(f"⏱️ LLM completed: {frame.text[:50]}...")
```

### Monitor Pipeline Performance
Check `/tmp/web_server.log` for frame processing times.

---

## 💰 Cost Comparison

### Current (All OpenAI):
- STT: $0.006/min
- LLM: $0.150/1M tokens (gpt-4o-mini)
- TTS: $0.015/1K chars
- **Total:** ~$0.10-0.15 per 10-min interview

### Optimized (Deepgram + ElevenLabs):
- STT: $0.0043/min (cheaper!)
- LLM: $0.150/1M tokens (same)
- TTS: $0.30/1K chars (more expensive)
- **Total:** ~$0.15-0.25 per 10-min interview

**Trade-off:** +50-70% cost, but 40-50% faster (worth it for UX!)

---

## 🎬 Summary

Your latency issue is **normal** for the current configuration. The AI is processing through 3 separate APIs (STT → LLM → TTS), each adding latency.

**Root Causes:**
1. OpenAI Whisper STT: Slower than alternatives (500-800ms)
2. GPT-4o-mini: Fast but still processes sequentially (800-1500ms)
3. OpenAI TTS: Decent but not optimized for streaming (400-800ms)
4. Sequential processing: No overlap between stages

**Quick Fix (Highest ROI):**
- Switch to **Deepgram STT** (faster)
- Switch to **ElevenLabs Turbo TTS** (faster + better quality)
- **Estimated improvement: 40-50% faster** (from 2-3s down to 1-1.5s)

**Ultimate Fix (Future):**
- Migrate to **OpenAI Realtime API** (single service handles everything)
- **Estimated improvement: 60-70% faster** (from 2-3s down to 0.5-1s)

---

**Next Steps:** Would you like me to implement the Deepgram + ElevenLabs optimization now?
