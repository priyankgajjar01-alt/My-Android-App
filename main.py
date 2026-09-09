import os
import json
import threading
import time
import socket
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.utils import platform

# Check if running as a Real Android APK (JNI supported)
is_real_android = False
if platform == 'android':
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        UUID = autoclass('java.util.UUID')
        is_real_android = True
    except:
        is_real_android = False

Window.clearcolor = (10/255, 25/255, 47/255, 1)

KV = '''
<RoundedTextInput@TextInput>:
    background_color: 0, 0, 0, 0
    cursor_color: 0.39, 1.0, 0.85, 1
    foreground_color: 0.39, 1.0, 0.85, 1
    multiline: False
    halign: 'center'
    padding: [10, 15, 10, 15]
    canvas.before:
        Color:
            rgba: 0.04, 0.1, 0.18, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12, 12, 12, 12]

<RoundedButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    bg_color: 0.39, 1.0, 0.85, 1
    color: 0.04, 0.1, 0.18, 1
    canvas.before:
        Color:
            rgba: self.bg_color if self.state == 'normal' else (self.bg_color[0]*0.8, self.bg_color[1]*0.8, self.bg_color[2]*0.8, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [18, 18, 18, 18]

<StatusLabel@Label>:
    bg_color: 0.82, 0.18, 0.18, 1
    canvas.before:
        Color:
            rgba: self.bg_color
        Rectangle:
            pos: self.pos
            size: self.size

<SettingsPopup>:
    title: 'Button Value Settings'
    title_color: 0.39, 1.0, 0.85, 1
    title_size: '20sp'
    background_color: 0.07, 0.13, 0.25, 1
    size_hint: 0.95, 0.95
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '15dp'

        GridLayout:
            cols: 2
            spacing: '15dp'
            row_default_height: '45dp'
            row_force_default: True

            Label:
                text: 'MAC Address'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.hc05_mac
                on_text: app.hc05_mac = self.text

            Label:
                text: 'ON Delay'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.on_delay
                on_text: app.on_delay = self.text

            Label:
                text: 'OFF Delay'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.off_delay
                on_text: app.off_delay = self.text

            Label:
                text: 'Slider 1 ON'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.s1_on_msg
                on_text: app.s1_on_msg = self.text

            Label:
                text: 'Slider 1 OFF'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.s1_off_msg
                on_text: app.s1_off_msg = self.text

            Label:
                text: 'Slider 2 ON'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.s2_on_msg
                on_text: app.s2_on_msg = self.text

            Label:
                text: 'Slider 2 OFF'
                color: 0.8, 0.84, 0.96, 1
                bold: True
            RoundedTextInput:
                text: app.s2_off_msg
                on_text: app.s2_off_msg = self.text

        RoundedButton:
            text: 'Save & Close'
            size_hint_y: None
            height: '70dp'
            bg_color: 0.0, 0.78, 0.32, 1
            bold: True
            font_size: '22sp'
            on_release: app.save_and_close_settings()

BoxLayout:
    orientation: 'vertical'

    StatusLabel:
        id: status_lbl
        text: 'Disconnected'
        size_hint_y: None
        height: '60dp'
        bold: True
        font_size: '22sp'
        color: 1, 1, 1, 1

    BoxLayout:
        orientation: 'vertical'

        # TOP 50%
        BoxLayout:
            padding: '15dp'
            TextInput:
                id: monitor
                readonly: True
                background_color: 0, 0, 0, 0 
                foreground_color: 0.39, 1.0, 0.85, 1
                font_size: '13sp'
                text: 'System Ready...\\n'
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1 
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [15, 15, 15, 15]

        # BOTTOM 50%
        BoxLayout:
            orientation: 'vertical'
            padding: '30dp'
            spacing: '30dp'

            BoxLayout:
                size_hint_y: None
                height: '80dp'
                Label:
                    text: 'Slider 1'
                    font_size: '36sp' 
                    bold: True
                    color: 0.8, 0.84, 0.96, 1
                Switch:
                    id: s1
                    on_active: app.s1_toggle(self.active)
                    canvas.before:
                        PushMatrix
                        Scale:
                            origin: self.center
                            x: 2.0
                            y: 2.0
                    canvas.after:
                        PopMatrix

            BoxLayout:
                size_hint_y: None
                height: '80dp'
                Label:
                    text: 'Slider 2'
                    font_size: '36sp'
                    bold: True
                    color: 0.8, 0.84, 0.96, 1
                Switch:
                    id: s2
                    on_active: app.s2_toggle(self.active)
                    canvas.before:
                        PushMatrix
                        Scale:
                            origin: self.center
                            x: 2.0
                            y: 2.0
                    canvas.after:
                        PopMatrix

            AnchorLayout:
                RoundedButton:
                    text: 'Settings'
                    size_hint: None, None
                    size: '250dp', '70dp'
                    bg_color: 0.39, 1.0, 0.85, 1
                    bold: True
                    font_size: '24sp'
                    on_release: app.open_settings()
'''

class SettingsPopup(Popup):
    pass

