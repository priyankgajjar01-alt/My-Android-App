import threading, socket, random, os, shutil
from kivy.config import Config
Config.set('graphics', 'resizable', '0')

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.core.window import Window
from kivy.utils import platform  # <--- પરમિશન ચેક કરવા માટે ઉમેર્યું

# Navy Blue background
Window.clearcolor = (0.13, 0.20, 0.38, 1)

KV = r"""
<RootWidget>:
    anchor_x: 'center'
    anchor_y: 'center'
    
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
                font_size: '22sp'
                size_hint_y: None
                height: dp(48)
                halign: "center"
                valign: "middle"
                text_size: self.width, None

            # --- Row 1: ID ---
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                Label:
                    text: "ID :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                TextInput:
                    id: etId
                    text: app.id_value
                    hint_text: "6-digit"
                    readonly: True  
                    multiline: False
                    input_filter: "int"
                    size_hint_x: 0.65
                    foreground_color: (0, 0, 0, 1)
                    cursor_color: (0, 0, 0, 1)
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    background_normal: ""
                    background_color: (0.83, 0.83, 0.83, 1)

            # --- Row 2: Password ---
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                Label:
                    text: "Password :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                TextInput:
                    id: etPass
                    text: app.pass_value
                    hint_text: "6-digit"
                    readonly: True  
                    multiline: False
                    input_filter: "int"
                    size_hint_x: 0.65
                    foreground_color: (0, 0, 0, 1)
                    cursor_color: (0, 0, 0, 1)
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    background_normal: ""
                    background_color: (0.83, 0.83, 0.83, 1)

            # --- Row 3: Target IP ---
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                Label:
                    text: "Target IP :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                TextInput:
                    id: etIp
                    text: app.local_ip
                    hint_text: "Enter PC IP..."
                    readonly: False  
                    multiline: False
                    size_hint_x: 0.65
                    foreground_color: (0, 0, 0, 1)
                    cursor_color: (0, 0, 0, 1)
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    background_normal: ""
                    background_color: (0.83, 0.83, 0.83, 1)

            # --- Row 4: Tunnel Link ---
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                Label:
                    text: "Tunnel :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                TextInput:
                    id: etTunnel
                    text: app.tunnel_link
                    hint_text: "Optional link"
                    multiline: False
                    size_hint_x: 0.65
                    foreground_color: (0, 0, 0, 1)
                    cursor_color: (0, 0, 0, 1)
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    background_normal: ""
                    background_color: (0.83, 0.83, 0.83, 1)

            # --- Row 5: Port (Dropdown Menu) ---
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                Label:
                    text: "Port :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                Spinner:
                    id: etPort
                    text: app.port_value
                    values: ["80 (Tunnel)", "22 (ssh)", "443 (Tunnel)", "443 (LT-HTTPS/WebSocket)", "8888", "9090", "4444"]
                    size_hint_x: 0.65
                    color: (0, 0, 0, 1) 
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    valign: 'middle'
                    background_normal: ""
                    background_color: (0.83, 0.83, 0.83, 1)

            # --- Row 6: Buttons ---
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(14)
                padding: [0, dp(10), 0, 0]

                Button:
                    text: "START"
                    bold: True
                    font_size: '20sp'
                    background_normal: ""
                    color: (0, 0, 0, 1) 
                    background_color: (0.4, 1, 0.4, 1) 
                    on_release: app.on_start()

                Button:
                    text: "STOP"
                    bold: True
                    font_size: '20sp'
                    background_normal: ""
                    color: (0, 0, 0, 1) 
                    background_color: (1.0, 0.23, 0.19, 1) 
                    on_release: app.on_stop()

            # --- Row 7: Status ---
            Label:
                id: statusLabel
                text: app.status_text
                color: (1, 0.84, 0.00, 1)
                bold: True
                font_size: '18sp'
                size_hint_y: None
                height: dp(50)
                halign: "center"
                valign: "middle"
                text_size: self.width, None
"""

