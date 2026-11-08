#!/usr/bin/env python3
"""The Ribbonwild's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  whorlshell  The Whorlshell (level 73, no quest): a giant snail whose shell is a banded carousel disc (rose, gold, teal, violet round a cream hub, a dark spiral
              wound across it, bone spikes along the upper rim). A long low foot, a hooded head with a jagged toothed maw and two eyestalks ending in red slit eyes
              under scowling brows. Winds up by rearing the head high and back on its neck, the shell tilting; the strike is the head slammed down and forward, the
              body thrown after it. Dies when it deflates: the foot sags flat, the head drops, the eyestalks go limp and the red eyes go out, a crack runs across the
              shell and the bands go grey one by one.
The manifest is client/assets/ribbonelites.txt. The shading helpers are copied from prism_elite_redraw.py.
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
OUT = ROOT / 'test-results/ribbon-elites'
REGISTRY = ROOT / 'scripts/ribbon_elite_sources.txt'
MANIFEST = ASSETS / 'ribbonelites.txt'
PREFIX = 'valhallasc_ribbon_elite_'
KINDS = ['whorlshell']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(whorlshell=(176, 108, 80, 100))
SCALE = dict(whorlshell=.82)
FLYING = ()
_mine = [
    '#3a1c24', '#7a3a4a', '#c4687c', '#f0a0a8', '#ffd8d0',   # FLESH (the foot and the head)
    '#4a0a2c', '#a01c5e', '#e04a8c', '#ff8cb8', '#ffd0e4',   # ROSEB (the outer shell band)
    '#4a3000', '#a87000', '#f0b820', '#ffe068', '#fff4b8',   # GOLDB
    '#00343a', '#0a7a82', '#34c8c8', '#8ceaea', '#d8ffff',   # TEALB
    '#2a1448', '#6a3cb0', '#a478e8', '#d0b4ff', '#f0e4ff',   # VIOLB (the inner band and the hub)
    '#18121c', '#3a3240', '#5a4c64', '#8a7e98', '#b8aec4',   # GREYB (a dead band, the hooks)
    '#3a000c', '#a00c28', '#ee2850', '#ff94a8', '#ffe6ea',   # EYE (the red slits, the glow)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
FLESH, ROSEB, GOLDB, TEALB, VIOLB, GREYB, EYE = [_i[5 * k:5 * k + 5] for k in range(7)]


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


# ---- the Whorlshell -----------------------------------------------------------------------------------------------------------
def whorlshell(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    lunge = st * 9 - w * 5 + recoil
    a = Painter('whorlshell', lunge)
    sag = dn                                             # the foot sags flat
    gone = dn                                                # the bands go grey from the outside in
    crawl = math.sin(ph) * 2.2 if walk else 0.
    tilt = w * 9 - st * 6 + (3 if hurt else 0)                              # the shell tips back on the wind-up and forward on the slam
    # ---- the long low foot: a tapered spine from the tail to the neck, with a pale sole line
    h0 = 12 - sag * 4
    spine = bez((-78, 9), (-44, h0 + 4 + crawl * .6), (-8, h0 + 5), 8) + bez((-8, h0 + 5), (14, h0 + 6 - sag * 2), (34 + st * 4, 14 - sag * 3), 6)[1:]
    taper(a, spine, FLESH, 22 - sag * 7, 16)
    a.line([(-72, 1), (-40, 1), (-8, 1), (30, 1)], FLESH[1], 1)
    for k in range(5):                                                     # ripples along the sole
        a.line([(-62 + k * 18 + crawl * (1 if k % 2 else -1), 6), (-60 + k * 18 + crawl, 9 - sag * 3)], FLESH[3], 1)
    # ---- the shell: a banded carousel disc on the back, rim spikes, a dark spiral wound across it
    cx_, cy_ = -16 + tilt * -.5, 46 + bob * .4 - sag * 6 - w * 2 + st * 2
    bands = [(ROSEB, 40, 0, 0), (GOLDB, 31, 1.5, -1), (TEALB, 22.5, 2.6, -1.6), (VIOLB, 14.5, 3.4, -2.2)]
    spikes = 7
    for i in range(spikes):                                               # bone spikes along the upper-left rim
        ang = math.radians(112 + i * 21 + tilt * 1.5)
        bx, by_ = cx_ + math.cos(ang) * 38, cy_ + math.sin(ang) * 38
        fang(a, bx, by_, 13 - abs(i - 3) * 1.4 - gone * 5, 6, ang, BONE)
    for k, (ramp, r, ox, oy) in enumerate(bands):
        g_ = clamp01(gone * 1.5 - k * .14)
        ramp_ = GREYB if g_ > .55 else ramp
        a.ball(cx_ + ox, cy_ + oy, r, r, ramp_, .1 * k)
    a.ball(cx_ + 3.8, cy_ - 2.6, 6.5, 6.5, [VIOLB[2], VIOLB[3], VIOLB[4], VIOLB[4], VIOLB[4]] if gone < .55 else GREYB, 0)    # the hub catches the light
    pts = []
    for k in range(40):
        t = k / 39.
        r = 3 + t * 36
        ang = t * math.pi * 4.6 + .7
        pts.append((cx_ + 3.8 * (1 - t) + math.cos(ang) * r, cy_ - 2.6 * (1 - t) + math.sin(ang) * r * .98))
    a.line(pts, OUTLINE, 2)
    if gone > .35:                                                         # a crack runs across the dying shell
        run = clamp01((gone - .35) * 1.6)
        crack = [(cx_ - 30, cy_ + 20), (cx_ - 18, cy_ + 6), (cx_ - 8, cy_ + 12), (cx_ + 4, cy_ - 4), (cx_ + 16, cy_ + 2), (cx_ + 30, cy_ - 22)]
        a.line(crack[:max(2, int(1 + run * 5))], OUTLINE, 2)
    # ---- neck and head: reared back on the wind-up, slammed down and forward on the strike
    hx = 46 + st * 24 - w * 9 + sag * 10 - (4 if hurt else 0)
    hy = 33 + w * 30 - st * 17 - sag * 22 + bob * .4 + (2 if hurt else 0)
    hy = max(hy, 17.)
    neck = bez((30, 14 - sag * 4), (36 + st * 6 - w * 6, 22 + w * 14 - sag * 6), (hx - 5, hy - 5), 7)
    taper(a, neck, FLESH, 22 - sag * 6, 17)
    open_ = (clip == 'attack' and 3 <= n <= 5) or hurt or sag > .4
    gape = 8.0 if open_ else 2.2
    a.ball(hx, hy, 15, 13, FLESH, .1)                                       # the hooded head
    a.poly([(hx - 14, hy + 2), (hx - 2, hy + 14), (hx + 11, hy + 10), (hx + 2, hy + 2)], FLESH[1], outline=FLESH[0])            # a heavy hood over the eyes
    a.poly([(hx + 4, hy - 4), (hx + 22, hy - 2 - gape * .3), (hx + 22, hy - 7 - gape), (hx + 5, hy - 9 - gape)], EYE[0])       # the jagged mouth
    teeth(a, hx + 6, hx + 21, hy - 3 - gape * .3, 3.2, BONE, down=True, n=5)
    teeth(a, hx + 6, hx + 21, hy - 8 - gape, 3.0, BONE, down=False, n=5)
    a.ball(hx + 9, hy - 10 - gape, 10, 4, [FLESH[0], FLESH[1], FLESH[1], FLESH[2], FLESH[2]], 0)                                   # the lower lip
    # ---- two eyestalks, each ending in a red slit eye under a scowling brow; they sway on the idle and the walk, whip on the wind-up, wilt as it dies
    for sd in (0, 1):
        bx_, by0 = hx - 5 + sd * 12, hy + 9
        lift = 1 - sag * .75
        sway_ = math.sin(ph * 1.3 + sd * 1.7) * (3.2 if clip in ('idle', 'walk') else 1.4) * (1 - sag)
        tip = (bx_ - 10 + sd * 20 + sway_ + w * (-6 if sd == 0 else 6) + st * 3, by0 + (26 + w * 8 - st * 10) * lift - sag * 6)
        mid = ((bx_ + tip[0]) / 2 + 2 - sd * 4, (by0 + tip[1]) / 2 + 4 - sag * 5)
        stalk = bez((bx_, by0), mid, tip, 6)
        taper(a, stalk, FLESH, 6, 4)
        glow_r = 9 + w * 3 + st * 3
        a.ball(tip[0], tip[1], 6.2, 6.2, [FLESH[0], FLESH[1], FLESH[2], FLESH[2], FLESH[3]], 0)
        if dn > .22:
            a.line([(tip[0] - 3.5, tip[1] - 1), (tip[0] + 3.5, tip[1] + 1)], OUTLINE, 2)                     # the eye goes out
        else:
            glow(a, tip[0], tip[1], glow_r, EYE, 1.0)
            a.poly([(tip[0] - 5, tip[1]), (tip[0], tip[1] + 2.4), (tip[0] + 5, tip[1] - .2), (tip[0], tip[1] - 2.2)], EYE[3])
            a.line([(tip[0] - 3.6, tip[1] - .1), (tip[0] + 3.4, tip[1] - .2)], EYE[4], 1)
            a.line([(tip[0] - 6, tip[1] + 6 - (2 if sd else 0)), (tip[0] + 6, tip[1] + 3 + (2 if sd else 0))], OUTLINE, 2)       # the scowl
    if clip == 'attack' and n in (4, 5):                                    # the slam lands: dust kicked up in front of the head
        for k in range(4):
            dust(a, 50 + k * 8, 4 + (k % 2) * 3, 3.2 - k * .45, PEARL)
    if clip == 'attack' and n in (1, 2):                                    # the foot gathers: a ripple of grit behind it
        for k in range(3):
            dust(a, -48 + k * 8, 3 + k, 2.2, PEARL)
    if dn > .6:
        for k in range(3):
            dust(a, -30 + k * 26 - dn * 6, 3 + (k % 2) * 2 + dn * 2, 2.8 + dn, PEARL)
    return a


DRAW = dict(whorlshell=whorlshell)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/ribbon_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='ribbon-elite')
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
        atlas.save(ASSETS / f'ribbonelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'ribbonelites_{kind}.png').convert('RGBA')
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
