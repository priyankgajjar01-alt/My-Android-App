import threading
import socket
import os
import shutil
import websocket
from kivy.config import Config

Config.set( 'graphics', 'resizable', '0' )

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.core.window import Window

# ============================================================
# ANDROID IMPORTS
# ============================================================
ANDROID = False
try:
    from android.permissions import (
        request_permissions, check_permission, Permission
    )
    from jnius import autoclass
    ANDROID = True
except Exception:
    ANDROID = False

# ============================================================
# WINDOW
# ============================================================
Window.clearcolor = ( 0.13, 0.20, 0.38, 1 )

# ============================================================
# KV UI
# ============================================================
KV = r"""
<RootWidget>:
    anchor_x: 'center'
    anchor_y: 'center'
    
    ScrollView:
        size_hint: (0.95, 0.9)
        do_scroll_x: False
        bar_width: 8
        
        GridLayout:
            id: main_grid
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            padding: dp(10)
            spacing: dp(16)
            
            # ====================================================
            # TITLE
            # ====================================================
            Label:
                text: "Android Tunnel Receiver"
                color: (1, 0.84, 0.00, 1)
                bold: True
                font_size: '22sp'
                size_hint_y: None
                height: dp(48)
                halign: "center"
                valign: "middle"
                
            # ====================================================
            # TARGET IP
            # ====================================================
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                Label:
                    text: "Target IP :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    
                TextInput:
                    id: etIp
                    text: app.local_ip
                    hint_text: "Enter PC IP..."
                    multiline: False
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    
            # ====================================================
            # TUNNEL
            # ====================================================
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                Label:
                    text: "Tunnel :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    
                TextInput:
                    id: etTunnel
                    text: app.tunnel_link
                    hint_text: "e.g. https://link.com"
                    multiline: False
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    padding: [dp(10), (self.height - self.line_height) / 2.0, dp(10), 0]
                    
            # ====================================================
            # PORT
            # ====================================================
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(10)
                
                Label:
                    text: "Port :"
                    color: (1, 0.84, 0.00, 1)
                    bold: True
                    font_size: '18sp'
                    size_hint_x: 0.35
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    
                Spinner:
                    id: etPort
                    text: app.port_value
                    values: ["443", "5000"]
                    size_hint_x: 0.65
                    font_size: '21sp'
                    bold: True
                    halign: 'center'
                    valign: 'middle'
                    
            # ====================================================
            # BUTTONS
            # ====================================================
            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(60)
                spacing: dp(14)
                padding: [0, dp(10), 0, 0]
                
                Button:
                    text: "START"
                    bold: True
                    font_size: '20sp'
                    color: (0, 0, 0, 1)
                    background_color: (0.4, 1, 0.4, 1)
                    disabled: app.start_disabled
                    on_release: app.start_connection()
                    
                Button:
                    text: "STOP"
                    bold: True
                    font_size: '20sp'
                    color: (0, 0, 0, 1)
                    background_color: (1.0, 0.23, 0.19, 1)
                    disabled: app.stop_disabled
                    on_release: app.stop_connection()
                    
            # ====================================================
            # STATUS
            # ====================================================
            Label:
                id: statusLabel
                text: app.status_text
                color: (1, 0.84, 0.00, 1)
                bold: True
                font_size: '18sp'
                size_hint_y: None
                height: dp(70)
                halign: "center"
                valign: "middle"
                text_size: self.width, None
"""

# ============================================================
# ROOT
# ============================================================
class RootWidget(AnchorLayout):
    pass

