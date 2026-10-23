"""Original violet-and-gold ritual robes, jeweled hood and orbiting shoulder globes."""
import math
from cel_common import V,unit

def orb(ink,c,r):
    centre,depth=ink.project(c)
    def disc(x,y,r,mat,tone,z):
        ink.poly([centre+V(x+math.cos(t)*r,y+math.sin(t)*r) for t in [math.tau*n/20 for n in range(20)]],ink.color[mat][tone],depth+z,outline=tone==0)
    disc(0,0,r,'hot',0,-3)
    disc(-.5,-.5,r-1.2,'hot',1,-3.1)
    disc(-1,-1,r-2.3,'hot',2,-3.2)
    disc(-2,-2,max(1,r*.27),'hot',3,-3.3)
    for n in range(24):
        t,q=math.tau*n/24,math.tau*(n+1)/24
        def at(v,r):return centre+V(math.cos(v)*r,math.sin(v)*r)
        ink.poly([at(t,r+3),at(q,r+3),at(q,r+2),at(t,r+2)],ink.color['brass'][2],depth-2,False)
    for side in (-1,1):
        ink.poly([centre+V(side*(r+4),1),centre+V(side*(r+12),-2),centre+V(side*(r+4),-1)],ink.color['hot'][2],depth-3,False)

def draw(ink,kind,p,Q,xf,j,h,colors):
    a,u=Q@V(1,0,0),Q@V(0,0,1)
    def plate(points,mat='forge',tone=2):ink.plate([xf(q) for q in points],mat,tone)
    if kind=='armor':
        import cel_common as cc
        cc.torso(ink,xf,'forge',8.7,6,37,70)
        for side in (-1,1):
            # Pale outer robe, purple side folds, long wine-red gold-edged banner.
            plate([(side*2,5,42),(side*9,3,44),(side*16,3,5),
                   (side*4,8,3)],'clothforge',2)
            plate([(side*8,-5,45),(side*11,-3,43),(side*17,-3,5),
                   (side*10,3,4),(side*10,3,21)],'forge',2)
            plate([(side*1,8,67),(side*8,6.8,72),(side*10,6.5,64),
                   (side*2,9,54)],'brass',2)
            plate([(side*3,9.3,65),(side*7,7.6,69),(side*8,7.5,64),
                   (side*3,9.8,58)],'forge',2)
            plate([(side*.5,9.8,55),(side*6,8.5,61),(side*6,8.5,40),
                   (side*.5,10,37)],'brass',2)
            plate([(side*2,10.4,53),(side*4.5,9.4,57),(side*4.5,9.4,41),
                   (side*2,10.5,40)],'leather',2)
            # Full banner continues from the belt to the ankle, with gold runes.
            plate([(0,10,40),(side*6,9,38),(side*8,9,9),(0,11,4)],'brass',2)
            plate([(side*.8,11,37),(side*4,10,36),(side*5.5,10,10),
                   (side*.8,11.5,7)],'leather',2)
            plate([(side*2,-7,69),(side*8,-6,70),(side*10,-6,39),
                   (side*17,-7,5),(side*2,-9,4)],'forge',1)
            plate([(side*3,-7.5,67),(side*4,-7.5,67),(side*6,-7.5,37),
                   (side*8,-8,6),(side*6,-8,6),(side*4,-7.5,37)],'brass',2)
            ink.bone(j['L' if side<0 else 'R']['shoulder'],j['L' if side<0 else 'R']['elbow'],4.1,3.2,'forge',-1)
        for z,r in ((42,4.1),(29,2.5),(19,2)):
            plate([(0,12,z+r),(-r,12,z),(0,12,z-r),(r,12,z)],'brass',3)
            plate([(0,12.4,z+r-1),(-r+1,12.4,z),(0,12.4,z-r+1),(r-1,12.4,z)],'hot',2 if z==42 else 0)
    elif kind=='headgear':
        H,hd=h['H'],h['hd']-8
        def f(pts,mat='forge',tone=2,z=0):ink.poly([H(x*.78,y*.78) for x,y in pts],colors[mat][tone],hd+z)
        f([(-19,-9),(-23,8),(-13,24),(0,31),(13,24),(23,8),(19,-9),
           (12,-13),(10,6),(0,14),(-10,6),(-12,-13)],'forge',1)
        if h['front']<-.4:
            f([(-15,-12),(-17,8),(0,28),(17,8),(15,-12)],'forge',2,-.1)
            f([(-2,-11),(-2,26),(2,26),(2,-11)],'brass',2,-.2)
        else:
            for side in (-1,1):
                f([(side*20,7),(side*11,20),(0,25),(0,20),(side*9,16),
                   (side*16,5),(side*12,-10),(side*15,-12)],'brass',2,-.3)
                f([(side*17,1),(side*12,-8),(side*15,-15),(side*22,-11)],'forge',2,-.2)
            f([(-4,20),(0,26),(4,20),(0,15)],'hot',2,-.5)
        # Small violet circlet sphere, bound above the hood in a thin gold rim.
        for r,mat,tone,z in ((6,'brass',2,-.6),(4.5,'hot',1,-.7),(2.8,'hot',2,-.8)):
            f([(math.cos(t)*r,34+math.sin(t)*r) for t in [math.tau*n/16 for n in range(16)]],mat,tone,z)
        f([(-2,35),(-1,37),(1,36),(0,34)],'hot',3,-.9)
    elif kind=='shoulders':
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*side
            ink.plate([c-out*3+u*3,c+out*4+u*8,c+out*15+u*4,
                       c+out*18-u*5,c+out*4-u*7],'brass',2)
            ink.plate([c+out+u,c+out*5+u*4,c+out*12+u,c+out*14-u*3,c+out*5-u*4],'forge',2)
            orb(ink,c+out*10+u*14,7)
            for n in range(2):
                d=c+out*(8+n*6)-u*(5+n*2)
                ink.plate([d-u*4,d-out*2,d+u*2,d+out*2],'clothforge',2)
    elif kind=='gloves':
        for key in ('L','R'):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c)
            ink.bone(c,c+v*15,4,5,'forge',-1.3)
            ink.bone(c+v*11,c+v*14,5.4,5.7,'brass',-1.8,2)
            d=c+v*8+Q@V(0,5,0)
            ink.plate([d-a*4,d+v*7,d+a*4,d-v*4],'brass',2)
            ink.plate([d-a*2,d+v*4,d+a*2,d-v*2],'hot',2)
            ink.plate([c-a*4,c-a*3-v*6,c+a*3-v*6,c+a*4],'forge',1)
    elif kind=='pants':
        for key in ('L','R'):
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle']
            ink.bone(hip,knee,5,4.3,'veil',-1.2)
            ink.bone(knee,ankle,4.5,3.6,'veil',-1.3)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,7,-2),4.9,3.9,'veil',-1.5)
            d=knee+Q@V(0,5,0)
            ink.plate([d-a*3,d+u*5,d+a*3,d-u*4],'trim',2)
    else:raise ValueError(kind)
