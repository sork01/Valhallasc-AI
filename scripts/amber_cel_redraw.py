"""Cel-shaded Amber Archive enemies (zone 38, dungeon) for make_yearwheel_dungeon_sprites.py via dungeon_cel.install.

Same recipe as cairn_cel_redraw.py on the cel_arch.py archetypes. 96x96 frame, foot anchor (48,90), five clips; kind IDs
unchanged (amber_cocoon borrows the sentinel's art). `python3 scripts/dungeon_cel.py amber preview [kind...]` writes
contact sheets to test-results/amber-cel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, moth, parts, spark, tendrils
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('amber_page', 'amber_moth', 'amber_sentinel', 'amber_curator', 'amber_chronicle', 'amber_memory')

PALETTES = {
    'amber_page': mk(paper=('#a8883c', '#e0c070', '#f8e8b0', '#fffae0'), ink=('#2a1c0c', '#5a3a1c'), iris='#2a1c0c',
                     blush='#ff9a7a', mouth=('#3a1208', '#a8442a'), shadow=('#4a3a1c', '#7a5c2c'), seal=('#a8281c', '#e8503a')),
    'amber_moth': mk(body=('#5a3a14', '#a87030', '#e0a860', '#ffe0a0'), wing=('#a8681c', '#e8a02c', '#ffd868', '#fff4b0'),
                     wing2=('#7a4a14', '#c88a24', '#f0c050'), spot=('#2a1c0c', '#5a3a1c'), glow=('#d8a01c', '#fff070'),
                     iris='#2a1c0c', blush='#ff8a6a', ant=('#4a3a1c', '#9a7a3c')),
    'amber_sentinel': mk(amber=('#7a3a0c', '#d8841c', '#ffc040', '#fff0a0'), plate=('#4a3a2a', '#8a7054', '#c8a882', '#f0dcc0'),
                         skin=('#d0a888', '#f4ccac', '#ffe8d0'), tome=('#5a1c1c', '#a8382c', '#e8704c', '#ffb090'),
                         iris='#d8841c', blush='#ff9a8a', mouth=('#4a1028', '#d83a68'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                         blade=('#8a96b0', '#d0dcf0', '#ffffff')),
    'amber_curator': mk(robe=('#4a2a1c', '#8a5a34', '#c8945c', '#f4d49c'), skin=('#d8b49c', '#f8d8c0', '#ffeedc'),
                        glass=('#58a8d8', '#b0e8ff', '#ffffff'), gold=('#9c6a1b', '#e3ac38', '#ffe587'),
                        hair=('#8a8a9c', '#d8d8e8', '#ffffff'), iris='#5a3a1c', blush='#ff9a8a',
                        mouth=('#4a1028', '#d83a68'), quill=('#e8e0d0', '#ffffff'), ink=('#1c1428', '#4a3a68')),
    'amber_chronicle': mk(cover=('#5a1c1c', '#a8382c', '#e8704c', '#ffb090'), page=('#a8883c', '#e0c070', '#f8e8b0', '#fffae0'),
                          gold=('#9c6a1b', '#e3ac38', '#ffe587'), iris='#2a1c0c', blush='#ff9a7a',
                          mouth=('#3a1208', '#a8442a'), shadow=('#4a3a1c', '#7a5c2c'), ink=('#2a1c0c', '#5a3a1c')),
    'amber_memory': mk(amber=('#7a3a0c', '#d8841c', '#ffc040', '#fff0a0'), glass=('#a8681c', '#f0b848', '#ffe898', '#ffffff'),
                       figure=('#3a2a4a', '#6a5a8a', '#a898cc', '#e0d8f8'), sand=('#c8943c', '#ffe080'),
                       iris='#ffe080', blush='#ff9a7a', mouth=('#2a1c3a', '#6a4a8a'), shadow=('#4a3a1c', '#7a5c2c'),
                       glow=('#fff0a0', '#ffffff')),
}
R.PALETTES.update(PALETTES)


def amber_page(clip, n):
    T = R.timing(clip, n)
    a = R.Art('amber_page', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk, a.ox = .9, -2
    a.lift = fall * 6
    x = strike * 6 - wind * 4
    y = 34 + bob * 1.2 + 3 - fall * 20
    a.e(x * .3, 3, 14, 2.2, 'shadow', out=False)
    # a sheet of parchment with a curled corner, ink lines and a wax seal; the face is on the page
    a.band([(x - 14, y - 20), (x + 14, y - 20), (x + 14 + sw, y + 20), (x - 14 + sw, y + 20)], 'paper')
    a.poly([(x + 14, y - 20), (x + 6, y - 20), (x + 14, y - 12)], 'paper3', out=True)
    for k in range(2):
        a.line((x - 10, y - 12 - k * 3.4), (x + 9, y - 12 - k * 3.4 + (k % 2)), 'ink1', 1)
    a.e(x - 6, y - 14, 2.4, 2.4, 'seal')
    a.eye(x - 4, y + 7, 4.6, iris='iris', look=(.5, .1))
    a.eye(x + 7, y + 7, 4.2, iris='iris', look=(.9, .1))
    a.dot(x - 10, y + 2, 'blush', 3)
    a.e(x + 2, y - 3, 3.6, 1.2 + max(wind * .4, strike) * 2.6, 'mouth')
    spark(a, 'ink1', x + 24, y)
    return a.done()


def amber_moth(clip, n):
    a = R.Art('amber_moth', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        pass

    c = moth(a, 'body', 'wing', 'wing2', spot='spot', R=(7, 11), cy=38, span=1.1, glow='glow')
    # tiny script strokes on the wing
    a.line((c.x - 6, c.y + 14), (c.x + 3, c.y + 12), 'spot1', 1)
    a.line((c.x - 6, c.y + 10), (c.x + 3, c.y + 8), 'spot1', 1)
    spark(a, 'wing3', c.x + 24, c.y + 6)
    return a.done()


def amber_sentinel(clip, n):
    a = R.Art('amber_sentinel', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        # a big tome held up as a shield
        fx, fy = c.far[0] - 4, c.far[1] + 3
        a.band([(fx - 10, fy - 12), (fx + 9, fy - 12), (fx + 9, fy + 12), (fx - 10, fy + 12)], 'tome')
        a.e(fx, fy, 3.4, 3.4, 'gold')
        a.line((fx - 8, fy - 10), (fx - 8, fy + 10), 'gold1', 1)

    def post(c):
        a.band([(c.hx - 11, c.hy + 2), (c.hx + 11, c.hy + 2), (c.hx + 11, c.hy + 11), (c.hx, c.hy + 15), (c.hx - 11, c.hy + 11)], 'plate')
        a.e(c.hx, c.hy + 14, 3, 4.4, 'amber')

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 3, hy - 6), (hx + 3, hy + 26), 'gold1', 2)
        a.poly([(hx + 3, hy + 28), (hx + 7, hy + 18), (hx - 1, hy + 18)], 'amber2')

    c = humanoid(a, 'plate', 'skin', leg='plate', arm='plate', hand='skin', w=14, legh=15, th=23, hr=(10.4, 9.4),
                 pre=pre, post=post, weapon=weapon, pk=.8, armw=4)
    a.e(2, 33, 4.4, 4.4, 'amber', out=False)
    spark(a, 'amber2', c.near[0] + 14, c.near[1])
    return a.done()


def amber_curator(clip, n):
    T = R.timing(clip, n)
    a = R.Art('amber_curator', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        a.e(c.hx - 5, c.hy + 4, 12, 11, 'hair')

    def post(c):
        # round spectacles over the eyes
        for dx in (-4.4, 5.6):
            a.e(c.hx + dx, c.hy + 1.6, 5.8, 6.4, 'glass', out=True) if False else None
            a.line((c.hx + dx - 5, c.hy + 7), (c.hx + dx + 5, c.hy + 7), 'gold1', 1)
        a.line((c.hx + .6, c.hy + 4), (c.hx + 1.2, c.hy + 4), 'gold1', 1)

    def weapon(c):
        hx, hy = c.near
        a.c((hx, hy), (hx + 8, hy + 14), 1.4, 1, 'quill')
        a.poly([(hx + 8, hy + 14), (hx + 13, hy + 22), (hx + 6, hy + 19)], 'quill1')
        a.e(hx + 1, hy - 2, 2.4, 2.4, 'ink')

    c = humanoid(a, 'robe', 'skin', w=13, legh=3, th=28, hr=(10, 9.6), robe=True, hem='gold', pre=pre, post=post,
                 weapon=weapon, pk=.84)
    # key ring at the belt
    a.e(-8, 16, 3.4, 3.4, 'gold')
    a.line((-8, 14), (-8, 8), 'gold1', 1)
    spark(a, 'ink1', c.near[0] + 14, c.near[1] + 10)
    return a.done()


def amber_chronicle(clip, n):
    T = R.timing(clip, n)
    a = R.Art('amber_chronicle', clip, n, sy=1 - T['fall'] * .5)
    f = math.sin(n * math.pi / 3) if clip == 'idle' else math.sin(n * math.pi / 2) if clip == 'walk' else 0
    if clip == 'attack':
        f = (-.4, -.8, -1, .9, 1, .5, .1, 0)[n]

    def pre(c):
        # open pages fanning out left and right, flapping like wings
        for s in (-1, 1):
            a.e(c.x + s * 20, c.y + 8 + f * 5, 11, 17, 'page', ang=s * (.35 - f * .22))
            for k in range(3):
                a.line((c.x + s * (12 + k * 5), c.y + 18 + f * 4), (c.x + s * (14 + k * 5), c.y - 6 + f * 3), 'ink1', 1)

    def post(c):
        # spine and a gold clasp across the cover
        a.band([(c.x - 17, c.y + 15), (c.x + 17, c.y + 15), (c.x + 17, c.y + 19), (c.x - 17, c.y + 19)], 'gold')
        a.e(c.x, c.y - 17, 4, 3, 'gold')

    c = floater(a, 'cover', R=(19, 19), cy=44, pre=pre, post=post, eye=6, shadow='shadow', hover=3, pk=.86)
    spark(a, 'ink1', c.x + 28, c.y)
    return a.done()


def amber_memory(clip, n):
    a = R.Art('amber_memory', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    sw = R.timing(clip, n)['sw']

    def pre(c):
        for k in range(4):
            a.e(c.x - 9 + k * 6 + sw * .5, c.y - 25 - ((n * 2 + k * 3) % 6), 1.8, 1.8, 'sand', out=False)

    def post(c):
        # glass highlight, a shadowed figure low in the amber and an hourglass crown
        a.e(c.x - 11, c.y + 14, 6, 3, 'glass', out=False)
        a.e(c.x + 1, c.y - 13, 9, 5.4, 'figure', out=False)
        a.poly([(c.x - 6, c.y + 27), (c.x + 6, c.y + 27), (c.x, c.y + 21)], 'sand0')
        a.poly([(c.x - 6, c.y + 15), (c.x + 6, c.y + 15), (c.x, c.y + 21)], 'sand1')

    c = floater(a, 'amber', R=(20, 21), cy=44, pre=pre, post=post, eye=5.8, shadow='shadow', hover=3, pk=.86, mouth=None)
    spark(a, 'glow1', c.x + 26, c.y)
    return a.done()


DRAW = dict(amber_page=amber_page, amber_moth=amber_moth, amber_sentinel=amber_sentinel, amber_curator=amber_curator,
            amber_chronicle=amber_chronicle, amber_memory=amber_memory)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/amber-cel-preview')
    print('ok')


if __name__ == '__main__':
    main()
