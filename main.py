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
from kivy.utils import get_color_from_hex, platform
from kivy.clock import Clock
from kivy.metrics import dp

PythonActivity = Context = AudioManager = PowerManager = None
Intent = Settings = Uri = Equalizer = autoclass = None

if platform == "android":
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Context = autoclass("android.content.Context")
        AudioManager = autoclass("android.media.AudioManager")
        PowerManager = autoclass("android.os.PowerManager")
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri = autoclass("android.net.Uri")
        Equalizer = autoclass("android.media.audiofx.Equalizer")
    except Exception as exc:
        print("Android imports:", exc)


def format_freq(hz):
    return f"{int(round(hz))} Hz" if hz < 1000 else f"{hz / 1000.0:.1f} kHz"


class ProCard(BoxLayout):
    def __init__(self, bg_hex="#112240", **kwargs):
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
        Clock.schedule_interval(self.animate, 1 / 30)

    def animate(self, dt):
        self.time += dt
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        if self.width < 10 or self.height < 10:
            return
        with self.canvas:
            colors = ["#00e676", "#00b0ff", "#ff6d00"]
            amps = [0.25, 0.15, 0.35]
            speeds = [4.0, 6.5, 3.5]
            phases = [0, 1.5, 3.0]
            for i in range(3):
                Color(rgba=get_color_from_hex(colors[i]))
                pts = []
                step = max(2, int(self.width / 60))
                for x in range(0, int(self.width), step):
                    y = self.height / 2 + math.sin(
                        (x / self.width) * 10 + self.time * speeds[i] + phases[i]
                    ) * (self.height * amps[i])
                    pts.extend([self.x + x, self.y + y])
                Line(points=pts, width=1.5)


