#!/usr/bin/env python3
"""
Personal Assistant Server with Direct Edge TTS Audio
Sends MP3 directly without conversion - let client handle it
"""

if __name__ == '__main__':
    print("Starting Personal Assistant Server with Direct Edge TTS...")
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
    import edge_tts
    import numpy as np

    # Try to import Anthropic for LLM support
    try:
        import anthropic
        ANTHROPIC_AVAILABLE = True
    except ImportError:
        ANTHROPIC_AVAILABLE = False
        print("Warning: Anthropic not installed. LLM features disabled.")
        print("Install with: pip install anthropic")

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
    
    # TTS settings
    TTS_VOICE = "en-US-JennyNeural"  # Natural female voice
    
    # Simple command handling
    COMMANDS = {
        "assistant mode": lambda: enable_assistant_mode(),
        "transcription mode": lambda: disable_assistant_mode(),
        "clear history": lambda: clear_conversation(),
    }

    async def send_to_clients(message, is_binary=False):
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
        """Generate LLM response using Anthropic Claude API"""
        if not ANTHROPIC_AVAILABLE:
            return "LLM features are not available. Please install Anthropic: pip install anthropic"
        
        try:
            # Get API key
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if not api_key:
                return "Please set ANTHROPIC_API_KEY environment variable"
            
            # Create Anthropic client
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
            
            # Generate response using Claude
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
            error_msg = f"LLM Error: {str(e)}"
            print(f"\n>>> {error_msg}")
            return "I'm sorry, I encountered an error processing your request."

    def generate_simple_tts(text):
        """Generate simple audio tones as fallback"""
        duration = min(0.2 + len(text) * 0.02, 3.0)
        sample_rate = 16000
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create a simple melody
        frequencies = []
        for i, char in enumerate(text[:20]):
            if char.isalpha():
                freq = 300 + (ord(char.lower()) - ord('a')) * 20
                frequencies.append(freq)
        
        if not frequencies:
            frequencies = [440]
        
        audio = np.zeros(len(t))
        note_duration = duration / len(frequencies)
        
        for i, freq in enumerate(frequencies):
            start = int(i * note_duration * sample_rate)
            end = min(int((i + 1) * note_duration * sample_rate), len(t))
            
            note_t = t[start:end] - t[start]
            envelope = np.exp(-3 * note_t / note_duration)
            note = np.sin(2 * np.pi * freq * note_t) * envelope * 0.3
            
            audio[start:end] = note
        
        return (audio * 32767).astype(np.int16).tobytes()

    async def send_tts_audio(text):
        """Generate and send TTS audio to clients"""
        try:
            # Try Edge TTS first
            try:
                print(f"\n>>> Generating Edge TTS for: {text[:50]}...")
                
                # Create Edge TTS communicate object
                communicate = edge_tts.Communicate(text, TTS_VOICE)
                
                # Collect MP3 audio chunks
                mp3_chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        mp3_chunks.append(chunk["data"])
                
                # Combine all chunks
                mp3_data = b''.join(mp3_chunks)
                print(f">>> Generated {len(mp3_data)} bytes of MP3 audio")
                
                # Send audio metadata with MP3 format
                await send_to_clients(json.dumps({
                    'type': 'audio_response',
                    'format': 'mp3',  # Tell client it's MP3
                    'text': text
                }))
                
                # Send MP3 data directly
                chunk_size = 4096
                for i in range(0, len(mp3_data), chunk_size):
                    chunk = mp3_data[i:i + chunk_size]
                    await send_to_clients(chunk, is_binary=True)
                    await asyncio.sleep(0.01)
                
                # Send end marker
                await send_to_clients(json.dumps({'type': 'audio_end'}))
                
                print(">>> Edge TTS audio sent successfully")
                
            except Exception as e:
                print(f">>> Edge TTS failed: {e}, using simple tones")
                
                # Fallback to simple tones
                pcm_data = generate_simple_tts(text)
                
                # Send audio metadata with PCM format
                await send_to_clients(json.dumps({
                    'type': 'audio_response',
                    'sample_rate': 16000,
                    'channels': 1,
                    'format': 'int16',  # PCM format
                    'length': len(pcm_data) // 2,
                    'text': text
                }))
                
                # Send PCM data
                chunk_size = 4096
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i:i + chunk_size]
                    await send_to_clients(chunk, is_binary=True)
                    await asyncio.sleep(0.01)
                
                await send_to_clients(json.dumps({'type': 'audio_end'}))
                
        except Exception as e:
            print(f">>> TTS Send Error: {e}")
            await send_to_clients(json.dumps({
                'type': 'tts_error',
                'error': str(e)
            }))

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
                    if conversation_mode and ANTHROPIC_AVAILABLE:
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
                        
                        # Send TTS audio
                        asyncio.run(send_tts_audio(response))
                        
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
            'llm_available': ANTHROPIC_AVAILABLE,
            'tts_available': True,
            'tts_engine': 'Edge TTS (MP3) / Simple tones (PCM)',
            'tts_voice': TTS_VOICE
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
        
        # Test Edge TTS availability
        try:
            print("Testing Edge TTS...")
            communicate = edge_tts.Communicate("Test", TTS_VOICE)
            test_complete = False
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    test_complete = True
                    break
            if test_complete:
                print("✓ Edge TTS is working!")
            else:
                print("✗ Edge TTS test failed")
        except Exception as e:
            print(f"✗ Edge TTS error: {e}")
        
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
        print(f"Personal Assistant Server (Direct Audio)")
        print(f"{'='*60}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"\nFeatures:")
        print(f"  - Real-time speech transcription")
        print(f"    • Main model: medium.en (high accuracy)")
        print(f"    • Realtime model: tiny.en (fast updates)")
        print(f"    • GPU acceleration: enabled (CUDA)")
        print(f"  - Claude assistant mode {'(available)' if ANTHROPIC_AVAILABLE else '(not available - install anthropic)'}")
        print(f"  - Audio streaming:")
        print(f"    • Edge TTS: MP3 format (natural voices)")
        print(f"    • Fallback: PCM tones (if Edge TTS fails)")
        print(f"    • Voice: {TTS_VOICE}")
        print(f"  - Voice commands:")
        print(f"    • 'assistant mode' - Enable Claude + TTS")
        print(f"    • 'transcription mode' - Disable assistant")
        print(f"    • 'clear history' - Clear conversation")
        
        if ANTHROPIC_AVAILABLE:
            api_key_set = bool(os.environ.get('ANTHROPIC_API_KEY'))
            print(f"\nAnthropic API Key: {'SET' if api_key_set else 'NOT SET'}")
            if not api_key_set:
                print("  Set with: export ANTHROPIC_API_KEY='your-key-here'")
        
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
        if recorder:
            recorder.stop()
            recorder.shutdown()
        print("Server stopped")