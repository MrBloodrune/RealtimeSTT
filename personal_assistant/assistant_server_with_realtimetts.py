#!/usr/bin/env python3
"""
Personal Assistant Server with Anthropic Claude and RealtimeTTS
Uses actual TTS engines for natural speech output
"""

if __name__ == '__main__':
    print("Starting Personal Assistant Server with RealtimeTTS...")
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
    import numpy as np
    from datetime import datetime
    import io

    # Try to import Anthropic for LLM support
    try:
        import anthropic
        ANTHROPIC_AVAILABLE = True
    except ImportError:
        ANTHROPIC_AVAILABLE = False
        print("Warning: Anthropic not installed. LLM features disabled.")
        print("Install with: pip install anthropic")

    # Try to import RealtimeTTS
    TTS_ENGINE = None
    TTS_STREAM = None
    TTS_AVAILABLE = False
    
    try:
        from RealtimeTTS import TextToAudioStream, SystemEngine, CoquiEngine, EdgeEngine
        TTS_AVAILABLE = True
        print("RealtimeTTS is available!")
    except ImportError:
        print("Warning: RealtimeTTS not installed.")
        print("Install with: pip install realtimetts[all]")
        
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
    
    # Audio capture for TTS
    audio_chunks = []
    capturing_audio = False
    
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
                    if is_binary:
                        await client.send(message)
                    else:
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

    def on_audio_chunk(chunk):
        """Callback to capture audio chunks from TTS"""
        global audio_chunks, capturing_audio
        if capturing_audio:
            audio_chunks.append(chunk)

    async def send_tts_audio(text):
        """Generate and send TTS audio using RealtimeTTS"""
        global TTS_STREAM, audio_chunks, capturing_audio
        
        if not TTS_AVAILABLE or not TTS_STREAM:
            print(">>> TTS not available, sending simple tones")
            # Fallback to simple tones
            await send_simple_tts(text)
            return
            
        print(f"\n>>> Generating TTS for: {text[:50]}...")
        
        try:
            # Send audio metadata first
            await send_to_clients(json.dumps({
                'type': 'audio_response',
                'sample_rate': 16000,
                'channels': 1,
                'format': 'int16',
                'text': text
            }))
            
            # Reset audio capture
            audio_chunks = []
            capturing_audio = True
            
            # Feed text to TTS and play (which triggers on_audio_chunk)
            TTS_STREAM.feed(text)
            TTS_STREAM.play()
            
            # Send captured audio chunks
            capturing_audio = False
            
            if audio_chunks:
                # Combine all chunks
                combined_audio = b''.join(audio_chunks)
                
                # Send in smaller chunks over WebSocket
                chunk_size = 4096
                for i in range(0, len(combined_audio), chunk_size):
                    chunk = combined_audio[i:i + chunk_size]
                    await send_to_clients(chunk, is_binary=True)
                    await asyncio.sleep(0.01)
                    
                print(f">>> Sent {len(combined_audio)} bytes of TTS audio")
            
            # Send end marker
            await send_to_clients(json.dumps({'type': 'audio_end'}))
            
        except Exception as e:
            print(f">>> TTS Error: {e}")
            # Fallback to simple tones
            await send_simple_tts(text)

    async def send_simple_tts(text):
        """Fallback simple tone generation"""
        try:
            # Generate simple tones
            duration = min(0.2 + len(text) * 0.02, 3.0)
            sample_rate = 16000
            t = np.linspace(0, duration, int(sample_rate * duration))
            
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
            
            audio_data = (audio * 32767).astype(np.int16).tobytes()
            
            # Send audio
            await send_to_clients(json.dumps({
                'type': 'audio_response',
                'sample_rate': 16000,
                'channels': 1,
                'format': 'int16',
                'length': len(audio_data) // 2,
                'text': text
            }))
            
            chunk_size = 4096
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await send_to_clients(chunk, is_binary=True)
                await asyncio.sleep(0.01)
            
            await send_to_clients(json.dumps({'type': 'audio_end'}))
            
        except Exception as e:
            print(f">>> Simple TTS Error: {e}")

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
            'tts_available': TTS_AVAILABLE,
            'tts_engine': TTS_ENGINE.__class__.__name__ if TTS_ENGINE else 'None'
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
        global main_loop, TTS_ENGINE, TTS_STREAM
        main_loop = asyncio.get_running_loop()
        
        # Initialize TTS if available
        if TTS_AVAILABLE:
            try:
                print("Initializing TTS engine...")
                # Try different engines in order of preference
                try:
                    # Try Edge TTS first (free, good quality)
                    TTS_ENGINE = EdgeEngine()
                    print("Using Edge TTS engine")
                except:
                    try:
                        # Try System TTS
                        TTS_ENGINE = SystemEngine()
                        print("Using System TTS engine")
                    except:
                        # Try Coqui as last resort
                        TTS_ENGINE = CoquiEngine()
                        print("Using Coqui TTS engine")
                
                # Create TTS stream with audio capture callback
                TTS_STREAM = TextToAudioStream(
                    TTS_ENGINE,
                    on_audio_chunk=on_audio_chunk,
                    muted=True  # Mute local playback since we're streaming
                )
                print("TTS stream initialized")
            except Exception as e:
                print(f"Failed to initialize TTS: {e}")
                TTS_ENGINE = None
                TTS_STREAM = None
        
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
        print(f"Personal Assistant Server with RealtimeTTS")
        print(f"{'='*60}")
        print(f"Server address: ws://<server-ip>:{port}")
        print(f"\nFeatures:")
        print(f"  - Real-time speech transcription")
        print(f"    • Main model: medium.en (high accuracy)")
        print(f"    • Realtime model: tiny.en (fast updates)")
        print(f"    • GPU acceleration: enabled (CUDA)")
        print(f"  - Claude assistant mode {'(available)' if ANTHROPIC_AVAILABLE else '(not available - install anthropic)'}")
        
        if TTS_AVAILABLE:
            print(f"  - TTS audio streaming: {TTS_ENGINE.__class__.__name__ if TTS_ENGINE else 'Failed to initialize'}")
        else:
            print(f"  - TTS audio streaming: Not installed (using simple tones)")
            
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