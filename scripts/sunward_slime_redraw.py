#!/usr/bin/env python3
"""Sunward Vale (zone 20, index 19 in map.txt) enemy redo: six native PixelFlow sources with per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye-plus-blush face. Each kind has its own
face routine: a bloodshot mad eye under a heavy brow over bared chisel teeth (meadowhare), hooked-pupil eyestalks over
a toothed rasp mouth (sunbacksnail), a narrow amber vertical slit over a bared muzzle (brushfox), small beady eyes
under a white brow stripe with a snarl (spadebadger), sunken ember pinpoints in a scarred honeycomb-dripping maw
(honeyjaw), and hollow ember slots cut into a woven wicker face under a ragged hat (wickerwarden). No blush anywhere.
Effects (drips, embers, straw) are attached to the body, never loose glyphs. Shaded volume, eight distinct attack
frames (wind-up, strike, recovery) and eight distinct death frames per kind. The six enemies share `sunward.txt` with
three villager NPCs (`sun_miller`, `sun_keeper`, `sun_travel`): export merges only the six enemy entries and never
touches the villagers. Original cel-shaded art: /media/raid/valhallasc-data/sunward-slime-original-20261104
(`scripts/rollback_sunward_art.py`).
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
from moonspore_slime_redraw import (
    PALETTE as BASE_PALETTE, plate, blob, fang, dust, curves,
)
from astral_slime_redraw import (
    Painter as BasePainter, OUTLINE, WHITE, EYE_WHITE,
    BONE, PEARL, CRIMSON, CORAL, AMBER, GOLD,
    mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/sunward-slime'
REGISTRY = ROOT / 'scripts/sunward_slime_sources.txt'
PREFIX = 'valhallasc_sunward_slime_style_'
KINDS = ['meadowhare', 'sunbacksnail', 'brushfox', 'spadebadger', 'honeyjaw', 'wickerwarden']
NAMES = dict(zip(KINDS, ['Meadow Hare', 'Sunback Snail', 'Brush Fox', 'Spade Badger', 'Honeyjaw', 'Wicker Warden']))
VILLAGERS = ['sun_miller', 'sun_keeper', 'sun_travel']
MANIFEST = ASSETS / 'sunward.txt'
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    meadowhare=(122, 78, 56, 72),
    sunbacksnail=(112, 65, 39, 59),
    brushfox=(124, 92, 56, 86),
    spadebadger=(122, 73, 36, 67),
    honeyjaw=(167, 113, 89, 107),
    wickerwarden=(130, 135, 41, 129),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ()
LEGS = {}   # spadebadger records each leg's ground x per frame, so the walk's diagonal gait is checked on geometry, not pixels
PALETTE = BASE_PALETTE[:] + [
    '#2a2224', '#5a4a48', '#8c7a70', '#bba898', '#e6d8c6',   # HARE (taupe-grey fur)
    '#3a1408', '#8a3612', '#d2681e', '#f0a04a', '#ffdca0',   # FOX (rust orange)
    '#102a14', '#2c5a24', '#5c9a34', '#98cc58', '#d4f090',   # SLUG (sickly green flesh)
    '#4a2a06', '#9a5c0c', '#dc9a1c', '#f6cc4c', '#fff0a0',   # SHELL (sun-gold spiral shell)
    '#14181c', '#363e44', '#68747a', '#9eaaac', '#d6dedc',   # BADGER (slate-grey pelt)
    '#06080a', '#181c20', '#2c3236', '#454d52', '#6a7478',   # CHAR (badger black and claws)
    '#2c1208', '#64300e', '#9a5a22', '#c88a46', '#ecc07a',   # BEAR (hive-bear brown)
    '#5a2c04', '#b8620a', '#f09a10', '#ffd038', '#fff6a4',   # HONEY (glossy honey)
    '#3a2410', '#7a5426', '#b88a46', '#dcb870', '#f6e2a4',   # WICKER (woven cane)
    '#5a3c0a', '#a47a14', '#d8b02c', '#f2d85a', '#fff6b0',   # STRAW
    '#2a0606', '#8a1608', '#e04a0c', '#ff9a24', '#fff2a6',   # EMBER (burning slots)
    '#2a1018', '#6a2a34', '#a04450', '#c87074', '#eca4a0',   # CLOTH (faded red hat band)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
assert len(PALETTE) <= 256, 'palette exceeds the indexed limit'
_n = len(BASE_PALETTE)
HARE, FOX, SLUG, SHELL, BADGER, CHAR, BEAR, HONEY, WICKER, STRAW, EMBER, CLOTH = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(12)]


_curves = curves


def curves(clip, n):
    """The shared beats, with the walk phase offset so no two of the eight walk frames mirror each other exactly."""
    w, st, d, ph, bob, recoil = _curves(clip, n)
    if clip == 'walk':
        ph += .45
    return w, st, d, ph, bob, recoil


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


# Art scale per kind (1.0 = the coordinates written in the draw functions); judged on an in-game screenshot.
SCALE = dict(meadowhare=.82, sunbacksnail=.8, brushfox=.72, spadebadger=.82, honeyjaw=.7, wickerwarden=.62)


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


# KINDS-START

def hare_ear(a, bx, by, ang, length, bend, ramp, notch=False):
    """A long taper ear from (bx, by) at angle ang, bending by `bend` over its length; a transparent notch can tear the tip."""
    pts = []
    for i in range(6):
        t = i / 5
        pts.append(polar(bx, by, ang + bend * t * t, length * t))
    taper(a, pts, ramp, 7, 3)
    inner = [polar(bx, by, ang + bend * (i / 5) ** 2, length * (i / 5) * .92) for i in range(1, 5)]
    a.line(inner, CORAL[1], 1)
    if notch:
        tx, ty = pts[-1]
        a.poly([(tx - 1, ty - 3), (tx + 1.5, ty - 1), (tx - 2, ty + 1.5)], 0)


def meadowhare(clip, n):
    """Grey-brown hunched hare: haunch ball, long flat hind foot, torn ears, one mad bloodshot eye under a heavy brow, bared chisel teeth."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 18 - w * 7 + recoil * 1.2
    a = Painter('meadowhare', lunge * .55)
    cy = mix(mix(25 + bob * .5, 16, w), 22, st)
    cy = mix(cy, 10.5, sm(dn * 1.7))
    far = [HARE[0], HARE[0], HARE[1], HARE[2], HARE[3]]
    swing = math.sin(ph) if clip == 'walk' else 0
    lift_h, lift_f = max(0, swing) * 7, max(0, -swing) * 7
    # hind leg: heel and a long flat foot; stretches back on the strike, stiff and straight when it dies
    heel = (-22 + swing * 5 - st * 9 + w * 3, 2.6 + lift_h + st * 9)
    toe = (heel[0] + 21 - st * 6, 1.8 + lift_h * 1.1 + st * 12)
    if dn:
        heel = mixp(heel, (-40, 9.5), sm(dn * 1.6))
        toe = mixp(toe, (-58, 12), sm(dn * 1.6))
    for shade, off in ((far, -5), (HARE, 0)):
        h0, t0 = (heel[0] + off * .4, heel[1]), (toe[0] + off * .4, toe[1])
        a.limb([(-10 + off * .3, cy - 4), mixp((-10, cy - 4), h0, .55), h0], shade, 7)
        a.limb([h0, t0], shade, 5)
        a.ball(t0[0] + 1, t0[1] + 1, 3.2, 2.2, CHAR)
    # front legs: thin, reaching; the strike throws both forward with spread claws
    for shade, off in ((far, -4), (HARE, 3)):
        sh = (13 + off, cy - 3)
        paw = (19 + off + (-swing if off > 0 else swing) * 4 + st * 20 - w * 2, 2.5 + (lift_f if off > 0 else lift_h * .6) + st * (cy - 2))
        if dn:
            paw = mixp(paw, (36 + off * 2, cy - 2 + off), sm(dn * 1.6))
        a.limb([sh, mixp(sh, paw, .5), paw], shade, 5)
        for k in (-1, 0, 1):
            a.line([(paw[0] + 1, paw[1]), (paw[0] + 4 + k, paw[1] + k * 1.6 - .4)], CHAR[0], 1)
    # body and haunch, pale chest
    a.ball(0, cy, 26, 16.5, HARE, .12)
    a.ball(-13, cy - 2, 15, 14, HARE, -.2)
    a.ellipse(15, cy - 6, 8, 6.5, BONE[3])
    a.line([(-6, cy + 12), (4, cy + 14), (14, cy + 11)], HARE[0], 1)
    a.ball(-30, cy + 3, 6.5, 6, [BONE[1], BONE[2], BONE[3], BONE[4], WHITE])
    # head: heavy skull, long muzzle, bared chisel teeth, a scar across the nose
    hx = 31 + st * 9 - w * 4 - dn * 8
    hy = mix(cy + 14 - st * 3 + w * 2, 8, sm(dn * 1.7))
    a.ball(mix(22, hx, .55), mix(cy + 6, hy, .6), 10, 9, HARE)
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    jaw = 2.5 + (6 if open_ else 0) + dn * 3
    a.ball(hx + 9, hy - 6 - jaw * .4, 9, 3.6, far, -.18 - jaw * .02)
    a.ball(hx, hy, 12.5, 10.5, HARE, .12)
    a.ball(hx + 11, hy - 3, 9.5, 6.4, [HARE[1], HARE[2], HARE[3], BONE[3], BONE[4]], -.12)
    a.ellipse(hx + 19.5, hy - 1, 2.4, 1.8, CHAR[0])
    a.line([(hx + 7, hy + 2), (hx + 16, hy - 6)], CRIMSON[2], 1)
    a.line([(hx + 10, hy + 3), (hx + 18, hy - 4)], CRIMSON[1], 1)
    lip_y = hy - 7.5 - jaw * .2
    a.poly([(hx + 11, lip_y), (hx + 21, lip_y + 2.5), (hx + 21, lip_y + 1), (hx + 11, lip_y - 1.2)], CHAR[0])
    for tx in (14.2, 17.6):
        a.poly([(hx + tx, lip_y + .8), (hx + tx + 3, lip_y + .8), (hx + tx + 3, lip_y - 8), (hx + tx, lip_y - 8.5)], BONE[4], outline=CHAR[0])
    # bloodshot mad eye under a heavy slanted brow
    ex, ey = hx + 4.5, hy + 3
    if dying(clip, n):
        cross_eye(a, ex, ey, 3)
    else:
        a.ellipse(ex, ey, 5.2, 5, OUTLINE)
        a.ellipse(ex, ey, 4, 3.8, BONE[4])
        for vx, vy in ((-3, 1.5), (-2.5, -2), (2.8, -1.5), (1, 3)):
            a.line([(ex + vx, ey + vy), (ex + vx * .3, ey + vy * .3)], CRIMSON[2], 1)
        a.ellipse(ex + 1.4 + st * .8, ey - .6, 1.6, 1.6, OUTLINE)
        a.ellipse(ex + 1.9 + st * .8, ey - .1, .7, .7, WHITE)
    brow(a, ex - 6, ey + 7, ex + 7, ey + 2.2, 3.4, HARE if False else CHAR)
    # long torn ears: upright with a twitch, laid flat on the wind-up and strike, drooping when it dies
    flat = max(w, st * .9)
    up = 1.42 - .09 * math.sin(ph * 1.5 + 1) if clip != 'walk' else 1.5 - .1 * swing
    ang = mix(up, 2.9, flat)
    ang = mix(ang, 3.45, sm(dn * 1.6))
    bend = mix(.35, .8, flat) + dn * .6
    bx, by = hx - 6, hy + 8
    hare_ear(a, bx - 3, by - 1, ang + .15, 30, bend, far)
    hare_ear(a, bx + 3, by + 1, ang - .08, 33, bend, HARE, notch=True)
    if dn > .6:
        for i in range(3):
            a.line([(hx + 8 + i * 3, hy - 15 - i), (hx + 5 + i * 3, hy - 17.5 - i)], BONE[3], 1)
    return a


