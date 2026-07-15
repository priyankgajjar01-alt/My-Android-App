import math
import traceback
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy.utils import get_color_from_hex, platform

# બેકગ્રાઉન્ડ કલર
Window.clearcolor = get_color_from_hex('#0a0f1a')

# એન્ડ્રોઇડમાં કીબોર્ડ ખુલે ત્યારે UI ઉપર જાય તે માટે 
Window.softinput_mode = "below_target"

if platform not in ('android', 'ios'):
    Window.size = (450, 800)

# --- રિઝલ્ટ ટેબલ માટેના નવા પાયથોન ક્લાસ ---
class ResultHeaderCell(BoxLayout):
    lbl_text = StringProperty('')

class ResultLabelCell(BoxLayout):
    lbl_text = StringProperty('')

class ResultDataCell(BoxLayout):
    lbl_top = StringProperty('')
    lbl_bot = StringProperty('')
# -----------------------------------------------------------------

KV = """
#:import utils kivy.utils

<HeaderLabel@Label>:
    font_size: '14sp'
    bold: True
    color: utils.get_color_from_hex('#00ddff')
    size_hint_y: None
    height: '35dp'
    text_size: self.size
    halign: 'left'
    valign: 'middle'

<SectionTitle@Label>:
    font_size: '11sp'
    bold: True
    color: utils.get_color_from_hex('#ffdd00')
    size_hint_y: None
    height: '25dp'
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    padding_x: '5dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#001a33')
        Rectangle:
            pos: self.pos
            size: self.size

<InputRow@BoxLayout>:
    size_hint_y: None
    height: '28dp'
    spacing: '5dp'
    lbl_text: ''
    unit_text: 'D.M'
    txt_id: ''
    
    Label:
        text: root.lbl_text
        font_size: '11sp'
        color: utils.get_color_from_hex('#aaaaaa')
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        size_hint_x: 0.4
    BoxLayout:
        canvas.before:
            Color:
                rgba: utils.get_color_from_hex('#1a2333')
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: utils.get_color_from_hex('#2a3a50')
            Line:
                rectangle: self.x, self.y, self.width, self.height
                width: 1
        size_hint_x: 0.6
        TextInput:
            id: inner_input
            background_color: 0,0,0,0
            foreground_color: 1,1,1,1
            cursor_color: 1,1,1,1
            multiline: False
            font_size: '13sp'
            font_name: 'RobotoMono-Regular'
            halign: 'left'
            padding_y: [self.height / 2.0 - (self.line_height / 2.0), 0]
            on_text_validate: app.focus_next(self)
        Label:
            text: root.unit_text
            font_size: '10sp'
            color: utils.get_color_from_hex('#00ddff')
            size_hint_x: None
            width: '35dp'

<ResultHeaderCell>:
    size_hint_y: None
    height: '30dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#121926')
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: root.lbl_text
        font_size: '11sp'
        bold: True
        color: utils.get_color_from_hex('#00ddff')

<ResultLabelCell>:
    size_hint_y: None
    height: '40dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#121926')
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: root.lbl_text
        font_size: '10sp'
        bold: True
        color: utils.get_color_from_hex('#ffdd00')
        text_size: self.size
        halign: 'center'
        valign: 'middle'

<ResultDataCell>:
    orientation: 'vertical'
    size_hint_y: None
    height: '40dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#121926')
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: root.lbl_top
        font_size: '12sp'
        bold: True
        color: utils.get_color_from_hex('#ffdd00')
    Label:
        text: root.lbl_bot
        font_size: '10sp'
        bold: True
        color: utils.get_color_from_hex('#888888')

BoxLayout:
    orientation: 'vertical'
    
    # HEADER
    BoxLayout:
        size_hint_y: None
        height: '45dp'
        padding: ['10dp', '0dp']
        canvas.before:
            Color:
                rgba: utils.get_color_from_hex('#001a33')
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "Alignment Calculator"
            font_size: '18sp'
            bold: True
            color: utils.get_color_from_hex('#00ddff')
            text_size: self.size
            halign: 'left'
            valign: 'middle'

    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: '10dp'
            spacing: '10dp'

            # CARD 1: INPUT SPECIFICATIONS
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: '5dp'
                spacing: '5dp'
                canvas.before:
                    Color:
                        rgba: utils.get_color_from_hex('#121926')
                    Rectangle:
                        pos: self.pos
                        size: self.size
                    Color:
                        rgba: utils.get_color_from_hex('#00ddff')
                    Line:
                        rectangle: self.x, self.y, self.width, self.height
                        width: 1

                HeaderLabel:
                    text: " 1. INPUT SPECIFICATIONS "
                
                # Rim Size
                BoxLayout:
                    size_hint_y: None
                    height: '30dp'
                    Label:
                        text: "Rim Size (Inch)"
                        font_size: '11sp'
                        color: utils.get_color_from_hex('#ffdd00')
                        text_size: self.size
                        halign: 'left'
                        valign: 'middle'
                        size_hint_x: 0.4
                    TextInput:
                        id: inp_common_rim
                        size_hint_x: 0.6
                        background_color: utils.get_color_from_hex('#1b2a47')
                        foreground_color: 1,1,1,1
                        multiline: False
                        font_size: '13sp'
                        on_text_validate: app.focus_next(self)
                
                # Tab Bar
                BoxLayout:
                    size_hint_y: None
                    height: '35dp'
                    spacing: 1
                    canvas.before:
                        Color:
                            rgba: utils.get_color_from_hex('#0a101c')
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    ToggleButton:
                        text: "DM"
                        group: 'tabs'
                        state: 'down'
                        background_normal: ''
                        background_down: ''
                        background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#0a101c')
                        color: (0,0,0,1) if self.state == 'down' else (0.6,0.6,0.6,1)
                        bold: True if self.state == 'down' else False
                        on_state: if self.state == 'down': sm.current = 'tab1'
                    ToggleButton:
                        text: "Decimal"
                        group: 'tabs'
                        background_normal: ''
                        background_down: ''
                        background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#0a101c')
                        color: (0,0,0,1) if self.state == 'down' else (0.6,0.6,0.6,1)
                        bold: True if self.state == 'down' else False
                        on_state: if self.state == 'down': sm.current = 'tab2'
                    ToggleButton:
                        text: "Std±Tol"
                        group: 'tabs'
                        background_normal: ''
                        background_down: ''
                        background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#0a101c')
                        color: (0,0,0,1) if self.state == 'down' else (0.6,0.6,0.6,1)
                        bold: True if self.state == 'down' else False
                        on_state: if self.state == 'down': sm.current = 'tab3'

                # Screen Manager for Tabs
                ScreenManager:
                    id: sm
                    size_hint_y: None
                    height: tab1_box.minimum_height if self.current == 'tab1' else (tab2_box.minimum_height if self.current == 'tab2' else tab3_box.minimum_height)

                    # TAB 1: DM
                    Screen:
                        name: 'tab1'
                        BoxLayout:
                            id: tab1_box
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: '8dp'
                            
                            BoxLayout:
                                orientation: 'vertical'
                                size_hint_y: None
                                height: self.minimum_height
                                padding: '3dp'
                                spacing: '3dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#2a3a50')
                                    Line:
                                        rectangle: self.x, self.y, self.width, self.height
                                        width: 1
                                SectionTitle:
                                    text: " FRONT WHEEL"
                                BoxLayout:
                                    size_hint_y: None
                                    height: '25dp'
                                    CheckBox:
                                        group: 't1_f_toe'
                                        active: True
                                        size_hint_x: None
                                        width: '30dp'
                                        on_active: app.t1_f_toe_type = 'DM' if self.active else 'MM'
                                    Label:
                                        text: 'D.M'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                    CheckBox:
                                        group: 't1_f_toe'
                                        size_hint_x: None
                                        width: '30dp'
                                    Label:
                                        text: 'mm'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                InputRow:
                                    id: t1_fToeMin
                                    lbl_text: "Toe Min *"
                                    unit_text: 'D.M' if app.t1_f_toe_type == 'DM' else 'mm'
                                InputRow:
                                    id: t1_fToeMax
                                    lbl_text: "Toe Max *"
                                    unit_text: 'D.M' if app.t1_f_toe_type == 'DM' else 'mm'
                                InputRow:
                                    id: t1_fCamMin
                                    lbl_text: "Camber Min *"
                                InputRow:
                                    id: t1_fCamMax
                                    lbl_text: "Camber Max *"
                                InputRow:
                                    id: t1_fCasMin
                                    lbl_text: "Castor Min *"
                                InputRow:
                                    id: t1_fCasMax
                                    lbl_text: "Castor Max *"

                            BoxLayout:
                                orientation: 'vertical'
                                size_hint_y: None
                                height: self.minimum_height
                                padding: '3dp'
                                spacing: '3dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#2a3a50')
                                    Line:
                                        rectangle: self.x, self.y, self.width, self.height
                                        width: 1
                                SectionTitle:
                                    text: " REAR WHEEL (OPTIONAL)"
                                BoxLayout:
                                    size_hint_y: None
                                    height: '25dp'
                                    CheckBox:
                                        group: 't1_r_toe'
                                        active: True
                                        size_hint_x: None
                                        width: '30dp'
                                        on_active: app.t1_r_toe_type = 'DM' if self.active else 'MM'
                                    Label:
                                        text: 'D.M'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                    CheckBox:
                                        group: 't1_r_toe'
                                        size_hint_x: None
                                        width: '30dp'
                                    Label:
                                        text: 'mm'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                InputRow:
                                    id: t1_rToeMin
                                    lbl_text: "Toe Min"
                                    unit_text: 'D.M' if app.t1_r_toe_type == 'DM' else 'mm'
                                InputRow:
                                    id: t1_rToeMax
                                    lbl_text: "Toe Max"
                                    unit_text: 'D.M' if app.t1_r_toe_type == 'DM' else 'mm'
                                InputRow:
                                    id: t1_rCamMin
                                    lbl_text: "Camber Min"
                                InputRow:
                                    id: t1_rCamMax
                                    lbl_text: "Camber Max"

                    # TAB 2: Decimal
                    Screen:
                        name: 'tab2'
                        BoxLayout:
                            id: tab2_box
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: '8dp'
                            
                            BoxLayout:
                                orientation: 'vertical'
                                size_hint_y: None
                                height: self.minimum_height
                                padding: '3dp'
                                spacing: '3dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#2a3a50')
                                    Line:
                                        rectangle: self.x, self.y, self.width, self.height
                                        width: 1
                                SectionTitle:
                                    text: " FRONT WHEEL"
                                BoxLayout:
                                    size_hint_y: None
                                    height: '25dp'
                                    CheckBox:
                                        group: 't2_f_toe'
                                        active: True
                                        size_hint_x: None
                                        width: '30dp'
                                        on_active: app.t2_f_toe_type = 'DD' if self.active else 'MM'
                                    Label:
                                        text: 'Degree (°)'
                                        size_hint_x: None
                                        width: '70dp'
                                        font_size: '11sp'
                                    CheckBox:
                                        group: 't2_f_toe'
                                        size_hint_x: None
                                        width: '30dp'
                                    Label:
                                        text: 'mm'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                InputRow:
                                    id: t2_fToeMin
                                    lbl_text: "Toe Min *"
                                    unit_text: '°' if app.t2_f_toe_type == 'DD' else 'mm'
                                InputRow:
                                    id: t2_fToeMax
                                    lbl_text: "Toe Max *"
                                    unit_text: '°' if app.t2_f_toe_type == 'DD' else 'mm'
                                InputRow:
                                    id: t2_fCamMin
                                    lbl_text: "Camber Min *"
                                    unit_text: '°'
                                InputRow:
                                    id: t2_fCamMax
                                    lbl_text: "Camber Max *"
                                    unit_text: '°'
                                InputRow:
                                    id: t2_fCasMin
                                    lbl_text: "Castor Min *"
                                    unit_text: '°'
                                InputRow:
                                    id: t2_fCasMax
                                    lbl_text: "Castor Max *"
                                    unit_text: '°'

                            BoxLayout:
                                orientation: 'vertical'
                                size_hint_y: None
                                height: self.minimum_height
                                padding: '3dp'
                                spacing: '3dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#2a3a50')
                                    Line:
                                        rectangle: self.x, self.y, self.width, self.height
                                        width: 1
                                SectionTitle:
                                    text: " REAR WHEEL (OPTIONAL)"
                                BoxLayout:
                                    size_hint_y: None
                                    height: '25dp'
                                    CheckBox:
                                        group: 't2_r_toe'
                                        active: True
                                        size_hint_x: None
                                        width: '30dp'
                                        on_active: app.t2_r_toe_type = 'DD' if self.active else 'MM'
                                    Label:
                                        text: 'Degree (°)'
                                        size_hint_x: None
                                        width: '70dp'
                                        font_size: '11sp'
                                    CheckBox:
                                        group: 't2_r_toe'
                                        size_hint_x: None
                                        width: '30dp'
                                    Label:
                                        text: 'mm'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                InputRow:
                                    id: t2_rToeMin
                                    lbl_text: "Toe Min"
                                    unit_text: '°' if app.t2_r_toe_type == 'DD' else 'mm'
                                InputRow:
                                    id: t2_rToeMax
                                    lbl_text: "Toe Max"
                                    unit_text: '°' if app.t2_r_toe_type == 'DD' else 'mm'
                                InputRow:
                                    id: t2_rCamMin
                                    lbl_text: "Camber Min"
                                    unit_text: '°'
                                InputRow:
                                    id: t2_rCamMax
                                    lbl_text: "Camber Max"
                                    unit_text: '°'

                    # TAB 3: Std±Tol
                    Screen:
                        name: 'tab3'
                        BoxLayout:
                            id: tab3_box
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: '8dp'
                            BoxLayout:
                                size_hint_y: None
                                height: '30dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#111c30')
                                    Rectangle:
                                        pos: self.pos
                                        size: self.size
                                ToggleButton:
                                    text: "DM Std ± Tol"
                                    group: 't3_sub'
                                    state: 'down'
                                    background_normal: ''
                                    background_down: ''
                                    background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#111c30')
                                    color: (0,0,0,1) if self.state == 'down' else utils.get_color_from_hex('#ffdd00')
                                    bold: True if self.state == 'down' else False
                                    on_state: if self.state == 'down': app.t3_sub_mode = 'DM'
                                ToggleButton:
                                    text: "Decimal Std ± Tol"
                                    group: 't3_sub'
                                    background_normal: ''
                                    background_down: ''
                                    background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#111c30')
                                    color: (0,0,0,1) if self.state == 'down' else utils.get_color_from_hex('#ffdd00')
                                    bold: True if self.state == 'down' else False
                                    on_state: if self.state == 'down': app.t3_sub_mode = 'DD'
                            
                            BoxLayout:
                                orientation: 'vertical'
                                size_hint_y: None
                                height: self.minimum_height
                                padding: '3dp'
                                spacing: '3dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#2a3a50')
                                    Line:
                                        rectangle: self.x, self.y, self.width, self.height
                                        width: 1
                                SectionTitle:
                                    text: " FRONT WHEEL - STD/TOL"
                                BoxLayout:
                                    size_hint_y: None
                                    height: '25dp'
                                    CheckBox:
                                        group: 't3_f_toe'
                                        active: True
                                        size_hint_x: None
                                        width: '30dp'
                                        on_active: app.t3_f_toe_type = 'DEG' if self.active else 'MM'
                                    Label:
                                        text: 'Degree'
                                        size_hint_x: None
                                        width: '50dp'
                                        font_size: '11sp'
                                    CheckBox:
                                        group: 't3_f_toe'
                                        size_hint_x: None
                                        width: '30dp'
                                    Label:
                                        text: 'mm'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                InputRow:
                                    id: t3_fToeStd
                                    lbl_text: "Toe Std *"
                                    unit_text: 'Val' if app.t3_f_toe_type == 'DEG' else 'mm'
                                InputRow:
                                    id: t3_fToeTol
                                    lbl_text: "Toe Tol *"
                                    unit_text: 'Tol' if app.t3_f_toe_type == 'DEG' else 'mm'
                                InputRow:
                                    id: t3_fCamStd
                                    lbl_text: "Camber Std *"
                                    unit_text: 'Val'
                                InputRow:
                                    id: t3_fCamTol
                                    lbl_text: "Camber Tol *"
                                    unit_text: 'Tol'
                                InputRow:
                                    id: t3_fCasStd
                                    lbl_text: "Castor Std *"
                                    unit_text: 'Val'
                                InputRow:
                                    id: t3_fCasTol
                                    lbl_text: "Castor Tol *"
                                    unit_text: 'Tol'

                            BoxLayout:
                                orientation: 'vertical'
                                size_hint_y: None
                                height: self.minimum_height
                                padding: '3dp'
                                spacing: '3dp'
                                canvas.before:
                                    Color:
                                        rgba: utils.get_color_from_hex('#2a3a50')
                                    Line:
                                        rectangle: self.x, self.y, self.width, self.height
                                        width: 1
                                SectionTitle:
                                    text: " REAR WHEEL (OPTIONAL)"
                                BoxLayout:
                                    size_hint_y: None
                                    height: '25dp'
                                    CheckBox:
                                        group: 't3_r_toe'
                                        active: True
                                        size_hint_x: None
                                        width: '30dp'
                                        on_active: app.t3_r_toe_type = 'DEG' if self.active else 'MM'
                                    Label:
                                        text: 'Degree'
                                        size_hint_x: None
                                        width: '50dp'
                                        font_size: '11sp'
                                    CheckBox:
                                        group: 't3_r_toe'
                                        size_hint_x: None
                                        width: '30dp'
                                    Label:
                                        text: 'mm'
                                        size_hint_x: None
                                        width: '30dp'
                                        font_size: '11sp'
                                InputRow:
                                    id: t3_rToeStd
                                    lbl_text: "Toe Std"
                                    unit_text: 'Val' if app.t3_r_toe_type == 'DEG' else 'mm'
                                InputRow:
                                    id: t3_rToeTol
                                    lbl_text: "Toe Tol"
                                    unit_text: 'Tol' if app.t3_r_toe_type == 'DEG' else 'mm'
                                InputRow:
                                    id: t3_rCamStd
                                    lbl_text: "Camber Std"
                                    unit_text: 'Val'
                                InputRow:
                                    id: t3_rCamTol
                                    lbl_text: "Camber Tol"
                                    unit_text: 'Tol'

                Button:
                    text: "CALCULATE"
                    font_size: '14sp'
                    bold: True
                    size_hint_y: None
                    height: '40dp'
                    background_normal: ''
                    background_color: utils.get_color_from_hex('#0055aa')
                    on_release: app.calculate_results()

            # CARD 2: RESULTS
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: '5dp'
                spacing: '5dp'
                canvas.before:
                    Color:
                        rgba: utils.get_color_from_hex('#121926')
                    Rectangle:
                        pos: self.pos
                        size: self.size
                    Color:
                        rgba: utils.get_color_from_hex('#00ddff')
                    Line:
                        rectangle: self.x, self.y, self.width, self.height
                        width: 1

                HeaderLabel:
                    text: " 2. CALCULATION RESULTS "
                
                BoxLayout:
                    id: results_container
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: 1
                    canvas.before:
                        Color:
                            rgba: utils.get_color_from_hex('#1a2333')
                        Rectangle:
                            pos: self.pos
                            size: self.size
"""

