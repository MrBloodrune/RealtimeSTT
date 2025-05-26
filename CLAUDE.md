# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Server Launch
```bash
# Main server launcher with menu
./start_server.sh

# Direct server launch (activate venv first)
source venv/bin/activate
python server_no_realtime.py      # High accuracy, no real-time (default)
python server_realtime_balanced.py # Medium.en + tiny.en real-time
python server_realtime_fast.py    # All tiny.en for speed
python server_with_recording.py   # Saves audio files + transcriptions
```

### Client Commands (Windows)
```bash
# Install dependencies
pip install -r requirements-client.txt

# Run client
python client.py <server-ip>
python client.py <server-ip> <device-index>  # Specific audio device
```

### Testing
```bash
# Test local microphone on server
source venv/bin/activate
python test_local.py

# Test RealtimeSTT installation
python tests/simple_test.py
```

### Recording Mode Output
```bash
# Watch live transcriptions (when using recording server)
cd /home/bloodrune/nscix/voice
tail -f transcriptions/session_*.txt

# Audio files saved to
./recordings/recording_YYYYMMDD_HHMMSS_mmm.wav
```

## Architecture Overview

### System Design
WebSocket-based client-server architecture for real-time speech-to-text:
- **Server**: Linux VM (80GB RAM, 24 cores) running RealtimeSTT
- **Client**: Windows PC streaming microphone audio
- **Protocol**: WebSocket on port 9999
- **Audio**: 16kHz, mono, 16-bit PCM

### Server Modes

1. **High Accuracy (server_no_realtime.py)**
   - Model: medium.en (769M params)
   - Real-time transcription: Disabled
   - Best for: Maximum accuracy, lower CPU usage

2. **Balanced Real-time (server_realtime_balanced.py)**
   - Main model: medium.en
   - Real-time model: tiny.en
   - Best for: Good accuracy with live feedback

3. **Fast Real-time (server_realtime_fast.py)**
   - Model: tiny.en throughout
   - Processing pause: 0.05s
   - Best for: Maximum responsiveness

4. **Recording Mode (server_with_recording.py)**
   - Same as balanced mode
   - Saves WAV files per sentence
   - Logs all transcriptions with timestamps

### Key Implementation Details

#### Server Components
- **AudioToTextRecorder**: Core RealtimeSTT class
  - `use_microphone=False` - Accepts WebSocket audio
  - `feed_audio()` - Processes incoming chunks
  - Callbacks for VAD and transcription events

#### Client Components
- **PyAudio**: Captures microphone input
- **WebSocket**: Streams raw PCM audio
- **Message Handler**: Displays transcription updates

#### Audio Flow
```
Microphone → PyAudio → WebSocket → Server → RealtimeSTT → Transcription
                                      ↓
                            (Recording Mode Only)
                                      ↓
                              Save WAV + Log Text
```

### Message Types
Server sends JSON messages:
- `partial`: Live transcription updates
- `realtime`: Stabilized intermediate text
- `fullSentence`: Final transcription
- `recording_start/stop`: Voice activity events
- `audio_file`: Path to saved recording (recording mode)

## Critical Configuration

### Model Selection
Models are hardcoded in server files. To change:
```python
'model': 'large-v2',  # Main transcription model
'realtime_model_type': 'base.en',  # Real-time feedback model
```

### Performance vs Accuracy Trade-offs
- **tiny.en**: 39M params, very fast, lower accuracy
- **base.en**: 74M params, good balance
- **small.en**: 244M params, better accuracy
- **medium.en**: 769M params, high accuracy (current default)
- **large-v2**: 1550M params, best accuracy, slower

### Audio Requirements
Must be exactly:
- 16000 Hz sample rate
- 1 channel (mono)
- 16-bit PCM
- Chunk size: 1024 samples (client.py)

### Network Configuration
- Port: 9999 (hardcoded)
- Host: 0.0.0.0 (all interfaces)
- Firewall must allow TCP on port 9999

## Important Notes

### Resource Usage
- Model loading: ~10-20 seconds for medium.en
- Memory: 2-4GB for medium.en
- CPU: Real-time modes use more CPU continuously

### Current Status
- System tested and working with 80GB RAM
- Previous issues were due to insufficient memory
- All server modes functional

### File Outputs (Recording Mode)
- Audio: `./recordings/` - Individual WAV files per sentence
- Text: `./transcriptions/session_YYYYMMDD_HHMMSS.txt`
- Format: Timestamped transcriptions with audio file references

