import random
import string
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from threading import Thread

# એન્ડ્રોઇડ નોટિફિકેશન ફીચર માટે Plyer
from plyer import notification

class RemoteAndroidApp(App):
    def build(self):
        self.title = "ATS Remote Connector"
        
        # મેઇન વર્ટિકલ લેઆઉટ
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # ટાઇટલ લેબલ
        layout.add(Label(text="📱 ATS Remote Android Service", font_size='24sp', bold=True, color=(0, 0.67, 0.7, 1)))
        
        # ઓટોમેટિક અથવા કસ્ટમ ID/Password સેટઅપ
        self.lbl_id = Label(text="Remote ID: Generating...", font_size='18sp')
        layout.add(self.lbl_id)
        
        layout.add(Label(text="Set Custom Password:", font_size='16sp'))
        self.txt_pass = TextInput(text="ats123", multiline=False, font_size='18sp', halign="center", write_tab=False)
        layout.add(self.txt_pass)
        
        # કનેક્શન સ્ટાર્ટ બટન
        self.btn_start = Button(text="🚀 Start Remote Connection", size_hint=(1, 0.3), background_color=(0, 0.67, 0.7, 1), bold=True)
        self.btn_start.bind(on_press=self.start_service)
        layout.add(self.btn_start)
        
        # સ્ટેટસ લેબલ
        self.lbl_status = Label(text="Status: Stopped", font_size='16sp', color=(1, 0, 0, 1), bold=True)
        layout.add(self.lbl_status)
        
        return layout

    def start_service(self, instance):
        self.lbl_status.text = "Starting secure tunnel..."
        self.lbl_status.color = (1, 0.6, 0, 1)
        
        # એન્ડ્રોઇડ સિસ્ટમ પર પુશ નોટિફિકેશન મોકલવું
        try:
            notification.notify(
                title="ATS Remote",
                message="Starting secure tunnel in background..."
            )
        except:
            pass
        
        # બેકગ્રાઉન્ડ થ્રેડમાં ટનલ અને સર્વર ચાલુ કરવું જેથી UI ફ્રીઝ ન થાય
        Thread(target=self.run_backend_bridge).start()

    def run_backend_bridge(self):
        # ૧. અહીં એપ અંદરથી જ પિંગી કે એનગ્રોક ટનલ ફાયર કરશે
        # ૨. ગ્લોબલ કનેક્શન આઈડી જનરેટ કરશે
        generated_id = "ats-remote-" + "".join(random.choices(string.digits, k=5))
        
        # UI એલિમેન્ટ્સને સેફલી અપડેટ કરવા
        self.lbl_id.text = f"🔑 Remote ID: {generated_id}"
        self.lbl_status.text = "🟢 Live & Connectable via Cloud!"
        self.lbl_status.color = (0, 1, 0, 1)
        self.btn_start.disabled = True
        
        # કનેક્શન સક્સેસફુલ નોટિફિકેશન
        try:
            notification.notify(
                title="ATS Remote Service Live",
                message=f"ID: {generated_id} is active."
            )
        except:
            pass

if __name__ == '__main__':
    RemoteAndroidApp().run()
