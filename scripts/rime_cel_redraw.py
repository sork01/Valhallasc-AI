"""Cel-shaded Rimeveil Glacier enemies (zone 2) for make_rime_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi
proportions. 96x96 frame, foot anchor (48,90), five clips. Kind IDs and clip layout are unchanged.
`python3 scripts/rime_cel_redraw.py [kind...]` writes contact sheets to test-results/rime-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, claw, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('crab', 'wolf', 'yeti', 'wyrm')

PALETTES = {
    'crab': mk(shell=('#245e92', '#4aa2d4', '#8ddcf2', '#d6f6ff'), leg=('#1f4a72', '#3a7cae', '#72b8de'),
               ice=('#4a7ab8', '#9cd0f4', '#e2f6ff', '#f4fdff'), iris='#1e3a9a', blush='#ff9fb4', frost='#f2fcff'),
    'wolf': mk(fur=('#566c8e', '#94aecd', '#d6e4f4', '#fafdff'), belly=('#b8c8dc', '#e6eef8', '#fdfeff'),
               ice=('#3f6aa8', '#8cc8f0', '#d8f2ff', '#f4fdff'), iris='#2aa8e6', blush='#ff9fb8',
               mouth=('#5a1c34', '#ff7a98'), fang=('#e0e8f2', '#ffffff')),
    'yeti': mk(fur=('#7a96b6', '#b8cfe6', '#e8f2fb', '#fdfeff'), face=('#3a6ea4', '#6cb0e0', '#a8dcf6'),
               ice=('#3f6aa8', '#8cc8f0', '#d8f2ff', '#f4fdff'), iris='#1a4a9a', blush='#ff9fb8',
               tusk=('#c8d4de', '#fafcff'), mouth=('#4a1830', '#c8486e')),
    'wyrm': mk(scale=('#1a4c86', '#2f86c8', '#6ccaf0', '#c4f2ff'), belly=('#8cc2e0', '#d0ecf8', '#f6fdff'),
               ice=('#3f6aa8', '#8cc8f0', '#d8f2ff', '#f4fdff'), iris='#e0407e', blush='#ff9fc8',
               mouth=('#5a1c3c', '#ff6f98'), frost=('#bff2ff', '#eafbff')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def crab(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob = T['fall'], T['wind'], T['strike'], T['bob']
    a = Art('crab', clip, n)
    by = 16 - fall * 7 + bob
    for i, (bx, dx) in enumerate(((-17, -9), (-9, -7), (5, 8), (13, 11))):
        up = max(0, math.sin(n * math.pi / 2 + i * math.pi / 2)) * 7 if clip == 'walk' else 0
        hip = (bx, by - 3)
        knee = (bx + dx * 1.5, by - 2 + fall * 8)
        foot = (bx + dx * 1.9 * (1 - fall * .5), up + fall * (by + 8))
        a.c(hip, knee, 3.2, 2.7, 'leg')
        a.c(knee, foot, 2.7, 1.6, 'leg')

    def pose(rest, w, s):
        pw = [lerp(rest[0][k], w[0][k], wind) for k in (0, 1)]
        ang = lerp(rest[1], w[1], wind)
        op = lerp(rest[2], w[2], wind)
        pw = [lerp(pw[k], s[0][k], strike) for k in (0, 1)]
        return tuple(pw), lerp(ang, s[1], strike), lerp(op, s[2], strike)
    idle_open = .3 + (.25 if clip == 'idle' and n in (2, 3) else 0)
    wr, an, op = pose(((17, 31), .55, idle_open), ((12, 46), 1.3, 1.), ((24, 8), -.25, 0.))
    if clip == 'die':
        wr, an, op = (17 - fall * 6, 31 - fall * 18), .55 - fall * 1.5, .6
    claw(a, wr, an, op, 6.3, 'shell', arm_from=(8, by + 2), arm_group='leg')
    # domed shell with frost crystals
    a.e(0, by, 23, 13.5, 'shell')
    a.e(-2, by + 4, 17, 8, 'shell', out=False)
    for k, (x, h, tl) in enumerate(((-14, 10, -3), (-7, 15, -1), (0, 12, 1))):
        crystal(a, x, by + 9 - k * .5, 3.4, h * (1 - fall * .5), 'ice', tilt=tl)
    for k in range(4):
        a.dot(-16 + k * 6, by + 3 + (k % 2) * 2, 'frost', 2)
    # eyes on stalks
    a.c((11, by + 8), (14, by + 19), 2.3, 2.1, 'shell')
    a.c((18, by + 6), (22, by + 17), 2.3, 2.1, 'shell')
    a.eye(14.5, by + 22, 4.1, iris='iris')
    a.eye(23, by + 20, 3.6, iris='iris')
    a.dot(20, by + 3, 'blush', 2)
    wr, an, op = pose(((27, 15), .1, idle_open), ((26, 38), 1.3, 1.), ((26, 8), -.2, 0.))
    if clip == 'die':
        wr, an, op = (27 - fall * 10, 15 - fall * 5), .1 + fall * 1.2, .8
    claw(a, wr, an, op, 7.4, 'shell', arm_from=(14, by - 2), arm_group='leg')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(25 + k * 2.6, 36), 5 + (k % 2) * 4 + n - 3, 2.2, 'frost')
    return a.done()


# ------------------------------------------------------------------------------------------------
def wolf(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('wolf', clip, n, sy=1 - fall * .45)
    b = bob * .6 - fall * 5
    by = 25 + b
    lean = strike * 3 - wind * 5
    # bushy tail with a frosted tip
    tail = (-31, by + 8 + math.sin(n * 1.3) * 2 + wind * 5)
    a.c((-19, by + 1), tail, 5, 3, 'fur')
    a.e(tail[0] - 2, tail[1] + 2, 5, 4, 'ice')
    for lx, ph in ((-15, 1.6), (9, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 6 if clip == 'walk' else 0
        a.c((lx + 3, by - 4), (lx + 5 + up * .3, up), 4.4, 3.2, 'fur')
        a.e(lx + 7 + up * .3, up + 1, 4.8, 2.2, 'belly')
    # icy spine ridge, body, ruff
    for k in range(5):
        crystal(a, -17 + k * 7, by + 10 - abs(k - 2) * .6, 2.6, 7 + (k % 2) * 3, 'ice', tilt=-1)
    a.e(-6, by, 20, 12.6, 'fur')
    a.e(-3, by - 7, 14, 5, 'belly', out=False)
    a.e(12, by + 3, 11.5, 11, 'fur')
    for lx, ph in ((-12, 0), (11, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 6 if clip == 'walk' else 0
        a.c((lx, by - 4), (lx + 2 + up * .3, up), 5, 3.6, 'fur')
        a.e(lx + 4 + up * .3, up + 1, 5.2, 2.4, 'belly')
    hx, hy = 21 + lean, by + 11
    if clip == 'die':
        hx, hy = lerp(21, 25, fall), lerp(by + 11, 10, fall)
    jaw = max(wind * .5, strike) * 5.5
    a.e(hx + 9, hy - 6 - jaw, 7.6, 3.2, 'belly')
    if jaw > 1:
        a.e(hx + 10, hy - 4 - jaw / 2, 6, jaw / 2 + 1, 'mouth')
        a.poly([(hx + 5, hy - 5 - jaw), (hx + 7, hy - 5 - jaw + 4), (hx + 9, hy - 5 - jaw)], 'fang1', out=False)
    a.e(hx, hy, 12.4, 10.6, 'fur')
    a.e(hx + 10, hy - 2.6, 9, 5.2, 'belly')
    a.e(hx + 6, hy - 1, 8, 4.6, 'fur', out=False)
    a.dot(hx + 17, hy - 1.4, 'ink', 2)
    for (ex, eh, tilt) in ((-6, 14, -2), (1, 16, 3)):
        a.poly([(hx + ex - 4.4, hy + 7), (hx + ex + tilt, hy + 7 + eh), (hx + ex + 5.4, hy + 7)], 'fur1')
        a.poly([(hx + ex - 1.6, hy + 8), (hx + ex + tilt * .5, hy + 5 + eh), (hx + ex + 2.6, hy + 8)], 'ice1', out=False)
    a.eye(hx + 2.4, hy + 2.4, 4.6, iris='iris')
    a.eye(hx + 10.5, hy + 2, 3.2, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(hx + 20 + k * 4, 38), hy - 3 + (k % 2) * 5, 2.4, 'ice2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def yeti(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('yeti', clip, n, sy=1 - fall * .5)
    b = bob * .8
    for s in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if s < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.c((s * 11, 18), (s * 11 + fall * s * 4, 6 + up), 8 * (1 - fall * .5), 8.4 * (1 - fall * .55), 'fur')
        a.e(s * 11 + fall * s * 5, 4 + up, 10.6, 4.8, 'fur')
        for k in range(3):
            a.dot(s * 11 - 4 + k * 4, 3 + up, 'ice1', 2)
    a.c((-19, 40 + b), (-29 - fall * 3, 25 - fall * 14), 8, 7.4, 'fur')
    a.e(-30 - fall * 3, 21 - fall * 12, 9.8, 9, 'fur')
    a.e(0, 33 + b - fall * 8, 24, 20, 'fur')
    a.e(0, 29 + b - fall * 8, 13, 11, 'belly') if False else None
    a.e(-8, 42 + b - fall * 8, 11, 6, 'fur', out=False)
    for k in range(5):                                      # shaggy fur fringe over the belt line
        a.poly([(-18 + k * 8.4, 19), (-14 + k * 8.4, 10 + (k % 2) * 3), (-10 + k * 8.4, 19)], 'fur1')
    for s in (-1, 1):
        a.e(s * 18, 47 + b - fall * 9, 9, 7.6, 'fur')
        crystal(a, s * 18, 51 + b - fall * 9, 3, 9, 'ice', tilt=s * 2)
    hx = lerp(0, -9, fall)
    hy = lerp(58 + b, 13, fall)
    crystal(a, hx - 7, hy + 9, 3.2, 12, 'ice', tilt=-3)
    crystal(a, hx + 6, hy + 9, 3, 10, 'ice', tilt=3)
    a.e(hx, hy, 14, 12.6, 'fur')
    a.e(hx + 1, hy - 2, 10.4, 8.6, 'face')
    a.e(hx - 2, hy + 2, 6, 3, 'face', out=False)
    state = T['state']
    a.eye(hx - 3.6, hy + 1, 4.4, iris='iris')
    a.eye(hx + 6.2, hy + 1, 4.2, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 3, 'blush', 3)
    a.dot(hx + 11, hy - 3, 'blush', 2)
    mouth = max(wind * .6, strike) * 3
    a.e(hx + 1.4, hy - 6.2 - mouth * .5, 3.4, 1.6 + mouth, 'mouth')
    for s in (-1, 1):
        a.poly([(hx + 1.4 + s * 3.6 - 1.2, hy - 5), (hx + 1.4 + s * 3.6, hy - 11 - mouth), (hx + 1.4 + s * 3.6 + 1.2, hy - 5)], 'tusk1')
    fist = (lerp(lerp(30, 26, wind), 33, strike), lerp(lerp(25, 75, wind), 9, strike))
    if clip == 'die':
        fist = (lerp(30, 27, fall), lerp(25, 8, fall))
    a.c((19, 41 + b - fall * 8), fist, 8, 7.4, 'fur')
    a.e(fist[0], fist[1], 11, 10, 'fur')
    for k in range(3):
        a.line((fist[0] + 2 + k * 2.6, fist[1] - 4), (fist[0] + 3 + k * 2.6, fist[1] - 9), 'ice1', 1)
    if clip == 'attack' and n in (4, 5):
        for k in range(5):
            star(a, min(33 + k * 1.6, 36), 4 + (k * 7) % 10 + (n - 4) * 3, 2.2, 'ice2')
    if clip == 'die':
        for k in range(5):
            a.e(-22 + k * 11, 5 + (k % 2) * 2, 4 - k % 2, 3, 'fur' if k % 2 else 'ice')
    return a.done()


# ------------------------------------------------------------------------------------------------
def wyrm(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('wyrm', clip, n, sy=1 - fall * .35)
    b = bob * .6
    k = 1 - fall * .55
    # tail tip out of the bottom coil
    a.c((18, 9 * k), (36 - fall * 8, 4 + math.sin(n * 1.1) * 1.4), 6, 1.6, 'scale')
    crystal(a, 36 - fall * 8, 4, 2.4, 6, 'ice', tilt=2)
    # three stacked coils with pale belly bands and ice spines
    for i, (dx, y, rx, ry) in enumerate(((0, 9, 28, 10), (2, 20, 24, 9), (-1, 31, 19, 8))):
        a.e(dx, y * k, rx, ry * (1 - fall * .2), 'scale')
        a.e(dx + 3, y * k - ry * .45, rx * .72, ry * .36, 'belly', out=False)
        for j in range(4):
            crystal(a, dx - rx * .75 + j * 4.4, y * k + ry * .75 - j * .7, 2.4, 5 + (j % 2) * 3 - fall * 3, 'ice', tilt=-1)
    # neck and head
    wave = math.sin(n * math.pi / 3) * 1.3 if clip == 'idle' else sw * 1.8
    hx = lerp(lerp(2, -6, wind), 17, strike) + wave
    hy = lerp(lerp(62 + b, 62, wind), 52, strike)
    if clip == 'die':
        hx, hy = lerp(2, 14, fall), lerp(62, 20, fall)
    a.c((-1, 36 * k), (hx - 2, hy - 8), 8, 7, 'scale')
    a.c((0, 40 * k), (hx - 2, hy - 8), 5, 5, 'belly', out=False)
    # frill of ice behind the head
    for j, (dx, h, tl) in enumerate(((-12, 11, -5), (-7, 15, -2), (-2, 17, 0), (3, 14, 2))):
        crystal(a, hx + dx, hy + 6 + (3 - abs(dx + 5)) * .2, 3, h * (1 - fall * .5), 'ice', tilt=tl)
    jaw = max(wind * .5, strike) * 6
    a.e(hx + 7, hy - 6 - jaw, 8, 3.2, 'belly')
    if jaw > 1.5:
        a.e(hx + 8, hy - 4 - jaw / 2, 6.4, jaw / 2 + 1.2, 'mouth')
    a.e(hx, hy, 13.4, 11, 'scale')
    a.e(hx + 9, hy - 3, 8.4, 5.4, 'scale')
    a.e(hx + 4, hy - 5, 10, 3.6, 'belly', out=False)
    a.dot(hx + 15.6, hy - 2.2, 'ink', 2)
    a.eye(hx + 2.4, hy + 1.8, 4.7, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for j in range(4):
            diamond(a, min(hx + 18 + j * 4 + (n - 3) * 2, 38), hy - 4 - jaw / 2 + (j % 2) * 5, 2.4, 3.8, 'frost1' if j % 2 else 'frost0')
    return a.done()


DRAW = dict(crab=crab, wolf=wolf, yeti=yeti, wyrm=wyrm)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/rime-cel-preview')
    print('ok')
