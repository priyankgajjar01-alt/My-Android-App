import time
import json
import os

from jnius import autoclass

PythonService = autoclass("org.kivy.android.PythonService")
Context = autoclass("android.content.Context")
AudioManager = autoclass("android.media.AudioManager")
Equalizer = autoclass("android.media.audiofx.Equalizer")
BassBoost = autoclass("android.media.audiofx.BassBoost")
LoudnessEnhancer = autoclass("android.media.audiofx.LoudnessEnhancer")
PowerManager = autoclass("android.os.PowerManager")

# Optional Android 9+ (API 28+) Hardware Multi-Band DynamicsProcessing
DynamicsProcessing = None
ConfigBuilder = None
Limiter = None
Eq = None
EqBand = None
try:
    DynamicsProcessing = autoclass("android.media.audiofx.DynamicsProcessing")
    ConfigBuilder = autoclass(
        "android.media.audiofx.DynamicsProcessing$Config$Builder"
    )
    Limiter = autoclass("android.media.audiofx.DynamicsProcessing$Limiter")
    Eq = autoclass("android.media.audiofx.DynamicsProcessing$Eq")
    EqBand = autoclass("android.media.audiofx.DynamicsProcessing$EqBand")
except Exception as exc:
    print("DynamicsProcessing unavailable (fallback active):", exc)

service = PythonService.mService
service.setAutoRestartService(True)

try:
    power = service.getSystemService(Context.POWER_SERVICE)
    wake_lock = power.newWakeLock(1, "PhotonAudio::ServiceWakeLock")
    wake_lock.setReferenceCounted(False)
    if not wake_lock.isHeld():
        wake_lock.acquire()
except Exception as exc:
    print("WakeLock:", exc)

audio_manager = service.getSystemService(Context.AUDIO_SERVICE)
files_dir = service.getFilesDir().getAbsolutePath()
settings_path = os.path.join(files_dir, "audio_eq_settings.json")
caps_path = os.path.join(files_dir, "hw_eq_caps.json")

# Hardware DSP Engines bound to Session 0 (Global Hardware Output Mix)
eq_engine = None
bass_engine = None
loudness_engine = None
dp_engine = None
dp_bass_eq = None

cfg = {
    "cmd_seq": -1,
    "volume": 70,
    "bass": 15,
    "hw_eq_levels": {},
    "hw_eq_mb": {}
}

hw_band_specs = []
hw_min_mb = -1500
hw_max_mb = 1500

last_mtime_ns = -1
last_cmd_seq = -1
last_vol = -1
last_bass_pct = -1
last_hw_signature = None
tick = 0
control_lost_ticks = 0
dsp_paused_reason = "init"

# Tuned Bass Boost Frequency Ranges & Maximum Gain Targets (Clean Punch Profile):
# (Cutoff Frequency Hz, Max Gain at 100% Bass in dB)
# Band 0: 20-65 Hz   -> +6.0 dB (Deep Sub-Bass Extension)
# Band 1: 65-140 Hz  -> +5.2 dB (Tight Chest Punch / Kick Thump)
# Band 2: 140-250 Hz -> +1.8 dB (Warm Upper-Bass Transition)
# Band 3: 250-450 Hz -> -1.5 dB (Anti-Mud Cut to keep vocals crisp)
# Band 4: 450-20k Hz ->  0.0 dB (Untouched Mids & Highs)
BASS_FREQ_PROFILE = [
    (65.0, 6.0),
    (140.0, 5.2),
    (250.0, 1.8),
    (450.0, -1.5),
    (20000.0, 0.0)
]


def notification_text():
    return (
        f"Bass:{cfg.get('bass', 15)}% | "
        f"Vol:{cfg.get('volume', 70)}% | HW EQ: Active"
    )


def update_notification(active, message=None):
    try:
        service.updateDspNotification(
            bool(active), message if message is not None else notification_text()
        )
    except Exception as exc:
        print("Notification:", exc)


def show_popup(message):
    try:
        service.showToast(message)
    except Exception as exc:
        print("Toast:", exc)


