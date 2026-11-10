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
KIND_FRAMES = dict(skoll=(192, 124, 74, 116), shardking=(160, 192, 80, 186), heimdallr=(160, 192, 84, 186))
# art scale per kind (1.0 = the coordinates written in the draw functions), so the biggest frame (192) holds each; judged on an in-game screenshot
SCALE = dict(skoll=.74, shardking=.58, heimdallr=.62)
FLYING = ()
_mine = [
    '#06080e', '#141a28', '#2a3550', '#46587a', '#6c82a8',   # STORM (Sköll's fur: ink to slate)
    '#2a3858', '#5a729e', '#9ab4d8', '#d8e6f8', '#ffffff',   # MANE (silver, frost)
    '#0a1a40', '#1e50b0', '#4a9af4', '#a8dcff', '#f4fcff',   # BOLT (lightning, the white-hot eye)
    '#0e0830', '#2c1a78', '#5a3ec4', '#9a7ff0', '#d6c8ff',   # CRYSTAL (violet)
    '#04202e', '#0a5a78', '#22a4cc', '#7ae0f0', '#e0fcff',   # ICE (cyan)
    '#3a0810', '#a01c28', '#e04a3c', '#ff8a6a', '#ffd0b8',   # RED shards
    '#3a2004', '#a8620c', '#f0a020', '#ffd458', '#fff2b0',   # AMBER shards
    '#06300e', '#1c7a2a', '#48c848', '#98f078', '#e0ffc8',   # GREEN shards
    '#34063a', '#8a1e90', '#d450d8', '#f294f0', '#ffd8fc',   # MAGENTA shards
    '#101826', '#2c3a54', '#566a8c', '#8ea4c4', '#cfdcf0',   # PLATE (the Shade's pale steel)
    '#161c2c', '#2e3a54', '#546284', '#8896b8', '#c4d0e8',   # CLOAK (ghost grey-blue)
    '#2a1a06', '#74501c', '#bf8e3c', '#ecc46c', '#fff0b8',   # HORN (old ivory-gold)
    '#3a0a0e', '#8a1c24', '#d04040', '#ff7a6a', '#ffc0b0',   # FLESH (Sköll's maw, tongue)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
STORM, MANE, BOLT, CRYSTAL, ICE, RED, AMBER, GREEN, MAGENTA, PLATE, CLOAK, HORN, MAW = [_i[5 * k:5 * k + 5] for k in range(13)]
RAINBOW = [RED, AMBER, GREEN, ICE, MAGENTA]


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


# ---- shading toolkit: filled shapes with a lit gradient, a dithered terminator, a dark rim and a bright edge ---------------------------------------
from PIL import ImageDraw
from scipy import ndimage


def smooth(pts, n=5, closed=True):
    """Catmull-Rom through the points: organic outlines from a few control points."""
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
    """A limb: a tapered round-ended bar from p (width w0) to q (width w1)."""
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
    """Fill a polygon (painter coordinates) with a lit gradient. Light comes from the upper left of the screen."""
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
    if edge:                                                    # a bright rim on the lit side, a dark one on the shadow side
        rim = mk & ~inner
        ry, rx = np.nonzero(rim)
        lit = ((rx - cx) * light[0] + (ry - cy) * light[1]) > 0
        arr[ry[~lit], rx[~lit]] = ramp[0]
        if outline is not None:
            arr[ry[lit], rx[lit]] = outline
    a.im.paste(Image.fromarray(arr, 'P'), mask=Image.fromarray((mk * 255).astype(np.uint8)))


def outline_of(a, pts, col=OUTLINE, width=1):
    a.d.line([a.pos(*p) for p in list(pts) + [pts[0]]], fill=col, width=max(1, round(width * a.S)))


def glow(a, x, y, r, ramp, strength=1.):
    """A soft dithered halo: bright at the middle, fading out, never darker than what is under it."""
    px, py = a.pos(x, y)
    R = r * a.S
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


def bolt_line(a, pts, col, width=1, jag=2.2, seed=1):
    """A jagged lightning line along the control points."""
    rng = np.random.RandomState(seed)
    out = [pts[0]]
    for p, q in zip(pts, pts[1:]):
        k = max(2, int(math.dist(p, q) / 5))
        for i in range(1, k + 1):
            t = i / k
            out.append((p[0] + (q[0] - p[0]) * t + (rng.rand() - .5) * jag * 2 * (i < k), p[1] + (q[1] - p[1]) * t + (rng.rand() - .5) * jag * 2 * (i < k)))
    a.line(out, col, width)


def fur(a, pts, ramp, seed=3, density=.12, length=4):
    """Short lighter strokes inside a shape, so a coat has grain."""
    P = [a.pos(*p) for p in pts]
    m = Image.new('1', (a.w, a.h), 0)
    ImageDraw.Draw(m).polygon(P, fill=1)
    mk = np.array(m, bool)
    ys, xs = np.nonzero(mk)
    rng = np.random.RandomState(seed)
    for k in rng.choice(len(xs), int(len(xs) * density), replace=False):
        x, y = xs[k], ys[k]
        c = ramp[min(len(ramp) - 1, 2 + rng.randint(2))]
        for j in range(int(length * a.S * rng.rand()) + 1):
            if 0 <= y + j < a.h and 0 <= x - j // 2 < a.w and mk[y + j, max(0, x - j // 2)]:
                a.im.putpixel((x - j // 2, y + j), c)


# ---- Sköll ----------------------------------------------------------------------------------------------------------------------
def skoll(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    lie = sm(clamp01((dn - .1) * 1.15))
    a = Painter('skoll', st * 9 - w * 8 + recoil + lie * 2)
    walk = clip == 'walk'
    body = 57 + bob * .6 - w * 12 + st * 3 - lie * 31 - dn * 4
    sway = math.sin(ph * 1.1) * 4 if clip in ('idle', 'walk') else -st * 5
    FUR = STORM

    def leg(x, front, far):
        p = (0 if front else math.pi) + (math.pi if far else 0)
        sw = math.sin(ph + p) * 8 if walk else 0
        lift = max(0, math.cos(ph + p)) * 6 if walk else 0
        if clip == 'attack':
            sw = (st * (13 if front else -9) - w * (7 if front else -5)) * (.7 if far else 1)
            lift = st * (9 if front else 3) * (0 if far else 1)
        top = (x + 2, body - 4)
        if front:
            knee = (x - 3 + sw * .4 + lie * 7, body * .52 + lift * .3 - lie * 8)
            ank = (x + 1 + sw * .8 + lie * 15, 13 + lift * .6)
        else:
            knee = (x + 11 + sw * .3 - lie * 5, body * .5 + 3 + lift * .3 - lie * 8)
            ank = (x - 6 + sw * .8 - lie * 13, 17 + lift * .6)
        foot = (ank[0] + 3 + (lie * 5 if front else -lie * 5), 3.5 + lift)
        base = .32 if far else .62
        shaded(a, capsule(top, knee, 15, 9, 4), FUR, base=base, contrast=.9)
        shaded(a, capsule(knee, ank, 9, 5.5, 4), FUR, base=base, contrast=.9)
        shaded(a, smooth([(ank[0] - 4, ank[1] + 1), (ank[0] + 5, ank[1] + 2), (foot[0] + 10, foot[1] + 2.5), (foot[0] + 10, foot[1] - 2.5), (foot[0] - 4, foot[1] - 2.5)], 3), FUR, base=base, contrast=.8)
        for k in range(3):
            a.line([(foot[0] + 8 + k * 2.4, foot[1] + .5), (foot[0] + 13 + k * 2.4, foot[1] - 1.5)], BONE[4], 1)

    leg(-24, False, True)
    leg(25, True, True)
    # the tail, a storm streamer: thick at the root, lightning in the tip
    tl = [(-44, body + 4), (-58 + sway * .3, body + 14 + w * 4 - lie * 10), (-74 + sway * .8 - st * 3, body + 12 - lie * 16), (-88 + sway * 1.2 - st * 6, body + 2 - lie * 20)]
    for (p, q), (w0, w1) in zip(zip(tl, tl[1:]), ((16, 12), (12, 8), (8, 3))):
        shaded(a, capsule(p, q, w0, w1, 4), MANE, base=.45, contrast=.8)
    # the barrel, chest and haunch as one organic shape
    torso = smooth([(-42, body + 2), (-32, body + 16), (-8, body + 19), (14, body + 27), (34, body + 29), (45, body + 12), (46, body - 10), (36, body - 21), (12, body - 20), (-10, body - 15), (-28, body - 15), (-42, body - 8)], 5)
    shaded(a, torso, FUR, base=.55, contrast=1.1)
    shaded(a, smooth([(-44, body + 4), (-32, body + 10), (-24, body - 8), (-38, body - 14), (-48, body - 6)], 4), FUR, base=.64, contrast=.5, edge=False)   # the haunch
    shaded(a, smooth([(8, body - 8), (30, body - 4), (44, body - 14), (36, body - 21), (12, body - 20)], 4), FUR, base=.42, contrast=.4, edge=False)         # the belly in shadow
    fur(a, torso, MANE, seed=4, density=.018, length=4)
    bolt_line(a, [(-28, body + 15), (-18, body + 4), (-24, body - 2), (-8, body - 11)], BOLT[3], 1, 1.4, 5)                                          # a scar of lightning on the flank
    bolt_line(a, [(2, body + 22), (10, body + 10), (6, body + 6), (18, body - 4)], BOLT[2], 1, 1.4, 6)
    # the neck and the mane: spikes swept back from the head, down the spine and under the chest
    hx, hy = 60 + st * 3 - w * 3, body + 9 - lie * 17 - w * 6 + (2 if clip == 'attack' else 0)
    neck = smooth([(26, body + 29), (40, body + 30), (hx + 2, hy + 14), (hx + 8, hy - 8), (46, body - 10), (28, body - 8)], 5)
    shaded(a, neck, FUR, base=.6, contrast=1., edge=False)
    for k in range(7):
        t = k / 6 * .62
        bx, by = mixp((hx - 4, hy + 15), (-30, body + 17), t)
        ln = 30 - 14 * t
        tip = (bx - ln * .8 - st * 3 + sway * .12 * k, by + ln * .75 - lie * 5)
        shaded(a, [(bx + 5, by - 2), (bx - 5, by - 1), tip], MANE, base=.55 + .25 * (k % 2), contrast=.9)
    for k in range(5):                                                  # the ruff under the throat
        bx, by = mixp((hx + 2, hy - 6), (38, body - 14), k / 4)
        shaded(a, [(bx + 4, by + 2), (bx - 4, by + 1), (bx - 8 - k * .5, by - 14 - (k % 2) * 4)], MANE, base=.45, contrast=.8)
    # the head: wolf skull, long muzzle, the maw open on the strike
    gape = (w * .55 + st * 1.0) if clip == 'attack' else (.3 if clip == 'idle' and n in (2, 3) else 0.)
    gape = max(gape, lie * .2)
    hd = Rig(a, hx + 4, hy - 8, -.1 + w * .14 - st * .04 + lie * .25)
    T = lambda pts: [hd.t(*p) for p in pts]
    jaw = [(hx + 4, hy - 8), (hx + 32, hy - 9), (hx + 52, hy - 8), (hx + 47, hy - 16), (hx + 28, hy - 20), (hx + 8, hy - 17)]
    pivot = (hx + 4, hy - 8)
    ang = gape * .52
    jaw = [(pivot[0] + (x - pivot[0]) * math.cos(ang) + (y - pivot[1]) * math.sin(ang), pivot[1] - (x - pivot[0]) * math.sin(ang) + (y - pivot[1]) * math.cos(ang)) for x, y in jaw]
    if gape > .12:
        a.poly(T([(hx + 6, hy - 6), (hx + 50, hy - 6), (jaw[2][0] - 2, jaw[2][1] + 2), (jaw[1][0], jaw[1][1] + 3)]), MAW[0])                            # the dark of the mouth
        a.poly(T([(hx + 14, jaw[1][1] + 4), (hx + 38, jaw[1][1] + 5), (hx + 32, jaw[1][1] - 1), (hx + 16, jaw[1][1] + 1)]), MAW[2])                       # the tongue
    shaded(a, T(jaw), FUR, base=.4, contrast=.8)
    skull = smooth([(hx - 14, hy + 10), (hx - 4, hy + 19), (hx + 10, hy + 18), (hx + 24, hy + 10), (hx + 46, hy + 4), (hx + 55, hy - 1), (hx + 54, hy - 8), (hx + 34, hy - 10), (hx + 14, hy - 11), (hx - 10, hy - 7)], 4)
    shaded(a, T(skull), [STORM[0], STORM[1], STORM[2], STORM[3], STORM[4]], base=.62, contrast=1.1)
    a.poly(T([(hx + 14, hy - 10), (hx + 54, hy - 8), (hx + 54, hy - 7.5)]), OUTLINE)
    for k in range(6):                                                  # fangs, long and unequal, upper and lower
        fx = hx + 20 + k * 5.4
        a.poly(T([(fx, hy - 9), (fx + 3, hy - 9), (fx + 1.5, hy - 17 - (k % 2) * 3 - gape * 3)]), BONE[4])
    for k in range(3):
        fx = hx + 24 + k * 8
        a.poly(T([(fx, jaw[1][1] + 2), (fx + 3, jaw[1][1] + 2), (fx + 1.5, jaw[1][1] + 9 + (k % 2) * 2)]), BONE[3]) if gape > .2 else None
    nose = hd.t(hx + 54, hy - 2)
    a.ellipse(nose[0] - a.cx + 0, 0, 0, 0, 0) if False else None
    shaded(a, T(smooth([(hx + 50, hy + 1), (hx + 57, hy), (hx + 57, hy - 5), (hx + 51, hy - 6)], 3)), [OUTLINE, STORM[0], STORM[1], STORM[2], STORM[3]], base=.5, edge=False)
    a.line(T([(hx + 4, hy + 14), (hx + 18, hy + 3), (hx + 34, hy - 5)]), STORM[0], 2)               # an old scar across the muzzle
    ex, ey = hd.t(hx + 17, hy + 6)
    if dying(clip, n, 2):
        a.line([(ex - 4, ey), (ex + 4, ey)], OUTLINE, 1)
    else:
        glow(a, hd.t(hx + 17, hy + 6)[0], hd.t(hx + 17, hy + 6)[1], 9, BOLT, .9)
        a.poly([(ex - 7, ey + 2), (ex + 7, ey - 3), (ex + 6, ey + 2.5), (ex - 6, ey + 5)], OUTLINE)
        a.poly([(ex - 5.4, ey + 2), (ex + 5.4, ey - 1.4), (ex + 4.6, ey + 2), (ex - 4.4, ey + 3.8)], BOLT[3])
        a.line([(ex - 2, ey + 1.4), (ex + 3.4, ey + .4)], BOLT[4], 1)
    a.line(T([(hx + 8, hy + 12), (hx + 18, hy + 9), (hx + 26, hy + 11)]), OUTLINE, 3)             # the heavy brow
    shaded(a, T([(hx - 12, hy + 12), (hx - 20 - w * 4, hy + 36), (hx - 1, hy + 18)]), STORM, base=.5)
    shaded(a, T([(hx - 3, hy + 15), (hx - 10 - w * 3, hy + 40), (hx + 9, hy + 16)]), STORM, base=.7)
    leg(-22, False, False)
    leg(27, True, False)
    if clip == 'attack' and n in (4, 5):                                # a fork of lightning off the fangs
        tx, ty = hd.t(hx + 52, hy - 14)
        bolt_line(a, [(tx, ty), (tx + 12, ty - 6), (tx + 8, ty - 14), (tx + 20, ty - 20)], BOLT[3], 2, 2.4, n)
        bolt_line(a, [(tx + 10, ty - 7), (tx + 24, ty - 4)], BOLT[4], 1, 1.6, n + 3)
        glow(a, tx + 6, ty - 8, 12, BOLT, .8)
    if clip == 'attack' and n in (6, 7):
        for k in range(3):
            dust(a, -38 + k * 8, 4 + (k % 2) * 3, 3.4 - k * .5, PEARL)
    return a


# ---- the Shard-King -------------------------------------------------------------------------------------------------------------
def shardking(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('shardking', recoil * .6 + st * 3 - w * 4)
    if clip == 'die' and n >= 1:
        return shatter_king(a, n, dn)
    walk = clip == 'walk'
    hip = 54 + bob * .5 - w * 6 + st * 4 + (math.sin(ph * 2) * 1.5 if walk else 0)
    R = Rig(a, 0, hip, -w * .1 + st * .18)
    T = lambda pts: [R.t(*p) for p in pts]
    # legs: squat pillars of violet crystal on block feet
    for x, far in ((-18, True), (18, False)):
        sw = (math.sin(ph + (math.pi if far else 0)) * 8) if walk else 0
        lift = (max(0, math.cos(ph + (math.pi if far else 0))) * 7) if walk else 0
        fx, fy = x + sw, 3 + lift
        base = .38 if far else .6
        shaded(a, [(x - 16, hip + 8), (x + 16, hip + 8), (x + 17, hip - 24), (fx + 19, fy + 22), (fx - 19, fy + 22), (x - 17, hip - 24)], CRYSTAL, base=base, contrast=1.1)
        a.line([(x - 17, hip - 24), (x + 17, hip - 24)], CRYSTAL[1], 1)
        a.line([(x - 4, hip + 8), (x + 2, hip - 24), (fx - 2, fy + 22)], CRYSTAL[4] if not far else CRYSTAL[2], 1)
        shaded(a, [(fx - 24, fy + 22), (fx + 24, fy + 22), (fx + 27, fy), (fx - 27, fy)], CRYSTAL, base=base + .08, contrast=1.2)
    shaded(a, T([(-36, hip + 12), (36, hip + 12), (30, hip - 12), (-30, hip - 12)]), CRYSTAL, base=.5, contrast=.9)                   # the pelvis block
    # the torso: two great faces and a fissure of white light down the middle
    torso_l = T([(-32, hip + 12), (1, hip + 8), (1, hip + 92), (-38, hip + 96), (-62, hip + 72)])
    torso_r = T([(1, hip + 8), (32, hip + 12), (62, hip + 72), (38, hip + 96), (1, hip + 92)])
    shaded(a, torso_l, CRYSTAL, base=.72, contrast=1.2)
    shaded(a, torso_r, CRYSTAL, base=.36, contrast=1.1)
    glow(a, *R.t(1, hip + 50), 30, ICE, .85)
    fiss = T([(-3, hip + 90), (7, hip + 72), (-4, hip + 58), (8, hip + 44), (-1, hip + 28), (4, hip + 12), (10, hip + 30), (3, hip + 46), (12, hip + 64), (5, hip + 82)])
    shaded(a, fiss, ICE, base=.95, contrast=.3, outline=None, edge=False)
    a.line(T([(2, hip + 86), (4, hip + 60), (2, hip + 36), (6, hip + 16)]), ICE[4], 1)
    for k, (p, q) in enumerate((((6, hip + 70), (30, hip + 82)), ((-4, hip + 56), (-34, hip + 66)), ((8, hip + 40), (34, hip + 30)), ((-2, hip + 30), (-30, hip + 22)))):
        bolt_line(a, T([p, q]), RAINBOW[k][3], 1, 1.8, k + 2)                                         # veins of every colour a shard ever was
    # the rainbow: shards driven into the shoulders, tall at the back
    for s in (-1, 1):
        b = (s * 56, hip + 88)
        shaded(a, T([(b[0] - 20, b[1] - 16), (b[0] + 20, b[1] - 16), (b[0] + 24, b[1] + 6), (b[0], b[1] + 14), (b[0] - 24, b[1] + 6)]), CRYSTAL if s < 0 else ICE, base=.6)
        for k, (dx, ln, tilt) in enumerate(((-12, 34, -5), (0, 48, 2), (12, 30, 8))):
            col = RAINBOW[(k + (2 if s > 0 else 0)) % 5]
            shaded(a, T([(b[0] + dx - 7, b[1] + 8), (b[0] + dx + 7, b[1] + 8), (b[0] + dx + tilt + s * 4, b[1] + 8 + ln)]), col, base=.65, contrast=1.1)
    # arms: overhead on the wind-up, slammed to the ground on the strike
    def arm(s, far):
        sh = R.t(s * 58, hip + 76)
        up = (s * 26, hip + 150)
        down = (s * 22 + 12, 16)
        idle = (s * 66, hip + 2)
        hand = mixp(mixp(idle, up, w), down, st)
        el = ((sh[0] + hand[0]) / 2 + s * 16, (sh[1] + hand[1]) / 2 + (8 if clip == 'attack' else -2))
        ramp = CRYSTAL if far else ICE
        base = .4 if far else .62
        shaded(a, capsule(sh, el, 26, 24, 4), ramp, base=base, contrast=1.1)
        shaded(a, capsule(el, hand, 24, 30, 4), ramp, base=base, contrast=1.1)
        shaded(a, [(hand[0] - 17, hand[1] - 13), (hand[0] + 17, hand[1] - 13), (hand[0] + 20, hand[1] + 10), (hand[0], hand[1] + 19), (hand[0] - 19, hand[1] + 9)], ramp, base=base + .06, contrast=1.2)
        for k in range(3):
            a.line([(hand[0] - 9 + k * 9, hand[1] - 2), (hand[0] - 9 + k * 9, hand[1] + 9)], OUTLINE, 1)
        return hand
    arm(-1, True)
    arm(1, False)
    # the head: a faceted helm, two white slits, a crown of five shards
    hdc = hip + 108
    face = T([(-16, hdc - 14), (16, hdc - 14), (21, hdc + 6), (9, hdc + 24), (-9, hdc + 24), (-21, hdc + 6)])
    shaded(a, face, ICE, base=.65, contrast=1.2)
    for ex in (-9, 9):
        e = R.t(ex, hdc + 6)
        if dying(clip, n, 2):
            a.line([(e[0] - 3, e[1]), (e[0] + 3, e[1])], OUTLINE, 1)
        else:
            glow(a, e[0] - a.cx + 0, 0, 0, ICE, 0) if False else None
            a.poly([(e[0] - 6, e[1] + 1.5), (e[0] + 6, e[1] - 2.5), (e[0] + 5, e[1] + 2), (e[0] - 5, e[1] + 4)], OUTLINE)
            a.poly([(e[0] - 4, e[1] + 1.5), (e[0] + 4, e[1] - 1), (e[0] + 3, e[1] + 1.6), (e[0] - 3, e[1] + 3)], ICE[4])
    a.poly(T([(-10, hdc - 9), (10, hdc - 9), (7, hdc - 3), (-7, hdc - 3)]), OUTLINE)
    for k in range(4):
        a.poly(T([(-7 + k * 4.6, hdc - 3), (-4.4 + k * 4.6, hdc - 3), (-5.7 + k * 4.6, hdc - 8.5)]), ICE[4])
    for k, (cx, ch) in enumerate(((-15, 20), (-7, 30), (1, 38), (9, 30), (17, 20))):
        b = (cx, hdc + 20 - abs(cx) * .15)
        shaded(a, T([(b[0] - 4.5, b[1]), (b[0] + 4.5, b[1]), (b[0] + (k - 2) * 2.2, b[1] + ch)]), RAINBOW[k], base=.7, contrast=1.2)
    if clip in ('idle', 'walk'):                                        # shards drift beside it: built from every shard the others dropped
        for k, (dx, dy, col) in enumerate(((-82, 120, 1), (86, 104, 3), (-74, 52, 4))):
            bob2 = math.sin(ph * .8 + k * 2) * 3
            shaded(a, [(dx - 4, dy + bob2), (dx + 4, dy + bob2), (dx + 1, dy + 13 + bob2)], RAINBOW[col], base=.7)
    if clip == 'attack' and n in (5, 6):                                # the slam: a ring of shards off the ground
        for k in range(9):
            ang = k / 9 * math.pi
            r = 24 + (n - 5) * 12 + (k % 3) * 6
            px, py = 20 + math.cos(ang) * r * 1.4, 4 + math.sin(ang) * r * .55 * (1 + (k % 2) * .4)
            shaded(a, [(px - 2.6, py), (px + 2.6, py), (px + (k - 4) * .7, py + 10 + (k % 3) * 3)], RAINBOW[k % 5], base=.7)
        dust(a, 30, 3, 3.4, PEARL)
        dust(a, -20, 3, 3, PEARL)
    return a


def shatter_king(a, n, dn):
    """The Shard-King comes apart: slabs fall in turn and lie in a pile under the crown."""
    k = n / 7.
    rng = np.random.RandomState(7)
    ground = 4
    pieces = [
        ('foot', -18, 12, 34, 14, CRYSTAL), ('foot', 20, 12, 34, 14, ICE), ('leg', -18, 40, 28, 40, CRYSTAL), ('leg', 18, 40, 28, 40, CRYSTAL),
        ('chest', 0, 90, 76, 52, CRYSTAL), ('pauld', -52, 122, 34, 22, CRYSTAL), ('pauld', 54, 122, 34, 22, ICE),
        ('arm', -62, 84, 20, 46, CRYSTAL), ('arm', 64, 84, 20, 46, ICE), ('head', 0, 160, 38, 38, ICE),
    ]
    rest = {'foot': (0, 8), 'leg': (0, 16), 'chest': (0, 24), 'pauld': (0, 14), 'arm': (0, 8), 'head': (0, 40)}
    for i, (name, x, y, w_, h_, ramp) in enumerate(pieces):
        start = (i % 5) * .1
        t = clamp01((k - start) / .55)
        fall = t * t
        rx = rest[name][0] + (x * .55 if name in ('foot', 'leg') else x * .8) + (i - 5) * (6 if name != 'foot' else 2)
        ry = rest[name][1] + (i % 3) * 5 * (name != 'head')
        px = mix(x, rx, fall)
        py = mix(y, max(ground + h_ / 2, ry), fall)
        tilt = (i - 4) * .08 * fall
        pts = [(-w_ / 2, -h_ / 2), (w_ / 2, -h_ / 2 + 2), (w_ / 2 - 3, h_ / 2), (0, h_ / 2 + 4), (-w_ / 2 + 2, h_ / 2 - 2)]
        pts = [(px + x0 * math.cos(tilt) - y0 * math.sin(tilt), py + x0 * math.sin(tilt) + y0 * math.cos(tilt)) for x0, y0 in pts]
        shaded(a, pts, ramp, base=.6, contrast=1.1)
        if name == 'chest' and k < .6:
            glow(a, px, py, 26, ICE, .8 * (1 - k))
    for j in range(5):                                                                                       # the crown lies on the pile
        t = clamp01((k - .3) / .6)
        cx = -20 + j * 10
        cy = mix(184 - j * 3, 44 + (j % 2) * 4, t * t)
        shaded(a, [(cx - 4, cy), (cx + 4, cy), (cx + (j - 2) * 3 * t, cy + mix(30, 9, t))], RAINBOW[j], base=.7, contrast=1.2)
    for j in range(int(k * 14)):                                                                             # loose shards fly out
        ang = rng.uniform(.2, math.pi - .2)
        r = rng.uniform(20, 60) * (.3 + k)
        px, py = math.cos(ang) * r * 1.5, max(ground + 2, 70 + math.sin(ang) * r * 1.1 - k * k * 70)
        shaded(a, [(px - 2.2, py), (px + 2.2, py), (px, py + 6)], RAINBOW[j % 5], base=.7)
    return a


# ---- Heimdall's Shade ------------------------------------------------------------------------------------------------------------
def heimdallr(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    a = Painter('heimdallr', st * 6 - w * 4 + recoil)
    walk = clip == 'walk'
    hov = 6 + bob * .8 + (math.sin(ph * 2) * 1.6 if walk else 0) - w * 3
    sway = math.sin(ph * 1.3) * 4 if clip in ('idle', 'walk') else -st * 8
    R = Rig(a, 0, hov + 60, -w * .06 + st * .12)
    T = lambda pts: [R.t(*p) for p in pts]
    top = hov + 126
    # the cloak: broad, streaming back, ragged to the ground
    cl = [(-18, top - 8), (-30, top - 30), (-56 + sway * .5, top - 50), (-80 + sway, top - 82), (-98 + sway * 1.4 - st * 6, hov + 6), (-78 + sway, hov + 22), (-64 + sway, hov + 2), (-46, hov + 18), (-30, hov + 4), (-16, hov + 24)]
    shaded(a, smooth(T(cl), 4), CLOAK, base=.3, contrast=1.1)
    for k in range(5):                                                  # the folds
        a.line(T([(-24 - k * 3, top - 22 - k * 6), (-46 - k * 9 + sway * (k + 1) * .2, top - 62 - k * 5), (-66 - k * 6 + sway, hov + 24 + k * 3)]), CLOAK[1], 1)
    # the robe, a long tattered hem that fades into the sky
    robe = smooth(T([(-26, top - 8), (26, top - 8), (36, hov + 66), (32, hov + 30), (38, hov + 4), (22, hov + 12), (10, hov + 2), (-2, hov + 14), (-14, hov + 2), (-26, hov + 12), (-40, hov + 3), (-32, hov + 32), (-36, hov + 66)]), 3)
    shaded(a, robe, CLOAK, base=.55, contrast=1.1)
    for k in range(4):
        a.line(T([(-18 + k * 12, hov + 66), (-20 + k * 13, hov + 22), (-22 + k * 13, hov + 6)]), CLOAK[1], 1)
    # the breastplate and gorget, the great round pauldrons
    shaded(a, T([(-26, top - 8), (26, top - 8), (22, top - 50), (0, top - 62), (-22, top - 50)]), PLATE, base=.6, contrast=1.2)
    a.line(T([(0, top - 10), (0, top - 58)]), PLATE[1], 1)
    a.line(T([(-22, top - 38), (0, top - 44), (22, top - 38)]), PLATE[1], 1)
    shaded(a, T([(-30, top - 8), (30, top - 8), (24, top - 18), (-24, top - 18)]), PLATE, base=.7, contrast=.8)
    for s in (-1, 1):
        R.ball(s * 32, top - 14, 15, 12, PLATE)
        a.line(T([(s * 22, top - 14), (s * 40, top - 14)]), PLATE[0], 1)
    # the horn in the far hand: at the chest when idle, at the lips on the wind-up (all in painter coordinates)
    horn_idle, horn_up = (-26, top - 38), (14, top + 12)
    hh = mixp(mixp(horn_idle, horn_up, w), (22, top - 6), st)
    hp = R.t(*hh)
    shaded(a, capsule(R.t(-34, top - 14), (hp[0] - 6, hp[1] - 10), 11, 9, 4), CLOAK, base=.4)
    shaded(a, capsule((hp[0] - 6, hp[1] - 10), hp, 9, 9, 4), PLATE, base=.4)
    path = bez((hp[0] - 4, hp[1] + 2), (hp[0] + 6, hp[1] + 26), (hp[0] + 34, hp[1] + 22), 12)
    horn = [(px + 3 * (i / (len(path) - 1)) ** 2, py - 3 - 11 * (i / (len(path) - 1)) ** 2) for i, (px, py) in enumerate(path)]
    horn += [(px - 3 * (i / (len(path) - 1)) ** 2, py + 2.5 + 6 * (i / (len(path) - 1)) ** 2) for i, (px, py) in reversed(list(enumerate(path)))]
    shaded(a, horn, HORN, base=.62, contrast=1.3)
    bell = path[-1]
    a.line([(bell[0] + 1, bell[1] - 12), (bell[0] + 4, bell[1]), (bell[0] + 1, bell[1] + 12)], OUTLINE, 2)
    a.line([(bell[0] + 2, bell[1] - 9), (bell[0] + 4, bell[1]), (bell[0] + 2, bell[1] + 9)], HORN[1], 1)
    a.line([(path[2][0], path[2][1] + 4), (path[7][0], path[7][1] + 9)], HORN[4], 1)
    # the spear in the near hand: drawn back on the wind-up, thrust on the strike
    hand = mixp(mixp((30, top - 40), (10, top - 34), w), (30, top - 38), st)
    sh = R.t(34, top - 12)
    hnd = R.t(*hand)
    elb = ((sh[0] + hnd[0]) / 2 + 8 + st * 6, (sh[1] + hnd[1]) / 2 - 2)
    shaded(a, capsule(sh, elb, 11, 9, 4), PLATE, base=.6)
    shaded(a, capsule(elb, hnd, 9, 8, 4), PLATE, base=.5)
    ang = mix(mix(1.5, 1.2, w), .1, st)
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    butt = (hnd[0] - dx * 40, hnd[1] - dy * 40)
    tip = (hnd[0] + dx * 44, hnd[1] + dy * 44)
    a.line([butt, tip], PLATE[1], 3)
    a.line([(butt[0] - 1, butt[1] + 1), (tip[0] - 1, tip[1] + 1)], PLATE[3], 1)
    shaded(a, [(tip[0] - nx * 5, tip[1] - ny * 5), (tip[0] + dx * 20, tip[1] + dy * 20), (tip[0] + nx * 5, tip[1] + ny * 5), (tip[0] - dx * 4, tip[1] - dy * 4)], ICE, base=.7, contrast=1.2)
    a.line([tip, (tip[0] + dx * 20, tip[1] + dy * 20)], ICE[4], 1)
    a.ball(hnd[0], hnd[1], 4.4, 4.4, PLATE)
    # the head: a winged helm over a dark face and two cold lights
    hc = top + 12
    helm = T(smooth([(-15, hc - 14), (15, hc - 14), (18, hc + 6), (10, hc + 20), (0, hc + 24), (-10, hc + 20), (-18, hc + 6)], 3))
    shaded(a, helm, PLATE, base=.62, contrast=1.2)
    a.poly(T([(-12, hc - 2), (12, hc - 2), (13, hc - 14), (-13, hc - 14)]), PLATE[1], outline=OUTLINE)
    a.poly(T([(-11, hc + 8), (11, hc + 8), (12, hc - 1), (-12, hc - 1)]), OUTLINE)
    a.line(T([(0, hc + 22), (0, hc + 8)]), PLATE[3], 1)
    for ex in (-6, 6):
        e = R.t(ex, hc + 3.5)
        if dying(clip, n, 2):
            a.line([(e[0] - 2.5, e[1]), (e[0] + 2.5, e[1])], OUTLINE, 1)
        else:
            glow(a, e[0], e[1], 7, ICE, .9)
            a.poly([(e[0] - 3.5, e[1] - 1.8), (e[0] + 3.5, e[1] - 1.8), (e[0] + 3.5, e[1] + 1.8), (e[0] - 3.5, e[1] + 1.8)], ICE[4])
    for s_ in (-1, 1):                                                  # the wings on the helm
        base = R.t(s_ * 15, hc + 8)
        tipw = (base[0] + s_ * 22, base[1] + 26 + (math.sin(ph) * 2 if clip in ('idle', 'walk') else 0))
        wing = [base, (base[0] + s_ * 9, base[1] + 6), tipw, (base[0] + s_ * 15, base[1] + 16), (base[0] + s_ * 5, base[1] - 3)]
        shaded(a, wing, MANE, base=.6, contrast=1.1)
        a.line([base, tipw], MANE[4], 1)
    shaded(a, T([(-4, hc + 20), (6, hc + 20), (1, hc + 40)]), PLATE, base=.7)
    if clip == 'attack' and n in (4, 5, 6):                             # three rings of sound off the horn
        c = (bell[0] + 6, bell[1])
        for k in range(3):
            r = 10 + k * 9 + (n - 4) * 6
            pts = [(c[0] + math.cos(t) * r * .55, c[1] + math.sin(t) * r) for t in np.linspace(-1.25, 1.25, 11)]
            a.line(pts, ICE[3] if k % 2 else ICE[2], 2 if k == 0 else 1)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, 20 + k * 8, 4 + (k % 2) * 4, 3 - k * .4, PEARL)
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
    noise = (np.sin(xs * 12.9898 + ys * 78.233) * 43758.5453) % 1
    band = (ys / max(1, h)) * .35
    ok = noise + band * dn * 1.6 > dn * 1.25 - .05
    keep[ys[ok], xs[ok]] = grid[ys[ok], xs[ok]]
    if dn > .1:
        for j in range(int(10 + 28 * dn)):
            i = rng.randint(len(xs))
            lift = int(dn * rng.uniform(6, 34))
            x, y = xs[i] + rng.randint(-2, 3), ys[i] - lift
            if 2 < y < h - 2 and 2 < x < w_ - 2:
                keep[y, x] = ICE[3 if j % 2 else 4]
                if j % 3 == 0 and y > 3:
                    keep[y - 1, x] = ICE[2]
    pal = a.im.getpalette()
    a.im = Image.fromarray(keep, 'P')
    if pal:
        a.im.putpalette(pal)
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
