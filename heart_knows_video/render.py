"""Render the animated video for "The Heart Knows (Tempo Shift Take)".

A man comes in, takes a jacket from the hook and leaves, seven times with
seven different jackets. The fern on the balcony withers across the song.
At the end a mirror hangs on the hook and his reflection has no face.

Usage:
    python3 render.py COVER.jpg AUDIO.wav OUT.mp4 [--endcard CARD.png] [--preview SECONDS ...]
"""
import math
import os
import random
import subprocess
import sys
from multiprocessing import Pool

from PIL import Image, ImageDraw, ImageChops

W, H = 1408, 768
SS = 2                      # supersampling factor
FPS = 24
DURATION = 157.57
ENDCARD_SECONDS = 5.5          # landing page after the song: total about 2:43

INK = (22, 24, 12)
LW = 2.6                    # line width at 1x

# ---------------------------------------------------------------- helpers

def S(v):
    return v * SS


def pts(seq):
    return [(S(x), S(y)) for x, y in seq]


def poly(d, seq, fill, outline=INK, width=LW):
    p = pts(seq)
    d.polygon(p, fill=fill)
    if outline is not None:
        d.line(p + [p[0]], fill=outline, width=max(1, int(round(S(width)))), joint="curve")


def line(d, seq, fill=INK, width=LW):
    d.line(pts(seq), fill=fill, width=max(1, int(round(S(width)))), joint="curve")


def ellipse(d, cx, cy, rx, ry, fill, outline=INK, width=LW):
    d.ellipse([S(cx - rx), S(cy - ry), S(cx + rx), S(cy + ry)], fill=fill,
              outline=outline, width=max(1, int(round(S(width)))) if outline else 0)


def lerp(a, b, t):
    return a + (b - a) * t


def lerpc(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))


def clamp01(t):
    return max(0.0, min(1.0, t))


