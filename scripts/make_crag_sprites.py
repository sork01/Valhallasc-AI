#!/usr/bin/env python3
"""makesprites workflow for the Emberfall Crags monsters: preview | build [--replace] | export.

Four kinds (wisp, spider, wraith, golem) share one 96x96 frame, a foot anchor at (48, 90),
right-facing art (the game mirrors it) and the same five clips as the Ironhide Beetle
(idle 6, walk 8, attack 8, hurt 4, die 8), so client/field.js drives them with one state machine.

Frames are drawn from parameters, not by hand: shaded ellipsoids and capsules lit from the
upper left, a dithered ramp per material, and a dark outline around every part.
`build` saves ONE new 34-frame PixelFlow sprite per kind (valhallasc_crag_<kind>_all) and refuses
existing names unless --replace is given; --replace discards hand edits made in the editor.
`export` reads the editor frames back, so edits survive, and writes client/assets/crags_<kind>.png
plus crags.txt. Needs numpy/Pillow; build/export also need PixelFlow and its local agent key.
"""
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.error
import urllib.request

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
W, H, AX, AY = 96, 96, 48, 90
PREFIX = 'valhallasc_crag_'
KINDS = ['wisp', 'spider', 'wraith', 'golem']
CLIPS = {'idle': (6, 6), 'walk': (10, 8), 'attack': (12, 8), 'hurt': (10, 4), 'die': (8, 8)}
OUTLINE = '#1a1118'
FLASH = '#fffaf0'
YY, XX = np.mgrid[0:H, 0:W]
YY = YY + .5
XX = XX + .5
LIGHT = np.array([-.5, -.62, .6])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + .5) / 16 - .5
DITHER = np.tile(BAYER, (H // 4, W // 4))


class Palette:
    """Named colours -> indices. Index 0 is transparent; every hex must be unique."""

    def __init__(self, colors):
        self.names = {'clear': 0}
        self.hex = ['#00000000']
        for name, value in [('ol', OUTLINE), ('flash', FLASH)] + list(colors.items()):
            assert value not in self.hex, f'duplicate colour {name} {value}'
            self.names[name] = len(self.hex)
            self.hex.append(value)

    def __getitem__(self, name):
        return self.names[name]

    def ramp(self, *names):
        return np.array([self.names[n] for n in names], dtype=np.uint8)


def dilate(mask, steps=1):
    out = mask.copy()
    for _ in range(steps):
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        out = grown
    return out


def rotate(u, v, angle):
    c, s = math.cos(angle), math.sin(angle)
    return u * c + v * s, -u * s + v * c


def ellipsoid(cx, cy, rx, ry, angle=0.):
    """Mask and lit intensity (0..1) of a rotated ellipsoid, light from the upper left."""
    u, v = rotate(XX - cx, YY - cy, angle)
    q = (u / rx) ** 2 + (v / ry) ** 2
    mask = q <= 1
    nz = np.sqrt(np.clip(1 - q, 0, 1))
    nx, ny = u / rx, v / ry
    c, s = math.cos(angle), math.sin(angle)
    nx, ny = nx * c - ny * s, nx * s + ny * c       # back to screen axes
    lum = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    return mask, lum


def capsule(p0, p1, r0, r1=None):
    """A limb: a stretched ellipsoid between two joints with its own radius at each end."""
    r1 = r0 if r1 is None else r1
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy or 1e-9
    t = np.clip(((XX - x0) * dx + (YY - y0) * dy) / length2, 0, 1)
    px, py = x0 + t * dx, y0 + t * dy
    r = r0 + (r1 - r0) * t
    dist = np.hypot(XX - px, YY - py)
    mask = dist <= r
    side = np.clip(((XX - px) * -dy + (YY - py) * dx) / (np.sqrt(length2) * np.maximum(r, 1e-6)), -1, 1)
    nz = np.sqrt(np.clip(1 - side ** 2, 0, 1))
    n = math.hypot(dx, dy) or 1
    nx, ny = side * -dy / n, side * dx / n
    lum = np.clip(nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2], 0, 1)
    return mask, lum


def polygon(points):
    image = Image.new('L', (W, H), 0)
    ImageDraw.Draw(image).polygon([(x, y) for x, y in points], fill=255)
    return np.array(image) > 0


def gradient(mask, x0, y0, x1, y1, lo=.15, hi=.95):
    """Flat parts get a linear light ramp from (x0, y0) dark to (x1, y1) lit."""
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((XX - x0) * dx + (YY - y0) * dy) / (dx * dx + dy * dy or 1e-9), 0, 1)
    return mask, lo + (hi - lo) * t


class Frame:
    def __init__(self, palette):
        self.p = palette
        self.a = np.zeros((H, W), dtype=np.uint8)

    def paint(self, shape, ramp, outline=True, edge=None, dither=.55, mirror=False):
        mask, lum = shape
        if mirror:
            mask, lum = mask[:, ::-1], lum[:, ::-1]
        if not mask.any():
            return
        if outline:
            ring = dilate(mask) & ~mask
            self.a[ring] = self.p['ol'] if edge is None else self.p[edge]
        levels = len(ramp)
        position = np.clip(lum * (levels - 1) + DITHER * dither, 0, levels - 1)
        self.a[mask] = ramp[np.round(position).astype(int)][mask]

    def flat(self, mask, name, outline=False, edge=None):
        if outline:
            ring = dilate(mask) & ~mask
            self.a[ring] = self.p['ol'] if edge is None else self.p[edge]
        self.a[mask] = self.p[name]

    def dots(self, points, name):
        for x, y in points:
            if 0 <= int(x) < W and 0 <= int(y) < H:
                self.a[int(y), int(x)] = self.p[name]

    def line(self, p0, p1, name, width=1):
        image = Image.new('L', (W, H), 0)
        ImageDraw.Draw(image).line([p0, p1], fill=255, width=width)
        self.a[np.array(image) > 0] = self.p[name]

    def whiten(self, keep=('ol',)):
        solid = self.a > 0
        for name in keep:
            solid &= self.a != self.p[name]
        self.a[solid] = self.p['flash']

    def shift(self, dx, dy):
        out = np.zeros_like(self.a)
        ys, xs = np.nonzero(self.a)
        ny, nx = ys + dy, xs + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        out[ny[ok], nx[ok]] = self.a[ys[ok], xs[ok]]
        self.a = out


def rng_for(kind, clip, n):
    return np.random.default_rng(sum(ord(c) for c in kind) * 1009 + sum(ord(c) for c in clip) * 31 + n)


def lerp(a, b, t):
    return a + (b - a) * t


