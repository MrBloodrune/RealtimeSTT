#!/usr/bin/env python3
"""
WebSocket client for sending audio files to RealtimeSTT server
Processes pre-recorded audio files instead of microphone input
"""

import asyncio
import websockets
import json
import sys
import wave
import time
import numpy as np

class AudioFileClient:
    def __init__(self, server_ip, port=9999):
        self.server_url = f"ws://{server_ip}:{port}"
        
    async def process_audio_file(self, audio_file_path):
        """Process an audio file and send to server"""
        try:
            # Open the audio file
            with wave.open(audio_file_path, 'rb') as wav_file:
                # Check audio format
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                
                print(f"Audio file info:")
                print(f"  Channels: {channels}")
                print(f"  Sample width: {sample_width} bytes")
                print(f"  Sample rate: {framerate} Hz")
                
                # Read all audio data
                audio_data = wav_file.readframes(wav_file.getnframes())
                
                # Convert to 16kHz mono if needed
                if framerate != 16000 or channels != 1:
                    print("Converting audio to 16kHz mono...")
                    import numpy as np
                    from scipy import signal
                    
                    # Convert bytes to numpy array
                    if sample_width == 2:
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    else:
                        raise ValueError("Only 16-bit audio supported")
                    
                    # Convert to mono if stereo
                    if channels == 2:
                        audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
                    
                    # Resample to 16kHz if needed
                    if framerate != 16000:
                        num_samples = int(len(audio_array) * 16000 / framerate)
                        audio_array = signal.resample(audio_array, num_samples).astype(np.int16)
                    
                    audio_data = audio_array.tobytes()
                
            # Connect to server
            async with websockets.connect(self.server_url) as websocket:
                print(f"Connected to {self.server_url}")
                print("Sending audio file...")
                
                # Create receive task
                receive_task = asyncio.create_task(self.receive_messages(websocket))
                
                # Send audio in chunks (simulating real-time)
                chunk_size = 1024 * 2  # 1024 samples * 2 bytes
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    await websocket.send(chunk)
                    # Small delay to simulate real-time streaming
                    await asyncio.sleep(0.032)  # ~32ms per chunk
                
                print("Audio file sent. Waiting for final transcription...")
                
                # Wait a bit for final processing
                await asyncio.sleep(2)
                
                # Cancel receive task
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def receive_messages(self, websocket):
        """Receive and display messages from server"""
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get('type', 'unknown')
                
                if msg_type == 'partial':
                    print(f"\r[Partial] {data.get('text', '')}", end='', flush=True)
                elif msg_type == 'realtime':
                    print(f"\r[Realtime] {data.get('text', '')}", end='', flush=True)
                elif msg_type == 'fullSentence':
                    print(f"\n[Final] {data.get('text', '')}")
                elif msg_type == 'recording_start':
                    print("\n[Recording started]")
                elif msg_type == 'recording_stop':
                    print("\n[Recording stopped]")
                elif msg_type == 'audio_file':
                    print(f"\n[Audio saved] {data.get('filename', '')}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"\nReceive error: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python client_file.py <server-ip> <audio-file>")
        print("Example: python client_file.py 192.168.1.100 recording.wav")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    audio_file = sys.argv[2]
    
    print(f"Processing audio file: {audio_file}")
    print(f"Server: {server_ip}")
    
    client = AudioFileClient(server_ip)
    asyncio.run(client.process_audio_file(audio_file))

if __name__ == "__main__":
    main()