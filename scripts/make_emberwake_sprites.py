#!/usr/bin/env python3
"""Seven original cel silhouettes, 34 editable frames each, through PixelFlow.

preview | build [--replace] | export | verify. Export preserves editor changes.
"""
import math
import sys
import cathedral_reliquary_redraw as R
from cel_zone_common import mku as mk
import make_eye_below_sprites as maker
from emberwake_content import ENEMIES

KINDS=[e['kind'] for e in ENEMIES]
PALETTES={e['kind']:mk(
    rock=('#252332','#42404d','#656370','#9c9da9'),
    fire=('#742e29','#bc5034','#f19650','#ffdc8b'),
    glass=('#243143','#3c647b','#6da9bd','#b4e3e7'),
    skin=('#7c4a43','#bb7e65','#efb494'),
    iron=('#292d39','#505c6c','#8799a8','#c5d0d5'),
    cloth=('#452e43','#784455','#b97469'),
    gold=('#80502e','#c08a46','#f1cc75'),iris='#ffdba0') for e in ENEMIES}
R.PALETTES.update(PALETTES)

def draw(e,clip,n):
    a=R.Art(e['kind'],clip,n,sy=1-R.timing(clip,n)['fall']*.7)
    a.pk=.88
    T=a.T;b=T['bob']+math.sin(n*.79)*.4;sw=T['sw'];hit=T['strike'];kind=e['kind'][3:]
    def leg(x,y=25):
        up=max(0,sw*(1 if x>0 else -1))*4 if clip=='walk' else 0
        a.c((x*.75,y+b),(x,7+up),4,3,'rock');a.e(x+2,5+up,6,3,'rock')
    def tooth(x,y):a.band([(x-2,y),(x+2,y),(x+1,y-7)],'gold')
    def chain(x,y,count=4):
        for j in range(count):
            a.e(x+math.sin(j*.8+sw*.2)*3,y-j*7,3.8,4.7,'iron')
            a.e(x+math.sin(j*.8+sw*.2)*3,y-j*7,1.4,2.3,'rock',out=False)
    if kind=='ashback':
        for x in [-20,-10,12,23]:leg(x,21)
        a.c((-18,25+b),(-33,14+sw),7,2,'fire')
        a.e(-4,26+b,24,12,'fire');a.e(22+hit*3,30+b,13,11,'rock')
        for x,y in [(-18,39),(-8,43),(2,41),(11,37)]:a.band([(x-5,y-5+b),(x,y+10+b),(x+6,y-5+b)],'rock')
        a.eye(26+hit*3,34+b,4);a.c((26,21+b),(34,21+b),1,1,'fire')
    elif kind=='glasswing':
        cy=40+b
        for s in [-1,1]:
            a.band([(s*5,cy),(s*(31+sw*3),cy+26),(s*35,cy-9),(s*13,cy-17)],'glass')
            a.c((s*7,cy),(s*29,cy+19),1.1,1,'fire')
        a.e(0,cy-5,8,19,'rock');a.e(0,cy+15,11,10,'rock')
        a.eye(-4,cy+17,3);a.eye(5,cy+17,3)
        for s in [-1,1]:a.c((s*5,cy+23),(s*11,cy+33),1.4,1,'gold')
    elif kind=='slagjaw':
        for x in [-25,-12,13,26]:leg(x,20)
        a.e(-3,25+b,28,18,'rock')
        for x in [-22,-10,2,14]:a.band([(x-5,34+b),(x,52+b),(x+7,34+b)],'iron')
        a.e(23,22+b+hit*4,14,11,'fire');a.eye(26,27+b+hit*4,4)
        for x in [20,26,32]:tooth(x,17+b+hit*4)
    elif kind=='cinderhorn':
        for x in [-22,-10,13,24]:leg(x,32)
        a.e(-5,34+b,23,16,'rock');a.e(21+hit*3,44+b,14,14,'fire')
        for x in [9,26]:
            a.e(x,55+b,9,10,'iron');a.e(x+2,55+b,4,5,'fire',out=False)
        a.eye(27+hit*3,45+b,4)
        a.c((-24,38+b),(-33,48+b),4,2,'fire')
    elif kind=='chainmaw':
        for x in [-22,-10,15,26]:leg(x,29)
        a.e(-3,31+b,27,21,'rock');a.e(22+hit*3,31+b,15,15,'iron')
        for x in [-17,-5,7]:a.c((x-4,20+b),(x+3,47+b),2,2,'fire')
        chain(-22,43+b);chain(6,52+b,5)
        a.eye(26+hit*3,37+b,5)
        for x in [20,28,34]:tooth(x,22+b)
    elif kind=='bellows':
        for x in [-12,13]:leg(x,25)
        a.band([(-18,15+b),(-23,45+b),(-15,62+b),(14,62+b),(23,44+b),(18,15+b)],'cloth')
        a.e(0,62+b,13,12,'skin');a.eye(-4,65+b,3);a.eye(5,65+b,3)
        a.band([(-16,73+b),(-7,83+b),(1,77+b),(11,84+b),(16,72+b)],'iron')
        for s in [-1,1]:
            a.c((s*16,46+b),(s*29,36+b+hit*5),5,4,'skin')
            a.e(s*28,35+b+hit*5,8,14,'iron')
            for y in [28,34,40]:a.c((s*22,y+b),(s*34,y+b),1,1,'fire')
        a.band([(-11,47+b),(11,47+b),(8,21+b),(-8,21+b)],'fire')
    else:
        cy=40+b
        for s in [-1,1]:
            a.c((s*10,cy-14),(s*15,7),6,4,'rock');a.e(s*17,5,8,4,'iron')
            a.c((s*20,cy+4),(s*(30+hit*3),cy-13),6,5,'rock')
            a.e(s*(30+hit*3),cy-13,7,8,'fire')
        a.e(0,cy,22,24,'rock');a.e(0,cy+21,16,15,'fire')
        a.eye(-6,cy+24,4);a.eye(7,cy+24,4)
        a.band([(-20,cy+31),(-20,cy+44),(-8,cy+36),(1,cy+47),(10,cy+36),(21,cy+43),(19,cy+31)],'gold')
        chain(-12,cy+10);chain(13,cy+8)
        a.e(0,cy-3,9,11,'fire')
    return a.done()

maker.ENEMIES=ENEMIES;maker.KINDS=KINDS;maker.PALETTES=PALETTES
maker.PREFIX='valhallasc_emberwake_';maker.draw=draw
if __name__=='__main__':
    action=sys.argv[1];kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='build':maker.build(kinds,replace='--replace' in sys.argv[2:])
    else:getattr(maker,action)(kinds)
