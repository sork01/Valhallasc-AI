"""Cel-shaded Thousandfold Pavilion enemies (zone 31, dungeon) for make_thousandfold_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py thousandfold preview [kind...]` writes contact sheets to
test-results/thousandfold-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import bird, burst, floater, humanoid, moth, parts, quad, spark, spider, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('pavilion_foldling', 'pavilion_inkmoth', 'pavilion_silkguard', 'pavilion_mirror', 'pavilion_weaver',
         'pavilion_sovereign')

PALETTES = {
    'pavilion_foldling': mk(paper=('#a8a0b8', '#e0d8ec', '#fbf6ff', '#ffffff'), wing=('#b8284a', '#f0587a', '#ffa0b0'),
                            crease=('#8a80a0', '#c8c0dc'), beak=('#a8741a', '#f4c448', '#fff0a0'), leg=('#6a5a7a', '#a898b8'),
                            claw=('#7a6a8a', '#b8a8c8'), iris='#2a1c4a', blush='#ff8aa8', shine=('#fff8c8', '#ffffff')),
    'pavilion_inkmoth': mk(body=('#14101c', '#2a2438', '#5a4a78', '#9a88c0'), wing=('#0c0a14', '#241c34', '#4a3a68', '#8a78b8'),
                           wing2=('#2a2438', '#6a5a98', '#b8a8e8'), spot=('#d8b01c', '#fff070'), glow=('#c8a01c', '#fff070'),
                           iris='#ffe060', blush='#ff8aa8', ant=('#3a3050', '#7a6aa0')),
    'pavilion_silkguard': mk(silk=('#7a1c3a', '#c83a5c', '#f07890', '#ffc0c8'), skin=('#d8a888', '#f4ccac', '#ffe8d0'),
                             gold=('#9c6a1b', '#e3ac38', '#ffe587'), hat=('#c8a85a', '#f0d890', '#fff4c8'),
                             shaft=('#4a2a1c', '#8a5a34', '#c08a54'), blade=('#8a96b0', '#d0dcf0', '#ffffff'),
                             iris='#3a1c2a', blush='#ff8a9a', mouth=('#4a1028', '#d83a68'), hair=('#1c1424', '#3a2c4c')),
    'pavilion_mirror': mk(robe=('#1c3a6a', '#3a68b8', '#78a8f0', '#c8e0ff'), skin=('#d8b4a4', '#f8d8c4', '#fff0e4'),
                          mirror=('#7a8ab0', '#c8d8f8', '#f4faff'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                          hair=('#1c1830', '#3a3060'), iris='#3a2a88', blush='#ff8aa8', mouth=('#4a1028', '#d83a68'),
                          ribbon=('#b8284a', '#f0587a', '#ffa0b0')),
    'pavilion_weaver': mk(body=('#2a1c48', '#5a3a98', '#9070d8', '#d0b8ff'), abd=('#1c1438', '#4a2c88', '#7a58c8', '#b8a0f4'),
                          leg=('#2a1c48', '#5a3a98', '#9070d8'), mark=('#f0587a', '#ffc0c8'), fang=('#d8d0e8', '#ffffff'),
                          iris='#ff5a7a', blush='#ff8aa8', thread=('#d8c8f0', '#ffffff'), silk=('#e0d0f4', '#ffffff')),
    'pavilion_sovereign': mk(robe=('#6a1428', '#b8283c', '#f06070', '#ffb0b0'), skin=('#d8b4a4', '#f8d8c4', '#fff0e4'),
                             paper=('#b0a8c0', '#e8e0f4', '#fbf6ff', '#ffffff'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                             hair=('#1c1830', '#3a3060'), iris='#7a1c3a', blush='#ff8aa8', mouth=('#4a1028', '#d83a68'),
                             fan=('#8a1c28', '#e83c48', '#ffa0a0'), wave=('#fff0a0', '#ffffff')),
}
R.PALETTES.update(PALETTES)


def pavilion_foldling(clip, n):
    a = R.Art('pavilion_foldling', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # fold creases across the body
        a.line((-8, c.cy - 8), (6, c.cy + 12), 'crease1', 1)
        a.line((-2, c.cy - 12), (10, c.cy + 4), 'crease1', 1)
        a.line((-12, c.cy), (-2, c.cy + 12), 'crease1', 1)

    c = bird(a, 'paper', None, wing='wing', leg='leg', claw='claw', beak='beak', R=(13, 14), pre=pre, hr=(10.6, 9.6),
             tailn=0)
    # a stiff folded tail fan
    a.poly([(-10, c.cy + 2), (-28, c.cy - 4 + c.T['sw'] * 2), (-26, c.cy + 12), (-10, c.cy + 8)], 'wing1')
    spark(a, 'shine1', c.hx + 20, c.hy)
    return a.done()


def pavilion_inkmoth(clip, n):
    a = R.Art('pavilion_inkmoth', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    c = moth(a, 'body', 'wing', 'wing2', spot='spot', R=(7, 11), cy=38, span=1.1)
    spark(a, 'spot1', c.x + 24, c.y + 6)
    return a.done()


def pavilion_silkguard(clip, n):
    a = R.Art('pavilion_silkguard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def post(c):
        a.e(c.hx, c.hy + 7, 17, 4, 'hat')
        a.poly([(c.hx - 11, c.hy + 8), (c.hx, c.hy + 21), (c.hx + 11, c.hy + 8)], 'hat1')
        a.e(c.hx, c.hy + 21, 2, 2, 'gold', out=False)

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 3, hy - 22), (hx + 3, hy + 28), 'shaft1', 2)
        a.poly([(hx + 3, hy + 28), (hx + 6, hy + 18), (hx, hy + 18)], 'blade2')
        a.e(hx + 2, hy + 18, 2.6, 2.6, 'silk', out=False)

    c = humanoid(a, 'silk', 'skin', leg='silk', arm='silk', hand='skin', w=13, legh=15, th=22, hr=(10, 9.4), post=post,
                 weapon=weapon, pk=.8)
    a.e(0, 20, 14, 3, 'gold', out=False)
    spark(a, 'blade1', c.near[0] + 12, c.near[1])
    return a.done()


def pavilion_mirror(clip, n):
    T = R.timing(clip, n)
    a = R.Art('pavilion_mirror', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']

    def pre(c):
        a.c((c.hx - 6, c.hy + 4), (c.hx - 13 + sw * 2, c.hy - 14), 4.4, 2.4, 'hair')
        a.e(c.far[0] - 3, c.far[1] + 2, 9, 11, 'gold')
        a.e(c.far[0] - 3, c.far[1] + 2, 7, 9, 'mirror')
        a.dot(c.far[0] - 6, c.far[1] + 6, 'mirror2', 2)

    def post(c):
        a.e(c.hx - 1, c.hy + 9, 10, 2.6, 'hair')
        for k in range(3):
            diamond(a, c.hx - 5 + k * 5, c.hy + 14 - abs(k - 1) * 1.4, 1.8, 3.4, 'gold', out=True)

    def weapon(c):
        hx, hy = c.near
        a.e(hx + 5, hy + 8, 8.6, 10.4, 'gold')
        a.e(hx + 5, hy + 8, 6.8, 8.6, 'mirror')
        a.dot(hx + 2, hy + 13, 'mirror2', 2)

    c = humanoid(a, 'robe', 'skin', w=12, legh=3, th=26, hr=(9.6, 9.6), robe=True, hem='ribbon', pre=pre, post=post,
                 weapon=weapon, pk=.88)
    spark(a, 'mirror1', c.near[0] + 16, c.near[1] + 4)
    return a.done()


def pavilion_weaver(clip, n):
    a = R.Art('pavilion_weaver', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a loom of silk thread hanging from the abdomen
        sw = c.T['sw']
        for k in range(4):
            a.line((-24 + k * 3, c.cy - 8), (-24 + k * 3 + sw, 4), 'thread1', 1)

    def post(c):
        # hourglass-free pattern: pink diamonds along the abdomen
        for k in range(3):
            diamond(a, -22 + k * 8, c.cy + 6 + (k % 2) * 3, 2.4, 3.4, 'mark1')

    c = spider(a, 'body', 'abd', 'leg', R=(17, 14), hr=(11, 9.6), base=24, legspan=15, pre=pre, post=post, abdx=-16, ox=-2)
    spark(a, 'silk1', c.hx + 18, c.hy)
    return a.done()


def pavilion_sovereign(clip, n):
    T = R.timing(clip, n)
    a = R.Art('pavilion_sovereign', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']

    def pre(c):
        # layered paper wings of robe sleeves behind and a tall folded crown
        for k, s in enumerate((-1, 1)):
            a.e(c.hx + s * 13, c.hy - 12 + k * 2, 5, 15, 'paper', ang=s * -.3)
        a.band([(c.hx - 9, c.hy + 7), (c.hx + 9, c.hy + 7), (c.hx + 6, c.hy + 28), (c.hx, c.hy + 34), (c.hx - 6, c.hy + 28)], 'paper')
        a.line((c.hx, c.hy + 8), (c.hx, c.hy + 32), 'paper1', 1)

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 2, hy - 8), (hx + 3, hy + 16), 'gold1', 2)
        for k in range(5):
            ang = -.5 + k * .25
            a.poly([(hx + 3, hy + 16), (hx + 3 + math.sin(ang) * 17, hy + 16 + math.cos(ang) * 15),
                    (hx + 3 + math.sin(ang + .22) * 17, hy + 16 + math.cos(ang + .22) * 15)], 'fan' + str(1 + k % 2))

    c = humanoid(a, 'robe', 'skin', w=14, legh=3, th=30, hr=(10, 9.6), robe=True, hem='gold', pre=pre, weapon=weapon,
                 pk=.78)
    spark(a, 'wave1', c.near[0] + 16, c.near[1] + 8)
    return a.done()


DRAW = dict(pavilion_foldling=pavilion_foldling, pavilion_inkmoth=pavilion_inkmoth, pavilion_silkguard=pavilion_silkguard,
            pavilion_mirror=pavilion_mirror, pavilion_weaver=pavilion_weaver, pavilion_sovereign=pavilion_sovereign)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/thousandfold-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
