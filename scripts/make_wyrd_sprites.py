#!/usr/bin/env python3
"""makesprites workflow for the Wyrdwood monsters: preview | build [--replace] | export | verify.

Seven kinds share the Emberfall Crags contract (scripts/make_crag_sprites.py): one 96x96 frame, a foot anchor at
(48, 90), right-facing art (the game mirrors it) and five clips (idle 6, walk 8, attack 8, hurt 4, die 8) so client/field.js
drives them with the Ironhide's state machine: walk frames 2-4 are the hop, 5-7 the landing, attack 0-2 the windup,
3-5 the lunge, 6-7 the recovery.

  boar      Rotfang Boar     (L21)  a bristled, blight-veined boar that charges
  crow      Gallowcrow       (L23)  a big raven that hovers and shoots feathers
  troll     Mosshide Troll   (L25)  a hunched, mossy brute with a tree growing out of its shoulder; ground-pounds
  weaver    Wyrdweaver       (L27)  a hooded spinner of fate, golden threads between her hands
  ram       Stormram         (L29)  a storm-charged ram with crackling horns
  oakhorn   Oakhorn (elite)  (L25)  the grove's guardian stag, antlers like an oak in autumn, a golden thread through its chest
  hrungnir  Hrungnir (elite) (L30)  a granite storm giant with a lightning beard

The drawing toolkit (shaded ellipsoids and capsules lit from the upper left, a dithered ramp per material, an outline
around every part) is imported from make_crag_sprites.py. `build` saves ONE new 34-frame PixelFlow sprite per kind
(valhallasc_wyrd_<kind>_all) and refuses existing names unless --replace is given (it discards editor edits).
`export` reads the editor frames back, so edits survive, and writes client/assets/wyrd_<kind>.png plus wyrd.txt.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_crag_sprites as mc  # noqa: E402
from make_crag_sprites import (AX, AY, CLIPS, DITHER, H, W, XX, YY, Frame, Palette, api, capsule, ellipsoid,  # noqa: E402
                               gradient, lerp, polygon, rgba, rng_for, rotate)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
PREFIX = 'valhallasc_wyrd_'
KINDS = ['boar', 'crow', 'troll', 'weaver', 'ram', 'oakhorn', 'hrungnir']
RAW = ROOT / 'scripts'


def smooth(points, samples):
    """Catmull-Rom-ish resampling of a polyline into `samples` points (for tails, necks, threads)."""
    pts = np.array(points, dtype=float)
    out = []
    for i in range(samples):
        t = i / (samples - 1) * (len(pts) - 1)
        j = min(int(t), len(pts) - 2)
        u = t - j
        p0, p1, p2, p3 = pts[max(j - 1, 0)], pts[j], pts[j + 1], pts[min(j + 2, len(pts) - 1)]
        out.append(tuple(.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)))
    return out


def ik(a, target, l1, l2, flip=1):
    """Two-bone IK: the middle joint of a limb from `a` to `target` (flip chooses which way it bends)."""
    dx, dy = target[0] - a[0], target[1] - a[1]
    d = max(abs(l1 - l2) + .01, min(math.hypot(dx, dy), l1 + l2 - .01))
    base = math.atan2(dy, dx)
    c = max(-1., min(1., (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    k = base + flip * math.acos(c)
    return (a[0] + math.cos(k) * l1, a[1] + math.sin(k) * l1)


def eye_dead(f, x, y, name='socket'):
    f.dots([(x - 1, y - 1), (x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x, y)], name)


def chain_paint(f, discs, ramp, dither=.55):
    """One outline round a chain of ellipsoids, then every disc shaded without its own outline."""
    union = np.zeros((H, W), bool)
    for shape in discs:
        union |= shape[0]
    f.a[mc.dilate(union) & ~union] = f.p['ol']
    for shape in discs:
        f.paint(shape, ramp, outline=False, dither=dither)
    return union


def thread(f, points, name, samples=24, width=1):
    pts = smooth(points, samples)
    for a, b in zip(pts, pts[1:]):
        f.line(a, b, name, width)


def fit(grid, floor=AY, margin=1):
    """Slides a frame back inside the canvas and above the ground line (only for effects that wander)."""
    ys, xs = np.nonzero(grid)
    if not len(xs):
        return grid
    dx = 0
    if xs.min() < margin:
        dx = margin - xs.min()
    if xs.max() + dx > W - 1 - margin:
        dx = (W - 1 - margin) - xs.max()
    dy = min(0, (floor + 2) - ys.max()) if ys.max() > floor + 2 else 0
    if dx or dy:
        out = np.zeros_like(grid)
        yy, xx = ys + dy, xs + dx
        ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        out[yy[ok], xx[ok]] = grid[ys[ok], xs[ok]]
        return out
    return grid


# ----------------------------------------------------------------------------------------------
# The four-legged rig used by the boar, the ram and the stag: side-on, facing right.
# ----------------------------------------------------------------------------------------------
def quad_gait(clip, n):
    """Per-frame (body dx, lift, crouch, tilt, head dx, head dy, head tilt, jaw, foot offsets x4 [far hind, far front, near hind, near front], foot lifts x4, tail, eyes, glow, flash)."""
    d = dict(dx=0., lift=0., crouch=0., tilt=0., hx=0., hy=0., ht=0., jaw=0., fx=[0., 0., 0., 0.], fl=[0., 0., 0., 0.], tail=0., eyes='open', glow=1., flash=False, lie=0., shake=0.)
    if clip == 'idle':
        d['crouch'] = [0, .5, 1, .5, 0, .3][n]
        d['hy'] = [0, .3, .8, .3, 0, .2][n]
        d['tail'] = [0, .3, .5, .3, 0, -.2][n]
        d['glow'] = [1, 1.05, 1.1, 1.05, 1, .95][n]
        d['eyes'] = 'blink' if n == 3 else 'open'
    elif clip == 'walk':
        # 0-1 gather, 2-4 airborne (the hop), 5-7 landing and settling
        d['lift'] = [0, 0, 4, 8, 5, 0, 0, 0][n]
        d['crouch'] = [1, 3, 0, 0, 0, 3, 2, 1][n]
        d['tilt'] = [.02, .06, -.06, -.1, -.03, .05, .03, 0][n]
        d['fx'] = [[0, 0, 0, 0], [0, 0, 0, 0], [-4, 3, -5, 5], [-7, 6, -8, 8], [-4, 3, -5, 5], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]][n]
        d['fl'] = [[0, 0, 0, 0], [0, 0, 0, 0], [3, 3, 3, 3], [5, 5, 5, 5], [3, 3, 3, 3], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]][n]
        d['hy'] = [0, 1, -1, -2, -1, 1, 1, 0][n]
        d['tail'] = [0, 0, .3, .5, .3, -.2, -.1, 0][n]
    elif clip == 'attack':
        d['dx'] = [-2, -4, -5, 4, 9, 7, 2, 0][n]
        d['crouch'] = [2, 4, 5, 0, 0, 1, 0, 0][n]
        d['tilt'] = [.05, .12, .18, -.12, -.2, -.1, 0, 0][n]
        d['hx'] = [-1, -3, -4, 4, 6, 3, 1, 0][n]
        d['hy'] = [1, 3, 5, 2, 3, 2, 1, 0][n]
        d['ht'] = [.1, .25, .4, .05, -.1, 0, 0, 0][n]
        d['jaw'] = [0, 0, .4, .8, .6, .2, 0, 0][n]
        d['fx'] = [[0, 0, 0, 0], [-1, 0, -1, 0], [-3, -2, -3, -2], [3, 3, 3, 4], [6, 6, 6, 7], [3, 4, 3, 4], [0, 1, 0, 1], [0, 0, 0, 0]][n]
        d['fl'] = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [3, 2, 3, 2], [5, 4, 5, 4], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]][n]
        d['lift'] = [0, 0, 0, 3, 3, 0, 0, 0][n]
        d['eyes'] = 'angry'
        d['glow'] = [1.1, 1.25, 1.4, 1.4, 1.3, 1.1, 1, 1][n]
        d['tail'] = [.2, .4, .6, -.4, -.5, -.2, 0, 0][n]
    elif clip == 'hurt':
        d['dx'] = [-4, -3, -1, 0][n]
        d['crouch'] = [3, 2, 1, 0][n]
        d['tilt'] = [-.14, -.08, -.02, 0][n]
        d['ht'] = [-.3, -.15, 0, 0][n]
        d['hy'] = [-2, -1, 0, 0][n]
        d['jaw'] = [.7, .4, 0, 0][n]
        d['flash'] = n == 0
        d['eyes'] = 'hurt' if n < 3 else 'angry'
        d['glow'] = [1.5, 1.3, 1.1, 1][n]
        d['shake'] = [1, .6, .2, 0][n]
    elif clip == 'die':
        d['flash'] = n == 0
        d['eyes'] = 'dead'
        d['dx'] = [0, -3, -4, -4, -4, -4, -4, -4][n]
        d['lift'] = [0, 3, 0, 0, 0, 0, 0, 0][n]
        d['lie'] = [0, 0, .25, .55, .85, 1, 1, 1][n]       # how far over on its side it is (1: lying flat)
        d['crouch'] = [0, 0, 3, 6, 8, 9, 9, 9][n]
        d['glow'] = [1.5, 1.2, 1, .8, .55, .35, .2, .1][n]
        d['jaw'] = [.5, .8, .5, .3, .2, .2, .2, .2][n]
    return d


def lerp_pts(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


# ----------------------------------------------------------------------------------------------
# Rotfang Boar: a bristled, blight-veined boar with curved tusks. It lowers its head and charges.
# ----------------------------------------------------------------------------------------------
BOAR = Palette({
    'fur0': '#1e1511', 'fur1': '#33261d', 'fur2': '#4f3a2b', 'fur3': '#6f5340', 'fur4': '#93725a', 'fur5': '#b8977a',
    'far0': '#150f0c', 'far1': '#251a14', 'far2': '#3a2a20', 'bel0': '#6f5a4a', 'bel1': '#947c68', 'bel2': '#b9a18a',
    'bris0': '#120c09', 'bris1': '#2a1e16', 'rot0': '#5a1410', 'rot1': '#a82a1a', 'rot2': '#e2551f', 'rot3': '#ff9b3d',
    'rot4': '#ffe27a', 'tusk0': '#6d5b38', 'tusk1': '#c4b283', 'tusk2': '#f4ead0', 'tuskred': '#9a3a28', 'hoof': '#17120f',
    'hoof2': '#2e2620', 'eye': '#ff5a30', 'eye2': '#ffd0a0', 'socket': '#10070a', 'mouth': '#3b1218', 'tongue': '#c8465a',
    'snout': '#c28a7a', 'snout2': '#e3ab9a', 'nostril': '#2a0f12', 'drool': '#e8f0d8',
})


class Ctx:
    """What a quadruped's decoration callbacks need: the frame, palette, gait, and the body's frame of reference."""

    def __init__(self, f, p, g, bx, by, tilt, ang):
        self.f, self.p, self.g, self.bx, self.by, self.tilt, self.ang = f, p, g, bx, by, tilt, ang

    def at(self, dx, dy):
        x, y = rotate(dx, dy, -self.tilt)
        return self.bx + x, self.by + y


def draw_quad(f, p, g, S):
    """A side-on four-legged animal. S describes it: dims, ramps and the callbacks `tail`, `deco_back`, `deco_front`, `head`."""
    lie = g['lie']
    if S.get('gscale'):
        g = dict(g, dx=g['dx'] * S['gscale'], hx=g['hx'] * S['gscale'], lift=g['lift'] * S['gscale'])
    bx = 44 + g['dx']
    by = AY - S['height'] - g['lift'] + g['crouch'] + lie * 6
    tilt = g['tilt']
    ang = tilt - lie * 1.45
    c = Ctx(f, p, g, bx, by, tilt, ang)
    ground = AY - 1
    feet_base = S.get('feet', [-11, 14, -5, 19])
    legs = []
    for i, base in enumerate(feet_base):
        fx = bx + base + g['fx'][i] + 6 * lie * (1 if i % 2 else -1)
        fy = ground - g['fl'][i] - lie * (14 + 4 * (i % 2))
        legs.append((fx, fy))
    hips = [c.at(-13, 6), c.at(12, 7), c.at(-9, 7), c.at(16, 8)]
    flips = [1, -1, 1, -1]
    l1, l2 = S['leg']

    def draw_leg(i, ramp):
        hip, foot = hips[i], legs[i]
        knee = ik(hip, foot, l1, l2, flips[i])
        t = S.get('thick', 1.)
        f.paint(capsule(hip, knee, (4.3 if i in (0, 2) else 3.8) * t, 2.6 * t), ramp, dither=.35)
        f.paint(capsule(knee, foot, 2.6 * t, 1.9 * t), ramp, dither=.35)
        f.paint(ellipsoid(foot[0] + 1, foot[1] - .5, 2.9 * t, 2.0), p.ramp(*S['hoof']), dither=.2)

    for i in (0, 1):
        draw_leg(i, p.ramp(*S['far']))
    S['tail'](c)
    rx, ry = S['barrel']
    rump = ellipsoid(*c.at(-9, 0), S['rump'][0], S['rump'][1] - lie * 2, ang)
    barrel = ellipsoid(*c.at(2, 1), rx, ry - lie * 2, ang)
    hump = ellipsoid(*c.at(*S['hump'][:2]), S['hump'][2], S['hump'][3] - lie * 3, ang)
    belly = ellipsoid(*c.at(2, 8), 17, 5, ang)
    union = rump[0] | barrel[0] | hump[0]
    f.a[mc.dilate(union) & ~union] = p['ol']
    f.paint(rump, p.ramp(*S['body'][:-1]), outline=False, dither=.5)
    f.paint(barrel, p.ramp(*S['body']), outline=False, dither=.5)
    f.paint(hump, p.ramp(*S['body']), outline=False, dither=.5)
    f.paint((belly[0] & union, np.clip(belly[1] * .8 + .1, 0, 1)), p.ramp(*S['belly']), outline=False, dither=.4)
    S['deco_back'](c)
    for i in (2, 3):
        draw_leg(i, p.ramp(*S['near']))
    S['head'](c)
    S['deco_front'](c)
    if g['flash']:
        f.whiten()
    return fit(f.a)


def eyes_on(f, g, ex, ey, glow_name, brow='bris0', size=2.6):
    eyes = g['eyes']
    if eyes == 'blink':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    elif eyes == 'dead':
        eye_dead(f, ex, ey)
    else:
        f.flat(ellipsoid(ex, ey, size, size - .4)[0], 'socket')
        f.dots([(ex + 1, ey), (ex, ey - 1)] if eyes != 'hurt' else [(ex, ey), (ex + 1, ey + 1)], glow_name)
        if eyes in ('angry', 'open') and brow:
            f.line((ex - 3, ey - 3), (ex + 3, ey - 1 - (1 if eyes == 'angry' else 0)), brow, 1)


# ----------------------------------------------------------------------------------------------
# Rotfang Boar: a bristled, blight-veined boar with curved tusks. It lowers its head and charges.
# ----------------------------------------------------------------------------------------------
BOAR = Palette({
    'fur0': '#1e1511', 'fur1': '#33261d', 'fur2': '#4f3a2b', 'fur3': '#6f5340', 'fur4': '#93725a', 'fur5': '#b8977a',
    'far0': '#150f0c', 'far1': '#251a14', 'far2': '#3a2a20', 'bel0': '#6f5a4a', 'bel1': '#947c68', 'bel2': '#b9a18a',
    'bris0': '#120c09', 'bris1': '#2a1e16', 'rot0': '#5a1410', 'rot1': '#a82a1a', 'rot2': '#e2551f', 'rot3': '#ff9b3d',
    'rot4': '#ffe27a', 'tusk0': '#6d5b38', 'tusk1': '#c4b283', 'tusk2': '#f4ead0', 'tuskred': '#9a3a28', 'hoof': '#17120f',
    'hoof2': '#2e2620', 'eye': '#ff5a30', 'eye2': '#ffd0a0', 'socket': '#10070a', 'mouth': '#3b1218', 'tongue': '#c8465a',
    'snout': '#c28a7a', 'snout2': '#e3ab9a', 'nostril': '#2a0f12', 'drool': '#e8f0d8',
})


def boar(clip, n):
    f = Frame(BOAR)
    p = BOAR
    g = quad_gait(clip, n)
    glow = g['glow']

    def tail(c):
        tb = c.at(-20, -3)
        pts = smooth([tb, (tb[0] - 5, tb[1] - 3 - g['tail'] * 4), (tb[0] - 8, tb[1] - 8 - g['tail'] * 6), (tb[0] - 5, tb[1] - 11 - g['tail'] * 5)], 10)
        for a, b in zip(pts, pts[1:]):
            f.line(a, b, 'bris0', 3)
        for a, b in zip(pts, pts[1:]):
            f.line(a, b, 'fur2', 1)

    def deco_back(c):
        for (ox, oy, rx, ry, a) in [(2, -8, 5.5, 3.6, .3), (-8, -6, 4.2, 3, -.4), (9, 0, 3.4, 4.6, .6), (-14, 2, 3.4, 2.6, .2)]:
            crystal = ellipsoid(*c.at(ox, oy), rx, ry, a + c.ang)
            f.paint((crystal[0], np.clip(crystal[1] * glow, 0, 1)), p.ramp('rot0', 'rot1', 'rot2', 'rot3', 'rot4'), outline=True, edge='rot0', dither=.4)
        for (a, b) in [(c.at(-3, -4), c.at(5, 3)), (c.at(7, -9), c.at(12, -2)), (c.at(-12, 0), c.at(-6, 4))]:
            f.line(a, b, 'rot2' if glow > .9 else 'rot1', 1)
        for sweep in (0, 1):
            for k in range(9):
                t = k / 8
                sx, sy = c.at(lerp(-18, 13, t), lerp(-11, -14, math.sin(t * math.pi * .9)) - 2 + (1 if k % 2 else 0))
                h = 5 + 2.5 * math.sin(t * math.pi) + (k % 2)
                sway = g['shake'] * (1 if k % 2 else -1)
                tri = polygon([(sx - 2, sy + 1), (sx + 1.5 + sway, sy - h), (sx + 2, sy + 1)])
                if sweep == 0:
                    f.a[mc.dilate(tri) & ~tri] = p['ol']
                else:
                    f.a[tri] = p['bris1' if k % 3 else 'bris0']

    def head(c):
        lie = g['lie']
        hx0, hy0 = c.at(19, -3)
        head_c = (hx0 + 10 + g['hx'], hy0 + 4 + g['hy'] + lie * 2)
        ht = .25 + g['ht']
        neck = capsule(c.at(14, -3), head_c, 8.5, 7.2)
        skull = ellipsoid(head_c[0] + 1, head_c[1], 10.5, 8.6, ht)
        snout_c = (head_c[0] + 10.5 * math.cos(ht), head_c[1] + 10.5 * math.sin(ht) + 1.5)
        snout = ellipsoid(snout_c[0], snout_c[1], 6.5, 4.8, ht)
        jaw_c = (head_c[0] + 7 * math.cos(ht) - g['jaw'] * 1, head_c[1] + 6.4 + g['jaw'] * 4.5)
        jaw = ellipsoid(jaw_c[0] + 2, jaw_c[1], 8, 3.2, ht * .6 + g['jaw'] * .35)
        tusk_base = (snout_c[0] - 3.5, jaw_c[1] - 1)
        tusk_tip = (snout_c[0] + 6.5, snout_c[1] - 13 - g['jaw'] * 1.5)
        mid = (snout_c[0] + 7.5, snout_c[1] + 1.5)
        tp = smooth([tusk_base, mid, tusk_tip], 9)
        for a, b in zip(tp, tp[1:]):
            f.line(a, b, 'ol', 5)
        for k, (a, b) in enumerate(zip(tp, tp[1:])):
            f.line(a, b, 'tusk1' if k < 5 else 'tusk2', 3 if k < 6 else 2)
        f.dots([tp[-1], tp[-2]], 'tuskred')
        if g['jaw'] > .1:
            mouth = ellipsoid(snout_c[0] - 1, snout_c[1] + 3.2 + g['jaw'] * 1.5, 6, 1.8 + g['jaw'] * 2.2, ht)
            f.flat(mouth[0], 'mouth', outline=True)
        chain_paint(f, [neck, skull], p.ramp('fur0', 'fur1', 'fur2', 'fur3', 'fur4'), dither=.5)
        f.paint(jaw, p.ramp('far1', 'fur1', 'fur2', 'fur3'), outline=True, dither=.4)
        f.paint(snout, p.ramp('fur1', 'snout', 'snout2'), outline=True, dither=.4)
        f.dots([(snout_c[0] + 5, snout_c[1] - 1), (snout_c[0] + 5, snout_c[1] + 1)], 'nostril')
        ear = polygon([(head_c[0] - 2, head_c[1] - 7), (head_c[0] - 6, head_c[1] - 16 - g['shake'] * 2), (head_c[0] + 3, head_c[1] - 8)])
        f.a[mc.dilate(ear) & ~ear] = p['ol']
        f.paint((ear, np.full((H, W), .5)), p.ramp('fur1', 'fur2', 'rot1'), outline=False, dither=.2)
        eyes_on(f, g, head_c[0] + 3, head_c[1] - 3, 'eye')

    return draw_quad(f, p, g, dict(
        height=29, leg=(11.5, 11.5), thick=1., barrel=(21, 13.5), rump=(15, 13), hump=(11, -5, 12, 11),
        body=['fur0', 'fur1', 'fur2', 'fur3', 'fur4', 'fur5'], belly=['bel0', 'bel1', 'bel2'], far=['far0', 'far1', 'far2'],
        near=['fur0', 'fur1', 'fur2', 'fur3', 'fur4'], hoof=['hoof', 'hoof2'], tail=tail, deco_back=deco_back, deco_front=lambda c: None, head=head))


# ----------------------------------------------------------------------------------------------
# Stormram: a fleece the colour of a thundercloud, curled horns that crackle, glowing eyes. It charges faster than anything.
# ----------------------------------------------------------------------------------------------
RAM = Palette({
    'wool0': '#252c3d', 'wool1': '#414c66', 'wool2': '#68799b', 'wool3': '#9bb0cf', 'wool4': '#d2e0f0', 'wool5': '#f2f8ff',
    'far0': '#14161d', 'far1': '#22252f', 'far2': '#343845', 'bel0': '#59647e', 'bel1': '#7b88a6', 'bel2': '#a3b2cc',
    'face0': '#15171e', 'face1': '#262a35', 'face2': '#3c4252', 'face3': '#5b6377', 'horn0': '#40362a', 'horn1': '#7a6b4e',
    'horn2': '#b9a97c', 'horn3': '#e6dab0', 'bolt0': '#2a73d6', 'bolt1': '#5fc4ff', 'bolt2': '#b8f0ff', 'bolt3': '#f2fdff',
    'eye': '#8ff3ff', 'socket': '#070a12', 'hoof': '#15171c', 'hoof2': '#2b2e38', 'nostril': '#0c0d12', 'mouth': '#3a1620',
})


def bolt_path(rng, a, b, jag=3.0, steps=5):
    pts = [a]
    for i in range(1, steps):
        t = i / steps
        pts.append((lerp(a[0], b[0], t) + rng.uniform(-jag, jag), lerp(a[1], b[1], t) + rng.uniform(-jag, jag)))
    pts.append(b)
    return pts


def ram(clip, n):
    f = Frame(RAM)
    p = RAM
    g = quad_gait(clip, n)
    rng = rng_for('ram', clip, n)
    glow = g['glow']

    def tail(c):
        tb = c.at(-21, -2)
        f.paint(ellipsoid(tb[0] - 2, tb[1] + 1, 4.5, 3.4, c.ang), p.ramp('wool1', 'wool2', 'wool3', 'wool4'), dither=.4)

    def deco_back(c):
        # fleece: lumpy clouds over the back and shoulders
        for (ox, oy, r) in [(-14, -7, 6), (-7, -10, 6.5), (0, -11, 6.8), (7, -11, 6.5), (13, -8, 6), (-17, 1, 5), (16, 0, 5.5), (-4, 6, 5.5), (5, 7, 5.5)]:
            bump = ellipsoid(*c.at(ox, oy), r, r * .85, c.ang)
            f.paint(bump, p.ramp('wool0', 'wool1', 'wool2', 'wool3', 'wool4', 'wool5'), outline=True, edge='ol', dither=.5)
        # static: short blue arcs hopping over the fleece
        for _ in range(int(2 + 3 * (glow - .8))):
            a = c.at(rng.uniform(-16, 14), rng.uniform(-14, 4))
            b = (a[0] + rng.uniform(-7, 7), a[1] + rng.uniform(-6, 3))
            for u, v in zip(bolt_path(rng, a, b, 1.6, 3), bolt_path(rng, a, b, 1.6, 3)[1:]):
                f.line(u, v, 'bolt1', 1)
            f.dots([a, b], 'bolt3')

    def head(c):
        lie = g['lie']
        hx0, hy0 = c.at(19, -2)
        head_c = (hx0 + 8 + g['hx'], hy0 + 5 + g['hy'] + lie * 2)
        ht = .2 + g['ht']
        neck = capsule(c.at(14, -2), head_c, 7.5, 6)
        skull = ellipsoid(head_c[0], head_c[1], 8.5, 7.6, ht)
        muzzle_c = (head_c[0] + 8.5 * math.cos(ht), head_c[1] + 8.5 * math.sin(ht) + 2)
        muzzle = ellipsoid(muzzle_c[0], muzzle_c[1], 6, 4.8, ht)
        jaw = ellipsoid(muzzle_c[0] - 1, muzzle_c[1] + 3.6 + g['jaw'] * 3.5, 5.5, 2.2, ht + g['jaw'] * .3)
        if g['jaw'] > .1:
            f.flat(ellipsoid(muzzle_c[0], muzzle_c[1] + 3 + g['jaw'] * 1.5, 4.5, 1.5 + g['jaw'] * 2)[0], 'mouth', outline=True)
        # horns first (behind the head): a thick curl back over the ear and down
        hb = (head_c[0] - 1, head_c[1] - 5)
        curl = smooth([hb, (hb[0] - 5, hb[1] - 10), (hb[0] - 16, hb[1] - 6), (hb[0] - 17, hb[1] + 6), (hb[0] - 9, hb[1] + 12), (hb[0] - 2, hb[1] + 8)], 24)
        union = np.zeros((H, W), bool)
        shapes = []
        for i, (x, y) in enumerate(curl):
            r = lerp(5.6, 1.6, i / (len(curl) - 1))
            sh = ellipsoid(x, y, r, r)
            shapes.append((sh, i))
            union |= sh[0]
        f.a[mc.dilate(union) & ~union] = p['ol']
        for sh, i in shapes:
            f.paint(sh, p.ramp('horn0', 'horn1', 'horn2', 'horn3') if (i // 3) % 2 == 0 else p.ramp('horn0', 'horn1', 'horn2'), outline=False, dither=.3)
        chain_paint(f, [neck, skull], p.ramp('face0', 'face1', 'face2', 'face3'), dither=.4)
        f.paint(jaw, p.ramp('face0', 'face1', 'face2'), outline=True, dither=.3)
        f.paint(muzzle, p.ramp('face0', 'face1', 'face2', 'face3'), outline=True, dither=.4)
        f.dots([(muzzle_c[0] + 4, muzzle_c[1] - 1), (muzzle_c[0] + 4, muzzle_c[1] + 1)], 'nostril')
        ear = polygon([(head_c[0] - 4, head_c[1] - 1), (head_c[0] - 11, head_c[1] + 2 + g['shake'] * 2), (head_c[0] - 4, head_c[1] + 4)])
        f.a[mc.dilate(ear) & ~ear] = p['ol']
        f.a[ear] = p['face2']
        eyes_on(f, g, head_c[0] + 3, head_c[1] - 2, 'eye', brow='face0', size=2.4)
        # lightning: from each horn tip to the other horn, to the ground in the attack
        tip = curl[-1]
        arc_to = (head_c[0] + 2, head_c[1] - 9)
        k = max(1, int(1 + 2 * (glow - .85)))
        for _ in range(k):
            pts = bolt_path(rng, tip, arc_to, 2.2, 5)
            for u, v in zip(pts, pts[1:]):
                f.line(u, v, 'bolt1', 1)
            f.dots(pts[1:-1], 'bolt3')
        if clip == 'attack' and n in (3, 4):
            pts = bolt_path(rng, (tip[0] + 2, tip[1]), (tip[0] - 4 + 14 * (n - 3), AY - 2), 3, 7)
            for u, v in zip(pts, pts[1:]):
                f.line(u, v, 'bolt2', 1)

    return draw_quad(f, p, g, dict(
        height=31, leg=(11, 11), thick=1.05, barrel=(21, 13.5), rump=(15, 13), hump=(11, -5, 12, 11),
        body=['wool0', 'wool1', 'wool2', 'wool3', 'wool4'], belly=['bel0', 'bel1', 'bel2'], far=['far0', 'far1', 'far2'],
        near=['face0', 'face1', 'face2', 'face3'], hoof=['hoof', 'hoof2'], tail=tail, deco_back=deco_back, deco_front=lambda c: None, head=head))


# ----------------------------------------------------------------------------------------------
# Oakhorn: the grove's guardian stag. Antlers like an oak in autumn, moss on the shoulders, a golden thread through the heart.
# ----------------------------------------------------------------------------------------------
OAKHORN = Palette({
    'fur0': '#2a1810', 'fur1': '#47281a', 'fur2': '#6e4026', 'fur3': '#975a34', 'fur4': '#be8250', 'fur5': '#dcae7a',
    'far0': '#1c110b', 'far1': '#30190f', 'far2': '#4a2a18', 'bel0': '#a07a58', 'bel1': '#c8a27a', 'bel2': '#ead2ac',
    'moss0': '#25401f', 'moss1': '#3f6a2c', 'moss2': '#6a9a3e', 'moss3': '#a2cc5a', 'ant0': '#3a2a1c', 'ant1': '#5e4630',
    'ant2': '#8a6c48', 'ant3': '#b79868', 'leaf0': '#7a1c12', 'leaf1': '#c0381a', 'leaf2': '#e87a1e', 'leaf3': '#f4b830',
    'leaf4': '#ffe27a', 'gold0': '#b8860b', 'gold1': '#ffc83a', 'gold2': '#fff0a0', 'eye': '#ffe066', 'socket': '#150b06',
    'hoof': '#1a120c', 'hoof2': '#35261a', 'nostril': '#1e0f08', 'mouth': '#3b1218', 'muzzle0': '#5c3a26', 'muzzle1': '#8a6446',
    'muzzle2': '#b89068',
})


def oakhorn(clip, n):
    f = Frame(OAKHORN)
    p = OAKHORN
    g = quad_gait(clip, n)
    rng = rng_for('oakhorn', clip, n)
    glow = g['glow']

    def tail(c):
        tb = c.at(-19, -5)
        tip = (tb[0] - 5, tb[1] + 2 - g['tail'] * 4)
        f.paint(capsule(tb, tip, 3.2, 1.6), p.ramp('fur1', 'fur2', 'bel1', 'bel2'), dither=.3)

    def deco_back(c):
        for (ox, oy, rx, ry, a) in [(8, -9, 7, 3.4, .1), (-2, -10, 6, 3, 0), (-11, -8, 5, 3, -.1)]:
            m = ellipsoid(*c.at(ox, oy), rx, ry, a + c.ang)
            f.paint(m, p.ramp('moss0', 'moss1', 'moss2', 'moss3'), outline=True, edge='ol', dither=.5)
        # the golden thread through the heart: in at the chest, out round the flank, pulsing
        ch = c.at(14, -1)
        pts = smooth([ch, c.at(8, 4), c.at(0, 2), c.at(-6, 6), c.at(-12, 2), c.at(-16, -2)], 20)
        for a, b in zip(pts, pts[1:]):
            f.line(a, b, 'gold0', 3)
        for a, b in zip(pts, pts[1:]):
            f.line(a, b, 'gold1' if glow < 1.2 else 'gold2', 1)
        f.flat(ellipsoid(ch[0], ch[1], 3.2 * glow, 3.2 * glow)[0], 'gold1', outline=True, edge='gold0')
        f.dots([ch], 'gold2')

    def head(c):
        lie = g['lie']
        hx0, hy0 = c.at(18, -8)
        head_c = (hx0 + 6 + g['hx'], hy0 - 4 + g['hy'] + lie * 8)
        ht = .45 + g['ht'] - lie * .4
        neck = capsule(c.at(13, -4), head_c, 7.5, 5.2)
        skull = ellipsoid(head_c[0], head_c[1], 7, 5.6, ht)
        mz = (head_c[0] + 9 * math.cos(ht), head_c[1] + 9 * math.sin(ht))
        muzzle = ellipsoid(mz[0], mz[1], 6.5, 3.6, ht)
        jaw = ellipsoid(mz[0] - 1, mz[1] + 3 + g['jaw'] * 3, 5.5, 1.8, ht + g['jaw'] * .3)
        if g['jaw'] > .1:
            f.flat(ellipsoid(mz[0], mz[1] + 2.5 + g['jaw'] * 1.5, 4.5, 1.2 + g['jaw'] * 2)[0], 'mouth', outline=True)
        # antlers: two main beams sweeping up and back with tines, then a crown of autumn leaves
        for beam, shade in ((1, 'back'), (0, 'front')):
            ox = head_c[0] - 2 - beam * 3
            base = (ox, head_c[1] - 4)
            main = smooth([base, (ox - 3, base[1] - 7), (ox + 1, base[1] - 13), (ox - 6 + beam * 2, base[1] - 18), (ox - 4 + beam * 6, base[1] - 23)], 18)
            tines = [(main[5], (main[5][0] + 9, main[5][1] - 6)), (main[9], (main[9][0] + 10, main[9][1] - 5)), (main[9], (main[9][0] - 9, main[9][1] - 5)),
                     (main[13], (main[13][0] + 9, main[13][1] - 5)), (main[13], (main[13][0] - 8, main[13][1] - 4)), (main[16], (main[16][0] + 4, main[16][1] - 6))]
            col = 'ant1' if beam else 'ant2'
            for a, b in zip(main, main[1:]):
                f.line(a, b, 'ol', 6)
            for a, b in tines:
                f.line(a, b, 'ol', 5)
            for a, b in zip(main, main[1:]):
                f.line(a, b, col, 4)
            for a, b in tines:
                f.line(a, b, col, 3)
            # leaf clusters on the tine tips
            if beam == 0:
                for (_, (tx, ty)), tone in zip(tines, ('leaf2', 'leaf1', 'leaf3', 'leaf2', 'leaf1', 'leaf3')):
                    for k in range(3):
                        lx, ly = tx + rng.uniform(-3, 3), ty + rng.uniform(-3, 2)
                        blob = ellipsoid(lx, ly, 2.6, 2.2)
                        f.paint(blob, p.ramp('leaf0', tone, 'leaf4'), outline=True, edge='leaf0', dither=.3)
        chain_paint(f, [neck, skull], p.ramp('fur0', 'fur1', 'fur2', 'fur3', 'fur4'), dither=.45)
        f.paint(jaw, p.ramp('fur1', 'muzzle1', 'muzzle2'), outline=True, dither=.3)
        f.paint(muzzle, p.ramp('muzzle0', 'muzzle1', 'muzzle2'), outline=True, dither=.4)
        f.dots([(mz[0] + 5, mz[1] - 1)], 'nostril')
        ear = polygon([(head_c[0] - 3, head_c[1] - 3), (head_c[0] - 10, head_c[1] - 6 - g['shake'] * 2), (head_c[0] - 2, head_c[1] + 1)])
        f.a[mc.dilate(ear) & ~ear] = p['ol']
        f.a[ear] = p['fur2']
        eyes_on(f, g, head_c[0] + 2, head_c[1] - 1, 'eye', brow='fur0', size=2.2)

    return draw_quad(f, p, g, dict(
        height=30, leg=(12, 12), thick=.9, gscale=.5, barrel=(19, 11.5), rump=(13, 11.5), hump=(10, -4, 10, 9.5), feet=[-10, 13, -4, 18],
        body=['fur0', 'fur1', 'fur2', 'fur3', 'fur4', 'fur5'], belly=['bel0', 'bel1', 'bel2'], far=['far0', 'far1', 'far2'],
        near=['fur0', 'fur1', 'fur2', 'fur3', 'fur4'], hoof=['hoof', 'hoof2'], tail=tail, deco_back=deco_back, deco_front=lambda c: None, head=head))


# ----------------------------------------------------------------------------------------------
# The two-legged rig used by the troll and the giant: hunched, facing right, long arms, a slam attack.
# ----------------------------------------------------------------------------------------------
def biped_gait(clip, n):
    d = dict(dx=0., lift=0., crouch=0., tilt=0., hx=0., hy=0., jaw=0., lie=0., eyes='open', glow=1., flash=False, fx=[0., 0.], fl=[0., 0.],
             arm_n=(5., 27.), arm_f=(-2., 27.), slam=0., sway=0.)
    if clip == 'idle':
        d['crouch'] = [0, .5, 1, .5, 0, .3][n]
        d['hy'] = [0, .4, .8, .4, 0, .2][n]
        d['arm_n'] = (5 + [0, .5, 1, .5, 0, -.3][n], 27 + [0, .6, 1, .6, 0, .3][n])
        d['arm_f'] = (-2 - [0, .5, 1, .5, 0, -.3][n], 27 + [0, .4, .8, .4, 0, .2][n])
        d['glow'] = [1, 1.05, 1.1, 1.05, 1, .95][n]
        d['eyes'] = 'blink' if n == 3 else 'open'
    elif clip == 'walk':
        d['lift'] = [0, 0, 3, 6, 4, 0, 0, 0][n]
        d['crouch'] = [1, 3, 0, 0, 0, 3, 2, 1][n]
        d['tilt'] = [.02, .06, -.04, -.08, -.02, .06, .03, 0][n]
        d['fx'] = [[0, 0], [0, 0], [-3, 4], [-6, 7], [-3, 4], [0, 0], [0, 0], [0, 0]][n]
        d['fl'] = [[0, 0], [0, 0], [3, 3], [5, 5], [3, 3], [0, 0], [0, 0], [0, 0]][n]
        d['arm_n'] = [(5, 27), (6, 26), (9, 22), (11, 20), (9, 22), (5, 27), (5, 27), (5, 27)][n]
        d['arm_f'] = [(-2, 27), (-3, 26), (-8, 22), (-10, 20), (-8, 22), (-2, 27), (-2, 27), (-2, 27)][n]
        d['hy'] = [0, 1, -1, -2, -1, 1, 1, 0][n]
    elif clip == 'attack':
        # windup: both fists up and back; lunge: they come down in front; recovery: a heavy settle
        d['dx'] = [-1, -3, -4, 3, 6, 5, 2, 0][n]
        d['crouch'] = [1, 2, 3, 6, 5, 3, 1, 0][n]
        d['tilt'] = [-.06, -.13, -.2, .24, .34, .22, .08, 0][n]
        d['arm_n'] = [(2, -8), (-2, -22), (-4, -30), (15, 19), (22, 25), (18, 25), (11, 26), (6, 27)][n]
        d['arm_f'] = [(-6, 10), (-9, -14), (-10, -26), (9, 21), (17, 26), (14, 26), (7, 27), (-1, 27)][n]
        d['hx'] = [0, -1, -2, 3, 5, 3, 1, 0][n]
        d['hy'] = [0, -1, -2, 3, 4, 2, 1, 0][n]
        d['jaw'] = [0, .2, .6, 1, .8, .3, 0, 0][n]
        d['eyes'] = 'angry'
        d['slam'] = [0, 0, 0, .4, 1, .7, .3, 0][n]
        d['glow'] = [1.1, 1.25, 1.4, 1.5, 1.4, 1.1, 1, 1][n]
    elif clip == 'hurt':
        d['dx'] = [-4, -3, -1, 0][n]
        d['crouch'] = [3, 2, 1, 0][n]
        d['tilt'] = [-.16, -.08, -.02, 0][n]
        d['hy'] = [-2, -1, 0, 0][n]
        d['jaw'] = [.7, .4, 0, 0][n]
        d['arm_n'] = [(2, 16), (4, 22), (5, 26), (5, 27)][n]
        d['arm_f'] = [(-6, 16), (-4, 22), (-3, 26), (-2, 27)][n]
        d['flash'] = n == 0
        d['eyes'] = 'hurt' if n < 3 else 'angry'
        d['glow'] = [1.5, 1.3, 1.1, 1][n]
    elif clip == 'die':
        d['flash'] = n == 0
        d['eyes'] = 'dead'
        d['dx'] = [0, -3, -5, -7, -8, -9, -9, -9][n]
        d['lie'] = [0, 0, .12, .35, .65, .92, 1, 1][n]
        d['crouch'] = [0, 2, 4, 5, 4, 3, 2, 2][n]
        d['tilt'] = [0, -.1, -.15, -.1, 0, 0, 0, 0][n]
        d['arm_n'] = [(5, 27), (3, 20), (0, 14), (-4, 12), (-6, 14), (-4, 18), (-3, 22), (-3, 22)][n]
        d['arm_f'] = [(-2, 27), (-5, 20), (-8, 14), (-9, 12), (-10, 14), (-8, 18), (-6, 22), (-6, 22)][n]
        d['jaw'] = [.5, .9, .6, .4, .3, .3, .3, .3][n]
        d['glow'] = [1.5, 1.2, 1, .8, .55, .35, .2, .1][n]
    return d


def draw_biped(f, p, g, S):
    """S: dims (leg, arm, torso, pelvis, head), ramps and callbacks `back`, `deco_torso`, `head`, `hand`, `after`."""
    lie = g['lie']
    theta = -lie * 1.5
    pivot_x = 44 + g['dx'] + 4
    leg_h = S['leg_h']

    def T(x, y):
        """A figure-space point -> canvas, after the fall (a rotation about the heels)."""
        dx, dy = x - pivot_x, y - AY
        c, s = math.cos(theta), math.sin(theta)
        return pivot_x + dx * c - dy * s, AY + dx * s + dy * c

    bx = 44 + g['dx']
    by = AY - leg_h - g['lift'] + g['crouch']
    tilt = g['tilt']
    ang = tilt + theta

    def at(dx, dy, base=(None, None)):
        x, y = rotate(dx, dy, -tilt)
        return T(bx + x, by + y)

    ctx = Ctx(f, p, g, bx, by, tilt, ang)
    ctx.at = at
    ctx.T = T
    ctx.theta = theta
    ctx.S = S
    ground = AY - 1
    feet = [(bx + 8 + g['fx'][0], ground - g['fl'][0]), (bx - 7 + g['fx'][1], ground - g['fl'][1])]    # near, far
    hip_near, hip_far = at(3, 4), at(-4, 4)
    l1, l2 = S['leg']
    t = S.get('thick', 1.)
    S['back'](ctx)
    # far arm and leg
    sh = S['shoulder']
    sh_far, sh_near = at(sh[0] - 4, sh[1] + 1), at(sh[0] + 3, sh[1] + 2)
    aL1, aL2 = S['arm']

    def arm(shoulder, rel, ramp, flip=1):
        goal = (shoulder[0] + rel[0] * S.get('reach', 1.), shoulder[1] + rel[1] * S.get('reach', 1.))
        if lie:
            goal = T(goal[0], goal[1])
        elbow = ik(shoulder, goal, aL1, aL2, flip)
        f.paint(capsule(shoulder, elbow, S['arm_r'][0], S['arm_r'][1]), ramp, dither=.4)
        f.paint(capsule(elbow, goal, S['arm_r'][1], S['arm_r'][2]), ramp, dither=.4)
        return goal

    far_ramp = p.ramp(*S['far'])
    hand_far = arm(sh_far, g['arm_f'], far_ramp)
    foot_far = T(*feet[1])
    knee_far = ik(hip_far, foot_far, l1, l2, -1)
    f.paint(capsule(hip_far, knee_far, 6.4 * t, 4.4 * t), far_ramp, dither=.35)
    f.paint(capsule(knee_far, foot_far, 4.4 * t, 3.4 * t), far_ramp, dither=.35)
    f.paint(ellipsoid(foot_far[0] + 2, foot_far[1] - 1, 5.2 * t, 2.8), far_ramp, dither=.2)
    # torso
    pel = ellipsoid(*at(0, 2), S['pelvis'][0], S['pelvis'][1], ang)
    tor = ellipsoid(*at(S['torso_at'][0], S['torso_at'][1]), S['torso'][0], S['torso'][1], ang + S.get('torso_tilt', .2))
    union = pel[0] | tor[0]
    f.a[mc.dilate(union) & ~union] = p['ol']
    f.paint(pel, p.ramp(*S['body']), outline=False, dither=.5)
    f.paint(tor, p.ramp(*S['body']), outline=False, dither=.5)
    S['deco_torso'](ctx)
    # near leg
    foot_n = T(*feet[0])
    knee_n = ik(hip_near, foot_n, l1, l2, -1)
    ramp = p.ramp(*S['near'])
    f.paint(capsule(hip_near, knee_n, 7 * t, 4.8 * t), ramp, dither=.35)
    f.paint(capsule(knee_n, foot_n, 4.8 * t, 3.6 * t), ramp, dither=.35)
    f.paint(ellipsoid(foot_n[0] + 2, foot_n[1] - 1, 5.6 * t, 3), ramp, dither=.2)
    S['head'](ctx)
    hand_near = arm(sh_near, g['arm_n'], ramp)
    S['hand'](ctx, hand_near, hand_far)
    S['after'](ctx, hand_near, hand_far)
    if g['flash']:
        f.whiten()
    return fit(f.a)


def dust(f, rng, x, amount, color='dust'):
    for k in range(int(10 * amount)):
        a = rng.uniform(0, math.pi)
        d = rng.uniform(4, 6 + 16 * amount)
        f.dots([(x + math.cos(a) * d * (1 if k % 2 else -1), AY - 1 - math.sin(a) * d * .4)], color)


# ----------------------------------------------------------------------------------------------
# Mosshide Troll: a hunched brute the colour of a wet boulder, moss and mushrooms on its back and a sapling growing from its
# shoulder. It raises both fists and slams the ground.
# ----------------------------------------------------------------------------------------------
TROLL = Palette({
    'sk0': '#1c2620', 'sk1': '#2f4236', 'sk2': '#48634e', 'sk3': '#688766', 'sk4': '#92ae82', 'sk5': '#bfd4a8',
    'far0': '#141c17', 'far1': '#223028', 'far2': '#344a3b', 'bel0': '#656a54', 'bel1': '#8a9072', 'bel2': '#b2b896',
    'ms0': '#1b381a', 'ms1': '#2e6424', 'ms2': '#56a038', 'ms3': '#98d24e', 'bk0': '#281c13', 'bk1': '#483221', 'bk2': '#6c4c33',
    'tusk': '#d9ccaa', 'tusk2': '#f4ecd2', 'eye': '#ffe14a', 'socket': '#0c120d', 'mouth': '#3c1a1e', 'cap0': '#7a1620',
    'cap1': '#c42a38', 'cap2': '#f0603c', 'dot': '#f7f0dc', 'dust': '#a89878', 'nail': '#cfc7a8', 'wart': '#7e9c62',
})


def troll(clip, n):
    f = Frame(TROLL)
    p = TROLL
    rng = rng_for('troll', clip, n)
    g = biped_gait(clip, n)
    HEAD_AT = (14, -27)

    def back(c):
        # a sapling growing from the far shoulder
        base = c.at(-6, -19)
        top = (base[0] - 3, base[1] - 17)
        f.line(base, top, 'ol', 4)
        f.line(base, top, 'bk1', 2)
        for (ox, oy, r) in [(-3, -2, 5), (3, -7, 4.5), (-8, -9, 4.5), (0, -14, 4)]:
            leaf = ellipsoid(top[0] + ox, top[1] + oy + 4, r, r * .8)
            f.paint(leaf, p.ramp('ms0', 'ms1', 'ms2', 'ms3'), outline=True, edge='ol', dither=.4)

    def deco_torso(c):
        for (ox, oy, rx, ry) in [(-3, -14, 8, 4), (4, -17, 7, 3.4), (-9, -8, 5, 4)]:
            m = ellipsoid(*c.at(ox, oy), rx, ry, c.ang)
            f.paint(m, p.ramp('ms0', 'ms1', 'ms2', 'ms3'), outline=True, edge='ol', dither=.5)
        for (ox, oy, r) in [(-10, -12, 3), (-5, -19, 3.4)]:
            x, y = c.at(ox, oy)
            f.line((x, y), (x + 1, y - 3), 'bel2', 2)
            f.flat(ellipsoid(x + 1, y - 4, r, r * .7)[0], 'cap1', outline=True)
            f.dots([(x - 1, y - 5), (x + 2, y - 4)], 'dot')
        # belly and a ragged hide loincloth
        bel = ellipsoid(*c.at(7, 5), 9, 10, c.ang)
        f.paint(bel, p.ramp('bel0', 'bel1', 'bel2'), outline=False, dither=.4)
        x0, y0 = c.at(-2, 7)
        cloth = polygon([(x0 - 9, y0), (x0 + 9, y0 + 1), (x0 + 7, y0 + 7), (x0 + 3, y0 + 5), (x0, y0 + 8), (x0 - 4, y0 + 5), (x0 - 8, y0 + 7)])
        f.a[mc.dilate(cloth) & ~cloth] = p['ol']
        f.a[cloth] = p['bk1']
        f.line((x0 - 8, y0 + 2), (x0 + 8, y0 + 3), 'bk0', 1)

    def head(c):
        hx, hy = c.at(HEAD_AT[0], HEAD_AT[1])
        hx += g['hx']
        hy += g['hy'] + g['lie'] * 2
        skull = ellipsoid(hx, hy, 9.5, 8.2, c.ang * .5)
        jaw = ellipsoid(hx + 3, hy + 6 + g['jaw'] * 3, 8, 4, c.ang * .3)
        neck = capsule(c.at(HEAD_AT[0] - 6, HEAD_AT[1] + 6), (hx, hy), 7, 6)
        if g['jaw'] > .1:
            f.flat(ellipsoid(hx + 4, hy + 6 + g['jaw'] * 2, 6.5, 1.5 + g['jaw'] * 2)[0], 'mouth', outline=True)
        # tusks
        for k, tx in enumerate((hx + 1, hx + 8)):
            f.line((tx, hy + 5 + g['jaw'] * 2), (tx + 1, hy - 3 + g['jaw']), 'ol', 4)
            f.line((tx, hy + 5 + g['jaw'] * 2), (tx + 1, hy - 3 + g['jaw']), 'tusk2' if k else 'tusk', 2)
        chain_paint(f, [neck, skull], p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'), dither=.5)
        f.paint(jaw, p.ramp('sk0', 'sk1', 'sk2', 'sk3'), outline=True, dither=.4)
        f.dots([(hx + 9, hy + 1), (hx + 8, hy + 3)], 'wart')
        # ear and a heavy brow
        ear = polygon([(hx - 5, hy - 3), (hx - 13, hy - 8 - g['sway']), (hx - 6, hy + 2)])
        f.a[mc.dilate(ear) & ~ear] = p['ol']
        f.a[ear] = p['sk2']
        brow = ellipsoid(hx + 4, hy - 3.5, 5.2, 2.2, -.15)
        f.paint(brow, p.ramp('sk0', 'sk1', 'sk2'), outline=False, dither=.2)
        eyes_on(f, g, hx + 5, hy - 1, 'eye', brow=None, size=2.3)

    def hand(c, near, far):
        for (hx, hy), ramp in ((far, p.ramp('far0', 'far1', 'far2')), (near, p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4'))):
            fist = ellipsoid(hx, hy, 6.4, 5.6)
            f.paint(fist, ramp, dither=.4)
            f.dots([(hx + 3, hy + 3), (hx + 5, hy + 1)], 'nail')

    def after(c, near, far):
        if g['slam'] > 0:
            x = max(near[0], far[0])
            dust(f, rng, x, g['slam'])
            f.dots([(x + k * 3, AY - 1) for k in range(-4, 5)], 'dust')

    return draw_biped(f, p, g, dict(
        leg_h=27, leg=(14.5, 14.5), thick=1.1, arm=(16, 16), arm_r=(5.6, 4.6, 3.8), shoulder=(8, -19), torso=(15, 17), torso_at=(3, -13), torso_tilt=.25,
        pelvis=(11, 8), head_at=(14, -27),
        body=['sk0', 'sk1', 'sk2', 'sk3', 'sk4', 'sk5'], far=['far0', 'far1', 'far2'], near=['sk0', 'sk1', 'sk2', 'sk3', 'sk4'],
        back=back, deco_torso=deco_torso, head=head, hand=hand, after=after))


# ----------------------------------------------------------------------------------------------
# Hrungnir: a granite storm giant, cracked with lightning, a braided beard that crackles and a crown of stone spikes.
# ----------------------------------------------------------------------------------------------
HRUNGNIR = Palette({
    'gr0': '#1b2030', 'gr1': '#2f3850', 'gr2': '#4a5676', 'gr3': '#6c7ba2', 'gr4': '#98a9ce', 'gr5': '#c6d3ec',
    'far0': '#131725', 'far1': '#222a3d', 'far2': '#343f58', 'bel0': '#58648a', 'bel1': '#7f8db3', 'bel2': '#a9b8d8',
    'zap0': '#2a73d6', 'zap1': '#5fc4ff', 'zap2': '#b8f0ff', 'zap3': '#f2fdff', 'bd0': '#7c879f', 'bd1': '#b0bcd2', 'bd2': '#e6edf7',
    'fur0': '#33261c', 'fur1': '#573f2a', 'fur2': '#7f6040', 'gold0': '#a8760a', 'gold1': '#f4bc34', 'eye': '#c2f4ff', 'socket': '#080b14',
    'mouth': '#2a1620', 'dust': '#8a93ae', 'nail': '#d6dcea', 'spike0': '#252b3f', 'spike1': '#444f70',
})


def hrungnir(clip, n):
    f = Frame(HRUNGNIR)
    p = HRUNGNIR
    rng = rng_for('hrungnir', clip, n)
    g = biped_gait(clip, n)
    glow = g['glow']

    def zap_line(a, b, jag=2.2, steps=4):
        pts = bolt_path(rng, a, b, jag, steps)
        for u, v in zip(pts, pts[1:]):
            f.line(u, v, 'zap1' if glow < 1.3 else 'zap2', 1)

    def back(c):
        # a stormcloud mantle of stone spikes on the back of the head
        hx, hy = c.at(S_HEAD[0], S_HEAD[1])
        for k in range(5):
            a = -2.6 + k * .42
            tip = (hx + math.cos(a) * 17, hy + math.sin(a) * 15)
            tri = polygon([(hx + math.cos(a - .35) * 7, hy + math.sin(a - .35) * 7), tip, (hx + math.cos(a + .35) * 7, hy + math.sin(a + .35) * 7)])
            f.a[mc.dilate(tri) & ~tri] = p['ol']
            f.a[tri] = p['spike1' if k % 2 else 'spike0']

    def deco_torso(c):
        # fur kilt with a gold belt, lightning cracks across the chest
        x0, y0 = c.at(0, 6)
        kilt = polygon([(x0 - 11, y0 - 1), (x0 + 11, y0), (x0 + 9, y0 + 8), (x0 + 4, y0 + 6), (x0, y0 + 9), (x0 - 5, y0 + 6), (x0 - 10, y0 + 8)])
        f.a[mc.dilate(kilt) & ~kilt] = p['ol']
        f.a[kilt] = p['fur1']
        f.line((x0 - 10, y0 + 2), (x0 + 10, y0 + 3), 'gold1', 2)
        f.dots([(x0, y0 + 2)], 'zap3')
        a = c.at(1, -14)
        pts = [a, c.at(5, -8), c.at(2, -3), c.at(7, 3)]
        for u, v in zip(pts, pts[1:]):
            f.line(u, v, 'zap0', 2)
        for u, v in zip(pts, pts[1:]):
            f.line(u, v, 'zap1' if glow < 1.2 else 'zap3', 1)
        for (ox, oy) in [(-8, -10), (11, -5)]:
            x, y = c.at(ox, oy)
            f.line((x, y), (x + 3, y + 4), 'zap1', 1)

    def head(c):
        hx, hy = c.at(S_HEAD[0], S_HEAD[1])
        hx += g['hx']
        hy += g['hy'] + g['lie'] * 2
        skull = ellipsoid(hx, hy, 8.6, 8, c.ang * .5)
        neck = capsule(c.at(S_HEAD[0] - 6, S_HEAD[1] + 6), (hx, hy), 7.5, 6.5)
        # the beard: a long braided slab hanging from the chin, tips crackling
        by0 = hy + 5
        beard = polygon([(hx - 2, by0), (hx + 9, by0), (hx + 8, by0 + 14 + g['jaw'] * 2), (hx + 4, by0 + 18 + g['jaw'] * 2), (hx - 1, by0 + 13)])
        f.a[mc.dilate(beard) & ~beard] = p['ol']
        f.a[beard] = p['bd1']
        for k in range(4):
            f.line((hx + k * 2, by0 + 2), (hx + k * 2 + 1, by0 + 14), 'bd0', 1)
        f.dots([(hx + 4, by0 + 17 + g['jaw'] * 2)], 'zap3')
        if g['jaw'] > .1:
            f.flat(ellipsoid(hx + 4, hy + 6 + g['jaw'] * 1.5, 5, 1 + g['jaw'] * 1.6)[0], 'mouth', outline=True)
        chain_paint(f, [neck, skull], p.ramp('gr0', 'gr1', 'gr2', 'gr3', 'gr4'), dither=.5)
        f.line((hx + 1, hy - 7), (hx + 3, hy - 3), 'zap1', 1)
        brow = ellipsoid(hx + 4, hy - 3.2, 5.2, 2.2, -.15)
        f.paint(brow, p.ramp('gr0', 'gr1', 'gr2'), outline=False, dither=.2)
        eyes_on(f, g, hx + 5, hy - 1, 'eye', brow=None, size=2.2)
        # moustache braids over the beard top
        f.line((hx + 2, hy + 5), (hx + 9, hy + 7), 'bd2', 2)

    def hand(c, near, far):
        for (hx, hy), ramp in ((far, p.ramp('far0', 'far1', 'far2')), (near, p.ramp('gr0', 'gr1', 'gr2', 'gr3', 'gr4'))):
            f.paint(ellipsoid(hx, hy, 6.6, 6), ramp, dither=.4)
            f.dots([(hx + 3, hy + 3), (hx + 5, hy + 1)], 'nail')

    def after(c, near, far):
        if clip == 'attack' and 2 <= n <= 5:
            for hnd in (near, far):
                for _ in range(2):
                    zap_line(hnd, (hnd[0] + rng.uniform(-9, 11), hnd[1] + rng.uniform(-10, 8)))
        elif glow > 1.3:
            zap_line(near, (near[0] + 6, near[1] - 6))
        if g['slam'] > 0:
            x = max(near[0], far[0])
            dust(f, rng, x, g['slam'])
            zap_line((x, AY - 1), (x + 12, AY - 2), 1.2, 4)
            zap_line((x, AY - 1), (x - 12, AY - 2), 1.2, 4)

    S_HEAD = (13, -30)
    return draw_biped(f, p, g, dict(
        leg_h=29, leg=(15.5, 15.5), thick=1.05, arm=(16.5, 16.5), arm_r=(5.4, 4.6, 3.9), shoulder=(8, -20), torso=(14.5, 18), torso_at=(3, -14), torso_tilt=.18,
        pelvis=(11, 8), head_at=S_HEAD, reach=1.0,
        body=['gr0', 'gr1', 'gr2', 'gr3', 'gr4', 'gr5'], far=['far0', 'far1', 'far2'], near=['gr0', 'gr1', 'gr2', 'gr3', 'gr4'],
        back=back, deco_torso=deco_torso, head=head, hand=hand, after=after))


# ----------------------------------------------------------------------------------------------
# Gallowcrow: a raven the size of a dog that hovers on ragged wings, a scrap of the Hanged King's rope on one claw.
# It draws its head back and shoots feathers.
# ----------------------------------------------------------------------------------------------
CROW = Palette({
    'pl0': '#0d0c14', 'pl1': '#1a1a2b', 'pl2': '#2c2d47', 'pl3': '#444768', 'pl4': '#6a6f9a', 'sheen': '#6f5aa8', 'sheen2': '#9a84d6',
    'far0': '#08070d', 'far1': '#12121d', 'far2': '#202136', 'beak0': '#4a3a2a', 'beak1': '#8a7050', 'beak2': '#c4aa78',
    'eye': '#ff4a3a', 'eye2': '#ffd0b0', 'socket': '#050408', 'claw': '#cfc4a8', 'leg': '#3a2e28', 'rope0': '#5a4630', 'rope1': '#a88a5a',
    'rope2': '#d8bc86', 'mouth': '#3a1018', 'dart': '#c9d2e8', 'dart2': '#f2f6ff',
})


def crow(clip, n):
    f = Frame(CROW)
    p = CROW
    rng = rng_for('crow', clip, n)
    flap = [-1.9, -1.3, -.6, 0., -.6, -1.3][n % 6] if clip == 'idle' else 0.
    cx, cy = 44., 52.
    tilt, head_dx, head_dy, beak, wing, eyes, flash, glow, fall = .25, 0., 0., 0., flap, 'open', False, 1., 0.
    spread = .24
    if clip == 'walk':
        cy += [0, 1, -3, -6, -3, 1, 1, 0][n]
        wing = [-1.4, -.6, -2.1, -1.8, -.4, .1, -.6, -1.2][n]
        tilt = [.25, .3, .1, 0., .1, .3, .3, .25][n]
    elif clip == 'attack':
        cx += [-2, -4, -5, 4, 7, 5, 1, 0][n]
        wing = [-1.9, -2.3, -2.5, -.2, .3, -.6, -1.3, -1.7][n]
        spread = [.24, .22, .2, .3, .32, .28, .24, .24][n]
        head_dx = [-1, -3, -4, 4, 6, 3, 1, 0][n]
        head_dy = [0, 1, 2, 1, 2, 1, 0, 0][n]
        beak = [0, 0, .2, 1, .8, .3, 0, 0][n]
        tilt = [.3, .45, .55, .05, -.1, .1, .2, .25][n]
        eyes = 'angry'
        glow = 1.3
    elif clip == 'hurt':
        cx += [-5, -3, -1, 0][n]
        wing = [-2.3, -1.9, -1.3, -1.][n]
        tilt = [.6, .45, .3, .25][n]
        head_dx = [-3, -2, -1, 0][n]
        beak = [.8, .5, .2, 0][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead'
        fall = [0, 0, .2, .5, .8, 1, 1, 1][n]
        wing = [-1.4, -2.4, -2.6, -2.2, -1.8, -1.2, -.6, -.4][n]
        tilt = [.3, .6, 1., 1.3, 1.5, 1.57, 1.57, 1.57][n]
        beak = [.5, .9, .8, .5, .4, .4, .4, .4][n]
        cx += [0, -2, -4, -5, -6, -6, -6, -6][n]
    cy += fall * (AY - 13 - cy) + (math.sin(n * 1.0) * 1.2 if clip == 'idle' else 0)
    if clip == 'idle':
        cy += [0, -1, -2, -1, 0, 1][n]
    lying = fall >= 1

    def at(dx, dy):
        x, y = rotate(dx, dy, -tilt * (.2 if not fall else 0))
        return cx + x, cy + y

    # far wing, legs, tail, body, near wing, head: back to front
    def wing_draw(shoulder, ramp, length, scale=1.):
        sx, sy = shoulder
        base_angle = wing
        feathers = []
        for k in range(8):
            a = base_angle + (k - 3.5) * spread * scale
            ln = length * (.62 + .38 * math.sin((k + 1) / 9 * math.pi))
            tip = (sx + math.cos(a + math.pi) * ln * (-1), sy + math.sin(a + math.pi) * ln * (-1))
            feathers.append(tip)
        # a wing sweeps back (to the left) from the shoulder: angle 0 = straight back, negative = raised
        feathers = [(sx - math.cos(base_angle + (k - 3.5) * spread * scale) * ln, sy + math.sin(base_angle + (k - 3.5) * spread * scale) * ln)
                    for k, ln in [(k, length * (.62 + .38 * math.sin((k + 1) / 9 * math.pi))) for k in range(8)]]
        union = np.zeros((H, W), bool)
        shapes = [capsule((sx, sy), tip, 3.6, 1.2) for tip in feathers]
        for sh in shapes:
            union |= sh[0]
        f.a[mc.dilate(union) & ~union] = p['ol']
        for k, sh in enumerate(shapes):
            f.paint(sh, ramp, outline=False, dither=.3)
        cov = ellipsoid(sx - 4, sy, 7, 4.5, base_angle * .5)
        f.paint(cov, ramp, outline=True, dither=.4)

    if not lying:
        wing_draw(at(-2, -7), p.ramp('far0', 'far1', 'far2'), 25, 1.0)
        # tail: three long feathers
        tb = at(-10, 1)
        for k, a in enumerate((.35, .1, -.15)):
            tip = (tb[0] - 14 * math.cos(a + tilt * .5) - 3, tb[1] + 14 * math.sin(a + tilt * .5) + 8)
            f.line(tb, tip, 'ol', 5)
        for k, a in enumerate((.35, .1, -.15)):
            tip = (tb[0] - 14 * math.cos(a + tilt * .5) - 3, tb[1] + 14 * math.sin(a + tilt * .5) + 8)
            f.line(tb, tip, 'pl1' if k % 2 else 'pl2', 3)
        # legs and claws, with the rope
        for lx, near in ((at(1, 6), False), (at(5, 6), True)):
            foot = (lx[0] + 3 + (2 if beak > .5 else 0), lx[1] + 11)
            f.line(lx, foot, 'ol', 4)
            f.line(lx, foot, 'leg', 2)
            for d in (-2, 0, 2):
                f.line(foot, (foot[0] + 3 + d * .5, foot[1] + 3 + abs(d) * .2), 'claw', 1)
        foot = (at(5, 6)[0] + 3, at(5, 6)[1] + 11)
        sway = math.sin(n * .9) * 1.5
        rope = smooth([(foot[0], foot[1]), (foot[0] + 1 + sway, foot[1] + 5), (foot[0] - 1 + sway, foot[1] + 10), (foot[0] + 2 + sway, foot[1] + 14)], 8)
        for a2, b2 in zip(rope, rope[1:]):
            f.line(a2, b2, 'ol', 3)
        for k, (a2, b2) in enumerate(zip(rope, rope[1:])):
            f.line(a2, b2, 'rope1' if k % 2 else 'rope2', 1)
        f.flat(ellipsoid(rope[-1][0], rope[-1][1] + 1, 2.4, 2.4)[0], 'rope0', outline=True)
    body = ellipsoid(*at(0, 0), 13.5, 9, .3 + (tilt - .25) * .5 if not fall else tilt)
    f.paint(body, p.ramp('pl0', 'pl1', 'pl2', 'pl3', 'pl4'), dither=.5)
    # an iridescent sheen along the back
    sheen = ellipsoid(*at(-1, -4), 9, 3, .2)
    f.paint((sheen[0] & body[0], sheen[1] * .6), p.ramp('pl2', 'sheen', 'sheen2'), outline=False, dither=.5)
    # a ruff of ragged neck feathers
    for k in range(5):
        a = .5 + k * .5
        x0, y0 = at(8, -2)
        tri = polygon([(x0 + math.cos(a) * 4, y0 - math.sin(a) * 4), (x0 + math.cos(a + .15) * 10 - 2, y0 - math.sin(a + .15) * 10 + 1), (x0 + math.cos(a + .5) * 4, y0 - math.sin(a + .5) * 4)])
        f.a[mc.dilate(tri) & ~tri] = p['ol']
        f.a[tri] = p['pl1' if k % 2 else 'pl2']
    # head and beak
    hxy = at(12 + head_dx, -7 + head_dy)
    neck = capsule(at(7, -3), hxy, 6.5, 5.6)
    skull = ellipsoid(hxy[0], hxy[1], 6.6, 6.0, .2)
    chain_paint(f, [neck, skull], p.ramp('pl0', 'pl1', 'pl2', 'pl3'), dither=.4)
    bx0, by0 = hxy[0] + 4, hxy[1] - 1
    upper = polygon([(bx0, by0 - 3), (bx0 + 11, by0 + 1 - beak * 1.5), (bx0 + 12, by0 + 3 - beak * 1.5), (bx0 + 3, by0 + 2 - beak)])
    lower = polygon([(bx0 + 2, by0 + 3 + beak * 2), (bx0 + 9, by0 + 4 + beak * 5), (bx0 + 3, by0 + 5 + beak * 3)])
    if beak > .1:
        f.flat(polygon([(bx0 + 2, by0 + 1), (bx0 + 9, by0 + 3 + beak), (bx0 + 3, by0 + 5 + beak * 3)]), 'mouth')
    f.a[mc.dilate(lower) & ~lower] = p['ol']
    f.a[lower] = p['beak0']
    f.a[mc.dilate(upper) & ~upper] = p['ol']
    f.paint((upper, gradient(upper, bx0, by0 - 3, bx0 + 8, by0 + 4)[1]), p.ramp('beak0', 'beak1', 'beak2'), outline=False, dither=.3)
    f.dots([(bx0 + 10, by0 + 2 - beak)], 'beak0')
    ex, ey = hxy[0] + 2, hxy[1] - 2
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif n == 3 and clip == 'idle':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex, ey, 2.4, 2.2)[0], 'socket')
        f.dots([(ex + 1, ey), (ex, ey - 1)], 'eye')
    if not lying:
        wing_draw(at(-1, -8), p.ramp('pl0', 'pl1', 'pl2', 'pl3', 'pl4'), 27, 1.05)
    else:
        # dead: wings spread flat on the ground either side
        for sgn, ramp in ((-1, p.ramp('far0', 'far1', 'far2')), (1, p.ramp('pl0', 'pl1', 'pl2', 'pl3'))):
            for k in range(7):
                tip = (cx + sgn * (6 + k * 3.6) - 2, AY - 3 - k * .2 + abs(k - 3) * .3)
                f.line((cx - 2, AY - 9), tip, 'ol', 4)
            for k in range(7):
                tip = (cx + sgn * (6 + k * 3.6) - 2, AY - 3 - k * .2 + abs(k - 3) * .3)
                f.line((cx - 2, AY - 9), tip, 'pl1' if k % 2 else 'pl2', 2)
    if clip == 'attack' and n in (3, 4):
        for k in range(2):
            x0 = hxy[0] + 13 + (n - 3) * 7 + k * 3
            y0 = hxy[1] + 1 + (k - .5) * 5
            f.line((x0, y0), (x0 + 6, y0 + (k - .5) * 2), 'dart', 1)
            f.dots([(x0 + 6, y0 + (k - .5) * 2)], 'dart2')
    if flash:
        f.whiten()
    return fit(f.a, floor=AY + 2)


# ----------------------------------------------------------------------------------------------
# Wyrdweaver: a hooded spinner of fate with golden thread between her hands. She pulls it taut and lets three strands fly.
# ----------------------------------------------------------------------------------------------
WEAVER = Palette({
    'rb0': '#150f28', 'rb1': '#271b45', 'rb2': '#3d2b6e', 'rb3': '#5a41a0', 'rb4': '#8068cc', 'gd0': '#8a6a14', 'gd1': '#e0b030',
    'gd2': '#fff0a0', 'sk1': '#5c4c62', 'sk2': '#8c7c92', 'sk3': '#bcaabf', 'void': '#06030c', 'eye': '#ffdc5a', 'th0': '#c88a18',
    'th1': '#ffd25a', 'th2': '#fff4c0', 'wd0': '#33241a', 'wd1': '#6a4a2e', 'orb': '#ffe27a', 'socket': '#0a0614', 'far0': '#0e0a1c',
    'far1': '#1c1334', 'far2': '#2e2150', 'mouth': '#2a1020',
})


def weaver(clip, n):
    f = Frame(WEAVER)
    p = WEAVER
    rng = rng_for('weaver', clip, n)
    hover, lean, sink, hand_n, hand_f, eyes, flash, glow, spread, strands, hood_dy = 5., 0., 0., (14., -4.), (-8., -2.), 'open', False, 1., 0., 0, 0.
    cx = 46.
    if clip == 'idle':
        hover = 5 + [0, 1, 2, 1, 0, -1][n]
        hand_n = (14 + [0, .5, 1, .5, 0, -.5][n], -4 + [0, 1, 2, 1, 0, -1][n])
        hand_f = (-8 - [0, .5, 1, .5, 0, -.5][n], -2 + [0, 1, 2, 1, 0, -1][n])
        eyes = 'blink' if n == 3 else 'open'
        glow = [1, 1.05, 1.1, 1.05, 1, .95][n]
    elif clip == 'walk':
        hover = 5 + [0, -1, 4, 8, 5, 0, 0, 0][n]
        lean = [0, .05, -.03, -.05, 0, .06, .04, 0][n]
        hand_n = [(14, -4), (15, -4), (16, -9), (17, -12), (16, -8), (14, -4), (14, -4), (14, -4)][n]
        sink = [0, 1, 0, 0, 0, 1.5, 1, 0][n]
    elif clip == 'attack':
        cx += [-1, -3, -4, 2, 5, 3, 1, 0][n]
        lean = [-.05, -.12, -.2, .15, .25, .1, .04, 0][n]
        hand_n = [(16, -6), (22, -3), (26, 1), (22, 0), (20, -1), (17, -3), (15, -4), (14, -4)][n]
        hand_f = [(-6, -4), (-10, -6), (-14, -6), (4, -2), (7, 0), (2, -2), (-4, -2), (-8, -2)][n]
        strands = [0, 0, 0, 3, 3, 1, 0, 0][n]
        glow = [1.1, 1.3, 1.5, 1.5, 1.4, 1.1, 1, 1][n]
        eyes = 'angry'
        hover = 5 + [0, 0, 1, 2, 1, 0, 0, 0][n]
    elif clip == 'hurt':
        cx += [-4, -3, -1, 0][n]
        lean = [-.22, -.12, -.04, 0][n]
        hand_n = [(8, 6), (11, 2), (13, -2), (14, -4)][n]
        hand_f = [(-2, 4), (-5, 1), (-7, -1), (-8, -2)][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
        hover = 5 + [-2, -1, 0, 0][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead'
        hover = [5, 7, 4, 2, 0, 0, 0, 0][n]
        sink = [0, 0, 4, 10, 18, 24, 27, 28][n]
        lean = [0, -.15, -.2, -.1, 0, 0, 0, 0][n]
        glow = [1.5, 1.2, 1, .7, .4, .2, .1, .1][n]
        hand_n = [(14, -4), (11, 2), (9, 3), (8, 2), (8, 0), (9, -1), (9, -1), (9, -1)][n]
        hand_f = [(-8, -2), (-7, 3), (-6, 3), (-5, 2), (-5, 0), (-5, -1), (-5, -1), (-5, -1)][n]
    top = AY - 62 - hover
    foot_y = AY - hover - 4
    hem_y = min(AY - 1, foot_y + 2)
    mound = min(1., sink / 28.)
    # robe: shoulders to a scalloped hem, shaded left (light) to right (dark)
    sh_y = lerp(top + 22, hem_y - 8, mound)
    lx = lambda y: cx - 7 - (y - sh_y) * .28 + lean * (hem_y - y) * -.3
    rx = lambda y: cx + 7 + (y - sh_y) * .26 + lean * (hem_y - y) * -.3
    hem = [(lx(hem_y), hem_y)] + [(lerp(lx(hem_y), rx(hem_y), t / 6), hem_y - (2 if t % 2 else -1) + (1 if clip == 'idle' and n % 2 else 0)) for t in range(1, 6)] + [(rx(hem_y), hem_y)]
    robe_poly = polygon([(cx - 6 + lean * 8, sh_y - 3), (cx + 6 + lean * 8, sh_y - 3)] + [(rx(sh_y + (hem_y - sh_y) * t), sh_y + (hem_y - sh_y) * t) for t in (.4, .7)] + hem[::-1] + [(lx(sh_y + (hem_y - sh_y) * t), sh_y + (hem_y - sh_y) * t) for t in (.7, .4)])
    if robe_poly.any():
        # hair of threads trailing behind
        for k in range(3):
            y0 = sh_y + 4 + k * 5
            tip = (cx - 14 - k * 3 - math.sin(n + k) * 1.5, y0 + 12 + k * 3)
            f.line((cx - 4, y0), tip, 'th0', 1)
        f.a[mc.dilate(robe_poly) & ~robe_poly] = p['ol']
        _, lum = gradient(robe_poly, cx - 16, 0, cx + 16, 0, .1, .95)
        f.paint((robe_poly, lum), p.ramp('rb0', 'rb1', 'rb2', 'rb3', 'rb4'), outline=False, dither=.5)
        # gold hem and embroidered runes
        for (a, b) in zip(hem, hem[1:]):
            f.line((a[0], a[1] - 1), (b[0], b[1] - 1), 'gd1', 1)
        for k in range(4):
            yy = sh_y + 8 + k * (hem_y - sh_y - 12) / 3
            if yy < hem_y - 4:
                f.dots([(cx + 1 + (k % 2) * 3, yy), (cx + 2 + (k % 2) * 3, yy + 1)], 'gd1')
    if mound > .15:
        heap = ellipsoid(cx + 1, hem_y - 5, lerp(12, 19, mound), lerp(3, 8, mound))
        f.paint(heap, p.ramp('rb0', 'rb1', 'rb2', 'rb3', 'rb4'), outline=True, dither=.5)
        for k in range(3):
            f.line((cx - 12 + k * 9, hem_y - 2), (cx - 8 + k * 9, hem_y - 7 - k % 2), 'gd1', 1)
    # head
    hy = lerp(top + 12, hem_y - 14, mound)
    hx = cx + 2 + lean * 12
    hood = ellipsoid(hx, hy, 9.5, 11.5, lean * .5)
    peak = polygon([(hx - 7, hy - 6), (hx + 1 + lean * 6, hy - 19), (hx + 8, hy - 5)])
    f.a[mc.dilate(peak | hood[0]) & ~(peak | hood[0])] = p['ol']
    f.paint(hood, p.ramp('rb0', 'rb1', 'rb2', 'rb3'), outline=False, dither=.5)
    f.paint((peak, np.full((H, W), .55)), p.ramp('rb1', 'rb2', 'rb3'), outline=False, dither=.2)
    face = ellipsoid(hx + 3, hy + 1, 6, 7.6)
    f.flat(face[0], 'void')
    ex, ey = hx + 4, hy
    if eyes == 'blink':
        f.line((ex - 2, ey), (ex + 2, ey), 'gd1', 1)
    elif eyes == 'dead':
        eye_dead(f, ex, ey, 'gd0')
    else:
        f.dots([(ex - 2, ey), (ex - 1, ey), (ex + 2, ey), (ex + 3, ey)] + ([(ex - 2, ey - 1), (ex + 2, ey - 1)] if glow > 1.2 else []), 'eye')
    # arms: wide sleeves to pale hands
    sh_n = (cx + 5 + lean * 8, sh_y + 1)
    sh_f = (cx - 4 + lean * 8, sh_y + 1)
    hn = (sh_n[0] + hand_n[0], sh_n[1] + hand_n[1] + 8)
    hf = (sh_f[0] + hand_f[0], sh_f[1] + hand_f[1] + 8)
    for sh, hnd, ramp in ((sh_f, hf, p.ramp('far0', 'far1', 'far2')), (sh_n, hn, p.ramp('rb0', 'rb1', 'rb2', 'rb3'))):
        el = ik(sh, hnd, 11, 11, 1)
        f.paint(capsule(sh, el, 4.4, 3.6), ramp, dither=.4)
        f.paint(capsule(el, hnd, 3.6, 2.6), ramp, dither=.4)
        f.paint(ellipsoid(hnd[0], hnd[1], 2.8, 2.4), p.ramp('sk1', 'sk2', 'sk3'), dither=.3)
    # the thread between the hands, sagging when slack
    slack = max(0, 14 - math.hypot(hn[0] - hf[0], hn[1] - hf[1])) * .4 + 2
    mid = ((hn[0] + hf[0]) / 2, (hn[1] + hf[1]) / 2 + slack)
    pts = smooth([hf, ((hf[0] + mid[0]) / 2, (hf[1] + mid[1]) / 2 + 1), mid, ((hn[0] + mid[0]) / 2, (hn[1] + mid[1]) / 2 + 1), hn], 18)
    for a, b in zip(pts, pts[1:]):
        f.line(a, b, 'th1' if glow < 1.3 else 'th2', 1)
    # a drop spindle hanging from the near hand
    sp = (hn[0] + 1, hn[1] + 9 + math.sin(n) * 1)
    f.line(hn, sp, 'th0', 1)
    f.flat(ellipsoid(sp[0], sp[1] + 2, 2.6, 2.6)[0], 'orb', outline=True)
    f.line((sp[0], sp[1] + 5), (sp[0], sp[1] + 8), 'wd1', 1)
    # strands flung out in the lunge
    for k in range(strands):
        a = (k - 1) * .22
        x0, y0 = hn
        pts = smooth([(x0, y0), (x0 + 10, y0 + math.sin(a) * 6 + 2), (x0 + 20, y0 + math.sin(a) * 12)], 8)
        for u, v in zip(pts, pts[1:]):
            f.line(u, v, 'th2' if k == 1 else 'th1', 1)
        f.dots([pts[-1]], 'th2')
    # drifting motes of thread
    if clip in ('idle', 'walk'):
        for k in range(3):
            f.dots([(cx - 18 + k * 17 + math.sin(n + k * 2) * 3, top + 8 + k * 9 + math.cos(n + k) * 2)], 'th1')
    if flash:
        f.whiten()
    return fit(f.a)


# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_crag_sprites.py)
# ----------------------------------------------------------------------------------------------
DRAWERS = {k: pair for k, pair in {'boar': (globals().get('boar'), globals().get('BOAR')), 'crow': (globals().get('crow'), globals().get('CROW')),
                                   'troll': (globals().get('troll'), globals().get('TROLL')), 'weaver': (globals().get('weaver'), globals().get('WEAVER')),
                                   'ram': (globals().get('ram'), globals().get('RAM')), 'oakhorn': (globals().get('oakhorn'), globals().get('OAKHORN')),
                                   'hrungnir': (globals().get('hrungnir'), globals().get('HRUNGNIR'))}.items()
           if pair[0] is not None}
for _kind, _pair in DRAWERS.items():
    assert len(_pair[1].hex) <= 255


def render(kind):
    draw, _ = DRAWERS[kind]
    return {clip: np.array([draw(clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def bounds_report(kind, frames):
    """Every frame's bounding box against the canvas edges: nothing may touch them."""
    bad = []
    for clip, grids in frames.items():
        for n, grid in enumerate(grids):
            ys, xs = np.nonzero(grid)
            if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > W - 2 or ys.max() > H - 2):
                bad.append(f'{clip} {n}: x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}')
    return bad


