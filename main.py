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
from kivy.uix.gridlayout import GridLayout

# Android permissions
try:
    from android.permissions import request_permissions, Permission, check_permission
    from android.toast import toast
    ANDROID = True
except ImportError:
    ANDROID = False
    print("⚠️ Running on non-Android platform")

class RemoteStorageServer:
    """Backend storage server for remote file access"""
    def __init__(self, port=5000):
        self.port = port
        self.users = {}
        self.authenticated_sessions = set()
        self.running = False
        self.socket = None
    
    def start(self):
        """Start listening for connections"""
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
    
    def handle_client(self, client, addr):
        """Handle incoming client connection"""
        try:
            # Receive authentication
            auth_data = client.recv(1024).decode()
            if not auth_data:
                return
            
            auth_json = json.loads(auth_data)
            user_id = auth_json.get('id')
            password = auth_json.get('password')
            
            # Verify credentials
            if not self.verify_auth(user_id, password):
                client.send(json.dumps({"status": "FAILED", "msg": "Invalid credentials"}).encode())
                client.close()
                return
            
            # Send success
            client.send(json.dumps({"status": "OK", "msg": "Authenticated"}).encode())
            self.authenticated_sessions.add(addr[0])
            print(f"✅ User {user_id} authenticated from {addr[0]}")
            
            # Handle commands
            while True:
                try:
                    cmd_data = client.recv(2048).decode()
                    if not cmd_data:
                        break
                    
                    cmd_json = json.loads(cmd_data)
                    response = self.process_command(cmd_json)
                    client.send(json.dumps(response).encode())
                except Exception as e:
                    print(f"❌ Command error: {e}")
                    break
        
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
        """Process file operations: LIST, READ, WRITE, DELETE"""
        try:
            operation = cmd.get('op')
            path = cmd.get('path', '/sdcard/')
            
            # Security: Only allow /sdcard/ and /storage/
            if not (path.startswith('/sdcard/') or path.startswith('/storage/')):
                return {"status": "FAILED", "msg": "Access denied"}
            
            if operation == 'LIST':
                files = []
                if os.path.isdir(path):
                    try:
                        files = os.listdir(path)
                    except PermissionError:
                        return {"status": "FAILED", "msg": "Permission denied"}
                return {"status": "OK", "files": files}
            
            elif operation == 'READ':
                if os.path.isfile(path):
                    try:
                        with open(path, 'r') as f:
                            content = f.read()
                        return {"status": "OK", "content": content}
                    except PermissionError:
                        return {"status": "FAILED", "msg": "Permission denied"}
                return {"status": "FAILED", "msg": "File not found"}
            
            elif operation == 'WRITE':
                try:
                    content = cmd.get('content', '')
                    with open(path, 'w') as f:
                        f.write(content)
                    return {"status": "OK", "msg": "File written"}
                except PermissionError:
                    return {"status": "FAILED", "msg": "Permission denied"}
            
            elif operation == 'DELETE':
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        return {"status": "OK", "msg": "File deleted"}
                    except PermissionError:
                        return {"status": "FAILED", "msg": "Permission denied"}
                return {"status": "FAILED", "msg": "File not found"}
            
            else:
                return {"status": "FAILED", "msg": "Unknown operation"}
        
        except Exception as e:
            return {"status": "FAILED", "msg": str(e)}
    
    def add_user(self, user_id, password):
        """Register user credentials"""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        self.users[user_id] = pwd_hash
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

