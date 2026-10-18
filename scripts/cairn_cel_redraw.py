"""Cel-shaded Cairnspine enemies (zone 27) for make_cairn_sprites.py.

Same recipe as frostwake_cel_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the six cairn_* NPCs keep their old art).
`python3 scripts/cairn_cel_redraw.py [kind...]` writes contact sheets to test-results/cairn-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp
from cel_zone_common import ROOT, diamond, mku as mk, preview, star, timing

KINDS = ('screeferret', 'stoneibex', 'slateraven', 'ridgeadder', 'cairnbehemoth', 'whitebarktitan', 'stormcondor')

PALETTES = {
    'screeferret': mk(fur=('#4a3a34', '#8a7258', '#c4a67e', '#f0dcb4'), belly=('#e8d8b8', '#fff8e4'),
                      mask=('#2a2024', '#5a4440'), stone=('#6a6a78', '#a8a8b8', '#dcdce8'), iris='#2a3a8a',
                      blush='#ff9a9a', nose='#e8607a', tooth='#fffcf0'),
    'stoneibex': mk(fur=('#4a3e32', '#8e7a5e', '#c8b088', '#f2e0b8'), horn=('#5a4a38', '#a89070', '#e0ccaa', '#fff2d4'),
                    belly=('#e8dcc0', '#fff8e8'), hoof=('#2a2028', '#5a4a58'), iris='#c88a1c', blush='#ff9a9a',
                    nose='#e8607a', beard=('#7a6a54', '#b8a888')),
    'slateraven': mk(feather=('#1c2234', '#3e4868', '#707c9c', '#b4c0dc'), beak=('#3a3a4a', '#6a6a7e', '#a8a8bc'),
                     claw=('#4a4a5a', '#8a8a9c'), iris='#e8c030', blush='#ff9ab0', shine=('#5a78c8', '#a8c0f4'),
                     leg=('#3a3844', '#6a6674')),
    'ridgeadder': mk(skin=('#5a4a20', '#a8903c', '#d8c070', '#f6ecb0'), belly=('#f0e4b0', '#fffcdc'),
                     zig=('#2a2418', '#5a4a30'), iris='#c8402a', blush='#ff9a9a', tongue=('#a82a4a', '#ff6a8a'),
                     fang=('#d8d0b8', '#fffcf0'), stone=('#6a6a78', '#a8a8b8', '#dcdce8')),
    'cairnbehemoth': mk(stone=('#3a3a44', '#6e6e7c', '#a4a4b2', '#d8d8e4'), moss=('#1c5a2c', '#3a9a48', '#8ad060'),
                        rock=('#52504e', '#8e8a84', '#c8c0b4'), iris='#ffd24a', blush='#ff9a9a', glow=('#7a4a14', '#f0a030'),
                        mouth=('#2a1a2c', '#5a3a58'), fist=('#5a5a68', '#9494a4', '#c8c8d8')),
    'whitebarktitan': mk(bark=('#8a8a74', '#d4d0b8', '#f2eed8', '#ffffff'), wood=('#4a3a2a', '#8a6a48', '#b8946a'),
                         leaf=('#1c6a3a', '#38b058', '#94ec88', '#e4ffc8'), iris='#ffd24a', blush='#ff9a9a',
                         mouth=('#3a1a24', '#7a3a4a'), glow=('#b8821a', '#ffd864'), root=('#3a2a20', '#6a4a38', '#9a7456')),
    'stormcondor': mk(feather=('#1c2640', '#3e5280', '#7490c0', '#c8dcf8'), wing=('#16203a', '#344a78', '#5c78b0', '#a8c4f0'),
                      ruff=('#d8d4c0', '#f8f4e4', '#ffffff'), skin=('#8a5a44', '#c88a64', '#f0b890'),
                      beak=('#a8741a', '#f4c448', '#fff0a0'), claw=('#5a5a6a', '#a8a8b8'), iris='#2ad0ff',
                      blush='#ff9ab0', bolt=('#d8b01a', '#ffe85a', '#fffbc0')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def screeferret(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('screeferret', clip, n, sy=1 - fall * .5)
    a.ox = -3
    a.pk = .94
    cy = 16 + bob * .5 - fall * 4
    lunge = strike * 4 - wind * 2
    for k, lx in enumerate((-18, -9, 8, 17)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 3 if clip == 'walk' else 0
        a.c((lx * .9, cy - 1), (lx + 2 + (lunge if k > 1 else 0), 3 + up), 3.2, 2.2, 'fur')
        a.e(lx + 3 + (lunge if k > 1 else 0), 2 + up, 3.4, 1.8, 'fur')
    wav = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else sw * 3
    a.c((-24, cy + 2), (-34, cy + 8 + wav * .5), 4.4, 2.6, 'fur')
    a.e(-2, cy + 3, 25, 9.4, 'fur')
    a.e(2, cy - 3, 16, 4.6, 'belly', out=False)
    # a loose scree stone on the back
    a.e(-8, cy + 13, 7, 4.4, 'stone')
    a.dot(-11, cy + 14, 'stone2', 2)
    hx, hy = 21 + lunge, cy + 10 - wind * 2
    a.e(hx - 4, hy + 8, 3, 3, 'fur')
    a.e(hx + 4, hy + 8, 3, 3, 'fur')
    a.e(hx, hy, 11.4, 9.2, 'fur')
    a.e(hx - 4, hy + 4, 6, 3, 'fur', out=False)
    a.e(hx + 4, hy + 2, 8, 3.6, 'mask', out=False)
    a.e(hx + 6, hy - 3, 6.4, 4.2, 'belly')
    a.dot(hx + 10, hy - 1, 'nose', 3)
    a.eye(hx - 1.8, hy + 2.6, 4.4, iris='iris', look=(.8, .1))
    a.eye(hx + 6.4, hy + 2.4, 3.6, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 2, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    if jaw > 1.2:
        a.dot(hx + 6, hy - 6 - jaw, 'tooth', 2)
        a.dot(hx + 9, hy - 6 - jaw, 'tooth', 2)
    else:
        a.line((hx + 3, hy - 6), (hx + 8, hy - 6), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 15 + k * 3, 40), hy - 2 + k * 3 - 4, 1.6, 2.6, 'stone1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def stoneibex(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('stoneibex', clip, n, sy=1 - fall * .5)
    a.ox = -6
    a.pk = .9
    cy = 26 + bob * .5 - fall * 7
    charge = strike * 6 - wind * 4
    for k, lx in enumerate((-17, -8, 8, 16)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        a.c((lx * .9, cy - 2), (lx + (charge * .5 if k > 1 else 0), 4 + up), 3.6, 2.6, 'fur')
        a.e(lx + 1 + (charge * .5 if k > 1 else 0), 2.6 + up, 3.8, 2.6, 'hoof')
    a.c((-22, cy + 6), (-28, cy + 10 + sw * 2), 2.2, 1.6, 'fur')
    a.e(-4, cy + 3, 22, 12, 'fur')
    a.e(2, cy - 4, 14, 5, 'belly', out=False)
    # neck, head and giant curved horns
    hx, hy = 18 + charge, cy + 14 - wind * 2 + strike * 2
    a.c((10, cy + 8), (hx - 2, hy - 2), 7, 6.4, 'fur')
    a.c((hx - 4, hy + 8), (hx - 14, hy + 18), 3.2, 2.6, 'horn')
    a.c((hx - 14, hy + 18), (hx - 22, hy + 10 - wind * 3), 2.6, 1.4, 'horn')
    a.c((hx - 1, hy + 8), (hx - 9, hy + 20), 3.2, 2.6, 'horn')
    a.c((hx - 9, hy + 20), (hx - 19, hy + 16), 2.6, 1.4, 'horn')
    for k in range(3):
        a.line((hx - 7 - k * 2, hy + 12 + k * 1.2), (hx - 5 - k * 2, hy + 14 + k * 1.2), 'horn0', 1)
    a.e(hx + 3, hy + 6, 3.4, 5, 'fur', ang=-.6)
    a.e(hx, hy, 11, 9.4, 'fur')
    a.e(hx - 4, hy + 4, 6, 3, 'fur', out=False)
    a.e(hx + 6, hy - 3, 6.6, 4.6, 'belly')
    a.dot(hx + 10, hy - 2, 'nose', 2)
    a.c((hx + 4, hy - 7), (hx + 3, hy - 14), 2.6, 1.4, 'beard')
    a.eye(hx - 1.4, hy + 2.6, 4.4, iris='iris', look=(.8, .1))
    a.eye(hx + 6, hy + 2.4, 3.4, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 15 + k * 3, 40), hy - 2 + k * 3 - 4, 2, 'horn3')
    return a.done()


# ------------------------------------------------------------------------------------------------
def slateraven(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('slateraven', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .9
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-4, -9, -14, 8, 10, 4, 1, 0)[n]
    cy = 32 + b - fall * 8
    for k in range(3):
        a.c((-6, cy - 4), (-20 - k * 2 + sw * 1.5, 8 + k * 3), 3.6, 1.6, 'feather')
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 4 - 2, cy - 11), (s * 5 - 1, 5 + up), 2, 1.6, 'leg')
        a.e(s * 5 + 2, 3 + up, 4.6, 1.8, 'claw')
    a.e(0, cy, 14, 15, 'feather')
    a.e(5, cy - 3, 7.6, 9.6, 'feather', out=False)
    a.e(-10, cy + 1 + flap * .8, 9, 14, 'feather', ang=.25 - flap * .03)
    a.e(-10, cy + 3 + flap * .8, 5, 9, 'shine', ang=.25 - flap * .03, out=False)
    hx, hy = 8 + strike * 5 - wind * 3, cy + 20 + wind * 2 - strike * 5
    a.e(hx, hy, 11.4, 10.4, 'feather')
    a.e(hx - 4, hy + 4, 6, 3, 'feather', out=False)
    jaw = max(wind * .5, strike) * 3
    a.poly([(hx + 6, hy + 3), (hx + 19, hy - 1 - jaw * .4), (hx + 6, hy - 4 - jaw)], 'beak1')
    a.line((hx + 7, hy - 1), (hx + 16, hy - 1.4), 'beak0', 1)
    for k in range(3):
        a.c((hx - 2 + k * 3, hy + 9), (hx - 4 + k * 3 + sw * .5, hy + 14), 2.4, 1, 'feather')
    a.eye(hx + 0.6, hy + 2.6, 4.6, iris='iris', look=(.8, .1))
    a.dot(hx - 5, hy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 20 + k * 2, 40), hy - 4 + k * 4, 2.2, 'shine1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def ridgeadder(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('ridgeadder', clip, n, sy=1 - fall * .5)
    a.ox = -6
    a.pk = .94
    b = bob * .5
    # an S of coils, lowest at the back, rising to a raised head
    wav = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else sw * 2
    segs = [(-30, 6), (-22, 8), (-12, 7), (-2, 8), (8, 11), (12 + wav, 20), (11 + wav, 30 + b)]
    for i in range(len(segs) - 1):
        r = 5 + i * .5
        a.c(segs[i], segs[i + 1], r, r + .5, 'skin')
    for i in range(0, len(segs) - 1):
        x, y = segs[i]
        a.dot(x - 1, y + 1, 'zig0', 3)
    a.c((-30, 6), (-38, 4 + sw * 2), 4, 1.2, 'skin')
    a.c((8, 8), (12 + wav, 20), 2.4, 2.4, 'belly', out=False)
    hx = 14 + strike * 12 - wind * 5 + wav
    hy = 40 + b - strike * 12 + wind * 3 - fall * 14
    a.c((11 + wav, 30 + b), (hx - 2, hy - 4), 5.6, 5.6, 'skin')
    a.e(hx, hy, 11.4, 8.4, 'skin')
    a.e(hx - 4, hy + 3, 6, 2.6, 'skin', out=False)
    a.e(hx + 6, hy - 2, 6, 4, 'belly')
    # zigzag ridge on the head
    for k in range(3):
        diamond(a, hx - 5 + k * 4, hy + 8, 1.8, 2.6, 'zig1')
    a.eye(hx - 1.4, hy + 2.6, 4.2, iris='iris', look=(.8, .1))
    a.eye(hx + 6, hy + 2.4, 3.2, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 1, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 4, hy - 4 - jaw), (hx + 12, hy - 4 - jaw), 'ink', 1)
    tl = 6 + strike * 5
    a.line((hx + 11, hy - 4 - jaw), (hx + 11 + tl, hy - 4 - jaw), 'tongue1', 1)
    a.line((hx + 11 + tl, hy - 4 - jaw), (hx + 13 + tl, hy - 2 - jaw), 'tongue1', 1)
    a.line((hx + 11 + tl, hy - 4 - jaw), (hx + 13 + tl, hy - 6 - jaw), 'tongue1', 1)
    if jaw > 1.5:
        a.poly([(hx + 7, hy - 4 - jaw), (hx + 9, hy - 4 - jaw), (hx + 8, hy - 8 - jaw)], 'fang1', out=False)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 17 + k * 3, 40), hy - 4 + k * 4, 2, 'zig1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def cairnbehemoth(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('cairnbehemoth', clip, n, sy=1 - fall * .5)
    a.pk = .82
    a.lift = fall * 5
    b = bob * .7
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 10, 22), (s * 11, 5 + up), 7.4, 6, 'stone')
        a.e(s * 12, 3.6 + up, 9, 4, 'rock')
    # a stack of balanced boulders for the torso, moss on top
    a.e(0, 30 + b, 24, 12, 'stone')
    a.e(-1, 44 + b, 20, 10, 'rock')
    a.e(0, 56 + b, 15, 8, 'stone')
    a.e(-10, 50 + b, 9, 3.4, 'rock', out=False)
    for k, (mx, my) in enumerate(((-9, 62), (-3, 65), (4, 63))):
        a.e(mx, my + b, 4.4, 3, 'moss')
    a.e(-8, 36 + b, 8, 2.6, 'stone', out=False)
    a.e(8, 41 + b, 4, 4, 'glow', out=False)
    # arms of stacked rocks, the near fist slams
    far = (-31, 36 + b + sw * 2)
    a.c((-20, 46 + b), far, 8, 7, 'stone')
    a.e(far[0], far[1] - 4, 8.4, 7.4, 'fist')
    fist = (lerp(lerp(30, 28, wind), 33, strike), lerp(lerp(40, 66, wind), 34, strike) + b)
    if clip == 'die':
        fist = (lerp(32, 36, fall), lerp(40, 8, fall))
    a.c((19, 46 + b), fist, 8.4, 7.4, 'stone')
    a.e(fist[0], fist[1] - 3, 9.4, 8, 'fist')
    for k in range(3):
        a.line((fist[0] - 3 + k * 3, fist[1] - 7), (fist[0] - 3 + k * 3, fist[1] - 2), 'fist0', 1)
    # head: a small round boulder with glowing eyes
    hx, hy = 0 + strike * 2, 70 + b
    a.e(hx, hy, 12.4, 10.6, 'stone')
    a.e(hx - 4, hy + 5, 6.4, 3, 'stone', out=False)
    a.eye(hx - 4.4, hy + 1.6, 4.4, iris='iris', look=(.4, .1))
    a.eye(hx + 5.6, hy + 1.6, 4, iris='iris', look=(.8, .1))
    a.dot(hx - 10, hy - 3, 'blush', 3)
    a.e(hx + 1, hy - 6, 4.4, 1.6 + max(wind * .4, strike) * 2.6, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(fist[0] + 10 + k * 2, 40), fist[1] - 6 + k * 5, 2.4, 'glow1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def whitebarktitan(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('whitebarktitan', clip, n, sy=1 - fall * .5)
    a.pk = .8
    a.lift = fall * 5
    b = bob * .6
    # root feet
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 9, 20), (s * 11, 5 + up), 6.4, 5, 'wood')
        for k in range(3):
            a.c((s * 12, 5 + up), (s * (16 + k * 3), 2), 2.4, 1, 'root')
    # pale trunk body with knot-face scars
    a.band([(-14, 22), (14, 22), (20, 50 + b), (-20, 50 + b)], 'bark')
    for k in range(4):
        a.line((-12 + k * 8, 24), (-14 + k * 9.4, 48 + b), 'bark0', 1)
    a.e(0, 50 + b, 21, 8, 'bark')
    a.e(3, 36 + b, 4, 6, 'glow', out=False)
    # branch arms with leaf hands
    far = (-31, 54 + b + sw * 2)
    a.c((-18, 48 + b), far, 5.4, 4, 'wood')
    for k in range(3):
        a.e(far[0] - 3 + k * 3, far[1] + 3 + k, 3, 5, 'leaf', ang=(k - 1) * .5)
    hand = (lerp(lerp(28, 26, wind), 29, strike), lerp(lerp(48, 70, wind), 40, strike) + b)
    if clip == 'die':
        hand = (lerp(30, 34, fall), lerp(48, 8, fall))
    a.c((17, 48 + b), hand, 5.8, 4.4, 'wood')
    for k in range(3):
        a.e(hand[0] + 1 + k * 3, hand[1] + 3 + k, 3, 5, 'leaf', ang=(k - 1) * .5)
    # face in the crown trunk and a leafy canopy
    hx, hy = 0 + strike * 2, 62 + b
    a.e(hx, hy, 14, 11.4, 'bark')
    a.e(hx - 5, hy + 5, 7, 3, 'bark', out=False)
    a.eye(hx - 5, hy + 1.6, 4.4, iris='iris', look=(.4, .1))
    a.eye(hx + 6, hy + 1.6, 4, iris='iris', look=(.8, .1))
    a.dot(hx - 11, hy - 3, 'blush', 3)
    a.e(hx + 1, hy - 6, 4.4, 1.6 + max(wind * .4, strike) * 2.6, 'mouth')
    for k, (lx, ly, ang) in enumerate(((-12, 11, .8), (-5, 14, .3), (3, 14, -.3), (11, 11, -.8))):
        a.e(hx + lx + sw * .5 * (k - 1.5), hy + ly, 4.6, 8, 'leaf', ang=ang)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hand[0] + 10 + k * 2, 40), hand[1] - 6 + k * 5, 2.4, 'glow1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def stormcondor(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('stormcondor', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .88
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 5 if clip == 'idle' else (math.sin(n * math.pi / 2) * 4 if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-4, -10, -16, 8, 12, 6, 2, 0)[n]
    cy = 32 + b - fall * 10
    for k in range(3):
        a.c((-8, cy - 4), (-24 - k * 2 + sw * 1.5, 8 + k * 3), 4.6, 1.8, 'feather')
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 6 - 2, cy - 10), (s * 6 - 1, 5 + up), 3, 2.4, 'claw')
        a.e(s * 6 + 3, 3 + up, 5.4, 2.2, 'claw')
    a.e(-2, cy + 2, 17, 16, 'feather')
    a.e(5, cy - 3, 9, 10, 'feather', out=False)
    # two storm-banded wings, one visible raised, a lightning bolt on it
    for k, grp in enumerate(('wing', 'feather', 'wing')):
        tip = (-32 + k * 8, cy + 30 + flap - k * 3)
        a.band([(-6 + k, cy + 8), (-2 + k * 4, cy + 12), tip, (-22 + k * 3, cy + 16 + k)], grp)
    bx, by = -24, cy + 18 + flap * .5
    a.poly([(bx + 2, by + 8), (bx - 2, by + 1), (bx + 1, by + 1), (bx - 3, by - 7), (bx + 5, by + 1), (bx + 2, by + 1)], 'bolt1')
    # neck, ruff and bald head
    hx, hy = 10 + strike * 6 - wind * 3, cy + 24 - strike * 3
    a.c((2, cy + 10), (hx - 2, hy - 3), 6, 5, 'skin')
    for k in range(6):
        a.e(-2 + k * 2.6, cy + 14 + (k % 2) * 2, 3.8, 3.4, 'ruff')
    a.e(hx, hy, 11.4, 10.4, 'skin')
    a.e(hx - 4, hy + 5, 6, 3, 'skin', out=False)
    jaw = max(wind * .5, strike) * 3
    a.poly([(hx + 6, hy + 1), (hx + 19, hy - 3 - jaw * .4), (hx + 15, hy - 9 - jaw), (hx + 5, hy - 5 - jaw)], 'beak1')
    a.line((hx + 7, hy - 3), (hx + 16, hy - 4), 'beak0', 1)
    a.eye(hx - 0.4, hy + 2.4, 4.8, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    for k in range(3):
        a.line((hx - 2 + k * 3, hy + 10), (hx - 4 + k * 3, hy + 15 + k), 'bolt1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(hx + 20 + k * 2, 40), hy - 6 + (k * 5) % 12, 2.2, 'bolt2')
    return a.done()


DRAW = dict(screeferret=screeferret, stoneibex=stoneibex, slateraven=slateraven, ridgeadder=ridgeadder,
            cairnbehemoth=cairnbehemoth, whitebarktitan=whitebarktitan, stormcondor=stormcondor)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/cairn-preview')
    print('ok')
