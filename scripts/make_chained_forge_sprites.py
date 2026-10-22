#!/usr/bin/env python3
"""Four original raid elite silhouettes. preview | build | export | verify [kinds].

96x96, anchor (48,90), five clips/34 frames. PixelFlow is the editable
source of every exported atlas. Existing kinds are never rebuilt implicitly.
"""
import math
import sys
import cathedral_reliquary_redraw as R
import cel_arch as C
from cel_zone_common import mku as mk
import make_eye_below_sprites as maker
from chained_forge_content import ENEMIES

KINDS=[e['kind'] for e in ENEMIES]
PALETTES={k:mk(
    rock=('#242330','#45414e','#696270','#a39ba8'),
    iron=('#243442','#435c6c','#7997a4','#c1d6db'),
    fire=('#782e2c','#c04c32','#f39750','#ffe09a'),
    gold=('#80522e','#bb8845','#f6d484'),
    cloth=('#302840','#59415c','#9c667b'),
    glass=('#174350','#2e7c88','#64c6cf','#b3f2e9'),
    skin=('#80554c','#b47f67','#eac3a1'),
    mouth=('#251824','#4c2832','#89413e'),
    iris='#ffdb8b',nose='#251925',blush='#cb7564',fang=('#9595ac','#e2d9cb')) for k in KINDS}
R.PALETTES.update(PALETTES)

def draw(e,clip,n):
    kind=e['kind'];a=R.Art(kind,clip,n,sy=1-R.timing(clip,n)['fall']*.7)
    a.pk=.86
    def rivets(x,y):
        for dx in [-7,7]:
            for dy in [-6,6]:a.e(x+dx,y+dy,1.4,1.4,'gold',out=False)
    def stack(x,y,height=20):
        a.c((x,y),(x,y+height),4,4,'iron')
        a.e(x,y+height,6,3,'fire')
        for j in range(3):a.e(x+math.sin(n*.7+j)*2,y+height+5+j*4,3-j*.5,2,'rock',out=False)
    def hammer(c):
        x,y=c.near
        a.c((x-4,y-10),(x+1,y+20),2,2,'iron')
        a.band([(x-10,y+13),(x+11,y+13),(x+11,y+25),(x-10,y+25)],'iron')
        a.c((x-6,y+18),(x+7,y+18),1.5,1.5,'fire');rivets(x,y+19)
    if kind=='cf_brute':
        def armor(c):
            a.band([(-18,c.top),(-8,c.top+7),(12,c.top+7),(20,c.top),(13,c.top-10),(-13,c.top-10)],'iron')
            stack(-13,c.top+1,12)
        C.humanoid(a,'rock','rock',w=16,legh=15,th=24,hr=(13,12),armw=5,
            hand='fire',foot='iron',pk=.86,pre=armor,weapon=hammer,blush=None)
    elif kind=='cf_crawler':
        def vents(c):
            for x,y in [(-19,c.cy+14),(-5,c.cy+20),(6,c.cy+12)]:stack(x,y,13)
            for x in [-22,-13,-4]:a.c((x,c.cy-1),(x+6,c.cy+8),1.8,1.8,'fire')
        C.spider(a,'iron','rock','iron',R=(18,13),base=23,legspan=8,thickness=3,pk=.88,pre=vents,blush=None)
    elif kind=='cf_caster':
        b=C.parts(a)[3];cy=34+b
        for s in [-1,1]:
            a.c((s*12,cy+25),(s*23,cy+10),3,3,'iron')
            a.c((s*23,cy+10),(s*18,cy-6),3,3,'iron')
            for j in range(3):a.e(s*(9+j*4),cy-20-j*4,3,2,'fire')
        a.band([(-21,cy+11),(21,cy+11),(15,cy-13),(-15,cy-13)],'iron')
        a.e(0,cy+12,21,6,'fire');a.e(0,cy+14,15,3,'gold',out=False)
        a.e(0,cy+32,12,13,'fire');a.eye(-4,cy+34,4);a.eye(6,cy+34,4)
        a.band([(-13,cy+43),(-21,cy+58),(-7,cy+48),(0,cy+60),(9,cy+48),(20,cy+56),(13,cy+43)],'iron')
        for x in [-10,0,10]:a.c((x,cy+4),(x*.7,cy-8),1,1,'glass')
        C.spark(a,'fire',23,cy+20,count=3)
    elif kind=='cf_sentry':
        def shield(c):
            x,y=c.near
            a.band([(x-10,y+18),(x+9,y+18),(x+13,y+2),(x,y-16),(x-13,y+2)],'rock')
            a.band([(x-6,y+12),(x+5,y+12),(x+8,y+2),(x,y-9),(x-8,y+2)],'glass')
            a.c((x,y-7),(x,y+11),1.4,1.4,'gold')
        def helm(c):
            a.band([(c.hx-13,c.hy+5),(c.hx-8,c.hy+16),(c.hx+8,c.hy+16),(c.hx+14,c.hy+4)],'iron')
            a.c((c.hx,c.hy+15),(c.hx,c.hy+25),3,1,'glass')
        C.humanoid(a,'iron','rock',w=14,legh=17,th=23,hr=(12,11),pk=.9,pre=helm,weapon=shield,blush=None)
    return a.done()

maker.ENEMIES=ENEMIES;maker.KINDS=KINDS;maker.PALETTES=PALETTES
maker.PREFIX='valhallasc_chained_forge_';maker.draw=draw
if __name__=='__main__':
    action=sys.argv[1];kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='build':maker.build(kinds,replace='--replace' in sys.argv[2:])
    else:getattr(maker,action)(kinds)
