import math
import os
import json
import traceback
import threading
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.properties import StringProperty, DictProperty
from kivy.utils import get_color_from_hex, platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock, mainthread

# Background
Window.clearcolor = get_color_from_hex('#0a0f1a')
Window.softinput_mode = "below_target"

if platform not in ('android', 'ios'):
    Window.size = (380, 700)


# ==========================================
# CUSTOM WIDGETS
# ==========================================
class RoundedButton(Button):
    def __init__(self, bg_hex='#0055aa', radius=12, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.bg_hex = bg_hex
        self.radius = radius
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(rgba=get_color_from_hex('#64ffda80'))
            else:
                Color(rgba=get_color_from_hex(self.bg_hex))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])


class ExcelHeaderCell(BoxLayout):
    lbl_text = StringProperty('')

class ExcelParamCell(BoxLayout):
    lbl_text = StringProperty('')

class ExcelValueCell(BoxLayout):
    lbl_text = StringProperty('')


class ListItem(ButtonBehavior, BoxLayout):
    brand_model = StringProperty('')
    spec_data = DictProperty({})

    def on_release(self):
        App.get_running_app().open_spec_popup(self.spec_data)


class MainScreen(Screen):
    pass

class ListScreen(Screen):
    def on_pre_enter(self, *args):
        self.ids.search_bar.text = ''
        self.populate_list(App.get_running_app().db)

    def populate_list(self, data_list):
        container = self.ids.list_container
        container.clear_widgets()
        for spec in data_list:
            item = ListItem()
            item.brand_model = f"{spec.get('brand','-')}  |  {spec.get('model','-')}"
            item.spec_data = spec
            container.add_widget(item)

    def filter_list(self, query):
        db = App.get_running_app().db
        if not query:
            self.populate_list(db)
        else:
            q = query.lower()
            filtered = [s for s in db if q in s.get('brand','').lower() or q in s.get('model','').lower()]
            self.populate_list(filtered)


# ==========================================
# KV STRING
# ==========================================
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

<RoundedButton>:
    background_normal: ''
    background_down: ''
    background_color: 0,0,0,0
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#64ffda80') if self.state == 'down' else utils.get_color_from_hex(root.bg_hex)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [root.radius]

<StringInputRow@BoxLayout>:
    size_hint_y: None
    height: '30dp'
    spacing: '5dp'
    lbl_text: ''
    Label:
        text: root.lbl_text
        font_size: '11sp'
        color: utils.get_color_from_hex('#ffdd00')
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        size_hint_x: 0.4
    TextInput:
        id: inner_input
        size_hint_x: 0.6
        background_color: utils.get_color_from_hex('#1b2a47')
        foreground_color: 1,1,1,1
        multiline: False
        font_size: '13sp'
        padding_y: [self.height / 2.0 - (self.line_height / 2.0), 0]
        on_text_validate: app.focus_next(self)

<InputRow@BoxLayout>:
    size_hint_y: None
    height: '28dp'
    spacing: '5dp'
    lbl_text: ''
    unit_text: 'D.M'
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
            halign: 'left'
            padding_y: [self.height / 2.0 - (self.line_height / 2.0), 0]
            on_text_validate: app.focus_next(self)
        Label:
            text: root.unit_text
            font_size: '10sp'
            color: utils.get_color_from_hex('#00ddff')
            size_hint_x: None
            width: '35dp'

<ExcelHeaderCell>:
    size_hint_y: None
    height: '50dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#003366')
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: utils.get_color_from_hex('#00ddff')
        Line:
            rectangle: self.x, self.y, self.width, self.height
            width: 1
    Label:
        text: root.lbl_text
        font_size: '13.5sp'
        bold: True
        color: utils.get_color_from_hex('#00ddff')
        text_size: self.size
        halign: 'center'
        valign: 'middle'

<ExcelParamCell>:
    size_hint_y: None
    height: '65dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#0f1623')
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: utils.get_color_from_hex('#2a3a50')
        Line:
            rectangle: self.x, self.y, self.width, self.height
            width: 1
    Label:
        text: root.lbl_text
        font_size: '14sp'
        bold: True
        color: utils.get_color_from_hex('#ffdd00')
        text_size: self.size
        halign: 'center'
        valign: 'middle'
        markup: True

<ExcelValueCell>:
    size_hint_y: None
    height: '65dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#121926')
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: utils.get_color_from_hex('#2a3a50')
        Line:
            rectangle: self.x, self.y, self.width, self.height
            width: 1
    Label:
        text: root.lbl_text
        font_size: '16sp'
        bold: True
        color: utils.get_color_from_hex('#ffffff')
        text_size: self.size
        halign: 'center'
        valign: 'middle'
        markup: True

<ListItem>:
    size_hint_y: None
    height: '55dp'
    padding: '10dp'
    spacing: '10dp'
    canvas.before:
        Color:
            rgba: utils.get_color_from_hex('#64ffda40') if self.state == 'down' else utils.get_color_from_hex('#1a2333')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
        Color:
            rgba: utils.get_color_from_hex('#00ddff')
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 10]
            width: 1
    Label:
        text: root.brand_model
        font_size: '16sp'
        bold: True
        color: utils.get_color_from_hex('#ffffff')
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        shorten: True
        shorten_from: 'right'
    Label:
        text: 'TAP TO VIEW'
        size_hint_x: None
        width: '90dp'
        font_size: '11sp'
        bold: True
        color: utils.get_color_from_hex('#00ddff')

