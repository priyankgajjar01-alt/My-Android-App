#!/usr/bin/env python3
import random
import string
import time
import os
import json
import socket
import ssl      
import hashlib
import re
import urllib.request  
import base64  
from threading import Thread

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window  
from kivy.graphics import Color, RoundedRectangle  

try:
    from android.permissions import request_permissions, Permission, check_permission
    from android.toast import toast
    from jnius import autoclass, cast 
    ANDROID = True
except ImportError:
    ANDROID = False
    print("⚠️ Running on non-Android platform")

class RemoteStorageServer:
    def __init__(self, port=5000):
        self.port = port
        self.users = {}
        self.authenticated_sessions = set()
        self.running = False
        self.socket = None

    def start(self):  
        try:  
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
            self.socket.bind(('0.0.0.0', self.port))  
            self.socket.listen(5)  
            self.running = True  
              
            while self.running:  
                try:  
                    self.socket.settimeout(1.0)  
                    client, addr = self.socket.accept()  
                    Thread(target=self.handle_client, args=(client, addr), daemon=True).start()  
                except socket.timeout:  
                    continue  
                except Exception:  
                    break  
        except Exception as e:  
            print(f"❌ Failed to start storage server: {e}")  
      
    def _recv_full_json(self, client):
        data = ""
        while True:
            chunk = client.recv(65536).decode('utf-8', errors='ignore')
            if not chunk: break
            data += chunk
            try:
                if data.strip().endswith('}'):
                    parsed = json.loads(data)
                    if "op" in parsed or "id" in parsed: return parsed
            except json.JSONDecodeError: continue
        return json.loads(data) if data else {}

    def handle_client(self, client, addr):  
        try:  
            auth_json = self._recv_full_json(client)
            user_id = auth_json.get('id')  
            password = auth_json.get('password')  
              
            if not self.verify_auth(user_id, password):  
                client.send(json.dumps({"status": "FAILED", "msg": "Invalid credentials"}).encode())  
                client.close()  
                return  
              
            client.send(json.dumps({"status": "OK", "msg": "Authenticated"}).encode())  
            self.authenticated_sessions.add(addr[0])  
              
            while self.running:  
                try:  
                    cmd_json = self._recv_full_json(client)
                    if not cmd_json: break  
                    
                    operation = cmd_json.get('op')
                    if operation == 'STREAM_START':
                        path = cmd_json.get('path', '')
                        total_size = cmd_json.get('size', 0)
                        
                        if not (path.startswith('/sdcard/') or path.startswith('/storage/')):
                            client.send(json.dumps({"status": "FAILED", "msg": "Access denied"}).encode())
                            continue
                        
                        client.send(json.dumps({"status": "OK", "msg": "Ready for stream"}).encode())
                        received_bytes = 0
                        chunk_size = 4 * 1024 * 1024
                        
                        try:
                            with open(path, 'wb') as f:
                                while received_bytes < total_size:
                                    remaining = total_size - received_bytes
                                    current_buf = min(chunk_size, remaining)
                                    chunk = client.recv(current_buf)
                                    if not chunk: break
                                    f.write(chunk)
                                    received_bytes += len(chunk)
                            
                            if received_bytes == total_size:
                                client.send(json.dumps({"status": "OK", "msg": "Large file saved fully"}).encode())
                            else:
                                client.send(json.dumps({"status": "FAILED", "msg": "Stream cut off short"}).encode())
                        except Exception as file_err:
                            client.send(json.dumps({"status": "FAILED", "msg": f"Write error: {file_err}"}).encode())
                    else:
                        response = self.process_command(cmd_json)  
                        client.send(json.dumps(response).encode())  
                except: break  
        except: pass  
        finally:
            try:
                self.authenticated_sessions.discard(addr[0])
                client.close()
            except: pass
      
    def verify_auth(self, user_id, password):  
        if user_id in self.users:  
            stored_hash = self.users[user_id]  
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()  
            return stored_hash == pwd_hash  
        return False  
      
    def process_command(self, cmd):  
        try:  
            operation = cmd.get('op')  
            path = cmd.get('path', '/sdcard/')  
              
            if not (path.startswith('/sdcard/') or path.startswith('/storage/')):  
                return {"status": "FAILED", "msg": "Access denied"}  
              
            if operation == 'LIST':  
                files = []  
                if os.path.isdir(path):  
                    try: files = os.listdir(path)
                    except PermissionError: return {"status": "FAILED", "msg": "Permission denied"}  
                return {"status": "OK", "files": files}  
              
            elif operation == 'READ':  
                if os.path.isfile(path):  
                    try:  
                        with open(path, 'rb') as f: raw_data = f.read()  
                        content_b64 = base64.b64encode(raw_data).decode('utf-8') 
                        return {"status": "OK", "content": content_b64}  
                    except PermissionError: return {"status": "FAILED", "msg": "Permission denied"}  
                return {"status": "FAILED", "msg": "File not found"}  
              
            elif operation == 'WRITE':  
                try:  
                    content_b64 = cmd.get('content', '')  
                    raw_data = base64.b64decode(content_b64) 
                    with open(path, 'wb') as f: f.write(raw_data)  
                    return {"status": "OK", "msg": "File written"}  
                except PermissionError: return {"status": "FAILED", "msg": "Permission denied"}  
              
            elif operation == 'DELETE':  
                if os.path.isfile(path):  
                    try:  
                        os.remove(path)  
                        return {"status": "OK", "msg": "File deleted"}  
                    except PermissionError: return {"status": "FAILED", "msg": "Permission denied"}  
                return {"status": "FAILED", "msg": "File not found"}  
            else: return {"status": "FAILED", "msg": "Unknown operation"}  
        except Exception as e: return {"status": "FAILED", "msg": str(e)}  
      
    def add_user(self, user_id, password):  
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()  
        self.users[user_id] = pwd_hash  
      
    def stop(self):  
        self.running = False  
        if self.socket:  
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except: pass
            try:
                self.socket.close()  
            except: pass

