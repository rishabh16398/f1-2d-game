import pygame
import sys
import os
import math
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from entities.car          import Car
from entities.track        import Track
from entities.ai_car       import AICar
from entities.sound_engine import SoundEngine
from entities.controller   import get_controller

WHITE  = (255,255,255); BLACK  = (0,0,0)
YELLOW = (240,200,0);   RED    = (210,30,30)
GREEN  = (30,200,80);   GRAY   = (140,140,155)
PURPLE = (160,80,255);  ORANGE = (255,140,0)

TYRE_COL  = {"Soft":(220,30,30),"Medium":(240,200,0),"Hard":(220,220,220)}
TYRE_DESC = {"Soft":"Fastest — wears very quickly",
             "Medium":"Balanced pace and durability",
             "Hard":"Durable — slower but lasts long"}
DRIVER_NAMES = ["YOU","Hamilton","Verstappen","Leclerc"]


def fmt_time(ms):
    if ms<=0: return "--:--.---"
    s=ms//1000; m=s//60; s%=60; ms%=1000
    return f"{m}:{s:02d}.{ms:03d}"

def bar(surf,x,y,w,h,pct,fg,bg=(45,45,52)):
    pct=max(0.0,min(1.0,pct))
    pygame.draw.rect(surf,bg,(x,y,w,h),border_radius=3)
    fw=int(w*pct)
    if fw: pygame.draw.rect(surf,fg,(x,y,fw,h),border_radius=3)
    pygame.draw.rect(surf,(78,78,94),(x,y,w,h),1,border_radius=3)

def tyre_col(pct):
    return GREEN if pct>60 else (YELLOW if pct>30 else RED)

def resolve_collisions(cars, snd):
    R = 22
    for i in range(len(cars)):
        for j in range(i+1, len(cars)):
            a, b   = cars[i], cars[j]
            diff   = a.position - b.position
            dist   = diff.length()
            if 0 < dist < R*2:
                overlap = R*2 - dist
                push    = diff.normalize()
                a.position += push * (overlap * 0.52)
                b.position -= push * (overlap * 0.52)
                rel = a.velocity - b.velocity
                imp = rel.dot(push) * 0.40
                a.velocity -= push * imp
                b.velocity += push * imp
                a.rect.center = (int(a.position.x), int(a.position.y))
                b.rect.center = (int(b.position.x), int(b.position.y))
                # Tell AI cars they were hit so they stop following waypoints
                if hasattr(a, 'receive_collision'):
                    a.receive_collision(push,  abs(imp))
                if hasattr(b, 'receive_collision'):
                    b.receive_collision(-push, abs(imp))
                if abs(imp) > 1.5 and snd:
                    snd.play_thud()

def race_standings(player, bots, waypoints):
    N=len(waypoints)
    def score(car):
        bi=min(range(N),key=lambda i:car.position.distance_squared_to(
               pygame.math.Vector2(waypoints[i])))
        return car.laps_done*N+bi
    all_cars=[(player,"YOU")]+[(b,DRIVER_NAMES[i+1]) for i,b in enumerate(bots)]
    return sorted(all_cars,key=lambda p:score(p[0]),reverse=True)