def shell_spiral(a, cx, cy, r, turn, ramp, spin=0.):
    """Log-spiral ridge on a rigid shell; spin rotates the whole pattern (the shell tipping over)."""
    pts = []
    for i in range(26):
        t = i / 25
        ang = spin + turn * (1 - t) * 6.4
        rr = r * (.14 + .78 * (1 - t)) * (1 if i else .9)
        pts.append((cx + math.cos(ang) * rr * .96, cy + math.sin(ang) * rr * .96))
    a.line(pts, ramp[0], 2)
    a.line([(x - .8, y + .8) for x, y in pts[2:-4]], ramp[4], 1)


def sunbacksnail(clip, n):
    """Sun-gold spiral shell edged with thorns on a sickly green body; hooked-pupil eyestalks over a toothed rasp mouth."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 14 - w * 6 + recoil
    a = Painter('sunbacksnail', lunge * .4)
    wave = math.sin(ph) if clip == 'walk' else 0
    tip = sm(dn)                                    # shell tipping over
    retract = sm(max(0, dn - .1) * 1.1)                  # soft body pulling in
    flesh = [SLUG[0], SLUG[1], SLUG[2], SLUG[3], SLUG[4]]
    # foot: a long muscular slab with a ripple down its sole
    fl = 38 * (1 - retract * .8)
    a.ball(mix(2, -6, retract) + wave * 1.4, 6 - retract * 1.4, fl, 7 - retract * 1.5, flesh)
    for k in range(5):
        x0 = -fl * .7 + k * fl * .34 + wave * 2.5 * math.sin(k)
        a.line([(x0, 2), (x0 + 2, 4.6)], SLUG[1], 1)
    # neck and head, rearing high on the wind-up and driving forward on the strike
    reach = 30 * (1 - retract) + 4
    hx = 22 + reach * .45 + st * 24 - w * 10 + wave * 1.5
    hy = (17 + w * 20 - st * 5 + bob * .6) * (1 - retract) + 7 * retract
    neck = [(18, 7), mixp((18, 7), (hx, hy), .5), (hx, hy)]
    neck[1] = (neck[1][0] - 4, neck[1][1] + 2)
    taper(a, neck, flesh, 11, 9)
    a.ball(hx + 1, hy, 10.5, 8.5, flesh)
    # rasp mouth: a dark gape ringed with tiny teeth, widening on the strike
    gape = 3.2 + st * 5 + (3 if clip == 'hurt' and n == 1 else 0) + dn * 2
    a.ellipse(hx + 5, hy - 4.6, 6 + gape * .4, 2.4 + gape * .5, OUTLINE)
    for k in range(5):
        tx = hx + 1.2 + k * 2.2
        a.poly([(tx, hy - 4 + gape * .1), (tx + 1.2, hy - 4 + gape * .1), (tx + .6, hy - 6.6 - gape * .3)], BONE[4])
        a.poly([(tx, hy - 4.8 - gape * .5), (tx + 1.2, hy - 4.8 - gape * .5), (tx + .6, hy - 2.4 - gape * .2)], BONE[3])
    if st > .4:
        a.line([(hx + 4, hy - 4.5), (hx + 11 + st * 4, hy - 5 - st * 2)], CRIMSON[2], 2)
    # eyestalks: long, bent forward, a pale bulb with a hooked slit pupil and a heavy brow cap
    for k, (bx, ang, ln) in enumerate(((hx - 2, 1.5, 22), (hx + 6, 1.18, 25))):
        bend = (.35 - w * .5 + st * .5 + .12 * math.sin(ph * 1.3 + k * 2)) * (1 - retract * .6)
        ln *= 1 - retract * .9
        pts = [polar(bx, hy + 5, ang + bend * (i / 4) ** 2, ln * i / 4) for i in range(5)]
        taper(a, pts, flesh, 4.4, 3.2)
        ex, ey = pts[-1]
        if dying(clip, n) or retract > .5:
            a.ellipse(ex, ey, 4.4, 4.4, OUTLINE)
            a.ellipse(ex, ey, 3.2, 3.2, SLUG[2])
            cross_eye(a, ex, ey, 1.9)
            continue
        a.ellipse(ex, ey, 5.2, 5.2, OUTLINE)
        a.ellipse(ex, ey, 4.2, 4.2, [BONE[3], BONE[4]][k])
        a.ellipse(ex - .5, ey - .4, 3, 3, [GOLD[3], AMBER[3]][k])
        hook = [(ex + 2.6, ey + 2.4), (ex + 1.2, ey - 1.2), (ex - 1, ey - 2.6), (ex - 2.4, ey - 1.2)]
        a.line(hook, OUTLINE, 2)
        a.poly([(ex - 5.4, ey + 4.6), (ex + 5.4, ey + 1.2), (ex + 5.4, ey + 3.6), (ex - 5.4, ey + 7)], SLUG[0])
    # shell: rigid, never squashed. It tips forward and cracks when the snail dies.
    sx, sy = mix(-9, -2, tip) + st * 3 - w * 2, mix(27 + bob * .3, 22, tip)
    sr = 25
    a.ball(sx, sy, sr, sr * .93, SHELL, .0)
    a.ball(sx - 5, sy + 5, sr * .5, sr * .38, [SHELL[2], SHELL[3], SHELL[4], SHELL[4], WHITE], .5)
    shell_spiral(a, sx, sy - 1, sr, 1, SHELL, spin=-.5 - tip * 1.6)
    for k in range(9):                                   # thorns round the crown
        ang = math.pi * (.12 + k * .095) + tip * .9 * (1 if k < 5 else .4) + (-.2 if clip == 'attack' and 3 <= n <= 5 else 0)
        bx, by = polar(sx, sy, ang, sr * .92)
        fang(a, bx, by, 8.5 - abs(k - 4) * .5, 5, ang, [SHELL[0], SHELL[1], SHELL[2], BONE[3], BONE[4]])
    a.ellipse(sx + 13 - tip * 8, sy - 14 + tip * 5, 8, 5, SHELL[0])     # the dark aperture the body hides in
    cracks = max(0, (dn - .2) / .8)
    if cracks > 0:
        pts = [(sx - 4, sy + 21), (sx + 1, sy + 11), (sx - 5, sy + 4), (sx + 3, sy - 6), (sx + 12, sy - 11)]
        a.line(pts[:2 + int(cracks * 3.99)], OUTLINE, 2)
        a.line([(sx + 10, sy + 14), (sx + 6, sy + 7), (sx + 14, sy + 1)][:1 + int(cracks * 2.99)], OUTLINE, 2)
    if retract > .3:                                     # goo left behind, flat on the ground
        for k, gx in enumerate((-20, -8, 8, 22)):
            a.ellipse(gx * (.6 + dn * .5), 2, 5 * dn + 3 + retract * 2, 1.6 + (k % 2) * .6, SLUG[1])
    return a


def muscle(r, pts, rad0, rad1, ramp):
    """A shaded limb built from overlapping balls along a polyline, so it reads as a rounded cylinder, never a board."""
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in segs) or 1
    steps = max(3, int(total / (min(rad0, rad1) * .55)))
    for i in range(steps + 1):
        d = total * i / steps
        for p, q in segs:
            ln = math.hypot(q[0] - p[0], q[1] - p[1])
            if d <= ln + 1e-6 or (p, q) == segs[-1]:
                u = min(1, d / (ln or 1))
                rad = mix(rad0, rad1, i / steps)
                r.ball(p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u, rad, rad, ramp)
                break
            d -= ln




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


def brushfox(clip, n):
    """Rust-orange stalker: narrow amber vertical-slit eye under a heavy brow, bared fangs, black socks, a white-tipped brush; rolls onto its back when it dies."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 22 - w * 10 + recoil * 1.2
    a = Painter('brushfox', lunge * .5)
    phi = sm(dn * 1.15) * math.pi * .96
    lift = math.sin(min(1, dn * 1.3) * math.pi) * 9 * (dn > 0)
    crouch = w * 7
    cy = 38 + bob * .4 - crouch - st * 3
    r = Rig(a, 2, cy, phi, lift)
    swing = math.sin(ph) if clip == 'walk' else 0
    far = [FOX[0], FOX[0], FOX[1], FOX[2], FOX[3]]
    sock = [CHAR[0], CHAR[1], CHAR[2], CHAR[3], CHAR[4]]
    # tail: a thick brush with a white tip, lashing on the strike
    wag = math.sin(ph * 1.2) * 4 * (1 - dn) + st * 5 - w * 5
    tp = [(-24, cy + 2), (-38, cy + 7 + wag * .4), (-51, cy + 3 + wag)]
    for k, (t, sz) in enumerate(((.0, 7), (.3, 8.6), (.62, 9.4), (.9, 8.6))):
        x, y = bez(tp[0], tp[1], tp[2], 4)[int(t * 4 + .5)] if False else (mix(mix(tp[0][0], tp[1][0], t), mix(tp[1][0], tp[2][0], t), t), mix(mix(tp[0][1], tp[1][1], t), mix(tp[1][1], tp[2][1], t), t))
        r.ball(x, y, sz, sz * .72, FOX, -.2)
    r.ball(tp[2][0] - 7, tp[2][1] + .5, 7, 5.6, [BONE[1], BONE[2], BONE[3], BONE[4], WHITE], -.15)
    # four lean legs, trotting in diagonal pairs: rust above, black socks below
    for k, (hx, shade) in enumerate(((-18, far), (14, far), (-12, FOX), (20, FOX))):
        front = hx > 0
        sw = math.sin(ph + (math.pi if (k % 2) else 0)) if clip == 'walk' else 0
        lift_ = max(0, sw) * 6
        reach = 0
        hip = (hx, cy - 8)
        foot_ = (hx + sw * 8 + reach, 1.6 + lift_)
        if clip == 'attack':
            if front:
                foot_ = (hx + 6 + st * 26 - w * 4, 1.6 + st * (cy - 6 + k % 2 * 4) * .9 + w * 2) if st else (hx - 2 * w, 1.6)
            else:
                foot_ = (hx - 6 * w - st * 8, 1.6 + st * 3)
        if clip == 'hurt':
            foot_ = (hx - recoil, 1.6)
        knee = (mix(hip[0], foot_[0], .45) + (3 if front else -3), mix(hip[1], foot_[1], .5) + 1)
        r.limb([hip, knee, foot_], shade, 7)
        r.limb([mixp(knee, foot_, .35), foot_], sock, 5)
        r.ball(foot_[0] + 1.5, foot_[1] + 1.2, 3.4, 2.2, sock)
    # body: long barrel, cream chest and belly
    r.ball(0, cy, 28, 13, FOX, .06)
    r.ball(-15, cy + 1, 13, 12.4, FOX, 0)
    r.ellipse(15, cy - 7, 10, 5.4, BONE[3])
    r.ellipse(-4, cy - 9.4, 17, 3.2, BONE[2])
    for k in range(4):                                    # darker back stripe of coarse fur
        r.line([(-14 + k * 9, cy + 12.6), (-12 + k * 9, cy + 8)], FOX[0], 1)
    # neck, head: long snout with bared fangs, black ears
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    jaw = 3 + (10 if open_ else 0) + dn * 4
    hx = 37 + st * 9 - w * 6
    hy = cy + 13 - st * 5 - w * 2 + (clip == 'idle') * math.sin(ph) * .5
    r.limb([(20, cy + 3), mixp((20, cy + 3), (hx - 4, hy - 2), .55), (hx - 4, hy - 2)], FOX, 13)
    r.ball(hx - 1, hy + 6, 4, 4, FOX)
    r.ball(hx, hy, 12, 10.5, FOX, .05)
    for k in range(3):                                    # cheek ruff
        r.poly([(hx - 8, hy - 3 - k * 3), (hx - 16 - k, hy - 7 - k * 3), (hx - 6, hy - 6 - k * 3)], FOX[3], outline=FOX[0])
    r.poly([(hx + 6, hy - jaw * .1 - 5.5), (hx + 25, hy - 7.5 - jaw * .3), (hx + 24, hy - 10.5 - jaw), (hx + 9, hy - 10.5 - jaw * .75)], FOX[1], outline=CHAR[0])
    r.poly([(hx + 5, hy + 5), (hx + 26, hy - 5), (hx + 25, hy - 7.5 - jaw * .1), (hx + 5, hy - 6)], FOX[2], outline=CHAR[0])
    r.poly([(hx + 9, hy + 4), (hx + 24, hy - 4), (hx + 24, hy - 5.4), (hx + 9, hy + 1)], FOX[3])
    r.ball(hx + 25.5, hy - 5.5, 2.8, 2.6, CHAR)
    r.line([(hx + 10, hy - 7.5 - jaw * .4), (hx + 23, hy - 8.6 - jaw * .5)], OUTLINE, 1)
    for k, fx in enumerate((12.5, 19, 23.2)):             # bared fangs top and bottom
        r.poly([(hx + fx, hy - 6.4 - k * .6), (hx + fx + 3.2, hy - 6.9 - k * .5), (hx + fx + 1.2, hy - 13.5 + (k == 0) * 1.4 - jaw * .1 - k)], BONE[4], outline=CHAR[0])
    for k, fx in enumerate((14, 20)):
        r.poly([(hx + fx, hy - 8 - jaw * .8), (hx + fx + 2.6, hy - 8.4 - jaw * .8), (hx + fx + 1.2, hy - 3.8 - jaw * .6)], BONE[3], outline=CHAR[0])
    if dn > .55:
        r.poly([(hx + 14, hy - 9 - jaw * .8), (hx + 24, hy - 12 - jaw), (hx + 23, hy - 16 - jaw), (hx + 13, hy - 11 - jaw * .8)], CORAL[2], outline=CRIMSON[0])
    # ears: black-backed triangles, laid flat on the wind-up
    flat = max(w, st * .6)
    for k, (ex, sh) in enumerate(((hx - 8, far), (hx - 1, FOX))):
        lean = mix(.15, -1.2, flat)
        tip = (ex - 4 + lean * 12 + k * 3, hy + 22 - flat * 11)
        r.poly([(ex - 5, hy + 8), tip, (ex + 6, hy + 7)], sock[1], outline=CHAR[0])
        r.poly([(ex - 2.6, hy + 9), (tip[0] + .5, tip[1] - 3), (ex + 3, hy + 8.4)], CORAL[1])
    # the eye: a narrow amber slit with a vertical pupil under a heavy dark brow, scarred cheek
    ex, ey = hx + 7.2, hy + 3.2
    if dying(clip, n):
        r.line([(ex - 3, ey - 1.5), (ex + 3, ey + 1.5)], OUTLINE, 2)
        r.line([(ex - 3, ey + 1.5), (ex + 3, ey - 1.5)], OUTLINE, 2)
    else:
        r.poly([(ex - 5, ey - .5), (ex + 6, ey + 2.4), (ex + 5.4, ey - 1.2), (ex - 4, ey - 3.2)], OUTLINE)
        r.poly([(ex - 3.6, ey - .8), (ex + 4.6, ey + 1.6), (ex + 4.2, ey - .4), (ex - 3.2, ey - 2.4)], AMBER[3] if not (clip == 'attack' and 2 <= n <= 5) else WHITE)
        r.line([(ex + .5, ey + .6), (ex + .5, ey - 2.5)], OUTLINE, 1)
    r.poly([(ex - 7, ey + 5.6), (ex + 8, ey + 2), (ex + 8, ey + 4.6), (ex - 7, ey + 8.6)], CHAR[0])
    r.line([(hx + 1, hy - 4), (hx + 8, hy - 8)], CRIMSON[2], 1)
    return a


