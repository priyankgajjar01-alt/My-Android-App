import os
import json
import threading
import time
import socket
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp

# JNI Check (Android mate)
is_real_android = False
if platform == 'android':
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        UUID = autoclass('java.util.UUID')
        InputStreamReader = autoclass('java.io.InputStreamReader')
        BufferedReader = autoclass('java.io.BufferedReader')
        JavaString = autoclass('java.lang.String')
        is_real_android = True
    except Exception as e:
        print("JNI Loading Error:", e)

# Dark Navy Background
Window.clearcolor = (10/255, 25/255, 47/255, 1)

KV = '''
<CustomTextInput@TextInput>:
    background_normal: ''
    background_color: [0.04, 0.1, 0.18, 1]
    foreground_color: [0.39, 1.0, 0.85, 1]
    cursor_color: [0.39, 1.0, 0.85, 1]
    multiline: False
    halign: 'center'
    font_size: '14sp'
    size_hint_y: None
    height: '34dp'
    padding_y: (self.height - self.line_height) / 2
    use_bubble: False
    use_handles: False

<RoundedButton@Button>:
    background_color: [0, 0, 0, 0]
    background_normal: ''
    bg_color: [0.39, 1.0, 0.85, 1]
    color: [0.04, 0.1, 0.18, 1]
    canvas.before:
        Color:
            rgba: self.bg_color if self.state == 'normal' else [self.bg_color[0]*0.8, self.bg_color[1]*0.8, self.bg_color[2]*0.8, 1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [18, 18, 18, 18]

# ===== FORCE UPDATE BUTTON (with glow) =====
<ForceButton@Button>:
    background_normal: ''
    background_color: [0, 0, 0, 0]
    bold: True
    font_size: '15sp'
    color: [0.04, 0.1, 0.18, 1] if self.state == 'down' else [0.39, 1.0, 0.85, 1]
    canvas.before:
        Color:
            rgba: [0.39, 1.0, 0.85, 0.35] if self.state == 'down' else [0, 0, 0, 0]
        RoundedRectangle:
            pos: self.x - 4, self.y - 4
            size: self.width + 8, self.height + 8
            radius: [28, 28, 28, 28]
        Color:
            rgba: [0.39, 1.0, 0.85, 1] if self.state == 'down' else [0.1, 0.2, 0.3, 1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [25, 25, 25, 25]
        Color:
            rgba: [0.39, 1.0, 0.85, 1]
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 25]
            width: 2

<StatusLabel@Label>:
    bg_color: [0.82, 0.18, 0.18, 1]
    selectable: False
    canvas.before:
        Color:
            rgba: self.bg_color
        Rectangle:
            pos: self.pos
            size: self.size

# ===== LOG VIEW CARD (Replaces Monitor Box with Rounded Card + ScrollView) =====
<LogCard>:
    orientation: 'vertical'
    padding: ['10dp', '6dp', '10dp', '6dp']
    spacing: '4dp'
    canvas.before:
        Color:
            rgba: [0.04, 0.09, 0.18, 0.95]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12, 12, 12, 12]
        Color:
            rgba: [0.25, 0.55, 0.85, 0.65]
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 12]
            width: 1.2

# ===== ANALOG SENSOR CARD (A0 / A1: Grey 0.0 Preview, Green Live Value & Green Unit) =====
<AnalogCard>:
    size_hint: 0.5, None
    height: '64dp'
    pin_title: 'A0'
    val_text: '0.0'
    unit_text: ''
    is_live: False
    canvas.before:
        Color:
            rgba: [0.05, 0.16, 0.28, 0.90]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12, 12, 12, 12]
        Color:
            rgba: [0.39, 0.86, 1.0, 0.75]
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 12]
            width: 1.2

    Label:
        text: root.pin_title
        color: [0.40, 0.86, 1.0, 1]
        font_size: '12sp'
        bold: True
        size_hint: None, None
        size: '34dp', '18dp'
        pos_hint: {'x': 0, 'top': 1}
        padding: ['8dp', '4dp', '0dp', '0dp']
        halign: 'left'
        valign: 'top'
        text_size: self.size
        selectable: False

    BoxLayout:
        orientation: 'horizontal'
        size_hint: 1, 1
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        padding: ['28dp', '0dp', '10dp', '0dp']
        spacing: '4dp'

        Label:
            text: root.val_text
            color: [0.25, 0.96, 0.55, 1] if root.is_live else [0.55, 0.60, 0.66, 1]
            font_size: max(dp(12), root.height - dp(10))
            bold: True
            size_hint: 1, 1
            halign: 'right'
            valign: 'middle'
            text_size: self.size
            shorten: True
            selectable: False

        Label:
            id: unit_lbl
            text: root.unit_text
            color: [0.25, 0.96, 0.55, 1]
            font_size: '16sp'
            bold: True
            size_hint_x: None
            width: (self.texture_size[0] + dp(4)) if root.unit_text else 0
            size_hint_y: 1
            text_size: None, None
            selectable: False

# ===== CONTROL CARD (20% Reduced Height, Card with Title + ON/OFF Switch Button) =====
<ControlCard>:
    orientation: 'vertical'
    spacing: '4dp'
    padding: ['6dp', '5dp', '6dp', '5dp']
    size_hint_y: None
    height: '62dp'
    card_name: 'S1'
    card_id: 1
    is_on: False
    canvas.before:
        Color:
            rgba: [0.08, 0.22, 0.24, 0.85] if root.is_on else [0.06, 0.13, 0.24, 0.85]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12, 12, 12, 12]
        Color:
            rgba: [0.25, 0.95, 0.65, 0.85] if root.is_on else [0.25, 0.50, 0.80, 0.45]
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 12]
            width: 1.2

    Label:
        text: root.card_name
        color: [0.39, 1.0, 0.85, 1]
        font_size: '14sp'
        bold: True
        size_hint_y: None
        height: '18dp'
        halign: 'center'
        valign: 'middle'
        text_size: self.size
        shorten: True
        selectable: False

    Button:
        text: 'ON' if root.is_on else 'OFF'
        background_normal: ''
        background_color: [0, 0, 0, 0]
        color: [0.04, 0.1, 0.18, 1] if root.is_on else [0.88, 0.94, 1.0, 1]
        bold: True
        font_size: '13sp'
        size_hint_y: 1
        on_release: app.toggle_card(root.card_id)
        canvas.before:
            Color:
                rgba: [0.15, 0.82, 0.45, 1] if root.is_on else [0.14, 0.28, 0.48, 0.95]
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [9, 9, 9, 9]

# ===== DATA FORMAT POPUP =====
<DataFormatPopup>:
    title: 'Data Format & Logic'
    title_color: [0.39, 1.0, 0.85, 1]
    title_size: '18sp'
    separator_color: [0.39, 1.0, 0.85, 1]
    background_color: [0.11, 0.14, 0.18, 1]
    size_hint: 0.9, 0.8
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '10dp'

        ScrollView:
            bar_width: '5dp'
            do_scroll_x: False
            Label:
                text: 'TX Format:\\n    <on_delay,off_delay,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13,s14,s15,force>\\\\n\\nExample:\\n    <1000,1000,1,0,0,1,0,0,1,0,0,0,0,0,0,1,0,0>\\\\n\\nRX Format:\\n    <A0,val>\\\\n and <A1,val>\\\\n\\nRules:\\n    - Switch ON = 1, OFF = 0 (S1 to S15)\\n    - Force Update sends force=1, then sends force=0 right after OK/DONE\\n    - Packets hold until OK or DONE reply arrives\\n    - When OK or DONE arrives, latest held packet is sent'
                color: [0.8, 0.84, 0.96, 1]
                font_size: '12sp'
                halign: 'left'
                valign: 'top'
                text_size: self.width, None
                size_hint_y: None
                height: self.texture_size[1] + dp(12)
                selectable: False

        Button:
            text: 'Close'
            background_color: [0.8, 0.2, 0.2, 1]
            background_normal: ''
            color: [1, 1, 1, 1]
            bold: True
            size_hint_y: None
            height: '45dp'
            on_release: root.dismiss()

# ===== CONTROLLER SETTINGS POPUP =====
<SettingsPopup>:
    title: ''
    separator_height: 0
    background_color: [0.11, 0.14, 0.18, 1]
    size_hint: 0.95, 0.95
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: '12dp'
        spacing: '6dp'

        Label:
            text: 'Controller Settings'
            color: [0.39, 1.0, 0.85, 1]
            bold: True
            font_size: '18sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            size_hint_y: None
            height: '26dp'
            selectable: False

        Widget:
            size_hint_y: None
            height: '2dp'
            canvas:
                Color:
                    rgba: [0.39, 1.0, 0.85, 1]
                Rectangle:
                    pos: self.pos
                    size: self.size

        ScrollView:
            bar_width: '4dp'
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                spacing: '8dp'
                size_hint_y: None
                height: self.minimum_height

                GridLayout:
                    cols: 2
                    spacing: '6dp'
                    row_default_height: '34dp'
                    row_force_default: True
                    size_hint_y: None
                    height: '114dp'

                    Label:
                        text: 'MAC Address (Editable)'
                        color: [0.7, 0.8, 0.9, 1]
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        selectable: False
                    CustomTextInput:
                        text: app.hc05_mac
                        on_text: app.hc05_mac = self.text

                    Label:
                        text: 'ON Delay (ms)'
                        color: [0.7, 0.8, 0.9, 1]
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        selectable: False
                    CustomTextInput:
                        text: app.on_delay
                        on_text: app.on_delay = self.text

                    Label:
                        text: 'OFF Delay (ms)'
                        color: [0.7, 0.8, 0.9, 1]
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        selectable: False
                    CustomTextInput:
                        text: app.off_delay
                        on_text: app.off_delay = self.text

                Label:
                    text: 'A0 & A1 Sensor Units'
                    color: [0.40, 0.86, 1.0, 1]
                    bold: True
                    font_size: '14sp'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_y: None
                    height: '20dp'
                    selectable: False

                GridLayout:
                    cols: 2
                    spacing: '6dp'
                    row_default_height: '34dp'
                    row_force_default: True
                    size_hint_y: None
                    height: '74dp'

                    Label:
                        text: 'A0 Unit (e.g. V, C, %)'
                        color: [0.7, 0.8, 0.9, 1]
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        selectable: False
                    CustomTextInput:
                        id: a0_unit_input
                        hint_text: 'Unit'
                        on_text: app.on_unit_input_change('A0', self.text)

                    Label:
                        text: 'A1 Unit (e.g. V, C, %)'
                        color: [0.7, 0.8, 0.9, 1]
                        halign: 'left'
                        valign: 'middle'
                        text_size: self.size
                        selectable: False
                    CustomTextInput:
                        id: a1_unit_input
                        hint_text: 'Unit'
                        on_text: app.on_unit_input_change('A1', self.text)

                Label:
                    text: 'Switch Names (S1 - S15)'
                    color: [0.39, 1.0, 0.85, 1]
                    bold: True
                    font_size: '14sp'
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                    size_hint_y: None
                    height: '20dp'
                    selectable: False

                GridLayout:
                    cols: 3
                    spacing: '6dp'
                    row_default_height: '34dp'
                    row_force_default: True
                    size_hint_y: None
                    height: '194dp'

                    CustomTextInput:
                        hint_text: 'S1'
                        text: app.s1_name
                        on_text: app.s1_name = self.text
                    CustomTextInput:
                        hint_text: 'S2'
                        text: app.s2_name
                        on_text: app.s2_name = self.text
                    CustomTextInput:
                        hint_text: 'S3'
                        text: app.s3_name
                        on_text: app.s3_name = self.text
                    CustomTextInput:
                        hint_text: 'S4'
                        text: app.s4_name
                        on_text: app.s4_name = self.text
                    CustomTextInput:
                        hint_text: 'S5'
                        text: app.s5_name
                        on_text: app.s5_name = self.text
                    CustomTextInput:
                        hint_text: 'S6'
                        text: app.s6_name
                        on_text: app.s6_name = self.text
                    CustomTextInput:
                        hint_text: 'S7'
                        text: app.s7_name
                        on_text: app.s7_name = self.text
                    CustomTextInput:
                        hint_text: 'S8'
                        text: app.s8_name
                        on_text: app.s8_name = self.text
                    CustomTextInput:
                        hint_text: 'S9'
                        text: app.s9_name
                        on_text: app.s9_name = self.text
                    CustomTextInput:
                        hint_text: 'S10'
                        text: app.s10_name
                        on_text: app.s10_name = self.text
                    CustomTextInput:
                        hint_text: 'S11'
                        text: app.s11_name
                        on_text: app.s11_name = self.text
                    CustomTextInput:
                        hint_text: 'S12'
                        text: app.s12_name
                        on_text: app.s12_name = self.text
                    CustomTextInput:
                        hint_text: 'S13'
                        text: app.s13_name
                        on_text: app.s13_name = self.text
                    CustomTextInput:
                        hint_text: 'S14'
                        text: app.s14_name
                        on_text: app.s14_name = self.text
                    CustomTextInput:
                        hint_text: 'S15'
                        text: app.s15_name
                        on_text: app.s15_name = self.text

                Button:
                    text: 'View Data Format & Logic'
                    background_color: [0.1, 0.2, 0.3, 1]
                    background_normal: ''
                    color: [0.39, 1.0, 0.85, 1]
                    bold: True
                    font_size: '14sp'
                    size_hint_y: None
                    height: '38dp'
                    on_release: app.show_data_format_popup()

        ForceButton:
            text: 'Force Update Settings'
            size_hint_y: None
            height: '44dp'
            on_press: app.force_update_and_close()

        Button:
            text: 'Save & Close'
            background_color: [0.0, 0.78, 0.32, 1]
            background_normal: ''
            color: [0.04, 0.1, 0.18, 1]
            bold: True
            font_size: '16sp'
            size_hint_y: None
            height: '44dp'
            on_release: app.save_and_close_settings()

# ===== MAIN LAYOUT =====
BoxLayout:
    orientation: 'vertical'

    StatusLabel:
        id: status_lbl
        text: 'System Starting...'
        size_hint_y: None
        height: '52dp'
        bold: True
        font_size: '19sp'
        color: [1, 1, 1, 1]
        bg_color: [0.85, 0.53, 0.1, 1]
        on_touch_up: 
            if self.collide_point(*args[1].pos): app.reconnect_bluetooth()

    # Log View Card occupying monitor space with 10dp gap above A0/A1 row
    BoxLayout:
        size_hint_y: 1
        padding: ['10dp', '8dp', '10dp', '0dp']

        LogCard:
            Label:
                text: 'LOG VIEW'
                color: [0.40, 0.86, 1.0, 1]
                font_size: '11sp'
                bold: True
                size_hint_y: None
                height: '16dp'
                halign: 'left'
                valign: 'middle'
                text_size: self.size
                selectable: False

            ScrollView:
                id: log_scroll
                bar_width: '5dp'
                bar_color: [0.39, 1.0, 0.85, 0.85]
                bar_inactive_color: [0.39, 1.0, 0.85, 0.30]
                scroll_type: ['bars', 'content']
                do_scroll_x: False
                do_scroll_y: True

                BoxLayout:
                    id: log_container
                    orientation: 'vertical'
                    size_hint_x: 1
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '2dp'
                    padding: ['2dp', '2dp', '6dp', '2dp']

    # Centered Cards Block with 10dp gap above A0/A1 row
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        padding: ['10dp', '10dp', '10dp', '0dp']

        BoxLayout:
            orientation: 'vertical'
            spacing: '6dp'
            size_hint_y: None
            height: self.minimum_height

            # Row above S1: 2 Analog Sensor Cards (A0 & A1) fitted cleanly in 1 row
            BoxLayout:
                orientation: 'horizontal'
                spacing: '6dp'
                size_hint_y: None
                height: '64dp'

                AnalogCard:
                    id: card_a0
                    pin_title: 'A0'
                    val_text: app.a0_val if app.a0_val else '0.0'
                    unit_text: app.a0_unit
                    is_live: bool(app.a0_val)

                AnalogCard:
                    id: card_a1
                    pin_title: 'A1'
                    val_text: app.a1_val if app.a1_val else '0.0'
                    unit_text: app.a1_unit
                    is_live: bool(app.a1_val)

            # Main 3x4 Switch Grid (S1 - S12)
            GridLayout:
                cols: 3
                rows: 4
                spacing: '6dp'
                size_hint_y: None
                height: self.minimum_height

                ControlCard:
                    card_name: app.s1_name
                    card_id: 1
                    is_on: bool(app.s1_state)
                ControlCard:
                    card_name: app.s2_name
                    card_id: 2
                    is_on: bool(app.s2_state)
                ControlCard:
                    card_name: app.s3_name
                    card_id: 3
                    is_on: bool(app.s3_state)
                ControlCard:
                    card_name: app.s4_name
                    card_id: 4
                    is_on: bool(app.s4_state)
                ControlCard:
                    card_name: app.s5_name
                    card_id: 5
                    is_on: bool(app.s5_state)
                ControlCard:
                    card_name: app.s6_name
                    card_id: 6
                    is_on: bool(app.s6_state)
                ControlCard:
                    card_name: app.s7_name
                    card_id: 7
                    is_on: bool(app.s7_state)
                ControlCard:
                    card_name: app.s8_name
                    card_id: 8
                    is_on: bool(app.s8_state)
                ControlCard:
                    card_name: app.s9_name
                    card_id: 9
                    is_on: bool(app.s9_state)
                ControlCard:
                    card_name: app.s10_name
                    card_id: 10
                    is_on: bool(app.s10_state)
                ControlCard:
                    card_name: app.s11_name
                    card_id: 11
                    is_on: bool(app.s11_state)
                ControlCard:
                    card_name: app.s12_name
                    card_id: 12
                    is_on: bool(app.s12_state)

            # Last Row: 3 Switches (S13 - S15) included in TX format & Settings
            GridLayout:
                cols: 3
                rows: 1
                spacing: '6dp'
                size_hint_y: None
                height: self.minimum_height

                ControlCard:
                    card_name: app.s13_name
                    card_id: 13
                    is_on: bool(app.s13_state)
                ControlCard:
                    card_name: app.s14_name
                    card_id: 14
                    is_on: bool(app.s14_state)
                ControlCard:
                    card_name: app.s15_name
                    card_id: 15
                    is_on: bool(app.s15_state)

    # Settings button centered between last switch row and bottom Android bar
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: '76dp'
        padding: ['10dp', '0dp', '10dp', '14dp']

        Widget:
            size_hint_y: 1

        AnchorLayout:
            size_hint_y: None
            height: '42dp'
            anchor_x: 'center'
            anchor_y: 'center'
            RoundedButton:
                text: 'Settings'
                size_hint: None, None
                size: '140dp', '40dp'
                bg_color: [0.39, 1.0, 0.85, 1]
                bold: True
                font_size: '16sp'
                on_release: app.open_settings()

        Widget:
            size_hint_y: 1
'''


