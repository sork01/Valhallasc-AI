"""Original furnace/chain equipment; joint-fitted 3D cel shapes, no stock drawers."""
import math
import numpy as np
import cel_common as cc
import gear_shapes as rig
from cel_common import V, unit

MATS = {
    'forge': ['#201b24', '#493946', '#866873', '#c7acaa'],
    'hot': ['#832318', '#cf4b21', '#ff9439', '#fff0ae'],
    'brass': ['#4d3024', '#97613b', '#dca36a', '#ffe4b5'],
    'clothforge': ['#211d2e', '#3c3146', '#695168', '#9e8099'],
}
PALETTE, COLOR = cc.palette_of({**rig.MATS, **MATS})
HOOD_MATS={
    'hood':['#1b090e','#391015','#632027','#943739'],
    'hoodtrim':['#5a201e','#97392e','#cd5540','#f18a58'],
}
HOOD_PALETTE,HOOD_COLOR=cc.palette_of({**rig.MATS,**MATS,**HOOD_MATS})
MIGHT_MATS={
    'forge':['#252f26','#46513b','#748063','#b9bd8c'],
    'hot':['#102e2e','#24534f','#3e8374','#83baa1'],
    'brass':['#423c20','#82733c','#bba958','#e9db92'],
    'clothforge':['#1e2925','#354038','#58634a','#8c9771'],
}
MIGHT_PALETTE,MIGHT_COLOR=cc.palette_of({**rig.MATS,**MIGHT_MATS})
MIGHT_WEAPON_PALETTE,MIGHT_WEAPON_COLOR=cc.palette_of({**rig.MATS,**MIGHT_MATS,'hot':MATS['hot']})
BLOOD_MATS={
    'forge':['#12141c','#24222b','#3c353f','#625660'],
    'hot':['#5d0f15','#961c24','#c93236','#f36550'],
    'brass':['#360d14','#77151f','#b5242d','#ed4c49'],
    'clothforge':['#1a111c','#321d2a','#53303c','#79505a'],
}
BLOOD_PALETTE,BLOOD_COLOR=cc.palette_of({**rig.MATS,**BLOOD_MATS})
HUNT_MATS={
    'forge':['#241d13','#514027','#82683e','#b6a16b'],
    'hot':['#24371c','#4f7029','#8ca849','#d3db7e'],
    'brass':['#493415','#967024','#d2aa3b','#ffe18a'],
    'clothforge':['#3d4240','#777f74','#afb3a0','#e1e1c5'],
}
HUNT_PALETTE,HUNT_COLOR=cc.palette_of({**rig.MATS,**HUNT_MATS})
HUNT_WEAPON_PALETTE,HUNT_WEAPON_COLOR=cc.palette_of({**rig.MATS,**HUNT_MATS,'hot':MATS['hot']})
MAGE_MATS={
    'forge':['#16182c','#302c4d','#504569','#807093'],
    'hot':['#351567','#7133b0','#ae6aed','#ecd2ff'],
    'brass':['#4c361e','#947044','#d4af68','#ffe5a4'],
    'clothforge':['#393744','#696576','#a09aaa','#d4ced9'],
}
MAGE_PALETTE,MAGE_COLOR=cc.palette_of({**rig.MATS,**MAGE_MATS})
MAGE_WEAPON_PALETTE,MAGE_WEAPON_COLOR=cc.palette_of({**rig.MATS,**MAGE_MATS,'hot':MATS['hot']})
PRIEST_MATS={
    'forge':['#55544e','#8e8d7d','#c8c6ad','#f3efd2'],
    'hot':['#195969','#459ca7','#83e7e9','#e9fffa'],
    'brass':['#574729','#a3894f','#d1bd7b','#fff0b8'],
    'clothforge':['#15344a','#275f7e','#4c9cb3','#9ad0da'],
}
PRIEST_PALETTE,PRIEST_COLOR=cc.palette_of({**rig.MATS,**PRIEST_MATS})
PRIEST_WEAPON_PALETTE,PRIEST_WEAPON_COLOR=cc.palette_of({**rig.MATS,**PRIEST_MATS,'hot':MATS['hot']})
def palette_for(task):
    if task['className']=='priest':return PRIEST_WEAPON_PALETTE if task['kind']=='weapon' else PRIEST_PALETTE
    if task['className']=='mage':return MAGE_WEAPON_PALETTE if task['kind']=='weapon' else MAGE_PALETTE
    if task['className']=='hunter':return HUNT_WEAPON_PALETTE if task['kind']=='weapon' else HUNT_PALETTE
    if task['className']=='warrior' and task['kind']=='weapon':return MIGHT_WEAPON_PALETTE
    if task['className']=='assassin' and task['kind'] in ('armor','shoulders','gloves'):
        return BLOOD_PALETTE
    if task['className']=='warrior' and task['kind'] in ('armor','headgear','shoulders','gloves'):
        return MIGHT_PALETTE
    return HOOD_PALETTE if task['className']=='assassin' and task['kind']=='headgear' else PALETTE

