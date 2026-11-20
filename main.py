import os
import re
import json
import time
import math
import copy
import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp
from kivy.utils import platform, escape_markup
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider

# Detect compiled Android APK vs Pydroid 3 / Desktop environment
IS_ANDROID_APK = False
if platform == 'android':
    try:
        import jnius
        import android
        IS_ANDROID_APK = True
    except Exception:
        IS_ANDROID_APK = False

Window.softinput_mode = 'below_target'
# Subtle dark-navy base background
Window.clearcolor = (0.04, 0.08, 0.16, 1)

# Color Palette (Light Navy Blue Translucent / Glass Theme)
CARD_BG = (0.12, 0.24, 0.44, 0.30)
CARD_BG_ACTIVE = (0.10, 0.36, 0.30, 0.48)
CARD_BORDER = (0.35, 0.60, 0.95, 0.38)
CARD_BORDER_ACTIVE = (0.30, 0.90, 0.60, 0.72)
INPUT_BG = (0.08, 0.16, 0.30, 0.55)
BTN_PRIMARY = (0.16, 0.42, 0.78, 0.85)
BTN_SUCCESS = (0.12, 0.55, 0.38, 0.88)
BTN_WARN = (0.72, 0.45, 0.12, 0.85)
BTN_DANGER = (0.68, 0.20, 0.24, 0.85)
TEXT_MAIN = (0.94, 0.97, 1.0, 1)
TEXT_MUTED = (0.62, 0.74, 0.90, 1)
TEXT_CYAN = (0.40, 0.86, 1.0, 1)

# Data source options for the 6-Box Packet Builder
BOX_OPTIONS = (
    "PIN",
    "X",
    "Y",
    "VAL",
    "CUSTOM1",
    "CUSTOM2",
    "CMD",
    "OFF",
)

DEFAULT_BOXES = [
    {"source": "PIN", "default": "0"},      # Box 1: Pin Number
    {"source": "X", "default": "0"},        # Box 2: Joystick X Value
    {"source": "Y", "default": "0"},        # Box 3: Joystick Y Value
    {"source": "VAL", "default": "0"},      # Box 4: Main Control Value
    {"source": "CUSTOM1", "default": "0"},  # Box 5: Custom Field 1
    {"source": "CUSTOM2", "default": "0"},  # Box 6: Custom Field 2
]

# Default ready-to-use project profiles
DEFAULT_PROFILES = {
    "Home Automation": [
        {
            "id": "w1", "type": "Switch", "name": "Main Light",
            "pin": "13", "mode": "1", "cmd": "D",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "255",
            "custom1": "", "custom2": "", "unit": ""
        },
        {
            "id": "w2", "type": "Slider", "name": "Fan Speed (PWM)",
            "pin": "9", "mode": "2", "cmd": "A",
            "val_on": "255", "val_off": "0", "min_val": "0", "max_val": "255",
            "custom1": "", "custom2": "", "unit": ""
        },
        {
            "id": "w3", "type": "Push Button", "name": "Door Bell",
            "pin": "7", "mode": "1", "cmd": "D",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "1",
            "custom1": "", "custom2": "", "unit": ""
        },
        {
            "id": "w4", "type": "Sensor Display", "name": "Room Temp",
            "pin": "0", "mode": "0", "cmd": "R",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "100",
            "custom1": "", "custom2": "", "unit": "C"
        },
    ],
    "RC Car": [
        {
            "id": "rc1", "type": "Joystick", "name": "Drive Joystick",
            "pin": "5", "mode": "2", "cmd": "A",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "255",
            "custom1": "", "custom2": "", "unit": ""
        },
        {
            "id": "rc2", "type": "Switch", "name": "Headlights",
            "pin": "12", "mode": "1", "cmd": "D",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "1",
            "custom1": "", "custom2": "", "unit": ""
        },
        {
            "id": "rc3", "type": "Push Button", "name": "Horn",
            "pin": "8", "mode": "1", "cmd": "D",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "1",
            "custom1": "", "custom2": "", "unit": ""
        },
        {
            "id": "rc4", "type": "Sensor Display", "name": "Obstacle Dist",
            "pin": "1", "mode": "0", "cmd": "R",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "400",
            "custom1": "", "custom2": "", "unit": "cm"
        },
    ]
}


def safe_int(val, default=0):
    """Safely convert a value to an integer with a fallback default."""
    try:
        return int(str(val).strip())
    except Exception:
        return default


# ==========================================
# Custom Glass / Translucent UI Components
# ==========================================
class GlassBox(BoxLayout):
    """Rounded translucent container with a subtle glowing border."""
    def __init__(self, bg_color=CARD_BG, border_color=CARD_BORDER, radius=14, **kwargs):
        super().__init__(**kwargs)
        self._bg_color = bg_color
        self._border_color = border_color
        self._radius = [dp(radius)]
        with self.canvas.before:
            self._c_bg = Color(*self._bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self._radius)
            self._c_bd = Color(*self._border_color)
            self._border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(radius)),
                width=1.1
            )
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def set_colors(self, bg_color, border_color):
        self._c_bg.rgba = bg_color
        self._c_bd.rgba = border_color

    def _update_canvas(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size
        r = self._radius[0]
        if self.width > 0 and self.height > 0:
            self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, r)


class ClickableGlassBox(ButtonBehavior, GlassBox):
    """GlassBox with touch/click behavior."""
    pass


class GlassButton(ButtonBehavior, GlassBox):
    """Styled translucent button with centered label."""
    def __init__(self, text='', font_size=13, bold=True, bg_color=BTN_PRIMARY,
                 border_color=(0.45, 0.72, 1.0, 0.45), radius=12, **kwargs):
        super().__init__(bg_color=bg_color, border_color=border_color, radius=radius, **kwargs)
        self.lbl = Label(
            text=text,
            font_size=dp(font_size),
            bold=bold,
            color=TEXT_MAIN,
            halign='center',
            valign='middle',
            shorten=True
        )
        self.lbl.bind(size=self.lbl.setter('text_size'))
        self.add_widget(self.lbl)

    def set_text(self, text):
        self.lbl.text = text


class StyledInput(TextInput):
    """Styled TextInput with text selection, selection handles, and copy/paste completely disabled."""
    def __init__(self, hint='', multiline=False, input_filter=None, **kwargs):
        super().__init__(
            hint_text=hint,
            multiline=multiline,
            input_filter=input_filter,
            use_bubble=False,
            use_handles=False,
            allow_copy=False,
            background_normal='',
            background_active='',
            background_color=INPUT_BG,
            foreground_color=TEXT_MAIN,
            hint_text_color=(0.50, 0.62, 0.80, 0.8),
            cursor_color=(0.45, 0.80, 1.0, 1),
            selection_color=(0, 0, 0, 0),
            padding=[dp(10), dp(10)],
            font_size=dp(14),
            size_hint_y=None,
            height=dp(44),
            **kwargs
        )

    def select_text(self, start, end):
        pass

    def select_all(self):
        pass

    def copy(self, data=''):
        pass

    def cut(self):
        pass

    def paste(self):
        pass

    def on_double_tap(self):
        pass

    def on_triple_tap(self):
        pass

    def _show_cut_copy_paste(self, *args, **kwargs):
        pass


class JoystickPad(Widget):
    """Interactive 2D Touch Joystick that emits X and Y together in a single packet."""
    def __init__(self, min_val=0, max_val=255, on_move=None, **kwargs):
        super().__init__(**kwargs)
        self.min_val = int(min_val)
        self.max_val = int(max_val)
        self.center_val = int((self.min_val + self.max_val) / 2)
        self.on_move = on_move
        self._norm_x = 0.0
        self._norm_y = 0.0
        self._last_sent = 0.0
        self.bind(pos=self._schedule_redraw, size=self._schedule_redraw)
        Clock.schedule_once(self._redraw, 0)

    def _schedule_redraw(self, *args):
        Clock.unschedule(self._redraw)
        Clock.schedule_once(self._redraw, 0)

    def _get_geometry(self):
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        radius = min(self.width, self.height) * 0.44
        knob_r = max(dp(18), radius * 0.30)
        return cx, cy, radius, knob_r

    def _redraw(self, *args):
        self.canvas.clear()
        cx, cy, r, kr = self._get_geometry()
        if r <= 2:
            return
        kx = cx + self._norm_x * (r - kr * 0.6)
        ky = cy + self._norm_y * (r - kr * 0.6)

        with self.canvas:
            # Outer boundary circle
            Color(0.08, 0.18, 0.36, 0.55)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(0.35, 0.65, 1.0, 0.50)
            Line(circle=(cx, cy, r), width=1.4)

            # Center crosshair
            Color(0.35, 0.65, 1.0, 0.25)
            Line(points=[cx - r * 0.85, cy, cx + r * 0.85, cy], width=1.0)
            Line(points=[cx, cy - r * 0.85, cx, cy + r * 0.85], width=1.0)

            # Guide vector from center to thumb knob
            Color(0.35, 0.85, 1.0, 0.55)
            Line(points=[cx, cy, kx, ky], width=1.6)

            # Thumb knob
            Color(0.22, 0.62, 1.0, 0.90)
            Ellipse(pos=(kx - kr, ky - kr), size=(kr * 2, kr * 2))
            Color(0.75, 0.92, 1.0, 0.85)
            Line(circle=(kx, ky, kr), width=1.3)

    def _map_val(self, norm):
        ratio = (norm + 1.0) / 2.0
        return int(round(self.min_val + ratio * (self.max_val - self.min_val)))

    def _update_from_touch(self, tx, ty, force_emit=False):
        cx, cy, r, kr = self._get_geometry()
        max_dist = max(1.0, r - kr * 0.6)
        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy)
        if dist > max_dist:
            dx = dx * max_dist / dist
            dy = dy * max_dist / dist

        self._norm_x = dx / max_dist
        self._norm_y = dy / max_dist
        self._redraw()

        now = time.time()
        # Rate-limit transmissions to avoid flooding the HC-05 serial buffer
        if self.on_move and (force_emit or (now - self._last_sent) >= 0.08):
            self._last_sent = now
            self.on_move(self._map_val(self._norm_x), self._map_val(self._norm_y), True)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._update_from_touch(touch.x, touch.y, force_emit=True)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._update_from_touch(touch.x, touch.y, force_emit=False)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._norm_x = 0.0
            self._norm_y = 0.0
            self._redraw()
            if self.on_move:
                self.on_move(self.center_val, self.center_val, False)
            return True
        return super().on_touch_up(touch)


