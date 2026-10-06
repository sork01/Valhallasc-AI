#!/usr/bin/env python3
"""Inventory icons for every piece of equipment (makesprites workflow, drawn in code).

    python3 scripts/make_item_sprites.py preview [id ...]   contact sheet -> scripts/item_raw/preview.png
    python3 scripts/make_item_sprites.py build [--replace]  one PixelFlow sprite (48x48, one frame per item)
    python3 scripts/make_item_sprites.py export [--local]   read PixelFlow back (or the local cache) and write
                                                            client/assets/items.png + items.txt + client/itemicons.js

50 icons: the weapon, chest, head, shoulder and glove piece of every class (two sets each, Priest weapon and chest
only) plus the generic Ironhide Helm / Pauldrons, Duelist Gloves, Wayfarer Pants, Moonstone Necklace and Amber Ring.
Light comes from the top left. Every icon is a function of shapes (polygons, ribbons, ellipses) shaded from four-tone
ramps taken from the class sprite ramps, so the icon and the worn art read as the same object.

`build` recreates the PixelFlow sprite and discards editor edits; `export` reads PixelFlow, so edits survive.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'scripts' / 'item_raw'
N = 48
SS = 4                      # supersampling for polygon masks
OUT = (24, 18, 32)          # outer outline


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


RAMPS = {name: [rgb(h) for h in hs] for name, hs in dict(
    steel=['#3a4658', '#6a7a92', '#aebdd2', '#eef4ff'],
    gold=['#6e4a12', '#b0801f', '#e8b840', '#fff0a0'],
    leather=['#2a1a16', '#47291f', '#6e4331', '#9a6a4c'],
    crimson=['#5a0f1c', '#9a1f30', '#d83c4a', '#ff8a8a'],
    azure=['#0f2a5a', '#1f4f9a', '#3c82d8', '#8ac4ff'],
    plume=['#7a1230', '#c22850', '#f05a7a', '#ffc0c8'],
    wing=['#8a9ab0', '#c4d0e0', '#f0f5ff', '#ffffee'],
    glow=['#0f8a96', '#2fd0d8', '#8af0ee', '#e4ffff'],
    wood=['#3a2214', '#5e3a22', '#8a5a34', '#b98a58'],
    blue=['#16295a', '#2a4c9a', '#4a80d8', '#9cc8ff'],
    violet=['#2a1650', '#4d2a8a', '#7a4cc0', '#b894f0'],
    shadow=['#120f1e', '#241c38', '#3a2d54', '#5a4a7a'],
    moon=['#3a3858', '#6a6890', '#a8a6cc', '#e4e2fa'],
    cream=['#8a7a64', '#c4b498', '#e8dcc0', '#fff8e6'],
    green=['#143a22', '#24633a', '#3c9a56', '#8ad47a'],
    teal=['#0a3a44', '#176b72', '#2bb0a8', '#8af0e0'],
    fur=['#6a6a78', '#a0a0b0', '#d0d0dc', '#f6f6ff'],
    bronze=['#3a2410', '#6e4620', '#a8742e', '#dca860'],
    amber=['#6a2a08', '#b8581a', '#f09a2c', '#ffe080'],
    bone=['#6a5c44', '#a8977a', '#d8c8a4', '#fff2d4'],
    ink=['#0c0a12', '#1c1828', '#2e2840', '#463e5e'],
    pearl=['#5a5a82', '#9a9ac4', '#d4d4f2', '#ffffff'],
    # the game master's golden set (same ramps as the worn art in make_warrior_cel_sprites.py)
    gilt=['#8c5c12', '#d9a226', '#ffd84e', '#fff8c4'],
    brocade=['#5e3808', '#a8700f', '#d89a1c', '#f6d870'],
    ruby=['#58081a', '#a8142e', '#e8344e', '#ff9ca8'],
    ivory=['#8c8678', '#cac4b6', '#f4f0e4', '#fffcf2'],
).items()}
R = type('R', (), RAMPS)
BAYER = np.array([[0, 2], [3, 1]]) / 4.0 - .375


def bez(pts, n=16):
    out = []
    for k in range(n + 1):
        t = k / n
        q = list(pts)
        while len(q) > 1:
            q = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(q, q[1:])]
        out.append(q[0])
    return out


def sym(half):
    """left half, top to bottom, mirrored about the centre line x = 24"""
    return list(half) + [(N - x, y) for x, y in reversed(half)]


def ribbon(pts, width):
    """polygon around a centre line; width is a number or f(t) -> full width"""
    w = (lambda t: width) if not callable(width) else width
    left, right = [], []
    for k, (x, y) in enumerate(pts):
        a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        h = w(k / max(1, len(pts) - 1)) / 2
        left.append((x + nx * h, y + ny * h))
        right.append((x - nx * h, y - ny * h))
    return left + right[::-1]


def strip(a, b, prof):
    """straight shape from a to b; prof = [(t, half width)] mirrored about the axis"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy)
    ux, uy, nx, ny = dx / d, dy / d, -dy / d, dx / d
    pt = lambda t, o: (a[0] + dx * t + nx * o, a[1] + dy * t + ny * o)
    return [pt(t, h) for t, h in prof] + [pt(t, -h) for t, h in reversed(prof)]


