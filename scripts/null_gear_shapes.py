"""Original Nullforged gear. Uses joints/primitives only, no stock gear drawers."""
import math
import numpy as np
import cel_common as cc
import gear_shapes as rig
from cel_common import V, unit

MATS={
 'null_iron':['#10121d','#282a3c','#51566f','#9fa9c2'],
 'null_violet':['#25132f','#4d246d','#9852cb','#d9a7f5'],
 'null_coil':['#123d4a','#1a8496','#61d9da','#cbfff0'],
 'null_warning':['#51491d','#8c8732','#cfcd5b','#f4eda5'],
 'null_cloth':['#171523','#30283f','#554260','#92769f'],
}
PALETTE,COLOR=cc.palette_of({**rig.MATS,**MATS})
I,P,C,Y,S='null_iron','null_violet','null_coil','null_warning','null_cloth'

def disk(ink,c,a,u,r,mat,tone=2):
    ink.plate([c+(a*math.cos(t)+u*math.sin(t))*r for t in np.linspace(0,math.tau,13)[:-1]],mat,tone)

def ring(ink,c,a,u,r,width=2,mat=P):
    for k in range(12):
        t,q=k*math.pi/6,(k+1)*math.pi/6
        d,e=a*math.cos(t)+u*math.sin(t),a*math.cos(q)+u*math.sin(q)
        ink.plate([c+d*r,c+e*r,c+e*(r-width),c+d*(r-width)],mat,2)

