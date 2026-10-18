"""Cel-shaded art of the six boss-mechanic helpers, which used to borrow another kind's sprite (`artFrom`).

The Bound Singer (`choirsinger`, Flooded Cloister), the Reliquary Pearl (`reliquarypearl`, Coral Reliquary), the Worldseed
Seed (`seed_sprout`) and Bloom Treant (`seed_treant`) of the Seed Vault, the Cinder of the Crucible (`solar_cinder`) and
the Amber Cocoon (`amber_cocoon`, Silent Solstice's Amber Archive). Same toolkit as the zone redraws (Art, cel_arch): 96x96
frame, foot anchor (48,90), five clips, hard bands, big glossy eyes. Installed into the dungeon makers with
dungeon_cel.install and into make_cathedral_sprites.py; `scripts/boss_helper_art.py` builds, exports and verifies them
without touching the sprites they used to borrow. `python3 scripts/boss_helper_cel_redraw.py [kind...]` writes contact
sheets to test-results/boss-helper-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import burst, floater, humanoid, parts, spark
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('choirsinger', 'reliquarypearl', 'seed_sprout', 'seed_treant', 'solar_cinder', 'amber_cocoon')

PALETTES = {
    'choirsinger': mk(robe=('#17566a', '#2f93a4', '#6edcd0', '#dcfff4'), skin=('#7fb2c4', '#bfe3ee', '#f0fcff'),
                      hair=('#3b6aa8', '#74a8e0', '#cbe6ff'), chain=('#23252f', '#4d5266', '#8a90ab', '#c7cce0'),
                      mist=('#4f8fa8', '#9fd8e6', '#eefcff'), note=('#2e6f9a', '#9ff2ff'), iris='#2e9fc0', blush='#ff9ab0',
                      mouth=('#5a1c34', '#ff7a98'), wave=('#7fe8ff', '#e6ffff')),
    'reliquarypearl': mk(pearl=('#9a7aa8', '#e2c4dc', '#fbeaf2', '#ffffff'), shell=('#7a4a62', '#c98aa0', '#f0bcc8', '#ffe6e8'),
                         inner=('#d96a9a', '#ff9ec0', '#ffd6e4'), gold=('#8c5d16', '#dba22f', '#ffe382'),
                         sheen=('#8ee8ff', '#ffb0e0', '#fff3a0'), iris='#9a4ab8', blush='#ff8ab4', mouth=('#7a2a4a', '#ff7a9a'),
                         shadow=('#3a2a4a', '#6a4a7a')),
    'seed_sprout': mk(seed=('#6a3c14', '#a8682a', '#dca058', '#ffd890'), root=('#3a2414', '#6a4628', '#a07448'),
                      leaf=('#1c7a2c', '#3cc83c', '#98f070', '#e4ffc0'), crack=('#e8841c', '#ffe060', '#fffcd0'),
                      iris='#3a2a12', blush='#ff8a7a', mouth=('#3a1208', '#a8442a')),
    'seed_treant': mk(bark=('#3a2418', '#6e4a2c', '#a47448', '#dca874'), moss=('#2c5a2b', '#4c8c3a', '#86c755', '#c8ef88'),
                      blossom=('#d8508a', '#ff86b4', '#ffc4d8', '#fff2f6'), heart=('#c8841c', '#ffd048', '#fff4b0'),
                      leaf=('#1c7a2c', '#3cc83c', '#98f070'), iris='#6a9a1c', blush='#ff8a9a', mouth=('#3a1208', '#a8442a')),
    'solar_cinder': mk(coal=('#241a1c', '#44302c', '#6a4a40', '#94705c'), lava=('#a8300c', '#f0701c', '#ffc040', '#fff8c0'),
                       flame=('#e0501c', '#ff9a2c', '#ffd860', '#fffbd0'), ash=('#5a524e', '#948a82'), iris='#ffd860',
                       blush='#ff7a3a', mouth=('#3a0c08', '#ff9a2c'), shadow=('#3a2218', '#6a4430')),
    'amber_cocoon': mk(amber=('#8a4a0c', '#d08a1c', '#f6c24a', '#fff0a8'), deep=('#5a2c08', '#9a5a14'), pupa=('#4a2a1c', '#7a4a2c', '#b07a48'),
                       silk=('#d0c8b8', '#fff6e4'), glow=('#ffb02a', '#fff0a0'), resin=('#a05c10', '#e8a02c', '#ffd878'),
                       iris='#ffd25a', bubble=('#d8a040', '#fff8d0')),
}
R.PALETTES.update(PALETTES)


def note(a, x, y, group='note'):
    """A floating music note."""
    a.e(x, y, 2.4, 1.8, group, ang=.4)
    a.line((x + 2, y + .4), (x + 2, y + 8), group + '0', 1)
    a.line((x + 2, y + 8), (x + 5, y + 6), group + '0', 1)


def choirsinger(clip, n):
    T = R.timing(clip, n)
    a = R.Art('choirsinger', clip, n, sy=1 - T['fall'] * .5)
    wind, strike, sw = T['wind'], T['strike'], T['sw']

    def pre(c):
        a.e(c.hx - 5, c.hy - 2, 12, 13, 'hair')                                   # hair behind the head
        a.e(c.hx - 8, c.hy - 10, 5, 8, 'hair', ang=.2)
        a.e(0, c.top - 2, 13, 4.6, 'chain')                                       # the iron collar
        a.e(0, c.top - 2, 8.4, 2.6, 'robe', out=False)

    def post(c):
        for (hx, hy) in (c.near, c.far):                                           # shackles on both wrists
            a.e(hx, hy, 4.6, 4.6, 'chain', out=True)
            a.e(hx, hy, 2.4, 2.4, 'skin', out=False)
        # a broken chain from the far wrist to a ball on the ground
        fx, fy = c.far
        a.line((fx, fy - 3), (fx - 5, 12), 'chain2', 1)
        a.line((fx - 5, 12), (fx - 10, 5), 'chain2', 1)
        a.e(fx - 11, 4, 5, 4.4, 'chain')
        open_ = max(wind * .4, strike)
        a.e(c.hx + 3, c.hy - 5.4, 2.8 + open_ * 1.2, 1.8 + open_ * 3.6, 'mouth')   # singing
        if clip == 'attack':
            for k in range(3 if n in (3, 4, 5) else 0):
                a.line((c.hx + 11 + k * 5, c.hy - 5 - k * 3), (c.hx + 13 + k * 5, c.hy - 1 + k * 3), 'wave0', 2)
        elif clip == 'idle':
            note(a, c.hx + 14, c.hy + 4 + (n % 3) * 2)
        if clip != 'die':
            a.e(sw * .6, 3, 14, 3, 'mist', out=False)

    humanoid(a, 'robe', 'skin', w=11.5, legh=3, th=25, hr=(9.6, 10), robe=True, hem='mist', pre=pre, post=post, pk=.9,
             blush='blush', mouth=None)
    return a.done()


def reliquarypearl(clip, n):
    a = R.Art('reliquarypearl', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)
    T = a.T
    snap = max(T['wind'], T['strike'])

    def pre(c):                                                                   # the open shell the pearl rests in
        a.e(c.x * .4, c.y - 17, 22, 9, 'shell')
        a.e(c.x * .4, c.y - 15, 17, 5, 'inner', out=False)
        for k in range(5):
            a.line((c.x * .4 - 16 + k * 8, c.y - 22), (c.x * .4 - 12 + k * 6, c.y - 14), 'shell0', 1)

    def post(c):
        a.e(c.x * .4, c.y + 22 + (1 - T['strike']) * (6 + T['wind'] * 6) - T['strike'] * 14, 20, 8, 'shell')   # the lid snaps shut on a slam
        a.e(c.x * .4, c.y + 24 + (1 - T['strike']) * (6 + T['wind'] * 6) - T['strike'] * 14, 13, 3, 'inner', out=False)
        a.poly([(c.x - 11, c.y + 9), (c.x - 4, c.y + 14), (c.x + 3, c.y + 12), (c.x - 5, c.y + 6)], 'sheen0', out=False)   # an oil-slick sheen
        a.poly([(c.x + 6, c.y - 8), (c.x + 12, c.y - 2), (c.x + 14, c.y - 8), (c.x + 9, c.y - 12)], 'sheen1', out=False)
        a.dot(c.x - 9, c.y + 3, 'sheen2', 2)
        a.e(c.x * .4, c.y - 9, 4, 2.6, 'gold')

    c = floater(a, 'pearl', R=(17, 17), cy=36, pre=pre, post=post, eye=5, shadow='shadow', hover=0)
    spark(a, 'sheen1', c.x + 24, c.y)
    return a.done()


def seed_sprout(clip, n):
    T = R.timing(clip, n)
    a = R.Art('seed_sprout', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk, a.ox = .92, -1
    a.lift = fall * 5
    cy = 21 + bob * .7 - fall * 7 - wind * 2
    for s in (-1, 1):                                                              # two root-legs trot along
        up = max(0, s * math.sin(n * math.pi / 2)) * 3.4 if clip == 'walk' else 0
        a.c((s * 5, cy - 6), (s * 7, 3 + up), 2.4, 1.8, 'root')
        a.e(s * 7 + 2, 2 + up, 3.8, 1.8, 'root')
    for s in (-1, 1):
        a.c((s * 12, cy + 2), (s * 17 + (strike * 6 if s > 0 else sw), cy - 4 - wind * 4), 2, 1.6, 'root')
    a.e(0, cy + 8, 14, 17, 'seed')                                                 # the plump seed
    a.e(-4, cy + 14, 7, 9, 'seed', out=False)
    a.line((4, cy + 2), (7, cy + 10), 'crack1', 2)                                 # a glowing crack
    a.line((7, cy + 10), (4, cy + 18), 'crack2', 1)
    a.c((1, cy + 24), (2 + sw * .8, cy + 33), 1.8, 1.4, 'leaf')                    # the sprout
    a.e(-4 + sw * 1.4, cy + 36, 7, 3.4, 'leaf', ang=.5)
    a.e(8 + sw * 1.4, cy + 35, 7, 3.4, 'leaf', ang=-.5)
    a.eye(-2, cy + 9, 4.6, iris='iris', look=(.6, .1))
    a.eye(8, cy + 9, 4.1, iris='iris', look=(.9, .1))
    a.dot(-9, cy + 4, 'blush', 3)
    a.e(3, cy + 1.6, 3, 1 + max(wind * .4, strike) * 2.4, 'mouth')
    spark(a, 'crack2', 24, cy + 6)
    return a.done()


def seed_treant(clip, n):
    a = R.Art('seed_treant', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        for k in range(3):                                                         # root hair of leaves behind the head
            a.e(c.hx - 6 + k * 5, c.hy + 10, 3, 7, 'leaf', ang=(k - 1) * .5)

    def post(c):
        a.e(0, 23, 8, 7, 'moss', out=False)                                        # a mossy belly with the heart-wood glow
        a.e(1, 22, 3.4, 3.4, 'heart', out=False)
        for k in range(7):                                                         # a crown of blossoms
            ang = math.pi / 6 * k + .3
            a.e(c.hx - 1 + math.cos(ang) * 11, c.hy + 7 + math.sin(ang) * 8, 4.2, 4.2, 'blossom')
            a.dot(c.hx - 1 + math.cos(ang) * 11, c.hy + 7 + math.sin(ang) * 8, 'heart1', 2)
        a.e(c.far[0], c.far[1] - 2, 6, 6, 'moss')                                  # a mossy mitten on the far arm

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 1, hy - 4), (hx + 4, hy + 15), 2.6, 4.4, 'bark')
        for k in range(5):
            ang = k * 1.26
            a.e(hx + 5 + math.cos(ang) * 4.6, hy + 18 + math.sin(ang) * 4.6, 3.2, 3.2, 'blossom')
        a.e(hx + 5, hy + 18, 2.6, 2.6, 'heart')

    c = humanoid(a, 'bark', 'bark', leg='bark', arm='bark', hand='moss', w=15, legh=13, th=22, hr=(11, 9.6), pre=pre,
                 post=post, weapon=weapon, pk=.9, armw=4.4, blush='blush')
    spark(a, 'blossom2', c.near[0] + 14, c.near[1] + 10)
    return a.done()


def solar_cinder(clip, n):
    T = R.timing(clip, n)
    a = R.Art('solar_cinder', clip, n, sy=1 - T['fall'] * .55)
    fall, wind, strike, bob, sw = parts(a)
    a.pk, a.ox = .95, -2
    a.lift = fall * 4
    squash = 1 - wind * .08 + strike * .06
    cy = 22 + bob * .7 - fall * 6
    flick = n % 3
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.e(s * 8, 3 + up, 5.4, 3, 'coal')
    a.e(0, cy + 2, 19 * (1 + wind * .05), 20 * squash, 'coal')                     # the cooling lump
    a.e(-6, cy + 9, 9, 8, 'coal', out=False)
    glow = 'lava2' if (clip != 'idle' or n % 2) else 'lava1'
    for (p, q) in (((-10, cy + 4), (-4, cy - 6)), ((-4, cy - 6), (3, cy - 2)), ((3, cy - 2), (10, cy - 12)), ((8, cy + 12), (13, cy + 4)), ((-12, cy + 12), (-6, cy + 16))):
        a.line(p, q, glow, 2 if clip == 'attack' and strike else 1)                # molten cracks
    for k, (fx, fh, ph) in enumerate(((-7, 12, 0), (0, 18, 1.4), (7, 11, 2.7))):   # a flame tuft that flickers
        h = fh + math.sin(n * 1.3 + ph) * 2.6 + strike * 6
        a.poly([(fx - 5, cy + 18), (fx + sw * 1.6, cy + 18 + h), (fx + 5, cy + 18)], 'flame1' if k % 2 == 0 else 'flame2')
    a.poly([(-3, cy + 18), (sw * 1.2, cy + 18 + 8 + flick), (3, cy + 18)], 'flame3', out=False)
    a.eye(-3, cy + 4, 4.6, iris='iris', look=(.6, .1))
    a.eye(8, cy + 4, 4.1, iris='iris', look=(.9, .1))
    a.dot(-11, cy - 1, 'blush', 3)
    a.e(4, cy - 5, 3.4, 1.2 + max(wind * .4, strike) * 3, 'mouth')
    if clip in ('idle', 'walk'):
        a.dot(12 + sw * 2, cy + 24 + flick * 3, 'flame3', 1)                       # a rising spark
    spark(a, 'flame3', 28, cy + 4)
    if clip == 'die' and n > 3:
        a.e(0, 3, 22, 3.4, 'ash')
    return a.done()


def amber_cocoon(clip, n):
    T = R.timing(clip, n)
    a = R.Art('amber_cocoon', clip, n, sy=1 - T['fall'] * .6)
    fall, wind, strike, bob, sw = parts(a)
    a.pk, a.ox = .96, -1
    a.lift = 0
    pulse = 1 if clip == 'attack' and n in (3, 4, 5) else 0
    breathe = 1 + math.sin(n * math.pi / 3) * .015 if clip == 'idle' else 1
    a.e(0, 4, 21, 5, 'resin')                                                      # the resin it stands in
    a.e(5, 3, 9, 2.4, 'resin', out=False)
    for k, x in enumerate((-6, 0, 6)):                                             # silk strands anchoring it
        a.line((x, 56 + k), (x * 2.2 + sw * 1.4, 78 - k * 2), 'silk0', 1)
    a.e(0, 34 * (1 - fall * .15), 17, 28 * breathe, 'amber')                       # the amber shell
    a.e(-6, 44, 6, 15, 'amber', out=False)
    a.poly([(-12, 24), (-9, 52), (-6, 54), (-9, 24)], 'amber3', out=False)         # a long gloss
    a.e(1, 31, 8.6, 20, 'pupa')                                                    # the sleeper inside
    for k in range(5):
        a.line((-7, 20 + k * 7), (9, 22 + k * 7), 'pupa0', 1)
    a.e(3, 46, 4.6, 4.2, 'pupa')
    if pulse or clip == 'idle' and n % 3 == 0:
        a.e(1, 31, 5, 13, 'glow', out=False)
    a.dot(1, 46, 'glow1', 2)
    a.dot(6, 46, 'glow1', 2)
    for bx, by, br in ((9, 24, 1.6), (11, 38, 1.2), (-10, 50, 1.4), (6, 15, 1)):
        a.e(bx, by + sw * .3, br, br, 'bubble', out=False)
    if clip == 'die' and n > 2:                                                    # the shell cracks and spills
        a.line((-8, 50), (0, 34), 'deep1', 1)
        a.line((0, 34), (8, 18), 'deep1', 1)
    spark(a, 'glow1', 22, 36)
    return a.done()


DRAW = dict(choirsinger=choirsinger, reliquarypearl=reliquarypearl, seed_sprout=seed_sprout, seed_treant=seed_treant,
            solar_cinder=solar_cinder, amber_cocoon=amber_cocoon)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


def main():
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/boss-helper-preview')
    print('ok')


if __name__ == '__main__':
    main()
