"""Original Fatewoven equipment geometry on the existing ten animated hero rigs.

No starter gear is drawn or repainted. Each slot is a separate depth-fitted layer.
Funeral shuttles, pegged weaving frames, wound cord and amber knots form the set.
"""
import numpy as np
import cel_common as cc
import gear_shapes as rig
from cel_common import V, unit

MATS = {
 'bark':['#262725','#4a3830','#79573b','#b68c55'],
 'amber':['#70452d','#a56531','#e7a748','#ffe3a0'],
 'linen':['#323c38','#657468','#abb5a1','#e0dfbc'],
 'weave':['#202d32','#31484c','#4f7472','#8aafa0'],
 'bronze':['#453c31','#756344','#b49a65','#f0d4a0'],
}
PALETTE,COLOR=cc.palette_of(MATS)
SLOTS=('armor','pants','shoulders','gloves','head','necklace','accessory','weapon')
KINDS={'head':'headgear'}
CLASSES=('warrior','mage','assassin','priest','hunter')
META={'warrior':'warrior_layered',**{c:c for c in CLASSES if c!='warrior'}}


def knot(ink,c,a,u,size=4):
    ink.plate([c-u*size,c-a*size,c+u*size,c+a*size],'bronze',2)
    ink.plate([c-u*(size-1.4),c-a*(size-1.4),c+u*(size-1.4),c+a*(size-1.4)],'amber',3,True)


