#!/usr/bin/env python3
"""makesprites workflow for the Gloamfen monsters: preview | build [--replace] | export | verify.

Five kinds (toad, croc, knight, hydra and the elite gloomroot) share the Emberfall Crags contract (scripts/make_crag_sprites.py): one 96x96 frame,
a foot anchor at (48, 90), right-facing art (the game mirrors it) and five clips (idle 6, walk 8, attack 8, hurt 4,
die 8) so client/field.js drives them with the Ironhide's state machine: walk frames 2-4 are the hop, 5-7 the landing,
attack 0-2 the windup, 3-5 the lunge, 6-7 the recovery.

The drawing toolkit (shaded ellipsoids and capsules lit from the upper left, a dithered ramp per material, an outline
around every part) is imported from make_crag_sprites.py. `build` saves ONE new 34-frame PixelFlow sprite per kind
(valhallasc_fen_<kind>_all) and refuses existing names unless --replace is given. `export` reads the editor frames
back, so edits survive, and writes client/assets/fen_<kind>.png plus fen.txt.
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
PREFIX = 'valhallasc_fen_'
KINDS = ['toad', 'croc', 'knight', 'hydra', 'gloomroot']
RAW = ROOT / 'scripts'


def smooth(points, samples):
    """Catmull-Rom-ish resampling of a polyline into `samples` points (for tails, necks, coils)."""
    pts = np.array(points, dtype=float)
    out = []
    for i in range(samples):
        t = i / (samples - 1) * (len(pts) - 1)
        j = min(int(t), len(pts) - 2)
        u = t - j
        p0, p1, p2, p3 = pts[max(j - 1, 0)], pts[j], pts[j + 1], pts[min(j + 2, len(pts) - 1)]
        out.append(tuple(.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)))
    return out


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


# ----------------------------------------------------------------------------------------------
# Fen Toad: a squat, warty, olive toad with lantern-yellow glands and a long sticky tongue; it hops.
# ----------------------------------------------------------------------------------------------
TOAD = Palette({
    'sk0': '#16200f', 'sk1': '#27401a', 'sk2': '#3f6a26', 'sk3': '#62952f', 'sk4': '#8fc044', 'sk5': '#c3e86b',
    'far0': '#101a0b', 'far1': '#1c2d12', 'far2': '#2d4a1c', 'bel0': '#9aa05a', 'bel1': '#c9cf7c', 'bel2': '#eef1b4',
    'spot': '#1e2b12', 'wart': '#a7d452', 'glow': '#e6ff70', 'glow2': '#fffbb0', 'eye': '#ffd23f', 'eye2': '#fff1a0',
    'pupil': '#120d08', 'socket': '#0a1006', 'mouth': '#3a1020', 'tongue': '#e0607a', 'tongue2': '#f59ab0',
    'slime': '#d9f7c8', 'drip': '#7fd0e0',
})


def toad(clip, n):
    f = Frame(TOAD)
    p = TOAD
    rng = rng_for('toad', clip, n)
    cx, lift, squash, flash, eyes = 40., 0., 1., False, 'open'
    sac, tongue, jaw, reach, tuck, tilt = 0., 0., 0., 0., 0., 0.
    glow = 1.
    supine = 0.
    if clip == 'idle':
        squash = [1, 1.02, 1.04, 1.02, 1, .98][n]
        sac = [0, .3, .8, 1, .6, .2][n]
        glow = [.8, 1, 1.2, 1.3, 1.1, .9][n]
        eyes = 'blink' if n == 4 else 'open'
    elif clip == 'walk':
        lift = [0, 0, 11, 19, 11, 0, 0, 0][n]
        squash = [1, .9, 1.08, 1.12, 1.06, .84, .92, .98][n]
        reach = [0, 0, .7, 1, .8, 0, 0, 0][n]
        tuck = [0, .4, 0, 0, 0, 0, 0, 0][n]
        sac = [0, .3, 0, 0, 0, .5, .3, 0][n]
        tilt = [0, 0, -.12, -.2, -.05, .06, .03, 0][n]
    elif clip == 'attack':
        cx += [-1, -2, -3, 3, 7, 6, 3, 0][n]
        squash = [.93, .84, .78, 1.05, .96, .94, .98, 1][n]
        sac = [.5, .9, 1, .4, 0, 0, 0, 0][n]
        tongue = [0, 0, 0, 15, 16, 6, 0, 0][n]
        jaw = [0, .3, .5, 1, 1, .6, .2, 0][n]
        lift = [0, 0, 0, 5, 2, 0, 0, 0][n]
        reach = [0, 0, 0, 1, .8, .2, 0, 0][n]
        eyes = 'angry'
        glow = [1.3, 1.6, 1.8, 1.5, 1.2, 1, 1, 1][n]
    elif clip == 'hurt':
        flash = n == 0
        cx += [-3, -2, -1, 0][n]
        squash = [.84, .9, .96, 1][n]
        jaw = [.8, .5, .2, 0][n]
        tongue = [5, 2, 0, 0][n]
        eyes = 'hurt' if n < 3 else 'angry'
        glow = [1.8, 1.4, 1.1, 1][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        cx += [0, -1, -1, 0, 1, 1, 1, 1][n]
        squash = [1, .92, .84, .8, .8, .8, .8, .8][n]
        supine = [0, 0, .35, .7, 1, 1, 1, 1][n]
        jaw = [.8, .5, .4, .5, .5, .5, .5, .5][n]
        tongue = [4, 6, 8, 9, 10, 10, 10, 10][n]
        glow = [1.6, 1.1, .8, .5, .3, .2, .15, .1][n]
    ground = AY - lift
    cy = AY - 22 * squash - lift + (2 if supine else 0)
    rx, ry = 22 / squash ** .45, 18 * squash
    skin = p.ramp('sk0', 'sk1', 'sk2', 'sk3', 'sk4', 'sk5')
    far = p.ramp('far0', 'far1', 'far2')
    belly = p.ramp('bel0', 'bel1', 'bel2')
    wr = np.random.default_rng(11)
    warts = [(wr.uniform(-.8, .8), wr.uniform(-.8, .3)) for _ in range(16)]

    def leg_set(side):
        """Hind and fore legs; `side` far is darker and offset behind the body."""
        ramp = skin if side == 'near' else far
        off = 0 if side == 'near' else -5
        # hind leg: haunch, shank folded back along the ground, long foot
        hx, hy = cx - 12 + off, cy + 5
        foot = (cx + 3 + off - reach * 19, ground - 2 - (reach * 6 if lift else 0))
        knee = (cx - 21 + off - reach * 4, cy + 7 - tuck * 2 - reach * 2)
        if supine:
            f.paint(capsule((hx, hy - 4), (hx - 8 + supine * 0, hy - 16 * supine - 3), 5, 3.4), ramp, dither=.4)
            f.paint(capsule((hx - 8, hy - 16 * supine - 3), (hx + 1 + 3 * supine, hy - 22 * supine - 6), 3.4, 2.4), ramp, dither=.4)
            f.paint(capsule((cx + 12 + off, cy - 6), (cx + 15 + off, cy - 5 - 14 * supine), 3.4, 2.6), ramp, dither=.4)
            f.paint(capsule((cx + 15 + off, cy - 5 - 14 * supine), (cx + 20 + off, cy - 9 - 16 * supine), 2.6, 2.0), ramp, dither=.4)
            return
        f.paint(ellipsoid(hx, hy, 11.5, 10.5), ramp, dither=.5)
        f.paint(capsule((hx - 4, hy + 3), knee, 5, 3.2), ramp, dither=.4)
        f.paint(capsule(knee, (foot[0] - 2, foot[1] - 2), 3.4, 2.4), ramp, dither=.4)
        f.paint(ellipsoid(foot[0] + 2, foot[1] - 1, 8.5, 2.7), ramp, dither=.3)
        f.dots([(foot[0] + 9 - k * 2, foot[1] - 0.5 + (k % 2)) for k in range(3)], 'sk5' if side == 'near' else 'sk2')
        # fore leg
        sx, sy = cx + 14 + off + reach * 4, cy + 7
        hand = (sx + 4 + reach * 6, ground - 2 - (reach * 3 if lift else 0))
        elbow = (sx + 1, (sy + hand[1]) / 2 + 1)
        f.paint(capsule((sx, sy), elbow, 3.8, 3.0), ramp, dither=.4)
        f.paint(capsule(elbow, (hand[0], hand[1] - 1), 3.0, 2.3), ramp, dither=.4)
        f.paint(ellipsoid(hand[0] + 2, hand[1], 5, 2.2), ramp, dither=.3)

    leg_set('far')
    body = ellipsoid(cx, cy, rx, ry, -tilt)
    if supine:
        # on its back: pale belly up, drawn with the belly ramp
        f.paint(body, belly, dither=.55)
        rim = body[0] & ~(ellipsoid(cx, cy + 1.5, rx - 5, ry - 4.5)[0])
        f.a[rim] = p['sk2']
        f.a[rim & (DITHER > .1) & (YY < cy)] = p['sk3']
        f.a[body[0] & (YY > cy + ry * .55) & (DITHER > -.3)] = p['bel0']
        sp = ellipsoid(cx - 2, cy + 1, rx * .5, ry * .45)[0]
        f.a[sp & (DITHER > .25) & (np.abs(XX - cx) < rx * .5)] = p['bel2']
    else:
        f.paint(body, skin, dither=.6)
        # pale belly and throat
        under = ellipsoid(cx + 2, cy + ry * .5, rx * .88, ry * .5)[0] & body[0] & (YY > cy + ry * .42)
        f.a[under] = p['bel1']
        f.a[under & (YY > cy + ry * .75) & (DITHER > -.1)] = p['bel2']
        # dark mottling and warts
        for k, (u, v) in enumerate(warts):
            x, y = cx + u * rx * .9, cy + v * ry * .85
            if not body[0][min(max(int(y), 0), H - 1), min(max(int(x), 0), W - 1)] or y > cy + ry * .5:
                continue
            if k % 3 == 0:
                f.flat(ellipsoid(x, y, 3.2, 2.2)[0] & body[0], 'spot')
            else:
                f.dots([(x, y), (x + 1, y)], 'wart')
        # glands behind the eyes glow like fen lanterns
        gx, gy = cx + 3, cy - ry * .78
        f.paint(ellipsoid(gx, gy, 5.5, 3.2, .3), p.ramp('sk3', 'glow', 'glow2') if glow > 1.15 else p.ramp('sk2', 'sk4', 'glow'), dither=.4)
        if sac:
            f.paint(ellipsoid(cx + rx * .72, cy + 3 + sac * 2, 4 + 6 * sac, 3 + 7 * sac), belly, dither=.4)
        # the mouth: a long curved line, or a dark open gape with the tongue
        mx0, my0 = cx + rx * .95, cy - 1 + jaw * 1
        if jaw > .25:
            gape = polygon([(cx + 8, cy - 1), (mx0 + 1, cy - 2), (mx0 - 1, cy + 2 + jaw * 6), (cx + 9, cy + 4 + jaw * 3)])
            f.flat(gape, 'mouth', outline=True)
            if tongue:
                tip = (mx0 - 2 + tongue, cy + 2 - jaw * 1)
                f.paint(capsule((cx + 12, cy + 2 + jaw * 2), tip, 1.7, 1.5), p.ramp('tongue', 'tongue2'), dither=.3)
                f.paint(ellipsoid(tip[0] + 1, tip[1], 3.2, 2.8), p.ramp('tongue', 'tongue2', 'slime'), dither=.3)
        else:
            f.line((mx0 + 1, my0 + 1), (cx + 4, my0 + 5), 'mouth', 2)
            f.line((mx0, my0 - 1), (cx + 6, my0 + 2), 'sk5', 1)
    # eyes on top: big bulging domes
    if not supine:
        for k, (dx, dy, er) in enumerate([(5, -ry * .95, 4.6), (13, -ry * .88, 5.6)]):
            ex, ey = cx + dx, cy + dy - (1 if eyes == 'angry' else 0)
            f.paint(ellipsoid(ex, ey, er + .6, er * .85), skin, dither=.4)
            if eyes == 'dead':
                eye_dead(f, ex + 1, ey)
            elif eyes == 'blink':
                f.line((ex - 3, ey), (ex + 3, ey), 'socket', 1)
            else:
                f.flat(ellipsoid(ex + 1, ey, er * .75, er * .62)[0], 'eye', outline=True, edge='socket')
                f.dots([(ex + 1 + k2, ey) for k2 in (-1, 0, 1)], 'pupil')
                f.dots([(ex - 1, ey - 1)], 'eye2')
                if eyes in ('angry', 'hurt'):
                    f.line((ex - er, ey - er * .7 - 1), (ex + er, ey - er * .7 + (0 if eyes == 'angry' else -3)), 'socket', 1)
    else:
        ex, ey = cx + rx * .62, cy - 1
        eye_dead(f, ex, ey)
        f.line((cx + rx * .95, cy + 1), (cx + rx * .6, cy + 3), 'mouth', 1)
        if tongue:
            f.paint(capsule((cx + rx * .8, cy + 3), (cx + rx * .8 + tongue * .7, cy + 7), 2.2, 1.8), p.ramp('tongue', 'tongue2'), dither=.3)
    near_ok = True
    leg_set('near') if near_ok else None
    if clip == 'attack' and n in (3, 4):
        for k in range(4):
            f.dots([(cx + 33 + tongue + rng.uniform(0, 6), cy + rng.uniform(-3, 8))], 'drip' if k % 2 else 'slime')
    if clip == 'walk' and n == 5:
        for k in range(6):
            f.dots([(cx + rng.uniform(-24, 24), AY - 1 - rng.uniform(0, 4))], 'slime' if k % 2 else 'drip')
    if clip == 'die' and n >= 4:
        for k in range(5 if n < 7 else 2):
            f.dots([(cx - 22 + rng.uniform(0, 46), AY - 3 - rng.uniform(0, 8))], 'slime' if k % 2 else 'drip')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Mire Crocodile: a long, low, moss-streaked crocodile in side view with a heavy jaw, a ridge of scutes, a lashing tail.
# ----------------------------------------------------------------------------------------------
CROC = Palette({
    'sc0': '#161c14', 'sc1': '#26331f', 'sc2': '#3c5128', 'sc3': '#5b7433', 'sc4': '#86a047', 'sc5': '#b3c76a',
    'far0': '#0f130d', 'far1': '#1a2415', 'far2': '#2a3a1d', 'bel0': '#a69a62', 'bel1': '#d0c58c', 'bel2': '#f0e8b8',
    'moss': '#4f8a3a', 'moss2': '#79b84e', 'scute': '#131810', 'scute2': '#3b4a2a', 'eye': '#ffc83a', 'eye2': '#fff2a8',
    'pupil': '#0d0a06', 'socket': '#080b06', 'mouth': '#4a1424', 'tongue': '#c8506c', 'tooth': '#f4f0dc',
    'mud': '#6b5a3a', 'drip': '#7fd0e0', 'spray': '#c8ecf2',
})


def croc(clip, n):
    f = Frame(CROC)
    p = CROC
    rng = rng_for('croc', clip, n)
    cx, crouch, jaw, tail_sw, head_up, lift, flash, eyes = 41., 0., 0., 0., 0., 0., False, 'open'
    gait, sag, thrash = 0., 0., 0.
    sw = n / 6 * 2 * math.pi
    if clip == 'idle':
        crouch = [0, .4, .8, .4, 0, -.3][n]
        jaw = [0, 0, .12, .25, .12, 0][n]
        tail_sw = math.sin(sw) * 2.5
        head_up = [0, .3, .6, .3, 0, 0][n]
        eyes = 'blink' if n == 4 else 'open'
    elif clip == 'walk':
        gait = n / 8 * 2 * math.pi
        crouch = [0, 0, -1, -1.5, -1, 0, .5, .2][n]
        lift = [0, 0, 1, 2, 1, 0, 0, 0][n]
        tail_sw = math.sin(gait) * 4
        head_up = [0, .2, .5, .6, .4, 0, 0, 0][n]
        jaw = [0, 0, .1, .2, .1, 0, 0, 0][n]
    elif clip == 'attack':
        cx += [-1, -2, -2, 3, 6, 5, 3, 0][n]
        crouch = [1, 2.5, 4, -1, 0, 0, .5, 0][n]
        jaw = [.2, .5, .8, 1, 1, .6, .2, .1][n]
        head_up = [.3, .9, 1.4, -.6, -.8, -.3, 0, 0][n]
        tail_sw = [2, 4, 5, -6, -7, -3, 0, 0][n]
        lift = [0, 0, 0, 1, 0, 0, 0, 0][n]
        eyes = 'angry'
        thrash = 1. if n in (4, 5) else 0.
    elif clip == 'hurt':
        flash = n == 0
        cx += [-3, -2, -1, 0][n]
        crouch = [3, 2, 1, 0][n]
        jaw = [1, .7, .3, 0][n]
        head_up = [1.3, .9, .3, 0][n]
        tail_sw = [-5, -3, -1, 0][n]
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        cx += [0, -1, 0, 1, 2, 2, 2, 2][n]
        sag = [0, .2, .45, .7, .9, 1, 1, 1][n]
        crouch = [0, 1.5, 3, 4.5, 6, 6, 6, 6][n]
        jaw = [1, .8, .7, .8, .9, .9, .9, .9][n]
        head_up = [1, .5, 0, -.4, -.6, -.6, -.6, -.6][n]
        tail_sw = [-4, -6, -8, -9, -9, -9, -9, -9][n]
    ground = AY - lift
    cy = AY - 17 + crouch - lift
    ry = 9.5 - sag * 2.5
    body_ramp = p.ramp('sc0', 'sc1', 'sc2', 'sc3', 'sc4', 'sc5')
    far = p.ramp('far0', 'far1', 'far2')

    def leg(x, side, phase):
        ramp = far if side == 'far' else body_ramp
        ox = -4 if side == 'far' else 0
        hip = (x + ox, cy + ry * .5)
        swing = math.sin(gait + phase) * 5 if clip == 'walk' else 0
        raise_ = max(0., -math.cos(gait + phase)) * 4 if clip == 'walk' else 0
        foot = (hip[0] + 3 + swing + sag * 8 * (1 if side == 'near' else .6), ground - 1 - raise_)
        if sag:
            foot = (hip[0] + 8 + 6 * sag * (1 if x > cx else -1), ground - 1)
        knee = (hip[0] + 5 + swing * .4, (hip[1] + foot[1]) / 2 + 1)
        f.paint(capsule(hip, knee, 4.2, 3.2), ramp, dither=.4)
        f.paint(capsule(knee, (foot[0] - 2, foot[1] - 1), 3.2, 2.4), ramp, dither=.4)
        f.paint(ellipsoid(foot[0] + 1, foot[1] - 1, 5.2, 2.3), ramp, dither=.3)
        f.dots([(foot[0] + 5, foot[1] - 1), (foot[0] + 6, foot[1])], 'tooth' if side == 'near' else 'sc2')

    leg(cx + 14, 'far', math.pi)
    leg(cx - 14, 'far', 0)
    # tail: chain of discs curling up at the tip, one outline round the lot
    base = (cx - 16, cy + 1)
    tip = (cx - 31 + sag * 2, cy + 3 - tail_sw * .5 * (1 - sag) - 6 * (1 - sag) + 1 * sag)
    mid = (cx - 25, cy + 4 + tail_sw * .3)
    tail = smooth([base, (cx - 20, cy + 2 + tail_sw * .2), mid, tip], 18)
    discs = []
    for i, (x, y) in enumerate(tail):
        t = i / 17
        r = 7.5 * (1 - t) ** .8 + 1.6
        discs.append(ellipsoid(x, y, r + .6, r * (1 - sag * .15)))
    body = ellipsoid(cx, cy, 23, ry)
    discs.append(body)
    chain_paint(f, discs, body_ramp, dither=.55)
    # belly stripe along the underside
    low = (body[0] | np.any([d[0] for d in discs[:-1]], axis=0)) & (YY > cy + ry * .45)
    low &= XX > cx - 20
    f.a[low & (DITHER > -.1) & (XX > cx - 18)] = p['bel0']
    f.a[low & (YY > cy + ry * .68) & (XX > cx - 14) & (DITHER > -.2)] = p['bel1']
    # moss patches and mud
    for k in range(9):
        x = cx - 26 + (k * 11) % 48 + rng_for('crocmoss', 'x', k).uniform(0, 3)
        y = cy - ry * .6 + (k * 5) % 7
        f.dots([(x, y), (x + 1, y), (x, y + 1)], 'moss2' if k % 2 else 'moss')
    # scutes along the back: dark plates with a lit edge
    for k in range(11):
        x = cx + 18 - k * 4.4
        t = k / 10
        top = cy - ry + 1.5 if x > cx - 16 else cy - 6.5 - (x - (cx - 16)) * .0 + (cx - 16 - x) * -.15
        top = cy - ry + 1.2 - (4 if x < cx - 16 else 0) * 0 + max(0, (cx - 16 - x)) * .35 * 0
        sp = polygon([(x - 2, top + 2), (x, top - 3.2), (x + 2, top + 2)])
        f.flat(sp, 'scute')
        f.dots([(x - 1, top)], 'scute2')
    # near legs
    leg(cx + 15, 'near', 0)
    leg(cx - 13, 'near', math.pi)
    # head: skull, upper jaw, lower jaw hinged at the skull
    hx, hy = cx + 19, cy - 3 - head_up * 3
    a = -head_up * .12
    ca, sa = math.cos(a), math.sin(a)

    def at(u, v):
        return hx + u * ca - v * sa, hy + u * sa + v * ca
    open_a = jaw * .5
    jd = (math.cos(a + open_a), math.sin(a + open_a))
    jaw_base = at(2, 4)
    jaw_tip = (jaw_base[0] + jd[0] * 18, jaw_base[1] + jd[1] * 18)
    if jaw > .15:
        f.flat(polygon([at(4, 1), at(20, 1), jaw_tip, jaw_base]), 'mouth', outline=True)
        f.dots([((jaw_base[0] + jaw_tip[0]) / 2 + 2, (jaw_base[1] + jaw_tip[1]) / 2 - 2)], 'tongue')
    f.paint(capsule(jaw_base, jaw_tip, 3.6, 2.6), p.ramp('bel0', 'bel1', 'bel2'), dither=.3)
    for k in range(5):
        tx = jaw_base[0] + (jaw_tip[0] - jaw_base[0]) * (k + 1) / 6
        ty = jaw_base[1] + (jaw_tip[1] - jaw_base[1]) * (k + 1) / 6
        f.dots([(tx, ty - 1 - (1 if k % 2 else 0))], 'tooth')
    skull = ellipsoid(*at(2, -1), 9.5, 7.6, a)
    f.paint(skull, body_ramp, dither=.5)
    snout = capsule(at(6, 0), at(19 + jaw * 1, 1), 6.2, 4.4)
    f.paint(snout, body_ramp, dither=.5)
    f.paint(ellipsoid(*at(20, -1.5), 3, 2.4, a), body_ramp, dither=.3)
    f.dots([at(21, -2.5), at(20, -2.5)], 'socket')
    for k in range(5):
        u = 9 + k * 2.6
        f.dots([at(u, 4.4 + (0 if jaw > .15 else -.6)), at(u, 5.4 + (0 if jaw > .15 else -.6))], 'tooth')
    # brow ridge and golden eye with a slit pupil
    ex, ey = at(8, -6.5)
    f.paint(ellipsoid(ex, ey + .5, 4.2, 3.2), body_ramp, dither=.3)
    if eyes == 'dead':
        eye_dead(f, ex + 1, ey)
    elif eyes == 'blink':
        f.line((ex - 2, ey), (ex + 3, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex + 1, ey, 2.7, 2.1 if eyes != 'angry' else 1.5)[0], 'eye', outline=True, edge='socket')
        f.dots([(ex + 1, ey - 1), (ex + 1, ey), (ex + 1, ey + 1)] if eyes != 'angry' else [(ex + 1, ey)], 'pupil')
        f.dots([(ex, ey - 1)], 'eye2')
        if eyes in ('angry', 'hurt'):
            f.line((ex - 3, ey - 3), (ex + 4, ey - 2 if eyes == 'angry' else ey - 5), 'socket', 1)
    if thrash:
        for k in range(8):
            f.dots([(cx + 26 + rng.uniform(0, 14), cy + 4 + rng.uniform(-10, 10))], 'spray' if k % 2 else 'drip')
    if clip == 'die' and n >= 4:
        for k in range(5 if n < 7 else 2):
            f.dots([(cx - 24 + rng.uniform(0, 60), AY - 3 - rng.uniform(0, 5))], 'drip' if k % 2 else 'mud')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Drowned Knight: a barnacled, verdigris-green suit of plate with a kelp plume, a ragged surcoat, a tower shield and a
# notched sword; teal light in the visor. Dying, it comes apart into a pile of armour.
# ----------------------------------------------------------------------------------------------
KNIGHT = Palette({
    'ar0': '#1b2423', 'ar1': '#2d403c', 'ar2': '#466359', 'ar3': '#6a8d7a', 'ar4': '#9bbfa8', 'ar5': '#cde8d4',
    'rust': '#7a3f1e', 'rust2': '#b86a2c', 'kelp0': '#18321d', 'kelp1': '#2b6332', 'kelp2': '#58a448',
    'cl0': '#1d2146', 'cl1': '#313a74', 'cl2': '#5560a8', 'eye': '#6ff5e0', 'eye2': '#e8fffa', 'socket': '#04100e',
    'drip': '#7fd0e0', 'spray': '#c8ecf2', 'barn': '#d9d4bc', 'barn2': '#a8a38a',
})
KNIGHT_PARTS = {
    'leg_far': ('cap', (-4, -29), (-6, -5), 4.6, 4.0),
    'boot_far': ('ell', (-4, -3.5), 7.5, 3.4),
    'shield': ('ell', (-15, -37), 6.5, 14),
    'arm_far': ('cap', (-9, -54), (-14, -33), 3.6, 3.4),
    'shoulder_far': ('ell', (-9, -55), 6, 5),
    'pelvis': ('ell', (1, -32), 9, 6),
    'leg_near': ('cap', (6, -29), (8, -5), 5, 4.4),
    'boot_near': ('ell', (10, -3.5), 8.5, 3.6),
    'torso': ('ell', (1, -47), 11, 14),
    'head': ('ell', (4, -68), 6.8, 8.4),
    'arm_near': ('cap', (12, -54), (18, -33), 4, 3.7),
    'shoulder_near': ('ell', (12, -56), 7, 5.4),
    'fist_near': ('ell', (18, -32), 4.4, 4.2),
}
KNIGHT_ORDER = ['leg_far', 'boot_far', 'shield', 'arm_far', 'shoulder_far', 'pelvis', 'leg_near', 'boot_near', 'surcoat',
                'torso', 'head', 'arm_near', 'sword', 'shoulder_near', 'fist_near']
KNIGHT_RUBBLE = {
    'leg_far': (-18, -7), 'boot_far': (-8, -6), 'shield': (-21, -7), 'arm_far': (-27, -5), 'shoulder_far': (-12, -8),
    'pelvis': (2, -8), 'leg_near': (14, -7), 'boot_near': (20, -6), 'torso': (-3, -13), 'head': (12, -9),
    'arm_near': (26, -5), 'shoulder_near': (6, -10), 'fist_near': (31, -6),
}


def knight(clip, n):
    f = Frame(KNIGHT)
    p = KNIGHT
    rng = rng_for('knight', clip, n)
    cx = 40
    eyes, glow, flash, squash, lean, lift, rubble = 'open', 1., False, 1., 0., 0., 0.
    off = {k: [0., 0.] for k in KNIGHT_PARTS}
    pose_fist = None
    theta = .55                      # sword angle from straight up, toward the front
    impact = 0
    sway = n / 6 * 2 * math.pi
    plume = 0.
    if clip == 'idle':
        breathe = [0, .5, 1, 1, .5, 0][n]
        for k in ('torso', 'head', 'shoulder_near', 'shoulder_far'):
            off[k][1] = -breathe
        glow = [.8, 1, 1.2, 1.3, 1.1, .9][n]
        theta = .55 + math.sin(sway) * .06
        plume = math.sin(sway)
        eyes = 'blink' if n == 4 else 'open'
    elif clip == 'walk':
        lift = [0, 0, 2, 3, 2, 0, 0, 0][n]
        squash = [1, 1, 1, 1, 1, .96, .94, .98][n]
        lean = [1, 1, 2, 3, 2, 0, -1, 0][n]
        w = [-1, -.5, .6, 1, .7, 0, -.8, -1][n]
        off['leg_near'][0] = off['boot_near'][0] = w * 7
        off['leg_far'][0] = off['boot_far'][0] = -w * 7
        off['boot_near'][1] = -max(0, w) * 5
        off['boot_far'][1] = -max(0, -w) * 5
        theta = .55 - w * .15
        plume = [0, .3, .8, 1, .6, -.4, -.6, -.2][n]
    elif clip == 'attack':
        lean = [-2, -4, -6, 3, 8, 7, 3, 0][n]
        cx += [-1, -2, -3, 1, 3, 3, 2, 0][n]
        glow = [1.3, 1.5, 1.7, 1.7, 1.5, 1.2, 1, 1][n]
        eyes = 'angry'
        impact = 1 if n in (4, 5) else 0
        squash = [.99, .97, .96, 1.02, .94, .95, .98, 1][n]
        pose_fist = [(19, -36), (14, -56), (7, -68), (15, -62), (21, -38), (22, -31), (21, -32), (19, -33)][n]
        theta = [.6, -.2, -1.35, 1.0, 2.5, 2.7, .8, .6][n]
        plume = [0, -.5, -1, .8, 1, .5, 0, 0][n]
    elif clip == 'hurt':
        flash = n == 0
        lean = [-5, -3, -1, 0][n]
        cx += [-3, -2, -1, 0][n]
        squash = [.94, .96, .99, 1][n]
        glow = [1.8, 1.4, 1.15, 1][n]
        eyes = 'hurt' if n < 3 else 'angry'
        theta = [.1, .3, .5, .55][n]
        plume = [-1, -.6, -.2, 0][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        lean = [0, -3, -4, 0, 0, 0, 0, 0][n]
        rubble = [0, 0, .3, .62, .9, 1, 1, 1][n]
        glow = [1.8, 1.3, 1.0, .7, .4, .2, .1, .05][n]
        squash = [1, .96, .9, .85, .8, .75, .75, .75][n]
    ground = AY
    ramp = p.ramp('ar0', 'ar1', 'ar2', 'ar3', 'ar4', 'ar5')

    def center(name, base):
        dx, dy = off[name]
        if rubble:
            delay = {'head': 0, 'sword': 0, 'fist_near': .05, 'arm_near': .08, 'arm_far': .08, 'shield': .1, 'shoulder_near': .1,
                     'shoulder_far': .1, 'torso': .15}.get(name, .25)
            t = float(np.clip((rubble - delay) / (1 - delay), 0, 1)) ** .85
            rx, ry = KNIGHT_RUBBLE[name]
            return (lerp(base[0], rx, t) + dx, lerp(base[1], ry, t) + dy), t
        return (base[0] + dx, base[1] + dy), 0.

    def place(base):
        x, y = base
        k = (-y) / 70
        return cx + x + lean * k * 1.5, ground + y * squash - lift

    anchors = {}
    for name in KNIGHT_ORDER:
        if name == 'surcoat':
            # a ragged cloth hanging from the waist, swaying with the legs; gone once the armour has fallen
            if rubble > .3:
                continue
            top = place((2, -36))
            hem = ground - 17 * squash - lift - rubble * 20
            wob = off['leg_near'][0] * .25
            pts = [(top[0] - 7, top[1]), (top[0] + 8, top[1])]
            for k in range(4):
                x = top[0] + 8 - k * 5 + (wob if k % 2 else -wob)
                pts.append((x, hem + (4 if k % 2 else 0) + (k % 3)))
            m = polygon(pts)
            f.paint(gradient(m, top[0] - 7, top[1], top[0] + 8, hem, .15, .85), p.ramp('cl0', 'cl1', 'cl2'), dither=.4)
            continue
        if name == 'sword':
            if rubble:
                t = float(np.clip(rubble / .9, 0, 1))
                hx_, hy_ = place((lerp(19, 12, t), lerp(-28, -8, t)))
                ang = lerp(theta, 1.62, t)
            else:
                fx, fy = pose_fist if pose_fist else (18, -32)
                dx_, dy_ = off['fist_near']
                hx_, hy_ = place((fx + dx_, fy + dy_))
                ang = theta
            L = 32
            tip = (hx_ + L * math.sin(ang), hy_ - L * math.cos(ang))
            blade = capsule((hx_, hy_), tip, 3.0, 1.1)
            f.paint(blade, p.ramp('ar2', 'ar3', 'ar4', 'ar5'), dither=.3)
            for k in range(5):
                u = (k + 1.5) / 6.5
                f.dots([(hx_ + (tip[0] - hx_) * u, hy_ + (tip[1] - hy_) * u)], 'rust' if k % 2 else 'rust2')
            gx, gy = hx_ + 2.4 * math.sin(ang) * 0, hy_
            f.line((hx_ - 5 * math.cos(ang), hy_ - 5 * math.sin(ang)), (hx_ + 5 * math.cos(ang), hy_ + 5 * math.sin(ang)), 'rust2', 2)
            anchors['sword'] = tip
            continue
        spec = KNIGHT_PARTS[name]
        if spec[0] == 'ell':
            (bx, by), t = center(name, spec[1])
            ox, oy = place((bx, by))
            rx, ry = spec[2], spec[3] * (1 - .3 * t)
            if name == 'fist_near' and pose_fist and not rubble:
                ox, oy = place(pose_fist)
            if name == 'shield' and rubble:
                rx, ry = spec[2] + 5 * t, spec[3] * (1 - .8 * t)
            shape = ellipsoid(ox, oy, rx * (1 + .12 * t), ry)
        else:
            (b0x, b0y), t = center(name, spec[1])
            (b1x, b1y), _ = center(name, spec[2])
            if rubble:
                mid = ((b0x + b1x) / 2, max(b0y, b1y))
                b0x, b0y = mid[0] - 7 * t - (1 - t) * (mid[0] - b0x), lerp(b0y, mid[1], t)
                b1x, b1y = mid[0] + 7 * t + (1 - t) * (b1x - mid[0]), lerp(b1y, mid[1], t)
            a, b = place((b0x, b0y)), place((b1x, b1y))
            if name == 'arm_near' and pose_fist and not rubble:
                a = place(KNIGHT_PARTS['shoulder_near'][1])
                b = place(pose_fist)
                a = (a[0], a[1] + 2)
            shape = capsule(a, b, spec[3] * (1 - .35 * t), spec[4] * (1 - .35 * t))
        mask, lum = shape
        f.paint(shape, ramp, dither=.6)
        ys, xs = np.nonzero(mask)
        if not len(xs):
            continue
        mx, my = xs.mean(), ys.mean()
        # rust streaks and barnacles on the plates
        if name in ('torso', 'shoulder_near', 'shoulder_far', 'pelvis', 'boot_near', 'shield'):
            for k in range(4):
                bx_, by_ = mx + rng_for('knbarn' + name, 'x', k).uniform(-5, 5), my + rng_for('knbarn' + name, 'y', k).uniform(-6, 6)
                if 0 <= int(by_) < H and 0 <= int(bx_) < W and mask[int(by_), int(bx_)]:
                    f.dots([(bx_, by_), (bx_ + 1, by_)], 'barn' if k % 2 else 'rust2')
            f.a[mask & (DITHER > .3) & (np.abs(XX - mx - 3) < 1) & (YY > my - 4)] = p['rust']
        if name == 'shield':
            f.line((mx, my - ry * .75), (mx, my + ry * .75), 'ar4', 1)
            f.line((mx - min(4, rx * .5), my - ry * .2), (mx + min(4, rx * .5), my - ry * .2), 'ar4', 1)
        if name == 'torso':
            f.line((mx - 6, my - 3), (mx + 8, my - 1), 'ar1', 1)      # the plate seam
            f.dots([(mx - 4, my + 5), (mx + 5, my + 6)], 'kelp2')
        if name == 'head':
            hx_, hy_ = mx, my
            if not rubble:
                for k in range(3):                      # a plume of kelp, trailing back and swaying
                    base = (hx_ - 3 - k * 1.5, hy_ - 7)
                    tipk = (hx_ - 10 - k * 3 - plume * 4 * (k + 1) * .5, hy_ - 14 + k * 4 + abs(plume) * 2)
                    mid = (hx_ - 7 - k * 2 - plume * 2, hy_ - 14 + k * 2)
                    for (a_, b_) in zip([base, mid], [mid, tipk]):
                        f.paint(capsule(a_, b_, 2.2 - k * .3, 1.4 - k * .3), p.ramp('kelp0', 'kelp1', 'kelp2'), dither=.3)
                f.paint(ellipsoid(hx_, hy_, 6.8, 8.4), ramp, dither=.6)
                f.a[polygon([(hx_ - 1, hy_ - 2.5), (hx_ + 9, hy_ - 3), (hx_ + 9, hy_ + 0.5), (hx_ - 1, hy_ + 1)]) & mask] = p['socket']
                for xe in (hx_ + 2, hx_ + 6):
                    if eyes == 'dead':
                        f.dots([(xe, hy_ - 1)], 'ar1')
                    elif eyes == 'blink':
                        pass
                    else:
                        f.dots([(xe, hy_ - 1), (xe + 1, hy_ - 1)] + ([(xe, hy_ - 2)] if glow > 1.2 else []), 'eye')
                        f.dots([(xe + 1, hy_ - 1)], 'eye2')
                f.line((hx_ + 1, hy_ + 3), (hx_ + 8, hy_ + 3), 'ar1', 1)      # breaths
                f.line((hx_ + 4, hy_ + 1), (hx_ + 4, hy_ + 7), 'ar1', 1)
                f.dots([(hx_ - 2, hy_ - 7), (hx_ - 3, hy_ - 6)], 'barn')
            else:
                f.dots([(hx_ + 2, hy_), (hx_ + 6, hy_)], 'socket')
    if impact:
        gx = cx + 27
        for k in range(10):
            a_ = rng.uniform(-3.1, 0)
            d_ = rng.uniform(5, 14) * (1 if n == 4 else 1.2)
            f.dots([(gx + math.cos(a_) * d_, ground - 2 + math.sin(a_) * d_ * .8)], 'spray' if k % 2 else 'drip')
        f.a[ellipsoid(gx, ground - 1, 11, 2.6)[0] & (f.a == 0) & (DITHER > -.1)] = p['drip']
    if clip != 'die' or n < 4:
        for k in range(3):                      # water running off the plate
            f.dots([(cx - 14 + rng.uniform(0, 30), ground - 8 - rng.uniform(0, 50))], 'drip')
    if clip == 'die' and n >= 4:
        for k in range(6 if n < 7 else 3):
            f.dots([(cx - 24 + rng.uniform(0, 60), ground - 3 - rng.uniform(0, 12))], 'drip' if k % 2 else 'spray')
        for k in range(4):
            f.dots([(cx - 10 + rng.uniform(0, 30), ground - 1 - rng.uniform(0, 3))], 'kelp1' if k % 2 else 'kelp2')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Mire Hydra: a heavy, low, bog-black body with three long necks and three snapping heads, violet underbellies and
# amber eyes. The heads strike one after another; dying, the necks fall limp over the body.
# ----------------------------------------------------------------------------------------------
HYDRA = Palette({
    'sc0': '#14161f', 'sc1': '#233040', 'sc2': '#33505a', 'sc3': '#4b7a74', 'sc4': '#78aa8a', 'sc5': '#b0d6a0',
    'far0': '#0e1018', 'far1': '#182230', 'far2': '#26404a', 'vi0': '#4a2a62', 'vi1': '#7a4a96', 'vi2': '#b08acb',
    'ridge0': '#2a1a3a', 'ridge1': '#9a5ac0', 'ridge2': '#d8a8f0', 'eye': '#ffb42e', 'eye2': '#fff0a0', 'socket': '#060810',
    'mouth': '#3a0f20', 'tongue': '#e0507a', 'tooth': '#f4f0dc', 'drool': '#9ae070', 'drip': '#7fd0e0', 'spray': '#c8ecf2',
    'mud': '#5a4a32',
})


def hydra(clip, n):
    f = Frame(HYDRA)
    p = HYDRA
    rng = rng_for('hydra', clip, n)
    cx, lift, squash, flash, eyes = 40., 0., 1., False, 'open'
    sway = n / 6 * 2 * math.pi
    # per neck: (reach dx, rise dy, head tilt, jaw); neck 0 is the front one, 2 the rear
    necks = [[0., 0., 0., 0.], [0., 0., 0., 0.], [0., 0., 0., 0.]]
    sag = 0.
    spray = 0.
    if clip == 'idle':
        for k in range(3):
            necks[k] = [math.sin(sway + k * 2.1) * 3, math.sin(sway * 2 + k) * 1.5, math.sin(sway + k) * .08, [0, .15, .3, .15, 0, 0][(n + k * 2) % 6]]
        squash = 1 + math.sin(sway) * .015
        eyes = 'blink' if n == 4 else 'open'
    elif clip == 'walk':
        lift = [0, 0, 3, 6, 3, 0, 0, 0][n]
        squash = [1, .96, 1.02, 1.04, 1.02, .9, .94, .98][n]
        for k in range(3):
            necks[k] = [[0, 1, 4, 6, 3, -3, -2, 0][(n - k) % 8], [0, 0, -1, -2, 0, 3, 2, 0][(n - k) % 8], 0, [0, 0, .3, .5, .3, 0, 0, 0][(n - k) % 8]]
    elif clip == 'attack':
        cx += [-1, -2, -2, 1, 2, 2, 1, 0][n]
        squash = [.98, .95, .93, 1.02, .98, .97, .99, 1][n]
        # heads strike in turn: front, middle, rear
        seq = [
            [[-2, 2, -.1, .2], [-1, 1, -.1, .1], [-1, 1, -.1, 0]],
            [[-4, 5, -.3, .2], [-3, 4, -.2, .2], [-2, 3, -.2, .1]],
            [[-6, 8, -.5, .3], [-4, 7, -.4, .3], [-3, 6, -.3, .2]],
            [[8, -8, .6, 1], [-2, 4, -.2, .3], [-3, 4, -.2, .2]],
            [[10, -13, .8, 1], [5, -7, .5, 1], [-2, 4, -.2, .3]],
            [[6, -6, .5, .8], [10, -13, .8, 1], [4, -6, .5, .8]],
            [[2, -1, .2, .4], [6, -6, .5, .6], [10, -12, .8, 1]],
            [[0, 1, 0, .2], [2, -1, .1, .2], [5, -4, .3, .5]],
        ][n]
        necks = [list(map(float, v)) for v in seq]
        eyes = 'angry'
        spray = 1. if n in (4, 5) else 0.
    elif clip == 'hurt':
        flash = n == 0
        cx += [-3, -2, -1, 0][n]
        squash = [.92, .95, .98, 1][n]
        for k in range(3):
            necks[k] = [[-5, -3, -2, 0][n] - k, [4, 2, 1, 0][n], [-.4, -.3, -.1, 0][n], [1, .7, .3, 0][n]]
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        sag = [0, .12, .35, .6, .82, 1, 1, 1][n]
        cx += [0, -1, 0, 1, 2, 2, 2, 2][n]
        squash = [1, .96, .9, .86, .82, .8, .8, .8][n]
        for k in range(3):
            necks[k] = [[0, -3, 2, 6, 9, 10, 10, 10][n] + k * 2, -[0, -2, 6, 18, 32, 44, 44, 44][n] + k * 3, [0, -.2, .1, .4, .6, .7, .7, .7][n], [1, .8, .5, .3, .3, .3, .3, .3][n]]
    ground = AY - lift
    cy = ground - 17 * squash
    ramp = p.ramp('sc0', 'sc1', 'sc2', 'sc3', 'sc4', 'sc5')
    far = p.ramp('far0', 'far1', 'far2')

    def legs(side):
        ramp_ = far if side == 'far' else ramp
        off = -5 if side == 'far' else 0
        for hx_, kind in ((cx + 15 + off, 'f'), (cx - 12 + off, 'b')):
            hip = (hx_, cy + 7)
            sw = math.sin(n / 8 * 2 * math.pi + (math.pi if kind == 'b' else 0) + (1.6 if side == 'far' else 0)) * 3 if clip == 'walk' else 0
            foot = (hip[0] + 3 + sw + sag * 5 * (1 if kind == 'f' else -1), ground - 1 - (max(0, sw) if clip == 'walk' else 0) * .6)
            knee = (hip[0] + 5, (hip[1] + foot[1]) / 2)
            f.paint(capsule(hip, knee, 5.6, 4.3), ramp_, dither=.4)
            f.paint(capsule(knee, (foot[0] - 1, foot[1] - 1), 4.3, 3.2), ramp_, dither=.4)
            f.paint(ellipsoid(foot[0] + 2, foot[1] - 1, 6.5, 2.7), ramp_, dither=.3)
            f.dots([(foot[0] + 8, foot[1] - 1), (foot[0] + 7, foot[1])], 'tooth' if side == 'near' else 'far2')

    # tail
    tail = smooth([(cx - 14, cy + 4), (cx - 21, cy + 6), (cx - 26, cy + 3 - 4 * (1 - sag)), (cx - 28, cy - 3 * (1 - sag) + 3 * sag)], 12)
    legs('far')
    discs = [ellipsoid(x, y, 6.2 * (1 - i / 14) + 1.4, 5.6 * (1 - i / 14) + 1.2) for i, (x, y) in enumerate(tail)]
    discs.append(ellipsoid(cx, cy, 24, 14.5 * squash ** .6))
    chain_paint(f, discs, ramp, dither=.6)
    body_m = discs[-1][0]
    # violet belly plates, warts and mud
    under = body_m & (YY > cy + 14.5 * squash ** .6 * .42)
    f.a[under & (DITHER > -.2)] = p['vi0']
    f.a[under & (YY > cy + 14.5 * squash ** .6 * .62) & (DITHER > -.1)] = p['vi1']
    for k in range(4):
        x = cx - 18 + k * 7
        f.line((x, cy + 14.5 * squash ** .6 * .45), (x + 1, cy + 14.5 * squash ** .6 * .95), 'vi2', 1)
    for k in range(12):
        r2 = rng_for('hydrawart', 'x', k)
        x, y = cx + r2.uniform(-20, 18), cy + r2.uniform(-11, 4) * squash
        if 0 <= int(y) < H and 0 <= int(x) < W and body_m[int(y), int(x)]:
            f.dots([(x, y), (x + 1, y)], 'sc5' if k % 3 else 'mud')
    # spines along the back
    for k in range(7):
        x = cx + 14 - k * 5
        top = cy - 13.5 * squash ** .6 + abs(x - cx) * .05 + 1
        sp = polygon([(x - 2.4, top + 3), (x + .5, top - 5), (x + 2.4, top + 3)])
        f.paint((sp, np.where(sp, .5 + .4 * (XX < x), 0)), p.ramp('ridge0', 'ridge1', 'ridge2'), dither=.2)
    # necks, rear first; each neck is one chain with its own outline, so the three stay distinct
    anchors = [(cx + 14, cy - 8 * squash), (cx + 4, cy - 12 * squash), (cx - 7, cy - 11 * squash)]
    heads = []
    for k in (2, 1, 0):
        dx, rise, tilt, jaw = necks[k]
        bx, by = anchors[k]
        reach = [6, 1, -7][k] + dx
        hx_ = bx + reach + 6
        hy_ = by - [34, 31, 26][k] - rise
        if sag:
            hy_ = min(hy_, ground - 7 + k)
        mid1 = (bx + 1 + dx * .2, by - (by - hy_) * .38)
        mid2 = (bx + reach * .55 + dx * .1, by - (by - hy_) * .72)
        pts = smooth([(bx, by + 2), mid1, mid2, (hx_, hy_)], 20)
        nd = [ellipsoid(x, y, 5.6 - 2.2 * i / 19 + .8, 5.2 - 2.0 * i / 19 + .8) for i, (x, y) in enumerate(pts)]
        chain_paint(f, nd, ramp if k != 2 else far, dither=.55)
        for i in range(1, 20, 3):
            x, y = pts[i]
            f.dots([(x + 3 - i * .08, y)], 'vi1')
        heads.append((k, hx_, hy_, tilt, jaw))
        # head
        d = (math.cos(tilt), math.sin(tilt))
        q = (-d[1], d[0])

        def at(a, b, hx_=hx_, hy_=hy_, d=d, q=q):
            return (hx_ + d[0] * a + q[0] * b, hy_ + d[1] * a + q[1] * b)
        hr = ramp if k != 2 else far
        open_a = jaw * .55
        jd = (math.cos(tilt + open_a), math.sin(tilt + open_a))
        jb = at(1, 3)
        jt = (jb[0] + jd[0] * 11, jb[1] + jd[1] * 11)
        if jaw > .25:
            f.flat(polygon([at(2, 1), at(12, 1.5), jt, jb]), 'mouth', outline=True)
            f.dots([((jt[0] + jb[0]) / 2 + 1, (jt[1] + jb[1]) / 2 - 1)], 'tongue')
            f.dots([(jt[0] - 1, jt[1] - 1), (jt[0] - 4, jt[1] - 1.5)], 'tooth')
            f.dots([(jt[0] - 2, jt[1] + 1)], 'drool')
        f.paint(capsule(jb, jt, 2.3, 1.6), p.ramp('vi0', 'vi1', 'vi2'), dither=.3)
        f.paint(ellipsoid(*at(1, -.5), 6.3, 5.0, tilt), hr, dither=.5)
        f.paint(capsule(at(3, 0), at(12, 1), 3.8, 2.5), hr, dither=.5)
        f.dots([at(12, 3), at(10, 3.4), at(8, 3.4)], 'tooth')
        f.dots([at(13, -.5)], 'socket')
        for fr in range(2):                                         # a crest of violet frills
            fp = polygon([at(-3 - fr * 2, -3), at(-10 - fr * 2, -7 + fr * 3), at(-4 - fr * 2, 0)])
            f.paint((fp, np.where(fp, .6, 0)), p.ramp('ridge0', 'ridge1', 'ridge2'), dither=.2)
        ex, ey = at(4, -2.2)
        if eyes == 'dead':
            eye_dead(f, ex, ey)
        elif eyes == 'blink':
            f.line((ex - 1.5, ey), (ex + 1.5, ey), 'socket', 1)
        else:
            f.flat(ellipsoid(ex, ey, 2.0, 1.7 if eyes != 'angry' else 1.2)[0], 'eye', outline=True, edge='socket')
            f.dots([(ex + .5, ey)], 'eye2')
    legs('near')
    if spray:
        for k in range(10):
            f.dots([(cx + 26 + rng.uniform(0, 14), ground - 2 - rng.uniform(0, 14))], 'spray' if k % 2 else 'drip')
    if clip == 'die' and n >= 4:
        for k in range(5 if n < 7 else 2):
            f.dots([(cx - 26 + rng.uniform(0, 62), ground - 3 - rng.uniform(0, 5))], 'drip' if k % 2 else 'mud')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Gloomroot Colossus (elite): a drowned willow grown into a giant. Bark body, a hollow chest that glows like the
# fen's mushrooms, a stump of a head with antler branches and hanging willow fronds, root-club fists, root feet.
# Heavy and slow: it stomps, raises both fists and slams them down, and falls apart into a heap of roots.
# ----------------------------------------------------------------------------------------------
GLOOMROOT = Palette({
    'bk0': '#120f0b', 'bk1': '#241b12', 'bk2': '#3a2b1c', 'bk3': '#573f27', 'bk4': '#7a5a38', 'bk5': '#a3835a',
    'ms0': '#142210', 'ms1': '#24401a', 'ms2': '#3c6a26', 'ms3': '#62953a', 'ms4': '#9bc85a',
    'gl0': '#0c5a52', 'gl1': '#18a597', 'gl2': '#4fe0c8', 'gl3': '#b8fff0',
    'fr0': '#1d3a2a', 'fr1': '#2f5e3d', 'fr2': '#4f8a55',
    'fu0': '#5a3d8a', 'fu1': '#8a64c8', 'fu2': '#c8a8f2',
    'eye': '#e8ff6a', 'eye2': '#fbffc0', 'socket': '#07100c', 'tooth': '#e6dcc0',
    'mud': '#2a1f14', 'drip': '#6fb0a0', 'spray': '#c4e8d8',
})


def gloomroot(clip, n):
    f = Frame(GLOOMROOT)
    p = GLOOMROOT
    rng = rng_for('gloomroot', clip, n)
    cx = 42.
    eyes, glow, flash, squash, lean, lift, rubble = 'open', 1., False, 1., 0., 0., 0.
    sway = n / 6 * 2 * math.pi
    fist_n, fist_f = (23., -27.), (-19., -29.)           # near (right) and far (left) fists, relative to the foot anchor
    step = 0.                                            # walking: -1..1, the near foot forward when positive
    breathe = 0.
    impact = 0
    wind = 0.                                            # fronds trail behind when it moves
    if clip == 'idle':
        breathe = [0, .6, 1.2, 1.2, .6, 0][n]
        glow = [.8, 1, 1.2, 1.3, 1.1, .9][n]
        fist_n = (23 + math.sin(sway) * .8, -27 + math.cos(sway) * 1.2)
        fist_f = (-19 - math.sin(sway) * .8, -29 + math.cos(sway) * 1.0)
        eyes = 'blink' if n == 4 else 'open'
        wind = math.sin(sway) * .6
    elif clip == 'walk':
        lift = [0, 0, 1, 2, 1, 0, 0, 0][n]
        step = [-1, -.5, .6, 1, .7, 0, -.8, -1][n]
        lean = [1, 1, 2, 3, 2, 0, -1, 0][n]
        squash = [1, 1, 1, 1, 1, .98, .96, .99][n]
        fist_n = (23 - step * 5, -27 + abs(step) * 1.5)
        fist_f = (-19 + step * 5, -29 + abs(step) * 1.5)
        glow = [1, 1.1, 1.2, 1.2, 1.1, 1, .9, .9][n]
        wind = [0, .3, .8, 1, .6, -.4, -.6, -.2][n]
    elif clip == 'attack':
        lean = [-2, -3, -4, 3, 8, 6, 2, 0][n]
        cx += [-1, -2, -3, 1, 3, 3, 2, 0][n]
        squash = [1, 1.02, 1.03, .98, .93, .95, .98, 1][n]
        glow = [1.3, 1.6, 1.9, 1.9, 1.6, 1.3, 1.1, 1][n]
        eyes = 'angry'
        impact = 1 if n in (4, 5) else 0
        fist_n = [(21, -33), (14, -56), (8, -69), (17, -60), (30, -9), (29, -8), (27, -20), (24, -28)][n]
        fist_f = [(-19, -30), (-13, -54), (-7, -67), (2, -58), (18, -11), (18, -12), (6, -22), (-14, -28)][n]
        wind = [0, -.5, -1, 1, 1.4, .8, 0, 0][n]
    elif clip == 'hurt':
        flash = n == 0
        lean = [-6, -4, -2, 0][n]
        cx += [-3, -2, -1, 0][n]
        squash = [.95, .97, .99, 1][n]
        glow = [1.9, 1.5, 1.2, 1][n]
        eyes = 'hurt' if n < 3 else 'angry'
        fist_n = [(14, -38), (18, -34), (21, -30), (23, -27)][n]
        fist_f = [(-12, -40), (-15, -35), (-17, -31), (-19, -29)][n]
        wind = [-1, -.6, -.2, 0][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        lean = [0, -4, -6, -2, 3, 5, 5, 5][n]
        rubble = [0, 0, .2, .5, .75, .92, 1, 1][n]
        squash = [1, .97, .92, .8, .62, .5, .45, .45][n]
        glow = [1.9, 1.3, 1., .7, .45, .25, .12, .05][n]
        fist_n = [(23, -27), (24, -25), (26, -20), (29, -13), (31, -8), (32, -5), (32, -4), (32, -4)][n]
        fist_f = [(-19, -29), (-20, -26), (-22, -20), (-25, -13), (-27, -8), (-28, -5), (-28, -4), (-28, -4)][n]
        wind = 0.
    ground = AY
    bark = p.ramp('bk0', 'bk1', 'bk2', 'bk3', 'bk4', 'bk5')
    bark_far = p.ramp('bk0', 'bk1', 'bk2', 'bk3')
    moss = p.ramp('ms0', 'ms1', 'ms2', 'ms3', 'ms4')
    frond = p.ramp('fr0', 'fr1', 'fr2')
    fungus = p.ramp('fu0', 'fu1', 'fu2')

    def place(base, k_=1.):
        x, y = base
        k = (-y) / 70
        return cx + x + lean * k * 1.5 * k_, ground + y * squash - lift

    def foot(sign, w):
        """Foot position and a lifted flag for the near (+1) or far (-1) leg."""
        fx = sign * 10 + w * 8 * sign
        up = max(0., w * sign) * 5
        return fx, -3 - up

    # ---- far leg and far arm sit behind the trunk
    legs = {}
    for sign, tone in ((-1, bark_far), (1, bark)):
        fx, fy = foot(sign, step)
        hip = place((sign * 7, -27 + breathe * .3))
        kneex = hip[0] + (fx - sign * 7) * .45 + sign * 3
        knee = (kneex, ground + (-15 + fy * .3 + 3) * squash - lift)
        ft = place((fx, fy))
        legs[sign] = (hip, knee, ft, tone)
    if rubble:
        for sign in (-1, 1):
            hip, knee, ft, tone = legs[sign]
            t = rubble
            legs[sign] = ((hip[0], lerp(hip[1], ground - 6, t)), (lerp(knee[0], cx + sign * 14, t), lerp(knee[1], ground - 3, t)), (lerp(ft[0], cx + sign * 22, t), lerp(ft[1], ground - 2, t)), tone)

    def draw_leg(sign):
        hip, knee, ft, tone = legs[sign]
        thigh = capsule(hip, knee, 6.4, 5.2)
        shin = capsule(knee, ft, 5.0, 4.0)
        chain_paint(f, [thigh, shin], tone, dither=.55)
        # a broad root foot with three toes gripping the ground
        fm = ellipsoid(ft[0] + 2, ground - 3 + (ft[1] - ground) * .4, 8.5, 3.6)
        f.paint(fm, tone, dither=.5)
        for t_ in (-1, 0, 1):
            f.paint(capsule((ft[0] + 5, ft[1] - 1), (ft[0] + 11 + t_ * 2, ft[1] + 1.5 + t_ * 1.4), 2.4, 1.2), tone, dither=.4)

    def draw_arm(sign, fist, hid):
        sh = place((sign * 14.5, -52 + breathe * .5), 1.)
        fh = place(fist) if not rubble else (lerp(place(fist)[0], cx + sign * 24, rubble * .3), place(fist)[1])
        fh = (fh[0], min(fh[1], ground - 8))
        mid = ((sh[0] + fh[0]) / 2 + sign * 3.5, (sh[1] + fh[1]) / 2 + 5)
        tone = bark_far if hid else bark
        upper = capsule(sh, mid, 6.2, 5.0)
        lower = capsule(mid, fh, 5.0, 5.6)
        chain_paint(f, [upper, lower], tone, dither=.55)
        # the club of roots at the end of the arm
        fm = ellipsoid(fh[0], fh[1] + 1, 7.6, 7.0)
        f.paint(fm, tone, dither=.55)
        for k in range(3):
            a = (-.7 + k * .7) + (0 if sign > 0 else math.pi)
            f.paint(capsule((fh[0], fh[1] + 2), (fh[0] + math.cos(a) * 9, fh[1] + 2 + math.sin(a) * 3 + 3), 2.6, 1.3), tone, dither=.4)
        f.dots([(fh[0] - 3, fh[1] - 2), (fh[0] - 2, fh[1] - 2), (fh[0] + 2, fh[1] + 2)], 'ms2' if sign > 0 else 'ms1')
        return fh

    draw_arm(-1, fist_f, True)
    draw_leg(-1)

    # ---- fronds trailing from the shoulders and the crown (behind the trunk)
    def fronds(origin, count, length, spread, seed):
        for k in range(count):
            r2 = rng_for('gloomfrond' + seed, 'x', k)
            ox = origin[0] + (k - (count - 1) / 2) * spread
            pts = []
            for i in range(9):
                u = i / 8
                pts.append((ox - wind * 3 * u * u - u * 2.5 + math.sin(sway * 1.0 + k + u * 3) * .8 * u, origin[1] + u * length * (.8 + .4 * r2.random())))
            discs = [ellipsoid(x, y, 1.7 - .7 * (i / 8), 2.1 - .6 * (i / 8)) for i, (x, y) in enumerate(pts)]
            chain_paint(f, discs, frond, dither=.35)

    if not rubble:
        fronds(place((-12, -56)), 3, 24 * squash, 4.0, 'a')
        fronds(place((17, -56)), 3, 20 * squash, 4.0, 'b')

    # ---- trunk: belly, chest, shoulders
    trunk_c = place((0, -41 + breathe * .4))
    trunk = ellipsoid(trunk_c[0], trunk_c[1], 16.5, 21 * squash ** .8)
    belly = ellipsoid(*place((0, -29)), 14, 10 * squash ** .8)
    sh_n = ellipsoid(*place((14.5, -52 + breathe * .5)), 8.4, 7.4)
    sh_f = ellipsoid(*place((-14.5, -52 + breathe * .5)), 8.4, 7.4)
    chain_paint(f, [belly, trunk, sh_f, sh_n], bark, dither=.6)
    union = belly[0] | trunk[0] | sh_f[0] | sh_n[0]
    # bark fissures, knots and moss
    for k in range(7):
        x0 = trunk_c[0] - 13 + k * 4.4
        f.a[union & (np.abs(XX - x0 - (YY - trunk_c[1]) * .08) < .55) & (YY > trunk_c[1] - 19 * squash) & (YY < trunk_c[1] + 23 * squash) & (DITHER > -.25)] = p['bk1']
    for k in range(5):
        r2 = rng_for('gloombark', 'x', k)
        x, y = trunk_c[0] + r2.uniform(-12, 12), trunk_c[1] + r2.uniform(-17, 17) * squash
        if 0 <= int(y) < H and 0 <= int(x) < W and union[int(y), int(x)]:
            f.a[ellipsoid(x, y, 2.6, 3.4)[0] & union] = p['bk0']
            f.dots([(x - 1, y - 1)], 'bk4')
    top_lit = union & (YY < trunk_c[1] - 14 * squash + (XX - trunk_c[0]) * .35) & (XX < trunk_c[0] + 2) & (DITHER > -.35)
    f.a[top_lit] = p['ms2']
    f.a[top_lit & (DITHER > .1)] = p['ms3']
    f.a[union & (YY > ground - 14) & (DITHER > .25)] = p['ms1']
    # the hollow chest: a dark cavity with a glowing heart of fungus
    if not rubble or rubble < .6:
        cav = ellipsoid(trunk_c[0] + 2.5, trunk_c[1] - 1, 6.6, 10.5 * squash ** .8)
        f.paint(cav, p.ramp('socket', 'bk0'), outline=True, edge='bk0', dither=.1)
        heart = ellipsoid(trunk_c[0] + 2.5, trunk_c[1] + 1, 3.8 * glow ** .4, 6.2 * squash ** .8 * glow ** .3)
        f.paint(heart, p.ramp('gl0', 'gl1', 'gl2', 'gl3'), outline=False, dither=.35)
        for k in range(3):
            f.dots([(trunk_c[0] + 1 + k * 2.2, trunk_c[1] - 6 - (k % 2) * 3)], 'gl2')
    # bracket fungus on the shoulders
    for (bx, by, size) in ((-18, -57, 4.2), (-12, -59, 3.2), (19, -56, 4.6), (13, -59, 3.4), (-3, -26, 3.6)):
        c = place((bx, by))
        f.paint(ellipsoid(c[0], c[1], size, size * .55), fungus, dither=.4)
        f.dots([(c[0] - size * .4, c[1] - 1), (c[0] + size * .5, c[1])], 'gl2' if glow > 1 else 'fu2')

    draw_leg(1)

    # ---- head: a stump with a brow, glowing eyes, a canopy of leaves and antler branches
    head_c = place((7, -68 + breathe * .6), 1.4)
    hr = (10.6, 9.4 * squash ** .8)
    if not rubble:
        fronds((head_c[0] - 8, head_c[1] - 2), 4, 24 * squash, 3.4, 'c')        # willow fronds hang behind the head and down the back
    for sign in (-1, 1):
        base = (head_c[0] + sign * 6, head_c[1] - 6)
        tip = (head_c[0] + sign * (13 + 1.5 * glow) + lean * .3, head_c[1] - 10 * squash - 2)
        mid = (base[0] + sign * 5, base[1] - 3)
        f.paint(capsule(base, mid, 2.8, 2.2), bark, dither=.5)
        f.paint(capsule(mid, tip, 2.2, 1.0), bark, dither=.5)
        if not rubble:
            f.paint(ellipsoid(tip[0], tip[1] - 1, 3.2, 2.6), moss, dither=.45)
            f.dots([(tip[0] + sign, tip[1] - 1)], 'gl2')
    f.paint(ellipsoid(head_c[0], head_c[1], *hr), bark, dither=.6)
    hm = ellipsoid(head_c[0], head_c[1], *hr)[0]
    if not rubble:
        for (dx_, dy_, rx_, ry_) in ((-4, -8.5, 9.5, 4.2), (5, -8, 7, 3.4), (-9, -5, 4.6, 3.2)):
            f.paint(ellipsoid(head_c[0] + dx_, head_c[1] + dy_, rx_, ry_), moss, dither=.5)
    f.a[hm & (YY < head_c[1] - 5) & (DITHER > -.1)] = p['ms2']
    brow = polygon([(head_c[0] - 7, head_c[1] - 2.4), (head_c[0] + 10.5, head_c[1] - 3.6), (head_c[0] + 10.5, head_c[1] - 1.2), (head_c[0] - 7, head_c[1] + .2)])
    f.a[brow & hm] = p['bk0']
    for ex in (head_c[0] + 2, head_c[0] + 7.6):
        ey = head_c[1] + .4
        if eyes == 'dead':
            f.dots([(ex - 1, ey - 1), (ex + 1, ey + 1), (ex + 1, ey - 1), (ex - 1, ey + 1)], 'bk4')
        elif eyes == 'blink':
            f.line((ex - 1.5, ey), (ex + 1.5, ey), 'socket', 1)
        else:
            h_ = 1.2 if eyes == 'angry' else 2.0
            f.flat(ellipsoid(ex, ey, 2.3, h_)[0], 'eye', outline=True, edge='socket')
            f.dots([(ex + .6, ey)], 'eye2')
            if glow > 1.4:
                f.dots([(ex, ey - 2.6), (ex + 1, ey + 2.6)], 'gl2')
    jaw = 2.2 if (clip == 'attack' and n in (3, 4, 5)) else 1.1
    f.a[polygon([(head_c[0] + 1.5, head_c[1] + 4.6), (head_c[0] + 10, head_c[1] + 4), (head_c[0] + 9, head_c[1] + 4.6 + jaw * 1.5), (head_c[0] + 2.5, head_c[1] + 4.8 + jaw * 1.5)]) & hm] = p['socket']
    f.dots([(head_c[0] + 4, head_c[1] + 5), (head_c[0] + 7.4, head_c[1] + 4.8)], 'tooth')

    draw_arm(1, fist_n, False)

    # ---- effects
    if impact:
        gx = cx + 27 + lean * .3
        for k in range(5):                       # roots bursting from the ground
            bx = gx - 12 + k * 6 + rng.uniform(-1, 1)
            hgt = [10, 17, 22, 15, 9][k] * (1 if n == 4 else .8)
            sp = polygon([(bx - 3.2, ground), (bx + .6 * (k - 2), ground - hgt), (bx + 3.2, ground)])
            f.paint((sp, np.where(sp, .55 + .4 * (XX < bx), 0)), p.ramp('bk1', 'bk2', 'bk3', 'bk4'), dither=.2)
        for k in range(12):
            a_ = rng.uniform(-3.1, 0)
            d_ = rng.uniform(5, 13) * (1 if n == 4 else 1.15)
            f.dots([(gx + math.cos(a_) * d_, ground - 2 + math.sin(a_) * d_ * .8)], 'spray' if k % 2 else 'mud')
        f.a[ellipsoid(gx, ground - 1, 13, 2.8)[0] & (f.a == 0) & (DITHER > -.1)] = p['drip']
    if clip != 'die':
        for k in range(3):                       # swamp water running off the bark
            f.dots([(cx - 12 + rng.uniform(0, 28), ground - 6 - rng.uniform(0, 48))], 'drip')
    if clip == 'idle' or clip == 'walk':
        for k in range(3):                       # spores drifting from the fungus
            u = (n / 6 + k / 3) % 1
            f.dots([(cx - 14 + k * 16 + math.sin(u * 6 + k) * 3, ground - 62 - u * 18)], 'gl2' if k % 2 else 'gl3')
    if clip == 'die' and n >= 3:
        for k in range(6 + n):
            u = (n - 2) / 5
            f.dots([(cx - 22 + rng.uniform(0, 50), ground - 10 - rng.uniform(0, 28) * u - rng.uniform(0, 6))], 'gl3' if k % 3 == 0 else 'gl2')
        for k in range(6 if n < 7 else 3):
            f.dots([(cx - 26 + rng.uniform(0, 60), ground - 2 - rng.uniform(0, 4))], 'drip' if k % 2 else 'mud')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_crag_sprites.py)
# ----------------------------------------------------------------------------------------------
DRAWERS = {k: pair for k, pair in {'toad': (globals().get('toad'), globals().get('TOAD')), 'croc': (globals().get('croc'), globals().get('CROC')),
                                   'knight': (globals().get('knight'), globals().get('KNIGHT')), 'hydra': (globals().get('hydra'), globals().get('HYDRA')),
                                   'gloomroot': (globals().get('gloomroot'), globals().get('GLOOMROOT'))}.items()
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


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        for problem in bounds_report(kind, frames):
            print(f'  EDGE {kind} {problem}')
        for clip, grids in frames.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#2a3a2c')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def ids():
    meta = ASSETS / 'fen.txt'
    return json.loads(meta.read_text()).get('sprites', {}) if meta.exists() else {}


def build(kinds, replace=False):
    meta_path = ASSETS / 'fen.txt'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in fen.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = DRAWERS[kind][1].hex
        np.savez_compressed(RAW / f'fen_{kind}_raw.npz', **frames)
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
        meta_path.write_text(json.dumps(meta, indent=2) + '\n')


def export(kinds):
    meta_path = ASSETS / 'fen.txt'
    meta = json.loads(meta_path.read_text())
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
            dest = ROOT / 'test-results/fen-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'fen_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved}
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/fen_<kind>.png and fen.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        atlas = Image.open(ASSETS / f'fen_{kind}.png').convert('RGBA')
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * W, row * H, (n + 1) * W, (row + 1) * H))
                if np.array(cell).tobytes() != np.array(rgba(frames[clip][n], palette)).tobytes():
                    raise SystemExit(f'{kind} {clip} {n} differs from the render')
        print(kind, 'atlas is pixel-identical to the render')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    names = [a for a in sys.argv[2:] if a in DRAWERS] or list(DRAWERS)
    if command == 'build':
        build(names, '--replace' in sys.argv)
    elif command == 'export':
        export(names)
    elif command == 'verify':
        verify(names)
    elif command == 'preview':
        directory = next((a for a in sys.argv[2:] if a not in DRAWERS and not a.startswith('--')), ROOT / 'test-results/fen-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_fen_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...]')
