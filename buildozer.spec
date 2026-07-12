[app]
title = ATS Remote Connector
package.name = atsremoteconnector
package.domain = org.ats.remote
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# Kivy અને Plyer (નોટિફિકેશન માટે jnius ની જરૂર પડશે)
requirements = python3,kivy==2.3.0,plyer,jnius

orientation = portrait
fullscreen = 0

# ઇન્ટરનેટ અને બેકગ્રાઉન્ડ સર્વિસ પર્મિશન્સ
android.permissions = INTERNET, FOREGROUND_SERVICE

android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = armeabi-v7a, arm64-v8a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
