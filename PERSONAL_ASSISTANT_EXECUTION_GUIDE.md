# Personal Assistant Execution Guide

This guide provides step-by-step instructions for implementing the Personal Assistant architecture described in `PERSONAL_ASSISTANT_ARCHITECTURE.md`.

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ or Alma Linux 9 recommended)
- **Python**: 3.11+
- **RAM**: 16GB minimum (32GB recommended)
- **GPU**: NVIDIA with CUDA 12.4+ support (optional but recommended)
- **Storage**: 50GB free space minimum
- **Network**: Ports 9999, 8000, 5432, 6379, 8080, 8200 available

### Software Requirements
```bash
# Check versions
python3 --version  # Should be 3.11+
docker --version   # Should be 20.10+
docker-compose --version  # Should be 2.0+
nvidia-smi  # Should show CUDA 12.4+
```

## Phase 1: Initial Setup (Days 1-3)

### 1.1 Clone Repository and Create Structure

```bash
# Clone RealtimeSTT (base library)
git clone https://github.com/KoljaB/RealtimeSTT.git
cd RealtimeSTT

# Create personal assistant structure
mkdir -p personal_assistant/{core,modules,interfaces,config,utils,security,observability,websocket,adapters,examples}
mkdir -p personal_assistant/modules/{transcription,telephony,llm}
mkdir -p config/{profiles,keycloak,openbao,alloy}

# Create __init__.py files
find personal_assistant -type d -exec touch {}/__init__.py \;

# Create requirements file
cat > requirements-assistant.txt << 'EOF'
# Base dependencies from RealtimeSTT
RealtimeSTT>=0.3.104
RealtimeTTS>=0.4.5

# Web framework
fastapi>=0.104.0
websockets>=12.0
uvicorn>=0.24.0

# Database
asyncpg>=0.29.0
pgvector>=0.2.4
redis>=5.0.1
SQLAlchemy>=2.0.0

# Security
python-keycloak>=3.7.0
hvac>=2.1.0  # For OpenBao/Vault
python-jose>=3.3.0
passlib>=1.7.4

# Observability
opentelemetry-api>=1.22.0
opentelemetry-sdk>=1.22.0
opentelemetry-instrumentation>=0.43b0
opentelemetry-exporter-otlp>=1.22.0

# LLM
openai>=1.10.0
anthropic>=0.18.0
tiktoken>=0.5.0

# Utilities
pydantic>=2.5.0
pydantic-settings>=2.1.0
structlog>=24.1.0
dependency-injector>=4.41.0

# Development
pytest>=7.4.0
pytest-asyncio>=0.23.0
black>=23.12.0
mypy>=1.8.0
EOF
```

### 1.2 Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y \
    portaudio19-dev \
    ffmpeg \
    postgresql-client \
    redis-tools \
    build-essential

# Install Python packages
pip install -r requirements-assistant.txt

# Install GPU support (if available)
pip install torch==2.1.0+cu124 -f https://download.pytorch.org/whl/torch_stable.html
pip install nvidia-ml-py3
```

### 1.3 Create Base Configuration

```bash
# Create base configuration
cat > config/default.yaml << 'EOF'
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
  device: cuda  # or cpu
  compute_type: float16  # or int8

tts:
  engine: system  # Start with system TTS
  system:
    voice: espeak  # Cross-platform

llm:
  provider: openai
  model: gpt-3.5-turbo
  temperature: 0.7
  max_tokens: 500

database:
  host: localhost
  port: 5432
  user: assistant
  password: assistant_password
  database: personal_assistant

redis:
  host: localhost
  port: 6379
  db: 0

security:
  auth_required: false  # Start without auth
  session_timeout: 3600

telemetry:
  enabled: false  # Start without telemetry
EOF

# Create .env file
cat > .env << 'EOF'
# Database
POSTGRES_PASSWORD=assistant_password
POSTGRES_USER=assistant
POSTGRES_DB=personal_assistant

# Redis
REDIS_PASSWORD=redis_password

# APIs (add your keys)
OPENAI_API_KEY=your_openai_key_here
AZURE_SPEECH_KEY=your_azure_key_here
AZURE_SPEECH_REGION=eastus

# Security (for later phases)
KEYCLOAK_ADMIN_PASSWORD=admin_password
KEYCLOAK_DB_PASSWORD=keycloak_password
VAULT_TOKEN=dev-only-token

