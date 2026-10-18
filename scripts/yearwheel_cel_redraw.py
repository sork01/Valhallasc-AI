"""Cel-shaded Yearwheel enemies (zone 28) for make_yearwheel_sprites.py.

Same recipe as cairn_cel_redraw.py, built on the shared archetypes of cel_arch.py: hard colour bands, one dark outline
per part, big glossy eyes, chibi proportions. 96x96 frame, foot anchor (48,90), five clips; kind IDs unchanged (the
eight year_* NPCs keep their old art). `python3 scripts/yearwheel_cel_redraw.py [kind...]` writes contact sheets to
test-results/yearwheel-preview.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import (bird, burst, floater, humanoid, mouth_open, parts, quad, serpent, spark)
from cel_zone_common import ROOT, diamond, mku as mk, preview, star

KINDS = ('brooknewt', 'sundarter', 'acornmimic', 'snowstoat', 'bloomtortoise', 'petalchimera', 'rainseraph', 'glasslion',
         'sunwheel', 'firephoenix', 'lanternowl', 'harvestreaper', 'ambermantis', 'rimesaber', 'snowgiant',
         'longnightwyrm')

PALETTES = {
    'brooknewt': mk(skin=('#1c5a5e', '#3a9a8a', '#78d8a0', '#c8fcc0'), belly=('#e8a050', '#ffd488'),
                    spot=('#2a7ad0', '#8ae0ff'), iris='#1c2a8a', blush='#ff9aa0', fin=('#2a7a9a', '#6ad0d0', '#b8f4e8'),
                    nose='#d8606a'),
    'sundarter': mk(skin=('#7a3a1c', '#d8742c', '#f8b848', '#ffe890'), belly=('#ffe0a0', '#fff6d0'),
                    sail=('#c8321c', '#ff7a2a', '#ffc040'), iris='#3a1c6a', blush='#ff8a8a', nose='#a82a2a'),
    'acornmimic': mk(nut=('#6a3a1c', '#b8742c', '#e8b060', '#fce0a0'), cap=('#4a3220', '#8a5a34', '#c28a52'),
                     stem=('#3a5a1c', '#7aa83a'), iris='#2a1c1c', blush='#ff9a8a', mouth=('#3a0c1c', '#a8283a'),
                     tooth='#fffcf0', leaf=('#2a7a2c', '#6ac84a')),
    'snowstoat': mk(fur=('#7a96b8', '#c4d8ec', '#f2f8ff', '#ffffff'), tip=('#1c1c2c', '#4a4a64'),
                    belly=('#e8f0fa', '#fcffff'), iris='#1c3a8a', blush='#ffa0b8', nose='#3a2a3a'),
    'bloomtortoise': mk(skin=('#3a6a2a', '#68a840', '#a4dc68', '#dcfaa0'), shell=('#4a3a1c', '#8a6a34', '#c49a58'),
                        petal=('#c83a6a', '#ff7a9a', '#ffc0cc', '#fff0f0'), mid=('#c88a1c', '#ffd048'),
                        iris='#2a2a6a', blush='#ff9aa0', leaf=('#2a7a2c', '#58c04a')),
    'petalchimera': mk(fur=('#7a3a6a', '#c870a8', '#f0a8c8', '#ffe0ec'), petal=('#d83a7a', '#ff7aaa', '#ffc4d8', '#fff2f4'),
                       belly=('#ffe0f0', '#fff8fc'), tail=('#2a7a4a', '#58c078', '#a8f0a0'), horn=('#6a4a1c', '#d8a444'),
                       iris='#2a6a4a', blush='#ffa0b0', nose='#e8507a'),
    'rainseraph': mk(robe=('#1c4a78', '#3a88c8', '#7cc8f0', '#c8f0ff'), skin=('#a8d8e8', '#dcf6fc', '#ffffff'),
                     wing=('#5a8ac8', '#a4d0f4', '#e4f6ff'), halo=('#6a8ae8', '#c0d8ff', '#f4faff'),
                     drop=('#2a88e0', '#9ae8ff'), iris='#2a5ad0', blush='#ffa0c8', mouth=('#1c3a6a', '#5a88c8'),
                     hair=('#2a6ab0', '#5aa4e0')),
    'glasslion': mk(fur=('#a8602a', '#e8a248', '#fcd078', '#fff0b8'), mane=('#2aa8a8', '#78e8e0', '#cafff4', '#ffffff'),
                    belly=('#ffe8b0', '#fff8dc'), tuft=('#2a9898', '#78e0d8'), iris='#1c6a8a', blush='#ff9a8a',
                    nose='#d8486a', tooth='#fffcf0'),
    'sunwheel': mk(disc=('#b8481c', '#f08a2a', '#ffc848', '#fff098'), ray=('#d8681c', '#ffa836', '#ffe478'),
                   rim=('#6a3a1c', '#b8742c', '#e8b458'), iris='#4a1c1c', blush='#ff7a5a', mouth=('#5a0c1c', '#d8382a'),
                   shadow=('#5a3a1c', '#8a5a2c')),
    'firephoenix': mk(feather=('#a8281c', '#e8541c', '#ff9a30', '#ffd868'), flame=('#e8341c', '#ff8a28', '#ffd44a', '#fff6b0'),
                      beak=('#a8741a', '#f4c448', '#fff0a0'), leg=('#6a3a1c', '#b8742c'), claw=('#7a4a1c', '#d8a444'),
                      iris='#2a1c4a', blush='#ffb08a', shine=('#ffe8a0', '#fffcd8')),
    'lanternowl': mk(feather=('#4a3a4a', '#8a7064', '#c4a07c', '#f0d8ac'), face=('#a89080', '#e8d4b8', '#fff4dc'),
                     beak=('#a8741a', '#f4c448', '#fff0a0'), leg=('#5a4a3a', '#9a8268'), claw=('#6a5a4a', '#b8a888'),
                     lamp=('#6a4a1c', '#b8842c', '#f0b848'), glow=('#ffb028', '#ffe678', '#fffbd0'), iris='#ffb81c',
                     blush='#ffa098', cord=('#4a3a2a', '#8a7054')),
    'harvestreaper': mk(robe=('#3a1c4a', '#6a3a7a', '#a8648a', '#e8a0a8'), skin=('#c8741c', '#f4a436', '#ffd068'),
                        hat=('#8a6a1c', '#d8b040', '#fce078'), blade=('#7a8aa8', '#c0d0ec', '#f4fcff'),
                        shaft=('#4a2a1c', '#8a5a34', '#c08a54'), iris='#ffe848', blush='#ff7a5a',
                        mouth=('#2a0c1c', '#d8742a'), wheat=('#c8962a', '#f8d860')),
    'ambermantis': mk(body=('#7a4a1c', '#c8842c', '#f0b848', '#ffe898'), blade=('#a8461c', '#f08a2a', '#ffd068'),
                      belly=('#fcd078', '#fff0b8'), eye=('#2a1c0c', '#ffd048'), iris='#7a1c1c', blush='#ff9a6a',
                      sac=('#ffb028', '#fff0a0'), wing=('#e8b868', '#fff0c0', '#ffffe8')),
    'rimesaber': mk(fur=('#3a5a8a', '#7aa4d0', '#c4e4f8', '#f4fcff'), ice=('#4a9ad0', '#9ae0ff', '#e0fcff', '#ffffff'),
                    belly=('#e8f8ff', '#ffffff'), fang=('#c8e8f8', '#ffffff'), iris='#1c8ad8', blush='#ffa0c0',
                    nose='#e8608a', stripe=('#1c3a6a', '#3a64a0')),
    'snowgiant': mk(fur=('#5a7a9a', '#a4c4dc', '#e0f0fa', '#ffffff'), skin=('#7a98b8', '#bcd8ec', '#e8f6ff'),
                    horn=('#5a5a6a', '#a8a8b8', '#e8e8f4'), cloth=('#4a2a1c', '#8a5a34', '#c08a54'),
                    iris='#2a6ad0', blush='#ffa0b8', mouth=('#2a1c3a', '#6a3a5a'), club=('#5a3a24', '#9a6a40', '#d0a064'),
                    ice=('#4a9ad0', '#cafaff')),
    'longnightwyrm': mk(skin=('#141c48', '#2a3c8a', '#5a78d0', '#a8c8fc'), belly=('#a8b0f0', '#e0e8ff'),
                        star=('#ffe478', '#fffcd0'), sail=('#2a1c6a', '#5a3aa8', '#9a7ae0'), iris='#ffd848',
                        blush='#ff9ac8', tongue=('#6a3ac0', '#c88aff'), fang=('#d8e0f8', '#ffffff')),
}
R.PALETTES.update(PALETTES)


# ------------------------------------------------------------------------------------------------
def brooknewt(clip, n):
    a = R.Art('brooknewt', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-20, c.cy + 2), (-29, c.cy + 6 + c.wav * .5), 4.6, 2.6, 'skin')
        a.c((-29, c.cy + 6 + c.wav * .5), (-37, c.cy + 3 + c.wav), 3, 1, 'skin')
        a.e(-28, c.cy + 12 + c.wav * .5, 4.4, 3, 'fin', ang=.5)

    def pre(c):
        for k, sx in enumerate((-14, -4, 6)):
            a.e(sx, c.cy + 11, 2.6, 2.1, 'spot')
        for k in range(3):
            a.poly([(-10 + k * 6, c.cy + 12), (-8 + k * 6, c.cy + 17), (-6 + k * 6, c.cy + 12)], 'fin1', out=False)

    c = quad(a, 'skin', 'belly', L=26, Hh=8.4, base=10, legw=3, stance=(-18, -8, 8, 17), hr=(11, 8.6), hdx=24, hdy=6,
             tail=tail, pre=pre, nose=None)
    spark(a, 'spot1', c.hx + 15, c.hy)
    return a.done()


def sundarter(clip, n):
    a = R.Art('sundarter', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-22, c.cy + 2), (-38, c.cy + 5 + c.wav * .6), 4.2, 1.2, 'skin')

    def pre(c):
        pts = [(-18, c.cy + 9), (-14, c.cy + 24), (-8, c.cy + 14), (-2, c.cy + 28), (4, c.cy + 15), (10, c.cy + 24), (14, c.cy + 10)]
        a.band(pts, 'sail')
        for sx in (-14, -2, 10):
            a.line((sx, c.cy + 11), (sx, c.cy + 19), 'sail3', 1)

    c = quad(a, 'skin', 'belly', L=22, Hh=9.4, base=14, hr=(10.4, 8.6), hdx=22, hdy=8, tail=tail, pre=pre)
    spark(a, 'sail2', c.hx + 15, c.hy)
    return a.done()


def acornmimic(clip, n):
    T = R.timing(clip, n)
    fall, wind, strike, bob, sw = parts(R.Art('acornmimic', clip, n))
    a = R.Art('acornmimic', clip, n, sy=1 - fall * .5)
    a.pk = .92
    a.lift = fall * 5
    b = bob * .6
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 7, 16), (s * 8, 4 + up), 3.4, 2.6, 'stem')
        a.e(s * 10 + 2, 2.6 + up, 4.6, 2.4, 'cap')
    # a round acorn body, the cap hat above, a toothy mouth on the front
    a.e(0, 30 + b, 17, 17, 'nut')
    a.e(-6, 38 + b, 8, 4, 'nut', out=False)
    hand = (lerp_(24, 22, wind, 28, strike), lerp_(30, 50, wind, 30, strike) + b)
    for s in (-1, 1):
        h = hand if s > 0 else (-23 + sw * 1.5, 30 + b)
        a.c((s * 15, 29 + b), h, 3.2, 2.8, 'nut')
        a.e(h[0], h[1], 3.6, 3.6, 'leaf')
    a.eye(-4, 33 + b, 4.6, iris='iris', look=(.5, .1))
    a.eye(7, 33 + b, 4.2, iris='iris', look=(.9, .1))
    a.dot(-10, 27 + b, 'blush', 3)
    gape = max(wind * .5, strike) * 4
    a.e(2, 24 + b, 7, 2.4 + gape, 'mouth')
    for k in (-1, 1):
        a.poly([(2 + k * 3, 26 + b + gape * .5), (4 + k * 3, 26 + b + gape * .5), (3 + k * 3, 22.4 + b + gape * .5)], 'tooth', out=False)
    # cap with a stem and a leaf
    a.e(0, 44 + b, 19.4, 8.6, 'cap')
    a.e(-6, 47 + b, 9, 2.6, 'cap', out=False)
    for k in range(5):
        a.line((-14 + k * 7, 41 + b), (-13 + k * 7, 46 + b), 'cap0', 1)
    a.c((1, 51 + b), (3, 60 + b), 2.4, 1.6, 'stem')
    a.e(8 + sw * .8, 62 + b, 5, 2.6, 'leaf', ang=.5)
    spark(a, 'cap2', hand[0] + 8, hand[1])
    return a.done()


def lerp_(rest, w_to, w, s_to, s):
    """rest -> w_to by `w` (wind-up) -> s_to by `s` (strike), as the humanoid arms do."""
    return R.lerp(R.lerp(rest, w_to, w), s_to, s)


def snowstoat(clip, n):
    a = R.Art('snowstoat', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-22, c.cy + 2), (-35, c.cy + 6 + c.wav * .5), 3.6, 2.6, 'fur')
        a.e(-37, c.cy + 6.5 + c.wav * .5, 4, 3, 'tip')

    def pre(c):
        a.e(c.hx + 3, c.hy + 8, 3.4, 5, 'fur', ang=-.5)

    c = quad(a, 'fur', 'belly', L=24, Hh=9.6, base=13, hr=(10.6, 9), hdx=21, hdy=8, tail=tail, tailpre=True, pre=pre)
    spark(a, 'fur3', c.hx + 15, c.hy)
    return a.done()


def bloomtortoise(clip, n):
    T = R.timing(clip, n)
    a = R.Art('bloomtortoise', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.ox = -4
    a.pk = .9
    a.lift = fall * 5
    b = bob * .5
    for k, lx in enumerate((-16, -6, 8, 18)):
        up = max(0, math.sin(n * math.pi / 2 + k * 1.6)) * 3 if clip == 'walk' else 0
        a.c((lx * .9, 12 + b), (lx + 1, 3 + up), 4.4, 3.4, 'skin')
        a.e(lx + 2, 2 + up, 4.6, 2, 'skin')
    a.c((-24, 14), (-33, 10 + sw * 2), 3.4, 1.2, 'skin')
    # a big domed shell with flower buds
    a.e(-3, 22 + b, 26, 15, 'shell')
    a.e(-8, 30 + b, 14, 4.4, 'shell', out=False)
    for k in range(4):
        a.line((-20 + k * 9, 14 + b), (-16 + k * 9, 33 + b), 'shell0', 1)
    for k, (fx, fy, r) in enumerate(((-14, 36, 6), (1, 40, 7.4), (14, 34, 6))):
        for j in range(5):
            ang = j * 6.283 / 5 + sw * .1
            a.e(fx + math.cos(ang) * r * .9, fy + b + math.sin(ang) * r * .9, r * .5, r * .5, 'petal')
        a.e(fx, fy + b, r * .45, r * .45, 'mid')
    a.e(-22, 31 + b, 3.6, 5, 'leaf', ang=.6)
    hx, hy = 29 + strike * 5 - wind * 3, 19 + b - wind * 1
    a.c((20, 16 + b), (hx - 3, hy), 5, 5.6, 'skin')
    a.e(hx, hy, 10, 8.4, 'skin')
    a.e(hx - 3, hy + 3.4, 5, 2.6, 'skin', out=False)
    a.eye(hx - 1, hy + 1.8, 4.2, iris='iris', look=(.8, .1))
    a.eye(hx + 6, hy + 1.6, 3.2, iris='iris', look=(.9, .1))
    a.dot(hx - 6, hy - 2, 'blush', 2)
    a.line((hx + 2, hy - 4 - max(wind * .5, strike) * 2), (hx + 9, hy - 4 - max(wind * .5, strike) * 2), 'ink', 1)
    spark(a, 'petal2', hx + 12, hy)
    return a.done()


def petalchimera(clip, n):
    a = R.Art('petalchimera', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        w = c.wav
        a.c((-20, c.cy + 4), (-28, c.cy + 14 + w * .5), 3.6, 2.6, 'tail')
        a.c((-28, c.cy + 14 + w * .5), (-30, c.cy + 26 + w), 2.6, 1.8, 'tail')
        for j in range(5):
            ang = j * 1.257 + .4
            a.e(-30 + math.cos(ang) * 5, c.cy + 29 + w + math.sin(ang) * 5, 3.4, 3.4, 'petal')
        a.e(-30, c.cy + 29 + w, 2.8, 2.8, 'horn')

    def pre(c):
        for j in range(9):
            ang = j * 6.283 / 9
            a.e(c.hx - 2 + math.cos(ang) * 12.4, c.hy + 1 + math.sin(ang) * 11, 4.6, 6.4, 'petal', ang=ang + 1.57)

    c = quad(a, 'fur', 'belly', L=22, Hh=11, base=15, hr=(9.6, 8.2), hdx=20, hdy=9, tail=tail, pre=pre, snout=True, k=1.15, ox=-1)
    spark(a, 'petal2', c.hx + 18, c.hy)
    return a.done()


def rainseraph(clip, n):
    T = R.timing(clip, n)
    a = R.Art('rainseraph', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    flap = math.sin(n * math.pi / 3) * 4 if clip == 'idle' else (3 * sw if clip == 'walk' else 0)
    if clip == 'attack':
        flap = (-3, -7, -11, 6, 8, 4, 1, 0)[n]
    hov = 6 + bob * 1.2 - fall * 6
    a.pk = .88
    # two feathered wings behind the figure
    for s in (-1, 1):
        a.e(s * 18, 46 + hov + flap * .8, 6.4, 17, 'wing', ang=s * (.5 - flap * .04))
        a.e(s * 15, 52 + hov + flap * .8, 3.4, 11, 'wing', ang=s * (.5 - flap * .04), out=False)
    # raindrops circling the halo
    a.e(0, 20 + hov * .2, 9, 2, 'drop', out=False)

    def pre(c):
        for k in range(5):
            ang = k * 1.256 + sw * .2
            a.e(c.hx + math.cos(ang) * 12, c.hy + 14 + math.sin(ang) * 3, 2.2, 3.4, 'drop')
        a.e(c.hx, c.hy + 13, 9, 2.4, 'halo', out=False)

    def pre2(c):
        pre(c)
        a.e(c.hx - 4, c.hy + 1, 11, 11.4, 'hair')

    c = humanoid(a, 'robe', 'skin', w=11, legh=hov, th=24, hr=(9.6, 10), robe=True, hem='robe', pre=pre2,
                 mouth='mouth')
    spark(a, 'drop1', c.near[0] + 8, c.near[1])
    return a.done()


def glasslion(clip, n):
    a = R.Art('glasslion', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-22 * c.k, c.cy + 3), (-31 * c.k, c.cy + 8 + c.wav * .6), 2.8, 1.8, 'fur')
        a.e(-33 * c.k, c.cy + 9 + c.wav * .6, 4.4, 5, 'tuft')

    def pre(c):
        mx, my = c.hx - 3, c.hy + 1
        for j in range(12):
            ang = j * 6.283 / 12
            a.poly([(mx + math.cos(ang - .22) * 12, my + math.sin(ang - .22) * 11),
                    (mx + math.cos(ang) * 19, my + math.sin(ang) * 17),
                    (mx + math.cos(ang + .22) * 12, my + math.sin(ang + .22) * 11)], 'mane' + str(1 + j % 3))
        a.e(mx, my, 13.4, 12, 'mane')

    c = quad(a, 'fur', 'belly', L=22, Hh=10, base=14, hr=(8.6, 7.4), hdx=19, hdy=7, tail=tail, pre=pre, k=1.2, ox=-6)
    spark(a, 'mane2', c.hx + 20, c.hy)
    return a.done()


def sunwheel(clip, n):
    a = R.Art('sunwheel', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        spin = n * .26
        for k in range(12):
            ang = spin + k * 6.283 / 12
            a.poly([(c.x + math.cos(ang - .14) * 17, c.y + math.sin(ang - .14) * 17),
                    (c.x + math.cos(ang) * 27, c.y + math.sin(ang) * 27),
                    (c.x + math.cos(ang + .14) * 17, c.y + math.sin(ang + .14) * 17)], 'ray' + str(1 + k % 2))
        a.e(c.x, c.y, 19.4, 19.4, 'rim')

    c = floater(a, 'disc', R=(15, 15), cy=44, pre=pre, eye=4.8)
    spark(a, 'ray2', c.x + 24, c.y)
    return a.done()


def firephoenix(clip, n):
    T = R.timing(clip, n)
    a = R.Art('firephoenix', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        # tail plumes of flame
        for k in range(4):
            a.poly([(-8, c.cy - 2), (-26 - k * 2 + math.sin(n * .9 + k) * 2, 6 + k * 9), (-14, c.cy - 8 + k)], 'flame' + str(1 + k % 3))

    def post(c):
        # flame crest on the head
        for k in range(3):
            a.poly([(c.hx - 3 + k * 3, c.hy + 9), (c.hx - 6 + k * 3.4 + math.sin(n + k) * 1.2, c.hy + 19 + k * 2), (c.hx + 1 + k * 3, c.hy + 9)],
                   'flame' + str(1 + k))

    c = bird(a, 'feather', wing='flame', beak='beak', leg='leg', claw='claw', pre=pre, post=post, R=(14, 15), tailn=0)
    spark(a, 'flame2', c.hx + 20, c.hy)
    return a.done()


def lanternowl(clip, n):
    T = R.timing(clip, n)
    a = R.Art('lanternowl', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.ox = -2
    a.pk = .92
    a.lift = fall * 6
    b = bob * .6
    flap = math.sin(n * math.pi / 3) * 3 if clip == 'idle' else 0
    if clip == 'attack':
        flap = (-4, -8, -12, 6, 8, 4, 1, 0)[n]
    cy = 32 + b - fall * 8
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 3 if clip == 'walk' else 0
        a.c((s * 6, cy - 12), (s * 7, 5 + up), 2.2, 1.8, 'leg')
        a.e(s * 7 + 2, 3 + up, 5, 1.8, 'claw')
    a.e(0, cy, 17, 20, 'feather')
    a.e(4, cy - 3, 10, 13, 'face', out=False)
    for k in range(3):
        a.line((-6 + k * 5, cy - 8), (-5 + k * 5, cy - 14), 'feather0', 1)
    a.e(-14, cy + 1 + flap, 7, 15, 'feather', ang=.15)
    a.e(14, cy + 1 + flap * .6, 5, 13, 'feather', ang=-.15)
    # ear tufts, great round eyes, hooked beak
    hx, hy = 2 + strike * 4, cy + 18
    for s in (-1, 1):
        a.poly([(hx + s * 9, hy + 6), (hx + s * 13, hy + 17), (hx + s * 5, hy + 10)], 'feather1')
    a.e(hx, hy, 15, 11.4, 'feather')
    a.e(hx - 5, hy + 5, 7, 3, 'feather', out=False)
    for s in (-1, 1):
        a.e(hx + s * 6.4, hy + .6, 6.6, 7, 'face')
    a.eye(hx - 6.4, hy + .6, 4.6, iris='iris', look=(.5, .1))
    a.eye(hx + 6.4, hy + .6, 4.6, iris='iris', look=(.5, .1))
    a.poly([(hx - 2, hy - 2), (hx + 2, hy - 2), (hx, hy - 8 - max(wind * .5, strike) * 2)], 'beak1')
    a.dot(hx - 12, hy - 4, 'blush', 2)
    # a hanging lantern in the near talon
    lx, ly = 22 + strike * 6 - wind * 2, cy - 6 + sw * 1
    a.line((12, cy + 2), (lx, ly + 8), 'cord1', 1)
    a.e(lx, ly + 1.4, 7.4, 7.4, 'glow', out=False)
    a.e(lx, ly, 4.6, 5.4, 'lamp')
    a.e(lx, ly, 2.6, 3.4, 'glow')
    a.e(lx, ly + 6.4, 4, 1.6, 'lamp', out=False)
    spark(a, 'glow2', lx + 8, ly)
    return a.done()


def harvestreaper(clip, n):
    T = R.timing(clip, n)
    a = R.Art('harvestreaper', clip, n, sy=1 - T['fall'] * .5)

    def post(c):
        # straw hat with a wheat sprig; pumpkin cheeks come from the skin group
        a.e(c.hx + 1, c.hy + 8, 15, 3.4, 'hat')
        a.e(c.hx + 1, c.hy + 13, 8, 6, 'hat')
        a.e(c.hx - 3, c.hy + 15, 4, 1.8, 'hat', out=False)
        for k in range(3):
            a.line((c.hx + 8 + k * 2, c.hy + 10), (c.hx + 10 + k * 3, c.hy + 16 + k), 'wheat1', 1)

    def weapon(c):
        hx, hy = c.near
        a.line((hx - 3, hy - 22), (hx + 1, hy + 24), 'shaft1', 2)
        a.poly([(hx + 1, hy + 24), (hx + 17, hy + 22), (hx + 10, hy + 12), (hx + 3, hy + 17)], 'blade2')
        a.line((hx + 2, hy + 23), (hx + 14, hy + 21), 'blade0', 1)

    c = humanoid(a, 'robe', 'skin', w=12, th=26, hr=(10.4, 10), robe=True, post=post, weapon=weapon, pk=.8)
    spark(a, 'blade1', c.near[0] + 14, c.near[1])
    return a.done()


def ambermantis(clip, n):
    T = R.timing(clip, n)
    a = R.Art('ambermantis', clip, n, sy=1 - T['fall'] * .5)
    fall, wind, strike, bob, sw = parts(a)
    a.pk = .82
    a.lift = fall * 5
    b = bob * .6
    for s in (-1, 1):
        up = max(0, s * math.sin(n * math.pi / 2)) * 4 if clip == 'walk' else 0
        a.c((s * 5, 24), (s * 9, 14 + up), 2.4, 1.8, 'body')
        a.c((s * 9, 14 + up), (s * 11, 3 + up), 1.8, 1.4, 'blade')
    # tapering abdomen with a wing case, slim thorax
    a.e(-6, 26 + b, 16, 12, 'body')
    a.e(-12, 29 + b, 10, 5, 'wing', out=False)
    a.band([(-4, 30 + b), (6, 30 + b), (5, 52 + b), (-3, 52 + b)], 'body')
    a.e(2, 40 + b, 3, 6, 'belly', out=False)
    # raptorial forelegs: the near one chops
    far = (-14 + sw, 40 + b)
    a.c((-3, 48 + b), far, 3, 2.4, 'blade')
    a.c(far, (-10, 28 + b), 2.4, 1.2, 'blade')
    k1 = (lerp_(14, 12, wind, 20, strike), lerp_(54, 72, wind, 40, strike) + b)
    if clip == 'die':
        k1 = (R.lerp(14, 18, fall), R.lerp(54, 10, fall))
    a.c((4, 48 + b), k1, 3.4, 2.6, 'blade')
    k2 = (k1[0] + 8 + strike * 4, k1[1] - 10 - strike * 6)
    a.c(k1, k2, 2.6, 1, 'blade')
    for q in range(3):
        a.line((k1[0] + 1 + q * 2, k1[1] - 1 - q * 2), (k2[0] - 1, k2[1] + 2 - q), 'blade3', 1)
    # triangular head with huge eyes and bent antennae
    hx, hy = 3 + strike * 2, 62 + b
    a.c((hx - 3, hy + 8), (hx - 10 - sw, hy + 20), 1.6, 1, 'body')
    a.c((hx + 2, hy + 8), (hx + 8 + sw, hy + 20), 1.6, 1, 'body')
    a.e(hx, hy, 12, 10, 'body')
    a.e(hx - 4, hy + 4, 6, 3, 'body', out=False)
    a.eye(hx - 4.4, hy + 1.2, 4.8, iris='iris', look=(.4, .1))
    a.eye(hx + 5.8, hy + 1.2, 4.4, iris='iris', look=(.8, .1))
    a.dot(hx - 10, hy - 3, 'blush', 3)
    a.e(hx + 1, hy - 6, 3.4, 1.2 + max(wind * .4, strike) * 2.4, 'blade')
    spark(a, 'blade3', k1[0] + 14, k1[1] - 8)
    return a.done()


def rimesaber(clip, n):
    a = R.Art('rimesaber', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def tail(c):
        a.c((-22 * c.k, c.cy + 3), (-33 * c.k, c.cy + 10 + c.wav * .6), 4.4, 2.2, 'fur')

    def pre(c):
        for s in (-1, 1):
            bx = c.hx + s * 5
            a.c((bx, c.hy + 7), (bx + s * 4, c.hy + 16), 2.4, 2, 'ice')
            a.c((bx + s * 4, c.hy + 16), (bx + s * 10, c.hy + 21), 2, 1, 'ice')
            a.c((bx + s * 3, c.hy + 14), (bx - s * 3, c.hy + 22), 1.8, 1, 'ice')
        for k in range(3):
            a.line((-14 + k * 8, c.cy + 10), (-13 + k * 8, c.cy + 4), 'stripe1', 2)

    def post(c):
        for s in (0, 1):
            a.poly([(c.hx + 6 + s * 3, c.hy - 5), (c.hx + 8 + s * 3, c.hy - 5), (c.hx + 7 + s * 3, c.hy - 13 - max(c.T['wind'] * .5, c.T['strike']) * 2)], 'fang1')

    c = quad(a, 'fur', 'belly', L=22, Hh=10, base=15, hr=(10, 8.4), hdx=20, hdy=9, tail=tail, pre=pre, post=post, k=1.2, ox=-6)
    spark(a, 'ice2', c.hx + 15, c.hy)
    return a.done()


def snowgiant(clip, n):
    T = R.timing(clip, n)
    a = R.Art('snowgiant', clip, n, sy=1 - T['fall'] * .5)

    def pre(c):
        for s in (-1, 1):
            a.c((c.hx + s * 8, c.hy + 7), (c.hx + s * 15, c.hy + 14), 3.6, 3, 'horn')
            a.c((c.hx + s * 15, c.hy + 14), (c.hx + s * 14, c.hy + 23), 3, 1.2, 'horn')

    def weapon(c):
        hx, hy = c.near
        a.c((hx - 2, hy - 4), (hx + 4, hy + 18), 3.2, 4.4, 'club')
        a.e(hx + 5, hy + 22, 7.4, 7.4, 'ice')
        a.dot(hx + 3, hy + 25, 'ice1', 2)

    c = humanoid(a, 'fur', 'skin', leg='fur', arm='fur', hand='skin', w=17, legh=15, th=22, hr=(13, 11.4), pre=pre,
                 weapon=weapon, pk=.82, handr=4.4, armw=5)
    a.e(0, 20, 16, 4, 'cloth')
    spark(a, 'ice1', c.near[0] + 14, c.near[1])
    return a.done()


def longnightwyrm(clip, n):
    a = R.Art('longnightwyrm', clip, n, sy=1 - R.timing(clip, n)['fall'] * .5)

    def pre(c):
        pts = c.pts
        a.band([(pts[1][0], 16), (pts[2][0] - 4, 33), (pts[3][0], 22), (pts[4][0] - 2, 36), (pts[5][0] - 6, 40), (pts[5][0] + 2, 18)], 'sail')
        for k in range(3):
            star(a, pts[1][0] + k * 12 + 2, 14 + (k % 2) * 8, 1.8, 'star0')

    c = serpent(a, 'skin', 'belly', mark='star0', length=28, rise=32, thick=5.6, hr=(11.6, 8.6), pre=pre, crest='fang0', ox=-5, lunge=7)
    for s in (-1, 1):
        pass
    spark(a, 'star1', c.hx + 18, c.hy)
    return a.done()


DRAW = dict(brooknewt=brooknewt, sundarter=sundarter, acornmimic=acornmimic, snowstoat=snowstoat,
            bloomtortoise=bloomtortoise, petalchimera=petalchimera, rainseraph=rainseraph, glasslion=glasslion,
            sunwheel=sunwheel, firephoenix=firephoenix, lanternowl=lanternowl, harvestreaper=harvestreaper,
            ambermantis=ambermantis, rimesaber=rimesaber, snowgiant=snowgiant, longnightwyrm=longnightwyrm)


def draw(kind, clip, n):
    return DRAW[kind](clip, n)


if __name__ == '__main__':
    names = [k for k in sys.argv[1:] if k in KINDS] or list(KINDS)
    preview(names, PALETTES, draw, ROOT / 'test-results/yearwheel-preview')
    print('ok')
