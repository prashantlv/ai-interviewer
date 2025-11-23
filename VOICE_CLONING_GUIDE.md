# 🎤 Voice Cloning Guide

Backend utility for cloning voices using Cartesia Instant Voice Cloning API.

## 📁 Directory Structure

```
server/
├── clone_voice.py          # Voice cloning utility script
└── voice_samples/          # Store audio samples here
    ├── interviewer1.wav    # Your audio files (3-5 seconds each)
    ├── interviewer2.mp3
    └── README.md           # Instructions
```

## 🚀 Quick Start

### 1. Prepare Audio Sample

**Requirements:**
- **Duration:** 3-5 seconds (optimal)
- **Quality:** Clear recording, no background noise
- **Format:** WAV, MP3, FLAC, or OGG
- **Content:** Natural speech in target voice

**Tips:**
- Record in a quiet environment
- Use a good quality microphone
- Speak naturally and clearly
- 5 seconds gives best accuracy

### 2. Store Audio File

```bash
# Place your audio file in voice_samples/
cp /path/to/your/audio.wav server/voice_samples/interviewer.wav
```

### 3. Clone the Voice

```bash
cd server

# Clone voice (basic)
python clone_voice.py voice_samples/interviewer.wav "Professional Interviewer"

# Clone voice with language
python clone_voice.py voice_samples/alex.mp3 "Alex Voice" en

# List all cloned voices
python clone_voice.py --list
```

### 4. Use Cloned Voice

The script will output a `voice_id`. Use it in your `.env`:

```bash
# Update server/.env
CARTESIA_VOICE_ID=<your-cloned-voice-id>
```

---

## 📖 Usage Examples

### Example 1: Clone from WAV file

```bash
python clone_voice.py voice_samples/interviewer.wav "HR Interviewer"
```

**Output:**
```
📁 File: voice_samples/interviewer.wav
📊 Size: 0.42 MB
🎤 Cloning voice: HR Interviewer
🌐 Language: en

============================================================
✅ SUCCESS! Voice cloned successfully!
============================================================
🆔 Voice ID: abc123xyz789
📝 Name: HR Interviewer
🌐 Language: en
🎯 Mode: similarity

💡 To use this voice in interviews:
   Set CARTESIA_VOICE_ID=abc123xyz789 in your .env

🔧 Or update ai-interviewer.py to use this voice_id dynamically
============================================================
```

### Example 2: List All Voices

```bash
python clone_voice.py --list
```

**Output:**
```
📋 Fetching all voices from Cartesia...

✅ Found 15 voices:

================================================================================
🎤 Barbershop Man
   ID: a0e99841-438c-4a64-b679-ae501e7d6091
   Language: en
   Type: Public

🎤 Professional Interviewer
   ID: abc123xyz789
   Language: en
   Type: Custom (Cloned)

🎤 Friendly Woman
   ID: def456uvw012
   Language: en
   Type: Public
================================================================================
```

---

## 🔧 API Endpoints (for future integration)

The voice cloning service also provides REST API endpoints:

### Clone Voice (POST)
```http
POST http://localhost:8009/api/v1/voices/clone
Content-Type: multipart/form-data

audio_file: <file>
voice_name: "Interviewer Voice"
language: "en"
mode: "similarity"
enhance: false
```

### List Voices (GET)
```http
GET http://localhost:8009/api/v1/voices/
```

### Get Voice Details (GET)
```http
GET http://localhost:8009/api/v1/voices/{voice_id}
```

---

## 🎯 Voice Cloning Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `similarity` | Matches voice characteristics closely | **Recommended** - Best for interviews |
| `stability` | More stable but less accurate | Use if similarity is inconsistent |

---

## 🔍 Audio Requirements

### ✅ Good Audio Samples

```
✓ 3-5 seconds of clear speech
✓ Recorded in quiet environment
✓ Natural speaking pace
✓ Good microphone quality
✓ No background music/noise
✓ Single speaker
```

### ❌ Poor Audio Samples

```
✗ Too short (<2 seconds)
✗ Background noise/music
✗ Multiple speakers
✗ Echo or reverb
✗ Poor quality microphone
✗ Compressed/low bitrate
```

---

## 🧪 Testing Cloned Voice

After cloning, test it in an interview:

```bash
# 1. Update .env with new voice_id
echo "CARTESIA_VOICE_ID=your-cloned-voice-id" >> server/.env

# 2. Restart Docker containers
docker stop ai-interviewer-web ai-interviewer-worker
docker rm ai-interviewer-web ai-interviewer-worker

# 3. Rebuild and restart
docker build -f Dockerfile.web -t ai-interviewer-web:latest .
docker build -f Dockerfile.worker -t ai-interviewer-worker:latest .

docker run -d --name ai-interviewer-web --network host \
  --env-file server/.env --env-file web_server/.env \
  --restart unless-stopped ai-interviewer-web:latest

docker run -d --name ai-interviewer-worker --network host \
  --env-file server/.env --env-file web_server/.env \
  --restart unless-stopped ai-interviewer-worker:latest

# 4. Schedule test interview and listen to the cloned voice!
```

---

## 🎬 Future Plans

### Phase 1 (Current): Manual Cloning ✅
- Store audio samples in project
- Run backend script to clone
- Manually update voice_id

### Phase 2 (Future): Automatic Cloning 🔄
- Extract audio from uploaded videos
- Auto-clone when creating interviewer profile
- Store multiple voices per organization
- Dynamic voice selection per interview

### Phase 3 (Future): Advanced Features 🚀
- Voice library management UI
- A/B testing different voices
- Voice analytics (which performs best)
- Emotion/tone adjustment per interview type

---

## 📝 Database Schema

Cloned voices are stored in MongoDB:

```javascript
{
  "voice_id": "abc123xyz789",
  "name": "Professional Interviewer",
  "language": "en",
  "mode": "similarity",
  "enhanced": false,
  "owner_id": "user_123",  // Optional: for multi-tenant
  "created_at": ISODate("2025-11-23T..."),
  "metadata": {
    // Cartesia API response
  }
}
```

---

## 🔐 Security Notes

- ✅ Cloned voices are private to your Cartesia account
- ✅ Voice IDs are stored in database for reuse
- ✅ Audio files are NOT stored (only used for cloning)
- ⚠️  Keep your `CARTESIA_API_KEY` secure
- ⚠️  Voice cloning uses API credits

---

## 💰 Pricing

Cartesia Voice Cloning:
- **Instant Cloning:** Free with API key
- **Usage:** Standard TTS pricing (1.5 credits/char)
- **No training cost** for instant cloning

---

## 🆘 Troubleshooting

### Error: "CARTESIA_API_KEY not configured"
```bash
# Make sure your .env has:
echo "CARTESIA_API_KEY=sk_car_..." >> server/.env
```

### Error: "Audio file too small"
```
✗ Audio must be at least 3 seconds
✓ Recommended: 5 seconds for best results
```

### Error: "Voice cloning failed"
```bash
# Check audio format is supported
file voice_samples/your-audio.wav

# Try with enhance=True if noisy
# Edit clone_voice.py line 50: enhance=True
```

### Cloned voice doesn't sound right
```
✓ Try recording a longer sample (5 seconds)
✓ Ensure audio is clear and high quality
✓ Try mode="stability" instead of "similarity"
✓ Record in quieter environment
```

---

## 📞 Support

For issues:
1. Check logs: `docker logs ai-interviewer-worker | grep -i cartesia`
2. Verify API key is valid
3. Test with Cartesia's default voices first
4. Check audio file is valid format

---

**Status:** ✅ Backend implementation complete  
**Next:** Extract audio from video and auto-clone (future)