# IN-APP FILE CHOOSER POPUP
<FileChooserPopup@Popup>:
    title: '  Select Backup File (.json)'
    title_color: utils.get_color_from_hex('#00ddff')
    title_size: '16sp'
    size_hint: (0.95, 0.85)
    background: ''  
    background_color: utils.get_color_from_hex('#0a0f1a')
    separator_color: utils.get_color_from_hex('#00ddff')
    separator_height: '2dp'
    
    BoxLayout:
        orientation: 'vertical'
        spacing: '10dp'
        padding: '5dp'

        BoxLayout:
            size_hint_y: None
            height: '40dp'
            spacing: '10dp'
            RoundedButton:
                text: '📂 Downloads'
                font_size: '13sp'
                bold: True
                bg_hex: '#1b2a47'
                radius: 8
                color: 1,1,1,1
                on_release: filechooser.path = app.get_download_path()
            RoundedButton:
                text: '📁 WaDataBase'
                font_size: '13sp'
                bold: True
                bg_hex: '#1b2a47'
                radius: 8
                color: 1,1,1,1
                on_release: filechooser.path = app.get_current_path()

        BoxLayout:
            canvas.before:
                Color:
                    rgba: utils.get_color_from_hex('#121926')
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [10]
                Color:
                    rgba: utils.get_color_from_hex('#2a3a50')
                Line:
                    rounded_rectangle: [self.x, self.y, self.width, self.height, 10]
                    width: 1
            padding: '5dp'

            FileChooserListView:
                id: filechooser
                path: app.get_download_path()
                filters: ['*.json']

        BoxLayout:
            size_hint_y: None
            height: '45dp'
            spacing: '15dp'
            RoundedButton:
                text: 'CANCEL'
                bg_hex: '#d32f2f'
                radius: 8
                font_size: '14sp'
                bold: True
                color: 1,1,1,1
                on_release: root.dismiss()
            RoundedButton:
                text: 'LOAD THIS FILE'
                bg_hex: '#00aa55'
                radius: 8
                font_size: '14sp'
                bold: True
                color: 1,1,1,1
                on_release: 
                    if filechooser.selection: app.process_selected_file(filechooser.selection[0]); root.dismiss()

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        
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
                text: "Vehicle Spec Database"
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

                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: '8dp'
                    spacing: '8dp'
                    canvas.before:
                        Color:
                            rgba: utils.get_color_from_hex('#121926')
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [12]
                        Color:
                            rgba: utils.get_color_from_hex('#00ddff')
                        Line:
                            rounded_rectangle: [self.x, self.y, self.width, self.height, 12]
                            width: 1

                    HeaderLabel:
                        text: " 1. ADD NEW VEHICLE SPEC "
                    
                    StringInputRow:
                        id: inp_brand
                        lbl_text: "Brand *"
                    StringInputRow:
                        id: inp_model_name
                        lbl_text: "Model Name *"
                    StringInputRow:
                        id: inp_common_rim
                        lbl_text: "Rim Size (Inch)"
                    
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
                            on_release: sm.current = 'tab1'
                        ToggleButton:
                            text: "Decimal"
                            group: 'tabs'
                            background_normal: ''
                            background_down: ''
                            background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#0a101c')
                            color: (0,0,0,1) if self.state == 'down' else (0.6,0.6,0.6,1)
                            bold: True if self.state == 'down' else False
                            on_release: sm.current = 'tab2'
                        ToggleButton:
                            text: "Std±Tol"
                            group: 'tabs'
                            background_normal: ''
                            background_down: ''
                            background_color: utils.get_color_from_hex('#4CAF50') if self.state == 'down' else utils.get_color_from_hex('#0a101c')
                            color: (0,0,0,1) if self.state == 'down' else (0.6,0.6,0.6,1)
                            bold: True if self.state == 'down' else False
                            on_release: sm.current = 'tab3'

                    ScreenManager:
                        id: sm
                        size_hint_y: None
                        height: tab1_box.minimum_height if self.current == 'tab1' else (tab2_box.minimum_height if self.current == 'tab2' else tab3_box.minimum_height)

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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [8]
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
                                            on_active: if self.active: app.t1_f_toe_type = 'DM'
                                        Label:
                                            text: 'D.M'
                                            size_hint_x: None
                                            width: '30dp'
                                            font_size: '11sp'
                                        CheckBox:
                                            group: 't1_f_toe'
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t1_f_toe_type = 'MM'
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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [8]
                                    SectionTitle:
                                        text: " REAR WHEEL (OPT)"
                                    BoxLayout:
                                        size_hint_y: None
                                        height: '25dp'
                                        CheckBox:
                                            group: 't1_r_toe'
                                            active: True
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t1_r_toe_type = 'DM'
                                        Label:
                                            text: 'D.M'
                                            size_hint_x: None
                                            width: '30dp'
                                            font_size: '11sp'
                                        CheckBox:
                                            group: 't1_r_toe'
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t1_r_toe_type = 'MM'
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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [8]
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
                                            on_active: if self.active: app.t2_f_toe_type = 'DD'
                                        Label:
                                            text: 'Degree'
                                            size_hint_x: None
                                            width: '50dp'
                                            font_size: '11sp'
                                        CheckBox:
                                            group: 't2_f_toe'
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t2_f_toe_type = 'MM'
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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [8]
                                    SectionTitle:
                                        text: " REAR WHEEL (OPT)"
                                    BoxLayout:
                                        size_hint_y: None
                                        height: '25dp'
                                        CheckBox:
                                            group: 't2_r_toe'
                                            active: True
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t2_r_toe_type = 'DD'
                                        Label:
                                            text: 'Degree'
                                            size_hint_x: None
                                            width: '50dp'
                                            font_size: '11sp'
                                        CheckBox:
                                            group: 't2_r_toe'
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t2_r_toe_type = 'MM'
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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [6]
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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [8]
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
                                            on_active: if self.active: app.t3_f_toe_type = 'DEG'
                                        Label:
                                            text: 'Degree'
                                            size_hint_x: None
                                            width: '50dp'
                                            font_size: '11sp'
                                        CheckBox:
                                            group: 't3_f_toe'
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t3_f_toe_type = 'MM'
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
                                        RoundedRectangle:
                                            pos: self.pos
                                            size: self.size
                                            radius: [8]
                                    SectionTitle:
                                        text: " REAR WHEEL (OPT)"
                                    BoxLayout:
                                        size_hint_y: None
                                        height: '25dp'
                                        CheckBox:
                                            group: 't3_r_toe'
                                            active: True
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t3_r_toe_type = 'DEG'
                                        Label:
                                            text: 'Degree'
                                            size_hint_x: None
                                            width: '50dp'
                                            font_size: '11sp'
                                        CheckBox:
                                            group: 't3_r_toe'
                                            size_hint_x: None
                                            width: '30dp'
                                            on_active: if self.active: app.t3_r_toe_type = 'MM'
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

                    Label:
                        id: msg_label
                        text: ""
                        size_hint_y: None
                        height: '25dp'
                        color: utils.get_color_from_hex('#00ff88')
                        font_size: '12sp'
                        bold: True
                        
                RoundedButton:
                    text: "+ SAVE & ADD TO LIST"
                    font_size: '14sp'
                    bold: True
                    size_hint_y: None
                    height: '45dp'
                    bg_hex: '#00aa55'
                    radius: 14
                    color: 1,1,1,1
                    on_release: app.save_data()
                    
                RoundedButton:
                    text: "VIEW SPECIFICATIONS"
                    font_size: '14sp'
                    bold: True
                    size_hint_y: None
                    height: '45dp'
                    bg_hex: '#0055aa'
                    radius: 14
                    color: 1,1,1,1
                    on_release: app.root.current = 'list_screen'

