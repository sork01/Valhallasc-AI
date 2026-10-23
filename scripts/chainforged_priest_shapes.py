"""Original azure-and-ivory vestments, glowing shoulder stones and a floating halo."""
import math
from cel_common import V,unit

def glow(ink,c,r):
    centre,z=ink.project(c)
    for rad,tone,bias in ((r+1.3,0,-5),(r,2,-5.1),(r*.6,3,-5.2)):
        ink.poly([centre+V(math.cos(math.tau*n/14)*rad,math.sin(math.tau*n/14)*rad) for n in range(14)],ink.color['hot'][tone],z+bias,outline=tone==0)

def draw(ink,kind,p,Q,xf,j,h,colors):
    a,u=Q@V(1,0,0),Q@V(0,0,1)
    def plate(points,mat='forge',tone=2):ink.plate([xf(q) for q in points],mat,tone)
    if kind=='armor':
        import cel_common as cc
        cc.torso(ink,xf,'forge',8.8,6,37,70)
        for side in (-1,1):
            # Ivory outer cloth wraps a broad azure center and ornate gold seams.
            plate([(side*.5,8.5,68),(side*8,6.7,72),(side*10,6.5,61),
                   (side*3,9,53),(side*.5,9,55)],'brass',2)
            plate([(side*2.5,9.3,65),(side*7,7.6,69),(side*8,7.4,62),
                   (side*3,9.7,56)],'clothforge',2)
            plate([(side*.6,9,53),(side*7,7.5,60),(side*9,7,41),
                   (side*.6,9,37)],'clothforge',2)
            plate([(side*2.5,9.6,51),(side*3.5,9.3,52),(side*7,8,42),
                   (side*6,8.5,40)],'brass',2)
            plate([(side*2,5,41),(side*10,3,43),(side*17,2,4),(side*2,8,3)],'forge',2)
            plate([(side*4,7,38),(side*8,5,40),(side*14,5,6),(side*9,7,5)],'clothforge',2)
            plate([(side*7,7.6,37),(side*9,6,38),(side*15,5.6,6),(side*13,6,5)],'brass',2)
            plate([(side*1,8.8,38),(side*4,8,39),(side*6,9,5),(side*1,10,3)],'brass',2)
            plate([(side*1.2,9.6,36),(side*2.5,8.8,36),(side*4,9.8,6),
                   (side*1.2,10.6,4)],'clothforge',1)
            plate([(side*2,-7,69),(side*8,-6,70),(side*10,-6,39),
                   (side*17,-7,5),(side*2,-9,4)],'forge',2)
            plate([(side*3,-7.5,67),(side*6,-7,67),(side*8,-7,37),
                   (side*12,-8,6),(side*8,-8.5,5),(side*5,-7.5,37)],'clothforge',2)
            ink.bone(j['L' if side<0 else 'R']['shoulder'],j['L' if side<0 else 'R']['elbow'],4.1,3.2,'forge',-1)
        for z,r in ((62,3),(40,4),(24,2.1),(13,1.7)):
            plate([(0,11,z+r),(-r,11,z),(0,11,z-r),(r,11,z)],'brass',3)
            plate([(0,11.4,z+r-1),(-r+1,11.4,z),(0,11.4,z-r+1),(r-1,11.4,z)],'hot',2)
    elif kind=='headgear':
        H,hd=h['H'],h['hd']-9
        # The supplied reference has an exposed head and a cyan floating halo.
        # A narrow oval stays above the actual head axis in all poses/facings.
        for n in range(32):
            t,q=math.tau*n/32,math.tau*(n+1)/32
            def at(v,rx,ry):return H(math.cos(v)*rx*.78,(31+math.sin(v)*ry)*.78)
            ink.poly([at(t,15,5),at(q,15,5),at(q,11.5,2.7),at(t,11.5,2.7)],colors['hot'][2],hd-.1)
            ink.poly([at(t,13.8,4.3),at(q,13.8,4.3),at(q,12.5,3.4),at(t,12.5,3.4)],colors['hot'][3],hd-.2,False)
    elif kind=='shoulders':
        front=Q@V(0,1,0)
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*side
            ink.plate([c-out*4-u*4,c-out*2+u*24,c+out*7+u*13,
                       c+out*17+u*10,c+out*24+u,c+out*15-u*3,c+out*5-u*8],'brass',2)
            ink.plate([c-out*2-u*2,c-out+u*19,c+out*6+u*10,
                       c+out*15+u*8,c+out*20+u*1,c+out*14-u,c+out*5-u*5],'forge',2)
            ink.plate([c+out*3+u*8,c+out*6+u*15,c+out*13+u*11,
                       c+out*10+u*3,c+out*7-u*2],'clothforge',2)
            for x,z,r in ((4,15,3),(10,10,3.2),(15,6,2.8)):
                glow(ink,c+out*x+u*z+front*5,r)
            for x,z in ((4,21),(13,14)):
                d=c+out*x+u*z
                ink.plate([d-out*2,d+out*3+u*7,d+u],'hot',1)
    elif kind=='gloves':
        for key in ('L','R'):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c);front=Q@V(0,5,0)
            ink.bone(c,c+v*15,5.1,4.2,'forge',-1.3)
            d=c+front
            ink.plate([d-a*8-v*3,d-a*4+v*13,d+a*4+v*13,d+a*8-v*3],'brass',2)
            ink.plate([d-a*5.5-v,d-a*2.5+v*10,d+a*2.5+v*10,d+a*5.5-v],'clothforge',2)
            ink.plate([c-a*4,c-a*3-v*6,c+a*3-v*6,c+a*4],'clothforge',1)
    elif kind=='pants':
        for key in ('L','R'):
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle']
            ink.bone(hip,knee,5,4.3,'cloth',-1.2)
            ink.bone(knee,ankle,4.5,3.6,'metal',-1.3)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,7,-2),4.9,3.9,'cloth',-1.5)
            d=knee+Q@V(0,5,0)
            ink.plate([d-a*3,d+u*5,d+a*3,d-u*4],'trim',2)
    else:raise ValueError(kind)
