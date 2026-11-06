#!/usr/bin/env python3
"""The Emberfall Crags' two new elites (zone shapes pilot): native PixelFlow sources, per-kind frames.

preview | montage | build | refresh <kinds> | export | verify

Owner rule (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye face. Each kind has its own face and silhouette:
  slagmaw   a low, wide fire salamander under cracked basalt plates with magma in the gaps, a jaw as wide as its body full of glowing gullet,
            small yellow slits high on the skull. Rears, gapes, then snaps down. Dies: the magma goes out plate by plate, the legs splay and it sags flat.
  ashwing   a carrion bird of ash and bone: a bare skull beak, ragged smoking wings with ember edges, long raking talons, one white pinprick eye.
            Hovers; wings thrown up, then a dive with the talons first. Dies: the wings fold, it falls to the ground and lies on its side, smoking.
Eight distinct attack and death frames each. The manifest is client/assets/cragselites.txt. Drawing helpers come from the Lapis redo.
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
from lapis_slime_redraw import (Rig, BasePainter, OUTLINE, BONE, CRIMSON, GOLD, EYE_WHITE, PEARL, clamp01, curves, dying, settle,
                                polar, cross_eye, mix, mixp, sm, bez, taper, fang, dust, old)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/crags-elites'
REGISTRY = ROOT / 'scripts/crags_elite_sources.txt'
MANIFEST = ASSETS / 'cragselites.txt'
PREFIX = 'valhallasc_crags_elite_'
KINDS = ['slagmaw', 'ashwing']
KIND_FRAMES = dict(slagmaw=(192, 112, 80, 104), ashwing=(176, 174, 84, 164))
FLYING = ('ashwing',)
_mine = [
    '#0e0a0c', '#221a1e', '#3a2e32', '#5a4a4c', '#86767a',   # PLATE (cracked basalt)
    '#2a0806', '#6a1408', '#c02a0a', '#f06a14', '#ffc040',   # MAGMA (hot gaps)
    '#14100e', '#2c2422', '#4a3e3a', '#6e6058', '#9a8c80',   # DEAD (cold plates and cold magma)
    '#1e1a1c', '#3a3436', '#5e5658', '#8a8284', '#bcb4b0',   # ASH (feathers)
    '#5a4a3a', '#8a7a62', '#b8a888', '#dcd0b4', '#f4ecd8',   # SKULL (bone beak)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
PLATE, MAGMA, DEAD, ASH, SKULL = [_i[5 * k:5 * k + 5] for k in range(5)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = 1.
        self.im = Image.new('P', (self.w, self.h), 0)
        from PIL import ImageDraw
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax + dx

    def pos(self, x, y):
        return round(self.cx + x), round(self.ay - y)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width)))


def slit_eye(r, x, y, w=4.2, shut=False, glow=None):
    glow = glow or CRIMSON
    if shut:
        r.line([(x - w, y - .6), (x + w, y + .6)], OUTLINE, 2)
        return
    r.poly([(x - w, y - .6), (x - w * .1, y + 1.8), (x + w, y - 1.5), (x + w * .2, y - 2.6)], glow[3], outline=OUTLINE)
    r.ellipse(x + w * .2, y - .6, 1, 1.3, OUTLINE)
    r.poly([(x - w - 1.5, y + 2.8), (x + w + 1, y - .6), (x + w + 1, y + 1.8), (x - w - .5, y + 4.4)], OUTLINE)


# ---- Slagmaw ---------------------------------------------------------------------------------------------------------
def slagmaw(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .3) * 1.5))
    gait = math.sin(ph) if clip == 'walk' else 0.
    a = Painter('slagmaw', st * 9 - w * 6 + recoil + gait * 1.5)
    base = 17 + bob * .5 - lie * 8 - fall * 2 + w * 2 - st * 2
    cold = clamp01(dn * 1.6)                     # the magma goes out from the tail forward
    heat = lambda t: MAGMA if cold < t else [DEAD[0], DEAD[1], DEAD[1], DEAD[2], DEAD[2]]
    r = Rig(a, -8, 10, -w * .12 + st * .10 - lie * .02)

    def leg(x, ramp, phase, front):
        sw = math.sin(ph + phase) * 6 if clip == 'walk' else 0
        lift = max(0, math.cos(ph + phase)) * 2.5 if clip == 'walk' else 0
        hip = (x, base + 3)
        foot = mixp((x + sw + (11 if front else -11), 3 + lift), (x + (18 if front else -18), 4), lie)
        knee = mixp((x + (13 if front else -13) + sw * .4, base + 4), (x + (15 if front else -15), base + 3), lie)
        a.limb([r.t(*hip), knee, foot], ramp, 8.5)
        for k in (-1, 0, 1):                     # stubby splayed claws
            fang(a, foot[0] + k * 3.4 + 2, foot[1] - .8, 5, 2.6, -.2 + k * .35, BONE)

    leg(-24, [PLATE[0], PLATE[0], PLATE[1], PLATE[1], PLATE[2]], 1.6, False)
    leg(10, [PLATE[0], PLATE[0], PLATE[1], PLATE[1], PLATE[2]], 0, True)
    # tail: thick at the root, a long whip of plates that swings, then settles flat
    sweep = math.sin(ph) * 5 if clip != 'die' else 0
    tail = bez((-34, base + 4), (-52, base + 8 + sweep + w * 6), (-70, base - 6 + sweep * 1.6 - fall * 4), 11)
    tw = settle(r, tail, lie, -1, .15)
    taper(a, tw, PLATE, 12, 2)
    for k, p in enumerate(tw[1:-1]):
        if k % 2 == 0:
            a.ball(p[0], p[1] + 1.5, 2.2, 1.6, heat(.25))
        fang(a, p[0], p[1] + 4.5 - k * .4, 6 - k * .4, 4, 1.7, PLATE)
    # the body: long and low, belly glowing through
    r.ball(-20, base + 8, 22, 15, PLATE, -.1)
    r.ball(4, base + 10, 25, 17, PLATE, -.1)
    r.poly([(-34, base - 3), (24, base - 4), (20, base + 2), (-30, base + 2)], heat(.8)[2], outline=OUTLINE)
    r.poly([(-27, base - 2.5), (16, base - 3), (12, base), (-23, base)], heat(.8)[4])
    # back plates: broken slabs, each with a hot seam round it; they die one at a time
    slabs = [(-34, 6, 11), (-22, 11, 13), (-8, 15, 15), (8, 16, 15), (22, 12, 11)]
    for k, (x, up, wd) in enumerate(slabs):
        y = base + up + 7
        hot = heat(.15 + k * .17)
        r.poly([(x - wd / 2 - 1.5, y - 7), (x - wd / 2 + 1, y + 5), (x + 2, y + 8), (x + wd / 2 + 2, y + 3), (x + wd / 2 + 1, y - 7)], hot[3], outline=OUTLINE)
        r.poly([(x - wd / 2, y - 6), (x - wd / 2 + 2.4, y + 3.4), (x + 2, y + 5.6), (x + wd / 2, y + 1.5), (x + wd / 2 - .5, y - 6)], PLATE[2])
        r.poly([(x - wd / 2 + 2, y + 2), (x + 2, y + 4), (x + 3, y + 1), (x - wd / 2 + 2.6, y - 1)], PLATE[3])
        r.line([(x - 1, y + 5), (x + 2, y - 1), (x - 2, y - 6)], hot[3], 1)
        fang(a, *r.t(x - 2 + k % 2 * 3, y + 7), 6 + k % 2 * 4, 4.6, 1.5 + (k - 2) * .1, PLATE)
    leg(-14, PLATE, 3.2, False)
    leg(19, PLATE, 4.7, True)
    # head: flat, a wedge wider than the neck. The lower jaw drops, the upper skull rears back; the gullet is the brightest thing on it.
    gape = .22 + w * .62 + st * .1 + (.1 if clip == 'idle' and n in (2, 3) else 0) + (.28 if clip == 'hurt' and n == 1 else 0) + (.2 if clip == 'die' and n < 4 else 0)
    gape *= 1 - lie * .3
    hx, hy = 34 + st * 4 - w * 3, base + 13 + w * 11 - st * 3 - lie * 6
    tilt = w * .34 - st * .30 - lie * .10
    # the neck: as thick as the body, so the head never leaves it
    a.limb([r.t(10, base + 11), (hx - 14, hy + 3), (hx - 2, hy + 2)], PLATE, 17)
    for k, t in enumerate((.25, .55, .85)):
        px, py = mixp(r.t(10, base + 11), (hx - 2, hy + 2), t)
        fang(a, px, py + 8, 6, 4.4, 1.5, PLATE)
        a.line([(px - 3, py + 7), (px + 2, py - 3)], heat(.9)[3], 1)
    jaw = Rig(a, hx - 2, hy - 2, tilt - gape)
    jaw.poly([(hx - 9, hy + 2), (hx + 6, hy - 9), (hx + 38, hy - 9), (hx + 46, hy - 3), (hx + 34, hy + 1)], PLATE[2], outline=OUTLINE)
    jaw.poly([(hx - 5, hy + 1), (hx + 34, hy - .5), (hx + 40, hy - 3.4), (hx + 8, hy - 6)], heat(.96)[1])
    jaw.poly([(hx - 3, hy + .5), (hx + 16, hy - .2), (hx + 12, hy - 3.2), (hx - 1, hy - 2)], heat(.96)[3])
    for k in range(6):                            # lower teeth, big at the front
        jaw.fang(hx + 10 + k * 5.6, hy + .4, 4 + k * .8, 3.6, 1.57, BONE)
    if gape > .4 and cold < .9:                   # the throat lights the inside of the mouth
        a.ball(hx + 2, hy - 1, 8 + gape * 4, 6 + gape * 3, MAGMA)
    up = Rig(a, hx - 2, hy, tilt + gape * .34)
    up.poly([(hx - 13, hy - 3), (hx - 11, hy + 13), (hx + 4, hy + 20), (hx + 22, hy + 16), (hx + 42, hy + 8), (hx + 49, hy + 1), (hx + 36, hy - 3)], PLATE[2], outline=OUTLINE)
    up.poly([(hx - 7, hy + 10), (hx + 5, hy + 16), (hx + 20, hy + 13), (hx + 10, hy + 6)], PLATE[3])
    up.poly([(hx - 10, hy - 3), (hx + 36, hy - 3), (hx + 42, hy + 1), (hx + 8, hy + 3)], heat(.96)[1])
    for k in range(7):                            # upper teeth, hooked
        up.fang(hx + 7 + k * 5.5, hy - 2.6, 5.5 + (k % 2) * 2.5, 4, -1.57, BONE)
    for x, y in ((hx + 34, hy + 7), (hx + 25, hy + 12), (hx + 44, hy + 3)):     # nostril ridge
        up.fang(x, y, 5, 3.6, 1.1, PLATE)
    up.line([(hx + 2, hy + 19), (hx + 7, hy + 10), (hx + 2, hy + 5)], heat(.9)[3], 1)
    # the eyes: two small yellow slits, high and close together, under a brow plate
    eye = GOLD if cold < .9 else DEAD
    slit_eye(up, hx + 12, hy + 12, 4.2, shut=dying(clip, n), glow=eye)
    slit_eye(up, hx + 20, hy + 11.5, 3.2, shut=dying(clip, n), glow=eye)
    if clip == 'attack' and n in (4, 5):          # sparks spat on the snap
        for k in range(5):
            a.ball(hx + 42 + k * 3.4, hy + 6 - k * 2 + (k % 2) * 6, 2.6 - k * .3, 2.2 - k * .25, MAGMA)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, 60 + k * 7, 5 + (k % 2) * 4, 3.2 - k * .5, PEARL)
    return a


# ---- Ashwing ---------------------------------------------------------------------------------------------------------
def ashwing(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.1)
    lie = sm(clamp01((dn - .35) * 1.6))
    dead = clip == 'die'
    a = Painter('ashwing', st * 14 - w * 8 + recoil + fall * 6)
    hover = 56 + math.sin(ph * 2) * 3 + w * 5 - st * 6
    y0 = mix(hover, 13, fall)
    # it never rolls through the ground: a little nose-down on the dive, then flat on its side
    tilt = -st * .30 + w * .18 - fall * .08
    r = Rig(a, 0, y0, tilt)
    beat = [.0, -.30, -.55, -.26][n % 4] if clip not in ('attack', 'die') else 0
    flap = w * .12 - st * .55 + beat

    def wing(far):
        """A bony arm thrown up and out, ragged primaries hanging off it like a torn cloak, embers along the trailing edge."""
        ramp = ASH
        root = (-4 if far else 3, y0 + 13)
        ang = mix((2.18 if far else 1.05) - flap * (-1 if far else 1), 3.3 if far else 2.9, fold := fall)
        span = (58 if far else 55) * (1 - fold * .5)
        elbow = polar(*root, ang, span * .46)
        out = ang + (.5 if far else -.5) * (1 - fold)
        hand = polar(*elbow, out, span * .54)
        hang = mix(-2.2 if far else -1.9, 3.3, fold)
        pts = []
        for k in range(9):
            t = k / 8
            b = mixp(hand, elbow, t * 2) if t < .5 else mixp(elbow, root, (t - .5) * 2)
            ln = (span * .62) * (1 - t * .55) + (k % 3 - 1) * 6
            f = polar(*b, hang + t * .55 + math.sin(k * 2.4) * .12, ln * (1 - fold * .5))
            pts.append((b, f))
        col = ramp[1] if far else ramp[2]
        for b, f in pts:
            nx, ny = (f[1] - b[1]) * .16, -(f[0] - b[0]) * .16
            a.poly([r.t(b[0] + nx, b[1] + ny), r.t(*f), r.t(b[0] - nx, b[1] - ny)], col, outline=OUTLINE)
            if not (dead and n >= 3) and (pts.index((b, f)) % 2 == 0):
                a.ball(*r.t(*f), 1.9, 1.7, MAGMA)
        a.limb([r.t(*root), r.t(*elbow), r.t(*hand)], ASH if far else [ASH[1], ASH[1], ASH[2], ASH[2], ASH[3]], 5.4)
        fang(a, *r.t(*elbow), 8, 3.6, ang + 1.4, BONE)
        fang(a, *r.t(*hand), 11, 3.6, out, BONE)

    wing(True)
    # tail: a fan of torn plumes
    for k, ang in enumerate((3.15, 3.45, 3.75)):
        p = (-17, y0 + 2)
        q = polar(*p, ang + st * .3, 30 - k * 4)
        taper(a, [r.t(*p), r.t(*mixp(p, q, .5)), r.t(*q)], [ASH[0], ASH[0], ASH[1], ASH[1], ASH[2]], 8, 1)
    # body: hunched shoulders, a ragged black cape of feathers
    r.poly([(-22, y0 + 4), (-16, y0 + 16), (0, y0 + 21), (15, y0 + 17), (20, y0 + 6), (12, y0 - 9), (-8, y0 - 12)], ASH[1], outline=OUTLINE)
    r.poly([(-14, y0 + 8), (-6, y0 + 16), (10, y0 + 14), (6, y0 + 5)], ASH[2])
    for k in range(7):                            # the ragged lower edge of the cape
        x = -18 + k * 6
        r.fang(x, y0 - 8 + abs(k - 3) * 1.5, 7 + (k % 2) * 3, 4.4, -1.5 - k * .04, ASH)
    # legs: tucked up in flight, thrown forward on the dive, curled in death
    for k, lx in enumerate((-3, 6)):
        reach = st * 20 - w * 8
        knee = (lx + 4 + reach * .45, y0 - 15 + st * 4)
        foot = (lx + 8 + reach, y0 - 26 + st * 9 + fall * 12 + math.sin(ph + k) * 1.5)
        r.limb([(lx, y0 - 8), knee, foot], [SKULL[0], SKULL[0], SKULL[1], SKULL[1], SKULL[2]], 3.4)
        for off in (-.7, 0, .7):
            r.fang(foot[0], foot[1], 11 - fall * 5, 3.2, -.9 + off + st * .6 + fall * 1.8, BONE)
    # neck: bare and wattled, hung forward and low like a vulture's, snapping out on the dive
    hx, hy = 32 + st * 10 - w * 8 - fall * 2, y0 + 8 - st * 8 + w * 12 - fall * 4
    nk = bez((13, y0 + 12), (32 - w * 6, y0 + 26 - st * 8), (hx - 2, hy + 3), 7)
    taper(a, [r.t(*p) for p in nk], [PLATE[1], PLATE[2], PLATE[3], SKULL[0], SKULL[1]], 8, 4.4)
    for k in range(6):                            # the ruff
        r.fang(13 + k * 1.2, y0 + 11 + k, 9, 5, .4 + k * .36, ASH)
    # skull: small, flat and long, a deep hooked beak, a black brow over one white pinprick
    h = L.HeadRig(a, hx, hy, 1.25, phi=tilt - st * .28 + w * .1, cx=hx, cy=hy)
    op = 1 + w * 6 + st * 2.5 + (3 if clip == 'hurt' and n == 1 else 0)
    h.poly([(hx + 2, hy - 4), (hx + 15, hy - 5 - op), (hx + 21, hy - 8 - op), (hx + 4, hy - 7)], SKULL[1], outline=OUTLINE)
    h.poly([(hx - 7, hy - 3), (hx - 8, hy + 3), (hx - 2, hy + 7), (hx + 8, hy + 7), (hx + 17, hy + 5), (hx + 25, hy - 1), (hx + 27, hy - 12), (hx + 21, hy - 7), (hx + 12, hy - 4), (hx + 2, hy - 5)], SKULL[2], outline=OUTLINE)
    h.poly([(hx - 3, hy + 3), (hx + 9, hy + 5.4), (hx + 20, hy + 2), (hx + 8, hy + 1)], SKULL[3])
    h.ellipse(hx + 15, hy + 1, 1, .7, OUTLINE)
    if dying(clip, n):
        cross_eye(h, hx + 3, hy + 2, 2)
    else:
        h.poly([(hx - 2, hy + 3.4), (hx + 8, hy + 1.6), (hx + 6, hy - .4), (hx - 1, hy + .4)], OUTLINE)
        h.ellipse(hx + 4.4, hy + 1.2, .9, .9, EYE_WHITE)
    h.poly([(hx - 3, hy + 5.4), (hx + 9, hy + 4), (hx + 9, hy + 2.4), (hx - 2, hy + 3.2)], OUTLINE)    # the scowling brow
    wing(False)
    if dead and n >= 3:                           # smoke off the dead wings
        for k in range(3):
            dust(a, -22 + k * 24, 18 + (n - 3) * 3 + k * 4, 3.4 - k * .6, PEARL)
    return a


DRAW = dict(slagmaw=slagmaw, ashwing=ashwing)
# the shared frame/preview machinery reads these names
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/crags_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='crags-elite')
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
        atlas.save(ASSETS / f'cragselites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'cragselites_{kind}.png').convert('RGBA')
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
    {'preview': L.preview, 'montage': L.montage, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'montage']()
