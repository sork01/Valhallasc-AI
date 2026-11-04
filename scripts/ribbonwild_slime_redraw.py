#!/usr/bin/env python3
"""The Ribbonwild (zone 21, index 20 in map.txt) enemy redo: six native PixelFlow sources with per-kind frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner direction (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye-plus-blush face. The old Ribbonwild art
was the worst case (googly round eyes everywhere, blush on the jesterling and the colossus). Each kind has its own face
routine: bulging lidded eyes with vertical slit pupils over a toothed gape and a lashing tongue (ribbongecko), faceted
red compound eyes over hooked mandibles (balloonbeetle), a pinprick eye in a bare white face patch over a tapered hooked
beak (paintedmacaw), hollow sockets with pinpoint glints over a painted needle-tooth grin (jesterling), a hard yellow
raptor glare under a heavy brow over a screaming hooked beak (paradegryphon), and a porcelain carnival mask with hollow
sockets and a jagged black mouth (maskcolossus). No blush anywhere. Effects (ribbons, strings, bells, plumes) are
attached to the body, never loose glyphs. Shaded volume, eight distinct attack frames (wind-up, strike, recovery) and
eight distinct death frames per kind. The six enemies share `ribbonwild.txt` with three NPCs (`ribbon_host`,
`ribbon_keeper`, `ribbon_travel`): export merges only the six enemy entries and never touches the NPCs. Original
cel-shaded art: /media/raid/valhallasc-data/ribbonwild-slime-original-20261104 (`scripts/rollback_ribbonwild_art.py`).
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
    TEAL, SPORE, PINK, ORCHID, PLUM, PURPLE, VIOLET, BLUE, AZURE, GREEN, GHOST, HEART, VOID, FUR,
)
from astral_slime_redraw import (
    Painter as BasePainter, OUTLINE, WHITE, EYE_WHITE,
    BONE, PEARL, CRIMSON, CORAL, AMBER, GOLD,
    mix, mixp, rot, sm, bez, taper, foot, arm_ik,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/ribbonwild-slime'
REGISTRY = ROOT / 'scripts/ribbonwild_slime_sources.txt'
PREFIX = 'valhallasc_ribbonwild_slime_style_'
KINDS = ['ribbongecko', 'balloonbeetle', 'paintedmacaw', 'jesterling', 'paradegryphon', 'maskcolossus']
NAMES = dict(zip(KINDS, ['Ribbon Gecko', 'Balloon Beetle', 'Painted Macaw', 'Jesterling', 'Parade Gryphon', 'Mask Colossus']))
VILLAGERS = ['ribbon_host', 'ribbon_keeper', 'ribbon_travel']
MANIFEST = ASSETS / 'ribbonwild.txt'
W = H = 96
AX, AY = 48, 90
# (frame w, frame h, anchor x, anchor y): tuned with `extents` so each kind's art fills its own frame.
KIND_FRAMES = dict(
    ribbongecko=(128, 40, 59, 34),
    balloonbeetle=(92, 99, 40, 93),
    paintedmacaw=(100, 80, 46, 74),
    jesterling=(88, 86, 26, 80),
    paradegryphon=(129, 88, 63, 82),
    maskcolossus=(120, 96, 41, 90),
)
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('balloonbeetle',)
PALETTE = BASE_PALETTE[:] + [
    '#3a0808', '#8a1010', '#d82020', '#ff5a3c', '#ffb09c',   # RED (scarlet macaw, balloon)
    '#0c0c10', '#24242c', '#44444e', '#6a6a78', '#9a9aa8',   # INK (jester shadow, claws, gryphon talons)
    '#3a2a12', '#8a6a24', '#d2aa44', '#f4d870', '#fff4b4',   # BRASS (bells, crown)
]
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
assert len(PALETTE) <= 256, 'palette exceeds the indexed limit'
_n = len(BASE_PALETTE)
RED, INK, BRASS = [list(range(_n + 5 * i, _n + 5 * i + 5)) for i in range(3)]


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
SCALE = dict(ribbongecko=.82, balloonbeetle=.78, paintedmacaw=.85, jesterling=.85, paradegryphon=.74, maskcolossus=.78)


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

def teeth(a, x0, x1, y, size, ramp=BONE, down=True, n=None):
    """A row of small triangular teeth between x0 and x1 hanging from (down) or rising from (not down) the line y."""
    n = n or max(2, int(abs(x1 - x0) / 2.6))
    for i in range(n):
        x = mix(x0, x1, (i + .5) / n)
        tip = y - size * (1 - .35 * (i % 2)) if down else y + size * (1 - .35 * (i % 2))
        a.poly([(x - 1.15, y), (x + 1.15, y), (x, tip)], ramp[4], outline=ramp[0])


def ribbongecko(clip, n):
    """Teal wall-gecko with a magenta back-frill and a ribbon-tipped tail: bulging lidded eye with a vertical slit pupil, a toothed gape, a lashing tongue."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 14 - w * 7 + recoil
    a = Painter('ribbongecko', lunge * .5)
    swing = math.sin(ph) if clip == 'walk' else 0
    flat = sm(dn * 1.5)                                       # the body goes slack and flat on death
    cy = mix(mix(18 + bob * .5, 12, w), 17, st)
    cy = mix(cy, 5.4, flat)
    belly = [SPORE[1], SPORE[2], SPORE[3], SPORE[4], WHITE]
    far = [TEAL[0], TEAL[0], TEAL[1], TEAL[2], TEAL[3]]
    # tail: a thick tapered curl ending in a ribbon-bow; whips on the strike, lies limp when dead
    wag = math.sin(ph * 1.1) * 3 * (1 - dn) + st * 6 - w * 4
    tp = [(-18, cy - 1), (-34, cy + 2 + wag * .3 - flat * 2), (-48 - flat * 4, cy + 7 + wag + flat * 2), (-56 - flat * 6, cy + 4 + wag * .6 - flat * 3)]
    pts = bez(tp[0], tp[1], tp[2], 7)
    taper(a, pts, TEAL, 9, 2.4)
    for i in range(1, 7, 2):                                   # belly-pale bands on the tail
        px, py = pts[i]
        a.ellipse(px, py - 1.2, 2.4, 2.4, SPORE[3])
    ex, ey = pts[-1]
    # ribbon tip: two magenta streamers and a knot, attached to the tail end
    flutter = math.sin(ph * 1.7) * 3 * (1 - dn)
    a.poly([(ex, ey), (ex - 9, ey + 6 + flutter), (ex - 13, ey + 2 + flutter), (ex - 5, ey - 1.5)], PINK[2], outline=PINK[0])
    a.poly([(ex, ey), (ex - 8, ey - 6 - flutter), (ex - 12, ey - 2 - flutter), (ex - 4, ey + .5)], PINK[3], outline=PINK[0])
    a.ellipse(ex + .5, ey, 2.4, 2.4, PINK[1])
    # legs: splayed gecko limbs (elbows out), four broad webbed toes each
    for k, (hx, shade) in enumerate(((-12, far), (14, far), (-7, TEAL), (19, TEAL))):
        front = hx > 0
        sw = math.sin(ph + (math.pi if k % 2 else 0)) if clip == 'walk' else 0
        lift = max(0, sw) * 5
        hip = (hx, cy - 2)
        foot_ = (hx + sw * 6 + (3 if front else -3), 2 + lift)
        if clip == 'attack' and front:
            foot_ = (hx + 4 + st * 20 - w * 4, 2 + st * (cy + 2) * (.9 if k == 3 else .5) + w * 1)
        if flat:
            foot_ = (hx + (9 if front else -9) * flat + foot_[0] * (1 - flat), 1.8 + (k % 2) * 1.4)
        spread = max(0, 1 - flat * .5)
        elbow = (mix(hip[0], foot_[0], .5) + (4 if front else -4) * spread, mix(hip[1], foot_[1], .5) + 3 * spread)
        a.limb([hip, elbow, foot_], shade, 4.6)
        for t in (-1, 0, 1):                                    # toes with pink pads
            tx = foot_[0] + 3.2 + t * 1.6
            a.line([(foot_[0] + .5, foot_[1] + .6), (tx + (1 if front else -1) * 1.5, max(.8, foot_[1] - .8 + t * 1.2))], shade[0], 2)
            a.ball(tx + (1 if front else -1) * 1.5, max(1.4, foot_[1] + t * .6), 1.7, 1.4, PINK)
    # body: long, low, with a pale belly and a ridge of magenta frill spikes
    a.ball(0, cy, 24, mix(8.8, 4.2, flat), TEAL, .06)
    a.ball(1, cy - 3.4 + flat, 20, mix(4.8, 2.2, flat), belly, 0)
    for k in range(-1, 2):
        a.ellipse(-8 + k * 9, cy + 1.2 - flat, 2.3, 1.9, PINK[3])
    for k in range(7):
        x = -16 + k * 5.2
        h = 8 - abs(k - 3) * .6
        fang(a, x, cy + mix(7.6, 3.6, flat) - abs(k - 3) * .3, h * (1 - flat * .55), 5.4, math.pi * .5 + .3 + st * .1, PINK)
    # head: a heavy wedge skull, a hinged lower jaw ringed with teeth, a lashing tongue
    hx = 27 + st * 9 - w * 5 - flat * 6
    hy = mix(cy + 3.6 - st * 1.5 + w * 1.5, 6, flat)
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    gape = 1.0 + (12 if open_ else 0) * (st if clip == 'attack' else 1) + flat * 3.5 + w * 1.2
    a.ball(hx - 9, hy - 1.5, 13, 8, far, .05)                               # neck, joins head and body
    jx, jy = hx + 11, hy - 5.2 - gape * .5
    a.ball(jx, jy, 12.5, 3.8, belly, -(gape * .035))                        # lower jaw
    teeth(a, hx + 1, hx + 20, jy + 3.2, 3.6, BONE, down=False, n=7)
    if gape > 3:                                                            # dark mouth cavity and the tongue
        a.poly([(hx - 1, hy - 2.6), (hx + 20, hy - 4 - gape * .1), (hx + 20, jy + 3.4), (hx - 1, jy + 1)], OUTLINE)
        a.ellipse(hx + 8, jy + 3.4, 8, 1.8 + gape * .12, PINK[1])
        tl = 3 + st * 15 + (4 if open_ else 0)
        a.line([(hx + 8, jy + 4), (hx + 8 + tl, jy + 3 - st * 3)], PINK[2], 3)
        a.line([(hx + 8 + tl, jy + 3 - st * 3), (hx + 11 + tl, jy + 1 - st * 3)], PINK[2], 1)
        a.line([(hx + 8 + tl, jy + 3 - st * 3), (hx + 11 + tl, jy + 5 - st * 3)], PINK[2], 1)
    a.ball(hx + 2, hy + .8, 15.5, 8.8, TEAL, .08)
    a.ball(hx + 14, hy - .6, 10, 5.6, [TEAL[1], TEAL[2], TEAL[3], SPORE[3], SPORE[4]], .02)
    a.ellipse(hx + 21, hy + 1.6, 1.4, 1.2, OUTLINE)                          # nostril
    teeth(a, hx + 2, hx + 21, hy - 3.8, 4.2, BONE, down=True, n=7)
    a.line([(hx + 1, hy - 3.8), (hx + 22, hy - 3.8)], TEAL[0], 1)
    # the eye: a bulging dome on top of the skull, a gold iris with a vertical slit pupil and a heavy lid
    exx, eyy = hx + 3, hy + 8
    if dying(clip, n):
        a.ellipse(exx, eyy, 5.6, 5.6, SPORE[1])
        cross_eye(a, exx, eyy, 2.8)
    else:
        a.ellipse(exx, eyy, 7.4, 7.4, OUTLINE)
        a.ball(exx, eyy, 6.2, 6.2, [AMBER[0], AMBER[1], AMBER[2], AMBER[3], AMBER[4]], 0)
        sq = 1 if (clip == 'idle' and n == 3) else 0
        a.ellipse(exx + .6, eyy - .2, 1.3 + sq * .6, 5 - sq * 4, OUTLINE)
        a.ellipse(exx - 1.6, eyy + 2.2, 1.1, 1.1, WHITE)
        a.poly([(exx - 8, eyy + 2), (exx - 5, eyy + 8), (exx + 7, eyy + 5.6), (exx + 8, eyy - .8 - sq * 4), (exx, eyy + 1.8 - sq * 4)], TEAL[0])
        a.line([(exx - 6, eyy + 4.4), (exx + 6.6, eyy + 2.2)], TEAL[2], 1)
    for k in range(3):                                                       # pale spots down the skull
        a.ellipse(hx - 4 + k * 5, hy + 5.2 + (k % 2) * .8, 1.6, 1.4, SPORE[4])
    return a


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


