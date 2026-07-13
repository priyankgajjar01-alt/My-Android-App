#!/usr/bin/env python3
import random
import string
import time
import subprocess
import os
import json
import socket
import hashlib
import re
from threading import Thread

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

try:
    from android.permissions import request_permissions, Permission, check_permission
    from android.toast import toast
    ANDROID = True
except ImportError:
    ANDROID = False
    print("⚠️ Running on non-Android platform")

class RemoteStorageServer:
    """Backend storage server for remote file access with Large File Streaming Support"""
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
            print(f"✅ Storage Server started on port {self.port}")  
              
            while self.running:  
                try:  
                    self.socket.settimeout(1.0)  
                    client, addr = self.socket.accept()  
                    Thread(target=self.handle_client, args=(client, addr), daemon=True).start()  
                except socket.timeout:  
                    continue  
                except Exception as e:  
                    if self.running:  
                        print(f"❌ Server error: {e}")  
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
            except json.JSONDecodeError:
                continue
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
              
            while True:  
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
                        content_str = raw_data.decode('latin-1')
                        return {"status": "OK", "content": content_str}  
                    except PermissionError: return {"status": "FAILED", "msg": "Permission denied"}  
                return {"status": "FAILED", "msg": "File not found"}  
              
            elif operation == 'WRITE':  
                try:  
                    content_str = cmd.get('content', '')  
                    raw_data = content_str.encode('latin-1')
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
            else:  
                return {"status": "FAILED", "msg": "Unknown operation"}  
        except Exception as e:  
            return {"status": "FAILED", "msg": str(e)}  
      
    def add_user(self, user_id, password):  
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()  
        self.users[user_id] = pwd_hash  
      
    def stop(self):  
        self.running = False  
        if self.socket:  
            try: self.socket.close()  
            except: pass


