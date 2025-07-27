#!/usr/bin/env python3
"""
Interruptible TTS Wrapper for Personal Assistant
Provides interrupt capabilities for audio playback based on VAD, wake words, or manual triggers
"""

import asyncio
import threading
import queue
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

# For TTS we'll use edge_tts directly for now
import edge_tts
import pyaudio
import numpy as np
from pydub import AudioSegment
import io

logger = logging.getLogger(__name__)

class InterruptReason(Enum):
    """Reasons for audio interruption"""
    MANUAL = "manual"
    VAD_DETECTED = "vad_detected"
    WAKE_WORD = "wake_word"
    NEW_MESSAGE = "new_message"
    SHUTDOWN = "shutdown"

@dataclass
class AudioTask:
    """Represents a queued audio task"""
    text: str
    task_id: str
    priority: int = 0
    metadata: dict = None

class InterruptibleTTSWrapper:
    """
    Wrapper for TTS with interruption support
    Following the Personal Assistant architecture principles
    """
    
    def __init__(
        self,
        voice: str = "en-US-JennyNeural",
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable] = None,
        on_speech_interrupted: Optional[Callable[[InterruptReason], None]] = None
    ):
        self.voice = voice
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_speech_interrupted = on_speech_interrupted
        
        # Audio configuration
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        
        # State management
        self.is_speaking = False
        self.should_stop = threading.Event()
        self.audio_queue = queue.Queue()
        self.current_task: Optional[AudioTask] = None
        
        # PyAudio for playback
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None
        
        # Worker thread for audio processing
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"InterruptibleTTSWrapper initialized with voice: {voice}")
    
    def speak(self, text: str, task_id: str = None, priority: int = 0, metadata: dict = None):
        """
        Queue text for speech synthesis and playback
        
        Args:
            text: Text to speak
            task_id: Unique identifier for this task
            priority: Higher priority tasks interrupt lower priority ones
            metadata: Additional data associated with this task
        """
        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())
        
        task = AudioTask(text=text, task_id=task_id, priority=priority, metadata=metadata or {})
        
        # If higher priority, interrupt current playback
        if self.is_speaking and self.current_task and priority > self.current_task.priority:
            logger.info(f"Interrupting current task {self.current_task.task_id} for higher priority {task_id}")
            self.interrupt(InterruptReason.NEW_MESSAGE)
        
        self.audio_queue.put(task)
        return task_id
    
    def interrupt(self, reason: InterruptReason = InterruptReason.MANUAL):
        """Interrupt current audio playback"""
        if self.is_speaking:
            logger.info(f"Interrupting audio playback: {reason.value}")
            self.should_stop.set()
            
            if self.on_speech_interrupted:
                self.on_speech_interrupted(reason)
    
    def clear_queue(self):
        """Clear all pending audio tasks"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def shutdown(self):
        """Shutdown the TTS wrapper"""
        self.interrupt(InterruptReason.SHUTDOWN)
        self.clear_queue()
        
        # Signal shutdown
        self.audio_queue.put(None)
        
        # Close PyAudio
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pyaudio.terminate()
    
    async def _generate_audio(self, text: str) -> Optional[bytes]:
        """Generate audio using Edge TTS"""
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            
            # Collect MP3 chunks
            mp3_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_chunks.append(chunk["data"])
                
                # Check for interruption during generation
                if self.should_stop.is_set():
                    logger.info("Audio generation interrupted")
                    return None
            
            # Convert MP3 to PCM
            mp3_data = b''.join(mp3_chunks)
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            
            # Convert to our target format
            audio = audio.set_frame_rate(self.sample_rate)
            audio = audio.set_channels(self.channels)
            audio = audio.set_sample_width(2)  # 16-bit
            
            return audio.raw_data
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None
    
    def _play_audio(self, audio_data: bytes) -> bool:
        """
        Play audio data through PyAudio
        Returns True if completed, False if interrupted
        """
        if not self.stream:
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
        
        # Play in chunks, checking for interruption
        for i in range(0, len(audio_data), self.chunk_size * 2):  # *2 for 16-bit samples
            if self.should_stop.is_set():
                return False
            
            chunk = audio_data[i:i + self.chunk_size * 2]
            self.stream.write(chunk)
        
        return True
    
    def _worker_loop(self):
        """Main worker loop for processing audio tasks"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                # Get next task from queue
                task = self.audio_queue.get()
                
                # Check for shutdown signal
                if task is None:
                    break
                
                self.current_task = task
                self.is_speaking = True
                self.should_stop.clear()
                
                logger.info(f"Processing audio task: {task.task_id}")
                
                # Notify start
                if self.on_speech_start:
                    self.on_speech_start()
                
                # Generate audio
                audio_data = loop.run_until_complete(self._generate_audio(task.text))
                
                if audio_data and not self.should_stop.is_set():
                    # Play audio
                    completed = self._play_audio(audio_data)
                    
                    # Notify end
                    if completed and self.on_speech_end:
                        self.on_speech_end()
                
                self.is_speaking = False
                self.current_task = None
                
            except Exception as e:
                logger.error(f"Error in TTS worker: {e}")
                self.is_speaking = False

class EnhancedAssistantTTSWrapper(InterruptibleTTSWrapper):
    """
    Enhanced wrapper with VAD integration for the Personal Assistant
    """
    
    def __init__(self, recorder=None, **kwargs):
        super().__init__(**kwargs)
        self.recorder = recorder
        self._setup_vad_callbacks()
    
    def _setup_vad_callbacks(self):
        """Setup VAD callbacks for automatic interruption"""
        if self.recorder:
            # Store original callbacks
            self._original_on_vad_start = getattr(self.recorder, 'on_vad_detect_start', None)
            
            # Set our interrupt callback
            def on_vad_interrupt():
                self.interrupt(InterruptReason.VAD_DETECTED)
                # Call original if exists
                if self._original_on_vad_start:
                    self._original_on_vad_start()
            
            self.recorder.on_vad_detect_start = on_vad_interrupt
    
    def enable_auto_interrupt(self, enabled: bool = True):
        """Enable/disable automatic interruption on VAD"""
        if self.recorder:
            if enabled:
                self._setup_vad_callbacks()
            else:
                # Restore original callback
                self.recorder.on_vad_detect_start = self._original_on_vad_start


# Example usage
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from RealtimeSTT import AudioToTextRecorder
    
    # Create TTS with callbacks
    def on_start():
        print("🔊 Speaking...")
    
    def on_end():
        print("🔇 Finished speaking")
    
    def on_interrupted(reason):
        print(f"⚡ Speech interrupted: {reason.value}")
    
    tts = InterruptibleTTSWrapper(
        voice="en-US-JennyNeural",
        on_speech_start=on_start,
        on_speech_end=on_end,
        on_speech_interrupted=on_interrupted
    )
    
    # Test basic speech
    print("Testing basic speech...")
    tts.speak("Hello! This is a test of the interruptible text to speech system.")
    
    # Test interruption
    import time
    time.sleep(1)
    print("Testing interruption in 2 seconds...")
    tts.speak("This is a longer message that will be interrupted. Let me tell you about all the features of this system.")
    time.sleep(2)
    tts.interrupt()
    
    # Test priority
    print("Testing priority system...")
    tts.speak("Low priority message", priority=0)
    time.sleep(0.5)
    tts.speak("High priority alert!", priority=10)
    
    # Wait for completion
    time.sleep(5)
    tts.shutdown()