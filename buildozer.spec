[app]
title = ATS Remote Connector
package.name = atsremoteconnector
package.domain = org.ats.remote
source.dir =.
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

requirements = python3,kivy,plyer,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, FOREGROUND_SERVICE, WAKE_LOCK

android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = armeabi-v7a, arm64-v8a
android.allow_backup = True

# --- AA 2 LINE NAVI ADD KARI ---
android.cmdline_tools = True
android.accept_sdk_license = True
# -------------------------------

[buildozer]
log_level = 2
warn_on_root = 1
