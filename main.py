import json
import os
import time
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

# Android Bluetooth integration via Pyjnius
BluetoothAdapter = None
BluetoothDevice = None
UUID = None

if platform == 'android':
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
        UUID = autoclass('java.util.UUID')
        
        # 🚀 FIX: Android 12+ માટે "Allow" વાળું પોપઅપ લાવવા માટેનો કોડ
        try:
            from android.permissions import request_permissions
            request_permissions([
                'android.permission.BLUETOOTH_CONNECT',
                'android.permission.BLUETOOTH_SCAN',
                'android.permission.ACCESS_FINE_LOCATION'
            ])
        except ImportError:
            print("Pydroid 3 માં પરમિશન પોપઅપ ની જરૂર નથી.")
            
    except Exception as e:
        print("Android Pyjnius Import Error:", e)

class GlowButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.pressed_state = False
        self.bind(pos=self.draw_button, size=self.draw_button)

    def draw_button(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.pressed_state:
                Color(rgba=get_color_from_hex('#64ffda40')) 
                RoundedRectangle(pos=(self.pos[0] - 5, self.pos[1] - 5), size=(self.size[0] + 10, self.size[1] + 10), radius=[22])
                
                Color(rgba=get_color_from_hex('#64ffda'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
            else:
                Color(rgba=get_color_from_hex('#1e3a5f'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
                Color(rgba=get_color_from_hex('#0a192f'))
                RoundedRectangle(pos=(self.pos[0] + 2, self.pos[1] + 2), size=(self.size[0] - 4, self.size[1] - 4), radius=[16])

    def on_state_change(self, pressed):
        self.pressed_state = pressed
        self.color = get_color_from_hex('#0a192f') if pressed else get_color_from_hex('#64ffda')
        self.draw_button()


class HC05GamepadApp(App):
    def build(self):
        self.title = "HC-05 Pro Gamepad"
        self.btn_state = {'brake': False, 'park': False, 'head': False}
        self.pressed_keys = set()
        self.speed = 4
        self.bt_socket = None
        self.bt_writer = None

        self.load_settings()

        self.main_layout = BoxLayout(orientation='vertical')
        with self.main_layout.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        self.status_bar = Label(text="Disconnected", size_hint_y=None, height=35, color=get_color_from_hex('#ffffff'), font_size='14sp', bold=True)
        self.update_status_bar(False)
        self.main_layout.add_widget(self.status_bar)

        top_bar = BoxLayout(size_hint_y=None, height=90, padding=8, spacing=8)
        with top_bar.canvas.before:
            Color(rgba=get_color_from_hex('#112240'))
            RoundedRectangle(pos=top_bar.pos, size=top_bar.size)

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
        slider_box.add_widget(self.lbl_speed)

        self.speed_slider = Slider(min=0, max=9, value=self.speed, step=1, size_hint_x=0.5)
        self.speed_slider.bind(value=self.on_slider_change)
        slider_box.add_widget(self.speed_slider)

        self.btn_connect = Button(text="Connect", font_size='16sp', bold=True, size_hint_x=0.3, background_color=get_color_from_hex('#2962ff'), color=get_color_from_hex('#ffffff'))
        self.btn_connect.bind(on_release=lambda x: self.toggle_bluetooth())
        slider_box.add_widget(self.btn_connect)
        self.main_layout.add_widget(slider_box)

        control_wrap = BoxLayout(orientation='horizontal', padding=12, spacing=15)

        left_side = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing=15)
        self.btn_f = GlowButton(text="UP", font_size='28sp', bold=True)
        self.btn_f.bind(on_press=lambda x: self.press_key('F', self.btn_f), on_release=lambda x: self.release_key('F', self.btn_f))
        
        self.btn_b = GlowButton(text="DOWN", font_size='28sp', bold=True)
        self.btn_b.bind(on_press=lambda x: self.press_key('B', self.btn_b), on_release=lambda x: self.release_key('B', self.btn_b))
        left_side.add_widget(self.btn_f)
        left_side.add_widget(self.btn_b)
        control_wrap.add_widget(left_side)

        right_side = BoxLayout(orientation='horizontal', size_hint_x=0.6, spacing=15)
        self.btn_l = GlowButton(text="LEFT", font_size='28sp', bold=True)
        self.btn_l.bind(on_press=lambda x: self.press_key('L', self.btn_l), on_release=lambda x: self.release_key('L', self.btn_l))
        
        self.btn_r = GlowButton(text="RIGHT", font_size='28sp', bold=True)
        self.btn_r.bind(on_press=lambda x: self.press_key('R', self.btn_r), on_release=lambda x: self.release_key('R', self.btn_r))
        right_side.add_widget(self.btn_l)
        right_side.add_widget(self.btn_r)
        control_wrap.add_widget(right_side)

        self.main_layout.add_widget(control_wrap)
        return self.main_layout

    def toggle_bluetooth(self):
        if self.bt_socket:
            self.disconnect_bluetooth()
            return
        if platform != 'android' or BluetoothAdapter is None:
            self.update_status_bar(True)
            self.btn_connect.text = "Disconnect"
            self.btn_connect.background_color = get_color_from_hex('#d32f2f')
            self.bt_socket = "PC_DUMMY_CONNECTION"
            return
            
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.messagebox_kivy("Bluetooth Disabled", "કૃપા કરીને પહેલા મોબાઈલનું બ્લૂટૂથ ચાલુ કરો!")
                return
                
            paired_devices = adapter.getBondedDevices().toArray()
            hc05_device = next((d for d in paired_devices if "HC-05" in d.getName() or "HC-06" in d.getName()), None)
            
            if not hc05_device:
                self.messagebox_kivy("HC-05 Not Found", "તમારા ફોનમાં HC-05 બ્લૂટૂથ પેર કરેલું હોવું જોઈએ!")
                return
                
            s_uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
            
            # --- Android 14+ માટે Secure + Insecure નો ડબલ પ્રયાસ ---
            time.sleep(0.5) # પરમિશન સેટ થવા માટે થોડો સમય 
            try:
                self.bt_socket = hc05_device.createRfcommSocketToServiceRecord(s_uuid)
                self.bt_socket.connect()
            except Exception as e:
                print("Secure connection failed, trying Insecure...", e)
                try:
                    self.bt_socket = hc05_device.createInsecureRfcommSocketToServiceRecord(s_uuid)
                    self.bt_socket.connect()
                except Exception as e2:
                    raise Exception(f"Failed to connect (Secure & Insecure): {e2}")
            # ---------------------------------------------------------

            self.bt_writer = self.bt_socket.getOutputStream()

            self.update_status_bar(True)
            self.btn_connect.text = "Disconnect"
            self.btn_connect.background_color = get_color_from_hex('#d32f2f')
            self.send_data(self.btn_map.get('S', 'S') + "\n")
            
        except Exception as e:
            self.disconnect_bluetooth()
            self.messagebox_kivy("Connection Failed", str(e))

    def disconnect_bluetooth(self):
        try:
            if self.bt_writer: self.bt_writer.close()
            if self.bt_socket and hasattr(self.bt_socket, 'close'): self.bt_socket.close()
        except: pass
        self.bt_socket = None; self.bt_writer = None
        self.update_status_bar(False)
        self.btn_connect.text = "Connect"
        self.btn_connect.background_color = get_color_from_hex('#2962ff')

    def send_data(self, data):
        try:
            print(f"[Command Generated] Data: {repr(data)}")
            if self.bt_socket and self.bt_writer:
                try:
                    self.bt_writer.write(data.encode('utf-8'))
                except Exception as java_e:
                    print(f"Bluetooth Send Error: {java_e}")
                    self.disconnect_bluetooth()
        except Exception as general_e:
            print(f"Safety Catch in send_data: {general_e}")

    def update_status_bar(self, connected):
        self.status_bar.text = "Connected via Bluetooth!" if connected else "Disconnected"
        with self.status_bar.canvas.before:
            Color(rgba=get_color_from_hex('#00c853' if connected else '#d32f2f'))
            RoundedRectangle(pos=self.status_bar.pos, size=self.status_bar.size)

    def press_key(self, key, widget):
        # 1. UP અને DOWN ક્યારેય સાથે ના ચાલે
        if key == 'F' and 'B' in self.pressed_keys:
            self.pressed_keys.discard('B')
            self.btn_b.on_state_change(False)
        elif key == 'B' and 'F' in self.pressed_keys:
            self.pressed_keys.discard('F')
            self.btn_f.on_state_change(False)
            
        # 2. LEFT અને RIGHT ક્યારેય સાથે ના ચાલે
        if key == 'L' and 'R' in self.pressed_keys:
            self.pressed_keys.discard('R')
            self.btn_r.on_state_change(False)
        elif key == 'R' and 'L' in self.pressed_keys:
            self.pressed_keys.discard('L')
            self.btn_l.on_state_change(False)

        widget.on_state_change(True)
        self.pressed_keys.add(key)
        self.check_and_send_combo()

    def release_key(self, key, widget):
        widget.on_state_change(False)
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
        
        if not self.pressed_keys:
            self.send_data(self.btn_map.get('S', 'S') + "\n")
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
        speed_key = f'S{self.speed}'
        self.send_data(self.btn_map.get(speed_key, str(self.speed)) + "\n")

    def toggle_btn(self, type_name, key, widget):
        self.btn_state[type_name] = not self.btn_state[type_name]
        state = '1' if self.btn_state[type_name] else '0'
        widget.background_color = get_color_from_hex('#64ffda') if self.btn_state[type_name] else get_color_from_hex('#1e3a5f')
        widget.color = get_color_from_hex('#0a192f') if self.btn_state[type_name] else get_color_from_hex('#ccd6f6')
        self.send_data(self.btn_map.get(key, key) + state + "\n")

    def show_settings_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        scroll_view = ScrollView()
        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        self.inputs = {}
        keys_to_show = [
            ('Forward (F)', 'F'), ('Backward (B)', 'B'), ('Left (L)', 'L'), ('Right (R)', 'R'),
            ('Stop (S)', 'S'), ('Brake (K)', 'K'), ('Park Light (P)', 'P'), ('Head Light (H)', 'H'),
            ('Horn (O)', 'O'), ('F + L Combo', 'FL'), ('F + R Combo', 'FR'), ('B + L Combo', 'BL'), ('B + R Combo', 'BR')
        ]
        for i in range(10): keys_to_show.append((f'Speed {i}', f'S{i}'))

        for label_text, map_key in keys_to_show:
            lbl = Label(text=label_text, size_hint=(0.6, None), height=45, color=get_color_from_hex('#ccd6f6'), font_size='15sp', halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            
            txt_input = TextInput(
                text=self.btn_map.get(map_key, ''), size_hint=(0.4, None), height=45,
                multiline=False, background_color=get_color_from_hex('#0a192f'),
                foreground_color=get_color_from_hex('#64ffda'), cursor_color=get_color_from_hex('#64ffda'),
                font_size='16sp', halign='center'
            )
            txt_input.bind(size=lambda instance, value: setattr(instance, 'padding', [10, (instance.height - instance.line_height) / 2, 10, 0]))

            grid.add_widget(lbl)
            grid.add_widget(txt_input)
            self.inputs[map_key] = txt_input

        scroll_view.add_widget(grid)
        popup_layout.add_widget(scroll_view)

        btn_save = Button(text="Save & Close", size_hint_y=None, height=55, font_size='16sp', background_color=get_color_from_hex('#00c853'), color=get_color_from_hex('#0a192f'), bold=True)
        popup_layout.add_widget(btn_save)
        
        popup = Popup(title="Button Value Settings", content=popup_layout, size_hint=(0.95, 0.9), background_color=get_color_from_hex('#112240'))
        btn_save.bind(on_release=lambda x: self.save_settings(popup))
        popup.open()

    def save_settings(self, popup):
        for key, text_widget in self.inputs.items(): 
            self.btn_map[key] = text_widget.text.strip()
        with open('btn_settings.json', 'w') as f: 
            json.dump(self.btn_map, f)
        popup.dismiss()

    def load_settings(self):
        self.btn_map = {'F':'F', 'B':'B', 'L':'L', 'R':'R', 'S':'S', 'K':'K', 'P':'P', 'H':'H', 'O':'O', 'FL':'A', 'FR':'C', 'BL':'D', 'BR':'E'}
        for i in range(10): self.btn_map[f'S{i}'] = str(i)
        if os.path.exists('btn_settings.json'):
            try: 
                with open('btn_settings.json', 'r') as f: self.btn_map.update(json.load(f))
            except Exception as e: print("Setting Load Error:", e)

    def messagebox_kivy(self, title, text):
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        lbl = Label(text=text, color=get_color_from_hex('#ccd6f6'), halign='center', valign='middle')
        lbl.bind(size=lbl.setter('text_size')) 
        box.add_widget(lbl)
        
        btn_ok = Button(text="OK", size_hint_y=None, height=45, bold=True, background_color=get_color_from_hex('#64ffda'), color=get_color_from_hex('#0a192f'))
        box.add_widget(btn_ok)
        
        popup = Popup(title=title, content=box, size_hint=(0.85, 0.5))
        btn_ok.bind(on_release=popup.dismiss)
        popup.open()

if __name__ == "__main__":
    HC05GamepadApp().run()
