#!/usr/bin/env python3
"""Original cel-shaded Wardens, editable in PixelFlow. preview|build|export|verify [kinds]."""
import math
import sys
import cathedral_reliquary_redraw as R
import cel_arch as C
from cel_zone_common import mku as mk
import make_eye_below_sprites as maker
from chained_forge_bosses import ENEMIES
KINDS=[e['kind'] for e in ENEMIES]
PALETTES={k:mk(
    iron=('#202e38','#3c5662','#7895a2','#c7d8dd'),
    brass=('#5b3527','#a0693a','#dba95d','#ffe1a0'),
    fire=('#792a35','#c24835','#fa984c','#fff3b5'),
    skin=('#815249','#bf886a','#edc8a0'),
    cloth=('#30283e','#62425b','#ae6678'),
    hair=('#281e27','#674538','#b1885b'),
    glass=('#17526a','#329eb0','#8de0e3'),
    mouth=('#261623','#502735','#945447'),
    iris='#ffdb8e',nose='#261825',blush='#ce7b68',fang=('#9b96aa','#e8e0cd')) for k in KINDS}
R.PALETTES.update(PALETTES)

def draw(e,clip,n):
    k=e['kind'];a=R.Art(k,clip,n,sy=1-R.timing(clip,n)['fall']*.7);a.pk=.83
    def chain(x,y,length=22):
        for j in range(6):
            a.e(x+math.sin(j*.8+n*.25)*2,y-j*length/6,3.4 if j%2 else 2,2 if j%2 else 3.5,'brass')
            a.e(x+math.sin(j*.8+n*.25)*2,y-j*length/6,1.3,1.2,'iron',out=False)
    if k=='cf_kettil':
        def behind(c):
            for side in [-1,1]:
                chain(side*22,c.top+9,27)
                a.band([(side*11,c.top),(side*25,c.top+4),(side*24,c.top+14),(side*12,c.top+10)],'iron')
        def shackle(c):
            x,y=c.near
            a.e(x,y,10,8,'brass');a.e(x,y+1,5,4,'iron');chain(x-2,y-5,15)
            a.c((x+4,y+8),(x+7,y+22),3,3,'iron')
            a.e(x+7,y+24,7,8,'brass');a.e(x+7,y+24,3.5,4,'iron',out=False)
        def face(c):
            a.band([(c.hx-12,c.hy+6),(c.hx-9,c.hy+16),(c.hx+9,c.hy+16),(c.hx+13,c.hy+6)],'iron')
            a.e(c.hx,c.hy+14,3,4,'fire');a.c((c.hx-10,c.hy-5),(c.hx+9,c.hy-5),2,2,'brass')
        C.humanoid(a,'iron','skin',w=15,legh=16,th=23,hr=(12,11),armw=5,foot='iron',hand='brass',pk=.83,pre=behind,post=face,weapon=shackle,blush=None)
    elif k=='cf_ysolt':
        def bellows(c):
            for side in [-1,1]:
                a.band([(side*9,c.top-6),(side*28,c.top),(side*29,c.top+24),(side*16,c.top+30),(side*12,c.top+12)],'iron')
                for j in range(5):
                    a.c((side*16,c.top+2+j*4),(side*25,c.top-1+j*4),1.6,1.6,'cloth')
                a.c((side*20,c.top+26),(side*21,c.top+37),3,3,'brass')
                a.e(side*21,c.top+38,5,2,'glass')
        def face(c):
            a.band([(c.hx-12,c.hy+7),(c.hx-10,c.hy+20),(c.hx,c.hy+26),(c.hx+10,c.hy+20),(c.hx+12,c.hy+7)],'iron')
            for side in [-1,1]:
                a.c((c.hx+side*12,c.hy),(c.hx+side*20,c.hy-14),3,1,'hair')
            a.band([(c.hx-9,c.hy-2),(c.hx+9,c.hy-2),(c.hx+7,c.hy-10),(c.hx-7,c.hy-10)],'brass')
            for dx in [-4,0,4]:a.c((c.hx+dx,c.hy-4),(c.hx+dx,c.hy-8),.8,.8,'glass')
        def wand(c):
            x,y=c.near
            a.c((x,y-9),(x,y+18),2,2,'iron');a.e(x,y+21,7,8,'glass');a.e(x,y+21,3,4,'iron')
        C.humanoid(a,'cloth','skin',w=10,legh=17,th=25,hr=(11,11),armw=3.5,hand='brass',foot='iron',pk=.83,pre=bellows,post=face,weapon=wand,blush=None)
    else:
        def anvil(c):
            y=c.top
            a.band([(-24,y+2),(-27,y+10),(-11,y+10),(-10,y+4),(13,y+4),(24,y+12),(26,y+4),(16,y-1),(11,y-10),(-12,y-10),(-16,y-1)],'iron')
            a.c((-10,y-4),(10,y-4),1.5,1.5,'fire')
        def face(c):
            a.band([(c.hx-10,c.hy-2),(c.hx+9,c.hy-2),(c.hx+8,c.hy-12),(c.hx,c.hy-19),(c.hx-7,c.hy-12)],'hair')
            for dx in [-5,0,5]:a.c((c.hx+dx,c.hy-5),(c.hx+dx*.7,c.hy-13),1,1,'brass')
            a.band([(c.hx-13,c.hy+8),(c.hx-9,c.hy+19),(c.hx+9,c.hy+19),(c.hx+13,c.hy+8)],'brass')
            a.e(c.hx-5,c.hy+5,5,3,'glass');a.e(c.hx+6,c.hy+5,5,3,'glass')
        def hammer(c):
            x,y=c.near
            a.c((x,y-10),(x+2,y+21),2.8,2.8,'hair')
            a.band([(x-12,y+16),(x+12,y+16),(x+12,y+30),(x-12,y+30)],'iron')
            a.c((x-8,y+22),(x+7,y+22),1.8,1.8,'fire')
            for dx in [-9,9]:a.e(x+dx,y+26,1.8,1.8,'brass',out=False)
        C.humanoid(a,'cloth','skin',w=17,legh=15,th=22,hr=(12,11),armw=6,hand='skin',foot='iron',pk=.83,pre=anvil,post=face,weapon=hammer,blush=None)
    return a.done()

maker.ENEMIES=ENEMIES;maker.KINDS=KINDS;maker.PALETTES=PALETTES
maker.PREFIX='valhallasc_chained_forge_warden_';maker.draw=draw
if __name__=='__main__':
    action=sys.argv[1];kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='build':maker.build(kinds,replace='--replace' in sys.argv[2:])
    else:getattr(maker,action)(kinds)
