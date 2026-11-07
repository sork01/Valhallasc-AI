#!/usr/bin/env python3
"""Astralhollow's three elites (zone shapes pilot): native PixelFlow sources, each with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames per kind. Each has its own
body plan, its own eyes and its own death (not the Bifrost three's lunge, ghost and shatter):
  cometmaw      The Cometmaw (level 42, quest): a low hunched hound of blue-white ice, shoulders high, head slung low and nearly all mouth, a
                ring of icicle fangs, two pinpoint embers for eyes. A comet-tail of fire streams from its nape and is the biggest thing on the
                sprite. Winds up by dropping and opening the maw; the strike is a burning rush, tail stretched out behind. Dies like a fire going
                out: the plume gutters to embers, the legs fold, the body slumps and cracks with frost, the jaw hangs.
  eclipsequeen  The Eclipse Queen (level 44, quest): a rooted bark dryad, her skirt a spread of roots that shuffle when she walks, a black sun with a
                gold corona hung behind her head, a crown of branch-antlers, two black eclipse eyes ringed in gold. Winds up with both arms raised
                and the corona flaring, then sweeps a branch-fingered arm across. Dies by withering: the leaves fall, the body sags and bends, the
                sun goes out and she is left a dry husk on her roots.
  orbitwarden   The Orbit Warden (level 45, no quest): a star-metal sentinel, two pillar legs, a bell of a torso with a glass lantern for a heart, one
                great lens for an eye under a crescent crest, three bronze rings orbiting it. Winds up with the rings raised over its head and
                slams them down in front in a ring of dust. Dies kneeling: the knees buckle, the rings fall off and roll, the lantern dims.
The manifest is client/assets/astralelites.txt. The shading helpers are copied from bifrost_elite_redraw.py (importing it would add 63 palette colours).
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import kindframe
import lapis_slime_redraw as L
from lapis_slime_redraw import (BasePainter, OUTLINE, BONE, PEARL, clamp01, curves, dying, settle, polar, mix, mixp, sm, bez, dust, old, Rig)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/astral-elites'
REGISTRY = ROOT / 'scripts/astral_elite_sources.txt'
MANIFEST = ASSETS / 'astralelites.txt'
PREFIX = 'valhallasc_astral_elite_'
KINDS = ['cometmaw', 'eclipsequeen', 'orbitwarden']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(cometmaw=(192, 140, 84, 132), eclipsequeen=(160, 192, 80, 186), orbitwarden=(160, 192, 80, 186))
SCALE = dict(cometmaw=.6, eclipsequeen=.55, orbitwarden=.58)
FLYING = ()
_mine = [
    '#0a1630', '#1f4a8a', '#4a96d8', '#a8e0ff', '#f4fcff',   # FROST (the hound's ice-fur)
    '#3a0c08', '#a02a10', '#f06a1c', '#ffb54a', '#fff0b0',   # FLAME (the plume, the ember eyes)
    '#2a0414', '#7a1030', '#d03a50', '#ff8a80', '#ffd8d0',   # INNER (the maw)
    '#0c0a08', '#2a1c14', '#503424', '#84583a', '#b88a5c',   # BARK
    '#08180c', '#16401c', '#2c7a30', '#62b84a', '#b4f080',   # LEAF
    '#02020a', '#0c0a1c', '#1a1838', '#2a2658', '#403a80',   # VOID (the black sun)
    '#6a4a10', '#c8921c', '#ffd24a', '#fff2a8', '#fffff0',   # CORONA (gold, the lantern light)
    '#2a0a3a', '#5a1a78', '#9a3ac8', '#d08af0', '#f4d8ff',   # VIOLET (blossoms)
    '#0e1018', '#2c3040', '#586070', '#98a0b4', '#d8dcec',   # STEEL (star-metal)
    '#2a1604', '#74421a', '#c08034', '#f0c060', '#fff0b0',   # BRONZE (the rings)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
FROST, FLAME, INNER, BARK, LEAF, VOID, CORONA, VIOLET, STEEL, BRONZE = [_i[5 * k:5 * k + 5] for k in range(10)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = SCALE.get(kind, 1.)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax + dx * self.S

    def pos(self, x, y):
        return round(self.cx + x * self.S), min(round(self.ay - y * self.S), self.ay + 4)      # nothing sinks more than four rows under the ground

    def ellipse(self, x, y, rx, ry, col):
        super().ellipse(x, y, rx * self.S, ry * self.S, col)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width * self.S)))

    def ball(self, x, y, rx, ry, ramp, ang=0.0):
        super().ball(x, y, rx * self.S, ry * self.S, ramp, ang)


# ---- shading toolkit (copied from bifrost_elite_redraw.py) ----------------------------------------------------------------------
def smooth(pts, n=5, closed=True):
    P = list(pts)
    m = len(P)
    out = []
    for i in range(m if closed else m - 1):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        if not closed:
            p0 = P[max(i - 1, 0)]
            p3 = P[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            out.append(tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    return out


def capsule(p, q, w0, w1, caps=5):
    dx, dy = q[0] - p[0], q[1] - p[1]
    ln = math.hypot(dx, dy) or 1.
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    pts = [(p[0] + nx * w0 / 2, p[1] + ny * w0 / 2), (q[0] + nx * w1 / 2, q[1] + ny * w1 / 2)]
    for k in range(1, caps):
        a = math.pi * k / caps
        pts.append((q[0] + (nx * math.cos(a) + ux * math.sin(a)) * w1 / 2, q[1] + (ny * math.cos(a) + uy * math.sin(a)) * w1 / 2))
    pts += [(q[0] - nx * w1 / 2, q[1] - ny * w1 / 2), (p[0] - nx * w0 / 2, p[1] - ny * w0 / 2)]
    for k in range(1, caps):
        a = math.pi * k / caps
        pts.append((p[0] - (nx * math.cos(a) - ux * math.sin(a)) * w0 / 2, p[1] - (ny * math.cos(a) - uy * math.sin(a)) * w0 / 2))
    return pts


def shaded(a, pts, ramp, light=(-.6, -.8), base=.58, contrast=1., outline=OUTLINE, edge=True, grain=0.):
    P = [a.pos(*p) for p in pts]
    m = Image.new('1', (a.w, a.h), 0)
    ImageDraw.Draw(m).polygon(P, fill=1)
    mk = np.array(m, bool)
    ys, xs = np.nonzero(mk)
    if not xs.size:
        return
    cx, cy = xs.mean(), ys.mean()
    proj = (xs - cx) * light[0] + (ys - cy) * light[1]
    ext = max(1e-6, np.abs(proj).max())
    v = base + .5 * contrast * proj / ext
    thr = (((xs % 4) * 5 + (ys % 4) * 3) % 16) / 16. - .5
    v += thr * .22
    if grain:
        v += ((np.sin(xs * 12.9898 + ys * 78.233) * 43758.5453) % 1 - .5) * grain
    idx = np.clip((v * (len(ramp) - 1) + .5).astype(int), 0, len(ramp) - 1)
    arr = np.array(a.im)
    rows = np.array(ramp)[idx]
    inner = ndimage.binary_erosion(mk, iterations=1)
    arr[ys, xs] = rows
    if edge:
        rim = mk & ~inner
        ry, rx = np.nonzero(rim)
        lit = ((rx - cx) * light[0] + (ry - cy) * light[1]) > 0
        arr[ry[~lit], rx[~lit]] = ramp[0]
        if outline is not None:
            arr[ry[lit], rx[lit]] = outline
    a.im.paste(Image.fromarray(arr, 'P'), mask=Image.fromarray((mk * 255).astype(np.uint8)))


def glow(a, x, y, r, ramp, strength=1.):
    px, py = a.pos(x, y)
    R = max(1., r * a.S)
    arr = np.array(a.im)
    for yy in range(max(0, int(py - R) - 1), min(a.h, int(py + R) + 2)):
        for xx in range(max(0, int(px - R) - 1), min(a.w, int(px + R) + 2)):
            d = math.hypot(xx - px, yy - py) / R
            if d > 1:
                continue
            v = (1 - d) ** 1.4 * strength
            thr = (((xx % 4) * 5 + (yy % 4) * 3) % 16) / 16.
            if v > thr * .9 + .08:
                arr[yy, xx] = ramp[min(len(ramp) - 1, int(v * len(ramp)))]
    a.im.paste(Image.fromarray(arr, 'P'))


def tapered(a, spine, w0, w1, ramp, base=.55, contrast=1., n=None, edge=True):
    """A shape that follows a spine (list of points) from width w0 to w1."""
    n = len(spine)
    left, right = [], []
    for i, p in enumerate(spine):
        q = spine[min(i + 1, n - 1)]
        r = spine[max(i - 1, 0)]
        dx, dy = q[0] - r[0], q[1] - r[1]
        ln = math.hypot(dx, dy) or 1.
        nx, ny = -dy / ln, dx / ln
        wd = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((p[0] + nx * wd, p[1] + ny * wd))
        right.append((p[0] - nx * wd, p[1] - ny * wd))
    shaded(a, left + right[::-1], ramp, base=base, contrast=contrast, edge=edge)


def ring_arc(a, cx, cy, rx, ry, tilt, t0, t1, col, width=1, steps=24):
    pts = []
    for k in range(steps + 1):
        t = t0 + (t1 - t0) * k / steps
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)))
    a.line(pts, col, width)
    return pts


# ---- the Cometmaw ---------------------------------------------------------------------------------------------------------------
def cometmaw(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lie = sm(clamp01((dn - .05) * 1.12))
    walk = clip == 'walk'
    rush = st * 22 - w * 8 + recoil
    a = Painter('cometmaw', rush)
    hip = 54 + bob * .5 - lie * 44 - w * 8
    sh = 68 + bob * .5 - lie * 50 - w * 14 + st * 3
    flame = max(0., 1. - dn * 1.25)
    flick = math.sin(ph * 2.4 + n)
    # --- the plume: a comet-tail of fire off the nape, longer on the strike, the biggest shape of the sprite
    length = (98 + st * 52 - w * 14) * flame
    bx, by = 4, sh + 14
    for layer, (wd, rampbase) in enumerate(((58, .3), (45, .45), (31, .62), (17, .82))):
        spine = []
        for k in range(8):
            t = k / 7
            spine.append((bx - t * length * (.78 + st * .12), by + t * length * .5 * (1 - st * .45) + t * t * 22 * (1 - st * .6) + math.sin(t * 5 + ph * 1.7 + layer) * 6 * t * flame))
        if length > 6:
            tapered(a, spine, wd * flame + 2, 2, FLAME, base=rampbase, contrast=.9, edge=(layer == 0))
    if flame > .15:
        for k in range(5):                                                  # sparks and cinders thrown off the tail
            t = .25 + k * .17
            sx = bx - t * length * .8 - 6 * math.sin(ph + k)
            sy = by + t * length * .42 + 8 + math.cos(ph * 1.3 + k * 2) * 6
            a.ball(sx, sy, 2.2, 2.2, FLAME[2:])
    if dn > .2:
        for k in range(int(6 * dn)):                                        # embers and a thread of smoke left behind
            a.ball(-34 - k * 9 + dn * 6, hip + 8 + k * 5 + (k % 2) * 3, 2, 2, FLAME[1:4])
    # --- legs
    def leg(x, front, far):
        p = (0 if front else math.pi) + (math.pi if far else 0)
        sw = math.sin(ph + p) * 9 if walk else 0
        lift = max(0, math.cos(ph + p)) * 7 if walk else 0
        if clip == 'attack':
            sw = (st * (16 if front else -12) - w * (6 if front else -4)) * (.7 if far else 1)
            lift = st * (10 if front else 4) * (0 if far else 1)
        top = (x + 2, (sh if front else hip) - 6)
        if front:
            knee = (x - 4 + sw * .4 + lie * 12, sh * .5 + lift * .3 - lie * 8)
            ank = (x + 2 + sw * .8 + lie * 20, 11 + lift * .6)
        else:
            knee = (x + 11 + sw * .3 - lie * 6, hip * .52 + 3 + lift * .3 - lie * 6)
            ank = (x - 5 + sw * .8 - lie * 14, 12 + lift * .6)
        foot = (ank[0] + 4, 3 + lift)
        base = .32 if far else .6
        shaded(a, capsule(top, knee, 16, 10, 4), FROST, base=base, contrast=.9)
        shaded(a, capsule(knee, ank, 10, 6, 4), FROST, base=base, contrast=.9)
        shaded(a, smooth([(ank[0] - 4, ank[1] + 1), (ank[0] + 5, ank[1] + 2), (foot[0] + 10, foot[1] + 2), (foot[0] + 10, foot[1] - 2.5), (foot[0] - 4, foot[1] - 2.5)], 3), FROST, base=base, contrast=.8)
        for k in range(3):
            a.line([(foot[0] + 8 + k * 2.4, foot[1] + .5), (foot[0] + 13 + k * 2.4, foot[1] - 1.5)], FROST[4], 1)
    leg(-26, False, True)
    leg(26, True, True)
    # --- the hunched body: high shoulders, a low rump, a back of icicle spines
    torso = smooth([(-50, hip - 4), (-44, hip + 16), (-20, hip + 22), (0, sh + 10), (24, sh + 16), (44, sh + 4), (46, sh - 16), (30, sh - 26), (6, hip - 14), (-20, hip - 12), (-42, hip - 14)], 5)
    shaded(a, torso, FROST, base=.52 - lie * .12, contrast=1.1)
    shaded(a, smooth([(-46, hip - 2), (-34, hip + 12), (-22, hip - 2), (-36, hip - 12)], 4), FROST, base=.66, contrast=.4, edge=False)     # the haunch
    for k in range(7):
        t = k / 6
        px, py = mixp((-34, hip + 20), (22, sh + 14), t)
        ln = 14 + 9 * math.sin(t * 3.1) - lie * 6
        shaded(a, [(px - 4, py - 1), (px + 4, py - 1), (px - 6 - st * 5, py + ln)], FROST[2:] + [FROST[4]], base=.6 + .25 * (k % 2), contrast=.9)
    for k in range(3):                                                  # frost cracks across the flank
        x0 = -26 + k * 20
        a.line([(x0, hip + 14), (x0 + 6, hip + 4), (x0 + 2, hip - 4), (x0 + 9, hip - 10)], FROST[0], 1)
    # --- the head: slung low, mostly mouth
    gape = {'idle': .42 + .1 * math.sin(ph), 'walk': .5, 'hurt': .55 if n == 1 else .2, 'die': .3 + lie * .55, 'attack': w * 1.05 + st * .6}[clip]
    hx, hy = 40 + rush * .15 + st * 6 - lie * 6, sh - 22 - w * 8 - lie * 14 + (st * -3)
    neck = smooth([(24, sh + 12), (44, sh + 4), (hx + 2*1.6, hy + 18*1.6), (hx + 10*1.6, hy - 4*1.6), (46, sh - 16), (26, sh - 22)], 5)
    shaded(a, neck, FROST, base=.56, contrast=1., edge=False)
    pivot = (hx + 2*1.6, hy - 2*1.6)
    ang = gape * .62
    def rot(p):
        x, y = p[0] - pivot[0], p[1] - pivot[1]
        return pivot[0] + x * math.cos(ang) + y * math.sin(ang), pivot[1] - x * math.sin(ang) + y * math.cos(ang)
    low = [rot(p) for p in [(hx + 2*1.6, hy - 2*1.6), (hx + 30*1.6, hy - 5*1.6), (hx + 58*1.6, hy - 4*1.6), (hx + 54*1.6, hy - 15*1.6), (hx + 30*1.6, hy - 21*1.6), (hx + 8*1.6, hy - 16*1.6)]]
    # the dark of the throat and the tongue, between the jaws
    if gape > .1:
        shaded(a, [(hx + 4*1.6, hy + 2*1.6), (hx + 58*1.6, hy + 1*1.6), (low[2][0], low[2][1] + 2), (low[1][0], low[1][1] + 2), (low[0][0], low[0][1] + 1)], INNER, base=.28, contrast=.5, edge=False)
        a.poly([(hx + 14*1.6, low[1][1] + 4), (hx + 44*1.6, low[2][1] + 3), (hx + 34*1.6, low[1][1] + 9), (hx + 18*1.6, low[1][1] + 8)], INNER[2])
        if clip == 'attack' and w + st > .5 and flame > .3:                     # fire welling up the throat on the rush
            glow(a, hx + 30*1.6, hy - 6*1.6, 20 + st * 10, FLAME, .9)
    shaded(a, low, FROST, base=.38 - lie * .1, contrast=.8)
    skull = smooth([(hx - 18*1.6, hy + 8*1.6), (hx - 6*1.6, hy + 21*1.6), (hx + 12*1.6, hy + 20*1.6), (hx + 30*1.6, hy + 12*1.6), (hx + 52*1.6, hy + 6*1.6), (hx + 62*1.6, hy + 1*1.6), (hx + 60*1.6, hy - 4*1.6), (hx + 38*1.6, hy - 5*1.6), (hx + 14*1.6, hy - 6*1.6), (hx - 10*1.6, hy - 4*1.6)], 4)
    shaded(a, skull, FROST, base=.62 - lie * .1, contrast=1.1)
    a.poly([(hx + 12*1.6, hy - 5*1.6), (hx + 60*1.6, hy - 4*1.6), (hx + 60*1.6, hy - 3*1.6)], OUTLINE)
    for k in range(7):                                                  # icicle fangs: long above, shorter below, no two alike
        fx = hx + 12*1.6 + k * 6.6*1.6
        ln = 11 + (k * 5 % 7) + gape * 4
        a.poly([(fx, hy - 4*1.6), (fx + 5, hy - 4*1.6), (fx + 2, hy - 4*1.6 - ln*1.3)], FROST[4])
        a.line([(fx + 1, hy - 4*1.6), (fx + 1.2, hy - 4*1.6 - ln + 2)], FROST[2], 1)
    for k in range(5):
        fx = low[0][0] + 22 + k * 13
        fy = low[1][1] + 2
        a.poly([(fx, fy), (fx + 3.2, fy), (fx + 1.6, fy + 8 + (k % 2) * 4 + gape * 3)], FROST[3])
    # --- the eyes: two pinpoint embers set high on the skull, trailing a thread of sparks back along the brow
    for ex, ey in ((hx + 22*1.6, hy + 14*1.6), (hx + 8*1.6, hy + 16*1.6)):
        if dying(clip, n, 2):
            a.line([(ex - 2, ey), (ex + 2, ey)], OUTLINE, 1)
        else:
            glow(a, ex, ey, 7, FLAME, .9)
            a.ball(ex, ey, 2.4, 2.4, FLAME[2:])
            a.line([(ex, ey), (ex - 8, ey + 4 + flick)], FLAME[2], 1)
    a.line([(hx + 2*1.6, hy + 24*1.6), (hx + 16*1.6, hy + 19*1.6), (hx + 30*1.6, hy + 17*1.6)], OUTLINE, 2)      # a hard brow over both
    leg(-23, False, False)
    leg(29, True, False)
    if clip == 'attack' and n in (6, 7):
        for k in range(3):
            dust(a, -36 + k * 9, 4 + (k % 2) * 3, 3.2 - k * .5, PEARL)
    return a


# ---- the Eclipse Queen ----------------------------------------------------------------------------------------------------------
def eclipsequeen(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    wilt = sm(clamp01(dn * 1.05))
    walk = clip == 'walk'
    a = Painter('eclipsequeen', st * 4 - w * 3 + recoil)
    sag = 1 - .5 * wilt                                                 # the whole body shortens as she withers
    base_y = 40 * sag
    hov = bob * .5
    R = Rig(a, 0, base_y, -wilt * .38 + st * .08 - w * .05)
    T = lambda pts: [R.t(*p) for p in pts]
    top = 150 * sag + hov
    # --- the roots she walks on: a spread skirt of root-legs, tips lifting in turn
    for k in range(8):
        side = -1 if k < 4 else 1
        j = k % 4
        reach = 28 + j * 17
        lift = (max(0, math.sin(ph * 1.4 + k * .9)) * 9) if walk else 0
        spread = 1 + wilt * .35
        root = [(side * 8, base_y + 8), (side * (reach * .5) * spread, base_y - 4 + j * -2 + lift * .3), (side * reach * spread, 8 + lift * .6), (side * (reach + 9) * spread, 1 + lift)]
        tapered(a, smooth(root, 4, closed=False), 11 - j, 3, BARK, base=.35 + .08 * j, contrast=.9, edge=False)
    # --- the black sun behind the head, its gold corona turning; it flares on the wind-up and the strike, and goes out as she dies
    sun = 1 - wilt * .95
    sx, sy = 0, top + 34 * sag
    rad = (33 + w * 5 + st * 12) * sun
    if sun > .05:
        flare = w * .6 + st
        for k in range(18):
            ang0 = k * math.tau / 18 + ph * .12 + (.07 if k % 2 else 0)
            ln = rad * (1.38 + .3 * (k % 3) / 2 + flare * .45)
            a.poly([(sx + math.cos(ang0 - .1) * rad * .96, sy + math.sin(ang0 - .1) * rad * .96), (sx + math.cos(ang0) * ln, sy + math.sin(ang0) * ln),
                    (sx + math.cos(ang0 + .1) * rad * .96, sy + math.sin(ang0 + .1) * rad * .96)], CORONA[2 + (k % 2)])
        glow(a, sx, sy, rad * 1.5, CORONA, .6 + flare * .3)
        a.ball(sx, sy, rad + 3, rad + 3, CORONA[1:4])
        a.ball(sx, sy, rad, rad, [VOID[0], VOID[0], VOID[1]])
        a.ball(sx + rad * .28, sy - rad * .1, rad * .6, rad * .75, [VOID[0], VOID[0], VOID[0]])
    # --- the bark body: a slim trunk of a torso, ribbed, with moss for a gown over the root flare
    gown = smooth(T([(-20, top - 40), (20, top - 40), (34, base_y + 30), (46, base_y + 6), (20, base_y - 6), (-20, base_y - 6), (-46, base_y + 6), (-34, base_y + 30)]), 4)
    shaded(a, gown, LEAF, base=.2, contrast=.9, edge=False)
    for k in range(6):
        x0 = -28 + k * 11
        a.line(T([(x0 * .6, top - 38), (x0 * .9, base_y + 20), (x0 * 1.2, base_y - 2)]), LEAF[1], 1)
    for k in range(5):                                                  # ragged leaf-hem
        hx_ = -40 + k * 20
        shaded(a, T([(hx_ - 6, base_y + 4), (hx_ + 6, base_y + 4), (hx_ + 1, base_y - 8 - (k % 2) * 4)]), LEAF, base=.5, contrast=.8)
    trunk = smooth(T([(-18, top - 54), (18, top - 54), (24, top - 10), (14, top + 14), (-14, top + 14), (-24, top - 10)]), 4)
    shaded(a, trunk, BARK, base=.5, contrast=1.15)
    for k in range(4):                                                  # ribs of grain
        a.line(T([(-14, top - 36 + k * 11), (0, top - 31 + k * 11), (14, top - 36 + k * 11)]), BARK[1], 1)
    a.line(T([(0, top - 44), (-2, top - 20), (3, top + 8)]), BARK[0], 1)
    # --- arms: bark capsules ending in branch-fingers; both raised on the wind-up, the near one sweeps across on the strike
    def arm(s, far):
        sh_ = R.t(s * 26, top + 6)
        idle = (s * 54, top - 54 + sag * 10 + math.sin(ph + s) * 3 * (clip in ('idle', 'walk')))
        up = (s * 40, top + 56)
        sweep = (s * 78 + 10, top - 74) if not far else (s * 52, top + 30)
        hand = mixp(mixp(idle, up, w), sweep, st)
        droop = (s * 40, 24 * sag)
        hand = mixp(hand, droop, wilt)
        hand = R.t(*hand) if False else hand
        el = ((sh_[0] + hand[0]) / 2 + s * 10, (sh_[1] + hand[1]) / 2 + (-6 if clip == 'attack' else 4))
        base = .38 if far else .6
        shaded(a, capsule(sh_, el, 13, 10, 4), BARK, base=base, contrast=1.)
        shaded(a, capsule(el, hand, 10, 6, 4), BARK, base=base, contrast=1.)
        for k in range(4):                                              # branch-fingers: long, forked, no leaves while dying
            ang0 = math.atan2(hand[1] - el[1], hand[0] - el[0]) + (k - 1.5) * .42
            ln = 24 - abs(k - 1.5) * 5 - wilt * 8
            tip = (hand[0] + math.cos(ang0) * ln, hand[1] + math.sin(ang0) * ln)
            a.line([hand, tip], BARK[0], 2)
            a.line([(hand[0], hand[1] + .6), (tip[0], tip[1] + .6)], BARK[3], 1)
            fork = (tip[0] + math.cos(ang0 + .6) * 7, tip[1] + math.sin(ang0 + .6) * 7)
            a.line([tip, fork], BARK[2], 1)
            if wilt < .5 and k % 2 == 0:
                a.ball(fork[0], fork[1], 2, 1.6, LEAF[2:])
    arm(-1, True)
    # --- the head: a bark mask under a crown of branch-antlers, moss hair, two black eyes ringed in gold
    hc = top + 34 * sag
    for s in (-1, 1):
        for j, (ax_, ay_, bx_, by_) in enumerate(((16, 14, 34, 40), (22, 6, 46, 20))):
            bend = math.sin(ph * .6 + j) * 1.5 * (clip in ('idle', 'walk')) - wilt * 14
            p0 = R.t(s * ax_, hc + ay_)
            p1 = (R.t(s * bx_, hc + by_)[0], R.t(s * bx_, hc + by_)[1] + bend)
            a.line([p0, p1], BARK[0], 4)
            a.line([p0, p1], BARK[3], 2)
            for k in range(3):
                t = .3 + k * .3
                q = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
                tw = (q[0] + s * 8, q[1] + 10 - wilt * 6)
                a.line([q, tw], BARK[2], 1)
                if wilt < .6:
                    a.ball(tw[0], tw[1], 2.2, 1.8, VIOLET[2:] if k % 2 else LEAF[2:])
    for k in range(5):                                                  # moss hair, hanging
        hxx = -14 + k * 7
        a.line(T([(hxx, hc + 14), (hxx * 1.2, hc - 14), (hxx * 1.35 + math.sin(ph + k) * 1.2, hc - 34 + wilt * 8)]), LEAF[2 if k % 2 else 1], 2)
    face = smooth(T([(-15, hc + 16), (15, hc + 16), (17, hc - 2), (9, hc - 20), (-9, hc - 20), (-17, hc - 2)]), 4)
    shaded(a, face, BARK, base=.6, contrast=1.1)
    for ex in (-7.5, 7.5):
        e = R.t(ex, hc + 2)
        if dying(clip, n, 2):
            a.line([(e[0] - 3, e[1]), (e[0] + 3, e[1])], OUTLINE, 1)
        else:
            a.ball(e[0] - a.cx + 0, 0, 0, 0, VOID) if False else None
            a.poly([(e[0] - 5, e[1]), (e[0], e[1] + 4.5), (e[0] + 5, e[1]), (e[0], e[1] - 4.5)], CORONA[2])
            a.poly([(e[0] - 3.6, e[1]), (e[0], e[1] + 3), (e[0] + 3.6, e[1]), (e[0], e[1] - 3)], VOID[0])
    a.line(T([(-5, hc - 12), (0, hc - 14), (5, hc - 12)]), BARK[0], 1)      # a thin crack of a mouth
    a.line(T([(-9, hc + 12), (-5, hc + 6)]), BARK[0], 1)
    arm(1, False)
    # --- leaves falling as she withers, and on the sweep
    if clip == 'die':
        rng = np.random.RandomState(5 + n)
        for k in range(int(4 + 12 * wilt)):
            x0 = rng.uniform(-60, 60)
            y0 = max(4, rng.uniform(40, 220) * (1 - wilt * .8) - wilt * rng.uniform(20, 90))
            a.poly([(x0, y0), (x0 + 3, y0 + 1.6), (x0 + 6, y0), (x0 + 3, y0 - 1.6)], LEAF[1 + k % 3])
    if clip == 'attack' and n in (4, 5):                                # the strike throws a ring of gold off the sweep
        for k in range(3):
            r = 30 + k * 12 + (n - 4) * 10
            ring_arc(a, 40, top - 40, r, r * .5, 0, -1.2, 1.2, CORONA[3 if k % 2 else 2], 2 if k == 0 else 1)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, 36 + k * 9, 4 + (k % 2) * 3, 3 - k * .4, PEARL)
    return a


# ---- the Orbit Warden -----------------------------------------------------------------------------------------------------------
def orbitwarden(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lie = sm(clamp01((dn - .08) * 1.15))
    walk = clip == 'walk'
    a = Painter('orbitwarden', st * 5 - w * 4 + recoil)
    knee = lie                                                          # the knees buckle
    hip = 82 * (1 - .62 * knee) + bob * .5 - w * 4 + st * 5 + (math.sin(ph * 2) * 1.5 if walk else 0)
    R = Rig(a, 0, hip, -w * .05 + st * .1 + lie * .36)
    T = lambda pts: [R.t(*p) for p in pts]
    # --- legs: two pillars of star-metal on broad block feet, bronze rings at the knees
    for x, far in ((-22, True), (22, False)):
        sw = (math.sin(ph + (math.pi if far else 0)) * 9) if walk else 0
        lift = (max(0, math.cos(ph + (math.pi if far else 0))) * 7) if walk else 0
        fx, fy = x + sw + knee * (22 if not far else -22), 3 + lift
        kx = x + knee * (18 if not far else -18)
        ky = hip * .46
        base = .36 if far else .58
        shaded(a, [(x - 14, hip + 6), (x + 14, hip + 6), (kx + 15, ky), (fx + 16, fy + 14), (fx - 16, fy + 14), (kx - 15, ky)], STEEL, base=base, contrast=1.1)
        shaded(a, [(kx - 16, ky + 5), (kx + 16, ky + 5), (kx + 16, ky - 5), (kx - 16, ky - 5)], BRONZE, base=base + .06, contrast=1.2)
        shaded(a, [(fx - 22, fy + 14), (fx + 22, fy + 14), (fx + 25, fy), (fx - 25, fy)], STEEL, base=base + .08, contrast=1.2)
    # --- the rings orbit the torso: the back halves are drawn before the body, the front halves after
    cy0 = hip + 70
    rings = []
    for k, (rx, ry, tilt, speed) in enumerate(((78, 15, .1, 1.), (64, 13, -.16, -1.3), (50, 11, .24, 1.7))):
        up_ = w * (130 - k * 26)
        cx_, cy_, rxx, ryy = 0., cy0 + (k - 1) * 22 + up_, rx * (1 - w * .35), ry * (1 + w * .3)
        if clip == 'attack' and st > 0:
            cx_, cy_ = 24. * st + 0, mix(cy_, 34 + k * 6, st)
            rxx, ryy = rx * (1 - st * .25), ry * (1 + st * .8)
            tilt *= 1 - st
        if clip == 'die':                                               # they drop, flatten and roll away from the body
            cx_ = mix(0., (-40 + k * 24), lie)
            cy_ = mix(cy_, 6 + k * 4, lie)
            ryy = ry * (1 - lie * .35)
            rxx = rx * (1 - lie * .3)
            tilt *= 1 - lie
        rings.append((cx_, cy_, rxx, ryy, tilt, ph * speed))
    def draw_rings(front):
        for cx_, cy_, rxx, ryy, tilt, spin in rings:
            t0, t1 = (math.pi, math.tau) if front else (0., math.pi)
            ring_arc(a, cx_, cy_, rxx, ryy, tilt, t0, t1, BRONZE[0], 9)
            ring_arc(a, cx_, cy_, rxx, ryy, tilt, t0, t1, BRONZE[2], 6)
            ring_arc(a, cx_, cy_ + 1.5, rxx, ryy, tilt, t0 + .1, t1 - .1, BRONZE[3], 1)
            for j in range(4):                                          # rune studs round the rim
                t = spin + j * math.pi / 2
                if (math.sin(t) < 0) == front:
                    x, y = rxx * math.cos(t), ryy * math.sin(t)
                    a.ball(cx_ + x * math.cos(tilt) - y * math.sin(tilt), cy_ + x * math.sin(tilt) + y * math.cos(tilt), 3, 3, CORONA[2:] if lie < .6 else BRONZE[1:4])
    draw_rings(False)
    # --- the pelvis block, the bell of a torso with a glass lantern for a heart
    shaded(a, T([(-34, hip + 10), (34, hip + 10), (28, hip - 12), (-28, hip - 12)]), STEEL, base=.5, contrast=.9)
    bell = T(smooth([(-30, hip + 8), (30, hip + 8), (46, hip + 62), (50, hip + 100), (24, hip + 118), (-24, hip + 118), (-50, hip + 100), (-46, hip + 62)], 4))
    shaded(a, bell, STEEL, base=.5, contrast=1.2)
    shaded(a, T([(-46, hip + 62), (-30, hip + 8), (-8, hip + 8), (-12, hip + 116), (-24, hip + 118), (-50, hip + 100)]), STEEL, base=.68, contrast=.6, edge=False)
    for k in range(3):
        a.line(T([(-44 + k * 3, hip + 50 + k * 18), (0, hip + 44 + k * 18), (44 - k * 3, hip + 50 + k * 18)]), STEEL[1], 1)
    lx, ly = R.t(0, hip + 64)
    lit = max(0., 1. - lie * 1.1)
    shaded(a, T([(-23, hip + 64), (-16, hip + 82), (0, hip + 88), (16, hip + 82), (23, hip + 64), (16, hip + 46), (0, hip + 40), (-16, hip + 46)]), BRONZE, base=.5, contrast=1.1)
    if lit > .05:
        glow(a, lx, ly, 30 + w * 10 + st * 14, CORONA, .75 * lit + .1)
    a.ball(lx, ly, 15, 15, CORONA[:4] if lit > .35 else STEEL[:3])
    if lit > .35:
        a.ball(lx - 2, ly + 2, 7, 7, CORONA[3:])
    a.line([(lx - 15, ly), (lx + 15, ly)], BRONZE[1], 1)
    a.line([(lx, ly - 15), (lx, ly + 15)], BRONZE[1], 1)
    # --- shoulders and arms: heavy capsules ending in fists; both lift with the rings on the wind-up and come down with them
    for s in (-1, 1):
        R.ball(s * 52, hip + 100, 20, 15, STEEL)
        a.line(T([(s * 34, hip + 100), (s * 70, hip + 100)]), STEEL[0], 1)
    def arm(s, far):
        sh_ = R.t(s * 56, hip + 94)
        idle = (s * 74, hip + 20 + math.sin(ph + s) * 2)
        up = (s * 40, hip + 160)
        down = (s * 40 + 16, 14)
        hand = mixp(mixp(idle, up, w), down, st)
        hand = mixp(hand, (s * 52 + 24 * lie, hip - 4), lie)
        el = ((sh_[0] + hand[0]) / 2 + s * 12, (sh_[1] + hand[1]) / 2 + (-4 if clip == 'attack' else 0))
        base = .36 if far else .6
        shaded(a, capsule(sh_, el, 24, 20, 4), STEEL, base=base, contrast=1.1)
        shaded(a, capsule(el, hand, 20, 24, 4), STEEL, base=base, contrast=1.1)
        shaded(a, [(hand[0] - 15, hand[1] - 11), (hand[0] + 15, hand[1] - 11), (hand[0] + 17, hand[1] + 9), (hand[0], hand[1] + 16), (hand[0] - 17, hand[1] + 8)], BRONZE, base=base + .06, contrast=1.1)
        for k in range(3):
            a.line([(hand[0] - 8 + k * 8, hand[1] - 1), (hand[0] - 8 + k * 8, hand[1] + 8)], OUTLINE, 1)
    arm(-1, True)
    arm(1, False)
    # --- the head: a hooded helm, a crescent crest, one great lens for an eye
    hc = hip + 140
    helm = T(smooth([(-17, hc - 14), (17, hc - 14), (20, hc + 4), (10, hc + 20), (-10, hc + 20), (-20, hc + 4)], 3))
    shaded(a, helm, STEEL, base=.6, contrast=1.2)
    cres = T(smooth([(-18, hc + 16), (-6, hc + 40), (14, hc + 44), (0, hc + 34), (-8, hc + 24)], 3))
    shaded(a, cres, BRONZE, base=.62, contrast=1.2)
    ex, ey = R.t(0, hc + 2)
    a.ball(ex, ey, 10, 10, BRONZE[:4])
    if lit > .3:
        glow(a, ex, ey, 14, CORONA, .8)
        a.ball(ex, ey, 6.4, 6.4, CORONA[2:])
        a.ball(ex - 1, ey + 1, 2.4, 2.4, CORONA[4:])
    else:
        a.ball(ex, ey, 6, 6, STEEL[:3])
        a.line([(ex - 4, ey), (ex + 4, ey)], OUTLINE, 1)
    draw_rings(True)
    if clip == 'attack' and n in (5, 6):                                # the slam: dust in a wave along the ground
        for k in range(5):
            dust(a, 30 + k * 12, 4 + (k % 2) * 3, 3.6 - k * .5, PEARL)
        for k in range(3):
            dust(a, -10 - k * 10, 3 + (k % 2) * 3, 3 - k * .5, PEARL)
    return a


DRAW = dict(cometmaw=cometmaw, eclipsequeen=eclipsequeen, orbitwarden=orbitwarden)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/astral_elite_{kind}_raw.npz'


def build():
    L.STRICT = True
    saved = registry()
    names = {s['name'] for s in old.api('list')['sprites']}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        data = frames(kind)
        name = PREFIX + kind + os.environ.get('SOURCE_SUFFIX', '')
        assert name not in names, name
        np.savez_compressed(raw(kind), **data)
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(name=name, width=kw, height=kh, frames=34, layers=1, fps=10, palette=PALETTE, persist=True,
                                     ops=[dict(op='set_layer', layer=0, name=kind)]))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, L.api_draw(sid, 0, data), 'frames saved', flush=True)


def refresh():
    L.STRICT = True
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(raw(kind), **data)
        print('Refreshed', kind, saved[kind], L.api_draw(saved[kind], 0, data), 'frames', flush=True)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    clips, off = {}, 0
    for row, (clip, (fps, count)) in enumerate(L.CLIPS.items()):
        clips[clip] = dict(fps=fps, n=count, row=row, editorStart=off)
        off += count
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='astral-elite')
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, idle = 0, []
        for row, (clip, (_, count)) in enumerate(L.CLIPS.items()):
            for n in range(count):
                im = rgba(L.cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                b = im.getbbox()
                kindframe.check_bounds(b, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                if clip == 'idle':
                    idle.append(b)
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of(idle, kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlas.save(ASSETS / f'astralelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'astralelites_{kind}.png').convert('RGBA')
        offset = 0
        for row, (clip, (_, count)) in enumerate(L.CLIPS.items()):
            seen = set()
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(L.cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n)
                seen.add(cell.tobytes())
            offset += count
            if clip in ('attack', 'die'):
                assert len(seen) == 8, (kind, clip, 'needs eight distinct frames', len(seen))
        print(kind, '34 editor frames equal the atlas; attack and death have eight distinct frames', flush=True)


if __name__ == '__main__':
    {'preview': L.preview, 'montage': L.montage, 'extents': L.extents, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'montage']()
