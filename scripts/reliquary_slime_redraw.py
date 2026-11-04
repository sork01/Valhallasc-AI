#!/usr/bin/env python3
"""Coral Reliquary (Drowned Cathedral wing 2, zone 11) slime-style native PixelFlow sources.

preview | extents | build | refresh | export | verify.
Greenmeadow glossy shading, big eyes with highlights (#fffbea) and blush, material-appropriate movement,
per-kind frame sizes (KIND_FRAMES, docs/kind-frames.md), grounded feet/bases on the anchor row in every living
and death frame (QUADRUPED-GROUNDING), eight distinct attack frames (wind-up, strike, recovery) and eight
distinct fitting death frames per kind:
  - reliccrab: rigid rose-coral carapace with gold/glass pearl shrine on eight jointed legs; rears claws high
    then slams forward; on death rolls onto its back with curled legs, slack claws and cracked shrine glass.
  - pearlwidow: deep-violet spider with giant pearl abdomen and hourglass mark on eight jointed legs; rears
    front legs and fangs high then lunges forward with venom pearls; on death legs buckle and curl inward as
    the rigid carapace and pearl abdomen settle onto the floor.
  - glasscantor: gothic stained-glass lancet robe and hood with tuning-fork scepter and orbiting glass shards;
    raises scepter high then sweeps it forward to hurl shards; on death cracks spread, scepter drops flat and
    the stained-glass panes shatter downward into a glittering heap on the floor.
  - relicwarden: heavy crimson-and-gold plated crustacean juggernaut on four armoured legs with kite shield and
    war-hammer claw; heaves hammer-claw overhead then slams it down; on death legs buckle, shield and claw drop
    flat, heart-gem cracks and the heavy carapace slumps low.
  - coralregent: Queen Avariel in rose-coral gown with living coral hem, teal hair, coral crown and pearl-orb
    scepter; raises scepter high then sweeps a tidal pearl volley ahead; on death scepter clatters flat, crown
    tumbles to the floor and she swoons into a pooled gown.
  - reliquarypearl: giant luminous pearl in a hinged fluted clam-shell reliquary on a gold base; opens upper
    shell high then snaps forward with a pearl-sheen burst; on death the pearl cracks and splits while the
    upper shell lid collapses shut over the dimmed shards.

`client/assets/cathedral.txt` is shared by 146 kinds: export replaces ONLY these six kinds' `sprites`, `tops`
and `kindFrames` entries and asserts that all other 140 kinds (including Flooded Cloister's `tidetemplar` and
`tidecantor`, which also spawn in Coral Reliquary) are untouched.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

import make_crag_sprites as old
import kindframe
from deep_slime_redraw import PALETTE as DEEP_PALETTE, BAYER

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/reliquary-slime'
REGISTRY = ROOT / 'scripts/reliquary_slime_sources.txt'
MANIFEST = ASSETS / 'cathedral.txt'
PREFIX = 'valhallasc_reliquary_slime_style_'
KINDS = ['reliccrab', 'pearlwidow', 'glasscantor', 'relicwarden', 'coralregent', 'reliquarypearl']
NAMES = dict(
    reliccrab='Reliquary Crab',
    pearlwidow='Neritha, the Pearl Widow',
    glasscantor='Ilyr, Cantor of Shattered Glass',
    relicwarden='Sarkhos, Warden of the Reliquary',
    coralregent='Queen Avariel, the Coral Regent',
    reliquarypearl='Reliquary Pearl',
)
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = dict(
    reliccrab=(128, 96, 54, 90),
    pearlwidow=(136, 100, 58, 94),
    glasscantor=(124, 108, 52, 102),
    relicwarden=(136, 112, 56, 106),
    coralregent=(136, 114, 54, 108),
    reliquarypearl=(116, 96, 50, 90),
)
CLIPS = old.CLIPS


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


PALETTE = DEEP_PALETTE[:] + [
    '#5a1f38', '#a8456e', '#e07a9a', '#f6b0c4', '#ffe4ec',   # 95-99 PINK (pale coral / rose)
    '#2e0f1c', '#6a2038', '#a63a56', '#d8708a', '#ffb0be',   # 100-104 MAROON (deep rose / shell)
    '#6e2444', '#b83c66', '#ef6c8e', '#ffa6be', '#ffe2ea',   # 105-109 CORAL (bright rose-coral)
    '#56447a', '#8d78b8', '#c6b2e6', '#eadcf9', '#fbf5ff',   # 110-114 PEARL (lustrous lavender-white)
    '#1f143d', '#3e2973', '#6847b0', '#9b7be0', '#cfbaff',  # 115-119 VIOLET
    '#3c1629', '#782840', '#b54552', '#e87a64', '#ffbfa3',   # 120-124 CRIMSON (warden carapace)
    '#5e320c', '#a85c18', '#e89628', '#ffc95c', '#fff1b8',   # 125-129 AMBER (stained glass)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
OUTLINE, WHITE, EYE_WHITE, BLUSH = 1, 2, 3, 4
BONE = list(range(5, 10))
PLATE = list(range(10, 15))
PURPLE = list(range(15, 20))
TEAL = list(range(20, 25))
GOLD = list(range(25, 30))
GREEN = list(range(30, 35))
FUR = list(range(45, 50))
BLUE = list(range(55, 60))
BROWN = list(range(60, 65))
OLIVE = list(range(75, 80))
PINK = list(range(95, 100))
MAROON = list(range(100, 105))
CORAL = list(range(105, 110))
PEARL = list(range(110, 115))
VIOLET = list(range(115, 120))
CRIMSON = list(range(120, 125))
AMBER = list(range(125, 130))


def mix(a, b, t):
    return a + (b - a) * t


def mixp(p, q, t):
    return (mix(p[0], q[0], t), mix(p[1], q[1], t))


def rot(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return x * c - y * s, x * s + y * c


def sm(t):
    t = max(0., min(1., t))
    return t * t * (3 - 2 * t)


def bez(p0, p1, p2, k=8):
    return [((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * p1[0] + s * s * p2[0],
             (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * p1[1] + s * s * p2[1])
            for s in (i / k for i in range(k + 1))]


def taper(a, pts, ramp, w0, w1):
    last = len(pts) - 1
    for i in range(last):
        a.line([pts[i], pts[i + 1]], ramp[0], max(1, round(mix(w0, w1, i / last) + 2)))
    for i in range(last):
        a.line([pts[i], pts[i + 1]], ramp[2], max(1, round(mix(w0, w1, i / last))))
    for i in range(last):
        w = mix(w0, w1, i / last)
        if w >= 4:
            a.line([(pts[i][0] - w * .18, pts[i][1] + w * .18),
                    (pts[i + 1][0] - w * .18, pts[i + 1][1] + w * .18)], ramp[3], 1)


class Painter:
    """Round glossy shaded components on a kind-sized canvas; y is up from the ground row, x from the centre."""
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx

    def pos(self, x, y):
        return round(self.cx + x), round(self.ay - y)

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.pos(x, y)
        self.d.ellipse((round(px - rx), round(py - ry), round(px + rx), round(py + ry)), fill=col)

    def line(self, pts, col, width=1):
        self.d.line([self.pos(*p) for p in pts], fill=col, width=width)

    def poly(self, pts, col, outline=None):
        self.d.polygon([self.pos(*p) for p in pts], fill=col, outline=outline)

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        px, py = self.pos(x, y)
        R = max(rx, ry)
        c, s = math.cos(ang), math.sin(ang)
        for yy in range(max(0, math.floor(py - R)), min(self.h, math.ceil(py + R) + 1)):
            for xx in range(max(0, math.floor(px - R)), min(self.w, math.ceil(px + R) + 1)):
                dx, dy = xx - px, yy - py
                u, v = (dx * c - dy * s) / rx, (dx * s + dy * c) / ry
                rr = u * u + v * v
                if rr > 1:
                    continue
                z = math.sqrt(max(0, 1 - rr))
                nx, ny = u * c + v * s, -u * s + v * c
                value = max(0, min(.999, .23 + .71 * (-.40 * nx - .54 * ny + .74 * z))) * (len(ramp) - 1)
                lo = int(value)
                threshold = ((xx % 4) * 5 + (yy % 4) * 3) % 16 / 16
                shade = min(len(ramp) - 1, lo + int(value - lo > threshold))
                if rr > .93 and nx + ny > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])

    def limb(self, points, ramp, width=5):
        self.line(points, ramp[0], width + 2)
        self.line(points, ramp[min(2, len(ramp) - 1)], width)
        for x, y in points[1:-1]:
            self.ball(x, y, width / 2, width / 2, ramp)

    def eye(self, x, y, clip, n, size=1.):
        if clip == 'die' and n >= 2:
            self.line([(x - 2, y - 2), (x + 2, y + 2)], 1, 2)
            self.line([(x - 2, y + 2), (x + 2, y - 2)], 1, 2)
        elif clip == 'idle' and n == 3:
            self.line([(x - 3 * size, y), (x + 3 * size, y + .5)], 1, 2)
        else:
            self.ellipse(x, y, 4.3 * size, 6.4 * size, 1)
            self.ellipse(x, y + .5, 3.3 * size, 5.3 * size, EYE_WHITE)
            self.ellipse(x + 1, y - .2, 1.6 * size, 3.4 * size, 1)
            self.ellipse(x + .7, y + 2.2, 1, 1, 2)
            if clip == 'attack' and n < 3:
                self.line([(x - 4, y + 6), (x + 3, y + 3)], 1, 2)

    def face(self, x, y, clip, n, size=1.):
        for dx in (-6, 6):
            self.eye(x + dx * size, y, clip, n, size)
        if clip != 'die' or n < 2:
            self.ellipse(x - 11 * size, y - 5, 2.5, 1.3, BLUSH)
            self.ellipse(x + 11 * size, y - 5, 2.5, 1.3, BLUSH)
        self.line([(x - 3, y - 8), (x, y - 9), (x + 3, y - 8)], 1)


def motion(clip, n):
    phase = n * math.pi / 4
    stride = math.sin(phase) if clip == 'walk' else 0
    bob = [0, 1, 2, 1, 0, -1][n] * .5 if clip == 'idle' else 0
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    fall = [0, .07, .19, .36, .56, .76, .92, 1.0][n] if clip == 'die' else 0
    return stride, bob, recoil, fall


ATTACK = [-1.4, -2.8, -4.0, .6, 4.0, 3.4, 1.5, 0.0]
SW = [(.32, 0.), (.68, 0.), (1., 0.), (.25, .75), (0., 1.), (0., .84), (0., .38), (0., 0.)]


def atk(clip, n):
    return SW[n] if clip == 'attack' else (0., 0.)


def foot(a, x, lift, rx, ry, ramp):
    """A planted foot: integer ry and centre y = ry, so its lowest pixel is row ay when lift is 0."""
    a.ball(x, ry + lift, rx, ry, ramp)


def spark(a, x, y, col=TEAL[4], r=3):
    y = max(y, r + 1)
    a.line([(x - r, y), (x + r, y)], col, 1)
    a.line([(x, y - r), (x, y + r)], col, 1)


# ----------------------------------------------------------------------------------------------
# 1. Reliquary Crab (`reliccrab`): rose-coral carapace with a gold-and-teal-glass pearl shrine on its back,
#    stalked glossy eyes, eight jointed legs, and two pincer claws.
#    Attack: leans back and rears both claws high overhead (pincers wide), then lunges and slams them far
#    ahead with reliquary sparks before recovering.
#    Death: legs curl inward as the rigid shell rolls onto its back on the floor, claws slack on the ground
#    and the shrine glass cracked.
# ----------------------------------------------------------------------------------------------
def reliccrab(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    a = Painter('reliccrab', recoil + st * 4 - wu * 3 + 8 * t)
    ph = n * math.pi / 4
    cy0 = 26 + bob * .6 - wu * 1.5 - st * 2
    ang = 3.0 * t
    half = max(13, round(math.hypot(22 * math.sin(ang), 13 * math.cos(ang))))
    cy = mix(cy0, half, t)

    def T(x, y):
        dx, dy = rot(x + 2, y - cy0, ang)
        return -2 + dx, max(3.5, cy + dy)

    # Four pairs of jointed walking legs; near feet rest on y=0 at x = -28, -11, 7, 24 (4 clear ground runs & leg tracks)
    near_x = (-28, -11, 7, 24)
    hips_x = (-19, -7, 5, 16)
    for far in (True, False):
        for k in range(4):
            hx = hips_x[k] + (-2 if far else 0)
            fx = near_x[k] + (-3 if far else 0)
            d = -1 if k < 2 else 1
            s = ph + (k % 2) * math.pi + (math.pi if far else 0)
            lift = max(0, math.sin(s)) * 4.5 if clip == 'walk' else 0
            push = math.cos(s) * 2.5 if clip == 'walk' else 0
            base = 4 if far else 0
            hip = (hx, cy0 - 4)
            knee = (hx + d * 7, cy0 - 1 + lift * .4)
            ft = (fx + push + (d * st * 2 if clip == 'attack' else 0), base + lift)
            if t > 0:
                knee = (mix(knee[0], hx + d * 5, t), mix(knee[1], cy0 - 11, t))
                ft = (mix(ft[0], hx + d * 2, t), mix(ft[1], cy0 - 16 - (k % 2) * 2, t))
                pts = [T(*hip), T(*knee), T(*ft)]
                ramp = MAROON if far else CORAL
                a.limb(pts, ramp, 3)
                a.ball(pts[2][0], max(4, pts[2][1]), 2.5, 2.5, ramp)
            else:
                ramp = MAROON if far else CORAL
                a.limb([hip, knee, (ft[0], ft[1] + 3)], ramp, 3)
                foot(a, ft[0], ft[1], 2.8, 3, ramp)

    def draw_claw(cx_, cy_, far):
        ramp = MAROON if far else CORAL
        if clip == 'die':
            fx, fy = (-24, 7) if far else (-32, 6)
            cx_, cy_ = mix(cx_, fx, t), mix(cy_, fy, t)
        openness = 3 + wu * 8 - st * 2.5 if clip == 'attack' else (2.8 + bob * .6 if not fall else max(.5, 2.8 - n * .35))
        phi = (wu * 1.05 - st * .45) if clip == 'attack' else ang * .35
        sh = T(11 if far else 14, cy0 + (2 if far else -2))
        a.limb([sh, (mix(sh[0], cx_, .5), mix(sh[1], cy_, .5) + 4), (cx_, cy_)], ramp, 5)
        a.ball(cx_, max(6, cy_), 7.5, 6.5, ramp)
        for sgn in (1, -1):
            p0 = rot(4.5, sgn * 2.8, phi)
            p1 = rot(11.5, sgn * (3.2 + openness * .65), phi)
            p2 = rot(17.5, sgn * (.7 + openness * .28), phi)
            pts = bez((cx_ + p0[0], max(4, cy_ + p0[1])),
                      (cx_ + p1[0], max(4, cy_ + p1[1])),
                      (cx_ + p2[0], max(4, cy_ + p2[1])))
            taper(a, pts, GOLD if (not far and sgn > 0) else ramp, 4.5, 1)

    far_c = (mix(mix(22, 16, wu), 38, st), mix(mix(32, 60, wu), 22, st))
    near_c = (mix(mix(24, 22, wu), 43, st), mix(mix(16, 52, wu), 15, st))
    draw_claw(*far_c, True)

    # Reliquary case on the back of the carapace (fades before rotating below the shell)
    shrine_fade = 1 - min(1, t * 2.1)
    if shrine_fade > .08:
        h_box = 12 * shrine_fade
        a.poly([T(-16, cy0 + 11), T(2, cy0 + 11), T(2, cy0 + 14), T(-16, cy0 + 14)], GOLD[1])
        a.poly([T(-15, cy0 + 14), T(1, cy0 + 14), T(1, cy0 + 14 + h_box), T(-15, cy0 + 14 + h_box)], TEAL[2])
        a.line([T(-15, cy0 + 14), T(-15, cy0 + 14 + h_box), T(1, cy0 + 14 + h_box), T(1, cy0 + 14)], GOLD[2], 2)
        a.poly([T(-17, cy0 + 14 + h_box), T(-7, cy0 + 14 + h_box + 8 * shrine_fade), T(3, cy0 + 14 + h_box)], GOLD[3])
        px, py = T(-7, cy0 + 14 + h_box * .5)
        a.ball(px, max(5, py), 4, 4, PEARL if t < .4 else PLATE)

    # Domed rose-coral carapace (guaranteed bottom on y=0 when rolled over at t > 0)
    a.ball(-2, max(14, cy), 22, 13, CORAL, ang)
    if t > 0:
        foot(a, -2, 0, 8, 3, CORAL)
    for k in range(5):
        nx, ny = T(-13 + k * 5.5, cy0 + 8 - abs(k - 2) * .8)
        a.ball(nx, max(3, ny), 2.4, 2.2, BONE)
    if t > .25:
        a.line([T(-6, cy0 + 9), T(-2, cy0 + 2), T(-5, cy0 - 6)], OUTLINE, 2)

    # Eye stalks with large glossy eyes and blush
    for ex0, ey0, sz in ((12, cy0 + 17, .92), (21, cy0 + 15, .86)):
        shrink = 1 - .7 * t
        b0 = T(ex0 - 3, cy0 + 7)
        tp = T(ex0 - 3 + 3 * shrink, cy0 + 7 + (ey0 - cy0 - 7) * shrink)
        a.limb([b0, (tp[0], max(6, tp[1] - 2))], CORAL, 3)
        a.eye(tp[0], max(8, tp[1]), clip, n, sz)
    if not fall:
        a.ellipse(18, cy0 + 4, 2.5, 1.3, BLUSH)
        a.ellipse(8, cy0 + 5, 2.5, 1.3, BLUSH)

    draw_claw(*near_c, False)
    if clip == 'attack' and st > .5:
        for k in range(3):
            spark(a, near_c[0] + 13 + k * 4, 6 + k * 5 + (n % 2) * 2, TEAL[4] if k % 2 else GOLD[4], 3)
    if clip == 'die' and fall > .25:
        for k in range(3):
            a.ellipse(-16 + k * 14 + (n % 2) * 2, 3 + (k % 2) * 2, 2, 1.5, TEAL[3 - k % 2])
    return a


# ----------------------------------------------------------------------------------------------
# 2. Neritha, the Pearl Widow (`pearlwidow`): deep-violet cephalothorax with fangs and glossy eyes,
#    giant lustrous pearl abdomen with a crimson hourglass mark and dangling silk pearl, on eight jointed
#    spider legs with pearl knee joints.
#    Attack: rears front legs and cephalothorax high up with fangs parted, then lunges far forward slamming
#    legs and fangs down with venom-pearl droplets before recovering.
#    Death: legs buckle and curl inward over the carapace as the pearl abdomen and body sink to the floor.
# ----------------------------------------------------------------------------------------------
def pearlwidow(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    a = Painter('pearlwidow', recoil + st * 5 - wu * 3)
    by = mix(26 + bob * .6 + wu * 3 - st * 3, 14, t)

    # Four near feet at (-36, -18, 8, 28), far feet shifted; all planted on y=0 in idle
    hips = (-16, -6, 4, 13)
    feet = (-36, -18, 8, 28)

    def draw_legs(far):
        for k in range(4):
            hx = hips[k] + (-2 if far else 1)
            fx = feet[k] + (-3 if far else 0)
            s = ph + (k % 2) * math.pi + (math.pi if far else 0)
            lift = max(0, math.sin(s)) * 5 if clip == 'walk' else 0
            push = math.cos(s) * 3 if clip == 'walk' else 0
            base = 4 if far else 0
            if clip == 'attack' and k >= 2:
                lift = wu * (18 if k == 3 else 13) + st * (2 if k == 3 else 0)
                push = -wu * 5 + st * (16 if k == 3 else 10)
            hip = (hx, by + 1)
            kx = mix(hx, fx + push, .58)
            ky = by + 16 + (3 if k in (1, 2) else 0) + lift * .65 - t * 9
            ft = (fx + push, base + lift)
            if t > 0:
                kx = mix(kx, hx + (8 if fx > 0 else -8), t)
                ky = mix(ky, by + 12 - k, t)
                ft = (mix(ft[0], hx + (14 if fx > 0 else -14), t), 0 if not far else 3)
            ramp = PURPLE if far else VIOLET
            a.limb([hip, (kx, ky), (ft[0], ft[1] + 3)], ramp, 3)
            a.ball(kx, ky, 3, 3, PEARL)
            foot(a, ft[0], ft[1], 2.8, 3, ramp)

    draw_legs(True)

    # Giant pearl abdomen with hourglass mark and silk-thread pearl
    ax_, ay_ = -18 - wu * 2 + st * 2, mix(by + 7 - wu * 2, 14, t)
    a.ball(ax_, ay_, 19, 14 if t > .6 else 16, PEARL)
    if t > .5:
        foot(a, ax_, 0, 11, 3, PEARL)
    a.poly([(ax_ - 6, ay_ + 8), (ax_ + 6, ay_ + 8), (ax_, ay_)], MAROON[2], outline=OUTLINE)
    a.poly([(ax_ - 6, ay_ - 8), (ax_ + 6, ay_ - 8), (ax_, ay_)], MAROON[2], outline=OUTLINE)
    a.ball(ax_, ay_, 2.5, 2.5, GOLD)
    if t > .25:
        a.line([(ax_ - 8, ay_ + 11), (ax_ - 2, ay_ + 3), (ax_ - 6, ay_ - 5)], OUTLINE, 2)
    sx = ax_ - 13 + (math.sin(n * .9) * 2 if not fall else t * 4)
    sy = max(3, ay_ - 20 * (1 - t * .6))
    a.line([(ax_ - 12, ay_ - 8), (sx, sy)], PEARL[3], 1)
    a.ball(sx, sy, 3.2, 3, PEARL)

    draw_legs(False)

    # Cephalothorax, eyes, blush, and fangs hanging from the mouth corners
    hx = 12 + st * 6 - wu * 2
    hy = mix(by + 3 + wu * 9 - st * 3, 12, t)
    a.ball(hx, hy, 14, 12, VIOLET)
    if t > .4:
        foot(a, hx, 0, 9, 3, VIOLET)
    for k in range(3):
        a.ellipse(hx - 5 + k * 4.5, hy + 8 + (k % 2), 1.6, 1.6, CORAL[3])
    a.face(hx + 3, hy + 3, clip, n, .82)
    spread = .7 + wu * 2.2 + st * 2.8
    for sg in (-1, 1):
        bx = hx + 3 + sg * 3.2
        my = hy - 5.0
        tip = (bx + sg * spread * .45, max(2, my - 4.5 - wu * 1.5 - st * 2.5))
        a.poly([(bx - 1.5, my), (bx + 1.5, my), tip], BONE[4], outline=OUTLINE)
    if clip == 'attack' and st > .5:
        for k in range(3):
            a.ball(hx + 20 + k * 5, max(5, hy - 2 + (k - 1) * 4), 2.8 - k * .3, 2.8 - k * .3, PEARL)
    if clip == 'die' and fall > .3:
        for k in range(3):
            a.ellipse(-20 + k * 16 + (n % 2) * 2, 3 + (k % 2) * 2, 1.8, 1.5, PEARL[3])
    return a


# ----------------------------------------------------------------------------------------------
# 3. Ilyr, Cantor of Shattered Glass (`glasscantor`): pointed-arch stained-glass lancet robe and hood,
#    orbiting stained-glass diamond shards, and a golden tuning-fork scepter.
#    Attack: raises the tuning-fork scepter high overhead as the glass shards gather, then sweeps the scepter
#    far forward to launch a fan of stained-glass shards and sound rings before recovering.
#    Death: cracks spread across the lancet panes, the scepter drops flat to the floor, and the stained-glass
#    robe shatters downward into a glittering pile of coloured shards and collapsed hood on the floor.
# ----------------------------------------------------------------------------------------------
def glasscantor(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    sway = math.sin(ph) * 2 if clip == 'walk' else math.sin(n * math.pi / 3) * .8 if clip == 'idle' else 0
    a = Painter('glasscantor', recoil + st * 3 - wu * 2)

    h = mix(1.0, .32, t)
    hw = round(mix(16, 26, t))
    top = 44 * h + bob * .4 * (1 - t)

    # Pointed lancet robe resting solidly on the floor (y=0)
    a.poly([(-10 + sway * .4, top), (10 + sway * .4, top), (hw, 0), (-hw, 0)], VIOLET[1], outline=OUTLINE)
    a.poly([(-10 + sway * .4, top), (-1, top), (-2, 0), (-hw, 0)], VIOLET[0])
    a.line([(-hw + 1, 0), (hw - 1, 0)], OUTLINE, 1)
    a.line([(-hw + 2, 2), (hw - 2, 2)], GOLD[2], 2)

    # Stained-glass diamond panes inside the robe (intact while alive, shattering downward on death)
    panes = [
        (-6, 32, CORAL), (5, 32, TEAL), (0, 25, AMBER),
        (-8, 18, BLUE), (8, 18, CORAL), (0, 12, TEAL),
        (-10, 7, AMBER), (10, 7, BLUE),
    ]
    for k, (px, py, ramp) in enumerate(panes):
        if clip == 'die':
            drop = sm(max(0, (fall - k * .05) / .65))
            sx = px * mix(1., 1.65, drop) + ((k % 3) - 1) * 3 * drop
            sy = mix(py * h, 3 + (k % 3) * 1.5, drop)
        else:
            sx, sy = px + sway * .5 * (py / 36), py * h
        rx, ry = 4.2, mix(5.2, 2.8, t)
        a.poly([(sx, sy + ry), (sx + rx, sy), (sx, sy - ry), (sx - rx, sy)], ramp[3], outline=OUTLINE)
        a.poly([(sx, sy + ry - 1), (sx - rx + 1, sy), (sx, sy)], ramp[4])

    if clip == 'die' and fall > .1:
        a.line([(-4, top - 2), (3, top * .6), (-3, top * .3), (4, 3)], OUTLINE, 2)

    # Hood and face
    hx = mix(0, 7, t) + sway * .3
    hy = mix(54 + bob * .5 + wu * 2 - st * 1, 13, t)
    a.poly([(hx - 13, hy - 4), (hx - 11, hy + 8), (hx, hy + 18 * mix(1, .6, t)),
            (hx + 11, hy + 8), (hx + 13, hy - 4)], VIOLET[2], outline=OUTLINE)
    a.ball(hx, hy, 11.5, mix(10.5, 7, t), VIOLET)
    a.ball(hx + 1, hy - 1, 8.8, mix(8.2, 5.5, t), PEARL)
    a.face(hx + 1, hy - 1, clip, n, .74)
    if (clip == 'attack' and (wu > .2 or st > .2)) or (clip == 'idle' and n in (1, 2)):
        a.ellipse(hx + 1, hy - 6, 2.5, 2.0, OUTLINE)

    # Left sleeve
    a.limb([(-9, 38 * h), (-16, 30 * h), (-18 - wu * 2, mix(24, 4, t))], VIOLET, 4)
    a.ball(-18 - wu * 2, mix(24, 4, t), 3.4, 3.4, PEARL)

    # Right arm and golden tuning-fork scepter (raised high on wind-up clear of the face, thrust forward on strike)
    hx_r = mix(mix(18, 19, wu), 30, st)
    hy_r = mix(mix(30 + bob * .4, 54, wu), 32, st)
    ang = mix(mix(.18, .08, wu), 1.28, st)
    if clip == 'die':
        drop = sm(fall / .55)
        hx_r, hy_r = mix(18, 22, drop), mix(30, 3, drop)
        ang = mix(.18, 1.54, drop)
    if clip != 'die' or fall < .35:
        a.limb([(9, 38 * h), ((9 + hx_r) / 2, (38 * h + hy_r) / 2 + 2), (hx_r, hy_r)], VIOLET, 4)
    d = (math.sin(ang), math.cos(ang))
    nrm = (-d[1], d[0])
    base = (hx_r - d[0] * 8, max(2, hy_r - d[1] * 8))
    tip = (hx_r + d[0] * 18, max(3, hy_r + d[1] * 18))
    a.line([base, tip], GOLD[0], 4)
    a.line([base, tip], GOLD[3], 2)
    for sg in (-1, 1):
        p0 = (tip[0] + nrm[0] * sg * 4, max(2, tip[1] + nrm[1] * sg * 4))
        p1 = (p0[0] + d[0] * 10, max(2, p0[1] + d[1] * 10))
        a.line([tip, p0, p1], TEAL[0], 3)
        a.line([tip, p0, p1], TEAL[4] if st > .3 else TEAL[3], 1)
    if clip != 'die' or fall < .35:
        a.ball(hx_r, hy_r, 3.5, 3.5, PEARL)

    # Five orbiting stained-glass shards (gather high on wind-up, shoot forward on strike, scatter to floor on death)
    shard_ramps = (CORAL, AMBER, TEAL, BLUE, CORAL)
    for k, sr in enumerate(shard_ramps):
        orb_n = 0 if (clip == 'attack' and n == 7) else n
        orb = orb_n * math.pi / 4 + k * 2 * math.pi / 5
        ox = math.cos(orb) * 24
        oy = 46 + math.sin(orb) * 9 + k * 2
        if clip == 'attack':
            ox = mix(mix(ox, -10 + k * 4, wu), 28 + k * 5, st)
            oy = mix(mix(oy, 68 + (k % 2) * 6, wu), 30 + (k - 2) * 7, st)
        elif clip == 'die':
            sd = sm(max(0, (fall - k * .06) / .6))
            ox = mix(ox, -20 + k * 10 + (n % 2), sd)
            oy = mix(oy, 5, sd)
        a.poly([(ox, oy + 5), (ox + 3.5, oy), (ox, max(2, oy - 5)), (ox - 3.5, oy)], sr[3], outline=OUTLINE)
        if st > .4 and clip == 'attack':
            spark(a, ox + 5, oy, sr[4], 2)
    return a


# ----------------------------------------------------------------------------------------------
# 4. Sarkhos, Warden of the Reliquary (`relicwarden`): heavy crimson-and-gold plated crustacean juggernaut
#    on four armoured legs, with a teal heart-gem, horned coral-and-gold helm, kite shield and massive
#    war-hammer pincer claw.
#    Attack: braces behind the kite shield and heaves the war-hammer claw high overhead, then lunges forward
#    and slams it down ahead with shockwave sparks before recovering.
#    Death: four armoured legs buckle outward, kite shield and hammer-claw drop flat onto the floor, cracks
#    split the carapace and heart-gem, and the heavy plated shell slumps low on the ground.
# ----------------------------------------------------------------------------------------------
def relicwarden(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    a = Painter('relicwarden', recoil + st * 4 - wu * 3)
    by = mix(30 + bob * .6 + wu * 2 - st * 3, 14, t)

    # Four heavy armoured legs planted at x = -28, -11, 9, 26 (4 distinct ground runs & leg tracks in idle)
    hips = (-18, -7, 6, 17)
    feet = (-28, -11, 9, 26)
    for k in range(4):
        hx, fx = hips[k], feet[k]
        d = -1 if k < 2 else 1
        s = ph + (k % 2) * math.pi
        lift = max(0, math.sin(s)) * 4.5 if clip == 'walk' else 0
        push = math.cos(s) * 2.5 if clip == 'walk' else 0
        hip = (hx, by - 4)
        knee = (mix(hx, fx, .55) + d * 3, by + 2 + lift * .4 - t * 4)
        ft = (fx + push + (d * st * 2 if clip == 'attack' else 0), lift * (1 - t))
        if t > 0:
            ft = (fx + d * 5 * t, 0)
            knee = (mix(hx, ft[0], .6), max(7, by - 1))
        ramp = CRIMSON[:4] if k in (0, 2) else CRIMSON
        a.limb([hip, knee, (ft[0], ft[1] + 3)], ramp, 4)
        a.ball(knee[0], knee[1], 4, 4, GOLD)
        foot(a, ft[0], ft[1], 3.4, 3, ramp)

    # Far arm: gold-and-crimson kite shield (dropped flat on the floor on death)
    if t < .55:
        shx = 24 - wu * 4 + st * 3
        shy = by + 2 - t * 10
        a.limb([(10, by + 4), (shx - 5, shy)], CRIMSON[:4], 4)
        a.poly([(shx - 9, shy + 14), (shx + 9, shy + 14), (shx + 8, shy - 6),
                (shx, shy - 17), (shx - 8, shy - 6)], GOLD[2], outline=OUTLINE)
        a.poly([(shx - 6, shy + 11), (shx + 6, shy + 11), (shx + 5, shy - 5),
                (shx, shy - 13), (shx - 5, shy - 5)], CRIMSON[2])
        a.ball(shx, shy, 3.5, 4, TEAL)
    else:
        a.ball(26, 4, 10, 4, GOLD)

    # Plated carapace with three gold-trimmed segments and teal heart-gem
    a.ball(-2, by, 23, 14 if not fall else mix(14, 11, t), CRIMSON)
    if t > .35:
        foot(a, -2, 0, 12, 3, CRIMSON)
    for k in range(3):
        px = -14 + k * 9.5
        a.line([(px - 4, by + 11 - k), (px + 4, by + 11 - k)], GOLD[3], 2)
        a.line([(px - 4, by + 11 - k), (px - 5, by - 5)], GOLD[1], 1)
    a.ball(8, by - 2, 4.5, 5, TEAL if t < .6 else PLATE)
    if t > .2:
        a.line([(-6, by + 12), (0, by + 3), (-4, by - 7)], OUTLINE, 2)
        a.line([(6, by + 3), (10, by - 6)], OUTLINE, 2)

    # Helmed head and massive war-hammer pincer claw: head drawn over shoulder so both eyes stay clear
    wr_x = mix(mix(28, 22, wu), 40, st)
    wr_y = mix(mix(by + 14, by + 44, wu), 17, st)
    ang = mix(mix(.45, .35, wu), -.22, st)
    openness = 3 + wu * 7 - st * 2.5 if clip == 'attack' else 3
    if clip == 'die':
        drop = sm(fall / .6)
        wr_x, wr_y = mix(28, 34, drop), mix(by + 14, 8, drop)
        ang = mix(.45, -.05, drop)
        openness = 2
    sh = (12, by + 6)
    a.limb([sh, (mix(sh[0], wr_x, .5), mix(sh[1], wr_y, .5) + 3), (wr_x, wr_y)], CRIMSON, 6)
    a.ball(13, by + 8, 6.5, 6.5, GOLD)

    # Helmed head with coral-and-gold horns, glossy eyes and blush
    hx = 10 + st * 2 - wu * 1
    hy = mix(by + 17, 15, t)
    a.ball(hx, hy, 13, 11, CRIMSON)
    for k, (dx, hh, tilt) in enumerate(((-7, 10, -3), (-1, 14, -1), (5, 12, 1), (10, 8, 3))):
        col = BONE[3] if k % 2 else GOLD[3]
        a.poly([(hx + dx - 3, hy + 8), (hx + dx + tilt, hy + 8 + hh * (1 - t * .35)), (hx + dx + 3, hy + 8)],
               col, outline=OUTLINE)
    a.line([(hx - 9, hy + 7), (hx + 11, hy + 7)], GOLD[2], 2)
    a.face(hx + 2, hy - 1, clip, n, .78)

    a.ball(wr_x, wr_y, 9, 7.5, CRIMSON)
    for sgn in (1, -1):
        p0 = rot(5, sgn * 3.5, ang)
        p1 = rot(13, sgn * (4 + openness * .65), ang)
        p2 = rot(20, sgn * (1 + openness * .3), ang)
        pts = bez((wr_x + p0[0], max(5, wr_y + p0[1])),
                  (wr_x + p1[0], max(5, wr_y + p1[1])),
                  (wr_x + p2[0], max(5, wr_y + p2[1])))
        taper(a, pts, GOLD if sgn > 0 else CRIMSON, 5.5, 1.5)
    if clip == 'attack' and st > .5:
        for k in range(4):
            spark(a, wr_x + 16 + k * 4, 5 + (k % 2) * 5 + (n - 3) * 2, TEAL[4] if k % 2 else GOLD[4], 3)
    if clip == 'die' and fall > .3:
        for k in range(3):
            a.ellipse(-18 + k * 15 + (n % 2) * 2, 3 + (k % 2) * 2, 2, 1.5, GOLD[3 - k % 2])
    return a


# ----------------------------------------------------------------------------------------------
# 5. Queen Avariel, the Coral Regent (`coralregent`): regal rose-coral gown with living coral branches on the
#    hem, pearl belt, streaming sea-teal hair, gold-and-coral antler crown, and a royal pearl-orb scepter.
#    Attack: lifts the pearl-orb scepter high above her crown with a tidal halo, then sweeps it far forward in
#    a commanding arc unleashing pearl-and-coral wave energy before recovering.
#    Death: the scepter clatters flat on the floor ahead, the coral crown tips off and tumbles beside her, and
#    she swoons as her royal gown pools wide and low across the floor.
# ----------------------------------------------------------------------------------------------
def coralregent(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    sway = math.sin(ph) * 2 if clip == 'walk' else math.sin(n * math.pi / 3) * 1.2 if clip == 'idle' else 0
    a = Painter('coralregent', recoil + st * 4 - wu * 2)

    h = mix(1.0, .34, t)
    hw = round(mix(21, 30, t))
    top = 42 * h + bob * .4 * (1 - t)
    hx = mix(2, 10, t)
    hy = mix(56 + bob * .5 + wu * 2 - st * 1, 16, sm(fall / .85))

    # Streaming sea-teal hair behind the shoulders
    hair_pts = [
        (hx - 6, hy + 5),
        (hx - 16 + sway, hy - 8 * h),
        (hx - 23 + sway * 1.4, max(3, hy - 26 * h)),
        (hx - 14 + sway, max(2, hy - 34 * h)),
        (hx - 4, max(4, hy - 14 * h)),
    ]
    a.poly(hair_pts, TEAL[2], outline=OUTLINE)
    a.line([hair_pts[0], hair_pts[2]], TEAL[3], 2)

    # Flared royal gown resting on y=0 with living coral branches along the hem
    a.poly([(-9 + sway * .3, top), (9 + sway * .3, top), (hw, 0), (-hw, 0)], CORAL[2], outline=OUTLINE)
    a.poly([(-9 + sway * .3, top), (-1, top), (-2, 0), (-hw, 0)], CORAL[1])
    a.line([(-hw + 1, 0), (hw - 1, 0)], OUTLINE, 1)
    for dx in (-9, 2, 10):
        a.line([(dx * .4 + sway * .3, top - 3), (dx * mix(1.4, 1.8, t), 2)], CORAL[3] if dx > 0 else CORAL[0], 1)
    for k, (cx_, ch) in enumerate(((-19, 11), (-13, 14), (13, 13), (19, 10))):
        ch2 = ch * mix(1.0, .45, t)
        bx = cx_ * mix(1.0, 1.25, t)
        a.poly([(bx - 3, 1), (bx - 1 + sway * .2, 1 + ch2), (bx + 2, 1 + ch2 * .6), (bx + 3, 1)],
               PINK[4] if k % 2 else PINK[3], outline=OUTLINE)
    for k in range(-4, 5):
        a.ball(k * hw / 4.8, 3, 2, 2, PEARL)

    # Bodice and gold corset belt
    a.ball(0, 34 * h + 2, 11, 10 * h + 1, CORAL)
    a.line([(-11, 23 * h + 2), (11, 23 * h + 2)], GOLD[2], 3)
    a.ball(0, 23 * h + 2, 3.2, 3.2, PEARL)

    # Left arm
    a.limb([(-9, 39 * h), (-16, 33 * h), (-18 - wu * 2, mix(27, 5, t))], CORAL, 4)
    a.ball(-18 - wu * 2, mix(27, 5, t), 3.4, 3.4, BONE)

    # Head, teal fringe, glossy eyes and blush
    a.ball(hx, hy, 12, 11, BONE)
    a.poly([(hx - 12, hy + 4), (hx - 7, hy + 11), (hx + 4, hy + 9), (hx + 12, hy + 9), (hx + 7, hy + 3)],
           TEAL[3], outline=OUTLINE)
    a.face(hx + 1, hy - 1, clip, n, .76)

    # Gold-and-coral antler crown (tumbles to the floor beside her on death)
    drop_c = sm(max(0, (fall - .2) / .65)) if clip == 'die' else 0
    cx_c = mix(hx, -20, drop_c)
    cy_c = mix(hy + 10, 3, drop_c)
    a.line([(cx_c - 9, cy_c), (cx_c + 9, cy_c)], GOLD[2], 3)
    for k, (dx, hh, tilt) in enumerate(((-7, 9, -2), (-2, 13, -1), (3, 13, 1), (8, 9, 2))):
        hh2 = hh * (1 - drop_c * .35)
        a.poly([(cx_c + dx - 2.5, cy_c + 1), (cx_c + dx + tilt, cy_c + 1 + hh2), (cx_c + dx + 2.5, cy_c + 1)],
               PINK[4] if k % 2 else GOLD[3], outline=OUTLINE)
    a.ball(cx_c, cy_c + 3, 2.5, 2.5, PEARL)

    # Right arm and royal pearl-orb scepter (raised high clear of the face on wind-up, swept forward on strike)
    hx_r = mix(mix(19, 20, wu), 30, st)
    hy_r = mix(mix(31 + bob * .4, 65, wu), 34, st)
    ang = mix(mix(.15, .04, wu), 1.22, st)
    if clip == 'die':
        drop = sm(fall / .55)
        hx_r, hy_r = mix(19, 24, drop), mix(31, 5, drop)
        ang = mix(.15, 1.53, drop)
    if clip != 'die' or fall < .35:
        a.limb([(9, 39 * h), ((9 + hx_r) / 2, (39 * h + hy_r) / 2 + 2), (hx_r, hy_r)], CORAL, 4)
        a.ball((9 + hx_r) / 2, (39 * h + hy_r) / 2 + 2, 4, 3.5, GOLD)
    d = (math.sin(ang), math.cos(ang))
    base = (hx_r - d[0] * 10, max(4, hy_r - d[1] * 10))
    tip = (hx_r + d[0] * 21, max(7, hy_r + d[1] * 21))
    a.line([base, tip], GOLD[0], 4)
    a.line([base, tip], GOLD[3], 2)
    a.ball(tip[0], tip[1], 6, 6, PEARL)
    a.ellipse(tip[0] - 1.5, tip[1] + 2, 2, 2, WHITE)
    if clip != 'die' or fall < .35:
        a.ball(hx_r, hy_r, 3.5, 3.5, BONE)
    if clip == 'attack' and st > .5:
        for k in range(3):
            wx = tip[0] + 6 + k * 4.5
            wy = max(8, tip[1] + (k - 1) * 6)
            a.ball(wx, wy, 3 - k * .3, 3 - k * .3, PEARL if k % 2 else TEAL)
            spark(a, wx + 2, wy + 2, TEAL[4], 2)
    return a


# ----------------------------------------------------------------------------------------------
# 6. Reliquary Pearl (`reliquarypearl`, boss-mechanic helper add): a giant luminous pearl with iridescent
#    sheen and glossy eyes, cradled in a hinged fluted clam-shell reliquary on a gold base.
#    Attack: hinges the upper clam-shell lid high open as the pearl swells, then lunges/snaps forward shooting
#    a pearl-sheen burst before recovering.
#    Death: dark cracks spread across the pearl, its sheen gutters out, the pearl splits into shards inside
#    the shell, and the cracked upper lid collapses shut over the broken pearl on the floor.
# ----------------------------------------------------------------------------------------------
def reliquarypearl(clip, n):
    stride, bob, recoil, fall = motion(clip, n)
    t = sm(fall)
    wu, st = atk(clip, n)
    ph = n * math.pi / 4
    rock = math.sin(ph) * 2.5 if clip == 'walk' else 0
    a = Painter('reliquarypearl', recoil + rock + st * 5 - wu * 3)

    # Gold reliquary pedestal resting on y=0 and fluted lower clam shell
    foot(a, 0, 0, 14, 3, GOLD)
    a.ball(0, 9, 23, 8, MAROON)
    a.ball(0, 11, 18, 5, PINK)
    for k in range(-3, 4):
        a.line([(k * 5, 4), (k * 6, 11)], MAROON[0], 1)
    a.ball(0, 5, 5, 3, GOLD)

    # Luminous pearl inside the shell (rises on wind-up, thrusts forward on strike, splits & sinks on death)
    px = st * 6 - wu * 2
    py = mix(26 + bob * .7 + wu * 5 - st * 1, 14, t)
    prx = round(mix(17, 19, t))
    pry = round(mix(17, 9, t))
    if t < .65:
        a.ball(px, py, prx, pry, PEARL)
        a.ellipse(px - 6, py + pry * .45, 5, 3, TEAL[3])
        a.ellipse(px + 6, py - pry * .3, 4, 2.5, PINK[3])
        a.ellipse(px - 7, py + pry * .55, 2.5, 1.5, WHITE)
        if t > .1:
            a.line([(px - 2, py + pry - 2), (px + 3, py + 2), (px - 3, py - 4), (px + 2, py - pry + 2)], OUTLINE, 2)
            a.line([(px + 3, py + 2), (px + 10, py - 2)], OUTLINE, 2)
        a.face(px + 2, py, clip, n, .85)
    else:
        # Split into two cracked pearl halves inside the shell
        for sg in (-1, 1):
            a.ball(sg * 8, 13, 10, 7, PEARL[:4])
            a.line([(sg * 3, 18), (sg * 5, 9)], OUTLINE, 2)
        a.eye(4, 13, 'die', n, .75)

    # Hinged upper clam-shell lid (hinged high open on wind-up, snaps forward on strike, collapses over the pearl on death)
    lid_y = mix(mix(47 + bob * .6, 59, wu), 38, st)
    lid_x = mix(mix(-2, -6, wu), 8, st)
    lid_ang = mix(mix(.18, .48, wu), -.22, st)
    if clip == 'die':
        lid_x = mix(-2, 2, t)
        lid_y = mix(47, 19, t)
        lid_ang = mix(.18, -.08, t)
    a.ball(lid_x, lid_y, 21, 8, MAROON, lid_ang)
    a.ball(lid_x + 1, lid_y - 2, 15, 4, PINK, lid_ang)
    r0 = rot(-16, -1, lid_ang)
    r1 = rot(16, -1, lid_ang)
    a.line([(lid_x + r0[0], lid_y + r0[1]), (lid_x + r1[0], lid_y + r1[1])], GOLD[2], 2)
    if t > .3:
        a.line([(lid_x - 3, lid_y + 6), (lid_x + 2, lid_y - 5)], OUTLINE, 2)

    if clip == 'attack' and st > .5:
        for k in range(3):
            bx = px + 23 + k * 5.5
            by_ = 26 + (k - 1) * 7
            a.ball(bx, by_, 3.5 - k * .3, 3.5 - k * .3, PEARL if k % 2 else TEAL)
            spark(a, bx + 2, by_ + 2, TEAL[4], 2)
    if clip == 'die' and .12 < fall < .75:
        for k in range(3):
            a.ellipse(-10 + k * 10 + (n % 2) * 2, 22 + k * 3 + n, 1.5, 1.5, TEAL[3 - k % 2])
    return a


DRAW = dict(
    reliccrab=reliccrab,
    pearlwidow=pearlwidow,
    glasscantor=glasscantor,
    relicwarden=relicwarden,
    coralregent=coralregent,
    reliquarypearl=reliquarypearl,
)


def frame(kind, clip, n):
    kw, kh, _, _ = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    if os.environ.get('RELIQUARY_LOOSE'):
        ys, xs = np.nonzero(grid)
        if not grid.any() or min(xs.min(), ys.min()) <= 0 or xs.max() >= kw - 1 or ys.max() >= kh - 1:
            print('BOUNDS', kind, clip, n, (xs.min(), ys.min(), xs.max(), ys.max()) if grid.any() else 'empty')
        return grid
    assert grid.any(), (kind, clip, n, 'empty')
    assert not (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()), (kind, clip, n, 'border')
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def extents():
    """Measure bounds, ground row contact, leg runs, and attack wind-up/strike/recovery for all six kinds."""
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        data = frames(kind)
        lows = set()
        for clip, grids in data.items():
            for n, g in enumerate(grids):
                ys, xs = np.nonzero(g)
                lows.add(int(ys.max()))
        idle = data['idle']
        att = data['attack']
        die = data['die']
        idle_top = min(int(np.nonzero(g)[0].min()) for g in idle)
        idle_right = max(int(np.nonzero(g)[1].max()) for g in idle)
        idle0_ys, idle0_xs = np.nonzero(idle[0])
        att2_ys, att2_xs = np.nonzero(att[2])
        att4_ys, att4_xs = np.nonzero(att[4])
        att7_ys, att7_xs = np.nonzero(att[7])
        rises = idle_top - int(att2_ys.min())
        reach = int(att4_xs.max()) - idle_right
        rec = (int(att7_ys.min()) - int(idle0_ys.min()),
               int(att7_xs.min()) - int(idle0_xs.min()),
               int(att7_xs.max()) - int(idle0_xs.max()))

        def runs_at(g, y):
            row = g[y] > 0
            r, prev = 0, False
            for v in row:
                if v and not prev:
                    r += 1
                prev = bool(v)
            return r

        idle_gr = [runs_at(g, kay) for g in idle]
        walk_gr = [runs_at(g, kay) for g in data['walk']]
        idle_lt = [max(runs_at(g, kay - d) for d in range(7, 13)) for g in idle]
        att_hashes = len({g.tobytes() for g in att})
        die_hashes = len({g.tobytes() for g in die})
        print(f'{kind:15s} frame={kw}x{kh} ay={kay} lows={sorted(lows)} rises={rises} reach={reach} '
              f'rec={rec} att={att_hashes}/8 die={die_hashes}/8 idleGR={idle_gr} walkGR={walk_gr} idleLT={idle_lt}')


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    existing = {sp['name']: sp['sprite_id'] for sp in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        kw, kh, _, _ = kind_frame(kind)
        name = PREFIX + kind + '_all'
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/reliquary_slime_{kind}_raw.npz', **data[kind])
        sid = old.api('create', dict(
            name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
            palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]
        ))['sprite_id']
        print('Created native source', kind, sid, f'{kw}x{kh}', flush=True)
        offset = 0
        for clip, grids in data[kind].items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=sid, frame=offset + n,
                                     ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, offset, 'frames saved', flush=True)


def refresh():
    """Rewrite the frames of the named kinds' existing saved sources from the drawers."""
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = json.loads(REGISTRY.read_text())
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/reliquary_slime_{kind}_raw.npz', **data)
        offset = 0
        for clip, grids in data.items():
            for n, grid in enumerate(grids):
                old.api('draw', dict(sprite_id=saved[kind], frame=offset + n,
                                     ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
            offset += len(grids)
        print('Refreshed', kind, saved[kind], offset, 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    """Replace the six Reliquary atlases and ONLY their `sprites`/`tops`/`kindFrames` entries in cathedral.txt."""
    saved = json.loads(REGISTRY.read_text())
    assert set(saved) == set(KINDS)
    meta = json.loads(MANIFEST.read_text())
    before = json.loads(MANIFEST.read_text())
    proof, atlases, tops = {}, {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset = 0
        rows = []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), 'clip layout changed'
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        tops[kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frame=[kw, kh, kax, kay], frames=rows)
    meta = kindframe.merge_kind_entries(meta, KINDS, saved, tops, {k: kind_frame(k) for k in KINDS if k in KIND_FRAMES})
    for key in meta:
        if key in ('sprites', 'tops', 'kindFrames'):
            assert {k: v for k, v in (meta.get(key) or {}).items() if k not in KINDS} == \
                   {k: v for k, v in (before.get(key) or {}).items() if k not in KINDS}
            if key != 'kindFrames':
                assert list(meta[key]) == list(before[key]), 'key order changed'
        else:
            assert meta[key] == before[key], key
    for kind, atlas in atlases.items():
        dest = ASSETS / f'cathedral_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames; shared cathedral.txt changed only for', ', '.join(KINDS), flush=True)


def verify():
    """Compare the installed atlases directly to saved editor frames."""
    meta = json.loads(MANIFEST.read_text())
    saved = json.loads(REGISTRY.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'cathedral_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh),
                                              sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def preview():
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    for kind in only:
        kw, kh, kax, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8 * kw * 2, 5 * (kh * 2 + 24)), '#2b2438')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw * 2, kh * 2), Image.Resampling.NEAREST)
                x, y = n * kw * 2, row * (kh * 2 + 24)
                sheet.paste(im, (x, y), im)
                sd.line([(x, y + kay * 2 + 1), (x + kw * 2, y + kay * 2 + 1)], fill='#e8a0e0')
                sd.text((x + 6, y + kh * 2 + 2), f'{kind} {clip} {n}', fill='white')
        sheet.save(OUT / f'preview-{kind}.png')
    print('Wrote previews to', OUT)


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1]]()