# ==========================================
# HC-05 Bluetooth Manager (Android APK + Preview Mode)
# ==========================================
class HC05Manager:
    SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

    def __init__(self, on_status, on_log, on_rx_data=None):
        self.on_status = on_status
        self.on_log = on_log
        self.on_rx_data = on_rx_data
        self.socket = None
        self.in_stream = None
        self.out_stream = None
        self.connected = False
        self.connecting = False
        self.mac_address = ""
        self.auto_connect = True
        self.line_ending = "\n"
        self._stop_flag = False
        self._lock = threading.Lock()
        self._br = None

        if IS_ANDROID_APK:
            self._request_android_permissions()
        else:
            self._emit_log("SYS", "Preview Mode active (Tap BT to connect in Demo mode).")

        # Start background auto-connect thread
        threading.Thread(target=self._auto_connect_loop, daemon=True).start()

    def _request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            perms = [
                Permission.BLUETOOTH,
                Permission.BLUETOOTH_ADMIN,
                Permission.ACCESS_FINE_LOCATION,
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.BLUETOOTH_SCAN",
            ]
            request_permissions(perms)
        except Exception as e:
            self._emit_log("SYS", f"Permission request error: {e}")

    def _emit_status(self, is_connected, msg):
        Clock.schedule_once(lambda dt: self.on_status(is_connected, msg))

    def _emit_log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        Clock.schedule_once(lambda dt: self.on_log(ts, tag, msg))

    def set_config(self, mac_address, auto_connect):
        self.mac_address = mac_address.strip().upper()
        self.auto_connect = auto_connect

    def set_line_ending(self, ending_key):
        if ending_key == "CRLF (\\r\\n)":
            self.line_ending = "\r\n"
        elif ending_key == "None":
            self.line_ending = ""
        else:
            self.line_ending = "\n"

    def get_paired_devices(self):
        if not IS_ANDROID_APK:
            return [
                ("HC-05 Controller (Demo)", "00:21:13:00:AB:CD"),
                ("HC-05 RC Car (Demo)", "98:D3:31:F5:12:44")
            ]
        devices_list = []
        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter and adapter.isEnabled():
                bonded = adapter.getBondedDevices().toArray()
                for dev in bonded:
                    devices_list.append((dev.getName() or "Unknown", dev.getAddress()))
            else:
                self._emit_log("SYS", "Bluetooth is OFF. Please turn ON Bluetooth.")
        except Exception as e:
            self._emit_log("SYS", f"Paired device error: {e}")
        return devices_list

    def start_nearby_scan(self, on_device_found):
        if not IS_ANDROID_APK:
            on_device_found("HC-05 Nearby (Demo)", "98:D3:32:10:88:99")
            self._emit_log("SYS", "Demo scan complete.")
            return
        try:
            from jnius import autoclass
            from android.broadcast import BroadcastReceiver
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self._emit_log("SYS", "Scan failed: Please turn ON Bluetooth.")
                return

            if self._br:
                try:
                    self._br.stop()
                except Exception:
                    pass

            def on_receive(context, intent):
                try:
                    if intent.getAction() == BluetoothDevice.ACTION_FOUND:
                        dev = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
                        if dev:
                            name = dev.getName() or "HC-05 / BT Device"
                            addr = dev.getAddress()
                            Clock.schedule_once(lambda dt, n=name, a=addr: on_device_found(n, a))
                except Exception:
                    pass

            self._br = BroadcastReceiver(on_receive, actions=[BluetoothDevice.ACTION_FOUND])
            self._br.start()
            if adapter.isDiscovering():
                adapter.cancelDiscovery()
            adapter.startDiscovery()
            self._emit_log("SYS", "Nearby HC-05 scanning started...")
        except Exception as e:
            self._emit_log("SYS", f"Nearby scan unavailable ({e}); please use the Paired list.")

    def connect(self, mac=None):
        if mac:
            self.mac_address = mac.strip().upper()
        if not self.mac_address:
            self._emit_log("SYS", "MAC Address is empty. Select a device in the Connection screen.")
            return
        if self.connecting or self.connected:
            return
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        with self._lock:
            if self.connected or self.connecting:
                return
            self.connecting = True

        self._emit_status(False, "Connecting...")
        self._emit_log("SYS", f"Connecting to {self.mac_address}...")

        if not IS_ANDROID_APK:
            time.sleep(0.3)
            self.connected = True
            self.connecting = False
            self._emit_status(True, f"Demo ({self.mac_address[-5:]})")
            self._emit_log("SYS", "Demo mode connected.")
            return

        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            UUID = autoclass('java.util.UUID')

            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                raise Exception("Bluetooth is OFF")

            if adapter.isDiscovering():
                adapter.cancelDiscovery()

            device = adapter.getRemoteDevice(self.mac_address)
            sock = device.createRfcommSocketToServiceRecord(UUID.fromString(self.SPP_UUID))
            sock.connect()

            self.socket = sock
            self.in_stream = sock.getInputStream()
            self.out_stream = sock.getOutputStream()
            self.connected = True
            self.connecting = False

            self._emit_status(True, f"Connected ({self.mac_address[-5:]})")
            self._emit_log("SYS", f"HC-05 Connected: {self.mac_address}")

            threading.Thread(target=self._read_loop, daemon=True).start()

        except Exception as e:
            self.connected = False
            self.connecting = False
            self._close_socket()
            self._emit_status(False, "Disconnected")
            self._emit_log("SYS", f"Connection failed: {e}")

    def _read_loop(self):
        buffer = bytearray()
        while self.connected and not self._stop_flag:
            try:
                avail = self.in_stream.available()
                if avail > 0:
                    for _ in range(avail):
                        b = self.in_stream.read()
                        if b == -1:
                            raise Exception("Stream closed")
                        if b == 10:  # Newline '\n'
                            line = buffer.decode('utf-8', errors='replace').strip()
                            buffer.clear()
                            if line:
                                self._emit_log("RX", line)
                                if self.on_rx_data:
                                    Clock.schedule_once(lambda dt, ln=line: self.on_rx_data(ln))
                        elif b != 13:  # Ignore carriage return '\r'
                            buffer.append(b)
                else:
                    time.sleep(0.04)
            except Exception as e:
                self._emit_log("SYS", f"Connection lost: {e}")
                self.disconnect(silent=True)
                break

    def send(self, command_str):
        cmd = str(command_str).strip()
        if not cmd:
            return False
        if not self.connected:
            self._emit_log("SYS", f"Not Connected! Packet: {cmd}")
            return False

        if not IS_ANDROID_APK:
            self._emit_log("TX", cmd)
            return True

        try:
            payload = (cmd + self.line_ending).encode('utf-8')
            self.out_stream.write(payload)
            self.out_stream.flush()
            self._emit_log("TX", cmd)
            return True
        except Exception as e:
            self._emit_log("SYS", f"TX Error: {e}")
            self.disconnect(silent=True)
            return False

    def disconnect(self, silent=False):
        self.connected = False
        self.connecting = False
        self._close_socket()
        self._emit_status(False, "Disconnected")
        if not silent:
            self._emit_log("SYS", "Disconnected.")

    def _close_socket(self):
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        self.socket = None
        self.in_stream = None
        self.out_stream = None

    def _auto_connect_loop(self):
        time.sleep(2)
        while not self._stop_flag:
            if self.auto_connect and self.mac_address and not self.connected and not self.connecting:
                self._connect_worker()
            time.sleep(4)

    def shutdown(self):
        self._stop_flag = True
        if self._br:
            try:
                self._br.stop()
            except Exception:
                pass
        self.disconnect(silent=True)


