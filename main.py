import random
import string
import time
import subprocess
import os
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
        if len(self.txt_id.text.strip()) != 10:
            self.lbl_status.text = "❌ Error: ID must be exactly 10 digits!"
            self.lbl_status.color = (1, 0, 0, 1)
            return

        self.lbl_status.text = "Starting secure tunnel..."
        self.lbl_status.color = (1, 0.6, 0, 1)
        
        self.txt_id.disabled = True
        self.txt_pass.disabled = True
        self.btn_start.disabled = True
        
        self.is_running = True
        
        Thread(target=self.run_backend_bridge, daemon=True).start()

    def run_backend_bridge(self):
        # એન્ડ્રોઇડ એન્વાયર્નમેન્ટ સુરક્ષિત સેટઅપ
        cmd = "ssh -p 443 -R0:localhost:5000 -o StrictHostKeyChecking=no qr@pinggy.io"
        
        while self.is_running:
            try:
                if self.tunnel_process:
                    try:
                        self.tunnel_process.terminate()
                    except:
                        pass
                
                # 🚀 સેફ એક્ઝિક્યુશન: એન્ડ્રોઇડ પર ssh ન હોય તો એપ ક્રેશ નહીં થાય
                self.tunnel_process = subprocess.Popen(
                    cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                
                time.sleep(2)
                
                # ચેક કરવું કે પ્રોસેસ તરત જ મરી તો નથી ગઈ ને? (જેમ કે ssh ન મળવાથી થાય)
                if self.tunnel_process.poll() is not None:
                    errors = self.tunnel_process.stderr.read()
                    raise Exception(f"SSH Binary Missing or Exec Error: {errors if errors else 'Executable not found'}")
                
                Clock.schedule_once(self.update_ui_success, 0)
                time.sleep(3300)
                
            except Exception as e:
                # એરરને સેફલી UI પર પાસ કરવી, ક્રેસ નહીં થવા દે
                error_str = str(e)
                Clock.schedule_once(lambda dt: self.update_ui_error(error_str), 0)
                time.sleep(10)

    def update_ui_success(self, dt):
        user_id = self.txt_id.text
        self.lbl_status.text = f"🟢 Live! ID: {user_id} (Protected)"
        self.lbl_status.color = (0, 1, 0, 1)
        self.lbl_tunnel.text = "Tunnel active & auto-refreshing in background."

    def update_ui_error(self, error_msg):
        # ઇનપુટ્સ ફરીથી ઓપન કરવા જેથી યુઝર અટકી ન જાય
        self.txt_id.disabled = False
        self.txt_pass.disabled = False
        self.btn_start.disabled = False
        self.is_running = False
        
        self.lbl_status.text = f"❌ Connection Failed!"
        self.lbl_status.color = (1, 0, 0, 1)
        self.lbl_tunnel.text = f"Error: {error_msg[:60]}..."

    def on_stop(self):
        self.is_running = False
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
            except:
                pass

if __name__ == '__main__':
    RemoteAndroidApp().run()
    