def smooth(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def rot(px, py, ang, ox=0.0, oy=0.0):
    c, s = math.cos(ang), math.sin(ang)
    x, y = px - ox, py - oy
    return ox + x * c - y * s, oy + x * s + y * c


def darker(c, f=0.78):
    return tuple(int(v * f) for v in c)


# ---------------------------------------------------------------- background

WALL_L = (136, 140, 117)
WALL_R = (115, 118, 100)
RAIL = (62, 71, 71)
DECK = (163, 146, 122)
WALL_LOW = (142, 146, 127)

PANEL_X = 625               # dividing line between the two panels
RWALL = (117, 123, 89)
CONE = (187, 183, 110)
CONE_LOW = (160, 158, 120)
SHADOW = (100, 109, 108)
LAMP = (248, 229, 140)


def build_background(cover_path):
    cover = Image.open(cover_path).convert("RGB").resize((W, H))
    big = cover.resize((S(W), S(H)), Image.LANCZOS)
    d = ImageDraw.Draw(big)

    # --- left panel: paint out the original fern and rebuild what was behind it
    x0, x1, y0, y1 = 398, 624, 272, 549
    d.rectangle([S(x0), S(y0), S(PANEL_X) - 1, S(y1)], fill=WALL_L)
    d.rectangle([S(558), S(y0), S(PANEL_X) - 1, S(538)], fill=WALL_R)
    line(d, [(558, y0), (558, 380)], width=2.2)                    # wall corner
    d.rectangle([S(x0), S(531), S(PANEL_X) - 1, S(538)], fill=WALL_LOW)
    # deck
    d.rectangle([S(x0), S(538), S(PANEL_X) - 1, S(y1 + 2)], fill=DECK)
    line(d, [(x0, 538), (PANEL_X, 538)], width=2.0)
    for xb in (409, 448, 492, 538, 589):
        line(d, [(xb + 7.5, 538), (xb - 5, y1 + 3)], fill=(60, 44, 24), width=2.0)
    # wires
    for i, yw in enumerate((407.5, 427.5, 447, 465.5, 484.5, 503.5)):
        line(d, [(x0, yw), (551, yw - 0.010 * (i + 1) * 151)], width=1.8)
    # top bar
    poly(d, [(x0, 380), (558, 376), (558, 385), (x0, 389)], RAIL, width=2.0)
    # bottom bar
    poly(d, [(x0, 521), (551, 515), (551, 523), (x0, 530)], RAIL, width=2.0)
    # posts
    poly(d, [(422, 386), (430, 386), (430, 538), (422, 538)], RAIL, width=2.0)
    poly(d, [(550, 377), (558, 377), (558, 524), (550, 524)], RAIL, width=2.0)

    # --- right panel: redraw wall, lamp, light cone and hook (coat removed)
    d.rectangle([S(PANEL_X + 2), 0, S(W), S(H)], fill=RWALL)
    cone = [(706, 95), (873, 95), (1096, 336), (1096, H), (PANEL_X + 2, H), (PANEL_X + 2, 362)]
    d.polygon(pts(cone), fill=CONE)
    # soft lower falloff of the light, like the original's paler floor zone
    low = [(PANEL_X + 2, 560), (1096, 470), (1096, H), (PANEL_X + 2, H)]
    lay = Image.new("RGB", big.size, CONE_LOW)
    m = Image.new("L", big.size, 0)
    ImageDraw.Draw(m).polygon(pts(low), fill=255)
    mc = Image.new("L", big.size, 0)
    ImageDraw.Draw(mc).polygon(pts(cone), fill=255)
    m = ImageChops.multiply(m, mc).point(lambda v: int(v * 0.55))
    big.paste(lay, (0, 0), m)
    d = ImageDraw.Draw(big)
    # lamp
    poly(d, [(706, -5), (873, -5), (873, 95), (706, 95)], LAMP, width=2.2)
    # hook plate
    poly(d, [(776, 160), (880, 150), (880, 252), (776, 258)], (92, 100, 96), outline=None)
    poly(d, [(768, 155), (872, 146), (872, 246), (768, 252)], (170, 168, 140), width=2.2)
    line(d, [(PANEL_X, 0), (PANEL_X, H)], width=2.6)
    return big


def draw_hook(d):
    """The S hook, drawn on top of anything hanging from it."""
    for col, w in ((INK, 7.5), ((92, 100, 98), 4.0)):
        line(d, [(822, 175), (822, 222), (812, 230), (800, 232)], fill=col, width=w)
        line(d, [(822, 175), (840, 172), (842, 215)], fill=col, width=w)
        line(d, [(800, 232), (786, 226), (781, 236), (790, 248), (806, 248)], fill=col, width=w)


# ---------------------------------------------------------------- plant

PLANT_CX, PLANT_CY = 541, 474
GREEN_D = (40, 58, 32)
GREEN_L = (150, 166, 98)
YELLOW = (176, 164, 78)
BROWN = (120, 92, 52)
BROWN_D = (78, 58, 30)


def health(t):
    """1 = lush, 0 = dead. Healthy through the bloom, then withers to the end."""
    return 1.0 - smooth((t - 70.0) / 78.0) ** 0.85


def growth(t):
    return 0.82 + 0.18 * smooth(t / 45.0)


PINK = (222, 118, 168)
PINK_D = (176, 78, 128)
FADED = (176, 128, 128)
CENTER = (232, 192, 84)


class Plant:
    def __init__(self):
        rng = random.Random(7)
        self.fronds = []
        n = 15
        for i in range(n):
            a = math.radians(lerp(-172, -8, i / (n - 1)) + rng.uniform(-6, 6))
            L = rng.uniform(140, 195) * (0.8 if abs(math.degrees(a) + 90) > 60 else 1.0)
            leaflets = []
            k = int(L / 10)
            for j in range(2, k):
                s = j / k
                for side in (-1, 1):
                    leaflets.append(dict(s=s, side=side,
                                         u=rng.uniform(0.04, 0.93) ** 0.8,
                                         tint=rng.uniform(-0.12, 0.12),
                                         land=(rng.uniform(395, 620), rng.uniform(542, 600)),
                                         spin=rng.uniform(-3.0, 3.0),
                                         drift=rng.uniform(-30, 30)))
            self.fronds.append(dict(a=a, L=L, leaflets=leaflets,
                                    collapse=rng.uniform(0.03, 0.2),
                                    sway=rng.uniform(0, 6.28)))
        self.flowers = []
        for i in range(9):
            a = math.radians(lerp(-140, -40, i / 8) + rng.uniform(-8, 8))
            self.flowers.append(dict(
                a=a, L=rng.uniform(105, 160), open=rng.uniform(14, 40),
                wilt=rng.uniform(88, 104), sway=rng.uniform(0, 6.28),
                petals=[dict(td=rng.uniform(100, 128), land=(rng.uniform(400, 620), rng.uniform(544, 604)),
                             spin=rng.uniform(-3, 3), drift=rng.uniform(-25, 25)) for _ in range(8)]))
        # time at which each leaflet drops
        samples = [(i / 10.0, health(i / 10.0)) for i in range(int(DURATION * 10) + 1)]
        for f in self.fronds:
            for lf in f["leaflets"]:
                lf["td"] = next((tt for tt, hh in samples if hh < lf["u"]), 1e9)

    def frond_point(self, f, h, s, t):
        a = f["a"] + 0.015 * math.sin(t * 0.7 + f["sway"]) * h
        L = f["L"] * (0.92 + 0.08 * h) * growth(t)
        dx, dy = math.cos(a), math.sin(a)
        droop = (1 - h) * 1.25
        if h < f["collapse"]:
            droop += (f["collapse"] - h) * 6
        out = 1 if dx >= 0 else -1
        x = PLANT_CX + dx * L * s + out * droop * 0.25 * L * s * s
        y = PLANT_CY + dy * L * s + droop * L * s * s
        return x, y

    def leaf_poly(self, cx, cy, ang, ln, wd):
        c, s = math.cos(ang), math.sin(ang)
        loc = [(0, 0), (ln * 0.35, -wd), (ln, 0), (ln * 0.35, wd)]
        return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in loc]

    def leaf_color(self, h, tint):
        dead = clamp01(1 - h + tint)
        if dead < 0.5:
            return lerpc(GREEN_L, YELLOW, dead * 2)
        return lerpc(YELLOW, BROWN, (dead - 0.5) * 2)

    def draw(self, d, t):
        h = health(t)
        stem = lerpc(GREEN_D, BROWN_D, 1 - h)
        floor_leaves, falling = [], []
        # back fronds first (upright ones last so they read on top)
        order = sorted(self.fronds, key=lambda f: -abs(math.cos(f["a"])))
        for f in order:
            path = [self.frond_point(f, h, i / 12, t) for i in range(13)]
            line(d, path, fill=stem, width=2.2)
            for lf in f["leaflets"]:
                s = lf["s"]
                px, py = self.frond_point(f, h, s, t)
                qx, qy = self.frond_point(f, h, min(1, s + 0.02), t)
                fa = math.atan2(qy - py, qx - px)
                spread = math.radians(lerp(28, 58, h))
                la = fa + lf["side"] * spread
                ln = 21 * (1.05 - 0.45 * s) * (0.75 + 0.25 * h)
                wd = 3.6 * (0.6 + 0.4 * h)
                col = self.leaf_color(h, lf["tint"])
                if t < lf["td"]:
                    poly(d, self.leaf_poly(px, py, la, ln, wd), col, outline=stem, width=1.3)
                else:
                    col = self.leaf_color(min(health(lf["td"]), 0.3), lf["tint"])
                    dt = t - lf["td"]
                    fall = 1.6
                    sx, sy = self.frond_point(f, health(lf["td"]), s, lf["td"])
                    lx, ly = lf["land"]
                    if dt < fall:
                        k = dt / fall
                        x = lerp(sx, lx, k) + math.sin(k * 6) * lf["drift"] * (1 - k)
                        y = lerp(sy, ly, k * k)
                        falling.append((self.leaf_poly(x, y, la + lf["spin"] * k, ln, wd), col))
                    else:
                        floor_leaves.append((self.leaf_poly(lx, ly, lf["spin"] * 0.3, ln * 0.95, wd * 0.6),
                                             lerpc(col, BROWN, 0.5)))
        # flowers ride above the foliage
        for fl in self.flowers:
            self.draw_flower(d, fl, t, h, floor_leaves, falling)
        return floor_leaves, falling

    def flower_point(self, fl, s, t):
        h = health(t)
        a = fl["a"] + 0.02 * math.sin(t * 0.8 + fl["sway"])
        L = fl["L"] * growth(t)
        wilt = smooth((t - fl["wilt"]) / 30.0)
        dx, dy = math.cos(a), math.sin(a)
        out = 1 if dx >= 0 else -1
        droop = wilt * 1.5 + (1 - h) * 0.5
        return (PLANT_CX + dx * L * s + out * droop * 0.3 * L * s * s,
                PLANT_CY + dy * L * s + droop * L * s * s)

    def petal_poly(self, cx, cy, ang, r, w):
        c, s = math.cos(ang), math.sin(ang)
        loc = [(0, 0), (r * 0.5, -w), (r, -w * 0.6), (r * 1.08, 0), (r, w * 0.6), (r * 0.5, w)]
        return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in loc]

    def draw_flower(self, d, fl, t, h, floor_leaves, falling):
        stem = lerpc(GREEN_D, BROWN_D, clamp01((t - fl["wilt"]) / 35.0))
        path = [self.flower_point(fl, i / 10, t) for i in range(11)]
        line(d, path, fill=stem, width=2.0)
        x, y = path[-1]
        bloom = smooth((t - fl["open"]) / 16.0)
        wilt = smooth((t - fl["wilt"]) / 30.0)
        col = lerpc(lerpc(PINK, FADED, wilt * 1.4), BROWN, max(0.0, wilt - 0.55) * 2)
        if bloom < 0.25:                       # still a bud
            r = 5 + bloom * 16
            ellipse(d, x, y, r * 0.75, r, lerpc(GREEN_L, PINK, bloom * 3), outline=stem, width=1.4)
            return
        r = 6 + 13 * bloom
        # petals droop toward the ground as the flower wilts
        for k, pt in enumerate(fl["petals"]):
            ang = k * math.pi / 4 + fl["sway"]
            ang = lerp(ang, math.pi / 2 + (ang % (2 * math.pi) - math.pi) * 0.35, wilt)
            if t < pt["td"]:
                poly(d, self.petal_poly(x, y, ang, r, r * 0.42), col, outline=PINK_D if wilt < 0.5 else BROWN_D, width=1.2)
            else:
                dt = t - pt["td"]
                lx, ly = pt["land"]
                pc = lerpc(col, FADED, 0.4)
                if dt < 1.8:
                    k2 = dt / 1.8
                    px = lerp(x, lx, k2) + math.sin(k2 * 6) * pt["drift"] * (1 - k2)
                    py = lerp(y, ly, k2 * k2)
                    falling.append((self.petal_poly(px, py, ang + pt["spin"] * k2, r * 0.9, r * 0.38), pc))
                else:
                    floor_leaves.append((self.petal_poly(lx, ly, pt["spin"], r * 0.85, r * 0.3), pc))
        cc = lerpc(CENTER, BROWN_D, wilt)
        ellipse(d, x, y, 4 + 2 * bloom, 4 + 2 * bloom, cc, width=1.4)

    def draw_all(self, d, t):
        # leaves on the floor sit behind the pot
        h = health(t)
        d2 = d
        floor_leaves, falling = self.draw_offscreen(t)
        for p, c in floor_leaves:
            if p[0][1] < 548:  # behind the pot
                poly(d2, p, c, outline=BROWN_D, width=1.1)
        self.draw_pot(d2, h)
        for p, c in floor_leaves:
            if p[0][1] >= 548:
                poly(d2, p, c, outline=BROWN_D, width=1.1)
        self.draw(d2, t)
        for p, c in falling:
            poly(d2, p, c, outline=BROWN_D, width=1.1)

    def draw_offscreen(self, t):
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        return self.draw(dummy, t)

    def draw_pot(self, d, h):
        poly(d, [(503, 478), (580, 478), (568, 546), (516, 546)], (124, 136, 140), width=2.2)
        poly(d, [(503, 478), (580, 478), (578, 489), (505, 489)], (140, 152, 156), width=2.0)
        soil = lerpc((60, 52, 40), (98, 84, 62), 1 - h)
        poly(d, [(508, 479), (575, 479), (573, 484), (510, 484)], soil, outline=None)


