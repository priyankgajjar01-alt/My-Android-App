import json
import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex, platform
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty
from kivy.metrics import dp

# ==========================================
# ANDROID BLUETOOTH SETUP
# ==========================================
BluetoothAdapter = None
BluetoothDevice = None
UUID = None
InputStreamReader = None
BufferedReader = None

if platform == 'android':
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
        UUID = autoclass('java.util.UUID')
        InputStreamReader = autoclass('java.io.InputStreamReader')
        BufferedReader = autoclass('java.io.BufferedReader')
        try:
            from android.permissions import request_permissions
            request_permissions([
                'android.permission.BLUETOOTH_CONNECT',
                'android.permission.BLUETOOTH_SCAN',
                'android.permission.ACCESS_FINE_LOCATION'
            ])
        except Exception:
            pass
    except Exception as e:
        print("Android Pyjnius Import Error:", e)


# ==========================================
# CUSTOM WIDGETS
# ==========================================
class ProButton(Button):
    def __init__(self, bg_hex='#1e3a5f', **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.bg_hex = bg_hex
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(rgba=get_color_from_hex('#64ffda80'))
            else:
                Color(rgba=get_color_from_hex(self.bg_hex))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12])

    def set_bg_color(self, new_hex):
        self.bg_hex = new_hex
        self.update_canvas()


class CenteredTextInput(TextInput):
    """TextInput with vertical text centering"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(height=self._update_padding)

    def _update_padding(self, *args):
        pad = max(0, (self.height - self.line_height) / 2)
        self.padding_y = [pad, pad]


class ReconnectButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.is_connected = False
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(rgba=get_color_from_hex('#ffffff80'))
            else:
                Color(rgba=get_color_from_hex('#00c853' if self.is_connected else '#d32f2f'))
            radius = min(self.size[0], self.size[1]) / 2
            RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])

    def set_connected(self, connected):
        self.is_connected = connected
        self.update_canvas()


class GlowButton(Label):
    state = StringProperty('normal')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_touches = set()
        self.bind(pos=self.draw_button, size=self.draw_button, state=self.draw_button)

    def draw_button(self, *args):
        self.canvas.before.clear()
        pressed = self.state == 'down'
        self.color = get_color_from_hex('#0a192f') if pressed else get_color_from_hex('#64ffda')
        with self.canvas.before:
            if pressed:
                Color(rgba=get_color_from_hex('#64ffda40'))
                RoundedRectangle(
                    pos=(self.pos[0] - 5, self.pos[1] - 5),
                    size=(self.size[0] + 10, self.size[1] + 10),
                    radius=[22]
                )
                Color(rgba=get_color_from_hex('#64ffda'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
            else:
                Color(rgba=get_color_from_hex('#1e3a5f'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
                Color(rgba=get_color_from_hex('#0a192f'))
                RoundedRectangle(
                    pos=(self.pos[0] + 2, self.pos[1] + 2),
                    size=(self.size[0] - 4, self.size[1] - 4),
                    radius=[16]
                )

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.active_touches.add(touch.uid)
            self.state = 'down'
        return False

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            if touch.uid not in self.active_touches:
                self.active_touches.add(touch.uid)
                self.state = 'down'
        else:
            if touch.uid in self.active_touches:
                self.active_touches.remove(touch.uid)
                if not self.active_touches:
                    self.state = 'normal'
        return False

    def on_touch_up(self, touch):
        if touch.uid in self.active_touches:
            self.active_touches.remove(touch.uid)
            if not self.active_touches:
                self.state = 'normal'
        return False


class AutoCenterSlider(Slider):
    def __init__(self, center_value=10, **kwargs):
        super().__init__(**kwargs)
        self.center_value = center_value
        self.cursor_size = ('68dp', '68dp')
        self.background_width = '28dp'

    def on_touch_up(self, touch):
        if touch.grab_current == self:
            Clock.schedule_once(lambda dt: setattr(self, 'value', self.center_value), 0.05)
        return super().on_touch_up(touch)


class SliderCard(AnchorLayout):
    """Centered card container with card-centered slider and card-bound touch swiping."""

    def __init__(
        self,
        slider,
        swipe_orientation='vertical',
        trim_horizontal=0.0,
        trim_vertical=0.0,
        card_offset_x=0.0,
        card_offset_y=0.0,
        slider_offset_x=0.0,
        slider_offset_y=0.0,
        **kwargs
    ):
        super().__init__(anchor_x='center', anchor_y='center', **kwargs)
        self.slider = slider
        self.swipe_orientation = swipe_orientation
        self.trim_horizontal = float(trim_horizontal)
        self.trim_vertical = float(trim_vertical)
        self.card_offset_x = float(card_offset_x)
        self.card_offset_y = float(card_offset_y)
        self.slider_offset_x = float(slider_offset_x)
        self.slider_offset_y = float(slider_offset_y)
        self.active_touch_uid = None
        self.is_swiping = False

        self.slider.disabled = True
        self.bind(pos=self._layout_card, size=self._layout_card)
        self.slider.bind(size=self._layout_card)
        self.add_widget(self.slider)

    def _card_rect(self):
        x = self.x + self.trim_horizontal + self.card_offset_x
        w = max(dp(20), self.width - 2 * self.trim_horizontal)
        y = self.y + self.trim_vertical + self.card_offset_y
        h = max(dp(20), self.height - 2 * self.trim_vertical)
        return x, y, w, h

    def _layout_card(self, *args):
        cx, cy, cw, ch = self._card_rect()
        Clock.schedule_once(self._apply_slider_offset, 0)

        self.canvas.before.clear()
        with self.canvas.before:
            Color(rgba=get_color_from_hex('#64ffda45' if self.is_swiping else '#1e3a5f'))
            RoundedRectangle(pos=(cx, cy), size=(cw, ch), radius=[16])
            Color(rgba=get_color_from_hex('#0d2240'))
            RoundedRectangle(
                pos=(cx + 2, cy + 2),
                size=(max(0, cw - 4), max(0, ch - 4)),
                radius=[14]
            )

    def _apply_slider_offset(self, *args):
        cx, cy, cw, ch = self._card_rect()
        self.slider.center_x = (cx + cw / 2.0) + self.slider_offset_x
        self.slider.center_y = (cy + ch / 2.0) + self.slider_offset_y

    def collide_point(self, x, y):
        cx, cy, cw, ch = self._card_rect()
        return (cx <= x <= cx + cw) and (cy <= y <= cy + ch)

    def _set_value_from_pos(self, pos):
        if self.slider.max <= self.slider.min:
            return
        cx, cy, cw, ch = self._card_rect()
        if self.swipe_orientation == 'vertical':
            pad_y = min(dp(24), ch * 0.1)
            usable_h = max(1.0, ch - 2 * pad_y)
            ratio = (pos[1] - (cy + pad_y)) / usable_h
        else:
            pad_x = min(dp(24), cw * 0.1)
            usable_w = max(1.0, cw - 2 * pad_x)
            ratio = (pos[0] - (cx + pad_x)) / usable_w

        ratio = max(0.0, min(1.0, ratio))
        raw_val = self.slider.min + ratio * (self.slider.max - self.slider.min)
        if self.slider.step:
            stepped = round((raw_val - self.slider.min) / self.slider.step) * self.slider.step + self.slider.min
            new_val = max(self.slider.min, min(self.slider.max, stepped))
        else:
            new_val = raw_val

        if isinstance(self.slider.value, int) or (self.slider.step and float(self.slider.step).is_integer()):
            new_val = int(round(new_val))
        self.slider.value = new_val

    def on_touch_down(self, touch):
        if self.active_touch_uid is None and self.collide_point(*touch.pos):
            self.active_touch_uid = touch.uid
            self.is_swiping = True
            self._layout_card()
            touch.grab(self)
            self._set_value_from_pos(touch.pos)
            return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current == self and touch.uid == self.active_touch_uid:
            if self.collide_point(*touch.pos):
                self._set_value_from_pos(touch.pos)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current == self and touch.uid == self.active_touch_uid:
            touch.ungrab(self)
            self.active_touch_uid = None
            self.is_swiping = False
            self._layout_card()
            center_val = getattr(self.slider, 'center_value', 10)
            Clock.schedule_once(lambda dt: setattr(self.slider, 'value', center_val), 0.05)
            return True
        return False


class StepSlider(Slider):
    """Non-auto-centering slider for Digital mode (0 to 20)"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_size = ('44dp', '44dp')
        self.background_width = '18dp'