# ==========================================
# Screen 1: Dynamic Custom Dashboard
# ==========================================
class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.edit_mode = False
        self.sensor_labels = {}
        self.switch_states = {}

        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        # --- Top App Bar ---
        top_bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))

        bt_badge = ClickableGlassBox(
            orientation='vertical',
            padding=[dp(10), dp(4)],
            bg_color=(0.08, 0.18, 0.34, 0.55),
            border_color=CARD_BORDER,
            radius=12
        )
        bt_badge.bind(on_release=lambda x: self.go_to('connection'))

        self.title_lbl = Label(
            text="Pro HC-05 Controller",
            font_size=dp(14),
            bold=True,
            color=TEXT_MAIN,
            halign='left',
            valign='bottom',
            shorten=True
        )
        self.title_lbl.bind(size=self.title_lbl.setter('text_size'))

        self.status_lbl = Label(
            text="OFF: Disconnected",
            font_size=dp(11),
            color=(1.0, 0.45, 0.45, 1),
            halign='left',
            valign='top',
            shorten=True
        )
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))
        bt_badge.add_widget(self.title_lbl)
        bt_badge.add_widget(self.status_lbl)

        btn_bt = GlassButton(text="BT", font_size=12, bg_color=(0.12, 0.32, 0.58, 0.65),
                             size_hint_x=None, width=dp(46))
        btn_bt.bind(on_release=lambda x: self.go_to('connection'))

        btn_fmt = GlassButton(text="Format", font_size=12, bg_color=(0.12, 0.32, 0.58, 0.65),
                              size_hint_x=None, width=dp(62))
        btn_fmt.bind(on_release=lambda x: self.go_to('protocol'))

        btn_term = GlassButton(text="Log", font_size=12, bg_color=(0.12, 0.32, 0.58, 0.65),
                               size_hint_x=None, width=dp(48))
        btn_term.bind(on_release=lambda x: self.go_to('terminal'))

        top_bar.add_widget(bt_badge)
        top_bar.add_widget(btn_bt)
        top_bar.add_widget(btn_fmt)
        top_bar.add_widget(btn_term)
        root.add_widget(top_bar)

        # --- Profile Selector Row ---
        prof_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.sp_profile = Spinner(
            text='Home Automation',
            values=('Home Automation', 'RC Car'),
            background_normal='',
            background_color=(0.12, 0.28, 0.52, 0.65),
            color=TEXT_MAIN,
            font_size=dp(13),
            bold=True
        )
        self.sp_profile.bind(text=self.on_profile_selected)

        btn_prof_mgr = GlassButton(
            text="Profiles",
            font_size=12,
            bg_color=CARD_BG,
            size_hint_x=None,
            width=dp(76)
        )
        btn_prof_mgr.bind(on_release=lambda x: self.go_to('profiles'))

        prof_row.add_widget(self.sp_profile)
        prof_row.add_widget(btn_prof_mgr)
        root.add_widget(prof_row)

        # --- Action Toolbar ---
        tool_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        btn_add = GlassButton(text="+ Add Widget", font_size=12, bg_color=BTN_SUCCESS)
        btn_add.bind(on_release=self.add_new_widget)

        btn_sync = GlassButton(text="Sync Modes (M)", font_size=12, bg_color=BTN_PRIMARY)
        btn_sync.bind(on_release=self.sync_all_pin_modes)

        self.btn_edit = GlassButton(text="Edit UI", font_size=12, bg_color=CARD_BG,
                                    size_hint_x=None, width=dp(72))
        self.btn_edit.bind(on_release=self.toggle_edit_mode)

        tool_row.add_widget(btn_add)
        tool_row.add_widget(btn_sync)
        tool_row.add_widget(self.btn_edit)
        root.add_widget(tool_row)

        # --- Scrollable Dynamic Widgets Container (Vertical Scroll Only) ---
        scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        self.widget_container = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint_y=None,
            padding=[0, dp(4), 0, dp(16)]
        )
        self.widget_container.bind(minimum_height=self.widget_container.setter('height'))
        scroll.add_widget(self.widget_container)
        root.add_widget(scroll)

        # --- Mini Live Terminal Strip ---
        mini_term = GlassButton(
            text="Terminal: Ready...",
            font_size=11,
            bold=False,
            bg_color=(0.03, 0.07, 0.14, 0.80),
            border_color=CARD_BORDER,
            radius=10,
            size_hint_y=None,
            height=dp(36)
        )
        mini_term.lbl.halign = 'left'
        mini_term.padding = [dp(10), 0]
        mini_term.bind(on_release=lambda x: self.go_to('terminal'))
        self.mini_log_btn = mini_term
        root.add_widget(mini_term)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh_profile_spinner()
        self.rebuild_dashboard()

    def refresh_profile_spinner(self):
        app = App.get_running_app()
        names = list(app.profiles.keys())
        self.sp_profile.values = names
        if app.active_profile in names:
            self.sp_profile.text = app.active_profile
        elif names:
            app.active_profile = names[0]
            self.sp_profile.text = names[0]

    def on_profile_selected(self, spinner, text):
        app = App.get_running_app()
        if text in app.profiles and text != app.active_profile:
            app.active_profile = text
            app.save_state()
            self.rebuild_dashboard()

    def toggle_edit_mode(self, *args):
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.btn_edit.set_text("Done")
            self.btn_edit.set_colors(BTN_WARN, (1.0, 0.72, 0.30, 0.7))
        else:
            self.btn_edit.set_text("Edit UI")
            self.btn_edit.set_colors(CARD_BG, CARD_BORDER)
        self.rebuild_dashboard()

    def add_new_widget(self, *args):
        editor = self.manager.get_screen('editor')
        editor.load_widget(widget_index=None)
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'editor'

    def edit_widget(self, idx):
        editor = self.manager.get_screen('editor')
        editor.load_widget(widget_index=idx)
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'editor'

    def move_widget(self, idx, delta):
        app = App.get_running_app()
        wlist = app.get_active_widgets()
        new_idx = idx + delta
        if 0 <= new_idx < len(wlist):
            wlist[idx], wlist[new_idx] = wlist[new_idx], wlist[idx]
            app.save_state()
            self.rebuild_dashboard()

    def delete_widget(self, idx):
        app = App.get_running_app()
        wlist = app.get_active_widgets()
        if 0 <= idx < len(wlist):
            wlist.pop(idx)
            app.save_state()
            self.rebuild_dashboard()

    def sync_all_pin_modes(self, *args):
        """Send pin mode (M) commands sequentially for all unique pins in the active profile."""
        app = App.get_running_app()
        wlist = app.get_active_widgets()
        sent_pins = set()
        delay = 0.0
        for w in wlist:
            p = str(w.get("pin", "")).strip()
            mode = str(w.get("mode", "1"))
            c1 = w.get("custom1", "")
            c2 = w.get("custom2", "")
            if p and p not in sent_pins:
                sent_pins.add(p)
                Clock.schedule_once(
                    lambda dt, pin=p, m=mode, k1=c1, k2=c2: app.send_protocol(
                        cmd="M", pin=pin, val=m, custom1=k1, custom2=k2
                    ),
                    delay
                )
                delay += 0.08

    def rebuild_dashboard(self):
        self.widget_container.clear_widgets()
        self.sensor_labels = {}
        app = App.get_running_app()
        wlist = app.get_active_widgets()

        if not wlist:
            empty = GlassBox(padding=dp(20), size_hint_y=None, height=dp(110))
            empty.add_widget(Label(
                text="No widgets in this profile.\nTap '+ Add Widget' above to add controls.",
                color=TEXT_MUTED,
                font_size=dp(14),
                halign='center'
            ))
            self.widget_container.add_widget(empty)
            return

        for idx, w in enumerate(wlist):
            wtype = w.get("type", "Switch")
            if wtype == "Switch":
                card = self._build_switch_card(idx, w)
            elif wtype == "Push Button":
                card = self._build_push_card(idx, w)
            elif wtype == "Slider":
                card = self._build_slider_card(idx, w)
            elif wtype == "Joystick":
                card = self._build_joystick_card(idx, w)
            elif wtype == "Sensor Display":
                card = self._build_sensor_card(idx, w)
            else:
                card = self._build_switch_card(idx, w)
            self.widget_container.add_widget(card)

    def _build_card_header(self, idx, w, subtitle):
        hdr = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        safe_name = escape_markup(str(w.get('name', 'Control')))
        safe_sub = escape_markup(str(subtitle))
        title = Label(
            text=f"{safe_name}  [color=77aadd]({safe_sub})[/color]",
            markup=True,
            font_size=dp(13),
            bold=True,
            color=TEXT_MAIN,
            halign='left',
            valign='middle',
            shorten=True
        )
        title.bind(size=title.setter('text_size'))
        hdr.add_widget(title)

        if self.edit_mode:
            b_up = GlassButton(text="Up", font_size=11, bg_color=CARD_BG, size_hint_x=None, width=dp(36))
            b_up.bind(on_release=lambda x, i=idx: self.move_widget(i, -1))
            b_dn = GlassButton(text="Dn", font_size=11, bg_color=CARD_BG, size_hint_x=None, width=dp(36))
            b_dn.bind(on_release=lambda x, i=idx: self.move_widget(i, 1))
            b_ed = GlassButton(text="Edit", font_size=11, bg_color=BTN_PRIMARY, size_hint_x=None, width=dp(44))
            b_ed.bind(on_release=lambda x, i=idx: self.edit_widget(i))
            b_dl = GlassButton(text="X", font_size=11, bg_color=BTN_DANGER, size_hint_x=None, width=dp(32))
            b_dl.bind(on_release=lambda x, i=idx: self.delete_widget(i))
            hdr.add_widget(b_up)
            hdr.add_widget(b_dn)
            hdr.add_widget(b_ed)
            hdr.add_widget(b_dl)
        return hdr

    def _build_switch_card(self, idx, w):
        wid = w.get("id", str(idx))
        is_on = self.switch_states.get(wid, False)
        card = GlassBox(
            orientation='vertical',
            padding=dp(12),
            spacing=dp(8),
            bg_color=CARD_BG_ACTIVE if is_on else CARD_BG,
            border_color=CARD_BORDER_ACTIVE if is_on else CARD_BORDER,
            size_hint_y=None,
            height=dp(96)
        )
        sub = f"Pin {w.get('pin')} | {w.get('cmd', 'D')}"
        card.add_widget(self._build_card_header(idx, w, sub))

        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        state_lbl = Label(
            text="STATE: ON" if is_on else "STATE: OFF",
            font_size=dp(13),
            bold=True,
            color=(0.35, 0.96, 0.60, 1) if is_on else TEXT_MUTED,
            halign='left',
            valign='middle'
        )
        state_lbl.bind(size=state_lbl.setter('text_size'))

        toggle_btn = GlassButton(
            text="TURN OFF" if is_on else "TURN ON",
            font_size=13,
            bg_color=BTN_SUCCESS if is_on else BTN_PRIMARY,
            size_hint_x=None,
            width=dp(116)
        )

        def on_toggle(inst):
            new_state = not self.switch_states.get(wid, False)
            self.switch_states[wid] = new_state
            val = w.get("val_on", "1") if new_state else w.get("val_off", "0")
            App.get_running_app().send_protocol(
                cmd=w.get("cmd", "D"),
                pin=w.get("pin", "13"),
                val=val,
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", "")
            )
            if new_state:
                card.set_colors(CARD_BG_ACTIVE, CARD_BORDER_ACTIVE)
                state_lbl.text = f"STATE: ON ({val})"
                state_lbl.color = (0.35, 0.96, 0.60, 1)
                toggle_btn.set_text("TURN OFF")
                toggle_btn.set_colors(BTN_SUCCESS, CARD_BORDER_ACTIVE)
            else:
                card.set_colors(CARD_BG, CARD_BORDER)
                state_lbl.text = f"STATE: OFF ({val})"
                state_lbl.color = TEXT_MUTED
                toggle_btn.set_text("TURN ON")
                toggle_btn.set_colors(BTN_PRIMARY, (0.45, 0.72, 1.0, 0.45))

        toggle_btn.bind(on_release=on_toggle)
        row.add_widget(state_lbl)
        row.add_widget(toggle_btn)
        card.add_widget(row)
        return card

    def _build_push_card(self, idx, w):
        card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(8),
                        size_hint_y=None, height=dp(98))
        sub = f"Pin {w.get('pin')} | Hold {w.get('cmd', 'D')}"
        card.add_widget(self._build_card_header(idx, w, sub))

        btn = GlassButton(
            text=f"HOLD / PRESS  ({w.get('name', 'Push')})",
            font_size=13,
            bg_color=BTN_PRIMARY,
            size_hint_y=None,
            height=dp(42)
        )

        def on_down(inst):
            inst.set_colors(BTN_SUCCESS, CARD_BORDER_ACTIVE)
            App.get_running_app().send_protocol(
                cmd=w.get("cmd", "D"),
                pin=w.get("pin", "7"),
                val=w.get("val_on", "1"),
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", "")
            )

        def on_up(inst):
            inst.set_colors(BTN_PRIMARY, (0.45, 0.72, 1.0, 0.45))
            App.get_running_app().send_protocol(
                cmd=w.get("cmd", "D"),
                pin=w.get("pin", "7"),
                val=w.get("val_off", "0"),
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", "")
            )

        btn.bind(on_press=on_down, on_release=on_up)
        card.add_widget(btn)
        return card

    def _build_slider_card(self, idx, w):
        mn = safe_int(w.get("min_val"), 0)
        mx = safe_int(w.get("max_val"), 255)
        if mx <= mn:
            mx = mn + 255

        card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(6),
                        size_hint_y=None, height=dp(106))
        sub = f"Pin {w.get('pin')} | {w.get('cmd', 'A')} ({mn}-{mx})"
        card.add_widget(self._build_card_header(idx, w, sub))

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        val_lbl = Label(
            text=str(mn),
            font_size=dp(16),
            bold=True,
            color=TEXT_CYAN,
            size_hint_x=None,
            width=dp(52)
        )
        sld = Slider(min=mn, max=mx, value=mn, step=1)
        last_sent = {"t": 0.0, "v": None}

        def send_slider(val, force=False):
            iv = int(round(val))
            val_lbl.text = str(iv)
            now = time.time()
            if force or (iv != last_sent["v"] and (now - last_sent["t"]) >= 0.08):
                last_sent["t"] = now
                last_sent["v"] = iv
                App.get_running_app().send_protocol(
                    cmd=w.get("cmd", "A"),
                    pin=w.get("pin", "9"),
                    val=str(iv),
                    custom1=w.get("custom1", ""),
                    custom2=w.get("custom2", "")
                )

        sld.bind(value=lambda inst, v: send_slider(v, force=False))

        def on_sld_touch_up(inst, touch):
            if inst.collide_point(*touch.pos):
                send_slider(inst.value, force=True)

        sld.bind(on_touch_up=on_sld_touch_up)
        row.add_widget(sld)
        row.add_widget(val_lbl)
        card.add_widget(row)
        return card

    def _build_joystick_card(self, idx, w):
        mn = safe_int(w.get("min_val"), 0)
        mx = safe_int(w.get("max_val"), 255)
        if mx <= mn:
            mx = mn + 255
        mid = int((mn + mx) / 2)
        pin = str(w.get("pin", "5"))

        card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(6),
                        size_hint_y=None, height=dp(248))
        sub = f"Pin {pin} | X & Y Together"
        card.add_widget(self._build_card_header(idx, w, sub))

        xy_lbl = Label(
            text=f"X: {mid}    |    Y: {mid}",
            font_size=dp(13),
            bold=True,
            color=TEXT_CYAN,
            size_hint_y=None,
            height=dp(22)
        )
        card.add_widget(xy_lbl)

        def on_joy_move(xv, yv, is_moving):
            xy_lbl.text = f"X: {xv}    |    Y: {yv}"
            val_state = w.get("val_on", "1") if is_moving else w.get("val_off", "0")
            # Send both X and Y together in a single formatted packet
            App.get_running_app().send_protocol(
                cmd=w.get("cmd", "A"),
                pin=pin,
                x=str(xv),
                y=str(yv),
                val=val_state,
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", "")
            )

        pad = JoystickPad(min_val=mn, max_val=mx, on_move=on_joy_move,
                          size_hint=(1, None), height=dp(168))
        card.add_widget(pad)
        return card

    def _build_sensor_card(self, idx, w):
        pin = str(w.get("pin", "0"))
        unit = w.get("unit", "")
        card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(8),
                        size_hint_y=None, height=dp(100))
        sub = f"Pin {pin} | {w.get('cmd', 'R')}"
        card.add_widget(self._build_card_header(idx, w, sub))

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        read_lbl = Label(
            text=f"-- {unit}".strip(),
            font_size=dp(22),
            bold=True,
            color=(0.35, 0.95, 0.65, 1),
            halign='left',
            valign='middle'
        )
        read_lbl.bind(size=read_lbl.setter('text_size'))
        self.sensor_labels.setdefault(pin, []).append((read_lbl, unit))

        btn_read = GlassButton(
            text="Read",
            font_size=13,
            bg_color=BTN_PRIMARY,
            size_hint_x=None,
            width=dp(92)
        )
        btn_read.bind(
            on_release=lambda x: App.get_running_app().send_protocol(
                cmd=w.get("cmd", "R"),
                pin=pin,
                val=w.get("val_on", "1"),
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", "")
            )
        )
        row.add_widget(read_lbl)
        row.add_widget(btn_read)
        card.add_widget(row)
        return card

    def update_sensor_from_rx(self, line):
        """Parse incoming serial lines and update matching sensor display widgets."""
        cleaned = line.strip().strip("<>").strip()
        parts = re.split(r'[: ,;=]+', cleaned)
        updated = False
        if len(parts) >= 4 and parts[0] in self.sensor_labels:
            pin, val = parts[0], parts[3]
            for lbl, unit in self.sensor_labels[pin]:
                lbl.text = f"{val} {unit}".strip()
            updated = True
        elif len(parts) >= 3 and parts[1] in self.sensor_labels:
            pin, val = parts[1], parts[2]
            for lbl, unit in self.sensor_labels[pin]:
                lbl.text = f"{val} {unit}".strip()
            updated = True
        elif len(parts) == 2 and parts[0] in self.sensor_labels:
            pin, val = parts[0], parts[1]
            for lbl, unit in self.sensor_labels[pin]:
                lbl.text = f"{val} {unit}".strip()
            updated = True

        if not updated and len(self.sensor_labels) == 1:
            # If only one sensor widget exists, display the raw incoming value directly
            only_pin = next(iter(self.sensor_labels))
            for lbl, unit in self.sensor_labels[only_pin]:
                lbl.text = f"{cleaned} {unit}".strip()

    def update_mini_log(self, ts, tag, msg):
        self.mini_log_btn.set_text(f"[{tag}] {msg}")

    def update_bt_status(self, connected, msg):
        if connected:
            self.status_lbl.text = f"ON: {msg}"
            self.status_lbl.color = (0.30, 0.95, 0.55, 1)
        else:
            self.status_lbl.text = f"OFF: {msg}"
            self.status_lbl.color = (1.0, 0.45, 0.45, 1)

    def go_to(self, screen_name):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = screen_name


