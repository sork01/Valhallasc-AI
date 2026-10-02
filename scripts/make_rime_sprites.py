#!/usr/bin/env python3
"""makesprites workflow for the Rimeveil Glacier monsters: preview | build [--replace] | export.

Four kinds (crab, wolf, yeti, wyrm) share the Emberfall Crags contract (scripts/make_crag_sprites.py): one 96x96 frame,
a foot anchor at (48, 90), right-facing art (the game mirrors it) and five clips (idle 6, walk 8, attack 8, hurt 4,
die 8) so client/field.js drives them with the Ironhide's state machine: walk frames 2-4 are the hop, 5-7 the landing,
attack 0-2 the windup, 3-5 the lunge, 6-7 the recovery.

The drawing toolkit (shaded ellipsoids and capsules lit from the upper left, a dithered ramp per material, an outline
around every part) is imported from make_crag_sprites.py. `build` saves ONE new 34-frame PixelFlow sprite per kind
(valhallasc_rime_<kind>_all) and refuses existing names unless --replace is given. `export` reads the editor frames
back, so edits survive, and writes client/assets/rime_<kind>.png plus rime.txt.
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
PREFIX = 'valhallasc_rime_'
KINDS = ['crab', 'wolf', 'yeti', 'wyrm']
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


# ----------------------------------------------------------------------------------------------
# Rime Crab: an ice-crusted shell, two big claws, eight legs, eyes on stalks.
# ----------------------------------------------------------------------------------------------
CRAB = Palette({
    'sh0': '#16304f', 'sh1': '#21507f', 'sh2': '#3280b4', 'sh3': '#5db3dc', 'sh4': '#9adcf2', 'sh5': '#dff6ff',
    'far0': '#10243b', 'far1': '#183855', 'far2': '#25577d', 'frost': '#f2fbff', 'frost2': '#bfe6f8',
    'belly': '#9bb7c9', 'socket': '#0a1626', 'eye': '#e8fdff', 'pupil': '#2fd8ff', 'mouth': '#0d1a2e',
    'shard': '#c8efff', 'shard2': '#7cc4e6', 'puff': '#d6eefc',
})
CRAB_HIPS = [-16, -6, 5, 15]


def crab(clip, n):
    f = Frame(CRAB)
    p = CRAB
    rng = rng_for('crab', clip, n)
    cx, lift, squash = 37, 0., 1.
    claw_open, claw_raise, reach, eyes, flash, tuck = .35, 0., 0., 'open', False, 0.
    curl, droop, sag = 0., 0., 0.
    gait = n / 8 * 2 * math.pi
    snap = 0.
    if clip == 'idle':
        squash = [1, 1.02, 1.04, 1.02, 1, .98][n]
        claw_open = [.3, .4, .55, .4, .3, .2][n]
        claw_raise = [0, .05, .1, .05, 0, 0][n]
        eyes = 'blink' if n == 3 else 'open'
    elif clip == 'walk':
        lift = [0, 0, 6, 12, 7, 0, 0, 0][n]
        squash = [1, 1, 1.05, 1.08, 1.04, .86, .92, .97][n]
        tuck = [0, 0, .6, 1, .7, 0, 0, 0][n]
        claw_raise = [0, 0, .3, .5, .3, 0, 0, 0][n]
        claw_open = [.3, .3, .6, .8, .6, .2, .2, .3][n]
        reach = [0, 0, 1, 2, 1, 0, 0, 0][n]
    elif clip == 'attack':
        cx += [-2, -3, -4, 4, 8, 7, 3, 0][n]
        squash = [.96, .9, .86, 1.04, .95, .94, .98, 1][n]
        claw_raise = [.5, .9, 1.2, .2, -.1, 0, .1, 0][n]
        claw_open = [.6, .9, 1, 1, .1, .1, .3, .35][n]
        reach = [0, -1, -2, 2, 3, 3, 1, 0][n]
        snap = 1. if n in (4, 5) else 0.
        eyes = 'angry'
        lift = [0, 0, 0, 3, 1, 0, 0, 0][n]
    elif clip == 'hurt':
        flash = n == 0
        cx += [-4, -3, -1, 0][n]
        squash = [.88, .93, .98, 1][n]
        claw_open = [1, .8, .5, .35][n]
        claw_raise = [.6, .4, .2, 0][n]
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        cx += [0, -1, -1, 0, 1, 2, 2, 2][n]
        sag = [0, .1, .35, .6, .85, 1, 1, 1][n]
        curl = [0, 0, .3, .6, .9, 1, 1, 1][n]
        droop = sag
        squash = [1, .97, .92, .86, .8, .76, .76, .76][n]
        claw_open = [1, .9, .6, .3, .2, .1, .1, .1][n]
    cy = AY - 24 - lift + sag * 7
    rx, ry = 22 / squash ** .5, 15 * squash
    claw_raise += .45 * (1 - sag)

    def leg(hx, side):
        hip = (cx + hx * (1.05 if side == 'near' else .9) * (squash ** -.25), cy + ry * .55)
        out = 1 if hx > 0 else -1
        phase = gait + (math.pi if CRAB_HIPS.index(hx) % 2 else 0) + (math.pi / 2 if side == 'far' else 0)
        walking = clip == 'walk'
        foot = (hip[0] + out * 9 + (math.cos(phase) * 3 if walking and lift == 0 else 0), AY - 1 - lift * (.75 + .1 * tuck))
        knee = (hip[0] + out * 6, min(hip[1] + 5, foot[1] - 7) - (3 if side == 'far' else 0) - tuck * 3)
        if curl:
            foot = (lerp(foot[0], hip[0] + out * 5, curl), lerp(foot[1], cy - ry - 6 - (hx % 3), curl))
            knee = (lerp(knee[0], hip[0] + out * 12, curl), lerp(knee[1], cy - ry * .2, curl))
        return hip, knee, foot

    for side, ramp in (('far', ('far0', 'far1', 'far2')), ('near', ('sh0', 'sh1', 'sh2', 'sh3'))):
        for hx in CRAB_HIPS:
            hip, knee, foot = leg(hx, side)
            f.paint(capsule(hip, knee, 2.4, 1.9), p.ramp(*ramp), dither=.3)
            f.paint(capsule(knee, foot, 1.9, .9), p.ramp(*ramp), dither=.3)
        if side == 'far':
            # the far claw hangs behind the shell
            far_c = (cx + 22 + reach * .6, cy - 9 - claw_raise * 9 + droop * 16)
            elbow = (cx + 16, cy - 2 + droop * 10)
            f.paint(capsule(elbow, far_c, 3.2, 2.6), p.ramp('far0', 'far1', 'far2'), dither=.3)
            f.paint(ellipsoid(far_c[0] + 2, far_c[1], 6.5, 5.5), p.ramp('far0', 'far1', 'far2'), dither=.3)
            f.paint(capsule((far_c[0] + 4, far_c[1] - 2), (far_c[0] + 10, far_c[1] - 3 - claw_open * 5), 2.6, .8), p.ramp('far0', 'far1', 'far2'), dither=.2)
            f.paint(capsule((far_c[0] + 4, far_c[1] + 2), (far_c[0] + 9, far_c[1] + 2 + claw_open * 3), 2.4, .8), p.ramp('far0', 'far1', 'far2'), dither=.2)
    # frost spikes on the back
    for k, (dx, hgt, w) in enumerate([(-15, 11, 4.5), (-8, 15, 5), (0, 12, 5), (8, 9, 4)]):
        bx, by = cx + dx, cy - ry * (.86 - abs(dx) / 60) + 2
        sp = polygon([(bx - w, by + 2), (bx + 1 + (k % 2), by - hgt * (1 - sag * .5)), (bx + w, by + 2)])
        f.paint((sp, np.where(sp, .35 + .55 * (YY < by - hgt * .4), 0)), p.ramp('sh1', 'sh3', 'sh4', 'frost'), dither=.2)
    body = ellipsoid(cx, cy, rx, ry)
    f.paint(body, p.ramp('sh0', 'sh1', 'sh2', 'sh3', 'sh4', 'sh5'), dither=.6)
    belly = ellipsoid(cx, cy + ry * .55, rx * .9, ry * .45)
    f.a[belly[0] & body[0] & (YY > cy + ry * .5)] = p['belly']
    speckle = body[0] & (YY < cy - 1) & (DITHER > .22) & (((XX * 3 + YY * 7).astype(int) % 11) == 0)
    f.a[speckle] = p['frost']
    # shell ridges
    for k in (-1, 0, 1):
        f.line((cx + k * 9 - 3, cy - ry * .55), (cx + k * 9 + 2, cy + ry * .25), 'sh1', 1)
    # eyes on stalks
    for k, (dx, h) in enumerate([(11, 9), (18, 10)]):
        base = (cx + dx, cy - ry * .75)
        top = (cx + dx + 2 + reach * .3, cy - ry * .75 - h * (1 - sag * .6) + sag * 3)
        f.paint(capsule(base, top, 1.6, 1.3), p.ramp('sh1', 'sh2', 'sh3'), dither=.2)
        if eyes == 'dead':
            eye_dead(f, top[0], top[1] - 1)
        elif eyes == 'blink':
            f.line((top[0] - 2, top[1]), (top[0] + 2, top[1]), 'socket', 1)
        else:
            f.paint(ellipsoid(top[0], top[1] - 1, 3.3, 3.3), p.ramp('sh3', 'eye', 'frost'), dither=.2)
            f.dots([(top[0] + 1, top[1] - 1)], 'pupil')
            if eyes == 'angry':
                f.line((top[0] - 3, top[1] - 4 + (1 if k == 0 else 0)), (top[0] + 3, top[1] - 4 + (0 if k == 0 else 1)), 'socket', 1)
    # mouth plates
    f.line((cx + rx * .72, cy + 1), (cx + rx * .72 + 3, cy + 4), 'mouth', 1)
    # near claw
    shoulder = (cx + rx * .75, cy)
    claw = (cx + 32 + reach - claw_raise * 2 - droop * 4, cy - 4 - claw_raise * 17 + droop * 12 - snap * 1)
    elbow = (cx + 27 + reach * .5, cy - 1 - claw_raise * 6 + droop * 10)
    f.paint(capsule(shoulder, elbow, 4.2, 3.6), p.ramp('sh0', 'sh1', 'sh2', 'sh3', 'sh4'), dither=.45)
    f.paint(capsule(elbow, claw, 3.8, 3.4), p.ramp('sh0', 'sh1', 'sh2', 'sh3', 'sh4'), dither=.45)
    f.paint(ellipsoid(claw[0] + 1, claw[1], 9.5, 7.8, -.1 * claw_raise), p.ramp('sh0', 'sh1', 'sh2', 'sh3', 'sh4', 'sh5'), dither=.55)
    upper = (claw[0] + 14, claw[1] - 5 - claw_open * 9)
    lower = (claw[0] + 12, claw[1] + 5 + claw_open * 4)
    f.paint(capsule((claw[0] + 3, claw[1] - 4), upper, 3.8, 1), p.ramp('sh1', 'sh2', 'sh3', 'sh4', 'frost'), dither=.35)
    f.paint(capsule((claw[0] + 3, claw[1] + 4), lower, 3.4, 1), p.ramp('sh0', 'sh1', 'sh2', 'sh3'), dither=.35)
    f.dots([(upper[0] - 3, upper[1] + 2), (upper[0] - 6, upper[1] + 3), (lower[0] - 3, lower[1] - 2), (lower[0] - 6, lower[1] - 3)], 'frost')
    if snap:
        for k in range(5):
            a = rng.uniform(-1.2, 1.2)
            f.dots([(upper[0] + 4 + math.cos(a) * rng.uniform(3, 10), (upper[1] + lower[1]) / 2 + math.sin(a) * rng.uniform(2, 10))], 'shard' if k % 2 else 'frost')
    if clip == 'die' and n >= 3:
        for k in range(6 if n < 7 else 3):
            f.dots([(cx - 22 + rng.uniform(0, 44), AY - 8 - rng.uniform(0, 26 if n < 6 else 12))], 'shard' if k % 2 else 'shard2')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Frostfang Wolf: a lean slate-and-white wolf with an ice crest along the spine, glowing eyes, long fangs.
# ----------------------------------------------------------------------------------------------
WOLF = Palette({
    'fur0': '#1f2a40', 'fur1': '#35476a', 'fur2': '#5d7699', 'fur3': '#90a9c6', 'fur4': '#cbdbea', 'fur5': '#f3f8fc',
    'far0': '#141c2c', 'far1': '#222f48', 'far2': '#394b6b', 'ice0': '#6fbfe4', 'ice1': '#bdeaff', 'ice2': '#effaff',
    'eye': '#8ff3ff', 'eye2': '#ffffff', 'nose': '#10131c', 'mouth': '#4a1424', 'tongue': '#d84a6c', 'tooth': '#fbfdff',
    'claw': '#dfe9f2', 'socket': '#0a0f1a', 'puff': '#dcecf8', 'snow': '#e9f4fc',
})


def wolf(clip, n):
    f = Frame(WOLF)
    p = WOLF
    rng = rng_for('wolf', clip, n)
    cx, crouch, lift, tilt, flash = 40., 0., 0., 0., False
    stretch, jaw, ears, eyes = 0., 0., 0., 'open'
    head_dx, head_dy, tail_up, breathe, lie = 0., 0., 0., 0., 0.
    pounce = 0.
    if clip == 'idle':
        breathe = [0, .4, .8, .4, 0, -.4][n]
        head_dy = [0, -.5, -1, -.5, 0, .5][n]
        tail_up = [0, 1.5, 3, 1.5, 0, -1.5][n]
        ears = [0, 0, .4, 0, 0, 0][n]
        eyes = 'blink' if n == 3 else 'open'
        jaw = [0, 0, .1, .1, 0, 0][n]
    elif clip == 'walk':
        lift = [0, 0, 6, 11, 6, 0, 0, 0][n]
        stretch = [0, .2, .7, 1, .3, -.7, -.3, 0][n]
        crouch = [0, 0, 0, 0, 0, 6, 4, 1][n]
        tilt = [0, 0, -.08, -.12, .05, .08, .04, 0][n]
        tail_up = [0, 0, 3, 5, 3, -1, 0, 0][n]
        head_dy = [0, 0, -2, -3, -1, 3, 2, 0][n]
        ears = [0, 0, .5, .8, .5, 0, 0, 0][n]
    elif clip == 'attack':
        crouch = [3, 7, 10, 0, 0, 1, 2, 1][n]
        cx += [0, -1, -1, 0, 1, 1, 0, 0][n]
        tilt = [.05, .1, .14, -.14, -.1, -.03, 0, 0][n]
        head_dx = [-2, -3, -5, 2, 3, 2, 1, 0][n]
        head_dy = [2, 5, 8, -1, 3, 3, 1, 0][n]
        jaw = [.1, .2, .1, 1, 1, .8, .4, .15][n]
        ears = [.6, 1, 1, 1, 1, .8, .4, .2][n]
        stretch = [-.2, -.4, -.5, 1, .8, .2, 0, 0][n]
        lift = [0, 0, 0, 4, 2, 0, 0, 0][n]
        tail_up = [3, 5, 6, -2, -3, 0, 2, 2][n]
        eyes = 'angry'
        pounce = 1. if n in (3, 4) else 0.
    elif clip == 'hurt':
        flash = n == 0
        cx += [-1, -1, 0, 0][n]
        crouch = [4, 3, 1, 0][n]
        tilt = [.12, .08, .03, 0][n]
        head_dy = [-4, -3, -1, 0][n]
        head_dx = [-3, -2, -1, 0][n]
        jaw = [.9, .7, .3, 0][n]
        ears = [1, .8, .4, 0][n]
        eyes = 'hurt' if n < 3 else 'angry'
        tail_up = [4, 3, 1, 0][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        lie = [0, .1, .35, .6, .85, 1, 1, 1][n]
        cx += [0, -1, 0, 0, 0, 1, 1, 1][n]
        tilt = [.1, .15, .1, .05, 0, 0, 0, 0][n]
        head_dy = [-3, -2, 2, 6, 10, 12, 12, 12][n]
        jaw = [.9, .6, .3, .2, .3, .3, .3, .3][n]
        ears = [1, 1, 1, 1, 1, 1, 1, 1][n]
        stretch = [0, 0, .2, .5, .8, 1, 1, 1][n]
        tail_up = [0, -2, -4, -6, -8, -9, -9, -9][n]
    cy = AY - 33 + crouch - lift + lie * 21
    ry = 11 * (1 + breathe * .04) * (1 - lie * .28)
    ct, st = math.cos(tilt), math.sin(tilt)

    def body(dx, dy):
        return cx + dx * ct - dy * st, cy + dx * st + dy * ct

    fur = p.ramp('fur0', 'fur1', 'fur2', 'fur3', 'fur4', 'fur5')
    far = p.ramp('far0', 'far1', 'far2')
    leglift = lift * .9

    def paws(side):
        out = []
        spec = [(14, 6, 15, 1), (-12, 5, -11, -1)] if side == 'near' else [(10, 6, 12, 1), (-16, 5, -15, -1)]
        for k, (hx, hy, fx, kind) in enumerate(spec):
            sign = 1 if kind > 0 else -1
            reach = 10 * stretch * sign * (1 if side == 'near' else .85)
            if side == 'far':
                reach += 2.5 * sign
            hip = body(hx, hy)
            foot = (cx + fx + reach, AY - 2 - leglift * (1 if stretch > .3 else .6) - (3 if side == 'far' and clip == 'walk' else 0))
            if lie:
                foot = (lerp(foot[0], cx + fx + 13 * sign * (1 if side == 'near' else .7), lie), lerp(foot[1], AY - 3 - (2 if side == 'far' else 0), lie))
            out.append((hip, foot, kind))
        return out

    def draw_leg(hip, foot, kind, ramp, thick):
        mid = ((hip[0] + foot[0]) / 2, (hip[1] + foot[1]) / 2)
        if kind > 0:
            knee = (mid[0] + 1, mid[1] + 1)
            f.paint(capsule(hip, knee, thick + 1.4, thick - .2), ramp, dither=.4)
            f.paint(capsule(knee, (foot[0], foot[1] - 2), thick - .2, thick - 1.1), ramp, dither=.4)
        else:
            knee = (mid[0] + 6 * (1 - lie), mid[1] - 1)
            hock = (foot[0] - 3 * (1 - lie), max(foot[1] - 11 * (1 - lie), hip[1] + 4))
            f.paint(capsule(hip, knee, thick + 2.6, thick), ramp, dither=.4)
            f.paint(capsule(knee, hock, thick, thick - .7), ramp, dither=.4)
            f.paint(capsule(hock, (foot[0], foot[1] - 2), thick - .7, thick - 1.2), ramp, dither=.4)
        f.paint(ellipsoid(foot[0] + 1.5, foot[1] - 1.5, thick + 2, 2.9), ramp, dither=.3)
        f.dots([(foot[0] + 4, foot[1]), (foot[0] + 3, foot[1] + 1)], 'claw')

    # tail
    base = body(-21, -3)
    tail = smooth([base, (base[0] - 5, base[1] - 3 - tail_up * .3), (base[0] - 10, base[1] - 7 - tail_up * .6), (base[0] - 13, base[1] - 4 - tail_up * 1.0 + 9 * lie)], 24)
    discs = []
    for i, (x, y) in enumerate(tail):
        t = i / 23
        r = 2.4 + 2.8 * math.sin(math.pi * min(1, t * 1.2)) + (1 - t) * 1.4
        discs.append(ellipsoid(x, y, r + .8, r))
    union = np.zeros((H, W), bool)
    for m, _ in discs:
        union |= m
    ring = mc.dilate(union) & ~union          # one outline round the whole tail, not one per disc
    f.a[ring] = p['ol']
    for shape in discs:
        f.paint(shape, fur, outline=False, dither=.5)
    # far legs first
    for hip, foot, kind in paws('far'):
        draw_leg(hip, foot, kind, far, 2.8)
    # body
    haunch = ellipsoid(*body(-12, 1), 12, ry, tilt)
    f.paint(haunch, fur, dither=.55)
    chest = ellipsoid(*body(12, -1), 11.5, ry + .5, tilt)
    f.paint(chest, fur, dither=.55)
    torso = ellipsoid(*body(0, 0), 19, ry, tilt)
    f.paint(torso, fur, dither=.55)
    # pale belly and chest fur
    belly = (torso[0] | chest[0] | haunch[0]) & (YY > cy + ry * .55) & (YY < cy + ry + 1)
    f.a[belly & (DITHER > -.05)] = p['fur4']
    # frost crest along the spine
    for k, (dx, h) in enumerate([(-12, 4), (-6, 6), (0, 5), (6, 6), (11, 4)]):
        bx, by = body(dx, -ry + 1.5)
        sp = polygon([(bx - 2.2, by + 2), (bx + 1 - tilt * 4, by - h), (bx + 2.2, by + 2)])
        f.paint((sp, np.where(sp, .4 + .5 * (YY < by - h * .4), 0)), p.ramp('ice0', 'ice1', 'ice2'), dither=.2)
    # ruff
    nx, ny = body(17, -7)
    for k in range(5):
        a = -2.2 + k * .5
        tip = (nx + math.cos(a) * 11 + head_dx * .3, ny + math.sin(a) * 9 + head_dy * .3 + 4)
        f.paint((polygon([(nx - 4, ny + 4), tip, (nx + 5, ny + 5)]), np.full((H, W), .75)), p.ramp('fur3', 'fur4', 'fur5'), dither=.2)
    # near legs and neck
    hx, hy = cx + 30 + head_dx + 3 * lie, cy - 14 + head_dy + (1 - lie) * 0
    neck_base = body(15, -5)
    f.paint(capsule(neck_base, (hx - 3, hy + 5), 8, 6.2), fur, dither=.5)
    for hip, foot, kind in paws('near'):
        draw_leg(hip, foot, kind, fur, 3.5)
    # head
    far_ear = polygon([(hx - 5 - ears * 3, hy - 6), (hx - 4 - ears * 6, hy - 16 + ears * 7), (hx + 2, hy - 6)])
    f.paint((far_ear, np.where(far_ear, .35, 0)), far, dither=.2)
    skull = ellipsoid(hx, hy, 9.5, 8)
    f.paint(skull, fur, dither=.5)
    snout_b = (hx + 5, hy + 1)
    snout_t = (hx + 15, hy + 3)
    # lower jaw first so the snout overlaps it; open mouth shows the dark interior
    jaw_tip = (hx + 13 + jaw * 1, hy + 6.5 + jaw * 8)
    if jaw > .3:
        f.flat(polygon([(hx + 5, hy + 3), (hx + 16, hy + 4), (jaw_tip[0] + 1, jaw_tip[1] - 1), (hx + 5, hy + 7)]), 'mouth', outline=True)
        f.dots([(hx + 11, jaw_tip[1] - 2), (hx + 12, jaw_tip[1] - 2), (hx + 13, jaw_tip[1] - 3)], 'tongue')
    f.paint(capsule((hx + 3, hy + 6), jaw_tip, 3, 2), p.ramp('fur1', 'fur3', 'fur4'), dither=.3)
    f.paint(capsule(snout_b, snout_t, 5.2, 3.5), fur, dither=.5)
    f.paint(ellipsoid(snout_t[0] + 1, snout_t[1] - 1, 2.6, 2.4), p.ramp('nose', 'fur0'), dither=.1)
    for k in range(3):
        tx = hx + 8 + k * 3
        f.dots([(tx, hy + 5 + (1 if jaw > .3 else 0)), (tx, hy + 6 + (1 if jaw > .3 else 0))], 'tooth')
    if jaw > .3:
        f.dots([(jaw_tip[0] - 1 - k * 3, jaw_tip[1] - 1 - (k % 2)) for k in range(3)], 'tooth')
    ear = polygon([(hx - 3 - ears * 3, hy - 6), (hx - 2 - ears * 8, hy - 17 + ears * 8), (hx + 5, hy - 6.5)])
    f.paint((ear, np.where(ear, .3 + .45 * (YY < hy - 10), 0)), p.ramp('fur0', 'fur1', 'fur2', 'fur3'), dither=.2)
    ex, ey = hx + 5, hy - 2
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif eyes == 'blink':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex, ey, 2.7, 1.9 if eyes != 'angry' else 1.4)[0], 'eye', outline=True, edge='socket')
        f.dots([(ex + 1, ey)], 'eye2')
        if eyes in ('angry', 'hurt'):
            f.line((ex - 3, ey - 3), (ex + 3, ey - 2 if eyes == 'angry' else -5 + ey), 'socket', 1)
    if pounce:
        for k in range(7):
            f.dots([(cx - 20 - rng.uniform(0, 12), AY - 2 - rng.uniform(0, 10))], 'puff' if k % 2 else 'snow')
    if clip == 'die' and n >= 4:
        for k in range(6 if n < 7 else 3):
            f.dots([(cx - 22 + rng.uniform(0, 50), AY - 6 - rng.uniform(0, 22 if n < 6 else 8))], 'ice1' if k % 2 else 'ice0')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Glacier Yeti: a hunched, long-armed white brute with a blue-grey face, ice horns and tusks; it pounds the ground.
# ----------------------------------------------------------------------------------------------
YETI = Palette({
    'fur0': '#3d4e66', 'fur1': '#677f9b', 'fur2': '#9ab1c7', 'fur3': '#cbdae7', 'fur4': '#e8f1f8', 'fur5': '#fbfdff',
    'skn0': '#274560', 'skn1': '#456f90', 'skn2': '#74a4c4', 'skn3': '#a6cfe5', 'ice0': '#57a5d3', 'ice1': '#9edcf4',
    'ice2': '#e4faff', 'eye': '#bff6ff', 'eye2': '#ffffff', 'mouth': '#141c2a', 'tooth': '#fdfeff', 'socket': '#0a111d',
    'dust': '#c4d8e8', 'dust2': '#eef6fc', 'claw': '#d9e6f0', 'shade': '#58708c',
})
# Rest pose relative to (cx, ground); 'o' = paint with its own outline (limbs, feet, head), the trunk shares one outer outline.
YETI_PARTS = {
    'leg_far': ('cap', (-10, -26), (-11, -6), 8.5, 7.5, 'o'),
    'foot_far': ('ell', (-12, -4), 11, 5, 'o'),
    'leg_near': ('cap', (10, -26), (11, -6), 9, 8, 'o'),
    'foot_near': ('ell', (13, -4), 11.5, 5.5, 'o'),
    'pelvis': ('ell', (0, -28), 17, 10, ''),
    'torso': ('ell', (1, -45), 23, 22, ''),
    'arm_far': ('cap', (-20, -53), (-28, -24), 8, 8, 'o'),
    'fist_far': ('ell', (-29, -19), 10, 9.5, 'o'),
    'arm_near': ('cap', (22, -53), (30, -24), 8.5, 8.5, 'o'),
    'fist_near': ('ell', (31, -19), 11, 10, 'o'),
    'shoulder_far': ('ell', (-19, -54), 11, 10, ''),
    'shoulder_near': ('ell', (23, -54), 11.5, 10.5, ''),
    'head': ('ell', (3, -65), 12, 10.5, 'o'),
}
YETI_ORDER = list(YETI_PARTS)
YETI_RUBBLE = {
    'leg_far': (-22, -7), 'foot_far': (-12, -4), 'leg_near': (20, -7), 'foot_near': (12, -4), 'pelvis': (0, -6),
    'arm_far': (-28, -7), 'fist_far': (-17, -7), 'torso': (-2, -11), 'head': (13, -8), 'shoulder_far': (-8, -8),
    'arm_near': (26, -7), 'shoulder_near': (5, -10), 'fist_near': (31, -6),
}
# Fur tufts: (anchor part, dx, dy, width, length, angle): narrow tapered spikes hanging or streaming off the silhouette.
YETI_TUFTS = [
    ('torso', -20, 4, 4.5, 10, -2.4), ('torso', -17, 14, 4.5, 10, -2.0), ('torso', -9, 20, 4.5, 11, -1.8), ('torso', 0, 22, 4.5, 11, -1.6),
    ('torso', 9, 20, 4.5, 11, -1.4), ('torso', 17, 14, 4.5, 10, -1.2), ('torso', 21, 4, 4.5, 9, -.8),
    ('pelvis', -11, 7, 4, 8, -2.0), ('pelvis', -3, 10, 4, 8, -1.7), ('pelvis', 6, 9, 4, 8, -1.5),
    ('arm_far', -5, 12, 3.6, 8, -2.2), ('arm_far', 3, 16, 3.6, 8, -1.8), ('arm_near', -3, 12, 3.6, 8, -1.8), ('arm_near', 5, 16, 3.6, 8, -1.2),
    ('shoulder_far', -9, -2, 4, 8, -2.6), ('shoulder_near', 10, -2, 4, 8, -.6),
]


def yeti(clip, n):
    f = Frame(YETI)
    p = YETI
    rng = rng_for('yeti', clip, n)
    cx, eyes, flash, squash, lean, lift = 46, 'open', False, 1., 0., 0.
    roar = 0.
    off = {k: [0., 0.] for k in YETI_PARTS}
    fist_near = fist_far = None
    rubble, impact = 0., 0
    if clip == 'idle':
        breathe = [0, .5, 1, 1, .5, 0][n]
        for k in ('torso', 'head', 'shoulder_near', 'shoulder_far'):
            off[k][1] = -breathe
        off['head'][0] = [0, 0, .5, 1, .5, 0][n]
        for k in ('arm_near', 'fist_near', 'arm_far', 'fist_far'):
            off[k][0] = [0, 0, 1, 1.5, 1, 0][n]
        eyes = 'blink' if n == 4 else 'open'
        roar = [0, 0, .2, .3, .2, 0][n]
    elif clip == 'walk':
        lift = [0, 0, 2, 5, 3, 0, 0, 0][n]
        squash = [1, 1, 1, 1, 1, .95, .92, .98][n]
        lean = [1, 1, 2, 3, 2, 0, -1, 0][n]
        sw = [-1, -.5, .6, 1, .7, 0, -.8, -1][n]
        off['leg_near'][0] = off['foot_near'][0] = sw * 6
        off['leg_far'][0] = off['foot_far'][0] = -sw * 6
        off['foot_near'][1] = -max(0, sw) * 5
        off['foot_far'][1] = -max(0, -sw) * 5
        off['fist_near'][0] = off['arm_near'][0] = -sw * 4
        off['fist_far'][0] = off['arm_far'][0] = sw * 4
    elif clip == 'attack':
        lean = [-1, -2, -3, 1, 3, 3, 1, 0][n]
        cx += [0, 0, 0, 0, 1, 1, 0, 0][n]
        eyes = 'angry'
        roar = [.2, .5, .9, 1, 1, .6, .2, 0][n]
        squash = [.99, .97, .96, 1.02, .9, .92, .97, 1][n]
        impact = 1 if n in (4, 5) else 0
        fist_near = [(32, -26), (34, -50), (30, -76), (34, -50), (31, -10), (31, -9), (31, -17), (31, -19)][n]
        fist_far = [(-29, -21), (-31, -48), (-26, -75), (-30, -46), (-27, -10), (-27, -9), (-28, -17), (-29, -19)][n]
        off['head'] = [[0, 1], [-1, 0], [-1, -2], [1, 5], [2, 9], [2, 8], [1, 3], [0, 0]][n]
    elif clip == 'hurt':
        flash = n == 0
        lean = [-4, -3, -1, 0][n]
        cx += [0, 0, 0, 0][n]
        squash = [.94, .96, .99, 1][n]
        eyes = 'hurt' if n < 3 else 'angry'
        roar = [.8, .6, .3, 0][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        lean = [0, -3, -4, 0, 0, 0, 0, 0][n]
        rubble = [0, 0, .3, .62, .9, 1, 1, 1][n]
        squash = [1, .96, .9, .85, .8, .75, .75, .75][n]
        roar = [.8, .6, .3, 0, 0, 0, 0, 0][n]
    ground = AY

    def center(name, base):
        dx, dy = off[name]
        if rubble:
            delay = {'head': 0, 'fist_near': .05, 'fist_far': .05, 'arm_near': .08, 'arm_far': .08, 'shoulder_near': .1, 'shoulder_far': .1, 'torso': .15}.get(name, .25)
            t = float(np.clip((rubble - delay) / (1 - delay), 0, 1)) ** .85
            rx, ry = YETI_RUBBLE[name]
            return (lerp(base[0], rx, t) + dx, lerp(base[1], ry, t) + dy), t
        return (base[0] + dx, base[1] + dy), 0.

    def place(base):
        x, y = base
        k = (-y) / 70
        return cx + x + lean * k * 1.5, ground + y * squash - lift

    ramp = p.ramp('fur0', 'fur1', 'fur2', 'fur3', 'fur4', 'fur5')
    centers = {}
    posed = (fist_near is not None) and not rubble
    for name in YETI_ORDER:
        spec = YETI_PARTS[name]
        edge = bool(spec[-1])
        if spec[0] == 'ell':
            (bx, by), t = center(name, spec[1])
            ox, oy = place((bx, by))
            if posed and name in ('fist_near', 'fist_far'):
                ox, oy = place(fist_near if name == 'fist_near' else fist_far)
            shape = ellipsoid(ox, oy, spec[2] * (1 + .12 * t), spec[3] * (1 - .3 * t))
            centers[name] = (ox, oy)
        else:
            (b0x, b0y), t = center(name, spec[1])
            (b1x, b1y), _ = center(name, spec[2])
            if rubble:
                mid = ((b0x + b1x) / 2, max(b0y, b1y))
                b0x, b0y = mid[0] - 7 * t - (1 - t) * (mid[0] - b0x), lerp(b0y, mid[1], t)
                b1x, b1y = mid[0] + 7 * t + (1 - t) * (b1x - mid[0]), lerp(b1y, mid[1], t)
            a, b = place((b0x, b0y)), place((b1x, b1y))
            if posed and name in ('arm_near', 'arm_far'):
                a = place(YETI_PARTS['shoulder_near' if name == 'arm_near' else 'shoulder_far'][1])
                b = place(fist_near if name == 'arm_near' else fist_far)
            shape = capsule(a, b, spec[3] * (1 - .35 * t), spec[4] * (1 - .35 * t))
            centers[name] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        mask, _ = shape
        f.paint(shape, ramp, outline=edge, dither=.6)
        # tufts belonging to this part go on right after it
        if not rubble:
            for anchor, dx, dy, w, ln, ang in YETI_TUFTS:
                if anchor != name:
                    continue
                ox, oy = centers[name]
                bx, by = ox + dx, oy + dy
                sway = math.sin(n * .9 + dx) * 1.3 if clip == 'idle' else lean * .3
                tip = (bx + math.cos(ang) * ln * .8 + sway, by - math.sin(ang) * ln * .8 * -1)
                perp = (-math.sin(ang), math.cos(ang))
                tuft = polygon([(bx + perp[0] * w, by + perp[1] * w), tip, (bx - perp[0] * w, by - perp[1] * w)])
                f.paint((tuft, np.where(tuft, .35 + .45 * ((XX - bx) / (2 * w + 6) + .4), 0)), ramp, outline=False, dither=.25)
        if name == 'torso' and not rubble:
            tx, ty = centers[name]
            f.paint((mask & (YY > ty + 6) & (XX < tx - 4), np.full((H, W), .45)), ramp, outline=False, dither=.2)
        if name == 'head':
            hx, hy = centers[name]
            if rubble and rubble > .55:
                continue
            # horns: one tapered polygon each, swept out and up from the crown
            for side, shade in ((-1, ('ice0', 'ice1', 'ice2')), (1, ('ice1', 'ice2'))):
                hb = (hx + side * 9, hy - 6)
                horn = polygon([(hb[0] - side * 3.5, hb[1] + 3), (hb[0] + side * 3, hb[1] - 4), (hb[0] + side * 8, hb[1] - 10), (hb[0] + side * 4, hb[1] - 1), (hb[0] + side * 4, hb[1] + 3)])
                f.paint(gradient(horn, hb[0] - 3, hb[1] - 10, hb[0] + 8, hb[1] + 3, .1, .95), p.ramp(*shade), dither=.3)
            # shaggy hair across the crown
            for dx, ln in [(-7, 7), (-2, 9), (3, 8), (8, 6)]:
                tuft = polygon([(hx + dx - 3, hy - 6), (hx + dx + lean * .2, hy - 6 - ln), (hx + dx + 3, hy - 6)])
                f.paint((tuft, np.full((H, W), .6)), ramp, outline=False, dither=.2)
            face = ellipsoid(hx + 1.5, hy + 2, 9, 7.6)
            f.paint((face[0] & mask, face[1]), p.ramp('skn0', 'skn1', 'skn2', 'skn3'), dither=.5)
            f.a[polygon([(hx - 8, hy - 5), (hx + 11, hy - 6), (hx + 11, hy - 2), (hx - 8, hy - 1)]) & mask] = p['fur1']          # heavy brow
            for i, x in enumerate((hx - 3, hx + 6)):
                if eyes == 'dead':
                    eye_dead(f, x, hy)
                elif eyes == 'blink':
                    f.line((x - 2, hy), (x + 2, hy), 'socket', 1)
                else:
                    f.flat(ellipsoid(x, hy, 2.4, 1.9 if eyes != 'angry' else 1.3)[0], 'eye', outline=True, edge='socket')
                    f.dots([(x + 1, hy)], 'eye2')
            f.dots([(hx + 1, hy + 3), (hx + 3, hy + 3)], 'skn0')
            open_h = 2 + roar * 5
            f.flat(polygon([(hx - 5, hy + 5), (hx + 8, hy + 5), (hx + 7, hy + 5 + open_h), (hx - 4, hy + 5 + open_h)]), 'mouth', outline=True)
            f.dots([(hx - 4, hy + 6), (hx - 1, hy + 6), (hx + 2, hy + 6), (hx + 5, hy + 6), (hx + 7, hy + 6)], 'tooth')
            for tx, lean_x in ((hx - 4, -1), (hx + 7, 1)):
                f.paint(capsule((tx, hy + 5 + open_h), (tx + lean_x, hy + 5 + open_h - 7), 1.5, .5), p.ramp('ice1', 'ice2'), dither=.1)
        if name == 'shoulder_near' and not rubble:
            sx, sy = centers[name]
            for k, (dx, dy, h) in enumerate([(-5, -7, 7), (1, -9, 8), (7, -6, 6)]):
                sp = polygon([(sx + dx - 2.4, sy + dy + 3), (sx + dx + .5, sy + dy - h), (sx + dx + 2.6, sy + dy + 3)])
                f.paint((sp, np.where(sp, .4 + .5 * (YY < sy + dy - h * .4), 0)), p.ramp('ice0', 'ice1', 'ice2'), dither=.2)
    # one outline round the whole trunk where parts without their own outline meet empty space
    solid = f.a > 0
    ring = mc.dilate(solid) & ~solid
    f.a[ring] = p['ol']
    if impact:
        gx = cx + 31 + lean * .3
        for k in range(10):
            a = rng.uniform(-3.1, 0)
            d = rng.uniform(5, 13) * (1 if n == 4 else 1.2)
            f.dots([(gx + math.cos(a) * d, ground - 2 + math.sin(a) * d * .8)], 'dust2' if k % 3 == 0 else 'dust')
        f.a[ellipsoid(gx, ground - 1, 12, 3)[0] & (f.a == 0) & (DITHER > -.1)] = p['dust']
    if clip == 'die' and n >= 4:
        for k in range(5 if n < 7 else 2):
            f.dots([(cx - 24 + rng.uniform(0, 56), ground - 4 - rng.uniform(0, 18))], 'dust2')
        f.shift(0, -3)
    if flash:
        f.whiten()
    return f.a



# ----------------------------------------------------------------------------------------------
# Rime Wyrm: a coiled ice serpent. Three stacked coils, a neck that rears and strikes, a crest of ice and a frost breath.
# ----------------------------------------------------------------------------------------------
WYRM = Palette({
    'sc0': '#102f50', 'sc1': '#1b5686', 'sc2': '#2f86b8', 'sc3': '#5bbbe0', 'sc4': '#a0e6f6', 'sc5': '#e8fcff',
    'bl0': '#8fb0c4', 'bl1': '#cde2ee', 'bl2': '#f1f9fd', 'ice0': '#4aa0d2', 'ice1': '#9ee0f6', 'ice2': '#effcff',
    'eye': '#ffffff', 'eyeg': '#69efff', 'socket': '#07121f', 'mouth': '#0b1c33', 'tongue': '#ff6f8f', 'tooth': '#fcfeff',
    'puff': '#e5f5fd', 'puff2': '#b0daf0', 'puff3': '#7fbfe0', 'shard': '#c8efff',
})
WYRM_COILS = [(0, -8, 27, 8), (2, -17, 23, 8), (-1, -25, 18, 7)]       # (dx, dy from the ground, rx, ry)


def wyrm(clip, n):
    f = Frame(WYRM)
    p = WYRM
    rng = rng_for('wyrm', clip, n)
    cx, lift, squash, flash, eyes = 42, 0., 1., False, 'open'
    neck_dx, neck_dy, theta, jaw, breath, sag, ear = 0., 0., .12, 0., 0., 0., 0.
    sway = n / 6 * 2 * math.pi
    if clip == 'idle':
        neck_dx = math.sin(sway) * 2.2
        neck_dy = math.sin(sway * 2) * 1.2
        theta = .12 + math.sin(sway) * .05
        jaw = [0, 0, .2, .3, .2, 0][n]
        eyes = 'blink' if n == 3 else 'open'
        squash = 1 + math.sin(sway) * .015
    elif clip == 'walk':
        lift = [0, 0, 3, 5, 3, 0, 0, 0][n]
        squash = [1, 1, 1.01, 1.02, 1.01, .88, .93, .98][n]
        neck_dx = [0, 1, 3, 5, 3, -2, -1, 0][n]
        neck_dy = [0, 0, 0, 0, 0, 3, 2, 0][n]
        theta = [.12, .12, .05, 0, .1, .22, .18, .12][n]
        jaw = [0, 0, .3, .5, .3, 0, 0, 0][n]
    elif clip == 'attack':
        neck_dx = [-2, -4, -6, 2, 3, 3, 2, 1][n]
        neck_dy = [-1, -3, -5, 8, 12, 9, 3, 0][n]
        theta = [0, -.2, -.35, .45, .65, .55, .3, .15][n]
        jaw = [.1, .1, .2, 1, 1, .8, .3, .1][n]
        squash = [.98, .95, .93, 1.02, .97, .97, .99, 1][n]
        breath = [0, 0, 0, .4, .7, .6, .3, 0][n]
        eyes = 'angry'
    elif clip == 'hurt':
        flash = n == 0
        neck_dx = [-6, -4, -2, 0][n]
        neck_dy = [-2, -1, 0, 0][n]
        theta = [-.3, -.2, -.05, .1][n]
        jaw = [1, .7, .3, 0][n]
        squash = [.94, .96, .99, 1][n]
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        sag = [0, .12, .35, .6, .82, 1, 1, 1][n]
        neck_dx = [0, -4, 3, 8, 11, 13, 13, 13][n]
        neck_dy = [-1, -3, 4, 14, 25, 33, 33, 33][n]
        theta = [-.2, -.3, .1, .4, .6, .75, .75, .75][n]
        jaw = [1, .8, .5, .3, .3, .3, .3, .3][n]
        squash = [1, .97, .93, .9, .87, .85, .85, .85][n]
    ground = AY - lift

    def gy(dy):
        return ground + dy * squash

    # tail tip first, trailing out of the bottom coil and curling up
    tail_pts = smooth([(cx - 18, gy(-8)), (cx - 26, gy(-5)), (cx - 32, gy(-8 - 3 * (1 - sag))), (cx - 35, gy(-15 + 5 * sag))], 14)
    # whole-silhouette outline: collect discs, outline the union once, then shade them without their own outlines
    ramp = p.ramp('sc0', 'sc1', 'sc2', 'sc3', 'sc4', 'sc5')
    discs = []
    for i, (x, y) in enumerate(tail_pts):
        discs.append((ellipsoid(x, y, 1.2 + 6.5 * (1 - i / 13) + 1, 1.2 + 6 * (1 - i / 13)), ramp))
    for dx, dy, rx, ry in WYRM_COILS:
        discs.append((ellipsoid(cx + dx, gy(dy), rx, ry * squash ** .5), ramp))
    # neck: base on the top coil, S-curve up and forward; head base at the end
    base = (cx + 4, gy(-29))
    head_base = (cx + 13 + neck_dx, gy(-64) + neck_dy)
    mid1 = (cx + 1 + neck_dx * .3, gy(-44) + neck_dy * .35)
    mid2 = (cx + 8 + neck_dx * .65, gy(-54) + neck_dy * .7)
    neck = smooth([base, mid1, mid2, head_base], 26)
    for i, (x, y) in enumerate(neck):
        t = i / 25
        discs.append((ellipsoid(x, y, 9.2 - 3.2 * t, 8.6 - 3.0 * t), ramp))
    union = np.zeros((H, W), bool)
    for m, _ in discs:
        union |= m[0] if isinstance(m, tuple) else m
    # `discs` entries are ((mask, lum), ramp)
    union = np.zeros((H, W), bool)
    for shape, _ in discs:
        union |= shape[0]
    f.a[mc.dilate(union) & ~union] = p['ol']
    for shape, r in discs:
        f.paint(shape, r, outline=False, dither=.55)
    # pale belly scutes: bands across the coils and down the front of the neck
    for dx, dy, rx, ry in WYRM_COILS:
        # a pale crescent along the underside of each coil, with a few scale arcs above it
        ring = ellipsoid(cx + dx, gy(dy), rx, ry * squash ** .5)[0]
        low = ring & (YY > gy(dy) + ry * squash ** .5 * .45)
        f.a[low & (DITHER > -.25)] = p['bl0']
        f.a[low & (YY > gy(dy) + ry * squash ** .5 * .62) & (DITHER > 0)] = p['bl1']
        for k in range(-3, 4):
            arc = ring & (np.abs(((XX - (cx + dx) - k * rx * .28) ** 2 / 9 + (YY - gy(dy) + 1) ** 2 / 4) - 1) < .35) & (YY < gy(dy) + 2)
            f.a[arc & (f.a != p['ol'])] = p['sc2'] if k % 2 else p['sc3']
    for i in range(1, 26, 2):
        t = i / 25
        x, y = neck[i]
        f.dots([(x + 5 - 3 * t, y)], 'bl1')
    # dorsal spines of ice down the back of the neck and the coils
    for i in range(1, 26, 3):
        t = i / 25
        x, y = neck[i]
        sx = x - (8.4 - 3 * t)
        sp = polygon([(sx + 4, y - 2.5), (sx - 3 - 2.5 * (1 - t), y - 1 + 2 * (1 - t)), (sx + 4, y + 2.5)])
        f.paint((sp, np.where(sp, .25 + .4 * (XX > sx - 3), 0)), p.ramp('ice0', 'ice1'), dither=.2)
    for dx, dy, h in [(-24, -12, 7), (-14, -31, 8), (-6, -33, 8)]:
        bx, by = cx + dx, gy(dy)
        sp = polygon([(bx - 3, by + 3), (bx - 1, by - h), (bx + 3, by + 3)])
        f.paint((sp, np.where(sp, .5, 0)), p.ramp('ice0', 'ice1', 'ice2'), dither=.2)
    # head
    hx, hy = head_base
    d = (math.cos(theta), math.sin(theta))
    q = (-d[1], d[0])           # points down-ish (the jaw side)

    def at(a, b):
        return (hx + d[0] * a + q[0] * b, hy + d[1] * a + q[1] * b)

    for side, shade in ((-1, ('ice0', 'ice1', 'ice2')), (1, ('ice1', 'ice2'))):
        base_pt = at(2 - side * 3, -6)
        horn = polygon([at(2 - side * 3 - 3, -4), at(-6 - side * 4, -13 - side), at(-12 - side * 4, -14 - side * 2), at(-3 - side * 4, -4), at(2 - side * 3 + 3, -4)])
        f.paint(gradient(horn, *at(-12, -12), *at(2, -4), .1, .95), p.ramp(*shade), dither=.3)
    for k in range(3):
        fr = polygon([at(-2, -4 + k * 3), at(-12 - k * 2, -6 + k * 6), at(-1, 0 + k * 3)])
        f.paint((fr, np.full((H, W), .6)), p.ramp('ice0', 'ice1', 'ice2'), dither=.2)
    skull = ellipsoid(*at(5, 0), 10.5, 7.3, theta)
    open_a = jaw * .55
    jd = (math.cos(theta + open_a), math.sin(theta + open_a))
    jaw_tip = (hx + d[0] * 6 + q[0] * 4 + jd[0] * 15, hy + d[1] * 6 + q[1] * 4 + jd[1] * 15)
    jaw_base = at(6, 4)
    if jaw > .25:
        up_tip = at(24, 3)
        f.flat(polygon([at(8, 3), up_tip, jaw_tip, jaw_base]), 'mouth', outline=True)
        f.dots([((jaw_tip[0] * 2 + jaw_base[0]) / 3 + 1, (jaw_tip[1] * 2 + jaw_base[1]) / 3 - 1)], 'tongue')
        f.dots([(jaw_tip[0] - 2, jaw_tip[1] - 1), (jaw_tip[0] - 5, jaw_tip[1] - 1.5), (jaw_tip[0] - 8, jaw_tip[1] - 2)], 'tooth')
    f.paint(capsule(jaw_base, jaw_tip, 3.2, 2.1), p.ramp('bl0', 'bl1', 'bl2'), dither=.3)
    f.paint(skull, ramp, dither=.5)
    f.paint(capsule(at(8, 1), at(23, 3), 5.4, 3.4), ramp, dither=.5)
    f.dots([at(23, 1), at(22, 2)], 'socket')
    f.dots([at(17, 5.2), at(20, 5), at(14, 5.4)], 'tooth')
    ex, ey = at(8, -2.5)
    if eyes == 'dead':
        eye_dead(f, ex, ey)
    elif eyes == 'blink':
        f.line((ex - 2, ey), (ex + 2, ey), 'socket', 1)
    else:
        f.flat(ellipsoid(ex, ey, 2.7, 2.2 if eyes != 'angry' else 1.5)[0], 'eyeg', outline=True, edge='socket')
        f.dots([(ex + 1, ey)], 'eye')
        if eyes in ('angry', 'hurt'):
            f.line((ex - 3, ey - 3), (ex + 3, ey - 2 if eyes == 'angry' else ey - 5), 'socket', 1)
    # the cold breath: a cone of clouds out of the mouth
    if breath:
        ox, oy = at(23, 4)
        for k in range(26):
            tt = rng.uniform(0, 1) * breath
            rr = 2 + 5 * tt + rng.uniform(0, 1.5)
            bx_ = ox + (3 + tt * 13) * d[0] + rng.uniform(-1, 1) * (2 + tt * 5)
            by_ = oy + (3 + tt * 13) * d[1] + 3 * tt + rng.uniform(-1, 1) * (2 + tt * 6)
            f.paint(ellipsoid(bx_, by_, rr, rr * .8), p.ramp('puff3', 'puff2', 'puff'), outline=False, dither=.6)
    if clip == 'die' and n >= 3:
        for k in range(7 if n < 7 else 3):
            f.dots([(cx - 26 + rng.uniform(0, 60), AY - 6 - rng.uniform(0, 30 if n < 6 else 14))], 'shard' if k % 2 else 'ice1')
    if flash:
        f.whiten()
    return f.a


# @@DRAWERS@@

# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_crag_sprites.py)
# ----------------------------------------------------------------------------------------------
DRAWERS = {k: pair for k, pair in {'crab': (globals().get('crab'), globals().get('CRAB')), 'wolf': (globals().get('wolf'), globals().get('WOLF')),
                                   'yeti': (globals().get('yeti'), globals().get('YETI')), 'wyrm': (globals().get('wyrm'), globals().get('WYRM'))}.items()
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
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#2d4a6b')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def ids():
    meta = ASSETS / 'rime.txt'
    return json.loads(meta.read_text()).get('sprites', {}) if meta.exists() else {}


def build(kinds, replace=False):
    meta_path = ASSETS / 'rime.txt'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    known = meta.get('sprites', {})
    clash = [k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist (ids in rime.txt). Use export to preserve edits; --replace discards them.')
    for kind in clash:
        api('delete', {'sprite_id': known[kind]})
    made = {}
    for kind in kinds:
        frames = render(kind)
        bad = bounds_report(kind, frames)
        if bad:
            raise SystemExit(f'{kind} touches the canvas edge: {bad}')
        palette = DRAWERS[kind][1].hex
        np.savez_compressed(RAW / f'rime_{kind}_raw.npz', **frames)
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
    meta_path = ASSETS / 'rime.txt'
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
            sheet = Image.new('RGBA', (8 * W, H), '#2d4a6b')
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
            dest = ROOT / 'test-results/rime-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'rime_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': saved}
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/rime_<kind>.png and rime.txt')


def verify(kinds):
    """The exported atlas must equal the freshly rendered frames pixel for pixel."""
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        atlas = Image.open(ASSETS / f'rime_{kind}.png').convert('RGBA')
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
        directory = next((a for a in sys.argv[2:] if a not in DRAWERS and not a.startswith('--')), ROOT / 'test-results/rime-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_rime_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...] | verify [kind...]')
