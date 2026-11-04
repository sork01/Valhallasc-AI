#!/usr/bin/env python3
"""The Tanglecrown (zone 22) enemy redo: six native PixelFlow sources with per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye-plus-blush face (the old Tanglecrown art
gave every kind googly round eyes). Each kind has its own face routine: a glaring slit eye above a row of heat pits and a
hinged fanged gape with a forked tongue (jadeanaconda), a snarling flat muzzle with narrowed tear-marked eyes and bared
canines under a crown of jade thorns (crownjaguar), a triangular head with long slanted smooth bulb eyes and a single
dark pseudopupil over crossed mandibles (orchidmantis), a masked narrow bat-like face with narrowed ringed eyes and
needle teeth (canopyglider), a sunken ember eye under an armoured brow ridge with interlocking teeth that show even
when the jaw is shut (poolcaiman), and deep-set glints under a heavy brow shelf over a jutting lower jaw with tusks
(drumgorilla). No blush anywhere. Effects are attached to the body, never loose glyphs. Shaded volume, eight distinct
attack frames (wind-up, strike, recovery) and eight distinct death frames per kind. The six enemies share
`tanglecrown.txt` with three NPCs (`tangle_warden`, `tangle_scholar`, `tangle_travel`): export merges only the six
enemy entries and never touches the NPCs. Original cel-shaded art: /media/raid/valhallasc-data/tanglecrown-slime-original-20261104
(`scripts/rollback_tanglecrown_art.py`).
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
    Painter as BasePainter, PALETTE as BASE_PALETTE, OUTLINE, WHITE, EYE_WHITE,
    BONE, PEARL, CRIMSON, CORAL, AMBER, GOLD, GREEN, TEAL, OLIVE, BROWN, PINK, VIOLET, PURPLE, AZURE, FUR, SLATE,
    mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)
from moonspore_slime_redraw import curves as _curves, plate, blob, fang, dust

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/tanglecrown-slime'
REGISTRY = ROOT / 'scripts/tanglecrown_slime_sources.txt'
PREFIX = 'valhallasc_tanglecrown_slime_style_'
KINDS = ['jadeanaconda', 'crownjaguar', 'orchidmantis', 'canopyglider', 'poolcaiman', 'drumgorilla']
NAMES = dict(zip(KINDS, ['The Jade Anaconda', 'The Crown Jaguar', 'Orchid Mantis', 'Canopy Glider', 'Blackwater Caiman', 'Drum Gorilla']))
VILLAGERS = ['tangle_warden', 'tangle_scholar', 'tangle_travel']
MANIFEST = ASSETS / 'tanglecrown.txt'
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    jadeanaconda=(143, 79, 47, 73),
    crownjaguar=(131, 62, 55, 56),
    orchidmantis=(136, 98, 93, 92),
    canopyglider=(94, 98, 46, 92),
    poolcaiman=(130, 38, 57, 32),
    drumgorilla=(143, 114, 90, 108),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('canopyglider',)
PALETTE = BASE_PALETTE[:] + [
    '#06241c', '#0f5a44', '#1f9566', '#58d08c', '#b8f5c8',   # JADE (anaconda scales, mantis, glider)
    '#3a1604', '#8a3e0c', '#d9791c', '#f5aa3c', '#ffdc8a',   # JAG (jaguar coat)
    '#0a0a10', '#22232c', '#454856', '#7b8094', '#b6bccc',   # INK (black rosettes, claws, gorilla fur)
    '#0a1a10', '#1d3a26', '#35603a', '#5b8c4c', '#9ac06c',   # BOG (caiman hide)
    '#3a0808', '#8a1010', '#d82020', '#ff5a3c', '#ffb09c',   # RED (tongue, ember eyes, drum paint)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
assert len(PALETTE) <= 256, 'palette exceeds the indexed limit'
_n = len(BASE_PALETTE)
JADE, JAG, INK, BOG, RED = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(5)]


def curves(clip, n):
    """The shared beats, with the walk phase offset so no two of the eight walk frames mirror each other exactly."""
    w, st, d, ph, bob, recoil = _curves(clip, n)
    if clip == 'walk':
        ph += .45
    return w, st, d, ph, bob, recoil


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions); judged on an in-game screenshot.
SCALE = dict(jadeanaconda=.95, crownjaguar=.92, orchidmantis=.92, canopyglider=.82, poolcaiman=.72, drumgorilla=.98)


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


def polar(x, y, ang, r):
    return x + math.cos(ang) * r, y + math.sin(ang) * r


def dying(clip, n, first=2):
    return (clip == 'die' and n >= first) or (clip == 'hurt' and n == 1)


def cross_eye(a, x, y, r=2.6):
    a.line([(x - r, y - r), (x + r, y + r)], OUTLINE, 2)
    a.line([(x - r, y + r), (x + r, y - r)], OUTLINE, 2)


def brow(a, x0, y0, x1, y1, thick, ramp):
    """A heavy angled brow slab from (x0, y0) to (x1, y1)."""
    a.poly([(x0, y0), (x1, y1), (x1, y1 - thick), (x0, y0 - thick * .7)], ramp[0])
    a.line([(x0, y0 - thick * .2), (x1, y1 - thick * .2)], ramp[1], 1)


def teeth(a, x0, x1, y, size, ramp=BONE, down=True, n=None):
    """A row of small triangular teeth between x0 and x1 hanging from (down) or rising from (not down) the line y."""
    n = n or max(2, int(abs(x1 - x0) / 2.6))
    for i in range(n):
        x = mix(x0, x1, (i + .5) / n)
        tip = y - size * (1 - .35 * (i % 2)) if down else y + size * (1 - .35 * (i % 2))
        a.poly([(x - 1.15, y), (x + 1.15, y), (x, tip)], ramp[4], outline=ramp[0])


class Rig:
    """Draw body-local parts rotated by phi (radians, counter-clockwise, y up) about a pivot, so a whole creature can tumble."""

    def __init__(self, a, px, py, phi, lift=0.):
        self.a, self.px, self.py, self.phi, self.lift = a, px, py, phi, lift

    def t(self, x, y):
        c, s = math.cos(self.phi), math.sin(self.phi)
        dx, dy = x - self.px, y - self.py
        return self.px + dx * c - dy * s, self.py + dx * s + dy * c + self.lift

    def ball(self, x, y, rx, ry, ramp, ang=0.):
        self.a.ball(*self.t(x, y), rx, ry, ramp, ang + self.phi)

    def ellipse(self, x, y, rx, ry, col):
        pts = [self.t(x + math.cos(k * .5236) * rx, y + math.sin(k * .5236) * ry) for k in range(12)]
        self.a.poly(pts, col)

    def poly(self, pts, col, outline=None):
        self.a.poly([self.t(*p) for p in pts], col, outline=outline)

    def line(self, pts, col, width=1):
        self.a.line([self.t(*p) for p in pts], col, width)

    def limb(self, pts, ramp, width=5):
        self.a.limb([self.t(*p) for p in pts], ramp, width)

    def taper(self, pts, ramp, w0, w1):
        taper(self.a, [self.t(*p) for p in pts], ramp, w0, w1)

    def fang(self, x, y, length, width, ang, ramp=BONE):
        fang(self.a, *self.t(x, y), length, width, ang + self.phi, ramp)



class HeadRig(Rig):
    """A Rig that also enlarges everything drawn through it by `hs` about the pivot: big, menacing heads on small bodies."""

    def __init__(self, a, px, py, hs=1.3, phi=0., lift=0., cx=None, cy=None):
        super().__init__(a, px, py, phi, lift)
        self.hs = hs
        self.cx, self.cy = (px if cx is None else cx), (py if cy is None else cy)    # the point the head is enlarged about

    def t(self, x, y):
        return Rig.t(self, self.cx + (x - self.cx) * self.hs, self.cy + (y - self.cy) * self.hs)

    def ball(self, x, y, rx, ry, ramp, ang=0.):
        Rig.ball(self, x, y, rx * self.hs, ry * self.hs, ramp, ang)

    def ellipse(self, x, y, rx, ry, col):
        Rig.ellipse(self, x, y, rx * self.hs, ry * self.hs, col)

    def fang(self, x, y, length, width, ang, ramp=BONE):
        Rig.fang(self, x, y, length * self.hs, width * self.hs, ang, ramp)

    def eyes_out(self, x, y, r=2.4):
        self.line([(x - r, y - r), (x + r, y + r)], OUTLINE, 2)
        self.line([(x - r, y + r), (x + r, y - r)], OUTLINE, 2)

# KINDS-START
# --- jadeanaconda
def snake_pts(p0, p1, p2, p3, k=14):
    """Cubic bezier through four points (the neck S-curve)."""
    out = []
    for i in range(k + 1):
        s = i / k
        u = 1 - s
        out.append((u**3 * p0[0] + 3 * u * u * s * p1[0] + 3 * u * s * s * p2[0] + s**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * s * p1[1] + 3 * u * s * s * p2[1] + s**3 * p3[1]))
    return out


def jadeanaconda(clip, n):
    """Elite jade anaconda: three heaped coils, a raised S-curved neck, a wedge head with a glaring slit eye under a dark
    brow scale, heat pits along the lip, a hinged fanged gape and a forked red tongue, gold crown spines."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('jadeanaconda', recoil * .6)
    slither = math.sin(ph) if clip == 'walk' else 0
    belly = [BONE[0], BONE[1], BONE[2], BONE[3], BONE[4]]
    # --- coils: three stacked flattened rings that spread out along the ground as it dies
    spread = sm(dn * 1.02)
    coils = [(0, 5.4, 29, 5.6), (3, 12.4, 25, 5.6), (-2, 19.2, 20, 5.2)]
    for k, (cx, cy, rx, ry) in enumerate(coils):
        cx += slither * 2.2 * (1 if k % 2 else -1)
        cy = mix(cy, 4.4, spread)
        rx = mix(rx, 33 - k * 4, spread)
        ry = mix(ry, 4.2, spread)
        cx = mix(cx, -4 + k * 9 - 6, spread)
        a.ball(cx, cy, rx, ry, JADE, .03)
        a.ball(cx + 1, cy - ry * .66, rx * .9, ry * .34, belly, 0)
        for j in range(-2, 3):                                    # black diamond saddles with a gold dot
            sx = cx + j * rx * .36
            a.poly([(sx - 3.2, cy + ry * .5), (sx, cy + ry * .95 + .8), (sx + 3.2, cy + ry * .5), (sx, cy - ry * .05)], INK[1])
            a.ellipse(sx, cy + ry * .5, 1, 1, AMBER[3])
    # --- neck: an S-curve rising from the top coil to the head
    lean = -w * 19 + st * 26
    top = (-2 + slither, 22 - spread * 17)
    hx = 17 + lean + 6 * math.sin(ph * .7) * (1 - dn) * (clip == 'idle')
    hy = 51 + bob * 1.2 + w * 9 - st * 33 + recoil
    if clip == 'attack':
        hx = mix(hx, 40, st)
        hy = mix(hy, 20, st)
    hx = mix(hx, 40, spread)
    hy = mix(hy, 7.5, spread)
    mid1 = (top[0] - 15 + w * -10 + dn * 8, mix(top[1] + 14, 8, spread))
    mid2 = (hx - 17 - st * 6, mix(hy - 15 + st * 6, 7, spread))
    neck = snake_pts(top, mid1, mid2, (hx - 4, hy - 1))
    for i in range(len(neck) - 1):
        t = i / (len(neck) - 1)
        wd = mix(9.8, 7.6, t)
        a.line([neck[i], neck[i + 1]], JADE[0], round(wd + 2))
    for i in range(len(neck) - 1):
        t = i / (len(neck) - 1)
        wd = mix(9.8, 7.6, t)
        a.line([neck[i], neck[i + 1]], JADE[2], round(wd))
        a.line([(neck[i][0] - 1.4, neck[i][1] + wd * .22), (neck[i + 1][0] - 1.4, neck[i + 1][1] + wd * .22)], JADE[3], 2)
        if i % 2 == 0 and i < len(neck) - 2:                      # belly bands down the front of the neck
            a.ellipse(neck[i][0] + 1.6, neck[i][1] - wd * .2, 1.2, 1.2, INK[1])
    # --- head, rotated along the neck's last segment
    p, q = neck[-3], neck[-1]
    phi = math.atan2(q[1] - p[1], q[0] - p[0])
    phi = mix(phi, -.45, .55) if not spread else mix(phi, -.05, spread)
    HS = 1.32

    class Head(Rig):
        def t(self, x, y):
            return Rig.t(self, hx + (x - hx) * HS, hy + (y - hy) * HS)

        def ball(self, x, y, rx, ry, ramp, ang=0.):
            Rig.ball(self, x, y, rx * HS, ry * HS, ramp, ang)

        def ellipse(self, x, y, rx, ry, col):
            Rig.ellipse(self, x, y, rx * HS, ry * HS, col)

        def fang(self, x, y, length, width, ang, ramp=BONE):
            Rig.fang(self, x, y, length * HS, width * HS, ang, ramp)

    r = Head(a, hx, hy, phi)
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    gape = (1.0 if open_ else (.45 if clip == 'attack' and n in (2, 6) else 0)) + dn * .6 + (.25 if clip == 'idle' and n == 4 else 0)
    g = gape * 7.5
    # lower jaw, hinged near the skull
    r.ball(hx + 12, hy - 4 - g, 9.4, 2.8, belly, -gape * .32)
    mouth_in = gape > .35
    if mouth_in:
        r.poly([(hx + 4, hy - 1.6), (hx + 22, hy - 1.2), (hx + 21, hy - 4.4 - g), (hx + 5, hy - 3.2)], RED[0])
        r.ellipse(hx + 12, hy - 3.2 - g * .6, 6.5, 1.6, RED[1])
    # tongue: out when open or flicking
    flick = (clip == 'idle' and n in (1, 4)) or (clip == 'walk' and n % 3 == 1) or (clip == 'attack' and n in (3, 4)) or dn > .5
    if flick:
        tl = 9 + st * 5 + dn * 9
        ty = hy - 2.4 - g * .5
        r.line([(hx + 20, ty), (hx + 20 + tl, ty - (3 if dn > .5 else 0))], RED[2], 2)
        r.line([(hx + 20 + tl, ty - (3 if dn > .5 else 0)), (hx + 23 + tl, ty + 1.8)], RED[2], 1)
        r.line([(hx + 20 + tl, ty - (3 if dn > .5 else 0)), (hx + 23 + tl, ty - 4.8)], RED[2], 1)
    r.ball(hx + 7, hy, 10.5, 6.8, JADE, .02)                       # skull
    r.ball(hx + 16.5, hy - .6, 7.4, 4.2, JADE, 0)                   # snout
    r.ball(hx + 17, hy - 2.6, 6, 1.6, belly, 0)                     # pale lip
    for k in range(3):                                               # heat pits along the lip
        r.ellipse(hx + 14.5 + k * 2.6, hy - 1.7, .8, .8, INK[0])
    r.ellipse(hx + 22, hy + .6, .9, .9, INK[0])                      # nostril
    for k, fx in enumerate((14.4, 18)):                              # hinged fangs
        ln = 3.2 + gape * 5.8
        r.fang(hx + fx, hy - 2.6, ln, 2.2, -math.pi / 2 - .12, BONE)
    for k in range(3):                                               # crown: gold spines on the skull
        r.poly([(hx + 1.4 + k * 3.2, hy + 5.4), (hx + .2 + k * 3.2, hy + 10.2 - k * .8), (hx + 3.6 + k * 3.2, hy + 5.8)], GOLD[3], outline=GOLD[1])
    ex, ey = hx + 10.6, hy + 2.6
    if dying(clip, n):
        r.line([(ex - 2, ey - 2), (ex + 2, ey + 2)], OUTLINE, 2)
        r.line([(ex - 2, ey + 2), (ex + 2, ey - 2)], OUTLINE, 2)
    else:
        r.ellipse(ex, ey, 3.7, 2.8, OUTLINE)
        r.ball(ex, ey, 2.9, 2.2, AMBER, 0)
        r.ellipse(ex + .4, ey, .8, 2.3, OUTLINE)                     # vertical slit pupil
        r.poly([(ex - 5, ey + 4.6), (ex + 5.4, ey + 1.2), (ex + 5.2, ey + 3.6), (ex - 3, ey + 6.8)], JADE[0])   # brow scale: always scowling
        r.line([(ex - 4, ey + 4.4), (ex + 4.6, ey + 2)], JADE[2], 1)
    return a

