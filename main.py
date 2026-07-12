import random
import string
import os
import subprocess
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from threading import Thread
from kivy.clock import mainthread
from plyer import notification

class RemoteAndroidApp(App):
    def build(self):
        self.title = "ATS Remote Connector"
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add(Label(text="ATS Remote Android Service", font_size='24sp', bold=True, color=(0, 0.67, 0.7, 1)))
        
        self.lbl_id = Label(text="Remote ID: Not Started", font_size='18sp')
        layout.add(self.lbl_id)
        
        layout.add(Label(text="Set Custom Password:", font_size='16sp'))
        self.txt_pass = TextInput(text="ats123", multiline=False, font_size='18sp', halign="center", write_tab=False)
        layout.add(self.txt_pass)
        
        self.btn_start = Button(text="Start Remote Connection", size_hint=(1, 0.3), background_color=(0, 0.67, 0.7, 1), bold=True)
        self.btn_start.bind(on_press=self.start_service)
        layout.add(self.btn_start)
        
        self.lbl_status = Label(text="Status: Stopped", font_size='16sp', color=(1, 0, 0, 1), bold=True)
        layout.add(self.lbl_status)
        
        return layout

    def start_service(self, instance):
        self.lbl_status.text = "Starting secure tunnel..."
        self.lbl_status.color = (1, 0.6, 0, 1)
        self.btn_start.disabled = True
        
        try:
            notification.notify(title="ATS Remote", message="Initializing secure cloud tunnel...")
        except:
            pass
        
        Thread(target=self.run_backend_bridge).start()

    @mainthread
    def update_ui_success(self, session_id):
        self.lbl_id.text = f"Remote ID: {session_id}"
        self.lbl_status.text = "Live and Connectable via Cloud!"
        self.lbl_status.color = (0, 1, 0, 1)
        try:
            notification.notify(title="ATS Remote Live", message=f"Connected successfully with ID: {session_id}")
        except:
            pass

    @mainthread
    def update_ui_failure(self, error_msg):
        self.lbl_status.text = f"Error: {error_msg}"
        self.lbl_status.color = (1, 0, 0, 1)
        self.btn_start.disabled = False

    def run_backend_bridge(self):
        try:
            password = self.txt_pass.text.strip()
            generated_id = "ats-remote-" + "".join(random.choices(string.digits, k=5))
            
            command = f"ssh -o StrictHostKeyChecking=no -R {generated_id}:80:localhost:8080 R@{password}.pinggy.io"
            
            process = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.update_ui_success(generated_id)
            
        except Exception as e:
            self.update_ui_failure(str(e))

if __name__ == '__main__':
    RemoteAndroidApp().run()
    