# ---------------------------------------------------------------- jackets

JACKETS = [
    dict(name="olive trench", c=(114, 114, 54), L=430, lapel=1.0),
    dict(name="navy blazer", c=(55, 66, 96), L=330, lapel=0.8, buttons=2),
    dict(name="rust leather", c=(124, 70, 44), L=280, lapel=0.55, zip=True),
    dict(name="charcoal overcoat", c=(80, 82, 84), L=455, lapel=1.0, buttons=3),
    dict(name="mustard corduroy", c=(172, 136, 56), L=320, lapel=0.8, cord=True),
    dict(name="black dinner jacket", c=(36, 36, 40), L=340, lapel=1.0, satin=(78, 78, 86), buttons=1),
    dict(name="camel coat", c=(184, 146, 96), L=460, lapel=1.1, belt=True),
]

HANG_X, HANG_Y = 790, 262   # top of the hanger


def draw_jacket(d, j, ox, oy, shadow=True, scale=1.0):
    """Jacket on a hanger. (ox, oy) is the hanger's neck."""
    c = j["c"]
    cd = darker(c, 0.8)
    L = j["L"]
    lp = j["lapel"]

    def P(seq, dx=0, dy=0):
        return [(ox + (x + dx) * scale, oy + (y + dy) * scale) for x, y in seq]

    body = [(-38, 0), (38, 0), (96, 30), (118, L), (-118, L), (-96, 30)]
    sl_l = [(-96, 30), (-130, 46), (-150, min(330, L - 10)), (-110, min(342, L)), (-102, 130)]
    sl_r = [(96, 30), (130, 46), (150, min(330, L - 10)), (110, min(342, L)), (102, 130)]
    if shadow:
        for part in (body, sl_l, sl_r):
            poly(d, P(part, 30, 16), SHADOW, outline=None)
    # hanger
    line(d, [(ox, oy - 30), (ox, oy - 6)], fill=INK, width=4.5)
    line(d, [(ox, oy - 30), (ox, oy - 6)], fill=(110, 112, 110), width=2.2)
    poly(d, P(sl_l), cd)
    poly(d, P(sl_r), cd)
    poly(d, P(body), c)
    # shade the right half
    poly(d, P([(2, 120), (96, 30), (118, L), (10, L)]), cd, outline=None)
    poly(d, P(body), None)
    # lining at the neck
    poly(d, P([(-38, 0), (38, 0), (0, 70 * lp)]), darker(c, 0.5))
    # lapels
    lc = j.get("satin", c)
    poly(d, P([(-38, 0), (-4, 175 * lp), (-46, 82 * lp), (-66, 60 * lp), (-50, 30)]), lc)
    poly(d, P([(38, 0), (6, 175 * lp), (46, 82 * lp), (66, 60 * lp), (50, 30)]), darker(lc, 0.85))
    line(d, P([(2, 175 * lp), (8, L)]))
    if j.get("buttons"):
        for i in range(j["buttons"]):
            yb = 200 * lp + i * 50
            ellipse(d, ox + 16 * scale, oy + yb * scale, 5 * scale, 5 * scale, darker(c, 0.55), width=1.5)
    if j.get("zip"):
        line(d, P([(0, 60), (4, L)]), fill=(190, 180, 150), width=2)
        line(d, P([(-118, L - 22), (118, L - 22)]))
    if j.get("cord"):
        for xx in range(-100, 110, 16):
            line(d, P([(xx * 0.8, 50), (xx, L - 6)]), fill=darker(c, 0.72), width=1.2)
    if j.get("belt"):
        poly(d, P([(-112, 250), (114, 250), (115, 274), (-113, 274)]), darker(c, 0.85))
        poly(d, P([(-8, 248), (18, 248), (18, 276), (-8, 276)]), (90, 70, 40), width=1.8)
    # pockets
    line(d, P([(-92, L * 0.62), (-48, L * 0.6)]))
    line(d, P([(54, L * 0.6), (96, L * 0.62)]))


