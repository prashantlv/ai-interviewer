# 🎤 Voice Samples Directory

Store your audio samples here for voice cloning.

## 📁 What to Put Here

Audio files (3-5 seconds each) for cloning interviewer voices.

### ✅ Good Audio Files

```
interviewer_professional.wav    - 5 sec, clear, professional tone
interviewer_friendly.mp3         - 4 sec, clear, friendly tone
hr_manager.wav                   - 5 sec, clear, authoritative
tech_lead.mp3                    - 4 sec, clear, technical
```

### 📝 Naming Convention

Use descriptive names:
- `{role}_{tone}.{format}`
- Examples:
  - `hr_professional.wav`
  - `tech_friendly.mp3`
  - `manager_authoritative.wav`

## 🎯 Audio Requirements

| Requirement | Specification |
|-------------|---------------|
| Duration | 3-5 seconds (optimal) |
| Format | WAV, MP3, FLAC, OGG |
| Quality | Clear, no background noise |
| Sample Rate | 16kHz+ recommended |
| Channels | Mono or Stereo |
| Max Size | 10MB |

## 🚀 Usage

```bash
# 1. Add your audio file here
cp /path/to/audio.wav voice_samples/

# 2. Clone the voice
cd ..  # Go to server/ directory
python clone_voice.py voice_samples/audio.wav "Voice Name"

# 3. Copy the voice_id and use it in .env
```

## 📖 Example

```bash
# Place audio file
cp ~/Downloads/interviewer.wav voice_samples/

# Clone voice
cd ..
python clone_voice.py voice_samples/interviewer.wav "Professional Interviewer"

# Output will give you voice_id to use in .env
```

## ⚠️ Important Notes

- **DO NOT commit audio files to git** (already in .gitignore)
- Keep audio files private
- Delete unused samples to save space
- Backup important voice_ids in .env or database

## 🔄 Current Audio Files

*List your audio files here (manually):*

```
interviewer1.wav        - Professional male voice (5 sec)
interviewer2.mp3        - Friendly female voice (4 sec)
```

---

**Need help?** Check `VOICE_CLONING_GUIDE.md` in project root.

