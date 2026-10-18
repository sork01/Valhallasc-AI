"""Cel-shaded Solar Crucible enemies (zone 37, dungeon) for make_solar_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged (solar_cinder borrows the heart's art). `python3 scripts/dungeon_cel.py solar preview [kind...]` writes contact
sheets to test-results/solar-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, moth, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('solar_emberling', 'solar_sunmoth', 'solar_crucible_guard', 'solar_ashwarden', 'solar_heliomancer', 'solar_heart')

PALETTES = {
    'solar_emberling': mk(body=('#7a1c0c', '#c8481c', '#ff8a2a', '#ffd068'), flame=('#e8341c', '#ff8a28', '#ffd44a', '#fff6b0'),
                          skin=('#d8602a', '#ff9a40', '#ffd078'), iris='#2a1c0c', blush='#ffb08a',
                          mouth=('#3a0c0c', '#c8381c'), cinder=('#3a2a28', '#6a4a44')),
    'solar_sunmoth': mk(body=('#7a3a0c', '#c8741c', '#ffb43a', '#ffe898'), wing=('#e8341c', '#ff8a28', '#ffd44a', '#fff6b0'),
                        wing2=('#a8281c', '#e8601c', '#ffa83a'), spot=('#fff6b0', '#ffffff'), glow=('#e8a01c', '#fff070'),
                        iris='#2a1c0c', blush='#ff8a6a', ant=('#5a3a1c', '#b88a3c')),
    'solar_crucible_guard': mk(plate=('#3a2a28', '#7a5a50', '#b8907c', '#e8c8b0'), molten=('#c8381c', '#ff8a2a', '#ffd068', '#fff6b0'),
                               skin=('#d0a888', '#f4ccac', '#ffe8d0'), iron=('#2a2a34', '#5a5a6e', '#9a9ab0'),
                               iris='#c8381c', blush='#ff9a8a', mouth=('#4a1028', '#d83a68'), leg=('#2a2024', '#5a4048')),
    'solar_ashwarden': mk(robe=('#2a2a34', '#585868', '#8e8ea0', '#cacadc'), skin=('#8a8a98', '#c0c0d0', '#e8e8f4'),
                          ember=('#c8381c', '#ff8a2a', '#ffd068', '#fff6b0'), blade=('#5a5a6e', '#9a9ab0', '#dcdcee'),
                          iris='#ff6a2a', blush='#ffa08a', mouth=('#1c1424', '#6a3a4a'), ash=('#6a6a7a', '#b8b8c8'),
                          hood=('#1c1c28', '#3e3e50', '#6a6a80')),
    'solar_heliomancer': mk(robe=('#7a1c0c', '#c8481c', '#f08a3a', '#ffd88a'), skin=('#d8a888', '#f8ccac', '#ffe8d0'),
                            gold=('#9c6a1b', '#e3ac38', '#ffe587', '#fff8c8'), sun=('#c8481c', '#ff9a2a', '#ffe068', '#fffcd0'),
                            iris='#c8481c', blush='#ff8a7a', mouth=('#4a1028', '#d83a68'), hair=('#7a3a1c', '#d8741c'),
                            staff=('#4a2a1c', '#8a5a34', '#c08a54')),
    'solar_heart': mk(core=('#c8281c', '#ff6a2a', '#ffc040', '#fff6b0'), bowl=('#2a2a34', '#5a5a6e', '#9a9ab0', '#d0d0e4'),
                      flame=('#e8341c', '#ff8a28', '#ffd44a', '#fff6b0'), iris='#2a1c0c', blush='#ffb08a',
                      mouth=('#3a0c0c', '#c8381c'), shadow=('#3a2a28', '#6a4a44')),
}
R.PALETTES.update(PALETTES)


def flame(a, x, y, h, w, group, sway=0.):
    """A flame tongue: a pointed teardrop standing on (x, y)."""
    a.poly([(x - w, y), (x - w * .8, y + h * .5), (x + sway, y + h), (x + w * .6, y + h * .45), (x + w, y)], group)


def solar_emberling(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solar_emberling', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']

    def post(c):
        for k, (dx, h) in enumerate(((-7, 10), (0, 15), (7, 10))):
            flame(a, c.hx + dx, c.hy + 7, h + (n % 2), 4.4, 'flame' + str(1 + k % 2), sway=sw * 1.5)

    c = humanoid(a, 'body', 'skin', leg='body', arm='body', hand='skin', w=9, legh=11, th=13, hr=(10, 9.4), post=post,
                 pk=.94, handr=3, armw=3)
    a.e(0, 24, 5, 5, 'flame', out=False)
    spark(a, 'flame2', c.near[0] + 10, c.near[1])
    return a.done()


def solar_sunmoth(clip, n):
    a = R.Art('solar_sunmoth', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    c = moth(a, 'body', 'wing', 'wing2', spot='spot', R=(7, 11), cy=38, span=1.15, glow='glow')
    spark(a, 'wing2', c.x + 24, c.y + 6)
    return a.done()


def solar_crucible_guard(clip, n):
    a = R.Art('solar_crucible_guard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        fx, fy = c.far[0] - 4, c.far[1] + 3
        a.e(fx, fy, 11, 12, 'iron')
        a.e(fx, fy + 2, 8, 7, 'molten')

    def post(c):
        # a crucible bowl worn as a helm, bubbling molten metal
        a.band([(c.hx - 12, c.hy + 4), (c.hx + 12, c.hy + 4), (c.hx + 9, c.hy + 14), (c.hx - 9, c.hy + 14)], 'iron')
        a.e(c.hx, c.hy + 15, 9, 3, 'molten')
        for k in range(3):
            a.e(c.hx - 4 + k * 4, c.hy + 18 + (k + n) % 2, 2, 2.4, 'molten', out=False)

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 1, hy - 4), (hx + 4, hy + 18), 2.2, 3, 'iron')
        a.e(hx + 6, hy + 22, 7.4, 6, 'iron')
        a.e(hx + 6, hy + 22, 5, 3.4, 'molten', out=False)

    c = humanoid(a, 'plate', 'skin', leg='leg', arm='plate', hand='iron', w=14, legh=15, th=23, hr=(10.4, 9.4), pre=pre,
                 post=post, weapon=weapon, pk=.8, armw=4)
    spark(a, 'molten2', c.near[0] + 14, c.near[1])
    return a.done()


def solar_ashwarden(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solar_ashwarden', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']

    def pre(c):
        a.band([(c.hx - 11, c.hy + 8), (c.hx + 9, c.hy + 8), (c.hx + 12, c.hy - 28), (c.hx - 14, c.hy - 28)], 'hood')
        for k in range(4):
            a.e(c.hx - 16 + k * 10 + sw, c.hy + 18 - ((n * 3 + k * 5) % 14), 1.5, 1.5, 'ash', out=False)

    def post(c):
        a.e(c.hx - 2, c.hy + 8, 13, 5, 'hood')
        a.e(c.hx, c.hy + 13, 9, 6, 'hood')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 2, hy - 6), (hx + 4, hy + 30), 'blade1', 2)
        a.poly([(hx + 4, hy + 30), (hx + 7, hy + 20), (hx + 1, hy + 20)], 'ember2')
        a.e(hx + 1, hy + 4, 3.4, 1.6, 'ember', out=False)

    c = humanoid(a, 'robe', 'skin', w=13, legh=3, th=28, hr=(9.6, 9.4), robe=True, hem='ash', pre=pre, post=post,
                 weapon=weapon, pk=.8)
    spark(a, 'ember2', c.near[0] + 14, c.near[1] + 8)
    return a.done()


def solar_heliomancer(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solar_heliomancer', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        # a sun disc with rays behind the head
        for k in range(12):
            ang = n * .1 + k * .5236
            a.poly([(c.hx - 1 + math.cos(ang - .13) * 14, c.hy + 4 + math.sin(ang - .13) * 14),
                    (c.hx - 1 + math.cos(ang) * 22, c.hy + 4 + math.sin(ang) * 22),
                    (c.hx - 1 + math.cos(ang + .13) * 14, c.hy + 4 + math.sin(ang + .13) * 14)], 'sun' + str(1 + k % 2))
        a.e(c.hx - 1, c.hy + 4, 15, 15, 'sun')

    def post(c):
        a.e(c.hx - 4, c.hy + 9, 12, 3.4, 'hair')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 2, hy - 8), (hx + 3, hy + 20), 'staff1', 2)
        a.e(hx + 3, hy + 23, 6, 6, 'gold')
        a.e(hx + 3, hy + 23, 3.4, 3.4, 'sun')

    c = humanoid(a, 'robe', 'skin', w=12, legh=3, th=26, hr=(9.6, 9.6), robe=True, hem='gold', pre=pre, post=post,
                 weapon=weapon, pk=.84)
    spark(a, 'sun2', c.near[0] + 14, c.near[1] + 12)
    return a.done()


def solar_heart(clip, n):
    a = R.Art('solar_heart', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        for k, (dx, h) in enumerate(((-12, 14), (-4, 20), (5, 17), (13, 12))):
            flame(a, c.x + dx, c.y + 12, h + (n + k) % 3, 5, 'flame' + str(1 + k % 2), sway=c.T['sw'] * 2)

    def post(c):
        # the crucible bowl the molten heart rests in
        a.band([(c.x - 19, c.y - 9), (c.x + 19, c.y - 9), (c.x + 12, c.y - 24), (c.x - 12, c.y - 24)], 'bowl')
        a.e(c.x, c.y - 9, 19, 3.2, 'bowl')
        a.e(c.x, c.y - 8, 16, 2.2, 'core', out=False)

    c = floater(a, 'core', R=(17, 15), cy=50, pre=pre, post=post, eye=5.6, shadow='shadow', hover=3, pk=.86)
    spark(a, 'flame2', c.x + 26, c.y)
    return a.done()


DRAW = dict(solar_emberling=solar_emberling, solar_sunmoth=solar_sunmoth, solar_crucible_guard=solar_crucible_guard,
            solar_ashwarden=solar_ashwarden, solar_heliomancer=solar_heliomancer, solar_heart=solar_heart)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/solar-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