# ---------------------------------------------------------------- the man
# Styled after the reference clip: athletic build, swept-up dark hair with
# short sides, white crew-neck tee, black trousers, and a beard shadow.

SKIN = (224, 178, 142)
SKIN_D = (192, 148, 114)
STUBBLE = (198, 158, 130)        # beard shadow tone over the skin
HAIR = (62, 48, 38)
HAIR_HI = (96, 76, 60)
HAIR_FADE = (128, 104, 86)
SHIRT = (236, 234, 226)
SHIRT_D = (204, 202, 194)
PANTS = (40, 42, 46)
PANTS_D = (30, 32, 35)
BELT = (24, 24, 26)

HEAD_Y = 160
SHOULDER_Y = 240
HIP_Y = 486
FOOT_Y = 890


def limb(cx, cy, ang, length, w0, w1):
    """Tapered rectangle hanging from (cx, cy), rotated by ang (0 = straight down)."""
    loc = [(-w0 / 2, 0), (w0 / 2, 0), (w1 / 2, length), (-w1 / 2, length)]
    return [rot(cx + x, cy + y, ang, cx, cy) for x, y in loc], rot(cx, cy + length, ang, cx, cy)


def draw_arm(d, sx, sy, ang, jacket, near=True, length=236, bend=0.14):
    """Two-segment arm. bend turns the forearm forward (sign follows ang direction set by caller)."""
    sleeve_c = jacket["c"] if jacket else SHIRT
    skin = SKIN if near else SKIN_D
    if not near:
        sleeve_c = darker(sleeve_c, 0.84)
    up = length * 0.51
    lo = length - up
    upper, elbow = limb(sx, sy, ang, up, 44, 36)
    lower, wrist = limb(elbow[0], elbow[1], ang + bend, lo, 34, 26)
    poly(d, upper, skin)
    ellipse(d, elbow[0], elbow[1], 17, 17, skin, outline=None)
    poly(d, lower, skin)
    if jacket:
        poly(d, limb(sx, sy, ang, up, 50, 44)[0], sleeve_c)
        ellipse(d, elbow[0], elbow[1], 21, 21, sleeve_c, outline=None)
        poly(d, limb(elbow[0], elbow[1], ang + bend, lo - 12, 42, 36)[0], sleeve_c)
    else:
        ellipse(d, sx, sy + 6, 25, 22, sleeve_c, outline=None)
        sl, cuff = limb(sx, sy - 4, ang, 76, 50, 48)
        poly(d, sl, sleeve_c)
        line(d, [rot(sx - 23, sy + 64, ang, sx, sy), rot(sx + 23, sy + 64, ang, sx, sy)],
             fill=SHIRT_D, width=1.6)
    # hand with a thumb
    hx, hy = rot(wrist[0], wrist[1] + 10, ang + bend, wrist[0], wrist[1])
    ellipse(d, hx, hy, 14, 19, skin)
    return (hx, hy)


def draw_leg(d, hx, hy, ang, near=True):
    c = PANTS if near else PANTS_D
    p, _ = limb(hx, hy, ang, FOOT_Y - HIP_Y, 58, 44)
    poly(d, p, c)


