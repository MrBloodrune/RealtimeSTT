#!/bin/bash
# RealtimeSTT WebSocket Server Automated Setup Script
# For Alma Linux (RHEL-based systems)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RealtimeSTT WebSocket Server Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run this script as root!${NC}"
   exit 1
fi

# Get username and home directory
USER_NAME=$(whoami)
USER_HOME=$HOME
PROJECT_DIR="$USER_HOME/nscix/voice"

echo -e "${YELLOW}Installing system dependencies...${NC}"

# Update system
sudo dnf update -y

# Install development tools
sudo dnf groupinstall "Development Tools" -y

# Install Python 3.11
echo -e "${YELLOW}Installing Python 3.11...${NC}"
sudo dnf install -y python3.11 python3.11-devel python3.11-pip

# Install audio libraries
echo -e "${YELLOW}Installing audio libraries...${NC}"
sudo dnf install -y portaudio-devel

# Install ffmpeg from RPM Fusion
echo -e "${YELLOW}Installing ffmpeg...${NC}"
sudo dnf install -y epel-release
sudo dnf install -y --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-$(rpm -E %rhel).noarch.rpm
sudo dnf install -y ffmpeg

# Install git and other tools
sudo dnf install -y git wget curl

# Create project directory
echo -e "${YELLOW}Creating project directory...${NC}"
mkdir -p "$USER_HOME/nscix"
cd "$USER_HOME/nscix"

# Clone repository
echo -e "${YELLOW}Cloning RealtimeSTT repository...${NC}"
if [ -d "voice" ]; then
    echo "Directory 'voice' already exists. Backing up..."
    mv voice voice.backup.$(date +%Y%m%d_%H%M%S)
fi

git clone https://github.com/MrBloodrune/RealtimeSTT.git voice
cd voice

# Add upstream remote
git remote add upstream https://github.com/KoljaB/RealtimeSTT.git || true

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Fix known tqdm issue
echo -e "${YELLOW}Fixing tqdm compatibility...${NC}"
pip install "tqdm>=4.66.0,<4.67.0"

# Pre-download models
echo -e "${YELLOW}Pre-downloading Whisper models...${NC}"
cat > download_models.py << 'EOF'
from faster_whisper import WhisperModel
import sys

models = ['tiny.en', 'base.en', 'small.en', 'medium.en']
print("Downloading Whisper models (this may take a while)...")

for model in models:
    print(f"\nDownloading {model}...")
    try:
        WhisperModel(model, device="cpu", compute_type="int8")
        print(f"✓ {model} downloaded successfully")
    except Exception as e:
        print(f"✗ Error downloading {model}: {e}")

print("\nModel download complete!")
EOF

python download_models.py
rm download_models.py

# Configure firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
sudo firewall-cmd --add-port=9999/tcp --permanent
sudo firewall-cmd --reload
echo -e "${GREEN}✓ Port 9999 opened for WebSocket connections${NC}"

# Create required directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p recordings transcriptions

# Make scripts executable
chmod +x start_server.sh
chmod +x test_local.py
chmod +x client.py
chmod +x client_file.py
chmod +x transcribe_file.py

# Create systemd service (optional)
echo -e "${YELLOW}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/realtimestt.service << EOF
[Unit]
Description=RealtimeSTT WebSocket Server
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/server_no_realtime.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable realtimestt.service

# Get server IP
SERVER_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n1)

# Final message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Project location: ${YELLOW}$PROJECT_DIR${NC}"
echo -e "Server IP: ${YELLOW}$SERVER_IP${NC}"
echo ""
echo -e "${GREEN}To start the server:${NC}"
echo -e "  cd $PROJECT_DIR"
echo -e "  ./start_server.sh"
echo ""
echo -e "${GREEN}To start as service:${NC}"
echo -e "  sudo systemctl start realtimestt"
echo ""
echo -e "${GREEN}Windows clients can connect to:${NC}"
echo -e "  ${YELLOW}ws://$SERVER_IP:9999${NC}"
echo ""
echo -e "${GREEN}To test locally:${NC}"
echo -e "  cd $PROJECT_DIR"
echo -e "  source venv/bin/activate"
echo -e "  python test_local.py"
echo ""

# Ask if user wants to test
read -p "Would you like to test the server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$PROJECT_DIR"
    ./start_server.sh
fi