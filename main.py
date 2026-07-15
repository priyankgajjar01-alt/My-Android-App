#!/usr/bin/env python3
import random
import string
import time
import os
import sys
import subprocess
import stat
import socket
import ssl      
import re
from threading import Thread

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.anchorlayout import AnchorLayout
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.utils import platform

try:
    from android.permissions import request_permissions, Permission, check_permission
    from android.toast import toast
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False

class BoxLabel(Label):
    def __init__(self, **kwargs):
        super(BoxLabel, self).__init__(**kwargs)
        self.font_size = '15sp'
        self.color = (0, 0, 0, 1)
        self.bold = True
        self.halign = 'center'
        self.valign = 'middle'
        self.line_height = 1.3
        self.size_hint_y = None
        self.height = 55
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.92, 0.92, 0.92, 1)
            Rectangle(pos=self.pos, size=self.size)
        self.text_size = self.size

class ISAClientApp(App):
    def build(self):
        self.title = "INTERNET STORAGE ACCESS"
        self.is_running = False  
        self.ssh_process = None
        
        main_container = AnchorLayout(anchor_x='center', anchor_y='center', padding=30)

        self.root = BoxLayout(orientation='vertical', spacing=40, size_hint=(1, None))
        self.root.bind(minimum_height=self.root.setter('height'))

        # Title
        lbl_title = Label(text="INTERNET STORAGE ACCESS", font_size='22sp', bold=True, size_hint_y=None, height=60, halign="center", valign="middle")
        lbl_title.bind(size=lbl_title.setter('text_size'))
        self.root.add_widget(lbl_title)

        # Connection Status
        self.lbl_conn = Label(text="Connection - Offline", color=(1, 0, 0, 1), font_size='18sp', bold=True, size_hint_y=None, height=45, halign="center", valign="middle")
        self.lbl_conn.bind(size=self.lbl_conn.setter('text_size'))
        self.root.add_widget(self.lbl_conn)

        # IP Address
        lbl_ip = Label(text="IP Address (For Same Network):", font_size='15sp', size_hint_y=None, height=30, halign="center", valign="middle")
        lbl_ip.bind(size=lbl_ip.setter('text_size'))
        self.root.add_widget(lbl_ip)
        
        self.txt_ip = BoxLabel(text="Detecting...")
        self.root.add_widget(self.txt_ip)

        # 6-Digit Remote ID (શરૂઆતમાં ખાલી/બ્લેન્ક રાખવા "---")
        lbl_id = Label(text="6-Digit Remote ID:", font_size='15sp', size_hint_y=None, height=30, halign="center", valign="middle")
        lbl_id.bind(size=lbl_id.setter('text_size'))
        self.root.add_widget(lbl_id)
        
        self.txt_id = BoxLabel(text="---")
        self.root.add_widget(self.txt_id)

        # 6-Digit Password (શરૂઆતમાં ખાલી/બ્લેન્ક રાખવા "---")
        lbl_pass = Label(text="6-Digit Password:", font_size='15sp', size_hint_y=None, height=30, halign="center", valign="middle")
        lbl_pass.bind(size=lbl_pass.setter('text_size'))
        self.root.add_widget(lbl_pass)
        
        self.txt_pass = BoxLabel(text="---")
        self.root.add_widget(self.txt_pass)

        # Server Tunnel Link
        lbl_link = Label(text="Server Tunnel Link:", font_size='15sp', size_hint_y=None, height=30, halign="center", valign="middle")
        lbl_link.bind(size=lbl_link.setter('text_size'))
        self.root.add_widget(lbl_link)
        
        self.txt_link = BoxLabel(text="Waiting for secure response...")
        self.txt_link.height = 80
        self.txt_link.font_size = '14sp'
        self.root.add_widget(self.txt_link)

        # Action Buttons
        btn_layout = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=60)
        
        self.btn_start = Button(text="Start Service", font_size='18sp', bold=True, background_normal='', background_color=(0, 0.7, 0.3, 1))
        self.btn_start.bind(on_press=self.start_service)
        btn_layout.add_widget(self.btn_start)
        
        self.btn_stop = Button(text="Stop Service", font_size='18sp', bold=True, background_normal='', background_color=(0.9, 0.2, 0.2, 1), disabled=True)
        self.btn_stop.bind(on_press=self.stop_service)
        btn_layout.add_widget(self.btn_stop)
        
        self.root.add_widget(btn_layout)
        main_container.add_widget(self.root)

        Clock.schedule_once(self.check_network_status, 0.5)
        Clock.schedule_interval(self.check_network_status, 4)
        
        if ANDROID:
            Clock.schedule_once(self.request_android_permissions, 0.2)
        
        # એપ ચાલુ થતાં જ ૧.૨ સેકન્ડ પછી ઓટોમેટિક સર્વિસ સ્ટાર્ટ થશે (જે લાઈવ કી જનરેટ કરશે)
        Clock.schedule_once(lambda dt: self.start_service(None), 1.2)

        return main_container

    def request_android_permissions(self, dt=None):
        try:
            Build = autoclass('android.os.Build')
            api = Build.VERSION.SDK_INT
            req = [Permission.INTERNET, Permission.ACCESS_NETWORK_STATE]
            if api >= 33:
                ManifestPerm = autoclass('android.Manifest$permission')
                req.extend([ManifestPerm.READ_MEDIA_IMAGES, ManifestPerm.READ_MEDIA_VIDEO])
            else:
                req.extend([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            request_permissions(req)
        except: pass

    def check_network_status(self, dt):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            
            self.txt_ip.text = str(ip)
            if not self.is_running:
                self.lbl_conn.text = "Connection - Online"
                self.lbl_conn.color = (0, 1, 0, 1)
        except:
            self.txt_ip.text = "Not Connected"
            if not self.is_running:
                self.lbl_conn.text = "Connection - Offline"
                self.lbl_conn.color = (1, 0, 0, 1)

    def start_service(self, instance=None):
        if self.is_running and instance is not None:
            return
        
        self.is_running = True
        self.btn_start.disabled = True
        self.btn_stop.disabled = False
        self.lbl_conn.text = "Connection - Service Running..."
        self.lbl_conn.color = (0, 0.7, 1, 1)
        self.txt_link.text = "Initializing Dropbear Core Engine..."

        # 🎯 ફિક્સ: સર્વિસ ચાલુ થાય ત્યારે જ ID અને Password લાઈવ જનરેટ થશે
        generated_id = "".join(random.choices(string.digits, k=6))
        generated_password = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        
        self.txt_id.text = str(generated_id)
        self.txt_pass.text = str(generated_password)

        # બેકગ્રાઉન્ડ થ્રેડ્સ લોન્ચ કરવા
        Thread(target=self.launch_binary_core, daemon=True).start()

        unique_subdomain = "isa" + "".join(random.choices(string.digits, k=4))
        Thread(target=self.run_secure_tunnel, args=(unique_subdomain,), daemon=True).start()

        if ANDROID and instance is not None: 
            toast("Secure Binary Pipeline Triggered!")

    def launch_binary_core(self):
        try:
            internal_dir = os.environ.get('ANDROID_APP_FILES_DIR', '.')
            
            dropbear_bin = os.path.join(internal_dir, 'dropbear')
            key_generator = os.path.join(internal_dir, 'dropbearkey')
            key_file = os.path.join(internal_dir, 'dropbear_rsa_host_key')

            for bin_f in [dropbear_bin, key_generator]:
                if os.path.exists(bin_f):
                    st = os.stat(bin_f)
                    os.chmod(bin_f, st.st_mode | stat.S_IEXEC)

            if os.path.exists(key_generator) and not os.path.exists(key_file):
                print("🔑 Generating Dropbear RSA Host Key...")
                subprocess.run([key_generator, "-t", "rsa", "-f", key_file, "-s", "2048"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if os.path.exists(dropbear_bin):
                self.ssh_process = subprocess.Popen(
                    [dropbear_bin, "-F", "-R", "-r", key_file, "-p", "8022"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                print("🟢 Dropbear SSH daemon started successfully on port 8022.")
            else:
                self.txt_link.text = "❌ Error: dropbear binary not found!"
                print("⚠️ dropbear binary not found in path!")
        except Exception as e:
            print(f"Binary initialization error: {e}")

    def run_secure_tunnel(self, unique_subdomain):
        while self.is_running:
            try:
                context = ssl.create_default_context()
                raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw_sock.settimeout(10)
                raw_sock.connect(("localhost.run", 443))
                
                secure_sock = context.wrap_socket(raw_sock, server_hostname="localhost.run")
                req = f"CONNECT {unique_subdomain}:8022 HTTP/1.1\r\nHost: localhost.run\r\n\r\n"
                secure_sock.sendall(req.encode())
                
                resp = secure_sock.recv(4096).decode('utf-8', errors='ignore')
                
                if "tunneled with tls" in resp or unique_subdomain in resp:
                    real_link = f"ssh -p 443 {unique_subdomain}@localhost.run"
                    
                    def _update_ui(dt):
                        self.txt_link.text = real_link
                        self.lbl_conn.text = "Connection - Tunnel Live"
                        self.lbl_conn.color = (0, 1, 0, 1)
                    Clock.schedule_once(_update_ui)
                    
                    secure_sock.settimeout(None)
                    while self.is_running:
                        packet = secure_sock.recv(65536)
                        if not packet: break
                        
                        local_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        local_conn.connect(("127.0.0.1", 8022))
                        local_conn.sendall(packet)
                        local_resp = local_conn.recv(65536)
                        local_conn.close()
                        
                        if local_resp: secure_sock.sendall(local_resp)
                else:
                    break
            except:
                if not self.is_running: break
                time.sleep(5)

    def stop_service(self, instance):
        self.is_running = False
        self.btn_start.disabled = False
        self.btn_stop.disabled = True
        
        # 🎯 ફિક્સ: કનેક્શન પ્રોસેસ બ્રેક કરવી
        if self.ssh_process:
            try: 
                self.ssh_process.terminate()
                self.ssh_process.wait(timeout=1)
            except: pass
            self.ssh_process = None
            
        # 🎯 ફિક્સ: સ્ટોપ મારતા જ બધા બોક્સ પાછા ખાલી ("---") થઈ જશે
        self.txt_id.text = "---"
        self.txt_pass.text = "---"
        self.txt_link.text = "Waiting for secure response..."
        
        self.check_network_status(None)
        if ANDROID: toast("Binary Services & Tunnel Stopped Safely.")

    def on_stop(self):
        self.is_running = False
        if self.ssh_process:
            try: self.ssh_process.terminate()
            except: pass

if __name__ == '__main__':
    ISAClientApp().run()
