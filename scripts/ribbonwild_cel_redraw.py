"""Cel-shaded Ribbonwild enemies (zone 21) for make_ribbonwild_sprites.py.

Same recipe as orrery_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the three host/keeper/travel NPCs keep their old art).
`python3 scripts/ribbonwild_cel_redraw.py [kind...]` writes contact sheets to test-results/ribbonwild-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('ribbongecko', 'balloonbeetle', 'paintedmacaw', 'jesterling', 'paradegryphon', 'maskcolossus')

PALETTES = {
    'ribbongecko': mk(skin=('#14485c', '#238a9c', '#44d2c0', '#a8f6e4'), belly=('#a8e8d4', '#eafff4'),
                      ribbon=('#a8286a', '#f165aa', '#ffa8d0'), toe=('#1a6a7a', '#6ae0cc'), iris='#f2a82e',
                      blush='#ff8ab8', spot='#fff3ad', mouth=('#4a1830', '#ff7a98')),
    'balloonbeetle': mk(shell=('#3a2a5e', '#7a4eac', '#b684e0', '#ecb8f8'), stripe=('#9a7a1c', '#f2ca53', '#fff0b5'),
                        leg=('#2a2046', '#5a4090'), balloon=('#a82a6a', '#ee5a9c', '#ff9cc8', '#ffe0ee'),
                        balloon2=('#1c6a8a', '#3aa8d0', '#8ae0f0', '#e0fbff'), string='#fff6e0', iris='#4a2a8a',
                        blush='#ff8ab8'),
    'paintedmacaw': mk(red=('#7a1c34', '#d4344c', '#f26a6a', '#ffb0a0'), blue=('#143a8a', '#2e66d0', '#52bbdf', '#b4f0ff'),
                       yellow=('#a8741a', '#f3d75d', '#fff1a0'), beak=('#2a2230', '#5a4a58', '#a8a0a8'),
                       face=('#d8c8c0', '#fff4ec'), leg=('#6a5a58', '#a89896'), iris='#26203a', blush='#ff8ab8',
                       green=('#1c6a3a', '#3ab860', '#9af0a0')),
    'jesterling': mk(pink=('#7a2a6a', '#d36ab3', '#f09ad4', '#ffd0ec'), teal=('#14625a', '#2eb09a', '#65d1aa', '#b8f6dc'),
                     skin=('#d49c8a', '#f8cdb4', '#ffe8d8'), gold=('#a8741a', '#f4bf78', '#fff0b8'), bell=('#c88a18', '#ffe27a'),
                     ball=('#a82a4a', '#f06a7a', '#ffb4ba'), iris='#6a2a8a', blush='#ff8a98', mouth=('#5a1c34', '#ff7a98'),
                     boot=('#3a2a4a', '#7a5a8a')),
    'paradegryphon': mk(feather=('#4a2a6a', '#8753a0', '#bc7cba', '#f0b8e0'), body=('#a8641c', '#e8a040', '#f7bb72', '#ffe4a8'),
                        wing=('#1c6a82', '#38acc4', '#67c8d9', '#c0f4fc'), plume=('#a82a6a', '#f165aa', '#ffa8d0'),
                        beak=('#a8741a', '#f4c448', '#fff0a0'), claw=('#c8b888', '#fff6d8'), iris='#2a4aa8',
                        blush='#ff8ab8', ribbon=('#d8a018', '#ffe88a')),
    'maskcolossus': mk(robe=('#34324d', '#7364b1', '#ae94dc', '#dccaf8'), mask=('#c8b090', '#f5e8cc', '#fffaee'),
                       gold=('#a8741a', '#f5d48a', '#fff4c0'), rose=('#a82a5a', '#e96c9c', '#ffa8c8'),
                       ruff=('#c8c0e0', '#f4f0ff', '#ffffee'), iris='#c8407a', fist=('#7a5a98', '#b494d8', '#e0ccf8'),
                       mouth=('#4a1830', '#d4507a')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def ribbongecko(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('ribbongecko', clip, n, sy=1 - fall * .5)
    a.ox = -2
    cy = 27 + bob * .6 - fall * 6
    lunge = strike * 7 - wind * 3
    # legs with sticky toe pads
    for k, lx in enumerate((-14, -5, 9, 17)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        grp = 'skin'
        a.c((lx * .85, cy - 1), (lx + 4 + (lunge if k > 1 else 0), 3 + up), 3.8, 2.4, grp)
        for t in (-1, 0, 1):
            a.e(lx + 4 + t * 2.6 + (lunge if k > 1 else 0), 2 + up, 1.7, 1.5, 'toe', out=False)
    # a thick tail ending in a bow with streaming ribbons
    wav = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else sw * 3
    a.c((-18, cy + 3), (-30, cy + 10 + wav * .5), 5, 3, 'skin')
    a.e(-31, cy + 11 + wav * .5, 3.6, 3.6, 'ribbon')
    for k, (dy, ph) in enumerate(((7, 0), (0, 1.6), (-7, 3.1))):
        w2 = math.sin(n * math.pi / 3 + ph) * 3 if clip == 'idle' else sw * 3 * (1 - k * .25)
        a.c((-31, cy + 11 + wav * .5), (-37 + k * 2, cy + 14 + dy * .9 + w2), 2.8, 1.2, 'ribbon')
    # body with spots and belly
    a.e(-2, cy + 4, 21, 12, 'skin')
    a.e(2, cy - 5, 14, 5.4, 'belly', out=False)
    for k in range(4):
        a.dot(-12 + k * 6, cy + 9 + (k % 2), 'spot', 2)
    # head: wide, with huge eyes on top
    hx, hy = 19 + lunge, cy + 11 - wind * 2 - strike * 2
    a.e(hx, hy, 12.6, 9.6, 'skin')
    a.e(hx - 3, hy + 4, 6, 3, 'skin', out=False)
    a.e(hx + 7, hy - 2, 6.4, 4.4, 'belly')
    a.eye(hx - 2.4, hy + 5.6, 4.8, iris='iris', look=(.7, .1))
    a.eye(hx + 7.4, hy + 5, 4, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 1, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 3, hy - 4 - jaw), (hx + 11, hy - 4 - jaw), 'mouth1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 13 + k * 3, 40), hy + k * 3 - 4, 1.6, 2.6, 'ribbon2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def balloonbeetle(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('balloonbeetle', clip, n, sy=1 - fall * .5)
    a.pk = .9
    hop = (math.sin(n * math.pi / 4 + .4) * .5 + .5) * 5 if clip == 'walk' else (bob * .6 if clip == 'idle' else 0)
    a.lift = hop
    cy = 24 - fall * 6
    # six stubby legs
    for k, lx in enumerate((-14, -5, 4, 13)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.5)) * 3 if clip == 'walk' else 0
        a.c((lx, cy - 2), (lx + (-3 if lx < 0 else 3), 3 + up), 3, 2, 'leg')
    # two balloons tethered to the shell, bobbing
    for k, (bx, grp) in enumerate(((-12, 'balloon'), (10, 'balloon2'))):
        sway2 = math.sin(n * math.pi / 3 + k * 2) * 2 if clip == 'idle' else sw * 2 * (1 if k else -1)
        top = (bx + sway2 * 1.4 - wind * 2 * (1 if k else -1), 62 + k * 4 + bob * .4 - fall * 28)
        a.line((bx * .5, cy + 14), (top[0], top[1] - 8), 'string', 1)
        a.e(top[0], top[1], 10.6, 12.2, grp)
        a.dot(top[0] - 4, top[1] + 4, 'string', 2)
    # round shell with stripes and a head peeking out front
    a.e(-4, cy + 6, 21, 17, 'shell')
    a.e(-10, cy + 13, 11, 5, 'shell', out=False)
    a.line((-4, cy - 10), (-4, cy + 22), 'stripe0', 2)
    a.e(-4, cy + 6, 3.4, 15, 'stripe', out=False)
    hx, hy = 19 + strike * 7 - wind * 3, cy + 2
    a.e(hx, hy, 10.6, 9.6, 'shell')
    a.e(hx - 3, hy + 4, 5.6, 3, 'shell', out=False)
    a.eye(hx - 1.6, hy + 2, 4.4, iris='iris', look=(.7, .1))
    a.eye(hx + 7.6, hy + 1.4, 3.4, iris='iris', look=(.9, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    for s in (0, 1):
        tip = (hx + 2 + s * 5 + sw, hy + 17 + s)
        a.c((hx + 1 + s * 4, hy + 8), tip, 1.1, .9, 'leg')
        a.e(tip[0], tip[1], 2, 2, 'stripe')
    jaw = max(wind * .5, strike) * 2
    a.line((hx + 2, hy - 5 - jaw), (hx + 8, hy - 5 - jaw), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 12 + k * 3, 40), hy - 2 + k * 4 - 4, 2.2, 'stripe2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def paintedmacaw(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('paintedmacaw', clip, n, sy=1 - fall * .5)
    a.ox = -4
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-4, -9, -14, 8, 10, 4, 1, 0)[n]
    cy = 38 + b - fall * 10
    # long tail feathers sweeping down-left
    for k, (grp, off) in enumerate((('blue', 0), ('red', 3), ('yellow', -3))):
        a.c((-6, cy - 4), (-20 - off + sw * 1.5 + k, 8 + k * 2), 4.4, 1.8, grp)
    # legs and talons
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 5 - 2, cy - 12), (s * 5 - 1, 5 + up), 2, 1.6, 'leg')
        a.e(s * 5 + 2, 3 + up, 4.4, 1.8, 'leg')
    # round body with a yellow-green breast
    a.e(0, cy, 14.6, 17, 'red')
    a.e(5, cy - 4, 8, 11, 'yellow')
    a.e(-6, cy + 8, 7, 4, 'red', out=False)
    # wing: a big painted fan that flaps
    a.e(-10, cy + 2 + flap * .8, 9, 15, 'blue', ang=.25 - flap * .03)
    a.e(-10, cy + 4 + flap * .8, 5, 9, 'blue', ang=.25 - flap * .03, out=False)
    a.e(-12, cy - 2 + flap * .6, 5, 8, 'green', ang=.25 - flap * .03, out=False)
    # head with white face patch, hooked beak and a bright crest
    hx, hy = 7 + strike * 5 - wind * 3, cy + 21 + wind * 2 - strike * 5
    for k, (dx, ln) in enumerate(((-3, 8), (0, 10), (3, 7))):
        a.c((hx + dx - 3, hy + 7), (hx + dx - 7 - k * 2 + sw, hy + 7 + ln), 2.2, 1.2, ('red', 'yellow', 'blue')[k])
    a.e(hx, hy, 12, 11, 'red')
    a.e(hx - 4, hy + 5, 6, 3, 'red', out=False)
    a.e(hx + 3, hy - 1, 7, 6.4, 'face')
    a.poly([(hx + 6, hy + 5), (hx + 18, hy + 3), (hx + 19, hy - 5), (hx + 14, hy - 10), (hx + 9, hy - 4)], 'beak1')
    a.poly([(hx + 7, hy - 2), (hx + 15, hy - 5), (hx + 11, hy - 11), (hx + 6, hy - 6)], 'beak2' if 'beak2' in a.p.names else 'beak1')
    a.eye(hx + 1.4, hy + 1.6, 4.2, iris='iris', look=(.8, .1))
    a.dot(hx - 5, hy - 3, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(min(hx + 20 + k * 2, 40), hy - 6 + k * 3, 'yellow1', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def jesterling(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('jesterling', clip, n, sy=1 - fall * .5)
    a.pk = .96
    hop = abs(math.sin(n * math.pi / 4 + .3)) * 3 if clip == 'walk' else (bob * .5 if clip == 'idle' else 0)
    a.lift = hop
    # curly boots
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 6, 24), (s * 7, 6 + up), 3.6, 3, 'teal' if s < 0 else 'pink')
        a.e(s * 9 + 2, 4 + up, 7, 3.8, 'boot')
        a.e(s * 15 + 3, 6 + up, 2.2, 2.2, 'bell')
    # harlequin tunic: pink and teal halves with a diamond band
    a.band([(-11, 38), (11, 38), (15, 24), (-15, 24)], 'pink')
    a.band([(0, 38), (11, 38), (15, 24), (0, 24)], 'teal', out=False)
    a.e(0, 42, 13, 9, 'pink')
    a.e(7, 42, 6.6, 9, 'teal', out=False)
    for k in range(3):
        diamond(a, -9 + k * 9, 30, 3.4, 4.4, 'gold1')
    # arms juggling balls: one up, one holding
    t = n * .9
    for k in range(3):
        ph = t + k * 2.1
        bx = math.cos(ph) * 17
        by = 62 + abs(math.sin(ph)) * 12 + wind * 6
        if clip == 'attack' and k == 0:
            bx, by = lerp(lerp(-14, -18, wind), 30, strike), lerp(lerp(60, 78, wind), 42, strike)
        if clip == 'die':
            bx, by = -20 + k * 20, lerp(by, 6 + k * 2, fall)
        a.e(bx, by, 3.8, 3.8, 'ball')
        a.dot(bx - 1.4, by + 1.4, 'shine', 1)
    a.c((-9, 44), (-18, 52 + sw), 3, 2.6, 'teal')
    a.e(-19, 53 + sw, 3, 3, 'skin')
    a.c((9, 44), (18, 52 - sw), 3, 2.6, 'pink')
    a.e(19, 53 - sw, 3, 3, 'skin')
    # head with a two-point bell cap and a big grin
    hx, hy = 1 + strike * 2, 56
    a.e(hx, hy, 12.4, 11, 'skin')
    a.e(hx - 4, hy + 5, 6.6, 3.2, 'skin', out=False)
    for s, grp in ((-1, 'teal'), (1, 'pink')):
        base = (hx + s * 5, hy + 9)
        tip = (hx + s * 18 + sw * s * 2, hy + 8 + 4 - wind * 3)
        a.c(base, (hx + s * 12, hy + 14), 4.6, 3.4, grp)
        a.c((hx + s * 12, hy + 14), tip, 3.4, 2, grp)
        a.e(tip[0], tip[1] - 1, 2.6, 2.6, 'bell')
    a.e(hx, hy + 9, 11, 3.2, 'gold')
    a.eye(hx - 3.6, hy - 1, 4.2, iris='iris', look=(.4, .1))
    a.eye(hx + 5.4, hy - 1, 3.8, iris='iris', look=(.8, .1))
    a.dot(hx - 8, hy - 4, 'blush', 2)
    a.dot(hx + 9.6, hy - 4, 'blush', 2)
    a.e(hx + 1.4, hy - 6.4 - max(wind * .4, strike) * 1.4, 4.2, 2 + max(wind * .4, strike) * 1.4, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(36 + k * 0, 38), 50 + k * 6 - 6, 2.4, 'gold1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def paradegryphon(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('paradegryphon', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .92
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 5 if clip == 'idle' else (math.sin(n * math.pi / 2) * 4 if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-4, -10, -16, 8, 12, 6, 2, 0)[n]
    cy = 30 + b - fall * 10
    # hind legs (lion) and tail with a plume
    for k, lx in enumerate((-20, -12)):
        up = max(0, math.sin(n * math.pi / 2 + k * 2)) * 4 if clip == 'walk' else 0
        a.c((lx, cy - 3), (lx, 4 + up), 6.4, 4.4, 'body')
        a.e(lx + 1, 3 + up, 5.4, 2.8, 'body')
    a.c((-24, cy + 4), (-30, cy + 11 + sw * 2), 2.6, 2, 'body')
    a.e(-32, cy + 13 + sw * 2, 4.6, 6.6, 'plume', ang=.5)
    # lion body
    a.e(-8, cy + 2, 22, 13.6, 'body')
    a.e(-12, cy - 6, 14, 5, 'body', out=False)
    # big rainbow wing raised over the back
    for k, (grp, dx) in enumerate((('wing', 0), ('feather', 8), ('plume', 15))):
        tip = (-30 + dx + k * 3, cy + 30 + flap - k * 3)
        a.band([(-6 + k, cy + 10), (-2 + k * 4, cy + 14), tip, (-20 + dx * .3, cy + 16 + k * 1)], grp)
    # front legs (eagle), the near one raised for the strike
    far = (6, 5)
    a.c((4, cy - 2), far, 5.4, 4, 'claw')
    a.c((8, cy), (11, 5), 5.6, 4.2, 'body')
    hand = (lerp(lerp(14, 11, wind), 25, strike), lerp(lerp(8, 24, wind), 6, strike))
    if clip == 'die':
        hand = (lerp(14, 22, fall), lerp(8, 4, fall))
    a.c((10, cy + 2), hand, 6, 4.4, 'body')
    for k in range(3):
        a.c((hand[0] + 1, hand[1]), (hand[0] + 6, hand[1] - 2 + k * 1.6 - 2), 1.6, .9, 'claw')
    # eagle head with a crest of ribbon plumes
    hx, hy = 15 + strike * 4 - wind * 3, cy + 22 - strike * 3
    a.c((6, cy + 8), (hx - 2, hy - 3), 7, 6, 'feather')
    for k, (dx, ln) in enumerate(((-6, 10), (-1, 13), (4, 9))):
        a.c((hx + dx, hy + 6), (hx + dx - 4 + sw + k * 2, hy + 6 + ln), 2.4, 1.2, ('plume', 'ribbon', 'wing')[k])
    a.e(hx, hy, 12.4, 11, 'feather')
    a.e(hx - 4, hy + 5, 6.4, 3.2, 'feather', out=False)
    jaw = max(wind * .5, strike) * 3
    a.poly([(hx + 6, hy + 1), (hx + 19, hy - 4 - jaw * .4), (hx + 6, hy - 5 - jaw)], 'beak1')
    a.line((hx + 7, hy - 2), (hx + 16, hy - 4), 'beak0', 1)
    a.eye(hx - 0.4, hy + 2, 4.6, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(hx + 20 + k * 2, 38), hy - 6 + (k * 5) % 12, 2.2, 'ribbon1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def maskcolossus(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('maskcolossus', clip, n, sy=1 - fall * .5)
    a.pk = .84
    b = bob * .7
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 10, 22), (s * 11, 5 + up), 6.4, 5.4, 'robe')
        a.e(s * 12, 3.6 + up, 8.4, 4, 'robe')
    # robe body with stage-curtain stripes and a gold sash
    a.band([(-16, 22), (16, 22), (22, 44 + b), (-22, 44 + b)], 'robe')
    for k in range(4):
        a.line((-12 + k * 8, 24), (-14 + k * 9.4, 42 + b), 'robe0', 1)
    a.e(0, 44 + b, 23, 9, 'robe')
    a.line((-20, 36 + b), (20, 28 + b), 'gold1', 3)
    # a ruff collar
    for k in range(9):
        ang = k * math.pi / 8
        a.e(-20 + k * 5, 48 + b + math.sin(ang) * 3, 4.6, 3.4, 'ruff')
    # floating fists on both sides, the near one punches
    far = (-31, 46 + b + sw * 2)
    a.e(far[0], far[1], 7.4, 7, 'fist')
    a.e(far[0] - 3, far[1] + 3, 3.4, 2, 'fist', out=False)
    fist = (lerp(lerp(28, 26, wind), 34, strike), lerp(lerp(46, 60, wind), 44, strike) + b)
    if clip == 'die':
        fist = (lerp(30, 34, fall), lerp(46, 8, fall))
    a.e(fist[0], fist[1], 8.4, 8, 'fist')
    a.e(fist[0] - 3, fist[1] + 3, 4, 2.4, 'fist', out=False)
    for k in range(3):
        a.dot(fist[0] + 4, fist[1] - 3 + k * 3, 'fist0', 1)
    # the great mask: a big pale oval, rosy cheeks, gold brow, eyes and a wide smile
    hx, hy = 0 + strike * 2, 65 + b
    a.e(hx, hy, 19, 21, 'mask')
    a.e(hx - 7, hy + 9, 9, 4.6, 'mask', out=False)
    a.e(hx, hy + 19, 11, 3.2, 'gold')
    for k in range(5):
        diamond(a, hx - 12 + k * 6, hy + 19 + (k % 2), 2.4, 3.6, 'gold1' if k % 2 else 'gold2')
    a.eye(hx - 7, hy + 3, 5.4, iris='iris', look=(.3, .1))
    a.eye(hx + 8, hy + 3, 5, iris='iris', look=(.8, .1))
    a.dot(hx - 14, hy - 4, 'rose1', 4)
    a.dot(hx + 12, hy - 4, 'rose1', 4)
    smile = max(wind * .4, strike) * 3
    a.e(hx + 1, hy - 10, 8.4, 3.6 + smile, 'mouth')
    a.line((hx - 6, hy - 9), (hx - 10, hy - 6), 'ink', 1)
    a.line((hx + 8, hy - 9), (hx + 12, hy - 6), 'ink', 1)
    # tiara of tassels
    for k, dx in enumerate((-9, 0, 9)):
        a.c((hx + dx, hy + 19), (hx + dx + sw * (k - 1), hy + 27 - (k % 2) * 3), 1.6, 1, 'gold')
        a.e(hx + dx + sw * (k - 1), hy + 28 - (k % 2) * 3, 2.4, 2.4, 'rose')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(fist[0] + 6 + k * 2, 40), fist[1] - 6 + k * 5, 2.4, 'gold1')
    return a.done()


DRAW = dict(ribbongecko=ribbongecko, balloonbeetle=balloonbeetle, paintedmacaw=paintedmacaw, jesterling=jesterling,
            paradegryphon=paradegryphon, maskcolossus=maskcolossus)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/ribbonwild-preview')
    print('ok')