def main():
    pygame.init()
    info=pygame.display.Info()
    W,H=info.current_w,info.current_h
    screen=pygame.display.set_mode((W,H),pygame.FULLSCREEN)
    pygame.display.set_caption("F1 2D")
    clock=pygame.time.Clock()

    fsm  = pygame.font.SysFont("Arial",13,bold=True)
    fmd  = pygame.font.SysFont("Arial",19,bold=True)
    flg  = pygame.font.SysFont("Arial",42,bold=True)
    fxlg = pygame.font.SysFont("Arial",56,bold=True)
    fhud = pygame.font.SysFont("Arial",17,bold=True)
    fpit = pygame.font.SysFont("Arial",52,bold=True)
    fnum = pygame.font.SysFont("Arial",110,bold=True)  # start lights

    # Init sound (graceful fallback if no audio)
    try:
        snd = SoundEngine()
        sound_ok = True
    except Exception:
        snd = None; sound_ok = False

    # ── STRATEGY SCREEN ───────────────────────────────────────────────────────
    result = _run_strategy_screen(screen,W,H,flg,fmd,fsm,clock)
    if result[0] is None:
        if snd: snd.stop_engine()
        pygame.quit(); sys.exit()
    chosen_laps, chosen_tyre, auto_drs, chosen_track = result
    TOTAL_LAPS = chosen_laps

    track = Track(W, H, track_id=chosen_track)
    # Build grass colour set from actual track grass colour
    gc = track.image.get_at((5,5))[:3]
    gc2 = tuple(min(255,c+12) for c in gc)
    gc3 = tuple(max(0,  c-10) for c in gc)
    GRASS_COLS = {gc, gc2, gc3}

    # Controller (PS5 / any gamepad)
    ctrl = get_controller()
    if ctrl.connected:
        print(f"Controller connected: {ctrl.name}")

    sx,sy=track.waypoints[0]
    player=Car(sx,sy,color=(200,20,20),accent=(255,255,255))
    player.angle=180; player.set_bounds(W,H)
    player.change_tyres(chosen_tyre); player.auto_drs=auto_drs

    bot_defs=[
        ((0,110,200),(255,255,255),0),
        ((0,155,72),(255,210,0),1),
        ((165,0,175),(255,255,255),2),
    ]
    bots=[]
    for i,((bc,ba,pi),gap) in enumerate(zip(bot_defs,[45,90,135])):
        b=AICar(sx+gap,sy,track.waypoints,color=bc,accent=ba,personality_index=pi)
        b.angle=180; b.wp_index=0
        b.pit_entry_waypoints=track.pit_entry_waypoints
        b.pit_box_centre=track.pit_box_centre
        b.set_bounds(W,H); bots.append(b)

    all_sprites=pygame.sprite.Group(player,*bots)

    # ── START LIGHTS STATE ────────────────────────────────────────────────────
    # lights_phase: 0=waiting,1-5=lights on,6=GO,7=racing
    lights_phase      = 0
    lights_timer      = 0
    LIGHTS_INTERVAL   = 70   # frames between each light (≈1.15s)
    lights_out_timer  = 0    # countdown after all 5 lights on before GO
    pit_sound_played  = False

    laps=0; lap_start=0; best_lap=0; last_lap=0
    hit_cp=False; drs_zone=False; race_over=False
    finish_order=[]; winner_msg=""; confetti=[]; celebration_timer=0
    prev_pitting=False; prev_laps=0

    # Kick off start sequence
    lights_phase=1; lights_timer=0

    while True:
        clock.tick(60)
        keys=pygame.key.get_pressed()
        now=pygame.time.get_ticks()
        ctrl.tick()   # snapshot all button states ONCE per frame

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if ev.key==pygame.K_r: main(); return

        # ── START LIGHTS SEQUENCE ─────────────────────────────────────────────
        racing = (lights_phase == 7)
        if not racing:
            lights_timer += 1
            if lights_phase in (1,2,3,4,5):
                if lights_timer >= LIGHTS_INTERVAL:
                    if snd: snd.light_on.play()
                    lights_timer = 0
                    lights_phase += 1
                    if lights_phase == 6:
                        lights_out_timer = random.randint(50,100)
            elif lights_phase == 6:
                lights_out_timer -= 1
                if lights_out_timer <= 0:
                    if snd: snd.go.play()
                    lights_phase = 7
                    lap_start = pygame.time.get_ticks()

        # ── RACE LOGIC ────────────────────────────────────────────────────────
        if racing and not race_over:
            GRASS_COLS_L={(36,126,36),(41,136,41),(32,116,32)}
            for car in [player,*bots]:
                rad=math.radians(car.angle)
                samples=[(int(car.position.x+math.cos(rad)*14),
                          int(car.position.y-math.sin(rad)*14)),
                         (int(car.rect.centerx),int(car.rect.centery))]
                on=False
                for cx,cy in samples:
                    if 0<=cx<W and 0<=cy<H:
                        if track.image.get_at((cx,cy))[:3] not in GRASS_COLS_L:
                            on=True; break
                car.is_off_track=not on

            for car in [player,*bots]:
                if car.rect.colliderect(track.pit_lane_rect):
                    if car.velocity.length()>3.0:
                        car.velocity.scale_to_length(3.0)

            if player.rect.colliderect(track.drs_detection):
                drs_zone=True; player.drs_available=True
            if player.rect.colliderect(track.finish_line):
                drs_zone=False; player.drs_available=False; player.close_drs()
            for b in bots: b.drs_available=True

            all_sprites.update(keys, ctrl)
            resolve_collisions([player,*bots], snd or type('',(),{'play_thud':lambda self:None})())

            player.wp_index=min(range(len(track.waypoints)),
                key=lambda i:player.position.distance_squared_to(
                    pygame.math.Vector2(track.waypoints[i])))

            # Controller restart
            if ctrl.connected and ctrl.restart:
                main(); return

            # Player pit — keyboard OR controller face buttons
            # Use edge-triggered presses so holding a button doesn't re-trigger
            ctrl_tyre1 = ctrl.connected and ctrl.triangle_pressed  # △ = Soft
            ctrl_tyre2 = ctrl.connected and ctrl.circle_pressed    # ○ = Medium
            ctrl_tyre3 = ctrl.connected and ctrl.cross_pressed     # ✕ = Hard

            if (player.rect.colliderect(track.pit_box)
                    and not player.is_pitting
                    and player.velocity.length()<1.5):
                kb1 = keys[pygame.K_1]; kb2 = keys[pygame.K_2]; kb3 = keys[pygame.K_3]
                if kb1 or ctrl_tyre1:
                    nt = "Soft"
                elif kb2 or ctrl_tyre2:
                    nt = "Medium"
                elif kb3 or ctrl_tyre3:
                    nt = "Hard"
                else:
                    nt = None
                if nt:
                    player.change_tyres(nt)
                    player.is_pitting=True; player.pit_timer=190
                    if snd: snd.play_pit_start(); pit_sound_played=True

            # Pit sound ended?
            if prev_pitting and not player.is_pitting:
                pit_sound_played=False
            prev_pitting=player.is_pitting

            # Tyre squeal — based on steering input vs speed
            if snd:
                turn_held = keys[pygame.K_a] or keys[pygame.K_LEFT] or \
                            keys[pygame.K_d] or keys[pygame.K_RIGHT]
                spd_n = player.velocity.length() / 8.0
                if turn_held and spd_n > 0.3:
                    snd.play_squeal(spd_n)

            # Engine sound
            if snd:
                throttle_held = keys[pygame.K_w] or keys[pygame.K_UP]
                snd.update_engine(player.velocity.length(), 8.0, throttle_held)

            # Lap counting
            if player.rect.colliderect(track.finish_line) and hit_cp:
                elapsed=now-lap_start; last_lap=elapsed
                if best_lap==0 or elapsed<best_lap: best_lap=elapsed
                laps+=1; player.laps_done=laps; lap_start=now; hit_cp=False
                if snd: snd.play_lap_chime()
                if laps>=TOTAL_LAPS and player not in [c for c,_ in finish_order]:
                    finish_order.append((player,"YOU"))
                    if len(finish_order)==1:
                        winner_msg=_pick_msg("YOU"); _spawn_confetti(confetti,W,H)
                        celebration_timer=480
            if player.rect.colliderect(track.checkpoint): hit_cp=True

            for b in bots:
                if b.laps_done>=TOTAL_LAPS and b not in [c for c,_ in finish_order]:
                    nm=DRIVER_NAMES[bots.index(b)+1]
                    finish_order.append((b,nm))
                    if len(finish_order)==1:
                        winner_msg=_pick_msg(nm); _spawn_confetti(confetti,W,H)
                        celebration_timer=480

            if len(finish_order)>=4: race_over=True

        # ── RENDER ────────────────────────────────────────────────────────────
        track.draw(screen)
        all_sprites.draw(screen)
        standings=race_standings(player,bots,track.waypoints)

        _hud(screen,player,standings,laps,TOTAL_LAPS,
             lap_start,best_lap,last_lap,drs_zone,auto_drs,
             track,W,H,fhud,fpit,fsm,fmd,ctrl)

        # Start lights overlay
        if not racing:
            _draw_start_lights(screen,lights_phase,W,H,fnum,flg)

        if celebration_timer>0:
            celebration_timer-=1
            _update_confetti(screen,confetti)
            _draw_celebration(screen,winner_msg,finish_order,
                              celebration_timer,W,H,fxlg,flg,fmd,fsm)

        pygame.display.flip()


