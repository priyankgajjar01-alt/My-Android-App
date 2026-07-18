import threading, socket, random, os, shutil
import websocket
from kivy.config import Config
Config.set('graphics', 'resizable', '0')

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.core.window import Window

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
                    readonly: True  
                    multiline: False
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
            
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
                    readonly: True  
                    multiline: False
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]

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
                    multiline: False
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
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
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                TextInput:
                    id: etTunnel
                    text: app.tunnel_link
                    hint_text: "e.g. https://link.com"
                    multiline: False
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
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
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                Spinner:
                    id: etPort
                    text: app.port_value
                    values: ["80", "443", "5000", "8888", "9090"]
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    valign: 'middle'

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
                    color: (0, 0, 0, 1) 
                    background_color: (0.4, 1, 0.4, 1) 
                    on_release: app.on_start()
                Button:
                    text: "STOP"
                    bold: True
                    font_size: '20sp'
                    color: (0, 0, 0, 1) 
                    background_color: (1.0, 0.23, 0.19, 1) 
                    on_release: app.on_stop()

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
    port_value = StringProperty("5000") 
    status_text = StringProperty("Status: idle")
    running = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_flag = threading.Event()
        self.ws_client = None

    def build(self):
        Builder.load_string(KV)
        self.id_value = self.generate_6digit()
        self.pass_value = self.generate_6digit()
        self.local_ip = self.get_local_ipv4() or "0.0.0.0"
        self.status_text = "Status: idle"
        return RootWidget()

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
        if self.running: return

        expected_id = self.root.ids.etId.text.strip() if self.root else self.id_value
        expected_pass = self.root.ids.etPass.text.strip() if self.root else self.pass_value
        tunnel_url = self.root.ids.etTunnel.text.strip()

        if tunnel_url:
            ws_url = tunnel_url.replace("https://", "wss://").replace("http://", "ws://")
            if not ws_url.startswith("ws"): ws_url = f"wss://{tunnel_url}"
        else:
            host = self.root.ids.etIp.text.strip() or "127.0.0.1"
            port_text = self.root.ids.etPort.text.strip().split()[0]
            ws_url = f"ws://{host}:{port_text}"

        self.running = True
        self.stop_flag.clear()
        self.status_text = f"Connecting to {ws_url}..."
        threading.Thread(target=self.client_loop, args=(ws_url, expected_id, expected_pass), daemon=True).start()

    def _set_status(self, t):
        self.status_text = t

    def on_stop(self):
        if not self.running: return
        self.stop_flag.set()
        self.running = False
        self.status_text = "Status: stopped"
        if self.ws_client:
            try: self.ws_client.close()
            except: pass
        if self.root:
            self.root.ids.etId.text = self.generate_6digit()
            self.root.ids.etPass.text = self.generate_6digit()

    def client_loop(self, ws_url, expected_id, expected_pass):
        try:
            self.ws_client = websocket.WebSocket()
            self.ws_client.settimeout(15.0) 
            self.ws_client.connect(ws_url)
            self.ws_client.settimeout(None) 
            
            Clock.schedule_once(lambda dt: self._set_status("Connected! Waiting for Auth..."), 0)

            auth_msg = self.ws_client.recv()
            if isinstance(auth_msg, bytes): auth_msg = auth_msg.decode('utf-8')
            
            if auth_msg.strip() == f"AUTH|{expected_id}|{expected_pass}":
                self.ws_client.send("OK|ACCESS_GRANTED")
                Clock.schedule_once(lambda dt: self._set_status("Auth Success! PC Controlled."), 0)
            else:
                self.ws_client.send("DENY|INVALID_CREDENTIALS")
                self.ws_client.close()
                Clock.schedule_once(lambda dt: self._set_status("Auth Failed. Disconnected."), 0)
                self.running = False
                return

            # Main Command Loop (FUSE API)
            while not self.stop_flag.is_set():
                data = self.ws_client.recv()
                if not data: break
                if isinstance(data, bytes): data = data.decode('utf-8')
                
                parts = data.strip().split("|")
                cmd = parts[0].upper()

                try:
                    if cmd == "LS":
                        path = parts[1]
                        if os.path.isdir(path):
                            items_info = []
                            for name in os.listdir(path):
                                full_p = os.path.join(path, name)
                                if os.path.isdir(full_p):
                                    items_info.append(f"{name}:DIR:0")
                                else:
                                    try: sz = os.path.getsize(full_p)
                                    except: sz = 0
                                    items_info.append(f"{name}:FILE:{sz}")
                            self.ws_client.send("OK|" + ",".join(items_info))
                        else:
                            self.ws_client.send("ERROR|Folder not found")

                    # ૨. Raw Binary મોકલવાનું લોજીક (No Base64!)
                    elif cmd == "READ":
                        path = parts[1]
                        offset = int(parts[2])
                        length = int(parts[3])
                        if os.path.isfile(path):
                            with open(path, 'rb') as f:
                                f.seek(offset)
                                chunk = f.read(length) # ઓરિજિનલ Bytes
                            
                            # પહેલા Text Frame (કન્ફર્મેશન)
                            self.ws_client.send("OK|BINARY_FOLLOWS") 
                            
                            # તરત જ બીજો મેસેજ (Raw Binary Frame) મોકલો
                            self.ws_client.send(chunk)
                        else:
                            self.ws_client.send("ERROR|File not found")

                    elif cmd == "DELETE":
                        path = parts[1]
                        if os.path.isdir(path): shutil.rmtree(path)
                        else: os.remove(path)
                        self.ws_client.send("OK|Deleted")

                    elif cmd == "RENAME":
                        os.rename(parts[1], parts[2])
                        self.ws_client.send("OK|Renamed")

                except Exception as e:
                    self.ws_client.send(f"ERROR|{str(e)}")

        except Exception as e:
            Clock.schedule_once(lambda dt: self._set_status(f"Error: Connection Failed"), 0)
        finally:
            self.running = False
            if self.ws_client:
                try: self.ws_client.close()
                except: pass

if __name__ == "__main__":
    MainApp().run()