class HardwareEqPopup(ModalView):
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.size_hint = (0.94, 0.88)
        self.background_color = (0, 0, 0, 0.85)
        self.auto_dismiss = False
        self.band_sliders = []

        root = ProCard(
            bg_hex="#0a192f", orientation="vertical",
            padding=dp(12), spacing=dp(8)
        )
        self.add_widget(root)

        root.add_widget(Label(
            text="📱 HARDWARE EQ BANDS",
            size_hint_y=None, height=dp(32), font_size="16sp",
            bold=True, color=get_color_from_hex("#b388ff")
        ))

        # Detect hardware EQ bands (from service cache or direct hardware probe)
        self.app.query_and_init_hardware_eq()

        root.add_widget(Label(
            text=f"Detected: {len(self.app.hw_bands)} Bands | "
                 f"Gain Range: {self.app.hw_min_mb / 100:+.1f} dB "
                 f"to {self.app.hw_max_mb / 100:+.1f} dB",
            size_hint_y=None, height=dp(24), font_size="12sp",
            color=get_color_from_hex("#64ffda")
        ))

        reset_btn = Button(
            text="🔄 RESET ALL TO NEUTRAL (0.0 dB)",
            size_hint_y=None, height=dp(40), font_size="13sp",
            bold=True, background_normal="",
            background_color=get_color_from_hex("#ff9800"),
            color=get_color_from_hex("#0a192f")
        )
        reset_btn.bind(on_release=self.reset_all_bands)
        root.add_widget(reset_btn)

        if not self.app.hw_bands:
            root.add_widget(Label(
                text="❌ Hardware EQ Not Detected / Not Available",
                halign="center", color=get_color_from_hex("#ff5252")
            ))
        else:
            scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
            layout = BoxLayout(
                orientation="vertical", spacing=dp(8), size_hint_y=None
            )
            layout.bind(minimum_height=layout.setter("height"))

            for info in self.app.hw_bands:
                idx = int(info["index"])
                center = format_freq(float(info["center_hz"]))
                band_range = (
                    f"{format_freq(float(info['min_hz']))} - "
                    f"{format_freq(float(info['max_hz']))}"
                )
                current = self.app.hw_eq_levels.get(str(idx), 50)
                db = self.app.slider_to_db(current)

                card = ProCard(
                    orientation="vertical", padding=[dp(12), dp(6)],
                    spacing=dp(4), size_hint_y=None, height=dp(88)
                )
                top = BoxLayout(
                    orientation="horizontal", size_hint_y=0.45
                )
                title = Label(
                    text=f"Band {idx + 1}: {center} [{band_range}]",
                    font_size="12sp", bold=True,
                    color=get_color_from_hex("#ccd6f6"),
                    halign="left", valign="middle"
                )
                title.bind(size=title.setter("text_size"))
                value_label = Label(
                    text=f"{db:+.1f} dB", font_size="14sp", bold=True,
                    color=get_color_from_hex("#b388ff"),
                    size_hint_x=0.32, halign="right", valign="middle"
                )
                value_label.bind(size=value_label.setter("text_size"))
                top.add_widget(title)
                top.add_widget(value_label)

                slider = Slider(
                    min=0, max=100, value=current, step=1,
                    cursor_size=("28dp", "28dp"),
                    background_width="14dp", value_track=True,
                    value_track_color=get_color_from_hex("#b388ff"),
                    value_track_width="5dp", size_hint_y=0.55
                )

                def make_callback(band_index, label):
                    def changed(instance, value):
                        label.text = f"{self.app.slider_to_db(value):+.1f} dB"
                        self.app.on_hw_slider_change(band_index, value)
                    return changed

                slider.bind(value=make_callback(idx, value_label))
                self.band_sliders.append((idx, slider, value_label))
                card.add_widget(top)
                card.add_widget(slider)
                layout.add_widget(card)

            scroll.add_widget(layout)
            root.add_widget(scroll)

        close_btn = Button(
            text="💾 SAVE & CLOSE", size_hint_y=None, height=dp(48),
            font_size="15sp", bold=True, background_normal="",
            background_color=get_color_from_hex("#00c853"),
            color=get_color_from_hex("#0a192f")
        )
        close_btn.bind(on_release=self.save_and_close)
        root.add_widget(close_btn)

    def reset_all_bands(self, *args):
        for idx, slider, label in self.band_sliders:
            slider.value = 50
            label.text = "+0.0 dB"
            self.app.hw_eq_levels[str(idx)] = 50
        self.app.save_settings()

    def save_and_close(self, *args):
        self.app.save_settings()
        self.dismiss()