# --- crownjaguar
def paw(a, x, y, ramp, claws=0., size=1.):
    """A big cat paw: a ball with three claws that extend by `claws` (0..1)."""
    a.ball(x, y, 4.6 * size, 2.8 * size, ramp)
    for k in (-1, 0, 1):
        cl = 1.2 + claws * 3.8
        a.poly([(x + 3.2 * size + k * .2, y + k * 1.2 * size + .8), (x + 3.2 * size + cl + 2, y + k * 1.4 * size - claws * 1.2), (x + 3 * size, y + k * 1.2 * size - .7)], BONE[4], outline=BONE[1])


def crownjaguar(clip, n):
    """Elite crown jaguar: heavy black-rosetted gold cat with a flat snarling muzzle, narrowed tear-marked eyes under a
    scowling brow, bared canines and a crown of jade thorns between its round ears; crouches, pounces claws first."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 11 - w * 6 + recoil
    a = Painter('crownjaguar', lunge * .45)
    walk = clip == 'walk'
    sink = sm(dn * 1.25)                                     # collapse onto the belly
    cream = [JAG[1], JAG[3], JAG[4], BONE[3], BONE[4]]
    cs = mix(29 + bob * .5 - w * 10 + st * 1, 10, sink)       # shoulder height
    ch = mix(27 + bob * .4 + w * 2.6 - st * 3.5, 9, sink)     # hip height
    shx, hpx = 14 + st * 3, -16 - st * 2
    # tail: a thick curve that whips when attacking and lies limp when dead
    sw = math.sin(ph * 1.2) * 3 * (1 - dn)
    tail = bez((hpx - 8, ch + 1), (hpx - 24 - w * 4, ch + 5 + sw - sink * 5), (hpx - 28 - st * 6 - sink * 6, mix(ch + 19 + sw * 1.4 + st * 5, 3.5, sink)), 8)
    taper(a, tail, JAG, 7, 4)
    a.ball(tail[-1][0], tail[-1][1], 3.7, 3.7, [INK[0], INK[0], INK[1], INK[1], INK[2]])
    # legs: far pair first (darker), near pair after the body
    def leg(front, near, k):
        x0 = (shx - 1 if front else hpx + 2) + (0 if near else 6)
        sg = math.sin(ph + (math.pi if k % 2 else 0)) if walk else 0
        top = (x0, (cs if front else ch) - 2)
        foot_x = x0 + sg * 8 + (3 if front else -2)
        lift = max(0, sg) * 5
        foot_y = 2.8 + lift
        claws = 0.
        if clip == 'attack' and front:
            foot_x = x0 + 5 + st * 22 - w * 5
            foot_y = 2.8 + st * (cs - 1) * (.9 if near else .55) + w * 0
            claws = st
        if sink:
            foot_x = x0 + (12 if front else -10) * sink * (1 if near else .6) + foot_x * (1 - sink) * .5
            foot_y = 2.6 + (k % 2) * 1.2
        elbow, hand = arm_ik(top, (foot_x, foot_y + 1.6), 12.4, 12.4, -1 if front else 1)
        ramp = JAG if near else [JAG[0], JAG[0], JAG[1], JAG[2], JAG[2]]
        a.limb([top, elbow, (foot_x - 1, foot_y + 2.2)], ramp, 7.6 if front else 7.2)
        paw(a, foot_x + 1, foot_y, ramp, claws)
    for k, (front, near) in enumerate(((False, False), (True, False))):
        leg(front, near, k)
    # body: long barrel, deep chest, thick haunch, pale belly
    a.ball(0, (cs + ch) / 2, 25, 11, JAG, (cs - ch) * .01)
    a.ball(hpx + 2, ch + 1, 14, 12.4, JAG, 0)
    a.ball(shx - 1, cs + 1, 14.6, 13.4, JAG, 0)
    a.ball(1, (cs + ch) / 2 - 8.6, 21, 4, cream, 0)
    for (sx, sy) in ((-18, 5), (-8, 6.5), (3, 7), (-13, -2), (-2, -1), (9, 4), (15, 1), (-22, 0), (17, -7)):
        yy = (cs + ch) / 2 + sy - (0 if sy > -8 else 0)
        a.ellipse(sx, yy, 3, 2.5, INK[1])
        a.ellipse(sx + .2, yy, 1.4, 1.1, JAG[3])
    for k, (front, near) in enumerate(((False, True), (True, True))):
        leg(front, near, k + 1)
    # head, enlarged
    hx = shx + 13 + st * 12 - w * 4 - sink * 5
    hy = mix(cs + 6 - w * 4 - st * 4 + recoil * .2 + bob * .3, 6.2, sink)
    r = HeadRig(a, hx, hy, 1.34)
    if clip == 'attack' and 3 <= n <= 5:
        hy -= 1
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or (dn > .55)
    gape = 1. if open_ else (.3 if clip == 'attack' and n in (2, 6) else 0.)
    r.ball(hx - 8, hy - 3, 11, 9, JAG, 0)                          # thick neck/ruff
    # far ear then skull
    r.ball(hx + 1.6, hy + 10.6, 3.6, 4, [JAG[0], JAG[0], JAG[1], JAG[2], JAG[2]])
    r.ball(hx + 8, hy - 7.4 - gape * 6.5, 8.2, 2.9, cream, -gape * .3)   # lower jaw
    if open_:
        r.poly([(hx + 4, hy - 3), (hx + 17, hy - 2.6), (hx + 17, hy - 7 - gape * 6), (hx + 3, hy - 6.6)], RED[0])
        r.ellipse(hx + 11, hy - 6 - gape * 4, 4.6, 1.5, RED[1])
        for fx in (14.6,):                                         # lower canine
            r.fang(hx + fx, hy - 7.2 - gape * 5, 4.2, 2, math.pi / 2, BONE)
    r.ball(hx + 1.5, hy + .2, 11.6, 9.6, JAG, .04)                 # skull
    r.ball(hx + 10.6, hy - 2.4, 8.6, 5.8, JAG, 0)                  # broad flat muzzle
    r.ball(hx + 10, hy - 4.4, 7, 2.6, cream, 0)
    r.ellipse(hx + 18, hy - .4, 2.4, 1.9, INK[0])                  # nose pad
    r.ellipse(hx + 17.4, hy + .2, .8, .6, CORAL[2])
    for k in range(3):                                              # wrinkled snarl lines over the nose
        r.line([(hx + 11.5 + k * 2, hy + 2.2 - k * .3), (hx + 13.4 + k * 2, hy + 3.7 - k * .3)], JAG[0], 1)
    for k in range(4):                                              # whisker spots
        r.ellipse(hx + 12 + (k % 2) * 3, hy - 2.4 - (k // 2) * 1.4, .55, .55, INK[1])
    r.fang(hx + 14.8, hy - 5.4, 5.2 + gape * 1.2, 2.4, -math.pi / 2, BONE)    # bared upper canines, always
    r.fang(hx + 11.4, hy - 5.1, 3.4, 1.9, -math.pi / 2, BONE)
    # near ear with a pale spot, and the jade thorn crown
    r.ball(hx - 4.2, hy + 10, 4.6, 4.8, JAG)
    r.ellipse(hx - 3.4, hy + 10, 1.8, 2.1, INK[1])
    r.ellipse(hx - 6, hy + 12.2, .9, .9, BONE[4])
    r.line([(hx - 1, hy + 9.2), (hx + 8, hy + 7.6)], GOLD[3], 2)
    for k in range(4):
        bx = hx - .6 + k * 2.9
        by = hy + 9.2 - k * .4
        r.poly([(bx - 1.4, by), (bx + .1 - k * .4, by + 7.2 + (1 if k in (1, 2) else 0)), (bx + 1.8, by)], JADE[2], outline=JADE[0])
        r.line([(bx, by + 1), (bx - .2, by + 5)], JADE[4], 1)
    # eye: a narrow glaring almond with a heavy scowling brow and a black tear mark
    ex, ey = hx + 6.6, hy + 2.6
    if dying(clip, n):
        r.eyes_out(ex, ey, 2.4)
    else:
        r.ellipse(ex + .6, ey + .2, 6.4, 4.6, JAG[1])                     # a dark mask so the eye pops
        r.poly([(ex - 4.6, ey + .2), (ex, ey + 3), (ex + 4.8, ey + 2), (ex + 4.2, ey - 1.4), (ex - .4, ey - 2.6)], OUTLINE)
        r.poly([(ex - 3.7, ey + .2), (ex, ey + 2.2), (ex + 3.9, ey + 1.4), (ex + 3.4, ey - 1), (ex - .2, ey - 1.9)], JADE[4])
        r.poly([(ex - 1.8, ey + .4), (ex + .8, ey + 1.7), (ex + 2.2, ey + .2), (ex + .6, ey - 1)], JADE[3])
        r.ellipse(ex + .8, ey + .1, 1.1, 1.3, OUTLINE)
        r.poly([(ex - 5, ey + 5.6), (ex + 5.6, ey + 1.2), (ex + 5.6, ey + 3.2), (ex - 4, ey + 7.6)], INK[1])
    r.line([(ex + .6, ey - 2), (ex + 2.4, ey - 7.6)], INK[1], 2)
    return a

# --- orchidmantis
def petal(r, x, y, ang, length, wid, ramp, vein=None):
    """A leaf/petal blade rooted at (x, y), pointing along ang, with a midrib; every part attached to the body."""
    c, s = math.cos(ang), math.sin(ang)
    nx, ny = -s, c
    pts = [(x, y), (x + c * length * .45 + nx * wid, y + s * length * .45 + ny * wid), (x + c * length, y + s * length),
           (x + c * length * .45 - nx * wid * .8, y + s * length * .45 - ny * wid * .8)]
    r.poly(pts, ramp[2], outline=ramp[0])
    r.poly([(x + c * 1.5, y + s * 1.5), (x + c * length * .45 + nx * wid * .45, y + s * length * .45 + ny * wid * .45),
            (x + c * length * .85, y + s * length * .85), (x + c * length * .4, y + s * length * .4)], ramp[3])
    r.line([(x, y), (x + c * length * .92, y + s * length * .92)], vein if vein is not None else ramp[1], 1)


def orchidmantis(clip, n):
    """Orchid mantis: an upright lime-green chitin body with pink/gold orchid-petal lobes and folded petal wings, a
    triangular scowling head with slanted smooth bulb eyes (one dark pseudopupil each) over crossed mandibles, and
    spined raptorial forelegs that cock up behind the head and snap down."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('orchidmantis', (st * 5 - w * 3 + recoil) * .5)
    fall = sm(dn * 1.1)
    phi = fall * 1.75                                        # tips over backwards (counter-clockwise), rigid
    curl = sm(dn * 1.4)                                      # legs pull in as the chitin buckles
    r = Rig(a, -2, 0, phi, 0)
    body = [JADE[0], JADE[1], JADE[2], JADE[3], JADE[4]]
    far = [JADE[0], JADE[0], JADE[1], JADE[2], JADE[2]]
    sway = math.sin(ph) * (1.2 if clip == 'idle' else 0)
    lean = w * -3.5 + st * 9 + recoil * .6
    walk = clip == 'walk'
    # --- petal wings folded behind (drawn first), pink/gold
    for k, (ang, ln, ramp) in enumerate(((2.35, 30, PINK), (2.0, 34, [GOLD[0], GOLD[1], GOLD[2], GOLD[3], GOLD[4]]), (1.62, 30, PINK), (2.7, 24, VIOLET))):
        sp = math.sin(ph * 1.3 + k) * .05 * (1 - curl)
        petal(r, -5, 46 + k * 1.5, ang + sp + fall * (-.35 + k * .2) + dn * .3, ln * (1 - curl * .1), 5.4, ramp)
    # --- four walking legs (far pair darker): long, knees splayed up and out, petal lobes at the knees
    legs = ((-8, -19, far, 0), (-3, 14, far, 1), (-6, -12, body, 1), (0, 19, body, 0))
    for k, (tx, fdx, ramp, par) in enumerate(legs):
        sg = math.sin(ph + (math.pi if par else 0)) if walk else 0
        lift = max(0, sg) * 5
        foot_ = (tx + fdx * (1 - curl * .8) + sg * 4, 1.6 + lift + curl * (6 + 4 * (k % 2)))
        top = (tx * .5, 40 - curl * 2)
        knee, foot_ = arm_ik(top, foot_, 21, 22, 1 if fdx > 0 else -1)
        r.limb([top, knee, foot_], ramp, 3.4)
        if ramp is body:
            petal(r, knee[0], knee[1], 1.0 if fdx > 0 else 2.15, 8, 2.8, PINK)
    # --- abdomen and thorax: a long jointed, tapered chitin body
    r.ball(-13, 33, 7.2, 16, body, -.62)
    for k in range(4):                                       # segment bands
        r.line([(-20 + k * 2.4, 27 + k * 4.5), (-14 + k * 2.4, 22 + k * 4.5)], JADE[1], 1)
    r.ball(-4, 44, 6.4, 7.6, body, -.2)
    r.ball(1.5 + lean * .3, 54, 5, 10, body, -.18 + lean * .015)       # prothorax: the long neck
    r.ball(-2, 40, 5.6, 5, [PINK[0], PINK[1], PINK[2], PINK[3], PINK[4]])
    # --- raptorial forelegs, spined: shoulder -> elbow -> claw
    sh = (3 + lean * .3, 56)
    if clip == 'attack':
        hand = (mix(mix(15, -7, w), 27, st), mix(mix(52, 84, w), 22, st))
    elif clip == 'walk':
        hand = (15 + math.sin(ph) * 1.5, 52)
    else:
        hand = (15, 52 + sway)
    hand = (mix(hand[0], 4, curl), mix(hand[1], 44, curl))
    for k, (shift, ramp) in enumerate(((-2.6, far), (0, body))):
        s2 = (sh[0] + shift, sh[1] - shift * .4)
        elbow, h2 = arm_ik(s2, (hand[0] + shift, hand[1] + shift * .3), 13, 15, -1 if clip != 'attack' or w > .5 else 1)
        r.limb([s2, elbow, h2], ramp, 4)
        if ramp is body:
            for t in (.3, .55, .8):                          # spine row along the forearm
                px, py = mixp(elbow, h2, t)
                nx, ny = h2[1] - elbow[1], -(h2[0] - elbow[0])
                ln = math.hypot(nx, ny) or 1
                r.poly([(px, py), (px + nx / ln * 4.4 + (h2[0] - elbow[0]) * .06, py + ny / ln * 4.4), (px + (h2[0] - elbow[0]) * .12, py + (h2[1] - elbow[1]) * .12)], BONE[4], outline=BONE[0])
            r.poly([(h2[0], h2[1]), (h2[0] + 6, h2[1] - 1.6), (h2[0] + 1.6, h2[1] - 4)], BONE[3], outline=BONE[0])
    # --- head: a big wide triangle, long slanted bulb eyes on its top corners under angry ridges
    k = 1.32
    hx, hy = 5 + lean + st * 3, 68 + bob * .6 - curl * 4

    def H(dx, dy):
        return hx + dx * k, hy + dy * k
    r.poly([H(-10, 4.4), H(10, 4.4), H(3.5, -9), H(-3.5, -9)], JADE[2], outline=JADE[0])
    r.poly([H(-8, 3.6), H(6, 3.6), H(2, -7)], JADE[3])
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or dn > .6
    gp = 2.6 if open_ else .6
    for sd in (-1, 1):                                       # crossed mandibles
        r.poly([H(sd * 1.2, -7.2), H(sd * (3.2 + gp), -12.2), H(sd * (1.6 + gp * .6), -6.4)], BONE[4], outline=BONE[0])
    for sd in (-1, 1):                                       # long antennae with a tiny gold bulb
        r.line([H(sd * 5, 4.4), H(sd * 10 + sway, 15 - dn * 4), H(sd * 14 + sway * 1.5 + dn * 3 * sd, 18 - dn * 9)], JADE[0], 1)
        r.ellipse(*H(sd * 14 + sway * 1.5 + dn * 3 * sd, 18 - dn * 9), 1.2, 1.2, GOLD[3])
    for sd in (-1, 1):
        ex, ey = H(sd * 7.2, 1.2)
        if dying(clip, n):
            r.line([(ex - 2.4, ey - 3), (ex + 2.4, ey + 3)], OUTLINE, 2)
            r.line([(ex - 2.4, ey + 3), (ex + 2.4, ey - 3)], OUTLINE, 2)
        else:
            tilt = sd * .5
            r.ball(ex, ey, 4.4 * k, 7 * k, [VIOLET[0], VIOLET[0], VIOLET[1], PINK[2], PINK[3]], tilt)        # glossy bulb, slanted outward
            r.ball(ex, ey + 1, 2.8 * k, 4.4 * k, [VIOLET[0], VIOLET[0], VIOLET[1], VIOLET[2], VIOLET[2]], tilt)
            r.ellipse(ex + sd * .3, ey - .6, 1.2 * k, 2.1 * k, OUTLINE)                                          # the single dark pseudopupil
            r.line([(ex - sd * 2.2, ey + 4.6), (ex - sd * .8, ey + 6)], WHITE, 1)                              # a hot glint
        r.poly([H(sd * 2.2, 5.6), H(sd * 12.4, 9.4), H(sd * 12.8, 7), H(sd * 3.4, 3.4)], JADE[0])            # ridge slants down to the nose: always scowling
    return a

