#!/usr/bin/env python3
"""
Voice Cloning Utility - Backend Script
Clone voices from audio files stored in voice_samples/

Usage:
    python clone_voice.py <audio_file> <voice_name>
    
Example:
    python clone_voice.py voice_samples/interviewer.wav "Professional Interviewer"
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add web_server to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent / "web_server"))

from services.voice_cloning_service import voice_cloning_service


async def clone_voice_from_file(audio_file_path: str, voice_name: str, language: str = "en"):
    """
    Clone a voice from an audio file
    
    Args:
        audio_file_path: Path to audio file (WAV/MP3, 3-5 seconds recommended)
        voice_name: Name for the cloned voice
        language: Language code (default: "en")
    
    Returns:
        Dict with voice_id and details
    """
    # Check if file exists
    if not os.path.exists(audio_file_path):
        print(f"❌ Error: File not found: {audio_file_path}")
        return None
    
    # Read audio file
    try:
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        file_size_mb = len(audio_data) / (1024 * 1024)
        print(f"📁 File: {audio_file_path}")
        print(f"📊 Size: {file_size_mb:.2f} MB")
        print(f"🎤 Cloning voice: {voice_name}")
        print(f"🌐 Language: {language}")
        print()
        
        # Clone voice
        result = await voice_cloning_service.clone_voice(
            audio_data=audio_data,
            voice_name=voice_name,
            language=language,
            mode="similarity",  # Best for matching voice characteristics
            enhance=False  # Set to True if audio is noisy
        )
        
        print("=" * 60)
        print("✅ SUCCESS! Voice cloned successfully!")
        print("=" * 60)
        print(f"🆔 Voice ID: {result['voice_id']}")
        print(f"📝 Name: {result['name']}")
        print(f"🌐 Language: {result['language']}")
        print(f"🎯 Mode: {result['mode']}")
        print()
        print("💡 To use this voice in interviews:")
        print(f"   Set CARTESIA_VOICE_ID={result['voice_id']} in your .env")
        print()
        print("🔧 Or update ai-interviewer.py to use this voice_id dynamically")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        print(f"❌ Error cloning voice: {str(e)}")
        return None


async def list_cloned_voices():
    """List all cloned voices from Cartesia"""
    try:
        print("📋 Fetching all voices from Cartesia...")
        voices = await voice_cloning_service.list_voices()
        
        if not voices:
            print("⚠️  No voices found or CARTESIA_API_KEY not set")
            return
        
        print(f"\n✅ Found {len(voices)} voices:\n")
        print("=" * 80)
        
        for voice in voices:
            voice_id = voice.get("id", "N/A")
            name = voice.get("name", "Unnamed")
            language = voice.get("language", "unknown")
            is_public = voice.get("is_public", False)
            
            print(f"🎤 {name}")
            print(f"   ID: {voice_id}")
            print(f"   Language: {language}")
            print(f"   Type: {'Public' if is_public else 'Custom (Cloned)'}")
            print()
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error listing voices: {str(e)}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("🎤 Voice Cloning Utility")
        print("=" * 60)
        print()
        print("Usage:")
        print("  Clone voice:")
        print("    python clone_voice.py <audio_file> <voice_name> [language]")
        print()
        print("  List all voices:")
        print("    python clone_voice.py --list")
        print()
        print("Examples:")
        print("  python clone_voice.py voice_samples/interviewer.wav 'Professional Interviewer'")
        print("  python clone_voice.py voice_samples/alex.mp3 'Alex Voice' en")
        print("  python clone_voice.py --list")
        print()
        print("Requirements:")
        print("  - Audio file: 3-5 seconds (optimal)")
        print("  - Clear recording without background noise")
        print("  - Supported formats: WAV, MP3, FLAC, OGG")
        print()
        print("Voice samples should be stored in: server/voice_samples/")
        print("=" * 60)
        sys.exit(1)
    
    # Check for --list flag
    if sys.argv[1] == "--list":
        asyncio.run(list_cloned_voices())
        sys.exit(0)
    
    # Clone voice
    audio_file = sys.argv[1]
    voice_name = sys.argv[2] if len(sys.argv) > 2 else "Cloned Voice"
    language = sys.argv[3] if len(sys.argv) > 3 else "en"
    
    result = asyncio.run(clone_voice_from_file(audio_file, voice_name, language))
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

