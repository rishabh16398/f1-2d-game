"""
F1 sound engine.
Engine sound loaded from assets/sounds/engine.mp3 (real recording).
All other sounds (squeal, thud, pit, chime, lights) are procedural fallbacks.
"""
import pygame
import numpy as np
import math
import os


SAMPLE_RATE = 44100

# Path relative to this file: ../../assets/sounds/
_HERE       = os.path.dirname(os.path.abspath(__file__))
_SOUNDS_DIR = os.path.join(_HERE, "..", "assets", "sounds")

def _asset(filename):
    return os.path.join(_SOUNDS_DIR, filename)


def _make_array(duration_s, func):
    n = int(SAMPLE_RATE * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    wave = np.clip(func(t), -1.0, 1.0)
    arr  = (wave * 32767).astype(np.int16)
    return np.column_stack([arr, arr])

def _make_sound(duration_s, func):
    return pygame.sndarray.make_sound(_make_array(duration_s, func))


# ── Procedural engine fallback (used if MP3 missing) ─────────────────────────
def _make_proc_engine(rpm_factor=0.0):
    base = 80 + rpm_factor * 300
    def f(t):
        sig  = 0.40 * np.sin(2*np.pi*base*t)
        sig += 0.28 * np.sin(2*np.pi*base*2*t)
        sig += 0.18 * np.sin(2*np.pi*base*3*t)
        sig += 0.08 * np.sin(2*np.pi*base*4*t)
        return sig * 0.4
    return _make_sound(0.12, f)


# ── Start lights sequence ─────────────────────────────────────────────────────
def make_light_on():
    """Single light click/beep — 1200 Hz short pip."""
    def f(t):
        env = np.exp(-t * 30)
        return np.sin(2*np.pi*1200*t) * env * 0.7
    return _make_sound(0.12, f)


def make_go():
    """GO signal — rising two-tone burst."""
    def f(t):
        freq = 800 + t * 600
        env  = np.where(t < 0.05, t/0.05,
               np.where(t < 0.35, 1.0, np.exp(-(t-0.35)*8)))
        return np.sin(2*np.pi*freq*t) * env * 0.8
    return _make_sound(0.5, f)


# ── Tyre squeal ───────────────────────────────────────────────────────────────
def make_squeal():
    def f(t):
        freq = 3000 + 500*np.sin(2*np.pi*8*t)
        env  = np.where(t < 0.02, t/0.02,
               np.where(t < 0.15, 1.0, np.exp(-(t-0.15)*12)))
        noise = np.random.uniform(-0.3, 0.3, len(t))
        return (np.sin(2*np.pi*freq*t)*0.5 + noise*0.5) * env * 0.45
    return _make_sound(0.4, f)


# ── Collision thud ────────────────────────────────────────────────────────────
def make_thud():
    def f(t):
        env  = np.exp(-t * 18)
        sig  = np.sin(2*np.pi*120*t)*0.5
        sig += np.random.uniform(-0.5,0.5,len(t))*0.5
        return sig * env * 0.6
    return _make_sound(0.25, f)


# ── Pit stop ──────────────────────────────────────────────────────────────────
def make_pit_buzz():
    """Pneumatic gun sound — rapid stuttering pulse."""
    def f(t):
        rate = 40
        pulse = (np.sin(2*np.pi*rate*t) > 0.5).astype(float)
        noise = np.random.uniform(-0.4,0.4,len(t))
        env   = np.where(t<0.05,t/0.05,
                np.where(t<1.8,1.0,np.exp(-(t-1.8)*4)))
        return (noise*0.7 + pulse*0.3) * env * 0.5
    return _make_sound(2.0, f)


# ── Lap complete chime ────────────────────────────────────────────────────────
def make_lap_chime():
    freqs=[523,659,784,1047]  # C5 E5 G5 C6
    def f(t):
        sig=np.zeros_like(t)
        for i,freq in enumerate(freqs):
            start=i*0.12
            mask=(t>=start).astype(float)
            env=np.exp(-(t-start)*4)*mask
            sig+=np.sin(2*np.pi*freq*t)*env*0.5
        return sig*0.4
    return _make_sound(0.8, f)


# ── Main SoundEngine class ────────────────────────────────────────────────────
class SoundEngine:
    def __init__(self):
        pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        # ── Engine: real MP3 via mixer.music ──────────────────────────────────
        self._engine_mp3  = _asset("engine.mp3")
        self._mp3_ok      = os.path.exists(self._engine_mp3)
        self._target_vol  = 0.3   # updated each frame
        self._current_vol = 0.3

        if self._mp3_ok:
            pygame.mixer.music.load(self._engine_mp3)
            pygame.mixer.music.set_volume(self._current_vol)
            pygame.mixer.music.play(loops=-1)   # loop forever
        else:
            # Procedural fallback if file missing
            self._eng_channel = pygame.mixer.Channel(0)
            self._eng_samples = [_make_proc_engine(i/4) for i in range(5)]
            self._cur_rpm_idx = 0
            self._eng_channel.play(self._eng_samples[0], loops=-1)

        # ── Other sounds — procedural ─────────────────────────────────────────
        self.light_on  = make_light_on()
        self.go        = make_go()
        self.squeal    = make_squeal()
        self.thud      = make_thud()
        self.pit_buzz  = make_pit_buzz()
        self.lap_chime = make_lap_chime()

        self._squeal_cooldown = 0
        self._thud_cooldown   = 0

    def update_engine(self, speed, max_speed, throttle_held):
        """Call every frame. Scales volume with RPM to simulate acceleration."""
        rpm = speed / max(max_speed, 0.1)

        # Volume curve: quiet at idle, loud at full throttle
        # idle=0.18, full throttle full speed=0.90
        base_vol = 0.18 + rpm * 0.72
        if not throttle_held:
            base_vol *= 0.60   # lift-off sounds quieter / coasting
        self._target_vol = min(1.0, base_vol)

        # Smooth volume changes (avoid clicks)
        self._current_vol += (self._target_vol - self._current_vol) * 0.12

        if self._mp3_ok:
            pygame.mixer.music.set_volume(self._current_vol)
        else:
            # Fallback: switch between pre-built procedural samples
            idx = min(4, int(rpm * 5))
            if idx != self._cur_rpm_idx:
                self._cur_rpm_idx = idx
                self._eng_channel.set_volume(self._current_vol)
                self._eng_channel.play(self._eng_samples[idx], loops=-1, fade_ms=80)
            else:
                self._eng_channel.set_volume(self._current_vol)

    def play_squeal(self, cornering_force):
        if self._squeal_cooldown > 0:
            self._squeal_cooldown -= 1; return
        if cornering_force > 0.55:
            vol = min(1.0, (cornering_force - 0.55) * 2.8)
            ch  = pygame.mixer.find_channel()
            if ch: ch.set_volume(vol * 0.45); ch.play(self.squeal)
            self._squeal_cooldown = 20

    def play_thud(self):
        if self._thud_cooldown > 0:
            self._thud_cooldown -= 1; return
        ch = pygame.mixer.find_channel()
        if ch: ch.set_volume(0.75); ch.play(self.thud)
        self._thud_cooldown = 30

    def play_pit_start(self):
        ch = pygame.mixer.Channel(1)
        ch.set_volume(0.65); ch.play(self.pit_buzz)

    def play_lap_chime(self):
        ch = pygame.mixer.Channel(2)
        ch.set_volume(0.85); ch.play(self.lap_chime)

    def stop_engine(self):
        if self._mp3_ok:
            pygame.mixer.music.stop()
        else:
            self._eng_channel.stop()