# ==========================================
# SCREENS
# ==========================================
class AnalogScreen(Screen):
    pass


class DigitalScreen(Screen):
    pass


# ==========================================
# MAIN APP
# ==========================================
class HC05ProApp(App):
    def build(self):
        self.title = "HC-05 Pro Controller"

        self.bt_socket = None
        self.bt_writer = None
        self.bt_reader = None
        self.mac_address = "98:D3:31:F4:XX:XX"

        # Profile numbers: 1 = Analog (Joystick), 2 = Digital (D-Pad)
        self.current_mode = 'analog'
        self.profile_map = {'analog': 1, 'digital': 2}

        # Analog values: 1..19, center = 10
        self.val_v = 10
        self.val_h = 10

        # Digital values
        self.val_up = 0
        self.val_down = 0
        self.val_left = 0
        self.val_right = 0
        self.val_dig_slider = 0

        self.val_brake = 0
        self.val_park = 0
        self.val_head = 0
        self.val_horn = 0
        self.btn_state = {'brake': False, 'park': False, 'head': False}

        # ACK / Flow-Control state ("done" or "ok" from controller)
        self.tx_lock = threading.Lock()
        self.awaiting_ack = False
        self.last_sent_packet = ""
        self.pending_packet = None

        self.last_combined = ""
        self.is_connected = False
        self.is_connecting = False
        self.live_preview_label = None
        self.selected_profile_mode = 'analog'
        self.profile_btn_analog = None
        self.profile_btn_digital = None

        self.reconnect_buttons = []

        self.load_settings()

        self.sm = ScreenManager(transition=SlideTransition(duration=0.25))
        self.sm.add_widget(self._build_analog_screen())
        self.sm.add_widget(self._build_digital_screen())
        self.reset_values_for_mode(self.current_mode)
        self.sm.current = self.current_mode
        return self.sm

    # ==========================================
    # HELPER: Reconnect Button
    # ==========================================
    def _make_reconnect_button(self):
        rb = ReconnectButton(
            text="RECONNECT",
            font_size='10sp',
            bold=True,
            color=get_color_from_hex('#ffffff'),
            size_hint_x=1
        )
        rb.bind(on_release=lambda x: self.reconnect_bluetooth())
        self.reconnect_buttons.append(rb)
        return rb

    # ==========================================
    # TOP BAR (shared, uniform button sizes)
    # ==========================================
    def _build_top_bar(self):
        top_bar = BoxLayout(size_hint_y=None, height='52dp', padding='4dp', spacing='4dp')

        brake_btn = ProButton(
            bg_hex='#1e3a5f', text="BRAKE", font_size='11sp', bold=True,
            color=get_color_from_hex('#ccd6f6'), size_hint_x=1
        )
        brake_btn.bind(on_release=self.toggle_brake)
        top_bar.add_widget(brake_btn)

        park_btn = ProButton(
            bg_hex='#1e3a5f', text="PARK", font_size='11sp', bold=True,
            color=get_color_from_hex('#ccd6f6'), size_hint_x=1
        )
        park_btn.bind(on_release=self.toggle_park)
        top_bar.add_widget(park_btn)

        head_btn = ProButton(
            bg_hex='#1e3a5f', text="HEAD", font_size='11sp', bold=True,
            color=get_color_from_hex('#ccd6f6'), size_hint_x=1
        )
        head_btn.bind(on_release=self.toggle_head)
        top_bar.add_widget(head_btn)

        horn_btn = ProButton(
            bg_hex='#ff6d00', text="HORN", font_size='11sp', bold=True,
            color=get_color_from_hex('#ffffff'), size_hint_x=1
        )
        horn_btn.bind(on_press=self.press_horn, on_release=self.release_horn)
        top_bar.add_widget(horn_btn)

        reconnect_btn = self._make_reconnect_button()
        top_bar.add_widget(reconnect_btn)

        settings_btn = ProButton(
            bg_hex='#64ffda', text="SETTINGS", font_size='11sp', bold=True,
            color=get_color_from_hex('#0a192f'), size_hint_x=1
        )
        settings_btn.bind(on_release=lambda x: self.show_settings_popup())
        top_bar.add_widget(settings_btn)

        return top_bar, brake_btn, park_btn, head_btn, horn_btn, reconnect_btn, settings_btn

    # ==========================================
    # ANALOG SCREEN (Horizontal card & slider shifted 20dp left, centered in card)
    # ==========================================
    def _build_analog_screen(self):
        screen = AnalogScreen(name='analog')
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        top_bar, self.ana_btn_brake, self.ana_btn_park, self.ana_btn_head, self.ana_btn_horn, _, _ = self._build_top_bar()
        root.add_widget(top_bar)

        control_wrap = BoxLayout(orientation='horizontal', padding='8dp', spacing='8dp')

        self.slider_v = AutoCenterSlider(
            min=1, max=19, value=10, center_value=10,
            orientation='vertical', step=1,
            size_hint=(None, 0.88), width='84dp'
        )
        self.slider_v.bind(value=self.on_v_slider)
        self.v_slider_card = SliderCard(
            self.slider_v,
            swipe_orientation='vertical',
            trim_horizontal=dp(48),
            trim_vertical=dp(8),
            card_offset_x=0.0,
            card_offset_y=0.0,
            slider_offset_x=0.0,
            slider_offset_y=0.0,
            size_hint_x=0.5
        )
        control_wrap.add_widget(self.v_slider_card)

        self.slider_h = AutoCenterSlider(
            min=1, max=19, value=10, center_value=10,
            orientation='horizontal', step=1,
            size_hint=(0.88, None), height='84dp'
        )
        self.slider_h.bind(value=self.on_h_slider)
        self.h_slider_card = SliderCard(
            self.slider_h,
            swipe_orientation='horizontal',
            trim_horizontal=dp(8),
            trim_vertical=dp(48),
            card_offset_x=-dp(20),
            card_offset_y=0.0,
            slider_offset_x=0.0,
            slider_offset_y=0.0,
            size_hint_x=0.5
        )
        control_wrap.add_widget(self.h_slider_card)

        root.add_widget(control_wrap)
        screen.add_widget(root)
        return screen

    # ==========================================
    # DIGITAL SCREEN (Top bar + 0..20 slider + 4 D-Pad buttons)
    # ==========================================
    def _build_digital_screen(self):
        screen = DigitalScreen(name='digital')
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        top_bar, self.dig_btn_brake, self.dig_btn_park, self.dig_btn_head, self.dig_btn_horn, _, _ = self._build_top_bar()
        root.add_widget(top_bar)

        slider_bar = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height='52dp',
            padding=('12dp', '4dp', '12dp', '4dp'),
            spacing='10dp'
        )
        self.dig_slider_val_lbl = Label(
            text="0",
            size_hint_x=None, width='36dp',
            color=get_color_from_hex('#64ffda'),
            font_size='16sp', bold=True
        )
        self.slider_dig = StepSlider(
            min=0, max=20, value=0, step=1,
            orientation='horizontal',
            size_hint_x=1
        )
        self.slider_dig.bind(value=self.on_dig_slider)
        slider_bar.add_widget(self.dig_slider_val_lbl)
        slider_bar.add_widget(self.slider_dig)
        root.add_widget(slider_bar)

        control_wrap = BoxLayout(orientation='horizontal', padding='12dp', spacing='15dp')

        left_side = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing='15dp')
        self.btn_f = GlowButton(text="UP", font_size='24sp', bold=True)
        self.btn_f.key_id = 'UP'
        self.btn_f.bind(state=self.on_dpad_state)

        self.btn_b = GlowButton(text="DOWN", font_size='24sp', bold=True)
        self.btn_b.key_id = 'DOWN'
        self.btn_b.bind(state=self.on_dpad_state)

        left_side.add_widget(self.btn_f)
        left_side.add_widget(self.btn_b)
        control_wrap.add_widget(left_side)

        right_side = BoxLayout(orientation='horizontal', size_hint_x=0.6, spacing='15dp')

        self.btn_l = GlowButton(text="LEFT", font_size='24sp', bold=True)
        self.btn_l.key_id = 'LEFT'
        self.btn_l.bind(state=self.on_dpad_state)

        self.btn_r = GlowButton(text="RIGHT", font_size='24sp', bold=True)
        self.btn_r.key_id = 'RIGHT'
        self.btn_r.bind(state=self.on_dpad_state)

        right_side.add_widget(self.btn_l)
        right_side.add_widget(self.btn_r)
        control_wrap.add_widget(right_side)

        root.add_widget(control_wrap)
        screen.add_widget(root)
        return screen

    # ==========================================
    # NAVIGATION & PROFILE SWITCHING
    # ==========================================
    def switch_mode(self, mode):
        if mode not in ('analog', 'digital'):
            return
        self.current_mode = mode
        self.reset_values_for_mode(mode)
        self.sm.current = mode
        with self.tx_lock:
            self.last_sent_packet = ""
        self.last_combined = ""
        self.send_combined_data()

    def reset_values_for_mode(self, mode):
        if mode == 'analog':
            self.val_v = 10
            self.val_h = 10
            if hasattr(self, 'slider_v'):
                self.slider_v.value = 10
            if hasattr(self, 'slider_h'):
                self.slider_h.value = 10
        elif mode == 'digital':
            self.val_up = self.val_down = self.val_left = self.val_right = 0
            self.val_dig_slider = 0
            if hasattr(self, 'slider_dig'):
                self.slider_dig.value = 0
            if hasattr(self, 'dig_slider_val_lbl'):
                self.dig_slider_val_lbl.text = "0"
            for attr in ['btn_f', 'btn_b', 'btn_l', 'btn_r']:
                if hasattr(self, attr):
                    b = getattr(self, attr)
                    b.active_touches.clear()
                    b.state = 'normal'

    # ==========================================
    # LIFECYCLE
    # ==========================================
    def on_start(self):
        Clock.schedule_once(lambda dt: self.start_connection_thread(), 1)
        if platform == 'android':
            try:
                from android import mActivity
                mActivity.bind(on_keyboard=self._on_keyboard)
            except Exception:
                pass

    def _on_keyboard(self, window, key, *args):
        return False

    # ==========================================
    # BLUETOOTH
    # ==========================================
    def start_connection_thread(self):
        mac = self.mac_address.strip()
        if not mac or mac == '98:D3:31:F4:XX:XX':
            self.update_status_text("No MAC Address! Set in Settings")
            return
        self.update_status_text(f"Connecting to {mac}...")
        self.is_connecting = True
        threading.Thread(target=self.connect_task, args=(mac,), daemon=True).start()

    def connect_task(self, mac):
        try:
            if platform != 'android':
                Clock.schedule_once(lambda dt: self.on_connection_success(sim=True))
                return

            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter and adapter.isDiscovering():
                adapter.cancelDiscovery()

            device = adapter.getRemoteDevice(mac)
            s_uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")

            self.bt_socket = device.createRfcommSocketToServiceRecord(s_uuid)
            self.bt_socket.connect()
            self.bt_writer = self.bt_socket.getOutputStream()
            self.bt_reader = BufferedReader(InputStreamReader(self.bt_socket.getInputStream()))

            self.is_connected = True
            self.is_connecting = False
            Clock.schedule_once(lambda dt: self.on_connection_success(sim=False))

            while True:
                data = self.bt_reader.readLine()
                if data is None:
                    break
                line = str(data).strip().lower()
                if line in ("done", "ok"):
                    self.handle_ack_received(line)
        except Exception as e:
            print("BT Error:", e)
            self.is_connected = False
            self.is_connecting = False
        Clock.schedule_once(lambda dt: self.disconnect_bluetooth())

    def on_connection_success(self, sim=False):
        self.is_connected = True
        self.is_connecting = False
        with self.tx_lock:
            self.awaiting_ack = False
            self.pending_packet = None
            self.last_sent_packet = ""
        self.update_status_text("Simulated Connected Mode!" if sim else "Connected via Bluetooth!")
        self._update_all_reconnect_buttons(True)
        self.last_combined = ""
        self.send_combined_data()

    def disconnect_bluetooth(self):
        try:
            if self.bt_writer:
                self.bt_writer.close()
            if self.bt_reader:
                self.bt_reader.close()
            if self.bt_socket:
                self.bt_socket.close()
        except Exception:
            pass
        self.bt_socket = None
        self.bt_writer = None
        self.bt_reader = None
        self.is_connected = False
        with self.tx_lock:
            self.awaiting_ack = False
            self.pending_packet = None
        self.update_status_text("Disconnected")
        self._update_all_reconnect_buttons(False)

    def reconnect_bluetooth(self):
        if self.is_connecting:
            print("Reconnect already in progress...")
            return
        if self.is_connected:
            self.disconnect_bluetooth()
        Clock.schedule_once(lambda dt: self.start_connection_thread(), 0.5)

    def _update_all_reconnect_buttons(self, connected):
        for rb in self.reconnect_buttons:
            try:
                rb.set_connected(connected)
            except Exception:
                pass

    @mainthread
    def update_status_text(self, text_msg):
        print("BT STATUS:", text_msg)

    # ==========================================
    # DATA SENDING & ACK FLOW CONTROL ("done" / "ok")
    # ==========================================
    def _write_packet_now(self, packet):
        """Writes a single packet immediately. Caller must hold self.tx_lock."""
        mode_tag = self.current_mode
        if self.bt_socket and self.bt_writer:
            try:
                self.bt_writer.write(packet.encode('utf-8'))
                self.awaiting_ack = True
                self.last_sent_packet = packet
                print(f"SENT[{mode_tag}]: {packet.strip()} (waiting for done/ok)")
                Clock.schedule_once(lambda dt, pkt=packet, m=mode_tag: self._on_packet_dispatched(pkt, m), 0)
            except Exception:
                self.awaiting_ack = False
                Clock.schedule_once(lambda dt: self.disconnect_bluetooth(), 0)
        elif platform != 'android':
            # Non-Android simulation mode: immediately acknowledge
            self.awaiting_ack = False
            self.last_sent_packet = packet
            print(f"SIM-SENT[{mode_tag}]: {packet.strip()} (auto-ok)")
            Clock.schedule_once(lambda dt, pkt=packet, m=mode_tag: self._on_packet_dispatched(pkt, m), 0)
        else:
            # Disconnected on Android: hold latest packet until connected
            self.pending_packet = packet
            print(f"HOLD-OFFLINE[{mode_tag}]: {packet.strip()}")

    @mainthread
    def _on_packet_dispatched(self, packet, mode_tag):
        self.last_combined = packet
        if self.live_preview_label is not None:
            try:
                p_num = self.profile_map[self.current_mode]
                self.live_preview_label.text = f"[P{p_num} - {self.current_mode.upper()}] {packet.strip()}"
            except Exception:
                pass

    def handle_ack_received(self, ack_token="done"):
        """Called when receiver sends 'done' or 'ok'. Sends only the latest held packet."""
        next_packet = None
        with self.tx_lock:
            self.awaiting_ack = False
            if self.pending_packet is not None and self.pending_packet != self.last_sent_packet:
                next_packet = self.pending_packet
                self.pending_packet = None
                self._write_packet_now(next_packet)
            else:
                self.pending_packet = None
                print(f"ACK[{ack_token}] received; no pending packet.")

    def send_combined_data(self):
        profile_num = self.profile_map[self.current_mode]
        if self.current_mode == 'analog':
            packet = (
                f"<{profile_num},{self.val_v},{self.val_h},"
                f"{self.val_brake},{self.val_park},{self.val_head},{self.val_horn}>\n"
            )
        else:
            packet = (
                f"<{profile_num},{self.val_up},{self.val_down},{self.val_left},{self.val_right},"
                f"{self.val_brake},{self.val_park},{self.val_head},{self.val_horn},{self.val_dig_slider}>\n"
            )

        with self.tx_lock:
            if not self.awaiting_ack:
                if packet != self.last_sent_packet:
                    self._write_packet_now(packet)
            else:
                # Hold only the latest packet while waiting for 'done'/'ok'
                if packet != self.last_sent_packet:
                    self.pending_packet = packet
                    print(f"HOLD-LATEST[{self.current_mode}]: {packet.strip()}")
                else:
                    # Returned to already-sent state before ACK: clear stale pending change
                    self.pending_packet = None

    @mainthread
    def _update_live_preview(self, text):
        if self.live_preview_label is not None:
            try:
                p_num = self.profile_map[self.current_mode]
                self.live_preview_label.text = f"[P{p_num} - {self.current_mode.upper()}] {text}"
            except Exception:
                pass

    # ==========================================
    # ANALOG HANDLERS (1..19, center 10)
    # ==========================================
    def on_v_slider(self, instance, value):
        if self.current_mode != 'analog':
            return
        self.val_v = 20 - int(value)
        self.send_combined_data()

    def on_h_slider(self, instance, value):
        if self.current_mode != 'analog':
            return
        self.val_h = int(value)
        self.send_combined_data()

    # ==========================================
    # DIGITAL HANDLERS
    # ==========================================
    def on_dig_slider(self, instance, value):
        self.val_dig_slider = int(value)
        if hasattr(self, 'dig_slider_val_lbl'):
            self.dig_slider_val_lbl.text = str(self.val_dig_slider)
        if self.current_mode != 'digital':
            return
        self.send_combined_data()

    def on_dpad_state(self, instance, state):
        if self.current_mode != 'digital':
            return
        key = instance.key_id
        if state == 'down':
            self.press_key(key)
        else:
            self.release_key(key)

    def press_key(self, key):
        if key == 'UP' and self.btn_b.state == 'down':
            self.btn_b.active_touches.clear()
            self.btn_b.state = 'normal'
        elif key == 'DOWN' and self.btn_f.state == 'down':
            self.btn_f.active_touches.clear()
            self.btn_f.state = 'normal'
        if key == 'LEFT' and self.btn_r.state == 'down':
            self.btn_r.active_touches.clear()
            self.btn_r.state = 'normal'
        elif key == 'RIGHT' and self.btn_l.state == 'down':
            self.btn_l.active_touches.clear()
            self.btn_l.state = 'normal'

        if key == 'UP':
            self.val_up = 1
        elif key == 'DOWN':
            self.val_down = 1
        elif key == 'LEFT':
            self.val_left = 1
        elif key == 'RIGHT':
            self.val_right = 1
        self.send_combined_data()

    def release_key(self, key):
        if key == 'UP':
            self.val_up = 0
        elif key == 'DOWN':
            self.val_down = 0
        elif key == 'LEFT':
            self.val_left = 0
        elif key == 'RIGHT':
            self.val_right = 0
        self.send_combined_data()

    # ==========================================
    # SHARED BUTTON HANDLERS
    # ==========================================
    def _update_btn_visual(self, ana_btn, dig_btn, state, on_hex, off_hex):
        for b in [ana_btn, dig_btn]:
            if b is None:
                continue
            b.set_bg_color(on_hex if state else off_hex)
            b.color = get_color_from_hex('#0a192f') if state else get_color_from_hex('#ccd6f6')

    def toggle_brake(self, btn):
        self.btn_state['brake'] = not self.btn_state['brake']
        self.val_brake = 1 if self.btn_state['brake'] else 0
        self._update_btn_visual(
            getattr(self, 'ana_btn_brake', None),
            getattr(self, 'dig_btn_brake', None),
            self.val_brake, '#64ffda', '#1e3a5f'
        )
        self.send_combined_data()

    def toggle_park(self, btn):
        self.btn_state['park'] = not self.btn_state['park']
        self.val_park = 1 if self.btn_state['park'] else 0
        self._update_btn_visual(
            getattr(self, 'ana_btn_park', None),
            getattr(self, 'dig_btn_park', None),
            self.val_park, '#64ffda', '#1e3a5f'
        )
        self.send_combined_data()

    def toggle_head(self, btn):
        self.btn_state['head'] = not self.btn_state['head']
        self.val_head = 1 if self.btn_state['head'] else 0
        self._update_btn_visual(
            getattr(self, 'ana_btn_head', None),
            getattr(self, 'dig_btn_head', None),
            self.val_head, '#64ffda', '#1e3a5f'
        )
        self.send_combined_data()

    def press_horn(self, btn):
        self.val_horn = 1
        for b in [getattr(self, 'ana_btn_horn', None), getattr(self, 'dig_btn_horn', None)]:
            if b:
                b.set_bg_color('#ffab40')
        self.send_combined_data()

    def release_horn(self, btn):
        self.val_horn = 0
        for b in [getattr(self, 'ana_btn_horn', None), getattr(self, 'dig_btn_horn', None)]:
            if b:
                b.set_bg_color('#ff6d00')
        self.send_combined_data()

    # ==========================================
    # SETTINGS POPUP (Includes Profile Selection Bar)
    # ==========================================
    def show_settings_popup(self):
        self.selected_profile_mode = self.current_mode
        popup_layout = BoxLayout(orientation='vertical', padding='15dp', spacing='10dp')

        lbl_prof = Label(
            text="PROFILE SELECTION", size_hint_y=None, height='24dp',
            color=get_color_from_hex('#64ffda'), font_size='14sp', bold=True,
            halign='left', valign='middle'
        )
        lbl_prof.bind(size=lbl_prof.setter('text_size'))
        popup_layout.add_widget(lbl_prof)

        prof_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp', spacing='10dp')
        self.profile_btn_analog = ProButton(
            bg_hex='#1e3a5f', text="1: ANALOG (JOYSTICK)",
            font_size='12sp', bold=True,
            color=get_color_from_hex('#ccd6f6')
        )
        self.profile_btn_analog.bind(on_release=lambda x: self._select_profile_in_popup('analog'))

        self.profile_btn_digital = ProButton(
            bg_hex='#1e3a5f', text="2: DIGITAL (D-PAD)",
            font_size='12sp', bold=True,
            color=get_color_from_hex('#ccd6f6')
        )
        self.profile_btn_digital.bind(on_release=lambda x: self._select_profile_in_popup('digital'))

        prof_bar.add_widget(self.profile_btn_analog)
        prof_bar.add_widget(self.profile_btn_digital)
        popup_layout.add_widget(prof_bar)
        self._refresh_profile_bar_visual()

        lbl_mac = Label(
            text="HC-05 MAC Address", size_hint_y=None, height='24dp',
            color=get_color_from_hex('#64ffda'), font_size='14sp', bold=True,
            halign='left', valign='middle'
        )
        lbl_mac.bind(size=lbl_mac.setter('text_size'))
        popup_layout.add_widget(lbl_mac)

        mac_wrap = AnchorLayout(
            size_hint_y=None, height='46dp',
            anchor_x='center', anchor_y='center'
        )
        self.mac_input = CenteredTextInput(
            text=self.mac_address, size_hint=(1, 1), multiline=False,
            background_color=get_color_from_hex('#0a192f'),
            foreground_color=get_color_from_hex('#64ffda'),
            cursor_color=get_color_from_hex('#64ffda'),
            font_size='17sp', halign='center',
            use_bubble=False, use_handles=False
        )
        mac_wrap.add_widget(self.mac_input)
        popup_layout.add_widget(mac_wrap)

        live_title = Label(
            text="LIVE DATA PREVIEW", size_hint_y=None, height='22dp',
            color=get_color_from_hex('#64ffda'), font_size='13sp', bold=True,
            halign='left', valign='middle'
        )
        live_title.bind(size=live_title.setter('text_size'))
        popup_layout.add_widget(live_title)

        p_num = self.profile_map[self.current_mode]
        current_pkt = self.last_combined.strip() if self.last_combined else "Waiting for data..."
        self.live_preview_label = Label(
            text=f"[P{p_num} - {self.current_mode.upper()}] {current_pkt}",
            size_hint_y=None, height='42dp',
            color=get_color_from_hex('#64ffda'),
            font_size='14sp', bold=True,
            halign='center', valign='middle'
        )
        self.live_preview_label.bind(size=self.live_preview_label.setter('text_size'))
        with self.live_preview_label.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=self.live_preview_label.pos, size=self.live_preview_label.size, radius=[8])
        self.live_preview_label.bind(pos=self._repaint_live, size=self._repaint_live)
        popup_layout.add_widget(self.live_preview_label)

        btn_view_format = ProButton(
            bg_hex='#1e3a5f', text="VIEW DATA FORMAT & LOGIC",
            size_hint_y=None, height='46dp',
            font_size='14sp', bold=True,
            color=get_color_from_hex('#64ffda')
        )
        btn_view_format.bind(on_release=lambda x: self.show_format_popup())
        popup_layout.add_widget(btn_view_format)

        popup_layout.add_widget(Label())

        btn_save = ProButton(
            bg_hex='#00c853', text="SAVE & RECONNECT",
            size_hint_y=None, height='50dp',
            font_size='16sp', color=get_color_from_hex('#0a192f'), bold=True
        )
        btn_save.bind(on_release=self.save_settings)
        popup_layout.add_widget(btn_save)

        self.popup = Popup(
            title="Controller Settings",
            content=popup_layout, size_hint=(0.95, 0.82),
            background_color=[0.07, 0.13, 0.25, 1]
        )
        self.popup.bind(on_dismiss=lambda x: setattr(self, 'live_preview_label', None))
        self.popup.open()

    def _select_profile_in_popup(self, mode):
        self.selected_profile_mode = mode
        self._refresh_profile_bar_visual()

    def _refresh_profile_bar_visual(self):
        if self.profile_btn_analog and self.profile_btn_digital:
            is_ana = (self.selected_profile_mode == 'analog')
            self.profile_btn_analog.set_bg_color('#64ffda' if is_ana else '#1e3a5f')
            self.profile_btn_analog.color = get_color_from_hex('#0a192f' if is_ana else '#ccd6f6')

            self.profile_btn_digital.set_bg_color('#64ffda' if not is_ana else '#1e3a5f')
            self.profile_btn_digital.color = get_color_from_hex('#0a192f' if not is_ana else '#ccd6f6')

    # ==========================================
    # DATA FORMAT POPUP (Framed <...> + ACK Flow Control)
    # ==========================================
    def show_format_popup(self):
        content = BoxLayout(orientation='vertical', padding='15dp', spacing='10dp')

        scroll = ScrollView(size_hint=(1, 1))
        info_text = (
            "PACKET FRAMING (<...>)\n"
            "Every packet starts with '<', ends with '>', and appends '\\n':\n"
            "  Profile 1 = Analog (Joystick)\n"
            "  Profile 2 = Digital (D-Pad)\n"
            "──────────────────────────────\n\n"
            "ACK FLOW CONTROL ('done' / 'ok')\n"
            "  • After sending a packet, the app waits for 'done' or 'ok'\n"
            "    from the controller before sending the next packet.\n"
            "  • While waiting for 'done'/'ok', any new packets generated\n"
            "    are held and overwritten so only the LATEST packet is kept\n"
            "    (intermediate packets are skipped).\n"
            "  • As soon as 'done' or 'ok' arrives, the latest held packet\n"
            "    is transmitted immediately.\n"
            "──────────────────────────────\n\n"
            "PROFILE 1: ANALOG MODE (Joystick)\n"
            "Format: <1, V, H, B, P, L, O>\\n\n\n"
            "  1  = Profile Number (Analog)\n"
            "  V  = Vertical (1..19, center = 10)\n"
            "       1  = Fast Forward\n"
            "       10 = Stop / Center\n"
            "       19 = Fast Back\n\n"
            "  H  = Horizontal (1..19, center = 10)\n"
            "       1  = Left\n"
            "       10 = Straight / Center\n"
            "       19 = Right\n\n"
            "  B  = Brake      (0 / 1)\n"
            "  P  = Park       (0 / 1)\n"
            "  L  = Head Light (0 / 1)\n"
            "  O  = Horn       (0 / 1)\n\n"
            "  Example: <1,5,10,0,0,1,0>\\n\n"
            "──────────────────────────────\n\n"
            "PROFILE 2: DIGITAL MODE (D-Pad)\n"
            "Format: <2, U, D, L, R, B, P, Hd, Hr, S>\\n\n\n"
            "  2  = Profile Number (Digital)\n"
            "  U  = Up         (0 / 1)\n"
            "  D  = Down       (0 / 1)\n"
            "  L  = Left       (0 / 1)\n"
            "  R  = Right      (0 / 1)\n"
            "  B  = Brake      (0 / 1)\n"
            "  P  = Park       (0 / 1)\n"
            "  Hd = Head Light (0 / 1)\n"
            "  Hr = Horn       (0 / 1)\n"
            "  S  = Slider     (0..20 step, default 0)\n\n"
            "  Example: <2,1,0,0,0,0,0,0,0,14>\\n\n"
            "──────────────────────────────\n\n"
            "NOTES:\n"
            "  • '<' and '>' prevent partial/corrupted packet reads.\n"
            "  • Next packet waits for 'done' or 'ok'; latest packet is sent on ACK.\n"
            "  • Last selected profile is saved and loaded on restart.\n"
            "  • Switch profiles (1 / 2) inside Settings.\n"
            "  • Horizontal card & slider shifted 20dp left and centered inside the horizontal card.\n"
            "  • Touch response works only inside each card's bounds.\n"
            "  • Analog sliders range 1..19 and auto-center to 10 on release.\n"
            "  • Digital top slider steps 0 to 20 (same height as top bar).\n"
            "  • D-Pad auto-excludes opposite directions."
        )

        lbl = Label(
            text=info_text,
            color=get_color_from_hex('#ccd6f6'),
            font_size='13sp',
            halign='left', valign='top',
            size_hint_y=None
        )
        lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        lbl.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))
        scroll.add_widget(lbl)
        content.add_widget(scroll)

        btn_close = ProButton(
            bg_hex='#64ffda', text="CLOSE",
            size_hint_y=None, height='50dp',
            font_size='16sp', bold=True,
            color=get_color_from_hex('#0a192f')
        )
        format_popup = Popup(
            title="Data Format & Logic",
            content=content, size_hint=(0.92, 0.85),
            background_color=[0.07, 0.13, 0.25, 1]
        )
        btn_close.bind(on_release=format_popup.dismiss)
        content.add_widget(btn_close)
        format_popup.open()

    def _repaint_live(self, widget, *args):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[8])

    def save_settings(self, btn):
        old_mac = self.mac_address
        self.mac_address = self.mac_input.text.strip()
        chosen_mode = self.selected_profile_mode if self.selected_profile_mode in ('analog', 'digital') else self.current_mode
        mode_changed = (chosen_mode != self.current_mode)

        try:
            with open('bt_settings.json', 'w') as f:
                json.dump({'MAC': self.mac_address, 'mode': chosen_mode}, f)
        except Exception:
            pass

        self.popup.dismiss()

        if mode_changed:
            self.switch_mode(chosen_mode)

        if old_mac != self.mac_address:
            self.disconnect_bluetooth()
            self.start_connection_thread()

    def load_settings(self):
        if os.path.exists('bt_settings.json'):
            try:
                with open('bt_settings.json', 'r') as f:
                    data = json.load(f)
                    if 'MAC' in data:
                        self.mac_address = data['MAC']
                    elif 'mac' in data:
                        self.mac_address = data['mac']
                    if data.get('mode') in ('analog', 'digital'):
                        self.current_mode = data['mode']
            except Exception as e:
                print("Setting load error:", e)


if __name__ == "__main__":
    HC05ProApp().run()
