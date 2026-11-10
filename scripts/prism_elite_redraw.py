#!/usr/bin/env python3
"""The Prismwaste's new elite (zone shapes pilot): a native PixelFlow source with its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule: every enemy UNIQUE and MEAN, no shared round-eye face. Eight distinct attack and eight distinct death frames.
  shatterhorn  The Shatterhorn (level 48, no quest): a rhinoceros of rose glass, low-slung and heavy, a back of pale prism crystals, plates of grey-violet
               hide on the flanks, a small hard head with two red slit eyes under a notched brow, two lower tusks and a great faceted prism for a horn.
               Winds up by sinking onto its haunches and pawing the ground with a forefoot, the head dipping; the strike is a charge, the whole body
               thrown forward with the horn levelled. Dies when its legs buckle: it sinks onto its chest, the horn snaps off and falls beside it, the
               crystals along its back go dark one by one and the red eyes go out.
The manifest is client/assets/prismelites.txt. The shading helpers are copied from orrery_elite_redraw.py.
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

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/prism-elites'
REGISTRY = ROOT / 'scripts/prism_elite_sources.txt'
MANIFEST = ASSETS / 'prismelites.txt'
PREFIX = 'valhallasc_prism_elite_'
KINDS = ['shatterhorn']
# PixelFlow caps width * height * 34 frames at 1,048,576: 30,840 pixels per frame
KIND_FRAMES = dict(shatterhorn=(190, 96, 90, 88))
SCALE = dict(shatterhorn=.76)
FLYING = ()
_mine = [
    '#240a1e', '#5a2048', '#a8487c', '#e48cb4', '#ffd4e6',   # ROSE (the rose-glass body)
    '#2c1c52', '#6a4aa8', '#b890e8', '#e4cdff', '#fffcff',   # PRISM (the horn and the back crystals)
    '#161018', '#342a3a', '#5a4c64', '#8a7a98', '#bcb0c8',   # HIDE (the grey-violet plates and the hooves)
    '#3a000c', '#a00c28', '#ee2850', '#ff94a8', '#ffe6ea',   # EYE (the red slits, the glow)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE), len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
ROSE_L, PRISM, HIDE, EYE = [_i[5 * k:5 * k + 5] for k in range(4)]
ROSE = [ROSE_L[0], ROSE_L[1], ROSE_L[2], ROSE_L[2], ROSE_L[3]]      # a darker, meaner rose: the lightest tone is kept for the shoulder highlight


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


# ---- the Shatterhorn -----------------------------------------------------------------------------------------------------------
def prism_crystal(a, x, y, rx, h, tilt, dim=0.):
    """A faceted prism standing on (x, y): pale glass, going dull grey as the life leaves it."""
    ramp = PRISM if dim < .5 else [HIDE[0], HIDE[1], HIDE[2], HIDE[3], HIDE[3]]
    a.crystal(x, y, rx, h, ramp, tilt)


def shatterhorn(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    walk = clip == 'walk'
    hurt = clip == 'hurt' and n == 1
    lunge = st * 15 - w * 6 + recoil - 16
    a = Painter('shatterhorn', lunge)
    sag = sm(clamp01(dn * 1.7))                                           # the legs buckle first
    lie = sm(clamp01((dn - .3) * 1.5))                                    # then it sinks onto its chest
    gait = math.sin(ph) if walk else 0.
    by = 54 + bob * .5 - w * 6 + st * 3 - sag * 18 - lie * 11 - (2 if hurt else 0)      # the height of the barrel's centre
    thin = 1 - .1 * lie
    under = [ROSE[0], ROSE[0], ROSE[1], ROSE[1], ROSE[2]]

    # ---- legs: two-bone IK from hip to hoof
    def leg(hx, hy, foot, ramp, bend, th):
        foot = (foot[0], max(foot[1], 6.))
        knee, ft = arm_ik((hx, hy), foot, 21, 21, bend)
        knee = (knee[0], max(knee[1], 8.))                                  # a buckled knee rests on the ground, never under it
        a.limb([(hx, hy), knee], ramp, th)
        a.limb([knee, ft], ramp, th * .82)
        a.ball(ft[0] + 3, max(ft[1] - 1, 4.2), 8, 3.4, HIDE, 0)             # a broad hoof
    def foreleg(sd, ramp):
        base = (32 + sd * 3 + gait * sd * 11, 2 + max(0., gait * sd) * 8)
        if sd > 0:                                                         # the near forefoot paws the ground on the wind-up
            base = mixp(base, (46 + math.sin(ph * 3) * 2, 15 + w * 2), w * .9)
        base = mixp(base, (50 + sd * 4, 3), st)
        base = mixp(base, (44 + sd * 5, 3), lie)
        leg(26 + sd * 3 + st * 3, by - 12, base, ramp, -1, 13)
    def hindleg(sd, ramp):
        base = (-36 + sd * 3 - gait * sd * 11, 2 + max(0., -gait * sd) * 8)
        base = mixp(base, (-52 + sd * 3, 3), st)
        base = mixp(base, (-46 + sd * 6, 3), lie)
        leg(-34 + sd * 3 - st * 3, by - 12, base, ramp, 1, 15)
    far = [HIDE[0], HIDE[0], HIDE[1], HIDE[1], HIDE[2]]
    foreleg(-1, far)
    hindleg(-1, far)

    # ---- the short thick tail with a tuft of crystal
    sway = math.sin(ph * 1.1) * 2.6 * (1 - lie)
    t0 = (-58, by + 6)
    t1 = (-76, by + 8 + sway - sag * 2)
    t2 = (-84 + lie * 4, mix(by - 6 + sway * 1.5, 4, lie))
    tail = bez(t0, t1, t2, 9)
    taper(a, tail, ROSE, 8, 4)
    prism_crystal(a, tail[-1][0] - 1, max(tail[-1][1] - 3, 2), 3.2, 11 - lie * 5, -5, dn)

    # ---- the body: rump, barrel, chest, the shoulder hump and a dark underside
    a.ball(-34, by, 28, 25 * thin, ROSE, .05)
    a.ball(-6, by + 2, 34, 27 * thin, ROSE, 0)
    a.ball(24 + st * 2, by + 4, 28, 27 * thin, ROSE, -.05)
    a.ball(26, by + 22, 20, 10, [ROSE_L[1], ROSE_L[2], ROSE_L[3], ROSE_L[4], ROSE_L[4]], -.2)       # the shoulder hump catches the light
    a.ball(0, by - 17, 42, 9, under, 0)
    # plates of grey-violet hide on the flank: shoulder, back and haunch
    plate(a, [(12, by + 15), (36, by + 17), (40, by - 6), (22, by - 13), (10, by - 2)], HIDE)
    plate(a, [(-18, by + 17), (0, by + 18), (3, by + 2), (-14, by - 1)], HIDE, .74)
    plate(a, [(-50, by + 14), (-27, by + 17), (-23, by - 9), (-43, by - 13), (-53, by - 2)], HIDE)
    # ---- the back: pale prisms along the spine; they go dull one by one as it dies
    for i, (cx_, h, rx, tilt) in enumerate(((32, 24, 6.4, -2), (16, 30, 7.4, -4), (0, 29, 7.2, -5), (-16, 25, 6.4, -6), (-32, 20, 5.4, -7), (-47, 15, 4.4, -8))):
        gone = clamp01(dn * 1.6 - i * .1)
        prism_crystal(a, cx_, by + 23 - (3 if cx_ < -20 else 0) - lie * 3 * (i * .2), rx, h * (1 - gone * .45), tilt, gone * 1.4)

    foreleg(1, ROSE)
    hindleg(1, ROSE)

    # ---- the neck and head: low-slung, the horn levelled on the charge
    hx = 56 + st * 12 - w * 7 + lie * 5 - (3 if hurt else 0)
    hy = mix(by - 13 - st * 6 - w * 3 + math.sin(ph) * .8, 25, lie)
    neck = bez((30, by + 12), (44 + st * 6, by + 10 - st * 4), (hx - 8, hy + 6), 7)
    taper(a, neck, ROSE, 30, 22)
    open_ = (clip == 'attack' and 3 <= n <= 5) or hurt or lie > .4
    gape = 5.0 if open_ else 1.2
    if dn < .3:                                                            # the second horn, small, behind the first
        prism_crystal(a, hx + 3, hy + 13, 6, 22, 7 + st * 5)
    ear_y = hy + 14
    a.poly([(hx - 12, ear_y), (hx - 4, ear_y), (hx - 12 - lie * 3, ear_y + 10 - lie * 6)], HIDE[2], outline=HIDE[0])        # a small notched ear
    a.ball(hx, hy, 17, 14, ROSE, .1)                                       # the skull
    a.ball(hx + 20, hy - 3, 14, 9, ROSE, -.1)                              # the blunt snout
    a.ball(hx + 14, hy - 12 - gape, 14, 5, [HIDE[0], HIDE[1], HIDE[2], HIDE[3], HIDE[3]], 0)     # the lower jaw
    a.poly([(hx + 6, hy - 9), (hx + 33, hy - 6), (hx + 31, hy - 9 - gape), (hx + 8, hy - 11 - gape)], EYE[0])           # the mouth
    for tx, tl, ta in ((hx + 14, 16, 1.15), (hx + 24, 13, 1.3)):           # two lower tusks, up and forward
        fang(a, tx, hy - 10 - gape, tl, 4, ta, BONE)
    a.ellipse(hx + 31, hy - 1, 1.8, 1.4, HIDE[0])                          # a nostril
    # the brow: a heavy notched slab over the eye
    a.poly([(hx - 3, hy + 9), (hx + 23, hy + 4), (hx + 23, hy + 11), (hx + 12, hy + 12), (hx + 7, hy + 16), (hx - 1, hy + 15)], HIDE[1], outline=HIDE[0])
    a.line([(hx + 1, hy + 11), (hx + 21, hy + 7)], HIDE[3], 1)
    ex, ey = hx + 11, hy + 4.5
    if dn > .22 or False:
        a.line([(ex - 3, ey), (ex + 3, ey - 1)], OUTLINE, 2)               # the eye goes out
    else:
        glow(a, ex, ey, 8 + w * 3 + st * 3, EYE, 1.0)
        a.poly([(ex - 4.4, ey - .6), (ex, ey + 2), (ex + 5.4, ey - .2), (ex + 1, ey - 2.2)], EYE[3])
        a.line([(ex - 3, ey - .2), (ex + 4, ey - .4)], EYE[4], 1)
    # ---- the horn: a great faceted prism on the snout; it snaps off as the beast falls
    horn_x, horn_y = hx + 22, hy + 5
    snap = sm(clamp01((dn - .3) * 3))
    if snap < .02:
        prism_crystal(a, horn_x, horn_y, 9.5, 44, 22 + st * 7 - w * 4 + math.sin(ph) * 1.2)
    else:
        a.poly([(horn_x - 8, horn_y), (horn_x + 8, horn_y), (horn_x + 5, horn_y + 8 - snap * 3), (horn_x - 4, horn_y + 9 - snap * 3)], PRISM[1], outline=PRISM[0])    # the broken stump
        fx = mix(horn_x + 24, horn_x + 16, snap)                           # the horn falls forward and lies on the ground
        fy = mix(horn_y + 30, 6, snap)
        ang = mix(.6, 0., snap)
        shard = [(fx - 18 * math.cos(ang), fy - 18 * math.sin(ang) - 5), (fx + 18 * math.cos(ang), fy + 18 * math.sin(ang)), (fx - 18 * math.cos(ang), fy - 18 * math.sin(ang) + 6)]
        shaded(a, shard, PRISM, base=.6, contrast=1.1)
    if clip == 'attack' and n in (5, 6):                                    # the charge lands: dust kicked up round the forefeet
        for k in range(4):
            dust(a, 46 + k * 9, 4 + (k % 2) * 3, 3.2 - k * .4, PEARL)
    if clip == 'attack' and n in (1, 2):                                    # the forefoot scrapes: grit thrown back
        for k in range(3):
            dust(a, 36 + k * 7, 3 + k, 2.4, PEARL)
    if dn > .8:
        for k in range(3):
            dust(a, -40 + k * 28, 3 + (k % 2) * 2, 2.8, PEARL)
    return a



DRAW = dict(shatterhorn=shatterhorn)
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/prism_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='prism-elite')
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
        atlas.save(ASSETS / f'prismelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'prismelites_{kind}.png').convert('RGBA')
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
