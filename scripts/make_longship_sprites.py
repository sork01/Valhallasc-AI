#!/usr/bin/env python3
"""Original Keelbound cel sprites; all clips saved and re-exported through PixelFlow."""
import math
import sys
import cathedral_reliquary_redraw as R
from cel_arch import humanoid
from cel_zone_common import mku as mk
import make_eye_below_sprites as maker
from longship_content import ENEMIES

KINDS=[e['kind'] for e in ENEMIES]
PALETTES={e['kind']:mk(body=('#193f43','#2d7778','#62b4a4','#b3ebca'),
    cloth=('#17283e','#2a405c','#496282','#8ba6bd'),
    copper=('#593e32','#9c704a','#d3a566','#f4d29a'),
    rope=('#6d5941','#b39b70','#eed6a5'),
    coral=('#6b3046','#bd5360','#f18e81'),
    skin=('#487d80','#83bbb2','#c6e7d5'),
    hair=('#243948','#467480','#77adaf'),
    glow=('#318e9b','#72e8ce','#dcfff0'),iris='#40b7cd',blush='#e2908a',nose='#29444e',
    fang=('#b9b399','#f9edce'),mouth=('#2a223b','#ad5e6c')) for e in ENEMIES}
R.PALETTES.update(PALETTES)

def draw(e,clip,n):
    art=e['art'];a=R.Art(e['kind'],clip,n,sy=1-R.timing(clip,n)['fall']*.62)
    T=a.T;b=T['bob'];swing=T['sw'];strike=T['strike']
    if art in ('crab','cargomaw'):
        big=art=='cargomaw';cy=25+b;w=21 if big else 15
        for side in (-1,1):
            for j in range(3):
                y=cy-8+j*6;ex=side*(w+12);ey=6+j*3+swing*(2 if j%2 else -2)
                a.c((side*w*.6,y),(ex,ey+7),2.7,2,'body');a.c((ex,ey+7),(ex+side*3,ey),2,1,'copper')
            x=side*(w+8);y=cy+12+strike*9
            a.c((side*w,cy+4),(x,y-3),4,4,'body')
            a.e(x,y,7,9,'copper');a.poly([(x-side*2,y+2),(x+side*5,y+12),(x+side*6,y+1)],'body2')
        a.e(0,cy,w,14,'body')
        if big:
            a.band([(-21,cy+2),(-24,cy+27),(19,cy+32),(23,cy+6)],'copper')
            a.band([(-24,cy+27),(-17,cy+38),(15,cy+41),(19,cy+32)],'cloth')
            for x in (-12,10):a.c((x,cy+5),(x-2,cy+34),2,2,'rope')
            a.e(0,cy+20,6,7,'copper');a.e(0,cy+20,3,4,'glow')
            a.poly([(-15,cy+6),(-12,cy-4),(-7,cy+1),(-2,cy-5),(4,cy+1),(9,cy-3),(15,cy+7)],'mouth0')
            for x in (-10,-2,7):a.poly([(x,cy+6),(x+3,cy+6),(x+1,cy)],'fang1')
        else:
            a.e(0,cy+4,12,10,'copper')
            a.line((-7,cy+7),(7,cy+2),'rope1',2)
        for side in (-1,1):
            a.c((side*7,cy+9),(side*8,cy+18),2,2,'body');a.eye(side*8,cy+18,3.5)
    elif art=='lantern':
        cy=36+b+math.sin(n*.9)*1.5
        a.c((-5,cy+19),(-7,cy+29),2,2,'copper');a.c((-7,cy+29),(7,cy+29),2,2,'copper');a.c((7,cy+29),(5,cy+19),2,2,'copper')
        a.e(0,cy,15,19,'copper');a.e(0,cy,11,15,'glow')
        for x in (-8,8):a.c((x,cy-13),(x,cy+13),1.5,1.5,'copper')
        a.band([(-15,cy+16),(-10,cy+24),(10,cy+24),(15,cy+16)],'cloth')
        a.e(0,cy-18,17,4,'copper')
        for side in (-1,1):
            a.c((side*6,cy-20),(side*(10+swing),cy-29),2,1,'rope')
            a.eye(side*4,cy+1,3)
    else:
        captain=art=='captain';bosun=art=='bosun'
        def pre(c):
            if captain:
                for side in (-1,1):
                    a.band([(side*7,42),(side*21,43),(side*26,11),(side*11,17)],'cloth')
                    a.line((side*15,39),(side*20,16),'copper2',2)
            if bosun:
                a.e(-19,34,9,14,'rope');a.e(-19,34,4,8,'cloth')
        def post(c):
            hx,hy=c.hx,c.hy
            if captain:
                a.e(hx,hy+9,18,4,'cloth')
                a.band([(hx-17,hy+9),(hx-20,hy+20),(hx-5,hy+16),(hx,hy+25),(hx+8,hy+17),(hx+18,hy+22),(hx+16,hy+8)],'cloth')
                a.line((hx-17,hy+20),(hx,hy+25),'copper2',2);a.line((hx,hy+25),(hx+18,hy+22),'copper2',2)
                a.e(hx,hy+17,3,3,'coral')
                a.c((hx-10,hy-1),(hx-12,hy-13),3,1,'hair');a.c((hx+10,hy-1),(hx+13,hy-13),3,1,'hair')
            elif bosun:
                a.band([(hx-12,hy+7),(hx-10,hy+19),(hx+11,hy+19),(hx+14,hy+7)],'coral')
                a.line((hx-10,hy+10),(hx+11,hy+10),'rope2',2)
            else:
                a.band([(hx-12,hy+6),(hx-10,hy+17),(hx+10,hy+17),(hx+13,hy+6)],'cloth')
                a.c((hx-12,hy+5),(hx+12,hy+5),2,2,'rope')
            a.line((-6,29),(6,29),'rope2',2)
        def weapon(c):
            x,y=c.near
            if captain:
                a.c((x,y-5),(x,y+24),2,2,'copper')
                a.e(x,y+27,5,5,'copper');a.e(x,y+27,2,2,'glow')
                a.c((x-10,y+9),(x+10,y+9),2,2,'copper')
                a.c((x-13,y-2),(x,y-9),3,3,'copper');a.c((x,y-9),(x+13,y-2),3,2,'copper')
                a.poly([(x-13,y-2),(x-14,y+5),(x-8,y+1)],'copper2');a.poly([(x+13,y-2),(x+14,y+5),(x+8,y+1)],'copper2')
            elif bosun:
                a.c((x,y-4),(x,y+15),3,2,'copper');a.c((x,y+15),(x+8,y+19),2,2,'copper');a.c((x+8,y+19),(x+11,y+13),2,1,'copper')
                a.c((x-2,y-6),(x-9,y-15),2,1,'rope')
            else:
                a.c((x,y-5),(x+3,y+17),2,2,'rope');a.band([(x+1,y+6),(x+10,y+23),(x+6,y+26),(x-3,y+11)],'copper')
        humanoid(a,'cloth','skin',leg='cloth',w=14 if bosun else 11,legh=12,th=22,hr=(11,10),
                 pre=pre,post=post,weapon=weapon,pk=.77 if captain else .86)
    return a.done()

maker.ENEMIES=ENEMIES;maker.KINDS=KINDS;maker.PALETTES=PALETTES
maker.PREFIX='valhallasc_longship_';maker.draw=draw
if __name__=='__main__':
    action=sys.argv[1];kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='build':maker.build(kinds,replace='--replace' in sys.argv[2:])
    else:getattr(maker,action)(kinds)
