import os
import json
import threading
import time
import socket
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp

# JNI Check (Android mate)
is_real_android = False
if platform == 'android':
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        UUID = autoclass('java.util.UUID')
        InputStreamReader = autoclass('java.io.InputStreamReader')
        BufferedReader = autoclass('java.io.BufferedReader')
        JavaString = autoclass('java.lang.String')
        is_real_android = True
    except Exception as e:
        print("JNI Loading Error:", e)

# Dark Navy Background
Window.clearcolor = (10/255, 25/255, 47/255, 1)

KV = '''
<CustomTextInput@TextInput>:
    background_normal: ''
    background_color: [0.04, 0.1, 0.18, 1]
    foreground_color: [0.39, 1.0, 0.85, 1]
    cursor_color: [0.39, 1.0, 0.85, 1]
    multiline: False
    halign: 'center'
    font_size: '15sp'
    size_hint_y: None
    height: '40dp'
    padding_y: (self.height - self.line_height) / 2
    use_bubble: False
    use_handles: False

<RoundedButton@Button>:
    background_color: [0, 0, 0, 0]
    background_normal: ''
    bg_color: [0.39, 1.0, 0.85, 1]
    color: [0.04, 0.1, 0.18, 1]
    canvas.before:
        Color:
            rgba: self.bg_color if self.state == 'normal' else [self.bg_color[0]*0.8, self.bg_color[1]*0.8, self.bg_color[2]*0.8, 1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [18, 18, 18, 18]

# ===== FORCE UPDATE BUTTON (with glow) =====
<ForceButton@Button>:
    background_normal: ''
    background_color: [0, 0, 0, 0]
    bold: True
    font_size: '17sp'
    color: [0.04, 0.1, 0.18, 1] if self.state == 'down' else [0.39, 1.0, 0.85, 1]
    canvas.before:
        # Outer glow (only when pressed)
        Color:
            rgba: [0.39, 1.0, 0.85, 0.35] if self.state == 'down' else [0, 0, 0, 0]
        RoundedRectangle:
            pos: self.x - 4, self.y - 4
            size: self.width + 8, self.height + 8
            radius: [28, 28, 28, 28]
        # Main button background
        Color:
            rgba: [0.39, 1.0, 0.85, 1] if self.state == 'down' else [0.1, 0.2, 0.3, 1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [25, 25, 25, 25]
        # Border
        Color:
            rgba: [0.39, 1.0, 0.85, 1]
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 25]
            width: 2

<StatusLabel@Label>:
    bg_color: [0.82, 0.18, 0.18, 1]
    selectable: False
    canvas.before:
        Color:
            rgba: self.bg_color
        Rectangle:
            pos: self.pos
            size: self.size

# ===== DATA FORMAT POPUP =====
<DataFormatPopup>:
    title: 'Data Format & Logic'
    title_color: [0.39, 1.0, 0.85, 1]
    title_size: '18sp'
    separator_color: [0.39, 1.0, 0.85, 1]
    background_color: [0.11, 0.14, 0.18, 1]
    size_hint: 0.9, 0.75
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '10dp'

        Label:
            text: 'Format:\\n    on_delay,off_delay,s1,s2,force\\n\\nExample:\\n    1000,1000,1,0,0\\n\\nRules:\\n    - Slider ON  = 1\\n    - Slider OFF = 0\\n    - Force Update pressed = 1\\n    - Force Update normally = 0\\n    - All values sent together in ONE line\\n    - Every message ends with newline (\\\\n)\\n    - Force button applies settings & closes popup'
            color: [0.8, 0.84, 0.96, 1]
            font_size: '13sp'
            halign: 'left'
            valign: 'top'
            text_size: self.width, None
            size_hint_y: 1
            selectable: False

        Button:
            text: 'Close'
            background_color: [0.8, 0.2, 0.2, 1]
            background_normal: ''
            color: [1, 1, 1, 1]
            bold: True
            size_hint_y: None
            height: '45dp'
            on_release: root.dismiss()

# ===== CONTROLLER SETTINGS POPUP =====
<SettingsPopup>:
    title: ''
    separator_height: 0
    background_color: [0.11, 0.14, 0.18, 1]
    size_hint: 0.95, 0.95
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '10dp'

        # Header
        Label:
            text: 'Controller Settings'
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '18sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            size_hint_y: None
            height: '30dp'
            selectable: False

        # Underline
        Widget:
            size_hint_y: None
            height: '2dp'
            canvas:
                Color:
                    rgba: [0.39, 1.0, 0.85, 1]
                Rectangle:
                    pos: self.pos
                    size: self.size

        # Form Grid
        GridLayout:
            cols: 2
            spacing: '10dp'
            row_default_height: '40dp'
            row_force_default: True
            size_hint_y: None
            height: '250dp'

            Label:
                text: 'MAC Address (Editable)'
                color: [0.7, 0.8, 0.9, 1]
                halign: 'left'
                valign: 'middle'
                text_size: self.size
                selectable: False
            CustomTextInput:
                text: app.hc05_mac
                on_text: app.hc05_mac = self.text

            Label:
                text: 'ON Delay (ms)'
                color: [0.7, 0.8, 0.9, 1]
                halign: 'left'
                valign: 'middle'
                text_size: self.size
                selectable: False
            CustomTextInput:
                text: app.on_delay
                on_text: app.on_delay = self.text

            Label:
                text: 'OFF Delay (ms)'
                color: [0.7, 0.8, 0.9, 1]
                halign: 'left'
                valign: 'middle'
                text_size: self.size
                selectable: False
            CustomTextInput:
                text: app.off_delay
                on_text: app.off_delay = self.text

            Label:
                text: 'Slider 1 Logic'
                color: [0.7, 0.8, 0.9, 1]
                halign: 'left'
                valign: 'middle'
                text_size: self.size
                selectable: False
            CustomTextInput:
                text: 'Press=1 / Release=0'
                readonly: True

            Label:
                text: 'Slider 2 Logic'
                color: [0.7, 0.8, 0.9, 1]
                halign: 'left'
                valign: 'middle'
                text_size: self.size
                selectable: False
            CustomTextInput:
                text: 'Press=1 / Release=0'
                readonly: True

        # View Data Format Button
        Button:
            text: 'View Data Format & Logic'
            background_color: [0.1, 0.2, 0.3, 1]
            background_normal: ''
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '15sp'
            size_hint_y: None
            height: '45dp'
            on_release: app.show_data_format_popup()

        # Spacer (push bottom buttons down)
        Widget:
            size_hint_y: 1

        # ===== FORCE UPDATE BUTTON (above Save & Close) =====
        ForceButton:
            text: 'Force Update Settings'
            size_hint_y: None
            height: '50dp'
            on_press: app.force_update_and_close()

        # Save & Close Button
        Button:
            text: 'Save & Close'
            background_color: [0.0, 0.78, 0.32, 1]
            background_normal: ''
            color: [0.04, 0.1, 0.18, 1]
            bold: True
            font_size: '18sp'
            size_hint_y: None
            height: '50dp'
            on_release: app.save_and_close_settings()

# ===== MAIN LAYOUT =====
BoxLayout:
    orientation: 'vertical'

    StatusLabel:
        id: status_lbl
        text: 'System Starting...'
        size_hint_y: None
        height: '60dp'
        bold: True
        font_size: '22sp'
        color: [1, 1, 1, 1]
        bg_color: [0.85, 0.53, 0.1, 1]
        on_touch_up: 
            if self.collide_point(*args[1].pos): app.reconnect_bluetooth()

    BoxLayout:
        orientation: 'vertical'

        BoxLayout:
            padding: '15dp'
            TextInput:
                id: monitor
                readonly: True
                background_normal: ''
                background_color: [0, 0, 0, 1]
                foreground_color: [0.39, 1.0, 0.85, 1]
                font_size: '13sp'
                text: 'System Ready...\\n'
                use_bubble: False
                use_handles: False

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
                    color: [0.8, 0.84, 0.96, 1]
                    selectable: False
                Switch:
                    id: s1
                    on_active: app.on_slider_change(1, self.active)
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
                    color: [0.8, 0.84, 0.96, 1]
                    selectable: False
                Switch:
                    id: s2
                    on_active: app.on_slider_change(2, self.active)
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
                    bg_color: [0.39, 1.0, 0.85, 1]
                    bold: True
                    font_size: '24sp'
                    on_release: app.open_settings()
'''

