"""Cel-shaded Coral Reliquary enemies (zone 11) for make_cathedral_sprites.py.

Style note from the TODO: cel-shaded Korean MMO anime, like the Greenmeadow slimes. Shaded ellipsoids and
capsules (the toolkit of the zone 1-8 monsters) with HARD colour bands (no dither), one dark outline per part,
big glossy eyes with a shine pixel, saturated harmonious ramps. Same 96x96 frame, foot anchor (48,90), five clips.
`python3 scripts/cathedral_reliquary_redraw.py [kind...]` writes contact sheets to test-results/reliquary-preview.
"""
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

from make_crag_sprites import (AX, AY, CLIPS, H, W, XX, YY, Frame, Palette, capsule, dilate, ellipsoid, polygon,
                               rgba)

KINDS = ('reliccrab', 'relicwarden', 'pearlwidow', 'glasscantor', 'coralregent', 'tidetemplar', 'tidecantor')
ROOT = Path(__file__).resolve().parents[1]

BASE = dict(ink='#1b1630', white='#fdfdff', shine='#fffef2')


def mk(**groups):
    colors = dict(BASE)
    for name, value in groups.items():
        if isinstance(value, str):
            colors[name] = value
        else:
            for i, c in enumerate(value):
                colors[f'{name}{i}'] = c
    return Palette(colors)


