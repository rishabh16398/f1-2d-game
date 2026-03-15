import pygame
import math


def _draw_f1_car(color, accent=(255,255,255), drs_open=False):
    """Sprite faces RIGHT. angle=0→right, angle=180→left."""
    W, H = 44, 18
    surf = pygame.Surface((W,H), pygame.SRCALPHA)
    body=[(W-1,H//2),(W-5,2),(W-18,1),(10,2),(2,6),(0,H//2),
          (2,H-6),(10,H-2),(W-18,H-1),(W-5,H-2)]
    pygame.draw.polygon(surf, color, body)
    pygame.draw.polygon(surf,accent,[(W-9,0),(W-20,1),(W-20,4),(W-9,3)])
    pygame.draw.polygon(surf,accent,[(W-9,H),(W-20,H-1),(W-20,H-4),(W-9,H-3)])
    if drs_open:
        pygame.draw.rect(surf,(0,220,120),(0,H//2-1,5,2))
    else:
        pygame.draw.rect(surf,accent,(0,0,5,H))
        pygame.draw.rect(surf,color,(1,3,3,H-6))
    cc=tuple(max(0,c-65) for c in color[:3])
    pygame.draw.ellipse(surf,cc,(W-28,4,14,H-8))
    pygame.draw.ellipse(surf,(185,210,255,130),(W-27,5,9,4))
    pod=tuple(min(255,c+22) for c in color[:3])
    pygame.draw.rect(surf,pod,(7,1,15,4),border_radius=2)
    pygame.draw.rect(surf,pod,(7,H-5,15,4),border_radius=2)
    for tx,ty in [(8,1),(34,1),(8,H-1),(34,H-1)]:
        pygame.draw.circle(surf,(18,18,18),(tx,ty),4)
        pygame.draw.circle(surf,(140,140,140),(tx,ty),2)
    pygame.draw.line(surf,(18,18,18),(W-28,H//2),(W-16,H//2),2)
    return surf


class Car(pygame.sprite.Sprite):
    COMPOUND_STATS = {
        "Soft":   {"accel":0.22,"max_spd":8.0,"wear":0.050,"grip_bonus": 0.08},
        "Medium": {"accel":0.18,"max_spd":7.0,"wear":0.018,"grip_bonus": 0.00},
        "Hard":   {"accel":0.13,"max_spd":6.3,"wear":0.007,"grip_bonus":-0.05},
    }
    TYRE_COL = {"Soft":(220,30,30),"Medium":(240,200,0),"Hard":(220,220,220)}

    def __init__(self, x, y, color=(200,20,20), accent=(255,255,255)):
        super().__init__()
        self.car_color      = color
        self.car_accent     = accent
        self.original_image = _draw_f1_car(color, accent, False)
        self.image          = self.original_image.copy()
        self.rect           = self.image.get_rect(center=(x,y))
        self.position       = pygame.math.Vector2(x,y)
        self.velocity       = pygame.math.Vector2(0,0)
        self.angle          = 180

        self.compound       = "Medium"
        self.tyre_health    = 100.0
        self.is_pitting     = False
        self.pit_timer      = 0
        self.is_off_track   = False
        self.drs_available  = False
        self.drs_open       = False
        self.drs_cooldown   = 0
        self.auto_drs       = False   # set by strategy screen
        self.laps_done      = 0
        self.wp_index       = 0
        self._bw            = 1920
        self._bh            = 1080

    def set_bounds(self, w, h):
        self._bw = w; self._bh = h

    def change_tyres(self, compound):
        self.compound    = compound
        self.tyre_health = 100.0
        self.original_image = _draw_f1_car(self.car_color, self.car_accent, False)

    @property
    def grip(self):
        stats = self.COMPOUND_STATS[self.compound]
        base  = 0.60 + 0.40*(self.tyre_health/100.0)
        return max(0.2, base + stats["grip_bonus"])

    def open_drs(self):
        if self.drs_available and self.drs_cooldown == 0:
            self.drs_open = True
            self.original_image = _draw_f1_car(self.car_color, self.car_accent, True)

    def close_drs(self):
        if self.drs_open:
            self.drs_open     = False
            self.drs_cooldown = 30
            self.original_image = _draw_f1_car(self.car_color, self.car_accent, False)

    def update(self, keys, ctrl=None):
        """
        ctrl = ControllerInput instance or None.
        If ctrl is connected, analogue axes take priority over keyboard.
        Both can be used simultaneously — whichever gives larger input wins.
        """
        if self.drs_cooldown > 0:
            self.drs_cooldown -= 1

        if self.pit_timer > 0:
            self.pit_timer -= 1
            self.velocity.update(0, 0)
            if self.pit_timer == 0: self.is_pitting = False
            self._sync(); return

        stats   = self.COMPOUND_STATS[self.compound]
        max_spd = stats["max_spd"] * max(0.3, self.grip)
        accel   = stats["accel"]

        if self.is_off_track: max_spd = min(max_spd, 2.5)
        elif self.drs_open:   max_spd += 2.0

        if self.auto_drs and self.drs_available and not self.drs_open:
            self.open_drs()
        if self.auto_drs and not self.drs_available and self.drs_open:
            self.close_drs()

        rad = math.radians(self.angle)
        fwd = pygame.math.Vector2(math.cos(rad), -math.sin(rad))
        going_fwd = self.velocity.length() < 0.1 or self.velocity.dot(fwd) >= 0

        # ── Read inputs — controller takes priority, keyboard as fallback ─────
        c = ctrl if (ctrl and ctrl.connected) else None

        # Throttle: R2 (0→1) or W/UP key
        throttle_kb  = keys[pygame.K_w] or keys[pygame.K_UP]
        throttle_val = c.throttle if c else (1.0 if throttle_kb else 0.0)

        # Brake: L2 (0→1) or S/DOWN key
        brake_kb  = keys[pygame.K_s] or keys[pygame.K_DOWN]
        brake_val = c.brake if c else (1.0 if brake_kb else 0.0)

        # Steering: left stick X (-1=left +1=right) or A/D keys
        if c:
            steer_axis = c.steer   # -1..+1, already dead-zoned
        else:
            steer_axis = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:  steer_axis = -1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: steer_axis =  1.0

        # ── Apply throttle ────────────────────────────────────────────────────
        if throttle_val > 0.05:
            self.velocity += fwd * accel * throttle_val

        # ── Apply brake ───────────────────────────────────────────────────────
        if brake_val > 0.05:
            spd = self.velocity.length()
            if spd > 0.1:
                self.velocity -= self.velocity.normalize() * min(0.55 * brake_val, spd)

        # ── Steering — analogue gives proportional angle change ───────────────
        spd   = self.velocity.length()
        steer = max(3.0, 5.0 - spd * 0.10)   # 3.0–5.0 °/frame
        s_dir = 1 if going_fwd else -1

        if abs(steer_axis) > 0.01:
            # Analogue: proportional + slight expo curve for precision
            expo  = steer_axis * abs(steer_axis)   # softens small inputs
            delta = steer * expo * s_dir
            # Left stick left = steer left = angle increases in pygame coords
            self.angle -= delta   # negative because right-stick = right-turn

        # ── DRS ───────────────────────────────────────────────────────────────
        if not self.auto_drs:
            # Controller: Square button (edge triggered inside controller module)
            drs_btn = (c.drs_pressed if c else False) or keys[pygame.K_q]
            if drs_btn:
                if self.drs_open: self.close_drs()
                else:             self.open_drs()
            elif not c and not keys[pygame.K_q] and self.drs_open:
                self.close_drs()   # keyboard hold-to-open behaviour

        # ── Friction & speed cap ──────────────────────────────────────────────
        throttle_held = throttle_val > 0.05
        self.velocity *= (0.992 if throttle_held else 0.920)
        if self.velocity.length() > max_spd:
            self.velocity.scale_to_length(max_spd)

        if spd > 0.3:
            self.tyre_health = max(0, self.tyre_health - stats["wear"])

        self.position += self.velocity
        self._sync()

    def _sync(self):
        self.position.x = max(10, min(self._bw-10, self.position.x))
        self.position.y = max(10, min(self._bh-10, self.position.y))
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect  = self.image.get_rect(center=(int(self.position.x),
                                                  int(self.position.y)))