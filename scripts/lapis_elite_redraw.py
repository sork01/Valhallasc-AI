#!/usr/bin/env python3
"""The Lapis Erg's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  cobaltbasilisk  The Cobalt Basilisk (level 83, no quest): a huge desert lizard with lapis-blue scales, a sand-gold belly, a fan of brass spines down its back and two swept brass
              horns on a wedge skull, one burning orange slit eye under a heavy brow and a jaw of bone fangs. Winds up by lowering its chest, rearing the head back and up with the jaws
              wide and the spines flared; the strike snaps the whole neck forward and down; it recovers with the head swinging back. Dies when its legs splay and the body sinks onto the sand,
              the head drops with the jaws open, the colour drains to grey from the tail forward and the eye goes out.
The manifest is client/assets/lapiselites.txt (the six old Lapis enemies and five NPCs keep lapis.txt). The shading helpers are copied from tangle_elite_redraw.py.
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
OUT = ROOT / 'test-results/lapis-elites'
REGISTRY = ROOT / 'scripts/lapis_elite_sources.txt'
MANIFEST = ASSETS / 'lapiselites.txt'
PREFIX = 'valhallasc_lapis_elite_'
KINDS = ['cobaltbasilisk']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(cobaltbasilisk=(192, 84, 94, 78))
SCALE = dict(cobaltbasilisk=.78)
FLYING = ()
_mine = [
    '#050c20', '#0e2660', '#1f55b4', '#4a8ae6', '#a8d0ff',   # COBALT (the scales)
    '#2a1a04', '#7a520e', '#c8901c', '#f0c850', '#fff0a8',   # BRASS (the spines, horns, claws)
    '#3a2a14', '#7a5c34', '#b89460', '#e0c890', '#f8ecc8',   # SAND (the belly)
    '#3a0c00', '#a02800', '#ff6a10', '#ffb840', '#fff0b0',   # EYEO (the burning eye)
    '#18181a', '#383a3c', '#5c5e60', '#8a8c8e', '#b8babc',   # GREYD (a dead scale)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
COBALT, BRASS, SAND, EYEO, GREYD = [_i[5 * k:5 * k + 5] for k in range(5)]


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


# ---- the Cobalt Basilisk -------------------------------------------------------------------------------------------------------
def rot2(u, v, ang):
    c, s = math.cos(ang), math.sin(ang)
    return u * c - v * s, u * s + v * c


def cobaltbasilisk(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    if clip == 'attack' and n == 7:
        w = .05                                                       # the last beat is not the first: the head is still settling back
    a = Painter('cobaltbasilisk', st * 4 - w * 5 + recoil)
    live = 1 - dn
    # ---- greying: the colour drains from the tail forward when it dies
    gt, gb, gh = clamp01(dn * 2.4 - .1), clamp01(dn * 1.9 - .3), clamp01(dn * 1.7 - .55)
    R = lambda ramp, g: GREYD if g > .55 else ramp
    # ---- the body rides low on the wind-up (the chest drops), high on the strike, and settles on the sand when it dies
    by = max(21., 34 + bob * .5 - w * 6 + st * 3 - dn * 21 - (3 if hurt else 0))
    # ---- the head: reared back and up on the wind-up, thrown forward and down on the strike, dropped on the sand when dead
    hx = 62 - w * 20 + st * 22 - dn * 6 - (7 if hurt else 0)
    hy = 46 + bob * .6 + w * 28 - st * 34 - dn * 32 + (3 if hurt else 0)
    face = -.12 + w * .55 - st * .85 - dn * .55 + (.2 if hurt else 0)
    op = (.62 if (clip == 'attack' and 2 <= n <= 5) else .95 if dn > .3 else .5 if hurt else .1 + w * .3)
    hy = max(hy, 13. - 36 * math.sin(face - op), 13.)                  # the lower jaw never goes under the ground
    swing = lambda off, amp: math.sin(ph + off) * amp * live
    # ---- far legs (dark) and the tail go behind the body
    def leg(hipx, off, far):
        sw = swing(off, 7.5 if walk else 1.0)
        lift = max(0., math.cos(ph + off)) * (4 if walk else 0) * live
        hip = (hipx, by - 7)
        knee = (hipx + 9 + sw * .5 + 5 * dn, by - 15 + 4 * dn)
        foot = (hipx + 4 + sw + 13 * dn, 4.5 + lift)
        if dn > .5:
            knee = (hipx + 13, by - 8)
        ramp = COBALT if not far else [COBALT[0], COBALT[0], COBALT[1], COBALT[1], COBALT[2]]
        a.limb([hip, knee, foot], R(ramp, gb), 9 if not far else 8)
        for k in range(3):                                           # three brass claws
            ang = -.12 - k * .3
            fang(a, foot[0] + 1.5, foot[1] + 2.0, 5.5, 3.0, ang, BRASS if gb < .55 else GREYD)
    leg(26, 0, True)
    leg(-26, math.pi, True)
    tl1 = math.sin(ph * .9) * 3.2 * live + w * 8 - st * 7
    tl2 = math.sin(ph * .9 - .8) * 5 * live + w * 24 - st * 21
    tip_y = max(4., by - 22 + tl2 - dn * (by - 22))
    spine = [(-30, by - 2), (-58, by - 6 + tl1), (-86, by - 15 + tl1 * .8 + tl2 * .3), (-112, tip_y)]
    sp = smooth(spine, 8, closed=False)
    sp = [(x, max(y, 4.)) for x, y in sp]
    tapered(a, sp, 21, 3, R(COBALT, gt), base=.6, contrast=1.05)
    # brass bands round the tail
    for k in range(3, len(sp) - 4, 6):
        (x0, y0), (x1, y1) = sp[k], sp[k + 1]
        a.line([(x0, y0 - 3), (x1, y1 + 3)], R(BRASS, gt)[2] if gt < .55 else GREYD[1], 1)
    # ---- the body: a deep barrel, a sand-gold belly strip, rows of pale scale ticks and brass studs
    top = [(-46, by - 1), (-38, by + 12), (-14, by + 20), (12, by + 21), (34, by + 14), (46, by + 2), (42, by - 12), (22, by - 20), (-8, by - 20), (-34, by - 14)]
    shaded(a, smooth(top, 5), R(COBALT, gb), light=(-.55, .8), base=.6, contrast=1.1, grain=.05)
    belly = [(-36, by - 13), (-10, by - 19), (20, by - 19), (40, by - 11), (36, by - 6), (10, by - 12), (-14, by - 12), (-32, by - 7)]
    shaded(a, smooth(belly, 4), R(SAND, gb), light=(-.4, .8), base=.55, contrast=.9, edge=False)
    for i in range(9):
        x = -38 + i * 9.4
        y = by + 9 - (4 if i % 2 else 0)
        a.line([(x, y), (x + 3.5, y - 3.5)], R(COBALT, gb)[3], 1)
        a.line([(x + 1, y - 7), (x + 4.5, y - 10)], R(COBALT, gb)[1], 1)
    for i in range(5):
        a.ellipse(-30 + i * 15, by + 2 - (i % 2) * 3, 2.2, 2.0, R(BRASS, gb)[2])
        a.ellipse(-30.6 + i * 15, by + 2.6 - (i % 2) * 3, 1.0, .9, R(BRASS, gb)[4])
    # ---- the dorsal sail: a fan of brass spines on a cobalt membrane, flared on the wind-up, folded when it dies
    flare = 1 + w * .55 - dn * .85
    base = [(-34 + k * 10.5, by + 15.5 + (4 if k in (0, 7) else 0) - (k - 3.5) ** 2 * .06) for k in range(8)]
    tips = [(b[0] - 3 + k * .35, b[1] + (17 + 7 * math.sin(k * 1.3 + .4)) * flare) for k, b in enumerate(base)]
    tips = [(x, min(y, by + 40 + w * 10)) for x, y in tips]
    sail = base + tips[::-1]
    a.poly(sail, R(COBALT, gb)[2], outline=R(COBALT, gb)[0])
    a.poly([(b[0], b[1] + 2) for b in base] + [(t[0], (b[1] + t[1]) / 2 + 2) for b, t in zip(base[::-1], tips[::-1])], R(COBALT, gb)[3])
    for b, t in zip(base, tips):
        a.line([b, t], R(BRASS, gb)[2], 2)
        a.line([(b[0] + .6, b[1] + 1), (t[0] + .3, t[1] - 1)], R(BRASS, gb)[4] if gb < .55 else GREYD[3], 1)
    # ---- near legs, over the body
    leg(24, math.pi, False)
    leg(-28, 0, False)
    # ---- the neck: from the shoulder up to the skull, thick and scaled
    nk = bez((32, by + 5), (44 + (hx - 66) * .3, by + 16 + (hy - 46) * .2), (hx - 11, hy - 6), 9)
    tapered(a, nk, 21, 14, R(COBALT, gh), base=.6, contrast=1.05)
    for k in range(1, len(nk) - 2, 2):                              # a pale throat under it
        a.line([(nk[k][0] + 1, nk[k][1] - 6), (nk[k + 1][0] + 1, nk[k + 1][1] - 6)], R(SAND, gh)[2], 3)
    # ---- the head: a wedge skull with a heavy brow, a hinged jaw, bone fangs, two swept horns and one burning slit eye
    def at(u, v):
        x, y = rot2(u, v, face)
        return hx + x, hy + y
    upper = [at(-14, 11), at(0, 15), at(18, 11), at(36, 5), at(40, 0), at(16, -3), at(-10, -5)]
    shaded(a, smooth(upper, 3), R(COBALT, gh), light=(-.5, .85), base=.62, contrast=1.1)
    hinge = (-8., -4.)
    lower = [(-8, -4), (16, -3.5), (36, -2), (33, -8), (14, -11), (-6, -12)]
    low = []
    for u, v in lower:
        du, dv = u - hinge[0], v - hinge[1]
        ru, rv = rot2(du, dv, -op)
        low.append(at(hinge[0] + ru, hinge[1] + rv))
    shaded(a, low, R(SAND, gh), light=(-.4, .8), base=.55, contrast=.9)
    # the open mouth: a dark gap and a row of fangs on both jaws
    if op > .3:
        a.poly([at(-4, -4), at(34, -1), low[2], low[1], at(-8, -4)], R(EYEO, gh)[0], outline=None)
    for k in range(5):
        u = 12 + k * 6
        fx, fy = at(u, -2.5)
        fang(a, fx, fy, 6 - k * .5, 2.6, face - math.pi / 2 - .1, BONE)
        ux, uy = rot2(u - hinge[0], -3 - hinge[1], -op)
        lx, ly = at(hinge[0] + ux, hinge[1] + uy)
        fang(a, lx, ly, 5.2 - k * .4, 2.4, face + math.pi / 2 + .15 - op, BONE)
    # horns: two swept-back brass spikes above the skull
    for k, (hu, hv, ang_off, ln) in enumerate(((-9, 11, 2.35, 22), (-2, 14, 2.05, 15))):
        px, py = at(hu, hv)
        fang(a, px, py, ln, 6.5 - k * 1.5, face + ang_off, BRASS if gh < .55 else GREYD)
    # a nostril and a scale ridge along the snout
    nx_, ny_ = at(35, 2.5)
    a.ellipse(nx_, ny_, 1.4, 1.1, OUTLINE)
    a.line([at(4, 12), at(20, 9), at(33, 4)], R(COBALT, gh)[4], 1)
    # the eye: one big orange slit under a heavy brow that slants down to the snout
    ex, ey = at(6, 5.5)
    a.ellipse(ex, ey, 5.2, 4.4, OUTLINE)
    if dn > .25:
        a.line([(ex - 3, ey - 2), (ex + 3, ey + 2)], OUTLINE, 2)
        a.line([(ex - 3, ey + 2), (ex + 3, ey - 2)], OUTLINE, 2)
    else:
        if w > .3 or st > .3:
            glow(a, ex, ey, 9 + w * 3 + st * 3, EYEO, .55)
        a.ellipse(ex, ey, 4.1, 3.4, EYEO[3])
        a.ellipse(ex + .6, ey + .6, 2.6, 2.0, EYEO[2])
        a.ellipse(ex - .7, ey + .8, 1.6, 1.1, EYEO[4])
        a.line([(ex, ey - 3.4), (ex, ey + 3.4)], EYEO[0], 1)
    a.poly([at(-4, 11), at(14, 10), at(16, 5.4), at(8, 7.8), at(-3, 8)], OUTLINE)
    a.line([at(-4, 10), at(14, 8)], R(COBALT, gh)[0], 1)
    # ---- effects attached to the body: sand kicked up on the wind-up and strike, a puff when it falls
    if clip == 'attack' and n in (4, 5):
        for k in range(3):
            dust(a, hx + 2 + k * 6, 4 + (k % 2) * 3, 3.0 - k * .5, PEARL)
    if clip == 'attack' and n in (1, 2):
        for k in range(3):
            dust(a, -52 + k * 9, 3 + k, 2.4, PEARL)
    if dn > .5:
        for k in range(3):
            dust(a, -36 + k * 34 - dn * 6, 3 + (k % 2) * 2 + dn * 2, 3. + dn, PEARL)
    return a


DRAW = dict(cobaltbasilisk=cobaltbasilisk)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/lapis_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='lapis-elite')
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
        atlas.save(ASSETS / f'lapiselites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'lapiselites_{kind}.png').convert('RGBA')
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