# ==========================================
# Screen 2: Add / Edit Widget Screen
# ==========================================
class WidgetEditorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.editing_index = None

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_back = GlassButton(text="< Back", font_size=13, bg_color=CARD_BG, size_hint_x=None, width=dp(82))
        btn_back.bind(on_release=self.go_back)
        self.hdr_lbl = Label(text="Add New Widget", font_size=dp(18), bold=True,
                             color=TEXT_MAIN, halign='left', valign='middle')
        self.hdr_lbl.bind(size=self.hdr_lbl.setter('text_size'))
        top_bar.add_widget(btn_back)
        top_bar.add_widget(self.hdr_lbl)
        root.add_widget(top_bar)

        self.scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        form = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, padding=[0, dp(4), 0, dp(24)])
        form.bind(minimum_height=form.setter('height'))

        card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(8), size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))

        card.add_widget(self._flbl("Widget Type"))
        self.sp_type = Spinner(
            text='Switch',
            values=('Switch', 'Push Button', 'Slider', 'Joystick', 'Sensor Display'),
            size_hint_y=None, height=dp(44),
            background_normal='', background_color=(0.14, 0.32, 0.58, 0.65),
            color=TEXT_MAIN, font_size=dp(14)
        )
        self.sp_type.bind(text=self.on_type_changed)
        card.add_widget(self.sp_type)

        card.add_widget(self._flbl("Widget Name"))
        self.in_name = StyledInput(hint="e.g. Drive Joystick / Light 1")
        card.add_widget(self.in_name)

        pin_row = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        pin_row.add_widget(self._linput("Pin Number (Box 1)", "13", None, "in_pin"))
        c_box = BoxLayout(orientation='vertical', spacing=dp(4))
        c_box.add_widget(self._flbl("Command (CMD)"))
        self.sp_cmd = Spinner(
            text='D',
            values=('D', 'A', 'R', 'M'),
            size_hint_y=None, height=dp(44),
            background_normal='', background_color=INPUT_BG,
            color=TEXT_MAIN, font_size=dp(14)
        )
        c_box.add_widget(self.sp_cmd)
        pin_row.add_widget(c_box)
        card.add_widget(pin_row)

        card.add_widget(self._flbl("Pin Mode (for Sync M)"))
        self.sp_mode = Spinner(
            text='1 - Output',
            values=('0 - Input', '1 - Output', '2 - PWM'),
            size_hint_y=None, height=dp(44),
            background_normal='', background_color=INPUT_BG,
            color=TEXT_MAIN, font_size=dp(13)
        )
        card.add_widget(self.sp_mode)

        val_row1 = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        val_row1.add_widget(self._linput("ON / Active Value (Box 4)", "1", None, "in_on"))
        val_row1.add_widget(self._linput("OFF / Stop Value (Box 4)", "0", None, "in_off"))
        card.add_widget(val_row1)

        val_row2 = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        val_row2.add_widget(self._linput("Min Value (Slider/Joy)", "0", "int", "in_min"))
        val_row2.add_widget(self._linput("Max Value (Slider/Joy)", "255", "int", "in_max"))
        card.add_widget(val_row2)

        cust_row = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        cust_row.add_widget(self._linput("Box 5 Custom (Optional)", "Format default", None, "in_c1"))
        cust_row.add_widget(self._linput("Box 6 Custom (Optional)", "Format default", None, "in_c2"))
        card.add_widget(cust_row)

        card.add_widget(self._flbl("Sensor Unit (e.g. C, cm, V)"))
        self.in_unit = StyledInput(hint="Optional unit")
        card.add_widget(self.in_unit)

        form.add_widget(card)

        btn_save = GlassButton(text="Save Widget", font_size=15, bg_color=BTN_SUCCESS,
                               size_hint_y=None, height=dp(50))
        btn_save.bind(on_release=self.save_widget)
        form.add_widget(btn_save)

        self.scroll.add_widget(form)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def _flbl(self, txt):
        l = Label(text=txt, font_size=dp(12), color=TEXT_MUTED,
                  size_hint_y=None, height=dp(20), halign='left', valign='bottom')
        l.bind(size=l.setter('text_size'))
        return l

    def _linput(self, title, hint, flt, attr):
        box = BoxLayout(orientation='vertical', spacing=dp(4))
        box.add_widget(self._flbl(title))
        inp = StyledInput(hint=hint, input_filter=flt)
        setattr(self, attr, inp)
        box.add_widget(inp)
        return box

    def on_type_changed(self, spinner, wtype):
        if self.editing_index is not None:
            return
        if wtype in ('Switch', 'Push Button'):
            self.sp_mode.text = '1 - Output'
            self.sp_cmd.text = 'D'
        elif wtype in ('Slider', 'Joystick'):
            self.sp_mode.text = '2 - PWM'
            self.sp_cmd.text = 'A'
        elif wtype == 'Sensor Display':
            self.sp_mode.text = '0 - Input'
            self.sp_cmd.text = 'R'

    def load_widget(self, widget_index=None):
        self.editing_index = widget_index
        self.scroll.scroll_y = 1
        app = App.get_running_app()

        if widget_index is None:
            self.hdr_lbl.text = "Add New Widget"
            self.sp_type.text = "Switch"
            self.in_name.text = ""
            self.in_pin.text = "13"
            self.sp_mode.text = "1 - Output"
            self.sp_cmd.text = "D"
            self.in_on.text = "1"
            self.in_off.text = "0"
            self.in_min.text = "0"
            self.in_max.text = "255"
            self.in_c1.text = ""
            self.in_c2.text = ""
            self.in_unit.text = ""
        else:
            w = app.get_active_widgets()[widget_index]
            self.hdr_lbl.text = f"Edit: {w.get('name', 'Widget')}"
            self.sp_type.text = w.get("type", "Switch")
            self.in_name.text = w.get("name", "")
            self.in_pin.text = str(w.get("pin", "13"))
            m = str(w.get("mode", "1"))
            self.sp_mode.text = '0 - Input' if m == '0' else ('2 - PWM' if m == '2' else '1 - Output')
            self.sp_cmd.text = w.get("cmd", "D")
            self.in_on.text = str(w.get("val_on", "1"))
            self.in_off.text = str(w.get("val_off", "0"))
            self.in_min.text = str(w.get("min_val", "0"))
            self.in_max.text = str(w.get("max_val", "255"))
            self.in_c1.text = str(w.get("custom1", ""))
            self.in_c2.text = str(w.get("custom2", ""))
            self.in_unit.text = str(w.get("unit", ""))

    def save_widget(self, *args):
        app = App.get_running_app()
        wlist = app.get_active_widgets()
        mode_code = self.sp_mode.text.split(" ")[0]
        wtype = self.sp_type.text
        wdata = {
            "id": f"w_{int(time.time() * 1000)}",
            "type": wtype,
            "name": self.in_name.text.strip() or f"{wtype} {self.in_pin.text.strip() or '1'}",
            "pin": self.in_pin.text.strip() or "13",
            "mode": mode_code,
            "cmd": self.sp_cmd.text.strip() or "D",
            "val_on": self.in_on.text.strip() or "1",
            "val_off": self.in_off.text.strip() or "0",
            "min_val": self.in_min.text.strip() or "0",
            "max_val": self.in_max.text.strip() or "255",
            "custom1": self.in_c1.text.strip(),
            "custom2": self.in_c2.text.strip(),
            "unit": self.in_unit.text.strip(),
        }
        if self.editing_index is None:
            wlist.append(wdata)
        else:
            wdata["id"] = wlist[self.editing_index].get("id", wdata["id"])
            wlist[self.editing_index] = wdata

        app.save_state()
        self.go_back()

    def go_back(self, *args):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'dashboard'


