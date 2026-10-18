"""Cel-shaded Stormglass Shore enemies (zone 19) for make_stormglass_sprites.py.

Same recipe as orrery_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/stormglass_cel_redraw.py [kind...]` writes contact sheets to test-results/stormglass-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('saltclaw', 'stormgull', 'glassray', 'breakersentinel', 'maelstromheart')

PALETTES = {
    'saltclaw': mk(shell=('#1c4a58', '#3a8a96', '#7ccac4', '#d0f4e6'), salt=('#a8b8bc', '#e8f0ee', '#fbfffd'),
                   claw=('#5a2e44', '#a8505e', '#e0827a', '#ffc4a8'), leg=('#17404c', '#2e7482', '#5eaeb0'),
                   iris='#c8486e', blush='#ff9a98', foam='#bef4ff', mouth=('#3a1428', '#ff7a98')),
    'stormgull': mk(plume=('#3a4e6e', '#7a96b4', '#c4d8e6', '#f6fbff'), wing=('#1c2a4a', '#3c5486', '#6c8cc4', '#b4ccf0'),
                    beak=('#a8641c', '#f2a82e', '#ffe07a'), leg=('#9a5a18', '#f0b03a'), bolt=('#fff29a', '#ffffe8'),
                    iris='#2a7ad0', blush='#ff9ac0', cloud=('#5a6a8a', '#aab8d4')),
    'glassray': mk(glass=('#14406a', '#2e84b4', '#6cd0dc', '#cffbf2'), edge=('#0e2a50', '#2a5a92', '#58a0cc'),
                   core=('#1fb8c8', '#8cf6ff', '#f2ffff'), tail=('#2a6a98', '#9ae6f0'), iris='#16a8c8',
                   blush='#ff9ac0', bubble='#c4f6ff'),
    'breakersentinel': mk(stone=('#2c3a40', '#5a7480', '#8ea8ae', '#cadcd6'), barn=('#a8a890', '#e4e4cc', '#fbfbe8'),
                          foam=('#7ab0c4', '#c8ecf4', '#f6ffff'), gold=('#a8761e', '#f6cf62', '#fff2b0'),
                          weed=('#1c4a34', '#3a8a58', '#78c88a'), iris='#ffc23a', blush='#f0a6a6', conch=('#9a5a6a', '#e8a8a0', '#fff0e0')),
    'maelstromheart': mk(deep=('#0e1236', '#26346c', '#4a68b0', '#8cacee'), swirl=('#4e6cb4', '#9ac0f4', '#e8f4ff'),
                         heart=('#6a2a8a', '#c070e0', '#f0b8ff', '#fff0ff'), spike=('#aab8d8', '#f0f4ff'),
                         iris='#8ce6ff', blush='#ff9ac8', foam='#d8f0ff'),
}
R.PALETTES.update(PALETTES)


def heart(a, x, y, w, name):
    """A little heart (two lobes and a point) in a flat colour."""
    a.poly([(x, y - w), (x - w * 1.1, y + w * .15), (x - w * .75, y + w * .8), (x, y + w * .3), (x + w * .75, y + w * .8),
            (x + w * 1.1, y + w * .15)], name, out=True)


# ------------------------------------------------------------------------------------------------
def saltclaw(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('saltclaw', clip, n, sy=1 - fall * .5)
    b = bob * .6
    cy = 22 + b - fall * 6
    # six little legs
    for k, lx in enumerate((-22, -14, -6, 6, 14, 22)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.3)) * 4 if clip == 'walk' else 0
        side = -1 if lx < 0 else 1
        a.c((lx * .6, cy - 3), (lx * 1.25 + side * 3, 4 + up), 2.6, 1.8, 'leg')
    # claws on short arms, the near one raised
    def claw(root, wrist, ang, op):
        a.c(root, wrist, 3.4, 3, 'claw')
        d = (math.cos(ang), math.sin(ang))
        p = (-d[1], d[0])
        for sg, r1 in ((-1, 2.2), (1, 3)):
            base = (wrist[0] + p[0] * sg * (1.4 + op * 3), wrist[1] + p[1] * sg * (1.4 + op * 3))
            tip = (wrist[0] + d[0] * 11 + p[0] * sg * (1.4 + op * 6), wrist[1] + d[1] * 11 + p[1] * sg * (1.4 + op * 6))
            a.c(base, tip, 4.8, r1, 'claw')
        a.e(wrist[0], wrist[1], 5.4, 5.4, 'claw')
    claw((-16, cy + 4), (-26 + sw, cy + 12 + wind * 2), 2.2, .3)
    nw = (lerp(lerp(21, 18, wind), 28, strike), lerp(lerp(cy + 12, cy + 30, wind), cy + 2, strike))
    if clip == 'die':
        nw = (lerp(21, 26, fall), lerp(cy + 12, 6, fall))
    claw((16, cy + 4), nw, lerp(lerp(.9, 1.15, wind), .1, strike), .6 + wind * .4 - strike * .5)
    # domed shell, salt crust crystals, belly rim
    a.e(0, cy + 2, 21, 15.4, 'shell')
    a.e(-6, cy + 9, 11, 4.6, 'shell', out=False)
    for k, (cx_, h) in enumerate(((-12, 8), (-3, 11), (7, 8), (14, 5))):
        a.poly([(cx_ - 3, cy + 10), (cx_ + .5, cy + 10 + h), (cx_ + 3.4, cy + 10)], 'salt1')
        a.line((cx_, cy + 11), (cx_ + .4, cy + 9 + h), 'salt2', 1)
    # eye stalks with big eyes
    for s, ex in ((-1, -7), (1, 7)):
        a.c((ex, cy + 12), (ex + s * 2, cy + 21 + wind * 3), 1.6, 1.4, 'shell')
        a.eye(ex + s * 2 + (1 if s > 0 else -1), cy + 25 + wind * 3, 4.4, iris='iris', look=(.5 + s * .3, .1))
    a.dot(-14, cy + 3, 'blush', 2)
    a.dot(14, cy + 3, 'blush', 2)
    mouth = max(wind * .5, strike) * 2
    a.line((-4, cy - 3 - mouth), (4, cy - 3 - mouth), 'mouth1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(nw[0] + 8 + k * 2, 38), nw[1] - 4 + k * 3, 'foam', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def stormgull(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('stormgull', clip, n, sy=1 - fall * .5)
    flap = math.sin(n * (math.pi / 3 if clip == 'idle' else math.pi / 2)) * 9
    if clip == 'attack':
        flap = (-4, -8, -12, 10, 12, 6, 2, 0)[n]
    if clip == 'hurt':
        flap = (-4, -2, 2, 4)[n]
    if fall:
        flap = lerp(flap, -10, fall)
    cy = 44 + bob * 1.3 - fall * 28
    # storm-cloud wings, far one first
    for s in (-1, 1):
        wk = 1 - fall * .3
        if s == 1:
            continue
        a.e(-22 * wk, cy + 4 + flap * .9, 20, 8.6, 'wing', ang=.35 + flap * .035)
        a.e(-20 * wk, cy + 4 + flap * .9, 12, 3.6, 'wing', ang=.35 + flap * .035, out=False)
    a.e(-8, cy - 4, 14, 10, 'plume')
    a.poly([(-14, cy - 7), (-26, cy - 18), (-20, cy - 4)], 'plume1')
    # tail feathers and feet
    a.c((-3, cy - 9), (-2, cy - 17), 1.2, 1, 'leg')
    a.c((4, cy - 9), (5, cy - 18 - (strike * 4)), 1.2, 1, 'leg')
    a.e(-1, cy - 18, 3.4, 1.4, 'leg')
    # round chest and head
    a.e(5, cy + 1, 15, 13, 'plume')
    a.e(1, cy - 6, 9, 4.6, 'plume', out=False)
    # near wing over the body
    a.e(-1, cy + 6 + flap * .8, 19 * (1 - fall * .3), 8, 'wing', ang=-.5 - flap * .035)
    a.e(-1, cy + 6 + flap * .8, 11, 3.2, 'wing', ang=-.5 - flap * .035, out=False)
    hx, hy = 9 + strike * 5 - wind * 3, cy + 16 - strike * 4
    a.e(hx, hy, 11, 10, 'plume')
    a.e(hx - 4, hy + 5, 6, 3, 'plume', out=False)
    a.poly([(hx + 7, hy + 1), (hx + 20 + strike * 2, hy - 2), (hx + 7, hy - 4 - max(wind * .4, strike) * 3)], 'beak1')
    a.line((hx + 8, hy - 1), (hx + 18, hy - 2), 'beak0', 1)
    a.eye(hx - 1.6, hy + 2, 4.4, iris='iris', look=(.7, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    # lightning bolts: crackling off the wing tips
    if clip in ('idle', 'walk') and n % 2 == 0:
        star(a, -28, cy + 16 + flap * .5, 2.2, 'bolt1')
    if clip == 'attack' and n in (3, 4, 5):
        bx = min(hx + 24, 38)
        pts = [(hx + 18, hy - 2), (hx + 22, hy + 3), (bx - 2, hy - 1), (bx + 2, hy - 7), (bx - 4, hy - 4)]
        a.poly([(bx - 6, hy + 4), (bx - 1, hy + 4), (bx - 3, hy - 1), (bx + 2, hy - 1), (bx - 6, hy - 12), (bx - 4, hy - 4), (bx - 8, hy - 4)], 'bolt0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def glassray(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('glassray', clip, n, sy=1 - fall * .45)
    flap = math.sin(n * (math.pi / 3 if clip == 'idle' else math.pi / 2)) * 8
    if clip == 'attack':
        flap = (-4, -8, -12, 10, 12, 6, 2, 0)[n]
    if fall:
        flap = lerp(flap, 0, fall)
    cy = 48 + bob * 1.2 - fall * 30
    wk = 1 - fall * .2
    # tail dangling behind
    a.c((0, cy - 10), (-6 + sw * 2, cy - 22 + fall * 10), 3, 1.6, 'tail')
    a.c((-6 + sw * 2, cy - 22), (-4 + sw * 3, cy - 32 + fall * 14), 1.6, .9, 'tail')
    # glass wings (fins) with flapping tips
    for s in (-1, 1):
        tip = (s * 40 * wk, cy + 2 + flap)
        a.band([(s * 4, cy + 10), (s * 20, cy + 14 + flap * .4), tip, (s * 30, cy - 8 + flap * .3), (s * 6, cy - 12)], 'glass')
        a.line((s * 8, cy), (tip[0] - s * 4, tip[1] - 1), 'edge1', 1)
        a.line((s * 10, cy + 8), (tip[0] - s * 8, tip[1] + 3), 'edge2', 1)
    # body: a rounded diamond with a glowing core
    a.e(0, cy, 17, 17, 'glass')
    a.e(-6, cy + 8, 9, 4.4, 'glass', out=False)
    a.poly([(0, cy - 7), (6, cy - 11), (0, cy - 17), (-6, cy - 11)], 'core1', out=True)
    a.eye(-5, cy + 3, 5, iris='iris', look=(.3, .1))
    a.eye(6.6, cy + 3, 4.6, iris='iris', look=(.8, .1))
    a.dot(-11, cy - 2, 'blush', 2)
    a.dot(13, cy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(min(14 + (n - 3) * 4 + k * 4, 38), cy - 6 + (k * 5) % 12, 'bubble', 2)
    if clip == 'idle':
        for k in range(3):
            a.dot(-22 + k * 20 + (n % 2) * 2, cy - 22 - ((n * 3 + k * 4) % 8), 'bubble', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def breakersentinel(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('breakersentinel', clip, n, sy=1 - fall * .5)
    b = bob * .5
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 9, 24), (s * 10, 6 + up), 6.4, 5.4, 'stone')
        a.e(s * 10.5, 4 + up, 8.4, 4.4, 'stone')
        a.dot(s * 10, 5 + up, 'barn1', 2)
    # far arm and a barnacled shield-shell
    a.c((-15, 40 + b), (-22, 30 + b + sw), 5, 4, 'stone')
    # torso: a tide-worn boulder with a foam stripe and barnacles
    a.e(0, 37 + b, 17, 15, 'stone')
    a.e(-6, 43 + b, 9, 4.4, 'stone', out=False)
    a.band([(-14, 36 + b), (14, 36 + b), (15, 32 + b), (-15, 32 + b)], 'foam', out=False)
    for k, (bx_, by_) in enumerate(((-9, 45), (4, 28), (10, 42), (-4, 26))):
        a.e(bx_, by_ + b, 2.6, 2.4, 'barn')
    # weed on the shoulder
    a.c((-12, 49 + b), (-17, 58 + b + sw), 1.4, 1, 'weed')
    a.e(-17, 59 + b + sw, 3.2, 2, 'weed', ang=.7)
    # conch hammer: a big shell on a driftwood haft
    hand = (lerp(lerp(21, 17, wind), 26, strike), lerp(lerp(34, 40, wind), 32, strike) + b)
    top = (min(hand[0] + lerp(lerp(2, -6, wind), 12, strike), 28), lerp(lerp(66, 72, wind), 36, strike))
    low = (hand[0] - 1, lerp(lerp(8, 12, wind), 31, strike))
    if clip == 'die':
        hand = (lerp(21, 28, fall), lerp(34, 8, fall))
        top = (lerp(22, 30, fall), lerp(66, 10, fall))
        low = (lerp(20, 8, fall), 4)
    a.line(low, top, 'ink', 4)
    a.line(low, top, 'gold1', 2)
    a.e(top[0] + 3, top[1] + 2, 11, 8.6, 'conch', ang=.4)
    a.e(top[0] + 6, top[1] + 4, 4, 3.4, 'conch', out=False)
    for k in range(3):
        a.line((top[0] - 3 + k * 4, top[1] + 8 - k), (top[0] + 2 + k * 4, top[1] - 4), 'conch0', 1)
    a.c((10, 44 + b), hand, 5, 4.4, 'stone')
    a.e(hand[0], hand[1], 4.4, 4.2, 'stone')
    # head: a rounded rock with a wave crest and golden eyes
    hx, hy = 1 + strike * 2, 58 + b
    a.poly([(hx - 8, hy + 8), (hx - 4, hy + 20), (hx + 2, hy + 12), (hx + 6, hy + 21), (hx + 9, hy + 8)], 'foam1')
    a.e(hx, hy, 13, 11.6, 'stone')
    a.e(hx - 5, hy + 6, 7, 3.6, 'stone', out=False)
    a.eye(hx - 4.4, hy - 1, 4.8, iris='iris', look=(.3, .1))
    a.eye(hx + 6.6, hy - 1, 4.4, iris='iris', look=(.8, .1))
    a.dot(hx - 10, hy - 5, 'blush', 2)
    a.dot(hx + 11.4, hy - 5, 'blush', 2)
    a.line((hx - 2, hy - 7), (hx + 5, hy - 7 - strike), 'ink', 1)
    a.e(hx - 8, hy + 5, 2.6, 2.2, 'barn')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(top[0] + 12 + k * 3, 38), top[1] - 6 + k * 3, 'foam2', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def maelstromheart(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('maelstromheart', clip, n, sy=1 - fall * .4)
    a.pk = .93
    cy = 46 + bob * 1.4 - fall * 24
    flare = max(wind, strike)
    spin = n * (math.pi / 6 if clip in ('idle', 'walk') else math.pi / 3)
    # ring of spiny fins around the whirlpool
    for k in range(10):
        ang = spin * .5 + k * 2 * math.pi / 10
        r = 29 + flare * 3 - fall * 6
        x, y = math.cos(ang) * r, cy + math.sin(ang) * r * .8
        a.poly([(x - 4, y - 2), (x + math.cos(ang) * 8, y + math.sin(ang) * 8), (x + 4, y + 2)], 'spike1')
    # the dark whirlpool body with spiral bands
    a.e(0, cy, 24, 23, 'deep')
    a.e(-9, cy + 11, 11, 5, 'deep', out=False)
    for k in range(6):
        th = spin + k * math.pi / 3
        for j in range(5):
            tt = th + j * .5
            rr = 8 + j * 3.2
            a.dot(math.cos(tt) * rr, cy + math.sin(tt) * rr * .94, 'swirl1' if j % 2 else 'swirl2', 2)
    # the glowing heart in the eye of the storm
    pulse = 1 + .14 * math.sin(n * .9) + flare * .2
    heart(a, 0, cy - 3, 9 * pulse, 'heart1')
    a.poly([(-4, cy), (0, cy - 6 * pulse), (-1, cy + 1)], 'heart3', out=False)
    # eyes above the heart and a calm brow
    state = T['state']
    for ex in (-9, 9):
        a.eye(ex, cy + 11, 4.4, iris='iris', look=(.4 * (1 if ex > 0 else .5), .1))
    a.dot(-15, cy + 4, 'blush', 2)
    a.dot(15, cy + 4, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(6):
            a.e(min(26 + k * 2 + (n - 3) * 2, 40), cy - 8 + k * 4 - 8 + (k % 2) * 3, 2.2, 2.2, 'swirl', out=False)
    if clip == 'idle':
        for k in range(3):
            a.dot(-30 + k * 28 + (n % 2) * 2, cy - 26 + ((n * 3 + k * 4) % 8), 'foam', 1)
    return a.done()


DRAW = dict(saltclaw=saltclaw, stormgull=stormgull, glassray=glassray, breakersentinel=breakersentinel,
            maelstromheart=maelstromheart)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/stormglass-preview')
    print('ok')
