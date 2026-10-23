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
PALETTES['cf_hildr']=mk(iron=('#202e38','#3c5662','#7895a2','#c7d8dd'),brass=('#5b3527','#a0693a','#dba95d','#ffe1a0'),fire=('#792a35','#c24835','#fa984c','#fff3b5'),skin=('#815249','#bf886a','#edc8a0'),cloth=('#30283e','#62425b','#ae6678'),hair=('#281e27','#674538','#b1885b'),glass=('#4d536b','#a4b1cc','#f5f7fe'),mouth=('#261623','#502735','#945447'),iris='#ffdb8e',nose='#261825',blush='#ce7b68',fang=('#9b96aa','#e8e0cd'))
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
    elif k=='cf_sigrun':
        # A broad foundry matron with a six-toothed mould crown, stone apron,
        # glowing slag seams and a pouring ladle: her own silhouette.
        def furnace(c):
            a.band([(-24,c.top+1),(-27,c.top-10),(-20,c.top-15),(-11,c.top-5),
                    (11,c.top-5),(20,c.top-15),(27,c.top-10),(24,c.top+1)],'iron')
            for side in [-1,1]:
                for j in range(3):
                    a.c((side*18,c.top-2-j*4),(side*24,c.top-4-j*4),1.4,1.4,'fire')
        def face(c):
            a.band([(c.hx-13,c.hy+8),(c.hx+13,c.hy+8),(c.hx+12,c.hy+14),
                    (c.hx-12,c.hy+14)],'brass')
            for dx in [-10,-6,-2,2,6,10]:
                a.c((c.hx+dx,c.hy+12),(c.hx+dx,c.hy+23-abs(dx)*.2),1.5,1.5,'iron')
                a.e(c.hx+dx,c.hy+20-abs(dx)*.2,1.3,1.5,'fire',out=False)
            for side in [-1,1]:
                a.c((c.hx+side*11,c.hy+1),(c.hx+side*16,c.hy-13),3,2,'hair')
                a.e(c.hx+side*16,c.hy-15,3,3,'brass')
            a.band([(-12,c.top-2),(12,c.top-2),(17,c.top-24),(-17,c.top-24)],'iron')
            a.band([(-7,c.top-7),(7,c.top-7),(10,c.top-10),(-10,c.top-10)],'fire')
            for dx in [-5,0,5]: a.c((dx,c.top-8),(dx,c.top-20),1.4,1.4,'iron')
        def ladle(c):
            x,y=c.near
            a.c((x-2,y-14),(x+3,y+18),2.5,2.5,'brass')
            a.e(x+4,y+23,10,6,'iron');a.e(x+4,y+25,7,3,'fire',out=False)
            if clip=='attack': a.c((x+10,y+23),(x+12,y+10),1.8,1,'fire')
        C.humanoid(a,'cloth','skin',w=16,legh=14,th=24,hr=(12,11),armw=5,
                   hand='brass',foot='iron',pk=.83,pre=furnace,post=face,weapon=ladle,blush=None)
    elif k in ('cf_dagfinn','cf_thorbjorg','cf_ragnhild','cf_orm','cf_hildr'):
        def regalia(c):
            y=c.top
            if k=='cf_dagfinn':
                # Twin toothed valve wheels behind broad forge shoulders.
                for side in [-1,1]:
                    x=side*23
                    a.e(x,y+9,11,11,'brass');a.e(x,y+9,7,7,'iron')
                    for j in range(6):
                        t=j*math.tau/6
                        a.c((x,y+9),(x+10*math.cos(t),y+9+10*math.sin(t)),1.3,1.3,'brass')
            elif k=='cf_thorbjorg':
                # Three chimney braids and hanging red-hot brand cages.
                for x in [-20,0,20]:
                    a.c((x*.5,y+6),(x,y+31),3.5,2.5,'hair')
                    a.e(x,y+34,6,9,'brass');a.e(x,y+35,3,6,'fire')
            elif k=='cf_ragnhild':
                # Four organ pipes and a high, asymmetrical sound collar.
                for j,x in enumerate([-24,-16,16,24]):
                    a.c((x,y+4),(x,y+22+(j%2)*8),3.5,3.5,'iron')
                    a.e(x,y+23+(j%2)*8,3,2,'glass')
                a.band([(-24,y+4),(-14,y+19),(14,y+19),(24,y+4)],'cloth')
            elif k=='cf_orm':
                # Huge round cooling tank with cyan sight glass and two water tubes.
                a.e(0,y+9,26,21,'iron');a.e(0,y+12,20,15,'brass')
                a.e(-17,y+18,5,12,'glass');a.e(17,y+18,5,12,'glass')
                for x in [-23,23]: a.c((x,y+3),(x,y-11),3,3,'iron')
            else:
                # Fractured mirror halo, white armour, and a broken final chain.
                for j in range(7):
                    t=math.pi*j/6
                    x=math.cos(t)*25; yy=y+8+math.sin(t)*30
                    a.band([(x-5,yy),(x,yy+10),(x+5,yy),(x,yy-7)],'glass')
                for side in [-1,1]:chain(side*23,y+6,16)
        def face(c):
            x,y=c.hx,c.hy
            if k=='cf_dagfinn':
                a.band([(x-12,y+7),(x-10,y+20),(x,y+28),(x+10,y+20),(x+12,y+7)],'hair')
                a.c((x-10,y-2),(x+10,y-2),2,2,'brass')
            elif k=='cf_thorbjorg':
                a.band([(x-13,y+10),(x-14,y-8),(x-5,y-15),(x+12,y-8),(x+14,y+10),(x+7,y+14),(x+8,y)],'hair')
                for dx in [-7,0,7]:a.e(x+dx,y-5,2,3,'fire')
            elif k=='cf_ragnhild':
                a.band([(x-14,y+5),(x-9,y+14),(x+10,y+16),(x+14,y+5),(x+9,y-2),(x-8,y-2)],'iron')
                a.c((x-8,y+7),(x+8,y+7),2.4,2.4,'glass')
                a.band([(x-11,y+10),(x-10,y+20),(x-3,y+17)],'cloth')
            elif k=='cf_orm':
                a.e(x,y+1,15,14,'brass');a.e(x,y+3,11,10,'iron')
                a.e(x-5,y+5,4,5,'glass');a.e(x+5,y+5,4,5,'glass')
                a.c((x,y-2),(x+2,y-15),3,3,'iron')
            else:
                a.band([(x-13,y+8),(x-9,y+20),(x+9,y+20),(x+13,y+8),(x+7,y+3),(x-7,y+3)],'glass')
                a.e(x-5,y+10,3,2,'iron');a.e(x+5,y+10,3,2,'iron')
                a.c((x-6,y+19),(x+7,y+5),1,1,'brass')
        def tool(c):
            x,y=c.near
            if k=='cf_dagfinn':
                for side in [-1,1]:
                    a.c((x,y-12),(x+side*9,y+23),2,2,'iron')
                    a.c((x+side*9,y+23),(x+side*3,y+30),2.4,2.4,'brass')
            elif k=='cf_thorbjorg':
                a.c((x,y-12),(x,y+23),2.8,2.8,'hair')
                a.e(x,y+26,9,10,'brass');a.e(x,y+27,5,7,'fire')
            elif k=='cf_ragnhild':
                a.c((x,y-8),(x+3,y+24),2.5,2.5,'brass')
                a.e(x+3,y+26,9,6,'iron');a.c((x-3,y+26),(x+8,y+26),2,2,'glass')
            elif k=='cf_orm':
                a.band([(x-8,y-6),(x-9,y+19),(x,y+26),(x+9,y+19),(x+8,y-6)],'iron')
                a.e(x,y+15,5,8,'glass');a.c((x-7,y+23),(x+7,y+23),2,2,'brass')
            else:
                a.band([(x-12,y-5),(x-12,y+20),(x,y+31),(x+12,y+20),(x+12,y-5),(x,y-10)],'brass')
                a.band([(x-8,y-2),(x-8,y+17),(x,y+25),(x+8,y+17),(x+8,y-2)],'glass')
                a.c((x-6,y+20),(x+7,y+1),1.2,1.2,'iron')
        C.humanoid(a,'glass' if k=='cf_hildr' else 'cloth','skin',w=16,legh=14,th=22,hr=(12,11),armw=5,
                   hand='brass',foot='iron',pk=.83,pre=regalia,post=face,weapon=tool,blush=None)
    elif k=='cf_ingot':
        bob=math.sin(n*math.tau/7)*.6
        y=16+bob
        a.band([(-21,y),(-17,y+20),(14,y+20),(22,y), (15,y-5),(-15,y-5)],'iron')
        a.band([(-17,y+18),(14,y+18),(9,y+27),(-11,y+27)],'brass')
        a.band([(-16,y+2),(-13,y+16),(9,y+16),(15,y+2)],'fire')
        for dx in [-9,-3,3,9]: a.c((dx,y+4),(dx-1,y+12),1,1,'iron')
        a.c((-18,y-1),(18,y-1),1.6,1.6,'brass')
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
