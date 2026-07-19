import threading
import socket
import random
import os
import shutil
import time

import websocket

from kivy.config import Config
Config.set('graphics', 'resizable', '0')

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
        request_permissions,
        check_permission,
        Permission
    )

    from jnius import autoclass

    ANDROID = True

except Exception:

    ANDROID = False


# ============================================================
# WINDOW
# ============================================================

Window.clearcolor = (0.13, 0.20, 0.38, 1)


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
            # ID
            # ====================================================

            BoxLayout:

                orientation: "horizontal"

                size_hint_y: None

                height: dp(60)

                spacing: dp(10)


                Label:

                    text: "ID :"

                    color: (1, 0.84, 0.00, 1)

                    bold: True

                    font_size: '18sp'

                    size_hint_x: 0.35

                    halign: 'left'

                    valign: 'middle'

                    text_size: self.size


                TextInput:

                    id: etId

                    text: app.id_value

                    readonly: True

                    multiline: False

                    size_hint_x: 0.65

                    font_size: '21sp'

                    bold: True

                    halign: 'center'

                    padding:

                        [dp(10),

                        (self.height - self.line_height) / 2.0,

                        dp(10),

                        0]


            # ====================================================
            # PASSWORD
            # ====================================================

            BoxLayout:

                orientation: "horizontal"

                size_hint_y: None

                height: dp(60)

                spacing: dp(10)


                Label:

                    text: "Password :"

                    color: (1, 0.84, 0.00, 1)

                    bold: True

                    font_size: '18sp'

                    size_hint_x: 0.35

                    halign: 'left'

                    valign: 'middle'

                    text_size: self.size


                TextInput:

                    id: etPass

                    text: app.pass_value

                    readonly: True

                    multiline: False

                    size_hint_x: 0.65

                    font_size: '21sp'

                    bold: True

                    halign: 'center'

                    padding:

                        [dp(10),

                        (self.height - self.line_height) / 2.0,

                        dp(10),

                        0]


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

                    padding:

                        [dp(10),

                        (self.height - self.line_height) / 2.0,

                        dp(10),

                        0]


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

                    padding:

                        [dp(10),

                        (self.height - self.line_height) / 2.0,

                        dp(10),

                        0]


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

                    values:

                        ["80",

                        "443",

                        "5000",

                        "8888",

                        "9090"]

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

                padding:

                    [0,

                    dp(10),

                    0,

                    0]


                Button:

                    text: "START"

                    bold: True

                    font_size: '20sp'

                    color: (0, 0, 0, 1)

                    background_color: (0.4, 1, 0.4, 1)

                    disabled: app.start_disabled

                    on_release:

                        app.start_connection()


                Button:

                    text: "STOP"

                    bold: True

                    font_size: '20sp'

                    color: (0, 0, 0, 1)

                    background_color: (1.0, 0.23, 0.19, 1)

                    disabled: app.stop_disabled

                    on_release:

                        app.stop_connection()


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

    id_value = StringProperty("")

    pass_value = StringProperty("")

    local_ip = StringProperty("0.0.0.0")

    tunnel_link = StringProperty("")

    port_value = StringProperty("5000")

    status_text = StringProperty("Status: idle")

    running = BooleanProperty(False)

    start_disabled = BooleanProperty(False)

    stop_disabled = BooleanProperty(True)


    # ========================================================
    # INIT
    # ========================================================

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.stop_flag = threading.Event()

        self.ws_client = None

        self.permission_check_done = False


    # ========================================================
    # BUILD
    # ========================================================

    def build(self):

        Builder.load_string(KV)

        self.id_value = self.generate_6digit()

        self.pass_value = self.generate_6digit()

        self.local_ip = self.get_local_ipv4() or "0.0.0.0"

        self.status_text = "Checking storage permission..."

        # Android permission check
        if ANDROID:

            Clock.schedule_once(

                lambda dt:
                self.check_storage_permission(),

                1

            )

        else:

            self.status_text = "Status: idle"


        return RootWidget()


    # ========================================================
    # GENERATE ID/PASSWORD
    # ========================================================

    def generate_6digit(self):

        return str(random.randint(100000, 999999))


    # ========================================================
    # GET LOCAL IP
    # ========================================================

    def get_local_ipv4(self):

        try:

            s = socket.socket(

                socket.AF_INET,

                socket.SOCK_DGRAM

            )

            s.connect(

                ("8.8.8.8", 80)

            )

            ip = s.getsockname()[0]

            s.close()

            return ip

        except Exception:

            return None


    # ========================================================
    # ANDROID VERSION
    # ========================================================

    def get_android_sdk(self):

        if not ANDROID:

            return 0

        try:

            Build = autoclass(

                'android.os.Build$VERSION'

            )

            return int(

                Build.SDK_INT

            )

        except Exception:

            return 0


    # ========================================================
    # STORAGE PERMISSION CHECK
    # Android 7 to Android 15
    # ========================================================

    def check_storage_permission(self):

        if not ANDROID:

            self.status_text = "Status: idle"

            return True


        sdk = self.get_android_sdk()


        # ====================================================
        # Android 11+ (API 30 to 35)
        # MANAGE_EXTERNAL_STORAGE
        # ====================================================

        if sdk >= 30:

            try:

                Environment = autoclass(

                    'android.os.Environment'

                )


                if Environment.isExternalStorageManager():

                    self.permission_check_done = True

                    self.status_text = (

                        "Storage Permission: GRANTED"

                    )

                    return True


                else:

                    self.permission_check_done = False

                    self.status_text = (

                        "Allow All Files Access in Settings"

                    )


                    Clock.schedule_once(

                        lambda dt:

                        self.open_all_files_settings(),

                        0.5

                    )


                    return False


            except Exception as e:

                self.status_text = (

                    "Storage Permission Error"

                )

                print(

                    "Storage permission error:",

                    e

                )

                return False


        # ====================================================
        # Android 7 to Android 10
        # API 24 to 29
        # ====================================================

        else:

            try:

                permissions = []


                # READ permission

                if not check_permission(

                    Permission.READ_EXTERNAL_STORAGE

                ):

                    permissions.append(

                        Permission.READ_EXTERNAL_STORAGE

                    )


                # WRITE permission

                if not check_permission(

                    Permission.WRITE_EXTERNAL_STORAGE

                ):

                    permissions.append(

                        Permission.WRITE_EXTERNAL_STORAGE

                    )


                if permissions:

                    request_permissions(

                        permissions,

                        self.permission_callback

                    )

                    self.status_text = (

                        "Requesting Storage Permission..."

                    )

                    return False


                else:

                    self.permission_check_done = True

                    self.status_text = (

                        "Storage Permission: GRANTED"

                    )

                    return True


            except Exception as e:

                print(

                    "Legacy permission error:",

                    e

                )

                self.status_text = (

                    "Storage Permission Error"

                )

                return False


    # ========================================================
    # LEGACY PERMISSION CALLBACK
    # ========================================================

    def permission_callback(

        self,

        permissions,

        grants

    ):

        all_granted = all(

            grants

        )


        if all_granted:

            self.permission_check_done = True

            self.status_text = (

                "Storage Permission: GRANTED"

            )

        else:

            self.permission_check_done = False

            self.status_text = (

                "Storage Permission: DENIED"

            )


    # ========================================================
    # OPEN ALL FILES ACCESS SETTINGS
    # Android 11+
    # ========================================================

    def open_all_files_settings(self):

        if not ANDROID:

            return


        try:

            PythonActivity = autoclass(

                'org.kivy.android.PythonActivity'

            )

            Intent = autoclass(

                'android.content.Intent'

            )

            Settings = autoclass(

                'android.provider.Settings'

            )

            Uri = autoclass(

                'android.net.Uri'

            )


            package_name = (

                PythonActivity

                .mActivity

                .getPackageName()

            )


            intent = Intent(

                Settings

                .ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION

            )


            intent.setData(

                Uri.parse(

                    "package:" +

                    package_name

                )

            )


            PythonActivity.mActivity.startActivity(

                intent

            )


            # Settingsમાંથી પાછા આવ્યા પછી ફરી check
            Clock.schedule_once(

                lambda dt:

                self.check_storage_permission(),

                2

            )


        except Exception as e:

            print(

                "All Files Settings error:",

                e

            )


            # Fallback: General All Files settings

            try:

                PythonActivity = autoclass(

                    'org.kivy.android.PythonActivity'

                )

                Intent = autoclass(

                    'android.content.Intent'

                )

                Settings = autoclass(

                    'android.provider.Settings'

                )


                intent = Intent(

                    Settings

                    .ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION

                )


                PythonActivity.mActivity.startActivity(

                    intent

                )


            except Exception as e2:

                print(

                    "Fallback settings error:",

                    e2

                )


    # ========================================================
    # START CONNECTION
    # ========================================================

    def start_connection(self):

        if self.running:

            return


        # Storage permission check
        if ANDROID and not self.permission_check_done:

            if not self.check_storage_permission():

                return


        expected_id = self.root.ids.etId.text.strip()

        expected_pass = self.root.ids.etPass.text.strip()

        tunnel_url = self.root.ids.etTunnel.text.strip()


        # ====================================================
        # TUNNEL URL
        # ====================================================

        if tunnel_url:

            ws_url = tunnel_url.strip()


            if ws_url.startswith("https://"):

                ws_url = (

                    "wss://" +

                    ws_url[8:]

                )


            elif ws_url.startswith("http://"):

                ws_url = (

                    "ws://" +

                    ws_url[7:]

                )


            elif not ws_url.startswith(

                ("ws://", "wss://")

            ):

                ws_url = (

                    "wss://" +

                    ws_url

                )


        # ====================================================
        # LOCAL IP
        # ====================================================

        else:

            host = self.root.ids.etIp.text.strip()

            if not host:

                host = "127.0.0.1"


            port = self.root.ids.etPort.text.strip()


            if not port:

                port = "5000"


            ws_url = (

                f"ws://{host}:{port}"

            )


        # ====================================================
        # LOCK BUTTONS
        # ====================================================

        self.running = True

        self.start_disabled = True

        self.stop_disabled = False

        self.stop_flag.clear()


        self.status_text = (

            f"Connecting to {ws_url}..."

        )


        threading.Thread(

            target=self.client_loop,

            args=(

                ws_url,

                expected_id,

                expected_pass

            ),

            daemon=True

        ).start()


    # ========================================================
    # STOP CONNECTION
    # ========================================================

    def stop_connection(self):

        if not self.running:

            return


        self.stop_flag.set()


        self.running = False

        self.start_disabled = False

        self.stop_disabled = True


        self.status_text = (

            "Status: stopped"

        )


        if self.ws_client:

            try:

                self.ws_client.close()

            except Exception:

                pass


            self.ws_client = None


        # New credentials
        self.id_value = self.generate_6digit()

        self.pass_value = self.generate_6digit()


        if self.root:

            self.root.ids.etId.text = self.id_value

            self.root.ids.etPass.text = self.pass_value


    # ========================================================
    # SET STATUS
    # ========================================================

    def _set_status(self, text):

        self.status_text = text


    # ========================================================
    # CONNECTION FAILED
    # ========================================================

    def connection_failed(self):

        self.running = False

        self.start_disabled = False

        self.stop_disabled = True

        self.status_text = (

            "Error: Connection Failed"

        )


    # ========================================================
    # CLIENT LOOP
    # ========================================================

    def client_loop(

        self,

        ws_url,

        expected_id,

        expected_pass

    ):

        try:

            # =================================================
            # CONNECT
            # =================================================

            self.ws_client = websocket.WebSocket()

            self.ws_client.settimeout(

                15.0

            )

            self.ws_client.connect(

                ws_url

            )

            self.ws_client.settimeout(

                None

            )


            Clock.schedule_once(

                lambda dt:

                self._set_status(

                    "Connected! Waiting for Auth..."

                ),

                0

            )


            # =================================================
            # AUTH
            # =================================================

            auth_msg = self.ws_client.recv()


            if isinstance(

                auth_msg,

                bytes

            ):

                auth_msg = auth_msg.decode(

                    "utf-8"

                )


            expected_auth = (

                f"AUTH|{expected_id}|{expected_pass}"

            )


            if auth_msg.strip() == expected_auth:


                self.ws_client.send(

                    "OK|ACCESS_GRANTED"

                )


                Clock.schedule_once(

                    lambda dt:

                    self._set_status(

                        "Auth Success! PC Controlled."

                    ),

                    0

                )


            else:


                try:

                    self.ws_client.send(

                        "DENY|INVALID_CREDENTIALS"

                    )

                except Exception:

                    pass


                try:

                    self.ws_client.close()

                except Exception:

                    pass


                Clock.schedule_once(

                    lambda dt:

                    self.connection_failed(),

                    0

                )

                return


            # =================================================
            # COMMAND LOOP
            # =================================================

            while not self.stop_flag.is_set():


                data = self.ws_client.recv()


                if not data:

                    break


                if isinstance(

                    data,

                    bytes

                ):

                    data = data.decode(

                        "utf-8"

                    )


                parts = data.strip().split("|")


                cmd = parts[0].upper()


                try:


                    # =========================================
                    # LS
                    # =========================================

                    if cmd == "LS":


                        if len(parts) < 2:

                            self.ws_client.send(

                                "ERROR|Invalid LS command"

                            )

                            continue


                        path = parts[1]


                        if os.path.isdir(path):


                            items_info = []


                            for name in os.listdir(path):


                                full_path = os.path.join(

                                    path,

                                    name

                                )


                                if os.path.isdir(

                                    full_path

                                ):

                                    items_info.append(

                                        f"{name}:DIR:0"

                                    )


                                else:


                                    try:

                                        size = os.path.getsize(

                                            full_path

                                        )

                                    except Exception:

                                        size = 0


                                    items_info.append(

                                        f"{name}:FILE:{size}"

                                    )


                            self.ws_client.send(

                                "OK|" +

                                ",".join(

                                    items_info

                                )

                            )


                        else:

                            self.ws_client.send(

                                "ERROR|Folder not found"

                            )


                    # =========================================
                    # READ
                    # =========================================

                    elif cmd == "READ":


                        if len(parts) < 4:

                            self.ws_client.send(

                                "ERROR|Invalid READ command"

                            )

                            continue


                        path = parts[1]

                        offset = int(

                            parts[2]

                        )

                        length = int(

                            parts[3]

                        )


                        if os.path.isfile(path):


                            with open(

                                path,

                                "rb"

                            ) as f:


                                f.seek(

                                    offset

                                )


                                chunk = f.read(

                                    length

                                )


                            self.ws_client.send(

                                "OK|BINARY_FOLLOWS"

                            )


                            self.ws_client.send(

                                chunk

                            )


                        else:

                            self.ws_client.send(

                                "ERROR|File not found"

                            )


                    # =========================================
                    # DELETE
                    # =========================================

                    elif cmd == "DELETE":


                        path = parts[1]


                        if os.path.isdir(path):

                            shutil.rmtree(

                                path

                            )

                        else:

                            os.remove(

                                path

                            )


                        self.ws_client.send(

                            "OK|Deleted"

                        )


                    # =========================================
                    # RENAME
                    # =========================================

                    elif cmd == "RENAME":


                        if len(parts) < 3:

                            self.ws_client.send(

                                "ERROR|Invalid RENAME command"

                            )

                            continue


                        old_path = parts[1]

                        new_path = parts[2]


                        os.rename(

                            old_path,

                            new_path

                        )


                        self.ws_client.send(

                            "OK|Renamed"

                        )


                    # =========================================
                    # UNKNOWN
                    # =========================================

                    else:

                        self.ws_client.send(

                            "ERROR|Unknown command"

                        )


                except Exception as e:


                    try:

                        self.ws_client.send(

                            f"ERROR|{str(e)}"

                        )

                    except Exception:

                        pass


        except Exception as e:


            print(

                "Connection error:",

                e

            )


            Clock.schedule_once(

                lambda dt:

                self.connection_failed(),

                0

            )


        finally:


            self.running = False


            if self.ws_client:

                try:

                    self.ws_client.close()

                except Exception:

                    pass


                self.ws_client = None


            Clock.schedule_once(

                lambda dt:

                self.reset_buttons_after_disconnect(),

                0

            )


    # ========================================================
    # RESET BUTTONS
    # ========================================================

    def reset_buttons_after_disconnect(self):

        self.running = False

        self.start_disabled = False

        self.stop_disabled = True


        if (

            self.status_text

            == "Auth Success! PC Controlled."

        ):

            self.status_text = (

                "Status: disconnected"

            )


    # ========================================================
    # ANDROID RESUME
    # ========================================================

    def on_resume(self):

        if ANDROID:

            Clock.schedule_once(

                lambda dt:

                self.check_storage_permission(),

                0.5

            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    MainApp().run()