def is_external_audio_connected():
    """True only for a connected external playback output."""
    try:
        devices = audio_manager.getDevices(2)  # GET_DEVICES_OUTPUTS
        if devices:
            for dev in devices:
                if int(dev.getType()) in (3, 4, 7, 8, 11, 12, 22, 26, 27):
                    return True
    except Exception as exc:
        print("Audio device query:", exc)

    try:
        if audio_manager.isBluetoothA2dpOn() or audio_manager.isWiredHeadsetOn():
            return True
    except Exception:
        pass
    return False


def export_hardware_eq_caps():
    """Detect and export exact hardware EQ band specs for the App UI."""
    global hw_band_specs, hw_min_mb, hw_max_mb
    if eq_engine is None:
        return

    try:
        level_range = eq_engine.getBandLevelRange()
        min_mb = -1500
        max_mb = 1500
        if level_range is not None and len(level_range) >= 2:
            r_min = int(level_range[0])
            r_max = int(level_range[1])
            if r_min < r_max:
                min_mb = r_min if r_min < 0 else -abs(r_max)
                max_mb = r_max if r_max > 0 else abs(r_min)

        count = int(eq_engine.getNumberOfBands())
        if count <= 0 or count > 64:
            return

        detected = []
        for i in range(count):
            center_mhz = int(eq_engine.getCenterFreq(i))
            center = max(10.0, float(center_mhz) / 1000.0)
            low = center * 0.70
            high = center * 1.40
            try:
                freq_range = eq_engine.getBandFreqRange(i)
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

        hw_min_mb = min_mb
        hw_max_mb = max_mb
        hw_band_specs = detected

        temp = caps_path + ".tmp"
        with open(temp, "w") as file:
            json.dump({
                "hw_min_mb": hw_min_mb,
                "hw_max_mb": hw_max_mb,
                "hw_bands": hw_band_specs
            }, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, caps_path)
    except Exception as exc:
        print("Export hardware EQ caps error:", exc)


def release_engines():
    global eq_engine, bass_engine, loudness_engine, dp_engine, dp_bass_eq
    global last_bass_pct, last_hw_signature

    for engine in (eq_engine, bass_engine, loudness_engine, dp_engine):
        if engine is not None:
            try:
                engine.setEnabled(False)
            except Exception:
                pass
            try:
                engine.release()
            except Exception as exc:
                print("Effect release:", exc)

    eq_engine = None
    bass_engine = None
    loudness_engine = None
    dp_engine = None
    dp_bass_eq = None
    last_bass_pct = -1
    last_hw_signature = None


def init_dynamics_processing():
    """
    Initialize Android Hardware DynamicsProcessing on Session 0 for
    dedicated Bass Frequency & Range Gain shaping + Anti-Clip Limiter.
    """
    global dp_engine, dp_bass_eq
    if DynamicsProcessing is None or ConfigBuilder is None:
        return

    try:
        # Variant 0 (FAVOR_FREQUENCY_RESOLUTION), 2 channels,
        # Pre-EQ enabled (5 bass-shaping bands), MBC disabled,
        # Post-EQ disabled, Hardware Limiter enabled.
        builder = ConfigBuilder(
            0, 2, True, len(BASS_FREQ_PROFILE), False, 0, False, 0, True
        )
        config = builder.build()

        dp_bass_eq = config.getPreEqByChannelIndex(0)
        for idx, (cutoff_hz, _) in enumerate(BASS_FREQ_PROFILE):
            band = EqBand(True, float(cutoff_hz), 0.0)
            config.setPreEqBandAllChannelsTo(idx, band)

        # Hardware Brickwall Limiter: prevents distortion during heavy bass
        # inUse=True, enabled=True, linkGroup=0, attack=2ms, release=50ms,
        # ratio=10:1, threshold=-1.0dB, postGain=0.0dB
        limiter = Limiter(True, True, 0, 2.0, 50.0, 10.0, -1.0, 0.0)
        config.setLimiterAllChannelsTo(limiter)

        dp_engine = DynamicsProcessing(1000, 0, config)
        dp_engine.setEnabled(True)
    except Exception as exc:
        print("DynamicsProcessing init skipped:", exc)
        dp_engine = None
        dp_bass_eq = None