# --- canopyglider
def canopyglider(clip, n):
    """Canopy glider: a hovering gliding predator with a teal fur body, tan membranes stretched between wrist and ankle
    and a ringed brush tail; a narrow bat-like face with a black mask band, glaring narrowed eyes, tall ears and
    needle teeth. It climbs and tucks, then dives claws-first; its membranes crumple and it tumbles to the ground."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.05)
    flap = math.sin(ph * 1.35) * (1 - fall) * (1 if clip in ('walk', 'idle') else .4)
    pitch = w * .5 - st * .6 + recoil * .05 + math.sin(ph * .8) * .05 * (1 - fall) + fall * 3.0
    lift = 6 + bob * 1.3 - st * 3 + w * 3 - fall * 44
    a = Painter('canopyglider', st * 6 - w * 4 + recoil * .5)
    r = Rig(a, 0, 58, pitch, lift)
    fur = [TEAL[0], TEAL[1], TEAL[2], TEAL[3], TEAL[4]]
    belly = [TEAL[2], TEAL[3], BONE[2], BONE[3], BONE[4]]
    mem = [AMBER[0], BROWN[2], AMBER[1], AMBER[2], AMBER[3]]
    memfar = [AMBER[0], AMBER[0], BROWN[2], BROWN[3], BROWN[3]]
    tuck = max(w, fall)                                       # membranes draw in while tucking and dying
    wr = lambda x, y: (mix(x, 6, tuck * .8), mix(y, 50, tuck * .8))
    def membrane(sh, wrist, ankle, hip, ramp, sag):
        wrist, ankle = wr(*wrist), wr(*ankle)
        mid = mixp(wrist, ankle, .5)
        r.poly([sh, wrist, (mid[0] + 2, mid[1] - sag), ankle, hip], ramp[2], outline=ramp[0])
        r.poly([mixp(sh, wrist, .12), mixp(wrist, mid, .55), mixp(ankle, mid, .55), mixp(hip, ankle, .12)], ramp[3])
        for t in (.3, .55, .8):                              # dark ribs and a cream trailing edge
            r.line([mixp(sh, hip, .5), mixp(wrist, ankle, t)], ramp[0], 1)
        r.line([wrist, (mid[0] + 2, mid[1] - sag), ankle], BONE[3], 1)
    # far membrane (behind the body)
    membrane((2, 62), (32, 86 + flap * 12), (-30, 64 + flap * 6), (-4, 52), memfar, 5)
    # ringed brush tail, rooted at the rump
    sw = math.sin(ph) * 3
    tail = bez((-9, 52), (-30, 44 + sw - fall * 6), (-46 - st * 5, 58 + sw * 1.4 + w * 4 - fall * 14), 8)
    taper(a, [r.t(*p) for p in tail], fur, 8, 4)
    for t in (2, 4, 6):
        px, py = r.t(*tail[t])
        a.ellipse(px, py, 2, 2, INK[1])
    # hind legs
    for sd, ramp in ((-1, [fur[0], fur[0], fur[1], fur[2], fur[2]]), (1, fur)):
        r.limb([(-3, 50), (-8 + sd * 2, 41 - tuck * 4), (-16 + sd * 3 + st * 14 - w * 4, 37 - tuck * 6 - st * 4)], ramp, 3.6)
        for c in (-1, 0, 1):
            r.line([(-16 + sd * 3 + st * 14 - w * 4, 37 - tuck * 6 - st * 4), (-19 + sd * 3 + st * 15 - w * 4 - .4 * c, 35 - tuck * 6 - st * 4 + c)], BONE[4], 1)
    # body
    r.ball(0, 57, 9.4, 12.8, fur, -.18)
    r.ball(2.4, 55, 5.6, 9.4, belly, -.1)
    # near membrane and the arm that holds it out
    membrane((4, 60), (40 + st * 12, 62 + flap * 14 + st * -8), (-32, 36 + flap * 8), (-6, 48), mem, 8)
    r.limb([(5, 60), (20 + st * 6, 61 + flap * 6), (40 + st * 12, 62 + flap * 14 + st * -8)], fur, 3.6)
    hand = (40 + st * 12, 62 + flap * 14 + st * -8)
    for c in (-1, 0, 1):                                      # three hooked claws; they spread on the strike
        r.line([hand, (hand[0] + 4 + st * 3, hand[1] + c * 2.2 * (1 + st) - 1)], BONE[4], 1)
    # head
    hx, hy = 10 + st * 2, 70
    class Hd(Rig):
        def t(self, x, y):
            return Rig.t(self, hx + (x - hx) * 1.3, hy + (y - hy) * 1.3)
        def ball(self, x, y, rx, ry, ramp, ang=0.):
            Rig.ball(self, x, y, rx * 1.3, ry * 1.3, ramp, ang)
        def ellipse(self, x, y, rx, ry, col):
            Rig.ellipse(self, x, y, rx * 1.3, ry * 1.3, col)
    h = Hd(a, 0, 58, pitch, lift)
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or dn > .5
    for sd, col in ((-1, fur), (1, fur)):                      # tall pointed ears with dark linings
        h.poly([(hx + sd * 2.4 - 1.8, hy + 5), (hx + sd * 6.6 - .6, hy + 15), (hx + sd * 7 + 1.6, hy + 4.4)], col[1], outline=col[0])
        h.poly([(hx + sd * 3.6, hy + 5.4), (hx + sd * 6.4, hy + 11.8), (hx + sd * 6.6 + .6, hy + 5)], INK[1])
    h.ball(hx, hy, 9.4, 7.8, fur, .02)                         # skull
    h.ball(hx + 6, hy - 2.6, 5.8, 3.8, belly, 0)               # short muzzle
    h.ellipse(hx + 10.8, hy - 1.6, 1.3, 1.1, INK[0])           # nose
    gap = 2.4 if open_ else .4
    h.poly([(hx + 2.6, hy - 3), (hx + 11.4, hy - 3), (hx + 9, hy - 6.2 - gap), (hx + 3, hy - 5.6 - gap)], RED[0] if open_ else belly[1])
    for t in range(5):                                          # needle teeth
        x = hx + 3.6 + t * 1.8
        h.poly([(x - .7, hy - 3), (x + .7, hy - 3), (x, hy - 5.4 - gap * .5)], BONE[4])
    h.poly([(hx - 7, hy + 4.4), (hx + 10, hy + 3.6), (hx + 10.6, hy - .4), (hx - 6.4, hy - .6)], INK[1])    # black mask band
    ex, ey = hx + 4.8, hy + 2
    if dying(clip, n):
        h.line([(ex - 2, ey - 1.6), (ex + 2, ey + 1.6)], OUTLINE, 2)
        h.line([(ex - 2, ey + 1.6), (ex + 2, ey - 1.6)], OUTLINE, 2)
        h.line([(hx - 3.4, ey - 1.6), (hx + .6, ey + 1.6)], OUTLINE, 2)
    else:
        for exx, sz in ((hx + 4.8, 1), (hx - 2.4, .8)):
            h.poly([(exx - 3, ey - .6), (exx, ey + 1.8), (exx + 3, ey + .2), (exx + 2, ey - 1.6), (exx - 1, ey - 1.8)], GOLD[3])
            h.ellipse(exx + .6, ey - .1, .8, 1.3, OUTLINE)
            h.poly([(exx - 3.6, ey + 3.2), (exx + 3.4, ey + .8), (exx + 3.4, ey + 2.6), (exx - 2.6, ey + 4.6)], INK[0])   # glaring brow
    return a

# --- poolcaiman
class FlipRig(Rig):
    """A Rig that rolls the whole creature over its long axis: y about the pivot is scaled by cos(theta), so at pi/2 it is a
    thin line and at pi it is belly-up with its legs in the air."""

    def __init__(self, a, py, theta, hs=1.0, hx=0., hy=0.):
        super().__init__(a, 0, py, 0.)
        self.c, self.hs, self.hx, self.hy = math.cos(theta), hs, hx, hy

    def t(self, x, y):
        if self.hs != 1.:
            x, y = self.hx + (x - self.hx) * self.hs, self.hy + (y - self.hy) * self.hs
        return x, self.py + (y - self.py) * self.c

    def ball(self, x, y, rx, ry, ramp, ang=0.):
        px, py = self.t(x, y)
        s = self.hs
        self.a.ball(px, py, rx * s, max(1.6, ry * s * abs(self.c)), ramp, ang * (1 if self.c >= 0 else -1))

    def ellipse(self, x, y, rx, ry, col):
        px, py = self.t(x, y)
        self.a.ellipse(px, py, rx * self.hs, max(.8, ry * self.hs * abs(self.c)), col)

    def fang(self, x, y, length, width, ang, ramp=BONE):
        px, py = self.t(x, y)
        fang(self.a, px, py, length * self.hs, width * self.hs, ang if self.c >= 0 else -ang, ramp)


def poolcaiman(clip, n):
    """Blackwater caiman: a low, armoured bog-green croc with keeled back scutes and a thick keeled tail; its eye is a
    small ember glint sunk under a bony brow ridge on a raised turret, and its interlocking teeth show even when the jaw
    is shut. It rears the head back with the jaws agape, then snaps forward; it dies by rolling belly-up, legs in the air."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    roll = sm(dn * 1.12) * math.pi                            # a death roll over the long axis
    a = Painter('poolcaiman', st * 12 - w * 9 + recoil * .6)
    hs = 1.0
    r = FlipRig(a, 12, roll)
    walk = clip == 'walk'
    up = roll > math.pi / 2
    back = [BOG[0], BOG[1], BOG[2], BOG[3], BOG[4]]
    belly = [BOG[2], BOG[3], BOG[4], BONE[2], BONE[3]]
    lowgap = 1 + dn * 3
    # --- tail: a thick keeled whip
    sw = math.sin(ph * 1.2) * (3 if walk else 1.6) * (1 - dn) + st * -7 + w * 6
    tail = bez((-26, 12), (-42, 10 + sw), (-60 - st * 4, 8 + sw * 1.8 - dn * 3), 9)
    for i in range(len(tail) - 1):
        wd = mix(11, 2.6, i / (len(tail) - 1))
        r.line([tail[i], tail[i + 1]], BOG[0], round(wd + 2))
    for i in range(len(tail) - 1):
        wd = mix(11, 2.6, i / (len(tail) - 1))
        r.line([tail[i], tail[i + 1]], BOG[2], round(wd))
        r.line([(tail[i][0], tail[i][1] + wd * .25), (tail[i + 1][0], tail[i + 1][1] + wd * .25)], BOG[3], 1)
        if not up and i % 2 == 0:
            tx, ty = tail[i]
            r.poly([(tx - 1.2, ty + wd * .5), (tx + 1.2, ty + wd * .5 + 4.2), (tx + 3, ty + wd * .5)], BOG[4], outline=BOG[0])
    # --- four stubby legs, elbows out, big claws
    def legs(near):
      for k, (hx, shade) in enumerate(((-22, [BOG[0], BOG[0], BOG[1], BOG[2], BOG[2]]), (17, [BOG[0], BOG[0], BOG[1], BOG[2], BOG[2]]), (-14, back), (25, back))):
        if (k >= 2) != near:
            continue
        front = hx > 0
        sg = math.sin(ph + (math.pi if k % 2 else 0)) if walk else 0
        lift = max(0, sg) * 4
        foot_ = (hx + sg * 5 + (4 if front else -3), 1.6 + lift)
        if clip == 'attack' and front:
            foot_ = (hx + 5 + st * 8 - w * 3, 1.8 + st * 2)
        if roll > .5:                                            # legs kick up and curl in as it rolls
            foot_ = (hx + (5 if front else -5) * (1 - sm(roll / math.pi) * .6), mix(foot_[1], 22 + (k % 2) * 3, sm(roll / math.pi)))
        top = (hx, 9)
        elbow = (mix(top[0], foot_[0], .5) + (5 if front else -5), mix(top[1], foot_[1], .5) + (2 if not up else -1))
        r.limb([top, elbow, foot_], shade, 5.4)
        r.ball(foot_[0] + 1, foot_[1], 4.4, 2.1 if not up else 2.6, shade)
        for c in (-1, 0, 1):
            r.line([(foot_[0] + 3, foot_[1] + c * .9), (foot_[0] + 6.4, foot_[1] + c * 1.5 - (1 if not up else -1))], BONE[3], 1)
    legs(False)
    # --- barrel body
    r.ball(0, 13, 30, 10, back, .02)
    r.ball(1, 5.8, 26, 2.8, belly, 0)
    if not up:
        for k in range(-6, 7):                                    # keeled dorsal scutes
            x = k * 4.4
            top_y = 13 + 10 * math.sqrt(max(0, 1 - (x / 30) ** 2))
            r.poly([(x - 2, top_y - .4), (x, top_y + 3.6), (x + 2.2, top_y - .6)], BOG[4], outline=BOG[0])
        for k in range(-5, 6):                                    # armour plates and moss tufts
            r.ellipse(k * 5, 13.4 + (k % 2) * 2.4, 1.5, 1.2, BOG[1])
        for k, mx in enumerate((-17, 3, 19)):
            r.line([(mx, 22), (mx - 1.5, 26 + k % 2 * 2)], OLIVE[3], 1)
            r.line([(mx + 1, 22), (mx + 3, 25 + k % 2 * 2)], OLIVE[2], 1)
    else:
        for k in range(-5, 6):                                    # pale belly scutes
            r.line([(k * 5 - 2, 6.2), (k * 5 + 2, 9)], BONE[1], 1)
    legs(True)
    # --- head (enlarged)
    hx0 = 34 + st * 8 + w * -3 - dn * 3
    hy0 = 15 + bob * .3 + w * 9 - st * 6 + recoil * .2
    open_ = (clip == 'attack' and 2 <= n <= 4) or (clip == 'hurt' and n == 1) or dn > .35
    gape = (1. if open_ else (.35 if clip == 'attack' and n in (1, 5) else 0)) * (1 + (.2 if clip == 'attack' and n == 3 else 0))
    h = FlipRig(a, 12, roll, 1.22, hx0, hy0)
    hy = hy0
    g = gape * 9.6 + lowgap * .1
    h.ball(hx0 - 4, hy - 1, 11, 7.6, back, .03)                                         # neck
    h.ball(hx0 + 13.4, hy - 4.4 - g, 14, 3.1, belly, -gape * .2)                       # lower jaw
    for t in range(6):                                                                 # lower teeth poke up past the lip
        x = hx0 + 6.4 + t * 4.2
        h.poly([(x - 1, hy - 4.6 - g + gape * t * .3), (x + 1, hy - 4.6 - g + gape * t * .3), (x, hy - 2.6 - g + gape * t * .8)], BONE[4], outline=BONE[1])
    if open_:
        h.poly([(hx0 + 3, hy - 2.4), (hx0 + 27, hy - 1.8), (hx0 + 27, hy - 4.6 - g), (hx0 + 4, hy - 4)], RED[0])
        h.ellipse(hx0 + 17, hy - 3.8 - g * .55, 7, 1.4, RED[1])
    h.ball(hx0 + 2, hy + 1, 11.4, 8.4, back, .02)                                      # skull
    h.ball(hx0 + 17, hy - .6, 13, 5.2, back, .02)                                      # broad snout
    h.ball(hx0 + 16, hy - 3.2, 12, 2.4, [BOG[2], BOG[3], BOG[4], BONE[3], BONE[3]], 0)  # pale upper lip
    for t in range(7):                                                                 # upper teeth hang over the lower jaw even shut
        x = hx0 + 6.4 + t * 3.6
        h.poly([(x - 1.2, hy - 3.4), (x + 1.2, hy - 3.4), (x, hy - 5.6 - (t % 2) * 1.0)], BONE[4], outline=BONE[1])
    h.ball(hx0 + 29, hy + 1.2, 2.5, 2.3, back, 0)                                      # nostril bump
    h.ellipse(hx0 + 29.4, hy + 2, .8, .8, OUTLINE)
    for t in range(3):                                                                 # bony ridge down the snout
        h.poly([(hx0 + 13 + t * 4, hy + 4.2), (hx0 + 14.6 + t * 4, hy + 6.6), (hx0 + 16.6 + t * 4, hy + 4.4)], BOG[4], outline=BOG[0])
    # eye turret under an armoured brow, with a tiny ember glint
    ex, ey = hx0 + 6, hy + 8.4
    h.ball(ex, ey, 4.6, 3.4, back, 0)
    if dying(clip, n):
        h.line([(ex - 1.8, ey - 1.6), (ex + 1.8, ey + 1.6)], OUTLINE, 2)
        h.line([(ex - 1.8, ey + 1.6), (ex + 1.8, ey - 1.6)], OUTLINE, 2)
    else:
        h.ellipse(ex + .8, ey - .6, 2.4, 1.7, OUTLINE)
        h.ellipse(ex + 1, ey - .6, 1.7, 1.2, RED[3])
    h.poly([(ex - 5, ey + 2.2), (ex + 6, ey + .2), (ex + 6, ey + 2.8), (ex - 3.6, ey + 5)], BOG[0])
    h.line([(ex - 3.6, ey + 3.6), (ex + 5.4, ey + 1.8)], BOG[3], 1)
    return a

