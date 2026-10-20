#!/usr/bin/env python3
"""Six original giant clockwork silhouettes, editable 34-frame PixelFlow sprites."""
import math
import sys
import cathedral_reliquary_redraw as R
from cel_zone_common import mku as mk
import make_eye_below_sprites as maker
from blackhour_content import ENEMIES

KINDS=[e['kind'] for e in ENEMIES]
PALETTES={e['kind']:mk(iron=('#10121e','#242535','#44465d','#8994ae'),
    violet=('#251333','#522d76','#9959d5','#d3a6ff'),
    glow=('#14515d','#249baf','#66e5e1','#d0fff4'),
    brass=('#46351f','#857035','#c5b66c','#f0e3ae'),
    black=('#0d1019','#1b2330','#334455','#62768a'),
    iris='#b6fff6',mouth=('#1a1424','#633755'),fang=('#8b9aae','#eef7ff'),
    skin=('#283142','#5b7083','#a2bcc7'),hair=('#23152f','#704d8d','#b593d1'),
    blush='#94679c',nose='#303948') for e in ENEMIES}
R.PALETTES.update(PALETTES)

def draw(e,clip,n):
    a=R.Art(e['kind'],clip,n,sy=1-R.timing(clip,n)['fall']*.65)
    a.pk=.84
    T=a.T;b=T['bob'];sw=T['sw'];hit=T['strike'];art=e['art']
    def gear(x,y,r,teeth=10,mat='iron'):
        pts=[]
        for k in range(teeth*4):
            t=math.tau*k/(teeth*4);rr=r*(1 if k%4 in (1,2) else .82)
            pts.append((x+rr*math.cos(t),y+rr*math.sin(t)))
        a.band(pts,mat);a.e(x,y,r*.60,r*.60,'black');a.e(x,y,r*.31,r*.31,'glow')
    if art=='hauler':
        for s in (-1,1):
            for k in range(2):
                x=s*(16+k*7);y=20-k*5
                a.c((s*13,30+b),(x,14+sw*(1 if k else -1)),5,3,'iron')
                a.e(x,6,8,5,'black')
        a.e(0,32+b,25,18,'iron')
        a.band([(-21,35+b),(-18,59+b),(14,62+b),(25,43+b),(21,30+b)],'violet')
        for x,y in [(-13,58),(-2,62),(11,60)]:
            a.c((x,y+b),(x-3,y+16+b),3,4,'iron');a.e(x-3,y+16+b,4,2,'glow')
        a.e(0,37+b,15,11,'black')
        for x in (-9,-3,3,9):a.c((x,30+b),(x,44+b),1.3,1.3,'glow')
        a.e(21,25+b+hit*4,11,10,'iron');a.eye(24,29+b+hit*4,4)
        for x in (15,24):a.band([(x,21+b),(x+4,21+b),(x+2,15+b)],'brass')
    elif art=='breaker':
        for s in (-1,1):
            a.c((s*9,31+b),(s*14,8+sw*s),6,5,'black');a.e(s*15,5,10,5,'iron')
            a.c((s*15,52+b),(s*(25+hit*4),31+b),8,6,'iron')
            gear(s*(25+hit*4),27+b,10,8)
        a.band([(-18,27+b),(-20,58+b),(-10,69+b),(14,65+b),(20,48+b),(15,26+b)],'iron')
        a.band([(-11,54+b),(-6,68+b),(10,65+b),(13,50+b)],'violet')
        a.eye(1,59+b,6)
        a.c((-6,43+b),(9+sw*2,22+b),2,2,'brass');a.e(9+sw*2,21+b,8,10,'violet')
        for s in (-1,1):a.band([(s*13,58+b),(s*28,66+b),(s*26,49+b)],'violet')
    elif art=='coil':
        cy=35+b
        for s in (-1,1):
            for k in range(3):
                x=s*(11+k*7);high=65-k*9
                a.c((x,cy-7),(x,high+b),3.5,3.5,'iron')
                a.e(x,high+b,4,2,'glow')
                a.c((s*4,cy),(x,cy-7),2,2,'violet')
        gear(0,cy,18,12,'violet');a.eye(0,cy+1,7)
        a.band([(-13,cy-11),(-6,8),(0,15),(7,7),(14,cy-11)],'black')
        for x in (-7,7):a.c((x,20),(x+sw*2,5),1,1,'glow')
    elif art=='bell':
        for s in (-1,1):
            a.c((s*11,27+b),(s*16,7),7,5,'iron');a.e(s*17,5,9,5,'black')
            a.c((s*22,49+b),(s*29,26+hit*6),7,7,'iron')
            a.band([(s*23,34+hit*6),(s*36,33+hit*6),(s*35,16+hit*6),(s*24,17+hit*6)],'violet')
        a.band([(-28,27+b),(-20,47+b),(-16,67+b),(-5,74+b),(8,73+b),(18,63+b),(21,45+b),(29,27+b)],'violet')
        a.e(0,26+b,29,7,'iron');a.e(0,27+b,22,3,'black')
        a.c((0,35+b),(sw*2,17+b),3,3,'brass');a.e(sw*2,16+b,7,7,'glow')
        a.eye(-6,56+b,5);a.eye(7,56+b,5)
        a.c((-8,71+b),(-8,82+b),3,3,'iron');a.c((8,71+b),(8,82+b),3,3,'iron');a.c((-8,82+b),(8,82+b),3,3,'iron')
    elif art=='conductor':
        cy=40+b
        for s in (-1,1):
            for k in range(3):
                a.c((s*13,cy+5),(s*(25+k*4),20+k*15),2,2,'glow')
                a.e(s*(25+k*4),20+k*15,4,7,'iron')
            a.band([(s*8,37+b),(s*21,30+b),(s*28,8),(s*13,14)],'violet')
        a.e(0,cy,16,23,'black');gear(0,cy+17,20,12,'violet');a.eye(0,cy+17,7)
        a.band([(-12,34+b),(-9,15+b),(0,9+b),(10,15+b),(13,34+b)],'iron')
        for y in (26,33,40):a.c((-8,y+b),(8,y+b),1,1,'glow')
    else:
        cy=43+b
        for s in (-1,1):
            a.c((s*12,cy-16),(s*22,6),5,4,'iron');a.e(s*23,4,10,4,'black')
            a.c((s*24,cy),(s*32,17+hit*8),5,5,'violet')
            a.e(s*32,17+hit*8,7,7,'glow')
        gear(0,cy,34,12,'violet');a.e(0,cy,25,25,'black')
        for k in range(12):
            t=math.tau*k/12;a.c((math.sin(t)*20,cy+math.cos(t)*20),(math.sin(t)*23,cy+math.cos(t)*23),1,1,'brass')
        angle=-.8+hit*.6
        a.c((0,cy),(math.sin(angle)*19,cy+math.cos(angle)*19),2,1,'glow')
        a.c((0,cy),(-15,cy-7),2,1,'glow');a.eye(0,cy,6)
        a.band([(-12,cy+29),(-9,cy+39),(0,cy+32),(8,cy+38),(13,cy+28)],'iron')
    return a.done()

maker.ENEMIES=ENEMIES;maker.KINDS=KINDS;maker.PALETTES=PALETTES
maker.PREFIX='valhallasc_blackhour_';maker.draw=draw
if __name__=='__main__':
    action=sys.argv[1];kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='build':maker.build(kinds,replace='--replace' in sys.argv[2:])
    else:getattr(maker,action)(kinds)
