import pygame, math


def _offset_polygon(points, offset):
    result = []
    n = len(points)
    for i in range(n):
        p0=points[(i-1)%n]; p1=points[i]; p2=points[(i+1)%n]
        d1=(p1[0]-p0[0],p1[1]-p0[1]); l1=math.hypot(*d1) or 1
        n1=(-d1[1]/l1,d1[0]/l1)
        d2=(p2[0]-p1[0],p2[1]-p1[1]); l2=math.hypot(*d2) or 1
        n2=(-d2[1]/l2,d2[0]/l2)
        nx=n1[0]+n2[0]; ny=n1[1]+n2[1]; nl=math.hypot(nx,ny) or 1
        result.append((int(p1[0]+nx/nl*offset), int(p1[1]+ny/nl*offset)))
    return result


# Verified non-crossing waypoints (generated mathematically)
TRACKS = [
    {
        "name":'Albert Park', "country":'Australia 🇦🇺', "grass":(34, 128, 34),
        "sf":4, "cp":16,
        "wps":[(1216, 710), (1101, 726), (986, 750), (872, 710), (759, 670), (642, 694), (526, 710), (411, 710), (296, 710), (247, 702), (202, 679), (167, 644), (144, 599), (136, 550), (136, 518), (136, 485), (136, 452), (136, 420), (136, 388), (136, 355), (136, 322), (144, 241), (167, 196), (202, 161), (247, 138), (296, 130), (411, 130), (526, 130), (641, 130), (756, 108), (871, 75), (984, 130), (1095, 185), (1263, 160), (1310, 161), (1345, 196), (1368, 241), (1376, 290), (1376, 322), (1376, 355), (1376, 388), (1376, 420), (1376, 452), (1376, 485), (1376, 518), (1368, 599), (1345, 644), (1310, 679), (1265, 702), (1216, 710)],
    },
    {
        "name":'Monaco', "country":'Monaco 🇲🇨', "grass":(20, 92, 20),
        "sf":3, "cp":14,
        "wps":[(1146, 670), (1016, 690), (890, 700), (765, 641), (630, 650), (496, 670), (366, 670), (326, 664), (270, 659), (230, 655), (267, 604), (254, 544), (236, 500), (236, 460), (236, 420), (214, 379), (181, 337), (220, 259), (261, 224), (290, 195), (326, 176), (366, 152), (493, 143), (618, 196), (753, 188), (886, 170), (1016, 170), (1174, 193), (1193, 235), (1239, 240), (1270, 260), (1276, 300), (1276, 340), (1276, 380), (1276, 420), (1276, 460), (1276, 500), (1270, 580), (1251, 616), (1222, 645), (1186, 664), (1146, 670)],
    },
    {
        "name":'Silverstone', "country":'Great Britain 🇬🇧', "grass":(42, 148, 42),
        "sf":5, "cp":18,
        "wps":[(1186, 710), (1090, 710), (995, 710), (899, 710), (804, 710), (708, 710), (613, 710), (517, 710), (422, 710), (326, 710), (274, 703), (226, 683), (185, 651), (153, 610), (133, 562), (126, 510), (98, 490), (56, 470), (121, 466), (183, 470), (123, 437), (61, 417), (100, 381), (126, 350), (133, 278), (153, 230), (185, 189), (226, 157), (274, 137), (326, 130), (422, 130), (517, 130), (613, 130), (708, 130), (804, 130), (899, 156), (995, 195), (1090, 156), (1238, 137), (1286, 157), (1327, 189), (1359, 230), (1379, 278), (1386, 330), (1386, 350), (1386, 370), (1386, 390), (1386, 410), (1386, 430), (1386, 450), (1386, 470), (1386, 490), (1379, 562), (1359, 610), (1327, 651), (1286, 683), (1238, 703), (1186, 710)],
    },
    {
        "name":'Monza', "country":'Italy 🇮🇹', "grass":(30, 115, 30),
        "sf":5, "cp":16,
        "wps":[(1186, 710), (1090, 732), (1001, 744), (915, 679), (810, 689), (708, 710), (613, 710), (517, 710), (422, 710), (326, 710), (242, 693), (170, 646), (123, 574), (106, 490), (106, 474), (106, 459), (106, 443), (106, 428), (106, 412), (106, 397), (106, 381), (106, 366), (123, 266), (179, 215), (254, 177), (313, 100), (413, 110), (517, 130), (613, 130), (708, 130), (804, 130), (899, 130), (995, 130), (1090, 130), (1270, 147), (1342, 194), (1389, 266), (1406, 350), (1406, 366), (1406, 381), (1406, 397), (1406, 412), (1406, 428), (1406, 443), (1406, 459), (1406, 474), (1389, 574), (1342, 646), (1270, 693), (1186, 710)],
    },
    {
        "name":'Suzuka', "country":'Japan 🇯🇵', "grass":(36, 132, 36),
        "sf":4, "cp":16,
        "wps":[(1201, 700), (1090, 700), (978, 700), (867, 700), (756, 700), (645, 700), (534, 700), (422, 700), (311, 700), (257, 691), (184, 684), (109, 672), (150, 601), (210, 537), (139, 517), (69, 507), (109, 460), (136, 420), (136, 394), (136, 368), (136, 341), (145, 261), (169, 212), (208, 173), (257, 149), (311, 140), (422, 140), (534, 140), (645, 140), (756, 166), (860, 180), (960, 104), (1082, 115), (1255, 149), (1288, 185), (1302, 242), (1351, 273), (1376, 315), (1376, 341), (1376, 368), (1376, 394), (1376, 420), (1376, 446), (1376, 472), (1376, 499), (1367, 579), (1343, 628), (1304, 667), (1255, 691), (1201, 700)],
    },
    {
        "name":'Spa-Francorchamps', "country":'Belgium 🇧🇪', "grass":(44, 152, 44),
        "sf":5, "cp":19,
        "wps":[(1221, 710), (1128, 710), (1035, 710), (942, 710), (849, 710), (756, 710), (663, 710), (570, 710), (477, 710), (384, 710), (291, 710), (234, 701), (153, 696), (94, 693), (149, 618), (131, 531), (106, 504), (106, 483), (106, 462), (106, 441), (106, 420), (106, 399), (106, 378), (106, 357), (106, 336), (115, 258), (127, 187), (145, 141), (214, 179), (289, 154), (384, 130), (477, 102), (570, 60), (663, 102), (756, 130), (849, 130), (942, 152), (1031, 163), (1118, 98), (1274, 117), (1330, 165), (1371, 206), (1397, 258), (1406, 315), (1406, 336), (1406, 357), (1406, 378), (1406, 399), (1406, 420), (1406, 441), (1406, 462), (1406, 483), (1406, 504), (1397, 582), (1371, 634), (1330, 675), (1278, 701), (1221, 710)],
    },
    {
        "name":'COTA', "country":'USA 🇺🇸', "grass":(35, 125, 35),
        "sf":4, "cp":16,
        "wps":[(1196, 700), (1086, 700), (976, 700), (866, 700), (756, 700), (646, 700), (536, 700), (426, 700), (316, 700), (242, 717), (163, 730), (152, 652), (145, 576), (110, 520), (71, 495), (133, 482), (194, 475), (135, 441), (75, 418), (112, 379), (136, 345), (167, 281), (227, 255), (233, 191), (260, 149), (316, 140), (426, 140), (536, 140), (646, 140), (756, 140), (866, 140), (976, 140), (1086, 140), (1252, 149), (1302, 174), (1342, 214), (1367, 264), (1376, 320), (1376, 345), (1376, 370), (1376, 395), (1376, 420), (1376, 445), (1376, 470), (1376, 495), (1367, 576), (1342, 626), (1302, 666), (1252, 691), (1196, 700)],
    },
    {
        "name":'Interlagos', "country":'Brazil 🇧🇷', "grass":(46, 155, 46),
        "sf":4, "cp":15,
        "wps":[(1181, 690), (1075, 712), (974, 724), (876, 659), (762, 669), (650, 690), (544, 690), (437, 690), (331, 690), (280, 682), (234, 658), (198, 622), (174, 576), (166, 525), (166, 499), (166, 472), (166, 446), (166, 420), (166, 394), (166, 368), (166, 341), (197, 280), (233, 254), (203, 184), (259, 153), (331, 150), (437, 150), (544, 150), (650, 150), (756, 150), (862, 150), (968, 150), (1075, 150), (1232, 158), (1278, 182), (1295, 224), (1290, 279), (1327, 321), (1346, 341), (1346, 368), (1346, 394), (1346, 420), (1346, 446), (1346, 472), (1346, 499), (1338, 576), (1314, 622), (1278, 658), (1232, 682), (1181, 690)],
    },
    {
        "name":'Bahrain', "country":'Bahrain 🇧🇭', "grass":(188, 168, 118),
        "sf":4, "cp":16,
        "wps":[(1186, 700), (1078, 700), (971, 700), (864, 700), (756, 700), (648, 700), (541, 700), (434, 700), (326, 700), (255, 712), (208, 713), (229, 635), (180, 571), (146, 520), (146, 495), (146, 470), (146, 445), (146, 420), (146, 395), (146, 370), (146, 345), (155, 264), (180, 214), (220, 174), (269, 121), (322, 70), (432, 112), (541, 164), (642, 177), (740, 106), (857, 117), (971, 140), (1078, 140), (1242, 149), (1292, 174), (1332, 214), (1357, 264), (1366, 320), (1366, 345), (1366, 370), (1366, 395), (1366, 420), (1366, 445), (1366, 470), (1366, 495), (1357, 576), (1332, 626), (1292, 666), (1242, 691), (1186, 700)],
    },
    {
        "name":'Singapore', "country":'Singapore 🇸🇬', "grass":(15, 65, 15),
        "sf":3, "cp":14,
        "wps":[(1156, 680), (1042, 704), (933, 721), (826, 656), (704, 661), (585, 680), (470, 680), (356, 680), (294, 694), (230, 704), (219, 639), (213, 576), (228, 530), (246, 512), (190, 500), (191, 449), (206, 404), (184, 371), (151, 338), (191, 262), (235, 222), (274, 208), (319, 198), (346, 137), (464, 143), (585, 160), (699, 182), (813, 215), (927, 182), (1042, 160), (1202, 167), (1244, 189), (1277, 222), (1299, 264), (1306, 310), (1306, 341), (1306, 373), (1306, 404), (1306, 436), (1306, 467), (1306, 499), (1299, 576), (1277, 618), (1244, 651), (1202, 673), (1156, 680)],
    }
]


