#!/usr/bin/env python3
"""
Enhanced WebSocket server for RealtimeSTT with mobile client storage
Saves audio files and transcriptions per session
"""

if __name__ == '__main__':
    print("Starting enhanced server with storage, please wait...")
    from RealtimeSTT import AudioToTextRecorder
    import asyncio
    import websockets
    import threading
    import json
    import logging
    import sys
    import os
    import wave
    import struct
    from datetime import datetime
    from pathlib import Path

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger('websockets').setLevel(logging.WARNING)

    # Storage configuration
    STORAGE_BASE = Path("/home/bloodrune/RTTS/RealtimeSTT/transcriptions/user1_mobile")
    STORAGE_BASE.mkdir(parents=True, exist_ok=True)

    # Global variables
    is_running = True
    recorder = None
    recorder_ready = threading.Event()
    connected_clients = {}  # websocket: client_info
    main_loop = None

    class ClientSession:
        def __init__(self, websocket, session_id):
            self.websocket = websocket
            self.session_id = session_id
            self.start_time = datetime.now()
            self.audio_buffer = []  # Buffer for audio chunks
            self.transcriptions = []  # List of transcriptions
            self.sentence_count = 0
            self.session_dir = STORAGE_BASE / session_id
            self.session_dir.mkdir(exist_ok=True)
            self.current_audio_file = None
            self.audio_file_count = 0
            
            # Write session info
            info_file = self.session_dir / "session_info.txt"
            with open(info_file, 'w') as f:
                f.write(f"Session ID: {session_id}\n")
                f.write(f"Start Time: {self.start_time.isoformat()}\n")
                f.write(f"Client Address: {websocket.remote_address}\n")
                
        def add_audio(self, audio_data):
            """Add audio data to buffer"""
            self.audio_buffer.extend(audio_data)
            
        def save_audio_chunk(self):
            """Save current audio buffer as WAV file"""
            if not self.audio_buffer:
                return
                
            self.audio_file_count += 1
            filename = f"audio_{self.audio_file_count:04d}.wav"
            filepath = self.session_dir / filename
            
            # Save as WAV file (16kHz, mono, 16-bit)
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                
                # Convert bytes to proper format
                audio_frames = b''.join(self.audio_buffer)
                wav_file.writeframes(audio_frames)
                
            self.audio_buffer.clear()
            return filename
            
        def add_transcription(self, text, transcription_type):
            """Add transcription and save to file"""
            self.sentence_count += 1
            timestamp = datetime.now().isoformat()
            
            # Save audio chunk when we get a full sentence
            audio_filename = None
            if transcription_type == "full_sentence":
                audio_filename = self.save_audio_chunk()
            
            transcription_entry = {
                "timestamp": timestamp,
                "type": transcription_type,
                "text": text,
                "sentence_number": self.sentence_count if transcription_type == "full_sentence" else None,
                "audio_file": audio_filename
            }
            
            self.transcriptions.append(transcription_entry)
            
            # Append to transcription file
            trans_file = self.session_dir / "transcription.txt"
            with open(trans_file, 'a') as f:
                if transcription_type == "full_sentence":
                    f.write(f"\n[{timestamp}] Sentence {self.sentence_count}: {text}\n")
                    if audio_filename:
                        f.write(f"   Audio: {audio_filename}\n")
                        
            # Also save as JSON for structured access
            json_file = self.session_dir / "transcription.json"
            with open(json_file, 'w') as f:
                json.dump(self.transcriptions, f, indent=2)
                
        def close_session(self):
            """Finalize session"""
            # Save any remaining audio
            if self.audio_buffer:
                self.save_audio_chunk()
                
            # Write session summary
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds()
            
            summary_file = self.session_dir / "summary.txt"
            with open(summary_file, 'w') as f:
                f.write(f"Session Summary\n")
                f.write(f"===============\n")
                f.write(f"Session ID: {self.session_id}\n")
                f.write(f"Start Time: {self.start_time.isoformat()}\n")
                f.write(f"End Time: {end_time.isoformat()}\n")
                f.write(f"Duration: {duration:.2f} seconds\n")
                f.write(f"Total Sentences: {self.sentence_count}\n")
                f.write(f"Audio Files: {self.audio_file_count}\n")

    async def send_to_client(websocket, message):
        """Send message to specific client"""
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def send_to_all_clients(message):
        """Send message to all connected clients"""
        if connected_clients:
            tasks = []
            for client_session in connected_clients.values():
                tasks.append(send_to_client(client_session.websocket, message))
            await asyncio.gather(*tasks, return_exceptions=True)

    def on_realtime_transcription_update(text):
        """Called with partial transcriptions during speech"""
        global main_loop
        if main_loop and text:
            message = json.dumps({
                'type': 'realtime',
                'text': text
            })
            for session in connected_clients.values():
                asyncio.run_coroutine_threadsafe(
                    send_to_client(session.websocket, message), 
                    main_loop
                )

    def on_realtime_transcription_stabilized(text):
        """Called with stabilized transcriptions during speech"""
        global main_loop
        if main_loop and text:
            message = json.dumps({
                'type': 'partial',
                'text': text
            })
            for session in connected_clients.values():
                asyncio.run_coroutine_threadsafe(
                    send_to_client(session.websocket, message),
                    main_loop
                )

    def on_recording_start():
        """Called when voice activity starts"""
        if main_loop:
            message = json.dumps({'type': 'recording_start'})
            asyncio.run_coroutine_threadsafe(
                send_to_all_clients(message), 
                main_loop
            )
        print("\n>>> Recording started")

    def on_recording_stop():
        """Called when voice activity stops"""
        if main_loop:
            message = json.dumps({'type': 'recording_stop'})
            asyncio.run_coroutine_threadsafe(
                send_to_all_clients(message),
                main_loop
            )
        print("\n>>> Recording stopped")

    def on_vad_detect_start():
        """Called when VAD detects speech"""
        print(">>> VAD: Speech detected")

    def on_vad_detect_stop():
        """Called when VAD detects silence"""
        print(">>> VAD: Silence detected")

    # Recorder configuration
    recorder_config = {
        'spinner': False,
        'use_microphone': False,  # We'll feed audio from WebSocket
        'model': 'medium.en',
        'language': 'en',
        'device': 'cuda',
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
        recorder_ready.set()
        print("RealtimeSTT initialized successfully")
        
        while is_running:
            try:
                # This blocks until a full sentence is detected
                full_sentence = recorder.text()
                if full_sentence:
                    print(f"\n[Full sentence]: {full_sentence}")
                    
                    # Send to all clients and save
                    message = json.dumps({
                        'type': 'full_sentence',
                        'text': full_sentence
                    })
                    
                    if main_loop:
                        for session in connected_clients.values():
                            # Save transcription
                            session.add_transcription(full_sentence, 'full_sentence')
                            # Send to client
                            asyncio.run_coroutine_threadsafe(
                                send_to_client(session.websocket, message),
                                main_loop
                            )
            except Exception as e:
                logging.error(f"Error in recorder thread: {e}")
                if is_running:
                    import time
                    time.sleep(0.1)

    async def handle_client(websocket):
        """Handle WebSocket client connection"""
        global connected_clients
        
        # Create session for this client
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S_") + str(len(connected_clients))
        client_session = ClientSession(websocket, session_id)
        connected_clients[websocket] = client_session
        
        client_addr = websocket.remote_address
        print(f"\nClient connected from {client_addr}")
        print(f"Session ID: {session_id}")
        print(f"Total clients: {len(connected_clients)}")
        
        try:
            chunks_received = 0
            bytes_received = 0
            
            async for message in websocket:
                if not recorder_ready.is_set():
                    print("Recorder not ready yet")
                    continue
                    
                if isinstance(message, bytes):
                    # Direct audio data (16kHz, mono, 16-bit PCM)
                    chunks_received += 1
                    bytes_received += len(message)
                    
                    # Save audio to session buffer
                    client_session.add_audio(message)
                    
                    # Feed to recorder
                    recorder.feed_audio(message)
                    
                    # Log progress every 100 chunks
                    if chunks_received % 100 == 0:
                        print(f"\n[{session_id}] Received {chunks_received} chunks, {bytes_received/1024:.1f} KB")
                else:
                    # Text message (control)
                    try:
                        data = json.loads(message)
                        if data.get("type") == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                    except Exception as e:
                        print(f"Error processing control message: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"\nClient {client_addr} disconnected")
        finally:
            # Clean up session
            if websocket in connected_clients:
                client_session.close_session()
                del connected_clients[websocket]
            print(f"Total clients: {len(connected_clients)}")

    async def main():
        global main_loop
        main_loop = asyncio.get_running_loop()
        
        # Start recorder thread
        thread = threading.Thread(target=recorder_thread)
        thread.daemon = True
        thread.start()
        
        # Wait for recorder to be ready
        recorder_ready.wait()
        
        # Server configuration
        host = "0.0.0.0"
        port = 9999
        
        print(f"\n{'='*50}")
        print(f"WebSocket Audio Streaming Server with Storage")
        print(f"{'='*50}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"Storage path: {STORAGE_BASE}")
        print(f"Features:")
        print(f"  - Real-time partial transcriptions")
        print(f"  - Full sentence transcriptions")
        print(f"  - Audio file storage per session")
        print(f"  - Transcription logging")
        print(f"\nPress Ctrl+C to stop")
        print(f"{'='*50}\n")
        
        async with websockets.serve(handle_client, host, port):
            try:
                await asyncio.Future()  # Run forever
            except asyncio.CancelledError:
                print("\nShutting down server...")

    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        is_running = False
        print("\nShutting down...")
        if recorder:
            recorder.stop()
            recorder.shutdown()
        print("Server stopped")