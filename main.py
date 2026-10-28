import json
import os
import math
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp

PythonActivity = None
Context = None
AudioManager = None
Equalizer = None
BassBoost = None
Virtualizer = None
LoudnessEnhancer = None
Visualizer = None
PowerManager = None
Intent = None
Settings = None
Uri = None
Build = None

if platform == 'android':
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        AudioManager = autoclass('android.media.AudioManager')
        Equalizer = autoclass('android.media.audiofx.Equalizer')
        BassBoost = autoclass('android.media.audiofx.BassBoost')
        Virtualizer = autoclass('android.media.audiofx.Virtualizer')
        LoudnessEnhancer = autoclass('android.media.audiofx.LoudnessEnhancer')
        Visualizer = autoclass('android.media.audiofx.Visualizer')
        PowerManager = autoclass('android.os.PowerManager')
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        Uri = autoclass('android.net.Uri')
        Build = autoclass('android.os.Build')
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


class AudioWaveWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.time = 0
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        Clock.schedule_interval(self.animate, 1 / 30.0)

    def animate(self, dt):
        self.time += dt
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        if self.width < 10 or self.height < 10:
            return

        with self.canvas:
            colors = ['#00e676', '#00b0ff', '#ff6d00']
            amps = [0.25, 0.15, 0.35]
            speeds = [4.0, 6.5, 3.5]
            phases = [0, 1.5, 3.0]

            for i in range(3):
                Color(rgba=get_color_from_hex(colors[i]))
                pts = []
                step = max(2, int(self.width / 60))
                for x in range(0, int(self.width), step):
                    y = (self.height / 2) + math.sin((x / self.width) * 10 + self.time * speeds[i] + phases[i]) * (self.height * amps[i])
                    pts.extend([self.x + x, self.y + y])
                Line(points=pts, width=1.5)


class SettingsPopup(ModalView):
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.size_hint = (0.92, 0.85)
        self.background_color = (0, 0, 0, 0.7)
        self.auto_dismiss = False

        root = ProCard(bg_hex='#0a192f', orientation='vertical', padding='12dp', spacing='10dp')
        self.add_widget(root)

        title_lbl = Label(
            text="⚙️ ADVANCED DSP SETTINGS",
            size_hint_y=None, height='40dp',
            font_size='16sp', bold=True,
            color=get_color_from_hex('#64ffda')
        )
        root.add_widget(title_lbl)

        sliders_box = BoxLayout(orientation='vertical', spacing='10dp', size_hint_y=None, height=dp(420))

        self.card_cut, self.lbl_cut_val, self.slider_cut = self.app.create_slider_card(
            title="3. LOW CUT-OFF & AUTO-BASS (HPF)",
            min_val=50, max_val=250, cur_val=self.app.low_cut,
            unit=" Hz", accent_hex='#ffab40',
            callback=self.app.on_cut_change
        )
        sliders_box.add_widget(self.card_cut)

        self.card_lmid, self.lbl_lmid_val, self.slider_lmid = self.app.create_slider_card(
            title="4. LOW-MID AMPLITUDE (250-500Hz)",
            min_val=0, max_val=100, cur_val=self.app.low_mid,
            unit="%", accent_hex='#ab47bc',
            callback=self.app.on_lmid_change
        )
        sliders_box.add_widget(self.card_lmid)

        self.card_mid, self.lbl_mid_val, self.slider_mid = self.app.create_slider_card(
            title="5. MID & UPPER (VOCAL)",
            min_val=0, max_val=100, cur_val=self.app.mid_upper,
            unit="%", accent_hex='#26a69a',
            callback=self.app.on_mid_change
        )
        sliders_box.add_widget(self.card_mid)

        self.card_treble, self.lbl_treble_val, self.slider_treble = self.app.create_slider_card(
            title="6. TREBLE (CLARITY)",
            min_val=0, max_val=100, cur_val=self.app.treble,
            unit="%", accent_hex='#00b0ff',
            callback=self.app.on_treble_change
        )
        sliders_box.add_widget(self.card_treble)

        root.add_widget(sliders_box)
        root.add_widget(Widget())

        btn_save = Button(
            text="💾 SAVE & CLOSE",
            size_hint_y=None, height='50dp',
            font_size='15sp', bold=True,
            background_normal='',
            background_color=get_color_from_hex('#00c853'),
            color=get_color_from_hex('#0a192f')
        )
        btn_save.bind(on_release=self.save_and_close)
        root.add_widget(btn_save)

    def save_and_close(self, *args):
        self.app.save_settings()
        self.app.apply_all_audio_data()
        self.dismiss()


