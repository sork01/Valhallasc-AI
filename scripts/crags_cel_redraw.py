"""Cel-shaded Emberfall Crags enemies (zone 1) for make_crag_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi
proportions. 96x96 frame, foot anchor (48,90), five clips. Kind IDs and clip layout are unchanged.
`python3 scripts/crags_cel_redraw.py [kind...]` writes contact sheets to test-results/crags-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('wisp', 'spider', 'wraith', 'golem', 'cinderlord')

PALETTES = {
    'wisp': mk(flame=('#8a1c14', '#e04a1c', '#ff9a2c', '#ffdc5a', '#fff6c0'), iris='#6a2410', blush='#ff7a5a',
               ember=('#ff6a1c', '#ffd04a')),
    'spider': mk(body=('#17141c', '#2e2a38', '#4a4458', '#6c6580'), leg=('#100e14', '#221e2a', '#3a3446'),
                 lava=('#a8300e', '#ff7a1e', '#ffd04a'), iris='#ff9a1e', fang=('#d8c8b0', '#fff0d8'),
                 ash=('#8a8296', '#c8c0d4')),
    'wraith': mk(cloak=('#14102a', '#2a2350', '#463c80', '#6e60b0'), voidc=('#08060f', '#18122a'),
                 lava=('#d9501e', '#ff8a2e', '#ffd36a'), pole=('#4a3424', '#8a6a48'), blade=('#6a7690', '#b8c6dc', '#f0f6ff'),
                 bone=('#a8a0b8', '#e6e0ee'), ash=('#8a8296', '#c8c0d4')),
    'golem': mk(rock=('#1f1c26', '#3c3846', '#6a6474', '#a29cae'), lava=('#a8300e', '#ff7a1e', '#ffd04a', '#fff2a8'),
                dark=('#14121a', '#262230'), smoke=('#74707e', '#b4aec0')),
    'cinderlord': mk(plate=('#1e1a26', '#3c3548', '#6a6078', '#aaa0bc'), gold=('#7a4f12', '#c98f28', '#f6d467', '#fff0a0'),
                     cape=('#7a2410', '#c9461c', '#ff7a2a'), lava=('#a8300e', '#ff7a1e', '#ffd04a', '#fff2a8'),
                     skin=('#1a1420', '#2e2438'), iris='#ffb02e', haft=('#4a3424', '#8a6a48'),
                     steel=('#4a4658', '#8e8aa4', '#d4d0e4')),
}
R.PALETTES.update(PALETTES)


def flame_tongue(a, p0, p1, r, group='flame'):
    a.c(p0, p1, r, .8, group)


# ------------------------------------------------------------------------------------------------
def wisp(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob = T['fall'], T['wind'], T['strike'], T['bob']
    a = Art('wisp', clip, n, sy=1 - fall * .4)
    cx = 8 + strike * 8 - wind * 4 - fall * 4
    cy = 40 + bob * 1.4 - fall * 22
    k = 1 - fall * .7
    fl = math.sin(n * 1.3)
    fl2 = math.sin(n * 1.3 + 2)
    back = 3 + wind * 3 - strike * 4
    # three flame tongues streaming up and back, then the ember head
    a.c((cx - 6, cy + 2), (cx - 36 - back + fl * 2, cy + 10 * k + fl2 * 3), 10, .8, 'flame')
    a.c((cx - 3, cy + 7), (cx - 22 - back * .5 + fl2 * 2, cy + 28 * k + fl * 3), 8.4, .8, 'flame')
    a.c((cx + 5, cy + 8), (cx + 4 + fl * 2, cy + 27 * k + fl2 * 3), 6.4, .8, 'flame')
    a.e(cx - 16, cy + 4, 7, 5, 'flame', out=False)
    hr = 14.5 - fall * 4
    a.e(cx, cy, hr, hr * .94, 'flame')
    a.e(cx - 3, cy + 5, hr * .55, hr * .3, 'flame', out=False)
    if fall < .8:
        a.eye(cx + 1, cy + 1.5, 4.7, iris='iris')
        a.eye(cx + 9.8, cy + 1.2, 3.9, iris='iris')
        a.dot(cx - 5, cy - 4, 'blush', 3)
        a.dot(cx + 12, cy - 4, 'blush', 2)
        if max(wind, strike) > .4:
            a.f.flat(ellipsoid(*a.g(cx + 6, cy - 7), 2.6, 2.2 * a.sy)[0], 'ink')
        else:
            a.line((cx + 3, cy - 7), (cx + 8, cy - 6.4), 'ink', 1)
    if clip != 'die' or fall < .8:
        for i in range(3):
            a.dot(cx - 12 - i * 5 + ((n * 3 + i * 2) % 4), cy - 8 - i * 3 + ((n * 2 + i) % 5), 'ember0' if i % 2 else 'ember1', 2)
    if clip == 'die':
        for i in range(5):
            star(a, -20 + i * 11, max(3, 30 - fall * 26 + (i % 2) * 8), 2.4, 'ember1' if i % 2 else 'ember0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def spider(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob = T['fall'], T['wind'], T['strike'], T['bob']
    a = Art('spider', clip, n)
    by = 24 - fall * 14 + bob * .6
    feet_near = (40, 28, -16, -32)
    feet_far = (34, 22, -24, -38)
    hips = (15, 11, 7, 3)

    def legs(feet, grp, off, flip):
        for i, fx in enumerate(feet):
            up = max(0, math.sin(n * math.pi / 2 + i * math.pi / 2 + flip)) * 5 if clip == 'walk' else 0
            hip = (hips[i] + off, by + 1)
            foot = [fx, up]
            if i < 2 and clip == 'attack':
                foot = [fx + strike * 5 - wind * 8, lerp(0, 36, wind) * (1 - strike)]
            if fall:
                foot = [lerp(fx, hips[i] * .6 + 4, fall), lerp(up, by + 6 + i * 3, fall)]
            kneex = lerp(hip[0], foot[0], .6)
            kneey = by + 17 + (4 if i in (1, 2) else 0) - fall * 10
            a.c(hip, (kneex, kneey), 3.4, 2.7, grp)
            a.c((kneex, kneey), tuple(foot), 2.7, 1.3, grp)
            a.e(kneex, kneey, 2.7, 2.7, grp)
    legs(feet_far, 'leg', -1, 1.4)
    # abdomen: big cracked basalt egg with spikes and a glowing seam
    ax_, ay_ = -19, by + 6
    for sx, sh in ((-9, 10), (-2, 13), (6, 9)):
        a.poly([(ax_ + sx - 3.4, ay_ + 13), (ax_ + sx + 1, ay_ + 13 + sh), (ax_ + sx + 4, ay_ + 12)], 'ash0')
    a.e(ax_, ay_, 19, 16.5, 'body')
    a.e(ax_ - 5, ay_ + 7, 8, 5, 'body', out=False)
    zig = [(ax_ - 9, ay_ + 9), (ax_ - 3, ay_ + 4), (ax_ - 8, ay_ - 1), (ax_ - 1, ay_ - 7), (ax_ + 5, ay_ - 2), (ax_ + 3, ay_ + 7)]
    for p, q in zip(zig, zig[1:]):
        a.line(p, q, 'lava1' if fall < .6 else 'body0', 2)
    a.dot(ax_ - 9, ay_ + 11, 'ash1', 2)
    legs(feet_near, 'body', 0, 0)
    # head with a big pair of eyes and a ring of small ones, and fangs
    hx, hy = 11, by + 3
    a.e(hx, hy, 15, 12.5, 'body')
    a.e(hx + 2, hy + 7, 8, 4.5, 'body', out=False)
    mouth = lerp(0, 5, wind + strike)
    for sgn in (-1, 1):
        a.poly([(hx + 15 + sgn * 2.4 - 2, hy - 3), (hx + 15 + sgn * 2.4 + 2, hy - 3),
                (hx + 16 + sgn * (2.4 + mouth), hy - 12 - mouth * .6)], 'fang1')
    a.eye(hx + 6.5, hy + 3, 4.4, iris='iris')
    a.eye(hx + 15, hy + 2, 3.7, iris='iris')
    for dx, dy in ((1, 9), (6, 10), (11, 9.5)):
        a.dot(hx + dx, hy + dy, 'iris', 2)
    a.dot(hx - 5, hy + 8, 'lava0', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.e(min(hx + 19 + k * 2.6, 38), hy - 4 + (k % 2) * 4, 2.2, 2.2, 'lava')
    return a.done()


# ------------------------------------------------------------------------------------------------
def wraith(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('wraith', clip, n, sy=1 - fall * .6)
    a.lift = 8 + bob * 1.2 - fall * 8
    sway = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else sw * 2
    rag = [-1, 1, 0, -1, 1][n % 5]
    hem = [(-22, 2), (-17, 8 + rag), (-13, 0), (-8, 9), (-3, 1), (2, 10 - rag), (7, 0), (12, 9), (17, 2), (21, 8 + rag)]
    cloak = [(-9, 56 + bob), (10, 56 + bob), (16 + sway * .3, 36), (22 + sway, 12)] + hem[::-1] + [(-20, 12), (-15, 36)]
    a.band(cloak, 'cloak')
    a.band([(-3 + sway * .2, 44), (6, 44), (9, 8), (-2, 8)], 'cloak', out=False)
    for k in range(5):
        a.dot(-17 + k * 8.4 + sway * .3, 3 + (k % 2) * 6, 'lava1', 2)
    # scythe: pole angle from raised back to swung forward
    hand = (lerp(lerp(17, 12, wind), 21, strike), lerp(lerp(34, 55, wind), 26, strike))
    ang = lerp(lerp(1.5, 2.1, wind), .25, strike)       # pole direction, radians from +x
    if clip == 'die':
        hand = (lerp(17, 10, fall), lerp(34, 6, fall))
        ang = lerp(1.5, 3.0, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 24, hand[1] - dy * 24)
    top = (hand[0] + dx * 30, hand[1] + dy * 30)
    top = (min(top[0], 26), min(top[1], 68))
    a.line(base, top, 'ink', 4)
    a.line(base, top, 'pole1', 2)
    px, py = dy, -dx
    blade = [(top[0] - dx * 5, top[1] - dy * 5), (top[0] + px * 11 + dx * 3, top[1] + py * 11 + dy * 3),
             (top[0] + px * 20 - dx * 2, top[1] + py * 20 - dy * 2), (top[0] + px * 12 - dx * 6, top[1] + py * 12 - dy * 6),
             (top[0] + px * 3 - dx * 8, top[1] + py * 3 - dy * 8)]
    a.band(blade, 'blade')
    # arm, hand, and the great hood with its void face
    a.c((9, 49 + bob), hand, 4.4, 3.8, 'cloak')
    a.e(hand[0], hand[1], 3.2, 3.2, 'bone')
    hx, hy = 1 + sway * .4, 60 + bob
    a.poly([(hx - 10, hy + 2), (hx - 20 - sway, hy + 12 - rag), (hx - 6, hy + 10)], 'cloak1')
    a.e(hx, hy, 14, 13, 'cloak')
    a.e(hx - 4, hy + 6, 8, 4.4, 'cloak', out=False)
    a.e(hx + 3.5, hy - 1.5, 10, 9.2, 'voidc')
    state = T['state']
    for ex in (hx, hx + 9):
        if state == 'dead':
            a.line((ex - 2.4, hy - 1), (ex + 2.4, hy - 5), 'lava1', 2)
            a.line((ex - 2.4, hy - 5), (ex + 2.4, hy - 1), 'lava1', 2)
        elif T['blink'] and state == 'open':
            a.line((ex - 3, hy - 3), (ex + 3, hy - 3), 'lava1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(ex, hy - 2.5), 3.6, 4.2 * a.sy)[0], 'lava1', outline=True, edge='voidc0')
            a.f.flat(ellipsoid(*a.g(ex + .5, hy - 3.5), 2, 2.4 * a.sy)[0], 'lava2')
            a.dot(ex - 1.5, hy - 1, 'shine', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(top[0] + 12 + k * 3, 34), max(top[1] - 8 + k * 4, 6), 2.3, 'lava2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def golem(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('golem', clip, n, sy=1 - fall * .45)
    b = bob * .8
    # smoke from the shoulder vents
    if clip != 'die':
        for k in range(3):
            rise = (n * 1.7 + k * 4) % 11
            a.e(-16 + k * 3 + rise * .3, 62 + b + rise * .8, 2.4 + rise * .2, 2.2 + rise * .18, 'smoke', out=False)
    for s in (-1, 1):                          # pillar legs and wide feet
        up = max(0, math.sin(n * math.pi / 2 + (0 if s < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.c((s * 10, 20), (s * 10 + fall * s * 4, 7 + up), 8 * (1 - fall * .5), 8.6 * (1 - fall * .55), 'rock')
        a.e(s * 10 + fall * s * 5, 4 + up, 10.4, 4.6, 'rock')
    a.c((-18, 40 + b), (-29 - fall * 3, 26 - fall * 14), 7, 6.6, 'rock')
    a.e(-30 - fall * 3, 22 - fall * 12, 9.6, 8.8, 'rock')
    # barrel torso with a molten heart and cracks
    a.e(0, 33 + b - fall * 8, 22.4, 18.6, 'rock')
    a.e(-8, 41 + b - fall * 8, 10, 6, 'rock', out=False)
    a.e(0, 34 + b - fall * 8, 8, 9, 'dark')
    if fall < .6:
        a.e(0, 34 + b, 5.8, 6.8, 'lava')
        a.dot(-2, 37 + b, 'shine', 2)
    zig = [(-15, 22), (-9, 27), (-13, 34), (-7, 38)]
    for (x0, y0), (x1, y1) in zip(zig, zig[1:]):
        a.line((x0, y0 + b), (x1, y1 + b), 'lava1' if fall < .6 else 'rock0', 2)
    for (x0, y0), (x1, y1) in zip([(12, 20), (16, 27), (11, 32)], [(16, 27), (11, 32), (15, 38)]):
        a.line((x0, y0 + b), (x1, y1 + b), 'lava1' if fall < .6 else 'rock0', 1)
    # big round shoulders with vents
    for s in (-1, 1):
        a.e(s * 17, 46 + b - fall * 9, 8.4, 7, 'rock')
        a.e(s * 17, 52 + b - fall * 9, 3.6, 1.8, 'dark', out=False)
    # small head sunk between the shoulders: a visor of glowing eyes
    hx = lerp(0, -9, fall)
    hy = lerp(57 + b, 13, fall)
    a.e(hx, hy, 12.4, 10.6, 'rock')
    a.e(hx - 4, hy + 5, 6, 3.4, 'rock', out=False)
    a.poly([(hx - 10, hy + 3), (hx + 10, hy + 3), (hx + 10, hy - 6), (hx - 10, hy - 6)], 'dark1', out=False)
    state = T['state']
    for dx in (-4.4, 4.8):
        if state == 'dead':
            a.line((hx + dx - 2.4, hy - 1), (hx + dx + 2.4, hy - 5), 'lava1', 2)
            a.line((hx + dx - 2.4, hy - 5), (hx + dx + 2.4, hy - 1), 'lava1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2), 3.4, 3.1 * a.sy)[0], 'lava2', outline=True, edge='dark0')
            a.f.flat(ellipsoid(*a.g(hx + dx + .6, hy - 2.3), 1.7, 2 * a.sy)[0], 'lava0')
            a.dot(hx + dx - 1.4, hy - .6, 'shine', 1)
    if state == 'angry':
        a.line((hx - 9, hy + 2), (hx - 1, hy - 1), 'ink', 2)
        a.line((hx + 2, hy - 1), (hx + 9, hy + 2), 'ink', 2)
    fist = (lerp(lerp(30, 26, wind), 32, strike), lerp(lerp(26, 74, wind), 9, strike))
    if clip == 'die':
        fist = (lerp(30, 27, fall), lerp(26, 8, fall))
    a.c((18, 40 + b - fall * 8), fist, 7.4, 6.8, 'rock')
    a.e(fist[0], fist[1], 10.6, 9.6, 'rock')
    a.e(fist[0] - 3, fist[1] + 4, 5, 2.8, 'rock', out=False)
    a.line((fist[0] + 2, fist[1] - 3), (fist[0] + 3, fist[1] - 8), 'lava1', 1) if fall < .6 else None
    if clip == 'attack' and n in (4, 5):
        for k in range(5):
            a.e(min(34 + k * 2.2, 38), 4 + (k * 7) % 9 + (n - 4) * 3, 2.4, 2.4, 'lava' if k % 2 else 'rock')
    if clip == 'die':
        for k in range(5):
            a.e(-22 + k * 11, 5 + (k % 2) * 2, 4.2 - k % 2, 3, 'rock' if k % 2 else 'dark')
    return a.done()


# ------------------------------------------------------------------------------------------------
def cinderlord(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('cinderlord', clip, n, sy=1 - fall * .5)
    b = bob * .5
    # flowing cape behind
    flow = math.sin(n * math.pi / 3) * 1.5 if clip == 'idle' else sw * 2
    a.band([(-8, 56 + b), (8, 56 + b), (18 + flow, 30), (21 + flow * 1.4, 7), (-21 + flow, 7), (-18, 30)], 'cape')
    a.band([(-20 + flow, 7), (-14, 13), (-8, 6), (-2, 12), (4, 6), (10, 12), (16, 6), (21 + flow, 7)], 'cape', out=False)
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 8, 24), (s * 8, 7 + up), 5.2, 4.6, 'plate')
        a.e(s * 8.6, 4.4 + up, 8, 4.4, 'plate')
        a.line((s * 8 - 3, 7 + up), (s * 8 + 3, 7 + up), 'gold1', 1)
    # tasset, torso with a lava diamond, belt
    a.band([(-13, 27), (13, 27), (16, 18), (-16, 18)], 'gold')
    a.e(0, 38 + b, 15.4, 13, 'plate')
    a.e(-5, 44 + b, 8, 4.4, 'plate', out=False)
    a.poly([(0, 47 + b), (6, 38 + b), (0, 29 + b), (-6, 38 + b)], 'lava1', edge='gold1')
    a.poly([(0, 44 + b), (3.4, 38 + b), (0, 32 + b), (-3.4, 38 + b)], 'lava2', out=False)
    a.line((-14, 30 + b), (14, 30 + b), 'gold1', 2)
    # shoulder spikes
    for s in (-1, 1):
        a.e(s * 19, 49 + b, 8.4, 7, 'plate')
        a.poly([(s * 19 - 4, 53 + b), (s * 19 + s * 3, 66 + b), (s * 19 + 4, 53 + b)], 'gold2')
    # warhammer: haft from the near hand, golden-banded head
    hand = (lerp(lerp(24, 20, wind), 27, strike), lerp(lerp(40, 58, wind), 30, strike))
    far = (-22, 38 + b + (sw * 2 if clip == 'walk' else 0))
    a.c((-12, 46 + b), far, 3.8, 3.4, 'plate')
    a.e(far[0], far[1], 3.6, 3.6, 'gold')
    ang = lerp(lerp(1.62, 2.0, wind), .3, strike)
    if clip == 'die':
        hand = (lerp(24, 22, fall), lerp(40, 8, fall))
        ang = lerp(1.62, 3.0, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 14, hand[1] - dy * 14)
    top = (min(hand[0] + dx * 22, 30), min(hand[1] + dy * 22, 78))
    a.line(base, top, 'ink', 4)
    a.line(base, top, 'haft1', 2)
    px, py = dy, -dx
    head = [(top[0] - px * 9 - dx * 6, top[1] - py * 9 - dy * 6), (top[0] + px * 9 - dx * 6, top[1] + py * 9 - dy * 6),
            (top[0] + px * 9 + dx * 6, top[1] + py * 9 + dy * 6), (top[0] - px * 9 + dx * 6, top[1] - py * 9 + dy * 6)]
    a.band(head, 'steel')
    a.line((top[0] - px * 9, top[1] - py * 9), (top[0] + px * 9, top[1] + py * 9), 'gold1', 2)
    a.c((14, 47 + b), hand, 4.2, 3.8, 'plate')
    a.e(hand[0], hand[1], 4, 3.8, 'gold')
    # horned helm with a dark visor and burning eyes
    hx, hy = 1, 62 + b
    for s in (-1, 1):
        a.poly([(hx + s * 9, hy + 6), (hx + s * 17, hy + 20 + (2 if s > 0 else 0)), (hx + s * 5, hy + 10)], 'gold2')
    a.e(hx, hy, 14, 12.4, 'plate')
    a.e(hx - 4, hy + 6, 8, 4.2, 'plate', out=False)
    a.poly([(hx - 12, hy + 3), (hx + 12, hy + 3), (hx + 12, hy - 7), (hx - 12, hy - 7)], 'skin0', out=False)
    state = T['state']
    for dx_ in (-5, 5.6):
        if state == 'dead':
            a.line((hx + dx_ - 2.4, hy - 1), (hx + dx_ + 2.4, hy - 5), 'lava1', 2)
            a.line((hx + dx_ - 2.4, hy - 5), (hx + dx_ + 2.4, hy - 1), 'lava1', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx_, hy - 2), 3.8, 3.3 * a.sy)[0], 'lava2', outline=True, edge='skin0')
            a.f.flat(ellipsoid(*a.g(hx + dx_ + .6, hy - 2.3), 2, 2.3 * a.sy)[0], 'iris')
            a.dot(hx + dx_ - 1.4, hy - .2, 'shine', 1)
    a.line((hx - 12, hy - 8), (hx + 12, hy - 8), 'gold1', 2)
    a.poly([(hx - 3, hy + 12), (hx, hy + 20), (hx + 3, hy + 12)], 'gold2')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(top[0] + 6 + k * 4, 38), top[1] - 10 + k * 4, 2.6, 'lava2')
    return a.done()


DRAW = dict(wisp=wisp, spider=spider, wraith=wraith, golem=golem, cinderlord=cinderlord)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/crags-preview')
    print('ok')
