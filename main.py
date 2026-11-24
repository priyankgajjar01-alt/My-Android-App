import os
import json
import time
import math
import copy
import threading
from datetime import datetime

from kivy.config import Config
from kivy.utils import platform, escape_markup

# Enable full-screen dynamically for all Android screen sizes before Window loads
if platform == 'android':
    Config.set('graphics', 'fullscreen', 'auto')
    Config.set('graphics', 'borderless', '1')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.modalview import ModalView
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
if platform == 'android':
    Window.fullscreen = 'auto'
    Window.borderless = True


def apply_android_fullscreen(*args):
    """Apply edge-to-edge dark-navy fullscreen on Android (removes top white border on all screens)."""
    if not IS_ANDROID_APK:
        return
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread

        @run_on_ui_thread
        def _set_fullscreen():
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                View = autoclass('android.view.View')
                LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
                AndroidColor = autoclass('android.graphics.Color')
                ColorDrawable = autoclass('android.graphics.drawable.ColorDrawable')
                BuildVersion = autoclass('android.os.Build$VERSION')

                activity = PythonActivity.mActivity
                window = activity.getWindow()
                navy = AndroidColor.rgb(10, 20, 41)

                # Match window & system bars to dark-navy theme so no white border ever appears
                window.setBackgroundDrawable(ColorDrawable(navy))
                if BuildVersion.SDK_INT >= 21:
                    window.addFlags(LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                    window.setStatusBarColor(navy)
                    window.setNavigationBarColor(navy)

                # Extend cleanly into notch / punch-hole cutout area on tall displays
                if BuildVersion.SDK_INT >= 28:
                    lp = window.getAttributes()
                    lp.layoutInDisplayCutoutMode = (
                        LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
                    )
                    window.setAttributes(lp)

                # Fullscreen sticky mode for top bar across all Android screen sizes
                window.addFlags(LayoutParams.FLAG_FULLSCREEN)
                decor = window.getDecorView()
                flags = (
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )
                decor.setSystemUiVisibility(flags)
            except Exception:
                pass

        _set_fullscreen()
    except Exception:
        pass


# Color Palette (Light Navy Blue Translucent / Glass Theme)
CARD_BG = (0.12, 0.24, 0.44, 0.30)
CARD_BG_ACTIVE = (0.10, 0.36, 0.30, 0.48)
CARD_BORDER = (0.35, 0.60, 0.95, 0.38)
CARD_BORDER_ACTIVE = (0.30, 0.90, 0.60, 0.72)
INPUT_BG = (0.08, 0.16, 0.30, 0.65)
INPUT_LOCKED_BG = (0.05, 0.10, 0.20, 0.50)
MODAL_BG = (0.06, 0.13, 0.26, 0.97)
MINI_TERM_BG = (0.03, 0.07, 0.14, 0.80)
BTN_PRIMARY = (0.16, 0.42, 0.78, 0.85)
BTN_SUCCESS = (0.12, 0.55, 0.38, 0.88)
BTN_WARN = (0.72, 0.45, 0.12, 0.85)
BTN_DANGER = (0.68, 0.20, 0.24, 0.90)
TEXT_MAIN = (0.94, 0.97, 1.0, 1)
TEXT_MUTED = (0.62, 0.74, 0.90, 1)
TEXT_CYAN = (0.40, 0.86, 1.0, 1)

# Uniform Dashboard Card Sizing & Safe Margins
ROW_CARD_H = dp(88)
ROW_CARD_H_EDIT = dp(116)
ROW_GAP = dp(6)
TOP_SAFE_SPACE = dp(35)
BOTTOM_SAFE_SPACE = dp(20)

# Packet Send Modes
MODE_SINGLE_10BOX = "10-Box (Single Widget)"
MODE_ALL_COMBINED = "All Widgets (Combined)"
SEND_MODE_OPTIONS = (MODE_SINGLE_10BOX, MODE_ALL_COMBINED)
COMBINED_STYLE_OPTIONS = ("Values Only", "Pin=Value")

# Combined Start-End Wrapper Pairs, Separators, and Newline Options
WRAPPER_PAIRS = {
    "< >": ("<", ">"),
    "[ ]": ("[", "]"),
    "{ }": ("{", "}"),
    "$ #": ("$", "#"),
    "None": ("", ""),
}
WRAPPER_OPTIONS = ("< >", "[ ]", "{ }", "$ #", "None")
SEPARATOR_OPTIONS = (":", ",", ";", "|", "-")
NEWLINE_OPTIONS = ("\\n", "None")

# English App Working Guide text (displayed from Log -> Guide button)
APP_GUIDE_TEXT = (
    "[b][color=66ddff]1. BLUETOOTH CONNECTION[/color][/b]\n"
    "- Pair your HC-05 module in your phone's Bluetooth settings first.\n"
    "- Tap the top-left 'HC05 CONTROLLER' status box on the Dashboard to open Bluetooth Connection.\n"
    "- Select a Paired device, tap 'Scan Nearby', or enter the MAC address and enable 'Auto-Connect'.\n"
    "- When the app is closed and reopened, it automatically reconnects to the saved MAC.\n\n"

    "[b][color=66ddff]2. DYNAMIC DASHBOARD & WIDGETS[/color][/b]\n"
    "- Tap '+ Widget' on the top bar to add Switch, Push Button, Slider (PWM), Joystick, or Sensor Display.\n"
    "- Switch, Push Button, and Sensor Display take half width (2 per row); Slider and Joystick use full width.\n"
    "- Tap 'Edit UI' beside the profile selector to reorder, edit settings, or delete any widget.\n"
    "- All widget states (ON/OFF, Slider values, etc.) are automatically saved and restored on reopen.\n\n"

    "[b][color=66ddff]3. PROJECT PROFILES[/color][/b]\n"
    "- Use the Profile dropdown or 'Profiles' button to manage separate layouts.\n"
    "- You can create new blank profiles or save a copy of your current layout anytime.\n\n"

    "[b][color=66ddff]4. PACKET SEND FORMAT (FORMAT SCREEN)[/color][/b]\n"
    "- [b]10-Box (Single Widget):[/b] Sends only the widget you tap/move using up to 10 customizable boxes (PIN, X, Y, VAL, CMD, TEXT/MSG, CUSTOM1-4, or OFF).\n"
    "- [b]All Widgets (Combined):[/b] Sends the live values of EVERY widget on the Dashboard together in ONE single packet.\n"
    "- Joystick always sends X and Y together in a single packet.\n"
    "- Configure 3 packet options: Start-End pair (< >, [ ], { }, $ #, None), Separator (:, ,, ;, |, -), and Newline (\\n or None).\n\n"

    "[b][color=66ddff]5. REPLY HANDSHAKE & TIMEOUT[/color][/b]\n"
    "- Turn ON 'Wait for Controller Reply' in Format settings so the app waits for a controller reply before sending the next packet.\n"
    "- Tap 'Edit' to change the Expected Reply (e.g. OK, or leave blank for any reply) and Wait Timeout in seconds.\n"
    "- If no reply arrives within the timeout, a red error 'Controller not responding' appears.\n"
    "- Tap 'Unlock' in Terminal anytime to clear the queue and unlock immediately.\n\n"

    "[b][color=66ddff]6. SENSOR DISPLAY RECEIVE FORMAT (SYNCED 2-BOX)[/color][/b]\n"
    "- Sensor Display widgets update automatically in real time as soon as the controller connects and sends data.\n"
    "- The receive parser STRICTLY uses the Start-End pair and Separator saved in Format settings:\n"
    "  [b][color=55ff99][Start]pin[Separator]value[End]\\n[/color][/b]\n"
    "- Example (Start-End='< >', Sep=':'):  <0:28.5>\\n\n"
    "- Example (Start-End='< >', Sep=','):  <0,28.5>\\n\n"
    "- Example (Start-End='[ ]', Sep=';'):  [0;28.5]\\n\n"
    "- Messages that do not match your saved 2-box format (such as 'OK') are ignored by Sensor Displays and shown only in the Terminal.\n\n"

    "[b][color=66ddff]7. TERMINAL / LOG VIEW[/color][/b]\n"
    "- [color=44ccff][TX][/color] = Sent to controller  |  [color=44ee88][RX][/color] = Received from controller\n"
    "- [color=ffcc55][SYS][/color] = System status     |  [color=ff5555][ERR][/color] = Timeout / Error\n"
    "- Use the bottom input bar to send manual commands, or type a 2-box sensor packet and tap 'Sim RX' to test in preview mode."
)

# Data source options for the 10-Box Packet Builder
BOX_OPTIONS = (
    "PIN",
    "X",
    "Y",
    "VAL",
    "CMD",
    "TEXT/MSG",
    "CUSTOM1",
    "CUSTOM2",
    "CUSTOM3",
    "CUSTOM4",
    "OFF",
)

DEFAULT_BOXES = [
    {"source": "PIN", "default": "0"},       # Box 1: Pin Number
    {"source": "X", "default": "0"},         # Box 2: Joystick X Value
    {"source": "Y", "default": "0"},         # Box 3: Joystick Y Value
    {"source": "VAL", "default": "0"},       # Box 4: Main Control Value
    {"source": "CUSTOM1", "default": "0"},   # Box 5: Custom Field 1
    {"source": "CUSTOM2", "default": "0"},   # Box 6: Custom Field 2
    {"source": "OFF", "default": "0"},       # Box 7: Selectable / Message
    {"source": "OFF", "default": "0"},       # Box 8: Selectable / Message
    {"source": "OFF", "default": "0"},       # Box 9: Selectable / Message
    {"source": "OFF", "default": "0"},       # Box 10: Selectable / Message
]

# Full-width widget types (all others render at half-width, 2 per row)
FULL_WIDTH_TYPES = ("Slider", "Joystick")

# Default project profile (single Home Automation starter profile)
DEFAULT_PROFILES = {
    "Home Automation": [
        {
            "id": "w1", "type": "Switch", "name": "Main Light",
            "pin": "13", "cmd": "D",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "255",
            "custom1": "", "custom2": "", "custom3": "", "custom4": "", "unit": ""
        },
        {
            "id": "w3", "type": "Push Button", "name": "Door Bell",
            "pin": "7", "cmd": "D",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "1",
            "custom1": "", "custom2": "", "custom3": "", "custom4": "", "unit": ""
        },
        {
            "id": "w2", "type": "Slider", "name": "Fan Speed (PWM)",
            "pin": "9", "cmd": "A",
            "val_on": "255", "val_off": "0", "min_val": "0", "max_val": "255",
            "custom1": "", "custom2": "", "custom3": "", "custom4": "", "unit": ""
        },
        {
            "id": "w4", "type": "Sensor Display", "name": "Room Temp",
            "pin": "0", "cmd": "R",
            "val_on": "1", "val_off": "0", "min_val": "0", "max_val": "100",
            "custom1": "", "custom2": "", "custom3": "", "custom4": "", "unit": "C"
        },
    ]
}


def safe_int(val, default=0):
    """Safely convert a value to an integer with a fallback default."""
    try:
        return int(str(val).strip())
    except Exception:
        return default


def safe_float(val, default=3.0, min_v=0.5, max_v=120.0):
    """Safely convert a value to a bounded float for timeout settings."""
    try:
        f = float(str(val).strip())
        if f < min_v:
            return min_v
        if f > max_v:
            return max_v
        return f
    except Exception:
        return default


def markers_to_wrapper_label(start_m, end_m):
    """Find matching Start-End dropdown label for stored start and end markers."""
    for label, (sm, em) in WRAPPER_PAIRS.items():
        if sm == start_m and em == end_m:
            return label
    return "None" if (not start_m and not end_m) else "< >"


# ==========================================
# Custom Glass / Translucent UI Components
# ==========================================
class GlassBox(BoxLayout):
    """Rounded translucent container with an inset border so ScrollView never clips it."""
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
        if self.width > dp(2) and self.height > dp(2):
            pad = dp(0.8)
            self._border.rounded_rectangle = (
                self.x + pad,
                self.y + pad,
                self.width - pad * 2,
                self.height - pad * 2,
                max(0, r - pad)
            )


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
    """Styled TextInput with text selection, handles, and copy/paste completely disabled."""
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
        radius = min(self.width, self.height) * 0.45
        knob_r = max(dp(15), radius * 0.30)
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
# HC-05 Bluetooth Manager (Strict Wait-for-Reply + Timeout + Auto-Connect)
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

        # Strict Wait-for-Reply (ACK handshake) + Timeout state
        self.wait_for_reply = False
        self.expected_reply = "OK"
        self.reply_timeout = 3.0
        self._waiting_ack = False
        self._timeout_ev = None
        self._tx_queue = []
        self._tx_lock = threading.Lock()

        self._stop_flag = False
        self._lock = threading.Lock()
        self._br = None

        if IS_ANDROID_APK:
            self._request_android_permissions()
        else:
            self._emit_log("SYS", "Preview Mode active (Tap top-left status box to connect Demo).")

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
        if ending_key == "None":
            self.line_ending = ""
        else:
            self.line_ending = "\n"

    def _cancel_timer_locked(self):
        if self._timeout_ev is not None:
            Clock.unschedule(self._timeout_ev)
            self._timeout_ev = None

    def _start_timer_locked(self):
        self._cancel_timer_locked()
        self._timeout_ev = Clock.schedule_once(self._on_reply_timeout, self.reply_timeout)

    def _on_reply_timeout(self, dt):
        """Fired when controller does not reply within the configured timeout seconds."""
        timed_out = False
        dropped = 0
        t_sec = self.reply_timeout
        with self._tx_lock:
            if self._waiting_ack:
                timed_out = True
                dropped = len(self._tx_queue)
                self._tx_queue.clear()
                self._waiting_ack = False
                self._timeout_ev = None

        if timed_out:
            extra = f" ({dropped} queued dropped)" if dropped > 0 else ""
            self._emit_log("ERR", f"Controller not responding (no reply in {t_sec:g}s){extra}")

    def set_reply_config(self, wait_enabled, expected_reply, reply_timeout=3.0):
        pending_flush = []
        with self._tx_lock:
            self.wait_for_reply = bool(wait_enabled)
            self.expected_reply = str(expected_reply).strip()
            self.reply_timeout = safe_float(reply_timeout, default=3.0)
            if not self.wait_for_reply:
                self._cancel_timer_locked()
                self._waiting_ack = False
                pending_flush = list(self._tx_queue)
                self._tx_queue.clear()
        for cmd in pending_flush:
            if self.connected:
                self._transmit_now(cmd)

    def unlock_queue(self):
        """Force-unlock waiting state and clear any pending queued messages."""
        with self._tx_lock:
            self._cancel_timer_locked()
            cleared = len(self._tx_queue)
            self._tx_queue.clear()
            self._waiting_ack = False
        self._emit_log("SYS", f"Reply wait unlocked (cleared {cleared} queued packets).")

    def simulate_rx(self, text=""):
        """Manual RX trigger for testing sensor updates and reply handshake in Preview mode."""
        reply = text.strip() if text and text.strip() else (self.expected_reply or "OK")
        self._handle_incoming_line(reply)

    def get_paired_devices(self):
        if not IS_ANDROID_APK:
            return [
                ("HC-05 Controller (Demo)", "00:21:13:00:AB:CD"),
                ("HC-05 Module 2 (Demo)", "98:D3:31:F5:12:44")
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
            with self._tx_lock:
                self._cancel_timer_locked()
                self._waiting_ack = False
                self._tx_queue.clear()
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

            with self._tx_lock:
                self._cancel_timer_locked()
                self._waiting_ack = False
                self._tx_queue.clear()

            self._emit_status(True, f"Connected ({self.mac_address[-5:]})")
            self._emit_log("SYS", f"HC-05 Connected: {self.mac_address}")

            threading.Thread(target=self._read_loop, daemon=True).start()

        except Exception as e:
            self.connected = False
            self.connecting = False
            self._close_socket()
            self._emit_status(False, "Disconnected")
            self._emit_log("SYS", f"Connection failed: {e}")

    def _handle_incoming_line(self, line):
        """Process a received line: log, update 2-box sensors, and release strict ACK wait."""
        clean_line = line.strip()
        self._emit_log("RX", clean_line)
        if self.on_rx_data:
            Clock.schedule_once(lambda dt, ln=clean_line: self.on_rx_data(ln))

        next_cmd = None
        unlocked = False
        with self._tx_lock:
            if self.wait_for_reply and self._waiting_ack:
                exp = self.expected_reply.strip()
                if exp == "" or exp == "*":
                    matched = True
                else:
                    matched = (clean_line.lower() == exp.lower())

                if matched:
                    self._cancel_timer_locked()
                    if self._tx_queue:
                        next_cmd = self._tx_queue.pop(0)
                        self._start_timer_locked()
                    else:
                        self._waiting_ack = False
                        unlocked = True

        if next_cmd is not None and self.connected:
            self._emit_log("SYS", "Reply matched -> Sending next queued packet.")
            ok = self._transmit_now(next_cmd)
            if not ok:
                with self._tx_lock:
                    self._cancel_timer_locked()
                    self._waiting_ack = False
        elif unlocked:
            self._emit_log("SYS", "Reply matched -> Ready for next packet.")

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
                                self._handle_incoming_line(line)
                        elif b != 13:  # Ignore carriage return '\r'
                            buffer.append(b)
                else:
                    time.sleep(0.03)
            except Exception as e:
                self._emit_log("SYS", f"Connection lost: {e}")
                self.disconnect(silent=True)
                break

    def _transmit_now(self, cmd):
        if not self.connected:
            return False

        if not IS_ANDROID_APK:
            self._emit_log("TX", cmd)
            if self.wait_for_reply:
                exp_txt = self.expected_reply if self.expected_reply else "ANY"
                self._emit_log("SYS", f"Waiting '{exp_txt}' ({self.reply_timeout:g}s)...")
            return True

        try:
            payload = (cmd + self.line_ending).encode('utf-8')
            self.out_stream.write(payload)
            self.out_stream.flush()
            self._emit_log("TX", cmd)
            if self.wait_for_reply:
                exp_txt = self.expected_reply if self.expected_reply else "ANY"
                self._emit_log("SYS", f"Waiting '{exp_txt}' ({self.reply_timeout:g}s)...")
            return True
        except Exception as e:
            self._emit_log("SYS", f"TX Error: {e}")
            self.disconnect(silent=True)
            return False

    def send(self, command_str):
        cmd = str(command_str).strip()
        if not cmd:
            return False
        if not self.connected:
            self._emit_log("SYS", f"Not Connected (Tap status box first)! Packet: {cmd}")
            return False

        send_immediately = False
        with self._tx_lock:
            if self.wait_for_reply:
                if self._waiting_ack:
                    if len(self._tx_queue) < 50:
                        self._tx_queue.append(cmd)
                        exp_txt = self.expected_reply if self.expected_reply else "ANY"
                        self._emit_log(
                            "SYS",
                            f"HELD (Wait '{exp_txt}' | Q:{len(self._tx_queue)}): {cmd}"
                        )
                    else:
                        self._emit_log("SYS", "Queue full (50). Waiting for controller reply...")
                    return True
                else:
                    self._waiting_ack = True
                    self._start_timer_locked()
                    send_immediately = True
            else:
                send_immediately = True

        if send_immediately:
            ok = self._transmit_now(cmd)
            if not ok:
                with self._tx_lock:
                    self._cancel_timer_locked()
                    self._waiting_ack = False
            return ok
        return True

    def disconnect(self, silent=False):
        self.connected = False
        self.connecting = False
        with self._tx_lock:
            self._cancel_timer_locked()
            self._waiting_ack = False
            self._tx_queue.clear()
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
        time.sleep(0.8)
        while not self._stop_flag:
            if self.auto_connect and self.mac_address and not self.connected and not self.connecting:
                self._connect_worker()
            time.sleep(3.5)

    def shutdown(self):
        self._stop_flag = True
        if self._br:
            try:
                self._br.stop()
            except Exception:
                pass
        self.disconnect(silent=True)


# ==========================================
# Screen 1: Dynamic Custom Dashboard (Full Screen + 35dp Top & 20dp Bottom Safe Space)
# ==========================================
class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.edit_mode = False
        self.sensor_labels = {}  # pin -> list of (read_lbl, status_lbl, unit)

        root = BoxLayout(
            orientation='vertical',
            padding=[dp(10), TOP_SAFE_SPACE, dp(10), BOTTOM_SAFE_SPACE],
            spacing=dp(6)
        )

        # --- Row 1: Top App Bar (4 Aligned Items: BT Status Box, + Widget, Format, Log) ---
        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(5))

        bt_badge = ClickableGlassBox(
            orientation='vertical',
            padding=[dp(8), dp(3)],
            bg_color=(0.08, 0.18, 0.34, 0.55),
            border_color=CARD_BORDER,
            radius=11,
            size_hint_x=0.39
        )
        bt_badge.bind(on_release=lambda x: self.go_to('connection'))

        self.title_lbl = Label(
            text="HC05 CONTROLLER",
            font_size=dp(12),
            bold=True,
            color=TEXT_MAIN,
            halign='left',
            valign='bottom',
            shorten=True
        )
        self.title_lbl.bind(size=self.title_lbl.setter('text_size'))

        self.status_lbl = Label(
            text="OFF: Disconnected",
            font_size=dp(10),
            color=(1.0, 0.45, 0.45, 1),
            halign='left',
            valign='top',
            shorten=True
        )
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))
        bt_badge.add_widget(self.title_lbl)
        bt_badge.add_widget(self.status_lbl)

        btn_add = GlassButton(
            text="+ Widget",
            font_size=11.5,
            bg_color=BTN_SUCCESS,
            border_color=CARD_BORDER_ACTIVE,
            radius=11,
            size_hint_x=0.24
        )
        btn_add.bind(on_release=self.add_new_widget)

        btn_fmt = GlassButton(
            text="Format",
            font_size=11.5,
            bg_color=(0.12, 0.32, 0.58, 0.65),
            radius=11,
            size_hint_x=0.21
        )
        btn_fmt.bind(on_release=lambda x: self.go_to('protocol'))

        btn_term = GlassButton(
            text="Log",
            font_size=11.5,
            bg_color=(0.12, 0.32, 0.58, 0.65),
            radius=11,
            size_hint_x=0.16
        )
        btn_term.bind(on_release=lambda x: self.go_to('terminal'))

        top_bar.add_widget(bt_badge)
        top_bar.add_widget(btn_add)
        top_bar.add_widget(btn_fmt)
        top_bar.add_widget(btn_term)
        root.add_widget(top_bar)

        # --- Row 2: Profile Selector + Edit UI + Profiles ---
        prof_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(5))
        self.sp_profile = Spinner(
            text='Home Automation',
            values=('Home Automation',),
            background_normal='',
            background_color=(0.12, 0.28, 0.52, 0.65),
            color=TEXT_MAIN,
            font_size=dp(12.5),
            bold=True,
            size_hint_x=0.48
        )
        self.sp_profile.bind(text=self.on_profile_selected)

        self.btn_edit = GlassButton(
            text="Edit UI",
            font_size=12,
            bg_color=CARD_BG,
            radius=10,
            size_hint_x=0.26
        )
        self.btn_edit.bind(on_release=self.toggle_edit_mode)

        btn_prof_mgr = GlassButton(
            text="Profiles",
            font_size=12,
            bg_color=CARD_BG,
            radius=10,
            size_hint_x=0.26
        )
        btn_prof_mgr.bind(on_release=lambda x: self.go_to('profiles'))

        prof_row.add_widget(self.sp_profile)
        prof_row.add_widget(self.btn_edit)
        prof_row.add_widget(btn_prof_mgr)
        root.add_widget(prof_row)

        # --- Row 3: Send All (Combined Mode) & Mini Log View Strip (Placed Above Widgets) ---
        self.top_strip = BoxLayout(
            orientation='vertical',
            spacing=dp(6),
            size_hint_y=None,
            height=dp(36)
        )
        self.top_strip.bind(minimum_height=self.top_strip.setter('height'))

        mini_term = GlassButton(
            text="Terminal: Ready...",
            font_size=11,
            bold=False,
            bg_color=MINI_TERM_BG,
            border_color=CARD_BORDER,
            radius=10,
            size_hint_y=None,
            height=dp(36)
        )
        mini_term.lbl.halign = 'left'
        mini_term.padding = [dp(10), 0]
        mini_term.bind(on_release=lambda x: self.go_to('terminal'))
        self.mini_log_btn = mini_term
        self.top_strip.add_widget(mini_term)
        root.add_widget(self.top_strip)

        # --- Scrollable Dynamic Widgets Container (Tiny 2-3dp anti-clip margin only) ---
        self.scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        self.widget_container = BoxLayout(
            orientation='vertical',
            spacing=ROW_GAP,
            size_hint_y=None,
            padding=[dp(2), dp(3), dp(2), dp(3)]
        )
        self.widget_container.bind(minimum_height=self.widget_container.setter('height'))
        self.scroll.add_widget(self.widget_container)
        root.add_widget(self.scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh_profile_spinner()
        self.rebuild_dashboard(reset_scroll=True)

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
            self.rebuild_dashboard(reset_scroll=True)

    def toggle_edit_mode(self, *args):
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.btn_edit.set_text("Done")
            self.btn_edit.set_colors(BTN_WARN, (1.0, 0.72, 0.30, 0.7))
        else:
            self.btn_edit.set_text("Edit UI")
            self.btn_edit.set_colors(CARD_BG, CARD_BORDER)
        self.rebuild_dashboard(reset_scroll=False)

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
            self.rebuild_dashboard(reset_scroll=False)

    def delete_widget(self, idx):
        app = App.get_running_app()
        wlist = app.get_active_widgets()
        if 0 <= idx < len(wlist):
            removed = wlist.pop(idx)
            app.remove_widget_state(removed.get("id", ""))
            app.save_state()
            self.rebuild_dashboard(reset_scroll=False)

    def _refresh_combined_bar(self):
        self.top_strip.clear_widgets()
        app = App.get_running_app()
        if app.protocol_settings.get("send_mode") == MODE_ALL_COMBINED:
            btn_all = GlassButton(
                text="Send All Screen Widgets (Combined)",
                font_size=13,
                bg_color=BTN_SUCCESS,
                border_color=CARD_BORDER_ACTIVE,
                size_hint_y=None,
                height=dp(38)
            )
            btn_all.bind(on_release=lambda x: app.send_all_widgets())
            self.top_strip.add_widget(btn_all)
            self.top_strip.add_widget(self.mini_log_btn)
            self.top_strip.height = dp(38) + dp(6) + dp(36)
        else:
            self.top_strip.add_widget(self.mini_log_btn)
            self.top_strip.height = dp(36)

    def _get_row_height(self):
        return ROW_CARD_H_EDIT if self.edit_mode else ROW_CARD_H

    def _flush_half_row(self, pending_half):
        """Place 1 or 2 half-width widgets into a uniform-height 2-column row."""
        if not pending_half:
            return
        row = BoxLayout(
            orientation='horizontal',
            spacing=ROW_GAP,
            size_hint_y=None,
            height=self._get_row_height()
        )
        for card in pending_half:
            card.size_hint = (0.5, 1)
            row.add_widget(card)
        if len(pending_half) == 1:
            row.add_widget(Widget(size_hint=(0.5, 1)))
        self.widget_container.add_widget(row)
        pending_half.clear()

    def rebuild_dashboard(self, reset_scroll=True):
        self.widget_container.clear_widgets()
        self.sensor_labels = {}
        self._refresh_combined_bar()
        app = App.get_running_app()
        wlist = app.get_active_widgets()

        if not wlist:
            empty = GlassBox(padding=dp(20), size_hint_y=None, height=dp(110))
            empty.add_widget(Label(
                text="No widgets in this profile.\nTap '+ Widget' above to add controls.",
                color=TEXT_MUTED,
                font_size=dp(14),
                halign='center'
            ))
            self.widget_container.add_widget(empty)
        else:
            pending_half = []
            for idx, w in enumerate(wlist):
                wtype = w.get("type", "Switch")
                if wtype in FULL_WIDTH_TYPES:
                    self._flush_half_row(pending_half)
                    if wtype == "Slider":
                        card = self._build_slider_card(idx, w)
                    else:
                        card = self._build_joystick_card(idx, w)
                    self.widget_container.add_widget(card)
                else:
                    if wtype == "Switch":
                        card = self._build_switch_card(idx, w)
                    elif wtype == "Push Button":
                        card = self._build_push_card(idx, w)
                    elif wtype == "Sensor Display":
                        card = self._build_sensor_card(idx, w)
                    else:
                        card = self._build_switch_card(idx, w)
                    pending_half.append(card)
                    if len(pending_half) == 2:
                        self._flush_half_row(pending_half)

            self._flush_half_row(pending_half)

        if reset_scroll:
            Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 1), 0)

    def _build_full_header(self, idx, w, subtitle):
        """Compact header for full-width widgets with optional edit row."""
        box = BoxLayout(orientation='vertical', spacing=dp(3), size_hint_y=None)
        box.height = dp(48) if self.edit_mode else dp(22)

        hdr = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
        safe_name = escape_markup(str(w.get('name', 'Control')))
        title = Label(
            text=safe_name,
            font_size=dp(13),
            bold=True,
            color=TEXT_MAIN,
            halign='left',
            valign='middle',
            shorten=True,
            size_hint_x=0.55
        )
        title.bind(size=title.setter('text_size'))

        sub_lbl = Label(
            text=str(subtitle),
            font_size=dp(10.5),
            color=TEXT_MUTED,
            halign='right',
            valign='middle',
            shorten=True,
            size_hint_x=0.45
        )
        sub_lbl.bind(size=sub_lbl.setter('text_size'))

        hdr.add_widget(title)
        hdr.add_widget(sub_lbl)
        box.add_widget(hdr)

        if self.edit_mode:
            ed_row = BoxLayout(size_hint_y=None, height=dp(23), spacing=dp(6))
            b_up = GlassButton(text="Up", font_size=11, bg_color=CARD_BG, radius=8)
            b_up.bind(on_release=lambda x, i=idx: self.move_widget(i, -1))
            b_dn = GlassButton(text="Dn", font_size=11, bg_color=CARD_BG, radius=8)
            b_dn.bind(on_release=lambda x, i=idx: self.move_widget(i, 1))
            b_ed = GlassButton(text="Edit", font_size=11, bg_color=BTN_PRIMARY, radius=8)
            b_ed.bind(on_release=lambda x, i=idx: self.edit_widget(i))
            b_dl = GlassButton(text="Delete", font_size=11, bg_color=BTN_DANGER, radius=8)
            b_dl.bind(on_release=lambda x, i=idx: self.delete_widget(i))
            ed_row.add_widget(b_up)
            ed_row.add_widget(b_dn)
            ed_row.add_widget(b_ed)
            ed_row.add_widget(b_dl)
            box.add_widget(ed_row)

        return box, sub_lbl

    def _build_compact_header(self, idx, w, left_text, right_text="",
                              right_color=TEXT_MUTED, right_bold=False):
        """Uniform 2-line header: Name on line 1; Pin|CMD (left) & State (right) on line 2."""
        box = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_y=None)
        box.height = dp(60) if self.edit_mode else dp(33)

        safe_name = escape_markup(str(w.get('name', 'Control')))
        name_lbl = Label(
            text=safe_name,
            font_size=dp(12.5),
            bold=True,
            color=TEXT_MAIN,
            size_hint_y=None,
            height=dp(17),
            halign='left',
            valign='middle',
            shorten=True
        )
        name_lbl.bind(size=name_lbl.setter('text_size'))
        box.add_widget(name_lbl)

        # Single combined row: Pin | CMD on LEFT, Status/State on RIGHT
        info_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(14),
            spacing=dp(4)
        )
        left_lbl = Label(
            text=str(left_text),
            font_size=dp(10),
            color=TEXT_MUTED,
            halign='left',
            valign='middle',
            shorten=True,
            size_hint_x=0.56
        )
        left_lbl.bind(size=left_lbl.setter('text_size'))

        right_lbl = Label(
            text=str(right_text),
            font_size=dp(10),
            bold=right_bold,
            color=right_color,
            halign='right',
            valign='middle',
            shorten=True,
            size_hint_x=0.44
        )
        right_lbl.bind(size=right_lbl.setter('text_size'))

        info_row.add_widget(left_lbl)
        info_row.add_widget(right_lbl)
        box.add_widget(info_row)

        if self.edit_mode:
            ed_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(4))
            b_up = GlassButton(text="<", font_size=11, bg_color=CARD_BG, radius=8)
            b_up.bind(on_release=lambda x, i=idx: self.move_widget(i, -1))
            b_dn = GlassButton(text=">", font_size=11, bg_color=CARD_BG, radius=8)
            b_dn.bind(on_release=lambda x, i=idx: self.move_widget(i, 1))
            b_ed = GlassButton(text="Ed", font_size=11, bg_color=BTN_PRIMARY, radius=8)
            b_ed.bind(on_release=lambda x, i=idx: self.edit_widget(i))
            b_dl = GlassButton(text="X", font_size=11, bg_color=BTN_DANGER, radius=8)
            b_dl.bind(on_release=lambda x, i=idx: self.delete_widget(i))
            ed_row.add_widget(b_up)
            ed_row.add_widget(b_dn)
            ed_row.add_widget(b_ed)
            ed_row.add_widget(b_dl)
            box.add_widget(ed_row)

        return box, right_lbl

    def _build_switch_card(self, idx, w):
        app = App.get_running_app()
        wid = w.get("id", str(idx))
        st = app.get_widget_state(wid)
        is_on = bool(st.get("on", False))
        cur_val = str(w.get("val_on", "1") if is_on else w.get("val_off", "0"))

        card = GlassBox(
            orientation='vertical',
            padding=[dp(8), dp(6)],
            spacing=dp(5),
            bg_color=CARD_BG_ACTIVE if is_on else CARD_BG,
            border_color=CARD_BORDER_ACTIVE if is_on else CARD_BORDER
        )
        left_txt = f"Pin {w.get('pin')} | {w.get('cmd', 'D')}"
        right_txt = f"ON ({cur_val})" if is_on else f"OFF ({cur_val})"
        hdr, state_lbl = self._build_compact_header(
            idx, w,
            left_text=left_txt,
            right_text=right_txt,
            right_color=(0.35, 0.96, 0.60, 1) if is_on else TEXT_MUTED,
            right_bold=True
        )
        card.add_widget(hdr)

        toggle_btn = GlassButton(
            text="TURN OFF" if is_on else "TURN ON",
            font_size=12,
            bg_color=BTN_SUCCESS if is_on else BTN_PRIMARY,
            border_color=CARD_BORDER_ACTIVE if is_on else (0.45, 0.72, 1.0, 0.45),
            radius=10,
            size_hint_y=1
        )

        def on_toggle(inst):
            cur = bool(app.get_widget_state(wid).get("on", False))
            new_state = not cur
            val = w.get("val_on", "1") if new_state else w.get("val_off", "0")
            app.set_widget_state(wid, {"on": new_state, "val": str(val)}, save_now=True)
            app.send_widget_action(
                cmd=w.get("cmd", "D"),
                pin=w.get("pin", "13"),
                val=val,
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", ""),
                custom3=w.get("custom3", ""),
                custom4=w.get("custom4", "")
            )
            if new_state:
                card.set_colors(CARD_BG_ACTIVE, CARD_BORDER_ACTIVE)
                state_lbl.text = f"ON ({val})"
                state_lbl.color = (0.35, 0.96, 0.60, 1)
                toggle_btn.set_text("TURN OFF")
                toggle_btn.set_colors(BTN_SUCCESS, CARD_BORDER_ACTIVE)
            else:
                card.set_colors(CARD_BG, CARD_BORDER)
                state_lbl.text = f"OFF ({val})"
                state_lbl.color = TEXT_MUTED
                toggle_btn.set_text("TURN ON")
                toggle_btn.set_colors(BTN_PRIMARY, (0.45, 0.72, 1.0, 0.45))

        toggle_btn.bind(on_release=on_toggle)
        card.add_widget(toggle_btn)
        return card

    def _build_push_card(self, idx, w):
        app = App.get_running_app()
        wid = w.get("id", str(idx))
        card = GlassBox(orientation='vertical', padding=[dp(8), dp(6)], spacing=dp(5))
        left_txt = f"Pin {w.get('pin')} | {w.get('cmd', 'D')}"
        hdr, state_lbl = self._build_compact_header(
            idx, w,
            left_text=left_txt,
            right_text=f"OFF ({w.get('val_off', '0')})",
            right_color=TEXT_MUTED,
            right_bold=True
        )
        card.add_widget(hdr)

        btn = GlassButton(
            text="HOLD / PRESS",
            font_size=12,
            bg_color=BTN_PRIMARY,
            radius=10,
            size_hint_y=1
        )

        def on_down(inst):
            val = w.get("val_on", "1")
            app.set_widget_state(wid, {"on": True, "val": str(val)}, save_now=False)
            card.set_colors(CARD_BG_ACTIVE, CARD_BORDER_ACTIVE)
            state_lbl.text = f"ON ({val})"
            state_lbl.color = (0.35, 0.96, 0.60, 1)
            inst.set_colors(BTN_SUCCESS, CARD_BORDER_ACTIVE)
            app.send_widget_action(
                cmd=w.get("cmd", "D"),
                pin=w.get("pin", "7"),
                val=val,
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", ""),
                custom3=w.get("custom3", ""),
                custom4=w.get("custom4", "")
            )

        def on_up(inst):
            val = w.get("val_off", "0")
            app.set_widget_state(wid, {"on": False, "val": str(val)}, save_now=True)
            card.set_colors(CARD_BG, CARD_BORDER)
            state_lbl.text = f"OFF ({val})"
            state_lbl.color = TEXT_MUTED
            inst.set_colors(BTN_PRIMARY, (0.45, 0.72, 1.0, 0.45))
            app.send_widget_action(
                cmd=w.get("cmd", "D"),
                pin=w.get("pin", "7"),
                val=val,
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", ""),
                custom3=w.get("custom3", ""),
                custom4=w.get("custom4", "")
            )

        btn.bind(on_press=on_down, on_release=on_up)
        card.add_widget(btn)
        return card

    def _build_sensor_card(self, idx, w):
        """Auto-updating live Sensor Display card with uniform row height."""
        app = App.get_running_app()
        pin = str(w.get("pin", "0")).strip()
        unit = w.get("unit", "")
        saved_rx = app.sensor_values.get(pin)

        rx_fmt = app.get_rx_format_string(pin, "val")
        card = GlassBox(orientation='vertical', padding=[dp(8), dp(6)], spacing=dp(5))
        hdr, rx_status = self._build_compact_header(
            idx, w,
            left_text=f"Pin {pin} | {rx_fmt}",
            right_text="LIVE RX" if saved_rx is not None else "WAIT",
            right_color=TEXT_CYAN if saved_rx is not None else TEXT_MUTED,
            right_bold=(saved_rx is not None)
        )
        card.add_widget(hdr)

        display_text = f"{saved_rx} {unit}".strip() if saved_rx is not None else f"-- {unit}".strip()
        read_lbl = Label(
            text=display_text,
            font_size=dp(21),
            bold=True,
            color=(0.35, 0.95, 0.65, 1),
            size_hint_y=1,
            halign='left',
            valign='middle',
            shorten=True
        )
        read_lbl.bind(size=read_lbl.setter('text_size'))
        card.add_widget(read_lbl)

        self.sensor_labels.setdefault(pin, []).append((read_lbl, rx_status, unit))
        return card

    def _build_slider_card(self, idx, w):
        """Full-width PWM Slider card matching the exact same height as all other cards."""
        app = App.get_running_app()
        wid = w.get("id", str(idx))
        mn = safe_int(w.get("min_val"), 0)
        mx = safe_int(w.get("max_val"), 255)
        if mx <= mn:
            mx = mn + 255
        saved_v = safe_int(app.get_widget_state(wid).get("val"), mn)
        saved_v = max(mn, min(mx, saved_v))

        card = GlassBox(
            orientation='vertical',
            padding=[dp(10), dp(6)],
            spacing=dp(4),
            size_hint_y=None,
            height=self._get_row_height()
        )
        sub = f"Pin {w.get('pin')} | {w.get('cmd', 'A')} ({mn}-{mx})"
        hdr, _ = self._build_full_header(idx, w, sub)
        card.add_widget(hdr)

        row = BoxLayout(size_hint_y=1, spacing=dp(8))
        val_lbl = Label(
            text=str(saved_v),
            font_size=dp(16),
            bold=True,
            color=TEXT_CYAN,
            size_hint_x=None,
            width=dp(48)
        )
        sld = Slider(min=mn, max=mx, value=saved_v, step=1)
        last_sent = {"t": 0.0, "v": saved_v}

        def send_slider(val, force=False):
            iv = int(round(val))
            val_lbl.text = str(iv)
            app.set_widget_state(wid, {"val": str(iv)}, save_now=force)
            now = time.time()
            if force or (iv != last_sent["v"] and (now - last_sent["t"]) >= 0.08):
                last_sent["t"] = now
                last_sent["v"] = iv
                app.send_widget_action(
                    cmd=w.get("cmd", "A"),
                    pin=w.get("pin", "9"),
                    val=str(iv),
                    custom1=w.get("custom1", ""),
                    custom2=w.get("custom2", ""),
                    custom3=w.get("custom3", ""),
                    custom4=w.get("custom4", "")
                )

        sld.bind(value=lambda inst, v: send_slider(v, force=False))

        def on_sld_touch_up(inst, touch):
            if touch.grab_current is inst or inst.collide_point(*touch.pos):
                send_slider(inst.value, force=True)

        sld.bind(on_touch_up=on_sld_touch_up)
        row.add_widget(sld)
        row.add_widget(val_lbl)
        card.add_widget(row)
        return card

    def _build_joystick_card(self, idx, w):
        """Full-width Joystick card aligned cleanly to 2 uniform row heights."""
        app = App.get_running_app()
        wid = w.get("id", str(idx))
        mn = safe_int(w.get("min_val"), 0)
        mx = safe_int(w.get("max_val"), 255)
        if mx <= mn:
            mx = mn + 255
        mid = int((mn + mx) / 2)
        pin = str(w.get("pin", "5"))
        st = app.get_widget_state(wid)
        init_x = st.get("x", str(mid))
        init_y = st.get("y", str(mid))

        joy_h = (ROW_CARD_H * 2 + ROW_GAP) + (dp(28) if self.edit_mode else 0)
        card = GlassBox(
            orientation='vertical',
            padding=[dp(10), dp(6)],
            spacing=dp(4),
            size_hint_y=None,
            height=joy_h
        )
        hdr, xy_lbl = self._build_full_header(idx, w, f"Pin {pin} | X:{init_x} Y:{init_y}")
        xy_lbl.color = TEXT_CYAN
        xy_lbl.bold = True
        card.add_widget(hdr)

        def on_joy_move(xv, yv, is_moving):
            xy_lbl.text = f"Pin {pin} | X:{xv} Y:{yv}"
            val_state = w.get("val_on", "1") if is_moving else w.get("val_off", "0")
            app.set_widget_state(
                wid,
                {"x": str(xv), "y": str(yv), "val": str(val_state)},
                save_now=(not is_moving)
            )
            app.send_widget_action(
                cmd=w.get("cmd", "A"),
                pin=pin,
                x=str(xv),
                y=str(yv),
                val=val_state,
                custom1=w.get("custom1", ""),
                custom2=w.get("custom2", ""),
                custom3=w.get("custom3", ""),
                custom4=w.get("custom4", "")
            )

        pad = JoystickPad(min_val=mn, max_val=mx, on_move=on_joy_move, size_hint=(1, 1))
        card.add_widget(pad)
        return card

    def apply_sensor_value(self, pin, val):
        """Update all visible Sensor Display cards bound to this pin."""
        if pin in self.sensor_labels:
            for read_lbl, rx_status, unit in self.sensor_labels[pin]:
                read_lbl.text = f"{val} {unit}".strip()
                rx_status.text = "LIVE RX"
                rx_status.bold = True
                rx_status.color = TEXT_CYAN

    def update_mini_log(self, ts, tag, msg):
        if tag == "ERR":
            self.mini_log_btn.set_colors(BTN_DANGER, (1.0, 0.42, 0.42, 0.95))
            self.mini_log_btn.lbl.bold = True
            self.mini_log_btn.set_text(f"ERROR: {msg}")
        else:
            self.mini_log_btn.set_colors(MINI_TERM_BG, CARD_BORDER)
            self.mini_log_btn.lbl.bold = False
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

        root = BoxLayout(
            orientation='vertical',
            padding=[dp(12), TOP_SAFE_SPACE, dp(12), BOTTOM_SAFE_SPACE],
            spacing=dp(10)
        )

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
        form = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, padding=[dp(2), dp(3), dp(2), dp(3)])
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
        pin_row.add_widget(self._linput("Pin Number (PIN)", "13", None, "in_pin"))
        c_box = BoxLayout(orientation='vertical', spacing=dp(4))
        c_box.add_widget(self._flbl("Command (CMD)"))
        self.sp_cmd = Spinner(
            text='D',
            values=('D', 'A', 'R'),
            size_hint_y=None, height=dp(44),
            background_normal='', background_color=INPUT_BG,
            color=TEXT_MAIN, font_size=dp(14)
        )
        c_box.add_widget(self.sp_cmd)
        pin_row.add_widget(c_box)
        card.add_widget(pin_row)

        val_row1 = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        val_row1.add_widget(self._linput("ON / Active Value (VAL)", "1", None, "in_on"))
        val_row1.add_widget(self._linput("OFF / Stop Value (VAL)", "0", None, "in_off"))
        card.add_widget(val_row1)

        val_row2 = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        val_row2.add_widget(self._linput("Min Value (Slider/Joy)", "0", "int", "in_min"))
        val_row2.add_widget(self._linput("Max Value (Slider/Joy)", "255", "int", "in_max"))
        card.add_widget(val_row2)

        cust_row1 = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        cust_row1.add_widget(self._linput("CUSTOM1 (Optional)", "Format default", None, "in_c1"))
        cust_row1.add_widget(self._linput("CUSTOM2 (Optional)", "Format default", None, "in_c2"))
        card.add_widget(cust_row1)

        cust_row2 = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(70))
        cust_row2.add_widget(self._linput("CUSTOM3 (Optional)", "Format default", None, "in_c3"))
        cust_row2.add_widget(self._linput("CUSTOM4 (Optional)", "Format default", None, "in_c4"))
        card.add_widget(cust_row2)

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
            self.sp_cmd.text = 'D'
        elif wtype in ('Slider', 'Joystick'):
            self.sp_cmd.text = 'A'
        elif wtype == 'Sensor Display':
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
            self.sp_cmd.text = "D"
            self.in_on.text = "1"
            self.in_off.text = "0"
            self.in_min.text = "0"
            self.in_max.text = "255"
            self.in_c1.text = ""
            self.in_c2.text = ""
            self.in_c3.text = ""
            self.in_c4.text = ""
            self.in_unit.text = ""
        else:
            w = app.get_active_widgets()[widget_index]
            self.hdr_lbl.text = f"Edit: {w.get('name', 'Widget')}"
            self.sp_type.text = w.get("type", "Switch")
            self.in_name.text = w.get("name", "")
            self.in_pin.text = str(w.get("pin", "13"))
            c = w.get("cmd", "D")
            self.sp_cmd.text = c if c in ('D', 'A', 'R') else "D"
            self.in_on.text = str(w.get("val_on", "1"))
            self.in_off.text = str(w.get("val_off", "0"))
            self.in_min.text = str(w.get("min_val", "0"))
            self.in_max.text = str(w.get("max_val", "255"))
            self.in_c1.text = str(w.get("custom1", ""))
            self.in_c2.text = str(w.get("custom2", ""))
            self.in_c3.text = str(w.get("custom3", ""))
            self.in_c4.text = str(w.get("custom4", ""))
            self.in_unit.text = str(w.get("unit", ""))

    def save_widget(self, *args):
        app = App.get_running_app()
        wlist = app.get_active_widgets()
        wtype = self.sp_type.text
        wdata = {
            "id": f"w_{int(time.time() * 1000)}",
            "type": wtype,
            "name": self.in_name.text.strip() or f"{wtype} {self.in_pin.text.strip() or '1'}",
            "pin": self.in_pin.text.strip() or "13",
            "cmd": self.sp_cmd.text.strip() or "D",
            "val_on": self.in_on.text.strip() or "1",
            "val_off": self.in_off.text.strip() or "0",
            "min_val": self.in_min.text.strip() or "0",
            "max_val": self.in_max.text.strip() or "255",
            "custom1": self.in_c1.text.strip(),
            "custom2": self.in_c2.text.strip(),
            "custom3": self.in_c3.text.strip(),
            "custom4": self.in_c4.text.strip(),
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
# Screen 3: Format Mode + Reply Handshake + 10-Box Builder (Save at Top)
# ==========================================
class ProtocolScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._loading = False
        self._expected_reply = "OK"
        self._reply_timeout = 3.0
        self.box_widgets = []

        root = BoxLayout(
            orientation='vertical',
            padding=[dp(12), TOP_SAFE_SPACE, dp(12), BOTTOM_SAFE_SPACE],
            spacing=dp(8)
        )

        # --- Top Bar ---
        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        btn_back = GlassButton(text="< Back", font_size=13, bg_color=CARD_BG, size_hint_x=None, width=dp(80))
        btn_back.bind(on_release=self.go_back)
        hdr = Label(text="Format & Reply Settings", font_size=dp(16), bold=True,
                    color=TEXT_MAIN, halign='left', valign='middle', shorten=True)
        hdr.bind(size=hdr.setter('text_size'))
        btn_reset = GlassButton(text="Reset", font_size=12, bg_color=BTN_WARN, size_hint_x=None, width=dp(62))
        btn_reset.bind(on_release=self.reset_default_boxes)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(hdr)
        top_bar.add_widget(btn_reset)
        root.add_widget(top_bar)

        # --- Fixed Top Save Button + Status Message ---
        btn_save = GlassButton(
            text="Save Format Settings",
            font_size=15,
            bg_color=BTN_SUCCESS,
            border_color=CARD_BORDER_ACTIVE,
            size_hint_y=None,
            height=dp(46)
        )
        btn_save.bind(on_release=self.save_format_click)
        root.add_widget(btn_save)

        self.msg_lbl = Label(
            text="",
            font_size=dp(12),
            color=(0.35, 0.95, 0.55, 1),
            size_hint_y=None,
            height=dp(18)
        )
        root.add_widget(self.msg_lbl)

        # --- Scrollable Format Cards ---
        scroll = ScrollView(bar_width=dp(4), do_scroll_x=False)
        body = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, padding=[dp(2), dp(3), dp(2), dp(3)])
        body.bind(minimum_height=body.setter('height'))

        # --- Card 1: Packet Send Mode Selector ---
        mode_card = GlassBox(orientation='vertical', padding=dp(10), spacing=dp(8), size_hint_y=None)
        mode_card.bind(minimum_height=mode_card.setter('height'))

        m_hdr = Label(
            text="Packet Send Format Mode",
            font_size=dp(13), bold=True, color=TEXT_CYAN,
            size_hint_y=None, height=dp(20), halign='left'
        )
        m_hdr.bind(size=m_hdr.setter('text_size'))
        mode_card.add_widget(m_hdr)

        self.sp_send_mode = Spinner(
            text=MODE_SINGLE_10BOX,
            values=SEND_MODE_OPTIONS,
            size_hint_y=None,
            height=dp(44),
            background_normal='',
            background_color=(0.14, 0.36, 0.64, 0.80),
            color=TEXT_MAIN,
            font_size=dp(13),
            bold=True
        )
        self.sp_send_mode.bind(text=self.on_any_change)
        mode_card.add_widget(self.sp_send_mode)

        cstyle_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        cs_lbl = Label(
            text="Combined Style:",
            font_size=dp(12), color=TEXT_MUTED,
            size_hint_x=0.42, halign='left', valign='middle'
        )
        cs_lbl.bind(size=cs_lbl.setter('text_size'))
        self.sp_combined_style = Spinner(
            text="Values Only",
            values=COMBINED_STYLE_OPTIONS,
            size_hint_x=0.58,
            background_normal='',
            background_color=INPUT_BG,
            color=TEXT_MAIN,
            font_size=dp(12),
            bold=True
        )
        self.sp_combined_style.bind(text=self.on_any_change)
        cstyle_row.add_widget(cs_lbl)
        cstyle_row.add_widget(self.sp_combined_style)
        mode_card.add_widget(cstyle_row)

        self.mode_tip_lbl = Label(
            text="",
            font_size=dp(10), color=TEXT_MUTED,
            size_hint_y=None, height=dp(28), halign='left', valign='middle'
        )
        self.mode_tip_lbl.bind(size=self.mode_tip_lbl.setter('text_size'))
        mode_card.add_widget(self.mode_tip_lbl)
        body.add_widget(mode_card)

        # --- Card 2: Wait-for-Reply (Locked Display + Popup Edit) ---
        ack_card = GlassBox(orientation='vertical', padding=dp(10), spacing=dp(8), size_hint_y=None)
        ack_card.bind(minimum_height=ack_card.setter('height'))

        ack_top = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        ack_hdr = Label(
            text="Reply Handshake & Timeout",
            font_size=dp(13), bold=True, color=TEXT_CYAN,
            halign='left', valign='middle'
        )
        ack_hdr.bind(size=ack_hdr.setter('text_size'))
        self.btn_edit_reply = GlassButton(
            text="Edit",
            font_size=12,
            bg_color=BTN_PRIMARY,
            size_hint_x=None,
            width=dp(78)
        )
        self.btn_edit_reply.bind(on_release=self.open_reply_editor)
        ack_top.add_widget(ack_hdr)
        ack_top.add_widget(self.btn_edit_reply)
        ack_card.add_widget(ack_top)

        sw_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        sw_lbl = Label(
            text="Wait for Controller Reply (ON/OFF)",
            font_size=dp(13), color=TEXT_MAIN, halign='left', valign='middle'
        )
        sw_lbl.bind(size=sw_lbl.setter('text_size'))
        self.sw_wait_reply = Switch(active=False, size_hint_x=None, width=dp(70))
        self.sw_wait_reply.bind(active=self.on_any_change)
        sw_row.add_widget(sw_lbl)
        sw_row.add_widget(self.sw_wait_reply)
        ack_card.add_widget(sw_row)

        # Read-only display boxes (can ONLY be changed via Edit button popup)
        rep_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(66))

        box_rep = BoxLayout(orientation='vertical', spacing=dp(4))
        l_rep = Label(text="Expected Reply", font_size=dp(11), color=TEXT_MUTED,
                      size_hint_y=None, height=dp(18), halign='left')
        l_rep.bind(size=l_rep.setter('text_size'))
        rep_val_card = GlassBox(bg_color=INPUT_LOCKED_BG, border_color=CARD_BORDER,
                                radius=10, padding=[dp(10), 0], size_hint_y=None, height=dp(42))
        self.lbl_reply_val = Label(text="OK", font_size=dp(14), bold=True, color=TEXT_MAIN,
                                   halign='left', valign='middle', shorten=True)
        self.lbl_reply_val.bind(size=self.lbl_reply_val.setter('text_size'))
        rep_val_card.add_widget(self.lbl_reply_val)
        box_rep.add_widget(l_rep)
        box_rep.add_widget(rep_val_card)

        box_tmo = BoxLayout(orientation='vertical', spacing=dp(4))
        l_tmo = Label(text="Wait Timeout", font_size=dp(11), color=TEXT_MUTED,
                      size_hint_y=None, height=dp(18), halign='left')
        l_tmo.bind(size=l_tmo.setter('text_size'))
        tmo_val_card = GlassBox(bg_color=INPUT_LOCKED_BG, border_color=CARD_BORDER,
                                radius=10, padding=[dp(10), 0], size_hint_y=None, height=dp(42))
        self.lbl_timeout_val = Label(text="3 s", font_size=dp(14), bold=True, color=TEXT_CYAN,
                                     halign='left', valign='middle', shorten=True)
        self.lbl_timeout_val.bind(size=self.lbl_timeout_val.setter('text_size'))
        tmo_val_card.add_widget(self.lbl_timeout_val)
        box_tmo.add_widget(l_tmo)
        box_tmo.add_widget(tmo_val_card)

        rep_grid.add_widget(box_rep)
        rep_grid.add_widget(box_tmo)
        ack_card.add_widget(rep_grid)

        ack_tip = Label(
            text="Tap 'Edit' to change Reply or Timeout. Sensor RX automatically matches Start-End & Sep set below.",
            font_size=dp(10), color=TEXT_MUTED,
            size_hint_y=None, height=dp(28), halign='left', valign='middle'
        )
        ack_tip.bind(size=ack_tip.setter('text_size'))
        ack_card.add_widget(ack_tip)
        body.add_widget(ack_card)

        # --- Card 3: 3-Box Packet Wrapper, Separator & Newline (TX & RX) ---
        wrap_card = GlassBox(orientation='vertical', padding=dp(10), spacing=dp(8), size_hint_y=None)
        wrap_card.bind(minimum_height=wrap_card.setter('height'))

        w_hdr = Label(text="Packet Wrapper, Separator & Newline (TX & RX)", font_size=dp(13), bold=True,
                      color=TEXT_CYAN, size_hint_y=None, height=dp(20), halign='left')
        w_hdr.bind(size=w_hdr.setter('text_size'))
        wrap_card.add_widget(w_hdr)

        m_grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(62))
        self.sp_wrapper = self._make_small_spinner(m_grid, "Start-End", "< >", WRAPPER_OPTIONS)
        self.sp_sep = self._make_small_spinner(m_grid, "Sep", ":", SEPARATOR_OPTIONS)
        self.sp_ending = self._make_small_spinner(m_grid, "Newline", "\\n", NEWLINE_OPTIONS)
        wrap_card.add_widget(m_grid)
        body.add_widget(wrap_card)

        # --- Card 4: Live Packet Preview (Auto-Sized) ---
        prev_card = GlassBox(orientation='vertical', padding=dp(12), spacing=dp(6),
                             bg_color=(0.04, 0.10, 0.20, 0.78), size_hint_y=None)
        prev_card.bind(minimum_height=prev_card.setter('height'))

        self.prev_hdr = Label(text="Live Packet Preview", font_size=dp(13), bold=True,
                              color=TEXT_CYAN, size_hint_y=None, height=dp(20), halign='left')
        self.prev_hdr.bind(size=self.prev_hdr.setter('text_size'))

        self.preview_lbl = Label(text="", font_size=dp(12), color=TEXT_MAIN,
                                 halign='left', valign='top', size_hint_y=None)
        self.preview_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        self.preview_lbl.bind(texture_size=lambda inst, s: setattr(inst, 'height', max(s[1] + dp(8), dp(64))))

        prev_card.add_widget(self.prev_hdr)
        prev_card.add_widget(self.preview_lbl)
        body.add_widget(prev_card)

        # --- Card 5: 10 Configurable Boxes (Used in 10-Box Mode) ---
        boxes_card = GlassBox(orientation='vertical', padding=dp(10), spacing=dp(7), size_hint_y=None)
        boxes_card.bind(minimum_height=boxes_card.setter('height'))

        boxes_title = Label(
            text="10-Box Builder (for Single Widget Mode)",
            font_size=dp(13), bold=True, color=TEXT_CYAN,
            size_hint_y=None, height=dp(20), halign='left'
        )
        boxes_title.bind(size=boxes_title.setter('text_size'))
        boxes_card.add_widget(boxes_title)

        b_hdr = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
        for txt, sx in [("Slot", 0.22), ("Select Data", 0.42), ("Value / Message", 0.36)]:
            l = Label(text=txt, font_size=dp(11), bold=True, color=TEXT_MUTED,
                      size_hint_x=sx, halign='left', valign='middle')
            l.bind(size=l.setter('text_size'))
            b_hdr.add_widget(l)
        boxes_card.add_widget(b_hdr)

        for i in range(10):
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            lbl = Label(
                text=f"Box {i + 1}",
                font_size=dp(12),
                bold=True,
                color=TEXT_MAIN,
                size_hint_x=0.22,
                halign='left',
                valign='middle',
                shorten=True
            )
            lbl.bind(size=lbl.setter('text_size'))

            sp = Spinner(
                text=DEFAULT_BOXES[i]["source"],
                values=BOX_OPTIONS,
                size_hint_x=0.42,
                background_normal='',
                background_color=(0.14, 0.32, 0.58, 0.70),
                color=TEXT_MAIN,
                font_size=dp(12),
                bold=True
            )
            sp.bind(text=self.on_any_change)

            inp = StyledInput(hint="Val / Msg", size_hint_x=0.36)
            inp.height = dp(42)
            inp.text = "0"
            inp.bind(text=self.on_any_change)

            row.add_widget(lbl)
            row.add_widget(sp)
            row.add_widget(inp)
            boxes_card.add_widget(row)
            self.box_widgets.append((sp, inp))

        tip = Label(
            text="Tip: Select 'TEXT/MSG' in any box to send a fixed message/value. Select 'OFF' to skip a box.",
            font_size=dp(11),
            color=TEXT_MUTED,
            size_hint_y=None,
            height=dp(32),
            halign='left',
            valign='middle'
        )
        tip.bind(size=tip.setter('text_size'))
        boxes_card.add_widget(tip)
        body.add_widget(boxes_card)

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
            font_size=dp(13),
            bold=True
        )
        sp.bind(text=self.on_any_change)
        col.add_widget(l)
        col.add_widget(sp)
        parent_grid.add_widget(col)
        return sp

    def _refresh_reply_labels(self):
        self.lbl_reply_val.text = self._expected_reply if self._expected_reply else "ANY (Blank)"
        self.lbl_timeout_val.text = f"{self._reply_timeout:g} s"

    def open_reply_editor(self, *args):
        """Open a top-anchored modal dialog with fresh editable inputs for Reply & Timeout."""
        modal = ModalView(
            size_hint=(0.92, None),
            height=dp(280),
            pos_hint={'center_x': 0.5, 'top': 0.90},
            background='',
            background_color=(0, 0, 0, 0),
            auto_dismiss=False
        )

        box = GlassBox(
            orientation='vertical',
            padding=dp(14),
            spacing=dp(10),
            bg_color=MODAL_BG,
            border_color=(0.45, 0.78, 1.0, 0.80),
            radius=16
        )

        title = Label(
            text="Edit Reply & Timeout",
            font_size=dp(16), bold=True, color=TEXT_CYAN,
            size_hint_y=None, height=dp(26), halign='left', valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        box.add_widget(title)

        l1 = Label(
            text="Expected Reply Message / Value (blank = any reply)",
            font_size=dp(11), color=TEXT_MUTED,
            size_hint_y=None, height=dp(18), halign='left'
        )
        l1.bind(size=l1.setter('text_size'))
        box.add_widget(l1)

        inp_rep = StyledInput(hint="e.g. OK, DONE, 1")
        inp_rep.text = self._expected_reply
        box.add_widget(inp_rep)

        l2 = Label(
            text="Wait Timeout in Seconds (0.5 to 120)",
            font_size=dp(11), color=TEXT_MUTED,
            size_hint_y=None, height=dp(18), halign='left'
        )
        l2.bind(size=l2.setter('text_size'))
        box.add_widget(l2)

        inp_tmo = StyledInput(hint="e.g. 3", input_filter='float')
        inp_tmo.text = f"{self._reply_timeout:g}"
        box.add_widget(inp_tmo)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        btn_cancel = GlassButton(text="Cancel", font_size=14, bg_color=BTN_DANGER)
        btn_save = GlassButton(text="Save", font_size=14, bg_color=BTN_SUCCESS)

        def on_save_modal(inst):
            self._expected_reply = inp_rep.text.strip()
            self._reply_timeout = safe_float(inp_tmo.text, default=3.0)
            self._refresh_reply_labels()
            self.save_format(silent=False)
            self.update_preview()
            self.msg_lbl.text = (
                f"Saved: Reply='{self._expected_reply or 'ANY'}', Timeout={self._reply_timeout:g}s"
            )
            modal.dismiss()

        btn_cancel.bind(on_release=lambda x: modal.dismiss())
        btn_save.bind(on_release=on_save_modal)
        btn_row.add_widget(btn_cancel)
        btn_row.add_widget(btn_save)
        box.add_widget(btn_row)

        modal.add_widget(box)
        modal.open()

    def on_pre_enter(self):
        self._loading = True
        app = App.get_running_app()
        ps = app.protocol_settings

        smode = ps.get("send_mode", MODE_SINGLE_10BOX)
        self.sp_send_mode.text = smode if smode in SEND_MODE_OPTIONS else MODE_SINGLE_10BOX
        cstyle = ps.get("combined_style", "Values Only")
        self.sp_combined_style.text = cstyle if cstyle in COMBINED_STYLE_OPTIONS else "Values Only"

        self.sw_wait_reply.active = bool(ps.get("wait_for_reply", False))
        self._expected_reply = str(ps.get("expected_reply", "OK")).strip()
        self._reply_timeout = safe_float(ps.get("reply_timeout", 3.0))
        self._refresh_reply_labels()

        s_mark = ps.get("start_marker", "<")
        e_mark = ps.get("end_marker", ">")
        self.sp_wrapper.text = markers_to_wrapper_label(s_mark, e_mark)
        sep = ps.get("separator", ":")
        self.sp_sep.text = sep if sep in SEPARATOR_OPTIONS else ":"
        le = ps.get("line_ending", "\\n")
        self.sp_ending.text = "None" if le == "None" else "\\n"

        boxes = ps.get("boxes") or copy.deepcopy(DEFAULT_BOXES)
        for i in range(10):
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
        start_m, end_m = WRAPPER_PAIRS.get(self.sp_wrapper.text, ("<", ">"))
        return {
            "send_mode": self.sp_send_mode.text,
            "combined_style": self.sp_combined_style.text,
            "start_marker": start_m,
            "separator": self.sp_sep.text,
            "end_marker": end_m,
            "line_ending": self.sp_ending.text,
            "wait_for_reply": self.sw_wait_reply.active,
            "expected_reply": self._expected_reply,
            "reply_timeout": self._reply_timeout,
            "boxes": boxes,
        }

    def on_any_change(self, *args):
        if self._loading:
            return
        self.save_format(silent=True)
        self.update_preview()

    def update_preview(self):
        if self._loading:
            return
        app = App.get_running_app()
        cfg = self._collect_settings()
        t_val = cfg["reply_timeout"]
        rx_fmt = app.get_rx_format_string("pin", "value", settings=cfg)
        nl_txt = "" if cfg["line_ending"] == "None" else "\\n"
        if cfg["wait_for_reply"]:
            ack_str = f"ON (Reply: '{cfg['expected_reply'] or 'ANY'}', Timeout: {t_val:g}s)"
        else:
            ack_str = "OFF"

        if cfg["send_mode"] == MODE_ALL_COMBINED:
            self.mode_tip_lbl.text = (
                "All Widgets Mode: Sends every dashboard widget's current value together in ONE message."
            )
            self.prev_hdr.text = f"Live Preview: All Widgets ({app.active_profile})"
            pkt = app.build_combined_packet(settings=cfg)
            order_lines = app.get_combined_slot_map()
            order_str = ", ".join(order_lines) if order_lines else "No widgets on screen"
            self.preview_lbl.text = (
                f"Packet:   {pkt}{nl_txt}\n"
                f"Order:    {order_str}\n"
                f"SensorRX: {rx_fmt}\\n (Synced 2-Box)\n"
                f"Wait ACK: {ack_str}"
            )
        else:
            self.mode_tip_lbl.text = (
                "10-Box Mode: Sends only the tapped/moved widget using the 10-Box layout below."
            )
            self.prev_hdr.text = "Live Preview: 10-Box (Single Widget)"
            p_joy = app.format_packet(cmd="A", pin="5", x="210", y="180", val="1", settings=cfg)
            p_sw = app.format_packet(cmd="D", pin="13", val="1", settings=cfg)
            p_sld = app.format_packet(cmd="A", pin="9", val="150", settings=cfg)
            self.preview_lbl.text = (
                f"Joystick: {p_joy}{nl_txt}\n"
                f"Switch:   {p_sw}{nl_txt}\n"
                f"Slider:   {p_sld}{nl_txt}\n"
                f"SensorRX: {rx_fmt}\\n (Synced 2-Box)\n"
                f"Wait ACK: {ack_str}"
            )

    def reset_default_boxes(self, *args):
        self._loading = True
        self.sp_send_mode.text = MODE_SINGLE_10BOX
        self.sp_combined_style.text = "Values Only"
        self.sw_wait_reply.active = False
        self._expected_reply = "OK"
        self._reply_timeout = 3.0
        self._refresh_reply_labels()
        self.sp_wrapper.text = "< >"
        self.sp_sep.text = ":"
        self.sp_ending.text = "\\n"
        for i in range(10):
            sp, inp = self.box_widgets[i]
            sp.text = DEFAULT_BOXES[i]["source"]
            inp.text = DEFAULT_BOXES[i]["default"]
        self._loading = False
        self.save_format(silent=False)
        self.update_preview()
        self.msg_lbl.text = "Default Format Settings Restored!"

    def save_format_click(self, *args):
        self.save_format(silent=False)

    def save_format(self, silent=False):
        app = App.get_running_app()
        cfg = self._collect_settings()
        app.protocol_settings = cfg
        app.bt.set_line_ending(cfg["line_ending"])
        app.bt.set_reply_config(
            cfg["wait_for_reply"],
            cfg["expected_reply"],
            cfg["reply_timeout"]
        )
        app.save_state()
        if not silent:
            self.msg_lbl.text = "Format & Reply Settings Saved!"

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
        self._loading = False

        root = BoxLayout(
            orientation='vertical',
            padding=[dp(12), TOP_SAFE_SPACE, dp(12), BOTTOM_SAFE_SPACE],
            spacing=dp(10)
        )

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
        self.sw_auto.bind(active=self.on_auto_toggle)
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
        self.dev_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, padding=[dp(2), dp(3), dp(2), dp(3)])
        self.dev_box.bind(minimum_height=self.dev_box.setter('height'))
        scroll.add_widget(self.dev_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self._loading = True
        app = App.get_running_app()
        self.in_mac.text = app.bt_settings.get("mac_address", "")
        self.sw_auto.active = app.bt_settings.get("auto_connect", True)
        self._loading = False
        self.msg_lbl.text = ""
        self.load_paired()

    def on_auto_toggle(self, inst, val):
        if self._loading:
            return
        app = App.get_running_app()
        app.bt_settings["auto_connect"] = bool(val)
        app.bt.set_config(app.bt_settings.get("mac_address", ""), bool(val))
        app.save_state()

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
        root = BoxLayout(
            orientation='vertical',
            padding=[dp(12), TOP_SAFE_SPACE, dp(12), BOTTOM_SAFE_SPACE],
            spacing=dp(10)
        )

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

        self.in_prof_name = StyledInput(hint="e.g. RC Car / Robot Arm")
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
        self.list_box = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, padding=[dp(2), dp(3), dp(2), dp(3)])
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
            src_profile = app.active_profile
            app.profiles[name] = copy.deepcopy(app.get_active_widgets())
            app.copy_profile_states(src_profile, name)
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
        app.remove_profile_states(pname)
        if app.active_profile == pname:
            app.active_profile = next(iter(app.profiles.keys()))
        app.save_state()
        self.refresh_list()

    def go_back(self, *args):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'dashboard'