class AudioControllerApp(App):
    def build(self):
        self.title = "Photon Audio"
        self.always_on = True
        self.volume = 50
        self.bass = 50
        self.low_cut = 50
        self.low_mid = 50
        self.mid_upper = 50
        self.treble = 50
        self.device_name = "Detecting Audio Device..."
        self.was_music_active = False
        self.in_foreground = True

        self.eq_engine = None
        self.bass_engine = None
        self.virtualizer_engine = None
        self.loudness_engine = None
        self.visualizer = None
        self.wake_lock = None

        self.avg_bass_energy = 0.0
        self.avg_lmid_energy = 0.0
        self.limiter_active = False
        self.bass_synth_active = False
        self.dynamic_punch_boost = 0.0
        self.bass_restorer_boost = 0.0
        self.lmid_restorer_boost = 0.0
        self.safety_reduction = 0.0

        self.update_event = None
        self.load_settings()

        root = BoxLayout(orientation='vertical', padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8))
        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        device_bar = ProCard(bg_hex='#004d40', size_hint_y=None, height=dp(40), padding=dp(6))
        self.lbl_device = Label(
            text=f"🔊 Output: {self.device_name}",
            font_size='13sp', bold=True, color=get_color_from_hex('#64ffda')
        )
        device_bar.add_widget(self.lbl_device)
        root.add_widget(device_bar)

        self.btn_always_on = Button(
            text=self.get_always_on_text(),
            size_hint_y=None, height=dp(42),
            font_size='13sp', bold=True, background_normal='',
            background_color=get_color_from_hex('#00c853' if self.always_on else '#d32f2f'),
            color=get_color_from_hex('#0a192f' if self.always_on else '#ffffff')
        )
        self.btn_always_on.bind(on_release=self.toggle_always_on)
        root.add_widget(self.btn_always_on)

        dsp_bar = ProCard(bg_hex='#1e3a5f', size_hint_y=None, height=dp(36), padding=dp(4))
        self.lbl_status = Label(
            text=self.get_status_text(),
            font_size='11sp', bold=True, color=get_color_from_hex('#ccd6f6')
        )
        dsp_bar.add_widget(self.lbl_status)
        root.add_widget(dsp_bar)

        btn_settings = Button(
            text="⚙️ ADVANCED DSP SETTINGS",
            size_hint_y=None, height=dp(48),
            font_size='14sp', bold=True, background_normal='',
            background_color=get_color_from_hex('#26a69a'),
            color=get_color_from_hex('#0a192f')
        )
        btn_settings.bind(on_release=self.open_settings)
        root.add_widget(btn_settings)

        self.audio_wave = AudioWaveWidget(size_hint_y=1)
        root.add_widget(self.audio_wave)

        self.card_vol, self.lbl_vol_val, self.slider_vol = self.create_slider_card(
            title="1. MASTER VOLUME",
            min_val=0, max_val=100, cur_val=self.volume,
            unit="%", accent_hex='#00e676',
            callback=self.on_volume_change
        )
        root.add_widget(self.card_vol)

        self.card_bass, self.lbl_bass_val, self.slider_bass = self.create_slider_card(
            title="2. BASS BOOSTER (+30% AMP POWER)",
            min_val=0, max_val=100, cur_val=self.bass,
            unit="%", accent_hex='#ff6d00',
            callback=self.on_bass_change
        )
        root.add_widget(self.card_bass)

        branding_box = BoxLayout(orientation='vertical', size_hint_y=1, spacing=dp(2))
        branding_box.add_widget(Widget())

        lbl_logo = Label(
            text="PHOTON AUDIO", font_size='22sp', bold=True,
            color=get_color_from_hex('#64ffda'), halign='center'
        )
        lbl_sub = Label(
            text="ULTIMATE DSP ENGINE", font_size='11sp',
            color=get_color_from_hex('#8892b0'), halign='center'
        )
        branding_box.add_widget(lbl_logo)
        branding_box.add_widget(lbl_sub)
        branding_box.add_widget(Widget())
        root.add_widget(branding_box)

        return root

    def open_settings(self, *args):
        popup = SettingsPopup(self)
        popup.open()

    def _update_bg(self, instance, *args):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def create_slider_card(self, title, min_val, max_val, cur_val, unit, accent_hex, callback):
        card = ProCard(orientation='vertical', padding=['12dp', '8dp'], spacing='4dp')
        card.size_hint_y = None
        card.height = dp(95)

        top_row = BoxLayout(orientation='horizontal', size_hint_y=0.4)
        lbl_title = Label(
            text=title, font_size='12sp', bold=True,
            color=get_color_from_hex('#ccd6f6'), halign='left', valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))

        lbl_val = Label(
            text=f"{int(cur_val)}{unit}", font_size='15sp', bold=True,
            color=get_color_from_hex(accent_hex), size_hint_x=0.35,
            halign='right', valign='middle'
        )
        lbl_val.bind(size=lbl_val.setter('text_size'))

        top_row.add_widget(lbl_title)
        top_row.add_widget(lbl_val)

        slider = Slider(
            min=min_val, max=max_val, value=cur_val, step=1,
            cursor_size=('28dp', '28dp'), background_width='14dp',
            value_track=True, value_track_color=get_color_from_hex(accent_hex),
            value_track_width='5dp', size_hint_y=0.6
        )

        def on_value(instance, value):
            lbl_val.text = f"{int(value)}{unit}"
            callback(instance, value)

        slider.bind(value=on_value)

        card.add_widget(top_row)
        card.add_widget(slider)
        return card, lbl_val, slider

    # ==========================================
    # LIFECYCLE & ALWAYS ON SERVICE
    # ==========================================
    def on_start(self):
        self.in_foreground = True
        Clock.schedule_once(self.request_android_permissions, 0.5)
        self.acquire_wakelock()
        self.request_battery_unrestricted()
        self.init_audio_engine()
        self.detect_connected_audio_device()
        self.apply_all_audio_data()
        if self.always_on:
            self.start_background_service()
        Clock.schedule_interval(self.background_monitor, 1.5)
        Clock.schedule_interval(self.smart_track_analyzer, 0.1)
        Clock.schedule_interval(self.service_health_check, 20)

    def request_android_permissions(self, dt):
        if platform == 'android':
            try:
                from android.permissions import request_permissions
                request_permissions([
                    'android.permission.BLUETOOTH_CONNECT',
                    'android.permission.BLUETOOTH_SCAN',
                    'android.permission.MODIFY_AUDIO_SETTINGS',
                    'android.permission.RECORD_AUDIO',
                    'android.permission.POST_NOTIFICATIONS'
                ])
            except Exception as e:
                print("Permission request error:", e)

    def on_pause(self):
        self.in_foreground = False
        self.save_settings()
        if self.always_on:
            # મેઈન એપના ઓડિયો એન્જિન રીલીઝ કરો જેથી બેકગ્રાઉન્ડ સર્વિસને 100% કંટ્રોલ મળે
            self.release_audio_engine()
            self.start_background_service()
        return True

    def on_resume(self):
        self.in_foreground = True
        self.detect_connected_audio_device()
        self.init_audio_engine()
        self.apply_all_audio_data()
        if self.always_on:
            self.start_background_service()

    def get_always_on_text(self):
        return "🟢 ALWAYS ON (KILL-PROOF): ACTIVE" if self.always_on else "🔴 ALWAYS ON (KILL-PROOF): OFF"

    def toggle_always_on(self, *args):
        self.always_on = not self.always_on
        self.btn_always_on.text = self.get_always_on_text()
        self.btn_always_on.background_color = get_color_from_hex('#00c853' if self.always_on else '#d32f2f')
        self.btn_always_on.color = get_color_from_hex('#0a192f' if self.always_on else '#ffffff')
        self.save_settings()

        if self.always_on:
            self.request_battery_unrestricted()
            self.start_background_service(force=True)
        else:
            self.stop_background_service()

    def is_service_running(self):
        if platform != 'android':
            return False
        try:
            activity = PythonActivity.mActivity
            am = activity.getSystemService(Context.ACTIVITY_SERVICE)
            target = "com.photon.audio.ServicePhotondsp"
            running = am.getRunningServices(100)
            if running:
                for svc in running.toArray():
                    if str(svc.service.getClassName()) == target:
                        return True
        except Exception as e:
            print("Service check error:", e)
        return False

    def start_background_service(self, force=False):
        if platform != 'android':
            return
        try:
            if not force and self.is_service_running():
                return
            activity = PythonActivity.mActivity
            service_class = autoclass('com.photon.audio.ServicePhotondsp')
            title = "Photon Audio EQ Active"
            info = f"Bass:{self.bass}% | Cut:<{self.low_cut}Hz | L-Mid:{self.low_mid}% | Treble:{self.treble}%"
            try:
                service_class.start(activity, 'icon', title, info, '')
            except Exception:
                service_class.start(activity, '')
        except Exception as e:
            print("Start Service Error:", e)

    def stop_background_service(self):
        if platform != 'android':
            return
        try:
            activity = PythonActivity.mActivity
            service_class = autoclass('com.photon.audio.ServicePhotondsp')
            intent = Intent(activity, service_class)
            activity.stopService(intent)
        except Exception as e:
            print("Stop Service Error:", e)

    def service_health_check(self, dt):
        if self.always_on and platform == 'android':
            if not self.is_service_running():
                self.start_background_service(force=True)

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
    # AUDIO & DSP
    # ==========================================
    def release_audio_engine(self):
        for attr in ('visualizer', 'eq_engine', 'bass_engine', 'virtualizer_engine', 'loudness_engine'):
            eng = getattr(self, attr, None)
            if eng is not None:
                try:
                    eng.release()
                except Exception:
                    pass
                setattr(self, attr, None)

    def init_audio_engine(self):
        if platform != 'android' or not self.in_foreground:
            return
        try:
            if self.eq_engine is None or not self.eq_engine.hasControl():
                if self.eq_engine:
                    try: self.eq_engine.release()
                    except Exception: pass
                self.eq_engine = Equalizer(100, 0)
            self.eq_engine.setEnabled(True)
        except Exception:
            self.eq_engine = None

        try:
            if self.bass_engine is None or not self.bass_engine.hasControl():
                if self.bass_engine:
                    try: self.bass_engine.release()
                    except Exception: pass
                self.bass_engine = BassBoost(100, 0)
            self.bass_engine.setEnabled(True)
        except Exception:
            self.bass_engine = None

        try:
            if Virtualizer and (self.virtualizer_engine is None or not self.virtualizer_engine.hasControl()):
                if self.virtualizer_engine:
                    try: self.virtualizer_engine.release()
                    except Exception: pass
                self.virtualizer_engine = Virtualizer(100, 0)
            if self.virtualizer_engine:
                self.virtualizer_engine.setEnabled(True)
        except Exception:
            self.virtualizer_engine = None

        try:
            if LoudnessEnhancer and (self.loudness_engine is None or not self.loudness_engine.hasControl()):
                if self.loudness_engine:
                    try: self.loudness_engine.release()
                    except Exception: pass
                self.loudness_engine = LoudnessEnhancer(0)
            if self.loudness_engine:
                self.loudness_engine.setEnabled(True)
        except Exception:
            self.loudness_engine = None

        try:
            if Visualizer and self.visualizer is None:
                self.visualizer = Visualizer(0)
                self.visualizer.setCaptureSize(128)
                self.visualizer.setEnabled(True)
        except Exception:
            self.visualizer = None

    def smart_track_analyzer(self, dt):
        if platform != 'android' or not self.in_foreground or not self.visualizer or not self.was_music_active:
            return
        try:
            fft_bytes = bytearray(128)
            if self.visualizer.getFft(fft_bytes) != 0:
                return

            low_energy = 0.0
            for i in range(2, 12, 2):
                real = fft_bytes[i] - 256 if fft_bytes[i] > 127 else fft_bytes[i]
                imag = fft_bytes[i + 1] - 256 if fft_bytes[i + 1] > 127 else fft_bytes[i + 1]
                low_energy += (real * real + imag * imag) ** 0.5
            low_energy /= 5.0

            lmid_energy = 0.0
            for i in range(12, 26, 2):
                real = fft_bytes[i] - 256 if fft_bytes[i] > 127 else fft_bytes[i]
                imag = fft_bytes[i + 1] - 256 if fft_bytes[i + 1] > 127 else fft_bytes[i + 1]
                lmid_energy += (real * real + imag * imag) ** 0.5
            lmid_energy /= 7.0

            self.avg_bass_energy = (self.avg_bass_energy * 0.85) + (low_energy * 0.15)
            self.avg_lmid_energy = (self.avg_lmid_energy * 0.85) + (lmid_energy * 0.15)

            beat_delta = low_energy - self.avg_bass_energy
            if beat_delta > 11.0 and self.bass > 0:
                self.dynamic_punch_boost = min(300.0, beat_delta * (self.bass / 32.0))
            else:
                self.dynamic_punch_boost *= 0.60

            if 2.0 < self.avg_bass_energy < 38.0 and self.bass > 20:
                self.bass_synth_active = True
                deficit = 38.0 - self.avg_bass_energy
                self.bass_restorer_boost = min(280.0, deficit * 7.5 * (self.bass / 100.0))
            else:
                self.bass_synth_active = False
                self.bass_restorer_boost *= 0.75

            if 1.5 < self.avg_lmid_energy < 30.0 and self.low_mid > 50:
                lmid_deficit = 30.0 - self.avg_lmid_energy
                self.lmid_restorer_boost = min(0.45, (lmid_deficit / 30.0) * ((self.low_mid - 50) / 50.0))
            else:
                self.lmid_restorer_boost *= 0.80

            if self.avg_bass_energy > 85.0 and self.bass > 65:
                self.limiter_active = True
                excess = self.avg_bass_energy - 85.0
                self.safety_reduction = min(300.0, excess * 4.5 * (self.bass / 100.0))
            else:
                self.limiter_active = False
                self.safety_reduction *= 0.70

            self.apply_dynamic_dsp()
        except Exception:
            pass

    def apply_dynamic_dsp(self):
        if platform != 'android' or not self.in_foreground:
            return
        try:
            base_strength = self.bass * 9.5
            final_strength = int(base_strength + self.dynamic_punch_boost + self.bass_restorer_boost - self.safety_reduction)
            final_strength = max(0, min(1000, final_strength))

            if self.bass_engine and self.bass_engine.hasControl():
                self.bass_engine.setStrength(final_strength)

            if self.loudness_engine and self.loudness_engine.hasControl():
                amp_boost_mb = int((self.bass * 7.5) + (self.bass_restorer_boost * 1.5) - self.safety_reduction)
                self.loudness_engine.setTargetGain(max(0, min(900, amp_boost_mb)))

            if self.virtualizer_engine and self.virtualizer_engine.hasControl():
                self.virtualizer_engine.setStrength(int(self.low_mid * 10))

            if hasattr(self, 'lbl_status'):
                self.lbl_status.text = self.get_status_text()
        except Exception:
            pass

    def schedule_audio_update(self):
        if self.update_event:
            self.update_event.cancel()
        self.update_event = Clock.schedule_once(self._do_audio_update, 0.12)

    def _do_audio_update(self, dt):
        self.save_settings()
        self.apply_all_audio_data()

    def apply_all_audio_data(self):
        if hasattr(self, 'lbl_status'):
            self.lbl_status.text = self.get_status_text()
        if platform != 'android' or not self.in_foreground:
            return
        try:
            activity = PythonActivity.mActivity
            audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
            max_vol = audio_manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            audio_manager.setStreamVolume(AudioManager.STREAM_MUSIC, int((self.volume / 100.0) * max_vol), 0)
            self.init_audio_engine()
            self.apply_dynamic_dsp()

            if self.eq_engine and self.eq_engine.hasControl():
                num_bands = self.eq_engine.getNumberOfBands()
                level_range = self.eq_engine.getBandLevelRange()
                min_lvl, max_lvl = level_range[0], level_range[1]

                cutoff_milli = self.low_cut * 1000
                bass_drive = min(1.35, (self.bass / 100.0) * 1.30)
                lmid_amp = (self.low_mid - 50) / 50.0
                mid_ratio = (self.mid_upper - 50) / 50.0
                treble_ratio = (self.treble - 50) / 50.0
                synth_extra = 0.30 if self.bass_synth_active else 0.0

                for b in range(num_bands):
                    freq_range = self.eq_engine.getBandFreqRange(b)
                    low_f, high_f = freq_range[0], freq_range[1]
                    center_f = self.eq_engine.getCenterFreq(b)

                    if 150000 <= center_f <= 550000:
                        if high_f <= cutoff_milli:
                            self.eq_engine.setBandLevel(b, min_lvl)
                        else:
                            eff = max(-1.0, min(1.0, lmid_amp + self.lmid_restorer_boost))
                            lvl = int(max_lvl * eff) if eff >= 0 else int(abs(eff) * min_lvl)
                            self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, lvl)))
                    elif center_f < 150000:
                        if high_f <= cutoff_milli:
                            self.eq_engine.setBandLevel(b, min_lvl)
                        elif low_f < cutoff_milli < high_f:
                            above_ratio = (high_f - cutoff_milli) / float(high_f - low_f)
                            if above_ratio < 0.28 and not self.bass_synth_active:
                                lvl = int(min_lvl * (1.0 - above_ratio))
                            else:
                                boost = min(1.0, (bass_drive + synth_extra) * max(0.65, above_ratio))
                                lvl = int(max_lvl * boost)
                            self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, lvl)))
                        else:
                            punch = int(max_lvl * min(1.0, bass_drive + synth_extra))
                            if self.limiter_active:
                                punch = int(punch * 0.78)
                            self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, punch)))
                    elif 550000 < center_f < 4000000:
                        coupled = max(-1.0, min(1.0, (mid_ratio * 0.75) + (lmid_amp * 0.35)))
                        self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, int(max_lvl * 0.70 * coupled))))
                    else:
                        self.eq_engine.setBandLevel(b, max(min_lvl, min(max_lvl, int(max_lvl * treble_ratio))))
        except Exception as e:
            print("Apply Audio Data Error:", e)

    def detect_connected_audio_device(self):
        if platform != 'android':
            self.device_name = "PC / Simulated Speaker"
            if hasattr(self, 'lbl_device'):
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
            if hasattr(self, 'lbl_device'):
                self.lbl_device.text = f"🔊 Output: {self.device_name}"
            self.apply_all_audio_data()

    def background_monitor(self, dt):
        if not self.in_foreground:
            return
        self.detect_connected_audio_device()
        if platform != 'android':
            return
        try:
            activity = PythonActivity.mActivity
            audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
            is_playing = audio_manager.isMusicActive()

            if is_playing and not self.was_music_active:
                self.init_audio_engine()
                self.apply_all_audio_data()

            self.was_music_active = is_playing
            state = "🎵 Active" if is_playing else "⏸ Idle"
            if hasattr(self, 'lbl_device'):
                self.lbl_device.text = f"🔊 {self.device_name}  [{state}]"
        except Exception as e:
            print("Monitor Error:", e)

    def get_status_text(self):
        tag = "🛡️ LIMITER" if self.limiter_active else ("🔥 AUTO-BASS ADD" if self.bass_synth_active else "⚡ +30% AMP PUNCH")
        return f"CUT:<{self.low_cut}Hz | BASS:{self.bass}% | LM:{self.low_mid}% | {tag}"

    # ==========================================
    # SLIDER CALLBACKS
    # ==========================================
    def on_volume_change(self, instance, value):
        self.volume = int(value)
        self.schedule_audio_update()

    def on_bass_change(self, instance, value):
        self.bass = int(value)
        self.schedule_audio_update()

    def on_cut_change(self, instance, value):
        self.low_cut = int(value)
        self.schedule_audio_update()

    def on_lmid_change(self, instance, value):
        self.low_mid = int(value)
        self.schedule_audio_update()

    def on_mid_change(self, instance, value):
        self.mid_upper = int(value)
        self.schedule_audio_update()

    def on_treble_change(self, instance, value):
        self.treble = int(value)
        self.schedule_audio_update()

    # ==========================================
    # SETTINGS FILE
    # ==========================================
    def get_settings_path(self):
        if platform == 'android':
            try:
                return os.path.join(PythonActivity.mActivity.getFilesDir().getAbsolutePath(), 'audio_eq_settings.json')
            except Exception:
                pass
        return 'audio_eq_settings.json'

    def save_settings(self):
        data = {
            'always_on': self.always_on, 'volume': self.volume, 'bass': self.bass,
            'low_cut': self.low_cut, 'low_mid': self.low_mid,
            'mid_upper': self.mid_upper, 'treble': self.treble
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
