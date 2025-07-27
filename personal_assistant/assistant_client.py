#!/usr/bin/env python3
"""
Personal Assistant Client
Simple audio streaming client that works with assistant_server.py
Based on the existing client.py pattern
"""

import asyncio
import websockets
import pyaudio
import json
import sys
import threading
import queue
from datetime import datetime

# Audio configuration (must match server expectations)
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

class AssistantClient:
    def __init__(self, server_url="ws://localhost:9999"):
        self.server_url = server_url
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.websocket = None
        self.running = False
        self.audio_queue = queue.Queue()
        
    def list_audio_devices(self):
        """List available audio input devices"""
        print("\nAvailable audio input devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  Device {i}: {info['name']} (Channels: {info['maxInputChannels']})")
    
    def start_microphone(self, device_index=None):
        """Start capturing from microphone"""
        try:
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=device_index
            )
            print("✓ Microphone started successfully")
            return True
        except Exception as e:
            print(f"✗ Error starting microphone: {e}")
            return False
    
    def audio_capture_thread(self):
        """Capture audio from microphone in a separate thread"""
        print("Audio capture thread started")
        while self.running:
            try:
                # Read audio chunk from microphone
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_queue.put(data)
            except Exception as e:
                if self.running:
                    print(f"Audio capture error: {e}")
                break
    
    async def send_audio(self):
        """Send audio data to server"""
        chunks_sent = 0
        while self.running:
            try:
                # Get audio from queue (with timeout to allow checking self.running)
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.audio_queue.get, True, 0.1
                )
                
                # Send to server
                await self.websocket.send(data)
                chunks_sent += 1
                
                # Progress indicator every 100 chunks
                if chunks_sent % 100 == 0:
                    print(f".", end="", flush=True)
                    
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"\nError sending audio: {e}")
                break
    
    async def receive_messages(self):
        """Receive and display messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'connected':
                        print(f"\n✓ Connected to server")
                        print(f"  Mode: {data.get('mode', 'unknown')}")
                        print(f"  LLM: {'available' if data.get('llm_available') else 'not available'}")
                        print("\n" + "-"*50)
                        
                    elif msg_type == 'partial':
                        # Show partial transcription on same line
                        text = data.get('text', '')
                        print(f"\r[PARTIAL] {text}", end="", flush=True)
                        
                    elif msg_type == 'realtime':
                        # Clear the partial line
                        print("\r" + " "*80 + "\r", end="", flush=True)
                        
                    elif msg_type == 'fullSentence':
                        # Clear any partial text and show full sentence
                        print("\r" + " "*80 + "\r", end="", flush=True)
                        timestamp = data.get('timestamp', datetime.now().strftime("%H:%M:%S"))
                        text = data.get('text', '')
                        print(f"[{timestamp}] USER: {text}")
                        
                    elif msg_type == 'assistant_processing':
                        print("  [Assistant thinking...]")
                        
                    elif msg_type == 'assistant_response':
                        timestamp = data.get('timestamp', datetime.now().strftime("%H:%M:%S"))
                        text = data.get('text', '')
                        print(f"[{timestamp}] ASSISTANT: {text}")
                        print("-"*50)
                        
                    elif msg_type == 'mode_change':
                        mode = data.get('mode')
                        message = data.get('message', '')
                        print(f"\n>>> Mode changed to: {mode} - {message}")
                        print("-"*50)
                        
                    elif msg_type == 'recording_start':
                        print("\n[Recording...]", end="", flush=True)
                        
                    elif msg_type == 'recording_stop':
                        print(" [Processing...]", end="", flush=True)
                        
                except json.JSONDecodeError:
                    print(f"\nReceived non-JSON message: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("\n\n✗ Connection to server lost")
    
    async def run(self, device_index=None):
        """Main client loop"""
        print(f"Connecting to {self.server_url}...")
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                self.running = True
                
                # Start microphone
                if not self.start_microphone(device_index):
                    return
                
                # Start audio capture thread
                capture_thread = threading.Thread(target=self.audio_capture_thread)
                capture_thread.daemon = True
                capture_thread.start()
                
                print("\n" + "="*50)
                print("Personal Assistant Client")
                print("="*50)
                print("Voice Commands:")
                print("  • Say 'assistant mode' to enable LLM")
                print("  • Say 'transcription mode' to disable LLM")
                print("  • Say 'clear history' to reset conversation")
                print("\nPress Ctrl+C to exit")
                print("="*50 + "\n")
                print("Listening... (speak clearly into your microphone)")
                
                # Run send and receive tasks
                await asyncio.gather(
                    self.send_audio(),
                    self.receive_messages()
                )
                
        except Exception as e:
            print(f"\nConnection error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        print("\nAudio devices closed")

def main():
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python assistant_client.py [server_url] [device_index]")
            print("\nExamples:")
            print("  python assistant_client.py")
            print("  python assistant_client.py ws://192.168.1.100:9999")
            print("  python assistant_client.py ws://localhost:9999 1")
            sys.exit(0)
        server_url = sys.argv[1]
    else:
        server_url = "ws://localhost:9999"
    
    device_index = None
    if len(sys.argv) > 2:
        try:
            device_index = int(sys.argv[2])
        except ValueError:
            print("Invalid device index")
            sys.exit(1)
    
    # Create and run client
    client = AssistantClient(server_url)
    
    # List devices if no device specified
    if device_index is None and len(sys.argv) <= 2:
        client.list_audio_devices()
        print("\nUsing default audio input device")
        print("To use a specific device, run:")
        print(f"  python {sys.argv[0]} {server_url} <device_index>\n")
    
    try:
        asyncio.run(client.run(device_index))
    except KeyboardInterrupt:
        print("\n\nShutting down...")

if __name__ == "__main__":
    main()