def balloon(a, x, y, rx, ry, ramp, tie, pop=0., sway=0.):
    """A glossy balloon on a string whose lower end is `tie`; pop 0 = full, 1 = a shrivelled rag hanging from the string."""
    if pop < .15:
        s = 1 - pop * 2
        a.line([tie, (mixp(tie, (x, y - ry * s), .5)[0] + sway * 2, mixp(tie, (x, y - ry * s), .5)[1]), (x, y - ry * s)], WEBGREY_STRING, 1)
        a.ball(x, y, rx * s, ry * s, ramp, sway * .08)
        a.poly([(x - 1.6, y - ry * s + .6), (x + 1.6, y - ry * s + .6), (x, y - ry * s - 2.6)], ramp[1])
    else:
        k = min(1, (pop - .15) * 1.4)
        end = mixp((x, y - ry), (tie[0] - 2, tie[1] + 14), k * .8)
        a.line([tie, end], WEBGREY_STRING, 1)
        a.poly([(end[0] - 3.4, end[1] + 1), (end[0] + 3.2, end[1] + 1.4), (end[0] + 1.6, end[1] - 6), (end[0] - 1.4, end[1] - 4)], ramp[1], outline=ramp[0])


WEBGREY_STRING = INK[3]


def balloonbeetle(clip, n):
    """Armoured violet beetle lifted by a red and a blue balloon tied to its shell: faceted red compound eyes under a plated brow, hooked mandibles; the balloons pop and it falls onto its back."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 20 - w * 10 + recoil
    a = Painter('balloonbeetle', lunge * .6)
    hov = 48 + math.sin(ph * (1 if clip == 'idle' else 1.4)) * 2.2 * (clip in ('idle', 'walk', 'hurt'))
    fall = sm(max(0, dn - .08) * 1.35)
    cy = mix(hov - w * 3 + st * 5, 17, fall)
    if clip == 'hurt':
        cy += recoil * .6
    pitch = (-.30 * w + .30 * st) if clip == 'attack' else (.04 * math.sin(ph) if clip == 'walk' else 0)
    flip = sm(max(0, dn - .35) * 1.6) * math.pi
    phi = -pitch + flip
    r = Rig(a, 2, cy, phi, 0)
    swing = math.sin(ph) if clip == 'walk' else 0
    sh = [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[4]]
    dark = [VIOLET[0], VIOLET[0], VIOLET[1], VIOLET[2], VIOLET[3]]
    # balloons first (behind): tied to the shell crown, bobbing; they pop when it dies and the strings go limp
    ax, ay = r.t(-7, cy + 15)
    pop = min(1, dn * 3.5) if dn else 0
    sway = math.sin(ph * 1.3)
    bx1, by1 = ax - 5 - w * 3 + st * 5 + sway * 2, ay + 36 + (1 - fall) * 2 - st * 6 + bob
    bx2, by2 = ax + 9 + w * 2 - st * 3 - sway * 1.5, ay + 30 + (1 - fall) * 2 - st * 3 - bob
    if pop < 1 or fall < .99:
        balloon(a, bx2, by2, 10, 12, AZURE, (ax + 2, ay), pop, -sway)
        balloon(a, bx1, by1, 10.5, 12.5, RED, (ax - 2, ay), pop, sway)
    # legs: six hooked legs hanging below the shell; the near three swing, curl forward on the strike, curl up on death
    curl = max(w * .5 + st * .9, fall * 1.1)
    for k, (lx, shade, side) in enumerate(((-12, dark, 0), (0, dark, 1), (11, dark, 0), (-14, sh, 1), (-2, sh, 0), (9, sh, 1))):
        phase = ph + k * 1.9
        sw = math.sin(phase) * (3.2 if clip == 'walk' else 1.4)
        hip = (lx + 2, cy - 8)
        knee = (lx + 8 + sw * .7 - curl * 4, cy - 12 - curl * 2)
        foot_ = (lx + 6 + sw - curl * 14 + st * 7, cy - 22 + curl * 14 + abs(sw) * .2)
        r.limb([hip, knee, foot_], shade, 3.4)
        r.poly([(foot_[0] - 1, foot_[1] + .5), (foot_[0] + 2.2, foot_[1] - .3), (foot_[0] + .6, foot_[1] - 4)], INK[1])
    # shell: a heavy plated dome, a brass seam, raised thorns on the rear edge
    r.ball(-4, cy + 3, 21, 16, sh, .05)
    r.ball(-6, cy + 8, 11, 6.4, [PURPLE[2], PURPLE[3], PURPLE[4], PURPLE[4], WHITE], .5)
    r.line([(-4, cy + 18), (-4, cy + 13), (-3, cy - 6), (-3, cy - 12)], BRASS[1], 2)
    r.line([(-5, cy + 17), (-5, cy - 10)], BRASS[3], 1)
    for k in range(3):
        r.fang(-22 + k * .5, cy + 6 - k * 5.5, 8.5 - k * 1.2, 5, math.pi + .35 + k * .12, [INK[0], INK[1], INK[2], INK[3], INK[4]])
    for k, (sx, sy) in enumerate(((-13, 4), (4, 9), (6, -4), (-14, -6))):    # brass studs
        r.ball(sx, cy + sy, 2.2, 2.2, BRASS)
    if fall > .6:                                           # the shell splits when it hits the ground
        r.line([(-3, cy + 15), (-6, cy + 4), (-1, cy - 3), (-6, cy - 11)], OUTLINE, 2)
    # head
    hx, hy = 21 + st * 3, cy - 1.5
    open_ = .32 + w * .5 + (st * .15 if st < .9 else 0) + (.45 if clip == "hurt" and n == 1 else 0) + fall * .4
    if clip == 'attack' and n >= 5:
        open_ = max(.1, .4 - (n - 4) * .13)
    r.ball(hx - 5, hy - 2, 9, 8, dark, 0)
    r.ball(hx, hy, 12.4, 10.6, [PLUM[0], PLUM[1], PLUM[2], PLUM[3], PLUM[4]], .05)
    # mandibles: two hooked sickles that spread on the wind-up and snap shut on the strike
    for sgn, shade in ((1, [BONE[0], BONE[1], BONE[2], BONE[3], BONE[4]]), (-1, [BONE[0], BONE[0], BONE[1], BONE[2], BONE[3]])):
        by = hy - 4.4
        pts = [(hx + 8, by), (hx + 14, by - sgn * (1 + open_ * 4)), (hx + 19, by - sgn * (3 + open_ * 8)), (hx + 17 - open_ * 3, by - sgn * (7 + open_ * 11) - (3 if sgn > 0 else 0))]
        if sgn < 0:
            pts = [(x, y - 3.2) for x, y in pts]
        r.taper(pts, shade, 5.4, 1.4)
        r.fang(pts[-1][0] - 1, pts[-1][1], 5, 3, math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0]) + sgn * .3, BONE)
    # compound eyes: faceted red domes under a heavy angled brow plate, no pupils
    if dying(clip, n):
        r.ball(hx + 3, hy + 3.4, 6, 6.6, [INK[0], INK[1], INK[1], INK[2], INK[2]], 0)
        r.line([(hx, hy + 1), (hx + 6, hy + 6)], OUTLINE, 2)
        r.line([(hx, hy + 6), (hx + 6, hy + 1)], OUTLINE, 2)
    else:
        r.ball(hx - 3, hy + 4.6, 4.2, 5, RED, 0)
        r.ball(hx + 3.2, hy + 3.4, 6.4, 6.8, RED, 0)
        for k in range(-3, 4):                              # facet lattice
            r.line([(hx + 3.2 + k * 1.7, hy - 3), (hx + 3.2 + k * 1.7 - 1, hy + 10)], RED[0], 1)
        for k in range(-1, 3):
            r.line([(hx - 3, hy + 3.4 + k * 2.4), (hx + 10, hy + 3.4 + k * 2.4 - 1)], RED[0], 1)
        r.ball(hx + 1.6, hy + 5.4, 2.1, 2.1, [RED[3], RED[4], WHITE, WHITE, WHITE], 0)
    r.poly([(hx - 5, hy + 10.4), (hx + 10.6, hy + 4.2), (hx + 10.6, hy + 8.6), (hx - 5, hy + 14.4)], dark[1], outline=INK[0])
    r.line([(hx - 4, hy + 12.2), (hx + 9.4, hy + 6.6)], PURPLE[3], 1)
    # antennae: bent, with a clubbed tip
    for k, (ang, ln) in enumerate(((1.05, 16), (1.4, 14))):
        ant = [(hx + 1 + k * 2, hy + 11), (hx + 3 + k * 3 + math.cos(ang) * ln * .6, hy + 15 + math.sin(ang) * ln * .55),
               (hx + 8 + k * 4 + math.cos(ang) * ln * .9 + (sway if clip != 'die' else 0) * 1.4, hy + 14 + math.sin(ang) * ln * .85 + 4)]
        r.line(ant, INK[2], 1)
        r.ball(ant[-1][0], ant[-1][1], 2.3, 2.3, BRASS)
    return a


def feather_fan(r, root, ang0, ang1, count, length, ramps, width=5.2, droop=0.):
    """A fan of tapered feathers from `root`, angles ang0..ang1; length shortens towards the ends, droop bends the tips down."""
    for i in range(count):
        t = i / max(1, count - 1)
        ang = mix(ang0, ang1, t)
        ln = length * (1 - .22 * abs(t - .45))
        pts = [(root[0] + math.cos(ang + droop * (j / 4) ** 2) * ln * j / 4, root[1] + math.sin(ang + droop * (j / 4) ** 2) * ln * j / 4) for j in range(5)]
        r.taper(pts, ramps[i % len(ramps)], width, 1.6)


def paintedmacaw(clip, n):
    """Scarlet macaw on thin talons: a pinprick yellow eye in a bare white face patch under a heavy red brow, a tall hooked dark beak; blue-gold-green wings that flare, a long barred tail; topples forward when it dies."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('paintedmacaw', 0)
    swing = math.sin(ph) if clip == 'walk' else 0
    topple = sm(dn * 1.2) * 1.5
    lunge = st * 14 - w * 7 + recoil
    cy = 33 + bob * .4 - w * 3 + (st * 2 if clip == 'attack' else 0)
    cy = mix(cy, 9.5, sm(dn * 1.5))
    pivot_x = 4 - dn * 4
    r = Rig(a, pivot_x, 3, -topple, 0)
    # talons: two thin legs with four toes gripping the ground
    for k, (lx, shade) in enumerate(((-3, [INK[0], INK[0], INK[1], INK[2], INK[3]]), (5, [INK[0], INK[1], INK[2], INK[3], INK[4]]))):
        sw = math.sin(ph + k * math.pi) * (4 if clip == 'walk' else 0)
        lift = max(0, math.sin(ph + k * math.pi)) * 4 if clip == 'walk' else 0
        hip = (lx + 1, cy - 12)
        foot_ = (lx + sw, 2.2 + lift)
        r.limb([hip, (lx + 1.5 + sw * .5, mix(hip[1], foot_[1], .5)), foot_], shade, 3.2)
        for t in (-1, 0, 1, 2):
            r.line([(foot_[0], foot_[1] + .4), (foot_[0] + 3 + t * 2.4, max(.8, foot_[1] - .6))], INK[1], 2)
            r.ball(foot_[0] + 3.6 + t * 2.4, max(1.4, foot_[1] - .4), 1.5, 1.2, BONE)
    # tail: three long barred feathers hanging down and back
    tail_root = (-6, cy - 8)
    sway = math.sin(ph * 1.2) * .06
    for k, (ang, ln, ramp) in enumerate(((-2.45, 42, BLUE), (-2.15, 46, RED), (-1.95, 38, GOLD))):
        pts = [(tail_root[0] + math.cos(ang + sway * k + topple * .4 * (k - 1)) * ln * j / 5, tail_root[1] + math.sin(ang + sway * k) * ln * j / 5) for j in range(6)]
        r.taper(pts, ramp, 7, 2)
        r.line([pts[1], pts[4]], ramp[4], 1)
    # body: an upright egg of scarlet with a pale belly, tilted forward
    r.ball(0, cy, 14.5, 20, RED, -.28)
    r.ball(3.4, cy - 6, 9, 13, [RED[1], RED[2], RED[3], RED[3], RED[4]], -.28)
    for k in range(4):                                                  # breast feather scallops
        r.line([(2 + k * .8, cy - 3 - k * 4.6), (6 + k * .8, cy - 5 - k * 4.6), (10 + k * .8, cy - 3 - k * 4.6)], RED[1], 1)
    # wing: folded against the flank, or flared back and up on the wind-up and strike
    flare = max(w * .85, st * 1.0) if clip == 'attack' else 0
    flare = max(flare, sm(dn * 1.4) * 1.1, .7 if clip == 'hurt' and n == 1 else 0)
    wing_root = (-1, cy + 5)
    a0 = mix(-2.2, -.6, flare * .95)
    a1 = mix(-1.8, 1.9, flare)
    feather_fan(r, wing_root, a0, a1, 6 + int(flare * 2), mix(29, 42, flare), [BLUE, BLUE, GREEN, GOLD], mix(7.4, 6.4, flare), droop=sm(dn) * -.5)
    r.ball(-2, cy + 1, 9.2, 15, [BLUE[0], BLUE[1], BLUE[1], BLUE[2], BLUE[3]], -.3)           # the folded wing body
    r.ball(0.4, cy + 8, 8.4, 6, [GOLD[0], GOLD[1], GOLD[2], GOLD[3], GOLD[4]], .1)            # gold shoulder band
    r.ball(-1, cy + 2.4, 7.6, 3.8, [GREEN[0], GREEN[1], GREEN[2], GREEN[3], GREEN[3]], -.3)   # green band
    r.line([(-6, cy - 9), (-4.4, cy - 2), (-1, cy + 5)], BLUE[3], 1)
    # head: a big skull on a short neck; the strike drives it forward and down
    reach = st * 22 - w * 8
    hx = 10 + reach * .85 + recoil * .5
    hy = cy + 21 - st * 14 + w * 6 - topple * 3
    r.ball(5, cy + 15, 7, 9, RED, -.5)
    r.ball(hx, hy, 11.4, 10.8, RED, .15)
    # bare white face patch, scalloped with tiny feather lines
    r.ball(hx + 4, hy - 2.6, 8, 7.4, [BONE[2], BONE[3], BONE[4], WHITE, WHITE], .1)
    for k in range(3):
        r.line([(hx + 1.5, hy - .2 - k * 2.3), (hx + 8, hy + .6 - k * 2.3)], BONE[1], 1)
    # beak: a tall hooked upper mandible in dark horn with a pale tip, a smaller lower hook that drops open
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    gap = 1.2 + (9 if open_ else 0) * (1 if clip != 'attack' else min(1, st * 1.4)) + sm(dn) * 5
    bx, by = hx + 8, hy - 2.6
    up = bez((bx, by + 4.6), (bx + 11, by + 8), (bx + 15, by - 4), 7)
    up = [(x, y) for x, y in up] + [(bx + 15.4, by - 8.4)]
    r.taper(up, [INK[0], INK[1], INK[2], INK[3], INK[4]], 9, 1.6)
    r.fang(bx + 14.6, by - 5, 6.6, 4, -math.pi / 2 - .15, BONE)
    low = bez((bx, by - .4 - gap * .2), (bx + 7, by - 2.4 - gap), (bx + 12, by - 1.2 - gap * 1.2), 5)
    r.taper(low, [INK[0], INK[0], INK[1], INK[2], INK[2]], 5.2, 1.4)
    if gap > 4:
        r.poly([(bx + .5, by + .4), (bx + 11, by - 1), (bx + 11, by - 1.6 - gap), (bx + .5, by - .6 - gap * .3)], OUTLINE)
        r.line([(bx + 3, by - 1 - gap * .4), (bx + 9, by - 1.4 - gap * .7)], PINK[2], 2)
    # the pinprick eye: a tiny pale-gold ring around a hard black point, under a heavy scarlet brow
    ex, ey = hx + 3.2, hy + 2.2
    if dying(clip, n):
        r.line([(ex - 2.4, ey - 2), (ex + 2.4, ey + 2)], OUTLINE, 2)
        r.line([(ex - 2.4, ey + 2), (ex + 2.4, ey - 2)], OUTLINE, 2)
    else:
        r.ellipse(ex, ey, 3.5, 3.5, OUTLINE)
        r.ellipse(ex, ey, 2.7, 2.7, GOLD[4])
        r.ellipse(ex + .5, ey - .2, 1.15, 1.15, OUTLINE)
    r.poly([(ex - 5.6, ey + 3.4), (ex + 5.4, ey + 1), (ex + 5.4, ey + 4.8), (ex - 5.6, ey + 7.6)], RED[1], outline=RED[0])
    r.line([(ex - 4, ey + 6), (ex + 4.4, ey + 3.6)], RED[3], 1)
    # a crest of three scarlet feathers swept back
    for k in range(3):
        base = (hx - 4 + k * 3, hy + 8.6)
        r.taper([base, (base[0] - 4, base[1] + 6 + (k == 1) * 2), (base[0] - 9 + k, base[1] + 8 + k)], RED, 4, 1.4)
    return a