class AlignmentApp(App):
    t1_f_toe_type = StringProperty('DM')
    t1_r_toe_type = StringProperty('DM')
    t2_f_toe_type = StringProperty('DD')
    t2_r_toe_type = StringProperty('DD')
    t3_sub_mode = StringProperty('DM')
    t3_f_toe_type = StringProperty('DEG')
    t3_r_toe_type = StringProperty('DEG')

    def build(self):
        root = Builder.load_string(KV)
        self.show_placeholder(root.ids.results_container)
        return root

    def get_all_textinputs(self, parent):
        inputs = []
        if not parent: return inputs
        for child in reversed(parent.children):
            if isinstance(child, TextInput):
                inputs.append(child)
            else:
                inputs.extend(self.get_all_textinputs(child))
        return inputs

    def focus_next(self, current_input):
        rim_input = self.root.ids.inp_common_rim
        active_tab = self.root.ids.sm.current_screen
        all_inputs = [rim_input] + self.get_all_textinputs(active_tab)
        
        try:
            idx = all_inputs.index(current_input)
            if idx + 1 < len(all_inputs):
                all_inputs[idx + 1].focus = True
            else:
                self.calculate_results()
        except ValueError:
            pass

    def show_placeholder(self, container, text_msg="Click 'CALCULATE' to see results.", color_hex='#888888'):
        container.clear_widgets()
        container.add_widget(Label(
            text=text_msg,
            font_size='12sp',
            italic=True,
            bold=True if color_hex != '#888888' else False,
            color=get_color_from_hex(color_hex),
            size_hint_y=None, height='40dp'
        ))

    def write_table_header(self, container):
        grid = GridLayout(cols=4, size_hint_y=None, height='30dp', spacing=1)
        headers = ["Param", "Min", "Max", "Std ± Tol"]
        for text in headers:
            grid.add_widget(ResultHeaderCell(lbl_text=text))
        container.add_widget(grid)

    def write_table_row(self, container, label, std, tol, min_val, max_val):
        if min_val == "-" or min_val is None: return

        grid = GridLayout(cols=4, size_hint_y=None, height='40dp', spacing=1)
        
        grid.add_widget(ResultLabelCell(lbl_text=label))
        
        grid.add_widget(ResultDataCell(
            lbl_top=self.dd_to_dm_str(min_val), 
            lbl_bot=f"({min_val:.2f}°)" if min_val != "-" else "-"
        ))
        
        grid.add_widget(ResultDataCell(
            lbl_top=self.dd_to_dm_str(max_val), 
            lbl_bot=f"({max_val:.2f}°)" if max_val != "-" else "-"
        ))
        
        dm_std = self.dd_to_dm_str(std)
        dm_tol = self.dd_to_dm_str(tol)
        grid.add_widget(ResultDataCell(
            lbl_top=f"{dm_std} ± {dm_tol}", 
            lbl_bot=f"({std:.2f}°±{tol:.2f}°)"
        ))
        
        container.add_widget(grid)

    def dm_to_dd(self, val_str):
        if not val_str or str(val_str).strip() == "": return None
        try:
            num = float(val_str)
            sign = -1.0 if num < 0 or math.copysign(1.0, num) < 0 else 1.0
            abs_v = abs(num)
            deg = math.floor(abs_v)
            m = (abs_v - deg) * 100.0
            return sign * (deg + m/60.0)
        except: return None

    def mm_to_dd(self, mm_val, rim_inch):
        if not mm_val or not rim_inch or rim_inch <= 0: return 0.0
        try:
            r_mm = rim_inch * 25.4
            return math.asin(float(mm_val) / r_mm) * (180.0 / math.pi)
        except: return 0.0

    def dd_to_dm_str(self, dd_val):
        if dd_val == "-" or dd_val is None or isinstance(dd_val, str): return "-"
        neg = dd_val < 0 or math.copysign(1.0, dd_val) < 0
        abs_v = abs(dd_val)
        d = math.floor(abs_v)
        m = round((abs_v - d) * 60.0)
        if m >= 60: 
            d += 1
            m = 0
        return f"{'-' if neg else ''}{d}°{m:02d}'"

    def safe_float(self, s):
        try: return float(s) if str(s).strip()!="" else None
        except: return None

    def get_val(self, id_name):
        return self.root.ids[id_name].ids.inner_input.text

    def calculate_results(self):
        common_rim = self.safe_float(self.root.ids.inp_common_rim.text)
        current_tab = self.root.ids.sm.current
        container = self.root.ids.results_container
        
        # --- 1. Rim Size ની Compulsory ચકાસણી (Validation) ---
        is_mm_selected = False
        if current_tab == 'tab1' and (self.t1_f_toe_type == 'MM' or self.t1_r_toe_type == 'MM'):
            is_mm_selected = True
        elif current_tab == 'tab2' and (self.t2_f_toe_type == 'MM' or self.t2_r_toe_type == 'MM'):
            is_mm_selected = True
        elif current_tab == 'tab3' and (self.t3_f_toe_type == 'MM' or self.t3_r_toe_type == 'MM'):
            is_mm_selected = True
            
        if is_mm_selected and (common_rim is None or common_rim <= 0):
            self.show_placeholder(container, "Please enter ream size to calculate", color_hex='#ff3333')
            return # ગણતરી અટકાવી દો 
        # --------------------------------------------------------

        fToeMin, fToeMax, fToeStd, fToeTol = "-", "-", "-", "-"
        fCamMin, fCamMax, fCamStd, fCamTol = "-", "-", "-", "-"
        fCasMin, fCasMax, fCasStd, fCasTol = "-", "-", "-", "-"
        rToeMin, rToeMax, rToeStd, rToeTol = "-", "-", "-", "-"
        rCamMin, rCamMax, rCamStd, rCamTol = "-", "-", "-", "-"

        try:
            if current_tab == 'tab1':
                t_min, t_max = self.get_val('t1_fToeMin'), self.get_val('t1_fToeMax')
                fToeMin = self.mm_to_dd(t_min, common_rim) if self.t1_f_toe_type=="MM" else self.dm_to_dd(t_min)
                fToeMax = self.mm_to_dd(t_max, common_rim) if self.t1_f_toe_type=="MM" else self.dm_to_dd(t_max)
                if fToeMin is not None and fToeMax is not None:
                    fToeStd = (fToeMax + fToeMin)/2; fToeTol = abs(fToeMax - fToeMin)/2
                
                c_min, c_max = self.get_val('t1_fCamMin'), self.get_val('t1_fCamMax')
                fCamMin = self.dm_to_dd(c_min); fCamMax = self.dm_to_dd(c_max)
                if fCamMin is not None and fCamMax is not None:
                    fCamStd = (fCamMax+fCamMin)/2; fCamTol = abs(fCamMax-fCamMin)/2
                
                ca_min, ca_max = self.get_val('t1_fCasMin'), self.get_val('t1_fCasMax')
                fCasMin = self.dm_to_dd(ca_min); fCasMax = self.dm_to_dd(ca_max)
                if fCasMin is not None and fCasMax is not None:
                    fCasStd = (fCasMax+fCasMin)/2; fCasTol = abs(fCasMax-fCasMin)/2

                rt_min, rt_max = self.get_val('t1_rToeMin'), self.get_val('t1_rToeMax')
                if rt_min and rt_max:
                    rToeMin = self.mm_to_dd(rt_min, common_rim) if self.t1_r_toe_type=="MM" else self.dm_to_dd(rt_min)
                    rToeMax = self.mm_to_dd(rt_max, common_rim) if self.t1_r_toe_type=="MM" else self.dm_to_dd(rt_max)
                    rToeStd = (rToeMax+rToeMin)/2; rToeTol = abs(rToeMax-rToeMin)/2
                    
                rc_min, rc_max = self.get_val('t1_rCamMin'), self.get_val('t1_rCamMax')
                if rc_min and rc_max:
                    rCamMin = self.dm_to_dd(rc_min); rCamMax = self.dm_to_dd(rc_max)
                    rCamStd = (rCamMax+rCamMin)/2; rCamTol = abs(rCamMax-rCamMin)/2

            elif current_tab == 'tab2':
                t_min, t_max = self.safe_float(self.get_val('t2_fToeMin')), self.safe_float(self.get_val('t2_fToeMax'))
                fToeMin = self.mm_to_dd(t_min, common_rim) if self.t2_f_toe_type=="MM" else t_min
                fToeMax = self.mm_to_dd(t_max, common_rim) if self.t2_f_toe_type=="MM" else t_max
                if fToeMin is not None and fToeMax is not None:
                    fToeStd = (fToeMax+fToeMin)/2; fToeTol = abs(fToeMax-fToeMin)/2
                
                fCamMin = self.safe_float(self.get_val('t2_fCamMin')); fCamMax = self.safe_float(self.get_val('t2_fCamMax'))
                if fCamMin is not None and fCamMax is not None:
                    fCamStd = (fCamMax+fCamMin)/2; fCamTol = abs(fCamMax-fCamMin)/2
                
                fCasMin = self.safe_float(self.get_val('t2_fCasMin')); fCasMax = self.safe_float(self.get_val('t2_fCasMax'))
                if fCasMin is not None and fCasMax is not None:
                    fCasStd = (fCasMax+fCasMin)/2; fCasTol = abs(fCasMax-fCasMin)/2

                rt_min, rt_max = self.safe_float(self.get_val('t2_rToeMin')), self.safe_float(self.get_val('t2_rToeMax'))
                if rt_min is not None and rt_max is not None:
                    rToeMin = self.mm_to_dd(rt_min, common_rim) if self.t2_r_toe_type=="MM" else rt_min
                    rToeMax = self.mm_to_dd(rt_max, common_rim) if self.t2_r_toe_type=="MM" else rt_max
                    rToeStd = (rToeMax+rToeMin)/2; rToeTol = abs(rToeMax-rToeMin)/2
                    
                rc_min, rc_max = self.safe_float(self.get_val('t2_rCamMin')), self.safe_float(self.get_val('t2_rCamMax'))
                if rc_min is not None and rc_max is not None:
                    rCamMin = rc_min; rCamMax = rc_max; rCamStd = (rc_max+rc_min)/2; rCamTol = abs(rc_max-rc_min)/2

            elif current_tab == 'tab3':
                std_raw, tol_raw = self.get_val('t3_fToeStd'), self.get_val('t3_fToeTol')
                if self.t3_sub_mode == "DM":
                    fToeStd = self.mm_to_dd(std_raw, common_rim) if self.t3_f_toe_type=="MM" else self.dm_to_dd(std_raw)
                    fToeTol = self.mm_to_dd(tol_raw, common_rim) if self.t3_f_toe_type=="MM" else abs(self.dm_to_dd(tol_raw) or 0)
                    fCamStd = self.dm_to_dd(self.get_val('t3_fCamStd')); fCamTol = abs(self.dm_to_dd(self.get_val('t3_fCamTol')) or 0)
                    fCasStd = self.dm_to_dd(self.get_val('t3_fCasStd')); fCasTol = abs(self.dm_to_dd(self.get_val('t3_fCasTol')) or 0)
                else:
                    fToeStd = self.mm_to_dd(std_raw, common_rim) if self.t3_f_toe_type=="MM" else self.safe_float(std_raw)
                    fToeTol = self.mm_to_dd(tol_raw, common_rim) if self.t3_f_toe_type=="MM" else abs(self.safe_float(tol_raw) or 0)
                    fCamStd = self.safe_float(self.get_val('t3_fCamStd')); fCamTol = abs(self.safe_float(self.get_val('t3_fCamTol')) or 0)
                    fCasStd = self.safe_float(self.get_val('t3_fCasStd')); fCasTol = abs(self.safe_float(self.get_val('t3_fCasTol')) or 0)
                
                if fToeStd is not None and fToeTol is not None:
                    fToeMin = fToeStd - fToeTol; fToeMax = fToeStd + fToeTol
                if fCamStd is not None and fCamTol is not None:
                    fCamMin = fCamStd - fCamTol; fCamMax = fCamStd + fCamTol
                if fCasStd is not None and fCasTol is not None:
                    fCasMin = fCasStd - fCasTol; fCasMax = fCasStd + fCasTol

                r_std, r_tol = self.get_val('t3_rToeStd'), self.get_val('t3_rToeTol')
                if r_std and r_tol:
                    if self.t3_sub_mode == "DM":
                        rToeStd = self.mm_to_dd(r_std, common_rim) if self.t3_r_toe_type=="MM" else self.dm_to_dd(r_std)
                        rToeTol = self.mm_to_dd(r_tol, common_rim) if self.t3_r_toe_type=="MM" else abs(self.dm_to_dd(r_tol) or 0)
                    else:
                        rToeStd = self.mm_to_dd(r_std, common_rim) if self.t3_r_toe_type=="MM" else self.safe_float(r_std)
                        rToeTol = self.mm_to_dd(r_tol, common_rim) if self.t3_r_toe_type=="MM" else abs(self.safe_float(r_tol) or 0)
                    if rToeStd is not None and rToeTol is not None:
                        rToeMin = rToeStd - rToeTol; rToeMax = rToeStd + rToeTol

                rc_std, rc_tol = self.get_val('t3_rCamStd'), self.get_val('t3_rCamTol')
                if rc_std and rc_tol:
                    rCamStd = self.dm_to_dd(rc_std) if self.t3_sub_mode=="DM" else self.safe_float(rc_std)
                    rCamTol = abs(self.dm_to_dd(rc_tol) or 0) if self.t3_sub_mode=="DM" else abs(self.safe_float(rc_tol) or 0)
                    if rCamStd is not None and rCamTol is not None:
                        rCamMin = rCamStd - rCamTol; rCamMax = rCamStd + rCamTol

            container.clear_widgets()
            self.write_table_header(container)

            row_added = False
            if fToeMin != "-" and fToeMin is not None: 
                self.write_table_row(container, "Front Toe", fToeStd, fToeTol, fToeMin, fToeMax); row_added = True
            if fCamMin != "-" and fCamMin is not None: 
                self.write_table_row(container, "Front Camber", fCamStd, fCamTol, fCamMin, fCamMax); row_added = True
            if fCasMin != "-" and fCasMin is not None: 
                self.write_table_row(container, "Front Castor", fCasStd, fCasTol, fCasMin, fCasMax); row_added = True
            if rToeMin != "-" and rToeMin is not None: 
                self.write_table_row(container, "Rear Toe", rToeStd, rToeTol, rToeMin, rToeMax); row_added = True
            if rCamMin != "-" and rCamMin is not None: 
                self.write_table_row(container, "Rear Camber", rCamStd, rCamTol, rCamMin, rCamMax); row_added = True

            if not row_added:
                self.show_placeholder(container, "કોઈ માહિતી દાખલ કરેલ નથી!")

        except Exception as e:
            container.clear_widgets()
            container.add_widget(Label(text=f"Error: ખોટી કિંમત!\n{str(e)}", color=(1,0,0,1), font_size='12sp'))
            print("Traceback:", traceback.format_exc())

if __name__ == "__main__":
    AlignmentApp().run()
