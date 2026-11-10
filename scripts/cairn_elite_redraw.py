#!/usr/bin/env python3
"""Cairnspine's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  avalanchebear  The Avalanche Bear (level 92, no quest): a mountain-sized bear with slate-grey fur gone white along the belly and legs, a ridge of jagged blue-white ice
              spines down its back, small ice-blue eyes under a scowling brow, round torn ears, a heavy blunt snout and bone fangs. Winds up by rearing onto its hind legs with the
              forepaws raised and the ice spines flared; the strike drops the whole front half forward and down with the jaws wide; it recovers settling back onto all fours. Dies when
              its legs splay and the body sinks onto the snow, the head drops, the ice spines shatter shorter, the colour drains to grey from the rump forward and the eyes go out.
The manifest is client/assets/cairnelites.txt (the seven old Cairnspine enemies and the six NPCs keep cairn.txt). The shading helpers are copied from lapis_elite_redraw.py.
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
OUT = ROOT / 'test-results/cairn-elites'
REGISTRY = ROOT / 'scripts/cairn_elite_sources.txt'
MANIFEST = ASSETS / 'cairnelites.txt'
PREFIX = 'valhallasc_cairn_elite_'
KINDS = ['avalanchebear']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(avalanchebear=(156, 120, 60, 112))
SCALE = dict(avalanchebear=.82)
FLYING = ()
_mine = [
    '#0a0f18', '#222c3c', '#46566e', '#7488a4', '#a8b8cc',   # FUR (the slate coat)
    '#2c3446', '#5a6a84', '#92a2ba', '#c8d4e4', '#f0f5fb',   # SNOWFUR (the white belly and legs)
    '#06223e', '#1a5a9c', '#48a4e4', '#a4dcff', '#f0fcff',   # ICE (the back spines, the eyes)
    '#1e1008', '#46281a', '#7a4a30', '#a87a58', '#d8b894',   # PAW (the dark pads and the nose)
    '#18181a', '#383a3c', '#5c5e60', '#8a8c8e', '#b8babc',   # GREYD (a dead fur)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
FUR, SNOW, ICE, PAW, GREYD = [_i[5 * k:5 * k + 5] for k in range(5)]


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

# ---- the Avalanche Bear --------------------------------------------------------------------------------------------------------
def rot2(u, v, ang):
    c, s = math.cos(ang), math.sin(ang)
    return u * c - v * s, u * s + v * c


def avalanchebear(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05                                                       # the last beat is not the first: the front half is still settling back
    a = Painter('avalanchebear', st * 3 - w * 4 + recoil)
    live = 1 - dn
    # ---- greying: the colour drains from the rump forward when it dies
    gb, gh = clamp01(dn * 2.2 - .1), clamp01(dn * 1.8 - .45)
    R = lambda ramp, g: GREYD if g > .55 else ramp
    # ---- the body rides high on all fours, sinks when it dies; the front half rears about the hips on the wind-up and drops on the strike
    by = max(22., 42 + bob * .5 - dn * 21 - (2 if hurt else 0))
    rear = .50 * w - .26 * st - .12 * dn + (.06 if hurt else 0)
    hip = (-32., by)

    def T(x, y, k=1.):
        """A point of the front half, rotated about the hips by the rearing angle (k = how much of it: 0 at the rump, 1 at the shoulders)."""
        dx, dy = x - hip[0], y - hip[1]
        c, s = math.cos(rear * k), math.sin(rear * k)
        return hip[0] + dx * c - dy * s, hip[1] + dx * s + dy * c

    def Tb(x, y):                                                     # a body point: the rotation fades in from the rump to the shoulders
        return T(x, by + y, clamp01((x + 36) / 70))
    swing = lambda off, amp: math.sin(ph + off) * amp * live
    splay = dn * 1.0

    def hind(off, near):
        sw = swing(off, 8. if walk else 1.)
        lift = max(0., math.cos(ph + off)) * (4 if walk else 0) * live
        top = (-34 + (3 if near else -2), by - 4)
        knee = (-27 + sw * .4 - 12 * splay * (1 if near else -.6), by - 22 + 5 * dn)
        foot = (-30 + sw + (14 if near else 6) * splay, 4.5 + lift)
        ramp = FUR if near else [FUR[0], FUR[0], FUR[1], FUR[1], FUR[2]]
        tapered(a, smooth([top, knee, foot], 6, closed=False), 21 if near else 18, 13 if near else 12, R(ramp, gb), base=.55, contrast=1.0)
        a.ball(foot[0] + 3, foot[1] + 1.5, 10, 5, R(SNOW if near else FUR, gb))             # a big pale foot
        for k in range(3):
            fang(a, foot[0] + 11 + k * 1.2, foot[1] + 4 - k * 2.2, 4.8, 2.6, -.4 - k * .2, BONE)

    def front(off, near):
        sw = swing(off, 8. if walk else 1.)
        lift = max(0., math.cos(ph + off)) * (4 if walk else 0) * live
        top = T(34 + (2 if near else -4), by - 2, 1.)
        elbow = T(35 + sw * .3 + 8 * splay * (1 if near else -.5), by - 22 + 6 * dn, 1.)
        foot = T(38 + sw + (16 if near else 8) * splay, 6 + lift + 2 * dn, 1.)
        foot = (foot[0], max(foot[1], 4.5))
        ramp = SNOW if near else [SNOW[0], SNOW[0], SNOW[1], SNOW[1], SNOW[2]]
        tapered(a, smooth([top, elbow, foot], 6, closed=False), 22 if near else 19, 14 if near else 12, R(ramp, gb), base=.55, contrast=1.0)
        a.ball(foot[0] + 3, foot[1] + 1, 11, 6, R(SNOW if near else FUR, gb))
        for k in range(4):                                             # four bone claws
            fang(a, foot[0] + 12 + k * .5, foot[1] + 5 - k * 2.4, 7.5, 3.0, -.1 - k * .22 - st * .3, BONE)
    hind(0, False)
    front(math.pi, False)
    # ---- the stub of a tail, then the body: a deep barrel with a hunched shoulder hump, a pale belly, dark saddle fur and rows of fur ticks
    a.ball(-56, by + 6 - dn * 6, 8, 7, R(FUR, gb))
    top = [(-52, -4), (-50, 14), (-38, 28), (-14, 31), (10, 34), (30, 44), (46, 38), (55, 20), (53, -2), (42, -20), (10, -25), (-20, -23), (-44, -17)]
    shaded(a, smooth([Tb(x, y) for x, y in top], 5), R(FUR, gb), light=(-.5, .85), base=.55, contrast=1.1, grain=.06)
    belly = [(-44, -15), (-20, -22), (10, -24), (42, -19), (50, -4), (36, -8), (8, -14), (-22, -12), (-42, -8)]
    shaded(a, smooth([Tb(x, y) for x, y in belly], 4), R(SNOW, gb), light=(-.4, .85), base=.55, contrast=.9, edge=False, grain=.08)
    sad = [(-40, 22), (-14, 29), (12, 32), (30, 41), (40, 34), (14, 24), (-14, 21)]
    shaded(a, smooth([Tb(x, y) for x, y in sad], 4), R(FUR, gb)[:4], light=(-.5, .85), base=.4, contrast=.9, edge=False)
    for i in range(10):                                                # fur ticks
        x, y = -46 + i * 10, 6 + (i % 3) * 8
        p, q = Tb(x, y), Tb(x + 6, y + 4)
        a.line([p, q], R(FUR, gb)[4] if y > 14 else R(SNOW, gb)[4], 1)
        r_, s_ = Tb(x + 3, y - 8), Tb(x + 9, y - 5)
        a.line([r_, s_], R(FUR, gb)[1], 1)
    # ---- the avalanche: a ridge of jagged blue-white ice spines down the back, flared on the wind-up, shattered shorter when it dies
    flare = 1 + w * .5 - dn * .62
    for k in range(8):
        bx = -40 + k * 11.5
        by_ = 26 + (10 if bx > 14 else 2) * (1 if bx > 8 else 0) + (3 if bx > 24 else 0)
        base = [Tb(bx - 4.5, by_ - 2), Tb(bx + 4.5, by_ - 2)]
        tl = (13 + 9 * math.sin(k * 1.7 + .5) + 3 * (k > 4)) * flare
        tip = Tb(bx - 3 + (2 if k % 2 else -2) - w * 2, by_ + tl)
        shaded(a, [base[0], tip, base[1]], R(ICE, gh), light=(-.5, .85), base=.6, contrast=1.1)
        a.line([(tip[0] + .8, tip[1] - 1.6), ((base[0][0] + base[1][0]) / 2 + .5, (base[0][1] + base[1][1]) / 2 + 1)], R(ICE, gh)[4] if gh < .55 else GREYD[3], 1)
    # ---- near legs, over the body
    hind(math.pi, True)
    front(0, True)
    # ---- the head: a wide skull, a blunt snout, a hinged jaw with bone fangs, torn round ears, a scowling brow and two small ice-blue eyes
    hx, hy = T(60 + st * 4, by + 7, 1.)
    face = -.14 + w * .30 - st * .62 - dn * .55 + (.18 if hurt else 0) - rear * .55
    op = (.64 if (clip == 'attack' and 2 <= n <= 5) else .95 if dn > .3 else .5 if hurt else .1 + w * .3)
    hy = max(hy, 16. - 38 * math.sin(face - op), 14.)                     # the lower jaw never goes under the ground
    nk = [T(30, by + 18, 1.), T(44, by + 12, 1.), (hx - 8, hy + 2)]
    tapered(a, smooth(nk, 6, closed=False), 30, 24, R(FUR, gh), base=.58, contrast=1.05)

    def at(u, v):
        x, y = rot2(u, v, face)
        return hx + x, hy + y
    for k, (u, v) in enumerate(((-10, 17), (2, 19))):                  # two round ears, one torn
        ex_, ey_ = at(u, v)
        a.ball(ex_, ey_, 7, 7, R(FUR, gh))
        a.ellipse(ex_ + .5, ey_ - .5, 3.6, 3.6, R(PAW, gh)[1] if gh < .55 else GREYD[1])
        if k == 1:
            a.poly([at(u - 1, v + 7), at(u + 4, v + 3), at(u + 2, v + 6.5)], 0)
    upper = [at(-18, 12), at(-6, 18), at(10, 17), at(24, 11), at(36, 5), at(40, -1), at(38, -6), at(14, -5), at(-12, -6)]
    shaded(a, smooth(upper, 3), R(FUR, gh), light=(-.5, .85), base=.6, contrast=1.05, grain=.05)
    muzzle = [at(14, 5), at(32, 6), at(40, 0), at(38, -6), at(14, -5)]
    shaded(a, muzzle, R(SNOW, gh), light=(-.4, .8), base=.6, contrast=.8, edge=False)
    hinge = (-9., -5.)
    lower = [(-9, -5), (16, -4.5), (38, -4), (35, -11), (14, -15), (-7, -13)]
    low = []
    for u, v in lower:
        du, dv = u - hinge[0], v - hinge[1]
        ru, rv = rot2(du, dv, -op)
        low.append(at(hinge[0] + ru, hinge[1] + rv))
    shaded(a, low, R(SNOW, gh), light=(-.4, .8), base=.55, contrast=.9)
    if op > .3:                                                         # the open mouth: a dark gap, a tongue, fangs on both jaws
        a.poly([at(-4, -5), at(36, -3), low[2], low[1], at(-9, -5)], R(PAW, gh)[0], outline=None)
        a.poly([at(6, -6), at(26, -5), low[2], low[1]], R(PAW, gh)[2] if gh < .55 else GREYD[1], outline=None)
    for k in range(4):
        u = 16 + k * 6
        fx, fy = at(u, -3.5)
        fang(a, fx, fy, 7.5 - k * .9, 3.0, face - math.pi / 2 - .1, BONE)
        ux, uy = rot2(u - hinge[0], -4 - hinge[1], -op)
        lx, ly = at(hinge[0] + ux, hinge[1] + uy)
        fang(a, lx, ly, 6 - k * .6, 2.6, face + math.pi / 2 + .15 - op, BONE)
    # the nose, a scar across the snout and a ridge of dark brow
    nx_, ny_ = at(38, 0)
    a.ball(nx_, ny_, 4.2, 3.4, R(PAW, gh))
    a.line([at(18, 9), at(26, 2), at(31, -3)], R(FUR, gh)[0], 1)
    ex, ey = at(8, 7)
    a.ellipse(ex, ey, 5.6, 4.6, OUTLINE)
    if dn > .25:
        a.line([(ex - 3, ey - 2), (ex + 3, ey + 2)], OUTLINE, 2)
        a.line([(ex - 3, ey + 2), (ex + 3, ey - 2)], OUTLINE, 2)
    else:
        if w > .3 or st > .3:
            glow(a, ex, ey, 9 + w * 3 + st * 3, ICE, .55)
        a.ellipse(ex, ey, 4.2, 3.4, ICE[3])
        a.ellipse(ex + .6, ey + .4, 2.8, 2.2, ICE[2])
        a.ellipse(ex - .6, ey + .6, 1.6, 1.2, ICE[4])
        a.line([(ex + .4, ey - 3.2), (ex + .4, ey + 3.2)], ICE[0], 1)
    a.poly([at(-6, 12), at(16, 12), at(18, 6), at(8, 9), at(-4, 9)], OUTLINE)             # a heavy scowling brow
    a.line([at(-5, 11), at(15, 10)], R(FUR, gh)[0], 1)
    # ---- effects attached to the body: snow kicked up on the wind-up and the strike, a puff when it falls
    if clip == 'attack' and n in (4, 5):
        for k in range(3):
            dust(a, hx + 4 + k * 6, 4 + (k % 2) * 3, 3.0 - k * .5, PEARL)
    if clip == 'attack' and n in (1, 2):
        for k in range(3):
            dust(a, -54 + k * 9, 3 + k, 2.4, PEARL)
    if dn > .5:
        for k in range(3):
            dust(a, -40 + k * 38 - dn * 6, 3 + (k % 2) * 2 + dn * 2, 3. + dn, PEARL)
    return a


DRAW = dict(avalanchebear=avalanchebear)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/cairn_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='cairn-elite')
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
        atlas.save(ASSETS / f'cairnelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'cairnelites_{kind}.png').convert('RGBA')
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