I, E, B, S = 'forge', 'hot', 'brass', 'clothforge'
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')

class ForgeInk(cc.Ink):
    def plate(self, points, mat, tone=2, detail=False):
        proj=[self.project(q) for q in points]
        xy=np.array([q[0] for q in proj]); z=np.array([q[1] for q in proj])
        slope=np.linalg.lstsq(np.c_[np.ones(len(xy)),xy],z,rcond=None)[0]
        g=slope[1:]; norm=float(np.linalg.norm(g))
        bias=-.3 if mat==E else -.12 if mat==B else -.03
        if norm<1e-6:
            self.poly(xy,self.color[mat][tone],float(z.mean())+bias,not detail);return
        axis=g/norm;along=xy@axis;centre=xy.mean(0)
        a=centre+axis*(along.min()-centre@axis);b=centre+axis*(along.max()-centre@axis)
        self.poly(xy,self.color[mat][tone],bias,not detail,(a,b,slope[0]+a@g,slope[0]+b@g))


def link(ink, c, a, u, r=4, mat=B):
    # An elongated hexagonal link with an open centre and two cut corners.
    pts = [(-.55,-1),(.55,-1),(1,-.45),(1,.45),(.55,1),(-.55,1),(-1,.45),(-1,-.45)]
    for n, (x,y) in enumerate(pts):
        q,v = pts[(n+1)%len(pts)]
        ink.plate([c+a*x*r+u*y*r*1.25,c+a*q*r+u*v*r*1.25,
                   c+a*q*(r-1.4)+u*v*(r-1.4)*1.25,c+a*x*(r-1.4)+u*y*(r-1.4)*1.25],mat,2)

