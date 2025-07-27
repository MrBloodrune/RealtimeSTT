# Personal Assistant - Simple RealtimeSTT Extension

A simple personal assistant that extends RealtimeSTT with LLM capabilities using the existing server patterns.

## Overview

This implementation follows the existing RealtimeSTT architecture:
- Uses the proven WebSocket server pattern from `server_realtime_balanced.py`
- Adds LLM integration for conversational responses
- Maintains simplicity - no extra dependencies beyond OpenAI (optional)
- Works with the existing RealtimeSTT audio streaming protocol

## Quick Start

### 1. Start the Assistant Server
```bash
cd personal_assistant
python assistant_server.py
```

The server runs on port 9999 and provides:
- Real-time speech transcription
- Optional LLM responses (requires OpenAI)
- Voice command control

### 2. Connect the Client
```bash
# From another terminal
python assistant_client.py

# Or connect to remote server
python assistant_client.py ws://192.168.1.100:9999

# Use specific audio device
python assistant_client.py ws://localhost:9999 1
```

### 3. Voice Commands
- Say **"assistant mode"** - Enable LLM responses
- Say **"transcription mode"** - Disable LLM (transcription only)
- Say **"clear history"** - Reset conversation

## Features

- **Real-time Transcription**: See partial results as you speak
- **LLM Integration**: Optional OpenAI integration for conversational AI
- **Simple Architecture**: Extends existing RealtimeSTT patterns
- **No Complex Dependencies**: Just RealtimeSTT + optional OpenAI

## Requirements

### Required
- Python 3.8+
- RealtimeSTT (already installed)
- PyAudio (for client microphone)
- websockets

### Optional
- OpenAI: `pip install openai` (for LLM features)
- Set `OPENAI_API_KEY` environment variable

## How It Works

The assistant extends the existing RealtimeSTT WebSocket server:

1. **Audio Stream**: Client sends 16kHz PCM audio chunks
2. **Transcription**: Server processes with RealtimeSTT
3. **LLM Response**: Optional OpenAI processing in assistant mode
4. **Response**: JSON messages back to client

## Message Protocol

Same as RealtimeSTT with additions:

### Server to Client
```json
// Standard RealtimeSTT messages
{"type": "partial", "text": "partial transcription"}
{"type": "realtime", "text": "stabilized text"}
{"type": "fullSentence", "text": "complete sentence"}

// Assistant additions
{"type": "mode_change", "mode": "assistant"}
{"type": "assistant_processing"}
{"type": "assistant_response", "text": "AI response"}
```

## Extending

To add features, modify `assistant_server.py`:

1. **Add Commands**: Update the `COMMANDS` dictionary
2. **Custom LLM**: Replace `generate_llm_response()` function
3. **Add TTS**: Send audio chunks back through WebSocket

## Architecture Notes

This implementation:
- Uses RealtimeSTT's built-in `feed_audio()` method
- Follows the single WebSocket pattern (port 9999)
- Maintains conversation history in memory
- Processes commands through transcription

## Comparison with Existing Servers

- `stt-server` (port 8011/8012): Full-featured production server
- `server_realtime_balanced.py`: Base transcription server
- `assistant_server.py`: Adds LLM on top of balanced server

## Future Enhancements

- [ ] Add TTS support (RealtimeTTS integration)
- [ ] Persist conversation history
- [ ] Support multiple LLM providers
- [ ] Add more voice commands
- [ ] WebUI client option