<ListScreen>:
    name: 'list_screen'
    BoxLayout:
        orientation: 'vertical'
        
        BoxLayout:
            size_hint_y: None
            height: '50dp'
            padding: ['10dp', '5dp']
            spacing: '10dp'
            canvas.before:
                Color:
                    rgba: utils.get_color_from_hex('#001a33')
                Rectangle:
                    pos: self.pos
                    size: self.size
            RoundedButton:
                text: 'BACK'
                size_hint_x: 0.25
                font_size: '12sp'
                bold: True
                bg_hex: '#1e2a3a'
                radius: 10
                color: 1,1,1,1
                on_release: app.root.current = 'main'
            Label:
                text: "Saved Vehicles"
                font_size: '16sp'
                bold: True
                color: utils.get_color_from_hex('#00ddff')
                size_hint_x: 0.4
                halign: 'left'
                valign: 'middle'
                text_size: self.size
            RoundedButton:
                text: 'IMPORT FILE'
                size_hint_x: 0.35
                font_size: '12sp'
                bold: True
                bg_hex: '#d97706'
                radius: 10
                color: 1,1,1,1
                on_release: app.import_from_file()

        BoxLayout:
            size_hint_y: None
            height: '40dp'
            padding: '5dp'
            canvas.before:
                Color:
                    rgba: utils.get_color_from_hex('#0a0f1a')
                Rectangle:
                    pos: self.pos
                    size: self.size
            TextInput:
                id: search_bar
                hint_text: 'Search Brand or Model...'
                background_color: utils.get_color_from_hex('#1b2a47')
                foreground_color: 1,1,1,1
                multiline: False
                font_size: '14sp'
                on_text: root.filter_list(self.text)

        ScrollView:
            do_scroll_x: False
            GridLayout:
                id: list_container
                cols: 1
                spacing: '5dp'
                padding: '10dp'
                size_hint_y: None
                height: self.minimum_height
