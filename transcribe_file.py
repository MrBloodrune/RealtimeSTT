#!/usr/bin/env python3
"""
Simple script to transcribe audio files using RealtimeSTT
Processes files locally without needing the WebSocket server
"""

from RealtimeSTT import AudioToTextRecorder
import sys
import wave
import numpy as np
from scipy import signal

def transcribe_audio_file(file_path, model="medium.en"):
    """Transcribe an audio file using RealtimeSTT"""
    
    print(f"Loading model: {model}")
    recorder = AudioToTextRecorder(
        model=model,
        language="en",
        use_microphone=False,
        spinner=False,
        enable_realtime_transcription=False
    )
    
    print(f"Processing file: {file_path}")
    
    # Read audio file
    with wave.open(file_path, 'rb') as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        audio_data = wav_file.readframes(wav_file.getnframes())
        
        print(f"Audio info: {channels} channels, {framerate}Hz, {sample_width*8}-bit")
        
        # Convert to 16kHz mono 16-bit if needed
        if sample_width == 2:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
        else:
            raise ValueError("Only 16-bit audio supported")
        
        # Convert to mono
        if channels == 2:
            audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
        
        # Resample to 16kHz
        if framerate != 16000:
            print(f"Resampling from {framerate}Hz to 16000Hz...")
            num_samples = int(len(audio_array) * 16000 / framerate)
            audio_array = signal.resample(audio_array, num_samples).astype(np.int16)
        
        # Feed audio to recorder
        print("Transcribing...")
        recorder.feed_audio(audio_array.tobytes())
        
        # Get transcription
        transcription = recorder.text()
        
        print("\n" + "="*50)
        print("TRANSCRIPTION:")
        print("="*50)
        print(transcription)
        print("="*50)
        
        return transcription

def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe_file.py <audio-file> [model]")
        print("Example: python transcribe_file.py recording.wav")
        print("Example: python transcribe_file.py recording.wav tiny.en")
        print("\nAvailable models: tiny.en, base.en, small.en, medium.en, large-v2")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "medium.en"
    
    try:
        transcribe_audio_file(audio_file, model)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()