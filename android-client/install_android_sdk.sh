#!/bin/bash

echo "=== Android SDK Installer for Linux ==="
echo ""

# Set SDK location
ANDROID_HOME="$HOME/Android/Sdk"
CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-10406996_latest.zip"

# Create directories
echo "Creating Android SDK directory..."
mkdir -p "$ANDROID_HOME/cmdline-tools"

# Download command line tools
echo "Downloading Android command line tools..."
cd /tmp
wget -q --show-progress "$CMDLINE_TOOLS_URL" -O cmdline-tools.zip

# Extract tools
echo "Extracting tools..."
unzip -q cmdline-tools.zip
mv cmdline-tools "$ANDROID_HOME/cmdline-tools/latest"
rm cmdline-tools.zip

# Set up environment
echo "Setting up environment..."
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

# Accept licenses
echo "Accepting licenses..."
yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null 2>&1

# Install required SDK components
echo "Installing SDK components..."
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
    "platform-tools" \
    "platforms;android-34" \
    "build-tools;34.0.0" \
    "sources;android-34"

# Update local.properties
echo "Updating local.properties..."
cd "$HOME/rtts/RealtimeSTT/android-client"
echo "sdk.dir=$ANDROID_HOME" > local.properties

# Add to bashrc
echo ""
echo "Add these lines to your ~/.bashrc:"
echo "export ANDROID_HOME=$HOME/Android/Sdk"
echo 'export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH'
echo ""
echo "Then run: source ~/.bashrc"
echo ""
echo "Android SDK installed successfully!"