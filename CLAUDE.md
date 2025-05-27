# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Installation Status (2025-05-26)

### Current Environment
- **OS**: Alma Linux 9 VM (QEMU)
- **Hardware**: 8 cores, RTX 3080 GPU (✅ ACTIVE)
- **Python**: 3.11 with virtual environment
- **Location**: `/home/bloodrune/RTTS/RealtimeSTT/`
- **CUDA**: 12.4 (via nvidia-smi)
- **cuDNN**: 8.9.7.29

### Completed Setup
- ✅ All system dependencies installed (including portaudio-devel)
- ✅ Python environment with all packages (PyAudio fixed)
- ✅ Whisper models downloaded (tiny.en through medium.en)
- ✅ Server scripts present and executable
- ✅ NVIDIA drivers installed and active (550.144.03)
- ✅ CUDA repository configured
- ✅ cuDNN 8.x installed for GPU acceleration
- ✅ ctranslate2 downgraded to 4.4.0 for compatibility
- ✅ All server modes tested and working

### GPU Setup Instructions
1. **Fix ctranslate2/cuDNN compatibility**:
   ```bash
   source venv/bin/activate
   pip install ctranslate2==4.4.0
   ```

2. **Install CUDA repository**:
   ```bash
   wget https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo
   sudo mv cuda-rhel9.repo /etc/yum.repos.d/
   ```

3. **Install cuDNN 8**:
   ```bash
   sudo dnf install libcudnn8
   ```

### Key Installation Notes
1. **PyAudio requires portaudio-devel**: Must install system package before pip
2. **soundfile module**: Not in requirements.txt but needed by RealtimeSTT
3. **tqdm version conflict**: Must downgrade to 4.66.x for compatibility
4. **GPU driver sequence**: Install RPM Fusion repos → akmod-nvidia → reboot
5. **ctranslate2 version**: Must use 4.4.0 with cuDNN 8.x (not 4.5.0+)
6. **cuDNN requirement**: libcudnn8 package from NVIDIA repo required for GPU

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
- **Server**: Linux VM (8GB RAM, 8 cores, RTX 3080) running RealtimeSTT
- **Client**: Windows PC streaming microphone audio
- **Protocol**: WebSocket on port 9999
- **Audio**: 16kHz, mono, 16-bit PCM
- **GPU**: CUDA 12.4 with cuDNN 8.9.7 for acceleration

### Server Modes (All GPU-Accelerated)

1. **High Accuracy (server_no_realtime.py)** ✅ WORKING
   - Model: medium.en (769M params)
   - Real-time transcription: Disabled
   - Best for: Maximum accuracy, lower GPU usage
   - Shows final sentences only

2. **Balanced Real-time (server_realtime_balanced.py)** ✅ WORKING
   - Main model: medium.en (final transcriptions)
   - Real-time model: tiny.en (live updates)
   - Best for: Good accuracy with live feedback
   - GPU accelerated with CUDA

3. **Fast Real-time (server_realtime_fast.py)** ✅ WORKING
   - Model: tiny.en throughout
   - Processing pause: 0.05s
   - Best for: Maximum responsiveness
   - Lower accuracy but very fast

4. **Recording Mode (server_with_recording.py)** ✅ WORKING
   - Same as balanced mode
   - Saves WAV files per sentence
   - Logs all transcriptions with timestamps
   - Audio saved to ./recordings/
   - Transcriptions to ./transcriptions/

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
- Model loading: ~5-10 seconds with GPU (vs 10-20s CPU)
- Memory: 2-4GB for medium.en model
- GPU Memory: ~1-2GB VRAM usage
- GPU: RTX 3080 provides 5-10x speedup over CPU

### Current Status
- System tested and working with 8GB RAM
- GPU acceleration enabled with CUDA 12.4
- All server modes functional and GPU-accelerated
- cuDNN 8.9.7 installed and working

### File Outputs (Recording Mode)
- Audio: `./recordings/` - Individual WAV files per sentence
- Text: `./transcriptions/session_YYYYMMDD_HHMMSS.txt`
- Format: Timestamped transcriptions with audio file references