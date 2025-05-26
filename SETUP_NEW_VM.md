# RealtimeSTT WebSocket Server Setup Guide

This guide will help you rebuild the exact RealtimeSTT WebSocket server setup on a fresh Alma Linux VM.

## Prerequisites

- Fresh Alma Linux installation
- At least 80GB RAM (for large models)
- 24+ CPU cores recommended
- Internet connection

## Quick Setup Script

Save and run the automated setup script below, or follow the manual steps.

```bash
wget https://raw.githubusercontent.com/MrBloodrune/RealtimeSTT/master/setup_realtimestt_server.sh
chmod +x setup_realtimestt_server.sh
./setup_realtimestt_server.sh
```

## Manual Setup Steps

### 1. System Dependencies

```bash
# Update system
sudo dnf update -y

# Install development tools
sudo dnf groupinstall "Development Tools" -y

# Install Python 3.11 and dependencies
sudo dnf install -y python3.11 python3.11-devel python3.11-pip

# Install audio libraries
sudo dnf install -y portaudio-devel
sudo dnf install -y ffmpeg

# Install git
sudo dnf install -y git

# Install other dependencies
sudo dnf install -y wget curl
```

### 2. Create Project Directory

```bash
# Create project structure
mkdir -p /home/$(whoami)/nscix
cd /home/$(whoami)/nscix
```

### 3. Clone Repository

```bash
# Clone your fork
git clone https://github.com/MrBloodrune/RealtimeSTT.git voice
cd voice

# Add upstream remote
git remote add upstream https://github.com/KoljaB/RealtimeSTT.git
```

### 4. Python Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 5. Install Python Dependencies

```bash
# Install main requirements
pip install -r requirements.txt

# Install CUDA support (optional, if you have NVIDIA GPU)
# For CUDA 11.8:
# pip install torch==2.5.1+cu118 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118
# For CUDA 12.X:
# pip install torch==2.5.1+cu121 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
```

### 6. Fix Known Issues

```bash
# Fix tqdm compatibility issue
pip install "tqdm>=4.66.0,<4.67.0"
```

### 7. Download Models (Pre-warm)

```python
# Create a script to pre-download models
cat > download_models.py << 'EOF'
from faster_whisper import WhisperModel
import sys

models = ['tiny.en', 'base.en', 'small.en', 'medium.en']
print("Downloading Whisper models...")

for model in models:
    print(f"Downloading {model}...")
    try:
        WhisperModel(model, device="cpu", compute_type="int8")
        print(f"✓ {model} downloaded")
    except Exception as e:
        print(f"✗ Error downloading {model}: {e}")

print("\nModel download complete!")
EOF

python download_models.py
rm download_models.py
```

### 8. Configure Firewall

```bash
# Open port 9999 for WebSocket
sudo firewall-cmd --add-port=9999/tcp --permanent
sudo firewall-cmd --reload

# Open port 8000 for future API server (optional)
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### 9. Create Systemd Service (Optional)

```bash
# Create service file
sudo tee /etc/systemd/system/realtimestt.service << EOF
[Unit]
Description=RealtimeSTT WebSocket Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=/home/$(whoami)/nscix/voice
Environment="PATH=/home/$(whoami)/nscix/voice/venv/bin"
ExecStart=/home/$(whoami)/nscix/voice/venv/bin/python /home/$(whoami)/nscix/voice/server_no_realtime.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service (don't start yet)
sudo systemctl daemon-reload
sudo systemctl enable realtimestt.service
```

### 10. Test Installation

```bash
# Test local microphone (if available)
cd /home/$(whoami)/nscix/voice
source venv/bin/activate
python test_local.py

# Test server startup
./start_server.sh
```

## Directory Structure

After setup, you should have:

```
/home/[username]/nscix/voice/
├── venv/                    # Python virtual environment
├── recordings/              # Audio recordings (created on first use)
├── transcriptions/          # Transcription logs (created on first use)
├── start_server.sh          # Server launcher script
├── server_no_realtime.py    # High accuracy server
├── server_realtime_balanced.py  # Balanced real-time server
├── server_realtime_fast.py  # Fast real-time server
├── server_with_recording.py # Recording mode server
├── client.py                # Windows client
├── client_file.py           # Audio file client
├── transcribe_file.py       # Local transcription tool
├── test_local.py            # Local microphone test
├── CLAUDE.md                # Documentation for Claude Code
└── requirements.txt         # Python dependencies
```

## Client Setup (Windows)

On Windows machines that will connect to this server:

1. Install Python 3.11+
2. Install dependencies:
   ```
   pip install -r requirements-client.txt
   ```
3. Run client:
   ```
   python client.py <server-ip>
   ```

## Verification Checklist

- [ ] Virtual environment activates: `source venv/bin/activate`
- [ ] Server starts without errors: `./start_server.sh`
- [ ] Port 9999 is accessible: `sudo firewall-cmd --list-ports`
- [ ] Models are downloaded (check ~/.cache/huggingface)
- [ ] Git remotes are correct: `git remote -v`

## Troubleshooting

### Out of Memory Errors
- Ensure you have at least 80GB RAM
- Use smaller models (tiny.en or base.en)
- Reduce batch size in server configuration

### Module Import Errors
- Ensure virtual environment is activated
- Re-run: `pip install -r requirements.txt`

### Connection Refused
- Check firewall: `sudo firewall-cmd --list-ports`
- Verify server is running: `ps aux | grep python`
- Check server IP: `ip addr show`

### Model Download Issues
- Check internet connection
- Clear cache: `rm -rf ~/.cache/huggingface`
- Manually download models using the script above

## Notes

- Server runs on port 9999 by default
- Audio format must be 16kHz, mono, 16-bit PCM
- Models are cached in ~/.cache/huggingface
- Logs are written to console (stdout)