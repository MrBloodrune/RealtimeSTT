#!/bin/bash
# Start the Personal Assistant Server

echo "Starting Personal Assistant Server..."
cd /home/bloodrune/RTTS/RealtimeSTT
source venv/bin/activate
cd personal_assistant

# Check firewall
echo "Checking firewall..."
if command -v firewall-cmd &> /dev/null; then
    if sudo firewall-cmd --list-ports | grep -q "9999/tcp"; then
        echo "Port 9999 is already open"
    else
        echo "Opening port 9999..."
        echo "Run: sudo firewall-cmd --add-port=9999/tcp --permanent"
        echo "Then: sudo firewall-cmd --reload"
    fi
fi

# Start server
python assistant_server.py