class Painter:
    def __init__(self):
        self.rgb = np.zeros((N, N, 3), np.uint8)
        self.a = np.zeros((N, N), bool)

    @staticmethod
    def mask(pts):
        im = Image.new('L', (N * SS, N * SS), 0)
        ImageDraw.Draw(im).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
        return np.asarray(im.resize((N, N), Image.BOX)) >= 128

    def fill(self, m, ramp, tone=None, flat=False, edge=True, light=(.45, .55)):
        if not m.any():
            return m
        if edge:
            ring = ndi.binary_dilation(m, iterations=1) & ~m & self.a
            self.rgb[ring] = ramp[0]
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        gx, gy = (np.arange(N)[None, :] - x0) / max(1, x1 - x0), (np.arange(N)[:, None] - y0) / max(1, y1 - y0)
        d = ndi.distance_transform_edt(m)
        v = .62 * (1 - (light[0] * gx + light[1] * gy)) + .38 * np.minimum(1, d / 3.5) - .05
        v = v + np.tile(BAYER, (N // 2, N // 2)) * .09
        t = np.digitize(v, [.30, .52, .74]) if tone is None else np.full((N, N), tone)
        if flat:
            t = np.full((N, N), 1 if tone is None else tone)
        idx = np.nonzero(m)
        for y, x in zip(*idx):
            self.rgb[y, x] = ramp[int(t[y, x])]
        self.a |= m
        return m

    def poly(self, pts, ramp, **kw):
        return self.fill(self.mask(pts), ramp, **kw)

    def ell(self, cx, cy, rx, ry, ramp, **kw):
        return self.poly([(cx + rx * math.cos(a / 24 * math.pi), cy + ry * math.sin(a / 24 * math.pi)) for a in range(48)], ramp, **kw)

    def line(self, a, b, w0, ramp, w1=None, **kw):
        w1 = w0 if w1 is None else w1
        return self.poly(ribbon([a, b], lambda t: w0 + (w1 - w0) * t), ramp, **kw)

    def rect(self, x0, y0, x1, y1, col):
        """exact pixel rectangle [x0, x1) x [y0, y1) in a colour (tuple or ramp tone)"""
        self.rgb[int(y0):int(y1), int(x0):int(x1)] = col
        self.a[int(y0):int(y1), int(x0):int(x1)] = True

    def dots(self, pts, col):
        for x, y in pts:
            if 0 <= x < N and 0 <= y < N:
                self.rgb[int(y), int(x)] = col
                self.a[int(y), int(x)] = True

    def paint_over(self, m, col):
        """recolour only pixels that already exist (a stripe, a rune, a stitch)"""
        m = m & self.a
        self.rgb[m] = col

    def mirror_from(self, q):
        """composite a horizontally mirrored copy of another painter underneath what is drawn here"""
        fa, fr = q.a[:, ::-1], q.rgb[:, ::-1]
        keep = fa & ~self.a
        self.rgb[keep] = fr[keep]
        self.a |= fa

    def image(self):
        out = np.zeros((N, N, 4), np.uint8)
        body = self.a
        outline = ndi.binary_dilation(body, structure=ndi.generate_binary_structure(2, 1)) & ~body
        out[body, :3] = self.rgb[body]
        out[body, 3] = 255
        out[outline, :3] = OUT
        out[outline, 3] = 255
        return out


ICONS = {}


def icon(id_, kind):
    def deco(fn):
        ICONS[id_] = (kind, fn)
        return fn
    return deco


# ---------------------------------------------------------------- shared pieces
def gem(p, x, y, ramp, r=1.8):
    p.ell(x, y, r, r * 1.15, ramp, edge=True)
    p.dots([(x - r * .35, y - r * .5)], ramp[3])


def hand(p, skin, cuff, tips=None, fingers=(9, 6, 5, 8), ex=(0, 0, 0, 0), thumb=True, tone=None):
    """a glove pointing up: back of the hand, four fingers, a thumb and a cuff drawn by the caller"""
    p.line((13.5, 29), (7.5, 21), 5.5, skin, 4.6) if thumb else None
    for x, top, extra in zip((16.6, 21.6, 26.6, 31.6), fingers, ex):
        p.poly(ribbon([(x, 24), (x, top + 2)], 4.6), skin, tone=tone)
        p.ell(x, top + 2, 2.3, 2.3, skin, tone=tone)
    p.poly([(14, 22), (34, 22), (35.5, 33), (32, 39), (16, 39), (12.5, 33)], skin, tone=tone)


# ---------------------------------------------------------------- headgear
@icon('warrior_headgear_crimson', 'headgear')
def _(p):
    p.poly(bez([(17, 17), (14, 5), (24, 0.5), (34, 5), (31, 17)], 14) + [(24, 15)], R.plume)
    p.poly([(22, 3), (25, 3), (27, 14), (22, 14)], R.plume, tone=3, edge=False)
    p.poly(sym([(24, 9.5), (16, 11.5), (11, 18), (9.5, 26), (10, 34)]), R.steel)
    p.poly([(22, 10), (26, 10), (26, 24), (22, 24)], R.crimson)
    p.poly([(9.5, 25), (24, 23.2), (38.5, 25), (38.5, 29.5), (24, 27.7), (9.5, 29.5)], R.gold)
    p.poly([(10, 29), (18.5, 28), (18.5, 40), (14, 38.5), (10, 33)], R.steel)
    p.poly([(38, 29), (29.5, 28), (29.5, 40), (34, 38.5), (38, 33)], R.steel)
    p.poly([(22.3, 27.5), (25.7, 27.5), (25.7, 39), (24, 41.5), (22.3, 39)], R.steel)
    p.rect(18.5, 31, 22, 33.5, R.ink[0]); p.rect(26, 31, 29.5, 33.5, R.ink[0])
    gem(p, 24, 25.4, R.crimson, 1.6); p.dots([(12, 27), (36, 27)], R.gold[3])


@icon('warrior_headgear_azure', 'headgear')
def _(p):
    for s in (0, 1):
        f = (lambda x: x) if s == 0 else (lambda x: N - x)
        for k, (y, tipx, tipy) in enumerate([(24, 1.5, 9), (26, 1, 15), (28, 2.5, 21)]):
            p.poly([(f(11), y + 3), (f(9), y - 3), (f(tipx + 2), tipy - 4), (f(tipx), tipy), (f(11), y + 6)], R.wing, edge=True)
    p.poly(sym([(24, 12), (16, 14), (12, 19), (10.5, 27), (11, 35)]), R.steel)
    p.poly([(10.5, 24.5), (24, 22), (37.5, 24.5), (37.5, 29), (24, 26.5), (10.5, 29)], R.azure)
    p.poly([(22.5, 12), (25.5, 12), (25.5, 22.5), (22.5, 22.5)], R.gold)
    p.poly([(11, 29), (18.5, 28), (18.5, 40), (14.5, 38.5), (11, 33)], R.steel)
    p.poly([(37, 29), (29.5, 28), (29.5, 40), (33.5, 38.5), (37, 33)], R.steel)
    p.poly([(22.3, 26.5), (25.7, 26.5), (25.7, 39), (24, 41.5), (22.3, 39)], R.steel)
    p.rect(18.5, 31, 22, 33.5, R.ink[0]); p.rect(26, 31, 29.5, 33.5, R.ink[0])
    gem(p, 24, 24.4, R.azure, 1.7)


@icon('mage_headgear_apprentice', 'headgear')
def _(p):
    p.ell(24, 35, 21, 6, R.blue)
    p.poly(ribbon(bez([(24, 34), (23, 24), (26, 14), (36, 11)], 22), lambda t: 22 * (1 - t) ** .85 + 1.6), R.blue)
    p.poly([(12.5, 30), (24, 32.5), (35.5, 30), (36, 35), (24, 38), (12, 35)], R.leather)
    p.poly([(21.5, 32), (26.5, 32), (26.5, 37), (21.5, 37)], R.gold); p.rect(23, 33.5, 25, 35.5, R.ink[0])
    p.dots([(20, 23), (19, 24), (20, 24), (21, 24), (20, 25)], R.gold[3]); p.dots([(27, 19), (26, 20), (27, 20), (28, 20), (27, 21)], R.gold[2])


@icon('mage_headgear_runic', 'headgear')
def _(p):
    p.poly(bez([(3, 24), (9, 37), (24, 40), (45, 24)], 14) + bez([(45, 24), (40, 36), (24, 36), (3, 24)], 14)[1:], R.violet)
    p.poly(ribbon([(24, 35), (24, 20), (23, 9), (25, 3)], lambda t: 20 * (1 - t) ** .7 + 1.4), R.violet)
    p.poly([(14, 31), (24, 33.5), (34, 31), (34.5, 35.5), (24, 38), (13.5, 35.5)], R.gold)
    p.ell(24, 22, 4.2, 4.2, R.gold, tone=2); p.ell(25.6, 22, 3.4, 3.8, R.violet, tone=1, edge=False)
    p.poly([(24, 8), (25, 10.5), (27.5, 10.5), (25.5, 12), (26.3, 14.8), (24, 13), (21.7, 14.8), (22.5, 12), (20.5, 10.5), (23, 10.5)], R.gold, tone=3)
    p.dots([(18, 16), (30, 27), (17, 27)], R.glow[3])
    p.rect(6, 29, 8, 31, R.gold[2]); p.rect(40, 29, 42, 31, R.gold[2])


@icon('assassin_headgear_shadow', 'headgear')
def _(p):
    p.poly(ribbon(bez([(9, 22), (10, 33), (4, 38), (7, 46)], 14), lambda t: 7 - 6 * t), R.crimson)
    p.poly(ribbon(bez([(39, 22), (38, 33), (44, 38), (41, 46)], 14), lambda t: 7 - 6 * t), R.crimson)
    p.poly(ribbon(bez([(6, 22), (14, 15), (34, 15), (42, 22)], 20), 9), R.ink)
    p.poly([(15, 14), (33, 14), (31, 28), (24, 31), (17, 28)], R.steel)
    p.poly([(17.5, 17), (30.5, 17), (29.5, 20.5), (18.5, 20.5)], R.steel, tone=0, edge=False)
    gem(p, 24, 24.5, R.crimson, 2.2)
    p.dots([(18, 16), (30, 16)], R.steel[3])


@icon('assassin_headgear_moon', 'headgear')
def _(p):
    p.poly(ribbon(bez([(14, 29), (11, 38), (14, 44), (11, 47)], 10), lambda t: 6 - 3 * t), R.pearl)
    p.poly(ribbon(bez([(34, 29), (37, 38), (34, 44), (37, 47)], 10), lambda t: 6 - 3 * t), R.pearl)
    p.poly(ribbon(bez([(5, 31), (10, 36), (38, 36), (43, 31)], 20), 5), R.moon)
    for s in (0, 1):
        f = (lambda x: x) if s == 0 else (lambda x: N - x)
        horn = bez([(f(7), 31), (f(2), 17), (f(11), 6), (f(17), 4)], 14) + bez([(f(15), 8), (f(8), 14), (f(10), 24), (f(11), 31)], 10)
        p.poly(horn, R.steel)
    p.poly([(24, 24), (30, 31), (24, 40), (18, 31)], R.moon)
    gem(p, 24, 31.5, R.violet, 3.0)
    p.dots([(22.6, 29.6)], R.violet[3])


@icon('hunter_headgear_scout', 'headgear')
def _(p):
    p.poly(strip((25, 29), (40, 2), [(0, 1.2), (.15, 3.6), (.5, 6), (.8, 5), (1, 0)]), R.plume)
    p.poly(strip((26, 28), (40, 3), [(0, .6), (.5, 1.1), (1, 0)]), R.bone, flat=True, tone=2)
    p.line((26, 29), (38, 8), 1.3, R.bone, tone=3, edge=False)
    p.poly(ribbon(bez([(4, 32), (10, 24), (38, 24), (44, 32)], 22), 8), R.green)
    p.poly(ribbon(bez([(4, 33), (8, 28), (14, 27)], 6), 4.5), R.leather)
    p.poly([(21, 25), (28, 25), (28, 32), (21, 32)], R.gold); p.rect(23, 27, 26, 30, R.ink[0])
    p.dots([(12, 28), (16, 26), (32, 26), (36, 28)], R.leather[3])
    p.line((9, 33), (7, 44), 2.4, R.leather); p.ell(7, 45, 1.8, 1.8, R.bone)
    p.line((14, 33), (14, 41), 2.2, R.leather, edge=True); p.ell(14, 42, 1.6, 1.6, R.green, tone=3)


@icon('hunter_headgear_warden', 'headgear')
def _(p):
    for x, s in ((12, 1), (36, -1)):
        p.poly([(x - 6 * s, 20), (x - 7 * s, 3), (x + 4 * s, 12), (x + 6 * s, 20)], R.teal)
        p.poly([(x - 4 * s, 17), (x - 4.5 * s, 7), (x + 2 * s, 13), (x + 3 * s, 17)], R.crimson, tone=2)
    p.poly(sym([(24, 9), (14, 11), (8.5, 19), (7, 29), (9, 36), (14, 42)]), R.teal)
    p.poly(sym([(24, 14), (17, 16), (12.5, 23), (12, 31), (17, 37), (24, 38)]), R.fur)
    p.poly(sym([(24, 27), (19, 31), (17.5, 38), (21, 44), (24, 45)]), R.wing)
    p.poly([(21.3, 33.5), (26.7, 33.5), (24, 38)], R.ink, flat=True, tone=0)
    p.poly([(14, 22), (21, 25), (20.5, 28), (14, 27)], R.ink, flat=True, tone=0, edge=False)
    p.poly([(34, 22), (27, 25), (27.5, 28), (34, 27)], R.ink, flat=True, tone=0, edge=False)
    p.dots([(16, 24), (31, 24)], R.glow[3])
    p.line((24, 9), (24, 18), 2.2, R.teal, tone=3, edge=False)


@icon('headgear_upgrade', 'headgear')
def _(p):
    p.poly(sym([(24, 6), (14, 8.5), (8, 17), (6.5, 28), (9, 38)]), R.bronze)
    for x in (13, 18.5, 24, 29.5, 35):
        p.poly(ribbon(bez([(24, 6.5), (24 + (x - 24) * .55, 17), (x, 34)], 10), 1.5), R.bronze, tone=0, edge=False)
    p.poly([(21, 7), (27, 7), (27, 30), (24, 33), (21, 30)], R.steel)
    p.poly([(7, 29), (24, 25), (41, 29), (41, 34), (24, 31), (7, 34)], R.steel)
    p.poly([(10, 34), (20, 32), (20, 42), (14, 40.5), (10, 37)], R.bronze)
    p.poly([(38, 34), (28, 32), (28, 42), (34, 40.5), (38, 37)], R.bronze)
    p.rect(15, 28, 21, 30, R.ink[0]); p.rect(27, 28, 33, 30, R.ink[0])
    p.dots([(10, 31), (38, 31), (24, 11), (24, 17), (24, 23)], R.gold[3])


# ---------------------------------------------------------------- shoulders (a pair, the right drawn behind)
def pair(draw):
    def wrapped(p):
        q = Painter(); draw(q)
        p.mirror_from(q)
        draw(p)
    return wrapped


def shoulders(id_):
    def deco(fn):
        icon(id_, 'shoulders')(pair(fn))
        return fn
    return deco


@shoulders('warrior_shoulders_crimson')
def _(p):
    p.poly(bez([(3, 33), (2, 15), (14, 9), (25, 14)], 12) + [(24, 36), (12, 39)], R.crimson)
    p.poly([(4, 26), (13, 22), (24, 25), (24, 30), (12, 28), (4, 31)], R.steel)
    p.poly([(5, 33), (14, 29.5), (24, 32), (24, 37), (13, 35.5), (6, 38)], R.steel)
    gem(p, 13, 17, R.gold, 2.4)
    p.dots([(7, 24), (19, 23)], R.gold[3])


@shoulders('warrior_shoulders_azure')
def _(p):
    p.poly(bez([(7, 35), (5, 19), (16, 13), (25, 18)], 12) + [(24, 36), (14, 40)], R.azure)
    p.poly([(7, 30), (15, 26), (24, 29), (24, 34), (15, 32), (8, 36)], R.steel)
    for k, (tx, ty) in enumerate([(1, 10), (0, 17), (2, 24)]):
        p.poly([(10, 20 + k * 3), (tx + 3, ty - 2), (tx, ty + 2), (11, 25 + k * 3)], R.wing)
    gem(p, 15, 22, R.gold, 2.2)


@shoulders('mage_shoulders_apprentice')
def _(p):
    p.poly(bez([(3, 34), (3, 17), (13, 10), (25, 12)], 12) + [(25, 36)] + [(x, y + (2 if int(x) % 2 else 0)) for x, y in [(22, 38), (18, 36), (14, 39), (10, 36), (6, 39)]], R.blue)
    p.poly(ribbon(bez([(4, 31), (13, 24), (25, 25)], 10), 4), R.cream)
    p.rect(22, 33, 26, 38, R.gold[1]); gem(p, 24, 32, R.gold, 1.6)
    p.dots([(9, 17), (15, 16)], R.blue[3])


@shoulders('mage_shoulders_runic')
def _(p):
    p.poly(bez([(4, 33), (3, 14), (15, 7), (25, 13)], 12) + [(24, 35), (12, 38)], R.violet)
    p.poly(ribbon(bez([(4, 31), (13, 24), (25, 27)], 10), 3.4), R.gold)
    p.poly([(13, 4), (17, 12), (13, 15), (9, 12)], R.glow)
    p.dots([(9, 20), (15, 19), (20, 22)], R.glow[3]); p.rect(7, 32, 9, 34, R.gold[3]); p.rect(15, 32, 17, 34, R.gold[3])


@shoulders('assassin_shoulders_shadow')
def _(p):
    p.poly(bez([(3, 35), (3, 16), (11, 10), (24, 15)], 12) + [(24, 37), (12, 40)], R.ink)
    p.poly([(4, 29), (13, 24), (24, 28), (24, 33), (13, 29.5), (5, 34)], R.shadow)
    p.poly([(9, 9), (12, 0.5), (16, 10)], R.steel); p.poly([(16, 12), (21, 4), (23, 15)], R.steel)
    p.line((4, 34.5), (24, 37.5), 1.6, R.crimson, edge=False)
    p.dots([(8, 21), (14, 19)], R.shadow[3])


@shoulders('assassin_shoulders_moon')
def _(p):
    p.poly(bez([(4, 36), (2, 18), (12, 10), (25, 15)], 12) + [(24, 36), (12, 40)], R.moon)
    p.poly(bez([(3, 32), (1, 14), (10, 3), (19, 2)], 14) + bez([(15, 6), (8, 12), (8, 24), (10, 33)], 10), R.steel)
    gem(p, 16, 25, R.violet, 2.2)
    p.dots([(9, 18), (12, 14)], R.moon[3])


@shoulders('hunter_shoulders_scout')
def _(p):
    p.poly(bez([(3, 34), (3, 16), (12, 10), (25, 13)], 12) + [(25, 33), (22, 40), (16, 36), (10, 41), (4, 37)], R.leather)
    p.poly(ribbon(bez([(4, 21), (13, 15), (25, 17)], 10), 4), R.green)
    p.line((11, 26), (11, 36), 1.4, R.bone, edge=False); p.line((17, 25), (17, 35), 1.4, R.bone, edge=False)
    p.rect(9, 24, 14, 26, R.bone[2]); p.dots([(10, 29), (12, 29)], R.leather[0])


@shoulders('hunter_shoulders_warden')
def _(p):
    p.poly(bez([(4, 34), (3, 16), (13, 9), (25, 14)], 12) + [(24, 35), (12, 38)], R.steel)
    p.poly([(5, 29), (14, 24.5), (25, 28), (25, 33), (14, 29), (6, 34)], R.teal)
    p.poly(bez([(1, 22), (4, 11), (14, 6), (26, 11)], 12) + [(26, 17), (22, 21), (19, 17), (15, 22), (11, 17), (7, 22), (4, 18), (2, 24)], R.fur)
    p.dots([(10, 31), (18, 31)], R.gold[3])


@shoulders('shoulders_upgrade')
def _(p):
    p.poly(bez([(3, 34), (3, 14), (14, 8), (25, 13)], 12) + [(24, 38), (12, 40)], R.bronze)
    for x in (9, 15, 21):
        p.poly(ribbon(bez([(x - 1, 34), (x - 3, 22), (x + 1, 11)], 8), 1.6), R.bronze, tone=0, edge=False)
    p.poly([(4, 26), (24, 23), (24, 29), (5, 32)], R.steel)
    p.poly([(7, 11), (9, 2), (12, 10)], R.steel); p.poly([(17, 9), (20, 1.5), (22, 12)], R.steel)
    p.dots([(6, 28), (12, 27), (18, 26)], R.gold[3])


# ---------------------------------------------------------------- gloves
def glove(id_):
    def deco(fn):
        icon(id_, 'gloves')(fn)
        return fn
    return deco


@glove('warrior_gloves_crimson')
def _(p):
    hand(p, R.steel, None)
    for y in (13, 18):
        p.poly(ribbon([(14.5, y), (33.7, y)], 1.4), R.steel, tone=0, edge=False)
    p.poly([(12, 37), (36, 37), (39, 46), (9, 46)], R.crimson)
    p.poly([(12, 34), (36, 34), (36, 38), (12, 38)], R.crimson, tone=2)
    p.rect(11, 38, 37, 40, R.gold[2]); p.dots([(15, 24), (22, 24), (28, 24)], R.gold[3])


@glove('warrior_gloves_azure')
def _(p):
    hand(p, R.steel, None)
    for y in (12, 17):
        p.poly(ribbon([(14.5, y), (33.7, y)], 1.4), R.azure, tone=1, edge=False)
    p.poly([(12, 37), (36, 37), (38, 46), (10, 46)], R.azure)
    for k, (tx, ty) in enumerate([(41, 33), (45, 38), (44, 44)]):
        p.poly([(36, 37 + k * 2.4), (tx, ty), (36, 40 + k * 2.4)], R.wing)
    gem(p, 24, 42, R.gold, 1.8); p.rect(11, 38, 37, 39, R.gold[2])


@glove('mage_gloves_apprentice')
def _(p):
    hand(p, R.blue, None)
    p.poly([(11, 36), (37, 36), (38, 45), (10, 45)], R.cream)
    p.poly(ribbon([(10.5, 37), (37.5, 37)], 1.4), R.blue, tone=1, edge=False)
    p.ell(24, 30, 2.2, 2.2, R.gold)
    p.dots([(18, 14), (22, 12)], R.blue[3])


@glove('mage_gloves_runic')
def _(p):
    hand(p, R.violet, None)
    p.poly([(11, 35), (37, 35), (39, 46), (9, 46)], R.violet, tone=1)
    p.poly(ribbon([(10, 36.5), (38, 36.5)], 2.4), R.gold)
    p.rect(10, 44, 38, 46, R.gold[2])
    p.poly([(24, 24), (28, 29), (24, 33), (20, 29)], R.glow)
    p.dots([(24, 29)], R.glow[3]); p.dots([(17, 15), (27, 11)], R.glow[3])


@glove('assassin_gloves_shadow')
def _(p):
    hand(p, R.ink, None, fingers=(15, 12, 11, 14))
    for x, top in zip((16.6, 21.6, 26.6, 31.6), (15, 12, 11, 14)):
        p.poly(strip((x, top + 2), (x + (x - 24) * .08, top - 9), [(0, 1.7), (.5, 1.1), (1, 0)]), R.steel, edge=True)
    p.poly([(12, 35), (36, 35), (38, 46), (10, 46)], R.shadow)
    for y in (36, 41):
        p.line((11, y), (37, y + 2.2), 2.6, R.crimson, edge=False)
    p.dots([(18, 27), (24, 27), (30, 27)], R.steel[2])


@glove('assassin_gloves_moon')
def _(p):
    hand(p, R.moon, None)
    p.poly([(12, 35), (36, 35), (38, 46), (10, 46)], R.pearl)
    p.poly(bez([(10, 38), (1, 27), (4, 14), (9, 10)], 12) + bez([(8, 17), (7, 24), (11, 32)], 6), R.steel)
    gem(p, 24, 40.5, R.violet, 2.3)
    p.line((14, 24), (34, 24), 1.4, R.steel, edge=False)


@glove('hunter_gloves_scout')
def _(p):
    hand(p, R.leather, None)
    for x, top in zip((16.6, 21.6, 26.6, 31.6), (9, 6, 5, 8)):
        p.poly([(x - 2.3, top + 1), (x + 2.3, top + 1), (x + 2.3, top + 7), (x - 2.3, top + 7)], R.bone, tone=1, edge=False)
    p.poly([(11.5, 35), (36.5, 35), (37, 47), (11, 47)], R.leather)
    for y in (38, 43):
        p.poly(ribbon([(11, y), (37, y)], 2.8), R.green, edge=True)
        p.rect(23, y - 1.5, 26, y + 1.5, R.gold[2])
    p.line((12, 36), (12, 47), 1, R.bone, edge=False)


@glove('hunter_gloves_warden')
def _(p):
    hand(p, R.teal, None)
    for y in (14, 19):
        p.poly(ribbon([(14.5, y), (33.7, y)], 1.6), R.steel, tone=2, edge=False)
    p.poly(bez([(9, 34), (7, 39), (9, 41), (12, 38)], 6) + bez([(12, 38), (14, 42), (17, 38), (19, 43)], 6) + bez([(19, 43), (22, 40), (24, 44), (27, 40)], 6) + bez([(27, 40), (30, 43), (32, 39), (35, 43)], 6) + bez([(35, 43), (37, 40), (40, 38), (39, 34)], 6) + [(37, 34), (11, 34)], R.fur)
    p.poly([(11, 41), (37, 41), (38, 47), (10, 47)], R.teal)
    p.dots([(18, 28), (30, 28)], R.glow[3])


@glove('gloves_upgrade')
def _(p):
    hand(p, R.leather, None, tone=None)
    p.poly([(11, 34), (37, 34), (38, 46), (10, 46)], R.cream)
    p.poly(ribbon([(10.5, 37), (37.5, 37)], 2), R.leather, edge=False)
    p.poly([(21.5, 33.5), (26.5, 33.5), (26.5, 40), (21.5, 40)], R.gold); p.rect(23, 35.5, 25, 38, R.ink[0])
    for x in (18.5, 24, 29.5):
        p.line((x, 24), (x, 31), 1, R.leather, tone=0, edge=False)


# ---------------------------------------------------------------- chest pieces
def tunic(p, ramp, shoulder=15, sleeve=5, hem=44, flare=2, neck=6):
    """T-shaped upper body with sleeves"""
    body = sym([(24 - neck, 6), (24 - shoulder, 8), (24 - shoulder - sleeve, 12), (24 - shoulder - sleeve - 1, 24 + sleeve),
                (24 - shoulder - sleeve + 5, 26 + sleeve), (24 - shoulder + 2, 24), (24 - shoulder + 2 - flare * .3, 30),
                (24 - shoulder + 2 - flare, hem)])
    return p.poly(body, ramp)


@icon('warrior_armor_crimson', 'armor')
def _(p):
    p.poly(sym([(14, 36), (11, 41), (9, 46)]) + [], R.crimson)
    p.poly(sym([(8, 11), (3, 17), (3, 25), (7, 29), (12, 24)]), R.steel)
    p.poly(sym([(13, 6), (10, 12), (11, 22), (13, 33), (24, 36)]), R.steel)
    p.poly(sym([(17, 7), (14, 13), (15, 30), (24, 33)]), R.crimson)
    p.poly([(21, 8), (27, 8), (27, 32), (21, 32)], R.gold, tone=2)
    p.poly([(12, 32), (36, 32), (36, 36), (12, 36)], R.leather); p.rect(21, 32, 27, 36, R.gold[2])
    p.poly([(12, 36), (22, 36), (21, 46), (10, 46)], R.steel); p.poly([(26, 36), (36, 36), (38, 46), (27, 46)], R.steel)
    p.poly([(21.5, 36), (26.5, 36), (26.5, 47), (21.5, 47)], R.crimson)
    p.dots([(18, 15), (30, 15), (15, 25), (33, 25)], R.steel[3])


@icon('warrior_armor_azure', 'armor')
def _(p):
    p.poly(sym([(8, 11), (3, 17), (3, 25), (7, 29), (12, 24)]), R.steel)
    p.poly(sym([(13, 6), (10, 12), (11, 22), (13, 33), (24, 36)]), R.steel)
    p.poly(sym([(14, 31), (13, 44), (24, 47)]), R.azure)
    p.poly([(15, 33), (33, 33), (35, 47), (13, 47)], R.azure)
    p.poly(sym([(24, 8), (17, 8), (15, 14), (17, 28), (24, 31)]), R.azure)
    p.poly(sym([(24, 12), (13, 14), (12, 18), (24, 20)]), R.wing)
    gem(p, 24, 17, R.gold, 3)
    p.poly([(12, 31), (36, 31), (36, 35), (12, 35)], R.gold)
    p.dots([(24, 26)], R.wing[3])


@icon('mage_armor_apprentice', 'armor')
def _(p):
    p.poly(sym([(15, 7), (7, 12), (2, 27), (5, 32), (10, 28), (13, 22), (14, 45)]), R.blue)
    p.poly(sym([(24, 6), (17, 6), (16, 9), (24, 22)]), R.cream)
    p.poly([(14, 29), (34, 29), (35, 33), (13, 33)], R.leather); p.rect(22, 29, 26, 33, R.gold[2])
    p.rect(2, 30, 6, 33, R.cream[2]); p.rect(42, 30, 46, 33, R.cream[2])
    p.line((24, 22), (24, 29), 1.4, R.blue, tone=0, edge=False)
    p.dots([(18, 38), (30, 38), (24, 41)], R.blue[3])


@icon('mage_armor_runic', 'armor')
def _(p):
    p.poly(sym([(17, 5), (7, 10), (2, 28), (6, 33), (11, 29), (13, 24), (13, 46), (24, 47)]), R.violet)
    p.poly(sym([(24, 4), (14, 3), (14, 12), (24, 22)]), R.gold)
    p.poly(sym([(24, 6), (17, 5), (17, 11), (24, 18)]), R.violet, tone=1)
    p.poly([(13, 28), (35, 28), (35, 32), (13, 32)], R.gold)
    p.poly([(21, 30), (27, 30), (28, 45), (20, 45)], R.gold, tone=1, edge=False)
    p.poly([(24, 35), (26.5, 38), (24, 41), (21.5, 38)], R.glow)
    p.dots([(17, 38), (31, 38), (8, 24), (40, 24), (24, 38)], R.glow[2])
    p.line((2.5, 30), (7, 34), 2, R.gold, edge=False); p.line((45.5, 30), (41, 34), 2, R.gold, edge=False)


@icon('assassin_armor_shadow', 'armor')
def _(p):
    p.poly(sym([(14, 7), (7, 10), (2, 24), (5, 28), (9, 25), (12, 19), (13, 40), (24, 43)]), R.ink)
    p.poly(sym([(15, 8), (14, 38), (24, 41)]), R.shadow)
    p.line((14, 9), (33, 36), 4.4, R.leather, 4.4)
    p.line((12, 28), (36, 28), 3.2, R.leather, edge=True)
    p.rect(22, 26, 27, 30, R.steel[2])
    p.poly(ribbon(bez([(17, 4), (24, 9), (31, 4)], 8), 5), R.crimson)
    p.poly(ribbon(bez([(30, 7), (36, 17), (33, 28)], 8), 4.4), R.crimson)
    p.dots([(11, 32), (37, 32), (24, 36)], R.shadow[3])


@icon('assassin_armor_moon', 'armor')
def _(p):
    p.poly(sym([(14, 4), (6, 10), (2, 25), (5, 29), (9, 26), (12, 20), (13, 41), (24, 44)]), R.moon)
    p.poly(sym([(24, 3), (14, 2), (13, 10), (24, 18)]), R.pearl)
    p.poly(sym([(15, 22), (14, 40), (24, 43)]), R.shadow, tone=1)
    p.poly([(13, 28), (35, 28), (35, 32), (13, 32)], R.steel)
    p.poly(bez([(19, 15), (14, 23), (19, 31), (26, 32)], 8) + bez([(24, 29), (19.5, 24), (22, 17)], 6), R.pearl, tone=3)
    gem(p, 24, 24.5, R.violet, 2)
    p.dots([(9, 22), (39, 22), (17, 38), (31, 38)], R.pearl[3])


@icon('priest_armor_pilgrim', 'armor')
def _(p):
    p.poly(sym([(17, 5), (8, 10), (3, 28), (7, 33), (11, 28), (13, 24), (11, 46), (24, 47)]), R.cream)
    p.poly(sym([(24, 5), (16, 5), (14, 12), (24, 20)]), R.leather)
    p.poly(sym([(24, 20), (13, 16), (14, 24), (24, 28)]), R.cream, tone=2, edge=False)
    p.poly([(11, 44), (37, 44), (38, 47), (10, 47)], R.crimson)
    p.line((13, 29), (35, 29), 2.4, R.bone, edge=True)
    p.line((24, 30), (21, 42), 1.8, R.bone, edge=False); p.line((26, 30), (28, 41), 1.8, R.bone, edge=False)
    p.rect(23, 31, 25, 38, R.gold[2]); p.rect(21, 34, 27, 36, R.gold[2])
    p.line((3.5, 30), (7.5, 34), 2.4, R.crimson, edge=False)


@icon('priest_armor_dawn', 'armor')
def _(p):
    p.poly(sym([(15, 4), (6, 9), (2, 28), (6, 34), (11, 29), (13, 23), (10, 45), (24, 47)]), R.wing)
    p.poly(sym([(24, 4), (14, 3), (12, 13), (24, 22)]), R.gold)
    p.poly([(20, 8), (28, 8), (29, 47), (19, 47)], R.crimson)
    p.poly([(19, 40), (29, 40), (29, 47), (19, 47)], R.crimson, tone=1, edge=False)
    p.rect(19, 44, 29, 46, R.gold[2])
    p.poly([(11, 30), (37, 30), (37, 33), (11, 33)], R.gold)
    p.ell(24, 20, 5, 5, R.gold)
    for a in range(8):
        p.line((24 + 5.5 * math.cos(a * math.pi / 4), 20 + 5.5 * math.sin(a * math.pi / 4)), (24 + 8 * math.cos(a * math.pi / 4), 20 + 8 * math.sin(a * math.pi / 4)), 1.4, R.gold, edge=False)
    p.dots([(23, 19)], R.gold[3])


@icon('hunter_armor_scout', 'armor')
def _(p):
    p.poly(sym([(13, 5), (6, 10), (3, 27), (7, 31), (11, 27), (13, 21), (13, 42), (24, 44)]), R.green)
    p.poly(sym([(24, 6), (17, 6), (15, 12), (24, 22)]), R.leather)
    for k in range(4):
        y = 14 + k * 4
        p.line((21, y), (27, y + 2), 1.2, R.bone, edge=False)
        p.line((27, y), (21, y + 2), 1.2, R.bone, edge=False)
    p.poly([(13, 31), (35, 31), (35, 35), (13, 35)], R.leather); p.rect(21, 31, 27, 35, R.gold[2]); p.rect(23, 32, 25, 34, R.ink[0])
    p.poly([(13, 38), (21, 36), (24, 44), (19, 46), (13, 44)], R.green, tone=1)
    p.poly([(35, 38), (27, 36), (24, 44), (29, 46), (35, 44)], R.green, tone=2)
    p.rect(4, 28, 7, 31, R.leather[2]); p.rect(41, 28, 44, 31, R.leather[2])


@icon('hunter_armor_warden', 'armor')
def _(p):
    p.poly(sym([(14, 6), (6, 11), (2, 28), (6, 32), (10, 28), (12, 22), (11, 44), (24, 47)]), R.teal)
    p.poly(sym([(24, 18), (14, 16), (14, 40), (24, 44)]), R.teal, tone=1, edge=False)
    p.poly(bez([(10, 12), (12, 4), (24, 2), (36, 4), (38, 12)], 10) + [(34, 18), (30, 14), (27, 20), (24, 14), (21, 20), (18, 14), (14, 18)], R.fur)
    p.poly([(11, 30), (37, 30), (37, 34), (11, 34)], R.leather); gem(p, 24, 32, R.bone, 2)
    for y in (22, 27, 38):
        p.rect(23, y, 25, y + 2, R.bone[2])
    p.dots([(7, 22), (41, 22)], R.glow[2])


# ---------------------------------------------------------------- weapons
def shield(p, cx, cy, r, ramp, boss, rim=R.steel):
    p.ell(cx, cy, r, r, rim)
    p.ell(cx, cy, r - 2.2, r - 2.2, ramp)
    p.ell(cx, cy, 2.6, 2.6, boss)


@icon('warrior_weapon_sword', 'weapon')
def _(p):
    shield(p, 15, 31, 12, R.crimson, R.steel)
    p.poly(strip((16, 36), (40, 6), [(0, 1.5), (.1, 2.6), (.75, 2.6), (1, 0)]), R.steel)
    p.line((18, 34), (38, 9), 1, R.steel, tone=3, edge=False)
    p.poly(strip((17, 36), (21, 31), [(0, 5.4), (1, 5.4)]), R.bronze)
    p.line((12.5, 41.5), (17, 36), 3.2, R.leather); p.ell(11.5, 43, 2.4, 2.4, R.bronze)


@icon('warrior_weapon_royal', 'weapon')
def _(p):
    shield(p, 15, 32, 12.5, R.gold, R.azure, R.gold)
    p.poly(strip((16, 37), (44, 3), [(0, 1.5), (.08, 3.2), (.8, 3.2), (1, 0)]), R.steel)
    p.line((18, 35), (41, 6), 1.2, R.azure, tone=2, edge=False)
    p.poly(strip((17, 38), (22, 31.5), [(0, 7.5), (.3, 5), (.5, 3.2), (.7, 5), (1, 7.5)]), R.gold)
    p.line((12, 43), (17, 38), 3.4, R.azure); gem(p, 11, 44, R.azure, 2.6)
    gem(p, 15, 32, R.azure, 3.4)


@icon('mage_weapon_ash', 'weapon')
def _(p):
    p.poly(ribbon(bez([(9, 45), (21, 29), (27, 16), (31, 10)], 16), lambda t: 4.2 - 1.6 * t), R.wood)
    for t in (.3, .55):
        x, y = bez([(9, 45), (21, 29), (27, 16), (31, 10)], 16)[int(t * 16)]
        p.ell(x + 1, y, 1.8, 2.2, R.wood, tone=0, edge=False)
    p.poly(bez([(26, 14), (22, 5), (27, 2), (30, 8)], 8), R.wood); p.poly(bez([(33, 12), (39, 8), (41, 12), (36, 16)], 8) + [(33, 15)], R.wood)
    p.ell(32, 8, 4.8, 4.8, R.glow); p.dots([(30, 6), (31, 6)], R.glow[3])
    p.poly(ribbon(bez([(27, 14), (24, 7), (29, 2)], 8), 1.8), R.wood); p.poly(ribbon(bez([(34, 14), (40, 9), (37, 3)], 8), 1.8), R.wood)
    p.dots([(11, 43), (17, 36)], R.wood[3])


@icon('mage_weapon_crystal', 'weapon')
def _(p):
    p.poly(ribbon(bez([(7, 46), (18, 33), (25, 21), (29, 14)], 16), 3.4), R.steel)
    for y in (39, 32, 25):
        x = 7 + (46 - y) * .55
        p.line((x - 2, y + 1.2), (x + 2.2, y - 1.2), 2, R.azure, edge=False)
    p.poly(ribbon(bez([(26, 20), (20, 14), (23, 4)], 8), 2.6), R.gold); p.poly(ribbon(bez([(33, 19), (40, 12), (36, 3)], 8), 2.6), R.gold)
    p.poly([(31, 0.5), (38, 9.5), (31, 20), (24, 9.5)], R.azure)
    p.poly([(31, 0.5), (31, 20), (24, 9.5)], R.glow, tone=3, edge=False)
    p.poly([(31, 4), (34, 9.5), (31, 15), (28, 9.5)], R.glow, tone=2, edge=False)
    p.dots([(29, 7)], R.glow[3])


@icon('assassin_weapon_daggers', 'weapon')
def _(p):
    for a, b, g, h in (((6, 45), (34, 6), (10, 38), (7, 44)), ((41, 45), (13, 6), (37, 38), (40, 44))):
        pass
    p.poly(strip((12, 38), (38, 4), [(0, 1.4), (.12, 2.8), (.7, 2.8), (1, 0)]), R.steel)
    p.line((14, 35), (36, 6), 1, R.steel, tone=3, edge=False)
    p.poly(strip((36, 38), (10, 4), [(0, 1.4), (.12, 2.8), (.7, 2.8), (1, 0)]), R.steel)
    p.line((34, 35), (12, 6), 1, R.steel, tone=3, edge=False)
    p.poly(strip((11, 39), (15.5, 33), [(0, 5), (1, 5)]), R.bronze)
    p.poly(strip((37, 39), (32.5, 33), [(0, 5), (1, 5)]), R.bronze)
    p.line((6.5, 46), (11, 39), 3.2, R.ink); p.line((41.5, 46), (37, 39), 3.2, R.ink)
    p.dots([(7, 45), (41, 45)], R.crimson[2])


@icon('assassin_weapon_moonfang', 'weapon')
def _(p):
    # two curved fang blades crossing like scimitars, the right one in front; the tips hook upward
    width = lambda t: 1 + 6.4 * math.sin(math.pi * min(1, t * 1.08) ** .75) * (1 - .35 * t) if t < .93 else .6
    p.poly(ribbon(bez([(12, 39), (14, 25), (27, 18), (41, 3)], 24), width), R.moon)
    p.poly(ribbon(bez([(36, 39), (34, 25), (21, 18), (7, 3)], 24), width), R.pearl)
    p.poly(strip((8, 40), (19, 38), [(0, 2.6), (1, 2.6)]), R.steel)
    p.poly(strip((40, 40), (29, 38), [(0, 2.6), (1, 2.6)]), R.steel)
    p.line((13, 39), (10, 47), 3.4, R.ink); p.line((35, 39), (38, 47), 3.4, R.ink)
    p.dots([(38, 6), (10, 6), (30, 17), (18, 17)], R.violet[3]); gem(p, 24, 40.5, R.violet, 1.8)


@icon('priest_weapon_mace', 'weapon')
def _(p):
    p.poly(ribbon([(10, 44), (30, 17)], 4), R.wood)
    p.ell(33, 13, 9.5, 9.5, R.bronze)
    for a in range(8):
        x, y = 33 + 10 * math.cos(a * math.pi / 4), 13 + 10 * math.sin(a * math.pi / 4)
        p.poly([(x - 2, y - 2), (x + 2, y - 2), (x + 2, y + 2), (x - 2, y + 2)], R.steel, edge=False)
    p.ell(33, 13, 5, 5, R.steel, tone=2); p.dots([(31, 11)], R.steel[3])
    p.rect(14, 38, 17, 41, R.bone[2]); p.ell(9, 45.5, 2.2, 2.2, R.bronze)


@icon('priest_weapon_sunmace', 'weapon')
def _(p):
    p.poly(ribbon([(8, 45), (29, 19)], 4), R.gold)
    for k in range(12):
        a = k * math.pi / 6
        p.poly(strip((33 + 7 * math.cos(a), 13 + 7 * math.sin(a)), (33 + 13.5 * math.cos(a), 13 + 13.5 * math.sin(a)), [(0, 2.4), (1, 0)]), R.gold, tone=2 + (k % 2), edge=False)
    p.ell(33, 13, 8, 8, R.gold)
    p.ell(33, 13, 4.2, 4.2, R.wing, tone=3); p.dots([(32, 12)], R.wing[3])
    p.rect(16, 36, 20, 39, R.crimson[2]); p.line((13, 40), (17, 35), 3, R.crimson); p.ell(7.5, 46, 2.4, 2.4, R.gold)


@icon('hunter_weapon_shortbow', 'weapon')
def _(p):
    p.poly(ribbon(bez([(33, 3), (5, 14), (5, 34), (33, 45)], 24), lambda t: 2 + 3.2 * math.sin(math.pi * t)), R.wood)
    p.line((33, 3), (33, 45), 1, R.bone, tone=2, edge=False)
    p.line((12, 24), (46, 24), 1.4, R.wood, tone=2)
    p.poly([(44, 24), (38, 20.5), (38, 27.5)], R.steel)
    p.poly([(15, 22), (11, 20), (13, 24), (11, 28), (15, 26)], R.plume)
    p.rect(6, 22, 9, 26, R.leather[2])


@icon('hunter_weapon_wardenbow', 'weapon')
def _(p):
    p.poly(ribbon(bez([(35, 1), (1, 12), (1, 36), (35, 47)], 26), lambda t: 2 + 3.6 * math.sin(math.pi * t)), R.teal)
    p.poly(bez([(35, 1), (41, 4), (38, 8)], 5), R.bone); p.poly(bez([(35, 47), (41, 44), (38, 40)], 5), R.bone)
    p.line((35, 3), (35, 45), 1, R.glow, tone=3, edge=False)
    p.line((8, 24), (47, 24), 1.5, R.bone, tone=2)
    p.poly([(46, 24), (39, 20), (39, 28)], R.glow)
    p.poly([(14, 21), (9, 18), (12, 24), (9, 30), (14, 27)], R.fur)
    p.poly(ribbon([(2, 20), (2, 28)], 4), R.leather)
    p.dots([(6, 12), (4, 18), (4, 30), (6, 36)], R.glow[3])


# ---------------------------------------------------------------- the Priest's head, shoulder and glove pieces
@icon('priest_headgear_pilgrim', 'headgear')
def _(p):
    p.poly(sym([(24, 2.5), (15.5, 6.5), (9.5, 17), (7.5, 30), (9, 41), (13, 45)]), R.cream)
    p.ell(24, 29, 11.4, 13.4, R.gold, tone=2, flat=True)
    p.ell(24, 29.5, 9.4, 11.4, R.crimson, tone=0, flat=True, edge=False)
    p.poly(ribbon(bez([(12, 33), (11, 38), (13, 43)], 6), 2.6), R.crimson); p.poly(ribbon(bez([(36, 33), (37, 38), (35, 43)], 6), 2.6), R.crimson)
    p.dots([(14, 12), (18, 8), (30, 8)], R.cream[3])


@icon('priest_headgear_dawn', 'headgear')
def _(p):
    xs = [-18, -12, -6, 0, 6, 12, 18]
    tops = [20, 12, 7, 3, 7, 12, 20]
    pts = [(24 + xs[0] - 3, 40), (24 + xs[0] - 3, 30)]
    for x, t in zip(xs, tops):
        pts += [(24 + x - 3, 28), (24 + x, t), (24 + x + 3, 28)]
    pts += [(24 + xs[-1] + 3, 30), (24 + xs[-1] + 3, 40), (24, 43)]
    p.poly(pts, R.gold)
    p.poly([(6, 31), (42, 31), (42, 36), (6, 36)], R.gold, tone=2)
    gem(p, 24, 33.5, R.glow, 3.4)
    p.poly(ribbon(bez([(8, 36), (6, 42), (8, 47)], 6), 4), R.wing); p.poly(ribbon(bez([(40, 36), (42, 42), (40, 47)], 6), 4), R.wing)
    p.dots([(8, 46), (9, 46), (39, 46), (40, 46)], R.crimson[2])


@shoulders('priest_shoulders_pilgrim')
def _(p):
    p.poly(bez([(4, 34), (3, 15), (14, 9), (25, 14)], 12) + [(24, 36), (12, 39)], R.cream)
    p.poly(ribbon(bez([(4, 33), (13, 29), (25, 32)], 10), 4), R.crimson)
    p.line((15, 14), (15, 28), 1.4, R.bone, edge=False)
    gem(p, 21, 20, R.gold, 2.2)
    p.dots([(8, 20), (14, 16)], R.cream[3])


@shoulders('priest_shoulders_dawn')
def _(p):
    p.poly(bez([(4, 36), (3, 18), (14, 12), (25, 17)], 12) + [(24, 38), (12, 41)], R.gold)
    p.poly(ribbon(bez([(4, 34), (13, 30), (25, 33)], 10), 4), R.wing)
    for k, (tx, ty) in enumerate([(3, 2), (11, -1), (19, 2)]):
        p.poly([(6 + k * 6, 17), (tx, ty + 6), (10 + k * 6, 17)], R.glow)
    gem(p, 15, 24, R.glow, 2.4)


@glove('priest_gloves_pilgrim')
def _(p):
    hand(p, R.cream, None)
    p.poly([(11, 35), (37, 35), (38, 46), (10, 46)], R.cream, tone=1)
    for y in (36, 43):
        p.poly(ribbon([(11, y), (37, y)], 3), R.leather, edge=True)
    p.dots([(18, 14), (23, 11)], R.cream[3])


@glove('priest_gloves_dawn')
def _(p):
    hand(p, R.wing, None)
    p.poly([(10, 34), (38, 34), (40, 46), (8, 46)], R.gold)
    p.rect(9, 36, 39, 38, R.gold[3])
    gem(p, 24, 28, R.glow, 3.0)
    p.dots([(18, 14), (24, 11)], R.wing[3])


# ---------------------------------------------------------------- the rest
@icon('pants_upgrade', 'pants')
def _(p):
    p.poly([(11, 5), (37, 5), (39, 20), (35, 45), (26, 45), (24, 22), (22, 45), (13, 45), (9, 20)], R.leather)
    p.poly([(11, 5), (37, 5), (37.5, 10), (10.5, 10)], R.leather, tone=1)
    p.rect(21, 6, 27, 10, R.gold[2]); p.rect(23, 7, 25, 9, R.ink[0])
    p.poly([(11, 39), (23, 39), (22, 45), (13, 45)], R.cream, flat=True, tone=2)
    p.poly([(25, 39), (37, 39), (35, 45), (26, 45)], R.cream, flat=True, tone=2)
    p.poly([(28, 24), (34, 24), (34, 30), (28, 30)], R.bone, tone=2, flat=True)
    p.dots([(29, 27), (33, 27), (30, 24), (31, 30)], R.leather[0])
    p.line((16, 12), (15, 34), 1, R.leather, tone=3, edge=False)


@icon('necklace_upgrade', 'necklace')
def _(p):
    p.poly(ribbon(bez([(5, 4), (6, 30), (24, 30), (42, 4)], 24), 2.6), R.steel, edge=True)
    for x, y in ((8.5, 14), (11, 21), (16, 26), (32, 26), (37, 21), (39.5, 14)):
        p.ell(x, y, 2.1, 2.1, R.pearl)
    p.poly([(24, 30), (31, 37), (24, 47), (17, 37)], R.steel)
    p.poly([(24, 32.5), (29, 37.5), (24, 44.5), (19, 37.5)], R.pearl)
    p.poly([(24, 32.5), (24, 44.5), (19, 37.5)], R.wing, tone=3, edge=False)


@icon('accessory_upgrade', 'accessory')
def _(p):
    p.ell(24, 33, 15, 13, R.gold)
    hole = Painter.mask([(24 + 9 * math.cos(a / 24 * math.pi), 34 + 7.5 * math.sin(a / 24 * math.pi)) for a in range(48)])
    p.a &= ~hole
    inner = ndi.binary_dilation(hole, iterations=1) & ~hole & p.a
    p.rgb[inner] = R.gold[0]
    p.poly([(24, 3), (34, 10), (34, 20), (24, 28), (14, 20), (14, 10)], R.gold)
    p.poly([(24, 6), (31.5, 11.5), (31.5, 19), (24, 25), (16.5, 19), (16.5, 11.5)], R.amber)
    p.poly([(24, 6), (16.5, 11.5), (16.5, 19), (24, 25)], R.amber, tone=3, edge=False)
    p.dots([(19, 11), (20, 10)], R.amber[3]); p.dots([(18, 26), (30, 26)], R.gold[3])


# ---------------------------------------------------------------- the game master's golden set
@icon('warrior_armor_gm', 'armor')
def _(p):
    p.poly(sym([(15, 7), (7, 12), (2, 27), (5, 33), (10, 29), (13, 22), (9, 45)]), R.gilt)
    p.poly([(2.4, 30), (6.5, 34), (11, 30), (7.6, 26.6)], R.ivory)
    p.poly([(45.6, 30), (41.5, 34), (37, 30), (40.4, 26.6)], R.ivory)
    p.poly([(17, 7), (22, 7), (33, 28), (28, 28)], R.brocade)
    p.poly([(31, 7), (26, 7), (15, 28), (20, 28)], R.brocade)
    p.poly(sym([(24, 6), (18, 6), (16, 9), (24, 24)]), R.ivory)
    p.poly([(11, 28), (37, 28), (38, 34), (10, 34)], R.ruby); gem(p, 24, 31, R.gilt, 2.4)
    p.poly([(21, 35), (27, 35), (30, 40), (24, 45), (18, 40)], R.brocade)
    p.poly([(24, 37), (27, 40.5), (24, 44), (21, 40.5)], R.ruby, edge=False)
    p.poly([(9, 43), (39, 43), (40, 46.5), (8, 46.5)], R.ivory)
    p.rect(9, 44, 39, 45, R.ruby[2])
    p.dots([(14, 38), (34, 38), (24, 16)], R.gilt[3])


@icon('warrior_headgear_gm', 'headgear')
def _(p):
    p.poly([(15.5, 7), (32.5, 7), (33.5, 31), (14.5, 31)], R.gilt)
    p.poly([(32.5, 7), (28, 7), (28.5, 31), (33.5, 31)], R.gilt, tone=1, edge=False)
    p.poly([(17.5, 8), (20.5, 8), (20.5, 30), (17.5, 30)], R.gilt, tone=3, edge=False)
    p.ell(24, 7, 8.6, 2.8, R.gilt, tone=3)
    p.ell(24, 7, 6.2, 1.6, R.brocade, tone=2, edge=False)
    p.poly([(14.6, 22.5), (33.4, 22.5), (33.8, 30), (14.2, 30)], R.ruby)
    p.poly([(33.4, 22.5), (28.5, 22.5), (28.6, 30), (33.8, 30)], R.ruby, tone=1, edge=False)
    p.rect(14, 21, 34, 22.4, R.ivory[2])
    p.poly([(20, 22), (28, 22), (28, 31), (20, 31)], R.gilt, tone=3)
    p.poly([(22, 24), (26, 24), (26, 29.5), (22, 29.5)], R.ruby, tone=2, edge=False)
    p.ell(24, 33, 18.5, 4.6, R.gilt)
    p.poly([(7, 34), (41, 34), (38, 38.4), (24, 39.6), (10, 38.4)], R.gilt, tone=1, edge=False)
    p.dots([(9, 31), (10, 31), (11, 32)], R.ivory[3])
    p.poly(star(24, 14.6, 3.6, 1.5), R.ivory, tone=2, edge=False)


def star(cx, cy, r1, r2):
    return [(cx + (r1 if i % 2 == 0 else r2) * math.sin(i * math.pi / 5), cy - (r1 if i % 2 == 0 else r2) * math.cos(i * math.pi / 5)) for i in range(10)]


@icon('warrior_weapon_gm', 'weapon')
def _(p):
    p.ell(15, 32, 12.8, 12.8, R.gilt, tone=1)
    p.ell(15, 32, 11.2, 11.2, R.gilt, tone=2)
    p.ell(15, 32, 9.4, 9.4, R.ivory, tone=2)
    p.ell(15, 32, 8, 8, R.ruby, tone=2)
    p.poly(star(15, 32, 7.2, 3.2) + [], R.gilt, tone=3, edge=False)
    p.ell(15, 32, 2.6, 2.6, R.ruby, tone=3)
    p.dots([(15, 20.6), (15, 43.4), (3.6, 32), (26.4, 32)], R.ivory[3])
    p.poly(strip((16, 37), (44, 3), [(0, 1.5), (.08, 3.4), (.8, 3.4), (1, 0)]), R.gilt)
    p.line((18, 35), (41, 6), 1.2, R.ivory, tone=3, edge=False)
    p.poly(strip((17, 38), (22.5, 31), [(0, 8), (.3, 5.4), (.5, 3.4), (.7, 5.4), (1, 8)]), R.gilt)
    p.line((12, 43), (17, 38), 3.4, R.ruby); gem(p, 11, 44, R.ruby, 2.6)


# ---------------------------------------------------------------- output
ORDER = list(ICONS)


def render(id_):
    p = Painter()
    ICONS[id_][1](p)
    return p.image()


def ordered_ids():
    return [i for i in ORDER if not i.endswith('unused')]


def contact_sheet(ids, scale=4, cols=10):
    rows = -(-len(ids) // cols)
    sheet = Image.new('RGBA', (cols * (N * scale + 8) + 8, rows * (N * scale + 8) + 8), (62, 96, 78, 255))
    for k, id_ in enumerate(ids):
        im = Image.fromarray(render(id_)).resize((N * scale, N * scale), Image.NEAREST)
        sheet.alpha_composite(im, (8 + (k % cols) * (N * scale + 8), 8 + (k // cols) * (N * scale + 8)))
    return sheet


def palette_of(frames):
    cols = {}
    for im in frames:
        for c in {tuple(v) for v in im.reshape(-1, 4) if v[3]}:
            cols.setdefault(c[:3], len(cols) + 1)
    return ['#00000000'] + ['#%02x%02x%02x' % c for c in cols], cols


def index_frames(frames, cols):
    return [np.array([[0 if px[3] == 0 else cols[tuple(px[:3])] for px in row] for row in im], int) for im in frames]


def cmd_preview(args):
    RAW.mkdir(exist_ok=True)
    ids = args or ordered_ids()
    sheet = contact_sheet(ids)
    sheet.save(RAW / 'preview.png')
    print('wrote', RAW / 'preview.png', len(ids), 'icons')


def cmd_build(args):
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf
    ids = ordered_ids()
    frames = [render(i) for i in ids]
    palette, cols = palette_of(frames)
    print('palette', len(palette) - 1, 'opaque colours')
    assert len(palette) <= 256, 'too many colours for one sprite'
    existing = pf.ids('valhallasc_items')
    if existing and '--replace' not in args:
        sys.exit('valhallasc_items exists; use --replace (this discards editor edits)')
    pf.delete_prefix('valhallasc_items')
    sid = pf.create('valhallasc_items', N, N, len(ids), palette, fps=1)
    for k, grid in enumerate(index_frames(frames, cols)):
        pf.draw_grid(sid, k, 0, grid)
    RAW.mkdir(exist_ok=True)
    (RAW / 'sprite_id.txt').write_text(sid)
    (RAW / 'order.txt').write_text('\n'.join(ids))
    print('built', sid, len(ids), 'frames; edit at /pixelflow/?sprite=' + sid)


def cmd_export(args):
    ids = (RAW / 'order.txt').read_text().split('\n') if (RAW / 'order.txt').exists() else ordered_ids()
    if '--local' in args:
        frames = [render(i) for i in ids]
        sid = None
    else:
        sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
        import pf
        sid = (RAW / 'sprite_id.txt').read_text().strip()
        sp, grids = pf.load(sid)
        palette = sp['palette']
        frames = [pf.to_rgba(g[0], palette) for g in grids]
        assert len(frames) == len(ids), (len(frames), len(ids))
    cols = 10
    rows = -(-len(ids) // cols)
    atlas = Image.new('RGBA', (cols * N, rows * N), (0, 0, 0, 0))
    at = {}
    for k, (id_, im) in enumerate(zip(ids, frames)):
        atlas.alpha_composite(Image.fromarray(np.asarray(im, np.uint8)), ((k % cols) * N, (k // cols) * N))
        at[id_] = [k % cols, k // cols]
    atlas.save(ROOT / 'client/assets/items.png', optimize=True)
    meta = {'size': N, 'cols': cols, 'rows': rows, 'at': at, 'sprite': sid, 'light': 'top left', 'editing': 'one PixelFlow sprite, one frame per item in `at` order; build --replace discards edits'}
    (ROOT / 'client/assets/items.txt').write_text(json.dumps(meta, indent=1))
    (ROOT / 'client/itemicons.js').write_text("'use strict';\n// Generated by scripts/make_item_sprites.py export. Equipment icons are cells of assets/items.png.\nwindow.ITEM_ICONS = " + json.dumps({'size': N, 'cols': cols, 'rows': rows, 'at': at}, separators=(',', ':')) + ';\n')
    print('exported', len(ids), 'icons ->', ROOT / 'client/assets/items.png')
    import gear_art_catalog
    gear_art_catalog.append_icons(refresh_base=True)


if __name__ == '__main__':
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else 'preview'), sys.argv[2:]
    {'preview': cmd_preview, 'build': cmd_build, 'export': cmd_export}[cmd](args)