class SettingsPopup(Popup):
    pass

class DataFormatPopup(Popup):
    pass

class BluetoothApp(App):
    hc05_mac = StringProperty("98:D3:31:F4:XX:XX")
    on_delay = StringProperty("1000")
    off_delay = StringProperty("1000")
    s1_state = NumericProperty(0)
    s2_state = NumericProperty(0)
    force_state = NumericProperty(0)

    def build(self):
        self.bt_socket = None
        self.bt_out = None
        self.bt_in = None
        self.is_connected = False
        self.waiting_ack = False
        self.pending_data = ""
        self.is_connecting = False

        self.load_settings()
        self.root = Builder.load_string(KV)
        self.settings_popup = SettingsPopup()
        self.data_format_popup = DataFormatPopup()
        return self.root

    def on_start(self):
        self.log(f"Loaded MAC: {self.hc05_mac}")

        if is_real_android:
            try:
                from android.permissions import request_permissions
                request_permissions([
                    'android.permission.BLUETOOTH_CONNECT',
                    'android.permission.BLUETOOTH_SCAN',
                    'android.permission.ACCESS_FINE_LOCATION',
                    'android.permission.BLUETOOTH',
                    'android.permission.BLUETOOTH_ADMIN'
                ])
                self.update_status("Waiting for Permissions...", [0.85, 0.53, 0.1, 1])
                Clock.schedule_once(lambda dt: threading.Thread(target=self.connect_bluetooth, daemon=True).start(), 4)
            except:
                Clock.schedule_once(lambda dt: threading.Thread(target=self.connect_bluetooth, daemon=True).start(), 1)
        else:
            Clock.schedule_once(lambda dt: threading.Thread(target=self.connect_bluetooth, daemon=True).start(), 1)

    def reconnect_bluetooth(self):
        if self.is_connected:
            self.log("Already connected. Ignoring reconnect request.")
            return
        if self.is_connecting:
            self.log("Reconnect already in progress...")
            return
        
        self.is_connecting = True
        self.log("Manual reconnect requested...")
        self.update_status("Reconnecting...", [0.85, 0.53, 0.1, 1])
        
        if self.bt_socket:
            try:
                self.bt_socket.close()
            except:
                pass
            self.bt_socket = None
            self.bt_out = None
            self.bt_in = None
        
        self.is_connected = False
        self.waiting_ack = False
        
        threading.Thread(target=self.connect_bluetooth, daemon=True).start()

    def load_settings(self):
        if os.path.exists("bt_settings.json"):
            try:
                with open("bt_settings.json", "r") as f:
                    data = json.load(f)
                    if "mac" in data: self.hc05_mac = data["mac"]
                    if "on_delay" in data: self.on_delay = data["on_delay"]
                    if "off_delay" in data: self.off_delay = data["off_delay"]
            except: pass

    def save_settings_to_file(self):
        data = {
            "mac": self.hc05_mac.strip(),
            "on_delay": self.on_delay,
            "off_delay": self.off_delay,
        }
        try:
            with open("bt_settings.json", "w") as f:
                json.dump(data, f)
        except: pass

    def open_settings(self):
        self.settings_popup.open()

    def show_data_format_popup(self):
        self.data_format_popup.open()

    def save_and_close_settings(self):
        self.force_state = 0
        self.save_settings_to_file()
        self.send_full_state()
        self.settings_popup.dismiss()

    # ==================================================
    # FORCE UPDATE: Press -> Send force=1 -> Save -> Close -> Reset to 0
    # ==================================================
    def force_update_and_close(self):
        self.force_state = 1
        self.log("Force Update -> applying settings & closing popup")
        
        # Save settings first (so latest delays are stored)
        self.save_settings_to_file()
        
        # Send full state with force=1 in ONE line
        self.send_full_state()
        
        # Close popup after short delay (so user sees glow)
        Clock.schedule_once(lambda dt: self._close_popup_after_force(), 0.35)

    def _close_popup_after_force(self):
        try:
            self.settings_popup.dismiss()
        except:
            pass
        # Reset force back to 0 and send again (background)
        Clock.schedule_once(lambda dt: self._reset_force_after_close(), 0.6)

    def _reset_force_after_close(self):
        if self.force_state == 1:
            self.force_state = 0
            self.log("Force reset to 0 (post-update)")
            self.send_full_state()

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
        self.update_status("Connecting...", [0.85, 0.53, 0.1, 1])
        
        try:
            if is_real_android:
                adapter = BluetoothAdapter.getDefaultAdapter()
                device = adapter.getRemoteDevice(mac)
                spp_uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
                self.bt_socket = device.createRfcommSocketToServiceRecord(spp_uuid)
                adapter.cancelDiscovery()
                self.bt_socket.connect()
                self.bt_out = self.bt_socket.getOutputStream()
                self.bt_in = BufferedReader(InputStreamReader(self.bt_socket.getInputStream()))
                self.is_connected = True
            else:
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
        
        finally:
            self.is_connecting = False

    def listen_for_ack(self):
        while self.is_connected and self.bt_socket:
            try:
                if is_real_android:
                    if self.bt_in.ready():
                        recv_data = self.bt_in.readLine()
                        if recv_data:
                            self.log(f"RCV: {recv_data.strip()}")
                            if "OK" in recv_data.upper(): self.waiting_ack = False
                else:
                    recv_data = self.bt_socket.recv(1024).decode("utf-8").strip()
                    if recv_data:
                        self.log(f"RCV: {recv_data}")
                        if "OK" in recv_data.upper(): self.waiting_ack = False
            except:
                break

    # Format: on_delay,off_delay,s1,s2,force
    def build_state_message(self):
        return f"{self.on_delay},{self.off_delay},{int(self.s1_state)},{int(self.s2_state)},{int(self.force_state)}"

    def send_full_state(self):
        data = self.build_state_message()
        self.send_data(data)

    def send_data(self, data, is_retry=False):
        if self.is_connected and self.bt_socket:
            try:
                msg = data + "\n"
                if is_real_android:
                    java_msg = JavaString(msg).getBytes()
                    self.bt_out.write(java_msg)
                    self.bt_out.flush()
                else:
                    self.bt_socket.send(msg.encode("utf-8"))

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

    def on_slider_change(self, slider_num, is_active):
        val = 1 if is_active else 0
        if slider_num == 1:
            self.s1_state = val
        else:
            self.s2_state = val
        self.send_full_state()

if __name__ == "__main__":
    try:
        BluetoothApp().run()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