def draw(ink,slot,cls,p,R,xf,joints,head):
    up,side=R@V(0,0,1),R@V(1,0,0)
    plate=lambda pts,mat='bark',tone=2:ink.plate([xf(q) for q in pts],mat,tone)
    if slot=='armor':
        # Ribbed root corslet around a woven core; three separate hanging shuttles.
        w=9 if cls=='warrior' else 7.7
        cc.torso(ink,xf,'weave',w,5.5,37,69)
        for s in (-1,1):
            path=[xf((s*(w-1),5,67)),xf((s*4,7,56)),xf((s*7,6,42))]
            ink.ribbon(path,2.7,2,'bark',2,-1)
            plate([(s*3,-6,69),(s*12,-8,74),(s*16,-10,51),(s*9,-9,38)],'bark',1)
            # Long funeral bands, asymmetrically split rather than a common tunic.
            hem=16 if cls in ('mage','priest') else 30
            plate([(s*3,-4,42),(s*9,-5,43),(s*(14+p['sway']*.4),-8,hem+5),(s*8,-8,hem)],'linen')
        for x in (-5,0,5):
            plate([(x-1.3,7.2,66),(x+1.3,7.2,66),(x+1.3,7.3,47),(x-1.3,7.3,47)],'linen')
        for n,x in enumerate((-7,0,7)):
            z=39-(7 if n==1 else 0)
            plate([(x-3,6,42),(x+3,6,42),(x+2,6,z-9),(x,6,z-13),(x-2,6,z-9)],'bronze')
        knot(ink,xf((0,8,57)),side,up,4.5)
        for key in 'LR':
            j=joints[key];ink.bone(j['shoulder'],j['elbow'],3.6,2.8,'weave',-.8)
            if cls in ('mage','priest'):ink.bone(j['elbow'],j['hand']+(j['elbow']-j['hand'])*.4,4.8,3.8,'linen',-.7)
    elif slot=='head':
        H,hd=head['H'],head['hd']-8
        def face(points,mat,tone=2,z=0):ink.poly([H(*q) for q in points],COLOR[mat][tone],hd+z)
        # All crowns have open centres: the face and body stay the original art.
        if cls=='mage':
            # A miniature pegged loom, no pointed wizard hat.
            face([(-16,9),(-16,29),(-12,30),(-12,13),(12,13),(12,30),(16,29),(16,9)],'bark')
            face([(-18,24),(18,24),(18,29),(-18,29)],'bronze',2,-.2)
            for x in (-8,-4,0,4,8):face([(x,14),(x+1,14),(x+1,24),(x,24)],'linen',3,-.3)
        elif cls=='warrior':
            face([(-14,-9),(-16,10),(-10,20),(-4,16),(0,26),(4,16),(10,20),(16,10),(14,-9),(9,-5),(9,6),(-9,6),(-9,-5)],'bark')
            for s in (-1,1):face([(s*9,13),(s*19,23),(s*21,20),(s*13,5)],'bronze',2,-.2)
        elif cls=='assassin':
            face([(-14,2),(-16,9),(-10,12),(0,8),(10,12),(16,9),(14,2),(6,4),(-6,4)],'weave')
            for s in (-1,1):
                for n in range(3):face([(s*(10+n*3),8),(s*(16+n*3),23-n*3),(s*(19+n*2),21-n*3),(s*(13+n*2),7)],'bronze',2,-.2)
        elif cls=='priest':
            face([(-15,4),(-14,13),(-10,21),(-5,15),(0,28),(5,15),(10,21),(14,13),(15,4)],'linen')
            for x in (-9,0,9):face([(x-2,10),(x,22 if x==0 else 17),(x+2,10),(x,7)],'amber',3,-.3)
        else:
            face([(-15,3),(-13,11),(0,8),(13,11),(15,3),(0,5)],'weave')
            for s in (-1,1):face([(s*10,6),(s*15,15),(s*22,19),(s*18,20),(s*17,26),(s*13,23),(s*12,16),(s*6,11)],'bark')
        face([(-3,9),(0,15),(3,9),(0,6)],'amber',3,-.5)
    elif slot=='shoulders':
        for s,key in ((-1,'L'),(1,'R')):
            c=joints[key]['shoulder'];a=side*s
            # Wooden loom cheeks extend sideways; visible holes are woven, not spikes.
            reach=16 if cls=='warrior' else 13
            ink.plate([c-a*2+up*5,c+a*reach+up*8,c+a*(reach+3)-up*4,c+a*5-up*8,c-a*2-up*2],'bark',2)
            for n in range(3):
                start=c+a*(4+n*3)+up*5
                ink.bone(start,start-up*(9+n%2*3),.9,.9,'linen',-2,3)
            ink.bone(c+up*7,c+a*(reach+1)+up*9,1.5,1.5,'bronze',-2,2)
            knot(ink,c+a*(reach-1)+R@V(0,4,0),a,up,3)
    elif slot=='gloves':
        for key in 'LR':
            c=joints[key]['hand'];el=joints[key]['elbow'];u=unit(el-c)
            ink.bone(c+u*1,c+u*12,3.4,4.3,'linen',-1)
            ink.bone(c+u*9,c+u*14,5,4.3,'bark',-1.5)
            for n in range(3):ink.bone(c+u*(3+n*3),c+u*(4+n*3),3.9,3.9,'bronze',-1.7,2)
            # Projecting shuttle ferrule on each cuff.
            ink.plate([c+u*6-side*4,c+u*19-side*5,c+u*14-side*9,c+u*7-side*7],'bark',2)
    elif slot=='pants':
        for s,key in ((-1,'L'),(1,'R')):
            j=joints[key];k,a=j['knee'],j['ankle'];u=unit(a-k)
            ink.bone(j['hip'],k,4.7,3.8,'weave',-.7)
            ink.bone(k,a,4,3.2,'linen',-.8)
            for n in range(4):ink.bone(k+u*(n*3+1),k+u*(n*3+2),4.2,4.2,'bronze',-1.1)
            # A split wooden shin rather than ordinary flat leggings.
            ink.ribbon([k+side*s*3,k+u*9+side*s*5,a+side*s*3],2.2,1.4,'bark',2,-1.5)
            ink.bone(a+V(0,-1,-1),a+V(0,6,-2),3.2,2.3,'bark',-1.1)
    elif slot=='necklace':
        pts=[xf(q) for q in [(-6,3,70),(-5,7,63),(0,8,51),(5,7,63),(6,3,70)]]
        ink.ribbon(pts,.9,.9,'linen',3,-2)
        c=xf((0,8.5,51))
        ink.plate([c-up*7,c-side*4,c+up*7,c+side*4],'bark',2)
        knot(ink,c,side,up,3)
    elif slot=='accessory':
        c=joints['L']['hand']+R@V(0,3.5,1)
        ink.bone(c-up*1,c+up*2,3.7,3.7,'bronze',-2)
        # Three small burial beads on a cord, rather than the round starter stone.
        for n in (-1,0,1):knot(ink,c+side*n*3.3,side,up,1.9)
    elif slot=='weapon':
        weapon(ink,cls,p,R,xf,joints)


