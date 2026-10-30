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
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp

PythonActivity = None
Context = None
AudioManager = None
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


class HardwareEqPopup(ModalView):
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.size_hint = (0.92, 0.85)
        self.background_color = (0, 0, 0, 0.8)
        self.auto_dismiss = False

        root = ProCard(bg_hex='#0a192f', orientation='vertical', padding='12dp', spacing='8dp')
        self.add_widget(root)

        title_lbl = Label(
            text="📱 HARDWARE EQ BANDS", size_hint_y=None, height='40dp',
            font_size='16sp', bold=True, color=get_color_from_hex('#b388ff')
        )
        root.add_widget(title_lbl)

        if not self.app.hw_bands:
            self.app.hw_bands = self.app.detect_hardware_bands()

        if not self.app.hw_bands:
            err_lbl = Label(
                text="❌ Hardware EQ Not Detected!", halign='center',
                valign='middle', color=get_color_from_hex('#ff5252')
            )
            root.add_widget(err_lbl)
        else:
            scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
            scroll_layout = BoxLayout(orientation='vertical', spacing='8dp', size_hint_y=None)
            scroll_layout.bind(minimum_height=scroll_layout.setter('height'))

            for band_idx, freq in self.app.hw_bands:
                freq_str = f"{int(freq)} Hz" if freq < 1000 else f"{freq/1000.0:.1f} kHz"
                current_val = self.app.hw_eq_levels.get(str(band_idx), 50)
                current_db = (current_val - 50) * 0.3

                card = ProCard(orientation='vertical', padding=['12dp', '6dp'], spacing='4dp', size_hint_y=None, height=dp(82))
                top_row = BoxLayout(orientation='horizontal', size_hint_y=0.4)

                lbl_title = Label(
                    text=f"Band {band_idx+1} ({freq_str})", font_size='12sp', bold=True,
                    color=get_color_from_hex('#ccd6f6'), halign='left', valign='middle'
                )
                lbl_title.bind(size=lbl_title.setter('text_size'))
                lbl_val = Label(
                    text=f"{current_db:+.1f} dB", font_size='15sp', bold=True,
                    color=get_color_from_hex('#b388ff'), size_hint_x=0.35, halign='right', valign='middle'
                )
                lbl_val.bind(size=lbl_val.setter('text_size'))

                top_row.add_widget(lbl_title)
                top_row.add_widget(lbl_val)

                slider = Slider(
                    min=0, max=100, value=current_val, step=1, cursor_size=('28dp', '28dp'),
                    background_width='14dp', value_track=True, value_track_color=get_color_from_hex('#b388ff'),
                    value_track_width='5dp', size_hint_y=0.6
                )

                def make_callback(idx, label_widget):
                    def on_value(instance, value):
                        db_val = (int(value) - 50) * 0.3
                        label_widget.text = f"{db_val:+.1f} dB"
                        self.app.on_hw_slider_change(idx, value)
                    return on_value

                slider.bind(value=make_callback(band_idx, lbl_val))
                card.add_widget(top_row)
                card.add_widget(slider)
                scroll_layout.add_widget(card)

            scroll.add_widget(scroll_layout)
            root.add_widget(scroll)

        btn_close = Button(
            text="💾 SAVE & CLOSE", size_hint_y=None, height='48dp',
            font_size='15sp', bold=True, background_normal='',
            background_color=get_color_from_hex('#00c853'), color=get_color_from_hex('#0a192f')
        )
        btn_close.bind(on_release=self.save_and_close)
        root.add_widget(btn_close)

    def save_and_close(self, *args):
        self.app.save_settings()
        self.dismiss()