class BluetoothApp(App):
    hc05_mac = StringProperty("98:D3:31:F4:XX:XX")
    on_delay = StringProperty("1000")
    off_delay = StringProperty("1000")
    s1_on_msg = StringProperty("S1_ON")
    s1_off_msg = StringProperty("S1_OFF")
    s2_on_msg = StringProperty("S2_ON")
    s2_off_msg = StringProperty("S2_OFF")

    def build(self):
        self.bt_socket = None
        self.bt_out = None
        self.bt_in = None
        self.is_connected = False
        self.waiting_ack = False
        self.pending_data = ""
        
        self.load_settings()
        self.root = Builder.load_string(KV)
        self.settings_popup = SettingsPopup()
        
        self.log(f"Loaded MAC: {self.hc05_mac}")
        threading.Thread(target=self.connect_bluetooth, daemon=True).start()
        return self.root

    def load_settings(self):
        if os.path.exists("bt_settings.json"):
            try:
                with open("bt_settings.json", "r") as f:
                    data = json.load(f)
                    if "mac" in data: self.hc05_mac = data["mac"]
                    if "on_delay" in data: self.on_delay = data["on_delay"]
                    if "off_delay" in data: self.off_delay = data["off_delay"]
                    if "s1_on" in data: self.s1_on_msg = data["s1_on"]
                    if "s1_off" in data: self.s1_off_msg = data["s1_off"]
                    if "s2_on" in data: self.s2_on_msg = data["s2_on"]
                    if "s2_off" in data: self.s2_off_msg = data["s2_off"]
            except: pass

    def save_settings_to_file(self):
        data = {
            "mac": self.hc05_mac.strip(), "on_delay": self.on_delay, "off_delay": self.off_delay,
            "s1_on": self.s1_on_msg, "s1_off": self.s1_off_msg, "s2_on": self.s2_on_msg, "s2_off": self.s2_off_msg
        }
        try:
            with open("bt_settings.json", "w") as f:
                json.dump(data, f)
        except: pass

    def open_settings(self):
        self.settings_popup.open()

    def save_and_close_settings(self):
        self.save_settings_to_file()
        data = f"SET:{self.on_delay},{self.off_delay}"
        self.send_data(data)
        self.settings_popup.dismiss()

    @mainthread
    def log(self, msg):
        monitor = self.root.ids.monitor
        monitor.text += msg + "\n"
        monitor.cursor = (0, len(monitor.text))

    @mainthread
    def update_status(self, text, bg_color):
        self.root.ids.status_lbl.text = text
        self.root.ids.status_lbl.bg_color = bg_color

    def connect_bluetooth(self):
        mac = self.hc05_mac.strip()
        self.log(f"Connecting to {mac}...")
        try:
            if is_real_android:
                # Android Native Java API logic (For APK)
                adapter = BluetoothAdapter.getDefaultAdapter()
                device = adapter.getRemoteDevice(mac)
                spp_uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
                self.bt_socket = device.createRfcommSocketToServiceRecord(spp_uuid)
                adapter.cancelDiscovery()
                self.bt_socket.connect()
                self.bt_out = self.bt_socket.getOutputStream()
                self.bt_in = self.bt_socket.getInputStream()
                self.is_connected = True
            else:
                # Standard Python Socket (For Pydroid / PC)
                if hasattr(socket, 'AF_BLUETOOTH'):
                    self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                    self.bt_socket.connect((mac, 1))
                    self.is_connected = True
                else:
                    self.log("AF_BLUETOOTH missing. Simulated Mode.")

            if self.is_connected:
                threading.Thread(target=self.listen_for_ack, daemon=True).start()
                self.update_status("Connected via Bluetooth!", [0.0, 0.78, 0.32, 1])
                self.log("HC-05 Connected Successfully!")

        except Exception as e:
            self.is_connected = False
            self.update_status("Disconnected", [0.82, 0.18, 0.18, 1])
            self.log(f"Failed: {str(e)}")

    def listen_for_ack(self):
        while self.is_connected and self.bt_socket:
            try:
                if is_real_android:
                    buffer = bytearray(1024)
                    bytes_read = self.bt_in.read(buffer)
                    if bytes_read > 0:
                        recv_data = buffer[:bytes_read].decode('utf-8', 'ignore').strip()
                        if recv_data:
                            self.log(f"RCV: {recv_data}")
                            if "OK" in recv_data.upper(): self.waiting_ack = False
                else:
                    recv_data = self.bt_socket.recv(1024).decode("utf-8").strip()
                    if recv_data:
                        self.log(f"RCV: {recv_data}")
                        if "OK" in recv_data.upper(): self.waiting_ack = False
            except:
                break

    def send_data(self, data, is_retry=False):
        if self.is_connected and self.bt_socket:
            try:
                msg = (data + "\n").encode("utf-8")
                if is_real_android:
                    self.bt_out.write(msg)
                    self.bt_out.flush()
                else:
                    self.bt_socket.send(msg)
                
                self.log(f"RE-SENT: {data}" if is_retry else f"SENT: {data}")
                self.waiting_ack = True
                self.pending_data = data
                Clock.schedule_once(lambda dt: self.check_ack(data, is_retry), 3)
            except:
                self.update_status("Disconnected", [0.82, 0.18, 0.18, 1])
                self.is_connected = False
        else:
            self.log(f"Simulated SENT: {data}")

    def check_ack(self, data, is_retry):
        if self.is_connected and self.waiting_ack and self.pending_data == data:
            if not is_retry:
                self.log("No message! Retrying...")
                self.send_data(data, is_retry=True)
            else:
                self.log("Controller Not Responding")
                self.waiting_ack = False 

    def s1_toggle(self, is_active):
        self.send_data(self.s1_on_msg if is_active else self.s1_off_msg)

    def s2_toggle(self, is_active):
        self.send_data(self.s2_on_msg if is_active else self.s2_off_msg)

if __name__ == "__main__":
    try:
        BluetoothApp().run()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
