"""Cel-shaded Elder Hollow enemies (zone 30, dungeon) for make_elder_hollow_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged. `python3 scripts/dungeon_cel.py elder_hollow preview [kind...]` writes contact sheets to
test-results/elder-hollow-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, moth, parts, quad, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('elder_thornling', 'elder_moth', 'elder_barkguard', 'elder_gatekeeper', 'elder_matron', 'elder_heart')

PALETTES = {
    'elder_thornling': mk(bark=('#3a2a1c', '#6a4a2c', '#9a7448', '#d0a870'), thorn=('#c8d89a', '#f4fcc8'),
                          leaf=('#1c6a2c', '#3ca83c', '#88e060'), belly=('#a88a58', '#e0c88c'), iris='#ffd02a',
                          blush='#ff9a8a', nose='#a82a2a'),
    'elder_moth': mk(body=('#6a4a24', '#b08850', '#e0c088', '#fff0c8'), wing=('#1c5a3a', '#3a9a58', '#88e088', '#d0ffc0'),
                     wing2=('#8a5a1c', '#d8982c', '#ffd868'), glow=('#c8a01c', '#fff070'), spot=('#2a1c0c', '#ffe060'),
                     iris='#2a1c0c', blush='#ff9a7a', ant=('#4a3a1c', '#8a7444')),
    'elder_barkguard': mk(bark=('#3a2a1c', '#6a4a2c', '#9a7448', '#d0a870'), plate=('#4a3a20', '#8a6a38', '#c8a05a', '#f4d898'),
                          skin=('#7a5a34', '#b88a54', '#e8bc84'), leaf=('#1c6a2c', '#3ca83c', '#88e060'),
                          moss=('#2a6a2a', '#58b048'), iris='#ffd02a', blush='#ff9a7a', mouth=('#2a1208', '#6a2a1c'),
                          shield=('#4a3220', '#8a6238', '#c49058')),
    'elder_gatekeeper': mk(bark=('#2a1c14', '#5a3c26', '#8a6240', '#c09a68'), wood=('#3a2a1c', '#7a5634', '#b88a56'),
                           skin=('#6a4a2c', '#a07844', '#d8a868'), leaf=('#1c6a2c', '#3ca83c', '#88e060'),
                           glow=('#c88a1c', '#ffe060'), iris='#ffe060', blush='#ff9a6a', mouth=('#1c0c08', '#7a2a1c'),
                           iron=('#4a4a58', '#8a8a9c', '#c8c8d8')),
    'elder_matron': mk(robe=('#4a1c5a', '#8a3a98', '#c870c8', '#f4b0f0'), skin=('#c8a0a0', '#f0c8c0', '#ffe8e0'),
                       petal=('#c83a88', '#ff7ab8', '#ffc0dc', '#fff0f4'), pollen=('#c8a01c', '#fff070'),
                       leaf=('#1c6a2c', '#3ca83c', '#88e060'), iris='#7a2ac8', blush='#ff8aa8',
                       mouth=('#4a1028', '#d83a68'), pod=('#2a6a2c', '#58c048', '#b0f070')),
    'elder_heart': mk(wood=('#3a1c14', '#7a3a2c', '#b8604c', '#f08a70'), root=('#2a1c14', '#5a3c26', '#8a6240'),
                      core=('#c8381c', '#ff6a3a', '#ffb868', '#fff0b0'), leaf=('#1c6a2c', '#3ca83c', '#88e060'),
                      iris='#ffe060', blush='#ff9a8a', mouth=('#2a0c0c', '#8a2a2a'), shadow=('#3a2a1c', '#6a4a2c')),
}
R.PALETTES.update(PALETTES)


def elder_thornling(clip, n):
    a = R.Art('elder_thornling', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-20, c.cy + 3), (-30, c.cy + 9 + c.wav * .6), 3.6, 1.2, 'bark')
        for k in range(3):
            a.poly([(-26 - k * 2, c.cy + 7 + k), (-28 - k * 2, c.cy + 13 + k), (-23 - k * 2, c.cy + 8 + k)], 'thorn1', out=False)

    def pre(c):
        for k in range(6):
            x = -16 + k * 6
            a.poly([(x - 2, c.cy + 9 + (k % 2)), (x + 1, c.cy + 18 + (k % 2) * 2), (x + 3, c.cy + 9 + (k % 2))], 'thorn1')
        for k in range(2):
            a.e(-6 + k * 10, c.cy + 10, 3.6, 2.4, 'leaf')

    c = quad(a, 'bark', 'belly', L=21, Hh=9.6, base=13, hr=(10.4, 8.8), hdx=20, hdy=7, tail=tail, pre=pre, k=1.05,
             ox=-2, nose='nose')
    spark(a, 'thorn1', c.hx + 16, c.hy)
    return a.done()


def elder_moth(clip, n):
    a = R.Art('elder_moth', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    c = moth(a, 'body', 'wing', 'wing2', spot='spot', R=(8, 12), cy=36, glow='glow')
    spark(a, 'glow1', c.x + 24, c.y + 6)
    return a.done()


def elder_barkguard(clip, n):
    a = R.Art('elder_barkguard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a round bark shield on the far arm
        a.e(c.far[0] - 4, c.far[1] + 3, 11, 13, 'shield')
        a.e(c.far[0] - 4, c.far[1] + 3, 5, 6, 'plate')
        for k in range(3):
            a.line((c.far[0] - 4 + (k - 1) * 4, c.far[1] - 6), (c.far[0] - 4 + (k - 1) * 4, c.far[1] + 11), 'shield0', 1)

    def post(c):
        # leaf-crested bark helm
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 10, c.hy + 12), (c.hx, c.hy + 15), (c.hx - 10, c.hy + 12)], 'plate')
        for k, lx in enumerate((-6, 0, 6)):
            a.e(c.hx + lx, c.hy + 17 + (k == 1) * 3, 2.6, 5, 'leaf', ang=(k - 1) * .5)

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 1, hy - 4), (hx + 4, hy + 18), 2.6, 4.6, 'bark')
        a.e(hx + 5, hy + 20, 6, 5, 'bark')
        a.dot(hx + 3, hy + 22, 'moss1', 2)

    c = humanoid(a, 'plate', 'skin', leg='bark', arm='bark', hand='skin', w=14, legh=15, th=22, hr=(10.4, 9), pre=pre,
                 post=post, weapon=weapon, pk=.86, armw=4)
    spark(a, 'plate2', c.near[0] + 14, c.near[1])
    return a.done()


def elder_gatekeeper(clip, n):
    a = R.Art('elder_gatekeeper', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # crown of branches and a gnarled knot of a nose
        for k, s in enumerate((-1, 1)):
            a.c((c.hx + s * 7, c.hy + 7), (c.hx + s * 13, c.hy + 17), 3.2, 2, 'wood')
            a.c((c.hx + s * 13, c.hy + 17), (c.hx + s * 10, c.hy + 25), 2, 1, 'wood')
            a.e(c.hx + s * 16, c.hy + 19, 3.4, 5, 'leaf', ang=s * -.6)

    def post(c):
        a.e(c.hx + 6, c.hy - 2, 3, 3, 'skin', out=True)
        a.e(c.hx - 7, c.hy + 7, 3.6, 3.6, 'wood', out=False)

    def weapon(c):
        hx, hy = c.near
        # a barred wooden gate slab held like a ram
        a.band([(hx + 1, hy - 10), (hx + 15, hy - 10), (hx + 15, hy + 20), (hx + 1, hy + 20)], 'wood')
        for k in range(3):
            a.line((hx + 3 + k * 5, hy - 8), (hx + 3 + k * 5, hy + 18), 'bark0', 1)
        a.e(hx + 8, hy + 5, 3, 3, 'iron')

    c = humanoid(a, 'bark', 'bark', leg='wood', arm='wood', hand='skin', w=17, legh=15, th=24, hr=(13, 11), pre=pre,
                 post=post, weapon=weapon, pk=.8, armw=5, handr=4.4, ox=-6)
    a.e(0, 38, 4, 5, 'glow', out=False)
    spark(a, 'glow1', c.near[0] + 16, c.near[1])
    return a.done()


def elder_matron(clip, n):
    T = R.timing(clip, n)
    a = R.Art('elder_matron', clip, n, sy=1 - T['fall'] * .5)
    sw = T['sw']

    def pre(c):
        # a huge flower collar behind the head
        for k in range(10):
            ang = k * 6.283 / 10
            a.e(c.hx + math.cos(ang) * 13, c.hy + 2 + math.sin(ang) * 12, 4.8, 7, 'petal', ang=ang + 1.57)
        for k in range(3):
            a.e(c.hx - 14 + k * 14 + sw * (k - 1), c.hy - 10 - k % 2 * 6 + n % 3, 1.8, 1.8, 'pollen', out=False)

    def weapon(c):
        hx, hy = c.near
        a.e(hx + 4, hy + 5, 5.4, 6.4, 'pod')
        a.dot(hx + 3, hy + 8, 'pod2', 2)

    c = humanoid(a, 'robe', 'skin', w=12, legh=3, th=26, hr=(9.6, 9.6), robe=True, hem='petal', pre=pre, weapon=weapon,
                 pk=.88)
    a.e(c.hx, c.hy + 4, 4.6, 3, 'petal', out=False)
    spark(a, 'pollen1', c.near[0] + 12, c.near[1] + 4)
    return a.done()


def elder_heart(clip, n):
    T = R.timing(clip, n)
    a = R.Art('elder_heart', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk = .88
    a.lift = fall * 6
    beat = 1 + .05 * math.sin(n * math.pi / 3) if clip == 'idle' else 1
    x = strike * 5 - wind * 3
    y = 42 + bob * 1.2 - fall * 28
    tendrils(a, x, y - 12, 6, 7.4, 34, 'root', r0=3.4, sway=4)
    a.e(x - 9, y + 6, 14 * beat, 13 * beat, 'wood')
    a.e(x + 9, y + 6, 14 * beat, 13 * beat, 'wood')
    a.band([(x - 22, y + 2), (x + 22, y + 2), (x + 2, y - 26), (x - 2, y - 26)], 'wood')
    a.e(x, y + 4, 10, 9, 'core', out=False)
    a.e(x - 12, y + 12, 4, 2.2, 'wood', out=False)
    a.eye(x - 4, y + 4, 5.4, iris='iris', look=(.5, .1))
    a.eye(x + 8, y + 4, 4.8, iris='iris', look=(.9, .1))
    a.dot(x - 12, y - 4, 'blush', 3)
    a.e(x + 2, y - 8, 4, 1.5 + max(wind * .4, strike) * 3, 'mouth')
    for k in range(3):
        a.e(x - 14 + k * 14, y + 17 + (k % 2) * 3 + sw * .5, 3, 5, 'leaf', ang=(k - 1) * .6)
    spark(a, 'core2', x + 26, y)
    return a.done()


DRAW = dict(elder_thornling=elder_thornling, elder_moth=elder_moth, elder_barkguard=elder_barkguard,
            elder_gatekeeper=elder_gatekeeper, elder_matron=elder_matron, elder_heart=elder_heart)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/elder-hollow-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
