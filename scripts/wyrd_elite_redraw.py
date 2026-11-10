#!/usr/bin/env python3
"""The Wyrdwood's new elite (zone shapes pilot): native PixelFlow source, its own frame.

preview | montage | extents | build | refresh <kinds> | export | verify

Owner rule (2026-11-04): every enemy UNIQUE and MEAN, no shared round-eye face.
  hangedking   The Hanged King of Gallows Hill (level 26, no quest): a tall gaunt corpse-king, grey-green flesh drawn tight over a ribcage that a loop of old
               rope winds round, a skull under a crown of rusted nails with two hollow sockets burning violet, a noose pulled tight round the neck whose
               long end streams up and back like a banner, and a cloak of black crow feathers in tatters from the shoulders. His weapon is a piece of the
               gallows itself: a rope-bound timber beam with a loop dangling from its tip. Swings it back over the shoulder, then brings it down in a
               ring of violet light. Dies: the beam falls, the long rope goes slack, the knees fold and the sockets go dark.
Eight distinct attack and death frames. The manifest is client/assets/wyrdelites.txt. Drawing helpers come from the Lapis redo.
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
OUT = ROOT / 'test-results/wyrd-elites'
REGISTRY = ROOT / 'scripts/wyrd_elite_sources.txt'
MANIFEST = ASSETS / 'wyrdelites.txt'
PREFIX = 'valhallasc_wyrd_elite_'
KINDS = ['hangedking']
KIND_FRAMES = dict(hangedking=(184, 164, 70, 156))
FLYING = ()
_mine = [
    '#10161a', '#2a3a38', '#566a60', '#8aa090', '#c4d4c0',   # FLESH (grey-green, drawn tight)
    '#2a1a0a', '#5a3c1c', '#946a34', '#c8a05a', '#ecd090',   # ROPE (old hemp)
    '#08060e', '#1c1230', '#3a2862', '#5e4a92', '#8c78c0',   # FEATHER (black crow, violet sheen)
    '#1a0a32', '#5a2aa0', '#a066f0', '#d8b0ff', '#f8f0ff',   # GLOW (the sockets, the strike)
    '#1a0e06', '#3e2410', '#6a421e', '#966034', '#bc8a52',   # TIMBER (the gallows beam)
    '#1c0c08', '#4e2414', '#8a4a24', '#c07a3c', '#e8b068',   # RUST (crown nails)
]
L.PALETTE.extend(c for c in _mine if c not in L.PALETTE)
PALETTE = L.PALETTE
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
_i = [PALETTE.index(c) for c in _mine]
FLESH, ROPE, FEATHER, GLOW, TIMBER, RUST = [_i[5 * k:5 * k + 5] for k in range(6)]


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kindframe.check_frame(*KIND_FRAMES[kind])
        self.S = 1.
        self.im = Image.new('P', (self.w, self.h), 0)
        from PIL import ImageDraw
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax + dx

    def pos(self, x, y):
        return round(self.cx + x), min(round(self.ay - y), self.ay + 4)      # nothing sinks more than four rows under the ground, so a fallen king stays on the canvas

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width)))


def hangedking(clip, n):
    w, st, dn, ph, bob, recoil = curves(clip, n)
    fall = sm(dn * 1.05)
    lie = sm(clamp01((dn - .2) * 1.3))
    a = Painter('hangedking', st * 8 - w * 7 + recoil + lie * 6)
    walk = clip == 'walk'
    hip = 47 + bob * .5 - lie * 28 - fall * 2 + w * 1.5 - st * 4
    stg = sm(clamp01(dn * 2.4)) * (1 - lie) if clip == 'die' else 0.      # the first beats of a death: thrown back, the arms flung
    lean = -w * .1 + st * .15 + lie * .6 - stg * .14
    R = Rig(a, 0, hip, lean)
    dark = [FLESH[0], FLESH[0], FLESH[1], FLESH[1], FLESH[2]]
    lit = [FLESH[0], FLESH[1], FLESH[1], FLESH[2], FLESH[3]]
    sway = math.sin(ph * 1.2) * 2.4 if clip in ('idle', 'walk') else -st * 5

    def leg(x, p0, far):
        sw = math.sin(ph + p0) * 7 if walk else 0
        lift = max(0, math.cos(ph + p0)) * 5 if walk else 0
        if clip == 'attack':
            sw = (st * 6 if x > 0 else -st * 3) - w * 3
        foot = (x + sw + lie * (12 if x > 0 else -9), 3 + lift)
        knee = (x + 3 + sw * .4 + lie * (8 if x > 0 else 1), hip * .5 + lift * .5 - lie * 3)
        a.limb([(x, hip), knee, foot], dark if far else lit, 7)
        a.ball(knee[0] + 1, knee[1], 4.6, 4.6, dark if far else lit)
        a.ellipse(foot[0] + 3, foot[1] + 1.2, 8, 3, FLESH[0])
        a.ellipse(foot[0] + 4, foot[1] + 1.8, 6, 2, FLESH[2] if not far else FLESH[1])
        for k in range(3):                                                         # long dry toes
            a.line([(foot[0] + 3 + k * 3, foot[1] + 2), (foot[0] + 8 + k * 3, foot[1] + 1)], BONE[2], 1)

    leg(-5, 0, True)
    # the beam: gripped near its butt, swung back over the shoulder on the wind-up, brought down on the strike
    hand_idle, hand_up, hand_dn = (28, hip + 4), (-6, hip + 70), (34, hip + 18)
    hand = mixp(mixp(hand_idle, hand_up, w), hand_dn, st)
    hand = (hand[0] - stg * 6, hand[1] + stg * 9)
    if clip == 'idle':
        hand = (hand[0] + math.sin(ph) * 1.2, hand[1] + math.cos(ph) * .8)
    ang_idle, ang_up, ang_dn = 1.42, 2.55, -.05
    ang = mix(mix(ang_idle, ang_up, w), ang_dn, st)
    if lie:
        hand = (22 + lie * 10, hip + 2)
        ang = mix(ang, -.02, lie)
    far_arm = [(-6, hip + 44), (-17 - stg * 5, hip + 30 - lie * 8 + stg * 10), (-12 + lie * 4 - stg * 9, hip + 14 - lie * 8 + stg * 20)]
    a.limb([R.t(*far_arm[0]), R.t(*far_arm[1]), R.t(*far_arm[2])], dark, 5)
    for k in range(3):                                                             # the far hand's long fingers
        a.line([R.t(far_arm[2][0], far_arm[2][1]), R.t(far_arm[2][0] - 3 + k * 3, far_arm[2][1] - 7)], FLESH[1], 1)
    # the shroud: ragged strips from the hips
    for k, (x0, l0) in enumerate(((-9, 20), (-3, 26), (4, 22), (10, 17))):
        R.poly([(x0, hip + 4), (x0 + 6, hip + 4), (x0 + 4 + sway * .4, max(1.5, hip - l0 + (k % 2) * 4 + lie * 6)), (x0 + 1, max(2.5, hip - l0 + 6))], FEATHER[1], outline=OUTLINE)
    # the cloak of crow feathers: from the shoulders, trailing behind
    for k in range(7):
        base = (-8 - k * .6, hip + 52 - k * 4)
        tip = (-26 - k * 4 + sway * (1 + k * .2) - st * 4, max(1.5 + k * .4, hip + 34 - k * 7 - lie * 12 + (k % 2) * 3))
        taper(a, [R.t(*p) for p in bez(base, (base[0] - 8, base[1] - 2 + sway * .3), tip, 6)], FEATHER, 5.4 - k * .3, .8)
    # the ribcage and the rope round it
    R.ball(1, hip + 30, 11.5, 22, [FLESH[0], FLESH[1], FLESH[2], FLESH[2], FLESH[3]], -.03)
    R.ball(5, hip + 38, 7, 11, [FLESH[1], FLESH[2], FLESH[2], FLESH[3], FLESH[3]])
    for k in range(5):
        y0 = hip + 22 + k * 5.4
        R.line([(-6, y0 - 1.4), (2, y0 + 1), (10, y0 - .4)], BONE[2], 1)           # ribs showing through the skin
    R.line([(-9, hip + 42), (-1, hip + 34), (8, hip + 26), (12, hip + 14)], ROPE[2], 3)
    R.line([(-8, hip + 24), (0, hip + 30), (9, hip + 38), (12, hip + 46)], ROPE[1], 3)
    for k in range(6):
        R.ball(-7 + k * 3.4, hip + 40 - k * 2.6, 1.3, 1.1, ROPE)
    leg(6, math.pi, False)
    # the head: a skull under a crown of nails, the noose at the neck
    hd = Rig(a, 2, hip + 56, lean * .6 - w * .1 + st * .14 + lie * .35)
    T = lambda x, y: R.t(*hd.t(x, y))
    a.limb([R.t(1, hip + 44), T(1, hip + 54)], lit, 7)
    a.ball(*T(2, hip + 66), 10.4, 12, [FLESH[0], FLESH[1], FLESH[2], FLESH[3], FLESH[4]], lean)
    a.poly([T(5, hip + 62), T(17, hip + 59), T(18, hip + 51), T(12, hip + 49), T(4, hip + 53)], FLESH[3], outline=OUTLINE)       # the muzzle, drawn tight
    a.poly([T(7, hip + 58), T(17, hip + 56.5), T(17, hip + 52), T(7, hip + 53.5)], OUTLINE)                                      # the open mouth
    for k in range(5):
        a.poly([T(7.5 + k * 2.2, hip + 58), T(9 + k * 2.2, hip + 58), T(8.2 + k * 2.2, hip + 54.6)], BONE[4])
    for ex in (8.5, 14.5):                                                         # two hollow sockets burning violet
        gx, gy = T(ex, hip + 66)
        if dying(clip, n, 2):
            a.line([(gx - 2.4, gy), (gx + 2.4, gy)], OUTLINE, 1)
        else:
            a.ellipse(gx, gy, 3.6, 3.2, OUTLINE)
            a.ellipse(gx + .4, gy, 2.4, 2.1, GLOW[2])
            a.ellipse(gx + .8, gy, 1.2, 1.1, GLOW[4])
    for k in range(7):                                                             # the crown: rusted nails driven through the brow, pointing up
        ang_n = -.3 + k * .26
        bx, by = 2 + math.cos(1.57 + ang_n * 1.9) * 9, hip + 72 + math.sin(1.57 + ang_n * 1.9) * 5.6
        length = 8 + (k % 3) * 3
        a.poly([T(bx - 1, by), T(bx + 1, by), T(bx + math.sin(ang_n) * 3, by + length)], RUST[3], outline=OUTLINE)
    a.line([T(-8, hip + 70), T(0, hip + 74.4), T(11, hip + 72)], RUST[1], 2)       # the band they are driven through
    # the noose: a loop pulled tight at the neck, the long end streaming up and back from the knot
    a.line([T(-6, hip + 55.4), T(2, hip + 53.4), T(10, hip + 54.4)], ROPE[3], 3)
    knot = T(-6, hip + 56)
    a.ball(knot[0], knot[1], 3, 3.4, ROPE)
    tail = bez(knot, (knot[0] - 8 + sway * 2, knot[1] + 18), (knot[0] - 22 + sway * 4 + st * 6 - lie * 10, knot[1] + 34 - lie * 30 - st * 8), 10)
    taper(a, tail, ROPE, 3, 1)
    for k in range(3):                                                             # the frayed end
        p = tail[-1]
        a.line([p, (p[0] - 3 - k * 2, p[1] - 4 + k * 3 + sway * .5)], ROPE[3], 1)
    # the near arm and the gallows beam
    shoulder = R.t(11, hip + 46)
    elbow = (shoulder[0] + 9 + st * 6 - w * 14, shoulder[1] - 9 + w * 15 - lie * 6)
    a.limb([shoulder, elbow, hand], lit, 6)
    a.ball(*hand, 3.4, 3.2, lit)
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    butt = (hand[0] - dx * 12, hand[1] - dy * 12)
    tip = (hand[0] + dx * 46, hand[1] + dy * 46)
    a.limb([butt, tip], TIMBER, 7)
    a.line([(butt[0] + nx * 2.4, butt[1] + ny * 2.4), (tip[0] + nx * 2.4, tip[1] + ny * 2.4)], TIMBER[1], 1)
    for k in range(4):                                                             # the rope binding the beam, and its old nails
        bp = (hand[0] + dx * (12 + k * 9), hand[1] + dy * (12 + k * 9))
        a.line([(bp[0] + nx * 4, bp[1] + ny * 4), (bp[0] - nx * 4, bp[1] - ny * 4)], ROPE[2], 2)
        a.ball(bp[0] + nx * 1.2, bp[1] + ny * 1.2, 1.2, 1.1, RUST)
    loop_c = (tip[0] + dx * 6 - nx * 2, tip[1] + dy * 6 - ny * 2 - 6 + sway * .3)
    a.line([tip, (tip[0] + dx * 1 - nx * 3, tip[1] - 2)], ROPE[2], 2)
    for k in range(12):
        t = k / 12 * math.tau
        a.ball(tip[0] - nx * 3 + math.cos(t) * 6, tip[1] - 9 + math.sin(t) * 7, 1.4, 1.4, ROPE)        # the loop, hanging open
    if clip == 'attack' and n in (4, 5):                                           # the ring of violet light the beam throws on the strike
        for k in range(3):
            c = tip
            pts = [(c[0] + math.cos(t) * (8 + k * 8 + (n - 4) * 4), c[1] + math.sin(t) * (6 + k * 5 + (n - 4) * 3)) for t in np.linspace(-1.2, 1.2, 11)]
            a.line(pts, GLOW[3] if k % 2 else GLOW[2], 1)
    if clip == 'attack' and n in (5, 6):
        for k in range(3):
            dust(a, tip[0] + 4 + k * 9, 4 + (k % 2) * 3, 3.2 - k * .5, PEARL)
    if clip == 'idle' and n in (1, 4):                                             # a drifting feather
        a.ball(-30 + n * 3, hip - 4 - n * 2, 1.6, 1, FEATHER)
    return a


DRAW = dict(hangedking=hangedking)
# the shared frame/preview machinery reads these names
L.KINDS, L.DRAW, L.KIND_FRAMES, L.FLYING, L.OUT = KINDS, DRAW, KIND_FRAMES, FLYING, OUT
frames, rgba, kind_frame = L.frames, L.rgba, L.kind_frame


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def raw(kind):
    return ROOT / f'scripts/wyrd_elite_{kind}_raw.npz'


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
    meta = dict(frame=[96, 96], anchor=[48, 90], kinds=KINDS, clips=clips, sprites={}, tops={}, artStyle='wyrd-elite')
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
        atlas.save(ASSETS / f'wyrdelites_{kind}.png', optimize=True)
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', len(KINDS) * 34, 'saved PixelFlow frames', hashlib.sha256(MANIFEST.read_bytes()).hexdigest()[:12])


def verify():
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'wyrdelites_{kind}.png').convert('RGBA')
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
