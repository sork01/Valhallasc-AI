#!/usr/bin/env python3
"""Nornroot's original cel enemies: preview | build | export | verify [kind...].

PixelFlow stores every 96x96, 34-frame sprite; export preserves edits and merges the shared cathedral manifest.
"""
import math
import sys

import cathedral_reliquary_redraw as R
from cel_arch import floater, humanoid, quad, spark
from cel_zone_common import diamond, mku as mk
import make_eye_below_sprites as maker
from nornroot_content import ENEMIES

KINDS = [e['kind'] for e in ENEMIES]
PALETTES = {}
for e in ENEMIES:
    if e['art'] in ('scarab', 'doorward', 'king'):
        body = ('#52352d', '#9f6a3b', '#d6a05c', '#f7d994')
    elif e['art'] in ('hound', 'keeper'):
        body = ('#342b58', '#665287', '#a184c0', '#d4b6e6')
    else:
        body = ('#234740', '#428278', '#7cb8a1', '#c9e7c1')
    PALETTES[e['kind']] = mk(body=body, shade=('#29263b', '#48415e', '#77678c'),
        skin=('#a77d68', '#e0b692', '#ffe2bb'), gold=('#835622', '#cf9d46', '#f9dc8a'),
        thread=('#f4cd70', '#fff4c0'), iris='#74e1d9', blush='#ed8e9e',
        mouth=('#251c2e', '#a1586c'), nose='#32223e', fang=('#c6bca2', '#f6efd4'))
R.PALETTES.update(PALETTES)


def draw(enemy, clip, n):
    kind, art = enemy['kind'], enemy['art']
    a = R.Art(kind, clip, n, sy=1-R.timing(clip,n)['fall']*.55)
    if art == 'scarab':
        b = math.sin(n*math.pi/4)*1.2
        for s in (-1, 1):
            for j in range(3):
                x=-14+j*13
                a.c((x,25+b),(x+s*4,10+(j%2)*3),3,1.6,'shade')
        a.e(-5,29+b,23,16,'body')
        a.e(-8,34+b,17,12,'gold',out=False)
        a.line((-19,36+b),(8,29+b),'body0',2)
        a.e(19,29+b,11,11,'body')
        a.eye(22,33+b,4.5,a.T['state'],'iris')
        for s in (-1,1):
            a.c((20+s*5,38+b),(23+s*8,47+b),1.3,1,'gold')
        diamond(a,-9,36+b,5,7,'thread0')
    elif art == 'hound':
        def tail(c):
            a.c((-21,c.cy),(-31,c.cy+8+c.wav),4,2,'body')
            a.poly([(-31,c.cy+9+c.wav),(-37,c.cy+18+c.wav),(-25,c.cy+12)],'thread0')
        def post(c):
            for x in (-8,0,8):
                diamond(a,x,c.cy+7,2,4,'gold1')
            for s in (-1,1):
                a.poly([(c.hx+s*8,c.hy+5),(c.hx+s*10,c.hy+20),(c.hx+s*1,c.hy+9)],'body2')
            a.line((c.hx-9,c.hy-6),(c.hx+10,c.hy-5),'thread0',2)
        quad(a,'body','shade',L=23,Hh=10,base=12,hr=(11,10),hdx=20,hdy=9,
             tail=tail,post=post,ox=-3,pk=.92)
    elif art == 'spinner':
        def pre(c):
            for side in (-1,1):
                a.c((side*10,34),(side*28,20+a.T['sw']*2),2,1,'gold')
                a.line((side*28,20+a.T['sw']*2),(side*22,8),'thread0',1)
            a.e(0,54,18,4,'gold')
            a.e(0,25,18,4,'gold')
        c=floater(a,'body',R=(13,15),cy=40,eye=4.5,pre=pre)
        for j in range(4):
            a.line((-12,31+j*4),(12,31+j*4),'thread0',1)
        spark(a,'thread1',c.x+19,c.y)
    else:
        def pre(c):
            if art == 'doorward':
                a.e(c.far[0]-2,c.far[1]+1,11,18,'gold')
                diamond(a,c.far[0]-2,c.far[1]+1,7,12,'body2')
            elif art == 'king':
                for s in (-1,1):
                    a.band([(s*7,42),(s*25,48),(s*29,12),(s*12,7)],'shade')
                    a.line((s*15,38),(s*25,16),'thread0',2)
            else:
                for s in (-1,1):
                    a.c((s*8,40),(s*21,18),5,2,'shade')
                    a.line((s*10,44),(s*26,25),'thread0',1)
        def post(c):
            if art == 'king':
                a.band([(c.hx-12,c.hy+6),(c.hx-14,c.hy+22),(c.hx-5,c.hy+16),
                        (c.hx,c.hy+26),(c.hx+5,c.hy+16),(c.hx+14,c.hy+22),(c.hx+12,c.hy+6)],'gold')
                diamond(a,c.hx,c.hy+13,3,5,'iris')
            elif art == 'doorward':
                a.band([(c.hx-12,c.hy),(c.hx-13,c.hy+12),(c.hx,c.hy+19),
                        (c.hx+13,c.hy+12),(c.hx+12,c.hy)],'body')
                a.line((c.hx-9,c.hy+3),(c.hx+9,c.hy+3),'thread0',2)
            else:
                a.band([(c.hx-13,c.hy-3),(c.hx-14,c.hy+12),(c.hx,c.hy+21),
                        (c.hx+14,c.hy+12),(c.hx+13,c.hy-3),(c.hx+7,c.hy+7),(c.hx-7,c.hy+7)],'shade')
        def weapon(c):
            x,y=c.near
            a.c((x,y-7),(x+2,y+20),1.9,1.6,'gold')
            if art == 'doorward':
                a.e(x+2,y+23,5,6,'gold')
                a.e(x+2,y+23,2,3,'shade',out=False)
                a.line((x,y-4),(x+8,y-4),'thread0',3)
            else:
                a.e(x+2,y+16,6,3,'gold')
                a.e(x+2,y+27,6,3,'gold')
                for j in range(3):
                    a.line((x-3,y+18+j*3),(x+7,y+18+j*3),'thread0',1)
        humanoid(a,'body','skin',leg='shade',w=13 if art=='king' else 11,legh=12,th=22,
                 hr=(11,10),robe=art=='keeper',pre=pre,post=post,weapon=weapon,
                 pk=.81 if art=='king' else .9,hem='gold' if art=='keeper' else None)
        spark(a,'thread1',29,33)
    return a.done()


maker.ENEMIES=ENEMIES
maker.KINDS=KINDS
maker.PALETTES=PALETTES
maker.PREFIX='valhallasc_nornroot_'
maker.draw=draw

if __name__=='__main__':
    action=sys.argv[1]
    kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='build': maker.build(kinds,replace='--replace' in sys.argv[2:])
    else: getattr(maker,action)(kinds)
