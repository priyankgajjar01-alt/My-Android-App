import random
import string
import time
import subprocess
import os
import json
import socket
import hashlib
from threading import Thread
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock

class RemoteStorageServer:
    """Backend server for remote file access from Linux PC"""
    def __init__(self, port=5000):
        self.port = port
        self.users = {}  # {id: password_hash}
        self.authenticated_sessions = set()
    
    def start(self):
        """Start listening for connections from Linux PC"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(5)
            print(f"✅ Storage Server listening on port {self.port}")
            
            while True:
                try:
                    client, addr = self.socket.accept()
                    Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
                except Exception as e:
                    print(f"❌ Server error: {e}")
        except Exception as e:
            print(f"❌ Failed to start storage server: {e}")
    
    def handle_client(self, client, addr):
        """Handle incoming connection from Linux PC"""
        try:
            auth_data = client.recv(1024).decode()
            auth_json = json.loads(auth_data)
            
            user_id = auth_json.get('id')
            password = auth_json.get('password')
            
            if not self.verify_auth(user_id, password):
                client.send(json.dumps({"status": "FAILED", "msg": "Invalid credentials"}).encode())
                client.close()
                return
            
            client.send(json.dumps({"status": "OK", "msg": "Authenticated"}).encode())
            self.authenticated_sessions.add(addr[0])
            
            while True:
                cmd_data = client.recv(2048).decode()
                if not cmd_data:
                    break
                
                cmd_json = json.loads(cmd_data)
                response = self.process_command(cmd_json)
                client.send(json.dumps(response).encode())
        
        except Exception as e:
            print(f"❌ Client error: {e}")
        finally:
            try:
                self.authenticated_sessions.discard(addr[0])
                client.close()
            except:
                pass
    
    def verify_auth(self, user_id, password):
        """Verify user credentials"""
        if user_id in self.users:
            stored_hash = self.users[user_id]
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            return stored_hash == pwd_hash
        return False
    
    def process_command(self, cmd):
        """Process file operations: read, write, delete, list"""
        try:
            operation = cmd.get('op')
            path = cmd.get('path', '/sdcard/')
            
            if operation == 'LIST':
                files = []
                if os.path.isdir(path):
                    files = os.listdir(path)
                return {"status": "OK", "files": files}
            
            elif operation == 'READ':
                if os.path.isfile(path):
                    with open(path, 'r') as f:
                        content = f.read()
                    return {"status": "OK", "content": content}
                return {"status": "FAILED", "msg": "File not found"}
            
            elif operation == 'WRITE':
                content = cmd.get('content', '')
                with open(path, 'w') as f:
                    f.write(content)
                return {"status": "OK", "msg": "File written"}
            
            elif operation == 'DELETE':
                if os.path.isfile(path):
                    os.remove(path)
                    return {"status": "OK", "msg": "File deleted"}
                return {"status": "FAILED", "msg": "File not found"}
            
            else:
                return {"status": "FAILED", "msg": "Unknown operation"}
        
        except Exception as e:
            return {"status": "FAILED", "msg": str(e)}
    
    def add_user(self, user_id, password):
        """Register user credentials"""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        self.users[user_id] = pwd_hash

class RemoteAndroidApp(App):
    def build(self):
        self.title = "ATS Remote Connector"
        
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Header
        main_layout.add_widget(Label(text="📱 ATS Remote Android Service", font_size=24, color=(0, 0.67, 0.7, 1), size_hint_y=0.1))
        
        # Scrollable content
        scroll = ScrollView()
        scroll_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))
        
        # Remote ID
        scroll_layout.add_widget(Label(text="📋 Set 10-Digit Remote ID:", font_size=16, size_hint_y=None, height=40))
        default_id = "".join(random.choices(string.digits, k=10))
        self.txt_id = TextInput(text=default_id, multiline=False, font_size=18, halign="center", size_hint_y=None, height=50)
        scroll_layout.add_widget(self.txt_id)
        
        # Password
        scroll_layout.add_widget(Label(text="🔐 Set Custom Password:", font_size=16, size_hint_y=None, height=40))
        self.txt_pass = TextInput(text="ats123", multiline=False, font_size=18, halign="center", password=True, size_hint_y=None, height=50)
        scroll_layout.add_widget(self.txt_pass)
        
        # Start Button
        self.btn_start = Button(text="🚀 Start Remote Connection", size_hint_y=None, height=50, background_color=(0, 0.67, 0.7, 1))
        self.btn_start.bind(on_press=self.start_service)
        scroll_layout.add_widget(self.btn_start)
        
        # Status
        scroll_layout.add_widget(Label(text="Status:", font_size=14, size_hint_y=None, height=30))
        self.lbl_status = Label(text="🔴 Status: Stopped", color=(1, 0, 0, 1), font_size=14, size_hint_y=None, height=40)
        scroll_layout.add_widget(self.lbl_status)
        
        scroll_layout.add_widget(Label(text="Tunnel Link:", font_size=14, size_hint_y=None, height=30))
        self.lbl_tunnel = Label(text="❌ Tunnel Link: Not Active", color=(0.7, 0.7, 0.7, 1), font_size=12, size_hint_y=None, height=40)
        scroll_layout.add_widget(self.lbl_tunnel)
        
        scroll_layout.add_widget(Label(text="Storage Access:", font_size=14, size_hint_y=None, height=30))
        self.lbl_storage = Label(text="⏳ Storage Server: Initializing...", color=(1, 0.6, 0, 1), font_size=12, size_hint_y=None, height=40)
        scroll_layout.add_widget(self.lbl_storage)
        
        # Info
        scroll_layout.add_widget(Label(text="", size_hint_y=None, height=20))
        info_text = "ℹ️ Linux PC Connection:\nUse ID & Password to remotely:\n✓ Copy/Paste files\n✓ Delete files\n✓ List storage"
        scroll_layout.add_widget(Label(text=info_text, font_size=11, color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=100))
        
        scroll.add_widget(scroll_layout)
        main_layout.add_widget(scroll)
        
        self.tunnel_process = None
        self.is_running = False
        self.storage_server = RemoteStorageServer(port=5000)
        
        return main_layout

    def start_service(self, instance):
        if len(self.txt_id.text.strip()) != 10 or not self.txt_id.text.isdigit():
            self.lbl_status.text = "❌ Error: ID must be exactly 10 digits!"
            self.lbl_status.color = (1, 0, 0, 1)
            return

        if len(self.txt_pass.text.strip()) < 4:
            self.lbl_status.text = "❌ Error: Password must be at least 4 characters!"
            self.lbl_status.color = (1, 0, 0, 1)
            return

        self.lbl_status.text = "⏳ Starting secure services..."
        self.lbl_status.color = (1, 0.6, 0, 1)
        
        self.txt_id.disabled = True
        self.txt_pass.disabled = True
        self.btn_start.disabled = True
        
        self.is_running = True
        
        # Register user
        self.storage_server.add_user(self.txt_id.text, self.txt_pass.text)
        
        # Start services
        Thread(target=self.storage_server.start, daemon=True).start()
        Thread(target=self.run_backend_bridge, daemon=True).start()

    def run_backend_bridge(self):
        cmd = "ssh -p 443 -R0:localhost:5000 -o StrictHostKeyChecking=no qr@pinggy.io"
        
        while self.is_running:
            try:
                if self.tunnel_process:
                    try:
                        self.tunnel_process.terminate()
                        self.tunnel_process.wait(timeout=2)
                    except:
                        pass
                
                try:
                    self.tunnel_process = subprocess.Popen(
                        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                    )
                    
                    time.sleep(3)
                    
                    if self.tunnel_process.poll() is not None:
                        errors = self.tunnel_process.stderr.read()
                        error_msg = f"SSH Error: {errors if errors else 'SSH binary not found'}"
                        raise Exception(error_msg)
                    
                    Clock.schedule_once(self.update_ui_success, 0)
                    time.sleep(3300)
                
                except FileNotFoundError:
                    error_msg = "SSH binary not found on system"
                    Clock.schedule_once(lambda dt: self.update_ui_error(error_msg), 0)
                    time.sleep(10)
                    
            except Exception as e:
                error_msg = str(e)
                Clock.schedule_once(lambda dt: self.update_ui_error(error_msg), 0)
                time.sleep(10)

    def update_ui_success(self, dt):
        user_id = self.txt_id.text
        self.lbl_status.text = f"🟢 Connected! ID: {user_id}"
        self.lbl_status.color = (0, 1, 0, 1)
        self.lbl_tunnel.text = "✅ Tunnel: Active & Auto-Refreshing"
        self.lbl_storage.text = "✅ Storage Server: Ready (Port 5000)"
        self.lbl_storage.color = (0, 1, 0, 1)

    def update_ui_error(self, error_msg):
        self.txt_id.disabled = False
        self.txt_pass.disabled = False
        self.btn_start.disabled = False
        self.is_running = False
        
        self.lbl_status.text = f"❌ Connection Failed!"
        self.lbl_status.color = (1, 0, 0, 1)
        self.lbl_tunnel.text = f"Error: {error_msg[:50]}..."
        self.lbl_storage.text = "❌ Storage Server: Failed to start"
        self.lbl_storage.color = (1, 0, 0, 1)

    def on_stop(self):
        self.is_running = False
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
            except:
                pass

if __name__ == '__main__':
    RemoteAndroidApp().run()