class AudioControllerApp(App):
    def build(self):
        self.title = "Photon Audio"
        self.volume = 70
        self.bass = 15
        self.cmd_seq = 0

        # Pure Remote Control state: actual DSP mixing runs in hardware via Service
        self.hw_bands = []
        self.hw_eq_levels = {}
        self.hw_min_mb = -1500
        self.hw_max_mb = 1500

        self.device_name = "Detecting Audio Device..."
        self.in_foreground = True
        self._save_ev = None
        self._syncing_vol = False

        self.load_settings()
        self.query_and_init_hardware_eq()

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(12), dp(10), dp(12), dp(10)],
            spacing=dp(8)
        )
        with root.canvas.before:
            Color(rgba=get_color_from_hex("#0a192f"))
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        device_bar = ProCard(
            bg_hex="#004d40", size_hint_y=None,
            height=dp(40), padding=dp(6)
        )
        self.lbl_device = Label(
            text=f"🔊 Output: {self.device_name}",
            font_size="13sp", bold=True,
            color=get_color_from_hex("#64ffda")
        )
        device_bar.add_widget(self.lbl_device)
        root.add_widget(device_bar)

        self.btn_always_on = Button(
            text="🟢 ALWAYS ON (AUTO SPEAKER PAUSE): ACTIVE",
            size_hint_y=None, height=dp(42), font_size="13sp",
            bold=True, background_normal="",
            background_color=get_color_from_hex("#00c853"),
            color=get_color_from_hex("#0a192f")
        )
        self.btn_always_on.bind(on_release=self.ensure_always_on)
        root.add_widget(self.btn_always_on)

        hw_btn = Button(
            text="📱 OPEN HARDWARE EQ", size_hint_y=None,
            height=dp(48), font_size="14sp", bold=True,
            background_normal="",
            background_color=get_color_from_hex("#6200ea"),
            color=get_color_from_hex("#ffffff")
        )
        hw_btn.bind(on_release=self.open_hw_eq)
        root.add_widget(hw_btn)

        root.add_widget(AudioWaveWidget(size_hint_y=1))

        self.card_vol, self.lbl_vol_val, self.slider_vol = self.create_slider_card(
            "1. MASTER VOLUME", 0, 100, self.volume, "%",
            "#00e676", self.on_volume_change
        )
        root.add_widget(self.card_vol)

        self.card_bass, self.lbl_bass_val, self.slider_bass = self.create_slider_card(
            "2. BASS BOOSTER (CLEAN PUNCH)", 0, 100, self.bass, "%",
            "#ff6d00", self.on_bass_change
        )
        root.add_widget(self.card_bass)

        branding = BoxLayout(orientation="vertical", size_hint_y=1, spacing=dp(2))
        branding.add_widget(Widget())
        branding.add_widget(Label(
            text="PHOTON AUDIO", font_size="22sp", bold=True,
            color=get_color_from_hex("#64ffda"), halign="center"
        ))
        branding.add_widget(Label(
            text="ULTIMATE DSP ENGINE", font_size="11sp",
            color=get_color_from_hex("#8892b0"), halign="center"
        ))
        branding.add_widget(Widget())
        root.add_widget(branding)
        return root

    def get_caps_path(self):
        if platform == "android":
            try:
                return os.path.join(
                    PythonActivity.mActivity.getFilesDir().getAbsolutePath(),
                    "hw_eq_caps.json"
                )
            except Exception:
                pass
        return "hw_eq_caps.json"

    def _load_cached_hw_caps(self):
        path = self.get_caps_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r") as file:
                caps = json.load(file)
            bands = caps.get("hw_bands", [])
            min_mb = int(caps.get("hw_min_mb", -1500))
            max_mb = int(caps.get("hw_max_mb", 1500))
            if isinstance(bands, list) and len(bands) > 0 and min_mb < max_mb:
                self.hw_bands = bands
                self.hw_min_mb = min_mb
                self.hw_max_mb = max_mb
                self._normalize_hw_levels(len(bands))
                return True
        except Exception as exc:
            print("Load cached EQ caps:", exc)
        return False

    def _save_cached_hw_caps(self):
        if not self.hw_bands:
            return
        try:
            path = self.get_caps_path()
            temp = path + ".tmp"
            with open(temp, "w") as file:
                json.dump({
                    "hw_min_mb": self.hw_min_mb,
                    "hw_max_mb": self.hw_max_mb,
                    "hw_bands": self.hw_bands
                }, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp, path)
        except Exception as exc:
            print("Save cached EQ caps:", exc)

    def _normalize_hw_levels(self, count):
        valid = {str(i) for i in range(count)}
        self.hw_eq_levels = {
            k: max(0, min(100, int(v)))
            for k, v in self.hw_eq_levels.items()
            if k in valid
        }
        for i in range(count):
            self.hw_eq_levels.setdefault(str(i), 50)

    def query_and_init_hardware_eq(self):
        """
        Detect exact hardware EQ bands without disrupting the running service.
        First checks service-reported hardware capabilities; if unavailable,
        probes the hardware Equalizer once and caches the result.
        """
        if self._load_cached_hw_caps():
            return

        if platform != "android" or Equalizer is None:
            return

        probe = None
        detected = []
        try:
            probe = Equalizer(0, 0)

            level_range = probe.getBandLevelRange()
            min_mb = -1500
            max_mb = 1500
            if level_range is not None and len(level_range) >= 2:
                r_min = int(level_range[0])
                r_max = int(level_range[1])
                if r_min < r_max:
                    min_mb = r_min if r_min < 0 else -abs(r_max)
                    max_mb = r_max if r_max > 0 else abs(r_min)

            count = int(probe.getNumberOfBands())
            if count <= 0 or count > 64:
                raise RuntimeError(f"Invalid EQ band count: {count}")

            for i in range(count):
                center_mhz = int(probe.getCenterFreq(i))
                center = max(10.0, float(center_mhz) / 1000.0)

                low = center * 0.70
                high = center * 1.40
                try:
                    freq_range = probe.getBandFreqRange(i)
                    if freq_range is not None and len(freq_range) >= 2:
                        r_low = float(freq_range[0]) / 1000.0
                        r_high = float(freq_range[1]) / 1000.0
                        if r_low > 0:
                            low = r_low
                        if r_high >= low:
                            high = r_high
                        elif r_high <= 0:
                            high = max(center * 1.40, 20000.0)
                except Exception:
                    pass

                detected.append({
                    "index": i,
                    "center_hz": center,
                    "min_hz": low,
                    "max_hz": high
                })

            self.hw_min_mb = min_mb
            self.hw_max_mb = max_mb
            self.hw_bands = detected
            self._normalize_hw_levels(count)
            self._save_cached_hw_caps()
            self.save_settings()
        except Exception as exc:
            print("Hardware EQ Detection Error:", exc)
        finally:
            if probe is not None:
                try:
                    probe.release()
                except Exception:
                    pass

    def slider_to_mb(self, slider_value):
        value = max(0, min(100, int(round(slider_value))))
        if value == 50:
            return 0
        if value < 50:
            return int(round(((50 - value) / 50.0) * self.hw_min_mb))
        return int(round(((value - 50) / 50.0) * self.hw_max_mb))

    def slider_to_db(self, slider_value):
        return self.slider_to_mb(slider_value) / 100.0

    def on_hw_slider_change(self, band_idx, value):
        self.hw_eq_levels[str(band_idx)] = max(0, min(100, int(round(value))))
        self.schedule_save()

    def open_hw_eq(self, *args):
        HardwareEqPopup(self).open()

    def _update_bg(self, instance, *args):
        if hasattr(self, "bg_rect"):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def create_slider_card(self, title, min_val, max_val, cur_val,
                           unit, accent_hex, callback):
        card = ProCard(
            orientation="vertical", padding=[dp(12), dp(6)],
            spacing=dp(4)
        )
        card.size_hint_y = None
        card.height = dp(82)

        top = BoxLayout(orientation="horizontal", size_hint_y=0.4)
        title_lbl = Label(
            text=title, font_size="12sp", bold=True,
            color=get_color_from_hex("#ccd6f6"),
            halign="left", valign="middle"
        )
        title_lbl.bind(size=title_lbl.setter("text_size"))
        value_lbl = Label(
            text=f"{int(cur_val)}{unit}", font_size="15sp", bold=True,
            color=get_color_from_hex(accent_hex),
            size_hint_x=0.35, halign="right", valign="middle"
        )
        value_lbl.bind(size=value_lbl.setter("text_size"))
        top.add_widget(title_lbl)
        top.add_widget(value_lbl)

        slider = Slider(
            min=min_val, max=max_val, value=cur_val, step=1,
            cursor_size=("28dp", "28dp"),
            background_width="14dp", value_track=True,
            value_track_color=get_color_from_hex(accent_hex),
            value_track_width="5dp", size_hint_y=0.6
        )

        def changed(instance, value):
            value_lbl.text = f"{int(value)}{unit}"
            callback(instance, value)

        slider.bind(value=changed)
        card.add_widget(top)
        card.add_widget(slider)
        return card, value_lbl, slider

    def on_start(self):
        self.in_foreground = True
        self.sync_system_volume()
        self.save_settings()
        Clock.schedule_once(self.request_android_permissions, 0.5)
        self.request_battery_unrestricted()
        self.detect_connected_audio_device()
        self.start_background_service()
        Clock.schedule_interval(self.background_monitor, 1.0)
        Clock.schedule_interval(self.sync_system_volume, 0.5)

    def request_android_permissions(self, dt):
        if platform == "android":
            try:
                from android.permissions import request_permissions
                request_permissions([
                    "android.permission.BLUETOOTH_CONNECT",
                    "android.permission.BLUETOOTH_SCAN",
                    "android.permission.MODIFY_AUDIO_SETTINGS",
                    "android.permission.POST_NOTIFICATIONS"
                ])
            except Exception as exc:
                print("Permission request:", exc)

    def on_pause(self):
        self.in_foreground = False
        self.save_settings()
        self.start_background_service()
        return True

    def on_resume(self):
        self.in_foreground = True
        self._load_cached_hw_caps()
        self.sync_system_volume()
        self.detect_connected_audio_device()
        self.start_background_service()

    def ensure_always_on(self, *args):
        self.save_settings()
        self.request_battery_unrestricted()
        self.start_background_service(force=True)

    def sync_system_volume(self, *args):
        if not self.in_foreground or platform != "android":
            return
        try:
            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.AUDIO_SERVICE)
            maximum = manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            if maximum <= 0:
                return
            current = manager.getStreamVolume(AudioManager.STREAM_MUSIC)
            expected = int(round((self.volume / 100.0) * maximum))
            if current != expected:
                pct = max(0, min(100, int(round(current / float(maximum) * 100))))
                self._syncing_vol = True
                self.volume = pct
                if hasattr(self, "slider_vol"):
                    self.slider_vol.value = pct
                if hasattr(self, "lbl_vol_val"):
                    self.lbl_vol_val.text = f"{pct}%"
                self._syncing_vol = False
                self.schedule_save()
        except Exception as exc:
            self._syncing_vol = False
            print("Volume sync:", exc)

    def is_service_running(self):
        if platform != "android":
            return False
        try:
            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.ACTIVITY_SERVICE)
            running = manager.getRunningServices(100)
            if running:
                for item in running.toArray():
                    if str(item.service.getClassName()) == "com.photon.audio.ServicePhotondsp":
                        return True
        except Exception:
            pass
        return False

    def start_background_service(self, force=False):
        if platform != "android":
            return
        try:
            if not force and self.is_service_running():
                return
            service_class = autoclass("com.photon.audio.ServicePhotondsp")
            activity = PythonActivity.mActivity
            title = "Photon Audio EQ Active"
            info = f"Bass:{self.bass}% | Vol:{self.volume}% | HW EQ: Service"
            try:
                service_class.start(activity, "icon", title, info, "")
            except Exception:
                service_class.start(activity, "")
        except Exception as exc:
            print("Start Service Error:", exc)

    def request_battery_unrestricted(self):
        if platform == "android" and PowerManager and Settings and Uri:
            try:
                activity = PythonActivity.mActivity
                manager = activity.getSystemService(Context.POWER_SERVICE)
                package = activity.getPackageName()
                if not manager.isIgnoringBatteryOptimizations(package):
                    intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    intent.setData(Uri.parse(f"package:{package}"))
                    activity.startActivity(intent)
            except Exception as exc:
                print("Battery optimization request:", exc)

    def detect_connected_audio_device(self):
        if platform != "android":
            return
        detected = "Phone Speaker (DSP Paused)"
        try:
            manager = PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE)
            devices = manager.getDevices(2)
            if devices:
                for dev in devices:
                    dtype = dev.getType()
                    if dtype in (3, 4, 7, 8, 11, 12, 22, 26, 27):
                        product = dev.getProductName()
                        name = product.toString() if product else "External Audio"
                        detected = (
                            f"BT: {name}" if dtype in (7, 8, 26, 27)
                            else f"Headphones: {name}"
                        )
                        break
        except Exception as exc:
            print("Device detection:", exc)

        if detected != self.device_name:
            self.device_name = detected
            if hasattr(self, "lbl_device"):
                self.lbl_device.text = f"🔊 Output: {detected}"

    def background_monitor(self, dt):
        if not self.in_foreground:
            return
        if not self.hw_bands:
            self._load_cached_hw_caps()
        self.detect_connected_audio_device()
        if platform != "android":
            return
        try:
            manager = PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE)
            active = manager.isMusicActive()
            state = "🎵 Active" if active else "⏸ Idle"
            if hasattr(self, "lbl_device"):
                self.lbl_device.text = f"🔊 {self.device_name} [{state}]"
            if not self.is_service_running():
                self.start_background_service(force=True)
        except Exception as exc:
            print("Background monitor:", exc)

    def schedule_save(self):
        if self._save_ev:
            self._save_ev.cancel()
        # Fast 40ms remote-control dispatch to hardware service
        self._save_ev = Clock.schedule_once(lambda dt: self.save_settings(), 0.04)

    def on_volume_change(self, instance, value):
        if self._syncing_vol:
            return
        self.volume = int(value)
        if platform == "android":
            try:
                manager = PythonActivity.mActivity.getSystemService(Context.AUDIO_SERVICE)
                maximum = manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                target = int(round((self.volume / 100.0) * maximum))
                manager.setStreamVolume(AudioManager.STREAM_MUSIC, target, 0)
            except Exception as exc:
                print("Volume apply:", exc)
        self.schedule_save()

    def on_bass_change(self, instance, value):
        self.bass = int(value)
        self.schedule_save()

    def get_settings_path(self):
        if platform == "android":
            try:
                return os.path.join(
                    PythonActivity.mActivity.getFilesDir().getAbsolutePath(),
                    "audio_eq_settings.json"
                )
            except Exception:
                pass
        return "audio_eq_settings.json"

    def save_settings(self):
        """
        Dispatch exact remote-control commands (volume, bass, slider %,
        and exact per-band hardware millibel/dB targets) to Service.
        """
        self.cmd_seq += 1
        hw_eq_mb = {}
        hw_eq_db = {}
        for k, v in self.hw_eq_levels.items():
            mb_val = self.slider_to_mb(v)
            hw_eq_mb[str(k)] = mb_val
            hw_eq_db[str(k)] = round(mb_val / 100.0, 2)

        data = {
            "cmd_seq": self.cmd_seq,
            "volume": self.volume,
            "bass": self.bass,
            "hw_min_mb": self.hw_min_mb,
            "hw_max_mb": self.hw_max_mb,
            "hw_eq_levels": self.hw_eq_levels,
            "hw_eq_mb": hw_eq_mb,
            "hw_eq_db": hw_eq_db
        }
        try:
            path = self.get_settings_path()
            temp = path + ".tmp"
            with open(temp, "w") as file:
                json.dump(data, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp, path)
        except Exception as exc:
            print("Save settings:", exc)

    def load_settings(self):
        path = self.get_settings_path()
        if not os.path.exists(path):
            self.hw_eq_levels = {}
            return
        try:
            with open(path, "r") as file:
                data = json.load(file)
            self.cmd_seq = int(data.get("cmd_seq", 0))
            self.volume = max(0, min(100, int(data.get("volume", 70))))
            self.bass = max(0, min(100, int(data.get("bass", 15))))
            levels = data.get("hw_eq_levels", {})
            self.hw_eq_levels = {}
            if isinstance(levels, dict):
                for key, value in levels.items():
                    try:
                        self.hw_eq_levels[str(key)] = max(0, min(100, int(value)))
                    except (TypeError, ValueError):
                        continue
        except Exception as exc:
            print("Load settings:", exc)
            self.hw_eq_levels = {}


if __name__ == "__main__":
    AudioControllerApp().run()
