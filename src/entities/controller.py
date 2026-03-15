"""
PS5 DualSense — VERIFIED button mapping on macOS (Rish's controller):

  Buttons:
    0  = Cross    ✕
    1  = Circle   ○   (confirmed)
    2  = Square   □
    3  = Triangle △
    5  = PS button
    6  = Options  ≡
    9  = L1
    10 = L2 (button)
    11 = D-pad Up
    12 = D-pad Down
    13 = D-pad Left
    14 = D-pad Right

  Axes:
    0  = Left stick X  (-1=left, +1=right)
    1  = Left stick Y
    2  = Right stick X
    3  = Right stick Y
    4  = L2 trigger    (-1 released → +1 fully pressed)
    5  = R2 trigger    (-1 released → +1 fully pressed)
"""
import pygame

DEAD_ZONE = 0.12

BTN_CROSS      = 0
BTN_SQUARE     = 2
BTN_TRIANGLE   = 3
BTN_CIRCLE     = 1   # confirmed btn 1 (was wrongly set to 4)
BTN_PS         = 5
BTN_OPTIONS    = 6
BTN_L1         = 9
BTN_L2         = 10
BTN_DPAD_UP    = 11
BTN_DPAD_DOWN  = 12
BTN_DPAD_LEFT  = 13
BTN_DPAD_RIGHT = 14

AXIS_LEFT_X  = 0
AXIS_LEFT_Y  = 1
AXIS_RIGHT_X = 2
AXIS_RIGHT_Y = 3
AXIS_L2      = 4
AXIS_R2      = 5


class ControllerInput:
    """
    IMPORTANT: call .tick() exactly ONCE per frame before reading any buttons.
    This snapshots the current state so every part of the code reads the same
    values — no edge state gets "eaten" by being read twice.
    """

    def __init__(self):
        pygame.joystick.init()
        self._joy       = None
        self._connected = False

        # Current and previous raw button states (updated in tick())
        self._cur  = {}   # btn_idx → bool
        self._prev = {}   # btn_idx → bool (last frame)

        # Snapshot of edge events for this frame (set in tick())
        self._pressed  = set()   # buttons that just went down this frame
        self._released = set()   # buttons that just went up this frame

        self.reconnect()

    def reconnect(self):
        pygame.joystick.quit()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self._joy = pygame.joystick.Joystick(0)
            self._joy.init()
            self._connected = True
        else:
            self._joy       = None
            self._connected = False

    @property
    def connected(self):
        return self._connected

    @property
    def name(self):
        return self._joy.get_name() if self._connected else "No controller"

    def tick(self):
        """
        Call once per frame (at the top of the game loop).
        Snapshots button states and computes which buttons were
        just pressed or released this frame.
        """
        if not self._connected:
            self._pressed  = set()
            self._released = set()
            return

        # Try reconnect if joy was lost
        try:
            n = self._joy.get_numbuttons()
        except Exception:
            self.reconnect()
            return

        self._prev = dict(self._cur)
        self._cur  = {i: bool(self._joy.get_button(i)) for i in range(n)}

        self._pressed  = {i for i in self._cur
                          if self._cur[i] and not self._prev.get(i, False)}
        self._released = {i for i in self._cur
                          if not self._cur[i] and self._prev.get(i, False)}

    # ── Raw button state (held) ───────────────────────────────────────────────
    def held(self, btn_idx):
        return self._cur.get(btn_idx, False)

    # ── Edge queries — safe to call multiple times per frame ──────────────────
    def just_pressed(self, btn_idx):
        """True if this button was pressed THIS frame (rising edge)."""
        return btn_idx in self._pressed

    def just_released(self, btn_idx):
        """True if this button was released THIS frame (falling edge)."""
        return btn_idx in self._released

    # ── Named button states (held) ────────────────────────────────────────────
    @property
    def cross_held(self):    return self.held(BTN_CROSS)
    @property
    def circle_held(self):   return self.held(BTN_CIRCLE)
    @property
    def triangle_held(self): return self.held(BTN_TRIANGLE)
    @property
    def square_held(self):   return self.held(BTN_SQUARE)

    # ── Named button presses (edge, safe to read many times) ──────────────────
    @property
    def cross_pressed(self):    return self.just_pressed(BTN_CROSS)
    @property
    def circle_pressed(self):   return self.just_pressed(BTN_CIRCLE)
    @property
    def triangle_pressed(self): return self.just_pressed(BTN_TRIANGLE)
    @property
    def square_pressed(self):   return self.just_pressed(BTN_SQUARE)
    @property
    def options_pressed(self):  return self.just_pressed(BTN_OPTIONS)
    @property
    def dpad_up_pressed(self):    return self.just_pressed(BTN_DPAD_UP)
    @property
    def dpad_down_pressed(self):  return self.just_pressed(BTN_DPAD_DOWN)
    @property
    def dpad_left_pressed(self):  return self.just_pressed(BTN_DPAD_LEFT)
    @property
    def dpad_right_pressed(self): return self.just_pressed(BTN_DPAD_RIGHT)

    # ── Analogue inputs ───────────────────────────────────────────────────────
    def _axis(self, idx):
        try:
            v = self._joy.get_axis(idx)
            return v if abs(v) > DEAD_ZONE else 0.0
        except:
            return 0.0

    def _trigger(self, axis_idx):
        try:
            raw = self._joy.get_axis(axis_idx)
        except:
            raw = -1.0
        return (raw + 1.0) / 2.0

    @property
    def steer(self):
        return self._axis(AXIS_LEFT_X)

    @property
    def throttle(self):
        return self._trigger(AXIS_R2)

    @property
    def brake(self):
        return self._trigger(AXIS_L2)

    # ── Legacy aliases ────────────────────────────────────────────────────────
    @property
    def tyre_soft(self):    return self.held(BTN_TRIANGLE)
    @property
    def tyre_medium(self):  return self.held(BTN_CIRCLE)
    @property
    def tyre_hard(self):    return self.held(BTN_CROSS)
    @property
    def drs_pressed(self):  return self.just_pressed(BTN_SQUARE)
    @property
    def restart(self):      return self.held(BTN_OPTIONS)
    @property
    def dpad_left(self):    return self.held(BTN_DPAD_LEFT)
    @property
    def dpad_right(self):   return self.held(BTN_DPAD_RIGHT)


# ── Singleton ─────────────────────────────────────────────────────────────────
_instance = None

def get_controller():
    global _instance
    if _instance is None:
        _instance = ControllerInput()
    return _instance