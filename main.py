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
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.utils import platform

try:
    from android.permissions import request_permissions, Permission, check_permission
    from android.toast import toast
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False

class ATSStorageApp(App):
    def build(self):
        self.title = "INTERNET STORAGE ACCESS"
        self.is_running = False  
        self.ssh_process = None
        
        # ઓટો-જનરેટેડ 6-ડિજિટલ ID અને પાસવર્ડ
        self.generated_id = "".join(random.choices(string.digits, k=6))
        self.generated_password = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # મેઈન લેઆઉટ (Vertical)
        self.root = BoxLayout(orientation='vertical', padding=25, spacing=15)

        # 1. Title
        self.root.add_widget(Label(
            text="INTERNET STORAGE ACCESS", 
            font_size='24sp', 
            bold=True, 
            size_hint_y=None, 
            height=50
        ))

        # 2. Connection Status
        self.lbl_conn = Label(
            text="Connection - Offline", 
            color=(1, 0, 0, 1), 
            font_size='18sp', 
            bold=True,
            size_hint_y=None, 
            height=40
        )
        self.root.add_widget(self.lbl_conn)

        # 3. IP Address (For Same Network)
        self.root.add_widget(Label(text="IP Address (For Same Network):", size_hint_y=None, height=25, halign="left"))
        self.txt_ip = TextInput(text="Detecting...", readonly=True, multiline=False, font_size='16sp', size_hint_y=None, height=45, halign="center")
        self.root.add_widget(self.txt_ip)

        # 4. 6-Digit Remote ID
        self.root.add_widget(Label(text="6-Digit Remote ID:", size_hint_y=None, height=25))
        self.txt_id = TextInput(text=str(self.generated_id), readonly=True, multiline=False, font_size='16sp', size_hint_y=None, height=45, halign="center")
        self.root.add_widget(self.txt_id)

        # 5. 6-Digit Password
        self.root.add_widget(Label(text="6-Digit Password:", size_hint_y=None, height=25))
        self.txt_pass = TextInput(text=str(self.generated_password), readonly=True, multiline=False, font_size='16sp', size_hint_y=None, height=45, halign="center")
        self.root.add_widget(self.txt_pass)

        # 6. Server Tunnel Link
        self.root.add_widget(Label(text="Server Tunnel Link:", size_hint_y=None, height=25))
        self.txt_link = TextInput(text="Waiting for secure response...", readonly=True, multiline=True, font_size='15sp', size_hint_y=None, height=70, halign="center")
        self.root.add_widget(self.txt_link)

        # 7. Action Buttons (Horizontal Layout)
        btn_layout = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=60)
        
        self.btn_start = Button(text="Start Service", font_size='18sp', bold=True, background_normal='', background_color=(0, 0.7, 0.3, 1))
        self.btn_start.bind(on_press=self.start_service)
        btn_layout.add_widget(self.btn_start)
        
        self.btn_stop = Button(text="Stop Service", font_size='18sp', bold=True, background_normal='', background_color=(0.9, 0.2, 0.2, 1), disabled=True)
        self.btn_stop.bind(on_press=self.stop_service)
        btn_layout.add_widget(self.btn_stop)
        
        self.root.add_widget(btn_layout)

        # નેટવર્ક સ્ટેટસ લાઇવ ચેક કરવા માટે
        Clock.schedule_once(self.check_network_status, 1)
        Clock.schedule_interval(self.check_network_status, 4)
        
        if ANDROID:
            Clock.schedule_once(self.request_android_permissions, 1)

        return self.root

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

    def start_service(self, instance):
        self.is_running = True
        self.btn_start.disabled = True
        self.btn_stop.disabled = False
        self.lbl_conn.text = "Connection - Service Running..."
        self.lbl_conn.color = (0, 0.7, 1, 1)
        self.txt_link.text = "Spawning Executable Binary Core..."

        # 🚀 1. એમ્બેડેડે આર્કિટેક્ચર વાળી SSHD બાઈનરી શરૂ કરો
        Thread(target=self.launch_binary_core, daemon=True).start()

        # 🚀 2. લોકલહોસ્ટ રન રિવર્સ ટનલ શરૂ કરો
        unique_subdomain = "ats" + "".join(random.choices(string.digits, k=4))
        Thread(target=self.run_secure_tunnel, args=(unique_subdomain,), daemon=True).start()

        if ANDROID: toast("Secure Binary Pipeline Triggered!")

    def launch_binary_core(self):
        try:
            import platform as py_platform
            internal_dir = os.environ.get('ANDROID_APP_FILES_DIR', '.')
            
            # 🎯 1. ફોનનું આર્કિટેક્ચર ચેક કરો (64-bit છે કે 32-bit)
            machine = py_platform.machine().lower()
            is_64bit = "64" in machine or "armv8" in machine or "aarch64" in machine
            
            # 🎯 2. સાચી બાઈનરી ફાઈલ નક્કી કરો
            binary_name = 'sshd_64' if is_64bit else 'sshd_32'
            bin_path = os.path.join(internal_dir, binary_name)

            if os.path.exists(bin_path):
                # Executable પરમિશન સેટ કરો
                st = os.stat(bin_path)
                os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
                
                # પોર્ટ 8022 પર સિલેક્ટ થયેલી સાચી બાઈનરી રન કરો
                self.ssh_process = subprocess.Popen(
                    [bin_path, "-D", "-p", "8022", "-e"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                print(f"🟢 Successfully launched embedded {binary_name} core.")
            else:
                print(f"⚠️ Binary {binary_name} not found in path!")
        except Exception as e:
            print(f"Binary architecture selection runtime error: {e}")

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
                    
                    # UI અપડેટ કરો
                    def _update_ui(dt):
                        self.txt_link.text = real_link
                        self.lbl_conn.text = "Connection - Tunnel Live"
                        self.lbl_conn.color = (0, 1, 0, 1)
                    Clock.schedule_once(_update_ui)
                    
                    secure_sock.settimeout(None)
                    # ડેટા ટ્રાન્સફર પાઇપલાઇન (પોર્ટ 8022 બ્રિજ)
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
        
        if self.ssh_process:
            try: self.ssh_process.terminate()
            except: pass
            
        # નવી સિક્યોરિટી માટે ID/Pass રીસેટ કરો
        self.generated_id = "".join(random.choices(string.digits, k=6))
        self.generated_password = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        
        self.txt_id.text = str(self.generated_id)
        self.txt_pass.text = str(self.generated_password)
        self.txt_link.text = "Waiting for secure response..."
        
        self.check_network_status(None)
        if ANDROID: toast("Binary Services Stopped safely.")

    def on_stop(self):
        self.is_running = False
        if self.ssh_process:
            try: self.ssh_process.terminate()
            except: pass

if __name__ == '__main__':
    ATSStorageApp().run()
