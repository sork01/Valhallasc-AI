"""Cel-shaded Grand Nave enemies (zone 12) for make_cathedral_sprites.py.

Same recipe as cathedral_reliquary_redraw.py (hard bands, dark outlines, big glossy eyes, chibi heads); the
Drowned Templar and Bound Cantor that also live here are drawn there.
`python3 scripts/cathedral_nave_redraw.py [kind...]` writes contact sheets to test-results/nave-preview.
"""
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk, timing
from make_crag_sprites import AX, AY, CLIPS, H, W, ellipsoid, rgba

KINDS = ('abysszealot', 'chainmarshal', 'starseraph', 'tidejudicator', 'hierophant')
ROOT = Path(__file__).resolve().parents[1]

PALETTES = {
    'abysszealot': mk(robe=('#1d1240', '#3b2678', '#6446b4', '#a58ae8'), rag=('#120a2b', '#2a1b58', '#4a3590'),
                      gold=('#8c5d16', '#dba22f', '#ffe382'), flame=('#5a2fb8', '#9b6bff', '#e3d2ff'),
                      chain=('#5a6783', '#a0aec6', '#e0eaf6'), iris='#b57bff', bone=('#b8a8c8', '#efe6f8')),
    'chainmarshal': mk(steel=('#252d40', '#46577a', '#7d92b6', '#c5d4ec'), gold=('#7a4f12', '#c98f28', '#f6d467'),
                       chain=('#4b566f', '#98a6c0', '#dfe9f6'), glow=('#e6ffff', '#4fe3f0'),
                       rust=('#5a2f24', '#8f4a32', '#c26e45'), iris='#ff7a45', dust='#cfc4b6'),
    'starseraph': mk(wing=('#5b4c9c', '#9d8de0', '#d6ccff', '#f6f2ff'), robe=('#352b6e', '#6154b4', '#988ae6', '#d2c8ff'),
                     skin=('#b49ac4', '#e6d0ec', '#fff0f8'), hair=('#7f78ae', '#c3bee8', '#f2f0ff'),
                     gold=('#8c5d16', '#dba22f', '#ffe382'), iris='#7a55ee', tear='#a8e8ff'),
    'tidejudicator': mk(robe=('#403b30', '#7a7260', '#b6ab8e', '#e6dcc0'), gold=('#7a4f12', '#c98f28', '#f6d467'),
                        skin=('#a98672', '#d8b49a', '#f6dcc6'), cloth=('#8a8598', '#cbc6d8', '#f6f4ff'),
                        iron=('#2d2f3c', '#585d73', '#9399b3'), dust='#cfc4b6', mouth='#6a2f3e',
                        hair=('#7a7a8e', '#c0c0d0')),
    'hierophant': mk(robe=('#2c1c60', '#5838a6', '#8c66e4', '#c8aeff'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                     skin=('#bc8c78', '#ecbfa6', '#ffe2d0'), beard=('#9a96b8', '#d4d0ec', '#f6f4ff'),
                     tide=('#1c63b4', '#3aa6f2', '#9fe4ff', '#f0ffff'), iris='#5d3fd8'),
}

R.PALETTES.update(PALETTES)   # Art looks its palette up by kind


def chain(a, p0, p1, sag, group='chain', r=1.6):
    for k in range(1, 8):
        t = k / 8
        x = lerp(p0[0], p1[0], t)
        y = lerp(p0[1], p1[1], t) - math.sin(t * math.pi) * sag
        a.e(x, max(y, 2), r, r, group)


def abysszealot(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('abysszealot', clip, n, sy=1 - fall * .5)
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    stoop = 4
    # ragged robe, hunched forward
    a.band([(-9, 46 + bob), (9 + stoop, 46 + bob), (14, 20), (17, 8), (13, 0), (8, 6), (3, 0), (-2, 7), (-7, 1),
            (-13, 7), (-15, 0), (-13, 20)], 'robe')
    a.line((-4, 40), (-9, 6), 'robe0', 2)
    a.line((-14, 18), (14, 18), 'gold1', 2)
    # far arm drags the censer chain; near arm lifts it
    swing = math.sin(n * math.pi / 3) * 4 if clip == 'idle' else sw * 5
    hand = (lerp(lerp(17, 8, wind), 24, strike), lerp(lerp(34, 52, wind), 38, strike) + bob)
    a.c((7 + stoop * .6, 44 + bob), hand, 3.6, 3, 'robe')
    a.e(hand[0], hand[1], 3, 3, 'bone')
    cens = (lerp(lerp(hand[0] + swing, hand[0] - 18, wind), 28, strike),
            lerp(lerp(hand[1] - 20, hand[1] + 10, wind), 30, strike))
    if fall > .5:
        cens = (hand[0] + 4, 5)
    chain(a, (hand[0], hand[1] - 2), cens, 3)
    a.e(cens[0], cens[1], 5.5, 5.5, 'gold')
    a.e(cens[0], cens[1] + 6, 3.4, 4.4, 'flame')
    a.dot(cens[0] - 2, cens[1] + 2, 'shine')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            a.dot(cens[0] + 5 + k * 2, cens[1] + 2 + (k % 2) * 3, 'flame1', 2)
    # tall pointed cowl around a black void with two big staring eyes
    hx, hy = 3 + stoop, 57 + bob
    a.band([(hx - 12, hy - 10), (hx + 12, hy - 10), (hx + 11, hy + 8), (hx + 1, hy + 24), (hx - 5, hy + 12),
            (hx - 12, hy + 4)], 'robe')
    a.e(hx + 1, hy, 9.5, 10, 'rag', edge='ink')
    a.f.flat(ellipsoid(*a.g(hx + 1, hy), 8.2, 8.8)[0], 'ink')
    for dx, r in ((-1.5, 3.9), (7, 3.2)):
        a.eye(hx + dx, hy + 1, r, iris='iris', look=(.9, 0))
    a.dot(hx - 5, hy + 15, 'gold2', 2)
    return a.done()


def chainmarshal(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('chainmarshal', clip, n, sy=1 - fall * .45)
    a.pk = 0.85
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    for side in (-1, 1):
        g = sw * 5 * side if clip == 'walk' else 0
        up = max(0, math.sin(n * math.pi / 2 + (side > 0) * math.pi)) * 3 if clip == 'walk' else 0
        a.c((side * 6, 30 + bob), (side * 7 + g, 4 + up), 6.4, 5, 'steel')
        a.e(side * 7 + g + 3, 3 + up, 8, 4, 'steel')
    # far arm: a manacle fist hanging with a loop of chain
    a.c((-12, 60 + bob), (-19, 40 + bob), 5.6, 5, 'steel')
    a.e(-19, 38 + bob, 5.2, 5.2, 'gold')
    chain(a, (-19, 34 + bob), (-26, 6), 6)
    # barrel chest strapped with chains, a gold lock at the crossing
    a.e(0, 52 + bob, 16.5, 18, 'steel')
    a.line((-13, 64 + bob), (13, 40 + bob), 'chain1', 3)
    a.line((13, 64 + bob), (-13, 40 + bob), 'chain2', 3)
    a.e(0, 52 + bob, 4.6, 5, 'gold')
    a.band([(-12, 36 + bob), (12, 36 + bob), (15, 28), (-15, 28)], 'rust')
    a.line((-15, 36 + bob), (15, 36 + bob), 'gold1', 2)
    # spiked pauldrons
    for side, k in ((-1, 0), (1, 1)):
        a.e(side * 18, 66 + bob, 8.5, 6.5, 'steel')
        for dx in (-4, 0, 4):
            a.poly([(side * 18 + dx - 2, 70 + bob), (side * 18 + dx, 77 + bob), (side * 18 + dx + 2, 70 + bob)], 'gold2')
    # great helm: visor slit, glowing eyes, hanging chain veil
    hx, hy = 3, 76 + bob
    a.e(hx, hy, 12.5, 10.5, 'steel')
    a.poly([(hx - 5, hy + 1), (hx + 13, hy + 1), (hx + 13, hy - 5), (hx - 5, hy - 5)], 'ink', out=False)
    for dx in (0, 8):
        if T['state'] == 'dead':
            a.line((hx + dx - 2.5, hy - 2), (hx + dx + 2.5, hy - 4), 'glow1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2), 3.2, 1.9)[0], 'iris' if T['state'] == 'angry' else 'glow1')
    a.line((hx - 4, hy + 10), (hx + 3, hy + 14), 'gold2', 2)
    for k in range(5):
        a.e(hx - 11 + k * .3, hy - 4 - k * 2.5, 1.6, 1.6, 'chain')
    # near arm swings a great iron anchor on a chain
    hand = (lerp(lerp(21, 10, wind), 24, strike), lerp(lerp(56, 74, wind), 36, strike) + bob)
    a.c((14, 62 + bob), hand, 5.6, 5, 'steel')
    a.e(hand[0], hand[1], 5, 5, 'gold')
    ax_ = lerp(lerp(hand[0] + 6, hand[0] - 10, wind), 28, strike)
    ay_ = lerp(lerp(hand[1] - 24, hand[1] - 6, wind), 17, strike)
    if fall > .5:
        ax_, ay_ = hand[0] + 6, 15
    chain(a, hand, (ax_, ay_ + 7), 3)
    a.line((ax_, ay_ - 7), (ax_, ay_ + 7), 'chain1', 3)
    a.e(ax_, ay_ + 9, 3.4, 3.4, 'chain')
    a.line((ax_ - 8, ay_ - 4), (ax_ + 8, ay_ - 4), 'chain1', 3)
    a.poly([(ax_ - 9, ay_ - 7), (ax_ - 5, ay_ - 11), (ax_, ay_ - 7), (ax_ + 5, ay_ - 11), (ax_ + 9, ay_ - 7),
            (ax_, ay_ - 14)], 'chain2')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(ax_ - 8 + k * 4, 2 + (k % 2) * 3, 'dust', 2)
    return a.done()


def starseraph(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('starseraph', clip, n, sy=1 - fall * .55)
    a.pk = 0.86
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    a.lift = 8 + bob * 1.2 - fall * 8
    flap = math.sin(n * math.pi / 3) * 5 if clip == 'idle' else math.sin(n * math.pi / 2) * 6
    if clip == 'attack':
        flap = lerp(-6, 8, wind) - strike * 4
    spread = 1 - fall * .6
    # two layers of broad feathered wings
    for side, ys, shade in ((-1, 1., 'wing'), (1, .8, 'wing')):
        for k in range(5):
            ang = math.radians(8 + k * 17) + flap * .02
            ln = (36 - k * 3) * ys * spread
            bx, by_ = side * 6, 52
            tip = (bx + side * math.cos(ang) * ln * .9, by_ + math.sin(ang) * ln - fall * 18 - 6)
            mid = (bx + side * math.cos(ang - .22) * ln * .6, by_ + math.sin(ang - .22) * ln * .6)
            mid2 = (bx + side * math.cos(ang + .25) * ln * .6, by_ + math.sin(ang + .25) * ln * .6)
            a.band([(bx, by_ - 2), mid, tip, mid2], shade)
    # gown with trailing cloth wisps and little gold stars
    a.band([(-7, 50 + bob), (7, 50 + bob), (11, 24), (14, 4), (6, 10), (0, 2), (-6, 10), (-14, 4), (-11, 24)], 'robe')
    for x, y in ((-4, 36), (4, 28), (-2, 18)):
        a.poly([(x, y + 3), (x + 1, y + 1), (x + 3, y), (x + 1, y - 1), (x, y - 3), (x - 1, y - 1), (x - 3, y),
                (x - 1, y + 1)], 'gold2', out=False)
    a.e(0, 49 + bob, 8.5, 6, 'robe')
    a.line((-8, 46 + bob), (8, 46 + bob), 'gold1', 2)
    # head: chibi face, long pale hair, a tear, broken halo
    hx, hy = 2, 62 + bob
    a.band([(hx - 8, hy + 5), (hx - 16, hy - 12), (hx - 12, hy - 30), (hx - 3, hy - 14), (hx + 2, hy - 4)], 'hair')
    a.e(hx, hy, 12, 12, 'skin')
    a.e(hx + 7, hy - 5.5, 2.4, 1.7, 'robe', out=False)
    a.eye(hx + 2.5, hy + .5, 4.3, iris='iris')
    a.eye(hx + 11, hy + .5, 3.5, iris='iris')
    a.dot(hx + 5, hy - 5, 'tear', 2)
    a.poly([(hx - 13, hy + 3), (hx - 8, hy + 14), (hx + 3, hy + 11), (hx + 13, hy + 11), (hx + 8, hy + 4),
            (hx + 1, hy + 5)], 'hair1')
    for k in range(9):
        t = math.radians(20 + k * 17)
        if k in (3, 4):
            continue
        a.e(hx + math.cos(t) * 12, hy + 15 + math.sin(t) * 5, 1.6, 1.6, 'gold')
    # arms: folded in prayer, thrown wide as the star bolt leaves
    open_ = max(wind, strike)
    for side in (-1, 1):
        h = (side * lerp(5, 21, open_), lerp(44, 56, open_) + bob)
        a.c((side * 6, 49 + bob), h, 3, 2.6, 'robe')
        a.e(h[0], h[1], 2.8, 2.8, 'skin')
    if clip == 'attack' and n in (3, 4, 5):
        sx = 30 + (n - 3) * 2
        a.poly([(sx, 61), (sx + 3, 57), (sx + 8, 56), (sx + 3, 55), (sx, 51), (sx - 3, 55), (sx - 8, 56),
                (sx - 3, 57)], 'gold2')
    return a.done()


def tidejudicator(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('tidejudicator', clip, n, sy=1 - fall * .4)
    a.pk = 0.88
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    # a monumental gown with gold borders
    a.band([(-10, 52 + bob), (10, 52 + bob), (16, 24), (21, 0), (-21, 0), (-16, 24)], 'robe')
    a.line((-6, 46), (-11, 4), 'robe0', 2)
    a.line((0, 50), (0, 2), 'gold1', 3)
    a.line((-20, 6), (20, 6), 'gold1', 2)
    # scales on the far hand: a beam with two tilting pans
    tilt = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else sw * 2
    sh = (-17, 44 + bob)
    a.c((-9, 52 + bob), sh, 4, 3.4, 'robe')
    a.e(sh[0], sh[1], 3.4, 3.4, 'skin')
    a.line((sh[0] - 11, sh[1] + 9 + tilt), (sh[0] + 5, sh[1] + 9 - tilt), 'gold2', 2)
    for sgn, tl in ((-1, tilt), (1, -tilt)):
        px = sh[0] - 3 + sgn * 8
        py = sh[1] + 9 + tl
        a.line((px, py), (px - 3, py - 8), 'gold1', 1)
        a.line((px, py), (px + 3, py - 8), 'gold1', 1)
        a.e(px, py - 9, 4.8, 2, 'gold')
    # chest and collar
    a.e(0, 56 + bob, 12, 11, 'robe')
    a.band([(-9, 62 + bob), (9, 62 + bob), (6, 52 + bob), (-6, 52 + bob)], 'gold')
    # head: stern chibi face with a blindfold and trailing knot
    hx, hy = 3, 70 + bob
    a.e(hx, hy, 12, 11.5, 'skin')
    a.poly([(hx - 13, hy + 5), (hx + 13, hy + 5), (hx + 13, hy - 3), (hx - 13, hy - 3)], 'cloth2')
    a.line((hx - 13, hy + 1), (hx + 13, hy + 1), 'cloth0', 1)
    a.e(hx + 5, hy + 1, 3, 3, 'gold')
    a.f.flat(ellipsoid(*a.g(hx + 5, hy + 1), 1.3, 1.3)[0], 'ink')
    a.poly([(hx - 12, hy + 1), (hx - 20 + sw * 2, hy - 2), (hx - 16, hy - 8)], 'cloth2')
    a.line((hx + 3, hy - 8), (hx + 8, hy - 8), 'mouth', 2)
    a.poly([(hx - 13, hy + 6), (hx - 9, hy + 15), (hx + 4, hy + 13), (hx + 13, hy + 7), (hx + 7, hy + 5)], 'hair1')
    a.band([(hx - 11, hy + 12), (hx + 12, hy + 12), (hx + 8, hy + 20), (hx - 7, hy + 20)], 'gold')
    # gavel: raised, then brought down on the floor
    hand = (lerp(lerp(21, 13, wind), 22, strike), lerp(lerp(46, 70, wind), 20, strike) + bob)
    a.c((9, 54 + bob), hand, 4, 3.4, 'robe')
    a.e(hand[0], hand[1], 3.4, 3.4, 'skin')
    ang = lerp(lerp(math.pi / 2, 2.1, wind), 0, strike)
    d = (math.cos(ang), math.sin(ang))
    pr = (-d[1], d[0])
    head = (hand[0] + d[0] * 14, hand[1] + d[1] * 14)
    a.c((hand[0] - d[0] * 6, hand[1] - d[1] * 6), head, 1.8, 1.8, 'gold')
    a.c((head[0] - pr[0] * 8, head[1] - pr[1] * 8), (head[0] + pr[0] * 8, head[1] + pr[1] * 8), 6, 6, 'iron')
    a.line((head[0] - pr[0] * 5, head[1] - pr[1] * 5), (head[0] + pr[0] * 5, head[1] + pr[1] * 5), 'gold2', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(24 + k * 2.2, 3 + (k % 2) * 3 + (n - 3), 'dust', 2)
    return a.done()


def hierophant(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('hierophant', clip, n, sy=1 - fall * .5)
    a.pk = 0.85
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    sway = math.sin(n * math.pi / 3) * 1.5 if clip == 'idle' else sw * 2
    # cathedral vestments: wide bell of violet with a gold orphrey and a hem of gold
    a.band([(-11, 54 + bob), (11, 54 + bob), (17, 26), (23, 0), (-23, 0), (-17, 26)], 'robe')
    a.band([(-3, 54 + bob), (3, 54 + bob), (4, 2), (-4, 2)], 'gold')
    a.line((-22, 6), (22, 6), 'gold1', 3)
    for x in (-13, 13):
        a.line((x, 40), (x * 1.3, 8), 'robe0', 2)
    # staff with a swirling tide orb
    hand = (lerp(lerp(26, 20, wind), 25, strike), lerp(lerp(46, 58, wind), 44, strike) + bob)
    top = (hand[0] + 1 + strike * 2, hand[1] + 28)
    a.c((hand[0] + 1, 4), top, 1.5, 1.5, 'gold')
    pulse = 'tide2' if (wind + strike) > .5 or (clip == 'idle' and n % 2) else 'tide1'
    a.e(top[0], top[1] + 5, 7, 7, 'tide')
    a.f.flat(ellipsoid(*a.g(top[0], top[1] + 5), 4.2, 4.2)[0], pulse)
    a.dot(top[0] - 3, top[1] + 8, 'shine', 2)
    # chest: a glowing tide-heart in the open mantle
    a.e(0, 52 + bob, 12, 10, 'robe')
    a.e(0, 50 + bob, 5.2, 5.6, 'tide')
    a.f.flat(ellipsoid(*a.g(0, 50 + bob), 2.6, 3)[0], pulse)
    a.band([(-14, 62 + bob), (14, 62 + bob), (11, 54 + bob), (-11, 54 + bob)], 'gold')
    # far hand open as if casting
    fh = (-lerp(14, 20, max(wind, strike)), lerp(44, 62, max(wind, strike)) + bob)
    a.c((-9, 56 + bob), fh, 4, 3.4, 'robe')
    a.e(fh[0], fh[1], 3.2, 3.2, 'skin')
    # near arm and sleeve
    a.c((9, 56 + bob), hand, 4, 3.6, 'robe')
    a.e(lerp(9, hand[0], .6), lerp(56 + bob, hand[1], .6), 4.4, 3.8, 'gold')
    a.e(hand[0], hand[1], 3.2, 3.2, 'skin')
    # head: stern chibi face, long white beard, tall gold mitre
    hx, hy = 3, 66 + bob
    a.e(hx, hy, 11.5, 11, 'skin')
    a.poly([(hx - 10, hy - 2), (hx + 12, hy - 2), (hx + 10, hy - 18 - sway * .3), (hx + 1, hy - 24), (hx - 7, hy - 16)],
           'beard1')
    a.e(hx + 6, hy - 1, 3.2, 1.6, 'robe', out=False) if False else None
    a.eye(hx + 2.5, hy + 1.5, 4, iris='iris')
    a.eye(hx + 10.5, hy + 1.5, 3.3, iris='iris')
    a.line((hx - 1, hy + 7), (hx + 6, hy + 5), 'ink', 2)
    a.band([(hx - 11, hy + 8), (hx + 12, hy + 8), (hx + 8, hy + 19), (hx - 1, hy + 24), (hx - 9, hy + 19)], 'robe')
    a.band([(hx - 8, hy + 10), (hx + 9, hy + 10), (hx + 6, hy + 19), (hx - 1, hy + 22), (hx - 6, hy + 19)], 'gold',
           out=False)
    a.line((hx, hy + 12), (hx, hy + 20), 'gold0', 2)
    a.line((hx - 3, hy + 17), (hx + 3, hy + 17), 'gold0', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(2):
            a.e(top[0] + 6 + k * 2, top[1] + 4 + (k % 2) * 4 - k, 2.2, 2.2, 'tide')
    return a.done()


DRAW = dict(abysszealot=abysszealot, chainmarshal=chainmarshal, starseraph=starseraph,
            tidejudicator=tidejudicator, hierophant=hierophant)


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
                    print(f'  EDGE {kind} {clip} {n} x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()}')
                d.text((ox + 2, oy + H), f'{kind} {clip} {n}', fill='white')
            sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(
                out / f'{kind}_{clip}.png')


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, ROOT / 'test-results/nave-preview')
    line = Image.new('RGBA', (len(names) * W, H), '#2c3a44')
    for i, kind in enumerate(names):
        line.alpha_composite(rgba(draw(kind, 'idle', 0), PALETTES[kind].hex), (i * W, 0))
    line.resize((line.width * 3, line.height * 3), Image.Resampling.NEAREST).save(
        ROOT / 'test-results/nave-preview/lineup.png')
    print('ok')
