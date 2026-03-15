import pygame
import math
import random
from entities.car import Car


class AICar(Car):
    PERSONALITIES = [
        {"name":"Aggressive","aggression":0.88,"consistency":0.55,"speed":0.94},
        {"name":"Balanced",  "aggression":0.72,"consistency":0.35,"speed":0.88},
        {"name":"Cautious",  "aggression":0.58,"consistency":0.20,"speed":0.82},
    ]

    def __init__(self, x, y, waypoints, color=(0,120,255), accent=(255,255,255),
                 personality_index=None):
        super().__init__(x, y, color=color, accent=accent)
        self.waypoints = waypoints
        self.wp_index  = 0
        self._last_wp  = 0
        self.state     = "RACING"

        self.pit_entry_waypoints = []
        self.pit_box_centre      = None
        self.pit_wp_index        = 0
        self.pit_threshold       = random.uniform(20, 35)

        if personality_index is None:
            personality_index = random.randint(0, 2)
        p = self.PERSONALITIES[personality_index % 3]
        self.aggression   = p["aggression"] + random.uniform(-0.08, 0.08)
        self.consistency  = p["consistency"]
        self.speed_factor = p["speed"]      + random.uniform(-0.05, 0.05)

        self._mistake_timer   = 0
        self._mistake_steer   = 0.0
        self._next_mistake_in = self._rand_interval()
        self._off_track_frames = 0

        # ── Collision response ────────────────────────────────────────────────
        # When hit, AI coasts freely for _stun_timer frames instead of
        # snapping back to its racing line immediately.
        self._stun_timer     = 0
        self._stun_friction  = 0.92   # deceleration while stunned

    # ── Public: called by resolve_collisions() ────────────────────────────────
    def receive_collision(self, push_vector, impulse_magnitude):
        """
        Called when this car is involved in a collision.
        push_vector  : normalised direction of the push (pygame.math.Vector2)
        impulse_magnitude : how hard the hit was (speed difference projected)
        """
        # Only stun if the hit is meaningful (not just gentle touching)
        if impulse_magnitude > 0.8:
            # Stun duration scales with impact — hard hits stun longer
            frames = int(20 + impulse_magnitude * 14)
            self._stun_timer = min(frames, 80)   # cap at ~1.3 seconds

    # ── Mistake helpers ───────────────────────────────────────────────────────
    def _rand_interval(self):
        base = int(300 * (1.0 - self.consistency * 0.7))
        return random.randint(base, base + int(200*(1.0 - self.consistency*0.5)))

    def _tick_mistakes(self):
        if self._mistake_timer > 0:
            self._mistake_timer -= 1
            if self._mistake_timer == 0:
                self._mistake_steer = 0.0
            return self._mistake_steer
        self._next_mistake_in -= 1
        if self._next_mistake_in <= 0:
            max_err = 6 + self.consistency * 12
            self._mistake_steer   = random.choice([-1,1]) * random.uniform(4, max_err)
            self._mistake_timer   = random.randint(25, 80)
            self._next_mistake_in = self._rand_interval()
        return 0.0

    # ── Main update ───────────────────────────────────────────────────────────
    def update(self, keys=None, ctrl=None):
        # Pit stop freeze
        if self.pit_timer > 0:
            self.pit_timer -= 1
            self.velocity.update(0, 0)
            if self.pit_timer == 0:
                self.is_pitting = False
                self.change_tyres(random.choice(["Medium","Hard"]))
                self.pit_threshold = random.uniform(20, 35)
                self.state = "RACING"
            self._sync(); return

        # Tyre wear
        spd = self.velocity.length()
        if spd > 0.3:
            self.tyre_health = max(0,
                self.tyre_health - self.COMPOUND_STATS[self.compound]["wear"])

        # ── COLLISION STUN — coast freely, don't follow waypoints ─────────────
        if self._stun_timer > 0:
            self._stun_timer -= 1
            # Apply friction so the car slows down naturally
            self.velocity *= self._stun_friction
            # Clamp to screen
            self.position += self.velocity
            self._sync()
            # Update lap counter even while stunned
            if self._last_wp >= len(self.waypoints)-3 and self.wp_index <= 2:
                self.laps_done += 1
            self._last_wp = self.wp_index
            return   # skip waypoint logic entirely while stunned

        # Strategy: decide to pit
        if self.state == "RACING" and self.tyre_health < self.pit_threshold:
            if self.pit_entry_waypoints:
                self.state = "PIT_ENTRY"; self.pit_wp_index = 0

        if self.state == "PIT_ENTRY":
            self._follow_pit_entry()
        else:
            self._follow_race_waypoints()

        if self._last_wp >= len(self.waypoints)-3 and self.wp_index <= 2:
            self.laps_done += 1
        self._last_wp = self.wp_index
        self._sync()

    # ── Race line following ───────────────────────────────────────────────────
    def _follow_race_waypoints(self):
        wp  = pygame.math.Vector2(self.waypoints[self.wp_index])
        spd = self.velocity.length()

        if self.position.distance_to(wp) < 28 + spd * 1.8:
            self.wp_index = (self.wp_index + 1) % len(self.waypoints)
            wp = pygame.math.Vector2(self.waypoints[self.wp_index])

        angle_diff  = self._angle_to(wp)
        steer_error = self._tick_mistakes()
        self._steer(angle_diff + steer_error)

        nxt       = pygame.math.Vector2(
            self.waypoints[(self.wp_index+1) % len(self.waypoints)])
        sharpness = abs(self._angle_to(nxt))

        base_spd = (self.COMPOUND_STATS[self.compound]["max_spd"]
                    * self.grip * self.speed_factor)

        if sharpness > 15:
            factor   = self.aggression * (1.0 - (sharpness - 15) / 100.0)
            base_spd *= max(0.38, factor)

        if self.is_off_track:
            self._off_track_frames += 1
            base_spd = min(base_spd, 1.8)
            correction = angle_diff * 0.3
            self.angle += max(-4, min(4, correction))
        else:
            self._off_track_frames = 0

        self.drs_open = (sharpness < 10 and self.drs_available)
        if self.drs_open: base_spd = min(base_spd + 1.0, 8.8)

        self._drive(angle_diff, base_spd)

    # ── Pit entry routing ─────────────────────────────────────────────────────
    def _follow_pit_entry(self):
        if not self.pit_entry_waypoints:
            self.state = "RACING"; return
        if self.pit_wp_index >= len(self.pit_entry_waypoints):
            self.velocity.update(0, 0)
            self.is_pitting = True; self.pit_timer = 190
            self.state = "STOPPED"; return
        tgt  = pygame.math.Vector2(self.pit_entry_waypoints[self.pit_wp_index])
        if self.position.distance_to(tgt) < 28:
            self.pit_wp_index += 1; return
        angle_diff = self._angle_to(tgt)
        self._steer(angle_diff)
        progress = self.pit_wp_index / max(1, len(self.pit_entry_waypoints))
        self._drive(angle_diff, max(1.5, 4.0 - progress*1.8))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _angle_to(self, target):
        diff    = pygame.math.Vector2(target) - self.position
        t_angle = math.degrees(math.atan2(-diff.y, diff.x)) % 360
        return (t_angle - (self.angle % 360) + 180) % 360 - 180

    def _steer(self, angle_diff):
        turn = max(-4.5, min(4.5, angle_diff * 0.45))
        self.angle += turn

    def _drive(self, angle_diff, limit):
        spd = self.velocity.length()
        if abs(angle_diff) < 22:
            spd = min(spd + 0.13, limit)
        else:
            spd = max(0, spd * 0.85)
        self.velocity.x  = math.cos(math.radians(self.angle)) * spd
        self.velocity.y  = -math.sin(math.radians(self.angle)) * spd
        self.position   += self.velocity
        self.rect.center = (int(self.position.x), int(self.position.y))