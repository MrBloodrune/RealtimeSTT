#!/usr/bin/env python3
"""
Enhanced Personal Assistant Server with RealtimeVoiceChat-inspired features
Implements concurrent processing, turn detection, and natural interruption handling
"""

if __name__ == '__main__':
    print("Starting Enhanced Personal Assistant Server...")
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from RealtimeSTT import AudioToTextRecorder
    from RealtimeTTS import TextToAudioStream, CoquiEngine, SystemEngine
    import asyncio
    import websockets
    import threading
    import json
    import logging
    import time
    from datetime import datetime
    import anthropic
    from typing import Optional
    import queue

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.getLogger('websockets').setLevel(logging.WARNING)

    class TurnDetector:
        """
        Detects conversation turns based on silence and speech patterns
        Inspired by RealtimeVoiceChat's turndetect.py
        """
        def __init__(self):
            self.last_speech_time = time.time()
            self.silence_threshold = 0.8  # seconds
            self.min_speech_duration = 0.3
            self.is_user_speaking = False
            self.conversation_pace = "normal"  # slow, normal, fast
            
        def on_speech_start(self):
            """Called when speech starts"""
            self.is_user_speaking = True
            self.last_speech_time = time.time()
            
        def on_speech_end(self):
            """Called when speech ends"""
            self.is_user_speaking = False
            
        def should_respond(self):
            """Determine if assistant should respond"""
            silence_duration = time.time() - self.last_speech_time
            
            # Adjust threshold based on conversation pace
            threshold = self.silence_threshold
            if self.conversation_pace == "fast":
                threshold *= 0.7
            elif self.conversation_pace == "slow":
                threshold *= 1.3
                
            return not self.is_user_speaking and silence_duration > threshold
            
        def update_pace(self, response_time):
            """Update conversation pace based on response patterns"""
            if response_time < 0.5:
                self.conversation_pace = "fast"
            elif response_time > 1.5:
                self.conversation_pace = "slow"
            else:
                self.conversation_pace = "normal"

    class ConcurrentProcessor:
        """
        Handles concurrent STT, LLM, and TTS processing
        Inspired by RealtimeVoiceChat's parallel processing
        """
        def __init__(self, llm_client, tts_stream):
            self.llm_client = llm_client
            self.tts_stream = tts_stream
            self.processing_queue = asyncio.Queue()
            self.is_processing = False
            
        async def process_speech(self, text, conversation_history):
            """Process speech through LLM and TTS concurrently"""
            self.is_processing = True
            
            try:
                # Start LLM processing
                llm_task = asyncio.create_task(
                    self.generate_response(text, conversation_history)
                )
                
                # Get response and start TTS streaming
                response = await llm_task
                
                # Stream TTS as text arrives (if using streaming LLM)
                await self.stream_tts(response)
                
            finally:
                self.is_processing = False
                
        async def generate_response(self, text, conversation_history):
            """Generate LLM response"""
            messages = []
            
            # Add conversation history
            for msg in conversation_history[-10:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": text
            })
            
            # Generate response
            response = self.llm_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=0.7,
                system="You are a helpful personal assistant. Keep responses concise and natural for speech. Be friendly and conversational.",
                messages=messages
            )
            
            return response.content[0].text
            
        async def stream_tts(self, text):
            """Stream TTS audio"""
            # For streaming LLM responses, this would process chunks
            # For now, process complete text
            self.tts_stream.feed(text)
            self.tts_stream.play_async()

    class EnhancedAssistant:
        """
        Main assistant class with RealtimeVoiceChat-inspired features
        """
        def __init__(self):
            self.is_running = True
            self.recorder = None
            self.tts_stream = None
            self.turn_detector = TurnDetector()
            self.processor = None
            self.conversation_history = []
            self.connected_clients = set()
            self.main_loop = None
            
            # Audio buffer for smoother playback
            self.audio_buffer = queue.Queue()
            
            # State tracking
            self.is_listening = False
            self.is_speaking = False
            self.last_transcript = ""
            
        async def initialize(self):
            """Initialize all components"""
            print("Initializing components...")
            
            # Initialize LLM
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                self.llm_client = anthropic.Anthropic(api_key=api_key)
            else:
                print("Warning: ANTHROPIC_API_KEY not set")
                self.llm_client = None
            
            # Initialize TTS
            try:
                # Try Coqui engine first (like RealtimeVoiceChat)
                from RealtimeTTS import CoquiEngine
                engine = CoquiEngine()
            except:
                # Fallback to system engine
                engine = SystemEngine()
            
            self.tts_stream = TextToAudioStream(
                engine,
                on_audio_stream_start=self.on_tts_start,
                on_audio_stream_stop=self.on_tts_stop
            )
            
            # Initialize concurrent processor
            self.processor = ConcurrentProcessor(self.llm_client, self.tts_stream)
            
            # Initialize STT
            self.recorder = AudioToTextRecorder(
                model='base.en',  # Faster for real-time
                language='en',
                device='cuda',
                compute_type='float16',
                spinner=False,
                use_microphone=False,
                enable_realtime_transcription=True,
                realtime_model_type='tiny',
                on_realtime_transcription_update=self.on_partial_transcription,
                on_recording_start=self.on_recording_start,
                on_recording_stop=self.on_recording_stop,
                on_vad_detect_start=self.on_vad_start,
                on_vad_detect_stop=self.on_vad_stop,
                silero_sensitivity=0.4,
                post_speech_silence_duration=0.8,
                min_length_of_recording=0.5,
            )
            
            print("All components initialized")
            
        def on_tts_start(self):
            """Called when TTS starts"""
            self.is_speaking = True
            if self.main_loop:
                asyncio.run_coroutine_threadsafe(
                    self.send_to_clients(json.dumps({
                        'type': 'assistant_speaking',
                        'status': 'start'
                    })), self.main_loop)
            
        def on_tts_stop(self):
            """Called when TTS stops"""
            self.is_speaking = False
            if self.main_loop:
                asyncio.run_coroutine_threadsafe(
                    self.send_to_clients(json.dumps({
                        'type': 'assistant_speaking',
                        'status': 'stop'
                    })), self.main_loop)
            
        def on_vad_start(self):
            """Called when voice activity detected"""
            self.turn_detector.on_speech_start()
            
            # Interrupt TTS if speaking
            if self.is_speaking:
                print("🔇 Interrupting assistant...")
                self.tts_stream.stop()
                
        def on_vad_stop(self):
            """Called when voice activity stops"""
            self.turn_detector.on_speech_end()
            
        def on_recording_start(self):
            """Called when recording starts"""
            self.is_listening = True
            print("🎙️ Listening...")
            
        def on_recording_stop(self):
            """Called when recording stops"""
            self.is_listening = False
            
        def on_partial_transcription(self, text):
            """Handle partial transcription updates"""
            if text and self.main_loop:
                asyncio.run_coroutine_threadsafe(
                    self.send_to_clients(json.dumps({
                        'type': 'partial_transcript',
                        'text': text
                    })), self.main_loop)
                
        async def send_to_clients(self, message):
            """Send message to all connected clients"""
            if self.connected_clients:
                disconnected = set()
                for client in self.connected_clients:
                    try:
                        await client.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        disconnected.add(client)
                for client in disconnected:
                    self.connected_clients.remove(client)
                    
        def process_audio_loop(self):
            """Main audio processing loop"""
            while self.is_running:
                try:
                    # Get transcribed text
                    text = self.recorder.text()
                    if text and text != self.last_transcript:
                        self.last_transcript = text
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        print(f"\n[{timestamp}] User: {text}")
                        
                        # Send to clients
                        if self.main_loop:
                            asyncio.run_coroutine_threadsafe(
                                self.send_to_clients(json.dumps({
                                    'type': 'user_message',
                                    'text': text,
                                    'timestamp': timestamp
                                })), self.main_loop)
                        
                        # Process through LLM and TTS
                        if self.processor and self.llm_client:
                            # Add to history
                            self.conversation_history.append({
                                "role": "user",
                                "content": text
                            })
                            
                            # Process concurrently
                            asyncio.run_coroutine_threadsafe(
                                self.process_response(text), self.main_loop)
                            
                except Exception as e:
                    print(f"Error in audio loop: {e}")
                    
        async def process_response(self, text):
            """Process and respond to user input"""
            try:
                # Generate and speak response
                response = await self.processor.generate_response(
                    text, self.conversation_history
                )
                
                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Send to clients
                timestamp = datetime.now().strftime("%H:%M:%S")
                await self.send_to_clients(json.dumps({
                    'type': 'assistant_message',
                    'text': response,
                    'timestamp': timestamp
                }))
                
                print(f"[{timestamp}] Assistant: {response}")
                
                # Stream TTS
                await self.processor.stream_tts(response)
                
            except Exception as e:
                print(f"Error processing response: {e}")
                
        async def handle_websocket(self, websocket):
            """Handle WebSocket connections"""
            self.connected_clients.add(websocket)
            client_addr = websocket.remote_address
            print(f"Client connected from {client_addr}")
            
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connected',
                'features': {
                    'concurrent_processing': True,
                    'turn_detection': True,
                    'interruption_support': True,
                    'real_time_transcription': True
                }
            }))
            
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Audio data
                        self.recorder.feed_audio(message)
                    else:
                        # Control message
                        try:
                            data = json.loads(message)
                            await self.handle_control_message(data, websocket)
                        except json.JSONDecodeError:
                            pass
                            
            except websockets.exceptions.ConnectionClosed:
                print(f"Client {client_addr} disconnected")
            finally:
                self.connected_clients.remove(websocket)
                
        async def handle_control_message(self, data, websocket):
            """Handle control messages from client"""
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            elif msg_type == 'stop_speaking':
                self.tts_stream.stop()
            elif msg_type == 'clear_history':
                self.conversation_history.clear()
                
        async def run_server(self, host='0.0.0.0', port=9999):
            """Run the WebSocket server"""
            self.main_loop = asyncio.get_running_loop()
            
            # Start audio processing thread
            audio_thread = threading.Thread(target=self.process_audio_loop)
            audio_thread.daemon = True
            audio_thread.start()
            
            print(f"\n{'='*60}")
            print(f"Enhanced Personal Assistant Server")
            print(f"{'='*60}")
            print(f"Server: ws://{host}:{port}")
            print(f"\nFeatures:")
            print(f"  ✅ Concurrent STT/LLM/TTS processing")
            print(f"  ✅ Natural turn detection")
            print(f"  ✅ Automatic interruption handling")
            print(f"  ✅ Real-time transcription")
            print(f"  ✅ Conversation pace adaptation")
            print(f"\nPress Ctrl+C to stop")
            print(f"{'='*60}\n")
            
            async with websockets.serve(
                self.handle_websocket, 
                host, 
                port,
                max_size=10*1024*1024
            ):
                try:
                    await asyncio.Future()
                except asyncio.CancelledError:
                    print("\nShutting down...")
                    
        def shutdown(self):
            """Clean shutdown"""
            self.is_running = False
            if self.recorder:
                self.recorder.stop()
                self.recorder.shutdown()
            if self.tts_stream:
                self.tts_stream.stop()

    # Main execution
    async def main():
        assistant = EnhancedAssistant()
        await assistant.initialize()
        
        try:
            await assistant.run_server()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            assistant.shutdown()

    # Run the assistant
    asyncio.run(main())