# ==========================================
# Screen 3: 6-Box Packet Format Builder
# ==========================================
class ProtocolScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._loading = False
        self.box_widgets = []

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_back = GlassButton(text="< Back", font_size=13, bg_color=CARD_BG, size_hint_x=None, width=dp(82))
        btn_back.bind(on_release=self.go_back)
        hdr = Label(text="6-Box Packet Format", font_size=dp(17), bold=True,
                    color=TEXT_MAIN, halign='left', valign='middle')
        hdr.bind(size=hdr.setter('text_size'))
        btn_reset = GlassButton(text="Reset", font_size=12, bg_color=BTN_WARN, size_hint_x=None, width=dp(64))
        btn_reset.bind(on_release=self.reset_default_boxes)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(hdr)
        top_bar.add_widget(btn_reset)
        root.add_widget(top_bar)

        scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, padding=[0, dp(4), 0, dp(24)])
        body.bind(minimum_height=body.setter('height'))

        # --- Markers & Separator Card ---
        wrap_card = GlassBox(orientation='vertical', padding=dp(10), spacing=dp(8), size_hint_y=None)
        wrap_card.bind(minimum_height=wrap_card.setter('height'))

        w_hdr = Label(text="Packet Wrapper & Separator", font_size=dp(13), bold=True,
                      color=TEXT_CYAN, size_hint_y=None, height=dp(20), halign='left')
        w_hdr.bind(size=w_hdr.setter('text_size'))
        wrap_card.add_widget(w_hdr)

        m_grid = GridLayout(cols=4, spacing=dp(6), size_hint_y=None, height=dp(62))
        self.sp_start = self._make_small_spinner(m_grid, "Start", "<", ("<", "[", "{", "$", "None"))
        self.sp_sep = self._make_small_spinner(m_grid, "Sep", ":", (":", ",", ";", "|", "-"))
        self.sp_end = self._make_small_spinner(m_grid, "End", ">", (">", "]", "}", "#", "None"))
        self.sp_ending = self._make_small_spinner(m_grid, "Newline", "LF (\\n)", ("LF (\\n)", "CRLF (\\r\\n)", "None"))
        wrap_card.add_widget(m_grid)
        body.add_widget(wrap_card)

        # --- 6 Configurable Boxes Card ---
        boxes_card = GlassBox(orientation='vertical', padding=dp(10), spacing=dp(8), size_hint_y=None)
        boxes_card.bind(minimum_height=boxes_card.setter('height'))

        b_hdr = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
        for txt, sx in [("Slot", 0.28), ("Data Type", 0.40), ("Custom / Default", 0.32)]:
            l = Label(text=txt, font_size=dp(11), bold=True, color=TEXT_CYAN,
                      size_hint_x=sx, halign='left', valign='middle')
            l.bind(size=l.setter('text_size'))
            b_hdr.add_widget(l)
        boxes_card.add_widget(b_hdr)

        box_hints = [
            "Box 1 (Pin)",
            "Box 2 (X)",
            "Box 3 (Y)",
            "Box 4 (Val)",
            "Box 5 (Cust1)",
            "Box 6 (Cust2)",
        ]

        for i in range(6):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            lbl = Label(
                text=box_hints[i],
                font_size=dp(12),
                bold=True,
                color=TEXT_MAIN,
                size_hint_x=0.28,
                halign='left',
                valign='middle',
                shorten=True
            )
            lbl.bind(size=lbl.setter('text_size'))

            sp = Spinner(
                text=DEFAULT_BOXES[i]["source"],
                values=BOX_OPTIONS,
                size_hint_x=0.40,
                background_normal='',
                background_color=(0.14, 0.32, 0.58, 0.70),
                color=TEXT_MAIN,
                font_size=dp(13),
                bold=True
            )
            sp.bind(text=self.on_any_change)

            inp = StyledInput(hint="0", size_hint_x=0.32)
            inp.text = "0"
            inp.bind(text=self.on_any_change)

            row.add_widget(lbl)
            row.add_widget(sp)
            row.add_widget(inp)
            boxes_card.add_widget(row)
            self.box_widgets.append((sp, inp))

        tip = Label(
            text="Tip: Use CUSTOM1/CUSTOM2 in Box 5 & 6 and enter a default value beside it. Select OFF to disable any box.",
            font_size=dp(11),
            color=TEXT_MUTED,
            size_hint_y=None,
            height=dp(36),
            halign='left',
            valign='middle'
        )
        tip.bind(size=tip.setter('text_size'))
        boxes_card.add_widget(tip)
        body.add_widget(boxes_card)

        # --- Live Packet Preview Card ---
        prev_card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(6),
                             bg_color=(0.04, 0.10, 0.20, 0.78), size_hint_y=None, height=dp(130))
        prev_hdr = Label(text="Live Packet Preview (6 Boxes)", font_size=dp(13), bold=True,
                         color=TEXT_CYAN, size_hint_y=None, height=dp(20), halign='left')
        prev_hdr.bind(size=prev_hdr.setter('text_size'))
        self.preview_lbl = Label(text="", font_size=dp(13), color=TEXT_MAIN,
                                 halign='left', valign='top')
        self.preview_lbl.bind(size=self.preview_lbl.setter('text_size'))
        prev_card.add_widget(prev_hdr)
        prev_card.add_widget(self.preview_lbl)
        body.add_widget(prev_card)

        self.msg_lbl = Label(text="", font_size=dp(12), color=(0.35, 0.95, 0.55, 1),
                             size_hint_y=None, height=dp(20))
        body.add_widget(self.msg_lbl)

        btn_save = GlassButton(text="Save 6-Box Format", font_size=15, bg_color=BTN_SUCCESS,
                               size_hint_y=None, height=dp(48))
        btn_save.bind(on_release=self.save_format_click)
        body.add_widget(btn_save)

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    def _make_small_spinner(self, parent_grid, title, default_val, values):
        col = BoxLayout(orientation='vertical', spacing=dp(3))
        l = Label(text=title, font_size=dp(11), color=TEXT_MUTED,
                  size_hint_y=None, height=dp(16), halign='center')
        l.bind(size=l.setter('text_size'))
        sp = Spinner(
            text=default_val,
            values=values,
            size_hint_y=None,
            height=dp(40),
            background_normal='',
            background_color=INPUT_BG,
            color=TEXT_MAIN,
            font_size=dp(12),
            bold=True
        )
        sp.bind(text=self.on_any_change)
        col.add_widget(l)
        col.add_widget(sp)
        parent_grid.add_widget(col)
        return sp

    def on_pre_enter(self):
        self._loading = True
        app = App.get_running_app()
        ps = app.protocol_settings

        s_mark = ps.get("start_marker", "<")
        e_mark = ps.get("end_marker", ">")
        self.sp_start.text = s_mark if s_mark else "None"
        self.sp_sep.text = ps.get("separator", ":")
        self.sp_end.text = e_mark if e_mark else "None"
        self.sp_ending.text = ps.get("line_ending", "LF (\\n)")

        boxes = ps.get("boxes") or copy.deepcopy(DEFAULT_BOXES)
        for i in range(6):
            b = boxes[i] if i < len(boxes) else DEFAULT_BOXES[i]
            sp, inp = self.box_widgets[i]
            src = b.get("source", DEFAULT_BOXES[i]["source"])
            sp.text = src if src in BOX_OPTIONS else "OFF"
            inp.text = str(b.get("default", "0"))

        self._loading = False
        self.msg_lbl.text = ""
        self.update_preview()

    def _collect_settings(self):
        boxes = []
        for sp, inp in self.box_widgets:
            boxes.append({
                "source": sp.text,
                "default": inp.text.strip() if inp.text.strip() != "" else "0"
            })
        return {
            "start_marker": "" if self.sp_start.text == "None" else self.sp_start.text,
            "separator": self.sp_sep.text,
            "end_marker": "" if self.sp_end.text == "None" else self.sp_end.text,
            "line_ending": self.sp_ending.text,
            "boxes": boxes,
        }

    def on_any_change(self, *args):
        if self._loading:
            return
        self.save_format(silent=True)
        self.update_preview()

    def update_preview(self):
        app = App.get_running_app()
        cfg = self._collect_settings()
        p_joy = app.format_packet(cmd="A", pin="5", x="210", y="180", val="1", settings=cfg)
        p_sw = app.format_packet(cmd="D", pin="13", val="1", settings=cfg)
        p_sld = app.format_packet(cmd="A", pin="9", val="150", settings=cfg)
        self.preview_lbl.text = (
            f"Joystick (X+Y): {p_joy}\n"
            f"Switch ON:      {p_sw}\n"
            f"Slider PWM:     {p_sld}"
        )

    def reset_default_boxes(self, *args):
        self._loading = True
        self.sp_start.text = "<"
        self.sp_sep.text = ":"
        self.sp_end.text = ">"
        self.sp_ending.text = "LF (\\n)"
        for i in range(6):
            sp, inp = self.box_widgets[i]
            sp.text = DEFAULT_BOXES[i]["source"]
            inp.text = DEFAULT_BOXES[i]["default"]
        self._loading = False
        self.save_format(silent=False)
        self.update_preview()
        self.msg_lbl.text = "Default 6 Boxes Restored!"

    def save_format_click(self, *args):
        self.save_format(silent=False)

    def save_format(self, silent=False):
        app = App.get_running_app()
        cfg = self._collect_settings()
        app.protocol_settings = cfg
        app.bt.set_line_ending(cfg["line_ending"])
        app.save_state()
        if not silent:
            self.msg_lbl.text = "6-Box Format Saved!"

    def go_back(self, *args):
        self.save_format(silent=True)
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'dashboard'


