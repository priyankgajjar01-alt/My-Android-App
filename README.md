# My-Android-App

# 🚀 ATS Remote Connector

Remote storage access between Android device and Linux PC using Python for Android.

## Features

✅ **Local Network Access** - Access storage on same WiFi network
✅ **Remote Access** - Connect from different networks via SSH tunnel
✅ **File Operations** - Read, Write, Delete, List files remotely
✅ **Secure** - ID + Password authentication
✅ **Automatic Build** - GitHub Actions workflow included

## Installation

### Prerequisites
- Android device (Android 6.0+)
- Linux PC with Python 3.8+
- Network connection

### Build APK

#### Method 1: GitHub Actions (Recommended)

1. Push code to GitHub
2. Go to **Actions** tab
3. Select **"Build APK with Python for Android"**
4. Click **"Run workflow"**
5. Wait 30-45 minutes
6. Download APK from artifacts

#### Method 2: Local Build

```bash
# Install dependencies
pip install python-for-android cython kivy

# Setup Android SDK/NDK
mkdir -p ~/android/sdk/cmdline-tools
cd ~/android/sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip

# Build
p4a apk --debug --private . \
  --package=org.ats.remote \
  --name="ATS Remote" \
  --version=1.0 \
  --bootstrap=sdl2 \
  --requirements=hostpython3,python3,kivy,openssl \
  --permission=INTERNET \
  --permission=READ_EXTERNAL_STORAGE \
  --permission=WRITE_EXTERNAL_STORAGE \
  --arch=arm64-v8a \
  --android-api=34