def draw_profile_head(d, X, y):
    """Head in profile. X(dx) maps 'forward' offsets to screen x."""
    def P(seq):
        return [(X(a), b + y) for a, b in seq]
    # neck
    poly(d, P([(-20, 196), (18, 204), (22, 246), (-24, 246)]), SKIN)
    line(d, P([(16, 214), (20, 236)]), fill=SKIN_D, width=1.6)
    head = [(30, 118), (38, 132), (42, 148), (41, 157), (56, 178), (44, 186), (45, 195), (42, 207),
            (32, 217), (14, 219), (-6, 208), (-18, 196), (-34, 186), (-42, 165), (-42, 140),
            (-32, 118), (-12, 106), (10, 106)]
    poly(d, P(head), SKIN)
    # beard shadow: jaw, chin and upper lip, no outline
    poly(d, P([(43, 187), (44.5, 195), (41.5, 207), (32, 216), (14, 218), (-5, 207), (-15, 195),
               (-6, 190), (8, 197), (24, 196), (34, 186)]), STUBBLE, outline=None)
    poly(d, P(head), None)
    line(d, P([(2, 192), (-4, 200)]), fill=SKIN_D, width=1.4)     # jaw hint
    # ear
    ellipse(d, X(-14), 166 + y, 8, 13, SKIN_D, width=2)
    line(d, P([(-14, 160), (-17, 168), (-13, 174)]), fill=darker(SKIN_D, 0.8), width=1.4)
    # hair: swept-up top, short faded sides
    poly(d, P([(-24, 146), (-32, 162), (-36, 184), (-26, 190), (-22, 168)]), HAIR_FADE, outline=None)
    hair = [(40, 130), (52, 114), (48, 96), (30, 84), (6, 82), (-20, 88), (-38, 104), (-46, 134),
            (-42, 160), (-34, 150), (-24, 146), (-10, 138), (8, 132), (28, 130)]
    poly(d, P(hair), HAIR)
    for a in ((44, 104, 10, 90), (30, 106, -6, 94), (16, 116, -18, 104)):
        line(d, P([(a[0], a[1]), (a[2], a[3])]), fill=HAIR_HI, width=1.8)
    # brow and eye
    line(d, P([(22, 146), (40, 145)]), fill=HAIR, width=3.6)
    line(d, P([(27, 157), (36, 156)]), width=2.4)
    ellipse(d, X(32), 158 + y, 2.4, 2.4, INK, outline=None)
    line(d, P([(28, 152), (36, 151)]), fill=SKIN_D, width=1.2)     # eyelid crease


def draw_side(d, cx, bob, phase, facing, jacket, walking=True):
    """Profile view. facing = -1 walks left, +1 walks right."""
    f = facing
    swing = math.sin(phase) * (0.28 if walking else 0.0)
    y = bob

    def X(dx):
        return cx + f * dx

    # far limbs
    draw_arm(d, X(-4), SHOULDER_Y + 16 + y, -f * swing * 0.9, jacket, near=False, bend=-f * 0.16)
    draw_leg(d, X(0), HIP_Y + y, f * swing, near=False)
    draw_leg(d, X(0), HIP_Y + y, -f * swing, near=True)
    # belt
    poly(d, [(X(-38), HIP_Y - 8 + y), (X(38), HIP_Y - 8 + y), (X(38), HIP_Y + 8 + y), (X(-38), HIP_Y + 8 + y)], BELT)
    # torso
    if jacket:
        Lj = min(jacket["L"] * 0.62, 300)
        tor = [(X(-38), SHOULDER_Y + y), (X(34), SHOULDER_Y + 4 + y), (X(50), SHOULDER_Y + 50 + y),
               (X(50), SHOULDER_Y + Lj + y), (X(-46), SHOULDER_Y + Lj + y), (X(-50), SHOULDER_Y + 40 + y)]
        poly(d, tor, jacket["c"])
        lc = jacket.get("satin", jacket["c"])
        poly(d, [(X(26), SHOULDER_Y + 2 + y), (X(50), SHOULDER_Y + 104 + y), (X(32), SHOULDER_Y + 62 + y)],
             darker(lc, 0.85))
        poly(d, [(X(14), SHOULDER_Y + 2 + y), (X(26), SHOULDER_Y + 2 + y), (X(30), SHOULDER_Y + 40 + y)], SHIRT)
        poly(d, [(X(-38), SHOULDER_Y + y), (X(-24), SHOULDER_Y - 14 + y), (X(0), SHOULDER_Y - 8 + y),
                 (X(-6), SHOULDER_Y + 18 + y)], darker(jacket["c"], 0.7))
        if jacket.get("belt"):
            poly(d, [(X(-48), SHOULDER_Y + 160 + y), (X(50), SHOULDER_Y + 160 + y),
                     (X(50), SHOULDER_Y + 178 + y), (X(-48), SHOULDER_Y + 178 + y)], darker(jacket["c"], 0.85))
    else:
        tor = [(X(-40), SHOULDER_Y - 2 + y), (X(28), SHOULDER_Y + 4 + y), (X(50), SHOULDER_Y + 42 + y),
               (X(52), SHOULDER_Y + 96 + y), (X(40), SHOULDER_Y + 180 + y), (X(38), HIP_Y - 8 + y),
               (X(-36), HIP_Y - 8 + y), (X(-40), SHOULDER_Y + 150 + y), (X(-48), SHOULDER_Y + 50 + y)]
        poly(d, tor, SHIRT)
        poly(d, [(X(-46), SHOULDER_Y + 40 + y), (X(-30), SHOULDER_Y + 30 + y), (X(-26), HIP_Y - 8 + y),
                 (X(-36), HIP_Y - 8 + y), (X(-40), SHOULDER_Y + 120 + y)], SHIRT_D, outline=None)
        line(d, [(X(42), SHOULDER_Y + 96 + y), (X(20), SHOULDER_Y + 110 + y)], fill=SHIRT_D, width=1.6)
        poly(d, tor, None)
    draw_profile_head(d, X, y)
    if not jacket:
        line(d, [(X(-20), SHOULDER_Y - 2 + y), (X(4), SHOULDER_Y + 8 + y), (X(24), SHOULDER_Y + 4 + y)], width=2.2)
    # near arm on top
    draw_arm(d, X(-2), SHOULDER_Y + 16 + y, f * swing * 0.9, jacket, near=True, bend=-f * 0.16)


