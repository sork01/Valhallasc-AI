"""Cel-shaded Moonwell enemies (zone 18) for make_moonwell_garden_sprites.py and make_moonwell_sprites.py.

Same recipe as orrery_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi proportions.
96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/moonwell_cel_redraw.py [kind...]` writes contact sheets to test-results/moonwell-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('dew_moth', 'lumen_eel', 'rootbell', 'tideglass_heron', 'hourpetal_stag', 'moonskein_weaver', 'moonwell_echo')

PALETTES = {
    'dew_moth': mk(drop=('#164a62', '#2e8aa6', '#6cd2d2', '#d2fff0'), wing=('#5a6a98', '#a8bcd8', '#e0f0f4', '#fbffff'),
                   lilac=('#43386e', '#8276b5', '#b8a8e4'), gold=('#a8761e', '#f8e8ad', '#fff6d2'), iris='#2aa8b8',
                   blush='#ff9ac0', mist='#d8fff2'),
    'lumen_eel': mk(skin=('#124a5c', '#2e8aa0', '#6ed8c4', '#ccfff0'), fin=('#43386e', '#8276b5', '#c4b4f0'),
                    belly=('#a8e8d4', '#f0fff4'), lure=('#a8761e', '#ffe48a', '#fffbd8'), iris='#1c6a92',
                    blush='#ff9ac0', glow='#e8fff6', bubble='#bef4ff'),
    'rootbell': mk(bell=('#4a5a7a', '#8aa2c0', '#c8e0ea', '#f4fcff'), rim=('#a8761e', '#f8d878', '#fff2b8'),
                   root=('#1c4a50', '#367d91', '#6cc0b8'), leaf=('#1e5a3c', '#3aa06a', '#8ae09a'),
                   clap=('#b4801c', '#f2e2a4', '#fffbe2'), iris='#2a6a86', blush='#f0a6be', note='#c8f8ff'),
    'tideglass_heron': mk(plume=('#2a5a72', '#6aa8b4', '#b8e4de', '#f4ffff'), glass=('#2e8aa6', '#7ad4d8', '#d4fff8'),
                          leg=('#43386e', '#8276b5', '#b8a8e4'), beak=('#a8761e', '#f8c85a', '#fff0a0'),
                          crest=('#c0587c', '#f0a6be', '#ffd8e4'), iris='#1c6a92', blush='#ff9ac0', drip='#bef4ff'),
    'hourpetal_stag': mk(coat=('#34286a', '#6a58a8', '#a898dc', '#e0d8ff'), cream=('#a89ec8', '#f0ecff'),
                         antler=('#6a4a40', '#b08a70', '#f0d8b8'), petal=('#a83a6a', '#f0a6be', '#ffe0ea'),
                         gold=('#a8761e', '#f8e8ad', '#fff6d2'), iris='#2a8aa6', blush='#ff9ac0',
                         hoof=('#2a2040', '#54447e')),
    'moonskein_weaver': mk(yarn=('#4a3a86', '#8276b5', '#b4a4e8', '#e4dcff'), thread=('#c0587c', '#f0a6be', '#ffd8e4'),
                           gold=('#a8761e', '#f8e8ad', '#fff6d2'), needle=('#6a7a8a', '#d8e8f0'),
                           skin=('#b8a0c8', '#e8d8f4'), iris='#d0487c', blush='#ff9ac0', limb=('#3a2e6a', '#6a5aa8')),
    'moonwell_echo': mk(glass=('#10152b', '#1c2141', '#415579', '#7796ae'), shard=('#46597d', '#7c9ab2', '#d0e6df', '#fff9df'),
                        glow=('#2aa890', '#91f6e2', '#d8fff6'), iris='#91d8f6', blush='#eb9bd6', wave=('#58b8b0', '#b8f6ee')),
}
R.PALETTES.update(PALETTES)


def crescent(a, cx, cy, r, shift, a0, a1, group):
    steps = 10
    outer = [(cx + r * math.cos(a0 + (a1 - a0) * k / steps), cy + r * math.sin(a0 + (a1 - a0) * k / steps)) for k in range(steps + 1)]
    inner = [(cx + shift + r * .78 * math.cos(a0 + (a1 - a0) * k / steps), cy + r * .78 * math.sin(a0 + (a1 - a0) * k / steps))
             for k in range(steps, -1, -1)]
    a.band(outer + inner, group)


# ------------------------------------------------------------------------------------------------
def dew_moth(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('dew_moth', clip, n, sy=1 - fall * .5)
    flap = math.sin(n * (math.pi / 3 if clip == 'idle' else math.pi / 2)) * .5
    if clip == 'attack':
        flap = (-.3, -.5, -.6, .7, .8, .4, .1, 0)[n]
    if fall:
        flap = lerp(flap, -.5, fall)
    cy = 50 + bob * 1.4 - fall * 30
    wk = 1 - fall * .35
    # big rounded wings behind the drop: silver above, lilac below
    for s in (-1, 1):
        a.e(s * 20 * wk, cy + 8 + flap * 7, 19, 9.6, 'wing', ang=s * (.5 + flap * .3))
        a.e(s * 20 * wk, cy + 8 + flap * 7, 12, 4, 'wing', ang=s * (.5 + flap * .3), out=False)
        a.e(s * 17 * wk, cy - 11 - flap * 5, 13.6, 6.4, 'lilac', ang=-s * (.62 - flap * .3))
        a.e(s * 27 * wk, cy + 11 + flap * 8, 3.8, 3.8, 'gold')
        a.dot(s * 27 * wk - 1, cy + 12 + flap * 8, 'wing3', 2)
    # the hanging dewdrop body
    a.poly([(-9, cy - 12), (0, cy - 25 - bob * .4), (9, cy - 12)], 'drop1')
    a.e(0, cy - 2, 13.4, 14.4, 'drop')
    a.e(-4, cy + 6, 7, 4, 'drop', out=False)
    a.dot(-7, cy - 4, 'mist', 2)
    # chibi face
    a.eye(-4.4, cy + 2, 4.8, iris='iris', look=(.3, .1))
    a.eye(5.8, cy + 2, 4.4, iris='iris', look=(.8, .1))
    a.dot(-9.6, cy - 3, 'blush', 2)
    a.dot(11, cy - 3, 'blush', 2)
    # tuning-fork antennae with golden tips
    for s in (-1, 1):
        tip = (s * 13 + sw * s, cy + 24 + wind * 2)
        a.c((s * 3, cy + 11), tip, 1.2, .9, 'lilac')
        a.e(tip[0], tip[1], 2.6, 2.6, 'gold')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(6):
            a.dot(min(12 + (n - 3) * 5 + k * 3, 38), cy - 14 - k * 1.5 + (k % 2) * 8, 'mist', 2)
    if clip == 'idle':
        for k in range(3):
            a.dot(-8 + k * 8, cy - 16 - ((n * 3 + k * 4) % 10), 'mist', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def lumen_eel(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('lumen_eel', clip, n, sy=1 - fall * .5)
    ph = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) * (1.4 if clip == 'attack' else 1)
    base = 30 + bob * 1.2 - fall * 20
    segs = 9
    pts = []
    for k in range(segs):
        t = k / (segs - 1)
        x = -28 + t * 50 + strike * 6 * t
        amp = (1 - fall * .8) * (6 + wind * 6)
        y = base + 8 * (1 - t) + math.sin(ph - t * 5.2) * amp * (1 - t * .3) + (t * 8 if clip == 'attack' and strike else 0)
        pts.append((x, y))
    # fins behind the body
    a.poly([(pts[3][0] - 2, pts[3][1] + 4), (pts[2][0] - 8, pts[2][1] + 17 + sw * 2), (pts[4][0] + 3, pts[4][1] + 4)], 'fin1')
    a.poly([(pts[5][0] - 3, pts[5][1] - 3), (pts[4][0] - 9, pts[4][1] - 15 - sw * 2), (pts[6][0] + 2, pts[6][1] - 3)], 'fin1')
    for k in range(segs - 1):
        r0 = 3.4 + math.sin(k / (segs - 1) * math.pi) * 3.6 + (k / (segs - 1)) * 2
        r1 = 3.4 + math.sin((k + 1) / (segs - 1) * math.pi) * 3.6 + ((k + 1) / (segs - 1)) * 2
        a.c(pts[k], pts[k + 1], r0 + .4, r1 + .4, 'skin')
    for k in range(1, segs - 2, 2):
        a.dot(pts[k][0], pts[k][1] - 2, 'belly1', 2)
    # tail fan
    tx, ty = pts[0]
    a.poly([(tx + 1, ty), (tx - 9, ty + 8 + sw * 2), (tx - 8, ty - 7), ], 'fin2')
    # head with a lure
    hx, hy = pts[-1]
    a.e(hx + 1, hy, 11.4, 9.6, 'skin')
    a.e(hx - 3, hy + 4, 6, 3, 'skin', out=False)
    stalk_end = (hx - 2 + sw, hy + 16 + wind * 3)
    a.c((hx - 2, hy + 7), stalk_end, 1.2, .9, 'fin')
    a.e(stalk_end[0], stalk_end[1] + 1, 3.6, 3.6, 'lure')
    a.dot(stalk_end[0] - 1, stalk_end[1] + 2, 'shine', 1)
    a.eye(hx - 1.4, hy + 1.8, 4.2, iris='iris', look=(.4, .1))
    a.eye(hx + 7, hy + 1.2, 3.4, iris='iris', look=(.9, .1))
    a.dot(hx - 5, hy - 3, 'blush', 2)
    jaw = max(wind * .5, strike) * 3
    a.line((hx + 3, hy - 4.6 - jaw), (hx + 11, hy - 3.4 - jaw), 'ink', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(hx + 10 + k * 3, 38), hy - 6 + k * 3, 'glow', 2)
    for k in range(3):
        a.dot(-24 + k * 18 + (n % 3) * 2, 4 + ((n * 2 + k * 5) % 9), 'bubble', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def rootbell(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('rootbell', clip, n, sy=1 - fall * .5)
    b = bob * .6
    # three root feet
    for k, fx in enumerate((-14, 0, 14)):
        up = max(0, math.sin(n * math.pi / 2 + k * 2)) * 4 if clip == 'walk' else 0
        a.c((fx * .6, 22 + b), (fx, 5 + up), 4.4, 3, 'root')
        a.c((fx, 5 + up), (fx + (k - 1) * 4 + 3, 2 + up), 2.4, 1.4, 'root')
    # the bell body: dome plus a flared skirt with a golden rim
    cy = 38 + b - fall * 6
    a.band([(-14, cy + 14), (14, cy + 14), (21, cy - 10), (24, cy - 17), (-24, cy - 17), (-21, cy - 10)], 'bell')
    a.e(0, cy + 12, 14.4, 12.4, 'bell')
    a.e(-5, cy + 18, 7.6, 3.6, 'bell', out=False)
    a.band([(-25, cy - 16), (25, cy - 16), (26, cy - 21), (-26, cy - 21)], 'rim')
    # sway the clapper under the skirt and ring when attacking
    ring = math.sin(n * 1.4) * 5 if clip == 'idle' else sw * 3 + strike * 9 - wind * 6
    a.c((0, cy - 16), (ring, cy - 26), 1.2, 1, 'rim')
    a.e(ring, cy - 27, 4.6, 4.6, 'clap')
    # little leaf sprout on top
    a.c((0, cy + 23), (1, cy + 29), 1.4, 1.2, 'leaf')
    a.e(-5, cy + 31, 5, 2.6, 'leaf', ang=.5)
    a.e(6, cy + 32, 5.4, 2.8, 'leaf', ang=-.5)
    # face and little arm-leaves
    a.eye(-6, cy + 6, 4.8, iris='iris', look=(.3, .1))
    a.eye(6.4, cy + 6, 4.6, iris='iris', look=(.7, .1))
    a.dot(-12, cy + 1, 'blush', 2)
    a.dot(12.6, cy + 1, 'blush', 2)
    a.line((-2, cy - 2), (3, cy - 2 - strike * 2), 'ink', 1)
    for s in (-1, 1):
        a.e(s * 23, cy - 4 + sw * s, 4.6, 2.8, 'leaf', ang=-s * .6)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            diamond(a, min(14 + (n - 3) * 6 + k * 6, 38), cy - 18 + k * 7, 1.8, 3, 'note')
    return a.done()


# ------------------------------------------------------------------------------------------------
def tideglass_heron(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('tideglass_heron', clip, n, sy=1 - fall * .5)
    a.pk = .88
    a.ox = -5
    b = bob * .6
    cy = 40 + b - fall * 14
    # two long legs with knees and toes
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 6 if clip == 'walk' else (4 if clip == 'idle' and s == 1 and n in (2, 3, 4) else 0)
        knee = (s * 5 + 2 + up * .4, 22 - fall * 8)
        foot = (s * 6 + 4, 3 + up)
        a.c((s * 3, cy - 2), knee, 2.2, 1.6, 'leg')
        a.c(knee, foot, 1.6, 1.2, 'leg')
        a.e(foot[0] + 2.4, foot[1], 4, 1.8, 'leg')
    # glassy wing fan behind the body and tail plumes
    for k in range(4):
        wy = cy + 10 - k * 5
        a.poly([(-8, wy + 2), (-30 - k * 2 + sw, wy + 8 - k * 3 + (strike * 5 if k == 0 else 0)), (-12, wy - 6)], 'glass2' if k % 2 else 'glass1')
    a.e(-6, cy + 2, 17, 11.4, 'plume')
    a.e(-4, cy - 4, 10, 4, 'plume', out=False)
    a.band([(-18, cy + 5), (-30, cy + 1), (-22, cy - 3), (-12, cy)], 'glass')
    # neck: S-curve of capsules, lunging on the attack
    reach = lerp(lerp(0, -8, wind), 10, strike)
    drop = lerp(lerp(0, 2, wind), -22, strike)
    n1 = (7, cy + 10)
    n2 = (9 + reach * .3, cy + 22)
    n3 = (5 + reach * .5, cy + 31 + drop * .4)
    hx, hy = 8 + reach, cy + 36 + drop
    if clip == 'die':
        hx, hy = lerp(8, 22, fall), lerp(cy + 36, 10, fall)
        n3 = (lerp(5, 14, fall), lerp(cy + 31, 14, fall))
        n2 = (lerp(9, 12, fall), lerp(cy + 22, 14, fall))
    a.c(n1, n2, 3.4, 2.6, 'plume')
    a.c(n2, n3, 2.6, 2.4, 'plume')
    a.c(n3, (hx, hy), 2.6, 4.6, 'plume')
    # crested head and long bill
    a.e(hx, hy + 1, 8.6, 7.8, 'plume')
    a.e(hx - 3, hy + 5, 5, 2.6, 'plume', out=False)
    for k in range(3):
        a.e(hx - 7 - k * 2, hy + 5 + k * 2.4 + sw * .6, 5, 1.8, 'crest', ang=.4 + k * .2)
    a.poly([(hx + 5, hy + 4), (hx + 22, hy - 2), (hx + 5, hy - 3)], 'beak1')
    a.line((hx + 6, hy), (hx + 19, hy - 1), 'beak0', 1)
    a.eye(hx + 1.4, hy + 2, 3.8, iris='iris', look=(.8, .1))
    a.dot(hx - 4, hy - 2, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.dot(min(hx + 26 + k * 2, 40), hy - 4 + (k * 5) % 10, 'drip', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def hourpetal_stag(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('hourpetal_stag', clip, n, sy=1 - fall * .5)
    a.ox = -5
    b = bob * .6
    cy = 29 + b - fall * 9
    # four sturdy legs (far pair darker)
    for k, lx in enumerate((-18, -8, 8, 18)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 5 if clip == 'walk' else 0
        grp = 'coat' if k in (1, 3) else 'hoof'
        a.c((lx * .85, cy - 3), (lx + (k % 2) * 2, 5 + up), 4.2, 3, grp)
        a.e(lx + (k % 2) * 2 + 1, 3 + up, 3.8, 2.2, 'hoof')
    a.e(-24, cy + 4, 5, 3, 'cream', ang=.6)
    # body with a gold hourglass flank mark
    a.e(-3, cy + 2, 22, 13, 'coat')
    a.e(-8, cy + 8, 14, 5, 'coat', out=False)
    a.e(-3, cy - 5, 14, 5, 'cream', out=False)
    a.poly([(-12, cy + 8), (4, cy + 8), (-4, cy + 2), (4, cy - 4), (-12, cy - 4), (-4, cy + 2)], 'gold1', out=True)
    # neck and head, lowering to charge
    lunge = strike * 4 - wind * 3
    nk = (17 + lunge * .5, cy + 12 - strike * 5)
    hx, hy = 26 + lunge, cy + 19 - strike * 10 + wind * 3
    if clip == 'die':
        hx, hy = lerp(25, 30, fall), lerp(cy + 22, 14, fall)
        nk = (lerp(17, 24, fall), lerp(cy + 14, 16, fall))
    a.c((12, cy + 6), nk, 6.6, 5, 'coat')
    a.e(hx, hy, 11.6, 9.8, 'coat')
    a.e(hx + 7, hy - 3, 6.8, 4.6, 'cream')
    a.dot(hx + 10, hy - 4, 'ink', 3)
    a.eye(hx - 1.6, hy + 2, 4.2, iris='iris', look=(.7, .1))
    a.dot(hx - 6, hy - 3, 'blush', 2)
    a.e(hx - 5, hy + 7, 2.8, 5, 'coat', ang=.5)
    # antlers that branch into petals
    for k, off in enumerate((-5, 3)):
        base = (hx + off, hy + 7)
        mid = (hx + off - 5 + k * 5, hy + 17 + wind * 2)
        top = (hx + off - 8 + k * 14, hy + 27 + sw * .6)
        a.c(base, mid, 1.8, 1.4, 'antler')
        a.c(mid, top, 1.4, 1.1, 'antler')
        a.c(mid, (mid[0] + 8 - k * 14, mid[1] + 4), 1.2, 1, 'antler')
        for t, pt in enumerate((mid, top, (mid[0] + 8 - k * 14, mid[1] + 4))):
            a.e(pt[0], pt[1] + 1, 6 - t, 3.4, 'petal', ang=.9 - t * 1.1 + k)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 10 + k * 4, 38), hy + 10 - k * 4 + (k % 2) * 6, 1.6, 2.6, 'petal1')
    if clip == 'idle':
        diamond(a, hx - 6 + (n % 3) * 3, hy + 4 - (n % 3) * 3 - 8, 1.4, 2.2, 'petal2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def moonskein_weaver(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('moonskein_weaver', clip, n, sy=1 - fall * .5)
    a.ox = -3
    b = bob * .7
    cy = 40 + b - fall * 10
    spin = n * .22
    # halo of gold beads strung behind
    for k in range(14):
        ang = k * 2 * math.pi / 14 + spin
        a.e(math.cos(ang) * 33, cy + 6 + math.sin(ang) * 29 * .75, 2.4, 2.4, 'gold', out=True)
    # four stick legs, two of them needles
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 6, cy - 12), (s * 11, 4 + up), 3.2, 2.2, 'limb')
        a.e(s * 12 + 1, 3 + up, 5, 2.6, 'limb')
    # yarn-ball body wound with thread
    a.e(0, cy, 22, 21, 'yarn')
    a.e(-8, cy + 10, 11, 5, 'yarn', out=False)
    for k in range(4):
        a.line((-16 + k * 2, cy - 12 + k * 7 - 6), (14 - k * 2, cy - 4 + k * 7 - 6 + (k % 2) * 3), 'yarn0', 1)
    a.line((-20, cy + 4), (20, cy - 8), 'thread1', 1)
    a.line((-21, cy - 6), (18, cy + 8), 'thread1', 1)
    # arms: far one holds a needle straight up, near one jabs
    a.c((-18, cy + 4), (-27, cy + 12 + sw * 2), 3.2, 2.6, 'limb')
    a.c((-27, cy + 12 + sw * 2), (-26, cy + 30 + sw * 2), 1.6, 1.2, 'needle')
    a.e(-27, cy + 12 + sw * 2, 3, 3, 'skin')
    hand = (lerp(lerp(24, 20, wind), 33, strike), lerp(lerp(cy + 4, cy + 20, wind), cy - 6, strike))
    if clip == 'die':
        hand = (lerp(24, 30, fall), lerp(cy + 4, 8, fall))
    a.c((16, cy + 4), hand, 3.2, 2.6, 'limb')
    a.e(hand[0], hand[1], 3, 3, 'skin')
    tip = (hand[0] + 5 + strike * 4, hand[1] + 14 - strike * 12)
    a.line(hand, tip, 'ink', 3)
    a.line(hand, tip, 'needle1', 1)
    a.e(tip[0], tip[1], 1.8, 1.8, 'gold')
    # face: big sleepy eyes in a pale mask
    a.e(1, cy + 2, 13.4, 10.6, 'skin')
    a.e(-3, cy + 6, 7, 3.4, 'skin', out=False)
    a.eye(-3.6, cy + 3.6, 4.8, iris='iris', look=(.3, .1))
    a.eye(6.4, cy + 3.6, 4.4, iris='iris', look=(.8, .1))
    a.dot(-9, cy - 1, 'blush', 2)
    a.dot(11, cy - 1, 'blush', 2)
    a.line((-1, cy - 3), (4, cy - 3 - strike * 2), 'ink', 1)
    # a loose thread end with a moon bead
    a.c((-6, cy + 20), (-9 + sw * 2, cy + 27), 1, .8, 'thread')
    a.e(-9 + sw * 2, cy + 28, 2.6, 2.6, 'gold')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            a.line((min(tip[0] + 3, 36), tip[1] - 4 + k * 4), (min(tip[0] + 10 + k * 2, 40), tip[1] - 4 + k * 5), 'thread2', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def moonwell_echo(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('moonwell_echo', clip, n, sy=1 - fall * .5)
    a.pk = .94
    b = bob * 1.3
    cy = 46 + b - fall * 26
    flare = max(wind, strike)
    # ripple ring on the ground
    a.e(0, 3, 22 + flare * 4, 4.2, 'wave', out=True)
    a.e(0, 3.4, 14, 2.6, 'glow', out=False)
    # orbiting crystal shards: crown and sides, a hollow mirror mask
    for s in (-1, 1):
        sx = s * (24 + flare * 6 + math.sin(n * .9 + s) * 2)
        sy_ = cy + 4 + math.cos(n * .9 + s) * 2
        a.poly([(sx, sy_ + 14), (sx + 5, sy_), (sx, sy_ - 11), (sx - 5, sy_)], 'shard1')
        a.poly([(sx, sy_ + 14), (sx + 5, sy_), (sx, sy_)], 'shard2', out=False)
    for k, (dx, h) in enumerate(((-12, 11), (0, 17), (12, 11))):
        a.poly([(dx - 5, cy + 17), (dx, cy + 17 + h), (dx + 5, cy + 17)], 'shard1')
        a.poly([(dx - 1, cy + 17), (dx, cy + 17 + h), (dx + 5, cy + 17)], 'shard2', out=False)
    # the round dark-glass body with bright facets and a reflection streak
    a.e(0, cy, 22, 21, 'glass')
    a.e(-8, cy + 10, 10, 5, 'glass', out=False)
    a.poly([(-14, cy + 12), (-4, cy + 20), (-2, cy + 4)], 'shard2', out=False)
    a.poly([(14, cy + 12), (4, cy + 20), (2, cy + 4)], 'shard1', out=False)
    a.poly([(-13, cy - 13), (-3, cy - 18), (0, cy - 6)], 'shard1', out=False)
    # three big eyes
    for ex, ey, er in ((-8.4, cy + 1, 4.8), (8.4, cy + 1, 4.8), (0, cy - 8.6, 4)):
        a.eye(ex, ey, er, iris='iris', look=(.4, .1))
    a.dot(-13, cy - 5, 'blush', 2)
    a.dot(13, cy - 5, 'blush', 2)
    if clip == 'attack' and n in (3, 4, 5):
        w = 4 + (n - 3) * 2
        for k in range(3):
            a.e(min(26 + k * 4 + (n - 3) * 2, 40), cy - 4, 1.6 + k, 6 + k * 2 + w * .4, 'wave', out=False)
    if clip == 'idle':
        for k in range(3):
            a.dot(-18 + k * 18 + (n % 2) * 2, cy + 22 - ((n * 3 + k * 4) % 10), 'glow1', 1)
    return a.done()


DRAW = dict(dew_moth=dew_moth, lumen_eel=lumen_eel, rootbell=rootbell, tideglass_heron=tideglass_heron,
            hourpetal_stag=hourpetal_stag, moonskein_weaver=moonskein_weaver, moonwell_echo=moonwell_echo)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/moonwell-preview')
    print('ok')
