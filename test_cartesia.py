#!/usr/bin/env python3
"""
Quick test script for Cartesia TTS integration
Run this to verify Cartesia is working before deploying
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_cartesia():
    """Test Cartesia TTS service"""
    print("🧪 Testing Cartesia TTS Integration...")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        print("❌ CARTESIA_API_KEY not set in .env")
        return False
    
    print(f"✅ API Key found: {api_key[:15]}...")
    
    # Import and test service
    try:
        from server.services.cartesia_tts import CartesiaTTSService
        print("✅ CartesiaTTSService imported successfully")
    except Exception as e:
        print(f"❌ Failed to import CartesiaTTSService: {e}")
        return False
    
    # Initialize service
    try:
        voice_id = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")
        tts = CartesiaTTSService(
            api_key=api_key,
            voice_id=voice_id,
            model="sonic-english"
        )
        print(f"✅ Service initialized with voice: {voice_id}")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return False
    
    # Test generation
    try:
        print("\n🎤 Generating test speech...")
        test_text = "Hello, this is a test of the Cartesia text to speech system."
        
        audio_frames = []
        async for frame in tts.run_tts(test_text):
            audio_frames.append(frame)
        
        if audio_frames:
            print(f"✅ Generated {len(audio_frames)} audio frame(s)")
            print(f"   Total audio size: {sum(len(f.audio) if hasattr(f, 'audio') else 0 for f in audio_frames)} bytes")
            return True
        else:
            print("❌ No audio frames generated")
            return False
            
    except Exception as e:
        print(f"❌ Failed to generate speech: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("CARTESIA TTS INTEGRATION TEST")
    print("="*60 + "\n")
    
    result = asyncio.run(test_cartesia())
    
    print("\n" + "="*60)
    if result:
        print("✅ ALL TESTS PASSED - Cartesia TTS is working!")
        print("✅ Ready to deploy to EC2")
    else:
        print("❌ TESTS FAILED - Please fix errors before deploying")
    print("="*60 + "\n")