def weapon(ink,cls,p,R,xf,joints):
    if cls=='hunter':
        c=joints['L']['hand'];axis=R@unit(V(*p['bow']));face=unit(c-joints['R']['hand']) if p['draw'] else R@unit(V(*p['aim']))
        if p['dropped']:c,axis,face=V(-21,8,3),unit(V(.3,1,0)),V(0,0,1)
        axis=unit(axis-face*(axis@face))
        # A double-limbed loom bow with flat pegged ends, not a recoloured shortbow.
        for s in (-1,1):
            pts=[c+axis*s*t+face*(4+4*np.sin(t/24*np.pi)) for t in (3,10,18,24)]
            ink.ribbon(pts,2.8,1.8,'bark',2,-.6)
            end=pts[-1];ink.bone(end-axis*2,end+axis*2,3.5,3.5,'bronze',-1)
            nock=joints['R']['hand'] if p['draw'] and not p['dropped'] else c-face*3
            ink.ribbon([end,nock],.6,.6,'linen',3,-.8,False)
        ink.bone(c-axis*4,c+axis*4,2,2,'weave',-1)
        if p['arrow'] and not p['dropped']:
            u=unit(c-joints['R']['hand']);tip=joints['R']['hand']+u*34
            ink.bone(joints['R']['hand'],tip,.6,.6,'bronze',-.5)
            ink.plate([tip+u*4,tip+axis*2,tip-axis*2],'amber',3)
        return
    keys='LR' if cls=='assassin' else 'R' if cls in ('warrior','priest') else 'L'
    for n,key in enumerate(keys):
        hand=joints[key]['hand'];direction=p['blade'+key] if cls=='assassin' else p[{'warrior':'blade','mage':'staff','priest':'mace'}[cls]]
        u,across=R@unit(V(*direction)),R@V(1,0,0)
        if p['dropped']:hand,u=V((n*2-1)*21,-8,3),unit(V(.4,1,0));across=unit(V(u[1],-u[0],0))
        ink.bone(hand-u*(19 if cls=='mage' else 4),hand+u*7,1.8,1.8,'bark',-.3)
        def at(x,y):return hand+across*x+u*y
        if cls=='mage':
            # A rectangular spindle staff with a hollow threaded window.
            for s in (-1,1):ink.bone(at(s*7,17),at(s*7,34),1.9,1.9,'bark',-.5)
            ink.bone(at(-9,33),at(9,33),2,2,'bronze',-.6)
            ink.bone(at(-9,18),at(9,18),2,2,'bronze',-.6)
            ink.bone(at(0,5),at(0,18),1.7,1.7,'bark',-.4)
            for x in (-3,0,3):ink.bone(at(x,19),at(x,32),.6,.6,'linen',-1,3)
            knot(ink,at(0,26),across,u,3.5)
        elif cls=='priest':
            # Two flanged spool discs and an amber core form the mace head.
            ink.bone(at(0,4),at(0,24),2.2,2.2,'bark',-.4)
            ink.bone(at(0,18),at(0,27),5,5,'linen',-.5)
            for y in (17,27):ink.plate([at(-8,y),at(-6,y+3),at(6,y+3),at(8,y),at(6,y-2),at(-6,y-2)],'bronze',2)
            knot(ink,at(0,22)+R@V(0,5,0),across,u,4)
        else:
            # Forked needle / weaving shuttle blades, with an actual open slot.
            length=25 if cls=='assassin' else 36
            ink.bone(at(-5,6),at(5,6),1.6,1.6,'bronze',-.5)
            pts=[(-2,7),(-5,13),(-4,length-5),(0,length),(4,length-5),(5,13),(2,7)]
            ink.plate([at(x,y) for x,y in pts],'bronze',2)
            ink.plate([at(-1.4,13),at(-1.4,length-7),at(0,length-4),at(1.4,length-7),at(1.4,13)],'weave',0,True)
            for y in (11,15):ink.bone(at(-3,y),at(3,y+1),.6,.6,'linen',-1,3)
    if cls=='warrior':
        c=(joints['L']['elbow']+joints['L']['hand'])/2+R@V(0,3,0);a,b=R@V(1,0,0),R@V(0,0,1)
        if p['dropped']:c,a,b=V(-21,8,2),V(1,0,0),V(0,1,0)
        # A split root shield with five warp lines and a coffin-shaped outline.
        pts=[(-11,10),(-6,15),(6,15),(11,10),(9,-9),(0,-17),(-9,-9)]
        ink.plate([c+a*x+b*y for x,y in pts],'bark',2)
        for x in (-6,-3,0,3,6):ink.bone(c+a*x+b*10,c+a*x-b*8,.6,.6,'linen',-1,3)
        knot(ink,c+R@V(0,5,0),a,b,5)


def render(cls,gender,clip,facing,k,slot):
    _,ink,p,R,xf,joints,head=rig.pose(cls,gender,clip,facing,k);ink.color=COLOR
    draw(ink,slot,cls,p,R,xf,joints,head)
    return ink.resolve(clip in ('hurt','die') and k==0)