def spade_claws(a, x, y, ang, size, ramp=BONE):
    """A badger's digging hand: a dark scoop paw fanned with four long flat spade claws, tips along ang."""
    a.ball(x, y, 5.8 * size, 4.8 * size, CHAR, ang)
    for k in range(4):
        spread = (k - 1.5) * .26
        fang(a, x + math.cos(ang + spread) * 3 * size, y + math.sin(ang + spread) * 3 * size, 12.5 * size, 4.2 * size, ang + spread, ramp)


def spadebadger(clip, n):
    """Low slate-grey digger with a white-striped black mask, tiny hard eyes, a tusked snarl and four huge spade claws; face-plants when it dies."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 14 - w * 4 + recoil
    a = Painter('spadebadger', lunge * .5)
    fall = sm(dn)
    cy = (25 + bob * .5 + w * 6 - st * 3)
    cy = mix(cy, 12, fall)
    sw = math.sin(ph) if clip == 'walk' else 0
    tilt = (w * .22 - st * .2) + fall * -.28 + recoil * .01
    dark = [CHAR[0], CHAR[0], CHAR[1], CHAR[2], CHAR[3]]
    # hind legs first (behind)
    for k, (hx, shade) in enumerate(((-24, dark), (-13, BADGER))):
        s = -sw if k else sw
        hip = (hx, cy - 4)
        ft = (hx + s * 7 - fall * 6, 3.2 + max(0, s) * 5)
        if dn:
            ft = (hx - 8 * fall - k * 3, 3 + fall * 2 + k * 3)
        LEGS.setdefault((clip, n), {})[f'hind{k}'] = ft[0]
        muscle(a, [ft, mixp(hip, ft, .5), hip], 5, 6.4, shade)
        a.ball(ft[0] + 2, ft[1] + .6, 5, 3.2, CHAR)
    # body: a wide low barrel, grey mantle over a black belly
    a.ball(-2, cy, 31, 13.5, CHAR, tilt)
    a.ball(-3, cy + 2.5, 31, 12, BADGER, tilt)
    a.line([(-24, cy + 13), (-6, cy + 17), (14, cy + 14)], BADGER[4], 1)
    for k in range(6):                                    # coarse guard hairs
        a.line([(-24 + k * 9, cy + 14 - abs(k - 2) * .8), (-26 + k * 9, cy + 18 - abs(k - 2) * .8)], BADGER[3], 1)
    # head: low, thick wedge with a white blaze and black eye bands
    hx = 38 + st * 13 - w * 3 + fall * 4
    hy = mix(cy + 3 - w * 7 + st * -5 + math.sin(ph) * (.6 if clip == 'idle' else 0), 5.4, fall)
    a.limb([(22, cy + 3), mixp((22, cy + 3), (hx - 4, hy), .5), (hx - 4, hy)], BADGER, 17)
    a.ball(hx, hy, 16, 13, BADGER, .1)
    a.ball(hx + 16, hy - 3.5, 13.5, 8, [BADGER[1], BADGER[2], BADGER[3], BADGER[4], WHITE], -.2)
    plate(a, [(hx - 3, hy + 10), (hx + 9, hy + 6.5), (hx + 26, hy - 1), (hx + 24, hy - 3), (hx + 8, hy + 2), (hx - 4, hy + 5)], [BONE[1], BONE[2], BONE[3], BONE[4], WHITE], .55)
    a.poly([(hx - 5, hy + 2.8), (hx + 16, hy - 2.2), (hx + 15, hy - 7.2), (hx - 5, hy - 3.4)], CHAR[0])
    a.ellipse(hx + 26.5, hy - 4, 3.2, 2.6, OUTLINE)
    a.ellipse(hx + 26, hy - 3.6, 1.3, 1, WHITE)
    # snarl: heavy dark gape, short tusks and a row of teeth, jaw swinging open on the strike
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    jaw = 1.5 + (7 if open_ else 0) + fall * 3
    a.poly([(hx + 11, hy - 8.4 - jaw), (hx + 26, hy - 6.2), (hx + 26, hy - 8.6), (hx + 14, hy - 11.6 - jaw)], CHAR[0])
    a.poly([(hx + 12, hy - 7.2), (hx + 25, hy - 5), (hx + 25.5, hy - 7), (hx + 13, hy - 9.2 - jaw * .4)], OUTLINE)
    for tx in (14, 18, 22):
        a.poly([(hx + tx, hy - 6.4), (hx + tx + 2.6, hy - 6.8), (hx + tx + 1.2, hy - 11 - (tx == 22) * .5)], BONE[4], outline=CHAR[0])
    fang(a, hx + 16, hy - 9.4 - jaw, 7, 3.4, 1.35, BONE)
    fang(a, hx + 22, hy - 9 - jaw * .7, 5.6, 3, 1.4, BONE)
    # small hard eye under a thick white brow stripe
    ex, ey = hx + 9.5, hy + 1
    if dying(clip, n):
        cross_eye(a, ex, ey, 2.1)
    else:
        a.ellipse(ex, ey, 3.2, 2.7, OUTLINE)
        a.ellipse(ex + .5, ey - .2, 1.9, 1.7, CRIMSON[3] if (clip == 'attack' and 2 <= n <= 5) else AMBER[2])
        a.ellipse(ex + .9, ey - .2, .8, .8, OUTLINE)
    a.poly([(ex - 6.4, ey + 5.6), (ex + 7, ey + 1.6), (ex + 7, ey + 4.2), (ex - 6.4, ey + 8.6)], BONE[4], outline=CHAR[0])
    for dx in (-2, 2.5):
        a.poly([(hx + dx - 5, hy + 10), (hx + dx - 8, hy + 17 - fall * 5), (hx + dx - 1, hy + 11)], CHAR[1], outline=CHAR[0])   # ears
    # front legs and spade claws: they stride opposite the hind legs, rake overhead on the wind-up, slam on the strike
    for k, (sx0, shade) in enumerate(((16, dark), (25, BADGER))):
        s = sw if k else -sw
        sh = (sx0, cy - 2)
        paw = (sx0 + 5 + s * 9, 5 + max(0, -s) * 5.4 + (0 if clip == 'walk' else 0))
        if clip == 'attack':
            up = (sx0 + 8 - k * 4, cy + 34 + k * 3)
            down = (sx0 + 22 + k * 8, 5 - k)
            paw = mixp(mixp(paw, up, w), down, st)
        if dn:
            paw = mixp(paw, (sx0 + 22 + k * 7, 4 + k * 1.2), fall)
        LEGS.setdefault((clip, n), {})[f'front{k}'] = paw[0]
        el, hd = arm_ik(sh, paw, 17, 17, bend=-1 if paw[1] < cy else 1)
        muscle(a, [hd, el], 5.4, 6.2, shade)
        muscle(a, [el, sh], 6.2, 7.4, shade)
        pang = math.atan2(paw[1] - el[1], paw[0] - el[0]) if paw[1] > cy else (-.2 + st * .3 + s * .08)
        spade_claws(a, hd[0], hd[1], pang if clip == 'attack' and (w or st) else -.15 + s * .25, 1.0)
    if st > .45 or (clip == 'die' and n >= 5):            # dirt thrown off the claws, attached to the ground in front
        for i in range(5):
            a.ellipse(hx + 14 + i * 5 + st * 2 + dn * 3, 3 + (i % 3) * 1.8, 2.2 + dn * .9, 1.6 + dn * .5, [BADGER[1], BEAR[2], BEAR[3]][i % 3])
    return a



def comb(r, x, y, rx, ry, cells, seed=0):
    """A lump of honeycomb: a shaded plate with dark hexagonal cells, some capped in honey."""
    pts = [(x + math.cos(k * .7854 + .2) * rx * (1 + .12 * math.sin(k * 2.3 + seed)), y + math.sin(k * .7854 + .2) * ry) for k in range(8)]
    r.poly(pts, HONEY[1], outline=BEAR[0])
    r.poly([(x + (px - x) * .8 - 1, y + (py - y) * .8 + 1) for px, py in pts], HONEY[2])
    r.poly([(x + (px - x) * .5 - 2, y + (py - y) * .5 + 2) for px, py in pts], HONEY[3])
    for i in range(cells):
        cx = x + (((i * 5 + seed) % 7) - 3) * rx * .24
        cy = y + (((i * 3 + seed * 2) % 5) - 2) * ry * .3
        r.ellipse(cx, cy, 2.6, 2.3, BEAR[0] if (i + seed) % 3 else HONEY[0])
        if (i + seed) % 3 == 0:
            r.ellipse(cx - .5, cy + .4, 1.3, 1.1, HONEY[4])


def honey_string(r, x, y, length, sway, drop=2.8):
    """A drip hanging from (x, y): a thin amber strand ending in a swollen drop, always attached to what it drips from."""
    r.line([(x, y), (x + sway * .4, y - length * .5), (x + sway, y - length)], HONEY[2], 2)
    r.ball(x + sway, y - length - 1.4, drop, drop * 1.2, HONEY)


def honeyjaw(clip, n):
    """Hulking hive-bear: a honeycomb hive grown over its back, sunken ember eyes under a scarred brow, a hanging comb-toothed jaw trailing honey."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 20 - w * 14 + recoil * 1.4
    a = Painter('honeyjaw', lunge * .5)
    phi = sm(dn * 1.1) * 1.52
    lift = math.sin(min(1, dn * 1.2) * math.pi) * 6 * (dn > 0)
    r = Rig(a, -12, 2, phi, lift)
    sw = math.sin(ph) if clip == 'walk' else 0
    breath = math.sin(ph) * (.8 if clip == 'idle' else .4)
    lean = (st * 7 - w * 9) + recoil
    dark = [BEAR[0], BEAR[0], BEAR[1], BEAR[2], BEAR[3]]
    # legs: two thick pillars with big flat feet
    for k, (hx, shade) in enumerate(((-17, dark), (13, BEAR))):
        s = sw if k else -sw
        hip = (hx + lean * .3, 44)
        ft = (hx + s * 9 + (4 if st else 0) * (k * 2 - 1), 4 + max(0, s) * 7)
        knee = (mix(hip[0], ft[0], .5) + 5, 24)
        muscle(r, [ft, knee], 8, 9.6, shade)
        muscle(r, [knee, hip], 9.6, 11.5, shade)
        r.ball(ft[0] + 5, ft[1] + 1.5, 11, 5, dark if k == 0 else BEAR)
        for c in (-1, 0, 1):
            r.fang(ft[0] + 12, ft[1] + 1.5 + c * 2.6, 4, 2.6, 0 + c * .1, BONE)
    # hive on the back and shoulders: comb lumps with honey seams
    for (cx0, cy0, rx, ry, cells, seed) in ((-27, 76, 15, 16, 6, 1), (-20, 94, 14, 12, 5, 2), (-6, 100, 11, 8, 3, 3), (-33, 58, 10, 12, 4, 4)):
        comb(r, cx0 + lean * .5, cy0 + breath, rx, ry, cells, seed)
    # torso: pale belly over a heavy hunched mass
    r.ball(-2 + lean * .5, 60 + breath, 27, 28, BEAR, .1)
    r.ball(4 + lean * .6, 55 + breath, 18, 20, [BEAR[1], BEAR[2], BEAR[3], BEAR[3], BEAR[4]], .1)
    r.ball(8 + lean * .8, 78 + breath, 24, 15, BEAR, -.1)
    for k in range(6):                                    # matted fur and honey crust on the chest
        r.line([(-6 + k * 5 + lean * .6, 66 - k % 2 * 3 + breath), (-8 + k * 5 + lean * .6, 59 - k % 2 * 3 + breath)], BEAR[0], 1)
    r.ball(10 + lean * .6, 48 + breath, 6, 4.4, HONEY)
    # head, thrown back on the wind-up and out on the strike
    hx, hy = 24 + lean * 1.2 + st * 8, 94 + breath - w * 2 - st * 8
    open_ = (clip == 'attack' and 1 <= n <= 5) or (clip == 'hurt' and n == 1)
    gape = 7 + (14 if open_ else 0) + dn * 6
    r.limb([(8 + lean * .8, 78 + breath), (hx - 6, hy - 6)], BEAR, 18)
    # lower jaw: a heavy comb-honey slab hanging open, teeth, strands of honey
    jy = hy - 10 - gape
    r.ball(hx + 8, jy, 15, 7, [HONEY[0], HONEY[1], HONEY[2], HONEY[3], HONEY[4]], -.12)
    for cx0 in (-2, 7, 16):
        r.ellipse(hx + cx0, jy - .4, 2.5, 2.2, BEAR[0])
    for tx in (-1, 6, 13, 20):
        r.fang(hx + tx, jy + 3, 7.5, 3.8, math.pi / 2, BONE)
    r.ball(hx + 1, hy, 20, 16.5, BEAR, .1)
    r.ball(hx + 17, hy - 5.5, 15, 9.6, [BEAR[1], BEAR[2], BEAR[3], BONE[3], BONE[4]], -.18)
    r.ball(hx + 30, hy - 3, 4.6, 3.8, CHAR)
    for tx in (-1, 6, 13, 20):                           # top fangs
        r.fang(hx + tx + 2, hy - 11.4 - (tx == 20), 8.5 - abs(tx - 6) * .15, 4, -math.pi / 2, BONE)
    r.line([(hx + 5, hy + 4), (hx + 14, hy - 7)], CRIMSON[1], 2)                    # old scar
    r.line([(hx + 8, hy + 5), (hx + 17, hy - 4)], CRIMSON[2], 1)
    for k in range(3):                                   # drool strands off the fangs
        honey_string(r, hx + 4 + k * 8, jy + 4, 15 + k * 5 + math.sin(ph + k) * 3 * (clip == 'idle'), 2 - k, 2.5)
    # sunken eye under a scarred brow ridge: a dark socket with a lone ember pinpoint
    ex, ey = hx + 12, hy + 3
    r.poly([(ex - 9, ey + 10), (ex + 9, ey + 4.4), (ex + 9, ey + 8.2), (ex - 9, ey + 14)], BEAR[0])
    if dying(clip, n):
        r.line([(ex - 3, ey - 1.5), (ex + 3, ey + 1.5)], OUTLINE, 2)
        r.line([(ex - 3, ey + 1.5), (ex + 3, ey - 1.5)], OUTLINE, 2)
    else:
        r.ellipse(ex, ey, 7, 5.6, OUTLINE)
        r.ellipse(ex + .8, ey - .2, 2.6, 2.6, EMBER[3] if not (clip == 'attack' and 1 <= n <= 5) else EMBER[2])
        r.ellipse(ex + 1.2, ey + .1, 1, 1, EMBER[0])
    for dx in (-9, -1):                                  # torn ears
        r.ball(hx + dx, hy + 14, 5.4, 5, BEAR)
        r.poly([(hx + dx - 1, hy + 18), (hx + dx + 1.5, hy + 16), (hx + dx + 2, hy + 19)], 0)
    # arms: huge, claws raised overhead on the wind-up and hammered down on the strike
    for k, (sx0, shade) in enumerate(((-4, dark), (18, BEAR))):
        sh = (sx0 + lean * .8, 82 + breath)
        paw = (sx0 + 16 - sw * 6 * (1 if k else -1), 30 + max(0, sw) * 3)
        if clip == 'attack':
            up = (sx0 - 6 + k * 8, 140)
            down = (sx0 + 44 + k * 8, 6)
            paw = mixp(mixp(paw, up, w), down, st)
        if dn:
            paw = mixp(paw, (sx0 + 30 + k * 10, 40), sm(dn))
        if clip == 'hurt':
            paw = (paw[0] - recoil * 2, paw[1])
        el, hd = arm_ik(sh, paw, 34, 32, bend=-1)
        muscle(r, [hd, el], 8.5, 9.4, shade)
        muscle(r, [el, sh], 9.4, 11.5, shade)
        r.ball(hd[0], hd[1], 8.5, 7.5, shade)
        for c in (-1, 0, 1):
            r.fang(hd[0] + 3, hd[1] - 1 + c * 3, 11, 4, -.3 + c * .35 + st * -.4, BONE)
        if clip != 'die' or n < 4:
            honey_string(r, hd[0] + 1, hd[1] - 6, 10 + k * 4 + (7 if st > .5 else 0), 1.5, 2.6)
    if st > .45:                                         # the slam bursts honey out along the ground
        for i in range(6):
            a.ball(34 + i * 8 + lean * 2, 3 + (i % 2) * 1.5, 3.4, 2.6, HONEY)
    if dn > .35:                                         # the hive splits and the honey spreads over the ground
        sp = min(1, (dn - .35) / .5)
        for i, (gx, gr) in enumerate(((-46, 8), (-26, 14), (-4, 18), (22, 12))):
            a.ellipse(gx * (.5 + sp * .7), 2.2 + (i % 2) * .4, gr * sp + 2, 2 + sp * .6, HONEY[1] if i % 2 else HONEY[2])
    return a


