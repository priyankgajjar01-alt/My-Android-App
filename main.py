import os
import json
import threading
import time
import socket
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
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
    height: '34dp'
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

# ===== SLIDER CELL (Aligned for 4 rows without changing Switch size) =====
<SliderCell@BoxLayout>:
    orientation: 'vertical'
    spacing: '0dp'
    slider_name: ''
    slider_id: 0
    padding: [0, 2, 0, 2]
    
    Label:
        text: root.slider_name
        color: [0.39, 1.0, 0.85, 1]
        font_size: '20sp'
        bold: True
        size_hint_y: None
        height: '26dp'
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
    size_hint: 0.92, 0.85
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '10dp'

        ScrollView:
            do_scroll_x: False
            Label:
                text: 'Multi-HC05 Data Split Logic:\\n\\n1) Only 1 MAC ON (e.g. MAC 1) - 15 Values:\\n    MAC 1 (S1-S12):\\n    on_delay,off_delay,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,force\\n    Ex: 1000,1000,1,0,0,1,0,0,1,0,0,0,0,0,0\\n\\n2) 2 MACs ON (e.g. MAC 1 & MAC 2) - 9 Values each:\\n    MAC 1 (S1-S6):\\n    on_delay,off_delay,s1,s2,s3,s4,s5,s6,force\\n    MAC 2 (S7-S12):\\n    on_delay,off_delay,s7,s8,s9,s10,s11,s12,force\\n    Ex: 1000,1000,1,0,0,1,0,0,0\\n\\n3) All 3 MACs ON (MAC 1, 2 & 3) - 7 Values each:\\n    MAC 1 (S1-S4):\\n    on_delay,off_delay,s1,s2,s3,s4,force\\n    MAC 2 (S5-S8):\\n    on_delay,off_delay,s5,s6,s7,s8,force\\n    MAC 3 (S9-S12):\\n    on_delay,off_delay,s9,s10,s11,s12,force\\n    Ex: 1000,1000,1,0,0,1,0\\n\\nRules:\\n    - MAC 1 is ON by default\\n    - App auto-connects to all enabled MACs\\n    - Slider ON = 1, OFF = 0 (S1 to S12)\\n    - Force Update pressed = 1 (for 3 seconds)\\n    - Force Update normally = 0\\n    - All values sent in ONE line per HC-05\\n    - Every message ends with newline (\\\\n)'
                color: [0.8, 0.84, 0.96, 1]
                font_size: '12sp'
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: self.texture_size[1]
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
        padding: '12dp'
        spacing: '6dp'

        Label:
            text: 'Controller Settings'
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '18sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            size_hint_y: None
            height: '26dp'
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

        ScrollView:
            do_scroll_x: False
            size_hint_y: 1

            BoxLayout:
                orientation: 'vertical'
                spacing: '6dp'
                size_hint_y: None
                height: self.minimum_height

                # --- MAC 1 ROW ---
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: '6dp'
                    size_hint_y: None
                    height: '34dp'
                    Label:
                        text: 'MAC 1'
                        color: [0.7, 0.8, 0.9, 1]
                        bold: True
                        font_size: '13sp'
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        size_hint_x: None
                        width: '48dp'
                        selectable: False
                    AnchorLayout:
                        size_hint_x: None
                        width: '72dp'
                        anchor_x: 'center'
                        anchor_y: 'center'
                        Switch:
                            size_hint: None, None
                            size: '68dp', '30dp'
                            active: app.mac1_enabled
                            on_active: app.mac1_enabled = self.active
                            canvas.before:
                                PushMatrix
                                Scale:
                                    origin: self.center
                                    x: 0.82
                                    y: 0.82
                            canvas.after:
                                PopMatrix
                    CustomTextInput:
                        text: app.mac1
                        font_size: '13sp'
                        on_text: app.mac1 = self.text

                # --- MAC 2 ROW ---
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: '6dp'
                    size_hint_y: None
                    height: '34dp'
                    Label:
                        text: 'MAC 2'
                        color: [0.7, 0.8, 0.9, 1]
                        bold: True
                        font_size: '13sp'
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        size_hint_x: None
                        width: '48dp'
                        selectable: False
                    AnchorLayout:
                        size_hint_x: None
                        width: '72dp'
                        anchor_x: 'center'
                        anchor_y: 'center'
                        Switch:
                            size_hint: None, None
                            size: '68dp', '30dp'
                            active: app.mac2_enabled
                            on_active: app.mac2_enabled = self.active
                            canvas.before:
                                PushMatrix
                                Scale:
                                    origin: self.center
                                    x: 0.82
                                    y: 0.82
                            canvas.after:
                                PopMatrix
                    CustomTextInput:
                        text: app.mac2
                        font_size: '13sp'
                        on_text: app.mac2 = self.text

                # --- MAC 3 ROW ---
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: '6dp'
                    size_hint_y: None
                    height: '34dp'
                    Label:
                        text: 'MAC 3'
                        color: [0.7, 0.8, 0.9, 1]
                        bold: True
                        font_size: '13sp'
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        size_hint_x: None
                        width: '48dp'
                        selectable: False
                    AnchorLayout:
                        size_hint_x: None
                        width: '72dp'
                        anchor_x: 'center'
                        anchor_y: 'center'
                        Switch:
                            size_hint: None, None
                            size: '68dp', '30dp'
                            active: app.mac3_enabled
                            on_active: app.mac3_enabled = self.active
                            canvas.before:
                                PushMatrix
                                Scale:
                                    origin: self.center
                                    x: 0.82
                                    y: 0.82
                            canvas.after:
                                PopMatrix
                    CustomTextInput:
                        text: app.mac3
                        font_size: '13sp'
                        on_text: app.mac3 = self.text

                # --- DELAYS ---
                GridLayout:
                    cols: 2
                    spacing: '6dp'
                    row_default_height: '34dp'
                    row_force_default: True
                    size_hint_y: None
                    height: '74dp'

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
                    text: 'Slider Names (S1 - S12)'
                    color: [0.39, 1.0, 0.85, 1]
                    bold: True
                    font_size: '14sp'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_y: None
                    height: '20dp'
                    selectable: False

                GridLayout:
                    cols: 3
                    spacing: '6dp'
                    row_default_height: '34dp'
                    row_force_default: True
                    size_hint_y: None
                    height: '154dp'

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
                    CustomTextInput:
                        hint_text: 'S10'
                        text: app.s10_name
                        on_text: app.s10_name = self.text
                    CustomTextInput:
                        hint_text: 'S11'
                        text: app.s11_name
                        on_text: app.s11_name = self.text
                    CustomTextInput:
                        hint_text: 'S12'
                        text: app.s12_name
                        on_text: app.s12_name = self.text

                Button:
                    text: 'View Data Format & Logic'
                    background_color: [0.1, 0.2, 0.3, 1]
                    background_normal: ''
                    color: [0.39, 1.0, 0.85, 1]
                    bold: True
                    font_size: '14sp'
                    size_hint_y: None
                    height: '40dp'
                    on_release: app.show_data_format_popup()

        ForceButton:
            text: 'Force Update Settings'
            size_hint_y: None
            height: '46dp'
            on_press: app.force_update_and_close()

        Button:
            text: 'Save & Close'
            background_color: [0.0, 0.78, 0.32, 1]
            background_normal: ''
            color: [0.04, 0.1, 0.18, 1]
            bold: True
            font_size: '16sp'
            size_hint_y: None
            height: '46dp'
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
        rows: 4
        spacing: '4dp'
        padding: ['10dp', '4dp', '10dp', '4dp']
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
        SliderCell:
            slider_name: app.s10_name
            slider_id: 10
        SliderCell:
            slider_name: app.s11_name
            slider_id: 11
        SliderCell:
            slider_name: app.s12_name
            slider_id: 12

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
    # 3 HC-05 MAC addresses & ON/OFF toggles (MAC 1 ON by default)
    mac1 = StringProperty("98:D3:31:F4:XX:XX")
    mac2 = StringProperty("98:D3:31:F4:XX:X2")
    mac3 = StringProperty("98:D3:31:F4:XX:X3")

    mac1_enabled = BooleanProperty(True)
    mac2_enabled = BooleanProperty(False)
    mac3_enabled = BooleanProperty(False)

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
    s10_name = StringProperty("S10")
    s11_name = StringProperty("S11")
    s12_name = StringProperty("S12")

    s1_state = NumericProperty(0)
    s2_state = NumericProperty(0)
    s3_state = NumericProperty(0)
    s4_state = NumericProperty(0)
    s5_state = NumericProperty(0)
    s6_state = NumericProperty(0)
    s7_state = NumericProperty(0)
    s8_state = NumericProperty(0)
    s9_state = NumericProperty(0)
    s10_state = NumericProperty(0)
    s11_state = NumericProperty(0)
    s12_state = NumericProperty(0)

    force_state = NumericProperty(0)

    def build(self):
        # Independent Bluetooth connection state for each HC-05 (1, 2, 3)
        self.bt_sockets = {1: None, 2: None, 3: None}
        self.bt_outs = {1: None, 2: None, 3: None}
        self.bt_ins = {1: None, 2: None, 3: None}
        self.connected_macs = {1: "", 2: "", 3: ""}
        self.is_connected = {1: False, 2: False, 3: False}
        self.waiting_ack = {1: False, 2: False, 3: False}
        self.pending_data = {1: "", 2: "", 3: ""}

        self.is_connecting = False
        self._conn_lock = threading.Lock()
        self._force_reset_event = None

        self.load_settings()
        self.root = Builder.load_string(KV)
        self.settings_popup = SettingsPopup()
        self.data_format_popup = DataFormatPopup()
        return self.root

    def on_start(self):
        active = self.get_active_macs()
        if active:
            summary = ", ".join([f"M{i}:{self.get_mac_address(i)}" for i in active])
            self.log(f"Enabled MACs -> {summary}")
        else:
            self.log("No MAC enabled in settings.")

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
                Clock.schedule_once(lambda dt: self.start_sync_thread(send_after=False), 4)
            except Exception:
                Clock.schedule_once(lambda dt: self.start_sync_thread(send_after=False), 1)
        else:
            Clock.schedule_once(lambda dt: self.start_sync_thread(send_after=False), 1)

    def on_stop(self):
        for idx in (1, 2, 3):
            self.disconnect_mac(idx, silent=True)

    # ===== HELPER METHODS =====
    def get_mac_address(self, idx):
        return getattr(self, f"mac{idx}").strip().upper()

    def is_mac_enabled(self, idx):
        return bool(getattr(self, f"mac{idx}_enabled"))

    def get_active_macs(self):
        return [i for i in (1, 2, 3) if self.is_mac_enabled(i)]

    def get_mac_switch_ranges(self):
        """
        1 MAC ON  -> 1..12 (15 values)
        2 MACs ON -> 1..6 and 7..12 (9 values each)
        3 MACs ON -> 1..4, 5..8, and 9..12 (7 values each)
        """
        active = self.get_active_macs()
        count = len(active)
        if count == 1:
            return {active[0]: (1, 12)}
        elif count == 2:
            return {active[0]: (1, 6), active[1]: (7, 12)}
        elif count == 3:
            return {active[0]: (1, 4), active[1]: (5, 8), active[2]: (9, 12)}
        return {}

    # ===== CONNECTION MANAGEMENT =====
    def reconnect_bluetooth(self):
        active = self.get_active_macs()
        if not active:
            self.log("No MAC enabled. Enable a MAC in Settings.")
            self.refresh_status_bar()
            return

        if all(self.is_connected[i] for i in active):
            self.log("All enabled MACs already connected.")
            return

        if self.is_connecting:
            self.log("Connection already in progress...")
            return

        self.log("Manual reconnect requested...")
        self.start_sync_thread(send_after=False)

    def start_sync_thread(self, send_after=False):
        threading.Thread(
            target=self.sync_connections,
            args=(send_after,),
            daemon=True
        ).start()

    def disconnect_mac(self, idx, silent=False):
        was_connected = self.is_connected[idx] or (self.bt_sockets[idx] is not None)
        self.is_connected[idx] = False
        self.waiting_ack[idx] = False
        self.pending_data[idx] = ""
        self.connected_macs[idx] = ""

        sock = self.bt_sockets[idx]
        self.bt_sockets[idx] = None
        self.bt_outs[idx] = None
        self.bt_ins[idx] = None

        if sock:
            try:
                sock.close()
            except Exception:
                pass

        if was_connected and not silent:
            self.log(f"[M{idx}] Disconnected.")

    def sync_connections(self, send_after=False):
        with self._conn_lock:
            self.is_connecting = True
            try:
                # 1. Disconnect any MAC that is disabled or whose address changed
                for idx in (1, 2, 3):
                    target_mac = self.get_mac_address(idx)
                    if not self.is_mac_enabled(idx):
                        if self.is_connected[idx] or self.bt_sockets[idx]:
                            self.disconnect_mac(idx)
                    elif self.is_connected[idx] and self.connected_macs[idx] != target_mac:
                        self.log(f"[M{idx}] MAC changed, reconnecting...")
                        self.disconnect_mac(idx)

                active = self.get_active_macs()
                if not active:
                    self.refresh_status_bar()
                    return

                # 2. Connect each enabled MAC that is not yet connected (sequentially for Android stability)
                need_connect = [i for i in active if not self.is_connected[i]]
                if need_connect:
                    self.update_status("Connecting...", [0.85, 0.53, 0.1, 1])

                for idx in need_connect:
                    self.connect_single_mac(idx)
                    if len(need_connect) > 1:
                        time.sleep(0.35)

                self.refresh_status_bar()

                # 3. Optionally send full state to active MACs after syncing
                if send_after:
                    self.send_full_state()
            finally:
                self.is_connecting = False
                self.refresh_status_bar()

    def connect_single_mac(self, idx):
        mac = self.get_mac_address(idx)
        self.log(f"[M{idx}] Connecting to {mac}...")
        self.disconnect_mac(idx, silent=True)

        try:
            if is_real_android:
                adapter = BluetoothAdapter.getDefaultAdapter()
                device = adapter.getRemoteDevice(mac)
                spp_uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
                sock = device.createRfcommSocketToServiceRecord(spp_uuid)
                adapter.cancelDiscovery()
                sock.connect()

                self.bt_sockets[idx] = sock
                self.bt_outs[idx] = sock.getOutputStream()
                self.bt_ins[idx] = BufferedReader(InputStreamReader(sock.getInputStream()))
                self.connected_macs[idx] = mac
                self.is_connected[idx] = True
            else:
                if hasattr(socket, 'AF_BLUETOOTH'):
                    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                    sock.connect((mac, 1))
                    self.bt_sockets[idx] = sock
                    self.connected_macs[idx] = mac
                    self.is_connected[idx] = True
                else:
                    self.log(f"[M{idx}] AF_BLUETOOTH missing. Simulated Mode.")

            if self.is_connected[idx]:
                threading.Thread(target=self.listen_for_ack, args=(idx,), daemon=True).start()
                self.log(f"[M{idx}] Connected Successfully!")

        except Exception as e:
            self.disconnect_mac(idx, silent=True)
            self.log(f"[M{idx}] Failed: {str(e)}")

    def listen_for_ack(self, idx):
        while self.is_connected[idx] and self.bt_sockets[idx]:
            try:
                if is_real_android:
                    bt_in = self.bt_ins[idx]
                    if bt_in and bt_in.ready():
                        recv_data = bt_in.readLine()
                        if recv_data:
                            self.log(f"[M{idx}] RCV: {recv_data.strip()}")
                            if "OK" in recv_data.upper():
                                self.waiting_ack[idx] = False
                    else:
                        time.sleep(0.05)
                else:
                    recv_data = self.bt_sockets[idx].recv(1024).decode("utf-8").strip()
                    if recv_data:
                        self.log(f"[M{idx}] RCV: {recv_data}")
                        if "OK" in recv_data.upper():
                            self.waiting_ack[idx] = False
                    else:
                        break
            except Exception:
                break

    # ===== SETTINGS LOAD / SAVE =====
    def load_settings(self):
        if os.path.exists("bt_settings.json"):
            try:
                with open("bt_settings.json", "r") as f:
                    data = json.load(f)
                    # Backward compatibility with old single-MAC config
                    if "mac1" in data:
                        self.mac1 = data["mac1"]
                    elif "mac" in data:
                        self.mac1 = data["mac"]

                    if "mac2" in data:
                        self.mac2 = data["mac2"]
                    if "mac3" in data:
                        self.mac3 = data["mac3"]

                    self.mac1_enabled = bool(data.get("mac1_enabled", True))
                    self.mac2_enabled = bool(data.get("mac2_enabled", False))
                    self.mac3_enabled = bool(data.get("mac3_enabled", False))

                    if "on_delay" in data:
                        self.on_delay = data["on_delay"]
                    if "off_delay" in data:
                        self.off_delay = data["off_delay"]

                    for i in range(1, 13):
                        key = f"s{i}_name"
                        if key in data:
                            setattr(self, key, data[key])
            except Exception:
                pass

    def save_settings_to_file(self):
        data = {
            "mac1": self.mac1.strip(),
            "mac2": self.mac2.strip(),
            "mac3": self.mac3.strip(),
            "mac1_enabled": bool(self.mac1_enabled),
            "mac2_enabled": bool(self.mac2_enabled),
            "mac3_enabled": bool(self.mac3_enabled),
            "on_delay": self.on_delay,
            "off_delay": self.off_delay,
        }
        for i in range(1, 13):
            data[f"s{i}_name"] = getattr(self, f"s{i}_name")

        try:
            with open("bt_settings.json", "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def open_settings(self):
        self.settings_popup.open()

    def show_data_format_popup(self):
        self.data_format_popup.open()

    def save_and_close_settings(self):
        if self._force_reset_event:
            self._force_reset_event.cancel()
            self._force_reset_event = None
        self.force_state = 0
        self.save_settings_to_file()
        self.settings_popup.dismiss()
        # Sync connections for enabled/disabled/edited MACs, then send state
        self.start_sync_thread(send_after=True)

    def force_update_and_close(self):
        if self._force_reset_event:
            self._force_reset_event.cancel()

        self.force_state = 1
        self.log("Force Update (1) -> waiting 3s before reset...")

        self.save_settings_to_file()
        self.start_sync_thread(send_after=True)

        # Close popup smoothly after button press
        Clock.schedule_once(lambda dt: self._close_popup_after_force(), 0.35)
        # Send force_state = 0 exactly 3 seconds after Force Update is sent
        self._force_reset_event = Clock.schedule_once(self._reset_force_after_close, 3.0)

    def _close_popup_after_force(self):
        try:
            self.settings_popup.dismiss()
        except Exception:
            pass

    def _reset_force_after_close(self, dt=0):
        self._force_reset_event = None
        if self.force_state == 1:
            self.force_state = 0
            self.log("Force reset to 0 (after 3s delay)")
            self.send_full_state()

    # ===== UI UPDATES =====
    @mainthread
    def log(self, msg):
        monitor = self.root.ids.monitor
        monitor.text += msg + "\n"
        monitor.cursor = (0, len(monitor.text))

    @mainthread
    def update_status(self, text, bg_color):
        self.root.ids.status_lbl.text = text
        self.root.ids.status_lbl.bg_color = bg_color

    @mainthread
    def refresh_status_bar(self):
        active = self.get_active_macs()
        if not active:
            self.update_status("No MAC Enabled", [0.82, 0.18, 0.18, 1])
            return

        connected = [i for i in active if self.is_connected[i]]
        if len(connected) == len(active):
            names = ", ".join([f"M{i}" for i in connected])
            self.update_status(f"Connected: {names}", [0.0, 0.78, 0.32, 1])
        elif len(connected) > 0:
            ok_names = ",".join([f"M{i}" for i in connected])
            self.update_status(f"Partial ({len(connected)}/{len(active)}): {ok_names}", [0.85, 0.53, 0.1, 1])
        else:
            self.update_status("Disconnected", [0.82, 0.18, 0.18, 1])

    # ===== DATA BUILDING & SENDING =====
    def build_message_for_mac(self, idx):
        ranges = self.get_mac_switch_ranges()
        if idx not in ranges:
            return None
        start_s, end_s = ranges[idx]
        parts = [self.on_delay.strip(), self.off_delay.strip()]
        for i in range(start_s, end_s + 1):
            parts.append(str(int(getattr(self, f"s{i}_state"))))
        parts.append(str(int(self.force_state)))
        return ",".join(parts)

    def send_full_state(self):
        ranges = self.get_mac_switch_ranges()
        if not ranges:
            self.log("No MAC enabled! Cannot send data.")
            return
        for idx in ranges:
            data = self.build_message_for_mac(idx)
            if data:
                self.send_data(idx, data)

    def send_data(self, idx, data, is_retry=False):
        if self.is_connected[idx] and self.bt_sockets[idx]:
            try:
                msg = data + "\n"
                if is_real_android:
                    java_msg = JavaString(msg).getBytes()
                    self.bt_outs[idx].write(java_msg)
                    self.bt_outs[idx].flush()
                else:
                    self.bt_sockets[idx].send(msg.encode("utf-8"))

                self.log(f"[M{idx}] RE-SENT: {data}" if is_retry else f"[M{idx}] SENT: {data}")
                self.waiting_ack[idx] = True
                self.pending_data[idx] = data
                Clock.schedule_once(lambda dt, i=idx, d=data, r=is_retry: self.check_ack(i, d, r), 3)
            except Exception:
                self.disconnect_mac(idx, silent=True)
                self.log(f"[M{idx}] Send failed -> Disconnected")
                self.refresh_status_bar()
        else:
            self.log(f"[M{idx}] Simulated SENT: {data}")

    def check_ack(self, idx, data, is_retry):
        if self.is_connected[idx] and self.waiting_ack[idx] and self.pending_data[idx] == data:
            if not is_retry:
                self.log(f"[M{idx}] No message! Retrying...")
                self.send_data(idx, data, is_retry=True)
            else:
                self.log(f"[M{idx}] Controller Not Responding")
                self.waiting_ack[idx] = False

    def on_slider_change(self, slider_id, is_active):
        val = 1 if is_active else 0
        if 1 <= slider_id <= 12:
            setattr(self, f"s{slider_id}_state", val)

        # If Force Update 3s timer is active, wait for the 3s timer to finish before sending
        if self._force_reset_event is not None:
            return

        # Send only to the MAC responsible for this switch
        ranges = self.get_mac_switch_ranges()
        if not ranges:
            self.log("No MAC enabled! Enable at least 1 MAC in Settings.")
            return

        for idx, (start_s, end_s) in ranges.items():
            if start_s <= slider_id <= end_s:
                data = self.build_message_for_mac(idx)
                if data:
                    self.send_data(idx, data)
                break


if __name__ == "__main__":
    try:
        BluetoothApp().run()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
