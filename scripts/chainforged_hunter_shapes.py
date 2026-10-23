"""Original Beaststalker-inspired leather, gold edging, fur and hunting trophies."""
from cel_common import V,unit

def draw(ink,kind,p,Q,xf,j,h,colors):
    a,u=Q@V(1,0,0),Q@V(0,0,1)
    def plate(points,mat='forge',tone=2):ink.plate([xf(q) for q in points],mat,tone)
    if kind=='armor':
        import cel_common as cc
        cc.torso(ink,xf,'forge',8.7,5.9,36,70)
        for side in (-1,1):
            # Gold seams divide the leather breast and tapered overlapping skirts.
            plate([(side*1,8,68),(side*8,6.5,71),(side*9,6.5,62),
                   (side*2,9,53)],'brass',2)
            plate([(side*3,8.8,66),(side*7,7.4,68),(side*7,7.4,62),
                   (side*3,9.4,57)],'forge',2)
            plate([(side*1,8.5,52),(side*8,7,61),(side*9,7,42),
                   (side*2,9,39)],'brass',2)
            plate([(side*3,9.4,51),(side*7,8.1,57),(side*7,8.1,43),
                   (side*3,9.5,42)],'forge',1)
            plate([(side*3,5,40),(side*9,3,43),(side*14,3,27),
                   (side*8,6,23),(side*4,7,30)],'brass',2)
            plate([(side*5,6,38),(side*8,5,40),(side*11,5,28),
                   (side*8,7,26)],'forge',2)
            plate([(side*2,-7,68),(side*8,-6,69),(side*9,-6,40),
                   (side*2,-7,37)],'forge',1)
            plate([(side*3,-7.5,66),(side*4,-7.5,66),(side*5,-7.5,41),
                   (side*3,-7.5,40)],'brass',2)
            ink.bone(j['L' if side<0 else 'R']['shoulder'],j['L' if side<0 else 'R']['elbow'],3.8,3,'forge',-1)
        for z in (39,68):
            for x in range(-7,8,3):
                plate([(x-2,8,z+1),(x,9,z+3),(x+2,8,z+1),(x+1,9,z-2),(x-1,9,z-3)],'clothforge',2)
        for z,r in ((61,3.5),(39,4.5)):
            plate([(0,10,z+r),(-r,10,z),(0,10,z-r),(r,10,z)],'brass',3)
            plate([(0,10.4,z+r-1.3),(-r+1.3,10.4,z),(0,10.4,z-r+1.3),(r-1.3,10.4,z)],'hot',2)
    elif kind=='headgear':
        H,hd=h['H'],h['hd']-8
        def f(pts,mat='forge',tone=2,z=0):ink.poly([H(x*.78,y*.78) for x,y in pts],colors[mat][tone],hd+z)
        # Beast-head cap with pointed ears; the hero's eyes stay visible below it.
        f([(-20,-1),(-21,14),(-27,31),(-10,26),(0,30),(10,26),(27,31),
           (21,14),(20,-1),(12,4),(9,12),(0,9),(-9,12),(-12,4)],'forge',2)
        f([(-20,16),(-24,27),(-13,23),(-11,17)],'clothforge',1,-.1)
        f([(20,16),(24,27),(13,23),(11,17)],'clothforge',1,-.1)
        if h['front']<-.4:
            f([(-16,-3),(-17,15),(0,27),(17,15),(16,-3),(0,-8)],'forge',2,-.2)
            f([(-2,-7),(-2,24),(2,24),(2,-7)],'brass',1,-.3)
        else:
            for side in (-1,1):
                f([(side*2,13),(side*10,20),(side*15,16),(side*9,11)],'brass',2,-.3)
                f([(side*5,14),(side*10,17),(side*12,15),(side*8,13)],'hot',3,-.4)
                f([(side*14,9),(side*20,5),(side*20,-7),(side*14,-13),(side*11,-5)],'clothforge',2,-.2)
            f([(-5,12),(0,19),(5,12),(3,7),(-3,7)],'forge',1,-.5)
            f([(-3,10),(0,13),(3,10),(0,7)],'brass',2,-.6)
    elif kind=='shoulders':
        front=Q@V(0,1,0)
        for side,key in ((-1,'L'),(1,'R')):
            c=j[key]['shoulder'];out=a*side
            ink.plate([c-out*3+u*4,c+out*5+u*10,c+out*14+u*5,
                       c+out*17-u*6,c+out*4-u*8],'brass',2)
            ink.plate([c-out+u*3,c+out*5+u*7,c+out*12+u*3,
                       c+out*14-u*4,c+out*5-u*5],'forge',2)
            points=[c+out*12-u*2,c+out*19+u*5,c+out*23+u*16,c+out*22+u*29]
            for n in range(3):ink.bone(points[n],points[n+1],4-n*1.2,2.8-n*1.2,'clothforge',-1,3)
            for n in range(4):
                d=c+out*(2+n*3)-u*5+front*3
                ink.plate([d-out*2,d+u*3,d+out*2,d+out-u*4,d-out-u*3],'clothforge',2)
    elif kind=='gloves':
        for key in ('L','R'):
            c=j[key]['hand'];v=unit(j[key]['elbow']-c)
            ink.bone(c,c+v*15,4.1,5.3,'brass',-1.3)
            ink.bone(c+v,c+v*12,3.5,4.3,'forge',-1.8,2)
            d=c+v*13
            ink.bone(c+v*11,c+v*15,5.9,6.2,'clothforge',-2.1,2)
            d=c+v*6+Q@V(0,5,0)
            ink.plate([d-a*3,d+v*4,d+a*3,d-v*4],'brass',2)
            ink.plate([c-a*4,c-a*3-v*6,c+a*3-v*6,c+a*4],'forge',1)
    elif kind=='pants':
        front=Q@V(0,5,0)
        for key in ('L','R'):
            hip,knee,ankle=j[key]['hip'],j[key]['knee'],j[key]['ankle'];v=unit(ankle-knee)
            ink.bone(hip,knee,5.5,4.8,'trim',-1.2)
            ink.bone(knee,ankle,4.7,3.6,'trim',-1.3)
            for n in range(2):
                c=hip*(1-(n+1)/3)+knee*((n+1)/3)+front
                ink.plate([c-a*4,c-v*3,c+a*4,c+v*3,c-a*3+v*5],'leather',2)
            d=knee+front
            ink.plate([d-a*5,d-v*5,d+a*5,d+v*6],'trim',3)
            ink.plate([d-a*3,d-v*3,d+a*3,d+v*4],'leather',2)
            for n in range(5):
                d=knee+v*6+a*(n-2)*2+front
                ink.plate([d-a*2-v*3,d-v*5,d+a*2-v*3,d+a*2+v*2,d+v*4,d-a*2+v*2],'metal',2)
            ink.bone(ankle+Q@V(0,-2,-1),ankle+Q@V(0,7,-2),5.1,4,'trim',-1.5)
    else:raise ValueError(kind)