def _pick_msg(name):
    return random.choice([
        "{} WINS THE RACE!",
        "{} TAKES THE CHEQUERED FLAG!",
        "VICTORY FOR {}!",
        "{} — FIRST ACROSS THE LINE!",
    ]).format(name.upper())


# ── Start lights drawing ──────────────────────────────────────────────────────
def _draw_start_lights(screen, phase, W, H, fnum, flg):
    # Dark overlay
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,155))
    screen.blit(ov,(0,0))

    if phase == 7: return

    # Light panel
    n_lights = 5
    lw,lh    = 56,56
    gap      = 18
    total_w  = n_lights*(lw+gap)-gap
    px       = (W-total_w)//2
    py       = H//2 - 80

    # Panel background
    panel_pad=24
    pygame.draw.rect(screen,(20,20,28),
                     (px-panel_pad,py-panel_pad,
                      total_w+panel_pad*2,lh+panel_pad*2+60),
                     border_radius=14)
    pygame.draw.rect(screen,(70,70,90),
                     (px-panel_pad,py-panel_pad,
                      total_w+panel_pad*2,lh+panel_pad*2+60),1,border_radius=14)

    title = flg.render("GET READY",True,(200,200,200))
    screen.blit(title,((W-title.get_width())//2, py-64))

    # Draw 5 lights
    lights_on = phase - 1   # how many are red (phase 1=1 lit, phase 5=5 lit)
    if phase == 6:
        lights_on = 5   # all on, about to go

    for i in range(n_lights):
        lx = px + i*(lw+gap)
        lit = (i < lights_on)
        col = (220,20,20) if lit else (40,20,20)
        rim = (255,80,80) if lit else (80,50,50)
        pygame.draw.circle(screen,col,(lx+lw//2,py+lh//2),lw//2)
        pygame.draw.circle(screen,rim,(lx+lw//2,py+lh//2),lw//2,3)
        # Glow effect for lit lights
        if lit:
            glow=pygame.Surface((lw+20,lh+20),pygame.SRCALPHA)
            pygame.draw.circle(glow,(220,20,20,60),(lw//2+10,lh//2+10),lw//2+8)
            screen.blit(glow,(lx-10,py-10))

    # Phase 6: all on — show "LIGHTS OUT!" anticipation text
    if phase == 6:
        t=flg.render("LIGHTS OUT...",True,RED)
        screen.blit(t,((W-t.get_width())//2, py+lh+panel_pad+10))


# ── Strategy screen ───────────────────────────────────────────────────────────
def _run_strategy_screen(screen, W, H, flg, fmd, fsm, clock):
    """Returns (laps, tyre, auto_drs, track_id) or (None,None,None,None)."""
    from entities.controller import get_controller
    from entities.track import get_track_names
    ctrl = get_controller()

    chosen_laps  = 5
    chosen_tyre  = "Medium"
    auto_drs     = False
    chosen_track = 0
    lap_opts     = [3, 5, 10, 15, 20]
    tyre_list    = ["Soft", "Medium", "Hard"]
    track_names  = get_track_names()   # [(id, name, country), ...]

    # Rows: 0=track, 1=laps, 2=tyre, 3=drs, 4=start
    ROWS   = ["TRACK","LAPS","TYRE","DRS","START"]
    cursor = 0

    while True:
        clock.tick(60)
        ctrl.tick()

        # ── Keyboard ──────────────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return None,None,None,None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return None,None,None,None
                if ev.key == pygame.K_RETURN: return chosen_laps,chosen_tyre,auto_drs,chosen_track
                if ev.key == pygame.K_UP:   cursor=(cursor-1)%len(ROWS)
                if ev.key == pygame.K_DOWN: cursor=(cursor+1)%len(ROWS)
                if ev.key == pygame.K_LEFT:
                    if cursor==0: chosen_track=(chosen_track-1)%len(track_names)
                    elif cursor==1:
                        idx=lap_opts.index(chosen_laps); chosen_laps=lap_opts[max(0,idx-1)]
                    elif cursor==2:
                        ti=tyre_list.index(chosen_tyre); chosen_tyre=tyre_list[max(0,ti-1)]
                if ev.key == pygame.K_RIGHT:
                    if cursor==0: chosen_track=(chosen_track+1)%len(track_names)
                    elif cursor==1:
                        idx=lap_opts.index(chosen_laps); chosen_laps=lap_opts[min(len(lap_opts)-1,idx+1)]
                    elif cursor==2:
                        ti=tyre_list.index(chosen_tyre); chosen_tyre=tyre_list[min(len(tyre_list)-1,ti+1)]
                if ev.key == pygame.K_1: chosen_tyre="Soft"
                if ev.key == pygame.K_2: chosen_tyre="Medium"
                if ev.key == pygame.K_3: chosen_tyre="Hard"
                if ev.key == pygame.K_d: auto_drs=not auto_drs

        # ── Controller ────────────────────────────────────────────────────────
        if ctrl.connected:
            if ctrl.dpad_up_pressed:   cursor=(cursor-1)%len(ROWS)
            if ctrl.dpad_down_pressed: cursor=(cursor+1)%len(ROWS)
            if ctrl.dpad_left_pressed:
                if cursor==0: chosen_track=(chosen_track-1)%len(track_names)
                elif cursor==1:
                    idx=lap_opts.index(chosen_laps); chosen_laps=lap_opts[max(0,idx-1)]
                elif cursor==2:
                    ti=tyre_list.index(chosen_tyre); chosen_tyre=tyre_list[max(0,ti-1)]
            if ctrl.dpad_right_pressed:
                if cursor==0: chosen_track=(chosen_track+1)%len(track_names)
                elif cursor==1:
                    idx=lap_opts.index(chosen_laps); chosen_laps=lap_opts[min(len(lap_opts)-1,idx+1)]
                elif cursor==2:
                    ti=tyre_list.index(chosen_tyre); chosen_tyre=tyre_list[min(len(tyre_list)-1,ti+1)]
            if ctrl.triangle_pressed: chosen_tyre="Soft"
            if ctrl.circle_pressed:   chosen_tyre="Medium"
            if ctrl.square_pressed:
                if cursor==3: auto_drs=not auto_drs
                else: auto_drs=not auto_drs
            if ctrl.cross_pressed:
                if cursor==2: chosen_tyre="Hard"
                else: return chosen_laps,chosen_tyre,auto_drs,chosen_track
            if ctrl.options_pressed: return None,None,None,None

        # ── Draw ──────────────────────────────────────────────────────────────
        screen.fill((10,10,18))
        title=flg.render("F1 2D  —  RACE SETUP",True,WHITE)
        screen.blit(title,((W-title.get_width())//2,40))

        pw,ph=700,590; px,py=(W-pw)//2,(H-ph)//2-20
        panel=pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((20,20,32,242))
        screen.blit(panel,(px,py))
        pygame.draw.rect(screen,(68,68,110),(px,py,pw,ph),1,border_radius=12)

        def hl(row_idx,y,h):
            if cursor==row_idx:
                s=pygame.Surface((pw-20,h),pygame.SRCALPHA); s.fill((60,60,120,80))
                screen.blit(s,(px+10,y))
                pygame.draw.rect(screen,(120,120,220),(px+10,y,pw-20,h),1,border_radius=6)

        # ── Row 0: Track ──────────────────────────────────────────────────────
        hl(0, py+16, 78)
        screen.blit(fmd.render("Track:", True, GRAY), (px+40, py+24))
        tid, tname, tcountry = track_names[chosen_track]
        # Prev/next arrows
        prev_t = track_names[(chosen_track-1)%len(track_names)]
        next_t = track_names[(chosen_track+1)%len(track_names)]
        screen.blit(fsm.render(f"◄  {prev_t[1]}", True, (80,80,100)), (px+40, py+48))
        tn_surf = fmd.render(f"{tname}  {tcountry}", True, YELLOW)
        screen.blit(tn_surf, (px+(pw-tn_surf.get_width())//2, py+46))
        screen.blit(fsm.render(f"{next_t[1]}  ►", True, (80,80,100)),
                    (px+pw-fsm.size(f"{next_t[1]}  ►")[0]-40, py+48))
        screen.blit(fsm.render(f"Track {chosen_track+1} of {len(track_names)}  |  ◄► to change",
                    True, (80,80,110)), (px+40, py+70))

        pygame.draw.line(screen,(50,50,70),(px+30,py+102),(px+pw-30,py+102),1)

        # ── Row 1: Laps ───────────────────────────────────────────────────────
        hl(1, py+110, 80)
        screen.blit(fmd.render("Number of laps:", True, GRAY), (px+40, py+118))
        for i,lv in enumerate(lap_opts):
            lx=px+40+i*122; ly=py+144; sel=chosen_laps==lv
            pygame.draw.rect(screen,(55,55,80) if sel else (28,28,44),(lx,ly,108,38),border_radius=8)
            if sel: pygame.draw.rect(screen,YELLOW,(lx,ly,108,38),2,border_radius=8)
            lt=fmd.render(str(lv),True,YELLOW if sel else WHITE)
            screen.blit(lt,(lx+(108-lt.get_width())//2,ly+8))

        pygame.draw.line(screen,(50,50,70),(px+30,py+196),(px+pw-30,py+196),1)

        # ── Row 2: Tyre ───────────────────────────────────────────────────────
        hl(2, py+204, 215)
        screen.blit(fmd.render("Starting tyre:", True, GRAY), (px+40, py+212))
        tyres=[("△/1","Soft",TYRE_COL["Soft"]),("○/2","Medium",TYRE_COL["Medium"]),("✕/3","Hard",TYRE_COL["Hard"])]
        for i,(btn,name,col) in enumerate(tyres):
            ry=py+238+i*60; sel=chosen_tyre==name
            pygame.draw.rect(screen,(50,50,72) if sel else (28,28,42),(px+30,ry,pw-60,52),border_radius=8)
            if sel: pygame.draw.rect(screen,col,(px+30,ry,pw-60,52),2,border_radius=8)
            pygame.draw.circle(screen,col,(px+65,ry+26),16)
            pygame.draw.circle(screen,(0,0,0),(px+65,ry+26),16,2)
            screen.blit(fmd.render(f"  {name}",True,WHITE),(px+95,ry+10))
            screen.blit(fsm.render(f"{btn}  {TYRE_DESC[name]}",True,col if sel else GRAY),(px+95,ry+32))
            wr={"Soft":5,"Medium":2,"Hard":1}[name]
            for d in range(5):
                pygame.draw.circle(screen,col if d<wr else (40,40,50),(px+pw-90+d*16,ry+26),5)

        pygame.draw.line(screen,(50,50,70),(px+30,py+425),(px+pw-30,py+425),1)

        # ── Row 3: DRS ────────────────────────────────────────────────────────
        hl(3, py+433, 52)
        drs_col=GREEN if auto_drs else GRAY
        pygame.draw.rect(screen,(30,60,30) if auto_drs else (28,28,42),(px+30,py+440,pw-60,40),border_radius=8)
        pygame.draw.rect(screen,drs_col,(px+30,py+440,pw-60,40),2,border_radius=8)
        sq_hint="□/[D]" if ctrl.connected else "[D]"
        screen.blit(fmd.render(f"{sq_hint}  DRS: {'AUTO' if auto_drs else 'MANUAL'}",True,drs_col),(px+54,py+450))

        pygame.draw.line(screen,(50,50,70),(px+30,py+492),(px+pw-30,py+492),1)

        # ── Row 4: Start ──────────────────────────────────────────────────────
        hl(4, py+500, 42)
        sc=YELLOW if cursor==4 else (160,160,80)
        pygame.draw.rect(screen,(40,40,10) if cursor==4 else (28,28,28),(px+30,py+504,pw-60,34),border_radius=8)
        pygame.draw.rect(screen,sc,(px+30,py+504,pw-60,34),2,border_radius=8)
        sh="✕ / ENTER  to start race" if ctrl.connected else "ENTER  to start race"
        st=fmd.render(sh,True,sc); screen.blit(st,(px+(pw-st.get_width())//2,py+511))

        # Guide
        guide="↑↓=navigate  ◄►=change  △=Soft  ○=Med  ✕=confirm  □=DRS  Options=quit" if ctrl.connected \
              else "↑↓=navigate  ◄►=change  1/2/3=tyre  D=DRS  ENTER=start  ESC=quit"
        screen.blit(fsm.render(guide,True,(75,75,105)),((W-fsm.size(guide)[0])//2,py+ph+14))

        pygame.display.flip()


    while True:
        clock.tick(60)
        ctrl.tick()   # snapshot button states once per frame

        # ── Keyboard events ───────────────────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None, None, None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None, None, None
                if ev.key == pygame.K_RETURN:
                    return chosen_laps, chosen_tyre, auto_drs
                # Laps
                if ev.key == pygame.K_LEFT:
                    idx = lap_opts.index(chosen_laps)
                    chosen_laps = lap_opts[max(0, idx-1)]
                if ev.key == pygame.K_RIGHT:
                    idx = lap_opts.index(chosen_laps)
                    chosen_laps = lap_opts[min(len(lap_opts)-1, idx+1)]
                # Tyres
                if ev.key == pygame.K_1: chosen_tyre = "Soft"
                if ev.key == pygame.K_2: chosen_tyre = "Medium"
                if ev.key == pygame.K_3: chosen_tyre = "Hard"
                # DRS
                if ev.key == pygame.K_d: auto_drs = not auto_drs
                # Cursor
                if ev.key == pygame.K_UP:
                    cursor = (cursor - 1) % len(ROWS)
                if ev.key == pygame.K_DOWN:
                    cursor = (cursor + 1) % len(ROWS)

        # ── Controller navigation ─────────────────────────────────────────────
        if ctrl.connected:
            # D-pad up/down — move cursor between rows
            if ctrl.dpad_up_pressed:
                cursor = (cursor - 1) % len(ROWS)
            if ctrl.dpad_down_pressed:
                cursor = (cursor + 1) % len(ROWS)

            # D-pad left/right — change value on current row
            if ctrl.dpad_left_pressed:
                if cursor == 0:   # laps
                    idx = lap_opts.index(chosen_laps)
                    chosen_laps = lap_opts[max(0, idx-1)]
                elif cursor == 1: # tyre
                    ti = tyre_list.index(chosen_tyre)
                    chosen_tyre = tyre_list[max(0, ti-1)]

            if ctrl.dpad_right_pressed:
                if cursor == 0:
                    idx = lap_opts.index(chosen_laps)
                    chosen_laps = lap_opts[min(len(lap_opts)-1, idx+1)]
                elif cursor == 1:
                    ti = tyre_list.index(chosen_tyre)
                    chosen_tyre = tyre_list[min(len(tyre_list)-1, ti+1)]

            # △ Triangle = Soft tyre
            if ctrl.triangle_pressed:
                chosen_tyre = "Soft"

            # ○ Circle = Medium tyre
            if ctrl.circle_pressed:
                chosen_tyre = "Medium"

            # □ Square = toggle DRS
            if ctrl.square_pressed:
                auto_drs = not auto_drs

            # ✕ Cross = Hard tyre OR start race
            if ctrl.cross_pressed:
                if cursor == 1:          # on tyre row = select Hard
                    chosen_tyre = "Hard"
                else:                    # anywhere else = start
                    return chosen_laps, chosen_tyre, auto_drs

            # Options = quit
            if ctrl.options_pressed:
                return None, None, None

        # ── Draw ──────────────────────────────────────────────────────────────
        screen.fill((10, 10, 18))
        title = flg.render("F1 2D  —  RACE SETUP", True, WHITE)
        screen.blit(title, ((W - title.get_width())//2, 55))

        pw, ph = 660, 560
        px, py = (W - pw)//2, (H - ph)//2 - 30
        panel  = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 32, 240))
        screen.blit(panel, (px, py))
        pygame.draw.rect(screen, (68,68,110), (px,py,pw,ph), 1, border_radius=12)

        def row_highlight(row_idx, y, h):
            """Draw cursor highlight behind a row if it's selected."""
            if cursor == row_idx:
                hl = pygame.Surface((pw-20, h), pygame.SRCALPHA)
                hl.fill((60, 60, 120, 80))
                screen.blit(hl, (px+10, y))
                pygame.draw.rect(screen, (120,120,220),
                                 (px+10, y, pw-20, h), 1, border_radius=6)

        # ── Row 0: Laps ───────────────────────────────────────────────────────
        row_highlight(0, py+18, 100)
        screen.blit(fmd.render("Number of laps:", True, GRAY), (px+40, py+28))
        for i, lv in enumerate(lap_opts):
            lx = px+40+i*110; ly = py+60; sel = chosen_laps==lv
            pygame.draw.rect(screen, (55,55,80) if sel else (28,28,44),
                             (lx,ly,90,44), border_radius=8)
            if sel:
                pygame.draw.rect(screen, YELLOW, (lx,ly,90,44), 2, border_radius=8)
            lt = fmd.render(str(lv), True, YELLOW if sel else WHITE)
            screen.blit(lt, (lx+(90-lt.get_width())//2, ly+10))

        # Controls hint for laps row
        lap_hint = "D-pad ◄►  or  ← →" if ctrl.connected else "← →  to change"
        screen.blit(fsm.render(lap_hint, True, (100,100,140)), (px+40, py+112))

        pygame.draw.line(screen,(50,50,70),(px+30,py+130),(px+pw-30,py+130),1)

        # ── Row 1: Tyre ───────────────────────────────────────────────────────
        row_highlight(1, py+138, 260)
        screen.blit(fmd.render("Starting tyre:", True, GRAY), (px+40, py+148))

        tyres = [("△  btn 3","Soft",  TYRE_COL["Soft"]),
                 ("○  btn 4","Medium",TYRE_COL["Medium"]),
                 ("✕  btn 0","Hard",  TYRE_COL["Hard"])]
        kb_keys = ["1","2","3"]
        for i,(btn,name,col) in enumerate(tyres):
            ry = py+182+i*78; sel = chosen_tyre==name
            pygame.draw.rect(screen,(50,50,72) if sel else (28,28,42),
                             (px+30,ry,pw-60,66), border_radius=8)
            if sel:
                pygame.draw.rect(screen,col,(px+30,ry,pw-60,66),2,border_radius=8)
            pygame.draw.circle(screen,col,(px+68,ry+33),18)
            pygame.draw.circle(screen,(0,0,0),(px+68,ry+33),18,2)
            # PS5 symbol on left, keyboard key on right
            ps_sym  = btn.split("  ")[0]   # just △ / ○ / ✕
            key_lbl = f"{ps_sym} / [{kb_keys[i]}]" if ctrl.connected else f"[{kb_keys[i]}]"
            screen.blit(fmd.render(f"  {name}", True, WHITE), (px+100, ry+12))
            screen.blit(fsm.render(key_lbl,    True, col),   (px+100, ry+36))
            screen.blit(fsm.render(TYRE_DESC[name], True, GRAY), (px+250, ry+36))
            wr = {"Soft":5,"Medium":2,"Hard":1}[name]
            for d in range(5):
                pygame.draw.circle(screen, col if d<wr else (40,40,50),
                                   (px+pw-90+d*16, ry+33), 5)

        pygame.draw.line(screen,(50,50,70),(px+30,py+422),(px+pw-30,py+422),1)

        # ── Row 2: DRS ────────────────────────────────────────────────────────
        row_highlight(2, py+430, 62)
        drs_col = GREEN if auto_drs else GRAY
        pygame.draw.rect(screen, (30,60,30) if auto_drs else (28,28,42),
                         (px+30,py+438,pw-60,50), border_radius=8)
        pygame.draw.rect(screen, drs_col, (px+30,py+438,pw-60,50), 2, border_radius=8)
        sq_hint = "□ / [D]" if ctrl.connected else "[D]"
        drs_lbl = f"{sq_hint}  DRS: {'AUTO — opens automatically' if auto_drs else 'MANUAL — press Q / □ in zone'}"
        screen.blit(fmd.render(drs_lbl, True, drs_col), (px+54, py+452))

        pygame.draw.line(screen,(50,50,70),(px+30,py+500),(px+pw-30,py+500),1)

        # ── Row 3: Start button ───────────────────────────────────────────────
        row_highlight(3, py+508, 46)
        start_col = YELLOW if cursor==3 else (160,160,80)
        pygame.draw.rect(screen, (40,40,10) if cursor==3 else (28,28,28),
                         (px+30,py+510,pw-60,38), border_radius=8)
        pygame.draw.rect(screen, start_col, (px+30,py+510,pw-60,38), 2, border_radius=8)
        start_hint = "✕ (Cross) / ENTER  to start race" if ctrl.connected else "ENTER  to start race"
        st = fmd.render(start_hint, True, start_col)
        screen.blit(st, (px+(pw-st.get_width())//2, py+518))


# ── Confetti ──────────────────────────────────────────────────────────────────
def _spawn_confetti(confetti,W,H):
    cols=[(220,30,30),(240,200,0),(30,200,80),(0,120,255),(200,0,200),(255,140,0)]
    for _ in range(200):
        confetti.append({"x":random.randint(0,W),"y":random.randint(-120,0),
            "vx":random.uniform(-1.5,1.5),"vy":random.uniform(2.5,6),
            "col":random.choice(cols),"size":random.randint(4,9),
            "rot":random.uniform(0,360),"rot_v":random.uniform(-5,5)})

def _update_confetti(screen,confetti):
    Hh=screen.get_height()
    for p in confetti:
        p["x"]+=p["vx"]; p["y"]+=p["vy"]; p["rot"]+=p["rot_v"]
        p["vy"]=min(p["vy"]+0.06,7)
        if p["y"]>Hh+20: p["y"]=-20
        s=p["size"]
        pts=[(p["x"]+s*math.cos(math.radians(p["rot"]+a)),
              p["y"]+s*math.sin(math.radians(p["rot"]+a))) for a in [0,120,240]]
        pygame.draw.polygon(screen,p["col"],pts)


# ── Celebration ───────────────────────────────────────────────────────────────
def _draw_celebration(screen,winner_msg,finish_order,timer,W,H,fxlg,flg,fmd,fsm):
    fade=min(160,int((1-timer/480)*200))
    ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((0,0,0,fade))
    screen.blit(ov,(0,0))
    pulse_y=int(math.sin(pygame.time.get_ticks()*0.003)*6)
    t=fxlg.render(winner_msg,True,YELLOW)
    screen.blit(t,((W-t.get_width())//2,H//2-200+pulse_y))
    if finish_order:
        pw,ph=520,260; px,py=(W-pw)//2,H//2-80
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA); ps.fill((18,18,30,238))
        screen.blit(ps,(px,py))
        pygame.draw.rect(screen,YELLOW,(px,py,pw,ph),2,border_radius=12)
        r_title=flg.render("RACE RESULTS",True,YELLOW)
        screen.blit(r_title,(px+(pw-r_title.get_width())//2,py+14))
        pos_cols=[YELLOW,(200,200,200),(180,120,40),GRAY]
        for i,(car,nm) in enumerate(finish_order[:4]):
            y=py+72+i*44
            pygame.draw.rect(screen,(30,30,44),(px+20,y-2,pw-40,36),border_radius=5)
            screen.blit(fmd.render(f"P{i+1}",True,pos_cols[i]),(px+30,y+6))
            pygame.draw.circle(screen,car.car_color,(px+80,y+18),10)
            screen.blit(fmd.render(nm,True,WHITE if nm!="YOU" else YELLOW),(px+100,y+6))
            tc=TYRE_COL.get(car.compound,(200,200,200))
            pygame.draw.circle(screen,tc,(px+300,y+18),8)
            screen.blit(fsm.render(car.compound,True,GRAY),(px+316,y+12))
    if timer<240:
        r=fmd.render("Press R for new race   ESC to quit",True,GRAY)
        screen.blit(r,((W-r.get_width())//2,H//2+210))


# ── HUD ───────────────────────────────────────────────────────────────────────
def _hud(screen,player,standings,laps,total,lap_start,best_lap,last_lap,
         drs_zone,auto_drs,track,W,H,fhud,fpit,fsm,fmd,ctrl=None):
    now=pygame.time.get_ticks()
    curr=now-lap_start if lap_start else 0

    ts=pygame.Surface((W,54),pygame.SRCALPHA); ts.fill((8,8,16,228))
    screen.blit(ts,(0,0)); pygame.draw.line(screen,(52,52,76),(0,54),(W,54),1)

    def hcol(x,lbl,val,vc=WHITE):
        screen.blit(fsm.render(lbl,True,GRAY),(x,8))
        screen.blit(fhud.render(val,True,vc),(x,24))

    hcol(16,"LAP",f"{laps}/{total}")
    hcol(115,"CURRENT",fmt_time(curr))
    hcol(300,"BEST",fmt_time(best_lap),PURPLE)
    hcol(468,"LAST",fmt_time(last_lap))
    spd=int(player.velocity.length()*27)
    hcol(638,"KM/H",str(spd))
    gear=min(8,max(1,int(player.velocity.length()/0.9)+1))
    hcol(728,"GEAR",str(gear),YELLOW)
    # Track name centre top
    tn = fsm.render(f"📍 {track.name}", True, (160,160,180))
    screen.blit(tn, ((W-tn.get_width())//2, 18))

    if player.drs_open: dc=GREEN; dbc=(0,80,0,200)
    elif player.drs_available: dc=ORANGE; dbc=(60,40,0,200)
    else: dc=(55,55,65); dbc=(20,20,28,200)
    dbs=pygame.Surface((90,34),pygame.SRCALPHA); dbs.fill(dbc)
    screen.blit(dbs,(818,10)); pygame.draw.rect(screen,dc,(818,10,90,34),2,border_radius=4)
    drs_txt="DRS AUTO" if auto_drs else ("DRS OPEN" if player.drs_open else "DRS [Q]")
    screen.blit(fhud.render(drs_txt,True,dc),(825,18))

    tc=TYRE_COL[player.compound]
    pygame.draw.circle(screen,tc,(965,27),19); pygame.draw.circle(screen,(0,0,0),(965,27),19,2)
    bl=fsm.render(player.compound[0],True,(0,0,0) if player.compound=="Hard" else WHITE)
    screen.blit(bl,(959,19)); screen.blit(fsm.render(player.compound,True,tc),(990,21))

    my_pos=next((i+1 for i,(c,_) in enumerate(standings) if c is player),"?")
    hcol(1060,"POSITION",f"P{my_pos}",YELLOW if my_pos==1 else WHITE)

    bs=pygame.Surface((W,56),pygame.SRCALPHA); bs.fill((8,8,16,228))
    screen.blit(bs,(0,H-56)); pygame.draw.line(screen,(52,52,76),(0,H-56),(W,H-56),1)
    by=H-56

    # Controller status badge
    using_ctrl = ctrl and ctrl.connected
    badge_col  = GREEN if using_ctrl else (80,80,100)
    badge_txt  = "PS5" if using_ctrl else "KB"
    pygame.draw.rect(screen, (20,40,20) if using_ctrl else (28,28,38),
                     (16, by+6, 38, 22), border_radius=4)
    pygame.draw.rect(screen, badge_col, (16, by+6, 38, 22), 1, border_radius=4)
    screen.blit(fsm.render(badge_txt, True, badge_col), (20, by+10))

    screen.blit(fsm.render("THROTTLE",True,GRAY),(62,by+4))
    bar(screen,62,by+20,110,12,player.velocity.length()/8.5,GREEN)
    screen.blit(fsm.render("TYRE WEAR",True,GRAY),(190,by+4))
    bar(screen,190,by+20,138,12,player.tyre_health/100.0,tyre_col(player.tyre_health))
    screen.blit(fsm.render(f"{int(player.tyre_health)}%",True,tyre_col(player.tyre_health)),(337,by+18))

    if using_ctrl:
        hints = "R2=throttle  L2=brake  L-stick=steer  □=DRS  △/○/✕=tyres  Options=restart"
    else:
        q_hint = "" if auto_drs else "  Q=DRS"
        hints  = f"W/S=throttle  A/D=steer{q_hint}  1/2/3=pit tyres  R=restart  ESC=quit"
    screen.blit(fsm.render(hints, True,(70,70,90)),(370,by+20))

    if player.rect.colliderect(track.pit_box) and not player.is_pitting:
        tyre_hint = "△=Soft  ○=Medium  ✕=Hard" if using_ctrl else "1=Soft  2=Medium  3=Hard"
        g=fmd.render(f"PIT BOX — {tyre_hint}",True,YELLOW)
        screen.blit(g,(W//2-g.get_width()//2,H-90))
    if player.is_pitting:
        msg=fpit.render(f"BOXING  {player.pit_timer/60:.1f}s",True,YELLOW)
        screen.blit(msg,(W//2-msg.get_width()//2,H//2-32))

    sx2=W-238; ph2=38+len(standings)*40
    sp=pygame.Surface((230,ph2),pygame.SRCALPHA); sp.fill((8,8,16,220))
    screen.blit(sp,(sx2-6,60)); pygame.draw.rect(screen,(52,52,76),(sx2-6,60,230,ph2),1)
    screen.blit(fsm.render("STANDINGS",True,GRAY),(sx2,64))
    for r,(car,nm) in enumerate(standings):
        y=86+r*40; is_you=nm=="YOU"
        if is_you: pygame.draw.rect(screen,(36,36,16),(sx2-5,y-4,228,32))
        pc=YELLOW if is_you else WHITE
        screen.blit(fsm.render(f"P{r+1}",True,pc),(sx2,y))
        pygame.draw.circle(screen,car.car_color,(sx2+38,y+8),9)
        screen.blit(fsm.render(nm,True,WHITE),(sx2+52,y))
        ct=TYRE_COL[car.compound]
        pygame.draw.circle(screen,ct,(sx2+132,y+8),6)
        screen.blit(fsm.render(f"{int(car.tyre_health)}%",True,tyre_col(car.tyre_health)),(sx2+146,y))

    if player.tyre_health<25 and (now//500)%2==0:
        w=fmd.render("TYRE WARNING — PIT NOW",True,RED)
        screen.blit(w,(W//2-w.get_width()//2,64))
    elif drs_zone and not player.drs_open and not auto_drs:
        dz=fmd.render("DRS ZONE — Press Q",True,ORANGE)
        screen.blit(dz,(W//2-dz.get_width()//2,62))
    elif player.drs_open:
        dz=fmd.render("DRS OPEN",True,GREEN)
        screen.blit(dz,(W//2-dz.get_width()//2,62))


if __name__=="__main__":
    main()