def draw_back(d, cx, jacket, reach=0.0, target=(HANG_X, HANG_Y - 10), y=0.0):
    """Back view, facing the wall. reach 0..1 raises the left arm toward target."""
    draw_leg(d, cx - 28, HIP_Y + y, 0.03)
    draw_leg(d, cx + 28, HIP_Y + y, -0.03)
    poly(d, [(cx - 54, HIP_Y - 8 + y), (cx + 54, HIP_Y - 8 + y), (cx + 54, HIP_Y + 8 + y), (cx - 54, HIP_Y + 8 + y)], BELT)
    # right arm (at his side)
    draw_arm(d, cx + 64, SHOULDER_Y + 16 + y, -0.08, jacket, bend=0.06)
    # torso: broad shoulders tapering to the waist
    if jacket:
        Lj = min(jacket["L"] * 0.62, 300)
        tor = [(cx - 68, SHOULDER_Y + y), (cx + 68, SHOULDER_Y + y), (cx + 66, SHOULDER_Y + Lj + y),
               (cx - 66, SHOULDER_Y + Lj + y)]
        poly(d, tor, jacket["c"])
        poly(d, [(cx, SHOULDER_Y + 40 + y), (cx + 68, SHOULDER_Y + y), (cx + 66, SHOULDER_Y + Lj + y),
                 (cx + 4, SHOULDER_Y + Lj + y)], darker(jacket["c"], 0.88), outline=None)
        poly(d, tor, None)
        line(d, [(cx, SHOULDER_Y + Lj * 0.55 + y), (cx, SHOULDER_Y + Lj + y)])
        poly(d, [(cx - 36, SHOULDER_Y - 10 + y), (cx + 36, SHOULDER_Y - 10 + y), (cx + 42, SHOULDER_Y + 10 + y),
                 (cx - 42, SHOULDER_Y + 10 + y)], darker(jacket["c"], 0.75))
        if jacket.get("belt"):
            poly(d, [(cx - 66, SHOULDER_Y + 160 + y), (cx + 66, SHOULDER_Y + 160 + y),
                     (cx + 66, SHOULDER_Y + 178 + y), (cx - 66, SHOULDER_Y + 178 + y)], darker(jacket["c"], 0.85))
    else:
        tor = [(cx - 66, SHOULDER_Y + 4 + y), (cx - 30, SHOULDER_Y - 6 + y), (cx + 30, SHOULDER_Y - 6 + y),
               (cx + 66, SHOULDER_Y + 4 + y), (cx + 60, SHOULDER_Y + 110 + y), (cx + 48, HIP_Y - 8 + y),
               (cx - 48, HIP_Y - 8 + y), (cx - 60, SHOULDER_Y + 110 + y)]
        poly(d, tor, SHIRT)
        poly(d, [(cx + 10, SHOULDER_Y + 30 + y), (cx + 66, SHOULDER_Y + 4 + y), (cx + 60, SHOULDER_Y + 110 + y),
                 (cx + 48, HIP_Y - 8 + y), (cx + 14, HIP_Y - 8 + y)], SHIRT_D, outline=None)
        line(d, [(cx - 30, SHOULDER_Y + 70 + y), (cx - 8, SHOULDER_Y + 90 + y)], fill=SHIRT_D, width=1.6)
        poly(d, tor, None)
    # neck, ears, head (hair from behind, faded at the nape)
    poly(d, [(cx - 20, 196 + y), (cx + 20, 196 + y), (cx + 24, SHOULDER_Y + y), (cx - 24, SHOULDER_Y + y)], SKIN)
    ellipse(d, cx - 41, 166 + y, 8, 13, SKIN_D, width=2)
    ellipse(d, cx + 41, 166 + y, 8, 13, SKIN_D, width=2)
    ellipse(d, cx, HEAD_Y + y, 41, 50, HAIR_FADE)
    poly(d, [(cx - 41, 172 + y), (cx - 44, 140 + y), (cx - 34, 108 + y), (cx - 12, 96 + y), (cx + 14, 96 + y),
             (cx + 36, 108 + y), (cx + 44, 140 + y), (cx + 41, 172 + y), (cx + 24, 180 + y), (cx, 184 + y),
             (cx - 24, 180 + y)], HAIR)
    for k in (-18, 0, 18):
        line(d, [(cx + k * 1.2, 104 + y), (cx + k, 150 + y)], fill=HAIR_HI, width=1.6)
    # left arm: hangs, or reaches up toward the hanger (straightens as it reaches)
    sx, sy = cx - 64, SHOULDER_Y + 16 + y
    tx, ty = target
    reach_ang = math.atan2(-(tx - sx), (ty - sy))     # angle from straight down
    k = smooth(reach)
    ang = lerp(0.08, reach_ang, k)
    dist = math.hypot(tx - sx, ty - sy)
    length = lerp(236, min(250, dist), k)
    return draw_arm(d, sx, sy, ang, jacket, length=length, bend=lerp(-0.06, 0.0, k))


# ---------------------------------------------------------------- mirror

MIR_CX, MIR_CY, MIR_RX, MIR_RY = 812, 352, 92, 122


def draw_mirror(d, big, reflect=None):
    ellipse(d, MIR_CX + 12, MIR_CY + 8, MIR_RX + 12, MIR_RY + 12, SHADOW, outline=None)
    ellipse(d, MIR_CX, MIR_CY, MIR_RX + 12, MIR_RY + 12, (96, 74, 46), width=2.6)
    glass = (172, 182, 176)
    ellipse(d, MIR_CX, MIR_CY, MIR_RX, MIR_RY, glass, width=2.2)
    if reflect is not None:
        layer = Image.new("RGB", big.size, glass)
        ld = ImageDraw.Draw(layer)
        reflect(ld)
        # sheen
        for k in (-40, -10):
            line(ld, [(MIR_CX + k - 40, MIR_CY - 90), (MIR_CX + k + 60, MIR_CY + 40)], fill=(198, 206, 200), width=7)
        m = Image.new("L", big.size, 0)
        ImageDraw.Draw(m).ellipse([S(MIR_CX - MIR_RX + 2), S(MIR_CY - MIR_RY + 2),
                                   S(MIR_CX + MIR_RX - 2), S(MIR_CY + MIR_RY - 2)], fill=255)
        big.paste(layer, (0, 0), m)
        d = ImageDraw.Draw(big)
        ellipse(d, MIR_CX, MIR_CY, MIR_RX, MIR_RY, None, width=2.2)
    else:
        for k in (-40, -10):
            line(d, [(MIR_CX + k - 40, MIR_CY - 90), (MIR_CX + k + 60, MIR_CY + 40)], fill=(198, 206, 200), width=7)
    # cord up to the hook
    line(d, [(MIR_CX - 40, MIR_CY - MIR_RY - 6), (806, 247), (MIR_CX + 40, MIR_CY - MIR_RY - 6)], width=2.2)