class ModernRoundButton(Button):
    def __init__(self, bg_color=(0, 0.67, 0.7, 1), radius=[15], **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)  
        self.bg_color = bg_color
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

class RemoteAndroidApp(App):
    def build(self):
        self.title = "Internet Storage Access"
        self.is_running = False  
        self.storage_server = RemoteStorageServer(port=5000)  
        self.permissions_granted = False  
        self.current_screen = "home"  
        
        self.generated_10digit_id = "".join(random.choices(string.digits, k=10))
        self.generated_password = "".join(random.choices(string.ascii_letters + string.digits, k=6))

        self.lbl_permissions = Label(text="⏳ Checking Storage Permission...", color=(1, 0.6, 0, 1), font_size=32, size_hint_y=None, height=60)  
        self.lbl_net_internet = Label(text="🌐 Internet Connection: Checking...", font_size=32, size_hint_y=None, height=60)
        self.lbl_net_local = Label(text="🏠 Local Network: Checking...", font_size=32, size_hint_y=None, height=60)
        
        self.root_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        self.show_home_screen()
        
        Window.bind(on_keyboard=self.on_hardware_back_button)
        
        Clock.schedule_once(self.check_and_request_android_storage, 1)  
        Clock.schedule_interval(self.update_network_status_ui, 3)
          
        return self.root_layout  

    def on_hardware_back_button(self, window, key, *args):
        if key == 27:  
            if self.current_screen != "home":
                self.safe_back_home()
                return True  
            return False  
        return False

    def show_home_screen(self):
        self.current_screen = "home"
        self.root_layout.clear_widgets()
        self.root_layout.add_widget(Label(text="📱 ATS Storage Gateway", font_size=46, bold=True, color=(0, 0.67, 0.7, 1), size_hint_y=0.15))
        
        status_box = BoxLayout(orientation='vertical', size_hint_y=0.25, spacing=5)
        status_box.add_widget(self.lbl_permissions)
        status_box.add_widget(self.lbl_net_internet)
        status_box.add_widget(self.lbl_net_local)
        self.root_layout.add_widget(status_box)
        
        btn_box = BoxLayout(orientation='vertical', spacing=15, size_hint=(0.6, None), height=120, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        
        btn_same_net = ModernRoundButton(text="🏠 Same Network", font_size=32, bold=True, bg_color=(0.1, 0.7, 0.3, 1), radius=[20])
        btn_same_net.bind(on_press=self.show_same_network_screen)
        
        btn_diff_net = ModernRoundButton(text="🌐 Different Network", font_size=32, bold=True, bg_color=(0, 0.5, 0.8, 1), radius=[20])
        btn_diff_net.bind(on_press=self.show_different_network_screen)
        
        btn_box.add_widget(btn_same_net)
        btn_box.add_widget(btn_diff_net)
        
        wrapper = BoxLayout(orientation='vertical', size_hint_y=0.6)
        wrapper.add_widget(btn_box)
        self.root_layout.add_widget(wrapper)

    def show_same_network_screen(self, instance=None):
        self.current_screen = "same_net"
        def _build_same_screen(dt):
            self.root_layout.clear_widgets()
            
            header = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
            btn_back = ModernRoundButton(text="⬅️", size_hint_x=0.15, font_size=36, bold=True, bg_color=(0.3, 0.3, 0.3, 1))
            btn_back.bind(on_press=lambda x: self.safe_back_home()) 
            header.add_widget(btn_back)
            header.add_widget(Label(text="🏠 Local Same Network", font_size=40, bold=True, color=(0.1, 0.7, 0.3, 1), size_hint_x=0.85, halign="left"))
            self.root_layout.add_widget(header)
            
            scroll = ScrollView(size_hint_y=0.9)  
            layout = BoxLayout(orientation='vertical', spacing=15, size_hint_y=None)  
            layout.bind(minimum_height=layout.setter('height'))
            
            layout.add_widget(Label(text="📋 10-Digit Device ID:", font_size=34, bold=True, size_hint_y=None, height=50))  
            self.txt_same_id = TextInput(text=self.generated_10digit_id, multiline=False, font_size=36, halign="center", size_hint_y=None, height=85, disabled=True)  
            layout.add_widget(self.txt_same_id)
            
            layout.add_widget(Label(text="🔐 Auto-Generated Password:", font_size=34, bold=True, size_hint_y=None, height=50))  
            self.txt_same_pass = TextInput(text=self.generated_password, multiline=False, font_size=36, halign="center", password=False, size_hint_y=None, height=85, disabled=True)  
            layout.add_widget(self.txt_same_pass)
            
            layout.add_widget(Label(text="📌 Local IP Address for PC:", font_size=34, bold=True, size_hint_y=None, height=50))  
            
            # 🌟 CRITICAL FIX 1: અહીં ડાયરેક્ટ આઈપી સેટ કરી દીધો, જેથી લોડ થતા જ તરત આઈપી દેખાવા મંડે!
            current_detected_ip = self.get_device_ip()
            self.txt_same_ip = TextInput(text=str(current_detected_ip), multiline=False, font_size=36, halign="center", size_hint_y=None, height=85, disabled=True)  
            layout.add_widget(self.txt_same_ip)
            
            layout.add_widget(Label(text="📊 Engine Status:", font_size=32, bold=True, size_hint_y=None, height=50))
            self.lbl_same_status = Label(text="🏠 Local Server: Inactive", font_size=30, bold=True, color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=70)
            layout.add_widget(self.lbl_same_status)
            
            self.btn_same_start = ModernRoundButton(text="🚀 Start Service", size_hint_y=None, height=48, font_size=32, bold=True, bg_color=(0, 0.67, 0.7, 1), radius=[15])  
            self.btn_same_start.bind(on_press=self.start_same_net_service)  
            layout.add_widget(self.btn_same_start)
            
            self.btn_same_stop = ModernRoundButton(text="🛑 Stop Service", size_hint_y=None, height=48, font_size=32, bold=True, bg_color=(1, 0.2, 0.2, 1), radius=[15], disabled=True)  
            self.btn_same_stop.bind(on_press=self.stop_all_services)  
            layout.add_widget(self.btn_same_stop)
            
            scroll.add_widget(layout)
            self.root_layout.add_widget(scroll)
            
            if self.is_running:
                self.btn_same_start.disabled = True
                self.btn_same_stop.disabled = False
                self.lbl_same_status.text = f"🟢 LAN Server Active on Port 5000"
                self.lbl_same_status.color = (0, 1, 0, 1)
        Clock.schedule_once(_build_same_screen)

    def show_different_network_screen(self, instance=None):
        self.current_screen = "diff_net"
        def _build_diff_screen(dt):
            self.root_layout.clear_widgets()
            
            header = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
            btn_back = ModernRoundButton(text="⬅️", size_hint_x=0.15, font_size=36, bold=True, bg_color=(0.3, 0.3, 0.3, 1))
            btn_back.bind(on_press=lambda x: self.safe_back_home()) 
            header.add_widget(btn_back)
            header.add_widget(Label(text="🌐 Different Network Tunnel", font_size=40, bold=True, color=(0, 0.5, 0.8, 1), size_hint_x=0.85, halign="left"))
            self.root_layout.add_widget(header)
            
            scroll = ScrollView(size_hint_y=0.9)  
            layout = BoxLayout(orientation='vertical', spacing=12, size_hint_y=None)  
            layout.bind(minimum_height=layout.setter('height'))
            
            layout.add_widget(Label(text="⚡ Select Tunnel Server Platform:", font_size=34, bold=True, size_hint_y=None, height=50))
            self.spn_server = Spinner(text='Localhost.run Server', values=('Localhost.run Server', 'Pinggy HTTP Bridge'), size_hint_y=None, height=75, font_size=32)
            layout.add_widget(self.spn_server)
            
            layout.add_widget(Label(text="📋 10-Digit Tunnel ID:", font_size=34, bold=True, size_hint_y=None, height=50))  
            self.txt_diff_id = TextInput(text=self.generated_10digit_id, multiline=False, font_size=36, halign="center", size_hint_y=None, height=85, disabled=True)  
            layout.add_widget(self.txt_diff_id)
            
            layout.add_widget(Label(text="🔐 Auto-Generated Password:", font_size=34, bold=True, size_hint_y=None, height=50))  
            self.txt_diff_pass = TextInput(text=self.generated_password, multiline=False, font_size=36, halign="center", password=False, size_hint_y=None, height=85, disabled=True)  
            layout.add_widget(self.txt_diff_pass)
            
            layout.add_widget(Label(text="🔗 Active Live Gateway Link:", font_size=34, bold=True, size_hint_y=None, height=50))  
            self.txt_diff_link = TextInput(text="Click Start Services to Generate...", multiline=True, font_size=32, halign="center", size_hint_y=None, height=130, disabled=True)  
            layout.add_widget(self.txt_diff_link)
            
            layout.add_widget(Label(text="📊 Tunnel Engine Status:", font_size=32, bold=True, size_hint_y=None, height=50))
            self.lbl_diff_status = Label(text="🔗 Tunnel Connection: Inactive", font_size=30, bold=True, color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=70)
            layout.add_widget(self.lbl_diff_status)
            
            self.btn_diff_start = ModernRoundButton(text="🚀 Start Tunnel Services", size_hint_y=None, height=48, font_size=32, bold=True, bg_color=(0, 0.67, 0.7, 1), radius=[15])  
            self.btn_diff_start.bind(on_press=self.start_diff_net_service)  
            layout.add_widget(self.btn_diff_start)
            
            self.btn_diff_stop = ModernRoundButton(text="🛑 Stop Tunnel Services", size_hint_y=None, height=48, font_size=32, bold=True, bg_color=(1, 0.2, 0.2, 1), radius=[15], disabled=True)  
            self.btn_diff_stop.bind(on_press=self.stop_all_services)  
            layout.add_widget(self.btn_diff_stop)
            
            scroll.add_widget(layout)
            self.root_layout.add_widget(scroll)
            
            if self.is_running:
                self.spn_server.disabled = True
                self.btn_diff_start.disabled = True
                self.btn_diff_stop.disabled = False
        Clock.schedule_once(_build_diff_screen)

    def safe_back_home(self):
        def _go(dt):
            self.show_home_screen()
        Clock.schedule_once(_go)

    def check_and_request_android_storage(self, dt=None):
        if not ANDROID:
            self.lbl_permissions.text = "✅ Desktop Mode (No restrictions)"
            self.lbl_permissions.color = (0, 1, 0, 1)
            self.permissions_granted = True
            return

        try:
            Build = autoclass('android.os.Build')
            api = Build.VERSION.SDK_INT
            
            if api <= 29:
                storage_read_ok = check_permission(Permission.READ_EXTERNAL_STORAGE)  
                storage_write_ok = check_permission(Permission.WRITE_EXTERNAL_STORAGE)
                
                if storage_read_ok and storage_write_ok:
                    self.lbl_permissions.text = "✅ Storage Access Granted!"
                    self.lbl_permissions.color = (0, 1, 0, 1)
                    self.permissions_granted = True
                else:
                    self.lbl_permissions.text = "❌ Storage Permission Required!"
                    self.lbl_permissions.color = (1, 0, 0, 1)
                    self.permissions_granted = False
                    request_permissions([
                        Permission.INTERNET, 
                        Permission.ACCESS_NETWORK_STATE, 
                        Permission.READ_EXTERNAL_STORAGE, 
                        Permission.WRITE_EXTERNAL_STORAGE
                    ])
            else:
                Environment = autoclass('android.os.Environment')
                if Environment.isExternalStorageManager():
                    self.lbl_permissions.text = "✅ All-Files Access Granted!"
                    self.lbl_permissions.color = (0, 1, 0, 1)
                    self.permissions_granted = True
                else:
                    self.lbl_permissions.text = "❌ All-Files Access Required!"
                    self.lbl_permissions.color = (1, 0, 0, 1)
                    self.permissions_granted = False
                    
                    Settings = autoclass('android.provider.Settings')
                    Uri = autoclass('android.net.Uri')
                    Intent = autoclass('android.content.Intent')
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    
                    activity = PythonActivity.mActivity
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    intent.setData(Uri.parse("package:" + activity.getPackageName()))
                    activity.startActivity(intent)
                    toast("Please turn ON the switch for All Files Access!")
        except Exception as e:
            self.lbl_permissions.text = f"⚠️ Setup Error: {str(e)[:40]}"

    def start_same_net_service(self, instance):
        if ANDROID and not self.permissions_granted:  
            self.check_and_request_android_storage()
            return  
            
        self.is_running = True
        self.btn_same_start.disabled = True  
        self.btn_same_stop.disabled = False
        
        self.storage_server.add_user(self.generated_10digit_id, self.generated_password)  
        Thread(target=self.storage_server.start, daemon=True).start()  
        
        self.lbl_same_status.text = "🟢 LAN Server Active on Port 5000"
        self.lbl_same_status.color = (0, 1, 0, 1)
        if ANDROID: toast("Local Storage Services Enabled Successfully!")

    def start_diff_net_service(self, instance):
        if ANDROID and not self.permissions_granted:  
            self.check_and_request_android_storage()
            return  
            
        self.is_running = True
        self.spn_server.disabled = True
        self.btn_diff_start.disabled = True  
        self.btn_diff_stop.disabled = False
        
        self.storage_server.add_user(self.generated_10digit_id, self.generated_password)  
        Thread(target=self.storage_server.start, daemon=True).start()  
        
        self.lbl_diff_status.text = "🔄 Initiating Secure Server Tunnel Connection..."
        self.lbl_diff_status.color = (1, 0.6, 0, 1)
        
        unique_subdomain = "ats" + "".join(random.choices(string.digits, k=4))
        
        if self.spn_server.text == 'Localhost.run Server':
            Thread(target=self.run_localhost_tunnel, args=(unique_subdomain,), daemon=True).start()  
        else:
            Thread(target=self.run_pinggy_tunnel, args=(unique_subdomain,), daemon=True).start()  

    def stop_all_services(self, instance=None):
        if not self.is_running:
            return  

        self.is_running = False  
        self.storage_server.stop()  
        
        self.generated_10digit_id = "".join(random.choices(string.digits, k=10))
        self.generated_password = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        
        if ANDROID: 
            try:
                PythonService = autoclass('org.kivy.android.PythonService')
                PythonService.stopService()
            except: pass
            toast("Services stopped safely. UI active.")
        
        def _reset_ui(dt):
            self.show_home_screen()
        Clock.schedule_once(_reset_ui, 0.5)

    def run_localhost_tunnel(self, unique_subdomain):
        unique_link = f"https://{unique_subdomain}.localhost.run"
        self.update_tunnel_ui_fields(unique_link, "🟢 Localhost Tunnel Engine: Live & Online")
        
        while self.is_running:
            try:
                context = ssl.create_default_context()
                raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw_sock.settimeout(5)
                raw_sock.connect(("localhost.run", 443))
                
                secure_sock = context.wrap_socket(raw_sock, server_hostname="localhost.run")
                
                req = f"CONNECT {unique_subdomain}:5000 HTTP/1.1\r\nHost: localhost.run\r\n\r\n"
                secure_sock.sendall(req.encode())
                
                secure_sock.settimeout(2)
                try:
                    resp = secure_sock.recv(4096)
                except: pass
                
                secure_sock.settimeout(None)
                self._start_data_pipeline(secure_sock)
            except Exception:
                if not self.is_running: break
                time.sleep(3)

    def run_pinggy_tunnel(self, unique_subdomain):  
        tunnel_host = f"{unique_subdomain}.pinggy.link"
        self.update_tunnel_ui_fields(f"https://{tunnel_host}", "🟢 Pinggy Tunnel Engine: Live & Online")
        
        context = ssl.create_default_context()
        while self.is_running:
            try:
                with socket.create_connection(("pinggy.io", 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname="pinggy.io") as ssock:
                        req = f"GET /requests HTTP/1.1\r\nHost: pinggy.io\r\nToken: free\r\nLocal-Port: 5000\r\nConnection: keep-alive\r\n\r\n"
                        ssock.sendall(req.encode())
                        self._start_data_pipeline(ssock)
            except:
                time.sleep(1)
                if not self.is_running: break

    def _start_data_pipeline(self, secure_sock):
        try:
            secure_sock.settimeout(1.0)
            while self.is_running:
                try:
                    data_packet = secure_sock.recv(65536)
                    if not data_packet: break
                    
                    local_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    local_conn.connect(("127.0.0.1", 5000))
                    local_conn.sendall(data_packet)
                    
                    local_response = local_conn.recv(65536)
                    local_conn.close()
                    
                    if local_response:
                        secure_sock.sendall(local_response)
                except socket.timeout:
                    continue
        except: pass
        finally:
            try: secure_sock.close()
            except: pass

    def update_tunnel_ui_fields(self, link_text, status_text, success=True):
        def set_ui(dt):
            try:
                self.txt_diff_link.text = link_text
                self.lbl_diff_status.text = status_text
                self.lbl_diff_status.color = (0, 1, 0, 1) if success else (1, 0, 0, 1)
            except: pass
        Clock.schedule_once(set_ui)

    def update_network_status_ui(self, dt):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            self.lbl_net_internet.text = "🌐 Internet Connection: Online"
            self.lbl_net_internet.color = (0, 1, 0, 1)
        except OSError:
            self.lbl_net_internet.text = "🌐 Internet Connection: Offline"
            self.lbl_net_internet.color = (1, 0, 0, 1)

        ip = self.get_device_ip()
        if ip != "127.0.0.1":
            self.lbl_net_local.text = f"🏠 Local Network: OK (IP: {ip})"
            self.lbl_net_local.color = (0, 1, 0, 1)
            
            # 🌟 CRITICAL FIX 2: પહેલાં ચેક કરી લેશે કે `txt_same_ip` ઓબ્જેક્ટ બનેલો છે કે નહિ, જેથી ક્રેશ થયા વગર બોક્સ અપડેટ થાય!
            if hasattr(self, 'txt_same_ip') and self.txt_same_ip:
                try: self.txt_same_ip.text = str(ip)
                except: pass
        else:
            self.lbl_net_local.text = "🏠 Local Network: No Wi-Fi / Hotspot"
            self.lbl_net_local.color = (1, 0, 0, 1)

        if ANDROID and not self.permissions_granted:
            try:
                Build = autoclass('android.os.Build')
                if Build.VERSION.SDK_INT >= 30:
                    Environment = autoclass('android.os.Environment')
                    if Environment.isExternalStorageManager():
                        self.lbl_permissions.text = "✅ All-Files Access Granted!"
                        self.lbl_permissions.color = (0, 1, 0, 1)
                        self.permissions_granted = True
                else:
                    if check_permission(Permission.READ_EXTERNAL_STORAGE) and check_permission(Permission.WRITE_EXTERNAL_STORAGE):
                        self.lbl_permissions.text = "✅ Storage Access Granted!"
                        self.lbl_permissions.color = (0, 1, 0, 1)
                        self.permissions_granted = True
            except: pass

    def get_device_ip(self):  
        try:  
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
            s.connect(("8.8.8.8", 80))  
            ip = s.getsockname()[0]  
            s.close()  
            return ip  
        except: return "127.0.0.1"  

    def on_stop(self):  
        self.is_running = False  
        self.storage_server.stop()  
        time.sleep(0.5)

if __name__ == '__main__':
    RemoteAndroidApp().run()
