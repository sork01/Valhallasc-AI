"""Cel-shaded Prismwaste enemies (zone 14) for make_prism_sprites.py.

Same recipe as cathedral_reliquary_redraw.py and astral_redraw.py: hard colour bands, one dark outline per part,
big glossy eyes, chibi proportions. 96x96 frame, foot anchor (48,90), five clips.
`python3 scripts/prism_redraw.py [kind...]` writes contact sheets to test-results/prism-preview.
"""
import math
import sys

import numpy as np

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, timing, crystal, diamond, preview, star
from make_crag_sprites import XX, YY, ellipsoid, polygon

KINDS = ('miragejackal', 'shardscarab', 'glassharrier', 'prismsentinel', 'mirrorqueen', 'sunshard')

PALETTES = {
    'miragejackal': mk(fur=('#5e4466', '#9a6e86', '#d6a28c', '#ffd9a8'), cream=('#c9a894', '#f2dcc2', '#fff6e8'),
                       pr=('#ff6fae', '#ffd25a', '#4fe0cc', '#7a8cff'), prism=('#2a8fa8', '#5fd8e0', '#b5f5ff', '#f0ffff'),
                       iris='#12b6c8', blush='#ff8fb0', ghost='#f0dcee', mouth=('#5a1c34', '#ff7a98')),
    'shardscarab': mk(glass=('#0f4a5e', '#1f8fa0', '#59d8d0', '#c9fff2'), dark=('#25285a', '#4d52a0', '#8088dc'),
                      shard=('#5a2480', '#a844c8', '#e090ee', '#ffe2ff'), iris='#e8408a', glow=('#fff6c0', '#ffe27a'),
                      blush='#ff9fc0', comb=('#b08a2a', '#f0c850', '#fff0a0')),
    'glassharrier': mk(plume=('#4a3a8a', '#8c76d0', '#c9b8f6', '#f2eaff'), glass=('#2f4f98', '#5f9ae0', '#aee0ff', '#f2fdff'),
                       beak=('#a86a14', '#f0b030', '#ffe27a'), iris='#1f86e0', talon=('#5a4a6a', '#a898c0'),
                       blush='#ff90b8', spark='#dff6ff'),
    'prismsentinel': mk(plate=('#2f3f5e', '#63809e', '#a4c2e0', '#e8f6ff'), prism=('#2a8fa8', '#5fd8e0', '#b5f5ff', '#f0ffff'),
                        pr=('#ff6fae', '#ffd25a', '#4fe0cc', '#7a8cff'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                        cloth=('#5a2a6e', '#9040b0', '#cc72e4'), glow=('#9ff6ff', '#38d6ee'), iris='#16b8d8',
                        spear=('#7a6a8c', '#c8bcd8')),
    'mirrorqueen': mk(gown=('#36104e', '#6e2294', '#aa46cc', '#e49af0'), mirror=('#4f6ab0', '#9cbcee', '#e2f2ff', '#f7fdff'),
                      skin=('#b898cc', '#e8d2f4', '#fff2ff'), hair=('#150c3a', '#33266f', '#5a48a8'),
                      gold=('#8c5d16', '#dba22f', '#ffe382'), iris='#d83a9c', beam=('#fff2b8', '#ffffff'),
                      blush='#ff9ac8'),
    'sunshard': mk(sun=('#8c2a14', '#e0661e', '#ffb236', '#ffe27a'), core=('#fff1b0', '#fffbe0'),
                   ray=('#ff9a2e', '#ffd84a', '#fff2a0'), iris='#e0481e', blush='#ff8a6a',
                   ember=('#a83a14', '#ff8a2e'), dark=('#4a1a14', '#7a3a1c')),
}
R.PALETTES.update(PALETTES)


def ghost_copy(a, mask_fn, dx):
    """A dithered afterimage: the same silhouette shifted by dx, on every other pixel."""
    ys, xs = np.nonzero(mask_fn)
    out = a.f.a
    for y, x in zip(ys, xs):
        nx = int(x + dx)
        if 0 < nx < out.shape[1] - 1 and (nx + y) % 2 == 0 and out[y, nx] == 0:
            out[y, nx] = a.p['ghost']


# ------------------------------------------------------------------------------------------------
def miragejackal(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('miragejackal', clip, n, sy=1 - fall * .45)
    b = bob * .6 - fall * 5
    by = 22 + b
    lean = strike * 4 - wind * 4
    if fall:
        a.ox = fall * 4
    # shimmer afterimage of the body, behind everything
    if clip in ('walk', 'attack') and n % 2 == 0:
        cx, cy = a.g(-6, by)
        ghost_copy(a, ellipsoid(cx, cy, 20, 12.5)[0], -9 - strike * 6)
    # tail with a prism tip
    tail = (-30 - (strike * -3), by + 10 + math.sin(n * 1.3) * 2 + wind * 6)
    a.c((-20, by + 2), tail, 4.2, 2.6, 'fur')
    crystal(a, tail[0] - 1, tail[1] - 1, 3, 10, 'prism', tilt=-3)
    # far legs
    for lx, ph in ((-15, 1.6), (8, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 6 if clip == 'walk' else 0
        a.c((lx + 3, by - 4), (lx + 5 + up * .3, up), 4.4, 3.2, 'fur')
        a.e(lx + 7 + up * .3, up + 1, 4.6, 2.2, 'cream')
    # body, belly and the rainbow stripes
    a.e(-6, by, 20, 12.5, 'fur')
    a.e(-3, by - 7, 14, 5, 'cream', out=False)
    for k, x in enumerate((-15, -9, -3, 3)):
        top = by + 12.5 * math.sqrt(max(0, 1 - ((x + 6) / 20) ** 2)) - 1
        a.line((x, top), (x - 4, top - 8), f'pr{k}', 2)
    a.e(12, by + 3, 11, 10.5, 'fur')
    # near legs
    for lx, ph in ((-12, 0), (11, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 6 if clip == 'walk' else 0
        a.c((lx, by - 4), (lx + 2 + up * .3, up), 5, 3.6, 'fur')
        a.e(lx + 4 + up * .3, up + 1, 5, 2.4, 'cream')
    # head
    hx, hy = 21 + lean, by + 12
    if clip == 'die':
        hx, hy = lerp(21, 24, fall), lerp(by + 12, 10, fall)
    jaw = max(wind * .5, strike) * 5
    a.e(hx + 9, hy - 6 - jaw, 7.2, 3.2, 'cream')
    if jaw > 1:
        a.e(hx + 10, hy - 4 - jaw / 2, 5.6, jaw / 2 + 1, 'mouth')
    a.e(hx, hy, 12.5, 10.5, 'fur')
    a.e(hx + 9.5, hy - 2.6, 8, 5, 'cream')
    a.dot(hx + 16, hy - 1.4, 'ink', 2)
    for (ex, eh, tilt) in ((-6, 17, -4), (1, 19, 2)):
        a.poly([(hx + ex - 5, hy + 7), (hx + ex + tilt, hy + 7 + eh), (hx + ex + 6, hy + 7)], 'fur1')
        a.poly([(hx + ex - 2, hy + 8), (hx + ex + tilt * .5, hy + 5 + eh), (hx + ex + 3, hy + 8)], 'blush', out=False)
    a.eye(hx + 2, hy + 2.4, 4.7, iris='iris')
    a.eye(hx + 10, hy + 2, 3.2, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(hx + 18 + k * 4, 40), hy - 3 + (k % 2) * 5, 2.4, 'pr1' if k % 2 else 'pr2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def shardscarab(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('shardscarab', clip, n, sy=1 - fall * .15)
    by = 21 + bob * .8 - fall * 4
    flare = max(wind, strike)
    # legs
    for i, (lx, dx, near) in enumerate(((-17, -9, 0), (-6, -4, 0), (6, 7, 0), (-12, -7, 1), (0, 1, 1), (12, 9, 1))):
        up = max(0, math.sin(n * math.pi / 2 + i * 1.6)) * 5 if clip == 'walk' else 0
        hip = (lx, by - 8)
        knee = (lx + dx * 1.4, by - 10 + fall * 12)
        foot = (lx + dx * 1.9, lerp(up, by + 17 + math.sin(n * 1.7 + i) * 3, fall))
        if near == 0:
            a.c(hip, knee, 2.7, 2.3, 'dark')
            a.c(knee, foot, 2.3, 1.5, 'dark')
    # fan of glass shards on the back, behind the shell
    spread = 5 + flare * 8
    for k, (x, h, tilt) in enumerate(((-12, 14, -spread), (-4, 19, -spread * .3), (5, 16, spread * .6), (12, 11, spread))):
        crystal(a, x, by + 8 + (1 if k in (0, 3) else 3), 3.6, h * (1 - fall * .6) + flare * 3, 'shard', tilt=tilt)
    # low, wide dome shell with glass facets
    a.e(-3, by, 27, 15.2, 'glass')
    a.e(-12, by + 8, 11, 4.4, 'glass', out=False)
    a.line((-3, by + 14), (-3, by - 12), 'glass0', 1)
    a.line((-14, by + 11), (-8, by - 5), 'glass3', 2)
    a.line((-22, by + 5), (-16, by - 6), 'glass3', 1)
    a.line((9, by + 11), (13, by + 1), 'glass3', 1)
    for sx, sy, r in ((6, 6, 2.2), (14, 1, 1.6), (-20, -3, 1.6)):
        diamond(a, sx, by + sy, r, r * 1.3, 'glow0')
    for i, (lx, dx, near) in enumerate(((-12, -7, 1), (0, 1, 1), (12, 9, 1))):
        up = max(0, math.sin(n * math.pi / 2 + (i + 3) * 1.6)) * 5 if clip == 'walk' else 0
        hip = (lx, by - 11)
        knee = (lx + dx * 1.4, by - 12 + fall * 10)
        foot = (lx + dx * 1.9, lerp(up, by + 15 + math.sin(n * 1.3 + i) * 3, fall))
        a.c(hip, knee, 3, 2.5, 'dark')
        a.c(knee, foot, 2.5, 1.6, 'dark')
    # head: broad, with a golden comb and big eyes
    hx = 22 + strike * 6 - wind * 3
    hy = by - 5 - fall * 2
    a.e(hx, hy, 11.5, 9.5, 'dark')
    snap = max(wind * .5, strike) * 4
    for s in (-1, 1):
        a.c((hx + 7, hy - 5 + s * 1.5), (hx + 16, hy - 6 + s * (3 + snap * .6)), 2.6, 1.2, 'comb')
    a.eye(hx + 3, hy + 1.6, 4.5, iris='iris')
    a.eye(hx - 5.4, hy + 3, 3.1, iris='iris')
    a.dot(hx + 7.5, hy - 3.4, 'blush', 2)
    for s in (-1, 1):
        a.c((hx - 2 + s * 4, hy + 7), (hx - 6 + s * 9, hy + 16 + s * 2), 1.2, 1.2, 'dark')
        a.e(hx - 6 + s * 9, hy + 17 + s * 2, 2.4, 2.4, 'glow')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 15 + k * 5 + (n - 3) * 2, 38), by + 9 + (k % 2) * 6 + k, 2.4, 3.4, 'shard2' if k % 2 else 'glass3')
    return a.done()


# ------------------------------------------------------------------------------------------------
def glassharrier(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('glassharrier', clip, n, sy=1 - fall * .3)
    if clip == 'idle':
        fl = math.sin(n * math.pi / 3)
    elif clip == 'walk':
        fl = math.sin(n * math.pi / 2)
    elif clip == 'attack':
        fl = lerp(lerp(.4, 1., wind), -1.1, strike)
    elif clip == 'hurt':
        fl = (1., .7, .3, 0.)[n]
    else:
        fl = .3
    by = 42 + bob * 1.2 - fall * 16 + (-strike * 6)
    hx, hy = 13 + strike * 5, by + 9 - strike * 4
    # tail fan
    for k in range(3):
        a.c((-9, by - 2), (-27 + k * 3 - fall * 4, by - 6 - k * 5 + fl * 2 - fall * 6), 3.2, 2.4, 'glass')
    # far wing, then body, then near wing: each a fan of five glass feathers
    def wing(base_ang, length, grp):
        sh = (-2, by + 6)
        ang0 = base_ang + fl * 32 * (1 - fall)
        pts = [sh]
        tips = []
        for k in range(5):
            th = math.radians(ang0 + (k - 2) * 15)
            ln = length - abs(k - 2) * 3.4
            nth = math.radians(ang0 + (k - 2) * 15 - 7.5)
            pts.append((sh[0] + math.cos(nth) * length * .56, sh[1] + math.sin(nth) * length * .56))
            tip = (sh[0] + math.cos(th) * ln, sh[1] + math.sin(th) * ln)
            pts.append(tip)
            tips.append(tip)
        nth = math.radians(ang0 + 2 * 15 + 7.5)
        pts.append((sh[0] + math.cos(nth) * length * .56, sh[1] + math.sin(nth) * length * .56))
        a.band(pts, grp)
        for tip in tips:
            a.line((sh[0] + (tip[0] - sh[0]) * .25, sh[1] + (tip[1] - sh[1]) * .25),
                   (sh[0] + (tip[0] - sh[0]) * .8, sh[1] + (tip[1] - sh[1]) * .8), grp + '0', 1)
    wing(138 + fall * 30, 29, 'glass')
    a.e(0, by, 15, 11.5, 'plume')
    a.e(-3, by - 5, 11, 4.5, 'plume', out=False)
    for k in range(3):
        a.line((-6 + k * 4, by + 7 - k), (-5 + k * 4, by + 3 - k), 'plume0', 1)
    wing(122 + fall * 56 - fl * 6, 34, 'glass')
    for k in range(3):
        a.dot(-8 + k * 4, by + 6 - abs(k - 1), 'spark')
    # talons
    reach = strike * 14 + wind * -2
    for s, off in ((-1, 0), (1, 3)):
        a.c((2 + off, by - 8), (4 + off + reach, by - 18 - fall * 0 + strike * 3), 2.2, 1.6, 'talon')
        for t in range(3):
            a.line((4 + off + reach, by - 18 + strike * 3), (4 + off + reach + 3 - t * 2.4, by - 23 + strike * 3), 'talon0', 1)
    # head, hooked beak, crest, big eye
    gap = max(wind * .4, strike) * 4
    a.poly([(hx + 6, hy - 3 - gap), (hx + 17, hy - 5 - gap), (hx + 8, hy - 9 - gap)], 'beak0')
    a.e(hx, hy, 11, 10, 'plume')
    a.poly([(hx + 7, hy + 1), (hx + 19, hy - 2), (hx + 16, hy - 6), (hx + 8, hy - 5)], 'beak1')
    a.poly([(hx + 16, hy - 2), (hx + 20, hy - 7), (hx + 15, hy - 5)], 'beak2', out=False)
    for k, (dx, h) in enumerate(((-7, 9), (-2, 13), (3, 10))):
        a.poly([(hx + dx - 2.6, hy + 8), (hx + dx - 1, hy + 8 + h), (hx + dx + 3, hy + 8)], 'glass2')
    a.eye(hx + 2, hy + 1.8, 4.7, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (4, 5):
        for k in range(3):
            star(a, 24 + k * 5 - (n - 4) * 2, by - 14 + k * 3, 2.4, 'spark')
    return a.done()


# ------------------------------------------------------------------------------------------------
def prismsentinel(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('prismsentinel', clip, n, sy=1 - fall * .5)
    b = bob * .5
    step = sw * 3 if clip == 'walk' else 0
    for s in (-1, 1):                                    # boots and legs
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 7, 22), (s * 7 + step * s * .1, 6 + up), 4.6, 4, 'plate')
        a.e(s * 7.5, 4 + up, 7, 4, 'plate')
        a.line((s * 7 - 3, 5 + up), (s * 7 + 3, 5 + up), 'gold1', 1)
    # shield on the far side: a kite of glass with a rainbow boss
    sx = -25 + wind * -2
    sy_ = 36 + b
    a.poly([(sx - 9, sy_ + 14), (sx + 9, sy_ + 14), (sx + 8, sy_ - 8), (sx, sy_ - 17), (sx - 8, sy_ - 8)], 'plate1')
    a.band([(sx - 6.5, sy_ + 11.5), (sx + 6.5, sy_ + 11.5), (sx + 5.5, sy_ - 7), (sx, sy_ - 14), (sx - 5.5, sy_ - 7)],
           'prism', out=False)
    for k in range(4):
        a.line((sx - 5 + k * 3, sy_ + 11), (sx - 2 + k * 3, sy_ - 8), f'pr{k}', 1)
    a.e(sx, sy_ + 2, 3.4, 3.8, 'gold')
    a.c((-12, 40 + b), (sx + 5, sy_ + 2), 3.4, 3, 'plate')
    # torso, tasset, chest prism
    a.band([(-11, 24), (11, 24), (14, 17), (-14, 17)], 'cloth')
    a.e(0, 34 + b, 13.4, 11.5, 'plate')
    a.e(-4, 39 + b, 7, 4, 'plate', out=False)
    a.poly([(0, 39 + b), (4, 34 + b), (0, 29 + b), (-4, 34 + b)], 'pr1', edge='ink')
    a.dot(-1.2, 35.8 + b, 'shine', 2)
    a.line((-12, 28 + b), (12, 28 + b), 'gold1', 2)
    # spear arm
    hand = (lerp(lerp(19, 15, wind), 25, strike), lerp(lerp(33, 37, wind), 36, strike))
    tilt_x = lerp(lerp(0, -5, wind), 24, strike)
    tip = (min(hand[0] + 1 + tilt_x, 30), lerp(lerp(70, 72, wind), 40, strike))
    base_ = (hand[0] - 1 - tilt_x * .5, lerp(lerp(2, 6, wind), 33, strike))
    if clip == 'die':
        hand = (lerp(19, 24, fall), lerp(33, 8, fall))
        tip = (lerp(20, 28, fall), lerp(70, 16, fall))
        base_ = (lerp(18, 6, fall), 3)
    a.line(base_, tip, 'ink', 4)
    a.line(base_, tip, 'spear1', 2)
    dx_, dy_ = tip[0] - base_[0], tip[1] - base_[1]
    ln = math.hypot(dx_, dy_) or 1
    ux, uy = dx_ / ln, dy_ / ln
    a.poly([(tip[0] - uy * 3.4, tip[1] + ux * 3.4), (tip[0] + ux * 11, tip[1] + uy * 11), (tip[0] + uy * 3.4, tip[1] - ux * 3.4)],
           'prism1')
    a.line((tip[0], tip[1]), (tip[0] + ux * 8, tip[1] + uy * 8), 'prism3', 1)
    a.c((10, 41 + b), hand, 4, 3.4, 'plate')
    a.e(hand[0], hand[1], 3.8, 3.6, 'gold')
    # pauldrons with crystal spikes
    for s in (-1, 1):
        a.e(s * 15, 42 + b, 7.5, 6.4, 'plate')
        a.line((s * 15 - 5, 40 + b), (s * 15 + 5, 40 + b), 'gold1', 1)
        crystal(a, s * 16, 46 + b, 2.8, 9 - (1 if s < 0 else 0), 'prism', tilt=s * 2)
    # helm with a visor, glowing eyes and a crystal crest
    hx, hy = 1, 57 + b
    for k, (dx, h, tilt) in enumerate(((-7, 10, -4), (-2, 14, -1), (3, 12, 1), (8, 8, 3))):
        crystal(a, hx + dx, hy + 9, 2.8, h, 'prism', tilt=tilt)
    a.e(hx, hy, 13.5, 12, 'plate')
    a.e(hx - 4, hy + 6, 7.4, 4, 'plate', out=False)
    a.poly([(hx - 11, hy + 3), (hx + 12, hy + 3), (hx + 12, hy - 7), (hx - 11, hy - 7)], 'ink', out=False)
    state = T['state']
    for dx in (-4.8, 5.4):
        if state == 'dead':
            a.line((hx + dx - 2.4, hy - 1), (hx + dx + 2.4, hy - 5), 'glow1', 2)
            a.line((hx + dx - 2.4, hy - 5), (hx + dx + 2.4, hy - 1), 'glow1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2), 3.8, 3.3 * a.sy)[0], 'glow0', outline=True)
            a.f.flat(ellipsoid(*a.g(hx + dx + .6, hy - 2.3), 2.1, 2.5 * a.sy)[0], 'iris')
            a.dot(hx + dx - 1.4, hy - .2, 'shine', 1)
    a.line((hx - 11, hy - 8), (hx + 12, hy - 8), 'gold1', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 8 + k * 4, 36), tip[1] + k * 4 - 4, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def mirrorqueen(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('mirrorqueen', clip, n, sy=1 - fall * .55)
    sway = math.sin(n * math.pi / 3) * 1.4 if clip == 'idle' else sw * 1.8
    b = bob * .7
    # floating shards that orbit her
    for k in range(5):
        th = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) + k * 2 * math.pi / 5
        if fall:
            continue
        px, py = math.cos(th) * 31, 43 + math.sin(th) * 7 + (k % 2) * 8 + b
        diamond(a, px, py, 2.6, 5, 'mirror1' if math.sin(th) < 0 else 'mirror2', out=True)
        a.dot(px - .6, py + 1.4, 'shine')
    # hair behind, then the gown
    hx, hy = 1 + sway * .3, 57 + b
    a.e(hx - 2, hy - 5, 15.4, 19, 'hair')
    hem = [(-24, 6), (-21, 14), (-17, 4), (-12, 12), (-7, 2), (-2, 11), (3, 2), (8, 11), (13, 3), (17, 12), (21, 4),
           (24, 14), (24, 6)]
    gown = [(-10, 42 + b), (10, 42 + b), (15, 30), (24 + sway, 14)] + hem[::-1][:0] + [(25 + sway * .5, 6), (-25 + sway * .5, 6), (-24, 14), (-15, 30)]
    a.band(gown, 'gown')
    a.band([(-18 + sway * .3, 7), (-12, 14), (-7, 4), (-2, 13), (3, 4), (8, 13), (13, 5), (18, 12), (19, 7)], 'gown', out=False)
    for k, (x, y, w, h) in enumerate(((-12, 20, 3, 6), (0, 15, 4, 8), (12, 20, 3, 6), (-6, 30, 2.4, 5), (7, 30, 2.4, 5))):
        diamond(a, x + sway * .3, y, w, h, 'mirror2' if k % 2 else 'mirror1', out=True)
        a.dot(x - 1 + sway * .3, y + 1, 'shine')
    a.line((-24, 5), (24, 5), 'gold1', 2)
    a.e(0, 41 + b, 10.4, 7.6, 'gown')
    a.line((-9, 38 + b), (9, 38 + b), 'gold1', 2)
    a.poly([(0, 46 + b), (3, 42.5 + b), (0, 39 + b), (-3, 42.5 + b)], 'mirror2', edge='ink')
    # the hand mirror (her sceptre)
    wind_, strike_ = wind, strike
    hand = (lerp(lerp(-23, -17, wind_), 14, strike_), lerp(lerp(40, 62, wind_), 50, strike_))
    if clip == 'die':
        hand = (lerp(-23, -14, fall), lerp(40, 10, fall))
    far = (24, 36 + b)
    a.c((9, 43 + b), far, 3.4, 3, 'gown')
    a.e(far[0], far[1], 3, 3, 'skin')
    a.c((-9, 43 + b), hand, 3.6, 3, 'gown')
    a.e(hand[0], hand[1], 3, 3, 'skin')
    if clip != 'die' or fall < .4:
        a.line((hand[0], hand[1]), (hand[0] - 2, hand[1] + 9), 'gold1', 2)
        a.e(hand[0] - 2.5, hand[1] + 16, 7, 8.4, 'gold')
        a.e(hand[0] - 2.5, hand[1] + 16, 5, 6.4, 'mirror', out=False)
        a.line((hand[0] - 5, hand[1] + 19), (hand[0] - 1, hand[1] + 13), 'beam1', 1)
        a.dot(hand[0] - 5, hand[1] + 20, 'shine', 2)
    # head: big chibi face, crown of mirror shards
    for k, (dx, h, tilt) in enumerate(((-9, 10, -4), (-4.5, 15, -2), (0, 18, 0), (4.5, 14, 2), (9, 9, 4))):
        crystal(a, hx + dx, hy + 8, 2.6, h, 'mirror', tilt=tilt)
    a.e(hx, hy, 12.4, 11.6, 'skin')
    a.poly([(hx - 12, hy + 3), (hx - 7, hy + 9), (hx - 1, hy + 1), (hx + 5, hy + 8), (hx + 12, hy + 3), (hx + 13, hy + 10),
            (hx - 13, hy + 10)], 'hair1')
    a.line((hx - 11, hy + 8), (hx + 11, hy + 8), 'gold1', 2)
    a.eye(hx + 2.4, hy - 2, 4.5, iris='iris')
    a.eye(hx + 10, hy - 2, 3.4, iris='iris')
    a.dot(hx - 4, hy - 6, 'blush', 3)
    a.line((hx + 3, hy - 7), (hx + 7, hy - 6), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        mx, my = hand[0] - 2.5, hand[1] + 16
        a.poly([(mx + 6, my + 3), (35, my + 11 + (n - 3)), (35, my - 7 - (n - 3)), (mx + 6, my - 3)], 'beam0', out=False)
        a.poly([(mx + 6, my + 1.4), (35, my + 5), (35, my - 1), (mx + 6, my - 1.4)], 'beam1', out=False)
        for k in range(3):
            star(a, 20 + k * 8, my + 6 - k * 3, 2.6, 'beam1')
    if clip == 'die':
        for k in range(5):
            diamond(a, -22 + k * 11, max(3, 38 - fall * 34 + (k % 3) * 6), 2.4, 4.4, 'mirror2' if k % 2 else 'mirror1', out=True)
    return a.done()


# ------------------------------------------------------------------------------------------------
def sunshard(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('sunshard', clip, n, sy=1 - fall * .55)
    flare = max(wind, strike)
    cy = 44 + bob * 1.4 - fall * 26
    a.lift = 0
    # rays: a rotating wheel of long and short points behind the crystal
    if fall < .6:
        spin = n * (math.pi / 18 if clip in ('idle', 'walk') else math.pi / 7)
        for k in range(12):
            ang = spin + k * math.pi / 6
            ln = (35 if k % 2 == 0 else 28) + flare * 5
            r0 = 19
            a.poly([(math.cos(ang - .13) * r0, cy + math.sin(ang - .13) * r0 * .9),
                    (math.cos(ang) * ln, cy + math.sin(ang) * ln * .9),
                    (math.cos(ang + .13) * r0, cy + math.sin(ang + .13) * r0 * .9)], 'ray1' if k % 2 == 0 else 'ray0')
    # orbiting shards, those behind first
    def orbit(front):
        for k in range(6):
            th = n * (math.pi / 5 if clip == 'idle' else math.pi / 3.5) + k * math.pi / 3
            if (math.sin(th) >= 0) != front or fall > .6:
                continue
            px, py = math.cos(th) * 32, cy - 2 + math.sin(th) * 9
            diamond(a, px, py, 3, 6.4, 'sun2', out=True)
            a.dot(px - .8, py + 2, 'core0')
    orbit(False)
    # the crystal body: tall, faceted, hot at the middle
    body = [(0, cy + 28), (12, cy + 17), (16, cy + 2), (13, cy - 14), (0, cy - 25), (-13, cy - 14), (-16, cy + 2), (-12, cy + 17)]
    a.band(body, 'sun')
    a.poly([(0, cy + 25), (9, cy + 15), (11, cy + 2), (0, cy - 3), (-11, cy + 2), (-9, cy + 15)], 'sun2', out=False)
    a.poly([(0, cy + 25), (-9, cy + 15), (-4, cy + 8), (4, cy + 8), (9, cy + 15)], 'sun3', out=False)
    a.line((0, cy + 28), (0, cy + 8), 'sun1', 1)
    a.line((-12, cy + 17), (-6, cy + 2), 'sun3', 1)
    a.line((13, cy - 14), (7, cy - 2), 'sun1', 1)
    # a face on the crystal
    a.eye(-5.2, cy + 7, 4.6, iris='iris', look=(0, .1))
    a.eye(5.4, cy + 7, 4.6, iris='iris', look=(.5, .1))
    a.dot(-9, cy + 1, 'blush', 3)
    a.dot(8.5, cy + 1, 'blush', 3)
    a.line((-2, cy - 3), (2, cy - 3), 'ink', 1)
    # crystal fists float beside the body
    fist = (lerp(lerp(30, 27, wind), 33, strike), lerp(lerp(cy - 14, cy + 20, wind), cy - 8, strike))
    for s_, fx, fy in ((-1, -30, cy - 14 + sw * 2), (1, fist[0], fist[1])):
        if clip == 'die' and fall > .3:
            continue
        a.poly([(fx - 7, fy), (fx, fy + 9), (fx + 7, fy), (fx, fy - 9)], 'sun2')
        a.poly([(fx - 3, fy + 1), (fx, fy + 5), (fx + 3, fy + 1)], 'sun3', out=False)
        a.line((fx - 3, fy + 3), (fx - 1, fy - 3), 'core0', 1)
    orbit(True)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(fist[0] + 6 + k * 4, 38), fist[1] + 2 - k * 3 + (k % 2) * 3, 3.4, 'core0' if k % 2 else 'ray2')
    if clip == 'die':
        for k in range(6):
            px, py = -26 + k * 10, max(4, 40 - fall * 36 + (k % 3) * 7 - k)
            a.poly([(px - 3, py), (px, py + 5), (px + 3, py), (px, py - 5)], 'sun2' if k % 2 else 'ray1')
    return a.done()


DRAW = dict(miragejackal=miragejackal, shardscarab=shardscarab, glassharrier=glassharrier, prismsentinel=prismsentinel,
            mirrorqueen=mirrorqueen, sunshard=sunshard)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/prism-preview')
    print('ok')
