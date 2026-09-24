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
        except: pass
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
        # Center text vertically
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
                RoundedRectangle(pos=(self.pos[0] - 5, self.pos[1] - 5), size=(self.size[0] + 10, self.size[1] + 10), radius=[22])
                Color(rgba=get_color_from_hex('#64ffda'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
            else:
                Color(rgba=get_color_from_hex('#1e3a5f'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
                Color(rgba=get_color_from_hex('#0a192f'))
                RoundedRectangle(pos=(self.pos[0] + 2, self.pos[1] + 2), size=(self.size[0] - 4, self.size[1] - 4), radius=[16])

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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_size = ('80dp', '80dp')
        self.background_width = '35dp'

    def on_touch_up(self, touch):
        if touch.grab_current == self:
            Clock.schedule_once(lambda dt: setattr(self, 'value', 5), 0.05)
        return super().on_touch_up(touch)


# ==========================================
# SCREENS
# ==========================================
class MenuScreen(Screen):
    pass

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

        self.current_mode = 'analog'

        self.val_v = 5
        self.val_h = 5
        self.val_up = 0
        self.val_down = 0
        self.val_left = 0
        self.val_right = 0

        self.val_brake = 0
        self.val_park = 0
        self.val_head = 0
        self.val_horn = 0
        self.btn_state = {'brake': False, 'park': False, 'head': False}

        self.last_combined = ""
        self.is_connected = False
        self.is_connecting = False
        self.live_preview_label = None

        self.reconnect_buttons = []

        self.load_settings()

        self.sm = ScreenManager(transition=SlideTransition(duration=0.25))
        self.sm.add_widget(self._build_menu_screen())
        self.sm.add_widget(self._build_analog_screen())
        self.sm.add_widget(self._build_digital_screen())
        self.sm.current = 'menu'
        return self.sm

    # ==========================================
    # HELPER: Reconnect Button
    # ==========================================
    def _make_reconnect_button(self):
        rb = ReconnectButton(text="RECONNECT", font_size='11sp', bold=True,
                             color=get_color_from_hex('#ffffff'),
                             size_hint_x=None, width='90dp')
        rb.bind(on_release=lambda x: self.reconnect_bluetooth())
        self.reconnect_buttons.append(rb)
        return rb

    # ==========================================
    # MENU SCREEN
    # ==========================================
    def _build_menu_screen(self):
        screen = MenuScreen(name='menu')
        root = BoxLayout(orientation='vertical', padding='25dp', spacing='20dp')

        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        title = Label(
            text="HC-05 PRO CONTROLLER",
            size_hint_y=None, height='60dp',
            color=get_color_from_hex('#64ffda'),
            font_size='24sp', bold=True
        )
        root.add_widget(title)

        self.menu_status = Label(
            text="Initializing...",
            size_hint_y=None, height='35dp',
            color=get_color_from_hex('#ffffff'),
            font_size='13sp', bold=True
        )
        self._paint_status_bg(self.menu_status, False)
        root.add_widget(self.menu_status)

        root.add_widget(Label(size_hint_y=None, height='20dp'))

        select_lbl = Label(
            text="SELECT CONTROL MODE",
            size_hint_y=None, height='30dp',
            color=get_color_from_hex('#ccd6f6'),
            font_size='16sp', bold=True
        )
        root.add_widget(select_lbl)

        btn_analog = ProButton(
            bg_hex='#1e3a5f', text="ANALOG\n(Smooth Joystick)",
            size_hint_y=None, height='100dp',
            font_size='22sp', bold=True,
            color=get_color_from_hex('#64ffda')
        )
        btn_analog.bind(on_release=lambda x: self.switch_mode('analog'))
        root.add_widget(btn_analog)

        btn_digital = ProButton(
            bg_hex='#1e3a5f', text="DIGITAL\n(D-Pad Buttons)",
            size_hint_y=None, height='100dp',
            font_size='22sp', bold=True,
            color=get_color_from_hex('#64ffda')
        )
        btn_digital.bind(on_release=lambda x: self.switch_mode('digital'))
        root.add_widget(btn_digital)

        root.add_widget(Label())

        btn_settings = ProButton(
            bg_hex='#64ffda', text="SETTINGS",
            size_hint_y=None, height='55dp',
            font_size='18sp', bold=True,
            color=get_color_from_hex('#0a192f')
        )
        btn_settings.bind(on_release=lambda x: self.show_settings_popup())
        root.add_widget(btn_settings)

        screen.add_widget(root)
        return screen

    # ==========================================
    # TOP BAR (shared)
    # ==========================================
    def _build_top_bar(self, mode_prefix):
        top_bar = BoxLayout(size_hint_y=None, height='52dp', padding='4dp', spacing='4dp')

        btn_back = ProButton(bg_hex='#64ffda', text="BACK", font_size='12sp', bold=True,
                             color=get_color_from_hex('#0a192f'), size_hint_x=1)
        btn_back.bind(on_release=lambda x: self.go_back_to_menu())
        top_bar.add_widget(btn_back)

        brake_btn = ProButton(bg_hex='#1e3a5f', text="BRAKE", font_size='12sp', bold=True,
                              color=get_color_from_hex('#ccd6f6'), size_hint_x=1)
        brake_btn.bind(on_release=self.toggle_brake)
        top_bar.add_widget(brake_btn)

        park_btn = ProButton(bg_hex='#1e3a5f', text="PARK", font_size='12sp', bold=True,
                             color=get_color_from_hex('#ccd6f6'), size_hint_x=1)
        park_btn.bind(on_release=self.toggle_park)
        top_bar.add_widget(park_btn)

        head_btn = ProButton(bg_hex='#1e3a5f', text="HEAD", font_size='12sp', bold=True,
                             color=get_color_from_hex('#ccd6f6'), size_hint_x=1)
        head_btn.bind(on_release=self.toggle_head)
        top_bar.add_widget(head_btn)

        horn_btn = ProButton(bg_hex='#ff6d00', text="HORN", font_size='12sp', bold=True,
                             color=get_color_from_hex('#ffffff'), size_hint_x=1)
        horn_btn.bind(on_press=self.press_horn, on_release=self.release_horn)
        top_bar.add_widget(horn_btn)

        reconnect_btn = self._make_reconnect_button()
        top_bar.add_widget(reconnect_btn)

        return top_bar, btn_back, brake_btn, park_btn, head_btn, horn_btn, reconnect_btn

    # ==========================================
    # ANALOG SCREEN
    # ==========================================
    def _build_analog_screen(self):
        screen = AnalogScreen(name='analog')
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        top_bar, _, self.ana_btn_brake, self.ana_btn_park, self.ana_btn_head, self.ana_btn_horn, _ = self._build_top_bar('ana')
        root.add_widget(top_bar)

        control_wrap = BoxLayout(orientation='horizontal', padding='20dp', spacing='30dp')

        left_anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_x=0.5)
        self.slider_v = AutoCenterSlider(min=0, max=10, value=5, orientation='vertical', step=1, size_hint=(None, 0.95), width='120dp')
        self.slider_v.bind(value=self.on_v_slider)
        left_anchor.add_widget(self.slider_v)
        control_wrap.add_widget(left_anchor)

        right_anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_x=0.5)
        self.slider_h = AutoCenterSlider(min=0, max=10, value=5, orientation='horizontal', step=1, size_hint=(0.95, None), height='120dp')
        self.slider_h.bind(value=self.on_h_slider)
        right_anchor.add_widget(self.slider_h)
        control_wrap.add_widget(right_anchor)

        root.add_widget(control_wrap)
        screen.add_widget(root)
        return screen

    # ==========================================
    # DIGITAL SCREEN
    # ==========================================
    def _build_digital_screen(self):
        screen = DigitalScreen(name='digital')
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        top_bar, _, self.dig_btn_brake, self.dig_btn_park, self.dig_btn_head, self.dig_btn_horn, _ = self._build_top_bar('dig')
        root.add_widget(top_bar)

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
    # NAVIGATION
    # ==========================================
    def switch_mode(self, mode):
        self.current_mode = mode
        self.reset_values_for_mode(mode)
        self.sm.current = mode
        self.last_combined = ""
        self.send_combined_data()

    def go_back_to_menu(self):
        self.sm.current = 'menu'

    def reset_values_for_mode(self, mode):
        if mode == 'analog':
            self.val_v = 5
            self.val_h = 5
            if hasattr(self, 'slider_v'):
                self.slider_v.value = 5
            if hasattr(self, 'slider_h'):
                self.slider_h.value = 5
        elif mode == 'digital':
            self.val_up = self.val_down = self.val_left = self.val_right = 0
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
            except: pass

    def _on_keyboard(self, window, key, *args):
        if key == 27:
            if self.sm.current != 'menu':
                self.go_back_to_menu()
                return True
        return False

    # ==========================================
    # BLUETOOTH
    # ==========================================
    def start_connection_thread(self):
        mac = self.mac_address.strip()
        if not mac or mac == '98:D3:31:F4:XX:XX':
            self.update_status_bar(False, "No MAC Address! Set in Settings")
            return
        self.update_status_bar(False, f"Connecting to {mac}...")
        self.is_connecting = True
        threading.Thread(target=self.connect_task, args=(mac,), daemon=True).start()

    def connect_task(self, mac):
        try:
            if platform != 'android':
                Clock.schedule_once(lambda dt: self.update_status_bar(True, "Simulated Connected Mode!"))
                self.is_connected = True
                self.is_connecting = False
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
            Clock.schedule_once(lambda dt: self.on_connection_success())

            while True:
                data = self.bt_reader.readLine()
                if data is None:
                    break
        except Exception as e:
            print("BT Error:", e)
            self.is_connected = False
            self.is_connecting = False
        Clock.schedule_once(lambda dt: self.disconnect_bluetooth())

    def on_connection_success(self):
        self.update_status_bar(True, "Connected via Bluetooth!")
        self._update_all_reconnect_buttons(True)
        self.last_combined = ""
        self.send_combined_data()

    def disconnect_bluetooth(self):
        try:
            if self.bt_writer: self.bt_writer.close()
            if self.bt_reader: self.bt_reader.close()
            if self.bt_socket: self.bt_socket.close()
        except: pass
        self.bt_socket = None
        self.bt_writer = None
        self.bt_reader = None
        self.is_connected = False
        self.update_status_bar(False, "Disconnected")
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
            except: pass

    def _paint_status_bg(self, widget, connected):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(rgba=get_color_from_hex('#00c853' if connected else '#d32f2f'))
            RoundedRectangle(pos=widget.pos, size=widget.size)

    @mainthread
    def update_status_bar(self, connected, text_msg):
        if hasattr(self, 'menu_status'):
            self.menu_status.text = text_msg
            self._paint_status_bg(self.menu_status, connected)

    # ==========================================
    # DATA SENDING
    # ==========================================
    def send_combined_data(self):
        if self.current_mode == 'analog':
            packet = f"{self.val_v},{self.val_h},{self.val_brake},{self.val_park},{self.val_head},{self.val_horn}\n"
        else:
            packet = f"{self.val_up},{self.val_down},{self.val_left},{self.val_right},{self.val_brake},{self.val_park},{self.val_head},{self.val_horn}\n"

        if packet != self.last_combined:
            if self.bt_socket and self.bt_writer:
                try:
                    self.bt_writer.write(packet.encode('utf-8'))
                    print(f"SENT[{self.current_mode}]: {packet.strip()}")
                except Exception:
                    self.disconnect_bluetooth()
            else:
                print(f"SIM-SENT[{self.current_mode}]: {packet.strip()}")
            self.last_combined = packet

            if self.live_preview_label is not None:
                self._update_live_preview(packet.strip())

    @mainthread
    def _update_live_preview(self, text):
        if self.live_preview_label is not None:
            try:
                self.live_preview_label.text = f"[{self.current_mode.upper()}] {text}"
            except: pass

    # ==========================================
    # ANALOG HANDLERS
    # ==========================================
    def on_v_slider(self, instance, value):
        if self.current_mode != 'analog': return
        self.val_v = 10 - int(value)
        self.send_combined_data()

    def on_h_slider(self, instance, value):
        if self.current_mode != 'analog': return
        self.val_h = int(value)
        self.send_combined_data()

    # ==========================================
    # DIGITAL HANDLERS
    # ==========================================
    def on_dpad_state(self, instance, state):
        if self.current_mode != 'digital': return
        key = instance.key_id
        if state == 'down':
            self.press_key(key)
        else:
            self.release_key(key)

    def press_key(self, key):
        if key == 'UP' and self.btn_b.state == 'down':
            self.btn_b.active_touches.clear(); self.btn_b.state = 'normal'
        elif key == 'DOWN' and self.btn_f.state == 'down':
            self.btn_f.active_touches.clear(); self.btn_f.state = 'normal'
        if key == 'LEFT' and self.btn_r.state == 'down':
            self.btn_r.active_touches.clear(); self.btn_r.state = 'normal'
        elif key == 'RIGHT' and self.btn_l.state == 'down':
            self.btn_l.active_touches.clear(); self.btn_l.state = 'normal'

        if key == 'UP': self.val_up = 1
        elif key == 'DOWN': self.val_down = 1
        elif key == 'LEFT': self.val_left = 1
        elif key == 'RIGHT': self.val_right = 1
        self.send_combined_data()

    def release_key(self, key):
        if key == 'UP': self.val_up = 0
        elif key == 'DOWN': self.val_down = 0
        elif key == 'LEFT': self.val_left = 0
        elif key == 'RIGHT': self.val_right = 0
        self.send_combined_data()

    # ==========================================
    # SHARED BUTTON HANDLERS
    # ==========================================
    def _update_btn_visual(self, ana_btn, dig_btn, state, on_hex, off_hex):
        for b in [ana_btn, dig_btn]:
            if b is None: continue
            b.set_bg_color(on_hex if state else off_hex)
            b.color = get_color_from_hex('#0a192f') if state else get_color_from_hex('#ccd6f6')

    def toggle_brake(self, btn):
        self.btn_state['brake'] = not self.btn_state['brake']
        self.val_brake = 1 if self.btn_state['brake'] else 0
        self._update_btn_visual(getattr(self, 'ana_btn_brake', None),
                                getattr(self, 'dig_btn_brake', None),
                                self.val_brake, '#64ffda', '#1e3a5f')
        self.send_combined_data()

    def toggle_park(self, btn):
        self.btn_state['park'] = not self.btn_state['park']
        self.val_park = 1 if self.btn_state['park'] else 0
        self._update_btn_visual(getattr(self, 'ana_btn_park', None),
                                getattr(self, 'dig_btn_park', None),
                                self.val_park, '#64ffda', '#1e3a5f')
        self.send_combined_data()

    def toggle_head(self, btn):
        self.btn_state['head'] = not self.btn_state['head']
        self.val_head = 1 if self.btn_state['head'] else 0
        self._update_btn_visual(getattr(self, 'ana_btn_head', None),
                                getattr(self, 'dig_btn_head', None),
                                self.val_head, '#64ffda', '#1e3a5f')
        self.send_combined_data()

    def press_horn(self, btn):
        self.val_horn = 1
        for b in [getattr(self, 'ana_btn_horn', None), getattr(self, 'dig_btn_horn', None)]:
            if b: b.set_bg_color('#ffab40')
        self.send_combined_data()

    def release_horn(self, btn):
        self.val_horn = 0
        for b in [getattr(self, 'ana_btn_horn', None), getattr(self, 'dig_btn_horn', None)]:
            if b: b.set_bg_color('#ff6d00')
        self.send_combined_data()

    # ==========================================
    # SETTINGS POPUP (Compact - no format text)
    # ==========================================
    def show_settings_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding='15dp', spacing='12dp')

        # --- MAC Address ---
        lbl_mac = Label(text="HC-05 MAC Address", size_hint_y=None, height='28dp',
                        color=get_color_from_hex('#64ffda'), font_size='16sp', bold=True,
                        halign='left', valign='middle')
        lbl_mac.bind(size=lbl_mac.setter('text_size'))
        popup_layout.add_widget(lbl_mac)

        # MAC input - CENTERED via AnchorLayout with fixed height
        mac_wrap = AnchorLayout(size_hint_y=None, height='50dp',
                                anchor_x='center', anchor_y='center')
        self.mac_input = CenteredTextInput(
            text=self.mac_address, size_hint=(1, 1), multiline=False,
            background_color=get_color_from_hex('#0a192f'),
            foreground_color=get_color_from_hex('#64ffda'),
            cursor_color=get_color_from_hex('#64ffda'),
            font_size='18sp', halign='center',
            use_bubble=False, use_handles=False
        )
        mac_wrap.add_widget(self.mac_input)
        popup_layout.add_widget(mac_wrap)

        # --- ACTIVE MODE indicator ---
        mode_lbl = Label(
            text=f"ACTIVE MODE: {self.current_mode.upper()}",
            size_hint_y=None, height='36dp',
            color=get_color_from_hex('#0a192f'),
            font_size='16sp', bold=True
        )
        with mode_lbl.canvas.before:
            Color(rgba=get_color_from_hex('#64ffda'))
            RoundedRectangle(pos=mode_lbl.pos, size=mode_lbl.size, radius=[8])
        mode_lbl.bind(pos=self._repaint_mode_lbl, size=self._repaint_mode_lbl)
        popup_layout.add_widget(mode_lbl)

        # --- LIVE DATA PREVIEW ---
        live_title = Label(text="LIVE DATA PREVIEW", size_hint_y=None, height='24dp',
                           color=get_color_from_hex('#64ffda'), font_size='13sp', bold=True,
                           halign='left', valign='middle')
        live_title.bind(size=live_title.setter('text_size'))
        popup_layout.add_widget(live_title)

        self.live_preview_label = Label(
            text=f"[{self.current_mode.upper()}] Waiting for data...",
            size_hint_y=None, height='46dp',
            color=get_color_from_hex('#64ffda'),
            font_size='15sp', bold=True,
            halign='center', valign='middle'
        )
        self.live_preview_label.bind(size=self.live_preview_label.setter('text_size'))
        with self.live_preview_label.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=self.live_preview_label.pos, size=self.live_preview_label.size, radius=[8])
        self.live_preview_label.bind(pos=self._repaint_live, size=self._repaint_live)
        popup_layout.add_widget(self.live_preview_label)

        # --- View Data Format Button ---
        btn_view_format = ProButton(
            bg_hex='#1e3a5f', text="VIEW DATA FORMAT & LOGIC",
            size_hint_y=None, height='50dp',
            font_size='15sp', bold=True,
            color=get_color_from_hex('#64ffda')
        )
        btn_view_format.bind(on_release=lambda x: self.show_format_popup())
        popup_layout.add_widget(btn_view_format)

        # Spacer
        popup_layout.add_widget(Label())

        # --- Save Button ---
        btn_save = ProButton(bg_hex='#00c853', text="SAVE & RECONNECT",
                             size_hint_y=None, height='55dp',
                             font_size='18sp', color=get_color_from_hex('#0a192f'), bold=True)
        btn_save.bind(on_release=self.save_settings)
        popup_layout.add_widget(btn_save)

        self.popup = Popup(
            title="Controller Settings",
            content=popup_layout, size_hint=(0.95, 0.75),
            background_color=[0.07, 0.13, 0.25, 1]
        )
        self.popup.bind(on_dismiss=lambda x: setattr(self, 'live_preview_label', None))
        self.popup.open()

    # ==========================================
    # DATA FORMAT POPUP (separate)
    # ==========================================
    def show_format_popup(self):
        content = BoxLayout(orientation='vertical', padding='15dp', spacing='10dp')

        scroll = ScrollView(size_hint=(1, 1))
        info_text = (
            "ANALOG MODE (Joystick)\n"
            "Format: V, H, B, P, L, O\\n\n\n"
            "  V = Vertical\n"
            "      0 = Fast Forward\n"
            "      5 = Stop (center)\n"
            "      10 = Fast Back\n\n"
            "  H = Horizontal\n"
            "      0 = Left\n"
            "      5 = Straight (center)\n"
            "      10 = Right\n\n"
            "  B = Brake      (0 / 1)\n"
            "  P = Park       (0 / 1)\n"
            "  L = Head Light (0 / 1)\n"
            "  O = Horn       (0 / 1)\n\n"
            "  Example: 2,5,0,0,1,0\\n\n"
            "──────────────────────────────\n\n"
            "DIGITAL MODE (D-Pad)\n"
            "Format: U, D, L, R, B, P, Hd, Hr\\n\n\n"
            "  U = Up    (0 / 1)\n"
            "  D = Down  (0 / 1)\n"
            "  L = Left  (0 / 1)\n"
            "  R = Right (0 / 1)\n\n"
            "  B  = Brake      (0 / 1)\n"
            "  P  = Park       (0 / 1)\n"
            "  Hd = Head Light (0 / 1)\n"
            "  Hr = Horn       (0 / 1)\n\n"
            "  Example: 1,0,0,0,1,0,0,0\\n\n"
            "──────────────────────────────\n\n"
            "NOTES:\n"
            "  • Only ACTIVE mode's packet is transmitted.\n"
            "  • Mode switch = auto values reset + fresh send.\n"
            "  • Sliders auto-center to 5 on release.\n"
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

    def _repaint_mode_lbl(self, widget, *args):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(rgba=get_color_from_hex('#64ffda'))
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[8])

    def _repaint_live(self, widget, *args):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[8])

    def save_settings(self, btn):
        old_mac = self.mac_address
        self.mac_address = self.mac_input.text.strip()
        try:
            with open('bt_settings.json', 'w') as f:
                json.dump({'MAC': self.mac_address}, f)
        except: pass
        self.popup.dismiss()
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
            except Exception as e:
                print("Setting load error:", e)


if __name__ == "__main__":
    HC05ProApp().run()
