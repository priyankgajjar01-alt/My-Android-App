[app]
title = ATS Remote Connector
package.name = atsremoteconnector
package.domain = org.ats.remote
source.dir =.
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

requirements = python3,kivy,plyer,pyjnius,android
orientation = portrait
fullscreen = 0

android.permissions = INTERNET, FOREGROUND_SERVICE, WAKE_LOCK
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.cmdline_tools = True
android.accept_sdk_license = True

# --- AA 2 LINE NAVI ---
android.p4a.branch = master
p4a.source_dir =
# ----------------------

[buildozer]
log_level = 2
warn_on_root = 1
