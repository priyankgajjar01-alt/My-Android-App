[app]
title = ATS Remote Connector
package.name = atsremoteconnector
package.domain = org.ats.remote
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# 🛠️ સુધારો ૪: jnius ની જગ્યાએ pyjnius વાપર્યું
requirements = python3,kivy,plyer,pyjnius

orientation = portrait
fullscreen = 0

# 🛠️ સુધારો ૫: WAKE_LOCK પર્મિશન એડ કરી
android.permissions = INTERNET, FOREGROUND_SERVICE, WAKE_LOCK

android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = armeabi-v7a, arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
