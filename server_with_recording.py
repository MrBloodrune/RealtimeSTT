#!/usr/bin/env python3
"""
WebSocket server with audio recording and transcription logging
Saves both audio files and transcriptions
"""

if __name__ == '__main__':
    print("Starting server, please wait...")
    from RealtimeSTT import AudioToTextRecorder
    import asyncio
    import websockets
    import threading
    import json
    import logging
    import sys
    import wave
    import os
    from datetime import datetime
    import numpy as np

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger('websockets').setLevel(logging.WARNING)

    # Create output directories
    os.makedirs('recordings', exist_ok=True)
    os.makedirs('transcriptions', exist_ok=True)

    # Global variables
    is_running = True
    recorder = None
    recorder_ready = threading.Event()
    connected_clients = set()
    main_loop = None
    
    # Audio recording variables
    current_recording = []
    is_recording = False
    session_start = datetime.now().strftime('%Y%m%d_%H%M%S')
    transcription_log = f"transcriptions/session_{session_start}.txt"
    
    # Write session header
    with open(transcription_log, 'w') as f:
        f.write(f"Transcription Session Started: {datetime.now()}\n")
        f.write("="*50 + "\n\n")

    async def send_to_clients(message):
        """Send message to all connected clients"""
        if connected_clients:
            disconnected = set()
            for client in connected_clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            for client in disconnected:
                connected_clients.remove(client)

    def save_recording():
        """Save the current recording to a WAV file"""
        global current_recording
        if current_recording:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"recordings/recording_{timestamp}.wav"
            
            # Combine all audio chunks
            audio_data = b''.join(current_recording)
            
            # Save as WAV file
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_data)
            
            print(f"\n>>> Saved recording: {filename}")
            current_recording = []
            return filename
        return None

    def log_transcription(text, recording_file=None):
        """Log transcription to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(transcription_log, 'a') as f:
            f.write(f"[{timestamp}] {text}\n")
            if recording_file:
                f.write(f"  Audio: {recording_file}\n")
            f.write("\n")

    def on_realtime_transcription_update(text):
        """Called with partial transcriptions during speech"""
        global main_loop
        if main_loop and text:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'partial',
                    'text': text
                })), main_loop)
            print(f"\rPartial: {text}", flush=True, end='')

    def on_realtime_transcription_stabilized(text):
        """Called with stabilized transcriptions"""
        global main_loop
        if main_loop and text:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'realtime',
                    'text': text
                })), main_loop)
            print(f"\rRealtime: {text}", flush=True, end='')

    def on_recording_start():
        """Called when voice activity starts"""
        global is_recording
        is_recording = True
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'recording_start'
                })), main_loop)
        print("\n>>> Recording started")

    def on_recording_stop():
        """Called when voice activity stops"""
        global is_recording
        is_recording = False
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'recording_stop'
                })), main_loop)
        print("\n>>> Recording stopped")

    def on_vad_detect_start():
        print(">>> VAD: Speech detected")

    def on_vad_detect_stop():
        print(">>> VAD: Silence detected")

    # Recorder configuration
    recorder_config = {
        'spinner': False,
        'use_microphone': False,
        'model': 'medium.en',
        'language': 'en',
        'silero_sensitivity': 0.4,
        'webrtc_sensitivity': 2,
        'post_speech_silence_duration': 0.4,
        'min_length_of_recording': 0,
        'min_gap_between_recordings': 0,
        'enable_realtime_transcription': True,
        'realtime_processing_pause': 0.2,
        'realtime_model_type': 'tiny.en',
        'on_realtime_transcription_update': on_realtime_transcription_update,
        'on_realtime_transcription_stabilized': on_realtime_transcription_stabilized,
        'on_recording_start': on_recording_start,
        'on_recording_stop': on_recording_stop,
        'on_vad_detect_start': on_vad_detect_start,
        'on_vad_detect_stop': on_vad_detect_stop,
    }

    def recorder_thread():
        """Thread that runs the recorder and processes full sentences"""
        global recorder, is_running
        print("Initializing RealtimeSTT...")
        recorder = AudioToTextRecorder(**recorder_config)
        print("RealtimeSTT initialized successfully")
        recorder_ready.set()
        
        while is_running:
            try:
                full_sentence = recorder.text()
                if full_sentence:
                    # Save recording and log transcription
                    recording_file = save_recording()
                    log_transcription(full_sentence, recording_file)
                    
                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            send_to_clients(json.dumps({
                                'type': 'fullSentence',
                                'text': full_sentence,
                                'audio_file': recording_file
                            })), main_loop)
                    print(f"\nFull sentence: {full_sentence}")
                    
                    # Also print to make it easy to copy
                    print(f"\n{'='*50}")
                    print(f"TRANSCRIPTION: {full_sentence}")
                    print(f"{'='*50}\n")
                    
            except Exception as e:
                print(f"Error in recorder thread: {e}")
                continue

    async def handle_client(websocket):
        """Handle WebSocket client connection"""
        global connected_clients, current_recording, is_recording
        connected_clients.add(websocket)
        client_addr = websocket.remote_address
        print(f"\nClient connected from {client_addr}")
        print(f"Total clients: {len(connected_clients)}")
        
        try:
            chunks_received = 0
            bytes_received = 0
            
            async for message in websocket:
                if not recorder_ready.is_set():
                    print("Recorder not ready yet")
                    continue
                    
                if isinstance(message, bytes):
                    chunks_received += 1
                    bytes_received += len(message)
                    
                    # Store audio if recording
                    if is_recording:
                        current_recording.append(message)
                    
                    # Feed to recorder
                    recorder.feed_audio(message)
                    
                    if chunks_received % 100 == 0:
                        print(f"\nReceived {chunks_received} chunks, {bytes_received/1024:.1f} KB")
                else:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                    except Exception as e:
                        print(f"Error processing control message: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"\nClient {client_addr} disconnected")
        finally:
            connected_clients.remove(websocket)
            print(f"Total clients: {len(connected_clients)}")

    async def main():
        global main_loop
        main_loop = asyncio.get_running_loop()
        
        thread = threading.Thread(target=recorder_thread)
        thread.daemon = True
        thread.start()
        
        recorder_ready.wait()
        
        host = "0.0.0.0"
        port = 9999
        
        print(f"\n{'='*50}")
        print(f"WebSocket Server with Recording & Logging")
        print(f"{'='*50}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"\nOutput locations:")
        print(f"  Audio files: ./recordings/")
        print(f"  Transcriptions: {transcription_log}")
        print(f"\nFeatures:")
        print(f"  - Saves audio recordings for each sentence")
        print(f"  - Logs all transcriptions with timestamps")
        print(f"  - Real-time transcription display")
        print(f"\nPress Ctrl+C to stop")
        print(f"{'='*50}\n")
        
        async with websockets.serve(handle_client, host, port):
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                print("\nShutting down server...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        is_running = False
        print("\nShutting down...")
        if recorder:
            recorder.stop()
            recorder.shutdown()
        print("Server stopped")