import time
import json
import os
from jnius import autoclass

PythonService = autoclass('org.kivy.android.PythonService')
Context = autoclass('android.content.Context')
AudioManager = autoclass('android.media.AudioManager')
Equalizer = autoclass('android.media.audiofx.Equalizer')
BassBoost = autoclass('android.media.audiofx.BassBoost')
LoudnessEnhancer = autoclass('android.media.audiofx.LoudnessEnhancer')
PowerManager = autoclass('android.os.PowerManager')

service = PythonService.mService
service.setAutoRestartService(True)

try:
    pm = service.getSystemService(Context.POWER_SERVICE)
    wake_lock = pm.newWakeLock(1, "PhotonAudio::ServiceWakeLock")
    wake_lock.setReferenceCounted(False)
    if not wake_lock.isHeld():
        wake_lock.acquire()
except Exception as e:
    print("Service WakeLock Error:", e)

audio_manager = service.getSystemService(Context.AUDIO_SERVICE)
settings_path = os.path.join(service.getFilesDir().getAbsolutePath(), 'audio_eq_settings.json')

eq_engine = None
bass_engine = None
loudness_engine = None

cfg = {
    'volume': 70,
    'bass': 15,
    'hw_eq_levels': {}
}

last_mtime = 0
last_vol = -1
last_bass_strength = -1
last_amp_mb = -1
tick = 0
control_lost_ticks = 0
dsp_paused_reason = "init"

def get_info_text():
    return f"Bass:{cfg['bass']}% | Vol:{cfg['volume']}% | HW EQ: Active"

def update_topbar_icon(is_active, text=None):
    try:
        if text is None:
            text = get_info_text()
        service.updateDspNotification(is_active, text)
    except Exception as e:
        print("Notification Error:", e)

def show_popup(msg):
    try:
        service.showToast(msg)
    except Exception as e:
        print("Toast Error:", e)

def is_external_audio_connected():
    try:
        devices = audio_manager.getDevices(2)
        if devices:
            for dev in devices:
                if dev.getType() in (3, 4, 7, 8, 11, 12, 22, 26, 27):
                    return True
    except Exception:
        pass
    try:
        if audio_manager.isBluetoothA2dpOn() or audio_manager.isWiredHeadsetOn():
            return True
    except Exception:
        pass
    return False

def release_engines():
    global eq_engine, bass_engine, loudness_engine, last_bass_strength, last_amp_mb
    for eng in (eq_engine, bass_engine, loudness_engine):
        if eng is not None:
            try:
                eng.setEnabled(False)
                eng.release()
            except Exception as e:
                print("Engine Release Error:", e)
    eq_engine = None
    bass_engine = None
    loudness_engine = None
    last_bass_strength = -1
    last_amp_mb = -1

def init_engines(force=False):
    global eq_engine, bass_engine, loudness_engine
    if force:
        release_engines()

    if eq_engine is None:
        try:
            eq_engine = Equalizer(1000, 0)
        except Exception as e:
            print("EQ Init Failed:", e)
            eq_engine = None

    if bass_engine is None:
        try:
            bass_engine = BassBoost(1000, 0)
        except Exception as e:
            print("Bass Init Failed:", e)
            bass_engine = None

    if loudness_engine is None:
        try:
            loudness_engine = LoudnessEnhancer(0)
        except Exception as e:
            print("Loudness Init Failed:", e)
            loudness_engine = None

def apply_volume():
    global last_vol
    try:
        vol = int(cfg.get('volume', 70))
        if vol != last_vol:
            max_vol = audio_manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            target_vol = int(round((vol / 100.0) * max_vol))
            audio_manager.setStreamVolume(AudioManager.STREAM_MUSIC, target_vol, 0)
            last_vol = vol
    except Exception as e:
        print("Volume Apply Error:", e)

def apply_dynamic_dsp(force=False):
    global last_bass_strength, last_amp_mb
    bass_val = max(0, min(100, int(cfg.get('bass', 15))))

    try:
        if bass_engine and bass_engine.hasControl():
            if bass_val <= 0:
                bass_engine.setStrength(0)
                bass_engine.setEnabled(False)
                last_bass_strength = 0
            else:
                bass_engine.setEnabled(True)
                final_strength = max(0, min(1000, int(bass_val * 10)))
                if force or abs(final_strength - last_bass_strength) >= 5:
                    bass_engine.setStrength(final_strength)
                    last_bass_strength = final_strength
    except Exception as e:
        print("DSP Bass Apply Error:", e)

    try:
        if loudness_engine and loudness_engine.hasControl():
            if bass_val <= 0:
                loudness_engine.setTargetGain(0)
                loudness_engine.setEnabled(False)
                last_amp_mb = 0
            else:
                loudness_engine.setEnabled(True)
                amp_mb = max(0, min(450, int(bass_val * 4.5)))
                if force or abs(amp_mb - last_amp_mb) >= 5:
                    loudness_engine.setTargetGain(amp_mb)
                    last_amp_mb = amp_mb
    except Exception as e:
        print("DSP Loudness Apply Error:", e)

