"""Cel-shaded Frostwake Shelf enemies (zone 26) for make_frostwake_sprites.py.

Same recipe as lapis_cel_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the six frostwake_* NPCs keep their old art).
`python3 scripts/frostwake_cel_redraw.py [kind...]` writes contact sheets to test-results/frostwake-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp
from cel_zone_common import ROOT, diamond, mku as mk, preview, star, timing

KINDS = ('snowhare', 'iceotter', 'frostheron', 'glaciercrab', 'bellmammoth', 'auroramanta', 'crevasseleviathan')

PALETTES = {
    'snowhare': mk(fur=('#6a86a8', '#b4cce0', '#e8f4fc', '#ffffff'), belly=('#d8e8f4', '#f8fcff'),
                   ear=('#e88aa0', '#ffc0cc'), tail=('#b4cce0', '#f4faff'), iris='#2a4a9a', blush='#ff9ab0',
                   nose='#e8607a', tooth='#fffcf0'),
    'iceotter': mk(fur=('#1c3a5e', '#3e78a6', '#7ab8d8', '#c8f0f8'), belly=('#c8e8ec', '#f4fcff'),
                   fish=('#b87a1c', '#f0b24a', '#ffe08a'), whisk='#f0fcff', iris='#1a2a6a', blush='#ff9ab0',
                   nose='#2a1a2c', mouth=('#4a1830', '#e85a78')),
    'frostheron': mk(feather=('#5a7ea8', '#9cc4e0', '#dcf0fa', '#ffffff'), wing=('#3a5a88', '#6c9cc8', '#a8d4f0'),
                     beak=('#a8741a', '#f4b43c', '#fff0a0'), leg=('#8a6a58', '#c8a088'), iris='#e8a020',
                     blush='#ff9ab0', crest=('#2a3a5e', '#5a78a8')),
    'glaciercrab': mk(shell=('#1c4a7a', '#3a8ec0', '#7ad4ec', '#d8fcff'), crystal=('#a8d8f0', '#e0f8ff', '#ffffff'),
                      claw=('#16406e', '#2e78a8', '#5cb8d8'), leg=('#14385e', '#2a6a98'), iris='#2a2a8a',
                      blush='#ff9ab0', mouth=('#4a1830', '#e85a78'), belly=('#b8e8f0', '#f0ffff')),
    'bellmammoth': mk(fur=('#4a5478', '#8494b4', '#bccae0', '#eef4fc'), tusk=('#c8c0a0', '#f4ecd0', '#fffcee'),
                      bell=('#8a5a14', '#d49a2a', '#f8d060', '#fff4b0'), skin=('#6a5a78', '#a894b8'),
                      iris='#2a3a8a', blush='#ff9ab0', mouth=('#4a1830', '#e85a78'), cord=('#5a2a3a', '#a84a58')),
    'auroramanta': mk(body=('#14305e', '#2e66a0', '#58b8c8', '#a8f4d0'), aurora=('#2a8a68', '#58d89a', '#a8ffd0'),
                      aurora2=('#6a2a9a', '#b070e8', '#e8c4ff'), belly=('#c8f0ec', '#f4ffff'), iris='#e8408a',
                      blush='#ff9ab0', mouth=('#4a1830', '#e85a78'), star=('#e8fff0', '#ffffff')),
    'crevasseleviathan': mk(skin=('#0c2650', '#1e5690', '#3a8ec4', '#8cd8ec'), belly=('#b8e8f0', '#f4ffff'),
                            fin=('#1a3a78', '#4a7ac8', '#8cb8f0'), tooth=('#d8d8c8', '#fffff0'),
                            maw=('#5a1c3a', '#d44a6a'), iris='#f2c02e', blush='#ff9ab0', ice=('#6a9ac8', '#a8d8f0', '#e8fcff')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def snowhare(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('snowhare', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .94
    hop = (math.sin(n * math.pi / 4 + .4) * .5 + .5) * 8 if clip == 'walk' else (bob * .7 if clip == 'idle' else 0)
    a.lift = hop * (1 - fall)
    cy = 22 - fall * 5
    a.e(-17, cy + 4, 5.6, 5.6, 'tail')
    a.c((-8, cy + 3), (-5, 4), 9, 4.6, 'fur')
    a.e(-2, 3, 9, 3.6, 'fur')
    a.e(0, 3, 4, 1.8, 'belly', out=False)
    a.e(0, cy + 7, 15, 13, 'fur')
    a.e(5, cy + 4, 8, 9, 'belly', out=False)
    a.c((8, cy + 2), (13 + strike * 6, cy - 4 + wind * 4), 2.6, 1.8, 'fur')
    hx, hy = 9 + strike * 5 - wind * 2, cy + 20
    for s, ex in ((-1, -6), (1, 2)):
        a.e(hx + ex, hy + 14, 3.4, 10, 'fur', ang=s * .12 - .12)
        a.e(hx + ex, hy + 14, 1.8, 7, 'ear', out=False, ang=s * .12 - .12)
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
            star(a, min(hx + 14 + k * 3, 40), hy - 2 + k * 3 - 4, 2, 'belly1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def iceotter(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('iceotter', clip, n, sy=1 - fall * .5)
    a.ox = -6
    a.pk = .94
    cy = 18 + bob * .5 - fall * 4
    lunge = strike * 4 - wind * 2
    for k, lx in enumerate((-14, -6, 8, 16)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 3 if clip == 'walk' else 0
        a.c((lx * .9, cy - 1), (lx + 2 + (lunge if k > 1 else 0), 3 + up), 3.4, 2.4, 'fur')
        a.e(lx + 3 + (lunge if k > 1 else 0), 2 + up, 3.6, 1.8, 'fur')
    wav = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else sw * 4
    a.c((-20, cy + 2), (-32, cy + 6 + wav * .5), 5.4, 3, 'fur')
    a.c((-32, cy + 6 + wav * .5), (-36, cy + 12 + wav), 3, 1.4, 'fur')
    a.e(-4, cy + 4, 22, 10.6, 'fur')
    a.e(2, cy - 3, 14, 5.6, 'belly', out=False)
    # a little fish held up in the paws
    a.c((12, cy + 2), (20 + lunge, cy + 6 - wind * 4), 3, 2.2, 'fur')
    fx, fy = 22 + lunge, cy + 12 + wind * 4 - strike * 4
    a.e(fx, fy, 6, 2.8, 'fish', ang=.3)
    a.poly([(fx - 5, fy - 1), (fx - 10, fy + 3), (fx - 10, fy - 4)], 'fish1', out=False)
    hx, hy = 16 + lunge, cy + 14 - wind * 2
    a.e(hx - 3, hy + 9, 3, 3, 'fur')
    a.e(hx + 5, hy + 9, 3, 3, 'fur')
    a.e(hx, hy, 11.6, 9.6, 'fur')
    a.e(hx - 4, hy + 4, 6, 3, 'fur', out=False)
    a.e(hx + 6, hy - 3, 7, 4.6, 'belly')
    a.dot(hx + 11, hy - 1, 'nose', 3)
    a.eye(hx - 1.8, hy + 2.6, 4.6, iris='iris', look=(.8, .1))
    a.eye(hx + 6.4, hy + 2.4, 3.6, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 2, 'blush', 2)
    for s in (-1, 1):
        a.line((hx + 9, hy - 3 + s), (hx + 15, hy - 3 + s * 2.5), 'whisk', 1)
    jaw = max(wind * .5, strike) * 3
    a.e(hx + 6, hy - 6 - jaw, 3, 1.2 + jaw * .6, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 18 + k * 2, 40), hy - 4 + k * 3, 2, 'whisk')
    return a.done()


# ------------------------------------------------------------------------------------------------
def frostheron(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('frostheron', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .9
    b = bob * .5
    flap = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-3, -6, -9, 5, 6, 3, 1, 0)[n]
    cy = 40 + b - fall * 14
    # long stilt legs
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 4, cy - 8), (s * 5 + (2 if s > 0 else -1), 4 + up), 2, 1.6, 'leg')
        a.e(s * 5 + 3, 2.6 + up, 5, 1.8, 'leg')
    a.c((-6, cy - 2), (-22 + sw, cy - 14), 5, 1.6, 'wing')
    a.e(-2, cy, 12.6, 11, 'feather')
    a.e(4, cy - 4, 6.6, 7, 'feather', out=False)
    # wing
    a.e(-8, cy + 1 + flap * .8, 7.4, 11.4, 'wing', ang=.25 - flap * .03)
    a.e(-8, cy + 3 + flap * .8, 4, 7, 'wing', ang=.25 - flap * .03, out=False)
    # S-curved neck and head
    hx, hy = 10 + strike * 9 - wind * 4, cy + 28 - strike * 9 + wind * 2
    a.c((2, cy + 6), (-3, cy + 15), 3.6, 3.2, 'feather')
    a.c((-3, cy + 15), (hx - 2, hy - 3), 3.2, 3, 'feather')
    a.e(hx, hy, 8.4, 7.6, 'feather')
    a.e(hx - 3, hy + 3, 4.4, 2.4, 'feather', out=False)
    for k in range(3):
        a.c((hx - 3, hy + 5), (hx - 12 + k * 2 + sw, hy + 9 - k * 3), 1.6, .8, 'crest')
    jaw = max(wind * .5, strike) * 2
    a.poly([(hx + 5, hy + 1.6), (hx + 20, hy - 1 - jaw * .3), (hx + 5, hy - 3 - jaw)], 'beak1')
    a.line((hx + 6, hy - 1), (hx + 17, hy - 1.4), 'beak0', 1)
    a.eye(hx - 0.4, hy + 2, 4, iris='iris', look=(.8, .1))
    a.dot(hx - 5, hy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 20 + k * 2, 40), hy - 2 + k * 4 - 4, 2.2, 'wing2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def glaciercrab(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('glaciercrab', clip, n, sy=1 - fall * .5)
    a.pk = .94
    cy = 17 + bob * .5 - fall * 4
    for s in (-1, 1):
        for k, lx in enumerate((-14, -6, 4)):
            up = max(0, math.sin(n * math.pi / 2 + k * 1.5 + (s > 0) * 2)) * 3 if clip == 'walk' else 0
            a.c((lx * .8, cy - 2), (lx + s * 12 - (2 if s < 0 else -2), 3 + up), 2.4, 1.4, 'leg')
    # shell with ice crystals
    a.e(0, cy + 6, 22, 14, 'shell')
    a.e(-8, cy + 11, 11, 4, 'shell', out=False)
    for k, (cx, ch) in enumerate(((-12, 10), (-4, 14), (5, 11), (13, 8))):
        a.band([(cx - 3.6, cy + 13), (cx - 1, cy + 13 + ch), (cx + 1, cy + 13 + ch), (cx + 3.6, cy + 13)], 'crystal')
    # claws
    far = (-27, cy + 10)
    a.c((-18, cy + 6), far, 3.4, 3, 'claw')
    a.e(far[0] - 2, far[1] + 4, 6.4, 6, 'claw')
    hand = (lerp(lerp(26, 24, wind), 32, strike), lerp(lerp(cy + 6, cy + 24, wind), cy + 2, strike))
    if clip == 'die':
        hand = (lerp(26, 28, fall), lerp(cy + 6, 6, fall))
    a.c((18, cy + 6), hand, 3.6, 3.4, 'claw')
    a.e(hand[0] + 2, hand[1] + 3, 7, 6.4, 'claw')
    a.line((hand[0] + 4, hand[1] + 3), (hand[0] + 10, hand[1] + 3 - strike * 2), 'ink', 1)
    # eyes on stalks and a little mouth
    for s, ex in ((-1, -7), (1, 5)):
        a.c((ex, cy + 16), (ex + s, cy + 24), 2, 1.8, 'shell')
        a.eye(ex + s, cy + 26, 3.8, iris='iris', look=(.5 + s * .2, .1))
    a.dot(-9, cy + 14, 'blush', 2)
    a.dot(8, cy + 14, 'blush', 2)
    jaw = max(wind * .5, strike) * 2
    a.e(-1, cy + 10, 4, 1.4 + jaw, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hand[0] + 10 + k * 2, 40), hand[1] - 4 + k * 4, 2, 'crystal2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def bellmammoth(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('bellmammoth', clip, n, sy=1 - fall * .5)
    a.ox = -4
    a.pk = .88
    b = bob * .5
    a.lift = fall * 6
    cy = 32 + b - fall * 8
    # four pillar legs
    for k, lx in enumerate((-22, -12, 10, 20)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        a.c((lx * .9, cy - 3), (lx, 4 + up), 8, 6.6, 'fur')
        a.e(lx + 1, 3 + up, 7.4, 3, 'skin')
    a.c((-26, cy + 8), (-32, cy - 2 + sw * 2), 2.4, 2, 'cord')
    a.e(-32, cy - 4 + sw * 2, 3, 4.4, 'fur')
    # shaggy body and a big hanging bell on the flank
    a.e(-6, cy + 6, 27, 20, 'fur')
    a.e(-14, cy + 17, 14, 5.6, 'fur', out=False)
    a.e(-8, cy - 2, 12, 4.6, 'fur', out=False)
    bx, by = -8, cy - 4 + sw * .6
    a.c((bx, cy + 8), (bx, by + 2), 1.4, 1.4, 'cord')
    a.band([(bx - 7, by - 2), (bx - 4.4, by + 9), (bx + 4.4, by + 9), (bx + 7, by - 2)], 'bell')
    a.e(bx, by - 3, 7, 3, 'bell', out=False)
    a.e(bx + sw * 1.4, by - 4, 2, 2, 'bell3' if False else 'bell')
    # head with floppy ear, tusks and a trunk
    hx, hy = 22 + strike * 6 - wind * 3, cy + 14
    a.e(hx - 7, hy + 1, 5.4, 9.4, 'skin')
    a.e(hx, hy + 2, 13.4, 12.4, 'fur')
    a.e(hx - 4, hy + 8, 7, 3.4, 'fur', out=False)
    trunk = (hx + 12 + strike * 3, hy - 12 - wind * 3 + strike * 6)
    a.c((hx + 6, hy - 2), (hx + 9, hy - 8), 5, 4, 'fur')
    a.c((hx + 9, hy - 8), trunk, 4, 2.6, 'fur')
    a.c((hx + 4, hy - 4), (hx + 14, hy - 9 + strike * 2), 2.6, 1.2, 'tusk')
    a.eye(hx - 1.4, hy + 5, 4.4, iris='iris', look=(.8, .1))
    a.eye(hx + 8, hy + 4.6, 3.6, iris='iris', look=(.9, .1))
    a.dot(hx - 7, hy - 1, 'blush', 3)
    a.e(hx + 3, hy - 7, 4, 1.2 + max(wind * .4, strike) * 2, 'mouth')
    # little hairy crest and a cord-hung bell bobbing on the head
    for k in range(3):
        a.c((hx - 6 + k * 5, hy + 12), (hx - 7 + k * 5 + sw * .5, hy + 17), 3, 1, 'fur')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(trunk[0] + 6 + k * 2, 40), trunk[1] + 2 + k * 3, 2.2, 'bell3')
    return a.done()


# ------------------------------------------------------------------------------------------------
def auroramanta(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('auroramanta', clip, n, sy=1 - fall * .5)
    a.pk = .88
    hover = (math.sin(n * math.pi / 3) * 3 + 8 if clip == 'idle' else
             abs(math.sin(n * math.pi / 4 + .3)) * 4 + 8 if clip == 'walk' else 8)
    a.lift = hover * (1 - fall)
    cy = 36 - fall * 8
    flap = math.sin(n * math.pi / 3) * 4 if clip == 'idle' else (sw * 5 if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-4, -8, -12, 8, 10, 5, 2, 0)[n]
    # aurora ribbon tail
    for k, grp in enumerate(('aurora', 'aurora2', 'aurora')):
        a.c((0, cy - 8), (-6 + k * 6 + sw * 2 * (k - 1), cy - 24 - k * 2), 3.4 - k * .4, 1, grp)
    # the great wings: bands of colour sweeping out and up
    for s in (-1, 1):
        a.band([(s * 3, cy + 5), (s * 26, cy + 14 + flap), (s * 40, cy + 6 + flap * 1.3), (s * 28, cy - 8), (s * 6, cy - 6)],
               'body')
        a.band([(s * 8, cy + 3), (s * 24, cy + 9 + flap), (s * 32, cy + 3 + flap), (s * 22, cy - 3), (s * 10, cy - 2)],
               'aurora' if s < 0 else 'aurora2', out=False)
    # round body, pale belly
    a.e(0, cy + 2, 13.4, 14, 'body')
    a.e(2, cy - 2, 8, 8, 'belly', out=False)
    # face
    hx, hy = 1 + strike * 5 - wind * 2, cy + 10
    a.e(hx, hy, 10, 6.4, 'body')
    a.eye(hx - 4, hy + 2, 4.2, iris='iris', look=(.5, .1))
    a.eye(hx + 5, hy + 2, 3.8, iris='iris', look=(.8, .1))
    a.dot(hx - 8, hy - 2, 'blush', 2)
    a.e(hx + 1, hy - 4, 3, 1.2 + max(wind * .4, strike) * 2, 'mouth')
    # sparkles
    for k in range(3):
        star(a, -26 + k * 26 + (n % 3) * 2, cy + 22 + ((k + n) % 3) * 4, 1.8, 'star0')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 12 + k * 4, 40), hy - 6 - k * 3, 2.2, 'aurora2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def crevasseleviathan(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('crevasseleviathan', clip, n, sy=1 - fall * .5)
    a.ox = -6
    a.pk = .9
    b = bob * .5
    a.lift = fall * 7
    # ice shards of the crevasse around the base
    for k, (cx, ch) in enumerate(((-30, 12), (-24, 8), (22, 9), (30, 13))):
        a.band([(cx - 4, 2), (cx - 1, 2 + ch), (cx + 3, 2 + ch * .6), (cx + 5, 2)], 'ice')
    # coiled body rising from the ice
    wav = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else sw * 2
    a.e(-12, 8, 20, 8, 'skin')
    a.e(-10, 6, 12, 3, 'belly', out=False)
    a.c((-8, 12), (-12 + wav, 30), 12, 10, 'skin')
    a.c((-12 + wav, 30), (-4 + wav, 46 + b), 10.4, 9, 'skin')
    a.c((-10 + wav, 18), (-8 + wav, 40 + b), 3.6, 3.6, 'belly', out=False)
    # side fins
    a.band([(-18, 36), (-32, 40 + sw * 3), (-28, 28), (-16, 26)], 'fin')
    # the head lunges forward, jaw wide when striking
    hx, hy = 8 + strike * 14 - wind * 8, 56 + b - strike * 10 + wind * 3 - fall * 30
    a.c((-4 + wav, 46 + b), (hx - 3, hy - 3), 9, 9, 'skin')
    a.e(hx, hy, 15, 11.4, 'skin')
    a.e(hx - 5, hy + 6, 8, 3.4, 'skin', out=False)
    jaw = max(wind * .6, strike) * 6
    # lower jaw and mouth
    a.e(hx + 8, hy - 8 - jaw, 11, 4.4 + jaw * .3, 'skin')
    a.e(hx + 9, hy - 5 - jaw * .5, 9, 2.6 + jaw * .6, 'maw')
    for k in range(4):
        a.poly([(hx + 3 + k * 4, hy - 3 - jaw * .3), (hx + 5.6 + k * 4, hy - 3 - jaw * .3), (hx + 4.4 + k * 4, hy - 7 - jaw * .3)],
               'tooth1', out=False)
    a.e(hx - 1, hy + 3, 3, 8, 'fin', ang=.1, out=False)
    a.eye(hx - 3, hy + 5, 4.8, iris='iris', look=(.8, .1))
    a.eye(hx + 6.4, hy + 4.4, 3.8, iris='iris', look=(.9, .1))
    a.dot(hx - 10, hy - 1, 'blush', 3)
    for k in range(3):
        a.band([(hx - 8 + k * 6, hy + 10), (hx - 6 + k * 6, hy + 17 - k), (hx - 4 + k * 6, hy + 10)], 'fin', out=False)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(hx + 20 + k * 2, 40), hy - 6 + (k * 5) % 12, 2.2, 'ice1')
    return a.done()


DRAW = dict(snowhare=snowhare, iceotter=iceotter, frostheron=frostheron, glaciercrab=glaciercrab, bellmammoth=bellmammoth,
            auroramanta=auroramanta, crevasseleviathan=crevasseleviathan)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/frostwake-preview')
    print('ok')
