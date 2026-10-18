"""Cel-shaded Wyrdwood enemies (zone 6) for make_wyrd_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes, chibi
proportions. 96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/wyrd_cel_redraw.py [kind...]` writes contact sheets to test-results/wyrd-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, crystal, diamond, preview, star, timing
from make_crag_sprites import ellipsoid

KINDS = ('boar', 'crow', 'troll', 'weaver', 'ram', 'oakhorn', 'hrungnir')

PALETTES = {
    'boar': mk(hide=('#3a261a', '#6a4630', '#a2704a', '#d8a470'), mane=('#24160e', '#46301e', '#7a5636'),
               rot=('#a8300e', '#ff7a1e', '#ffd04a'), tusk=('#c8c0a8', '#fffbe6'), iris='#ff8a1e', blush='#ff8a98',
               mouth=('#5a1c34', '#ff6f8c'), snout=('#a8707a', '#e0a0a8', '#ffc8c8')),
    'crow': mk(plume=('#14101e', '#2c2444', '#4a3c78', '#7a68b8'), beak=('#8a6414', '#e0a428', '#ffe07a'),
               bone=('#b8b29a', '#fffbea'), iris='#ffc23a', thread=('#8a5a3a', '#c89868'), claw=('#4a3c5a', '#8a7aa0'),
               blush='#ff8a98', glint='#c8b8f8'),
    'troll': mk(skin=('#2a4a2a', '#4a7a42', '#7eb25e', '#c2e68c'), moss=('#1a3a1a', '#3a7a2e', '#78b844', '#c4ee78'),
                club=('#4a3220', '#7a5634', '#b08454'), tusk=('#c8c0a8', '#fffbe6'), cloth=('#4a3222', '#7a5a3a', '#a88458'),
                iris='#ffd23a', cap=('#a83a3a', '#e8604e'), spot='#fff0d4', mouth=('#4a1830', '#c8486e'),
                blush='#ff9a8a'),
    'weaver': mk(robe=('#22103e', '#44247a', '#7248b8', '#b08cf0'), gold=('#7a4f12', '#c98f28', '#f6d467', '#fff0a0'),
                 void=('#08060f', '#1c1230'), iris='#ffd23a', thread=('#c8962a', '#ffe27a'),
                 spool=('#8a5a2a', '#d8a050'), bone=('#c8b8d8', '#f0e8fa')),
    'ram': mk(wool=('#5a6a8e', '#9aaccc', '#d8e4f8', '#fcfeff'), horn=('#6a5030', '#b08a52', '#e8c888', '#fff0c8'),
              face=('#3a3a52', '#6a6a88', '#a4a4c0'), bolt=('#ffd23a', '#fffbc8'), iris='#38b8ff',
              blush='#ff9ab8', hoof=('#2a2438', '#4a4062')),
    'oakhorn': mk(hide=('#4a2a14', '#8a5230', '#c4854c', '#f0b878'), moss=('#1a3a1a', '#3a7a2e', '#78b844', '#c4ee78'),
                  wood=('#3a2410', '#6a4624', '#9a6c3a'), leaf=('#a83a14', '#e8761e', '#ffb43a', '#ffe27a'),
                  belly=('#c8a078', '#f0d4a8', '#fff2d8'), iris='#2a6a2a', blush='#ff8a98', hoof=('#2a1c14', '#4a3424')),
    'hrungnir': mk(stone=('#2a3a54', '#4e6a92', '#86a4cc', '#c4dcf6'), ice=('#1e5a96', '#3aa4e8', '#9ae0ff', '#f0fcff'),
                   skin=('#6a8aa8', '#a4c4dc', '#d8ecf8'), beard=('#9ab4cc', '#dceaf6', '#f8fcff'),
                   iron=('#2c3444', '#5a6a82', '#9aaac4'), rune=('#58d8ff', '#d8fbff'), iris='#38b8ff',
                   wood=('#4a3220', '#7a5634', '#b08454'), cloth=('#2a2a4a', '#4a4a80', '#7878b8')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def boar(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('boar', clip, n, sy=1 - fall * .45)
    b = bob * .5 - fall * 4
    by = 22 + b
    lean = strike * 5 - wind * 4
    a.c((-26, by + 4), (-31, by + 8 + math.sin(n * 1.3) * 2), 2.4, 1.2, 'hide')
    for lx, ph in ((-14, 1.6), (12, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx + 3, by - 4), (lx + 4 + up * .3, up + 3), 4.8, 3.6, 'hide')
        a.e(lx + 6 + up * .3, up + 3, 5, 2.4, 'mane')
    # bristly mane with glowing rot patches
    for k in range(7):
        a.poly([(-22 + k * 5, by + 11 - abs(k - 3) * .7), (-19.5 + k * 5, by + 19 + (k % 2) * 3), (-17 + k * 5, by + 11 - abs(k - 3) * .7)], 'mane1')
    a.e(-6, by, 22, 13.4, 'hide')
    a.e(-3, by - 7, 15, 5, 'hide', out=False)
    for (rx, ry, r) in ((-14, 6, 3.4), (-4, 9, 2.8), (-18, -1, 2.2)):
        a.e(rx, by + ry, r, r * .8, 'rot')
    a.e(12, by + 3, 12, 11.4, 'hide')
    for lx, ph in ((-12, 0), (11, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx, by - 4), (lx + 2 + up * .3, up + 3), 5.2, 4, 'hide')
        a.e(lx + 4 + up * .3, up + 3, 5.4, 2.6, 'mane')
    hx, hy = 21 + lean, by + 4
    if clip == 'die':
        hx, hy = lerp(21, 25, fall), lerp(by + 4, 10, fall)
    jaw = max(wind * .5, strike) * 4
    a.e(hx + 7, hy - 6 - jaw, 6.6, 3, 'snout')
    if jaw > 1.5:
        a.e(hx + 8, hy - 4 - jaw / 2, 5.4, jaw / 2 + 1, 'mouth')
    a.e(hx, hy, 12.6, 10.8, 'hide')
    a.e(hx + 9, hy - 3, 8.2, 6, 'snout')
    a.dot(hx + 14, hy - 2, 'ink', 2)
    a.poly([(hx + 5, hy - 5), (hx + 14, hy + 3), (hx + 12, hy - 4)], 'tusk0', out=True)
    a.poly([(hx + 6, hy - 4.6), (hx + 13, hy + 1.6), (hx + 11.4, hy - 3.6)], 'tusk1', out=False)
    a.poly([(hx - 8, hy + 7), (hx - 4, hy + 16), (hx + 1, hy + 8)], 'hide1')
    a.eye(hx + 1.6, hy + 2.4, 4.6, iris='iris')
    a.eye(hx + 9, hy + 1.6, 3.2, iris='iris')
    a.dot(hx - 4, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(hx + 18 + k * 4, 38), hy - 5 + (k % 2) * 5, 2.4, 'rot2')
    return a.done()


# ------------------------------------------------------------------------------------------------
def crow(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('crow', clip, n, sy=1 - fall * .3)
    if clip == 'idle':
        fl = math.sin(n * math.pi / 3) * .4
    elif clip == 'walk':
        fl = math.sin(n * math.pi / 2) * .7
    elif clip == 'attack':
        fl = lerp(lerp(.2, 1., wind), -.8, strike)
    elif clip == 'hurt':
        fl = (1., .6, .3, 0.)[n]
    else:
        fl = .3
    by = 36 + bob * .8 - fall * 14 - strike * 4
    hx, hy = 12 + strike * 5, by + 9 - strike * 5
    for k in range(4):                                      # tail feather fan
        a.c((-9, by - 3), (-28 + k * 2 - fall * 4, by - 14 + k * 5 + fl * 3), 3.4, 1.8, 'plume')

    def wing(base_ang, length, grp):
        sh = (-2, by + 5)
        ang0 = base_ang + fl * 30 * (1 - fall)
        pts = [sh]
        for k in range(5):
            th = math.radians(ang0 + (k - 2) * 15)
            ln = length - abs(k - 2) * 3.4
            nth = math.radians(ang0 + (k - 2) * 15 - 7.5)
            pts.append((sh[0] + math.cos(nth) * length * .56, sh[1] + math.sin(nth) * length * .56))
            pts.append((sh[0] + math.cos(th) * ln, sh[1] + math.sin(th) * ln))
        nth = math.radians(ang0 + 2 * 15 + 7.5)
        pts.append((sh[0] + math.cos(nth) * length * .56, sh[1] + math.sin(nth) * length * .56))
        a.band(pts, grp)
    wing(132 + fall * 30, 27, 'plume')
    a.e(0, by, 15, 12, 'plume')
    a.e(-3, by - 6, 11, 4.4, 'plume', out=False)
    wing(118 + fall * 50 - fl * 6, 32, 'plume')
    # dangling bone charm on a thread
    a.line((2, by - 8), (4, by - 17), 'thread1', 1)
    a.e(4, by - 20, 2.6, 2.6, 'bone')
    a.dot(3, by - 19, 'ink', 1)
    for sg, off in ((-1, 0), (1, 3)):
        a.c((2 + off, by - 9), (3 + off + strike * 10, by - 20 + strike * 3), 1.8, 1.4, 'claw')
        for t in range(3):
            a.line((3 + off + strike * 10, by - 20 + strike * 3), (5 + off + strike * 10 - t * 2, by - 24 + strike * 3), 'claw1', 1)
    gap = max(wind * .4, strike) * 4
    a.poly([(hx + 5, hy - 3 - gap), (hx + 17, hy - 5 - gap), (hx + 7, hy - 9 - gap)], 'beak0')
    a.e(hx, hy, 11, 10, 'plume')
    a.poly([(hx + 7, hy + 1), (hx + 20, hy - 3), (hx + 16, hy - 7), (hx + 8, hy - 5)], 'beak1')
    a.poly([(hx + 16, hy - 3), (hx + 21, hy - 8), (hx + 15, hy - 6)], 'beak2', out=False)
    for k, (dx, h) in enumerate(((-7, 7), (-2, 10), (3, 7))):
        a.poly([(hx + dx - 2.4, hy + 8), (hx + dx, hy + 8 + h), (hx + dx + 3, hy + 8)], 'plume2')
    a.eye(hx + 2, hy + 1.8, 4.7, iris='iris')
    a.dot(hx - 5, hy - 3, 'blush', 3)
    return a.done()


# ------------------------------------------------------------------------------------------------
def troll(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('troll', clip, n, sy=1 - fall * .5)
    b = bob * .8
    for sg in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if sg < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.c((sg * 10, 20), (sg * 10 + fall * sg * 4, 6 + up), 7.4 * (1 - fall * .5), 7 * (1 - fall * .5), 'skin')
        a.e(sg * 10 + fall * sg * 5, 4 + up, 9.6, 4.4, 'skin')
    a.band([(-14, 24), (14, 24), (16, 14), (-16, 14)], 'cloth')
    a.c((-18, 40 + b), (-28 - fall * 3, 26 - fall * 14), 6.4, 6, 'skin')
    a.e(-29 - fall * 3, 22 - fall * 12, 8.2, 7.6, 'skin')
    a.e(0, 35 + b - fall * 8, 21, 18, 'skin')
    a.e(-7, 42 + b - fall * 8, 10, 6, 'skin', out=False)
    a.band([(-18, 40 + b), (18, 40 + b), (14, 32 + b), (8, 36 + b), (0, 31 + b), (-8, 36 + b), (-14, 32 + b)], 'moss', out=False)
    for sg in (-1, 1):
        a.e(sg * 16, 47 + b - fall * 9, 8, 6.8, 'skin')
        a.e(sg * 16, 51 + b - fall * 9, 7, 3.4, 'moss')
    hx = lerp(0, -9, fall)
    hy = lerp(55 + b, 14, fall)
    # clover sprout and a red mushroom on the head
    a.line((hx - 2, hy + 11), (hx - 3, hy + 17), 'ink', 4)
    a.line((hx - 2, hy + 11), (hx - 3, hy + 17), 'moss1', 2)
    for (dx, dy) in ((-7, 20), (-3, 23), (1, 20)):
        a.e(hx + dx, hy + dy, 3.2, 3.2, 'moss')
    a.e(hx + 7, hy + 12, 4.2, 3, 'cap')
    a.dot(hx + 6, hy + 13, 'spot', 2)
    a.e(hx, hy, 13.6, 12, 'skin')
    a.e(hx - 4, hy + 6, 7, 4, 'skin', out=False)
    a.e(hx + 1, hy + 9, 12, 4, 'moss', out=False)
    state = T['state']
    a.eye(hx - 3.6, hy + 1, 4.3, iris='iris', look=(.4, .1))
    a.eye(hx + 6.2, hy + 1, 4, iris='iris', look=(.9, .1))
    a.dot(hx - 8, hy - 3, 'blush', 3)
    mouth = max(wind * .6, strike) * 3
    a.e(hx + 1, hy - 6 - mouth * .5, 4.2, 2 + mouth, 'mouth')
    for sg in (-1, 1):
        a.poly([(hx + 1 + sg * 3.8 - 1.4, hy - 5), (hx + 1 + sg * 3.8, hy - 11 - mouth), (hx + 1 + sg * 3.8 + 1.4, hy - 5)], 'tusk1')
    # a big knotted club
    hand = (lerp(lerp(21, 17, wind), 25, strike), lerp(lerp(30, 38, wind), 28, strike))
    ang = lerp(lerp(1.5, 2.0, wind), .25, strike)
    if clip == 'die':
        hand = (lerp(21, 26, fall), lerp(30, 8, fall))
        ang = lerp(1.5, 2.9, fall)
    dx_, dy_ = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx_ * 8, hand[1] - dy_ * 8)
    top = (min(hand[0] + dx_ * 24, 26), min(hand[1] + dy_ * 24, 66))
    a.line(base, top, 'ink', 8)
    a.line(base, top, 'club1', 6)
    a.e(top[0], top[1], 7.4, 8.4, 'club')
    a.dot(top[0] - 2, top[1] + 2, 'club2', 2)
    a.c((16, 42 + b - fall * 8), hand, 6.6, 5.6, 'skin')
    a.e(hand[0], hand[1], 5.6, 5.2, 'skin')
    if clip == 'attack' and n in (4, 5):
        for k in range(5):
            a.e(min(31 + k * 1.8, 36), 4 + (k * 7) % 9 + (n - 4) * 3, 2.2, 2.2, 'moss')
    return a.done()


# ------------------------------------------------------------------------------------------------
def weaver(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('weaver', clip, n, sy=1 - fall * .55)
    a.lift = 5 + bob * 1.2 - fall * 5
    sway = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else sw * 2
    rag = [-1, 1, 0, -1, 1][n % 5]
    hem = [(-19, 2), (-14, 9 + rag), (-9, 1), (-4, 10), (1, 2), (6, 10 - rag), (11, 1), (16, 9), (20, 2)]
    robe = [(-9, 48), (9, 48), (14, 32), (19 + sway, 11), (21 + sway * .5, 3), (-21 + sway * .5, 3), (-19, 11), (-14, 32)]
    a.band(robe, 'robe')
    a.band([(-19 + sway * .3, 4), (-14, 10 + rag), (-9, 3), (-4, 11), (1, 3), (6, 10 - rag), (11, 3), (16, 9), (20, 4)], 'robe', out=False)
    # woven gold bands: crossing threads on the robe
    for k in range(3):
        a.line((-12 + k * 3, 24 - k * 2), (12 - k * 3, 36 + k * 2), 'thread1', 1)
        a.line((12 - k * 3, 24 - k * 2), (-12 + k * 3, 36 + k * 2), 'thread0', 1)
    a.line((-13, 40), (13, 40), 'gold1', 2)
    # a glowing spool of thread floats beside her, threads link it to her hands
    sp = (lerp(lerp(24, 20, wind), 31, strike), lerp(lerp(36, 52, wind), 36, strike) + math.sin(n * 1.1) * 1.5)
    hand = (lerp(lerp(14, 12, wind), 20, strike), lerp(lerp(38, 46, wind), 38, strike))
    far = (-17, 35)
    if clip == 'die':
        sp = (lerp(24, 12, fall), lerp(36, 6, fall))
        hand = (lerp(14, 8, fall), lerp(38, 8, fall))
    a.c((9, 44), hand, 3.6, 3.2, 'robe')
    a.e(hand[0], hand[1], 3, 3, 'bone')
    a.c((-9, 44), far, 3.6, 3.2, 'robe')
    a.e(far[0], far[1], 3, 3, 'bone')
    a.line(far, (hand[0], hand[1]), 'thread1', 1)
    a.line(hand, sp, 'thread1', 1)
    a.e(sp[0], sp[1], 5.8, 5.8, 'spool')
    a.line((sp[0] - 5, sp[1] + 2), (sp[0] + 5, sp[1] + 2), 'thread1', 2)
    a.line((sp[0] - 5, sp[1] - 2), (sp[0] + 5, sp[1] - 2), 'thread0', 2)
    # hood with a veil and big golden owl eyes
    hx, hy = 1 + sway * .3, 53
    a.poly([(hx - 11, hy + 3), (hx - 3, hy + 20), (hx + 7, hy + 3)], 'robe1')
    a.e(hx, hy, 14, 13, 'robe')
    a.e(hx - 4, hy + 6, 8, 4.4, 'robe', out=False)
    a.f.flat(ellipsoid(*a.g(hx + 3, hy - 1.5), 10, 9.2 * a.sy)[0], 'void0')
    a.eye(hx - .4, hy - .6, 4.4, iris='iris', look=(.4, .1))
    a.eye(hx + 8.4, hy - .6, 3.8, iris='iris', look=(.9, .1))
    a.line((hx - 12, hy + 3), (hx + 13, hy + 3), 'gold1', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            x = min(sp[0] + 4 + k * 4, 38)
            a.line((x, sp[1] + 3 - k * 2), (x + 4, sp[1] + 5 - k * 2), 'thread1', 2)
    return a.done()


# ------------------------------------------------------------------------------------------------
def ram(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('ram', clip, n, sy=1 - fall * .4)
    b = bob * .5 - fall * 4
    by = 23 + b
    lean = strike * 6 - wind * 4
    for lx, ph in ((-14, 1.6), (12, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx + 3, by - 4), (lx + 4 + up * .3, up + 3), 3.6, 2.8, 'face')
        a.e(lx + 6 + up * .3, up + 2.4, 4.2, 2.2, 'hoof')
    # cloud-wool body with a couple of lightning marks
    a.e(-6, by, 23, 15, 'wool')
    for k in range(6):
        a.e(-24 + k * 8, by + 11 + (k % 2) * 1.5, 5, 4.6, 'wool')
    a.e(-8, by - 8, 15, 5, 'wool', out=False)
    for (x, y) in ((-14, 6), (-2, 10)):
        a.poly([(x, by + y), (x + 3, by + y - 4), (x + 1, by + y - 4.5), (x + 4, by + y - 9), (x - 3, by + y - 3.5), (x - 1, by + y - 3)], 'bolt0')
    for lx, ph in ((-10, 0), (12, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx, by - 4), (lx + 2 + up * .3, up + 3), 4, 3, 'face')
        a.e(lx + 4 + up * .3, up + 2.4, 4.6, 2.4, 'hoof')
    hx, hy = 20 + lean, by + 3
    if clip == 'die':
        hx, hy = lerp(20, 25, fall), lerp(by + 3, 10, fall)
    # big spiral horns
    for sg, dx in ((1, 0), (-1, -8)):
        a.c((hx + dx - 2, hy + 6), (hx + dx - 9, hy + 12), 5, 4, 'horn')
        a.c((hx + dx - 9, hy + 12), (hx + dx - 11, hy + 3), 4, 3, 'horn')
        a.c((hx + dx - 11, hy + 3), (hx + dx - 5, hy - 2), 3, 2, 'horn')
    a.e(hx, hy, 12, 10.8, 'wool')
    a.e(hx + 7, hy - 3, 9, 7.4, 'face')
    a.e(hx + 11, hy - 6, 4, 2, 'face', out=False)
    a.dot(hx + 14, hy - 3, 'ink', 2)
    a.poly([(hx - 3, hy + 9), (hx + 4, hy + 8), (hx + 1, hy + 15)], 'wool1')
    a.eye(hx + 3, hy + 1.6, 4.4, iris='iris')
    a.eye(hx + 11, hy + 1, 3, iris='iris')
    a.dot(hx - 2, hy - 4, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            a.poly([(min(hx + 14 + k * 4, 36), hy + 4 - k), (min(hx + 17 + k * 4, 38), hy), (min(hx + 15 + k * 4, 37), hy - .6),
                    (min(hx + 18 + k * 4, 39), hy - 5)], 'bolt1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def oakhorn(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('oakhorn', clip, n, sy=1 - fall * .4)
    b = bob * .5 - fall * 4
    by = 28 + b
    lean = strike * 5 - wind * 4
    a.e(-27, by + 4, 3.4, 4.6, 'belly')
    for lx, ph in ((-17, 1.6), (11, 0)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx + 3, by - 6), (lx + 4 + up * .3, up + 3), 3.8, 2.8, 'hide')
        a.e(lx + 6 + up * .3, up + 2.4, 4, 2, 'hoof')
    a.e(-6, by, 22, 12.6, 'hide')
    a.e(-4, by - 7, 15, 4.4, 'belly', out=False)
    a.band([(-18, by + 9), (6, by + 9), (4, by + 4), (-2, by + 7), (-8, by + 3), (-14, by + 6)], 'moss', out=False)
    for k in range(3):
        a.e(-15 + k * 7, by + 12 + (k % 2), 2.6, 3, 'cap') if False else None
    a.e(14, by + 5, 9, 12, 'hide')
    for lx, ph in ((-12, 0), (12, 1.6)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx, by - 6), (lx + 2 + up * .3, up + 3), 4.4, 3.2, 'hide')
        a.e(lx + 4 + up * .3, up + 2.4, 4.4, 2.2, 'hoof')
    hx, hy = 21 + lean, by + 13
    if clip == 'die':
        hx, hy = lerp(21, 26, fall), lerp(by + 13, 12, fall)
    # oak-branch antlers with orange leaves
    for sg, dx in ((1, 3), (-1, -4)):
        base = (hx + dx, hy + 8)
        mid = (hx + dx - 2 + sg * 3, hy + 17)
        tip = (hx + dx - 5 + sg * 7, hy + 25)
        a.line(base, mid, 'ink', 5)
        a.line(base, mid, 'wood1', 3)
        a.line(mid, tip, 'ink', 4)
        a.line(mid, tip, 'wood1', 2)
        a.line(mid, (mid[0] + 7, mid[1] + 2), 'ink', 4)
        a.line(mid, (mid[0] + 7, mid[1] + 2), 'wood1', 2)
        for (lx, ly) in (tip, (mid[0] + 7, mid[1] + 2), (mid[0] - 2, mid[1] + 6)):
            a.e(lx, ly, 3.6, 3.2, 'leaf')
    a.e(hx + 6, hy - 6 - max(wind * .3, strike) * 3, 7.6, 3, 'belly')
    a.e(hx, hy, 10.6, 9.4, 'hide')
    a.e(hx + 7, hy - 3, 8, 5.4, 'belly')
    a.dot(hx + 13, hy - 2.4, 'ink', 2)
    a.poly([(hx - 8, hy + 6), (hx - 13, hy + 12), (hx - 4, hy + 8)], 'hide1')
    a.eye(hx + 2, hy + 2, 4.4, iris='iris')
    a.dot(hx - 3, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hx + 15 + k * 4, 38), hy + 8 + (k % 2) * 6, 2.4, 3, 'leaf2' if k % 2 else 'leaf1')
    if clip == 'die':
        for k in range(5):
            diamond(a, -24 + k * 11, max(4, 40 - fall * 34 + (k % 3) * 6), 2.2, 3.2, 'leaf2' if k % 2 else 'leaf1')
    return a.done()


# ------------------------------------------------------------------------------------------------
def hrungnir(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('hrungnir', clip, n, sy=1 - fall * .5)
    b = bob * .6
    for sg in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if sg < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.c((sg * 10, 22), (sg * 10 + fall * sg * 4, 7 + up), 7.8 * (1 - fall * .5), 7.2 * (1 - fall * .5), 'stone')
        a.e(sg * 10.6 + fall * sg * 5, 4 + up, 10, 4.6, 'iron')
    # round rune shield on the far arm
    sx, sy_ = -26 + wind * -2, 36 + b
    a.e(sx, sy_, 12.8, 13.6, 'iron')
    a.e(sx, sy_, 9.4, 10.2, 'ice', out=False)
    a.poly([(sx, sy_ + 6), (sx + 3, sy_), (sx, sy_ - 6), (sx - 3, sy_)], 'rune1')
    a.c((-14, 42 + b), (sx + 6, sy_ + 2), 4.8, 4.2, 'stone')
    a.band([(-14, 25), (14, 25), (16, 15), (-16, 15)], 'cloth')
    a.e(0, 36 + b, 17, 13.8, 'stone')
    a.e(-6, 42 + b, 9, 5, 'stone', out=False)
    a.poly([(0, 44 + b), (5, 37 + b), (0, 30 + b), (-5, 37 + b)], 'ice1', edge='iron0')
    a.line((-16, 28 + b), (16, 28 + b), 'iron1', 2)
    # greatsword
    hand = (lerp(lerp(21, 17, wind), 27, strike), lerp(lerp(34, 42, wind), 34, strike))
    ang = lerp(lerp(1.5, 2.0, wind), .2, strike)
    if clip == 'die':
        hand = (lerp(21, 26, fall), lerp(34, 8, fall))
        ang = lerp(1.5, 2.9, fall)
    dx, dy = math.cos(ang), math.sin(ang)
    base = (hand[0] - dx * 6, hand[1] - dy * 6)
    tip = (min(hand[0] + dx * 30, 28), min(hand[1] + dy * 30, 70))
    a.line(base, tip, 'ink', 8)
    a.line(base, tip, 'ice1', 6)
    a.line(base, tip, 'ice3', 1)
    a.line((hand[0] - dy * 8, hand[1] + dx * 8), (hand[0] + dy * 8, hand[1] - dx * 8), 'iron1', 3)
    a.c((12, 43 + b), hand, 5, 4.4, 'stone')
    a.e(hand[0], hand[1], 4.6, 4.4, 'skin')
    for sg in (-1, 1):
        a.e(sg * 18, 46 + b, 8.6, 7.4, 'stone')
        crystal(a, sg * 18, 50 + b, 3, 9, 'ice', tilt=sg * 2)
    # big bearded head under a horned iron helm with an ice crystal
    hx, hy = 1, 57 + b
    a.e(hx, hy - 7, 10, 9, 'beard')
    a.e(hx, hy, 13.4, 11.8, 'skin')
    a.e(hx - 4, hy + 6, 7, 4, 'skin', out=False)
    a.e(hx + 1, hy - 8, 9, 7.6, 'beard')
    a.e(hx, hy + 8, 13.8, 7, 'iron')
    for sg in (-1, 1):
        a.poly([(hx + sg * 11, hy + 7), (hx + sg * 20, hy + 14), (hx + sg * 15, hy + 20), (hx + sg * 8, hy + 10)], 'beard1')
    crystal(a, hx, hy + 13, 3.6, 12, 'ice', tilt=0)
    a.eye(hx - 3.4, hy + 1.4, 4.2, iris='iris', look=(.4, .1))
    a.eye(hx + 6.2, hy + 1.4, 3.8, iris='iris', look=(.9, .1))
    a.line((hx - 9, hy + 5), (hx - 1, hy + 3), 'ink', 2)
    a.line((hx + 2, hy + 3), (hx + 10, hy + 5), 'ink', 2)
    a.line((hx - 13, hy + 7), (hx + 13, hy + 7), 'iron0', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, min(tip[0] + 6 + k * 4, 36), tip[1] - 4 + k * 4, 2.6, 'rune1')
    return a.done()


DRAW = dict(boar=boar, crow=crow, troll=troll, weaver=weaver, ram=ram, oakhorn=oakhorn, hrungnir=hrungnir)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def drawer(kind):
    return lambda clip, n: draw(kind, clip, n)


DRAWERS = {k: (drawer(k), PALETTES[k]) for k in KINDS}

if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/wyrd-cel-preview')
    print('ok')
