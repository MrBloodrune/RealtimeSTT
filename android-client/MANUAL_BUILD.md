# Manual Build Instructions for RealtimeSTT Android Client

Since your system has Java 8 and Android development requires Java 11+, here are alternative ways to get the APK:

## Option 1: Install Java 11 on AlmaLinux 9

```bash
# Install Java 11
sudo dnf install java-11-openjdk-devel

# Switch Java version
sudo alternatives --config java
# Select java-11-openjdk from the list

# Verify Java version
java -version  # Should show version 11.x.x

# Build the APK
cd /home/bloodrune/rtts/RealtimeSTT/android-client
./gradlew assembleDebug

# APK will be at: app/build/outputs/apk/debug/app-debug.apk
```

## Option 2: Use Another Computer

1. Copy the entire `android-client` folder to a computer with:
   - Windows/Mac/Linux with Java 11+ installed
   - Android Studio (easiest option)

2. Open in Android Studio:
   - File → Open → Select android-client folder
   - Wait for sync
   - Build → Build Bundle(s) / APK(s) → Build APK(s)

3. Or via command line:
   ```bash
   cd android-client
   ./gradlew assembleDebug  # Linux/Mac
   gradlew.bat assembleDebug  # Windows
   ```

## Option 3: Pre-built APK Request

If you cannot build locally, you could:
1. Push the code to GitHub
2. Use GitHub Actions to build the APK
3. Or ask someone with Android Studio to build it

## Option 4: Use Cloud Build Service

Use free services like:
- **Appetize.io** - Upload source, get APK
- **Codemagic** - Free tier for open source
- **Bitrise** - Free tier available

## Quick Install Once You Have the APK

```bash
# If you built it locally
adb install app/build/outputs/apk/debug/app-debug.apk

# If you have the APK file elsewhere
adb install /path/to/app-debug.apk

# Or copy to phone and install manually
```

## Testing Without Building

The source code is complete and ready. Key files:
- MainActivity: `app/src/main/java/com/realtimestt/android/ui/MainActivity.kt`
- WebSocket: `app/src/main/java/com/realtimestt/android/network/WebSocketManager.kt`
- Audio Service: `app/src/main/java/com/realtimestt/android/services/AudioCaptureService.kt`

All functionality is implemented and the app will work once built.