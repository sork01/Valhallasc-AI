"""Cel-shaded Temple of the Rain Crown enemies (zone 32, dungeon) for make_rain_crown_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py rain_crown preview [kind...]` writes contact sheets to
test-results/rain-crown-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('rain_crown_droplet', 'rain_crown_oracle', 'rain_crown_guard', 'rain_crown_gatekeeper', 'rain_crown_sibyl',
         'rain_crown_sovereign')

PALETTES = {
    'rain_crown_droplet': mk(water=('#1c5ab8', '#3a98f0', '#88d8ff', '#e0fcff'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                             iris='#1c2a8a', blush='#ff8aa8', mouth=('#0c2a5a', '#3a78c8'), shadow=('#143a6a', '#245a98')),
    'rain_crown_oracle': mk(robe=('#0c5a48', '#1ca878', '#58e0a8', '#c0ffe0'), skin=('#58b898', '#a0e8c8', '#e0fff0'),
                            gold=('#9c6a1b', '#e3ac38', '#ffe587'), glow=('#40f0b8', '#d0ffec'), iris='#e8d02a',
                            blush='#ff9ab0', mouth=('#0c3a30', '#3a8870'), hair=('#0c4a58', '#1c88a0')),
    'rain_crown_guard': mk(plate=('#1c3a6a', '#3a68b0', '#78a8e8', '#c8e0ff'), skin=('#d8b4a4', '#f8d8c4', '#fff0e4'),
                           brolly=('#0c5a78', '#1ca0c8', '#78e0f4', '#d0fcff'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                           shaft=('#4a3a2a', '#8a6a48', '#c8a074'), blade=('#8a96b0', '#d0dcf0', '#ffffff'),
                           iris='#1c2a8a', blush='#ff9a9a', mouth=('#4a1028', '#d83a68'), cape=('#0c3a58', '#1c6a98')),
    'rain_crown_gatekeeper': mk(stone=('#3a4a5a', '#6a8098', '#a4bcd0', '#e0f0fc'), iron=('#3a3a4a', '#7a7a90', '#b8b8cc'),
                                skin=('#6a8098', '#a8c0d4', '#dcf0fc'), water=('#1c5ab8', '#3a98f0', '#88d8ff', '#e0fcff'),
                                gold=('#9c6a1b', '#e3ac38', '#ffe587'), iris='#ffe060', blush='#ff9a9a',
                                mouth=('#0c1c2a', '#3a5878'), moss=('#1c5a38', '#3a9a58')),
    'rain_crown_sibyl': mk(robe=('#2a2a78', '#4a58c8', '#8098f4', '#d0dcff'), skin=('#c8b8d0', '#eadcf0', '#fbf4ff'),
                           cloud=('#6a7a98', '#b8c4dc', '#f0f4ff'), drop=('#2a88e0', '#9ae8ff'), hair=('#3a2a88', '#7a68d8'),
                           gold=('#9c6a1b', '#e3ac38', '#ffe587'), iris='#3a88f0', blush='#ffa0c8',
                           mouth=('#2a1c58', '#6a58b8'), bolt=('#d8b01a', '#ffe85a', '#fffbc0')),
    'rain_crown_sovereign': mk(body=('#1c3a9a', '#3a78e0', '#88c0ff', '#e0f4ff'), crown=('#9c6a1b', '#e3ac38', '#ffe587', '#fff8c8'),
                               gem=('#c8283c', '#ff6a7a', '#ffc0c8'), water=('#1c5ab8', '#3a98f0', '#88d8ff', '#e0fcff'),
                               iris='#e8d02a', blush='#ff8aa8', mouth=('#0c2a5a', '#3a78c8'), shadow=('#143a6a', '#245a98')),
}
R.PALETTES.update(PALETTES)


def rain_crown_droplet(clip, n):
    a = R.Art('rain_crown_droplet', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a teardrop: a point on top, a splash ring under it
        a.poly([(c.x - 9, c.y + 6), (c.x + 1, c.y + 26), (c.x + 11, c.y + 6)], 'water1')
        a.e(c.x, 4, 16, 2.6, 'water', out=False)

    def post(c):
        for k, dx in enumerate((-5, 1, 7)):
            a.poly([(c.x + dx - 2, c.y + 20 - abs(dx) * .2), (c.x + dx, c.y + 26), (c.x + dx + 2, c.y + 20 - abs(dx) * .2)], 'gold1')
        a.e(c.x + 1, c.y + 20, 8, 2.2, 'gold', out=False)

    c = floater(a, 'water', R=(14, 13), cy=26, pre=pre, post=post, eye=4.8, shadow='shadow', hover=0)
    spark(a, 'water3', c.x + 20, c.y)
    return a.done()


def rain_crown_oracle(clip, n):
    T = R.timing(clip, n)
    a = R.Art('rain_crown_oracle', clip, n, sy=1 - T['fall'] * .5)
    hov = 8 + T['bob'] * 1.1

    def pre(c):
        a.e(c.hx - 3, c.hy + 2, 13, 12, 'hair')
        a.e(c.hx - 2, 4, 14, 2.4, 'glow', out=False)

    def post(c):
        # a jade third eye and a circlet
        a.e(c.hx + 1, c.hy + 10, 2.6, 2.6, 'glow')
        a.dot(c.hx + 1, c.hy + 10, 'iris', 1)
        a.band([(c.hx - 9, c.hy + 8), (c.hx + 9, c.hy + 8), (c.hx + 8, c.hy + 12), (c.hx - 8, c.hy + 12)], 'gold')

    def weapon(c):
        hx, hy = c.near
        a.e(hx + 4, hy + 6, 6, 6, 'glow', out=False)
        a.e(hx + 4, hy + 6, 3.6, 3.6, 'gold')

    c = humanoid(a, 'robe', 'skin', w=12, legh=hov, th=22, hr=(9.6, 9.6), robe=True, hem='glow', pre=pre, post=post,
                 weapon=weapon, mouth=None)
    spark(a, 'glow1', c.near[0] + 12, c.near[1])
    return a.done()


def rain_crown_guard(clip, n):
    a = R.Art('rain_crown_guard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a big umbrella shield held by the far hand
        fx, fy = c.far[0] - 3, c.far[1] + 8
        a.poly([(fx - 15, fy), (fx - 9, fy + 11), (fx, fy + 14), (fx + 9, fy + 11), (fx + 15, fy)], 'brolly1')
        a.e(fx, fy, 15, 3.4, 'brolly')
        a.line((fx, fy), (fx, fy - 14), 'shaft1', 1)

    def post(c):
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 11, c.hy + 11), (c.hx, c.hy + 14), (c.hx - 11, c.hy + 11)], 'plate')
        a.e(c.hx, c.hy + 14, 2.6, 3.6, 'gold', out=False)

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 3, hy - 22), (hx + 3, hy + 26), 'shaft1', 2)
        a.poly([(hx + 3, hy + 26), (hx + 7, hy + 16), (hx - 1, hy + 16)], 'blade2')

    c = humanoid(a, 'plate', 'skin', leg='cape', arm='plate', hand='skin', w=13, legh=15, th=22, hr=(10, 9.4), pre=pre,
                 post=post, weapon=weapon, pk=.8)
    spark(a, 'blade1', c.near[0] + 12, c.near[1])
    return a.done()


def rain_crown_gatekeeper(clip, n):
    a = R.Art('rain_crown_gatekeeper', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # sluice-wheel on the back and moss on the shoulders
        a.e(c.hx - 14, c.hy - 12, 11, 11, 'iron')
        a.e(c.hx - 14, c.hy - 12, 4, 4, 'stone')
        for k in range(6):
            ang = k * 1.047 + c.T['n'] * .1
            a.c((c.hx - 14, c.hy - 12), (c.hx - 14 + math.cos(ang) * 11, c.hy - 12 + math.sin(ang) * 11), 1.4, 1.4, 'iron')

    def post(c):
        a.band([(c.hx - 11, c.hy + 4), (c.hx + 11, c.hy + 4), (c.hx + 10, c.hy + 12), (c.hx, c.hy + 15), (c.hx - 10, c.hy + 12)], 'stone')
        a.e(c.hx - 4, c.hy + 14, 3.4, 2.4, 'moss', out=False)

    def weapon(c):
        hx, hy = c.near
        a.band([(hx, hy - 12), (hx + 16, hy - 12), (hx + 16, hy + 14), (hx, hy + 14)], 'iron')
        for k in range(3):
            a.line((hx + 2, hy - 8 + k * 8), (hx + 14, hy - 8 + k * 8), 'iron0', 1)
        for k in range(2):
            a.c((hx + 4 + k * 8, hy - 12), (hx + 4 + k * 8, hy - 21), 1.6, 1, 'water')

    c = humanoid(a, 'stone', 'skin', leg='stone', arm='stone', hand='iron', w=17, legh=15, th=24, hr=(13, 10.4), pre=pre,
                 post=post, weapon=weapon, pk=.8, armw=5, handr=4.4, ox=-6)
    spark(a, 'water3', c.near[0] + 16, c.near[1])
    return a.done()


def rain_crown_sibyl(clip, n):
    T = R.timing(clip, n)
    a = R.Art('rain_crown_sibyl', clip, n, sy=1 - T['fall'] * .5)
    hov = 7 + T['bob'] * 1.1
    sw = T['sw']

    def pre(c):
        a.c((c.hx - 6, c.hy + 4), (c.hx - 14 + sw * 2, c.hy - 14), 4.4, 2.4, 'hair')
        # a rain cloud over the head with raindrops falling beside her
        for k, (dx, dy, r) in enumerate(((-9, 17, 6), (0, 20, 7.4), (9, 17, 6))):
            a.e(c.hx + dx, c.hy + dy, r, r * .8, 'cloud')
        for k in range(3):
            y = c.hy + 12 - ((n * 3 + k * 7) % 22)
            a.e(c.hx - 12 + k * 12, y, 1.5, 2.6, 'drop', out=False)

    def weapon(c):
        hx, hy = c.near
        a.poly([(hx + 1, hy + 12), (hx + 8, hy + 6), (hx + 5, hy + 1), (hx + 11, hy - 6), (hx + 2, hy), (hx + 5, hy + 5)], 'bolt1')

    c = humanoid(a, 'robe', 'skin', w=12, legh=hov, th=22, hr=(9.6, 9.6), robe=True, hem='drop', pre=pre, weapon=weapon)
    spark(a, 'bolt1', c.near[0] + 12, c.near[1])
    return a.done()


def rain_crown_sovereign(clip, n):
    a = R.Art('rain_crown_sovereign', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        tendrils(a, c.x, c.y - 14, 5, 7, 34, 'water', r0=3.4, sway=4)

    def post(c):
        # a tall crown of gold points with a red gem
        a.band([(c.x - 17, c.y + 15), (c.x + 17, c.y + 15), (c.x + 17, c.y + 22), (c.x - 17, c.y + 22)], 'crown')
        for k in range(5):
            a.poly([(c.x - 17 + k * 8.5, c.y + 21), (c.x - 13 + k * 8.5, c.y + 33 + (k == 2) * 5), (c.x - 8.5 + k * 8.5, c.y + 21)], 'crown2')
        a.e(c.x, c.y + 19, 2.8, 2.8, 'gem')

    c = floater(a, 'body', R=(20, 17), cy=38, pre=pre, post=post, eye=6, iris='iris', shadow='shadow')
    spark(a, 'water3', c.x + 26, c.y)
    return a.done()


DRAW = dict(rain_crown_droplet=rain_crown_droplet, rain_crown_oracle=rain_crown_oracle, rain_crown_guard=rain_crown_guard,
            rain_crown_gatekeeper=rain_crown_gatekeeper, rain_crown_sibyl=rain_crown_sibyl,
            rain_crown_sovereign=rain_crown_sovereign)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/rain-crown-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
