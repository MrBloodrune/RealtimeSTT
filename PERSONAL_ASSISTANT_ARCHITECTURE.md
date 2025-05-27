# Personal Assistant Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture Design](#architecture-design)
3. [Project Structure](#project-structure)
4. [Core Components](#core-components)
5. [Database Design](#database-design)
6. [Security Architecture](#security-architecture)
7. [Observability](#observability)
8. [Containerization](#containerization)
9. [Implementation Phases](#implementation-phases)
10. [Integration Examples](#integration-examples)

## Overview

This document outlines the complete architecture for a production-ready Personal Assistant built on top of RealtimeSTT and RealtimeTTS libraries. The system is designed to be:

- **Non-invasive**: Wraps existing libraries without modifying source code
- **Scalable**: Containerized with horizontal scaling support
- **Secure**: Full authentication/authorization with secret management
- **Observable**: Complete metrics, logs, and traces with OpenTelemetry
- **Extensible**: Plugin-based module system for new features
- **Production-ready**: PostgreSQL storage, Redis caching, proper error handling

### Key Features
- Real-time speech-to-text and text-to-speech
- Phone call handling (incoming/outgoing)
- Conversation memory and context awareness
- Multi-user support with role-based access
- Automated transcription storage and retrieval
- LLM integration for intelligent responses
- Wake word activation
- Module-based extensibility

## Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
├─────────────────┬─────────────────┬────────────────────────┤
│   Web Client    │  Phone System   │   Voice Interface      │
│   (WebSocket)   │  (SIP/Twilio)   │   (Direct Mic)        │
└────────┬────────┴────────┬────────┴────────┬──────────────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  WebSocket  │
                    │   Server    │
                    └──────┬──────┘
                           │
         ┌─────────────────▼─────────────────┐
         │      Personal Assistant Core       │
         │  ┌─────────────────────────────┐  │
         │  │    Event Bus System         │  │
         │  └─────────────────────────────┘  │
         │  ┌──────────┐  ┌──────────────┐  │
         │  │   STT    │  │     TTS      │  │
         │  │ Wrapper  │  │   Wrapper    │  │
         │  └──────────┘  └──────────────┘  │
         │  ┌──────────────────────────────┐ │
         │  │   Conversation Manager       │ │
         │  └──────────────────────────────┘ │
         └───────────────┬───────────────────┘
                         │
    ┌────────────────────┴────────────────────┐
    │              Services Layer              │
    ├──────────┬─────────────┬───────────────┤
    │   LLM    │ Transcription│   Telephony  │
    │ Handler  │   Manager    │   Handler    │
    └──────────┴──────┬──────┴───────────────┘
                      │
    ┌─────────────────▼─────────────────────┐
    │           Data Layer                   │
    ├───────────┬──────────┬───────────────┤
    │PostgreSQL │  Redis   │ File Storage  │
    └───────────┴──────────┴───────────────┘
```

### Component Interaction Flow

```
User Speech → Audio Capture → WebSocket → STT Wrapper → 
Event Bus → Conversation Manager → LLM Handler → 
TTS Wrapper → Audio Output → User
                ↓
        Transcription Manager
                ↓
           PostgreSQL
```

## Project Structure

```
personal_assistant/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── assistant.py          # Main PersonalAssistant class
│   ├── stt_wrapper.py        # Enhanced STT with transcription
│   ├── tts_wrapper.py        # Enhanced TTS with queuing
│   ├── conversation.py       # Conversation state management
│   └── container.py          # Dependency injection container
├── modules/
│   ├── __init__.py
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── manager.py        # Transcription storage/retrieval
│   │   ├── formatter.py      # Format transcriptions
│   │   └── models.py         # Data models
│   ├── telephony/
│   │   ├── __init__.py
│   │   ├── handler.py        # Phone call handling
│   │   ├── sip_adapter.py    # SIP/PJSIP integration
│   │   └── twilio_adapter.py # Twilio integration
│   └── llm/
│       ├── __init__.py
│       ├── openai_handler.py # OpenAI integration
│       ├── local_handler.py   # Local LLM support
│       └── prompt_manager.py  # System prompts
├── integrations/
│   ├── __init__.py
│   ├── calendar.py           # Calendar integration
│   ├── contacts.py           # Contacts management
│   └── tasks.py              # Task management
├── interfaces/
│   ├── __init__.py
│   ├── base.py               # Core interfaces (STT, TTS, LLM)
│   ├── modules.py            # Module plugin interface
│   ├── events.py             # Event system interface
│   ├── storage.py            # Storage interface
│   ├── telephony.py          # Phone interface
│   └── context.py            # Assistant context
├── security/
│   ├── __init__.py
│   ├── secrets.py            # OpenBao/Vault integration
│   ├── auth.py               # Keycloak authentication
│   ├── context.py            # User context management
│   └── rotation.py           # Secret rotation automation
├── observability/
│   ├── __init__.py
│   ├── telemetry.py          # OpenTelemetry setup
│   ├── health_metrics.py     # Health monitoring
│   └── dashboards.py         # Grafana dashboard configs
├── config/
│   ├── __init__.py
│   ├── settings.py           # Configuration management
│   ├── secure_config.py      # Secret-aware configuration
│   └── profiles/             # User profiles
│       ├── default.yaml
│       └── phone.yaml        # Phone-specific settings
├── utils/
│   ├── __init__.py
│   ├── audio.py              # Audio utilities
│   ├── events.py             # Event system implementation
│   ├── logger.py             # Structured logging
│   └── health.py             # Health check utilities
├── websocket/
│   ├── __init__.py
│   ├── server.py             # WebSocket server
│   └── secure_server.py      # Authenticated WebSocket
├── adapters/
│   ├── __init__.py
│   ├── base.py               # Base adapter class
│   ├── openai_adapter.py     # OpenAI adapter
│   ├── twilio_adapter.py     # Twilio adapter
│   └── google_adapter.py     # Google services adapter
└── examples/
    ├── basic_assistant.py
    ├── phone_assistant.py
    ├── transcription_demo.py
    └── secure_example.py
```

## Core Components

### 1. Enhanced STT Wrapper

```python
from RealtimeSTT import AudioToTextRecorder
from typing import Optional, Callable, Dict, Any
import threading
import queue
import time

class EnhancedSTT:
    """
    Wrapper around AudioToTextRecorder with additional features:
    - Transcription session management
    - Audio buffering for recording
    - Phone call mode support
    - Event emission through event bus
    - Metrics collection
    """
    
    def __init__(self, 
                 base_config: Dict[str, Any],
                 transcription_manager=None,
                 event_bus=None,
                 telemetry=None):
        # Store original callbacks
        self._user_callbacks = {}
        
        # Internal state
        self._current_session_id = None
        self._audio_buffer = []
        self._is_phone_call = False
        self._phone_metadata = {}
        
        # Inject our callbacks while preserving user's
        enhanced_config = self._enhance_config(base_config)
        self.recorder = AudioToTextRecorder(**enhanced_config)
        
        self.transcription_manager = transcription_manager
        self.event_bus = event_bus
        self.telemetry = telemetry
        
    def _enhance_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance configuration with our callbacks"""
        # Store user callbacks
        callback_names = [
            'on_recording_start', 'on_recording_stop',
            'on_realtime_transcription_update',
            'on_realtime_transcription_stabilized',
            'on_vad_detect_start', 'on_vad_detect_stop',
            'on_wakeword_detected', 'on_recorded_chunk'
        ]
        
        for cb_name in callback_names:
            if cb_name in config:
                self._user_callbacks[cb_name] = config[cb_name]
        
        # Replace with our enhanced callbacks
        config['on_recording_start'] = self._on_recording_start
        config['on_recording_stop'] = self._on_recording_stop
        config['on_recorded_chunk'] = self._on_recorded_chunk
        config['on_realtime_transcription_update'] = self._on_realtime_update
        config['on_realtime_transcription_stabilized'] = self._on_realtime_stabilized
        config['on_vad_detect_start'] = self._on_vad_start
        config['on_vad_detect_stop'] = self._on_vad_stop
        
        return config
        
    def _on_recording_start(self):
        """Enhanced recording start handler"""
        # Create new session if needed
        if not self._current_session_id and self.transcription_manager:
            metadata = {
                'type': 'phone_call' if self._is_phone_call else 'conversation',
                'phone_metadata': self._phone_metadata if self._is_phone_call else None
            }
            self._current_session_id = self.transcription_manager.create_session(metadata)
        
        # Clear audio buffer
        self._audio_buffer = []
        
        # Emit event
        if self.event_bus:
            self.event_bus.emit(Event(
                type=EventType.RECORDING_START,
                data={'session_id': self._current_session_id},
                timestamp=time.time(),
                source='stt_wrapper'
            ))
        
        # Call user callback
        if 'on_recording_start' in self._user_callbacks:
            self._user_callbacks['on_recording_start']()
            
    def _on_recorded_chunk(self, chunk):
        """Store audio chunks for later saving"""
        self._audio_buffer.append(chunk)
        
        # Call user callback
        if 'on_recorded_chunk' in self._user_callbacks:
            self._user_callbacks['on_recorded_chunk'](chunk)
            
    async def process_and_store_transcription(self, text: str):
        """Process completed transcription"""
        if not text or not self.transcription_manager:
            return
            
        # Save audio if we have it
        audio_path = None
        if self._audio_buffer:
            audio_data = b''.join(self._audio_buffer)
            audio_path = await self.transcription_manager.save_audio(
                audio_data,
                self._current_session_id
            )
        
        # Store transcription
        utterance = {
            'session_id': self._current_session_id,
            'text': text,
            'speaker': 'user',
            'timestamp': time.time(),
            'audio_path': audio_path,
            'is_phone_call': self._is_phone_call
        }
        
        await self.transcription_manager.add_utterance(
            self._current_session_id,
            utterance
        )
        
    def set_phone_mode(self, phone_number: str, direction: str):
        """Switch to phone call mode"""
        self._is_phone_call = True
        self._phone_metadata = {
            'number': phone_number,
            'direction': direction,
            'start_time': time.time()
        }
        
        # Create new session for phone call
        if self.transcription_manager:
            self._current_session_id = self.transcription_manager.create_session({
                'type': 'phone_call',
                'phone_number': phone_number,
                'direction': direction
            })
```

### 2. Enhanced TTS Wrapper

```python
from RealtimeTTS import TextToAudioStream
import queue
import threading
from typing import Dict, Any, Optional
import asyncio

class EnhancedTTS:
    """
    TTS wrapper with queuing and priority support:
    - Priority queue for speech ordering
    - Interrupt support for urgent messages
    - Concurrent speech tracking
    - Phone call audio routing
    """
    
    def __init__(self, engine, event_bus=None, telemetry=None):
        self.stream = TextToAudioStream(
            engine,
            on_audio_stream_start=self._on_stream_start,
            on_audio_stream_stop=self._on_stream_stop,
            on_character=self._on_character
        )
        
        self.queue = queue.PriorityQueue()
        self.is_speaking = False
        self.current_text = ""
        self.event_bus = event_bus
        self.telemetry = telemetry
        
        # Phone call audio routing
        self._phone_audio_callback = None
        
        # Start queue processor
        self._queue_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self._queue_thread.start()
        
    def speak(self, text: str, priority: int = 5, metadata: Dict = None):
        """
        Queue text for speaking with priority
        Priority: 1 (highest) to 10 (lowest)
        """
        self.queue.put((priority, time.time(), text, metadata))
        
    def speak_immediate(self, text: str):
        """Interrupt current speech for urgent message"""
        if self.is_speaking:
            self.stream.stop()
        
        self.current_text = text
        self.stream.feed(text)
        self.stream.play_async()
        
    def _process_queue(self):
        """Process speech queue"""
        while True:
            try:
                # Get next item from queue
                priority, timestamp, text, metadata = self.queue.get(timeout=0.1)
                
                # Wait if currently speaking
                while self.is_speaking:
                    time.sleep(0.1)
                
                # Speak the text
                self.current_text = text
                self.stream.feed(text)
                
                if metadata and metadata.get('phone_call') and self._phone_audio_callback:
                    # Route to phone instead of speaker
                    self.stream.play_async(
                        audio_callback=self._phone_audio_callback
                    )
                else:
                    self.stream.play_async()
                
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                if self.event_bus:
                    self.event_bus.emit(Event(
                        type=EventType.TTS_ERROR,
                        data={'error': str(e)},
                        timestamp=time.time(),
                        source='tts_wrapper'
                    ))
                    
    def set_phone_audio_callback(self, callback):
        """Set callback for routing audio to phone"""
        self._phone_audio_callback = callback
```

### 3. Main Assistant Class

```python
class PersonalAssistant:
    """
    Main coordinator for all assistant functions.
    
    Features:
    - Manages STT/TTS lifecycle
    - Coordinates between modules
    - Handles conversation context
    - Manages user sessions
    - Integrates with LLM
    - Supports phone calls
    """
    
    def __init__(self, config_path: str = None):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize event bus
        self.event_bus = EventBus()
        
        # Initialize telemetry
        self.telemetry = TelemetryManager(self.config.get('telemetry', {}))
        
        # Initialize security
        self.secret_manager = SecretManager(self.config.get('secrets', {}))
        self.auth_manager = AuthManager(
            self.config.get('auth', {}),
            self.secret_manager
        )
        
        # Initialize core components
        self.transcription_manager = TranscriptionManager(
            self.config.get('transcription', {}),
            self.telemetry
        )
        
        self.stt = EnhancedSTT(
            self.config.get('stt', {}),
            transcription_manager=self.transcription_manager,
            event_bus=self.event_bus,
            telemetry=self.telemetry
        )
        
        self.tts = EnhancedTTS(
            self._create_tts_engine(),
            event_bus=self.event_bus,
            telemetry=self.telemetry
        )
        
        # Initialize modules
        self.conversation = ConversationManager(
            self.config.get('conversation', {}),
            self.event_bus
        )
        
        self.llm = self._create_llm_handler()
        
        # Module registry
        self.modules = {}
        self._load_modules()
        
        # Phone handling (lazy loaded)
        self._telephony = None
        
        # User sessions
        self.user_sessions = {}
        
        # Register event handlers
        self._register_event_handlers()
        
    def start(self):
        """Start the assistant"""
        # Start telemetry
        self.telemetry.start()
        
        # Start STT processing loop
        self._stt_thread = threading.Thread(
            target=self._stt_loop,
            daemon=True
        )
        self._stt_thread.start()
        
        # Start event processor
        asyncio.create_task(self.event_bus.start())
        
        self.logger.info("Personal Assistant started")
        
    def _stt_loop(self):
        """Main STT processing loop"""
        while True:
            try:
                # Get transcription
                text = self.stt.recorder.text()
                
                if text:
                    # Process transcription
                    asyncio.run(self._process_transcription(text))
                    
            except Exception as e:
                self.logger.error(f"STT loop error: {e}")
                time.sleep(1)
                
    async def _process_transcription(self, text: str):
        """Process completed transcription"""
        with self.telemetry.tracer.start_as_current_span("process_transcription"):
            # Store transcription
            await self.stt.process_and_store_transcription(text)
            
            # Get current context
            context = await self._build_context(text)
            
            # Check modules
            handled = await self._try_modules(text, context)
            
            if not handled:
                # Default LLM processing
                response = await self._get_llm_response(text, context)
                
                # Speak response
                self.tts.speak(response, priority=5)
                
                # Store assistant response
                await self._store_assistant_response(response, context)
                
    async def _build_context(self, text: str) -> AssistantContext:
        """Build context for processing"""
        # Get relevant memories
        memories = await self.transcription_manager.search_conversations(
            text,
            limit=5
        )
        
        # Get user preferences
        user_prefs = await self._get_user_preferences()
        
        return AssistantContext(
            session_id=self.stt._current_session_id,
            user_id=self._current_user_id,
            conversation_history=self.conversation.get_history(),
            relevant_memories=memories,
            user_preferences=user_prefs,
            is_phone_call=self.stt._is_phone_call,
            phone_number=self.stt._phone_metadata.get('number')
        )
        
    def register_module(self, module: AssistantModule):
        """Register a new module"""
        self.modules[module.name] = module
        module.assistant = self
        asyncio.create_task(module.on_activate())
        
    async def handle_phone_call(self, call_info: Dict):
        """Handle incoming/outgoing phone calls"""
        if not self._telephony:
            from ..modules.telephony import TelephonyHandler
            self._telephony = TelephonyHandler(
                self.config.get('telephony', {}),
                self.telemetry
            )
            
        # Switch to phone mode
        self.stt.set_phone_mode(
            call_info['number'],
            call_info['direction']
        )
        
        # Set TTS phone routing
        self.tts.set_phone_audio_callback(
            self._telephony.send_audio_to_call
        )
        
        # Start call handling
        await self._telephony.handle_call(call_info)
```

### 4. Conversation Manager

```python
class ConversationManager:
    """
    Manages conversation state and history.
    
    Features:
    - Conversation history with sliding window
    - Context tracking
    - Turn management
    - Memory integration
    """
    
    def __init__(self, config: Dict, event_bus: EventBus):
        self.max_history = config.get('max_history', 10)
        self.history = []
        self.context = {}
        self.event_bus = event_bus
        
    def add_turn(self, role: str, content: str, metadata: Dict = None):
        """Add a conversation turn"""
        turn = {
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        self.history.append(turn)
        
        # Maintain sliding window
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
        # Emit event
        self.event_bus.emit(Event(
            type=EventType.CONVERSATION_TURN,
            data=turn,
            timestamp=time.time(),
            source='conversation_manager'
        ))
        
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation history"""
        if limit:
            return self.history[-limit:]
        return self.history.copy()
        
    def get_context_for_llm(self) -> List[Dict]:
        """Format conversation for LLM"""
        return [
            {'role': turn['role'], 'content': turn['content']}
            for turn in self.history
        ]
        
    def clear_history(self):
        """Clear conversation history"""
        self.history.clear()
        self.context.clear()
```

## Database Design

### PostgreSQL Schema

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For pgvector
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search

-- Users table (synced with Keycloak)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keycloak_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    type VARCHAR(50) NOT NULL, -- 'conversation', 'phone_call', 'meeting'
    metadata JSONB DEFAULT '{}',
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (type IN ('conversation', 'phone_call', 'meeting'))
);

-- Utterances table
CREATE TABLE utterances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    speaker VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'caller'
    text TEXT NOT NULL,
    text_vector vector(1536), -- For semantic search
    timestamp TIMESTAMPTZ NOT NULL,
    confidence FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (speaker IN ('user', 'assistant', 'caller'))
);

-- Audio recordings table
CREATE TABLE audio_recordings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    utterance_id UUID REFERENCES utterances(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    duration_seconds FLOAT NOT NULL,
    format VARCHAR(20) NOT NULL,
    size_bytes BIGINT NOT NULL,
    sample_rate INTEGER,
    channels INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Phone calls table
CREATE TABLE phone_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL, -- 'incoming', 'outgoing'
    duration_seconds FLOAT,
    status VARCHAR(20) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (direction IN ('incoming', 'outgoing')),
    CHECK (status IN ('initiated', 'ringing', 'connected', 'completed', 'failed'))
);

-- Module interactions table
CREATE TABLE module_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    module_name VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    input_data JSONB NOT NULL,
    output_data JSONB,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    learned_from_session UUID REFERENCES sessions(id),
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, category, preference_key)
);

-- Memories table (for long-term storage)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'fact', 'preference', 'relationship', 'event'
    content TEXT NOT NULL,
    content_vector vector(1536),
    importance FLOAT DEFAULT 0.5,
    source_session_id UUID REFERENCES sessions(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_sessions_user_time ON sessions(user_id, start_time DESC);
CREATE INDEX idx_utterances_session_timestamp ON utterances(session_id, timestamp);
CREATE INDEX idx_utterances_speaker ON utterances(speaker);
CREATE INDEX idx_utterances_text_search ON utterances USING GIN(to_tsvector('english', text));
CREATE INDEX idx_utterances_vector ON utterances USING ivfflat (text_vector vector_cosine_ops);
CREATE INDEX idx_phone_calls_number ON phone_calls(phone_number);
CREATE INDEX idx_memories_user_vector ON memories(user_id) USING ivfflat (content_vector vector_cosine_ops);

-- Full-text search support
ALTER TABLE utterances ADD COLUMN text_search tsvector 
    GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;
CREATE INDEX idx_utterances_fts ON utterances USING GIN(text_search);

-- Create views for common queries
CREATE VIEW recent_conversations AS
SELECT 
    s.id as session_id,
    s.user_id,
    s.start_time,
    s.type,
    COUNT(u.id) as utterance_count,
    MAX(u.timestamp) as last_utterance,
    ARRAY_AGG(DISTINCT u.speaker) as speakers
FROM sessions s
LEFT JOIN utterances u ON s.id = u.session_id
WHERE s.start_time > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY s.id;

-- Materialized view for conversation statistics
CREATE MATERIALIZED VIEW conversation_stats AS
SELECT 
    DATE_TRUNC('day', s.start_time) as day,
    s.user_id,
    s.type,
    COUNT(DISTINCT s.id) as session_count,
    COUNT(u.id) as total_utterances,
    AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time))) as avg_duration_seconds,
    COUNT(DISTINCT CASE WHEN u.speaker = 'user' THEN u.id END) as user_utterances,
    COUNT(DISTINCT CASE WHEN u.speaker = 'assistant' THEN u.id END) as assistant_utterances
FROM sessions s
LEFT JOIN utterances u ON s.id = u.session_id
WHERE s.end_time IS NOT NULL
GROUP BY DATE_TRUNC('day', s.start_time), s.user_id, s.type
WITH DATA;

-- Refresh materialized view periodically
CREATE OR REPLACE FUNCTION refresh_conversation_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY conversation_stats;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Function to calculate session duration
CREATE OR REPLACE FUNCTION calculate_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.end_time IS NOT NULL AND NEW.start_time IS NOT NULL THEN
        -- Update phone call duration if applicable
        UPDATE phone_calls 
        SET duration_seconds = EXTRACT(EPOCH FROM (NEW.end_time - NEW.start_time))
        WHERE session_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_session_duration
    AFTER UPDATE OF end_time ON sessions
    FOR EACH ROW
    WHEN (NEW.end_time IS NOT NULL)
    EXECUTE FUNCTION calculate_session_duration();
```

### Redis Cache Schema

```python
# Cache key patterns
CACHE_PATTERNS = {
    # User preferences cache
    'user_preferences': 'user:{user_id}:preferences',
    
    # Active sessions
    'active_session': 'session:{session_id}:active',
    
    # Conversation history
    'conversation_history': 'session:{session_id}:history',
    
    # LLM response cache
    'llm_cache': 'llm:hash:{prompt_hash}',
    
    # User authentication tokens
    'auth_token': 'auth:token:{token_id}',
    
    # Module state
    'module_state': 'module:{module_name}:state:{session_id}',
    
    # Audio buffer for streaming
    'audio_buffer': 'audio:buffer:{session_id}',
    
    # Rate limiting
    'rate_limit': 'ratelimit:{user_id}:{action}',
}

# TTL settings (seconds)
CACHE_TTL = {
    'user_preferences': 3600,        # 1 hour
    'active_session': 1800,          # 30 minutes
    'conversation_history': 7200,    # 2 hours
    'llm_cache': 86400,             # 24 hours
    'auth_token': 3600,             # 1 hour
    'module_state': 1800,           # 30 minutes
    'audio_buffer': 300,            # 5 minutes
    'rate_limit': 60,               # 1 minute
}
```

## Security Architecture

### OpenBao/Vault Configuration

```hcl
# config/openbao/config.hcl
storage "raft" {
  path    = "/vault/data"
  node_id = "node1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/certs/cert.pem"
  tls_key_file  = "/vault/certs/key.pem"
}

api_addr = "https://openbao:8200"
cluster_addr = "https://openbao:8201"
ui = true

# Audit logging
audit {
  file {
    path = "/vault/logs/audit.log"
  }
}
```

### Secret Structure

```yaml
# Vault secret paths
secret/
├── api-keys/
│   ├── openai          # OpenAI API key
│   ├── azure-speech    # Azure Speech Services key
│   ├── elevenlabs      # ElevenLabs API key
│   └── twilio          # Twilio credentials
├── database/
│   ├── admin-password  # PostgreSQL admin
│   └── app-password    # Application user
├── keycloak/
│   ├── admin          # Keycloak admin credentials
│   └── client-secret  # Client secret
├── encryption/
│   ├── master-key     # Master encryption key
│   └── jwt-secret     # JWT signing secret
└── certificates/
    ├── tls-cert       # TLS certificate
    └── tls-key        # TLS private key
```

### Keycloak Realm Configuration

```json
{
  "realm": "personal-assistant",
  "enabled": true,
  "sslRequired": "external",
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "resetPasswordAllowed": true,
  "editUsernameAllowed": false,
  "bruteForceProtected": true,
  "permanentLockout": false,
  "maxFailureWaitSeconds": 900,
  "minimumQuickLoginWaitSeconds": 60,
  "waitIncrementSeconds": 60,
  "quickLoginCheckMilliSeconds": 1000,
  "maxDeltaTimeSeconds": 43200,
  "failureFactor": 5,
  "defaultRoles": ["user"],
  "requiredCredentials": ["password"],
  "passwordPolicy": "length(12) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)",
  
  "clients": [
    {
      "clientId": "assistant-client",
      "enabled": true,
      "clientAuthenticatorType": "client-secret",
      "secret": "${vault.secret/keycloak/client-secret}",
      "redirectUris": [
        "http://localhost:3000/*",
        "https://assistant.example.com/*"
      ],
      "webOrigins": ["+"],
      "standardFlowEnabled": true,
      "implicitFlowEnabled": false,
      "directAccessGrantsEnabled": true,
      "serviceAccountsEnabled": true,
      "authorizationServicesEnabled": false,
      "protocol": "openid-connect",
      "bearerOnly": false,
      "consentRequired": false,
      "defaultClientScopes": [
        "web-origins",
        "profile",
        "roles",
        "email"
      ],
      "optionalClientScopes": [
        "address",
        "phone",
        "offline_access"
      ]
    }
  ],
  
  "roles": {
    "realm": [
      {
        "name": "user",
        "description": "Basic user access",
        "composite": false,
        "clientRole": false
      },
      {
        "name": "admin",
        "description": "Administrative access",
        "composite": true,
        "composites": {
          "realm": ["user"]
        },
        "clientRole": false
      },
      {
        "name": "phone_user",
        "description": "Can make and receive phone calls",
        "composite": false,
        "clientRole": false
      },
      {
        "name": "premium",
        "description": "Premium features access",
        "composite": true,
        "composites": {
          "realm": ["user", "phone_user"]
        },
        "clientRole": false
      }
    ]
  },
  
  "groups": [
    {
      "name": "family",
      "realmRoles": ["user", "phone_user"]
    },
    {
      "name": "administrators",
      "realmRoles": ["admin", "user", "phone_user", "premium"]
    }
  ],
  
  "authenticationFlows": [
    {
      "alias": "mfa-flow",
      "description": "Multi-factor authentication flow",
      "providerId": "basic-flow",
      "topLevel": true,
      "builtIn": false,
      "authenticationExecutions": [
        {
          "authenticator": "auth-username-password-form",
          "requirement": "REQUIRED",
          "priority": 10
        },
        {
          "authenticator": "auth-otp-form",
          "requirement": "OPTIONAL",
          "priority": 20
        }
      ]
    }
  ],
  
  "components": {
    "org.keycloak.storage.UserStorageProvider": [
      {
        "name": "assistant-user-storage",
        "providerId": "ldap",
        "providerType": "org.keycloak.storage.UserStorageProvider",
        "config": {
          "enabled": ["true"],
          "priority": ["0"],
          "fullSyncPeriod": ["3600"],
          "changedSyncPeriod": ["900"]
        }
      }
    ]
  },
  
  "identityProviders": [
    {
      "alias": "google",
      "providerId": "google",
      "enabled": true,
      "trustEmail": true,
      "storeToken": false,
      "addReadTokenRoleOnCreate": false,
      "config": {
        "clientId": "${env.GOOGLE_CLIENT_ID}",
        "clientSecret": "${vault.secret/oauth/google-secret}",
        "syncMode": "IMPORT",
        "useJwksUrl": "true"
      }
    }
  ]
}
```

### Authentication Flow

```python
# personal_assistant/security/auth_flow.py
class AuthenticationFlow:
    """Complete authentication flow implementation"""
    
    async def login_flow(self, username: str, password: str, mfa_code: Optional[str] = None):
        """
        Complete login flow:
        1. Authenticate with Keycloak
        2. Validate MFA if required
        3. Create session
        4. Return tokens
        """
        # Initial authentication
        auth_result = await self.auth_manager.authenticate_user(username, password)
        
        # Check if MFA required
        if 'mfa_required' in auth_result:
            if not mfa_code:
                return {'status': 'mfa_required', 'session': auth_result['session']}
            
            # Validate MFA
            mfa_result = await self.auth_manager.validate_mfa(
                auth_result['session'],
                mfa_code
            )
            
            if not mfa_result['valid']:
                raise AuthenticationError("Invalid MFA code")
                
        # Create user session
        session = await self.create_user_session(auth_result)
        
        # Store in Redis for quick access
        await self.cache.set(
            f"auth:session:{session['id']}",
            json.dumps(session),
            ex=3600  # 1 hour
        )
        
        return {
            'status': 'success',
            'access_token': auth_result['access_token'],
            'refresh_token': auth_result['refresh_token'],
            'session_id': session['id'],
            'user': {
                'id': auth_result['user_id'],
                'username': auth_result['username'],
                'roles': auth_result['roles']
            }
        }
```

## Observability

### OpenTelemetry Configuration

```python
# personal_assistant/observability/config.py
OTEL_CONFIG = {
    'service_name': 'personal-assistant',
    'service_version': '1.0.0',
    'deployment_environment': os.getenv('ENVIRONMENT', 'development'),
    
    'exporters': {
        'otlp': {
            'endpoint': os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'),
            'headers': os.getenv('OTEL_EXPORTER_OTLP_HEADERS', ''),
            'compression': 'gzip',
            'timeout': 10,
        }
    },
    
    'traces': {
        'sampler': 'parentbased_traceidratio',
        'sampler_arg': 0.1,  # Sample 10% of traces
        'max_attribute_length': 4096,
        'max_span_attributes': 128,
    },
    
    'metrics': {
        'export_interval': 60000,  # 1 minute
        'export_timeout': 30000,   # 30 seconds
    },
    
    'logs': {
        'export_interval': 10000,  # 10 seconds
        'export_timeout': 5000,    # 5 seconds
    }
}

# Instrumentation configuration
INSTRUMENTATION_CONFIG = {
    'asyncpg': {'capture_parameters': True},
    'redis': {'capture_statement': True},
    'httpx': {'capture_headers': True},
    'asyncio': {'enable': True},
}
```

### Metrics Definition

```python
# personal_assistant/observability/metrics.py
class AssistantMetrics:
    """Application-specific metrics"""
    
    def __init__(self, meter):
        # Counters
        self.transcriptions = meter.create_counter(
            "assistant.transcriptions.total",
            description="Total transcriptions processed",
            unit="1"
        )
        
        self.tts_requests = meter.create_counter(
            "assistant.tts.requests.total",
            description="Total TTS requests",
            unit="1"
        )
        
        self.llm_requests = meter.create_counter(
            "assistant.llm.requests.total",
            description="Total LLM API requests",
            unit="1"
        )
        
        self.errors = meter.create_counter(
            "assistant.errors.total",
            description="Total errors by type",
            unit="1"
        )
        
        # Histograms
        self.transcription_duration = meter.create_histogram(
            "assistant.transcription.duration",
            description="Transcription processing duration",
            unit="s"
        )
        
        self.llm_latency = meter.create_histogram(
            "assistant.llm.response.latency",
            description="LLM response latency",
            unit="s"
        )
        
        self.e2e_latency = meter.create_histogram(
            "assistant.e2e.latency",
            description="End-to-end response latency",
            unit="s"
        )
        
        # Gauges
        self.active_sessions = meter.create_up_down_counter(
            "assistant.sessions.active",
            description="Currently active sessions",
            unit="1"
        )
        
        self.memory_usage = meter.create_observable_gauge(
            "assistant.memory.usage",
            callbacks=[self._observe_memory_usage],
            description="Memory usage in bytes",
            unit="By"
        )
        
        self.model_load_status = meter.create_observable_gauge(
            "assistant.models.loaded",
            callbacks=[self._observe_model_status],
            description="Model loading status",
            unit="1"
        )
```

### Distributed Tracing

```python
# personal_assistant/observability/tracing.py
class TracedAssistant:
    """Assistant with distributed tracing"""
    
    @trace_method
    async def process_request(self, audio_data: bytes, context: Dict):
        """Process request with full tracing"""
        span = trace.get_current_span()
        
        # Add request attributes
        span.set_attributes({
            "assistant.request.audio_size": len(audio_data),
            "assistant.request.user_id": context.get('user_id'),
            "assistant.request.session_id": context.get('session_id'),
        })
        
        # STT processing
        with tracer.start_as_current_span("stt_processing") as stt_span:
            stt_start = time.time()
            text = await self.stt.process_audio(audio_data)
            
            stt_span.set_attributes({
                "stt.text_length": len(text) if text else 0,
                "stt.duration": time.time() - stt_start,
                "stt.model": self.config['stt']['model']
            })
            
        # LLM processing
        with tracer.start_as_current_span("llm_processing") as llm_span:
            llm_start = time.time()
            response = await self.llm.get_response(text, context)
            
            llm_span.set_attributes({
                "llm.prompt_tokens": self._count_tokens(text),
                "llm.response_tokens": self._count_tokens(response),
                "llm.duration": time.time() - llm_start,
                "llm.model": self.config['llm']['model']
            })
            
        # TTS processing
        with tracer.start_as_current_span("tts_processing") as tts_span:
            tts_start = time.time()
            audio_response = await self.tts.synthesize(response)
            
            tts_span.set_attributes({
                "tts.text_length": len(response),
                "tts.audio_duration": self._get_audio_duration(audio_response),
                "tts.duration": time.time() - tts_start,
                "tts.engine": self.config['tts']['engine']
            })
            
        return audio_response
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Personal Assistant Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(assistant_transcriptions_total[5m])"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(assistant_errors_total[5m]) / rate(assistant_transcriptions_total[5m])"
        }]
      },
      {
        "title": "Response Time (P95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(assistant_e2e_latency_bucket[5m]))"
        }]
      },
      {
        "title": "Active Sessions",
        "targets": [{
          "expr": "assistant_sessions_active"
        }]
      },
      {
        "title": "LLM Token Usage",
        "targets": [{
          "expr": "sum(rate(assistant_llm_requests_total[5m])) by (model)"
        }]
      },
      {
        "title": "Memory Usage",
        "targets": [{
          "expr": "assistant_memory_usage / 1024 / 1024"
        }]
      }
    ]
  }
}
```

## Containerization

### Production Dockerfile

```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Build stage for GPU support
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04 as gpu-base

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-distutils \
    portaudio19-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Final stage
FROM gpu-base as final

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Create non-root user
RUN useradd -m -u 1000 assistant && \
    mkdir -p /app /app/models /app/audio_cache /app/logs && \
    chown -R assistant:assistant /app

USER assistant
WORKDIR /app

# Copy application code
COPY --chown=assistant:assistant . .

# Download models at build time
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium.en', device='cuda', compute_type='float16')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()"

# Entry point
ENTRYPOINT ["python", "-m", "personal_assistant"]
CMD ["--config", "/app/config/production.yaml"]
```

### Docker Compose Production

```yaml
version: '3.9'

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:
  # Personal Assistant
  assistant:
    build:
      context: .
      dockerfile: Dockerfile
      target: final
    image: personal-assistant:${VERSION:-latest}
    container_name: personal-assistant
    restart: unless-stopped
    logging: *default-logging
    environment:
      - ENVIRONMENT=production
      - VAULT_ADDR=http://openbao:8200
      - VAULT_ROLE_ID=${VAULT_ROLE_ID}
      - VAULT_SECRET_ID=${VAULT_SECRET_ID}
      - KEYCLOAK_URL=http://keycloak:8080
      - KEYCLOAK_REALM=personal-assistant
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - OTEL_SERVICE_NAME=personal-assistant
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317
    volumes:
      - ./models:/app/models:ro
      - audio_cache:/app/audio_cache
      - ./config:/app/config:ro
    ports:
      - "9999:9999"  # WebSocket
      - "8000:8000"  # HTTP API
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      openbao:
        condition: service_started
      keycloak:
        condition: service_healthy
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    networks:
      - assistant-network
    
  # PostgreSQL with pgvector
  postgres:
    image: pgvector/pgvector:17-alpine
    container_name: assistant-postgres
    restart: unless-stopped
    logging: *default-logging
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: personal_assistant
      POSTGRES_INITDB_ARGS: "-c shared_preload_libraries=vector"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/001-init.sql:ro
      - ./scripts/backup.sh:/usr/local/bin/backup.sh:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - assistant-network
    
  # Redis for caching
  redis:
    image: redis:7-alpine
    container_name: assistant-redis
    restart: unless-stopped
    logging: *default-logging
    command: >
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "--pass", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - assistant-network
    
  # OpenBao (Vault fork) for secrets
  openbao:
    image: openbao/openbao:latest
    container_name: assistant-openbao
    restart: unless-stopped
    logging: *default-logging
    cap_add:
      - IPC_LOCK
    environment:
      VAULT_ADDR: http://0.0.0.0:8200
      VAULT_API_ADDR: http://openbao:8200
      VAULT_CLUSTER_ADDR: http://openbao:8201
    volumes:
      - ./config/openbao:/vault/config:ro
      - openbao_data:/vault/data
      - openbao_logs:/vault/logs
    ports:
      - "8200:8200"
      - "8201:8201"
    command: server
    networks:
      - assistant-network
    
  # Keycloak for authentication
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: assistant-keycloak
    restart: unless-stopped
    logging: *default-logging
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KEYCLOAK_DB_PASSWORD}
      KC_HOSTNAME: keycloak
      KC_HOSTNAME_STRICT: false
      KC_HTTP_ENABLED: true
      KC_HTTP_PORT: 8080
      KC_HEALTH_ENABLED: true
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
    volumes:
      - ./config/keycloak/realm.json:/opt/keycloak/data/import/realm.json:ro
    ports:
      - "8080:8080"
    command: start --import-realm
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - assistant-network
    
  # Grafana Alloy for observability
  alloy:
    image: grafana/alloy:latest
    container_name: assistant-alloy
    restart: unless-stopped
    logging: *default-logging
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
      - "12345:12345" # Alloy UI
    volumes:
      - ./config/alloy/config.alloy:/etc/alloy/config.alloy:ro
      - alloy_data:/var/lib/alloy
    command: run /etc/alloy/config.alloy
    environment:
      - GRAFANA_CLOUD_API_KEY=${GRAFANA_CLOUD_API_KEY}
      - GRAFANA_CLOUD_PROMETHEUS_ENDPOINT=${GRAFANA_CLOUD_PROMETHEUS_ENDPOINT}
      - GRAFANA_CLOUD_LOKI_ENDPOINT=${GRAFANA_CLOUD_LOKI_ENDPOINT}
      - GRAFANA_CLOUD_TEMPO_ENDPOINT=${GRAFANA_CLOUD_TEMPO_ENDPOINT}
    networks:
      - assistant-network

volumes:
  postgres_data:
  redis_data:
  openbao_data:
  openbao_logs:
  alloy_data:
  audio_cache:

networks:
  assistant-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Kubernetes Deployment (Optional)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: personal-assistant
  labels:
    app: personal-assistant
spec:
  replicas: 3
  selector:
    matchLabels:
      app: personal-assistant
  template:
    metadata:
      labels:
        app: personal-assistant
    spec:
      containers:
      - name: assistant
        image: personal-assistant:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
            nvidia.com/gpu: 1
          limits:
            memory: "4Gi"
            cpu: "2000m"
            nvidia.com/gpu: 1
        env:
        - name: VAULT_ADDR
          value: "http://vault:8200"
        - name: VAULT_ROLE_ID
          valueFrom:
            secretKeyRef:
              name: vault-creds
              key: role-id
        - name: VAULT_SECRET_ID
          valueFrom:
            secretKeyRef:
              name: vault-creds
              key: secret-id
        volumeMounts:
        - name: models
          mountPath: /app/models
          readOnly: true
        - name: audio-cache
          mountPath: /app/audio_cache
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: models-pvc
      - name: audio-cache
        emptyDir:
          sizeLimit: 10Gi
```

## Implementation Phases

### Phase 1: Core Wrapper Implementation (Week 1-2)

**Goal**: Create basic wrappers around RealtimeSTT/TTS

1. **Setup Project Structure**
   ```bash
   mkdir -p personal_assistant/{core,modules,interfaces,config,utils}
   touch personal_assistant/__init__.py
   ```

2. **Implement Basic Wrappers**
   - EnhancedSTT with event callbacks
   - EnhancedTTS with queue support
   - Basic PersonalAssistant coordinator
   - Simple event bus

3. **Create Examples**
   - Basic conversation example
   - Simple transcription storage

**Deliverables**:
- Working STT/TTS wrappers
- Basic assistant that can hear and respond
- Event system foundation

### Phase 2: Transcription System (Week 3-4)

**Goal**: Implement full transcription management

1. **Database Setup**
   - PostgreSQL with pgvector
   - Create schema and indexes
   - Setup connection pooling

2. **Transcription Manager**
   - Session management
   - Utterance storage
   - Audio file handling
   - Search capabilities

3. **Memory System**
   - Conversation history
   - Semantic search
   - Context retrieval

**Deliverables**:
- Complete transcription storage
- Searchable conversation history
- Audio recording management

### Phase 3: LLM Integration (Week 5-6)

**Goal**: Add intelligent conversation capabilities

1. **LLM Handlers**
   - OpenAI adapter
   - Local LLM support
   - Response streaming

2. **Conversation Management**
   - Context building
   - Prompt engineering
   - Memory integration

3. **Module System**
   - Base module interface
   - Module registration
   - Event routing

**Deliverables**:
- Intelligent assistant responses
- Modular architecture
- Context-aware conversations

### Phase 4: Security Implementation (Week 7-8)

**Goal**: Add authentication and secret management

1. **OpenBao Integration**
   - Secret storage setup
   - Dynamic credentials
   - Secret rotation

2. **Keycloak Integration**
   - Realm configuration
   - Authentication flow
   - Role-based access

3. **Secure WebSocket**
   - Token validation
   - Session management
   - Encrypted communications

**Deliverables**:
- Full authentication system
- Secure secret management
- Multi-user support

### Phase 5: Advanced Features (Week 9-10)

**Goal**: Add phone support and advanced features

1. **Phone Integration**
   - SIP/Twilio adapters
   - Audio routing
   - Call management

2. **Additional Modules**
   - Calendar integration
   - Task management
   - Email handling

3. **Performance Optimization**
   - Caching strategies
   - Query optimization
   - Resource management

**Deliverables**:
- Phone call support
- Extended module ecosystem
- Optimized performance

### Phase 6: Production Readiness (Week 11-12)

**Goal**: Prepare for production deployment

1. **Observability**
   - Complete OTEL integration
   - Grafana dashboards
   - Alerting rules

2. **Containerization**
   - Docker images
   - Compose configuration
   - Kubernetes manifests

3. **Documentation**
   - API documentation
   - Deployment guide
   - User manual

**Deliverables**:
- Production-ready containers
- Complete observability
- Comprehensive documentation

## Integration Examples

### Basic Usage Example

```python
# examples/basic_assistant.py
import asyncio
from personal_assistant import PersonalAssistant

async def main():
    # Initialize assistant
    assistant = PersonalAssistant('config/default.yaml')
    
    # Register event handlers
    @assistant.event_bus.on(EventType.TRANSCRIPTION_FINAL)
    async def on_transcription(event):
        print(f"User said: {event.data['text']}")
    
    @assistant.event_bus.on(EventType.TTS_START)
    async def on_tts_start(event):
        print(f"Assistant saying: {event.data['text']}")
    
    # Start assistant
    await assistant.start()
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

### Phone Integration Example

```python
# examples/phone_assistant.py
import asyncio
from personal_assistant import PersonalAssistant
from personal_assistant.modules.telephony import TwilioAdapter

async def main():
    # Initialize with phone support
    assistant = PersonalAssistant('config/phone.yaml')
    
    # Setup Twilio
    telephony = TwilioAdapter(assistant.config['twilio'])
    assistant.set_telephony_adapter(telephony)
    
    # Handle incoming calls
    @telephony.on_incoming_call
    async def handle_incoming(call_info):
        print(f"Incoming call from {call_info['from']}")
        
        # Answer call
        await assistant.handle_phone_call({
            'number': call_info['from'],
            'direction': 'incoming',
            'call_sid': call_info['sid']
        })
        
        # Greet caller
        assistant.tts.speak_immediate(
            f"Hello, you've reached the AI assistant. How can I help you?",
            metadata={'phone_call': True}
        )
    
    # Start services
    await assistant.start()
    await telephony.start()
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

### Module Development Example

```python
# examples/weather_module.py
from personal_assistant.interfaces.modules import AssistantModule
import aiohttp

class WeatherModule(AssistantModule):
    name = "weather"
    triggers = ["weather", "temperature", "forecast", "rain", "snow"]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def can_handle(self, text: str, context: Dict) -> bool:
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in self.triggers)
        
    async def handle(self, text: str, context: Dict) -> Dict[str, Any]:
        # Extract location
        location = self._extract_location(text) or "current location"
        
        # Get weather data
        weather = await self._get_weather(location)
        
        # Format response
        response = self._format_weather_response(weather)
        
        return {
            'response': response,
            'speak': True,
            'data': weather
        }
        
    async def _get_weather(self, location: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            async with session.get(
                f"{self.base_url}/weather",
                params=params
            ) as resp:
                return await resp.json()
                
    def _format_weather_response(self, weather: Dict) -> str:
        temp = weather['main']['temp']
        desc = weather['weather'][0]['description']
        location = weather['name']
        
        return f"The weather in {location} is currently {desc} with a temperature of {temp} degrees Celsius."

# Usage
assistant = PersonalAssistant()
weather_module = WeatherModule(api_key="your-api-key")
assistant.register_module(weather_module)
```

### Secure WebSocket Client Example

```python
# examples/secure_client.py
import asyncio
import websockets
import json
from keycloak import KeycloakOpenID

async def authenticated_client():
    # Get token from Keycloak
    keycloak = KeycloakOpenID(
        server_url="http://localhost:8080",
        client_id="assistant-client",
        realm_name="personal-assistant"
    )
    
    token = keycloak.token("username", "password")
    
    # Connect to WebSocket
    async with websockets.connect("ws://localhost:9999") as websocket:
        # Authenticate
        await websocket.send(json.dumps({
            'type': 'auth',
            'token': token['access_token']
        }))
        
        # Wait for auth response
        auth_response = json.loads(await websocket.recv())
        
        if auth_response['type'] == 'auth_success':
            print(f"Connected as {auth_response['username']}")
            
            # Send audio or commands
            await websocket.send(json.dumps({
                'type': 'command',
                'data': 'start_listening'
            }))
            
            # Handle messages
            async for message in websocket:
                data = json.loads(message)
                print(f"Received: {data}")

if __name__ == "__main__":
    asyncio.run(authenticated_client())
```

## Configuration Templates

### Default Configuration

```yaml
# config/default.yaml
service:
  name: personal-assistant
  version: 1.0.0
  environment: development

stt:
  model: medium.en
  language: en
  realtime_model_type: tiny.en
  enable_realtime_transcription: true
  use_microphone: false
  silero_sensitivity: 0.4
  post_speech_silence_duration: 0.4
  min_length_of_recording: 0.3

tts:
  engine: azure
  azure:
    voice: en-US-JennyNeural
    rate: 0
    pitch: 0
  system:
    voice: Microsoft David Desktop
  elevenlabs:
    voice_id: EXAVITQu4vr4xnSDxMaL
    model: eleven_monolingual_v1

llm:
  provider: openai
  openai:
    model: gpt-4
    temperature: 0.7
    max_tokens: 500
    streaming: true
  local:
    model_path: /app/models/llama-2-7b
    context_length: 4096

transcription:
  storage_path: /app/transcriptions
  audio_format: wav
  save_audio: true
  retention_days: 90

database:
  host: postgres
  port: 5432
  database: personal_assistant
  pool_size: 20

redis:
  host: redis
  port: 6379
  db: 0

security:
  auth_required: true
  mfa_enabled: false
  session_timeout: 3600

telemetry:
  enabled: true
  otlp_endpoint: http://alloy:4317
  service_name: personal-assistant
  trace_sample_rate: 0.1

modules:
  enabled:
    - transcription
    - conversation
    - calendar
    - weather
```

### Production Configuration

```yaml
# config/production.yaml
service:
  name: personal-assistant
  version: 1.0.0
  environment: production

stt:
  model: large-v2
  language: en
  realtime_model_type: base.en
  enable_realtime_transcription: true
  use_microphone: false
  silero_sensitivity: 0.3
  post_speech_silence_duration: 0.5
  min_length_of_recording: 0.5
  compute_type: float16
  device: cuda

tts:
  engine: azure
  cache_enabled: true
  cache_ttl: 86400

llm:
  provider: openai
  openai:
    model: gpt-4-turbo-preview
    temperature: 0.7
    max_tokens: 1000
    streaming: true
  cache_enabled: true
  cache_ttl: 3600

database:
  host: postgres
  port: 5432
  database: personal_assistant
  pool_size: 50
  ssl_mode: require

redis:
  host: redis
  port: 6379
  password: ${REDIS_PASSWORD}
  ssl: true

security:
  auth_required: true
  mfa_enabled: true
  session_timeout: 1800
  token_refresh_interval: 300

telemetry:
  enabled: true
  otlp_endpoint: ${OTEL_ENDPOINT}
  service_name: personal-assistant
  trace_sample_rate: 0.01
  
backup:
  enabled: true
  schedule: "0 2 * * *"
  retention_days: 30
  s3_bucket: ${BACKUP_BUCKET}
```

## Maintenance and Operations

### Backup Strategy

```bash
#!/bin/bash
# scripts/backup.sh

# Database backup
pg_dump -h postgres -U postgres personal_assistant | \
  gzip > /backups/db_$(date +%Y%m%d_%H%M%S).sql.gz

# Audio files backup
tar -czf /backups/audio_$(date +%Y%m%d_%H%M%S).tar.gz /app/audio_cache

# Upload to S3
aws s3 sync /backups s3://${BACKUP_BUCKET}/backups/

# Clean old backups
find /backups -mtime +30 -delete
```

### Monitoring Alerts

```yaml
# monitoring/alerts.yaml
groups:
  - name: assistant_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(assistant_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High error rate detected
          
      - alert: SlowResponse
        expr: histogram_quantile(0.95, assistant_e2e_latency_bucket) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: Slow response times
          
      - alert: LowDiskSpace
        expr: node_filesystem_avail_bytes{mountpoint="/app/audio_cache"} < 1073741824
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: Low disk space for audio cache
```

### Health Checks

```python
# personal_assistant/utils/health.py
async def health_check():
    """Comprehensive health check"""
    checks = {
        'database': await check_database(),
        'redis': await check_redis(),
        'models': check_models_loaded(),
        'auth': await check_auth_service(),
        'disk_space': check_disk_space(),
        'memory': check_memory_usage()
    }
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    
    return {
        'status': status,
        'timestamp': time.time(),
        'checks': checks,
        'version': '1.0.0'
    }
```

## Conclusion

This architecture provides a robust, scalable, and secure foundation for a personal assistant that:

1. **Preserves original functionality** of RealtimeSTT/TTS
2. **Adds enterprise features** like authentication, observability, and persistence
3. **Supports multiple deployment options** from development to production
4. **Enables easy extension** through the module system
5. **Maintains security** with proper secret management and authentication
6. **Provides insights** through comprehensive observability

The modular design ensures that each component can be developed, tested, and deployed independently while maintaining clean interfaces between systems.