def scythe(r, hand, ang, length, ramp_blade, thick=5):
    """A rusted harvest scythe: a stout pole from the hand with a long curved steel blade at the far end, all outlined."""
    d = (math.cos(ang), math.sin(ang))
    tip = (hand[0] + d[0] * length, hand[1] + d[1] * length)
    tail = (hand[0] - d[0] * length * .22, hand[1] - d[1] * length * .22)
    r.line([tail, tip], BEAR[0], thick + 2)
    r.line([tail, tip], WICKER[2], thick)
    r.line([(tail[0] - d[1] * 1, tail[1] + d[0] * 1), (tip[0] - d[1] * 1, tip[1] + d[0] * 1)], WICKER[4], 1)
    c = (tip[0] + math.cos(ang - .5) * 30, tip[1] + math.sin(ang - .5) * 30)
    e = (tip[0] + math.cos(ang - 1.45) * 40, tip[1] + math.sin(ang - 1.45) * 40)
    mid = bez(tip, c, e, 9)
    out, inn = [], []
    for i, (px, py) in enumerate(mid):
        t = i / 9
        k = 8 * (1 - t) ** .7 + .6
        nx, ny = (-(mid[min(i + 1, 9)][1] - mid[max(i - 1, 0)][1]), mid[min(i + 1, 9)][0] - mid[max(i - 1, 0)][0])
        ln = math.hypot(nx, ny) or 1
        out.append((px + nx / ln * k * .15, py + ny / ln * k * .15))
        inn.append((px - nx / ln * k, py - ny / ln * k))
    r.poly(out + inn[::-1], ramp_blade[2], outline=ramp_blade[0])
    r.line([(x - .6, y + .6) for x, y in out[1:-1]], ramp_blade[4], 1)
    return tip