# Telemetry (for later phases)
OTEL_SERVICE_NAME=personal-assistant
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
EOF
```

## Phase 2: Core Implementation (Days 4-7)

### 2.1 Create Interface Definitions

```bash
# Create base interfaces
cat > personal_assistant/interfaces/base.py << 'EOF'
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional, Callable
import asyncio

class STTInterface(ABC):
    """Base interface for Speech-to-Text components"""
    
    @abstractmethod
    async def start_listening(self) -> None:
        """Start listening for audio input"""
        pass
    
    @abstractmethod
    async def stop_listening(self) -> None:
        """Stop listening"""
        pass
    
    @abstractmethod
    async def feed_audio(self, chunk: bytes) -> None:
        """Feed audio data for processing"""
        pass
    
    @abstractmethod
    def on_transcription(self, callback: Callable) -> None:
        """Register transcription callback"""
        pass

class TTSInterface(ABC):
    """Base interface for Text-to-Speech components"""
    
    @abstractmethod
    async def speak(self, text: str, priority: int = 5) -> None:
        """Convert text to speech"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop current speech"""
        pass
    
    @abstractmethod
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        pass

class LLMInterface(ABC):
    """Base interface for Language Model components"""
    
    @abstractmethod
    async def complete(self, messages: list, **kwargs) -> AsyncIterator[str]:
        """Get completion from LLM"""
        pass
