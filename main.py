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
    font_size: '14sp'
    size_hint_y: None
    height: '36dp'
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
    font_size: '15sp'
    color: [0.04, 0.1, 0.18, 1] if self.state == 'down' else [0.39, 1.0, 0.85, 1]
    canvas.before:
        Color:
            rgba: [0.39, 1.0, 0.85, 0.35] if self.state == 'down' else [0, 0, 0, 0]
        RoundedRectangle:
            pos: self.x - 4, self.y - 4
            size: self.width + 8, self.height + 8
            radius: [28, 28, 28, 28]
        Color:
            rgba: [0.39, 1.0, 0.85, 1] if self.state == 'down' else [0.1, 0.2, 0.3, 1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [25, 25, 25, 25]
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

# ===== SLIDER CELL (UPDATED: Name bigger, Switch close to name) =====
<SliderCell@BoxLayout>:
    orientation: 'vertical'
    spacing: '0dp'
    slider_name: ''
    slider_id: 0
    padding: [0, 4, 0, 4]
    
    Label:
        text: root.slider_name
        color: [0.39, 1.0, 0.85, 1]
        font_size: '24sp'
        bold: True
        size_hint_y: None
        height: '34dp'
        halign: 'center'
        valign: 'middle'
        text_size: self.size
        selectable: False
    
    AnchorLayout:
        anchor_x: 'center'
        anchor_y: 'top'
        Switch:
            size_hint: None, None
            size: '45dp', '30dp'
            on_active: app.on_slider_change(root.slider_id, self.active)
            canvas.before:
                PushMatrix
                Scale:
                    origin: self.center
                    x: 1.5
                    y: 1.5
            canvas.after:
                PopMatrix

# ===== DATA FORMAT POPUP =====
<DataFormatPopup>:
    title: 'Data Format & Logic'
    title_color: [0.39, 1.0, 0.85, 1]
    title_size: '18sp'
    separator_color: [0.39, 1.0, 0.85, 1]
    background_color: [0.11, 0.14, 0.18, 1]
    size_hint: 0.9, 0.8
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '10dp'

        Label:
            text: 'Format:\\n    on_delay,off_delay,s1,s2,s3,s4,s5,s6,s7,s8,s9,force\\n\\nExample:\\n    1000,1000,1,0,0,1,0,0,1,0,0,0\\n\\nRules:\\n    - Slider ON  = 1, OFF = 0 (S1 to S9)\\n    - Force Update pressed = 1 (during press)\\n    - Force Update normally = 0\\n    - All values sent in ONE line\\n    - Every message ends with newline (\\\\n)'
            color: [0.8, 0.84, 0.96, 1]
            font_size: '12sp'
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
        spacing: '8dp'

        Label:
            text: 'Controller Settings'
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '18sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            size_hint_y: None
            height: '28dp'
            selectable: False

        Widget:
            size_hint_y: None
            height: '2dp'
            canvas:
                Color:
                    rgba: [0.39, 1.0, 0.85, 1]
                Rectangle:
                    pos: self.pos
                    size: self.size

        GridLayout:
            cols: 2
            spacing: '8dp'
            row_default_height: '36dp'
            row_force_default: True
            size_hint_y: None
            height: '124dp'

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
            text: 'Slider Names (S1 - S9)'
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '14sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            size_hint_y: None
            height: '22dp'
            selectable: False

        GridLayout:
            cols: 3
            spacing: '6dp'
            row_default_height: '36dp'
            row_force_default: True
            size_hint_y: None
            height: '120dp'

            CustomTextInput:
                hint_text: 'S1'
                text: app.s1_name
                on_text: app.s1_name = self.text
            CustomTextInput:
                hint_text: 'S2'
                text: app.s2_name
                on_text: app.s2_name = self.text
            CustomTextInput:
                hint_text: 'S3'
                text: app.s3_name
                on_text: app.s3_name = self.text
            CustomTextInput:
                hint_text: 'S4'
                text: app.s4_name
                on_text: app.s4_name = self.text
            CustomTextInput:
                hint_text: 'S5'
                text: app.s5_name
                on_text: app.s5_name = self.text
            CustomTextInput:
                hint_text: 'S6'
                text: app.s6_name
                on_text: app.s6_name = self.text
            CustomTextInput:
                hint_text: 'S7'
                text: app.s7_name
                on_text: app.s7_name = self.text
            CustomTextInput:
                hint_text: 'S8'
                text: app.s8_name
                on_text: app.s8_name = self.text
            CustomTextInput:
                hint_text: 'S9'
                text: app.s9_name
                on_text: app.s9_name = self.text

        Button:
            text: 'View Data Format & Logic'
            background_color: [0.1, 0.2, 0.3, 1]
            background_normal: ''
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '14sp'
            size_hint_y: None
            height: '42dp'
            on_release: app.show_data_format_popup()

        Widget:
            size_hint_y: 1

        ForceButton:
            text: 'Force Update Settings'
            size_hint_y: None
            height: '48dp'
            on_press: app.force_update_and_close()

        Button:
            text: 'Save & Close'
            background_color: [0.0, 0.78, 0.32, 1]
            background_normal: ''
            color: [0.04, 0.1, 0.18, 1]
            bold: True
            font_size: '16sp'
            size_hint_y: None
            height: '48dp'
            on_release: app.save_and_close_settings()

# ===== MAIN LAYOUT =====
BoxLayout:
    orientation: 'vertical'

    StatusLabel:
        id: status_lbl
        text: 'System Starting...'
        size_hint_y: None
        height: '55dp'
        bold: True
        font_size: '20sp'
        color: [1, 1, 1, 1]
        bg_color: [0.85, 0.53, 0.1, 1]
        on_touch_up: 
            if self.collide_point(*args[1].pos): app.reconnect_bluetooth()

    BoxLayout:
        size_hint_y: 0.3
        padding: '10dp'
        TextInput:
            id: monitor
            readonly: True
            background_normal: ''
            background_color: [0, 0, 0, 1]
            foreground_color: [0.39, 1.0, 0.85, 1]
            font_size: '12sp'
            text: 'System Ready...\\n'
            use_bubble: False
            use_handles: False

    GridLayout:
        cols: 3
        rows: 3
        spacing: '6dp'
        padding: '10dp'
        size_hint_y: 0.7

        SliderCell:
            slider_name: app.s1_name
            slider_id: 1
        SliderCell:
            slider_name: app.s2_name
            slider_id: 2
        SliderCell:
            slider_name: app.s3_name
            slider_id: 3
        SliderCell:
            slider_name: app.s4_name
            slider_id: 4
        SliderCell:
            slider_name: app.s5_name
            slider_id: 5
        SliderCell:
            slider_name: app.s6_name
            slider_id: 6
        SliderCell:
            slider_name: app.s7_name
            slider_id: 7
        SliderCell:
            slider_name: app.s8_name
            slider_id: 8
        SliderCell:
            slider_name: app.s9_name
            slider_id: 9

    AnchorLayout:
        size_hint_y: None
        height: '50dp'
        anchor_x: 'center'
        anchor_y: 'center'
        RoundedButton:
            text: 'Settings'
            size_hint: None, None
            size: '140dp', '40dp'
            bg_color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '16sp'
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
    
    s1_name = StringProperty("S1")
    s2_name = StringProperty("S2")
    s3_name = StringProperty("S3")
    s4_name = StringProperty("S4")
    s5_name = StringProperty("S5")
    s6_name = StringProperty("S6")
    s7_name = StringProperty("S7")
    s8_name = StringProperty("S8")
    s9_name = StringProperty("S9")
    
    s1_state = NumericProperty(0)
    s2_state = NumericProperty(0)
    s3_state = NumericProperty(0)
    s4_state = NumericProperty(0)
    s5_state = NumericProperty(0)
    s6_state = NumericProperty(0)
    s7_state = NumericProperty(0)
    s8_state = NumericProperty(0)
    s9_state = NumericProperty(0)
    
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
                    for i in range(1, 10):
                        key = f"s{i}_name"
                        if key in data:
                            setattr(self, key, data[key])
            except: pass

    def save_settings_to_file(self):
        data = {
            "mac": self.hc05_mac.strip(),
            "on_delay": self.on_delay,
            "off_delay": self.off_delay,
        }
        for i in range(1, 10):
            data[f"s{i}_name"] = getattr(self, f"s{i}_name")
        
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

    def force_update_and_close(self):
        self.force_state = 1
        self.log("Force Update -> applying settings & closing popup")
        
        self.save_settings_to_file()
        self.send_full_state()
        
        Clock.schedule_once(lambda dt: self._close_popup_after_force(), 0.35)

    def _close_popup_after_force(self):
        try:
            self.settings_popup.dismiss()
        except:
            pass
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

    def build_state_message(self):
        parts = [self.on_delay, self.off_delay]
        for i in range(1, 10):
            parts.append(str(int(getattr(self, f"s{i}_state"))))
        parts.append(str(int(self.force_state)))
        return ",".join(parts)

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

    def on_slider_change(self, slider_id, is_active):
        val = 1 if is_active else 0
        if 1 <= slider_id <= 9:
            setattr(self, f"s{slider_id}_state", val)
        self.send_full_state()

if __name__ == "__main__":
    try:
        BluetoothApp().run()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