# --- drumgorilla
def drumgorilla(clip, n):
    """Drum gorilla: a hulking charcoal silverback with a silver saddle, a war drum slung at its belly and bone drumsticks;
    deep-set red glints under a heavy brow shelf, a flat flared nose and a jutting lower jaw with two upturned tusks.
    It hauls both sticks overhead and slams them down on the drum, and dies by toppling over backwards, the drum rolling off."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    phi = fall * 1.62
    lean = st * 7 - w * 5 + recoil * .5
    a = Painter('drumgorilla', lean * .4)
    px_ = -8
    r = Rig(a, px_, 0, phi, 0)
    fur = [INK[0], INK[0], INK[1], INK[1], INK[2]]
    lit = [INK[0], INK[2], INK[3], INK[3], INK[4]]
    far = [INK[0], INK[0], INK[0], INK[1], INK[1]]
    silver = [INK[2], INK[3], INK[4], BONE[3], BONE[4]]
    skin = [INK[0], INK[1], BROWN[0], BROWN[0], BROWN[1]]
    walk = clip == 'walk'
    sway = math.sin(ph) if walk else 0
    breathe = math.sin(ph) * (.8 if clip == 'idle' else 0) + (bob * .6 if clip == 'attack' else 0)
    # legs: short, bowed, with broad feet
    for k, (hx, ramp) in enumerate(((-8, far), (8, lit))):
        sg = math.sin(ph + (math.pi if k else 0)) if walk else 0
        foot_ = (hx + sg * 7 + (3 if k else -3), 2.4 + max(0, sg) * 4)
        top = (hx * .6, 26)
        knee = (mix(top[0], foot_[0], .5) + (5 if k else -5), mix(top[1], foot_[1], .5) + 1)
        r.limb([top, knee, foot_], ramp, 9)
        r.ball(foot_[0] + 2, foot_[1], 6.8, 2.6 + (0 if not k else .2), ramp)
        for c in (-2, 0, 2):
            r.ellipse(foot_[0] + 7, foot_[1] + .2 + c * .3, 1, 1, ramp[0])
    # arms: far arm, torso, then the near arm and the drum
    sh_far, sh_near = (-6 + lean * .5, 53 + breathe), (4 + lean * .5, 52 + breathe)
    if clip == 'attack':
        tgt = lambda sd: ((mix(mix(14, -4, w), 22, st)) + sd * 5, mix(mix(30, 84, w), 31, st) + sd * (-3 if w > .5 else 1) * 3)
    elif clip == 'walk':
        tgt = lambda sd: (13 + sd * 6 + math.sin(ph + sd) * 4, 27 + math.cos(ph + sd) * 3)
    elif clip == 'idle':
        tgt = lambda sd: (13 + sd * 6, 28 + (1 + sd) * .6 * math.sin(ph * 2) * 2 + breathe)
    else:
        tgt = lambda sd: (13 + sd * 6, 28)
    def arm(sh, hand, ramp, bend):
        elbow, hnd = arm_ik(sh, hand, 21, 24, bend)
        r.limb([sh, elbow, hnd], ramp, 11.4)
        r.ball(hnd[0], hnd[1], 6.2, 5.8, ramp)
        # drumstick: a bone club gripped in the fist, pointing along the forearm so the club head lands where the fist goes
        dx, dy = hnd[0] - elbow[0], hnd[1] - elbow[1]
        ln = math.hypot(dx, dy) or 1
        dx, dy = dx / ln, dy / ln
        tip = (hnd[0] + dx * 13, hnd[1] + dy * 13)
        r.line([(hnd[0] - dx * 3, hnd[1] - dy * 3), tip], BONE[1], 3)
        r.line([(hnd[0] - dx * 3, hnd[1] - dy * 3), tip], BONE[3], 1)
        r.ball(tip[0], tip[1], 3.4, 3.4, BONE)
        return hnd
    if dn:
        tgt = lambda sd: (mix(13 + sd * 6, -14 + sd * 12, fall), mix(28, 40 + sd * 8, fall))
    arm(sh_far, tgt(-1), far, -1)
    # torso: a deep barrel chest, a hunched silver-saddled back
    r.ball(-3 + lean * .3, 42 + breathe * .5, 20, 21, fur, .25)
    r.ball(-9 + lean * .4, 52 + breathe, 17, 13, silver, .3)                  # silver saddle
    r.ball(8 + lean * .3, 38, 12, 15, skin, .1)                               # bare dark chest
    for k in range(5):                                                         # fur tufts on the silver saddle
        r.poly([(-18 + k * 5, 59 + breathe), (-16 + k * 5, 65 + breathe + (k % 2) * 2), (-14 + k * 5, 59 + breathe)], silver[3], outline=silver[0])
    # head: low between the shoulders, big and ugly
    hx = 12 + lean + st * 3 - fall * 3
    hy = 59 + breathe - w * 3 - st * 6 + recoil * .2 - fall * 2
    h = HeadRig(a, px_, 0, 1.3, phi, 0., hx, hy)
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1) or dn > .5
    g = 6 if open_ else 0
    h.ball(hx - 2, hy + 4.6, 10, 5.6, silver, 0)                               # sagittal crest dome
    h.ball(hx, hy, 11.2, 10, fur, 0)                                           # skull
    h.ball(hx + 6, hy - 1.4, 8.6, 7.4, skin, 0)                                # bare dark face
    h.ball(hx + 8.6, hy - 4.4, 6.6, 5, skin, 0)                                # muzzle
    h.ball(hx + 6, hy - 7.6 - g * .5, 9, 3.6 + g * .1, fur, -g * .03)          # heavy lower jaw, juts out
    if open_:
        h.poly([(hx + 2, hy - 6), (hx + 14, hy - 5.4), (hx + 13, hy - 8.2 - g), (hx + 3, hy - 8)], RED[0])
    for sd in (0, 1):                                                          # tusks
        h.fang(hx + 9.6 + sd * 4, hy - 7 - g * .5, 5.6, 2.4, math.pi / 2 + .2, BONE)
    h.ellipse(hx + 13.4, hy - 1.8, 2.8, 2.1, INK[0])                           # flared nostrils
    h.ellipse(hx + 11.6, hy - 1.4, 1.1, 1.3, INK[1])
    for c in (0, 1):
        h.line([(hx + 5 + c * 4, hy - 4.6), (hx + 6 + c * 4, hy - 6)], INK[0], 1)    # scowl creases
    # heavy brow shelf over deep-set glinting eyes
    h.poly([(hx + 1, hy + 6.6), (hx + 14, hy + 2.4), (hx + 14, hy + 5), (hx + 1, hy + 9)], INK[1])
    h.line([(hx + 1.6, hy + 8.4), (hx + 13, hy + 4.4)], INK[3], 1)
    ex, ey = hx + 8, hy + .2
    if dying(clip, n):
        h.line([(ex - 1.8, ey - 1.4), (ex + 1.8, ey + 1.4)], OUTLINE, 2)
        h.line([(ex - 1.8, ey + 1.4), (ex + 1.8, ey - 1.4)], OUTLINE, 2)
    else:
        h.ellipse(ex, ey, 3.4, 2.4, INK[0])
        h.ellipse(ex + .5, ey - .2, 1.5, 1.1, RED[3])
    # drum and the near arm go in front of the head, so the strike on the drum is always visible
    # war drum on a strap
    dxp = 20 + lean * .5 + fall * 14 + dn * 5
    dyp = mix(30, 8.6, fall)
    r.line([(dxp - 6, dyp + 13), (3, 58 + breathe)], BROWN[0], 3)
    r.line([(dxp - 6, dyp + 13), (3, 58 + breathe)], BROWN[2], 1)
    r.ball(dxp, dyp, 9.4, 10.6, [BROWN[0], BROWN[1], BROWN[2], BROWN[3], BROWN[4]], 0)
    r.line([(dxp - 8, dyp - 1.6), (dxp + 8, dyp - 1.6)], RED[2], 3)
    r.line([(dxp - 8, dyp + 3.4), (dxp + 8, dyp + 3.4)], RED[2], 2)
    r.ellipse(dxp, dyp + 9.6, 8.6, 2.9, BONE[1])
    r.ellipse(dxp, dyp + 10, 7.4, 2.2, BONE[3])
    hit = clip == 'attack' and n in (4, 5)
    if hit:                                                                    # the head of the drum is visibly struck
        r.line([(dxp - 7, dyp + 12), (dxp - 10, dyp + 15)], BONE[4], 1)
        r.line([(dxp + 7, dyp + 12), (dxp + 10, dyp + 15)], BONE[4], 1)
        r.line([(dxp, dyp + 13), (dxp, dyp + 17)], BONE[4], 1)
    arm(sh_near, tgt(1), lit, -1)
    return a

# KINDS-END

DRAW = {k: globals()[k] for k in KINDS if k in globals()}
STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in FLYING:
        # Flyers hover well above the ground while alive and settle onto kay at the end of death.
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
        np.savez_compressed(ROOT / f'scripts/tanglecrown_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/tanglecrown_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'tanglecrown_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    assert live['kinds'][-3:] == VILLAGERS, 'villager entries moved'
    villagers = {k: (live['sprites'][k], live['tops'][k]) for k in VILLAGERS}
    meta = json.loads(json.dumps(live))
    meta['artStyle'] = 'tanglecrown-slime'
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), clip
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for k in VILLAGERS:   # the villager NPCs must come out exactly as they went in
        assert (meta['sprites'][k], meta['tops'][k]) == villagers[k] and k not in (meta.get('kindFrames') or {})
    for kind, atlas in atlases.items():
        dest = atlas_path(kind)
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    saved = registry()
    for kind in KINDS:
        meta = json.loads(MANIFEST.read_text())
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(atlas_path(kind)).convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    """Measure each kind's art on a scratch canvas: pass A (anchor x 100) gives the left reach, pass B (anchor x 36) the right."""
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW and (len(sys.argv) < 3 or k in sys.argv[2:])]:
        old_kf = KIND_FRAMES.get(kind)
        left = right = up = 0
        for axs in (100, 36):
            KIND_FRAMES[kind] = (192, 192, axs, 186)
            for clip, grids in frames(kind).items():
                for grid in grids:
                    ys, xs = np.nonzero(grid)
                    if not xs.size:
                        continue
                    assert (xs.min() > 0 if axs == 100 else xs.max() < 191) and ys.min() > 0, (kind, clip, 'scratch canvas clipped', axs)
                    if axs == 100:
                        left = max(left, axs - 2 - int(xs.min()) + 2)
                        up = max(up, 184 - int(ys.min()))
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