def init_engines(force=False):
    global eq_engine, bass_engine, loudness_engine

    if force:
        release_engines()

    if eq_engine is None:
        try:
            eq_engine = Equalizer(1000, 0)
            eq_engine.setEnabled(True)
            export_hardware_eq_caps()
        except Exception as exc:
            print("EQ init failed:", exc)
            eq_engine = None

    if bass_engine is None:
        try:
            bass_engine = BassBoost(1000, 0)
        except Exception as exc:
            print("BassBoost init failed:", exc)
            bass_engine = None

    if loudness_engine is None:
        try:
            loudness_engine = LoudnessEnhancer(0)
        except Exception as exc:
            print("Loudness init failed:", exc)
            loudness_engine = None

    if dp_engine is None:
        init_dynamics_processing()


def apply_volume():
    global last_vol
    try:
        pct = max(0, min(100, int(cfg.get("volume", 70))))
        if pct == last_vol:
            return
        maximum = audio_manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        if maximum > 0:
            target = int(round((pct / 100.0) * maximum))
            audio_manager.setStreamVolume(AudioManager.STREAM_MUSIC, target, 0)
            last_vol = pct
    except Exception as exc:
        print("Volume apply:", exc)


def compute_fallback_bass_mb(center_hz, bass_pct):
    """
    If hardware DynamicsProcessing is not supported on older Android devices,
    shape sub-bass & punch-bass frequency ranges directly on the Hardware EQ.
    """
    if dp_engine is not None or bass_pct <= 0:
        return 0
    ratio = (bass_pct / 100.0) ** 0.85
    if center_hz <= 90.0:
        return int(round(ratio * 450))      # +4.5 dB Sub-Bass (30-90 Hz)
    if center_hz <= 160.0:
        return int(round(ratio * 350))      # +3.5 dB Punch-Bass (90-160 Hz)
    if center_hz <= 260.0:
        return int(round(ratio * 150))      # +1.5 dB Warmth (160-260 Hz)
    if 260.0 < center_hz <= 480.0:
        return int(round(ratio * -120))     # -1.2 dB Anti-Mud Cut
    return 0


def get_hw_signature():
    levels = cfg.get("hw_eq_levels", {})
    if not isinstance(levels, dict):
        levels = {}
    bass_key = int(cfg.get("bass", 15)) if dp_engine is None else 0
    return (
        bass_key,
        tuple(sorted((str(k), int(v)) for k, v in levels.items()))
    )


def apply_hw_eq(force=False):
    """
    Execute the App's remote-control band commands directly on the
    Android Hardware Equalizer (Session 0).
    """
    global last_hw_signature

    try:
        if eq_engine is None:
            return False
        if not eq_engine.hasControl():
            print("EQ: service does not currently have control")
            return False

        count = int(eq_engine.getNumberOfBands())
        if count <= 0:
            return False

        if not hw_band_specs or len(hw_band_specs) != count:
            export_hardware_eq_caps()

        min_mb = hw_min_mb
        max_mb = hw_max_mb
        gain_range = eq_engine.getBandLevelRange()
        if gain_range is not None and len(gain_range) >= 2:
            r_min = int(gain_range[0])
            r_max = int(gain_range[1])
            if r_min < r_max:
                min_mb = r_min
                max_mb = r_max

        levels = cfg.get("hw_eq_levels", {})
        if not isinstance(levels, dict):
            levels = {}
        explicit_mb = cfg.get("hw_eq_mb", {})
        if not isinstance(explicit_mb, dict):
            explicit_mb = {}

        signature = get_hw_signature()
        if not force and signature == last_hw_signature:
            return True

        # Ensure Equalizer is enabled before writing hardware band registers
        eq_engine.setEnabled(True)

        bass_pct = max(0, min(100, int(cfg.get("bass", 15))))

        for band in range(count):
            band_key = str(band)
            if band_key in explicit_mb:
                try:
                    target = int(explicit_mb[band_key])
                except (TypeError, ValueError):
                    target = 0
            else:
                try:
                    pct = max(0, min(100, int(levels.get(band_key, 50))))
                except (TypeError, ValueError):
                    pct = 50
                if pct == 50:
                    target = 0
                elif pct < 50:
                    target = int(round(((50 - pct) / 50.0) * min_mb))
                else:
                    target = int(round(((pct - 50) / 50.0) * max_mb))

            # Add fallback bass frequency shaping only if DynamicsProcessing is absent
            if dp_engine is None and band < len(hw_band_specs):
                center_hz = float(hw_band_specs[band].get("center_hz", 1000.0))
                target += compute_fallback_bass_mb(center_hz, bass_pct)

            target = max(min_mb, min(max_mb, int(target)))
            eq_engine.setBandLevel(int(band), int(target))

        eq_engine.setEnabled(True)
        last_hw_signature = signature
        return True

    except Exception as exc:
        print("Hardware EQ apply error:", exc)
        return False


