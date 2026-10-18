"""Cel-shaded Thunderheart Gate enemies (zone 35, dungeon) for make_astrolabe_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py thunder preview [kind...]` writes contact sheets to
test-results/thunder-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('thunder_spark', 'thunder_ray', 'thunder_guard', 'thunder_conductor', 'thunder_bastion', 'thunder_heart')

PALETTES = {
    'thunder_spark': mk(bolt=('#b88a14', '#f0d030', '#fff070', '#fffcc8'), body=('#c89a14', '#ffe040', '#fff6a0', '#ffffff'),
                        iris='#1c2a6a', blush='#ff8a6a', mouth=('#4a1c0c', '#d8541c'), shadow=('#4a4a6a', '#7a7aa0')),
    'thunder_ray': mk(body=('#1c2a68', '#3a58b8', '#78a0f0', '#d0e4ff'), belly=('#a8c0f0', '#e8f0ff'),
                      bolt=('#b88a14', '#f0d030', '#fff070'), iris='#ffe060', blush='#ff9ab8', fin=('#2a3a88', '#6a88d8', '#b8d0ff'),
                      shadow=('#2a2a4a', '#4a4a7a')),
    'thunder_guard': mk(slate=('#2a3040', '#5a647c', '#8e9ab4', '#c8d4ec'), skin=('#d0a888', '#f4ccac', '#ffe8d0'),
                        bolt=('#b88a14', '#f0d030', '#fff070'), iris='#1c4a9a', blush='#ff9a8a',
                        mouth=('#4a1028', '#d83a68'), cloth=('#1c2a58', '#3a4a98'), shield=('#3a4256', '#7a86a0', '#b8c4dc')),
    'thunder_conductor': mk(coat=('#3a1c6a', '#6a3ab8', '#a478f0', '#dcc8ff'), skin=('#d8b4a4', '#f8d8c4', '#fff0e4'),
                            bolt=('#b88a14', '#f0d030', '#fff070', '#fffcc8'), coil=('#7a4a1c', '#d88a34', '#ffc868'),
                            iris='#e8c01c', blush='#ff8aa8', mouth=('#4a1028', '#d83a68'), hair=('#d8d8f0', '#ffffff')),
    'thunder_bastion': mk(stone=('#2a3040', '#5a647c', '#8e9ab4', '#c8d4ec'), iron=('#3a3a4a', '#7a7a90', '#b8b8cc'),
                          bolt=('#b88a14', '#f0d030', '#fff070', '#fffcc8'), skin=('#5a647c', '#a0acc8', '#dce6fc'),
                          iris='#ffe060', blush='#ff9a8a', mouth=('#0c1220', '#3a4a68'), moss=('#1c5a38', '#3a9a58')),
    'thunder_heart': mk(crystal=('#2a1c78', '#5a3ad8', '#9a78ff', '#e0d0ff'), bolt=('#b88a14', '#f0d030', '#fff070', '#fffcc8'),
                        ring=('#3a4a6a', '#6a84b0', '#a8c4e8', '#e0f0ff'), iris='#ffe060', blush='#ff9ac8',
                        mouth=('#1c0c4a', '#6a3ac8'), shadow=('#2a2a4a', '#4a4a7a')),
}
R.PALETTES.update(PALETTES)


def zig(a, x, y, h, name, w=3):
    """A lightning zigzag hanging from (x, y) down h."""
    a.poly([(x, y), (x - w, y - h * .35), (x, y - h * .38), (x - w * 1.4, y - h), (x + w * .6, y - h * .5), (x - w * .2, y - h * .5),
            (x + w * .4, y)], name)


def thunder_spark(clip, n):
    a = R.Art('thunder_spark', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        for k in range(7):
            ang = n * .3 + k * 6.283 / 7
            a.poly([(c.x + math.cos(ang - .22) * 12, c.y + math.sin(ang - .22) * 12),
                    (c.x + math.cos(ang) * (22 if k % 2 else 18), c.y + math.sin(ang) * (22 if k % 2 else 18)),
                    (c.x + math.cos(ang + .22) * 12, c.y + math.sin(ang + .22) * 12)], 'bolt' + str(1 + k % 2))

    c = floater(a, 'body', R=(12, 12), cy=32, pre=pre, eye=4.8, shadow='shadow', hover=2)
    spark(a, 'bolt2', c.x + 22, c.y)
    return a.done()


def thunder_ray(clip, n):
    T = R.timing(clip, n)
    a = R.Art('thunder_ray', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk = .9
    a.ox = -2
    f = math.sin(n * math.pi / 3) if clip == 'idle' else math.sin(n * math.pi / 2) if clip == 'walk' else 0
    if clip == 'attack':
        f = (-.4, -.8, -1, .9, 1, .5, .1, 0)[n]
    x = strike * 6 - wind * 4
    y = 40 + bob * 1.4 - fall * 24
    a.e(x * .3, 4, 24, 2.4, 'shadow', out=False) if 'shadow0' in a.p.names else None
    # a tail with a lightning tip, flapping fins either side of a round face
    a.c((x - 14, y - 2), (x - 30 - sw * 2, y - 10), 3, 1, 'fin')
    zig(a, x - 31 - sw * 2, y - 6, 10, 'bolt1', 3)
    a.e(x - 12, y + 7 + f * 7, 15, 8, 'fin', ang=.35 - f * .35)
    a.e(x - 8, y + 1 - f * 3, 22, 10, 'body')
    a.e(x - 6, y - 3, 16, 5, 'belly', out=False)
    a.e(x + 12, y + 7 + f * 7, 9, 6, 'fin', ang=-.3 + f * .3)
    a.e(x + 7, y + 5, 12, 11, 'body')
    a.e(x + 3, y + 10, 6, 3, 'body', out=False)
    a.eye(x + 5, y + 6.4, 4.6, iris='iris', look=(.7, .1))
    a.eye(x + 14, y + 6, 3.8, iris='iris', look=(.9, .1))
    a.dot(x - 1, y + 2, 'blush', 3)
    a.e(x + 10, y - 1, 3, 1 + max(wind * .4, strike) * 2.4, 'fin')
    spark(a, 'bolt2', x + 22, y + 6)
    return a.done()


def thunder_guard(clip, n):
    a = R.Art('thunder_guard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        fx, fy = c.far[0] - 4, c.far[1] + 3
        a.band([(fx - 10, fy + 12), (fx + 10, fy + 12), (fx + 10, fy - 6), (fx, fy - 14), (fx - 10, fy - 6)], 'shield')
        zig(a, fx + 2, fy + 9, 16, 'bolt1', 3)

    def post(c):
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 11, c.hy + 11), (c.hx, c.hy + 15), (c.hx - 11, c.hy + 11)], 'slate')
        zig(a, c.hx + 1, c.hy + 24, 9, 'bolt1', 2)

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 1, hy - 4), (hx + 4, hy + 20), 2.2, 3.4, 'slate')
        a.e(hx + 5, hy + 23, 5.4, 5.4, 'slate')
        a.e(hx + 5, hy + 23, 2.4, 2.4, 'bolt')

    c = humanoid(a, 'slate', 'skin', leg='cloth', arm='slate', hand='skin', w=14, legh=15, th=23, hr=(10.4, 9.4),
                 pre=pre, post=post, weapon=weapon, pk=.82, armw=4)
    spark(a, 'bolt2', c.near[0] + 14, c.near[1])
    return a.done()


def thunder_conductor(clip, n):
    T = R.timing(clip, n)
    a = R.Art('thunder_conductor', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']

    def pre(c):
        # wild white hair and two coils on the shoulders
        a.e(c.hx - 4, c.hy + 7, 13, 10, 'hair')
        for s in (-1, 1):
            a.e(c.hx + s * 14, c.hy - 14, 5, 6.4, 'coil')
            a.line((c.hx + s * 14, c.hy - 18), (c.hx + s * 14, c.hy - 10), 'coil0', 1)

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 1, hy - 6), (hx + 4, hy + 18), 'coil1', 2)
        a.e(hx + 4, hy + 20, 3.6, 3.6, 'bolt')
        zig(a, hx + 8, hy + 24, 12, 'bolt2', 3)

    c = humanoid(a, 'coat', 'skin', leg='coat', arm='coat', hand='skin', w=13, legh=3, th=30, hr=(10, 9.6), robe=True,
                 hem='coil', pre=pre, weapon=weapon, pk=.84)
    spark(a, 'bolt2', c.near[0] + 14, c.near[1] + 8)
    return a.done()


def thunder_bastion(clip, n):
    a = R.Art('thunder_bastion', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # crenellations on the shoulders
        for s in (-1, 1):
            for k in range(3):
                a.band([(c.hx + s * 14 - 2 + k * s * 4, c.hy - 12), (c.hx + s * 14 + 2 + k * s * 4, c.hy - 12),
                        (c.hx + s * 14 + 2 + k * s * 4, c.hy - 6), (c.hx + s * 14 - 2 + k * s * 4, c.hy - 6)], 'stone', out=True)

    def post(c):
        # a crenellated crown with a bolt, blocky jaw
        a.band([(c.hx - 12, c.hy + 4), (c.hx + 12, c.hy + 4), (c.hx + 12, c.hy + 12), (c.hx - 12, c.hy + 12)], 'stone')
        for k in range(4):
            a.band([(c.hx - 12 + k * 6.4, c.hy + 11), (c.hx - 8 + k * 6.4, c.hy + 11), (c.hx - 8 + k * 6.4, c.hy + 17), (c.hx - 12 + k * 6.4, c.hy + 17)], 'stone')
        zig(a, c.hx + 1, c.hy + 12, 12, 'bolt1', 2)

    def weapon(c):
        hx, hy = c.near
        a.band([(hx, hy - 12), (hx + 17, hy - 12), (hx + 17, hy + 16), (hx, hy + 16)], 'iron')
        zig(a, hx + 9, hy + 12, 20, 'bolt1', 3)

    c = humanoid(a, 'stone', 'skin', leg='stone', arm='stone', hand='iron', w=19, legh=14, th=26, hr=(13, 10.4), pre=pre,
                 post=post, weapon=weapon, pk=.78, armw=5.4, handr=4.6, ox=-7)
    a.e(0, 34, 5, 5, 'bolt', out=False)
    spark(a, 'bolt2', c.near[0] + 18, c.near[1])
    return a.done()


def thunder_heart(clip, n):
    a = R.Art('thunder_heart', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    spin = n * .4

    def pre(c):
        # a ring of orbiting lightning bolts
        a.e(c.x, c.y, 27, 11, 'ring', ang=.25)
        a.e(c.x, c.y, 24, 8, 'crystal', ang=.25, out=False)
        for k in range(5):
            ang = spin + k * 1.257
            zig(a, c.x + math.cos(ang) * 25, c.y + math.sin(ang) * 10 + 6, 12, 'bolt1', 2)

    def post(c):
        for k in range(3):
            a.poly([(c.x - 9 + k * 9, c.y + 15), (c.x - 5 + k * 9, c.y + 26 + (k == 1) * 6), (c.x - 1 + k * 9, c.y + 15)], 'crystal3')

    c = floater(a, 'crystal', R=(17, 19), cy=40, pre=pre, post=post, eye=6, shadow='shadow', hover=3)
    spark(a, 'bolt2', c.x + 28, c.y)
    return a.done()


DRAW = dict(thunder_spark=thunder_spark, thunder_ray=thunder_ray, thunder_guard=thunder_guard,
            thunder_conductor=thunder_conductor, thunder_bastion=thunder_bastion, thunder_heart=thunder_heart)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/thunder-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