def montage():
    """A compact review sheet in the scratchpad: idle, walk, hurt, 8 attack and 8 death frames at 1.5x, cropped to the art."""
    global STRICT
    STRICT = False
    dest = Path(os.environ.get('MONTAGE_DIR', OUT))
    dest.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
    for kind in only:
        data = frames(kind)
        picks = [('idle', 0), ('idle', 3), ('walk', 2), ('hurt', 1)] + [('attack', i) for i in range(8)] + [('die', i) for i in range(8)]
        ims = [rgba(data[c][i]) for c, i in picks]
        box = None
        for im in ims:
            b = im.getbbox()
            if b:
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        pad = 3
        box = (max(0, box[0] - pad), max(0, box[1] - pad), box[2] + pad, box[3] + pad)
        cw, ch = box[2] - box[0], box[3] - box[1]
        sc = float(os.environ.get('MONTAGE_SCALE', 1.5))
        cols = 5
        rows_n = (len(picks) + cols - 1) // cols
        sheet = Image.new('RGB', (int(cols * cw * sc), int(rows_n * (ch * sc + 14))), '#221f33')
        sd = ImageDraw.Draw(sheet)
        for k, ((c, i), im) in enumerate(zip(picks, ims)):
            x, y = int((k % cols) * cw * sc), int((k // cols) * (ch * sc + 14))
            tile = im.crop(box).resize((int(cw * sc), int(ch * sc)), Image.Resampling.NEAREST)
            sheet.paste(tile, (x, y), tile)
            sd.text((x + 3, y + int(ch * sc) + 1), f'{c} {i}', fill='white')
        sheet.save(dest / f'montage-{kind}.png')
        print(dest / f'montage-{kind}.png', sheet.size)
    print('Frame problems:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'montage': montage, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
