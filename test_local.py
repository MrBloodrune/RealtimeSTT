#!/usr/bin/env python3
"""
Test RealtimeSTT locally with microphone
This helps verify the installation is working before testing streaming
"""

from RealtimeSTT import AudioToTextRecorder

def process_text(text):
    print(f"Transcribed: {text}")

if __name__ == '__main__':
    print("Testing RealtimeSTT with local microphone...")
    print("This test uses the default microphone input")
    print("Say something after you see 'Listening...'\n")
    
    try:
        recorder = AudioToTextRecorder(
            model="tiny.en",
            language="en",
            spinner=False,
            enable_realtime_transcription=True,
            on_realtime_transcription_update=lambda text: print(f"\rPartial: {text}", end="", flush=True),
            on_realtime_transcription_stabilized=lambda text: print(f"\rStabilized: {text}", end="", flush=True)
        )
        
        print("Listening... (Press Ctrl+C to stop)")
        
        while True:
            text = recorder.text(process_text)
            
    except KeyboardInterrupt:
        print("\n\nTest stopped")
        recorder.shutdown()
    except Exception as e:
        print(f"Error: {e}")
        print("\nIf this fails, the issue is with RealtimeSTT setup, not the streaming code")