import json
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from kivy.clock import Clock

# Android System Audio, Device Detection, EQ & WakeLock
PythonActivity = None
Context = None
AudioManager = None
Equalizer = None
BassBoost = None
BluetoothAdapter = None
PowerManager = None
Intent = None

if platform == 'android':
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        AudioManager = autoclass('android.media.AudioManager')
        Equalizer = autoclass('android.media.audiofx.Equalizer')
        BassBoost = autoclass('android.media.audiofx.BassBoost')
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        PowerManager = autoclass('android.os.PowerManager')
        Intent = autoclass('android.content.Intent')

        try:
            from android.permissions import request_permissions
            request_permissions([
                'android.permission.BLUETOOTH_CONNECT',
                'android.permission.BLUETOOTH_SCAN',
                'android.permission.MODIFY_AUDIO_SETTINGS',
                'android.permission.WAKE_LOCK'
            ])
        except Exception:
            pass
    except Exception as e:
        print("Android Import Error:", e)


class ProCard(BoxLayout):
    def __init__(self, bg_hex='#112240', **kwargs):
        super().__init__(**kwargs)
        self.bg_hex = bg_hex
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(rgba=get_color_from_hex(self.bg_hex))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[14])


class AudioControllerApp(App):
    def build(self):
        self.title = "Pro Audio EQ Controller"

        # Default Values
        self.volume = 50       # 0 to 100%
        self.bass = 50         # 0 to 100%
        self.treble = 50       # 0 to 100%
        self.bass_freq = 50    # Min 50Hz (Range: 50Hz to 150Hz)

        self.device_name = "Detecting Audio Device..."
        self.was_music_active = False
        self.eq_engine = None
        self.bass_engine = None
        self.wake_lock = None

        self.load_settings()

        # Main Layout
        self.main_layout = BoxLayout(orientation='vertical', padding='15dp', spacing='12dp')
        with self.main_layout.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            self.bg_rect = RoundedRectangle(pos=self.main_layout.pos, size=self.main_layout.size)
        self.main_layout.bind(pos=self.update_bg, size=self.update_bg)

        # 1. TOP BAR: Connected Audio Device Name
        device_bar = ProCard(bg_hex='#004d40', size_hint_y=None, height='50dp', padding='10dp')
        self.lbl_device = Label(
            text=f"🔊 Output: {self.device_name}",
            font_size='16sp',
            bold=True,
            color=get_color_from_hex('#64ffda')
        )
        device_bar.add_widget(self.lbl_device)
        self.main_layout.add_widget(device_bar)

        # 2. SUB-BAR: Live Data Status
        status_bar = ProCard(bg_hex='#1e3a5f', size_hint_y=None, height='42dp', padding='8dp')
        self.lbl_status = Label(
            text=self.get_status_text(),
            font_size='14sp',
            bold=True,
            color=get_color_from_hex('#ccd6f6')
        )
        status_bar.add_widget(self.lbl_status)
        self.main_layout.add_widget(status_bar)

        # 3. SLIDERS CONTAINER (Takes full remaining screen space)
        sliders_box = BoxLayout(orientation='vertical', spacing='12dp')

        # VOLUME SLIDER (0 - 100%)
        self.card_vol, self.lbl_vol_val, self.slider_vol = self.create_slider_card(
            title="MASTER VOLUME",
            min_val=0, max_val=100, cur_val=self.volume,
            unit="%", accent_hex='#00e676',
            callback=self.on_volume_change
        )
        sliders_box.add_widget(self.card_vol)

        # BASS SLIDER (0 - 100%)
        self.card_bass, self.lbl_bass_val, self.slider_bass = self.create_slider_card(
            title="BASS BOOST",
            min_val=0, max_val=100, cur_val=self.bass,
            unit="%", accent_hex='#ff6d00',
            callback=self.on_bass_change
        )
        sliders_box.add_widget(self.card_bass)

        # BASS FREQUENCY SLIDER (Min 50Hz - 150Hz)
        self.card_freq, self.lbl_freq_val, self.slider_freq = self.create_slider_card(
            title="BASS FREQUENCY (MIN 50Hz)",
            min_val=50, max_val=150, cur_val=self.bass_freq,
            unit=" Hz", accent_hex='#ffab40',
            callback=self.on_freq_change
        )
        sliders_box.add_widget(self.card_freq)

        # TREBLE SLIDER (0 - 100%)
        self.card_treble, self.lbl_treble_val, self.slider_treble = self.create_slider_card(
            title="TREBLE (CLARITY)",
            min_val=0, max_val=100, cur_val=self.treble,
            unit="%", accent_hex='#00b0ff',
            callback=self.on_treble_change
        )
        sliders_box.add_widget(self.card_treble)

        self.main_layout.add_widget(sliders_box)
        return self.main_layout

    # ==========================================
    # APP LIFECYCLE (LOCK SCREEN & BACKGROUND)
    # ==========================================
    def on_start(self):
        # 1. Acquire WakeLock so app runs even when phone is locked
        self.acquire_wakelock()
        # 2. Initialize Global Audio Engine (Session 0 = All Apps)
        self.init_audio_engine()
        # 3. Detect Device & Send Data immediately on app open
        self.detect_connected_audio_device()
        self.apply_all_audio_data()
        # 4. Continuous background monitor (every 1.5 sec)
        Clock.schedule_interval(self.background_monitor, 1.5)

    def on_pause(self):
        # Phone lock thay ke home dabavo tyare app bandh na thava de
        return True

    def on_resume(self):
        # App pachi screen par aave tyare data refresh kare
        self.detect_connected_audio_device()
        self.apply_all_audio_data()

    def acquire_wakelock(self):
        if platform == 'android' and PowerManager:
            try:
                activity = PythonActivity.mActivity
                pm = activity.getSystemService(Context.POWER_SERVICE)
                # PARTIAL_WAKE_LOCK keeps CPU running when screen is off/locked
                self.wake_lock = pm.newWakeLock(1, "ProAudioEQ::WakeLock")
                if not self.wake_lock.isHeld():
                    self.wake_lock.acquire()
            except Exception as e:
                print("WakeLock Error:", e)

    # ==========================================
    # DEVICE DETECTION & GLOBAL AUDIO DSP ENGINE
    # ==========================================
    def init_audio_engine(self):
        if platform == 'android':
            try:
                # Session 0 attaches to Android Global Output Mix (Spotify, YouTube, etc.)
                if self.eq_engine is None:
                    self.eq_engine = Equalizer(100, 0)
                    self.eq_engine.setEnabled(True)
                if self.bass_engine is None:
                    self.bass_engine = BassBoost(100, 0)
                    self.bass_engine.setEnabled(True)
            except Exception as e:
                print("AudioFX Init Error:", e)

    def detect_connected_audio_device(self):
        if platform != 'android':
            self.device_name = "PC / Simulated Speaker"
            self.lbl_device.text = f"🔊 Output: {self.device_name}"
            return

        detected = "Phone Internal Speaker"
        try:
            activity = PythonActivity.mActivity
            audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)

            # Method 1: Check active audio output devices (API 23+)
            # GET_DEVICES_OUTPUTS = 2
            devices = audio_manager.getDevices(2)
            if devices:
                for dev in devices:
                    dev_type = dev.getType()
                    # 8 = Bluetooth A2DP, 7 = Bluetooth SCO, 22 = BLE Headset, 3/4 = Wired Headset
                    if dev_type in (8, 7, 22, 3, 4):
                        p_name = dev.getProductName()
                        if p_name:
                            detected = p_name.toString()
                            if dev_type in (8, 7, 22):
                                detected = f"BT: {detected}"
                            break
        except Exception as e:
            print("Device Scan Error:", e)

        if detected != self.device_name:
            self.device_name = detected
            self.lbl_device.text = f"🔊 Output: {self.device_name}"
            # Nava device connect thata j tarat data apply karo
            self.apply_all_audio_data()

    def background_monitor(self, dt):
        # 1. Check connected audio device
        self.detect_connected_audio_device()

        # 2. Check if music is playing in ANY app
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
                is_playing = audio_manager.isMusicActive()

                if is_playing and not self.was_music_active:
                    # Jevu song play thavanu chalu thay etle tarat EQ data send karo
                    self.init_audio_engine()
                    self.apply_all_audio_data()
                    self.bring_app_to_front()

                self.was_music_active = is_playing
                play_state = "🎵 Playing" if is_playing else "⏸ Idle"
                self.lbl_device.text = f"🔊 {self.device_name}  [{play_state}]"
            except Exception as e:
                print("Monitor Error:", e)

    def bring_app_to_front(self):
        # Track chalu thay tyare app ne auto-launch / front ma lavva mate
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                pm = activity.getPackageManager()
                intent = pm.getLaunchIntentForPackage(activity.getPackageName())
                if intent:
                    # FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_SINGLE_TOP
                    intent.addFlags(268435456 | 536870912)
                    activity.startActivity(intent)
            except Exception as e:
                print("Auto-Launch Error:", e)

    # ==========================================
    # APPLY AUDIO DATA TO ACTIVE DEVICE
    # ==========================================
    def apply_all_audio_data(self):
        self.lbl_status.text = self.get_status_text()
        self.save_settings()

        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)

                # 1. Set Master Volume (0 to 100%)
                max_vol = audio_manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                target_vol = int((self.volume / 100.0) * max_vol)
                audio_manager.setStreamVolume(AudioManager.STREAM_MUSIC, target_vol, 0)

                # 2. Set Bass Boost (0 to 1000 permille)
                if self.bass_engine:
                    self.bass_engine.setStrength(int(self.bass * 10))

                # 3. Set Bass Frequency (Min 50Hz) & Treble via Equalizer Bands
                if self.eq_engine:
                    num_bands = self.eq_engine.getNumberOfBands()
                    level_range = self.eq_engine.getBandLevelRange()
                    min_lvl = level_range[0]
                    max_lvl = level_range[1]

                    target_freq_milli = max(50, self.bass_freq) * 1000  # Convert Hz to milliHertz

                    for b in range(num_bands):
                        center_freq = self.eq_engine.getCenterFreq(b)  # in milliHertz

                        # Sub-50Hz protection: Cut frequencies strictly below 50Hz
                        if center_freq < 50000:
                            self.eq_engine.setBandLevel(b, int(min_lvl // 2))

                        # Bass Band (50Hz to 250Hz): Boost around selected Bass Frequency
                        elif 50000 <= center_freq <= 250000:
                            dist = abs(center_freq - target_freq_milli) / 200000.0
                            factor = max(0.2, 1.0 - dist)
                            bass_lvl = int(((self.bass - 50) / 50.0) * max_lvl * factor)
                            self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, bass_lvl)))

                        # Treble Band (>= 4000Hz): Adjust Clarity/Treble
                        elif center_freq >= 4000000:
                            treble_lvl = int(((self.treble - 50) / 50.0) * max_lvl)
                            self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, treble_lvl)))
            except Exception as e:
                print("Apply Audio Data Error:", e)
        else:
            print(f"SENT TO [{self.device_name}] -> VOL:{self.volume}%, BASS:{self.bass}%@{self.bass_freq}Hz, TREBLE:{self.treble}%")

    # ==========================================
    # UI HELPERS & SLIDER EVENTS
    # ==========================================
    def update_bg(self, instance, *args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def create_slider_card(self, title, min_val, max_val, cur_val, unit, accent_hex, callback):
        card = ProCard(orientation='vertical', padding=['15dp', '10dp'], spacing='5dp')

        top_row = BoxLayout(orientation='horizontal', size_hint_y=0.45)
        lbl_title = Label(
            text=title,
            font_size='15sp',
            bold=True,
            color=get_color_from_hex('#ccd6f6'),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))

        lbl_val = Label(
            text=f"{int(cur_val)}{unit}",
            font_size='20sp',
            bold=True,
            color=get_color_from_hex(accent_hex),
            size_hint_x=0.35,
            halign='right',
            valign='middle'
        )
        lbl_val.bind(size=lbl_val.setter('text_size'))

        top_row.add_widget(lbl_title)
        top_row.add_widget(lbl_val)

        slider = Slider(
            min=min_val,
            max=max_val,
            value=cur_val,
            step=1,
            cursor_size=('34dp', '34dp'),
            background_width='20dp',
            value_track=True,
            value_track_color=get_color_from_hex(accent_hex),
            value_track_width='6dp',
            size_hint_y=0.55
        )
        slider.bind(value=callback)

        card.add_widget(top_row)
        card.add_widget(slider)
        return card, lbl_val, slider

    def get_status_text(self):
        return f"VOL: {self.volume}%  |  BASS: {self.bass}% ({self.bass_freq}Hz)  |  TREBLE: {self.treble}%"

    def on_volume_change(self, instance, value):
        self.volume = int(value)
        self.lbl_vol_val.text = f"{self.volume}%"
        self.apply_all_audio_data()

    def on_bass_change(self, instance, value):
        self.bass = int(value)
        self.lbl_bass_val.text = f"{self.bass}%"
        self.apply_all_audio_data()

    def on_freq_change(self, instance, value):
        self.bass_freq = max(50, int(value))
        self.lbl_freq_val.text = f"{self.bass_freq} Hz"
        self.apply_all_audio_data()

    def on_treble_change(self, instance, value):
        self.treble = int(value)
        self.lbl_treble_val.text = f"{self.treble}%"
        self.apply_all_audio_data()

    # ==========================================
    # AUTO-SAVE & LOAD SETTINGS
    # ==========================================
    def save_settings(self):
        data = {
            'volume': self.volume,
            'bass': self.bass,
            'treble': self.treble,
            'bass_freq': max(50, self.bass_freq)
        }
        try:
            with open('audio_eq_settings.json', 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def load_settings(self):
        if os.path.exists('audio_eq_settings.json'):
            try:
                with open('audio_eq_settings.json', 'r') as f:
                    data = json.load(f)
                    self.volume = data.get('volume', 50)
                    self.bass = data.get('bass', 50)
                    self.treble = data.get('treble', 50)
                    self.bass_freq = max(50, data.get('bass_freq', 50))
            except Exception:
                pass


if __name__ == "__main__":
    AudioControllerApp().run()
