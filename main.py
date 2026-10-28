import json
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from kivy.clock import Clock

PythonActivity = None
Context = None
AudioManager = None
Equalizer = None
BassBoost = None
Visualizer = None
PowerManager = None
Intent = None
Settings = None
Uri = None

if platform == 'android':
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        AudioManager = autoclass('android.media.AudioManager')
        Equalizer = autoclass('android.media.audiofx.Equalizer')
        BassBoost = autoclass('android.media.audiofx.BassBoost')
        Visualizer = autoclass('android.media.audiofx.Visualizer')
        PowerManager = autoclass('android.os.PowerManager')
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        Uri = autoclass('android.net.Uri')

        try:
            from android.permissions import request_permissions
            request_permissions([
                'android.permission.BLUETOOTH_CONNECT',
                'android.permission.BLUETOOTH_SCAN',
                'android.permission.MODIFY_AUDIO_SETTINGS',
                'android.permission.RECORD_AUDIO',
                'android.permission.WAKE_LOCK',
                'android.permission.FOREGROUND_SERVICE',
                'android.permission.POST_NOTIFICATIONS'
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
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12])


class AudioControllerApp(App):
    def build(self):
        self.title = "Photon Audio"

        # 6-Band Professional Audio Settings + Always On Flag
        self.always_on = True  # Kill-Proof Background Mode (Default ON)
        self.volume = 50       # Master Volume
        self.bass = 50         # Bass Booster (Punch)
        self.low_cut = 50      # Low Cut-Off High-Pass Filter (50Hz to 250Hz)
        self.low_mid = 50      # Low-Mid Range (250Hz - 500Hz)
        self.mid_upper = 50    # Mid & Upper-Mid Range (500Hz - 4kHz)
        self.treble = 50       # Treble / Highs (4kHz - 20kHz)

        self.device_name = "Detecting Audio Device..."
        self.was_music_active = False

        self.eq_engine = None
        self.bass_engine = None
        self.visualizer = None
        self.wake_lock = None

        self.avg_bass_energy = 0.0
        self.limiter_active = False
        self.dynamic_punch_boost = 0.0
        self.safety_reduction = 0.0

        self.load_settings()

        # Main Layout
        self.main_layout = BoxLayout(orientation='vertical', padding='10dp', spacing='6dp')
        with self.main_layout.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            self.bg_rect = RoundedRectangle(pos=self.main_layout.pos, size=self.main_layout.size)
        self.main_layout.bind(pos=self.update_bg, size=self.update_bg)

        # 1. TOP BAR: Connected Audio Device Name
        device_bar = ProCard(bg_hex='#004d40', size_hint_y=None, height='38dp', padding='6dp')
        self.lbl_device = Label(
            text=f"🔊 Output: {self.device_name}",
            font_size='13sp',
            bold=True,
            color=get_color_from_hex('#64ffda')
        )
        device_bar.add_widget(self.lbl_device)
        self.main_layout.add_widget(device_bar)

        # 2. ALWAYS ON (KILL-PROOF SERVICE) TOGGLE BUTTON
        self.btn_always_on = Button(
            text=self.get_always_on_text(),
            size_hint_y=None,
            height='40dp',
            font_size='13sp',
            bold=True,
            background_normal='',
            background_color=get_color_from_hex('#00c853' if self.always_on else '#d32f2f'),
            color=get_color_from_hex('#0a192f' if self.always_on else '#ffffff')
        )
        self.btn_always_on.bind(on_release=self.toggle_always_on)
        self.main_layout.add_widget(self.btn_always_on)

        # 3. STATUS MONITOR BAR (Live DSP & Limiter status)
        dsp_bar = ProCard(bg_hex='#1e3a5f', size_hint_y=None, height='34dp', padding='4dp')
        self.lbl_status = Label(
            text=self.get_status_text(),
            font_size='11sp',
            bold=True,
            color=get_color_from_hex('#ccd6f6')
        )
        dsp_bar.add_widget(self.lbl_status)
        self.main_layout.add_widget(dsp_bar)

        # 4. 6 SLIDERS CONTAINER
        sliders_box = BoxLayout(orientation='vertical', spacing='6dp')

        self.card_vol, self.lbl_vol_val, self.slider_vol = self.create_slider_card(
            title="1. MASTER VOLUME",
            min_val=0, max_val=100, cur_val=self.volume,
            unit="%", accent_hex='#00e676',
            callback=self.on_volume_change
        )
        sliders_box.add_widget(self.card_vol)

        self.card_bass, self.lbl_bass_val, self.slider_bass = self.create_slider_card(
            title="2. BASS BOOSTER (PUNCH)",
            min_val=0, max_val=100, cur_val=self.bass,
            unit="%", accent_hex='#ff6d00',
            callback=self.on_bass_change
        )
        sliders_box.add_widget(self.card_bass)

        self.card_cut, self.lbl_cut_val, self.slider_cut = self.create_slider_card(
            title="3. LOW CUT-OFF (HPF)",
            min_val=50, max_val=250, cur_val=self.low_cut,
            unit=" Hz", accent_hex='#ffab40',
            callback=self.on_cut_change
        )
        sliders_box.add_widget(self.card_cut)

        self.card_lmid, self.lbl_lmid_val, self.slider_lmid = self.create_slider_card(
            title="4. LOW-MID RANGE (250-500Hz)",
            min_val=0, max_val=100, cur_val=self.low_mid,
            unit="%", accent_hex='#ab47bc',
            callback=self.on_lmid_change
        )
        sliders_box.add_widget(self.card_lmid)

        self.card_mid, self.lbl_mid_val, self.slider_mid = self.create_slider_card(
            title="5. MID & UPPER (VOCAL)",
            min_val=0, max_val=100, cur_val=self.mid_upper,
            unit="%", accent_hex='#26a69a',
            callback=self.on_mid_change
        )
        sliders_box.add_widget(self.card_mid)

        self.card_treble, self.lbl_treble_val, self.slider_treble = self.create_slider_card(
            title="6. TREBLE (CLARITY)",
            min_val=0, max_val=100, cur_val=self.treble,
            unit="%", accent_hex='#00b0ff',
            callback=self.on_treble_change
        )
        sliders_box.add_widget(self.card_treble)

        self.main_layout.add_widget(sliders_box)
        return self.main_layout

    # ==========================================
    # ALWAYS ON SERVICE & BATTERY EXEMPTION
    # ==========================================
    def on_start(self):
        self.acquire_wakelock()
        self.request_battery_unrestricted()
        self.init_audio_engine()
        self.detect_connected_audio_device()
        self.apply_all_audio_data()
        if self.always_on:
            self.start_background_service()
        Clock.schedule_interval(self.background_monitor, 1.5)
        Clock.schedule_interval(self.smart_track_analyzer, 0.1)

    def on_pause(self):
        self.save_settings()
        if self.always_on:
            self.start_background_service()
        return True

    def on_resume(self):
        self.detect_connected_audio_device()
        self.init_audio_engine()
        self.apply_all_audio_data()

    def get_always_on_text(self):
        if self.always_on:
            return "🟢 ALWAYS ON (KILL-PROOF ENGINE): ACTIVE"
        return "🔴 ALWAYS ON (KILL-PROOF ENGINE): OFF"

    def toggle_always_on(self, *args):
        self.always_on = not self.always_on
        self.btn_always_on.text = self.get_always_on_text()
        self.btn_always_on.background_color = get_color_from_hex('#00c853' if self.always_on else '#d32f2f')
        self.btn_always_on.color = get_color_from_hex('#0a192f' if self.always_on else '#ffffff')
        self.save_settings()

        if self.always_on:
            self.request_battery_unrestricted()
            self.start_background_service()
        else:
            self.stop_background_service()

    def start_background_service(self):
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                service = autoclass('com.photon.audio.ServicePhotondsp')
                service.start(activity, "")
            except Exception as e:
                print("Start Service Error:", e)

    def stop_background_service(self):
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                service_class = autoclass('com.photon.audio.ServicePhotondsp')
                intent = Intent(activity, service_class)
                activity.stopService(intent)
            except Exception as e:
                print("Stop Service Error:", e)

    def request_battery_unrestricted(self):
        if platform == 'android' and PowerManager and Settings and Uri:
            try:
                activity = PythonActivity.mActivity
                pm = activity.getSystemService(Context.POWER_SERVICE)
                pkg = activity.getPackageName()
                if not pm.isIgnoringBatteryOptimizations(pkg):
                    intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    intent.setData(Uri.parse(f"package:{pkg}"))
                    activity.startActivity(intent)
            except Exception as e:
                print("Battery Unrestrict Error:", e)

    def acquire_wakelock(self):
        if platform == 'android' and PowerManager:
            try:
                activity = PythonActivity.mActivity
                pm = activity.getSystemService(Context.POWER_SERVICE)
                self.wake_lock = pm.newWakeLock(1, "PhotonAudio::6BandWakeLock")
                if not self.wake_lock.isHeld():
                    self.wake_lock.acquire()
            except Exception as e:
                print("WakeLock Error:", e)

    # ==========================================
    # AUDIO ENGINE INIT & SMART ANALYZER
    # ==========================================
    def init_audio_engine(self):
        if platform == 'android':
            try:
                if self.eq_engine is None:
                    self.eq_engine = Equalizer(100, 0)
                    self.eq_engine.setEnabled(True)
                if self.bass_engine is None:
                    self.bass_engine = BassBoost(100, 0)
                    self.bass_engine.setEnabled(True)
                if self.visualizer is None and Visualizer:
                    self.visualizer = Visualizer(0)
                    self.visualizer.setCaptureSize(128)
                    self.visualizer.setEnabled(True)
            except Exception as e:
                print("AudioFX Init Error:", e)

    def smart_track_analyzer(self, dt):
        if platform != 'android' or not self.visualizer or not self.was_music_active:
            return

        try:
            fft_bytes = bytearray(128)
            status = self.visualizer.getFft(fft_bytes)
            if status != 0:
                return

            low_energy = 0.0
            for i in range(2, 12, 2):
                real = fft_bytes[i]
                imag = fft_bytes[i + 1]
                if real > 127:
                    real -= 256
                if imag > 127:
                    imag -= 256
                mag = (real * real + imag * imag) ** 0.5
                low_energy += mag

            low_energy = low_energy / 5.0
            self.avg_bass_energy = (self.avg_bass_energy * 0.88) + (low_energy * 0.12)

            beat_delta = low_energy - self.avg_bass_energy
            if beat_delta > 14.0 and self.bass > 0:
                self.dynamic_punch_boost = min(200.0, beat_delta * (self.bass / 45.0))
            else:
                self.dynamic_punch_boost *= 0.55

            overload_threshold = 72.0
            if self.avg_bass_energy > overload_threshold and self.bass > 55:
                self.limiter_active = True
                excess = self.avg_bass_energy - overload_threshold
                self.safety_reduction = min(350.0, excess * 5.5 * (self.bass / 100.0))
            else:
                self.limiter_active = False
                self.safety_reduction *= 0.7

            self.apply_dynamic_dsp()
        except Exception:
            pass

    def apply_dynamic_dsp(self):
        if platform != 'android':
            return
        try:
            base_strength = self.bass * 6.5
            final_strength = int(base_strength + self.dynamic_punch_boost - self.safety_reduction)
            final_strength = max(0, min(1000, final_strength))

            if self.bass_engine:
                self.bass_engine.setStrength(final_strength)

            self.lbl_status.text = self.get_status_text()
        except Exception:
            pass

    # ==========================================
    # APPLY PRO 6-BAND EQUALIZER CURVE
    # ==========================================
    def apply_all_audio_data(self):
        self.lbl_status.text = self.get_status_text()
        self.save_settings()

        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)

                max_vol = audio_manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                target_vol = int((self.volume / 100.0) * max_vol)
                audio_manager.setStreamVolume(AudioManager.STREAM_MUSIC, target_vol, 0)

                self.apply_dynamic_dsp()

                if self.eq_engine:
                    num_bands = self.eq_engine.getNumberOfBands()
                    level_range = self.eq_engine.getBandLevelRange()
                    min_lvl = level_range[0]
                    max_lvl = level_range[1]

                    cutoff_milli = self.low_cut * 1000
                    bass_ratio = self.bass / 100.0
                    lmid_ratio = (self.low_mid - 50) / 50.0
                    mid_ratio = (self.mid_upper - 50) / 50.0
                    treble_ratio = (self.treble - 50) / 50.0

                    for b in range(num_bands):
                        freq_range = self.eq_engine.getBandFreqRange(b)
                        low_f = freq_range[0]
                        high_f = freq_range[1]
                        center_f = self.eq_engine.getCenterFreq(b)

                        if high_f <= cutoff_milli:
                            self.eq_engine.setBandLevel(b, min_lvl)
                        elif low_f < cutoff_milli < high_f:
                            above_ratio = (high_f - cutoff_milli) / float(high_f - low_f)
                            if above_ratio < 0.4:
                                lvl = int(min_lvl * (1.0 - above_ratio))
                            else:
                                lvl = int(max_lvl * 0.7 * bass_ratio * above_ratio)
                            self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, lvl)))
                        else:
                            if center_f <= 180000:
                                punch_lvl = int(max_lvl * 0.85 * bass_ratio)
                                if self.limiter_active:
                                    punch_lvl = int(punch_lvl * 0.72)
                                self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, punch_lvl)))
                            elif 240000 <= center_f <= 500000:
                                lmid_lvl = int(max_lvl * 0.6 * lmid_ratio)
                                self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, lmid_lvl)))
                            elif 500000 < center_f < 4000000:
                                mid_lvl = int(max_lvl * 0.6 * mid_ratio)
                                self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, mid_lvl)))
                            else:
                                treble_lvl = int(max_lvl * treble_ratio)
                                self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, treble_lvl)))

            except Exception as e:
                print("Apply Audio Data Error:", e)

    # ==========================================
    # DEVICE DETECTION & MONITOR
    # ==========================================
    def detect_connected_audio_device(self):
        if platform != 'android':
            self.device_name = "PC / Simulated Speaker"
            self.lbl_device.text = f"🔊 Output: {self.device_name}"
            return

        detected = "Phone Speaker"
        try:
            activity = PythonActivity.mActivity
            audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
            devices = audio_manager.getDevices(2)
            if devices:
                for dev in devices:
                    dev_type = dev.getType()
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
            self.apply_all_audio_data()

    def background_monitor(self, dt):
        self.detect_connected_audio_device()

        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
                is_playing = audio_manager.isMusicActive()

                if is_playing and not self.was_music_active:
                    self.init_audio_engine()
                    self.apply_all_audio_data()

                self.was_music_active = is_playing
                play_state = "🎵 Active" if is_playing else "⏸ Idle"
                self.lbl_device.text = f"🔊 {self.device_name}  [{play_state}]"
            except Exception as e:
                print("Monitor Error:", e)

    # ==========================================
    # UI HELPERS & SLIDER CALLBACKS
    # ==========================================
    def update_bg(self, instance, *args):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def create_slider_card(self, title, min_val, max_val, cur_val, unit, accent_hex, callback):
        card = ProCard(orientation='vertical', padding=['12dp', '5dp'], spacing='2dp')

        top_row = BoxLayout(orientation='horizontal', size_hint_y=0.42)
        lbl_title = Label(
            text=title,
            font_size='12sp',
            bold=True,
            color=get_color_from_hex('#ccd6f6'),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))

        lbl_val = Label(
            text=f"{int(cur_val)}{unit}",
            font_size='15sp',
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
            cursor_size=('28dp', '28dp'),
            background_width='14dp',
            value_track=True,
            value_track_color=get_color_from_hex(accent_hex),
            value_track_width='5dp',
            size_hint_y=0.58
        )
        slider.bind(value=callback)

        card.add_widget(top_row)
        card.add_widget(slider)
        return card, lbl_val, slider

    def get_status_text(self):
        guard_tag = "🛡️ LIMITER" if self.limiter_active else "⚡ DYNAMIC"
        return f"CUT: <{self.low_cut}Hz | PUNCH: {self.bass}% | LM:{self.low_mid}% | MID:{self.mid_upper}% | TR:{self.treble}% | {guard_tag}"

    def on_volume_change(self, instance, value):
        self.volume = int(value)
        self.lbl_vol_val.text = f"{self.volume}%"
        self.apply_all_audio_data()

    def on_bass_change(self, instance, value):
        self.bass = int(value)
        self.lbl_bass_val.text = f"{self.bass}%"
        self.apply_all_audio_data()

    def on_cut_change(self, instance, value):
        self.low_cut = int(value)
        self.lbl_cut_val.text = f"{self.low_cut} Hz"
        self.apply_all_audio_data()

    def on_lmid_change(self, instance, value):
        self.low_mid = int(value)
        self.lbl_lmid_val.text = f"{self.low_mid}%"
        self.apply_all_audio_data()

    def on_mid_change(self, instance, value):
        self.mid_upper = int(value)
        self.lbl_mid_val.text = f"{self.mid_upper}%"
        self.apply_all_audio_data()

    def on_treble_change(self, instance, value):
        self.treble = int(value)
        self.lbl_treble_val.text = f"{self.treble}%"
        self.apply_all_audio_data()

    # ==========================================
    # SHARED SETTINGS FILE (READ BY BACKGROUND SERVICE)
    # ==========================================
    def get_settings_path(self):
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                return os.path.join(activity.getFilesDir().getAbsolutePath(), 'audio_eq_settings.json')
            except Exception:
                pass
        return 'audio_eq_settings.json'

    def save_settings(self):
        data = {
            'always_on': self.always_on,
            'volume': self.volume,
            'bass': self.bass,
            'low_cut': self.low_cut,
            'low_mid': self.low_mid,
            'mid_upper': self.mid_upper,
            'treble': self.treble
        }
        try:
            with open(self.get_settings_path(), 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def load_settings(self):
        path = self.get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.always_on = data.get('always_on', True)
                    self.volume = data.get('volume', 50)
                    self.bass = data.get('bass', 50)
                    self.low_cut = data.get('low_cut', 50)
                    self.low_mid = data.get('low_mid', 50)
                    self.mid_upper = data.get('mid_upper', 50)
                    self.treble = data.get('treble', 50)
            except Exception:
                pass


if __name__ == "__main__":
    AudioControllerApp().run()