def bell(r, x, y, rad=2.6):
    r.ball(x, y, rad, rad, BRASS)
    r.ellipse(x, y - rad * .35, rad * .5, rad * .3, BRASS[0])


def blade(r, hand, ang, length, width=4.2):
    """A curved jester's dagger gripped at `hand`: brass hilt, steel blade curving forwards and up from its angle."""
    hx, hy = hand
    gx, gy = hx + math.cos(ang) * 3.2, hy + math.sin(ang) * 3.2
    r.line([(hx - math.cos(ang) * 2.4, hy - math.sin(ang) * 2.4), (gx, gy)], BRASS[1], 3)
    r.line([(gx - math.sin(ang) * 3.4, gy + math.cos(ang) * 3.4), (gx + math.sin(ang) * 3.4, gy - math.cos(ang) * 3.4)], BRASS[2], 2)
    pts = []
    for i in range(6):
        t = i / 5
        aa = ang + .55 * t * t
        pts.append((gx + math.cos(ang) * length * t * .9 + math.sin(aa) * 0 + math.cos(aa) * 0, gy + math.sin(ang) * length * t * .9 + (math.cos(ang) * 0) + (-math.sin(ang) * 0) + .55 * length * t * t * .35))
    taper(r, pts, [FUR[0], FUR[1], FUR[2], FUR[3], FUR[4]], width, 1)