## Common Development Commands

### Server Launch
```bash
# Main server launcher with menu
./start_server.sh

# Direct server launch (activate venv first)
source venv/bin/activate
python server_no_realtime.py      # High accuracy, no real-time (default)
python server_realtime_balanced.py # Medium.en + tiny.en real-time
python server_realtime_fast.py    # All tiny.en for speed
python server_with_recording.py   # Saves audio files + transcriptions
```

### Client Commands (Windows)
```bash
# Install dependencies
pip install -r requirements-client.txt

# Run client
python client.py <server-ip>
python client.py <server-ip> <device-index>  # Specific audio device
```

### Testing
```bash
# Test local microphone on server
source venv/bin/activate
python test_local.py

# Test RealtimeSTT installation
python tests/simple_test.py
```

### Recording Mode Output
```bash
# Watch live transcriptions (when using recording server)
cd /home/bloodrune/nscix/voice
tail -f transcriptions/session_*.txt

# Audio files saved to
./recordings/recording_YYYYMMDD_HHMMSS_mmm.wav
```

## Architecture Overview

### System Design
WebSocket-based client-server architecture for real-time speech-to-text:
- **Server**: Linux VM (80GB RAM, 24 cores) running RealtimeSTT
- **Client**: Windows PC streaming microphone audio
- **Protocol**: WebSocket on port 9999
- **Audio**: 16kHz, mono, 16-bit PCM

### Server Modes

1. **High Accuracy (server_no_realtime.py)**
   - Model: medium.en (769M params)
   - Real-time transcription: Disabled
   - Best for: Maximum accuracy, lower CPU usage

2. **Balanced Real-time (server_realtime_balanced.py)**
   - Main model: medium.en
   - Real-time model: tiny.en
   - Best for: Good accuracy with live feedback

3. **Fast Real-time (server_realtime_fast.py)**
   - Model: tiny.en throughout
   - Processing pause: 0.05s
   - Best for: Maximum responsiveness

4. **Recording Mode (server_with_recording.py)**
   - Same as balanced mode
   - Saves WAV files per sentence
   - Logs all transcriptions with timestamps

### Key Implementation Details

#### Server Components
- **AudioToTextRecorder**: Core RealtimeSTT class
  - `use_microphone=False` - Accepts WebSocket audio
  - `feed_audio()` - Processes incoming chunks
  - Callbacks for VAD and transcription events

#### Client Components
- **PyAudio**: Captures microphone input
- **WebSocket**: Streams raw PCM audio
- **Message Handler**: Displays transcription updates

#### Audio Flow
```
Microphone → PyAudio → WebSocket → Server → RealtimeSTT → Transcription
                                      ↓
                            (Recording Mode Only)
                                      ↓
                              Save WAV + Log Text
```

### Message Types
Server sends JSON messages:
- `partial`: Live transcription updates
- `realtime`: Stabilized intermediate text
- `fullSentence`: Final transcription
- `recording_start/stop`: Voice activity events
- `audio_file`: Path to saved recording (recording mode)

## Critical Configuration

### Model Selection
Models are hardcoded in server files. To change:
```python
'model': 'large-v2',  # Main transcription model
'realtime_model_type': 'base.en',  # Real-time feedback model
```

### Performance vs Accuracy Trade-offs
- **tiny.en**: 39M params, very fast, lower accuracy
- **base.en**: 74M params, good balance
- **small.en**: 244M params, better accuracy
- **medium.en**: 769M params, high accuracy (current default)
- **large-v2**: 1550M params, best accuracy, slower

### Audio Requirements
Must be exactly:
- 16000 Hz sample rate
- 1 channel (mono)
- 16-bit PCM
- Chunk size: 1024 samples (client.py)

### Network Configuration
- Port: 9999 (hardcoded)
- Host: 0.0.0.0 (all interfaces)
- Firewall must allow TCP on port 9999

## Important Notes

### Resource Usage
- Model loading: ~10-20 seconds for medium.en
- Memory: 2-4GB for medium.en
- CPU: Real-time modes use more CPU continuously

### Current Status
- System tested and working with 80GB RAM
- Previous issues were due to insufficient memory
- All server modes functional

### File Outputs (Recording Mode)
- Audio: `./recordings/` - Individual WAV files per sentence
- Text: `./transcriptions/session_YYYYMMDD_HHMMSS.txt`
- Format: Timestamped transcriptions with audio file references