def apply_dynamic_dsp(force=False):
    """
    Tune Bass Boost Frequency & Range Gain across Hardware DynamicsProcessing,
    Hardware BassBoost Exciter, and Hardware LoudnessEnhancer.
    """
    global last_bass_pct

    bass_pct = max(0, min(100, int(cfg.get("bass", 15))))
    if not force and bass_pct == last_bass_pct:
        return

    norm = bass_pct / 100.0
    # Smooth non-linear acoustic curve for strong punch at 20-70% without clipping
    punch_curve = norm ** 0.85

    # 1. Hardware Multi-Band Bass Frequency & Range Gain (DynamicsProcessing)
    if dp_engine is not None:
        try:
            dp_engine.setEnabled(True)
            for idx, (cutoff_hz, max_db) in enumerate(BASS_FREQ_PROFILE):
                gain_db = round(punch_curve * max_db, 2) if bass_pct > 0 else 0.0
                band = EqBand(True, float(cutoff_hz), float(gain_db))
                dp_engine.setPreEqBandAllChannelsTo(idx, band)

            # Adjust hardware limiter post-gain (0.0 dB to +2.2 dB clean slam)
            post_gain_db = round(punch_curve * 2.2, 2) if bass_pct > 0 else 0.0
            limiter = Limiter(
                True, True, 0, 2.0, 50.0, 10.0, -1.0, float(post_gain_db)
            )
            dp_engine.setLimiterAllChannelsTo(limiter)
        except Exception as exc:
            print("DynamicsProcessing bass apply:", exc)

    # 2. Hardware Sub-Bass Harmonic Exciter (BassBoost: capped at 850 sweet-spot)
    try:
        if bass_engine is not None and bass_engine.hasControl():
            if bass_pct == 0:
                bass_engine.setStrength(0)
                bass_engine.setEnabled(False)
            else:
                # 850/1000 is the maximum clean hardware punch before distortion
                strength = max(0, min(850, int(round((norm ** 0.82) * 850))))
                bass_engine.setEnabled(True)
                bass_engine.setStrength(strength)
    except Exception as exc:
        print("BassBoost apply:", exc)

    # 3. Hardware Range Gain Compensation (LoudnessEnhancer: 0 to 240 mB / +2.4 dB)
    try:
        if loudness_engine is not None and loudness_engine.hasControl():
            if bass_pct == 0:
                loudness_engine.setTargetGain(0)
                loudness_engine.setEnabled(False)
            else:
                gain_mb = max(0, min(240, int(round(punch_curve * 240))))
                loudness_engine.setEnabled(True)
                loudness_engine.setTargetGain(gain_mb)
    except Exception as exc:
        print("Loudness apply:", exc)

    # If using fallback mode on older Android, update low EQ bands too
    if dp_engine is None:
        apply_hw_eq(force=True)

    last_bass_pct = bass_pct


