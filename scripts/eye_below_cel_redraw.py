"""Cel-shaded Eye Below enemies (zone 29, dungeon) for make_eye_below_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes: hard colour bands, one dark outline per part, big
glossy eyes, chibi proportions. 96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged.
`python3 scripts/dungeon_cel.py eye_below preview [kind...]` writes contact sheets to test-results/eye-below-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, parts, quad, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('eye_drifter', 'eye_lurker', 'eye_adept', 'eye_lenswarden', 'eye_undertide', 'eye_unblinking')

PALETTES = {
    'eye_drifter': mk(body=('#1c5a78', '#3a9ab8', '#7ad8e0', '#d0fcf4'), fin=('#2a7aa0', '#7ae0e8', '#c8fff8'),
                      glow=('#40e8c8', '#b0fff0'), iris='#f0d078', blush='#ff9ac0', shadow=('#14384c', '#245a74')),
    'eye_lurker': mk(skin=('#3a2a6a', '#6a58b0', '#a890e0', '#e0d0ff'), belly=('#c8b8f0', '#f0e8ff'),
                     glass=('#6ac8f0', '#c0f0ff', '#ffffff'), iris='#ffe070', blush='#ff9ac8', mouth=('#2a0c3a', '#a8386a'),
                     fin=('#4a3a8a', '#8a70d0')),
    'eye_adept': mk(robe=('#1c5a68', '#38a0a8', '#78dcd8', '#d0fff4'), skin=('#a8d8d8', '#dcf8f4', '#ffffff'),
                    veil=('#58b8c8', '#a8eef0', '#e8ffff'), glow=('#40e8d8', '#c0fff4'), iris='#2a8ac8', blush='#ffa0c0',
                    mouth=('#1c3a4a', '#4a8898'), gold=('#a8741a', '#f4c448', '#fff0a0')),
    'eye_lenswarden': mk(plate=('#5a4a34', '#a88c5c', '#e0c488', '#fff0c8'), cloth=('#2a3a68', '#4a64a8', '#8aa0e0'),
                         skin=('#c8a080', '#f0c8a0', '#ffe8cc'), lens=('#2a8ab8', '#78dcf8', '#d8fcff'),
                         iris='#2a8ac8', blush='#ffa090', rim=('#6a4a1c', '#d8a444', '#fff0a0'),
                         mouth=('#3a1a1c', '#8a3a3a')),
    'eye_undertide': mk(robe=('#1c5a58', '#38a898', '#78e0c8', '#d0fff0'), skin=('#a8d8d0', '#dcf8f0', '#ffffff'),
                        hair=('#1c6a8a', '#3aa8c8', '#8ae8f0'), eyeb=('#2a5a78', '#fff4d0'), iris='#e8b81c',
                        blush='#ffa0b8', mouth=('#1c3a48', '#488898'), wave=('#40e8d0', '#c0fff4'),
                        drop=('#2a98d8', '#9ae8ff')),
    'eye_unblinking': mk(body=('#7a4a1c', '#d8984a', '#fcd488', '#fff4d0'), blade=('#2a8ab8', '#78dcf8', '#d8fcff'),
                         root=('#5a3a1c', '#9a6a34', '#d09a58'), iris='#2a1c3a', ring=('#c86a1c', '#ffb838', '#ffe888'),
                         blush='#ff9a7a', lash=('#4a2a1c', '#8a5a34'), glow=('#fff0a0', '#fffcd8'), shadow=('#4a3a2a', '#7a6244')),
}
R.PALETTES.update(PALETTES)


def eye_drifter(clip, n):
    a = R.Art('eye_drifter', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        tendrils(a, c.x, c.y - 10, 5, 7, 22 + c.y * .3, 'fin', r0=2.6)
        for k in range(4):
            a.e(c.x - 12 + k * 8, c.y + 6, 1.8, 1.8, 'glow', out=False)

    c = floater(a, 'body', R=(19, 15), cy=44, pre=pre, eye=5.6, iris='iris')
    a.e(c.x, c.y + 11, 21, 4, 'fin', out=False)
    spark(a, 'glow1', c.x + 22, c.y)
    return a.done()


def eye_lurker(clip, n):
    a = R.Art('eye_lurker', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-20, c.cy + 2), (-28, c.cy + 7 + c.wav * .6), 5, 2.4, 'skin')
        a.poly([(-27, c.cy + 7 + c.wav * .6), (-35, c.cy + 14 + c.wav), (-34, c.cy), ], 'fin1')

    def pre(c):
        for k in range(4):
            a.poly([(-12 + k * 8, c.cy + 9), (-9 + k * 8, c.cy + 18), (-5 + k * 8, c.cy + 9)], 'fin1', out=False)

    def post(c):
        # glassy jaw: a row of lens teeth under the mouth
        g = max(c.T['wind'] * .5, c.T['strike']) * 3
        for k in range(4):
            a.poly([(c.hx + 1 + k * 3, c.hy - 6 - g), (c.hx + 3 + k * 3, c.hy - 6 - g), (c.hx + 2 + k * 3, c.hy - 11 - g)], 'glass1', out=False)
        # eye stalk
        a.c((c.hx - 4, c.hy + 7), (c.hx - 6, c.hy + 15), 1.4, 1.2, 'skin')
        a.e(c.hx - 6, c.hy + 17, 3.2, 3.2, 'glass')

    c = quad(a, 'skin', 'belly', L=24, Hh=11, base=11, legw=3.4, hr=(12.4, 10), hdx=22, hdy=7, tail=tail, pre=pre,
             post=post, k=1.1, ox=-1, nose=None, blush='blush')
    spark(a, 'glass1', c.hx + 16, c.hy)
    return a.done()


def eye_adept(clip, n):
    a = R.Art('eye_adept', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    hov = 7 + R.timing(clip, n)['bob'] * 1.1

    def pre(c):
        # a long veil hangs behind the head and shoulders
        a.band([(c.hx - 11, c.hy + 8), (c.hx + 8, c.hy + 8), (c.hx + 12, c.hy - 26), (c.hx - 14, c.hy - 26)], 'veil', out=True)

    def post(c):
        for k in range(3):
            diamond(a, c.hx - 5 + k * 5, c.hy + 11 - abs(k - 1) * 1.4, 1.8, 3.6, 'glow0', out=True)

    def weapon(c):
        hx, hy = c.near
        a.e(hx + 3, hy + 6, 6, 6, 'glow', out=False)
        a.e(hx + 3, hy + 6, 3.2, 3.2, 'gold')

    c = humanoid(a, 'robe', 'skin', w=11, legh=hov, th=22, hr=(9.6, 10), robe=True, hem='veil', pre=pre, post=post,
                 weapon=weapon, mouth=None)
    spark(a, 'glow1', c.near[0] + 12, c.near[1])
    return a.done()


def eye_lenswarden(clip, n):
    a = R.Art('eye_lenswarden', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a great round lens shield on the far side, a plume of cloth behind the neck
        a.e(c.far[0] - 4, c.far[1] + 2, 13, 14, 'rim')
        a.e(c.far[0] - 4, c.far[1] + 2, 10, 11, 'lens')
        a.e(c.far[0] - 7, c.far[1] + 6, 4, 3, 'lens', out=False)
        a.poly([(c.hx - 8, c.hy + 3), (c.hx - 20, c.hy - 6 - c.T['sw'] * 2), (c.hx - 8, c.hy - 6)], 'cloth1')

    def post(c):
        # visored helm with a wide brow
        a.band([(c.hx - 11, c.hy + 3), (c.hx + 11, c.hy + 3), (c.hx + 12, c.hy + 14), (c.hx, c.hy + 19), (c.hx - 12, c.hy + 14)], 'plate')
        a.e(c.hx, c.hy + 4, 13, 2.4, 'rim')

    def weapon(c):
        hx, hy = c.near
        a.c((hx, hy - 2), (hx + 5, hy + 22), 2.2, 2.6, 'rim')
        a.e(hx + 6, hy + 26, 7.4, 7.4, 'rim')
        a.e(hx + 6, hy + 26, 5.4, 5.4, 'lens')

    c = humanoid(a, 'plate', 'skin', leg='cloth', arm='plate', hand='skin', w=15, legh=15, th=24, hr=(11, 9.4), pre=pre,
                 post=post, weapon=weapon, pk=.82, handr=4, armw=4.4, mouth=None, eyes=True)
    spark(a, 'lens1', c.near[0] + 14, c.near[1])
    return a.done()


def eye_undertide(clip, n):
    a = R.Art('eye_undertide', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    hov = 8 + R.timing(clip, n)['bob'] * 1.1
    sw = R.timing(clip, n)['sw']

    def pre(c):
        # tide-hair flowing behind
        for k in range(3):
            a.c((c.hx - 5, c.hy + 4 - k * 3), (c.hx - 14 - k * 2 + sw * 2, c.hy - 6 - k * 7), 4.6 - k, 2, 'hair')
        for k in range(4):
            ang = k * 1.57 + sw * .2
            a.e(c.hx + math.cos(ang) * 14, c.hy + 14 + math.sin(ang) * 3, 2, 3, 'drop')

    def post(c):
        # three small eyes across the brow
        for k, ex in enumerate((-5, 1, 7)):
            a.e(c.hx + ex, c.hy + 9, 2.6, 2.6, 'eyeb')
            a.dot(c.hx + ex, c.hy + 9, 'iris', 2)
        a.e(c.hx, c.hy + 15, 5, 2, 'wave', out=False)

    c = humanoid(a, 'robe', 'skin', w=12, legh=hov, th=22, hr=(10, 10), robe=True, hem='wave', pre=pre, post=post)
    spark(a, 'wave1', c.near[0] + 10, c.near[1])
    return a.done()


def eye_unblinking(clip, n):
    T = R.timing(clip, n)
    a = R.Art('eye_unblinking', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        tendrils(a, c.x, c.y - 14, 6, 6, 28, 'root', r0=3.2)
        spin = n * .22
        for k in range(10):
            ang = spin + k * 6.283 / 10
            a.poly([(c.x + math.cos(ang - .16) * 21, c.y + math.sin(ang - .16) * 21),
                    (c.x + math.cos(ang) * 31, c.y + math.sin(ang) * 31),
                    (c.x + math.cos(ang + .16) * 21, c.y + math.sin(ang + .16) * 21)], 'blade' + str(1 + k % 2))
        a.e(c.x, c.y, 23, 23, 'ring')

    c = floater(a, 'body', R=(19, 19), cy=44, pre=pre, eye=7.2, iris='iris', mouth=None, blush=None)
    # lashes
    for k in range(3):
        a.line((c.x - 6 + k * 6, c.y + 19), (c.x - 8 + k * 7, c.y + 24), 'lash1', 1)
    spark(a, 'glow1', c.x + 28, c.y)
    return a.done()


DRAW = dict(eye_drifter=eye_drifter, eye_lurker=eye_lurker, eye_adept=eye_adept, eye_lenswarden=eye_lenswarden,
            eye_undertide=eye_undertide, eye_unblinking=eye_unblinking)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/eye-below-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
