#!/usr/bin/env python3
"""The Obsidian Orrery redo (v2): six native PixelFlow slime-style sources with per-kind frames.

preview | extents | build | refresh <kinds> | export | verify

v1 (Beta 1.39.22) is kept as scripts/orrery_slime_v1_sources.txt and in the RAID backup
/media/raid/valhallasc-data/orrery-slime-v1-20261104. Owner rejected v1: the Bronze Mantis did not read as a mantis,
large parts were flat unshaded fills (shield, gown, gear rims) or two pixels thin (spear, pendulum arm), the creatures
looked small and plain, and attacks/deaths used floating '+' glyphs. This pass draws every body part as shaded volume
(`plate`/`gear`/`ball`), keeps props at least four pixels thick, sizes each kind's frame to its art, and gives every
kind eight distinct attack and death frames with no debug glyphs.

  - bronzemantis: bronze praying mantis: triangular head with big glossy eyes, long prothorax, two raptorial
    forelegs (femur plus spined steel blade) folded in front, four jointed walking legs, segmented abdomen with a
    verdigris wing case and a cog; rears both blades overhead then cuts forward and down; dies folding its legs.
  - gearling: round steel clockwork ball inside a big toothed copper gear with a winding key; crouches back,
    charges forward spinning with dust, then skids to a stop; dies as its rim gear breaks off and rolls away.
  - orbitseer: flying eyeball in two gyroscope rings with orbiting moons; charges a glowing pupil and fires a layered
    eye beam; dies by dropping to the ground with its rings settling flat around it.
  - chronoguard: armoured clock-knight with a gear-badge shield, crested helm and a thick spear; draws the spear
    back and thrusts; dies kneeling as the spear and shield clatter flat on the ground.
  - pendulummatron: clockwork matron in a pleated gown with a chained brass pendulum; swings it over her head and
    slams it forward; dies as the gown settles into a heap and the pendulum drops.
  - epochengine: huge clock-faced engine on piston legs with gear fists; raises both fists overhead and slams
    them down in a shockwave; dies as the pistons buckle and the rim gear breaks apart.
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
from astral_slime_redraw import (
    Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BLUSH,
    PLATE, TEAL, GOLD, FUR, BLUE, BROWN, PINK, PEARL, VIOLET, AMBER,
    AZURE, SLATE, mix, mixp, rot, sm, bez, taper, foot, arm_ik, biped_legs,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/orrery-slime'
REGISTRY = ROOT / 'scripts/orrery_slime_sources.txt'
MANIFEST = ASSETS / 'orrery.txt'
PREFIX = 'valhallasc_orrery_slime_style_b_'
KINDS = ['bronzemantis', 'gearling', 'orbitseer', 'chronoguard', 'pendulummatron', 'epochengine']
NAMES = dict(zip(KINDS, ['Bronze Mantis', 'Gearling', 'Orbit Seer', 'Chronoguard', 'Pendulum Matron', 'Epoch Engine']))
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    bronzemantis=(140, 118, 72, 112),
    gearling=(146, 88, 63, 82),
    orbitseer=(164, 92, 66, 86),
    chronoguard=(158, 118, 50, 112),
    pendulummatron=(145, 141, 71, 135),
    epochengine=(149, 130, 69, 124),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('orbitseer',)
PALETTE = PALETTE[:] + [
    '#2a160d', '#6a3a1f', '#a85f2c', '#dc9148', '#f9cf8f',   # BRONZE
    '#0d3a38', '#1d6d68', '#3ba69a', '#7ad9c4', '#caf7e8',   # VERDIGRIS
    '#3c2a0e', '#7e5a14', '#c48f20', '#f0c540', '#fff0a6',   # BRASS
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
BRONZE = list(range(len(PALETTE) - 15, len(PALETTE) - 10))
VERD = list(range(len(PALETTE) - 10, len(PALETTE) - 5))
BRASS = list(range(len(PALETTE) - 5, len(PALETTE)))


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions). The first redo pass drew every kind at full
# size and looked 30-60% taller than the neighbouring zones in the game screenshot, so each kind is scaled at the paint
# call (positions, radii and stroke widths), which keeps every pixel crisp and the shading bands intact.
SCALE = dict(bronzemantis=.78, gearling=.88, orbitseer=.88, chronoguard=.86, pendulummatron=.9, epochengine=.82)


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.S = SCALE.get(kind, 1.)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx * self.S

    def pos(self, x, y):
        return round(self.cx + x * self.S), round(self.ay - y * self.S)

    def ellipse(self, x, y, rx, ry, col):
        super().ellipse(x, y, rx * self.S, ry * self.S, col)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width * self.S)))

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        super().ball(x, y, rx * self.S, ry * self.S, ramp, ang)


def curves(clip, n):
    """Explicit animation beats: ready, anticipate, wind-up, release, impact, follow, recoil, recover."""
    wind = [0, .48, 1, .35, 0, 0, .08, 0][n] if clip == 'attack' else 0
    strike = [0, 0, 0, .50, 1, .72, .28, 0][n] if clip == 'attack' else 0
    dead = sm(n / 7) if clip == 'die' else 0
    phase = n * math.pi / (3 if clip == 'idle' else 4)
    bob = math.sin(phase) * (1.2 if clip == 'idle' else 2 if clip == 'walk' else 0)
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    return wind, strike, dead, phase, bob, recoil


def plate(a, pts, ramp, k=.78):
    """A shaded polygon: dark rim, mid body, lit upper-left panel and a bright core, never a flat fill."""
    a.poly(pts, ramp[1], outline=ramp[0])
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    a.poly([(cx + (x - cx) * k - .8, cy + (y - cy) * k + .8) for x, y in pts], ramp[2])
    a.poly([(cx + (x - cx) * k * .55 - 1.6, cy + (y - cy) * k * .55 + 1.6) for x, y in pts], ramp[3])


def gear(a, x, y, r, ramp, angle=0., teeth=10, sy=1.):
    """A toothed cog drawn as shaded plate with a domed face and a dark hub; sy < 1 lays it flat on the ground."""
    pts = []
    n = teeth * 4
    for i in range(n):
        t = angle + i * 2 * math.pi / n
        rad = r if i % 4 in (0, 1) else r * .78
        pts.append((x + math.cos(t) * rad, y + math.sin(t) * rad * sy))
    plate(a, pts, ramp, .9)
    a.ball(x, y, r * .64, r * .64 * sy, ramp)
    a.ellipse(x, y, max(1.5, r * .2), max(1., r * .2 * sy), ramp[0])
    a.ellipse(x - .6, y + .6 * sy, max(1., r * .1), max(.8, r * .1 * sy), ramp[3])


def rod(a, p, q, ramp, w0, w1=None):
    """A solid shaded bar from p to q (thickness w0 -> w1, at least 4 px so it survives game scale)."""
    w1 = w0 if w1 is None else w1
    taper(a, [mixp(p, q, i / 6) for i in range(7)], ramp, max(4, w0), max(3, w1))


def dust(a, x, y, r, ramp=PEARL):
    a.ball(x, y, r, r * .8, ramp)


def shock(a, x, r, t):
    """A ground shockwave ring that grows and fades into smaller chips (t 0..1)."""
    a.line([(x - r * 1.5, 2), (x - r * .5, 6 + 5 * (1 - t)), (x + r * .5, 6 + 5 * (1 - t)), (x + r * 1.5, 2)], GOLD[4], 2)
    for i in range(5):
        dust(a, x + (i - 2) * r * .7, 4 + (i % 2) * 9 * t, 2.2, GOLD)


# ----------------------------------------------------------------------------------------------
# 1. Bronze Mantis
# ----------------------------------------------------------------------------------------------
def bronzemantis(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    a = Painter('bronzemantis', recoil + st * 6 - w * 5)
    sink = d * 30
    lean = st * 8 - w * 7
    # four walking legs: femurs rise to arched knees, tibias slant down to planted feet (far pair darker, offset)
    legs = [(-22, -44, -30, True, 0), (-2, 20, 10, True, math.pi), (-30, -56, -42, False, math.pi), (-12, 12, 2, False, 0)]
    for hx, kx, foot_x, far, offset in legs:  # diagonal pairs trot together, so two feet are always planted
        hy = 46 - sink * .8
        swing = math.sin(ph + offset) if clip == 'walk' else 0
        lift = max(0, swing) * 5
        fx = foot_x + swing * 6 + d * (-8 if foot_x < 0 else 9)
        knee = (mix(kx, fx + (-12 if foot_x < 0 else 12), d), mix(66 - sink * .2, 12 + far * 3, d))
        ramp = BRONZE if not far else [BRONZE[0], BRONZE[0], BRONZE[1], BRONZE[1], BRONZE[2]]
        a.limb([(hx, hy), knee, (fx, 2 + lift if not d else 2)], ramp, 5)
        foot(a, fx, lift, 4, 3, BRONZE)
    # abdomen: three tapering segments with a verdigris wing case and a clockwork cog
    base = 52 - sink * .75
    for cx, cy, rx, ry in ((-24, base + 2, 20, 16), (-44, base - 3 - d * 4, 16, 12), (-58, base - 9 - d * 6, 11, 8)):
        a.ball(cx - lean * .3, cy, rx, ry, BRONZE, ang=-.18 - d * .3)
    a.ball(-36 - lean * .3, base + 12, 38, 9, VERD, ang=-.16)
    a.line([(-70, base - 2), (-12, base + 14)], VERD[0], 1)
    gear(a, -22 - lean * .3, base + 5, 8, BRASS, ph * .15 + d * 2, 8)
    # prothorax neck from the shoulders up to the head
    hx = 24 + st * 10 - w * 12 + d * 12
    hy = mix(96 + bob * .4 + w * 12 - st * 14, 22, d)
    sh = (8 + lean * .4, mix(60 + bob * .3, 30, d))
    for px, py in bez(sh, (mix(sh[0], hx, .4) - 5, mix(sh[1], hy, .6)), (hx - 3, hy - 8), 7):
        a.ball(px, py, 9.5, 9.5, BRONZE)
    a.ball(sh[0], sh[1], 12, 12, BRONZE)

    # far raptorial leg first (darker), then head, then near leg
    def foreleg(far):
        base_sh = (sh[0] + 3 + far * -5, sh[1] + 5 + far * 3)
        idle_target = (38 + far * -6, 42 + bob * .3)
        wind_target = (4 + far * -8, 118 - sink)
        strike_target = (84 + far * -6, 16 - far * 2)
        target = mixp(mixp(idle_target, wind_target, w), strike_target, st)
        if d:
            target = mixp(target, (50 + far * -9, 6), d)
        elbow, hand = arm_ik(base_sh, target, 24, 44, bend=-1 if w > .45 else 1)
        ramp = BRONZE if not far else [BRONZE[0], BRONZE[0], BRONZE[1], BRONZE[1], BRONZE[2]]
        a.limb([base_sh, elbow], ramp, 8)
        # steel blade with spines along its inner edge
        pts = bez(elbow, mixp(elbow, hand, .5), hand, 6)
        taper(a, pts, PLATE if not far else [PLATE[0], PLATE[0], PLATE[1], PLATE[1], PLATE[2]], 9, 3)
        vx, vy = hand[0] - elbow[0], hand[1] - elbow[1]
        ln = math.hypot(vx, vy) or 1
        nx, ny = -vy / ln, vx / ln
        for i in range(1, 5):
            px, py = mixp(elbow, hand, i / 5)
            a.poly([(px, py), (px + nx * 9 + vx / ln * 4, py + ny * 9 + vy / ln * 4), (px + vx / ln * 8, py + vy / ln * 8)], PLATE[3], outline=PLATE[0])
        a.ball(elbow[0], elbow[1], 5, 5, BRASS)
        return hand
    foreleg(True)
    a.ball(hx, hy, 15, 12, BRONZE, ang=-.2)
    a.poly([(hx + 8, hy - 8), (hx + 19, hy - 11), (hx + 9, hy - 17)], BRONZE[2], outline=BRONZE[0])
    a.face(hx + 1, hy + 1, clip, n, .78, sep=6.5, pupil=TEAL[0])
    for sg in (-1, 1):
        ant = bez((hx + sg * 4, hy + 10), (hx + sg * 12 + 6, hy + 32 - d * 18), (hx + sg * 20 + 14, hy + 30 - d * 26), 8)
        a.line(ant, BRONZE[1], 2)
        a.ball(ant[-1][0], ant[-1][1], 3, 3, TEAL)
    hand = foreleg(False)
    if st > .4:
        trail = bez((hand[0] - 28, hand[1] + 36), (hand[0] - 14, hand[1] + 8), (hand[0] - 3, hand[1] + 1), 8)
        taper(a, trail, GOLD, 2, 7)
    if d > .2:
        a.line([(-40, base + 6), (-30, base - 2), (-34, base - 9), (-24, base - 14)], OUTLINE, 2)
        gear(a, -70 - d * 8, 6 + (1 - d) * 24, 7, BRASS, d * 6, 7, sy=.55 if d > .8 else 1.)
    return a


# ----------------------------------------------------------------------------------------------
# 2. Gearling
# ----------------------------------------------------------------------------------------------
def gearling(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    run = st if clip == 'attack' else 0
    a = Painter('gearling', recoil + run * 40 - w * 12)
    cy = mix(38 + bob * .6 + w * 8, 22, d)
    spin = (ph * .2 if clip in ('idle', 'walk') else (-w * 1.6 + n * .9 * (2 < n < 7)) + d * 1.2)
    # stubby legs and feet
    for sg in (-1, 1):
        lift = max(0, math.sin(ph + (sg < 0) * math.pi)) * 5 if clip == 'walk' else 0
        a.limb([(sg * 14, cy - 18), (sg * 17, 8 + lift)], PLATE, 7)
        foot(a, sg * 17, lift, 8, 4, PLATE)
    # the big copper rim gear: on death it breaks away and rolls forward lying flat
    gx = mix(0, 52, sm(d * 1.1)); gy = mix(cy, 13, sm(d * 1.2)); sy = mix(1, .38, sm(d * 1.2))
    gear(a, gx, gy, 34, BRONZE, spin, 10, sy)
    # winding key on the back: a stem with a two-lobed brass bow that turns
    ka = -ph * .3 if clip in ('idle', 'walk') else 0
    a.limb([(-28, cy + 4), (-40, cy + 9)], BRASS, 6)
    for sg in (-1, 1):
        a.ball(-42 + math.cos(ka) * 6 * sg, cy + 10 + math.sin(ka) * 6 * sg, 5, 5, BRASS)
    a.ball(0, cy, 24, 24, PLATE)
    a.ball(-8, cy + 12, 8, 6, PLATE)
    a.face(1, cy + 1, clip, n, .98, sep=7.2, pupil=TEAL[0])
    for sg in (-1, 1):
        ant = bez((sg * 7, cy + 22), (sg * 11, cy + 34), (sg * 8, cy + 42), 6)
        a.line(ant, BRASS[1], 3)
        a.ball(ant[-1][0], ant[-1][1] + 1, 4, 4, BRASS)
    if run > .15:
        for i in range(4):
            dust(a, -34 - i * 12 + (n % 2) * 3, 5 + (i % 2) * 7, 5 - i * .6)
    if d > .15:
        a.line([(-12, cy + 16), (-4, cy + 6), (-9, cy - 2), (3, cy - 10)], OUTLINE, 2)
        for i in range(3):
            dust(a, -44 + i * 14 + d * (i - 1) * 8, 4 + (1 - d) * (12 + i * 6), 4, BRONZE)
    return a


# ----------------------------------------------------------------------------------------------
# 3. Orbit Seer
# ----------------------------------------------------------------------------------------------
def orbitseer(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    a = Painter('orbitseer', recoil + st * 6 - w * 8)
    cy = mix(54 + bob * .8 + w * 7 - st * 2, 24, d)
    spin = ph * .5 if clip in ('idle', 'walk') else (-w * 1.5 + st * 2.4)
    ring_fall = sm(d * 1.2)

    def ring(rx, ry, tilt, y0):
        pts = []
        for j in range(33):
            t = j * math.pi / 16
            x, y = rot(math.cos(t) * rx, math.sin(t) * ry, tilt)
            pts.append((x, y0 + y, math.sin(t)))
        return pts

    def stroke(pts, front):
        run = []
        for x, y, s in pts + [(None, None, None)]:
            if x is not None and (s <= 0) == front:
                run.append((x, y))
                continue
            if len(run) > 1:
                a.line(run, BRASS[0], 5)
                a.line(run, BRASS[2], 3)
                if front:
                    a.line(run, BRASS[4], 1)
            run = []

    tilt2 = .5 * math.cos(spin if clip in ('idle', 'walk') else 0) * (1 - ring_fall)  # attack keeps the gyroscope tilt steady
    r1 = ring(46, 13 * (1 - ring_fall * .35), 0., cy - ring_fall * 20)
    r2 = ring(42, 13 * (1 - ring_fall * .35), tilt2 + .35, cy - ring_fall * 6)
    stroke(r1, False)
    stroke(r2, False)
    moons = []
    for j in range(4):
        t = spin + j * math.pi / 2
        moons.append((math.cos(t) * 46, cy - ring_fall * 20 + math.sin(t) * 13 * (1 - ring_fall * .35), math.sin(t), j))
    for x, y, s, j in moons:
        if s > 0:
            a.ball(mix(x, (-1) ** j * (50 + j * 4), d), mix(y, 8, d), 6, 6, VIOLET if j % 2 else BRASS)
    a.ball(0, cy, 33, 33, BLUE)
    a.ball(0, cy, 26, 26, PEARL)
    charge = w * (1 - st)
    a.eye(1 + st * 4, cy, clip, n, 2.4 + charge * .5, pupil=TEAL[0])
    a.ellipse(-25, cy - 11, 4, 2, BLUSH)
    a.ellipse(25, cy - 11, 4, 2, BLUSH)
    if charge > .25:
        a.ball(30, cy, 4 + charge * 10, 4 + charge * 10, TEAL)
        a.ball(30, cy, 2 + charge * 6, 2 + charge * 6, [WHITE] * 5)
    stroke(r1, True)
    stroke(r2, True)
    for x, y, s, j in moons:
        if s <= 0:
            a.ball(mix(x, (-1) ** j * (50 + j * 4), d), mix(y, 8, d), 6, 6, VIOLET if j % 2 else BRASS)
    if st > .2:
        length = 22 + 34 * min(1, st * 1.5)
        spread = 7 + st * 6
        x0 = 34
        for col, k in ((TEAL[2], 1.0), (TEAL[4], .7), (WHITE, .38)):
            a.poly([(x0, cy + 3 * k), (x0 + length, cy + spread * k), (x0 + length, cy - spread * k), (x0, cy - 3 * k)], col)
        a.ball(x0 + length, cy, 9 * st, 9 * st, TEAL)
    if d > .1:
        a.line([(-15, cy + 18), (-5, cy + 6), (-10, cy - 3), (4, cy - 17)], OUTLINE, 2)
    return a


# ----------------------------------------------------------------------------------------------
# 4. Chronoguard
# ----------------------------------------------------------------------------------------------
def chronoguard(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    a = Painter('chronoguard', recoil + st * 7 - w * 4)
    by = mix(56 + bob * .4 - w * 2, 26, d)
    biped_legs(a, PLATE, ph, clip, 13, 32 - d * 14, 9, 4, 8, st, w, d)
    a.ball(0, by, 22, 25, PLATE)
    plate(a, [(-14, by + 10), (14, by + 10), (16, by - 12), (0, by - 17), (-16, by - 12)], BLUE, .8)
    gear(a, 0, by - 1, 9, BRASS, ph * .1, 8)
    a.ball(0, by - 1, 4, 4, PEARL)
    a.line([(0, by - 1), (0, by + 4), (3, by + 5)], OUTLINE, 2)
    for sg in (-1, 1):
        a.ball(sg * 26, by + 15, 11, 9, PLATE)
        a.ball(sg * 26, by + 18, 7, 4, BLUE)
    # head: helm with a pale face window, plume and brass crest
    hy = by + 34 - d * 5 + w * 3 - st * 2
    a.ball(1, hy, 18, 17, PLATE)
    a.ball(7, hy - 1, 12, 10, PEARL)
    a.face(8, hy, clip, n, .82, sep=6.4, mouth=False, pupil=TEAL[0])
    plume = bez((1, hy + 15), (-6 - st * 4, hy + 32 + w * 8), (-18 - st * 6, hy + 28 - d * 24), 7)
    taper(a, plume, BRASS, 7, 2)
    a.poly([(-1, hy + 14), (4, hy + 26 + w * 2), (9, hy + 14)], BRASS[3], outline=BRASS[0])
    # shield on the back arm: rimmed, shaded and carried forward during the thrust
    sx = -33 + st * 12 + w * 3 + d * 10
    sy = mix(by + 4, 11, d)
    rim = [(sx - 15, sy + 12), (sx + 15, sy + 12), (sx + 15, sy - 4), (sx, sy - 22), (sx - 15, sy - 4)]
    if d > .6:
        rim = [(sx - 22, sy + 5), (sx + 22, sy + 5), (sx + 20, sy - 3), (sx, sy - 6), (sx - 20, sy - 3)]
    plate(a, rim, BRASS, .88)
    inner = [(sx + (x - sx) * .72, sy + (y - sy) * .72) for x, y in rim]
    plate(a, inner, BLUE, .8)
    if d < .6:
        gear(a, sx, sy - 3, 6, BRASS, 0, 8)
    # spear arm: draw back, thrust, recover
    hand = (mix(26, 8, w) + st * 20, mix(by + 2, by + 12, w) - st * 3)
    if d:
        hand = mixp(hand, (20, 12), d)
    elbow, hand = arm_ik((20, by + 10), hand, 17, 19, bend=-1)
    a.limb([(20, by + 10), elbow, hand], PLATE, 8)
    a.ball(*hand, 6, 6, PLATE)
    ang = mix(mix(1.1, 1.38, w), .02, st) * (1 - d) + d * -.1
    back, tip = 28, 46
    p0 = (hand[0] - math.cos(ang) * back, hand[1] - math.sin(ang) * back)
    p1 = (hand[0] + math.cos(ang) * tip, hand[1] + math.sin(ang) * tip)
    if d > .6:
        p0, p1 = (hand[0] - 8, 6), (hand[0] + 52, 5)
    rod(a, p0, p1, BRONZE, 5, 4)
    ux, uy = (p1[0] - p0[0]), (p1[1] - p0[1])
    ln = math.hypot(ux, uy) or 1
    ux, uy = ux / ln, uy / ln
    head = [(p1[0], p1[1]), (p1[0] - ux * 4 - uy * 7, p1[1] - uy * 4 + ux * 7), (p1[0] + ux * 17, p1[1] + uy * 17), (p1[0] - ux * 4 + uy * 7, p1[1] - uy * 4 - ux * 7)]
    plate(a, head, BRASS, .8)
    a.ball(*hand, 5, 5, PLATE)
    if st > .45:
        for i in range(3):
            dust(a, p1[0] + 6 + i * 5, p1[1] + (i - 1) * 6, 3, BRASS)
    if d > .15:
        a.line([(-12, by + 12), (-4, by + 2), (-8, by - 6), (4, by - 14)], OUTLINE, 2)
    return a


# ----------------------------------------------------------------------------------------------
# 5. Pendulum Matron
# ----------------------------------------------------------------------------------------------
def pendulummatron(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    a = Painter('pendulummatron', recoil + st * 5 - w * 5)
    waist = mix(52 + bob * .4, 18, d)
    # pleated gown: layered shaded bell, folds and a rolled hem
    hem = 34 + d * 12
    gown = [(-12, waist + 3), (12, waist + 3), (hem - 4, 7), (hem, 4), (0, 2), (-hem, 4), (-hem + 4, 7)]
    plate(a, gown, VIOLET, .84)
    for x in (-24, -14, -4, 8, 18):
        a.line([(x * .35, waist - 4), (x * (hem / 34.), 7)], VIOLET[0], 1)
    a.ball(0, 6, hem + 1, 6, VIOLET)
    a.ball(0, waist + 6, 15, 12, VIOLET)
    # clock-face brooch on the bodice
    a.ball(0, waist + 6, 6, 6, PEARL)
    a.line([(0, waist + 6), (0, waist + 10), (3, waist + 9)], OUTLINE, 1)
    hy = mix(waist + 28 + bob * .4 - w * 2 + st * 1, 16, d)
    for x, y, r in ((-9, 13, 8), (0, 17, 9), (9, 13, 8)):
        a.ball(x, hy + y, r, r * .9, PLATE)
    a.ball(0, hy, 17, 16, PEARL)
    a.face(1, hy, clip, n, .85, sep=6.5, pupil=VIOLET[0])
    # free arm
    a.limb([(12, waist + 10), (24, waist + 6), (28, waist + 12 - st * 4)], VIOLET, 7)
    a.ball(28, waist + 12 - st * 4, 5, 5, PEARL)
    # pendulum arm: chain from the hand, swung overhead then slammed forward
    sh = (-12, waist + 11)
    hand_t = mixp(mixp((-24, waist + 3), (-10, waist + 52), w), (16, waist + 14), st)
    if d:
        hand_t = mixp(hand_t, (-26, 10), d)
    elbow, hand = arm_ik(sh, hand_t, 18, 20, bend=1 if w < .6 else -1)
    a.limb([sh, elbow, hand], VIOLET, 7)
    a.ball(*hand, 5, 5, PEARL)
    sway = math.sin(ph) * .22 if clip in ('idle', 'walk') else 0
    ang = (mix(mix(sway, -2.55, w), 1.35, st) if clip == 'attack' else sway) + (d * .2)
    L = 44
    bob_pt = (hand[0] + math.sin(ang) * L, hand[1] - math.cos(ang) * L)
    bob_pt = (bob_pt[0], max(11, bob_pt[1]))
    if d:
        bob_pt = mixp(bob_pt, (-38, 11), d)
    for i in range(1, 9):
        px, py = mixp(hand, bob_pt, i / 9)
        a.ball(px, py, 2.4, 2.4, BRASS)
    a.line([hand, bob_pt], BRASS[1], 1)
    gear(a, bob_pt[0], bob_pt[1], 11, BRASS, st * 2.5 + w, 9)
    a.ball(bob_pt[0], bob_pt[1], 5, 5, PEARL)
    return a


# ----------------------------------------------------------------------------------------------
# 6. Epoch Engine
# ----------------------------------------------------------------------------------------------
def epochengine(clip, n):
    w, st, d, ph, bob, recoil = curves(clip, n)
    a = Painter('epochengine', recoil + st * 6 - w * 4)
    cy = mix(68 + bob * .6 + w * 4 - st * 8, 34, d)
    # piston legs ending in flat gear feet
    for sg in (-1, 1):
        lift = max(0, math.sin(ph + (sg < 0) * math.pi)) * 4 if clip == 'walk' else 0
        fx = sg * 30 + d * sg * 14
        a.limb([(sg * 22, cy - 22), (sg * 27 - d * sg * 4, mix(30, 18, d)), (fx, 8 + lift)], BRONZE, 10)
        foot(a, fx, lift, 11, 3, PLATE)
        gear(a, fx, 8 + lift * .5, 12, PLATE, ph * .12 * sg, 8, .55)
    # tall brass whistle stack with steam puffs
    a.limb([(-6, cy + 42), (-6, cy + 56)], BRASS, 8)
    a.ball(-6, cy + 58, 8, 5, BRASS)
    if d < .7:
        a.ball(-6 + (n % 3 - 1) * 3, cy + 66, 4.5, 4, PEARL)
    # rim gear and clock-face dome
    gear(a, 0, cy, 48, BRONZE, ph * .08 + d * .5 + st * .4, 12)
    a.ball(0, cy, 37, 37, PEARL)
    for i in range(12):
        t = i * math.pi / 6
        a.ellipse(math.cos(t) * 32, cy + math.sin(t) * 32, 2, 2, PLATE[1])
    a.face(0, cy + 3, clip, n, 1.1, sep=8.5, pupil=BROWN[0])
    a.ball(0, cy + 25, 4, 4, BRASS)
    # gear fists on thick shoulder arms
    for sg in (-1, 1):
        sh = (sg * 40, cy + 8)
        up = (sg * 50 + sg * st * 6, cy + 62)
        down = (sg * 54 + (sg > 0) * st * 14, 12)
        rest = (sg * 56, cy + 2)
        hand = mixp(rest, up, w)
        hand = mixp(hand, down, st)
        if d:
            hand = mixp(hand, (sg * 60, 14), d)
        elbow, hand = arm_ik(sh, hand, 30, 32, bend=-sg)
        a.limb([sh, elbow, hand], BRONZE, 10)
        gear(a, hand[0], hand[1], 15, PLATE, st * .8 + ph * .05, 8)
    if st > .45:
        for i in range(5):
            dust(a, 56 + i * 6 + (1 - st) * 4, 4 + ((i * 7) % 5) * 5 * st, 3 + (i % 2), GOLD if i % 2 else PEARL)
    if d > .12:
        a.line([(-22, cy + 28), (-8, cy + 12), (-16, cy - 2), (4, cy - 20), (-2, cy - 36)], OUTLINE, 2)
        for i in range(3):
            gear(a, -52 + i * 50 + d * (i - 1) * 10, 6 + (1 - d) * 40, 8, BRONZE, d * 5 + i, 8, .6 if d > .8 else 1.)
    return a


DRAW = {k: globals()[k] for k in KINDS}


STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in FLYING:
        # Flying Orbit Seer stays well above the ground in living clips and settles onto kay at the end of death.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and clip == 'die' and (n == 7 or int(rows.max()) > kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    else:
        # Grounded kinds rest their lowest pixel exactly on the anchor row in every living and death frame.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (clip == 'die' or int(rows.max()) != kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    problem = None
    low = int(np.nonzero(grid.any(axis=1))[0].max()) if grid.any() else -1
    if not grid.any() or grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any():
        problem = 'empty or touches the border'
    elif kind in FLYING:
        if clip != 'die' and low > kay - 12:
            problem = f'flying kind should hover well above anchor row {kay} (lowest row {low})'
        elif clip == 'die' and low > kay:
            problem = f'flying death frame {n} sinks below anchor row {kay} (lowest row {low})'
    elif low != kay:
        problem = f'lowest row {low} != anchor row {kay}'
    if problem:
        BAD.append((kind, clip, n, problem))
        assert not STRICT, (kind, clip, n, problem)
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def api_draw(sid, offset, data):
    for clip, grids in data.items():
        for n, grid in enumerate(grids):
            old.api('draw', dict(sprite_id=sid, frame=offset + n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    return offset


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX + kind + '_all' + os.environ.get('SOURCE_SUFFIX', '')  # a frame-size change needs a NEW source
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/orrery_slime_{kind}_raw.npz', **data[kind])
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(
            name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
            palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]
        ))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, api_draw(sid, 0, data[kind]), 'frames saved', flush=True)


def refresh():
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/orrery_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    meta = dict(frame=[W, H], anchor=[AX, AY], kinds=KINDS, clips={}, sprites=saved, tops={}, artStyle='greenmeadow-slime')
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = ASSETS / f'orrery_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    meta = json.loads(MANIFEST.read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'orrery_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    """Measure each kind's art on a scratch canvas: pass A (anchor x 96) gives the left reach, pass B (anchor x 40) the right."""
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW]:
        old_kf = KIND_FRAMES.get(kind)
        left = right = up = 0
        for axs in (96, 40):
            KIND_FRAMES[kind] = (192, 192, axs, 160)
            for clip, grids in frames(kind).items():
                for grid in grids:
                    ys, xs = np.nonzero(grid)
                    if not xs.size:
                        continue
                    assert (xs.min() > 0 if axs == 96 else xs.max() < 191) and ys.min() > 0, (kind, clip, 'scratch canvas clipped', axs)
                    if axs == 96:
                        left = max(left, axs - 2 - int(xs.min()) + 2)
                        up = max(up, 158 - int(ys.min()))
                    else:
                        right = max(right, int(xs.max()) - (axs - 2) + 2)
        print(f'{kind}: left {left} right {right} up {up}  ->  suggested ax {left+4}, w {left+4+right+5}, ay {up+4}, h {up+4+6}')
        if old_kf:
            KIND_FRAMES[kind] = old_kf
        else:
            del KIND_FRAMES[kind]


def preview():
    global STRICT
    STRICT = False
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
    for kind in only:
        kw, kh, _, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8 * kw * 2, 5 * (kh * 2 + 26)), '#221f33')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw * 2, kh * 2), Image.Resampling.NEAREST)
                sheet.paste(im, (n * kw * 2, row * (kh * 2 + 26)), im)
                sd.text((n * kw * 2 + 8, row * (kh * 2 + 26) + kh * 2 + 4), f'{clip} {n}', fill='white')
                gy = row * (kh * 2 + 26) + kay * 2 + 2
                sd.line([(n * kw * 2, gy), (n * kw * 2 + kw * 2, gy)], fill='#5c5284')
        sheet.save(OUT / f'preview-{kind}.png')
        print(OUT / f'preview-{kind}.png')
    print('Frame problems:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
