"""Cel-shaded Bifrost Reach enemies (zone 7) for make_sky_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi
proportions. 96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/sky_cel_redraw.py [kind...]` writes contact sheets to test-results/sky-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('galehound', 'prismgolem', 'skyray', 'einherjar', 'thunderroc')

PALETTES = {
    'galehound': mk(fur=('#4a6a98', '#8aaad8', '#cfe0fa', '#fbfdff'), belly=('#b4c8e8', '#e8f0fc', '#fdfeff'),
                    wind=('#7ab0e8', '#c8e4ff', '#f4faff'), bolt=('#ffd23a', '#fffbc8'), iris='#18c0ff',
                    blush='#ff9ab8', mouth=('#5a1c34', '#ff6f98'), fang=('#e0e8f2', '#fefeff')),
    'prismgolem': mk(rock=('#2a2a5e', '#5a60b0', '#9aa4e4', '#dce4ff'), pr=('#ff6fae', '#ffd25a', '#4fe0cc', '#7a8cff'),
                     core=('#fff1b0', '#fffbe0'), dark=('#16163a', '#22224e'), iris='#ff4fae', glow=('#e8f0ff', '#8ab0ff'),
                     blush='#ff9ac8'),
    'skyray': mk(body=('#1a2a64', '#3454b0', '#6a94e6', '#b4d4ff'), belly=('#9ab8e6', '#dce8fb', '#f8fcff'),
                 fin=('#24348a', '#4a6ad0', '#8aaeff'), iris='#ffcc2e', blush='#ff9ab8', bolt=('#ffd23a', '#fffbc8'),
                 spot=('#d8f0ff', '#ffffff')),
    'einherjar': mk(plate=('#1a2030', '#3a4a64', '#6a82a8', '#a8c2e4'), ghost=('#0e5a6a', '#2ac8d8', '#9af4f8', '#e8ffff'),
                    horn=('#8a826a', '#d2cab0', '#f4ecd2'), cloth=('#2a2a50', '#464884', '#7678c0'),
                    wood=('#4a3220', '#7a5634', '#b08454'), iris='#38e8f0', iron=('#2c3444', '#5a6a82', '#9aaac4'),
                    blade=('#6a8aa4', '#b8d4ea', '#f2fbff')),
    'thunderroc': mk(plume=('#7a3a14', '#c4682a', '#f0a04a', '#ffd88a'), crest=('#1a3a98', '#3a78e0', '#8ac0ff', '#e0f0ff'),
                     head=('#aab8cc', '#e4ecf6', '#fbfdff'), wing=('#142a70', '#2a56c0', '#5a96f0', '#a8d4ff'),
                     beak=('#a86a14', '#f0b030', '#ffe27a'), iris='#ffc42e', claw=('#4a3c5a', '#8a7aa0'),
                     bolt=('#ffd23a', '#fffbc8'), blush='#ff8a98'),
}
R.PALETTES.update(PALETTES)


def bolt_poly(a, x, y, s, name):
    a.poly([(x, y + 5 * s), (x + 3 * s, y + 1 * s), (x + 1 * s, y + .5 * s), (x + 4 * s, y - 5 * s), (x - 3 * s, y), (x - 1 * s, y + .4 * s)], name)


# ------------------------------------------------------------------------------------------------
def galehound(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('galehound', clip, n, sy=1 - fall * .45)
    b = bob * .6 - fall * 5
    by = 25 + b
    lean = strike * 3 - wind * 5
    # a streaming wind-scarf tail
    for k in range(3):
        a.c((-19, by + 1 - k), (-34 + k * 2 + math.sin(n * 1.2 + k) * 2, by + 6 + k * 5 + math.sin(n + k) * 2), 4 - k * .6, .8, 'wind')
    for lx, ph in ((-15, 1.6), (9, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 6 if clip == 'walk' else 0
        a.c((lx + 3, by - 4), (lx + 5 + up * .3, up + 3), 4, 3, 'fur')
        a.e(lx + 7 + up * .3, up + 3, 4.6, 2.2, 'belly')
    for k in range(4):                                      # cloud-puff back ridge
        a.e(-14 + k * 7, by + 11 - abs(k - 1.5) * .8, 5, 4.4, 'wind')
    a.e(-6, by, 20, 12.4, 'fur')
    a.e(-3, by - 7, 14, 5, 'belly', out=False)
    a.e(12, by + 3, 11.4, 11, 'fur')
    for (bx, by2) in ((-12, 3), (-2, 6)):
        bolt_poly(a, bx, by + by2, .8, 'bolt0')
    for lx, ph in ((-12, 0), (11, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 6 if clip == 'walk' else 0
        a.c((lx, by - 4), (lx + 2 + up * .3, up + 3), 4.8, 3.4, 'fur')
        a.e(lx + 4 + up * .3, up + 3, 5, 2.4, 'belly')
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
    a.dot(hx + 17, hy - 1.4, 'ink', 2)
    for (ex, eh, tilt) in ((-6, 15, -3), (1, 17, 3)):
        a.poly([(hx + ex - 4.4, hy + 7), (hx + ex + tilt, hy + 7 + eh), (hx + ex + 5.4, hy + 7)], 'fur1')
        bolt_poly(a, hx + ex + tilt * .4, hy + 14, .5, 'bolt0')
    a.eye(hx + 2.4, hy + 2.4, 4.6, iris='iris')
    a.eye(hx + 10.5, hy + 2, 3.2, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            bolt_poly(a, min(hx + 20 + k * 4, 36), hy - 2 + (k % 2) * 5, .7, 'bolt0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def prismgolem(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('prismgolem', clip, n, sy=1 - fall * .45)
    b = bob * .8
    for sg in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if sg < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.c((sg * 10, 20), (sg * 10 + fall * sg * 4, 7 + up), 8 * (1 - fall * .5), 8 * (1 - fall * .55), 'rock')
        a.e(sg * 10 + fall * sg * 5, 4 + up, 10, 4.4, 'rock')
    a.c((-18, 40 + b), (-29 - fall * 3, 26 - fall * 14), 6.6, 6, 'rock')
    a.poly([(-35 - fall * 3, 22 - fall * 12), (-29 - fall * 3, 31 - fall * 12), (-23 - fall * 3, 22 - fall * 12), (-29 - fall * 3, 13 - fall * 12)], 'pr1')
    # faceted body: a big crystal torso with rainbow bands
    a.e(0, 34 + b - fall * 8, 21, 18.4, 'rock')
    a.e(-7, 42 + b - fall * 8, 9, 5.6, 'rock', out=False)
    for k in range(4):
        a.line((-14 + k * 3.4, 42 + b - fall * 8 - k * 2), (-9 + k * 3.4, 22 + b - fall * 8), f'pr{k}', 2)
    a.poly([(0, 46 + b - fall * 8), (7, 37 + b - fall * 8), (0, 28 + b - fall * 8), (-7, 37 + b - fall * 8)], 'core1', edge='dark0')
    a.poly([(0, 42 + b - fall * 8), (3.4, 37 + b - fall * 8), (0, 32 + b - fall * 8), (-3.4, 37 + b - fall * 8)], 'core0', out=False)
    for sg in (-1, 1):
        a.e(sg * 17, 48 + b - fall * 9, 8.4, 7, 'rock')
        crystal(a, sg * 17, 52 + b - fall * 9, 3.4, 11, 'rock', tilt=sg * 2)
    hx = lerp(0, -9, fall)
    hy = lerp(59 + b, 14, fall)
    crystal(a, hx - 6, hy + 8, 3.2, 12, 'rock', tilt=-3)
    crystal(a, hx + 6, hy + 8, 3, 10, 'rock', tilt=3)
    a.e(hx, hy, 13, 11.6, 'rock')
    a.e(hx - 4, hy + 5, 6.4, 3.6, 'rock', out=False)
    a.eye(hx - 3.6, hy + 1, 4.4, iris='iris', look=(.4, .1))
    a.eye(hx + 6, hy + 1, 4.2, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 3, 'blush', 3)
    a.line((hx - 3, hy - 7), (hx + 5, hy - 7), 'ink', 1)
    fist = (lerp(lerp(30, 26, wind), 32, strike), lerp(lerp(26, 74, wind), 9, strike))
    if clip == 'die':
        fist = (lerp(30, 27, fall), lerp(26, 8, fall))
    a.c((18, 42 + b - fall * 8), fist, 7, 6.4, 'rock')
    a.poly([(fist[0] - 9, fist[1]), (fist[0], fist[1] + 10), (fist[0] + 9, fist[1]), (fist[0], fist[1] - 10)], 'pr2')
    a.line((fist[0] - 3, fist[1] + 4), (fist[0] + 2, fist[1] - 3), 'core0', 2)
    if clip == 'attack' and n in (4, 5):
        for k in range(5):
            diamond(a, min(33 + k * 1.6, 36), 5 + (k * 7) % 9 + (n - 4) * 3, 2, 3, f'pr{k % 4}')
    if clip == 'die':
        for k in range(5):
            diamond(a, -22 + k * 11, 6 + (k % 2) * 2, 3.4, 4.4, f'pr{k % 4}', out=True)
    return a.done()


# ------------------------------------------------------------------------------------------------
def skyray(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('skyray', clip, n, sy=1 - fall * .35)
    if clip == 'idle':
        fl = math.sin(n * math.pi / 3)
    elif clip == 'walk':
        fl = math.sin(n * math.pi / 2)
    elif clip == 'attack':
        fl = lerp(lerp(.2, 1., wind), -1., strike)
    elif clip == 'hurt':
        fl = (1., .6, .3, 0.)[n]
    else:
        fl = .2
    cy = 44 + bob * 1.2 - fall * 28
    # long whip tail
    a.c((-12, cy - 2), (-26 - fall * 6, cy - 9 + math.sin(n * 1.2) * 3 - fall * 6), 4, 1.4, 'body')
    a.c((-26 - fall * 6, cy - 9 + math.sin(n * 1.2) * 3 - fall * 6), (-37 - fall * 6, cy - 5 + math.sin(n * 1.2 + 1) * 4 - fall * 8), 1.8, .8, 'body')
    # diamond wings flapping up and down, near and far
    for s, grp in ((-1, 'fin'), (1, 'fin')):
        tip = (s * (34 - abs(fl) * 4 - fall * 12), cy + fl * 17 - fall * 14)
        a.band([(s * 3, cy + 6), (s * 15, cy + 9 + fl * 6), tip, (s * 17, cy - 8 + fl * 3), (s * 4, cy - 7)], grp)
        a.line((s * 6, cy), (tip[0] - s * 5, tip[1] - 1), 'fin0', 1)
        for k in range(2):
            a.dot(s * (14 + k * 7), cy + 2 + fl * (4 + k * 3), 'spot0', 2)
    a.e(0, cy, 14.4, 12, 'body')
    a.e(2, cy - 5, 11.4, 5.6, 'belly', out=False)
    bolt_poly(a, -4, cy + 6, .7, 'bolt0')
    a.eye(1, cy + 2, 4.7, iris='iris')
    a.eye(10.4, cy + 1.6, 3.4, iris='iris')
    a.dot(-5, cy - 2, 'blush', 3)
    a.dot(13, cy - 3, 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            bolt_poly(a, min(16 + k * 7, 36), cy - 6 + (k % 2) * 6, .7, 'bolt0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def einherjar(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('einherjar', clip, n, sy=1 - fall * .5)
    b = bob * .5
    for sg in (-1, 1):
        up = max(0, sg * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((sg * 8, 22), (sg * 8, 6 + up), 4.8, 4.2, 'plate')
        a.e(sg * 8.6, 4 + up, 7.2, 4, 'plate')
    sx, sy_ = -25 + wind * -2, 36 + b
    a.e(sx, sy_, 12, 13, 'wood')
    a.e(sx, sy_, 8.6, 9.6, 'ghost', out=False)
    a.poly([(sx, sy_ + 6), (sx + 3, sy_), (sx, sy_ - 6), (sx - 3, sy_)], 'ghost3')
    a.c((-12, 41 + b), (sx + 6, sy_ + 2), 3.6, 3.2, 'plate')
    a.band([(-12, 25), (12, 25), (14, 15), (-14, 15)], 'cloth')
    # hollow breastplate: a ghost flame burns inside the open chest
    a.e(0, 35 + b, 14, 11.8, 'plate')
    a.e(-5, 40 + b, 7.4, 4.2, 'plate', out=False)
    a.e(0, 35 + b, 6.4, 7.4, 'ghost')
    a.e(1, 35 + b, 3, 4, 'ghost', out=False)
    a.line((-14, 27 + b), (14, 27 + b), 'iron1', 2)
    hand = (lerp(lerp(19, 15, wind), 25, strike), lerp(lerp(34, 41, wind), 34, strike))
    ang = lerp(lerp(1.5, 2.0, wind), .2, strike)
    if clip == 'die':
        hand = (lerp(19, 25, fall), lerp(34, 8, fall))
        ang = lerp(1.5, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 5, hand[1] - dy * 5)
    tip = (min(hand[0] + dx * 30, 28), min(hand[1] + dy * 30, 70))
    a.line(base, tip, 'ink', 6)
    a.line(base, tip, 'blade1', 4)
    a.line(base, tip, 'ghost2', 1)
    a.line((hand[0] - dy * 6, hand[1] + dx * 6), (hand[0] + dy * 6, hand[1] - dx * 6), 'iron1', 3)
    a.c((10, 42 + b), hand, 4, 3.6, 'plate')
    a.e(hand[0], hand[1], 3.8, 3.6, 'ghost')
    for sg in (-1, 1):
        a.e(sg * 15.6, 43 + b, 7.6, 6.6, 'plate')
        a.dot(sg * 15.6 - 1, 46 + b, 'iron2', 2)
    hx, hy = 1, 56 + b
    for sg in (-1, 1):
        a.poly([(hx + sg * 11, hy + 5), (hx + sg * 19, hy + 15), (hx + sg * 14, hy + 21), (hx + sg * 8, hy + 8)], 'horn1')
    a.e(hx, hy, 13.6, 12, 'plate')
    a.e(hx - 4, hy + 6, 7.4, 4, 'plate', out=False)
    a.poly([(hx - 11, hy + 3), (hx + 12, hy + 3), (hx + 12, hy - 7), (hx - 11, hy - 7)], 'ink', out=False)
    state = T['state']
    for dx_ in (-4.8, 5.4):
        if state == 'dead':
            a.line((hx + dx_ - 2.4, hy - 1), (hx + dx_ + 2.4, hy - 5), 'ghost2', 2)
            a.line((hx + dx_ - 2.4, hy - 5), (hx + dx_ + 2.4, hy - 1), 'ghost2', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx_, hy - 2), 3.8, 3.3 * a.sy)[0], 'ghost2', outline=True)
            a.f.flat(ellipsoid(*a.g(hx + dx_ + .6, hy - 2.3), 2.1, 2.5 * a.sy)[0], 'iris')
            a.dot(hx + dx_ - 1.4, hy - .2, 'shine', 1)
    a.line((hx - 11, hy - 8), (hx + 12, hy - 8), 'iron1', 2)
    for k in range(3):
        a.e(hx - 6 + k * 6 + math.sin(n + k) * 1.2, hy + 14 + (k % 2) * 3, 2, 2.8, 'ghost') if False else None
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 6 + k * 4, 36), tip[1] - 3 + k * 4, 2.4, 'ghost3')
    return a.done()


# ------------------------------------------------------------------------------------------------
def thunderroc(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('thunderroc', clip, n, sy=1 - fall * .35)
    if clip == 'idle':
        fl = math.sin(n * math.pi / 3) * .35
    elif clip == 'walk':
        fl = math.sin(n * math.pi / 2) * .6
    elif clip == 'attack':
        fl = lerp(lerp(.2, 1., wind), -.8, strike)
    elif clip == 'hurt':
        fl = (1., .6, .3, 0.)[n]
    else:
        fl = .3
    by = 30 + bob * .8 - fall * 12
    hx, hy = 12 + strike * 5, by + 17 - strike * 4
    for k in range(4):
        a.c((-10, by - 4), (-30 + k * 2 - fall * 4, by - 12 + k * 5 + fl * 3), 3.8, 2, 'wing')
    for sg, ox in ((-1, 0), (1, 5)):
        up = max(0, sg * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((ox - 1, by - 8), (ox + strike * 4, 4 + up), 3.4, 2.4, 'claw')
        for t in range(3):
            a.line((ox + strike * 4, 4 + up), (ox + 3 + strike * 4 - t * 3, 1 + up), 'claw1', 1)

    def wing(base_ang, length):
        sh = (-3, by + 7)
        ang0 = base_ang + fl * 30 * (1 - fall)
        pts = [sh]
        for k in range(5):
            th = math.radians(ang0 + (k - 2) * 15)
            ln = length - abs(k - 2) * 3.6
            nth = math.radians(ang0 + (k - 2) * 15 - 7.5)
            pts.append((sh[0] + math.cos(nth) * length * .56, sh[1] + math.sin(nth) * length * .56))
            pts.append((sh[0] + math.cos(th) * ln, sh[1] + math.sin(th) * ln))
        nth = math.radians(ang0 + 2 * 15 + 7.5)
        pts.append((sh[0] + math.cos(nth) * length * .56, sh[1] + math.sin(nth) * length * .56))
        a.band(pts, 'wing')
    wing(138 + fall * 30, 30)
    a.e(0, by, 17, 15, 'plume')
    a.e(-4, by - 8, 12, 5.4, 'plume', out=False)
    a.e(4, by + 1, 7.6, 9, 'head')
    wing(122 + fall * 50 - fl * 6, 36)
    bolt_poly(a, -6, by + 2, 1., 'bolt0')
    gap = max(wind * .4, strike) * 4
    a.poly([(hx + 6, hy - 3 - gap), (hx + 18, hy - 5 - gap), (hx + 8, hy - 10 - gap)], 'beak0')
    a.e(hx, hy, 11.4, 10.4, 'head')
    a.poly([(hx + 7, hy + 1), (hx + 21, hy - 3), (hx + 16, hy - 8), (hx + 8, hy - 6)], 'beak1')
    a.poly([(hx + 17, hy - 3), (hx + 22, hy - 9), (hx + 16, hy - 7)], 'beak2', out=False)
    for k, (dx, h) in enumerate(((-9, 9), (-4, 14), (1, 17), (6, 11))):
        a.poly([(hx + dx - 2.4, hy + 8), (hx + dx, hy + 8 + h), (hx + dx + 3, hy + 8)], 'crest1' if k % 2 else 'crest2')
    a.eye(hx + 2, hy + 1.8, 4.8, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (4, 5):
        for k in range(3):
            bolt_poly(a, min(hx + 20 + k * 4, 36), hy - 4 + (k % 2) * 6, .8, 'bolt0')
    return a.done()


DRAW = dict(galehound=galehound, prismgolem=prismgolem, skyray=skyray, einherjar=einherjar, thunderroc=thunderroc)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/sky-cel-preview')
    print('ok')
