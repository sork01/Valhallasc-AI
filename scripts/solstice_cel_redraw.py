"""Cel-shaded Silent Solstice enemies (zone 39, dungeon) for make_yearwheel_dungeon_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py solstice preview [kind...]` writes contact sheets to
test-results/solstice-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('solstice_flurry', 'solstice_owl', 'solstice_guard', 'solstice_watcher', 'solstice_harbinger', 'solstice_heart')

PALETTES = {
    'solstice_flurry': mk(snow=('#5a78a8', '#a8c4ec', '#e0f0ff', '#ffffff'), swirl=('#7a98c8', '#c8dcfa', '#f4faff'),
                          iris='#1c2a6a', blush='#ffa0c0', mouth=('#2a3a78', '#6a88d0'), shadow=('#2a3a58', '#4a5a88'),
                          glint=('#c8f4ff', '#ffffff')),
    'solstice_owl': mk(feather=('#1c2248', '#3a4688', '#7080c8', '#c0ccf8'), face=('#8a98d0', '#d0dcff', '#f4f8ff'),
                       beak=('#a8741a', '#f4c448', '#fff0a0'), leg=('#3a3a58', '#7a7aa0'), claw=('#4a4a68', '#9a9ac0'),
                       iris='#ffe060', blush='#ffa0c8', star=('#fff8c8', '#ffffff')),
    'solstice_guard': mk(plate=('#2a4a78', '#5a8ac0', '#98c8f0', '#e0f4ff'), skin=('#d0b8b0', '#f4d8cc', '#fff0e8'),
                         ice=('#58a8d8', '#b0e8ff', '#ffffff'), cloth=('#1c2a58', '#3a4a98'), shaft=('#4a3a2a', '#8a6a48', '#c8a074'),
                         iris='#2a6ac8', blush='#ffa0a0', mouth=('#4a1028', '#d83a68'), fur=('#c8d4e8', '#f8fcff')),
    'solstice_watcher': mk(ice=('#2a5a98', '#5a98d8', '#a0d8ff', '#f0fcff'), body=('#1c3a68', '#3a68a8', '#78a8e0', '#c8e4ff'),
                           eye=('#e8f4ff', '#ffffff'), iris='#2a1c6a', pupil='#1c1c3a', blush='#ffa0c0',
                           mouth=('#0c2a58', '#3a78c8'), shadow=('#2a3a58', '#4a5a88'), leg=('#1c3a68', '#3a68a8', '#78a8e0')),
    'solstice_harbinger': mk(cloak=('#14123a', '#2a2a6a', '#4a4ea8', '#8a90e0'), skin=('#a8a8d0', '#d8d8f4', '#f4f4ff'),
                             moon=('#a8a0d0', '#e8e4ff', '#ffffff'), star=('#fff0a0', '#ffffff'), iris='#b8f0ff',
                             blush='#ffa0d8', mouth=('#14123a', '#5a4a98'), hair=('#2a2a6a', '#6a6ab8'),
                             wing=('#1c1c58', '#3a3a98', '#7a80d8')),
    'solstice_heart': mk(crystal=('#1c3a78', '#3a78d0', '#88c4ff', '#e8f8ff'), moon=('#a8a0d0', '#e8e4ff', '#ffffff'),
                         star=('#fff0a0', '#ffffff'), iris='#fffcd0', blush='#ffa0d8', mouth=('#0c1c48', '#3a58a8'),
                         shadow=('#2a3a58', '#4a5a88'), ring=('#5a78a8', '#a8c4ec', '#e8f4ff')),
}
R.PALETTES.update(PALETTES)


def solstice_flurry(clip, n):
    a = R.Art('solstice_flurry', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a spiralling snow tail winding down to the ground
        for k in range(5):
            ang = n * .5 + k * 1.2
            a.e(c.x - 6 + math.cos(ang) * (12 - k * 1.6), c.y - 8 - k * 4.4, 9 - k * 1.4, 4.4 - k * .4, 'swirl')
        for k in range(4):
            a.dot(c.x - 14 + k * 8, c.y + 12 + (n + k) % 3 * 3, 'glint1', 2)

    c = floater(a, 'snow', R=(14, 13), cy=34, pre=pre, eye=4.8, shadow='shadow', hover=3)
    spark(a, 'glint0', c.x + 21, c.y)
    return a.done()


def solstice_owl(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solstice_owl', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.ox = -2
    a.pk = .92
    a.lift = fall * 6
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-4, -8, -12, 6, 8, 4, 1, 0)[n]
    cy = 32 + b - fall * 8
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 6, cy - 12), (s * 7, 5 + up), 2.2, 1.8, 'leg')
        a.e(s * 7 + 2, 3 + up, 5, 1.8, 'claw')
    a.e(0, cy, 17, 20, 'feather')
    a.e(4, cy - 3, 10, 13, 'face', out=False)
    a.e(-14, cy + 1 + flap, 7, 15, 'feather', ang=.15)
    a.e(14, cy + 1 + flap * .6, 5, 13, 'feather', ang=-.15)
    for k in range(3):
        star(a, -14 + k * 3, cy - 4 + k * 6 + flap * .6, 1.8, 'star0')
    hx, hy = 2 + strike * 4, cy + 18
    for s in (-1, 1):
        a.poly([(hx + s * 9, hy + 6), (hx + s * 13, hy + 17), (hx + s * 5, hy + 10)], 'feather1')
    a.e(hx, hy, 15, 11.4, 'feather')
    a.e(hx - 5, hy + 5, 7, 3, 'feather', out=False)
    for s in (-1, 1):
        a.e(hx + s * 6.4, hy + .6, 6.6, 7, 'face')
    a.eye(hx - 6.4, hy + .6, 4.6, iris='iris', look=(.5, .1))
    a.eye(hx + 6.4, hy + .6, 4.6, iris='iris', look=(.5, .1))
    a.poly([(hx - 2, hy - 2), (hx + 2, hy - 2), (hx, hy - 8 - max(wind * .5, strike) * 2)], 'beak1')
    a.dot(hx - 12, hy - 4, 'blush', 2)
    # a crescent moon marking on the chest
    a.e(4, cy - 6, 5, 5, 'star', out=False)
    a.e(6, cy - 6, 4.4, 4.4, 'feather', out=False)
    spark(a, 'star1', hx + 20, hy - 4)
    return a.done()


def solstice_guard(clip, n):
    a = R.Art('solstice_guard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        fx, fy = c.far[0] - 4, c.far[1] + 3
        a.band([(fx - 10, fy + 12), (fx + 10, fy + 12), (fx + 10, fy - 6), (fx, fy - 14), (fx - 10, fy - 6)], 'ice')
        a.line((fx, fy + 9), (fx, fy - 11), 'ice3', 1)
        a.line((fx - 7, fy), (fx + 7, fy), 'ice3', 1)

    def post(c):
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 11, c.hy + 11), (c.hx, c.hy + 15), (c.hx - 11, c.hy + 11)], 'plate')
        a.e(c.hx - 8, c.hy + 11, 5, 5, 'fur', out=True)
        a.e(c.hx + 8, c.hy + 11, 5, 5, 'fur', out=True)

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 3, hy - 22), (hx + 3, hy + 26), 'shaft1', 2)
        a.poly([(hx + 3, hy + 28), (hx + 7, hy + 18), (hx - 1, hy + 18)], 'ice2')

    c = humanoid(a, 'plate', 'skin', leg='cloth', arm='plate', hand='skin', w=14, legh=15, th=23, hr=(10.4, 9.4),
                 pre=pre, post=post, weapon=weapon, pk=.8, armw=4)
    spark(a, 'ice2', c.near[0] + 14, c.near[1])
    return a.done()


def solstice_watcher(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solstice_watcher', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk = .84
    a.lift = fall * 5
    b = bob * .6
    # two stilt legs of ice supporting one huge frozen eye
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 9, 36 + b), (s * 11, 5 + up), 4.4, 3, 'leg')
        a.e(s * 13 + 2, 3 + up, 5.4, 2.4, 'ice')
    a.e(0, 52 + b, 22, 20, 'body')
    a.e(-6, 62 + b, 11, 4.4, 'body', out=False)
    # the eye
    ex, ey = strike * 3, 52 + b
    a.e(ex + 1, ey, 15, 13, 'eye')
    a.eye(ex - 1, ey + 1, 7, iris='iris', look=(.5, .1))
    a.dot(ex - 12, ey - 6, 'blush', 3)
    a.e(ex + 7, ey - 12, 4.4, 1.4 + max(wind * .4, strike) * 3, 'mouth')
    # ice shards crowning the top
    for k in range(5):
        a.poly([(-14 + k * 7, 68 + b - abs(k - 2) * 1.6), (-12 + k * 7, 78 + b - abs(k - 2) * 2), (-9 + k * 7, 68 + b - abs(k - 2) * 1.6)], 'ice' + str(1 + k % 2))
    # frost arms
    far = (-26 + sw, 44 + b)
    a.c((-19, 52 + b), far, 3.6, 3, 'body')
    near = (R.lerp(R.lerp(25, 24, wind), 28, strike), R.lerp(R.lerp(44, 66, wind), 40, strike) + b)
    if clip == 'die':
        near = (R.lerp(26, 30, fall), R.lerp(44, 8, fall))
    a.c((19, 52 + b), near, 3.8, 3.2, 'body')
    a.e(near[0], near[1], 4, 4, 'ice')
    spark(a, 'ice2', near[0] + 10, near[1] - 6)
    return a.done()


def solstice_harbinger(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solstice_harbinger', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']
    f = math.sin(n * math.pi / 3) * 2 if clip == 'idle' else 0
    if clip == 'attack':
        f = (-2, -4, -6, 4, 5, 3, 1, 0)[n]
    hov = 8 + T['bob'] * 1.1

    def pre(c):
        for s in (-1, 1):
            a.e(c.hx + s * 22, c.hy - 6 + f, 8, 18, 'wing', ang=s * -.55)
            a.e(c.hx + s * 18, c.hy - 2 + f, 4.4, 11, 'wing', ang=s * -.55, out=False)
            star(a, c.hx + s * 22, c.hy - 8 + f, 2.2, 'star0')
        a.c((c.hx - 5, c.hy + 4), (c.hx - 14 + sw * 2, c.hy - 14), 4.4, 2.4, 'hair')

    def post(c):
        # a crescent moon crown
        a.e(c.hx + 1, c.hy + 14, 7, 7, 'moon')
        a.e(c.hx + 4, c.hy + 14, 6, 6, 'cloak', out=False)
        star(a, c.hx - 7, c.hy + 13, 2.4, 'star0')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 2, hy - 8), (hx + 3, hy + 22), 'moon1', 2)
        a.e(hx + 3, hy + 25, 6, 6, 'moon')
        a.e(hx + 5, hy + 25, 4.6, 4.6, 'cloak', out=False)

    c = humanoid(a, 'cloak', 'skin', w=13, legh=hov, th=24, hr=(9.6, 9.6), robe=True, hem='moon', pre=pre, post=post,
                 weapon=weapon, pk=.84)
    spark(a, 'star1', c.near[0] + 14, c.near[1] + 10)
    return a.done()


def solstice_heart(clip, n):
    a = R.Art('solstice_heart', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    spin = n * .3

    def pre(c):
        for k in range(8):
            ang = spin + k * .785
            a.poly([(c.x + math.cos(ang - .14) * 17, c.y + math.sin(ang - .14) * 19),
                    (c.x + math.cos(ang) * (27 if k % 2 else 23), c.y + math.sin(ang) * (29 if k % 2 else 25)),
                    (c.x + math.cos(ang + .14) * 17, c.y + math.sin(ang + .14) * 19)], 'crystal' + str(1 + k % 2))
        a.e(c.x, c.y, 19, 21, 'ring')

    def post(c):
        a.e(c.x - 10, c.y + 12, 5, 6, 'crystal', out=False)
        star(a, c.x + 12, c.y + 14, 2.6, 'star0')
        star(a, c.x - 16, c.y - 6, 2, 'star0')

    c = floater(a, 'crystal', R=(16, 18), cy=42, pre=pre, post=post, eye=6, shadow='shadow', hover=3, pk=.84)
    spark(a, 'star1', c.x + 28, c.y)
    return a.done()


DRAW = dict(solstice_flurry=solstice_flurry, solstice_owl=solstice_owl, solstice_guard=solstice_guard,
            solstice_watcher=solstice_watcher, solstice_harbinger=solstice_harbinger, solstice_heart=solstice_heart)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/solstice-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