def top_report(kind, frames):
    """The topmost pixel of the idle frames: the health bar's `top` in client/field.js."""
    tops = []
    for grid in frames['idle']:
        ys, _ = np.nonzero(grid)
        tops.append(AY - int(ys.min()))
    return min(tops), max(tops)


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        for problem in bounds_report(kind, frames):
            print(f'  EDGE {kind} {problem}')
        print(f'  {kind}: idle top {top_report(kind, frames)}')
        for clip, grids in frames.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#2a3a2c')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def meta_path():
    return ASSETS / 'wyrd.txt'


def build(kinds, replace=False):
    path = meta_path()
    meta = json.loads(path.read_text()) if path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in wyrd.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = DRAWERS[kind][1].hex
        np.savez_compressed(RAW / f'wyrd_{kind}_raw.npz', **frames)
        sid = api('create', {'name': PREFIX + kind + '_all', 'width': W, 'height': H,
                            'frames': sum(count for _, count in CLIPS.values()),
                            'layers': 1, 'fps': 10, 'palette': palette, 'persist': True,
                            'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}]})['sprite_id']
        made[kind] = sid
        offset = 0
        try:
            for clip, (_, count) in CLIPS.items():
                for n, grid in enumerate(frames[clip]):
                    api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [{'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
                offset += count
            print(kind, sid, f'{offset} frames')
        except Exception:
            api('delete', {'sprite_id': sid})
            raise
        # keep a manifest as we go: `list` only shows the newest 100 sprites
        meta['sprites'] = {**meta.get('sprites', {}), **made}
        path.write_text(json.dumps(meta, indent=2) + '\n')


def export(kinds):
    path = meta_path()
    meta = json.loads(path.read_text())
    saved = meta['sprites']
    clips = {}
    for kind in kinds:
        packet = api('get?sprite_id=' + saved[kind])
        sp = packet.get('sprite', packet)
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
        atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
        offset = 0
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            sheet = Image.new('RGBA', (8 * W, H), '#2a3a2c')
            for n in range(count):
                cel = sp['frames'][offset + n]['cels'][0]
                if 'rle' in cel:
                    runs = cel['rle']
                    grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
                else:
                    grid = np.array(cel['grid'], dtype=np.uint8)
                image = rgba(grid, sp['palette'])
                atlas.alpha_composite(image, (n * W, row * H))
                sheet.alpha_composite(image, (n * W, 0))
            clips[clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
            offset += count
            dest = ROOT / 'test-results/wyrd-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'wyrd_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved}
    path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/wyrd_<kind>.png and wyrd.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        atlas = Image.open(ASSETS / f'wyrd_{kind}.png').convert('RGBA')
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * W, row * H, (n + 1) * W, (row + 1) * H))
                if np.array(cell).tobytes() != np.array(rgba(frames[clip][n], palette)).tobytes():
                    raise SystemExit(f'{kind} {clip} {n} differs from the render')
        print(kind, 'atlas is pixel-identical to the render')


def view(kind, picks, out, scale=4):
    """A throwaway contact strip of chosen frames (clip:n ...) at `scale` on the dark ground."""
    palette = DRAWERS[kind][1].hex
    draw, _ = DRAWERS[kind]
    cells = []
    for pick in picks:
        clip, n = pick.split(':')
        cells.append((pick, draw(clip, int(n))))
    sheet = Image.new('RGBA', (len(cells) * W, H + 12), '#2a3a2c')
    d = ImageDraw.Draw(sheet)
    for i, (label, grid) in enumerate(cells):
        sheet.alpha_composite(rgba(grid, palette), (i * W, 0))
        d.line([(i * W + AX - 3, AY), (i * W + AX + 3, AY)], fill='#eabce1')
        d.text((i * W + 2, H), label, fill='white')
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out)


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    names = [a for a in sys.argv[2:] if a in DRAWERS] or list(DRAWERS)
    if command == 'build':
        build(names, '--replace' in sys.argv)
    elif command == 'export':
        export(names)
    elif command == 'verify':
        verify(names)
    elif command == 'view':
        view(names[0], [a for a in sys.argv[3:] if ':' in a and not a.startswith('/')], next(a for a in sys.argv[2:] if a.endswith('.png')))
    elif command == 'preview':
        directory = next((a for a in sys.argv[2:] if a not in DRAWERS and not a.startswith('--')), ROOT / 'test-results/wyrd-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_wyrd_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...] | view kind out.png clip:n ...')