# ==========================================
# Screen 4: Connection Screen (Scan + Auto-Connect)
# ==========================================
class ConnectionScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seen_macs = set()

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_back = GlassButton(text="< Back", font_size=13, bg_color=CARD_BG, size_hint_x=None, width=dp(82))
        btn_back.bind(on_release=self.go_back)
        hdr = Label(text="HC-05 Connection", font_size=dp(18), bold=True,
                    color=TEXT_MAIN, halign='left', valign='middle')
        hdr.bind(size=hdr.setter('text_size'))
        top_bar.add_widget(btn_back)
        top_bar.add_widget(hdr)
        root.add_widget(top_bar)

        card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(8), size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))

        l_mac = Label(text="HC-05 MAC Address (Auto-Connect)", font_size=dp(12),
                      color=TEXT_MUTED, size_hint_y=None, height=dp(20), halign='left')
        l_mac.bind(size=l_mac.setter('text_size'))
        card.add_widget(l_mac)

        self.in_mac = StyledInput(hint="XX:XX:XX:XX:XX:XX")
        card.add_widget(self.in_mac)

        sw_row = BoxLayout(size_hint_y=None, height=dp(38))
        sw_lbl = Label(text="Auto-Connect ON/OFF", font_size=dp(14), color=TEXT_MAIN,
                       halign='left', valign='middle')
        sw_lbl.bind(size=sw_lbl.setter('text_size'))
        self.sw_auto = Switch(active=True, size_hint_x=None, width=dp(70))
        sw_row.add_widget(sw_lbl)
        sw_row.add_widget(self.sw_auto)
        card.add_widget(sw_row)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b_conn = GlassButton(text="Save & Connect", bg_color=BTN_SUCCESS)
        b_conn.bind(on_release=self.save_and_connect)
        b_disc = GlassButton(text="Disconnect", bg_color=BTN_DANGER)
        b_disc.bind(on_release=lambda x: App.get_running_app().bt.disconnect())
        btn_row.add_widget(b_conn)
        btn_row.add_widget(b_disc)
        card.add_widget(btn_row)

        self.msg_lbl = Label(text="", font_size=dp(12), color=(0.35, 0.95, 0.55, 1),
                             size_hint_y=None, height=dp(20))
        card.add_widget(self.msg_lbl)
        root.add_widget(card)

        dev_hdr = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        d_lbl = Label(text="HC-05 Devices", font_size=dp(15), bold=True,
                      color=TEXT_MAIN, halign='left', valign='middle')
        d_lbl.bind(size=d_lbl.setter('text_size'))
        b_paired = GlassButton(text="Paired", font_size=12, bg_color=CARD_BG,
                               size_hint_x=None, width=dp(72))
        b_paired.bind(on_release=self.load_paired)
        b_scan = GlassButton(text="Scan Nearby", font_size=12, bg_color=BTN_PRIMARY,
                             size_hint_x=None, width=dp(100))
        b_scan.bind(on_release=self.scan_nearby)
        dev_hdr.add_widget(d_lbl)
        dev_hdr.add_widget(b_paired)
        dev_hdr.add_widget(b_scan)
        root.add_widget(dev_hdr)

        scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        self.dev_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)
        self.dev_box.bind(minimum_height=self.dev_box.setter('height'))
        scroll.add_widget(self.dev_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        app = App.get_running_app()
        self.in_mac.text = app.bt_settings.get("mac_address", "")
        self.sw_auto.active = app.bt_settings.get("auto_connect", True)
        self.msg_lbl.text = ""
        self.load_paired()

    def _add_device_row(self, name, mac, tag="Paired"):
        if mac in self.seen_macs:
            return
        self.seen_macs.add(mac)
        b = GlassButton(
            text=f"[{tag}]  {name}   ({mac})",
            font_size=13,
            bg_color=CARD_BG,
            size_hint_y=None,
            height=dp(48)
        )
        b.bind(on_release=lambda inst, m=mac: self.select_and_connect(m))
        self.dev_box.add_widget(b)

    def load_paired(self, *args):
        self.dev_box.clear_widgets()
        self.seen_macs.clear()
        devices = App.get_running_app().bt.get_paired_devices()
        if not devices:
            self.dev_box.add_widget(Label(
                text="No paired devices found.\nPair HC-05 in Phone Bluetooth settings or tap Scan Nearby.",
                color=TEXT_MUTED, size_hint_y=None, height=dp(52), halign='center'
            ))
            return
        for name, mac in devices:
            self._add_device_row(name, mac, tag="Paired")

    def scan_nearby(self, *args):
        self.msg_lbl.text = "Scanning nearby Bluetooth devices..."
        App.get_running_app().bt.start_nearby_scan(
            lambda name, mac: self._add_device_row(name, mac, tag="Nearby")
        )

    def select_and_connect(self, mac):
        self.in_mac.text = mac
        self.save_and_connect()

    def save_and_connect(self, *args):
        app = App.get_running_app()
        mac = self.in_mac.text.strip().upper()
        auto = self.sw_auto.active
        app.bt_settings["mac_address"] = mac
        app.bt_settings["auto_connect"] = auto
        app.save_state()
        app.bt.set_config(mac, auto)
        app.bt.disconnect(silent=True)
        if mac:
            app.bt.connect(mac)
            self.msg_lbl.text = f"Saved! Connecting to {mac}..."
        else:
            self.msg_lbl.text = "Settings Saved."

    def go_back(self, *args):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'dashboard'


# ==========================================
# Screen 5: Profile Manager
# ==========================================
class ProfileManagerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_back = GlassButton(text="< Back", font_size=13, bg_color=CARD_BG, size_hint_x=None, width=dp(82))
        btn_back.bind(on_release=self.go_back)
        hdr = Label(text="Saved Profiles", font_size=dp(18), bold=True,
                    color=TEXT_MAIN, halign='left', valign='middle')
        hdr.bind(size=hdr.setter('text_size'))
        top_bar.add_widget(btn_back)
        top_bar.add_widget(hdr)
        root.add_widget(top_bar)

        new_card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(8), size_hint_y=None)
        new_card.bind(minimum_height=new_card.setter('height'))
        lbl = Label(text="New Project Profile Name", font_size=dp(12), color=TEXT_MUTED,
                    size_hint_y=None, height=dp(20), halign='left')
        lbl.bind(size=lbl.setter('text_size'))
        new_card.add_widget(lbl)

        self.in_prof_name = StyledInput(hint="e.g. Robot Arm / Smart Farm")
        new_card.add_widget(self.in_prof_name)

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b_new = GlassButton(text="+ Create Blank", bg_color=BTN_SUCCESS)
        b_new.bind(on_release=lambda x: self.create_profile(duplicate_current=False))
        b_dup = GlassButton(text="Save Copy of Current", bg_color=BTN_PRIMARY)
        b_dup.bind(on_release=lambda x: self.create_profile(duplicate_current=True))
        row.add_widget(b_new)
        row.add_widget(b_dup)
        new_card.add_widget(row)

        self.msg_lbl = Label(text="", font_size=dp(12), color=(0.35, 0.95, 0.55, 1),
                             size_hint_y=None, height=dp(20))
        new_card.add_widget(self.msg_lbl)
        root.add_widget(new_card)

        scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        self.list_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter('height'))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.msg_lbl.text = ""
        self.refresh_list()

    def refresh_list(self):
        self.list_box.clear_widgets()
        app = App.get_running_app()
        for pname, widgets in app.profiles.items():
            is_act = (pname == app.active_profile)
            row = GlassBox(
                padding=dp(10), spacing=dp(8),
                bg_color=CARD_BG_ACTIVE if is_act else CARD_BG,
                border_color=CARD_BORDER_ACTIVE if is_act else CARD_BORDER,
                size_hint_y=None, height=dp(58)
            )
            lbl = Label(
                text=f"{pname}  ({len(widgets)} widgets)",
                font_size=dp(14), bold=is_act, color=TEXT_MAIN,
                halign='left', valign='middle'
            )
            lbl.bind(size=lbl.setter('text_size'))
            row.add_widget(lbl)

            if not is_act:
                b_use = GlassButton(text="Load", font_size=12, bg_color=BTN_PRIMARY,
                                    size_hint_x=None, width=dp(64))
                b_use.bind(on_release=lambda x, p=pname: self.load_profile(p))
                row.add_widget(b_use)
            else:
                act_lbl = Label(text="ACTIVE", font_size=dp(11), bold=True,
                                color=(0.35, 0.95, 0.60, 1), size_hint_x=None, width=dp(58))
                row.add_widget(act_lbl)

            if len(app.profiles) > 1:
                b_del = GlassButton(text="Del", font_size=12, bg_color=BTN_DANGER,
                                    size_hint_x=None, width=dp(50))
                b_del.bind(on_release=lambda x, p=pname: self.delete_profile(p))
                row.add_widget(b_del)

            self.list_box.add_widget(row)

    def create_profile(self, duplicate_current=False):
        app = App.get_running_app()
        name = self.in_prof_name.text.strip()
        if not name:
            self.msg_lbl.text = "Please enter a profile name!"
            return
        if name in app.profiles:
            self.msg_lbl.text = "A profile with this name already exists!"
            return
        if duplicate_current:
            app.profiles[name] = copy.deepcopy(app.get_active_widgets())
        else:
            app.profiles[name] = []
        app.active_profile = name
        app.save_state()
        self.in_prof_name.text = ""
        self.msg_lbl.text = f"Profile '{name}' created & activated!"
        self.refresh_list()

    def load_profile(self, pname):
        app = App.get_running_app()
        app.active_profile = pname
        app.save_state()
        self.go_back()

    def delete_profile(self, pname):
        app = App.get_running_app()
        if len(app.profiles) <= 1:
            return
        app.profiles.pop(pname, None)
        if app.active_profile == pname:
            app.active_profile = next(iter(app.profiles.keys()))
        app.save_state()
        self.refresh_list()

    def go_back(self, *args):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'dashboard'


