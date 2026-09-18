import json
import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty

# Android Bluetooth integration
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
    except Exception as e:
        print("Android Pyjnius Import Error:", e)


# ==========================================
# ADVANCED GLOW BUTTON (Custom Area-Based Swipe)
# ==========================================
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


class HC05GamepadApp(App):
    def build(self):
        self.title = "HC-05 Pro Gamepad"
        self.btn_state = {'brake': False, 'park': False, 'head': False}
        self.pressed_keys = set()
        self.speed = 4
        self.bt_socket = None
        self.bt_writer = None
        self.bt_reader = None

        self.load_settings()

        self.main_layout = BoxLayout(orientation='vertical')
        with self.main_layout.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        self.status_bar = Label(text="Initializing...", size_hint_y=None, height=35, color=get_color_from_hex('#ffffff'), font_size='14sp', bold=True)
        self.update_status_bar(False, "Initializing...")
        self.main_layout.add_widget(self.status_bar)

        top_bar = BoxLayout(size_hint_y=None, height=90, padding=8, spacing=8)
        self.btn_brake = Button(text="BRAKE", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_brake.bind(on_release=lambda x: self.toggle_btn('brake', 'K', self.btn_brake))
        self.btn_park = Button(text="PARK", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_park.bind(on_release=lambda x: self.toggle_btn('park', 'P', self.btn_park))
        self.btn_head = Button(text="HEAD", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_head.bind(on_release=lambda x: self.toggle_btn('head', 'H', self.btn_head))
        self.btn_horn = Button(text="HORN", font_size='16sp', bold=True, background_normal='', background_color=get_color_from_hex('#ff6d00'), color=get_color_from_hex('#ffffff'))
        self.btn_horn.bind(on_press=lambda x: self.send_momentary('O', self.btn_horn), on_release=lambda x: self.release_momentary(self.btn_horn))
        btn_setting = Button(text="⚙", font_size='26sp', size_hint_x=0.5, background_color=get_color_from_hex('#64ffda'), color=get_color_from_hex('#0a192f'))
        btn_setting.bind(on_release=lambda x: self.show_settings_popup())
        
        for b in [self.btn_brake, self.btn_park, self.btn_head, self.btn_horn, btn_setting]: 
            top_bar.add_widget(b)
        self.main_layout.add_widget(top_bar)

        slider_box = BoxLayout(size_hint_y=None, height=75, padding=10, spacing=10)
        self.lbl_speed = Label(text=f"Speed {self.speed}/9:", font_size='16sp', bold=True, color=get_color_from_hex('#8892b0'), size_hint_x=0.3)
        self.speed_slider = Slider(min=0, max=9, value=self.speed, step=1, size_hint_x=0.7)
        self.speed_slider.bind(value=self.on_slider_change)
        slider_box.add_widget(self.lbl_speed)
        slider_box.add_widget(self.speed_slider)
        self.main_layout.add_widget(slider_box)

        control_wrap = BoxLayout(orientation='horizontal', padding=12, spacing=15)
        left_side = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing=15)
        
        self.btn_f = GlowButton(text="UP", font_size='28sp', bold=True)
        self.btn_f.key_id = 'F'
        self.btn_f.bind(state=self.on_dpad_state)
        
        self.btn_b = GlowButton(text="DOWN", font_size='28sp', bold=True)
        self.btn_b.key_id = 'B'
        self.btn_b.bind(state=self.on_dpad_state)
        
        left_side.add_widget(self.btn_f)
        left_side.add_widget(self.btn_b)
        control_wrap.add_widget(left_side)
        
        right_side = BoxLayout(orientation='horizontal', size_hint_x=0.6, spacing=15)
        
        self.btn_l = GlowButton(text="LEFT", font_size='28sp', bold=True)
        self.btn_l.key_id = 'L'
        self.btn_l.bind(state=self.on_dpad_state)
        
        self.btn_r = GlowButton(text="RIGHT", font_size='28sp', bold=True)
        self.btn_r.key_id = 'R'
        self.btn_r.bind(state=self.on_dpad_state)
        
        right_side.add_widget(self.btn_l)
        right_side.add_widget(self.btn_r)
        control_wrap.add_widget(right_side)
        
        self.main_layout.add_widget(control_wrap)
        return self.main_layout


    # ==========================================
    # BLUETOOTH AUTO-CONNECT & DISCONNECT LOGIC
    # ==========================================
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions
            try:
                request_permissions([
                    'android.permission.BLUETOOTH_CONNECT',
                    'android.permission.BLUETOOTH_SCAN',
                    'android.permission.ACCESS_FINE_LOCATION'
                ])
            except: pass
            Clock.schedule_once(lambda dt: self.start_connection_thread(), 2)
        else:
            self.update_status_bar(False, "Simulated Mode (PC)")

    def start_connection_thread(self):
        mac = self.btn_map.get('MAC', '').strip()
        if not mac or mac == '98:D3:31:F4:XX:XX':
            self.update_status_bar(False, "Please set MAC Address in Settings")
            return
            
        self.update_status_bar(False, f"Connecting to {mac}...")
        threading.Thread(target=self.connect_task, args=(mac,), daemon=True).start()

    def connect_task(self, mac):
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter and adapter.isDiscovering(): 
                adapter.cancelDiscovery()
                
            device = adapter.getRemoteDevice(mac)
            s_uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
            
            self.bt_socket = device.createRfcommSocketToServiceRecord(s_uuid)
            self.bt_socket.connect()
            self.bt_writer = self.bt_socket.getOutputStream()
            self.bt_reader = BufferedReader(InputStreamReader(self.bt_socket.getInputStream()))
            
            Clock.schedule_once(lambda dt: self.on_connection_success())
            
            while True:
                data = self.bt_reader.readLine()
                if data is None:
                    break
        except Exception as e:
            print("BT Error:", e)
            
        Clock.schedule_once(lambda dt: self.disconnect_bluetooth())

    def on_connection_success(self):
        self.update_status_bar(True, "Connected via Bluetooth!")
        cmd = self.btn_map.get('S', 'S')
        if cmd.lower() != "no action":
            self.send_data(cmd + "\n")

    def disconnect_bluetooth(self):
        try:
            if self.bt_writer: self.bt_writer.close()
            if self.bt_reader: self.bt_reader.close()
            if self.bt_socket: self.bt_socket.close()
        except: pass
        self.bt_socket = None
        self.bt_writer = None
        self.bt_reader = None
        self.update_status_bar(False, "Disconnected")

    @mainthread
    def update_status_bar(self, connected, text_msg):
        self.status_bar.text = text_msg
        with self.status_bar.canvas.before:
            Color(rgba=get_color_from_hex('#00c853' if connected else '#d32f2f'))
            RoundedRectangle(pos=self.status_bar.pos, size=self.status_bar.size)

    def send_data(self, data):
        if self.bt_socket and self.bt_writer:
            try: 
                self.bt_writer.write(data.encode('utf-8'))
            except Exception as e: 
                self.disconnect_bluetooth()

    # ==========================================
    # DPAD CONTROL LOGIC (ANTI-GHOSTING & SAFETY)
    # ==========================================
    def on_dpad_state(self, instance, state):
        key = instance.key_id
        if state == 'down':
            self.press_key(key)
        else:
            self.release_key(key)

    def press_key(self, key):
        # AHIYA FIX THAYU CHE: UP ane DOWN ek sathe press thava par block kari dese
        if key == 'F' and self.btn_b.state == 'down':
            self.btn_b.active_touches.clear()
            self.btn_b.state = 'normal'
        elif key == 'B' and self.btn_f.state == 'down':
            self.btn_f.active_touches.clear()
            self.btn_f.state = 'normal'
            
        # AHIYA FIX THAYU CHE: LEFT ane RIGHT ek sathe press thava par block kari dese
        if key == 'L' and self.btn_r.state == 'down':
            self.btn_r.active_touches.clear()
            self.btn_r.state = 'normal'
        elif key == 'R' and self.btn_l.state == 'down':
            self.btn_l.active_touches.clear()
            self.btn_l.state = 'normal'
            
        self.pressed_keys.add(key)
        self.check_and_send_combo()

    def release_key(self, key):
        if key in self.pressed_keys:
            self.pressed_keys.discard(key)
                
            if not self.pressed_keys: 
                cmd = self.btn_map.get('S', 'S')
                if cmd.lower() != "no action":
                    self.send_data(cmd + "\n")
            else: 
                self.check_and_send_combo()

    def check_and_send_combo(self):
        cmd = self.btn_map.get('S', 'S')
        if 'F' in self.pressed_keys and 'L' in self.pressed_keys: cmd = self.btn_map.get('FL', 'A')
        elif 'F' in self.pressed_keys and 'R' in self.pressed_keys: cmd = self.btn_map.get('FR', 'C')
        elif 'B' in self.pressed_keys and 'L' in self.pressed_keys: cmd = self.btn_map.get('BL', 'D')
        elif 'B' in self.pressed_keys and 'R' in self.pressed_keys: cmd = self.btn_map.get('BR', 'E')
        elif 'F' in self.pressed_keys: cmd = self.btn_map.get('F', 'F')
        elif 'B' in self.pressed_keys: cmd = self.btn_map.get('B', 'B')
        elif 'L' in self.pressed_keys: cmd = self.btn_map.get('L', 'L')
        elif 'R' in self.pressed_keys: cmd = self.btn_map.get('R', 'R')
        self.send_data(cmd + "\n")

    def send_momentary(self, key, widget):
        self.send_data(self.btn_map.get(key, key) + "\n")
        widget.background_color = get_color_from_hex('#ffab40')

    def release_momentary(self, widget):
        widget.background_color = get_color_from_hex('#ff6d00')

    def on_slider_change(self, instance, value):
        self.speed = int(value)
        self.lbl_speed.text = f"Speed {self.speed}/9:"
        self.send_data(self.btn_map.get(f'S{self.speed}', str(self.speed)) + "\n")

    def toggle_btn(self, type_name, key, widget):
        self.btn_state[type_name] = not self.btn_state[type_name]
        state = '1' if self.btn_state[type_name] else '0'
        widget.background_color = get_color_from_hex('#64ffda') if self.btn_state[type_name] else get_color_from_hex('#1e3a5f')
        widget.color = get_color_from_hex('#0a192f') if self.btn_state[type_name] else get_color_from_hex('#ccd6f6')
        self.send_data(self.btn_map.get(key, key) + state + "\n")

    # ==========================================
    # SETTINGS LOGIC
    # ==========================================
    def show_settings_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        scroll_view = ScrollView()
        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        self.inputs = {}
        keys_to_show = [
            ('MAC Address', 'MAC'),
            ('Forward (F)', 'F'), 
            ('Backward (B)', 'B'), 
            ('Left (L)', 'L'), 
            ('Right (R)', 'R'), 
            ('Stop / Release (Type "No Action")', 'S'), 
            ('Brake (K)', 'K'), 
            ('Park Light (P)', 'P'), 
            ('Head Light (H)', 'H'), 
            ('Horn (O)', 'O'), 
            ('F + L Combo', 'FL'), 
            ('F + R Combo', 'FR'), 
            ('B + L Combo', 'BL'), 
            ('B + R Combo', 'BR')
        ]
        
        for i in range(10): 
            keys_to_show.append((f'Speed {i}', f'S{i}'))
            
        for label_text, map_key in keys_to_show:
            lbl = Label(text=label_text, size_hint=(0.6, None), height=45, color=get_color_from_hex('#ccd6f6'), font_size='15sp')
            grid.add_widget(lbl)
            txt_input = TextInput(text=self.btn_map.get(map_key, ''), size_hint=(0.4, None), height=45, multiline=False, background_color=get_color_from_hex('#0a192f'), foreground_color=get_color_from_hex('#64ffda'), cursor_color=get_color_from_hex('#64ffda'), font_size='16sp', halign='center')
            grid.add_widget(txt_input)
            self.inputs[map_key] = txt_input
            
        scroll_view.add_widget(grid)
        popup_layout.add_widget(scroll_view)
        
        btn_save = Button(text="Save & Close", size_hint_y=None, height=55, font_size='16sp', background_color=get_color_from_hex('#00c853'), color=get_color_from_hex('#0a192f'), bold=True)
        popup_layout.add_widget(btn_save)
        
        popup = Popup(title="Button Value Settings", content=popup_layout, size_hint=(0.95, 0.9))
        btn_save.bind(on_release=lambda x: self.save_settings(popup))
        popup.open()

    def save_settings(self, popup):
        old_mac = self.btn_map.get('MAC', '')
        for key, text_widget in self.inputs.items(): 
            self.btn_map[key] = text_widget.text.strip()
            
        with open('btn_settings.json', 'w') as f: 
            json.dump(self.btn_map, f)
        popup.dismiss()
        
        new_mac = self.btn_map.get('MAC', '')
        if old_mac != new_mac:
            self.disconnect_bluetooth()
            self.start_connection_thread()

    def load_settings(self):
        self.btn_map = {
            'MAC': '98:D3:31:F4:XX:XX',
            'F':'F', 'B':'B', 'L':'L', 'R':'R', 'S':'S', 
            'K':'K', 'P':'P', 'H':'H', 'O':'O', 
            'FL':'A', 'FR':'C', 'BL':'D', 'BR':'E'
        }
        for i in range(10): 
            self.btn_map[f'S{i}'] = str(i)
            
        if os.path.exists('btn_settings.json'):
            try: 
                with open('btn_settings.json', 'r') as f: 
                    self.btn_map.update(json.load(f))
            except Exception as e: 
                print(e)

if __name__ == "__main__":
    HC05GamepadApp().run()
