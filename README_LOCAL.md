# RealtimeSTT Local Installation

This is a customized installation of [RealtimeSTT](https://github.com/KoljaB/RealtimeSTT) configured for WebSocket-based audio streaming between Windows clients and a Linux server.

## System Configuration
- **Server**: Linux VM with 80GB RAM, 24 cores
- **Client**: Windows PC with microphone
- **Port**: 9999 (WebSocket)
- **Models**: Configured for high-accuracy transcription

## Quick Start

### Server (Linux)
```bash
./start_server.sh
```

Choose from 4 server modes:
1. **High Accuracy (No Real-time)** - Best quality, final sentences only
2. **Balanced Real-time** - Good accuracy with live feedback
3. **Fast Real-time** - Maximum responsiveness, lower accuracy
4. **Recording Mode** - Saves audio files and transcriptions

### Client (Windows)
```bash
# Install dependencies (first time only)
pip install -r requirements-client.txt

# Run client
python client.py <server-ip>
```

## Server Modes Explained

### 1. High Accuracy Mode (Default)
- **Model**: medium.en (769M parameters)
- **Real-time**: Disabled
- **Use case**: When you need the best transcription quality
- **File**: `server_no_realtime.py`

### 2. Balanced Real-time Mode
- **Main Model**: medium.en
- **Real-time Model**: tiny.en
- **Use case**: See what you're saying with high-quality final output
- **File**: `server_realtime_balanced.py`

### 3. Fast Real-time Mode
- **Model**: tiny.en throughout
- **Processing**: Very fast (0.05s pause)
- **Use case**: Maximum responsiveness for live applications
- **File**: `server_realtime_fast.py`

### 4. Recording Mode
- **Features**: Saves WAV files + transcription logs
- **Output**: `./recordings/` and `./transcriptions/`
- **Use case**: When you need to keep audio records
- **File**: `server_with_recording.py`

## Technical Details

### Audio Format
- Sample Rate: 16000 Hz (16 kHz)
- Channels: 1 (mono)
- Bit Depth: 16-bit
- Format: PCM (raw audio)

### Models Available
- `tiny.en` - 39M parameters (fastest)
- `base.en` - 74M parameters
- `small.en` - 244M parameters
- `medium.en` - 769M parameters (current default)
- `large-v2` - 1550M parameters (highest accuracy)

### Network Requirements
- Ensure firewall allows port 9999:
  ```bash
  sudo firewall-cmd --add-port=9999/tcp --permanent
  sudo firewall-cmd --reload
  ```

## Troubleshooting

### Test Local Microphone First
```bash
python test_local.py
```

### Audio Device Issues (Windows)
List devices:
```bash
python client.py
```

Use specific device:
```bash
python client.py <server-ip> <device-index>
```

### Performance Tuning
Edit server files to change models:
```python
'model': 'large-v2',  # For maximum accuracy
'realtime_model_type': 'base.en',  # For better real-time
```

## Original RealtimeSTT Features

RealtimeSTT is an easy-to-use, low-latency speech-to-text library for realtime applications. Key features:

- **Voice Activity Detection**: Automatically detects speech start/stop
- **Real-time Transcription**: Live feedback while speaking
- **Wake Word Support**: Can be triggered by keywords
- **GPU Acceleration**: Uses CUDA when available

### Core Components
- **VAD**: WebRTCVAD + SileroVAD for robust detection
- **STT**: Faster-Whisper for GPU-accelerated transcription
- **Wake Words**: Porcupine or OpenWakeWord

## File Structure
```
/home/bloodrune/nscix/voice/
├── start_server.sh           # Main server launcher
├── server_no_realtime.py     # High accuracy mode
├── server_realtime_balanced.py # Balanced mode
├── server_realtime_fast.py   # Fast mode
├── server_with_recording.py  # Recording mode
├── client.py                 # Windows client
├── test_local.py            # Test local microphone
├── requirements-client.txt   # Client dependencies
├── recordings/              # Audio files (recording mode)
└── transcriptions/          # Text logs (recording mode)
```

## Credits
Original RealtimeSTT by [Kolja Beigel](https://github.com/KoljaB/RealtimeSTT)