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
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from kivy.clock import Clock, mainthread

# Android Clipboard support for copy button
try:
    from kivy.core.clipboard import Clipboard
except:
    Clipboard = None

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
# 1. BEAUTIFUL ROUNDED BUTTON CLASS
# ==========================================
class ProButton(Button):
    def __init__(self, bg_hex, **kwargs):
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
                Color(rgba=get_color_from_hex('#64ffda60'))
            else:
                Color(rgba=get_color_from_hex(self.bg_hex))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12])
            
    def set_bg_color(self, new_hex):
        self.bg_hex = new_hex
        self.update_canvas()

# ==========================================
# 2. MASSIVE AUTO-CENTERING THICK SLIDER
# ==========================================
class AutoCenterSlider(Slider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_size = ('110dp', '110dp')
        self.background_width = '45dp'

    def on_touch_up(self, touch):
        if touch.grab_current == self:
            Clock.schedule_once(lambda dt: setattr(self, 'value', 5), 0.05)
        return super().on_touch_up(touch)


class HC05GamepadApp(App):
    def build(self):
        self.title = "HC-05 Pro Gamepad"
        self.bt_socket = None
        self.bt_writer = None
        self.bt_reader = None
        
        self.val_v = 5
        self.val_h = 5
        self.val_brake = 0
        self.val_park = 0
        self.val_head = 0
        self.val_horn = 0
        self.last_combined = ""
        self.mac_address = "98:D3:31:F4:XX:XX"

        self.load_settings()

        # ==========================================
        # MAIN UI LAYOUT
        # ==========================================
        self.main_layout = BoxLayout(orientation='vertical')
        with self.main_layout.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            RoundedRectangle(pos=(0, 0), size=(10000, 10000))

        # STATUS BAR
        self.status_bar = Label(text="Initializing Auto-Connect...", size_hint_y=None, height='25dp', color=get_color_from_hex('#ffffff'), font_size='12sp', bold=True)
        self.update_status_bar(False, "Initializing Auto-Connect...")
        self.main_layout.add_widget(self.status_bar)

        # TOP BAR (5 Buttons)
        top_bar = BoxLayout(size_hint_y=None, height='50dp', padding='5dp', spacing='5dp')
        
        self.btn_brake = ProButton(bg_hex='#1e3a5f', text="BRAKE", font_size='13sp', bold=True, color=get_color_from_hex('#ccd6f6'))
        self.btn_brake.bind(on_release=self.toggle_brake)
        
        self.btn_park = ProButton(bg_hex='#1e3a5f', text="PARK", font_size='13sp', bold=True, color=get_color_from_hex('#ccd6f6'))
        self.btn_park.bind(on_release=self.toggle_park)
        
        self.btn_head = ProButton(bg_hex='#1e3a5f', text="HEAD", font_size='13sp', bold=True, color=get_color_from_hex('#ccd6f6'))
        self.btn_head.bind(on_release=self.toggle_head)
        
        self.btn_horn = ProButton(bg_hex='#ff6d00', text="HORN", font_size='13sp', bold=True, color=get_color_from_hex('#ffffff'))
        self.btn_horn.bind(on_press=self.press_horn, on_release=self.release_horn)
        
        btn_setting = ProButton(bg_hex='#64ffda', text="SETTING", font_size='13sp', bold=True, color=get_color_from_hex('#0a192f'))
        btn_setting.bind(on_release=lambda x: self.show_settings_popup())
        
        for b in [self.btn_brake, self.btn_park, self.btn_head, self.btn_horn, btn_setting]: 
            top_bar.add_widget(b)
        self.main_layout.add_widget(top_bar)

        # ==========================================
        # MASSIVE JOYSTICKS
        # ==========================================
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
        
        self.main_layout.add_widget(control_wrap)
        return self.main_layout

    # ==========================================
    # BLUETOOTH AUTO-CONNECT
    # ==========================================
    def on_start(self):
        Clock.schedule_once(lambda dt: self.start_connection_thread(), 1)

    def start_connection_thread(self):
        mac = self.mac_address.strip()
        if not mac or mac == '98:D3:31:F4:XX:XX':
            self.update_status_bar(False, "No MAC Address! Update in Settings")
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

    # ==========================================
    # SINGLE PACKET SENDER
    # ==========================================
    def send_combined_data(self):
        packet = f"{self.val_v},{self.val_h},{self.val_brake},{self.val_park},{self.val_head},{self.val_horn}\n"
        
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

    def on_v_slider(self, instance, value):
        self.val_v = 10 - int(value)
        self.send_combined_data()

    def on_h_slider(self, instance, value):
        self.val_h = int(value)
        self.send_combined_data()

    def toggle_brake(self, btn):
        self.val_brake = 1 if self.val_brake == 0 else 0
        btn.set_bg_color('#64ffda' if self.val_brake else '#1e3a5f')
        btn.color = get_color_from_hex('#0a192f') if self.val_brake else get_color_from_hex('#ccd6f6')
        self.send_combined_data()

    def toggle_park(self, btn):
        self.val_park = 1 if self.val_park == 0 else 0
        btn.set_bg_color('#64ffda' if self.val_park else '#1e3a5f')
        btn.color = get_color_from_hex('#0a192f') if self.val_park else get_color_from_hex('#ccd6f6')
        self.send_combined_data()

    def toggle_head(self, btn):
        self.val_head = 1 if self.val_head == 0 else 0
        btn.set_bg_color('#64ffda' if self.val_head else '#1e3a5f')
        btn.color = get_color_from_hex('#0a192f') if self.val_head else get_color_from_hex('#ccd6f6')
        self.send_combined_data()

    def press_horn(self, btn):
        self.val_horn = 1
        btn.set_bg_color('#ffab40')
        self.send_combined_data()

    def release_horn(self, btn):
        self.val_horn = 0
        btn.set_bg_color('#ff6d00')
        self.send_combined_data()

    # ==========================================
    # SETTINGS UI (Non-Selectable Label View)
    # ==========================================
    def show_settings_popup(self):
        popup_layout = BoxLayout(orientation='vertical', padding='15dp', spacing='15dp')
        
        scroll = ScrollView(size_hint=(1, 1))
        box = BoxLayout(orientation='vertical', spacing='15dp', size_hint_y=None)
        box.bind(minimum_height=box.setter('height'))
        
        lbl_mac = Label(text="HC-05 MAC Address (Editable)", size_hint_y=None, height='30dp', color=get_color_from_hex('#ccd6f6'), font_size='16sp', bold=True)
        box.add_widget(lbl_mac)
        
        self.mac_input = TextInput(text=self.mac_address, size_hint_y=None, height='50dp', multiline=False, background_color=get_color_from_hex('#0a192f'), foreground_color=get_color_from_hex('#64ffda'), font_size='22sp', halign='center')
        box.add_widget(self.mac_input)
        
        box.add_widget(Label(size_hint_y=None, height='10dp'))
        
        info_text = (
            "--- ARDUINO DATA FORMAT ---\n\n"
            "Format: V, H, B, P, L, O \\n\n"
            "Values are separated by commas and end with \\n\n\n"
            "[ V ] Vertical Joystick (Speed & Direction):\n"
            "      0 to 4 = Moving FORWARD / UP (0 is max speed)\n"
            "      5      = STOP (Center / Neutral)\n"
            "      6 to 10 = Moving BACKWARD / DOWN (10 is max speed)\n\n"
            "[ H ] Horizontal Joystick (Steering):\n"
            "      0 to 4 = Turning LEFT (0 is max left)\n"
            "      5      = STRAIGHT (Center / Neutral)\n"
            "      6 to 10 = Turning RIGHT (10 is max right)\n\n"
            "--- BUTTONS (1 = ON, 0 = OFF) ---\n"
            "[ B ] Brake Button\n"
            "[ P ] Park Button\n"
            "[ L ] Head Light Button\n"
            "[ O ] Horn Button\n\n"
            "Example Packet (Moving Forward + Light ON):\n"
            "'2,5,0,0,1,0\\n'"
        )
        
        lbl_info = Label(text="Data Packet Visualization (Read Only)", size_hint_y=None, height='30dp', color=get_color_from_hex('#ccd6f6'), font_size='16sp', bold=True)
        box.add_widget(lbl_info)
        
        # AHIYA LABEL VAPARYU CHE JETHI COPY KE SELECT NA THAY (Pure Visualization)
        self.info_label = Label(
            text=info_text, 
            size_hint_y=None, 
            height='450dp', 
            color=get_color_from_hex('#8892b0'), 
            font_size='14sp', 
            halign='left', 
            valign='top'
        )
        self.info_label.bind(size=self.info_label.setter('text_size')) # Text ne left align rakhva mate
        
        # Label ni pachal dark background box banavva mate
        with self.info_label.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            self.info_bg = RoundedRectangle(pos=self.info_label.pos, size=self.info_label.size, radius=[8])
        self.info_label.bind(pos=self.update_info_bg, size=self.update_info_bg)
        
        box.add_widget(self.info_label)
        
        scroll.add_widget(box)
        popup_layout.add_widget(scroll)
        
        btn_save = ProButton(bg_hex='#00c853', text="SAVE & RECONNECT", size_hint_y=None, height='55dp', font_size='18sp', color=get_color_from_hex('#0a192f'), bold=True)
        btn_save.bind(on_release=self.save_settings)
        popup_layout.add_widget(btn_save)
        
        self.popup = Popup(title="Controller Settings & Logic", content=popup_layout, size_hint=(0.95, 0.95), background_color=[0.07, 0.13, 0.25, 1])
        self.popup.open()

    def update_info_bg(self, instance, *args):
        self.info_bg.pos = instance.pos
        self.info_bg.size = instance.size

    def save_settings(self, btn):
        old_mac = self.mac_address
        self.mac_address = self.mac_input.text.strip()
        
        with open('bt_settings.json', 'w') as f: 
            json.dump({'MAC': self.mac_address}, f)
            
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
            except Exception as e: 
                print("Setting load error:", e)

if __name__ == "__main__":
    HC05GamepadApp().run()
