#!/usr/bin/env python3
"""Sunward Vale's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  harrowox  The Harrow Ox (level 69, no quest): a plough-ox the size of a cart that dragged its iron harrow loose and never stopped. Russet hide scarred pale along the belly and legs, a hunched shoulder
            hump under a cracked leather yoke, a long rusted chain across the back to a spiked iron harrow that scrapes along behind it, a drooping scowling head with a brass nose ring, small
            red eyes under a heavy brow, a crooked jaw of yellow teeth and two huge forward-curving horns capped in iron. Winds up by hauling the head back and up with the front hooves lifted and the
            harrow swinging high behind; the strike drops the head and the whole front half forward and down with the horns levelled and the harrow whipping over; it recovers shaking its horns free.
            Dies when its forelegs fold and the front half sinks, the head drops onto the ground, the harrow falls flat, the colour drains to grey from the rump forward and the eyes go out.
The manifest is client/assets/sunwardelites.txt (the six old Sunward enemies and the NPCs keep sunward.txt). The shading helpers are copied from cairn_elite_redraw.py.
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
OUT = ROOT / 'test-results/sunward-elites'
REGISTRY = ROOT / 'scripts/sunward_elite_sources.txt'
MANIFEST = ASSETS / 'sunwardelites.txt'
PREFIX = 'valhallasc_sunward_elite_'
KINDS = ['harrowox']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(harrowox=(192, 124, 98, 110))
SCALE = dict(harrowox=.7)
FLYING = ()
_mine = [
    '#1c0f08', '#3c2012', '#6c3a1e', '#a0602c', '#d49858',   # HIDE (the russet coat)
    '#3a2e26', '#7a6652', '#b29c7a', '#dccaa4', '#f4eacc',   # PALE (the scarred belly and legs)
    '#0e1012', '#2a2e34', '#4a5058', '#7a828c', '#b4bcc6',   # IRON (the harrow, the horn caps, the chain)
    '#2a1208', '#5c2c12', '#9a5a1c', '#d49a2c', '#f2d474',   # BRASS (the nose ring, the yoke studs)
    '#3a0a0a', '#8c1616', '#d82c1c', '#ff7c4c', '#ffe2b4',   # EYE (the red glow)
    '#18181a', '#383a3c', '#5c5e60', '#8a8c8e', '#b8babc',   # GREYD (a dead coat)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
HIDE, PALE, IRON, BRASS, EYE, GREYD = [_i[5 * k:5 * k + 5] for k in range(6)]


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

# ---- the Harrow Ox --------------------------------------------------------------------------------------------------------------
def rot2(u, v, ang):
    c, s = math.cos(ang), math.sin(ang)
    return u * c - v * s, u * s + v * c


def harrowox(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05                                                       # the last beat is not the first: the head is still coming up
    a = Painter('harrowox', st * 3 - w * 3 + recoil)
    live = 1 - dn
    # ---- greying: the colour drains from the rump forward when it dies
    gb, gh = clamp01(dn * 2.2 - .1), clamp01(dn * 1.8 - .45)
    R = lambda ramp, g: GREYD if g > .55 else ramp
    # ---- the body rides low on all fours, sinks when it dies; the front half rises on the wind-up (head hauled back) and drops on the strike (horns levelled)
    by = max(22., 40 + bob * .5 - dn * 18 - (2 if hurt else 0))
    rear = .30 * w - .34 * st - .38 * dn + (.05 if hurt else 0)
    hip = (-30., by)

    def T(x, y, k=1.):
        """A point of the front half, rotated about the hips by the pitch (k = how much of it: 0 at the rump, 1 at the shoulders)."""
        dx, dy = x - hip[0], y - hip[1]
        c, s = math.cos(rear * k), math.sin(rear * k)
        return hip[0] + dx * c - dy * s, hip[1] + dx * s + dy * c

    def Tb(x, y):                                                     # a body point: the pitch fades in from the rump to the shoulders
        return T(x, by + y, clamp01((x + 36) / 70))
    swing = lambda off, amp: math.sin(ph + off) * amp * live
    splay = dn * 1.0

    def hind(off, near):
        sw = swing(off, 7. if walk else 1.)
        lift = max(0., math.cos(ph + off)) * (4 if walk else 0) * live
        top = (-34 + (3 if near else -2), by - 4)
        knee = (-24 + sw * .4 - 10 * splay * (1 if near else -.6), by - 20 + 5 * dn)
        foot = (-30 + sw + (12 if near else 5) * splay, 4.5 + lift)
        ramp = HIDE if near else [HIDE[0], HIDE[0], HIDE[1], HIDE[1], HIDE[2]]
        tapered(a, smooth([top, knee, foot], 6, closed=False), 22 if near else 19, 13 if near else 12, R(ramp, gb), base=.55, contrast=1.0)
        a.ball(foot[0] + 2, foot[1] + 1.5, 9, 5.5, R(PALE if near else HIDE, gb))              # a pale fetlock
        a.poly([(foot[0] - 4, 0), (foot[0] + 10, 0), (foot[0] + 8, foot[1] + 4), (foot[0] - 2, foot[1] + 4)], R(IRON, gb)[1])      # a dark cloven hoof
        a.line([(foot[0] + 3, 0), (foot[0] + 3, foot[1] + 3)], R(IRON, gb)[0], 1)

    def front(off, near):
        sw = swing(off, 7. if walk else 1.)
        lift = (max(0., math.cos(ph + off)) * (4 if walk else 0) + 5 * w * (1 if near else .4)) * live
        top = T(34 + (2 if near else -4), by - 2, 1.)
        elbow = T(34 + sw * .3 + 12 * splay * (1 if near else -.5), by - 20 + 10 * dn, 1.)
        foot = T(36 + sw + (15 if near else 7) * splay, 6 + lift + 3 * dn, 1.)
        foot = (foot[0], max(foot[1], 4.5))
        ramp = PALE if near else [PALE[0], PALE[0], PALE[1], PALE[1], PALE[2]]
        tapered(a, smooth([top, elbow, foot], 6, closed=False), 23 if near else 20, 15 if near else 13, R(ramp, gb), base=.55, contrast=1.0)
        a.ball(foot[0] + 2, foot[1] + 1, 10, 6, R(PALE if near else HIDE, gb))
        a.poly([(foot[0] - 5, max(foot[1] - 4, 0)), (foot[0] + 11, max(foot[1] - 4, 0)), (foot[0] + 9, foot[1] + 5), (foot[0] - 3, foot[1] + 5)], R(IRON, gb)[1])
        a.line([(foot[0] + 3, max(foot[1] - 4, 0)), (foot[0] + 3, foot[1] + 4)], R(IRON, gb)[0], 1)
    hind(0, False)
    front(math.pi, False)
    # ---- the harrow: a rusted iron frame on a chain from the yoke, dragged behind: it swings up on the wind-up and whips over on the strike, and drops flat when the ox falls
    sw_ = (.55 * w - .9 * st) * live
    ax_, ay_ = -60., by - 4 - dn * 8                                       # where the chain meets the frame
    lift = max(0., sw_)
    def Hp(u, v):                                                         # a point of the harrow in its own frame (u along it, v across), swung about the chain
        x, y = rot2(u, v, -sw_ * 1.1)
        return ax_ - 6 + x, max(2., ay_ - 24 + y - 4 * dn)
    frame = [Hp(-26, 0), Hp(2, 0), Hp(6, 8), Hp(-22, 8)]
    # the chain from the yoke over the back
    chain = [Tb(34, 50), Tb(8, 40), Tb(-20, 32), Tb(-48, 24), (ax_, ay_ + 1)]
    for k in range(len(chain) - 1):
        a.line([chain[k], chain[k + 1]], R(IRON, gb)[3], 2)
        a.line([(chain[k][0], chain[k][1] - 1), (chain[k + 1][0], chain[k + 1][1] - 1)], R(IRON, gb)[1], 1)
    a.line([(ax_, ay_ + 1), Hp(-4, 4)], R(IRON, gb)[3], 2)
    shaded(a, frame, R(IRON, gb), light=(-.5, .85), base=.5, contrast=1.1, grain=.06)
    for k in range(6):                                                    # six rusty teeth along the frame
        bx_, by_ = Hp(-24 + k * 5.2, 8.5)
        tx_, ty_ = Hp(-24 + k * 5.2 + .8, 18 + (k % 2) * 3)
        a.poly([(bx_ - 1.6, by_), (tx_, ty_), (bx_ + 1.6, by_)], R(IRON, gb)[2])
        a.line([(bx_, by_), (tx_, ty_)], R(BRASS, gb)[1] if gb < .55 else GREYD[1], 1)
    for k in range(3):                                                    # cross bars
        a.line([Hp(-24 + k * 10, 0), Hp(-24 + k * 10, 8)], R(IRON, gb)[0], 1)
    # ---- the tail, then the body: a deep barrel with a high shoulder hump, a scarred pale belly, a dark saddle and rows of hide ticks
    tailp = [(-52, by + 10 - dn * 8), (-60, by + 2 - dn * 6), (-63, by - 14 + swing(.5, 3) - dn * 10)]
    a.line(tailp, R(HIDE, gb)[1], 3)
    a.ball(tailp[2][0], tailp[2][1] - 2, 4.5, 6, R(IRON, gb))
    top = [(-52, -4), (-50, 14), (-38, 26), (-14, 30), (8, 36), (28, 52), (46, 46), (56, 24), (54, -2), (42, -20), (10, -25), (-20, -23), (-44, -17)]
    shaded(a, smooth([Tb(x, y) for x, y in top], 5), R(HIDE, gb), light=(-.5, .85), base=.55, contrast=1.1, grain=.07)
    belly = [(-44, -15), (-20, -22), (10, -24), (42, -19), (50, -4), (36, -8), (8, -14), (-22, -12), (-42, -8)]
    shaded(a, smooth([Tb(x, y) for x, y in belly], 4), R(PALE, gb), light=(-.4, .85), base=.55, contrast=.9, edge=False, grain=.1)
    sad = [(-40, 22), (-14, 28), (10, 33), (26, 49), (38, 42), (14, 24), (-14, 20)]
    shaded(a, smooth([Tb(x, y) for x, y in sad], 4), R(HIDE, gb)[:4], light=(-.5, .85), base=.4, contrast=.9, edge=False)
    for i in range(11):                                                   # hide ticks
        x, y = -46 + i * 9.5, 6 + (i % 3) * 8
        p, q = Tb(x, y), Tb(x + 6, y + 4)
        a.line([p, q], R(HIDE, gb)[4] if y > 14 else R(PALE, gb)[4], 1)
        r_, s_ = Tb(x + 3, y - 8), Tb(x + 9, y - 5)
        a.line([r_, s_], R(HIDE, gb)[1], 1)
    for k in range(3):                                                    # old scars across the flank
        sx_, sy_ = -20 + k * 14, 10 + k * 3
        a.line([Tb(sx_, sy_), Tb(sx_ + 8, sy_ + 8)], R(PALE, gb)[3], 1)
    # the cracked leather yoke across the shoulders, brass studs along it
    yoke = [Tb(26, 52), Tb(40, 48), Tb(52, 24), Tb(44, 20), Tb(34, 38)]
    shaded(a, yoke, R(IRON, gb)[:4], light=(-.5, .85), base=.4, contrast=.8, edge=True)
    for k in range(4):
        sx_, sy_ = Tb(33 + k * 4.4, 45 - k * 6.5)
        a.ellipse(sx_, sy_, 1.4, 1.4, R(BRASS, gb)[3])
    # ---- near legs, over the body
    hind(math.pi, True)
    front(0, True)
    # ---- the head: a heavy drooping skull on a thick neck, a broad muzzle with a brass ring, a hinged jaw with crooked yellow teeth, two iron-capped horns, small red eyes under a scowling brow
    hx, hy = T(64 + st * 5, by + 2, 1.)
    face = -.28 + w * .5 - st * .45 - dn * .5 + (.14 if hurt else 0) - rear * .45
    op = (.62 if (clip == 'attack' and 2 <= n <= 5) else .9 if dn > .3 else .5 if hurt else .08 + w * .2)
    hy = max(hy, 18. - 34 * math.sin(face - op), 16.)                     # the lower jaw never goes under the ground
    nk = [T(30, by + 22, 1.), T(46, by + 14, 1.), (hx - 8, hy + 4)]
    tapered(a, smooth(nk, 6, closed=False), 34, 26, R(HIDE, gh), base=.58, contrast=1.05)

    def at(u, v):
        x, y = rot2(u, v, face)
        return hx + x, hy + y
    # the far horn first (it sits behind the skull), then the skull, then the near horn over it
    def horn(side, near):
        base_u, base_v = -4 + side * 3, 14
        pts = [at(base_u, base_v), at(base_u + 6, base_v + 14), at(base_u + 20, base_v + 20), at(base_u + 36, base_v + 12), at(base_u + 46, base_v - 2)]
        ramp = PALE if near else [PALE[0], PALE[0], PALE[1], PALE[2], PALE[3]]
        tapered(a, smooth(pts, 5, closed=False), 11 if near else 9, 3, R(ramp, gh), base=.6, contrast=1.1)
        cap = pts[-3:]
        tapered(a, smooth(cap, 4, closed=False), 6, 1.5, R(IRON, gh), base=.6, contrast=1.0)                   # the iron cap on the tip
        a.line([pts[1], pts[2]], R(PALE, gh)[4] if gh < .55 else GREYD[3], 1)
    horn(-1, False)
    ear = at(-14, 8)
    a.ball(ear[0], ear[1] - 6, 9, 5, R(HIDE, gh), -.6)                    # a drooping ear
    a.ellipse(ear[0] + .5, ear[1] - 6, 4.4, 2.2, R(HIDE, gh)[1] if gh < .55 else GREYD[1])
    upper = [at(-20, 10), at(-8, 18), at(10, 18), at(26, 10), at(40, 2), at(46, -6), at(42, -12), at(14, -9), at(-12, -8)]
    shaded(a, smooth(upper, 3), R(HIDE, gh), light=(-.5, .85), base=.6, contrast=1.05, grain=.06)
    muzzle = [at(16, 2), at(36, 4), at(46, -4), at(42, -12), at(14, -9)]
    shaded(a, muzzle, R(PALE, gh), light=(-.4, .8), base=.6, contrast=.8, edge=False)
    hinge = (-9., -6.)
    lower = [(-9, -6), (16, -5.5), (40, -5), (37, -13), (14, -17), (-7, -15)]
    low = []
    for u, v in lower:
        du, dv = u - hinge[0], v - hinge[1]
        ru, rv = rot2(du, dv, -op)
        low.append(at(hinge[0] + ru, hinge[1] + rv))
    shaded(a, low, R(PALE, gh), light=(-.4, .8), base=.55, contrast=.9)
    if op > .3:                                                           # the open mouth: a dark gap, a tongue, crooked yellow teeth on both jaws
        a.poly([at(-4, -6), at(38, -4), low[2], low[1], at(-9, -6)], R(IRON, gh)[0], outline=None)
        a.poly([at(6, -7), at(28, -6), low[2], low[1]], R(HIDE, gh)[1] if gh < .55 else GREYD[1], outline=None)
    for k in range(4):
        u = 18 + k * 6
        fx, fy = at(u, -4.5)
        fang(a, fx, fy, 5.6 - k * .6, 3.2, face - math.pi / 2 - .1 + (k % 2) * .25, BONE)
        ux, uy = rot2(u - hinge[0], -5 - hinge[1], -op)
        lx, ly = at(hinge[0] + ux, hinge[1] + uy)
        fang(a, lx, ly, 5. - k * .5, 2.8, face + math.pi / 2 + .15 - op - (k % 2) * .2, BONE)
    # the nostril, the brass nose ring and a split in the muzzle
    nx_, ny_ = at(43, -3)
    a.ellipse(nx_, ny_, 2.6, 2.0, OUTLINE)
    ring = [at(40, -8), at(44, -14), at(40, -20), at(35, -17)]
    a.line(ring, R(BRASS, gh)[3], 2)
    a.line([at(36, -9), at(34, 0)], R(HIDE, gh)[0], 1)
    ex, ey = at(10, 8)
    a.ellipse(ex, ey, 5.8, 4.6, OUTLINE)
    if dn > .25:
        a.line([(ex - 3, ey - 2), (ex + 3, ey + 2)], OUTLINE, 2)
        a.line([(ex - 3, ey + 2), (ex + 3, ey - 2)], OUTLINE, 2)
    else:
        if w > .3 or st > .3:
            glow(a, ex, ey, 9 + w * 3 + st * 3, EYE, .6)
        a.ellipse(ex, ey, 4.2, 3.2, EYE[2])
        a.ellipse(ex + .6, ey + .4, 2.8, 2.0, EYE[3])
        a.ellipse(ex - .6, ey + .6, 1.4, 1.0, EYE[4])
        a.line([(ex + .4, ey - 3.0), (ex + .4, ey + 3.0)], EYE[0], 1)
    a.poly([at(-8, 14), at(18, 14), at(20, 7), at(10, 11), at(-6, 11)], OUTLINE)             # a heavy scowling brow
    a.line([at(-7, 13), at(17, 12)], R(HIDE, gh)[0], 1)
    horn(1, True)
    # ---- effects attached to the body: dust kicked up on the wind-up and the strike, a puff when it falls
    if clip == 'attack' and n in (4, 5):
        for k in range(3):
            dust(a, hx + 6 + k * 6, 4 + (k % 2) * 3, 3.0 - k * .5, PEARL)
    if clip == 'attack' and n in (1, 2):
        for k in range(3):
            dust(a, -56 + k * 9, 3 + k, 2.4, PEARL)
    if dn > .5:
        for k in range(3):
            dust(a, -40 + k * 38 - dn * 6, 3 + (k % 2) * 2 + dn * 2, 3. + dn, PEARL)
    return a



DRAW = dict(harrowox=harrowox)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/sunward_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='sunward-elite')
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
        atlas.save(ASSETS / f'sunwardelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'sunwardelites_{kind}.png').convert('RGBA')
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
