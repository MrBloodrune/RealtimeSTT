#!/usr/bin/env python3
"""
Personal Assistant Client with Fixed Audio Playback
Properly handles binary WebSocket messages
"""

import asyncio
import websockets
import pyaudio
import json
import sys
import threading
import queue
from datetime import datetime

# Audio configuration (must match server)
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

class AssistantClient:
    def __init__(self, server_url="ws://localhost:9999"):
        self.server_url = server_url
        self.audio = pyaudio.PyAudio()
        self.mic_stream = None
        self.speaker_stream = None
        self.websocket = None
        self.running = False
        
        # Queues
        self.mic_queue = queue.Queue()
        self.speaker_queue = queue.Queue()
        
        # Audio response handling
        self.receiving_audio = False
        self.audio_buffer = bytearray()
        
    def list_audio_devices(self):
        """List available audio devices"""
        print("\nAvailable audio devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            print(f"  Device {i}: {info['name']}")
            print(f"    - Input channels: {info['maxInputChannels']}")
            print(f"    - Output channels: {info['maxOutputChannels']}")
    
    def start_audio_devices(self, input_device=None, output_device=None):
        """Start microphone and speaker streams"""
        # Start microphone
        try:
            self.mic_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=input_device
            )
            print("✓ Microphone started successfully")
        except Exception as e:
            print(f"✗ Error starting microphone: {e}")
            raise
        
        # Start speaker
        try:
            self.speaker_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
                output_device_index=output_device
            )
            print("✓ Speaker started successfully")
        except Exception as e:
            print(f"✗ Error starting speaker: {e}")
            raise
    
    def audio_capture_thread(self):
        """Capture audio from microphone in a separate thread"""
        print("Audio capture thread started")
        while self.running:
            try:
                # Read audio chunk from microphone
                data = self.mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.mic_queue.put(data)
            except Exception as e:
                if self.running:
                    print(f"Audio capture error: {e}")
                break
    
    def audio_playback_thread(self):
        """Play audio to speaker in a separate thread"""
        print("Audio playback thread started")
        while self.running:
            try:
                # Get audio data from queue
                audio_data = self.speaker_queue.get(timeout=0.1)
                if audio_data:
                    self.speaker_stream.write(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"Audio playback error: {e}")
    
    async def send_audio(self):
        """Send audio data to server"""
        chunks_sent = 0
        while self.running:
            try:
                # Get audio from queue (with timeout to allow checking self.running)
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.mic_queue.get, True, 0.1
                )
                
                # Send to server as binary
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
        """Receive and process messages from server"""
        try:
            async for message in self.websocket:
                # Check message type first
                if isinstance(message, bytes):
                    # Binary message - should be audio data
                    if self.receiving_audio:
                        self.audio_buffer.extend(message)
                        # Show progress
                        print(f"\r  [Audio buffer: {len(self.audio_buffer)} bytes]", end="", flush=True)
                    else:
                        print(f"\n[Unexpected binary data: {len(message)} bytes]")
                        
                elif isinstance(message, str):
                    # Text message - should be JSON
                    try:
                        data = json.loads(message)
                        msg_type = data.get('type')
                        
                        if msg_type == 'connected':
                            print(f"\n✓ Connected to server")
                            print(f"  Mode: {data.get('mode', 'unknown')}")
                            print(f"  LLM: {'available' if data.get('llm_available') else 'not available'}")
                            print(f"  TTS: {'available' if data.get('tts_available') else 'not available'}")
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
                            
                        elif msg_type == 'audio_response':
                            # Start receiving audio
                            self.receiving_audio = True
                            self.audio_buffer = bytearray()
                            sample_rate = data.get('sample_rate', 16000)
                            length = data.get('length', 0)
                            print(f"  [Receiving audio: {length} samples at {sample_rate}Hz]")
                            
                        elif msg_type == 'audio_end':
                            # Process received audio
                            print()  # New line after progress
                            if self.audio_buffer:
                                print(f"  [Playing audio: {len(self.audio_buffer)} bytes]")
                                # Convert bytearray to bytes and queue for playback
                                audio_bytes = bytes(self.audio_buffer)
                                # Split into chunks for smooth playback
                                for i in range(0, len(audio_bytes), CHUNK_SIZE):
                                    chunk = audio_bytes[i:i + CHUNK_SIZE]
                                    self.speaker_queue.put(chunk)
                            self.receiving_audio = False
                            self.audio_buffer = bytearray()
                            print("-"*50)
                            
                        elif msg_type == 'mode_change':
                            mode = data.get('mode')
                            message_text = data.get('message', '')
                            print(f"\n>>> Mode changed to: {mode} - {message_text}")
                            print("-"*50)
                            
                        elif msg_type == 'recording_start':
                            print("\n[Recording...]", end="", flush=True)
                            
                        elif msg_type == 'recording_stop':
                            print(" [Processing...]", end="", flush=True)
                            
                        elif msg_type == 'tts_error':
                            print(f"\n[TTS Error: {data.get('error', 'Unknown')}]")
                            
                    except json.JSONDecodeError as e:
                        print(f"\nJSON decode error: {e}")
                        print(f"Message preview: {message[:100]}...")
                        
        except websockets.exceptions.ConnectionClosed:
            print("\n\n✗ Connection to server lost")
        except Exception as e:
            print(f"\nConnection error: {e}")
    
    async def run(self, input_device=None, output_device=None):
        """Main client loop"""
        print(f"Connecting to {self.server_url}...")
        
        try:
            # Configure WebSocket to handle large messages
            async with websockets.connect(
                self.server_url, 
                max_size=10*1024*1024,
                compression=None  # Disable compression for binary data
            ) as websocket:
                self.websocket = websocket
                self.running = True
                
                # Start audio devices
                self.start_audio_devices(input_device, output_device)
                
                # Start audio threads
                capture_thread = threading.Thread(target=self.audio_capture_thread)
                capture_thread.daemon = True
                capture_thread.start()
                
                playback_thread = threading.Thread(target=self.audio_playback_thread)
                playback_thread.daemon = True
                playback_thread.start()
                
                print("\n" + "="*50)
                print("Personal Assistant Client (with Audio)")
                print("="*50)
                print("Voice Commands:")
                print("  • Say 'assistant mode' to enable LLM + TTS")
                print("  • Say 'transcription mode' to disable assistant")
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
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
        self.audio.terminate()
        print("\nAudio devices closed")

