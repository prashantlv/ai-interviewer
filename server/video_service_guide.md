# 🎬 Video Service Configuration Guide

## 📊 Available Video Options

| Service | Resolution | Latency | Best For | Features | Cost |
|---------|------------|---------|----------|----------|------|
| **None** | N/A | Lowest | Audio-only, Testing | Basic | Free |
| **Robot Animation** | 1024x576 | Very Low | Basic visual feedback | Animation | Free |
| **Simli** | 512x512 | Very Low | Real-time conversations | WebRTC | Medium |
| **HeyGen** | 1280x720 | Low | Interactive conversations | VAD, Interruptions | Medium |
| **Tavus** | 1024x576 | Low | Professional interviews | Realistic | Higher |

## ⚙️ Configuration Options

### 🤖 Robot Animation (Default)
```bash
# In .env file:
VIDEO_SERVICE=none
```
- Uses static robot sprites with talking animation
- No additional costs
- Perfect for development and testing

### 🎯 Simli (Recommended for Real-time)
```bash
# In .env file:
VIDEO_SERVICE=simli
SIMLI_API_KEY=3fj43o53gdc0he8m3hxc1if
SIMLI_FACE_ID=dd10cb5a-d31d-4f12-b69f-6db3383c006e
```
- WebRTC streaming with very low latency
- 512x512 optimized resolution
- Perfect for real-time conversations
- Requires: `pip install pipecat-ai[simli]`

### 🎭 HeyGen (Interactive Conversations)
```bash
# In .env file:
VIDEO_SERVICE=heygen
HEYGEN_API_KEY=ZmRmOTQwYjM1MDkwNGYzZmI5YzY0M2E4YTRkZDc2YzYtMTc1NzY5MzM2OA==
HEYGEN_AVATAR_ID=Shawn_Therapist_public
```
- Interactive AI-powered avatars
- Voice activity detection
- Smart interruption handling
- Natural conversation flow
- Requires: `pip install pipecat-ai[heygen]`

### 👤 Tavus (Professional Interviews)
```bash
# In .env file:
VIDEO_SERVICE=tavus
TAVUS_API_KEY=0c5549cd455c4c7983c6b20d53f52aba
TAVUS_REPLICA_ID=r92debe21318
```
- High-quality realistic avatars
- Perfect lip sync
- Best for professional interviews
- Requires: `pip install pipecat-ai[tavus]`

## 🚀 Quick Switch Commands

**Test with Simli:**
```bash
# Edit .env: VIDEO_SERVICE=simli
python ai-interviewer.py --transport daily
```

**Test with HeyGen:**
```bash
# Edit .env: VIDEO_SERVICE=heygen
python ai-interviewer.py --transport daily
```

**Test with Tavus:**
```bash
# Edit .env: VIDEO_SERVICE=tavus  
python ai-interviewer.py --transport daily
```

**Test without video:**
```bash
# Edit .env: VIDEO_SERVICE=none
python ai-interviewer.py --transport daily
```

## 🔧 Technical Details

### Simli Configuration
- **Session Length:** 20 minutes max
- **Idle Timeout:** 60 seconds
- **Audio Sync:** Enabled
- **Silence Handling:** Video continues during silence
- **Network:** Standard networks (TURN server disabled)

### HeyGen Configuration
- **Resolution:** 1280x720 (HD quality)
- **Avatar:** Shawn_Therapist_public (default)
- **Features:** Voice activity detection, interruption handling
- **Audio Sync:** Perfect lip-sync with generated speech
- **Session Management:** Automatic avatar lifecycle management

### Tavus Configuration  
- **Resolution:** 1024x576 (Daily optimized)
- **Integration:** Video layer for bot audio
- **Latency:** Optimized for quality
- **Use Case:** Professional interviews

### Performance Tips
- **Simli:** Use for real-time demos and casual conversations
- **HeyGen:** Use for interactive conversations with smart features
- **Tavus:** Use for formal interviews and presentations
- **Robot:** Use for development and audio-focused interactions

Choose the video service that best fits your use case and budget!
