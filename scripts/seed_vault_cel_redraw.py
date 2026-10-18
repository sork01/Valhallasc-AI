"""Cel-shaded Seed Vault enemies (zone 33, dungeon) for make_seed_vault_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged (seed_sprout and seed_treant borrow the seedling's and the guard's art). `python3 scripts/dungeon_cel.py
seed_vault preview [kind...]` writes contact sheets to test-results/seed-vault-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, moth, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('seed_mote', 'seed_amberwing', 'seed_rootguard', 'seed_warden', 'seed_germinator', 'seed_worldseed')

PALETTES = {
    'seed_mote': mk(seed=('#6a4a1c', '#b88a3c', '#e8c070', '#fff0b8'), leaf=('#1c7a2c', '#3cc83c', '#98f070', '#e4ffc0'),
                    stem=('#2a6a1c', '#58a83a'), iris='#2a1c0c', blush='#ff8a7a', mouth=('#3a1208', '#a8442a'),
                    shadow=('#4a3a1c', '#7a5c2c')),
    'seed_amberwing': mk(body=('#5a3a14', '#a87030', '#e0a860', '#ffe0a0'), wing=('#b8601c', '#f09c2c', '#ffd868', '#fff4b0'),
                         wing2=('#8a4a14', '#d88a24', '#ffc850'), spot=('#2a1c0c', '#ffe060'), glow=('#d8a01c', '#fff070'),
                         iris='#2a1c0c', blush='#ff8a6a', ant=('#4a3a1c', '#9a7a3c')),
    'seed_rootguard': mk(root=('#2a1c14', '#5a3c26', '#8a6240', '#c09a68'), plate=('#3a2a1c', '#7a5634', '#b88a56', '#e8bc84'),
                         skin=('#8a6a3c', '#c8984c', '#f0c880'), leaf=('#1c7a2c', '#3cc83c', '#98f070'),
                         glow=('#d8841c', '#ffe060', '#fff4b0'), iris='#ffd02a', blush='#ff8a6a',
                         mouth=('#2a1208', '#7a2a1c')),
    'seed_warden': mk(robe=('#4a3a1c', '#8a7034', '#c8a858', '#f4e098'), skin=('#c8a070', '#f0c898', '#ffe8cc'),
                      ring=('#6a4a1c', '#b8842c', '#e8c060', '#fff0a0'), wood=('#3a2a1c', '#7a5634', '#b88a56'),
                      leaf=('#1c7a2c', '#3cc83c', '#98f070'), iris='#3a7a1c', blush='#ff9a7a',
                      mouth=('#3a1208', '#a8442a'), glow=('#ffe060', '#fff8c8')),
    'seed_germinator': mk(bulb=('#2a6a1c', '#58b83a', '#98f070', '#e4ffc0'), vine=('#1c5a1c', '#3a9a3a', '#78d858'),
                          petal=('#c83a6a', '#ff7a9a', '#ffc0cc', '#fff0f0'), mid=('#c88a1c', '#ffd048'),
                          iris='#2a1c3a', blush='#ff8a9a', mouth=('#4a0c1c', '#c83a5a'), shadow=('#2a4a1c', '#4a7a2c'),
                          tooth='#fffcf0'),
    'seed_worldseed': mk(seed=('#5a3a14', '#a87030', '#e0a860', '#ffe0a0'), crack=('#d8841c', '#ffe060', '#fffcd0'),
                         leaf=('#1c7a2c', '#3cc83c', '#98f070', '#e4ffc0'), iris='#2a1c0c', blush='#ff8a6a',
                         mouth=('#3a1208', '#a8442a'), shadow=('#4a3a1c', '#7a5c2c'), root=('#2a1c14', '#5a3c26', '#8a6240')),
}
R.PALETTES.update(PALETTES)


def seed_mote(clip, n):
    a = R.Art('seed_mote', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    sw = R.timing(clip, n)['sw']

    def pre(c):
        a.c((c.x, c.y + 10), (c.x + 2, c.y + 17), 1.8, 1.4, 'stem')
        a.e(c.x - 4 + sw, c.y + 20, 6, 3.2, 'leaf', ang=.5)
        a.e(c.x + 8 + sw, c.y + 19, 6, 3.2, 'leaf', ang=-.5)

    c = floater(a, 'seed', R=(11, 12), cy=22, pre=pre, eye=4.2, shadow='shadow', hover=1)
    spark(a, 'leaf2', c.x + 17, c.y)
    return a.done()


def seed_amberwing(clip, n):
    a = R.Art('seed_amberwing', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    c = moth(a, 'body', 'wing', 'wing2', spot='spot', R=(7, 11), cy=36, span=1.1, glow='glow')
    spark(a, 'wing3', c.x + 24, c.y + 6)
    return a.done()


def seed_rootguard(clip, n):
    a = R.Art('seed_rootguard', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        a.e(c.far[0] - 4, c.far[1] + 3, 10, 12, 'root')
        for k in range(3):
            a.line((c.far[0] - 4 + (k - 1) * 3, c.far[1] - 6), (c.far[0] - 4 + (k - 1) * 3, c.far[1] + 11), 'root0', 1)

    def post(c):
        for k, lx in enumerate((-6, 0, 6)):
            a.e(c.hx + lx, c.hy + 11 + (k == 1) * 3, 2.6, 5, 'leaf', ang=(k - 1) * .5)
        a.e(c.hx, c.hy + 7, 11, 2.4, 'root', out=False)

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 1, hy - 4), (hx + 4, hy + 16), 3, 5, 'root')
        a.e(hx + 5, hy + 18, 6.4, 5.6, 'root')

    c = humanoid(a, 'plate', 'skin', leg='root', arm='root', hand='skin', w=14, legh=15, th=22, hr=(10.4, 9.2), pre=pre,
                 post=post, weapon=weapon, pk=.86, armw=4)
    a.e(2, 32, 4, 5, 'glow', out=False)
    spark(a, 'glow2', c.near[0] + 14, c.near[1])
    return a.done()


def seed_warden(clip, n):
    T = R.timing(clip, n)
    a = R.Art('seed_warden', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        # tree-ring halo behind the head
        a.e(c.hx - 2, c.hy + 2, 17, 17, 'ring')
        a.e(c.hx - 2, c.hy + 2, 12, 12, 'wood')
        a.e(c.hx - 2, c.hy + 2, 7, 7, 'ring')
        # ringed shield on the far arm
        a.e(c.far[0] - 3, c.far[1] + 2, 9, 9, 'ring')
        a.e(c.far[0] - 3, c.far[1] + 2, 5, 5, 'wood')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 1, hy - 8), (hx + 3, hy + 20), 'wood1', 2)
        a.e(hx + 3, hy + 22, 7, 7, 'ring')
        a.e(hx + 3, hy + 22, 3.4, 3.4, 'glow')

    c = humanoid(a, 'robe', 'skin', w=12, legh=3, th=26, hr=(9.6, 9.6), robe=True, hem='ring', pre=pre, weapon=weapon,
                 pk=.88)
    spark(a, 'glow1', c.near[0] + 14, c.near[1] + 12)
    return a.done()


def seed_germinator(clip, n):
    a = R.Art('seed_germinator', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        tendrils(a, c.x, c.y - 12, 5, 8, 32, 'vine', r0=3.4, sway=4)
        # a flower crown of petals around the bulb top
        for k in range(8):
            ang = 3.14 / 8 * k + .2
            a.e(c.x + math.cos(ang) * 14 - 1, c.y + 10 + math.sin(ang) * 15, 4.6, 7.4, 'petal', ang=ang - 1.57)

    def post(c):
        a.e(c.x + 2, c.y + 14, 4, 4, 'mid')

    c = floater(a, 'bulb', R=(20, 17), cy=38, pre=pre, post=post, eye=6, shadow='shadow')
    a.e(c.x + 6, c.y - 7, 6, 2 + max(c.T['wind'] * .4, c.T['strike']) * 3, 'mouth')
    spark(a, 'petal2', c.x + 26, c.y)
    return a.done()


def seed_worldseed(clip, n):
    a = R.Art('seed_worldseed', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    sw = R.timing(clip, n)['sw']

    def pre(c):
        tendrils(a, c.x, c.y - 18, 6, 6, 32, 'root', r0=3.2, sway=4)

    def post(c):
        # glowing crack and a tiny sprout bursting from the top
        a.line((c.x - 4, c.y + 14), (c.x, c.y + 4), 'crack1', 2)
        a.line((c.x, c.y + 4), (c.x - 5, c.y - 4), 'crack1', 2)
        a.line((c.x - 5, c.y - 4), (c.x - 2, c.y - 12), 'crack2', 1)
        a.c((c.x + 2, c.y + 22), (c.x + 3, c.y + 30), 1.8, 1.4, 'leaf')
        a.e(c.x - 4 + sw, c.y + 33, 6, 3.2, 'leaf', ang=.5)
        a.e(c.x + 10 + sw, c.y + 32, 6, 3.2, 'leaf', ang=-.5)

    c = floater(a, 'seed', R=(19, 22), cy=40, pre=pre, post=post, eye=6, shadow='shadow')
    spark(a, 'crack2', c.x + 25, c.y)
    return a.done()


DRAW = dict(seed_mote=seed_mote, seed_amberwing=seed_amberwing, seed_rootguard=seed_rootguard, seed_warden=seed_warden,
            seed_germinator=seed_germinator, seed_worldseed=seed_worldseed)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/seed-vault-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
