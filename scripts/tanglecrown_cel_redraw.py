"""Cel-shaded Tanglecrown enemies (zone 22) for make_tanglecrown_sprites.py.

Same recipe as ribbonwild_cel_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the three warden/scholar/travel NPCs keep their old art).
`python3 scripts/tanglecrown_cel_redraw.py [kind...]` writes contact sheets to test-results/tanglecrown-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, diamond, preview, star, timing

KINDS = ('orchidmantis', 'canopyglider', 'poolcaiman', 'drumgorilla', 'jadeanaconda', 'crownjaguar')

PALETTES = {
    'orchidmantis': mk(body=('#1c5a2c', '#38a04a', '#82dc5e', '#d8ff9a'), petal=('#9a2a6a', '#e458a4', '#ff96cc', '#ffd8ee'),
                       petal2=('#b8a21c', '#f0dc4c', '#fff6a0'), leg=('#1a4a28', '#2e7a3c', '#58b058'),
                       claw=('#b8b090', '#f4f0d0'), iris='#e4408a', blush='#ff8ab8'),
    'canopyglider': mk(fur=('#1c5a6a', '#38a0a0', '#72dcc0', '#c8fff0'), wing=('#a8601c', '#eea04c', '#ffd088', '#fff0c8'),
                       belly=('#c8e4b0', '#f4ffe0'), tail=('#14485a', '#2a7a88', '#4cb8b0'), iris='#2a3a8a',
                       blush='#ff8ab8', nose='#e86a7a'),
    'poolcaiman': mk(skin=('#14382c', '#2a7058', '#52b088', '#a8ecb8'), belly=('#b8d490', '#f2f8c8'),
                     tooth=('#d8d0b8', '#fffcf0'), eyeg=('#a8841a', '#f6d84a'), iris='#1a2030', mouth=('#5a1c34', '#e85a78'),
                     blush='#ff8ab8', scute=('#143a32', '#3a8a68')),
    'drumgorilla': mk(fur=('#2a2430', '#5c4a58', '#8e7080', '#c4a4aa'), skin=('#7a5a4a', '#b8876a', '#e8b896'),
                      drum=('#6a2a1c', '#b0522c', '#e88a4a', '#ffc080'), skin2=('#e8d8b8', '#fff6dc'),
                      gold=('#a8741a', '#f4c448', '#fff0a0'), stick=('#a87a4a', '#e8c890'), iris='#2a6a4a',
                      blush='#ff8a8a', mouth=('#4a1830', '#e85a78')),
    'jadeanaconda': mk(scale=('#0e4438', '#1c9068', '#3ed49a', '#a0ffd0'), belly=('#c8e8a0', '#fff6c0', '#ffffe8'),
                       mark=('#0a3028', '#146a50'), gold=('#a8741a', '#f4c448', '#fff0a0'), iris='#f2a82e',
                       tongue=('#a82a4a', '#ff6a8a'), blush='#ff8ab8', fang=('#d8d0b8', '#fffcf0')),
    'crownjaguar': mk(fur=('#8a4a14', '#e08a2a', '#f6b254', '#ffe098'), spot=('#2a1a14', '#5a3420'),
                      belly=('#e8d4a8', '#fff4d8'), leaf=('#14663a', '#34b45a', '#92ec86', '#e0ffc0'),
                      gold=('#a8741a', '#f4c448', '#fff0a0'), claw=('#c8b888', '#fff6d8'), iris='#3aa05a',
                      blush='#ff8a8a', mouth=('#4a1830', '#e85a78'), nose='#e86a7a'),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def orchidmantis(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('orchidmantis', clip, n, sy=1 - fall * .5)
    a.pk = .92
    cy = 36 + bob * .6 - fall * 10
    # four stick legs
    for k, lx in enumerate((-9, -3, 4, 10)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        a.c((lx * .6, cy - 8), (lx * 1.5 + (-3 if lx < 0 else 3), 3 + up), 2.2, 1.4, 'leg')
    # petal-wing fans behind the back: orchid pink and gold
    flap = math.sin(n * math.pi / 3) * 2.5 if clip == 'idle' else (sw * 2 if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-2, -4, -6, 3, 4, 2, 1, 0)[n]
    for k, (gx, grp, ang) in enumerate(((-15, 'petal', -.5), (-8, 'petal2', -.2), (-21, 'petal2', -.8))):
        a.e(gx, cy + 12 + flap + k, 6.4, 16 - k, grp, ang=ang)
    a.e(-14, cy + 14 + flap, 3, 10, 'petal', ang=-.5, out=False)
    # slim abdomen and thorax
    a.e(-6, cy + 1, 13, 7.6, 'body')
    a.e(-8, cy - 3, 7, 3, 'body', out=False)
    a.e(5, cy + 8, 8, 12, 'body', ang=-.15)
    # scythe forelegs, the near one sweeps
    far = (lerp(12, 14, wind), cy + 14)
    a.c((7, cy + 12), (14, cy + 22), 2.4, 1.8, 'body')
    a.c((14, cy + 22), (20, cy + 10), 1.8, 1, 'claw')
    hand = (lerp(lerp(21, 17, wind), 30, strike), lerp(lerp(cy + 8, cy + 30, wind), cy - 4, strike))
    if clip == 'die':
        hand = (lerp(21, 24, fall), lerp(cy + 8, 6, fall))
    a.c((8, cy + 16), (hand[0] - 3, hand[1] + 9), 2.6, 2, 'body')
    a.c((hand[0] - 3, hand[1] + 9), hand, 2, 1.1, 'claw')
    a.poly([(hand[0] - 3, hand[1] + 9), (hand[0] + 3, hand[1] + 4), (hand[0], hand[1] - 3)], 'claw1', out=False)
    # triangle head with huge eyes and orchid lip petals
    hx, hy = 6 + strike * 3 - wind, cy + 28 - strike * 2
    a.c((hx - 2, hy + 12), (hx - 5 + sw, hy + 23), 1, .7, 'leg')
    a.c((hx + 3, hy + 12), (hx + 6 + sw, hy + 22), 1, .7, 'leg')
    a.e(hx, hy + 5, 10.4, 9, 'body')
    a.e(hx - 3, hy + 9, 5.6, 3, 'body', out=False)
    a.eye(hx - 3.6, hy + 7, 4.4, iris='iris', look=(.5, .1))
    a.eye(hx + 5.4, hy + 6.6, 3.6, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy + 3, 'blush', 2)
    jaw = max(wind * .5, strike) * 2
    a.e(hx + 1, hy - 1 - jaw, 3.4, 2 + jaw, 'petal')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hand[0] + 5 + k * 2, 40), hand[1] - 4 + k * 4, 1.6, 2.6, 'petal2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def canopyglider(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('canopyglider', clip, n, sy=1 - fall * .5)
    a.ox = 0
    a.pk = .9
    hover = (math.sin(n * math.pi / 3) * 2 + 3 if clip == 'idle' else
             abs(math.sin(n * math.pi / 4 + .3)) * 4 + 2 if clip == 'walk' else 4 if clip != 'die' else 0)
    a.lift = hover * (1 - fall)
    cy = 32 - fall * 8
    # big bushy tail with rings
    a.c((-12, cy - 2), (-28, cy + 8 + sw * 3), 6.4, 4, 'tail')
    a.c((-28, cy + 8 + sw * 3), (-36, cy + 20 + sw * 4), 4, 2.4, 'tail')
    for k in range(3):
        a.dot(-18 - k * 5, cy + 2 + k * 5 + sw * k, 'fur0', 2)
    # gliding membranes spread like a cape, one each side of the body
    flap = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else (sw * 3 if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-2, -4, -7, 5, 6, 3, 1, 0)[n]
    a.band([(-4, cy + 8), (-30 + flap, cy + 20), (-34, cy - 4 + flap), (-14, cy - 8)], 'wing')
    a.band([(4, cy + 6), (30 - flap, cy + 18), (36, cy - 8 - flap), (12, cy - 10)], 'wing')
    a.line((-14, cy + 6), (-33, cy + 1 + flap), 'wing0', 1)
    a.line((14, cy + 4), (34, cy - 3 - flap), 'wing0', 1)
    # round fluffy body with a pale belly
    a.e(0, cy + 6, 14.6, 15, 'fur')
    a.e(3, cy + 2, 8, 9.6, 'belly', out=False)
    # tiny clutching feet
    for s in (-1, 1):
        a.c((s * 6, cy - 6), (s * 8 + strike * 4 * (s > 0), cy - 12 - strike * 2), 2.4, 1.8, 'fur')
    # head with huge ears and eyes
    hx, hy = 3 + strike * 4 - wind * 2, cy + 26
    for s, ex in ((-1, -7), (1, 6)):
        a.e(hx + ex, hy + 9, 3.6, 6.4, 'fur', ang=s * .25)
        a.e(hx + ex, hy + 9, 1.8, 3.8, 'belly', out=False, ang=s * .25)
    a.e(hx, hy, 12.4, 10.6, 'fur')
    a.e(hx - 4, hy + 4, 6.6, 3.2, 'fur', out=False)
    a.e(hx + 5, hy - 3, 6.2, 4.6, 'belly')
    a.dot(hx + 9, hy - 2, 'nose', 2)
    a.eye(hx - 2.8, hy + 2.4, 4.6, iris='iris', look=(.6, .1))
    a.eye(hx + 6, hy + 2.4, 3.8, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 2, 'blush', 2)
    jaw = max(wind * .5, strike) * 2
    a.line((hx + 3, hy - 6 - jaw), (hx + 8, hy - 6 - jaw), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 14 + k * 3, 40), hy - 2 + k * 3 - 4, 1.6, 2.6, 'wing2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def poolcaiman(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('poolcaiman', clip, n, sy=1 - fall * .5)
    a.ox = -5
    cy = 17 + bob * .4 - fall * 4
    lunge = strike * 3 - wind * 2
    # stubby legs
    for k, lx in enumerate((-16, -6, 10, 20)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 3 if clip == 'walk' else 0
        a.c((lx * .9, cy - 1), (lx + 3 + (lunge * .5 if k > 1 else 0), 2 + up), 3.6, 2.6, 'skin')
        for t in (-1, 0, 1):
            a.dot(lx + 3 + t * 2 + (lunge * .5 if k > 1 else 0), 1 + up, 'tooth0', 1)
    # long ridged tail
    wav = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else sw * 4
    a.c((-24, cy + 2), (-31, cy + 5 + wav * .5), 6, 3.4, 'skin')
    a.c((-31, cy + 5 + wav * .5), (-35, cy + 10 + wav), 3.4, 1.4, 'skin')
    # body with a pale belly and scute ridge
    a.e(-4, cy + 3, 26, 11, 'skin')
    a.e(2, cy - 5, 16, 4.6, 'belly', out=False)
    for k in range(7):
        a.e(-20 + k * 6, cy + 13 - abs(k - 3) * .5, 2.4, 3, 'scute')
    # long snout with teeth, big gold eyes on top
    hx, hy = 24 + lunge, cy + 8 - wind * 2
    jaw = max(wind * .8, strike * 1.2) * 4
    a.e(hx + 8, hy - 3 - jaw * .5, 11.4, 4.6 + jaw * .4, 'skin')
    a.e(hx + 8, hy - 6 - jaw, 9.6, 3.2, 'belly', out=False)
    for k in range(4):
        a.poly([(hx + 5 + k * 5, hy - 5 - jaw * .8), (hx + 7 + k * 5, hy - 5 - jaw * .8), (hx + 6 + k * 5, hy - 8 - jaw * .8)],
               'tooth1', out=False)
    a.e(hx, hy + 2, 11, 9, 'skin')
    a.e(hx - 3, hy + 6, 5.6, 3, 'skin', out=False)
    a.eye(hx - 1, hy + 8, 4, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 1, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 25 + k * 2, 40), hy - 4 + k * 3, 2, 'tooth1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def drumgorilla(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('drumgorilla', clip, n, sy=1 - fall * .5)
    a.pk = .88
    b = bob * .6
    # short bowed legs
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 9, 24), (s * 11, 5 + up), 6, 5, 'fur')
        a.e(s * 12 + 2, 3.6 + up, 8, 3.6, 'skin')
    # big barrel torso with a pale chest
    a.e(0, 36 + b, 22, 18, 'fur')
    a.e(2, 33 + b, 12, 12, 'skin2', out=False)
    a.e(-12, 44 + b, 10, 6, 'fur', out=False)
    # the drum: a barrel slung at the waist
    dx, dy = 0, 20 + b - fall * 4
    a.e(dx, dy, 15, 9, 'drum')
    a.e(dx, dy + 6, 15, 4, 'skin2')
    a.line((dx - 14, dy - 3), (dx + 14, dy - 3), 'gold1', 1)
    a.line((dx - 14, dy + 2), (dx + 14, dy + 2), 'gold1', 1)
    # arms: far arm drums, near arm raises and slams
    far = (-27 + sw, 24 + b + abs(sw) * 4)
    a.c((-14, 46 + b), far, 7, 5.4, 'fur')
    a.e(far[0], far[1], 6.4, 5.4, 'skin')
    near = (lerp(lerp(26, 22, wind), 22, strike), lerp(lerp(26, 62, wind), 22, strike) + b)
    if clip == 'die':
        near = (lerp(26, 30, fall), lerp(26, 6, fall))
    a.c((14, 46 + b), near, 7.4, 5.8, 'fur')
    a.e(near[0], near[1], 7, 6, 'skin')
    a.line((near[0] + 2, near[1] + 6), (near[0] + 9, near[1] + 14 - strike * 10), 'stick0', 2)
    a.line((near[0] + 2, near[1] + 6), (near[0] + 9, near[1] + 14 - strike * 10), 'stick1', 1)
    # head: heavy brow, big eyes, flat muzzle, gold nose ring
    hx, hy = 3 + strike * 3 - wind, 58 + b
    a.e(hx, hy, 13.6, 12.4, 'fur')
    a.e(hx - 4, hy + 6, 7, 3.4, 'fur', out=False)
    a.e(hx + 2, hy - 5, 9.4, 6.4, 'skin')
    a.eye(hx - 3.4, hy + 1.4, 4, iris='iris', look=(.5, .1))
    a.eye(hx + 6.4, hy + 1.4, 3.6, iris='iris', look=(.9, .1))
    a.dot(hx - 9, hy - 3, 'blush', 2)
    jaw = max(wind * .4, strike) * 2
    a.e(hx + 2, hy - 8 - jaw, 5, 2 + jaw, 'mouth')
    a.e(hx + 7, hy - 4, 1.6, 1.6, 'gold')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(near[0] + 8 + k * 3, 40), near[1] - 4 + k * 4, 2.4, 'gold1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def jadeanaconda(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('jadeanaconda', clip, n, sy=1 - fall * .5)
    a.ox = -6
    a.pk = .9
    b = bob * .5
    # stacked coils, widest at the bottom
    for k, (cx, cyy, rx, ry) in enumerate(((-6, 8, 30, 8.6), (-1, 18, 25, 8), (-4, 28, 19, 7.6))):
        a.e(cx + (sw * 1.4 if k == 1 else 0), cyy - fall * 3, rx * (1 + fall * .1), ry, 'scale')
        a.e(cx + 2, cyy - ry * .5 - fall * 3, rx * .8, ry * .42, 'belly', out=False)
        for j in range(5):
            a.dot(cx - rx * .7 + j * rx * .35, cyy + ry * .5 - fall * 3, 'mark0', 2)
    # tail tip curling out at the bottom-left
    a.c((-26, 6), (-38, 4 + sw * 2), 5, 1.4, 'scale')
    # the rearing neck, an S-curve up to the head
    wav = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else sw * 2
    hx = 8 + strike * 9 - wind * 6 + wav
    hy = 54 + b - wind * 4 - strike * 14 - fall * 28
    a.c((-4, 30), (-8 + wav, 40), 8, 7.4, 'scale')
    a.c((-8 + wav, 40), (hx - 6, hy - 8), 7.4, 7, 'scale')
    a.c((-8 + wav, 40), (hx - 6, hy - 8), 3, 3, 'belly', out=False)
    for j in range(3):
        a.dot(-8 + wav * .6 + j * 2, 44 + j * 4, 'mark1', 2)
    # head: broad, glossy eyes, gold crown ring and a forked tongue
    a.e(hx, hy, 13.4, 10.6, 'scale')
    a.e(hx - 4, hy + 4, 7, 3.2, 'scale', out=False)
    a.e(hx + 9, hy - 3, 7, 5, 'belly')
    a.eye(hx - 2, hy + 3, 4.6, iris='iris', look=(.8, .1))
    a.eye(hx + 8, hy + 2.4, 3.4, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 2, 'blush', 2)
    a.line((hx - 7, hy + 10), (hx + 5, hy + 12), 'gold1', 2)
    a.e(hx - 1, hy + 13, 2, 2, 'gold')
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 5, hy - 5 - jaw), (hx + 15, hy - 5 - jaw), 'ink', 1)
    tl = 7 + strike * 5
    a.line((hx + 14, hy - 4 - jaw), (hx + 14 + tl, hy - 4 - jaw), 'tongue1', 1)
    a.line((hx + 14 + tl, hy - 4 - jaw), (hx + 16 + tl, hy - 2 - jaw), 'tongue1', 1)
    a.line((hx + 14 + tl, hy - 4 - jaw), (hx + 16 + tl, hy - 6 - jaw), 'tongue1', 1)
    if jaw > 1.5:
        a.poly([(hx + 9, hy - 5 - jaw), (hx + 11, hy - 5 - jaw), (hx + 10, hy - 9 - jaw)], 'fang1', out=False)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 20 + k * 3, 40), hy - 4 + k * 4, 1.6, 2.6, 'gold1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def crownjaguar(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('crownjaguar', clip, n, sy=1 - fall * .5)
    a.ox = -5
    a.pk = .92
    cy = 30 + bob * .5 - fall * 10
    pounce = strike * 8 - wind * 4
    # hind legs and a long ringed tail
    for k, lx in enumerate((-20, -11)):
        up = max(0, math.sin(n * math.pi / 2 + k * 2)) * 4 if clip == 'walk' else 0
        a.c((lx, cy - 3), (lx, 4 + up), 6.6, 4.6, 'fur')
        a.e(lx + 1, 3 + up, 5.6, 2.8, 'fur')
    a.c((-26, cy + 5), (-34, cy + 14 + sw * 2), 3.4, 2.4, 'fur')
    a.c((-34, cy + 14 + sw * 2), (-32, cy + 26 + sw * 3), 2.4, 2.4, 'fur')
    for k in range(3):
        a.dot(-31 - k, cy + 12 + k * 4 + sw * k, 'spot0', 2)
    # body with spots and belly
    a.e(-8, cy + 2, 23, 14, 'fur')
    a.e(-5, cy - 6, 16, 4.6, 'belly', out=False)
    for k, (sx, sy) in enumerate(((-18, 6), (-10, 9), (-2, 5), (-14, -1), (-5, 0), (3, 8))):
        a.e(sx, cy + sy, 2.6, 2.6, 'spot', out=False)
    # front legs, the near one raised for the swipe
    a.c((4, cy - 1), (6, 5), 5.6, 4.2, 'fur')
    a.e(8, 3.6, 5, 2.6, 'fur')
    hand = (lerp(lerp(14, 11, wind), 26, strike), lerp(lerp(8, 28, wind), 8, strike))
    if clip == 'die':
        hand = (lerp(14, 22, fall), lerp(8, 4, fall))
    a.c((8, cy + 2), hand, 6, 4.6, 'fur')
    for k in range(3):
        a.c((hand[0] + 1, hand[1]), (hand[0] + 6, hand[1] - 3 + k * 1.8), 1.6, .9, 'claw')
    # head with a crown of leaves, round ears and a big expressive face
    hx, hy = 14 + pounce, cy + 21 - strike * 3
    a.e(hx - 5, hy + 9, 3.8, 3.6, 'fur')
    a.e(hx + 4, hy + 10, 3.8, 3.6, 'fur')
    a.e(hx, hy, 13.4, 11.4, 'fur')
    a.e(hx - 4, hy + 5, 7, 3.4, 'fur', out=False)
    a.e(hx + 6, hy - 4, 7.4, 5.2, 'belly')
    a.dot(hx + 11, hy - 3, 'nose', 2)
    a.eye(hx - 1.6, hy + 2.6, 4.8, iris='iris', look=(.8, .1))
    a.eye(hx + 7.6, hy + 2.4, 3.8, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 2, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.e(hx + 6, hy - 8 - jaw, 3.6, 1.6 + jaw * .6, 'mouth')
    for k, dx in enumerate((-8, -3, 2, 7)):
        tip = (hx + dx + sw * .4 * (k - 1.5), hy + 17 + (k % 2) * 3)
        a.band([(hx + dx - 2.6, hy + 9), tip, (hx + dx + 2.6, hy + 9)], 'leaf')
    a.e(hx - 1, hy + 11, 10, 2.4, 'gold')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(hand[0] + 8 + k * 2, 40), hand[1] - 6 + (k * 5) % 12, 2.2, 'gold1')
    return a.done()


DRAW = dict(orchidmantis=orchidmantis, canopyglider=canopyglider, poolcaiman=poolcaiman, drumgorilla=drumgorilla,
            jadeanaconda=jadeanaconda, crownjaguar=crownjaguar)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/tanglecrown-preview')
    print('ok')