class RemoteAndroidApp(App):
    def build(self):
        self.title = "ATS Remote Connector"
        
        # Request permissions on Android
        if ANDROID:
            self.request_android_permissions()
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Header
        main_layout.add_widget(Label(
            text="📱 ATS Remote Android Service", 
            font_size=24, 
            color=(0, 0.67, 0.7, 1), 
            size_hint_y=0.08
        ))
        
        # Scrollable content
        scroll = ScrollView()
        scroll_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))
        
        # Remote ID Section
        scroll_layout.add_widget(Label(
            text="📋 10-Digit Remote ID:", 
            font_size=16, 
            size_hint_y=None, 
            height=40,
            color=(1, 1, 1, 1)
        ))
        default_id = "".join(random.choices(string.digits, k=10))
        self.txt_id = TextInput(
            text=default_id, 
            multiline=False, 
            font_size=18, 
            halign="center", 
            size_hint_y=None, 
            height=50
        )
        scroll_layout.add_widget(self.txt_id)
        
        # Password Section
        scroll_layout.add_widget(Label(
            text="🔐 Custom Password:", 
            font_size=16, 
            size_hint_y=None, 
            height=40,
            color=(1, 1, 1, 1)
        ))
        self.txt_pass = TextInput(
            text="ats123", 
            multiline=False, 
            font_size=18, 
            halign="center", 
            password=True, 
            size_hint_y=None, 
            height=50
        )
        scroll_layout.add_widget(self.txt_pass)
        
        # Permissions Status
        scroll_layout.add_widget(Label(
            text="📋 Permissions Status:", 
            font_size=14, 
            size_hint_y=None, 
            height=30,
            color=(1, 1, 1, 1)
        ))
        self.lbl_permissions = Label(
            text="⏳ Checking permissions...", 
            color=(1, 0.6, 0, 1), 
            font_size=12, 
            size_hint_y=None, 
            height=60
        )
        scroll_layout.add_widget(self.lbl_permissions)
        
        # Start Button
        self.btn_start = Button(
            text="🚀 Start Services", 
            size_hint_y=None, 
            height=50, 
            background_color=(0, 0.67, 0.7, 1)
        )
        self.btn_start.bind(on_press=self.start_service)
        scroll_layout.add_widget(self.btn_start)
        
        # Connection Type
        scroll_layout.add_widget(Label(
            text="🔗 Connection Type:", 
            font_size=14, 
            size_hint_y=None, 
            height=30,
            color=(1, 1, 1, 1)
        ))
        self.lbl_conn_type = Label(
            text="⏳ Initializing...", 
            color=(1, 0.6, 0, 1), 
            font_size=12, 
            size_hint_y=None, 
            height=40
        )
        scroll_layout.add_widget(self.lbl_conn_type)
        
        # Status
        scroll_layout.add_widget(Label(
            text="📌 Status:", 
            font_size=14, 
            size_hint_y=None, 
            height=30,
            color=(1, 1, 1, 1)
        ))
        self.lbl_status = Label(
            text="🔴 Stopped", 
            color=(1, 0, 0, 1), 
            font_size=14, 
            size_hint_y=None, 
            height=40
        )
        scroll_layout.add_widget(self.lbl_status)
        
        # Local Access
        scroll_layout.add_widget(Label(
            text="🏠 Local Access (Same Network):", 
            font_size=14, 
            size_hint_y=None, 
            height=30,
            color=(1, 1, 1, 1)
        ))
        self.lbl_local = Label(
            text="📍 Device IP: --", 
            color=(0.7, 0.7, 0.7, 1), 
            font_size=12, 
            size_hint_y=None, 
            height=40
        )
        scroll_layout.add_widget(self.lbl_local)
        
        # Remote Access
        scroll_layout.add_widget(Label(
            text="🌐 Remote Access (Different Network):", 
            font_size=14, 
            size_hint_y=None, 
            height=30,
            color=(1, 1, 1, 1)
        ))
        self.lbl_remote = Label(
            text="🌐 Tunnel: --", 
            color=(0.7, 0.7, 0.7, 1), 
            font_size=12, 
            size_hint_y=None, 
            height=60
        )
        scroll_layout.add_widget(self.lbl_remote)
        
        # Storage Server
        scroll_layout.add_widget(Label(
            text="💾 Storage Server:", 
            font_size=14, 
            size_hint_y=None, 
            height=30,
            color=(1, 1, 1, 1)
        ))
        self.lbl_storage = Label(
            text="⏳ Initializing...", 
            color=(1, 0.6, 0, 1), 
            font_size=12, 
            size_hint_y=None, 
            height=40
        )
        scroll_layout.add_widget(self.lbl_storage)
        
        # Info Section
        scroll_layout.add_widget(Label(text="", size_hint_y=None, height=20))
        info_text = "ℹ️ Required Permissions:\n✓ INTERNET - Network access\n✓ READ_EXTERNAL_STORAGE - Read files\n✓ WRITE_EXTERNAL_STORAGE - Write files\n\n📱 From Linux PC:\npython3 linux_client_remote.py"
        scroll_layout.add_widget(Label(
            text=info_text, 
            font_size=11, 
            color=(0.7, 0.7, 0.7, 1), 
            size_hint_y=None, 
            height=140
        ))
        
        scroll.add_widget(scroll_layout)
        main_layout.add_widget(scroll)
        
        # Instance variables
        self.tunnel_process = None
        self.is_running = False
        self.storage_server = RemoteStorageServer(port=5000)
        self.tunnel_url = None
        self.permissions_granted = False
        
        # Check permissions after build
        Clock.schedule_once(self.check_permissions, 1)
        
        return main_layout

    def request_android_permissions(self):
        """Request Android permissions"""
        if ANDROID:
            try:
                print("📋 Requesting Android permissions...")
                permissions = [
                    Permission.INTERNET,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ]
                request_permissions(permissions)
            except Exception as e:
                print(f"⚠️ Permission request error: {e}")

    def check_permissions(self, dt=None):
        """Check if permissions are granted"""
        if not ANDROID:
            self.lbl_permissions.text = "✅ Desktop Mode (No permissions needed)"
            self.lbl_permissions.color = (0, 1, 0, 1)
            self.permissions_granted = True
            return
        
        try:
            internet_ok = check_permission(Permission.INTERNET)
            storage_read_ok = check_permission(Permission.READ_EXTERNAL_STORAGE)
            storage_write_ok = check_permission(Permission.WRITE_EXTERNAL_STORAGE)
            
            status_text = ""
            all_ok = True
            
            if internet_ok:
                status_text += "✅ Internet\n"
            else:
                status_text += "❌ Internet\n"
                all_ok = False
            
            if storage_read_ok:
                status_text += "✅ Read Storage\n"
            else:
                status_text += "❌ Read Storage\n"
                all_ok = False
            
            if storage_write_ok:
                status_text += "✅ Write Storage"
            else:
                status_text += "❌ Write Storage"
                all_ok = False
            
            self.lbl_permissions.text = status_text
            
            if all_ok:
                self.lbl_permissions.color = (0, 1, 0, 1)
                self.permissions_granted = True
                print("✅ All permissions granted!")
            else:
                self.lbl_permissions.color = (1, 0, 0, 1)
                self.permissions_granted = False
                print("⚠️ Some permissions missing")
                if ANDROID:
                    self.request_android_permissions()
        
        except Exception as e:
            print(f"⚠️ Permission check error: {e}")
            self.lbl_permissions.text = f"⚠️ Error: {str(e)[:30]}"
            self.lbl_permissions.color = (1, 0.6, 0, 1)

    def get_device_ip(self):
        """Get device local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start_service(self, instance):
        """Start all services"""
        # Check permissions first
        if ANDROID and not self.permissions_granted:
            self.lbl_status.text = "❌ Permissions not granted!"
            self.lbl_status.color = (1, 0, 0, 1)
            if ANDROID:
                toast("Please grant permissions first!")
            return
        
        # Validate ID
        if len(self.txt_id.text.strip()) != 10 or not self.txt_id.text.isdigit():
            self.lbl_status.text = "❌ ID must be 10 digits!"
            self.lbl_status.color = (1, 0, 0, 1)
            if ANDROID:
                toast("ID must be exactly 10 digits!")
            return

        # Validate password
        if len(self.txt_pass.text.strip()) < 4:
            self.lbl_status.text = "❌ Password minimum 4 chars!"
            self.lbl_status.color = (1, 0, 0, 1)
            if ANDROID:
                toast("Password must be at least 4 characters!")
            return

        self.lbl_status.text = "⏳ Starting services..."
        self.lbl_status.color = (1, 0.6, 0, 1)
        
        self.txt_id.disabled = True
        self.txt_pass.disabled = True
        self.btn_start.disabled = True
        
        self.is_running = True
        
        # Register user in storage server
        self.storage_server.add_user(self.txt_id.text, self.txt_pass.text)
        
        # Get device local IP
        device_ip = self.get_device_ip()
        Clock.schedule_once(lambda dt: self._update_local_ip(device_ip), 0)
        
        # Start storage server (most important - local access)
        Thread(target=self.storage_server.start, daemon=True).start()
        Clock.schedule_once(lambda dt: self._check_storage_started(), 1)
        
        # Try to start SSH tunnel (optional - remote access)
        Thread(target=self.run_remote_tunnel, daemon=True).start()

    def _update_local_ip(self, ip):
        """Update local IP display"""
        self.lbl_local.text = f"📍 Device IP: {ip}:5000"
        self.lbl_local.color = (0, 1, 0, 1)

    def _check_storage_started(self):
        """Check if storage server started"""
        if self.storage_server.running:
            Clock.schedule_once(self.update_ui_success, 0)
        else:
            Clock.schedule_once(lambda dt: self._check_storage_started(), 1)

    def run_remote_tunnel(self):
        """Establish SSH tunnel for remote access"""
        cmd = "ssh -p 443 -R0:localhost:5000 -o StrictHostKeyChecking=no -o ConnectTimeout=5 qr@pinggy.io"
        
        retry_count = 0
        while self.is_running and retry_count < 5:
            try:
                if self.tunnel_process:
                    try:
                        self.tunnel_process.terminate()
                        self.tunnel_process.wait(timeout=2)
                    except:
                        pass
                
                print(f"🔄 Attempting SSH tunnel (try {retry_count + 1})...")
                
                self.tunnel_process = subprocess.Popen(
                    cmd, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    bufsize=1
                )
                
                time.sleep(4)
                
                # Check if process died immediately
                if self.tunnel_process.poll() is not None:
                    stderr = self.tunnel_process.stderr.read() if self.tunnel_process.stderr else ""
                    print(f"SSH error: {stderr}")
                    retry_count += 1
                    time.sleep(5)
                    continue
                
                print("✅ SSH tunnel established")
                Clock.schedule_once(self.update_tunnel_success, 0)
                time.sleep(3300)  # 55 minutes
                
            except FileNotFoundError:
                print("❌ SSH binary not found")
                Clock.schedule_once(lambda dt: self._update_no_ssh(), 0)
                break
            except subprocess.TimeoutExpired:
                print("SSH timeout")
                retry_count += 1
                time.sleep(5)
            except Exception as e:
                print(f"SSH error: {e}")
                retry_count += 1
                time.sleep(5)

    def update_ui_success(self, dt):
        """Update UI when services are running"""
        user_id = self.txt_id.text
        self.lbl_status.text = f"🟢 Connected! ID: {user_id}"
        self.lbl_status.color = (0, 1, 0, 1)
        self.lbl_storage.text = "✅ Storage Server: Ready (Port 5000)"
        self.lbl_storage.color = (0, 1, 0, 1)
        self.lbl_conn_type.text = "🔗 Local Access Active"
        self.lbl_conn_type.color = (0, 1, 0, 1)

    def update_tunnel_success(self, dt):
        """Update UI when tunnel is active"""
        self.lbl_remote.text = "🌐 SSH Tunnel: Active\n   Remote access available"
        self.lbl_remote.color = (0, 1, 0, 1)
        self.lbl_conn_type.text = "🔗 Both Local & Remote Active"
        self.lbl_conn_type.color = (0, 1, 0, 1)

    def _update_no_ssh(self):
        """Update UI when SSH not available"""
        self.lbl_remote.text = "⚠️ SSH Tunnel: Not available\n   Use local network access"
        self.lbl_remote.color = (1, 0.6, 0, 1)

    def on_stop(self):
        """Cleanup on app exit"""
        self.is_running = False
        self.storage_server.stop()
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
            except:
                pass

if __name__ == '__main__':
    RemoteAndroidApp().run()