EOF
```

### 2.2 Create STT Wrapper

```bash
# Save the EnhancedSTT implementation from the architecture doc
# Copy the full EnhancedSTT class from PERSONAL_ASSISTANT_ARCHITECTURE.md
# into personal_assistant/core/stt_wrapper.py
```

### 2.3 Create Main Assistant

```bash
# Save the PersonalAssistant implementation from the architecture doc
# Copy the full PersonalAssistant class from PERSONAL_ASSISTANT_ARCHITECTURE.md
# into personal_assistant/core/assistant.py
```

### 2.4 Create Simple Example

```bash
cat > examples/basic_test.py << 'EOF'
#!/usr/bin/env python3
"""Basic test of Personal Assistant wrapper"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personal_assistant.core.stt_wrapper import EnhancedSTT
from personal_assistant.utils.events import EventBus, Event, EventType
import asyncio
import yaml

async def main():
    # Load config
    with open('config/default.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create event bus
    event_bus = EventBus()
    
    # Register handlers
    async def on_transcription(event: Event):
        print(f"Transcribed: {event.data.get('text')}")
    
    event_bus.on(EventType.TRANSCRIPTION_FINAL, on_transcription)
    
    # Create STT wrapper
    stt = EnhancedSTT(
        config['stt'],
        event_bus=event_bus
    )
    
    print("Starting Personal Assistant Test...")
    print("Speak into your microphone...")
    
    # Simple transcription loop
    while True:
        text = stt.recorder.text()
        if text:
            print(f"You said: {text}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

chmod +x examples/basic_test.py
```

## Phase 3: Database Setup (Days 8-10)

### 3.1 PostgreSQL with Docker

```bash
# Create init.sql
cat > init.sql << 'EOF'
-- Create database if not exists
CREATE DATABASE personal_assistant;

-- Connect to the database
\c personal_assistant;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Copy full schema from PERSONAL_ASSISTANT_ARCHITECTURE.md
-- (All CREATE TABLE, INDEX, and VIEW statements)
EOF

# Start PostgreSQL
docker run -d \
  --name assistant-postgres \
  -e POSTGRES_USER=assistant \
  -e POSTGRES_PASSWORD=assistant_password \
  -e POSTGRES_DB=personal_assistant \
  -p 5432:5432 \
  -v $(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql \
  pgvector/pgvector:pg17

# Wait for it to start
sleep 10

# Test connection
PGPASSWORD=assistant_password psql -h localhost -U assistant -d personal_assistant -c "\dt"
```

### 3.2 Redis Setup

```bash
# Start Redis
docker run -d \
  --name assistant-redis \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes

# Test connection
redis-cli ping
```

## Phase 4: WebSocket Server (Days 11-13)

### 4.1 Create WebSocket Server

```bash
cat > personal_assistant/websocket/server.py << 'EOF'
import asyncio
import websockets
import json
import logging
from typing import Set, Dict
import uuid

logger = logging.getLogger(__name__)

class WebSocketServer:
    def __init__(self, assistant, host="0.0.0.0", port=9999):
        self.assistant = assistant
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_sessions: Dict[str, Dict] = {}

    async def handle_client(self, websocket, path):
        """Handle new client connection"""
        client_id = str(uuid.uuid4())
        self.clients.add(websocket)
        self.client_sessions[client_id] = {
            'websocket': websocket,
            'session_id': None
        }
        
        logger.info(f"Client {client_id} connected")
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connected',
                'client_id': client_id
            }))
            
            # Handle messages
            async for message in websocket:
                await self.process_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            self.clients.remove(websocket)
            del self.client_sessions[client_id]

    async def process_message(self, client_id: str, message: str):
        """Process client message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'audio':
                # Handle audio data
                audio_chunk = bytes.fromhex(data['data'])
                await self.assistant.stt.feed_audio(audio_chunk)
                
            elif msg_type == 'command':
                # Handle commands
                command = data.get('command')
                await self.handle_command(client_id, command, data)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(client_id, str(e))

    async def start(self):
        """Start WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        await websockets.serve(self.handle_client, self.host, self.port)

async def main():
    # Basic server test
    server = WebSocketServer(None)  # No assistant for test
    await server.start()
    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
EOF
```

### 4.2 Test WebSocket Server

```bash
# Run server
python personal_assistant/websocket/server.py &

# Test with websocat (install: cargo install websocat)
echo '{"type":"command","command":"status"}' | websocat ws://localhost:9999
```

## Phase 5: Deployment (Days 14-15)

### 5.1 Create Docker Compose

```bash
# Copy docker-compose.yml from PERSONAL_ASSISTANT_ARCHITECTURE.md
# This includes all services: PostgreSQL, Redis, Assistant, etc.
```

### 5.2 Create Dockerfile

```bash
# Copy Dockerfile from PERSONAL_ASSISTANT_ARCHITECTURE.md
```

### 5.3 Run Everything

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f assistant

# Test the system
python examples/basic_test.py
```

## Validation Checklist

### Phase 1 Validation
- [ ] Python environment created and activated
- [ ] All dependencies installed without errors
- [ ] Configuration files created
- [ ] Project structure matches architecture

### Phase 2 Validation
- [ ] Can import personal_assistant modules
- [ ] Basic STT wrapper instantiates
- [ ] Event system works
- [ ] Basic example runs

### Phase 3 Validation
- [ ] PostgreSQL running and accessible
- [ ] Database schema created
- [ ] Redis running and accessible
- [ ] Can connect from Python

### Phase 4 Validation
- [ ] WebSocket server starts
- [ ] Can connect with WebSocket client
- [ ] Messages are processed
- [ ] Audio streaming works

### Phase 5 Validation
- [ ] Docker images build successfully
- [ ] All containers start
- [ ] Services can communicate
- [ ] End-to-end test passes

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH includes project root
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   ```

2. **Database Connection Failed**
   ```bash
   # Check PostgreSQL is running
   docker ps | grep postgres
   
   # Check connection
   nc -zv localhost 5432
   ```

3. **GPU Not Available**
   ```python
   # Test CUDA availability
   import torch
   print(torch.cuda.is_available())
   ```

4. **WebSocket Connection Refused**
   ```bash
   # Check port is free
   lsof -i :9999
   
   # Check firewall
   sudo ufw allow 9999
   ```

## Next Steps

After completing Phase 1-5:

1. **Add Authentication** (Phase 6)
   - Setup Keycloak
   - Configure OpenBao
   - Enable auth in config

2. **Add Observability** (Phase 7)
   - Setup Grafana Alloy
   - Configure OpenTelemetry
   - Create dashboards

3. **Add Modules** (Phase 8)
   - Implement phone support
   - Add custom modules
   - Integrate external services

## Success Criteria

The implementation is successful when:
1. Can transcribe speech in real-time
2. Can generate and speak responses
3. Stores all transcriptions in database
4. WebSocket clients can connect
5. System is containerized and portable

## Resources

- [RealtimeSTT Documentation](https://github.com/KoljaB/RealtimeSTT)
- [RealtimeTTS Documentation](https://github.com/KoljaB/RealtimeTTS)
- [Faster Whisper Models](https://github.com/guillaumekln/faster-whisper)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)