def read_settings_if_changed():
    global last_mtime_ns, last_cmd_seq
    if not os.path.exists(settings_path):
        return False

    try:
        stat_info = os.stat(settings_path)
        mtime_ns = getattr(
            stat_info, "st_mtime_ns", int(stat_info.st_mtime * 1e9)
        )
        if mtime_ns == last_mtime_ns:
            return False

        with open(settings_path, "r") as file:
            loaded = json.load(file)

        if not isinstance(loaded, dict):
            return False

        cmd_seq = int(loaded.get("cmd_seq", -1))
        old_volume = cfg.get("volume", 70)
        old_bass = cfg.get("bass", 15)
        old_levels = dict(cfg.get("hw_eq_levels", {}))
        old_mb = dict(cfg.get("hw_eq_mb", {}))

        cfg["cmd_seq"] = cmd_seq
        cfg["volume"] = max(0, min(100, int(loaded.get("volume", 70))))
        cfg["bass"] = max(0, min(100, int(loaded.get("bass", 15))))

        clean_levels = {}
        raw_levels = loaded.get("hw_eq_levels", {})
        if isinstance(raw_levels, dict):
            for key, value in raw_levels.items():
                try:
                    clean_levels[str(key)] = max(0, min(100, int(value)))
                except (TypeError, ValueError):
                    continue
        cfg["hw_eq_levels"] = clean_levels

        clean_mb = {}
        raw_mb = loaded.get("hw_eq_mb", {})
        if isinstance(raw_mb, dict):
            for key, value in raw_mb.items():
                try:
                    clean_mb[str(key)] = int(value)
                except (TypeError, ValueError):
                    continue
        cfg["hw_eq_mb"] = clean_mb

        last_mtime_ns = mtime_ns
        last_cmd_seq = cmd_seq

        if cfg["volume"] != old_volume or last_vol == -1:
            apply_volume()

        if dsp_paused_reason is None:
            if cfg["hw_eq_levels"] != old_levels or cfg["hw_eq_mb"] != old_mb:
                apply_hw_eq(force=True)
            if cfg["bass"] != old_bass:
                apply_dynamic_dsp(force=True)
            update_notification(True)

        return True

    except Exception as exc:
        print("Settings read error:", exc)
        return False


def pause_dsp(reason):
    global dsp_paused_reason
    if dsp_paused_reason != reason:
        release_engines()
        dsp_paused_reason = reason
        message = (
            "DSP Paused during phone call"
            if reason == "call" else "DSP Paused on Phone Speaker"
        )
        update_notification(False, message)
        show_popup("DSP Paused")


def resume_dsp():
    global dsp_paused_reason
    dsp_paused_reason = None
    init_engines(force=True)

    eq_ok = apply_hw_eq(force=True)
    apply_dynamic_dsp(force=True)
    update_notification(True)
    show_popup("DSP Service Start")

    if not eq_ok:
        print("DSP resumed, but Hardware EQ could not be applied")


# Export hardware EQ capabilities once at service boot so UI always has bands
try:
    init_engines(force=True)
    release_engines()
except Exception:
    pass

# High-responsiveness hardware remote loop (80ms polling)
while True:
    try:
        read_settings_if_changed()

        mode = int(audio_manager.getMode())
        in_call = mode != int(AudioManager.MODE_NORMAL)
        external = is_external_audio_connected()

        if in_call:
            pause_dsp("call")
            time.sleep(0.25)
            continue

        if not external:
            pause_dsp("speaker")
            time.sleep(0.25)
            continue

        if dsp_paused_reason is not None:
            resume_dsp()

        tick += 1
        if tick % 40 == 0:
            lost = (
                eq_engine is None or not eq_engine.hasControl()
                or bass_engine is None or not bass_engine.hasControl()
            )
            if lost:
                control_lost_ticks += 1
                if control_lost_ticks >= 2:
                    init_engines(force=True)
                    apply_hw_eq(force=True)
                    apply_dynamic_dsp(force=True)
                    update_notification(True)
                    control_lost_ticks = 0
            else:
                control_lost_ticks = 0

    except Exception as exc:
        print("Main service loop error:", exc)

    time.sleep(0.08)
