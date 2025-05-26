#!/usr/bin/env python3
"""
Minimal WebSocket client for audio streaming
Captures audio from microphone and streams to server
"""

import asyncio
import websockets
import pyaudio
import json
import sys
import threading
import queue

# Audio configuration - must match server expectations
CHUNK_SIZE = 1024  # Number of audio samples per chunk
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1  # Mono audio
RATE = 16000  # 16 kHz sample rate

class AudioStreamClient:
    def __init__(self, server_ip, port=9999):
        self.server_url = f"ws://{server_ip}:{port}"
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
    
    def start_audio_stream(self, device_index=None):
        """Start capturing audio from microphone"""
        try:
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=device_index
            )
            print(f"Audio stream started (Device: {device_index if device_index is not None else 'default'})")
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.list_audio_devices()
            raise
    
    def audio_capture_thread(self):
        """Thread that captures audio and puts it in queue"""
        print("Audio capture thread started")
        while self.running:
            try:
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_queue.put(data)
            except Exception as e:
                print(f"Error reading audio: {e}")
                break
        print("Audio capture thread stopped")
    
    async def send_audio(self):
        """Coroutine that sends audio from queue to server"""
        chunks_sent = 0
        bytes_sent = 0
        
        while self.running:
            try:
                # Get audio data from queue (non-blocking with timeout)
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.audio_queue.get, True, 0.1
                )
                
                # Send to server
                await self.websocket.send(data)
                chunks_sent += 1
                bytes_sent += len(data)
                
                # Progress indicator
                if chunks_sent % 100 == 0:
                    print(f"Sent {chunks_sent} chunks ({bytes_sent/1024:.1f} KB)")
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error sending audio: {e}")
                break
    
    async def receive_messages(self):
        """Coroutine that receives messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'partial':
                        print(f"\r[PARTIAL] {data.get('text', '')}", end='', flush=True)
                    elif msg_type == 'realtime':
                        print(f"\r[REALTIME] {data.get('text', '')}", end='', flush=True)
                    elif msg_type == 'fullSentence':
                        print(f"\n[SENTENCE] {data.get('text', '')}")
                    elif msg_type == 'recording_start':
                        print("\n>>> Recording started")
                    elif msg_type == 'recording_stop':
                        print("\n>>> Recording stopped")
                    else:
                        print(f"\n[{msg_type}] {data}")
                        
                except json.JSONDecodeError:
                    print(f"Received non-JSON message: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed by server")
    
    async def run(self, device_index=None):
        """Main client loop"""
        print(f"Connecting to {self.server_url}...")
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                print(f"Connected to server!")
                
                # Start audio capture
                self.start_audio_stream(device_index)
                self.running = True
                
                # Start audio capture thread
                capture_thread = threading.Thread(target=self.audio_capture_thread)
                capture_thread.start()
                
                print("\nListening... Speak into your microphone")
                print("Press Ctrl+C to stop\n")
                
                # Run send and receive tasks concurrently
                await asyncio.gather(
                    self.send_audio(),
                    self.receive_messages()
                )
                
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket error: {e}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.running = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.audio.terminate()
            print("\nClient stopped")

def main():
    if len(sys.argv) < 2:
        print("Usage: python minimal_client.py <server-ip> [device-index]")
        print("Example: python minimal_client.py 192.168.1.100")
        print("         python minimal_client.py 192.168.1.100 1")
        
        # List available devices
        audio = pyaudio.PyAudio()
        print("\nAvailable audio input devices:")
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  Device {i}: {info['name']}")
        audio.terminate()
        sys.exit(1)
    
    server_ip = sys.argv[1]
    device_index = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print(f"{'='*50}")
    print("RealtimeSTT Audio Streaming Client")
    print(f"{'='*50}")
    print(f"Server: {server_ip}")
    print(f"Audio: {RATE}Hz, {CHANNELS} channel, 16-bit")
    print(f"Chunk size: {CHUNK_SIZE} samples")
    print(f"{'='*50}\n")
    
    client = AudioStreamClient(server_ip)
    
    try:
        asyncio.run(client.run(device_index))
    except KeyboardInterrupt:
        print("\nStopping client...")

if __name__ == "__main__":
    main()