#!/usr/bin/env python3
"""
Test Edge TTS to understand how it works
"""

import asyncio
import edge_tts
import pyaudio
import io

async def test_edge_tts():
    """Test Edge TTS generation"""
    
    text = "Hello! This is a test of Edge TTS. It should sound much more natural than simple tones."
    
    # Create a communication object
    communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
    
    # Generate audio
    print(f"Generating TTS for: {text}")
    
    # Collect audio chunks
    audio_chunks = []
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
            print(".", end="", flush=True)
    
    print("\nTTS generation complete!")
    
    # Combine all chunks
    audio_data = b''.join(audio_chunks)
    print(f"Total audio size: {len(audio_data)} bytes")
    
    # Save to file for testing
    with open("test_output.mp3", "wb") as f:
        f.write(audio_data)
    print("Saved to test_output.mp3")
    
    # Also list available voices
    print("\nAvailable voices:")
    voices = await edge_tts.list_voices()
    english_voices = [v for v in voices if v["Locale"].startswith("en-")]
    
    print("\nEnglish voices:")
    for voice in english_voices[:5]:  # Show first 5
        print(f"  - {voice['ShortName']}: {voice['Gender']}")

if __name__ == "__main__":
    asyncio.run(test_edge_tts())