def apply_hw_eq():
    try:
        if not eq_engine or not eq_engine.hasControl():
            return False

        num_bands = eq_engine.getNumberOfBands()
        level_range = eq_engine.getBandLevelRange()
        min_lvl = int(level_range[0])
        max_lvl = int(level_range[1])
        neutral = max(min_lvl, min(max_lvl, 0))

        hw_levels = cfg.get('hw_eq_levels', {})
        if not isinstance(hw_levels, dict):
            hw_levels = {}

        any_band_active = False
        for b in range(num_bands):
            try:
                pct = int(hw_levels.get(str(b), 50))
            except (TypeError, ValueError):
                pct = 50
            if pct != 50:
                any_band_active = True
                break

        if not any_band_active:
            for b in range(num_bands):
                eq_engine.setBandLevel(b, neutral)
            eq_engine.setEnabled(False)
            return True

        eq_engine.setEnabled(True)
        for b in range(num_bands):
            try:
                pct = int(hw_levels.get(str(b), 50))
            except (TypeError, ValueError):
                pct = 50
            pct = max(0, min(100, pct))

            if pct <= 50:
                hw_lvl = min_lvl + (pct / 50.0) * (neutral - min_lvl)
            else:
                hw_lvl = neutral + ((pct - 50) / 50.0) * (max_lvl - neutral)

            eq_engine.setBandLevel(b, int(round(hw_lvl)))
        return True
    except Exception as e:
        print("Hardware EQ Apply Error:", e)
        return False

while True:
    try:
        # 1. સેટિંગ્સ ફાઇલ અપડેટ ચેક
        if os.path.exists(settings_path):
            try:
                mtime = os.path.getmtime(settings_path)
                if mtime != last_mtime:
                    with open(settings_path, 'r') as f:
                        loaded_data = json.load(f)
                    last_mtime = mtime

                    if 'hw_eq_levels' in loaded_data and not isinstance(loaded_data['hw_eq_levels'], dict):
                        loaded_data['hw_eq_levels'] = {}

                    old_volume = cfg.get('volume', 70)
                    old_bass = cfg.get('bass', 15)
                    old_hw = dict(cfg.get('hw_eq_levels', {}))

                    cfg.update(loaded_data)

                    if cfg.get('volume') != old_volume or last_vol == -1:
                        apply_volume()

                    if dsp_paused_reason is None:
                        if cfg.get('hw_eq_levels') != old_hw:
                            apply_hw_eq()
                        if cfg.get('bass') != old_bass:
                            apply_dynamic_dsp(force=True)
                        update_topbar_icon(True) # 🎯 નોટિફિકેશન ટેક્સ્ટ તરત અપડેટ થશે
            except Exception as e:
                print("Settings Read Error:", e)

        # 2. કોલ અને ફોન સ્પીકર ડિટેક્શન
        audio_mode = audio_manager.getMode()
        in_call = (audio_mode != 0)
        ext_connected = is_external_audio_connected()

        if in_call:
            current_pause = "call"
        elif not ext_connected:
            current_pause = "speaker"
        else:
            current_pause = None

        if current_pause is not None:
            if dsp_paused_reason != current_pause:
                release_engines()
                dsp_paused_reason = current_pause
                msg = "DSP Paused during phone call" if current_pause == "call" else "DSP Paused on Phone Speaker"
                update_topbar_icon(False, msg)
                show_popup("DSP Service Stop")
            time.sleep(0.5)
            continue

        if dsp_paused_reason is not None:
            dsp_paused_reason = None
            init_engines(force=True)
            apply_hw_eq()
            apply_dynamic_dsp(force=True)
            update_topbar_icon(True)
            show_popup("DSP Service Start")

        tick += 1

        if tick % 10 == 0:
            status_ok = True
            if eq_engine is None or not eq_engine.hasControl():
                status_ok = False
            if bass_engine is None or not bass_engine.hasControl():
                status_ok = False

            if not status_ok:
                control_lost_ticks += 1
                if control_lost_ticks >= 2:
                    init_engines(force=True)
                    apply_hw_eq()
                    apply_dynamic_dsp(force=True)
                    update_topbar_icon(True)
                    control_lost_ticks = 0
            else:
                control_lost_ticks = 0

    except Exception as e:
        print("Main Service Loop Error:", e)

    time.sleep(0.5)