class AudioControllerApp(App):
    def build(self):
        self.title = "Photon Audio"
        self.volume = 70
        self.bass = 15

        self.hw_bands = self.detect_hardware_bands()
        self.hw_eq_levels = {}

        self.device_name = "Detecting Audio Device..."
        self.in_foreground = True
        self._save_ev = None

        self.load_settings()

        root = BoxLayout(orientation='vertical', padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8))
        with root.canvas.before:
            Color(rgba=get_color_from_hex('#0a192f'))
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        device_bar = ProCard(bg_hex='#004d40', size_hint_y=None, height=dp(40), padding=dp(6))
        self.lbl_device = Label(
            text=f"🔊 Output: {self.device_name}", font_size='13sp',
            bold=True, color=get_color_from_hex('#64ffda')
        )
        device_bar.add_widget(self.lbl_device)
        root.add_widget(device_bar)

        self.btn_always_on = Button(
            text="🟢 ALWAYS ON (ENGINE LOCKED): ACTIVE", size_hint_y=None, height=dp(42),
            font_size='13sp', bold=True, background_normal='',
            background_color=get_color_from_hex('#00c853'), color=get_color_from_hex('#0a192f')
        )
        self.btn_always_on.bind(on_release=self.ensure_always_on)
        root.add_widget(self.btn_always_on)

        btn_hw_eq = Button(
            text="📱 OPEN HARDWARE EQ", size_hint_y=None, height=dp(48),
            font_size='14sp', bold=True, background_normal='',
            background_color=get_color_from_hex('#6200ea'), color=get_color_from_hex('#ffffff')
        )
        btn_hw_eq.bind(on_release=self.open_hw_eq)
        root.add_widget(btn_hw_eq)

        self.audio_wave = AudioWaveWidget(size_hint_y=1)
        root.add_widget(self.audio_wave)

        self.card_vol, self.lbl_vol_val, self.slider_vol = self.create_slider_card(
            title="1. MASTER VOLUME", min_val=0, max_val=100, cur_val=self.volume,
            unit="%", accent_hex='#00e676', callback=self.on_volume_change
        )
        root.add_widget(self.card_vol)

        self.card_bass, self.lbl_bass_val, self.slider_bass = self.create_slider_card(
            title="2. BASS BOOSTER (FFT DYNAMIC)", min_val=0, max_val=100, cur_val=self.bass,
            unit="%", accent_hex='#ff6d00', callback=self.on_bass_change
        )
        root.add_widget(self.card_bass)

        branding_box = BoxLayout(orientation='vertical', size_hint_y=1, spacing=dp(2))
        branding_box.add_widget(Widget())
        branding_box.add_widget(Label(text="PHOTON AUDIO", font_size='22sp', bold=True, color=get_color_from_hex('#64ffda'), halign='center'))
        branding_box.add_widget(Label(text="ULTIMATE DSP ENGINE", font_size='11sp', color=get_color_from_hex('#8892b0'), halign='center'))
        branding_box.add_widget(Widget())
        root.add_widget(branding_box)

        return root

    def detect_hardware_bands(self):
        bands = []
        if platform == 'android':
            try:
                from jnius import autoclass
                Equalizer = autoclass('android.media.audiofx.Equalizer')
                # Priority 0 રાખી છે જેથી બેકગ્રાઉન્ડ સર્વિસ (Priority 1000) પાસેથી કંટ્રોલ છીનવાય નહીં
                eq = Equalizer(0, 0)
                num_bands = eq.getNumberOfBands()
                for i in range(num_bands):
                    center = eq.getCenterFreq(i) / 1000.0
                    bands.append((i, center))
                eq.release()
            except Exception as e:
                print("Hardware detect error:", e)
                return []
        return bands

    def open_hw_eq(self, *args):
        HardwareEqPopup(self).open()

    def _update_bg(self, instance, *args):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def create_slider_card(self, title, min_val, max_val, cur_val, unit, accent_hex, callback):
        card = ProCard(orientation='vertical', padding=['12dp', '6dp'], spacing='4dp')
        card.size_hint_y = None
        card.height = dp(82)
        top_row = BoxLayout(orientation='horizontal', size_hint_y=0.4)

        lbl_title = Label(text=title, font_size='12sp', bold=True, color=get_color_from_hex('#ccd6f6'), halign='left', valign='middle')
        lbl_title.bind(size=lbl_title.setter('text_size'))
        lbl_val = Label(text=f"{int(cur_val)}{unit}", font_size='15sp', bold=True, color=get_color_from_hex(accent_hex), size_hint_x=0.35, halign='right', valign='middle')
        lbl_val.bind(size=lbl_val.setter('text_size'))

        top_row.add_widget(lbl_title)
        top_row.add_widget(lbl_val)

        slider = Slider(
            min=min_val, max=max_val, value=cur_val, step=1, cursor_size=('28dp', '28dp'),
            background_width='14dp', value_track=True, value_track_color=get_color_from_hex(accent_hex),
            value_track_width='5dp', size_hint_y=0.6
        )

        def on_value(instance, value):
            lbl_val.text = f"{int(value)}{unit}"
            callback(instance, value)

        slider.bind(value=on_value)
        card.add_widget(top_row)
        card.add_widget(slider)
        return card, lbl_val, slider

    def on_start(self):
        self.in_foreground = True
        self.save_settings()
        Clock.schedule_once(self.request_android_permissions, 0.5)
        self.request_battery_unrestricted()
        self.detect_connected_audio_device()
        self.start_background_service()
        Clock.schedule_interval(self.background_monitor, 1.5)

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
            except Exception:
                pass

    def on_pause(self):
        self.in_foreground = False
        self.save_settings()
        self.start_background_service()
        return True

    def on_resume(self):
        self.in_foreground = True
        self.detect_connected_audio_device()
        self.start_background_service()

    def ensure_always_on(self, *args):
        self.save_settings()
        self.request_battery_unrestricted()
        self.start_background_service(force=True)

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
        except Exception:
            pass
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
            info = f"Bass:{self.bass}% | Vol:{self.volume}% | HW EQ: Active"
            try:
                service_class.start(activity, 'icon', title, info, '')
            except Exception:
                service_class.start(activity, '')
        except Exception as e:
            print("Start Service Error:", e)

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
            except Exception:
                pass

    def detect_connected_audio_device(self):
        if platform != 'android':
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
        except Exception:
            pass
        if detected != self.device_name:
            self.device_name = detected
            if hasattr(self, 'lbl_device'):
                self.lbl_device.text = f"🔊 Output: {self.device_name}"

    def background_monitor(self, dt):
        if not self.in_foreground:
            return
        self.detect_connected_audio_device()
        if platform != 'android':
            return
        try:
            if not self.is_service_running():
                self.start_background_service(force=True)
            activity = PythonActivity.mActivity
            audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
            is_playing = audio_manager.isMusicActive()
            state = "🎵 Active" if is_playing else "⏸ Idle"
            if hasattr(self, 'lbl_device'):
                self.lbl_device.text = f"🔊 {self.device_name} [{state}]"
        except Exception:
            pass

    def schedule_save(self):
        if self._save_ev:
            self._save_ev.cancel()
        self._save_ev = Clock.schedule_once(lambda dt: self.save_settings(), 0.08)

    def on_volume_change(self, instance, value):
        self.volume = int(value)
        if platform == 'android':
            try:
                activity = PythonActivity.mActivity
                audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
                max_vol = audio_manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                target_vol = int(round((self.volume / 100.0) * max_vol))
                audio_manager.setStreamVolume(AudioManager.STREAM_MUSIC, target_vol, 0)
            except Exception:
                pass
        self.schedule_save()

    def on_bass_change(self, instance, value):
        self.bass = int(value)
        self.schedule_save()

    def on_hw_slider_change(self, band_idx, value):
        self.hw_eq_levels[str(band_idx)] = int(value)
        self.schedule_save()

    def get_settings_path(self):
        if platform == 'android':
            try:
                return os.path.join(PythonActivity.mActivity.getFilesDir().getAbsolutePath(), 'audio_eq_settings.json')
            except Exception:
                pass
        return 'audio_eq_settings.json'

    def save_settings(self):
        data = {
            'volume': self.volume,
            'bass': self.bass,
            'hw_eq_levels': self.hw_eq_levels
        }
        try:
            path = self.get_settings_path()
            tmp_path = path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            pass

    def load_settings(self):
        path = self.get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                self.volume = max(0, min(100, int(data.get('volume', 70))))
                self.bass = max(0, min(100, int(data.get('bass', 15))))

                hw_data = data.get('hw_eq_levels', {})
                if isinstance(hw_data, dict):
                    self.hw_eq_levels = {str(k): int(v) for k, v in hw_data.items() if isinstance(v, (int, float, str))}
                else:
                    self.hw_eq_levels = {}
            except Exception:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass


if __name__ == "__main__":
    AudioControllerApp().run()
