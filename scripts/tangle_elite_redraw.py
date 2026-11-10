#!/usr/bin/env python3
"""The Tanglecrown's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  rootcentipede  The Hollowroot Centipede (level 77, no quest): a giant jungle centipede, thirteen banded plates (olive carapace, rust bands, pale belly) carried in an S that rises
              from the ground to a flared head with four glowing yellow eyes under a scowling brow, long whipping antennae and two venom-tipped forcipules like sickles. Winds up
              by rearing the front of the body high and back; the strike drops the whole length forward, head and fangs down at the ground. Dies when it goes limp: the head drops,
              the plates fade to grey from the tail forward, the legs curl up and the eyes go out.
The manifest is client/assets/tangleelites.txt. The shading helpers are copied from prism_elite_redraw.py.
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
OUT = ROOT / 'test-results/tangle-elites'
REGISTRY = ROOT / 'scripts/tangle_elite_sources.txt'
MANIFEST = ASSETS / 'tangleelites.txt'
PREFIX = 'valhallasc_tangle_elite_'
KINDS = ['rootcentipede']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(rootcentipede=(190, 119, 88, 113))
SCALE = dict(rootcentipede=.78)
FLYING = ()
_mine = [
    '#14180a', '#2e3a14', '#566a22', '#8ca03c', '#c4d878',   # CHIT (the olive carapace, the head)
    '#3a0a04', '#8a2410', '#cc4a1c', '#f08840', '#ffd09a',   # RUST (the banded plates)
    '#3a2604', '#8a5c10', '#d8a028', '#f8d860', '#fff2b0',   # LEGC (the legs, the antennae)
    '#06260c', '#0e6a22', '#32c850', '#8cf09a', '#e0ffe4',   # VENOM (the dripping fang tips)
    '#2a2014', '#5c4a30', '#98825a', '#cdb98a', '#f0e6c4',   # BELLY (the pale underside)
    '#18181a', '#383a3c', '#5c5e60', '#8a8c8e', '#b8babc',   # GREYD (a dead plate)
    '#2e2600', '#9a8a00', '#e8d400', '#fff56a', '#fffbd0',   # EYEC (the four yellow eyes, the glow)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
CHIT, RUST, LEGC, VENOM, BELLY, GREYD, EYEC = [_i[5 * k:5 * k + 5] for k in range(7)]


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


# ---- the Hollowroot Centipede -------------------------------------------------------------------------------------------------
SEGS = 13


def along(spine, t):
    """The point and the unit tangent at fraction t of the arc length of a polyline."""
    d = [0.]
    for p, q in zip(spine, spine[1:]):
        d.append(d[-1] + math.dist(p, q))
    s = t * d[-1]
    for i in range(1, len(d)):
        if d[i] >= s or i == len(d) - 1:
            u = (s - d[i - 1]) / max(d[i] - d[i - 1], 1e-6)
            p, q = spine[i - 1], spine[i]
            ln = math.dist(p, q) or 1.
            return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u), ((q[0] - p[0]) / ln, (q[1] - p[1]) / ln)


def rootcentipede(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    a = Painter('rootcentipede', st * 3 - w * 3 + recoil)
    # ---- where the head is carried: reared back and high on the wind-up, thrown forward and down on the strike, dropped on the ground when it dies
    hx = 48 - w * 30 + st * 22 - dn * 6 - (7 if hurt else 0)
    hy = 58 + bob * .8 + w * 34 - st * 38 - dn * 48 + (4 if hurt else 0)
    hy = max(hy, 11.)
    crawl = math.sin(ph) * 3.2 if walk else math.sin(ph) * .8
    knots = [(-88, 5), (-60, 8 + crawl * .6 * (1 - dn)), (-28 + (hx - 50) * .25, 12 + (hy - 11) * .16 + crawl * (1 - dn) * .4),
             (-2 + (hx - 50) * .55, 22 + (hy - 11) * .46), (hx - 9, hy - 5)]
    spine = smooth(knots, 8, closed=False)
    # the limp body lies in loose waves along the ground at the end
    if dn > .3:
        spine = [(x, y * (1 - dn * .35) + (math.sin(x * .09) * 2.4 * dn if y < 30 else 0)) for x, y in spine]
    plates = []
    for i in range(SEGS):
        t = (i + .5) / SEGS
        p, u = along(spine, t)
        wd = 8.6 + 6.6 * t - 1.0 * math.sin(t * math.pi)
        plates.append(((p[0], max(p[1], wd * .95)), u, wd))                  # every plate rests on the ground at its lowest
    gone = lambda i: clamp01(dn * 1.5 - (SEGS - 1 - i) / SEGS * .0 - i * .04 * 0) if dn > .0 else 0.      # dead plates fade tail first
    # ---- legs behind the body (far side, dark), then the body, then the legs in front
    def legs(front):
        for i, (p, u, wd) in enumerate(plates):
            nx, ny = -u[1], u[0]
            if ny > 0:
                nx, ny = -nx, -ny                                      # the belly side
            dirn = -1 if (i + (1 if front else 0)) % 2 else 1
            off = 3 if front else 0
            root = (p[0] + nx * wd * .45 + off * u[0], p[1] + ny * wd * .45 + off * u[1])
            swing = math.sin(ph * (1 if walk else .6) + i * .9 + (2.2 if front else 0)) * (3.2 if walk else 1.0) * (1 - dn)
            length = min(max(root[1] + 1, 5.), 13.)
            knee = (root[0] + dirn * (5.5 + swing), root[1] - length * .5)
            foot = (root[0] + dirn * (9 + swing * 1.5), max(0., root[1] - length))
            if dn > .35:                                               # the legs curl up and in as it dies
                foot = (root[0] + dirn * 3, root[1] - 1 + 3 * dn)
                knee = (root[0] + dirn * 6, root[1] - 2)
            ramp = LEGC if front else CHIT
            col = ramp[2] if front else ramp[1]
            a.line([root, knee, foot], col, 1)
            a.line([foot, (foot[0] + dirn * 2.5, foot[1] - 1)], OUTLINE if front else ramp[0], 1)
    legs(False)
    # the pale belly strip under the plates
    belly = []
    for p, u, wd in plates:
        nx, ny = -u[1], u[0]
        if ny > 0:
            nx, ny = -nx, -ny
        belly.append((p[0] + nx * wd * .38, p[1] + ny * wd * .38))
    a.line(belly, BELLY[1], 4)
    for i in range(SEGS - 1, -1, -1):                                  # tail to head, so each plate overlaps the one behind it
        (p, u, wd) = plates[i]
        nxt = plates[i - 1][0] if i > 0 else (p[0] - u[0] * 8, p[1] - u[1] * 8)
        g = clamp01(dn * 1.7 - (SEGS - 1 - i) * .03) if dn > 0 else 0.
        band = RUST if i % 2 == 0 else CHIT
        ramp = GREYD if g > .55 else band
        cap = capsule((p[0] - u[0] * 4.2, p[1] - u[1] * 4.2), (p[0] + u[0] * 4.2, p[1] + u[1] * 4.2), wd * 1.9, wd * 1.9, caps=4)
        shaded(a, cap, ramp, light=(-.55, .8), base=.6, contrast=1.05, grain=.04)
        # a dark seam at the front edge of every plate, a ridge spike on top of the rust ones
        nx, ny = -u[1], u[0]
        q = (p[0] + u[0] * 4.4, p[1] + u[1] * 4.4)
        a.line([(q[0] + nx * wd * .9, q[1] + ny * wd * .9), (q[0] - nx * wd * .9, q[1] - ny * wd * .9)], OUTLINE, 1)
        if i % 2 == 0 and g < .55:
            top = (-abs(nx), -abs(ny)) if ny > 0 else (nx, ny)
            ux, uy = (nx, ny) if ny > 0 else (-nx, -ny)
            fang(a, p[0] + ux * wd * .9, p[1] + uy * wd * .9, 5.5 - (1.8 if i < 3 else 0), 4.2, math.atan2(uy, ux), CHIT)
    legs(True)
    # ---- the tail: a pair of long stiff cerci trailing from the last plate
    tp, tu = plates[0][0], plates[0][1]
    for sd in (-1, 1):
        a.line([(tp[0] - tu[0] * 5, tp[1] - tu[1] * 5), (tp[0] - tu[0] * 15, tp[1] - tu[1] * 15 + sd * 3 + crawl * sd), (tp[0] - tu[0] * 22, max(1., tp[1] - tu[1] * 22 + sd * 6))], LEGC[1], 2)
    # ---- the head: a flared capsule with a heavy hood, four eyes under a scowling brow, antennae and two sickle fangs
    face = math.atan2(-6 + st * -12 + w * 8, 1.0)
    a.ball(hx, hy, 17, 13.5, [RUST[0], RUST[1], RUST[1], RUST[2], RUST[2]], .1)                                         # the head: a dark, glossy rust capsule
    a.poly([(hx - 15, hy + 5), (hx + 2, hy + 15), (hx + 18, hy + 5), (hx + 6, hy + 1)], CHIT[1], outline=CHIT[0])        # an olive hood over the eyes
    a.poly([(hx - 15, hy + 5), (hx + 2, hy + 15), (hx + 4, hy + 8)], CHIT[2])
    a.line([(hx - 9, hy + 11), (hx - 1, hy + 14), (hx + 9, hy + 12)], CHIT[3], 1)
    open_ = (clip == 'attack' and 3 <= n <= 5) or hurt or dn > .3
    spread = 1.0 if open_ else .55
    for sd in (-1, 1):                                                  # the forcipules: sickles that close in front of the mouth
        base = (hx + 11, hy - 5 - sd * 1.5)
        ang = -1.05 + st * .35 + sd * spread * .5 - dn * .25
        length = 25 - dn * 5
        if math.sin(-ang) > .05:
            length = min(length, max(7., (base[1] - 1.) / math.sin(-ang)))                  # the tips stop at the ground
        fang(a, base[0], base[1], length, 10, ang, BONE)
        tip = (base[0] + math.cos(ang) * length, base[1] + math.sin(ang) * length)
        a.ball(tip[0], tip[1] - 1, 2.6, 3.2, VENOM, 0)
        if open_ and dn < .3:
            a.line([(tip[0], tip[1] - 3), (tip[0] + 1, tip[1] - 8 - (n % 2) * 2)], VENOM[3], 1)
    a.line([(hx + 4, hy - 8), (hx + 16, hy - 9), (hx + 13, hy - 12)], OUTLINE, 2)                       # the lip between them
    for k, (ex, ey, er) in enumerate(((hx + 10, hy + 2, 3.6), (hx + 2, hy + 5, 3.2), (hx - 6, hy + 4, 2.7))):
        a.ellipse(ex, ey, er + 1.4, er * .9 + 1.4, OUTLINE)                                              # a dark socket round every eye
        if dn > .22:
            a.line([(ex - 2, ey - 1), (ex + 2, ey + 1)], EYEC[0], 1)                                    # the eyes go out
        else:
            if w > .3 or st > .3:
                glow(a, ex, ey, er * 2.0 + w * 1.5 + st * 1.5, EYEC, .45)
            a.ellipse(ex, ey, er, er * .85, EYEC[2])
            a.ellipse(ex - .4, ey + .3, er * .6, er * .5, EYEC[4])
            a.line([(ex, ey - er * .9), (ex, ey + er * .9)], EYEC[0], 1)
    a.line([(hx - 12, hy + 8), (hx + 6, hy + 5), (hx + 17, hy - 1)], OUTLINE, 3)                       # the scowl: one heavy brow slanting down to the front
    for sd in (0, 1):                                                   # antennae: long, whipping on the wind-up, drooping when it dies
        base = (hx + 2 + sd * 6, hy + 11)
        sway = math.sin(ph * 1.2 + sd * 1.9) * (4 if clip in ('idle', 'walk') else 2) * (1 - dn)
        tipx = base[0] + 8 + sd * 13 + sway - w * 14 + st * 18
        tipy = base[1] + (30 - dn * 40) * (1 - st * .6) + w * 8 - sd * 5
        mid = ((base[0] + tipx) / 2 - 3 + sd * 6, (base[1] + tipy) / 2 + 9 - dn * 16)
        pts = bez(base, mid, (tipx, max(tipy, 3)), 7)
        a.line(pts, OUTLINE, 3)
        a.line(pts, LEGC[2], 1)
    if clip == 'attack' and n in (4, 5):                                # the strike lands: grit thrown up in front of the head
        for k in range(4):
            dust(a, hx + 6 + k * 7, 4 + (k % 2) * 3, 3.2 - k * .45, PEARL)
    if clip == 'attack' and n in (1, 2):                                # the tail gathers: a ripple of leaf litter behind it
        for k in range(3):
            dust(a, -84 + k * 8, 3 + k, 2.2, PEARL)
    if dn > .6:
        for k in range(3):
            dust(a, -40 + k * 30 - dn * 6, 3 + (k % 2) * 2 + dn * 2, 2.8 + dn, PEARL)
    return a


DRAW = dict(rootcentipede=rootcentipede)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/tangle_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='tangle-elite')
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
        atlas.save(ASSETS / f'tangleelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'tangleelites_{kind}.png').convert('RGBA')
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
