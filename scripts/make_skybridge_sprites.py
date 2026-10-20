#!/usr/bin/env python3
"""The Shattered Span's original cel enemies: preview | build | export | verify [kind...].

PixelFlow stores every 96x96, 34-frame sprite; export preserves edits and merges the shared cathedral manifest.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import floater, humanoid, quad, spark
from cel_zone_common import crystal, diamond, mku as mk
import make_eye_below_sprites as maker
from skybridge_content import ENEMIES

KINDS = [e['kind'] for e in ENEMIES]
PALETTES = {}
for e in ENEMIES:
    if e['art'] in ('lynx', 'archon'):
        body = ('#1e4668', '#3682b5', '#68c2ec', '#bdf1ff')
    elif e['art'] in ('sentinel', 'warden'):
        body = ('#5c3d1e', '#a67332', '#e0a952', '#fce19c')
    else:
        body = ('#3d245e', '#7348a6', '#b17ae3', '#e6c6ff')
    PALETTES[e['kind']] = mk(body=body, shade=('#21263d', '#3e476b', '#6d79a3'),
        skin=('#a77d68', '#e0b692', '#ffe2bb'), gold=('#865922', '#d4a148', '#fae08c'),
        prism=('#3cc7e8', '#7df2ff', '#fff7c8'), iris='#62f5e8', blush='#ed8e9e',
        mouth=('#251c2e', '#a1586c'), nose='#32223e', fang=('#c6bca2', '#f6efd4'))
R.PALETTES.update(PALETTES)


def draw(enemy, clip, n):
    kind, art = enemy['kind'], enemy['art']
    a = R.Art(kind, clip, n, sy=1-R.timing(clip, n)['fall']*.55)
    if art == 'lynx':
        def tail(c):
            a.c((-21, c.cy), (-32, c.cy+10+c.wav), 3.8, 2.0, 'body')
            diamond(a, -34, c.cy+13+c.wav, 5, 7, 'prism0')
        def post(c):
            for x in (-8, 0, 8):
                diamond(a, x, c.cy+8, 2.5, 4.5, 'prism0')
            for s in (-1, 1):
                a.poly([(c.hx+s*8, c.hy+5), (c.hx+s*11, c.hy+21), (c.hx+s*2, c.hy+10)], 'body2')
                a.line((c.hx+s*9, c.hy+20), (c.hx+s*12, c.hy+25), 'gold1', 2)
            diamond(a, c.hx, c.hy+5, 2.5, 3.5, 'gold2')
        quad(a, 'body', 'shade', L=23, Hh=10, base=12, hr=(11, 10), hdx=20, hdy=9,
             tail=tail, post=post, ox=-3, pk=.92)
    elif art == 'sentinel':
        b = math.sin(n*math.pi/4)*1.4
        for s in (-1, 1):
            a.c((s*14, 14+b), (s*18, 34+b), 4.5, 3.2, 'shade')
            crystal(a, s*20, 42+b, 5, 11, 'body', tilt=s*4)
        a.e(0, 32+b, 18, 20, 'body')
        a.e(0, 34+b, 12, 13, 'gold', out=False)
        diamond(a, 0, 34+b, 6, 9, 'prism0')
        a.e(0, 52+b, 12, 9, 'body')
        a.eye(3, 52+b, 4.5, a.T['state'], 'iris')
        a.band([(-11, 56+b), (0, 65+b), (11, 56+b)], 'gold')
    elif art == 'caster':
        def pre(c):
            for side in (-1, 1):
                crystal(a, side*22, 38+a.T['sw']*2, 5, 13, 'gold', tilt=side*5)
                a.line((side*12, 36), (side*22, 38+a.T['sw']*2), 'prism0', 2)
            a.e(0, 56, 17, 4, 'gold')
            a.e(0, 24, 16, 4, 'gold')
        c = floater(a, 'body', R=(13, 15), cy=40, eye=4.5, pre=pre)
        for j in range(-1, 2):
            diamond(a, j*7, 31, 2.5, 4, 'prism0')
        spark(a, 'prism1', c.x+19, c.y)
    else:
        def pre(c):
            if art == 'warden':
                a.e(c.far[0]-2, c.far[1]+2, 11, 18, 'gold')
                diamond(a, c.far[0]-2, c.far[1]+2, 6, 12, 'prism0')
            elif art == 'archon':
                for s in (-1, 1):
                    a.band([(s*7, 42), (s*27, 50), (s*31, 16), (s*12, 9)], 'body')
                    a.line((s*14, 40), (s*26, 20), 'prism0', 2)
            else:
                for s in (-1, 1):
                    a.c((s*8, 40), (s*22, 20), 4.5, 2, 'shade')
                    diamond(a, s*22, 20, 3.5, 6, 'prism0')
        def post(c):
            if art == 'archon':
                a.band([(c.hx-12, c.hy+6), (c.hx-15, c.hy+23), (c.hx-5, c.hy+16),
                        (c.hx, c.hy+27), (c.hx+5, c.hy+16), (c.hx+15, c.hy+23), (c.hx+12, c.hy+6)], 'gold')
                diamond(a, c.hx, c.hy+14, 3.5, 5.5, 'prism0')
            elif art == 'warden':
                a.band([(c.hx-12, c.hy+1), (c.hx-14, c.hy+14), (c.hx, c.hy+20),
                        (c.hx+14, c.hy+14), (c.hx+12, c.hy+1)], 'gold')
                for s in (-1, 1):
                    a.poly([(c.hx+s*11, c.hy+6), (c.hx+s*20, c.hy+17), (c.hx+s*12, c.hy+14)], 'prism0')
            else:
                a.band([(c.hx-13, c.hy-2), (c.hx-14, c.hy+13), (c.hx, c.hy+22),
                        (c.hx+14, c.hy+13), (c.hx+13, c.hy-2), (c.hx+7, c.hy+7), (c.hx-7, c.hy+7)], 'shade')
                diamond(a, c.hx, c.hy+14, 3, 5, 'prism0')
        def weapon(c):
            x, y = c.near
            a.c((x, y-8), (x+2, y+20), 1.9, 1.6, 'gold')
            if art == 'warden':
                a.poly([(x+2, y+15), (x+11, y+21), (x+2, y+28)], 'gold')
                diamond(a, x+2, y+22, 3, 5, 'prism0')
            elif art == 'archon':
                crystal(a, x+2, y+27, 5, 12, 'prism', tilt=2)
                a.e(x+2, y+18, 6, 3, 'gold')
            else:
                a.e(x+2, y+22, 6, 6, 'gold')
                diamond(a, x+2, y+22, 3.5, 4.5, 'prism0')
        humanoid(a, 'body', 'skin', leg='shade', w=13 if art == 'archon' else 11, legh=12, th=22,
                 hr=(11, 10), robe=art == 'weaver', pre=pre, post=post, weapon=weapon,
                 pk=.81 if art == 'archon' else .9, hem='gold' if art == 'weaver' else None)
        spark(a, 'prism1', 29, 33)
    return a.done()


maker.ENEMIES = ENEMIES
maker.KINDS = KINDS
maker.PALETTES = PALETTES
maker.PREFIX = 'valhallasc_skybridge_'
maker.draw = draw

if __name__ == '__main__':
    action = sys.argv[1]
    kinds = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action == 'build':
        maker.build(kinds, replace='--replace' in sys.argv[2:])
    else:
        getattr(maker, action)(kinds)