def faceless_reflection(presence, jacket):
    """Head and shoulders seen from the front, with an empty face."""
    def fn(ld):
        if presence <= 0:
            return
        cx = MIR_CX + 26
        top = MIR_CY - 70
        c = jacket["c"]
        # shoulders in the coat
        poly(ld, [(cx - 95, top + 175), (cx - 40, top + 128), (cx + 40, top + 128), (cx + 95, top + 175),
                  (cx + 110, top + 260), (cx - 110, top + 260)], c)
        poly(ld, [(cx - 28, top + 128), (cx + 28, top + 128), (cx, top + 200)], SHIRT)
        poly(ld, [(cx - 40, top + 128), (cx - 4, top + 205), (cx - 30, top + 175), (cx - 50, top + 150)], darker(c, 0.85))
        poly(ld, [(cx + 40, top + 128), (cx + 4, top + 205), (cx + 30, top + 175), (cx + 50, top + 150)], darker(c, 0.85))
        poly(ld, [(cx - 18, top + 92), (cx + 18, top + 92), (cx + 21, top + 134), (cx - 21, top + 134)], SKIN)
        ellipse(ld, cx - 37, top + 52, 7, 12, SKIN_D, width=2)
        ellipse(ld, cx + 37, top + 52, 7, 12, SKIN_D, width=2)
        ellipse(ld, cx, top + 50, 36, 47, SKIN)                     # no eyes, no nose, no mouth
        poly(ld, [(cx - 37, top + 50), (cx - 36, top + 22), (cx - 28, top + 26), (cx - 30, top + 50)], HAIR_FADE, outline=None)
        poly(ld, [(cx + 37, top + 50), (cx + 36, top + 22), (cx + 28, top + 26), (cx + 30, top + 50)], HAIR_FADE, outline=None)
        poly(ld, [(cx - 34, top + 30), (cx - 34, top + 4), (cx - 16, top - 12), (cx + 10, top - 14), (cx + 30, top - 4),
                  (cx + 36, top + 30), (cx + 26, top + 16), (cx + 4, top + 12), (cx - 22, top + 16)], HAIR)
        line(ld, [(cx - 14, top - 6), (cx + 12, top - 8)], fill=HAIR_HI, width=1.8)
    return fn


# ---------------------------------------------------------------- timeline

INTRO = 2.5
ENDING = 26.0
N = len(JACKETS)
CYCLE = (DURATION - INTRO - ENDING) / N
# phase lengths inside a cycle (idle absorbs the rest)
T_ENTER, T_TURN, T_REACH, T_LIFT, T_WEAR, T_EXIT, T_EMPTY, T_FLICK = 3.4, 0.35, 1.1, 1.3, 0.6, 3.4, 1.4, 1.3
T_IDLE = CYCLE - (T_ENTER + T_TURN + T_REACH + T_LIFT + T_WEAR + T_EXIT + T_EMPTY + T_FLICK)

ENTER_X, STAND_X, EXIT_X = 1530, 985, 1560
STEP = 1.9  # walking cycles per second (radians handled below)


def walk(t0, t1, x0, x1, t):
    k = (t - t0) / (t1 - t0)
    x = lerp(x0, x1, k)
    phase = (t - t0) * STEP * 2 * math.pi
    bob = -abs(math.sin(phase)) * 6
    return x, phase, bob


def light_level(t):
    """Brightness of the scene during the lamp flickers between jackets."""
    def flick(tc):
        k = (t - tc) / T_FLICK
        if k < 0 or k > 1:
            return 1.0
        # off, a quick stutter, then on
        if k < 0.15:
            return lerp(1.0, 0.35, k / 0.15)
        if k < 0.55:
            return 0.35
        if k < 0.62:
            return 0.8
        if k < 0.72:
            return 0.4
        return lerp(0.4, 1.0, (k - 0.72) / 0.28)
    lv = 1.0
    for i in range(N):
        tc = INTRO + i * CYCLE + CYCLE - T_FLICK
        lv = min(lv, flick(tc))
    return lv