def jesterling(clip, n):
    """Pale painted jester in a harlequin tunic and a three-bell cap: hollow angled sockets with pinpoint glints, a wide painted needle-tooth grin and a curved knife; collapses into a heap of cloth and bells."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lunge = st * 13 - w * 7 + recoil
    a = Painter('jesterling', lunge * .55)
    swing = math.sin(ph) if clip == 'walk' else 0
    fold = sm(dn * 1.25)
    hipy = 21 - w * 5 + st * 1.5 + bob * .5 - sm(dn * 1.4) * 12
    r = Rig(a, 0, hipy, -fold * 1.35 - w * -.12 + st * .22 - (.18 if clip == 'hurt' and n == 1 else 0), 0)
    dark = [PLUM[0], PLUM[0], PLUM[1], PLUM[2], PLUM[3]]
    # legs: thin, in pointed curled shoes with brass bells; they buckle and splay as it falls
    for k, (lx, shade) in enumerate(((-2, [TEAL[0], TEAL[0], TEAL[1], TEAL[2], TEAL[3]]), (3, [PINK[0], PINK[0], PINK[1], PINK[2], PINK[3]]))):
        sw = math.sin(ph + k * math.pi) if clip == 'walk' else 0
        lift = max(0, sw) * 5
        hip = (lx, hipy - 2)
        foot_ = (lx + sw * 7 + (6 * st if k else -3 * w) + fold * (6 if k else -6), 2.4 + lift)
        knee = (mix(hip[0], foot_[0], .5) + 4 + fold * (9 if k else -2), mix(hip[1], foot_[1], .5) + 1 - fold * 4)
        a.limb([hip, knee, foot_], shade, 4.4)
        a.poly([(foot_[0] - 3, foot_[1] + 1.2), (foot_[0] + 5, foot_[1] + 1.6), (foot_[0] + 9, foot_[1] + 5.2), (foot_[0] + 4.4, foot_[1] - 2)], shade[2], outline=shade[0])
        bell(a, foot_[0] + 9.4, foot_[1] + 5.8, 2.2)
    # torso: a harlequin tunic of diamonds under a ruffled collar
    r.ball(0, hipy + 11, 10.8, 12.6, [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[3]], -.1)
    for k, (dx, dy, col) in enumerate(((-3.4, 4, PINK[2]), (3, 4, TEAL[2]), (0, 9.4, GOLD[2]), (-4, 14.4, TEAL[2]), (3.6, 14.4, PINK[2]), (0, 19.4, GOLD[2]))):
        r.poly([(dx, hipy + dy - 3.4), (dx + 3, hipy + dy), (dx, hipy + dy + 3.4), (dx - 3, hipy + dy)], col, outline=PURPLE[0])
    r.ball(0, hipy + 3, 10.6, 4, [PINK[0], PINK[1], PINK[2], PINK[3], PINK[3]], 0)         # waist sash
    neck_y = hipy + 22
    for k in range(7):                                      # a ruffled white collar
        cx = -9 + k * 3
        r.poly([(cx - 2.4, neck_y), (cx + 2.4, neck_y), (cx, neck_y - 5.4)], BONE[3] if k % 2 else WHITE, outline=BONE[1])
    # arms: long, thin, clawed; the near one holds the knife and cocks back on the wind-up, slashes forward-down on the strike
    sh = (3, hipy + 19)
    reach_target = (mix(mix(15, -11, w), 25, st), mix(mix(hipy + 17, hipy + 36, w), hipy + 7, st) + swing * 2)
    if dn:
        reach_target = (sh[0] + 7 + 6 * fold, hipy + 6 - fold * 3)
    e1, h1 = arm_ik(r.t(*sh), r.t(*reach_target), 11, 11, -1)
    far_target = (mix(-9, 8, st) + swing * -3, hipy + 9 - dn * 4 + w * 6)
    e2, h2 = arm_ik(r.t(sh[0] - 3, sh[1] - 1), r.t(*far_target), 10, 10, 1)
    a.limb([r.t(sh[0] - 3, sh[1] - 1), e2, h2], [PINK[0], PINK[0], PINK[1], PINK[2], PINK[3]], 3.4)
    for dx in (-2, 0, 2):
        a.line([h2, (h2[0] + 3 + dx * .5, h2[1] - 2.4 + dx * .8)], INK[1], 1)
    a.limb([r.t(*sh), e1, h1], [TEAL[0], TEAL[0], TEAL[1], TEAL[2], TEAL[3]], 3.4)
    bang = .1 + (w * 1.8 if clip == 'attack' else 0) - (st * 2.4)
    a.line([h1, (h1[0] + 3, h1[1] + 1)], INK[1], 3)
    if not (dn > .5):
        blade(a, h1, 1.1 - st * 1.5 + w * .7 if clip == 'attack' else 1.0 + .12 * math.sin(ph), 17 + st * 3)
    # head: a pale painted face; the sockets are hollow and angry, the grin is painted wide with needle teeth
    hx, hy = 3 + st * 1, neck_y + 10
    r.ball(hx, hy, 12.6, 12.8, [BONE[1], BONE[2], BONE[3], BONE[4], WHITE], .0)
    r.ball(hx + 5, hy - 4.4, 6.4, 5, [BONE[2], BONE[3], BONE[4], WHITE, WHITE], 0)
    dead = dying(clip, n)
    for sgn, ex in ((1, hx + 6.6), (-1, hx - 4.6)):
        if dead:
            r.line([(ex - 2.6, hy + 3), (ex + 2.6, hy + 8.4)], OUTLINE, 2)
            r.line([(ex - 2.6, hy + 8.4), (ex + 2.6, hy + 3)], OUTLINE, 2)
            continue
        r.poly([(ex - 3.4, hy + 9.8), (ex + 3.8, hy + 6.8), (ex + 3.8, hy + .6), (ex - 3.4, hy + 3.4)], OUTLINE)
        r.ellipse(ex + .8, hy + 3.8, 1.1, 1.1, RED[3] if not (clip == 'hurt' and n == 0) else WHITE)
        r.line([(ex - 5, hy + 11), (ex + 5.4, hy + 7.4)], PLUM[0], 2)               # heavy brow
    r.poly([(hx + 9, hy - .4), (hx + 14.4, hy - 3.8), (hx + 9, hy - 3.4)], PINK[2], outline=PINK[0])    # a long hooked nose
    # the painted grin: a black crescent, red corners hooked up the cheeks, a row of needle teeth
    open_ = 1.2 + st * 3.4 + (1.6 if clip == 'hurt' and n == 1 else 0) + fold * 2 + w * 1.4
    mp = [(hx - 6.4, hy - 3.4 + open_ * .3), (hx - 2.8, hy - 5.8 - open_), (hx + 2.4, hy - 6.4 - open_), (hx + 7, hy - 4.2 - open_ * .6), (hx + 8.6, hy - 2.4 + open_ * .1)]
    r.poly(mp + [(hx + 4, hy - 3.2), (hx - 1, hy - 3.4)], OUTLINE)
    r.line([(hx - 6.4, hy - 3.4), (hx - 8.4, hy - .6)], CRIMSON[2], 1)
    r.line([(hx + 8.6, hy - 2.4), (hx + 10, hy + .2)], CRIMSON[2], 1)
    for k in range(5):
        tx = hx - 4.4 + k * 2.9
        r.poly([(tx - .8, hy - 3.2), (tx + .8, hy - 3.2), (tx, hy - 6.6 - open_ * .5 - (1.4 if k % 2 else 0))], WHITE)
    for k in range(4):                                                                    # lower needles rising from the jaw
        tx = hx - 3 + k * 2.9
        r.poly([(tx - .7, hy - 6.6 - open_ * 1.1), (tx + .7, hy - 6.6 - open_ * 1.1), (tx, hy - 4.4 - open_ * .5)], BONE[4])
    # the three-bell cap: points droop back, up and forward, each tipped with a brass bell
    cap_y = hy + 14
    flick = math.sin(ph * 1.3) * 2 * (1 - fold) + st * 4 - w * 3
    pts_cap = (
        ([(hx - 3, cap_y), (hx - 11, cap_y + 5), (hx - 16 - flick, cap_y - 4), (hx - 17 - flick, cap_y - 11 + fold * 4)], TEAL),
        ([(hx + 1, cap_y + 1), (hx + 1, cap_y + 9), (hx - 1 + flick * .5, cap_y + 16), (hx - 6 + flick, cap_y + 20 - fold * 8)], PINK),
        ([(hx + 5, cap_y), (hx + 12, cap_y + 4), (hx + 17 + flick, cap_y - 1), (hx + 19 + flick, cap_y - 8 + fold * 3)], GOLD),
    )
    r.ball(hx, cap_y - 2, 12.4, 4.8, [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[3]], 0)          # the cap's band
    for pts, ramp in pts_cap:
        r.taper(pts, ramp, 7.4, 2.2)
        bell(r, pts[-1][0], pts[-1][1], 2.8)
    return a


def talons(a, foot_, front, ramp, spread=1., size=1.):
    """Three hooked talons from a foot at foot_ (a Painter), curving forward and down."""
    x, y = foot_
    a.ball(x, y + 1.6, 4.4 * size, 2.8 * size, ramp)
    for t in (-1, 0, 1):
        tx = x + 3 + t * 2.8 * spread
        a.poly([(tx - 1.4, y + 1.6), (tx + 1.4, y + 1.2), (tx + 3.2 * (1 if front else -1) + t * .6, max(.2, y - 2.8 * size))], BONE[4], outline=INK[0])


def paradegryphon(clip, n):
    """Lion-bodied parade gryphon with a violet eagle head: a hard yellow glare under a heavy brow, a screaming hooked beak, a crest of red, gold, teal and pink plumes and banded wings with streamers; rears and rakes with its talons, then collapses with its wings spread."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('paradegryphon', (st * 12 - w * 6 + recoil) * .5)
    swing = math.sin(ph) if clip == 'walk' else 0
    sink = sm(dn * 1.4)
    rear = (w * .30 - st * .08) if clip == 'attack' else (-.09 if clip == 'hurt' and n == 1 else 0)
    cy = mix(30 + bob * .5, 12, sink) + (w * 2 if clip == 'attack' else 0)
    r = Rig(a, -16, 3, rear + sink * .04, 0)
    lion = [GOLD[0], GOLD[1], GOLD[2], GOLD[3], GOLD[4]]
    lion_far = [GOLD[0], GOLD[0], GOLD[1], GOLD[2], GOLD[3]]
    # hind legs stay planted while the body rears: lion haunch, heavy paw
    for k, (hxx, shade) in enumerate(((-13, lion_far), (-20, lion))):
        sw = math.sin(ph + k * math.pi) * 6 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + k * math.pi)) * 5 if clip == 'walk' else 0
        hip = r.t(hxx, cy - 4)
        foot_ = (hxx + sw + 2 - sink * (6 if k else -2), 2 + lift)
        knee, _ = arm_ik(hip, foot_, 13, 12, -1)
        knee = (knee[0] - 5, knee[1] + 1)
        a.limb([hip, knee, foot_], shade, 7.4)
        a.ball(foot_[0] + 3, foot_[1] + 2, 6.4, 3, shade)
        for t in (0, 1, 2):
            a.line([(foot_[0] + 6 + t * 1.6, foot_[1] + 1), (foot_[0] + 8 + t * 1.8, max(.4, foot_[1] - .8))], BONE[3], 1)
    # tail: a lion's tail with a plume of scarlet and teal feathers
    sway = math.sin(ph * 1.2) * 3 * (1 - sink)
    tpts = bez((-26, cy), (-42, cy + 4 + sway), (-46 - st * 2, cy + 18 + sway - sink * 12 - dn * 3), 6)
    r.taper(tpts, lion, 5, 3)
    ex, ey = tpts[-1]
    for k, (ang, ramp) in enumerate(((1.7, RED), (2.4, AZURE), (1.1, PINK))):
        r.taper([(ex, ey), (ex + math.cos(ang) * 7, ey + math.sin(ang) * 6), (ex + math.cos(ang) * 14 - 2, ey + math.sin(ang) * 11 + (k - 1) * 2)], ramp, 5, 1.6)
    # body, a pale belly, a barrel of plumage across the chest
    r.ball(0, cy, 26, 14.4, lion, .05)
    r.ball(1, cy - 6.4, 20, 6, [GOLD[1], GOLD[2], GOLD[3], GOLD[4], BONE[4]], 0)
    # front legs: an eagle's, bare yellow scaled shanks ending in huge talons; they rake forward on the strike
    for k, (sxx, shade) in enumerate(((19, [BRASS[0], BRASS[0], BRASS[1], BRASS[2], BRASS[3]]), (13, [BRASS[0], BRASS[1], BRASS[2], BRASS[3], BRASS[4]]))):
        sw = math.sin(ph + k * math.pi + .6) * 6 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + k * math.pi + .6)) * 5 if clip == 'walk' else 0
        shoulder = r.t(sxx, cy - 3)
        tgt = (sxx + 10 + sw, 2 + lift)
        if clip == 'attack':
            raise_ = max(w, 0)
            tgt = r.t(sxx + 12 + st * 32 - w * 4, cy + 6 * raise_ - st * (cy - 6) * (1 if k else .55) + 4 * (1 - st) * raise_ - (1 - st) * 2)
        if sink:
            tgt = (sxx + 16 + 6 * sink + k * 5, 2)
        elbow, _ = arm_ik(shoulder, tgt, 11, 11, 1)
        a.limb([shoulder, elbow, tgt], shade, 5)
        talons(a, tgt, True, shade, 1., 1.1)
    r.ball(15, cy + 6, 13.4, 13.6, [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[4]], .1)
    for k in range(3):                                                  # chest feather scallops
        r.line([(8 + k * 5, cy + 2 - k * .5), (11 + k * 5, cy - 1.4 - k * .5), (14 + k * 5, cy + 2 - k * .5)], PURPLE[1], 1)
    # wings: banded, swept back along the flank; they flare high on the wind-up and strike, and spread flat when it dies
    flare = max(w * .9, st * .8) if clip == 'attack' else 0
    flare = max(flare, sink * 1.1, .6 if clip == 'hurt' and n == 1 else 0)
    root = (3, cy + 10)
    a0 = mix(math.pi - .5, 1.25, flare)
    a1 = mix(math.pi + .05, 2.9, flare)
    feather_fan(r, root, a0, a1, 5 + int(flare * 3), mix(36, 46, flare), [PINK, AZURE, GOLD, PURPLE], 11 - flare * 2, droop=sink * .7 + dn * .5)
    r.ball(2, cy + 8, 15, 10, [PINK[0], PINK[1], PINK[2], PINK[3], PINK[4]], -.15)
    r.ball(0, cy + 7, 8, 4, [AZURE[0], AZURE[1], AZURE[2], AZURE[3], AZURE[3]], -.3)
    flut = math.sin(ph * 1.4) * 3 * (1 - sink)
    for k, (dy, ramp) in enumerate(((16, RED), (13, GOLD))):                        # ribbon streamers tied to the wing
        r.poly([(root[0], cy + dy), (root[0] - 9, cy + dy + 4 + flut), (root[0] - 18, cy + dy - 1 + flut * 1.4), (root[0] - 17, cy + dy - 4 + flut), (root[0] - 8, cy + dy + 1)], ramp[2], outline=ramp[0])
    # neck and head: the strike drops the head and drives it forward; the glare never leaves the target
    hx = 28 + st * 10 - w * 5 + recoil * .4
    hy = cy + 29 - st * 15 - sink * 22 + w * 4
    r.taper([(18, cy + 9), (22 + st * 4, cy + 20 - st * 4), (hx - 2, hy - 4)], [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[4]], 13, 10)
    r.ball(hx, hy, 13, 12, [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[4]], .05)
    # the beak: a hooked upper mandible, a screaming lower one with a dark throat and a red tongue
    open_ = (clip == 'attack' and 3 <= n <= 5) or (clip == 'hurt' and n == 1)
    gap = 1.4 + (9 if open_ else 0) * (1 if clip != 'attack' else min(1, st * 1.4)) + sink * 4
    bx, by = hx + 8, hy - 1.4
    up = bez((bx - 1, by + 4.6), (bx + 13, by + 7), (bx + 16, by - 7), 7)
    r.taper(up + [(bx + 16.4, by - 12)], [AMBER[0], AMBER[1], AMBER[2], AMBER[3], AMBER[4]], 11, 1.4)
    low = bez((bx - 1, by - 2.4 - gap * .2), (bx + 6, by - 4 - gap), (bx + 11, by - 2.6 - gap * 1.1), 5)
    if gap > 3:
        r.poly([(bx - 1, by + .4), (bx + 10, by - .6), (bx + 10, by - 3 - gap), (bx - 1, by - 2 - gap * .3)], OUTLINE)
        r.line([(bx + 2, by - 2 - gap * .4), (bx + 8, by - 2.4 - gap * .75)], CRIMSON[3], 2)
    r.taper(low, [AMBER[0], AMBER[0], AMBER[1], AMBER[2], AMBER[2]], 5, 1.4)
    # raptor glare: a hard yellow eye with a hot black pupil, pinned under a heavy brow that slopes to the beak
    ex, ey = hx + 5, hy + 2.6
    if dying(clip, n):
        r.line([(ex - 2.6, ey - 2.2), (ex + 2.6, ey + 2.2)], OUTLINE, 2)
        r.line([(ex - 2.6, ey + 2.2), (ex + 2.6, ey - 2.2)], OUTLINE, 2)
    else:
        r.ellipse(ex, ey, 4.2, 3.8, OUTLINE)
        r.ellipse(ex, ey, 3.2, 2.8, GOLD[4])
        r.ellipse(ex + .8, ey - .1, 1.4, 1.9, OUTLINE)
    r.poly([(ex - 6, ey + 4.6), (ex + 6.4, ey + .2), (ex + 6.4, ey + 3.8), (ex - 6, ey + 8.8)], VIOLET[0], outline=OUTLINE)
    r.line([(ex - 4, ey + 7), (ex + 5.4, ey + 3)], VIOLET[3], 1)
    # parade crest: four long plumes streaming back and up from the crown
    for k, (ang, ramp, ln) in enumerate(((2.05, RED, 24), (1.75, GOLD, 28), (1.45, AZURE, 25), (2.4, PINK, 20))):
        wob = math.sin(ph * 1.3 + k) * .12 * (1 - sink) - sink * .5 - dn * .4
        base = (hx - 3 + k * 1.6, hy + 8)
        pts = [(base[0] + math.cos(ang + wob + .25 * (j / 4) ** 2) * ln * j / 4, base[1] + math.sin(ang + wob) * ln * j / 4) for j in range(5)]
        r.taper(pts, ramp, 5.4, 1.6)
    return a


