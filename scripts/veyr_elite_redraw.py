#!/usr/bin/env python3
"""The Veyrroot's three new elites (zone shapes pilot): native PixelFlow sources with their own frames.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  lanternqueen  The Lantern Queen (level 82, quest, flies): a wasp queen the size of a wagon. A dark chitin thorax striped with amber, four glass wings, six hooked legs, a head with two big
                slanted red compound eyes under a scowling ridge and a pair of serrated pale mandibles, and a fat abdomen that burns like a lantern with a hooked black stinger. Winds up by curling
                the abdomen up and forward over her back with the wings flung up and the mandibles wide; the strike drives the stinger forward and down; she recovers with the abdomen swinging back.
                Dies when the wings crumple, the glow goes out, the body drops and rolls onto its back with the legs curled.
  barkcolossus  The Heartbark Colossus (level 84, quest): a walking grove. A hunched trunk of split bark with a crown of moss and fungus on its shoulders, two huge root-arms ending in knotted
                knuckles, stump legs, a head sunk between the shoulders with a jagged brow ridge, pinprick green eyes and a gaping crack of a mouth full of splinters. Winds up by raising both
                root-arms over its head; the strike brings them down together; it recovers heaving them back up. Dies when the eyes go out and it topples forward and splits into logs.
  ambergolem    The Amber Sap Golem (level 83, no quest): a hulk of hardened sap, faceted and translucent, with whole insects trapped dark inside, a molten core burning in its chest, jagged amber
                spikes along its shoulders, a wedge skull with two hollow slits and a pair of block fists. Winds up by dragging the right fist back and up; the strike slams it forward and down; it
                recovers with a slow lift. Dies as cracks run across it and the core flickers out, then it breaks into amber chunks.
The manifest is client/assets/veyrelites.txt. The shading helpers are copied from lapis_elite_redraw.py.
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
from astral_slime_redraw import arm_ik, taper
from moonspore_slime_redraw import fang, plate
from lapis_slime_redraw import teeth

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/veyr-elites'
REGISTRY = ROOT / 'scripts/veyr_elite_sources.txt'
MANIFEST = ASSETS / 'veyrelites.txt'
PREFIX = 'valhallasc_veyr_elite_'
KINDS = ['lanternqueen', 'barkcolossus', 'ambergolem']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(lanternqueen=(160, 144, 76, 136), barkcolossus=(130, 144, 52, 136), ambergolem=(122, 140, 44, 132))
SCALE = dict(lanternqueen=.8, barkcolossus=.8, ambergolem=.8)
FLYING = ('lanternqueen',)
_mine = [
    '#2a1200', '#7a3406', '#d07a14', '#ffb83c', '#fff0a8',   # AMBER (the queen's lantern abdomen)
    '#0c0806', '#281a12', '#4a3222', '#6e4e36', '#9a7550',   # CHITIN (the thorax and legs)
    '#1c2c2a', '#4a6e66', '#8cb8a8', '#c8e8d8', '#f0fff4',   # WING (glass)
    '#2a0408', '#7a0e1a', '#c8281e', '#ff6a38', '#ffd8b0',   # EYER (compound eyes)
    '#14161a', '#34383e', '#586068', '#848c94', '#b4bcc4',   # GREYQ (everything dead)
    '#0e0a06', '#2e2014', '#523a22', '#7e5c38', '#b08a58',   # BARK
    '#0c2012', '#1e4a26', '#3a7a3a', '#68aa4c', '#a8d870',   # MOSS
    '#06200e', '#0e6030', '#20b060', '#70f0a0', '#e0ffe8',   # HEART (the green eyes)
    '#2a2214', '#6a5a3a', '#a89868', '#d8caa0', '#f4ecd0',   # PALE (splinters)
    '#3a1400', '#8a4204', '#d07a10', '#f4a828', '#ffd868',   # SAP (the golem's amber)
    '#5a0800', '#c82a00', '#ff6a10', '#ffb030', '#fff4a0',   # CORE (the molten core)
    '#0a0604', '#1c1208', '#34240e', '#503818', '#705028',   # BUGS (the trapped insects)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
AMBER, CHITIN, WING, EYER, GREYQ, BARK, MOSS, HEART, PALE, SAP, CORE, BUGS = [_i[5 * k:5 * k + 5] for k in range(12)]


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


# ---- shared -------------------------------------------------------------------------------------------------------------------------
def rot2(u, v, ang):
    c, s = math.cos(ang), math.sin(ang)
    return u * c - v * s, u * s + v * c


def seg(a, p, q, w0, w1, ramp, base=.58, contrast=1., light=(-.55, .8)):
    shaded(a, capsule(p, q, w0, w1, 4), ramp, light=light, base=base, contrast=contrast)


def leaf_blade(a, p, ang, ln, wd, ramp, base=.6):
    """A pointed leaf / wing blade from p along ang."""
    tip = (p[0] + math.cos(ang) * ln, p[1] + math.sin(ang) * ln)
    nx, ny = -math.sin(ang) * wd / 2, math.cos(ang) * wd / 2
    mid = (p[0] + math.cos(ang) * ln * .45, p[1] + math.sin(ang) * ln * .45)
    pts = [p, (mid[0] + nx, mid[1] + ny), tip, (mid[0] - nx * .8, mid[1] - ny * .8)]
    shaded(a, smooth(pts, 4), ramp, light=(-.4, .85), base=base, contrast=.9)
    return tip


# ---- the Lantern Queen ----------------------------------------------------------------------------------------------------------------
def lanternqueen(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05
    a = Painter('lanternqueen', st * 7 - w * 6 + recoil)
    live = 1 - dn
    gb, gh = clamp01(dn * 2.2 - .2), clamp01(dn * 1.8 - .5)
    R = lambda ramp, g: GREYQ if g > .55 else ramp
    # the body hangs in the air: it dips on the strike, rises on the wind-up and drops when it dies, rolling onto its back
    hy = 68 + math.sin(ph * 1.3) * 3.2 * live + bob * .5 + w * 4 + st * 17 - dn * 45 + (3 if hurt else 0)
    phi = w * .30 - st * .34 + dn * 2.5 + (.12 if hurt else 0)
    r = Rig(a, 0, hy, phi)
    T = lambda p: r.t(p[0], hy + p[1])
    # ---- the abdomen: rest hangs behind and low, the wind-up curls it up and over, the strike drives the stinger forward and down
    rest = [(-12, -2), (-30, -6), (-50, -10), (-64, -14)]
    wind = [(-12, 0), (-30, 6), (-44, 26), (-34, 46)]
    strike = [(-12, -2), (-26, -10), (-8, -28), (32, -40)]
    P = [mixp(mixp(rest[i], wind[i], w), strike[i], st) for i in range(4)]
    P = [(x, y - dn * 4) for x, y in P]
    wd = [15, 31, 28, 9]
    # ---- far legs and far wings go behind
    def wing(base, ang0, ln, wdt, flap, far):
        ang = ang0 + flap
        ramp = WING if not far else [WING[0], WING[0], WING[1], WING[1], WING[2]]
        tip = leaf_blade(a, T(base), ang + phi, ln, wdt, R(ramp, gh))
        a.line([T(base), tip], R(WING, gh)[4] if gh < .55 else GREYQ[3], 1)
    flap = math.sin(ph * 2.2) * .38 * live
    spread = .55 + w * .75 - dn * 1.35 - st * .2
    wing((-4, 11), 1.9 - spread * .35 + flap, 60 - dn * 24, 24, 0, True)
    wing((-7, 11), 2.45 - spread * .3 + flap * .8, 46 - dn * 18, 18, 0, True)
    def leg(x0, off, far):
        sw = math.sin(ph * 1.1 + off) * 3.5 * live
        curl = dn
        knee = (x0 + 6 - curl * 6 + sw, -22 + curl * 14)
        foot = (x0 + 12 - curl * 10 + sw * 1.5, -34 + curl * 28)
        ramp = CHITIN if not far else [CHITIN[0], CHITIN[0], CHITIN[1], CHITIN[1], CHITIN[2]]
        r.limb([(x0, hy - 8), (knee[0], hy + knee[1]), (foot[0], hy + foot[1])], R(ramp, gh), 3.4)
        fang(a, *T((foot[0], foot[1])), 6, 2.4, -1.2 + phi - dn * 1.0, R(CHITIN, gh) if gh < .55 else GREYQ)
    for x0, off in ((12, 0.), (0, 2.1), (-10, 4.2)):
        leg(x0, off, True)
    # ---- the abdomen, bright as a lantern: three banded segments
    seg(a, T(P[0]), T(P[1]), wd[0], wd[1], R(AMBER, gb), base=.62, contrast=1.1)
    seg(a, T(P[1]), T(P[2]), wd[1], wd[2], R(AMBER, gb), base=.62, contrast=1.1)
    seg(a, T(P[2]), T(P[3]), wd[2], wd[3], R(AMBER, gb), base=.6, contrast=1.0)
    for i in (1, 2):                                                  # dark chitin bands
        x, y = T(P[i])
        a.line([(x - 6, y - 14), (x - 4, y + 14)], R(CHITIN, gb)[1], 2)
    for k in range(3):
        px, py = mixp(P[1], P[2], .2 + k * .3)
        a.ellipse(*T((px, py + 5)), 2.6, 1.8, R(AMBER, gb)[4])
    if gb < .55:
        gx, gy = mixp(P[1], P[2], .5)
        glow(a, *T((gx, gy)), 34 + w * 6 + st * 4, AMBER, .75 + (w + st) * .2)
    # the stinger: a hooked black barb, longer and wider on the strike
    sx, sy = P[3]
    ang = math.atan2(P[3][1] - P[2][1], P[3][0] - P[2][0])
    tip = (sx + math.cos(ang) * (13 + st * 8), sy + math.sin(ang) * (13 + st * 8))
    hook = (tip[0] + math.cos(ang - 1.1) * 7, tip[1] + math.sin(ang - 1.1) * 7)
    a.poly([T((sx + math.cos(ang + 1.57) * 4, sy + math.sin(ang + 1.57) * 4)), T(tip), T(hook), T((sx + math.cos(ang - 1.57) * 4, sy + math.sin(ang - 1.57) * 4))], R(CHITIN, gb)[0], outline=R(CHITIN, gb)[1])
    # ---- the thorax: dark chitin with amber stripes and a fur ruff
    thorax = [(-17, 2), (-14, 13), (0, 18), (14, 13), (18, 0), (10, -12), (-6, -14), (-16, -8)]
    pts = smooth(thorax, 4)
    shaded(a, [r.t(x, hy + y) for x, y in pts], R(CHITIN, gh), light=(-.5, .85), base=.55, contrast=1.1, grain=.05)
    for k in range(3):
        a.line([T((-9 + k * 9, 14 - k)), T((-7 + k * 9, -11))], R(AMBER, gb)[2], 2)
    # ---- the near wings, over the thorax
    wing((2, 13), 1.5 - spread * .25 + flap, 66 - dn * 28, 26, 0, False)
    wing((-2, 12), 2.0 - spread * .3 + flap * .9, 50 - dn * 20, 20, 0, False)
    # ---- near legs
    for x0, off in ((16, 1.0), (4, 3.1), (-6, 5.2)):
        leg(x0, off, False)
    # ---- the head: dark, broad, two big slanted red compound eyes under a scowling ridge, serrated mandibles (drawn 1.4 times larger about the neck)
    hs = 1.4
    hx0, hy0 = 25, 4
    HT = lambda p: T((hx0 + (p[0] - hx0) * hs, hy0 + (p[1] - hy0) * hs))
    head = [(-10, 8), (0, 14), (14, 12), (20, 4), (18, -8), (6, -13), (-8, -9)]
    pts = [(hx0 + x, hy0 + y) for x, y in smooth(head, 3)]
    shaded(a, [HT(p) for p in pts], R(CHITIN, gh), light=(-.5, .85), base=.6, contrast=1.1)
    ex, ey = hx0 + 6, hy0 + 3
    eye = [(ex - 6, ey - 1), (ex - 3, ey + 8), (ex + 5, ey + 9), (ex + 8, ey), (ex + 3, ey - 8), (ex - 4, ey - 7)]
    a.poly([HT(p) for p in smooth(eye, 3)], R(EYER, gh)[1], outline=OUTLINE)
    a.poly([HT((ex - 3, ey - 2)), HT((ex + 3, ey + 4)), HT((ex + 5, ey - 1)), HT((ex, ey - 5))], R(EYER, gh)[3] if gh < .5 else GREYQ[2])
    for k in range(5):                                                   # facets of the compound eye
        a.line([HT((ex - 4 + k * 2.4, ey - 6 + (k % 2) * 3)), HT((ex - 3 + k * 2.4, ey + 6 - (k % 2) * 3))], R(EYER, gh)[0], 1)
    if gh < .5:
        glow(a, *HT((ex + 1, ey)), 12 + w * 4 + st * 4, EYER, .6)
        a.ellipse(*HT((ex + 2, ey + 3)), 2.2, 1.6, EYER[4])
    else:
        a.line([HT((ex - 4, ey - 4)), HT((ex + 5, ey + 5))], OUTLINE, 2)
        a.line([HT((ex - 4, ey + 5)), HT((ex + 5, ey - 4))], OUTLINE, 2)
    a.poly([HT((hx0 - 8, hy0 + 15)), HT((hx0 + 17, hy0 + 11)), HT((hx0 + 18, hy0 + 3)), HT((hx0 + 5, hy0 + 9)), HT((hx0 - 6, hy0 + 10))], OUTLINE)     # the scowling ridge
    op = .3 + (w + st) * .55 + (.45 if clip == 'attack' and 2 <= n <= 5 else 0) + (.3 if hurt else 0)
    for side in (1, -1):                                                # two serrated mandibles
        base = (hx0 + 17, hy0 - 6)
        ang = -1.1 - side * op * .55 - dn * .3
        fang(a, *HT(base), 24, 7, ang, BONE)
        tip = (base[0] + math.cos(ang) * 17, base[1] + math.sin(ang) * 17)
        for k in range(4):
            tx = base[0] + (tip[0] - base[0]) * (k + 1) / 5.2
            ty = base[1] + (tip[1] - base[1]) * (k + 1) / 5.2
            a.poly([HT((tx, ty)), HT((tx - 2.4, ty - 3.8 * side + 2)), HT((tx + 2.4, ty - 1))], BONE[3])
    for k in (1, -1):                                                   # two long antennae
        line_pts = bez((hx0 + 6, hy0 + 11), (hx0 + 22, hy0 + 26 + k * 4 + live * math.sin(ph + k) * 2), (hx0 + 34 + k * 3, hy0 + 20 + k * 6), 6)
        a.line([HT(p) for p in line_pts], R(CHITIN, gh)[3], 1)
    return a


# ---- the Heartbark Colossus ---------------------------------------------------------------------------------------------------------
def barkcolossus(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05
    a = Painter('barkcolossus', st * 6 - w * 5 + recoil - dn * 34)
    live = 1 - dn
    gb = 0.                                                               # it stays bark when it dies: only the eyes go out
    R = lambda ramp: GREYQ if gb > .55 else ramp
    by = 50 + bob * .5 - w * 3 + st * 3 - dn * 14                       # hip height
    phi = -dn * .5 - w * .07 + st * .12 - (.1 if hurt else 0)           # slumps forward when it dies
    r = Rig(a, 0, 0, phi, lift=dn * 16)
    T = lambda p: r.t(p[0], p[1])
    sway = math.sin(ph) * (8 if walk else 1.0) * live
    # ---- far arm and far leg
    def leg(hx, off, far):
        s = math.sin(ph + off) * (8 if walk else .8) * live
        lift = max(0., math.cos(ph + off)) * (5 if walk else 0) * live
        pts = [T((hx, by)), T((hx + 4 + s * .4, by * .5)), T((hx + 8 + s, 6 + lift))]
        a.limb(pts, R([BARK[0], BARK[0], BARK[1], BARK[1], BARK[2]] if far else BARK), 17 if not far else 15)
        foot = [(hx - 6 + s, 0 + lift), (hx + 20 + s, 0 + lift), (hx + 18 + s, 9 + lift), (hx - 2 + s, 11 + lift)]
        shaded(a, [T(p) for p in foot], R(BARK), light=(-.5, .85), base=.5, contrast=.9)
        for k in range(3):
            a.line([T((hx + 2 + k * 6 + s, 9 + lift)), T((hx + 4 + k * 6 + s, 1 + lift))], R(BARK)[0], 1)
    leg(-12, math.pi, True)
    # arm targets: hanging low at rest, overhead on the wind-up, slammed in front on the strike
    def fist_target(near):
        rest = (34 + (5 if near else -8) + sway * .3, 22 + (0 if near else 4))
        up = (18 + (6 if near else -6), 150)
        down = (64 + (6 if near else -2), 8)
        p = mixp(mixp(rest, up, w), down, st)
        return (p[0] - dn * 8, p[1] * (1 - dn * .7) + dn * 3)
    sh_far = (22, by + 56)
    el, fh = arm_ik(sh_far, fist_target(False), 40, 40, bend=-1 if (st > .5 or w > .5) else 1)
    a.limb([T(sh_far), T(el), T(fh)], R([BARK[0], BARK[0], BARK[1], BARK[1], BARK[2]]), 15)
    a.ball(*T(fh), 11, 10, R([BARK[0], BARK[1], BARK[1], BARK[2], BARK[3]]))
    # ---- the torso: a hunched trunk of split bark
    torso = [(-30, by - 4), (-36, by + 30), (-28, by + 68), (-4, by + 86), (26, by + 84), (44, by + 60), (36, by + 22), (30, by - 6)]
    shaded(a, [T(p) for p in smooth(torso, 4)], R(BARK), light=(-.5, .85), base=.55, contrast=1.15, grain=.07)
    for k in range(6):                                                  # cracks and ridges of the bark
        x = -26 + k * 11
        a.line([T((x, by + 6 + (k % 2) * 6)), T((x + 2, by + 34)), T((x - 1, by + 60 + (k % 3) * 4))], R(BARK)[0], 1)
        a.line([T((x + 2, by + 8)), T((x + 4, by + 36))], R(BARK)[4], 1)
    for k in range(4):                                                  # fungal shelves and moss
        px, py = -18 + k * 13, by + 18 + (k % 2) * 22
        a.ellipse(*T((px, py)), 7, 3, R(PALE)[3])
        a.ellipse(*T((px, py + 1)), 6, 2, R(PALE)[1])
    for k in range(8):
        a.ellipse(*T((-30 + k * 9, by + 80 - (k % 3) * 3)), 7, 4, R(MOSS)[2 + k % 2])
    # ---- near leg
    leg(8, 0., False)
    # ---- the head, sunk between the shoulders: a jagged brow, two pinpoint green eyes, a crack of a mouth full of splinters
    hx, hy = 28 + st * 4 - w * 3, by + 92 - st * 6 - dn * 6
    head = [(-14, -8), (-12, 12), (0, 20), (14, 16), (22, 4), (20, -10), (6, -16)]
    shaded(a, [T((hx + x, hy + y)) for x, y in smooth(head, 3)], R(BARK), light=(-.5, .85), base=.6, contrast=1.1)
    a.poly([T((hx - 14, hy + 15)), T((hx - 6, hy + 11)), T((hx + 2, hy + 14)), T((hx + 10, hy + 9)), T((hx + 18, hy + 12)), T((hx + 25, hy + 3)), T((hx + 22, hy - 1)), T((hx + 8, hy + 4)), T((hx - 2, hy + 1)), T((hx - 12, hy + 4))], OUTLINE)      # the jagged brow, low over the eyes
    open_ = .55 + (w + st) * .5 + (.3 if hurt else 0)
    mouth = [(hx - 2, hy - 4), (hx + 14, hy - 5), (hx + 16, hy - 5 - 6 * open_ - 2), (hx + 6, hy - 5 - 9 * open_ - 3), (hx - 1, hy - 5 - 4 * open_)]
    a.poly([T(p) for p in mouth], R(HEART)[0] if gb < .55 else OUTLINE, outline=OUTLINE)
    for k in range(4):
        mx = hx + 1 + k * 3.6
        a.poly([T((mx - 1.4, hy - 4.5)), T((mx + 1.4, hy - 4.5)), T((mx, hy - 4.5 - 4.5))], R(PALE)[4], outline=R(PALE)[0])
        a.poly([T((mx - 1.4, hy - 5.5 - 6 * open_)), T((mx + 1.4, hy - 5.5 - 6 * open_)), T((mx, hy - 5.5 - 6 * open_ + 3.5))], R(PALE)[3], outline=R(PALE)[0])
    for dx in (4, 14):
        ex, ey = hx + dx, hy + 4
        if dn > .3:
            a.line([T((ex - 2, ey - 2)), T((ex + 2, ey + 2))], OUTLINE, 2)
            a.line([T((ex - 2, ey + 2)), T((ex + 2, ey - 2))], OUTLINE, 2)
        else:
            glow(a, *T((ex, ey)), 9 + (w + st) * 3, HEART, .8)
            a.ellipse(*T((ex, ey)), 3.4, 2.2, HEART[3])
            a.ellipse(*T((ex + .6, ey + .4)), 1.6, 1.0, HEART[4])
    # ---- the crown on the shoulders: moss, ferns and a bracket fungus
    for k, (x, y, ln) in enumerate(((-26, by + 82, 18), (-12, by + 90, 22), (6, by + 96, 20), (22, by + 92, 17), (36, by + 80, 16), (-34, by + 70, 14))):
        for j in range(3):
            ang = 1.57 + (j - 1) * .55 + (k - 2.5) * .12
            a.line([T((x, y)), T((x + math.cos(ang) * ln, y + math.sin(ang) * ln * .8))], R(MOSS)[1 + (j + k) % 3], 2)
    a.ellipse(*T((-4, by + 90)), 9, 4, R(PALE)[2])
    # ---- near arm over everything
    sh = (30, by + 54)
    el, fh = arm_ik(sh, fist_target(True), 42, 42, bend=-1 if (st > .5 or w > .5) else 1)
    a.limb([T(sh), T(el), T(fh)], R(BARK), 17)
    for k in range(3):
        a.line([T((el[0] - 4 + k * 3, el[1] + 4)), T((el[0] - 3 + k * 3, el[1] - 4))], R(BARK)[0], 1)
    a.ball(*T(fh), 13, 12, R(BARK))
    for k in range(3):                                                  # knuckle knots
        a.ellipse(*T((fh[0] - 5 + k * 5, fh[1] + 4)), 2.6, 2.2, R(BARK)[4])
    a.ellipse(*T((fh[0], fh[1] + 8)), 5, 3, R(MOSS)[2])
    if clip == 'attack' and n in (4, 5):
        for k in range(4):
            dust(a, 52 + k * 8, 3 + (k % 2) * 3, 3.2 - k * .4, PEARL)
    if dn > .5:
        for k in range(3):
            dust(a, -20 + k * 26, 2 + (k % 2) * 2, 3. + dn, PEARL)
    return a


# ---- the Amber Sap Golem -----------------------------------------------------------------------------------------------------------
BUG_SPOTS = [(-18, 24, .4), (-6, 40, -.7), (8, 28, .9), (18, 50, -.3), (-22, 54, .2), (2, 62, 1.1), (-10, 14, -.2)]


def ambergolem(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05
    a = Painter('ambergolem', st * 5 - w * 5 + recoil)
    live = 1 - dn
    gb = 0.                                                               # it stays amber as it breaks: the core and eyes go out
    R = lambda ramp: GREYQ if gb > .85 else ramp
    # the core flickers out as it dies
    core_on = 1. - clamp01(dn * 1.8)
    squash = 1. - dn * .5                                                 # it slumps and shatters
    by = (46 + bob * .4 - w * 3 + st * 2) * squash
    sway = math.sin(ph) * (7 if walk else .9) * live
    Y = lambda y: y * squash
    # ---- far arm, far leg
    def leg(hx, off, far):
        s = math.sin(ph + off) * (7 if walk else .7) * live
        lift = max(0., math.cos(ph + off)) * (4 if walk else 0) * live
        ramp = [SAP[0], SAP[0], SAP[1], SAP[1], SAP[2]] if far else SAP
        a.limb([(hx, by), (hx + 3 + s * .4, Y(24)), (hx + 6 + s, 5 + lift)], R(ramp), 19 if not far else 17)
        foot = [(hx - 8 + s, 0 + lift), (hx + 18 + s, 0 + lift), (hx + 16 + s, 10 + lift), (hx - 4 + s, 11 + lift)]
        shaded(a, foot, R(SAP), light=(-.5, .85), base=.55, contrast=.9)
    leg(-12, math.pi, True)
    def fist_target(near):
        rest = (40 + (4 if near else -10) + sway * .3, 20 + (0 if near else 5))
        back = (-14 + (0 if near else -6), 104)
        slam = (64 + (6 if near else 0), 8)
        brace = (46, 36)
        p = mixp(rest, back, w if near else w * .25)
        p = mixp(p, slam if near else brace, st)
        return (p[0] - dn * 10, Y(p[1]) + dn * 2)
    sh_far = (20, by + 52)
    el, fh = arm_ik(sh_far, fist_target(False), 38, 38, bend=-1 if st > .5 else 1)
    a.limb([sh_far, el, fh], R([SAP[0], SAP[0], SAP[1], SAP[1], SAP[2]]), 16)
    shaded(a, [(fh[0] - 11, fh[1] - 9), (fh[0] + 11, fh[1] - 9), (fh[0] + 13, fh[1] + 9), (fh[0] - 9, fh[1] + 11)], R(SAP), base=.5)
    # ---- the body: a faceted slab of hardened sap
    body = [(-30, by - 2), (-38, Y(by + 30)), (-30, Y(by + 66)), (-8, Y(by + 84)), (24, Y(by + 82)), (44, Y(by + 58)), (38, Y(by + 22)), (30, by - 4)]
    shaded(a, smooth(body, 3), R(SAP), light=(-.45, .85), base=.58, contrast=1.2, grain=.04)
    # facet lines
    for pts in (((-30, by + 20), (-4, Y(by + 42)), (30, Y(by + 28))), ((-26, Y(by + 60)), (0, Y(by + 48)), (36, Y(by + 52))), ((-4, Y(by + 42)), (6, Y(by + 80)))):
        a.line([(x, Y(y) if False else y) for x, y in pts], R(SAP)[4], 1)
    # trapped insects: dark silhouettes inside the sap
    for k, (bx, by2, rot) in enumerate(BUG_SPOTS):
        x, y = bx, Y(by + by2 * .6 + 6)
        if k > 3 and by2 > 60:
            continue
        a.ellipse(x, y, 4.2, 2.6, R(BUGS)[1])
        a.ellipse(x + 3, y + 1, 2.2, 1.8, R(BUGS)[2])
        for j in (-1, 0, 1):
            a.line([(x + j * 2, y - 2), (x + j * 3.4, y - 5 + rot)], R(BUGS)[1], 1)
            a.line([(x + j * 2, y + 2), (x + j * 3.4, y + 5 - rot)], R(BUGS)[1], 1)
    # the molten core in the chest
    cx_, cy_ = 4, Y(by + 52)
    a.ellipse(cx_, cy_, 11, 11 * squash, R(SAP)[0])
    if core_on > .05:
        a.ellipse(cx_, cy_, 8.5, 8.5 * squash, CORE[1])
        a.ellipse(cx_ - 1, cy_ + 1, 6, 6 * squash, CORE[2])
        a.ellipse(cx_ - 1.6, cy_ + 1.6, 3.4, 3.2 * squash, CORE[3 if core_on > .5 else 2])
        glow(a, cx_, cy_, 26 + w * 6 + st * 8, CORE, (.55 + (w + st) * .2) * core_on)
    else:
        a.ellipse(cx_, cy_, 8, 8 * squash, GREYQ[1])
    # ---- shoulder spikes
    for k, (sx, sy, ang, ln) in enumerate(((-26, by + 80, 2.3, 24), (-8, by + 86, 1.9, 28), (14, by + 86, 1.4, 26), (34, by + 70, 1.0, 22))):
        fang(a, sx, Y(sy), ln * (1 - dn * .5), 11, ang, [SAP[0], SAP[2], SAP[3], SAP[4], SAP[4]] if gb < .85 else GREYQ)
    # ---- near leg
    leg(10, 0., False)
    # ---- the head: a low wedge skull with two hollow slits lit from the core
    hx, hy = 26 + st * 4 - w * 3, Y(by + 90) - dn * 4
    head = [(-12, -8), (-12, 10), (0, 16), (16, 12), (22, 0), (18, -10), (4, -14)]
    shaded(a, [(hx + x, hy + y) for x, y in smooth(head, 3)], R(SAP), light=(-.5, .85), base=.6, contrast=1.1)
    for dx in (3, 14):
        ex, ey = hx + dx, hy + 3
        a.poly([(ex - 4, ey + 3), (ex + 4, ey + 1), (ex + 3, ey - 2), (ex - 4, ey - 1)], OUTLINE)
        if core_on > .3:
            a.poly([(ex - 3, ey + 1.6), (ex + 3, ey + .6), (ex + 2.4, ey - 1), (ex - 3, ey - .4)], CORE[3 if (w + st) > .3 else 2])
            glow(a, ex, ey, 6, CORE, .6 * core_on)
    a.poly([(hx - 12, hy + 12), (hx + 22, hy + 8), (hx + 20, hy + 3), (hx + 6, hy + 6), (hx - 10, hy + 5)], R(SAP)[0])
    # ---- cracks run across it as it dies
    if dn > 0:
        rng = [(-26, 20, -6, 46), (-4, 70, 12, 44), (22, 60, 28, 24), (-14, 44, 6, 22), (0, 30, 20, 12), (-30, 56, -14, 74)]
        for k, (x0, y0, x1, y1) in enumerate(rng):
            if dn * 7 > k:
                a.line([(x0, Y(by + y0)), ((x0 + x1) / 2 + 2, Y(by + (y0 + y1) / 2)), (x1, Y(by + y1))], OUTLINE, 1)
    # ---- near arm
    sh = (30, by + 50)
    el, fh = arm_ik(sh, fist_target(True), 40, 40, bend=-1 if (st > .5 or w > .5) else 1)
    a.limb([sh, el, fh], R(SAP), 18)
    shaded(a, [(fh[0] - 12, fh[1] - 10), (fh[0] + 12, fh[1] - 10), (fh[0] + 15, fh[1] + 10), (fh[0] - 10, fh[1] + 12)], R(SAP), base=.55)
    a.line([(fh[0] - 4, fh[1] + 6), (fh[0] + 6, fh[1] - 4)], R(SAP)[4], 1)
    # ---- the whole thing falls to chunks
    if dn > .55:
        for k, (cx, cy, rw, rh) in enumerate(((-26, 6, 12, 8), (-6, 3, 10, 6), (14, 8, 14, 9), (34, 4, 9, 6), (-38, 2, 7, 5), (52, 3, 8, 5))):
            if dn * 7 > 3.2 + k * .5:
                shaded(a, [(cx - rw, cy - rh * .3), (cx - rw * .4, cy + rh), (cx + rw * .6, cy + rh * .8), (cx + rw, cy - rh * .3)], R(SAP), base=.55)
    if clip == 'attack' and n in (4, 5):
        for k in range(4):
            dust(a, 56 + k * 7, 3 + (k % 2) * 3, 3.0 - k * .4, PEARL)
    return a


DRAW = dict(lanternqueen=lanternqueen, barkcolossus=barkcolossus, ambergolem=ambergolem)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/veyr_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='veyr-elite')
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
        atlas.save(ASSETS / f'veyrelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'veyrelites_{kind}.png').convert('RGBA')
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