# ==========================================
# Screen 6: Terminal / Log View
# ==========================================
class TerminalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log_lines = []

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))

        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        btn_back = GlassButton(text="< Back", font_size=13, bg_color=CARD_BG, size_hint_x=None, width=dp(80))
        btn_back.bind(on_release=self.go_back)
        hdr = Label(text="Terminal / Log View", font_size=dp(18), bold=True,
                    color=TEXT_MAIN, halign='left', valign='middle')
        hdr.bind(size=hdr.setter('text_size'))
        btn_clear = GlassButton(text="Clear", font_size=12, bg_color=BTN_DANGER, size_hint_x=None, width=dp(68))
        btn_clear.bind(on_release=self.clear_log)

        top_bar.add_widget(btn_back)
        top_bar.add_widget(hdr)
        top_bar.add_widget(btn_clear)
        root.add_widget(top_bar)

        # Quick test packet buttons
        quick_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        tests = [
            ("Test Joy", dict(cmd="A", pin="5", x="210", y="180", val="1")),
            ("Test SW", dict(cmd="D", pin="13", val="1")),
            ("Test PWM", dict(cmd="A", pin="9", val="150")),
            ("Test Mode", dict(cmd="M", pin="13", val="1")),
        ]
        for lbl, kw in tests:
            qb = GlassButton(text=lbl, font_size=11, bg_color=CARD_BG)
            qb.bind(on_release=lambda x, k=kw: App.get_running_app().send_protocol(**k))
            quick_row.add_widget(qb)
        root.add_widget(quick_row)

        term_card = GlassBox(padding=dp(10), bg_color=(0.03, 0.06, 0.12, 0.80),
                             border_color=CARD_BORDER, radius=12)
        self.scroll = ScrollView(bar_width=dp(5), do_scroll_x=False)
        self.log_lbl = Label(
            text="[color=88aadd]Terminal Ready...[/color]",
            markup=True,
            font_size=dp(12),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        self.log_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        self.log_lbl.bind(texture_size=lambda inst, s: setattr(inst, 'height', max(s[1], dp(300))))
        self.scroll.add_widget(self.log_lbl)
        term_card.add_widget(self.scroll)
        root.add_widget(term_card)

        cmd_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.cmd_input = StyledInput(hint="Manual packet (e.g. <13:0:0:1:0:0>)")
        self.cmd_input.bind(on_text_validate=self.send_manual)
        btn_send = GlassButton(text="Send", bg_color=BTN_PRIMARY, size_hint_x=None, width=dp(80))
        btn_send.bind(on_release=self.send_manual)
        cmd_row.add_widget(self.cmd_input)
        cmd_row.add_widget(btn_send)
        root.add_widget(cmd_row)

        self.add_widget(root)

    def append_log(self, ts, tag, msg):
        safe_msg = escape_markup(str(msg))
        if tag == "TX":
            line = f"[color=7799bb]{ts}[/color] [b][color=44ccff][TX][/color][/b] {safe_msg}"
        elif tag == "RX":
            line = f"[color=7799bb]{ts}[/color] [b][color=44ee88][RX][/color][/b] {safe_msg}"
        else:
            line = f"[color=7799bb]{ts}[/color] [b][color=ffcc55][SYS][/color][/b] {safe_msg}"

        self.log_lines.append(line)
        if len(self.log_lines) > 300:
            self.log_lines = self.log_lines[-300:]
        self.log_lbl.text = "\n".join(self.log_lines)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.05)

    def clear_log(self, *args):
        self.log_lines = []
        self.log_lbl.text = ""

    def send_manual(self, *args):
        cmd = self.cmd_input.text.strip()
        if cmd:
            App.get_running_app().bt.send(cmd)
            self.cmd_input.text = ""

    def go_back(self, *args):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'dashboard'