def state_at(t):
    """Return a dict describing what is on screen at time t."""
    if t < INTRO + N * CYCLE:
        i = int((t - INTRO) // CYCLE) if t >= INTRO else 0
        i = max(0, min(N - 1, i))
        tc = t - INTRO - i * CYCLE if t >= INTRO else -1
        j = JACKETS[i]
        st = dict(jacket_idx=i, hanging=True, hang_pos=(HANG_X, HANG_Y), man=None, mirror=False)
        a = T_IDLE
        b = a + T_ENTER
        c = b + T_TURN
        dd = c + T_REACH
        e = dd + T_LIFT
        f = e + T_WEAR
        g = f + T_EXIT
        swap = CYCLE - T_FLICK * 0.4      # moment the next item appears, while the light is off
        if tc < a:
            pass
        elif tc < b:
            x, ph, bob = walk(a, b, ENTER_X, STAND_X, tc)
            st["man"] = dict(view="side", x=x, phase=ph, bob=bob, facing=-1, jacket=None)
        elif tc < c:
            st["man"] = dict(view="side", x=STAND_X, phase=0, bob=0, facing=-1, jacket=None, walking=False)
        elif tc < dd:
            st["man"] = dict(view="back", x=STAND_X, reach=(tc - c) / T_REACH, jacket=None)
        elif tc < e:
            k = smooth((tc - dd) / T_LIFT)
            hx = lerp(HANG_X, STAND_X - 40, k)
            hy = HANG_Y - 22 * math.sin(k * math.pi) + 20 * k
            st["hang_pos"] = (hx, hy)
            st["man"] = dict(view="back", x=STAND_X, reach=1.0, target=(hx, hy - 10), jacket=None, carry=True)
        elif tc < f:
            st["hanging"] = False
            st["man"] = dict(view="back", x=STAND_X, reach=lerp(1, 0, (tc - e) / T_WEAR), jacket=j)
        elif tc < g:
            st["hanging"] = False
            x, ph, bob = walk(f, g, STAND_X, EXIT_X, tc)
            st["man"] = dict(view="side", x=x, phase=ph, bob=bob, facing=1, jacket=j)
        else:
            st["hanging"] = False
            if tc >= swap:
                if i + 1 < N:
                    st["jacket_idx"] = i + 1
                    st["hanging"] = True
                    st["hang_pos"] = (HANG_X, HANG_Y)
                else:
                    st["mirror"] = True
        return st
    # ending: the mirror
    te = t - INTRO - N * CYCLE
    st = dict(jacket_idx=None, hanging=False, man=None, mirror=True, reflect=0)
    a, b = 3.0, 3.0 + 4.2
    if te < a:
        pass
    elif te < b:
        x, ph, bob = walk(a, b, ENTER_X, STAND_X + 20, te)
        st["man"] = dict(view="side", x=x, phase=ph, bob=bob, facing=-1, jacket=JACKETS[-1])
    elif te < b + 0.6:
        st["man"] = dict(view="side", x=STAND_X + 20, phase=0, bob=0, facing=-1, jacket=JACKETS[-1], walking=False)
    else:
        st["man"] = dict(view="back", x=STAND_X + 20, reach=0, jacket=JACKETS[-1])
        st["reflect"] = 1
    return st


# ---------------------------------------------------------------- frame

_BG = None
_PLANT = None


def init(cover):
    global _BG, _PLANT
    _BG = build_background(cover)
    _PLANT = Plant()


def render(t):
    img = _BG.copy()
    d = ImageDraw.Draw(img)
    _PLANT.draw_all(d, t)
    # keep the fern inside its own panel
    img.paste(_BG.crop((S(PANEL_X) - 2, 0, S(W), S(H))), (S(PANEL_X) - 2, 0))
    d = ImageDraw.Draw(img)
    st = state_at(t)
    man = st["man"]
    if st.get("mirror"):
        refl = faceless_reflection(st.get("reflect", 0), JACKETS[-1]) if st.get("reflect") else None
        draw_mirror(d, img, refl)
        d = ImageDraw.Draw(img)
        draw_hook(d)
    carrying = man is not None and man.get("carry")
    if st["hanging"] and st["jacket_idx"] is not None and not carrying:
        hx, hy = st["hang_pos"]
        draw_jacket(d, JACKETS[st["jacket_idx"]], hx, hy)
        draw_hook(d)
    elif not st.get("mirror"):
        draw_hook(d)
    if man:
        if man["view"] == "side":
            draw_side(d, man["x"], man["bob"], man["phase"], man["facing"], man["jacket"],
                      walking=man.get("walking", True))
        else:
            if carrying:
                hx, hy = st["hang_pos"]
                draw_jacket(d, JACKETS[st["jacket_idx"]], hx, hy, shadow=False)
            draw_back(d, man["x"], man["jacket"], reach=man.get("reach", 0),
                      target=man.get("target", (HANG_X, HANG_Y - 10)))
    out = img.resize((W, H), Image.LANCZOS)
    lv = light_level(t)
    if t < 1.5:
        lv *= t / 1.5
    if t > DURATION - 3.5:
        lv *= max(0.0, (DURATION - t) / 3.5)
    if lv < 0.999:
        out = Image.eval(out, lambda v, lv=lv: int(v * lv))
    return out


def render_chunk(args):
    cover, out_path, f0, f1 = args
    init(cover)
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(render(fi / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return out_path


def main():
    cover, audio, out = sys.argv[1:4]
    if "--preview" in sys.argv:
        init(cover)
        times = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1:]]
        for tt in times:
            render(tt).save(os.path.join(os.path.dirname(out), f"preview_{tt:07.2f}.png"))
        return
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "chunks")
    os.makedirs(work, exist_ok=True)
    total = int(math.ceil(DURATION * FPS))
    nproc = os.cpu_count() or 2
    nchunks = nproc * 2
    step = math.ceil(total / nchunks)
    jobs = [(cover, os.path.join(work, f"c{k:02d}.mp4"), k * step, min(total, (k + 1) * step))
            for k in range(nchunks) if k * step < total]
    with Pool(nproc) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as fh:
        for pth in parts:
            fh.write(f"file '{pth}'\n")
    song = os.path.join(work, "song.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-ar", "48000", "-ac", "2", "-shortest", song], check=True)
    endcard = None
    if "--endcard" in sys.argv:
        endcard = sys.argv[sys.argv.index("--endcard") + 1]
    if not endcard:
        os.replace(song, out)
        return
    # The landing page card: fades up from black after the song, holds, fades out.
    # It is letterboxed onto a near-black field to keep its 16:9 shape.
    card = os.path.join(work, "card.mp4")
    vf = (f"scale=-2:{H},pad={W}:{H}:(ow-iw)/2:0:color=0x141414,format=yuv420p,"
          f"fade=t=in:st=0:d=0.8,fade=t=out:st={ENDCARD_SECONDS - 0.9}:d=0.9")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", endcard,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(ENDCARD_SECONDS),
                    "-vf", vf, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "256k", "-shortest", card], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", song, "-i", card, "-filter_complex",
                    "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)


if __name__ == "__main__":
    main()