class RemoteAndroidApp(App):
    def build(self):
        self.title = "Internet Storage Access"
        
        if ANDROID:  
            self.request_android_permissions()  
          
        main_layout = BoxLayout(orientation='vertical', padding=30, spacing=25)  
          
        # Header - મોટા બોલ્ડ ફોન્ટ
        main_layout.add_widget(Label(  
            text="📱 Internet Storage Access",   
            font_size=48,   
            bold=True,
            color=(0, 0.67, 0.7, 1),   
            size_hint_y=0.1  
        ))  
          
        scroll = ScrollView()  
        scroll_layout = BoxLayout(orientation='vertical', spacing=20, size_hint_y=None)  
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))  
          
        # 📋 Remote ID (Detected IP)
        scroll_layout.add_widget(Label(text="📋 Remote ID (Detected IP):", font_size=36, bold=True, size_hint_y=None, height=60))  
        self.txt_id = TextInput(text="Detecting...", multiline=False, font_size=36, halign="center", size_hint_y=None, height=90, disabled=True)  
        scroll_layout.add_widget(self.txt_id)  
          
        # 🔐 Custom Password
        scroll_layout.add_widget(Label(text="🔐 Custom Password:", font_size=36, bold=True, size_hint_y=None, height=60))  
        self.txt_pass = TextInput(text="ats123", multiline=False, font_size=36, halign="center", password=True, size_hint_y=None, height=90)  
        scroll_layout.add_widget(self.txt_pass)  

        # 🌐 🌟 Pinggy Server Connection Command Box (જેનાથી કનેક્શન લિંક બદલી શકાય)
        scroll_layout.add_widget(Label(text="🌐 Pinggy Server Connection Command:", font_size=36, bold=True, size_hint_y=None, height=60))  
        pinggy_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, spacing=15)
        self.txt_tunnel_cmd = TextInput(
            text="ssh -p 443 -R0:localhost:5000 -o StrictHostKeyChecking=no -o ConnectTimeout=5 qr@pinggy.io",
            multiline=False, font_size=28, disabled=True
        )
        self.btn_edit_tunnel = Button(text="Edit", size_hint_x=0.2, font_size=30, bold=True, background_color=(0, 0.5, 0.7, 1))
        self.btn_edit_tunnel.bind(on_press=self.toggle_tunnel_edit)
        pinggy_box.add_widget(self.txt_tunnel_cmd)
        pinggy_box.add_widget(self.btn_edit_tunnel)
        scroll_layout.add_widget(pinggy_box)
          
        # 📋 Permissions Status
        scroll_layout.add_widget(Label(text="📋 Permissions Status:", font_size=32, bold=True, size_hint_y=None, height=50))  
        self.lbl_permissions = Label(text="⏳ Checking...", color=(1, 0.6, 0, 1), font_size=32, size_hint_y=None, height=70)  
        scroll_layout.add_widget(self.lbl_permissions)  
          
        # 📊 Real-time Network Status
        scroll_layout.add_widget(Label(text="📊 Real-time Network Status:", font_size=32, bold=True, size_hint_y=None, height=50))
        
        status_grid = BoxLayout(orientation='vertical', size_hint_y=None, height=360, spacing=15)
        self.lbl_net_internet = Label(text="🌐 Internet Connection: Checking...", font_size=32, halign="left", size_hint_y=None, height=60)
        self.lbl_net_local = Label(text="🏠 Local Network: Checking...", font_size=32, halign="left", size_hint_y=None, height=60)
        
        # 🔗 આ બોક્સમાં જનરેટ થયેલી અસલી લાઈવ લિંક ઓટોમેટિક મોટા અક્ષરે પ્રિન્ટ થશે
        self.lbl_net_remote = Label(
            text="🔗 Generated Tunnel Link: Inactive\n(Press Start to Generate)", 
            font_size=32, 
            bold=True,
            halign="center", 
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None, 
            height=140
        )
        
        status_grid.add_widget(self.lbl_net_internet)
        status_grid.add_widget(self.lbl_net_local)
        status_grid.add_widget(self.lbl_net_remote)
        scroll_layout.add_widget(status_grid)
          
        # 🚀 Start Button
        self.btn_start = Button(text="🚀 Start Services", size_hint_y=None, height=110, font_size=40, bold=True, background_color=(0, 0.67, 0.7, 1))  
        self.btn_start.bind(on_press=self.start_service)  
        scroll_layout.add_widget(self.btn_start)  
          
        scroll.add_widget(scroll_layout)  
        main_layout.add_widget(scroll)  
          
        self.tunnel_process = None  
        self.is_running = False  
        self.storage_server = RemoteStorageServer(port=5000)  
        self.permissions_granted = False  
          
        Clock.schedule_once(self.check_permissions, 1)  
        Clock.schedule_once(self.initialize_ip_id, 0.5)
        Clock.schedule_interval(self.update_network_status_ui, 3)
          
        return main_layout  

    def toggle_tunnel_edit(self, instance):
        if self.txt_tunnel_cmd.disabled:
            self.txt_tunnel_cmd.disabled = False
            self.btn_edit_tunnel.text = "Save"
            self.btn_edit_tunnel.background_color = (0, 0.7, 0.3, 1)
        else:
            self.txt_tunnel_cmd.disabled = True
            self.btn_edit_tunnel.text = "Edit"
            self.btn_edit_tunnel.background_color = (0, 0.5, 0.7, 1)

    def initialize_ip_id(self, dt):
        device_ip = self.get_device_ip()
        self.txt_id.text = str(device_ip)

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
            if not self.is_running:
                self.txt_id.text = str(ip)
        else:
            self.lbl_net_local.text = "🏠 Local Network: No Wi-Fi"
            self.lbl_net_local.color = (1, 0, 0, 1)

    def request_android_permissions(self):  
        if ANDROID:  
            try:  
                permissions = [  
                    Permission.INTERNET,  
                    Permission.READ_EXTERNAL_STORAGE,  
                    Permission.WRITE_EXTERNAL_STORAGE,  
                ]  
                request_permissions(permissions)  
            except Exception as e: print(f"⚠️ Permission request error: {e}")  

    def check_permissions(self, dt=None):  
        if not ANDROID:  
            self.lbl_permissions.text = "✅ Desktop Mode (No restrictions)"  
            self.lbl_permissions.color = (0, 1, 0, 1)  
            self.permissions_granted = True  
            return  
          
        try:  
            internet_ok = check_permission(Permission.INTERNET)  
            storage_read_ok = check_permission(Permission.READ_EXTERNAL_STORAGE)  
            storage_write_ok = check_permission(Permission.WRITE_EXTERNAL_STORAGE)  
              
            status_text = ""  
            all_ok = True  
              
            if internet_ok: status_text += "✅ Internet "  
            else: status_text += "❌ Internet "; all_ok = False  
              
            if storage_read_ok: status_text += "✅ Read "  
            else: status_text += "❌ Read "; all_ok = False  
              
            if storage_write_ok: status_text += "✅ Write"  
            else: status_text += "❌ Write"; all_ok = False  
              
            self.lbl_permissions.text = status_text  
              
            if all_ok:  
                self.lbl_permissions.color = (0, 1, 0, 1)  
                self.permissions_granted = True  
            else:  
                self.lbl_permissions.color = (1, 0, 0, 1)  
                self.permissions_granted = False  
                if ANDROID: self.request_android_permissions()  
        except Exception as e:  
            self.lbl_permissions.text = f"⚠️ Error: {str(e)[:30]}"  

    def get_device_ip(self):  
        try:  
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
            s.connect(("8.8.8.8", 80))  
            ip = s.getsockname()[0]  
            s.close()  
            return ip  
        except:  
            return "127.0.0.1"  

    def start_service(self, instance):  
        if ANDROID and not self.permissions_granted:  
            if ANDROID: toast("Please grant permissions first!")  
            return  
          
        if len(self.txt_pass.text.strip()) < 4:  
            if ANDROID: toast("Password minimum 4 chars!")  
            return  
          
        self.txt_pass.disabled = True  
        self.btn_start.disabled = True  
        self.txt_tunnel_cmd.disabled = True
        self.btn_edit_tunnel.disabled = True
        self.is_running = True  
        
        current_ip = self.get_device_ip()
        self.txt_id.text = str(current_ip)
        self.storage_server.add_user(self.txt_id.text, self.txt_pass.text)  
          
        Thread(target=self.storage_server.start, daemon=True).start()  
        
        self.lbl_net_remote.text = "🔄 Connecting to Pinggy Server..."
        self.lbl_net_remote.color = (1, 0.6, 0, 1)
        Thread(target=self.run_remote_tunnel, daemon=True).start()  

    def run_remote_tunnel(self):  
        cmd = self.txt_tunnel_cmd.text.strip()
          
        try:  
            if self.tunnel_process:  
                try: self.tunnel_process.terminate()  
                except: pass  
              
            self.tunnel_process = subprocess.Popen(  
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1  
            )  
              
            link_found = False
            for line in self.tunnel_process.stdout:
                if not self.is_running: break
                
                # પિંગી બેકગ્રાઉન્ડ હોસ્ટ સાથે કનેક્ટ થઈને નવી પબ્લિક લિંક આપે તેને જ ફિલ્ટર કરવું
                match = re.search(r'https://[a-zA-Z0-9\-]+\.pinggy\.link', line)
                if match:
                    full_url = match.group(0)
                    self.update_remote_label_ui(full_url, success=True)
                    link_found = True
                    break
            
            if not link_found:
                self.update_remote_label_ui("❌ Tunnel Connection Failed", success=False)
                
            while self.is_running and self.tunnel_process.poll() is None:
                time.sleep(2)
                
        except Exception as e:  
            self.update_remote_label_ui(f"❌ Error: {str(e)[:25]}", success=False)

    def update_remote_label_ui(self, text_val, success=True):
        def set_text(dt):
            self.lbl_net_remote.text = f"🔗 Generated Tunnel Link:\n{text_val}"
            if success:
                self.lbl_net_remote.color = (0, 1, 0, 1)
            else:
                self.lbl_net_remote.color = (1, 0, 0, 1)
        Clock.schedule_once(set_text)

    def on_stop(self):  
        self.is_running = False  
        self.storage_server.stop()  
        if self.tunnel_process:  
            try: self.tunnel_process.terminate()  
            except: pass

if __name__ == '__main__':
    RemoteAndroidApp().run()
            