def render(cls,theme,kind,gender,clip,facing,k):
    _,ink,p,Q,xf,j,h=rig.pose(cls,gender,clip,facing,k);ink.color=COLOR
    u,a=Q@V(0,0,1),Q@V(1,0,0)
    plate=lambda pts,mat=I,tone=2:ink.plate([xf(q) for q in pts],mat,tone)
    if kind=='armor':
        caster=cls in ('mage','priest');w=9 if cls=='warrior' else 7.5
        cc.torso(ink,xf,S,w,5.8,36,70)
        # Offset furnace doors and a floating heat exchanger, never a stock cuirass.
        plate([(-w,6,67),(3,8,71),(8,7,52),(-3,8,45),(-w,6,51)],P,2)
        plate([(4,7,68),(w+2,5,64),(w,6,43),(4,8,49)],I,3)
        for n in range(4):
            z=52+n*4;plate([(-6,8.3,z),(-4,8.4,z+1),(2,8.4,z+1),(2,8.3,z-1)],C,3)
        for s in (-1,1):
            hem=15 if caster else 30
            plate([(s*3,-6,48),(s*10,-6,53),(s*(18 if s<0 else 13),-9,hem+3),(s*6,-7,hem)],S,1)
            for n in range(3 if caster else 2):
                z=68-n*10
                plate([(s*8,-7,z),(s*(24 if s<0 else 18),-9,z+7),(s*20,-10,z-1),(s*9,-7,z-7)],I,2)
            ink.bone(j['L' if s<0 else 'R']['shoulder'],j['L' if s<0 else 'R']['elbow'],3.8,2.8,S,-.8)
        plate([(-8,7,43),(-1,8,47),(7,7,40),(2,8,34),(-8,6,36)],Y,2)
    elif kind=='headgear':
        H,hd=h['H'],h['hd']-8
        def f(pts,mat=I,tone=2,z=0):ink.poly([H(x*.8,y*.8) for x,y in pts],COLOR[mat][tone],hd+z)
        if cls=='warrior':
            f([(-17,-3),(-18,12),(-10,24),(5,25),(16,14),(17,-4),(10,0),(9,12),(-6,15),(-11,4)],I)
            f([(-16,12),(-21,22),(-17,29),(-8,21)],P,3,-.1)
            f([(-7,9),(10,10),(12,6),(-5,5)],C,3,-.3)
        elif cls=='mage':
            # Open right-angle induction crown with negative space, no pointed hat.
            f([(-20,7),(-20,28),(-9,34),(-3,27),(-14,24),(-14,9)],P)
            f([(5,8),(9,25),(19,29),(23,20),(17,18),(15,8)],I,3,-.1)
            f([(-14,25),(-8,29),(-5,26),(-12,22)],C,3,-.2)
        elif cls=='assassin':
            f([(-17,0),(-14,14),(-3,19),(5,16),(16,18),(20,6),(8,8),(0,11),(-8,7)],S)
            f([(-14,10),(-22,21),(-19,27),(-9,17)],P,3,-.2)
            f([(8,13),(18,19),(23,17),(16,9)],C,2,-.3)
        elif cls=='priest':
            f([(-17,0),(-16,17),(-9,26),(4,29),(16,18),(16,1),(10,4),(9,15),(0,20),(-9,13),(-11,1)],P)
            f([(-2,22),(-3,35),(4,35),(6,26)],I,3,-.1)
            f([(-1,26),(1,32),(3,27),(1,23)],C,3,-.2)
        else:
            f([(-17,4),(-12,17),(1,22),(15,17),(19,4),(8,6),(-7,5)],I)
            f([(-14,14),(-24,20),(-25,28),(-16,25),(-9,17)],P,2,-.2)
            f([(5,17),(15,27),(21,25),(13,16)],C,2,-.3)
    elif kind=='shoulders':
        for s,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*s;r=14 if s<0 else 10
            ring(ink,c+out*9+u*2,out,u,r,4,P if s<0 else I)
            for n in range(4):
                v=c+out*(3+n*4)
                ink.plate([v+u*5,v+out*4+u*(12 if s<0 else 7),v+out*6-u*2,v-u*5],I,2)
                ink.bone(v+u*3,v+out*2+u*7,1,1,C,-2,3)
    elif kind=='gloves':
        for s,key in ((-1,'L'),(1,'R')):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c)
            ink.bone(c,c+v*13,4,5.3,I,-1)
            ink.plate([c-a*5,c+v*12-a*7,c+v*17+a*2,c+v*9+a*6,c+a*4],P,2)
            for n in range(3):ink.bone(c+v*(3+n*4)-a*3,c+v*(3+n*4)+a*3,1,1,C,-2,3)
            ink.plate([c-a*3,c-v*6,c+a*3,c+v*2],Y,2)
    elif kind=='pants':
        for s,key in ((-1,'L'),(1,'R')):
            knee,ankle=j[key]['knee'],j[key]['ankle'];v=unit(ankle-knee)
            ink.bone(j[key]['hip'],knee,4.8,4.2,S,-.8);ink.bone(knee,ankle,4.2,3.8,I,-.8)
            for n in range(3):
                c=knee+v*(n*5)
                ink.plate([c-a*5,c-v*3+a*4,c+v*4+a*6,c+v*7-a*4],P if n%2 else I,2)
                ink.bone(c-a*3,c+a*4,1,1,C,-2,3)
            ink.bone(ankle+V(0,-3,-1),ankle+V(0,7,-2),4.6,3.5,I,-1.4)
    elif kind=='necklace':
        ink.ribbon([xf(q) for q in [(-6,4,71),(-4,8,61),(0,9,52),(5,8,63),(6,4,71)]],1.1,1.1,I,3,-2)
        c=xf((0,9.5,54));ring(ink,c,a,u,5,2,P)
        ink.bone(c-u*4,c+a*3+u*2,1,1,C,-2,3)
    elif kind=='accessory':
        c=j['L']['hand']+Q@V(0,4,1)
        ring(ink,c,a,u,4,1.6,I);ink.plate([c-a*4,c+u*5,c+a*3+u*3,c+a*5-u*2,c-u*4],P,2)
        ink.bone(c-u*2,c+u*2,1,1,C,-2,3)
    elif kind=='weapon':weapon(ink,cls,p,Q,xf,j)
    else:raise ValueError(kind)
    return ink.resolve(clip in ('hurt','die') and k==0)

