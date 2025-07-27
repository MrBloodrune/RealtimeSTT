# RealtimeSTT Android Client

Android client for the RealtimeSTT WebSocket speech-to-text server. This app captures audio from the device microphone and streams it to the server for real-time transcription.

## Features

- Real-time audio streaming to WebSocket server
- Three recording modes:
  - Push-to-talk: Hold button to record
  - Continuous: Toggle recording on/off
  - Voice Activity Detection: Server-controlled recording
- Live transcription display
- Automatic reconnection on network issues
- Foreground service for reliable audio capture
- Audio buffering for network interruptions

## Requirements

- Android 9.0 (API level 28) or higher
- Android Studio Arctic Fox or newer
- RealtimeSTT server running on local network
- Network access to the server (port 9999)

## Installation

### Building from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/RealtimeSTT.git
   cd RealtimeSTT/android-client
   ```

2. Open the project in Android Studio

3. Build the APK:
   - Debug build: `Build > Build APK(s)`
   - Or use command line:
     ```bash
     ./gradlew assembleDebug
     ```

4. The APK will be located at:
   ```
   app/build/outputs/apk/debug/app-debug.apk
   ```

### Installing the APK

#### Option 1: Using Android Studio
1. Connect your Android device via USB
2. Enable Developer Options and USB Debugging on your device
3. Click "Run" in Android Studio

#### Option 2: Using ADB
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

#### Option 3: Manual Installation
1. Copy the APK to your device
2. Open the file on your device
3. Allow installation from unknown sources if prompted
4. Install the app

## Configuration

1. Launch the app
2. Grant microphone permission when prompted
3. Enter your server's IP address (default: 192.168.1.100)
4. Tap "Connect" to establish connection
5. Choose your preferred recording mode
6. Start recording!

## Usage

### Recording Modes

**Push-to-Talk Mode**
- Press and hold the microphone button to record
- Release to stop recording
- Best for short commands or dictation

**Continuous Mode**
- Tap the microphone button to start/stop recording
- Records continuously until stopped
- Good for long-form dictation

**Voice Activity Detection Mode**
- Tap to enable VAD mode
- Server automatically detects speech
- Recording starts/stops based on voice activity

### Troubleshooting

**Cannot connect to server**
- Verify server is running: `python server_realtime_balanced.py`
- Check server IP address is correct
- Ensure devices are on the same network
- Check firewall allows port 9999

**No audio/transcription**
- Check microphone permission is granted
- Verify server shows "Client connected" message
- Try a different recording mode
- Check server console for errors

**App crashes or stops recording**
- Ensure battery optimization is disabled for the app
- Grant all requested permissions
- Check available storage space
- Update to latest Android version

## Development

### Project Structure
```
android-client/
├── app/
│   └── src/main/java/com/realtimestt/android/
│       ├── data/          # Data models
│       ├── network/       # WebSocket client
│       ├── services/      # Audio capture service
│       ├── ui/           # Activities and ViewModels
│       └── utils/        # Utility classes
├── build.gradle.kts
└── settings.gradle.kts
```

### Key Components

- **AudioCaptureService**: Foreground service for audio recording
- **WebSocketManager**: Handles server connection and messaging
- **MainActivity**: Main UI with recording controls
- **TranscriptionViewModel**: Manages app state and business logic
- **AudioBufferManager**: Manages audio chunk queuing

### Building for Release

1. Create a signing key (first time only)
2. Configure signing in `app/build.gradle.kts`
3. Build release APK:
   ```bash
   ./gradlew assembleRelease
   ```

## Known Limitations

- No TLS/SSL support (plain WebSocket only)
- No authentication mechanism
- English language only
- No audio file storage
- Local network only (no internet streaming)

## License

[Same as parent project]

## Contributing

Please submit issues and pull requests to the main RealtimeSTT repository.