# ==========================================
# Screen 6: Terminal / Log View (with App Working Guide Button)
# ==========================================
class TerminalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log_lines = []

        root = BoxLayout(
            orientation='vertical',
            padding=[dp(12), TOP_SAFE_SPACE, dp(12), BOTTOM_SAFE_SPACE],
            spacing=dp(8)
        )

        # --- Top Bar with Guide Button ---
        top_bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(5))
        btn_back = GlassButton(text="< Back", font_size=12, bg_color=CARD_BG, size_hint_x=None, width=dp(66))
        btn_back.bind(on_release=self.go_back)

        hdr = Label(text="Log", font_size=dp(17), bold=True,
                    color=TEXT_MAIN, halign='left', valign='middle', shorten=True)
        hdr.bind(size=hdr.setter('text_size'))

        btn_guide = GlassButton(text="Guide", font_size=11, bg_color=BTN_PRIMARY, size_hint_x=None, width=dp(56))
        btn_guide.bind(on_release=self.open_app_guide)

        btn_unlock = GlassButton(text="Unlock", font_size=11, bg_color=BTN_WARN, size_hint_x=None, width=dp(58))
        btn_unlock.bind(on_release=lambda x: App.get_running_app().bt.unlock_queue())

        btn_clear = GlassButton(text="Clear", font_size=11, bg_color=BTN_DANGER, size_hint_x=None, width=dp(52))
        btn_clear.bind(on_release=self.clear_log)

        top_bar.add_widget(btn_back)
        top_bar.add_widget(hdr)
        top_bar.add_widget(btn_guide)
        top_bar.add_widget(btn_unlock)
        top_bar.add_widget(btn_clear)
        root.add_widget(top_bar)

        # Quick test packet buttons
        quick_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        qb_all = GlassButton(text="Send All", font_size=11, bg_color=BTN_SUCCESS)
        qb_all.bind(on_release=lambda x: App.get_running_app().send_all_widgets())
        quick_row.add_widget(qb_all)

        tests = [
            ("Test SW", dict(cmd="D", pin="13", val="1")),
            ("Test PWM", dict(cmd="A", pin="9", val="150")),
        ]
        for lbl, kw in tests:
            qb = GlassButton(text=lbl, font_size=11, bg_color=CARD_BG)
            qb.bind(on_release=lambda x, k=kw: App.get_running_app().send_protocol(**k))
            quick_row.add_widget(qb)

        # Manual Sim RX button for testing sensor RX and reply handshake in Preview mode
        qb_rx = GlassButton(text="Sim RX", font_size=11, bg_color=BTN_WARN)
        qb_rx.bind(on_release=self.trigger_sim_rx)
        quick_row.add_widget(qb_rx)
        root.add_widget(quick_row)

        term_card = GlassBox(padding=dp(10), bg_color=(0.03, 0.06, 0.12, 0.80),
                             border_color=CARD_BORDER, radius=12)
        self.scroll = ScrollView(bar_width=dp(5), do_scroll_x=False)
        self.log_lbl = Label(
            text="[color=88aadd]Terminal Ready... Tap 'Guide' above to learn how this app works.[/color]",
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
        self.cmd_input = StyledInput(hint="Manual TX (or <0:28.5> & tap Sim RX)")
        self.cmd_input.bind(on_text_validate=self.send_manual)
        btn_send = GlassButton(text="Send", bg_color=BTN_PRIMARY, size_hint_x=None, width=dp(80))
        btn_send.bind(on_release=self.send_manual)
        cmd_row.add_widget(self.cmd_input)
        cmd_row.add_widget(btn_send)
        root.add_widget(cmd_row)

        self.add_widget(root)

    def on_pre_enter(self):
        app = App.get_running_app()
        ex_rx = app.get_rx_format_string("0", "28.5")
        self.cmd_input.hint_text = f"Manual TX (or {ex_rx} & tap Sim RX)"

    def open_app_guide(self, *args):
        """Show complete English documentation explaining how all app features work."""
        modal = ModalView(
            size_hint=(0.94, 0.86),
            background='',
            background_color=(0, 0, 0, 0),
            auto_dismiss=True
        )

        box = GlassBox(
            orientation='vertical',
            padding=dp(14),
            spacing=dp(10),
            bg_color=MODAL_BG,
            border_color=(0.45, 0.78, 1.0, 0.80),
            radius=16
        )

        hdr_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        title = Label(
            text="HC05 CONTROLLER - App Working Guide",
            font_size=dp(15),
            bold=True,
            color=TEXT_CYAN,
            halign='left',
            valign='middle',
            shorten=True
        )
        title.bind(size=title.setter('text_size'))
        btn_close = GlassButton(text="Close", font_size=12, bg_color=BTN_DANGER,
                                size_hint_x=None, width=dp(68))
        btn_close.bind(on_release=lambda x: modal.dismiss())
        hdr_row.add_widget(title)
        hdr_row.add_widget(btn_close)
        box.add_widget(hdr_row)

        guide_scroll = ScrollView(bar_width=dp(5), do_scroll_x=False)
        guide_lbl = Label(
            text=APP_GUIDE_TEXT,
            markup=True,
            font_size=dp(12.5),
            color=TEXT_MAIN,
            halign='left',
            valign='top',
            size_hint_y=None
        )
        guide_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w - dp(6), None)))
        guide_lbl.bind(texture_size=lambda inst, s: setattr(inst, 'height', s[1] + dp(16)))
        guide_scroll.add_widget(guide_lbl)
        box.add_widget(guide_scroll)

        modal.add_widget(box)
        modal.open()

    def trigger_sim_rx(self, *args):
        txt = self.cmd_input.text.strip()
        App.get_running_app().bt.simulate_rx(txt)
        if txt:
            self.cmd_input.text = ""

    def append_log(self, ts, tag, msg):
        safe_msg = escape_markup(str(msg))
        if tag == "TX":
            line = f"[color=7799bb]{ts}[/color] [b][color=44ccff][TX][/color][/b] {safe_msg}"
        elif tag == "RX":
            line = f"[color=7799bb]{ts}[/color] [b][color=44ee88][RX][/color][/b] {safe_msg}"
        elif tag == "ERR":
            line = f"[color=ff7777]{ts}[/color] [b][color=ff4444][ERR] {safe_msg}[/color][/b]"
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
# Main HC05 Controller Application
# ==========================================
class ProControllerApp(App):
    def build(self):
        self.title = "HC05 CONTROLLER"
        apply_android_fullscreen()

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

        # Restore persisted widget values/states and sensor readings
        loaded_states = saved.get("widget_states")
        self.widget_states = loaded_states if isinstance(loaded_states, dict) else {}
        loaded_sensors = saved.get("sensor_values")
        self.sensor_values = loaded_sensors if isinstance(loaded_sensors, dict) else {}

        self.bt_settings = saved.get("bt_settings") or {
            "mac_address": "",
            "auto_connect": True
        }

        # Upgrade any existing settings cleanly to unified Start-End + Newline (\n / None)
        ps = saved.get("protocol_settings") or {}
        old_boxes = ps.get("boxes")
        if isinstance(old_boxes, list) and len(old_boxes) > 0:
            boxes = old_boxes[:10]
            while len(boxes) < 10:
                boxes.append({"source": "OFF", "default": "0"})
        else:
            boxes = copy.deepcopy(DEFAULT_BOXES)

        raw_start = ps.get("start_marker", "<")
        raw_end = ps.get("end_marker", ">")
        pair_label = markers_to_wrapper_label(raw_start, raw_end)
        clean_start, clean_end = WRAPPER_PAIRS[pair_label]
        raw_le = ps.get("line_ending", "\\n")
        clean_le = "None" if raw_le == "None" else "\\n"

        self.protocol_settings = {
            "send_mode": ps.get("send_mode", MODE_SINGLE_10BOX),
            "combined_style": ps.get("combined_style", "Values Only"),
            "start_marker": clean_start,
            "separator": ps.get("separator", ":"),
            "end_marker": clean_end,
            "line_ending": clean_le,
            "wait_for_reply": bool(ps.get("wait_for_reply", False)),
            "expected_reply": str(ps.get("expected_reply", "OK")),
            "reply_timeout": safe_float(ps.get("reply_timeout", 3.0)),
            "boxes": boxes,
        }

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
            on_rx_data=self.handle_sensor_rx
        )
        self.bt.set_config(
            self.bt_settings.get("mac_address", ""),
            self.bt_settings.get("auto_connect", True)
        )
        self.bt.set_line_ending(self.protocol_settings.get("line_ending", "\\n"))
        self.bt.set_reply_config(
            self.protocol_settings.get("wait_for_reply", False),
            self.protocol_settings.get("expected_reply", "OK"),
            self.protocol_settings.get("reply_timeout", 3.0)
        )

        # Ensure dashboard widgets and saved states render immediately on startup
        Clock.schedule_once(lambda dt: self._init_dashboard_ready(), 0)
        return self.sm

    def on_start(self):
        apply_android_fullscreen()

    def on_resume(self):
        Clock.schedule_once(apply_android_fullscreen, 0.1)

    def _init_dashboard_ready(self):
        self.dashboard.refresh_profile_spinner()
        self.dashboard.rebuild_dashboard(reset_scroll=True)

    # --- Per-Profile Persistent Widget State Helpers ---
    def _state_key(self, wid, profile_name=None):
        pname = profile_name if profile_name is not None else self.active_profile
        return f"{pname}::{wid}"

    def get_widget_state(self, wid, profile_name=None):
        key = self._state_key(wid, profile_name)
        if key in self.widget_states:
            return self.widget_states[key]
        return self.widget_states.get(wid, {})

    def set_widget_state(self, wid, state_dict, save_now=False, profile_name=None):
        key = self._state_key(wid, profile_name)
        self.widget_states[key] = state_dict
        if save_now:
            self.save_state()
        else:
            self.schedule_save_state()

    def remove_widget_state(self, wid, profile_name=None):
        key = self._state_key(wid, profile_name)
        self.widget_states.pop(key, None)
        self.widget_states.pop(wid, None)

    def remove_profile_states(self, profile_name):
        prefix = f"{profile_name}::"
        for k in [k for k in self.widget_states if k.startswith(prefix)]:
            self.widget_states.pop(k, None)

    def copy_profile_states(self, src_profile, dst_profile):
        prefix = f"{src_profile}::"
        for k, v in list(self.widget_states.items()):
            if k.startswith(prefix):
                wid = k[len(prefix):]
                self.widget_states[f"{dst_profile}::{wid}"] = copy.deepcopy(v)

    def schedule_save_state(self, delay=0.25):
        Clock.unschedule(self._deferred_save)
        Clock.schedule_once(self._deferred_save, delay)

    def _deferred_save(self, dt):
        self.save_state()

    def get_rx_format_string(self, pin_txt="pin", val_txt="value", settings=None):
        """Return the active 2-box RX format string using saved Start-End pair and Separator."""
        cfg = settings if settings is not None else self.protocol_settings
        start_m = cfg.get("start_marker", "<")
        sep = cfg.get("separator", ":")
        end_m = cfg.get("end_marker", ">")
        return f"{start_m}{pin_txt}{sep}{val_txt}{end_m}"

    def handle_sensor_rx(self, line):
        """Strictly parse incoming 2-box sensor data using saved Start-End pair and Separator."""
        cfg = self.protocol_settings
        start_m = cfg.get("start_marker", "<")
        sep = cfg.get("separator", ":")
        end_m = cfg.get("end_marker", ">")

        s = line.strip()
        if start_m:
            if not s.startswith(start_m):
                return
            s = s[len(start_m):]
        if end_m:
            if not s.endswith(end_m):
                return
            s = s[:-len(end_m)]

        if not sep or sep not in s:
            return

        parts = s.split(sep)
        if len(parts) != 2:
            return

        pin = parts[0].strip()
        val = parts[1].strip()
        if not pin or not val:
            return

        self.sensor_values[pin] = val
        self.dashboard.apply_sensor_value(pin, val)
        self.schedule_save_state()

    def get_active_widgets(self):
        return self.profiles.setdefault(self.active_profile, [])

    def get_combined_slot_map(self, widgets=None):
        """Return human-readable index mapping for All Widgets Combined Mode."""
        wlist = widgets if widgets is not None else self.get_active_widgets()
        slots = []
        idx = 0
        for w in wlist:
            name = w.get("name", "Widget")
            if w.get("type") == "Joystick":
                slots.append(f"[{idx}]{name}_X")
                slots.append(f"[{idx + 1}]{name}_Y")
                idx += 2
            else:
                slots.append(f"[{idx}]{name}")
                idx += 1
        return slots

    def build_combined_packet(self, settings=None, widgets=None):
        """Build ONE packet containing the live values of all widgets on screen."""
        cfg = settings if settings is not None else self.protocol_settings
        start_m = cfg.get("start_marker", "<")
        sep = cfg.get("separator", ":")
        end_m = cfg.get("end_marker", ">")
        style = cfg.get("combined_style", "Values Only")
        wlist = widgets if widgets is not None else self.get_active_widgets()

        tokens = []
        for w in wlist:
            wid = w.get("id", "")
            wtype = w.get("type", "Switch")
            pin = str(w.get("pin", "0"))
            st = self.get_widget_state(wid)

            if wtype == "Joystick":
                mn = safe_int(w.get("min_val"), 0)
                mx = safe_int(w.get("max_val"), 255)
                if mx <= mn:
                    mx = mn + 255
                mid = str(int((mn + mx) / 2))
                xv = str(st.get("x", mid))
                yv = str(st.get("y", mid))
                if style == "Pin=Value":
                    tokens.append(f"{pin}X={xv}")
                    tokens.append(f"{pin}Y={yv}")
                else:
                    tokens.append(xv)
                    tokens.append(yv)
            elif wtype == "Slider":
                mn = str(safe_int(w.get("min_val"), 0))
                val = str(st.get("val", mn))
                tokens.append(f"{pin}={val}" if style == "Pin=Value" else val)
            elif wtype == "Sensor Display":
                val = str(self.sensor_values.get(pin, w.get("val_off", "0")))
                tokens.append(f"{pin}={val}" if style == "Pin=Value" else val)
            else:
                default_off = str(w.get("val_off", "0"))
                val = str(st.get("val", default_off))
                tokens.append(f"{pin}={val}" if style == "Pin=Value" else val)

        return f"{start_m}{sep.join(tokens)}{end_m}"

    def format_packet(self, cmd="D", pin="0", x=None, y=None, val=None,
                      custom1="", custom2="", custom3="", custom4="", settings=None):
        """Build the output packet string according to the active 10-box format."""
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
            elif src == "TEXT/MSG":
                v = default_v
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
            elif src == "CUSTOM3":
                v = str(custom3) if (custom3 is not None and str(custom3) != "") else default_v
            elif src == "CUSTOM4":
                v = str(custom4) if (custom4 is not None and str(custom4) != "") else default_v
            else:
                v = default_v
            values.append(v)

        return f"{start_m}{sep.join(values)}{end_m}"

    def send_protocol(self, cmd="D", pin="0", x=None, y=None, val=None,
                      custom1="", custom2="", custom3="", custom4=""):
        """Send a single-widget packet using the 10-box builder."""
        pkt = self.format_packet(
            cmd=cmd, pin=pin, x=x, y=y, val=val,
            custom1=custom1, custom2=custom2,
            custom3=custom3, custom4=custom4
        )
        return self.bt.send(pkt)

    def send_all_widgets(self):
        """Send one combined packet with all active dashboard widget values."""
        pkt = self.build_combined_packet()
        return self.bt.send(pkt)

    def send_widget_action(self, cmd="D", pin="0", x=None, y=None, val=None,
                           custom1="", custom2="", custom3="", custom4=""):
        """Route widget actions according to the selected Packet Send Format Mode."""
        if self.protocol_settings.get("send_mode") == MODE_ALL_COMBINED:
            return self.send_all_widgets()
        return self.send_protocol(
            cmd=cmd, pin=pin, x=x, y=y, val=val,
            custom1=custom1, custom2=custom2,
            custom3=custom3, custom4=custom4
        )

    def _load_json(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def save_state(self):
        Clock.unschedule(self._deferred_save)
        data = {
            "profiles": self.profiles,
            "active_profile": self.active_profile,
            "bt_settings": self.bt_settings,
            "protocol_settings": self.protocol_settings,
            "widget_states": self.widget_states,
            "sensor_values": self.sensor_values,
        }
        try:
            tmp_file = self.state_file + ".tmp"
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_file, self.state_file)
        except Exception:
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

    def on_pause(self):
        self.save_state()
        return True

    def on_stop(self):
        self.save_state()
        self.bt.shutdown()


if __name__ == '__main__':
    ProControllerApp().run()