class LogCard(BoxLayout):
    pass


class AnalogCard(FloatLayout):
    pin_title = StringProperty('A0')
    val_text = StringProperty('0.0')
    unit_text = StringProperty('')
    is_live = BooleanProperty(False)


class ControlCard(BoxLayout):
    card_name = StringProperty('S1')
    card_id = NumericProperty(1)
    is_on = BooleanProperty(False)


class SettingsPopup(Popup):
    pass


class DataFormatPopup(Popup):
    pass


class BluetoothApp(App):
    ANALOG_UPDATE_INTERVAL = 0.25

    hc05_mac = StringProperty("98:D3:31:F4:XX:XX")
    on_delay = StringProperty("1000")
    off_delay = StringProperty("1000")

    a0_val = StringProperty("")
    a1_val = StringProperty("")
    a0_unit = StringProperty("")
    a1_unit = StringProperty("")

    s1_name = StringProperty("S1")
    s2_name = StringProperty("S2")
    s3_name = StringProperty("S3")
    s4_name = StringProperty("S4")
    s5_name = StringProperty("S5")
    s6_name = StringProperty("S6")
    s7_name = StringProperty("S7")
    s8_name = StringProperty("S8")
    s9_name = StringProperty("S9")
    s10_name = StringProperty("S10")
    s11_name = StringProperty("S11")
    s12_name = StringProperty("S12")
    s13_name = StringProperty("S13")
    s14_name = StringProperty("S14")
    s15_name = StringProperty("S15")

    s1_state = NumericProperty(0)
    s2_state = NumericProperty(0)
    s3_state = NumericProperty(0)
    s4_state = NumericProperty(0)
    s5_state = NumericProperty(0)
    s6_state = NumericProperty(0)
    s7_state = NumericProperty(0)
    s8_state = NumericProperty(0)
    s9_state = NumericProperty(0)
    s10_state = NumericProperty(0)
    s11_state = NumericProperty(0)
    s12_state = NumericProperty(0)
    s13_state = NumericProperty(0)
    s14_state = NumericProperty(0)
    s15_state = NumericProperty(0)

    force_state = NumericProperty(0)

    def build(self):
        self.bt_socket = None
        self.bt_out = None
        self.bt_in = None
        self.is_connected = False
        self.waiting_ack = False
        self.latest_held_packet = None
        self.is_connecting = False
        self._send_force_reset_on_ack = False
        self._tx_lock = threading.Lock()
        self._syncing_popup = False

        self._latest_analog_rx = {"A0": None, "A1": None}
        self._analog_last_ui_time = {"A0": 0.0, "A1": 0.0}
        self._analog_flush_events = {"A0": None, "A1": None}

        self.load_settings()
        self.root = Builder.load_string(KV)
        self.settings_popup = SettingsPopup()
        self.data_format_popup = DataFormatPopup()
        self._apply_units_to_cards()
        return self.root

    def _apply_units_to_cards(self):
        if not self.root:
            return
        if "card_a0" in self.root.ids:
            self.root.ids.card_a0.unit_text = self.a0_unit
        if "card_a1" in self.root.ids:
            self.root.ids.card_a1.unit_text = self.a1_unit

    def on_unit_input_change(self, pin, text):
        if self._syncing_popup:
            return
        clean = str(text).strip()
        if pin == "A0":
            self.a0_unit = clean
        elif pin == "A1":
            self.a1_unit = clean
        self._apply_units_to_cards()

    def _sync_units_from_popup(self):
        if not hasattr(self, "settings_popup") or not self.settings_popup:
            return
        ids = self.settings_popup.ids
        if "a0_unit_input" in ids:
            self.a0_unit = ids.a0_unit_input.text.strip()
        if "a1_unit_input" in ids:
            self.a1_unit = ids.a1_unit_input.text.strip()
        self._apply_units_to_cards()

    def on_start(self):
        self.log("System Ready...")
        self.log(f"Loaded MAC: {self.hc05_mac}")

        if is_real_android:
            try:
                from android.permissions import request_permissions
                request_permissions([
                    'android.permission.BLUETOOTH_CONNECT',
                    'android.permission.BLUETOOTH_SCAN',
                    'android.permission.ACCESS_FINE_LOCATION',
                    'android.permission.BLUETOOTH',
                    'android.permission.BLUETOOTH_ADMIN'
                ])
                self.update_status("Waiting for Permissions...", [0.85, 0.53, 0.1, 1])
                Clock.schedule_once(lambda dt: threading.Thread(target=self.connect_bluetooth, daemon=True).start(), 4)
            except Exception:
                Clock.schedule_once(lambda dt: threading.Thread(target=self.connect_bluetooth, daemon=True).start(), 1)
        else:
            Clock.schedule_once(lambda dt: threading.Thread(target=self.connect_bluetooth, daemon=True).start(), 1)

    def reconnect_bluetooth(self):
        if self.is_connected:
            self.log("Already connected. Ignoring reconnect request.")
            return
        if self.is_connecting:
            self.log("Reconnect already in progress...")
            return

        self.is_connecting = True
        self.log("Manual reconnect requested...")
        self.update_status("Reconnecting...", [0.85, 0.53, 0.1, 1])

        if self.bt_socket:
            try:
                self.bt_socket.close()
            except Exception:
                pass
            self.bt_socket = None
            self.bt_out = None
            self.bt_in = None

        with self._tx_lock:
            self.is_connected = False
            self.waiting_ack = False
            self.latest_held_packet = None
            self._send_force_reset_on_ack = False

        threading.Thread(target=self.connect_bluetooth, daemon=True).start()

    def load_settings(self):
        if os.path.exists("bt_settings.json"):
            try:
                with open("bt_settings.json", "r") as f:
                    data = json.load(f)
                    if "mac" in data:
                        self.hc05_mac = data["mac"]
                    if "on_delay" in data:
                        self.on_delay = data["on_delay"]
                    if "off_delay" in data:
                        self.off_delay = data["off_delay"]
                    if "a0_unit" in data:
                        self.a0_unit = str(data["a0_unit"]).strip()
                    if "a1_unit" in data:
                        self.a1_unit = str(data["a1_unit"]).strip()
                    for i in range(1, 16):
                        n_key = f"s{i}_name"
                        if n_key in data:
                            setattr(self, n_key, data[n_key])
                        s_key = f"s{i}_state"
                        if s_key in data:
                            setattr(self, s_key, 1 if int(data[s_key]) else 0)
            except Exception:
                pass

    def save_settings_to_file(self):
        self._sync_units_from_popup()
        data = {
            "mac": self.hc05_mac.strip(),
            "on_delay": self.on_delay,
            "off_delay": self.off_delay,
            "a0_unit": self.a0_unit.strip(),
            "a1_unit": self.a1_unit.strip(),
        }
        for i in range(1, 16):
            data[f"s{i}_name"] = getattr(self, f"s{i}_name")
            data[f"s{i}_state"] = int(getattr(self, f"s{i}_state"))

        try:
            with open("bt_settings.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def open_settings(self):
        self._syncing_popup = True
        ids = self.settings_popup.ids
        if "a0_unit_input" in ids:
            ids.a0_unit_input.text = self.a0_unit
        if "a1_unit_input" in ids:
            ids.a1_unit_input.text = self.a1_unit
        self._syncing_popup = False
        self.settings_popup.open()

    def show_data_format_popup(self):
        self.data_format_popup.open()

    def save_and_close_settings(self):
        with self._tx_lock:
            self._send_force_reset_on_ack = False
        self.force_state = 0
        self.save_settings_to_file()
        self.send_full_state()
        self.settings_popup.dismiss()

    def force_update_and_close(self):
        self.save_settings_to_file()
        self.force_state = 1
        with self._tx_lock:
            self._send_force_reset_on_ack = True
        self.log("Force Update (1) -> sending now; will send 0 right after OK/DONE")
        self.send_full_state()
        # Button state returns to 0 immediately; force=0 packet waits for OK/DONE
        self.force_state = 0
        try:
            self.settings_popup.dismiss()
        except Exception:
            pass

    @mainthread
    def log(self, msg):
        if not self.root or "log_container" not in self.root.ids:
            return
        log_scroll = self.root.ids.log_scroll
        container = self.root.ids.log_container
        was_at_bottom = (container.height <= log_scroll.height) or (log_scroll.scroll_y <= 0.15)

        lbl = Label(
            text=str(msg),
            color=[0.39, 1.0, 0.85, 1],
            font_size='12sp',
            halign='left',
            valign='top',
            size_hint_x=1,
            size_hint_y=None,
        )
        lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        lbl.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1] + dp(2)))
        container.add_widget(lbl)

        if len(container.children) > 200:
            container.remove_widget(container.children[-1])

        if was_at_bottom:
            Clock.schedule_once(lambda dt: setattr(log_scroll, 'scroll_y', 0), 0.05)

    @mainthread
    def update_status(self, text, bg_color):
        if not self.root or "status_lbl" not in self.root.ids:
            return
        self.root.ids.status_lbl.text = text
        self.root.ids.status_lbl.bg_color = bg_color

    def _commit_analog_ui(self, pin):
        """Render the latest stored RX value for A0/A1 onto the card."""
        self._analog_flush_events[pin] = None
        val = self._latest_analog_rx.get(pin)
        if val is None:
            return
        self._analog_last_ui_time[pin] = time.monotonic()
        if pin == "A0":
            self.a0_val = val
        elif pin == "A1":
            self.a1_val = val

    @mainthread
    def _queue_analog_rx(self, pin, val):
        """Store latest RX reading and update A0/A1 card at most once every 0.25s."""
        self._latest_analog_rx[pin] = val
        now = time.monotonic()
        elapsed = now - self._analog_last_ui_time[pin]

        if elapsed >= self.ANALOG_UPDATE_INTERVAL and self._analog_flush_events[pin] is None:
            self._commit_analog_ui(pin)
        elif self._analog_flush_events[pin] is None:
            rem = max(0.01, self.ANALOG_UPDATE_INTERVAL - elapsed)
            self._analog_flush_events[pin] = Clock.schedule_once(
                lambda dt, p=pin: self._commit_analog_ui(p),
                rem
            )

    def _parse_analog_packet(self, line):
        """Parse `<A0,val>` or `<A1,val>` (also accepts `A0,val` / `A1,val`) and queue 0.25s UI update."""
        s = str(line).strip()
        if s.startswith("<") and s.endswith(">"):
            s = s[1:-1].strip()
        if "," not in s:
            return False
        parts = s.split(",", 1)
        pin = parts[0].strip().upper()
        val = parts[1].strip()
        if pin in ("A0", "A1") and val != "":
            self._queue_analog_rx(pin, val)
            return True
        return False

    def connect_bluetooth(self):
        mac = self.hc05_mac.strip()
        self.log(f"Connecting to {mac}...")
        self.update_status("Connecting...", [0.85, 0.53, 0.1, 1])

        try:
            if is_real_android:
                adapter = BluetoothAdapter.getDefaultAdapter()
                device = adapter.getRemoteDevice(mac)
                spp_uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
                self.bt_socket = device.createRfcommSocketToServiceRecord(spp_uuid)
                adapter.cancelDiscovery()
                self.bt_socket.connect()
                self.bt_out = self.bt_socket.getOutputStream()
                self.bt_in = BufferedReader(InputStreamReader(self.bt_socket.getInputStream()))
                self.is_connected = True
            else:
                if hasattr(socket, 'AF_BLUETOOTH'):
                    self.bt_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                    self.bt_socket.connect((mac, 1))
                    self.is_connected = True
                else:
                    self.log("AF_BLUETOOTH missing. Simulated Mode.")

            if self.is_connected:
                threading.Thread(target=self.listen_for_ack, daemon=True).start()
                self.update_status("Connected via Bluetooth!", [0.0, 0.78, 0.32, 1])
                self.log("HC-05 Connected Successfully!")

        except Exception as e:
            self.is_connected = False
            self.update_status("Disconnected", [0.82, 0.18, 0.18, 1])
            self.log(f"Failed: {str(e)}")

        finally:
            self.is_connecting = False

    def _on_reply_received(self, recv_data):
        """Release reply lock on OK/DONE, then send held packet or force=0 reset packet."""
        self._parse_analog_packet(recv_data)

        upper = recv_data.upper()
        if "OK" not in upper and "DONE" not in upper:
            return

        held_to_send = None
        send_force_reset = False
        with self._tx_lock:
            self.waiting_ack = False
            if self.latest_held_packet is not None:
                held_to_send = self.latest_held_packet
                self.latest_held_packet = None
            elif self._send_force_reset_on_ack:
                self._send_force_reset_on_ack = False
                send_force_reset = True

        if held_to_send is not None:
            self.log(f"Reply received -> Sending latest held packet: {held_to_send}")
            self._transmit_packet(held_to_send)
        elif send_force_reset:
            reset_pkt = self.build_state_message(force_val=0)
            self.log(f"Reply received -> Sending force=0 packet: {reset_pkt}")
            self._transmit_packet(reset_pkt)

    def listen_for_ack(self):
        while self.is_connected and self.bt_socket:
            try:
                if is_real_android:
                    if self.bt_in.ready():
                        recv_data = self.bt_in.readLine()
                        if recv_data:
                            clean = recv_data.strip()
                            self.log(f"RCV: {clean}")
                            self._on_reply_received(clean)
                    else:
                        time.sleep(0.05)
                else:
                    recv_data = self.bt_socket.recv(1024).decode("utf-8").strip()
                    if recv_data:
                        self.log(f"RCV: {recv_data}")
                        self._on_reply_received(recv_data)
            except Exception:
                break

    def build_state_message(self, force_val=None):
        on_d = str(self.on_delay).strip() or "1000"
        off_d = str(self.off_delay).strip() or "1000"
        f_val = int(self.force_state) if force_val is None else int(force_val)
        parts = [on_d, off_d]
        for i in range(1, 16):
            parts.append(str(int(getattr(self, f"s{i}_state"))))
        parts.append(str(f_val))
        return "<" + ",".join(parts) + ">"

    def send_full_state(self, force_val=None):
        packet = self.build_state_message(force_val=force_val)
        self.send_data(packet)

    def _transmit_packet(self, packet):
        """Transmit `<...>\n` and set `waiting_ack = True` until `OK` or `DONE` arrives."""
        if self.is_connected and self.bt_socket:
            try:
                msg = packet + "\n"
                if is_real_android:
                    java_msg = JavaString(msg).getBytes()
                    self.bt_out.write(java_msg)
                    self.bt_out.flush()
                else:
                    self.bt_socket.send(msg.encode("utf-8"))

                with self._tx_lock:
                    self.waiting_ack = True
                self.log(f"SENT: {packet} (waiting OK/DONE)")
            except Exception:
                with self._tx_lock:
                    self.waiting_ack = False
                self.update_status("Disconnected", [0.82, 0.18, 0.18, 1])
                self.is_connected = False
        else:
            self.log(f"Simulated SENT: {packet}")

    def send_data(self, data):
        """Hold latest packet while waiting for OK/DONE; send immediately when free."""
        with self._tx_lock:
            if self.waiting_ack:
                self.latest_held_packet = data
                self.log(f"HELD (waiting OK/DONE): {data}")
                return
        self._transmit_packet(data)

    def toggle_card(self, card_id):
        if 1 <= card_id <= 15:
            prop = f"s{card_id}_state"
            new_val = 0 if int(getattr(self, prop)) else 1
            setattr(self, prop, new_val)
            self.save_settings_to_file()
        self.send_full_state()

    def on_stop(self):
        self.save_settings_to_file()
        for pin, ev in list(self._analog_flush_events.items()):
            if ev is not None:
                ev.cancel()
            self._analog_flush_events[pin] = None
        if self.root and "log_container" in self.root.ids:
            self.root.ids.log_container.clear_widgets()
        with self._tx_lock:
            self.latest_held_packet = None
            self.waiting_ack = False
            self._send_force_reset_on_ack = False
            self.is_connected = False
        for stream in (self.bt_in, self.bt_out, self.bt_socket):
            if stream:
                try:
                    stream.close()
                except Exception:
                    pass
        self.bt_in = None
        self.bt_out = None
        self.bt_socket = None


if __name__ == "__main__":
    try:
        BluetoothApp().run()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
