"""Cel-shaded Rán's Deep enemies (zone 8) for make_deep_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi
proportions. 96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/deep_cel_redraw.py [kind...]` writes contact sheets to test-results/deep-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw')

PALETTES = {
    'draugr': mk(skin=('#2a4a52', '#4a7a80', '#80b4b0', '#c0e4dc'), weed=('#143a22', '#2a7a3a', '#5cb85a'),
                 cloth=('#3a3226', '#6a5a40', '#9a8660'), rust=('#4a2a1c', '#8a4a30', '#c07848'),
                 blade=('#5a6a6a', '#a0b4b0', '#e4f4f0'), wood=('#4a3220', '#7a5634', '#b08454'),
                 glow=('#d8fff4', '#7af0d8'), iris='#5af0d0', barn=('#c8c0a8', '#f4f0e0'), mouth=('#3a1424', '#a84868')),
    'angler': mk(body=('#0e3050', '#1f5e8a', '#4a9cc4', '#a0daf0'), belly=('#8ab8d0', '#cce8f4', '#f2fbff'),
                 fin=('#1a2a6a', '#3a56b0', '#7a9ae0'), lamp=('#2a8a7a', '#6af0d8', '#d8fff4'), tooth=('#d8e4ee', '#ffffff'),
                 iris='#ffd23a', blush='#ff8a98', mouth=('#4a1430', '#a83860')),
    'moray': mk(skin=('#2a4a22', '#4a7a3a', '#86b858', '#d0ee98'), belly=('#b8c880', '#e4eeb0', '#f8fcd8'),
                spot=('#1a2a14', '#3a5a28'), tooth=('#e4eaf0', '#ffffff'), iris='#ff4a4a', blush='#ff9a8a',
                mouth=('#4a1430', '#c0486a')),
    'siren': mk(tail=('#3a2a7a', '#6a4ac0', '#a284f0', '#d8c8ff'), skin=('#b898d0', '#e8d0f4', '#fff2ff'),
                hair=('#1a4a8a', '#3a82d0', '#82c0f8'), shell=('#d89ab8', '#ffc8dc', '#fff0f6'), fin=('#8a3a8a', '#d86ad0', '#ffa8f0'),
                iris='#e03a9c', mouth=('#4a1c3c', '#d8588a'), blush='#ff9ac0', note=('#ffffff', '#bfeaff')),
    'shellback': mk(shell=('#2a3a36', '#4a6a5a', '#7aa488', '#bcdcc0'), weed=('#143a22', '#2a7a3a', '#5cb85a'),
                    skin=('#4a6a3a', '#7ea45a', '#bcdc88'), barn=('#c8c0a8', '#f4f0e0'), wood=('#4a3220', '#7a5634', '#b08454'),
                    iris='#ffd23a', blush='#ff9a8a', beak=('#a86a14', '#e0a428', '#ffe07a')),
    'kraken': mk(dome=('#2a1a5a', '#5a3aa8', '#9a72e0', '#d8c4ff'), tent=('#3a2478', '#7a54c8', '#b494f4', '#e4d8ff'),
                 sucker=('#e8c4f0', '#fff0fb'), beak=('#4a3a2a', '#8a7048', '#d8b878'), iris='#ffd23a',
                 blush='#ff8ac0', mark=('#1a1040', '#44287e')),
    'hvitserk': mk(coat=('#14243a', '#2a4a6e', '#4a7aa8', '#8ab8e0'), skin=('#2a4a52', '#4a7a80', '#80b4b0'),
                   hat=('#10101c', '#2a2a40', '#4a4a68'), gold=('#7a4f12', '#c98f28', '#f6d467', '#fff0a0'),
                   beard=('#6a8a90', '#b4d0d0', '#eef8f6'), blade=('#5a6a6a', '#a0b4b0', '#e4f4f0'), glow=('#d8fff4', '#7af0d8'),
                   iris='#5af0d0', wood=('#4a3220', '#7a5634', '#b08454'), weed=('#143a22', '#2a7a3a', '#5cb85a'),
                   mouth=('#3a1424', '#a84868')),
    'ghostmaw': mk(body=('#2a6a68', '#4aaea4', '#8ae0d0', '#d4fff4'), belly=('#a8e4d8', '#e0fff6', '#f6fffc'),
                   ghost=('#7af0d8', '#c8fff0'), tooth=('#e8f4f0', '#fdfffe'), iris='#fff0a0', mouth=('#0e2a38', '#1a5a6a'),
                   fin=('#1e5a6a', '#3a96a0', '#7ad0cc'), blush='#ffb0b8'),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def biped(a, clip, n, T, who):
    """Shared legs for the two drowned sailors."""
    for sg in (-1, 1):
        up = max(0, sg * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((sg * 7, 22), (sg * 7, 6 + up), 4.4, 3.8, 'skin')
        a.e(sg * 7.6, 4 + up, 7, 3.8, 'cloth' if who == 'draugr' else 'hat')


def draugr(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('draugr', clip, n, sy=1 - fall * .5)
    b = bob * .5
    biped(a, clip, n, T, 'draugr')
    a.band([(-11, 25), (11, 25), (14, 13), (8, 17), (3, 11), (-3, 17), (-8, 11), (-14, 14)], 'cloth')
    far = (-19, 34 + b + wind * 3)
    a.c((-9, 42 + b), far, 3.4, 3, 'skin')
    a.e(far[0], far[1], 3.2, 3.2, 'skin')
    a.e(0, 34 + b, 12.6, 11.4, 'cloth')
    a.e(-4, 39 + b, 6.6, 4, 'cloth', out=False)
    a.line((-8, 36 + b), (6, 30 + b), 'rust0', 1)
    for (x, y) in ((-6, 30), (4, 38)):
        a.e(x, y + b, 1.8, 1.6, 'barn')
    hand = (lerp(lerp(17, 14, wind), 24, strike), lerp(lerp(33, 40, wind), 33, strike))
    ang = lerp(lerp(1.45, 2.0, wind), .2, strike)
    if clip == 'die':
        hand = (lerp(17, 23, fall), lerp(33, 8, fall))
        ang = lerp(1.45, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 10, hand[1] - dy * 10)
    top = (min(hand[0] + dx * 22, 26), min(hand[1] + dy * 22, 66))
    a.line(base, top, 'ink', 4)
    a.line(base, top, 'wood1', 2)
    px, py = dy, -dx
    blade = [(top[0] - dx * 7, top[1] - dy * 7), (top[0] + px * 11 - dx * 9, top[1] + py * 11 - dy * 9),
             (top[0] + px * 12 + dx * 5, top[1] + py * 12 + dy * 5), (top[0] + dx * 3, top[1] + dy * 3)]
    a.band(blade, 'blade')
    a.line((blade[1][0], blade[1][1]), (blade[2][0], blade[2][1]), 'rust1', 1)
    a.c((9, 41 + b), hand, 3.6, 3.2, 'skin')
    a.e(hand[0], hand[1], 3.4, 3.2, 'skin')
    for sg in (-1, 1):
        a.e(sg * 12.6, 42 + b, 4.8, 4.2, 'skin')
    hx, hy = 1, 56 + b
    a.e(hx, hy, 13, 11.6, 'skin')
    a.e(hx - 4, hy + 6, 7, 4, 'skin', out=False)
    # seaweed hair and a barnacle on the cheek
    for k, (dx_, h, tl) in enumerate(((-9, 9, -4), (-3, 12, -1), (3, 11, 2), (9, 8, 4))):
        a.poly([(hx + dx_ - 2.4, hy + 9), (hx + dx_ + tl, hy + 9 + h), (hx + dx_ + 2.6, hy + 9)], 'weed1')
    a.poly([(hx - 13, hy + 2), (hx - 17, hy - 8), (hx - 9, hy - 4)], 'weed1')
    a.eye(hx - 3.2, hy + 1, 4.4, iris='iris', look=(.3, .1))
    a.eye(hx + 6.4, hy + 1, 4, iris='iris', look=(.9, .1))
    a.e(hx + 9.5, hy - 5.4, 1.8, 1.6, 'barn')
    mouth = max(wind * .6, strike) * 3
    a.e(hx + 1.6, hy - 6.4 - mouth * .4, 3.6, 1.6 + mouth, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(top[0] + 6 + k * 4, 36), top[1] - 6 + k * 4, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def angler(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('angler', clip, n, sy=1 - fall * .3)
    cy = 36 + bob * 1.2 - fall * 20
    lean = strike * 4 - wind * 3
    flap = math.sin(n * math.pi / 2) * 3
    # tail and fins
    a.poly([(-15, cy + 1), (-32 - lean, cy + 10 + flap), (-33 - lean, cy - 9 - flap), (-15, cy - 3)], 'fin1')
    a.poly([(-3, cy + 12), (3 + flap, cy + 24), (8, cy + 11)], 'fin1')
    a.poly([(-8, cy - 12), (-2, cy - 22 - flap), (6, cy - 12)], 'fin1')
    a.e(-4, cy, 21, 15, 'body')
    a.e(-1, cy - 8, 15, 5.4, 'belly', out=False)
    for k in range(3):
        a.dot(-14 + k * 6, cy + 6 - (k % 2) * 4, 'fin2', 2)
    # lantern on a stalk
    gl = 'lamp2' if (clip == 'idle' and n % 2) or clip == 'attack' else 'lamp1'
    a.c((6, cy + 13), (18 + lean, cy + 25), 1.4, 1.2, 'fin')
    a.e(21 + lean, cy + 24, 6.6, 6.6, 'lamp')
    a.e(21 + lean, cy + 24, 3.2, 3.2, 'lamp', out=False)
    a.dot(19 + lean, cy + 26, 'shine', 2)
    # head and the wide toothy mouth
    hx, hy = 15 + lean, cy
    gape = max(wind * .5, strike) * 5
    a.e(hx + 3, hy - 8 - gape, 13, 5, 'belly')
    for k in range(5):
        a.poly([(hx - 5 + k * 4.4, hy - 7 - gape), (hx - 3.2 + k * 4.4, hy - 2 - gape), (hx - 1.6 + k * 4.4, hy - 7 - gape)], 'tooth1', out=False)
    a.e(hx + 2, hy - 4 - gape / 2, 12, 5 + gape / 2, 'mouth')
    a.e(hx, hy + 1, 13, 11.4, 'body')
    for k in range(5):
        a.poly([(hx - 7 + k * 4.4, hy - 5), (hx - 5.4 + k * 4.4, hy + 0), (hx - 3.6 + k * 4.4, hy - 5)], 'tooth1', out=False)
    a.eye(hx + 3, hy + 4, 5.4, iris='iris')
    a.dot(hx - 6, hy - 1, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(hx + 18 + k * 4, 37), hy - 4 + (k % 2) * 6, 2.4, 'lamp2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def moray(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('moray', clip, n, sy=1 - fall * .2)
    k = 1 - fall * .55
    ph = n * math.pi / 3 if clip == 'idle' else n * math.pi / 2
    amp = 3.4 if clip != 'idle' else 2
    base = [(-36, 6), (-26, 8), (-16, 11), (-7, 14), (2, 17), (10, 22), (14, 28)]
    radii = [2.2, 3.6, 5.2, 6.6, 7.6, 8, 7.6]
    pts = []
    for i, (x, y) in enumerate(base):
        w = math.sin(i * 1.1 - ph) * amp * (1 if i < 6 else .4)
        pts.append((x, (y + w) * k + (bob * .5 if i > 3 else 0)))
    hx = lerp(lerp(16, 10, wind), 22, strike)
    hy = lerp(lerp(34, 38, wind), 28, strike)
    if clip == 'die':
        hx, hy = lerp(16, 24, fall), lerp(34, 12, fall)
        pts[-1] = (lerp(14, 18, fall), lerp(28, 10, fall))
    for i in range(len(pts) - 1):
        a.c(pts[i], pts[i + 1], radii[i], radii[i + 1], 'skin')
    for i in range(1, 6):
        x, y = pts[i]
        a.e(x + 1, y - radii[i] * .55, radii[i] * .5, radii[i] * .38, 'belly', out=False)
        a.e(x - 1, y + radii[i] * .3, 1.8, 1.5, 'spot')
    a.c(pts[-2], (hx - 3, hy - 4), radii[-2], 7, 'skin')
    # dorsal fin ridge
    for i in range(1, 6):
        x, y = pts[i]
        a.poly([(x - 3, y + radii[i] - 1), (x - 1, y + radii[i] + 5), (x + 3, y + radii[i] - 1)], 'skin1')
    jaw = max(wind * .5, strike) * 7 + (2 if clip == 'idle' else 0)
    a.e(hx + 7, hy - 6 - jaw, 8.4, 3.4, 'belly')
    if jaw > 1.5:
        a.e(hx + 8, hy - 4 - jaw / 2, 6.6, jaw / 2 + 1.4, 'mouth')
    for t in range(3):
        a.poly([(hx + 3 + t * 4, hy - 5 - jaw), (hx + 4.6 + t * 4, hy - 1 - jaw), (hx + 6 + t * 4, hy - 5 - jaw)], 'tooth1', out=False)
    a.e(hx, hy, 12.6, 10, 'skin')
    a.e(hx + 9, hy - 2.6, 8.4, 5.2, 'skin')
    a.e(hx + 5, hy - 4.6, 9, 3.4, 'belly', out=False)
    a.dot(hx + 15, hy - 1.4, 'ink', 2)
    for t in range(3):
        a.poly([(hx + 3 + t * 4, hy - 1), (hx + 4.6 + t * 4, hy - 5), (hx + 6 + t * 4, hy - 1)], 'tooth1', out=False)
    a.eye(hx + 2.4, hy + 2, 4.7, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for t in range(3):
            star(a, min(hx + 20 + t * 4, 38), hy - 4 + (t % 2) * 5, 2.3, 'belly1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def siren(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('siren', clip, n, sy=1 - fall * .5)
    a.lift = 5 + bob * 1.2 - fall * 5
    sway = math.sin(n * math.pi / 3) * 1.8 if clip == 'idle' else sw * 2
    hx, hy = 2 + sway * .3, 59
    # long hair streaming behind
    a.c((hx - 6, hy + 2), (hx - 16 - sway, hy - 26), 9, 1.6, 'hair')
    a.c((hx - 1, hy), (hx - 6 - sway, hy - 30), 7, 1.4, 'hair')
    a.e(hx - 2, hy - 1, 15.4, 14, 'hair')
    # curled tail ending in a big fin
    sw2 = math.sin(n * 1.3) * 2.5
    a.c((0, 30), (-4, 18), 9, 7, 'tail')
    a.c((-4, 18), (6 + sw2, 8), 7, 5, 'tail')
    a.c((6 + sw2, 8), (16 + sw2, 12), 5, 3, 'tail')
    a.poly([(16 + sw2, 12), (30 + sw2, 20), (28 + sw2, 4), (22 + sw2, 8)], 'fin1')
    for k in range(4):
        a.dot(-2 + k * 2, 28 - k * 4, 'tail3', 2)
    a.e(0, 38, 9.4, 8.6, 'skin')
    a.e(0, 41, 9.6, 4, 'shell', out=False)
    a.e(-4, 41, 4.6, 3.8, 'shell')
    a.e(4, 41, 4.6, 3.8, 'shell')
    open_ = max(wind, strike)
    for sg in (-1, 1):
        hand = (sg * lerp(15, 24, open_), lerp(36, 47, open_))
        a.c((sg * 8, 42), hand, 3.2, 2.8, 'skin')
        a.e(hand[0], hand[1], 2.8, 2.8, 'skin')
    a.e(hx, hy, 12.2, 11.4, 'skin')
    a.poly([(hx - 13, hy + 5), (hx - 8, hy - 3), (hx - 3, hy + 6), (hx + 2, hy - 2), (hx + 7, hy + 6), (hx + 13, hy - 1),
            (hx + 14, hy + 11), (hx - 14, hy + 11)], 'hair1')
    a.e(hx - 6, hy + 8, 3.6, 3, 'shell')
    a.eye(hx + 2.4, hy - 2.4, 4.4, iris='iris')
    a.eye(hx + 10, hy - 2.4, 3.3, iris='iris')
    a.dot(hx - 4, hy - 6.4, 'blush', 3)
    o = max(wind * .6, strike) * 3
    a.e(hx + 5.6, hy - 7.6 - o * .4, 2.4 + o * .4, 1.4 + o, 'mouth')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            x = min(hx + 18 + k * 5 + (n - 3) * 2, 38)
            a.e(x, hy - 2 + (k % 2) * 8 - k, 2.2, 2.2, 'note')
            a.line((x + 2, hy - 2 + (k % 2) * 8 - k), (x + 2, hy + 4 + (k % 2) * 8 - k), 'note0', 1)
    return a.done()


# ------------------------------------------------------------------------------------------------
def shellback(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('shellback', clip, n, sy=1 - fall * .25)
    by = 20 + bob * .5 - fall * 4
    for lx, ph in ((-18, 1.6), (6, 0), (-8, 0), (16, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 3 if clip == 'walk' else 0
        a.c((lx, by - 2), (lx + 2, up + 3.4), 5, 3.8, 'skin')
        a.e(lx + 4, up + 3, 5.6, 2.6, 'skin')
    a.c((-22, by + 2), (-32, by - 1), 4, 1.6, 'skin')
    # great domed shell with barnacles, kelp and a barnacled plank stuck in it
    a.e(-4, by + 3, 26, 17, 'shell')
    a.e(-10, by + 11, 13, 5, 'shell', out=False)
    for k in range(4):
        a.line((-22 + k * 8, by + 1), (-18 + k * 8, by + 17), 'shell0', 1)
    a.line((-24, by + 3), (14, by + 3), 'shell0', 1)
    for (x, y) in ((-14, 12), (2, 15), (8, 8), (-6, 5)):
        a.e(x, by + y, 2.4, 2, 'barn')
    a.line((-16, by + 14), (4, by + 22), 'ink', 5)
    a.line((-16, by + 14), (4, by + 22), 'wood1', 3)
    for k in range(3):
        a.poly([(-22 + k * 5, by + 12), (-19 + k * 5, by + 24 + (k % 2) * 3), (-17 + k * 5, by + 12)], 'weed1')
    hx = lerp(lerp(22, 15, wind), 25, strike)
    hy = lerp(by + 5, by + 2, strike) - fall * 2
    if clip == 'die':
        hx, hy = lerp(22, 24, fall), lerp(by + 5, 9, fall)
    a.c((14, by + 2), (hx - 4, hy), 7, 7, 'skin')
    jaw = max(wind * .4, strike) * 4
    a.e(hx + 6, hy - 5 - jaw, 6.4, 2.8, 'beak')
    a.e(hx, hy, 11, 9.4, 'skin')
    a.e(hx + 8, hy - 2, 7.6, 5.2, 'skin')
    a.poly([(hx + 9, hy - 1), (hx + 18, hy - 3 - jaw * .4), (hx + 14, hy - 7), (hx + 8, hy - 5)], 'beak1')
    a.eye(hx + 1.6, hy + 2, 4.4, iris='iris')
    a.dot(hx - 4, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            a.e(min(hx + 18 + k * 4, 38), hy + 1 + (k % 2) * 5, 2.2, 2.2, 'barn')
    return a.done()


# ------------------------------------------------------------------------------------------------
def kraken(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('kraken', clip, n, sy=1 - fall * .45)
    b = bob * .8
    cy = 40 + b - fall * 16
    # tentacles curling out on the ground; the near pair reach on the attack
    for k, (x0, x1, h) in enumerate(((-22, -34, 14), (-12, -22, 7), (8, 22, 7), (16, 32, 14), (-3, 4, 4))):
        wv = math.sin(n * .9 + k * 1.3) * 3
        reach = strike * 6 if k in (3, 4) else 0
        top = h + 12 + wv - fall * 10
        a.c((x0 * .5, cy - 8), (x0 * .8 + (x1 - x0) * .3, top * .8 * (1 - fall * .6)), 5.4, 4.2, 'tent')
        a.c((x0 * .8 + (x1 - x0) * .3, top * .8 * (1 - fall * .6)), (x1 + reach, 3 + h * .2 * (1 - fall)), 4.2, 1.6, 'tent')
        for t in range(2):
            a.dot(x1 * .8 + x0 * .2 + t * 3, 6 + h * .3 + t * 4, 'sucker1', 2)
    a.e(0, cy, 24, 21, 'dome')
    a.e(-8, cy + 10, 12, 6.4, 'dome', out=False)
    for (x, y) in ((-12, 8), (-4, 14), (8, 10)):
        a.e(x, cy + y, 2.4, 2, 'mark')
    a.e(3, cy - 12, 17, 5.4, 'tent', out=False)
    a.poly([(1, cy - 14), (7, cy - 14), (4, cy - 22)], 'beak1')
    gape = max(wind * .5, strike) * 3
    a.poly([(-1, cy - 12 - gape), (4, cy - 12 - gape), (2, cy - 17 - gape)], 'beak1', out=False) if False else None
    a.eye(-6, cy + 3, 6, iris='iris', look=(.4, .1))
    a.eye(8, cy + 3, 5.4, iris='iris', look=(.9, .1))
    a.dot(-13, cy - 3, 'blush', 4)
    a.dot(14, cy - 3, 'blush', 3)
    if clip == 'attack' and n in (4, 5):
        for k in range(4):
            a.e(min(30 + k * 2, 38), 6 + (k * 7) % 11 + (n - 4) * 3, 2.4, 2.4, 'sucker')
    return a.done()


# ------------------------------------------------------------------------------------------------
def hvitserk(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('hvitserk', clip, n, sy=1 - fall * .5)
    b = bob * .5
    flow = math.sin(n * math.pi / 3) * 1.5 if clip == 'idle' else sw * 2
    a.band([(-9, 52 + b), (9, 52 + b), (17 + flow, 30), (21 + flow * 1.4, 7), (-21 + flow, 7), (-17, 30)], 'coat')
    for sg in (-1, 1):
        up = max(0, sg * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((sg * 7, 22), (sg * 7, 6 + up), 4.4, 3.8, 'skin')
        a.e(sg * 7.6, 4 + up, 7.4, 4, 'hat')
        a.line((sg * 7 - 3, 10 + up), (sg * 7 + 3, 10 + up), 'gold1', 1)
    a.band([(-12, 26), (12, 26), (16, 14), (8, 18), (0, 12), (-8, 18), (-16, 14)], 'coat')
    a.e(0, 36 + b, 14.4, 12, 'coat')
    a.e(-5, 41 + b, 7.4, 4.2, 'coat', out=False)
    for k in range(3):
        a.e(-4 + k * 4, 38 + b - k * .6, 1.4, 1.4, 'gold') if False else a.dot(-5 + k * 4, 36 + b, 'gold2', 2)
    a.line((-14, 28 + b), (14, 28 + b), 'gold1', 2)
    far = (-21, 36 + b + (sw * 2 if clip == 'walk' else 0))
    a.c((-11, 44 + b), far, 3.8, 3.4, 'coat')
    a.e(far[0], far[1], 3.4, 3.4, 'skin')
    hand = (lerp(lerp(19, 15, wind), 25, strike), lerp(lerp(34, 42, wind), 34, strike))
    ang = lerp(lerp(1.5, 2.0, wind), .2, strike)
    if clip == 'die':
        hand = (lerp(19, 24, fall), lerp(34, 8, fall))
        ang = lerp(1.5, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 5, hand[1] - dy * 5)
    tip = (min(hand[0] + dx * 28, 28), min(hand[1] + dy * 28, 70))
    a.line(base, tip, 'ink', 6)
    a.line(base, tip, 'blade1', 4)
    a.line(base, tip, 'blade2', 1)
    a.line((hand[0] - dy * 6, hand[1] + dx * 6), (hand[0] + dy * 6, hand[1] - dx * 6), 'gold1', 3)
    a.c((10, 44 + b), hand, 3.8, 3.4, 'coat')
    a.e(hand[0], hand[1], 3.6, 3.4, 'skin')
    for sg in (-1, 1):
        a.e(sg * 15, 45 + b, 7.6, 6.4, 'coat')
        a.line((sg * 15 - 4, 44 + b), (sg * 15 + 4, 44 + b), 'gold1', 2)
        for t in range(3):
            a.line((sg * 15 - 3 + t * 3, 40 + b), (sg * 15 - 3 + t * 3, 36 + b), 'gold2', 1)
    hx, hy = 1, 57 + b
    a.e(hx, hy, 13, 11.6, 'skin')
    a.e(hx - 4, hy + 6, 7, 4, 'skin', out=False)
    a.band([(hx - 12, hy - 3), (hx + 12, hy - 3), (hx + 10, hy - 11), (hx + 3, hy - 16), (hx - 3, hy - 16), (hx - 10, hy - 11)], 'beard')
    a.e(hx, hy - 9, 8, 5.4, 'beard', out=False)
    a.eye(hx - 3.4, hy + 2, 4.4, iris='iris', look=(.3, .1))
    a.eye(hx + 6.2, hy + 2, 4, iris='iris', look=(.9, .1))
    # tricorn captain's hat with a gold band and weed
    a.band([(hx - 20, hy + 7), (hx + 20, hy + 7), (hx + 14, hy + 13), (hx + 8, hy + 20), (hx - 8, hy + 20), (hx - 14, hy + 13)], 'hat')
    a.line((hx - 20, hy + 7), (hx + 20, hy + 7), 'gold1', 2)
    a.poly([(hx - 6, hy + 13), (hx + 5, hy + 13), (hx, hy + 18)], 'gold2', out=False)
    a.poly([(hx + 14, hy + 8), (hx + 20, hy + 2), (hx + 18, hy + 10)], 'weed1', out=False)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 5 + k * 4, 36), tip[1] - 3 + k * 4, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def ghostmaw(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('ghostmaw', clip, n, sy=1 - fall * .2)
    k = 1 - fall * .5
    ph = n * math.pi / 3 if clip == 'idle' else n * math.pi / 2
    amp = 3 if clip != 'idle' else 2
    base = [(-38, 12), (-28, 10), (-18, 11), (-8, 13), (2, 16), (10, 19)]
    radii = [2.2, 4, 6, 8.4, 10, 10.4]
    pts = []
    for i, (x, y) in enumerate(base):
        w = math.sin(i * 1.0 - ph) * amp
        pts.append((x, (y + w) * k + (bob * .6 if i > 2 else 0)))
    hx = lerp(lerp(18, 12, wind), 24, strike)
    hy = lerp(lerp(26, 30, wind), 22, strike)
    if clip == 'die':
        hx, hy = lerp(18, 26, fall), lerp(26, 12, fall)
    # ghost-fire trail behind the tail
    for t in range(4):
        a.e(-42 + t * 2 + math.sin(n + t) * 1.5, 14 + t * 5 + (n % 3), 2.8 - t * .4, 3.6 - t * .5, 'ghost', out=False)
    for i in range(len(pts) - 1):
        a.c(pts[i], pts[i + 1], radii[i], radii[i + 1], 'body')
    for i in range(1, 6):
        x, y = pts[i]
        a.e(x + 1, y - radii[i] * .55, radii[i] * .5, radii[i] * .4, 'belly', out=False)
        a.poly([(x - 3, y + radii[i] - 1), (x - 1, y + radii[i] + 7), (x + 3, y + radii[i] - 1)], 'fin1')
    a.c(pts[-1], (hx - 4, hy - 4), radii[-1], 9, 'body')
    # a huge gaping maw lined with teeth
    jaw = max(wind * .5, strike) * 8 + 5
    a.e(hx + 7, hy - 8 - jaw, 11, 4.4, 'belly')
    for t in range(4):
        a.poly([(hx + 1 + t * 4.4, hy - 7 - jaw), (hx + 2.8 + t * 4.4, hy - 2 - jaw), (hx + 4.4 + t * 4.4, hy - 7 - jaw)], 'tooth1', out=False)
    a.e(hx + 6, hy - 4 - jaw / 2, 10, jaw / 2 + 2, 'mouth')
    a.e(hx, hy, 14, 11.4, 'body')
    a.e(hx + 10, hy - 2.4, 9.6, 5.8, 'body')
    a.e(hx + 5, hy - 5, 10, 3.6, 'belly', out=False)
    for t in range(4):
        a.poly([(hx + 1 + t * 4.4, hy - 2.4), (hx + 2.8 + t * 4.4, hy - 7), (hx + 4.4 + t * 4.4, hy - 2.4)], 'tooth1', out=False)
    crystal(a, hx - 6, hy + 8, 3.2, 10, 'fin', tilt=-3)
    crystal(a, hx + 1, hy + 9, 2.8, 8, 'fin', tilt=-1)
    a.eye(hx + 2.4, hy + 2.4, 4.8, iris='iris')
    a.dot(hx - 6, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for t in range(4):
            star(a, min(hx + 22 + t * 3, 38), hy - 4 + (t % 2) * 6, 2.4, 'ghost1')
    return a.done()


DRAW = dict(draugr=draugr, angler=angler, moray=moray, siren=siren, shellback=shellback, kraken=kraken, hvitserk=hvitserk,
            ghostmaw=ghostmaw)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/deep-cel-preview')
    print('ok')