"""


class AlignmentApp(App):
    t1_f_toe_type = StringProperty('DM')
    t1_r_toe_type = StringProperty('DM')
    t2_f_toe_type = StringProperty('DD')
    t2_r_toe_type = StringProperty('DD')
    t3_f_toe_type = StringProperty('DEG')
    t3_r_toe_type = StringProperty('DEG')
    t3_sub_mode = StringProperty('DM')
    
    db = []
    editing_index = None
    progress_popup = None
    progress_bar = None
    progress_label = None
    progress_status = None

    def build(self):
        if platform == 'android':
            download_dir = '/storage/emulated/0/Download'
            app_folder = os.path.join(download_dir, 'WaDataBase')

            if not os.path.exists(app_folder):
                try:
                    os.makedirs(app_folder)
                except Exception as e:
                    print("Folder creation error:", e)

            self.db_path = os.path.join(app_folder, 'foc_specs_db.json')
        else:
            self.db_path = os.path.join(os.getcwd(), 'foc_specs_db.json')

        self.load_db()
        Builder.load_string(KV)
        
        sm = ScreenManager()
        sm.add_widget(MainScreen())
        sm.add_widget(ListScreen())
        return sm
        
    def on_start(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                Build = autoclass('android.os.Build$VERSION')
                
                if Build.SDK_INT >= 30:
                    Environment = autoclass('android.os.Environment')
                    if not Environment.isExternalStorageManager():
                        Intent = autoclass('android.content.Intent')
                        Settings = autoclass('android.provider.Settings')
                        Uri = autoclass('android.net.Uri')
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')

                        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                        uri = Uri.parse("package:" + PythonActivity.mActivity.getPackageName())
                        intent.setData(uri)
                        PythonActivity.mActivity.startActivity(intent)
                else:
                    from android.permissions import request_permissions, Permission
                    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
                    
            except Exception as e:
                print("Permission Request Error:", e)

    def get_download_path(self):
        download = '/storage/emulated/0/Download'
        if os.path.exists(download):
            return download
        return os.getcwd()

    def get_current_path(self):
        app_folder = '/storage/emulated/0/Download/WaDataBase'
        if os.path.exists(app_folder):
            return app_folder
        return os.getcwd()

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
        main = self.root.get_screen('main')
        all_inputs = self.get_all_textinputs(main)
        try:
            idx = all_inputs.index(current_input)
            if idx + 1 < len(all_inputs):
                all_inputs[idx + 1].focus = True
        except ValueError:
            pass

    def load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.db = json.load(f)
            except:
                self.db = []
        else:
            self.db = []

    def save_db(self):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.db, f)

    # ==========================================
    # MATH HELPERS
    # ==========================================
    def to_float(self, val):
        if val in (None, "-", ""): 
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

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
        dd_val = self.to_float(dd_val)
        if dd_val is None: return "-"
        
        neg = dd_val < 0 or math.copysign(1.0, dd_val) < 0
        abs_v = abs(dd_val)
        d = math.floor(abs_v)
        m = round((abs_v - d) * 60.0)
        if m >= 60: 
            d += 1
            m = 0
        return f"{'-' if neg else ''}{d}°{m:02d}'"

    def dd_to_input_dm(self, dd_val):
        dd_val = self.to_float(dd_val)
        if dd_val is None: return ""
        
        neg = dd_val < 0 or math.copysign(1.0, dd_val) < 0
        abs_v = abs(dd_val)
        d = math.floor(abs_v)
        m = round((abs_v - d) * 60.0)
        if m >= 60: 
            d += 1
            m = 0
        m_str = f"{m:02d}"
        return f"{'-' if neg else ''}{d}.{m_str}"

    def safe_float(self, s):
        try: return float(s) if str(s).strip()!="" else None
        except: return None

    def get_val(self, id_name):
        main_screen = self.root.get_screen('main')
        return main_screen.ids[id_name].ids.inner_input.text

    # ==========================================
    # IMPORT LOGIC (KIVY FILE CHOOSER)
    # ==========================================
    def import_from_file(self):
        from kivy.factory import Factory
        self.fc_popup = Factory.FileChooserPopup()
        self.fc_popup.open()

    def process_selected_file(self, filepath):
        self._show_progress_popup()
        Clock.schedule_once(lambda dt: self._start_import_worker(filepath), 0.15)

    def _start_import_worker(self, filepath):
        threading.Thread(target=self._import_worker, args=(filepath,), daemon=True).start()

    def _import_worker(self, filepath):
        try:
            self._update_progress(10, "Opening file...")
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            self._update_progress(40, "Parsing JSON...")
            data = json.loads(content)
            
            if not isinstance(data, list):
                self._close_progress_popup()
                self._show_message("File contains invalid JSON format! Expected a list.")
                return
            
            self._update_progress(60, f"Parsed {len(data)} records")
            
            existing_ids = set()
            for d in self.db:
                key = f"{d.get('brand','')}|{d.get('model','')}|{d.get('fToeMin','')}"
                existing_ids.add(key)
            
            self._update_progress(75, "Adding new records...")
            
            added = 0
            total = len(data)
            for i, d in enumerate(data):
                if not isinstance(d, dict):
                    continue
                key = f"{d.get('brand','')}|{d.get('model','')}|{d.get('fToeMin','')}"
                if key not in existing_ids:
                    self.db.append(d)
                    existing_ids.add(key)
                    added += 1
                
                if total > 0 and (i % 5 == 0 or i == total - 1):
                    progress = 75 + int((i / max(total, 1)) * 20)
                    self._update_progress(progress, f"Processing {i+1}/{total}...")
            
            self._update_progress(95, "Saving database...")
            self.save_db()
            self._update_progress(100, "Complete!")
            
            Clock.schedule_once(lambda dt: self._close_progress_popup(), 0.8)
            Clock.schedule_once(lambda dt: self._finish_import(added), 0.9)
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self._close_progress_popup())
            Clock.schedule_once(lambda dt: self._show_message(f"Import error: {str(e)}"))
            print(traceback.format_exc())

    # ==========================================
    # PROGRESS POPUP
    # ==========================================
    def _show_progress_popup(self):
        content = BoxLayout(orientation='vertical', padding='20dp', spacing='15dp')
        
        lbl_title = Label(
            text='Importing Database...',
            size_hint_y=None, height='40dp',
            color=get_color_from_hex('#00ddff'),
            font_size='16sp', bold=True,
            halign='center', valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        content.add_widget(lbl_title)
        
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height='25dp')
        content.add_widget(self.progress_bar)
        
        self.progress_label = Label(
            text='0%',
            size_hint_y=None, height='30dp',
            color=get_color_from_hex('#ffdd00'),
            font_size='20sp', bold=True,
            halign='center', valign='middle'
        )
        self.progress_label.bind(size=self.progress_label.setter('text_size'))
        content.add_widget(self.progress_label)
        
        self.progress_status = Label(
            text='Reading file...',
            size_hint_y=None, height='30dp',
            color=get_color_from_hex('#8892b0'),
            font_size='13sp',
            halign='center', valign='middle'
        )
        self.progress_status.bind(size=self.progress_status.setter('text_size'))
        content.add_widget(self.progress_status)
        
        self.progress_popup = Popup(
            title='Please Wait',
            title_color=get_color_from_hex('#00ddff'),
            title_size='14sp',
            content=content,
            size_hint=(0.85, 0.4),
            background_color=get_color_from_hex('#0a0f1a'),
            separator_color=get_color_from_hex('#00ddff'),
            auto_dismiss=False
        )
        self.progress_popup.open()

    @mainthread
    def _update_progress(self, value, status_text=None):
        try:
            if self.progress_bar:
                self.progress_bar.value = value
            if self.progress_label:
                self.progress_label.text = f"{int(value)}%"
            if status_text and self.progress_status:
                self.progress_status.text = status_text
        except: pass

    @mainthread
    def _close_progress_popup(self):
        try:
            if self.progress_popup:
                self.progress_popup.dismiss()
                self.progress_popup = None
        except: pass

    @mainthread
    def _finish_import(self, added):
        try:
            if self.root.current == 'list_screen':
                self.root.get_screen('list_screen').populate_list(self.db)
        except: pass
        self._show_message(f"Successfully imported {added} new records!")

    # ==========================================
    # MESSAGE POPUP
    # ==========================================
    def _show_message(self, msg):
        content = BoxLayout(orientation='vertical', padding='15dp', spacing='10dp')
        lbl = Label(
            text=msg,
            color=get_color_from_hex('#ffffff'),
            font_size='14sp',
            halign='center', valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        content.add_widget(lbl)
        
        btn = Button(
            text='OK', size_hint_y=None, height='45dp',
            background_normal='', background_color=get_color_from_hex('#0055aa'),
            color=(1,1,1,1), bold=True, font_size='15sp'
        )
        content.add_widget(btn)
        
        popup = Popup(
            title='Info', title_color=get_color_from_hex('#00ddff'),
            content=content, size_hint=(0.85, 0.35),
            background_color=get_color_from_hex('#0a0f1a'),
            separator_color=get_color_from_hex('#00ddff')
        )
        btn.bind(on_release=popup.dismiss)
        popup.open()

    # ==========================================
    # OPEN SPEC POPUP
    # ==========================================
    def open_spec_popup(self, data):
        app = self
        content = BoxLayout(orientation='vertical', padding='10dp', spacing='8dp')

        title = Label(
            text=f"{data.get('brand','')}  -  {data.get('model','')}",
            size_hint_y=None, height='40dp',
            color=get_color_from_hex('#ffdd00'),
            font_size='18sp', bold=True,
            halign='center', valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        content.add_widget(title)

        btn_edit = Button(
            text='EDIT THIS SPEC',
            size_hint_y=None, height='42dp',
            background_normal='',
            background_color=get_color_from_hex('#d97706'),
            color=(1,1,1,1), bold=True, font_size='14sp'
        )
        content.add_widget(btn_edit)

        scroll = ScrollView(size_hint=(1, 1))
        table = BoxLayout(orientation='vertical', size_hint_y=None, spacing=0)
        table.bind(minimum_height=table.setter('height'))

        header = GridLayout(cols=5, size_hint_y=None, height='50dp', spacing=1)
        for t, w in [("PARAM", 1.2), ("MIN", 0.9), ("MAX", 0.9), ("STD", 0.9), ("TOL", 0.9)]:
            c = ExcelHeaderCell(lbl_text=t)
            c.size_hint_x = w
            header.add_widget(c)
        table.add_widget(header)

        def add_row(label, std, tol, min_v, max_v):
            std = app.to_float(std)
            tol = app.to_float(tol)
            min_v = app.to_float(min_v)
            max_v = app.to_float(max_v)
            
            if std is None and tol is None and min_v is None and max_v is None:
                return
                
            def fmt_cell(val):
                if val is None: return "-"
                return f"{app.dd_to_dm_str(val)}\n[size=12sp][color=#aaaaaa]({val:.2f}°)[/color][/size]"

            r = GridLayout(cols=5, size_hint_y=None, height='65dp', spacing=1)
            
            p_cell = ExcelParamCell(lbl_text=label)
            p_cell.size_hint_x = 1.2
            r.add_widget(p_cell)
            
            for v in [min_v, max_v, std, tol]:
                v_cell = ExcelValueCell(lbl_text=fmt_cell(v))
                v_cell.size_hint_x = 0.9
                r.add_widget(v_cell)
                
            table.add_widget(r)

        add_row("Front\nToe", data.get('fToeStd'), data.get('fToeTol'), data.get('fToeMin'), data.get('fToeMax'))
        add_row("Front\nCamber", data.get('fCamStd'), data.get('fCamTol'), data.get('fCamMin'), data.get('fCamMax'))
        add_row("Front\nCastor", data.get('fCasStd'), data.get('fCasTol'), data.get('fCasMin'), data.get('fCasMax'))
        add_row("Rear\nToe", data.get('rToeStd'), data.get('rToeTol'), data.get('rToeMin'), data.get('rToeMax'))
        add_row("Rear\nCamber", data.get('rCamStd'), data.get('rCamTol'), data.get('rCamMin'), data.get('rCamMax'))

        scroll.add_widget(table)
        content.add_widget(scroll)

        btn_close = Button(
            text='CLOSE',
            size_hint_y=None, height='48dp',
            background_normal='',
            background_color=get_color_from_hex('#d32f2f'),
            color=(1,1,1,1), bold=True, font_size='15sp'
        )
        content.add_widget(btn_close)

        popup = Popup(
            title='Specifications',
            title_color=get_color_from_hex('#00ddff'),
            title_size='16sp',
            content=content,
            size_hint=(0.98, 0.9),
            background_color=get_color_from_hex('#0a0f1a'),
            separator_color=get_color_from_hex('#00ddff')
        )
        btn_close.bind(on_release=popup.dismiss)
        
        def do_edit(instance):
            popup.dismiss()
            app.load_spec_for_edit(data)
        
        btn_edit.bind(on_release=do_edit)
        popup.open()

    # ==========================================
    # LOAD SPEC FOR EDITING
    # ==========================================
    def load_spec_for_edit(self, data):
        main = self.root.get_screen('main')
        
        try:
            self.editing_index = self.db.index(data)
        except ValueError:
            self.editing_index = None
        
        main.ids.inp_brand.ids.inner_input.text = data.get('brand', '')
        main.ids.inp_model_name.ids.inner_input.text = data.get('model', '')
        main.ids.inp_common_rim.ids.inner_input.text = '15'
        
        main.ids.sm.current = 'tab1'
        self.t1_f_toe_type = 'DM'
        self.t1_r_toe_type = 'DM'
        
        def set_val(id_name, val):
            val = self.to_float(val)
            if val is not None:
                main.ids[id_name].ids.inner_input.text = self.dd_to_input_dm(val)
            else:
                main.ids[id_name].ids.inner_input.text = ""
        
        set_val('t1_fToeMin', data.get('fToeMin'))
        set_val('t1_fToeMax', data.get('fToeMax'))
        set_val('t1_fCamMin', data.get('fCamMin'))
        set_val('t1_fCamMax', data.get('fCamMax'))
        set_val('t1_fCasMin', data.get('fCasMin'))
        set_val('t1_fCasMax', data.get('fCasMax'))
        set_val('t1_rToeMin', data.get('rToeMin'))
        set_val('t1_rToeMax', data.get('rToeMax'))
        set_val('t1_rCamMin', data.get('rCamMin'))
        set_val('t1_rCamMax', data.get('rCamMax'))
        
        main.ids.msg_label.text = "Editing existing spec. Press SAVE to update."
        main.ids.msg_label.color = get_color_from_hex('#ffdd00')
        
        self.root.current = 'main'

    # ==========================================
    # SAVE / UPDATE LOGIC
    # ==========================================
    def save_data(self):
        main = self.root.get_screen('main')
        brand = main.ids.inp_brand.ids.inner_input.text.strip()
        model = main.ids.inp_model_name.ids.inner_input.text.strip()
        
        if not brand or not model:
            main.ids.msg_label.text = "Brand and Model required!"
            main.ids.msg_label.color = get_color_from_hex('#ff3333')
            return

        common_rim = self.safe_float(main.ids.inp_common_rim.ids.inner_input.text)
        current_tab = main.ids.sm.current
        
        fToeMin, fToeMax, fToeStd, fToeTol = "-", "-", "-", "-"
        fCamMin, fCamMax, fCamStd, fCamTol = "-", "-", "-", "-"
        fCasMin, fCasMax, fCasStd, fCasTol = "-", "-", "-", "-"
        rToeMin, rToeMax, rToeStd, rToeTol = "-", "-", "-", "-"
        rCamMin, rCamMax, rCamStd, rCamTol = "-", "-", "-", "-"

        try:
            if current_tab == 'tab1':
                t_min, t_max = self.get_val('t1_fToeMin'), self.get_val('t1_fToeMax')
                if self.t1_f_toe_type == "MM" and (common_rim is None or common_rim <= 0):
                    raise ValueError("Rim size required for MM!")
                fToeMin = self.mm_to_dd(self.safe_float(t_min), common_rim) if self.t1_f_toe_type=="MM" else self.dm_to_dd(t_min)
                fToeMax = self.mm_to_dd(self.safe_float(t_max), common_rim) if self.t1_f_toe_type=="MM" else self.dm_to_dd(t_max)
                if fToeMin is not None and fToeMax is not None:
                    fToeStd = (fToeMax + fToeMin)/2; fToeTol = abs(fToeMax - fToeMin)/2
                
                fCamMin = self.dm_to_dd(self.get_val('t1_fCamMin')); fCamMax = self.dm_to_dd(self.get_val('t1_fCamMax'))
                if fCamMin is not None and fCamMax is not None: fCamStd = (fCamMax+fCamMin)/2; fCamTol = abs(fCamMax-fCamMin)/2
                
                fCasMin = self.dm_to_dd(self.get_val('t1_fCasMin')); fCasMax = self.dm_to_dd(self.get_val('t1_fCasMax'))
                if fCasMin is not None and fCasMax is not None: fCasStd = (fCasMax+fCasMin)/2; fCasTol = abs(fCasMax-fCasMin)/2

                rt_min, rt_max = self.get_val('t1_rToeMin'), self.get_val('t1_rToeMax')
                if rt_min and rt_max:
                    if self.t1_r_toe_type == "MM" and (common_rim is None or common_rim <= 0):
                        raise ValueError("Rim size required for rear MM!")
                    rToeMin = self.mm_to_dd(self.safe_float(rt_min), common_rim) if self.t1_r_toe_type=="MM" else self.dm_to_dd(rt_min)
                    rToeMax = self.mm_to_dd(self.safe_float(rt_max), common_rim) if self.t1_r_toe_type=="MM" else self.dm_to_dd(rt_max)
                    if rToeMin is not None and rToeMax is not None:
                        rToeStd = (rToeMax+rToeMin)/2; rToeTol = abs(rToeMax-rToeMin)/2
                    
                rc_min, rc_max = self.get_val('t1_rCamMin'), self.get_val('t1_rCamMax')
                if rc_min and rc_max:
                    rCamMin = self.dm_to_dd(rc_min); rCamMax = self.dm_to_dd(rc_max)
                    if rCamMin is not None and rCamMax is not None:
                        rCamStd = (rCamMax+rCamMin)/2; rCamTol = abs(rCamMax-rCamMin)/2

            elif current_tab == 'tab2':
                t_min, t_max = self.get_val('t2_fToeMin'), self.get_val('t2_fToeMax')
                if self.t2_f_toe_type == "MM" and (common_rim is None or common_rim <= 0):
                    raise ValueError("Rim size required for MM!")
                fToeMin = self.mm_to_dd(self.safe_float(t_min), common_rim) if self.t2_f_toe_type=="MM" else self.safe_float(t_min)
                fToeMax = self.mm_to_dd(self.safe_float(t_max), common_rim) if self.t2_f_toe_type=="MM" else self.safe_float(t_max)
                if fToeMin is not None and fToeMax is not None: fToeStd = (fToeMax+fToeMin)/2; fToeTol = abs(fToeMax-fToeMin)/2
                
                fCamMin = self.safe_float(self.get_val('t2_fCamMin')); fCamMax = self.safe_float(self.get_val('t2_fCamMax'))
                if fCamMin is not None and fCamMax is not None: fCamStd = (fCamMax+fCamMin)/2; fCamTol = abs(fCamMax-fCamMin)/2
                
                fCasMin = self.safe_float(self.get_val('t2_fCasMin')); fCasMax = self.safe_float(self.get_val('t2_fCasMax'))
                if fCasMin is not None and fCasMax is not None: fCasStd = (fCasMax+fCasMin)/2; fCasTol = abs(fCasMax-fCasMin)/2

                rt_min, rt_max = self.get_val('t2_rToeMin'), self.get_val('t2_rToeMax')
                if rt_min and rt_max:
                    if self.t2_r_toe_type == "MM" and (common_rim is None or common_rim <= 0):
                        raise ValueError("Rim size required for rear MM!")
                    rToeMin = self.mm_to_dd(self.safe_float(rt_min), common_rim) if self.t2_r_toe_type=="MM" else self.safe_float(rt_min)
                    rToeMax = self.mm_to_dd(self.safe_float(rt_max), common_rim) if self.t2_r_toe_type=="MM" else self.safe_float(rt_max)
                    if rToeMin is not None and rToeMax is not None:
                        rToeStd = (rToeMax+rToeMin)/2; rToeTol = abs(rToeMax-rToeMin)/2
                    
                rc_min, rc_max = self.safe_float(self.get_val('t2_rCamMin')), self.safe_float(self.get_val('t2_rCamMax'))
                if rc_min is not None and rc_max is not None:
                    rCamMin = rc_min; rCamMax = rc_max; rCamStd = (rc_max+rc_min)/2; rCamTol = abs(rc_max-rc_min)/2

            elif current_tab == 'tab3':
                std_raw, tol_raw = self.get_val('t3_fToeStd'), self.get_val('t3_fToeTol')
                if self.t3_f_toe_type == "MM":
                    if common_rim is None or common_rim <= 0:
                        raise ValueError("Rim size required for MM!")
                    fToeStd = self.mm_to_dd(self.safe_float(std_raw), common_rim)
                    fToeTol = abs(self.mm_to_dd(self.safe_float(tol_raw), common_rim))
                elif self.t3_sub_mode == "DM":
                    fToeStd = self.dm_to_dd(std_raw); fToeTol = abs(self.dm_to_dd(tol_raw) or 0)
                else:
                    fToeStd = self.safe_float(std_raw); fToeTol = abs(self.safe_float(tol_raw) or 0)
                
                if self.t3_sub_mode == "DM":
                    fCamStd = self.dm_to_dd(self.get_val('t3_fCamStd'))
                    fCamTol = abs(self.dm_to_dd(self.get_val('t3_fCamTol')) or 0)
                    fCasStd = self.dm_to_dd(self.get_val('t3_fCasStd'))
                    fCasTol = abs(self.dm_to_dd(self.get_val('t3_fCasTol')) or 0)
                else:
                    fCamStd = self.safe_float(self.get_val('t3_fCamStd'))
                    fCamTol = abs(self.safe_float(self.get_val('t3_fCamTol')) or 0)
                    fCasStd = self.safe_float(self.get_val('t3_fCasStd'))
                    fCasTol = abs(self.safe_float(self.get_val('t3_fCasTol')) or 0)
                
                if fToeStd is not None and fToeTol is not None: fToeMin = fToeStd - fToeTol; fToeMax = fToeStd + fToeTol
                if fCamStd is not None and fCamTol is not None: fCamMin = fCamStd - fCamTol; fCamMax = fCamStd + fCamTol
                if fCasStd is not None and fCasTol is not None: fCasMin = fCasStd - fCasTol; fCasMax = fCasStd + fCasTol

                r_std, r_tol = self.get_val('t3_rToeStd'), self.get_val('t3_rToeTol')
                if r_std and r_tol:
                    if self.t3_r_toe_type == "MM":
                        if common_rim is None or common_rim <= 0:
                            raise ValueError("Rim size required for rear MM!")
                        rToeStd = self.mm_to_dd(self.safe_float(r_std), common_rim)
                        rToeTol = abs(self.mm_to_dd(self.safe_float(r_tol), common_rim))
                    elif self.t3_sub_mode == "DM":
                        rToeStd = self.dm_to_dd(r_std); rToeTol = abs(self.dm_to_dd(r_tol) or 0)
                    else:
                        rToeStd = self.safe_float(r_std); rToeTol = abs(self.safe_float(r_tol) or 0)
                    if rToeStd is not None and rToeTol is not None:
                        rToeMin = rToeStd - rToeTol; rToeMax = rToeStd + rToeTol

                rc_std, rc_tol = self.get_val('t3_rCamStd'), self.get_val('t3_rCamTol')
                if rc_std and rc_tol:
                    if self.t3_sub_mode == "DM":
                        rCamStd = self.dm_to_dd(rc_std); rCamTol = abs(self.dm_to_dd(rc_tol) or 0)
                    else:
                        rCamStd = self.safe_float(rc_std); rCamTol = abs(self.safe_float(rc_tol) or 0)
                    if rCamStd is not None and rCamTol is not None:
                        rCamMin = rCamStd - rCamTol; rCamMax = rCamStd + rCamTol

            data = {
                "brand": brand, "model": model,
                "fToeMin": fToeMin, "fToeMax": fToeMax, "fToeStd": fToeStd, "fToeTol": fToeTol,
                "fCamMin": fCamMin, "fCamMax": fCamMax, "fCamStd": fCamStd, "fCamTol": fCamTol,
                "fCasMin": fCasMin, "fCasMax": fCasMax, "fCasStd": fCasStd, "fCasTol": fCasTol,
                "rToeMin": rToeMin, "rToeMax": rToeMax, "rToeStd": rToeStd, "rToeTol": rToeTol,
                "rCamMin": rCamMin, "rCamMax": rCamMax, "rCamStd": rCamStd, "rCamTol": rCamTol
            }
            
            if self.editing_index is not None and 0 <= self.editing_index < len(self.db):
                self.db[self.editing_index] = data
                main.ids.msg_label.text = "Updated Successfully!"
                self.editing_index = None
            else:
                self.db.append(data)
                main.ids.msg_label.text = "Saved Successfully!"
            
            self.save_db()
            main.ids.msg_label.color = get_color_from_hex('#00ff88')
            
            for id_name in ['inp_brand', 'inp_model_name']:
                main.ids[id_name].ids.inner_input.text = ''
                
        except Exception as e:
            main.ids.msg_label.text = f"Error: {str(e)}"
            main.ids.msg_label.color = get_color_from_hex('#ff3333')
            print(traceback.format_exc())


if __name__ == "__main__":
    AlignmentApp().run()
