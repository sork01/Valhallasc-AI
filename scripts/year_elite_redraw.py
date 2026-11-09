#!/usr/bin/env python3
"""The Yearwheel's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  equinoxstag  The Equinox Stag (level 98, no quest): a stag as tall as a hut that carries the turning year in its antlers. A tawny coat gone grey at the muzzle and scarred across the flank, a heavy
            ruff of cream fur at the throat, long cloven legs, a short white tuft of tail and a great rack of pale antlers whose beams hold the four seasons in turn: pink blossom at the roots, green leaf,
            amber leaf, then blue frost at the tips. Small gold eyes under a heavy brow, a broken grin of yellow teeth. Winds up by throwing the head back and the antlers high with a front hoof raised; the
            strike drops the whole front half and sweeps the rack forward and down; it recovers shaking petals, leaves and frost loose. Dies when its forelegs fold, the head drops and the antlers sag
            onto the ground, the blossoms wither and the colour drains to grey from the rump forward and the eyes go out.
The manifest is client/assets/yearwheelelites.txt (the sixteen old Yearwheel enemies and the NPCs keep yearwheel.txt). The shading helpers are copied from sunward_elite_redraw.py.
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
from moonspore_slime_redraw import fang, plate

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/year-elites'
REGISTRY = ROOT / 'scripts/year_elite_sources.txt'
MANIFEST = ASSETS / 'yearwheelelites.txt'
PREFIX = 'valhallasc_year_elite_'
KINDS = ['equinoxstag']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(equinoxstag=(184, 164, 84, 152))
SCALE = dict(equinoxstag=.56)
FLYING = ()
_mine = [
    '#24140a', '#5a3820', '#9a6632', '#d49a52', '#f2cf8a',   # HIDE (the tawny coat)
    '#3a3028', '#76654f', '#b0a084', '#dccfb0', '#f8f0da',   # PALE (the ruff, belly and legs)
    '#2c2820', '#6a604c', '#a89c80', '#d8ccaa', '#f4ecd0',   # ANTLER (pale bone)
    '#6a1238', '#b4306a', '#e868a0', '#ffa8cc', '#ffe0ec',   # SPRING (blossom)
    '#143a1a', '#2a7430', '#58b448', '#9ce070', '#e2ffb0',   # SUMMER (leaf)
    '#5a1c08', '#a8420e', '#e0801c', '#f8c050', '#fff0a0',   # AUTUMN (amber leaf)
    '#102c4c', '#2c6aa0', '#68b0d8', '#b0e0f4', '#f0fcff',   # WINTER (frost)
    '#3a2406', '#8a5a0a', '#d49a14', '#f6d046', '#fff6a8',   # EYE (the gold glow)
    '#18181a', '#383a3c', '#5c5e60', '#8a8c8e', '#b8babc',   # GREYD (a dead coat)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
HIDE, PALE, ANTLER, SPRING, SUMMER, AUTUMN, WINTER, EYE, GREYD = [_i[5 * k:5 * k + 5] for k in range(9)]
SEASONS = [SPRING, SUMMER, AUTUMN, WINTER]


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

# ---- the Equinox Stag --------------------------------------------------------------------------------------------------------------
def rot2(u, v, ang):
    c, s = math.cos(ang), math.sin(ang)
    return u * c - v * s, u * s + v * c


def equinoxstag(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05                                                       # the last beat is not the first: the head is still coming up
    a = Painter('equinoxstag', st * 3 - w * 3 + recoil - 32)
    live = 1 - dn
    gb, gh = clamp01(dn * 2.2 - .1), clamp01(dn * 1.8 - .45)           # the colour drains from the rump forward when it dies
    R = lambda ramp, g: GREYD if g > .55 else ramp
    by = max(30., 60 + bob * .5 - dn * 32 - (2 if hurt else 0))        # the belly rides high on long legs and sinks when it dies
    rear = .20 * w - .24 * st - .30 * dn + (.04 if hurt else 0)
    hip = (-34., by)

    def T(x, y, k=1.):
        dx, dy = x - hip[0], y - hip[1]
        c, s = math.cos(rear * k), math.sin(rear * k)
        return hip[0] + dx * c - dy * s, hip[1] + dx * s + dy * c

    def Tb(x, y):
        return T(x, by + y, clamp01((x + 36) / 70))
    swing = lambda off, amp: math.sin(ph + off) * amp * live
    splay = dn * 1.0

    def hind(off, near):
        sw = swing(off, 8. if walk else 1.)
        lift = max(0., math.cos(ph + off)) * (5 if walk else 0) * live
        top = (-38 + (3 if near else -2), by - 2)
        knee = (-26 + sw * .35 - 8 * splay * (1 if near else -.6), by - 24 + 6 * dn)
        hock = (-40 + sw * .7 - 4 * splay, 24 + 4 * dn + lift * .5)
        foot = (-34 + sw + (14 if near else 6) * splay, 3.5 + lift)
        ramp = HIDE if near else [HIDE[0], HIDE[0], HIDE[1], HIDE[1], HIDE[2]]
        tapered(a, smooth([top, knee, hock, foot], 5, closed=False), 17 if near else 15, 6.5 if near else 6, R(ramp, gb), base=.55, contrast=1.0)
        a.poly([(foot[0] - 3, 0), (foot[0] + 6, 0), (foot[0] + 5, foot[1] + 3), (foot[0] - 2, foot[1] + 3)], R(ANTLER, gb)[1])      # a dark cloven hoof
        a.line([(foot[0] + 1.5, 0), (foot[0] + 1.5, foot[1] + 2)], R(ANTLER, gb)[0], 1)

    def front(off, near):
        sw = swing(off, 8. if walk else 1.)
        lift = (max(0., math.cos(ph + off)) * (5 if walk else 0) + 14 * w * (1 if near else .3)) * live
        top = T(36 + (2 if near else -4), by - 2, 1.)
        knee = T(40 + sw * .3 + 10 * splay * (1 if near else -.5), by - 26 + 10 * dn, 1.)
        foot = T(38 + sw + (16 if near else 8) * splay, 4 + lift + 3 * dn, 1.)
        foot = (foot[0], max(foot[1], 3.5))
        ramp = PALE if near else [PALE[0], PALE[0], PALE[1], PALE[1], PALE[2]]
        tapered(a, smooth([top, knee, foot], 6, closed=False), 16 if near else 14, 6 if near else 5.5, R(ramp, gb), base=.55, contrast=1.0)
        a.poly([(foot[0] - 3, max(foot[1] - 3, 0)), (foot[0] + 7, max(foot[1] - 3, 0)), (foot[0] + 6, foot[1] + 3), (foot[0] - 2, foot[1] + 3)], R(ANTLER, gb)[1])
        a.line([(foot[0] + 2, max(foot[1] - 3, 0)), (foot[0] + 2, foot[1] + 2)], R(ANTLER, gb)[0], 1)
    hind(0, False)
    front(math.pi, False)
    # ---- the tail: a short white tuft that flicks
    tl = (-54, by + 14 - dn * 8)
    a.ball(tl[0] - 2, tl[1] + swing(.5, 2), 5, 7, R(PALE, gb), -.5)
    # ---- the body: a deep chest, a straight back, a cream belly, a heavy scar across the flank and rows of coat ticks
    top = [(-50, 0), (-48, 20), (-32, 30), (-4, 32), (24, 30), (42, 22), (52, 8), (48, -8), (30, -16), (0, -18), (-26, -16), (-46, -10)]
    shaded(a, smooth([Tb(x, y) for x, y in top], 5), R(HIDE, gb), light=(-.5, .85), base=.55, contrast=1.1, grain=.07)
    belly = [(-44, -15), (-20, -19), (10, -20), (40, -15), (48, -6), (34, -10), (8, -13), (-22, -12), (-42, -8)]
    shaded(a, smooth([Tb(x, y) for x, y in belly], 4), R(PALE, gb), light=(-.4, .85), base=.55, contrast=.9, edge=False, grain=.1)
    for i in range(12):
        x, y = -46 + i * 8.6, 4 + (i % 3) * 7
        p, q = Tb(x, y), Tb(x + 5, y + 4)
        a.line([p, q], R(HIDE, gb)[4] if y > 10 else R(PALE, gb)[4], 1)
    for k in range(3):                                                    # old scars across the flank
        sx_, sy_ = -22 + k * 13, 8 + k * 3
        a.line([Tb(sx_, sy_), Tb(sx_ + 7, sy_ + 9)], R(PALE, gb)[3], 1)
    # ---- near legs, over the body
    hind(math.pi, True)
    front(0, True)
    # ---- the neck, a heavy cream ruff at the throat, then the head
    hx, hy = T(70 + st * 6, by + 62, 1.)
    face = -.50 + w * .55 - st * .7 - dn * .75 + (.16 if hurt else 0) - rear * .5
    op = (.60 if (clip == 'attack' and 2 <= n <= 5) else .85 if dn > .3 else .5 if hurt else .06 + w * .2)
    hy = max(hy, 28. - 38 * math.sin(face - op), 22.)                     # the lower jaw never goes under the ground
    nk = [T(30, by + 14, 1.), T(48, by + 38, 1.), (hx - 10, hy - 2)]
    tapered(a, smooth(nk, 6, closed=False), 32, 17, R(HIDE, gh), base=.58, contrast=1.05)
    ruff = [T(34, by + 8, 1.), T(54, by + 28, 1.), (hx - 4, hy - 8), (hx - 16, hy - 12), T(44, by + 14, 1.), T(26, by + 2, 1.)]
    shaded(a, smooth(ruff, 3), R(PALE, gh), light=(-.4, .85), base=.55, contrast=.8, edge=False, grain=.12)
    for k in range(5):                                                    # shaggy tufts down the ruff
        p = T(36 + k * 4.5, by + 6 + k * 5.5, 1.)
        a.line([p, (p[0] + 2.5, p[1] - 7)], R(PALE, gh)[4] if gh < .55 else GREYD[3], 1)

    def at(u, v):
        x, y = rot2(u, v, face)
        return hx + x, hy + y

    def antler(side, near):
        """One beam sweeping up and back from between the ears, then forward, with tines forward and up along it: the seasons in turn (blossom, leaf, amber leaf, frost)."""
        sag = dn * .9
        s = -1 if side < 0 else 1
        spine = [(-4, 14), (-12, 36), (-6, 60), (12, 80), (36, 90), (58, 86)] if near else [(-12, 14), (-26, 34), (-26, 58), (-12, 80), (10, 94), (34, 98)]
        spine = [(u * (.8 - st * .12) if u > 0 else u, v) for u, v in spine]
        base = spine[0]
        spine = [at(base[0] + rot2(u - base[0], v - base[1], -sag * (k / 5.) * 1.0)[0], base[1] + rot2(u - base[0], v - base[1], -sag * (k / 5.) * 1.0)[1]) for k, (u, v) in enumerate(spine)]
        ramp = ANTLER if near else [ANTLER[0], ANTLER[0], ANTLER[1], ANTLER[2], ANTLER[3]]
        tapered(a, smooth(spine, 5, closed=False), 14 if near else 12, 3.5, R(ramp, gh), base=.6, contrast=1.1)
        marks = (.18, .36, .54, .72, .9)
        for k, t in enumerate(marks):                                     # tines off the beam
            i = min(int(t * (len(spine) - 1)), len(spine) - 2)
            f = t * (len(spine) - 1) - i
            p = (spine[i][0] + (spine[i + 1][0] - spine[i][0]) * f, spine[i][1] + (spine[i + 1][1] - spine[i][1]) * f)
            ln = 26 + (k % 3) * 6 - k * 1.5
            tip = (p[0] + math.cos(face + 1.05 - sag * .6) * ln * .55 + 2, p[1] + math.sin(face + 1.05 - sag * .6) * ln + 3 * (k % 2))
            tapered(a, [p, ((p[0] + tip[0]) / 2 + 1.5, (p[1] + tip[1]) / 2 + 1), tip], 8 if near else 7, 2, R(ramp, gh), base=.6, contrast=1.0)
            season = SEASONS[min(3, k * 4 // 5)]
            col = GREYD if gh > .55 else season
            if k <= 1:                                                    # blossom: a small cluster of petals
                for q in range(3):
                    ang = q * 2.1 + k
                    a.ball(tip[0] + math.cos(ang) * 3.2, tip[1] + math.sin(ang) * 3.2, 3.0, 2.6, col)
                a.ellipse(tip[0], tip[1], 1.4, 1.4, GREYD[1] if gh > .55 else AUTUMN[3])
            elif k == 2:                                                  # summer leaf: a long green leaf
                a.ball(tip[0] + 2, tip[1] + 1, 6.5, 3.0, col, .6)
                a.line([tip, (tip[0] + 6, tip[1] + 3)], col[0], 1)
            elif k == 3:                                                  # amber leaf
                a.ball(tip[0] + 1, tip[1] + 1, 5.5, 3.2, col, -.5)
                a.line([tip, (tip[0] + 5, tip[1] - 2)], col[0], 1)
            else:                                                         # frost: a crystal of three spokes
                for q in range(3):
                    ang = q * 1.05 - .2 + (math.pi / 2 if k % 2 else 0)
                    a.line([tip, (tip[0] + math.cos(ang) * 6, tip[1] + math.sin(ang) * 6)], col[3], 1)
                a.ellipse(tip[0], tip[1], 1.8, 1.8, col[4] if gh < .55 else GREYD[4])
        a.ball(spine[-1][0], spine[-1][1], 3.2, 2.4, R(WINTER, gh) if gh < .55 else GREYD)   # frost on the beam's end
    antler(-1, False)
    ear = at(-12, 10)
    a.ball(ear[0] - 4, ear[1] + 2, 11, 4.4, R(HIDE, gh), -.9)             # a long leaf-shaped ear laid back
    a.ellipse(ear[0] - 3.5, ear[1] + 2, 5.5, 1.8, R(HIDE, gh)[1] if gh < .55 else GREYD[1])
    upper = [at(-16, 8), at(-2, 14), at(16, 12), at(34, 5), at(48, -2), at(54, -8), at(48, -13), at(16, -10), at(-10, -8)]
    shaded(a, smooth(upper, 3), R(HIDE, gh), light=(-.5, .85), base=.6, contrast=1.05, grain=.06)
    muzzle = [at(22, 2), at(40, 3), at(52, -4), at(48, -13), at(16, -10)]
    shaded(a, muzzle, R(PALE, gh), light=(-.4, .8), base=.6, contrast=.8, edge=False)
    hinge = (-6., -6.)
    lower = [(-6, -6), (20, -6), (46, -5.5), (43, -14), (16, -17), (-4, -15)]
    low = []
    for u, v in lower:
        du, dv = u - hinge[0], v - hinge[1]
        ru, rv = rot2(du, dv, -op)
        low.append(at(hinge[0] + ru, hinge[1] + rv))
    shaded(a, low, R(PALE, gh), light=(-.4, .8), base=.55, contrast=.9)
    if op > .3:                                                           # the open mouth: a dark gap and a broken grin of yellow teeth
        a.poly([at(14, -6), at(44, -5), low[2], low[1]], R(ANTLER, gh)[0], outline=None)
    for k in range(4):
        u = 22 + k * 6.5
        fx, fy = at(u, -5)
        fang(a, fx, fy, 5.0 - k * .5, 2.8, face - math.pi / 2 - .1 + (k % 2) * .25, BONE)
        ux, uy = rot2(u - hinge[0], -5 - hinge[1], -op)
        lx, ly = at(hinge[0] + ux, hinge[1] + uy)
        fang(a, lx, ly, 4.4 - k * .4, 2.5, face + math.pi / 2 + .15 - op - (k % 2) * .2, BONE)
    nx_, ny_ = at(51, -5)
    a.ellipse(nx_, ny_, 2.8, 2.0, OUTLINE)                                # the nostril
    ex, ey = at(10, 6)
    a.ellipse(ex, ey, 5.2, 4.2, OUTLINE)
    if dn > .25:
        a.line([(ex - 3, ey - 2), (ex + 3, ey + 2)], OUTLINE, 2)
        a.line([(ex - 3, ey + 2), (ex + 3, ey - 2)], OUTLINE, 2)
    else:
        if w > .3 or st > .3:
            glow(a, ex, ey, 9 + w * 3 + st * 3, EYE, .6)
        a.ellipse(ex, ey, 3.8, 3.0, EYE[2])
        a.ellipse(ex + .5, ey + .3, 2.5, 1.8, EYE[3])
        a.ellipse(ex - .5, ey + .5, 1.3, .9, EYE[4])
        a.line([(ex + .4, ey - 2.8), (ex + .4, ey + 2.8)], EYE[0], 1)
    a.poly([at(-6, 12), at(18, 13), at(22, 6), at(10, 10), at(-4, 9)], OUTLINE)             # a heavy scowling brow
    a.line([at(-5, 12), at(18, 11)], R(HIDE, gh)[0], 1)
    antler(1, True)
    # ---- effects attached to the body: petals and leaves shaken loose on the strike, dust on the wind-up, a puff when it falls
    if clip == 'attack' and n in (4, 5):
        for k in range(4):
            col = SEASONS[k]
            a.ball(hx + 20 + k * 9, 30 + (k % 2) * 8, 3, 2.2, col)
    if clip == 'attack' and n in (1, 2):
        for k in range(3):
            dust(a, -56 + k * 9, 3 + k, 2.4, PEARL)
    if dn > .5:
        for k in range(3):
            dust(a, -40 + k * 38 - dn * 6, 3 + (k % 2) * 2 + dn * 2, 3. + dn, PEARL)
    return a


DRAW = dict(equinoxstag=equinoxstag)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/year_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='year-elite')
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
        atlas.save(ASSETS / f'yearwheelelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'yearwheelelites_{kind}.png').convert('RGBA')
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
