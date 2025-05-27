# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Personal Assistant Wrapper Project

### Overview
This repository contains plans for a production-ready Personal Assistant system that wraps RealtimeSTT/TTS libraries without modifying their source code. The wrapper adds enterprise features while preserving all original functionality.

### Key Documentation Files
1. **PERSONAL_ASSISTANT_ARCHITECTURE.md** - Complete 40+ page architecture document
   - System design and component specifications
   - Database schemas (PostgreSQL with pgvector)
   - Security implementation (OpenBao + Keycloak)
   - Observability (OpenTelemetry + Grafana Alloy)
   - Full code examples for all components

2. **PERSONAL_ASSISTANT_EXECUTION_GUIDE.md** - Step-by-step implementation guide
   - 15-day phased implementation plan
   - Prerequisites and setup instructions
   - Validation checklists for each phase
   - Troubleshooting guide

3. **requirements-assistant.txt** - Complete dependency list for the wrapper

### Architecture Principles
- **Non-invasive**: Wraps existing libraries using composition pattern
- **Scalable**: Containerized with horizontal scaling support
- **Secure**: Full authentication/authorization with secret management
- **Observable**: Complete metrics, logs, and traces
- **Extensible**: Plugin-based module system

### Project Structure
```
personal_assistant/
├── core/               # Main wrapper classes
│   ├── stt_wrapper.py  # Enhanced STT with transcription storage
│   ├── tts_wrapper.py  # Enhanced TTS with queuing
│   └── assistant.py    # Main coordinator
├── modules/            # Feature modules
│   ├── transcription/  # Storage and retrieval
│   ├── telephony/      # Phone call support
│   └── llm/           # AI integrations
├── security/          # Auth and secrets
├── observability/     # Monitoring
└── websocket/         # Client connections
```

### Implementation Approach
The wrapper pattern ensures RealtimeSTT updates don't break custom code:
- Original library files remain untouched
- Wrappers use public APIs only
- Easy to pull upstream updates
- Graceful degradation for breaking changes

## Current RealtimeSTT Setup (Reference Only)

### Environment
- **OS**: Alma Linux 9 VM (QEMU)
- **Hardware**: 8 cores, RTX 3080 GPU
- **Python**: 3.11 with virtual environment
- **CUDA**: 12.4 with cuDNN 8.9.7

### Basic Testing Commands
```bash
# Test RealtimeSTT installation
source venv/bin/activate
python tests/simple_test.py

# Run existing server examples
./start_server.sh
```