def render(cls, theme, kind, gender, clip, facing, k):
    _,ink,p,Q,xf,j,h = rig.pose(cls,gender,clip,facing,k)
    colors=(PRIEST_WEAPON_COLOR if cls=='priest' and kind=='weapon' else
            PRIEST_COLOR if cls=='priest' and kind in ('armor','headgear','shoulders','gloves') else
            MAGE_WEAPON_COLOR if cls=='mage' and kind=='weapon' else
            MAGE_COLOR if cls=='mage' and kind in ('armor','headgear','shoulders','gloves') else
            HUNT_WEAPON_COLOR if cls=='hunter' and kind=='weapon' else
            HUNT_COLOR if cls=='hunter' and kind in ('armor','headgear','shoulders','gloves') else
            MIGHT_WEAPON_COLOR if cls=='warrior' and kind=='weapon' else
            BLOOD_COLOR if cls=='assassin' and kind in ('armor','shoulders','gloves') else
            MIGHT_COLOR if cls=='warrior' and kind in ('armor','headgear','shoulders','gloves') else
            HOOD_COLOR if cls=='assassin' and kind=='headgear' else COLOR)
    ink = ForgeInk(cc.rig.psi_for(facing), colors)
    u,a = Q@V(0,0,1), Q@V(1,0,0)
    ix=CLASSES.index(cls)
    if cls=='priest' and kind in ('armor','headgear','shoulders','gloves','pants'):
        import chainforged_priest_shapes
        chainforged_priest_shapes.draw(ink,kind,p,Q,xf,j,h,colors)
        return ink.resolve(clip in ('hurt','die') and k==0)
    if cls=='mage' and kind in ('armor','headgear','shoulders','gloves','pants'):

        import chainforged_mage_shapes
        chainforged_mage_shapes.draw(ink,kind,p,Q,xf,j,h,colors)
        return ink.resolve(clip in ('hurt','die') and k==0)
    if cls=='hunter' and kind in ('armor','headgear','shoulders','gloves','pants'):

        import chainforged_hunter_shapes
        chainforged_hunter_shapes.draw(ink,kind,p,Q,xf,j,h,colors)
        return ink.resolve(clip in ('hurt','die') and k==0)
    if cls=='assassin' and kind in ('armor','shoulders','gloves','pants'):

        import chainforged_assassin_shapes
        chainforged_assassin_shapes.draw(ink,kind,p,Q,xf,j)
        return ink.resolve(clip in ('hurt','die') and k==0)
    def plate(points,mat=I,tone=2):
        ink.plate([xf(q) for q in points],mat,tone)
    if cls=='warrior' and kind=='armor':
        # Owner's Might reference: articulated green plates inside a gold frame,
        # angular gorget, diamond breast ornament and wide plated hip guards.
        cc.torso(ink,xf,S,10.3,6.1,38,70)
        for side in (-1,1):
            plate([(side*1,8,67),(side*9,6,69),(side*11,6,55),(side*2,9,53)],B,2)
            plate([(side*3,9.1,65),(side*8,7.5,65),(side*9,7.3,57),(side*3,9.4,56)],E,2)
            plate([(side*2,9,51),(side*10,7,54),(side*10,7,43),(side*2,9,42)],I,2)
            plate([(side*3,9.4,49),(side*8,8.4,51),(side*8,8.4,45),(side*3,9.4,44)],E,2)
            plate([(side*3,5,41),(side*10,3,45),(side*16,3,31),(side*10,6,26),(side*4,7,33)],B,2)
            plate([(side*6,6,40),(side*10,5,42),(side*13,5,32),(side*10,7,30)],I,2)
            plate([(side*2,6,69),(side*9,3,75),(side*8,8,65),(side*3,10,62)],B,3)
            ink.bone(j['L' if side<0 else 'R']['shoulder'],j['L' if side<0 else 'R']['elbow'],4.1,3.2,S,-1)
        for z,r in ((59,4.2),(39,5.5)):
            plate([(0,10,z+r),(-r,10,z),(0,10,z-r),(r,10,z)],B,3)
            plate([(0,10.4,z+r-1.7),(-r+1.7,10.4,z),(0,10.4,z-r+1.7),(r-1.7,10.4,z)],E,2)
        for side in (-1,1):
            plate([(side*2,-7,68),(side*9,-6,70),(side*10,-6,44),(side*2,-7,41)],I,2)
            plate([(side*3,-7.5,64),(side*7,-7.5,65),(side*8,-7.5,47),(side*3,-7.5,45)],B,2)
    elif kind=='armor':
        w=9.7 if cls=='warrior' else 8.6
        cc.torso(ink,xf,S,w,5.9,37,70)
        # A horseshoe furnace surrounds an open, segmented ember grate.
        for side in (-1,1):
            plate([(side*w,6,68),(side*4,8,72),(side*2.7,8,55),
                   (side*6,8,45),(side*(w+2),6,49)],I,2)
            plate([(side*7,8.3,64),(side*4,8.4,66),(side*4,8.4,55),(side*7,8.3,52)],E,2)
            hem=18+ix*2 if cls in ('mage','priest') else 32
            plate([(side*3,-6,48),(side*9,-6,50),(side*(15+ix),-10,hem),
                   (side*8,-8,hem+5)],S,2)
            for n in range(2+ix%2):
                z=59-n*8
                plate([(side*8,-7,z),(side*(15+ix),-9,z+4),(side*(16+ix),-10,z-1),
                       (side*9,-8,z-5)],I,n%2+1)
            ink.bone(j['L' if side<0 else 'R']['shoulder'],j['L' if side<0 else 'R']['elbow'],3.7,3,S,-.9)
        for n in range(3):
            z=57+n*4
            plate([(-3,8.7,z),(3,8.7,z),(3,8.7,z+1.4),(-3,8.7,z+1.4)],B,3)
        link(ink,xf((0,9,42)),a,u,4+ix*.25)
    elif kind=='headgear':
        H,hd=h['H'],h['hd']-8
        def f(pts,mat=I,tone=2,z=0):
            ink.poly([H(x*.78,y*.78) for x,y in pts],colors[mat][tone],hd+z)
        if cls=='warrior':
            # Open face with a high jaw guard; the shoulders carry the large horns.
            f([(-19,0),(-20,13),(-11,23),(0,25),(11,23),(20,13),(19,0),
               (13,-7),(10,7),(0,14),(-10,7),(-13,-7)],I,2)
            if h['front']<-.4:
                f([(-16,0),(-16,15),(0,23),(16,15),(16,0),(0,-6)],I,2,-.1)
                f([(-2,-5),(-2,21),(2,21),(2,-5)],B,2,-.2)
            else:
                f([(-18,-3),(-11,-12),(0,-18),(11,-12),(18,-3),
                   (12,-1),(8,-7),(0,-10),(-8,-7),(-12,-1)],B,3,-.6)
                f([(-13,8),(-7,13),(0,16),(7,13),(13,8),(9,7),(0,12),(-9,7)],B,2,-.3)
                f([(-3,17),(0,23),(3,17),(0,14)],E,2,-.4)
        elif cls=='assassin':
            # Owner reference: pointed wine-red cowl, red stitched flames round
            # the face opening, and a dark mask below the eyes. Original fitted
            # shape, following the existing head axis in every animation.
            outline=[(-18,-15),(-24,-5),(-22,11),(-13,29),(0,42),
                     (9,27),(20,12),(23,-5),(16,-17),(0,-23)]
            if h['front']<-.4:
                f(outline,'hood',1)
                f([(-13,18),(0,36),(6,23),(4,-12),(-6,-15)],'hood',2,-.1)
                f([(-17,-7),(-5,-16),(10,-14),(16,-7),(10,-20),(-7,-23)],'hood',0,-.2)
            else:
                f([(-22,9),(-15,24),(0,42),(9,27),(21,10),(11,6),
                   (0,17),(-12,6)],'hood',1)
                f([(-17,17),(-12,27),(0,39),(3,30),(-1,24),(-8,19)],'hood',2,-.1)
                for side in (-1,1):
                    f([(side*21,11),(side*12,7),(side*12,-3),(side*5,-15),
                       (side*15,-19),(side*23,-7)],'hood',1,-.2)
                    f([(side*21,5),(side*16,3),(side*15,-9),(side*9,-15),
                       (side*16,-14),(side*21,-5)],'hood',2,-.3)
                    f([(side*14,11),(side*11,5),(side*13,-4),(side*10,-11),
                       (side*7,-13),(side*12,-13),(side*16,-4),(side*14,4),
                       (side*16,10)],'hoodtrim',1,-.6)
                    f([(side*14,13),(side*10,16),(side*10,22),(side*6,19),
                       (side*5,25),(side*2,20),(side*4,17),(side*6,21),
                       (side*9,17),(side*10,13)],'hoodtrim',2,-.7)
                f([(-15,-13),(0,-20),(15,-13),(7,-25),(-7,-25)],'hood',1,-.4)
                f([(-12,7),(0,17),(11,6),(9,2),(0,10),(-9,2)],'hood',0,-.5)
                f([(-10,-3),(0,-6),(10,-3),(6,-12),(0,-16),(-6,-12)],I,0,-.8)
                f([(-8,-5),(0,-9),(7,-5),(4,-11),(0,-13)],'hood',1,-.9)
        else:
            # Open brow and a bank of vertical chimney vents. Class crowns have
            # different vent counts/heights, rather than a tint over the same mask.
            f([(-18,0),(-18,11),(-9,18),(0,15),(9,18),(18,11),(18,0),(11,3),(9,9),(-9,9),(-11,3)])
            for n in range(3+ix%3):
                x=-12+n*24/(2+ix%3);height=23+(n%2)*5+ix
                f([(x-2,13),(x-3,height),(x+2,height),(x+3,13)],I,2,-.1)
                f([(x-.8,16),(x-1,height-2),(x+1,height-2),(x+.8,16)],E,3,-.2)
            f([(-13,7),(-9,11),(0,8),(9,11),(13,7),(0,4)],B,2,-.3)
    elif cls=='warrior' and kind=='shoulders':
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*side;front=Q@V(0,1,0)
            # Big angular pauldrons, rolled gold lower rim and three tall spikes.
            ink.plate([c-out*4+u*5,c+out*2+u*12,c+out*14+u*10,
                       c+out*19+u*2,c+out*15-u*9,c+out*1-u*8],I,2)
            ink.plate([c-out*4+u*5,c+out*2+u*12,c+out*14+u*10,
                       c+out*16+u*6,c+out*3+u*8],B,3)
            ink.plate([c+out-u*6+front*3,c+out*15-u*7+front*3,
                       c+out*19+u*2+front*3,c+out*18-u*7+front*3,
                       c+out*13-u*12+front*3,c+out-u*10+front*3],B,2)
            for n,(reach,height) in enumerate(((5,39),(16,32),(24,20))):
                base=c+out*(3+n*6)+u*(7-n*2)
                tip=c+out*reach+u*height
                ink.plate([base-out*3-front*2,base+out*3-front*2,tip],B,3)
                ink.plate([base+out*3-front*2,base+front*3,tip],I,2)
            d=c+out*10+front*4-u
            ink.plate([d-u*4,d-out*3,d+u*4,d+out*3],B,3)
    elif kind=='shoulders':
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*side
            # Three tiered anvil horns; open hanging chain below the shoulder.
            for n in range(2+ix%2):
                d=c+out*(4+n*4)
                ink.plate([d-out*4-u*2,d-out*5+u*6,d+out*7+u*(9+ix),
                           d+out*9+u*3,d+out*3-u*5],I,2)
                ink.bone(d+out*1+u*5,d+out*6+u*6,1,1,E,-1.7,3)
            link(ink,c+out*12-u*5,out,u,3.3)
    elif cls=='warrior' and kind=='gloves':
        for key in ('L','R'):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c);front=Q@V(0,5,0)
            ink.bone(c,c+v*15,4.5,6,I,-1.3)
            for t in (4,13):
                d=c+v*t
                ink.bone(d-a*5,d+a*5,1.8,1.8,B,-2,3)
            d=c+v*8+front
            ink.plate([d-a*3,d+v*3,d+a*3,d-v*3],B,3)
            ink.plate([d-a,d+v*1.5,d+a,d-v*1.5],E,2)
            ink.plate([c-a*4,c-a*3-v*6,c+a*4-v*5,c+a*5+v*2],B,2)
    elif kind=='gloves':
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c)
            ink.bone(c,c+v*14,4.1,5.4,I,-1.2)
            # Offset ratchet teeth and knuckle vents, asymmetrical brass cuff.
            for n in range(3):
                d=c+v*(2+n*4)
                ink.plate([d-a*5,d-a*(7+ix*.4)+v*3,d+a*5+v*4,d+a*4-v],B,2)
                ink.bone(d-a*3-v,d+a*3-v,1,1,E,-2,3)
            ink.plate([c-a*4,c-a*3-v*6,c+a*4-v*5,c+a*5+v*2],I,3)
    elif cls=='warrior' and kind=='pants':
        # Shared item, original class-fitted greaves; the other four rigs retain
        # their original shapes and editor sprites.
        for key in ('L','R'):
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle'];v=unit(ankle-knee)
            ink.bone(hip,knee,5.7,5,'trim',-1.2)
            ink.bone(knee,ankle,5.3,4.1,'trim',-1.3)
            front=Q@V(0,5,0)
            for c in (hip*.4+knee*.6,knee+v*11):
                d=c+front
                ink.plate([d-a*3-v*5,d+a*3-v*5,d+a*3+v*5,d+v*7,d-a*3+v*5],'gem',2)
            d=knee+front
            ink.plate([d-a*6,d-v*6,d+a*6,d+v*5],'trim',3)
            ink.plate([d-a*3,d-v*3,d+a*3,d+v*2],'gem',1)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,8,-2),5.3,4.1,'trim',-1.6)
    elif kind=='pants':
        for key in ('L','R'):
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle']
            v=unit(ankle-knee)
            ink.bone(hip,knee,5.2,4.6,S,-1);ink.bone(knee,ankle,4.7,3.7,I,-1)
            link(ink,knee+Q@V(0,5,0),a,u,5)
            for n in range(2):
                c=knee+v*(8+n*7)
                ink.plate([c-a*5,c+a*5,c+a*6+v*4,c-a*4+v*4],B,2)
                ink.bone(c-a*3+v,c+a*3+v,1,1,E,-2,3)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,7,-2),4.9,3.9,I,-1.5)
    elif kind=='necklace':
        ink.ribbon([xf(q) for q in [(-6,5,71),(-5,9,64),(0,11,56),(5,9,64),(6,5,71)]],1.2,1.2,B,2,-2)
        c=xf((0,11,55));link(ink,c,a,u,6,I)
        ink.plate([c-a*5-u,c-a*3-u*6,c+a-u*8,c+a*3-u*4],E,3)
    elif kind=='accessory':
        c=j['L']['hand']+Q@V(0,4,1)
        # Split circular crucible seal, with projecting hot pour spout.
        link(ink,c,a,u,4.8,I)
        ink.plate([c-a*3+u*3,c+u*8,c+a*6+u*6,c+a*3+u*1],B,2)
        ink.plate([c-a+u*4,c+u*6,c+a*3+u*5,c+a*2+u*3],E,3)
    elif kind=='cloak':
        phase=math.tau*k/(6 if clip=='idle' else 8)
        # Three separate hanging panels with nine chain ribs, not a stock cloak.
        from cloak_shapes import surface
        import cloak_shapes
        old=cloak_shapes.COLOR;cloak_shapes.COLOR=COLOR
        try:
            for n in range(3):
                x=(n-1)*12
                sway=math.sin(phase-n*.7)*(2.5 if clip=='walk' else .8)
                pts=[xf((x-5,-7,68)),xf((x+5,-7,68)),xf((x+8+sway,-16,22+n%2*5)),xf((x-7+sway,-16,18+n%2*5))]
                if clip=='die':
                    for q in pts:q[2]=max(1.6,q[2])
                surface(ink,pts,'gem' if cls=='warrior' else 'forge' if cls=='assassin' else 'leather' if cls=='hunter' else 'veil' if cls=='mage' else 'cloth' if cls=='priest' else S,1 if cls in ('warrior','hunter','mage','priest') else 0 if cls=='assassin' else 2)
                for rib in range(3):
                    lo=pts[0]*(1-(rib+1)/4)+pts[3]*(rib+1)/4
                    hi=pts[1]*(1-(rib+1)/4)+pts[2]*(rib+1)/4
                    ink.bone(lo,hi,.8,.8,'trim' if cls in ('warrior','hunter','mage','priest') else E,-.5,0 if cls=='assassin' else 2)
            for side in (-1,1):
                surface(ink,[xf((side*4,-7,69)),xf((side*12,-6,68)),xf((side*12,4,65)),xf((side*5,6,66))],'trim' if cls in ('warrior','hunter','mage','priest') else 'hot' if cls=='assassin' else I,0 if cls=='assassin' else 2)
        finally:cloak_shapes.COLOR=old
    elif kind=='weapon':
        weapon(ink,cls,p,Q,j)
    else:raise ValueError(kind)
    return ink.resolve(clip in ('hurt','die') and k==0)

