"""Cel-shaded Sunward Vale enemies (zone 20) for make_sunward_sprites.py.

Same recipe as orrery_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the three villager NPCs keep their old art).
`python3 scripts/sunward_cel_redraw.py [kind...]` writes contact sheets to test-results/sunward-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('meadowhare', 'sunbacksnail', 'brushfox', 'spadebadger', 'honeyjaw', 'wickerwarden')

PALETTES = {
    'meadowhare': mk(fur=('#4a3322', '#8a6040', '#c8955e', '#f0cc98'), belly=('#c8a888', '#f6e6cc', '#fff6e8'),
                     ear=('#a8606a', '#f0a6aa', '#ffd8d8'), iris='#6a3a18', blush='#ff9a98', dust='#e8d8b0',
                     paw=('#6a4a30', '#a87c54'), grass='#8ad060'),
    'sunbacksnail': mk(skin=('#2e4a2a', '#5a8a48', '#94c470', '#d4f0a0'), shell=('#7a3c14', '#d4841e', '#f6c240', '#fff0a0'),
                       ring=('#a8561a', '#ffd870'), iris='#2a6a3a', blush='#ff9a98', slime='#c8f0a0', ray='#fff6c0'),
    'brushfox': mk(fur=('#6a2a14', '#c4561c', '#ee8a3a', '#ffc078'), cream=('#d8b898', '#fff0d8', '#fff6e8'),
                   sock=('#2e1a14', '#5a3a2e'), iris='#2a7a4a', blush='#ff8a8a', nose='#2a1a22', tip='#fffcf2',
                   mouth=('#4a1830', '#ff7a98'), dust='#e8d4a8'),
    'spadebadger': mk(fur=('#2a3036', '#5a646c', '#98a2a6', '#d8dcd6'), stripe=('#14181c', '#363e44', '#566068'),
                      white=('#c8ccc4', '#f6f6ee', '#fffffa'), claw=('#6a5a3a', '#c8b078', '#f6e8b4'),
                      iris='#d4a030', blush='#ff9a98', dirt=('#4a3220', '#8a6440', '#c09468'), nose='#1a1c20'),
    'honeyjaw': mk(fur=('#3a2218', '#6e4228', '#a86a3a', '#d8a068'), belly=('#a8784c', '#e4b888', '#ffe8c0'),
                   honey=('#a85a0a', '#f0a416', '#ffd84a', '#fff0a0'), hive=('#7a4a10', '#c88a24', '#f4c448'),
                   claw=('#c8b888', '#fff6d8'), iris='#3a1c10', blush='#ff9a88', bee=('#2a2020', '#f2cc3a'),
                   mouth=('#4a1830', '#ff7a98'), wing='#e4f4ff'),
    'wickerwarden': mk(wicker=('#4a3220', '#8a6238', '#c89a54', '#f0d088'), straw=('#a8801e', '#e8c04a', '#fff0a0'),
                       hat=('#5a3a18', '#a8742c', '#e0aa48', '#fadc8a'), band=('#7a1c2c', '#c84a52'),
                       post=('#2c1e14', '#5a4028', '#8a6a44'), glow=('#c85a08', '#ffb020', '#fff6b4'),
                       iris='#ffd24a', iron=('#4a4e5a', '#a8aeb8', '#e8ecf4'), stitch='#2a1a14'),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def meadowhare(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('meadowhare', clip, n, sy=1 - fall * .5)
    hop = (math.sin(n * math.pi / 4 + .4) * .5 + .5) * 8 if clip == 'walk' else (bob * .5 if clip == 'idle' else 0)
    a.lift = hop
    cy = 24 - fall * 6
    kick = strike * 1.1
    # puff tail
    a.e(-24, cy + 2, 6, 5.6, 'belly')
    # big hind leg and foot (the foot swings forward to kick)
    a.e(-10, cy - 1, 14, 11.4, 'fur')
    a.e(-12, cy + 6, 7, 3.6, 'fur', out=False)
    a.e(-4 + kick * 8 - sw * 2, 4 - kick * 2 + strike * 8, 11.4, 3.6, 'paw', ang=kick * .4)
    # body leaning forward, pale belly
    a.e(2, cy + 5, 17, 12, 'fur')
    a.e(5, cy - 1, 10, 7, 'belly', out=False)
    # front paws
    a.c((9, cy + 2), (14 + strike * 3 + sw * 1.6, 4), 3.4, 2.6, 'fur')
    a.e(15 + strike * 3 + sw * 1.6, 3, 4.6, 2.4, 'paw')
    # head, tall ears, fluffy cheek
    hx, hy = 15 + strike * 3 - wind * 2, cy + 20 + (1 if clip == 'idle' and n in (2, 3) else 0)
    ear_back = wind * 6 + fall * 14
    for k, (ex, tilt) in enumerate(((-4, -.2), (4, .18))):
        tip = (hx + ex - 5 - ear_back * (1 if k else .8) + sw * 1.2, hy + 31 - ear_back * .8 - k * 2)
        a.c((hx + ex, hy + 6), tip, 3.6, 2.4, 'fur')
        a.c((hx + ex, hy + 7), (tip[0] * .35 + (hx + ex) * .65, tip[1] * .55 + (hy + 7) * .45 - 1), 1.8, 1.4, 'ear')
    a.e(hx, hy, 12.6, 10.6, 'fur')
    a.e(hx - 4, hy + 5, 7, 3.6, 'fur', out=False)
    a.e(hx + 8, hy - 3.4, 6.4, 4.6, 'belly')
    a.dot(hx + 12, hy - 1.6, 'blush', 1)
    a.eye(hx - 1.6, hy + 1.6, 4.6, iris='iris', look=(.7, .1))
    a.dot(hx - 7, hy - 3, 'blush', 2)
    a.dot(hx + 11, hy - 1.2, 'fur0', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.dot(min(8 + k * 4 + (n - 3) * 2, 38), 3 + (k * 5) % 9, 'dust', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def sunbacksnail(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('sunbacksnail', clip, n, sy=1 - fall * .5)
    b = bob * .5
    # slimy foot
    glide = math.sin(n * math.pi / 4) * 1.4 if clip == 'walk' else 0
    a.e(-4, 5, 26, 5.4, 'skin')
    a.e(-10, 7, 14, 2.6, 'skin', out=False)
    a.e(-27, 6 + glide, 5, 3.4, 'skin')
    # head on a raised neck with two eye stalks
    reach = lerp(lerp(0, -4, wind), 8, strike)
    hx, hy = 21 + reach, 20 + b + wind * 4 - strike * 2
    a.c((12, 8), (hx - 2, hy - 3), 6, 5.6, 'skin')
    a.e(hx + 1, hy, 9.4, 8.6, 'skin')
    a.e(hx - 2, hy + 4, 5, 2.6, 'skin', out=False)
    for s, ex in ((0, -4), (1, 5)):
        tip = (hx + ex + 1 + sw * (1 + s), hy + 15 + s * 2 + wind * 2)
        a.c((hx + ex, hy + 6), tip, 1.4, 1.2, 'skin')
        a.eye(tip[0], tip[1] + 2, 3.6, iris='iris', look=(.7, .1))
    a.dot(hx - 4, hy - 2, 'blush', 2)
    a.line((hx + 3, hy - 5 - max(wind * .4, strike) * 2), (hx + 8, hy - 5 - max(wind * .4, strike) * 2), 'ink', 1)
    # the big sun-spiral shell
    sx, sy_ = -7, 29 + b - fall * 4
    a.e(sx, sy_, 21, 20, 'shell')
    a.e(sx - 6, sy_ + 9, 11, 4.6, 'shell', out=False)
    for r, nm in ((15, 'ring0'), (9.6, 'ring1'), (4.6, 'ring0')):
        for k in range(26):
            th = k * 2 * math.pi / 26
            a.dot(sx + math.cos(th) * r * .98, sy_ + math.sin(th) * r * .98, nm, 1)
    spin = n * .3 if clip in ('idle', 'walk') else n * .9
    for k in range(8):
        th = spin + k * math.pi / 4
        a.dot(sx + math.cos(th) * 19.6, sy_ + math.sin(th) * 19, 'ray', 2)
    a.e(sx, sy_, 3.4, 3.4, 'shell', out=True)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(hx + 10 + k * 3, 38), hy - 4 + k * 3, 'slime', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def brushfox(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('brushfox', clip, n, sy=1 - fall * .5)
    a.ox = -2
    hop = max(0, math.sin(n * math.pi / 4)) * 4 if clip == 'walk' else 0
    a.lift = hop + (strike * 7 if clip == 'attack' else 0)
    cy = 26 + bob * .4 - fall * 7
    lunge = strike * 8 - wind * 3
    # legs: dark socks
    for k, lx in enumerate((-15, -9, 9, 15)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 4 if clip == 'walk' else 0
        grp = 'sock' if k % 2 == 0 else 'fur'
        a.c((lx, cy - 2), (lx + 1 + (lunge if k > 1 else 0), 4 + up), 3.6, 2.4, grp)
        a.e(lx + 2 + (lunge if k > 1 else 0), 3 + up, 3.8, 2.2, 'sock')
    # big brush tail with a white tip
    tl = (-28, cy + 12 + sw * 2 + wind * 3)
    a.c((-14, cy + 2), (-26, cy + 7 + wind * 2), 5, 7, 'fur')
    a.e(tl[0], tl[1], 8.4, 11.6, 'fur', ang=.5)
    a.poly([(tl[0] - 7, tl[1] + 9), (tl[0] - 1, tl[1] + 15), (tl[0] + 5, tl[1] + 10), (tl[0] - 1, tl[1] + 5)], 'tip')
    # body and cream belly
    a.e(0, cy + 3, 20, 10.6, 'fur')
    a.e(2, cy - 3, 14, 5, 'cream', out=False)
    a.e(-8, cy + 9, 10, 3.4, 'fur', out=False)
    # head: pointed muzzle, ears, big eyes
    hx, hy = 17 + lunge, cy + 12 - wind * 2 - strike * 3
    a.c((10, cy + 7), (hx - 4, hy - 1), 6, 5, 'fur')
    a.e(hx, hy, 11, 9.6, 'fur')
    a.e(hx - 4, hy + 4, 6, 3, 'fur', out=False)
    a.e(hx + 8, hy - 3, 7.4, 4.6, 'cream')
    a.dot(hx + 13, hy - 1.4, 'nose', 3)
    for s, ex in ((-1, -5), (1, 3)):
        a.poly([(hx + ex - 3, hy + 6), (hx + ex + 1 + s, hy + 17), (hx + ex + 5, hy + 6)], 'fur1')
        a.poly([(hx + ex - 1, hy + 7), (hx + ex + 1 + s * .6, hy + 13), (hx + ex + 3, hy + 7)], 'cream1')
    a.eye(hx - 1.4, hy + 1.6, 4.4, iris='iris', look=(.8, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 5, hy - 6 - jaw), (hx + 11, hy - 6 - jaw), 'mouth1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(hx + 14 + k * 3, 40), 6 + (k * 4) % 10, 'dust', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def spadebadger(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('spadebadger', clip, n, sy=1 - fall * .5)
    a.ox = -4
    cy = 26 + bob * .5 - fall * 7
    # stubby hind legs
    for k, lx in enumerate((-16, -7)):
        step = math.sin(n * math.pi / 4 + k * math.pi) if clip == 'walk' else 0
        up = max(0, step) * 3
        a.c((lx, cy - 3), (lx + step * 3, 5 + up), 6, 4, 'fur')
        a.e(lx + 1 + step * 3, 3 + up, 5.4, 2.8, 'stripe')
    # low barrel body with a pale back stripe
    a.e(-2, cy + 3, 25, 16, 'fur')
    a.e(-4, cy + 12, 17, 3.8, 'white', out=False)
    a.e(-2, cy - 6, 17, 5, 'fur', out=False)
    # big digging forelegs with spade claws (the near one swings)
    gait = math.sin(n * math.pi / 4) if clip == 'walk' else 0
    far = (14 - gait * 5, 6 + max(0, -gait) * 4)
    a.c((9, cy - 1), far, 5, 4.4, 'fur')
    for k in range(3):
        a.c((far[0] + 1, far[1] + 1), (far[0] + 7 + k, far[1] - 4 + k * 2), 1.8, 1, 'claw')
    hand = (lerp(lerp(19, 14, wind), 28, strike), lerp(lerp(8, 30, wind), 3, strike))
    if clip == 'walk':
        hand = (19 + gait * 5, 8 + max(0, gait) * 4)
    if clip == 'die':
        hand = (lerp(19, 24, fall), lerp(8, 3, fall))
    a.c((9, cy + 2), hand, 6, 5.4, 'fur')
    a.e(hand[0] + 1, hand[1], 7, 5, 'fur')
    for k in range(3):
        a.c((hand[0] + 2, hand[1] + 2 - k * 2), (hand[0] + 10, hand[1] + 3 - k * 3.6), 2, 1.2, 'claw')
    # head with the classic white stripes
    hx, hy = 23 + strike * 3, cy + 8 - wind * 1
    a.e(hx, hy, 14.4, 12, 'stripe')
    a.e(hx - 4, hy + 6, 8, 3.4, 'stripe', out=False)
    a.band([(hx - 4, hy + 11), (hx + 3, hy + 11), (hx + 8, hy - 8), (hx - 2, hy - 10)], 'white', out=False)
    a.e(hx + 9, hy - 3, 6.8, 4.4, 'white')
    a.dot(hx + 12, hy - 1.4, 'nose', 3)
    a.eye(hx - 2.8, hy + 1.8, 4.4, iris='iris', look=(.8, .1))
    a.dot(hx - 8, hy - 2.4, 'blush', 2)
    a.e(hx - 8, hy + 10, 3.2, 3.2, 'fur', out=True)
    a.e(hx + 4, hy + 11, 2.8, 2.8, 'fur', out=True)
    if clip == 'attack' and n in (2, 3, 4, 5):
        for k in range(6):
            a.e(min(hand[0] + 6 + k * 2.4, 38), 6 + (k * 7) % 14 + (n - 3) * 2, 2.2, 1.8, 'dirt', out=False)
    return a.done()


# ------------------------------------------------------------------------------------------------
def honeyjaw(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('honeyjaw', clip, n, sy=1 - fall * .5)
    a.ox = -3
    b = bob * .6
    cy = 40 + b - fall * 10
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 10, cy - 12), (s * 12, 6 + up), 8, 6.6, 'fur')
        a.e(s * 12.4, 4 + up, 9.6, 4.6, 'fur')
        for k in range(3):
            a.dot(s * 12 + 4 + k * 2.4, 3 + up, 'claw1', 1)
    # beehive on its back, with bees
    hv = (-14, cy + 14 + b * 0)
    for k, (w, h, dy) in enumerate(((13, 5.6, 0), (11, 5.4, 8), (8.6, 5, 15), (5, 3.8, 21))):
        a.e(hv[0], hv[1] + dy - 5, w, h, 'hive')
    a.e(-12, cy + 8, 4.6, 3.4, 'honey', out=False)
    for k in range(2):
        bx = -26 + k * 8 + math.sin(n * 1.2 + k * 2) * 3
        by = cy + 30 + math.cos(n * 1.5 + k) * 3
        a.e(bx, by, 2.8, 2.2, 'bee')
        a.dot(bx - 1, by + 2.4, 'wing', 2)
    # body, pale belly, honey-stained fur
    a.e(0, cy, 26, 23, 'fur')
    a.e(-9, cy + 11, 14, 6, 'fur', out=False)
    a.e(4, cy - 6, 15, 12, 'belly')
    # arms: far one hangs, near one swipes
    a.c((-18, cy + 8), (-26, cy - 6 + sw), 6, 5, 'fur')
    a.e(-27, cy - 8 + sw, 6.4, 5, 'fur')
    fist = (lerp(lerp(24, 22, wind), 32, strike), lerp(lerp(cy - 4, cy + 28, wind), cy - 12, strike))
    if clip == 'die':
        fist = (lerp(24, 30, fall), lerp(cy - 4, 7, fall))
    a.c((16, cy + 10), fist, 6.4, 5.6, 'fur')
    a.e(fist[0], fist[1], 7.4, 6, 'fur')
    for k in range(3):
        a.poly([(fist[0] + 6, fist[1] + 3 - k * 3.4), (fist[0] + 12.4, fist[1] + 2 - k * 3.6), (fist[0] + 6, fist[1] + 1 - k * 3.4)], 'claw1')
    # head with round ears, big honey-dripping jaw
    hx, hy = 8 + strike * 3 - wind * 2, cy + 24 - fall * 2
    for s in (-1, 1):
        a.e(hx + s * 10.4, hy + 9, 5, 4.6, 'fur')
        a.e(hx + s * 10.4, hy + 9, 2.4, 2.2, 'belly', out=False)
    a.e(hx, hy, 15, 12.6, 'fur')
    a.e(hx - 5, hy + 6, 8, 3.8, 'fur', out=False)
    a.e(hx + 7, hy - 4, 9.4, 6.6, 'belly')
    a.dot(hx + 14, hy - 1.6, 'ink', 4)
    a.eye(hx - 2.6, hy + 2, 4.6, iris='iris', look=(.7, .1))
    a.eye(hx + 7, hy + 2, 3.8, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 3, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 3, hy - 8 - jaw), (hx + 13, hy - 8 - jaw), 'mouth1', 1)
    # a honey-coated chin with two drips
    a.e(hx + 6, hy - 10, 9.4, 3.8, 'honey')
    for k, dx in enumerate((2, 10)):
        ln = 4 + (k * 3 + n) % 4 + wind * 2
        a.c((hx + dx, hy - 11), (hx + dx, hy - 12 - ln), 1.8, 1.8, 'honey')
        a.e(hx + dx, hy - 13 - ln, 2.4, 2.8, 'honey')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(5):
            a.e(min(fist[0] + 8 + k * 2, 40), fist[1] - 6 + k * 4 + (k % 2) * 2, 2.2, 2.6, 'honey', out=False)
    return a.done()


# ------------------------------------------------------------------------------------------------
def wickerwarden(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('wickerwarden', clip, n, sy=1 - fall * .5)
    a.ox = -2
    a.pk = .9
    b = bob * .6
    # two short wooden post legs
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 7, 24), (s * 9, 5 + up), 5, 4.4, 'post')
        a.e(s * 10, 3.6 + up, 7, 3.4, 'post')
    # tattered straw skirt
    for k in range(9):
        x = -17 + k * 4.2
        a.poly([(x - 2.6, 26), (x + .4 + (k % 2) * 2 + sw * .4, 15 - (k % 3) * 2), (x + 3, 26)], 'straw2' if k % 2 else 'straw1')
    # woven barrel torso with a rope belt
    a.e(0, 40 + b, 18, 17, 'wicker')
    a.e(-6, 47 + b, 9, 4.4, 'wicker', out=False)
    for k in range(5):
        a.line((-16 + k * 8, 28 + b), (-14 + k * 7, 52 + b), 'wicker0', 1)
    for k in range(4):
        a.line((-16, 31 + k * 6 + b), (16, 33 + k * 6 + b), 'wicker0', 1)
    a.line((-17, 36 + b), (17, 36 + b), 'band1', 2)
    # far arm with straw cuff; near arm swings a rusty scythe
    a.c((-14, 46 + b), (-24, 36 + b + sw), 4.4, 3.6, 'wicker')
    for k in range(3):
        a.c((-24, 36 + b + sw), (-28 + k * 2, 30 + b + sw - k), 1.4, 1, 'straw')
    hand = (lerp(lerp(21, 17, wind), 27, strike), lerp(lerp(40, 54, wind), 34, strike) + b)
    tip = (min(hand[0] + lerp(lerp(3, -8, wind), 12, strike), 30), lerp(lerp(72, 78, wind), 42, strike))
    low = (hand[0] - 1, lerp(lerp(10, 16, wind), 32, strike))
    if clip == 'die':
        hand = (lerp(21, 28, fall), lerp(40, 8, fall))
        tip = (lerp(24, 32, fall), lerp(72, 12, fall))
        low = (lerp(20, 6, fall), 4)
    a.c((13, 47 + b), hand, 4.6, 4, 'wicker')
    for k in range(3):
        a.c(hand, (hand[0] + 4 + k * 1.6, hand[1] - 5 + k * 3), 1.4, 1, 'straw')
    a.line(low, tip, 'ink', 4)
    a.line(low, tip, 'post1', 2)
    dx_, dy_ = tip[0] - low[0], tip[1] - low[1]
    ln = math.hypot(dx_, dy_) or 1
    ux, uy = dx_ / ln, dy_ / ln
    px, py = -uy, ux
    a.poly([(tip[0] - ux * 2, tip[1] - uy * 2), (tip[0] + px * 12 + ux * 3, tip[1] + py * 12 + uy * 3),
            (tip[0] + px * 10 + ux * 8, tip[1] + py * 10 + uy * 8), (tip[0] + px * 2 + ux * 3, tip[1] + py * 2 + uy * 3)], 'iron1')
    # round woven head with a big straw hat and glowing carved eyes
    hx, hy = 1 + strike * 2, 62 + b
    a.e(hx, hy, 13.4, 12, 'wicker')
    a.e(hx - 5, hy + 6, 7, 3.6, 'wicker', out=False)
    a.line((hx - 10, hy + 2), (hx + 10, hy - 2), 'wicker0', 1)
    a.line((hx - 9, hy - 5), (hx + 9, hy - 8), 'wicker0', 1)
    a.e(hx - 4, hy - .5, 4.6, 4.6, 'glow')
    a.e(hx + 6, hy - .5, 4.2, 4.2, 'glow')
    state = T['state']
    if state == 'dead':
        for ex in (hx - 4, hx + 6):
            a.line((ex - 2, hy - 3), (ex + 2, hy + 1), 'ink', 1)
            a.line((ex - 2, hy + 1), (ex + 2, hy - 3), 'ink', 1)
    else:
        a.dot(hx - 5, hy - 1.4, 'ink', 2)
        a.dot(hx + 5, hy - 1.4, 'ink', 2)
        a.dot(hx - 4.4, hy + 1, 'glow2', 1)
        a.dot(hx + 5.6, hy + 1, 'glow2', 1)
    a.line((hx - 5, hy - 7), (hx + 6, hy - 7 - strike), 'stitch', 1)
    for k in range(4):
        a.line((hx - 4 + k * 3, hy - 9), (hx - 4 + k * 3, hy - 5), 'stitch', 1)
    # hat: wide brim, dome, red band, straw sticking out
    a.e(hx, hy + 9, 21, 4.6, 'hat')
    a.e(hx, hy + 17, 11, 9.4, 'hat')
    a.e(hx - 4, hy + 20, 5.4, 3.2, 'hat', out=False)
    a.line((hx - 10, hy + 11), (hx + 10, hy + 11), 'band1', 2)
    for k in range(3):
        a.c((hx - 18 + k * 3, hy + 8), (hx - 24 + k * 2 + sw, hy + 4 - k * 2), 1.2, .9, 'straw')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(tip[0] + 8 + k * 3, 38), tip[1] - 4 + (k * 7) % 12, 2.4, 'glow1')
    return a.done()


DRAW = dict(meadowhare=meadowhare, sunbacksnail=sunbacksnail, brushfox=brushfox, spadebadger=spadebadger,
            honeyjaw=honeyjaw, wickerwarden=wickerwarden)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/sunward-preview')
    print('ok')
