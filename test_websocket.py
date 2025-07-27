#!/usr/bin/env python3
"""Test WebSocket connection to RealtimeSTT server"""

import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:9999"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("Sent ping")
            
            # Wait for pong
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            # Keep connection open for a bit
            await asyncio.sleep(2)
            print("Connection test successful!")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())