"""Cel-shaded Lapis Erg enemies (zone 25) for make_lapis_sprites.py.

Same recipe as tanglecrown_cel_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the five lapis_* NPCs keep their old art).
`python3 scripts/lapis_cel_redraw.py [kind...]` writes contact sheets to test-results/lapis-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp
from cel_zone_common import ROOT, diamond, mku as mk, preview, star, timing

KINDS = ('sandhopper', 'dunefennec', 'glassscorpion', 'sunvulture', 'dunecolossus', 'mirageroc')

PALETTES = {
    'sandhopper': mk(fur=('#7a4a28', '#c98a4a', '#eab872', '#fff0c0'), belly=('#e8d4a8', '#fff8e0'),
                     tail=('#6a3a22', '#b4743c', '#e0a460'), tuft=('#1c6a7a', '#38b0b0', '#9af0e0'),
                     iris='#2a3a8a', blush='#ff8a8a', nose='#e8607a', tooth='#fffcf0'),
    'dunefennec': mk(fur=('#8a4a2a', '#d88a52', '#f7bc84', '#ffe8c0'), ear=('#e07a8a', '#ffb4bc'),
                     belly=('#f4e4c8', '#fffaee'), mask=('#6a3a22', '#a8683c'), iris='#1a3a7a', blush='#ff8a8a',
                     nose='#2a1a1c', collar=('#1c6a7a', '#38b0b0', '#9af0e0'), mouth=('#4a1830', '#e85a78')),
    'glassscorpion': mk(shell=('#14507a', '#2a8cb4', '#6ed4e8', '#d0f8ff'), glow=('#a8741a', '#f4b43c', '#fff0a0'),
                        claw=('#0e4066', '#2478a0', '#52c0dc'), leg=('#0c3a5c', '#2a7ca0'),
                        sand=('#c8a068', '#f0d498'), iris='#e8a020', blush='#ff8ab8', mouth=('#4a1830', '#e85a78')),
    'sunvulture': mk(feather=('#4a2a3a', '#8a5a58', '#c8987a', '#f2d4a8'), skin=('#a8503a', '#e08a58', '#ffc890'),
                     ruff=('#b8a890', '#f4ecd8', '#fffcf0'), beak=('#a8741a', '#f4c448', '#fff0a0'),
                     claw=('#6a5a58', '#a89a98'), sun=('#b8821a', '#ffd24a', '#fff4a8'), iris='#1c3a8a',
                     blush='#ff8a8a', leg=('#8a5a48', '#cc9c7e')),
    'dunecolossus': mk(sand=('#6a4430', '#b88050', '#e2b076', '#fff0c8'), stone=('#4a3a40', '#8a6a68', '#c0a090'),
                       lapis=('#142a78', '#2a5ac8', '#5a96f0', '#c0dcff'), gold=('#a8741a', '#f4c448', '#fff0a0'),
                       iris='#7ae0ff', fist=('#7a5438', '#c48c58', '#f0c088'), mouth=('#2a1a2c', '#5a3a58'),
                       blush='#ff8a8a'),
    'mirageroc': mk(feather=('#1c4a6a', '#3a86a8', '#7acce0', '#d4f8ff'), body=('#a8741a', '#e8b84a', '#fcdf86', '#fff6c8'),
                    shimmer=('#7a2a8a', '#c864d0', '#ffa8f0'), beak=('#a8741a', '#f4c448', '#fff0a0'),
                    claw=('#6a5a58', '#c8b898'), iris='#c8407a', blush='#ff8ab8', crest=('#d86a1c', '#ffb050', '#fff0a0')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def sandhopper(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('sandhopper', clip, n, sy=1 - fall * .5)
    a.ox = -3
    a.pk = .94
    hop = (math.sin(n * math.pi / 4 + .4) * .5 + .5) * 8 if clip == 'walk' else (bob * .7 if clip == 'idle' else 0)
    a.lift = hop * (1 - fall)
    cy = 22 - fall * 5
    # long tail with a tuft
    a.c((-14, cy), (-26, cy + 8 + sw * 3), 3.4, 1.4, 'tail')
    a.e(-28, cy + 10 + sw * 3, 4, 5, 'tuft')
    # big hind legs
    a.c((-8, cy + 3), (-5, 4), 9, 4.6, 'fur')
    a.e(-2, 3, 9, 3.6, 'fur')
    a.e(0, 3, 4, 1.8, 'belly', out=False)
    # round body and belly
    a.e(0, cy + 7, 15, 13, 'fur')
    a.e(5, cy + 4, 8, 9, 'belly', out=False)
    # tiny front paws
    a.c((8, cy + 2), (13 + strike * 6, cy - 4 + wind * 4), 2.6, 1.8, 'fur')
    # head with huge ears
    hx, hy = 9 + strike * 5 - wind * 2, cy + 20
    for s, ex in ((-1, -5), (1, 3)):
        a.e(hx + ex, hy + 13, 3.2, 9, 'fur', ang=s * .18)
        a.e(hx + ex, hy + 13, 1.6, 6, 'belly', out=False, ang=s * .18)
    a.e(hx, hy, 11.6, 10, 'fur')
    a.e(hx - 4, hy + 4, 6, 3, 'fur', out=False)
    a.e(hx + 5, hy - 3, 6, 4.6, 'belly')
    a.dot(hx + 9, hy - 1, 'nose', 2)
    a.eye(hx - 2, hy + 2.4, 4.4, iris='iris', look=(.7, .1))
    a.eye(hx + 6, hy + 2.4, 3.6, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 2, 'blush', 2)
    jaw = max(wind * .5, strike) * 2
    if jaw > 1:
        a.dot(hx + 6, hy - 6 - jaw, 'tooth', 2)
    else:
        a.line((hx + 3, hy - 6), (hx + 8, hy - 6), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 14 + k * 3, 40), hy - 2 + k * 3 - 4, 1.6, 2.6, 'tuft1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def dunefennec(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('dunefennec', clip, n, sy=1 - fall * .5)
    a.ox = -6
    a.pk = .94
    cy = 20 + bob * .5 - fall * 5
    lunge = strike * 6 - wind * 3
    # four legs
    for k, lx in enumerate((-16, -8, 8, 15)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        a.c((lx * .9, cy - 1), (lx + 2 + (lunge if k > 1 else 0), 3 + up), 3.6, 2.6, 'fur')
        a.e(lx + 3 + (lunge if k > 1 else 0), 2 + up, 3.8, 1.8, 'belly')
    # bushy tail
    a.c((-18, cy + 4), (-30, cy + 8 + sw * 3), 4.6, 4, 'fur')
    a.e(-31, cy + 8 + sw * 3, 4, 4.6, 'belly')
    # body and chest
    a.e(-3, cy + 4, 20, 11, 'fur')
    a.e(3, cy - 4, 12, 4.6, 'belly', out=False)
    # head with enormous ears
    hx, hy = 17 + lunge, cy + 14 - wind * 2
    for s, ex, ang in ((-1, -5, -.25), (1, 3, .22)):
        a.e(hx + ex, hy + 17, 4.6, 13, 'fur', ang=ang)
        a.e(hx + ex, hy + 17, 2.4, 9.6, 'ear', out=False, ang=ang)
    a.c((hx - 4, hy - 6), (hx - 6, hy - 11), 4, 3, 'collar')
    a.e(hx, hy, 12.4, 9.6, 'fur')
    a.e(hx - 4, hy + 4, 6.6, 3, 'fur', out=False)
    a.e(hx + 7, hy - 3, 7.4, 4.6, 'belly')
    a.dot(hx + 12, hy - 1, 'nose', 3)
    a.eye(hx - 1.8, hy + 2.6, 4.8, iris='iris', look=(.8, .1))
    a.eye(hx + 7, hy + 2.4, 3.8, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 2, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.e(hx + 7, hy - 6 - jaw, 3.4, 1.4 + jaw * .6, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 17 + k * 3, 40), hy - 4 + k * 3, 2, 'collar2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def glassscorpion(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('glassscorpion', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .92
    cy = 17 + bob * .4 - fall * 4
    # eight-ish legs
    for k, lx in enumerate((-12, -4, 4, 12)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.5)) * 3 if clip == 'walk' else 0
        a.c((lx * .8, cy), (lx * 1.4 - 2, 3 + up), 2.4, 1.4, 'leg')
        a.c((lx * .8, cy), (lx * 1.4 + 8, 3 + up), 2.4, 1.4, 'leg')
    # curled tail rising over the back to a glowing stinger
    tl = wind * 5 - strike * 8
    pts = [(-14, cy + 4), (-24, cy + 12), (-26, cy + 26 + tl * .3), (-14, cy + 36 + tl * .5), (-2, cy + 34 + tl)]
    for i in range(len(pts) - 1):
        a.c(pts[i], pts[i + 1], 4.4 - i * .5, 3.8 - i * .5, 'shell')
    a.e(pts[-1][0] + 1, pts[-1][1] - 2, 3.8, 3.8, 'glow')
    a.poly([(pts[-1][0] - 1, pts[-1][1] - 5), (pts[-1][0] + 3, pts[-1][1] - 11), (pts[-1][0] + 5, pts[-1][1] - 4)], 'glow1', out=True)
    # glassy body with a bright core
    a.e(-4, cy + 4, 21, 12.4, 'shell')
    a.e(-8, cy + 9, 11, 3.6, 'shell', out=False)
    a.e(-4, cy + 3, 6, 5.6, 'glow', out=False)
    for k in range(4):
        a.line((-16 + k * 7, cy + 12), (-14 + k * 7, cy - 4), 'shell0', 1)
    # pincers
    far = (lerp(28, 24, wind), cy + 6)
    a.c((12, cy + 5), (22, cy + 10), 3.4, 3, 'claw')
    a.e(26, cy + 11, 6.4, 5, 'claw')
    hand = (lerp(lerp(26, 22, wind), 32, strike), lerp(lerp(cy + 2, cy + 16, wind), cy - 2, strike))
    if clip == 'die':
        hand = (lerp(26, 28, fall), lerp(cy + 2, 6, fall))
    a.c((10, cy + 2), hand, 3.6, 3.2, 'claw')
    a.e(hand[0] + 3, hand[1] + 1, 6.6, 5.2, 'claw')
    a.line((hand[0] + 4, hand[1] + 1), (hand[0] + 9, hand[1] - 1 + strike * 2), 'ink', 1)
    # head peeking out front: big eyes on stalks
    hx, hy = 14 + strike * 2, cy + 13
    a.e(hx, hy, 8.4, 6.4, 'shell')
    a.eye(hx - 1, hy + 4, 3.8, iris='iris', look=(.8, .1))
    a.eye(hx + 6, hy + 3.6, 3.2, iris='iris', look=(.9, .1))
    a.dot(hx - 6, hy - 1, 'blush', 2)
    jaw = max(wind * .5, strike) * 2
    a.e(hx + 3, hy - 3 - jaw * .3, 2.8, 1.2 + jaw * .5, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hand[0] + 10 + k * 2, 40), hand[1] - 4 + k * 3, 2, 'glow1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def sunvulture(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('sunvulture', clip, n, sy=1 - fall * .5)
    a.ox = -3
    a.pk = .9
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-4, -9, -14, 8, 10, 4, 1, 0)[n]
    cy = 34 + b - fall * 9
    # tail feathers
    for k in range(3):
        a.c((-6, cy - 6), (-20 - k * 2 + sw, 8 + k * 3), 4, 1.8, 'feather')
    # legs and talons
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 4 - 2, cy - 10), (s * 5 - 1, 5 + up), 2.2, 1.8, 'leg')
        a.e(s * 5 + 2, 3 + up, 4.4, 1.8, 'claw')
    # hunched body
    a.e(-2, cy, 15, 15, 'feather')
    a.e(4, cy - 3, 8, 10, 'feather', out=False)
    a.e(-4, cy + 9, 8, 4, 'feather', out=False)
    # big broad wing, hanging and flapping
    a.e(-12, cy + 1 + flap * .8, 9.4, 15, 'feather', ang=.25 - flap * .03)
    a.e(-12, cy + 3 + flap * .8, 5.4, 10, 'feather', ang=.25 - flap * .03, out=False)
    for k in range(3):
        a.line((-16 + k * 4, cy - 10 + flap * .6), (-17 + k * 4, cy - 16 + flap * .4), 'feather0', 1)
    # long bald neck with a fluffy ruff
    hx, hy = 10 + strike * 6 - wind * 3, cy + 20 - strike * 4 + wind * 2
    a.c((4, cy + 8), (hx - 3, hy - 4), 4.4, 3.4, 'skin')
    for k in range(6):
        a.e(-2 + k * 2.4, cy + 12 + (k % 2) * 2, 3.4, 3.2, 'ruff')
    # head: bald, sun-coloured crest dots, hooked beak
    a.e(hx, hy, 10.6, 9.6, 'skin')
    a.e(hx - 3, hy + 4, 5.6, 3, 'skin', out=False)
    a.e(hx - 1, hy + 10, 3.6, 3.6, 'sun')
    jaw = max(wind * .5, strike) * 3
    a.poly([(hx + 6, hy + 1), (hx + 17, hy - 3 - jaw * .5), (hx + 14, hy - 8 - jaw), (hx + 5, hy - 5 - jaw)], 'beak1')
    a.line((hx + 7, hy - 3), (hx + 15, hy - 4 - jaw * .5), 'beak0', 1)
    a.eye(hx - 0.4, hy + 2, 4.6, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 3, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 18 + k * 3, 40), hy - 4 + k * 4, 2.2, 'sun1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def dunecolossus(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('dunecolossus', clip, n, sy=1 - fall * .5)
    a.pk = .82
    b = bob * .7
    # stout stone legs
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 10, 22), (s * 11, 5 + up), 7.4, 6, 'sand')
        a.e(s * 12, 3.6 + up, 9, 4, 'stone')
    # layered sandstone torso with strata lines and a lapis core
    a.band([(-18, 22), (18, 22), (24, 50 + b), (-24, 50 + b)], 'sand')
    for k in range(4):
        a.line((-20 + k * 2, 28 + k * 6), (20 - k * 2, 30 + k * 6), 'sand0', 1)
    a.e(0, 50 + b, 25, 9, 'sand')
    a.e(0, 36 + b, 8, 9, 'lapis')
    a.dot(-4, 38 + b, 'lapis3', 3)
    # shoulders (rocks) and a stone fists
    far = (-33, 40 + b + sw * 2)
    a.c((-20, 52 + b), far, 8, 7, 'sand')
    a.e(far[0], far[1] - 4, 8.4, 7.4, 'fist')
    fist = (lerp(lerp(30, 28, wind), 32, strike), lerp(lerp(44, 66, wind), 38, strike) + b)
    if clip == 'die':
        fist = (lerp(32, 36, fall), lerp(44, 8, fall))
    a.c((20, 52 + b), fist, 8.4, 7.4, 'sand')
    a.e(fist[0], fist[1] - 3, 9.4, 8, 'fist')
    for k in range(3):
        a.line((fist[0] - 3 + k * 3, fist[1] - 7), (fist[0] - 3 + k * 3, fist[1] - 2), 'fist0', 1)
    # head: a blocky pharaoh helm with glowing eyes and a lapis gem
    hx, hy = 0 + strike * 2, 66 + b
    a.e(hx, hy, 16, 15, 'sand')
    a.e(hx - 6, hy + 7, 8, 4, 'sand', out=False)
    a.band([(hx - 14, hy + 6), (hx + 14, hy + 6), (hx + 18, hy + 22), (hx - 18, hy + 22)], 'gold')
    a.e(hx, hy + 14, 4, 4, 'lapis')
    a.eye(hx - 6, hy + 1, 4.8, iris='iris', look=(.4, .1))
    a.eye(hx + 7, hy + 1, 4.4, iris='iris', look=(.8, .1))
    a.dot(hx - 12, hy - 4, 'blush', 3)
    jaw = max(wind * .4, strike) * 3
    a.e(hx + 1, hy - 8, 6.4, 2.4 + jaw, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(fist[0] + 10 + k * 2, 40), fist[1] - 6 + k * 5, 2.4, 'gold1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def mirageroc(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('mirageroc', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .9
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 4 if clip == 'idle' else (math.sin(n * math.pi / 2) * 4 if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-4, -10, -16, 8, 12, 6, 2, 0)[n]
    cy = 32 + b - fall * 10
    # shimmering tail plumes
    for k, (grp, off) in enumerate((('shimmer', 0), ('feather', 4), ('crest', -4))):
        a.c((-8, cy - 4), (-24 - off + sw * 1.5, 8 + k * 3), 5.4, 2, grp)
    # legs and big talons
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 6 - 2, cy - 10), (s * 6 - 1, 5 + up), 3, 2.4, 'claw')
        a.e(s * 6 + 3, 3 + up, 5.4, 2.2, 'claw')
    # barrel body with a golden breast
    a.e(-2, cy + 2, 18, 16, 'feather')
    a.e(5, cy - 2, 10, 12, 'body', out=False)
    # huge wing raised behind, with a shimmer band
    for k, (grp, dx) in enumerate((('feather', 0), ('shimmer', 8), ('crest', 15))):
        tip = (-30 + dx + k * 2, cy + 28 + flap - k * 3)
        a.band([(-6 + k, cy + 8), (-2 + k * 4, cy + 12), tip, (-22 + dx * .3, cy + 16 + k)], grp)
    # neck and head with a flame crest
    hx, hy = 10 + strike * 6 - wind * 3, cy + 24 - strike * 3
    a.c((2, cy + 10), (hx - 2, hy - 3), 7, 6, 'feather')
    for k, (dx, ln) in enumerate(((-6, 11), (-1, 14), (4, 10))):
        a.c((hx + dx, hy + 6), (hx + dx - 4 + sw + k * 2, hy + 6 + ln), 2.4, 1.2, ('crest', 'shimmer', 'crest')[k])
    a.e(hx, hy, 12.4, 11, 'feather')
    a.e(hx - 4, hy + 5, 6.4, 3.2, 'feather', out=False)
    jaw = max(wind * .5, strike) * 3
    a.poly([(hx + 6, hy + 1), (hx + 20, hy - 4 - jaw * .4), (hx + 6, hy - 6 - jaw)], 'beak1')
    a.line((hx + 7, hy - 2), (hx + 17, hy - 4), 'beak0', 1)
    a.eye(hx - 0.4, hy + 2.4, 4.8, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(hx + 21 + k * 2, 40), hy - 6 + (k * 5) % 12, 2.2, 'shimmer1')
    return a.done()


DRAW = dict(sandhopper=sandhopper, dunefennec=dunefennec, glassscorpion=glassscorpion, sunvulture=sunvulture,
            dunecolossus=dunecolossus, mirageroc=mirageroc)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/lapis-preview')
    print('ok')