def wickerwarden(clip, n):
    """Tall woven-cane giant: a basket skull under a ragged hat with hollow ember slots and a zigzag mouth, straw bursting from its joints, a rusted scythe; it unravels into a heap when it dies."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 18 - w * 12 + recoil * 1.4
    a = Painter('wickerwarden', lunge * .5)
    r = Rig(a, 0, 0, 0)
    sw = math.sin(ph) if clip == 'walk' else 0
    breath = math.sin(ph) * (.9 if clip == 'idle' else .4)
    fall = sm(dn * 1.15)
    lean = (st * 9 - w * 12) + recoil
    top = 1 - fall                                        # how much of the standing figure remains
    cane = WICKER
    darkc = [WICKER[0], WICKER[0], WICKER[1], WICKER[2], WICKER[3]]
    sink = fall * 46
    # legs: two bundled-cane pillars wound with straw bands
    for k, (hx, shade) in enumerate(((-13, darkc), (13, cane))):
        s = sw if k else -sw
        hip = (hx + lean * .2, 46 - sink * .5)
        ft = (hx + s * 8, 4 + max(0, s) * 6)
        if dn:
            ft = (hx * (1 + fall * 1.2) + fall * 6 * (k * 2 - 1), 4)
        knee = (mix(hip[0], ft[0], .5) + 3, mix(hip[1], ft[1], .5) + 1)
        r.limb([hip, knee, ft], shade, 15 - fall * 3)
        for t_ in (.3, .62):
            p = mixp(hip, ft, t_)
            r.line([(p[0] - 7, p[1] - 1.4), (p[0] + 7, p[1] + 1.4)], STRAW[2], 2)
        r.ball(ft[0] + 3, ft[1] + 1.2, 10, 4.2, darkc)
        for c in range(4):                               # straw tufts at the ankle
            r.fang(ft[0] - 6 + c * 4, ft[1] + 6, 6 + c % 2 * 2, 2.6, 1.9 - c * .3, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    ty = 70 - sink + breath                               # torso centre
    # tattered straw skirt
    for c in range(11):
        fang(a, -22 + c * 4.4 + lean * .3, ty - 22, 14 + (c % 3) * 4, 4, -math.pi / 2 + (c - 5) * .05 + sw * .08, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    # torso: a woven barrel; crossed cane bands drawn over the shading
    a.ball(lean * .5, ty, 25 - fall * 4, 28 * (1 - fall * .35), WICKER, .0)
    for c in range(-3, 4, 2):
        a.line([(-19 + c * 3 + lean * .5, ty - 25 * (1 - fall * .35)), (-5 + c * 3 + lean * .5, ty + 25 * (1 - fall * .35))], darkc[1], 1)
        a.line([(19 + c * 3 + lean * .5, ty - 25 * (1 - fall * .35)), (5 + c * 3 + lean * .5, ty + 25 * (1 - fall * .35))], darkc[1], 1)
    for yy in (-14, -4, 6, 16):
        a.line([(-20 + lean * .5, ty + yy * (1 - fall * .35)), (20 + lean * .5, ty + yy * (1 - fall * .35) + 1)], WICKER[4], 1)
    a.line([(-22 + lean * .5, ty + 5), (22 + lean * .5, ty + 1)], CLOTH[2], 4)       # faded red cord belt
    for c in range(5):                                    # straw bursting from the seams
        fang(a, -14 + c * 7 + lean * .5, ty + 24 * (1 - fall * .3), 9, 3, math.pi / 2 + (c - 2) * .3, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    # arms: cane bundles ending in jagged cane claws; the right one swings the scythe
    shy = ty + 20 * (1 - fall * .3)
    hands = []
    for k, (sx0, shade) in enumerate(((-18, darkc), (20, cane))):
        sh = (sx0 + lean * .8, shy)
        paw = (sx0 + 12 - sw * 5 * (1 if k else -1), ty - 12 - sink * .2)
        if clip == 'attack':
            if k:
                up = (sx0 - 24, ty + 62)
                down = (sx0 + 48, 14)
                paw = mixp(mixp(paw, up, w), down, st)
            else:
                paw = mixp(paw, (sx0 + 10 + 20 * st, ty + 10 - 6 * st), w * .6 + st * .6)
        if dn:
            paw = mixp(paw, (sx0 * 1.5 + 8 + k * 16, 12), fall)
        el, hd = arm_ik(sh, paw, 25, 26, bend=-1)
        muscle(r, [hd, el], 5.4, 6.4, shade)
        muscle(r, [el, sh], 6.4, 8, shade)
        hands.append(hd)
        for c in range(4):
            fang(a, hd[0] + 1, hd[1] + (c - 1.5) * 2.6, 9, 3, -.5 + c * .25 - st * .3, [WICKER[1], WICKER[2], WICKER[3], WICKER[4], BONE[4]])
        for c in range(3):
            fang(a, el[0], el[1] - 2, 7, 2.6, 1.7 + c * .35 + k * .8, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    hd = hands[1]
    # the scythe: the pole follows the swing, blade out ahead
    s_ang = 1.0
    if clip == 'attack':
        s_ang = mix(mix(1.0, 2.35, w), -.42, st)
    if dn:
        s_ang = mix(s_ang, -.05, fall)
    scythe(r, (hd[0], hd[1] - 2 * (1 - fall)), s_ang, 62, [BEAR[0], BEAR[1], BADGER[2], BEAR[3], WHITE])
    # head: basket skull, ragged straw hair, broad hat with a faded band, hollow ember slots
    hx, hy = 4 + lean * 1.2 + st * 8, ty + 40 + breath - w * 2 - st * 7 - fall * 26 + (fall * 5)
    a.limb([(lean * .6, ty + 16), (hx - 1, hy - 10)], darkc, 12)
    a.ball(hx, hy, 17 - fall * 2, 18, WICKER, .0)
    for c in range(-2, 3):
        a.line([(hx + c * 5 - 2, hy - 15), (hx + c * 3 + 1, hy + 15)], darkc[1], 1)
    for yy in (-8, 0, 8):
        a.line([(hx - 15, hy + yy), (hx + 15, hy + yy + 1)], darkc[1], 1)
    for c in (0, 1, 5, 6):                                # straw hair spilling from the sides under the brim
        fang(a, hx - 16 + c * 5, hy + 4, 12 + c % 2 * 4, 3.4, -math.pi / 2 - .35 + (c > 2) * .7, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    ember = EMBER[3] if clip != 'attack' or not (1 <= n <= 5) else EMBER[4]
    if dying(clip, n):
        ember = EMBER[1] if clip == 'die' and n < 5 else EMBER[0]
    for sd, ex in ((1, hx + 6), (-1, hx - 8)):           # hollow angled slots, burning inside
        a.poly([(ex - 6, hy + 1), (ex + 6.4, hy + 6.4 * (1 if sd > 0 else .5)), (ex + 5.6, hy - 1.8), (ex - 5.4, hy - 6.4)], OUTLINE)
        a.poly([(ex - 4.4, hy), (ex + 4.8, hy + 4.2 * (1 if sd > 0 else .5)), (ex + 4.2, hy - 1), (ex - 4, hy - 4.2)], ember)
        if not dying(clip, n):
            a.line([(ex - 2, hy - 1), (ex + 3.4, hy + 1.2 * (1 if sd > 0 else .5))], EMBER[4], 1)
    zig = [(hx - 8, hy - 10), (hx - 5, hy - 7), (hx - 2, hy - 10.5), (hx + 1, hy - 7), (hx + 4, hy - 10.5), (hx + 7, hy - 7.4)]
    a.line(zig, OUTLINE, 3)
    if clip != 'die' or n < 5:
        a.line([(x, y - .6) for x, y in zig], ember, 1)
    hat_y = hy + 15 - fall * 3
    hc = hx + 2 + lean * .3
    a.ellipse(hc, hat_y, 32, 6, BEAR[0])
    a.ellipse(hc, hat_y + 1, 30, 4.6, STRAW[1])
    a.ellipse(hc, hat_y + 2, 25, 2.6, STRAW[2])
    a.ball(hc - 1, hat_y + 8 - fall * 2, 15, 11, STRAW, .0)
    a.poly([(hc - 14, hat_y + 5.4), (hc + 14, hat_y + 5.4), (hc + 13, hat_y + 9), (hc - 13, hat_y + 9)], CLOTH[1], outline=BEAR[0])
    a.line([(hc - 13, hat_y + 8.2), (hc + 13, hat_y + 8.2)], CLOTH[3], 1)
    a.poly([(hc - 7, hat_y + 17), (hc - 3, hat_y + 21), (hc - 1, hat_y + 16)], STRAW[0])         # a dent in the crown
    for c in range(4):                                    # torn brim
        fang(a, hc - 26 + c * 17, hat_y - 3, 6, 3, -math.pi / 2 - .15, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    # unravelled heap on the ground
    if fall > .3:
        sp = min(1, (fall - .3) / .6)
        for i in range(int(14 * sp)):
            x0 = -34 + (i * 29 % 67) + (i % 3)
            a.line([(x0, 2 + i % 4 * 1.6), (x0 + 12 - (i % 3) * 5, 3 + (i * 7 % 5) * 1.6)], darkc[(i % 3) + 1] if i % 3 else STRAW[2], 2)
        for i in range(int(7 * sp)):
            fang(a, -26 + i * 9, 3, 8, 3, 1.1 + (i % 3) * .5, [STRAW[0], STRAW[1], STRAW[2], STRAW[3], STRAW[4]])
    return a


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
        np.savez_compressed(ROOT / f'scripts/sunward_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/sunward_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'sunward_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    assert live['kinds'][-3:] == VILLAGERS, 'villager entries moved'
    villagers = {k: (live['sprites'][k], live['tops'][k]) for k in VILLAGERS}
    meta = json.loads(json.dumps(live))
    meta['artStyle'] = 'greenmeadow-slime'
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
