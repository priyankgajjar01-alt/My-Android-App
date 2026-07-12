[app]
title = ATS Remote Connector
package.name = atsremoteconnector
package.domain = org.ats.remote
source.dir =.
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0

requirements = python3,kivy,android

orientation = portrait
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25.1.8937393
android.build_tools = 33.0.2
android.archs = arm64-v8a

# OLD LINK HATAVI - NAVA STABLE LINK
android.p4a.url = https://github.com/kivy/python-for-android/archive/refs/tags/2024.08.22.zip

[buildozer]
log_level = 1
