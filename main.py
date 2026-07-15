import json
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, BoxShadow
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
    except Exception as e:
        print("Android Pyjnius Import Error:", e)

class GlowButton(Button):
    """HTML ગેમપેડ જેવો જ નિયોન ગ્લો ઇફેક્ટ ધરાવતું કસ્ટમ બટન"""
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
                Color(rgba=get_color_from_hex('#64ffda'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
                BoxShadow(
                    pos=self.pos, size=self.size,
                    offset=(0, 0), blur_radius=25, spread_radius=5,
                    border_radius=[18, 18, 18, 18],
                    shadow_color=get_color_from_hex('#64ffda80')
                )
            else:
                Color(rgba=get_color_from_hex('#1e3a5f'))
                RoundedRectangle(pos=self.pos, size=self.size, radius=[18])
                Color(rgba=get_color_from_hex('#0a192f'))
                RoundedRectangle(
                    pos=(self.pos[0] + 2, self.pos[1] + 2), 
                    size=(self.size[0] - 4, self.size[1] - 4), 
                    radius=[16]
                )

    def on_state_change(self, pressed):
        self.pressed_state = pressed
        if pressed:
            self.color = get_color_from_hex('#0a192f')
        else:
            self.color = get_color_from_hex('#64ffda')
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

        # ૧. Status Bar
        self.status_bar = Label(
            text="Disconnected", size_hint_y=None, height=35,
            color=get_color_from_hex('#ffffff'), font_size='14sp', bold=True
        )
        self.update_status_bar(False)
        self.main_layout.add_widget(self.status_bar)

        # ૨. Top Action Bar (ઊંચાઈ ડબલ કરી, લેબલ હટાવી આખી સ્ક્રીનમાં ફિટ કર્યું)
        top_bar = BoxLayout(size_hint_y=None, height=90, padding=8, spacing=8)
        with top_bar.canvas.before:
            Color(rgba=get_color_from_hex('#112240'))
            RoundedRectangle(pos=top_bar.pos, size=top_bar.size)

        # એક્શન બટન્સ (બધાને આખી જગ્યા સરખે ભાગે મળશે)
        self.btn_brake = Button(text="BRAKE", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_brake.bind(on_release=lambda x: self.toggle_btn('brake', 'K', self.btn_brake))
        top_bar.add_widget(self.btn_brake)

        self.btn_park = Button(text="PARK", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_park.bind(on_release=lambda x: self.toggle_btn('park', 'P', self.btn_park))
        top_bar.add_widget(self.btn_park)

        self.btn_head = Button(text="HEAD", font_size='16sp', bold=True, background_color=get_color_from_hex('#1e3a5f'), color=get_color_from_hex('#ccd6f6'))
        self.btn_head.bind(on_release=lambda x: self.toggle_btn('head', 'H', self.btn_head))
        top_bar.add_widget(self.btn_head)

        self.btn_horn = Button(
            text="HORN", font_size='16sp', bold=True,
            background_normal='', background_color=get_color_from_hex('#ff6d00'),
            color=get_color_from_hex('#ffffff')
        )
        self.btn_horn.bind(on_press=lambda x: self.send_momentary('O', self.btn_horn))
        self.btn_horn.bind(on_release=lambda x: self.release_momentary(self.btn_horn))
        top_bar.add_widget(self.btn_horn)

        # સેટીંગ્સ બટન (થોડું નાનું રાખ્યું છે જેથી બીજા બટન મોટા દેખાય)
        btn_setting = Button(text="⚙", font_size='26sp', size_hint_x=0.5, background_color=get_color_from_hex('#64ffda'), color=get_color_from_hex('#0a192f'))
        btn_setting.bind(on_release=lambda x: self.show_settings_popup())
        top_bar.add_widget(btn_setting)

        self.main_layout.add_widget(top_bar)

        # ૩. Slider & Connect Box (આની ઊંચાઈ પણ વધારી દીધી)
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

        # ૪. Main Controls Wrapper
        control_wrap = BoxLayout(orientation='horizontal', padding=12, spacing=15)

        # ડાબી બાજુ
        left_side = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing=15)
        # તીરના નિશાન ની જગ્યાએ ટેક્સ્ટ યુઝ કર્યું છે જેથી [X] બોક્સ ના આવે
        self.btn_f = GlowButton(text="UP", font_size='28sp', bold=True)
        self.btn_f.bind(on_press=lambda x: self.press_key('F', self.btn_f))
        self.btn_f.bind(on_release=lambda x: self.release_key('F', self.btn_f))
        
        self.btn_b = GlowButton(text="DOWN", font_size='28sp', bold=True)
        self.btn_b.bind(on_press=lambda x: self.press_key('B', self.btn_b))
        self.btn_b.bind(on_release=lambda x: self.release_key('B', self.btn_b))

        left_side.add_widget(self.btn_f)
        left_side.add_widget(self.btn_b)
        control_wrap.add_widget(left_side)

        # જમણી બાજુ
        right_side = BoxLayout(orientation='horizontal', size_hint_x=0.6, spacing=15)
        self.btn_l = GlowButton(text="LEFT", font_size='28sp', bold=True)
        self.btn_l.bind(on_press=lambda x: self.press_key('L', self.btn_l))
        self.btn_l.bind(on_release=lambda x: self.release_key('L', self.btn_l))

        self.btn_r = GlowButton(text="RIGHT", font_size='28sp', bold=True)
        self.btn_r.bind(on_press=lambda x: self.press_key('R', self.btn_r))
        self.btn_r.bind(on_release=lambda x: self.release_key('R', self.btn_r))

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
            if not adapter:
                messagebox_kivy("Error", "બ્લૂટૂથ હાર્ડવેર સપોર્ટ કરતું નથી!")
                return
            if not adapter.isEnabled():
                messagebox_kivy("Bluetooth Disabled", "કૃપા કરીને પહેલા મોબાઈલનું બ્લૂટૂથ ચાલુ કરો!")
                return

            paired_devices = adapter.getBondedDevices().toArray()
            hc05_device = None
            for device in paired_devices:
                if "HC-05" in device.getName() or "HC-06" in device.getName():
                    hc05_device = device
                    break

            if not hc05_device:
                messagebox_kivy("HC-05 Not Found", "તમારા ફોનમાં HC-05 બ્લૂટૂથ પેર કરેલું હોવું જોઈએ!")
                return

            s_uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
            self.bt_socket = hc05_device.createRfcommSocketToServiceRecord(s_uuid)
            self.bt_socket.connect()
            self.bt_writer = self.bt_socket.getOutputStream()

            self.update_status_bar(True)
            self.btn_connect.text = "Disconnect"
            self.btn_connect.background_color = get_color_from_hex('#d32f2f')
            self.send_data(self.btn_map['S'] + "\n")

        except Exception as e:
            self.disconnect_bluetooth()
            messagebox_kivy("Connection Failed", f"કનેક્શન નિષ્ફળ: Pydroid માં બ્લૂટૂથ પરમિશન આપો. {str(e)}")

    def disconnect_bluetooth(self):
        try:
            if self.bt_writer:
                self.bt_writer.close()
            if self.bt_socket and hasattr(self.bt_socket, 'close'):
                self.bt_socket.close()
        except:
            pass
        self.bt_socket = None
        self.bt_writer = None
        self.update_status_bar(False)
        self.btn_connect.text = "Connect"
        self.btn_connect.background_color = get_color_from_hex('#2962ff')

    def send_data(self, data):
        if not self.bt_socket or not self.bt_writer:
            print(f"[No connection] Data not sent: {repr(data)}")
            return
            
        try:
            self.bt_writer.write(bytearray(data, 'utf-8'))
        except Exception as e:
            print("BT Send Error:", e)
            self.disconnect_bluetooth()

    def update_status_bar(self, connected):
        if connected:
            self.status_bar.text = "Connected via Bluetooth Serial Mode!"
            with self.status_bar.canvas.before:
                Color(rgba=get_color_from_hex('#00c853'))
                RoundedRectangle(pos=self.status_bar.pos, size=self.status_bar.size)
        else:
            self.status_bar.text = "Disconnected"
            with self.status_bar.canvas.before:
                Color(rgba=get_color_from_hex('#d32f2f'))
                RoundedRectangle(pos=self.status_bar.pos, size=self.status_bar.size)

    def press_key(self, key, widget):
        widget.on_state_change(True)
        if key == 'F' and 'B' in self.pressed_keys: self.pressed_keys.remove('B')
        if key == 'B' and 'F' in self.pressed_keys: self.pressed_keys.remove('F')
        if key == 'L' and 'R' in self.pressed_keys: self.pressed_keys.remove('R')
        if key == 'R' and 'L' in self.pressed_keys: self.pressed_keys.remove('L')

        self.pressed_keys.add(key)
        self.check_and_send_combo()

    def release_key(self, key, widget):
        widget.on_state_change(False)
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
        self.send_data(self.btn_map['S'] + "\n")

    def check_and_send_combo(self):
        cmd = self.btn_map['S']
        if 'F' in self.pressed_keys and 'L' in self.pressed_keys:
            cmd = self.btn_map['FL']
        elif 'F' in self.pressed_keys and 'R' in self.pressed_keys:
            cmd = self.btn_map['FR']
        elif 'B' in self.pressed_keys and 'L' in self.pressed_keys:
            cmd = self.btn_map['BL']
        elif 'B' in self.pressed_keys and 'R' in self.pressed_keys:
            cmd = self.btn_map['BR']
        elif 'F' in self.pressed_keys:
            cmd = self.btn_map['F']
        elif 'B' in self.pressed_keys:
            cmd = self.btn_map['B']
        elif 'L' in self.pressed_keys:
            cmd = self.btn_map['L']
        elif 'R' in self.pressed_keys:
            cmd = self.btn_map['R']
            
        self.send_data(cmd + "\n")

    def send_momentary(self, key, widget):
        self.send_data(self.btn_map[key] + "\n")
        widget.background_color = get_color_from_hex('#ffab40')

    def release_momentary(self, widget):
        widget.background_color = get_color_from_hex('#ff6d00')

    def on_slider_change(self, instance, value):
        self.speed = int(value)
        self.lbl_speed.text = f"Speed {self.speed}/9:"
        self.send_data(self.btn_map[f'S{self.speed}'] + "\n")

    def toggle_btn(self, type_name, key, widget):
        self.btn_state[type_name] = not self.btn_state[type_name]
        if self.btn_state[type_name]:
            widget.background_color = get_color_from_hex('#64ffda')
            widget.color = get_color_from_hex('#0a192f')
            state = '1'
        else:
            widget.background_color = get_color_from_hex('#1e3a5f')
            widget.color = get_color_from_hex('#ccd6f6')
            state = '0'
        self.send_data(self.btn_map[key] + state + "\n")

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
        for i in range(10):
            keys_to_show.append((f'Speed {i}', f'S{i}'))

        for label_text, map_key in keys_to_show:
            lbl = Label(text=label_text, size_hint_y=None, height=30, color=get_color_from_hex('#ccd6f6'))
            txt_input = TextInput(
                text=self.btn_map[map_key], size_hint_y=None, height=35,
                multiline=False, background_color=get_color_from_hex('#0a192f'),
                foreground_color=get_color_from_hex('#64ffda'), cursor_color=get_color_from_hex('#64ffda')
            )
            grid.add_widget(lbl)
            grid.add_widget(txt_input)
            self.inputs[map_key] = txt_input

        scroll_view.add_widget(grid)
        popup_layout.add_widget(scroll_view)

        btn_save = Button(text="Save & Close", size_hint_y=None, height=50, font_size='16sp', background_color=get_color_from_hex('#00c853'), color=get_color_from_hex('#0a192f'), bold=True)
        popup_layout.add_widget(btn_save)

        popup = Popup(
            title="Button Value Settings", content=popup_layout,
            size_hint=(0.95, 0.9), background_color=get_color_from_hex('#112240')
        )
        btn_save.bind(on_release=lambda x: self.save_settings(popup))
        popup.open()

    def save_settings(self, popup):
        for key, text_widget in self.inputs.items():
            self.btn_map[key] = text_widget.text.strip()
        
        with open('btn_settings.json', 'w') as f:
            json.dump(self.btn_map, f)
        
        popup.dismiss()

    def load_settings(self):
        self.btn_map = {
            'F': 'F', 'B': 'B', 'L': 'L', 'R': 'R', 'S': 'S',
            'K': 'K', 'P': 'P', 'H': 'H', 'O': 'O',
            'FL': 'A', 'FR': 'C', 'BL': 'D', 'BR': 'E',
            'S0': '0', 'S1': '1', 'S2': '2', 'S3': '3', 'S4': '4',
            'S5': '5', 'S6': '6', 'S7': '7', 'S8': '8', 'S9': '9'
        }
        if os.path.exists('btn_settings.json'):
            try:
                with open('btn_settings.json', 'r') as f:
                    self.btn_map.update(json.load(f))
            except:
                pass


def messagebox_kivy(title, text):
    box = BoxLayout(orientation='vertical', padding=10, spacing=10)
    box.add_widget(Label(text=text, color=get_color_from_hex('#ccd6f6')))
    btn_ok = Button(text="OK", size_hint_y=None, height=45, bold=True, background_color=get_color_from_hex('#64ffda'), color=get_color_from_hex('#0a192f'))
    box.add_widget(btn_ok)
    popup = Popup(title=title, content=box, size_hint=(0.8, 0.4))
    btn_ok.bind(on_release=popup.dismiss)
    popup.open()


if __name__ == "__main__":
    HC05GamepadApp().run()