def main():
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python assistant_client_audio_fixed.py [server_url] [input_device] [output_device]")
            print("\nExamples:")
            print("  python assistant_client_audio_fixed.py")
            print("  python assistant_client_audio_fixed.py ws://192.168.1.100:9999")
            print("  python assistant_client_audio_fixed.py ws://localhost:9999 1 2")
            sys.exit(0)
        server_url = sys.argv[1]
    else:
        server_url = "ws://localhost:9999"
    
    input_device = None
    output_device = None
    
    if len(sys.argv) > 2:
        try:
            input_device = int(sys.argv[2])
        except ValueError:
            print("Invalid input device index")
            sys.exit(1)
    
    if len(sys.argv) > 3:
        try:
            output_device = int(sys.argv[3])
        except ValueError:
            print("Invalid output device index")
            sys.exit(1)
    
    # Create and run client
    client = AssistantClient(server_url)
    
    # List devices if no device specified
    if (input_device is None or output_device is None) and len(sys.argv) <= 3:
        client.list_audio_devices()
        print("\nUsing default audio devices")
        print("To use specific devices, run:")
        print(f"  python {sys.argv[0]} {server_url} <input_device> <output_device>\n")
    
    try:
        asyncio.run(client.run(input_device, output_device))
    except KeyboardInterrupt:
        print("\n\nShutting down...")

if __name__ == "__main__":
    main()