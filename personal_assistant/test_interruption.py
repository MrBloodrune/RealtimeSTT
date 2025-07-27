#!/usr/bin/env python3
"""
Test script for interruptible TTS
Demonstrates various interruption scenarios
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from interruptible_tts_wrapper import InterruptibleTTSWrapper, InterruptReason
import time
import threading

def test_interruption_scenarios():
    """Test various interruption scenarios"""
    
    # Create TTS wrapper with callbacks
    def on_start():
        print("🔊 Speaking...")
    
    def on_end():
        print("🔇 Finished speaking")
    
    def on_interrupted(reason):
        print(f"⚡ Speech interrupted: {reason.value}")
    
    tts = InterruptibleTTSWrapper(
        voice="en-US-JennyNeural",
        on_speech_start=on_start,
        on_speech_end=on_end,
        on_speech_interrupted=on_interrupted
    )
    
    print("="*60)
    print("Interruptible TTS Test Suite")
    print("="*60)
    
    # Test 1: Basic speech
    print("\n1. Testing basic speech (should complete)...")
    tts.speak("Hello! This is a test of the interruptible text to speech system.")
    time.sleep(3)
    
    # Test 2: Manual interruption
    print("\n2. Testing manual interruption...")
    tts.speak("This is a longer message that will be interrupted after 2 seconds. Let me tell you about all the amazing features of this system, including real-time interruption, priority queuing, and natural conversation flow.")
    time.sleep(2)
    tts.interrupt(InterruptReason.MANUAL)
    time.sleep(1)
    
    # Test 3: Priority interruption
    print("\n3. Testing priority interruption...")
    tts.speak("This is a low priority message that takes a while to say.", priority=0)
    time.sleep(1)
    print("   Injecting high priority message...")
    tts.speak("URGENT: High priority alert!", priority=10)
    time.sleep(3)
    
    # Test 4: Queue management
    print("\n4. Testing queue management...")
    tts.speak("First message in queue", task_id="msg1")
    tts.speak("Second message in queue", task_id="msg2")
    tts.speak("Third message in queue", task_id="msg3")
    time.sleep(2)
    print("   Clearing queue...")
    tts.clear_queue()
    tts.interrupt()
    time.sleep(1)
    
    # Test 5: Simulated VAD interruption
    print("\n5. Testing simulated VAD interruption...")
    def simulate_vad():
        time.sleep(1.5)
        print("   🎙️ Simulating user speaking...")
        tts.interrupt(InterruptReason.VAD_DETECTED)
    
    tts.speak("The assistant is speaking when suddenly the user starts talking...")
    vad_thread = threading.Thread(target=simulate_vad)
    vad_thread.start()
    vad_thread.join()
    time.sleep(1)
    
    # Test 6: Rapid messages
    print("\n6. Testing rapid message handling...")
    for i in range(3):
        tts.speak(f"Quick message {i+1}", priority=i)
        time.sleep(0.5)
    
    time.sleep(3)
    
    print("\n" + "="*60)
    print("Test completed! Shutting down...")
    tts.shutdown()

if __name__ == "__main__":
    test_interruption_scenarios()