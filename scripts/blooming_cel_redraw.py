"""Cel-shaded Blooming Labyrinth enemies (zone 36, dungeon) for make_blooming_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py blooming preview [kind...]` writes contact sheets to
test-results/blooming-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, moth, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('bloom_spore', 'bloom_moth', 'bloom_guard', 'bloom_thornkeeper', 'bloom_mirror', 'bloom_heart')

PALETTES = {
    'bloom_spore': mk(glass=('#6a58b8', '#a890f0', '#d8c8ff', '#ffffff'), petal=('#c83a8a', '#ff7ac0', '#ffc4e4', '#fff2f8'),
                      iris='#2a1c6a', blush='#ff8aa8', mouth=('#4a0c3a', '#c83a8a'), shadow=('#3a2a58', '#6a58a0'),
                      glow=('#fff8c8', '#ffffff')),
    'bloom_moth': mk(body=('#5a2a6a', '#a050b8', '#d890e8', '#fcd0ff'), wing=('#c83a8a', '#ff7ac0', '#ffc4e4', '#fff2f8'),
                     wing2=('#1c8a98', '#58d8d8', '#b8fcf0'), spot=('#d8b01a', '#fff070'), glow=('#c8a01c', '#fff070'),
                     iris='#2a1c6a', blush='#ff8aa8', ant=('#4a2a58', '#9a68b0')),
    'bloom_guard': mk(glass=('#1c6a78', '#3aa8b8', '#88e0e8', '#d8fcff'), vine=('#1c5a2c', '#3a9a48', '#78d868'),
                      skin=('#d0a888', '#f4ccac', '#ffe8d0'), petal=('#c83a8a', '#ff7ac0', '#ffc4e4'),
                      iris='#1c6a3a', blush='#ff9a8a', mouth=('#4a1028', '#d83a68'), leg=('#1c4a2c', '#3a8a48', '#78c868'),
                      shield=('#c83a8a', '#ff7ac0', '#ffc4e4', '#fff2f8')),
    'bloom_thornkeeper': mk(bark=('#2a1c28', '#5a3a50', '#8a5c7a', '#c090b0'), thorn=('#8a1c3a', '#d83a5a', '#ffa0b0'),
                            vine=('#1c5a2c', '#3a9a48', '#78d868'), skin=('#a88a78', '#d8b4a0', '#f8d8c4'),
                            blade=('#8a96b0', '#d0dcf0', '#ffffff'), iris='#ff5a7a', blush='#ff8aa8',
                            mouth=('#2a0c1c', '#a82a4a'), hat=('#3a2a1c', '#7a5a34', '#b88a56')),
    'bloom_mirror': mk(frame=('#a8286a', '#f05aa0', '#ffa0cc', '#fff0f8'), mirror=('#5a68b0', '#98acf0', '#d8e4ff', '#ffffff'),
                       petal=('#c83a8a', '#ff7ac0', '#ffc4e4', '#fff2f8'), iris='#2a1c6a', blush='#ff8aa8',
                       mouth=('#4a0c3a', '#c83a8a'), shadow=('#3a2a58', '#6a58a0'), vine=('#1c5a2c', '#3a9a48', '#78d868')),
    'bloom_heart': mk(rose=('#8a1c3a', '#d83a6a', '#ff7a9a', '#ffc4d4'), petal=('#a8284a', '#f05a7a', '#ffa0b4', '#fff0f4'),
                      vine=('#1c5a2c', '#3a9a48', '#78d868'), thorn=('#d8d0e8', '#ffffff'), iris='#2a1c3a',
                      blush='#ff8aa8', mouth=('#4a0c1c', '#c83a5a'), shadow=('#4a2a38', '#7a4a60'), glow=('#fff8c8', '#ffffff')),
}
R.PALETTES.update(PALETTES)


def bloom_spore(clip, n):
    a = R.Art('bloom_spore', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        for k in range(6):
            ang = k * 1.047 + n * .05
            a.e(c.x + math.cos(ang) * 11, c.y + math.sin(ang) * 11, 4.4, 6.6, 'petal', ang=ang + 1.57)

    c = floater(a, 'glass', R=(11, 11), cy=26, pre=pre, eye=4.4, shadow='shadow', hover=1)
    for k in range(3):
        star(a, c.x - 16 + k * 16, c.y + 16 + (k % 2) * 4 + n % 2, 1.8, 'glow1')
    spark(a, 'petal2', c.x + 18, c.y)
    return a.done()


def bloom_moth(clip, n):
    a = R.Art('bloom_moth', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    c = moth(a, 'body', 'wing', 'wing2', spot='spot', R=(7, 11), cy=38, span=1.15)
    spark(a, 'wing2', c.x + 24, c.y + 6)
    return a.done()


def bloom_guard(clip, n):
    a = R.Art('bloom_guard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        fx, fy = c.far[0] - 4, c.far[1] + 3
        for k in range(6):
            ang = k * 1.047
            a.e(fx + math.cos(ang) * 6, fy + math.sin(ang) * 6.6, 4.4, 5.4, 'shield', ang=ang + 1.57)
        a.e(fx, fy, 3.6, 3.6, 'glass')

    def post(c):
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 10, c.hy + 11), (c.hx, c.hy + 15), (c.hx - 10, c.hy + 11)], 'glass')
        for k in range(3):
            a.e(c.hx - 6 + k * 6, c.hy + 14 + (k == 1) * 3, 3, 5, 'petal', ang=(k - 1) * .5)

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 1, hy - 4), (hx + 4, hy + 20), 2.2, 3, 'vine')
        a.e(hx + 5, hy + 23, 5, 6, 'glass')
        a.poly([(hx + 5, hy + 28), (hx + 8, hy + 22), (hx + 2, hy + 22)], 'glass3', out=False)

    c = humanoid(a, 'glass', 'skin', leg='leg', arm='vine', hand='skin', w=13, legh=15, th=22, hr=(10, 9.4), pre=pre,
                 post=post, weapon=weapon, pk=.82)
    for k in range(3):
        a.line((-11 + k * 9, 20), (-9 + k * 9, 36), 'vine1', 1)
    spark(a, 'glass3', c.near[0] + 14, c.near[1])
    return a.done()


def bloom_thornkeeper(clip, n):
    a = R.Art('bloom_thornkeeper', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def post(c):
        a.e(c.hx, c.hy + 7, 16, 3.4, 'hat')
        a.e(c.hx, c.hy + 12, 9, 6, 'hat')
        for k in range(3):
            a.poly([(c.hx - 6 + k * 6, c.hy + 15), (c.hx - 4 + k * 6, c.hy + 22), (c.hx - 2 + k * 6, c.hy + 15)], 'thorn1', out=False)

    def weapon(c):
        hx, hy = c.near
        # giant garden shears: two crossed blades
        open_ = 4 + c.T['strike'] * 4
        a.line((hx, hy - 4), (hx + 3, hy + 12), 'bark1', 2)
        a.poly([(hx + 3, hy + 10), (hx + 3 - open_, hy + 30), (hx + 6 - open_, hy + 30), (hx + 7, hy + 10)], 'blade2')
        a.poly([(hx + 3, hy + 10), (hx + 3 + open_, hy + 30), (hx + 6 + open_, hy + 30), (hx + 7, hy + 10)], 'blade1')

    c = humanoid(a, 'bark', 'skin', leg='vine', arm='bark', hand='skin', w=16, legh=15, th=24, hr=(11.4, 10),
                 post=post, weapon=weapon, pk=.8, armw=4.6, handr=4, ox=-6)
    for k in range(4):
        a.poly([(-12 + k * 8, 38 + (k % 2) * 3), (-10 + k * 8, 46), (-8 + k * 8, 38 + (k % 2) * 3)], 'thorn1', out=False)
    spark(a, 'thorn1', c.near[0] + 14, c.near[1] + 10)
    return a.done()


def bloom_mirror(clip, n):
    a = R.Art('bloom_mirror', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        tendrils(a, c.x, c.y - 24, 4, 8, 22, 'vine', r0=2.8, sway=3)
        for k in range(10):
            ang = k * 0.6283
            a.e(c.x + math.cos(ang) * 21, c.y + math.sin(ang) * 23, 5.6, 8, 'petal', ang=ang + 1.57)
        a.e(c.x, c.y, 21, 23, 'frame')

    def post(c):
        # a sparkle across the glass
        a.line((c.x - 12, c.y + 14), (c.x - 5, c.y + 8), 'mirror3', 2)
        a.line((c.x - 12, c.y + 8), (c.x - 9, c.y + 5), 'mirror3', 1)

    c = floater(a, 'mirror', R=(17, 19), cy=44, pre=pre, post=post, eye=5.8, shadow='shadow', hover=2, pk=.86)
    spark(a, 'petal2', c.x + 28, c.y)
    return a.done()


def bloom_heart(clip, n):
    a = R.Art('bloom_heart', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    spin = n * .1

    def pre(c):
        tendrils(a, c.x, c.y - 18, 5, 8, 30, 'vine', r0=3.2, sway=4)
        # layered rose petals
        for k in range(8):
            ang = k * .785 + spin
            a.e(c.x + math.cos(ang) * 17, c.y + math.sin(ang) * 18, 8, 10, 'petal', ang=ang + 1.57)
        for k in range(6):
            ang = k * 1.047 + .4
            a.poly([(c.x + math.cos(ang - .12) * 22, c.y + math.sin(ang - .12) * 23),
                    (c.x + math.cos(ang) * 29, c.y + math.sin(ang) * 30),
                    (c.x + math.cos(ang + .12) * 22, c.y + math.sin(ang + .12) * 23)], 'thorn1')

    c = floater(a, 'rose', R=(15, 16), cy=42, pre=pre, eye=5.6, shadow='shadow', hover=3, pk=.84)
    spark(a, 'petal2', c.x + 28, c.y)
    return a.done()


DRAW = dict(bloom_spore=bloom_spore, bloom_moth=bloom_moth, bloom_guard=bloom_guard, bloom_thornkeeper=bloom_thornkeeper,
            bloom_mirror=bloom_mirror, bloom_heart=bloom_heart)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/blooming-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
