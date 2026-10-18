"""Cel-shaded Gloamfen enemies (zone 3) for make_fen_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi
proportions. 96x96 frame, foot anchor (48,90), five clips. Kind IDs and clip layout are unchanged.
`python3 scripts/fen_cel_redraw.py [kind...]` writes contact sheets to test-results/fen-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('toad', 'croc', 'knight', 'hydra', 'gloomroot')

PALETTES = {
    'toad': mk(skin=('#2a5a1a', '#4f9a2a', '#8ed44a', '#d0f88a'), belly=('#b8b050', '#ecdf86', '#fff6c0'),
               wart=('#7a5a2a', '#b88a46'), iris='#e8a31a', blush='#ff8a98', mouth=('#5a1c34', '#ff6f8c'),
               tongue=('#c8386a', '#ff7a98')),
    'croc': mk(scale=('#1f3a1a', '#3f7a2a', '#7ab844', '#c4ec78'), belly=('#a8b058', '#e0e48c', '#fbffc4'),
               iris='#f0b41e', blush='#ff8a98', mouth=('#5a1c34', '#ff6f8c'), tooth=('#d8d4c0', '#fffdf0'),
               mud=('#4a3a24', '#7a6238')),
    'knight': mk(plate=('#1f3c3a', '#3f726a', '#7ab8a4', '#c8f0dc'), kelp=('#1a4a22', '#2f8a3a', '#6cc85a'),
                 bone=('#a8b4a0', '#e4ecd6'), cloth=('#24304e', '#3f5588', '#6a86c0'), glow=('#b8fff0', '#5af0d0'),
                 iris='#20d8b8', rust=('#6a3a20', '#a8643a'), blade=('#6a8a8a', '#b4d0cc', '#f0fffb'),
                 barn=('#c8c0a8', '#f4f0e0')),
    'hydra': mk(body=('#16404a', '#2a7480', '#52b4ba', '#9ae6e2'), head=('#1f3a24', '#3f7a3e', '#78b860', '#c0ec8c'),
                frill=('#4a1c6a', '#8a3ab8', '#c470f0'), belly=('#a8c488', '#e0f0b4', '#fbffd8'),
                iris='#f0b41e', blush='#ff8a98', mouth=('#5a1c34', '#ff6f8c'), tooth=('#d8d4c0', '#fffdf0')),
    'gloomroot': mk(bark=('#24180e', '#4a3220', '#7a5634', '#b08454'), moss=('#1a3a1a', '#3a7a2e', '#78b844', '#c4ee78'),
                    heart=('#0e5a4a', '#2ac8a0', '#9affdc', '#e8fff6'), cap=('#5a1c3c', '#a83a64', '#e0709a'),
                    iris='#ffd23a', spot='#fff0d4', root=('#1a1008', '#3a2616')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def toad(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('toad', clip, n, sy=1 - fall * .45)
    hop = max(0, math.sin(n * math.pi / 4)) * 9 if clip == 'walk' else 0
    a.lift = hop
    sq = 1 - wind * .12 + strike * .06
    by = 16 + bob * .6 - fall * 4
    # hind legs folded, front legs propping the body
    a.e(-17, by - 5, 9, 8, 'skin')
    a.e(-20, by - 11, 10, 3.6, 'skin', out=False)
    a.e(-22, 3, 9, 3.4, 'skin')
    a.c((14, by - 3), (18, 4), 3.8, 3.2, 'skin')
    a.e(21, 3, 6.4, 2.8, 'skin')
    # fat body with a pale belly and warts
    a.e(-2, by, 24, 15 * sq, 'skin')
    a.e(3, by - 8, 14, 6.5, 'belly', out=False)
    for (wx, wy) in ((-12, 8), (-4, 11), (-17, 0), (6, 10), (-8, 3)):
        a.e(wx, by + wy, 2.2, 1.8, 'wart')
    # head: wide mouth, huge eyes bulging on top
    hx, hy = 14, by + 3
    gape = max(wind * .5, strike) * 5
    a.e(hx + 3, hy - 5 - gape, 15, 4.6, 'belly')
    if gape > 1.5:
        a.e(hx + 5, hy - 3 - gape / 2, 11, gape / 2 + 1.4, 'mouth')
        if strike > .3:
            a.c((hx + 8, hy - 4), (min(hx + 8 + strike * 20, 38), hy - 3 - gape / 2), 3, 3.4, 'tongue')
    a.e(hx + 2, hy, 17, 11, 'skin')
    a.e(hx + 5, hy - 5, 11, 3.6, 'belly', out=False)
    a.dot(hx + 13, hy - 1, 'ink', 2)
    a.e(hx - 5, hy + 10, 7.6, 7.6, 'skin')
    a.e(hx + 8, hy + 10, 7, 7, 'skin')
    a.eye(hx - 5, hy + 11, 5.4, iris='iris', look=(.5, .1))
    a.eye(hx + 8.5, hy + 11, 4.9, iris='iris', look=(.9, .1))
    a.dot(hx - 3, hy - 3, 'blush', 3)
    if clip == 'die':
        for k in range(4):
            star(a, -20 + k * 14, max(3, 24 - fall * 20), 2, 'belly1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def croc(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('croc', clip, n, sy=1 - fall * .35)
    by = 14 + bob * .5 - fall * 3
    swing = math.sin(n * math.pi / 3) * 2.4 if clip == 'idle' else sw * 3 + wind * -3 + strike * 3
    # tail in three tapering segments
    p0 = (-14, by + 1)
    p1 = (-26, by + 1 + swing * .4)
    p2 = (-37, by + 3 + swing)
    a.c(p0, p1, 8.2, 6, 'scale')
    a.c(p1, p2, 6, 2.2, 'scale')
    for k in range(5):
        a.poly([(-16 - k * 5.4, by + 7 - k * .5), (-13.5 - k * 5.4, by + 12 - k * .5), (-11 - k * 5.4, by + 7 - k * .5)], 'scale2', out=True)
    # legs, four stubby
    for lx, ph in ((-18, 1.6), (6, 0), (-8, 0), (14, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 3 if clip == 'walk' else 0
        a.c((lx, by - 2), (lx + 2, up + 3.4), 4.6, 3.6, 'scale')
        a.e(lx + 4, up + 3, 5.4, 2.4, 'scale')
    a.e(-4, by + 2, 22, 10.2, 'scale')
    a.e(-1, by - 5, 17, 4.6, 'belly', out=False)
    for k in range(6):
        a.poly([(-20 + k * 7, by + 9), (-17 + k * 7, by + 15), (-14 + k * 7, by + 9)], 'scale2')
    # head: long snout, big eye, teeth
    hx, hy = 19 + strike * 4 - wind * 3, by + 6
    gape = max(wind * .5, strike) * 7
    a.e(hx + 7, hy - 5 - gape, 15, 4, 'belly')
    for k in range(4):
        a.poly([(hx + 1 + k * 4.4, hy - 4 - gape), (hx + 2.6 + k * 4.4, hy - 1 - gape + 1.5), (hx + 4 + k * 4.4, hy - 4 - gape)], 'tooth1', out=False)
    if gape > 1.5:
        a.e(hx + 8, hy - 3 - gape / 2, 12, gape / 2 + 1.2, 'mouth')
    a.e(hx, hy, 12.4, 9.4, 'scale')
    a.e(hx + 10, hy - 1.2, 11.4, 5.4, 'scale')
    a.e(hx + 6, hy - 3, 9, 3.4, 'belly', out=False)
    a.dot(hx + 20, hy + 1, 'ink', 2)
    a.e(hx - 2, hy + 8, 6.2, 5.4, 'scale')
    a.eye(hx - 2, hy + 9.5, 5.2, iris='iris', look=(.7, .1))
    a.dot(hx + 3, hy - 3, 'blush', 3)
    for k in range(3):
        a.e(hx - 8 + k * 6, hy + 8.4 - k * .6, 1.6, 1.6, 'scale')
    return a.done()


# ------------------------------------------------------------------------------------------------
def knight(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('knight', clip, n, sy=1 - fall * .5)
    b = bob * .5
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 7, 22), (s * 7, 6 + up), 4.6, 4, 'plate')
        a.e(s * 7.5, 4 + up, 7, 4, 'plate')
        a.dot(s * 7 - 1, 14 + up, 'barn0', 2)
    # round shield on the far arm: weathered green bronze with a skull boss
    sx, sy_ = -24 + wind * -2, 36 + b
    a.e(sx, sy_, 11.4, 12.6, 'plate')
    a.e(sx, sy_, 8, 9, 'cloth', out=False)
    a.e(sx, sy_ + 1, 3.6, 3.6, 'bone')
    a.dot(sx - 1.4, sy_ + 2, 'ink', 1)
    a.dot(sx + 1.2, sy_ + 2, 'ink', 1)
    a.c((-12, 40 + b), (sx + 6, sy_ + 2), 3.6, 3.2, 'plate')
    a.band([(-11, 24), (11, 24), (14, 16), (-14, 16)], 'cloth')
    a.e(0, 34 + b, 13.4, 11.6, 'plate')
    a.e(-4, 39 + b, 7, 4, 'plate', out=False)
    for (x, y) in ((-6, 30), (5, 38), (-2, 35)):
        a.e(x, y + b, 2, 1.8, 'barn')
    a.line((-12, 27 + b), (12, 27 + b), 'rust0', 2)
    # sword arm
    hand = (lerp(lerp(19, 15, wind), 25, strike), lerp(lerp(33, 40, wind), 34, strike))
    ang = lerp(lerp(1.45, 1.9, wind), .15, strike)
    if clip == 'die':
        hand = (lerp(19, 24, fall), lerp(33, 8, fall))
        ang = lerp(1.45, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 6, hand[1] - dy * 6)
    tip = (min(hand[0] + dx * 30, 34), min(hand[1] + dy * 30, 74))
    a.line(base, tip, 'ink', 6)
    a.line(base, tip, 'blade1', 4)
    a.line((base[0] - dy * 1, base[1] + dx * 1), (tip[0] - dy * 1, tip[1] + dx * 1), 'blade2', 1)
    a.line((hand[0] - dy * 6, hand[1] + dx * 6), (hand[0] + dy * 6, hand[1] - dx * 6), 'rust1', 3)
    a.c((10, 41 + b), hand, 4, 3.6, 'plate')
    a.e(hand[0], hand[1], 3.8, 3.6, 'bone')
    for s in (-1, 1):
        a.e(s * 15, 42 + b, 7.6, 6.6, 'plate')
        a.e(s * 15 + s * 2, 45 + b, 2.4, 2.4, 'kelp')
    # helm: a kelp sprout, a dark visor and glowing eyes
    hx, hy = 1, 57 + b
    for k, (dx_, h, tl) in enumerate(((-3, 9, -4), (1, 13, 1), (5, 8, 5))):
        a.poly([(hx + dx_ - 2, hy + 10), (hx + dx_ + tl, hy + 10 + h), (hx + dx_ + 2, hy + 10)], 'kelp1')
    a.e(hx, hy, 13.6, 12, 'plate')
    a.e(hx - 4, hy + 6, 7.4, 4, 'plate', out=False)
    a.poly([(hx - 11, hy + 3), (hx + 12, hy + 3), (hx + 12, hy - 7), (hx - 11, hy - 7)], 'ink', out=False)
    state = T['state']
    for dx_ in (-4.8, 5.4):
        if state == 'dead':
            a.line((hx + dx_ - 2.4, hy - 1), (hx + dx_ + 2.4, hy - 5), 'glow1', 2)
            a.line((hx + dx_ - 2.4, hy - 5), (hx + dx_ + 2.4, hy - 1), 'glow1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx_, hy - 2), 3.8, 3.3 * a.sy)[0], 'glow0', outline=True)
            a.f.flat(ellipsoid(*a.g(hx + dx_ + .6, hy - 2.3), 2.1, 2.5 * a.sy)[0], 'iris')
            a.dot(hx + dx_ - 1.4, hy - .2, 'shine', 1)
    a.line((hx - 11, hy - 8), (hx + 12, hy - 8), 'rust0', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 5 + k * 4, 37), tip[1] - 4 + k * 4, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def hydra(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('hydra', clip, n, sy=1 - fall * .3)
    by = 15 + bob * .4 - fall * 3
    k = 1 - fall * .6
    # four stubby legs and a spiked turtle-like body
    for lx, ph in ((-20, 1.6), (-8, 0), (8, 1.6), (18, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 4 if clip == 'walk' else 0
        a.c((lx, by - 2), (lx + 1, up), 4.8, 3.8, 'body')
        a.e(lx + 3, up + 1, 5.4, 2.4, 'body')
    a.c((-24, by + 2), (-40, by - 1 + math.sin(n * 1.2) * 2), 6, 1.6, 'body')
    for j in range(5):
        a.poly([(-18 + j * 8, by + 11), (-14 + j * 8, by + 20 - (j % 2) * 3), (-10 + j * 8, by + 11)], 'frill1')
    a.e(-2, by + 1, 27, 13, 'body')
    a.e(2, by - 6, 18, 5, 'belly', out=False)

    def neck_head(root, hxy, r, open_, iris_dir=1., near=True):
        a.c(root, (hxy[0] - 2, hxy[1] - 7), 6.4, 5.4, 'head')
        a.e(hxy[0] + 7, hxy[1] - 5 - open_, 7.4, 2.8, 'belly')
        if open_ > 1.5:
            a.e(hxy[0] + 8, hxy[1] - 3 - open_ / 2, 5.6, open_ / 2 + 1.2, 'mouth')
        a.e(hxy[0], hxy[1], r, r * .86, 'head')
        a.e(hxy[0] + r * .62, hxy[1] - 2, r * .66, r * .4, 'head', out=False)
        a.poly([(hxy[0] - 5, hxy[1] + r * .6), (hxy[0] - 3, hxy[1] + r * .6 + 9), (hxy[0] + 2, hxy[1] + r * .6)], 'frill1')
        a.eye(hxy[0] + 2, hxy[1] + 1.4, r * .36, iris='iris')
        a.dot(hxy[0] - 4, hxy[1] - 3, 'blush', 2)
    wob = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else sw * 2
    far = (-17 + wob, 44 + bob - fall * 26)
    mid = (3 - wob, 52 + bob * .6 - fall * 36)
    # the middle head lunges on the attack
    mid = (lerp(lerp(mid[0], mid[0] - 8, wind), 22, strike), lerp(lerp(mid[1], mid[1] + 6, wind), 36, strike))
    near = (19 + wob * .6, 42 + bob * .8 - fall * 24)
    open_ = max(wind * .5, strike) * 5.5
    neck_head((-14, by + 8), far, 9, 0)
    neck_head((6, by + 10), mid, 11, open_)
    neck_head((14, by + 8), near, 9.4, 0)
    if clip == 'attack' and n in (3, 4, 5):
        for j in range(3):
            diamond(a, min(mid[0] + 18 + j * 4, 38), mid[1] - 3 + (j % 2) * 5, 2.2, 3.4, 'frill2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def gloomroot(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('gloomroot', clip, n, sy=1 - fall * .5)
    b = bob * .6
    # root feet
    for s in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if s < 0 else math.pi))) * 4 if clip == 'walk' else 0
        a.c((s * 9, 20), (s * 11, 6 + up), 8.2 * (1 - fall * .5), 7.6 * (1 - fall * .5), 'bark')
        for t in range(3):
            a.line((s * 11 + (t - 1) * 3, 4 + up), (s * 11 + (t - 1) * 8, 0 + up), 'root1', 2)
    # far branch arm
    a.c((-17, 42 + b), (-29 - fall * 2, 26 - fall * 12), 6.6, 5.6, 'bark')
    a.e(-30 - fall * 2, 22 - fall * 10, 8.6, 8, 'bark')
    # trunk body with a glowing heart gem and moss
    a.e(0, 33 + b - fall * 8, 22, 19.4, 'bark')
    a.e(-8, 42 + b - fall * 8, 10, 6, 'bark', out=False)
    for t in range(4):
        a.line((-12 + t * 8, 22 + b), (-10 + t * 8, 40 + b), 'bark0', 1)
    a.band([(-20, 30 + b), (20, 30 + b), (17, 22 + b), (11, 26 + b), (4, 21 + b), (-3, 26 + b), (-10, 21 + b), (-17, 24 + b)], 'moss', out=False)
    a.e(1, 34 + b - fall * 8, 7.6, 8.6, 'root')
    if fall < .7:
        a.e(1, 34 + b, 5.6, 6.6, 'heart')
        a.dot(-1, 37 + b, 'shine', 2)
    for s in (-1, 1):
        a.e(s * 17, 47 + b - fall * 9, 9, 7.4, 'bark')
        a.e(s * 17, 52 + b - fall * 9, 7.6, 4, 'moss')
        a.e(s * 19, 58 + b - fall * 9, 3.6, 3.2, 'cap')
        a.dot(s * 19 - 1, 59 + b - fall * 9, 'spot', 2)
    # head: a gnarled face under a crown of moss and two mushrooms
    hx = lerp(0, -9, fall)
    hy = lerp(58 + b, 14, fall)
    a.e(hx, hy, 14, 12.4, 'bark')
    a.e(hx - 4, hy + 5, 7, 4, 'bark', out=False)
    a.band([(hx - 14, hy + 3), (hx + 14, hy + 3), (hx + 13, hy + 10), (hx + 6, hy + 14), (hx - 6, hy + 14), (hx - 13, hy + 10)], 'moss')
    a.e(hx - 6, hy + 18, 4.6, 3.8, 'cap')
    a.dot(hx - 7, hy + 19, 'spot', 2)
    a.e(hx + 6, hy + 17, 3.6, 3, 'cap')
    a.dot(hx + 5, hy + 18, 'spot', 1)
    state = T['state']
    for dx in (-5, 5.4):
        if state == 'dead':
            a.line((hx + dx - 2.4, hy - 1), (hx + dx + 2.4, hy - 5), 'iris', 2)
            a.line((hx + dx - 2.4, hy - 5), (hx + dx + 2.4, hy - 1), 'iris', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2), 3.6, 3.8 * a.sy)[0], 'iris', outline=True, edge='root0')
            a.f.flat(ellipsoid(*a.g(hx + dx + .6, hy - 2.4), 1.6, 2 * a.sy)[0], 'root0')
            a.dot(hx + dx - 1.4, hy - .6, 'shine', 1)
    if state == 'angry':
        a.line((hx - 9, hy + 2), (hx - 1, hy - 1), 'ink', 2)
        a.line((hx + 2, hy - 1), (hx + 9, hy + 2), 'ink', 2)
    a.line((hx - 3, hy - 8), (hx + 4, hy - 8), 'ink', 1)
    # near arm: a root fist that slams
    fist = (lerp(lerp(30, 26, wind), 32, strike), lerp(lerp(26, 74, wind), 9, strike))
    if clip == 'die':
        fist = (lerp(30, 27, fall), lerp(26, 8, fall))
    a.c((18, 42 + b - fall * 8), fist, 7.4, 6.6, 'bark')
    a.e(fist[0], fist[1], 10, 9.4, 'bark')
    for t in range(3):
        a.line((fist[0] - 3 + t * 3, fist[1] - 6), (fist[0] - 4 + t * 4, fist[1] - 11), 'root1', 2)
    if clip == 'attack' and n in (4, 5):
        for t in range(5):
            a.e(min(33 + t * 1.6, 36), 4 + (t * 7) % 9 + (n - 4) * 3, 2.2, 2.2, 'moss')
    if clip == 'die':
        for t in range(5):
            diamond(a, -22 + t * 11, max(4, 36 - fall * 32 + (t % 3) * 6), 2.2, 3.2, 'moss1' if t % 2 else 'moss2')
    return a.done()


DRAW = dict(toad=toad, croc=croc, knight=knight, hydra=hydra, gloomroot=gloomroot)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/fen-cel-preview')
    print('ok')