def weapon(ink,cls,p,Q,xf,j):
    if cls=='hunter':
        c=j['L']['hand'];v=Q@unit(V(*p['bow']));f=unit(c-j['R']['hand']) if p['draw'] else Q@unit(V(*p['aim']))
        if p['dropped']:c,v,f=V(-21,8,3),unit(V(.3,1,0)),V(0,0,1)
        v=unit(v-f*(v@f))
        ink.bone(c-f*11,c+f*13,2.8,2,I,-.6)
        for s in (-1,1):
            for offset in (-2,2):
                pts=[c+v*s*3+f*offset,c+v*s*14+f*(7+offset),c+v*s*24+f*offset]
                ink.ribbon(pts,2,1.4,P,2,-.5)
            end=c+v*s*24;ink.bone(end,c+v*s*18-f*6,1.4,1.4,C,-1,3)
            nock=j['R']['hand'] if p['draw'] and not p['dropped'] else c-f*8
            ink.ribbon([end,nock],.6,.6,C,3,-1,False)
        if p['arrow'] and not p['dropped']:ink.bone(c-f*12,c+f*32,.8,.8,C,-1,3)
        return
    keys='LR' if cls=='assassin' else 'L' if cls=='mage' else 'R'
    for n,key in enumerate(keys):
        hand=j[key]['hand'];direction=p['blade'+key] if cls=='assassin' else p[{'warrior':'blade','priest':'mace','mage':'staff'}[cls]]
        v,a=Q@unit(V(*direction)),Q@V(1,0,0)
        if p['dropped']:hand,v,a=V((n*2-1)*21,-8,3),unit(V(.4,1,0)),unit(V(1,-.4,0))
        at=lambda x,y:hand+a*x+v*y
        ink.bone(at(0,-18 if cls=='mage' else -5),at(0,12),1.8,1.8,I,-.4)
        if cls=='warrior':
            ink.plate([at(-3,6),at(-6,23),at(-3,40),at(2,43),at(1,18),at(7,35),at(11,32),at(7,12)],I,3)
            ink.ribbon([at(0,9),at(-1,26),at(1,39)],1,1,C,3,-1)
            for y in (16,24,32):ink.plate([at(-4,y),at(-10,y+5),at(-4,y+7)],P,2)
        elif cls=='mage':
            ink.bone(at(0,8),at(0,24),1.8,1.8,P,-.4)
            ring(ink,at(0,29),a,v,10,2.7,I)
            # The open coil's gap is real transparency, closed only by cyan spark bars.
            for s in (-1,1):
                ink.plate([at(s*7,25),at(s*13,29),at(s*11,40),at(s*6,37)],P,2)
                ink.bone(at(s*7,33),at(s*4,36),1,1,C,-1,3)
        elif cls=='assassin':
            ink.plate([at(-2,5),at(-5,15),at(-4,25),at(2,30),at(12,27),at(14,19),at(9,15),at(10,22),at(4,25),at(1,21),at(2,7)],I,3)
            for y in (10,17,24):ink.plate([at(-4,y),at(-8,y+2),at(-4,y+5)],P,2)
            ink.bone(at(2,8),at(2,20),.9,.9,C,-1,3)
        else:
            ink.bone(at(0,7),at(0,21),2,2,I,-.4)
            ink.plate([at(-12,18),at(-13,30),at(-6,36),at(9,34),at(13,25),at(10,16)],P,2)
            for x in (-7,0,7):ink.bone(at(x,20),at(x,30),1,1,C,-1,3)
            for s in (-1,1):ink.ribbon([at(s*10,21),at(s*15,10),at(s*8,5)],.9,.9,I,3,-1)
    if cls=='warrior':
        c=(j['L']['hand']+j['L']['elbow'])/2+Q@V(0,4,0);a,u=Q@V(1,0,0),Q@V(0,0,1)
        if p['dropped']:c,a,u=V(-21,8,2),V(1,0,0),V(0,1,0)
        ink.plate([c-a*13+u*13,c+a*8+u*16,c+a*16-u*1,c+a*9-u*17,c-a*9-u*12,c-a*15],I,2)
        ring(ink,c+Q@V(0,1,0),a,u,9,3,P)
        ink.bone(c-a*3-u*9,c+a*4+u*9,1.3,1.3,C,-2,3)