class RootWidget(AnchorLayout):
    pass

class MainApp(App):
    id_value = StringProperty("")
    pass_value = StringProperty("")
    local_ip = StringProperty("0.0.0.0")
    tunnel_link = StringProperty("")
    port_value = StringProperty("4444") 
    status_text = StringProperty("Status: idle")
    running = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_flag = threading.Event()
        self.client_socket = None

    def build(self):
        Builder.load_string(KV)
        self.id_value = self.generate_6digit()
        self.pass_value = self.generate_6digit()
        self.local_ip = self.get_local_ipv4() or "0.0.0.0"
        self.status_text = "Status: idle"
        
        # એપ ચાલુ થાય ત્યારે જ પરમિશન ચેક કરવા કમાન્ડ
        Clock.schedule_once(lambda dt: self.check_and_request_permissions(), 0)
        
        return RootWidget()

    def check_and_request_permissions(self):
        """Android પરમિશન્સ ચેક અને રિક્વેસ્ટ કરવાનું ફંક્શન"""
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                from jnius import autoclass
                
                # ૧. Android 10 અને નીચેના માટે નોર્મલ સ્ટોરેજ પરમિશન
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.INTERNET
                ])
                
                # ૨. Android 11+ (API 30+) માટે All Files Access પરમિશન
                BuildVersion = autoclass('android.os.Build$VERSION')
                api_level = BuildVersion.SDK_INT
                
                if api_level >= 30:
                    Environment = autoclass('android.os.Environment')
                    
                    # જો પરમિશન ના હોય તો જ સેટિંગ્સ પેજ ખોલો
                    if not Environment.isExternalStorageManager():
                        Intent = autoclass('android.content.Intent')
                        Settings = autoclass('android.provider.Settings')
                        Uri = autoclass('android.net.Uri')
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        
                        current_activity = PythonActivity.mActivity
                        package_uri = Uri.parse("package:" + current_activity.getPackageName())
                        
                        # Settings પેજ ઓપન કરવાનો ઇન્ટેન્ટ (Intent)
                        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, package_uri)
                        current_activity.startActivity(intent)
                        
            except Exception as e:
                print(f"Permission Error: {str(e)}")

    def generate_6digit(self):
        return str(random.randint(100000, 999999))

    def get_local_ipv4(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def on_start(self):
        if self.running:
            return

        expected_id = self.root.ids.etId.text.strip() if self.root else self.id_value
        expected_pass = self.root.ids.etPass.text.strip() if self.root else self.pass_value
        tunnel_url = self.root.ids.etTunnel.text.strip()

        # Parse Connection Details (Tunnel Link OR Local IP)
        if tunnel_url:
            # e.g., tcp://pinggy.link:43210 -> host: pinggy.link, port: 43210
            url = tunnel_url.replace("tcp://", "").replace("http://", "").replace("https://", "")
            if ":" in url:
                host, port_str = url.split(":", 1)
                port = int(port_str.split("/")[0])
            else:
                host = url
                port_text = self.root.ids.etPort.text.strip().split()[0]
                port = int(port_text)
        else:
            host = self.root.ids.etIp.text.strip() or "127.0.0.1"
            port_text = self.root.ids.etPort.text.strip().split()[0]
            port = int(port_text)

        self.running = True
        self.stop_flag.clear()
        self.status_text = f"Connecting to {host}:{port}..."

        # Start Client Thread
        threading.Thread(target=self.client_loop, args=(host, port, expected_id, expected_pass), daemon=True).start()

    def _set_status(self, t):
        self.status_text = t

    def on_stop(self):
        if not self.running:
            return
        self.stop_flag.set()
        self.running = False
        self.status_text = "Status: stopped"
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        # STOP thaya pachi nava ID ane Password
        if self.root:
            self.root.ids.etId.text = self.generate_6digit()
            self.root.ids.etPass.text = self.generate_6digit()

    def client_loop(self, host, port, expected_id, expected_pass):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(15.0) # Wait 15s to connect
            self.client_socket.connect((host, port))
            self.client_socket.settimeout(None) # Remove timeout for persistent connection
            
            Clock.schedule_once(lambda dt: self._set_status("Connected! Waiting for Auth..."), 0)

            # 1. PC will send: AUTH|ID|PASS
            auth_msg = self.client_socket.recv(1024).decode('utf-8').strip()
            
            if auth_msg == f"AUTH|{expected_id}|{expected_pass}":
                self.client_socket.sendall(b"OK|ACCESS_GRANTED\n")
                Clock.schedule_once(lambda dt: self._set_status("Auth Success! PC Controlled."), 0)
            else:
                self.client_socket.sendall(b"DENY|INVALID_CREDENTIALS\n")
                self.client_socket.close()
                Clock.schedule_once(lambda dt: self._set_status("Auth Failed. PC Disconnected."), 0)
                self.running = False
                return

            # 2. Main Command Loop (For Storage Access)
            while not self.stop_flag.is_set():
                # Read command until newline
                data = b""
                while b"\n" not in data:
                    chunk = self.client_socket.recv(1024)
                    if not chunk: break
                    data += chunk
                
                if not data: break
                
                cmd_line = data.decode('utf-8').strip()
                parts = cmd_line.split("|")
                cmd = parts[0].upper()

                try:
                    # List Directory (LS|/sdcard)
                    if cmd == "LS":
                        path = parts[1]
                        if os.path.isdir(path):
                            items = os.listdir(path)
                            res = "OK|" + ",".join(items)
                        else:
                            res = "ERROR|Folder not found"
                        self.client_socket.sendall((res + "\n").encode('utf-8'))

                    # Rename / Move (RENAME|/old_path|/new_path)
                    elif cmd == "RENAME":
                        os.rename(parts[1], parts[2])
                        self.client_socket.sendall(b"OK|Renamed Successfully\n")

                    # Delete File or Folder (DELETE|/sdcard/test.txt)
                    elif cmd == "DELETE":
                        path = parts[1]
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        self.client_socket.sendall(b"OK|Deleted Successfully\n")

                    # Send File to PC (DOWNLOAD|/sdcard/photo.jpg)
                    elif cmd == "DOWNLOAD":
                        path = parts[1]
                        if os.path.isfile(path):
                            size = os.path.getsize(path)
                            self.client_socket.sendall(f"OK|{size}\n".encode('utf-8'))
                            with open(path, 'rb') as f:
                                while True:
                                    bytes_read = f.read(1048576) # <-- 1 MB Buffer Set
                                    if not bytes_read: break
                                    self.client_socket.sendall(bytes_read)
                        else:
                            self.client_socket.sendall(b"ERROR|File not found\n")

                    # Receive File from PC (UPLOAD|/sdcard/new.txt|1024)
                    elif cmd == "UPLOAD":
                        path = parts[1]
                        size = int(parts[2])
                        self.client_socket.sendall(b"READY\n") # Tell PC to start sending bytes
                        
                        received = 0
                        with open(path, 'wb') as f:
                            while received < size:
                                chunk = self.client_socket.recv(min(1048576, size - received)) # <-- 1 MB Buffer Set
                                if not chunk: break
                                f.write(chunk)
                                received += len(chunk)
                        
                        self.client_socket.sendall(b"OK|Upload Complete\n")

                except Exception as e:
                    self.client_socket.sendall(f"ERROR|{str(e)}\n".encode('utf-8'))

        except Exception as e:
            Clock.schedule_once(lambda dt: self._set_status(f"Error: Connection Failed"), 0)
        finally:
            self.running = False
            if self.client_socket:
                try: self.client_socket.close()
                except: pass

if __name__ == "__main__":
    MainApp().run()
