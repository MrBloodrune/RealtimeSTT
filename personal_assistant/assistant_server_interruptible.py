#!/usr/bin/env python3
"""
Personal Assistant Server with Interruptible Audio
Integrates the interruptible TTS wrapper for natural conversation flow
"""

if __name__ == '__main__':
    print("Starting Personal Assistant Server with Interruptible Audio...")
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from RealtimeSTT import AudioToTextRecorder
    from interruptible_tts_wrapper import EnhancedAssistantTTSWrapper, InterruptReason
    import asyncio
    import websockets
    import threading
    import json
    import logging
    import time
    from datetime import datetime
    import anthropic

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
    tts_wrapper = None
    recorder_ready = threading.Event()
    connected_clients = set()
    main_loop = None
    
    # Assistant state
    conversation_mode = True  # Start in assistant mode
    conversation_history = []
    
    # Conversation state
    is_assistant_speaking = False
    pending_user_input = None
    
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

    async def generate_llm_response(user_text):
        """Generate LLM response using Anthropic Claude API"""
        try:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                return "Please set ANTHROPIC_API_KEY environment variable"
            
            client = anthropic.Anthropic(api_key=api_key)
            
            # Build conversation messages
            messages = []
            
            # Add conversation history (last 10 exchanges)
            for msg in conversation_history[-20:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": user_text
            })
            
            # Generate response
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.7,
                system="You are a helpful personal assistant. Keep responses concise and natural for speech. Be friendly and conversational.",
                messages=messages
            )
            
            assistant_response = response.content[0].text
            
            # Add to conversation history
            conversation_history.append({"role": "user", "content": user_text})
            conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
            
        except Exception as e:
            print(f"\n>>> LLM Error: {e}")
            return "I'm sorry, I encountered an error processing your request."

    def on_speech_start():
        """Called when TTS starts speaking"""
        global is_assistant_speaking
        is_assistant_speaking = True
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'tts_start'
                })), main_loop)
        print("\n🔊 Assistant speaking...")

    def on_speech_end():
        """Called when TTS finishes speaking"""
        global is_assistant_speaking
        is_assistant_speaking = False
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'tts_end'
                })), main_loop)
        print("🔇 Assistant finished")

    def on_speech_interrupted(reason: InterruptReason):
        """Called when TTS is interrupted"""
        global is_assistant_speaking
        is_assistant_speaking = False
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'tts_interrupted',
                    'reason': reason.value
                })), main_loop)
        print(f"⚡ Speech interrupted: {reason.value}")

    def on_vad_detect_start():
        """Called when voice activity is detected"""
        global is_assistant_speaking
        if is_assistant_speaking:
            # User started talking while assistant is speaking - interrupt!
            print("\n🎙️ User interrupting...")
            # The TTS wrapper will handle the interruption via VAD callback
        else:
            print("\n🎙️ User speaking...")
        
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'vad_start'
                })), main_loop)

    def on_vad_detect_stop():
        """Called when voice activity stops"""
        if main_loop:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'vad_stop'
                })), main_loop)

    def on_realtime_transcription_update(text):
        """Called with partial transcriptions during speech"""
        if main_loop and text:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'partial',
                    'text': text
                })), main_loop)
            print(f"\rPartial: {text}", flush=True, end='')

    def on_realtime_transcription_stabilized(text):
        """Called with stabilized transcriptions"""
        if main_loop and text:
            asyncio.run_coroutine_threadsafe(
                send_to_clients(json.dumps({
                    'type': 'realtime',
                    'text': text
                })), main_loop)
            print(f"\rRealtime: {text}", flush=True, end='')

    # Recorder configuration
    recorder_config = {
        'spinner': False,
        'use_microphone': False,
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
        'on_vad_detect_start': on_vad_detect_start,
        'on_vad_detect_stop': on_vad_detect_stop,
    }

    def recorder_thread():
        """Thread that runs the recorder and processes full sentences"""
        global recorder, is_running, tts_wrapper, pending_user_input
        
        print("Initializing RealtimeSTT...")
        recorder = AudioToTextRecorder(**recorder_config)
        
        print("Initializing Interruptible TTS...")
        # Create TTS wrapper with VAD integration
        tts_wrapper = EnhancedAssistantTTSWrapper(
            recorder=recorder,
            voice="en-US-JennyNeural",
            on_speech_start=on_speech_start,
            on_speech_end=on_speech_end,
            on_speech_interrupted=on_speech_interrupted
        )
        
        print("Systems initialized successfully")
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
                    
                    # If in assistant mode, generate response
                    if conversation_mode:
                        # Clear any pending speech in queue
                        tts_wrapper.clear_queue()
                        
                        # Send processing indicator
                        if main_loop:
                            asyncio.run_coroutine_threadsafe(
                                send_to_clients(json.dumps({
                                    'type': 'assistant_processing'
                                })), main_loop)
                        
                        # Generate response
                        response = asyncio.run(generate_llm_response(full_sentence))
                        
                        # Send assistant response text
                        if main_loop:
                            asyncio.run_coroutine_threadsafe(
                                send_to_clients(json.dumps({
                                    'type': 'assistant_response',
                                    'text': response,
                                    'timestamp': datetime.now().strftime("%H:%M:%S")
                                })), main_loop)
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Assistant: {response}")
                        
                        # Speak the response (interruptible)
                        tts_wrapper.speak(response, priority=1)
                        
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
            'mode': 'assistant',
            'features': {
                'interruptible_audio': True,
                'vad_interruption': True,
                'priority_queue': True,
                'llm': 'claude-3-haiku',
                'tts': 'edge-tts'
            }
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
                        elif msg_type == "interrupt":
                            # Manual interrupt command
                            tts_wrapper.interrupt()
                        elif msg_type == "speak":
                            # Direct TTS request
                            text = data.get("text", "")
                            priority = data.get("priority", 0)
                            if text:
                                tts_wrapper.speak(text, priority=priority)
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
        print(f"Personal Assistant Server with Interruptible Audio")
        print(f"{'='*60}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"\nKey Features:")
        print(f"  ✅ Interruptible audio playback")
        print(f"  ✅ VAD-based automatic interruption")
        print(f"  ✅ Priority-based audio queue")
        print(f"  ✅ Natural conversation flow")
        print(f"\nInterruption triggers:")
        print(f"  • User starts speaking (VAD)")
        print(f"  • Manual interrupt command")
        print(f"  • Higher priority messages")
        print(f"\nPress Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        async with websockets.serve(handle_client, host, port, max_size=10*1024*1024):
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
        if tts_wrapper:
            tts_wrapper.shutdown()
        if recorder:
            recorder.stop()
            recorder.shutdown()
        print("Server stopped")