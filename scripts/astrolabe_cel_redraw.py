"""Cel-shaded Sunken Astrolabe enemies (zone 34, dungeon) for make_astrolabe_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py astrolabe preview [kind...]` writes contact sheets to
test-results/astrolabe-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, parts, quad, spark, tendrils
from cel_zone_common import ROOT, diamond, gear_points, mku as mk, preview, star

KINDS = ('astro_gearling', 'astro_starling', 'astro_sentinel', 'astro_warden', 'astro_navigator', 'astro_axis')

PALETTES = {
    'astro_gearling': mk(brass=('#6a4a14', '#b8842c', '#f0c050', '#fff0a0'), cog=('#4a3a1c', '#8a6a34', '#c8a058'),
                         iris='#2a3a8a', blush='#ff9a8a', glow=('#5af0d8', '#d0fff4'), leg=('#4a3a1c', '#8a6a34', '#c8a058'),
                         mouth=('#2a1208', '#7a3a1c'), shadow=('#3a2a1c', '#6a4a2c')),
    'astro_starling': mk(star=('#a8741a', '#f0c030', '#ffe878', '#fffcd0'), trail=('#2a3a9a', '#5a78e8', '#a8c0ff'),
                         iris='#2a1c4a', blush='#ff8a8a', mouth=('#4a1c1c', '#c8483a'), glow=('#fff8c8', '#ffffff')),
    'astro_sentinel': mk(brass=('#6a4a14', '#b8842c', '#f0c050', '#fff0a0'), steel=('#3a4a6a', '#6a84b0', '#a8c4e8', '#e0f0ff'),
                         skin=('#8a6a4a', '#c8a070', '#f0d0a0'), glow=('#5af0d8', '#d0fff4'), iris='#2ae8d0',
                         blush='#ff9a8a', mouth=('#2a1208', '#7a3a1c'), ring=('#8a6a1c', '#f0c840', '#fff4a8')),
    'astro_warden': mk(plate=('#1c3a78', '#3a68c0', '#78a8f0', '#d0e4ff'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                       skin=('#d0a888', '#f4ccac', '#ffe8d0'), cloth=('#1c2a58', '#3a4a98'), iris='#3a88f0',
                       blush='#ff9a8a', mouth=('#4a1028', '#d83a68'), glow=('#fff0a0', '#ffffff'),
                       blade=('#8a96b0', '#d0dcf0', '#ffffff')),
    'astro_navigator': mk(coat=('#1c2a58', '#3a58a8', '#6a90e0', '#b0ccff'), skin=('#d8b090', '#f8d4b0', '#ffecd0'),
                          brass=('#6a4a14', '#b8842c', '#f0c050', '#fff0a0'), hat=('#3a2a1c', '#7a5a34', '#b88a56'),
                          glass=('#58a8d8', '#b0e8ff', '#ffffff'), iris='#2a5ac8', blush='#ff9a8a',
                          mouth=('#4a1028', '#d83a68'), beard=('#8a8a9c', '#d8d8e8', '#f8f8ff')),
    'astro_axis': mk(ring=('#6a4a14', '#b8842c', '#f0c050', '#fff0a0'), core=('#1c2a78', '#3a58d8', '#78a8ff', '#d0e4ff'),
                     iris='#fff0a0', blush='#ff9a8a', mouth=('#0c1438', '#3a4a98'), star=('#fff8c8', '#ffffff'),
                     ring2=('#3a4a6a', '#6a84b0', '#a8c4e8', '#e0f0ff'), shadow=('#2a2a4a', '#4a4a7a')),
}
R.PALETTES.update(PALETTES)


def astro_gearling(clip, n):
    a = R.Art('astro_gearling', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk = .92
    a.lift = fall * 5
    cy = 28 + bob * .6 - fall * 12
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 7, cy - 10), (s * 8, 4 + up), 2.6, 2.2, 'leg')
        a.e(s * 10 + 2, 2.6 + up, 4.4, 2, 'cog')
    spin = n * .3 * (1 if clip != 'die' else 0)
    pts = gear_points(0, cy, 15, 9, spin)
    a.poly(pts, 'brass1')
    a.e(0, cy, 14, 14, 'brass')
    a.e(-4, cy + 5, 7, 3, 'brass', out=False)
    a.e(4, cy - 4, 5, 5, 'cog')
    a.eye(-2, cy + 2, 5, iris='iris', look=(.5, .1))
    a.eye(8, cy + 2, 4.4, iris='iris', look=(.9, .1))
    a.dot(-10, cy - 4, 'blush', 3)
    a.e(3, cy - 9, 3.6, 1.2 + max(wind * .4, strike) * 2.4, 'mouth')
    # a small second cog on the back and a wind-up key
    a.poly(gear_points(-17, cy + 6, 5, 6, -spin * 2), 'cog1')
    a.e(-17, cy + 6, 2, 2, 'brass', out=False)
    spark(a, 'glow1', 22 + strike * 4, cy)
    return a.done()


def astro_starling(clip, n):
    a = R.Art('astro_starling', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk = .9
    a.lift = fall * 6
    x = strike * 6 - wind * 4
    y = 40 + bob * 1.4 - fall * 28
    # a blue comet trail behind the fallen star
    for k in range(4):
        a.e(x - 12 - k * 6 + sw, y + 4 - k * 4.4, 8 - k * 1.6, 5 - k * .9, 'trail')
    # five-point star body
    pts = []
    for k in range(10):
        ang = math.pi / 2 + k * math.pi / 5 + n * .04
        r = 20 if k % 2 == 0 else 11
        pts.append((x + math.cos(ang) * r, y + math.sin(ang) * r))
    a.poly(pts, 'star1')
    a.e(x, y, 12, 12, 'star')
    a.e(x - 4, y + 5, 6, 3, 'star', out=False)
    a.eye(x - 2, y + 1, 4.6, iris='iris', look=(.6, .1))
    a.eye(x + 7, y + 1, 4, iris='iris', look=(.9, .1))
    a.dot(x - 9, y - 4, 'blush', 3)
    a.e(x + 3, y - 7, 3.4, 1.2 + max(wind * .4, strike) * 2.4, 'mouth')
    spark(a, 'glow1', x + 24, y)
    return a.done()


def astro_sentinel(clip, n):
    T = R.timing(clip, n)
    a = R.Art('astro_sentinel', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        # a brass orbit ring behind the head, a planet bead sliding round it
        a.e(c.hx - 1, c.hy + 4, 16, 16, 'ring')
        a.e(c.hx - 1, c.hy + 4, 13, 13, 'steel', out=False)
        ang = c.T['n'] * .8
        a.e(c.hx - 1 + math.cos(ang) * 14.5, c.hy + 4 + math.sin(ang) * 14.5, 3, 3, 'glow')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 2, hy - 8), (hx + 3, hy + 18), 'brass1', 2)
        a.e(hx + 3, hy + 21, 6, 6, 'ring')
        a.e(hx + 3, hy + 21, 3, 3, 'glow')

    c = humanoid(a, 'steel', 'skin', leg='brass', arm='brass', hand='steel', w=13, legh=15, th=22, hr=(10, 9.4), pre=pre,
                 weapon=weapon, pk=.84)
    a.e(0, 33, 4.4, 4.4, 'glow', out=False)
    spark(a, 'glow1', c.near[0] + 14, c.near[1])
    return a.done()


def astro_warden(clip, n):
    a = R.Art('astro_warden', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a round meridian shield with a gold cross
        fx, fy = c.far[0] - 4, c.far[1] + 3
        a.e(fx, fy, 12, 13, 'gold')
        a.e(fx, fy, 9, 10, 'plate')
        a.line((fx, fy - 8), (fx, fy + 8), 'gold1', 1)
        a.line((fx - 7, fy), (fx + 7, fy), 'gold1', 1)
        a.poly([(c.hx - 8, c.hy + 3), (c.hx - 20, c.hy - 8 - c.T['sw'] * 2), (c.hx - 8, c.hy - 6)], 'cloth1')

    def post(c):
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 11, c.hy + 11), (c.hx, c.hy + 15), (c.hx - 11, c.hy + 11)], 'plate')
        a.poly([(c.hx - 2, c.hy + 14), (c.hx + 1, c.hy + 25), (c.hx + 4, c.hy + 14)], 'gold1')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 3, hy - 6), (hx + 4, hy + 28), 'blade1', 2)
        a.poly([(hx + 4, hy + 28), (hx + 7, hy + 20), (hx + 1, hy + 20)], 'blade2')
        a.e(hx, hy + 3, 3.6, 1.6, 'gold', out=False)

    c = humanoid(a, 'plate', 'skin', leg='cloth', arm='plate', hand='skin', w=14, legh=15, th=23, hr=(10.4, 9.4),
                 pre=pre, post=post, weapon=weapon, pk=.8, armw=4)
    spark(a, 'glow1', c.near[0] + 14, c.near[1])
    return a.done()


def astro_navigator(clip, n):
    T = R.timing(clip, n)
    a = R.Art('astro_navigator', clip, n, sy=1 - T['fall'] * .5)

    def post(c):
        # captain's hat and a long grey beard
        a.e(c.hx, c.hy + 9, 15, 3.6, 'hat')
        a.e(c.hx, c.hy + 14, 9.6, 6, 'hat')
        a.e(c.hx, c.hy + 11, 4, 2, 'brass', out=False)
        a.c((c.hx + 1, c.hy - 6), (c.hx + 2 + c.T['sw'], c.hy - 16), 5.6, 2, 'beard')

    def weapon(c):
        hx, hy = c.near
        # a brass spyglass raised to the eye, lens glinting
        a.c((hx, hy), (hx + 10, hy + 12), 2.8, 3.6, 'brass')
        a.e(hx + 11, hy + 13, 3.4, 3.4, 'glass')

    c = humanoid(a, 'coat', 'skin', leg='coat', arm='coat', hand='skin', w=13, legh=15, th=22, hr=(10, 9.6), post=post,
                 weapon=weapon, pk=.84)
    a.band([(-9, 18), (9, 18), (9, 22), (-9, 22)], 'brass')
    spark(a, 'glass1', c.near[0] + 14, c.near[1] + 10)
    return a.done()


def astro_axis(clip, n):
    a = R.Art('astro_axis', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    spin = n * .35

    def pre(c):
        # tilted armillary rings turning around the core
        for k, (rx, ry, ang, g) in enumerate(((30, 12, .0, 'ring'), (24, 25, 1.1, 'ring2'), (28, 20, -.7, 'ring'))):
            a.e(c.x, c.y, rx, ry, g, ang=ang + math.sin(spin + k) * .12, out=True)
            a.e(c.x, c.y, rx - 3, ry - 3, 'core', ang=ang + math.sin(spin + k) * .12, out=False)

    def post(c):
        for k in range(4):
            ang = spin + k * 1.57
            star(a, c.x + math.cos(ang) * 29, c.y + math.sin(ang) * 15, 3, 'star0')

    c = floater(a, 'core', R=(15, 15), cy=44, pre=pre, post=post, eye=5.6, shadow='shadow', pk=.86, hover=5)
    spark(a, 'star1', c.x + 30, c.y)
    return a.done()


DRAW = dict(astro_gearling=astro_gearling, astro_starling=astro_starling, astro_sentinel=astro_sentinel,
            astro_warden=astro_warden, astro_navigator=astro_navigator, astro_axis=astro_axis)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/astrolabe-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
