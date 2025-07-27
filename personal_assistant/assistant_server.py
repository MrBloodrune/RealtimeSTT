#!/usr/bin/env python3
"""
Personal Assistant Server
Extends RealtimeSTT with LLM and TTS capabilities using existing patterns
"""

if __name__ == '__main__':
    print("Starting Personal Assistant Server...")
    import sys
    import os
    # Add parent directory to path for RealtimeSTT import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from RealtimeSTT import AudioToTextRecorder
    import asyncio
    import websockets
    import threading
    import json
    import logging
    import time
    from datetime import datetime

    # Try to import OpenAI for LLM support
    try:
        import openai
        OPENAI_AVAILABLE = True
    except ImportError:
        OPENAI_AVAILABLE = False
        print("Warning: OpenAI not installed. LLM features disabled.")
        print("Install with: pip install openai")

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
    
    # Assistant state
    conversation_mode = False
    conversation_history = []
    
    # Simple command handling
    COMMANDS = {
        "assistant mode": lambda: enable_assistant_mode(),
        "transcription mode": lambda: disable_assistant_mode(),
        "clear history": lambda: clear_conversation(),
    }

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

    def enable_assistant_mode():
        """Enable conversational assistant mode"""
        global conversation_mode
        conversation_mode = True
        print("\n>>> Assistant mode ENABLED")
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'mode_change',
                    'mode': 'assistant',
                    'message': 'Assistant mode enabled'
                })), main_loop)

    def disable_assistant_mode():
        """Disable assistant mode, return to transcription only"""
        global conversation_mode
        conversation_mode = False
        print("\n>>> Assistant mode DISABLED")
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'mode_change',
                    'mode': 'transcription',
                    'message': 'Transcription mode enabled'
                })), main_loop)

    def clear_conversation():
        """Clear conversation history"""
        global conversation_history
        conversation_history = []
        print("\n>>> Conversation history cleared")

    async def generate_llm_response(user_text):
        """Generate LLM response using OpenAI API"""
        if not OPENAI_AVAILABLE:
            return "LLM features are not available. Please install OpenAI: pip install openai"
        
        try:
            # Add user message to history
            conversation_history.append({"role": "user", "content": user_text})
            
            # Prepare messages for API
            messages = [
                {"role": "system", "content": "You are a helpful personal assistant. Keep responses concise and natural for speech."}
            ]
            # Include recent conversation history (last 10 messages)
            messages.extend(conversation_history[-10:])
            
            # Get OpenAI client
            client = openai.OpenAI()
            
            # Generate response
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            
            # Add assistant response to history
            conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"LLM Error: {str(e)}"
            print(f"\n>>> {error_msg}")
            return "I'm sorry, I encountered an error processing your request."

    def process_command(text):
        """Check if text contains a command"""
        text_lower = text.lower().strip()
        for command, action in COMMANDS.items():
            if command in text_lower:
                action()
                return True
        return False

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

    # Recorder configuration (same as server_realtime_balanced.py)
    recorder_config = {
        'spinner': False,
        'use_microphone': False,
        'model': 'tiny',  # Use tiny for faster processing
        'language': 'en',
        'silero_sensitivity': 0.4,
        'webrtc_sensitivity': 2,
        'post_speech_silence_duration': 0.4,
        'min_length_of_recording': 0,
        'min_gap_between_recordings': 0,
        'enable_realtime_transcription': True,
        'realtime_processing_pause': 0.2,
        'realtime_model_type': 'tiny',
        'on_realtime_transcription_update': on_realtime_transcription_update,
        'on_realtime_transcription_stabilized': on_realtime_transcription_stabilized,
        'on_recording_start': on_recording_start,
        'on_recording_stop': on_recording_stop,
    }

    def recorder_thread():
        """Thread that runs the recorder and processes full sentences"""
        global recorder, is_running
        print("Initializing RealtimeSTT...")
        recorder = AudioToTextRecorder(**recorder_config)
        print("RealtimeSTT initialized successfully")
        recorder_ready.set()
        
        # Process full sentences
        while is_running:
            try:
                full_sentence = recorder.text()
                if full_sentence:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Send transcription to clients
                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            send_to_clients(json.dumps({
                                'type': 'fullSentence',
                                'text': full_sentence,
                                'timestamp': timestamp
                            })), main_loop)
                    
                    print(f"\n[{timestamp}] User: {full_sentence}")
                    
                    # Check for commands
                    if process_command(full_sentence):
                        continue
                    
                    # If in assistant mode, generate response
                    if conversation_mode and OPENAI_AVAILABLE:
                        # Send processing indicator
                        if main_loop:
                            asyncio.run_coroutine_threadsafe(
                                send_to_clients(json.dumps({
                                    'type': 'assistant_processing'
                                })), main_loop)
                        
                        # Generate response
                        response = asyncio.run(generate_llm_response(full_sentence))
                        
                        # Send assistant response
                        if main_loop:
                            asyncio.run_coroutine_threadsafe(
                                send_to_clients(json.dumps({
                                    'type': 'assistant_response',
                                    'text': response,
                                    'timestamp': datetime.now().strftime("%H:%M:%S")
                                })), main_loop)
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Assistant: {response}")
                        
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
        
        # Send initial status
        await websocket.send(json.dumps({
            'type': 'connected',
            'mode': 'assistant' if conversation_mode else 'transcription',
            'llm_available': OPENAI_AVAILABLE
        }))
        
        try:
            chunks_received = 0
            bytes_received = 0
            
            async for message in websocket:
                if not recorder_ready.is_set():
                    print("Recorder not ready yet")
                    continue
                    
                if isinstance(message, bytes):
                    # Direct audio data
                    chunks_received += 1
                    bytes_received += len(message)
                    
                    # Feed to recorder
                    recorder.feed_audio(message)
                    
                    # Log progress every 100 chunks
                    if chunks_received % 100 == 0:
                        print(f"\nReceived {chunks_received} chunks, {bytes_received/1024:.1f} KB")
                else:
                    # Text message (control)
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                        elif msg_type == "set_mode":
                            mode = data.get("mode")
                            if mode == "assistant":
                                enable_assistant_mode()
                            elif mode == "transcription":
                                disable_assistant_mode()
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
        
        # Start recorder thread
        thread = threading.Thread(target=recorder_thread)
        thread.daemon = True
        thread.start()
        
        # Wait for recorder to be ready
        recorder_ready.wait()
        
        # Server configuration
        host = "0.0.0.0"
        port = 9999
        
        print(f"\n{'='*60}")
        print(f"Personal Assistant Server")
        print(f"{'='*60}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"\nFeatures:")
        print(f"  - Real-time speech transcription")
        print(f"  - LLM assistant mode {'(available)' if OPENAI_AVAILABLE else '(not available - install openai)'}")
        print(f"  - Voice commands:")
        print(f"    • 'assistant mode' - Enable LLM responses")
        print(f"    • 'transcription mode' - Disable LLM")
        print(f"    • 'clear history' - Clear conversation")
        print(f"\nPress Ctrl+C to stop")
        print(f"{'='*60}\n")
        
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