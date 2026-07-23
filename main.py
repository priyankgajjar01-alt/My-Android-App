import threading
import socket
import os
import shutil
import websocket
from kivy.config import Config

Config.set("graphics", "resizable", "0")

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.core.window import Window

# ============================================================
# ANDROID IMPORTS
# ============================================================
ANDROID = False
try:
    from android.permissions import request_permissions, check_permission, Permission
    from jnius import autoclass
    ANDROID = True
except Exception:
    ANDROID = False

# ============================================================
# WINDOW
# ============================================================
Window.clearcolor = (0.13, 0.20, 0.38, 1)

# ============================================================
# KV UI
# ============================================================
KV = r"""
<RootWidget>:
    anchor_x: "center"
    anchor_y: "center"
    
    ScrollView:
        size_hint: (0.95, 0.9)
        do_scroll_x: False
        bar_width: 8
        
        GridLayout:
            id: main_grid
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            padding: dp(10)
            spacing: dp(16)
            
            Label:
                text: "Android Tunnel Receiver"
                color: (1, 0.84, 0.00, 1)
                bold: True
                font_size: "22sp"
                size_hint_y: None
                height: dp(48)
                halign: "center"
                valign: "middle"
                
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                Label:
                    text: "Target IP :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: "18sp"
                    size_hint_x: 0.35
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    
                TextInput:
                    id: etIp
                    text: app.local_ip
                    hint_text: "Enter PC IP..."
                    multiline: False
                    size_hint_x: 0.65
                    font_size: "21sp"
                    bold: True
                    halign: "center"
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                Label:
                    text: "Tunnel :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: "18sp"
                    size_hint_x: 0.35
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    
                TextInput:
                    id: etTunnel
                    text: app.tunnel_link
                    hint_text: "e.g. https://link.com"
                    multiline: False
                    size_hint_x: 0.65
                    font_size: "21sp"
                    bold: True
                    halign: "center"
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                Label:
                    text: "Port :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: "18sp"
                    size_hint_x: 0.35
                    halign: "left"
                    valign: "middle"
                    text_size: self.size
                    
                Spinner:
                    id: etPort
                    text: app.port_value
                    values: ["80", "443", "5000", "8888", "9090"]
                    size_hint_x: 0.65
                    font_size: "21sp"
                    bold: True
                    halign: "center"
                    valign: "middle"
                    
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(14)
                padding: [0, dp(10), 0, 0]
                
                Button:
                    text: "START"
                    bold: True
                    font_size: "20sp"
                    color: (0, 0, 0, 1)
                    background_color: (0.4, 1, 0.4, 1)
                    disabled: app.start_disabled
                    on_release: app.start_connection()
                    
                Button:
                    text: "STOP"
                    bold: True
                    font_size: "20sp"
                    color: (0, 0, 0, 1)
                    background_color: (1.0, 0.23, 0.19, 1)
                    disabled: app.stop_disabled
                    on_release: app.stop_connection()
                    
            Label:
                id: statusLabel
                text: app.status_text
                color: (1, 0.84, 0.00, 1)
                bold: True
                font_size: "18sp"
                size_hint_y: None
                height: dp(70)
                halign: "center"
                valign: "middle"
                text_size: self.width, None
"""

class RootWidget(AnchorLayout):
    pass

