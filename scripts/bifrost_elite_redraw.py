#!/usr/bin/env python3
"""Bifrost Reach's three elites (zone shapes pilot): native PixelFlow sources, each with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames per kind.
  skoll       Sköll, the Gale-Alpha (level 31, quest): a wolf twice the size of a galehound, storm-black fur, a silver mane that stands up in
              spikes laced with blue lightning, a scarred muzzle bared over long fangs, one white-hot slit eye. Crouches, then bounds forward
              with the jaws open; the strike throws a fork of lightning off the fangs. Dies: the legs fold and the great body sinks onto its
              belly, the mane goes flat and the eye goes dark.
  shardking   The Shard-King (level 33, quest): a golem the size of a house built of every shard the others dropped: slabs of violet and
              blue crystal, a rainbow of shards on the shoulders, a chest split open on a white core, a crown of five tall shards, two cyan
              slits for eyes. Raises both fists overhead and slams them into the ground in a ring of shards. Dies: it shatters, the slabs fall
              and lie in a pile under the crown.
  heimdallr   Heimdall's Shade (level 35, no quest): the watchman's ghost in ice-pale plate under a winged helm, a tattered cloak streaming
              back, two white pits for eyes, a long spear in the right hand and the broken Gjallarhorn in the left. Raises the horn, blows,
              and the spear comes forward through three rings of sound. Dies: the armour comes apart into motes that rise and are gone.
The manifest is client/assets/bifrostelites.txt. Drawing helpers come from the Lapis redo.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image

import kindframe
import lapis_slime_redraw as L
from lapis_slime_redraw import (Rig, BasePainter, OUTLINE, BONE, EYE_WHITE, PEARL, clamp01, curves, dying, settle,
                                polar, cross_eye, mix, mixp, sm, bez, taper, fang, dust, old)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/bifrost-elites'
REGISTRY = ROOT / 'scripts/bifrost_elite_sources.txt'
MANIFEST = ASSETS / 'bifrostelites.txt'
PREFIX = 'valhallasc_bifrost_elite_'
KINDS = ['skoll', 'shardking', 'heimdallr']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(skoll=(192, 124, 78, 116), shardking=(160, 192, 80, 186), heimdallr=(160, 192, 84, 186))
# art scale per kind (1.0 = the coordinates written in the draw functions), so the biggest frame (192) holds each; judged on an in-game screenshot
SCALE = dict(skoll=.86, shardking=.62, heimdallr=.68)
FLYING = ()
_mine = [
    '#0a0e16', '#1a2232', '#34445e', '#5a6e8e', '#8aa0c0',   # STORM (Sköll's fur, black to slate blue)
    '#26324a', '#5a6e96', '#9ab0d0', '#d4e2f4', '#ffffff',   # MANE (silver)
    '#0a1a3a', '#1e4aa8', '#4a96f0', '#a6d8ff', '#f0fbff',   # BOLT (lightning, the white-hot eye)
    '#120a30', '#34208a', '#6a4ad0', '#a58af0', '#d8caff',   # CRYSTAL (violet slabs)
    '#08283a', '#0e6a8a', '#32b8d8', '#8ae8f4', '#e4fcff',   # ICE (cyan facets, the core, the Shade's plate)
    '#5a0e1a', '#c43a3a', '#e8a030', '#58c860', '#d060e8',   # RAINBOW (red, amber, green, magenta shards)
    '#1a2a44', '#3a5478', '#6e8cb0', '#a8c4de', '#e0eef8',   # PLATE (the Shade's pale steel)
    '#2a3448', '#4a5876', '#7886a6', '#b0bcd4', '#e4eaf6',   # CLOAK (the Shade's ragged cloak, ghost grey)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
STORM, MANE, BOLT, CRYSTAL, ICE, RAIN, PLATE, CLOAK = [_i[5 * k:5 * k + 5] for k in range(8)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = SCALE.get(kind, 1.)
        self.im = Image.new('P', (self.w, self.h), 0)
        from PIL import ImageDraw
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


def facet(a, pts, ramp, light=2, outline=OUTLINE):
    """A crystal slab: the polygon in its lit tone with its lower half in a darker one, so it reads as a cut face."""
    a.poly(pts, ramp[light], outline=outline)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        if (p[1] + q[1]) / 2 < cy - .5 or (p[0] + q[0]) / 2 > cx + 3:
            a.poly([p, q, (cx, cy)], ramp[max(1, light - 2)])
    a.poly([pts[0], pts[1], (cx, cy)], ramp[min(4, light + 1)])


# ---- Sköll ----------------------------------------------------------------------------------------------------------------------
def skoll(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lie = sm(clamp01((dn - .1) * 1.15))
    a = Painter('skoll', st * 9 - w * 7 + recoil + lie * 2)
    walk = clip == 'walk'
    body = 52 + bob * .6 - w * 13 + st * 3 - lie * 28 - dn * 5
    R = Rig(a, 0, body, -w * .06 + st * .1 + recoil * .01)
    fur_far = [STORM[0], STORM[0], STORM[1], STORM[1], STORM[1]]
    fur_near = [STORM[0], STORM[1], STORM[1], STORM[2], STORM[3]]
    belly = [STORM[0], STORM[1], STORM[2], STORM[2], STORM[3]]

    def leg(x, front, far):
        p = (0 if front else math.pi) + (math.pi if far else 0)
        sw = math.sin(ph + p) * 8 if walk else 0
        lift = max(0, math.cos(ph + p)) * 6 if walk else 0
        if clip == 'attack':
            sw = (st * (12 if front else -8) - w * (7 if front else -5)) * (.7 if far else 1)
            lift = st * (9 if front else 3) * (0 if far else 1)
        root = (x, body - 6)
        foot = (x + sw + lie * (16 if front else -14), 4 + lift)
        if front:                                               # a straight foreleg, the elbow back
            mid = (x - 4 + sw * .4 + lie * 6, body * .5 + lift * .3 - lie * 8)
            low = (x + sw * .8 + lie * 14, 14 + lift * .6)
        else:                                                   # a hind leg: thigh forward, hock back, shin forward again
            mid = (x + 8 + sw * .3 + lie * (-4), body * .5 + 4 + lift * .3 - lie * 8)
            low = (x - 4 + sw * .8 + lie * (-12), 17 + lift * .6)
        ramp = fur_far if far else fur_near
        R.limb([root, mid, low], ramp, 8 if front else 9)
        R.limb([low, (foot[0] - 1, foot[1] + 5)], ramp, 6)
        R.ball(foot[0] + 3, foot[1] + 2.5, 8.5, 4.6, ramp)
        for k in range(3):                                      # claws
            R.line([(foot[0] + 8 + k * 2.4, foot[1] + 1.6), (foot[0] + 12.5 + k * 2.4, foot[1] + .4)], BONE[3], 1)

    leg(-26, False, True)
    leg(26, True, True)
    # the tail: a storm streamer, thick at the root
    sway = math.sin(ph * 1.1) * 4 if clip in ('idle', 'walk') else -st * 5
    tail = bez((-40, body + 3), (-52 + sway, body + 16 + w * 6 - lie * 14), (-66 + sway * 1.4 - st * 6, body + 6 - lie * 18), 9)
    taper(a, [R.t(*p) for p in tail], MANE, 9, 2)
    # the body: barrel, deep chest, haunch, a shaggy ruff over the shoulders
    R.ball(0, body, 32, 20, fur_near)
    R.ball(23, body + 1, 21, 22, fur_near)
    R.ball(-24, body - 1, 19, 19, fur_near)
    R.ball(-2, body - 13, 28, 7, belly)
    R.ball(32, body + 8, 15, 17, fur_near)                       # the neck, thick, rising to the head
    for k in range(7):                                           # the mane: long spikes swept back from the neck and withers, shorter down the spine
        x0 = 38 - k * 7.2
        r = 20 - k * 2.2
        tip = (x0 - 13 - r * .3 - st * 3 + sway * .2 * k, body + 18 + r - k * .6 - lie * 8)
        R.poly([(x0 + 5, body + 20 - k * .7), (x0 - 3, body + 20 - k * .5), tip], MANE[2 + (k % 2)], outline=OUTLINE)
    for k in range(4):                                           # lightning laced through the ruff
        bx = 34 - k * 8
        R.line([(bx, body + 24), (bx - 5, body + 30), (bx - 2, body + 33), (bx - 8, body + 40)], BOLT[3 if k % 2 else 2], 1)
    leg(-24, False, False)
    leg(27, True, False)
    # the head: a big wolf skull, a long muzzle, ears up and back, one white-hot eye
    gape = (w * .5 + st * 1.0) if clip == 'attack' else (.3 if clip == 'idle' and n in (2, 3) else 0.)
    gape = max(gape, lie * .2)
    hx, hy = 52 + st * 3 - w * 2, body + 14 - lie * 18 + (2 if clip == 'attack' else 0) - w * 7
    hd = Rig(a, hx, hy, -.12 + w * .16 - st * .04 + lie * .25)
    T = lambda x, y: hd.t(hx + x, hy + y)
    a.ellipse(*T(0, 0), 20.6, 17, OUTLINE)
    a.ball(*T(0, 0), 19, 15.5, [STORM[0], STORM[1], STORM[2], STORM[3], STORM[4]], -.05)
    a.poly([T(8, 8), T(36, 3), T(40, -3), T(38, -7), T(10, -10)], STORM[3], outline=OUTLINE)                       # the muzzle, long and deep
    a.poly([T(12, -7 - gape * 8), T(38, -6 - gape * 10), T(33, -12.5 - gape * 14), T(10, -13 - gape * 12)], STORM[1], outline=OUTLINE)   # the lower jaw
    a.poly([T(14, -5 - gape * 7), T(37, -5 - gape * 8), T(34, -9 - gape * 11), T(15, -9 - gape * 9)], OUTLINE if gape > .25 else STORM[1])
    for k in range(5):                                                                                           # fangs: long, unequal, bared
        a.poly([T(17 + k * 4, -4.5 - gape * 6), T(20 + k * 4, -4.5 - gape * 6), T(18.5 + k * 4, -10.5 - gape * 9 - (k % 2) * 3)], BONE[4])
    for k in range(3):
        a.poly([T(16 + k * 6, -11 - gape * 12), T(19 + k * 6, -11 - gape * 12), T(17.5 + k * 6, -5.5 - gape * 8 - (k % 2) * 2)], BONE[3])
    a.ellipse(*T(40, -1), 3.2, 2.6, OUTLINE)                                                                      # the nose
    a.line([T(7, 11), T(17, 3), T(26, -3)], STORM[0], 2)                                                          # an old scar across the muzzle
    gx, gy = T(11, 5)
    if dying(clip, n, 2):
        a.line([(gx - 4, gy), (gx + 4, gy)], OUTLINE, 1)
    else:
        a.poly([(gx - 8, gy + 1.5), (gx + 8, gy - 3), (gx + 7, gy + 3), (gx - 7, gy + 5.5)], OUTLINE)
        a.poly([(gx - 6, gy + 1.5), (gx + 6, gy - 1.4), (gx + 5, gy + 2), (gx - 5, gy + 3.6)], BOLT[3])
        a.line([(gx - 2, gy + 1), (gx + 3, gy + .2)], BOLT[4], 1)
        a.ellipse(gx + 1, gy + 1.6, 1.4, 1.4, EYE_WHITE)
    a.line([T(2, 11), T(11, 8.5), T(17, 10)], STORM[0], 3)                                                        # the heavy brow
    a.poly([T(-8, 11), T(-14 - w * 4, 25), T(0, 13)], STORM[1], outline=OUTLINE)                                  # ears, pinned back
    a.poly([T(-2, 13), T(-7 - w * 3, 29), T(7, 14)], STORM[2], outline=OUTLINE)
    for k in range(5):                                                                                           # the ruff round the skull
        a.poly([T(-12 + k * 4.5, 8), T(-8 + k * 4.5, 8), T(-16 + k * 4.5 - 2 * w, 18 + (k % 2) * 5)], MANE[2 + k % 2], outline=OUTLINE)
    if clip == 'attack' and n in (4, 5):                                                                         # a fork of lightning off the fangs
        tx, ty = T(40, -8)
        a.line([(tx, ty), (tx + 6, ty - 4), (tx + 3, ty - 8), (tx + 9, ty - 11), (tx + 6, ty - 16), (tx + 11, ty - 19)], BOLT[3], 2)
        a.line([(tx + 6, ty - 4), (tx + 10, ty - 1), (tx + 12, ty - 6)], BOLT[4], 1)
        dust(a, hx - 30, 3, 3.4, PEARL)
    if clip == 'attack' and n in (6, 7):
        for k in range(3):
            dust(a, -38 + k * 8, 4 + (k % 2) * 3, 3.4 - k * .5, PEARL)
    return a


# ---- the Shard-King -------------------------------------------------------------------------------------------------------------
def shardking(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    shatter = dn
    a = Painter('shardking', recoil * .6 + st * 3 - w * 4)
    walk = clip == 'walk'
    hip = 62 + bob * .5 - w * 7 + st * 3 + (math.sin(ph * 2) * 1.6 if walk else 0)
    lean = -w * .12 + st * .22
    R = Rig(a, 0, hip, lean)
    if clip == 'die' and n >= 1:
        return shatter_king(a, n, dn)
    sh_y = hip + 62
    # legs: two thick slabs with a block foot
    for x, far in ((-14, True), (14, False)):
        sw = (math.sin(ph + (math.pi if far else 0)) * 8) if walk else 0
        lift = (max(0, math.cos(ph + (math.pi if far else 0))) * 7) if walk else 0
        ramp = CRYSTAL if far else ICE
        top = (x + sw * .3, hip + 4)
        foot = (x + sw, 6 + lift)
        facet(a, [(top[0] - 13, top[1]), (top[0] + 13, top[1]), (foot[0] + 14, foot[1] + 18), (foot[0] + 17, foot[1]), (foot[0] - 16, foot[1]), (foot[0] - 12, foot[1] + 18)], ramp, 2 if far else 3)
        facet(a, [(foot[0] - 18, foot[1]), (foot[0] + 22, foot[1]), (foot[0] + 20, foot[1] - 5 if foot[1] > 8 else foot[1]), (foot[0] - 20, foot[1])], CRYSTAL, 1)
    # the torso: an inverted wedge split down the middle on a white core
    torso = [R.t(*p) for p in [(-26, hip + 4), (26, hip + 4), (38, hip + 58), (-36, hip + 58), (-30, hip + 30)]]
    facet(a, torso, CRYSTAL, 3)
    core = [R.t(*p) for p in [(-5, hip + 14), (9, hip + 18), (13, hip + 44), (-2, hip + 50), (-10, hip + 30)]]
    a.poly(core, ICE[2], outline=OUTLINE)
    a.poly([R.t(-3, hip + 20), R.t(5, hip + 24), R.t(6, hip + 40), R.t(-3, hip + 42)], ICE[4])
    a.line([R.t(-22, hip + 50), R.t(-8, hip + 36), R.t(-14, hip + 22)], OUTLINE, 1)                  # cracks
    a.line([R.t(24, hip + 46), R.t(12, hip + 34), R.t(20, hip + 14)], OUTLINE, 1)
    # the rainbow: shards driven into the shoulders and chest
    for k, (sx, sy, col) in enumerate(((-34, 56, 0), (-24, 60, 1), (30, 58, 2), (36, 52, 3), (20, 12, 4), (-18, 10, 0))):
        p0 = R.t(sx, hip + sy)
        tip = R.t(sx + (-5 if sx < 0 else 5), hip + sy + 14 + (k % 2) * 4)
        a.poly([(p0[0] - 3, p0[1]), (p0[0] + 3, p0[1]), tip], RAIN[col], outline=OUTLINE)
    # shoulders: pauldrons of stacked crystal
    for sx, ramp in ((-36, CRYSTAL), (38, ICE)):
        p = R.t(sx, hip + 56)
        facet(a, [(p[0] - 16, p[1] - 8), (p[0] + 16, p[1] - 8), (p[0] + 12, p[1] + 12), (p[0] - 12, p[1] + 14)], ramp, 2)
        a.poly([(p[0] - 6, p[1] + 10), (p[0] + 5, p[1] + 10), (p[0] + 1, p[1] + 26)], ramp[3], outline=OUTLINE)
    # arms: overhead on the wind-up, slammed down on the strike
    def arm(side, far):
        sx = (-36 if side < 0 else 38)
        shoulder = R.t(sx, hip + 52)
        up = (shoulder[0] + side * 4, shoulder[1] + 52)
        down = (shoulder[0] + side * 12 + 8, 14)
        idle = (shoulder[0] + side * 14 + 8, shoulder[1] - 40)
        hand = mixp(mixp(idle, up, w), down, st)
        elbow = ((shoulder[0] + hand[0]) / 2 + side * 14, (shoulder[1] + hand[1]) / 2 + (6 if clip == 'attack' else -2))
        ramp = CRYSTAL if far else ICE
        a.limb([shoulder, elbow, hand], ramp, 15)
        facet(a, [(hand[0] - 14, hand[1] - 10), (hand[0] + 14, hand[1] - 10), (hand[0] + 17, hand[1] + 9), (hand[0] - 2, hand[1] + 15), (hand[0] - 16, hand[1] + 8)], ramp, 2)
        for k in range(3):
            a.line([(hand[0] - 9 + k * 9, hand[1] - 3), (hand[0] - 9 + k * 9, hand[1] + 7)], OUTLINE, 1)
        return hand
    hl = arm(-1, True)
    hr = arm(1, False)
    # the head: a faceted diamond under a crown of five shards
    hdy = hip + 80 + bob * .3
    head = [R.t(-15, hdy - 12), R.t(15, hdy - 12), R.t(19, hdy + 8), R.t(2, hdy + 22), R.t(-17, hdy + 8)]
    facet(a, head, ICE, 3)
    for ex in (-8, 7):
        e = R.t(ex, hdy + 2)
        if dying(clip, n, 2):
            a.line([(e[0] - 3, e[1]), (e[0] + 3, e[1])], OUTLINE, 1)
        else:
            a.poly([(e[0] - 5, e[1] + 1), (e[0] + 5, e[1] - 2), (e[0] + 4, e[1] + 2), (e[0] - 4, e[1] + 3)], OUTLINE)
            a.poly([(e[0] - 3, e[1] + 1), (e[0] + 3, e[1] - 1), (e[0] + 2.4, e[1] + 1.6), (e[0] - 2.6, e[1] + 2)], ICE[4])
    a.poly([R.t(-9, hdy - 8), R.t(9, hdy - 8), R.t(6, hdy - 3), R.t(-6, hdy - 3)], OUTLINE)             # the jagged mouth
    for k in range(4):
        a.poly([R.t(-7 + k * 4.4, hdy - 3), R.t(-4.4 + k * 4.4, hdy - 3), R.t(-5.7 + k * 4.4, hdy - 8)], ICE[4])
    for k, (cx, ch, col) in enumerate(((-13, 16, 0), (-6, 25, 1), (1, 32, 2), (8, 26, 3), (15, 18, 4))):      # the crown: five tall shards, a rainbow
        b = R.t(cx, hdy + 14 + (k % 2))
        a.poly([(b[0] - 3.4, b[1]), (b[0] + 3.4, b[1]), (b[0] + (k - 2) * 1.6, b[1] + ch)], RAIN[col], outline=OUTLINE)
        a.poly([(b[0] - 1, b[1] + 1), (b[0] + 1.6, b[1] + 1), (b[0] + (k - 2) * 1.2, b[1] + ch * .75)], mix(RAIN[col], ICE[4], 0) if False else ICE[3])
    if clip == 'attack' and n in (5, 6):                                                                    # the slam: a ring of shards off the ground
        for k in range(9):
            ang = k / 9 * math.pi
            r = 22 + (n - 5) * 12 + (k % 3) * 6
            px, py = 20 + math.cos(ang) * r * 1.4, 4 + math.sin(ang) * r * .55 * (1 + (k % 2) * .4)
            a.poly([(px - 2.4, py), (px + 2.4, py), (px + (k - 4) * .6, py + 9 + (k % 3) * 3)], RAIN[k % 5], outline=OUTLINE)
        dust(a, 30, 3, 3.4, PEARL)
        dust(a, -20, 3, 3, PEARL)
    return a


def R_pts(R, pts):
    return [R.t(*p) for p in pts]


def shatter_king(a, n, dn):
    """The Shard-King comes apart: slabs fall in turn and lie in a pile under the crown."""
    k = n / 7.
    rng = np.random.RandomState(7)
    ground = 4
    # the pile at the end (growing as the pieces land)
    pieces = [
        ('foot', -16, 14, 28, 12, CRYSTAL), ('foot', 18, 14, 28, 12, ICE), ('leg', -14, 34, 22, 36, CRYSTAL), ('leg', 14, 34, 22, 36, ICE),
        ('chest', 0, 82, 62, 44, CRYSTAL), ('core', 2, 82, 16, 28, ICE), ('pauld', -36, 112, 30, 20, CRYSTAL), ('pauld', 38, 112, 30, 20, ICE),
        ('arm', -48, 80, 16, 40, CRYSTAL), ('arm', 50, 80, 16, 40, ICE), ('head', 0, 158, 34, 32, ICE),
    ]
    rest = {'foot': (0, 8), 'leg': (0, 16), 'chest': (0, 22), 'core': (4, 30), 'pauld': (0, 14), 'arm': (0, 8), 'head': (0, 34)}
    for i, (name, x, y, w_, h_, ramp) in enumerate(pieces):
        start = (i % 5) * .1
        t = clamp01((k - start) / .55)
        fall = t * t
        rx = rest[name][0] + (x * .55 if name in ('foot', 'leg') else x * .8) + (i - 5) * (6 if name != 'foot' else 2)
        ry = rest[name][1] + (i % 3) * 5 * (name != 'head')
        px = mix(x, rx, fall)
        py = mix(y, max(ground + h_ / 2, ry), fall)
        if name == 'core' and k > .5:
            continue
        facet(a, [(px - w_ / 2, py - h_ / 2), (px + w_ / 2, py - h_ / 2 + (n % 3)), (px + w_ / 2 - 3, py + h_ / 2), (px, py + h_ / 2 + 3), (px - w_ / 2 + 2, py + h_ / 2 - 2)], ramp, 2)
    for j in range(5):                                                                                       # the crown lies on the pile
        t = clamp01((k - .3) / .6)
        cx = -18 + j * 9
        cy = mix(188 - j * 3, 40 + (j % 2) * 4, t * t)
        a.poly([(cx - 3, cy), (cx + 3, cy), (cx + (j - 2) * 3 * t, cy + mix(22, 7, t))], RAIN[j], outline=OUTLINE)
    for j in range(int(k * 14)):                                                                             # loose shards fly out
        ang = rng.uniform(.2, math.pi - .2)
        r = rng.uniform(20, 60) * (.3 + k)
        px, py = math.cos(ang) * r * 1.5, max(ground + 2, 70 + math.sin(ang) * r * 1.1 - k * k * 70)
        a.poly([(px - 2, py), (px + 2, py), (px, py + 5)], RAIN[j % 5], outline=OUTLINE)
    return a


# ---- Heimdall's Shade ------------------------------------------------------------------------------------------------------------
def heimdallr(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('heimdallr', st * 6 - w * 4 + recoil)
    walk = clip == 'walk'
    hip = 72 + bob * .7 + (math.sin(ph * 2) * 1.4 if walk else 0) - w * 3
    lean = -w * .08 + st * .16
    R = Rig(a, 0, hip, lean)
    sway = math.sin(ph * 1.3) * 3 if clip in ('idle', 'walk') else -st * 7
    # the cloak: long ragged strips streaming back from the shoulders
    for k in range(7):
        x0 = -10 - k * 2.4
        top = R.t(x0, hip + 66 - k * 3)
        tip = (top[0] - 20 - k * 4 + sway * (1 + k * .3) - st * 5, max(4 + k * .8, hip - 12 - k * 3 + (k % 2) * 6 + sway * .5))
        taper(a, bez(top, (top[0] - 12, top[1] - 16), tip, 7), CLOAK, 7 - k * .45, 1.4)
    # legs: pale greaves under a short tabard, a ghost's slow step
    for x, far in ((-8, True), (9, False)):
        sw = math.sin(ph + (math.pi if far else 0)) * 6 if walk else 0
        lift = max(0, math.cos(ph + (math.pi if far else 0))) * 5 if walk else 0
        a.limb([(x, hip - 2), (x + 2 + sw * .4, hip * .5 + lift * .4), (x + sw, 8 + lift)], PLATE if not far else CLOAK, 7)
        a.ellipse(x + sw + 4, 4 + lift, 8, 3.4, PLATE[1] if far else PLATE[2])
    # the tabard and the breastplate
    R.poly([(-14, hip + 6), (14, hip + 6), (12, hip - 16 + sway * .3), (0, hip - 22), (-12, hip - 16)], CLOAK[2], outline=OUTLINE)
    R.ball(0, hip + 34, 16, 28, PLATE, -.02)
    R.ball(4, hip + 44, 9, 12, PLATE[1:])
    R.line([(-13, hip + 26), (0, hip + 22), (13, hip + 26)], PLATE[0], 2)
    R.line([(0, hip + 22), (0, hip + 54)], PLATE[0], 1)
    R.ball(-17, hip + 52, 11, 8, PLATE)                                                                      # pauldrons
    R.ball(18, hip + 52, 11, 8, PLATE)
    # the spear: held in the near hand, drawn back on the wind-up, thrust on the strike
    hand_idle, hand_back, hand_thrust = (22, hip + 30), (6, hip + 36), (28, hip + 34)
    hand = mixp(mixp(hand_idle, hand_back, w), hand_thrust, st)
    sh = R.t(18, hip + 50)
    a.limb([sh, (sh[0] + 8 + st * 6 - w * 8, (sh[1] + hand[1]) / 2 - 4), R.t(*hand)], PLATE, 6)
    ang = mix(mix(1.5, 1.16, w), .12, st)
    dx, dy = math.cos(ang), math.sin(ang)
    hx, hy = R.t(*hand)
    butt = (hx - dx * 36, hy - dy * 36)
    tip = (hx + dx * 42, hy + dy * 42)
    a.line([butt, tip], PLATE[1], 3)
    a.line([(butt[0] + 1, butt[1] + 1), (tip[0] + 1, tip[1] + 1)], PLATE[3], 1)
    nx, ny = -dy, dx
    a.poly([(tip[0] + nx * 4, tip[1] + ny * 4), (tip[0] + dx * 14, tip[1] + dy * 14), (tip[0] - nx * 4, tip[1] - ny * 4), (tip[0] - dx * 4, tip[1] - dy * 4)], ICE[3], outline=OUTLINE)
    a.ball(hx, hy, 3.6, 3.6, PLATE)
    # the head: a winged helm over a hollow face
    hdy = hip + 74
    hd = Rig(a, 2, hdy, lean * .6 - w * .06 + st * .1)
    T = lambda x, y: R.t(*hd.t(x, y))
    a.limb([R.t(1, hip + 56), T(1, hdy - 6)], PLATE, 7)
    a.ball(*T(2, hdy), 11.5, 12.6, PLATE, lean)
    a.poly([T(-2, hdy - 8), T(14, hdy - 6), T(13, hdy - 14), T(0, hdy - 14)], OUTLINE)                       # the open visor
    a.poly([T(-9, hdy + 6), T(14, hdy + 6), T(13, hdy - 1), T(-8, hdy - 2)], PLATE[0])
    for ex in (-2, 8):
        gx, gy = T(ex + 1, hdy + 2)
        if dying(clip, n, 2):
            a.line([(gx - 2, gy), (gx + 2, gy)], OUTLINE, 1)
        else:
            a.ellipse(gx, gy, 3.4, 2.6, ICE[2])
            a.ellipse(gx + .4, gy, 2, 1.5, ICE[4])
    for side in (-1, 1):                                                                                      # the wings on the helm
        base = T(2 + side * 9, hdy + 8)
        tipw = (base[0] + side * 16, base[1] + 22 + (math.sin(ph) * 1.5 if clip in ('idle', 'walk') else 0))
        a.poly([base, (base[0] + side * 4, base[1] - 3), tipw, (base[0] + side * 8, base[1] + 12)], MANE[3], outline=OUTLINE)
        a.poly([base, (base[0] + side * 3, base[1] + 3), (tipw[0] - side * 3, tipw[1] - 8)], MANE[4])
    a.poly([T(-3, hdy + 11), T(7, hdy + 11), T(2, hdy + 28)], PLATE[3], outline=OUTLINE)                       # the crest
    # the horn: in the far hand, at the hip when idle, at the lips on the wind-up
    horn_idle, horn_up = (-24, hip + 40), (14, hdy - 4)
    hh = mixp(horn_idle, horn_up, w)
    hh = mixp(hh, (18, hip + 54), st)
    hp = R.t(*hh)
    arm_to = hp
    a.limb([R.t(-16, hip + 50), (hp[0] - 6, hp[1] + 8), hp], CLOAK, 5)
    hb = [bez(hp, (hp[0] + 10, hp[1] + 12), (hp[0] + 24, hp[1] + 4), 8)]
    taper(a, hb[0], BONE, 5, 11)
    a.ellipse(hb[0][-1][0] + 2, hb[0][-1][1], 4.2, 7, OUTLINE)
    a.ellipse(hb[0][-1][0] + 3, hb[0][-1][1], 2.6, 5, ICE[1])
    if clip == 'attack' and n in (4, 5, 6):                                                                   # three rings of sound off the horn
        c = (hb[0][-1][0] + 4, hb[0][-1][1])
        for k in range(3):
            r = 10 + k * 9 + (n - 4) * 6
            pts = [(c[0] + math.cos(t) * r * .55, c[1] + math.sin(t) * r) for t in np.linspace(-1.25, 1.25, 11)]
            a.line(pts, ICE[3] if k % 2 else ICE[2], 2 if k == 0 else 1)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, tip[0] - a.cx + 4 + k * 8, 4 + (k % 2) * 4, 3 - k * .4, PEARL)
    if clip == 'idle' and n in (1, 4):
        a.ball(-26 + n * 2, hip - 10 - n * 2, 1.6, 1.2, CLOAK)
    if clip == 'die':
        return dissolve(a, n, dn)
    return a


def dissolve(a, n, dn):
    """The Shade is not a body: the armour comes apart into motes that rise, a few more at each beat, and what is left sinks."""
    rng = np.random.RandomState(31 + n)
    grid = np.array(a.im)
    ys, xs = np.nonzero(grid)
    h, w_ = grid.shape
    keep = np.zeros_like(grid)
    thresh = 1.0 - dn * 1.02
    noise = (np.sin(xs * 12.9898 + ys * 78.233) * 43758.5453) % 1
    band = (ys / max(1, h)) * .35                                                                              # the top goes first
    ok = noise + band * dn * 1.6 > dn * 1.25 - .05
    for x, y, k in zip(xs, ys, ok):
        if k:
            keep[y, x] = grid[y, x]
    if dn > .1:                                                                                                # the motes rise from where the body was
        for j in range(int(10 + 28 * dn)):
            i = rng.randint(len(xs))
            lift = int(dn * rng.uniform(6, 34))
            x, y = xs[i] + rng.randint(-2, 3), ys[i] - lift
            if 2 < y < h - 2 and 2 < x < w_ - 2:
                keep[y, x] = ICE[3 if j % 2 else 4]
                if j % 3 == 0 and y > 3:
                    keep[y - 1, x] = ICE[2]
    a.im = Image.fromarray(keep, 'P')
    a.im.putpalette(Image.new('P', (1, 1)).getpalette() if False else a.im.getpalette() or [0] * 768)
    return a


DRAW = dict(skoll=skoll, shardking=shardking, heimdallr=heimdallr)
# the shared frame/preview machinery reads these names
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/bifrost_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='bifrost-elite')
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
        atlas.save(ASSETS / f'bifrostelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'bifrostelites_{kind}.png').convert('RGBA')
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