# ----------------------------------------------------------------------------------------------
# Cinder Wisp: a floating flame spirit. Heat (not light) shades it: white-hot core, red rim.
# ----------------------------------------------------------------------------------------------
WISP = Palette({
    'rim': '#6a1d1d', 'red': '#b8331f', 'orange': '#ee6a1c', 'amber': '#ffa22f', 'yellow': '#ffd95c',
    'hot': '#fff4b8', 'socket': '#2b0d10', 'eye': '#ffe57a', 'ember': '#ffb347', 'ash1': '#4a4044',
    'ash2': '#7b6f73', 'ash3': '#a99fa0', 'smoke': '#322a2e',
})


def wisp(clip, n):
    f = Frame(WISP)
    p = WISP
    rng = rng_for('wisp', clip, n)
    lift, shift, sx, sy, tail, eyes, flash, glow = 18, 0, 1., 1., 1., 'open', False, 1.
    phase = n * 1.1
    burst = 0
    if clip == 'idle':
        lift = 18 + [0, 1, 3, 4, 3, 1][n]
        glow = [1, 1.05, 1.1, 1.05, 1, .95][n]
        eyes = 'blink' if n == 3 else 'open'
    elif clip == 'walk':
        lift = 18 + [0, 0, 3, 6, 4, 1, 0, 0][n]
        tail = [1, 1, 1.15, 1.25, 1.2, 1.1, 1, 1][n]
        sx = [1, 1, .95, .92, .95, 1.06, 1.1, 1.03][n]
        sy = [1, 1, 1.05, 1.08, 1.05, .94, .9, .98][n]
    elif clip == 'attack':
        shift = [-2, -4, -6, 3, 8, 6, 1, 0][n]
        sx = [.92, .86, .82, 1.15, 1.22, 1.08, .96, 1][n]
        sy = [1.04, 1.1, 1.14, .88, .82, .94, 1, 1][n]
        tail = [.8, .7, .6, 1.35, 1.5, 1.3, 1, 1][n]
        glow = [1.1, 1.2, 1.3, 1.3, 1.3, 1.1, 1, 1][n]
        lift = 18 + [1, 1, 2, 1, 0, 1, 2, 1][n]
        eyes = 'angry'
    elif clip == 'hurt':
        shift = [-5, -3, -1, 0][n]
        sx, sy = [.86, .94, 1.04, 1][n], [1.14, 1.04, .98, 1][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
        lift = 18 + [3, 2, 1, 0][n]
    elif clip == 'die':
        eyes = 'dead'
        flash = n == 0
        sx = [1, 1.12, .9, .7, .5, 0, 0, 0][n]
        sy = [1, 1.12, .9, .7, .5, 0, 0, 0][n]
        tail = [1, 1.1, .8, .5, .3, 0, 0, 0][n]
        lift = 14 + [2, 3, 3, 1, 0, 0, 0, 0][n]
        burst = n
    cx, cy = 57 + shift, AY - lift - 14
    ramp = p.ramp('rim', 'red', 'orange', 'amber', 'yellow', 'hot')
    if sx > 0:
        k = (sx + sy) / 2
        heat = np.zeros((H, W))
        mask = np.zeros((H, W), bool)

        def tongue(points, radii, weight, samples=18):
            """A smooth tapering flame: discs interpolated along a path, hottest at the base."""
            nonlocal heat, mask
            pts = np.array(points, dtype=float)
            rad = np.array(radii, dtype=float)
            for i in range(samples + 1):
                t = i / samples * (len(pts) - 1)
                j = min(int(t), len(pts) - 2)
                u = t - j
                x = lerp(pts[j][0], pts[j + 1][0], u)
                y = lerp(pts[j][1], pts[j + 1][1], u)
                r = max(.9, lerp(rad[j], rad[j + 1], u))
                d = np.hypot(XX - x, YY - y)
                inside = d <= r
                mask |= inside
                level = np.where(inside, np.clip(1 - d / r, 0, 1) ** .7 * weight * (1 - .35 * i / samples), 0)
                heat = np.maximum(heat, level)

        def wave(i, amplitude, speed=1.):
            return math.sin(phase * speed + i * 1.25) * amplitude

        main = [(cx, cy), (cx - 11 * tail * sx, cy - 4 * sy)]
        main += [(cx - (11 + 9 * i) * min(tail, 1.5) ** .7 * sx + wave(i, 1.2 + i * 1.1), cy - (4 + 9 * i ** 1.1) * sy * (.8 + .2 * min(tail, 1.4))) for i in range(1, 4)]
        tongue(main, [15 * k, 13 * k, 10.5 * k, 7 * k, 2.2], 1.)
        tongue([(cx - 3, cy - 8 * sy), (cx - 6 + wave(1, 1.5, 1.3), cy - 20 * sy * min(tail, 1.3)), (cx - 9 + wave(2, 2.5, 1.3), cy - 33 * sy * min(tail, 1.3))],
               [9 * k, 5, 1.6], .85)
        tongue([(cx + 8 * sx, cy - 8 * sy), (cx + 12 * sx + wave(3, 1.3, .9), cy - 17 * sy * min(tail, 1.2)), (cx + 13 * sx + wave(4, 2, .9), cy - 25 * sy * min(tail, 1.2))],
               [6 * k, 3.6, 1.2], .8)
        heat = np.clip(heat * glow, 0, 1)
        f.paint((mask, heat), ramp, outline=True, edge='rim', dither=.7)
        # A hotter, rounder core and the face.
        core = ellipsoid(cx + 3, cy + 1, 10 * sx, 10 * sy)
        f.paint((core[0], .3 + .7 * core[1]), p.ramp('orange', 'amber', 'yellow', 'hot'), outline=False, dither=.5)
        ex = [cx + 1, cx + 11]
        ey = cy - 1
        for i, x in enumerate(ex):
            if eyes == 'blink':
                f.line((x - 2, ey + 1), (x + 2, ey + 1), 'socket', 1)
            elif eyes == 'dead':
                f.line((x - 2, ey - 2), (x + 2, ey + 2), 'socket', 1)
                f.line((x + 2, ey - 2), (x - 2, ey + 2), 'socket', 1)
            else:
                half = 3.4 if eyes == 'open' else 2.6
                f.flat(ellipsoid(x, ey, 2.7, half)[0], 'socket')
                f.dots([(x + 1, ey), (x + 1, ey - 1) if eyes == 'open' else (x + 1, ey + 1)], 'eye')
                if eyes in ('angry', 'hurt'):
                    inward = 1 if i == 0 else -1
                    f.line((x - 3, ey - 4 + (0 if inward > 0 else 1)), (x + 3, ey - 4 + (1 if inward > 0 else 0)), 'socket', 1)
        if eyes != 'dead':
            f.line((cx + 4, cy + 7), (cx + 10, cy + 6 + (1 if eyes == 'angry' else 0)), 'socket', 1)
    # Drifting sparks around the flame; death throws them outward.
    count = 5 if clip != 'die' else 0
    for k in range(count):
        a = rng.uniform(0, 6.28)
        d = rng.uniform(14, 26)
        f.dots([(cx - 8 + math.cos(a) * d, cy - 10 + math.sin(a) * d * .8)], 'ember')
    if clip == 'die':
        spread = [0, 0, 10, 18, 26, 30, 32, 33][n]
        fall = [0, 0, 0, 3, 8, 12, 15, 16][n]
        for k in range(14 if n < 7 else 5):
            a = rng.uniform(0, 6.28)
            d = rng.uniform(.4, 1.0) * spread
            x, y = cx + math.cos(a) * d, cy - 4 + math.sin(a) * d * .75 + fall * rng.uniform(.5, 1)
            f.dots([(x, min(AY - 1, y))], 'ember' if k % 3 else 'yellow')
        if n >= 4:
            width = [0, 0, 0, 0, 8, 13, 16, 17][n]
            height = [0, 0, 0, 0, 2, 3, 3, 3][n]
            heap = ellipsoid(cx, AY - 3, width, height)
            f.paint(heap, p.ramp('ash1', 'ash2', 'ash3'), outline=True, dither=.4)
            if n < 7:
                f.dots([(cx - 3, AY - 4), (cx + 4, AY - 3)], 'orange')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Magma Spider: basalt carapace, cracks of lava, eight arched legs (four far, four near).
# ----------------------------------------------------------------------------------------------
SPIDER = Palette({
    'far0': '#1d1923', 'far1': '#2b2531', 'far2': '#3c3443', 'bas0': '#27222d', 'bas1': '#3d3544',
    'bas2': '#594e5f', 'bas3': '#7d6f80', 'bas4': '#a395a3', 'lava0': '#8c2610', 'lava1': '#d94b14',
    'lava2': '#ff8b1f', 'lava3': '#ffd24b', 'lava4': '#fff2a8', 'socket': '#2a0b0b', 'eye': '#ffe27a',
    'fang': '#ead6b0', 'fang2': '#b9a07a', 'ash1': '#463f47', 'ash2': '#756c76', 'ash3': '#a59ca5',
    'ember': '#ff9d3a',
})
SPIDER_LEGS = {
    # (hip offset from the body centre, knee offset, resting foot x offset)
    'near': [((13, 9), (29, -15), 38), ((7, 10), (19, -19), 24), ((-1, 10), (-13, -17), -14), ((-8, 9), (-27, -13), -36)],
    'far': [((12, 8), (25, -19), 31), ((5, 9), (12, -22), 15), ((-2, 9), (-18, -21), -20), ((-9, 8), (-32, -16), -41)],
}


def spider(clip, n):
    f = Frame(SPIDER)
    p = SPIDER
    rng = rng_for('spider', clip, n)
    cx, lift, tilt, glow, eyes, flash = 47, 0., 0., 1., 'open', False
    crouch = 0.
    gait = n / 8 * 2 * math.pi
    stride = 0.
    reach = [0, 0, 0, 0]          # front legs raised / stabbing: per-leg (dx, dy) additions
    legdx = [0., 0., 0., 0.]
    legdy = [0., 0., 0., 0.]
    curl = 0.
    if clip == 'idle':
        crouch = [0, 0, 1, 1, 0, 0][n]
        glow = [1, 1.1, 1.2, 1.1, 1, .9][n]
        eyes = 'blink' if n == 4 else 'open'
        stride = 0
        legdx = [0, 0, math.sin(n / 6 * 6.28) * 1.2, 0]
    elif clip == 'walk':
        lift = [0, 0, 3, 6, 4, 0, 0, 0][n]
        crouch = [0, 0, 0, 0, 0, 2, 2, 1][n]
        stride = 1.
    elif clip == 'attack':
        tilt = [.12, .22, .3, -.06, -.12, -.05, 0, 0][n]
        cx += [-1, -1, -2, 2, 3, 3, 1, 0][n]
        crouch = [1, 2, 3, 0, 0, 1, 0, 0][n]
        lift = [0, 0, 0, 3, 2, 0, 0, 0][n]
        glow = [1.1, 1.25, 1.4, 1.4, 1.3, 1.1, 1, 1][n]
        eyes = 'angry'
        raised = [0, 1, 1.3, 0, 0, 0, 0, 0][n]
        stab = [0, 0, 0, 1, 1.2, .6, 0, 0][n]
        legdx = [raised * -2 + stab * 5, raised * -3 + stab * 5, 0, 0]
        legdy = [-raised * 16 + stab * -2, -raised * 13 + stab * -1, 0, 0]
    elif clip == 'hurt':
        cx += [-2, -2, -1, 0][n]
        crouch = [3, 2, 1, 0][n]
        tilt = [-.1, -.05, 0, 0][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
        glow = [1.4, 1.2, 1.1, 1][n]
        legdy = [-5, -3, -1, 0] if n < 4 else [0, 0, 0, 0]
        legdy = [legdy[n]] * 4
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead'
        cx += [0, -2, -3, -3, -3, -3, -3, -3][n]
        lift = [0, 4, 0, 0, 0, 0, 0, 0][n]
        crouch = [0, 0, 6, 12, 16, 17, 17, 17][n]
        curl = [0, 0, .35, .7, 1, 1, 1, 1][n]
        glow = [1.4, 1.2, 1, .8, .55, .35, .2, .1][n]
        tilt = [0, -.1, 0, 0, 0, 0, 0, 0][n]
    cy = AY - 31 - lift + crouch

    def body(dx, dy):
        x, y = rotate(dx, dy, tilt)
        return cx + x, cy + y

    # Legs: hip -> arched knee -> foot on the ground, animated by a scuttling gait.
    def legs(side):
        out = []
        for i, (hip_off, knee_off, fx) in enumerate(SPIDER_LEGS[side]):
            phase = gait + (i % 2) * math.pi + (math.pi / 2 if side == 'far' else 0)
            foot_dx = math.cos(phase) * 5 * stride + legdx[i]
            foot_lift = max(0, math.sin(phase)) * 7 * stride - legdy[i]
            hip = body(*hip_off)
            foot = (cx + fx + foot_dx, AY - 1 - foot_lift)
            knee = body(knee_off[0] + foot_dx * .3, knee_off[1] - foot_lift * .6)
            if curl:
                # Dead legs fold up and in over the body.
                foot = (lerp(foot[0], cx + fx * .3 + (-6 if i % 2 else 8), curl), lerp(foot[1], cy - 12 - (i % 2) * 5, curl))
                knee = (lerp(knee[0], cx + fx * .8, curl), lerp(knee[1], cy - 20, curl))
            out.append((hip, knee, foot))
        return out

    far = legs('far')
    for hip, knee, foot in far:
        f.paint(capsule(hip, knee, 2., 1.6), p.ramp('far0', 'far1', 'far2'), dither=.3)
        f.paint(capsule(knee, foot, 1.6, .85), p.ramp('far0', 'far1', 'far2'), dither=.3)
    near = legs('near')

    def draw_near(indices):
        for i in indices:
            hip, knee, foot = near[i]
            f.paint(capsule(hip, knee, 2.1, 1.7), p.ramp('bas0', 'bas1', 'bas2', 'bas3'), dither=.4)
            f.paint(capsule(knee, foot, 1.7, .95), p.ramp('bas0', 'bas1', 'bas2', 'bas3'), dither=.4)
            f.dots([knee], 'lava2' if glow > .6 else 'bas3')

    draw_near([0, 1, 2, 3])
    # Abdomen, spikes, thorax.
    abd = ellipsoid(*body(-14, -1), 17, 14, -tilt)
    spikes = []
    for k, (dx, dy, hgt) in enumerate([(-25, -11, 9), (-17, -16, 11), (-8, -15, 8)]):
        bx, by = body(dx, dy)
        tipx, tipy = body(dx - 2, dy - hgt)
        spikes.append(polygon([(bx - 3, by + 2), (tipx, tipy), (bx + 3, by + 2)]))
    for sp in spikes:
        f.paint((sp, np.where(sp, .45 + .4 * (YY < cy - 14), 0)), p.ramp('bas1', 'bas2', 'bas3'), dither=.2)
    f.paint(abd, p.ramp('bas0', 'bas1', 'bas2', 'bas3', 'bas4'), dither=.5)
    cracks = Image.new('L', (W, H), 0)
    cd = ImageDraw.Draw(cracks)
    for path in [[(-27, -7), (-22, -3), (-18, -5), (-13, 1), (-8, -1)], [(-18, -5), (-16, -11)], [(-13, 1), (-15, 7), (-20, 9)], [(-25, 4), (-22, 6)]]:
        cd.line([body(*pt) for pt in path], fill=255, width=2 if glow > .5 else 1)
    crack_mask = (np.array(cracks) > 0) & abd[0]
    f.a[crack_mask] = p['lava1'] if glow < .45 else p['lava2'] if glow < 1.05 else p['lava3']
    hot = crack_mask & (DITHER > .15 * (1.3 - min(glow, 1.3)) - .05) & (glow > .8)
    f.a[hot] = p['lava4']
    thorax = ellipsoid(*body(10, 2), 11, 9.5, -tilt)
    f.paint(thorax, p.ramp('bas0', 'bas1', 'bas2', 'bas3', 'bas4'), dither=.5)
    # Head plate, fangs and eyes.
    head = ellipsoid(*body(21, 3), 8, 7, -tilt)
    f.paint(head, p.ramp('bas0', 'bas1', 'bas2', 'bas3', 'bas4'), dither=.5)
    for off in (0, 4):
        base = body(26 + off * .3, 9)
        tip = body(29 + off * .5 + (3 if clip == 'attack' else 0), 17 + (2 if clip == 'attack' else 0))
        f.paint(capsule(base, tip, 2, .7), p.ramp('fang2', 'fang'), dither=.2)
        f.dots([tip], 'lava3')
    eye_points = [(22, -1, 1.7), (27, 0, 1.5), (17, 0, 1.2), (25, -4, 1.1)]
    for i, (dx, dy, r) in enumerate(eye_points):
        x, y = body(dx, dy)
        if eyes == 'dead':
            f.dots([(x - 1, y - 1), (x + 1, y + 1), (x + 1, y - 1), (x - 1, y + 1), (x, y)], 'socket')
        elif eyes == 'blink' and i > 1:
            f.dots([(x - 1, y), (x, y)], 'socket')
        else:
            f.flat(ellipsoid(x, y, r + .6, r + .6)[0], 'eye' if eyes != 'hurt' else 'lava4', outline=True, edge='socket')
            f.dots([(x + (1 if r > 1.4 else 0), y)], 'lava1')
    if eyes in ('angry', 'hurt'):
        f.line(body(16, -4), body(28, -2), 'socket', 1)
    if clip == 'die' and n >= 4:
        for k in range(7):
            f.dots([(cx - 20 + rng.uniform(0, 40), AY - 6 - rng.uniform(0, 26 if n < 6 else 8))], 'ember')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Ash Wraith: a hooded, floating specter in a tattered robe, ember eyes, a scythe of cold steel.
# ----------------------------------------------------------------------------------------------
WRAITH = Palette({
    'rob0': '#15121d', 'rob1': '#242033', 'rob2': '#383250', 'rob3': '#50486b', 'rob4': '#746b8e',
    'void': '#08070c', 'eye': '#ff8a2a', 'eye2': '#ffd45a', 'bone0': '#a39b86', 'bone1': '#cfc7b2',
    'bone2': '#efe8d6', 'stf0': '#3b2e28', 'stf1': '#5b4638', 'stf2': '#7a6150', 'bld0': '#6e7684',
    'bld1': '#9aa3b2', 'bld2': '#cdd4df', 'bld3': '#f2f5fa', 'hem': '#ff6a1c', 'hem2': '#ffb347',
    'ash1': '#463f47', 'ash2': '#756c76', 'ash3': '#a59ca5',
})


def wraith(clip, n):
    f = Frame(WRAITH)
    p = WRAITH
    rng = rng_for('wraith', clip, n)
    phase = n * 0.9
    float_h, shift, lean, theta, eyes, flash, sag = 7., 0., 2., .15, 'open', False, 0.
    slash = 0
    hood_tilt = 0.
    glow = 1.
    if clip == 'idle':
        float_h = 7 + [0, 1.5, 3, 3.5, 2, .5][n]
        lean = 2 + [0, .5, 1, 1, .5, 0][n]
        theta = .15 + [0, .03, .06, .03, 0, -.03][n]
        eyes = 'blink' if n == 4 else 'open'
        glow = [1, 1.1, 1.2, 1.1, 1, .9][n]
    elif clip == 'walk':
        float_h = 7 + [0, 0, 2, 5, 3, 1, 0, 0][n]
        lean = [3, 4, 5, 6, 6, 5, 3, 2][n]
        theta = .2 + [0, 0, .05, .1, .05, 0, 0, 0][n]
        shift = [0, 0, 1, 2, 1, 0, 0, 0][n]
    elif clip == 'attack':
        shift = [-2, -3, -4, 1, 3, 2, 1, 0][n]
        lean = [1, 0, -1, 6, 8, 6, 3, 2][n]
        theta = [-.35, -.85, -1.2, .3, .8, .95, .7, .4][n]
        hood_tilt = [-1, -2, -3, 2, 3, 2, 1, 0][n]
        float_h = 7 + [0, 1, 2, 1, 0, 1, 2, 1][n]
        eyes = 'angry'
        glow = [1.1, 1.25, 1.4, 1.4, 1.4, 1.2, 1.05, 1][n]
        slash = 1 if n in (4, 5) else 0
    elif clip == 'hurt':
        shift = [-5, -3, -1, 0][n]
        lean = [-2, 0, 1, 2][n]
        theta = [-.3, -.1, .1, .15][n]
        flash = n == 0
        eyes = 'hurt' if n < 3 else 'angry'
        hood_tilt = [-2, -1, 0, 0][n]
        float_h = 7 + [3, 2, 1, 0][n]
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n else 'hurt'
        sag = [0, .08, .3, .55, .8, 1, 1, 1][n]
        lean = [1, -2, -3, -2, 0, 0, 0, 0][n]
        float_h = 7 * (1 - sag)
        theta = [-.3, -.5, -.9, -1.3, -1.45, -1.57, -1.57, -1.57][n]
        glow = [1.4, 1.2, 1, .8, .5, .3, .2, .1][n]
    cx = 38 + shift
    ground = AY
    hem_y = ground - float_h - 11
    hood_y = lerp(ground - 61 - float_h, ground - 14, sag) + (0 if sag < 1 else 0)
    sh_y = hood_y + 14
    if sag < 1:
        top = sh_y
        # Robe: shoulders to a ragged hem; the lower body trails back by `lean`.
        def at(t, x):
            return x - lean * t * t * 1.4
        tatters = 6
        pts = [(cx - 6, top), (cx + 11, top + 1)]
        right_x = cx + 13
        pts.append((at(.5, right_x), lerp(top, hem_y, .5)))
        pts.append((at(1, cx + 12), hem_y - 2))
        for k in range(tatters + 1):
            u = k / tatters
            x = lerp(cx + 12, cx - 20 - lean * 1.2, u)
            tip = 8 + 7 * (k % 2) + 4 * math.sin(phase + k * 1.7)
            pts.append((at(1, x), hem_y + tip * (1 - sag * .5) - (6 if k % 2 == 0 else 0)))
        pts.append((at(.5, cx - 17), lerp(top, hem_y, .5)))
        pts.append((cx - 11, top + 6))
        robe = polygon(pts)
        robe &= YY < ground - 0.5
        lum = np.clip(.18 + .72 * ((XX - (cx - 22)) / 40) * .45 + .5 * ((cx + 14 - XX) / 36) * 0 + .32 * (1 - (YY - top) / max(1, hem_y + 14 - top)) * .8, 0, 1)
        folds = np.zeros((H, W))
        for k, off in enumerate((-9, -2, 5)):
            folds += (np.abs(((XX - (cx + off) + (YY - top) * (-.1 - lean * .02)) % 14) - 7) < 1.0) * -.17
        f.paint((robe, np.clip(lum + folds, 0, 1)), p.ramp('rob0', 'rob1', 'rob2', 'rob3', 'rob4'), dither=.55)
        # Glowing hem and a few embers lifting off it.
        edge = robe & ~np.roll(robe, -2, axis=0)
        f.a[edge & (DITHER > -.15)] = p['hem']
        f.a[edge & (DITHER > .22)] = p['hem2']
        if clip != 'die':
            for k in range(5):
                f.dots([(cx - 18 + rng.uniform(0, 34), hem_y - rng.uniform(-4, 22))], 'hem2' if k % 2 else 'hem')
        # Far arm drawn as a hanging sleeve behind the body is implied by the robe's right edge.
        # Hood: head mass, the pointed tail of the hood, and a deep dark face.
    hx = cx + 4 + hood_tilt * .5
    if sag >= 1:
        hood_y = -999
    tilt = hood_tilt * .05
    hood = ellipsoid(hx, hood_y, 12.5, 14, tilt)
    tail_pts = [(hx - 7, hood_y - 9), (hx - 22 - lean * .6, hood_y - 14 + math.sin(phase) * 2), (hx - 13, hood_y + 3)]
    f.paint((polygon(tail_pts), np.where(polygon(tail_pts), .35 + .1 * np.sin(XX * .4), 0)), p.ramp('rob0', 'rob1', 'rob2', 'rob3'), dither=.3)
    f.paint(hood, p.ramp('rob0', 'rob1', 'rob2', 'rob3', 'rob4'), dither=.5)
    face = ellipsoid(hx + 4.5, hood_y + 1, 8, 10, tilt)[0]
    f.flat(face, 'void', outline=False)
    ey = hood_y + (0 if sag < .8 else 3)
    for i, x in enumerate((hx + 2, hx + 10)):
        if eyes == 'blink':
            f.line((x - 2, ey + 1), (x + 2, ey + 1), 'eye', 1)
        elif eyes == 'dead':
            if sag < .6:
                f.dots([(x, ey)], 'hem')
        else:
            h = 3 if eyes in ('open', 'hurt') else 2
            f.flat(ellipsoid(x, ey, 2.5, h)[0], 'eye')
            f.dots([(x + 1, ey)], 'eye2')
            if glow > 1.15:
                f.dots([(x - 3, ey), (x + 4, ey)], 'hem')
        if eyes == 'angry':
            f.line((x - 3, ey - 4 + (1 if i == 0 else 0)), (x + 3, ey - 4 + (0 if i == 0 else 1)), 'void', 1)
    # Scythe in the front hand: a staff, a crescent blade, and a bony hand.
    shoulder = (cx + 9 + hood_tilt * .3, sh_y + 6)
    if sag < .5:
        hand = (cx + 22 + theta * 4, sh_y + 16 - theta * 3)
        hand = (min(hand[0], cx + 24), hand[1])
        f.paint(capsule(shoulder, hand, 5., 3.6), p.ramp('rob0', 'rob1', 'rob2', 'rob3'), dither=.4)
    else:
        hand = None
    stf_len = 46
    pivot = hand or (cx + 20, ground - 6)
    along = (math.sin(theta), -math.cos(theta))
    base = (pivot[0] - along[0] * stf_len * .38, pivot[1] - along[1] * stf_len * .38)
    tip = (pivot[0] + along[0] * stf_len * .62, pivot[1] + along[1] * stf_len * .62)
    if sag >= 1:
        base, tip = (cx - 22, ground - 4), (cx + 14, ground - 4)
        along = (1., 0.)
    f.paint(capsule(base, tip, 1.5, 1.5), p.ramp('stf0', 'stf1', 'stf2'), dither=.3)
    forward = (-along[1], along[0]) if sag < 1 else (0., -1.)   # blade bulges toward the side the staff leans to
    blade = [(x * .78, y * .78) for x, y in [(0, 0), (9, -5), (19, -3), (27, 6), (31, 15), (22, 9), (13, 4), (4, 4), (-2, 5)]]
    bpts = [(tip[0] + along[0] * (x * .05) + forward[0] * x * 1 + along[0] * -y * .9, tip[1] + along[1] * (x * .05) + forward[1] * x * 1 + along[1] * -y * .9) for x, y in blade]
    bmask = polygon(bpts)
    f.paint(gradient(bmask, tip[0], tip[1] + 6, tip[0] + 22 * forward[0], tip[1] - 8, .1, .95), p.ramp('bld0', 'bld1', 'bld2', 'bld3'), dither=.35)
    if hand:
        f.paint(ellipsoid(hand[0], hand[1], 3.6, 3.2), p.ramp('bone0', 'bone1', 'bone2'), dither=.3)
        f.dots([(hand[0] + 3, hand[1] + 2), (hand[0] + 2, hand[1] + 3)], 'bone2')
    if slash:
        # A pale crescent shows the swing.
        sweep = [(cx + 20, ground - 70), (cx + 30, ground - 62), (cx + 36, ground - 46), (cx + 32, ground - 28), (cx + 28, ground - 42), (cx + 24, ground - 58)]
        sm = polygon(sweep)
        f.a[sm] = p['bld3']
        f.a[sm & (DITHER > .1)] = p['bld2']
    if clip == 'die' and sag >= 1:
        heap = ellipsoid(cx, ground - 3, 17 if n == 5 else 18, 4)
        f.paint(heap, p.ramp('ash1', 'ash2', 'ash3'), dither=.4)
        for dx, w, h in ((-9, 7, 5), (3, 8, 6), (12, 5, 4)):
            scrap = polygon([(cx + dx - w, ground - 3), (cx + dx - w * .2, ground - 3 - h), (cx + dx + w * .6, ground - 3 - h * .6), (cx + dx + w, ground - 2)])
            f.paint((scrap, np.where(scrap, .45 + .2 * (DITHER + .5), 0)), p.ramp('rob0', 'rob1', 'rob2', 'rob3'), dither=.2)
        for k in range(6 if n < 7 else 3):
            f.dots([(cx - 14 + rng.uniform(0, 28), ground - 5 - rng.uniform(0, 24 if n < 7 else 10))], 'hem2' if k % 2 else 'hem')
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Basalt Golem: stacked boulders with lava in the cracks and a molten core in the chest.
# ----------------------------------------------------------------------------------------------
GOLEM = Palette({
    'b0': '#24212a', 'b1': '#3a363f', 'b2': '#544f58', 'b3': '#746e77', 'b4': '#9a939a', 'b5': '#c0b8bd',
    'lava0': '#8c2610', 'lava1': '#d94b14', 'lava2': '#ff8b1f', 'lava3': '#ffd24b', 'lava4': '#fff2a8',
    'socket': '#2a0b0b', 'eye': '#ffb42e', 'dust': '#8a8189', 'dust2': '#b3abb0', 'ember': '#ff9d3a',
})
# Rest pose, relative to (cx, ground). Boulders are ellipsoids; limbs are capsules.
GOLEM_PARTS = {
    'leg_far': ('cap', (-6, -28), (-9, -5), 8.5, 7.5),
    'foot_far': ('ell', (-9, -4), 10.5, 5),
    'leg_near': ('cap', (9, -28), (11, -5), 9, 8),
    'foot_near': ('ell', (12, -4), 11.5, 5.5),
    'pelvis': ('ell', (1, -32), 16, 9.5),
    'arm_far': ('cap', (-18, -57), (-25, -19), 7.5, 7.5),
    'fist_far': ('ell', (-25, -17), 9.5, 9),
    'torso': ('ell', (2, -50), 22, 20),
    'head': ('ell', (9, -73), 9.5, 8.5),
    'shoulder_far': ('ell', (-17, -58), 11, 10),
    'arm_near': ('cap', (23, -57), (30, -18), 8.5, 8),
    'shoulder_near': ('ell', (23, -58), 12, 11),
    'fist_near': ('ell', (30, -16), 11, 10),
}
GOLEM_ORDER = ['leg_far', 'foot_far', 'arm_far', 'fist_far', 'shoulder_far', 'pelvis', 'leg_near', 'foot_near', 'torso', 'head', 'arm_near', 'shoulder_near', 'fist_near']
# Where each boulder ends up once the golem has fallen apart.
GOLEM_RUBBLE = {
    'leg_far': (-22, -7), 'foot_far': (-12, -4), 'leg_near': (20, -7), 'foot_near': (12, -4), 'pelvis': (0, -6),
    'arm_far': (-28, -7), 'fist_far': (-17, -7), 'torso': (-2, -11), 'head': (11, -7), 'shoulder_far': (-8, -8),
    'arm_near': (26, -7), 'shoulder_near': (5, -10), 'fist_near': (31, -6),
}
GOLEM_CRACKS = {
    'torso': [[(-14, -8), (-8, -2), (-9, 5), (-3, 11)], [(10, -12), (6, -6), (11, 0)], [(-10, -14), (-4, -11)]],
    'shoulder_near': [[(-6, -5), (0, 0), (-2, 6), (4, 8)]],
    'shoulder_far': [[(-4, -6), (1, -1), (-3, 5)]],
    'pelvis': [[(-9, -3), (-3, 1), (5, -2)]],
    'fist_near': [[(-5, -3), (0, 1)]],
    'leg_near': [[(-3, -9), (1, -3), (-1, 3)]],
}


def golem(clip, n):
    f = Frame(GOLEM)
    p = GOLEM
    rng = rng_for('golem', clip, n)
    cx = 46
    glow = 1.
    eyes = 'open'
    flash = False
    squash = 1.
    lean = 0.
    off = {k: [0., 0.] for k in GOLEM_PARTS}      # per-part offsets from the rest pose
    pose_fist_near, pose_fist_far = None, None
    rubble = 0.
    impact = 0
    step = 0.
    lift = 0.
    if clip == 'idle':
        breathe = [0, .5, 1, 1, .5, 0][n]
        off['torso'][1] = -breathe
        for k in ('head', 'shoulder_near', 'shoulder_far'):
            off[k][1] = -breathe
        glow = [.9, 1, 1.15, 1.2, 1.1, .95][n]
        eyes = 'blink' if n == 4 else 'open'
        for k in ('arm_near', 'fist_near'):
            off[k][0] = [0, 0, 1, 1, 0, 0][n]
    elif clip == 'walk':
        lift = [0, 0, 2, 4, 2, 0, 0, 0][n]
        squash = [1, 1, 1, 1, 1, .96, .93, .98][n]
        lean = [1, 1, 2, 3, 2, 0, -1, 0][n]
        sw = [-1, -.5, .6, 1, .7, 0, -.8, -1][n]
        off['leg_near'][0] = off['foot_near'][0] = sw * 7
        off['leg_far'][0] = off['foot_far'][0] = -sw * 7
        off['foot_near'][1] = -max(0, sw) * 5
        off['foot_far'][1] = -max(0, -sw) * 5
        off['fist_near'][0] = off['arm_near'][0] = -sw * 3
        off['fist_far'][0] = off['arm_far'][0] = sw * 3
        glow = 1.
    elif clip == 'attack':
        lean = [-2, -4, -5, 3, 8, 7, 3, 0][n]
        cx += [-1, -2, -3, 2, 3, 3, 1, 0][n]
        glow = [1.2, 1.4, 1.6, 1.6, 1.5, 1.2, 1, 1][n]
        eyes = 'angry'
        impact = 1 if n in (4, 5) else 0
        squash = [.99, .97, .96, 1.02, .93, .95, .98, 1][n]
        pose_fist_near = [(30, -22), (27, -48), (24, -76), (32, -50), (31, -9), (31, -8), (31, -18), (30, -16)][n]
        pose_fist_far = [(-25, -22), (-20, -48), (-15, -74), (-2, -52), (20, -9), (20, -8), (-12, -18), (-25, -17)][n]
    elif clip == 'hurt':
        flash = n == 0
        lean = [-5, -3, -1, 0][n]
        cx += [-4, -3, -1, 0][n]
        squash = [.93, .96, .99, 1][n]
        glow = [1.7, 1.4, 1.15, 1][n]
        eyes = 'hurt' if n < 3 else 'angry'
    elif clip == 'die':
        flash = n == 0
        eyes = 'dead' if n > 0 else 'hurt'
        lean = [0, -3, -4, 0, 0, 0, 0, 0][n]
        rubble = [0, 0, .3, .62, .9, 1, 1, 1][n]
        glow = [1.7, 1.3, 1.1, .85, .55, .4, .28, .18][n]
        squash = [1, .96, .9, .85, .8, .75, .75, .75][n]
    ground = AY

    def center(name, base):
        dx, dy = off[name]
        if rubble:
            # Stagger the collapse: arms and head fall first, the legs last.
            delay = {'head': 0, 'fist_near': .05, 'fist_far': .05, 'arm_near': .08, 'arm_far': .08, 'shoulder_near': .1, 'shoulder_far': .1, 'torso': .15}.get(name, .25)
            t = np.clip((rubble - delay) / (1 - delay), 0, 1) ** .85
            rx, ry = GOLEM_RUBBLE[name]
            return (lerp(base[0], rx, t) + dx, lerp(base[1], ry, t) + dy), t
        return (base[0] + dx, base[1] + dy), 0.

    def place(base, rise=True):
        # Lean tilts the figure about its feet; squash compresses it; lift raises it.
        x, y = base
        k = (-y) / 70
        return cx + x + lean * k * 1.5, ground + y * squash - lift

    drawn = {}
    for name in GOLEM_ORDER:
        spec = GOLEM_PARTS[name]
        if spec[0] == 'ell':
            (bx, by), t = center(name, spec[1])
            ox, oy = place((bx, by))
            rx, ry = spec[2], spec[3] * (1 - .3 * t)
            if name in ('fist_near', 'fist_far') and (pose_fist_near or pose_fist_far) and not rubble:
                tx, ty = pose_fist_near if name == 'fist_near' else pose_fist_far
                ox, oy = place((tx, ty))
            shape = ellipsoid(ox, oy, rx * (1 + .12 * t), ry)
        else:
            (b0x, b0y), t = center(name, spec[1])
            (b1x, b1y), _ = center(name, spec[2])
            if rubble:
                # Limbs collapse to a short horizontal chunk.
                mid = ((b0x + b1x) / 2, max(b0y, b1y))
                b0x, b0y = mid[0] - 7 * t - (1 - t) * (mid[0] - b0x), lerp(b0y, mid[1], t)
                b1x, b1y = mid[0] + 7 * t + (1 - t) * (b1x - mid[0]), lerp(b1y, mid[1], t)
            a, b = place((b0x, b0y)), place((b1x, b1y))
            if name in ('arm_near', 'arm_far') and (pose_fist_near or pose_fist_far) and not rubble:
                a = place((GOLEM_PARTS['shoulder_near' if name == 'arm_near' else 'shoulder_far'][1]))
                b = place(pose_fist_near if name == 'arm_near' else pose_fist_far)
                a = (a[0], a[1] + 2)
            shape = capsule(a, b, spec[3] * (1 - .35 * t), spec[4] * (1 - .35 * t))
        mask, lum = shape
        drawn[name] = shape
        f.paint(shape, p.ramp('b0', 'b1', 'b2', 'b3', 'b4', 'b5'), dither=.6)
        # Lava veins, clipped to this boulder.
        veins = GOLEM_CRACKS.get(name)
        if veins and glow > .15:
            img = Image.new('L', (W, H), 0)
            d = ImageDraw.Draw(img)
            ys, xs = np.nonzero(mask)
            if len(xs):
                mx, my = xs.mean(), ys.mean()
                for path in veins:
                    d.line([(mx + x * (1 - .2 * t), my + y) for x, y in path], fill=255, width=2)
                vein = (np.array(img) > 0) & mask
                col = 'lava1' if glow < .6 else 'lava2' if glow < 1.1 else 'lava3'
                f.a[vein] = p[col]
                if glow > 1.3:
                    f.a[vein & (DITHER > .1)] = p['lava4']
        if name == 'torso':
            tm = np.nonzero(mask)
            if len(tm[0]):
                tcx, tcy = tm[1].mean() + 2, tm[0].mean() + 2
                core = ellipsoid(tcx, tcy, 6.5, 8.5)
                heat = np.clip(core[1] * .5 + .5 * (1 - np.hypot((XX - tcx) / 6.5, (YY - tcy) / 8.5)), 0, 1) * min(glow, 1.4)
                f.paint((core[0] & mask, np.clip(heat * .9 + .05, 0, 1)), p.ramp('lava0', 'lava1', 'lava2', 'lava3', 'lava4'), outline=True, edge='lava0', dither=.5)
        if name == 'head':
            hm = np.nonzero(mask)
            if len(hm[0]):
                hx, hy = hm[1].mean(), hm[0].mean()
                brow = polygon([(hx - 8, hy - 3), (hx + 9, hy - 5), (hx + 9, hy - 1), (hx - 8, hy + 1)])
                f.a[brow & mask] = p['b0']
                for i, x in enumerate((hx + 1, hx + 7)):
                    if eyes == 'dead':
                        f.dots([(x, hy)], 'lava0' if glow > .3 else 'b1')
                    elif eyes == 'blink':
                        f.dots([(x - 1, hy), (x, hy), (x + 1, hy)], 'socket')
                    else:
                        f.flat(ellipsoid(x, hy, 2.2, 1.9 if eyes != 'angry' else 1.4)[0] & mask, 'eye')
                        f.dots([(x + 1, hy)], 'lava4')
                f.a[polygon([(hx - 3, hy + 4), (hx + 8, hy + 3), (hx + 7, hy + 6), (hx - 2, hy + 7)]) & mask] = p['b0']
    if impact:
        gx = cx + 30
        for k in range(9):
            a = rng.uniform(-3.1, 0)
            d = rng.uniform(6, 20) * (1 if n == 4 else 1.4)
            f.dots([(gx + math.cos(a) * d, ground - 2 + math.sin(a) * d * .8)], 'lava3' if k % 3 == 0 else 'dust2')
        f.a[ellipsoid(gx, ground - 1, 13, 3)[0] & (f.a == 0) & (DITHER > -.1)] = p['dust']
    if clip != 'die' or n < 5:
        for k in range(3):
            f.dots([(cx - 20 + rng.uniform(0, 44), ground - 40 - rng.uniform(0, 38))], 'ember')
    if clip == 'die' and n >= 4:
        for k in range(5 if n < 7 else 2):
            f.dots([(cx - 30 + rng.uniform(0, 64), ground - 4 - rng.uniform(0, 18))], 'ember')
        f.shift(0, -3)      # the rubble's outline would otherwise sit below the frame
    if flash:
        f.whiten()
    return f.a


# ----------------------------------------------------------------------------------------------
# Rendering and PixelFlow plumbing (same contract as scripts/make_ironhide_sprites.py)
# ----------------------------------------------------------------------------------------------
DRAWERS = {'wisp': (wisp, WISP), 'spider': (spider, SPIDER), 'wraith': (wraith, WRAITH), 'golem': (golem, GOLEM)}
for _kind, _pair in list(DRAWERS.items()):
    assert len(_pair[1].hex) <= 255


def render(kind):
    draw, _ = DRAWERS[kind]
    return {clip: np.array([draw(clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def rgba(grid, palette):
    colors = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] + [0 if n == 0 else 255]
                       for n, c in enumerate(palette)], dtype=np.uint8)
    return Image.fromarray(colors[grid])


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        for clip, grids in frames.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#3a2f33')
            d = ImageDraw.Draw(sheet)
            for n, grid in enumerate(grids):
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, palette), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'{kind}_{clip}.png')


def api(route, body=None):
    env = Path(os.environ.get('PIXELFLOW_ENV', '/home/serveperry/webserver/www/pixelflow/.env'))
    key = re.search(r'^PIXELFLOW_API_KEY=(\S+)', env.read_text(), re.M).group(1)
    base = os.environ.get('PIXELFLOW_API_URL', 'https://localhost/pixelflow/api/sprites/')
    req = urllib.request.Request(base + route, None if body is None else json.dumps(body).encode(),
                                 {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
        raise RuntimeError(result.get('errors', result.get('error', 'PixelFlow request failed'))) from None
    if result.get('ok') is False:
        raise RuntimeError(result.get('errors', 'PixelFlow request failed'))
    return result


def ids():
    return {s['name']: s['sprite_id'] for s in api('list')['sprites'] if s['name'].startswith(PREFIX)}


def build(kinds, replace=False):
    existing = ids()
    wanted = {PREFIX + kind + '_all' for kind in kinds}
    clash = wanted & set(existing)
    if clash and not replace:
        raise SystemExit(f'{sorted(clash)} already exist. Use export to preserve edits; --replace discards them.')
    for name in clash:
        api('delete', {'sprite_id': existing[name]})
    for kind in kinds:
        frames = render(kind)
        palette = DRAWERS[kind][1].hex
        np.savez_compressed(ROOT / f'scripts/crag_{kind}_raw.npz', **frames)
        sid = api('create', {'name': PREFIX + kind + '_all', 'width': W, 'height': H,
                            'frames': sum(count for _, count in CLIPS.values()),
                            'layers': 1, 'fps': 10, 'palette': palette, 'persist': True,
                            'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}]})['sprite_id']
        offset = 0
        try:
            for clip, (_, count) in CLIPS.items():
                for n, grid in enumerate(frames[clip]):
                    api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [
                        {'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
                offset += count
            print(kind, sid, f'{offset} frames')
        except Exception:
            api('delete', {'sprite_id': sid})
            raise


def export(kinds):
    saved = ids()
    meta_path = ASSETS / 'crags.txt'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    clips = {}
    for kind in kinds:
        packet = api('get?sprite_id=' + saved[PREFIX + kind + '_all'])
        sp = packet.get('sprite', packet)
        assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
        atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
        offset = 0
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            sheet = Image.new('RGBA', (8 * W, H), '#3a2f33')
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
            dest = ROOT / 'test-results/crag-export'
            dest.mkdir(parents=True, exist_ok=True)
            sheet.resize((sheet.width * 3 // 2, H * 3 // 2), Image.Resampling.NEAREST).save(dest / f'{kind}_{clip}.png')
        atlas.save(ASSETS / f'crags_{kind}.png', optimize=True)
    old = meta.get('kinds', [])
    meta = {'frame': [W, H], 'anchor': [AX, AY], 'kinds': [k for k in KINDS if k in set(old) | set(kinds)],
            'clips': clips, 'sprites': {**meta.get('sprites', {}), **{k: saved[PREFIX + k + '_all'] for k in kinds}}}
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    print('Exported', ', '.join(kinds), 'to client/assets/crags_<kind>.png and crags.txt')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    names = [a for a in sys.argv[2:] if a in DRAWERS] or list(DRAWERS)
    if command == 'build':
        build(names, '--replace' in sys.argv)
    elif command == 'export':
        export(names)
    elif command == 'preview':
        directory = next((a for a in sys.argv[2:] if a not in DRAWERS and not a.startswith('--')), ROOT / 'test-results/crag-preview')
        preview(names, directory)
    else:
        raise SystemExit('Usage: make_crag_sprites.py preview [kind...] [directory] | build [kind...] [--replace] | export [kind...]')
