"""Render the animated video for "The Heart Knows (Tempo Shift Take)".

A man comes in, takes a jacket from the hook and leaves, seven times with
seven different jackets. The fern on the balcony withers across the song.
At the end a mirror hangs on the hook and his reflection has no face.

Usage:
    python3 render.py COVER.jpg AUDIO.wav OUT.mp4 [--preview SECONDS ...]
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
    """1 = lush, 0 = dead. Slow at first, fully dead a little before the end."""
    return 1.0 - smooth((t - 6.0) / 140.0) ** 0.85


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
        # time at which each leaflet drops
        samples = [(i / 10.0, health(i / 10.0)) for i in range(int(DURATION * 10) + 1)]
        for f in self.fronds:
            for lf in f["leaflets"]:
                lf["td"] = next((tt for tt, hh in samples if hh < lf["u"]), 1e9)

    def frond_point(self, f, h, s, t):
        a = f["a"] + 0.015 * math.sin(t * 0.7 + f["sway"]) * h
        L = f["L"] * (0.92 + 0.08 * h)
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
        return floor_leaves, falling

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

SKIN = (202, 162, 126)
SKIN_D = (170, 132, 100)
HAIR = (58, 46, 34)
SHIRT = (206, 203, 188)
SHIRT_D = (176, 173, 160)
PANTS = (70, 78, 84)
PANTS_D = (54, 60, 66)

HEAD_Y = 160
SHOULDER_Y = 238
HIP_Y = 480
FOOT_Y = 880


def limb(cx, cy, ang, length, w0, w1):
    """Tapered rectangle hanging from (cx, cy), rotated by ang (0 = straight down)."""
    loc = [(-w0 / 2, 0), (w0 / 2, 0), (w1 / 2, length), (-w1 / 2, length)]
    return [rot(cx + x, cy + y, ang, cx, cy) for x, y in loc], rot(cx, cy + length, ang, cx, cy)


def draw_arm(d, sx, sy, ang, jacket, near=True, length=240):
    sleeve_c = jacket["c"] if jacket else SHIRT
    if not near:
        sleeve_c = darker(sleeve_c, 0.82)
    skin = SKIN if near else SKIN_D
    full, hand = limb(sx, sy, ang, length, 34, 26)
    poly(d, full, skin)
    sleeve_len = length - 22 if jacket else 78
    sl, _ = limb(sx, sy, ang, sleeve_len, 40, 32 if jacket else 36)
    poly(d, sl, sleeve_c)
    ellipse(d, hand[0], hand[1], 15, 17, skin)
    return hand


def draw_leg(d, hx, hy, ang, near=True):
    c = PANTS if near else PANTS_D
    p, _ = limb(hx, hy, ang, FOOT_Y - HIP_Y, 54, 42)
    poly(d, p, c)


def draw_side(d, cx, bob, phase, facing, jacket, walking=True):
    """Profile view. facing = -1 walks left, +1 walks right."""
    f = facing
    swing = math.sin(phase) * (0.28 if walking else 0.0)
    y = bob

    def X(dx):
        return cx + f * dx

    # far limbs
    draw_arm(d, X(-4), SHOULDER_Y + 14 + y, -f * swing * 0.9, jacket, near=False)
    draw_leg(d, X(0), HIP_Y + y, f * swing, near=False)
    draw_leg(d, X(0), HIP_Y + y, -f * swing, near=True)
    # torso
    if jacket:
        Lj = min(jacket["L"] * 0.62, 300)
        tor = [(X(-34), SHOULDER_Y + y), (X(36), SHOULDER_Y + 4 + y), (X(46), SHOULDER_Y + 120 + y),
               (X(46), SHOULDER_Y + Lj + y), (X(-44), SHOULDER_Y + Lj + y), (X(-46), SHOULDER_Y + 40 + y)]
        poly(d, tor, jacket["c"])
        lc = jacket.get("satin", jacket["c"])
        poly(d, [(X(28), SHOULDER_Y + 2 + y), (X(46), SHOULDER_Y + 100 + y), (X(30), SHOULDER_Y + 60 + y)],
             darker(lc, 0.85))
        poly(d, [(X(-34), SHOULDER_Y + y), (X(-22), SHOULDER_Y - 12 + y), (X(0), SHOULDER_Y - 6 + y),
                 (X(-6), SHOULDER_Y + 18 + y)], darker(jacket["c"], 0.7))
        if jacket.get("belt"):
            poly(d, [(X(-46), SHOULDER_Y + 160 + y), (X(46), SHOULDER_Y + 160 + y),
                     (X(46), SHOULDER_Y + 178 + y), (X(-46), SHOULDER_Y + 178 + y)], darker(jacket["c"], 0.85))
    else:
        tor = [(X(-32), SHOULDER_Y + y), (X(34), SHOULDER_Y + 4 + y), (X(42), SHOULDER_Y + 110 + y),
               (X(38), HIP_Y + 4 + y), (X(-38), HIP_Y + 4 + y), (X(-42), SHOULDER_Y + 50 + y)]
        poly(d, tor, SHIRT)
        line(d, [(X(-6), HIP_Y - 30 + y), (X(30), HIP_Y - 26 + y)], fill=SHIRT_D, width=2)
    # neck and head
    poly(d, [(X(-14), 196 + y), (X(16), 196 + y), (X(18), SHOULDER_Y + 6 + y), (X(-16), SHOULDER_Y + 6 + y)], SKIN)
    hx, hy = X(4), HEAD_Y + y
    # nose and face contour, then head
    poly(d, [(X(34), 150 + y), (X(52), 176 + y), (X(36), 182 + y), (X(36), 196 + y), (X(14), 206 + y)], SKIN)
    ellipse(d, hx, hy, 40, 48, SKIN)
    poly(d, [(X(34), 151 + y), (X(51), 176 + y), (X(36), 181 + y)], SKIN, outline=None)
    line(d, [(X(36), 150 + y), (X(52), 176 + y), (X(37), 182 + y)], width=2.2)
    # hair covers top and back
    hair = [(X(36), 132 + y), (X(26), 114 + y), (X(4), 109 + y), (X(-22), 114 + y), (X(-40), 136 + y),
            (X(-44), 170 + y), (X(-36), 196 + y), (X(-18), 192 + y), (X(-14), 160 + y), (X(4), 140 + y), (X(30), 142 + y)]
    poly(d, hair, HAIR)
    ellipse(d, X(-6), 168 + y, 8, 12, SKIN_D, width=2)
    line(d, [(X(26), 146 + y), (X(38), 147 + y)], width=2.4)          # brow
    ellipse(d, X(31), 157 + y, 2.6, 2.6, INK, outline=None)            # eye
    # near arm on top
    draw_arm(d, X(-2), SHOULDER_Y + 14 + y, f * swing * 0.9, jacket, near=True)


def draw_back(d, cx, jacket, reach=0.0, target=(HANG_X, HANG_Y - 10), y=0.0):
    """Back view, facing the wall. reach 0..1 raises the left arm toward target."""
    draw_leg(d, cx - 26, HIP_Y + y, 0.03)
    draw_leg(d, cx + 26, HIP_Y + y, -0.03)
    # right arm (at his side)
    draw_arm(d, cx + 58, SHOULDER_Y + 14 + y, -0.06, jacket)
    # torso
    if jacket:
        Lj = min(jacket["L"] * 0.62, 300)
        tor = [(cx - 60, SHOULDER_Y + y), (cx + 60, SHOULDER_Y + y), (cx + 66, SHOULDER_Y + Lj + y),
               (cx - 66, SHOULDER_Y + Lj + y)]
        poly(d, tor, jacket["c"])
        poly(d, [(cx, SHOULDER_Y + 40 + y), (cx + 60, SHOULDER_Y + y), (cx + 66, SHOULDER_Y + Lj + y),
                 (cx + 4, SHOULDER_Y + Lj + y)], darker(jacket["c"], 0.88), outline=None)
        poly(d, tor, None)
        line(d, [(cx, SHOULDER_Y + Lj * 0.55 + y), (cx, SHOULDER_Y + Lj + y)])
        poly(d, [(cx - 34, SHOULDER_Y - 8 + y), (cx + 34, SHOULDER_Y - 8 + y), (cx + 40, SHOULDER_Y + 10 + y),
                 (cx - 40, SHOULDER_Y + 10 + y)], darker(jacket["c"], 0.75))
        if jacket.get("belt"):
            poly(d, [(cx - 64, SHOULDER_Y + 160 + y), (cx + 64, SHOULDER_Y + 160 + y),
                     (cx + 64, SHOULDER_Y + 178 + y), (cx - 64, SHOULDER_Y + 178 + y)], darker(jacket["c"], 0.85))
    else:
        tor = [(cx - 56, SHOULDER_Y + y), (cx + 56, SHOULDER_Y + y), (cx + 50, HIP_Y + 4 + y),
               (cx - 50, HIP_Y + 4 + y)]
        poly(d, tor, SHIRT)
        poly(d, [(cx + 8, SHOULDER_Y + 30 + y), (cx + 56, SHOULDER_Y + y), (cx + 50, HIP_Y + 4 + y),
                 (cx + 12, HIP_Y + 4 + y)], SHIRT_D, outline=None)
        poly(d, tor, None)
    # neck, ears, head (all hair from behind)
    poly(d, [(cx - 16, 196 + y), (cx + 16, 196 + y), (cx + 18, SHOULDER_Y + 2 + y), (cx - 18, SHOULDER_Y + 2 + y)], SKIN)
    ellipse(d, cx - 40, 166 + y, 8, 13, SKIN_D, width=2)
    ellipse(d, cx + 40, 166 + y, 8, 13, SKIN_D, width=2)
    ellipse(d, cx, HEAD_Y + y, 40, 48, HAIR)
    line(d, [(cx - 22, 200 + y), (cx, 205 + y), (cx + 22, 200 + y)], fill=darker(HAIR, 0.6), width=1.6)
    # left arm: hangs, or reaches up toward the hanger
    sx, sy = cx - 58, SHOULDER_Y + 14 + y
    tx, ty = target
    reach_ang = math.atan2(-(tx - sx), (ty - sy))     # angle from straight down
    ang = lerp(0.06, reach_ang, smooth(reach))
    dist = math.hypot(tx - sx, ty - sy)
    length = lerp(240, min(250, dist), smooth(reach))
    return draw_arm(d, sx, sy, ang, jacket, length=length)


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
        poly(ld, [(cx - 14, top + 92), (cx + 14, top + 92), (cx + 16, top + 134), (cx - 16, top + 134)], SKIN)
        ellipse(ld, cx - 37, top + 52, 7, 12, SKIN_D, width=2)
        ellipse(ld, cx + 37, top + 52, 7, 12, SKIN_D, width=2)
        ellipse(ld, cx, top + 48, 36, 46, SKIN)                     # no eyes, no nose, no mouth
        poly(ld, [(cx - 37, top + 44), (cx - 32, top + 14), (cx - 10, top), (cx + 16, top + 1), (cx + 34, top + 16),
                  (cx + 38, top + 44), (cx + 30, top + 26), (cx + 4, top + 18), (cx - 26, top + 24)], HAIR)
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
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", out], check=True)


if __name__ == "__main__":
    main()
