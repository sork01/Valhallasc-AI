"""Cel-shaded Flooded Cloister enemies (zone 10), second redraw for make_cathedral_sprites.py.

Replaces the flat-polygon first redraw (cathedral_cloister_redraw.py) with the style of the zone 11 and 12 sprites:
hard cel bands, dark outlines, big glossy eyes, chibi heads. The Drowned Templar and Bound Cantor of this zone are
drawn in cathedral_reliquary_redraw.py. `python3 scripts/cathedral_cloister_cel_redraw.py [kind...]` writes contact
sheets to test-results/cloister-preview.
"""
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk, timing
from make_crag_sprites import AX, AY, CLIPS, H, W, ellipsoid, rgba

KINDS = ('tideleech', 'bellkeeper', 'mournsister', 'rootabbot', 'choirmother')
ROOT = Path(__file__).resolve().parents[1]

PALETTES = {
    'tideleech': mk(body=('#1d5642', '#31905f', '#6cd486', '#c4f7a8'), belly=('#b6865a', '#f0c68a', '#fff0c6'),
                    spot='#f6a05a', mouth=('#45102a', '#d63a68'), iris='#2c3a86', fang='#fff7e6'),
    'bellkeeper': mk(verd=('#17595a', '#2f9a8e', '#7be0c6', '#d2fff0'), bronze=('#4a3220', '#8b5c2c', '#d19646', '#ffd988'),
                     skin=('#b8765f', '#e7aa8e', '#ffd9c0'), iron=('#2a2c36', '#585d73', '#9399b3'),
                     wood=('#4a2f1c', '#7d5233', '#b27d4f'), iris='#2d6fd0', dust='#cfc4b6', barn=('#8aa59c', '#d2e4dc')),
    'mournsister': mk(gown=('#40557d', '#7a9ac8', '#bad8f2', '#f0faff'), veil=('#8ea6d0', '#cfe0f6', '#fbfdff'),
                      skin=('#b88a86', '#ebc2bd', '#fff0ec'), hair=('#1e2a55', '#3b4f94'),
                      gold=('#8c5d16', '#dba22f', '#ffe382'), flame=('#2f98b8', '#7ee8ff', '#e9ffff'),
                      rose=('#d6607f', '#ff8aa8'), tear='#aef0ff', iris='#3f8fd8'),
    'rootabbot': mk(bark=('#3a291e', '#69482f', '#9b7348', '#d2a96d'), moss=('#2c5a2b', '#4c8c3a', '#86c755', '#c8ef88'),
                    kelp=('#1c5a49', '#2e9070', '#64d29e'), glow=('#ebffd2', '#8df069'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                    iris='#f2c230', dust='#cfc4b6'),
    'choirmother': mk(robe=('#1a4d66', '#2a8599', '#55c4bf', '#bbf4e6'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                      skin=('#c4806e', '#f0b8a2', '#ffe0cf'), hair=('#8a395a', '#cf6589', '#ff9db4'),
                      ghost=('#6a9cbe', '#b6dbef', '#effaff'), bell=('#2b9fa8', '#8ff0dc'), iris='#1e9fb0',
                      wave='#9ff2ff', mouth=('#5a1c34', '#ff7a98')),
}
R.PALETTES.update(PALETTES)   # Art looks its palette up by kind


def tideleech(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('tideleech', clip, n, sy=1 - fall * .35)
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    phase = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) * (1 if clip != 'idle' else .8)
    amp = {'idle': 1.4, 'walk': 3.2}.get(clip, 1.5)
    reach = lerp(lerp(0, -9, wind), 15, strike)
    rise = lerp(lerp(0, 7, wind), -6, strike)
    segs = []
    for k in range(7):
        t = k / 6
        x = -27 + t * 34 + reach * t ** 2
        y = 7 + 17 * t ** 1.6 * (1 - fall * .8) + math.sin(phase - k * .9) * amp * (1 - t * .5) + rise * t ** 2
        segs.append((x, y, 6.2 + 2.6 * math.sin(t * math.pi * .8) + t))
    for x, y, r in segs[:-1]:
        a.e(x, y, r, r * .95, 'body')
        a.e(x + 1, y - r * .45, r * .55, r * .3, 'belly', out=False)
    for x, y, r in segs[:-1:2]:
        a.dot(x - 1, y + r * .5, 'spot', 2)
    hx, hy, hr = segs[-1][0], segs[-1][1] + 5 - fall * 10, 11.5
    a.e(hx, hy, hr, hr - .5, 'body')
    # round sucker mouth with a ring of teeth, facing forward
    open_ = lerp(1., 1.5, max(wind, strike))
    a.e(hx + 8, hy - 1, 5.5 * open_, 7 * open_, 'mouth')
    for k in range(8):
        t = k / 8 * 2 * math.pi
        a.dot(hx + 8 + math.cos(t) * 4.6 * open_, hy - 1 + math.sin(t) * 6 * open_, 'fang', 1)
    a.eye(hx - 1.5, hy + 7, 4.1, iris='iris')
    a.eye(hx - 8.5, hy + 5.5, 3.3, iris='iris')
    return a.done()


def bellkeeper(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('bellkeeper', clip, n, sy=1 - fall * .4)
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    for side in (-1, 1):
        g = sw * 4 * side if clip == 'walk' else 0
        up = max(0, math.sin(n * math.pi / 2 + (side > 0) * math.pi)) * 3 if clip == 'walk' else 0
        a.c((side * 10, 12 + bob), (side * 11 + g, 3 + up), 5.6, 4.6, 'bronze')
        a.e(side * 11 + g + 2, 2 + up, 7, 3.4, 'bronze')
    # far hand rests on the bell
    a.c((-22, 34 + bob), (-28, 22 + bob), 4.4, 4, 'verd')
    a.e(-28, 21 + bob, 4.4, 4.4, 'skin')
    # the bell: verdigris dome, bronze rim and bands, barnacles
    a.band([(-28, 9 + bob), (-24, 28 + bob), (-17, 47 + bob), (-7, 58 + bob), (7, 58 + bob), (17, 47 + bob), (24, 28 + bob),
            (28, 9 + bob)], 'verd')
    a.e(0, 9 + bob, 28, 5.5, 'bronze')
    a.line((-24, 28 + bob), (24, 28 + bob), 'bronze2', 3)
    a.line((-17, 47 + bob), (17, 47 + bob), 'bronze2', 2)
    for x, y in ((-18, 20), (-9, 38), (19, 22), (14, 52), (-14, 52)):
        a.e(x, y + bob, 2.3, 1.9, 'barn')
    a.e(0, 61 + bob, 4.5, 4.5, 'bronze')
    # a round window in the bell frames his big-eyed face
    a.e(4, 34 + bob, 13.5, 13.5, 'bronze')
    a.e(4, 34 + bob, 11.5, 11.5, 'skin')
    a.eye(1, 36 + bob, 4.2, iris='iris')
    a.eye(10, 36 + bob, 3.5, iris='iris')
    a.line((1, 27 + bob), (8, 27 + bob), 'ink', 2)
    a.e(0, 29 + bob, 2.6, 1.7, 'verd', out=False)
    # mallet: upright at rest, hoisted back, then brought down on the stones
    hand = (lerp(lerp(27, 21, wind), 17, strike), lerp(lerp(30, 50, wind), 14, strike) + bob)
    a.c((19, 36 + bob), hand, 4.6, 4, 'verd')
    a.e(hand[0], hand[1], 4.2, 4.2, 'skin')
    ang = lerp(lerp(math.pi / 2, 2.0, wind), 0.1, strike)
    d = (math.cos(ang), math.sin(ang))
    pr = (-d[1], d[0])
    head = (hand[0] + d[0] * 15, hand[1] + d[1] * 15)
    a.c((hand[0] - d[0] * 8, hand[1] - d[1] * 8), head, 2.2, 2.2, 'wood')
    a.c((head[0] - pr[0] * 7, head[1] - pr[1] * 7), (head[0] + pr[0] * 7, head[1] + pr[1] * 7), 6.2, 6.2, 'iron')
    a.line((head[0] - pr[0] * 4, head[1] - pr[1] * 4), (head[0] + pr[0] * 4, head[1] + pr[1] * 4), 'bronze2', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(24 + k * 2, 3 + (k % 2) * 3 + (n - 3), 'dust', 2)
    return a.done()


def mournsister(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('mournsister', clip, n, sy=1 - fall * .5)
    a.pk = .88
    wind, strike, bob, sw = T['wind'], T['strike'], T['bob'], T['sw']
    a.lift = 6 + bob * 1.3 - fall * 6
    sway = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else sw * 2
    # long veil streaming behind, then the pale gown
    a.band([(0, 74), (-12, 66), (-20 + sway, 40), (-22 + sway * 1.4, 10), (-8, 14), (-2, 40), (4, 70)], 'veil')
    a.band([(-8, 50 + bob), (8, 50 + bob), (12, 24), (17, 4), (8, 10), (0, 2), (-8, 10), (-17, 4), (-12, 24)], 'gown')
    a.line((-4, 40), (-8, 8), 'gown0', 2)
    a.line((-12, 30), (12, 30), 'gold1', 2)
    a.e(0, 49 + bob, 8.6, 6.5, 'gown')
    # drops of water falling from the hem
    for k in range(3):
        a.e(-9 + k * 8, 3 + abs(math.sin(n * .8 + k * 2)) * 2, 1.5, 2, 'flame')
    # head under a long veil: huge sad eyes, a tear
    hx, hy = 2, 62 + bob
    a.e(hx, hy, 12, 12, 'skin')
    a.e(hx + 7, hy - 5.5, 2.4, 1.7, 'gown', out=False)
    a.e(hx - 3, hy - 5.5, 2.4, 1.7, 'gown', out=False)
    a.eye(hx + 2.5, hy + .5, 4.6, iris='iris', look=(.4, .4))
    a.eye(hx + 11, hy + .5, 3.7, iris='iris', look=(.4, .4))
    a.dot(hx + 5, hy - 4, 'tear', 2)
    a.dot(hx + 12, hy - 4, 'tear', 2)
    a.band([(hx - 13, hy + 2), (hx - 9, hy + 14), (hx + 3, hy + 15), (hx + 14, hy + 9), (hx + 8, hy + 6), (hx + 1, hy + 6),
            (hx - 8, hy + 5)], 'veil')
    a.poly([(hx - 12, hy + 4), (hx - 10, hy - 10), (hx - 6, hy - 8), (hx - 7, hy + 6)], 'hair1', out=False)
    a.e(hx - 6, hy + 15, 2.6, 2.6, 'rose')
    # lantern of tear-light: swings at rest, raised, then thrown forward
    hand = (lerp(lerp(21, 15, wind), 24, strike), lerp(lerp(37, 52, wind), 44, strike) + bob)
    a.c((8, 46 + bob), hand, 3.2, 2.8, 'gown')
    a.e(hand[0], hand[1], 3, 3, 'skin')
    lx, ly = hand[0] + 1, hand[1] - 11 + math.sin(n * 1.1) * (1 if clip == 'idle' else 0)
    a.line((hand[0], hand[1]), (lx, ly + 5), 'gold1', 1)
    a.poly([(lx - 5, ly + 4), (lx + 5, ly + 4), (lx + 4, ly - 6), (lx - 4, ly - 6)], 'gold1')
    a.f.flat(ellipsoid(*a.g(lx, ly - 1), 3, 4)[0], 'flame1')
    a.dot(lx - 1, ly + 1, 'flame2', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            tx, ty = lx + 7 + k * 3 + (n - 3), ly - 1 + (k % 2) * 3
            a.poly([(tx, ty + 3), (tx + 2, ty), (tx, ty - 3), (tx - 2, ty)], 'tear')
    return a.done()


def rootabbot(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('rootabbot', clip, n, sy=1 - fall * .45)
    a.pk = .9
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    for side in (-1, 1):
        g = sw * 4 * side if clip == 'walk' else 0
        up = max(0, math.sin(n * math.pi / 2 + (side > 0) * math.pi)) * 3 if clip == 'walk' else 0
        a.c((side * 8, 30 + bob), (side * 15 + g, 3 + up), 7, 4.4, 'bark')
        for k in (-1, 1):
            a.c((side * 15 + g, 4 + up), (side * 15 + g + k * 7, 1 + up), 2.4, 1.4, 'bark')
    # far branch-arm
    far = (-lerp(25, 28, max(wind, strike)), lerp(38, 62, max(wind, strike) * (1 - strike)) + bob)
    a.c((-14, 52 + bob), far, 7, 5.6, 'bark')
    a.e(far[0], far[1], 6, 5.2, 'moss')
    # trunk body in a rope-belted robe of moss, glowing heart
    a.e(0, 40 + bob, 20, 21, 'bark')
    a.e(-4, 52 + bob, 17, 9, 'moss')
    a.line((-19, 32 + bob), (19, 32 + bob), 'gold1', 3)
    a.e(2, 42 + bob, 6, 6.5, 'glow')
    a.f.flat(ellipsoid(*a.g(2, 42 + bob), 3, 3.4)[0], 'glow1')
    for x, y in ((-12, 36), (11, 28), (-6, 24)):
        a.e(x, y + bob, 3, 2.4, 'moss', out=False)
    # head with a mossy hood and a kelp beard
    hx, hy = 3, 68 + bob
    a.e(hx, hy, 14, 12.5, 'bark')
    a.band([(hx - 15, hy + 2), (hx - 11, hy + 14), (hx + 1, hy + 19), (hx + 13, hy + 13), (hx + 15, hy + 3), (hx + 6, hy + 8),
            (hx - 7, hy + 8)], 'moss')
    a.eye(hx + 2, hy + 1, 4.2, iris='iris')
    a.eye(hx + 11, hy + 1, 3.5, iris='iris')
    for k in range(5):
        sx = hx - 9 + k * 5
        a.poly([(sx - 2.4, hy - 7), (sx + sw * .6, hy - 18 - (k % 2) * 4), (sx + 2.4, hy - 7)], 'kelp1' if k % 2 else 'kelp2')
    # near branch-arm: raised for the wind-up, slammed down on the strike
    hand = (lerp(lerp(26, 20, wind), 30, strike), lerp(lerp(40, 64, wind), 10, strike) + bob)
    if clip == 'die':
        hand = (26 + fall * 4, 40 - fall * 28)
    a.c((15, 52 + bob), hand, 7.4, 6, 'bark')
    a.e(hand[0], hand[1], 7, 6, 'moss')
    for k in (-1, 0, 1):
        a.c((hand[0] + 2, hand[1]), (hand[0] + 8, hand[1] + k * 4), 2.4, 1.4, 'bark')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(28 + k * 2.2, 3 + (k % 2) * 3 + (n - 3), 'dust', 2)
    return a.done()


def choirmother(clip, n):
    T = timing(clip, n)
    fall = T['fall']
    a = Art('choirmother', clip, n, sy=1 - fall * .5)
    a.pk = .95
    sw, wind, strike, bob = T['sw'], T['wind'], T['strike'], T['bob']
    sing = max(wind, strike)
    # bell-flower halo behind the head
    hx, hy = 2, 62 + bob
    for k in range(9):
        t = math.radians(15 + k * 18)
        a.e(hx + math.cos(t) * 17, hy + 1 + math.sin(t) * 15, 3.4, 4, 'bell')
    # huge ruffled gown
    a.band([(-9, 48 + bob), (9, 48 + bob), (15, 26), (25, 0), (-25, 0), (-15, 26)], 'robe')
    a.line((-5, 38), (-10, 4), 'robe0', 2)
    a.line((5, 40), (11, 4), 'robe3', 1)
    for k in range(7):
        x = -22 + k * 7.3
        a.e(x, 3, 4.4, 3.6, 'robe', out=True)
    a.line((-14, 18), (14, 18), 'gold1', 2)
    a.e(0, 47 + bob, 9, 6.6, 'robe')
    a.band([(-10, 52 + bob), (10, 52 + bob), (6, 44 + bob), (-6, 44 + bob)], 'gold')
    # head: big eyes, coral hair piled in a bun, singing mouth
    a.e(hx - 7, hy + 14, 7, 6, 'hair')
    a.e(hx, hy, 12, 12, 'skin')
    a.e(hx + 7, hy - 5.5, 2.4, 1.7, 'mouth', out=False)
    a.e(hx - 3, hy - 5.5, 2.4, 1.7, 'mouth', out=False)
    if T['state'] in ('open', 'angry') and not T['blink']:
        for dx in (2.5, 11):
            a.line((hx + dx - 2.5, hy + 1), (hx + dx + 2.5, hy + 1), 'ink', 2)
            a.line((hx + dx - 2.5, hy + 1), (hx + dx - 3.5, hy - 1), 'ink', 1)
    else:
        a.eye(hx + 2.5, hy + .5, 4.4, iris='iris')
        a.eye(hx + 11, hy + .5, 3.6, iris='iris')
    a.e(hx + 5.5, hy - 7.5, 1.7 + sing * 1.3, 1.2 + sing * 2, 'mouth')
    a.poly([(hx - 13, hy + 3), (hx - 8, hy + 14), (hx + 3, hy + 11), (hx + 14, hy + 11), (hx + 8, hy + 4), (hx + 1, hy + 5)],
           'hair1')
    a.poly([(hx - 3, hy + 14), (hx + 1, hy + 21), (hx + 5, hy + 14)], 'gold2')
    # hands clasped at the chest
    a.c((-6, 46 + bob), (3, 40 + bob), 3, 2.8, 'robe')
    a.e(4, 41 + bob, 3.4, 3, 'skin')
    # three ghostly choir heads sing around her and surge forward on the attack
    for k in range(3):
        base = (-27 + k * 6, 66 - k * 10) if k < 2 else (20, 52)
        ang = n * (math.pi / 3 if clip != 'idle' else math.pi / 4) * .5 + k * 2.1
        gx = base[0] + math.cos(ang) * 3 + (strike * (4 + k * 1.5) if k != 0 else strike * 3)
        gy = base[1] + math.sin(ang) * 3 - fall * 30
        a.e(gx, gy, 7, 6.4, 'ghost')
        a.poly([(gx - 4, gy - 4), (gx - 1, gy - 12), (gx + 2, gy - 4)], 'ghost1', out=False)
        a.dot(gx - 3, gy + 1, 'ink', 2)
        a.dot(gx + 2, gy + 1, 'ink', 2)
        a.e(gx, gy - 3, 1.6 + sing * 1.2, 1.3 + sing * 1.8, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            for dy in (-5, 0, 5):
                a.dot(hx + 15 + k * 3 - abs(dy) * .25 + (n - 3), hy - 4 + dy, 'wave', 2)
    return a.done()


DRAW = dict(tideleech=tideleech, bellkeeper=bellkeeper, mournsister=mournsister, rootabbot=rootabbot,
            choirmother=choirmother)


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
    preview(names, ROOT / 'test-results/cloister-preview')
    line = Image.new('RGBA', (len(names) * W, H), '#2c3a44')
    for i, kind in enumerate(names):
        line.alpha_composite(rgba(draw(kind, 'idle', 0), PALETTES[kind].hex), (i * W, 0))
    line.resize((line.width * 3, line.height * 3), Image.Resampling.NEAREST).save(
        ROOT / 'test-results/cloister-preview/lineup.png')
    print('ok')