class Track:
    def __init__(self, width, height, track_id=0):
        self.width    = width
        self.height   = height
        self.track_id = track_id % len(TRACKS)
        self.image    = pygame.Surface((width, height))

        defn         = TRACKS[self.track_id]
        self.name    = defn["name"]
        self.country = defn["country"]

        sx = width  / 1512
        sy = height / 982
        ML=65; MR=65; MT=65; MB=75

        def s(x, y):
            return (int(max(ML, min(width-MR,   x*sx))),
                    int(max(MT, min(height-MB-int(75*sy), y*sy))))

        self.waypoints = [s(x,y) for x,y in defn["wps"]]
        N  = len(self.waypoints)
        hw = int(50*sx)

        gc  = defn["grass"]
        gc2 = tuple(min(255,c+14) for c in gc)
        gc3 = tuple(max(0,  c-12) for c in gc)
        self.image.fill(gc)
        for row in range(0, height, 22):
            c = gc2 if (row//22)%2==0 else gc3
            pygame.draw.rect(self.image, c, (0,row,width,22))

        pts = self.waypoints

        vo = _offset_polygon(pts,  hw+22)
        vi = _offset_polygon(pts, -(hw+22))
        vc = tuple(min(255,c+20) for c in gc)
        pygame.draw.polygon(self.image, vc, vo+list(reversed(vi)))

        ko = _offset_polygon(pts,  hw+8)
        ki = _offset_polygon(pts, -(hw+8))
        for i in range(N):
            j=(i+1)%N
            col=(218,28,28) if (i//2)%2==0 else (242,242,242)
            pygame.draw.polygon(self.image, col, [ko[i],ko[j],ki[j],ki[i]])

        ao = _offset_polygon(pts,  hw)
        ai = _offset_polygon(pts, -hw)
        pygame.draw.polygon(self.image, (70,70,76), ao+list(reversed(ai)))
        mo = _offset_polygon(pts,  hw-18)
        mi = _offset_polygon(pts, -(hw-18))
        pygame.draw.polygon(self.image, (76,76,82), mo+list(reversed(mi)))

        for i in range(N):
            j=(i+1)%N
            pygame.draw.line(self.image,(208,208,208),ao[i],ao[j],2)
            pygame.draw.line(self.image,(208,208,208),ai[i],ai[j],2)

        for i in range(N):
            j=(i+1)%N; p1,p2=pts[i],pts[j]
            dx,dy=p2[0]-p1[0],p2[1]-p1[1]; L=math.hypot(dx,dy)
            if L==0: continue
            nx,ny=dx/L,dy/L; steps=max(1,int(L//28))
            for k in range(steps):
                t0,t1=k/steps,(k+0.42)/steps
                a=(int(p1[0]+nx*L*t0),int(p1[1]+ny*L*t0))
                b=(int(p1[0]+nx*L*t1),int(p1[1]+ny*L*t1))
                pygame.draw.line(self.image,(200,180,0),a,b,2)

        straight_y = self.waypoints[0][1]
        asp_south  = straight_y + hw
        pit_top    = asp_south + 8
        pit_bot    = pit_top + max(32, int(40*sy))
        pit_h      = pit_bot - pit_top
        pit_mid_y  = pit_top + pit_h//2

        home_xs   = [self.waypoints[i][0] for i in range(min(8,N))]
        pit_right = min(width-MR, max(home_xs) + int(8*sx))
        pit_left  = max(ML,       min(home_xs) - int(8*sx))

        self.pit_lane_rect = pygame.Rect(pit_left, pit_top, pit_right-pit_left, pit_h)

        ep_x = pit_right - int(4*sx)
        sp_x = pit_left  + int(4*sx)
        pygame.draw.polygon(self.image,(58,58,64),
            [(ep_x,asp_south-1),(pit_right,pit_top),(pit_right,pit_bot),(ep_x,asp_south+3)])
        pygame.draw.polygon(self.image,(58,58,64),
            [(sp_x,asp_south-1),(pit_left,pit_top),(pit_left,pit_bot),(sp_x,asp_south+3)])
        pygame.draw.rect(self.image,(58,58,64),self.pit_lane_rect)
        pygame.draw.line(self.image,(235,235,235),(pit_left,pit_top),(pit_right,pit_top),5)
        pygame.draw.line(self.image,(160,160,160),(pit_left,pit_bot),(pit_right,pit_bot),2)
        for x in range(pit_left+24, pit_right-10, 50):
            pygame.draw.rect(self.image,(255,255,255),(x,pit_bot-8,22,5))
        for x in range(pit_left+16, pit_right-10, 36):
            pygame.draw.rect(self.image,(200,180,0),(x,pit_mid_y-2,16,4))

        pb_cx = (pit_left+pit_right)//2
        pb_w  = int(95*sx); pb_x=pb_cx-pb_w//2
        self.pit_box = pygame.Rect(pb_x, pit_top+2, pb_w, pit_h-4)
        pygame.draw.rect(self.image,(0,48,178),self.pit_box)
        pygame.draw.rect(self.image,(255,255,255),self.pit_box,2)
        for lx in range(pb_x+4, pb_x+pb_w-2, 11):
            pygame.draw.line(self.image,(0,72,210),(lx,pit_top+3),(lx,pit_bot-3),1)
        pf = pygame.font.SysFont("Arial",14,bold=True)
        self.image.blit(pf.render("PIT",True,(255,255,255)),(pb_cx-16,pit_mid_y-8))

        drs_x = ep_x - int(40*sx)
        self.drs_detection = pygame.Rect(drs_x-8, straight_y-hw, 16, hw*2)
        pygame.draw.line(self.image,(140,62,252),(drs_x,straight_y-hw),
                         (drs_x,straight_y+hw),4)

        sf_x  = self.waypoints[defn["sf"]][0]
        sf_y0 = straight_y - hw
        sf_h2 = hw*2
        self.finish_line = pygame.Rect(sf_x, sf_y0, 15, sf_h2)
        sq = max(7, sf_h2//10)
        for row in range(10):
            c=(255,255,255) if row%2==0 else (0,0,0)
            pygame.draw.rect(self.image,c,(sf_x,sf_y0+row*sq,15,sq))
        pygame.draw.rect(self.image,(255,215,0),self.finish_line,1)
        self.image.blit(pf.render("S/F",True,(255,215,0)),(sf_x-32,sf_y0+2))

        cp_wp = self.waypoints[defn["cp"]]
        self.checkpoint = pygame.Rect(cp_wp[0]-5, cp_wp[1]-hw, 10, hw*2)
        pygame.draw.rect(self.image,(85,85,85),self.checkpoint)

        for i in range(4, N, max(3, N//14)):
            pt = self.waypoints[i]
            pygame.draw.circle(self.image,(24,24,24),pt,7)
            pygame.draw.circle(self.image,(195,24,24),pt,7,2)

        last_wp = self.waypoints[-1]
        self.pit_entry_waypoints = [
            last_wp,
            (last_wp[0], straight_y),
            (ep_x, asp_south),
            (pit_right-8, pit_mid_y),
            (pb_cx+pb_w//2, pit_mid_y),
            (pb_cx, pit_mid_y),
        ]
        self.pit_box_centre = pygame.math.Vector2(pb_cx, pit_mid_y)
        self.rect = self.image.get_rect(topleft=(0,0))

    def draw(self, screen):
        screen.blit(self.image, self.rect)


def get_track_names():
    return [(i, t["name"], t["country"]) for i,t in enumerate(TRACKS)]