class MainApp(App):
    local_ip = StringProperty("0.0.0.0")
    tunnel_link = StringProperty("")
    port_value = StringProperty("5000")
    status_text = StringProperty("Status: idle")
    running = BooleanProperty(False)
    start_disabled = BooleanProperty(False)
    stop_disabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_flag = threading.Event()
        self.ws_client = None
        self.ws_lock = threading.Lock()
        self.permission_check_done = False
        self.wake_lock = None
        self.wifi_lock = None

    def build(self):
        Builder.load_string(KV)
        self.local_ip = self.get_local_ipv4() or "0.0.0.0"
        self.status_text = "Checking storage permission..."
        if ANDROID:
            Clock.schedule_once(lambda dt: self.check_storage_permission(), 1)
        else:
            self.status_text = "Status: idle"
        return RootWidget()

    def get_local_ipv4(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def get_android_sdk(self):
        if not ANDROID: return 0
        try:
            Build = autoclass("android.os.Build$VERSION")
            return int(Build.SDK_INT)
        except Exception:
            return 0

    def acquire_background_locks(self):
        if not ANDROID: return
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            pm = activity.getSystemService("power")
            self.wake_lock = pm.newWakeLock(1, "AndroidTunnel::CPUWakeLock")
            self.wake_lock.acquire()
            wm = activity.getSystemService("wifi")
            self.wifi_lock = wm.createWifiLock(3, "AndroidTunnel::WiFiLock")
            self.wifi_lock.acquire()
        except Exception as e:
            print("CLIENT: Failed to acquire locks:", repr(e))

    def release_background_locks(self):
        if not ANDROID: return
        try:
            if self.wake_lock and self.wake_lock.isHeld(): self.wake_lock.release()
            if self.wifi_lock and self.wifi_lock.isHeld(): self.wifi_lock.release()
            self.wake_lock = None
            self.wifi_lock = None
        except Exception as e:
            print("CLIENT: Failed to release locks:", repr(e))

    def check_storage_permission(self):
        if not ANDROID:
            self.permission_check_done = True
            self.status_text = "Status: idle"
            return True
        sdk = self.get_android_sdk()
        if sdk >= 30:
            try:
                Environment = autoclass("android.os.Environment")
                if Environment.isExternalStorageManager():
                    self.permission_check_done = True
                    self.status_text = "Storage Permission: GRANTED"
                    return True
                self.permission_check_done = False
                self.status_text = "Allow All Files Access in Settings"
                Clock.schedule_once(lambda dt: self.open_all_files_settings(), 0.5)
                return False
            except Exception as e:
                self.status_text = "Storage Permission Error"
                return False
        else:
            try:
                permissions = []
                if not check_permission(Permission.READ_EXTERNAL_STORAGE): permissions.append(Permission.READ_EXTERNAL_STORAGE)
                if not check_permission(Permission.WRITE_EXTERNAL_STORAGE): permissions.append(Permission.WRITE_EXTERNAL_STORAGE)
                if permissions:
                    request_permissions(permissions, self.permission_callback)
                    self.status_text = "Requesting Storage Permission..."
                    return False
                self.permission_check_done = True
                self.status_text = "Storage Permission: GRANTED"
                return True
            except Exception as e:
                self.status_text = "Storage Permission Error"
                return False

    def permission_callback(self, permissions, grants):
        if all(grants):
            self.permission_check_done = True
            self.status_text = "Storage Permission: GRANTED"
        else:
            self.permission_check_done = False
            self.status_text = "Storage Permission: DENIED"

    def open_all_files_settings(self):
        if not ANDROID: return
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")
            activity = PythonActivity.mActivity
            package_name = activity.getPackageName()
            intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
            intent.setData(Uri.parse("package:" + package_name))
            activity.startActivity(intent)
            Clock.schedule_once(lambda dt: self.check_storage_permission(), 2)
        except Exception as e:
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Intent = autoclass("android.content.Intent")
                Settings = autoclass("android.provider.Settings")
                intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                PythonActivity.mActivity.startActivity(intent)
            except Exception as e2:
                pass

    def start_connection(self):
        if self.running: return
        if ANDROID:
            if not self.permission_check_done:
                if not self.check_storage_permission(): return
        tunnel_url = self.root.ids.etTunnel.text.strip()
        if tunnel_url:
            ws_url = tunnel_url
            if ws_url.startswith("https://"): ws_url = "wss://" + ws_url[8:]
            elif ws_url.startswith("http://"): ws_url = "ws://" + ws_url[7:]
            elif not ws_url.startswith(("ws://", "wss://")): ws_url = "wss://" + ws_url
        else:
            host = self.root.ids.etIp.text.strip()
            if not host: host = "127.0.0.1"
            port = self.root.ids.etPort.text.strip()
            if not port: port = "5000"
            ws_url = f"ws://{host}:{port}"
        self.acquire_background_locks()
        self.running = True
        self.start_disabled = True
        self.stop_disabled = False
        self.stop_flag.clear()
        self.status_text = f"Connecting to {ws_url}..."
        threading.Thread(target=self.client_loop, args=(ws_url,), daemon=True).start()

    def stop_connection(self):
        if not self.running: return
        self.stop_flag.set()
        self.release_background_locks()
        self.running = False
        self.start_disabled = False
        self.stop_disabled = True
        self.status_text = "Status: stopped"
        if self.ws_client:
            try: self.ws_client.close()
            except: pass
            self.ws_client = None

    def _set_status(self, text):
        self.status_text = text

    def safe_send(self, data):
        with self.ws_lock:
            if not self.ws_client:
                raise websocket.WebSocketConnectionClosedException("WebSocket is not connected")
            self.ws_client.send(data)

    def client_loop(self, ws_url):
        print("CLIENT: Starting connection")
        try:
            self.ws_client = websocket.WebSocket()
            self.ws_client.settimeout(15.0)
            self.ws_client.connect(ws_url)
            self.ws_client.settimeout(None)
            Clock.schedule_once(lambda dt: self._set_status("Connected! PC Controlled."), 0)
            
            while not self.stop_flag.is_set():
                try:
                    data = self.ws_client.recv()
                except Exception:
                    break
                if not data: break
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                data = data.strip()
                
                parts = data.split("|", 3)
                if not parts:
                    self.safe_send("ERROR|Empty command")
                    continue
                    
                cmd = parts[0].upper()
                
                # =================================================
                # LS (WITH SAFE NAME REPLACE FOR \t and \n)
                # =================================================
                if cmd == "LS":
                    if len(parts) < 2:
                        self.safe_send("ERROR|Invalid LS command")
                        continue
                    path = parts[1]
                    try:
                        if not os.path.isdir(path):
                            self.safe_send("ERROR|Folder not found")
                            continue
                        items_info = []
                        for entry in os.scandir(path):
                            try:
                                safe_name = entry.name.replace("\t", "_").replace("\n", "_")
                                if entry.is_dir():
                                    items_info.append(f"{safe_name}\tDIR\t0")
                                else:
                                    items_info.append(f"{safe_name}\tFILE\t{entry.stat().st_size}")
                            except Exception:
                                continue
                        response = "OK|" + "\n".join(items_info)
                        self.safe_send(response)
                    except Exception as e:
                        self.safe_send(f"ERROR|{str(e)}")

                # =================================================
                # STAT
                # =================================================
                elif cmd == "STAT":
                    if len(parts) < 2:
                        self.safe_send("ERROR|Invalid STAT command")
                        continue
                    path = parts[1]
                    if not os.path.exists(path):
                        self.safe_send("ERROR|Not found")
                        continue
                    if os.path.isdir(path):
                        self.safe_send("OK|DIR|0")
                    else:
                        self.safe_send(f"OK|FILE|{os.path.getsize(path)}")

                # =================================================
                # TRUNCATE
                # =================================================
                elif cmd == "TRUNCATE":
                    if len(parts) < 3:
                        self.safe_send("ERROR|Invalid TRUNCATE command")
                        continue
                    path = parts[1]
                    try:
                        size = int(parts[2])
                        with open(path, "ab"): pass
                        os.truncate(path, size)
                        self.safe_send("OK|Truncated")
                    except Exception as e:
                        self.safe_send(f"ERROR|{str(e)}")

                # =================================================
                # READ
                # =================================================
                elif cmd == "READ":
                    if len(parts) < 4:
                        self.safe_send("ERROR|Invalid READ command")
                        continue
                    path = parts[1]
                    try:
                        offset = int(parts[2])
                        length = int(parts[3])
                    except ValueError:
                        self.safe_send("ERROR|Invalid offset or length")
                        continue
                    try:
                        if not os.path.isfile(path):
                            self.safe_send("ERROR|File not found")
                            continue
                        with open(path, "rb") as f:
                            f.seek(offset)
                            chunk = f.read(length)
                        self.safe_send("OK|BINARY_FOLLOWS")
                        self.safe_send(chunk)
                    except Exception as e:
                        try: self.safe_send(f"ERROR|{str(e)}")
                        except: pass

                # =================================================
                # MKDIR
                # =================================================
                elif cmd == "MKDIR":
                    if len(parts) < 2:
                        self.safe_send("ERROR|Invalid MKDIR command")
                        continue
                    path = parts[1]
                    try:
                        os.makedirs(path, exist_ok=True)
                        self.safe_send("OK|Created")
                    except Exception as e:
                        self.safe_send(f"ERROR|{str(e)}")

                # =================================================
                # CREATE
                # =================================================
                elif cmd == "CREATE":
                    if len(parts) < 2:
                        self.safe_send("ERROR|Invalid CREATE command")
                        continue
                    path = parts[1]
                    try:
                        open(path, "ab").close()
                        self.safe_send("OK|Created")
                    except Exception as e:
                        self.safe_send(f"ERROR|{str(e)}")

                # =================================================
                # WRITE
                # =================================================
                elif cmd == "WRITE":
                    if len(parts) < 4:
                        self.safe_send("ERROR|Invalid WRITE command")
                        continue
                    path = parts[1]
                    try:
                        offset = int(parts[2])
                        length = int(parts[3])
                    except ValueError:
                        self.safe_send("ERROR|Invalid offset or length")
                        continue
                    try:
                        self.safe_send("OK|READY")
                        chunk = self.ws_client.recv()
                        if not isinstance(chunk, bytes):
                            self.safe_send("ERROR|Expected binary data")
                            continue
                        if len(chunk) != length:
                            self.safe_send(f"ERROR|Size mismatch|Expected={length}|Received={len(chunk)}")
                            continue
                        mode = "r+b" if os.path.exists(path) else "wb"
                        with open(path, mode) as f:
                            f.seek(offset)
                            f.write(chunk)
                        self.safe_send(f"OK|{len(chunk)}")
                    except Exception as e:
                        try: self.safe_send(f"ERROR|{str(e)}")
                        except: pass

                # =================================================
                # DELETE
                # =================================================
                elif cmd == "DELETE":
                    if len(parts) < 2:
                        self.safe_send("ERROR|Invalid DELETE command")
                        continue
                    path = parts[1]
                    try:
                        if os.path.isdir(path): shutil.rmtree(path)
                        elif os.path.isfile(path): os.remove(path)
                        else:
                            self.safe_send("ERROR|File not found")
                            continue
                        self.safe_send("OK|Deleted")
                    except Exception as e:
                        self.safe_send(f"ERROR|{str(e)}")

                # =================================================
                # RENAME
                # =================================================
                elif cmd == "RENAME":
                    if len(parts) < 3:
                        self.safe_send("ERROR|Invalid RENAME command")
                        continue
                    old_path = parts[1]
                    new_path = parts[2]
                    try:
                        os.rename(old_path, new_path)
                        self.safe_send("OK|Renamed")
                    except Exception as e:
                        self.safe_send(f"ERROR|{str(e)}")

                else:
                    self.safe_send("ERROR|Unknown command")
        except Exception as e:
            print("CLIENT: Connection error:", repr(e))
        finally:
            self.release_background_locks()
            if self.ws_client:
                try: self.ws_client.close()
                except: pass
                self.ws_client = None
            Clock.schedule_once(lambda dt: self.reset_buttons_after_disconnect(), 0)

    def reset_buttons_after_disconnect(self):
        self.running = False
        self.start_disabled = False
        self.stop_disabled = True
        if self.status_text == "Connected! PC Controlled.":
            self.status_text = "Status: disconnected"

    def on_resume(self):
        if ANDROID:
            Clock.schedule_once(lambda dt: self.check_storage_permission(), 0.5)

if __name__ == "__main__":
    MainApp().run()
