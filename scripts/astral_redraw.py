"""Cel-shaded Astralhollow enemies (zone 13) for make_astral_sprites.py.

Same recipe as cathedral_reliquary_redraw.py: hard colour bands, one dark outline per part, big glossy eyes,
chibi proportions. 96x96 frame, foot anchor (48,90), five clips (idle 6, walk 8, attack 8, hurt 4, die 8).
`python3 scripts/astral_redraw.py [kind...]` writes contact sheets to test-results/astral-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cathedral_reliquary_redraw import Art, lerp, mk
from cel_zone_common import ROOT, timing, crystal, diamond, circle_ring, preview, star
from make_crag_sprites import ellipsoid

KINDS = ('voidmoth', 'crystalwyrm', 'orbitbeetle', 'eclipsedryad', 'meteorgolem')

PALETTES = {
    'voidmoth': mk(wing=('#271757', '#523aa8', '#8f6fe6', '#d8c8ff'), fur=('#7a68b8', '#c1b0f4', '#f4ecff'),
                   body=('#2c1c5a', '#4d3590', '#7b5cc8'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                   glow=('#fff3b8', '#ffd36a'), iris='#7a3fe0', blush='#ff8fc0', dust='#efe4ff'),
    'crystalwyrm': mk(scale=('#0f3a66', '#1f7fb8', '#5cc8e6', '#c4f6ff'), belly=('#78b6d6', '#c9ecf5', '#f4fdff'),
                      crystal=('#3f2a8a', '#7a5be0', '#b69cff', '#efe6ff'), glow=('#fff7c2', '#ffe58a'),
                      iris='#e0407e', blush='#ff9fc8', mouth=('#5a1c3c', '#ff6f98')),
    'orbitbeetle': mk(shell=('#6e2f1f', '#b8582c', '#ee8a3e', '#ffc46a'), dark=('#2b1a1c', '#4f2f28', '#80503a'),
                      wingu=('#4b2d88', '#8a62d8', '#c8a8ff'), glow=('#fff3b0', '#ffd96a'),
                      moon=('#a8741a', '#f2c13e', '#fff1a0'), iris='#2f4fc0', horn=('#b88a2c', '#f0cc66', '#fff2b0'),
                      blush='#ff8a70'),
    'eclipsedryad': mk(leaf=('#1f4a30', '#3c8a4a', '#79c957', '#d2f08a'), bark=('#4a2c20', '#7a4a30', '#b07a4c'),
                       skin=('#7fa883', '#bfe2b5', '#effbe0'), shade=('#14102a', '#3a2a6a'),
                       corona=('#d97a1c', '#ffb347', '#ffe58a', '#fff7d0'), bloom=('#d8588a', '#ff9fc0'),
                       iris='#e8a92a', blush='#ff9f9a'),
    'meteorgolem': mk(rock=('#2a2540', '#4f4673', '#8277b0', '#c0b4e8'), crack=('#d9501e', '#ff8a2e', '#ffd36a'),
                      amethyst=('#4a1a7a', '#a24ee0', '#e2b0ff', '#f8e6ff'), ember=('#ff6a28', '#ffd04a'),
                      chip=('#3a3158', '#6a5f94'), dust='#d8d0ee'),
}
R.PALETTES.update(PALETTES)   # Art looks its palette up by kind


def branch(a, p0, p1, group='bark', w=2):
    a.line(p0, p1, 'ink', w + 2)
    a.line(p0, p1, group + '1', w)


# ------------------------------------------------------------------------------------------------
def voidmoth(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob = T['fall'], T['wind'], T['strike'], T['bob']
    a = Art('voidmoth', clip, n, sy=1 - fall * .3)
    if clip == 'idle':
        fl = math.sin(n * math.pi / 3)
    elif clip == 'walk':
        fl = math.sin(n * math.pi / 2)
    elif clip == 'attack':
        fl = lerp(lerp(.1, 1., wind), -1., strike)
    elif clip == 'hurt':
        fl = (1., .6, .3, 0.)[n]
    else:
        fl = lerp(.4, -1.4, min(1, fall * 1.6))
    by = 46 + bob * 1.4 - fall * 22
    spread = 36 - abs(fl) * 3 - fall * 15

    def fan(s, root, a0, a1, rx, ry, k, sc=.07):
        """A rounded, scalloped wing: a fan of radius rx/ry around `root`, flapped by `fl`."""
        pts = [root]
        for i in range(15):
            t = i / 14
            ang = math.radians(lerp(a0, a1, t) + fl * 20 - fall * 25)
            r = (.72 + .28 * math.sin(math.pi * t) ** .6) * (1 - sc * (i % 2))
            pts.append((root[0] + s * math.cos(ang) * rx * r, max(3, root[1] + math.sin(ang) * ry * r)))
        return pts

    def at(s, root, a0, a1, rx, ry, t, r):
        ang = math.radians(lerp(a0, a1, t) + fl * 20 - fall * 25)
        return (root[0] + s * math.cos(ang) * rx * r, max(3, root[1] + math.sin(ang) * ry * r))

    for s in (-1, 1):                   # hind wings first, then the big forewings over them
        root = (s * 4, by + 1)
        a.band(fan(s, root, 8, -70, spread - 2, 25, 0), 'wing')
        ox, oy = at(s, root, 8, -70, spread - 2, 25, .45, .62)
        a.e(ox, oy, 3.8, 3.8, 'gold')
        a.dot(ox - 1.2, oy + 1.2, 'shine')
    for s in (-1, 1):
        root = (s * 3, by + 6)
        a.band(fan(s, root, 118, 4, spread, 32, 0), 'wing')
        a.line((s * 7, by + 7), at(s, root, 118, 4, spread, 32, .5, .75), 'wing0', 1)
        a.line((s * 7, by + 4), at(s, root, 118, 4, spread, 32, .75, .7), 'wing0', 1)
        ox, oy = at(s, root, 118, 4, spread, 32, .55, .63)
        a.e(ox, oy, 6, 6.4, 'gold')
        a.e(ox, oy, 3.6, 3.9, 'glow', out=False)
        a.f.flat(ellipsoid(*a.g(ox + .4, oy - .4), 1.8, 2.1)[0], 'ink')
        a.dot(ox - 1.6, oy + 2, 'shine')
        for k in range(3):
            px, py = at(s, root, 118, 4, spread, 32, .3 + k * .22, .86)
            a.dot(px, py - 2, 'dust')
    # fuzzy body: abdomen, chest ruff, big chibi head
    a.e(0, by - 11, 6.4, 10, 'body')
    for k in range(3):
        a.line((-5, by - 6 - k * 5), (5, by - 6 - k * 5), 'wing0', 1)
    a.e(0, by + 3, 9.5, 10, 'fur')
    a.e(0, by + 17, 11.5, 10, 'fur')
    for s in (-1, 1):
        a.e(s * 5.6, by + 17, 0, 0, 'fur', out=False) if False else None
    sway = math.sin(n * math.pi / 3) * 1.2 if clip == 'idle' else T['sw'] * 1.5
    for s in (-1, 1):
        a.line((s * 4, by + 24), (s * (9 + sway), by + 33), 'ink', 4)
        a.line((s * 4, by + 24), (s * (9 + sway), by + 33), 'gold1', 2)
        star(a, s * (9 + sway), by + 35, 3.4, 'glow0')
    a.eye(-4.2, by + 18, 4.3, iris='iris', look=(0, .1))
    a.eye(5.2, by + 18, 4.3, iris='iris', look=(.4, .1))
    a.dot(-8.5, by + 13, 'blush', 2)
    a.dot(9, by + 13, 'blush', 2)
    a.dot(0, by + 13, 'ink', 1)
    if clip == 'idle':
        for k in range(3):
            a.dot(-22 + k * 22 + (n % 2) * 2, by - 14 - ((n * 3 + k * 5) % 12), 'dust', 1)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(3):
            star(a, 15 + (n - 3) * 6 + k * 6, by + 14 - k * 6, 3.6, 'glow0' if k % 2 else 'dust')
    return a.done()


# ------------------------------------------------------------------------------------------------
def crystalwyrm(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob = T['fall'], T['wind'], T['strike'], T['bob']
    a = Art('crystalwyrm', clip, n, sy=1 - fall * .15)
    keep = 1 - .6 * fall
    wave = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else T['sw'] * 2.4
    base = [(-40, 11), (-32, 5), (-22, 8), (-12, 13), (-2, 16), (7, 21), (11, 29)]
    radii = [2.4, 4, 6, 8, 9.4, 9, 8]
    pts = []
    for i, (x, y) in enumerate(base):
        w = math.sin(i * 1.1 - (n * math.pi / 2 if clip == 'walk' else n * math.pi / 3)) * (2.2 if clip == 'walk' else 1.2)
        pts.append((x, y * keep + w * keep + (bob * .5 if i > 3 else 0)))
    hx = lerp(lerp(15, 9, wind), 24, strike)
    hy = lerp(lerp(37 + bob, 41, wind), 33, strike)
    if clip == 'die':
        hx, hy = lerp(15, 25, fall), lerp(37, 12, fall)
        pts[-1] = (lerp(11, 17, fall), lerp(29, 11, fall))
    # back crystals, behind the body
    for i in range(1, 7):
        x, y = pts[i]
        h = (6 + (i % 3) * 2.6) * (1 - fall * .6)
        crystal(a, x - 1, y + radii[i] - 2, 3.2, h, 'crystal', tilt=-1.5)
    # far legs and near legs
    for lx, ph in ((-11, 0), (5, 2)):
        up = max(0, math.sin(n * math.pi / 2 + ph)) * 5 if clip == 'walk' else 0
        a.c((lx, 14 * keep), (lx + 2, up), 3.6, 2.8, 'scale')
        a.e(lx + 3, up + 1, 4.2, 2.2, 'scale')
    for i in range(len(pts) - 1):
        a.c(pts[i], pts[i + 1], radii[i], radii[i + 1], 'scale')
    a.c(pts[-2], (hx - 3, hy - 4), radii[-2], 7, 'scale')
    for i in range(1, 6):                                   # pale belly scutes along the underside
        x, y = pts[i]
        a.e(x + 1, y - radii[i] * .55, radii[i] * .5, radii[i] * .38, 'belly', out=False)
    # head: big chibi dome, snout, jaw, crystal horns
    jaw = max(wind * .6, strike) * 6 + (2 if clip == 'die' and fall < .5 else 0)
    a.e(hx + 7.5, hy - 5.5 - jaw, 8.2, 3.4, 'belly')                       # lower jaw
    if jaw > 1.5:
        a.e(hx + 8.5, hy - 3.6 - jaw / 2, 6.2, jaw / 2 + 1.2, 'mouth')
    a.e(hx, hy, 12.5, 10, 'scale')
    a.e(hx + 9.5, hy - 2.6, 8.2, 5.2, 'scale')
    a.e(hx + 5, hy - 5, 10, 3.6, 'belly', out=False)
    crystal(a, hx - 6, hy + 7, 3.3, 12, 'crystal', tilt=-4)
    crystal(a, hx + 1, hy + 8, 2.8, 9.5, 'crystal', tilt=-2)
    a.dot(hx + 15.5, hy - 1.8, 'ink', 2)
    a.eye(hx + 3.2, hy + 1.6, 4.5, iris='iris')
    a.dot(hx - 4, hy - 3, 'blush', 3)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            x = hx + 19 + k * 4 + (n - 3) * 2
            diamond(a, min(x, 38), hy - 4 - jaw / 2 + (k % 2) * 5 - 2, 2.6, 4, 'glow0' if k % 2 else 'belly1')
    if clip == 'idle' and n in (1, 4):
        diamond(a, hx + 17, hy + 6 + n, 1.5, 2.4, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def orbitbeetle(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('orbitbeetle', clip, n, sy=1 - fall * .2)
    by = 27 + bob - fall * 9
    flip = fall
    # moon orbiting overhead
    th = n * (math.pi / 3 if clip == 'idle' else math.pi / 4 if clip == 'walk' else math.pi / 4) + .8
    mx, my = math.cos(th) * 25, by + 33 + math.sin(th) * 4 - fall * 12
    back = math.sin(th) < 0
    if back and fall < .8:
        a.e(mx, my, 4.6, 4.6, 'moon')
    # legs: three a side, a little gait
    for i, (lx, dx, near) in enumerate(((-14, -9, 0), (-3, -3, 0), (9, 8, 0), (-9, -7, 1), (2, 1, 1), (13, 10, 1))):
        up = max(0, math.sin(n * math.pi / 2 + i * 1.6)) * 6 if clip == 'walk' else 0
        hip = (lx, by - 11)
        knee = (lx + dx * 1.3, by - 12 + flip * 14)
        foot = (lx + dx * 1.7, lerp(up, by + 24 + math.sin(n * 1.7 + i) * 3, flip))
        if near == 0:
            a.c(hip, knee, 2.7, 2.3, 'dark')
            a.c(knee, foot, 2.3, 1.5, 'dark')
    # wing cases lift on the wind-up and show the violet under-wings
    lift = wind * 7
    if lift > 1:
        a.e(-7, by + 8 + lift, 18, 7, 'wingu')
    a.e(0, by, 25, 18.5, 'shell')
    a.e(-9, by + 8, 10, 5.5, 'shell', out=False)
    a.line((-1, by + 17), (-1, by - 12), 'dark0', 1)
    a.line((-2, by + 17), (-2, by - 12), 'shell1', 1)
    for (sx, sy, r) in ((-14, 4, 2.3), (-5, 11, 2.6), (8, 7, 2.1), (-9, -4, 2), (-18, -4, 1.6)):
        diamond(a, sx, by + sy, r, r * 1.3, 'glow0')
    for i, (lx, dx, near) in enumerate(((-9, -7, 1), (2, 1, 1), (13, 10, 1))):
        up = max(0, math.sin(n * math.pi / 2 + (i + 3) * 1.6)) * 6 if clip == 'walk' else 0
        hip = (lx, by - 14)
        knee = (lx + dx * 1.3, by - 14 + flip * 12)
        foot = (lx + dx * 1.7, lerp(up, by + 22 + math.sin(n * 1.3 + i) * 3, flip))
        a.c(hip, knee, 3, 2.5, 'dark')
        a.c(knee, foot, 2.5, 1.6, 'dark')
    # head with a golden horn, big eyes and pincers
    hx = 15 + strike * 6 - wind * 3
    hy = by - 4 - strike * 2 + wind * 2 - flip * 3
    a.c((hx + 5, hy + 8), (hx + 3 - sw * 1.2, hy + 21), 1.2, 1.2, 'dark')
    a.e(hx + 3 - sw * 1.2, hy + 22, 2.6, 2.6, 'glow')
    a.e(hx, hy, 12.5, 10.5, 'dark')
    a.poly([(hx - 2, hy + 8), (hx + 3, hy + 22 + strike * 2), (hx + 8, hy + 8)], 'horn1')
    a.line((hx + 1, hy + 9), (hx + 3, hy + 19), 'horn2', 1)
    spread = 2 + max(wind, strike) * 4
    for s in (-1, 1):
        a.c((hx + 9, hy - 7), (hx + 17, hy - 5 - s * spread * .5), 2.3, 1.1, 'horn')
    a.eye(hx + 3.5, hy + 1.4, 4.4, iris='iris')
    a.eye(hx - 5, hy + 3, 3.2, iris='iris')
    a.dot(hx + 9, hy - 3.6, 'blush', 2)
    if not back and fall < .8:
        a.e(mx, my, 4.6, 4.6, 'moon')
        a.dot(mx - 1.6, my + 1.6, 'shine', 2)
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            star(a, min(hx + 16 + k * 3.4, 38), hy - 1 + (k % 2) * 6, 2.2, 'glow0')
    return a.done()


# ------------------------------------------------------------------------------------------------
def eclipsedryad(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('eclipsedryad', clip, n, sy=1 - fall * .5)
    sway = math.sin(n * math.pi / 3) * 1.6 if clip == 'idle' else sw * 2
    hx, hy = 2 + sway * .3, 59 + bob * .8
    # halo: a black eclipse disc with a burning corona
    if fall < .7:
        flare = max(wind, strike)
        if flare > .3:
            for k in range(8):
                ang = k * math.pi / 4 + .2
                star_r = 25 + flare * 4
                a.poly([(hx + math.cos(ang - .2) * 18, hy + math.sin(ang - .2) * 18), (hx + math.cos(ang) * star_r,
                        hy + math.sin(ang) * star_r), (hx + math.cos(ang + .2) * 18, hy + math.sin(ang + .2) * 18)],
                       'corona2', out=False)
        circle_ring(a, hx, hy, 18.5, 14, 'corona1', 'shade0')
        a.f.flat(ellipsoid(*a.g(hx - 3, hy + 4), 12, 8 * a.sy)[0], 'shade0')
    # root feet and a skirt of layered leaves
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.e(s * 7.5 + (s * math.sin(n * math.pi / 2) * 2 if clip == 'walk' else 0), 3 + up, 8, 3.8, 'bark')
        a.line((s * 11, 1 + up), (s * 16, 0 + up), 'bark0', 1)
    hem = [(-15, 36), (15, 36), (19 + sway * .5, 17), (14 + sway * .5, 10), (9, 16), (4, 8), (0, 16), (-4, 8), (-9, 16),
           (-14 - sway * .5, 10), (-19 - sway * .5, 17)]
    a.band(hem, 'leaf')
    for k in range(5):
        diamond(a, -12 + k * 6, 22 - (k % 2) * 3, 2.2, 5, 'leaf3')
    a.e(0, 41, 8.4, 7.6, 'leaf')
    a.e(2.5, 38.5, 2.8, 2.8, 'bloom')
    a.dot(1.4, 39.8, 'shine')
    # arms are branches with leaf hands
    far = (-17 - (sw * 2 if clip == 'walk' else 0), 33 + wind * 3 + (sw * 2 if clip == 'walk' else 0))
    branch(a, (-8, 44), far, 'bark', 3)
    a.e(far[0], far[1], 3.4, 3.4, 'leaf')
    hand = (lerp(lerp(17, 14, wind), 29, strike) + (sw * 2 if clip == 'walk' else 0), lerp(lerp(34, 69, wind), 43, strike) - (sw * 2 if clip == 'walk' else 0))
    if clip == 'die':
        hand = (lerp(17, 12, fall), lerp(34, 12, fall))
    branch(a, (8, 44), hand, 'bark', 3)
    a.poly([(hand[0] - 3, hand[1]), (hand[0], hand[1] + 6), (hand[0] + 3, hand[1]), (hand[0], hand[1] - 5)], 'leaf2')
    a.poly([(hand[0], hand[1] + 5), (hand[0] + 5, hand[1] + 2), (hand[0] + 3, hand[1] - 2)], 'leaf3', out=False)
    # chibi head: leaf-hair behind, face, fringe in front
    a.e(hx - 2.5, hy + 1, 14.5, 13, 'leaf')
    a.e(hx, hy, 12, 11, 'skin')
    fringe = [(hx - 12, hy + 2), (hx - 8, hy - 1), (hx - 4, hy + 5), (hx, hy - 1), (hx + 5, hy + 6), (hx + 9, hy + 1),
              (hx + 13, hy + 5), (hx + 12, hy + 12), (hx - 11, hy + 12)]
    a.poly(fringe, 'leaf1')
    a.line((hx - 6, hy + 10), (hx + 7, hy + 10), 'leaf2', 1)
    a.eye(hx + 3, hy - 3, 4.3, iris='iris')
    a.eye(hx + 10.5, hy - 3, 3.4, iris='iris')
    a.dot(hx - 2.5, hy - 7, 'blush', 3)
    a.dot(hx + 6, hy - 8, 'ink', 1)
    for s, ang in ((-1, -.25), (1, .15)):                                      # branch antlers
        ax_ = hx + s * 6
        branch(a, (ax_, hy + 11), (ax_ + s * 7 + ang * 8, hy + 22), 'bark', 2)
        branch(a, (ax_ + s * 4, hy + 17), (ax_ + s * 12, hy + 21), 'bark', 1)
        diamond(a, ax_ + s * 8 + ang * 8, hy + 24, 2.2, 3.4, 'leaf3')
        diamond(a, ax_ + s * 13, hy + 22, 2, 3, 'leaf2')
    if clip == 'attack' and n in (3, 4, 5):
        for k in range(4):
            diamond(a, min(hand[0] + 6 + k * 5 + (n - 3) * 2, 38), hand[1] - 3 + (k % 2) * 6 - (n - 3), 3.4, 2, 'leaf3')
    if clip == 'die':
        for k in range(6):
            diamond(a, -22 + k * 9, max(3, 40 - fall * 36 + (k % 3) * 8 - k), 2.4, 3.4, 'leaf2' if k % 2 else 'leaf3')
    return a.done()


# ------------------------------------------------------------------------------------------------
def meteorgolem(clip, n):
    T = timing(clip, n)
    fall, wind, strike, bob, sw = T['fall'], T['wind'], T['strike'], T['bob'], T['sw']
    a = Art('meteorgolem', clip, n, sy=1 - fall * .45)
    b = bob * .8
    tx = fall * 0
    # ember trail and orbiting chips
    if clip != 'die':
        for k in range(4):
            a.dot(-16 + k * 7, 66 + b + ((n * 2 + k * 5) % 12), 'ember0' if k % 2 else 'ember1', 2)
        for k in range(3):
            th = n * (math.pi / 3 if clip == 'idle' else math.pi / 4) + k * 2.1
            a.e(math.cos(th) * 30, 50 + math.sin(th) * 6 + k * 3, 3 + k % 2, 3 + k % 2, 'chip')
    # legs
    for s in (-1, 1):
        up = max(0, math.sin(n * math.pi / 2 + (0 if s < 0 else math.pi))) * 5 if clip == 'walk' else 0
        a.e(s * 10 + fall * s * 5, 9 + up, 9.4, 8.4, 'rock')
        a.e(s * 10 + fall * s * 5 - s, 3 + up, 8, 3, 'rock', out=False)
    # far arm and fist
    a.c((-17, 38 + b), (-27 - fall * 3, 25 - fall * 14), 6.4, 5.8, 'rock')
    a.e(-28 - fall * 3, 21 - fall * 12, 8.8, 8.2, 'rock')
    # torso with a fissure and an amethyst core
    a.e(0, 29 + b - fall * 8, 21, 17.4, 'rock')
    a.e(-8, 36 + b - fall * 8, 10, 6, 'rock', out=False)
    core = 'amethyst'
    a.e(1, 31 + b - fall * 8, 7.6, 8.4, core)
    if fall < .6:
        a.f.flat(ellipsoid(*a.g(1.2, 31.5 + b), 3.4, 4.2 * a.sy)[0], 'crack1')
        a.dot(-.4, 34 + b, 'shine', 2)
    zig = [(-14, 22), (-9, 27), (-12, 33), (-7, 36)]
    for (x0, y0), (x1, y1) in zip(zig, zig[1:]):
        a.line((x0, y0 + b), (x1, y1 + b), 'crack1' if fall < .6 else 'rock0', 2)
    for (x0, y0), (x1, y1) in zip([(12, 20), (15, 26), (11, 31)], [(15, 26), (11, 31), (14, 36)]):
        a.line((x0, y0 + b), (x1, y1 + b), 'crack1' if fall < .6 else 'rock0', 1)
    # shoulder crystals
    crystal(a, -16, 40 + b - fall * 8, 3.4, 11, 'amethyst', tilt=-2)
    crystal(a, 15, 40 + b - fall * 8, 3.2, 9, 'amethyst', tilt=2)
    # head: heavy boulder with a brow, glowing eyes and a jagged mouth
    hx = lerp(0, -9, fall)
    hy = lerp(54 + b, 13, fall)
    a.e(hx, hy, 14, 11.8, 'rock')
    a.e(hx - 5, hy + 5, 7, 4, 'rock', out=False)
    a.poly([(hx - 12, hy + 4), (hx + 12, hy + 4), (hx + 10, hy + 1), (hx - 10, hy + 1)], 'rock0', out=False)
    state = T['state']
    for dx in (-5.4, 5.6):
        if state == 'dead':
            a.line((hx + dx - 2.5, hy - 1.5), (hx + dx + 2.5, hy - 5), 'ink', 2)
            a.line((hx + dx - 2.5, hy - 5), (hx + dx + 2.5, hy - 1.5), 'ink', 2)
        else:
            a.f.flat(ellipsoid(*a.g(hx + dx, hy - 2.5), 3.8, 3.3 * a.sy)[0], 'crack2', outline=True)
            a.f.flat(ellipsoid(*a.g(hx + dx + .8, hy - 2.7), 1.8, 2.2 * a.sy)[0], 'ink')
            a.dot(hx + dx - 1.4, hy - .6, 'shine', 1)
    if state == 'angry':
        a.line((hx - 10, hy + 3), (hx - 2, hy), 'ink', 2)
        a.line((hx + 2, hy), (hx + 10, hy + 3), 'ink', 2)
    mz = [(hx - 6, hy - 7), (hx - 3, hy - 9), (hx, hy - 7), (hx + 3, hy - 9), (hx + 6, hy - 7)]
    for p, q in zip(mz, mz[1:]):
        a.line(p, q, 'ink', 1)
    # near arm: swings up then slams down
    fist = (lerp(lerp(29, 25, wind), 31, strike), lerp(lerp(25, 71, wind), 8, strike))
    if clip == 'die':
        fist = (lerp(29, 33, fall), lerp(25, 6, fall))
    a.c((17, 38 + b - fall * 8), fist, 7, 6.4, 'rock')
    a.e(fist[0], fist[1], 10, 9.2, 'rock')
    a.e(fist[0] - 3, fist[1] + 4, 4.6, 2.6, 'rock', out=False)
    for k in range(3):
        a.line((fist[0] + 2 + k * 2.4, fist[1] - 3), (fist[0] + 3 + k * 2.4, fist[1] - 7), 'rock0', 1)
    if clip == 'attack' and n in (4, 5):
        for k in range(5):
            a.e(min(32 + k * 2.4, 38), 4 + (k * 7) % 9 + (n - 4) * 3, 2.4, 2.4, 'chip' if k % 2 else 'rock')
    if clip == 'die':
        for k in range(5):
            a.e(-24 + k * 12, 3 + (k % 2) * 2, 4.2 - k % 2, 3, 'rock' if k % 2 else 'chip')
    return a.done()


DRAW = dict(voidmoth=voidmoth, crystalwyrm=crystalwyrm, orbitbeetle=orbitbeetle, eclipsedryad=eclipsedryad,
            meteorgolem=meteorgolem)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/astral-preview')
    print('ok')
