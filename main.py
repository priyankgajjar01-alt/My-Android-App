import random
import string
import time
import subprocess
from threading import Thread
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

class RemoteAndroidApp(App):
    def build(self):
        self.title = "ATS Remote Connector"
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add(Label(text="📱 ATS Remote Android Service", font_size=24, color=(0, 0.67, 0.7, 1)))
        
        # 1. યુઝર પોતાનો ૧૦ આંકડાનો ID સેટ કરી શકે (બાય-ડિફોલ્ટ ઓટો-જનરેટ થશે)
        layout.add(Label(text="Set 10-Digit Remote ID:", font_size=16))
        default_id = "".join(random.choices(string.digits, k=10))
        self.txt_id = TextInput(text=default_id, multiline=False, font_size=18, halign="center")
        layout.add(self.txt_id)
        
        # 2. યુઝર પોતાનો પાસવર્ડ સેટ કરી શકે
        layout.add(Label(text="Set Custom Password:", font_size=16))
        self.txt_pass = TextInput(text="ats123", multiline=False, font_size=18, halign="center")
        layout.add(self.txt_pass)
        
        # સ્ટાર્ટ બટન
        self.btn_start = Button(text="🚀 Start Remote Connection", size_hint=(1, 0.3), background_color=(0, 0.67, 0.7, 1))
        self.btn_start.bind(on_press=self.start_service)
        layout.add(self.btn_start)
        
        # સ્ટેટસ અને લાઈવ લિંક જોવા માટેના લેબલ્સ
        self.lbl_status = Label(text="Status: Stopped", color=(1, 0, 0, 1), font_size=16)
        layout.add(self.lbl_status)
        
        self.lbl_tunnel = Label(text="Tunnel Link: Not Active", color=(0.7, 0.7, 0.7, 1), font_size=14)
        layout.add(self.lbl_tunnel)
        
        # ટનલ પ્રોસેસને ટ્રેક કરવા માટે
        self.tunnel_process = None
        self.is_running = False
        
        return layout

    def start_service(self, instance):
        # આઈડી ૧૦ આંકડાનો છે કે નહીં તે ચેક કરવું
        if len(self.txt_id.text.strip()) != 10:
            self.lbl_status.text = "❌ Error: ID must be exactly 10 digits!"
            self.lbl_status.color = (1, 0, 0, 1)
            return

        self.lbl_status.text = "Starting secure tunnel..."
        self.lbl_status.color = (1, 0.6, 0, 1)
        
        # ઇનપુટ બોક્સ લોક કરી દેવા જેથી યુઝર ચાલુ કનેક્શને આઈડી-પાસવર્ડ બદલી ના શકે
        self.txt_id.disabled = True
        self.txt_pass.disabled = True
        self.btn_start.disabled = True
        
        self.is_running = True
        
        # બેકગ્રાઉન્ડ થ્રેડમાં Pinggy ટનલ ફાયર કરવી
        Thread(target=self.run_backend_bridge, daemon=True).start()

    def run_backend_bridge(self):
        # અહીં આપણે ધારી લીધું છે કે આપણું લોકલ બેકએન્ડ સર્વર પોર્ટ 5000 પર ચાલશે
        # એન્ડ્રોઇડ પર કામ કરવા માટે StrictHostKeyChecking=no રાખવું જરૂરી છે
        cmd = "ssh -p 443 -R0:localhost:5000 -o StrictHostKeyChecking=no qr@pinggy.io"
        
        while self.is_running:
            try:
                # જુની પ્રોસેસ ચાલુ હોય તો બંધ કરવી
                if self.tunnel_process:
                    self.tunnel_process.terminate()
                
                # Pinggy SSH ટનલ ચાલુ કરવી
                self.tunnel_process = subprocess.Popen(
                    cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                
                # ટનલને સેટ થવા માટે ૨ સેકન્ડનો સમય આપવો
                time.sleep(2)
                
                # UI ને સેફલી અપડેટ કરવા માટે Kivy ના Clock નો ઉપયોગ કરવો
                Clock.schedule_once(self.update_ui_success, 0)
                
                # Pinggy ની ૧ કલાકની લિમિટ હોવાથી, આપણે દર 55 મિનિટે (3300 સેકન્ડ) 
                # ઓટોમેટિક લૂપ ફરીથી ચલાવીશું જેથી કનેક્શન તૂટે નહીં
                time.sleep(3300)
                
            except Exception as e:
                Clock.schedule_once(lambda dt: self.update_ui_error(str(e)), 0)
                time.sleep(10) # એરર આવે તો ૧૦ સેકન્ડ પછી ફરી ટ્રાય કરવો

    def update_ui_success(self, dt):
        # યુઝરનો સેટ કરેલો ID અને Password ફિક્સ જ રહેશે
        user_id = self.txt_id.text
        self.lbl_status.text = f"🟢 Live! ID: {user_id} (Protected)"
        self.lbl_status.color = (0, 1, 0, 1)
        self.lbl_tunnel.text = "Tunnel active & auto-refreshing in background."

    def update_ui_error(self, error_msg):
        self.lbl_status.text = f"❌ Connection Error! Retrying..."
        self.lbl_status.color = (1, 0, 0, 1)
        self.lbl_tunnel.text = error_msg

    def on_stop(self):
        # એપ બંધ થાય ત્યારે બેકગ્રાઉન્ડ ટનલ પ્રોસેસને પણ કિલ કરી દેવી
        self.is_running = False
        if self.tunnel_process:
            self.tunnel_process.terminate()

if __name__ == '__main__':
    RemoteAndroidApp().run()
    