# ==========================================
# Main Pro Controller Application
# ==========================================
class ProControllerApp(App):
    def build(self):
        self.title = "Pro HC-05 Controller"
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            self.state_file = os.path.join(self.user_data_dir, "pro_controller_state.json")
        except Exception:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.state_file = os.path.join(base_dir, "pro_controller_state.json")

        saved = self._load_json(self.state_file, {})
        self.profiles = saved.get("profiles") or copy.deepcopy(DEFAULT_PROFILES)
        self.active_profile = saved.get("active_profile") or next(iter(self.profiles.keys()))
        if self.active_profile not in self.profiles:
            self.active_profile = next(iter(self.profiles.keys()))

        self.bt_settings = saved.get("bt_settings") or {
            "mac_address": "",
            "auto_connect": True
        }

        # Ensure 6-box protocol structure is initialized cleanly
        ps = saved.get("protocol_settings") or {}
        if not isinstance(ps.get("boxes"), list) or len(ps.get("boxes")) != 6:
            ps = {
                "start_marker": "<",
                "separator": ":",
                "end_marker": ">",
                "line_ending": ps.get("line_ending", "LF (\\n)"),
                "boxes": copy.deepcopy(DEFAULT_BOXES),
            }
        self.protocol_settings = ps

        self.sm = ScreenManager()
        self.dashboard = DashboardScreen(name='dashboard')
        self.editor = WidgetEditorScreen(name='editor')
        self.protocol = ProtocolScreen(name='protocol')
        self.connection = ConnectionScreen(name='connection')
        self.profiles_screen = ProfileManagerScreen(name='profiles')
        self.terminal = TerminalScreen(name='terminal')

        self.sm.add_widget(self.dashboard)
        self.sm.add_widget(self.editor)
        self.sm.add_widget(self.protocol)
        self.sm.add_widget(self.connection)
        self.sm.add_widget(self.profiles_screen)
        self.sm.add_widget(self.terminal)

        def on_log(ts, tag, msg):
            self.terminal.append_log(ts, tag, msg)
            self.dashboard.update_mini_log(ts, tag, msg)

        self.bt = HC05Manager(
            on_status=self.dashboard.update_bt_status,
            on_log=on_log,
            on_rx_data=self.dashboard.update_sensor_from_rx
        )
        self.bt.set_config(
            self.bt_settings.get("mac_address", ""),
            self.bt_settings.get("auto_connect", True)
        )
        self.bt.set_line_ending(self.protocol_settings.get("line_ending", "LF (\\n)"))
        return self.sm

    def get_active_widgets(self):
        return self.profiles.setdefault(self.active_profile, [])

    def format_packet(self, cmd="D", pin="0", x=None, y=None, val=None,
                      custom1="", custom2="", settings=None):
        """Build the output packet string according to the active 6-box format."""
        cfg = settings if settings is not None else self.protocol_settings
        start_m = cfg.get("start_marker", "<")
        sep = cfg.get("separator", ":")
        end_m = cfg.get("end_marker", ">")
        boxes = cfg.get("boxes", DEFAULT_BOXES)

        values = []
        for b in boxes:
            src = b.get("source", "OFF")
            default_v = str(b.get("default", "0"))
            if src == "OFF":
                continue
            elif src == "PIN":
                v = str(pin) if (pin is not None and str(pin) != "") else default_v
            elif src == "X":
                v = str(x) if (x is not None and str(x) != "") else default_v
            elif src == "Y":
                v = str(y) if (y is not None and str(y) != "") else default_v
            elif src == "VAL":
                v = str(val) if (val is not None and str(val) != "") else default_v
            elif src == "CMD":
                v = str(cmd) if (cmd is not None and str(cmd) != "") else default_v
            elif src == "CUSTOM1":
                v = str(custom1) if (custom1 is not None and str(custom1) != "") else default_v
            elif src == "CUSTOM2":
                v = str(custom2) if (custom2 is not None and str(custom2) != "") else default_v
            else:
                v = default_v
            values.append(v)

        return f"{start_m}{sep.join(values)}{end_m}"

    def send_protocol(self, cmd="D", pin="0", x=None, y=None, val=None,
                      custom1="", custom2=""):
        pkt = self.format_packet(
            cmd=cmd, pin=pin, x=x, y=y, val=val,
            custom1=custom1, custom2=custom2
        )
        return self.bt.send(pkt)

    def _load_json(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def save_state(self):
        data = {
            "profiles": self.profiles,
            "active_profile": self.active_profile,
            "bt_settings": self.bt_settings,
            "protocol_settings": self.protocol_settings,
        }
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def on_stop(self):
        self.bt.shutdown()


if __name__ == '__main__':
    ProControllerApp().run()
