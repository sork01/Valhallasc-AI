"""Cel-shaded Moonspore Canopy enemies (zone 16) for make_moonspore_sprites.py.

Same recipe as orrery_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/moonspore_cel_redraw.py [kind...]` writes contact sheets to test-results/moonspore-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('glowcapgrazer', 'silkwing', 'rootlurker', 'lanternwraith', 'mireheart', 'silverwidow', 'nightbloom')

PALETTES = {
    'glowcapgrazer': mk(moss=('#1c3a2a', '#3f7a52', '#7cc27a', '#d2f5a4'), cap=('#0e5a5a', '#2fb89a', '#8cf0c0', '#e4ffe6'),
                        belly=('#a8cf88', '#e8f8b8'), stem=('#5a8a6a', '#b4dcb0'), spot='#fff6b8', iris='#1a7a8a',
                        blush='#ff9a9a', spore='#c8ffb8', mouth=('#4a1c34', '#ff7a98')),
    'silkwing': mk(fur=('#2a3a4e', '#5a7488', '#a8c0cc', '#eef4f2'), wing=('#2a4a72', '#4e86b4', '#9ad4e2', '#e8fbf4'),
                   edge=('#4a3a80', '#8a74c8', '#c8b8f4'), spot=('#fff0b8', '#ffd878'), iris='#2aa8b8', blush='#ff9ac0',
                   dust='#d8fff4', feel=('#7a8ea0', '#e4f0f0')),
    'rootlurker': mk(bark=('#241c1a', '#523e32', '#8a6a48', '#c8a474'), moss=('#1c3a2a', '#3f7a52', '#7cc27a'),
                     claw=('#a89878', '#f0e4c4'), bulb=('#0e6a58', '#38d8a8', '#c0ffe6'), iris='#38e8b0',
                     blush='#ff9a8a', mouth=('#3a1428', '#c8486e')),
    'lanternwraith': mk(cloak=('#1c2040', '#3a3e74', '#6a6ca8', '#aeb0e0'), void=('#0a0a1c', '#1a1a34'),
                        flame=('#2a8a3a', '#7ae860', '#e8ffc8'), iron=('#2e2e3e', '#6a6a82', '#a8a8c0'),
                        glass=('#58a85a', '#a8ecaa'), iris='#9cff7a', blush='#ffa0c0', mist=('#7a7cb8', '#c4c6f0')),
    'mireheart': mk(hide=('#1e3426', '#3e6a42', '#7ea050', '#c4d880'), belly=('#7a9060', '#b8c488', '#e4e8b0'),
                    heart=('#7a1c3c', '#d04a72', '#ff8fa8', '#ffd2dc'), moss=('#183a24', '#2e6a38', '#5ea848'),
                    bulb=('#a83a64', '#ff90b0', '#ffe0ea'), iris='#ff4a86', mouth=('#401428', '#d4507a'),
                    spore='#f4ffd0', blush='#ff9a98'),
    'silverwidow': mk(silver=('#2c2c44', '#6a6a88', '#b8b8d0', '#f0eefa'), orb=('#3a1c6a', '#7a44c0', '#bc84f2', '#f0d0ff'),
                      leg=('#26263c', '#52526e', '#8a8aa8'), mark=('#e87cff', '#ffd8ff'), fang=('#d8d4e8', '#f8f6ee'),
                      iris='#e85ad8', thread=('#cdd0e8', '#f2f4ff'), blush='#ff9ac8'),
    'nightbloom': mk(petal=('#34204e', '#7a3e84', '#c26ea8', '#f4b8d0'), inner=('#4a2260', '#9a52a8', '#e49ac8'),
                     stem=('#1c3a30', '#357a54', '#6cb878'), thorn=('#d8e8b0', '#fffbe0'),
                     disc=('#c8a838', '#f4e078', '#fff8b8'), iris='#46d058', glow=('#a8e84a', '#eaffa0'),
                     blush='#ff90b8', root=('#3a2a24', '#7a5a44')),
}
R.PALETTES.update(PALETTES)


def sparkle(a, n, cx, cy, spread, name='spore', size=1, count=4):
    for k in range(count):
        a.dot(cx + math.sin(n * 1.3 + k * 2.1) * spread, cy + math.cos(n * 1.7 + k * 1.9) * spread * .8, name, size)


# ------------------------------------------------------------------------------------------------
def glowcapgrazer(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('glowcapgrazer', clip, n, sy=1 - fall * .5)
    b = bob * .7
    graze = (0, 0, 3, 5, 3, 0)[n] if clip == 'idle' else 0
    cy = 22 + b - fall * 8
    # four stubby feet
    for k, (fx, near) in enumerate(((-16, 0), (-5, 1), (9, 0), (20, 1))):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        a.e(fx, 4 + up, 6, 3.4, 'moss', out=True)
    # mushroom cluster on the back: stems, caps and glow spots
    for cx_, h, r in ((-20, 24, 10), (-8, 31, 12), (6, 23, 8.4)):
        sway2 = math.sin(n * math.pi / 3 + cx_) * 1.2 if clip == 'idle' else sw * 1.4
        top = (cx_ + sway2 - wind * 2 + strike * 2, cy + h)
        a.c((cx_, cy + 8), top, 2.6, 2, 'stem')
        a.e(top[0], top[1] + 2, r, r * .55, 'cap')
        a.e(top[0] - r * .3, top[1] + 3.5, r * .55, r * .22, 'cap', out=False)
        a.dot(top[0] - r * .4, top[1] + 2, 'spot', 2)
        a.dot(top[0] + r * .35, top[1] + 3, 'spot', 2)
    # body and lighter belly
    a.e(-1, cy, 21, 14.4, 'moss')
    a.e(-4, cy - 6, 14, 6, 'belly', out=False)
    a.e(-12, cy + 8, 9, 4, 'moss', out=False)
    # head: lowers to graze, lunges on the attack
    hx = 17 + strike * 9 - wind * 4
    hy = cy + 3 - graze * 1.6 + wind * 6 - strike * 3 - fall * 2
    a.e(hx, hy, 12.4, 11.4, 'moss')
    a.e(hx - 4, hy + 5, 7, 3.4, 'moss', out=False)
    a.e(hx + 8, hy - 4, 5.6, 3.8, 'belly')
    a.eye(hx - 2.6, hy + 2.4, 4.6, iris='iris', look=(.3, .1))
    a.eye(hx + 6, hy + 2.4, 4, iris='iris', look=(.8, .1))
    a.dot(hx - 7, hy - 2, 'blush', 2)
    mouth = max(wind * .5, strike) * 3
    a.line((hx + 5, hy - 6 - mouth), (hx + 11, hy - 6 - mouth), 'mouth1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        sparkle(a, n, min(hx + 16, 36), hy + 2, 6, count=6)
    if clip == 'idle':
        sparkle(a, n, -4, cy + 40, 24, count=3)
    return a.done()


# ------------------------------------------------------------------------------------------------
def silkwing(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('silkwing', clip, n, sy=1 - fall * .45)
    flap = math.sin(n * (math.pi / 3 if clip == 'idle' else math.pi / 2)) * 8
    if clip == 'attack':
        flap = (-6, -10, -12, 12, 14, 8, 2, 0)[n]
    if clip == 'hurt':
        flap = (-4, -2, 2, 4)[n]
    if fall:
        flap = lerp(flap, -9, fall)
    cy = 46 + bob * 1.2 - fall * 28
    wk = 1 - fall * .4
    # wings: rounded upper and lower pair on both sides, with eyespots
    for s in (-1, 1):
        a.e(s * 15 * wk, cy - 13 - flap * .3, 15, 8.6, 'edge', ang=-s * (.62 + flap * .02))
        a.e(s * 21 * wk, cy + 9 + flap * .6, 19, 10, 'wing', ang=s * (.4 + flap * .035))
        a.e(s * 21 * wk, cy + 9 + flap * .5, 12, 4.6, 'wing', ang=s * (.4 + flap * .035), out=False)
        a.e(s * 26 * wk, cy + 11 + flap * .55, 4.8, 4.8, 'spot')
        a.dot(s * 26 - .5, cy + 11 + flap * .55, 'wing2', 2)
        a.e(s * 19 * wk, cy - 15 - flap * .3, 3.2, 3.2, 'spot')
    # fuzzy body and chibi head
    a.e(0, cy - 4, 7.6, 12.6, 'fur')
    for k in range(3):
        a.line((-5, cy - 8 + k * 4), (5, cy - 8 + k * 4), 'fur0', 1)
    a.e(0, cy + 13, 11.4, 10.4, 'fur')
    a.e(-4, cy + 17, 6, 3, 'fur', out=False)
    # feathery antennae
    for s in (-1, 1):
        tip = (s * 15 + sw * s, cy + 36)
        a.c((s * 4, cy + 21), tip, 1.2, .8, 'feel')
        a.e(tip[0], tip[1], 2.4, 3.6, 'feel')
    a.eye(-4.4, cy + 13, 4.6, iris='iris', look=(.3, .1))
    a.eye(5.4, cy + 13, 4.6, iris='iris', look=(.7, .1))
    a.dot(-9, cy + 9, 'blush', 2)
    a.dot(9.4, cy + 9, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(6):
            a.dot(min(10 + (n - 3) * 5 + k * 3, 38), cy - 6 - k * 2 + (k % 2) * 6, 'dust', 2)
    if clip == 'idle':
        sparkle(a, n, 0, cy - 24, 14, 'dust', 1, 3)
    return a.done()


# ------------------------------------------------------------------------------------------------
def rootlurker(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('rootlurker', clip, n, sy=1 - fall * .5)
    b = bob * .6
    # root-bundle legs splaying into tendril toes
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 6, 26 + b), (s * 11, 6 + up), 5.6, 4.4, 'bark')
        for t in (-1, 0, 1):
            a.c((s * 11, 6 + up), (s * 11 + t * 6 + s * 2, 2 + up), 2.2, 1.2, 'bark')
    # far arm
    a.c((-9, 40 + b), (-20, 28 + b + sw * 2), 4, 3, 'bark')
    for t in (-1, 0, 1):
        a.c((-20, 28 + b + sw * 2), (-24 + t * 2, 21 + b + t * 3), 1.6, .8, 'claw')
    # barrel-shaped torso with moss patches
    a.e(0, 38 + b, 14.4, 16, 'bark')
    a.e(-5, 42 + b, 7, 6, 'bark', out=False)
    a.e(-8, 30 + b, 5.2, 3.6, 'moss', out=False)
    a.e(6, 47 + b, 4, 2.6, 'moss', out=False)
    # near arm swipes
    elbow = (lerp(lerp(15, 10, wind), 24, strike), lerp(lerp(30, 54, wind), 30, strike) + b)
    hand = (lerp(lerp(22, 14, wind), 34, strike), lerp(lerp(22, 66, wind), 20, strike) + b)
    if clip == 'die':
        elbow = (lerp(15, 20, fall), lerp(30, 14, fall))
        hand = (lerp(22, 30, fall), lerp(22, 5, fall))
    a.c((9, 42 + b), elbow, 4.4, 3.6, 'bark')
    a.c(elbow, hand, 3.6, 3, 'bark')
    for t in (-1, 0, 1):
        a.c(hand, (hand[0] + 5 + t * 1.5, hand[1] - 5 + t * 3.6), 1.8, .8, 'claw')
    # head: a wide stump with a leaf sprout, lure bulb on a stalk
    hx, hy = 3 + strike * 5, 61 + b
    a.c((hx - 6, hy + 8), (hx - 10, hy + 18), 1.4, 1, 'moss')
    a.e(hx - 11, hy + 19, 4, 2.2, 'moss', ang=.6)
    a.c((hx + 2, hy + 9), (hx + 10, hy + 20), 1.4, 1, 'moss')
    a.e(hx, hy, 14, 12, 'bark')
    a.e(hx - 5, hy + 6, 7.6, 3.6, 'bark', out=False)
    a.c((hx + 4, hy + 10), (hx + 14 + sw, hy + 22 - wind * 3), 1.4, 1.2, 'bark')
    a.e(hx + 15 + sw, hy + 21 - wind * 3, 4.6, 4.6, 'bulb')
    a.dot(hx + 13 + sw, hy + 23 - wind * 3, 'shine', 2)
    a.eye(hx - 4, hy - 1, 4.8, iris='iris', look=(.3, .1))
    a.eye(hx + 7, hy - 1, 4.2, iris='iris', look=(.8, .1))
    a.dot(hx - 9, hy - 5, 'blush', 2)
    jaw = max(wind * .6, strike) * 3
    a.e(hx + 2, hy - 7.6 - jaw * .3, 5.4, 2 + jaw, 'mouth', out=True)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hand[0] + 6 + k * 3, 38), hand[1] + k * 4 - 4, 2.2, 'claw1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def lanternwraith(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('lanternwraith', clip, n, sy=1 - fall * .55)
    a.pk = .86
    b = bob * 1.2
    lift = 6 + b
    # wispy tail: three tapering ribbons in place of legs
    for k, (dx, ln) in enumerate(((-9, 16), (0, 20), (9, 15))):
        wag = math.sin(n * math.pi / 3 + k * 1.4) * 2.4 if clip == 'idle' else sw * 2 * (k - 1)
        a.c((dx, 22 + lift), (dx + wag * 1.4, 22 + lift - ln), 6 - k % 2, 1.4, 'mist')
    # cloak: a tall cone with a ragged hem
    cloak = [(-10, 58 + lift), (10, 58 + lift), (17, 40 + lift), (21, 22 + lift), (14, 20 + lift), (7, 24 + lift), (0, 19 + lift),
             (-7, 24 + lift), (-14, 20 + lift), (-21, 22 + lift), (-17, 40 + lift)]
    a.band(cloak, 'cloak')
    a.line((-6, 48 + lift), (-8, 28 + lift), 'cloak0', 1)
    a.line((7, 46 + lift), (9, 28 + lift), 'cloak0', 1)
    # lantern on a hooked staff in the near hand
    hand = (lerp(lerp(19, 15, wind), 26, strike), lerp(lerp(40, 54, wind), 38, strike) + lift)
    if clip == 'die':
        hand = (lerp(19, 28, fall), lerp(40, 10, fall))
    a.c((10, 48 + lift), hand, 3.6, 3, 'cloak')
    a.e(hand[0], hand[1], 3, 3, 'void')
    top = (hand[0] + 2, hand[1] + 16)
    a.line(hand, top, 'ink', 4)
    a.line(hand, top, 'iron1', 2)
    lx, ly = min(top[0] + 8, 34), top[1] - 2 - fall * 2
    a.line(top, (lx, ly + 5), 'iron1', 1)
    a.band([(lx - 5, ly + 5), (lx + 5, ly + 5), (lx + 6, ly - 9), (lx - 6, ly - 9)], 'iron')
    flare = max(wind, strike) * 2
    a.e(lx, ly - 2, 3.4 + flare, 5.4 + flare, 'flame')
    a.dot(lx - 1, ly - 1, 'shine', 2)
    a.poly([(lx - 6, ly + 6), (lx + 6, ly + 6), (lx, ly + 10)], 'iron1')
    # far hand holds the hood edge
    a.e(-17, 36 + lift + sw, 3.4, 3.4, 'void')
    # hooded head with an empty face and big glowing eyes
    hx, hy = 1 + strike * 3, 62 + lift
    a.e(hx, hy, 14, 14, 'cloak')
    a.e(hx - 5, hy + 7, 7, 4, 'cloak', out=False)
    a.poly([(hx - 9, hy + 12), (hx, hy + 22), (hx + 9, hy + 12)], 'cloak2', out=True)
    a.e(hx + 1, hy - 1, 10.6, 9.6, 'void')
    a.eye(hx - 2.6, hy - 1, 4.2, iris='iris', look=(.3, .1))
    a.eye(hx + 6.6, hy - 1, 3.8, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 5, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            star(a, min(lx + 4 + k * 2, 38), ly - 4 + (k * 7) % 14 - 4, 2.2, 'flame2')
    if clip == 'idle':
        sparkle(a, n, lx, ly + 4, 8, 'flame2', 1, 3)
    return a.done()


# ------------------------------------------------------------------------------------------------
def mireheart(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('mireheart', clip, n, sy=1 - fall * .5)
    b = bob * .7
    beat = 1 + .13 * math.sin(n * math.pi / 3) if clip == 'idle' else 1 + .18 * max(wind, strike)
    cy = 32 + b - fall * 8
    # splayed webbed feet
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.e(s * 15, 5 + up, 8.4, 4, 'hide')
        for t in (-1, 0, 1):
            a.e(s * 15 + t * 5 + s * 3, 3 + up, 2.2, 1.8, 'hide', out=False)
    # huge squat body, pale belly and a window onto the pink heart
    a.e(0, cy, 27, 22, 'hide')
    a.e(-9, cy + 10, 15, 6, 'hide', out=False)
    a.e(2, cy - 7, 19, 12, 'belly')
    a.e(4, cy - 5, 10.6 * beat, 9.6 * beat, 'heart')
    a.e(1, cy - 2.4, 4, 2.6, 'heart', out=False)
    a.dot(-2 - .4 * beat, cy - 1, 'shine', 2)
    for k in range(3):
        a.line((-12 + k * 12, cy - 15), (-10 + k * 12, cy - 20), 'belly0', 1)
    # moss patches
    a.e(-17, cy + 12, 7, 3.4, 'moss', out=False)
    a.e(14, cy + 14, 5.4, 3, 'moss', out=False)
    # arms: far one rests, near one slams
    a.c((-22, cy + 2), (-30, cy - 8 + sw), 5, 4, 'hide')
    a.e(-30, cy - 10 + sw, 5.4, 3.8, 'hide')
    fist = (lerp(lerp(28, 26, wind), 34, strike), lerp(lerp(cy - 10, cy + 20, wind), 7, strike))
    if clip == 'die':
        fist = (lerp(28, 36, fall), lerp(cy - 10, 6, fall))
    a.c((20, cy + 2), fist, 5.6, 4.8, 'hide')
    a.e(fist[0], fist[1], 6.4, 4.8, 'hide')
    for t in (-1, 0, 1):
        a.e(min(fist[0] + 5 + t * 1, 40), fist[1] - 2 + t * 2.4, 2.2, 1.8, 'hide', out=False)
    # eyes sit on top of the head like a toad's, antennae with pink bulbs
    hx, hy = 1 + strike * 3, cy + 19
    for s in (-1, 1):
        a.c((hx + s * 12, hy + 6), (hx + s * 20 + sw * s, hy + 18 - wind * 3), 1.4, 1.1, 'moss')
        a.e(hx + s * 20 + sw * s, hy + 19 - wind * 3, 4, 4, 'bulb')
        a.dot(hx + s * 19.4 + sw * s, hy + 20 - wind * 3, 'shine', 1)
    a.e(hx, hy - 1, 17, 8, 'hide', out=True)
    a.e(hx - 6, hy + 2, 9, 3, 'hide', out=False)
    a.eye(hx - 7, hy + 5.4, 5.4, iris='iris', look=(.3, .1))
    a.eye(hx + 9.4, hy + 5.4, 5, iris='iris', look=(.8, .1))
    a.dot(hx - 13, hy - 1, 'blush', 2)
    jaw = max(wind * .6, strike) * 3
    a.line((hx - 6, hy - 6 - jaw), (hx + 12, hy - 6 - jaw), 'mouth1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(6):
            a.dot(min(fist[0] + 6 + k * 2, 40), 8 + (k * 5) % 12 + (n - 3) * 2, 'spore', 2)
    if clip == 'idle':
        sparkle(a, n, 0, cy + 38, 20, 'spore', 1, 3)
    return a.done()


# ------------------------------------------------------------------------------------------------
def silverwidow(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('silverwidow', clip, n, sy=1 - fall * .55)
    b = bob * .6
    by = 31 + b - fall * 14

    def leg(k, near):
        d = (1.0, .42, -.5, -1.1)[k]
        ph = n * math.pi / 2 + k * 1.3 + near * 1.6
        lift = max(0, math.sin(ph)) * 5 if clip == 'walk' else 0
        root = (3 + d * 2.6, by + 2)
        knee = (root[0] + d * 14, by + 17 - fall * 7 + (2 if near else 0))
        foot = (root[0] + d * 29 * (1 - fall * .45) + (3 if near else 0), lift + fall * 4)
        grp = 'silver' if near else 'leg'
        a.c(root, knee, 2.4, 1.9, grp)
        a.c(knee, foot, 1.9, 1.1, grp)
    for k in range(4):
        leg(k, 0)
    # near-side legs; the first pair rears up in the wind-up
    for k in range(4):
        if not (clip == 'attack' and k == 0):
            leg(k, 1)
    # abdomen: a big glossy orb with an hourglass mark, spinneret thread
    a.e(-15, by + 7, 19.6, 17.6, 'orb')
    a.e(-22, by + 16, 9.6, 5, 'orb', out=False)
    a.poly([(-18, by + 14), (-9, by + 14), (-13, by + 6), (-9, by - 2), (-18, by - 2), (-14, by + 6)], 'mark0', out=False)
    a.poly([(-16, by + 11), (-11, by + 11), (-13.5, by + 7), (-11, by + 2), (-16, by + 2), (-13.5, by + 6)], 'mark1', out=False)
    a.line((-30, by - 4), (-30 - 2 - sw, by - 20 - fall * 0), 'thread0', 1)
    a.e(-30, by - 4, 2.2, 2.2, 'silver')
    # cephalothorax and head
    a.e(5, by + 3, 11, 9, 'silver')
    a.e(2, by + 7, 6, 3, 'silver', out=False)
    hx = 12 + strike * 5 - wind * 3
    hy = by + 5 - wind * 2
    a.e(hx, hy, 11.6, 10.4, 'silver')
    a.e(hx - 4, hy + 4.6, 6, 3, 'silver', out=False)
    # four eyes: two big, two small, and fangs
    a.eye(hx - 2, hy + 1.4, 4.4, iris='iris', look=(.4, .1))
    a.eye(hx + 7, hy + 1.4, 3.8, iris='iris', look=(.9, .1))
    a.dot(hx - 6, hy + 6.4, 'iris', 3)
    a.dot(hx + 3, hy + 6.4, 'iris', 3)
    a.dot(hx - 8, hy - 3.4, 'blush', 2)
    open_ = max(wind * .5, strike) * 3
    a.poly([(hx + 5, hy - 7), (hx + 7 + open_, hy - 15 - open_), (hx + 8, hy - 7)], 'fang1')
    a.poly([(hx + 9, hy - 6), (hx + 12 + open_, hy - 14 - open_), (hx + 12, hy - 6)], 'fang1')
    if clip == 'attack':
        reach = lerp(lerp(0, -10, wind), 12, strike)
        a.c((hx + 2, by + 6), (hx + 8 + reach * .4, by + 22 + wind * 8 - strike * 14), 2, 1.6, 'silver')
        a.c((hx + 8 + reach * .4, by + 22 + wind * 8 - strike * 14), (min(hx + 12 + reach, 36), by + 10 + wind * 14 - strike * 22),
            1.6, 1, 'silver')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.line((min(hx + 14 + k * 3, 38), by - 6 - k * 3), (min(hx + 18 + k * 3, 40), by - 10 - k * 3), 'thread1', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def nightbloom(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('nightbloom', clip, n, sy=1 - fall * .35)
    a.pk = .82
    b = bob * .8
    droop = fall * 22
    open_ = 1 + max(wind, strike) * .22 - fall * .4
    # root feet
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 3, 22), (s * 13, 4 + up), 4.4, 3.2, 'root')
        for t in (0, 1):
            a.c((s * 13, 4 + up), (s * 13 + s * (5 + t * 3), 2 + up - t), 2, 1, 'root')
    # stem with leaf arms and thorns
    sx = sw * .6
    a.c((0, 18), (sx + 2, 40 + b - droop * .4), 5, 4.4, 'stem')
    for s in (-1, 1):
        tip = (s * 26 + sw * s * 2, 30 + b - fall * 14 + (strike * 8 if s == 1 else 0))
        if s == 1 and clip == 'attack':
            tip = (lerp(lerp(24, 20, wind), 34, strike), lerp(lerp(30, 52, wind), 26, strike) + b)
        a.band([(s * 3, 30 + b), (s * 12, 40 + b), (tip[0], tip[1] + 4), (s * 16, 24 + b)], 'stem')
        a.line((s * 4, 31 + b), (tip[0] - s * 3, tip[1] + 2), 'stem3' if 'stem3' in a.p.names else 'stem2', 1)
        for t in range(2):
            a.poly([(tip[0] - s * (2 + t * 5), tip[1] + 2 + t), (tip[0] - s * (4 + t * 5), tip[1] + 7), (tip[0] - s * (6 + t * 5), tip[1] + 2)],
                   'thorn1')
    # flower head: back petals, front petals, golden disc with a great eye
    hx, hy = sx + 2 + strike * 3, 60 + b - droop
    for layer, (count, rr, pr, grp) in enumerate(((8, 19, 11.4, 'petal'), (7, 12, 8, 'inner'))):
        for k in range(count):
            ang = k * 2 * math.pi / count + layer * .4 + (n * .04 if clip == 'idle' else 0)
            px, py = hx + math.cos(ang) * rr * open_, hy + math.sin(ang) * rr * open_ * .88
            a.e(px, py, pr * (1 - fall * .2), pr * .56 * (1 - fall * .2), grp, ang=-ang)
    a.e(hx, hy, 13.4, 13, 'disc')
    a.e(hx - 4, hy + 6, 7.4, 3.6, 'disc', out=False)
    state = T['state']
    if state == 'dead':
        a.line((hx - 6, hy - 5), (hx + 6, hy + 5), 'ink', 2)
        a.line((hx - 6, hy + 5), (hx + 6, hy - 5), 'ink', 2)
    else:
        a.eye(hx + 1, hy, 8.4, iris='iris', look=(.7, .1))
        a.dot(hx - 10, hy - 5, 'blush', 3)
        a.dot(hx + 12, hy - 5, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(7):
            a.dot(min(hx + 18 + k * 3 + (n - 3) * 2, 40), hy - 8 + (k * 5) % 14 - 6, 'glow1', 2 if k % 2 else 1)
    if clip == 'idle':
        sparkle(a, n, hx, hy + 22, 22, 'glow1', 1, 3)
    return a.done()


DRAW = dict(glowcapgrazer=glowcapgrazer, silkwing=silkwing, rootlurker=rootlurker, lanternwraith=lanternwraith,
            mireheart=mireheart, silverwidow=silverwidow, nightbloom=nightbloom)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/moonspore-preview')
    print('ok')
