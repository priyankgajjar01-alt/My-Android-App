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
        
        self.val_up = 0
        self.val_down = 0
        self.val_left = 0
        self.val_right = 0
        self.val_brake = 0
        self.val_park = 0
        self.val_head = 0
        self.val_horn = 0
        
        self.last_combined = ""
        self.mac_address = "98:D3:31:F4:XX:XX"
        
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
        self.btn_brake.bind(on_release=lambda x: self.toggle_btn('brake', self.btn_brake))
        
        self.btn_park = Button(text="PARK", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_park.bind(on_release=lambda x: self.toggle_btn('park', self.btn_park))
        
        self.btn_head = Button(text="HEAD", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_head.bind(on_release=lambda x: self.toggle_btn('head', self.btn_head))
        
        self.btn_horn = Button(text="HORN", font_size='16sp', bold=True, background_normal='', background_color=get_color_from_hex('#ff6d00'), color=get_color_from_hex('#ffffff'))
        self.btn_horn.bind(on_press=lambda x: self.press_horn(self.btn_horn), on_release=lambda x: self.release_horn(self.btn_horn))
        
        btn_setting = Button(text="⚙", font_size='26sp', size_hint_x=0.5, background_color=get_color_from_hex('#64ffda'), color=get_color_from_hex('#0a192f'))
        btn_setting.bind(on_release=lambda x: self.show_settings_popup())
        
        for b in [self.btn_brake, self.btn_park, self.btn_head, self.btn_horn, btn_setting]: 
            top_bar.add_widget(b)
        self.main_layout.add_widget(top_bar)

        control_wrap = BoxLayout(orientation='horizontal', padding=12, spacing=15)
        left_side = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing=15)
        
        self.btn_f = GlowButton(text="UP", font_size='28sp', bold=True)
        self.btn_f.key_id = 'UP'
        self.btn_f.bind(state=self.on_dpad_state)
        
        self.btn_b = GlowButton(text="DOWN", font_size='28sp', bold=True)
        self.btn_b.key_id = 'DOWN'
        self.btn_b.bind(state=self.on_dpad_state)
        
        left_side.add_widget(self.btn_f)
        left_side.add_widget(self.btn_b)
        control_wrap.add_widget(left_side)
        
        right_side = BoxLayout(orientation='horizontal', size_hint_x=0.6, spacing=15)
        
        self.btn_l = GlowButton(text="LEFT", font_size='28sp', bold=True)
        self.btn_l.key_id = 'LEFT'
        self.btn_l.bind(state=self.on_dpad_state)
        
        self.btn_r = GlowButton(text="RIGHT", font_size='28sp', bold=True)
        self.btn_r.key_id = 'RIGHT'
        self.btn_r.bind(state=self.on_dpad_state)
        
        right_side.add_widget(self.btn_l)
        right_side.add_widget(self.btn_r)
        control_wrap.add_widget(right_side)
        
        self.main_layout.add_widget(control_wrap)
        return self.main_layout

    def on_start(self):
        Clock.schedule_once(lambda dt: self.start_connection_thread(), 1)

    def start_connection_thread(self):
        mac = self.mac_address.strip()
        if not mac or mac == '98:D3:31:F4:XX:XX':
            self.update_status_bar(False, "Please set MAC Address in Settings")
            return
            
        self.update_status_bar(False, f"Connecting to {mac}...")
        threading.Thread(target=self.connect_task, args=(mac,), daemon=True).start()

    def connect_task(self, mac):
        try:
            if platform != 'android':
                Clock.schedule_once(lambda dt: self.update_status_bar(True, "Simulated Connected Mode!"))
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
        self.update_status_bar(False, "Disconnected")

    @mainthread
    def update_status_bar(self, connected, text_msg):
        self.status_bar.text = text_msg
        with self.status_bar.canvas.before:
            Color(rgba=get_color_from_hex('#00c853' if connected else '#d32f2f'))
            RoundedRectangle(pos=self.status_bar.pos, size=self.status_bar.size)

    def send_combined_data(self):
        packet = f"{self.val_up},{self.val_down},{self.val_left},{self.val_right},{self.val_brake},{self.val_park},{self.val_head},{self.val_horn}\n"
        
        if packet != self.last_combined:
            if self.bt_socket and self.bt_writer:
                try: 
                    self.bt_writer.write(packet.encode('utf-8'))
                    print(f"SENT: {packet.strip()}")
                except Exception as e: 
                    self.disconnect_bluetooth()
            else:
                print(f"SIM-SENT: {packet.strip()}")
            self.last_combined = packet

    def on_dpad_state(self, instance, state):
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

    def toggle_btn(self, type_name, widget):
        self.btn_state[type_name] = not self.btn_state[type_name]
        state = 1 if self.btn_state[type_name] else 0
        
        if type_name == 'brake': self.val_brake = state
        elif type_name == 'park': self.val_park = state
        elif type_name == 'head': self.val_head = state
        
        widget.background_color = get_color_from_hex('#64ffda') if state else get_color_from_hex('#1e3a5f')
        widget.color = get_color_from_hex('#0a192f') if state else get_color_from_hex('#ccd6f6')
        self.send_combined_data()

    def press_horn(self, widget):
        self.val_horn = 1
        widget.background_color = get_color_from_hex('#ffab40')
        self.send_combined_data()

    def release_horn(self, widget):
        self.val_horn = 0
        widget.background_color = get_color_from_hex('#ff6d00')
        self.send_combined_data()

    def show_settings_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        scroll_view = ScrollView()
        grid = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        self.inputs = {}
        
        settings_items = [
            ('MAC Address (Editable)', 'MAC', True),
            ('Up Button Logic', 'UP', False),
            ('Down Button Logic', 'DOWN', False),
            ('Left Button Logic', 'LEFT', False),
            ('Right Button Logic', 'RIGHT', False),
            ('Brake Button Logic', 'BRAKE', False),
            ('Park Button Logic', 'PARK', False),
            ('Head Light Logic', 'HEAD', False),
            ('Horn Button Logic', 'HORN', False),
        ]
        
        for label_text, map_key, is_editable in settings_items:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=10)
            lbl = Label(text=label_text, size_hint=(0.5, 1), color=get_color_from_hex('#ccd6f6'), font_size='15sp', halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            
            val = self.mac_address if map_key == 'MAC' else "Press=1 / Release=0"
            txt_input = TextInput(
                text=val, 
                size_hint=(0.5, 1), 
                multiline=False, 
                readonly=not is_editable,
                background_color=get_color_from_hex('#0a192f'), 
                foreground_color=get_color_from_hex('#64ffda') if is_editable else get_color_from_hex('#8892b0'), 
                font_size='15sp', 
                halign='center'
            )
            row.add_widget(lbl)
            row.add_widget(txt_input)
            grid.add_widget(row)
            
            if is_editable:
                self.mac_input = txt_input

        grid.add_widget(Label(size_hint_y=None, height=15))

        # Format View Button (Instead of long text on main settings screen)
        btn_view_format = Button(
            text="📖 View Data Format & Logic", 
            size_hint_y=None, 
            height=50, 
            font_size='15sp', 
            background_color=get_color_from_hex('#1e3a5f'), 
            color=get_color_from_hex('#64ffda'), 
            bold=True
        )
        btn_view_format.bind(on_release=lambda x: self.show_format_popup())
        grid.add_widget(btn_view_format)
            
        scroll_view.add_widget(grid)
        popup_layout.add_widget(scroll_view)
        
        btn_save = Button(text="Save & Close", size_hint_y=None, height=55, font_size='16sp', background_color=get_color_from_hex('#00c853'), color=get_color_from_hex('#0a192f'), bold=True)
        btn_save.bind(on_release=lambda x: self.save_settings(popup))
        popup_layout.add_widget(btn_save)
        
        popup = Popup(title="Controller Settings", content=popup_layout, size_hint=(0.95, 0.9))
        popup.open()

    def show_format_popup(self):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        format_text = (
            "--- ARDUINO DATA FORMAT ---\n\n"
            "Format Sent: Up,Down,Left,Right,Brake,Park,Head,Horn\\n\n"
            "Values are separated by commas and end with \\n\n\n"
            "Logic:\n"
            "• Press = 1\n"
            "• Release = 0\n\n"
            "Example (Up Pressed + Brake ON):\n"
            "'1,0,0,0,1,0,0,0\\n'"
        )
        
        lbl_format = Label(
            text=format_text, 
            color=get_color_from_hex('#8892b0'), 
            font_size='15sp', 
            halign='center', 
            valign='middle'
        )
        lbl_format.bind(size=lbl_format.setter('text_size'))
        content.add_widget(lbl_format)
        
        btn_close = Button(
            text="Close", 
            size_hint_y=None, 
            height=50, 
            font_size='16sp', 
            background_color=get_color_from_hex('#64ffda'), 
            color=get_color_from_hex('#0a192f'), 
            bold=True
        )
        
        format_popup = Popup(title="Data Format & Visualization", content=content, size_hint=(0.85, 0.5))
        btn_close.bind(on_release=format_popup.dismiss)
        content.add_widget(btn_close)
        
        format_popup.open()

    def save_settings(self, popup):
        old_mac = self.mac_address
        self.mac_address = self.mac_input.text.strip()
        
        with open('bt_settings.json', 'w') as f: 
            json.dump({'MAC': self.mac_address}, f)
        popup.dismiss()
        
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
            except Exception as e: 
                print(e)

if __name__ == "__main__":
    HC05GamepadApp().run()
