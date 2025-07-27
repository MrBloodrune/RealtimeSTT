#!/usr/bin/env python3
"""
Simple HTTP server to serve the web client
"""

import http.server
import socketserver
import os
import sys

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.path = '/web_client.html'
        return super().do_GET()

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print(f"Starting web server on http://localhost:{PORT}")
print(f"Open http://localhost:{PORT} in your browser")
print(f"Or http://localhost:{PORT}?server=<your-server-ip> to connect to a remote server")
print(f"\nPress Ctrl+C to stop")

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server...")
        sys.exit(0)