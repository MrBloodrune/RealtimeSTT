#!/usr/bin/env python3
"""
Fast real-time WebSocket server for RealtimeSTT
Uses tiny models for maximum responsiveness
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

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger('websockets').setLevel(logging.WARNING)

    # Global variables
    is_running = True
    recorder = None
    recorder_ready = threading.Event()
    connected_clients = set()
    main_loop = None

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
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'recording_start'
                })), main_loop)
        print("\n>>> Recording started")

    def on_recording_stop():
        """Called when voice activity stops"""
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'recording_stop'
                })), main_loop)
        print("\n>>> Recording stopped")

    # Recorder configuration - FAST REAL-TIME
    recorder_config = {
        'spinner': False,
        'use_microphone': False,
        'model': 'tiny.en',  # Fast model for final transcription too
        'language': 'en',
        'silero_sensitivity': 0.4,
        'webrtc_sensitivity': 2,
        'post_speech_silence_duration': 0.3,  # Shorter silence for responsiveness
        'min_length_of_recording': 0,
        'min_gap_between_recordings': 0,
        'enable_realtime_transcription': True,
        'realtime_processing_pause': 0.05,  # Very fast processing
        'realtime_model_type': 'tiny.en',
        'on_realtime_transcription_update': on_realtime_transcription_update,
        'on_realtime_transcription_stabilized': on_realtime_transcription_stabilized,
        'on_recording_start': on_recording_start,
        'on_recording_stop': on_recording_stop,
    }

    def recorder_thread():
        """Thread that runs the recorder and processes full sentences"""
        global recorder, is_running
        print("Initializing RealtimeSTT (fast mode)...")
        recorder = AudioToTextRecorder(**recorder_config)
        print("RealtimeSTT initialized successfully")
        recorder_ready.set()
        
        while is_running:
            try:
                full_sentence = recorder.text()
                if full_sentence:
                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            send_to_clients(json.dumps({
                                'type': 'fullSentence',
                                'text': full_sentence
                            })), main_loop)
                    print(f"\nFull sentence: {full_sentence}")
            except Exception as e:
                print(f"Error in recorder thread: {e}")
                continue

    async def handle_client(websocket):
        """Handle WebSocket client connection"""
        global connected_clients
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
        print(f"WebSocket Audio Streaming Server (FAST REAL-TIME)")
        print(f"{'='*50}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"Configuration:")
        print(f"  - Model: tiny.en (fastest)")
        print(f"  - Real-time updates: Very responsive")
        print(f"  - Best for: Live feedback, less accuracy")
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