# ============================================================
# MAIN APP
# ============================================================
class MainApp(App):
    
    # ========================================================
    # PROPERTIES
    # ========================================================
    local_ip = StringProperty( "0.0.0.0" )
    tunnel_link = StringProperty( "" )
    port_value = StringProperty( "5000" )
    status_text = StringProperty( "Status: idle" )
    running = BooleanProperty( False )
    start_disabled = BooleanProperty( False )
    stop_disabled = BooleanProperty( True )
    
    # ========================================================
    # INIT
    # ========================================================
    def __init__(self, **kwargs):
        super().__init__( **kwargs )
        self.stop_flag = threading.Event()
        self.ws_client = None
        self.permission_check_done = False
        self.wake_lock = None
        self.wifi_lock = None

    # ========================================================
    # BUILD
    # ========================================================
    def build(self):
        Builder.load_string( KV )
        self.local_ip = ( self.get_local_ipv4() or "0.0.0.0" )
        self.status_text = ( "Checking storage permission..." )
        
        if ANDROID:
            Clock.schedule_once( lambda dt: self.check_storage_permission(), 1 )
        else:
            self.status_text = ( "Status: idle" )
            
        return RootWidget()

    # ========================================================
    # GET LOCAL IP
    # ========================================================
    def get_local_ipv4(self):
        try:
            s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
            s.connect( ( "8.8.8.8", 80 ) )
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    # ========================================================
    # ANDROID SDK
    # ========================================================
    def get_android_sdk(self):
        if not ANDROID:
            return 0
        try:
            Build = autoclass( 'android.os.Build$VERSION' )
            return int( Build.SDK_INT )
        except Exception:
            return 0

    # ========================================================
    # BACKGROUND LOCKS
    # ========================================================
    def acquire_background_locks(self):
        if not ANDROID:
            return
        try:
            PythonActivity = autoclass( 'org.kivy.android.PythonActivity' )
            activity = ( PythonActivity.mActivity )
            
            # CPU WAKE LOCK
            pm = activity.getSystemService( "power" )
            self.wake_lock = pm.newWakeLock( 1, "AndroidTunnel::CPUWakeLock" )
            self.wake_lock.acquire()
            
            # WIFI LOCK
            wm = activity.getSystemService( "wifi" )
            self.wifi_lock = wm.createWifiLock( 3, "AndroidTunnel::WiFiLock" )
            self.wifi_lock.acquire()
            
            print( "Background locks acquired" )
        except Exception as e:
            print( "Failed to acquire locks:", repr(e) )

    # ========================================================
    # RELEASE BACKGROUND LOCKS
    # ========================================================
    def release_background_locks(self):
        if not ANDROID:
            return
        try:
            if ( self.wake_lock and self.wake_lock.isHeld() ):
                self.wake_lock.release()
            if ( self.wifi_lock and self.wifi_lock.isHeld() ):
                self.wifi_lock.release()
                
            self.wake_lock = None
            self.wifi_lock = None
            print( "Background locks released" )
        except Exception as e:
            print( "Failed to release locks:", repr(e) )

    # ========================================================
    # STORAGE PERMISSION
    # ========================================================
    def check_storage_permission(self):
        if not ANDROID:
            self.permission_check_done = True
            self.status_text = ( "Status: idle" )
            return True
            
        sdk = self.get_android_sdk()
        if sdk >= 30:
            try:
                Environment = autoclass( 'android.os.Environment' )
                if Environment.isExternalStorageManager():
                    self.permission_check_done = True
                    self.status_text = ( "Storage Permission: GRANTED" )
                    return True
                    
                self.permission_check_done = False
                self.status_text = ( "Allow All Files Access in Settings" )
                Clock.schedule_once( lambda dt: self.open_all_files_settings(), 0.5 )
                return False
            except Exception as e:
                print( "Storage permission error:", repr(e) )
                self.status_text = ( "Storage Permission Error" )
                return False
        else:
            try:
                permissions = []
                if not check_permission( Permission.READ_EXTERNAL_STORAGE ):
                    permissions.append( Permission.READ_EXTERNAL_STORAGE )
                if not check_permission( Permission.WRITE_EXTERNAL_STORAGE ):
                    permissions.append( Permission.WRITE_EXTERNAL_STORAGE )
                    
                if permissions:
                    request_permissions( permissions, self.permission_callback )
                    self.status_text = ( "Requesting Storage Permission..." )
                    return False
                    
                self.permission_check_done = True
                self.status_text = ( "Storage Permission: GRANTED" )
                return True
            except Exception as e:
                print( "Legacy permission error:", repr(e) )
                self.status_text = ( "Storage Permission Error" )
                return False

    # ========================================================
    # PERMISSION CALLBACK
    # ========================================================
    def permission_callback( self, permissions, grants ):
        if all(grants):
            self.permission_check_done = True
            self.status_text = ( "Storage Permission: GRANTED" )
        else:
            self.permission_check_done = False
            self.status_text = ( "Storage Permission: DENIED" )

    # ========================================================
    # OPEN ALL FILES SETTINGS
    # ========================================================
    def open_all_files_settings(self):
        if not ANDROID:
            return
        try:
            PythonActivity = autoclass( 'org.kivy.android.PythonActivity' )
            Intent = autoclass( 'android.content.Intent' )
            Settings = autoclass( 'android.provider.Settings' )
            Uri = autoclass( 'android.net.Uri' )
            
            activity = ( PythonActivity.mActivity )
            package_name = ( activity.getPackageName() )
            
            intent = Intent( Settings .ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION )
            intent.setData( Uri.parse( "package:" + package_name ) )
            activity.startActivity( intent )
            
            Clock.schedule_once( lambda dt: self.check_storage_permission(), 2 )
        except Exception as e:
            print( "All files settings error:", repr(e) )
            try:
                PythonActivity = autoclass( 'org.kivy.android.PythonActivity' )
                Intent = autoclass( 'android.content.Intent' )
                Settings = autoclass( 'android.provider.Settings' )
                intent = Intent( Settings .ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION )
                PythonActivity.mActivity.startActivity( intent )
            except Exception as e2:
                print( "Fallback settings error:", repr(e2) )

    # ========================================================
    # START CONNECTION
    # ========================================================
    def start_connection(self):
        if self.running:
            return
            
        if ANDROID:
            if not self.permission_check_done:
                if not self.check_storage_permission():
                    return
                    
        tunnel_url = ( self.root .ids .etTunnel .text .strip() )
        if tunnel_url:
            ws_url = tunnel_url
            if ws_url.startswith( "https://" ):
                ws_url = ( "wss://" + ws_url[8:] )
            elif ws_url.startswith( "http://" ):
                ws_url = ( "ws://" + ws_url[7:] )
            elif not ws_url.startswith( ( "ws://", "wss://" ) ):
                ws_url = ( "wss://" + ws_url )
        else:
            host = ( self.root .ids .etIp .text .strip() )
            if not host:
                host = ( "127.0.0.1" )
            port = ( self.root .ids .etPort .text .strip() )
            if not port:
                port = ( "5000" )
            ws_url = ( f"ws://{host}:{port}" )
            
        self.acquire_background_locks()
        
        self.running = True
        self.start_disabled = True
        self.stop_disabled = False
        self.stop_flag.clear()
        
        self.status_text = ( f"Connecting to {ws_url}..." )
        
        threading.Thread(
            target=self.client_loop,
            args=( ws_url, ),
            daemon=True
        ).start()

    # ========================================================
    # STOP CONNECTION
    # ========================================================
    def stop_connection(self):
        if not self.running:
            return
            
        self.stop_flag.set()
        self.release_background_locks()
        
        self.running = False
        self.start_disabled = False
        self.stop_disabled = True
        self.status_text = ( "Status: stopped" )
        
        if self.ws_client:
            try:
                self.ws_client.close()
            except Exception:
                pass
            self.ws_client = None

    # ========================================================
    # STATUS
    # ========================================================
    def _set_status( self, text ):
        self.status_text = text

    # ========================================================
    # CLIENT LOOP
    # ========================================================
    def client_loop( self, ws_url ):
        print( "CLIENT: Starting connection" )
        try:
            self.ws_client = ( websocket.WebSocket() )
            self.ws_client.settimeout( 15.0 )
            
            print( "CLIENT: Connecting to:", ws_url )
            self.ws_client.connect( ws_url )
            print( "CLIENT: Connected successfully" )
            
            self.ws_client.settimeout( None )
            Clock.schedule_once( lambda dt: self._set_status( "Connected! PC Controlled." ), 0 )
            
            # =================================================
            # ONE REQUEST → ONE RESPONSE
            # =================================================
            while not self.stop_flag.is_set():
                try:
                    print( "CLIENT: Waiting for PC request..." )
                    data = ( self.ws_client.recv() )
                except websocket.WebSocketConnectionClosedException:
                    print( "CLIENT: WebSocket closed by PC" )
                    break
                except Exception as e:
                    print( "CLIENT: Receive error:", repr(e) )
                    break
                    
                if not data:
                    break
                    
                if isinstance( data, bytes ):
                    data = data.decode( "utf-8" )
                    
                data = data.strip()
                print( "CLIENT: Command received:", repr(data) )
                
                parts = data.split( "|" )
                if not parts:
                    self.ws_client.send( "ERROR|Empty command" )
                    continue
                    
                cmd = parts[0].upper()
                
                # =================================================
                # LS
                # =================================================
                if cmd == "LS":
                    if len(parts) < 2:
                        self.ws_client.send( "ERROR|Invalid LS command" )
                        continue
                        
                    path = parts[1]
                    try:
                        if not os.path.isdir(path):
                            self.ws_client.send( "ERROR|Folder not found" )
                            continue
                            
                        items_info = []
                        for name in os.listdir(path):
                            full_path = os.path.join( path, name )
                            try:
                                if os.path.isdir( full_path ):
                                    items_info.append( f"{name}:DIR:0" )
                                else:
                                    size = ( os.path.getsize( full_path ) )
                                    items_info.append( f"{name}:FILE:{size}" )
                            except Exception:
                                continue
                                
                        response = ( "OK|" + ",".join( items_info ) )
                        self.ws_client.send( response )
                    except Exception as e:
                        self.ws_client.send( f"ERROR|{str(e)}" )
                        
                # =================================================
                # READ
                # =================================================
                elif cmd == "READ":
                    if len(parts) < 4:
                        self.ws_client.send( "ERROR|Invalid READ command" )
                        continue
                        
                    path = parts[1]
                    try:
                        offset = int( parts[2] )
                        length = int( parts[3] )
                    except ValueError:
                        self.ws_client.send( "ERROR|Invalid offset or length" )
                        continue
                        
                    try:
                        if not os.path.isfile(path):
                            self.ws_client.send( "ERROR|File not found" )
                            continue
                            
                        with open( path, "rb" ) as f:
                            f.seek( offset )
                            chunk = f.read( length )
                            
                        self.ws_client.send( "OK|BINARY_FOLLOWS" )
                        self.ws_client.send( chunk )
                    except Exception as e:
                        try:
                            self.ws_client.send( f"ERROR|{str(e)}" )
                        except Exception:
                            pass
                            
                # =================================================
                # MKDIR (Create Directory)
                # =================================================
                elif cmd == "MKDIR":
                    if len(parts) < 2:
                        self.ws_client.send( "ERROR|Invalid MKDIR command" )
                        continue
                    path = parts[1]
                    try:
                        os.makedirs( path, exist_ok=True )
                        self.ws_client.send( "OK|Created" )
                    except Exception as e:
                        self.ws_client.send( f"ERROR|{str(e)}" )
                        
                # =================================================
                # CREATE (Create Empty File)
                # =================================================
                elif cmd == "CREATE":
                    if len(parts) < 2:
                        self.ws_client.send( "ERROR|Invalid CREATE command" )
                        continue
                    path = parts[1]
                    try:
                        open( path, "ab" ).close()
                        self.ws_client.send( "OK|Created" )
                    except Exception as e:
                        self.ws_client.send( f"ERROR|{str(e)}" )

                # =================================================
                # WRITE (PC to Android file write)
                # =================================================
                elif cmd == "WRITE":
                    if len(parts) < 4:
                        self.ws_client.send( "ERROR|Invalid WRITE command" )
                        continue
                    path = parts[1]
                    try:
                        offset = int( parts[2] )
                        length = int( parts[3] )
                    except ValueError:
                        self.ws_client.send( "ERROR|Invalid offset or length" )
                        continue
                    
                    try:
                        # 1. Tell PC to send binary data
                        self.ws_client.send( "OK|READY" )
                        
                        # 2. Immediately wait for the binary chunk
                        chunk = self.ws_client.recv()
                        
                        if not isinstance( chunk, bytes ):
                            self.ws_client.send( "ERROR|Expected binary data" )
                            continue
                            
                        # 3. Write data to file without overwriting the whole file
                        mode = "r+b" if os.path.exists(path) else "wb"
                        with open( path, mode ) as f:
                            f.seek( offset )
                            f.write( chunk )
                            
                        # 4. Confirm write
                        self.ws_client.send( f"OK|{len(chunk)}" )
                        
                    except Exception as e:
                        self.ws_client.send( f"ERROR|{str(e)}" )
                        
                # =================================================
                # DELETE
                # =================================================
                elif cmd == "DELETE":
                    if len(parts) < 2:
                        self.ws_client.send( "ERROR|Invalid DELETE command" )
                        continue
                        
                    path = parts[1]
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree( path )
                        elif os.path.isfile(path):
                            os.remove( path )
                        else:
                            self.ws_client.send( "ERROR|File not found" )
                            continue
                            
                        self.ws_client.send( "OK|Deleted" )
                    except Exception as e:
                        self.ws_client.send( f"ERROR|{str(e)}" )
                        
                # =================================================
                # RENAME
                # =================================================
                elif cmd == "RENAME":
                    if len(parts) < 3:
                        self.ws_client.send( "ERROR|Invalid RENAME command" )
                        continue
                        
                    old_path = parts[1]
                    new_path = parts[2]
                    try:
                        os.rename( old_path, new_path )
                        self.ws_client.send( "OK|Renamed" )
                    except Exception as e:
                        self.ws_client.send( f"ERROR|{str(e)}" )
                        
                # =================================================
                # UNKNOWN COMMAND
                # =================================================
                else:
                    print( "CLIENT: Unknown command:", cmd )
                    self.ws_client.send( "ERROR|Unknown command" )
                    
        except Exception as e:
            import traceback
            print( "CLIENT: Connection error:", repr(e) )
            traceback.print_exc()
        finally:
            print( "CLIENT: Client loop finished" )
            self.release_background_locks()
            
            if self.ws_client:
                try:
                    self.ws_client.close()
                except Exception:
                    pass
                self.ws_client = None
                
            Clock.schedule_once( lambda dt: self.reset_buttons_after_disconnect(), 0 )

    # ========================================================
    # RESET BUTTONS
    # ========================================================
    def reset_buttons_after_disconnect(self):
        self.running = False
        self.start_disabled = False
        self.stop_disabled = True
        if ( self.status_text == "Connected! PC Controlled." ):
            self.status_text = ( "Status: disconnected" )

    # ========================================================
    # ANDROID RESUME
    # ========================================================
    def on_resume(self):
        if ANDROID:
            Clock.schedule_once( lambda dt: self.check_storage_permission(), 0.5 )

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    MainApp().run()