PORCELAIN = [BONE[0], BONE[2], BONE[3], BONE[4], WHITE]


def maskcolossus(clip, n):
    """Giant in a violet robe and a gold sash behind a cracked porcelain carnival mask: tall hollow sockets with ember pinpoints, a jagged black screaming mouth and a gold crown; slams both fists down. On death the mask splits in two, the crown rolls off and the body slumps into a heap (rigid: no squash)."""
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('maskcolossus', (st * 8 - w * 4 + recoil) * .5)
    swing = math.sin(ph) if clip == 'walk' else 0
    sink = sm(dn * 1.3)
    hipy = 29 - w * 4 + st * 1 + bob * .4 - sink * 20
    lean = (st * .26 - w * .16) + sink * .95 + (-.12 if clip == 'hurt' and n == 1 else 0)
    r = Rig(a, 0, hipy, -lean, 0)
    stone = [PURPLE[0], PURPLE[1], PURPLE[2], PURPLE[3], PURPLE[4]]
    dark = [VIOLET[0], VIOLET[0], VIOLET[1], VIOLET[2], VIOLET[3]]
    # legs: two thick boots with gold bands; they buckle outward as the giant sinks
    for k, (lx, shade) in enumerate(((-9, dark), (9, stone))):
        sw = math.sin(ph + k * math.pi) * 6 if clip == 'walk' else 0
        lift = max(0, math.sin(ph + k * math.pi)) * 6 if clip == 'walk' else 0
        hip = (lx, hipy + 2)
        foot_ = (lx + sw + sink * lx * 1.1 + (4 if k else -2) * st, 4.5 + lift)
        knee = (mix(hip[0], foot_[0], .5) + (5 if k else -5) * (.3 + sink * 1.4), mix(hip[1], foot_[1], .5))
        a.limb([hip, knee, foot_], shade, 12)
        a.ball(foot_[0] + 3, 4.8 + lift, 9, 4.8, shade)
        a.line([(foot_[0] - 5, 8 + lift), (foot_[0] + 5, 8.6 + lift)], BRASS[2], 2)
    # torso: a wide robe flaring to the hem, a gold sash across it, a great ruffled collar
    r.poly([(-17, hipy + 28), (17, hipy + 28), (22, hipy - 2), (-22, hipy - 2)], dark[1], outline=VIOLET[0])
    r.ball(0, hipy + 15, 19, 17, stone, .05)
    r.ball(-6, hipy + 22, 9, 8, [PURPLE[2], PURPLE[3], PURPLE[4], PURPLE[4], WHITE], .5)
    r.poly([(-18, hipy + 26), (-10, hipy + 30), (19, hipy + 2), (11, hipy - 2)], BRASS[2], outline=BRASS[0])
    r.line([(-14, hipy + 27), (14, hipy + 1)], BRASS[4], 1)
    for k in range(4):
        r.ball(-9 + k * 6, hipy + 22 - k * 6.2, 1.9, 1.9, BRASS)
    nk = hipy + 30
    for k in range(9):
        cx = -18 + k * 4.5
        r.poly([(cx - 3, nk), (cx + 3, nk), (cx, nk - 8)], WHITE if k % 2 else BONE[3], outline=BONE[1])
    # arms: thick rounded limbs ending in huge gloved fists; both fists rise overhead on the wind-up and slam forward on the strike
    shoulders = ((-18, nk - 6), (19, nk - 6))
    for k, (shx, shy) in enumerate(shoulders):
        idle_t = (shx + (-5 if k == 0 else 6) + swing * (3 if k else -3), hipy + 7)
        up_t = (shx * 1.15 + (3 if k else -3), nk + 44)
        hit_t = (shx + 20 + st * 8 + (3 if k else 0), hipy - 2 + (1 - st) * 14)
        target = (mixp(idle_t, up_t, w) if clip == 'attack' else idle_t)
        if clip == 'attack' and st > 0:
            target = mixp(mixp(idle_t, up_t, w), hit_t, min(1, st * 1.25))
        if sink:
            target = mixp(target, (shx + (-14 if k == 0 else 28) * (1 + k * .2), 7 + k * 2), sink)
        sh = r.t(shx, shy)
        tgt = r.t(*target) if not sink else target
        elbow, hand = arm_ik(sh, tgt, 19, 18, -1 if k == 0 else 1)
        a.limb([sh, elbow, hand], stone if k else dark, 11)
        a.ball(*sh, 11.5, 11, stone if k else dark)                                    # the pauldron
        a.ball(hand[0] + 1, hand[1], 10.6, 10, PORCELAIN if k else [BONE[0], BONE[1], BONE[2], BONE[3], BONE[3]])
        a.line([(hand[0] - 4, hand[1] + 8), (hand[0] - 4, hand[1] - 8)], BRASS[1], 3)
        for f in (-1, 0, 1):
            a.line([(hand[0] + 3, hand[1] + f * 3.2), (hand[0] + 9, hand[1] + f * 3.4)], BONE[1], 1)
    # head: a huge egg-shaped carnival mask
    hx, hy = 2 + st * 4 - w * 2, nk + 25 - st * 5 + w * 3
    fall = max(0, dn - .3) / .7
    hxx, hyy = r.t(hx, hy)
    hyy -= sm(dn * 1.2) * 18 * (1 if dn > 0 else 0)
    hxx += sink * 12
    crown_off = sm(dn * 1.5)
    split = dn > .3
    if not split:
        a.ball(hxx, hyy, 16, 20, PORCELAIN, -.05)
        a.line([(hxx - 2, hyy + 19), (hxx, hyy + 12), (hxx - 3, hyy + 6), (hxx + 1, hyy - 1)], VIOLET[0] if dn < .1 else OUTLINE, 1)  # the seam
    else:
        gapx = 3 + fall * 14
        a.ball(hxx - gapx * .5 - 3, hyy - fall * 4, 8, 19, PORCELAIN, -.08 - fall * .5)
        a.ball(hxx + gapx * .5 + 3, hyy - fall * 9, 8, 19, [BONE[0], BONE[1], BONE[2], BONE[3], BONE[4]], .1 + fall * .6)
    # painted gold trim round the rim; a cracked cheek
    if not split:
        a.line([(hxx - 12, hyy + 4), (hxx - 15, hyy - 6), (hxx - 11, hyy - 14)], BRASS[2], 2)
        a.line([(hxx + 12, hyy + 4), (hxx + 15, hyy - 6), (hxx + 11, hyy - 14)], BRASS[2], 2)
    # tall hollow sockets, slanted angrily, with an ember pinpoint deep inside
    ex_off = (-6.4, 7.4)
    if not split:
        for sgn, ox in ((1, ex_off[1]), (-1, ex_off[0])):
            ex, ey = hxx + ox, hyy + 4
            a.poly([(ex - 4.4, ey + 8 - sgn * 1.2), (ex + 4.6, ey + 4.6 + sgn * 1.6), (ex + 4, ey - 7), (ex - 4, ey - 6)], OUTLINE)
            if dn < .1 and not (clip == 'hurt' and n == 0):
                a.ellipse(ex + .4, ey - .8, 1.5, 1.5, RED[3])
            a.line([(ex - 5, ey + 9.6 - sgn * 1.4), (ex + 5.4, ey + 6 + sgn * 1.8)], VIOLET[0], 2)
        a.poly([(hxx + 1, hyy - 2), (hxx + 3.6, hyy - 8.6), (hxx - 1.4, hyy - 8)], OUTLINE)               # nose slit
        scream = 3 + st * 5 + w * 2 + (3 if clip == 'hurt' and n == 1 else 0) + dn * 6
        mouth = [(hxx - 9.6, hyy - 11), (hxx - 5, hyy - 12 - scream), (hxx - 1, hyy - 13.4 - scream), (hxx + 4, hyy - 12.4 - scream), (hxx + 9.6, hyy - 11), (hxx + 4, hyy - 10), (hxx - 1, hyy - 10.2), (hxx - 5, hyy - 9.6)]
        a.poly(mouth, OUTLINE)
        for k in range(5):
            tx = hxx - 7.4 + k * 3.7
            a.poly([(tx - 1.2, hyy - 10.2), (tx + 1.2, hyy - 10.2), (tx, hyy - 13 - scream * .5)], WHITE)
        for k in range(4):
            tx = hxx - 5.6 + k * 3.7
            a.poly([(tx - 1, hyy - 12.4 - scream), (tx + 1, hyy - 12.4 - scream), (tx, hyy - 10 - scream * .45)], BONE[3])
    else:
        gapx = 3 + fall * 14
        for sgn, cx in ((-1, hxx - gapx * .5 - 3), (1, hxx + gapx * .5 + 3)):
            ey = hyy + 4 - (fall * 4 if sgn < 0 else fall * 9)
            a.poly([(cx - 3, ey + 8), (cx + 3, ey + 6), (cx + 3.4, ey - 6), (cx - 3, ey - 5)], OUTLINE)
            a.line([(cx - 4, ey - 11), (cx + 3, ey - 11), (cx + 4, ey - 14)], OUTLINE, 3)
            for k in range(3):
                tx = cx - 3 + k * 3
                a.poly([(tx - 1, ey - 11), (tx + 1, ey - 11), (tx, ey - 8.4)], WHITE)
    # crown: a gold band of points and red gems; it rolls off the head on death
    cx0, cy0 = hxx + crown_off * 20, hyy + 18 - crown_off * (16 + sink * 4)
    cy0 = max(cy0, 6) if crown_off > .5 else cy0
    for k in range(5):
        px = cx0 - 11 + k * 5.5
        h = 10 - abs(k - 2) * 1.8
        a.poly([(px - 3, cy0), (px + 3, cy0), (px, cy0 + h)], BRASS[2], outline=BRASS[0])
        a.ball(px, cy0 + h + .6, 1.9, 1.9, RED)
    a.ball(cx0, cy0 - .6, 13.4, 3.4, BRASS)
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
        np.savez_compressed(ROOT / f'scripts/ribbonwild_slime_{kind}_raw.npz', **data[kind])
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
        np.savez_compressed(ROOT / f'scripts/ribbonwild_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'ribbonwild_{kind}.png'


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    assert live['kinds'][-3:] == VILLAGERS, 'villager entries moved'
    villagers = {k: (live['sprites'][k], live['tops'][k]) for k in VILLAGERS}
    meta = json.loads(json.dumps(live))
    meta['artStyle'] = 'ribbonwild-slime'
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