PALETTES = {
    'tidetemplar': mk(plate=('#17505f', '#2a8a9a', '#5cd2c4', '#c9fff0'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                      skin=('#c88270', '#f2b9a0', '#ffe0cf'), hair=('#243a78', '#4663c2'),
                      shell=('#b49a8e', '#f2dccb', '#fff6ea'), cloth=('#6a2646', '#a63e62', '#d8647f'), iris='#2aa5b6',
                      wave='#9ff2ff'),
    'tidecantor': mk(robe=('#133768', '#2462b2', '#4da0e4', '#a4dcff'), skin=('#c88270', '#f2b9a0', '#ffe0cf'),
                     gold=('#8c5d16', '#dba22f', '#ffe382'), chain=('#5a6783', '#a0aec6', '#e0eaf6'),
                     hair=('#1c2f5c', '#3a5aa8'), mouth=('#5a1c34', '#ff7a98'), iris='#3a74d0', wave='#9ff2ff',
                     ),
    'reliccrab': mk(shell=('#7a2c52', '#c24b6c', '#f2787f', '#ffb3a3'), leg=('#4f2142', '#823a5c', '#b4536d'),
                    cream=('#c4a28c', '#f1d9bf', '#fff4e0'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                    glass=('#1b6c86', '#35b2c6', '#9cf1ef'), glow=('#fff7bf', '#ffd979'),
                    iris='#2b3a9a', blush='#ff8fa6', dust='#e8dac6'),
    'relicwarden': mk(plate=('#4a1f35', '#8a3047', '#c24f55', '#f08462'), gold=('#7d5214', '#d4a032', '#ffe07e'),
                      leg=('#35172c', '#5d2540', '#8a3a50'), glass=('#16617a', '#2fb0bf', '#a4f5ee'),
                      glow=('#f4ffd8', '#8cf6e3'), bone=('#b79c88', '#eed6bc', '#fff3df'),
                      iris='#ff6a4d', dust='#d9c3b0'),
    'pearlwidow': mk(body=('#2c1f55', '#4b3585', '#7455b8', '#a98ae0'), pearl=('#9a86c4', '#d2b6e8', '#f5dcf3'),
                     leg=('#241947', '#3b2b72', '#5c44a0'), mark=('#4c1763', '#c43c95'),
                     gold=('#9c6a1b', '#e3ac38', '#ffe587'), fang=('#d9c6b0', '#fff2dc'),
                     coral=('#bb3f6f', '#ff7aa2'), iris='#e8397d', thread='#d8cdee'),
    'glasscantor': mk(robe=('#40236c', '#6f3eb0', '#a863e0', '#d9a2ff'), skin=('#a58bc9', '#d9c4f0', '#f8eaff'),
                      pane=('#e23f8c', '#f7a22e', '#2dc8c4', '#5a7bf0'), lead='#241238',
                      gold=('#9c6a1b', '#e3ac38', '#ffe587'), mouth=('#4a1330', '#ff7a98'),
                      iris='#e2408d', hair=('#2d1a55', '#50308c')),
    'coralregent': mk(gown=('#7c2757', '#c9427c', '#f66f9c', '#ffb2c8'), coral=('#d0a39a', '#ffdcd1', '#fff6ee'),
                      skin=('#d6907f', '#f6c0ac', '#ffe4d3'), hair=('#14697c', '#23a6b0', '#6fe6d2'),
                      gold=('#9c6a1b', '#e3ac38', '#ffe587'), pearl=('#bfaed8', '#f4ecff'),
                      glow=('#fffbd8', '#ffd5ec'), iris='#17a2a8'),
}


def lerp(a, b, t):
    return a + (b - a) * t


def timing(clip, n):
    """One shared set of animation curves; each creature interprets them."""
    sw = math.sin(n * math.pi / 4)
    T = dict(sw=sw, bob=0., lean=0., wind=0., strike=0., blink=False, flash=False, fall=0., state='open', n=n,
             clip=clip)
    if clip == 'idle':
        T['bob'] = (0, 1, 2, 2, 1, 0)[n]
        T['blink'] = n == 3
    elif clip == 'walk':
        T['bob'] = abs(sw) * 2
        T['lean'] = sw * 1.5
    elif clip == 'attack':
        T['wind'] = (.35, .7, 1, .15, 0, 0, 0, 0)[n]
        T['strike'] = (0, 0, 0, .9, 1, .7, .3, 0)[n]
        T['lean'] = (-2, -3, -4, 2, 5, 4, 2, 0)[n]
        T['state'] = 'angry'
    elif clip == 'hurt':
        T['lean'] = (-6, -4, -2, 0)[n]
        T['flash'] = n == 0
        T['state'] = 'hurt' if n < 3 else 'open'
    elif clip == 'die':
        T['fall'] = (0, .08, .2, .4, .6, .78, .9, 1)[n]
        T['flash'] = n == 0
        T['state'] = 'dead' if n > 1 else 'hurt'
    return T


class Art:
    def __init__(self, kind, clip, n, sy=1.):
        self.p = PALETTES[kind]
        self.f = Frame(self.p)
        self.T = timing(clip, n)
        self.sy = sy
        self.lift = 0.
        self.ox = 0.

    def g(self, x, y):
        return (AX + self.ox + x + self.T['lean'] * y / 60, AY - y * self.sy - self.lift)

    def r(self, group):
        k = 0
        while f'{group}{k}' in self.p.names:
            k += 1
        return self.p.ramp(*[f'{group}{i}' for i in range(k)])

    def e(self, x, y, rx, ry, group, ang=0., out=True, edge=None):
        cx, cy = self.g(x, y)
        self.f.paint(ellipsoid(cx, cy, max(rx, .6), max(ry * self.sy, .6), ang), self.r(group), outline=out,
                     edge=edge, dither=0)

    def c(self, a, b, r0, r1, group, out=True, edge=None):
        self.f.paint(capsule(self.g(*a), self.g(*b), r0, r1), self.r(group), outline=out, edge=edge, dither=0)

    def poly(self, pts, name, out=True, edge=None):
        self.f.flat(polygon([self.g(*q) for q in pts]), name, outline=out, edge=edge)

    def band(self, pts, group, out=True):
        """A polygon in two flat tones: lit upper half, shaded lower half (cel band)."""
        mask = polygon([self.g(*q) for q in pts])
        if out:
            self.f.a[dilate(mask) & ~mask] = self.p['ol']
        ys = np.nonzero(mask)[0]
        if not len(ys):
            return
        mid = (ys.min() + ys.max()) / 2
        ramp = self.r(group)
        self.f.a[mask] = ramp[1]
        self.f.a[mask & (YY < mid - (ys.max() - ys.min()) * .18)] = ramp[2]
        self.f.a[mask & (YY > mid + (ys.max() - ys.min()) * .2)] = ramp[0]

    def line(self, a, b, name, w=1):
        self.f.line(self.g(*a), self.g(*b), name, w)

    def dot(self, x, y, name, size=1):
        cx, cy = self.g(x, y)
        for dx in range(size):
            for dy in range(size):
                self.f.dots([(cx + dx, cy + dy)], name)

    def eye(self, x, y, r=3., state=None, iris='iris', look=(.7, .1)):
        state = state or self.T['state']
        if self.T['blink'] and state == 'open':
            state = 'blink'
        cx, cy = self.g(x, y)
        f, p = self.f, self.p
        if state == 'blink':
            f.line((cx - r, cy), (cx + r, cy), 'ink', 2)
            return
        if state == 'dead':
            f.line((cx - r + 1, cy - r + 1), (cx + r - 1, cy + r - 1), 'ink', 2)
            f.line((cx - r + 1, cy + r - 1), (cx + r - 1, cy - r + 1), 'ink', 2)
            return
        if state == 'hurt':
            f.line((cx - r, cy - r), (cx + 1, cy), 'ink', 2)
            f.line((cx - r, cy + r), (cx + 1, cy), 'ink', 2)
            return
        f.flat(ellipsoid(cx, cy, r, r * 1.2)[0], 'white', outline=True, edge='ink')
        f.flat(ellipsoid(cx + look[0] * r * .4, cy + look[1] * r * .3, r * .66, r * .92)[0], iris)
        f.flat(ellipsoid(cx + look[0] * r * .45, cy + look[1] * r * .3, r * .34, r * .55)[0], 'ink')
        f.dots([(cx - r * .15, cy - r * .5), (cx - r * .15 + 1, cy - r * .5)], 'shine')
        if state == 'angry':
            f.line((cx - r - 1, cy - r * 1.5), (cx + r + 1, cy - r * .7), 'ink', 2)

    def done(self):
        if self.T['flash']:
            self.f.whiten()
        return self.f.a


# ------------------------------------------------------------------------------------------------
def claw(a, wrist, ang, opening, size, group, arm_from=None, arm_group=None):
    """A crab claw: wrist ball plus two pincers pointing along `ang` (radians, up positive)."""
    if arm_from:
        a.c(arm_from, wrist, size * .55, size * .5, arm_group or group)
    d = (math.cos(ang), math.sin(ang))
    perp = (-d[1], d[0])
    gap = 1.2 + opening * size * .5
    for sgn, r1 in ((-1, size * .22), (1, size * .3)):
        base = (wrist[0] + perp[0] * sgn * gap * .5, wrist[1] + perp[1] * sgn * gap * .5)
        tip = (wrist[0] + d[0] * size * 1.9 + perp[0] * sgn * gap * (1.1 if sgn > 0 else .8),
               wrist[1] + d[1] * size * 1.9 + perp[1] * sgn * gap * (1.1 if sgn > 0 else .8))
        a.c(base, tip, size * .52, r1, group)
    a.e(wrist[0], wrist[1], size * .62, size * .62, group)


def reliccrab(clip, n):
    a = Art('reliccrab', clip, n)
    T, f = a.T, None
    sw, fall, wind, strike, bob = T['sw'], T['fall'], T['wind'], T['strike'], T['bob']
    by = 16 - fall * 7 + bob
    # six legs, three each side of a 3/4 view; they curl upward as the crab dies
    for i, (bx, dx) in enumerate(((-17, -9), (-9, -7), (5, 8), (13, 11), (-2, -5), (1, 6))):
        if clip == 'walk':
            up = max(0, math.sin(n * math.pi / 2 + i * math.pi / 2)) * 7
        else:
            up = 0
        hip = (bx, by - 3)
        knee = (bx + dx * 1.5, by - 2 + fall * 8)
        foot = (bx + dx * 1.9 * (1 - fall * .5), up + fall * (by + 8))
        if i >= 4:
            continue
        a.c(hip, knee, 3.2, 2.7, 'leg')
        a.c(knee, foot, 2.7, 1.6, 'leg')
    # far claw (behind the shell)
    far_rest = ((17, 32), .5, .35)
    far_wind = ((12, 54), 1.3, 1.)
    far_hit = ((22, 9), -.3, 0.)
    def pose(rest, w, s):
        pw = [lerp(rest[0][k], w[0][k], wind) for k in (0, 1)]
        ang = lerp(rest[1], w[1], wind)
        op = lerp(rest[2], w[2], wind)
        pw = [lerp(pw[k], s[0][k], strike) for k in (0, 1)]
        return tuple(pw), lerp(ang, s[1], strike), lerp(op, s[2], strike)
    idle_open = .3 + (.25 if clip == 'idle' and n in (2, 3) else 0)
    wr, an, op = pose(((17, 31), .55, idle_open), ((11, 55), 1.35, 1.), ((24, 8), -.25, 0.), )
    if clip == 'die':
        wr, an, op = (17 - fall * 6, 31 - fall * 18), .55 - fall * 1.5, .6
    claw(a, wr, an, op, 6.3, 'shell', arm_from=(8, by + 2), arm_group='leg')
    # shell and ridge
    a.e(0, by, 23, 13.5, 'shell')
    a.e(-2, by + 4, 17, 8, 'shell', out=False)
    for k in range(5):
        a.e(-14 + k * 5.5, by + 11 - abs(k - 2) * .9, 2.2, 2.2, 'cream', out=True)
    # reliquary case: gold gable roof, glass box, glowing pearl
    cy = by + 15
    a.poly([(-17, cy), (-2, cy), (-2, cy + 3), (-17, cy + 3)], 'gold1')
    a.band([(-16, cy + 3), (-3, cy + 3), (-3, cy + 14), (-16, cy + 14)], 'glass')
    a.poly([(-18, cy + 14), (-9.5, cy + 22), (-1, cy + 14)], 'gold2')
    pulse = 'glow1' if (clip == 'idle' and n % 2) or (clip == 'attack' and n > 2) else 'glow0'
    a.e(-9.5, cy + 8.5, 3.6, 3.6, 'glow', out=False)
    a.dot(-11, cy + 10, 'shine')
    a.f.flat(ellipsoid(*a.g(-9.5, cy + 8.5), 2.2, 2.2)[0], pulse)
    # eyes on stalks, big and shiny
    a.c((11, by + 8), (14, by + 19), 2.3, 2.1, 'shell')
    a.c((18, by + 6), (22, by + 17), 2.3, 2.1, 'shell')
    a.eye(14.5, by + 22, 4.1, iris='iris')
    a.eye(23, by + 20, 3.6, iris='iris')
    a.dot(20, by + 3, 'blush', 2)
    # near claw
    wr, an, op = pose(((27, 15), .1, idle_open), ((26, 45), 1.3, 1.), ((26, 8), -.2, 0.), )
    if clip == 'die':
        wr, an, op = (27 - fall * 10, 15 - fall * 5), .1 + fall * 1.2, .8
    claw(a, wr, an, op, 7.4, 'shell', arm_from=(14, by - 2), arm_group='leg')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(6):
            a.dot(25 + k * 2.4, 3 + (k % 2) * 3 + n - 3, 'dust', 2)
    return a.done()


def relicwarden(clip, n):
    a = Art('relicwarden', clip, n)
    a.ox = -2
    T = a.T
    fall, wind, strike, bob = T['fall'], T['wind'], T['strike'], T['bob']
    by = 27 - fall * 13 + bob
    for i, (bx, dx) in enumerate(((-16, -8), (-8, -5), (7, 6), (15, 8))):
        up = max(0, math.sin(n * math.pi / 2 + i * math.pi / 2)) * 7 if clip == 'walk' else 0
        knee = (bx + dx * 1.6, by + 1 + fall * 10)
        foot = (bx + dx * 2.1 * (1 - fall * .5), up + fall * (by + 10))
        a.c((bx, by - 6), knee, 4, 3.4, 'leg')
        a.c(knee, foot, 3.4, 2, 'leg')
        a.e(knee[0], knee[1], 3.6, 3.6, 'gold')
    # far claw: a kite shield held out in front
    sh = (29 - wind * 4 + strike * 2, by - 1)
    if clip != 'die' or fall < .5:
        a.c((10, by + 2), (sh[0] - 6, sh[1]), 3.6, 3.4, 'leg')
        a.poly([(sh[0] - 11, sh[1] + 17), (sh[0] + 11, sh[1] + 17), (sh[0] + 10, sh[1] - 8), (sh[0], sh[1] - 21),
                (sh[0] - 10, sh[1] - 8)], 'gold1')
        a.band([(sh[0] - 8, sh[1] + 14), (sh[0] + 8, sh[1] + 14), (sh[0] + 7, sh[1] - 7), (sh[0], sh[1] - 17),
                (sh[0] - 7, sh[1] - 7)], 'plate', out=False)
        a.e(sh[0], sh[1] + 1, 3.6, 4.4, 'glass')
        a.f.flat(ellipsoid(*a.g(sh[0], sh[1] + 1), 1.8, 2.4)[0], 'glow1')
        a.line((sh[0], sh[1] + 14), (sh[0], sh[1] - 15), 'gold1', 1)
    # carapace with three gold-rimmed plates and a teal heart gem
    a.e(-2, by, 23, 15, 'plate')
    for k in range(3):
        px = -14 + k * 9.5
        a.band([(px - 4.5, by + 13 - k * .8), (px + 5, by + 13 - k * .8), (px + 7, by + 2), (px - 6, by + 2)], 'plate')
        a.line((px - 4.5, by + 13 - k * .8), (px + 5, by + 13 - k * .8), 'gold1', 2)
    a.e(10, by - 3, 4.5, 5, 'glass')
    a.f.flat(ellipsoid(*a.g(10, by - 3), 2.1, 2.5)[0], 'glow1')
    a.dot(8.8, by - 1, 'shine')
    # hammer claw: raised high at rest, swung down on the strike
    wr = (lerp(lerp(30, 22, wind), 25, strike), lerp(lerp(by + 33, 66, wind), 9, strike))
    ang = lerp(lerp(1.15, 1.7, wind), -.3, strike)
    op = lerp(lerp(.3, 1., wind), 0., strike)
    if clip == 'die':
        wr, ang, op = (30 - fall * 2, by + 33 - fall * 28), 1.15 - fall * 1.4, .7
    a.c((11, by + 8), wr, 6, 4.8, 'leg')
    a.e(14, by + 11, 6.8, 6.8, 'gold')
    claw(a, wr, ang, op, 8, 'plate')
    # helmed head with a coral crest and glowing eyes
    hx, hy = 13, by + 16
    a.e(hx, hy, 10, 9, 'plate')
    for k, (dx, h, tilt) in enumerate(((-6, 8, -4), (-1, 12, -2), (4, 9, 0))):
        a.poly([(hx + dx - 3, hy + 7), (hx + dx + tilt, hy + 7 + h), (hx + dx + 3, hy + 7)], 'bone1' if k % 2 else 'gold2')
    a.poly([(hx - 3, hy + 3), (hx + 11, hy + 3), (hx + 11, hy - 3), (hx - 3, hy - 3)], 'ink', out=False)
    state = T['state']
    for dx in (1, 7.5):
        if state == 'dead':
            a.line((hx + dx - 2, hy + 1), (hx + dx + 2, hy - 2), 'glow1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy), 2.6, 1.7)[0], 'iris' if state == 'angry' else 'glow1')
            a.dot(hx + dx - 1, hy + 1, 'shine')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(6):
            a.dot(25 + k * 2.2, 3 + (k % 3) * 3 + (n - 3), 'dust', 2)
    return a.done()


def pearlwidow(clip, n):
    a = Art('pearlwidow', clip, n)
    T = a.T
    sw, fall, wind, strike, bob = T['sw'], T['fall'], T['wind'], T['strike'], T['bob']
    by = 25 - fall * 14 + bob
    feet_near = (40, 28, -18, -34)
    feet_far = (34, 22, -26, -40)
    hips = (15, 11, 7, 3)

    def legs(feet, shade, off, flip):
        for i, fx in enumerate(feet):
            up = max(0, math.sin(n * math.pi / 2 + i * math.pi / 2 + flip)) * 5 if clip == 'walk' else 0
            hip = (hips[i] + off, by + 1)
            foot = [fx, up]
            if i < 2 and clip == 'attack':
                foot = [fx + strike * 5 - wind * 8, lerp(0, 38, wind) * (1 - strike)]
            if fall:
                foot = [lerp(fx, hips[i] * .6 + 4, fall), lerp(up, by + 6 + i * 3, fall)]
            kneex = lerp(hip[0], foot[0], .62)
            kneey = by + 17 + (4 if i in (1, 2) else 0) - fall * 10
            a.c(hip, (kneex, kneey), 3.4, 2.7, shade)
            a.c((kneex, kneey), tuple(foot), 2.7, 1.3, shade)
            a.e(kneex, kneey, 2.9, 2.9, 'pearl')
    legs(feet_far, 'leg', -1, 1.4)
    # abdomen: a giant pearl with an hourglass mark
    ax_, ay_ = -19, by + 6
    a.e(ax_, ay_, 19, 17, 'pearl')
    a.e(ax_ - 5, ay_ + 7, 8, 5.5, 'pearl', out=False)
    a.poly([(ax_ - 7, ay_ + 9), (ax_ + 7, ay_ + 9), (ax_, ay_ + 1)], 'mark1', out=True, edge='mark0')
    a.poly([(ax_ - 7, ay_ - 8), (ax_ + 7, ay_ - 8), (ax_, ay_ + 1)], 'mark1', out=True, edge='mark0')
    a.dot(ax_, ay_ + 1, 'gold2', 2)
    a.dot(ax_ - 9, ay_ + 12, 'shine', 3)
    # a pearl on a silk thread swings under the abdomen
    sx = ax_ - 14 + math.sin(n * .9) * 2
    a.line((ax_ - 14, ay_ - 12), (sx, max(ay_ - 25, 4.5)), 'thread', 1)
    a.e(sx, max(ay_ - 28, 4.5), 3, 3, 'pearl')
    legs(feet_near, 'body', 0, 0)
    # cephalothorax with eyes and fangs
    hx, hy = 11, by + 3
    a.e(hx, hy, 15, 12.5, 'body')
    a.e(hx + 2, hy + 7, 8, 4.5, 'body', out=False)
    for k in range(3):
        a.dot(hx - 6 + k * 4, hy + 8 + k % 2, 'coral1', 2)
    mouth = lerp(0, 5, wind + strike)
    for sgn in (-1, 1):
        a.poly([(hx + 15 + sgn * 2.4 - 2, hy - 3), (hx + 15 + sgn * 2.4 + 2, hy - 3),
                (hx + 16 + sgn * (2.4 + mouth), hy - 12 - mouth * .6)], 'fang1')
    a.eye(hx + 6.5, hy + 3, 4.3, iris='iris')
    a.eye(hx + 15, hy + 2, 3.6, iris='iris')
    for dx, dy in ((2, 9), (7, 10), (12, 9.5)):
        a.dot(hx + dx, hy + dy, 'iris', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.e(hx + 19 + k * 2.6, hy - 4 + (k % 2) * 4, 2.2, 2.2, 'pearl')
    return a.done()


def glasscantor(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('glasscantor', clip, n, sy=1 - fall * .5)
    wind, strike, bob = T['wind'], T['strike'], T['bob']
    a.lift = 9 + bob * 1.2 - fall * 9
    # a lancet window with a pointed-arch hood and a shattered hem
    robe = [(-14, 0), (-10, 6), (-7, 1), (-3, 7), (0, 1), (3, 8), (7, 1), (10, 6), (14, 0), (14, 22), (13, 40),
            (11, 47), (12, 53), (8, 63), (0, 71), (-8, 63), (-12, 53), (-11, 47), (-13, 40), (-14, 22)]
    mask = polygon([a.g(*q) for q in robe])
    f = a.f
    inner = ~dilate(dilate(dilate(~mask)))          # 3 px frame of plain robe around the glass
    cols = [a.p['pane0'], a.p['pane1'], a.p['pane2'], a.p['pane3']]
    size = 8.
    cu = np.floor((XX + YY) / size).astype(int)
    cv = np.floor((XX - YY) / size).astype(int)
    lead = (((XX + YY) % size) < 1.1) | (((XX - YY) % size) < 1.1)
    cid = (cu + 2 * cv) % 4
    if not fall:
        f.a[dilate(mask) & ~mask] = a.p['ol']
        f.a[mask] = a.p['robe1']
        f.a[mask & ~inner & (XX > a.g(0, 0)[0] + 1)] = a.p['robe0']
        f.a[mask & ~inner & (XX < a.g(0, 0)[0] - 4)] = a.p['robe2']
        glass = mask & inner
        for k in range(4):
            f.a[glass & (cid == k)] = cols[k]
        f.a[glass & lead] = a.p['lead']
        f.a[mask & ~inner & (YY > a.g(0, 3)[1] - 1)] = f.a[mask & ~inner & (YY > a.g(0, 3)[1] - 1)]
        # a bright highlight on the left of every pane
        hi = glass & ~lead & ((XX + YY) % size < 2.4) & (cid != 3)
        f.a[hi & (cid == 0)] = a.p['shine']
    else:
        # the window bursts: each diamond pane falls on its own path
        seen = np.unique(cu[mask] * 1000 + cv[mask])
        for key in seen:
            piece = mask & (cu * 1000 + cv == key)
            k = int(key)
            dx = int(((k * 7) % 9 - 4) * fall * 3)
            dy = int(min(fall * (10 + (k * 3) % 5 * 5) * (1 - (YY[piece].mean() / 100)), 42))
            ys2, xs2 = np.nonzero(piece)
            ny, nx = np.clip(ys2 + dy, 0, H - 2), np.clip(xs2 + dx, 1, W - 2)
            moved = np.zeros_like(piece)
            moved[ny, nx] = True
            f.a[dilate(moved) & ~moved & (f.a == 0)] = a.p['ol']
            f.a[moved] = cols[int(cid[piece][0])]
    if fall < .5:
        hx, hy = 3, 51
        a.e(hx, hy, 8, 9, 'skin')
        a.poly([(hx - 9, hy + 6), (hx + 1, hy + 10), (hx + 9, hy + 5), (hx + 9, hy + 12), (hx - 9, hy + 12)],
               'hair1', out=False)
        for sgn in (-1, 1):
            x, y = hx + 2 + sgn * 3.6, hy + 1
            if T['state'] == 'open' and not T['blink']:
                f.line(a.g(x - 2, y), a.g(x + 2, y), 'ink', 2)   # a closed, singing eye
                f.line(a.g(x - 2, y), a.g(x - 3, y - 2), 'ink', 1)
            else:
                a.eye(x, y, 2.3, iris='iris')
        singing = max(wind, strike)
        a.e(hx + 3, hy - 5, 2.3 + singing * 1.6, 1.5 + singing * 2.4, 'mouth')
        a.dot(hx - 3, hy - 3, 'mouth1', 2)
    if fall < .6:
        hand = (lerp(lerp(20, 16, wind), 25, strike), lerp(lerp(27, 38, wind), 36, strike))
        a.c((10, 34), hand, 3.4, 2.8, 'robe')
        a.e(hand[0], hand[1], 3, 3, 'skin')
        a.c((hand[0] + 1, hand[1]), (hand[0] + 1, hand[1] + 17), 1.1, 1.1, 'gold')
        a.line((hand[0] + 1, hand[1] + 17), (hand[0] - 3, hand[1] + 25), 'pane2', 2)
        a.line((hand[0] + 1, hand[1] + 17), (hand[0] + 5, hand[1] + 25), 'pane2', 2)
    for k in range(5):
        ang = n * (math.pi / 3 if clip != 'idle' else math.pi / 4) * .6 + k * 2 * math.pi / 5
        if clip == 'attack':
            px, py = lerp(math.cos(ang) * 28, 18 + k * 3, strike), lerp(math.sin(ang) * 8 + 44, 44 + (k - 2) * 8, strike)
        else:
            px, py = math.cos(ang) * 30, math.sin(ang) * 8 + 40 + k * 3
        py -= fall * 28
        col = ('pane0', 'pane1', 'pane2', 'pane3', 'pane1')[k]
        a.poly([(px, py + 5), (px + 3, py), (px, py - 5), (px - 3, py)], col)
        a.dot(px - 1, py + 1, 'shine')
    return f.a if not T['flash'] else (f.whiten() or f.a)


def coralregent(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('coralregent', clip, n, sy=1 - fall * .62)
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    sway = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else sw * 2
    by = bob * .6
    hx, hy = 3, 57 + by
    # long teal hair streaming behind
    a.band([(hx - 4, hy + 6), (hx - 13 + sway, hy - 8), (hx - 19 + sway * 1.5, hy - 26), (hx - 12 + sway, hy - 34),
            (hx - 4, hy - 16), (hx + 2, hy - 5)], 'hair')
    # gown with coral growing from the hem
    a.band([(-8, 40 + by), (8, 40 + by), (13, 22), (23, 0), (-23, 0), (-13, 22)], 'gown')
    a.line((-5, 26), (-9, 5), 'gown3', 2)
    a.line((4, 28), (7, 5), 'gown0', 2)
    for k, (x, h) in enumerate(((-22, 11), (-17, 15), (-12, 8), (12, 8), (17, 14), (22, 10))):
        a.poly([(x - 3, 2), (x - 1 + sway * .2, 2 + h), (x + 1, 2 + h * .55), (x + 3.5, 2)],
               'coral1' if k % 2 else 'coral2')
    for x in (-12, -6, 0, 6, 12):
        a.e(x, 9 + abs(x) * .06, 1.6, 1.6, 'pearl')
    a.band([(-8, 44 + by), (8, 44 + by), (9, 36 + by), (-9, 36 + by)], 'gold')
    a.e(0, 47 + by, 8, 8, 'gown')
    for k in range(5):
        a.e(-6 + k * 3.2, 51 + by - abs(k - 2) * .8, 1.5, 1.5, 'pearl')
    a.c((-6, 49 + by), (3, 41 + by), 2.8, 2.4, 'skin')
    # head: big eyes, blush, tiny smile, fringe
    a.e(hx, hy, 10, 10.5, 'skin')
    a.dot(hx + 6, hy - 4, 'gown2', 3)
    a.dot(hx - 3, hy - 4, 'gown2', 3)
    a.eye(hx + 3, hy + 1, 3.5, iris='iris')
    a.eye(hx + 10, hy + 1, 2.9, iris='iris')
    if T['state'] != 'hurt':
        a.line((hx + 5, hy - 6), (hx + 8, hy - 6), 'ink', 1)
    a.poly([(hx - 11, hy + 2), (hx - 6, hy + 11), (hx + 4, hy + 8), (hx + 12, hy + 9), (hx + 7, hy + 4),
            (hx + 1, hy + 4)], 'hair2')
    a.poly([(hx - 11, hy + 2), (hx - 9, hy - 8), (hx - 6, hy - 6), (hx - 7, hy + 6)], 'hair1', out=False)
    # coral crown
    a.poly([(hx - 8, hy + 9), (hx + 9, hy + 9), (hx + 9, hy + 12), (hx - 8, hy + 12)], 'gold1')
    for k, (dx, h, tilt) in enumerate(((-7, 8, -3), (-2, 14, -1), (3, 16, 1), (8, 9, 3))):
        a.poly([(hx + dx - 2.4, hy + 12), (hx + dx + tilt, hy + 12 + h), (hx + dx + 2.4, hy + 12)],
               'coral1' if k % 2 else 'coral2')
    a.e(hx + 1, hy + 13, 2, 2, 'pearl')
    # scepter arm: drawn back in the wind-up, thrust on the strike
    hand = (lerp(lerp(20, 16, wind), 24, strike), lerp(lerp(30, 40, wind), 36, strike) + by)
    a.c((7, 41 + by), hand, 3, 2.6, 'gown')
    a.e(hand[0], hand[1], 3, 3, 'skin')
    top = (hand[0] + 1, hand[1] + 24)
    a.c((hand[0] + 1, hand[1] - 16), top, 1.3, 1.3, 'gold')
    glow = 'glow0' if (wind + strike) > .5 or (clip == 'idle' and n % 2) else 'pearl1'
    a.e(top[0], top[1] + 4, 5.5, 5.5, 'pearl')
    a.f.flat(ellipsoid(*a.g(top[0], top[1] + 4), 3.4, 3.4)[0], glow)
    a.dot(top[0] - 2, top[1] + 6, 'shine', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(top[0] + 6 + k * 2.3, top[1] + 4 + (k % 2) * 4 - k, 'glow1', 2)
    return a.done()


def tidetemplar(clip, n):
    a = Art('tidetemplar', clip, n)
    T = a.T
    sw, fall, wind, strike, bob = T['sw'], T['fall'], T['wind'], T['strike'], T['bob']
    a.sy = 1 - fall * .35
    # legs: greaves and boots, striding in the walk
    for side in (-1, 1):
        g = sw * 5 * side if clip == 'walk' else 0
        up = max(0, math.sin(n * math.pi / 2 + (side > 0) * math.pi)) * 3 if clip == 'walk' else 0
        a.c((side * 4.5, 27 + bob), (side * 5.5 + g, 3 + up), 4.3, 3.6, 'plate')
        a.e(side * 5.5 + g + 2, 2 + up, 6, 3.2, 'plate')
    # far arm: a scallop-shell shield held forward
    shx, shy = 13 + strike * 2, 35 + bob
    if fall < .6:
        a.c((6, 45 + bob), (shx - 4, shy + 4), 3.4, 3, 'plate')
        a.e(shx, shy, 11, 12, 'shell')
        for k in range(-2, 3):
            a.line((shx, shy - 11), (shx + k * 4.2, shy + 10), 'shell0', 1)
        a.e(shx, shy, 3.6, 3.6, 'gold')
    # torso, belt, tabard
    a.e(0, 40 + bob, 11.5, 14, 'plate')
    a.band([(-9, 29 + bob), (9, 29 + bob), (11, 18), (-11, 18)], 'cloth')
    a.line((-11, 28 + bob), (11, 28 + bob), 'gold1', 2)
    a.e(0, 44 + bob, 4, 4, 'gold')
    # head: open helm with a swept coral fin, big eyes
    hx, hy = 2, 61 + bob
    a.e(hx, hy, 9.5, 10, 'skin')
    a.e(hx - 1, hy + 4, 11, 8, 'plate')
    a.poly([(hx - 6, hy + 8), (hx - 15 + sw, hy + 12), (hx - 17, hy + 2), (hx - 9, hy + 3)], 'shell1')
    a.poly([(hx - 3, hy + 11), (hx - 9 + sw, hy + 20), (hx + 2, hy + 13)], 'gold2')
    a.eye(hx + 3, hy - 1, 3.2, iris='iris')
    a.eye(hx + 9, hy - 1, 2.7, iris='iris')
    a.poly([(hx - 10, hy + 3), (hx + 12, hy + 3), (hx + 12, hy + 6), (hx - 10, hy + 6)], 'plate1', out=False)
    # shoulder pauldron
    a.e(-8, 51 + bob, 7.5, 5.5, 'shell')
    # trident arm and spear: upright at rest, cocked back, then thrust forward
    hand = (lerp(lerp(21, 12, wind), 12, strike), lerp(lerp(38, 46, wind), 42, strike) + bob)
    ang = lerp(lerp(math.pi / 2, 2.0, wind), .06, strike)
    d = (math.cos(ang), math.sin(ang))
    a.c((5, 49 + bob), hand, 3.4, 3, 'plate')
    a.e(hand[0], hand[1], 3, 3, 'skin')
    tail = (hand[0] - d[0] * 14, hand[1] - d[1] * 14)
    tip = (hand[0] + d[0] * 20, hand[1] + d[1] * 20)
    a.c(tail, tip, 1.5, 1.5, 'gold')
    pr = (-d[1], d[0])
    for k in (-1, 0, 1):
        end = (tip[0] + d[0] * (9 - abs(k) * 3) + pr[0] * k * 4.5, tip[1] + d[1] * (9 - abs(k) * 3) + pr[1] * k * 4.5)
        a.c((tip[0] + pr[0] * k * 2, tip[1] + pr[1] * k * 2), end, 1.5, .9, 'gold')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            a.dot(tip[0] + 4 + k * 2, tip[1] + (k - 1) * 3, 'wave', 2)
    return a.done()


def tidecantor(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('tidecantor', clip, n, sy=1 - fall * .5)
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    sing = max(wind, strike)
    sway = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else sw * 2
    # a draped robe over a trailing hem
    a.band([(-8, 50 + bob), (8, 50 + bob), (13, 22), (16, 0), (-16, 0), (-13, 22)], 'robe')
    a.line((-4, 40), (-8, 4), 'robe0', 2)
    a.line((4, 40), (8, 4), 'robe3', 1)
    a.line((-14, 14), (14, 14), 'gold1', 2)
    # shackled wrists with chains that swing
    hands = []
    for side in (-1, 1):
        if side < 0:
            h = (-15 + sway, 36 + bob + sing * 12)
        else:
            h = (lerp(lerp(17, 14, wind), 19, strike) + sway, lerp(37, 54, sing) + bob)
        hands.append(h)
        a.c((side * 7, 47 + bob), h, 3.6, 3.2, 'robe')
        a.e(h[0], h[1], 3.4, 3.4, 'skin')
        a.e(h[0], h[1] - 3, 3.8, 2.4, 'gold')
        for k in range(1, 6):
            t = k / 6
            x = h[0] + (side * 4 + sway * .8) * math.sin(t * math.pi) + side * 2 * t
            y = h[1] - 4 - t * (h[1] - 3 - 4) + math.sin(t * math.pi) * 0
            a.e(x, max(y, 2.5), 1.7, 1.7, 'chain')
    # head: big tear-bright eyes, an open singing mouth, a tall bell-shaped hood
    hx, hy = 3, 61 + bob
    a.e(hx, hy, 9.5, 10, 'skin')
    a.dot(hx + 6, hy - 4, 'mouth1', 3)
    a.dot(hx - 3, hy - 4, 'mouth1', 3)
    for sgn in (-1, 1):
        x, y = hx + 3 + sgn * 3.8, hy + 1
        if T['state'] in ('open', 'angry') and not T['blink']:
            a.line((x - 2, y), (x + 2, y), 'ink', 2)
            a.line((x - 2, y), (x - 3, y - 2), 'ink', 1)
        else:
            a.eye(x, y, 2.5, iris='iris')
    a.e(hx + 4, hy - 6, 2 + sing * 1.8, 1.4 + sing * 2.6, 'mouth')
    a.poly([(hx - 11, hy + 3), (hx - 8, hy - 9), (hx - 5, hy - 5), (hx - 6, hy + 5)], 'hair1', out=False)
    a.band([(hx - 12, hy + 1), (hx - 10, hy + 9), (hx - 3, hy + 17), (hx + 4, hy + 15), (hx + 11, hy + 8),
            (hx + 11, hy + 3), (hx + 3, hy + 6), (hx - 5, hy + 5)], 'robe')
    a.poly([(hx - 12, hy + 1), (hx - 15, hy - 6), (hx - 10, hy - 2)], 'robe1')
    a.e(hx - 2, hy + 14, 2.2, 2.2, 'gold')
    # sound: rings spread from the mouth as it sings
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            x = hx + 12 + k * 4 + (n - 3) * 2
            for dy in (-5, 0, 5):
                a.dot(x - abs(dy) * .25, hy - 4 + dy, 'wave', 2)
    return a.done()


DRAW = dict(tidetemplar=tidetemplar, tidecantor=tidecantor, reliccrab=reliccrab, relicwarden=relicwarden, pearlwidow=pearlwidow, glasscantor=glasscantor,
            coralregent=coralregent)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def preview(kinds, out, scale=2):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        hexes = PALETTES[kind].hex
        for clip, (_, count) in CLIPS.items():
            sheet = Image.new('RGBA', (4 * W, 2 * (H + 12)), '#2c3a44')
            d = ImageDraw.Draw(sheet)
            for n in range(count):
                grid = draw(kind, clip, n)
                ox, oy = (n % 4) * W, (n // 4) * (H + 12)
                sheet.alpha_composite(rgba(grid, hexes), (ox, oy))
                d.line([(ox + AX - 3, oy + AY), (ox + AX + 3, oy + AY)], fill='#eabce1')
                ys, xs = np.nonzero(grid)
                if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > W - 2 or ys.max() > H - 2):
                    print(f'  EDGE {kind} {clip} {n}')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(
                out / f'{kind}_{clip}.png')


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, ROOT / 'test-results/reliquary-preview')
    # one lineup of every idle frame 0 for a quick side-by-side
    line = Image.new('RGBA', (len(names) * W, H), '#2c3a44')
    for i, kind in enumerate(names):
        line.alpha_composite(rgba(draw(kind, 'idle', 0), PALETTES[kind].hex), (i * W, 0))
    line.resize((line.width * 3, line.height * 3), Image.Resampling.NEAREST).save(
        ROOT / 'test-results/reliquary-preview/lineup.png')
    print('ok')
