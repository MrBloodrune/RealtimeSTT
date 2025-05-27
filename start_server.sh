#!/bin/bash

# RealtimeSTT Server Launcher
# Clean, organized server selection

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get primary IP
IP_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n1)

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}     RealtimeSTT WebSocket Server${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Server will run on: ws://$IP_ADDR:9999${NC}"
echo ""
echo "Select server mode:"
echo ""
echo -e "${BLUE}1)${NC} High Accuracy (No Real-time) - ${GREEN}[DEFAULT]${NC}"
echo "   Best transcription quality with medium.en model"
echo "   Shows final sentences only"
echo ""
echo -e "${BLUE}2)${NC} Balanced Real-time"
echo "   Good accuracy with live feedback"
echo "   medium.en + real-time updates"
echo ""
echo -e "${BLUE}3)${NC} Fast Real-time"  
echo "   Maximum responsiveness"
echo "   tiny.en model throughout"
echo ""
echo -e "${BLUE}4)${NC} Recording Mode"
echo "   Saves audio files and transcriptions"
echo "   medium.en with logging"
echo ""
read -p "Enter choice [1-4] (default: 1): " choice

# Default to high accuracy if no choice
if [ -z "$choice" ]; then
    choice=1
fi

# Activate virtual environment
cd /home/bloodrune/RTTS/RealtimeSTT
source venv/bin/activate

echo ""
case $choice in
    1)
        echo -e "${GREEN}Starting High Accuracy Server (no real-time)...${NC}"
        exec python server_no_realtime.py
        ;;
    2)
        echo -e "${GREEN}Starting Balanced Real-time Server...${NC}"
        exec python server_realtime_balanced.py
        ;;
    3)
        echo -e "${GREEN}Starting Fast Real-time Server...${NC}"
        exec python server_realtime_fast.py
        ;;
    4)
        echo -e "${GREEN}Starting Recording Server...${NC}"
        echo "Audio files will be saved to: ./recordings/"
        echo "Transcriptions will be saved to: ./transcriptions/"
        exec python server_with_recording.py
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Starting High Accuracy Server...${NC}"
        exec python server_no_realtime.py
        ;;
esac