def weapon(ink,cls,p,Q,j):
    if cls=='hunter':
        c=j['L']['hand'];u=Q@unit(V(*p['bow']));f=unit(c-j['R']['hand']) if p['draw'] else Q@unit(V(*p['aim']))
        if p['dropped']:c,u,f=V(-21,8,3),unit(V(.3,1,0)),V(0,0,1)
        u=unit(u-f*(u@f))
        for side in (-1,1):
            pts=[c+u*side*3,c+u*side*11+f*8,c+u*side*22+f*5,c+u*side*25-f*3]
            ink.ribbon(pts,3,1.8,I,2,-.7)
            for n in (10,18):link(ink,c+u*side*n+f*6,f,u,2.8)
            end=pts[-1];nock=j['R']['hand'] if p['draw'] and not p['dropped'] else c-f*7
            ink.ribbon([end,nock],.7,.7,E,3,-1,False)
        ink.bone(c-u*4,c+u*4,2,2,B,-.8)
        if p['arrow'] and not p['dropped']:ink.bone(c-f*12,c+f*30,.8,.8,E,-1,3)
        return
    for n,key in enumerate('LR' if cls=='assassin' else 'L' if cls=='mage' else 'R'):
        c=j[key]['hand'];direction=p['blade'+key] if cls=='assassin' else p[{'warrior':'blade','priest':'mace','mage':'staff'}[cls]]
        u,a=Q@unit(V(*direction)),Q@V(1,0,0)
        if p['dropped']:c,u,a=V((n*2-1)*21,-8,3),unit(V(.4,1,0)),unit(V(1,-.4,0))
        at=lambda x,y:c+a*x+u*y
        ink.bone(at(0,-17 if cls=='mage' else -5),at(0,12),1.8,1.8,B,-.6)
        if cls=='warrior':
            # Broad cleaver with a broken chain welded through its spine.
            ink.plate([at(-4,8),at(-8,29),at(-4,40),at(7,37),at(10,30),at(7,10)],I,3)
            ink.plate([at(3,12),at(5,32),at(1,36),at(0,12)],E,3)
            for y in (13,23,33):link(ink,at(-7,y),a,u,3)
            ink.bone(at(-9,5),at(10,5),1.8,1.8,B,-1)
        elif cls=='mage':
            ink.bone(at(0,8),at(0,24),2,2,I,-.6)
            # A forked crucible holding an open ember globe.
            for side in (-1,1):
                ink.plate([at(side*3,21),at(side*10,27),at(side*10,37),at(side*5,39),at(side*6,28)],I,2)
            link(ink,at(0,32),a,u,6,E)
            ink.plate([at(-2,30),at(0,36),at(3,32),at(0,28)],E,3)
        elif cls=='assassin':
            # Tongs with two parallel prongs and a real notch between them.
            for side in (-1,1):
                ink.plate([at(side*1.4,5),at(side*5,12),at(side*6,27),at(side*3,30),at(side*3,13)],I,3)
                ink.bone(at(side*4,15),at(side*4,25),.8,.8,E,-1,3)
            link(ink,at(0,5),a,u,3,B)
        else:
            ink.bone(at(0,7),at(0,17),2,2,B,-.6)
            ink.plate([at(-9,19),at(-7,14),at(7,14),at(10,19),at(7,29),at(-7,29)],I,2)
            for x in (-5,0,5):ink.bone(at(x,18),at(x,27),1,1,E,-1,3)
            for side in (-1,1):
                ink.ribbon([at(side*7,25),at(side*12,32),at(0,36)],.8,.8,B,3,-1)
            link(ink,at(0,33),a,u,3,B)
    if cls=='warrior':
        c=(j['L']['hand']+j['L']['elbow'])/2+Q@V(0,5,0);a,u=Q@V(1,0,0),Q@V(0,0,1)
        if p['dropped']:c=V(-22,10,3);u=V(0,1,0);a=V(1,0,0)
        ink.plate([c-a*10+u*12,c+a*10+u*12,c+a*12-u*7,c-u*16,c-a*12-u*7],I,2)
        link(ink,c,a,u,7,B)
        ink.bone(c-u*7,c+u*7,1.3,1.3,E,-1,3)
